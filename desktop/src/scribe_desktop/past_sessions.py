"""The Past-sessions archive (privacy-professional-controls plan Task 2.2;
D1, D3, D5, D6, D13; Critical Constraints C1 and C4).

At every non-mock Complete the app keeps, encrypted, the session's
transcript, its saved note and its generated note — and audio only for a
recording kept under written development consent (plan-development-
recordings D5/D6); the archive's first key-under-key. On-disk
layout (D1 / D3), all under ``%LOCALAPPDATA%\\ClinikoScribe\\past_sessions\\``
(``ClinikoScribe-dev`` from a source checkout — ``install_layout``):

- ``<session id>\\`` — ONE entry per session id, holding the SAME filenames
  a session holds, so the existing readers (``read_transcript``,
  ``read_note``, ``read_generated``) work unchanged — re-encrypted byte for
  byte under a FRESH per-entry key:

  - ``key.dpapi`` — the entry's own key, DPAPI-wrapped with the description
    ``PAST_SESSION_KEY_DESCRIPTION`` (``unwrap_key_from_file`` refuses a
    blob wrapped for any other store, so no session, audit or profile key
    opens an entry and an entry key opens nothing else). Deleting it is the
    entry's cryptographic deletion (Delete now, expiry — D3);
  - ``label.enc`` — the ``PastSessionLabel`` (dates, the recording kind,
    the clinic id, the patient's name or None, what the entry holds), with
    the associated data ``past-label:<session id>``;
  - ``transcript.enc`` (no associated data, as in a session), ``note.enc``
    (no associated data) and ``generated.enc`` (``generated:<session id>``)
    — the SOURCE-DERIVED set (D6): the transcript always, the others when
    the completed session held them;
  - ``pending`` — a content-free marker the entry is PUBLISHED with and
    keeps until its Complete has deleted the source key (C1);
  - for a KEPT recording only (development-recordings plan D5/D6):
    ``audio.enc`` — the session chunk-store format under a FRESH audio key —
    and ``audio-key.enc``, that key's 32 bytes encrypted under the ENTRY key
    with the associated data ``past-audio-key:<session id>``. Deleting
    ``key.dpapi`` therefore destroys the audio too, on any build; Delete
    recording zeroes ``audio-key.enc`` in place, then unlinks it and
    ``audio.enc`` — the recording's two files alone. "Kept"
    is both files present and the key file not all zeros (``recording_kept``
    — no decryption).

- ``.staging\\<session id>\\`` — where an entry is built and verified before
  it is moved into place; ``clean_staging`` removes whatever a crash left
  there, at every start-up and sweep tick, whatever the retention setting.

- ``exports.enc`` + ``exports-key.dpapi`` (development-recordings plan Task
  3.3) — the EXPORT LEDGER, outside every entry: each export in flight (the
  chosen folder and the created ``<session id>.wav.part`` file's identity),
  so ``recover_exports`` (first at every start-up) deletes a partial
  plaintext file a hard kill left. The exported ``<session id>.wav`` itself
  is the practitioner's to delete; the app never touches it again.

The lifecycle (C1). ``write_entry`` stages the entry, FULLY verifies it
through its own key read back from disk (the exact file set, every
plaintext's SHA-256 against the source bytes, and the existing readers),
then replaces any earlier entry for the id key-first and moves it into place
— all BEFORE the Complete deletes the source key, so any failure keeps the
key and the Complete can be retried. An entry carrying ``pending`` whose
source ``sessions\\<id>\\key.dpapi`` still exists is PENDING: never listed.
Every NON-Complete destroyer of a source session (Discard, the recovery
list's Discard, expiry, a dead key's ``orphan_gc``) calls
``remove_pending_entry`` BEFORE it deletes the source key, so a ``pending``
entry whose source key is gone can only follow a Complete that reached its
key deletion — and ``commit`` (inside the Complete) or ``reconcile_pending``
(start-up and every sweep tick, on a CONFIRMED-absent source key only)
removes its marker.

What this store never holds: audio not kept under development consent (C4
— the source session's key, which also encrypted the session's
``audio.enc``, is still deleted; a kept recording is RE-encrypted under its
own key), the source key, or an audit id. The patient's name lives only in
``label.enc``.

Threading: every method runs on the GUI thread (the controller's custody
calls under its lock, the sweep timer), like the stores it sits beside
(C5) — with one exception: a Discard that waits for live transcription to
stop runs the controller's ``discard`` off the GUI thread (installation plan
round 40 LOW-002), and so ``remove_pending_entry`` with it, under the
controller's lock; such a session is still live, so it has no entry or
staging copy to remove (hardening review round 41 LOW-004). Nothing here
touches the network.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import shutil
import stat
import unicodedata
from collections.abc import Callable, Generator, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final, Literal, Protocol

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from scribe_desktop import install_layout
from scribe_desktop.logging_setup import log_event
from scribe_desktop.note import GeneratedNote
from scribe_desktop.note_config import (
    NoteConfigError,
    _write_config_file,
    default_config_root,
)
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import (
    AUDIO_FILENAME,
    CLOCK_SKEW_TOLERANCE,
    GENERATED_FILENAME,
    KEY_FILENAME,
    NOTE_FILENAME,
    SESSION_ID_PATTERN,
    TRANSCRIPT_FILENAME,
    ArchiveSource,
    GeneratedRecord,
    SessionChunkStore,
    atomic_write_bytes,
    generated_aad,
    iter_chunks,
    link_state,
    read_generated,
    read_note,
    unwrap_key_from_file,
    validate_session_id,
    wrap_key_to_file,
)
from scribe_desktop.transcription import TranscriptDocument, read_transcript

PAST_SESSIONS_DIRNAME: Final = "past_sessions"
# D1: the entry key's DPAPI description — distinct from every other store's.
PAST_SESSION_KEY_DESCRIPTION: Final = "ClinikoScribe past-session key"
LABEL_FILENAME: Final = "label.enc"
# Pilot plan Task 1.6: v2 adds the shadow flag; a v1 label reads as not
# shadow (D6).
LABEL_SCHEMA_VERSION: Final = 2
PENDING_FILENAME: Final = "pending"
# Development-recordings plan D6: the kept recording's audio key, wrapped
# under the entry key (12-byte nonce + 32-byte key + 16-byte tag).
AUDIO_KEY_FILENAME: Final = "audio-key.enc"
AUDIO_KEY_FILE_BYTES: Final = 60
STAGING_DIRNAME: Final = ".staging"
SETTINGS_FILENAME: Final = "past_sessions.json"
# Development-recordings plan Task 3.3 (D10, C5): the EXPORT LEDGER — which
# partial export (``<session id>.wav.part``) is in flight where, and the
# created file's identity — kept OUTSIDE every entry (so Delete now, expiry
# and ``reconcile_pending`` never remove it), under its own DPAPI-wrapped key.
EXPORT_LEDGER_FILENAME: Final = "exports.enc"
EXPORT_LEDGER_KEY_FILENAME: Final = "exports-key.dpapi"
EXPORT_LEDGER_KEY_DESCRIPTION: Final = "ClinikoScribe export ledger key"
MAX_EXPORT_LEDGER_BYTES: Final = 256 * 1024
EXPORT_SUFFIX: Final = ".wav"
EXPORT_PART_SUFFIX: Final = ".wav.part"
_EXPORT_LEDGER_AAD: Final = b"past-export-ledger"
# The retention setting (Agreed Scope, amended by practitioner decision
# 2026-10-02): a kept transcript is part of the health record, kept for 7
# YEARS MINIMUM (VIC/NSW/ACT health-records law). The one offered window is 7
# years (two leap days included); None is "never" — the default.
MIN_RETENTION_DAYS: Final = 7 * 365 + 2
RETENTION_DAYS_CHOICES: Final[tuple[int, ...]] = (MIN_RETENTION_DAYS,)
# The shorter windows an earlier build offered (1, 7, 30 or 90 days, 1 year):
# a settings file holding one reads as 7 years (never a fail-closed reset).
LEGACY_RETENTION_DAYS: Final[frozenset[int]] = frozenset({1, 7, 30, 90, 365})
# The validation-context key the settings model sets when it raised one.
RAISED_CONTEXT_KEY: Final = "retention_raised"
# How long the retention sweep waits before it tries an unreadable label
# again (H1 round 32 LOW-004): kept meanwhile — a later read can only delete.
UNDATED_RETRY_INTERVAL: Final = timedelta(hours=24)
# Bounds: a label is a few hundred bytes; a displayed name is short.
MAX_LABEL_FILE_BYTES: Final = 64 * 1024
MAX_SETTINGS_FILE_BYTES: Final = 4 * 1024  # three short fields (H3 round 35 SEC-005)
MAX_PATIENT_NAME_CHARS: Final = 200

_SESSION_ID_RE: Final = re.compile(SESSION_ID_PATTERN)
_CLINIC_ID_RE: Final = re.compile(r"^[0-9a-f]{16}$")

RecordingKind = Literal["linked", "desktop", "unknown"]


def default_past_sessions_root() -> Path:
    # No UNC refusal, exactly like the other custody roots (default_sessions_
    # root): a redirected LOCALAPPDATA is an accepted same-user residual.
    return install_layout.data_root() / PAST_SESSIONS_DIRNAME


def _utc_now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Errors.
# ---------------------------------------------------------------------------

# The reasons a failure names — authored words, never OS text (an OS error
# names a path, and a path names a session).
# Public: the Past sessions tab maps a ``PastSessionError`` code to its line
# through this table, never through exception text.
PAST_SESSION_REASONS: Final[dict[str, str]] = {
    "write_failed": "the Past-sessions copy could not be written",
    "verify_failed": "the Past-sessions copy did not read back as written",
    "publish_failed": "the Past-sessions copy could not be put in place",
    "not_found": "that Past-sessions entry does not exist",
    "pending": "that Past-sessions entry is not finished yet",
    "unreadable": "that Past-sessions entry cannot be read on this Windows account",
    "delete_failed": "that Past-sessions entry could not be deleted",
    # Development-recordings plan Task 2.2 (D8): raised ONLY when the audio
    # key could not be overwritten and verified — once its zeros are synced
    # the recording is destroyed, whatever the unlinks after.
    "recording_delete_failed": "that kept recording could not be deleted",
    "recording_not_kept": "that Past-sessions entry holds no kept recording",
    "recording_unreadable": (
        "the kept recording could not be read to the end, so it may be damaged - the "
        "transcript and notes are unaffected, and Delete recording removes it"
    ),
    # Task 3.3 (D10): Export recording's refusals and failures.
    "export_exists": "a file of that name is already in the folder you chose",
    "export_part_exists": (
        "a partial export file of that name (it ends .wav.part) is already in the folder "
        "you chose - delete it by hand first"
    ),
    "export_unresolved": (
        "an earlier partial export file (its name ends .wav.part) could not be removed - "
        "delete it by hand first"
    ),
    "export_ledger_unreadable": (
        "the record of earlier exports cannot be read - restart Clinic Scribe and try again"
    ),
    "export_ledger_busy": (
        "the record of earlier exports could not be opened - try again in a moment"
    ),
    "export_destination_refused": "Clinic Scribe could not check where that folder is",
    "export_unrecorded": "the export could not be recorded, so nothing was written",
    "export_failed": "the file could not be written",
    "export_cleanup_failed": "a partial unencrypted file may remain in the folder you chose",
}


class PastSessionError(Exception):
    """A Past-sessions operation failed (``reason`` is a
    ``PAST_SESSION_REASONS`` code; the text is authored). The cause, when
    chained, is for diagnosis only."""

    def __init__(self, reason: str) -> None:
        super().__init__(PAST_SESSION_REASONS.get(reason, reason))
        self.reason = reason


class ExportUnresolvedError(PastSessionError):
    """``export_unresolved``, naming the session ids of the earlier partial
    export files that could not be removed (review round 21 LOW-005: the
    id is the only way to find such a file)."""

    def __init__(self, session_ids: tuple[str, ...]) -> None:
        super().__init__("export_unresolved")
        self.session_ids = session_ids


class ExportDestinationRefused(PastSessionError):
    """``export_destination_refused``: the store's own check of the RESOLVED
    folder, immediately before the create (codex round 23 PR-HIGH-001),
    refused it. ``line`` is the check's authored refusal, or None when the
    check itself could not be made."""

    def __init__(self, line: str | None) -> None:
        super().__init__("export_destination_refused")
        self.line = line


class PastSessionSettingsError(Exception):
    """``past_sessions.json`` exists but cannot be read or parsed. The
    caller deletes NOTHING on this (Schema / Data Changes: an unreadable
    settings file means no retention sweep) and says so."""


# ---------------------------------------------------------------------------
# The label (D1, D5).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KeepLabel:
    """What the UI resolved for a Complete BEFORE calling it (D5): the
    patient's name as Cliniko showed it (None when not available), whether
    the recording was linked to a Cliniko note, a desktop recording, or
    cannot be told, and its clinic id. Built through ``keep_label`` — the
    one normaliser. repr-hidden: the name is patient data. ``shadow``
    (pilot plan Task 1.6): the recording was a shadow recording, so its kept
    saved note is never copied (``ui/past_sessions``)."""

    patient_name: str | None = field(repr=False)
    recording: RecordingKind
    clinic_id: str | None
    shadow: bool


# Pilot plan D3: a label nothing resolved is treated as a shadow recording's.
UNKNOWN_LABEL: Final = KeepLabel(None, "unknown", None, shadow=True)


def keep_label(
    patient_name: str | None,
    recording: RecordingKind,
    clinic_id: str | None,
    *,
    shadow: bool,
) -> KeepLabel:
    """``KeepLabel`` normalised so the stored label always validates — a
    Complete must never fail on a display string: control characters are
    dropped, whitespace collapsed, the name capped at
    ``MAX_PATIENT_NAME_CHARS`` (an empty one is None); a clinic id that is
    not the registry's shape is left out; a desktop recording has no
    name. ``shadow`` is the recording's mode (pilot plan Task 1.6) — the
    caller's to resolve, fail closed (``MainWindow.keep_label_for``)."""
    name: str | None = None
    if patient_name is not None and recording != "desktop":
        cleaned = "".join(
            " " if unicodedata.category(ch).startswith("C") else ch for ch in patient_name
        )
        name = " ".join(cleaned.split())[:MAX_PATIENT_NAME_CHARS].strip() or None
    clinic = clinic_id if clinic_id is not None and _CLINIC_ID_RE.fullmatch(clinic_id) else None
    return KeepLabel(name, recording, clinic, shadow=shadow is not False)


