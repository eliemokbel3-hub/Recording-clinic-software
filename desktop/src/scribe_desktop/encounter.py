"""The encounter a recording belongs to, its consent, and note verification.

Cliniko workflow safeguards plan, Tasks 3.1 (the types, D3), 3.2 (note
verification, D4), 3.3's ``encounter.enc`` record (D11) and 3.5 (the
write-back guard, Constraint 6).

TYPES (D3). ``EncounterContext`` names the Cliniko note a session is bound to
(ids only — the clinic, its web host, the patient, the treatment note, the
optional booking and template, the practitioner — and how it was verified).
``ConsentAttestation`` records the practitioner's consent tick: when, which
text version, and the practitioner and note it was given for (absent note
means an UNLINKED recording). Both are frozen and refuse extra fields.
``bind_consent`` is THE consent-to-context rule, applied by
``RecordingSession`` and ``EncounterRecord`` alike: an unlinked consent
carries no note, a linked one names exactly the context's note and, when it
names a practitioner, the context's practitioner. Display strings (the
patient's name, the appointment time) are never a field of either: they
travel separately as ``NoteDisplay``, in memory only.

VERIFICATION (D4) is split by thread, like the clinic registry's Validate:
``VerificationLedger`` (GUI thread) turns each context report into at most
one ``VerificationRequest`` and applies results; ``verify_note_context``
(worker thread) makes ONE Cliniko client call — the key read once from
Credential Manager — and never raises. The ledger applies a result only when
it answers the CURRENT connection's current bound report (same connection
generation, same target, the report run it was dispatched for) and the
clinic's ``clinic_rev`` has not moved; everything else is dropped without
touching the target, the display strings or Start eligibility.

THE WRITE-BACK GUARD (Constraint 6). ``writeback_context`` is the only way
to a write target: it returns a ``VerifiedTarget`` or a named refusal, over a
live session or a checked-out session's decrypted encounter, and in both
cases only on a current re-verification of that note. This module has no
write method: the draft write is ``draft_write.py``'s, which takes its
target from ``writeback_context``.

This module never logs. No error or refusal it produces carries a key, an id
or answer text: a refusal is a reason code.
"""

from __future__ import annotations

import re
import time
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Final, Literal, Protocol

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    StringConstraints,
    ValidationError,
    model_validator,
)

from scribe_desktop.clinics import KEY_SECRET_NAME, ClinicRecord, KeyStore, parse_clinic_address
from scribe_desktop.cliniko_client import (
    CertificateRejected,
    ClinikoCall,
    ClinikoClient,
    ClinikoError,
    CredentialsRejected,
    InvalidKey,
    NotFound,
    RateLimited,
    Transport,
    Unreachable,
    check_id,
)
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import SessionStoreError, read_encounter, write_encounter

RECORDING_CONSENT_TEXT_VERSION: Final = "recording-consent-v1"
# PLAN.md Flow 2 step 4, verbatim. Distinct from the learning consent
# (``ui/models.py`` ``CONSENT_TEXT_V3``): this one is given per recording.
RECORDING_CONSENT_TEXT: Final = (
    "I confirm the patient has consented to AI-assisted recording and documentation"
)
ENCOUNTER_SCHEMA_VERSION: Final = 1
_ID_PATTERN: Final = r"^[1-9][0-9]{0,18}$"
_CLINIC_ID_PATTERN: Final = r"^[0-9a-f]{16}$"
# Display strings are bounded and single-line before they leave this module.
MAX_DISPLAY_NAME_CHARS: Final = 120
# D4's per-note throttle: how long a VERIFIED outcome is reused for a new
# report run of the same note on the same connection and clinic rev.
VERIFIED_REUSE_SECONDS: Final = 60.0


def _clinic_host(value: str) -> str:
    """A clinic's web host exactly as the registry spells it."""
    if parse_clinic_address(value).host != value:
        raise ValueError("not a canonical Cliniko web host")
    return value


_ClinikoId = Annotated[str, StringConstraints(pattern=_ID_PATTERN)]
_ClinicId = Annotated[str, StringConstraints(pattern=_CLINIC_ID_PATTERN)]
_ClinicHost = Annotated[str, AfterValidator(_clinic_host)]


class Verification(StrEnum):
    """How a linked context was established at Start (D4). A named refusal
    never becomes a context, so it has no member here."""

    VERIFIED = "verified"
    UNVERIFIED_OFFLINE = "unverified_offline"


