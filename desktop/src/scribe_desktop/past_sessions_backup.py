"""The Past-sessions backup file (past-sessions-backup plan Task 1.3; D2, D3,
D4; Critical Constraints C3 and C8).

A backup is ONE file, ``ClinikoScribe-backup-YYYY-MM-DD[-n].csbk``: a
stored-only classic ZIP read ONLY through its encrypted manifest.

- ``header.json`` (plaintext, the first member at offset 0, at most 4 KiB):
  the format version, the app version and channel, when it was made, the
  KDF's parameters and salt, and the planned entry and row counts (upper
  bounds, never shown). Nothing the writer learns while it copies.
- ``manifest.enc``: AES-GCM under the backup key ``K_b`` with the associated
  data ``csbk-manifest:`` + SHA-256(header bytes), so any change to the header
  fails the manifest. ONE structure (``BackupManifest``): every entry's
  wrapped key and files and every row by size and SHA-256, what was left
  out, and ``not_restorable``.
- ``audit-key.enc`` (when the audit store has a key) and ``keys/<id>.enc``:
  the audit store key and each entry key, wrapped under ``K_b`` with
  ``csbk-audit-key`` / ``csbk-entry-key:<id>``.
- ``entries/<id>/<label|transcript|note|generated>.enc`` and
  ``audit/<YYYY-MM>/<id>.enc``: the archive's and the audit store's own
  ciphertext, byte for byte.

``K_b`` is Argon2id over the practitioner's passphrase (D3), fresh per
backup (a fresh salt); the passphrase is never stored. The reader refuses by
a CLOSED code at the first failure and writes nothing (C8): the preflight
walks the ZIP's own records with ``struct`` before anything else (no ZIP64,
no comment, no extra field, stored only, unique ASCII names, the header
first), then the header and its KDF envelope, the channel, the manifest, the
member set and every SHA-256, and finally the open check — every row
authenticates and every entry opens (``past_sessions.entry_opens``). The
reader iterates the manifest, never the ZIP's own listing, and never uses
``zipfile`` (the writer does).

Nothing here touches the network, the archive or the audit store; secrets
are ``bytearray``s the caller zeroes (D4: ``AESGCM`` and ``bytes()`` make
immutable copies that cannot be — the threat model names them)."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import struct
import zipfile
from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, Final, Literal, Protocol, cast

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from scribe_desktop import __version__, install_layout
from scribe_desktop.audit import (
    MAX_ROW_FILE_BYTES,
    AuditSnapshot,
    AuditUnavailable,
    RowDescriptor,
    RowState,
    _row_aad,
    row_importable,
    valid_month,
)
from scribe_desktop.logging_setup import exception_type_name
from scribe_desktop.past_sessions import (
    AUDIO_KEY_FILENAME,
    ENTRY_FILE_KINDS,
    MAX_LABEL_FILE_BYTES,
    ExportIdentity,
    FileIdentity,
    PastSessionError,
    PastSessionStore,
    _audio_key_state,
    _remove_part,
    entry_opens,
    inspect_entry_file,
)
from scribe_desktop.session_store import SESSION_ID_PATTERN, link_state

FORMAT_VERSION: Final = 1
# The one place the file name's prefix exists (D2); ``test_install_layout``'s
# literal scan names it.
BACKUP_FILENAME_PREFIX: Final = "ClinikoScribe-backup-"
BACKUP_SUFFIX: Final = ".csbk"
PART_SUFFIX: Final = ".csbk.part"
HEADER_MEMBER: Final = "header.json"
MANIFEST_MEMBER: Final = "manifest.enc"
AUDIT_KEY_MEMBER: Final = "audit-key.enc"

# D2's limits, each a closed refusal: no ZIP64 anywhere.
MAX_BACKUP_BYTES: Final = 1024 * 1024 * 1024
MAX_MEMBERS: Final = 65_535
MAX_ENTRY_FILE_BYTES: Final = 64 * 1024 * 1024
MAX_HEADER_BYTES: Final = 4 * 1024
MAX_MANIFEST_BYTES: Final = 16 * 1024 * 1024
MAX_MEMBER_NAME_BYTES: Final = 128
MAX_DIRECTORY_RECORD_BYTES: Final = 256
_END_SEARCH_BYTES: Final = 64 * 1024 + 22

# D3: Argon2id's defaults and the FINITE envelope a reader accepts.
KDF_NAME: Final = "argon2id"
KDF_SALT_BYTES: Final = 16
KEY_BYTES: Final = 32
KDF_ITERATIONS: Final = 3
KDF_LANES: Final = 1
KDF_MEMORY_COST: Final = 262_144  # KiB: 256 MiB
KDF_MEMORY_RANGE: Final = (65_536, 524_288)
KDF_ITERATIONS_RANGE: Final = (2, 10)
KDF_LANES_RANGE: Final = (1, 4)

_NONCE_BYTES: Final = 12
_TAG_BYTES: Final = 16
WRAPPED_KEY_BYTES: Final = _NONCE_BYTES + KEY_BYTES + _TAG_BYTES
_MANIFEST_AAD_PREFIX: Final = b"csbk-manifest:"
_ENTRY_KEY_AAD_PREFIX: Final = b"csbk-entry-key:"
_AUDIT_KEY_AAD: Final = b"csbk-audit-key"

_SHA256_PATTERN: Final = r"^[0-9a-f]{64}$"
_SESSION_ID_RE: Final = re.compile(SESSION_ID_PATTERN)
_MEMBER_NAME_RE: Final = re.compile(r"^[A-Za-z0-9._/-]{1,128}$")
_APP_VERSION_PATTERN: Final = r"^[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,6}$"
_READ_CHUNK: Final = 1024 * 1024

LeftOutReason = Literal[
    "holds_recording", "unreadable", "incomplete", "damaged", "changed", "uninspectable"
]
Channel = Literal["production", "dev"]


# ---------------------------------------------------------------------------
# Errors: closed codes, content-free (C3).
# ---------------------------------------------------------------------------

# What the READER refuses (D2), and the KDF's own refusals (D3).
FORMAT_CODES: Final = frozenset(
    {
        "unreadable",
        "not_a_backup",
        "too_large",
        "zip64",
        "comment",
        "too_many_members",
        "directory",
        "directory_too_large",
        "directory_count",
        "member_name",
        "member_duplicate",
        "member_extra",
        "member_comment",
        "member_method",
        "member_flags",
        "member_sizes",
        "local_header",
        "overlap",
        "header_first",
        "header_too_large",
        "manifest_missing",
        "manifest_too_large",
        "header_invalid",
        "format_newer",
        "kdf_unknown",
        "kdf_out_of_range",
        "kdf_memory",
        "kdf_unavailable",
        "other_channel",
        "passphrase",
        "manifest_invalid",
        "manifest_bounds",
        "member_set",
        "member_size",
        "member_hash",
        "audit_key",
        "row_unauthentic",
        "entry_key",
        "entry_does_not_open",
    }
)
# What a RUN refuses or fails with (D1, D5, D6, D8).
RUN_CODES: Final = frozenset(
    {
        "archive_unreadable",
        "audit_unavailable",
        "too_large",
        "nothing_to_back_up",
        "nothing_could_be_read",
        "destination_refused",
        "write_failed",
        "publish_unverified",
        "source_changed",
        "unexpected",
    }
)


class BackupFormatError(Exception):
    """The file was refused (``code`` one of ``FORMAT_CODES``; anything else
    reads ``unreadable``). ``channel`` names the other channel for
    ``other_channel``. The text is the code only."""

    def __init__(self, code: str, *, channel: str | None = None) -> None:
        self.code = code if code in FORMAT_CODES else "unreadable"
        self.channel = channel
        super().__init__(self.code)


class BackupRunError(Exception):
    """A run refused or failed (``code`` one of ``RUN_CODES``; anything else
    reads ``unexpected``). The text is the code only. From the writer (D6):
    ``part_may_remain`` — the ``.part`` file could not be confirmed removed,
    so the line ends "A partial backup file may remain on the drive." — and,
    for ``nothing_could_be_read``, the ``left_out`` counts the line gives.
    ``error_type``: for an ``unexpected`` one translated from an unforeseen
    exception, that exception's TYPE name only (sanitised by
    ``logging_setup.exception_type_name``; never its text or the object), so
    the page can log it once (D4; peer round 30 PR-LOW-301)."""

    def __init__(
        self,
        code: str,
        *,
        part_may_remain: bool = False,
        left_out: LeftOut | None = None,
        error_type: str | None = None,
    ) -> None:
        self.code = code if code in RUN_CODES else "unexpected"
        self.part_may_remain = part_may_remain
        self.left_out = left_out
        self.error_type = error_type
        super().__init__(self.code)


# ---------------------------------------------------------------------------
# The header and the manifest (D2).
# ---------------------------------------------------------------------------


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class KdfParams(_Frozen):
    """The KDF's name, salt (hex) and work parameters — read from the
    unauthenticated header, so checked against the envelope BEFORE any
    derivation (``check_kdf``)."""

    name: str = Field(max_length=32)
    salt: str = Field(pattern=r"^[0-9a-f]{32}$")
    iterations: int = Field(strict=True)
    lanes: int = Field(strict=True)
    memory_cost: int = Field(strict=True)


class BackupHeader(_Frozen):
    format_version: Literal[1] = FORMAT_VERSION
    app_version: str = Field(pattern=_APP_VERSION_PATTERN)
    channel: Channel
    made_at: AwareDatetime
    kdf: KdfParams
    max_entries: int = Field(ge=0, le=MAX_MEMBERS, strict=True)
    max_rows: int = Field(ge=0, le=MAX_MEMBERS, strict=True)

    def to_bytes(self) -> bytes:
        return self.model_dump_json().encode("utf-8")


class Digest(_Frozen):
    size: int = Field(ge=0, strict=True)
    sha256: str = Field(pattern=_SHA256_PATTERN)


class EntryFiles(_Frozen):
    label: Digest
    transcript: Digest
    note: Digest | None = None
    generated: Digest | None = None

    @model_validator(mode="after")
    def _bounded(self) -> EntryFiles:
        if self.label.size > MAX_LABEL_FILE_BYTES:
            raise ValueError("a label is bounded")
        for digest in (self.transcript, self.note, self.generated):
            if digest is not None and digest.size > MAX_ENTRY_FILE_BYTES:
                raise ValueError("an entry file is bounded")
        return self

    def kinds(self) -> dict[str, Digest]:
        """The files present, by kind (``past_sessions.ENTRY_FILE_KINDS``)."""
        present = {
            "label": self.label,
            "transcript": self.transcript,
            "note": self.note,
            "generated": self.generated,
        }
        return {kind: digest for kind, digest in present.items() if digest is not None}


class ManifestEntry(_Frozen):
    key: Digest
    files: EntryFiles

    @field_validator("key")
    @classmethod
    def _wrapped_key(cls, key: Digest) -> Digest:
        if key.size != WRAPPED_KEY_BYTES:
            raise ValueError("a wrapped key has one size")
        return key


class ManifestRow(_Frozen):
    month: str
    size: int = Field(ge=0, le=MAX_ROW_FILE_BYTES, strict=True)
    sha256: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("month")
    @classmethod
    def _a_real_month(cls, month: str) -> str:
        if valid_month(month) is None:
            raise ValueError("a row's month is a real calendar month")
        return month


class LeftOut(_Frozen):
    entries: dict[LeftOutReason, int] = Field(default_factory=dict)
    rows: int = Field(default=0, ge=0, strict=True)

    @field_validator("entries")
    @classmethod
    def _counts(cls, entries: dict[LeftOutReason, int]) -> dict[LeftOutReason, int]:
        if any(count < 0 for count in entries.values()):
            raise ValueError("a count is not negative")
        return entries


class BackupManifest(_Frozen):
    """The manifest (D2): ONE structure, so its parts cannot disagree. The
    counts shown anywhere are the lengths of these maps."""

    channel: Channel
    app_version: str = Field(pattern=_APP_VERSION_PATTERN)
    made_at: AwareDatetime
    entries: dict[str, ManifestEntry]
    audit_key: Digest | None = None
    rows: dict[str, ManifestRow]
    rows_unknown: tuple[str, ...] = ()
    left_out: LeftOut = LeftOut()
    not_restorable: int = Field(default=0, ge=0, strict=True)

    @model_validator(mode="after")
    def _consistent(self) -> BackupManifest:
        ids = [*self.entries, *self.rows, *self.rows_unknown]
        if not all(_SESSION_ID_RE.fullmatch(session_id) for session_id in ids):
            raise ValueError("every id is a session id")
        if len(set(self.rows_unknown)) != len(self.rows_unknown) or set(
            self.rows_unknown
        ) & set(self.rows):
            raise ValueError("an unknown row is listed once and is not a row")
        if self.audit_key is None and self.rows:
            raise ValueError("rows need the audit key")
        if self.audit_key is not None and self.audit_key.size != WRAPPED_KEY_BYTES:
            raise ValueError("a wrapped key has one size")
        return self

    def to_bytes(self) -> bytes:
        return self.model_dump_json(exclude_none=True).encode("utf-8")


def entry_member(session_id: str, kind: str) -> str:
    return f"entries/{session_id}/{kind}.enc"


def key_member(session_id: str) -> str:
    return f"keys/{session_id}.enc"


def row_member(month: str, session_id: str) -> str:
    return f"audit/{month}/{session_id}.enc"


def member_digests(manifest: BackupManifest) -> dict[str, Digest]:
    """Every payload member the manifest implies, with its size and hash —
    the two envelope members (header and manifest) excepted."""
    digests: dict[str, Digest] = {}
    if manifest.audit_key is not None:
        digests[AUDIT_KEY_MEMBER] = manifest.audit_key
    for session_id, entry in manifest.entries.items():
        digests[key_member(session_id)] = entry.key
        for kind, digest in entry.files.kinds().items():
            digests[entry_member(session_id, kind)] = digest
    for session_id, row in manifest.rows.items():
        digests[row_member(row.month, session_id)] = Digest(size=row.size, sha256=row.sha256)
    return digests


def manifest_aad(header_bytes: bytes) -> bytes:
    """``csbk-manifest:`` + SHA-256(header bytes): any change to the header
    fails the manifest (D2)."""
    return _MANIFEST_AAD_PREFIX + hashlib.sha256(header_bytes).digest()


def entry_key_aad(session_id: str) -> bytes:
    return _ENTRY_KEY_AAD_PREFIX + session_id.encode("ascii")


# ---------------------------------------------------------------------------
# Key wrapping under K_b (D2) — AES-GCM, fresh nonce per wrap.
# ---------------------------------------------------------------------------


def seal(key: bytes | bytearray, plaintext: bytes | bytearray, aad: bytes) -> bytes:
    nonce = os.urandom(_NONCE_BYTES)
    return nonce + AESGCM(bytes(key)).encrypt(nonce, bytes(plaintext), aad)


def unseal(key: bytes | bytearray, blob: bytes, aad: bytes) -> bytes:
    """``InvalidTag`` for anything that does not authenticate."""
    if len(blob) <= _NONCE_BYTES:
        raise InvalidTag()
    return AESGCM(bytes(key)).decrypt(blob[:_NONCE_BYTES], blob[_NONCE_BYTES:], aad)


def unwrap_key(k_b: bytes | bytearray, blob: bytes, aad: bytes) -> bytearray:
    """A wrapped 32-byte key as a ``bytearray`` the caller zeroes;
    ``InvalidTag`` (or ``ValueError`` for a wrong length)."""
    key = bytearray(unseal(k_b, blob, aad))
    if len(key) != KEY_BYTES:
        zero(key)
        raise ValueError("a wrapped key is 32 bytes")
    return key


def zero(buffer: bytearray | None) -> None:
    """Overwrite a mutable secret (D4: "zeroed" means the ``bytearray``s)."""
    if buffer is not None:
        for index in range(len(buffer)):
            buffer[index] = 0


# ---------------------------------------------------------------------------
# The KDF (D3).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KdfFloor:
    """The test floor (D15): ONLY a test sets ``_kdf_floor_for_tests``, which
    lowers the envelope's minimums AND is what a new backup uses — never a
    header field. Production leaves it None."""

    memory_cost: int = 8
    iterations: int = 1
    lanes: int = 1


_kdf_floor_for_tests: KdfFloor | None = None


def check_kdf(kdf: KdfParams) -> None:
    """D3's envelope, checked BEFORE any derivation (the header is not
    authenticated until the manifest decrypts): ``kdf_unknown`` for another
    name, ``kdf_out_of_range`` for a work parameter outside its range."""
    if kdf.name != KDF_NAME:
        raise BackupFormatError("kdf_unknown")
    floor = _kdf_floor_for_tests
    memory_low = floor.memory_cost if floor is not None else KDF_MEMORY_RANGE[0]
    iterations_low = floor.iterations if floor is not None else KDF_ITERATIONS_RANGE[0]
    if not (
        memory_low <= kdf.memory_cost <= KDF_MEMORY_RANGE[1]
        and iterations_low <= kdf.iterations <= KDF_ITERATIONS_RANGE[1]
        and KDF_LANES_RANGE[0] <= kdf.lanes <= KDF_LANES_RANGE[1]
    ):
        raise BackupFormatError("kdf_out_of_range")


def new_kdf_params() -> KdfParams:
    """A new backup's parameters: a fresh salt and D3's defaults (the test
    floor's values while a test has set one)."""
    floor = _kdf_floor_for_tests
    return KdfParams(
        name=KDF_NAME,
        salt=os.urandom(KDF_SALT_BYTES).hex(),
        iterations=floor.iterations if floor is not None else KDF_ITERATIONS,
        lanes=floor.lanes if floor is not None else KDF_LANES,
        memory_cost=floor.memory_cost if floor is not None else KDF_MEMORY_COST,
    )


def argon2id_derive(
    secret: bytes | bytearray, salt: bytes, *, iterations: int, lanes: int, memory_cost: int
) -> bytes:
    """THE derivation seam (Task 1.7's self-check calls it at small fixed
    parameters; tests replace it): Argon2id, 32 bytes, ``memory_cost`` in
    KiB. No envelope check here — ``derive_key`` makes it first."""
    from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

    return Argon2id(
        salt=salt,
        length=KEY_BYTES,
        iterations=iterations,
        lanes=lanes,
        memory_cost=memory_cost,
    ).derive(bytes(secret))


def derive_key(passphrase: bytes | bytearray, kdf: KdfParams) -> bytearray:
    """``K_b`` from ``passphrase`` (D3): the envelope first; a
    ``MemoryError`` refused by type (``kdf_memory``); any other failure of
    the derivation ``kdf_unavailable``. The caller zeroes the result."""
    check_kdf(kdf)
    try:
        derived = argon2id_derive(
            passphrase,
            bytes.fromhex(kdf.salt),
            iterations=kdf.iterations,
            lanes=kdf.lanes,
            memory_cost=kdf.memory_cost,
        )
    except MemoryError:
        raise BackupFormatError("kdf_memory") from None
    except Exception:  # noqa: BLE001 - an unforeseen failure is named, never echoed
        raise BackupFormatError("kdf_unavailable") from None
    return bytearray(derived)


# ---------------------------------------------------------------------------
# The size-and-read seam (D2): every byte the reader looks at comes through it.
# ---------------------------------------------------------------------------


class ByteSource(Protocol):
    def size(self) -> int: ...

    def read_at(self, offset: int, length: int) -> bytes: ...


class PathSource:
    """A backup file by path: each read opens it afresh (a file changed
    between reads is caught by the hashes). ``BackupFormatError
    ("unreadable")`` for any read error or short read."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def size(self) -> int:
        try:
            return os.stat(self._path).st_size
        except OSError:
            raise BackupFormatError("unreadable") from None

    def read_at(self, offset: int, length: int) -> bytes:
        try:
            with self._path.open("rb") as stream:
                stream.seek(offset)
                blob = stream.read(length)
        except OSError:
            raise BackupFormatError("unreadable") from None
        if len(blob) != length:
            raise BackupFormatError("unreadable")
        return blob


class HandleSource:
    """An open read-write handle — the writer's own (D6: what is verified is
    what this run wrote) — or any seekable binary stream in tests."""

    def __init__(self, stream: BinaryIO) -> None:
        self._stream = stream

    def size(self) -> int:
        try:
            return self._stream.seek(0, os.SEEK_END)
        except (OSError, ValueError):
            raise BackupFormatError("unreadable") from None

    def read_at(self, offset: int, length: int) -> bytes:
        try:
            self._stream.seek(offset)
            blob = self._stream.read(length)
        except (OSError, ValueError):
            raise BackupFormatError("unreadable") from None
        if len(blob) != length:
            raise BackupFormatError("unreadable")
        return blob


# ---------------------------------------------------------------------------
# The preflight (D2 step 1): the ZIP's own records, walked with ``struct``.
# ---------------------------------------------------------------------------

_END = struct.Struct("<IHHHHIIH")  # 22 bytes
_END_MAGIC: Final = b"PK\x05\x06"
_ZIP64_LOCATOR: Final = b"PK\x06\x07"
_ZIP64_LOCATOR_BYTES: Final = 20
_CENTRAL = struct.Struct("<IHHHHHHIIIHHHHHII")  # 46 bytes
_CENTRAL_SIGNATURE: Final = 0x02014B50
_LOCAL = struct.Struct("<IHHHHHIIIHH")  # 30 bytes
_LOCAL_SIGNATURE: Final = 0x04034B50
# Encrypted, a data descriptor, strong encryption, a masked header.
_FORBIDDEN_FLAGS: Final = 0x0001 | 0x0008 | 0x0040 | 0x2000


@dataclass(frozen=True)
class MemberSpan:
    """Where one member's (stored) data lies in the file."""

    offset: int
    size: int