class PastSessionLabel(BaseModel):
    """``label.enc``'s document: dates (UTC), the recording kind, the clinic
    id, the patient's name (None: not available, or a desktop recording)
    and what the entry holds. ``patient_name`` is a tripwire signature in
    ``logging_setup``, so a rendering of a label is never logged.

    Pilot plan Task 1.6 (v2): ``shadow`` — the entry is a shadow
    recording's, so its saved note is never copied. A v1 label (before
    0.2.0) has none and reads as not shadow (D6); a v1 label carrying one,
    or a v2 label without one, is not a label this app wrote and is
    refused (the entry lists as unreadable, and Copy fails closed). A newer
    version is refused the same way, and so are stored bytes naming no
    version (``_decode_label``, review round 22: the defaults here are for
    building a label)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1, 2] = LABEL_SCHEMA_VERSION
    session_id: str = Field(pattern=SESSION_ID_PATTERN)
    completed_at: AwareDatetime
    started_at: AwareDatetime | None = None
    recording: RecordingKind
    clinic_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{16}$")
    # repr=False (H3 round 35 SEC-008): the tripwire drops a rendering that
    # names the field, but a repr need not carry the name at all.
    patient_name: str | None = Field(
        default=None, max_length=MAX_PATIENT_NAME_CHARS, repr=False
    )
    has_generated: bool
    has_saved: bool
    shadow: bool = Field(default=False, strict=True)

    @model_validator(mode="before")
    @classmethod
    def _shadow_by_version(cls, data: Any) -> Any:
        if isinstance(data, dict):
            version = data.get("schema_version")  # absent: a label being built
            if "schema_version" in data and type(version) is not int:
                # Round 26: JSON ``true`` or ``1.0`` compares equal to 1 —
                # only an integer is a version this app wrote (as audit).
                raise ValueError("a label's version is an integer")
            if version == 1 and "shadow" in data:
                raise ValueError("a v1 label carries no shadow flag")
            if version == 2 and "shadow" not in data:
                raise ValueError("a v2 label names its shadow flag")
        return data

    @property
    def moment(self) -> datetime:
        """The entry's date: when its recording started, else when it
        completed — what the list sorts by, and what every audit write for
        the session is filed and judged by (development-recordings review
        rounds 15–16; one definition since hardening round 43 SIMP-002)."""
        return self.started_at if self.started_at is not None else self.completed_at

    def to_bytes(self) -> bytes:
        return self.model_dump_json().encode("utf-8")


def _label_aad(session_id: str) -> bytes:
    """Distinct from every other artifact's, and bound to the entry."""
    return b"past-label:" + validate_session_id(session_id).encode("ascii")


def _audio_key_aad(session_id: str) -> bytes:
    """The kept recording's wrapped audio key (development-recordings plan
    D6): distinct from every other artifact's, and bound to the entry."""
    return b"past-audio-key:" + validate_session_id(session_id).encode("ascii")


@dataclass(frozen=True)
class PastSessionListing:
    """One COMMITTED entry as the list shows it: its label, or None when the
    label cannot be read (the entry is still listed, so it can be deleted).
    ``recording_kept`` (development-recordings plan Task 2.2): the entry
    holds a kept recording — from two files' presence and a zero-check of
    the key file, never a decryption."""

    session_id: str
    label: PastSessionLabel | None = field(repr=False)
    recording_kept: bool = False


@dataclass(frozen=True)
class RetentionSweepReport:
    """``sweep_report``'s answer: each entry deleted with its completion
    date (content-free), how many were due but could not be deleted, and
    whether the walk finished — a sweep that stopped part-way (the archive
    could not be listed) is ``complete=False``. ``undated`` counts the
    committed entries whose date could not be read, which are KEPT whatever
    their age (round 17 LOW-020: the tab says so). Nothing here names a
    patient."""

    expired: tuple[tuple[str, datetime], ...] = ()
    failed: int = 0
    complete: bool = True
    undated: int = 0
    # The sweep was asked for a window shorter than ``MIN_RETENTION_DAYS``
    # and REFUSED it: nothing was read or deleted (practitioner decision
    # 2026-10-02 — the 7-year minimum, held here as well as in the settings).
    too_short: bool = False
    # Development-recordings plan Task 2.2: the expired ids whose entry held a
    # kept recording, read before the key went — so the audit can record the
    # kept fact before the expiry (review round 8 LOW-003).
    kept: frozenset[str] = frozenset()
    # Development-recordings review round 16 PR-MED-001: each expired id's
    # audit moment — its session's start, else its completion — what the
    # audit's unattended writes are judged and dated by (content-free).
    started: tuple[tuple[str, datetime], ...] = ()

    @property
    def problem(self) -> bool:
        """Some entry due for deletion may still be there."""
        return self.failed > 0 or not self.complete


@dataclass(frozen=True)
class PastSessionEntry:
    """One entry opened (Flow 5): the label, the transcript, and the saved
    and generated notes when kept. repr-hidden: clinical text."""

    label: PastSessionLabel = field(repr=False)
    transcript: TranscriptDocument = field(repr=False)
    saved_note: GeneratedNote | None = field(repr=False)
    generated: GeneratedRecord | None = field(repr=False)


# ---------------------------------------------------------------------------
# The export ledger (development-recordings plan Task 3.3).
# ---------------------------------------------------------------------------


class ExportIdentity(BaseModel):
    """A created ``.part`` file's identity (``os.fstat``: the file index and
    the volume) — a file at that path with any other identity is not the one
    the app created, and is never deleted (round 7 PR-MED-071)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    file_index: int = Field(ge=0, strict=True)
    device: int = Field(ge=0, strict=True)


class ExportRow(BaseModel):
    """One export in flight: the folder chosen (content-free — the file is
    named by the session id) and the created ``.part`` file's identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    folder: str = Field(min_length=1, max_length=32_767)
    identity: ExportIdentity


