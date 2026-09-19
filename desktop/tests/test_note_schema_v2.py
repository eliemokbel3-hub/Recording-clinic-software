"""Note-learning-and-styles plan, Phase 0 Task 0.2: note schema v2.

What is pinned here, per the task's Done-when:
- ``ConfirmationDecision.decided_by`` / ``config_digest`` /
  ``confirmation_count`` (D4, D5): a ``config`` decision without its digest is
  unrepresentable; a clinician decision carries neither field; a config
  decision's digest is pinned to the assertion it decides.
- The ``clinician`` provenance (D4): typed text with no coordinates, no
  proposal id, the same two digests every authored line carries, a decision
  that names the line itself, and an optional ``replaces``.
- ``GeneratedNote`` v2: ``schema_version`` 2 by default, ``style`` and
  ``style_renderings`` with v1-shaped defaults; a v1 ``note.enc`` fixture
  READS under v2 and a note labelled v1 cannot carry v2 content.
- The parametrised BRANCH test: every provenance branch the plan's Key
  Findings list handles a typed line explicitly — ``note.py`` (span,
  assertion, draft, compose, finalise), ``note_check.py`` (Checks 1-4),
  ``session_store.write_note`` and ``ui/models.py`` (label, editable rows).
  The two ``ui/note.py`` branches need a Qt screen and are pinned in
  ``test_ui_screens.py``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import pytest
from pydantic import ValidationError

from scribe_desktop import note_check as note_check_module
from scribe_desktop.note import (
    CANONICAL_SECTION_KEYS,
    DRAFT_BASE_PROVENANCES,
    NOTE_SCHEMA_VERSION,
    SECTION_INDEX,
    ConfirmationDecision,
    GeneratedNote,
    GeneratedSection,
    NoteAssertion,
    NoteDraft,
    NoteProposal,
    NoteSectionKey,
    NoteSpan,
    ProposalEvidenceError,
    ProposalResolution,
    ProviderOutputError,
    SourceCoords,
    StyleRendering,
    compose_draft,
    digest_bytes,
    finalise_note,
    text_digest,
    transcript_digest,
)
from scribe_desktop.note_check import (
    contradiction_warnings,
    omission_warnings,
    provenance_warnings,
    reconstruction_warnings,
)
from scribe_desktop.note_config import (
    NoteConfig,
    SectionMapping,
    TemplateProfile,
    TemplateTarget,
)
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import NoteWriteRefusedError, read_note, write_note
from scribe_desktop.transcription import (
    SPEAKER_1,
    SPEAKER_2,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
    write_transcript,
)
from scribe_desktop.ui import models

SESSION_ID = "e" * 32
_NOW = datetime(2026, 9, 19, 8, 0, tzinfo=UTC)
_OTHER_DIGEST = digest_bytes(b"another config")

# Segment 0: the clinician's examination (quoted into a clinician-owned
# section). Segment 1: the patient's symptom (quoted; the contradiction
# anchor). Segment 2: a clinician line carrying a number that NO assertion
# quotes — Check 4's omission candidate.
CLINICIAN_EXAM = "On examination the range of motion is limited"
PATIENT_SYMPTOM = "the numbness is worse at night"
CLINICIAN_UNQUOTED = "Review again in 2 weeks"
TYPED_TEXT = "Cervical HVLA performed"


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


_CONFIG = NoteConfig(template_profiles=(_profile(),), autofill_rules=(), prefill_templates=())
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


def _document() -> TranscriptDocument:
    turns = (
        (CLINICIAN_EXAM, SPEAKER_2),
        (PATIENT_SYMPTOM, SPEAKER_1),
        (CLINICIAN_UNQUOTED, SPEAKER_2),
    )
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
            for index, (text, speaker) in enumerate(turns)
        ),
    )


def _quoted(
    aid: str, section: NoteSectionKey, segment: int, text: str, speaker: str
) -> NoteAssertion:
    return NoteAssertion(
        assertion_id=aid,
        section_key=section,
        note_span=NoteSpan(
            span_text=text,
            provenance="transcript",
            source_coords=SourceCoords(segment, 0, len(text.split()) - 1),
        ),
        speaker=speaker,
    )


def _decision(aid: str, *, decided_at: datetime = _NOW) -> ConfirmationDecision:
    return ConfirmationDecision(
        proposal_id=aid, note_confirmation="confirmed", decided_at=decided_at
    )


def _typed(
    text: str = TYPED_TEXT,
    *,
    section: NoteSectionKey = "assessment",
    aid: str = "typed-1",
    config_digest: str = CONFIG_DIGEST,
    shown_text_digest: str | None = None,
    replaces: str | None = "q0",
) -> NoteAssertion:
    """A typed ``clinician`` line with complete evidence: the two digests and
    the decision that names the line itself (D4)."""
    return NoteAssertion(
        assertion_id=aid,
        section_key=section,
        note_span=NoteSpan(span_text=text, provenance="clinician"),
        shown_text_digest=(
            shown_text_digest if shown_text_digest is not None else text_digest(text)
        ),
        config_digest=config_digest,
        confirmation=_decision(aid),
        replaces=replaces,
    )


def _sections(assertions: tuple[NoteAssertion, ...]) -> tuple[GeneratedSection, ...]:
    grouped: dict[NoteSectionKey, list[NoteAssertion]] = {}
    for assertion in assertions:
        grouped.setdefault(assertion.section_key, []).append(assertion)
    return tuple(
        GeneratedSection(section_key=key, note_assertions=tuple(grouped[key]))
        for key in sorted(grouped, key=lambda key: SECTION_INDEX[key])
    )


def _base() -> tuple[NoteAssertion, NoteAssertion]:
    return (
        _quoted("q0", "objective_examination", 0, CLINICIAN_EXAM, SPEAKER_2),
        _quoted("q1", "presenting_complaint", 1, PATIENT_SYMPTOM, SPEAKER_1),
    )


def _draft(
    typed: NoteAssertion | None,
    *,
    clinician_speaker: str | None = SPEAKER_2,
    proposals: tuple[NoteProposal, ...] = (),
    config_decisions: tuple[ProposalResolution, ...] = (),
) -> NoteDraft:
    """The WORKING draft the Note tab finalises: the provider's quoted lines
    plus the typed line as a base-section addition (``ui.models.working_draft``
    is the shipping builder; ``NoteDraft`` is what it validates through)."""
    assertions = _base() + ((typed,) if typed is not None else ())
    return NoteDraft(
        session_id=SESSION_ID,
        template_profile_id="clinic-a",
        provider_name="extractive-v1",
        clinician_speaker=clinician_speaker,
        transcript_digest=transcript_digest(_document()),
        config_digest=CONFIG_DIGEST,
        note_sections=_sections(assertions),
        note_proposals=proposals,
        config_decisions=config_decisions,
    )


def _note(typed: NoteAssertion | None = None, **overrides: Any) -> GeneratedNote:
    """A finalised note holding the base lines plus ``typed``; ``overrides``
    are applied and the note RE-VALIDATED (``model_copy`` alone would skip
    the validators the override tests exist to exercise)."""
    draft = _draft(typed)
    note = finalise_note(draft, [], _document(), _CONFIG, created_at=_NOW)
    if not overrides:
        return note
    return GeneratedNote.model_validate(note.model_copy(update=overrides).model_dump())


def _hand_built_note(
    typed: NoteAssertion, *, config_digest: str = CONFIG_DIGEST
) -> GeneratedNote:
    """A note assembled directly (the ``write_note`` defence-in-depth path:
    construction checks evidence PRESENCE, ``write_note`` the relations)."""
    return GeneratedNote(
        session_id=SESSION_ID,
        created_at=_NOW,
        template_profile_id="clinic-a",
        provider_name="extractive-v1",
        clinician_speaker=SPEAKER_2,
        transcript_digest=transcript_digest(_document()),
        config_digest=config_digest,
        note_sections=_sections(_base() + (typed,)),
    )


def _codes(warnings: tuple[Any, ...]) -> list[str]:
    return [w.note_warning_code for w in warnings]


def _ids_of(warnings: tuple[Any, ...], code: str) -> set[str | None]:
    return {w.assertion_id for w in warnings if w.note_warning_code == code}


# ---------------------------------------------------------------------------
# ConfirmationDecision v2 (D4 / D5)
# ---------------------------------------------------------------------------


class TestConfirmationDecisionV2:
    def test_defaults_are_the_v1_shape(self) -> None:
        decision = _decision("p1")
        assert decision.decided_by == "clinician"
        assert decision.config_digest is None
        assert decision.confirmation_count is None

    def test_a_config_decision_without_a_digest_is_unrepresentable(self) -> None:
        with pytest.raises(ValidationError, match="requires a config_digest"):
            ConfirmationDecision(
                proposal_id="p1",
                note_confirmation="confirmed",
                decided_at=_NOW,
                decided_by="config",
            )
        with pytest.raises(ValidationError, match="requires a config_digest"):
            ConfirmationDecision(
                proposal_id="p1",
                note_confirmation="confirmed",
                decided_at=_NOW,
                decided_by="config",
                config_digest="not-a-digest",
            )

    def test_a_config_decision_carries_its_digest_and_may_carry_a_count(self) -> None:
        decision = ConfirmationDecision(
            proposal_id="p1",
            note_confirmation="confirmed",
            decided_at=_NOW,
            decided_by="config",
            config_digest=CONFIG_DIGEST,
            confirmation_count=3,
        )
        assert decision.config_digest == CONFIG_DIGEST
        assert decision.confirmation_count == 3
        with pytest.raises(ValidationError):
            ConfirmationDecision(
                proposal_id="p1",
                note_confirmation="confirmed",
                decided_at=_NOW,
                decided_by="config",
                config_digest=CONFIG_DIGEST,
                confirmation_count=-1,
            )

    def test_a_clinician_decision_carries_neither_config_field(self) -> None:
        for extra in ({"config_digest": CONFIG_DIGEST}, {"confirmation_count": 1}):
            with pytest.raises(ValidationError, match="clinician decision carries no"):
                ConfirmationDecision(
                    proposal_id="p1",
                    note_confirmation="confirmed",
                    decided_at=_NOW,
                    **extra,
                )

    def test_a_config_decision_is_pinned_to_the_assertion_it_decides(self) -> None:
        """D5: the digest on the decision must be the assertion's own —
        evidence about one config cannot back a line minted under another."""
        text = "Ice pack use explained."

        def assertion(decision_digest: str) -> NoteAssertion:
            return NoteAssertion(
                assertion_id="autofill-1",
                section_key="advice_home_exercise",
                note_span=NoteSpan(span_text=text, provenance="autofill"),
                proposal_id="autofill-1",
                shown_text_digest=text_digest(text),
                config_digest=CONFIG_DIGEST,
                confirmation=ConfirmationDecision(
                    proposal_id="autofill-1",
                    note_confirmation="confirmed",
                    decided_at=_NOW,
                    decided_by="config",
                    config_digest=decision_digest,
                    confirmation_count=3,
                ),
            )

        assert assertion(CONFIG_DIGEST).confirmation is not None
        with pytest.raises(ValidationError, match="config decision's config_digest"):
            assertion(_OTHER_DIGEST)

    def test_a_config_decided_resolution_passes_finalise_note(self) -> None:
        """The task's Done-when: a ``decided_by="config"`` line flows through
        the resolution loop into the note carrying its decision and count.
        Since Phase 2 the decision must be one the DRAFT carries (minted at
        the emitter): a draft cannot carry one under another digest, and a
        resolution the draft does not carry is refused."""
        proposal = NoteProposal(
            proposal_id="autofill-1",
            section_key="advice_home_exercise",
            provenance="autofill",
            note_excerpt="Ice pack use explained.",
            rule_id="rule-ice",
            config_digest=CONFIG_DIGEST,
        )

        def resolution(decision_digest: str, decided_at: datetime = _NOW) -> ProposalResolution:
            return ProposalResolution(
                shown_text_digest=proposal.shown_text_digest,
                confirmation=ConfirmationDecision(
                    proposal_id=proposal.proposal_id,
                    note_confirmation="confirmed",
                    decided_at=decided_at,
                    decided_by="config",
                    config_digest=decision_digest,
                    confirmation_count=3,
                ),
            )

        minted = resolution(CONFIG_DIGEST)
        draft = _draft(None, proposals=(proposal,), config_decisions=(minted,))
        note = finalise_note(draft, [minted], _document(), _CONFIG)
        [landed] = [
            a
            for s in note.note_sections
            for a in s.note_assertions
            if a.assertion_id == "autofill-1"
        ]
        assert landed.confirmation is not None
        assert landed.confirmation.decided_by == "config"
        assert landed.confirmation.confirmation_count == 3
        assert note.schema_version == 2
        # The hand-made proposal id resolves to no rule of this config, so
        # Check 3 fails closed — a warning riding the note, not a refusal.
        assert "autofill_trigger_absent" in _codes(note.blocking_warnings())
        with pytest.raises(ValidationError, match="draft's own config_digest"):
            _draft(None, proposals=(proposal,), config_decisions=(resolution(_OTHER_DIGEST),))
        not_minted = resolution(CONFIG_DIGEST, decided_at=_NOW.replace(minute=1))
        with pytest.raises(ProposalEvidenceError, match="not the one the emitter minted"):
            finalise_note(draft, [not_minted], _document(), _CONFIG)


# ---------------------------------------------------------------------------
# The clinician provenance (D4)
# ---------------------------------------------------------------------------


class TestClinicianProvenance:
    def test_a_typed_span_carries_no_coordinates(self) -> None:
        assert NoteSpan(span_text=TYPED_TEXT, provenance="clinician").source_coords is None
        with pytest.raises(ValidationError, match="must not carry source_coords"):
            NoteSpan(
                span_text=TYPED_TEXT, provenance="clinician", source_coords=SourceCoords(0, 0, 1)
            )

    def test_complete_evidence_is_accepted(self) -> None:
        typed = _typed()
        assert typed.provenance == "clinician"
        assert typed.proposal_id is None
        assert typed.replaces == "q0"
        assert typed.confirmation is not None
        assert typed.confirmation.proposal_id == typed.assertion_id
        assert _typed(replaces=None).replaces is None

    def test_nothing_proposed_it(self) -> None:
        with pytest.raises(ValidationError, match="nothing proposed it"):
            NoteAssertion(
                assertion_id="typed-1",
                section_key="assessment",
                note_span=NoteSpan(span_text=TYPED_TEXT, provenance="clinician"),
                proposal_id="p1",
                shown_text_digest=text_digest(TYPED_TEXT),
                config_digest=CONFIG_DIGEST,
                confirmation=_decision("typed-1"),
            )

    @pytest.mark.parametrize("missing", ["shown_text_digest", "config_digest", "confirmation"])
    def test_each_piece_of_evidence_is_required(self, missing: str) -> None:
        fields: dict[str, Any] = {
            "assertion_id": "typed-1",
            "section_key": "assessment",
            "note_span": NoteSpan(span_text=TYPED_TEXT, provenance="clinician"),
            "shown_text_digest": text_digest(TYPED_TEXT),
            "config_digest": CONFIG_DIGEST,
            "confirmation": _decision("typed-1"),
        }
        del fields[missing]
        with pytest.raises(ValidationError, match="clinician assertion requires"):
            NoteAssertion(**fields)

    def test_the_decision_names_the_line_itself(self) -> None:
        with pytest.raises(ValidationError, match="must name the assertion itself"):
            NoteAssertion(
                assertion_id="typed-1",
                section_key="assessment",
                note_span=NoteSpan(span_text=TYPED_TEXT, provenance="clinician"),
                shown_text_digest=text_digest(TYPED_TEXT),
                config_digest=CONFIG_DIGEST,
                confirmation=_decision("someone-else"),
            )

    def test_a_typed_line_is_never_config_decided(self) -> None:
        with pytest.raises(ValidationError, match="never by config"):
            NoteAssertion(
                assertion_id="typed-1",
                section_key="assessment",
                note_span=NoteSpan(span_text=TYPED_TEXT, provenance="clinician"),
                shown_text_digest=text_digest(TYPED_TEXT),
                config_digest=CONFIG_DIGEST,
                confirmation=ConfirmationDecision(
                    proposal_id="typed-1",
                    note_confirmation="confirmed",
                    decided_at=_NOW,
                    decided_by="config",
                    config_digest=CONFIG_DIGEST,
                ),
            )

    def test_a_declined_decision_cannot_become_a_typed_line(self) -> None:
        with pytest.raises(ValidationError, match="declined"):
            NoteAssertion(
                assertion_id="typed-1",
                section_key="assessment",
                note_span=NoteSpan(span_text=TYPED_TEXT, provenance="clinician"),
                shown_text_digest=text_digest(TYPED_TEXT),
                config_digest=CONFIG_DIGEST,
                confirmation=ConfirmationDecision(
                    proposal_id="typed-1", note_confirmation="declined", decided_at=_NOW
                ),
            )

    def test_an_assertion_cannot_replace_itself(self) -> None:
        with pytest.raises(ValidationError, match="cannot replace itself"):
            _typed(replaces="typed-1")

    def test_only_a_typed_line_replaces_anything(self) -> None:
        with pytest.raises(ValidationError, match="replaces nothing"):
            NoteAssertion(
                assertion_id="q0",
                section_key="objective_examination",
                note_span=NoteSpan(
                    span_text="left knee",
                    provenance="transcript",
                    source_coords=SourceCoords(0, 0, 1),
                ),
                replaces="q1",
            )
        text = "Ice pack use explained."
        with pytest.raises(ValidationError, match="replaces nothing"):
            NoteAssertion(
                assertion_id="autofill-1",
                section_key="advice_home_exercise",
                note_span=NoteSpan(span_text=text, provenance="autofill"),
                proposal_id="autofill-1",
                shown_text_digest=text_digest(text),
                config_digest=CONFIG_DIGEST,
                confirmation=_decision("autofill-1"),
                replaces="q1",
            )


# ---------------------------------------------------------------------------
# GeneratedNote v2: style, renderings, the version label
# ---------------------------------------------------------------------------


class TestNoteSchemaV2:
    def test_a_finalised_note_is_version_2_with_v1_shaped_defaults(self) -> None:
        note = _note()
        assert NOTE_SCHEMA_VERSION == 2
        assert note.schema_version == 2
        assert note.style == "verbatim"
        assert note.style_renderings == ()
        assert GeneratedNote.from_bytes(note.to_bytes()) == note

    def test_an_unknown_version_is_refused(self) -> None:
        payload = json.loads(_note().to_bytes())
        payload["schema_version"] = 3
        with pytest.raises(ValidationError):
            GeneratedNote.from_bytes(json.dumps(payload).encode("utf-8"))

    def test_a_passed_rendering_needs_prose_and_a_failed_one_keeps_none(self) -> None:
        rendering = StyleRendering(
            section_key="assessment",
            prose_text="The cervical spine was treated with HVLA.",
            input_digest=text_digest(TYPED_TEXT),
            verdict="passed",
        )
        assert rendering.verdict == "passed"
        with pytest.raises(ValidationError, match="must carry prose"):
            StyleRendering(
                section_key="assessment",
                prose_text="  ",
                input_digest=text_digest(TYPED_TEXT),
                verdict="passed",
            )
        failed = StyleRendering(
            section_key="assessment",
            prose_text="",
            input_digest=text_digest(TYPED_TEXT),
            verdict="failed",
        )
        assert failed.prose_text == ""
        with pytest.raises(ValidationError, match="refused text is not kept"):
            StyleRendering(
                section_key="assessment",
                prose_text="with paralysis",
                input_digest=text_digest(TYPED_TEXT),
                verdict="failed",
            )
        with pytest.raises(ValidationError, match="input_digest must match"):
            StyleRendering(
                section_key="assessment",
                prose_text="x",
                input_digest="nope",
                verdict="passed",
            )

    def test_renderings_are_bound_to_populated_sections_in_canonical_order(self) -> None:
        def rendering(section: NoteSectionKey) -> StyleRendering:
            return StyleRendering(
                section_key=section,
                prose_text="prose",
                input_digest=text_digest("inputs"),
                verdict="passed",
            )

        note = _note(_typed(), style="narrative", style_renderings=(rendering("assessment"),))
        assert note.style == "narrative"
        assert GeneratedNote.from_bytes(note.to_bytes()) == note
        with pytest.raises(ValidationError, match="does not populate"):
            _note(_typed(), style_renderings=(rendering("diagnosis"),))
        with pytest.raises(ValidationError, match="canonical order"):
            _note(
                _typed(),
                style_renderings=(rendering("assessment"), rendering("objective_examination")),
            )
        with pytest.raises(ValidationError, match="canonical order"):
            _note(_typed(), style_renderings=(rendering("assessment"), rendering("assessment")))

    @pytest.mark.parametrize(
        "v2_content",
        [
            pytest.param({"style": "clean"}, id="style"),
            pytest.param(
                {
                    "style_renderings": (
                        StyleRendering(
                            section_key="objective_examination",
                            prose_text="prose",
                            input_digest=text_digest("inputs"),
                            verdict="passed",
                        ),
                    )
                },
                id="rendering",
            ),
        ],
    )
    def test_a_note_labelled_v1_cannot_carry_v2_content(
        self, v2_content: dict[str, Any]
    ) -> None:
        with pytest.raises(ValidationError, match="schema-version-1 note cannot carry"):
            _note(schema_version=1, **v2_content)
        with pytest.raises(ValidationError, match="schema-version-1 note cannot carry"):
            _note(_typed(), schema_version=1)


# ---------------------------------------------------------------------------
# A v1 note.enc reads under v2
# ---------------------------------------------------------------------------

# Hand-written in the EXACT shape the v1 writer produced (every field the v1
# models had, none the v2 models added) — the artefact every note saved
# before this plan is.
_V1_NOTE: Final[dict[str, Any]] = {
    "schema_version": 1,
    "session_id": SESSION_ID,
    "created_at": "2026-08-04T09:10:00Z",
    "template_profile_id": "clinic-a",
    "provider_name": "extractive-v1",
    "clinician_speaker": SPEAKER_2,
    "transcript_digest": "sha256-v1:" + "a" * 64,
    "config_digest": "sha256-v1:" + "b" * 64,
    "note_sections": [
        {
            "section_key": "presenting_complaint",
            "note_assertions": [
                {
                    "assertion_id": "x0000",
                    "section_key": "presenting_complaint",
                    "note_span": {
                        "span_text": "left knee is sore",
                        "provenance": "transcript",
                        "source_coords": [0, 0, 3],
                    },
                    "speaker": SPEAKER_1,
                    "proposal_id": None,
                    "shown_text_digest": None,
                    "config_digest": None,
                    "confirmation": None,
                }
            ],
        },
        {
            "section_key": "advice_home_exercise",
            "note_assertions": [
                {
                    "assertion_id": "autofill-1",
                    "section_key": "advice_home_exercise",
                    "note_span": {
                        "span_text": "Ice pack use explained.",
                        "provenance": "autofill",
                        "source_coords": None,
                    },
                    "speaker": None,
                    "proposal_id": "autofill-1",
                    "shown_text_digest": text_digest("Ice pack use explained."),
                    "config_digest": "sha256-v1:" + "b" * 64,
                    "confirmation": {
                        "proposal_id": "autofill-1",
                        "note_confirmation": "confirmed",
                        "decided_at": "2026-08-04T09:12:00Z",
                    },
                }
            ],
        },
    ],
    "note_warnings": [
        {
            "note_warning_code": "clinician_asserted",
            "severity": "review",
            "section_key": "advice_home_exercise",
            "assertion_id": "autofill-1",
            "source_coords": None,
            "acknowledged": False,
        }
    ],
}


class TestV1FixtureReads:
    def test_the_v1_fixture_carries_no_v2_key(self) -> None:
        """The fixture is a v1 artefact: none of the four v2 keys appears
        (``config_digest`` on an assertion and a decision's absence of one
        are both v1-legal, so the decision-level key is checked by shape)."""
        blob = json.dumps(_V1_NOTE)
        for key in ("decided_by", "replaces", '"style"', "style_renderings", "confirmation_count"):
            assert key not in blob, key
        decision = _V1_NOTE["note_sections"][1]["note_assertions"][0]["confirmation"]
        assert set(decision) == {"proposal_id", "note_confirmation", "decided_at"}

    def test_a_v1_note_reads_under_v2_with_the_defaults(self) -> None:
        note = GeneratedNote.from_bytes(json.dumps(_V1_NOTE).encode("utf-8"))
        assert note.schema_version == 1
        assert note.style == "verbatim"
        assert note.style_renderings == ()
        assertions = [a for s in note.note_sections for a in s.note_assertions]
        assert [a.provenance for a in assertions] == ["transcript", "autofill"]
        assert all(a.replaces is None for a in assertions)
        confirmed = assertions[1].confirmation
        assert confirmed is not None
        assert confirmed.decided_by == "clinician"
        assert confirmed.config_digest is None
        assert confirmed.confirmation_count is None
        assert _codes(note.note_warnings) == ["clinician_asserted"]
        # It keeps the version it declares and round-trips as itself.
        reread = GeneratedNote.from_bytes(note.to_bytes())
        assert reread == note
        assert reread.schema_version == 1


# ---------------------------------------------------------------------------
# The parametrised branch test — every provenance branch, one typed line
# ---------------------------------------------------------------------------


def _branch_note_span(tmp_path: Path) -> None:
    """note.py NoteSpan._check_provenance: a clinician span is coordinate-free."""
    assert NoteSpan(span_text=TYPED_TEXT, provenance="clinician").source_coords is None
    with pytest.raises(ValidationError, match="must not carry source_coords"):
        NoteSpan(span_text=TYPED_TEXT, provenance="clinician", source_coords=SourceCoords(0, 0, 0))


def _branch_note_assertion(tmp_path: Path) -> None:
    """note.py NoteAssertion._check_confirmation: the clinician arm."""
    typed = _typed()
    assert typed.proposal_id is None
    assert typed.confirmation is not None and typed.confirmation.decided_by == "clinician"
    with pytest.raises(ValidationError, match="clinician assertion requires"):
        NoteAssertion(
            assertion_id="typed-1",
            section_key="assessment",
            note_span=NoteSpan(span_text=TYPED_TEXT, provenance="clinician"),
        )


def _branch_note_draft(tmp_path: Path) -> None:
    """note.py NoteDraft._check_draft: a typed base line is admitted, a
    rule-authored one is still refused."""
    assert "clinician" in DRAFT_BASE_PROVENANCES
    draft = _draft(_typed())
    assert any(
        a.provenance == "clinician" for s in draft.note_sections for a in s.note_assertions
    )
    text = "Ice pack use explained."
    smuggled = NoteAssertion(
        assertion_id="autofill-1",
        section_key="advice_home_exercise",
        note_span=NoteSpan(span_text=text, provenance="autofill"),
        proposal_id="autofill-1",
        shown_text_digest=text_digest(text),
        config_digest=CONFIG_DIGEST,
        confirmation=_decision("autofill-1"),
    )
    with pytest.raises(ValidationError, match="transcript-provenance"):
        _draft(smuggled)


def _branch_compose_draft(tmp_path: Path) -> None:
    """note.py compose_draft: a provider cannot return a typed line — the
    provider boundary is the ingestion check, not the draft type."""

    class _TypingProvider:
        @property
        def provider_name(self) -> str:
            return "typist-v1"

        def generate_sections(self, request: Any) -> tuple[GeneratedSection, ...]:
            return _sections((_typed(config_digest=request.config_digest, replaces=None),))

    with pytest.raises(ProviderOutputError, match="transcript-provenance"):
        compose_draft(_document(), _CONFIG, _TypingProvider(), clinician_speaker=SPEAKER_2)


def _branch_finalise_note(tmp_path: Path) -> None:
    """note.py finalise_note: the typed base line lands in the note; a
    forged typed line without its decision is refused."""
    note = _note(_typed())
    [landed] = [
        a for s in note.note_sections for a in s.note_assertions if a.assertion_id == "typed-1"
    ]
    assert landed.provenance == "clinician"
    assert landed.replaces == "q0"
    assert note.blocking_warnings() == ()
    forged_line = NoteAssertion.model_construct(
        assertion_id="typed-2",
        section_key="assessment",
        note_span=NoteSpan(span_text=TYPED_TEXT, provenance="clinician"),
        speaker=None,
        proposal_id=None,
        shown_text_digest=text_digest(TYPED_TEXT),
        config_digest=CONFIG_DIGEST,
        confirmation=None,
        replaces=None,
    )
    good = _draft(None)
    forged = NoteDraft.model_construct(
        session_id=good.session_id,
        template_profile_id=good.template_profile_id,
        provider_name=good.provider_name,
        clinician_speaker=good.clinician_speaker,
        transcript_digest=good.transcript_digest,
        config_digest=good.config_digest,
        note_sections=(
            GeneratedSection.model_construct(
                section_key="assessment", note_assertions=(forged_line,)
            ),
        ),
        note_proposals=(),
    )
    with pytest.raises(ProposalEvidenceError, match="carries no clinician decision"):
        finalise_note(forged, [], _document(), _CONFIG)


def _branch_check1_reconstruction(tmp_path: Path) -> None:
    """note_check.py Check 1: nothing to rebuild for a typed line."""
    note = _note(_typed())
    warnings = reconstruction_warnings(note, _document())
    assert not any(w.assertion_id == "typed-1" for w in warnings)


def _branch_check2_authored(tmp_path: Path) -> None:
    """note_check.py _structured_authored: a typed line is AUTHORED text and
    is contradiction-checked against the quoted evidence."""
    typed = _typed("No numbness reported.", section="red_flags_screening")
    note = _note(typed)
    authored = note_check_module._structured_authored(note)
    assert [a.assertion_id for a, _claims in authored] == ["typed-1"]
    warnings = contradiction_warnings(note, _document())
    assert _codes(warnings) == ["contradiction"]
    assert warnings[0].assertion_id == "typed-1"


def _branch_check2_quoted(tmp_path: Path) -> None:
    """note_check.py _structured_quoted: a typed line is never quoted evidence."""
    typed = _typed("No numbness reported.", section="red_flags_screening")
    note = _note(typed)
    quoted = note_check_module._structured_quoted(note, _document())
    assert "typed-1" not in {a.assertion_id for a, _claims in quoted}


def _branch_check3_role(tmp_path: Path) -> None:
    """note_check.py Check 3 role branch: a typed line in a clinician-owned
    section has no source segment to attribute — with the role confirmed it
    draws only the unsuppressible clinician_asserted review."""
    note = _note(_typed())
    warnings = provenance_warnings(note, _document(), _CONFIG)
    assert "role_unconfirmed" not in _codes(warnings)
    assert _ids_of(warnings, "clinician_asserted") == {"typed-1"}
    # With NO confirmed role the section-level rule still fires (it needs no
    # assertion to attribute): a typed line does not stand in for the role.
    unresolved = _note(_typed(), clinician_speaker=None)
    assert "role_unconfirmed" in _codes(provenance_warnings(unresolved, _document(), _CONFIG))


def _branch_check4_omission(tmp_path: Path) -> None:
    """note_check.py Check 4: coverage is coordinate carriage — a typed line
    naming the same number covers nothing."""
    note = _note(_typed("Review in 2 weeks", section="follow_up_review"))
    warnings = omission_warnings(note, _document())
    assert _codes(warnings) == ["high_risk_omission"]
    assert warnings[0].source_coords is not None
    assert warnings[0].source_coords.segment_index == 2


def _branch_write_note(tmp_path: Path) -> None:
    """session_store.py write_note: a typed line's digests are verified like
    every other authored line's, and a good one writes and reads back."""
    document = _document()
    session_dir = tmp_path / SESSION_ID
    session_dir.mkdir()
    crypto = SessionCrypto()
    write_transcript(session_dir, crypto, document)
    note = _note(_typed())
    write_note(session_dir, crypto, note, _CONFIG)
    assert read_note(session_dir, crypto) == note
    with pytest.raises(NoteWriteRefusedError, match="shown_text_digest"):
        write_note(
            session_dir,
            crypto,
            _hand_built_note(_typed(shown_text_digest=text_digest("other words"))),
            _CONFIG,
        )
    with pytest.raises(NoteWriteRefusedError, match="different config"):
        write_note(
            session_dir, crypto, _hand_built_note(_typed(config_digest=_OTHER_DIGEST)), _CONFIG
        )


