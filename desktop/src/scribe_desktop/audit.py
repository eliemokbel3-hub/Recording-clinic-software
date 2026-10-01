"""The audit record (privacy-professional-controls plan Tasks 1.2 / 1.3;
D7, D8, D9; Critical Constraints C2 and C3).

One encrypted, CONTENT-FREE row per session, kept seven years from the
session's month, exportable as CSV. On-disk layout (D7), all under
``%LOCALAPPDATA%\\ClinikoScribe\\audit\\``:

- ``key.dpapi`` — ONE store key, DPAPI-wrapped with the description
  ``AUDIT_KEY_DESCRIPTION`` (``unwrap_key_from_file`` refuses a blob wrapped
  for any other store, so a session key can never open the audit and the
  audit key can never open a session);
- ``YYYY-MM\\<session id>.enc`` — one row, filed under its session's LOCAL
  calendar month, AES-GCM under the store key with
  the associated data ``audit:<session id>`` (a row renamed onto another id
  fails authentication), rewritten read -> change -> ``atomic_write_bytes``.

What a row can hold (C3), BY CONSTRUCTION rather than by a list of banned
fields: ``AuditRow`` is ``extra="forbid"`` and every string it carries is
pattern-constrained — Cliniko and clinic ids, the session id, fixed
``Literal`` outcome codes, a refusal CODE (``[a-z][a-z0-9_]*``) and model
TOKENS (``session_store.FACT_TOKEN_PATTERN``: no space, so no sentence).
There is no field for a patient name, a patient id, transcript or note
text. Named residue: a single token-shaped word passes the token pattern,
so what callers put in a token field is theirs to keep content-free — the
only producers are ``session_store.fact_token`` over persisted model and
provider names, and ``draft_write.WriteRefusal.name``.

Custody rules (C2): ``begin`` — the row Start writes — RAISES
``AuditWriteError`` (a ``SessionControllerError``: the Start refusal) when
the row cannot be written; the real write is the check. Every later change
goes through ``update``, which NEVER raises: a failure is counted
(``failure_count``) and logged as ``audit_update_failed`` with the stage
code only, and the custody action it describes goes ahead regardless.

Fail-closed store rules (D8, D9): a row of a NEWER schema is kept
byte-for-byte, never rewritten, counted as "newer format" and pruned only
with its month; an unreadable row is counted and never overwritten; an
unreadable, dead or missing key (with rows present) refuses every write
until ``reset`` quarantines the whole store under a never-used name and
starts a new one — nothing is ever deleted by a reset.

Threading: every method runs on the GUI thread (the controller's custody
calls, the main window's write steps, the sweep timer), like the stores it
records (C5)."""

from __future__ import annotations

import csv
import io
import json
import logging
import math
import os
import re
import secrets
import shutil
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
from pathlib import Path
from typing import Annotated, Any, Final, Literal

from cryptography.exceptions import InvalidTag
from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)

from scribe_desktop.encounter import ConsentAttestation, EncounterContext
from scribe_desktop.logging_setup import log_event
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import SessionControllerError
from scribe_desktop.session_store import (
    FACT_NONE,
    FACT_TOKEN_PATTERN,
    FACT_UNKNOWN,
    KEY_FILENAME,
    SESSION_ID_PATTERN,
    CompletionFacts,
    KeyCustodyError,
    StoreCorruptError,
    StoreWriteError,
    atomic_write_bytes,
    earliest_trusted_timestamp,
    key_blob_is_dead,
    link_state,
    read_capped,
    unwrap_key_from_file,
    validate_session_id,
    wrap_key_to_file,
)

AUDIT_DIRNAME: Final = "audit"
# D7: the store key's DPAPI description — distinct from every other store's.
AUDIT_KEY_DESCRIPTION: Final = "ClinikoScribe audit key"
AUDIT_SCHEMA_VERSION: Final = 1
RETENTION_YEARS: Final = 7
MAX_EVENTS: Final = 32
ROW_SUFFIX: Final = ".enc"
# D7 with local dates (round 6 MED-002): a local calendar month can end up to
# 12 h after the UTC month (UTC-12; east of UTC it ends before it), so the
# prune waits one day more.
_PRUNE_MARGIN: Final = timedelta(days=1)
# No session this app records can predate the audit record's plan (D8, round
# 7 LOW-004): an earlier creation time is untrusted for a pre-audit row.
_EARLIEST_SESSION: Final = datetime(2026, 1, 1, tzinfo=UTC).timestamp()
_MONTH_RE: Final = re.compile(r"^([0-9]{4})-([0-9]{2})$")  # ASCII digits only
# H3 round 35 SEC-005: a row is a few KiB (MAX_EVENTS bounds it); a larger file
# is not one of ours and is never read whole.
MAX_ROW_FILE_BYTES: Final = 64 * 1024
_SESSION_ID_RE: Final = re.compile(SESSION_ID_PATTERN)
_CODE_PATTERN: Final = r"^[a-z][a-z0-9_]{0,47}$"
_CLINIKO_ID_PATTERN: Final = r"^[1-9][0-9]{0,18}$"
_CLINIKO_ID_RE: Final = re.compile(_CLINIKO_ID_PATTERN)
# The quarantine a reset renames the store to (D9): never an existing name.
_QUARANTINE_TRIES: Final = 8

