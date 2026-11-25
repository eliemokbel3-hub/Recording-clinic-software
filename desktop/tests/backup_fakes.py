"""Shared fakes for the Past-sessions backup tests (past-sessions-backup plan
Tasks 1.3 and 1.5; D15, C9): an archive and an audit store under the test's
own folder with FAKE key seams (never the host's DPAPI), a builder of a
backup file from them with every part open to tampering, and a hand-rolled
ZIP for the preflight's refusals. Synthetic content only."""

from __future__ import annotations

import io
import json
import struct
import uuid
import zlib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from scribe_desktop import past_sessions_backup as backup
from scribe_desktop.audit import AuditLog
from scribe_desktop.encounter import unlinked_consent
from scribe_desktop.note import GeneratedNote, digest_bytes
from scribe_desktop.past_sessions import KeepLabel, PastSessionStore
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_mode import SessionMode
from scribe_desktop.session_store import (
    KEY_FILENAME,
    ArchiveSource,
    GeneratedRecord,
    KeyCustodyError,
)
from scribe_desktop.transcription import TranscriptDocument

NOW = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
PASSPHRASE = b"correct horse battery staple, twenty+"
LINKED = KeepLabel("Jane Citizen", "linked", "0123456789abcdef", shadow=False)
ENTRY_FAKE = b"FAKE-ENTRY-KEY:"
AUDIT_FAKE = b"FAKE-AUDIT-KEY:"


def sid() -> str:
    return uuid.uuid4().hex


# --- the archive and the audit store, fake-keyed -----------------------------


def fake_entry_wrap(crypto: SessionCrypto, directory: Path) -> None:
    (directory / KEY_FILENAME).write_bytes(ENTRY_FAKE + crypto.export_key())


def fake_entry_unwrap(directory: Path) -> SessionCrypto:
    blob = (directory / KEY_FILENAME).read_bytes()
    if not blob.startswith(ENTRY_FAKE):
        raise KeyCustodyError("not an entry key")
    return SessionCrypto.from_key(blob[len(ENTRY_FAKE) :])


def fake_audit_wrap(crypto: SessionCrypto, root: Path) -> None:
    (root / KEY_FILENAME).write_bytes(AUDIT_FAKE + crypto.export_key())


def fake_audit_unwrap(root: Path) -> SessionCrypto:
    blob = (root / KEY_FILENAME).read_bytes()
    if not blob.startswith(AUDIT_FAKE):
        raise KeyCustodyError("not this store's key")
    return SessionCrypto.from_key(blob[len(AUDIT_FAKE) :])


def archive(root: Path, **overrides: Any) -> PastSessionStore:
    kwargs: dict[str, Any] = {
        "wrap_key": fake_entry_wrap,
        "unwrap_key": fake_entry_unwrap,
        "clock": lambda: NOW,
    }
    kwargs.update(overrides)
    return PastSessionStore(root / "past_sessions", **kwargs)


def audit_log(root: Path, **overrides: Any) -> AuditLog:
    kwargs: dict[str, Any] = {
        "wrap_key": fake_audit_wrap,
        "unwrap_key": fake_audit_unwrap,
        "clock": lambda: NOW,
        "local_zone": UTC,
    }
    kwargs.update(overrides)
    return AuditLog(root / "audit", **kwargs)


def transcript(session_id: str) -> bytes:
    return TranscriptDocument(
        session_id=session_id,
        created_at=NOW,
        model_name="small",
        sample_rate=16_000,
        transcript_segments=(),
    ).to_bytes()


def source(*, note: bool = True, generated: bool = True) -> ArchiveSource:
    session_id = sid()
    text = transcript(session_id)
    return ArchiveSource(
        session_id=session_id,
        created_at=(NOW - timedelta(minutes=20)).timestamp(),
        transcript_plain=text,
        note_plain=(
            GeneratedNote(
                session_id=session_id,
                created_at=NOW,
                template_profile_id="clinic-a",
                provider_name="extractive-v1",
                transcript_digest=digest_bytes(text),
                config_digest=digest_bytes(b"config"),
            ).to_bytes()
            if note
            else None
        ),
        generated_plain=(
            GeneratedRecord(
                session_id=session_id,
                created_at=NOW,
                provider_name="extractive-v1",
                style="verbatim",
                generated_text="Synthetic: a sore left knee for two weeks.",
            ).to_bytes()
            if generated
            else None
        ),
    )