def preflight(source: ByteSource) -> dict[str, MemberSpan]:
    """D2 step 1, before ``zipfile`` is used at all: the end record, the
    central directory and every local header, checked record by record.
    Returns each member's data span, in directory order."""
    size = source.size()
    if size > MAX_BACKUP_BYTES:
        raise BackupFormatError("too_large")
    if size < _END.size:
        raise BackupFormatError("not_a_backup")
    tail_length = min(size, _END_SEARCH_BYTES)
    tail = source.read_at(size - tail_length, tail_length)
    end_at = tail.rfind(_END_MAGIC)
    if end_at < 0:
        raise BackupFormatError("not_a_backup")
    if end_at != tail_length - _END.size:
        raise BackupFormatError("comment")
    (_sig, disk, directory_disk, on_disk, total, directory_size, directory_offset, comment) = (
        _END.unpack(tail[end_at:])
    )
    if comment:
        raise BackupFormatError("comment")
    # A ZIP64 locator is the 20 bytes right before the end record; the
    # directory's own last bytes there can never spell it (names are
    # ``_MEMBER_NAME_RE``; the writer's attributes are zero).
    locator_at = end_at - _ZIP64_LOCATOR_BYTES
    if (
        locator_at >= 0 and tail[locator_at : locator_at + 4] == _ZIP64_LOCATOR
    ) or 0xFFFFFFFF in (directory_size, directory_offset):
        raise BackupFormatError("zip64")
    if disk or directory_disk or on_disk != total:
        raise BackupFormatError("directory")
    if total > MAX_MEMBERS:
        raise BackupFormatError("too_many_members")
    if directory_size > MAX_DIRECTORY_RECORD_BYTES * total:
        raise BackupFormatError("directory_too_large")
    if directory_offset + directory_size != size - _END.size:
        raise BackupFormatError("directory")
    directory = source.read_at(directory_offset, directory_size)
    records = _walk_directory(directory, total)
    if not records or records[0][0] != HEADER_MEMBER or records[0][1] != 0:
        raise BackupFormatError("header_first")
    if records[0][2] > MAX_HEADER_BYTES:
        raise BackupFormatError("header_too_large")
    manifest = [record for record in records if record[0] == MANIFEST_MEMBER]
    if not manifest:
        raise BackupFormatError("manifest_missing")
    if manifest[0][2] > MAX_MANIFEST_BYTES:
        raise BackupFormatError("manifest_too_large")
    spans: dict[str, MemberSpan] = {}
    previous_end = 0
    for name, local_offset, member_size in sorted(records, key=lambda record: record[1]):
        span = _check_local_header(source, name, local_offset, member_size, directory_offset)
        if local_offset < previous_end:
            raise BackupFormatError("overlap")
        previous_end = span.offset + span.size
        spans[name] = span
    return {name: spans[name] for name, _offset, _size in records}


