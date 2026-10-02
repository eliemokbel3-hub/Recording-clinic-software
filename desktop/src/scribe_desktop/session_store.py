"""Encrypted session store + DPAPI key custody (Phase 2 Step 2).

On-disk layout (plan Schema / Data Changes), all under
``%LOCALAPPDATA%\\ClinikoScribe\\sessions\\<session_id>\\`` (``ClinikoScribe-dev``
from a source checkout — ``install_layout``):

- ``key.dpapi``   — the per-session AES-256-GCM key, DPAPI-wrapped
  (CryptProtectData, current-user scope). Deleting this blob IS the
  cryptographic deletion of the session at the same-user trust boundary
  (NTFS forensic residual accepted — plan Key Design Decision).
- ``audio.enc``   — append-only chunk store: fixed plaintext header
  (magic, version, session id, created-at, audio format), then
  length-prefixed AES-GCM records. Every record uses a FRESH RANDOM
  12-byte nonce (never counter-derived: a crash-restored counter risks
  catastrophic nonce reuse) and binds the chunk index as AAD (cheap
  reorder detection). A sealed FOOTER record with the final chunk count
  is written at Finish so post-Finish truncation is detectable.
- ``transcript.enc`` — written by the Phase-2 transcription step; this
  module only provides the Complete-ordering primitive that consumes it.
- ``note.enc`` — written by the Phase-3A note pipeline under the SAME key;
  read here by the same Complete-ordering primitive, by ``read_note`` (the
  review view) and by ``saved_note_identity`` (the draft write's SHA-256 of
  the saved plaintext, D5).
- ``encounter.enc`` — the recording's consent and Cliniko note context
  (Cliniko workflow safeguards plan D11), under the SAME key with the
  associated data ``encounter:<session id>``; written by
  ``SessionController.start`` between ``key.dpapi`` and ``audio.enc``.
  Discard's ``rmtree`` and the sweep remove it with the rest.
- ``write.enc`` — the Cliniko draft write's record (cliniko-draft-write plan
  D5): one document, rewritten atomically at every transition, under the
  SAME key with the associated data ``write:<session id>``. The document is
  ``draft_write.WriteRecord``'s; this module holds only the bytes' custody
  (a missing file reads as None, anything else unreadable as a terse
  ``StoreCorruptError``, never as "no record").
  Discard's ``rmtree`` and the sweep remove it with the rest.
- ``saved-provenance.enc`` — the saved note's model provenance (privacy-
  professional-controls plan D8): ids and the saved note's digest, never
  text, under the SAME key with the associated data
  ``saved-provenance:<session id>``. Complete reads it for the audit's
  completion facts; it dies with the session.
- ``generated.enc`` — the FIRST note body the review showed (privacy-
  professional-controls plan D2), with its provider, style and model ids,
  under the SAME key with the associated data ``generated:<session id>``;
  replaced on regeneration. Complete copies it into the Past-sessions entry;
  it dies with the session.

Durability ordering (BINDING, plan key-custody decision):
- ``key.dpapi`` is written atomically (temp + fsync + ``os.replace``)
  BEFORE the first chunk — ``SessionChunkStore.create`` refuses to create
  ``audio.enc`` unless the key blob already exists beside it.
- Complete: fsync ``transcript.enc`` → verify a decrypt round-trip →
  verify ``note.enc`` when one exists (decrypt, parse, session binding,
  transcript-digest match) → write, verify and publish the Past-sessions
  entry when the caller asks for one (privacy-professional-controls plan
  C1 / D4) → THEN delete the key. Every failure up to there retains the
  key, which is what keeps regeneration (and a retry) possible. After the
  key: the entry's ``pending`` marker is removed and the directory removed,
  both best-effort (Task 1.1; a failed removal leaves a keyless orphan the
  sweep's ``orphan_gc`` removes, and a marker left behind is committed by
  the next reconciliation).
- Discard: delete the key FIRST, then best-effort remove the rest.
- The 24 h expiry sweep skips sessions the caller reports as live
  (recording/paused/processing — keyed off state, not mtime), destroys
  expired sessions key-first, GCs orphan dirs with no key, and treats
  zero-length/truncated key blobs as already cryptographically dead.

Read path mirrors ``framing.py``: a declared record length beyond the
bound is rejected WITHOUT allocating the buffer; a truncated tail is
tolerated as expected crash behaviour (complete records still decrypt).

Disk-write failure (full/failing disk) raises ``StoreWriteError`` — the
session machine (Step 4) maps it to state=``failed`` (recoverable);
never silent data loss.

No custom cryptography — ``cryptography`` AESGCM via ``SessionCrypto``
only (Critical Constraint). Plaintext audio exists only in the byte
buffers passed through ``append_chunk``/``iter_chunks``.
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import re
import shutil
import stat as _stat
import struct
import sys
import time
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field, replace
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO, Final, Literal, NamedTuple, Protocol

from cryptography.exceptions import InvalidTag
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError
from pydantic_core import PydanticSerializationError

from scribe_desktop import install_layout
from scribe_desktop.logging_setup import log_event
from scribe_desktop.secure_storage import SessionCrypto

if TYPE_CHECKING:
    # Annotation-only: note.py imports THIS module at import time (for
    # SESSION_ID_PATTERN and atomic_write_bytes), so the note and config
    # types are imported at call time in the functions below.
    from scribe_desktop.note import GeneratedNote
    from scribe_desktop.note_config import NoteConfig

KEY_FILENAME: Final = "key.dpapi"
AUDIO_FILENAME: Final = "audio.enc"
TRANSCRIPT_FILENAME: Final = "transcript.enc"
# Phase 3A: the generated note artifact, under the SAME session key as audio
# and transcript, so deleting the session key destroys every copy held in
# THIS directory (any copy another store keeps is under that store's own key).
NOTE_FILENAME: Final = "note.enc"
# Cliniko workflow safeguards plan D11: the recording's consent and, when
# linked, its Cliniko note context — written on EVERY start, after the key
# and before ``audio.enc``, under the SAME key with its own associated data.
ENCOUNTER_FILENAME: Final = "encounter.enc"
# Cliniko draft-write plan D5: the session's ONE write record — ids, digests
# and the outcome, never note text — under the SAME key with the associated
# data ``write:<session id>``; destroyed with the session.
WRITE_RECORD_FILENAME: Final = "write.enc"
# Privacy-professional-controls plan D2: the first note body the review showed,
# under the SAME key with the associated data ``generated:<session id>``.
GENERATED_FILENAME: Final = "generated.enc"

_MAGIC: Final = b"CSS2"
_FORMAT_VERSION: Final = 1
# Fixed plaintext header: magic, version, session id (32 hex chars),
# created-at (unix seconds), sample rate, channels, sample width (bytes).
# Header content is non-clinical metadata only.
_HEADER = struct.Struct("<4sB32sdIHH")
_LENGTH = struct.Struct("<I")
_U64 = struct.Struct("<Q")

_REC_CHUNK: Final = 0x01
_REC_FOOTER: Final = 0x02

_NONCE_BYTES: Final = 12
_TAG_BYTES: Final = 16
# ~1 s of 16 kHz mono PCM16 is 32 000 B; 1 MiB gives ample headroom while
# keeping reject-without-allocation meaningful (mirrors framing.py policy).
MAX_CHUNK_PLAINTEXT_BYTES: Final = 1_048_576
_MIN_RECORD_BYTES: Final = 1 + _NONCE_BYTES + _TAG_BYTES
MAX_RECORD_BYTES: Final = _MIN_RECORD_BYTES + MAX_CHUNK_PLAINTEXT_BYTES
# Record-count bound (GCM safety margin; fail safe, never silently exceed).
# 24 h of 1 s chunks is 86 400 records; 1 000 000 stays far below the
# NIST SP 800-38D random-nonce invocation bound (2^32).
MAX_RECORDS: Final = 1_000_000

# Anything smaller cannot be a real DPAPI blob — zero-length/truncated key
# blobs are already cryptographically dead (sweep destroys the session).
_MIN_KEY_BLOB_BYTES: Final = 16


def key_blob_is_dead(size_bytes: int) -> bool:
    """True when a key.dpapi of this size is cryptographically dead
    (zero-length/truncated — cannot be a real DPAPI blob). THE single
    deadness definition: custody unwrap, the sweep's orphan GC, and the
    recovery listing must all agree (round 42 LOW-004)."""
    return size_bytes < _MIN_KEY_BLOB_BYTES

# Binding note from Step 1 (PR-MED-002/003): a session id is EXACTLY
# uuid4().hex, and key_reference resolves ONLY through resolve_key_path.
# SESSION_ID_PATTERN is THE single source of the id format (round 42
# LOW-010): the pydantic models and the recovery listing reference it.
SESSION_ID_PATTERN: Final = r"^[0-9a-f]{32}$"
_SESSION_ID_RE: Final = re.compile(SESSION_ID_PATTERN)

RECOVERY_WINDOW: Final = timedelta(hours=24)

# Filesystem timestamps can read marginally AHEAD of a later time.time().
# Windows' wall clock is coarse — on Python <= 3.12 time.time() comes from
# GetSystemTimeAsFileTime() at ~15.6 ms granularity, while NTFS records mtimes
# at 100 ns — and FAT-family volumes round mtimes up to a 2 s boundary. So a
# file written moments ago can carry a stamp a fraction of a second in the
# "future". The fail-closed rule below reads any future stamp as untrusted and
# ACTS on it, which for a freshly created session means the sweep expiring it
# (cryptographic deletion) or the recovery listing hiding it. Tolerate skew up
# to this bound — orders of magnitude above both quirks, and 0.006% of the 24 h
# window — and keep failing closed beyond it, where a future stamp really does
# mean a broken or tampered clock.
CLOCK_SKEW_TOLERANCE: Final = 5.0  # seconds

_FOOTER_AAD: Final = b"footer"


def _chunk_aad(index: int) -> bytes:
    return b"chunk:" + _U64.pack(index)


class SessionStoreError(Exception):
    """Base class for session-store failures."""


class StoreCorruptError(SessionStoreError):
    """The store violates its format or an AEAD check failed (tamper/reorder,
    post-Finish truncation, oversized declared record, count mismatch)."""


class StoreStateError(SessionStoreError):
    """The operation is illegal in the store's current state (e.g. appending
    to a finished store, creating audio before key custody exists)."""


class StoreLimitError(SessionStoreError):
    """The record-count bound would be exceeded — fail safe, never silently
    continue past the GCM safety margin."""


class StoreWriteError(SessionStoreError):
    """A disk write failed (disk full / failing disk). Recoverable: the
    session transitions to `failed`, never silent data loss."""


class KeyCustodyError(SessionStoreError):
    """Key custody blob is missing, truncated, or cannot be unwrapped —
    the session's data is cryptographically unrecoverable."""