_Token = Annotated[str, StringConstraints(pattern=FACT_TOKEN_PATTERN)]
_Code = Annotated[str, StringConstraints(pattern=_CODE_PATTERN)]
_ClinikoId = Annotated[str, StringConstraints(pattern=_CLINIKO_ID_PATTERN)]
_ClinicId = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{16}$")]

DeletionState = Literal[
    "pending",
    "completed",
    "completed_without_note",
    "discarded",
    "expired",
    "orphan_gc",
    "start_failed",
]
PastSessionState = Literal["none", "archived", "not_kept_mock", "deleted_early", "expired"]
WriteOutcomeCode = Literal["attempting", "written", "refused", "unknown"]


def default_audit_root() -> Path:
    # No UNC refusal, exactly like the other custody roots (default_sessions_
    # root): a redirected LOCALAPPDATA is an accepted same-user residual.
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "ClinikoScribe" / AUDIT_DIRNAME


def _utc_now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Errors.
# ---------------------------------------------------------------------------

# The reasons a Start refusal names — authored words, never OS text (an OS
# error names a path). ``update`` failures are counted under the same codes.
# Public: the Past sessions tab maps an ``AuditUnavailable`` code to its line
# through this table, never through exception text.
AUDIT_REASONS: Final[dict[str, str]] = {
    "key_unreadable": (
        "its key cannot be read on this Windows account - "
        "start a new audit record on the Past sessions tab"
    ),
    "key_missing": (
        "its key is missing - start a new audit record on the Past sessions tab"
    ),
    "unavailable": "the audit folder could not be read",
    "write_failed": "the audit folder could not be written",
    "exists": "a row for this session already exists",
}


class AuditUnavailable(Exception):
    """The store cannot be used (``reason`` is an ``AUDIT_REASONS`` code).
    Raised by the reading methods (``rows``, ``export_csv``); ``begin`` turns
    it into ``AuditWriteError`` and ``update`` counts it."""

    def __init__(self, reason: str) -> None:
        super().__init__(AUDIT_REASONS.get(reason, reason))
        self.reason = reason


class AuditWriteError(SessionControllerError):
    """Start's row could not be written (C2, D12): Start is refused and
    nothing was recorded. A ``SessionControllerError``, so every screen shows
    its authored text (``custody_refusal_text``) and Chrome gets the existing
    ``failed`` refusal."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            f"the audit record could not be saved ({AUDIT_REASONS.get(reason, reason)}). "
            "Nothing was recorded."
        )
        self.reason = reason


AUDIT_RESET_REASONS: Final[dict[str, str]] = {
    "set_aside_failed": "the audit folder could not be set aside",
    "no_free_name": "no unused name was found for the old audit folder",
    "key_failed": "the new audit key could not be created",
}


class AuditResetError(Exception):
    """``reset`` could not quarantine the store or create the new key.
    Nothing was deleted either way. ``reason`` is an ``AUDIT_RESET_REASONS``
    code (round 16 follow-up: the Past sessions tab maps codes, never
    exception text)."""

    def __init__(self, reason: str) -> None:
        super().__init__(AUDIT_RESET_REASONS.get(reason, reason))
        self.reason = reason


# ---------------------------------------------------------------------------
# The row (D8).
# ---------------------------------------------------------------------------


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AuditModels(_Frozen):
    """The models and providers the session's artifacts record (D8) — the
    saved note's, then the generated note's (``generated_*``). Tokens only."""

    transcription_model: _Token = FACT_UNKNOWN
    speaker_model: _Token = FACT_UNKNOWN
    note_provider: _Token = FACT_NONE
    note_schema_version: _Token = FACT_NONE
    template_profile: _Token = FACT_NONE
    note_style: _Token = FACT_NONE
    language_model_id: _Token = FACT_NONE
    prompt_version: _Token = FACT_NONE
    generated_provider: _Token = FACT_UNKNOWN
    generated_style: _Token = FACT_UNKNOWN
    generated_language_model_id: _Token = FACT_UNKNOWN
    generated_prompt_version: _Token = FACT_UNKNOWN


class AuditWrite(_Frozen):
    """The Cliniko draft write, as ``write.enc`` last recorded it."""

    attempts: int = Field(default=0, ge=0)
    last_outcome: WriteOutcomeCode | None = None
    # The latest refusal's fixed CODE — a pre-send ``draft_write.WriteRefusal``
    # name or Cliniko's ``SendRefusal`` — never a display line.
    last_refusal: _Code | None = None
    written_at: AwareDatetime | None = None


class AuditDeletion(_Frozen):
    state: DeletionState = "pending"
    at: AwareDatetime | None = None


class AuditPastSession(_Frozen):
    state: PastSessionState = "none"
    at: AwareDatetime | None = None


class AuditEvent(_Frozen):
    at: AwareDatetime
    code: _Code


class AuditRow(_Frozen):
    """One session's audit row (D8). ``schema_version`` is read FIRST (the
    before-validator), so a newer row is never half-parsed into this one."""

    schema_version: Literal[1] = AUDIT_SCHEMA_VERSION
    session_id: str = Field(pattern=SESSION_ID_PATTERN)
    # The practitioner's LOCAL calendar date (round 6 MED-002); it names the
    # row's month folder. Every timestamp field is an aware UTC time.
    session_date: date
    origin: Literal["recorded", "pre_audit"]
    consent_confirmed_at: AwareDatetime | None = None
    consent_text_version: _Token | None = None
    linked: bool | None = None
    verification: Literal["verified", "unverified_offline", "unlinked"] | None = None
    clinic_id: _ClinicId | None = None
    practitioner_id: _ClinikoId | None = None
    user_id: _ClinikoId | None = None
    booking_id: _ClinikoId | None = None
    treatment_note_id: _ClinikoId | None = None
    models: AuditModels | None = None
    write: AuditWrite = AuditWrite()
    deletion: AuditDeletion = AuditDeletion()
    past_session: AuditPastSession = AuditPastSession()
    note_provenance: Literal["known", "unknown"] | None = None
    events: tuple[AuditEvent, ...] = Field(default=(), max_length=MAX_EVENTS)

    @model_validator(mode="before")
    @classmethod
    def _version_first(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("schema_version", AUDIT_SCHEMA_VERSION) != (
            AUDIT_SCHEMA_VERSION
        ):
            raise ValueError("not an audit row of this schema version")
        return data

    def to_bytes(self) -> bytes:
        return self.model_dump_json().encode("utf-8")

    def with_event(self, code: str, at: datetime, **update: Any) -> AuditRow:
        """This row with ``update`` applied and ``code`` appended to the
        events (the newest ``MAX_EVENTS`` kept), RE-VALIDATED — ``model_copy``
        alone skips validation."""
        events = (*self.events, AuditEvent(at=at, code=code))[-MAX_EVENTS:]
        return AuditRow.model_validate({**self.model_dump(), **update, "events": events})


class _Newer:
    """A row whose ``schema_version`` is newer than this build's (D8)."""