class EncounterContext(BaseModel):
    """The Cliniko note a session is bound to (D3). Ids only."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    clinic_id: _ClinicId
    clinic_host: _ClinicHost
    patient_id: _ClinikoId
    treatment_note_id: _ClinikoId
    booking_id: _ClinikoId | None = None
    practitioner_id: _ClinikoId
    template_id: _ClinikoId | None = None
    verification: Verification
    verified_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def _verified_at_matches(self) -> EncounterContext:
        if (self.verification is Verification.VERIFIED) != (self.verified_at is not None):
            raise ValueError("verified_at is set exactly when the context is verified")
        return self

    @property
    def target(self) -> NoteTarget:
        return NoteTarget(
            clinic_host=self.clinic_host,
            patient_id=self.patient_id,
            note_id=self.treatment_note_id,
        )


class ConsentAttestation(BaseModel):
    """PLAN.md's consent record for ONE recording (D3)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    confirmed_at: AwareDatetime
    text_version: Literal["recording-consent-v1"] = RECORDING_CONSENT_TEXT_VERSION
    practitioner_id: _ClinikoId | None = None
    # Absent: the recording is unlinked.
    treatment_note_id: _ClinikoId | None = None


def bind_consent(consent: ConsentAttestation, context: EncounterContext | None) -> None:
    """THE consent-to-context rule (``ValueError`` when it fails): an
    unlinked consent names no note; a linked one names the context's note
    and, if it names a practitioner, the context's practitioner."""
    if context is None:
        if consent.treatment_note_id is not None:
            raise ValueError("a consent naming a note needs that note's context")
        return
    if consent.treatment_note_id != context.treatment_note_id:
        raise ValueError("the consent was given for another note")
    if consent.practitioner_id is not None and consent.practitioner_id != context.practitioner_id:
        raise ValueError("the consent was given by another practitioner")


def unlinked_consent(now: datetime | None = None) -> ConsentAttestation:
    """The consent a desktop Start records (no Cliniko note)."""
    return ConsentAttestation(confirmed_at=now if now is not None else datetime.now(UTC))


def linked_consent(context: EncounterContext, now: datetime | None = None) -> ConsentAttestation:
    """The consent a linked Start records, bound to ``context``'s note."""
    return ConsentAttestation(
        confirmed_at=now if now is not None else datetime.now(UTC),
        practitioner_id=context.practitioner_id,
        treatment_note_id=context.treatment_note_id,
    )


