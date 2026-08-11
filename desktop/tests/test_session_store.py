"""Step 2 validation batteries: encrypted chunk store, DPAPI key custody,
Complete/Discard ordering, and the 24 h expiry sweep."""

from __future__ import annotations

import errno
import os
import struct
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from scribe_desktop import session_store
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import (
    CLOCK_SKEW_TOLERANCE,
    KEY_FILENAME,
    MAX_RECORD_BYTES,
    NOTE_FILENAME,
    RECOVERY_WINDOW,
    KeyCustodyError,
    NoteWriteRefusedError,
    SessionChunkStore,
    StoreCorruptError,
    StoreLimitError,
    StoreStateError,
    StoreWriteError,
    complete_session,
    discard_session,
    earliest_trusted_timestamp,
    iter_chunks,
    read_note,
    read_store_header,
    resolve_key_path,
    sweep_sessions,
    unwrap_key_from_file,
    wrap_key_to_file,
    write_note,
)

if TYPE_CHECKING:
    from scribe_desktop.note import GeneratedNote, GeneratedSection, NoteWarning
    from scribe_desktop.note_config import NoteConfig

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-only")

_LEN = struct.Struct("<I")
_HEADER_SIZE = struct.Struct("<4sB32sdIHH").size


def _sid() -> str:
    return uuid.uuid4().hex


def _make_session_dir(tmp_path: Path, dummy_key: bool = True) -> tuple[Path, str]:
    sid = _sid()
    session_dir = tmp_path / sid
    session_dir.mkdir()
    if dummy_key:
        # Store-format tests do not need real DPAPI; a placeholder satisfies
        # the key-before-first-chunk ordering check.
        (session_dir / KEY_FILENAME).write_bytes(b"\0" * 64)
    return session_dir, sid


def _build_store(
    tmp_path: Path, chunks: list[bytes], *, finish: bool = True
) -> tuple[Path, SessionCrypto, str]:
    session_dir, sid = _make_session_dir(tmp_path)
    crypto = SessionCrypto()
    path = session_dir / "audio.enc"
    store = SessionChunkStore.create(path, crypto, sid)
    for chunk in chunks:
        store.append_chunk(chunk)
    if finish:
        store.finish()
    else:
        store.close()
    return path, crypto, sid


def _raw_records(path: Path) -> list[tuple[int, int, bytes]]:
    """Return (offset, length, payload) for each complete record."""
    data = path.read_bytes()
    records = []
    offset = _HEADER_SIZE
    while offset + _LEN.size <= len(data):
        (length,) = _LEN.unpack_from(data, offset)
        payload = data[offset + _LEN.size : offset + _LEN.size + length]
        if len(payload) < length:
            break
        records.append((offset, length, payload))
        offset += _LEN.size + length
    return records


# ---------------------------------------------------------------- chunk store