def _walk_directory(directory: bytes, total: int) -> list[tuple[str, int, int]]:
    """Every central-directory record as (name, local header offset, size):
    their number equals the declared count; each name ASCII, at most 128
    bytes, unique; no extra field or comment; stored, equal sizes, no
    forbidden flag."""
    records: list[tuple[str, int, int]] = []
    seen: set[str] = set()
    offset = 0
    while offset < len(directory):
        if len(directory) - offset < _CENTRAL.size:
            raise BackupFormatError("directory")
        (
            signature,
            _made_by,
            _needed,
            flags,
            method,
            _time,
            _date,
            _crc,
            compressed,
            uncompressed,
            name_length,
            extra_length,
            comment_length,
            disk_start,
            _internal,
            _external,
            local_offset,
        ) = _CENTRAL.unpack_from(directory, offset)
        if signature != _CENTRAL_SIGNATURE or disk_start:
            raise BackupFormatError("directory")
        if extra_length:
            raise BackupFormatError("member_extra")
        if comment_length:
            raise BackupFormatError("member_comment")
        start = offset + _CENTRAL.size
        end = start + name_length
        if end > len(directory):
            raise BackupFormatError("directory")
        name = _member_name(directory[start:end])
        if name in seen:
            raise BackupFormatError("member_duplicate")
        seen.add(name)
        if method != zipfile.ZIP_STORED:
            raise BackupFormatError("member_method")
        if flags & _FORBIDDEN_FLAGS:
            raise BackupFormatError("member_flags")
        if compressed != uncompressed:
            raise BackupFormatError("member_sizes")
        records.append((name, local_offset, uncompressed))
        offset = end
    if len(records) != total:
        raise BackupFormatError("directory_count")
    return records


