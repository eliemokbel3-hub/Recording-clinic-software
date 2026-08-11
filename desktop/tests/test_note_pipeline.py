"""Phase 3A Tasks 6.1 + 6.4: the two-stage pipeline (`compose_draft` /
`finalise_note`) and the first end-to-end ExtractiveNoteProvider run.

What is pinned here, per the plan's Done-when clauses:
- `compose_draft` runs NO checks; `finalise_note` runs EVERY check — the
  Flow 1 ordering (compose -> confirm -> CHECK -> write) as an observable
  call-order fact, not a docstring claim.
- `finalise_note` refuses a note containing an unconfirmed proposal as an
  ACTION STATE (global property 4): the pending proposal comes back as an
  `unconfirmed_proposal` error riding the artifact, `blocking_warnings()`
  is non-empty, and `write_note` refuses the artifact.
- `finalise_note` refuses (typed) a non-`transcript` assertion whose
  confirmed text digest is not the digest of the text the proposal inserts.
- Confirmed clinician-authored assertions pass Checks 2 and 3: the only
  warnings they draw are the unsuppressible `clinician_asserted` reviews.
- Task 6.4: the extractive provider runs compose -> confirm -> finalise ->
  write -> read -> Complete end to end over a fixture transcript, and the
  note's concrete section contents are asserted (the usability evidence the
  plan's handoff note records; the BINDING real-transcript judgment stays
  Task 9.1's shipping gate).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from scribe_desktop import note_check as note_check_module
from scribe_desktop.note import (
    CANONICAL_SECTION_KEYS,
    ConfirmationDecision,
    ExtractiveNoteProvider,
    GeneratedNote,
    GeneratedSection,
    NoteAssertion,
    NoteDraft,
    NoteProposal,
    NoteSpan,
    ProposalEvidenceError,
    ProposalResolution,
    compose_draft,
    finalise_note,
    text_digest,
    transcript_digest,
)
from scribe_desktop.note_check import CheckTargetMismatchError
from scribe_desktop.note_config import (
    AutofillRule,
    NoteConfig,
    PrefillSeedAssertion,
    PrefillTemplate,
    SectionMapping,
    TemplateProfile,
    TemplateTarget,
)
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import (
    KEY_FILENAME,
    NOTE_FILENAME,
    NoteWriteRefusedError,
    complete_session,
    read_note,
    write_note,
)
from scribe_desktop.transcription import (
    SPEAKER_1,
    SPEAKER_2,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
    write_transcript,
)

SESSION_ID = "d" * 32
_NOW = datetime(2026, 8, 11, 15, 30, tzinfo=UTC)


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


PIPELINE_CONFIG = NoteConfig(
    template_profiles=(_profile(),),
    autofill_rules=(
        AutofillRule(
            rule_id="rule-ice",
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

# One utterance per pipeline concern: a cue-routed patient opener, a
# cue-routed clinician examination, a clinician-owned diagnosis (requires
# the confirmed role), and an unrouted clinician utterance carrying the
# autofill trigger ("ice pack") — deliberately opened with "Please" so the
# segment holds no name-like/high-risk token and Check 4 stays silent.
_TURNS: tuple[tuple[str, str], ...] = (
    ("My left knee is sore when I walk", SPEAKER_1),
    ("On examination the range of motion is limited", SPEAKER_2),
    ("The diagnosis is a mild knee sprain", SPEAKER_2),
    ("Please use an ice pack tonight", SPEAKER_2),
)


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


def _document(session_id: str = SESSION_ID) -> TranscriptDocument:
    return TranscriptDocument(
        session_id=session_id,
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


def _resolve(
    proposal: NoteProposal,
    *,
    decision: str = "confirmed",
    shown_text: str | None = None,
) -> ProposalResolution:
    """Resolution evidence as Phase 7's review surface will record it: the
    digest of the text it actually DISPLAYED plus the decision."""
    displayed = shown_text if shown_text is not None else proposal.note_excerpt
    return ProposalResolution(
        shown_text_digest=text_digest(displayed),
        confirmation=ConfirmationDecision(
            proposal_id=proposal.proposal_id,
            note_confirmation=decision,  # type: ignore[arg-type]
            decided_at=_NOW,
        ),
    )


def _draft(document: TranscriptDocument | None = None) -> NoteDraft:
    return compose_draft(
        document if document is not None else _document(),
        PIPELINE_CONFIG,
        ExtractiveNoteProvider(),
        clinician_speaker=SPEAKER_2,
    )


class TestComposeDraft:
    def test_base_note_plus_proposals(self) -> None:
        draft = _draft()
        assert draft.session_id == SESSION_ID
        assert draft.template_profile_id == "clinic-a"
        assert draft.provider_name == "extractive-v1"
        assert draft.clinician_speaker == SPEAKER_2
        assert draft.transcript_digest == transcript_digest(_document())
        assert draft.config_digest == PIPELINE_CONFIG.config_digest()
        keys = tuple(section.section_key for section in draft.note_sections)
        assert keys == ("presenting_complaint", "objective_examination", "diagnosis")
        by_provenance = {
            proposal.provenance: proposal for proposal in draft.note_proposals
        }
        assert set(by_provenance) == {"autofill", "prefill"}
        assert by_provenance["autofill"].note_excerpt == "Ice pack use explained."
        assert by_provenance["prefill"].note_excerpt == "Knee effusion assessed."

    def test_base_sections_are_transcript_assertions_only(self) -> None:
        draft = _draft()
        for section in draft.note_sections:
            for assertion in section.note_assertions:
                assert assertion.provenance == "transcript"

    def test_unconfirmed_role_leaves_clinician_owned_sections_blank(self) -> None:
        draft = compose_draft(_document(), PIPELINE_CONFIG, ExtractiveNoteProvider())
        keys = tuple(section.section_key for section in draft.note_sections)
        assert "diagnosis" not in keys  # spoken content, but the role is unresolved

    def test_compose_runs_no_checks_finalise_runs_them_once(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The Flow 1 ordering pin: checks NEVER run before confirmation."""
        calls: list[str] = []
        original = note_check_module.check_note

        def spy(*args: Any, **kwargs: Any) -> Any:
            calls.append("check_note")
            return original(*args, **kwargs)

        monkeypatch.setattr(note_check_module, "check_note", spy)
        draft = _draft()
        assert calls == []
        resolutions = [_resolve(proposal) for proposal in draft.note_proposals]
        finalise_note(draft, resolutions, _document(), PIPELINE_CONFIG)
        assert calls == ["check_note"]

    def test_duplicate_proposal_ids_are_unrepresentable(self) -> None:
        draft = _draft()
        proposal = draft.note_proposals[0]
        with pytest.raises(ValueError, match="duplicate proposal_id"):
            NoteDraft(
                session_id=draft.session_id,
                template_profile_id=draft.template_profile_id,
                provider_name=draft.provider_name,
                clinician_speaker=draft.clinician_speaker,
                transcript_digest=draft.transcript_digest,
                config_digest=draft.config_digest,
                note_sections=draft.note_sections,
                note_proposals=(proposal, proposal),
            )