class NoteWriteRefusedError(SessionStoreError):
    """``write_note`` refused the artifact — an unresolved ``error`` warning,
    an unbacked clinician-authored assertion, or a digest/binding mismatch.
    Nothing was written; the on-disk state is unchanged."""


class ArchiveWriteError(SessionStoreError):
    """``complete_session`` could not write, verify or publish the Past-
    sessions entry it was asked for (privacy-professional-controls plan C1):
    raised BEFORE the key boundary, so the session key is retained and the
    Complete can be retried. The cause is chained for diagnosis only — the
    controller turns this into ``PastSessionWriteError``, whose text is
    authored."""


def default_sessions_root() -> Path:
    # Deliberately NO UNC refusal here (round 42 LOW-005): a
    # folder-redirected LOCALAPPDATA would place session stores on SMB —
    # refusing would block recording entirely, so this stays an accepted
    # same-user deployment residual (documented in the data-flow map).
    # Model paths DO refuse UNC: there refusal is cheap and report-only.
    return install_layout.data_root() / "sessions"


def validate_session_id(session_id: str) -> str:
    if not _SESSION_ID_RE.fullmatch(session_id):
        raise ValueError("session_id must be exactly 32 lowercase hex chars")
    return session_id


def resolve_key_path(root: Path, session_id: str) -> Path:
    """THE ONLY legal resolution of RecordingSession.key_reference (binding
    Step-1 note): <sessions root>/<validated session_id>/key.dpapi."""
    return root / validate_session_id(session_id) / KEY_FILENAME


@dataclass(frozen=True)
class StoreHeader:
    session_id: str
    created_at: float
    sample_rate: int
    channels: int
    sample_width: int