class ExportLedger(BaseModel):
    """``exports.enc``'s document: the unresolved exports by session id."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    rows: dict[str, ExportRow] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _an_integer_version(cls, data: Any) -> Any:
        if isinstance(data, dict) and type(data.get("schema_version")) is not int:
            raise ValueError("a ledger names its integer version")  # round 26's rule
        return data

    @field_validator("rows")
    @classmethod
    def _session_ids(cls, rows: dict[str, ExportRow]) -> dict[str, ExportRow]:
        if not all(_SESSION_ID_RE.fullmatch(session_id) for session_id in rows):
            raise ValueError("a ledger row is keyed by a session id")
        return rows

    def to_bytes(self) -> bytes:
        return self.model_dump_json().encode("utf-8")


@dataclass(frozen=True)
class ExportRecovery:
    """``recover_exports``'s answer: the session ids whose partial export
    file could not be removed (each owed one start-up line), and whether an
    unreadable ledger was started again (one line), or one could not be
    opened this time and was left as it is (one line — review round 21: a
    ledger that is never openable must not be silent). Content-free."""

    kept: tuple[str, ...] = ()
    reset: bool = False
    busy: bool = False


class _LedgerUnreadable(Exception):
    """The ledger exists but cannot be read (a link, its key, its bytes or
    its shape) — never shown; the callers decide."""


class _LedgerBusy(Exception):
    """The ledger's file could not be opened or read THIS time (a lock, a
    scanner, a transient error) — never a reason to start it again (review
    round 20 LOW: a reset forgets every unresolved partial file)."""


# ---------------------------------------------------------------------------
# The store.
# ---------------------------------------------------------------------------

WrapKey = Callable[[SessionCrypto, Path], object]
UnwrapKey = Callable[[Path], SessionCrypto]


def _wrap_entry_key(crypto: SessionCrypto, directory: Path) -> object:
    return wrap_key_to_file(crypto, directory, description=PAST_SESSION_KEY_DESCRIPTION)


def _unwrap_entry_key(directory: Path) -> SessionCrypto:
    return unwrap_key_from_file(directory, description=PAST_SESSION_KEY_DESCRIPTION)


def _wrap_ledger_key(crypto: SessionCrypto, root: Path) -> object:
    return wrap_key_to_file(
        crypto,
        root,
        description=EXPORT_LEDGER_KEY_DESCRIPTION,
        filename=EXPORT_LEDGER_KEY_FILENAME,
    )


def _unwrap_ledger_key(root: Path) -> SessionCrypto:
    return unwrap_key_from_file(
        root, description=EXPORT_LEDGER_KEY_DESCRIPTION, filename=EXPORT_LEDGER_KEY_FILENAME
    )


class _EntryKeeper:
    """The ``session_store.ArchiveKeeper`` one Complete is given (D4): the
    store plus the label the UI resolved."""

    def __init__(self, store: PastSessionStore, label: KeepLabel) -> None:
        self._store = store
        self._label = label

    def write(self, source: ArchiveSource) -> None:
        self._store.write_entry(source, self._label)

    def commit(self, session_id: str) -> bool:
        return self._store.commit(session_id)

    def drop_unfinished(self, session_id: str) -> bool:
        return self._store.remove_pending_entry(session_id)


class PastSessionStore:
    """The archive (D1 / D3). Construction touches nothing on disk.
    ``wrap_key`` / ``unwrap_key`` are the entry-key custody (DPAPI with
    ``PAST_SESSION_KEY_DESCRIPTION`` by default) — a test seam, so a failure
    of either can be injected without the host's DPAPI."""

    def __init__(
        self,
        root: Path | None = None,
        *,
        clock: Callable[[], datetime] = _utc_now,
        logger: logging.Logger | None = None,
        wrap_key: WrapKey = _wrap_entry_key,
        unwrap_key: UnwrapKey = _unwrap_entry_key,
        wrap_ledger_key: WrapKey = _wrap_ledger_key,
        unwrap_ledger_key: UnwrapKey = _unwrap_ledger_key,
    ) -> None:
        self._root = root if root is not None else default_past_sessions_root()
        self._clock = clock
        self._logger = logger
        self._wrap_key = wrap_key
        self._unwrap_key = unwrap_key
        # Development-recordings Task 3.3: the export ledger's key custody —
        # given the archive ROOT, it writes / reads ``exports-key.dpapi``
        # there (a test seam, like the entry key's).
        self._wrap_ledger_key = wrap_ledger_key
        self._unwrap_ledger_key = unwrap_ledger_key
        # The retention sweep's dates (review round 11 MED-001): a committed
        # entry's ``completed_at`` never changes, so each is decrypted ONCE
        # per process, not on every hourly tick (C5: the sweep runs on the
        # GUI thread; years of entries would otherwise mean one key unwrap
        # each, every hour). Content-free — a date per session id, never a
        # name. Dropped whenever this store writes, publishes or removes
        # the id's entry.
        self._completed_dates: dict[str, datetime] = {}
        # Development-recordings review round 16 PR-MED-001: each dated
        # entry's audit moment (its start, else its completion), read from
        # the same decryption — what the sweep's audit writes are judged and
        # dated by. Kept and dropped with ``_completed_dates``.
        self._started_dates: dict[str, datetime] = {}
        # The retention sweep's unreadable labels (H1 round 32 LOW-004, the
        # same class): when each id's label last failed to read, so an entry
        # whose key or label cannot be read (D9's broken DPAPI makes that
        # every entry) is retried once per ``UNDATED_RETRY_INTERVAL``, not
        # unwrapped again on every hourly tick. Still counted as undated
        # (kept) every tick. Dropped with the date cache's rule.
        self._undated: dict[str, datetime] = {}
        # Development-recordings review round 14 PR-MED-002: the entries the
        # latest ``tidy_dead_recordings`` held back because their recording's
        # deletion was not cleared (round 17 PR-MED-001: not listed and
        # recorded) — the retention sweep holds them too, so the evidence the
        # next record needs is not expired away.
        self._spared: frozenset[str] = frozenset()

    def _forget_dates(self, session_id: str) -> None:
        """The date caches' one rule: whenever this store writes, publishes
        or removes ``session_id``'s entry, both caches forget it (H2 round 34
        SIMP-002)."""
        self._completed_dates.pop(session_id, None)
        self._started_dates.pop(session_id, None)
        self._undated.pop(session_id, None)

    @property
    def root(self) -> Path:
        return self._root

    @property
    def staging_root(self) -> Path:
        return self._root / STAGING_DIRNAME

    def _staging_linked(self) -> bool:
        """True when ``.staging`` is a symlink or junction (round 13
        PR-LOW-010): every staging path would then resolve OUTSIDE it — to
        the archive's own entries, say — so staging is refused as a whole.
        The archive ROOT is not checked: relocating it is D10's location
        question (Phase 4)."""
        return _is_link(self.staging_root)

    def keeper(self, label: KeepLabel | None) -> _EntryKeeper:
        """The writer ``complete_session`` is given for one Complete (D4);
        None is ``UNKNOWN_LABEL`` ("Name not available")."""
        return _EntryKeeper(self, label if label is not None else UNKNOWN_LABEL)

    # --- writing (C1: everything here runs BEFORE the source key goes) -----

    def write_entry(self, source: ArchiveSource, label: KeepLabel) -> None:
        """Stage, fully verify and publish ``source`` as the entry for its
        session id, carrying ``pending`` (C1). Replaces an earlier entry for
        the id key-first. ``PastSessionError`` on any failure, with the
        staging copy removed best-effort (``clean_staging`` finishes it).
        Refused (``write_failed``, nothing touched) while ``.staging`` is a
        link (round 13 PR-LOW-010: nothing is written or removed through
        one)."""
        session_id = validate_session_id(source.session_id)
        self._forget_dates(session_id)
        if self._staging_linked():
            self._log(session_id, "staging_link_refused")
            raise PastSessionError("write_failed")
        staging = self.staging_root / session_id
        stage = "write_failed"
        try:
            if not _remove_key_first(staging):
                raise PastSessionError("write_failed")
            document = self._label_for(source, label)
            expected, audio_digest = self._stage(staging, source, document)
            stage = "verify_failed"
            self._verify_staged(staging, source, document, expected, audio_digest)
            stage = "publish_failed"
            self._publish(staging, self._root / session_id)
        except Exception as exc:
            _remove_key_first(staging)
            self._log(session_id, stage)
            raise PastSessionError(stage) from exc

    def _label_for(self, source: ArchiveSource, label: KeepLabel) -> PastSessionLabel:
        started: datetime | None = None
        created = source.created_at
        if created is not None and math.isfinite(created):
            try:
                started = datetime.fromtimestamp(created, UTC)
            except (OverflowError, OSError, ValueError):
                started = None
        return PastSessionLabel(
            session_id=source.session_id,
            completed_at=self._clock().astimezone(UTC),
            started_at=started,
            recording=label.recording,
            clinic_id=label.clinic_id,
            patient_name=label.patient_name,
            has_generated=source.generated_plain is not None,
            has_saved=source.note_plain is not None,
            shadow=label.shadow,
        )

    def _stage(
        self, staging: Path, source: ArchiveSource, document: PastSessionLabel
    ) -> tuple[frozenset[str], bytes | None]:
        """Write the entry into ``staging`` under a FRESH key; returns the
        exact file set it must hold and, for a kept recording, the SHA-256
        of the audio PCM as it was staged (None without audio)."""
        session_id = source.session_id
        crypto = SessionCrypto()
        audio_digest: bytes | None = None
        try:
            staging.mkdir(parents=True)
            self._wrap_key(crypto, staging)
            files = {
                LABEL_FILENAME: crypto.encrypt(document.to_bytes(), _label_aad(session_id)),
                TRANSCRIPT_FILENAME: crypto.encrypt(source.transcript_plain),
            }
            if source.note_plain is not None:
                files[NOTE_FILENAME] = crypto.encrypt(source.note_plain)
            if source.generated_plain is not None:
                files[GENERATED_FILENAME] = crypto.encrypt(
                    source.generated_plain, generated_aad(session_id)
                )
            for name, blob in files.items():
                atomic_write_bytes(staging / name, blob, error_label="past-session entry")
            names = {KEY_FILENAME, PENDING_FILENAME, *files}
            if source.audio_chunks is not None:
                audio_digest = _stage_audio(staging, crypto, session_id, source.audio_chunks)
                names |= {AUDIO_FILENAME, AUDIO_KEY_FILENAME}
            atomic_write_bytes(staging / PENDING_FILENAME, b"", error_label="pending marker")
        finally:
            crypto.destroy()
        return frozenset(names), audio_digest

    def _verify_staged(
        self,
        staging: Path,
        source: ArchiveSource,
        document: PastSessionLabel,
        expected: frozenset[str],
        audio_digest: bytes | None = None,
    ) -> None:
        """D1's full verification, through the entry's OWN key read back from
        disk: exactly the expected files; the label as written; every
        plaintext's SHA-256 equal to the source bytes; and the existing
        readers (``read_transcript``, ``read_note`` — which re-checks the
        note's session binding and transcript digest — ``read_generated``)
        accepting what they will later read. A kept recording's audio
        (development-recordings plan D5, C4): its key unwrapped through the
        entry key, the STAGED store re-read chunk by chunk with its footer
        required, and the PCM's SHA-256 equal to the digest taken while it
        was staged — never a whole-file read. Raises on any difference."""
        present = frozenset(path.name for path in staging.iterdir())
        if present != expected:
            raise PastSessionError("verify_failed")
        session_id = source.session_id
        crypto = self._unwrap_key(staging)
        try:
            label_plain = crypto.decrypt(
                _read_capped(staging / LABEL_FILENAME, MAX_LABEL_FILE_BYTES),
                _label_aad(session_id),
            )
            if _parse_label(label_plain) != document:
                raise PastSessionError("verify_failed")
            transcript = crypto.decrypt((staging / TRANSCRIPT_FILENAME).read_bytes())
            _require_same(transcript, source.transcript_plain)
            read_transcript(staging, crypto)
            if source.note_plain is not None:
                note = crypto.decrypt((staging / NOTE_FILENAME).read_bytes())
                _require_same(note, source.note_plain)
                read_note(staging, crypto)
            if source.generated_plain is not None:
                _require_same(
                    crypto.decrypt(
                        (staging / GENERATED_FILENAME).read_bytes(), generated_aad(session_id)
                    ),
                    source.generated_plain,
                )
                if read_generated(staging, crypto, session_id) is None:
                    raise PastSessionError("verify_failed")
            if audio_digest is not None:
                digest = hashlib.sha256()
                for chunk in _audio_chunks(staging, crypto, session_id):
                    digest.update(chunk)
                if digest.digest() != audio_digest:
                    raise PastSessionError("verify_failed")
        finally:
            crypto.destroy()

    def _publish(self, staging: Path, final: Path) -> None:
        """Replace any earlier entry for the id KEY-FIRST (C1: a retried
        Complete), then move the verified staging copy into place."""
        if not _remove_key_first(final) or final.exists():
            raise PastSessionError("publish_failed")
        os.rename(staging, final)

    def commit(self, session_id: str) -> bool:
        """Remove the entry's ``pending`` marker — called by the Complete
        right after the source key is deleted. NEVER raises; False leaves it
        for ``reconcile_pending``. Never commits through a link (round 13
        PR-LOW-010)."""
        try:
            entry = self._root / validate_session_id(session_id)
            if _is_link(entry):
                raise OSError("the entry is a link")
            (entry / PENDING_FILENAME).unlink(missing_ok=True)
        except (OSError, ValueError):
            self._log(session_id, "commit_deferred")
            return False
        return True

    # --- the C1 destroyers' hook and the reconciliations -------------------

    def remove_pending_entry(self, session_id: str) -> bool:
        """For every NON-Complete destroyer of a source session — Discard,
        the recovery list's Discard, expiry, a dead key's ``orphan_gc`` —
        called BEFORE it deletes the source key: remove any entry (and any
        staging copy) an interrupted Complete left for ``session_id``, key
        first. While the source key still exists no entry for its id can be
        a finished one (C1), so whatever is there goes. True when both keys
        are gone (the content is then cryptographically dead; leftover
        files are best-effort and ``reconcile_pending`` removes a keyless
        entry). NEVER raises: False means the caller must NOT delete the
        source key.

        A link where an entry or a staging copy would be (or a linked
        ``.staging``) is NOT ours (round 13 PR-LOW-010): it is never listed,
        committed or followed, so it cannot become a finished entry — it
        counts as nothing to remove and is left in place, untouched. A
        ``.staging`` whose link status cannot be read is neither (hardening
        review round 41 LOW-003, the rule of ``_remove_key_first_unless_link``
        one level up): a staging copy may sit under it — since 0.3.0 with a
        kept recording's audio — so False, and the source key stays this
        time."""
        try:
            validate_session_id(session_id)
        except ValueError:
            return True  # not a session id: nothing of ours can exist for it
        self._forget_dates(session_id)
        staging_linked = link_state(self.staging_root)
        if staging_linked is None:
            return False
        removed = True
        if not staging_linked:
            removed = _remove_key_first_unless_link(self.staging_root / session_id)
        return _remove_key_first_unless_link(self._root / session_id) and removed

    def reconcile_pending(self, sessions_root: Path) -> list[str]:
        """At start-up and on every sweep tick (C1): commit every ``pending``
        entry whose source ``sessions\\<id>\\key.dpapi`` is CONFIRMED absent
        (``FileNotFoundError`` — any other error decides nothing), and
        remove every keyless entry (only ever a key-first removal's
        leftover: an entry is published with its key). Returns the session
        ids it committed, so the caller can record them in the audit as
        ``archived`` (round 12 LOW-002: a Complete interrupted between its key
        deletion and its audit update). NEVER raises."""
        committed: list[str] = []
        try:
            for entry in self._entry_dirs():
                if not _exists(entry / KEY_FILENAME):
                    if _absent(entry / KEY_FILENAME):
                        self._forget_dates(entry.name)
                        shutil.rmtree(entry, ignore_errors=True)
                    continue
                if not _exists(entry / PENDING_FILENAME):
                    continue
                if _absent(sessions_root / entry.name / KEY_FILENAME) and self.commit(
                    entry.name
                ):
                    committed.append(entry.name)
        except Exception:  # noqa: BLE001 - a later tick tries again
            self._log(None, "reconcile_failed")
        return committed

    def clean_staging(self) -> int:
        """Remove every staging copy, key first — at every start-up and
        sweep tick, INDEPENDENT of the retention setting (it runs under
        "never" too). Only session-id-named folders are touched. Returns
        how many went. NEVER raises.

        Links are never followed (round 13 PR-LOW-010): a linked ``.staging``
        stops the cleanup, and a linked child is skipped. Each refusal is
        left in place, is not counted among the removed, and is logged as a
        content-free ``detail_code`` (``staging_link_refused`` /
        ``link_refused``, with the child's session id when its name is one)
        — never a path or exception text (C3), like every other failure
        here."""
        if self._staging_linked():
            self._log(None, "staging_link_refused")
            return 0
        removed = 0
        try:
            children = sorted(self.staging_root.iterdir())
        except OSError:
            return 0
        for child in children:
            if not _SESSION_ID_RE.fullmatch(child.name):
                continue
            if _is_link(child):
                self._log(child.name, "link_refused")
            elif _remove_key_first(child):
                removed += 1
        return removed

    # --- reading ------------------------------------------------------------

    def list_entries(self) -> list[PastSessionListing]:
        """Every COMMITTED entry (no ``pending`` marker, a key present), in
        directory order (the tab sorts). Decrypts ``label.enc`` only — one
        key unwrap per entry. An entry whose label cannot be read is listed
        with ``label`` None, so it can still be deleted. A missing archive is
        empty; one that exists but cannot be listed raises
        ``PastSessionError("unreadable")`` — never shown as empty (round 16
        LOW-003)."""
        listings: list[PastSessionListing] = []
        for entry in self._committed_dirs(strict=True):
            listings.append(
                PastSessionListing(
                    entry.name, self._read_label(entry), _recording_kept_in(entry)
                )
            )
        return listings

    def kept_entries(self) -> list[PastSessionListing]:
        """Every COMMITTED entry holding a kept recording (development-
        recordings plan Task 2.2: the start-up repair of the audit's
        ``recording.kept_at``), its label decrypted — None when it cannot be
        read. Only these labels are decrypted. NEVER raises: an archive that
        cannot be listed is empty here (the next start tries again)."""
        return self._labelled_where(_recording_kept_in, kept=True)

    def kept_session_ids(self) -> list[str]:
        """The session ids of every COMMITTED entry holding a kept recording
        (``recording_kept``), from names and the key file's zero-check only:
        NOTHING is decrypted (development-recordings review round 29 MED-001 —
        the replay tool lists without opening every patient's name). A
        missing archive is empty; one that exists but cannot be listed raises
        ``PastSessionError("unreadable")``, as ``list_entries`` does."""
        return [
            entry.name
            for entry in self._committed_dirs(strict=True)
            if _recording_kept_in(entry)
        ]

    def deleted_recordings(self) -> list[PastSessionListing]:
        """Every COMMITTED entry whose kept recording was DELETED but not yet
        tidied — its ``audio-key.enc`` zeroed, or gone with ``audio.enc``
        still there (review round 11 LOW-004: the start-up repair records the
        deletion before ``tidy_dead_recordings`` removes that evidence). Its
        label decrypted, None when it cannot be read; only these labels are.
        NEVER raises."""
        return self._labelled_where(_recording_deleted_in, kept=False)

    def _labelled_where(
        self, holds: Callable[[Path], bool], *, kept: bool
    ) -> list[PastSessionListing]:
        try:
            return [
                PastSessionListing(entry.name, self._read_label(entry), recording_kept=kept)
                for entry in self._committed_dirs()
                if holds(entry)
            ]
        except Exception:  # noqa: BLE001 - a later start tries again
            self._log(None, "kept_list_failed")
            return []

    def entry_label(self, session_id: str) -> PastSessionLabel | None:
        """The COMMITTED entry's label (one key unwrap), or None when there is
        no such entry or its label cannot be read — what a reconciled commit's
        audit write is dated and judged by (development-recordings review
        round 15 PR-MED-001). NEVER raises."""
        try:
            return self._read_label(self._committed(session_id))
        except Exception:  # noqa: BLE001 - no label is an answer, never a raise
            return None

    def recording_kept(self, session_id: str) -> bool:
        """True when ``session_id``'s entry holds a kept recording: BOTH
        ``audio.enc`` and ``audio-key.enc`` present and the key file not all
        zeros (a zeroed key is "destroyed, cleanup pending" — round 4
        PR-MED-041). A ~60-byte read, no decryption. A link, or anything not
        a session id, holds none. Never raises."""
        return self.recording_state(session_id) == "kept"

    def recording_held(self, session_id: str) -> bool:
        """True when ``session_id``'s entry holds a kept recording OR one whose
        deletion is not yet tidied (review round 13 LOW-001). No decryption;
        never raises."""
        return self.recording_state(session_id) != "none"

    def recording_state(self, session_id: str) -> RecordingState:
        """``kept``, ``gone`` (deleted, not yet tidied) or ``none`` from ONE
        read (``_recording_state``) — what Delete now decides from before it
        destroys the entry, so the kept fact and an earlier deletion are
        recorded first (review rounds 13–17). A link, or anything not a
        session id, holds none. No decryption; never raises."""
        try:
            entry = self._root / validate_session_id(session_id)
        except ValueError:
            return "none"
        return "none" if _is_link(entry) else _recording_state(entry)

    def read_recording(self, session_id: str) -> Iterator[bytes]:
        """The COMMITTED entry's kept recording as PCM chunks (entry key ->
        audio key -> ``iter_chunks``, footer required). Refused BEFORE any
        unwrap — ``PastSessionError`` ``not_found`` / ``pending`` for the
        entry, ``recording_not_kept`` when it holds no live recording (a
        missing or zeroed key file). The returned generator unwraps on its
        first step and destroys both keys when it finishes or is closed; a
        failure before any audio is read raises
        ``PastSessionError("unreadable")``, and one after it (a later chunk
        failing authentication) ``PastSessionError("recording_unreadable")``
        — the caller has then already received the earlier chunks."""
        entry = self._committed(session_id)
        if not _recording_kept_in(entry):
            raise PastSessionError("recording_not_kept")
        return self._recording_chunks(entry)

    def _recording_chunks(self, entry: Path) -> Iterator[bytes]:
        try:
            crypto = self._unwrap_key(entry)
        except Exception as exc:
            raise PastSessionError("unreadable") from exc
        started = False
        try:
            for chunk in _audio_chunks(entry, crypto, entry.name):
                started = True
                yield chunk
        except PastSessionError:
            raise
        except Exception as exc:
            # Review round 22 LOW: once audio has been read, a later failure
            # is the RECORDING's (a damaged chunk), never this account's.
            raise PastSessionError("recording_unreadable" if started else "unreadable") from exc
        finally:
            crypto.destroy()

    def delete_recording(
        self, session_id: str, *, on_destroyed: Callable[[], object] | None = None
    ) -> None:
        """Delete recording (development-recordings plan D8, D6): the kept
        recording ALONE — ``key.dpapi``, the transcript and the notes are
        never touched. ``audio-key.enc`` is overwritten with zeros IN PLACE
        (opened ``r+b``, the same file — never the atomic writer, whose
        replacement would leave the original bytes behind; round 1
        PR-HIGH-001), flushed, synced and read back as zeros; THEN it and
        ``audio.enc`` are unlinked best-effort. Once the zeros are synced the
        recording is destroyed: a failed unlink (a Windows file lock, or a
        crash between the two) is still a successful deletion whose cleanup
        is pending (``tidy_dead_recordings`` finishes it).
        ``PastSessionError`` — ``not_found`` / ``pending`` for the entry,
        ``recording_not_kept`` when it holds no live recording, and
        ``recording_delete_failed`` ONLY when the overwrite could not be
        completed and verified (the key file is then as it was, or partly
        zeroed — never reported deleted). ``on_destroyed`` (the caller's
        audit record of the deletion; True when recorded) runs between the
        verified zeros and the unlinks; when it does not record, the files
        are left for the next run."""
        entry = self._committed(session_id)
        if not _recording_kept_in(entry):
            raise PastSessionError("recording_not_kept")
        key_path = entry / AUDIO_KEY_FILENAME
        try:
            # Review round 11 LOW-001: the archive's only write THROUGH an
            # existing file in an entry, so it never follows a link (a
            # symlink, or a hard link naming another file) and never zeroes
            # more than a key file holds.
            if link_state(key_path) is not False:
                raise OSError("the audio key is a link")
            with key_path.open("r+b") as stream:
                status = os.fstat(stream.fileno())
                length = status.st_size
                if not _is_own_key_file(status):
                    raise OSError("not this entry's audio key")
                stream.seek(0)
                stream.write(b"\0" * length)
                stream.flush()
                os.fsync(stream.fileno())
                stream.seek(0)
                if stream.read(length + 1).strip(b"\0"):
                    raise OSError("the audio key did not read back as zeros")
        except OSError as exc:
            self._log(session_id, "recording_delete_failed")
            raise PastSessionError("recording_delete_failed") from exc
        # Review round 12 LOW-003: the caller records the deletion HERE —
        # after the zeros are synced and verified, before the unlinks — so a
        # kill after the unlinks never leaves an unrecorded deletion; a record
        # that fails (False, or raises) keeps the zeroed key as the evidence
        # the next run's deletion record (``app.record_deleted_recordings``)
        # needs, and the files stay for it.
        if on_destroyed is not None:
            try:
                recorded = bool(on_destroyed())
            except Exception:  # noqa: BLE001 - the deletion itself has happened
                recorded = False
            if not recorded:
                self._log(session_id, "recording_cleanup_pending")
                return
        for name in (AUDIO_KEY_FILENAME, AUDIO_FILENAME):
            if not _unlink_quietly(entry / name):
                self._log(session_id, "recording_cleanup_pending")

    def tidy_dead_recordings(self, *, cleared: frozenset[str] | None = None) -> int:
        """Remove every ``audio.enc`` whose ``audio-key.enc`` is CONFIRMED
        gone or zeroed, and every zeroed key file — what a Delete recording
        interrupted between its zeros and its unlinks (or refused an unlink
        by a file lock) leaves (development-recordings plan Task 2.2). Called
        where ``clean_staging`` is. A live key is never touched; a key file
        that cannot be read decides nothing. POSITIVE CLEARANCE (review
        round 17 PR-MED-001): given ``cleared`` — the ids whose deletion the
        caller's discovery LISTED and recorded (or owed no record) — an entry
        is tidied only when its id is in it; any other dead recording found
        here (its record refused, or missed by a discovery read that failed —
        tidy's own read is never trusted alone) is left for the next run and
        held from the retention sweep until a later call clears it (round 14
        PR-MED-002). ``cleared`` None (no audit: nothing can be recorded)
        tidies every one. Returns how many files went. NEVER raises."""
        held: set[str] = set()
        removed = 0
        try:
            for entry in self._entry_dirs():
                # Review round 18 PR-LOW-001: discovery's own rule decides what
                # is dead — a non-file where ``audio.enc`` would be, beside no
                # key, is no recording, so it is neither tidied nor held.
                if _recording_state(entry) != "gone":
                    continue
                paths = [
                    entry / name
                    for name in (AUDIO_FILENAME, AUDIO_KEY_FILENAME)
                    if _exists(entry / name)
                ]
                if not paths:
                    continue
                if cleared is not None and entry.name not in cleared:
                    held.add(entry.name)
                    continue
                for path in paths:
                    try:
                        path.unlink()
                        removed += 1
                    except OSError:
                        self._log(entry.name, "recording_cleanup_pending")
        except Exception:  # noqa: BLE001 - a later start tries again
            self._log(None, "tidy_failed")
        self._spared = frozenset(held)
        return removed

    # --- Export recording (development-recordings plan Task 3.3; D10, C5) ---

    def export_recording(
        self,
        session_id: str,
        folder: Path,
        *,
        check_destination: Callable[[Path], str | None],
    ) -> Path:
        """Write the COMMITTED entry's kept recording to ``folder`` as
        ``<session id>.wav`` (16 kHz mono PCM16, through the ONE writer
        ``speech.write_wav``) and return its path. A shadow recording's
        confirm is the caller's. The DESTINATION is checked HERE as well as
        by the caller (codex round 23 PR-HIGH-001): ``check_destination``
        (the caller's location check — ``exclusions.check_export_location``
        — answering a refusal line or None) is REQUIRED and runs on the
        RESOLVED folder immediately before the exclusive create, so a
        junction or drive mapping changed while the caller waited on the
        user cannot redirect the file; a refusal, or a check that raises,
        refuses (``ExportDestinationRefused``) with nothing written. This is
        the custody of the file:

        1. ``read_recording`` refuses (``not_found`` / ``pending`` /
           ``recording_not_kept``) before anything is written;
        2. every earlier unresolved ledger row is resolved — its ``.part``
           deleted only while it is still the file the app created — and one
           that cannot be resolved REFUSES (``export_unresolved``), so a
           partial export is never forgotten by a later one; an unreadable
           ledger refuses too (start-up resets it, with a line), and one that
           could not be opened this time refuses (``export_ledger_busy``);
           a relative folder refuses (``export_failed``);
        3. an existing ``<id>.wav`` refuses (``export_exists``: never
           overwritten); the resolved folder is checked
           (``check_destination``); ``<id>.wav.part`` is created EXCLUSIVELY — a file of
           that name already there refuses (``export_part_exists``; the app
           never adopts a file it did not create);
        4. the ledger row (the folder and the created file's identity) is
           written BEFORE the first byte of audio (``export_unrecorded`` when
           it cannot be — the empty file is removed);
        5. the PCM is streamed into the ``.part`` file, synced and renamed;
           the row is dropped after the rename.

        On ANY failure after the ``.part`` exists — a later chunk failing
        authentication (``iter_chunks`` yields earlier plaintext first), a
        full disk, a failed rename — the handle is closed and the ``.part``
        removed (``export_failed``, or the read's own reason); a ``.part``
        that cannot be removed keeps its row for the next start and raises
        ``export_cleanup_failed``. ``PastSessionError`` only."""
        chunks = self.read_recording(session_id)
        try:
            return self._export(session_id, folder, chunks, check_destination)
        finally:
            close = getattr(chunks, "close", None)
            if close is not None:
                close()

    def _export(
        self,
        session_id: str,
        folder: Path,
        chunks: Iterator[bytes],
        check_destination: Callable[[Path], str | None],
    ) -> Path:
        if not folder.is_absolute():
            # Review round 20 LOW-003: the ledger records the folder the next
            # start resolves a partial file in — never one relative to
            # whatever the working directory then is.
            raise PastSessionError("export_failed")
        # Review round 21 LOW-007: export into — and record — the RESOLVED
        # folder the location check judged, never a mapping (a `subst` drive)
        # that may be gone when the next start looks for a partial file.
        try:
            folder = Path(os.path.realpath(folder))
        except (OSError, ValueError):
            raise PastSessionError("export_failed") from None
        try:
            rows = self._read_ledger()
        except _LedgerUnreadable:
            raise PastSessionError("export_ledger_unreadable") from None
        except _LedgerBusy:
            raise PastSessionError("export_ledger_busy") from None
        remaining = self._resolve(rows)
        if remaining != rows:
            try:
                self._write_ledger(remaining)
            except Exception:  # noqa: BLE001 - the rows are kept; refused below
                self._log(session_id, "export_ledger_failed")
                raise PastSessionError("export_unrecorded") from None
        if remaining:
            raise ExportUnresolvedError(tuple(sorted(remaining)))
        final = folder / f"{session_id}{EXPORT_SUFFIX}"
        part = _part_path(folder, session_id)
        if _exists(final) or _is_link(final):
            raise PastSessionError("export_exists")
        # Imported BEFORE the file exists (review round 22 LOW): nothing that
        # can fail may sit between the create and the clean-up below.
        from scribe_desktop.speech import write_wav

        # Codex round 23 PR-HIGH-001: the RESOLVED folder is checked here,
        # the last step before the create — the caller's own check ran before
        # it waited on the user. Anything but a clear None refuses.
        try:
            refusal = check_destination(folder)
        except Exception:  # noqa: BLE001 - a check that cannot be made refuses
            self._log(session_id, "export_destination_refused")
            raise ExportDestinationRefused(None) from None
        if refusal is not None:
            self._log(session_id, "export_destination_refused")
            raise ExportDestinationRefused(refusal)
        flags =os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        try:
            descriptor = os.open(part, flags, 0o600)
        except FileExistsError:
            raise PastSessionError("export_part_exists") from None
        except OSError:
            self._log(session_id, "export_failed")
            raise PastSessionError("export_failed") from None
        try:
            stream = os.fdopen(descriptor, "wb")
        except Exception:  # noqa: BLE001 - the empty file goes, by its name
            try:
                os.close(descriptor)
            except OSError:
                pass  # already closed
            self._log(session_id, "export_failed")
            if not _unlink_quietly(part):
                raise PastSessionError("export_cleanup_failed") from None
            raise PastSessionError("export_failed") from None
        identity: ExportIdentity | None = None
        try:
            status = os.fstat(stream.fileno())
            identity = ExportIdentity(file_index=status.st_ino, device=status.st_dev)
            try:
                self._write_ledger({session_id: ExportRow(folder=str(folder), identity=identity)})
            except Exception:  # noqa: BLE001 - nothing written yet: refused
                self._log(session_id, "export_ledger_failed")
                raise PastSessionError("export_unrecorded") from None
            write_wav(stream, chunks)
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            os.rename(part, final)
        except BaseException as exc:
            # Review round 20 MED-001: the clean-up runs on EVERY failure — a
            # close that raises a second disk-full error included — and only
            # a PastSessionError leaves (the docstring's contract).
            try:
                stream.close()
            except OSError:
                pass  # the buffered bytes are lost; the handle is closed
            self._log(session_id, "export_failed")
            # Created exclusively an instant ago: with no identity read yet
            # (and so no row) it is removed by its name.
            removed = (
                _remove_part(part, identity) if identity is not None else _unlink_quietly(part)
            )
            if not removed:
                raise PastSessionError("export_cleanup_failed") from None
            self._drop_export_row(session_id)
            if isinstance(exc, PastSessionError) or not isinstance(exc, Exception):
                raise
            raise PastSessionError("export_failed") from exc
        self._drop_export_row(session_id)
        return final

    def recover_exports(self) -> ExportRecovery:
        """At START-UP, FIRST — before ``clean_staging``, ``reconcile_pending``,
        the kept-fact repair, ``tidy_dead_recordings`` and the retention sweep
        (Task 3.3): a hard kill or power loss mid-export skips
        ``export_recording``'s clean-up, so every ledger row's ``.part`` is
        deleted here while it is still the file the app created; a completed
        ``<id>.wav`` and a file whose identity differs are never touched. The
        resolved rows are dropped; a row whose ``.part`` could not be removed
        or no longer matches is KEPT and named in the answer (one start-up
        line each). An unreadable ledger is started again (``reset``: one
        line — a partial file may remain); one that could not be opened this
        time is left as it is (``busy``: one line). NEVER raises."""
        try:
            rows = self._read_ledger()
        except _LedgerUnreadable:
            self._log(None, "export_ledger_reset")
            self._reset_ledger()
            return ExportRecovery(reset=True)
        except _LedgerBusy:
            # Left as it is: the next export, or the next start, resolves it.
            self._log(None, "export_ledger_failed")
            return ExportRecovery(busy=True)
        if not rows:
            return ExportRecovery()
        remaining = self._resolve(rows)
        if remaining != rows:
            try:
                self._write_ledger(remaining)
            except Exception:  # noqa: BLE001 - the next start resolves them again
                self._log(None, "export_ledger_failed")
        for session_id in remaining:
            self._log(session_id, "export_part_kept")
        return ExportRecovery(kept=tuple(sorted(remaining)))

    @staticmethod
    def _resolve(rows: dict[str, ExportRow]) -> dict[str, ExportRow]:
        """The rows whose ``.part`` is still there and could not be removed
        as the app's own file — the unresolved ones."""
        return {
            session_id: row
            for session_id, row in rows.items()
            if not _remove_part(_part_path(row.folder, session_id), row.identity)
        }

    def _drop_export_row(self, session_id: str) -> None:
        """After a finished export: its row goes. NEVER raises — a row left
        behind names a ``.part`` that is gone, which the next resolution
        drops."""
        try:
            rows = self._read_ledger()
            if session_id in rows:
                self._write_ledger({sid: row for sid, row in rows.items() if sid != session_id})
        except Exception:  # noqa: BLE001 - resolved later
            self._log(session_id, "export_ledger_failed")

    def _read_ledger(self) -> dict[str, ExportRow]:
        """The ledger's rows; none when it does not exist. Raises
        ``_LedgerUnreadable`` when it exists but cannot be read (it is
        started again at the next start) and ``_LedgerBusy`` when its file
        could not be looked at or read this time (it is left as it is)."""
        path = self._root / EXPORT_LEDGER_FILENAME
        if _absent(path):
            return {}
        linked = link_state(path)
        if linked is None:
            raise _LedgerBusy
        if linked:
            raise _LedgerUnreadable
        try:
            blob = _read_capped(path, MAX_EXPORT_LEDGER_BYTES)
        except PastSessionError:
            raise _LedgerUnreadable from None
        except OSError as exc:
            raise _LedgerBusy from exc
        try:
            crypto = self._unwrap_ledger_key(self._root)
        except Exception as exc:
            # Review round 21 LOW-001: the KEY file read failing this time (a
            # scanner's lock) is busy too; a missing key, or one that does not
            # unwrap, is damage.
            if _transient(exc):
                raise _LedgerBusy from exc
            raise _LedgerUnreadable from exc
        try:
            try:
                plaintext = crypto.decrypt(blob, _EXPORT_LEDGER_AAD)
            finally:
                crypto.destroy()
            return dict(ExportLedger.model_validate_json(plaintext).rows)
        except Exception as exc:
            raise _LedgerUnreadable from exc

    def _write_ledger(self, rows: dict[str, ExportRow]) -> None:
        """Replace the ledger (atomically) with ``rows`` — its key created
        first when there is none, or when the one there does not unwrap and
        no ledger exists. Raises on failure (the callers decide)."""
        key_path = self._root / EXPORT_LEDGER_KEY_FILENAME
        self._root.mkdir(parents=True, exist_ok=True)
        crypto: SessionCrypto | None = None
        if not _absent(key_path):
            try:
                crypto = self._unwrap_ledger_key(self._root)
            except Exception as exc:
                # Hardening review round 44 SEC-002: a key with NO ledger beside
                # it holds no row (a reset whose key unlink failed), so one that
                # does not unwrap is replaced — kept, it would refuse every
                # later export. A ledger present, or a key read that failed
                # only this time, still raises.
                if _transient(exc) or not _absent(self._root / EXPORT_LEDGER_FILENAME):
                    raise
        if crypto is None:
            crypto = SessionCrypto()
            try:
                self._wrap_ledger_key(crypto, self._root)
            except BaseException:
                crypto.destroy()
                raise
        try:
            atomic_write_bytes(
                self._root / EXPORT_LEDGER_FILENAME,
                # The version is NAMED: the validator refuses a ledger
                # without one, written or read.
                crypto.encrypt(
                    ExportLedger(schema_version=1, rows=rows).to_bytes(), _EXPORT_LEDGER_AAD
                ),
                error_label="export ledger",
            )
        finally:
            crypto.destroy()

    def _reset_ledger(self) -> None:
        """An unreadable ledger is started again: both its files go (a fresh
        key comes with the next row). Never raises."""
        for name in (EXPORT_LEDGER_FILENAME, EXPORT_LEDGER_KEY_FILENAME):
            if not _unlink_quietly(self._root / name):
                self._log(None, "export_ledger_failed")

    def read_entry(self, session_id: str) -> PastSessionEntry:
        """Open a COMMITTED entry through the existing readers.
        ``PastSessionError`` (``not_found``, ``pending`` or ``unreadable``)
        otherwise."""
        entry = self._committed(session_id)
        try:
            crypto = self._unwrap_key(entry)
        except Exception as exc:
            raise PastSessionError("unreadable") from exc
        try:
            label = self._decode_label(entry, crypto)
            if label is None:
                raise PastSessionError("unreadable")
            transcript = read_transcript(entry, crypto)
            saved = read_note(entry, crypto) if _exists(entry / NOTE_FILENAME) else None
            generated = read_generated(entry, crypto, session_id)
        except PastSessionError:
            raise
        except Exception as exc:
            raise PastSessionError("unreadable") from exc
        finally:
            crypto.destroy()
        return PastSessionEntry(label, transcript, saved, generated)

    def read_replay_inputs(
        self, session_id: str
    ) -> tuple[TranscriptDocument, GeneratedNote | None]:
        """The kept-recordings replay's reader (development-recordings review
        round 30): a COMMITTED entry's transcript and saved note (None when
        there is none) — and NOTHING else: the label (the patient's name) and
        the generated note stay encrypted, so an unreadable label does not
        stop a replay either. ``PastSessionError`` (``not_found``,
        ``pending`` or ``unreadable``) otherwise."""
        entry = self._committed(session_id)
        try:
            crypto = self._unwrap_key(entry)
        except Exception as exc:
            raise PastSessionError("unreadable") from exc
        try:
            transcript = read_transcript(entry, crypto)
            saved = read_note(entry, crypto) if _exists(entry / NOTE_FILENAME) else None
        except Exception as exc:
            raise PastSessionError("unreadable") from exc
        finally:
            crypto.destroy()
        return transcript, saved

    # --- deleting -----------------------------------------------------------

    def delete_entry(self, session_id: str) -> None:
        """Delete now (Flow 5) and expiry: the COMMITTED entry's key first —
        its cryptographic deletion (D3) — then its files, best-effort.
        ``PastSessionError`` when there is no such entry or its key cannot
        be deleted."""
        entry = self._committed(session_id)
        if not _remove_key_first(entry):
            # The entry is intact: its remembered date stays good (H1 round
            # 32 LOW-004 — dropping it first re-decrypted the label on every
            # tick until the delete succeeded).
            raise PastSessionError("delete_failed")
        self._forget_dates(entry.name)

    def sweep(self, retention_days: int | None, now: datetime) -> list[str]:
        """``sweep_report``'s deleted ids (the retention sweep as a list)."""
        return [session_id for session_id, _date in self.sweep_report(retention_days, now).expired]

    def sweep_report(
        self,
        retention_days: int | None,
        now: datetime,
        *,
        before_held_delete: Callable[[str, datetime, datetime, bool], object] | None = None,
    ) -> RetentionSweepReport:
        """The retention sweep (Flow 4): delete every committed entry
        completed ``retention_days`` or more before ``now``. ``None``
        ("never") returns at once — nothing is decrypted. An entry with no
        readable date, or one dated in the future, is KEPT (fail toward
        keeping: a broken clock or label never deletes). Each committed
        entry's label is decrypted at most ONCE per process for its date
        (``_completed_dates``; round 11 MED-001); one that cannot be read is
        tried again only ``UNDATED_RETRY_INTERVAL`` after it failed, or
        sooner if the wall clock went back (``_undated``; H1 round 32
        LOW-004), and is counted as undated meanwhile. Reports each id deleted
        with its completion date, how many were due but could not be
        deleted, and whether the walk finished (round 16 MED-002: a
        retention control that fails says so). A window shorter than
        ``MIN_RETENTION_DAYS`` is REFUSED before any read — nothing deleted,
        ``too_short`` set, ``retention_too_short`` logged (the 7-year
        minimum, practitioner decision 2026-10-02; the settings file cannot
        hold one, so this is the second line). Each expired id's audit
        moment (its start, else its completion — review round 16 PR-MED-001)
        is reported in ``started``. ``before_held_delete(id, completed,
        started, recording_gone)`` runs just before an entry holding (or
        that held, deletion not yet tidied — ``recording_gone``) a kept
        recording is deleted — the caller records the kept fact there, and
        for a gone recording its deletion, before the evidence goes
        (development-recordings review round 14 PR-MED-003); for a live
        recording whatever it returns or raises (logged) lets the deletion go
        ahead (the audit never blocks custody), while a gone recording whose
        deletion it did not record (anything but True) is HELD and counted
        as not deleted — retention is a minimum (round 15 PR-MED-002). So is
        an entry the latest ``tidy_dead_recordings`` spared (round 14
        PR-MED-002). NEVER raises."""
        if retention_days is None:
            return RetentionSweepReport()
        if retention_days < MIN_RETENTION_DAYS:
            self._log(None, "retention_too_short")
            return RetentionSweepReport(too_short=True)
        expired: list[tuple[str, datetime]] = []
        starts: list[tuple[str, datetime]] = []
        kept: set[str] = set()
        failed = 0
        undated = 0
        try:
            window = timedelta(days=retention_days)
            present: set[str] = set()
            for entry in self._committed_dirs(strict=True):
                session_id = entry.name
                present.add(session_id)
                completed = self._completed_dates.get(session_id)
                if completed is None:
                    failed_at = self._undated.get(session_id)
                    if (
                        failed_at is not None
                        and timedelta(0) <= now - failed_at < UNDATED_RETRY_INTERVAL
                    ):
                        undated += 1
                        continue  # undated: kept; its label is tried again later
                    label = self._read_label(entry)
                    if label is None:
                        self._undated[session_id] = now
                        undated += 1
                        continue  # undated: kept
                    self._undated.pop(session_id, None)
                    completed = label.completed_at
                    self._completed_dates[session_id] = completed
                    self._started_dates[session_id] = label.moment
                # Round 16 PR-MED-001: read here — the deletion forgets it.
                started = self._started_dates.get(session_id, completed)
                if completed > now + timedelta(seconds=CLOCK_SKEW_TOLERANCE):
                    continue
                if now - completed < window:
                    continue
                if session_id in self._spared:
                    # Round 14 PR-MED-002: its recording's deletion is not yet
                    # recorded — due, but held (counted as not deleted) until
                    # a later sweep records it; retention is a minimum.
                    failed += 1
                    continue
                # Round 13 LOW-001: a deletion not yet tidied counts too.
                # Round 17 PR-MED-001: ONE read decides both.
                recording = _recording_state(entry)
                held_recording = recording != "none"
                recording_gone = recording == "gone"
                if held_recording and before_held_delete is not None:
                    # Review round 14 PR-MED-003: the kept fact is recorded
                    # BEFORE the entry (and its evidence) goes — a true fact
                    # whether or not the deletion then succeeds.
                    try:
                        recorded = before_held_delete(
                            session_id, completed, started, recording_gone
                        )
                    except Exception:  # noqa: BLE001 - the audit never blocks custody (C2)
                        self._log(session_id, "kept_record_failed")
                        recorded = False
                    if recording_gone and recorded is not True:
                        # Round 15 PR-MED-002: a recording deleted but not yet
                        # tidied whose deletion cannot be recorded now is
                        # held as a spared one is (judged afresh, not only
                        # from the latest tidy's spare set).
                        failed += 1
                        continue
                try:
                    self.delete_entry(session_id)
                except PastSessionError:
                    failed += 1
                    continue
                expired.append((session_id, completed))
                starts.append((session_id, started))
                if held_recording:
                    kept.add(session_id)
            for gone in set(self._completed_dates) - present:
                del self._completed_dates[gone]
            for gone in set(self._started_dates) - present:
                del self._started_dates[gone]
            for gone in set(self._undated) - present:
                del self._undated[gone]
        except Exception:  # noqa: BLE001 - a later tick tries again
            self._log(None, "sweep_failed")
            return RetentionSweepReport(
                tuple(expired),
                failed,
                complete=False,
                undated=undated,
                kept=frozenset(kept),
                started=tuple(starts),
            )
        return RetentionSweepReport(
            tuple(expired), failed, undated=undated, kept=frozenset(kept), started=tuple(starts)
        )

    # --- internals ----------------------------------------------------------

    def _log(self, session_id: str | None, code: str) -> None:
        if self._logger is None:
            return
        try:
            if session_id is not None and _SESSION_ID_RE.fullmatch(session_id):
                log_event(self._logger, "past_session", session_id=session_id, detail_code=code)
            else:
                log_event(self._logger, "past_session", detail_code=code)
        except Exception:  # noqa: BLE001 - logging never raises into custody
            pass

    def _entry_dirs(self, *, strict: bool = False) -> Iterator[Path]:
        """The entry folders. A missing root yields nothing; one that cannot
        be listed yields nothing too, unless ``strict`` (the listing and the
        retention sweep), which raises ``PastSessionError("unreadable")``."""
        try:
            children = sorted(self._root.iterdir())
        except FileNotFoundError:
            return
        except OSError:
            if strict:
                raise PastSessionError("unreadable") from None
            return
        for child in children:
            # Round 13 PR-LOW-010: a linked child is not an entry — never
            # listed, read, committed, swept or deleted through.
            if _SESSION_ID_RE.fullmatch(child.name) and not _is_link(child) and child.is_dir():
                yield child

    def _committed_dirs(self, *, strict: bool = False) -> Iterator[Path]:
        for entry in self._entry_dirs(strict=strict):
            if _exists(entry / KEY_FILENAME) and not _exists(entry / PENDING_FILENAME):
                yield entry

    def _committed(self, session_id: str) -> Path:
        try:
            entry = self._root / validate_session_id(session_id)
        except ValueError:
            raise PastSessionError("not_found") from None
        if _is_link(entry) or not _exists(entry / KEY_FILENAME):
            raise PastSessionError("not_found")
        if _exists(entry / PENDING_FILENAME):
            raise PastSessionError("pending")
        return entry

    def _read_label(self, entry: Path) -> PastSessionLabel | None:
        try:
            crypto = self._unwrap_key(entry)
        except Exception:  # noqa: BLE001 - listed as unreadable
            return None
        try:
            return self._decode_label(entry, crypto)
        finally:
            crypto.destroy()

    @staticmethod
    def _decode_label(entry: Path, crypto: SessionCrypto) -> PastSessionLabel | None:
        try:
            plaintext = crypto.decrypt(
                _read_capped(entry / LABEL_FILENAME, MAX_LABEL_FILE_BYTES),
                _label_aad(entry.name),
            )
            label = _parse_label(plaintext)
        except Exception:  # noqa: BLE001 - unreadable, never a raise
            return None
        return label if label.session_id == entry.name else None