def published(store: PastSessionStore, *, note: bool = True, generated: bool = True) -> str:
    entry = source(note=note, generated=generated)
    store.write_entry(entry, LINKED)
    assert store.commit(entry.session_id)
    return entry.session_id


def row(log: AuditLog, *, started_at: datetime = NOW, session_id: str | None = None) -> str:
    session_id = session_id if session_id is not None else sid()
    log.begin(
        session_id,
        consent=unlinked_consent(NOW),
        context=None,
        user_id=None,
        started_at=started_at,
        mode=SessionMode.NORMAL,
        app_version="0.5.0",
        development_consent_version=None,
    )
    return session_id


def entry_key(store: PastSessionStore, session_id: str) -> bytes:
    return (store.root / session_id / KEY_FILENAME).read_bytes()[len(ENTRY_FAKE) :]


def entry_files(store: PastSessionStore, session_id: str) -> dict[str, bytes]:
    folder = store.root / session_id
    return {
        kind: (folder / f"{kind}.enc").read_bytes()
        for kind in ("label", "transcript", "note", "generated")
        if (folder / f"{kind}.enc").exists()
    }


# --- a backup file, every part open to tampering ------------------------------


@dataclass
class Built:
    """One backup in memory: its bytes, ``K_b``, the passphrase, and what
    went in (the plaintext keys and files are the test's to compare)."""

    blob: bytes
    key: bytearray
    header: backup.BackupHeader
    manifest: dict[str, Any]
    members: list[tuple[str, bytes]]
    entry_keys: dict[str, bytes] = field(default_factory=dict)
    entry_files: dict[str, dict[str, bytes]] = field(default_factory=dict)
    audit_key: bytes | None = None
    rows: dict[str, tuple[str, bytes]] = field(default_factory=dict)

    def write(self, path: Path) -> Path:
        path.write_bytes(self.blob)
        return path


def digest(blob: bytes) -> dict[str, Any]:
    import hashlib

    return {"size": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}


def build(
    root: Path,
    *,
    entries: int = 1,
    rows: int = 1,
    passphrase: bytes = PASSPHRASE,
    header: Callable[[dict[str, Any]], None] | None = None,
    manifest: Callable[[dict[str, Any]], None] | None = None,
    members: Callable[[list[tuple[str, bytes]]], None] | None = None,
    store: PastSessionStore | None = None,
    log: AuditLog | None = None,
) -> Built:
    """A backup of ``entries`` fresh entries and ``rows`` fresh audit rows
    (or of ``store`` / ``log`` as they are), assembled as the writer does;
    each callback may change the header's or the manifest's document, or the
    payload (changed before the manifest's callback runs), before the file
    is written."""
    root.mkdir(parents=True, exist_ok=True)
    if store is None:
        store = archive(root)
        for _ in range(entries):
            published(store)
    if log is None:
        log = audit_log(root)
        for _ in range(rows):
            row(log)
    listed = sorted(listing.session_id for listing in store.list_entries())
    snapshot = log.backup_snapshot()
    header_model = backup.new_header(
        made_at=NOW, max_entries=len(listed), max_rows=len(snapshot.rows)
    )
    header_doc = json.loads(header_model.to_bytes())
    if header is not None:
        header(header_doc)
    header_bytes = json.dumps(header_doc).encode("utf-8")
    key = backup.derive_key(passphrase, header_model.kdf)
    built = Built(b"", key, header_model, {}, [])
    payload: list[tuple[str, bytes]] = []
    manifest_doc: dict[str, Any] = {
        "channel": header_model.channel,
        "app_version": header_model.app_version,
        "made_at": header_model.made_at.isoformat(),
        "entries": {},
        "rows": {},
        "rows_unknown": [],
        "left_out": {"entries": {}, "rows": 0},
        "not_restorable": 0,
    }
    if snapshot.key is not None:
        built.audit_key = bytes(snapshot.key)
        wrapped = backup.seal(key, snapshot.key, b"csbk-audit-key")
        payload.append((backup.AUDIT_KEY_MEMBER, wrapped))
        manifest_doc["audit_key"] = digest(wrapped)
    for session_id in listed:
        plain_key = entry_key(store, session_id)
        files = entry_files(store, session_id)
        built.entry_keys[session_id] = plain_key
        built.entry_files[session_id] = files
        wrapped = backup.seal(key, plain_key, backup.entry_key_aad(session_id))
        payload.append((backup.key_member(session_id), wrapped))
        for kind, blob in files.items():
            payload.append((backup.entry_member(session_id, kind), blob))
        manifest_doc["entries"][session_id] = {
            "key": digest(wrapped),
            "files": {kind: digest(blob) for kind, blob in files.items()},
        }
    for described in snapshot.rows:
        blob = described.path.read_bytes()
        built.rows[described.session_id] = (described.month, blob)
        payload.append((backup.row_member(described.month, described.session_id), blob))
        manifest_doc["rows"][described.session_id] = {"month": described.month, **digest(blob)}
    # The payload first: a manifest callback may hash what it changed.
    if members is not None:
        members(payload)
    if manifest is not None:
        manifest(manifest_doc)
    stream = io.BytesIO()
    backup.write_container(
        stream, header_bytes, payload, json.dumps(manifest_doc).encode("utf-8"), key
    )
    built.blob = stream.getvalue()
    built.manifest = manifest_doc
    built.members = payload
    return built