class TestChunkStore:
    def test_append_decrypt_stream_round_trip(self, tmp_path: Path) -> None:
        chunks = [os.urandom(320) for _ in range(5)]
        path, crypto, sid = _build_store(tmp_path, chunks)
        assert list(iter_chunks(path, crypto, require_footer=True)) == chunks
        header = read_store_header(path)
        assert header.session_id == sid
        assert header.sample_rate == 16_000

    def test_wrong_key_fails(self, tmp_path: Path) -> None:
        path, _crypto, _sid = _build_store(tmp_path, [b"audio"])
        with pytest.raises(StoreCorruptError):
            list(iter_chunks(path, SessionCrypto()))

    def test_aad_reorder_tamper_detected(self, tmp_path: Path) -> None:
        # THE one reorder-tamper test (plan: no dedicated battery): swapping
        # two equal-length records must trip the chunk-index AAD.
        path, crypto, _sid = _build_store(tmp_path, [b"A" * 100, b"B" * 100])
        records = _raw_records(path)
        data = bytearray(path.read_bytes())
        (off0, len0, pay0), (off1, len1, pay1) = records[0], records[1]
        assert len0 == len1
        data[off0 + _LEN.size : off0 + _LEN.size + len0] = pay1
        data[off1 + _LEN.size : off1 + _LEN.size + len1] = pay0
        path.write_bytes(bytes(data))
        with pytest.raises(StoreCorruptError, match="authentication"):
            list(iter_chunks(path, crypto))

    def test_truncated_tail_tolerated(self, tmp_path: Path) -> None:
        # Crash-sim: a partial final record is expected behaviour — complete
        # records still decrypt, iteration ends cleanly without footer.
        chunks = [b"one" * 50, b"two" * 50, b"three" * 50]
        path, crypto, _sid = _build_store(tmp_path, chunks, finish=False)
        last_off, last_len, _ = _raw_records(path)[-1]
        with path.open("r+b") as fh:
            fh.truncate(last_off + _LEN.size + last_len // 2)
        assert list(iter_chunks(path, crypto)) == chunks[:2]

    def test_footer_detects_post_finish_truncation(self, tmp_path: Path) -> None:
        path, crypto, _sid = _build_store(tmp_path, [b"x" * 64, b"y" * 64])
        footer_off, _, _ = _raw_records(path)[-1]
        with path.open("r+b") as fh:
            fh.truncate(footer_off)  # chop the footer off a Finished store
        with pytest.raises(StoreCorruptError, match="footer"):
            list(iter_chunks(path, crypto, require_footer=True))

    def test_footer_count_mismatch_detected(self, tmp_path: Path) -> None:
        # Remove a whole middle record but keep the footer: the next record's
        # AAD index no longer matches.
        path, crypto, _sid = _build_store(tmp_path, [b"a" * 32, b"b" * 32, b"c" * 32])
        records = _raw_records(path)
        data = path.read_bytes()
        off1 = records[1][0]
        off2 = records[2][0]
        path.write_bytes(data[:off1] + data[off2:])
        with pytest.raises(StoreCorruptError):
            list(iter_chunks(path, crypto, require_footer=True))

    def test_bounded_record_length_rejected_without_allocation(self, tmp_path: Path) -> None:
        path, crypto, _sid = _build_store(tmp_path, [b"z" * 16])
        off0 = _raw_records(path)[0][0]
        data = bytearray(path.read_bytes())
        _LEN.pack_into(data, off0, MAX_RECORD_BYTES + 1)  # declared ~1 MiB+ lie
        path.write_bytes(bytes(data))
        with pytest.raises(StoreCorruptError, match="out of bounds"):
            list(iter_chunks(path, crypto))

    def test_no_nonce_repeats_across_restart_append(self, tmp_path: Path) -> None:
        session_dir, sid = _make_session_dir(tmp_path)
        crypto = SessionCrypto()
        path = session_dir / "audio.enc"
        store = SessionChunkStore.create(path, crypto, sid)
        for _ in range(10):
            store.append_chunk(os.urandom(64))
        store.close()  # simulated crash: no finish
        store = SessionChunkStore.open_for_append(path, crypto)
        assert store.next_index == 10
        for _ in range(10):
            store.append_chunk(os.urandom(64))
        store.finish()
        nonces = [payload[1:13] for _, _, payload in _raw_records(path)]
        assert len(nonces) == 21  # 20 chunks + footer
        assert len(set(nonces)) == 21, "nonce repeated across restart-append"

    def test_restart_append_truncates_partial_tail_and_resumes(self, tmp_path: Path) -> None:
        session_dir, sid = _make_session_dir(tmp_path)
        crypto = SessionCrypto()
        path = session_dir / "audio.enc"
        store = SessionChunkStore.create(path, crypto, sid)
        store.append_chunk(b"keep-me" * 10)
        store.close()
        with path.open("ab") as fh:  # crash mid-write: garbage partial record
            fh.write(_LEN.pack(500) + b"\x01partial")
        store = SessionChunkStore.open_for_append(path, crypto)
        assert store.next_index == 1
        store.append_chunk(b"after-crash" * 5)
        store.finish()
        assert list(iter_chunks(path, crypto, require_footer=True)) == [
            b"keep-me" * 10,
            b"after-crash" * 5,
        ]

    def test_open_for_append_missing_file_maps_to_store_write_error(self, tmp_path: Path) -> None:
        # PR-LOW-001: recovery-open failures follow the store error contract.
        with pytest.raises(StoreWriteError):
            SessionChunkStore.open_for_append(tmp_path / "absent.enc", SessionCrypto())

    def test_open_for_append_refuses_finished_store(self, tmp_path: Path) -> None:
        path, crypto, _sid = _build_store(tmp_path, [b"done"])
        with pytest.raises(StoreStateError, match="finished"):
            SessionChunkStore.open_for_append(path, crypto)

    def test_record_count_bound_fails_safe(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(session_store, "MAX_RECORDS", 2)
        session_dir, sid = _make_session_dir(tmp_path)
        crypto = SessionCrypto()
        store = SessionChunkStore.create(session_dir / "audio.enc", crypto, sid)
        store.append_chunk(b"1")
        store.append_chunk(b"2")
        with pytest.raises(StoreLimitError):
            store.append_chunk(b"3")
        store.close()

    def test_create_requires_key_custody_first(self, tmp_path: Path) -> None:
        # Binding durability ordering: key.dpapi BEFORE the first chunk.
        session_dir, sid = _make_session_dir(tmp_path, dummy_key=False)
        with pytest.raises(StoreStateError, match="key.dpapi"):
            SessionChunkStore.create(session_dir / "audio.enc", SessionCrypto(), sid)

    def test_disk_full_raises_recoverable_store_write_error(self, tmp_path: Path) -> None:
        session_dir, sid = _make_session_dir(tmp_path)
        crypto = SessionCrypto()
        store = SessionChunkStore.create(session_dir / "audio.enc", crypto, sid)

        class FullDisk:
            def write(self, _data: bytes) -> int:
                raise OSError(errno.ENOSPC, "No space left on device")

            def flush(self) -> None:  # pragma: no cover - write raises first
                pass

            def close(self) -> None:
                pass

        store._stream = FullDisk()  # type: ignore[assignment]
        with pytest.raises(StoreWriteError):
            store.append_chunk(b"audio")
        with pytest.raises(StoreStateError, match="closed"):
            store.append_chunk(b"audio")  # handle was closed, not left dangling

    def test_create_collision_maps_to_store_write_error(self, tmp_path: Path) -> None:
        # LOW-001: create failures surface as the recoverable StoreWriteError,
        # never a raw OSError, and never leave a partial store lying around.
        session_dir, sid = _make_session_dir(tmp_path)
        path = session_dir / "audio.enc"
        SessionChunkStore.create(path, SessionCrypto(), sid).close()
        with pytest.raises(StoreWriteError):
            SessionChunkStore.create(path, SessionCrypto(), sid)  # exists already
        assert path.exists()  # the original store was not clobbered

    def test_oversized_chunk_rejected(self, tmp_path: Path) -> None:
        session_dir, sid = _make_session_dir(tmp_path)
        store = SessionChunkStore.create(session_dir / "audio.enc", SessionCrypto(), sid)
        with pytest.raises(ValueError):
            store.append_chunk(b"\0" * (session_store.MAX_CHUNK_PLAINTEXT_BYTES + 1))
        store.close()


# ------------------------------------------------------------- SessionCrypto


class TestSessionCryptoExtensions:
    def test_export_and_from_key_round_trip(self) -> None:
        original = SessionCrypto()
        blob = original.encrypt(b"payload", b"aad")
        restored = SessionCrypto.from_key(original.export_key())
        assert restored.decrypt(blob, b"aad") == b"payload"

    def test_wrong_aad_fails(self) -> None:
        crypto = SessionCrypto()
        blob = crypto.encrypt(b"payload", b"aad-1")
        from cryptography.exceptions import InvalidTag

        with pytest.raises(InvalidTag):
            crypto.decrypt(blob, b"aad-2")

    def test_export_after_destroy_raises(self) -> None:
        crypto = SessionCrypto()
        crypto.destroy()
        with pytest.raises(RuntimeError):
            crypto.export_key()

    def test_from_key_rejects_bad_length(self) -> None:
        with pytest.raises(ValueError):
            SessionCrypto.from_key(b"short")


# ---------------------------------------------------------------- key custody


class TestKeyPathResolution:
    def test_resolves_strictly_under_root(self, tmp_path: Path) -> None:
        sid = _sid()
        assert resolve_key_path(tmp_path, sid) == tmp_path / sid / KEY_FILENAME

    @pytest.mark.parametrize(
        "bad",
        [
            "",
            "..",
            "../escape",
            "ABCDEF" + "0" * 26,
            "0" * 31,
            "0" * 33,
            "key.dpapi",
            "0" * 31 + "\n",
        ],
    )
    def test_rejects_malformed_session_ids(self, tmp_path: Path, bad: str) -> None:
        with pytest.raises(ValueError):
            resolve_key_path(tmp_path, bad)


@windows_only
class TestDpapiCustody:
    def test_wrap_unwrap_round_trip(self, tmp_path: Path) -> None:
        session_dir, _sid_ = _make_session_dir(tmp_path, dummy_key=False)
        crypto = SessionCrypto()
        blob = crypto.encrypt(b"clinical-free test payload")
        key_path = wrap_key_to_file(crypto, session_dir)
        assert key_path == session_dir / KEY_FILENAME
        assert not (session_dir / (KEY_FILENAME + ".tmp")).exists()
        # Wrapped blob must not contain the raw key (DPAPI actually applied).
        assert crypto.export_key() not in key_path.read_bytes()
        restored = unwrap_key_from_file(session_dir)
        assert restored.decrypt(blob) == b"clinical-free test payload"

    def test_delete_key_makes_session_undecryptable(self, tmp_path: Path) -> None:
        session_dir, _sid_ = _make_session_dir(tmp_path, dummy_key=False)
        crypto = SessionCrypto()
        wrap_key_to_file(crypto, session_dir)
        session_store.delete_session_key(session_dir)
        with pytest.raises(KeyCustodyError):
            unwrap_key_from_file(session_dir)
        session_store.delete_session_key(session_dir)  # idempotent

    @pytest.mark.parametrize("blob", [b"", b"tiny", b"\0" * 400])
    def test_zero_length_or_garbage_key_blob_raises(self, tmp_path: Path, blob: bytes) -> None:
        session_dir, _sid_ = _make_session_dir(tmp_path, dummy_key=False)
        (session_dir / KEY_FILENAME).write_bytes(blob)
        with pytest.raises(KeyCustodyError):
            unwrap_key_from_file(session_dir)

    def test_truncated_real_blob_raises(self, tmp_path: Path) -> None:
        session_dir, _sid_ = _make_session_dir(tmp_path, dummy_key=False)
        key_path = wrap_key_to_file(SessionCrypto(), session_dir)
        data = key_path.read_bytes()
        key_path.write_bytes(data[: len(data) // 2])
        with pytest.raises(KeyCustodyError):
            unwrap_key_from_file(session_dir)


# --------------------------------------------------- Complete / Discard order


class TestDeletionOrdering:
    def test_complete_fsync_verify_then_delete_key(self, tmp_path: Path) -> None:
        session_dir, _sid_ = _make_session_dir(tmp_path)
        crypto = SessionCrypto()
        transcript = session_dir / "transcript.enc"
        transcript.write_bytes(crypto.encrypt(b"transcript body"))
        complete_session(session_dir, crypto)
        assert not (session_dir / KEY_FILENAME).exists()
        # PR-HIGH-001 (downgraded MED): the in-memory key must die with the
        # blob — nothing application-owned can decrypt after Complete.
        assert crypto.destroyed
        with pytest.raises(RuntimeError):
            crypto.export_key()

    def test_complete_keeps_key_when_transcript_fails_verification(self, tmp_path: Path) -> None:
        session_dir, _sid_ = _make_session_dir(tmp_path)
        crypto = SessionCrypto()
        (session_dir / "transcript.enc").write_bytes(b"\0" * 64)  # corrupt
        with pytest.raises(StoreCorruptError):
            complete_session(session_dir, crypto)
        assert (session_dir / KEY_FILENAME).exists()
        assert not crypto.destroyed  # failed verification keeps the key usable

    def test_complete_keeps_key_when_transcript_missing(self, tmp_path: Path) -> None:
        session_dir, _sid_ = _make_session_dir(tmp_path)
        with pytest.raises(StoreWriteError):
            complete_session(session_dir, SessionCrypto())
        assert (session_dir / KEY_FILENAME).exists()

    def test_discard_deletes_key_first_then_dir(self, tmp_path: Path) -> None:
        session_dir, _sid_ = _make_session_dir(tmp_path)
        (session_dir / "audio.enc").write_bytes(b"leftover")
        crypto = SessionCrypto()
        discard_session(session_dir, crypto)
        assert not session_dir.exists()
        assert crypto.destroyed

    def test_discard_without_live_crypto(self, tmp_path: Path) -> None:
        session_dir, _sid_ = _make_session_dir(tmp_path)
        discard_session(session_dir)  # recovery-screen discard: no unwrapped key
        assert not session_dir.exists()


# ------------------------------------------------- note custody at Complete


TRANSCRIPT_BODY = b"transcript body"


def _completable_session(tmp_path: Path) -> tuple[Path, SessionCrypto]:
    """A session dir with a transcript that would Complete cleanly on its own."""
    session_dir, _sid_ = _make_session_dir(tmp_path)
    crypto = SessionCrypto()
    (session_dir / "transcript.enc").write_bytes(crypto.encrypt(TRANSCRIPT_BODY))
    return session_dir, crypto


def _write_note(
    session_dir: Path,
    crypto: SessionCrypto,
    *,
    session_id: str | None = None,
    transcript_digest: str | None = None,
) -> None:
    from scribe_desktop.note import GeneratedNote, digest_bytes

    note = GeneratedNote(
        session_id=session_id if session_id is not None else session_dir.name,
        created_at=datetime.now(UTC),
        template_profile_id="clinic-a",
        provider_name="extractive-v1",
        transcript_digest=(
            transcript_digest
            if transcript_digest is not None
            else digest_bytes(TRANSCRIPT_BODY)
        ),
        config_digest=digest_bytes(b"config"),
    )
    (session_dir / NOTE_FILENAME).write_bytes(crypto.encrypt(note.to_bytes()))


def _digest_of_another_transcript() -> str:
    from scribe_desktop.note import digest_bytes

    return digest_bytes(b"a superseded transcript")


class TestNoteCustodyOnComplete:
    """Task 1.5: the note joins the Complete ordering and FAILS CLOSED
    exactly like the transcript. Every failure below must retain the key —
    custody is what keeps regeneration possible, so completing over an
    unverifiable note would destroy the only route to a correct one."""

    def test_note_absent_completes(self, tmp_path: Path) -> None:
        session_dir, crypto = _completable_session(tmp_path)
        complete_session(session_dir, crypto)
        assert not (session_dir / KEY_FILENAME).exists()

    def test_valid_note_completes_and_survives_on_disk(self, tmp_path: Path) -> None:
        session_dir, crypto = _completable_session(tmp_path)
        _write_note(session_dir, crypto)
        complete_session(session_dir, crypto)
        assert not (session_dir / KEY_FILENAME).exists()
        assert (session_dir / NOTE_FILENAME).is_file()
        assert crypto.destroyed

    def test_corrupt_ciphertext_retains_the_key(self, tmp_path: Path) -> None:
        session_dir, crypto = _completable_session(tmp_path)
        (session_dir / NOTE_FILENAME).write_bytes(b"\0" * 64)
        with pytest.raises(StoreCorruptError, match="note failed decrypt"):
            complete_session(session_dir, crypto)
        assert (session_dir / KEY_FILENAME).exists()
        assert not crypto.destroyed

    def test_authenticated_but_malformed_note_retains_the_key(self, tmp_path: Path) -> None:
        session_dir, crypto = _completable_session(tmp_path)
        (session_dir / NOTE_FILENAME).write_bytes(crypto.encrypt(b'{"nope": 1}'))
        with pytest.raises(StoreCorruptError, match="malformed"):
            complete_session(session_dir, crypto)
        assert (session_dir / KEY_FILENAME).exists()
        assert not crypto.destroyed

    def test_note_bound_to_another_session_retains_the_key(self, tmp_path: Path) -> None:
        session_dir, crypto = _completable_session(tmp_path)
        _write_note(session_dir, crypto, session_id=_sid())
        with pytest.raises(StoreCorruptError, match="another session"):
            complete_session(session_dir, crypto)
        assert (session_dir / KEY_FILENAME).exists()
        assert not crypto.destroyed

    def test_note_describing_another_transcript_retains_the_key(self, tmp_path: Path) -> None:
        from scribe_desktop.note import digest_bytes

        session_dir, crypto = _completable_session(tmp_path)
        _write_note(session_dir, crypto, transcript_digest=digest_bytes(b"an older transcript"))
        with pytest.raises(StoreCorruptError, match="does not describe this transcript"):
            complete_session(session_dir, crypto)
        assert (session_dir / KEY_FILENAME).exists()
        assert not crypto.destroyed

    def test_note_binding_uses_the_audio_header_when_present(self, tmp_path: Path) -> None:
        """The header is authoritative: a note carrying the DIRECTORY name
        while the store says otherwise must not clear Complete."""
        chunk_path, crypto, sid = _build_store(tmp_path, [b"audio"])
        session_dir = chunk_path.parent
        renamed = session_dir.parent / _sid()
        session_dir.rename(renamed)
        (renamed / "transcript.enc").write_bytes(crypto.encrypt(TRANSCRIPT_BODY))
        _write_note(renamed, crypto)  # binds to the NEW directory name
        with pytest.raises(StoreCorruptError, match="another session"):
            complete_session(renamed, crypto)
        assert (renamed / KEY_FILENAME).exists()
        _write_note(renamed, crypto, session_id=sid)  # binds to the header id
        complete_session(renamed, crypto)
        assert not (renamed / KEY_FILENAME).exists()

    def test_unresolvable_session_identity_retains_the_key(self, tmp_path: Path) -> None:
        session_dir = tmp_path / "not-a-session-id"
        session_dir.mkdir()
        (session_dir / KEY_FILENAME).write_bytes(b"\0" * 64)
        crypto = SessionCrypto()
        (session_dir / "transcript.enc").write_bytes(crypto.encrypt(TRANSCRIPT_BODY))
        _write_note(session_dir, crypto, session_id=_sid())
        with pytest.raises(StoreCorruptError, match="unresolvable"):
            complete_session(session_dir, crypto)
        assert (session_dir / KEY_FILENAME).exists()

    def test_explicit_delete_note_then_complete(self, tmp_path: Path) -> None:
        """The clinician's confirmed 'complete without a note' exit — the note
        is removed explicitly, never silently dropped by the ordering."""
        session_dir, crypto = _completable_session(tmp_path)
        _write_note(session_dir, crypto, transcript_digest=_digest_of_another_transcript())
        complete_session(session_dir, crypto, delete_note=True)
        assert not (session_dir / NOTE_FILENAME).exists()
        assert not (session_dir / KEY_FILENAME).exists()

    def test_unlink_failure_retains_the_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        session_dir, crypto = _completable_session(tmp_path)
        _write_note(session_dir, crypto)

        def refuse(self: Path, missing_ok: bool = False) -> None:
            raise OSError(errno.EACCES, "locked by another process")

        monkeypatch.setattr(Path, "unlink", refuse)
        with pytest.raises(StoreWriteError, match="not removable"):
            complete_session(session_dir, crypto, delete_note=True)
        assert (session_dir / KEY_FILENAME).exists()
        assert (session_dir / NOTE_FILENAME).exists()
        assert not crypto.destroyed


# ------------------------------------------------- note artifact I/O (6.2)


def _note_config() -> NoteConfig:
    from scribe_desktop.note_config import NoteConfig

    return NoteConfig()


def _writable_note(
    session_dir: Path,
    config: NoteConfig,
    *,
    note_sections: tuple[GeneratedSection, ...] = (),
    note_warnings: tuple[NoteWarning, ...] = (),
    session_id: str | None = None,
    transcript_dig: str | None = None,
    config_dig: str | None = None,
) -> GeneratedNote:
    from scribe_desktop.note import GeneratedNote, digest_bytes

    return GeneratedNote(
        session_id=session_id if session_id is not None else session_dir.name,
        created_at=datetime.now(UTC),
        template_profile_id="clinic-a",
        provider_name="extractive-v1",
        transcript_digest=(
            transcript_dig if transcript_dig is not None else digest_bytes(TRANSCRIPT_BODY)
        ),
        config_digest=config_dig if config_dig is not None else config.config_digest(),
        note_sections=note_sections,
        note_warnings=note_warnings,
    )


def _confirmed_assertion(
    config_digest: str, *, shown_text_digest: str | None = None
) -> tuple[GeneratedSection, ...]:
    """ONE section holding a legally-constructed confirmed autofill assertion.
    Construction checks evidence PRESENCE only (on purpose — note.py records
    why), so a mismatched ``shown_text_digest`` is constructable and it is
    ``write_note``'s job to refuse it."""
    from scribe_desktop.note import (
        ConfirmationDecision,
        GeneratedSection,
        NoteAssertion,
        NoteSpan,
        text_digest,
    )

    text = "Ice pack use explained."
    assertion = NoteAssertion(
        assertion_id="autofill-aaaaaaaaaaaaaaaaaaaaaaaa",
        section_key="advice_home_exercise",
        note_span=NoteSpan(span_text=text, provenance="autofill"),
        proposal_id="autofill-aaaaaaaaaaaaaaaaaaaaaaaa",
        shown_text_digest=(
            shown_text_digest if shown_text_digest is not None else text_digest(text)
        ),
        config_digest=config_digest,
        confirmation=ConfirmationDecision(
            proposal_id="autofill-aaaaaaaaaaaaaaaaaaaaaaaa",
            note_confirmation="confirmed",
            decided_at=datetime.now(UTC),
        ),
    )
    return (
        GeneratedSection(section_key="advice_home_exercise", note_assertions=(assertion,)),
    )


class TestNoteArtifactIO:
    """Task 6.2: `write_note`/`read_note` mirror the transcript artifact I/O
    (atomic_write_bytes, no AAD), and `write_note` enforces the artifact
    invariants ITSELF — defense in depth rather than trust in the UI or in
    construction-time validation. Every refusal leaves the disk unchanged."""

    def test_write_and_read_round_trip(self, tmp_path: Path) -> None:
        session_dir, crypto = _completable_session(tmp_path)
        config = _note_config()
        note = _writable_note(session_dir, config)
        path = write_note(session_dir, crypto, note, config)
        assert path == session_dir / NOTE_FILENAME
        assert not (session_dir / (NOTE_FILENAME + ".tmp")).exists()
        assert read_note(session_dir, crypto) == note

    def test_written_note_clears_the_complete_ordering(self, tmp_path: Path) -> None:
        session_dir, crypto = _completable_session(tmp_path)
        config = _note_config()
        write_note(session_dir, crypto, _writable_note(session_dir, config), config)
        complete_session(session_dir, crypto)
        assert not (session_dir / KEY_FILENAME).exists()
        assert (session_dir / NOTE_FILENAME).is_file()

    def test_refuses_unresolved_error_warning(self, tmp_path: Path) -> None:
        from scribe_desktop.note import NoteWarning

        session_dir, crypto = _completable_session(tmp_path)
        config = _note_config()
        note = _writable_note(
            session_dir,
            config,
            note_warnings=(
                NoteWarning(note_warning_code="contradiction", severity="error"),
            ),
        )
        with pytest.raises(NoteWriteRefusedError, match="unresolved error"):
            write_note(session_dir, crypto, note, config)
        assert not (session_dir / NOTE_FILENAME).exists()

    def test_refuses_shown_text_digest_mismatch(self, tmp_path: Path) -> None:
        """The relation construction deliberately does NOT verify: the digest
        must be the digest of the assertion's OWN text."""
        from scribe_desktop.note import text_digest

        session_dir, crypto = _completable_session(tmp_path)
        config = _note_config()
        sections = _confirmed_assertion(
            config.config_digest(), shown_text_digest=text_digest("different words")
        )
        note = _writable_note(session_dir, config, note_sections=sections)
        with pytest.raises(NoteWriteRefusedError, match="shown_text_digest"):
            write_note(session_dir, crypto, note, config)
        assert not (session_dir / NOTE_FILENAME).exists()

    def test_refuses_assertion_confirmed_under_a_different_config(
        self, tmp_path: Path
    ) -> None:
        from scribe_desktop.note import digest_bytes

        session_dir, crypto = _completable_session(tmp_path)
        config = _note_config()
        sections = _confirmed_assertion(digest_bytes(b"a different config"))
        note = _writable_note(session_dir, config, note_sections=sections)
        with pytest.raises(NoteWriteRefusedError, match="different config"):
            write_note(session_dir, crypto, note, config)

    def test_refuses_forged_validator_skipping_note(self, tmp_path: Path) -> None:
        """The unbacked-assertion CLASS guard: canonical re-validation, not an
        enumerated field list. A `model_construct` note whose autofill
        assertion carries no ConfirmationDecision dies typed."""
        from scribe_desktop.note import (
            GeneratedNote,
            GeneratedSection,
            NoteAssertion,
            NoteSpan,
            digest_bytes,
            text_digest,
        )

        session_dir, crypto = _completable_session(tmp_path)
        config = _note_config()
        text = "Ice pack use explained."
        forged_assertion = NoteAssertion.model_construct(
            assertion_id="autofill-bbbbbbbbbbbbbbbbbbbbbbbb",
            section_key="advice_home_exercise",
            note_span=NoteSpan(span_text=text, provenance="autofill"),
            speaker=None,
            proposal_id="autofill-bbbbbbbbbbbbbbbbbbbbbbbb",
            shown_text_digest=text_digest(text),
            config_digest=config.config_digest(),
            confirmation=None,  # the forgery: unconfirmed content wearing evidence fields
        )
        forged_section = GeneratedSection.model_construct(
            section_key="advice_home_exercise", note_assertions=(forged_assertion,)
        )
        forged = GeneratedNote.model_construct(
            schema_version=1,
            session_id=session_dir.name,
            created_at=datetime.now(UTC),
            template_profile_id="clinic-a",
            provider_name="extractive-v1",
            clinician_speaker=None,
            transcript_digest=digest_bytes(TRANSCRIPT_BODY),
            config_digest=config.config_digest(),
            note_sections=(forged_section,),
            note_warnings=(),
        )
        with pytest.raises(NoteWriteRefusedError, match="canonical re-validation"):
            write_note(session_dir, crypto, forged, config)
        assert not (session_dir / NOTE_FILENAME).exists()

    def test_refuses_config_digest_mismatch_with_presented_config(
        self, tmp_path: Path
    ) -> None:
        from scribe_desktop.note import digest_bytes

        session_dir, crypto = _completable_session(tmp_path)
        config = _note_config()
        note = _writable_note(
            session_dir, config, config_dig=digest_bytes(b"some other config")
        )
        with pytest.raises(NoteWriteRefusedError, match="presented config"):
            write_note(session_dir, crypto, note, config)

    def test_refuses_foreign_session_binding(self, tmp_path: Path) -> None:
        session_dir, crypto = _completable_session(tmp_path)
        config = _note_config()
        note = _writable_note(session_dir, config, session_id=_sid())
        with pytest.raises(NoteWriteRefusedError, match="another session"):
            write_note(session_dir, crypto, note, config)

    def test_refuses_stale_transcript_digest(self, tmp_path: Path) -> None:
        session_dir, crypto = _completable_session(tmp_path)
        config = _note_config()
        note = _writable_note(
            session_dir, config, transcript_dig=_digest_of_another_transcript()
        )
        with pytest.raises(NoteWriteRefusedError, match="transcript"):
            write_note(session_dir, crypto, note, config)

    def test_missing_transcript_fails_closed(self, tmp_path: Path) -> None:
        session_dir, _sid_ = _make_session_dir(tmp_path)
        crypto = SessionCrypto()
        config = _note_config()
        note = _writable_note(session_dir, config)
        with pytest.raises(StoreWriteError, match="transcript artifact unreadable"):
            write_note(session_dir, crypto, note, config)
        assert not (session_dir / NOTE_FILENAME).exists()

    def test_read_missing_note(self, tmp_path: Path) -> None:
        session_dir, crypto = _completable_session(tmp_path)
        with pytest.raises(StoreWriteError, match="note artifact unreadable"):
            read_note(session_dir, crypto)

    def test_read_corrupt_ciphertext(self, tmp_path: Path) -> None:
        session_dir, crypto = _completable_session(tmp_path)
        (session_dir / NOTE_FILENAME).write_bytes(b"\0" * 64)
        with pytest.raises(StoreCorruptError, match="note failed decrypt"):
            read_note(session_dir, crypto)

    def test_read_refuses_note_bound_to_another_session(self, tmp_path: Path) -> None:
        session_dir, crypto = _completable_session(tmp_path)
        _write_note(session_dir, crypto, session_id=_sid())
        with pytest.raises(StoreCorruptError, match="another session"):
            read_note(session_dir, crypto)

    def test_read_refuses_note_describing_another_transcript(self, tmp_path: Path) -> None:
        session_dir, crypto = _completable_session(tmp_path)
        _write_note(session_dir, crypto, transcript_digest=_digest_of_another_transcript())
        with pytest.raises(StoreCorruptError, match="does not describe this transcript"):
            read_note(session_dir, crypto)

    def test_read_and_complete_share_the_verification_core(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Task 6.2 Done-when: `read_note` verifies through the SAME code path
        `complete_session` uses — pinned structurally, not by prose."""
        session_dir, crypto = _completable_session(tmp_path)
        _write_note(session_dir, crypto)
        calls: list[str] = []
        original = session_store._verified_note

        def spy(*args: object, **kwargs: object) -> object:
            calls.append("verified")
            return original(*args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(session_store, "_verified_note", spy)
        read_note(session_dir, crypto)
        assert calls == ["verified"]
        complete_session(session_dir, crypto)
        assert calls == ["verified", "verified"]


# ----------------------------------------------------------------- the sweep


class TestEarliestTrustedTimestamp:
    """The single fail-safe rule shared by the sweep and the recovery
    listing (they used to carry separate copies and inherited the same
    clock-skew defect). Round 48 HIGH-001 merged this branch's skew
    tolerance into main's shared helper; these are the only direct unit
    tests it has."""

    NOW = 1_000_000.0

    def test_tolerance_stays_a_filesystem_allowance_not_a_retention_knob(self) -> None:
        """SEC-002: the tolerance is load-bearing for the 24 h cap, and both
        security docs quote its cost as a bound. Nothing else pins the value,
        so a bump would silently extend retention AND widen the band where a
        tampered far-future stamp reads as trusted. These are ABSOLUTE bounds
        on purpose — they do not derive from the constant, so raising it past
        what the docs promise fails here and forces the docs to move with it.
        """
        assert CLOCK_SKEW_TOLERANCE > 0
        assert CLOCK_SKEW_TOLERANCE < 60
        assert CLOCK_SKEW_TOLERANCE < RECOVERY_WINDOW.total_seconds() / 1000

    def test_earliest_past_value_wins(self) -> None:
        assert (
            earliest_trusted_timestamp([self.NOW - 60, self.NOW], self.NOW)
            == self.NOW - 60
        )

    def test_marginally_future_values_are_clamped_to_now(self) -> None:
        # Kept (a file written moments ago), but aged from now — never
        # allowed to read as younger than the present.
        skewed = self.NOW + CLOCK_SKEW_TOLERANCE / 2
        assert earliest_trusted_timestamp([skewed], self.NOW) == self.NOW

    def test_clamped_value_never_displaces_a_real_earlier_stamp(self) -> None:
        """The safety property behind the merge (round 48 HIGH-001): adding
        the tolerance can only ADD `now` to the trusted set, and every
        pre-existing trusted value is already <= now, so the minimum — and
        therefore every expiry decision — is unchanged wherever the
        untoleranced rule had anything to work with."""
        skewed = self.NOW + CLOCK_SKEW_TOLERANCE / 2
        assert (
            earliest_trusted_timestamp([self.NOW - 100, skewed], self.NOW)
            == self.NOW - 100
        )

    def test_tolerance_boundary_is_inclusive(self) -> None:
        edge = self.NOW + CLOCK_SKEW_TOLERANCE
        assert earliest_trusted_timestamp([edge], self.NOW) == self.NOW

    def test_values_beyond_the_tolerance_are_dropped(self) -> None:
        # A real clock problem still fails closed — callers see no trusted
        # candidate and expire (sweep) or hide (listing).
        beyond = self.NOW + CLOCK_SKEW_TOLERANCE + 1
        assert earliest_trusted_timestamp([beyond], self.NOW) is None

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_values_are_dropped(self, bad: float) -> None:
        assert earliest_trusted_timestamp([bad], self.NOW) is None

    def test_empty_input(self) -> None:
        assert earliest_trusted_timestamp([], self.NOW) is None


class TestExpirySweep:
    @staticmethod
    def _session_with_key(root: Path, *, age_hours: float = 0.0) -> str:
        sid = _sid()
        session_dir = root / sid
        session_dir.mkdir()
        key = session_dir / KEY_FILENAME
        key.write_bytes(b"\0" * 64)
        if age_hours:
            import time

            old = time.time() - age_hours * 3600
            os.utime(key, (old, old))
        return sid

    def test_fresh_session_kept(self, tmp_path: Path) -> None:
        sid = self._session_with_key(tmp_path, age_hours=1)
        results = {r.session_id: r.action for r in sweep_sessions(tmp_path)}
        assert results[sid] == "kept"
        assert (tmp_path / sid).exists()

    def test_expired_session_destroyed(self, tmp_path: Path) -> None:
        sid = self._session_with_key(tmp_path, age_hours=25)
        results = {r.session_id: r.action for r in sweep_sessions(tmp_path)}
        assert results[sid] == "expired"
        assert not (tmp_path / sid).exists()

    def test_expiry_uses_store_header_created_at(self, tmp_path: Path) -> None:
        import time

        session_dir, sid = _make_session_dir(tmp_path)
        crypto = SessionCrypto()
        store = SessionChunkStore.create(
            session_dir / "audio.enc", crypto, sid, created_at=time.time() - 25 * 3600
        )
        store.append_chunk(b"old audio")
        store.close()
        results = {r.session_id: r.action for r in sweep_sessions(tmp_path)}
        assert results[sid] == "expired"
        assert not session_dir.exists()

    @pytest.mark.parametrize("bad_created_at", [float("nan"), float("inf"), 4e12])
    def test_malformed_or_future_header_timestamp_cannot_extend_retention(
        self, tmp_path: Path, bad_created_at: float
    ) -> None:
        # PR-MED-004: NaN/inf/future created-at must not defeat the 24h cap —
        # the sweep falls back to the (old) key mtime and expires the session.
        import time

        session_dir, sid = _make_session_dir(tmp_path)
        store = SessionChunkStore.create(
            session_dir / "audio.enc", SessionCrypto(), sid, created_at=bad_created_at
        )
        store.append_chunk(b"audio")
        store.close()
        old = time.time() - 25 * 3600
        os.utime(session_dir / KEY_FILENAME, (old, old))
        results = {r.session_id: r.action for r in sweep_sessions(tmp_path)}
        assert results[sid] == "expired"
        assert not session_dir.exists()

    def test_marginally_future_timestamps_do_not_destroy_a_fresh_session(
        self, tmp_path: Path
    ) -> None:
        """Windows' coarse wall clock lets a just-written file carry an mtime
        a few ms AHEAD of a later time.time(). Before CLOCK_SKEW_TOLERANCE that
        read as "future = untrusted", and the sweep CRYPTOGRAPHICALLY DELETED
        the session. It must be kept."""
        import time

        sid = self._session_with_key(tmp_path)
        now = time.time()
        skewed = now + 0.05  # ~3x the 15.6 ms Windows clock tick
        os.utime(tmp_path / sid / KEY_FILENAME, (skewed, skewed))
        os.utime(tmp_path / sid, (skewed, skewed))
        results = {r.session_id: r.action for r in sweep_sessions(tmp_path, now=now)}
        assert results[sid] == "kept"
        assert (tmp_path / sid / KEY_FILENAME).is_file()

    def test_skew_tolerance_bounds_the_extra_retention_it_can_buy(
        self, tmp_path: Path
    ) -> None:
        """Accepting a near-future stamp lets a session read younger than it
        is, so it dies late — but by AT MOST CLOCK_SKEW_TOLERANCE. Pinned at
        the worst case (maximum skew), which the retention schedule quotes."""
        import time

        sid = self._session_with_key(tmp_path)
        now = time.time()
        skewed = now + CLOCK_SKEW_TOLERANCE  # the most skew that is tolerated
        os.utime(tmp_path / sid / KEY_FILENAME, (skewed, skewed))
        os.utime(tmp_path / sid, (skewed, skewed))
        window = RECOVERY_WINDOW.total_seconds()

        # One second before the bound it is still alive...
        kept = sweep_sessions(tmp_path, now=now + window + CLOCK_SKEW_TOLERANCE - 1)
        assert {r.session_id: r.action for r in kept}[sid] == "kept"
        # ...and at the bound it is destroyed. Overshoot can never exceed it.
        expired = sweep_sessions(tmp_path, now=now + window + CLOCK_SKEW_TOLERANCE)
        assert {r.session_id: r.action for r in expired}[sid] == "expired"
        assert not (tmp_path / sid).exists()

    def test_all_future_timestamps_fail_closed(self, tmp_path: Path) -> None:
        # PR-MED-005: header + key mtime + dir mtime ALL in the future must
        # expire immediately (fail-closed), not reset age to zero each sweep.
        import time

        session_dir, sid = _make_session_dir(tmp_path)
        store = SessionChunkStore.create(
            session_dir / "audio.enc", SessionCrypto(), sid, created_at=time.time() + 7 * 86400
        )
        store.append_chunk(b"audio")
        store.close()
        future = time.time() + 7 * 86400
        os.utime(session_dir / KEY_FILENAME, (future, future))
        os.utime(session_dir, (future, future))
        results = {r.session_id: r.action for r in sweep_sessions(tmp_path)}
        assert results[sid] == "expired"
        assert not session_dir.exists()

    def test_expiry_boundary_is_inclusive(self, tmp_path: Path) -> None:
        # Exactly max_age old expires (>= not >).
        import time

        sid = self._session_with_key(tmp_path)
        exact = time.time() - 3600
        os.utime(tmp_path / sid / KEY_FILENAME, (exact, exact))
        results = {
            r.session_id: r.action
            for r in sweep_sessions(tmp_path, now=exact + 3600, max_age=timedelta(hours=1))
        }
        assert results[sid] == "expired"

    def test_active_session_skipped_even_if_old(self, tmp_path: Path) -> None:
        sid = self._session_with_key(tmp_path, age_hours=48)
        results = {
            r.session_id: r.action
            for r in sweep_sessions(tmp_path, active_session_ids=frozenset({sid}))
        }
        assert results[sid] == "skipped_active"
        assert (tmp_path / sid / KEY_FILENAME).exists()

    def test_orphan_dir_without_key_gcd(self, tmp_path: Path) -> None:
        sid = _sid()
        orphan = tmp_path / sid
        orphan.mkdir()
        (orphan / "audio.enc").write_bytes(b"orphaned")
        results = {r.session_id: r.action for r in sweep_sessions(tmp_path)}
        assert results[sid] == "orphan_gc"
        assert not orphan.exists()

    def test_zero_length_key_blob_gcd(self, tmp_path: Path) -> None:
        sid = _sid()
        session_dir = tmp_path / sid
        session_dir.mkdir()
        (session_dir / KEY_FILENAME).write_bytes(b"")
        results = {r.session_id: r.action for r in sweep_sessions(tmp_path)}
        assert results[sid] == "orphan_gc"
        assert not session_dir.exists()

    def test_truncated_key_blob_gcd(self, tmp_path: Path) -> None:
        sid = _sid()
        session_dir = tmp_path / sid
        session_dir.mkdir()
        (session_dir / KEY_FILENAME).write_bytes(b"stub")  # < minimum DPAPI size
        results = {r.session_id: r.action for r in sweep_sessions(tmp_path)}
        assert results[sid] == "orphan_gc"
        assert not session_dir.exists()

    def test_inaccessible_key_reports_error_and_deletes_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # PR-MED-006: a transiently inaccessible key.dpapi (stat raises a
        # non-FileNotFoundError OSError) must NOT be treated as orphan
        # custody — no cryptographic deletion, action == "error".
        sid = self._session_with_key(tmp_path)
        key_file = tmp_path / sid / KEY_FILENAME
        real_stat = Path.stat

        def deny_key_stat(self: Path, **kwargs: object) -> os.stat_result:
            if self == key_file:
                raise PermissionError(13, "sharing violation", str(self))
            return real_stat(self, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "stat", deny_key_stat)
        results = {r.session_id: r.action for r in sweep_sessions(tmp_path)}
        monkeypatch.undo()
        assert results[sid] == "error"
        assert key_file.exists()
        assert (tmp_path / sid).exists()

    def test_foreign_names_left_alone(self, tmp_path: Path) -> None:
        foreign = tmp_path / "not-a-session-id"
        foreign.mkdir()
        (foreign / "file.txt").write_bytes(b"hands off")
        assert sweep_sessions(tmp_path) == []
        assert foreign.exists()

    def test_missing_root_is_noop(self, tmp_path: Path) -> None:
        assert sweep_sessions(tmp_path / "nope") == []

    def test_sweep_logs_whitelisted_metadata_only(self, tmp_path: Path) -> None:
        import logging

        self._session_with_key(tmp_path, age_hours=25)
        logger = logging.getLogger("test_sweep_logger")
        logger.setLevel(logging.INFO)
        records: list[logging.LogRecord] = []

        class Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        handler = Capture()
        logger.addHandler(handler)
        try:
            sweep_sessions(tmp_path, logger=logger)
        finally:
            logger.removeHandler(handler)
        assert records, "sweep should log its actions"
        assert all("session_sweep" in r.getMessage() for r in records)

    def test_custom_max_age(self, tmp_path: Path) -> None:
        sid = self._session_with_key(tmp_path, age_hours=2)
        results = {
            r.session_id: r.action
            for r in sweep_sessions(tmp_path, max_age=timedelta(hours=1))
        }
        assert results[sid] == "expired"