def _member_name(raw: bytes) -> str:
    try:
        name = raw.decode("ascii")
    except UnicodeDecodeError:
        raise BackupFormatError("member_name") from None
    if len(raw) > MAX_MEMBER_NAME_BYTES or not _MEMBER_NAME_RE.fullmatch(name):
        raise BackupFormatError("member_name")
    return name


def _check_local_header(
    source: ByteSource, name: str, offset: int, size: int, directory_offset: int
) -> MemberSpan:
    """The member's LOCAL header, checked like its directory record — the
    signature, stored, no data descriptor, the same name and sizes, and NO
    extra field (a ZIP64 field can hide there alone)."""
    if offset + _LOCAL.size > directory_offset:
        raise BackupFormatError("local_header")
    (
        signature,
        _needed,
        flags,
        method,
        _time,
        _date,
        _crc,
        compressed,
        uncompressed,
        name_length,
        extra_length,
    ) = _LOCAL.unpack(source.read_at(offset, _LOCAL.size))
    if signature != _LOCAL_SIGNATURE:
        raise BackupFormatError("local_header")
    if method != zipfile.ZIP_STORED:
        raise BackupFormatError("member_method")
    if flags & _FORBIDDEN_FLAGS:
        raise BackupFormatError("member_flags")
    if extra_length:
        raise BackupFormatError("member_extra")
    if (compressed, uncompressed) != (size, size) or name_length != len(name):
        raise BackupFormatError("local_header")
    data_offset = offset + _LOCAL.size + name_length
    if data_offset + size > directory_offset:
        raise BackupFormatError("local_header")
    if source.read_at(offset + _LOCAL.size, name_length) != name.encode("ascii"):
        raise BackupFormatError("local_header")
    return MemberSpan(data_offset, size)


# ---------------------------------------------------------------------------
# The header (D2 steps 2 and 3).
# ---------------------------------------------------------------------------


def parse_header(raw: bytes) -> BackupHeader:
    """The header, bounded and parsed: ``format_newer`` for a later format,
    ``header_invalid`` for anything else that is not a v1 header; then the
    KDF envelope (``check_kdf``)."""
    if len(raw) > MAX_HEADER_BYTES:
        raise BackupFormatError("header_too_large")
    try:
        data = json.loads(raw)
    except (ValueError, RecursionError):  # nesting past the stack is not a header
        raise BackupFormatError("header_invalid") from None
    if not isinstance(data, dict):
        raise BackupFormatError("header_invalid")
    version = data.get("format_version")
    if type(version) is not int:
        raise BackupFormatError("header_invalid")
    if version > FORMAT_VERSION:
        raise BackupFormatError("format_newer")
    try:
        header = BackupHeader.model_validate(data)
    except ValidationError:
        raise BackupFormatError("header_invalid") from None
    check_kdf(header.kdf)
    return header


def _this_channel(channel: str | None) -> str:
    return channel if channel is not None else install_layout.channel()


def _member(source: ByteSource, spans: dict[str, MemberSpan], name: str) -> bytes:
    span = spans[name]
    return source.read_at(span.offset, span.size)


def _source(source: ByteSource | Path | BinaryIO) -> ByteSource:
    if isinstance(source, Path):
        return PathSource(source)
    if isinstance(source, io.IOBase):
        return HandleSource(cast("BinaryIO", source))
    return cast(ByteSource, source)


def read_backup_header(
    source: ByteSource | Path | BinaryIO, *, channel: str | None = None
) -> BackupHeader:
    """D2 steps 1–3, before the passphrase: the preflight, the header and
    its KDF envelope, and the channel pre-filter (the header's copy; a
    courtesy refusal, ``other_channel``)."""
    reader = _source(source)
    spans = preflight(reader)
    header = parse_header(_member(reader, spans, HEADER_MEMBER))
    if header.channel != _this_channel(channel):
        raise BackupFormatError("other_channel", channel=header.channel)
    return header