def _branch_ui_models_label(tmp_path: Path) -> None:
    """ui/models.py provenance_label / format_note_body: the typed line is
    visibly distinguished in the one rendering path."""
    label = models.provenance_label("clinician")
    assert "typed" in label and "clinician-authored" in label
    body = models.format_note_body(_note(_typed()))
    assert f"  - {TYPED_TEXT}  [{label}]" in body


def _branch_ui_models_editable_lines(tmp_path: Path) -> None:
    """ui/models.py editable_lines / working_draft: a typed addition is
    admitted into the working draft but is not a movable transcript row."""
    typed = _typed()
    working = models.working_draft(_draft(None), removed=(), additions=(typed,))
    assert any(
        a.assertion_id == "typed-1" for s in working.note_sections for a in s.note_assertions
    )
    rows = models.editable_lines(
        working, _document(), removed=(), additions={"typed-1": typed}
    )
    assert "typed-1" not in {row.assertion_id for row in rows}
    assert {row.assertion_id for row in rows} == {"q0", "q1"}


_BRANCHES: Final[tuple[tuple[str, Callable[[Path], None]], ...]] = (
    ("note.py:NoteSpan._check_provenance", _branch_note_span),
    ("note.py:NoteAssertion._check_confirmation", _branch_note_assertion),
    ("note.py:NoteDraft._check_draft", _branch_note_draft),
    ("note.py:compose_draft", _branch_compose_draft),
    ("note.py:finalise_note", _branch_finalise_note),
    ("note_check.py:reconstruction_warnings", _branch_check1_reconstruction),
    ("note_check.py:_structured_authored", _branch_check2_authored),
    ("note_check.py:_structured_quoted", _branch_check2_quoted),
    ("note_check.py:provenance_warnings-role", _branch_check3_role),
    ("note_check.py:omission_warnings", _branch_check4_omission),
    ("session_store.py:write_note", _branch_write_note),
    ("ui/models.py:provenance_label", _branch_ui_models_label),
    ("ui/models.py:editable_lines", _branch_ui_models_editable_lines),
)


@pytest.mark.parametrize(
    ("branch", "check"), _BRANCHES, ids=[branch for branch, _check in _BRANCHES]
)
def test_every_provenance_branch_handles_a_typed_line(
    branch: str, check: Callable[[Path], None], tmp_path: Path
) -> None:
    """Task 0.2's Done-when: the branch list from the plan's Key Findings,
    each exercised with a ``clinician`` line (the two ``ui/note.py`` branches
    are in ``test_ui_screens.py``, which owns the Qt harness)."""
    check(tmp_path)