def _parse_label(plaintext: bytes) -> PastSessionLabel:
    """A stored label, else ``ValueError`` — the ONE reading rule, used by
    the listing and by the write-time verify (round 24), so a label that
    verifies is one the listing will read. Pilot review round 22 (the
    encounter record's peer round 9 rule): every label this app wrote names
    its version, and the model's defaults are for building one — stored
    bytes naming none would read as v2 not shadow, so they are refused."""
    named = json.loads(plaintext)
    if not isinstance(named, dict) or "schema_version" not in named:
        raise ValueError("not a label")
    return PastSessionLabel.model_validate_json(plaintext)


def sweep_past_sessions(
    root: Path, retention_days: int | None, now: datetime
) -> list[str]:
    """``PastSessionStore(root).sweep`` — the retention sweep as a function
    (the plan's name for it). A one-off: a fresh store has no remembered
    dates, so every call decrypts every label. The app's periodic sweep
    calls ``sweep`` on its ONE shared store instead, so each label is read
    once per process (round 11 MED-001, round 12 LOW-001)."""
    return PastSessionStore(root).sweep(retention_days, now)


# ---------------------------------------------------------------------------
# Filesystem helpers.
# ---------------------------------------------------------------------------


def _read_capped(path: Path, cap: int) -> bytes:
    with path.open("rb") as stream:
        blob = stream.read(cap + 1)
    if len(blob) > cap:
        raise PastSessionError("unreadable")
    return blob


