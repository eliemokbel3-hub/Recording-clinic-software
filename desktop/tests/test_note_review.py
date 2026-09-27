"""The Note tab's review decisions, Qt-free (note-learning plan Task H6).

``ui.note_review`` is called here with plain inputs — a composed draft, its
document and config, the dicts and sets ``NoteScreen`` would hold — and NO
``qapp`` fixture: the resolution precedence (C3, D5) with the read-back
digest, the learned-rule outcomes at Save, the correction entry point over
the practitioner's own line, the ownership test's laziness towards the
learning status, the ``_removed`` namespace pin and the NamedTuple boundary.
The widget-side order of mutation stays pinned in ``test_ui_screens.py``.
"""

from __future__ import annotations

import ast
import inspect
import re
from datetime import UTC, datetime

import pytest

from scribe_desktop.note import (
    CANONICAL_SECTION_KEYS,
    ConfirmationDecision,
    ExtractiveNoteProvider,
    NoteAssertion,
    NoteDraft,
    NoteProposal,
    NoteSectionKey,
    NoteSpan,
    ProposalEvidenceError,
    admissible_sections,
    compose_draft,
    finalise_note,
    manual_assertion_id,
    provider_assertion_id,
    reconstruct_span_text,
    text_digest,
    whole_utterance_assertion,
)
from scribe_desktop.note_config import (
    RULE_WORDING_MANY_CLAIMS,
    AutofillRule,
    LearnedRuleEntry,
    NoteConfig,
    PrefillSeedAssertion,
    PrefillTemplate,
    SectionMapping,
    TemplateProfile,
    TemplateTarget,
)
from scribe_desktop.transcription import (
    SPEAKER_1,
    SPEAKER_2,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
)
from scribe_desktop.ui import models, note_review
from scribe_desktop.ui.note_review import RuleReplacement

_SESSION_ID = "e" * 32
_NOW = datetime(2026, 9, 26, 9, 0, tzinfo=UTC)
_LEARNED_ICE = "learned-01J8ZK3Q9W4E5R6T7Y8U9I0O1P"
_LEARNED_DIAGNOSIS = "learned-01J8ZK3Q9W4E5R6T7Y8U9I0O2Q"
_TURNS: tuple[tuple[str, str], ...] = (
    ("My left knee is sore when I walk", SPEAKER_1),  # 0: the patient
    ("On examination the range of motion is limited", SPEAKER_2),
    ("The diagnosis is a mild knee sprain", SPEAKER_2),  # 2: routed, the clinician
    ("Please use an ice pack tonight", SPEAKER_2),  # 3: fires the ice-pack rule
    ("I walked to the shop this morning", SPEAKER_1),
    ("The knee felt steady on the stairs", SPEAKER_2),  # 5: unrouted, learnable
)
_DIAGNOSIS_INDEX = 2
_LEARNABLE_INDEX = 5
_DIAGNOSIS_TRIGGER = "diagnosis is a mild knee sprain"


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


