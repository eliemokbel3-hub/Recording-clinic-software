"""The Past-sessions archive (privacy-professional-controls plan Task 2.2;
D1, D3, D5, D6, D13; Critical Constraints C1 and C4).

At every non-mock Complete the app keeps, encrypted, the session's
transcript, its saved note and its generated note — never audio. On-disk
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
    keeps until its Complete has deleted the source key (C1).

- ``.staging\\<session id>\\`` — where an entry is built and verified before
  it is moved into place; ``clean_staging`` removes whatever a crash left
  there, at every start-up and sweep tick, whatever the retention setting.

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

What this store never holds: audio (C4 — the source session's key, which
also encrypted ``audio.enc``, is still deleted), the source key, or an
audit id. The patient's name lives only in ``label.enc``.

Threading: every method runs on the GUI thread (the controller's custody
calls under its lock, the sweep timer), like the stores it sits beside
(C5). Nothing here touches the network.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import shutil
import unicodedata
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final, Literal

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
    CLOCK_SKEW_TOLERANCE,
    GENERATED_FILENAME,
    KEY_FILENAME,
    NOTE_FILENAME,
    SESSION_ID_PATTERN,
    TRANSCRIPT_FILENAME,
    ArchiveSource,
    GeneratedRecord,
    atomic_write_bytes,
    generated_aad,
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
STAGING_DIRNAME: Final = ".staging"
SETTINGS_FILENAME: Final = "past_sessions.json"
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
}


class PastSessionError(Exception):
    """A Past-sessions operation failed (``reason`` is a
    ``PAST_SESSION_REASONS`` code; the text is authored). The cause, when
    chained, is for diagnosis only."""

    def __init__(self, reason: str) -> None:
        super().__init__(PAST_SESSION_REASONS.get(reason, reason))
        self.reason = reason


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

    def to_bytes(self) -> bytes:
        return self.model_dump_json().encode("utf-8")


def _label_aad(session_id: str) -> bytes:
    """Distinct from every other artifact's, and bound to the entry."""
    return b"past-label:" + validate_session_id(session_id).encode("ascii")


@dataclass(frozen=True)
class PastSessionListing:
    """One COMMITTED entry as the list shows it: its label, or None when the
    label cannot be read (the entry is still listed, so it can be deleted)."""

    session_id: str
    label: PastSessionLabel | None = field(repr=False)


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
# The store.
# ---------------------------------------------------------------------------

WrapKey = Callable[[SessionCrypto, Path], object]
UnwrapKey = Callable[[Path], SessionCrypto]


def _wrap_entry_key(crypto: SessionCrypto, directory: Path) -> object:
    return wrap_key_to_file(crypto, directory, description=PAST_SESSION_KEY_DESCRIPTION)


def _unwrap_entry_key(directory: Path) -> SessionCrypto:
    return unwrap_key_from_file(directory, description=PAST_SESSION_KEY_DESCRIPTION)


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
    ) -> None:
        self._root = root if root is not None else default_past_sessions_root()
        self._clock = clock
        self._logger = logger
        self._wrap_key = wrap_key
        self._unwrap_key = unwrap_key
        # The retention sweep's dates (review round 11 MED-001): a committed
        # entry's ``completed_at`` never changes, so each is decrypted ONCE
        # per process, not on every hourly tick (C5: the sweep runs on the
        # GUI thread; years of entries would otherwise mean one key unwrap
        # each, every hour). Content-free — a date per session id, never a
        # name. Dropped whenever this store writes, publishes or removes
        # the id's entry.
        self._completed_dates: dict[str, datetime] = {}
        # The retention sweep's unreadable labels (H1 round 32 LOW-004, the
        # same class): when each id's label last failed to read, so an entry
        # whose key or label cannot be read (D9's broken DPAPI makes that
        # every entry) is retried once per ``UNDATED_RETRY_INTERVAL``, not
        # unwrapped again on every hourly tick. Still counted as undated
        # (kept) every tick. Dropped with the date cache's rule.
        self._undated: dict[str, datetime] = {}

    def _forget_dates(self, session_id: str) -> None:
        """The date caches' one rule: whenever this store writes, publishes
        or removes ``session_id``'s entry, both caches forget it (H2 round 34
        SIMP-002)."""
        self._completed_dates.pop(session_id, None)
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
            expected = self._stage(staging, source, document)
            stage = "verify_failed"
            self._verify_staged(staging, source, document, expected)
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
    ) -> frozenset[str]:
        """Write the entry into ``staging`` under a FRESH key; returns the
        exact file set it must hold."""
        session_id = source.session_id
        crypto = SessionCrypto()
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
            atomic_write_bytes(staging / PENDING_FILENAME, b"", error_label="pending marker")
        finally:
            crypto.destroy()
        return frozenset({KEY_FILENAME, PENDING_FILENAME, *files})

    def _verify_staged(
        self,
        staging: Path,
        source: ArchiveSource,
        document: PastSessionLabel,
        expected: frozenset[str],
    ) -> None:
        """D1's full verification, through the entry's OWN key read back from
        disk: exactly the expected files; the label as written; every
        plaintext's SHA-256 equal to the source bytes; and the existing
        readers (``read_transcript``, ``read_note`` — which re-checks the
        note's session binding and transcript digest — ``read_generated``)
        accepting what they will later read. Raises on any difference."""
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
        counts as nothing to remove and is left in place, untouched."""
        try:
            validate_session_id(session_id)
        except ValueError:
            return True  # not a session id: nothing of ours can exist for it
        self._forget_dates(session_id)
        removed = True
        if not self._staging_linked():
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
            listings.append(PastSessionListing(entry.name, self._read_label(entry)))
        return listings

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

    def sweep_report(self, retention_days: int | None, now: datetime) -> RetentionSweepReport:
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
        hold one, so this is the second line). NEVER raises."""
        if retention_days is None:
            return RetentionSweepReport()
        if retention_days < MIN_RETENTION_DAYS:
            self._log(None, "retention_too_short")
            return RetentionSweepReport(too_short=True)
        expired: list[tuple[str, datetime]] = []
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
                if completed > now + timedelta(seconds=CLOCK_SKEW_TOLERANCE):
                    continue
                if now - completed < window:
                    continue
                try:
                    self.delete_entry(session_id)
                except PastSessionError:
                    failed += 1
                    continue
                expired.append((session_id, completed))
            for gone in set(self._completed_dates) - present:
                del self._completed_dates[gone]
            for gone in set(self._undated) - present:
                del self._undated[gone]
        except Exception:  # noqa: BLE001 - a later tick tries again
            self._log(None, "sweep_failed")
            return RetentionSweepReport(tuple(expired), failed, complete=False, undated=undated)
        return RetentionSweepReport(tuple(expired), failed, undated=undated)

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