class EncounterRecord(BaseModel):
    """What ``encounter.enc`` holds (D11): the consent, and the context when
    the session is linked. Serialised by this module, encrypted by
    ``session_store`` under the session key with its own associated data."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = ENCOUNTER_SCHEMA_VERSION
    consent: ConsentAttestation
    context: EncounterContext | None = None

    @model_validator(mode="after")
    def _bound(self) -> EncounterRecord:
        bind_consent(self.consent, self.context)
        return self

    def to_bytes(self) -> bytes:
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_bytes(cls, blob: bytes) -> EncounterRecord:
        """``EncounterUnavailable`` for anything that is not this schema
        (terse on purpose: pydantic's detail would echo ids)."""
        try:
            return cls.model_validate_json(blob)
        except (ValidationError, ValueError):
            pass
        raise EncounterUnavailable()  # outside the except: no chained detail


class EncounterUnavailable(Exception):
    """``encounter.enc`` is missing, cannot be decrypted, or is not the
    schema. The session is treated as UNLINKED for write-back (D11) and the
    consent record as unavailable."""

    def __init__(self) -> None:
        super().__init__("the encounter record is unavailable")


def write_encounter_record(
    session_dir: Path, crypto: SessionCrypto, session_id: str, record: EncounterRecord
) -> Path:
    return write_encounter(session_dir, crypto, session_id, record.to_bytes())


def read_encounter_record(
    session_dir: Path, crypto: SessionCrypto, session_id: str
) -> EncounterRecord:
    """Decrypt and parse ``encounter.enc`` (Critical Constraint 7) — only
    from its three authorised callers: a recovery CHECKOUT
    (``ui/main_window.py``), an Unreviewed recording opened for review
    (``SessionController.adopt_queued``) and the once-per-session
    reminder rebuild at app start (``ui.models.reconstruct_reminder_entries``);
    never the recovery listing, the sweep or a refresh (round 59
    PR-LOW-320). ``EncounterUnavailable`` when it is missing, unauthentic or
    not the schema."""
    try:
        plaintext = read_encounter(session_dir, crypto, session_id)
    except (SessionStoreError, ValueError):
        plaintext = None
    if plaintext is None:
        raise EncounterUnavailable()
    return EncounterRecord.from_bytes(plaintext)


# --- note targets and outcomes ------------------------------------------------


class NoteTarget(BaseModel):
    """What a context report names: an allow-listed web host, the patient
    and the treatment note from the page URL."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    clinic_host: _ClinicHost
    patient_id: _ClinikoId
    note_id: _ClinikoId


@dataclass(frozen=True)
class NoteDisplay:
    """Display strings, returned beside a verified context and NEVER
    persisted or logged. ``appointment_starts_at`` is UTC (the panel renders
    local time); None when the note links no booking."""

    patient_display_name: str
    appointment_starts_at: datetime | None


class NoteRefusal(StrEnum):
    """Why a note did not verify (Start is refused and the reason shown)."""

    CLINIC_NOT_SET_UP = "clinic_not_set_up"
    CLINIC_MISMATCH = "clinic_mismatch"
    PATIENT_MISMATCH = "patient_mismatch"
    NOTE_FINAL = "note_final"
    NOTE_ARCHIVED = "note_archived"
    WRONG_PRACTITIONER = "wrong_practitioner"
    NOTE_NOT_FOUND = "note_not_found"
    KEY_REJECTED = "key_rejected"
    KEY_UNAVAILABLE = "key_unavailable"
    CERTIFICATE_REJECTED = "certificate_rejected"
    ANSWER_UNREADABLE = "answer_unreadable"


@dataclass(frozen=True)
class Verified:
    context: EncounterContext
    display: NoteDisplay = field(repr=False)


@dataclass(frozen=True)
class UnverifiedOffline:
    """Cliniko could not be asked (a connection error, timeout, 5xx or 429):
    recording is allowed, write-back is blocked (D4). ``rate_limited``: the
    answer was a 429, or the shared ``RateLimitLatch``'s cooldown after one
    answered without a call — the bridge's (round 57 SEC-009) or the
    checkout's (draft-write D13)."""

    context: EncounterContext
    rate_limited: bool = False


@dataclass(frozen=True)
class NoteRefused:
    reason: NoteRefusal


VerificationOutcome = Verified | UnverifiedOffline | NoteRefused


@dataclass(frozen=True)
class VerificationRequest:
    """One dispatched verification. ``conn_gen`` and ``seq`` identify the
    report run it answers; ``clinic_rev`` is the clinic's rev at dispatch.
    No key: the worker reads it from Credential Manager."""

    conn_gen: int
    seq: int
    target: NoteTarget
    clinic: ClinicRecord
    clinic_rev: int
    contact_email: str


@dataclass(frozen=True)
class VerificationResult:
    request: VerificationRequest
    outcome: VerificationOutcome


# --- Cliniko's answers, as Task P.1 found them --------------------------------
# EVERY assumption this module makes about a treatment note's, patient's or
# booking's answer lives in this block. P.1 ran on clinic 1 (2026-09-27);
# clinic 2 is owed.
#
# (a) ``GET /treatment_notes/<id>`` carries ``draft`` (a JSON boolean) and
#     ``finalized_at`` (null while open) — CONFIRMED (clinic 1). A note is
#     open only when ``draft`` is true AND ``finalized_at`` is null.
#     ``archived_at`` and ``deleted_at`` are present and null on an open note
#     (CONFIRMED); an archived note answered 404 (CONFIRMED) — a set value is
#     refused here too.
# (b) The note's ``patient``, ``practitioner``, ``booking`` and
#     ``treatment_note_template`` are objects whose ``links.self`` is the
#     linked record's API URL, ending ``/<id>`` — CONFIRMED (clinic 1: the
#     patient link matched the URL's patient, the practitioner link the key
#     user's practitioner record). The URL is read as
#     ``https://<host>.cliniko.com/v1/<resource>/<id>``; ``patients`` and
#     ``practitioners`` are the documented resource names (not printed by
#     P.1); the booking and template resource names are not checked. A
#     booking link may be absent (P.1 run 1) — ``booking_id`` stays optional.
# (c) ``GET /patients/<id>`` carries ``first_name``, ``last_name`` and
#     ``preferred_first_name`` — CONFIRMED present (clinic 1), for display.
# (d) ``GET /bookings/<id>`` carries ``starts_at`` as a string — CONFIRMED
#     present (clinic 1); read as ISO 8601 UTC, for display.

_LINK_RE: Final = re.compile(
    r"https://[a-z0-9.-]+\.cliniko\.com/v1/(?P<resource>[a-z_]+)/(?P<id>[1-9][0-9]{0,18})"
)


class AnswerShapeError(Exception):
    """An answer did not have the shape the P.1 block expects. Public (round
    10 LOW-003) because ``link_id`` and ``note_state`` are: a caller catches
    this by name, never a bare ``Exception`` that would hide its own bugs."""


def link_id(note: Mapping[str, Any], name: str, resource: str | None) -> str | None:  # (b)
    """The id in a note link's ``self`` URL (``resource`` checked when
    given); None for an absent link. Raises ``AnswerShapeError`` on any other
    shape. Public for the draft write's note read (draft-write Task 1.1)."""
    value = note.get(name)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise AnswerShapeError()
    links = value.get("links")
    url = links.get("self") if isinstance(links, dict) else None
    if not isinstance(url, str):
        raise AnswerShapeError()
    match = _LINK_RE.fullmatch(url)
    if match is None or (resource is not None and match.group("resource") != resource):
        raise AnswerShapeError()
    return check_id(match.group("id"))


def note_state(note: Mapping[str, Any]) -> NoteRefusal | None:  # (a)
    """None for an open draft; ``NOTE_FINAL`` / ``NOTE_ARCHIVED`` otherwise.
    Raises ``AnswerShapeError`` on a note without ``draft`` /
    ``finalized_at``. Public for the draft write's note read (draft-write
    Task 1.1)."""
    draft = note.get("draft")
    if not isinstance(draft, bool) or "finalized_at" not in note:
        raise AnswerShapeError()
    if not draft or note["finalized_at"] is not None:
        return NoteRefusal.NOTE_FINAL
    if note.get("archived_at") is not None or note.get("deleted_at") is not None:
        return NoteRefusal.NOTE_ARCHIVED
    return None


def display_text(value: object) -> str:
    """Display text as plain single-line text: control and format characters
    — and a lone surrogate, which a JSON escape can produce and no UTF-8
    snapshot can carry (H1 round 53 LOW-044) — become spaces, whitespace is
    collapsed; a non-string is "". Never markup-interpreted — the UI renders
    it as text (D1). The ONE cleaner: the bridge's snapshot text uses it too
    (H2a SIMP-008)."""
    if not isinstance(value, str):
        return ""
    cleaned = "".join(
        " " if unicodedata.category(ch) in {"Cc", "Cf", "Cs", "Zl", "Zp"} else ch
        for ch in value
    )
    return " ".join(cleaned.split())


def _patient_name(patient: Mapping[str, Any]) -> str:  # (c)
    first = display_text(patient.get("preferred_first_name")) or display_text(
        patient.get("first_name")
    )
    name = " ".join(part for part in (first, display_text(patient.get("last_name"))) if part)
    return name[:MAX_DISPLAY_NAME_CHARS] or "Unnamed patient"


def _starts_at(booking: Mapping[str, Any]) -> datetime | None:  # (d)
    value = booking.get("starts_at")
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo is not None else None


# --- the worker ----------------------------------------------------------------


def _refusal_for(error: ClinikoError) -> NoteRefusal | None:
    """None: an offline class (``unverified_offline``)."""
    if isinstance(error, (Unreachable, RateLimited)):
        return None
    if isinstance(error, (CredentialsRejected, InvalidKey)):
        return NoteRefusal.KEY_REJECTED
    if isinstance(error, NotFound):
        return NoteRefusal.NOTE_NOT_FOUND
    if isinstance(error, CertificateRejected):
        return NoteRefusal.CERTIFICATE_REJECTED
    # Malformed, RedirectRefused, UnexpectedStatus.
    return NoteRefusal.ANSWER_UNREADABLE


def _offline_context(request: VerificationRequest) -> EncounterContext:
    target = request.target
    return EncounterContext(
        clinic_id=request.clinic.clinic_id,
        clinic_host=target.clinic_host,
        patient_id=target.patient_id,
        treatment_note_id=target.note_id,
        practitioner_id=request.clinic.practitioner_id,
        verification=Verification.UNVERIFIED_OFFLINE,
    )


# Cliniko's rate limit (round 57 SEC-009, practitioner decision 2026-09-28):
# after a 429 a clinic's calls are refused WITHOUT a request for this long —
# a fixed window from the 429; only a real 429 starts one.
RATE_LIMIT_COOLDOWN_SECONDS: Final = 60.0


class RateLimitLatch:
    """THE 429 cooldown (draft-write D13), one per app, owned by the main
    window and shared by D13's three paths: the bridge's note checks, the
    checkout re-verification and the draft write. A 429 recorded by any of
    them cools the clinic for all of them. The Clinics tab's Validate /
    Replace key is NOT one of them (it predates this latch, is an explicit
    click, and names its own 429 as ``ClinicRefusal.RATE_LIMITED``).

    Qt-free and GUI-thread only (it holds no lock); every caller reads and
    records on ``clock`` (never a clock of its own, round 9 LOW-012).
    Spacing between calls is NOT here: it stays the bridge's own timer, for
    bursts of Chrome reports."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._until: dict[str, float] = {}

    @property
    def clock(self) -> Callable[[], float]:
        return self._clock

    def cooling(self, clinic_id: str, now: float) -> float | None:
        """Seconds of the clinic's cooldown left at ``now``, or None when it
        is not cooling."""
        until = self._until.get(clinic_id)
        if until is None or now >= until:
            return None
        return until - now

    def record_429(self, clinic_id: str, now: float) -> None:
        """A real 429 at ``now``: the clinic cools until ``now`` plus
        ``RATE_LIMIT_COOLDOWN_SECONDS`` (never shortened by an older one)."""
        until = now + RATE_LIMIT_COOLDOWN_SECONDS
        self._until[clinic_id] = max(until, self._until.get(clinic_id, until))


def rate_limited_result(request: VerificationRequest) -> VerificationResult:
    """The answer recorded WITHOUT a call while the request's clinic is in
    the cooldown after a 429 (round 57 SEC-009): ``unverified_offline``, as
    the 429 itself was."""
    return VerificationResult(
        request=request,
        outcome=UnverifiedOffline(_offline_context(request), rate_limited=True),
    )


class _KeyUnavailable(Exception):
    pass


def verify_note_context(
    request: VerificationRequest,
    *,
    key_store: KeyStore,
    transport: Transport | None = None,
    clock: Callable[[], datetime] | None = None,
) -> VerificationResult:
    """Worker thread: D4's check as ONE client call. Never raises.

    One ``GET /treatment_notes/<id>``: the note's patient link must equal
    the URL's patient, the note must be an open draft, and its practitioner
    link must equal the clinic's practitioner. Then ``GET /patients/<id>``
    and the linked booking, for display only. A connection error, timeout,
    5xx or 429 anywhere is ``unverified_offline``; every other failure is a
    named refusal."""
    outcome: VerificationOutcome
    try:
        outcome = _verify(request, key_store, transport, clock)
    except _KeyUnavailable:
        outcome = NoteRefused(NoteRefusal.KEY_UNAVAILABLE)
    except ClinikoError as error:
        reason = _refusal_for(error)
        outcome = (
            UnverifiedOffline(
                _offline_context(request), rate_limited=isinstance(error, RateLimited)
            )
            if reason is None
            else NoteRefused(reason)
        )
    except Exception:  # noqa: BLE001 - AnswerShapeError, InvalidId, the unforeseen: never raise
        outcome = NoteRefused(NoteRefusal.ANSWER_UNREADABLE)
    # Only the outcome leaves: the exception, whose frames hold the key
    # (threat-model Cliniko residue (6)), goes with its block.
    return VerificationResult(request=request, outcome=outcome)


def _verify(
    request: VerificationRequest,
    key_store: KeyStore,
    transport: Transport | None,
    clock: Callable[[], datetime] | None,
) -> VerificationOutcome:
    clinic = request.clinic
    target = request.target
    if clinic.host != target.clinic_host:
        return NoteRefused(NoteRefusal.CLINIC_MISMATCH)
    client = ClinikoClient(contact_email=request.contact_email, transport=transport)

    def read_key() -> str | None:
        try:
            key = key_store.retrieve(clinic.clinic_id, KEY_SECRET_NAME)
        except Exception as exc:  # noqa: BLE001 - keyring backends raise their own types
            raise _KeyUnavailable() from exc
        if not key:
            raise _KeyUnavailable()
        return key

    with client.call(read_key) as call:
        return _check_note(call, request, clock)


def _check_note(
    call: ClinikoCall, request: VerificationRequest, clock: Callable[[], datetime] | None
) -> VerificationOutcome:
    clinic = request.clinic
    target = request.target
    note = call.get_treatment_note(target.note_id)
    state = note_state(note)
    patient_id = link_id(note, "patient", "patients")
    practitioner_id = link_id(note, "practitioner", "practitioners")
    if patient_id is None or practitioner_id is None:
        raise AnswerShapeError()
    if patient_id != target.patient_id:
        return NoteRefused(NoteRefusal.PATIENT_MISMATCH)
    if state is not None:
        return NoteRefused(state)
    if practitioner_id != clinic.practitioner_id:
        return NoteRefused(NoteRefusal.WRONG_PRACTITIONER)
    booking_id = link_id(note, "booking", None)
    template_id = link_id(note, "treatment_note_template", None)
    patient = call.get_patient(target.patient_id)
    starts_at: datetime | None = None
    if booking_id is not None:
        # The booking is display only (D4): a deleted one leaves no time
        # shown, never a "note not found" refusal (round 57 SEC-011). Any
        # other failure still refuses or goes offline, as before.
        try:
            starts_at = _starts_at(call.get_booking(booking_id))
        except NotFound:
            starts_at = None
    now = clock() if clock is not None else datetime.now(UTC)
    context = EncounterContext(
        clinic_id=clinic.clinic_id,
        clinic_host=target.clinic_host,
        patient_id=target.patient_id,
        treatment_note_id=target.note_id,
        booking_id=booking_id,
        practitioner_id=practitioner_id,
        template_id=template_id,
        verification=Verification.VERIFIED,
        verified_at=now,
    )
    return Verified(context, NoteDisplay(_patient_name(patient), starts_at))


# --- the GUI-thread ledger ---------------------------------------------------------


class ClinicDirectory(Protocol):
    """The registry surface verification needs (``ClinicRegistry``)."""

    @property
    def records(self) -> tuple[ClinicRecord, ...]: ...

    @property
    def contact_email(self) -> str | None: ...

    def record(self, clinic_id: str) -> ClinicRecord | None: ...

    def rev(self, clinic_id: str) -> int: ...

    def confirm_subdomain_from_note(
        self, clinic_id: str, host: str, expected_rev: int
    ) -> bool: ...


class StartRefusal(StrEnum):
    """Why a linked Start was refused before it reached the controller."""

    NO_REPORT = "no_report"
    TARGET_MISMATCH = "target_mismatch"
    CHECKING = "checking"
    NOT_VERIFIED = "not_verified"


@dataclass(frozen=True)
class StartRefused:
    reason: StartRefusal
    # Set when the bound report's verification was a named refusal.
    note_refusal: NoteRefusal | None = None


@dataclass
class _Run:
    """The current bound report: consecutive reports of one target on one
    connection. ``seq_start`` identifies the run a verification answers."""

    seq_start: int
    seq_latest: int
    target: NoteTarget | None
    clinic_id: str | None = None
    clinic_rev: int = 0
    outcome: VerificationOutcome | None = None


@dataclass(frozen=True)
class _RecentVerified:
    conn_gen: int
    clinic_id: str
    clinic_rev: int
    outcome: Verified
    at: float


class VerificationLedger:
    """GUI thread: the latest context report and its verification (D4).

    ``new_connection`` bumps ``conn_gen`` (the app's own count, never sent to
    Chrome) and clears the bound report, so Start needs a fresh report on
    the new connection. ``report`` records a report (``seq`` restarts per
    connection; a ``seq`` at or below the latest is a replay and ignored).
    Consecutive reports of the SAME target continue one run and share its
    one verification; a report of another target starts a new run and, for
    a registered host, dispatches a new verification. The per-note throttle
    (D4, round 20 LOW-016): a new run for a note VERIFIED within the last
    ``VERIFIED_REUSE_SECONDS`` on this connection, under the clinic's current
    ``clinic_rev``, reuses that outcome with no call — so switching between
    two notes' tabs does not re-check each on every switch. Refusals and
    offline outcomes are never reused (the next run checks again).
    ``accept`` applies a result only when its ``conn_gen`` is current, its
    target is the run's, it was dispatched for this run (``seq`` = the run's
    first), and the clinic still exists at the same ``clinic_rev``; anything
    else is dropped whole. Outcomes are re-checked against the clinic's rev
    when read, so Replace key and Remove (which bump it) void them;
    ``reverify_after_clinic_change`` dispatches afresh."""

    def __init__(
        self, clinics: ClinicDirectory, *, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._clinics = clinics
        self._clock = clock
        self._conn_gen = 0
        self._run: _Run | None = None
        self._recent: dict[NoteTarget, _RecentVerified] = {}

    @property
    def conn_gen(self) -> int:
        return self._conn_gen

    def new_connection(self) -> int:
        self._conn_gen += 1
        self._run = None
        self._recent.clear()
        return self._conn_gen

    def report(self, seq: int, target: NoteTarget | None) -> VerificationRequest | None:
        run = self._run
        if run is not None and seq <= run.seq_latest:
            return None  # replayed or out of order
        if run is not None and target is not None and target == run.target:
            run.seq_latest = seq
            return None
        self._run = _Run(seq_start=seq, seq_latest=seq, target=target)
        return self._dispatch(self._run)

    def _prune_recent(self) -> None:
        """Drop reuse entries past the window, so a reused outcome's display
        strings are held no longer than the throttle needs them."""
        now = self._clock()
        expired = [
            key
            for key, recent in self._recent.items()
            if not 0 <= now - recent.at <= VERIFIED_REUSE_SECONDS
        ]
        for key in expired:
            del self._recent[key]

    def _dispatch(self, run: _Run) -> VerificationRequest | None:
        self._prune_recent()
        target = run.target
        if target is None:
            return None
        clinic = next((r for r in self._clinics.records if r.host == target.clinic_host), None)
        email = self._clinics.contact_email
        if clinic is None or email is None:
            run.clinic_id = None
            run.outcome = NoteRefused(NoteRefusal.CLINIC_NOT_SET_UP)
            return None
        run.clinic_id = clinic.clinic_id
        run.clinic_rev = self._clinics.rev(clinic.clinic_id)
        run.outcome = None
        recent = self._recent.get(target)
        if (
            recent is not None
            and recent.conn_gen == self._conn_gen
            and recent.clinic_id == run.clinic_id
            and recent.clinic_rev == run.clinic_rev
            and 0 <= self._clock() - recent.at <= VERIFIED_REUSE_SECONDS
        ):
            run.outcome = recent.outcome  # the per-note throttle: no call
            return None
        return VerificationRequest(
            conn_gen=self._conn_gen,
            seq=run.seq_start,
            target=target,
            clinic=clinic,
            clinic_rev=run.clinic_rev,
            contact_email=email,
        )

    def _current_clinic(self, clinic_id: str, rev: int) -> ClinicRecord | None:
        record = self._clinics.record(clinic_id)
        if record is None or self._clinics.rev(clinic_id) != rev:
            return None
        return record

    def _is_run_request(self, request: VerificationRequest) -> bool:
        """``request`` is the one the current run dispatched, under its
        clinic's current rev — the guard ``accept`` and ``awaits`` share."""
        run = self._run
        return not (
            run is None
            or request.conn_gen != self._conn_gen
            or request.seq != run.seq_start
            or request.target != run.target
            or run.clinic_id != request.clinic.clinic_id
            or run.clinic_rev != request.clinic_rev
            or self._current_clinic(request.clinic.clinic_id, request.clinic_rev) is None
        )

    def awaits(self, request: VerificationRequest) -> bool:
        """A WAITING check is still wanted: it is the current run's request
        and the run has no outcome yet. Checked before a waiting check starts
        (codex round 65 PR-LOW-350), so a tab that closed or moved on — to a
        page that is no note, a note reused from the throttle, another clinic
        or one not set up — or a clinic change leaves no call behind; its
        answer would only have been dropped by ``accept``."""
        run = self._run
        return run is not None and run.outcome is None and self._is_run_request(request)

    def accept(self, result: VerificationResult) -> bool:
        request = result.request
        run = self._run
        if run is None or not self._is_run_request(request):
            return False
        run.outcome = result.outcome
        if isinstance(result.outcome, Verified):
            self._recent[request.target] = _RecentVerified(
                conn_gen=request.conn_gen,
                clinic_id=request.clinic.clinic_id,
                clinic_rev=request.clinic_rev,
                outcome=result.outcome,
                at=self._clock(),
            )
            record = self._clinics.record(request.clinic.clinic_id)
            if record is not None and not record.subdomain_confirmed:
                # D10: the first note verified with this key on this host
                # confirms a typed subdomain (a no-op if the rev moved).
                self._clinics.confirm_subdomain_from_note(
                    record.clinic_id, request.target.clinic_host, request.clinic_rev
                )
        return True

    def bound_target(self) -> NoteTarget | None:
        return self._run.target if self._run is not None else None

    def outcome(self) -> VerificationOutcome | None:
        """The bound report's outcome; None while checking, with no report,
        or when its clinic's rev has moved since it was dispatched."""
        run = self._run
        if run is None or run.outcome is None:
            return None
        clinic_id = run.clinic_id
        if clinic_id is not None and self._current_clinic(clinic_id, run.clinic_rev) is None:
            return None
        return run.outcome

    def reverify_after_clinic_change(self) -> VerificationRequest | None:
        """After a Replace key or Remove (``ClinicsScreen.clinics_changed``):
        when the bound report's clinic rev moved, dispatch afresh under the
        current key (a pending result from the old rev is dropped by
        ``accept``)."""
        run = self._run
        if run is None or run.target is None:
            return None
        if run.clinic_id is not None and self._current_clinic(run.clinic_id, run.clinic_rev):
            return None
        return self._dispatch(run)

    def start_context(self, target: NoteTarget) -> EncounterContext | StartRefused:
        """The context a linked Start may record: the bound report must be
        for ``target`` and verified or ``unverified_offline`` (D2)."""
        run = self._run
        if run is None or run.target is None:
            return StartRefused(StartRefusal.NO_REPORT)
        if run.target != target:
            return StartRefused(StartRefusal.TARGET_MISMATCH)
        outcome = self.outcome()
        if outcome is None:
            if run.outcome is not None:
                return StartRefused(StartRefusal.NOT_VERIFIED)  # its clinic changed
            return StartRefused(StartRefusal.CHECKING)
        if isinstance(outcome, NoteRefused):
            return StartRefused(StartRefusal.NOT_VERIFIED, outcome.reason)
        return outcome.context


