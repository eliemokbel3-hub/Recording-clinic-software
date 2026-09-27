"""The cross-patient adversarial matrix — encounter and custody cases
(Cliniko workflow safeguards plan Task 3.6; the context cases that need the
pipe and Chrome are Task 5.6's).

PLAN.md Phase 5's completion line: workflow and adversarial tests cannot
attach one consultation to another patient. Every case below ends in a
refusal of its named operation — a linked Start, or write-back — and no
session is started, re-bound or changed. The positive cases must succeed.
Every Cliniko answer comes from an injected transport (no socket)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from encounter_fakes import (
    CLINIC_ID,
    NOTE,
    OTHER_CLINIC_ID,
    OTHER_HOST,
    OTHER_NOTE,
    OTHER_PATIENT,
    OTHER_PRACTITIONER,
    PATIENT,
    NoteTransport,
    clinic_record,
    consent_for,
    context,
    make_registry,
    note_body,
    ok,
    status,
    target,
)
from scribe_desktop.audio_capture import MockCaptureBackend
from scribe_desktop.encounter import (
    EncounterContext,
    EncounterRecord,
    EncounterUnavailable,
    NoteRefusal,
    NoteTarget,
    StartRefusal,
    StartRefused,
    Verification,
    VerificationLedger,
    Verified,
    VerifiedTarget,
    WritebackRefusal,
    WritebackRefused,
    WritebackSubject,
    linked_consent,
    read_encounter_record,
    reverification_request,
    unlinked_consent,
    verify_note_context,
    write_encounter_record,
    writeback_context,
)
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import ConsentRequiredError, SessionController, SessionState
from scribe_desktop.session_store import ENCOUNTER_FILENAME, unwrap_key_from_file

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI custody is Windows-only")

_API = "https://api.au2.cliniko.com/v1"


def _ledger(registry: Any) -> VerificationLedger:
    ledger = VerificationLedger(registry)
    ledger.new_connection()
    return ledger


def _report_and_answer(
    registry: Any, ledger: VerificationLedger, seq: int, note_target: NoteTarget
) -> None:
    request = ledger.report(seq, note_target)
    if request is not None:
        ledger.accept(
            verify_note_context(
                request, key_store=registry.key_store, transport=registry.transport
            )
        )


class _NoStartController:
    """A controller no refused case may reach."""

    def start(self, *args: Any, **kwargs: Any) -> Any:
        pytest.fail("a refused case started a session")


def _linked_start(ledger: VerificationLedger, controller: Any, note_target: NoteTarget) -> Any:
    """What the app does on a panel Start (Task 4.5 wires it): the bound
    report's context, or the refusal — the controller only on a context."""
    started = ledger.start_context(note_target)
    if isinstance(started, StartRefused):
        return started
    return controller.start(0, consent=linked_consent(started), context=started)


# ---------------------------------------------------------------------------
# Start is refused when the note does not verify.
# ---------------------------------------------------------------------------


def _link(resource: str, record_id: str) -> dict[str, Any]:
    return {"links": {"self": f"{_API}/{resource}/{record_id}"}}


@pytest.mark.parametrize(
    "answer, reported, refusal",
    [
        (
            ok(note_body(patient=_link("patients", OTHER_PATIENT))),
            target(),
            NoteRefusal.PATIENT_MISMATCH,
        ),
        (ok(note_body(draft=False)), target(), NoteRefusal.NOTE_FINAL),
        (ok(note_body(finalized_at="2026-09-27T01:00:00Z")), target(), NoteRefusal.NOTE_FINAL),
        (
            ok(note_body(practitioner=_link("practitioners", OTHER_PRACTITIONER))),
            target(),
            NoteRefusal.WRONG_PRACTITIONER,
        ),
        # A note id from clinic A opened under clinic B's host: B's key finds
        # no such note (Cliniko answers 404 across accounts).
        (status(404), target(host=OTHER_HOST), NoteRefusal.NOTE_NOT_FOUND),
        # A host (or shard) that is not a registered clinic: never verified.
        (ok(note_body()), target(host="elsewhere.au3.cliniko.com"), NoteRefusal.CLINIC_NOT_SET_UP),
    ],
    ids=[
        "url-patient-differs-from-the-notes",
        "not-a-draft",
        "finalised",
        "wrong-practitioner",
        "other-clinics-note",
        "unregistered-host-or-shard",
    ],
)
def test_a_note_that_does_not_verify_refuses_start(
    tmp_path: Path, answer: Any, reported: NoteTarget, refusal: NoteRefusal
) -> None:
    registry = make_registry(
        tmp_path,
        clinic_record(),
        clinic_record(OTHER_CLINIC_ID, "southside"),
        transport=NoteTransport(note=answer),
    )
    ledger = _ledger(registry)
    _report_and_answer(registry, ledger, 1, reported)
    assert _linked_start(ledger, _NoStartController(), reported) == StartRefused(
        StartRefusal.NOT_VERIFIED, refusal
    )