class TestFinaliseNote:
    def test_all_confirmed_passes_checks_two_and_three(self) -> None:
        """Task 6.1 Done-when: confirmed clinician-authored assertions pass
        Checks 2 and 3 — the only warnings on a fully-confirmed note are the
        unsuppressible per-assertion `clinician_asserted` reviews."""
        draft = _draft()
        resolutions = [_resolve(proposal) for proposal in draft.note_proposals]
        note = finalise_note(draft, resolutions, _document(), PIPELINE_CONFIG, created_at=_NOW)
        assert note.blocking_warnings() == ()
        codes = sorted(warning.note_warning_code for warning in note.note_warnings)
        assert codes == ["clinician_asserted", "clinician_asserted"]

    def test_confirmation_evidence_rides_the_artifact(self) -> None:
        draft = _draft()
        resolutions = [_resolve(proposal) for proposal in draft.note_proposals]
        note = finalise_note(draft, resolutions, _document(), PIPELINE_CONFIG, created_at=_NOW)
        authored = [
            assertion
            for section in note.note_sections
            for assertion in section.note_assertions
            if assertion.provenance != "transcript"
        ]
        assert len(authored) == 2
        by_id = {proposal.proposal_id: proposal for proposal in draft.note_proposals}
        for assertion in authored:
            proposal = by_id[assertion.assertion_id]
            assert assertion.proposal_id == proposal.proposal_id
            assert assertion.text == proposal.note_excerpt
            assert assertion.shown_text_digest == text_digest(assertion.text)
            assert assertion.config_digest == note.config_digest
            assert assertion.confirmation is not None
            assert assertion.confirmation.note_confirmation == "confirmed"

    def test_sections_merge_in_canonical_order(self) -> None:
        draft = _draft()
        resolutions = [_resolve(proposal) for proposal in draft.note_proposals]
        note = finalise_note(draft, resolutions, _document(), PIPELINE_CONFIG, created_at=_NOW)
        keys = tuple(section.section_key for section in note.note_sections)
        assert keys == (
            "presenting_complaint",
            "objective_examination",
            "diagnosis",
            "advice_home_exercise",
        )
        # The prefill joined the EXISTING objective_examination section after
        # the provider's assertion; the autofill created its own section.
        objective = note.note_sections[1]
        assert [a.provenance for a in objective.note_assertions] == ["transcript", "prefill"]

    def test_pending_proposal_blocks_as_an_action_state(self, tmp_path: Path) -> None:
        """Global property 4, asserted as ACTION STATES: an unresolved
        proposal produces an `unconfirmed_proposal` error on the artifact,
        `blocking_warnings()` is non-empty, and `write_note` refuses."""
        draft = _draft()
        confirmed_prefill = [
            _resolve(proposal)
            for proposal in draft.note_proposals
            if proposal.provenance == "prefill"
        ]
        note = finalise_note(
            draft, confirmed_prefill, _document(), PIPELINE_CONFIG, created_at=_NOW
        )
        blocking = note.blocking_warnings()
        assert blocking, "an unresolved proposal must leave the note blocked"
        assert {warning.note_warning_code for warning in blocking} == {"unconfirmed_proposal"}
        session_dir = tmp_path / SESSION_ID
        session_dir.mkdir()
        crypto = SessionCrypto()
        write_transcript(session_dir, crypto, _document())
        with pytest.raises(NoteWriteRefusedError, match="unresolved error warnings"):
            write_note(session_dir, crypto, note, PIPELINE_CONFIG)
        assert not (session_dir / NOTE_FILENAME).exists()

    def test_declined_proposal_composes_nothing_and_is_resolved(self) -> None:
        draft = _draft()
        resolutions = [
            _resolve(
                proposal,
                decision="declined" if proposal.provenance == "autofill" else "confirmed",
            )
            for proposal in draft.note_proposals
        ]
        note = finalise_note(draft, resolutions, _document(), PIPELINE_CONFIG, created_at=_NOW)
        assert note.blocking_warnings() == ()  # declined IS resolved: no pending error
        keys = tuple(section.section_key for section in note.note_sections)
        assert "advice_home_exercise" not in keys

    def test_refuses_mismatched_shown_text_digest(self) -> None:
        """Task 6.1 Done-when: the clinician confirmed words that are not the
        words this proposal inserts — refused, never composed."""
        draft = _draft()
        resolutions = [
            _resolve(proposal, shown_text="Ice pack use explained daily.")
            if proposal.provenance == "autofill"
            else _resolve(proposal)
            for proposal in draft.note_proposals
        ]
        with pytest.raises(ProposalEvidenceError, match="not .*the digest of the text"):
            finalise_note(draft, resolutions, _document(), PIPELINE_CONFIG)

    def test_refuses_mismatched_digest_even_on_a_decline(self) -> None:
        """Round 25 LOW-001: the evidence discipline is decision-agnostic — a
        decline recorded against text the UI never displayed is refused, not
        treated as a resolution (it would otherwise silently drop a proposal
        the clinician never actually saw)."""
        draft = _draft()
        resolutions = [
            _resolve(proposal, decision="declined", shown_text="Something else entirely")
            if proposal.provenance == "autofill"
            else _resolve(proposal)
            for proposal in draft.note_proposals
        ]
        with pytest.raises(ProposalEvidenceError, match="not .*the digest of the text"):
            finalise_note(draft, resolutions, _document(), PIPELINE_CONFIG)

    def test_refuses_resolution_for_unknown_proposal(self) -> None:
        draft = _draft()
        foreign = ProposalResolution(
            shown_text_digest=text_digest("anything"),
            confirmation=ConfirmationDecision(
                proposal_id="autofill-000000000000000000000000",
                note_confirmation="confirmed",
                decided_at=_NOW,
            ),
        )
        resolutions = [_resolve(proposal) for proposal in draft.note_proposals]
        with pytest.raises(ProposalEvidenceError, match="never emitted"):
            finalise_note(draft, [*resolutions, foreign], _document(), PIPELINE_CONFIG)

    def test_refuses_duplicate_resolutions(self) -> None:
        draft = _draft()
        resolutions = [_resolve(proposal) for proposal in draft.note_proposals]
        with pytest.raises(ProposalEvidenceError, match="duplicate resolution"):
            finalise_note(
                draft, [*resolutions, resolutions[0]], _document(), PIPELINE_CONFIG
            )

    def test_stale_document_dies_in_the_digest_gate(self) -> None:
        draft = _draft()
        resolutions = [_resolve(proposal) for proposal in draft.note_proposals]
        other = _document().model_copy(update={"model_name": "other"})
        with pytest.raises(CheckTargetMismatchError):
            finalise_note(draft, resolutions, other, PIPELINE_CONFIG)