def reverification_request(
    context: EncounterContext, clinics: ClinicDirectory, *, seq: int, conn_gen: int = 0
) -> VerificationRequest | None:
    """D4's re-verification of a session's stored note: the same check, for
    the stored target, under the clinic's CURRENT key and rev. None when the
    clinic is gone (or has no contact email): the session cannot count as
    linked. ``conn_gen`` 0 marks a checkout request (Task 3.4 — it answers no
    pipe report); the Chrome bridge passes the pipe connection it re-checks
    a linked live session for (Task 4.5). ``seq`` is the caller's own
    number for the request."""
    clinic = clinics.record(context.clinic_id)
    email = clinics.contact_email
    if clinic is None or email is None:
        return None
    return VerificationRequest(
        conn_gen=conn_gen,
        seq=seq,
        target=context.target,
        clinic=clinic,
        clinic_rev=clinics.rev(clinic.clinic_id),
        contact_email=email,
    )


# --- the write-back guard (Task 3.5) -----------------------------------------------


class WritebackRefusal(StrEnum):
    """Why write-back is refused (Constraint 6). Each names its cause."""

    CONSENT_UNAVAILABLE = "consent_unavailable"
    UNLINKED = "unlinked"
    CONSENT_MISMATCH = "consent_mismatch"
    CLINIC_GONE = "clinic_gone"
    CLINIC_CHANGED = "clinic_changed"
    NOT_VERIFIED = "not_verified"
    NOT_REVERIFIED = "not_reverified"
    REVERIFICATION_STALE = "reverification_stale"
    REVERIFICATION_REFUSED = "reverification_refused"
    CONTEXT_CHANGED = "context_changed"