def _require_same(actual: bytes, expected: bytes) -> None:
    if hashlib.sha256(actual).digest() != hashlib.sha256(expected).digest():
        raise PastSessionError("verify_failed")


# ---------------------------------------------------------------------------
# The kept recording (development-recordings plan D5, D6).
# ---------------------------------------------------------------------------


def _stage_audio(
    staging: Path, crypto: SessionCrypto, session_id: str, chunks: Iterator[bytes]
) -> bytes:
    """Copy ``chunks`` (the source session's PCM, one-shot) into
    ``staging/audio.enc`` under a FRESH audio key, chunk by chunk — never
    buffered whole — and write that key, encrypted under the entry key
    ``crypto``, as ``audio-key.enc``. Returns the SHA-256 of the PCM as
    copied. The entry's ``key.dpapi`` must already be written
    (``SessionChunkStore.create`` refuses otherwise). The audio key is
    destroyed, and the source iterator closed, on every path."""
    audio_crypto = SessionCrypto()
    digest = hashlib.sha256()
    try:
        store = SessionChunkStore.create(staging / AUDIO_FILENAME, audio_crypto, session_id)
        try:
            for chunk in chunks:
                digest.update(chunk)
                store.append_chunk(chunk)
            store.finish()
        finally:
            store.close()
        atomic_write_bytes(
            staging / AUDIO_KEY_FILENAME,
            crypto.encrypt(audio_crypto.export_key(), _audio_key_aad(session_id)),
            error_label="past-session audio key",
        )
    finally:
        audio_crypto.destroy()
        if isinstance(chunks, Generator):
            chunks.close()  # the source store's handle, on a failure part-way
    return digest.digest()