def _smuggled_assertion(config_digest: str) -> NoteAssertion:
    """A fully schema-valid `prefill` assertion with fabricated-but-
    internally-consistent confirmation evidence and NO emitted proposal —
    the round-28 PR-MED-001 payload. Constructable on purpose (every
    evidence field is public); the PIPELINE boundary is what must refuse it."""
    text = "Knee effusion assessed."
    return NoteAssertion(
        assertion_id="prefill-smuggled000000000000",
        section_key="objective_examination",
        note_span=NoteSpan(span_text=text, provenance="prefill"),
        proposal_id="prefill-smuggled000000000000",
        shown_text_digest=text_digest(text),
        config_digest=config_digest,
        confirmation=ConfirmationDecision(
            proposal_id="prefill-smuggled000000000000",
            note_confirmation="confirmed",
            decided_at=_NOW,
        ),
    )


class _SmugglingProvider:
    """A VALID NoteModelProvider whose base sections carry a clinician-
    authored assertion that was never displayed or confirmed."""

    @property
    def provider_name(self) -> str:
        return "smuggler-v1"

    def generate_sections(self, request: Any) -> tuple[GeneratedSection, ...]:
        return (
            GeneratedSection(
                section_key="objective_examination",
                note_assertions=(_smuggled_assertion(request.config_digest),),
            ),
        )