@dataclass(frozen=True)
class WritebackRefused:
    reason: WritebackRefusal
    note_refusal: NoteRefusal | None = None


@dataclass(frozen=True)
class VerifiedTarget:
    """The one shape Phase 4's write accepts: ids only, from a
    re-verification whose clinic has kept its ``clinic_rev`` (no Replace key
    or Remove since) and its practitioner up to the moment of the guard."""

    clinic_id: str
    clinic_host: str
    patient_id: str
    treatment_note_id: str
    practitioner_id: str
    booking_id: str | None
    template_id: str | None


@dataclass(frozen=True)
class WritebackSubject:
    """What write-back is asked about. ``live`` is a live session's own
    consent and context; otherwise a checked-out (recovered or Unreviewed)
    session's DECRYPTED ``encounter.enc`` — ``consent`` and ``context`` None
    when it was missing or undecryptable. ``reverification`` is the D4
    result for this session's note, required on both paths."""

    consent: ConsentAttestation | None
    context: EncounterContext | None
    live: bool
    reverification: VerificationResult | None = None

    @classmethod
    def of_live(
        cls,
        consent: ConsentAttestation,
        context: EncounterContext | None,
        reverification: VerificationResult | None = None,
    ) -> WritebackSubject:
        return cls(consent, context, live=True, reverification=reverification)

    @classmethod
    def of_checkout(
        cls, record: EncounterRecord | None, reverification: VerificationResult | None
    ) -> WritebackSubject:
        if record is None:
            return cls(None, None, live=False, reverification=reverification)
        return cls(record.consent, record.context, live=False, reverification=reverification)