def _audio_chunks(entry: Path, crypto: SessionCrypto, session_id: str) -> Iterator[bytes]:
    """The kept recording in ``entry`` (a staged or committed entry) as PCM
    chunks: ``audio-key.enc`` decrypted under the entry key ``crypto``, then
    ``audio.enc`` streamed with its footer required. A zeroed key file is a
    destroyed recording — ``recording_not_kept`` before any decryption. The
    audio key is destroyed when the generator finishes or is closed."""
    blob = _read_capped(entry / AUDIO_KEY_FILENAME, AUDIO_KEY_FILE_BYTES)
    if not blob.strip(b"\0"):
        raise PastSessionError("recording_not_kept")
    audio_crypto = SessionCrypto.from_key(crypto.decrypt(blob, _audio_key_aad(session_id)))
    try:
        yield from iter_chunks(entry / AUDIO_FILENAME, audio_crypto, require_footer=True)
    finally:
        audio_crypto.destroy()


AudioKeyState = Literal["absent", "zeroed", "live", "unknown"]


def _is_own_key_file(status: os.stat_result) -> bool:
    """THE rule for an entry's own ``audio-key.enc`` (review round 13
    LOW-004), read through its open handle: a regular file with no other
    name (``st_nlink``) holding 1–60 bytes — what ``_audio_key_state``
    reads by and ``delete_recording`` zeroes under."""
    return (
        stat.S_ISREG(status.st_mode)
        and status.st_nlink == 1
        and 0 < status.st_size <= AUDIO_KEY_FILE_BYTES
    )