class TestProviderBoundaryConfinement:
    """Round 28 PR-MED-001: provider base sections are transcript-provenance
    ONLY — a non-transcript assertion, however complete its fabricated
    evidence, is refused at compose (the draft validator) and again at
    finalisation (against validator-skipping drafts), so it can never reach
    a writable note."""

    def test_compose_refuses_a_smuggling_provider(self) -> None:
        with pytest.raises(ValidationError, match="transcript-provenance"):
            compose_draft(
                _document(),
                PIPELINE_CONFIG,
                _SmugglingProvider(),
                clinician_speaker=SPEAKER_2,
            )

    def test_finalise_refuses_a_validator_skipping_draft(self) -> None:
        """The re-establishment leg: a `model_construct` draft bypasses the
        validator, and finalisation must still refuse the smuggled base
        assertion — no GeneratedNote ever exists, so nothing can reach
        `write_note`."""
        good = _draft()
        section = GeneratedSection(
            section_key="objective_examination",
            note_assertions=(_smuggled_assertion(good.config_digest),),
        )
        forged = NoteDraft.model_construct(
            session_id=good.session_id,
            template_profile_id=good.template_profile_id,
            provider_name=good.provider_name,
            clinician_speaker=good.clinician_speaker,
            transcript_digest=good.transcript_digest,
            config_digest=good.config_digest,
            note_sections=(section,),
            note_proposals=(),
        )
        with pytest.raises(ProposalEvidenceError, match="transcript-provenance"):
            finalise_note(forged, [], _document(), PIPELINE_CONFIG)

    def test_legitimate_providers_are_untouched_by_the_confinement(self) -> None:
        """The Extractive provider (and, by the same transcript-only
        construction, every Mock behaviour) still composes cleanly — the
        confinement narrows the provider boundary, not the pipeline."""
        draft = _draft()
        note = finalise_note(
            draft,
            [_resolve(proposal) for proposal in draft.note_proposals],
            _document(),
            PIPELINE_CONFIG,
            created_at=_NOW,
        )
        assert note.blocking_warnings() == ()


