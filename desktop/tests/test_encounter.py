"""Encounter types, note verification and the write-back guard (Cliniko
workflow safeguards plan Tasks 3.1, 3.2, 3.3's record and 3.5).

Every Cliniko answer comes from an injected transport; every key from an
in-memory key store. No socket, no Credential Manager, no DPAPI."""

from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from encounter_fakes import (
    API,
    BOOKING,
    CLINIC_ID,
    EMAIL,
    HOST,
    KEY,
    KEY_2,
    NOTE,
    NOW,
    OTHER_CLINIC_ID,
    OTHER_HOST,
    OTHER_KEY,
    OTHER_NOTE,
    OTHER_PATIENT,
    OTHER_PRACTITIONER,
    PATIENT,
    PRACTITIONER,
    TEMPLATE,
    MemoryKeyStore,
    NoteTransport,
    clinic_record,
    consent_for,
    context,
    make_registry,
    note_body,
    ok,
    request_for,
    status,
    target,
)
from scribe_desktop import cliniko_client as cc
from scribe_desktop.clinics import KEY_SECRET_NAME, Removed
from scribe_desktop.encounter import (
    RECORDING_CONSENT_TEXT_VERSION,
    VERIFIED_REUSE_SECONDS,
    ConsentAttestation,
    EncounterContext,
    EncounterRecord,
    EncounterUnavailable,
    NoteRefusal,
    NoteRefused,
    NoteTarget,
    StartRefusal,
    StartRefused,
    UnverifiedOffline,
    Verification,
    VerificationLedger,
    VerificationResult,
    Verified,
    VerifiedTarget,
    WritebackRefusal,
    WritebackRefused,
    WritebackSubject,
    bind_consent,
    linked_consent,
    read_encounter_record,
    reverification_request,
    unlinked_consent,
    verify_note_context,
    write_encounter_record,
    writeback_context,
)
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import ENCOUNTER_FILENAME


def _link(resource: str, record_id: str) -> dict[str, Any]:
    return {"links": {"self": f"{API}/{resource}/{record_id}"}}