def _audio_key_state(path: Path) -> AudioKeyState:
    """``audio-key.enc``'s state without decrypting it: CONFIRMED absent,
    all zeros (destroyed, cleanup pending), live, or ``unknown`` when it
    cannot be read (which decides nothing). Review round 13 LOW-004: only
    the app's own key file decides — a link, a file that is not regular or
    has another name (``st_nlink``), or a size outside 1–60 bytes is
    ``unknown`` (an empty file is never read as a deletion), by the same
    rule ``delete_recording`` writes under. Never raises."""
    try:
        if link_state(path) is not False:
            return "unknown"
        with path.open("rb") as stream:
            if not _is_own_key_file(os.fstat(stream.fileno())):
                return "unknown"
            blob = stream.read(AUDIO_KEY_FILE_BYTES + 1)
    except FileNotFoundError:
        return "absent"
    except OSError:
        return "unknown"
    return "live" if blob.strip(b"\0") else "zeroed"


RecordingState = Literal["none", "kept", "gone"]


def _recording_state(entry: Path) -> RecordingState:
    """What ``entry`` holds of a kept recording, from ONE read of its key
    file (review round 17 PR-MED-001: a destroyer decides from one read,
    never two that a transient error can make disagree). ``kept`` (D4/D6):
    ``audio.enc`` present and the key file present and not zeroed — a key
    file that cannot be read counts as present (``_exists``'s direction:
    shown, so it can be deleted). ``gone`` — deleted and not yet tidied: the
    key file CONFIRMED zeroed, or CONFIRMED gone with ``audio.enc``
    CONFIRMED present as a regular file, never a link, which no recording is
    (review round 12 LOW-005). Otherwise ``none``. Never raises."""
    key = _audio_key_state(entry / AUDIO_KEY_FILENAME)
    if key == "zeroed":
        return "gone"
    if key == "absent":
        try:
            status = os.lstat(entry / AUDIO_FILENAME)
        except OSError:
            return "none"
        return "gone" if stat.S_ISREG(status.st_mode) else "none"
    return "kept" if _exists(entry / AUDIO_FILENAME) else "none"


def _recording_kept_in(entry: Path) -> bool:
    """D4/D6: ``entry`` holds a kept recording (``_recording_state``)."""
    return _recording_state(entry) == "kept"


def _recording_deleted_in(entry: Path) -> bool:
    """``entry`` held a kept recording that was deleted and not yet tidied
    (``_recording_state``); anything that cannot be read decides nothing."""
    return _recording_state(entry) == "gone"


def _part_path(folder: str | Path, session_id: str) -> Path:
    """An export's temporary file: ``<folder>\\<session id>.wav.part``."""
    return Path(folder) / f"{session_id}{EXPORT_PART_SUFFIX}"


class PartKernel(Protocol):
    """The Windows calls ``_remove_part`` makes (codex round 24 PR-MED-001),
    behind ONE seam: the file is opened ONCE — exclusively, never through a
    link — and that same handle is identified and marked for deletion, so
    nothing can be swapped in at the path between the check and the delete.
    ``Win32PartKernel`` is the real one; tests inject a double (the conftest
    pins ``part_kernel``), and no test reaches the real Windows API."""

    def open(self, path: Path) -> int:
        """An exclusive descriptor on ``path`` itself (no sharing; a link
        opened as itself). ``FileNotFoundError`` when it — or its folder —
        is not there; any other ``OSError`` when it cannot be opened."""
        ...

    def status(self, descriptor: int) -> os.stat_result:
        """``os.fstat`` of that descriptor — the same identity the export
        recorded from its own descriptor."""
        ...

    def mark_deleted(self, descriptor: int) -> None:
        """Mark the OPEN file for deletion when it is closed. Raises
        ``OSError`` when Windows refuses."""
        ...

    def close(self, descriptor: int) -> None: ...


_DELETE: Final = 0x00010000
_FILE_READ_ATTRIBUTES: Final = 0x0080
_FILE_FLAG_OPEN_REPARSE_POINT: Final = 0x00200000
_OPEN_EXISTING: Final = 3
_FILE_DISPOSITION_INFO_CLASS: Final = 4  # FileDispositionInfo