# ---------------------------------------------------------------------------
# The whole reader (D2 steps 1–6, the derivation excepted).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BackupFacts:
    """What a verified file holds — key-free (D4): the header, the
    authenticated manifest, the whole file's SHA-256, each member's span,
    each entry's completion date, and the ids of the rows this build can
    import (``audit.row_importable``)."""

    header: BackupHeader
    manifest: BackupManifest = field(repr=False)
    file_sha256: str
    members: dict[str, MemberSpan] = field(repr=False)
    completed: dict[str, datetime] = field(repr=False)
    importable_rows: frozenset[str] = field(repr=False)


def verify_backup(
    source: ByteSource | Path | BinaryIO,
    k_b: bytes | bytearray,
    *,
    channel: str | None = None,
) -> BackupFacts:
    """Every step of D2's reader except the derivation, with the derived key
    ``k_b`` — the writer's read-back, Open, and Restore's second pass. The
    first failure refuses by name; nothing is written."""
    reader = _source(source)
    spans = preflight(reader)
    header_raw = _member(reader, spans, HEADER_MEMBER)
    header = parse_header(header_raw)
    expected_channel = _this_channel(channel)
    if header.channel != expected_channel:
        raise BackupFormatError("other_channel", channel=header.channel)
    try:
        plain = unseal(k_b, _member(reader, spans, MANIFEST_MEMBER), manifest_aad(header_raw))
    except InvalidTag:
        raise BackupFormatError("passphrase") from None
    manifest = _parse_manifest(plain)
    if manifest.channel != expected_channel:
        raise BackupFormatError("other_channel", channel=manifest.channel)
    if len(manifest.entries) > header.max_entries or len(manifest.rows) > header.max_rows:
        raise BackupFormatError("manifest_bounds")
    digests = member_digests(manifest)
    if set(spans) != {HEADER_MEMBER, MANIFEST_MEMBER, *digests}:
        raise BackupFormatError("member_set")
    for name, digest in digests.items():
        if spans[name].size != digest.size:
            raise BackupFormatError("member_size")

    def checked(name: str) -> bytes:
        blob = _member(reader, spans, name)
        if hashlib.sha256(blob).hexdigest() != digests[name].sha256:
            raise BackupFormatError("member_hash")
        return blob

    for name in digests:
        if name == AUDIT_KEY_MEMBER or name.startswith("keys/"):
            checked(name)
    importable = _open_rows(manifest, checked, k_b)
    completed = _open_entries(manifest, checked, k_b)
    return BackupFacts(
        header=header,
        manifest=manifest,
        file_sha256=_whole_sha256(reader),
        members=spans,
        completed=completed,
        importable_rows=importable,
    )


def _parse_manifest(plain: bytes) -> BackupManifest:
    try:
        data = json.loads(plain)
        return BackupManifest.model_validate(data)
    except (ValueError, ValidationError, RecursionError):
        raise BackupFormatError("manifest_invalid") from None


def _open_rows(
    manifest: BackupManifest, checked: Callable[[str], bytes], k_b: bytes | bytearray
) -> frozenset[str]:
    """D2 step 6 for the audit record: the audit key unwraps, every row's
    bytes match their hash and authenticate under it, and each is classified
    by ``audit.row_importable``. The key is zeroed; the plaintext dropped."""
    if manifest.audit_key is None:
        return frozenset()
    try:
        audit_key = unwrap_key(k_b, checked(AUDIT_KEY_MEMBER), _AUDIT_KEY_AAD)
    except (InvalidTag, ValueError):
        raise BackupFormatError("audit_key") from None
    importable: set[str] = set()
    try:
        for session_id, row in manifest.rows.items():
            blob = checked(row_member(row.month, session_id))
            try:
                plain = unseal(audit_key, blob, _row_aad(session_id))
            except InvalidTag:
                raise BackupFormatError("row_unauthentic") from None
            if row_importable(plain, session_id, row.month):
                importable.add(session_id)
    finally:
        zero(audit_key)
    return frozenset(importable)


def _open_entries(
    manifest: BackupManifest, checked: Callable[[str], bytes], k_b: bytes | bytearray
) -> dict[str, datetime]:
    """D2 step 6 for the archive, ONE entry in memory at a time: its key
    unwraps and the entry opens (``past_sessions.entry_opens``) — which
    yields its completion date; no key and no text leave here."""
    completed: dict[str, datetime] = {}
    for session_id, entry in manifest.entries.items():
        try:
            key = unwrap_key(k_b, checked(key_member(session_id)), entry_key_aad(session_id))
        except (InvalidTag, ValueError):
            raise BackupFormatError("entry_key") from None
        try:
            files = {
                kind: checked(entry_member(session_id, kind)) for kind in entry.files.kinds()
            }
            date = entry_opens(session_id, key, files)
        finally:
            zero(key)
        if date is None:
            raise BackupFormatError("entry_does_not_open")
        completed[session_id] = date
    return completed


def _whole_sha256(source: ByteSource) -> str:
    digest = hashlib.sha256()
    size = source.size()
    offset = 0
    while offset < size:
        length = min(_READ_CHUNK, size - offset)
        digest.update(source.read_at(offset, length))
        offset += length
    return digest.hexdigest()


class BackupReader:
    """An opened, verified backup for the GUI-thread planner and restorer
    (D4): the source, the facts, and reads that check each member's size and
    SHA-256 against the in-memory manifest at that read — a difference is
    ``BackupRunError("source_changed")``. Keys are unwrapped ONE at a time
    into a ``bytearray`` the caller zeroes."""

    def __init__(self, source: ByteSource | Path | BinaryIO, facts: BackupFacts) -> None:
        self._source = _source(source)
        self._facts = facts
        self._digests = member_digests(facts.manifest)

    @property
    def facts(self) -> BackupFacts:
        return self._facts

    @property
    def manifest(self) -> BackupManifest:
        return self._facts.manifest

    def read_member(self, name: str) -> bytes:
        digest = self._digests.get(name)
        span = self._facts.members.get(name)
        if digest is None or span is None:
            raise BackupRunError("source_changed")
        try:
            blob = self._source.read_at(span.offset, span.size)
        except BackupFormatError:
            raise BackupRunError("source_changed") from None
        if len(blob) != digest.size or hashlib.sha256(blob).hexdigest() != digest.sha256:
            raise BackupRunError("source_changed")
        return blob

    def entry_files(self, session_id: str) -> dict[str, bytes]:
        entry = self.manifest.entries[session_id]
        return {
            kind: self.read_member(entry_member(session_id, kind))
            for kind in entry.files.kinds()
        }

    def unwrap_entry_key(self, session_id: str, k_b: bytes | bytearray) -> bytearray:
        try:
            return unwrap_key(
                k_b, self.read_member(key_member(session_id)), entry_key_aad(session_id)
            )
        except (InvalidTag, ValueError):
            raise BackupRunError("source_changed") from None

    def unwrap_audit_key(self, k_b: bytes | bytearray) -> bytearray | None:
        if self.manifest.audit_key is None:
            return None
        try:
            return unwrap_key(k_b, self.read_member(AUDIT_KEY_MEMBER), _AUDIT_KEY_AAD)
        except (InvalidTag, ValueError):
            raise BackupRunError("source_changed") from None