def _same_note(a: EncounterContext, b: EncounterContext) -> bool:
    return (a.clinic_id, a.clinic_host, a.patient_id, a.treatment_note_id, a.practitioner_id) == (
        b.clinic_id,
        b.clinic_host,
        b.patient_id,
        b.treatment_note_id,
        b.practitioner_id,
    )


def writeback_context(
    subject: WritebackSubject, clinics: ClinicDirectory
) -> VerifiedTarget | WritebackRefused:
    """Phase 4's only entry to a write target (Constraint 6). Refused, by
    name, unless the session is linked, its consent names its note, its
    clinic still exists with the same host and practitioner, and a
    re-verification of that same note, dispatched under the clinic's
    CURRENT ``clinic_rev``, came back verified — for a live session and a
    checked-out one alike (D4: Phase 4 re-verifies before the write). A
    verification made at Start, or stored in ``encounter.enc``, is never
    trusted alone: a Replace key or Remove since then (D9) moved the rev
    (round 20 MED-012)."""
    consent, context = subject.consent, subject.context
    if consent is None:
        return WritebackRefused(WritebackRefusal.CONSENT_UNAVAILABLE)
    if context is None:
        return WritebackRefused(WritebackRefusal.UNLINKED)
    try:
        bind_consent(consent, context)
    except ValueError:
        return WritebackRefused(WritebackRefusal.CONSENT_MISMATCH)
    clinic = clinics.record(context.clinic_id)
    if clinic is None:
        return WritebackRefused(WritebackRefusal.CLINIC_GONE)
    if clinic.host != context.clinic_host or clinic.practitioner_id != context.practitioner_id:
        return WritebackRefused(WritebackRefusal.CLINIC_CHANGED)
    result = subject.reverification
    if result is None:
        if subject.live and context.verification is not Verification.VERIFIED:
            return WritebackRefused(WritebackRefusal.NOT_VERIFIED)
        return WritebackRefused(WritebackRefusal.NOT_REVERIFIED)
    request = result.request
    if (
        request.clinic.clinic_id != context.clinic_id
        or request.target != context.target
        or request.clinic_rev != clinics.rev(context.clinic_id)
    ):
        return WritebackRefused(WritebackRefusal.REVERIFICATION_STALE)
    outcome = result.outcome
    if isinstance(outcome, NoteRefused):
        return WritebackRefused(WritebackRefusal.REVERIFICATION_REFUSED, outcome.reason)
    if isinstance(outcome, UnverifiedOffline):
        return WritebackRefused(WritebackRefusal.NOT_VERIFIED)
    if not _same_note(outcome.context, context):
        return WritebackRefused(WritebackRefusal.CONTEXT_CHANGED)
    verified = outcome.context
    return VerifiedTarget(
        clinic_id=verified.clinic_id,
        clinic_host=verified.clinic_host,
        patient_id=verified.patient_id,
        treatment_note_id=verified.treatment_note_id,
        practitioner_id=verified.practitioner_id,
        booking_id=verified.booking_id,
        template_id=verified.template_id,
    )