class Win32PartKernel:
    """The real ``PartKernel``: ``_winapi.CreateFile`` (share mode 0, the
    reparse point opened as itself) handed to an ``msvcrt`` descriptor,
    ``os.fstat`` on it, and ``SetFileInformationByHandle(FileDispositionInfo)``
    through ``ctypes`` — the standard library only. Windows only; never
    built in tests."""

    def open(self, path: Path) -> int:
        import _winapi
        import msvcrt

        handle = _winapi.CreateFile(
            str(path),
            _DELETE | _FILE_READ_ATTRIBUTES,
            0,
            0,
            _OPEN_EXISTING,
            _FILE_FLAG_OPEN_REPARSE_POINT,
            0,
        )
        try:
            return int(msvcrt.open_osfhandle(handle, os.O_RDONLY))
        except BaseException:
            _winapi.CloseHandle(handle)
            raise

    def status(self, descriptor: int) -> os.stat_result:
        return os.fstat(descriptor)

    def mark_deleted(self, descriptor: int) -> None:
        import ctypes
        import msvcrt
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        set_information = kernel32.SetFileInformationByHandle
        set_information.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        set_information.restype = wintypes.BOOL
        delete_file = ctypes.c_ubyte(1)  # FILE_DISPOSITION_INFO { BOOLEAN DeleteFile; }
        handle = msvcrt.get_osfhandle(descriptor)
        if not set_information(
            handle, _FILE_DISPOSITION_INFO_CLASS, ctypes.byref(delete_file), 1
        ):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self, descriptor: int) -> None:
        os.close(descriptor)


def part_kernel() -> PartKernel:
    """The ``PartKernel`` in use — the conftest pins a double (C6)."""
    return Win32PartKernel()


def _remove_part(path: Path, identity: ExportIdentity, kernel: PartKernel | None = None) -> bool:
    """Task 3.3: remove an export's ``.part`` file ONLY while it is still the
    file the app created — a regular file (not a link or other reparse
    point) with the recorded identity (file index and volume). True when it
    is gone (removed, or CONFIRMED absent); False when it is still there —
    another identity (a file the practitioner put there, never deleted), a
    file another program holds open, or a removal Windows refused — and the
    caller then KEEPS its ledger row. Never raises.

    Codex round 24 PR-MED-001: the identity is read from, and the deletion
    made through, ONE exclusive handle (``PartKernel``) — never a check by
    path followed by a delete by path, which a file swapped in between would
    have turned into deleting the practitioner's file. Anything that does not
    secure the file that way keeps it.

    A missing FOLDER also reads "not found" and counts as gone (review
    round 20 LOW-005, kept): an export folder deleted by hand would
    otherwise hold its row — and refuse every later export — for ever, and
    the destination check admits only this computer's fixed drives."""
    kernel = kernel if kernel is not None else part_kernel()
    try:
        descriptor = kernel.open(path)
    except FileNotFoundError:
        return True
    except Exception:  # noqa: BLE001 - not secured: the row is kept
        return False
    try:
        status = kernel.status(descriptor)
        reparse = getattr(status, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        owned = (
            stat.S_ISREG(status.st_mode)
            and not reparse
            and (status.st_ino, status.st_dev) == (identity.file_index, identity.device)
        )
        if owned:
            kernel.mark_deleted(descriptor)
    except Exception:  # noqa: BLE001 - not secured: the row is kept
        owned = False
    if not owned:
        _close_quietly(kernel, descriptor)  # never marked: the file stays as it was
        return False
    try:
        kernel.close(descriptor)  # the deletion happens as the handle closes
    except Exception:  # noqa: BLE001 - unknown: the row is kept; the next start looks again
        return False
    return True


def _close_quietly(kernel: PartKernel, descriptor: int) -> None:
    try:
        kernel.close(descriptor)
    except Exception:  # noqa: BLE001 - the file is left as it was
        pass


def _transient(exc: BaseException) -> bool:
    """A key read that failed with an ``OSError`` other than "not found" —
    itself or as the cause ``unwrap_key_from_file`` wraps in
    ``KeyCustodyError`` — may succeed next time (review round 21 LOW-001)."""
    for error in (exc, exc.__cause__):
        if isinstance(error, OSError) and not isinstance(error, FileNotFoundError):
            return True
    return False


def _unlink_quietly(path: Path) -> bool:
    """Unlink ``path``: True when it is gone afterwards. Never raises."""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return False
    return True


def _exists(path: Path) -> bool:
    """True when ``path`` is there. An error other than absence reads as
    present — the direction that never commits, lists as gone, or deletes."""
    try:
        path.stat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def _absent(path: Path) -> bool:
    """True ONLY when ``path`` is CONFIRMED absent (C1: an inaccessible key
    is never treated as absent)."""
    try:
        path.stat()
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return False


def _is_link(path: Path) -> bool:
    """True when ``path`` is a symlink or a directory junction (round 13
    PR-LOW-010) — Windows resolves either mid-path, so ``<link>\\key.dpapi``
    names the TARGET's key. A status that cannot be read counts as a link:
    the direction that never follows (``session_store.link_state``, H3 round
    35 SEC-001 — ``Path.is_symlink`` swallows that error from Python 3.13)."""
    return link_state(path) is not False


def _remove_key_first(directory: Path) -> bool:
    """Delete ``directory``'s ``key.dpapi`` FIRST, then the rest best-effort.
    True when the key is gone (or the directory never existed); False when
    the key could not be deleted — nothing else is touched then. Never
    raises. A ``directory`` that is a link is REFUSED (False, untouched):
    deleting through it would delete its target's key (round 13
    PR-LOW-010); a caller that must place something there then fails
    closed."""
    if _is_link(directory):
        return False
    try:
        (directory / KEY_FILENAME).unlink(missing_ok=True)
    except FileNotFoundError:
        pass  # the directory itself is absent
    except OSError:
        return False
    # Development-recordings plan D6: a kept recording's audio key goes next,
    # best-effort — belt and braces, never load-bearing (the audio is already
    # dead under the entry key), and never deciding the result.
    _unlink_quietly(directory / AUDIO_KEY_FILENAME)
    shutil.rmtree(directory, ignore_errors=True)
    return True


def _remove_key_first_unless_link(directory: Path) -> bool:
    """``remove_pending_entry``'s removal: a CONFIRMED link is not ours
    (never listed, committed or followed), so it counts as nothing to
    remove — True, left in place untouched. Anything else is
    ``_remove_key_first``. A path whose link status cannot be read is
    neither (H1 round 32 LOW-001): ``_is_link``'s "an error counts as a
    link" is the safe direction for following, but here True is the
    destroyer's go-ahead to delete the SOURCE key — so it is False, and the
    key stays this time (read through ``session_store.link_state``: from
    Python 3.13 ``Path.is_symlink`` swallows that error — H3 round 35
    SEC-001)."""
    linked = link_state(directory)
    if linked is None:
        return False
    return True if linked else _remove_key_first(directory)


# ---------------------------------------------------------------------------
# The settings file (D13; Schema / Data Changes).
# ---------------------------------------------------------------------------


class PastSessionSettings(BaseModel):
    """On-disk shape of ``config\\past_sessions.json``:
    ``{"schema_version": 1, "retention_days": int | null, "hide_names": bool}``.
    Absent file = the defaults (retention "never", names shown — D13).
    ``retention_days`` must be one of ``RETENTION_DAYS_CHOICES`` or null; an
    unknown version or value fails loudly rather than parsing as a default.
    The one exception is a window an earlier build offered
    (``LEGACY_RETENTION_DAYS``): it reads as ``MIN_RETENTION_DAYS`` (the
    7-year minimum, practitioner decision 2026-10-02), so the upgrade never
    fails closed, and the next save writes 7 years."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    # STRICT (round 13 PR-LOW-011): lax mode would read JSON ``true``, ``1.0``
    # or ``"1"`` as 1 — the shortest, most destructive retention — before
    # the choice check; a hand-edited file must fail loudly instead.
    retention_days: int | None = Field(default=None, strict=True)
    hide_names: bool = Field(default=False, strict=True)

    @field_validator("retention_days", mode="before")
    @classmethod
    def _raise_a_legacy_window(cls, value: object, info: ValidationInfo) -> object:
        """A removed shorter window -> 7 years, BEFORE the strict type check.
        Only a genuine ``int`` is mapped (``type(...) is int``: JSON ``true``
        or ``1.0`` compare equal to 1 and must still be refused by the strict
        check). A caller that passes a dict as the validation context learns
        that a value was raised (``RAISED_CONTEXT_KEY``)."""
        if type(value) is int and value in LEGACY_RETENTION_DAYS:
            if isinstance(info.context, dict):
                info.context[RAISED_CONTEXT_KEY] = True
            return MIN_RETENTION_DAYS
        return value

    @field_validator("retention_days")
    @classmethod
    def _a_choice(cls, value: int | None) -> int | None:
        if value is not None and value not in RETENTION_DAYS_CHOICES:
            raise ValueError("retention_days is not one of the offered settings")
        return value

    def to_bytes(self) -> bytes:
        return (self.model_dump_json(indent=2) + "\n").encode("utf-8")


@dataclass(frozen=True)
class LoadedPastSessionSettings:
    """``read_past_session_settings``'s answer: the settings, and whether
    the file held a removed shorter window that now reads as 7 years
    (``retention_raised`` — true until the next save rewrites the file)."""

    settings: PastSessionSettings
    retention_raised: bool = False


def read_past_session_settings(config_root: Path | None = None) -> LoadedPastSessionSettings:
    """The settings file, or the defaults when it does not exist, with
    whether a removed shorter window was raised to 7 years on the way in.
    An existing file that cannot be read or parsed raises
    ``PastSessionSettingsError`` — never a silent fallback (the retention
    sweep then deletes nothing)."""
    root = config_root if config_root is not None else default_config_root()
    try:
        blob = _read_capped(root / SETTINGS_FILENAME, MAX_SETTINGS_FILE_BYTES)
    except FileNotFoundError:
        return LoadedPastSessionSettings(PastSessionSettings())
    except OSError as exc:
        raise PastSessionSettingsError(f"{SETTINGS_FILENAME} could not be read") from exc
    except PastSessionError:  # over its bound (H3 round 35 SEC-005)
        raise PastSessionSettingsError(f"{SETTINGS_FILENAME} is not valid") from None
    context: dict[str, bool] = {}
    try:
        settings = PastSessionSettings.model_validate_json(blob, context=context)
    except ValidationError as exc:
        raise PastSessionSettingsError(f"{SETTINGS_FILENAME} is not valid") from exc
    return LoadedPastSessionSettings(settings, context.get(RAISED_CONTEXT_KEY, False))


def load_past_session_settings(config_root: Path | None = None) -> PastSessionSettings:
    """``read_past_session_settings``'s settings alone."""
    return read_past_session_settings(config_root).settings


def save_past_session_settings(
    settings: PastSessionSettings, *, config_root: Path | None = None
) -> Path:
    """Replace the settings file atomically through the config directory's
    one write path (``note_config._write_config_file``);
    ``PastSessionSettingsError`` on any failure, the file never partial."""
    root = config_root if config_root is not None else default_config_root()
    try:
        _write_config_file(root, SETTINGS_FILENAME, settings.to_bytes())
    except NoteConfigError as exc:
        raise PastSessionSettingsError(f"{SETTINGS_FILENAME} could not be written") from exc
    return root / SETTINGS_FILENAME