class TestExtractivePipelineEndToEnd:
    """Task 6.4: the first ExtractiveNoteProvider run through the NEW
    pipeline, over the fixture transcript, all the way to Complete.

    The concrete section contents asserted here are the fixture-transcript
    usability evidence the plan's handoff note records; judging the provider
    on a REAL recorded transcript needs the practitioner and the app, and is
    Task 9.1's shipping gate — deliberately not simulated here.
    """

    def test_full_flow_compose_confirm_finalise_write_read_complete(
        self, tmp_path: Path
    ) -> None:
        document = _document()
        session_dir = tmp_path / document.session_id
        session_dir.mkdir()
        crypto = SessionCrypto()
        write_transcript(session_dir, crypto, document)

        draft = compose_draft(
            document, PIPELINE_CONFIG, ExtractiveNoteProvider(), clinician_speaker=SPEAKER_2
        )
        resolutions = [_resolve(proposal) for proposal in draft.note_proposals]
        note = finalise_note(draft, resolutions, document, PIPELINE_CONFIG, created_at=_NOW)
        assert note.blocking_warnings() == ()

        note_path = write_note(session_dir, crypto, note, PIPELINE_CONFIG)
        assert note_path == session_dir / NOTE_FILENAME
        assert read_note(session_dir, crypto) == note

        # The note the extractive provider actually produced, verbatim.
        contents = {
            section.section_key: [assertion.text for assertion in section.note_assertions]
            for section in note.note_sections
        }
        assert contents == {
            "presenting_complaint": ["My left knee is sore when I walk"],
            "objective_examination": [
                "On examination the range of motion is limited",
                "Knee effusion assessed.",
            ],
            "diagnosis": ["The diagnosis is a mild knee sprain"],
            "advice_home_exercise": ["Ice pack use explained."],
        }

        # The note joins the Complete ordering and verifies; the key dies.
        complete_session(session_dir, crypto)
        assert not (session_dir / KEY_FILENAME).exists()
        assert (session_dir / NOTE_FILENAME).is_file()

    def test_note_describing_a_superseded_transcript_cannot_survive(
        self, tmp_path: Path
    ) -> None:
        """The Task 6.2 unlink: re-transcription removes the stale note, so
        the compose-over-new-transcript path never sees it."""
        document = _document()
        session_dir = tmp_path / document.session_id
        session_dir.mkdir()
        crypto = SessionCrypto()
        write_transcript(session_dir, crypto, document)
        draft = compose_draft(
            document, PIPELINE_CONFIG, ExtractiveNoteProvider(), clinician_speaker=SPEAKER_2
        )
        note = finalise_note(
            draft,
            [_resolve(proposal) for proposal in draft.note_proposals],
            document,
            PIPELINE_CONFIG,
            created_at=_NOW,
        )
        write_note(session_dir, crypto, note, PIPELINE_CONFIG)
        rerun = document.model_copy(update={"model_name": "rerun"})
        write_transcript(session_dir, crypto, rerun)
        assert not (session_dir / NOTE_FILENAME).exists()


def test_generated_note_round_trips_bytes() -> None:
    draft = _draft()
    note = finalise_note(
        draft,
        [_resolve(proposal) for proposal in draft.note_proposals],
        _document(),
        PIPELINE_CONFIG,
        created_at=_NOW,
    )
    assert GeneratedNote.from_bytes(note.to_bytes()) == note
