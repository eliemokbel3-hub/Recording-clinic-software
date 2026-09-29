"""Shared fakes for the encounter / note-verification tests (Cliniko workflow
safeguards plan Phase 3). Every Cliniko answer comes from ``NoteTransport``
(no socket, ever) and every key from ``MemoryKeyStore`` (never Credential
Manager). Answers are shaped as Task P.1 found them on clinic 1."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scribe_desktop import cliniko_client as cc
from scribe_desktop.clinics import KEY_SECRET_NAME, ClinicRegistry
from scribe_desktop.encounter import (
    ConsentAttestation,
    EncounterContext,
    NoteTarget,
    Verification,
    VerificationRequest,
    linked_consent,
)

KEY = "MS0xMjM0NTY3ODkwLWZha2Uta2V5LWZvci10ZXN0cw-au2"
KEY_2 = "U2Vjb25kLWZha2Uta2V5LWZvci10aGUtc2FtZS1jbGluaWM-au2"
# The OTHER clinic's own key (codex round 22 PR-LOW-100): every clinic gets a
# distinct fake key, so a test can tell which clinic's credential was used.
OTHER_KEY = "T3RoZXItY2xpbmljLWZha2Uta2V5LWZvci10ZXN0cw-au2"
EMAIL = "practitioner@example-clinic.com.au"
CLINIC_ID = "0123456789abcdef"
OTHER_CLINIC_ID = "fedcba9876543210"
CLINIC_KEYS = {CLINIC_ID: KEY, OTHER_CLINIC_ID: OTHER_KEY}
HOST = "northside.au2.cliniko.com"
OTHER_HOST = "southside.au2.cliniko.com"
API = "https://api.au2.cliniko.com/v1"
PATIENT = "1001"
OTHER_PATIENT = "1002"
NOTE = "2001"
OTHER_NOTE = "2002"
PRACTITIONER = "7654321"
OTHER_PRACTITIONER = "7654322"
BOOKING = "3001"
TEMPLATE = "4001"
NOW = datetime(2026, 9, 27, 8, 0, tzinfo=UTC)


def target(
    host: str = HOST, patient_id: str = PATIENT, note_id: str = NOTE
) -> NoteTarget:
    return NoteTarget(clinic_host=host, patient_id=patient_id, note_id=note_id)


def ok(body: object) -> cc.RawResponse:
    return cc.RawResponse(status=200, rate_limit_reset=None, body=json.dumps(body).encode())


def status(code: int) -> cc.RawResponse:
    return cc.RawResponse(status=code, rate_limit_reset=None, body=b"")


def _link(resource: str, record_id: str) -> dict[str, Any]:
    return {"links": {"self": f"{API}/{resource}/{record_id}"}}


def note_body(**overrides: Any) -> dict[str, Any]:
    """An open draft as P.1 saw it: draft true, finalized_at null, links."""
    body: dict[str, Any] = {
        "id": NOTE,
        "draft": True,
        "finalized_at": None,
        "archived_at": None,
        "deleted_at": None,
        "patient": _link("patients", PATIENT),
        "practitioner": _link("practitioners", PRACTITIONER),
        "booking": _link("bookings", BOOKING),
        "treatment_note_template": _link("treatment_note_templates", TEMPLATE),
        "content": {"sections": []},
    }
    body.update(overrides)
    return body


PATIENT_BODY = {
    "id": PATIENT,
    "first_name": "Janet",
    "preferred_first_name": "Jan",
    "last_name": "Citizen",
    "archived_at": None,
}
BOOKING_BODY = {"id": BOOKING, "starts_at": "2026-09-27T00:30:00Z"}


class NoteTransport:
    """Answers the note, patient and booking reads by path prefix; records
    every request. An answer is a ``RawResponse``, an exception to raise, or
    a zero-argument callable."""

    def __init__(
        self,
        note: Any = None,
        patient: Any = None,
        booking: Any = None,
    ) -> None:
        self.routes: dict[str, Any] = {
            "/v1/treatment_notes/": note if note is not None else ok(note_body()),
            "/v1/patients/": patient if patient is not None else ok(PATIENT_BODY),
            "/v1/bookings/": booking if booking is not None else ok(BOOKING_BODY),
        }
        self.calls: list[tuple[str, str, str, dict[str, str]]] = []

    def request(
        self,
        method: str,
        host: str,
        path: str,
        headers: Mapping[str, str],
        max_body: int,
        *,
        body: bytes | None = None,
    ) -> cc.RawResponse:
        assert body is None, "note verification only reads"
        self.calls.append((method, host, path, dict(headers)))
        route = next(r for r in self.routes if path.startswith(r))
        answer = self.routes[route]
        if isinstance(answer, BaseException):
            raise answer
        if callable(answer):
            return answer()
        return answer


class MemoryKeyStore:
    def __init__(self) -> None:
        self.keys: dict[tuple[str, str], str] = {}
        self.reads = 0
        self.fail_read = False

    def store(self, clinic_id: str, secret_name: str, value: str) -> None:
        self.keys[(clinic_id, secret_name)] = value

    def retrieve(self, clinic_id: str, secret_name: str) -> str | None:
        self.reads += 1
        if self.fail_read:
            raise RuntimeError("backend unavailable")
        return self.keys.get((clinic_id, secret_name))

    def delete(self, clinic_id: str, secret_name: str) -> None:
        self.keys.pop((clinic_id, secret_name), None)


def clinic_record(
    clinic_id: str = CLINIC_ID,
    subdomain: str = "northside",
    practitioner_id: str = PRACTITIONER,
    *,
    confirmed: bool = True,
) -> dict[str, Any]:
    return {
        "clinic_id": clinic_id,
        "display_name": "Northside" if subdomain == "northside" else "Southside",
        "subdomain": subdomain,
        "shard": "au2",
        "user_id": "1234567",
        "practitioner_id": practitioner_id,
        "validated_at": "2026-09-27T07:00:00+00:00",
        "subdomain_confirmed": confirmed,
    }


def make_registry(
    tmp_path: Path,
    *records: dict[str, Any],
    transport: Any = None,
    storage: MemoryKeyStore | None = None,
) -> ClinicRegistry:
    """A registry holding ``records`` (default: Northside), each with its OWN
    key from ``CLINIC_KEYS`` (an unknown clinic id is a test error)."""
    records = records or (clinic_record(),)
    path = tmp_path / "clinics.json"
    path.write_text(
        json.dumps({"schema_version": 1, "contact_email": EMAIL, "clinics": list(records)}),
        encoding="utf-8",
    )
    store = storage if storage is not None else MemoryKeyStore()
    for record in records:
        store.store(record["clinic_id"], KEY_SECRET_NAME, CLINIC_KEYS[record["clinic_id"]])
    registry = ClinicRegistry(
        path,
        storage=store,
        transport=transport if transport is not None else NoteTransport(),
    )
    assert registry.load_problem is None
    return registry


def context(
    verification: Verification = Verification.VERIFIED, **overrides: Any
) -> EncounterContext:
    fields: dict[str, Any] = {
        "clinic_id": CLINIC_ID,
        "clinic_host": HOST,
        "patient_id": PATIENT,
        "treatment_note_id": NOTE,
        "booking_id": BOOKING,
        "practitioner_id": PRACTITIONER,
        "template_id": TEMPLATE,
        "verification": verification,
        "verified_at": NOW if verification is Verification.VERIFIED else None,
    }
    fields.update(overrides)
    return EncounterContext(**fields)


def consent_for(ctx: EncounterContext) -> ConsentAttestation:
    return linked_consent(ctx, NOW)


def request_for(
    registry: ClinicRegistry,
    note_target: NoteTarget | None = None,
    *,
    conn_gen: int = 1,
    seq: int = 1,
    clinic_id: str = CLINIC_ID,
) -> VerificationRequest:
    clinic = registry.record(clinic_id)
    assert clinic is not None
    return VerificationRequest(
        conn_gen=conn_gen,
        seq=seq,
        target=note_target if note_target is not None else target(),
        clinic=clinic,
        clinic_rev=registry.rev(clinic_id),
        contact_email=EMAIL,
    )
