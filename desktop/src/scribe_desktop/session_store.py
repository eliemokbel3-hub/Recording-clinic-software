"""Encrypted session store + DPAPI key custody (Phase 2 Step 2).

On-disk layout (plan Schema / Data Changes), all under
``%LOCALAPPDATA%\\ClinikoScribe\\sessions\\<session_id>\\``:

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

Durability ordering (BINDING, plan key-custody decision):
- ``key.dpapi`` is written atomically (temp + fsync + ``os.replace``)
  BEFORE the first chunk — ``SessionChunkStore.create`` refuses to create
  ``audio.enc`` unless the key blob already exists beside it.
- Complete: fsync ``transcript.enc`` → verify a decrypt round-trip →
  THEN delete the key.
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

import logging
import math
import os
import re
import shutil
import struct
import sys
import time
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import BinaryIO, Final

from cryptography.exceptions import InvalidTag

from scribe_desktop.logging_setup import log_event
from scribe_desktop.secure_storage import SessionCrypto

KEY_FILENAME: Final = "key.dpapi"
AUDIO_FILENAME: Final = "audio.enc"
TRANSCRIPT_FILENAME: Final = "transcript.enc"

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

# Binding note from Step 1 (PR-MED-002/003): a session id is EXACTLY
# uuid4().hex, and key_reference resolves ONLY through resolve_key_path.
_SESSION_ID_RE: Final = re.compile(r"^[0-9a-f]{32}$")

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


def default_sessions_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "ClinikoScribe" / "sessions"


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
        Refuses to append to a finished (footered) store."""
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
# DPAPI key custody (Windows-only; CryptProtectData, current-user scope).
# --------------------------------------------------------------------------


def _require_windows() -> None:
    if sys.platform != "win32":
        raise RuntimeError("DPAPI key custody is Windows-only")


def wrap_key_to_file(crypto: SessionCrypto, session_dir: Path) -> Path:
    """DPAPI-wrap the session key and write `key.dpapi` ATOMICALLY
    (temp + fsync + os.replace) — called BEFORE the first chunk."""
    _require_windows()
    import win32crypt

    blob: bytes = win32crypt.CryptProtectData(
        crypto.export_key(), "ClinikoScribe session key", None, None, None, 0
    )
    key_path = session_dir / KEY_FILENAME
    tmp_path = session_dir / (KEY_FILENAME + ".tmp")
    try:
        with tmp_path.open("wb") as stream:
            stream.write(blob)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_path, key_path)
    except OSError as exc:
        raise StoreWriteError(f"failed writing key custody blob: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)
    return key_path


def unwrap_key_from_file(session_dir: Path) -> SessionCrypto:
    """Read + DPAPI-unwrap `key.dpapi`. Missing/zero-length/truncated blobs
    raise KeyCustodyError — the session is cryptographically unrecoverable."""
    _require_windows()
    import win32crypt

    key_path = session_dir / KEY_FILENAME
    try:
        blob = key_path.read_bytes()
    except OSError as exc:
        raise KeyCustodyError(f"key custody blob unreadable: {exc}") from exc
    if len(blob) < _MIN_KEY_BLOB_BYTES:
        raise KeyCustodyError("key custody blob is zero-length or truncated")
    try:
        _description, key = win32crypt.CryptUnprotectData(blob, None, None, None, 0)
    except Exception as exc:  # pywin32 raises pywintypes.error (not OSError-rooted)
        raise KeyCustodyError("key custody blob failed DPAPI unwrap") from exc
    try:
        return SessionCrypto.from_key(key)
    except ValueError as exc:
        raise KeyCustodyError("unwrapped key has wrong length") from exc


def delete_session_key(session_dir: Path) -> None:
    """Delete the wrapped key blob — THE cryptographic deletion of the
    session (same-user boundary; NTFS residual documented). Idempotent."""
    (session_dir / KEY_FILENAME).unlink(missing_ok=True)


def complete_session(session_dir: Path, crypto: SessionCrypto) -> None:
    """Complete ordering (binding): fsync `transcript.enc` -> verify a
    decrypt round-trip -> THEN delete the key. Any failure keeps the key."""
    transcript_path = session_dir / TRANSCRIPT_FILENAME
    try:
        with transcript_path.open("r+b") as stream:
            os.fsync(stream.fileno())
            blob = stream.read()
    except OSError as exc:
        raise StoreWriteError(f"transcript not durably readable: {exc}") from exc
    try:
        crypto.decrypt(blob)
    except InvalidTag as exc:
        raise StoreCorruptError("transcript failed decrypt verification; key retained") from exc
    delete_session_key(session_dir)
    # PR-HIGH-001 (downgraded MED): after successful custody deletion no
    # application-owned object may decrypt the session — destroy the
    # in-memory key too, not just the wrapped blob.
    crypto.destroy()


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
# Expiry sweep (24 h recovery cap — enforced by code, not convention).
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SweepResult:
    session_id: str
    action: str  # kept | skipped_active | expired | orphan_gc | error


def trusted_timestamps(candidates: Iterable[float], now: float) -> list[float]:
    """The fail-safe timestamp rule for the 24 h cap, in ONE place.

    Shared by the sweep and the recovery listing — they enforce the same cap
    and previously carried separate copies of this rule, which is how both
    inherited the same clock-skew defect.

    Drops non-finite values and anything further than ``CLOCK_SKEW_TOLERANCE``
    into the future (a real clock problem: never allowed to extend retention).
    Values inside that tolerance are clamped to ``now``, so a file written
    milliseconds ago is aged from now rather than being thrown away.
    """
    return [
        min(value, now)
        for value in candidates
        if math.isfinite(value) and value <= now + CLOCK_SKEW_TOLERANCE
    ]


def _session_created_at(session_dir: Path, now: float) -> float:
    """Best available creation time, FAIL-SAFE for the 24 h cap (PR-MED-004):
    a malformed header timestamp (NaN/inf) or one claiming the future must
    not extend retention, so collect header created-at + key-blob mtime,
    filter through `trusted_timestamps`, and take the EARLIEST survivor.
    Falls back to the directory mtime, then to `now` (expires on the next
    window rather than never)."""
    candidates: list[float] = []
    audio_path = session_dir / AUDIO_FILENAME
    if audio_path.exists():
        try:
            candidates.append(read_store_header(audio_path).created_at)
        except (SessionStoreError, OSError):
            pass  # fall through to file times
    for stat_target in (session_dir / KEY_FILENAME, session_dir):
        try:
            candidates.append(stat_target.stat().st_mtime)
        except OSError:
            pass
    trusted = trusted_timestamps(candidates, now)
    if trusted:
        return min(trusted)
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


def sweep_sessions(
    root: Path,
    *,
    active_session_ids: frozenset[str] = frozenset(),
    now: float | None = None,
    max_age: timedelta = RECOVERY_WINDOW,
    logger: logging.Logger | None = None,
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
        key_path = child / KEY_FILENAME
        action: str
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
            if key_blob_size < _MIN_KEY_BLOB_BYTES:
                # Orphan or cryptographically-dead custody: GC.
                delete_session_key(child)
                shutil.rmtree(child, ignore_errors=True)
                action = "orphan_gc"
            elif current - _session_created_at(child, current) >= max_age.total_seconds():
                delete_session_key(child)  # key first — binding ordering
                shutil.rmtree(child, ignore_errors=True)
                action = "expired"
            else:
                action = "kept"
        except OSError:
            action = "error"
        results.append(SweepResult(session_id, action))
        if logger is not None:
            log_event(logger, "session_sweep", session_id=session_id, detail_code=action)
    return results