@dataclass
class OpenedBackup:
    """``open_backup``'s answer (tests): the reader and ``K_b``, which the
    caller zeroes."""

    reader: BackupReader
    key: bytearray = field(repr=False)


def open_backup(
    path: Path, passphrase: bytes | bytearray, *, channel: str | None = None
) -> OpenedBackup:
    """Derive plus verify, for tests: the header (steps 1–3), ``K_b``
    (``derive_key``), then ``verify_backup``."""
    header = read_backup_header(path, channel=channel)
    key = derive_key(passphrase, header.kdf)
    try:
        facts = verify_backup(path, key, channel=channel)
    except BaseException:
        zero(key)
        raise
    return OpenedBackup(BackupReader(path, facts), key)


# ---------------------------------------------------------------------------
# Writing a container (D6's one handle): ``zipfile`` in stored mode, ZIP64
# off — the header first, the payload, the manifest last.
# ---------------------------------------------------------------------------

_ZIP_TIME: Final = (1980, 1, 1, 0, 0, 0)


def new_header(
    *, made_at: datetime, max_entries: int, max_rows: int, kdf: KdfParams | None = None
) -> BackupHeader:
    """A new backup's header: this build's version and channel, and ``kdf``
    — the parameters and salt ``K_b`` was derived with, so the passphrase
    derives it again from the header — or, with none given, a fresh salt
    (``new_kdf_params``)."""
    return BackupHeader(
        app_version=__version__,
        channel=install_layout.channel(),
        made_at=made_at,
        kdf=kdf if kdf is not None else new_kdf_params(),
        max_entries=max_entries,
        max_rows=max_rows,
    )


def write_container(
    stream: BinaryIO,
    header_bytes: bytes,
    payload: Iterable[tuple[str, bytes]],
    manifest_plain: bytes | Callable[[], bytes],
    k_b: bytes | bytearray,
) -> None:
    """Write the ZIP into ``stream`` (positioned at 0): ``header.json``
    first, ``payload`` in order (an iterable consumed once — the writer's
    proved copy yields one entry at a time), ``manifest.enc`` (sealed under
    ``k_b``, bound to the header) last; ``manifest_plain`` may be a callable
    asked only once the payload is written. ``BackupRunError("too_large")``
    past the classic limits or ``MAX_MANIFEST_BYTES``; the stream's own
    ``OSError`` passes through."""
    if len(header_bytes) > MAX_HEADER_BYTES:
        raise BackupRunError("too_large")
    try:
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_STORED, allowZip64=False) as archive:
            _add(archive, HEADER_MEMBER, header_bytes)
            for name, blob in payload:
                _add(archive, name, blob)
            plain = manifest_plain() if callable(manifest_plain) else manifest_plain
            sealed = seal(k_b, plain, manifest_aad(header_bytes))
            if len(sealed) > MAX_MANIFEST_BYTES:
                raise BackupRunError("too_large")
            _add(archive, MANIFEST_MEMBER, sealed)
    except zipfile.LargeZipFile:
        raise BackupRunError("too_large") from None


def _add(archive: zipfile.ZipFile, name: str, blob: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=_ZIP_TIME)
    info.compress_type = zipfile.ZIP_STORED
    archive.writestr(info, blob)


# ---------------------------------------------------------------------------
# Backing up (D1, D5, D6): hop B's plan on the GUI thread, then hop C's proved
# copy, write, read-back and publish on a worker.
# ---------------------------------------------------------------------------


class BackupAuditSource(Protocol):
    """What hop B reads of the audit record (``AuditLog`` satisfies it, as
    does the Past sessions page's audit surface)."""

    def backup_snapshot(self) -> AuditSnapshot: ...

    def row_state(self, session_id: str) -> RowState: ...


class HoldsBackupKey(Protocol):
    """What ``prepare_backup`` needs of the run (D4's ``ArchiveRun``): the
    derived key ``K_b`` and the KDF parameters (with their salt) it was
    derived with, both written into it by hop A. The header carries those
    parameters, so the passphrase derives the same key from the file."""

    @property
    def backup_key(self) -> bytearray | None: ...

    @property
    def backup_kdf(self) -> KdfParams | None: ...


@dataclass(frozen=True)
class PlannedEntry:
    """One entry hop C will try to copy: its key already wrapped under
    ``K_b``, each required file's identity as hop B saw it, the label's
    SHA-256, and whether its local audit row could not be read (``newer`` or
    ``unreadable``) at the snapshot."""

    session_id: str
    wrapped_key: bytes = field(repr=False)
    files: dict[str, FileIdentity] = field(repr=False)
    label_sha256: str = field(repr=False)
    row_not_restorable: bool


@dataclass(frozen=True)
class BackupPlan:
    """Hop B's answer (D5) — key-free: the archive's root, the header (the
    planned counts as its bounds), the entries and rows to copy, the audit
    key wrapped under ``K_b``, and what the snapshot already left out."""

    archive_root: Path
    header: BackupHeader
    entries: tuple[PlannedEntry, ...]
    audit_key: bytes | None = field(repr=False)
    rows: tuple[RowDescriptor, ...]
    rows_unknown: tuple[str, ...]
    left_out: LeftOut
    planned_bytes: int


@dataclass(frozen=True)
class BackupReport:
    """What a published, verified backup holds (D6) — counts and the file's
    own name only."""

    file_name: str
    made_at: datetime
    entries: int
    rows: int
    left_out: LeftOut
    not_restorable: int
    file_sha256: str = field(repr=False)

    @property
    def holds_recording(self) -> int:
        """Sessions left out ONLY because their recording key is live (D12)."""
        return self.left_out.entries.get("holds_recording", 0)

    @property
    def nothing_left_out(self) -> bool:
        """Flow 1's middle sentence: no eligible session and no audit row was
        left out, and nothing is ``not_restorable``."""
        others = sum(
            count for reason, count in self.left_out.entries.items()
            if reason != "holds_recording"
        )
        return others == 0 and self.left_out.rows == 0 and self.not_restorable == 0


# Per member, generously: its local and directory records, its name twice
# and its line in the manifest.
_MEMBER_OVERHEAD: Final = 512
_MAX_NAME_TRIES: Final = 1000
_NOT_RESTORABLE_ROWS: Final = frozenset({"newer", "unreadable"})