def _document() -> TranscriptDocument:
    return TranscriptDocument(
        session_id=_SESSION_ID,
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


def _config(*rules: AutofillRule) -> NoteConfig:
    """One template profile, the given autofill rules (default: the learned
    ice-pack rule, which PROPOSES — no sidecar record) and a knee prefill
    seed, which arrives PRE-FILLED (hand-authored, D5)."""
    profile = TemplateProfile(
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
    return NoteConfig(
        template_profiles=(profile,),
        autofill_rules=rules
        or (
            AutofillRule(
                rule_id=_LEARNED_ICE,
                section_key="advice_home_exercise",
                trigger_phrase="ice pack",
                expansion=("Ice pack use explained.",),
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


def _compose(
    config: NoteConfig, *, learned_rules: dict[str, LearnedRuleEntry] | None = None
) -> tuple[NoteDraft, TranscriptDocument]:
    document = _document()
    draft = compose_draft(
        document,
        config,
        ExtractiveNoteProvider(),
        clinician_speaker=SPEAKER_2,
        learned_rules=learned_rules,
        decided_at=_NOW,
    )
    return draft, document


def _proposal(draft: NoteDraft, provenance: str) -> NoteProposal:
    [proposal] = [p for p in draft.note_proposals if p.provenance == provenance]
    return proposal


def _section_of(draft: NoteDraft, assertion_id: str) -> NoteSectionKey:
    for section in draft.note_sections:
        for assertion in section.note_assertions:
            if assertion.assertion_id == assertion_id:
                return section.section_key
    raise AssertionError(f"the fixture no longer routes {assertion_id}")


def _typed(
    draft: NoteDraft,
    wording: str,
    *,
    replaces: str,
    section_key: NoteSectionKey | None = None,
) -> NoteAssertion:
    """A typed line as `NoteScreen._typed_assertion` builds it, in the
    section of the provider line it replaces unless one is given."""
    return NoteAssertion(
        assertion_id="t0001",
        section_key=section_key if section_key is not None else _section_of(draft, replaces),
        note_span=NoteSpan(span_text=wording, provenance="clinician"),
        shown_text_digest=text_digest(wording),
        config_digest=draft.config_digest,
        confirmation=ConfirmationDecision(
            proposal_id="t0001", note_confirmation="confirmed", decided_at=_NOW
        ),
        replaces=replaces,
    )


def _added(document: TranscriptDocument, segment_index: int) -> NoteAssertion:
    """A whole utterance added as the widget's `add_line` builds it."""
    segment = document.transcript_segments[segment_index]
    key = admissible_sections(
        CANONICAL_SECTION_KEYS,
        speaker=segment.speaker,
        clinician_speaker=SPEAKER_2,
        text=reconstruct_span_text(segment.transcript_words),
    )[0]
    assertion = whole_utterance_assertion(
        manual_assertion_id(segment_index),
        key,
        segment_index=segment_index,
        speaker=segment.speaker,
        words=segment.transcript_words,
    )
    assert assertion is not None
    return assertion


class _Status:
    """A learning-status reader that records every call."""

    def __init__(self, enabled: bool, reason: str | None = None) -> None:
        self.calls = 0
        self._status = models.LearningStatus(enabled, reason)

    def __call__(self) -> models.LearningStatus:
        self.calls += 1
        return self._status


# --- (1) + (2): the resolution precedence and the read-back digest ------------


class TestResolutions:
    def test_the_precedence_table(self) -> None:
        config = _config()
        draft, document = _compose(config)
        ice, knee = _proposal(draft, "autofill"), _proposal(draft, "prefill")
        [minted] = draft.config_decisions
        assert minted.proposal_id == knee.proposal_id  # the prefill seed arrives pre-filled
        rendered = {ice.proposal_id: ice.note_excerpt}  # the row, read back faithfully
        ice_digest, knee_digest = text_digest(ice.note_excerpt), text_digest(knee.note_excerpt)
        as_minted = ("config", "confirmed", minted.shown_text_digest)
        # (clicked, removed, typed over) -> proposal id -> (by, decision, digest)
        cases: list[
            tuple[
                dict[str, note_review.ProposalDecision],
                set[str],
                set[str],
                dict[str, tuple[str, str, str]],
            ]
        ] = [
            # Nothing done: the config decision passes unchanged; the row is pending.
            ({}, set(), set(), {knee.proposal_id: as_minted}),
            # A click stands.
            (
                {ice.proposal_id: "confirmed"},
                set(),
                set(),
                {
                    ice.proposal_id: ("clinician", "confirmed", ice_digest),
                    knee.proposal_id: as_minted,
                },
            ),
            # Typed over beats a click: the clinician's decline.
            (
                {ice.proposal_id: "confirmed"},
                set(),
                {ice.proposal_id},
                {
                    ice.proposal_id: ("clinician", "declined", ice_digest),
                    knee.proposal_id: as_minted,
                },
            ),
            # Removed beats a click, and a Removed PRE-FILLED line declines with
            # the digest of its own excerpt (it has no row to read back).
            (
                {ice.proposal_id: "confirmed"},
                {ice.proposal_id, knee.proposal_id},
                set(),
                {
                    ice.proposal_id: ("clinician", "declined", ice_digest),
                    knee.proposal_id: ("clinician", "declined", knee_digest),
                },
            ),
            # A clinician's decision beats a config-minted one.
            (
                {knee.proposal_id: "declined"},
                set(),
                set(),
                {knee.proposal_id: ("clinician", "declined", knee_digest)},
            ),
        ]
        for clicked, removed, edited, expected in cases:
            built = note_review.build_resolutions(
                draft,
                resolutions=clicked,
                removed=removed,
                edited_proposals=edited,
                rendered_excerpt=rendered,
                now=_NOW,
            )
            table = {
                r.proposal_id: (
                    r.confirmation.decided_by,
                    r.confirmation.note_confirmation,
                    r.shown_text_digest,
                )
                for r in built
            }
            assert table == expected, (clicked, removed, edited)
            finalise_note(draft, built, document, config)  # the evidence is accepted

    def test_the_digest_is_the_rendered_texts_and_a_mismatch_is_refused(self) -> None:
        draft, document = _compose(_config())
        ice = _proposal(draft, "autofill")
        misrendered = ice.note_excerpt + " (edited by a rendering bug)"
        built = note_review.build_resolutions(
            draft,
            resolutions={ice.proposal_id: "confirmed"},
            removed=frozenset(),
            edited_proposals=frozenset(),
            rendered_excerpt={ice.proposal_id: misrendered},
            now=_NOW,
        )
        [row] = [r for r in built if r.confirmation.proposal_id == ice.proposal_id]
        assert row.shown_text_digest == text_digest(misrendered)
        assert row.shown_text_digest != ice.shown_text_digest
        with pytest.raises(ProposalEvidenceError, match="shown-text digest"):
            finalise_note(draft, built, document, _config())


# --- (3): learned-rule outcomes at Save ---------------------------------------


class TestLearnedRuleOutcomes:
    def test_removed_wins_across_two_proposals_of_one_rule(self) -> None:
        rule = AutofillRule(
            rule_id=_LEARNED_ICE,
            section_key="advice_home_exercise",
            trigger_phrase="ice pack",
            expansion=("Ice pack use explained.", "Advice given to rest."),
        )
        draft, _document = _compose(_config(rule))
        first, second = (p.proposal_id for p in draft.note_proposals if p.rule_id == _LEARNED_ICE)
        both_ways: tuple[dict[str, note_review.ProposalDecision], ...] = (
            {first: "confirmed", second: "declined"},
            {first: "declined", second: "confirmed"},
        )
        for clicked in both_ways:
            assert note_review.learned_rule_outcomes(
                draft,
                resolutions=clicked,
                removed=frozenset(),
                edited_proposals=frozenset(),
            ) == {_LEARNED_ICE: "removed"}
        # Removed or typed over counts as removed, whatever the other line says.
        for removed, edited in ((frozenset({second}), frozenset()), (frozenset(), {second})):
            assert note_review.learned_rule_outcomes(
                draft,
                resolutions={first: "confirmed"},
                removed=removed,
                edited_proposals=edited,
            ) == {_LEARNED_ICE: "removed"}
        assert note_review.learned_rule_outcomes(
            draft,
            resolutions={first: "confirmed", second: "confirmed"},
            removed=frozenset(),
            edited_proposals=frozenset(),
        ) == {_LEARNED_ICE: "confirmed"}

    def test_an_unchanged_pre_filled_learned_line_is_confirmed(self) -> None:
        entry = LearnedRuleEntry(learned_at=_NOW, confirmations=3, auto_confirmed=True)
        draft, _document = _compose(_config(), learned_rules={_LEARNED_ICE: entry})
        ice = _proposal(draft, "autofill")
        assert ice.proposal_id in note_review.prefilled_ids(draft)
        outcomes = note_review.learned_rule_outcomes(
            draft, resolutions={}, removed=frozenset(), edited_proposals=frozenset()
        )
        assert outcomes == {_LEARNED_ICE: "confirmed"}

    def test_an_unclicked_proposal_says_nothing(self) -> None:
        draft, _document = _compose(_config())
        assert note_review.prefilled_ids(draft) == {_proposal(draft, "prefill").proposal_id}
        assert (
            note_review.learned_rule_outcomes(
                draft, resolutions={}, removed=frozenset(), edited_proposals=frozenset()
            )
            == {}
        )

    def test_rule_ids_that_are_not_learned_are_ignored(self) -> None:
        hand = AutofillRule(
            rule_id="rule-ice",
            section_key="advice_home_exercise",
            trigger_phrase="ice pack",
            expansion=("Ice pack use explained.",),
        )
        draft, _document = _compose(_config(hand))
        ice, knee = _proposal(draft, "autofill"), _proposal(draft, "prefill")
        # Both pre-filled (hand-authored, D5); clicked, Removed or untouched,
        # neither the hand rule nor the prefill template is a learned rule.
        for removed in (frozenset(), frozenset({ice.proposal_id, knee.proposal_id})):
            assert (
                note_review.learned_rule_outcomes(
                    draft,
                    resolutions={ice.proposal_id: "confirmed"},
                    removed=removed,
                    edited_proposals=frozenset(),
                )
                == {}
            )


# --- (4) + (5): what an edit teaches, and when the status is read ------------


class TestShorthandLearning:
    def _learned_diagnosis_config(self) -> NoteConfig:
        """A config holding a LEARNED rule whose trigger is the diagnosis
        line's tail — so a typed edit over that line is correction entry
        point 2 (the practitioner's own line matching a learned trigger)."""
        return _config(
            AutofillRule(
                rule_id=_LEARNED_DIAGNOSIS,
                section_key="advice_home_exercise",
                trigger_phrase=_DIAGNOSIS_TRIGGER,
                expansion=("Mild knee sprain.",),
            )
        )

    def _consider(
        self, config: NoteConfig, wording: str, status: _Status
    ) -> note_review.RuleLearningVerdict:
        draft, document = _compose(config)
        target = provider_assertion_id(_DIAGNOSIS_INDEX)
        return note_review.consider_rule_learning(
            _typed(draft, wording, replaces=target),
            draft=draft,
            document=document,
            config=config,
            segment_index=_DIAGNOSIS_INDEX,
            learning_status=status,
        )

    def test_a_correction_over_the_practitioners_line_is_validated_at_the_edit(self) -> None:
        config = self._learned_diagnosis_config()
        # The control: a valid wording reaches entry point 2 and replaces in place.
        valid = self._consider(config, "Mild knee sprain", _Status(True))
        assert valid.rule is None
        assert valid.replacement == RuleReplacement(_LEARNED_DIAGNOSIS, "Mild knee sprain")
        assert valid.messages == (
            f"Will update the learned shorthand for '{_DIAGNOSIS_TRIGGER}' to your wording "
            "when you press Save note on this tab.",
        )
        # A dash wording (the Phase H smoke case): nothing queued, the plain reason.
        dash = self._consider(config, "Mild knee sprain - rest advised", _Status(True))
        assert (dash.rule, dash.replacement) == (None, None)
        assert dash.messages == (f"Not learned: {RULE_WORDING_MANY_CLAIMS}.",)
        assert not any("Will update" in message for message in dash.messages)

    def test_a_new_trigger_is_queued_as_a_rule(self) -> None:
        draft, _document = _compose(_config())
        verdict = self._consider(_config(), "Mild knee sprain", _Status(True))
        section = _section_of(draft, provider_assertion_id(_DIAGNOSIS_INDEX))
        assert verdict.replacement is None
        assert verdict.rule is not None
        assert (verdict.rule.trigger_phrase, verdict.rule.typed_wording) == (
            _DIAGNOSIS_TRIGGER,
            "Mild knee sprain",
        )
        assert verdict.messages == (
            f"Will learn shorthand: '{_DIAGNOSIS_TRIGGER}' -> 'Mild knee sprain' for "
            f"{models.section_title(section)} when you press Save note on this tab.",
        )

    def test_another_speakers_line_never_reads_the_status(self) -> None:
        # The patient's line, added and then typed over (the widget's
        # `edit_line` over a manual line: its segment is the one it quotes).
        config = _config()
        draft, document = _compose(config)
        patient = _added(document, 0)
        status = _Status(True)
        verdict = note_review.consider_rule_learning(
            _typed(
                draft,
                "Knee sore walking",
                replaces=patient.assertion_id,
                section_key=patient.section_key,
            ),
            draft=draft,
            document=document,
            config=config,
            segment_index=0,
            learning_status=status,
        )
        assert status.calls == 0
        assert (verdict.rule, verdict.replacement) == (None, None)
        assert verdict.messages == (models.LEARNING_NOT_ATTRIBUTED_NOTE,)

    def test_learning_off_reads_the_status_once_and_queues_nothing(self) -> None:
        status = _Status(False, models.LEARNING_OPTED_OUT_HINT)
        verdict = self._consider(_config(), "Mild knee sprain", status)
        assert status.calls == 1
        assert (verdict.rule, verdict.replacement) == (None, None)
        assert verdict.messages == (models.LEARNING_OPTED_OUT_HINT,)


class TestPhraseLearning:
    def test_the_practitioners_line_is_queued(self) -> None:
        config = _config()
        draft, document = _compose(config)
        added = _added(document, _LEARNABLE_INDEX)
        status = _Status(True)
        verdict = note_review.consider_learning(
            added, draft=draft, document=document, config=config, learning_status=status
        )
        assert status.calls == 1
        assert verdict.queued == (added.section_key, "the knee felt steady")
        [message] = verdict.messages
        assert message.startswith(
            f"Will learn 'the knee felt steady' for {models.section_title(added.section_key)} "
            "when you press Save note on this tab."
        )

    def test_another_speakers_line_never_reads_the_status(self) -> None:
        config = _config()
        draft, document = _compose(config)
        status = _Status(True)
        verdict = note_review.consider_learning(
            _added(document, 4),  # the patient's "I walked to the shop this morning"
            draft=draft,
            document=document,
            config=config,
            learning_status=status,
        )
        assert status.calls == 0
        assert verdict.queued is None
        assert verdict.messages == (models.LEARNING_NOT_ATTRIBUTED_NOTE,)

    def test_learning_off_reads_the_status_once_and_queues_nothing(self) -> None:
        config = _config()
        draft, document = _compose(config)
        status = _Status(False, models.LEARNING_OPTED_OUT_HINT)
        verdict = note_review.consider_learning(
            _added(document, _LEARNABLE_INDEX),
            draft=draft,
            document=document,
            config=config,
            learning_status=status,
        )
        assert status.calls == 1
        assert verdict.queued is None
        assert verdict.messages == (models.LEARNING_OPTED_OUT_HINT,)


# --- (6) + (7): the boundary types -------------------------------------------

_ASSERTION_ID = re.compile(r"[xmt][0-9]{4,}")
_PROPOSAL_ID = re.compile(r"(autofill|prefill)-[0-9a-f]{24}")


def test_the_removed_set_namespaces_cannot_collide() -> None:
    """`NoteScreen._removed` holds assertion ids AND pre-filled proposal ids
    in one set (practitioner decision 2026-09-26). An assertion id starts
    with x / m / t, a proposal id with a / p — no id is both."""
    draft, document = _compose(_config())
    segments = range(len(document.transcript_segments))
    assertion_ids = {
        assertion.assertion_id
        for section in draft.note_sections
        for assertion in section.note_assertions
    }
    assertion_ids |= {provider_assertion_id(index) for index in segments}
    assertion_ids |= {manual_assertion_id(index) for index in segments}
    # `NoteScreen._next_typed_id`'s scheme, first and a late one.
    assertion_ids |= {f"t{n:04d}" for n in (1, 12_345)}
    proposal_ids = {proposal.proposal_id for proposal in draft.note_proposals}
    assert {p.provenance for p in draft.note_proposals} == {"autofill", "prefill"}
    assert all(_ASSERTION_ID.fullmatch(i) for i in assertion_ids), assertion_ids
    assert all(_PROPOSAL_ID.fullmatch(i) for i in proposal_ids), proposal_ids
    assert {i[0] for i in assertion_ids}.isdisjoint({i[0] for i in proposal_ids})
    assert assertion_ids.isdisjoint(proposal_ids)


def test_a_rule_replacement_equals_the_old_tuple() -> None:
    replacement = RuleReplacement(_LEARNED_ICE, "Ice applied")
    assert replacement == (_LEARNED_ICE, "Ice applied")
    assert (replacement.rule_id, replacement.wording) == (_LEARNED_ICE, "Ice applied")
    rule_id, wording = replacement
    assert (rule_id, wording) == (_LEARNED_ICE, "Ice applied")


def test_the_module_imports_neither_qt_nor_logging() -> None:
    """C9 and the Qt-free contract, on the module's own imports."""
    tree = ast.parse(inspect.getsource(note_review))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    assert imported, "the walk must have found the module's imports"
    assert not any(name.split(".")[0] in {"PySide6", "logging"} for name in imported)
