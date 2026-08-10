"""Tests for autofill and prefill (Phase 3A, Tasks 4.1-4.2).

Covers the Done-when clauses directly:
- 4.1: a rule whose trigger is absent cannot fire; a three-assertion
  expansion yields THREE proposals; and a trigger spoken by the PATIENT
  still only produces proposals, never an insertion — the round-1 CRIT's
  failure case, pinned both by output type and structurally (a proposal
  cannot enter a ``GeneratedSection``).
- 4.2: prefill emits one proposal per atomic assertion in the selected
  seed; proposals are structurally distinct from assertions and cannot
  reach ``note.enc`` unconfirmed.

Also the Phase 1 carried item (Task 4.1's half): the single-tokenisation
pin is upgraded from a source scan to a REAL CALL-SITE pin — matching is
shown to run through ``note.content_tokens`` itself, not a lookalike.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

import scribe_desktop.note_fill as note_fill_module
from scribe_desktop.note import (
    GeneratedSection,
    NoteAssertion,
    NoteProposal,
    NoteSpan,
    text_digest,
)
from scribe_desktop.note_config import (
    AutofillRule,
    NoteConfig,
    NoteConfigInvalidError,
    PrefillTemplate,
    SingleClaimEntry,
)
from scribe_desktop.note_fill import (
    PrefillCandidate,
    PrefillSelectionAmbiguousError,
    UnknownPrefillError,
    autofill_proposals,
    detect_prefill_candidates,
    prefill_proposals,
)
from scribe_desktop.speech import SAMPLE_RATE
from scribe_desktop.transcription import (
    SPEAKER_1,
    SPEAKER_2,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
)

SESSION_ID = "c" * 32

# The id grammar proposals must satisfy (note._ID_PATTERN, restated here so
# the test does not import a private name).
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")


def _words(text: str) -> tuple[TranscriptWord, ...]:
    return tuple(
        TranscriptWord(
            word_text=token,
            start_seconds=index * 0.3,
            end_seconds=index * 0.3 + 0.25,
            probability=0.9,
            uncertain=False,
        )
        for index, token in enumerate(text.split())
    )


def _document(*spoken: tuple[str, str]) -> TranscriptDocument:
    texts = spoken or (("hello there", SPEAKER_1),)
    return TranscriptDocument(
        session_id=SESSION_ID,
        created_at=datetime(2026, 8, 10, 9, 0, tzinfo=UTC),
        model_name="mock",
        sample_rate=SAMPLE_RATE,
        transcript_segments=tuple(
            TranscriptSegment(
                start_seconds=float(index * 10),
                end_seconds=float(index * 10 + 5),
                speaker=speaker,
                transcript_words=_words(text),
            )
            for index, (text, speaker) in enumerate(texts)
        ),
    )


def _rule(
    rule_id: str = "r-hep",
    trigger: str = "home exercise",
    *expansion: str,
    section_key: str = "advice_home_exercise",
) -> AutofillRule:
    return AutofillRule.model_validate(
        {
            "rule_id": rule_id,
            "section_key": section_key,
            "trigger_phrase": trigger,
            "expansion": list(expansion) or ["Home exercise programme reviewed."],
        }
    )


def _prefill(
    prefill_id: str = "pf-knee",
    display_name: str = "Knee",
    keywords: tuple[str, ...] = ("knee",),
    seeds: tuple[tuple[str, str], ...] = (("objective_examination", "Knee inspected."),),
) -> PrefillTemplate:
    return PrefillTemplate.model_validate(
        {
            "prefill_id": prefill_id,
            "display_name": display_name,
            "region_keywords": list(keywords),
            "seed_assertions": [
                {"section_key": section_key, "seed_text": seed_text}
                for section_key, seed_text in seeds
            ],
        }
    )


def _config(
    *,
    rules: tuple[AutofillRule, ...] = (),
    prefills: tuple[PrefillTemplate, ...] = (),
) -> NoteConfig:
    return NoteConfig(autofill_rules=rules, prefill_templates=prefills)


# ---------------------------------------------------------------------------
# Task 4.1 — autofill.
# ---------------------------------------------------------------------------


class TestAutofill:
    def test_absent_trigger_cannot_fire(self) -> None:
        config = _config(rules=(_rule(trigger="dry needling"),))
        document = _document(("the knee is sore today", SPEAKER_1))
        assert autofill_proposals(document, config) == ()

    def test_three_assertion_expansion_yields_three_proposals(self) -> None:
        expansion = (
            "Home exercise programme reviewed.",
            "Exercises progressed as tolerated.",
            "Patient advised to continue daily.",
        )
        config = _config(rules=(_rule("r-hep", "home exercise", *expansion),))
        document = _document(("we reviewed your home exercise programme", SPEAKER_2))
        proposals = autofill_proposals(document, config)
        assert len(proposals) == 3
        # One proposal PER ATOMIC ASSERTION, exact text, authored order.
        assert tuple(p.note_excerpt for p in proposals) == expansion
        for proposal in proposals:
            assert proposal.provenance == "autofill"
            assert proposal.section_key == "advice_home_exercise"
            assert proposal.rule_id == "r-hep"
            assert proposal.config_digest == config.config_digest()
            # "home" is word index 3 in the segment -> 3 * 0.3 s.
            assert proposal.trigger_start_seconds == pytest.approx(0.9)

    def test_patient_spoken_trigger_produces_only_proposals_never_an_insertion(self) -> None:
        # The round-1 CRIT's failure case, pinned: presence gates candidacy,
        # not truth. The PATIENT saying the trigger yields exactly the same
        # proposal-shaped output — and nothing assertion-shaped.
        config = _config(rules=(_rule(),))
        document = _document(("I have been doing my home exercise plan", SPEAKER_1))
        proposals = autofill_proposals(document, config)
        assert proposals
        assert all(isinstance(p, NoteProposal) for p in proposals)
        assert not any(isinstance(p, NoteAssertion) for p in proposals)
        # Structurally: the emitted proposal cannot be placed in a section,
        # so no code path can turn a match into an insertion by mistake.
        with pytest.raises(ValidationError):
            GeneratedSection(
                section_key="advice_home_exercise",
                note_assertions=(proposals[0],),  # type: ignore[arg-type]
            )

    def test_matching_normalises_case_punctuation_and_fillers(self) -> None:
        config = _config(rules=(_rule(),))
        document = _document(("Home, um, EXERCISE! going well", SPEAKER_1))
        proposals = autofill_proposals(document, config)
        assert len(proposals) == 1
        # The trigger's start time is the FIRST matched word's start.
        assert proposals[0].trigger_start_seconds == pytest.approx(0.0)

    def test_trigger_does_not_match_across_a_segment_boundary(self) -> None:
        # Deliberate semantics (module docstring): a phrase split across a
        # VAD segment boundary fails toward silence, never toward a wrong
        # candidate.
        config = _config(rules=(_rule(),))
        document = _document(
            ("we talked about home", SPEAKER_2),
            ("exercise is important", SPEAKER_2),
        )
        assert autofill_proposals(document, config) == ()

    def test_first_occurrence_wins_and_later_repeats_add_nothing(self) -> None:
        config = _config(rules=(_rule(),))
        document = _document(
            ("no trigger here", SPEAKER_1),
            ("your home exercise plan", SPEAKER_2),
            ("keep the home exercise going", SPEAKER_2),
        )
        proposals = autofill_proposals(document, config)
        assert len(proposals) == 1
        # Word index 1 of segment 1 -> 0.3 s (segment-relative fixture times).
        assert proposals[0].trigger_start_seconds == pytest.approx(0.3)

    def test_rules_fire_independently(self) -> None:
        config = _config(
            rules=(
                _rule("r-hep", "home exercise"),
                _rule("r-ice", "ice pack", "Ice pack use explained."),
                _rule("r-absent", "dry needling"),
            )
        )
        document = _document(("home exercise and an ice pack", SPEAKER_2))
        proposals = autofill_proposals(document, config)
        assert tuple(p.rule_id for p in proposals) == ("r-hep", "r-ice")

    def test_proposal_ids_are_deterministic_unique_and_id_shaped(self) -> None:
        expansion = ("First claim.", "Second claim.")
        config = _config(rules=(_rule("r-hep", "home exercise", *expansion),))
        document = _document(("home exercise reviewed", SPEAKER_2))
        first = autofill_proposals(document, config)
        second = autofill_proposals(document, config)
        assert first == second
        ids = [p.proposal_id for p in first]
        assert len(set(ids)) == len(ids) == 2
        for proposal_id in ids:
            assert _ID_RE.match(proposal_id)

    def test_forged_config_dies_at_the_boundary(self) -> None:
        # The round-12 lesson applied here: a validator-skipping construction
        # must not survive to a stamped digest. Duplicate rule ids can only
        # coexist because validation was skipped.
        rule = _rule()
        forged: Any = NoteConfig.model_construct(
            template_profiles=(),
            autofill_rules=(rule, rule),
            prefill_templates=(),
        )
        with pytest.raises(NoteConfigInvalidError):
            autofill_proposals(_document(), forged)

    # Round 15 PR-HIGH-001 regression: the emitter is a mechanical
    # one-authored-entry -> one-proposal mapper. It never splits, joins, or
    # deduplicates — atomicity is the AUTHORING boundary's job.
    def test_emitter_performs_no_runtime_splitting_or_dedup(self) -> None:
        rule = AutofillRule.model_validate(
            {
                "rule_id": "r-override",
                "section_key": "advice_home_exercise",
                "trigger_phrase": "home exercise",
                "expansion": [
                    "Home exercise programme reviewed.",
                    {
                        # Compound-LOOKING single assertion, author-attested:
                        # must emit as ONE proposal with the exact full text,
                        # internal punctuation and all.
                        "assertion_text": "Advised to see Dr. Smith for review.",
                        "single_claim": True,
                    },
                ],
            }
        )
        config = _config(rules=(rule,))
        document = _document(("home exercise going well", SPEAKER_2))
        proposals = autofill_proposals(document, config)
        # One-to-one with the authored entries: same texts, same order, same
        # count — no split of the Dr.-Smith entry, no merge, no dedup.
        assert tuple(p.note_excerpt for p in proposals) == rule.expansion_texts()
        assert len(proposals) == len(rule.expansion) == 2
        assert isinstance(rule.expansion[1], SingleClaimEntry)


# ---------------------------------------------------------------------------
# Phase 1 carried item — the tokenisation pin becomes a call-site pin.
# ---------------------------------------------------------------------------


class TestTokenisationCallSite:
    def test_matching_runs_through_the_single_tokenisation_source(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Task 1.2's pin, upgraded per the Phase 1 handoff: not just "no
        second implementation exists in src/" (test_note.py still pins
        that), but that autofill matching CALLS ``note.content_tokens`` for
        both the trigger and the transcript words."""
        seen: list[str] = []
        real = note_fill_module.content_tokens

        def recording(text: str) -> tuple[str, ...]:
            seen.append(text)
            return real(text)

        monkeypatch.setattr(note_fill_module, "content_tokens", recording)
        config = _config(rules=(_rule(),))
        document = _document(("home exercise reviewed", SPEAKER_2))
        proposals = autofill_proposals(document, config)
        assert len(proposals) == 1
        assert "home exercise" in seen  # the trigger phrase
        assert "reviewed" in seen  # a transcript word

    def test_prefill_detection_runs_through_the_same_source(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[str] = []
        real = note_fill_module.content_tokens

        def recording(text: str) -> tuple[str, ...]:
            seen.append(text)
            return real(text)

        monkeypatch.setattr(note_fill_module, "content_tokens", recording)
        config = _config(prefills=(_prefill(),))
        document = _document(("the knee is sore", SPEAKER_1))
        assert detect_prefill_candidates(document, config)
        assert "knee" in seen


# ---------------------------------------------------------------------------
# Task 4.2 — prefill.
# ---------------------------------------------------------------------------


class TestPrefillDetection:
    def test_detection_finds_a_region_by_keyword(self) -> None:
        config = _config(prefills=(_prefill(),))
        document = _document(("my knee has been sore", SPEAKER_1))
        candidates = detect_prefill_candidates(document, config)
        assert candidates == (
            PrefillCandidate(
                prefill_id="pf-knee",
                display_name="Knee",
                start_seconds=pytest.approx(0.3),  # type: ignore[arg-type]
            ),
        )

    def test_no_keyword_no_candidate(self) -> None:
        config = _config(prefills=(_prefill(),))
        document = _document(("shoulder feels fine", SPEAKER_1))
        assert detect_prefill_candidates(document, config) == ()

    def test_candidates_are_ordered_by_earliest_match(self) -> None:
        config = _config(
            prefills=(
                _prefill("pf-knee", "Knee", ("knee",)),
                _prefill("pf-shoulder", "Shoulder", ("shoulder",)),
            )
        )
        document = _document(("the shoulder then the knee", SPEAKER_1))
        candidates = detect_prefill_candidates(document, config)
        assert tuple(c.prefill_id for c in candidates) == ("pf-shoulder", "pf-knee")


class TestPrefillProposals:
    def test_multi_assertion_seed_yields_one_proposal_per_claim(self) -> None:
        # 4.2's Done-when pin: three seed assertions -> three proposals,
        # exact text, each carrying ITS OWN section.
        seeds = (
            ("objective_examination", "Knee inspected."),
            ("objective_examination", "Active range of motion assessed."),
            ("outcome_measures", "Pain score recorded."),
        )
        config = _config(prefills=(_prefill(seeds=seeds),))
        document = _document(("my knee hurts", SPEAKER_1))
        proposals = prefill_proposals(document, config)
        assert len(proposals) == 3
        assert tuple((p.section_key, p.note_excerpt) for p in proposals) == seeds
        for proposal in proposals:
            assert proposal.provenance == "prefill"
            assert proposal.rule_id == "pf-knee"
            assert proposal.config_digest == config.config_digest()
            assert proposal.trigger_start_seconds is not None

    def test_zero_detections_emit_nothing(self) -> None:
        config = _config(prefills=(_prefill(),))
        document = _document(("shoulder feels fine", SPEAKER_1))
        assert prefill_proposals(document, config) == ()

    def test_ambiguous_detection_raises_naming_the_candidates(self) -> None:
        config = _config(
            prefills=(
                _prefill("pf-knee", "Knee", ("knee",)),
                _prefill("pf-shoulder", "Shoulder", ("shoulder",)),
            )
        )
        document = _document(("knee and shoulder both sore", SPEAKER_1))
        with pytest.raises(PrefillSelectionAmbiguousError) as excinfo:
            prefill_proposals(document, config)
        assert set(excinfo.value.candidate_ids) == {"pf-knee", "pf-shoulder"}

    def test_explicit_override_wins_even_when_ambiguous(self) -> None:
        config = _config(
            prefills=(
                _prefill("pf-knee", "Knee", ("knee",)),
                _prefill("pf-shoulder", "Shoulder", ("shoulder",)),
            )
        )
        document = _document(("knee and shoulder both sore", SPEAKER_1))
        proposals = prefill_proposals(document, config, prefill_id="pf-shoulder")
        assert all(p.rule_id == "pf-shoulder" for p in proposals)

    def test_explicit_override_works_without_any_keyword_match(self) -> None:
        # Region keywords are a heuristic; the clinician is not. An explicit
        # choice needs no detection — and with no match there is no trigger
        # time to claim.
        config = _config(prefills=(_prefill(),))
        document = _document(("shoulder feels fine", SPEAKER_1))
        proposals = prefill_proposals(document, config, prefill_id="pf-knee")
        assert len(proposals) == 1
        assert proposals[0].trigger_start_seconds is None

    def test_unknown_prefill_id_raises(self) -> None:
        config = _config(prefills=(_prefill(),))
        with pytest.raises(UnknownPrefillError, match="pf-hip"):
            prefill_proposals(_document(), config, prefill_id="pf-hip")

    def test_prefill_emitter_does_not_split_an_attested_seed(self) -> None:
        # Round 15 regression, prefill side: a single_claim-attested seed
        # flows through as ONE proposal with its exact text.
        seeds_with_override = PrefillTemplate.model_validate(
            {
                "prefill_id": "pf-knee",
                "display_name": "Knee",
                "region_keywords": ["knee"],
                "seed_assertions": [
                    {
                        "section_key": "objective_examination",
                        "seed_text": "Reviewed by Dr. Smith previously.",
                        "single_claim": True,
                    }
                ],
            }
        )
        config = _config(prefills=(seeds_with_override,))
        document = _document(("my knee hurts", SPEAKER_1))
        proposals = prefill_proposals(document, config)
        assert tuple(p.note_excerpt for p in proposals) == (
            "Reviewed by Dr. Smith previously.",
        )

    def test_prefill_proposals_are_deterministic_unique_and_id_shaped(self) -> None:
        seeds = (
            ("objective_examination", "Knee inspected."),
            ("outcome_measures", "Pain score recorded."),
        )
        config = _config(prefills=(_prefill(seeds=seeds),))
        document = _document(("my knee hurts", SPEAKER_1))
        first = prefill_proposals(document, config)
        second = prefill_proposals(document, config)
        assert first == second
        ids = [p.proposal_id for p in first]
        assert len(set(ids)) == len(ids) == 2
        for proposal_id in ids:
            assert _ID_RE.match(proposal_id)

    def test_forged_config_dies_at_the_boundary(self) -> None:
        prefill = _prefill()
        forged: Any = NoteConfig.model_construct(
            template_profiles=(),
            autofill_rules=(),
            prefill_templates=(prefill, prefill),
        )
        with pytest.raises(NoteConfigInvalidError):
            prefill_proposals(_document(), forged)


# ---------------------------------------------------------------------------
# The through-line: nothing from this phase reaches note.enc unconfirmed.
# ---------------------------------------------------------------------------


class TestProposalsCannotBecomeAssertionsUnconfirmed:
    def test_a_prefill_proposal_cannot_enter_a_section(self) -> None:
        config = _config(prefills=(_prefill(),))
        document = _document(("my knee hurts", SPEAKER_1))
        (proposal,) = prefill_proposals(document, config)
        with pytest.raises(ValidationError):
            GeneratedSection(
                section_key=proposal.section_key,
                note_assertions=(proposal,),  # type: ignore[arg-type]
            )

    def test_an_unconfirmed_assertion_built_from_a_proposal_is_rejected(self) -> None:
        # Even hand-carrying a proposal's fields into an assertion fails
        # without a ConfirmationDecision: the confirmation boundary is the
        # type's, not this module's.
        config = _config(prefills=(_prefill(),))
        document = _document(("my knee hurts", SPEAKER_1))
        (proposal,) = prefill_proposals(document, config)
        with pytest.raises(ValidationError, match="ConfirmationDecision"):
            NoteAssertion(
                assertion_id="a-1",
                section_key=proposal.section_key,
                note_span=NoteSpan(
                    span_text=proposal.note_excerpt, provenance=proposal.provenance
                ),
                proposal_id=proposal.proposal_id,
                shown_text_digest=text_digest(proposal.note_excerpt),
                config_digest=proposal.config_digest,
            )