def _read_header(stream: BinaryIO) -> StoreHeader:
    raw = stream.read(_HEADER.size)
    if len(raw) != _HEADER.size:
        raise StoreCorruptError("store header truncated")
    magic, version, sid_raw, created_at, sample_rate, channels, sample_width = _HEADER.unpack(raw)
    if magic != _MAGIC:
        raise StoreCorruptError("bad store magic")
    if version != _FORMAT_VERSION:
        raise StoreCorruptError(f"unsupported store version {version}")
    try:
        session_id = validate_session_id(sid_raw.decode("ascii"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise StoreCorruptError("invalid session id in header") from exc
    return StoreHeader(session_id, created_at, sample_rate, channels, sample_width)


def read_store_header(path: Path) -> StoreHeader:
    with path.open("rb") as stream:
        return _read_header(stream)


class SessionChunkStore:
    """Append-only encrypted chunk store — the SINGLE writer owns this
    object (plan Concurrency model: capture worker holds the handle)."""

    def __init__(
        self, path: Path, crypto: SessionCrypto, stream: BinaryIO, next_index: int
    ) -> None:
        self._path = path
        self._crypto = crypto
        self._stream: BinaryIO | None = stream
        self._next_index = next_index
        self._finished = False

    @property
    def path(self) -> Path:
        return self._path

    @property
    def next_index(self) -> int:
        return self._next_index

    @classmethod
    def create(
        cls,
        path: Path,
        crypto: SessionCrypto,
        session_id: str,
        *,
        sample_rate: int = 16_000,
        channels: int = 1,
        sample_width: int = 2,
        created_at: float | None = None,
        require_key: bool = True,
    ) -> SessionChunkStore:
        """Create a fresh store. Refuses (durability ordering, binding) unless
        the DPAPI key blob already exists beside it — key BEFORE first chunk.
        `require_key=False` exists ONLY for store-format unit tests."""
        validate_session_id(session_id)
        if require_key and not (path.parent / KEY_FILENAME).exists():
            raise StoreStateError("key.dpapi must be durably written before the first chunk")
        header = _HEADER.pack(
            _MAGIC,
            _FORMAT_VERSION,
            session_id.encode("ascii"),
            time.time() if created_at is None else created_at,
            sample_rate,
            channels,
            sample_width,
        )
        try:
            stream: BinaryIO = path.open("xb")
        except OSError as exc:
            raise StoreWriteError(f"failed creating store file: {exc}") from exc
        try:
            stream.write(header)
            stream.flush()
            os.fsync(stream.fileno())
        except OSError as exc:
            stream.close()
            path.unlink(missing_ok=True)  # never leave a headerless store behind
            raise StoreWriteError(f"failed writing store header: {exc}") from exc
        return cls(path, crypto, stream, 0)

    @classmethod
    def open_for_append(cls, path: Path, crypto: SessionCrypto) -> SessionChunkStore:
        """Reopen after a crash: scan complete records, truncate any partial
        tail record (expected crash behaviour), resume at the next index.
        Refuses to append to a finished (footered) store.

        NOT wired into any production flow (round 42 LOW-008): recording
        is NEVER resumed after a crash (plan Critical Constraint — recovery
        restarts TRANSCRIPTION, not capture). This reopen-and-append
        primitive exists for the store-format contract and its validation
        battery (restart-append nonce safety) only; do not wire it into a
        resume-recording flow."""
        try:
            scan_stream: BinaryIO = path.open("rb")
        except OSError as exc:
            raise StoreWriteError(f"failed opening store for recovery scan: {exc}") from exc
        with scan_stream as stream:
            _read_header(stream)
            valid_end = stream.tell()
            index = 0
            while True:
                prefix = stream.read(_LENGTH.size)
                if len(prefix) < _LENGTH.size:
                    break  # truncated tail — cut it off below
                (length,) = _LENGTH.unpack(prefix)
                if length > MAX_RECORD_BYTES or length < _MIN_RECORD_BYTES:
                    raise StoreCorruptError(f"declared record length {length} out of bounds")
                payload = stream.read(length)
                if len(payload) < length:
                    break  # truncated tail
                rtype = payload[0]
                if rtype == _REC_FOOTER:
                    raise StoreStateError("store is finished (footer present); cannot append")
                if rtype != _REC_CHUNK:
                    raise StoreCorruptError(f"unknown record type {rtype}")
                if index >= MAX_RECORDS:
                    raise StoreCorruptError("record count exceeds bound")
                # Integrity of the record is verified: a corrupt-but-complete
                # record must not be silently resumed past.
                try:
                    crypto.decrypt(payload[1:], _chunk_aad(index))
                except InvalidTag as exc:
                    raise StoreCorruptError(f"record {index} failed authentication") from exc
                index += 1
                valid_end = stream.tell()
        try:
            append_stream: BinaryIO = path.open("r+b")
        except OSError as exc:
            raise StoreWriteError(f"failed reopening store for append: {exc}") from exc
        try:
            append_stream.truncate(valid_end)
            append_stream.seek(valid_end)
        except OSError as exc:
            append_stream.close()
            raise StoreWriteError(f"failed truncating partial tail: {exc}") from exc
        return cls(path, crypto, append_stream, index)

    def _live_stream(self) -> BinaryIO:
        if self._stream is None:
            raise StoreStateError("store is closed")
        if self._finished:
            raise StoreStateError("store is finished")
        return self._stream

    def _write_record(self, record_type: int, blob: bytes) -> None:
        stream = self._live_stream()
        payload = bytes([record_type]) + blob
        try:
            stream.write(_LENGTH.pack(len(payload)))
            stream.write(payload)
            stream.flush()
        except OSError as exc:
            # Disk full / failing disk: close the handle; the session goes
            # to `failed` (recoverable) — never silent data loss.
            self.close()
            raise StoreWriteError(f"chunk write failed: {exc}") from exc

    def append_chunk(self, data: bytes) -> int:
        """Encrypt and append one audio chunk; returns its index."""
        if len(data) > MAX_CHUNK_PLAINTEXT_BYTES:
            raise ValueError("chunk exceeds maximum plaintext size")
        if self._next_index >= MAX_RECORDS:
            raise StoreLimitError("record-count bound reached; refusing to append")
        index = self._next_index
        # Fresh RANDOM nonce per record inside SessionCrypto.encrypt —
        # never counter-derived (binding: crash-restored counters risk reuse).
        self._write_record(_REC_CHUNK, self._crypto.encrypt(data, _chunk_aad(index)))
        self._next_index += 1
        return index

    def finish(self) -> int:
        """Seal the store: FOOTER record carrying the final chunk count,
        fsync, close. Returns the final count."""
        count = self._next_index
        self._write_record(_REC_FOOTER, self._crypto.encrypt(_U64.pack(count), _FOOTER_AAD))
        stream = self._live_stream()
        try:
            os.fsync(stream.fileno())
        except OSError as exc:
            self.close()
            raise StoreWriteError(f"fsync at finish failed: {exc}") from exc
        self._finished = True
        self.close()
        return count

    def close(self) -> None:
        if self._stream is not None:
            try:
                self._stream.close()
            finally:
                self._stream = None

    def __enter__(self) -> SessionChunkStore:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def iter_chunks(
    path: Path, crypto: SessionCrypto, *, require_footer: bool = False
) -> Iterator[bytes]:
    """Decrypt-stream the chunks in order.

    - Declared record lengths beyond the bound are rejected WITHOUT
      allocation (mirrors framing.py).
    - AAD binds each record to its index: reorder/tamper -> StoreCorruptError.
    - A truncated tail (crash) ends iteration cleanly when
      `require_footer=False`; with `require_footer=True` (a Finished store)
      a missing/mismatching footer raises — post-Finish truncation detection.
    """
    with path.open("rb") as stream:
        _read_header(stream)
        index = 0
        footer_seen = False
        while True:
            prefix = stream.read(_LENGTH.size)
            if len(prefix) < _LENGTH.size:
                break  # truncated tail (or clean end without footer)
            (length,) = _LENGTH.unpack(prefix)
            if length > MAX_RECORD_BYTES or length < _MIN_RECORD_BYTES:
                # Reject BEFORE allocating (a 4-byte prefix can declare ~4 GB).
                raise StoreCorruptError(f"declared record length {length} out of bounds")
            payload = stream.read(length)
            if len(payload) < length:
                break  # truncated tail
            rtype = payload[0]
            if footer_seen:
                raise StoreCorruptError("record found after footer")
            if rtype == _REC_CHUNK:
                if index >= MAX_RECORDS:
                    raise StoreCorruptError("record count exceeds bound")
                try:
                    plaintext = crypto.decrypt(payload[1:], _chunk_aad(index))
                except InvalidTag as exc:
                    raise StoreCorruptError(f"record {index} failed authentication") from exc
                yield plaintext
                index += 1
            elif rtype == _REC_FOOTER:
                try:
                    footer_plain = crypto.decrypt(payload[1:], _FOOTER_AAD)
                except InvalidTag as exc:
                    raise StoreCorruptError("footer failed authentication") from exc
                if len(footer_plain) != _U64.size:
                    raise StoreCorruptError("malformed footer payload")
                (declared_count,) = _U64.unpack(footer_plain)
                if declared_count != index:
                    raise StoreCorruptError(
                        f"footer declares {declared_count} chunks, found {index}"
                    )
                footer_seen = True
            else:
                raise StoreCorruptError(f"unknown record type {rtype}")
        if require_footer and not footer_seen:
            raise StoreCorruptError("finished store is missing its footer (truncated after Finish)")


def store_has_footer(path: Path) -> bool:
    """True when the store carries a COMPLETE footer record (reached Finish).

    Structural scan only — record type bytes are plaintext; nothing is
    decrypted and no key is needed. Truncated tails and malformed lengths
    simply yield False (an unfinished or damaged store is handled by the
    recovery path, which decides footer enforcement with this answer).
    """
    try:
        with path.open("rb") as stream:
            _read_header(stream)
            while True:
                prefix = stream.read(_LENGTH.size)
                if len(prefix) < _LENGTH.size:
                    return False
                (length,) = _LENGTH.unpack(prefix)
                if length > MAX_RECORD_BYTES or length < _MIN_RECORD_BYTES:
                    return False
                payload = stream.read(length)
                if len(payload) < length:
                    return False
                if payload[0] == _REC_FOOTER:
                    return True
    except (OSError, SessionStoreError):
        return False


# --------------------------------------------------------------------------
# Atomic durable write — THE binding durability idiom (round 42 MED-008).
# --------------------------------------------------------------------------


def atomic_write_bytes(path: Path, blob: bytes, *, error_label: str) -> None:
    """Write ``blob`` durably and atomically: temp + fsync + ``os.replace``.

    The single implementation of the binding durability idiom for
    custody-critical artifacts (``key.dpapi`` here, ``transcript.enc`` in
    the transcription module) — hardening (e.g. rename-durability changes)
    lands once, in lockstep for both. Any failure raises
    ``StoreWriteError`` and never leaves a partial file at ``path``.
    """
    tmp_path = path.with_name(path.name + ".tmp")
    try:
        with tmp_path.open("wb") as stream:
            stream.write(blob)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_path, path)
    except OSError as exc:
        raise StoreWriteError(f"failed writing {error_label}: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)


# --------------------------------------------------------------------------
# DPAPI key custody (Windows-only; CryptProtectData, current-user scope).
# --------------------------------------------------------------------------


def _require_windows() -> None:
    if sys.platform != "win32":
        raise RuntimeError("DPAPI key custody is Windows-only")


# The DPAPI blob description names WHAT a key.dpapi wraps. It is stored
# inside the blob by CryptProtectData and read back by CryptUnprotectData, so
# the unwrap verifies it: a blob wrapped for one purpose cannot be presented
# as a key for another (practitioner-profile plan D5 — the profile key carries
# its own description and the two custody stores can never read each other's
# key). Session callers keep the default and are unchanged.
SESSION_KEY_DESCRIPTION: Final = "ClinikoScribe session key"


def wrap_key_to_file(
    crypto: SessionCrypto, session_dir: Path, *, description: str = SESSION_KEY_DESCRIPTION
) -> Path:
    """DPAPI-wrap the key and write `key.dpapi` ATOMICALLY (temp + fsync +
    os.replace) — for a session, called BEFORE the first chunk. The blob
    carries ``description`` and ``unwrap_key_from_file`` verifies it."""
    _require_windows()
    import win32crypt

    blob: bytes = win32crypt.CryptProtectData(
        crypto.export_key(), description, None, None, None, 0
    )
    key_path = session_dir / KEY_FILENAME
    atomic_write_bytes(key_path, blob, error_label="key custody blob")
    return key_path


def unwrap_key_from_file(
    session_dir: Path, *, description: str = SESSION_KEY_DESCRIPTION
) -> SessionCrypto:
    """Read + DPAPI-unwrap `key.dpapi`. Missing/zero-length/truncated blobs,
    a failed unwrap, and a blob whose stored description is not
    ``description`` raise KeyCustodyError — the data under that key is
    cryptographically unrecoverable through THIS custody store."""
    _require_windows()
    import win32crypt

    key_path = session_dir / KEY_FILENAME
    try:
        blob = key_path.read_bytes()
    except OSError as exc:
        raise KeyCustodyError(f"key custody blob unreadable: {exc}") from exc
    if key_blob_is_dead(len(blob)):
        raise KeyCustodyError("key custody blob is zero-length or truncated")
    try:
        stored_description, key = win32crypt.CryptUnprotectData(blob, None, None, None, 0)
    except Exception as exc:  # pywin32 raises pywintypes.error (not OSError-rooted)
        raise KeyCustodyError("key custody blob failed DPAPI unwrap") from exc
    if stored_description != description:
        raise KeyCustodyError("key custody blob was wrapped for a different store")
    try:
        return SessionCrypto.from_key(key)
    except ValueError as exc:
        raise KeyCustodyError("unwrapped key has wrong length") from exc


# Windows' reparse tag for a directory junction (a "mount point").
_IO_REPARSE_TAG_MOUNT_POINT: Final = 0xA0000003


def link_state(path: Path) -> bool | None:
    """Whether ``path`` itself is a symlink or a directory junction, from ONE
    ``os.lstat`` (privacy-professional-controls H3 round 35 SEC-001): True or
    False — False also when it does not exist — and None when that cannot be
    read. ``Path.is_symlink`` / ``is_junction`` cannot serve: from Python 3.13
    both swallow every error and answer False, so "cannot tell" would read as
    "not a link". Every caller decides None in its own safe direction."""
    try:
        status = os.lstat(path)
    except FileNotFoundError:
        return False
    except OSError:
        return None
    if _stat.S_ISLNK(status.st_mode):
        return True
    return getattr(status, "st_reparse_tag", 0) == _IO_REPARSE_TAG_MOUNT_POINT


class SessionLinkError(OSError):
    """A session folder that is a link (or whose link status cannot be read)
    was refused by ``delete_session_key``: Windows resolves a junction
    mid-path, so ``<link>\\key.dpapi`` would be ANOTHER folder's key. An
    ``OSError``, so every caller's existing key-deletion failure path (key
    kept, nothing completed or discarded) handles it. Content-free."""


def delete_session_key(session_dir: Path) -> None:
    """Delete the wrapped key blob — THE cryptographic deletion of the
    session (same-user boundary; NTFS residual documented). Idempotent.

    Never through a link (H3 round 35 SEC-002 — the class ``past_sessions``
    closed in round 13): a ``session_dir`` that is a symlink or junction, or
    whose link status cannot be read, raises ``SessionLinkError`` and deletes
    nothing. Covers every caller — Complete, Discard and the sweep."""
    if link_state(session_dir) is not False:
        raise SessionLinkError("the session folder is a link; key kept")
    (session_dir / KEY_FILENAME).unlink(missing_ok=True)


def _resolve_session_identity(session_dir: Path) -> str:
    """The session id this directory IS, for artifact-binding checks.

    The audio store header is authoritative (written at create time and
    bound into every chunk's AAD); the directory name is the fallback, since
    the store layout names every session directory after its id. Fails
    CLOSED when neither yields a well-formed id — an artifact whose binding
    cannot be checked must not clear Complete.
    """
    audio_path = session_dir / AUDIO_FILENAME
    if audio_path.exists():
        try:
            return read_store_header(audio_path).session_id
        except (SessionStoreError, OSError):
            pass  # fall through to the directory name
    name = session_dir.name
    if _SESSION_ID_RE.match(name):
        return name
    raise StoreCorruptError("session identity is unresolvable; key retained")


def _note_identity(plaintext: bytes) -> str:
    """A saved note's IDENTITY — the one definition (draft-write D5;
    privacy-professional-controls D8): the SHA-256 hex of the decrypted
    ``note.enc`` plaintext, the exact bytes the review saved."""
    return hashlib.sha256(plaintext).hexdigest()


class _CompletedNote(NamedTuple):
    """The note a Complete read (privacy-professional-controls D4 / D8): the
    parsed note, its identity (``_note_identity``, round 6 LOW-005) and the
    exact plaintext bytes — what the Past-sessions entry re-encrypts, byte
    for byte, so the identity holds there too (D1)."""

    note: GeneratedNote
    identity: str
    plaintext: bytes


def _verified_note(
    session_dir: Path, crypto: SessionCrypto, note_blob: bytes, transcript_plain: bytes
) -> GeneratedNote:
    """``read_note``'s view of the single verification core
    (``_verified_note_with_identity``, which it runs): the parsed note
    only."""
    return _verified_note_with_identity(session_dir, crypto, note_blob, transcript_plain).note


def _verified_note_with_identity(
    session_dir: Path, crypto: SessionCrypto, note_blob: bytes, transcript_plain: bytes
) -> _CompletedNote:
    """THE single note-verification core (Tasks 1.5 / 6.2): decrypt ->
    parse -> session binding -> transcript-digest match, using the single
    Task-1.1 digest definition. ``read_note`` and the Complete ordering both
    verify through this exact code path, so the two can never disagree about
    what a valid note is. Every failure is typed and the caller's custody is
    untouched (the "key retained" wording states that custody fact). Also
    returns the note's identity, from the plaintext already in hand."""
    try:
        plain = crypto.decrypt(note_blob)
    except InvalidTag as exc:
        raise StoreCorruptError("note failed decrypt verification; key retained") from exc
    # Deferred import (not a cycle): note.py imports THIS module at import
    # time for SESSION_ID_PATTERN and atomic_write_bytes, so the note model
    # and the single digest definition are resolved here, at call time.
    from scribe_desktop.note import GeneratedNote, digest_bytes

    try:
        note = GeneratedNote.from_bytes(plain)
    except ValidationError as exc:
        raise StoreCorruptError("note artifact is malformed; key retained") from exc
    if note.session_id != _resolve_session_identity(session_dir):
        raise StoreCorruptError("note is bound to another session; key retained")
    if note.transcript_digest != digest_bytes(transcript_plain):
        raise StoreCorruptError("note does not describe this transcript; key retained")
    return _CompletedNote(note, _note_identity(plain), plain)


def _verify_note_for_completion(
    session_dir: Path, crypto: SessionCrypto, transcript_plain: bytes
) -> _CompletedNote | None:
    """Verify `note.enc` before custody deletion, FAIL-CLOSED and symmetric
    with the transcript: fsync -> decrypt -> parse -> session binding ->
    transcript-digest match (the shared ``_verified_note_with_identity``
    core). Any failure
    raises, so the caller never reaches `delete_session_key` and regeneration
    stays possible. A missing note is the normal pre-Phase-3A case and
    verifies vacuously (None). The verified note and its identity are
    returned (privacy-professional-controls plan D4), so the completion facts
    need no second decrypt."""
    note_path = session_dir / NOTE_FILENAME
    try:
        with note_path.open("r+b") as stream:
            os.fsync(stream.fileno())
            blob = stream.read()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise StoreWriteError(f"note not durably readable; key retained: {exc}") from exc
    return _verified_note_with_identity(session_dir, crypto, blob, transcript_plain)


# --------------------------------------------------------------------------
# The saved note's model provenance and the completion facts (privacy-
# professional-controls plan D4 / D8) — content-free, for the audit record.
# --------------------------------------------------------------------------

# D8: the saved note's language-model id and prompt version, captured at SAVE
# under the session key (AAD ``saved-provenance:<id>``) with the SHA-256 of the
# saved note's canonical bytes. Task 2.1 writes it inside Save's custody
# action; Complete only reads it, and uses the ids ONLY when the digest names
# the ``note.enc`` being completed. Never archived; dies with the session.
SAVED_PROVENANCE_FILENAME: Final = "saved-provenance.enc"
# Its bound (H3 round 35 SEC-005): a digest and four short ids.
MAX_SAVED_PROVENANCE_FILE_BYTES: Final = 64 * 1024

# What an audit row may hold for a model or provider name: one token — no
# space, so no sentence can pass — else ``FACT_UNRECOGNISED``. ``FACT_NONE``:
# the step did not run (no note, no voice profile, no prose stage);
# ``FACT_UNKNOWN``: it may have run but nothing trustworthy says how.
FACT_TOKEN_PATTERN: Final = r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}$"
_FACT_TOKEN_RE: Final = re.compile(FACT_TOKEN_PATTERN)
FACT_NONE: Final = "none"
FACT_UNKNOWN: Final = "unknown"
FACT_UNRECOGNISED: Final = "unrecognised"


class SavedProvenance(BaseModel):
    """``saved-provenance.enc``'s document (D8): ids and a digest, never
    note text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    note_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_name: str = Field(min_length=1, max_length=64)
    style: str = Field(min_length=1, max_length=32)
    language_model_id: str | None = None
    prompt_version: str | None = None

    def to_bytes(self) -> bytes:
        return self.model_dump_json().encode("utf-8")


def _saved_provenance_aad(session_id: str) -> bytes:
    """Distinct from every other artifact's, and bound to the session."""
    return b"saved-provenance:" + validate_session_id(session_id).encode("ascii")


def write_saved_provenance(
    session_dir: Path, crypto: SessionCrypto, session_id: str, provenance: SavedProvenance
) -> Path:
    """Encrypt and write ``saved-provenance.enc`` ATOMICALLY (D8). The bytes'
    custody only: wiring it into Save is Task 2.1's."""
    path = session_dir / SAVED_PROVENANCE_FILENAME
    atomic_write_bytes(
        path,
        crypto.encrypt(provenance.to_bytes(), _saved_provenance_aad(session_id)),
        error_label="saved-note provenance",
    )
    return path


def read_saved_provenance(
    session_dir: Path, crypto: SessionCrypto, session_id: str
) -> SavedProvenance | None:
    """``saved-provenance.enc`` decoded: None when there is no such file;
    ``StoreCorruptError`` (terse — pydantic's detail would echo the document)
    when it exists but cannot be read, authenticated or parsed."""
    try:
        blob: bytes | None = read_capped(
            session_dir / SAVED_PROVENANCE_FILENAME, MAX_SAVED_PROVENANCE_FILE_BYTES
        )
    except FileNotFoundError:
        return None
    except (OSError, StoreCorruptError):
        blob = None
    plaintext = _authentic(
        blob, crypto, _saved_provenance_aad(session_id), "saved-note provenance unreadable"
    )
    try:
        return SavedProvenance.model_validate_json(plaintext)
    except ValidationError:
        pass
    raise StoreCorruptError("saved-note provenance unreadable")  # no chained detail


def write_saved_note(
    session_dir: Path,
    crypto: SessionCrypto,
    note: GeneratedNote,
    config: NoteConfig,
    *,
    language_model_id: str | None,
    prompt_version: str | None,
) -> Path:
    """Save's two writes, in D8's order (privacy-professional-controls plan
    Task 2.1, round 4 PR-MED-001): ``saved-provenance.enc`` FIRST, naming
    the SHA-256 of the exact canonical bytes ``write_note`` will store, THEN
    ``note.enc`` — whose replacement stays the Save's one commit boundary.

    A provenance failure raises before ``note.enc`` is touched (nothing is
    committed); a ``write_note`` failure after it leaves a provenance whose
    digest names no ``note.enc`` on disk, which Complete reads as
    ``unknown`` — harmless. ``language_model_id`` / ``prompt_version`` are
    the caller's (None: no prose stage ran for this note); this module
    never imports the language model."""
    canonical = _canonical_note(note)
    if canonical.session_id != _resolve_session_identity(session_dir):
        raise NoteWriteRefusedError("the note is bound to another session")
    write_saved_provenance(
        session_dir,
        crypto,
        canonical.session_id,
        SavedProvenance(
            note_digest=_note_identity(canonical.to_bytes()),
            provider_name=canonical.provider_name,
            style=canonical.style,
            language_model_id=language_model_id,
            prompt_version=prompt_version,
        ),
    )
    return write_note(session_dir, crypto, note, config)


# --------------------------------------------------------------------------
# The first note body the review showed (privacy-professional-controls D2).
# --------------------------------------------------------------------------

# Bounds (the declared size is never an allocation bound — a file is capped
# before it is read): a rendered note body is a few kilobytes.
MAX_GENERATED_TEXT_CHARS: Final = 1_000_000
MAX_GENERATED_FILE_BYTES: Final = 8 * 1024 * 1024


class GeneratedRecord(BaseModel):
    """``generated.enc``'s document (D2): the first ``format_note_body``
    output the review showed, before any review action — or, when the first
    prose rendering landed before any edit, that prose — with what produced
    it, captured at render time (``language_model_id`` / ``prompt_version``
    None when no prose stage ran). ``generated_text`` is clinical text: the
    name is distinctive, a tripwire signature in ``logging_setup``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str = Field(pattern=SESSION_ID_PATTERN)
    created_at: AwareDatetime
    provider_name: str = Field(min_length=1, max_length=64)
    style: str = Field(min_length=1, max_length=32)
    language_model_id: str | None = Field(default=None, max_length=256)
    prompt_version: str | None = Field(default=None, max_length=64)
    generated_text: str = Field(max_length=MAX_GENERATED_TEXT_CHARS)

    def to_bytes(self) -> bytes:
        return self.model_dump_json().encode("utf-8")


class _KeptGenerated(NamedTuple):
    record: GeneratedRecord
    plaintext: bytes


def generated_aad(session_id: str) -> bytes:
    """Distinct from every other artifact's, and bound to the session. Public
    for the Past-sessions entry, which re-encrypts the exact plaintext under
    its own key with this same associated data (D1)."""
    return b"generated:" + validate_session_id(session_id).encode("ascii")


def write_generated(session_dir: Path, crypto: SessionCrypto, record: GeneratedRecord) -> Path:
    """Encrypt and write ``generated.enc`` ATOMICALLY, replacing any earlier
    one (a regeneration's first body replaces the previous generation's).
    Refused (``NoteWriteRefusedError``, nothing written) when the record
    names another session than the directory is."""
    if record.session_id != _resolve_session_identity(session_dir):
        raise NoteWriteRefusedError("the generated note is bound to another session")
    path = session_dir / GENERATED_FILENAME
    atomic_write_bytes(
        path,
        crypto.encrypt(record.to_bytes(), generated_aad(record.session_id)),
        error_label="generated note",
    )
    return path


def read_capped(path: Path, cap: int) -> bytes:
    """``path``'s bytes, refusing (``StoreCorruptError``) a file larger than
    ``cap`` before reading it. ``FileNotFoundError`` passes through. The one
    bounded read for the privacy-professional-controls stores (H3 round 35
    SEC-005: `generated.enc`, `saved-provenance.enc`, the audit rows)."""
    with path.open("rb") as stream:
        blob = stream.read(cap + 1)
    if len(blob) > cap:
        raise StoreCorruptError("artifact exceeds its size bound")
    return blob


def _read_generated(
    session_dir: Path, crypto: SessionCrypto, session_id: str
) -> _KeptGenerated | None:
    """``generated.enc`` decoded with its exact plaintext: None when there is
    none; ``StoreCorruptError`` (terse) when it cannot be read, is over its
    bound, fails authentication, does not parse or names another session."""
    label = "generated note unreadable"
    try:
        blob: bytes | None = read_capped(
            session_dir / GENERATED_FILENAME, MAX_GENERATED_FILE_BYTES
        )
    except FileNotFoundError:
        return None
    except (OSError, StoreCorruptError):
        blob = None
    plaintext = _authentic(blob, crypto, generated_aad(session_id), label)
    try:
        record = GeneratedRecord.model_validate_json(plaintext)
    except ValidationError:
        record = None
    if record is None or record.session_id != session_id:
        raise StoreCorruptError(label)  # outside the handler: no chained detail
    return _KeptGenerated(record, plaintext)


def read_generated(
    session_dir: Path, crypto: SessionCrypto, session_id: str
) -> GeneratedRecord | None:
    """``generated.enc`` decoded: None when there is no such file (a session
    completed before D2, or one never generated for); ``StoreCorruptError``
    (terse — pydantic's detail would echo the note) when it exists but cannot
    be read."""
    kept = _read_generated(session_dir, crypto, session_id)
    return kept.record if kept is not None else None


def is_mock_identity(name: str) -> bool:
    """THE one mock rule (privacy-professional-controls D6): a model or
    provider name of the test backends — ``MockSpeechProvider`` (the
    transcript's ``model_name``), a ``mock-<behaviour>`` note provider — is
    one starting ``mock``, case-insensitively. A mock session keeps no Past-
    sessions entry. Named residue: a real model someone named ``mock…``
    would be treated as mock (the safe direction: nothing kept)."""
    return name.casefold().startswith("mock")


def fact_token(value: object) -> str:
    """``value`` as an audit fact: ``FACT_NONE`` for None, the text when it
    is one token (``FACT_TOKEN_PATTERN``), else ``FACT_UNRECOGNISED`` — so a
    name that is not a plain identifier never reaches the audit."""
    if value is None:
        return FACT_NONE
    text = str(value)
    return text if _FACT_TOKEN_RE.fullmatch(text) else FACT_UNRECOGNISED


@dataclass(frozen=True)
class CompletionFacts:
    """What ``complete_session`` reports for the audit record (D4, D8):
    model and provider TOKENS (``fact_token``) and outcome codes only —
    never text. Every field is decided from what the session itself
    persisted, never from the constants in force at Complete:

    - the transcription and speaker models from the ``TranscriptDocument``;
    - the note's provider, schema version, template profile and style from
      the completed note (on a delete-note path, the note read for its
      provenance only — ``note_provenance`` ``unknown`` when it could not
      be read);
    - the saved note's language model and prompt version from
      ``saved-provenance.enc`` ONLY when its digest names that note, else
      ``unknown``;
    - the generated note's (``generated_*``) from ``generated.enc`` (D2),
      ``unknown`` when there is none or it cannot be read (a session
      generated before D2 is indistinguishable from one never generated);
    - ``past_session``: ``archived`` when the Past-sessions entry was
      published, ``not_kept_mock`` for a mock session, else ``none`` (no
      archive was asked for); ``commit_deferred`` when the entry was
      published but its ``pending`` marker could not be removed after the
      key — the entry appears after the next reconciliation (Flow 3 step 4).
      A status-line fact only, never an audit field: the row's
      ``past_session`` is ``archived`` either way, and the deferral is a
      transient no row update would follow."""

    transcription_model: str = FACT_UNKNOWN
    speaker_model: str = FACT_UNKNOWN
    note_provider: str = FACT_NONE
    note_schema_version: str = FACT_NONE
    template_profile: str = FACT_NONE
    note_style: str = FACT_NONE
    language_model_id: str = FACT_NONE
    prompt_version: str = FACT_NONE
    generated_provider: str = FACT_UNKNOWN
    generated_style: str = FACT_UNKNOWN
    generated_language_model_id: str = FACT_UNKNOWN
    generated_prompt_version: str = FACT_UNKNOWN
    note_provenance: Literal["known", "unknown"] | None = None
    past_session: Literal["none", "archived", "not_kept_mock"] = "none"
    commit_deferred: bool = False


class _UnreadableNote:
    """A ``note.enc`` present but not readable (the delete-note paths)."""


_UNREADABLE_NOTE: Final = _UnreadableNote()


def _note_for_provenance(
    session_dir: Path, crypto: SessionCrypto
) -> _CompletedNote | _UnreadableNote | None:
    """The delete-note paths' note, read best-effort for its provenance only
    (never verified — it is not being completed, and it is never archived):
    None when there is none, ``_UNREADABLE_NOTE`` when it cannot be read,
    decrypted or parsed (the delete-unreadable-note escape stays open). Read
    on EVERY attempt, since nothing unlinks it early any more (D6, round 3
    PR-MED-002). Never raises."""
    from scribe_desktop.note import GeneratedNote

    try:
        blob = (session_dir / NOTE_FILENAME).read_bytes()
    except FileNotFoundError:
        return None
    except OSError:
        return _UNREADABLE_NOTE
    try:
        plain = crypto.decrypt(blob)
        return _CompletedNote(GeneratedNote.from_bytes(plain), _note_identity(plain), plain)
    except Exception:  # noqa: BLE001 - any failure is "unreadable", never a raise
        return _UNREADABLE_NOTE


def _transcript_model_name(transcript_plain: bytes) -> tuple[str | None, str | None]:
    """The transcript document's ``(model_name, speaker_model_id)``, or
    ``(None, None)`` when the plaintext is not a document. Never raises."""
    from scribe_desktop.transcription import TranscriptDocument

    try:
        document = TranscriptDocument.from_bytes(transcript_plain)
    except Exception:  # noqa: BLE001 - a fact, never a Complete failure
        return None, None
    return document.model_name, document.speaker_model_id


def _is_mock_session(
    transcript_model: str | None,
    generated: _KeptGenerated | None,
    completed: _CompletedNote | _UnreadableNote | None,
) -> bool:
    """D6: mock when ANY discriminator says so — the transcript's model, the
    generated note's provider, or the saved (or, on a delete-note path, the
    provenance-read) note's provider. An unreadable note decides nothing."""
    names = [transcript_model]
    if generated is not None:
        names.append(generated.record.provider_name)
    if isinstance(completed, _CompletedNote):
        names.append(completed.note.provider_name)
    return any(name is not None and is_mock_identity(name) for name in names)


def _completion_facts(
    session_dir: Path,
    crypto: SessionCrypto,
    transcript_models: tuple[str | None, str | None],
    completed: _CompletedNote | _UnreadableNote | None,
    generated: _KeptGenerated | None = None,
) -> CompletionFacts:
    """Builds ``CompletionFacts`` while the key is still in hand, from the
    transcript's ``_transcript_model_name`` (parsed once by the caller, H2
    round 34 SIMP-001). BEST-EFFORT by construction: every read is inside its
    own guard and a failure yields ``FACT_UNKNOWN`` — the audit never decides
    whether a Complete happens (Critical Constraint C2)."""
    transcription_model = speaker_model = FACT_UNKNOWN
    model_name, speaker_model_id = transcript_models
    if model_name is not None:
        transcription_model = fact_token(model_name)
        speaker_model = fact_token(speaker_model_id)
    base = CompletionFacts(transcription_model=transcription_model, speaker_model=speaker_model)
    if generated is not None:
        record = generated.record
        base = replace(
            base,
            generated_provider=fact_token(record.provider_name),
            generated_style=fact_token(record.style),
            generated_language_model_id=fact_token(record.language_model_id),
            generated_prompt_version=fact_token(record.prompt_version),
        )
    if completed is None:
        return base
    if isinstance(completed, _UnreadableNote):
        return replace(
            base,
            note_provider=FACT_UNKNOWN,
            note_schema_version=FACT_UNKNOWN,
            template_profile=FACT_UNKNOWN,
            note_style=FACT_UNKNOWN,
            language_model_id=FACT_UNKNOWN,
            prompt_version=FACT_UNKNOWN,
            note_provenance="unknown",
        )
    note = completed.note
    language_model_id = prompt_version = FACT_UNKNOWN
    try:
        provenance = read_saved_provenance(
            session_dir, crypto, _resolve_session_identity(session_dir)
        )
        # The note's IDENTITY (the plaintext's SHA-256 — round 6 LOW-005),
        # never a re-serialisation of the parsed note.
        if provenance is not None and provenance.note_digest == completed.identity:
            language_model_id = fact_token(provenance.language_model_id)
            prompt_version = fact_token(provenance.prompt_version)
    except Exception:  # noqa: BLE001 - unreadable provenance is "unknown"
        pass
    return replace(
        base,
        note_provider=fact_token(note.provider_name),
        note_schema_version=fact_token(note.schema_version),
        template_profile=fact_token(note.template_profile_id),
        note_style=fact_token(note.style),
        language_model_id=language_model_id,
        prompt_version=prompt_version,
        note_provenance="known",
    )


@dataclass(frozen=True)
class ArchiveSource:
    """What a Complete hands the Past-sessions writer (privacy-professional-
    controls D1 / D6): the SOURCE-DERIVED set, as verified plaintext bytes —
    the transcript always, the saved note when this path completes it (never
    on a delete-note path), the generated note when ``generated.enc`` read
    back authentic. Never audio. ``created_at`` is the session's trusted
    creation time (epoch seconds) or None. repr-hidden: clinical text."""

    session_id: str
    created_at: float | None
    transcript_plain: bytes = field(repr=False)
    note_plain: bytes | None = field(repr=False)
    generated_plain: bytes | None = field(repr=False)


class ArchiveKeeper(Protocol):
    """The Past-sessions writer ``complete_session`` is given (D4), so this
    module imports neither ``past_sessions`` nor any UI code.

    ``write`` stages, FULLY verifies and publishes the entry carrying its
    ``pending`` marker — any failure raises, BEFORE the key boundary.
    ``commit`` removes the marker after the source key is gone and NEVER
    raises: False leaves the entry for the next reconciliation.
    ``drop_unfinished`` (H1 round 32 LOW-002) is a Complete that keeps
    nothing (a mock session): any entry an earlier attempt published for the
    id is removed key-first BEFORE the key boundary, as every non-Complete
    destroyer does (C1) — False means it could not be, and the key stays."""

    def write(self, source: ArchiveSource) -> None: ...

    def commit(self, session_id: str) -> bool: ...

    def drop_unfinished(self, session_id: str) -> bool: ...


def complete_session(
    session_dir: Path,
    crypto: SessionCrypto,
    *,
    delete_note: bool = False,
    keep: ArchiveKeeper | None = None,
) -> CompletionFacts:
    """Complete ordering (binding): fsync `transcript.enc` -> verify a
    decrypt round-trip -> verify `note.enc` when one exists -> the Past-
    sessions entry when ``keep`` is given -> THEN delete the key. Any failure
    up to there keeps the key.

    The note joins the ordering and fails closed exactly like the
    transcript. Retaining custody on a bad note is the POINT: the key is
    what keeps regeneration possible, so completing over an unverifiable
    note would delete the key, make the transcript unreadable, and destroy
    the only route to a correct note.

    `delete_note=True` is the clinician's explicit, confirmed
    "complete without a note" exit — never a silent deletion. Since the
    privacy-professional-controls plan (D6, round 3 PR-MED-002) the note is
    NOT unlinked early: it is excluded from verification and from the
    archive, read best-effort for its provenance only (an unreadable note
    never blocks), and stays on disk until the key and then the directory
    go — unreadable from the moment the key is deleted.

    The Past-sessions entry (C1 / D4): unless the session is mock (D6 — any
    of the transcript's model, the generated note's provider or the note's
    provider), ``keep.write`` publishes the SOURCE-DERIVED set BEFORE the
    key is deleted; a failure raises ``ArchiveWriteError`` with the key
    retained, so the Complete can be retried (a retry replaces the pending
    entry key-first) or the session discarded (which removes it). A mock
    session writes nothing (``not_kept_mock``) and removes, key-first and
    before the key, any entry an earlier attempt published for the id.

    ``delete_session_key`` is THE IRREVERSIBLE BOUNDARY. Once it has
    returned nothing below raises: the in-memory key is destroyed, the
    entry's marker removed best-effort (``commit_deferred`` when it could not
    be — the next reconciliation commits it) and the session directory
    removed best-effort, as Discard does: a removal that fails leaves a
    keyless directory, which the recovery list skips and the sweep removes
    as an orphan (``orphan_gc``, whose confirmed-absent key commits any
    entry).

    Returns the content-free ``CompletionFacts`` (privacy-professional-
    controls plan D4), gathered best-effort while the key is still in hand:
    a fact that cannot be read is ``unknown``, never a failure.
    """
    transcript_path = session_dir / TRANSCRIPT_FILENAME
    try:
        with transcript_path.open("r+b") as stream:
            os.fsync(stream.fileno())
            blob = stream.read()
    except OSError as exc:
        raise StoreWriteError(f"transcript not durably readable: {exc}") from exc
    try:
        transcript_plain = crypto.decrypt(blob)
    except InvalidTag as exc:
        raise StoreCorruptError("transcript failed decrypt verification; key retained") from exc
    completed_note: _CompletedNote | _UnreadableNote | None
    archived_note: bytes | None = None
    if delete_note:
        completed_note = _note_for_provenance(session_dir, crypto)
    else:
        completed_note = _verify_note_for_completion(session_dir, crypto, transcript_plain)
        archived_note = completed_note.plaintext if completed_note is not None else None
    session_id: str | None
    try:
        session_id = _resolve_session_identity(session_dir)
    except StoreCorruptError:
        session_id = None  # nothing bound to an identity can be read or kept
    generated: _KeptGenerated | None = None
    if session_id is not None:
        try:
            generated = _read_generated(session_dir, crypto, session_id)
        except Exception:  # noqa: BLE001 - unreadable: not kept, its facts unknown
            generated = None
    transcript_models = _transcript_model_name(transcript_plain)
    facts = _completion_facts(session_dir, crypto, transcript_models, completed_note, generated)
    past_session: Literal["none", "archived", "not_kept_mock"] = "none"
    if keep is not None:
        if _is_mock_session(transcript_models[0], generated, completed_note):
            past_session = "not_kept_mock"
            # H1 round 32 LOW-002: an earlier, non-mock attempt may have
            # published a pending entry for this id (its key deletion then
            # failed). Keeping nothing means removing it BEFORE the key goes —
            # reconciliation would otherwise commit it as a finished entry.
            # Keyed by the DIRECTORY, like every other destroyer.
            if not keep.drop_unfinished(session_dir.name):
                raise ArchiveWriteError("an unfinished Past-sessions entry remains; key retained")
        else:
            if session_id is None:
                raise ArchiveWriteError("the session identity is unresolvable; key retained")
            if session_id != session_dir.name:
                # C1 keys every entry by id, and every other destroyer
                # (Discard, the recovery list, the sweep) and the
                # reconciliation name the source by its DIRECTORY: an entry
                # under a header id the directory does not carry could
                # outlive a Discard and then be committed (round 11 LOW-001).
                raise ArchiveWriteError("the session identity is not its directory; key retained")
            created = audit_created_at(session_dir)
            source = ArchiveSource(
                session_id=session_id,
                created_at=created if created is not None and math.isfinite(created) else None,
                transcript_plain=transcript_plain,
                note_plain=archived_note,
                generated_plain=generated.plaintext if generated is not None else None,
            )
            try:
                keep.write(source)
            except Exception as exc:  # noqa: BLE001 - any archive failure keeps the key
                raise ArchiveWriteError("Past-sessions entry not written; key retained") from exc
            past_session = "archived"
    delete_session_key(session_dir)  # THE BOUNDARY: nothing below raises
    # PR-HIGH-001 (downgraded MED): after successful custody deletion no
    # application-owned object may decrypt the session — destroy the
    # in-memory key too, not just the wrapped blob.
    crypto.destroy()
    commit_deferred = False
    if past_session == "archived" and keep is not None and session_id is not None:
        try:
            commit_deferred = not keep.commit(session_id)
        except Exception:  # noqa: BLE001 - after the boundary: deferred, never raised
            commit_deferred = True
    shutil.rmtree(session_dir, ignore_errors=True)
    return replace(facts, past_session=past_session, commit_deferred=commit_deferred)


def discard_session(session_dir: Path, crypto: SessionCrypto | None = None) -> None:
    """Discard ordering (binding): delete the key FIRST (cryptographic
    deletion), then best-effort remove the remaining artifacts. Pass the
    live `crypto` when one exists so the in-memory key dies with the blob
    (a recovery-screen discard may have no unwrapped key — pass None)."""
    delete_session_key(session_dir)
    if crypto is not None:
        crypto.destroy()
    shutil.rmtree(session_dir, ignore_errors=True)


# --------------------------------------------------------------------------
# Note artifact I/O (Task 6.2) — mirrors write_transcript/read_transcript.
# --------------------------------------------------------------------------


def _read_transcript_plain(session_dir: Path, crypto: SessionCrypto) -> bytes:
    """The decrypted canonical transcript bytes — the byte domain the
    Task-1.1 ``transcript_digest`` definition is verified against."""
    transcript_path = session_dir / TRANSCRIPT_FILENAME
    try:
        blob = transcript_path.read_bytes()
    except OSError as exc:
        raise StoreWriteError(f"transcript artifact unreadable: {exc}") from exc
    try:
        return crypto.decrypt(blob)
    except InvalidTag as exc:
        raise StoreCorruptError("transcript failed authentication") from exc


def _canonical_note(note: GeneratedNote) -> GeneratedNote:
    """Round-trip ``note`` through ``GeneratedNote``'s OWN schema serializer
    and full re-validation (the ``note_config._canonical_config`` boundary
    lesson, round 12): the base-class serializer reads validated field data —
    never a subclass method or property — and re-validation re-runs every
    validator, so a validator-skipping construction or a lying subclass dies
    typed here instead of reaching disk. For an honestly validated note the
    round-trip is a byte-stable identity."""
    from scribe_desktop.note import GeneratedNote

    try:
        blob = GeneratedNote.__pydantic_serializer__.to_json(note)
        return GeneratedNote.model_validate_json(blob)
    except (ValidationError, PydanticSerializationError) as exc:
        # Terse ON PURPOSE — the clinical-artifact message convention
        # (`_verified_note`, `read_transcript`): a pydantic error's rendered
        # detail carries input values, i.e. note text, and this string must
        # stay safe to display or log anywhere.
        #
        # The contrast with `_parse_config_blob` (which DOES include detail)
        # is one of DESTINATION, not of safety class — round 47 PR-LOW-002
        # corrected the old wording here, which justified it "BECAUSE config
        # is not clinical content". Config is only INTENDED non-patient and
        # is validated for structure alone, so its detailed message is bounded
        # to the local UI, not log-safe. This message is the log-safe one.
        raise NoteWriteRefusedError("note artifact failed canonical re-validation") from exc


def write_note(
    session_dir: Path, crypto: SessionCrypto, note: GeneratedNote, config: NoteConfig
) -> Path:
    """Encrypt and write ``note.enc`` ATOMICALLY under the session key,
    mirroring ``write_transcript``: ``atomic_write_bytes``, and NO AAD —
    ``complete_session`` verifies with a plain decrypt and the two must stay
    in agreement (the ``write_transcript`` docstring's recorded reason).

    ``write_note`` ENFORCES the artifact invariants ITSELF — defense in
    depth, trusting neither the UI nor construction-time validation (plan
    Task 6.2; every refusal is typed ``NoteWriteRefusedError`` and leaves the
    disk unchanged):

    - the note is CANONICALISED first (``_canonical_note``), which re-runs
      every construction validator — so the whole class of unbacked
      clinician-authored assertions (missing/declined/mismatched
      ``ConfirmationDecision``, absent evidence fields) is refused at once
      rather than by an enumerated field list (the no-content-escapes
      lesson: confine the class, never enumerate spellings);
    - any unresolved ``error`` warning refuses the write —
      ``blocking_warnings()`` is the state (global property 4);
    - the TWO relations construction deliberately does NOT verify (the
      note.py docstring records why) are verified here: every
      non-``transcript`` assertion's ``shown_text_digest`` must be the
      digest of its exact text, and its ``config_digest`` must be the
      note's own — confirmation evidence under a different config backs a
      different proposal. A typed ``clinician`` line (schema v2) carries the
      same two digests and is verified identically;
    - ``transcript_digest`` is re-verified against the decrypted ON-DISK
      transcript and ``session_id`` against the store identity, so a note
      describing a superseded transcript or another session never lands;
    - ``config_digest`` is re-verified against the presented (canonicalised)
      config — the digest the confirmation evidence was collected under.
    """
    from scribe_desktop.note import digest_bytes, text_digest
    from scribe_desktop.note_config import _canonical_config

    note = _canonical_note(note)
    if note.blocking_warnings():
        raise NoteWriteRefusedError(
            "the note carries unresolved error warnings; resolve them and refinalise"
        )
    for section in note.note_sections:
        for assertion in section.note_assertions:
            if assertion.note_span.provenance == "transcript":
                continue
            # autofill, prefill and typed ``clinician`` lines alike.
            if (
                assertion.shown_text_digest is None
                or text_digest(assertion.note_span.span_text) != assertion.shown_text_digest
            ):
                raise NoteWriteRefusedError(
                    f"assertion {assertion.assertion_id}: shown_text_digest is not the "
                    "digest of the assertion's text — the confirmed wording is not the "
                    "wording this note carries"
                )
            if assertion.config_digest != note.config_digest:
                raise NoteWriteRefusedError(
                    f"assertion {assertion.assertion_id} was confirmed under a different "
                    "config than the note records"
                )
    if _canonical_config(config).config_digest() != note.config_digest:
        raise NoteWriteRefusedError(
            "the note's config_digest does not match the presented config"
        )
    if note.session_id != _resolve_session_identity(session_dir):
        raise NoteWriteRefusedError("the note is bound to another session")
    transcript_plain = _read_transcript_plain(session_dir, crypto)
    if note.transcript_digest != digest_bytes(transcript_plain):
        raise NoteWriteRefusedError(
            "the note does not describe this session's transcript"
        )
    note_path = session_dir / NOTE_FILENAME
    atomic_write_bytes(note_path, crypto.encrypt(note.to_bytes()), error_label="note artifact")
    return note_path


def _encounter_aad(session_id: str) -> bytes:
    """Distinct from every other artifact's (chunks bind their index, the
    footer ``footer``, transcript and note none), and bound to the session."""
    return b"encounter:" + validate_session_id(session_id).encode("ascii")


def write_encounter(
    session_dir: Path, crypto: SessionCrypto, session_id: str, plaintext: bytes
) -> Path:
    """Encrypt and write ``encounter.enc`` ATOMICALLY (D11). The caller
    serialises the record (``encounter.EncounterRecord``); this module only
    holds the bytes' custody."""
    path = session_dir / ENCOUNTER_FILENAME
    atomic_write_bytes(
        path, crypto.encrypt(plaintext, _encounter_aad(session_id)), error_label="encounter record"
    )
    return path


def read_encounter(session_dir: Path, crypto: SessionCrypto, session_id: str) -> bytes:
    """Decrypt ``encounter.enc``. Called ONLY through
    ``encounter.read_encounter_record`` by its three authorised callers — a
    recovery checkout, an Unreviewed recording opened for review, and the
    once-per-session reminder rebuild at app start (Critical Constraint 7;
    round 59 PR-LOW-320) — never by the recovery listing, the sweep or a
    refresh. A missing,
    unreadable or unauthentic file raises ``StoreCorruptError`` (terse), and
    the caller treats the session as unlinked."""
    return _authentic(
        _read_or_none(session_dir / ENCOUNTER_FILENAME),
        crypto,
        _encounter_aad(session_id),
        "encounter record unavailable",
    )


def _read_or_none(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None


def _authentic(
    blob: bytes | None, crypto: SessionCrypto, aad: bytes | None, label: str
) -> bytes:
    """``blob`` decrypted under ``aad``; a terse ``StoreCorruptError(label)``
    when there is no blob or it does not authenticate — raised outside any
    handler, so it chains nothing."""
    if blob is not None:
        try:
            return crypto.decrypt(blob, aad)
        except InvalidTag:
            pass
    raise StoreCorruptError(label)


def _write_record_aad(session_id: str) -> bytes:
    """Distinct from every other artifact's, and bound to the session."""
    return b"write:" + validate_session_id(session_id).encode("ascii")


def write_write_record(
    session_dir: Path, crypto: SessionCrypto, session_id: str, plaintext: bytes
) -> Path:
    """Encrypt and write ``write.enc`` ATOMICALLY (temp + fsync +
    ``os.replace``, so the new document is durable before this returns —
    the draft write's ``attempting`` row is on disk before its request is
    dispatched, D5). The caller serialises the record
    (``draft_write.WriteRecord``); ``StoreWriteError`` on any failure, the
    previous document intact."""
    path = session_dir / WRITE_RECORD_FILENAME
    atomic_write_bytes(
        path, crypto.encrypt(plaintext, _write_record_aad(session_id)), error_label="write record"
    )
    return path


def read_write_record(session_dir: Path, crypto: SessionCrypto, session_id: str) -> bytes | None:
    """Decrypt ``write.enc``: None when there is no such file (no write was
    ever attempted for the session); ``StoreCorruptError`` (terse) when it
    exists but cannot be read or authenticated — the caller treats that as
    an outcome it cannot know (D5's ``record_unreadable``), never as none."""
    try:
        blob: bytes | None = (session_dir / WRITE_RECORD_FILENAME).read_bytes()
    except FileNotFoundError:
        return None
    except OSError:
        blob = None
    return _authentic(blob, crypto, _write_record_aad(session_id), "write record unreadable")


def saved_note_identity(session_dir: Path, crypto: SessionCrypto) -> str:
    """The saved note's identity for the draft write (D5): the SHA-256 hex
    of the decrypted ``note.enc`` plaintext — the exact bytes the review
    saved. ``StoreCorruptError`` (terse) when there is no readable,
    authentic ``note.enc``."""
    plaintext = _authentic(
        _read_or_none(session_dir / NOTE_FILENAME), crypto, None, "saved note unavailable"
    )
    return _note_identity(plaintext)


def read_note(session_dir: Path, crypto: SessionCrypto) -> GeneratedNote:
    """Decrypt, parse and VERIFY ``note.enc`` (the review view's read path).

    Verification — session binding and transcript-digest match against the
    decrypted on-disk transcript — runs through ``_verified_note``, the SAME
    code path ``complete_session`` uses, with the single Task-1.1 digest
    definition (plan Task 6.2 Done-when: the two can never disagree)."""
    note_path = session_dir / NOTE_FILENAME
    try:
        note_blob = note_path.read_bytes()
    except OSError as exc:
        raise StoreWriteError(f"note artifact unreadable: {exc}") from exc
    transcript_plain = _read_transcript_plain(session_dir, crypto)
    return _verified_note(session_dir, crypto, note_blob, transcript_plain)


# --------------------------------------------------------------------------
# Expiry sweep — the 24 h recovery rule, applied by code rather than by
# convention. NOT a hard guarantee (round 47 PR-LOW-001): an UNPROTECTED
# store becomes expiry-ELIGIBLE at 24 h and is destroyed by the next
# SUCCESSFUL sweep. A protected store (live / queued-under-review / checked
# out for recovery) is exempt while it stays protected, and a sweep that
# hits an OSError records `action="error"` and RETAINS the store for a later
# pass. What is enforced is the rule and its fail-safe direction, not a
# deadline.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SweepResult:
    session_id: str
    action: str  # kept | skipped_active | expired | orphan_gc | error | link_refused
    # Privacy-professional-controls plan D8 (round 1 PR-MED-004): for an
    # ``expired`` or ``orphan_gc`` session, its ``session_created_at`` read
    # BEFORE anything was deleted (epoch seconds; ``-inf`` when every stamp
    # was untrusted), so an audit row the sweep has to create keeps the
    # session's true date. None for every other action. Content-free.
    created_at: float | None = None


def earliest_trusted_timestamp(candidates: Iterable[float], now: float) -> float | None:
    """The earliest trustworthy candidate, clamped to ``now``, or None.

    THE shared trust core of the 24 h cap (round 42 MED-009): non-finite
    or future timestamps must never extend retention, in the sweep OR the
    recovery listing. Fallback policy when nothing is trusted stays with
    each caller (the sweep fails closed to destruction; the listing fails
    closed to not-listing, and lists conservatively only when NOTHING was
    readable at all).

    "Future" means beyond ``CLOCK_SKEW_TOLERANCE`` (round 48 HIGH-001).
    Filesystem mtimes routinely read a fraction of a second ahead of a
    later ``time.time()``, and treating that as untrusted DESTROYED
    sessions that had just been created — measured at 106/400 surviving
    the sweep under a coarse clock. Candidates inside the tolerance are
    accepted and clamped to ``now``. Because every other trusted value is
    already <= now, the clamp can never lower the minimum, so this is a
    strict relaxation inside ``(now, now + CLOCK_SKEW_TOLERANCE]`` and
    cannot make anything expire sooner than the untoleranced rule did.
    """
    trusted = [
        min(value, now)
        for value in candidates
        if math.isfinite(value) and value <= now + CLOCK_SKEW_TOLERANCE
    ]
    return min(trusted) if trusted else None


def session_created_at(session_dir: Path, now: float) -> float:
    """Best available creation time, FAIL-SAFE for the 24 h cap (PR-MED-004):
    a malformed header timestamp (NaN/inf) or one claiming the future must
    not extend retention, so collect header created-at + key-blob mtime,
    filter through `earliest_trusted_timestamp`, which also applies the
    clock-skew tolerance, and take the EARLIEST survivor.
    Falls back to the directory mtime, then to `now` (expires on the next
    window rather than never).

    Public since the privacy-professional-controls plan (D8): a ``pre_audit``
    audit row — a session started before the audit record existed — is dated
    by this, read BEFORE the directory is removed (the Complete and Discard
    callers read it themselves; the sweep carries it on ``SweepResult``). It
    reads the plaintext audio header and file times only, never a key.
    ``-inf`` (every stamp untrusted) is the audit's cue to use its own
    clock."""
    candidates: list[float] = []
    # No ``exists()`` pre-check (round 6 LOW-002): on Python 3.12 it re-raises
    # a non-ENOENT OSError. A missing header is FileNotFoundError here, so
    # this read raises no OSError at all.
    try:
        candidates.append(read_store_header(session_dir / AUDIO_FILENAME).created_at)
    except (SessionStoreError, OSError):
        pass  # fall through to file times
    for stat_target in (session_dir / KEY_FILENAME, session_dir):
        try:
            candidates.append(stat_target.stat().st_mtime)
        except OSError:
            pass
    earliest = earliest_trusted_timestamp(candidates, now)
    if earliest is not None:
        return earliest
    if candidates:
        # PR-MED-005: every readable timestamp is untrusted (non-finite or
        # implausibly far in the future) — fail CLOSED: report an age past any
        # window so the 24 h cap cannot be defeated by clock skew. Active
        # sessions are already protected by the caller's active_session_ids
        # exemption.
        return float("-inf")
    # Nothing readable at all (transient I/O trouble): keep this sweep and
    # retry next time rather than destroying on a possibly-flaky stat.
    return now


def audit_created_at(session_dir: Path, now: float | None = None) -> float | None:
    """``session_created_at`` for the audit record (privacy-professional-
    controls D8): a pre-audit session's creation time, read BEFORE its
    directory goes (``now`` defaults to the wall clock). NEVER raises — None
    lets the audit use its own clock, so dating a row can never block the
    Complete, Discard or write it describes (C2). The one copy every caller
    uses (round 7 LOW-014)."""
    try:
        return session_created_at(session_dir, time.time() if now is None else now)
    except Exception:  # noqa: BLE001 - a date, never a reason anything changes
        return None


def session_expires_at(
    session_dir: Path, now: float, *, max_age: timedelta = RECOVERY_WINDOW
) -> float:
    """When the sweep will first treat ``session_dir`` as expired (POSIX
    seconds): THE sweep's own creation time (``session_created_at``) plus
    the window, so the Unreviewed expiry warning (Cliniko workflow
    safeguards plan D6) can never promise longer than the sweep allows."""
    return session_created_at(session_dir, now) + max_age.total_seconds()


def _before_destroy(callback: Callable[[str], bool] | None, session_id: str) -> bool:
    """``sweep_sessions``' C1 hook: True when there is none or it succeeded;
    a raise counts as a failure (the session is kept this tick)."""
    if callback is None:
        return True
    try:
        return bool(callback(session_id))
    except Exception:  # noqa: BLE001 - fail toward keeping the key
        return False


def sweep_sessions(
    root: Path,
    *,
    active_session_ids: frozenset[str] = frozenset(),
    now: float | None = None,
    max_age: timedelta = RECOVERY_WINDOW,
    logger: logging.Logger | None = None,
    before_destroy: Callable[[str], bool] | None = None,
) -> list[SweepResult]:
    """Startup/periodic sweep of the sessions root.

    - NEVER touches sessions the caller reports live (recording/paused/
      processing) — keyed off state, not mtime (Critical Constraint).
    - Sessions older than `max_age` are destroyed key-FIRST (expired).
    - Orphan dirs (no key blob) and zero-length/truncated key blobs are
      garbage-collected: without a wrappable key the data is already
      cryptographically dead.
    - Only well-formed session-id directory names are handled; anything
      else is left alone (never delete what we did not create).

    ``before_destroy(session_id)`` (privacy-professional-controls C1) runs
    BEFORE an ``expired`` key deletion and BEFORE a DEAD key's (an existing
    zero-length or truncated blob) ``orphan_gc`` deletion — the caller
    removes any Past-sessions entry an interrupted Complete published for
    that id, key first. False (or a raise) means it could not: the session
    is left alone this tick (``error``), key and all, so no discarded
    content can later be committed. It is NOT called for a CONFIRMED-absent
    key: that orphan follows a Complete that reached its key deletion, and
    its entry is committed, never deleted.
    """
    current = time.time() if now is None else now
    results: list[SweepResult] = []
    if not root.is_dir():
        return results
    for child in sorted(root.iterdir()):
        if not child.is_dir() or not _SESSION_ID_RE.fullmatch(child.name):
            continue
        session_id = child.name
        if session_id in active_session_ids:
            results.append(SweepResult(session_id, "skipped_active"))
            continue
        linked = link_state(child)
        if linked is not False:
            # H3 round 35 SEC-002: a linked folder is never followed — its
            # `key.dpapi` is ANOTHER folder's (a session's, or a Past-sessions
            # entry's). Left in place, untouched; status unreadable: next tick.
            refused = "link_refused" if linked else "error"
            results.append(SweepResult(session_id, refused))
            if logger is not None:
                log_event(logger, "session_sweep", session_id=session_id, detail_code=refused)
            continue
        key_path = child / KEY_FILENAME
        action: str
        created: float | None = None
        try:
            # PR-MED-006: a single stat() distinguishes CONFIRMED-missing
            # custody (FileNotFoundError -> orphan GC) from a transiently
            # inaccessible key (any other OSError -> "error" below, NO
            # deletion). Path.exists() suppresses OSError and returns False,
            # which would misread an inaccessible key.dpapi as an orphan and
            # risk premature cryptographic deletion of a recoverable session.
            try:
                key_blob_size = key_path.stat().st_size
            except FileNotFoundError:
                key_blob_size = -1  # confirmed absent: orphan custody
            if key_blob_is_dead(key_blob_size):
                # Orphan or cryptographically-dead custody: GC. The date is
                # read first (D8): the removal takes the header with it.
                created = session_created_at(child, current)
                if key_blob_size >= 0 and not _before_destroy(before_destroy, session_id):
                    created = None
                    action = "error"  # C1: the dead key stays this tick
                else:
                    delete_session_key(child)
                    shutil.rmtree(child, ignore_errors=True)
                    action = "orphan_gc"
            elif current - (created := session_created_at(child, current)) >= (
                max_age.total_seconds()
            ):
                if not _before_destroy(before_destroy, session_id):
                    created = None
                    action = "error"  # C1: the key stays this tick
                else:
                    delete_session_key(child)  # key first — binding ordering
                    shutil.rmtree(child, ignore_errors=True)
                    action = "expired"
            else:
                created = None
                action = "kept"
        except OSError:
            created = None
            action = "error"
        results.append(SweepResult(session_id, action, created))
        if logger is not None:
            log_event(logger, "session_sweep", session_id=session_id, detail_code=action)
    return results