def prepare_backup(
    store: PastSessionStore,
    audit: BackupAuditSource,
    run: HoldsBackupKey,
    *,
    made_at: datetime | None = None,
) -> BackupPlan:
    """Hop B (D5), GUI thread: the archive's snapshot (an archive that
    cannot be listed refuses, ``archive_unreadable``) and the audit store's
    (``AuditUnavailable`` refuses, ``audit_unavailable``); each entry key and
    the audit key wrapped under ``K_b`` at once and the plain bytes zeroed on
    every path; each entry's local row read (``newer`` / ``unreadable``
    marks it ``not_restorable`` should it be copied). Refused before any file
    exists: ``nothing_to_back_up`` (no committed entry and no audit row at
    all) and ``too_large`` (the planned members over 65 535 or the planned
    bytes over ``MAX_BACKUP_BYTES``)."""
    k_b = run.backup_key
    kdf = run.backup_kdf
    if k_b is None or kdf is None:
        raise BackupRunError("unexpected")
    try:
        archive = store.backup_snapshot()
    except PastSessionError:
        raise BackupRunError("archive_unreadable") from None
    audit_snapshot: AuditSnapshot | None = None
    try:
        try:
            audit_snapshot = audit.backup_snapshot()
        except AuditUnavailable:
            raise BackupRunError("audit_unavailable") from None
        entries = tuple(
            PlannedEntry(
                entry.session_id,
                seal(k_b, entry.key, entry_key_aad(entry.session_id)),
                dict(entry.files),
                entry.label_sha256,
                audit.row_state(entry.session_id) in _NOT_RESTORABLE_ROWS,
            )
            for entry in archive.entries
        )
        audit_key = (
            seal(k_b, audit_snapshot.key, _AUDIT_KEY_AAD)
            if audit_snapshot.key is not None
            else None
        )
    finally:
        for entry in archive.entries:
            zero(entry.key)
        if audit_snapshot is not None:
            zero(audit_snapshot.key)
    rows = audit_snapshot.rows
    unknown = audit_snapshot.unknown_ids
    if not archive.entries and not archive.left_out and not rows and not unknown:
        raise BackupRunError("nothing_to_back_up")
    members = 2 + (audit_key is not None) + len(rows)
    planned = MAX_HEADER_BYTES + (WRAPPED_KEY_BYTES if audit_key is not None else 0)
    for planned_entry in entries:
        # D2's per-file bounds, before any file is created or read in full
        # (round 25 PR-LOW-2501): ``EntryFiles`` would refuse it only after
        # the copy.
        if any(f.size > _file_cap(kind) for kind, f in planned_entry.files.items()):
            raise BackupRunError("too_large")
        members += 1 + len(planned_entry.files)
        planned += WRAPPED_KEY_BYTES + sum(f.size for f in planned_entry.files.values())
    planned += sum(row.size for row in rows) + members * _MEMBER_OVERHEAD
    if members > MAX_MEMBERS or planned > MAX_BACKUP_BYTES:
        raise BackupRunError("too_large")
    when = made_at if made_at is not None else datetime.now(UTC)
    return BackupPlan(
        archive_root=store.root,
        header=new_header(
            made_at=when, max_entries=len(entries), max_rows=len(rows), kdf=kdf
        ),
        entries=entries,
        audit_key=audit_key,
        rows=rows,
        rows_unknown=unknown,
        left_out=LeftOut(entries=dict(archive.left_out), rows=len(unknown)),
        planned_bytes=planned,
    )


def _file_cap(kind: str) -> int:
    """D2's bound for one entry file of ``kind`` (``EntryFiles._bounded``'s
    rule), read at the call."""
    return MAX_LABEL_FILE_BYTES if kind == "label" else MAX_ENTRY_FILE_BYTES


def _digest(blob: bytes) -> Digest:
    return Digest(size=len(blob), sha256=hashlib.sha256(blob).hexdigest())


class _ProvedCopy:
    """Hop C's copy (D5), on the worker, calling no store or audit method:
    ONE entry in memory at a time — its folder not a link, its recording key
    still ``absent`` or ``zeroed``, each required file re-opened ONCE and
    found with the snapshot's identity, the label's hash unchanged, then the
    open check (``past_sessions.entry_opens``) under its key, zeroed after.
    A difference leaves the entry out ``changed``; an open-check failure
    ``damaged``. Rows: an ordinary single-link file of the descriptor's
    size that authenticates under the audit key and is importable, else
    left out and listed unknown. ``payload`` yields only what passed;
    ``manifest`` is asked after it."""

    def __init__(self, plan: BackupPlan, k_b: bytes | bytearray) -> None:
        self._plan = plan
        self._k_b = k_b
        self.entries: dict[str, ManifestEntry] = {}
        self.rows: dict[str, ManifestRow] = {}
        self.rows_unknown: list[str] = list(plan.rows_unknown)
        self._left_entries: dict[LeftOutReason, int] = dict(plan.left_out.entries)
        self._left_rows = plan.left_out.rows
        self._audit_key: Digest | None = None
        self.not_restorable = 0

    def left_out(self) -> LeftOut:
        entries = {reason: count for reason, count in self._left_entries.items() if count}
        return LeftOut(entries=entries, rows=self._left_rows)

    def payload(self) -> Generator[tuple[str, bytes], None, None]:
        """The members, one entry in memory at a time. The caller CLOSES it
        on every exit (``write_backup_file``): a write that fails while the
        rows are being copied leaves it suspended with the plain audit key,
        which only its close zeroes."""
        if self._plan.audit_key is not None:
            self._audit_key = _digest(self._plan.audit_key)
            yield AUDIT_KEY_MEMBER, self._plan.audit_key
        for planned in self._plan.entries:
            proved = self._prove_entry(planned)
            if isinstance(proved, str):
                self._left_entries[proved] = self._left_entries.get(proved, 0) + 1
                continue
            session_id = planned.session_id
            yield key_member(session_id), planned.wrapped_key
            for kind, blob in proved.items():
                yield entry_member(session_id, kind), blob
            self.entries[session_id] = ManifestEntry(
                key=_digest(planned.wrapped_key),
                files=EntryFiles(**{kind: _digest(blob) for kind, blob in proved.items()}),
            )
        yield from self._copy_rows()

    def _prove_entry(self, planned: PlannedEntry) -> dict[str, bytes] | LeftOutReason:
        folder = self._plan.archive_root / planned.session_id
        if link_state(folder) is not False:
            return "changed"
        if _audio_key_state(folder / AUDIO_KEY_FILENAME) not in ("absent", "zeroed"):
            return "changed"
        files: dict[str, bytes] = {}
        for kind, identity in planned.files.items():
            looked = inspect_entry_file(
                folder / ENTRY_FILE_KINDS[kind], read_cap=min(identity.size, _file_cap(kind))
            )
            if not isinstance(looked, tuple) or looked[0] != identity:
                return "changed"
            files[kind] = looked[1]
        if hashlib.sha256(files.get("label", b"")).hexdigest() != planned.label_sha256:
            return "changed"
        try:
            key = unwrap_key(self._k_b, planned.wrapped_key, entry_key_aad(planned.session_id))
        except (InvalidTag, ValueError):
            return "damaged"
        try:
            opened = entry_opens(planned.session_id, key, files)
        finally:
            zero(key)
        return files if opened is not None else "damaged"

    def _copy_rows(self) -> Generator[tuple[str, bytes], None, None]:
        if not self._plan.rows:
            return
        if self._plan.audit_key is None:  # rows need the key (the snapshot's own rule)
            self._row_failed(*(row.session_id for row in self._plan.rows))
            return
        audit_key = unwrap_key(self._k_b, self._plan.audit_key, _AUDIT_KEY_AAD)
        try:
            for row in self._plan.rows:
                blob = self._prove_row(row, audit_key)
                if blob is None:
                    self._row_failed(row.session_id)
                    continue
                yield row_member(row.month, row.session_id), blob
                digest = _digest(blob)
                self.rows[row.session_id] = ManifestRow(
                    month=row.month, size=digest.size, sha256=digest.sha256
                )
        finally:
            zero(audit_key)

    def _row_failed(self, *session_ids: str) -> None:
        self.rows_unknown.extend(session_ids)
        self._left_rows += len(session_ids)

    @staticmethod
    def _prove_row(row: RowDescriptor, audit_key: bytearray) -> bytes | None:
        looked = inspect_entry_file(row.path, read_cap=MAX_ROW_FILE_BYTES)
        if not isinstance(looked, tuple) or looked[0].size != row.size:
            return None
        blob = looked[1]
        try:
            plain = unseal(audit_key, blob, _row_aad(row.session_id))
        except (InvalidTag, ValueError):
            return None
        return blob if row_importable(plain, row.session_id, row.month) else None

    def manifest(self) -> bytes:
        """The manifest, once the payload is written (D2); with no entry and
        no row written, ``nothing_could_be_read`` and nothing is published."""
        if not self.entries and not self.rows:
            raise BackupRunError("nothing_could_be_read", left_out=self.left_out())
        unknown = set(self.rows_unknown)
        self.not_restorable = sum(
            1
            for planned in self._plan.entries
            if planned.session_id in self.entries
            and (planned.row_not_restorable or planned.session_id in unknown)
        )
        header = self._plan.header
        return BackupManifest(
            channel=header.channel,
            app_version=header.app_version,
            made_at=header.made_at,
            entries=self.entries,
            audit_key=self._audit_key,
            rows=self.rows,
            rows_unknown=tuple(self.rows_unknown),
            left_out=self.left_out(),
            not_restorable=self.not_restorable,
        ).to_bytes()