def test_a_start_whose_target_does_not_match_the_bound_report_is_refused(
    tmp_path: Path,
) -> None:
    registry = make_registry(tmp_path)
    ledger = _ledger(registry)
    _report_and_answer(registry, ledger, 1, target())
    for other in (
        target(patient_id=OTHER_PATIENT),
        target(note_id=OTHER_NOTE),
        target(host=OTHER_HOST),
    ):
        assert _linked_start(ledger, _NoStartController(), other) == StartRefused(
            StartRefusal.TARGET_MISMATCH
        )


def test_a_stale_seq_result_leaves_target_display_and_eligibility_unchanged(
    tmp_path: Path,
) -> None:
    registry = make_registry(tmp_path)
    ledger = _ledger(registry)
    stale = ledger.report(1, target())
    _report_and_answer(registry, ledger, 2, target(patient_id=OTHER_PATIENT, note_id=OTHER_NOTE))
    bound = ledger.bound_target()
    outcome = ledger.outcome()
    assert stale is not None
    assert not ledger.accept(
        verify_note_context(stale, key_store=registry.key_store, transport=registry.transport)
    )
    assert ledger.bound_target() == bound  # the target did not move back
    assert ledger.outcome() == outcome  # nor its outcome or display
    assert _linked_start(ledger, _NoStartController(), target()) == StartRefused(
        StartRefusal.TARGET_MISMATCH
    )


def test_an_earlier_connections_same_seq_result_finishing_last_changes_nothing(
    tmp_path: Path,
) -> None:
    """After an extension reload the seq restarts; the OLD connection's
    result for the same seq and target, finishing last, must not make the
    new connection's report startable."""
    registry = make_registry(tmp_path)
    ledger = _ledger(registry)
    old = ledger.report(1, target())
    ledger.new_connection()
    fresh = ledger.report(1, target())
    assert old is not None and fresh is not None
    assert not ledger.accept(
        verify_note_context(old, key_store=registry.key_store, transport=registry.transport)
    )
    assert ledger.outcome() is None
    assert _linked_start(ledger, _NoStartController(), target()) == StartRefused(
        StartRefusal.CHECKING
    )


def test_a_result_dispatched_before_a_key_replace_cannot_start(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)
    ledger = _ledger(registry)
    request = ledger.report(1, target())
    assert request is not None
    registry._bump(CLINIC_ID)  # Replace key (D9)
    assert not ledger.accept(
        verify_note_context(request, key_store=registry.key_store, transport=registry.transport)
    )
    assert _linked_start(ledger, _NoStartController(), target()) == StartRefused(
        StartRefusal.CHECKING
    )


# ---------------------------------------------------------------------------
# Write-back is refused unless the context is verified (Constraint 6).
# ---------------------------------------------------------------------------


def _checkout_subject(
    tmp_path: Path, blob: bytes | None, *, write_valid: bool = False
) -> WritebackSubject:
    """A checked-out session whose encounter.enc is ``blob`` (None: absent),
    read exactly as the checkout reads it."""
    directory = tmp_path / ("a" * 32)
    directory.mkdir()
    crypto = SessionCrypto()
    if write_valid:
        ctx = context()
        record_in = EncounterRecord(consent=consent_for(ctx), context=ctx)
        write_encounter_record(directory, crypto, directory.name, record_in)
    elif blob is not None:
        (directory / ENCOUNTER_FILENAME).write_bytes(blob)
    try:
        record: EncounterRecord | None = read_encounter_record(directory, crypto, directory.name)
    except EncounterUnavailable:
        record = None
    return WritebackSubject.of_checkout(record, None)


@pytest.mark.parametrize(
    "blob", [None, b"", b"\x00" * 64], ids=["missing", "empty", "corrupt"]
)
def test_a_missing_or_corrupt_encounter_record_refuses_write_back(
    tmp_path: Path, blob: bytes | None
) -> None:
    registry = make_registry(tmp_path)
    subject = _checkout_subject(tmp_path, blob)
    assert writeback_context(subject, registry) == WritebackRefused(
        WritebackRefusal.CONSENT_UNAVAILABLE
    )


def test_a_valid_but_unreverified_checkout_refuses_write_back(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)
    subject = _checkout_subject(tmp_path, None, write_valid=True)
    assert writeback_context(subject, registry) == WritebackRefused(
        WritebackRefusal.NOT_REVERIFIED
    )


@pytest.mark.parametrize("live", [True, False], ids=["live", "checkout"])
def test_an_unlinked_session_refuses_write_back(tmp_path: Path, live: bool) -> None:
    registry = make_registry(tmp_path)
    if live:
        subject = WritebackSubject.of_live(unlinked_consent(), None)
    else:
        subject = WritebackSubject.of_checkout(EncounterRecord(consent=unlinked_consent()), None)
    assert writeback_context(subject, registry) == WritebackRefused(WritebackRefusal.UNLINKED)


