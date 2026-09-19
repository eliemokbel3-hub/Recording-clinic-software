"""Note-learning-and-styles plan Phase 2, Task 2.4: Save-as-ratification.

The non-Qt half of the D5 contract, pinned end to end:
- ``note_fill.config_decisions`` MINTS a ``decided_by="config"`` decision for
  every hand-authored rule and prefill entry and for a learned rule only
  when its sidecar record says ``auto_confirmed`` (carrying its count);
  every other learned rule proposes;
- ``compose_draft`` carries those decisions on the draft, and ``NoteDraft``
  refuses a decision that names an unknown proposal, was decided by the
  clinician, declines, or was minted under another digest or shown text;
- ``finalise_note`` accepts a config decision ONLY when the draft carries
  it (the emitter mints, the review surface passes on or replaces), and a
  clinician decline of a pre-filled proposal stands;
- Check 3 draws NO ``clinician_asserted`` for a config-decided line while
  every other warning keeps its gate (``autofill_trigger_absent`` still
  blocks a config-decided autofill line whose trigger is absent; the
  omission review still fires on the note); and a note holding ONLY
  pre-filled lines finalises with just that unrelated review warning and
  writes through ``write_note`` — the counted Save's half of the end-to-end
  case (the gating half is the Note tab's, in ``test_ui_screens.py``).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from scribe_desktop.note import (
    CANONICAL_SECTION_KEYS,
    ConfirmationDecision,
    GeneratedSection,
    NoteDraft,
    NoteProposal,
    ProposalEvidenceError,
    ProposalResolution,
    compose_draft,
    finalise_note,
)
from scribe_desktop.note_check import provenance_warnings
from scribe_desktop.note_config import (
    LEARNED_RULES_SIDECAR_FILENAME,
    AutofillRule,
    LearnedRuleCandidate,
    LearnedRuleEntry,
    NoteConfig,
    PrefillSeedAssertion,
    PrefillTemplate,
    SectionMapping,
    TemplateProfile,
    TemplateTarget,
    append_learned_rules,
    is_learned_rule_id,
)
from scribe_desktop.note_fill import autofill_proposals, config_decisions, prefill_proposals
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import read_note, write_note
from scribe_desktop.transcription import (
    SPEAKER_1,
    SPEAKER_2,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
    write_transcript,
)
from scribe_desktop.ui import models

SESSION_ID = "f" * 32
_NOW = datetime(2026, 9, 19, 10, 0, tzinfo=UTC)
LEARNED_ID = "learned-01J8ZK3Q9W4E5R6T7Y8U9I0O1P"


def _profile() -> TemplateProfile:
    return TemplateProfile(
        template_profile_id="clinic-a",
        display_name="Clinic A",
        template_targets=(
            TemplateTarget(
                target_id="t-main", group="Notes", field_label="Main", target_type="rich_text"
            ),
        ),
        section_mappings=tuple(
            SectionMapping(section_key=key, target_id="t-main")
            for key in CANONICAL_SECTION_KEYS
            if key != "consent"
        ),
        intentionally_unmapped=("consent",),
    )


def _config() -> NoteConfig:
    return NoteConfig(
        template_profiles=(_profile(),),
        autofill_rules=(
            AutofillRule(
                rule_id="rule-ice",
                section_key="advice_home_exercise",
                trigger_phrase="ice pack",
                expansion=("Ice pack use explained.",),
            ),
            AutofillRule(
                rule_id=LEARNED_ID,
                section_key="treatment_performed",
                trigger_phrase="crack into the neck",
                expansion=("HVLA Cx",),
            ),
        ),
        prefill_templates=(
            PrefillTemplate(
                prefill_id="knee-exam",
                display_name="Knee examination",
                region_keywords=("knee",),
                seed_assertions=(
                    PrefillSeedAssertion(
                        section_key="objective_examination", seed_text="Knee effusion assessed."
                    ),
                ),
            ),
        ),
    )


_CONFIG = _config()
CONFIG_DIGEST = _CONFIG.config_digest()


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


_TURNS = (
    ("My left knee is sore", SPEAKER_1),
    ("You should use an ice pack tonight", SPEAKER_2),
    ("ok we'll put a crack into the neck now", SPEAKER_2),
    ("Review again in 2 weeks", SPEAKER_2),  # a number no assertion quotes
)


def _document() -> TranscriptDocument:
    return TranscriptDocument(
        session_id=SESSION_ID,
        created_at=_NOW,
        model_name="mock",
        sample_rate=16_000,
        transcript_segments=tuple(
            TranscriptSegment(
                start_seconds=float(index * 10),
                end_seconds=float(index * 10 + 5),
                speaker=speaker,
                transcript_words=_words(text),
            )
            for index, (text, speaker) in enumerate(_TURNS)
        ),
    )


class _EmptyProvider:
    """Quotes nothing, so a note built from it holds only proposal-derived lines."""

    @property
    def provider_name(self) -> str:
        return "empty-v1"

    def generate_sections(self, request: Any) -> tuple[GeneratedSection, ...]:
        return ()


def _proposals() -> tuple[NoteProposal, ...]:
    document = _document()
    return (*autofill_proposals(document, _CONFIG), *prefill_proposals(document, _CONFIG))


def _by_rule(proposals: tuple[NoteProposal, ...]) -> dict[str, NoteProposal]:
    return {proposal.rule_id: proposal for proposal in proposals}


def _auto_confirmed(count: int = 3) -> dict[str, LearnedRuleEntry]:
    return {LEARNED_ID: LearnedRuleEntry(learned_at=_NOW, confirmations=count, auto_confirmed=True)}


def _draft(learned: dict[str, LearnedRuleEntry] | None = None) -> NoteDraft:
    return compose_draft(
        _document(),
        _CONFIG,
        _EmptyProvider(),
        clinician_speaker=SPEAKER_2,
        learned_rules=learned,
        decided_at=_NOW,
    )


def _codes(warnings: tuple[Any, ...]) -> list[str]:
    return [w.note_warning_code for w in warnings]


# ---------------------------------------------------------------------------
# The emitter mints the decisions (D4 / D5).
# ---------------------------------------------------------------------------


class TestConfigDecisions:
    def test_hand_authored_rules_and_prefills_pre_fill_while_a_learned_rule_proposes(
        self,
    ) -> None:
        proposals = _proposals()
        assert set(_by_rule(proposals)) == {"rule-ice", LEARNED_ID, "knee-exam"}
        decisions = config_decisions(proposals, learned={}, decided_at=_NOW)
        decided = {decision.proposal_id: decision for decision in decisions}
        ice, knee = _by_rule(proposals)["rule-ice"], _by_rule(proposals)["knee-exam"]
        assert set(decided) == {ice.proposal_id, knee.proposal_id}
        for proposal in (ice, knee):
            decision = decided[proposal.proposal_id]
            assert decision.shown_text_digest == proposal.shown_text_digest
            assert decision.confirmation.decided_by == "config"
            assert decision.confirmation.note_confirmation == "confirmed"
            assert decision.confirmation.config_digest == proposal.config_digest == CONFIG_DIGEST
            assert decision.confirmation.confirmation_count is None
            assert decision.confirmation.decided_at == _NOW

    def test_an_auto_confirmed_learned_rule_pre_fills_with_its_count(self) -> None:
        proposals = _proposals()
        learned = _by_rule(proposals)[LEARNED_ID]
        assert is_learned_rule_id(learned.rule_id)
        for entry, expected in (
            ({}, False),
            ({LEARNED_ID: LearnedRuleEntry(learned_at=_NOW, confirmations=2)}, False),
            (_auto_confirmed(3), True),
        ):
            decisions = config_decisions(proposals, learned=entry, decided_at=_NOW)
            mine = [d for d in decisions if d.proposal_id == learned.proposal_id]
            assert bool(mine) is expected, entry
            if mine:
                assert mine[0].confirmation.confirmation_count == 3

    def test_nothing_is_minted_for_no_proposals(self) -> None:
        assert config_decisions((), learned=_auto_confirmed(), decided_at=_NOW) == ()


# ---------------------------------------------------------------------------
# The draft carries them; the type refuses anything else.
# ---------------------------------------------------------------------------


class TestDraftCarriesDecisions:
    def test_compose_draft_carries_the_emitters_decisions(self) -> None:
        draft = _draft()
        by_rule = _by_rule(draft.note_proposals)
        decided = {decision.proposal_id for decision in draft.config_decisions}
        assert decided == {by_rule["rule-ice"].proposal_id, by_rule["knee-exam"].proposal_id}
        assert _draft(_auto_confirmed()).config_decisions != draft.config_decisions
        assert len(_draft(_auto_confirmed()).config_decisions) == 3
        assert _draft(None).config_decisions == draft.config_decisions

    @pytest.mark.parametrize(
        ("mutate", "message"),
        [
            (lambda d, p: d.model_copy(update={"confirmation": d.confirmation.model_copy(
                update={"proposal_id": "autofill-nobody"})}), "never emitted"),
            (lambda d, p: ProposalResolution(
                shown_text_digest=p.shown_text_digest,
                confirmation=ConfirmationDecision(
                    proposal_id=p.proposal_id, note_confirmation="confirmed", decided_at=_NOW
                ),
            ), "config decisions only"),
            (lambda d, p: ProposalResolution(
                shown_text_digest=p.shown_text_digest,
                confirmation=ConfirmationDecision(
                    proposal_id=p.proposal_id, note_confirmation="declined", decided_at=_NOW,
                    decided_by="config", config_digest=p.config_digest,
                ),
            ), "cannot decline"),
            (lambda d, p: ProposalResolution(
                shown_text_digest=p.shown_text_digest,
                confirmation=ConfirmationDecision(
                    proposal_id=p.proposal_id, note_confirmation="confirmed", decided_at=_NOW,
                    decided_by="config", config_digest="sha256-v1:" + "0" * 64,
                ),
            ), "draft's own config_digest"),
            (lambda d, p: d.model_copy(update={"shown_text_digest": "sha256-v1:" + "1" * 64}),
             "text its proposal inserts"),
        ],
        ids=["unknown-proposal", "clinician-decided", "declined", "other-digest", "other-text"],
    )
    def test_the_draft_refuses_a_decision_it_did_not_mint(
        self, mutate: Any, message: str
    ) -> None:
        draft = _draft()
        decision = draft.config_decisions[0]
        proposal = next(p for p in draft.note_proposals if p.proposal_id == decision.proposal_id)
        bad = mutate(decision, proposal)
        with pytest.raises(ValidationError, match=message):
            draft.model_copy(update={"config_decisions": (bad,)}).model_validate(
                draft.model_copy(update={"config_decisions": (bad,)}).model_dump()
            )

    def test_a_duplicate_decision_is_refused(self) -> None:
        draft = _draft()
        doubled = (draft.config_decisions[0], draft.config_decisions[0])
        with pytest.raises(ValidationError, match="duplicate config decision"):
            NoteDraft.model_validate(
                draft.model_copy(update={"config_decisions": doubled}).model_dump()
            )


# ---------------------------------------------------------------------------
# finalise_note: minted decisions only; the check exemption; write_note.
# ---------------------------------------------------------------------------


class TestFinaliseAndCheck:
    def test_the_counted_save_ratifies_only_pre_filled_lines_and_writes(
        self, tmp_path: Path
    ) -> None:
        """A note holding ONLY pre-filled lines: no ``clinician_asserted``,
        no blocking warning, one unrelated review (the omission of "2
        weeks"), and it writes and reads back with its config decisions."""
        draft = _draft(_auto_confirmed())
        note = finalise_note(draft, list(draft.config_decisions), _document(), _CONFIG)
        assertions = [a for s in note.note_sections for a in s.note_assertions]
        assert len(assertions) == 3
        for assertion in assertions:
            assert models.is_prefilled(assertion)
            assert assertion.confirmation is not None
            assert assertion.confirmation.config_digest == note.config_digest
        counts = {a.proposal_id: a.confirmation.confirmation_count for a in assertions}  # type: ignore[union-attr]
        learned = _by_rule(draft.note_proposals)[LEARNED_ID].proposal_id
        assert counts[learned] == 3 and all(v is None for k, v in counts.items() if k != learned)
        assert _codes(note.note_warnings) == ["high_risk_omission"]
        assert note.blocking_warnings() == ()
        body = models.format_note_body(note)
        assert f"[{models.PREFILLED_MARK} - autofill (clinician-authored)]" in body
        assert f"[{models.PREFILLED_MARK} - prefill (clinician-authored)]" in body
        session_dir = tmp_path / SESSION_ID
        session_dir.mkdir()
        crypto = SessionCrypto()
        write_transcript(session_dir, crypto, _document())
        write_note(session_dir, crypto, note, _CONFIG)
        assert read_note(session_dir, crypto) == note

    def test_a_config_decision_the_draft_did_not_mint_is_refused(self) -> None:
        draft = _draft()
        minted = draft.config_decisions[0]
        forged = minted.model_copy(
            update={
                "confirmation": minted.confirmation.model_copy(
                    update={"decided_at": _NOW.replace(minute=5)}
                )
            }
        )
        with pytest.raises(ProposalEvidenceError, match="not the one the emitter minted"):
            finalise_note(draft, [forged], _document(), _CONFIG)
        # A config decision for a proposal the config did NOT decide (the
        # learned rule with no auto-confirm) is likewise refused.
        proposal = _by_rule(draft.note_proposals)[LEARNED_ID]
        for_learned = ProposalResolution(
            shown_text_digest=proposal.shown_text_digest,
            confirmation=ConfirmationDecision(
                proposal_id=proposal.proposal_id,
                note_confirmation="confirmed",
                decided_at=_NOW,
                decided_by="config",
                config_digest=proposal.config_digest,
            ),
        )
        with pytest.raises(ProposalEvidenceError, match="not the one the emitter minted"):
            finalise_note(draft, [for_learned], _document(), _CONFIG)

    def test_the_clinician_may_decline_a_pre_filled_line(self) -> None:
        """A Remove is the clinician's DECLINE resolution: the line leaves the
        note and the proposal is resolved, so nothing about it blocks. (Every
        proposal here is config-decided; a learned rule still under its
        threshold would be a genuinely undecided proposal and stay an error —
        the next test pins that.)"""
        draft = _draft(_auto_confirmed())
        ice_id = _by_rule(draft.note_proposals)["rule-ice"].proposal_id
        [ice] = [d for d in draft.config_decisions if d.proposal_id == ice_id]
        declined = ProposalResolution(
            shown_text_digest=ice.shown_text_digest,
            confirmation=ConfirmationDecision(
                proposal_id=ice.proposal_id, note_confirmation="declined", decided_at=_NOW
            ),
        )
        others = [d for d in draft.config_decisions if d.proposal_id != ice.proposal_id]
        note = finalise_note(draft, [declined, *others], _document(), _CONFIG)
        ids = {a.assertion_id for s in note.note_sections for a in s.note_assertions}
        assert ice.proposal_id not in ids
        assert "unconfirmed_proposal" not in _codes(note.note_warnings)
        assert note.blocking_warnings() == ()
        # The same decline over a draft whose LEARNED rule still proposes: the
        # declined line is resolved, the undecided learned proposal is the
        # one and only error.
        pending = _draft()
        [ice] = [d for d in pending.config_decisions if d.proposal_id == ice_id]
        others = [d for d in pending.config_decisions if d.proposal_id != ice_id]
        note = finalise_note(pending, [declined, *others], _document(), _CONFIG)
        undecided = [w for w in note.note_warnings if w.note_warning_code == "unconfirmed_proposal"]
        assert [w.section_key for w in undecided] == ["treatment_performed"]  # the learned rule

    def test_no_clinician_asserted_for_config_decided_lines_only(self) -> None:
        draft = _draft()
        by_rule = _by_rule(draft.note_proposals)
        learned = by_rule[LEARNED_ID]
        clicked = ProposalResolution(
            shown_text_digest=learned.shown_text_digest,
            confirmation=ConfirmationDecision(
                proposal_id=learned.proposal_id, note_confirmation="confirmed", decided_at=_NOW
            ),
        )
        note = finalise_note(
            draft, [*draft.config_decisions, clicked], _document(), _CONFIG
        )
        warnings = provenance_warnings(note, _document(), _CONFIG)
        asserted = {w.assertion_id for w in warnings if w.note_warning_code == "clinician_asserted"}
        assert asserted == {learned.proposal_id}  # the clinician-clicked line only
        assert "unconfirmed_proposal" not in _codes(warnings)

    def test_every_other_check_keeps_its_gate_on_a_config_decided_line(self) -> None:
        """``autofill_trigger_absent`` (error) still blocks a pre-filled
        autofill line whose trigger this transcript never spoke."""
        draft = _draft()
        without_ice = _document().model_copy(
            update={
                "transcript_segments": tuple(
                    seg for seg in _document().transcript_segments
                    if "ice" not in " ".join(w.word_text for w in seg.transcript_words)
                )
            }
        )
        note = finalise_note(draft, list(draft.config_decisions), _document(), _CONFIG)
        warnings = provenance_warnings(note, without_ice, _CONFIG)
        assert "clinician_asserted" not in _codes(warnings)
        absent = [w for w in warnings if w.note_warning_code == "autofill_trigger_absent"]
        assert [w.assertion_id for w in absent] == [
            _by_rule(draft.note_proposals)["rule-ice"].proposal_id
        ]
        assert absent[0].severity == "error"

    def test_a_pending_learned_proposal_still_blocks(self) -> None:
        draft = _draft()
        note = finalise_note(draft, list(draft.config_decisions), _document(), _CONFIG)
        assert "unconfirmed_proposal" in _codes(note.blocking_warnings())


class TestLearnedRuleStates:
    """The generator's sidecar read (``ui.models.learned_rule_states``) is
    fail-SAFE: absent → no entries; malformed → no entries plus the C8 note,
    so every learned rule PROPOSES and nothing pre-fills on a broken record
    (round 12 LOW-002)."""

    def test_absent_and_present_sidecars(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        assert models.learned_rule_states(root) == ({}, ())
        [added] = append_learned_rules(
            [LearnedRuleCandidate("treatment_performed", "crack into the neck", "HVLA Cx")],
            config_root=root,
            learned_at=_NOW,
        ).added
        entries, notes = models.learned_rule_states(root)
        assert set(entries) == {added.rule_id} and notes == ()

    def test_a_malformed_sidecar_yields_no_entries_and_the_note(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        root.mkdir(parents=True)
        (root / LEARNED_RULES_SIDECAR_FILENAME).write_text("{not json", encoding="utf-8")
        entries, notes = models.learned_rule_states(root)
        assert entries == {}
        [note] = notes
        assert note.startswith("The learned-shorthand record could not be read")
        assert "Practitioner tab" in note