def write_backup_file(
    plan: BackupPlan,
    k_b: bytes | bytearray,
    destination: Path,
    *,
    check_location: Callable[[Path], bool],
) -> BackupReport:
    """Hop C (D5, D6), on a worker: the destination FOLDER checked again
    (``check_location`` answering True only for an admitted folder; anything
    else, or a raise, is ``destination_refused`` with nothing written); the
    app's own name — ``ClinikoScribe-backup-<date>[-n]`` — the first for
    which neither ``.csbk`` nor ``.csbk.part`` exists, made by ONE exclusive
    create; the proved copy written through that one handle, flushed,
    fsynced and verified by reading back through the SAME handle
    (``verify_backup``); the handle closed and the file published by a
    rename that never replaces; the published file read once more and its
    SHA-256 compared (``publish_unverified`` otherwise, the file left
    alone). On any failure before the rename the handle is closed FIRST and
    the ``.part`` removed only through the identity-checked ``_remove_part``;
    ``part_may_remain`` unless that removal confirmed this run's own file
    gone with the folder still listable."""
    try:
        admitted = check_location(destination) is True
    except Exception:  # noqa: BLE001 - a destination that cannot be checked is refused
        admitted = False
    if not admitted:
        raise BackupRunError("destination_refused")
    day = plan.header.made_at.astimezone().strftime("%Y-%m-%d")
    stems = [_stem(day, n) for n in range(1, _MAX_NAME_TRIES + 1)]
    descriptor, index, identity = _create_part(destination, stems)
    part = destination / f"{stems[index]}{PART_SUFFIX}"
    owned = True  # the descriptor is this frame's until _write_and_verify takes it
    payload: Generator[tuple[str, bytes], None, None] | None = None
    try:
        copy = _ProvedCopy(plan, k_b)
        payload = copy.payload()
        owned = False
        facts = _write_and_verify(descriptor, plan, k_b, copy, payload)
        final = _publish(part, destination, stems, index)
    except Exception as exc:  # noqa: BLE001 - named by code; the part removed by identity
        if owned:  # closed BEFORE the removal, which an open handle would block
            owned = False
            with contextlib.suppress(OSError):
                os.close(descriptor)
        error = _run_error(exc)
        removed = _remove_part(part, identity) and _listable(destination)
        raise BackupRunError(
            error.code,
            part_may_remain=not removed,
            left_out=error.left_out,
            error_type=error.error_type,
        ) from None
    finally:
        if owned:
            with contextlib.suppress(OSError):
                os.close(descriptor)
        if payload is not None:
            payload.close()  # zeroes the audit key a copy suspended mid-rows still holds
    if _sha256_of(final) != facts.file_sha256:
        raise BackupRunError("publish_unverified")
    return BackupReport(
        file_name=final.name,
        made_at=plan.header.made_at,
        entries=len(copy.entries),
        rows=len(copy.rows),
        left_out=copy.left_out(),
        not_restorable=copy.not_restorable,
        file_sha256=facts.file_sha256,
    )


def _stem(day: str, n: int) -> str:
    suffix = "" if n == 1 else f"-{n}"
    return f"{BACKUP_FILENAME_PREFIX}{day}{suffix}"


def _taken(path: Path) -> bool:
    """Something is at ``path`` — or it cannot be told (never touched)."""
    try:
        os.lstat(path)
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def _create_part(destination: Path, stems: list[str]) -> tuple[int, int, ExportIdentity]:
    """D6's ONE exclusive create, read-write: the first stem whose
    ``.csbk`` and ``.csbk.part`` are both absent; a create that finds the
    name taken moves on. Nothing existing is ever touched.
    ``write_failed`` when nothing can be created (nothing was)."""
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    for index, stem in enumerate(stems):
        if _taken(destination / f"{stem}{BACKUP_SUFFIX}") or _taken(
            destination / f"{stem}{PART_SUFFIX}"
        ):
            continue
        try:
            descriptor = os.open(destination / f"{stem}{PART_SUFFIX}", flags, 0o600)
        except FileExistsError:
            continue
        except OSError:
            raise BackupRunError("write_failed") from None
        try:
            status = os.fstat(descriptor)
            identity = ExportIdentity(file_index=status.st_ino, device=status.st_dev)
        except BaseException as exc:
            os.close(descriptor)
            if isinstance(exc, Exception):
                # No identity: the file is this run's but cannot be removed
                # safely, so it is left and said to remain (round 23
                # PR-LOW-2304).
                raise BackupRunError("write_failed", part_may_remain=True) from None
            raise
        return descriptor, index, identity
    raise BackupRunError("write_failed")


def _write_and_verify(
    descriptor: int,
    plan: BackupPlan,
    k_b: bytes | bytearray,
    copy: _ProvedCopy,
    payload: Iterable[tuple[str, bytes]],
) -> BackupFacts:
    """Write the container through the ONE handle, flush and fsync it, and
    verify it by reading back through that same handle; the handle is
    closed on every path before this returns (it owns the descriptor from
    the call on, a failed ``fdopen`` included)."""
    try:
        stream = os.fdopen(descriptor, "w+b")
    except BaseException:
        os.close(descriptor)
        raise
    with stream:
        write_container(stream, plan.header.to_bytes(), payload, copy.manifest, k_b)
        stream.flush()
        os.fsync(stream.fileno())
        if stream.seek(0, os.SEEK_END) > MAX_BACKUP_BYTES:
            raise BackupRunError("too_large")
        return verify_backup(HandleSource(stream), k_b)


def _publish(part: Path, destination: Path, stems: list[str], index: int) -> Path:
    """The rename to the final name (D6): this run's own stem, else the next
    whose ``.csbk`` and ``.csbk.part`` are absent; a rename never replaces
    (Windows refuses an existing name)."""
    for position in range(index, len(stems)):
        stem = stems[position]
        final = destination / f"{stem}{BACKUP_SUFFIX}"
        if position != index and _taken(destination / f"{stem}{PART_SUFFIX}"):
            continue
        if _taken(final):
            continue
        try:
            os.rename(part, final)
        except FileExistsError:
            continue
        return final
    raise BackupRunError("write_failed")


def _run_error(exc: Exception) -> BackupRunError:
    if isinstance(exc, BackupRunError):
        return exc
    if isinstance(exc, BackupFormatError):
        return BackupRunError("too_large" if exc.code == "too_large" else "write_failed")
    if isinstance(exc, OSError):
        return BackupRunError("write_failed")
    # Peer round 30 PR-LOW-301 (D4): the type name only, for the one log line.
    return BackupRunError("unexpected", error_type=exception_type_name(type(exc)))


def _listable(folder: Path) -> bool:
    try:
        with os.scandir(folder):
            pass
    except OSError:
        return False
    return True


def _sha256_of(path: Path) -> str | None:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(_READ_CHUNK), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()