def verify(registry: Any, request: Any = None, **kwargs: Any) -> VerificationResult:
    return verify_note_context(
        request if request is not None else request_for(registry),
        key_store=registry.key_store,
        transport=registry.transport,
        clock=lambda: NOW,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Task 3.1: the types.
# ---------------------------------------------------------------------------


class TestTypes:
    def test_a_context_is_ids_only_and_frozen(self) -> None:
        ctx = context()
        assert set(EncounterContext.model_fields) == {
            "clinic_id",
            "clinic_host",
            "patient_id",
            "treatment_note_id",
            "booking_id",
            "practitioner_id",
            "template_id",
            "verification",
            "verified_at",
        }
        with pytest.raises(ValidationError):
            ctx.patient_id = OTHER_PATIENT  # type: ignore[misc]
        with pytest.raises(ValidationError):
            EncounterContext(**{**ctx.model_dump(), "patient_name": "x"})

    @pytest.mark.parametrize(
        "field, value",
        [
            ("patient_id", "0123"),
            ("patient_id", "12a"),
            ("treatment_note_id", ""),
            ("practitioner_id", "1" * 20),
            ("booking_id", "-1"),
            ("clinic_id", "XYZ"),
            ("clinic_host", "https://northside.au2.cliniko.com"),
            ("clinic_host", "northside.au9.cliniko.com"),
            ("clinic_host", "api.au2.cliniko.com"),
            ("clinic_host", "Northside.au2.cliniko.com"),
            ("clinic_host", "northside.au2.cliniko.com.evil.test"),
        ],
    )
    def test_a_context_refuses_malformed_ids_and_hosts(self, field: str, value: str) -> None:
        with pytest.raises(ValidationError):
            context(**{field: value})

    def test_verified_at_is_set_exactly_when_verified(self) -> None:
        with pytest.raises(ValidationError):
            context(Verification.VERIFIED, verified_at=None)
        with pytest.raises(ValidationError):
            context(Verification.UNVERIFIED_OFFLINE, verified_at=NOW)
        assert context(Verification.UNVERIFIED_OFFLINE).verified_at is None

    def test_booking_and_template_are_optional(self) -> None:
        ctx = context(booking_id=None, template_id=None)
        assert ctx.booking_id is None and ctx.template_id is None

    def test_consent_defaults_to_the_recording_text_version(self) -> None:
        consent = unlinked_consent(NOW)
        assert consent.text_version == RECORDING_CONSENT_TEXT_VERSION == "recording-consent-v1"
        assert consent.treatment_note_id is None and consent.practitioner_id is None
        with pytest.raises(ValidationError):
            ConsentAttestation(confirmed_at=NOW, text_version="consent-v3")  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            ConsentAttestation(confirmed_at=datetime(2026, 9, 27))  # naive time

    def test_bind_consent(self) -> None:
        ctx = context()
        bind_consent(unlinked_consent(NOW), None)
        bind_consent(linked_consent(ctx, NOW), ctx)
        bind_consent(ConsentAttestation(confirmed_at=NOW, treatment_note_id=NOTE), ctx)
        for consent, bound in (
            (linked_consent(ctx, NOW), None),
            (unlinked_consent(NOW), ctx),
            (ConsentAttestation(confirmed_at=NOW, treatment_note_id=OTHER_NOTE), ctx),
            (
                ConsentAttestation(
                    confirmed_at=NOW, treatment_note_id=NOTE, practitioner_id=OTHER_PRACTITIONER
                ),
                ctx,
            ),
        ):
            with pytest.raises(ValueError):
                bind_consent(consent, bound)


class TestEncounterRecord:
    def _dir(self, tmp_path: Path) -> tuple[Path, str]:
        session_id = uuid.uuid4().hex
        directory = tmp_path / session_id
        directory.mkdir()
        return directory, session_id

    @pytest.mark.parametrize("linked", [True, False], ids=["linked", "unlinked"])
    def test_round_trip_under_the_session_key(self, tmp_path: Path, linked: bool) -> None:
        directory, session_id = self._dir(tmp_path)
        crypto = SessionCrypto()
        ctx = context() if linked else None
        record = EncounterRecord(
            consent=consent_for(ctx) if ctx is not None else unlinked_consent(NOW), context=ctx
        )
        write_encounter_record(directory, crypto, session_id, record)
        blob = (directory / ENCOUNTER_FILENAME).read_bytes()
        assert PATIENT.encode() not in blob and b"consent" not in blob  # encrypted
        assert read_encounter_record(directory, crypto, session_id) == record

    def test_the_record_refuses_an_unbound_consent(self) -> None:
        with pytest.raises(ValidationError):
            EncounterRecord(consent=unlinked_consent(NOW), context=context())

    def test_missing_is_unavailable(self, tmp_path: Path) -> None:
        directory, session_id = self._dir(tmp_path)
        with pytest.raises(EncounterUnavailable):
            read_encounter_record(directory, SessionCrypto(), session_id)

    def test_another_key_is_unavailable(self, tmp_path: Path) -> None:
        directory, session_id = self._dir(tmp_path)
        write_encounter_record(
            directory, SessionCrypto(), session_id, EncounterRecord(consent=unlinked_consent(NOW))
        )
        with pytest.raises(EncounterUnavailable):
            read_encounter_record(directory, SessionCrypto(), session_id)

    def test_the_associated_data_binds_the_session(self, tmp_path: Path) -> None:
        """Same key, another session's id: the distinct AAD refuses it."""
        directory, session_id = self._dir(tmp_path)
        crypto = SessionCrypto()
        write_encounter_record(
            directory, crypto, session_id, EncounterRecord(consent=unlinked_consent(NOW))
        )
        with pytest.raises(EncounterUnavailable):
            read_encounter_record(directory, crypto, uuid.uuid4().hex)
        # ...and a plain decrypt (the transcript/note shape, no AAD) fails too.
        with pytest.raises(Exception):  # noqa: B017 - cryptography's InvalidTag
            crypto.decrypt((directory / ENCOUNTER_FILENAME).read_bytes())

    @pytest.mark.parametrize(
        "corrupt", [b"", b"\x00" * 40, b"not encrypted at all, just some bytes here"]
    )
    def test_corrupt_is_unavailable(self, tmp_path: Path, corrupt: bytes) -> None:
        directory, session_id = self._dir(tmp_path)
        (directory / ENCOUNTER_FILENAME).write_bytes(corrupt)
        with pytest.raises(EncounterUnavailable):
            read_encounter_record(directory, SessionCrypto(), session_id)

    def test_a_decryptable_record_that_is_not_the_schema_is_unavailable(
        self, tmp_path: Path
    ) -> None:
        from scribe_desktop.session_store import write_encounter

        directory, session_id = self._dir(tmp_path)
        crypto = SessionCrypto()
        write_encounter(directory, crypto, session_id, b'{"schema_version": 1, "patient_id": "1"}')
        with pytest.raises(EncounterUnavailable) as caught:
            read_encounter_record(directory, crypto, session_id)
        assert PATIENT not in str(caught.value) and caught.value.__context__ is None


# ---------------------------------------------------------------------------
# Task 3.2: note verification (the worker).
# ---------------------------------------------------------------------------


class TestVerifyNoteContext:
    def test_an_open_note_of_this_patient_and_practitioner_verifies(
        self, tmp_path: Path
    ) -> None:
        transport = NoteTransport()
        registry = make_registry(tmp_path, transport=transport)
        result = verify(registry)
        assert isinstance(result.outcome, Verified)
        ctx = result.outcome.context
        assert ctx == context()  # ids, booking, template, verified at NOW
        display = result.outcome.display
        assert display.patient_display_name == "Jan Citizen"  # the preferred first name
        assert display.appointment_starts_at == datetime(2026, 9, 27, 0, 30, tzinfo=UTC)
        paths = [call[2] for call in transport.calls]
        assert paths == [
            f"/v1/treatment_notes/{NOTE}",
            f"/v1/patients/{PATIENT}",
            f"/v1/bookings/{BOOKING}",
        ]
        assert {call[0] for call in transport.calls} == {"GET"}
        assert {call[1] for call in transport.calls} == {"api.au2.cliniko.com"}

    def test_one_call_one_key_read(self, tmp_path: Path) -> None:
        """D9: one verification is ONE client call — the key is read once and
        every request carries that same credential."""
        storage = MemoryKeyStore()
        transport = NoteTransport()
        registry = make_registry(tmp_path, transport=transport, storage=storage)
        reads = storage.reads
        verify(registry)
        assert storage.reads == reads + 1
        assert len({call[3]["Authorization"] for call in transport.calls}) == 1

    def test_a_key_replaced_mid_call_is_not_mixed_in(self, tmp_path: Path) -> None:
        storage = MemoryKeyStore()

        def replace_then_answer() -> cc.RawResponse:
            storage.store(CLINIC_ID, KEY_SECRET_NAME, KEY_2)
            return ok({"id": PATIENT, "first_name": "Jan", "last_name": "Citizen"})

        transport = NoteTransport(patient=replace_then_answer)
        registry = make_registry(tmp_path, transport=transport, storage=storage)
        verify(registry)
        assert len({call[3]["Authorization"] for call in transport.calls}) == 1

    def test_no_booking_link_means_no_booking_read(self, tmp_path: Path) -> None:
        transport = NoteTransport(note=ok(note_body(booking=None, treatment_note_template=None)))
        registry = make_registry(tmp_path, transport=transport)
        result = verify(registry)
        assert isinstance(result.outcome, Verified)
        assert result.outcome.context.booking_id is None
        assert result.outcome.context.template_id is None
        assert result.outcome.display.appointment_starts_at is None
        assert [c[2] for c in transport.calls][-1] == f"/v1/patients/{PATIENT}"

    @pytest.mark.parametrize(
        "note, reason",
        [
            (note_body(patient=_link("patients", OTHER_PATIENT)), NoteRefusal.PATIENT_MISMATCH),
            (note_body(draft=False), NoteRefusal.NOTE_FINAL),
            (note_body(finalized_at="2026-09-27T01:00:00Z"), NoteRefusal.NOTE_FINAL),
            (note_body(archived_at="2026-09-27T01:00:00Z"), NoteRefusal.NOTE_ARCHIVED),
            (note_body(deleted_at="2026-09-27T01:00:00Z"), NoteRefusal.NOTE_ARCHIVED),
            (
                note_body(practitioner=_link("practitioners", OTHER_PRACTITIONER)),
                NoteRefusal.WRONG_PRACTITIONER,
            ),
        ],
        ids=[
            "url-patient-differs",
            "not-a-draft",
            "finalized",
            "archived",
            "deleted",
            "wrong-practitioner",
        ],
    )
    def test_a_named_refusal_for_each_mismatch(
        self, tmp_path: Path, note: dict[str, Any], reason: NoteRefusal
    ) -> None:
        transport = NoteTransport(note=ok(note))
        registry = make_registry(tmp_path, transport=transport)
        result = verify(registry)
        assert result.outcome == NoteRefused(reason)
        assert len(transport.calls) == 1  # no display read for a refused note

    @pytest.mark.parametrize(
        "answer, reason",
        [
            (status(401), NoteRefusal.KEY_REJECTED),
            (status(403), NoteRefusal.KEY_REJECTED),
            (status(404), NoteRefusal.NOTE_NOT_FOUND),
            (cc.CertificateRejected(), NoteRefusal.CERTIFICATE_REJECTED),
            (status(302), NoteRefusal.ANSWER_UNREADABLE),
            (status(418), NoteRefusal.ANSWER_UNREADABLE),
            (
                cc.RawResponse(status=200, rate_limit_reset=None, body=b"[]"),
                NoteRefusal.ANSWER_UNREADABLE,
            ),
        ],
        ids=["401", "403", "404", "certificate", "redirect", "teapot", "not-an-object"],
    )
    def test_refusal_statuses(self, tmp_path: Path, answer: Any, reason: NoteRefusal) -> None:
        registry = make_registry(tmp_path, transport=NoteTransport(note=answer))
        assert verify(registry).outcome == NoteRefused(reason)

    @pytest.mark.parametrize(
        "answer",
        [
            status(500),
            status(503),
            cc.RawResponse(status=429, rate_limit_reset="30", body=b""),
            cc.Unreachable(),  # a connection, DNS, timeout or non-certificate TLS failure
        ],
        ids=["500", "503", "429", "unreachable"],
    )
    def test_offline_classes_are_unverified_offline(self, tmp_path: Path, answer: Any) -> None:
        registry = make_registry(tmp_path, transport=NoteTransport(note=answer))
        result = verify(registry)
        assert isinstance(result.outcome, UnverifiedOffline)
        ctx = result.outcome.context
        assert ctx.verification is Verification.UNVERIFIED_OFFLINE
        assert ctx.verified_at is None and ctx.booking_id is None
        assert (ctx.clinic_id, ctx.patient_id, ctx.treatment_note_id, ctx.practitioner_id) == (
            CLINIC_ID,
            PATIENT,
            NOTE,
            PRACTITIONER,
        )

    def test_an_offline_display_read_is_offline_too(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path, transport=NoteTransport(patient=status(503)))
        assert isinstance(verify(registry).outcome, UnverifiedOffline)

    def test_a_deleted_booking_shows_no_time_and_still_verifies(self, tmp_path: Path) -> None:
        """Round 57 SEC-011: the booking is display only (D4) — its 404 is no
        time shown, never "note not found" for a note that passed every check."""
        transport = NoteTransport(booking=status(404))
        registry = make_registry(tmp_path, transport=transport)
        result = verify(registry)
        assert isinstance(result.outcome, Verified)
        assert result.outcome.context == context()
        assert result.outcome.display.appointment_starts_at is None

    @pytest.mark.parametrize(
        "answer, expected",
        [(status(401), NoteRefused(NoteRefusal.KEY_REJECTED)), (status(503), UnverifiedOffline)],
        ids=["401", "503"],
    )
    def test_any_other_booking_failure_is_unchanged(
        self, tmp_path: Path, answer: Any, expected: Any
    ) -> None:
        registry = make_registry(tmp_path, transport=NoteTransport(booking=answer))
        outcome = verify(registry).outcome
        if isinstance(expected, type):
            assert isinstance(outcome, expected)
        else:
            assert outcome == expected

    @pytest.mark.parametrize(
        "note",
        [
            note_body(draft="yes"),
            {k: v for k, v in note_body().items() if k != "finalized_at"},
            note_body(patient=None),
            note_body(practitioner=None),
            note_body(patient={"links": {"self": "https://evil.test/v1/patients/1001"}}),
            note_body(patient=_link("users", PATIENT)),
            note_body(patient={"links": {"self": f"{API}/patients/{PATIENT}?x=1"}}),
            note_body(booking="3001"),
        ],
        ids=[
            "draft-not-bool",
            "no-finalized-at",
            "no-patient-link",
            "no-practitioner-link",
            "foreign-link-host",
            "wrong-resource",
            "query-on-link",
            "link-not-object",
        ],
    )
    def test_an_answer_off_the_p1_shape_is_unreadable(
        self, tmp_path: Path, note: dict[str, Any]
    ) -> None:
        registry = make_registry(tmp_path, transport=NoteTransport(note=ok(note)))
        assert verify(registry).outcome == NoteRefused(NoteRefusal.ANSWER_UNREADABLE)

    def test_a_missing_or_unreadable_key_is_named(self, tmp_path: Path) -> None:
        storage = MemoryKeyStore()
        transport = NoteTransport()
        registry = make_registry(tmp_path, transport=transport, storage=storage)
        storage.keys.clear()
        assert verify(registry).outcome == NoteRefused(NoteRefusal.KEY_UNAVAILABLE)
        storage.fail_read = True
        assert verify(registry).outcome == NoteRefused(NoteRefusal.KEY_UNAVAILABLE)
        assert transport.calls == []  # nothing sent without a key

    def test_a_host_not_the_clinics_is_refused_without_a_call(self, tmp_path: Path) -> None:
        transport = NoteTransport()
        registry = make_registry(tmp_path, transport=transport)
        result = verify(registry, request_for(registry, target(host=OTHER_HOST)))
        assert result.outcome == NoteRefused(NoteRefusal.CLINIC_MISMATCH)
        assert transport.calls == []

    def test_the_worker_never_raises(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path, transport=NoteTransport(note=RuntimeError("boom")))
        assert verify(registry).outcome == NoteRefused(NoteRefusal.ANSWER_UNREADABLE)

    def test_display_strings_are_plain_bounded_text(self, tmp_path: Path) -> None:
        patient = ok(
            {
                "first_name": "<b>Jan</b>‮",
                "preferred_first_name": "",
                "last_name": "Cit\nizen\u0007" + "x" * 300,
            }
        )
        registry = make_registry(tmp_path, transport=NoteTransport(patient=patient))
        result = verify(registry)
        assert isinstance(result.outcome, Verified)
        name = result.outcome.display.patient_display_name
        assert "\n" not in name and "‮" not in name and "\u0007" not in name
        assert name.startswith("<b>Jan</b> Cit izen")  # kept as TEXT, never markup
        assert len(name) <= 120

    def test_a_lone_surrogate_in_a_name_becomes_a_space(self, tmp_path: Path) -> None:
        """H1 round 53 LOW-044: a JSON escape can carry a lone surrogate,
        which no UTF-8 snapshot can hold; it is cleaned like a control
        character, and the name still reads."""
        patient = ok({"first_name": "Jan\udc00", "preferred_first_name": "", "last_name": "Cit"})
        registry = make_registry(tmp_path, transport=NoteTransport(patient=patient))
        result = verify(registry)
        assert isinstance(result.outcome, Verified)
        name = result.outcome.display.patient_display_name
        assert name == "Jan Cit"
        name.encode("utf-8")  # a snapshot can carry it

    def test_nothing_in_a_result_repr_carries_the_key(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        result = verify(registry)
        assert KEY not in repr(result)
        assert "Jan" not in repr(result)  # the display is kept out of the repr


# ---------------------------------------------------------------------------
# Task 3.2: the GUI-thread ledger — tagging, staleness, throttling.
# ---------------------------------------------------------------------------


def _answer(registry: Any, request: Any) -> VerificationResult:
    return verify(registry, request)


class TestLedger:
    def test_a_report_dispatches_one_request_and_its_answer_binds(
        self, tmp_path: Path
    ) -> None:
        registry = make_registry(tmp_path)
        ledger = VerificationLedger(registry)
        ledger.new_connection()
        request = ledger.report(1, target())
        assert request is not None and (request.conn_gen, request.seq) == (1, 1)
        assert ledger.outcome() is None  # checking
        assert ledger.start_context(target()) == StartRefused(StartRefusal.CHECKING)
        assert ledger.accept(_answer(registry, request))
        assert isinstance(ledger.outcome(), Verified)
        assert ledger.start_context(target()) == context()

    def test_reports_of_the_same_note_share_one_verification(self, tmp_path: Path) -> None:
        """The per-note throttle: a run of reports of one target calls once."""
        registry = make_registry(tmp_path)
        ledger = VerificationLedger(registry)
        ledger.new_connection()
        first = ledger.report(1, target())
        assert ledger.report(2, target()) is None
        assert ledger.report(3, target()) is None
        assert first is not None and ledger.accept(_answer(registry, first))
        assert isinstance(ledger.outcome(), Verified)

    def test_a_recently_verified_note_is_reused_without_a_call(self, tmp_path: Path) -> None:
        """Round 20 LOW-016, D4's per-note throttle: switching A -> B -> A
        re-uses A's verification instead of checking it again."""
        now = [100.0]
        registry = make_registry(tmp_path)
        ledger = VerificationLedger(registry, clock=lambda: now[0])
        ledger.new_connection()
        first = ledger.report(1, target())
        assert first is not None and ledger.accept(_answer(registry, first))
        assert ledger.report(2, target(note_id=OTHER_NOTE)) is not None  # B: checked
        now[0] += VERIFIED_REUSE_SECONDS - 1
        assert ledger.report(3, target()) is None  # back to A: no call
        assert isinstance(ledger.outcome(), Verified)
        assert ledger.start_context(target()) == context()

    def test_reuse_ends_with_the_window_the_rev_or_the_connection(
        self, tmp_path: Path
    ) -> None:
        now = [100.0]
        registry = make_registry(tmp_path)
        ledger = VerificationLedger(registry, clock=lambda: now[0])
        ledger.new_connection()

        def verify_then_leave(seq: int) -> None:
            request = ledger.report(seq, target())
            assert request is not None and ledger.accept(_answer(registry, request))
            assert ledger.report(seq + 1, target(note_id=OTHER_NOTE)) is not None

        verify_then_leave(1)
        now[0] += VERIFIED_REUSE_SECONDS + 1  # the window passed
        assert ledger.report(3, target()) is not None
        ledger.report(4, target(note_id=OTHER_NOTE))
        verify_then_leave(5)
        registry._bump(CLINIC_ID)  # Replace key (D9)
        assert ledger.report(7, target()) is not None
        ledger.report(8, target(note_id=OTHER_NOTE))
        verify_then_leave(9)
        ledger.new_connection()
        assert ledger.report(1, target()) is not None

    def test_a_refused_or_offline_note_is_never_reused(self, tmp_path: Path) -> None:
        for answer in (ok(note_body(draft=False)), status(503)):
            registry = make_registry(tmp_path, transport=NoteTransport(note=answer))
            ledger = VerificationLedger(registry, clock=lambda: 100.0)
            ledger.new_connection()
            request = ledger.report(1, target())
            assert request is not None and ledger.accept(_answer(registry, request))
            ledger.report(2, target(note_id=OTHER_NOTE))
            assert ledger.report(3, target()) is not None  # checked again

    def test_a_replayed_or_out_of_order_report_is_ignored(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        ledger = VerificationLedger(registry)
        ledger.new_connection()
        ledger.report(5, target())
        assert ledger.report(5, target(note_id=OTHER_NOTE)) is None
        assert ledger.report(4, target(note_id=OTHER_NOTE)) is None
        assert ledger.bound_target() == target()

    def test_a_stale_seq_result_changes_nothing(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        ledger = VerificationLedger(registry)
        ledger.new_connection()
        stale = ledger.report(1, target())
        ledger.report(2, target(note_id=OTHER_NOTE))
        ledger.report(3, target())  # back to the first note: a NEW run
        assert stale is not None
        assert not ledger.accept(_answer(registry, stale))
        assert ledger.outcome() is None
        assert ledger.start_context(target()) == StartRefused(StartRefusal.CHECKING)

    def test_an_earlier_connections_result_with_the_same_seq_is_dropped(
        self, tmp_path: Path
    ) -> None:
        """After an extension reload the new connection's seq restarts; a
        result from the EARLIER connection carrying the SAME seq and target,
        finishing last, must not bind."""
        registry = make_registry(tmp_path)
        ledger = VerificationLedger(registry)
        ledger.new_connection()
        old = ledger.report(1, target())
        ledger.new_connection()
        fresh = ledger.report(1, target())
        assert old is not None and fresh is not None
        assert (old.seq, old.target) == (fresh.seq, fresh.target)
        assert not ledger.accept(_answer(registry, old))
        assert ledger.outcome() is None
        assert ledger.accept(_answer(registry, fresh))
        assert isinstance(ledger.outcome(), Verified)

    def test_a_new_connection_clears_the_bound_report(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        ledger = VerificationLedger(registry)
        ledger.new_connection()
        request = ledger.report(1, target())
        assert request is not None and ledger.accept(_answer(registry, request))
        ledger.new_connection()
        assert ledger.bound_target() is None and ledger.outcome() is None
        assert ledger.start_context(target()) == StartRefused(StartRefusal.NO_REPORT)

    def test_a_result_after_a_key_replace_is_dropped_and_a_fresh_check_runs(
        self, tmp_path: Path
    ) -> None:
        registry = make_registry(tmp_path)
        ledger = VerificationLedger(registry)
        ledger.new_connection()
        request = ledger.report(1, target())
        assert request is not None
        registry._bump(CLINIC_ID)  # what Replace key / Remove do (D9)
        assert not ledger.accept(_answer(registry, request))
        fresh = ledger.reverify_after_clinic_change()
        assert fresh is not None and fresh.clinic_rev == registry.rev(CLINIC_ID)
        assert ledger.accept(_answer(registry, fresh))
        assert isinstance(ledger.outcome(), Verified)

    def test_an_applied_outcome_is_voided_when_the_clinic_rev_moves(
        self, tmp_path: Path
    ) -> None:
        registry = make_registry(tmp_path)
        ledger = VerificationLedger(registry)
        ledger.new_connection()
        request = ledger.report(1, target())
        assert request is not None and ledger.accept(_answer(registry, request))
        registry._bump(CLINIC_ID)
        assert ledger.outcome() is None
        assert ledger.start_context(target()) == StartRefused(StartRefusal.NOT_VERIFIED)
        assert ledger.reverify_after_clinic_change() is not None

    def test_a_removed_clinics_pending_result_restores_nothing(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        ledger = VerificationLedger(registry)
        ledger.new_connection()
        request = ledger.report(1, target())
        assert request is not None
        assert isinstance(registry.remove(CLINIC_ID, live_session_clinic=None), Removed)
        assert not ledger.accept(_answer(registry, request))
        assert registry.record(CLINIC_ID) is None
        assert ledger.reverify_after_clinic_change() is None
        assert ledger.outcome() == NoteRefused(NoteRefusal.CLINIC_NOT_SET_UP)

    def test_an_unregistered_host_is_not_set_up_without_a_call(self, tmp_path: Path) -> None:
        transport = NoteTransport()
        registry = make_registry(tmp_path, transport=transport)
        ledger = VerificationLedger(registry)
        ledger.new_connection()
        assert ledger.report(1, target(host=OTHER_HOST)) is None
        assert ledger.outcome() == NoteRefused(NoteRefusal.CLINIC_NOT_SET_UP)
        assert ledger.start_context(target(host=OTHER_HOST)) == StartRefused(
            StartRefusal.NOT_VERIFIED, NoteRefusal.CLINIC_NOT_SET_UP
        )
        assert transport.calls == []

    def test_a_page_that_is_not_a_note_dispatches_nothing(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        ledger = VerificationLedger(registry)
        ledger.new_connection()
        assert ledger.report(1, None) is None
        assert ledger.start_context(target()) == StartRefused(StartRefusal.NO_REPORT)

    def test_start_context_must_name_the_bound_target(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        ledger = VerificationLedger(registry)
        ledger.new_connection()
        request = ledger.report(1, target())
        assert request is not None and ledger.accept(_answer(registry, request))
        assert ledger.start_context(target(patient_id=OTHER_PATIENT)) == StartRefused(
            StartRefusal.TARGET_MISMATCH
        )

    def test_a_refused_note_is_not_startable(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path, transport=NoteTransport(note=ok(note_body(draft=False))))
        ledger = VerificationLedger(registry)
        ledger.new_connection()
        request = ledger.report(1, target())
        assert request is not None and ledger.accept(_answer(registry, request))
        assert ledger.start_context(target()) == StartRefused(
            StartRefusal.NOT_VERIFIED, NoteRefusal.NOTE_FINAL
        )

    def test_an_offline_note_is_startable_unverified(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path, transport=NoteTransport(note=status(503)))
        ledger = VerificationLedger(registry)
        ledger.new_connection()
        request = ledger.report(1, target())
        assert request is not None and ledger.accept(_answer(registry, request))
        started = ledger.start_context(target())
        assert isinstance(started, EncounterContext)
        assert started.verification is Verification.UNVERIFIED_OFFLINE

    def test_a_verified_note_confirms_a_typed_subdomain(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path, clinic_record(confirmed=False))
        ledger = VerificationLedger(registry)
        ledger.new_connection()
        request = ledger.report(1, target())
        assert request is not None and ledger.accept(_answer(registry, request))
        record = registry.record(CLINIC_ID)
        assert record is not None and record.subdomain_confirmed

    def test_the_other_clinics_note_verifies_under_its_own_key(self, tmp_path: Path) -> None:
        """Codex round 22 PR-LOW-100: each clinic has its own fake key, and
        a note on clinic B's host is verified with B's credential only."""
        transport = NoteTransport()
        registry = make_registry(
            tmp_path,
            clinic_record(),
            clinic_record(OTHER_CLINIC_ID, "southside"),
            transport=transport,
        )
        ledger = VerificationLedger(registry)
        ledger.new_connection()
        request = ledger.report(1, target(host=OTHER_HOST))
        assert request is not None and request.clinic.clinic_id == OTHER_CLINIC_ID
        assert ledger.accept(_answer(registry, request))
        basic = {
            key: "Basic " + base64.b64encode(f"{key}:".encode("ascii")).decode("ascii")
            for key in (KEY, OTHER_KEY)
        }
        assert transport.calls, "no request was made"
        assert {call[3]["Authorization"] for call in transport.calls} == {basic[OTHER_KEY]}
        assert {call[1] for call in transport.calls} == {"api.au2.cliniko.com"}  # B's shard
        outcome = ledger.outcome()
        assert isinstance(outcome, Verified)
        assert (outcome.context.clinic_id, outcome.context.clinic_host) == (
            OTHER_CLINIC_ID,
            OTHER_HOST,
        )


# ---------------------------------------------------------------------------
# Task 3.4: the checkout re-verification request.
# ---------------------------------------------------------------------------


class TestReverificationRequest:
    def test_built_from_the_stored_context_under_the_current_rev(
        self, tmp_path: Path
    ) -> None:
        registry = make_registry(tmp_path)
        registry._bump(CLINIC_ID)
        request = reverification_request(context(), registry, seq=7)
        assert request is not None
        assert (request.conn_gen, request.seq, request.target) == (0, 7, target())
        assert request.clinic_rev == registry.rev(CLINIC_ID)
        assert request.contact_email == EMAIL

    def test_none_when_the_clinic_is_gone(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        registry.remove(CLINIC_ID, live_session_clinic=None)
        assert reverification_request(context(), registry, seq=1) is None


# ---------------------------------------------------------------------------
# Task 3.5: the write-back guard.
# ---------------------------------------------------------------------------


def _reverified(registry: Any, ctx: EncounterContext | None = None, **kw: Any) -> Any:
    request = reverification_request(ctx if ctx is not None else context(), registry, seq=1)
    assert request is not None
    return verify(registry, request, **kw)


class TestWritebackContext:
    def test_a_verified_live_session_yields_its_target_after_a_reverification(
        self, tmp_path: Path
    ) -> None:
        registry = make_registry(tmp_path)
        ctx = context()
        result = writeback_context(
            WritebackSubject.of_live(consent_for(ctx), ctx, _reverified(registry, ctx)), registry
        )
        assert result == VerifiedTarget(
            clinic_id=CLINIC_ID,
            clinic_host=HOST,
            patient_id=PATIENT,
            treatment_note_id=NOTE,
            practitioner_id=PRACTITIONER,
            booking_id=BOOKING,
            template_id=TEMPLATE,
        )

    def test_a_start_verification_alone_is_not_trusted(self, tmp_path: Path) -> None:
        """Round 20 MED-012: a live session verified at Start still needs a
        re-verification under the clinic's current rev — a Replace key since
        Start moved the rev, and the Start verification says nothing of it."""
        registry = make_registry(tmp_path)
        ctx = context()
        assert ctx.verification is Verification.VERIFIED
        subject = WritebackSubject.of_live(consent_for(ctx), ctx)
        assert writeback_context(subject, registry) == WritebackRefused(
            WritebackRefusal.NOT_REVERIFIED
        )
        stale = _reverified(registry, ctx)
        registry._bump(CLINIC_ID)  # Replace key after the re-verification
        assert writeback_context(
            WritebackSubject.of_live(consent_for(ctx), ctx, stale), registry
        ) == WritebackRefused(WritebackRefusal.REVERIFICATION_STALE)

    def test_an_unlinked_live_session_is_refused(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        subject = WritebackSubject.of_live(unlinked_consent(NOW), None)
        assert writeback_context(subject, registry) == WritebackRefused(WritebackRefusal.UNLINKED)

    def test_an_unverified_offline_live_session_is_refused(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        ctx = context(Verification.UNVERIFIED_OFFLINE)
        subject = WritebackSubject.of_live(consent_for(ctx), ctx)
        assert writeback_context(subject, registry) == WritebackRefused(
            WritebackRefusal.NOT_VERIFIED
        )

    def test_an_offline_live_session_is_allowed_after_a_current_reverification(
        self, tmp_path: Path
    ) -> None:
        registry = make_registry(tmp_path)
        ctx = context(Verification.UNVERIFIED_OFFLINE)
        subject = WritebackSubject.of_live(consent_for(ctx), ctx, _reverified(registry, ctx))
        result = writeback_context(subject, registry)
        assert isinstance(result, VerifiedTarget) and result.booking_id == BOOKING

    def test_a_checkout_without_a_reverification_is_refused(self, tmp_path: Path) -> None:
        """A checked-out session's stored verification is never trusted alone."""
        registry = make_registry(tmp_path)
        ctx = context()
        record = EncounterRecord(consent=consent_for(ctx), context=ctx)
        assert writeback_context(WritebackSubject.of_checkout(record, None), registry) == (
            WritebackRefused(WritebackRefusal.NOT_REVERIFIED)
        )

    def test_a_reverified_checkout_yields_its_target(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        ctx = context()
        record = EncounterRecord(consent=consent_for(ctx), context=ctx)
        subject = WritebackSubject.of_checkout(record, _reverified(registry, ctx))
        assert isinstance(writeback_context(subject, registry), VerifiedTarget)

    def test_a_missing_record_is_consent_unavailable(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        assert writeback_context(WritebackSubject.of_checkout(None, None), registry) == (
            WritebackRefused(WritebackRefusal.CONSENT_UNAVAILABLE)
        )

    def test_an_unlinked_record_is_refused(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        record = EncounterRecord(consent=unlinked_consent(NOW))
        assert writeback_context(WritebackSubject.of_checkout(record, None), registry) == (
            WritebackRefused(WritebackRefusal.UNLINKED)
        )

    def test_a_removed_clinic_is_refused(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        ctx = context()
        result = _reverified(registry, ctx)
        registry.remove(CLINIC_ID, live_session_clinic=None)
        subject = WritebackSubject.of_checkout(
            EncounterRecord(consent=consent_for(ctx), context=ctx), result
        )
        assert writeback_context(subject, registry) == WritebackRefused(
            WritebackRefusal.CLINIC_GONE
        )

    def test_a_clinic_whose_practitioner_changed_is_refused(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path, clinic_record(practitioner_id=OTHER_PRACTITIONER))
        ctx = context()
        subject = WritebackSubject.of_live(consent_for(ctx), ctx)
        assert writeback_context(subject, registry) == WritebackRefused(
            WritebackRefusal.CLINIC_CHANGED
        )

    def test_a_reverification_under_an_old_rev_is_stale(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        ctx = context()
        result = _reverified(registry, ctx)
        registry._bump(CLINIC_ID)  # a Replace key since
        subject = WritebackSubject.of_checkout(
            EncounterRecord(consent=consent_for(ctx), context=ctx), result
        )
        assert writeback_context(subject, registry) == WritebackRefused(
            WritebackRefusal.REVERIFICATION_STALE
        )

    def test_a_reverification_of_another_note_is_stale(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        ctx = context()
        other = reverification_request(context(treatment_note_id=OTHER_NOTE), registry, seq=1)
        assert other is not None
        subject = WritebackSubject.of_checkout(
            EncounterRecord(consent=consent_for(ctx), context=ctx), verify(registry, other)
        )
        assert writeback_context(subject, registry) == WritebackRefused(
            WritebackRefusal.REVERIFICATION_STALE
        )

    def test_a_refused_reverification_names_its_reason(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path, transport=NoteTransport(note=ok(note_body(draft=False))))
        ctx = context()
        subject = WritebackSubject.of_checkout(
            EncounterRecord(consent=consent_for(ctx), context=ctx), _reverified(registry, ctx)
        )
        assert writeback_context(subject, registry) == WritebackRefused(
            WritebackRefusal.REVERIFICATION_REFUSED, NoteRefusal.NOTE_FINAL
        )

    def test_an_offline_reverification_is_not_verified(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path, transport=NoteTransport(note=status(503)))
        ctx = context()
        subject = WritebackSubject.of_checkout(
            EncounterRecord(consent=consent_for(ctx), context=ctx), _reverified(registry, ctx)
        )
        assert writeback_context(subject, registry) == WritebackRefused(
            WritebackRefusal.NOT_VERIFIED
        )

    def test_a_consent_that_names_another_note_is_refused(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        ctx = context()
        forged = WritebackSubject(
            consent=ConsentAttestation(confirmed_at=NOW, treatment_note_id=OTHER_NOTE),
            context=ctx,
            live=True,
        )
        assert writeback_context(forged, registry) == WritebackRefused(
            WritebackRefusal.CONSENT_MISMATCH
        )

    def test_the_note_target_type_refuses_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            NoteTarget(clinic_host=HOST, patient_id=PATIENT, note_id=NOTE, url="x")  # type: ignore[call-arg]