def test_an_unverified_offline_session_refuses_write_back(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)
    ctx = context(Verification.UNVERIFIED_OFFLINE)
    assert writeback_context(
        WritebackSubject.of_live(consent_for(ctx), ctx), registry
    ) == WritebackRefused(WritebackRefusal.NOT_VERIFIED)


def test_a_session_of_the_other_clinic_cannot_borrow_this_clinics_verification(
    tmp_path: Path,
) -> None:
    """A re-verification of clinic A's note never verifies a session linked
    to clinic B, even with the same patient and note ids."""
    registry = make_registry(
        tmp_path, clinic_record(), clinic_record(OTHER_CLINIC_ID, "southside")
    )
    other = context(clinic_id=OTHER_CLINIC_ID, clinic_host=OTHER_HOST)
    request = reverification_request(context(), registry, seq=1)
    assert request is not None
    result = verify_note_context(
        request, key_store=registry.key_store, transport=registry.transport
    )
    assert isinstance(result.outcome, Verified)
    subject = WritebackSubject.of_checkout(
        EncounterRecord(consent=consent_for(other), context=other), result
    )
    assert writeback_context(subject, registry) == WritebackRefused(
        WritebackRefusal.REVERIFICATION_STALE
    )


# ---------------------------------------------------------------------------
# The controller: consent, the record, and the immutable target.
# ---------------------------------------------------------------------------


@windows_only
def test_an_unverified_offline_start_records_and_write_back_stays_refused(
    tmp_path: Path,
) -> None:
    """POSITIVE: an offline note may be recorded — consent in encounter.enc,
    the target immutable — and write-back is refused."""
    (tmp_path / "reg").mkdir()
    registry = make_registry(tmp_path / "reg", transport=NoteTransport(note=status(503)))
    ledger = _ledger(registry)
    _report_and_answer(registry, ledger, 1, target())
    controller = SessionController(MockCaptureBackend(), sessions_root=tmp_path / "sessions")
    session = _linked_start(ledger, controller, target())
    assert session.state is SessionState.RECORDING
    ctx = session.encounter_context
    assert isinstance(ctx, EncounterContext)
    assert ctx.verification is Verification.UNVERIFIED_OFFLINE
    directory = tmp_path / "sessions" / session.session_id
    record = read_encounter_record(directory, unwrap_key_from_file(directory), directory.name)
    assert record.consent == session.consent and record.consent.treatment_note_id == NOTE
    assert record.context == ctx
    # The target is immutable: a later report of another patient changes the
    # ledger's bound report, never the session.
    _report_and_answer(registry, ledger, 2, target(patient_id=OTHER_PATIENT, note_id=OTHER_NOTE))
    live = controller.session
    assert live is not None and live.encounter_context == ctx
    assert live.encounter_context is not None and live.encounter_context.patient_id == PATIENT
    assert writeback_context(
        WritebackSubject.of_live(live.consent, live.encounter_context), registry
    ) == WritebackRefused(WritebackRefusal.NOT_VERIFIED)
    controller.discard()


@windows_only
def test_a_verified_start_writes_back_only_to_its_own_note(tmp_path: Path) -> None:
    """POSITIVE: a verified Start yields its own note as the write target
    (after the pre-write re-verification, round 20 MED-012), and a later
    patient change on the page never moves it."""
    (tmp_path / "reg").mkdir()
    registry = make_registry(tmp_path / "reg")
    ledger = _ledger(registry)
    _report_and_answer(registry, ledger, 1, target())
    controller = SessionController(MockCaptureBackend(), sessions_root=tmp_path / "sessions")
    session = _linked_start(ledger, controller, target())
    _report_and_answer(registry, ledger, 2, target(patient_id=OTHER_PATIENT, note_id=OTHER_NOTE))
    live = controller.session
    assert live is not None and live.encounter_context is not None
    unchecked = WritebackSubject.of_live(live.consent, live.encounter_context)
    assert writeback_context(unchecked, registry) == WritebackRefused(
        WritebackRefusal.NOT_REVERIFIED
    )
    request = reverification_request(live.encounter_context, registry, seq=1)
    assert request is not None
    reverified = verify_note_context(
        request, key_store=registry.key_store, transport=registry.transport
    )
    result = writeback_context(
        WritebackSubject.of_live(live.consent, live.encounter_context, reverified), registry
    )
    assert isinstance(result, VerifiedTarget)
    assert (result.patient_id, result.treatment_note_id) == (PATIENT, NOTE)
    assert live.session_id == session.session_id
    controller.discard()


@windows_only
def test_a_consent_for_another_note_cannot_start_a_linked_session(tmp_path: Path) -> None:
    controller = SessionController(MockCaptureBackend(), sessions_root=tmp_path)
    ctx = context()
    other = context(treatment_note_id=OTHER_NOTE)
    with pytest.raises(ConsentRequiredError):
        controller.start(0, consent=consent_for(other), context=ctx)
    assert controller.session is None
    assert list(tmp_path.iterdir()) == []