# --- a hand-rolled ZIP for the preflight's refusals ---------------------------


def raw_zip(
    members: list[tuple[str, bytes]],
    *,
    method: dict[str, int] | None = None,
    flags: dict[str, int] | None = None,
    local_extra: dict[str, bytes] | None = None,
    central_extra: dict[str, bytes] | None = None,
    member_comment: dict[str, bytes] | None = None,
    local_name: dict[str, bytes] | None = None,
    local_sizes: dict[str, tuple[int, int]] | None = None,
    central_sizes: dict[str, tuple[int, int]] | None = None,
    raw_names: dict[str, bytes] | None = None,
    declared_count: int | None = None,
    comment: bytes = b"",
    zip64_locator: bool = False,
) -> bytes:
    """A ZIP built record by record, each field open to change — what
    ``zipfile`` would refuse to write."""
    out = bytearray()
    central = bytearray()
    for name, data in members:
        raw = (raw_names or {}).get(name, name.encode("ascii"))
        crc = zlib.crc32(data)
        m = (method or {}).get(name, 0)
        f = (flags or {}).get(name, 0)
        offset = len(out)
        l_name = (local_name or {}).get(name, raw)
        l_extra = (local_extra or {}).get(name, b"")
        l_comp, l_uncomp = (local_sizes or {}).get(name, (len(data), len(data)))
        out += struct.pack(
            "<IHHHHHIIIHH", 0x04034B50, 20, f, m, 0, 0x21, crc, l_comp, l_uncomp,
            len(l_name), len(l_extra),
        )
        out += l_name + l_extra + data
        c_extra = (central_extra or {}).get(name, b"")
        c_comment = (member_comment or {}).get(name, b"")
        c_comp, c_uncomp = (central_sizes or {}).get(name, (len(data), len(data)))
        central += struct.pack(
            "<IHHHHHHIIIHHHHHII", 0x02014B50, 20, 20, f, m, 0, 0x21, crc, c_comp, c_uncomp,
            len(raw), len(c_extra), len(c_comment), 0, 0, 0, offset,
        )
        central += raw + c_extra + c_comment
    directory_offset = len(out)
    out += central
    if zip64_locator:
        out += struct.pack("<IIQI", 0x07064B50, 0, len(out), 1)
    count = len(members) if declared_count is None else declared_count
    out += struct.pack(
        "<IHHHHIIH", 0x06054B50, 0, 0, count, count, len(central), directory_offset, len(comment)
    )
    out += comment
    return bytes(out)


def minimal_header() -> bytes:
    """A valid v1 header under the test floor's KDF (a fast derivation)."""
    return backup.new_header(made_at=NOW, max_entries=0, max_rows=0).to_bytes()