_NEWER: Final = _Newer()


def _row_aad(session_id: str) -> bytes:
    return b"audit:" + validate_session_id(session_id).encode("ascii")


def _decode(plaintext: bytes) -> AuditRow | _Newer:
    """A row, ``_NEWER`` for a newer schema, else ``ValueError`` (terse)."""
    try:
        data = json.loads(plaintext)
    except ValueError:
        data = None
    if isinstance(data, dict):
        version = data.get("schema_version")
        if isinstance(version, int) and not isinstance(version, bool) and version > (
            AUDIT_SCHEMA_VERSION
        ):
            return _NEWER
        try:
            return AuditRow.model_validate(data)
        except ValidationError:
            pass
    raise ValueError("not an audit row")  # outside the except: no chained detail


def _month_folder(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def month_prune_at(year: int, month: int) -> datetime:
    """When a month's rows may go (D7): the month's END (the first instant of
    the next month, UTC) plus ``RETENTION_YEARS``, plus ``_PRUNE_MARGIN`` —
    a row's month is its LOCAL calendar month (``session_date``), which can
    end up to 12 hours after the UTC one (UTC-12) — so every row in it is
    kept at least seven years from its session date in any zone."""
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    return datetime(next_year + RETENTION_YEARS, next_month, 1, tzinfo=UTC) + _PRUNE_MARGIN


def _local_date(moment: datetime, zone: tzinfo | None) -> date:
    """The practitioner's calendar date of ``moment`` (round 6 MED-002):
    ``zone``, or this computer's own zone when None — never the UTC date,
    which is the previous day for every morning session east of UTC."""
    return moment.astimezone(zone).date()


def _date_from_epoch(created_at: float | None, now: datetime, zone: tzinfo | None) -> date:
    """A ``pre_audit`` row's date (D8): the session's trusted creation time,
    else — missing, non-finite, in the future, or before any session this
    app records could exist (``_EARLIEST_SESSION``: a corrupt header or a
    reset clock, round 7 LOW-004 — a 1970 row would be pruned at once) —
    ``now``; the local date either way."""
    stamp = None
    if created_at is not None and math.isfinite(created_at) and created_at >= _EARLIEST_SESSION:
        stamp = earliest_trusted_timestamp([created_at], now.timestamp())
    moment = datetime.fromtimestamp(stamp, UTC) if stamp is not None else now
    return _local_date(moment, zone)


# ---------------------------------------------------------------------------
# Row changes — each returns the row to write (``update`` writes nothing when
# a change returns the row unchanged).
# ---------------------------------------------------------------------------

Change = Callable[[AuditRow, datetime], AuditRow]


def _start_failed(row: AuditRow, now: datetime) -> AuditRow:
    return _deleted("start_failed")(row, now)


def _still_open(row: AuditRow, state: DeletionState) -> bool:
    """Whether ``state`` may still end ``row``: only a ``pending`` one — or a
    ``start_failed`` one, whose cleanup can itself have failed and left a
    recoverable session behind (round 7 LOW-003: D6's "Complete, not the
    earlier failure, decides"). A Start failure only ever ends a ``pending``
    row."""
    if state == "start_failed":
        return row.deletion.state == "pending"
    return row.deletion.state in ("pending", "start_failed")


def _deleted(state: DeletionState) -> Change:
    """The session's end, recorded ONLY while the row is still open
    (``_still_open``): an expiry or an ``orphan_gc`` of a directory a
    Complete already ended (its removal failed) never overwrites that
    Complete."""

    def change(row: AuditRow, now: datetime) -> AuditRow:
        if not _still_open(row, state):
            return row
        return row.with_event(state, now, deletion=AuditDeletion(state=state, at=now))

    return change


def _completed(facts: CompletionFacts, state: DeletionState) -> Change:
    def change(row: AuditRow, now: datetime) -> AuditRow:
        if not _still_open(row, state):
            return row
        # Built HERE, inside ``update``'s guard (round 6 LOW-001): a fact the
        # model refuses is a counted failure, never a raise after the key is
        # gone. Every model field is read from the fact of the same name, so
        # a fact a later task adds cannot be silently left out.
        models = AuditModels(
            **{name: getattr(facts, name) for name in AuditModels.model_fields}
        )
        return row.with_event(
            state,
            now,
            models=models,
            deletion=AuditDeletion(state=state, at=now),
            past_session=AuditPastSession(state=facts.past_session, at=now),
            note_provenance=facts.note_provenance,
        )

    return change


PastSessionEvent = Literal["archived", "deleted_early", "expired"]

# The Past-sessions outcomes recorded after the Complete (Tasks 3.1 / 3.2), and
# the states each may replace: a reconciled commit only fills a row the
# Complete never reached (round 12 LOW-002 — a crash between the key deletion
# and the audit update); a deletion follows an entry that existed. A row that
# already reads a deletion, or ``not_kept_mock``, is never rewritten.
_PAST_SESSION_FROM: Final[dict[str, frozenset[str]]] = {
    "archived": frozenset({"none"}),
    "deleted_early": frozenset({"none", "archived"}),
    "expired": frozenset({"none", "archived"}),
}


def _past_session_recorded(state: PastSessionEvent) -> Change:
    def change(row: AuditRow, now: datetime) -> AuditRow:
        if row.past_session.state not in _PAST_SESSION_FROM[state]:
            return row
        return row.with_event(
            f"past_session_{state}", now, past_session=AuditPastSession(state=state, at=now)
        )

    return change


def _write_recorded(
    attempt: int, outcome: WriteOutcomeCode, finished_at: datetime | None, refusal: str | None
) -> Change:
    def change(row: AuditRow, now: datetime) -> AuditRow:
        written_at = finished_at if outcome == "written" else row.write.written_at
        # Round 6 LOW-006: Cliniko's refusal (a fixed ``SendRefusal`` code)
        # is the latest refusal, as a pre-send one is.
        last_refusal = refusal if outcome == "refused" and refusal else row.write.last_refusal
        write = AuditWrite(
            attempts=attempt,
            last_outcome=outcome,
            last_refusal=last_refusal,
            written_at=written_at,
        )
        if write == row.write:
            return row
        return row.with_event(f"write_{outcome}", now, write=write.model_dump())

    return change


def _write_refused(code: str) -> Change:
    def change(row: AuditRow, now: datetime) -> AuditRow:
        write = row.write.model_copy(update={"last_refusal": code})
        return row.with_event("write_refusal", now, write=write.model_dump())

    return change


# ---------------------------------------------------------------------------
# The store.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditListing:
    """``rows``' answer: the readable rows (oldest month first), and how
    many were of a newer format or unreadable (D8 — counted, never shown as
    rows and never rewritten)."""

    rows: tuple[AuditRow, ...]
    newer: int = 0
    unreadable: int = 0


class AuditLog:
    """The audit store (D7). Construction touches nothing on disk."""

    def __init__(
        self,
        root: Path | None = None,
        *,
        logger: logging.Logger | None = None,
        clock: Callable[[], datetime] = _utc_now,
        local_zone: tzinfo | None = None,
    ) -> None:
        self._root = root if root is not None else default_audit_root()
        self._logger = logger
        self._clock = clock
        # The zone a row's ``session_date`` is the calendar date in: None is
        # this computer's own (tests inject one).
        self._zone = local_zone
        self._failures = 0

    @property
    def root(self) -> Path:
        return self._root

    @property
    def failure_count(self) -> int:
        """How many ``update`` calls (and prunes) failed since start — C2's
        "counted and shown"."""
        return self._failures

    # --- the Start row (C2: the one write that refuses) --------------------

    def begin(
        self,
        session_id: str,
        *,
        consent: ConsentAttestation,
        context: EncounterContext | None,
        user_id: str | None,
        started_at: datetime,
    ) -> None:
        """Write the new session's row BEFORE anything of the session exists
        (Flow 1). ``AuditWriteError`` when it cannot be written — the key
        unreadable or missing, the folder unwritable, a row for the id
        already present — and nothing of the row is left behind."""
        now = self._clock()
        if user_id is not None and not _CLINIKO_ID_RE.fullmatch(user_id):
            user_id = None  # an id the registry could not vouch for is left out
        try:
            row = AuditRow(
                session_id=session_id,
                session_date=_local_date(started_at, self._zone),
                origin="recorded",
                consent_confirmed_at=consent.confirmed_at,
                consent_text_version=consent.text_version,
                linked=context is not None,
                verification=(
                    context.verification.value if context is not None else "unlinked"
                ),
                clinic_id=context.clinic_id if context is not None else None,
                practitioner_id=context.practitioner_id if context is not None else None,
                user_id=user_id if context is not None else None,
                booking_id=context.booking_id if context is not None else None,
                treatment_note_id=context.treatment_note_id if context is not None else None,
                events=(AuditEvent(at=now, code="started"),),
            )
        except (ValidationError, ValueError, OverflowError, OSError):
            # Round 7 LOW-005: a local-time conversion the platform refuses is
            # the same authored refusal as a row the schema refuses.
            raise AuditWriteError("write_failed") from None
        try:
            crypto = self._open_key()
        except AuditUnavailable as exc:
            raise AuditWriteError(exc.reason) from None
        try:
            existing = self._find(session_id)
        except OSError:
            crypto.destroy()
            raise AuditWriteError("unavailable") from None
        if existing:
            crypto.destroy()
            raise AuditWriteError("exists")
        path = self._root / _month_folder(row.session_date) / f"{session_id}{ROW_SUFFIX}"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if link_state(path.parent) is not False:
                # H3 round 35 SEC-003: a linked (or uninspectable) month
                # folder is never written through.
                raise AuditWriteError("unavailable")
            sealed = crypto.encrypt(row.to_bytes(), _row_aad(session_id))
            atomic_write_bytes(path, sealed, error_label="audit row")
        except (OSError, StoreWriteError):
            raise AuditWriteError("write_failed") from None
        finally:
            crypto.destroy()

    # --- best-effort changes (C2: never raise) ------------------------------

    def update(
        self,
        session_id: str,
        change: Change,
        *,
        stage: str,
        created_at: float | None = None,
    ) -> bool:
        """Apply ``change`` to the session's row and write it back. NEVER
        raises: any failure — the key, the folder, an unreadable or newer row
        (both left byte-for-byte), a change the row schema refuses — is
        counted and logged (``audit_update_failed``, ``detail_code=stage``)
        and False returned; the caller's custody action is unaffected.

        A session with no row (started before the audit existed) gets a
        ``pre_audit`` row, dated by ``created_at`` (``session_created_at``,
        read by the caller before the directory went) or, when that is
        missing or untrusted, by now (D8). The store is resolved PER CALL
        (every path and the key are looked up again), so nothing bound at
        construction can go stale."""
        try:
            self._update(session_id, change, created_at)
        except Exception:  # noqa: BLE001 - C2: an audit failure never blocks custody
            self._count_failure(stage)
            return False
        return True

    def record_start_failed(self, session_id: str) -> bool:
        """Flow 1 step 5: every Start failure after ``begin``."""
        return self.update(session_id, _start_failed, stage="start_failed")

    def record_completion(
        self,
        session_id: str,
        facts: CompletionFacts,
        *,
        deletion: Literal["completed", "completed_without_note"],
        created_at: float | None = None,
    ) -> bool:
        """A Complete (any of the five paths): its models, the deletion and
        the Past-sessions outcome, from ``complete_session``'s facts."""
        return self.update(
            session_id, _completed(facts, deletion), stage="completion", created_at=created_at
        )

    def record_deletion(
        self,
        session_id: str,
        state: Literal["discarded", "expired", "orphan_gc"],
        *,
        created_at: float | None = None,
    ) -> bool:
        """A Discard, an expiry or an ``orphan_gc`` — recorded only while the
        row still reads ``pending``."""
        return self.update(session_id, _deleted(state), stage=state, created_at=created_at)

    def record_past_session(
        self, session_id: str, state: PastSessionEvent, *, created_at: float | None = None
    ) -> bool:
        """A Past-sessions outcome after the Complete: ``archived`` for an
        entry ``reconcile_pending`` committed (round 12 LOW-002),
        ``deleted_early`` for the tab's Delete now, ``expired`` for the
        retention sweep (Tasks 3.1 / 3.2) — each only over the states
        ``_PAST_SESSION_FROM`` allows. ``created_at`` dates a ``pre_audit``
        row (D8)."""
        return self.update(
            session_id,
            _past_session_recorded(state),
            stage=f"past_session_{state}",
            created_at=created_at,
        )

    def record_write(
        self,
        session_id: str,
        *,
        attempt: int,
        outcome: WriteOutcomeCode,
        finished_at: datetime | None,
        refusal: str | None = None,
        created_at: float | None = None,
    ) -> bool:
        """A durable ``write.enc`` transition (Task 1.4): the attempt
        number, its outcome, — once ``written`` — when, and a ``refused``
        one's fixed code. ``created_at`` dates a ``pre_audit`` row (D8)."""
        return self.update(
            session_id,
            _write_recorded(attempt, outcome, finished_at, refusal),
            stage="write",
            created_at=created_at,
        )

    def record_write_refusal(
        self, session_id: str, code: str, *, created_at: float | None = None
    ) -> bool:
        """A pre-send refusal's FIXED code (``WriteRefusal.name``);
        ``created_at`` dates a ``pre_audit`` row (D8)."""
        return self.update(
            session_id, _write_refused(code), stage="write_refusal", created_at=created_at
        )

    # --- reading, pruning, export -----------------------------------------

    def rows(self) -> AuditListing:
        """Every readable row, oldest month first. ``AuditUnavailable`` when
        the key cannot be used (with rows present)."""
        if not self._has_rows():
            return AuditListing(())
        crypto = self._open_key()
        rows: list[AuditRow] = []
        newer = unreadable = 0
        try:
            for path in self._row_paths():
                decoded = self._read(path, crypto)
                if isinstance(decoded, AuditRow):
                    rows.append(decoded)
                elif decoded is _NEWER:
                    newer += 1
                else:
                    unreadable += 1
        except OSError:
            # Round 7 LOW-006: a month folder that cannot be listed is the
            # documented refusal, never a raw OS error (it names a path).
            raise AuditUnavailable("unavailable") from None
        finally:
            crypto.destroy()
        return AuditListing(tuple(rows), newer, unreadable)

    def row_for(self, session_id: str) -> AuditRow | None:
        """ONE session's readable row — the Past sessions tab's write-outcome
        line (Task 3.1) — decrypting that row only. None when there is no
        row (or no store yet), or it is unreadable or of a newer format (D8:
        counted by ``rows``, never shown); ``AuditUnavailable`` when the key
        cannot be used, or when the id has more than one row (round 16
        LOW-006: ``update`` refuses that state too — it is never "no
        record"). Creates nothing."""
        validate_session_id(session_id)
        try:
            crypto = self._open_key(create=False)
        except _NoKey:
            return None
        try:
            found = self._find(session_id)
            if len(found) > 1:
                raise AuditUnavailable("unavailable")
            decoded = self._read(found[0], crypto) if found else None
        except OSError:
            raise AuditUnavailable("unavailable") from None
        finally:
            crypto.destroy()
        return decoded if isinstance(decoded, AuditRow) else None

    def prune(self) -> int:
        """Remove every month folder whose ``month_prune_at`` has passed (D7)
        — newer and unreadable rows go with their month, nothing else is
        touched, no key is needed. Returns the folders removed; NEVER raises
        (a failure is counted under ``prune``, as ``update``'s are)."""
        now = self._clock()
        removed = 0
        try:
            for folder in self._month_folders():
                match = _MONTH_RE.fullmatch(folder.name)
                if match is None:
                    continue
                year, month = int(match.group(1)), int(match.group(2))
                if not 1 <= month <= 12:
                    continue
                try:
                    prune_at = month_prune_at(year, month)
                except (ValueError, OverflowError):
                    continue  # a year no date can hold (round 6 LOW-009): not ours
                if now < prune_at:
                    continue
                try:
                    shutil.rmtree(folder)
                    removed += 1
                except OSError:
                    self._count_failure("prune")
        except Exception:  # noqa: BLE001 - never raises into start-up or the timer
            self._count_failure("prune")
        return removed

    def export_csv(self, path: Path) -> int:
        """Write every readable row to ``path`` as CSV (UTF-8 with a BOM, for
        Excel) and return how many. Every cell passes the formula guard
        (``csv_cell``). ``AuditUnavailable`` when the key cannot be used;
        ``StoreWriteError`` when the file cannot be written."""
        listing = self.rows()
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\r\n")
        writer.writerow(CSV_COLUMNS)
        for row in listing.rows:
            writer.writerow([csv_cell(value) for value in _csv_values(row)])
        _write_export(path, buffer.getvalue().encode("utf-8-sig"))
        return len(listing.rows)

    # --- the unreadable-key reset (D9) --------------------------------------

    def key_unreadable(self) -> bool:
        """True when Starts are refused for the key (unreadable, dead, or
        missing with rows present) — the Past sessions tab then offers
        "Start a new audit record" (``reset``)."""
        try:
            self._open_key(create=False).destroy()
        except AuditUnavailable as exc:
            return exc.reason in {"key_unreadable", "key_missing"}
        except _NoKey:
            return False
        return False

    def reset(self) -> Path | None:
        """D9: rename the WHOLE store to a new, never-existing
        ``audit.unreadable-<YYYYMMDD-HHMMSS>-<8 hex>`` beside it (nothing is
        deleted; an existing quarantine is never overwritten or reused), then
        create a fresh key. Returns the quarantine, or None when there was no
        store. ``AuditResetError`` when the rename fails (nothing changed) or
        the new key cannot be created (the store is then ABSENT — the next
        Start or reset creates a fresh one, and every quarantine stays
        untouched)."""
        quarantine: Path | None = None
        if self._root.exists():
            stamp = self._clock().astimezone(UTC).strftime("%Y%m%d-%H%M%S")
            for _ in range(_QUARANTINE_TRIES):
                candidate = self._root.with_name(
                    f"{self._root.name}.unreadable-{stamp}-{secrets.token_hex(4)}"
                )
                if candidate.exists():
                    continue
                try:
                    os.rename(self._root, candidate)  # refuses an existing target
                except FileExistsError:
                    continue
                except OSError as exc:
                    raise AuditResetError("set_aside_failed") from exc
                quarantine = candidate
                break
            else:
                raise AuditResetError("no_free_name")
        crypto = SessionCrypto()
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            wrap_key_to_file(crypto, self._root, description=AUDIT_KEY_DESCRIPTION)
        except Exception as exc:  # noqa: BLE001 - DPAPI raises pywintypes.error (not OSError)
            try:
                self._root.rmdir()  # only ever the EMPTY folder made just now
            except OSError:
                pass
            raise AuditResetError("key_failed") from exc
        finally:
            crypto.destroy()
        return quarantine

    # --- internals ---------------------------------------------------------

    def _count_failure(self, stage: str) -> None:
        self._failures += 1
        if self._logger is not None:
            try:
                log_event(self._logger, "audit_update_failed", detail_code=stage)
            except Exception:  # noqa: BLE001 - counting must not raise either
                pass

    def _update(self, session_id: str, change: Change, created_at: float | None) -> None:
        validate_session_id(session_id)
        now = self._clock()
        crypto = self._open_key()
        try:
            found = self._find(session_id)
            if len(found) > 1:
                raise AuditUnavailable("unavailable")
            if found:
                path = found[0]
                current = self._read(path, crypto)
                if not isinstance(current, AuditRow):
                    # D8: a newer or unreadable row is never overwritten.
                    raise AuditUnavailable("unavailable")
            else:
                current = AuditRow(
                    session_id=session_id,
                    session_date=_date_from_epoch(created_at, now, self._zone),
                    origin="pre_audit",
                )
                path = self._root / _month_folder(current.session_date) / (
                    f"{session_id}{ROW_SUFFIX}"
                )
            changed = change(current, now)
            if changed == current and found:
                return
            if (changed.session_id, changed.session_date) != (
                current.session_id,
                current.session_date,
            ):
                raise ValueError("a change may not move a row")
            changed = AuditRow.model_validate_json(changed.to_bytes())  # re-validated
            path.parent.mkdir(parents=True, exist_ok=True)
            if link_state(path.parent) is not False:
                raise AuditUnavailable("unavailable")  # SEC-003, as ``begin``
            sealed = crypto.encrypt(changed.to_bytes(), _row_aad(session_id))
            atomic_write_bytes(path, sealed, error_label="audit row")
        finally:
            crypto.destroy()

    def _read(self, path: Path, crypto: SessionCrypto) -> AuditRow | _Newer | None:
        """The row at ``path``, ``_NEWER``, or None when it is unreadable
        (unauthentic — including a row moved onto another id — or not a
        row)."""
        session_id = path.name[: -len(ROW_SUFFIX)]
        try:
            blob = read_capped(path, MAX_ROW_FILE_BYTES)
            plaintext = crypto.decrypt(blob, _row_aad(session_id))
            decoded = _decode(plaintext)
        except (OSError, StoreCorruptError, InvalidTag, ValueError):
            return None
        if isinstance(decoded, AuditRow) and decoded.session_id != session_id:
            return None
        return decoded

    def _month_folders(self) -> Iterator[Path]:
        try:
            children = sorted(self._root.iterdir())
        except FileNotFoundError:
            return
        for child in children:
            # H3 round 35 SEC-003: a linked (or uninspectable) month folder is
            # never read, written or pruned — it is not one this store made.
            if (
                _MONTH_RE.fullmatch(child.name)
                and link_state(child) is False
                and child.is_dir()
            ):
                yield child

    def _row_paths(self) -> Iterator[Path]:
        for folder in self._month_folders():
            for path in sorted(folder.iterdir()):
                name = path.name
                if (
                    name.endswith(ROW_SUFFIX)
                    and _SESSION_ID_RE.fullmatch(name[: -len(ROW_SUFFIX)])
                    and path.is_file()
                ):
                    yield path

    def _find(self, session_id: str) -> list[Path]:
        name = f"{validate_session_id(session_id)}{ROW_SUFFIX}"
        return [
            folder / name for folder in self._month_folders() if (folder / name).is_file()
        ]

    def _has_rows(self) -> bool:
        try:
            return next(self._row_paths(), None) is not None
        except OSError:
            raise AuditUnavailable("unavailable") from None

    def _open_key(self, *, create: bool = True) -> SessionCrypto:
        """The store key, unwrapped (the caller destroys it). A missing key
        is created — only when NO row exists (a missing key beside rows would
        orphan them: refused, ``key_missing``). A dead or unwrappable key is
        ``key_unreadable`` (D9); an uninspectable one ``unavailable``."""
        key_path = self._root / KEY_FILENAME
        try:
            size: int | None = key_path.stat().st_size
        except FileNotFoundError:
            size = None
        except OSError:
            raise AuditUnavailable("unavailable") from None
        if size is None:
            if self._has_rows():
                raise AuditUnavailable("key_missing")
            if not create:
                raise _NoKey()
            crypto = SessionCrypto()
            try:
                self._root.mkdir(parents=True, exist_ok=True)
                wrap_key_to_file(crypto, self._root, description=AUDIT_KEY_DESCRIPTION)
            except Exception:  # noqa: BLE001 - DPAPI raises pywintypes.error (not OSError)
                crypto.destroy()
                raise AuditUnavailable("write_failed") from None
            return crypto
        if key_blob_is_dead(size):
            raise AuditUnavailable("key_unreadable")
        try:
            return unwrap_key_from_file(self._root, description=AUDIT_KEY_DESCRIPTION)
        except KeyCustodyError as exc:
            # Round 7 LOW-007: a blob that could not be READ (antivirus or a
            # backup holding the file) is a passing ``unavailable`` — never
            # ``key_unreadable``, which offers D9's reset.
            if isinstance(exc.__cause__, OSError):
                raise AuditUnavailable("unavailable") from None
            raise AuditUnavailable("key_unreadable") from None
        except RuntimeError:
            raise AuditUnavailable("key_unreadable") from None


class _NoKey(Exception):
    """``_open_key(create=False)`` found no key and no rows: a fresh store."""


# ---------------------------------------------------------------------------
# CSV (Flow 5's Export CSV).
# ---------------------------------------------------------------------------

CSV_COLUMNS: Final[tuple[str, ...]] = (
    "session_id",
    "session_date",
    "origin",
    "consent_confirmed_at",
    "consent_text_version",
    "linked",
    "verification",
    "clinic_id",
    "practitioner_id",
    "user_id",
    "booking_id",
    "treatment_note_id",
    *(f"models.{name}" for name in AuditModels.model_fields),
    "write.attempts",
    "write.last_outcome",
    "write.last_refusal",
    "write.written_at",
    # One convention for a nested field: ``<part>.<field>`` (round 7 LOW-017).
    "deletion.state",
    "deletion.at",
    "past_session.state",
    "past_session.at",
    "note_provenance",
)

# Characters a spreadsheet may read as the start of a formula.
_FORMULA_LEADS: Final = ("=", "+", "-", "@", "\t", "\r")


def csv_cell(value: object) -> str:
    """One CSV cell: empty for None, ISO text for a time, and a leading
    apostrophe on anything a spreadsheet could read as a formula."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        text = value.astimezone(UTC).isoformat()
    elif isinstance(value, bool):
        text = "yes" if value else "no"
    else:
        text = str(value)
    return "'" + text if text.startswith(_FORMULA_LEADS) else text


def _csv_values(row: AuditRow) -> list[object]:
    models = row.models
    model_values: list[object] = [
        getattr(models, name) if models is not None else None
        for name in AuditModels.model_fields
    ]
    return [
        row.session_id,
        row.session_date.isoformat(),
        row.origin,
        row.consent_confirmed_at,
        row.consent_text_version,
        row.linked,
        row.verification,
        row.clinic_id,
        row.practitioner_id,
        row.user_id,
        row.booking_id,
        row.treatment_note_id,
        *model_values,
        row.write.attempts,
        row.write.last_outcome,
        row.write.last_refusal,
        row.write.written_at,
        row.deletion.state,
        row.deletion.at,
        row.past_session.state,
        row.past_session.at,
        row.note_provenance,
    ]


def _write_export(path: Path, blob: bytes) -> None:
    """``atomic_write_bytes``' temp + fsync + ``os.replace`` for a file in a
    folder the USER chose (H3 round 35 SEC-004): the temp file is a fresh
    ``mkstemp`` name, so an existing ``<name>.tmp`` of theirs is never
    overwritten or deleted. ``StoreWriteError`` (terse) when the temp file
    cannot be made, written or moved into place; no partial file is left at
    ``path``. The temp file is removed on every path, except when Windows
    refuses that removal too — the ``OSError`` then propagates and the temp
    file (``.clinic-scribe-*.tmp``) stays; the tab reads either error as its
    one export-failed line."""
    try:
        handle, tmp_name = tempfile.mkstemp(
            dir=path.parent, prefix=".clinic-scribe-", suffix=".tmp"
        )
    except OSError:
        raise StoreWriteError("failed writing audit export") from None
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(blob)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_path, path)
    except OSError:
        raise StoreWriteError("failed writing audit export") from None
    finally:
        tmp_path.unlink(missing_ok=True)
