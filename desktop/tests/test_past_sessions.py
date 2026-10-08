"""The Past-sessions archive (privacy-professional-controls plan Tasks
2.1–2.3; D1, D3, D5, D6; Critical Constraints C1 and C4).

The entry-key custody is the store's injected ``wrap_key`` / ``unwrap_key``
seam — a fake that writes the raw key behind a marker — so nothing here
needs the host's DPAPI except the one ``windows_only`` class that pins the
real description isolation. Dates come from injected clocks, never the
wall clock."""

from __future__ import annotations

import errno
import os
import shutil
import stat
import sys
import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from cryptography.exceptions import InvalidTag

from scribe_desktop import past_sessions, session_store
from scribe_desktop.note import GeneratedNote, digest_bytes
from scribe_desktop.past_sessions import (
    AUDIO_KEY_FILE_BYTES,
    AUDIO_KEY_FILENAME,
    LABEL_FILENAME,
    LEGACY_RETENTION_DAYS,
    MAX_PATIENT_NAME_CHARS,
    MIN_RETENTION_DAYS,
    PENDING_FILENAME,
    RETENTION_DAYS_CHOICES,
    STAGING_DIRNAME,
    UNKNOWN_LABEL,
    KeepLabel,
    PastSessionError,
    PastSessionListing,
    PastSessionSettings,
    PastSessionSettingsError,
    PastSessionStore,
    keep_label,
    load_past_session_settings,
    read_past_session_settings,
    save_past_session_settings,
)
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import (
    AUDIO_FILENAME,
    GENERATED_FILENAME,
    KEY_FILENAME,
    NOTE_FILENAME,
    TRANSCRIPT_FILENAME,
    ArchiveSource,
    ArchiveWriteError,
    GeneratedRecord,
    KeyCustodyError,
    SessionChunkStore,
    StoreCorruptError,
    complete_session,
    sweep_sessions,
    write_generated,
)
from scribe_desktop.transcription import TranscriptDocument

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-only")

NOW = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
# The one retention window (the 7-year minimum, practitioner decision
# 2026-10-02) and its span: expiry is proven at it, never at a shorter one.
SEVEN = MIN_RETENTION_DAYS
WINDOW = timedelta(days=SEVEN)
_FAKE = b"FAKE-ENTRY-KEY:"
LINKED = KeepLabel("Jane Citizen", "linked", "0123456789abcdef", shadow=False)


def _sid() -> str:
    return uuid.uuid4().hex


def _fake_wrap(crypto: SessionCrypto, directory: Path) -> None:
    (directory / KEY_FILENAME).write_bytes(_FAKE + crypto.export_key())


def _fake_unwrap(directory: Path) -> SessionCrypto:
    blob = (directory / KEY_FILENAME).read_bytes()
    if not blob.startswith(_FAKE):
        raise KeyCustodyError("not an entry key")
    return SessionCrypto.from_key(blob[len(_FAKE) :])


class _Unwraps:
    """The fake unwrap, counted — "never" must decrypt nothing."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, directory: Path) -> SessionCrypto:
        self.calls += 1
        return _fake_unwrap(directory)


def _store(tmp_path: Path, *, clock: datetime = NOW, **overrides: Any) -> PastSessionStore:
    kwargs: dict[str, Any] = {"wrap_key": _fake_wrap, "unwrap_key": _fake_unwrap}
    kwargs.update(overrides)
    return PastSessionStore(tmp_path / "past_sessions", clock=lambda: clock, **kwargs)


def _transcript(session_id: str, *, model_name: str = "small") -> bytes:
    return TranscriptDocument(
        session_id=session_id,
        created_at=NOW,
        model_name=model_name,
        sample_rate=16_000,
        transcript_segments=(),
    ).to_bytes()


def _note(session_id: str, transcript: bytes, *, provider: str = "extractive-v1") -> bytes:
    return GeneratedNote(
        session_id=session_id,
        created_at=NOW,
        template_profile_id="clinic-a",
        provider_name=provider,
        transcript_digest=digest_bytes(transcript),
        config_digest=digest_bytes(b"config"),
    ).to_bytes()


def _generated(session_id: str, *, provider: str = "extractive-v1") -> GeneratedRecord:
    return GeneratedRecord(
        session_id=session_id,
        created_at=NOW,
        provider_name=provider,
        style="verbatim",
        generated_text="Subjective: sore left knee for two weeks.",
    )


def _source(*, note: bool = True, generated: bool = True) -> ArchiveSource:
    sid = _sid()
    transcript = _transcript(sid)
    return ArchiveSource(
        session_id=sid,
        created_at=(NOW - timedelta(minutes=20)).timestamp(),
        transcript_plain=transcript,
        note_plain=_note(sid, transcript) if note else None,
        generated_plain=_generated(sid).to_bytes() if generated else None,
    )


def _published(store: PastSessionStore, source: ArchiveSource | None = None) -> str:
    source = source if source is not None else _source()
    store.write_entry(source, LINKED)
    assert store.commit(source.session_id)
    return source.session_id


def _session(
    root: Path,
    *,
    model_name: str = "small",
    note_provider: str | None = "extractive-v1",
    generated_provider: str | None = "extractive-v1",
) -> tuple[Path, SessionCrypto]:
    """A completable SOURCE session with a placeholder session key (the
    Complete is handed its crypto directly)."""
    sid = _sid()
    directory = root / sid
    directory.mkdir(parents=True)
    (directory / KEY_FILENAME).write_bytes(b"\0" * 64)
    crypto = SessionCrypto()
    transcript = _transcript(sid, model_name=model_name)
    (directory / TRANSCRIPT_FILENAME).write_bytes(crypto.encrypt(transcript))
    if note_provider is not None:
        note = _note(sid, transcript, provider=note_provider)
        (directory / NOTE_FILENAME).write_bytes(crypto.encrypt(note))
    if generated_provider is not None:
        write_generated(directory, crypto, _generated(sid, provider=generated_provider))
    return directory, crypto


# ---------------------------------------------------------------------------
# The label (D5).
# ---------------------------------------------------------------------------


class TestKeepLabel:
    def test_the_name_is_normalised(self) -> None:
        label = keep_label(
            "  Jane\x00\tCitizen​\n ", "linked", "0123456789abcdef", shadow=False
        )
        assert label.patient_name is not None
        assert label.patient_name.split() == ["Jane", "Citizen"]
        assert "\x00" not in label.patient_name and "\n" not in label.patient_name
        assert keep_label("x" * 500, "linked", None, shadow=False).patient_name == (
            "x" * MAX_PATIENT_NAME_CHARS
        )

    def test_an_empty_name_is_not_available(self) -> None:
        assert keep_label(" \t\x07 ", "linked", None, shadow=False).patient_name is None
        assert keep_label(None, "unknown", None, shadow=True) == UNKNOWN_LABEL

    def test_a_desktop_recording_carries_no_name(self) -> None:
        assert keep_label("Jane Citizen", "desktop", None, shadow=False).patient_name is None

    def test_a_clinic_id_not_of_the_registry_shape_is_left_out(self) -> None:
        assert keep_label(None, "linked", "../../etc", shadow=False).clinic_id is None
        assert keep_label(None, "linked", "0123456789ABCDEF", shadow=False).clinic_id is None
        assert keep_label(None, "linked", "0123456789abcdef", shadow=False).clinic_id == (
            "0123456789abcdef"
        )

    def test_the_shadow_flag_fails_closed(self) -> None:
        """Pilot plan D3: the unresolved label is a shadow recording's, and
        only an explicit False makes a label not shadow."""
        assert UNKNOWN_LABEL.shadow is True
        assert keep_label(None, "linked", None, shadow=True).shadow is True
        assert keep_label(None, "linked", None, shadow=False).shadow is False
        assert keep_label(None, "linked", None, shadow=None).shadow is True  # type: ignore[arg-type]

    def test_the_name_never_reaches_a_repr(self) -> None:
        assert "Jane" not in repr(LINKED)


# ---------------------------------------------------------------------------
# Writing, verifying and publishing (C1).
# ---------------------------------------------------------------------------


class TestWriteEntry:
    def test_a_published_entry_reads_back_through_the_existing_readers(
        self, tmp_path: Path
    ) -> None:
        store = _store(tmp_path)
        source = _source()
        sid = _published(store, source)
        entry = store.read_entry(sid)
        assert entry.transcript.to_bytes() == source.transcript_plain
        assert entry.saved_note is not None and entry.saved_note.to_bytes() == source.note_plain
        assert entry.generated is not None
        assert entry.generated.to_bytes() == source.generated_plain
        label = entry.label
        assert (label.session_id, label.recording, label.clinic_id) == (
            sid,
            "linked",
            "0123456789abcdef",
        )
        assert label.patient_name == "Jane Citizen"
        assert label.completed_at == NOW
        assert label.started_at == NOW - timedelta(minutes=20)
        assert (label.has_saved, label.has_generated) == (True, True)
        assert [listing.session_id for listing in store.list_entries()] == [sid]

    def test_the_entry_holds_exactly_the_source_derived_set(self, tmp_path: Path) -> None:
        """D6: the transcript always; the note and the generated note only
        when the source held them. Never audio."""
        store = _store(tmp_path)
        sid = _published(store, _source(note=False, generated=False))
        names = {path.name for path in (store.root / sid).iterdir()}
        assert names == {KEY_FILENAME, LABEL_FILENAME, TRANSCRIPT_FILENAME}
        entry = store.read_entry(sid)
        assert (entry.saved_note, entry.generated) == (None, None)
        assert (entry.label.has_saved, entry.label.has_generated) == (False, False)

    def test_every_entry_has_its_own_key(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        first = _published(store)
        second = _published(store)
        first_key = (store.root / first / KEY_FILENAME).read_bytes()
        assert first_key != (store.root / second / KEY_FILENAME).read_bytes()
        crypto = _fake_unwrap(store.root / first)
        with pytest.raises(InvalidTag):
            crypto.decrypt((store.root / second / TRANSCRIPT_FILENAME).read_bytes())

    def test_a_pending_entry_is_never_listed_or_opened(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        source = _source()
        store.write_entry(source, LINKED)
        assert (store.root / source.session_id / PENDING_FILENAME).exists()
        assert store.list_entries() == []
        with pytest.raises(PastSessionError) as info:
            store.read_entry(source.session_id)
        assert info.value.reason == "pending"
        with pytest.raises(PastSessionError):
            store.delete_entry(source.session_id)
        assert (store.root / source.session_id / KEY_FILENAME).exists()

    def test_a_key_that_cannot_be_wrapped_writes_nothing(self, tmp_path: Path) -> None:
        def refuse(_crypto: SessionCrypto, _directory: Path) -> None:
            raise KeyCustodyError("DPAPI unavailable")

        store = _store(tmp_path, wrap_key=refuse)
        with pytest.raises(PastSessionError) as info:
            store.write_entry(_source(), LINKED)
        assert info.value.reason == "write_failed"
        assert str(info.value) == "the Past-sessions copy could not be written"
        assert list(store.staging_root.iterdir()) == []
        assert not any(path.name != STAGING_DIRNAME for path in store.root.iterdir())

    def test_an_unusable_archive_key_fails_verification(self, tmp_path: Path) -> None:
        def unusable(_directory: Path) -> SessionCrypto:
            return SessionCrypto()  # a different key: nothing authenticates

        store = _store(tmp_path, unwrap_key=unusable)
        source = _source()
        with pytest.raises(PastSessionError) as info:
            store.write_entry(source, LINKED)
        assert info.value.reason == "verify_failed"
        assert not (store.root / source.session_id).exists()
        assert list(store.staging_root.iterdir()) == []

    def test_a_missing_expected_file_fails_verification(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The exact file set: a saved note the source held but staging lost
        refuses the entry."""
        real = past_sessions.atomic_write_bytes

        def skip_note(path: Path, blob: bytes, **kwargs: Any) -> None:
            if path.name != NOTE_FILENAME:
                real(path, blob, **kwargs)

        monkeypatch.setattr(past_sessions, "atomic_write_bytes", skip_note)
        store = _store(tmp_path)
        with pytest.raises(PastSessionError) as info:
            store.write_entry(_source(), LINKED)
        assert info.value.reason == "verify_failed"

    @pytest.mark.parametrize("name", [LABEL_FILENAME, TRANSCRIPT_FILENAME, GENERATED_FILENAME])
    def test_a_file_that_reads_back_differently_fails_verification(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
    ) -> None:
        real = past_sessions.atomic_write_bytes

        def corrupt(path: Path, blob: bytes, **kwargs: Any) -> None:
            real(path, blob[:-1] + bytes([blob[-1] ^ 1]) if path.name == name else blob, **kwargs)

        monkeypatch.setattr(past_sessions, "atomic_write_bytes", corrupt)
        store = _store(tmp_path)
        with pytest.raises(PastSessionError) as info:
            store.write_entry(_source(), LINKED)
        assert info.value.reason == "verify_failed"
        assert list(store.staging_root.iterdir()) == []

    def test_a_transcript_the_reader_refuses_fails_verification(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        source = replace(_source(note=False), transcript_plain=b"not a document")
        with pytest.raises(PastSessionError) as info:
            store.write_entry(source, LINKED)
        assert info.value.reason == "verify_failed"

    def test_a_failed_publish_leaves_no_entry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def refuse(_src: Any, _dst: Any) -> None:
            raise PermissionError(errno.EACCES, "in use")

        monkeypatch.setattr(past_sessions.os, "rename", refuse)
        store = _store(tmp_path)
        source = _source()
        with pytest.raises(PastSessionError) as info:
            store.write_entry(source, LINKED)
        assert info.value.reason == "publish_failed"
        assert not (store.root / source.session_id).exists()
        assert list(store.staging_root.iterdir()) == []

    def test_a_retry_replaces_the_earlier_entry(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        source = _source()
        store.write_entry(source, UNKNOWN_LABEL)
        first_key = (store.root / source.session_id / KEY_FILENAME).read_bytes()
        store.write_entry(source, LINKED)
        assert (store.root / source.session_id / KEY_FILENAME).read_bytes() != first_key
        assert store.commit(source.session_id)
        assert store.read_entry(source.session_id).label.patient_name == "Jane Citizen"
        assert [path.name for path in store.root.iterdir() if path.name != STAGING_DIRNAME] == [
            source.session_id
        ]


# ---------------------------------------------------------------------------
# The C1 hooks and the reconciliations.
# ---------------------------------------------------------------------------


class TestPendingLifecycle:
    def test_remove_pending_entry_removes_the_entry_and_its_staging(
        self, tmp_path: Path
    ) -> None:
        store = _store(tmp_path)
        source = _source()
        store.write_entry(source, LINKED)
        (store.staging_root / source.session_id).mkdir(parents=True)
        (store.staging_root / source.session_id / KEY_FILENAME).write_bytes(b"k")
        assert store.remove_pending_entry(source.session_id)
        assert not (store.root / source.session_id).exists()
        assert not (store.staging_root / source.session_id).exists()
        assert store.remove_pending_entry(_sid())  # nothing there: done
        assert store.remove_pending_entry("not-a-session-id")

    def test_a_key_that_cannot_be_removed_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = _store(tmp_path)
        source = _source()
        store.write_entry(source, LINKED)
        real_unlink = Path.unlink

        def locked(self: Path, missing_ok: bool = False) -> None:
            if self.name == KEY_FILENAME:
                raise PermissionError(errno.EACCES, "in use")
            real_unlink(self, missing_ok=missing_ok)

        monkeypatch.setattr(Path, "unlink", locked)
        assert store.remove_pending_entry(source.session_id) is False
        monkeypatch.undo()
        assert (store.root / source.session_id / TRANSCRIPT_FILENAME).exists()

    def test_an_entry_whose_link_status_cannot_be_read_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """H1 round 32 LOW-001: "an error counts as a link" must not become
        "nothing to remove" — True would let the destroyer delete the SOURCE
        key while a pending entry stays, for reconciliation to commit."""
        store = _store(tmp_path)
        source = _source()
        store.write_entry(source, LINKED)
        entry = store.root / source.session_id
        real_lstat = os.lstat

        def uninspectable(path: Any, *args: Any, **kwargs: Any) -> os.stat_result:
            # H3 round 35 SEC-001: the status is read with ONE os.lstat —
            # Path.is_symlink swallows this error from Python 3.13.
            if Path(path) == entry:
                raise PermissionError(errno.EACCES, "in use")
            return real_lstat(path, *args, **kwargs)

        monkeypatch.setattr(os, "lstat", uninspectable)
        assert store.remove_pending_entry(source.session_id) is False
        monkeypatch.undo()
        assert (entry / KEY_FILENAME).exists() and (entry / PENDING_FILENAME).exists()
        assert store.remove_pending_entry(source.session_id)
        assert not entry.exists()

    def test_a_staging_folder_whose_link_status_cannot_be_read_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Hardening review round 41 LOW-003: the same rule one level up —
        "``.staging`` cannot be inspected" must not skip the staging copy and
        answer True, or the destroyer deletes the SOURCE key while a staging
        copy (since 0.3.0 possibly with a kept recording's audio) stays."""
        store = _store(tmp_path)
        source = _source()
        staged = store.staging_root / source.session_id
        staged.mkdir(parents=True)
        (staged / KEY_FILENAME).write_bytes(b"k")
        staging_root = store.staging_root
        real_lstat = os.lstat

        def uninspectable(path: Any, *args: Any, **kwargs: Any) -> os.stat_result:
            if Path(path) == staging_root:
                raise PermissionError(errno.EACCES, "in use")
            return real_lstat(path, *args, **kwargs)

        monkeypatch.setattr(os, "lstat", uninspectable)
        assert store.remove_pending_entry(source.session_id) is False
        monkeypatch.undo()
        assert (staged / KEY_FILENAME).exists()
        assert store.remove_pending_entry(source.session_id)
        assert not staged.exists()

    def test_link_state_reads_a_real_folder_a_missing_one_and_an_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.session_store import link_state

        assert link_state(tmp_path) is False
        assert link_state(tmp_path / "absent") is False

        def denied(_path: Any, *_args: Any, **_kwargs: Any) -> os.stat_result:
            raise PermissionError(errno.EACCES, "in use")

        monkeypatch.setattr(os, "lstat", denied)
        assert link_state(tmp_path) is None

    def test_reconcile_commits_only_on_a_confirmed_absent_source_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sessions = tmp_path / "sessions"
        store = _store(tmp_path)
        live, gone, locked = _source(), _source(), _source()
        for source in (live, gone, locked):
            store.write_entry(source, LINKED)
        for source in (live, locked):
            (sessions / source.session_id).mkdir(parents=True)
            (sessions / source.session_id / KEY_FILENAME).write_bytes(b"\0" * 64)
        real_stat = Path.stat

        def inaccessible(self: Path, **kwargs: Any) -> os.stat_result:
            if self == sessions / locked.session_id / KEY_FILENAME:
                raise PermissionError(errno.EACCES, "in use")
            return real_stat(self, **kwargs)

        monkeypatch.setattr(Path, "stat", inaccessible)
        # Round 12 LOW-002 (Task 3.2): the ids it committed, for the audit.
        assert store.reconcile_pending(sessions) == [gone.session_id]
        monkeypatch.undo()
        assert [listing.session_id for listing in store.list_entries()] == [gone.session_id]
        assert (store.root / live.session_id / PENDING_FILENAME).exists()
        assert (store.root / locked.session_id / PENDING_FILENAME).exists()

    def test_reconcile_removes_a_keyless_leftover(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        sid = _published(store)
        (store.root / sid / KEY_FILENAME).unlink()
        assert store.reconcile_pending(tmp_path / "sessions") == []
        assert not (store.root / sid).exists()

    def test_clean_staging_removes_only_session_folders(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        crashed = store.staging_root / _sid()
        crashed.mkdir(parents=True)
        (crashed / KEY_FILENAME).write_bytes(b"k")
        (crashed / TRANSCRIPT_FILENAME).write_bytes(b"t")
        foreign = store.staging_root / "not-ours"
        foreign.mkdir()
        assert store.clean_staging() == 1
        assert not crashed.exists() and foreign.exists()
        assert _store(tmp_path / "empty").clean_staging() == 0


# ---------------------------------------------------------------------------
# Links are never followed (codex round 13 PR-LOW-010).
# ---------------------------------------------------------------------------


def _link(kind: str, link: Path, target: Path) -> None:
    """A directory link at ``link`` to ``target``, all under ``tmp_path``
    (C6). A junction needs no privilege on Windows (``_winapi``, CPython's
    own helper) and exists nowhere else; a directory symlink needs Windows
    Developer Mode or admin — the test SKIPS, naming which, when this host
    cannot make the kind asked for."""
    if kind == "junction":
        if sys.platform != "win32":
            pytest.skip("directory junctions exist only on Windows")
        import _winapi

        _winapi.CreateJunction(str(target), str(link))
        return
    try:
        os.symlink(target, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("this host cannot create a directory symlink (no privilege)")


@pytest.mark.parametrize("kind", ["junction", "symlink"])
class TestLinksAreNeverFollowed:
    def test_a_linked_staging_child_is_skipped(self, tmp_path: Path, kind: str) -> None:
        store = _store(tmp_path)
        sid = _published(store)
        store.staging_root.mkdir(parents=True, exist_ok=True)
        link = store.staging_root / sid
        _link(kind, link, store.root / sid)
        assert store.clean_staging() == 0
        assert (store.root / sid / KEY_FILENAME).exists()  # the committed target survives
        assert os.path.lexists(link)  # left in place, untouched
        assert store.remove_pending_entry(_sid())
        assert [listing.session_id for listing in store.list_entries()] == [sid]

    def test_a_linked_staging_folder_stops_all_staging(self, tmp_path: Path, kind: str) -> None:
        """``.staging`` linked to the archive root would make every staging
        path an ENTRY path: cleanup would destroy every committed key."""
        store = _store(tmp_path)
        sid = _published(store)
        store.staging_root.rmdir()  # publishing left it empty
        _link(kind, store.staging_root, store.root)  # .staging -> the archive itself
        assert store.clean_staging() == 0
        assert (store.root / sid / KEY_FILENAME).exists()
        with pytest.raises(PastSessionError) as info:
            store.write_entry(_source(), LINKED)
        assert info.value.reason == "write_failed"
        assert (store.root / sid / KEY_FILENAME).exists()
        assert store.remove_pending_entry(_sid())  # skips the linked staging side
        assert (store.root / sid / KEY_FILENAME).exists()
        assert [listing.session_id for listing in store.list_entries()] == [sid]
        assert os.path.lexists(store.staging_root)

    def test_a_linked_entry_is_not_an_entry(self, tmp_path: Path, kind: str) -> None:
        store = _store(tmp_path)
        sid = _published(store)
        other = _sid()
        link = store.root / other
        _link(kind, link, store.root / sid)
        assert [listing.session_id for listing in store.list_entries()] == [sid]
        for action in (store.delete_entry, store.read_entry):
            with pytest.raises(PastSessionError) as info:
                action(other)
            assert info.value.reason == "not_found"
        assert store.remove_pending_entry(other)  # not ours: nothing to remove
        assert store.commit(other) is False
        assert store.reconcile_pending(tmp_path / "sessions") == []
        # Only the real one (the 7-year minimum: a date past the window).
        assert store.sweep(SEVEN, NOW + WINDOW + timedelta(days=30)) == [sid]
        assert os.path.lexists(link)

    def test_a_linked_entry_blocks_a_publish_under_its_id(
        self, tmp_path: Path, kind: str
    ) -> None:
        store = _store(tmp_path)
        sid = _published(store)
        source = _source()
        _link(kind, store.root / source.session_id, store.root / sid)
        with pytest.raises(PastSessionError) as info:
            store.write_entry(source, LINKED)
        assert info.value.reason == "publish_failed"
        assert (store.root / sid / KEY_FILENAME).exists()
        assert list(store.staging_root.iterdir()) == []


# ---------------------------------------------------------------------------
# Reading and deleting.
# ---------------------------------------------------------------------------


class TestReadAndDelete:
    def test_an_unreadable_label_is_still_listed_so_it_can_be_deleted(
        self, tmp_path: Path
    ) -> None:
        store = _store(tmp_path)
        sid = _published(store)
        (store.root / sid / LABEL_FILENAME).write_bytes(b"\0" * 64)
        [listing] = store.list_entries()
        assert (listing.session_id, listing.label) == (sid, None)
        with pytest.raises(PastSessionError) as info:
            store.read_entry(sid)
        assert info.value.reason == "unreadable"
        store.delete_entry(sid)
        assert store.list_entries() == []

    def test_a_key_this_account_cannot_open_is_unreadable(self, tmp_path: Path) -> None:
        sid = _published(_store(tmp_path))

        def refuse(_directory: Path) -> SessionCrypto:
            raise KeyCustodyError("another account's key")

        store = _store(tmp_path, unwrap_key=refuse)
        with pytest.raises(PastSessionError) as info:
            store.read_entry(sid)
        assert info.value.reason == "unreadable"
        assert [listing.label for listing in store.list_entries()] == [None]

    def test_delete_removes_the_key_first(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = _store(tmp_path)
        sid = _published(store)
        order: list[str] = []
        real_rmtree = past_sessions.shutil.rmtree

        def rmtree(path: Path, ignore_errors: bool = False) -> None:
            order.append("rmtree" if not (Path(path) / KEY_FILENAME).exists() else "LEAK")
            real_rmtree(path, ignore_errors=ignore_errors)

        monkeypatch.setattr(past_sessions.shutil, "rmtree", rmtree)
        store.delete_entry(sid)
        assert order == ["rmtree"]
        with pytest.raises(PastSessionError) as info:
            store.delete_entry(sid)
        assert info.value.reason == "not_found"
        with pytest.raises(PastSessionError):
            store.read_entry("../escape")


# ---------------------------------------------------------------------------
# The retention sweep (Flow 4).
# ---------------------------------------------------------------------------


class TestRetentionSweep:
    def test_never_deletes_and_decrypts_nothing(self, tmp_path: Path) -> None:
        _published(_store(tmp_path, clock=NOW - timedelta(days=4000)))
        unwraps = _Unwraps()
        store = _store(tmp_path, unwrap_key=unwraps)
        assert store.sweep(None, NOW) == []
        assert unwraps.calls == 0
        assert len(store.list_entries()) == 1

    def test_only_entries_past_the_window_go(self, tmp_path: Path) -> None:
        old = _published(_store(tmp_path, clock=NOW - WINDOW - timedelta(days=1)))
        fresh = _published(_store(tmp_path, clock=NOW - WINDOW + timedelta(days=1)))
        future = _published(_store(tmp_path, clock=NOW + timedelta(days=3)))
        pending = _source()
        _store(tmp_path, clock=NOW - WINDOW - timedelta(days=30)).write_entry(pending, LINKED)
        undated = _published(_store(tmp_path, clock=NOW - WINDOW - timedelta(days=30)))
        store = _store(tmp_path)
        (store.root / undated / LABEL_FILENAME).write_bytes(b"\0" * 64)
        assert store.sweep(SEVEN, NOW) == [old]
        remaining = {listing.session_id for listing in store.list_entries()}
        assert remaining == {fresh, future, undated}
        assert (store.root / pending.session_id / KEY_FILENAME).exists()

    def test_each_label_is_decrypted_once_per_process(self, tmp_path: Path) -> None:
        """Round 11 MED-001: the hourly tick decrypts a committed entry's
        label for its date once, not every tick; an entry this store
        rewrites or removes is read afresh."""
        kept = _published(_store(tmp_path, clock=NOW - timedelta(days=2)))
        other = _published(_store(tmp_path, clock=NOW - timedelta(days=3)))
        unwraps = _Unwraps()
        store = _store(tmp_path, unwrap_key=unwraps)
        assert store.sweep(SEVEN, NOW) == []
        assert unwraps.calls == 2
        assert store.sweep(SEVEN, NOW) == []
        assert unwraps.calls == 2  # the dates came from memory
        assert store.remove_pending_entry(other)  # any removal forgets the date
        assert store.sweep(SEVEN, NOW) == []
        assert unwraps.calls == 2
        assert store.sweep(SEVEN, NOW + WINDOW) == [kept]  # a cached date still expires
        assert unwraps.calls == 2
        assert store._completed_dates == {}  # noqa: SLF001

    def test_an_undated_entry_is_read_again_a_day_later(self, tmp_path: Path) -> None:
        """H1 round 32 LOW-004: an unreadable label is not unwrapped again
        on every hourly tick — it is kept, still counted, and tried again
        ``UNDATED_RETRY_INTERVAL`` after it failed (or at once if the clock
        went back)."""
        sid = _published(_store(tmp_path, clock=NOW - WINDOW - timedelta(days=30)))
        unwraps = _Unwraps()
        store = _store(tmp_path, unwrap_key=unwraps)
        label = (store.root / sid / LABEL_FILENAME).read_bytes()
        (store.root / sid / LABEL_FILENAME).write_bytes(b"\0" * 64)
        report = store.sweep_report(SEVEN, NOW)
        # Round 17 LOW-020: counted, so the tab can say it is kept by age.
        assert (report.expired, report.undated, report.problem) == ((), 1, False)
        assert unwraps.calls == 1
        (store.root / sid / LABEL_FILENAME).write_bytes(label)
        hourly = store.sweep_report(SEVEN, NOW + timedelta(hours=23))
        assert (hourly.expired, hourly.undated) == ((), 1)  # still counted
        assert unwraps.calls == 1  # not unwrapped again within the interval
        assert store.sweep(SEVEN, NOW + past_sessions.UNDATED_RETRY_INTERVAL) == [sid]
        assert unwraps.calls == 2

    def test_an_undated_entry_is_read_again_when_the_clock_goes_back(
        self, tmp_path: Path
    ) -> None:
        sid = _published(_store(tmp_path, clock=NOW - WINDOW - timedelta(days=30)))
        unwraps = _Unwraps()
        store = _store(tmp_path, unwrap_key=unwraps)
        label = (store.root / sid / LABEL_FILENAME).read_bytes()
        (store.root / sid / LABEL_FILENAME).write_bytes(b"\0" * 64)
        assert store.sweep_report(SEVEN, NOW).undated == 1
        (store.root / sid / LABEL_FILENAME).write_bytes(label)
        assert store.sweep(SEVEN, NOW - timedelta(minutes=1)) == [sid]
        assert unwraps.calls == 2

    def test_a_failed_delete_keeps_the_remembered_date(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """H1 round 32 LOW-004's sibling: an entry whose key could not be
        deleted is intact, so its date is not read again on the next tick."""
        sid = _published(_store(tmp_path, clock=NOW - WINDOW - timedelta(days=30)))
        unwraps = _Unwraps()
        store = _store(tmp_path, unwrap_key=unwraps)
        monkeypatch.setattr(past_sessions, "_remove_key_first", lambda _directory: False)
        assert store.sweep_report(SEVEN, NOW).failed == 1
        assert store.sweep_report(SEVEN, NOW).failed == 1
        assert unwraps.calls == 1
        monkeypatch.undo()
        assert store.sweep(SEVEN, NOW) == [sid]
        assert unwraps.calls == 1

    def test_an_entry_exactly_at_the_window_goes(self, tmp_path: Path) -> None:
        sid = _published(_store(tmp_path, clock=NOW - WINDOW))
        just_inside = _published(_store(tmp_path, clock=NOW - WINDOW + timedelta(seconds=1)))
        assert _store(tmp_path).sweep(SEVEN, NOW) == [sid]
        assert [listing.session_id for listing in _store(tmp_path).list_entries()] == [
            just_inside
        ]

    def test_the_choices_are_the_offered_settings(self) -> None:
        """Practitioner decision 2026-10-02: 7 years minimum — the one window
        offered (2557 days: seven years and two leap days); the shorter ones
        an earlier build offered are the legacy set, never a choice."""
        assert MIN_RETENTION_DAYS == 7 * 365 + 2 == 2557
        assert RETENTION_DAYS_CHOICES == (2557,)
        assert LEGACY_RETENTION_DAYS == frozenset({1, 7, 30, 90, 365})
        assert not LEGACY_RETENTION_DAYS & set(RETENTION_DAYS_CHOICES)

    @pytest.mark.parametrize("days", [0, -1, 1, 7, 30, 90, 365, MIN_RETENTION_DAYS - 1])
    def test_a_window_under_seven_years_is_refused_and_deletes_nothing(
        self, tmp_path: Path, days: int, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The second line behind the settings file (practitioner decision
        2026-10-02): a direct store call with a window shorter than 7 years
        reads no label, deletes nothing, says so (``too_short``, a fixed
        ``retention_too_short`` log code with no id) and never raises."""
        import logging

        old = _published(_store(tmp_path, clock=NOW - WINDOW - timedelta(days=400)))
        unwraps = _Unwraps()
        logger = logging.getLogger("test.past_sessions.too_short")
        store = _store(tmp_path, unwrap_key=unwraps, logger=logger)
        with caplog.at_level(logging.INFO, logger=logger.name):
            report = store.sweep_report(days, NOW)
            assert store.sweep(days, NOW) == []
        assert report == past_sessions.RetentionSweepReport(too_short=True)
        assert not report.problem
        assert unwraps.calls == 0
        assert (store.root / old / KEY_FILENAME).exists()
        assert [r.getMessage() for r in caplog.records] == [
            "past_session detail_code=retention_too_short"
        ] * 2
        # The 7-year window itself still deletes it.
        assert store.sweep(SEVEN, NOW) == [old]

    def test_the_report_dates_each_deletion_and_counts_what_could_not_go(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 16 MED-002 / LOW-005: an entry due but not deletable is
        counted (``problem``), never reported as expired; each one deleted
        carries its completion date."""
        completed = NOW - WINDOW - timedelta(days=2)
        sid = _published(_store(tmp_path, clock=completed))
        store = _store(tmp_path)
        monkeypatch.setattr(past_sessions, "_remove_key_first", lambda _directory: False)
        report = store.sweep_report(SEVEN, NOW)
        assert (report.expired, report.failed, report.complete) == ((), 1, True)
        assert report.problem
        monkeypatch.undo()
        report = store.sweep_report(SEVEN, NOW)
        assert report.expired == ((sid, completed),)
        assert not report.problem
        assert not past_sessions.RetentionSweepReport().problem  # "never"

    def test_an_archive_that_cannot_be_listed_is_reported_never_empty(
        self, tmp_path: Path
    ) -> None:
        """Round 16 LOW-003: the listing raises and the sweep reports an
        unfinished walk; a MISSING archive is still simply empty."""
        assert _store(tmp_path).list_entries() == []
        assert not _store(tmp_path).sweep_report(SEVEN, NOW).problem
        (tmp_path / "past_sessions").write_bytes(b"")  # not a folder
        store = _store(tmp_path)
        with pytest.raises(PastSessionError) as info:
            store.list_entries()
        assert info.value.reason == "unreadable"
        report = store.sweep_report(SEVEN, NOW)
        assert (report.expired, report.complete, report.problem) == ((), False, True)
        assert store.sweep_report(None, NOW).problem is False  # "never" walks nothing


# ---------------------------------------------------------------------------
# The settings file.
# ---------------------------------------------------------------------------


class TestSettings:
    def test_absent_is_the_defaults(self, tmp_path: Path) -> None:
        settings = load_past_session_settings(tmp_path)
        assert (settings.retention_days, settings.hide_names) == (None, False)

    def test_round_trip(self, tmp_path: Path) -> None:
        saved = PastSessionSettings(retention_days=SEVEN, hide_names=True)
        path = save_past_session_settings(saved, config_root=tmp_path / "config")
        assert path.name == "past_sessions.json"
        assert load_past_session_settings(tmp_path / "config") == saved
        assert read_past_session_settings(tmp_path / "config").retention_raised is False

    @pytest.mark.parametrize("days", [None, *RETENTION_DAYS_CHOICES])
    def test_every_valid_stored_file_still_loads_under_strict(
        self, tmp_path: Path, days: int | None
    ) -> None:
        import json

        blob = json.dumps({"schema_version": 1, "retention_days": days, "hide_names": True})
        (tmp_path / "past_sessions.json").write_text(blob, encoding="utf-8")
        settings = load_past_session_settings(tmp_path)
        assert (settings.retention_days, settings.hide_names) == (days, True)
        assert read_past_session_settings(tmp_path).retention_raised is False

    @pytest.mark.parametrize("days", sorted(LEGACY_RETENTION_DAYS))
    @pytest.mark.parametrize("hide", [False, True])
    def test_a_removed_shorter_window_loads_as_seven_years(
        self, tmp_path: Path, days: int, hide: bool
    ) -> None:
        """Practitioner decision 2026-10-02 (the upgrade): a file an earlier
        build wrote with 1, 7, 30 or 90 days or 1 year LOADS — never a
        fail-closed reset that stops the sweep and Hide names — as 7 years,
        says it was raised, and is not rewritten by the read; the next save
        writes 7 years and reads back as not raised."""
        import json

        config = tmp_path / "config"
        config.mkdir()
        blob = json.dumps({"schema_version": 1, "retention_days": days, "hide_names": hide})
        (config / "past_sessions.json").write_text(blob, encoding="utf-8")
        read = read_past_session_settings(config)
        assert read.retention_raised is True
        assert (read.settings.retention_days, read.settings.hide_names) == (SEVEN, hide)
        assert load_past_session_settings(config) == read.settings
        assert (config / "past_sessions.json").read_text(encoding="utf-8") == blob
        save_past_session_settings(read.settings, config_root=config)
        stored = json.loads((config / "past_sessions.json").read_text(encoding="utf-8"))
        assert stored["retention_days"] == SEVEN
        again = read_past_session_settings(config)
        assert (again.settings, again.retention_raised) == (read.settings, False)

    @pytest.mark.parametrize(
        "blob",
        [
            b'{"schema_version": 1, "retention_days": 5, "hide_names": false}',
            # Not offered, and not a removed window: still fails closed.
            b'{"schema_version": 1, "retention_days": 2556, "hide_names": false}',
            b'{"schema_version": 1, "retention_days": 2558, "hide_names": false}',
            b'{"schema_version": 1, "retention_days": 0, "hide_names": false}',
            b'{"schema_version": 1, "retention_days": -7, "hide_names": false}',
            # A removed window in the wrong type is refused, never raised.
            b'{"schema_version": 1, "retention_days": 7.0, "hide_names": false}',
            b'{"schema_version": 1, "retention_days": "30", "hide_names": false}',
            b'{"schema_version": 1, "retention_days": [365], "hide_names": false}',
            b'{"schema_version": 2, "retention_days": null, "hide_names": false}',
            b'{"schema_version": 1, "retention_days": null, "hide_names": false, "x": 1}',
            b"not json",
            # Round 13 PR-LOW-011: strict — no lax coercion to a valid choice.
            b'{"schema_version": 1, "retention_days": true, "hide_names": false}',
            b'{"schema_version": 1, "retention_days": 1.0, "hide_names": false}',
            b'{"schema_version": 1, "retention_days": "7", "hide_names": false}',
            b'{"schema_version": 1, "retention_days": null, "hide_names": "true"}',
            b'{"schema_version": 1, "retention_days": null, "hide_names": 1}',
        ],
    )
    def test_an_invalid_file_is_an_error_never_a_default(
        self, tmp_path: Path, blob: bytes
    ) -> None:
        (tmp_path / "past_sessions.json").write_bytes(blob)
        with pytest.raises(PastSessionSettingsError):
            load_past_session_settings(tmp_path)

    def test_an_unreadable_file_is_an_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "past_sessions.json").write_bytes(b"{}")
        real = Path.open

        def locked(self: Path, *args: Any, **kwargs: Any) -> Any:
            if self.name == "past_sessions.json":
                raise PermissionError(errno.EACCES, "in use")
            return real(self, *args, **kwargs)

        monkeypatch.setattr(Path, "open", locked)
        with pytest.raises(PastSessionSettingsError, match="could not be read"):
            load_past_session_settings(tmp_path)

    def test_an_oversized_file_is_an_error_never_read_whole(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """H3 round 35 SEC-005, made provable by round 37 PR-LOW-031: VALID
        settings padded with JSON whitespace — so only the bound can refuse
        them — one byte over the cap are refused; padded to exactly the cap
        they load; no read asks for more than cap + 1 bytes."""
        from conftest import bounded_read_spy

        cap = past_sessions.MAX_SETTINGS_FILE_BYTES
        valid = b'{"schema_version": 1, "retention_days": 2557, "hide_names": true}'
        path = tmp_path / "past_sessions.json"
        sizes = bounded_read_spy(monkeypatch, path.name)
        path.write_bytes(valid.ljust(cap + 1))
        with pytest.raises(PastSessionSettingsError, match="is not valid"):
            load_past_session_settings(tmp_path)
        path.write_bytes(valid.ljust(cap))
        settings = load_past_session_settings(tmp_path)
        assert (settings.retention_days, settings.hide_names) == (SEVEN, True)
        assert sizes == [cap + 1, cap + 1]

    def test_the_label_bound_applies_to_a_valid_label_before_it_is_read(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 37 PR-LOW-031, the sibling cap: an otherwise-VALID
        ``label.enc`` one byte over ``MAX_LABEL_FILE_BYTES`` lists as
        unreadable, at the cap it reads, and no read asks for more than
        cap + 1 bytes."""
        from conftest import bounded_read_spy

        store = _store(tmp_path)
        sid = _published(store)
        size = (store.root / sid / LABEL_FILENAME).stat().st_size
        sizes = bounded_read_spy(monkeypatch, LABEL_FILENAME)
        monkeypatch.setattr(past_sessions, "MAX_LABEL_FILE_BYTES", size - 1)
        assert [(item.session_id, item.label) for item in store.list_entries()] == [(sid, None)]
        monkeypatch.setattr(past_sessions, "MAX_LABEL_FILE_BYTES", size)
        [listing] = store.list_entries()
        assert listing.label is not None and listing.label.session_id == sid
        assert sizes == [size, size + 1]


# ---------------------------------------------------------------------------
# The Complete that keeps (Task 2.3; C1's ordering through complete_session).
# ---------------------------------------------------------------------------


class TestCompleteKeeps:
    def test_the_entry_is_published_before_the_key_and_committed_after(
        self, tmp_path: Path
    ) -> None:
        store = _store(tmp_path)
        directory, crypto = _session(tmp_path / "sessions")
        seen: list[str] = []
        keeper = store.keeper(LINKED)
        real_write, real_commit = keeper.write, keeper.commit

        def write(source: ArchiveSource) -> None:
            seen.append(f"write key={(directory / KEY_FILENAME).exists()}")
            real_write(source)

        def commit(session_id: str) -> bool:
            seen.append(f"commit key={(directory / KEY_FILENAME).exists()}")
            return real_commit(session_id)

        keeper.write = write  # type: ignore[method-assign]
        keeper.commit = commit  # type: ignore[method-assign]
        facts = complete_session(directory, crypto, keep=keeper)
        assert seen == ["write key=True", "commit key=False"]
        assert (facts.past_session, facts.commit_deferred) == ("archived", False)
        assert not directory.exists()
        entry = store.read_entry(directory.name)
        assert (entry.label.has_saved, entry.label.has_generated) == (True, True)
        assert entry.generated is not None
        assert entry.generated.generated_text.startswith("Subjective")

    @pytest.mark.parametrize(
        "session",
        [
            {"model_name": "mock"},
            {"generated_provider": "mock-extractive"},
            {"note_provider": "Mock-behaviour"},
        ],
        ids=["transcript", "generated", "note"],
    )
    def test_a_mock_session_keeps_nothing(self, tmp_path: Path, session: Any) -> None:
        store = _store(tmp_path)
        directory, crypto = _session(tmp_path / "sessions", **session)
        facts = complete_session(directory, crypto, keep=store.keeper(LINKED))
        assert facts.past_session == "not_kept_mock"
        assert not store.root.exists()
        assert not directory.exists()

    def test_a_mock_complete_removes_an_earlier_attempts_entry_before_the_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """H1 round 32 LOW-002: attempt 1 published a pending entry and
        failed at the key; attempt 2 decides the session is mock. It keeps
        nothing — so the entry goes, key first, BEFORE the source key, and
        reconciliation has nothing to commit."""
        store = _store(tmp_path)
        directory, crypto = _session(tmp_path / "sessions")

        def refuse(_directory: Path) -> None:
            raise PermissionError(errno.EACCES, "in use")

        monkeypatch.setattr(session_store, "delete_session_key", refuse)
        with pytest.raises(PermissionError):
            complete_session(directory, crypto, keep=store.keeper(LINKED))
        monkeypatch.undo()
        assert (store.root / directory.name / PENDING_FILENAME).exists()
        monkeypatch.setattr(session_store, "_is_mock_session", lambda *_args: True)
        order: list[str] = []
        keeper = store.keeper(LINKED)
        real_drop = keeper.drop_unfinished

        def drop(session_id: str) -> bool:
            order.append(f"drop key={(directory / KEY_FILENAME).exists()}")
            return real_drop(session_id)

        keeper.drop_unfinished = drop  # type: ignore[method-assign]
        facts = complete_session(directory, crypto, keep=keeper)
        assert facts.past_session == "not_kept_mock"
        assert order == ["drop key=True"]
        assert not (store.root / directory.name).exists()
        assert store.reconcile_pending(directory.parent) == []
        assert store.list_entries() == []

    def test_a_mock_complete_that_cannot_drop_the_entry_keeps_the_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = _store(tmp_path)
        directory, crypto = _session(tmp_path / "sessions", model_name="mock")
        monkeypatch.setattr(store, "remove_pending_entry", lambda _sid: False)
        with pytest.raises(ArchiveWriteError, match="key retained"):
            complete_session(directory, crypto, keep=store.keeper(LINKED))
        assert (directory / KEY_FILENAME).exists() and not crypto.destroyed

    def test_an_archive_failure_keeps_the_key_and_a_retry_leaves_one_entry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = _store(tmp_path)
        directory, crypto = _session(tmp_path / "sessions")

        def refuse(_src: Any, _dst: Any) -> None:
            raise PermissionError(errno.EACCES, "in use")

        monkeypatch.setattr(past_sessions.os, "rename", refuse)
        with pytest.raises(ArchiveWriteError, match="key retained"):
            complete_session(directory, crypto, keep=store.keeper(LINKED))
        assert (directory / KEY_FILENAME).exists() and not crypto.destroyed
        monkeypatch.undo()
        complete_session(directory, crypto, keep=store.keeper(LINKED))
        assert [listing.session_id for listing in store.list_entries()] == [directory.name]

    def test_a_failure_at_the_key_leaves_a_pending_entry_a_discard_removes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = _store(tmp_path)
        directory, crypto = _session(tmp_path / "sessions")

        def refuse(_directory: Path) -> None:
            raise PermissionError(errno.EACCES, "in use")

        monkeypatch.setattr(session_store, "delete_session_key", refuse)
        with pytest.raises(PermissionError):
            complete_session(directory, crypto, keep=store.keeper(LINKED))
        monkeypatch.undo()
        assert store.list_entries() == []
        assert store.reconcile_pending(directory.parent) == []  # the source key is there
        assert store.remove_pending_entry(directory.name)  # the Discard's hook
        session_store.discard_session(directory, crypto)
        assert store.reconcile_pending(directory.parent) == []
        assert not (store.root / directory.name).exists()

    def test_a_commit_that_fails_is_deferred_to_reconciliation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = _store(tmp_path)
        directory, crypto = _session(tmp_path / "sessions")
        keeper = store.keeper(LINKED)
        monkeypatch.setattr(keeper, "commit", lambda _sid: False)
        facts = complete_session(directory, crypto, keep=keeper)
        assert (facts.past_session, facts.commit_deferred) == ("archived", True)
        assert not (directory / KEY_FILENAME).exists()
        assert store.list_entries() == []
        assert store.reconcile_pending(directory.parent) == [directory.name]
        assert [listing.session_id for listing in store.list_entries()] == [directory.name]

    def test_a_commit_that_raises_is_deferred_never_raised(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        directory, crypto = _session(tmp_path / "sessions")
        keeper = store.keeper(LINKED)

        def boom(_sid: str) -> bool:
            raise OSError("disk gone")

        keeper.commit = boom  # type: ignore[method-assign]
        assert complete_session(directory, crypto, keep=keeper).commit_deferred

    def test_the_delete_note_path_keeps_no_note(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        directory, crypto = _session(tmp_path / "sessions")
        facts = complete_session(directory, crypto, delete_note=True, keep=store.keeper(LINKED))
        assert facts.past_session == "archived"
        entry = store.read_entry(directory.name)
        assert entry.saved_note is None and not entry.label.has_saved
        assert not (store.root / directory.name / NOTE_FILENAME).exists()

    def test_an_unreadable_generated_note_is_not_kept(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        directory, crypto = _session(tmp_path / "sessions")
        (directory / GENERATED_FILENAME).write_bytes(b"\0" * 64)
        facts = complete_session(directory, crypto, keep=store.keeper(LINKED))
        assert facts.generated_provider == "unknown"
        entry = store.read_entry(directory.name)
        assert entry.generated is None and not entry.label.has_generated

    def test_an_unresolvable_identity_keeps_the_key(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        directory, crypto = _session(tmp_path / "sessions", note_provider=None)
        renamed = directory.with_name("not-a-session-id")
        directory.rename(renamed)
        with pytest.raises(ArchiveWriteError):
            complete_session(renamed, crypto, keep=store.keeper(LINKED))
        assert (renamed / KEY_FILENAME).exists()

    def test_a_header_id_that_is_not_the_directory_keeps_the_key(self, tmp_path: Path) -> None:
        """Round 11 LOW-001: every destroyer names the source by its
        directory, so an entry is only ever kept under that name — a session
        whose audio header names another id is not archived."""
        from scribe_desktop.session_store import SessionChunkStore

        store = _store(tmp_path)
        directory, crypto = _session(
            tmp_path / "sessions", note_provider=None, generated_provider=None
        )
        audio = SessionChunkStore.create(directory / "audio.enc", crypto, _sid())
        audio.append_chunk(b"\0\1" * 8)
        audio.finish()
        audio.close()
        with pytest.raises(ArchiveWriteError, match="not its directory"):
            complete_session(directory, crypto, keep=store.keeper(LINKED))
        assert (directory / KEY_FILENAME).exists() and not crypto.destroyed
        assert not store.root.exists()

    def test_no_keeper_keeps_nothing(self, tmp_path: Path) -> None:
        directory, crypto = _session(tmp_path / "sessions")
        facts = complete_session(directory, crypto)
        assert facts.past_session == "none"
        assert facts.generated_provider == "extractive-v1"
        assert facts.generated_style == "verbatim"


# ---------------------------------------------------------------------------
# The expiry sweep's C1 hook (Task 2.3).
# ---------------------------------------------------------------------------

_OLD = 1_700_000_000.0


def _aged(root: Path, *, key: bytes | None = b"\0" * 64) -> Path:
    directory = root / _sid()
    directory.mkdir(parents=True)
    if key is not None:
        (directory / KEY_FILENAME).write_bytes(key)
        os.utime(directory / KEY_FILENAME, (_OLD, _OLD))
    os.utime(directory, (_OLD, _OLD))
    return directory


class TestSweepHook:
    @pytest.mark.parametrize("key", [b"\0" * 64, b""], ids=["expired", "dead_key"])
    def test_the_hook_runs_before_the_key_goes(self, tmp_path: Path, key: bytes) -> None:
        directory = _aged(tmp_path, key=key)
        seen: list[bool] = []

        def hook(session_id: str) -> bool:
            assert session_id == directory.name
            seen.append((directory / KEY_FILENAME).exists())
            return True

        [result] = sweep_sessions(tmp_path, now=_OLD + 2 * 86_400, before_destroy=hook)
        assert seen == [True]
        assert result.action in {"expired", "orphan_gc"}
        assert not directory.exists()

    @pytest.mark.parametrize("key", [b"\0" * 64, b""], ids=["expired", "dead_key"])
    @pytest.mark.parametrize("outcome", ["false", "raise"])
    def test_a_hook_that_fails_keeps_the_key(
        self, tmp_path: Path, key: bytes, outcome: str
    ) -> None:
        directory = _aged(tmp_path, key=key)

        def hook(_session_id: str) -> bool:
            if outcome == "raise":
                raise OSError("locked")
            return False

        [result] = sweep_sessions(tmp_path, now=_OLD + 2 * 86_400, before_destroy=hook)
        assert (result.action, result.created_at) == ("error", None)
        assert (directory / KEY_FILENAME).exists()

    def test_a_confirmed_absent_key_calls_no_hook(self, tmp_path: Path) -> None:
        directory = _aged(tmp_path, key=None)

        def hook(_session_id: str) -> bool:
            raise AssertionError("an absent key's entry is committed, never removed")

        [result] = sweep_sessions(tmp_path, now=_OLD + 2 * 86_400, before_destroy=hook)
        assert result.action == "orphan_gc"
        assert not directory.exists()

    def test_a_kept_session_calls_no_hook(self, tmp_path: Path) -> None:
        _aged(tmp_path)

        def hook(_session_id: str) -> bool:
            raise AssertionError("nothing is destroyed")

        [result] = sweep_sessions(tmp_path, now=_OLD + 60, before_destroy=hook)
        assert result.action == "kept"


@pytest.mark.parametrize("kind", ["junction", "symlink"])
class TestSessionLinksAreNeverFollowed:
    """H3 round 35 SEC-002 (carried from round 13 LEG 1): round 13's class,
    closed for the SESSIONS root. A session-id-named link under it — to
    another session's folder, or a Past-sessions entry's — is never swept,
    keyed away, discarded or listed: Windows resolves it mid-path, so
    ``<link>\\key.dpapi`` would be the target's key.

    Every test ends with a POSITIVE control: the same target folder, reached
    directly, is accepted by the same path — so the refusal is the link's,
    never a real folder's (leg f4: the first recovery-list control used an
    expired target and so proved nothing)."""

    def _linked(self, tmp_path: Path, kind: str, *, aged: bool = True) -> tuple[Path, Path, Path]:
        if aged:
            target = _aged(tmp_path / "elsewhere")
        else:  # within the 24 h recovery window: a session the listing offers
            target = tmp_path / "elsewhere" / _sid()
            target.mkdir(parents=True)
            (target / KEY_FILENAME).write_bytes(b"\0" * 64)
        sessions = tmp_path / "sessions"
        sessions.mkdir()
        link = sessions / _sid()
        _link(kind, link, target)
        return sessions, link, target

    def test_link_state_reads_the_link_and_never_its_target(
        self, tmp_path: Path, kind: str
    ) -> None:
        from scribe_desktop.session_store import link_state

        _sessions, link, target = self._linked(tmp_path, kind)
        assert link_state(link) is True
        assert link_state(target) is False
        assert link_state(target.parent) is False

    def test_the_sweep_never_deletes_through_a_link(self, tmp_path: Path, kind: str) -> None:
        sessions, link, target = self._linked(tmp_path, kind)

        def hook(_session_id: str) -> bool:
            raise AssertionError("a link is not a session: nothing to destroy")

        [result] = sweep_sessions(sessions, now=_OLD + 2 * 86_400, before_destroy=hook)
        assert (result.action, result.created_at) == ("link_refused", None)
        assert (target / KEY_FILENAME).exists()
        assert os.path.lexists(link)
        [direct] = sweep_sessions(
            target.parent, now=_OLD + 2 * 86_400, before_destroy=lambda _sid: True
        )
        assert (direct.session_id, direct.action) == (target.name, "expired")
        assert not (target / KEY_FILENAME).exists()

    def test_key_deletion_and_discard_refuse_a_link(self, tmp_path: Path, kind: str) -> None:
        from scribe_desktop.session_store import (
            SessionLinkError,
            delete_session_key,
            discard_session,
        )

        _sessions, link, target = self._linked(tmp_path, kind)
        with pytest.raises(SessionLinkError):
            delete_session_key(link)
        with pytest.raises(SessionLinkError):
            discard_session(link)
        assert (target / KEY_FILENAME).exists()
        assert os.path.lexists(link)
        discard_session(target)  # the real folder: key first, then the folder
        assert not os.path.lexists(target)

    def test_the_recovery_list_never_offers_a_link(self, tmp_path: Path, kind: str) -> None:
        from scribe_desktop.ui import models

        sessions, _link_path, target = self._linked(tmp_path, kind, aged=False)
        assert models.list_recoverable_sessions(sessions) == []
        assert [info.session_id for info in models.list_recoverable_sessions(target.parent)] == [
            target.name
        ]  # the same folder, reached directly, IS listed


class TestSweepWithArchive:
    """``app.sweep_with_archive`` — start-up and every sweep tick: staging
    cleaned, a dead-keyed session's unfinished entry removed BEFORE its key,
    a confirmed-absent key's pending entry committed. No clock involved: a
    dead or absent key is collected at any age."""

    def test_the_three_steps(self, tmp_path: Path) -> None:
        from scribe_desktop.app import sweep_with_archive

        sessions = tmp_path / "sessions"
        store = _store(tmp_path)
        dead = _aged(sessions, key=b"")
        absent = _aged(sessions, key=None)
        for directory in (dead, absent):
            source = ArchiveSource(
                session_id=directory.name,
                created_at=None,
                transcript_plain=_transcript(directory.name),
                note_plain=None,
                generated_plain=None,
            )
            store.write_entry(source, LINKED)
        crashed = store.staging_root / _sid()
        crashed.mkdir(parents=True)
        (crashed / KEY_FILENAME).write_bytes(b"k")
        results = sweep_with_archive(sessions, store, frozenset())
        assert {(r.session_id, r.action) for r in results} == {
            (dead.name, "orphan_gc"),
            (absent.name, "orphan_gc"),
        }
        assert not crashed.exists()
        assert not (store.root / dead.name).exists()
        assert [listing.session_id for listing in store.list_entries()] == [absent.name]

    def test_an_entry_that_cannot_be_removed_keeps_the_dead_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.app import sweep_with_archive

        sessions = tmp_path / "sessions"
        store = _store(tmp_path)
        dead = _aged(sessions, key=b"")
        monkeypatch.setattr(store, "remove_pending_entry", lambda _sid: False)
        [result] = sweep_with_archive(sessions, store, frozenset())
        assert result.action == "error"
        assert (dead / KEY_FILENAME).exists()

    def test_each_reconciled_commit_is_recorded_as_archived(self, tmp_path: Path) -> None:
        """Round 12 LOW-002 (Task 3.2): an entry committed by reconciliation
        — its Complete stopped between the key deletion and its own audit
        update — is recorded as ``archived``; a still-pending one is not."""
        from scribe_desktop.app import sweep_with_archive

        sessions = tmp_path / "sessions"
        store = _store(tmp_path)
        finished, live = _source(), _source()
        for source in (finished, live):
            store.write_entry(source, LINKED)
        (sessions / live.session_id).mkdir(parents=True)
        (sessions / live.session_id / KEY_FILENAME).write_bytes(b"\0" * 64)
        recorded: list[tuple[str, str]] = []

        class Recorder:
            def record_past_session(self, session_id: str, state: str, **_kw: Any) -> bool:
                recorded.append((session_id, state))
                return True

            def record_deletion(self, *args: Any, **kwargs: Any) -> bool:
                return True

            # Development-recordings Task 1.4 (review round 8 LOW-004).
            def record_recording_kept(self, *args: Any, **kwargs: Any) -> bool:
                return True

            def keeps_rows_of(self, *args: Any) -> bool:  # review round 13 LOW-005
                return True

            def record_recording_deleted(self, *args: Any, **kwargs: Any) -> bool:
                return True

            def record_recording_exported(self, *args: Any, **kwargs: Any) -> bool:
                return True

        audit: Any = Recorder()
        sweep_with_archive(sessions, store, frozenset({live.session_id}), audit=audit)
        assert recorded == [(finished.session_id, "archived")]
        assert (store.root / live.session_id / PENDING_FILENAME).exists()


# ---------------------------------------------------------------------------
# The real custody (Windows only): the entry key's own DPAPI description.
# ---------------------------------------------------------------------------


@windows_only
class TestRealEntryKeys:
    def test_an_entry_key_opens_only_its_entry(self, tmp_path: Path) -> None:
        store = PastSessionStore(tmp_path / "past_sessions", clock=lambda: NOW)
        sid = _published(store)
        assert store.read_entry(sid).label.session_id == sid
        with pytest.raises(KeyCustodyError):
            session_store.unwrap_key_from_file(store.root / sid)  # a session key's description
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        session_store.wrap_key_to_file(SessionCrypto(), session_dir)
        with pytest.raises(KeyCustodyError):
            past_sessions._unwrap_entry_key(session_dir)


# ---------------------------------------------------------------------------
# Kept recordings (development-recordings plan Tasks 2.1 and 2.2; D5, D6, D8,
# D15; C3, C4, C5).
# ---------------------------------------------------------------------------

_PCM: tuple[bytes, ...] = (b"\x01\x02" * 800, b"\x03\x04" * 500, b"\x05\x06" * 300)
_WITH_AUDIO: frozenset[str] = frozenset(
    {
        KEY_FILENAME,
        LABEL_FILENAME,
        TRANSCRIPT_FILENAME,
        NOTE_FILENAME,
        GENERATED_FILENAME,
        AUDIO_FILENAME,
        AUDIO_KEY_FILENAME,
    }
)


def _audio_session(
    root: Path, *, finished: bool = True, **kwargs: Any
) -> tuple[Path, SessionCrypto]:
    """``_session`` with a real ``audio.enc`` under the session key (the
    L1157 pattern) — finished, or as a crash leaves it (no footer)."""
    directory, crypto = _session(root, **kwargs)
    audio = SessionChunkStore.create(directory / AUDIO_FILENAME, crypto, directory.name)
    for chunk in _PCM:
        audio.append_chunk(chunk)
    if finished:
        audio.finish()
    audio.close()
    return directory, crypto


def _kept(
    store: PastSessionStore, *, commit: bool = True, started: datetime | None = None
) -> str:
    """A kept entry written through the store's own verified path — the
    session started at ``started`` (the label's ``started_at``) if given."""
    source = replace(_source(), audio_chunks=iter(_PCM))
    if started is not None:
        source = replace(source, created_at=started.timestamp())
    store.write_entry(source, LINKED)
    if commit:
        assert store.commit(source.session_id)
    return source.session_id


class _SourceKeeper:
    """A fake keeper: records what each Complete handed it (D4)."""

    def __init__(self) -> None:
        self.audio: list[bytes | None] = []

    def write(self, source: ArchiveSource) -> None:
        chunks = source.audio_chunks
        self.audio.append(None if chunks is None else b"".join(chunks))

    def commit(self, session_id: str) -> bool:
        return True

    def drop_unfinished(self, session_id: str) -> bool:
        return True


class TestKeptCompleteSource:
    """Task 2.1: only a kept, non-mock Complete hands the keeper the audio."""

    @pytest.mark.parametrize("finished", [True, False], ids=["finished", "crash_recovered"])
    def test_a_kept_complete_hands_the_keeper_the_pcm(
        self, tmp_path: Path, finished: bool
    ) -> None:
        """``store_has_footer`` decides footer enforcement, as the app's
        readers do: a crash-recovered store without one is still kept."""
        keeper = _SourceKeeper()
        directory, crypto = _audio_session(tmp_path, finished=finished)
        facts = complete_session(directory, crypto, keep=keeper, keep_audio=True)
        assert keeper.audio == [b"".join(_PCM)]
        assert (facts.past_session, facts.recording_kept) == ("archived", True)

    def test_every_other_complete_hands_none(self, tmp_path: Path) -> None:
        keeper = _SourceKeeper()
        directory, crypto = _audio_session(tmp_path)
        facts = complete_session(directory, crypto, keep=keeper)
        assert keeper.audio == [None]
        assert (facts.past_session, facts.recording_kept) == ("archived", False)

    def test_a_consented_mock_session_keeps_no_audio(self, tmp_path: Path) -> None:
        keeper = _SourceKeeper()
        directory, crypto = _audio_session(tmp_path, model_name="mock")
        facts = complete_session(directory, crypto, keep=keeper, keep_audio=True)
        assert keeper.audio == []  # write never called
        assert (facts.past_session, facts.recording_kept) == ("not_kept_mock", False)

    def test_no_keeper_keeps_no_audio(self, tmp_path: Path) -> None:
        directory, crypto = _audio_session(tmp_path)
        assert complete_session(directory, crypto, keep_audio=True).recording_kept is False


class TestKeptRecording:
    """Task 2.2: the sidecar — written and verified with the entry, under its
    own key wrapped by the entry key, destroyed by every destroyer."""

    def test_a_kept_complete_publishes_the_exact_set_and_the_pcm_reads_back(
        self, tmp_path: Path
    ) -> None:
        store = _store(tmp_path)
        directory, crypto = _audio_session(tmp_path / "sessions")
        facts = complete_session(directory, crypto, keep=store.keeper(LINKED), keep_audio=True)
        assert (facts.past_session, facts.recording_kept) == ("archived", True)
        assert not directory.exists()
        entry = store.root / directory.name
        assert {path.name for path in entry.iterdir()} == _WITH_AUDIO
        assert (entry / AUDIO_KEY_FILENAME).stat().st_size == AUDIO_KEY_FILE_BYTES
        assert b"".join(store.read_recording(directory.name)) == b"".join(_PCM)
        [listing] = store.list_entries()
        assert listing.recording_kept and store.recording_kept(directory.name)
        # The transcript and notes read as before.
        assert store.read_entry(directory.name).saved_note is not None

    def test_the_exact_set_without_audio_holds_neither_file(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        sid = _published(store)
        names = {path.name for path in (store.root / sid).iterdir()}
        assert names == _WITH_AUDIO - {AUDIO_FILENAME, AUDIO_KEY_FILENAME}
        assert not store.recording_kept(sid)
        assert [listing.recording_kept for listing in store.list_entries()] == [False]
        with pytest.raises(PastSessionError) as info:
            store.read_recording(sid)
        assert info.value.reason == "recording_not_kept"

    def test_the_audio_has_its_own_key_wrapped_by_the_entry_key(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        sid = _kept(store)
        entry = store.root / sid
        entry_crypto = _fake_unwrap(entry)
        with pytest.raises(StoreCorruptError):
            next(session_store.iter_chunks(entry / AUDIO_FILENAME, entry_crypto))
        wrapped = (entry / AUDIO_KEY_FILENAME).read_bytes()
        with pytest.raises(InvalidTag):
            entry_crypto.decrypt(wrapped)  # bound to its associated data
        key = entry_crypto.decrypt(wrapped, b"past-audio-key:" + sid.encode())
        audio = SessionCrypto.from_key(key)
        chunks = session_store.iter_chunks(entry / AUDIO_FILENAME, audio, require_footer=True)
        assert b"".join(chunks) == b"".join(_PCM)

    def test_a_digest_mismatch_keeps_the_source_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """C4: the staged audio is re-read and its digest compared with the
        one taken while it was copied — a difference refuses the entry
        BEFORE the key boundary."""

        class Tampering(SessionChunkStore):
            def append_chunk(self, data: bytes) -> int:
                return super().append_chunk(bytes([data[0] ^ 1]) + data[1:])

        monkeypatch.setattr(past_sessions, "SessionChunkStore", Tampering)
        store = _store(tmp_path)
        directory, crypto = _audio_session(tmp_path / "sessions")
        with pytest.raises(ArchiveWriteError, match="key retained"):
            complete_session(directory, crypto, keep=store.keeper(LINKED), keep_audio=True)
        assert (directory / KEY_FILENAME).exists() and not crypto.destroyed
        assert not (store.root / directory.name).exists()
        assert list(store.staging_root.iterdir()) == []

    def test_a_kept_complete_with_no_audio_store_keeps_the_key(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        directory, crypto = _session(tmp_path / "sessions")  # writes no audio.enc
        with pytest.raises(ArchiveWriteError, match="key retained"):
            complete_session(directory, crypto, keep=store.keeper(LINKED), keep_audio=True)
        assert (directory / KEY_FILENAME).exists() and not crypto.destroyed
        assert not (store.root / directory.name).exists()

    def test_a_consented_mock_complete_writes_no_audio(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        directory, crypto = _audio_session(tmp_path / "sessions", note_provider="mock-x")
        facts = complete_session(directory, crypto, keep=store.keeper(LINKED), keep_audio=True)
        assert (facts.past_session, facts.recording_kept) == ("not_kept_mock", False)
        assert not store.root.exists()

    def test_deleting_the_entry_key_alone_makes_the_recording_unreadable(
        self, tmp_path: Path
    ) -> None:
        """D6/C5: the audio key is wrapped under the entry key — another key
        in its place opens nothing, and with none the entry is gone."""
        store = _store(tmp_path)
        sid = _kept(store)
        _fake_wrap(SessionCrypto(), store.root / sid)  # a different entry key
        with pytest.raises(PastSessionError) as info:
            b"".join(store.read_recording(sid))
        assert info.value.reason == "unreadable"
        (store.root / sid / KEY_FILENAME).unlink()
        with pytest.raises(PastSessionError) as info:
            store.read_recording(sid)
        assert info.value.reason == "not_found"

    def test_a_pending_kept_entry_is_not_read(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        sid = _kept(store, commit=False)
        with pytest.raises(PastSessionError) as info:
            store.read_recording(sid)
        assert info.value.reason == "pending"

    @pytest.mark.parametrize("destroyer", ["delete_entry", "remove_pending_entry", "expiry"])
    def test_every_destroyer_deletes_both_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, destroyer: str
    ) -> None:
        store = _store(tmp_path, clock=NOW - WINDOW - timedelta(days=1))
        sid = _kept(store, commit=destroyer != "remove_pending_entry")
        unlinked: list[str] = []
        real_unlink = Path.unlink

        def unlink(self: Path, missing_ok: bool = False) -> None:
            unlinked.append(self.name)
            real_unlink(self, missing_ok=missing_ok)

        monkeypatch.setattr(Path, "unlink", unlink)
        if destroyer == "delete_entry":
            store.delete_entry(sid)
        elif destroyer == "remove_pending_entry":
            assert store.remove_pending_entry(sid)
        else:
            assert store.sweep(SEVEN, NOW) == [sid]
        # The entry's own removal (any staging copy's comes first): its key,
        # then the audio key, before the tree.
        assert unlinked[-2:] == [KEY_FILENAME, AUDIO_KEY_FILENAME]
        assert not (store.root / sid).exists()

    def test_a_failing_audio_key_unlink_does_not_flip_the_result(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Only ``key.dpapi`` decides: the audio is already dead under it."""
        store = _store(tmp_path)
        sid = _kept(store)
        real_unlink = Path.unlink

        def unlink(self: Path, missing_ok: bool = False) -> None:
            if self.name == AUDIO_KEY_FILENAME:
                raise PermissionError(errno.EACCES, "in use")
            real_unlink(self, missing_ok=missing_ok)

        monkeypatch.setattr(Path, "unlink", unlink)
        store.delete_entry(sid)  # no raise
        assert not (store.root / sid / KEY_FILENAME).exists()
        assert store.list_entries() == []

    @pytest.mark.parametrize("missing", [AUDIO_FILENAME, AUDIO_KEY_FILENAME])
    def test_kept_needs_both_files(self, tmp_path: Path, missing: str) -> None:
        store = _store(tmp_path)
        sid = _kept(store)
        (store.root / sid / missing).unlink()
        assert not store.recording_kept(sid)
        assert [listing.recording_kept for listing in store.list_entries()] == [False]

    def test_a_zeroed_key_is_not_kept_and_is_refused_before_any_unwrap(
        self, tmp_path: Path
    ) -> None:
        unwraps = _Unwraps()
        store = _store(tmp_path, unwrap_key=unwraps)
        sid = _kept(store)
        key = store.root / sid / AUDIO_KEY_FILENAME
        key.write_bytes(b"\0" * AUDIO_KEY_FILE_BYTES)
        calls = unwraps.calls
        assert not store.recording_kept(sid)
        with pytest.raises(PastSessionError) as info:
            store.read_recording(sid)
        assert info.value.reason == "recording_not_kept"
        assert unwraps.calls == calls

    def test_the_listing_marker_decrypts_nothing(self, tmp_path: Path) -> None:
        unwraps = _Unwraps()
        store = _store(tmp_path, unwrap_key=unwraps)
        sid = _kept(store)
        calls = unwraps.calls
        assert store.recording_kept(sid)
        assert unwraps.calls == calls

    def test_delete_recording_zeroes_the_original_file_then_unlinks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D6 (round 1 PR-HIGH-001): the zeros land IN the original file — the
        same file, not a replacement — before it is unlinked; the transcript
        and notes stay readable."""
        store = _store(tmp_path)
        sid = _kept(store)
        key = store.root / sid / AUDIO_KEY_FILENAME
        original = os.stat(key)
        seen: list[tuple[str, bytes, bool]] = []
        real_unlink = Path.unlink

        def unlink(self: Path, missing_ok: bool = False) -> None:
            if self.name == AUDIO_KEY_FILENAME:
                now = os.stat(self)
                same = (now.st_ino, now.st_dev) == (original.st_ino, original.st_dev)
                seen.append((self.name, self.read_bytes(), same))
            real_unlink(self, missing_ok=missing_ok)

        monkeypatch.setattr(Path, "unlink", unlink)
        store.delete_recording(sid)
        assert seen == [(AUDIO_KEY_FILENAME, b"\0" * AUDIO_KEY_FILE_BYTES, True)]
        assert not key.exists() and not (store.root / sid / AUDIO_FILENAME).exists()
        assert not store.recording_kept(sid)
        entry = store.read_entry(sid)
        assert entry.saved_note is not None and entry.generated is not None
        assert (store.root / sid / KEY_FILENAME).exists()
        with pytest.raises(PastSessionError) as info:
            store.delete_recording(sid)
        assert info.value.reason == "recording_not_kept"

    def test_a_zeroed_recording_whose_unlinks_fail_is_deleted_and_tidied_later(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 4 PR-MED-041: once the zeros are synced the recording is
        destroyed — a failed unlink is a pending cleanup, never a failure."""
        store = _store(tmp_path)
        sid = _kept(store)
        real_unlink = Path.unlink

        def unlink(self: Path, missing_ok: bool = False) -> None:
            if self.name in (AUDIO_KEY_FILENAME, AUDIO_FILENAME):
                raise PermissionError(errno.EACCES, "locked")
            real_unlink(self, missing_ok=missing_ok)

        monkeypatch.setattr(Path, "unlink", unlink)
        store.delete_recording(sid)  # success
        monkeypatch.undo()
        entry = store.root / sid
        assert (entry / AUDIO_KEY_FILENAME).read_bytes() == b"\0" * AUDIO_KEY_FILE_BYTES
        assert (entry / AUDIO_FILENAME).exists()
        assert [listing.recording_kept for listing in store.list_entries()] == [False]
        assert store.tidy_dead_recordings() == 2
        assert not (entry / AUDIO_KEY_FILENAME).exists()
        assert not (entry / AUDIO_FILENAME).exists()
        assert store.read_entry(sid).transcript is not None

    def test_a_failed_overwrite_raises_with_the_key_intact(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = _store(tmp_path)
        sid = _kept(store)
        key = store.root / sid / AUDIO_KEY_FILENAME
        before = key.read_bytes()
        real_open = Path.open

        def refuse(self: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
            if self.name == AUDIO_KEY_FILENAME and mode == "r+b":
                raise PermissionError(errno.EACCES, "locked")
            return real_open(self, mode, *args, **kwargs)

        monkeypatch.setattr(Path, "open", refuse)
        with pytest.raises(PastSessionError) as info:
            store.delete_recording(sid)
        assert info.value.reason == "recording_delete_failed"
        assert str(info.value) == "that kept recording could not be deleted"
        monkeypatch.undo()
        assert key.read_bytes() == before
        assert store.recording_kept(sid)

    def test_delete_recording_never_zeroes_through_a_hard_link(self, tmp_path: Path) -> None:
        """Review round 11 LOW-001: the in-place overwrite is the archive's
        only write through an existing file — a key file that is a hard link
        to another file is refused and NOTHING is zeroed (neither name)."""
        store = _store(tmp_path)
        victim, sid = _kept(store), _kept(store)
        victim_key = store.root / victim / AUDIO_KEY_FILENAME
        before = victim_key.read_bytes()
        key = store.root / sid / AUDIO_KEY_FILENAME
        key.unlink()
        os.link(victim_key, key)
        with pytest.raises(PastSessionError) as info:
            store.delete_recording(sid)
        assert info.value.reason == "recording_delete_failed"
        assert victim_key.read_bytes() == before
        assert b"".join(store.read_recording(victim)) == b"".join(_PCM)

    @pytest.mark.parametrize("answer", [True, None], ids=["a_link", "uninspectable"])
    def test_delete_recording_refuses_a_linked_or_uninspectable_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answer: bool | None
    ) -> None:
        """Review round 12 MED-001: both answers the guard must refuse — a
        symlink (True; ``fstat`` through it would see the TARGET as a regular
        one-link file) and "cannot tell" (None)."""
        from scribe_desktop import past_sessions as module

        store = _store(tmp_path)
        sid = _kept(store)
        key = store.root / sid / AUDIO_KEY_FILENAME
        before = key.read_bytes()
        real = module.link_state
        monkeypatch.setattr(
            module,
            "link_state",
            lambda path: answer if path.name == AUDIO_KEY_FILENAME else real(path),
        )
        with pytest.raises(PastSessionError) as info:
            store.delete_recording(sid)
        assert info.value.reason == "recording_delete_failed"
        assert key.read_bytes() == before

    def test_delete_recording_never_zeroes_more_than_a_key_file(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        sid = _kept(store)
        key = store.root / sid / AUDIO_KEY_FILENAME
        oversized = b"\x07" * (AUDIO_KEY_FILE_BYTES + 1)
        key.write_bytes(oversized)
        assert store.recording_kept(sid)  # still shown, so it can be deleted
        with pytest.raises(PastSessionError) as info:
            store.delete_recording(sid)
        assert info.value.reason == "recording_delete_failed"
        assert key.read_bytes() == oversized

    def test_an_unreadable_key_file_counts_as_kept_and_is_never_tidied(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review round 11 LOW-009: a key file that cannot be read decides
        nothing — shown as kept (so it can be deleted), and tidy keeps both."""
        store = _store(tmp_path)
        sid = _kept(store)
        real_open = Path.open

        def refuse(self: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
            if self.name == AUDIO_KEY_FILENAME:
                raise PermissionError(errno.EACCES, "locked")
            return real_open(self, mode, *args, **kwargs)

        monkeypatch.setattr(Path, "open", refuse)
        assert store.recording_kept(sid)
        assert store.tidy_dead_recordings() == 0
        assert [listing.session_id for listing in store.kept_entries()] == [sid]
        assert store.deleted_recordings() == []
        monkeypatch.undo()
        assert (store.root / sid / AUDIO_FILENAME).exists()
        assert (store.root / sid / AUDIO_KEY_FILENAME).exists()

    def test_the_deletion_is_recorded_between_the_zeros_and_the_unlinks(
        self, tmp_path: Path
    ) -> None:
        """Review round 12 LOW-003: ``on_destroyed`` runs once the zeros are
        verified and BEFORE the unlinks, so a kill after the unlinks never
        leaves an unrecorded deletion."""
        store = _store(tmp_path)
        sid = _kept(store)
        entry = store.root / sid
        seen: list[tuple[bytes, bool]] = []

        def recorded() -> bool:
            seen.append(
                ((entry / AUDIO_KEY_FILENAME).read_bytes(), (entry / AUDIO_FILENAME).exists())
            )
            return True

        store.delete_recording(sid, on_destroyed=recorded)
        assert seen == [(b"\0" * AUDIO_KEY_FILE_BYTES, True)]
        assert not (entry / AUDIO_KEY_FILENAME).exists()
        assert not (entry / AUDIO_FILENAME).exists()

    @pytest.mark.parametrize("outcome", ["refused", "raised"])
    def test_an_unrecorded_deletion_keeps_its_evidence(
        self, tmp_path: Path, outcome: str
    ) -> None:
        """A record that fails leaves the zeroed key (the recording IS
        destroyed) for the next run's deletion record; nothing is raised."""
        store = _store(tmp_path)
        sid = _kept(store)
        entry = store.root / sid

        def record() -> bool:
            if outcome == "raised":
                raise RuntimeError("audit unavailable")
            return False

        store.delete_recording(sid, on_destroyed=record)
        assert (entry / AUDIO_KEY_FILENAME).read_bytes() == b"\0" * AUDIO_KEY_FILE_BYTES
        assert (entry / AUDIO_FILENAME).exists()
        assert not store.recording_kept(sid)
        assert [listing.session_id for listing in store.deleted_recordings()] == [sid]

    def test_a_stray_non_file_audio_is_never_a_deleted_recording(self, tmp_path: Path) -> None:
        """Review round 12 LOW-005: with the key gone, only a REGULAR
        ``audio.enc`` is evidence of a deletion — never a link or a folder,
        which no recording is. Review round 18 PR-LOW-001: nor is it held by
        tidy's clearance rule — repeated sweeps with a healthy audit leave it
        alone and the retention sweep still expires the entry."""
        from scribe_desktop.app import sweep_with_archive
        from scribe_desktop.ui import past_sessions_view as view

        sessions = tmp_path / "sessions"
        sessions.mkdir()
        store = _store(tmp_path, clock=NOW - WINDOW - timedelta(days=1))
        sid = _kept(store)
        entry = store.root / sid
        (entry / AUDIO_KEY_FILENAME).unlink()
        (entry / AUDIO_FILENAME).unlink()
        (entry / AUDIO_FILENAME).mkdir()
        assert store.deleted_recordings() == []
        assert store.recording_state(sid) == "none"

        class Healthy:
            def keeps_rows_of(self, at: datetime) -> bool:
                return True

            def record_past_session(self, *args: Any, **kw: Any) -> bool:
                return True

            def record_recording_kept(self, *args: Any, **kw: Any) -> bool:
                return True

            def record_recording_deleted(self, *args: Any, **kw: Any) -> bool:
                return True

        audit: Any = Healthy()
        for _tick in range(2):
            sweep_with_archive(sessions, store, frozenset(), audit=audit)
            assert (entry / AUDIO_FILENAME).is_dir()  # not a recording: not tidied
        report = view.retention_sweep(store, audit, SEVEN, NOW)
        assert ([session_id for session_id, _ in report.expired], report.failed) == ([sid], 0)
        assert not entry.exists()

    def test_a_sweep_spares_a_deletion_it_could_not_record(self, tmp_path: Path) -> None:
        """Review round 12 LOW-002: on every sweep (a tick here) the deletion
        record runs before tidy, and tidy spares an entry whose record an
        audit refused — the zeroed key stays until a later run records it."""
        from scribe_desktop.app import sweep_with_archive

        sessions = tmp_path / "sessions"
        sessions.mkdir()
        store = _store(tmp_path)
        sid = _kept(store)
        entry = store.root / sid
        (entry / AUDIO_KEY_FILENAME).write_bytes(b"\0" * AUDIO_KEY_FILE_BYTES)
        calls: list[tuple[str, str]] = []

        class Refusing:
            ok = False

            def keeps_rows_of(self, at: datetime) -> bool:
                return True

            def record_past_session(self, session_id: str, state: str, **kw: Any) -> bool:
                calls.append((state, session_id))
                return self.ok

            def record_recording_kept(self, session_id: str, at: datetime, **kw: Any) -> bool:
                calls.append(("kept", session_id))
                return self.ok

            def record_recording_deleted(self, session_id: str, **kw: Any) -> bool:
                calls.append(("deleted", session_id))
                return self.ok

        audit: Any = Refusing()
        sweep_with_archive(sessions, store, frozenset(), audit=audit)
        assert calls == [("kept", sid)]
        assert (entry / AUDIO_KEY_FILENAME).exists() and (entry / AUDIO_FILENAME).exists()
        audit.ok = True
        calls.clear()
        sweep_with_archive(sessions, store, frozenset(), audit=audit)
        assert calls == [("kept", sid), ("archived", sid), ("deleted", sid)]
        assert not (entry / AUDIO_KEY_FILENAME).exists()
        assert not (entry / AUDIO_FILENAME).exists()

    @pytest.mark.parametrize("discovery", ["read_fails", "listing_fails"])
    def test_tidy_needs_positive_clearance(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, discovery: str
    ) -> None:
        """Review round 17 PR-MED-001: tidy removes a dead recording's files
        ONLY when the deletion record LISTED and recorded it. A discovery
        that missed it — its key read failing then (or the whole listing
        failing) but succeeding for tidy — leaves the evidence, held from the
        retention sweep; the next sweep records it, then tidies."""
        from scribe_desktop.app import sweep_with_archive
        from scribe_desktop.ui import past_sessions_view as view

        sessions = tmp_path / "sessions"
        sessions.mkdir()
        store = _store(tmp_path, clock=NOW - WINDOW - timedelta(days=1))
        sid = _kept(store)
        entry = store.root / sid
        (entry / AUDIO_KEY_FILENAME).write_bytes(b"\0" * AUDIO_KEY_FILE_BYTES)
        failing = [True]
        real_state = past_sessions._audio_key_state  # noqa: SLF001
        real_listing = store.deleted_recordings

        def state(path: Path) -> Any:
            if failing[0] and discovery == "read_fails":
                return "unknown"  # an OSError while discovery reads the key
            return real_state(path)

        def listing() -> list[PastSessionListing]:
            try:
                if discovery == "listing_fails":
                    return []  # `_labelled_where` swallowed a listing failure
                return real_listing()
            finally:
                failing[0] = False  # tidy's own read then succeeds

        monkeypatch.setattr(past_sessions, "_audio_key_state", state)
        monkeypatch.setattr(store, "deleted_recordings", listing)
        calls: list[tuple[str, str]] = []

        class Audit:
            def keeps_rows_of(self, at: datetime) -> bool:
                return True

            def record_past_session(self, session_id: str, state: str, **kw: Any) -> bool:
                calls.append((state, session_id))
                return True

            def record_recording_kept(self, session_id: str, at: datetime, **kw: Any) -> bool:
                calls.append(("kept", session_id))
                return True

            def record_recording_deleted(self, session_id: str, **kw: Any) -> bool:
                calls.append(("deleted", session_id))
                return True

        audit: Any = Audit()
        sweep_with_archive(sessions, store, frozenset(), audit=audit)
        assert ("deleted", sid) not in calls  # discovery missed it ...
        assert (entry / AUDIO_KEY_FILENAME).exists() and (entry / AUDIO_FILENAME).exists()
        report = view.retention_sweep(store, audit, SEVEN, NOW)  # ... and expiry holds it
        assert (report.expired, report.failed) == ((), 1)
        failing[0] = True
        monkeypatch.setattr(store, "deleted_recordings", real_listing)
        monkeypatch.setattr(past_sessions, "_audio_key_state", real_state)
        sweep_with_archive(sessions, store, frozenset(), audit=audit)
        assert ("deleted", sid) in calls
        assert not (entry / AUDIO_KEY_FILENAME).exists()
        assert not (entry / AUDIO_FILENAME).exists()

    def test_a_destroyer_decides_from_one_read(self, tmp_path: Path) -> None:
        """Review round 17 PR-MED-001: ``recording_state`` (Delete now) and
        the retention sweep decide kept / gone from ONE read of the key; an
        unreadable key reads as kept (shown, so it can be deleted)."""
        store = _store(tmp_path)
        kept, gone, plain = _kept(store), _kept(store), _published(store)
        (store.root / gone / AUDIO_KEY_FILENAME).write_bytes(b"\0" * AUDIO_KEY_FILE_BYTES)
        assert store.recording_state(kept) == "kept"
        assert store.recording_state(gone) == "gone"
        assert store.recording_state(plain) == "none"
        assert store.recording_state("not-an-id") == "none"
        (store.root / gone / AUDIO_KEY_FILENAME).unlink()  # key gone, audio left
        assert store.recording_state(gone) == "gone"

    @staticmethod
    def _one_good_read(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
        """Instrument the key-state reader: each key file's FIRST read is
        real, every later one fails transiently (``unknown``) — so a decision
        made from two reads disagrees with itself. Returns the reads per
        session id."""
        real = past_sessions._audio_key_state
        reads: dict[str, int] = {}

        def flaky(path: Path) -> past_sessions.AudioKeyState:
            sid = path.parent.name
            reads[sid] = reads.get(sid, 0) + 1
            return real(path) if reads[sid] == 1 else "unknown"

        monkeypatch.setattr(past_sessions, "_audio_key_state", flaky)
        return reads

    def test_recording_state_reads_the_key_once(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Hardening round 45 PR-LOW-001: the one-read rule itself, under a
        transient failure of any second read."""
        store = _store(tmp_path)
        gone = _kept(store)
        (store.root / gone / AUDIO_KEY_FILENAME).write_bytes(b"\0" * AUDIO_KEY_FILE_BYTES)
        reads = self._one_good_read(monkeypatch)
        assert store.recording_state(gone) == "gone"
        assert reads == {gone: 1}

    def test_the_retention_sweep_decides_from_one_read(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Hardening round 45 PR-LOW-001: an expired entry whose recording was
        deleted (zeroed key, audio not yet tidied) — the sweep reads the key
        ONCE, reports it to ``before_held_delete`` as gone (a second read that
        failed would call it kept, so its deletion would never be recorded),
        and deletes the entry once the deletion is recorded."""
        store = _store(tmp_path, clock=NOW - WINDOW - timedelta(days=30))
        gone = _kept(store)
        (store.root / gone / AUDIO_KEY_FILENAME).write_bytes(b"\0" * AUDIO_KEY_FILE_BYTES)
        reads = self._one_good_read(monkeypatch)
        told: list[tuple[str, bool]] = []

        def before_held_delete(sid: str, _completed: Any, _started: Any, was_gone: bool) -> bool:
            told.append((sid, was_gone))
            return True

        report = store.sweep_report(SEVEN, NOW, before_held_delete=before_held_delete)
        assert told == [(gone, True)]
        assert [sid for sid, _ in report.expired] == [gone]
        assert gone in report.kept
        assert reads == {gone: 1}
        assert not (store.root / gone).exists()

    @pytest.mark.parametrize("shape", ["empty", "hard_linked"])
    def test_only_the_apps_own_key_file_decides(self, tmp_path: Path, shape: str) -> None:
        """Review round 13 LOW-004: an empty key file, or one with another
        name (a hard link), is ``unknown`` — never read as a deletion (no
        audit record, no tidy), still shown as kept so the entry can go."""
        store = _store(tmp_path)
        other, sid = _kept(store), _kept(store)
        key = store.root / sid / AUDIO_KEY_FILENAME
        if shape == "empty":
            key.write_bytes(b"")
        else:
            zeros = store.root / other / AUDIO_KEY_FILENAME
            zeros.write_bytes(b"\0" * AUDIO_KEY_FILE_BYTES)
            key.unlink()
            os.link(zeros, key)  # both names now share zeroed bytes
        assert store.recording_kept(sid)
        assert sid not in [listing.session_id for listing in store.deleted_recordings()]
        store.tidy_dead_recordings()
        assert (store.root / sid / AUDIO_FILENAME).exists()

    def test_a_deletion_not_yet_tidied_still_counts_as_held(self, tmp_path: Path) -> None:
        """Review round 13 LOW-001: a destroyer of the WHOLE entry (Delete
        now, the retention sweep) asks ``recording_held`` — a zeroed key not
        yet tidied counts, so the kept fact (and with it the deletion) is
        recorded before the entry goes."""
        from scribe_desktop.ui import past_sessions_view as view

        store = _store(tmp_path, clock=NOW - WINDOW - timedelta(days=1))
        sid, plain = _kept(store), _published(store)
        (store.root / sid / AUDIO_KEY_FILENAME).write_bytes(b"\0" * AUDIO_KEY_FILE_BYTES)
        assert not store.recording_kept(sid) and store.recording_held(sid)
        assert not store.recording_held(plain)
        calls: list[tuple[Any, ...]] = []

        class Recorder:
            def record_recording_kept(self, session_id: str, at: datetime, **kw: Any) -> bool:
                calls.append(("kept", session_id))
                return True

            def record_past_session(self, session_id: str, state: str, **kw: Any) -> bool:
                calls.append((state, session_id))
                return True

            # Review round 15 PR-MED-002: the deletion is already a fact.
            def record_recording_deleted(self, session_id: str, **kw: Any) -> bool:
                calls.append(("deleted", session_id))
                return True

            def keeps_rows_of(self, at: datetime) -> bool:  # review round 16 PR-MED-001
                return True

        audit: Any = Recorder()
        report = view.retention_sweep(store, audit, SEVEN, NOW)
        assert report.kept == frozenset({sid})
        order = [calls.index((kind, sid)) for kind in ("kept", "deleted", "expired")]
        assert order == sorted(order)
        assert ("deleted", plain) not in calls

    @pytest.mark.parametrize("failure", ["refused", "raises"])
    def test_an_unrecordable_deletion_is_held_from_the_retention_sweep(
        self, tmp_path: Path, failure: str
    ) -> None:
        """Review round 15 PR-MED-002: the sweep judges a deleted-but-untidied
        recording AFRESH (not only from the latest tidy's spare set) — its
        deletion is recorded before the entry goes, and while that cannot be
        recorded the entry is held (counted as not deleted); a LIVE kept
        recording whose kept fact fails still expires (C2)."""
        from scribe_desktop.ui import past_sessions_view as view

        store = _store(tmp_path, clock=NOW - WINDOW - timedelta(days=1))
        gone, live = _kept(store), _kept(store)
        (store.root / gone / AUDIO_KEY_FILENAME).write_bytes(b"\0" * AUDIO_KEY_FILE_BYTES)
        assert store.recording_held(gone) and not store.recording_kept(gone)
        present_at_record: list[bool] = []

        class Audit:
            ok = False

            def keeps_rows_of(self, at: datetime) -> bool:  # review round 16 PR-MED-001
                return True

            def record_recording_kept(self, *args: Any, **kw: Any) -> bool:
                return True

            def record_recording_deleted(self, session_id: str, **kw: Any) -> bool:
                present_at_record.append((store.root / session_id / KEY_FILENAME).exists())
                if not self.ok and failure == "raises":
                    raise RuntimeError("audit unavailable")
                return self.ok

            def record_past_session(self, *args: Any, **kw: Any) -> bool:
                return True

        audit: Any = Audit()
        report = view.retention_sweep(store, audit, SEVEN, NOW)
        assert [session_id for session_id, _ in report.expired] == [live]
        assert report.failed == 1
        assert (store.root / gone / KEY_FILENAME).exists()
        audit.ok = True
        report = view.retention_sweep(store, audit, SEVEN, NOW)
        assert [session_id for session_id, _ in report.expired] == [gone]
        assert not (store.root / gone).exists()
        assert present_at_record == [True, True]

    def test_a_spared_deletion_is_held_from_the_retention_sweep(self, tmp_path: Path) -> None:
        """Review round 14 PR-MED-002: a deletion whose audit write failed is
        spared by tidy AND held by the retention sweep that follows in the
        same start-up (due, counted as not deleted) — then, once a later
        sweep records it, tidied and expired as usual."""
        from scribe_desktop.app import sweep_with_archive
        from scribe_desktop.ui import past_sessions_view as view

        sessions = tmp_path / "sessions"
        sessions.mkdir()
        store = _store(tmp_path, clock=NOW - WINDOW - timedelta(days=1))
        sid = _kept(store)
        entry = store.root / sid
        (entry / AUDIO_KEY_FILENAME).write_bytes(b"\0" * AUDIO_KEY_FILE_BYTES)

        class Audit:
            ok = False

            def keeps_rows_of(self, at: datetime) -> bool:
                return True

            def record_recording_kept(self, *args: Any, **kw: Any) -> bool:
                return self.ok

            def record_past_session(self, *args: Any, **kw: Any) -> bool:
                return self.ok

            def record_recording_deleted(self, *args: Any, **kw: Any) -> bool:
                return self.ok

        audit: Any = Audit()
        sweep_with_archive(sessions, store, frozenset(), audit=audit)
        report = view.retention_sweep(store, audit, SEVEN, NOW)
        assert (report.expired, report.failed) == ((), 1)
        assert (entry / AUDIO_KEY_FILENAME).exists() and (entry / KEY_FILENAME).exists()
        audit.ok = True
        sweep_with_archive(sessions, store, frozenset(), audit=audit)
        assert not (entry / AUDIO_KEY_FILENAME).exists()
        report = view.retention_sweep(store, audit, SEVEN, NOW)
        assert [session_id for session_id, _ in report.expired] == [sid]
        assert not entry.exists()

    def test_tidy_spares_a_live_recording(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        live = _kept(store)
        dead = _kept(store)
        (store.root / dead / AUDIO_KEY_FILENAME).unlink()
        assert store.tidy_dead_recordings() == 1
        assert not (store.root / dead / AUDIO_FILENAME).exists()
        assert store.recording_kept(live)
        assert b"".join(store.read_recording(live)) == b"".join(_PCM)

    def test_kept_entries_reads_only_the_kept_labels(self, tmp_path: Path) -> None:
        unwraps = _Unwraps()
        store = _store(tmp_path, unwrap_key=unwraps)
        kept = _kept(store)
        _published(store)
        calls = unwraps.calls
        [listing] = store.kept_entries()
        assert (listing.session_id, listing.recording_kept) == (kept, True)
        assert listing.label is not None and listing.label.completed_at == NOW
        assert unwraps.calls == calls + 1

    def test_the_retention_sweep_reports_which_expired_entries_were_kept(
        self, tmp_path: Path
    ) -> None:
        from scribe_desktop.ui import past_sessions_view as view

        store = _store(tmp_path, clock=NOW - WINDOW - timedelta(days=1))
        kept, plain = _kept(store), _published(store)
        calls: list[tuple[Any, ...]] = []
        present_at_record: list[bool] = []

        class Recorder:
            def record_recording_kept(self, session_id: str, at: datetime, **kw: Any) -> bool:
                calls.append(("kept", session_id, at))
                # Round 14 PR-MED-003: recorded BEFORE the entry goes.
                present_at_record.append((store.root / session_id / KEY_FILENAME).exists())
                return True

            def record_past_session(self, session_id: str, state: str, **kw: Any) -> bool:
                calls.append((state, session_id))
                return True

            def keeps_rows_of(self, at: datetime) -> bool:  # review round 16 PR-MED-001
                return True

        audit: Any = Recorder()
        report = view.retention_sweep(store, audit, SEVEN, NOW)
        assert report.kept == frozenset({kept})
        completed = NOW - WINDOW - timedelta(days=1)
        assert calls.index(("kept", kept, completed)) < calls.index(("expired", kept))
        assert ("expired", plain) in calls
        assert not any(call[0] == "kept" and call[1] == plain for call in calls)
        assert present_at_record == [True]
        assert not (store.root / kept).exists()

    def test_a_failing_kept_record_never_blocks_the_expiry(self, tmp_path: Path) -> None:
        """C2: the audit never blocks custody — a kept-fact record that
        raises is logged and the expiry goes ahead."""
        from scribe_desktop.ui import past_sessions_view as view

        store = _store(tmp_path, clock=NOW - WINDOW - timedelta(days=1))
        kept = _kept(store)

        raised: list[str] = []

        class Raising:
            def keeps_rows_of(self, at: datetime) -> bool:  # review round 16 PR-MED-001
                return True

            def record_recording_kept(self, session_id: str, *args: Any, **kw: Any) -> bool:
                raised.append(session_id)
                raise RuntimeError("audit unavailable")

            def record_past_session(self, *args: Any, **kw: Any) -> bool:
                return True

        audit: Any = Raising()
        report = view.retention_sweep(store, audit, SEVEN, NOW)
        assert raised == [kept]  # the raising write was reached
        assert [session_id for session_id, _ in report.expired] == [kept]
        assert not (store.root / kept).exists()

    def test_the_unattended_rule(self) -> None:
        """Review round 16 PR-MED-001: THE rule every unattended audit writer
        uses (``past_sessions_view.unattended_write``) — no moment → the
        existing row only; a pruned month → nothing; otherwise a re-made row
        dated by the moment; a failing ``keeps_rows_of`` → nothing."""
        from scribe_desktop.ui import past_sessions_view as view

        class Window:
            def __init__(self, keeps: bool | None) -> None:
                self.keeps = keeps

            def keeps_rows_of(self, at: datetime) -> bool:
                if self.keeps is None:
                    raise RuntimeError("no window")
                return self.keeps

        assert view.unattended_write(Window(True), None) == (None, False)
        assert view.unattended_write(Window(False), NOW) is None
        assert view.unattended_write(Window(True), NOW) == (NOW.timestamp(), True)
        assert view.unattended_write(Window(None), NOW) is None
        assert view.audit_moment(None) is None


@windows_only
class TestKeptFactsInTheAudit:
    """Task 2.2 with the REAL audit record: the kept fact follows the files —
    repaired at start-up for an interrupted completion (both shapes), and
    recorded by a destroyer before its own outcome (review round 8 LOW-003)."""

    def _audit(self, tmp_path: Path) -> Any:
        from scribe_desktop.audit import AuditLog

        return AuditLog(tmp_path / "audit", clock=lambda: NOW, local_zone=UTC)

    def _begin(self, audit: Any, session_id: str) -> None:
        from scribe_desktop.encounter import unlinked_consent
        from scribe_desktop.session_mode import SessionMode

        audit.begin(
            session_id,
            consent=unlinked_consent(NOW - timedelta(minutes=30)),
            context=None,
            user_id=None,
            started_at=NOW - timedelta(minutes=30),
            mode=SessionMode.NORMAL,
            app_version="0.3.0",
            development_consent_version="development-consent-v1",
        )

    def _row(self, audit: Any, session_id: str) -> Any:
        row = audit.row_for(session_id)
        assert row is not None
        return row

    @pytest.mark.parametrize("shape", ["pending", "committed"])
    def test_an_interrupted_completion_is_repaired_at_start_up(
        self, tmp_path: Path, shape: str
    ) -> None:
        """``pending``: killed between the key deletion and the commit;
        ``committed``: killed after ``keep.commit()`` and before the audit
        update — no ``pending``, which ``reconcile_pending`` skips (round 6
        PR-MED-062). Both end ``archived`` with ``recording.kept_at``, and a
        second start changes nothing."""
        from scribe_desktop.app import sweep_with_archive

        sessions = tmp_path / "sessions"
        sessions.mkdir()
        completed = NOW - timedelta(days=2)  # round 12 LOW-012: not the audit's clock
        store = _store(tmp_path, clock=completed)
        audit = self._audit(tmp_path)
        sid = _kept(store, commit=shape == "committed")
        self._begin(audit, sid)  # its completion write never ran
        sweep_with_archive(sessions, store, frozenset(), audit=audit, repair_kept=True)
        row = self._row(audit, sid)
        assert row.past_session.state == "archived"
        assert row.recording.kept_at == completed
        before = row.to_bytes()
        sweep_with_archive(sessions, store, frozenset(), audit=audit, repair_kept=True)
        assert self._row(audit, sid).to_bytes() == before

    def test_a_sweep_tick_does_not_repair(self, tmp_path: Path) -> None:
        from scribe_desktop.app import sweep_with_archive

        sessions = tmp_path / "sessions"
        sessions.mkdir()
        store = _store(tmp_path)
        audit = self._audit(tmp_path)
        sid = _kept(store)
        self._begin(audit, sid)
        # Review round 11 LOW-010: tidy runs on the tick too (as
        # `clean_staging` does) — a zeroed recording's files go.
        dead = _kept(store)
        (store.root / dead / AUDIO_KEY_FILENAME).write_bytes(b"\0" * AUDIO_KEY_FILE_BYTES)
        sweep_with_archive(sessions, store, frozenset(), audit=audit)
        assert self._row(audit, sid).recording.kept_at is None
        assert not (store.root / dead / AUDIO_FILENAME).exists()
        assert not (store.root / dead / AUDIO_KEY_FILENAME).exists()

    @pytest.mark.parametrize("zeroed", [True, False], ids=["zeroed", "key_gone"])
    def test_a_deleted_untidied_recording_is_recorded_before_tidy(
        self, tmp_path: Path, zeroed: bool
    ) -> None:
        """Review round 11 LOW-004: Delete recording synced its zeros (or
        also removed the key) and the process stopped before its audit
        write — the start-up repair records the kept fact AND the deletion
        before ``tidy_dead_recordings`` removes that evidence; idempotent."""
        from scribe_desktop.app import sweep_with_archive

        sessions = tmp_path / "sessions"
        sessions.mkdir()
        completed = NOW - timedelta(days=2)  # round 12 LOW-012: not the audit's clock
        store = _store(tmp_path, clock=completed)
        audit = self._audit(tmp_path)
        sid = _kept(store)
        self._begin(audit, sid)
        key = store.root / sid / AUDIO_KEY_FILENAME
        if zeroed:
            key.write_bytes(b"\0" * AUDIO_KEY_FILE_BYTES)
        else:
            key.unlink()
        assert [listing.session_id for listing in store.deleted_recordings()] == [sid]
        sweep_with_archive(sessions, store, frozenset(), audit=audit, repair_kept=True)
        row = self._row(audit, sid)
        # Kept at the label's completion; deleted when found (the audit's now).
        assert (row.recording.kept_at, row.recording.deleted_at) == (completed, NOW)
        assert row.past_session.state == "archived"
        assert not (store.root / sid / AUDIO_FILENAME).exists()
        assert store.deleted_recordings() == []
        before = row.to_bytes()
        sweep_with_archive(sessions, store, frozenset(), audit=audit, repair_kept=True)
        assert self._row(audit, sid).to_bytes() == before

    def test_the_repair_never_remakes_a_pruned_row(self, tmp_path: Path) -> None:
        """Review round 11 LOW-003: a kept entry older than the audit's
        retention window ("Until I delete them") — its row the prune removed
        — is left alone, never re-made as a ``pre_audit`` row."""
        from scribe_desktop.app import sweep_with_archive

        sessions = tmp_path / "sessions"
        sessions.mkdir()
        old = NOW - timedelta(days=366 * 8)
        store = _store(tmp_path, clock=old)
        audit = self._audit(tmp_path)
        sid = _kept(store, started=old - timedelta(minutes=20))
        assert not audit.keeps_rows_of(old) and audit.keeps_rows_of(NOW)
        sweep_with_archive(sessions, store, frozenset(), audit=audit, repair_kept=True)
        assert audit.row_for(sid) is None
        assert store.recording_kept(sid)

    def test_the_window_is_judged_by_the_session_start(self, tmp_path: Path) -> None:
        """Review round 12 LOW-001: ``begin`` files a row in the month the
        session STARTED. Started 31 Aug 2019 (its month pruned by NOW, 1 Oct
        2026) and completed 1 Sep 2019 (that month not yet): the row is gone,
        so the repair re-makes nothing."""
        from scribe_desktop.app import sweep_with_archive

        sessions = tmp_path / "sessions"
        sessions.mkdir()
        started = datetime(2019, 8, 31, 23, 50, tzinfo=UTC)
        completed = datetime(2019, 9, 1, 0, 10, tzinfo=UTC)
        store = _store(tmp_path, clock=completed)
        audit = self._audit(tmp_path)
        sid = _kept(store, started=started)
        assert not audit.keeps_rows_of(started) and audit.keeps_rows_of(completed)
        sweep_with_archive(sessions, store, frozenset(), audit=audit, repair_kept=True)
        assert audit.row_for(sid) is None

    @pytest.mark.parametrize("has_row", [True, False], ids=["row", "pruned"])
    def test_an_unreadable_labels_deletion_never_remakes_a_row(
        self, tmp_path: Path, has_row: bool
    ) -> None:
        """Review round 14 PR-MED-001: a deleted-but-untidied recording whose
        label cannot be read has no date to judge the retention window by —
        its deletion lands on the EXISTING row only; with no row (pruned)
        nothing is re-made, and the evidence is tidied (nothing to record)."""
        from scribe_desktop.app import sweep_with_archive

        def refuse(_directory: Path) -> SessionCrypto:
            raise OSError("DPAPI refused")

        sessions = tmp_path / "sessions"
        sessions.mkdir()
        sid = _kept(_store(tmp_path))
        (_store(tmp_path).root / sid / AUDIO_KEY_FILENAME).write_bytes(
            b"\0" * AUDIO_KEY_FILE_BYTES
        )
        store = _store(tmp_path, unwrap_key=refuse)
        [listing] = store.deleted_recordings()
        assert listing.label is None
        audit = self._audit(tmp_path)
        if has_row:
            self._begin(audit, sid)
        sweep_with_archive(sessions, store, frozenset(), audit=audit)
        if has_row:
            assert self._row(audit, sid).recording.deleted_at == NOW
        else:
            assert audit.row_for(sid) is None
        assert not (store.root / sid / AUDIO_FILENAME).exists()

    @pytest.mark.parametrize("case", ["reset", "pruned", "unreadable_row", "unreadable_none"])
    def test_a_reconciled_commit_is_dated_by_its_label(self, tmp_path: Path, case: str) -> None:
        """Review round 15 PR-MED-001: ``reconcile_pending``'s ``archived``
        follows the kept-fact repair's rule — a reset-away row is re-made in
        the session's START month, a pruned one is never re-made, and with
        no readable label it lands on an existing row only."""
        from scribe_desktop.app import sweep_with_archive

        def refuse(_directory: Path) -> SessionCrypto:
            raise OSError("DPAPI refused")

        sessions = tmp_path / "sessions"
        sessions.mkdir()
        started = (
            datetime(2018, 8, 31, 23, 50, tzinfo=UTC)
            if case == "pruned"
            else datetime(2026, 8, 31, 23, 50, tzinfo=UTC)
        )
        writer = _store(tmp_path, clock=started + timedelta(minutes=20))
        source = replace(_source(), created_at=started.timestamp())
        writer.write_entry(source, LINKED)  # pending; its source key is absent
        sid = source.session_id
        unreadable = case.startswith("unreadable")
        store = _store(tmp_path, unwrap_key=refuse) if unreadable else writer
        audit = self._audit(tmp_path)
        if case == "unreadable_row":
            self._begin(audit, sid)
        sweep_with_archive(sessions, store, frozenset(), audit=audit)
        assert not (store.root / sid / PENDING_FILENAME).exists()
        row = audit.row_for(sid)
        if case in ("pruned", "unreadable_none"):
            assert row is None
        else:
            assert row is not None and row.past_session.state == "archived"
            if case == "reset":
                assert (row.origin, row.session_date) == ("pre_audit", started.date())

    def test_a_remade_row_is_filed_in_the_month_the_session_started(
        self, tmp_path: Path
    ) -> None:
        """Review round 13 LOW-013: a kept entry whose row is gone (reset
        away) is re-made as ``pre_audit`` in its session's START month, where
        ``begin`` filed it — not the completion's."""
        from scribe_desktop.app import sweep_with_archive

        sessions = tmp_path / "sessions"
        sessions.mkdir()
        started = datetime(2026, 8, 31, 23, 50, tzinfo=UTC)
        completed = datetime(2026, 9, 1, 0, 10, tzinfo=UTC)
        store = _store(tmp_path, clock=completed)
        audit = self._audit(tmp_path)
        sid = _kept(store, started=started)
        sweep_with_archive(sessions, store, frozenset(), audit=audit, repair_kept=True)
        row = self._row(audit, sid)
        assert row.origin == "pre_audit"
        assert row.session_date == started.date()
        assert row.recording.kept_at == completed

    def test_expiry_records_the_deletion_of_a_kept_row_whose_completion_failed(
        self, tmp_path: Path
    ) -> None:
        from scribe_desktop.ui import past_sessions_view as view

        completed = NOW - WINDOW - timedelta(days=1)
        store = _store(tmp_path, clock=completed)
        audit = self._audit(tmp_path)
        sid = _kept(store)
        self._begin(audit, sid)  # its completion write never landed
        view.retention_sweep(store, audit, SEVEN, NOW)
        row = self._row(audit, sid)
        assert row.past_session.state == "expired"
        assert (row.recording.kept_at, row.recording.deleted_at) == (completed, NOW)

    @pytest.mark.parametrize("case", ["reset", "pruned"])
    def test_the_retention_sweep_follows_the_unattended_rule(
        self, tmp_path: Path, case: str
    ) -> None:
        """Review round 16 PR-MED-001: the sweep's kept fact, and its
        ``expired`` outcome, are UNATTENDED writes — a reset-away row is
        re-made in the session's START month; a row whose start month the
        prune has passed is never re-made, even when the completion's month
        is still kept (started 31 Aug 2027, completed 1 Sep 2027), and the
        entry still expires. Dated 2027 / 2034: a ``pre_audit`` date before
        2026 is untrusted (dated now, ``audit._EARLIEST_SESSION``)."""
        from scribe_desktop.audit import AuditLog
        from scribe_desktop.ui import past_sessions_view as view

        if case == "reset":
            started = datetime(2027, 9, 30, 8, 40, tzinfo=UTC)
            completed = datetime(2027, 9, 30, 9, 0, tzinfo=UTC)
            later = datetime(2034, 10, 1, 9, 0, tzinfo=UTC)
        else:
            started = datetime(2027, 8, 31, 23, 50, tzinfo=UTC)
            completed = datetime(2027, 9, 1, 0, 10, tzinfo=UTC)
            later = datetime(2034, 9, 15, 9, 0, tzinfo=UTC)
        store = _store(tmp_path, clock=completed)
        audit = AuditLog(tmp_path / "audit", clock=lambda: later, local_zone=UTC)
        sid = _kept(store, started=started)
        assert audit.keeps_rows_of(completed)
        assert audit.keeps_rows_of(started) is (case == "reset")
        report = view.retention_sweep(store, audit, SEVEN, later)
        assert [session_id for session_id, _ in report.expired] == [sid]
        assert not (store.root / sid).exists()
        row = audit.row_for(sid)
        if case == "pruned":
            assert row is None
        else:
            assert row is not None
            assert (row.origin, row.session_date) == ("pre_audit", started.date())
            assert row.past_session.state == "expired"
            assert (row.recording.kept_at, row.recording.deleted_at) == (completed, later)


# ---------------------------------------------------------------------------
# Export recording (development-recordings plan Task 3.3; D10, C2, C5): the
# store's custody of the one unencrypted file — the exclusive ``.part``, the
# export ledger OUTSIDE the entries, and its start-up recovery.
# ---------------------------------------------------------------------------

_FAKE_LEDGER = b"FAKE-LEDGER-KEY:"


def _fake_ledger_wrap(crypto: SessionCrypto, root: Path) -> None:
    (root / past_sessions.EXPORT_LEDGER_KEY_FILENAME).write_bytes(
        _FAKE_LEDGER + crypto.export_key()
    )


def _fake_ledger_unwrap(root: Path) -> SessionCrypto:
    blob = (root / past_sessions.EXPORT_LEDGER_KEY_FILENAME).read_bytes()
    if not blob.startswith(_FAKE_LEDGER):
        raise KeyCustodyError("not a ledger key")
    return SessionCrypto.from_key(blob[len(_FAKE_LEDGER) :])


def _export_store(tmp_path: Path) -> PastSessionStore:
    return _store(
        tmp_path, wrap_ledger_key=_fake_ledger_wrap, unwrap_ledger_key=_fake_ledger_unwrap
    )


def _anywhere(_folder: Path) -> str | None:
    """The store's destination check, admitting every folder — the location
    rule is ``exclusions.check_export_location``'s, tested there."""
    return None


def _wav_pcm(path: Path) -> tuple[int, int, int, bytes]:
    import wave

    with wave.open(str(path), "rb") as reader:
        return (
            reader.getnchannels(),
            reader.getsampwidth(),
            reader.getframerate(),
            reader.readframes(reader.getnframes()),
        )


def _left_part(store: PastSessionStore, folder: Path, sid: str) -> Path:
    """What a hard kill mid-export leaves: the exclusively created ``.part``
    (holding some plaintext) and its ledger row."""
    part = folder / f"{sid}.wav.part"
    descriptor = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(b"RIFF partial plaintext")
        status = os.fstat(stream.fileno())
    identity = past_sessions.ExportIdentity(file_index=status.st_ino, device=status.st_dev)
    rows = store._read_ledger()
    rows[sid] = past_sessions.ExportRow(folder=str(folder), identity=identity)
    store._write_ledger(rows)
    return part


class TestExportRecording:
    def test_the_kept_recording_is_written_as_a_16k_mono_pcm16_wav(self, tmp_path: Path) -> None:
        store = _export_store(tmp_path)
        sid = _kept(store)
        folder = tmp_path / "labelling"
        folder.mkdir()
        final = store.export_recording(sid, folder, check_destination=_anywhere)
        assert final == folder / f"{sid}.wav"
        assert _wav_pcm(final) == (1, 2, 16_000, b"".join(_PCM))
        assert sorted(p.name for p in folder.iterdir()) == [f"{sid}.wav"]  # no .part left
        assert store._read_ledger() == {}  # the row dropped after the rename
        # What the app writes names its version (the read refuses one without).
        crypto = _fake_ledger_unwrap(store.root)
        stored = crypto.decrypt(
            (store.root / past_sessions.EXPORT_LEDGER_FILENAME).read_bytes(),
            past_sessions._EXPORT_LEDGER_AAD,
        )
        assert b'"schema_version":1' in stored
        # The ledger lives OUTSIDE every entry, and the listing ignores it.
        assert (store.root / past_sessions.EXPORT_LEDGER_FILENAME).is_file()
        assert [listing.session_id for listing in store.list_entries()] == [sid]
        assert store.recording_kept(sid)  # the recording itself is untouched

    def test_the_row_is_written_after_the_create_and_before_the_first_chunk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop import speech

        store = _export_store(tmp_path)
        sid = _kept(store)
        part = tmp_path / f"{sid}.wav.part"
        real_write = speech.write_wav
        seen: list[Any] = []

        def spy(target: Any, chunks: Any) -> int:
            status = os.stat(part)
            row = store._read_ledger()[sid]
            seen.append((status.st_size, row.folder, row.identity.file_index, status.st_ino))
            return real_write(target, chunks)

        monkeypatch.setattr(speech, "write_wav", spy)
        store.export_recording(sid, tmp_path, check_destination=_anywhere)
        [(size, folder, recorded, actual)] = seen
        assert (size, folder, recorded) == (0, str(tmp_path), actual)

    def test_the_resolved_folder_is_checked_just_before_the_create(
        self, tmp_path: Path
    ) -> None:
        """Codex round 23 PR-HIGH-001: the junction the caller checked is
        retargeted while it waits on the user — the store checks the folder
        it RESOLVED, and a refusal writes nothing there."""
        store = _export_store(tmp_path)
        sid = _kept(store)
        allowed = tmp_path / "allowed"
        forbidden = tmp_path / "forbidden"
        allowed.mkdir()
        forbidden.mkdir()
        link = tmp_path / "via"
        _link("junction", link, allowed)
        checked: list[str] = []

        def check(folder: Path) -> str | None:
            checked.append(str(folder))
            if Path(os.path.realpath(folder)) == Path(os.path.realpath(forbidden)):
                return "that folder is inside OneDrive, which can copy the file off this computer."
            return None

        assert check(link) is None  # what the caller saw before its question
        checked.clear()
        link.rmdir()  # the junction itself, never its target
        _link("junction", link, forbidden)  # retargeted during the wait
        with pytest.raises(past_sessions.ExportDestinationRefused) as caught:
            store.export_recording(sid, link, check_destination=check)
        assert caught.value.reason == "export_destination_refused"
        assert caught.value.line is not None and "OneDrive" in caught.value.line
        assert checked == [os.path.realpath(forbidden)]  # the RESOLVED folder
        assert list(forbidden.iterdir()) == [] and list(allowed.iterdir()) == []
        assert store._read_ledger() == {}

    def test_a_destination_check_that_raises_refuses(self, tmp_path: Path) -> None:
        store = _export_store(tmp_path)
        sid = _kept(store)

        def broken(_folder: Path) -> str | None:
            raise OSError(errno.EIO, "cannot look")

        with pytest.raises(past_sessions.ExportDestinationRefused) as caught:
            store.export_recording(sid, tmp_path, check_destination=broken)
        assert caught.value.line is None
        assert not (tmp_path / f"{sid}.wav.part").exists()
        assert not (tmp_path / f"{sid}.wav").exists()

    def test_a_file_already_named_part_is_never_adopted(self, tmp_path: Path) -> None:
        store = _export_store(tmp_path)
        sid = _kept(store)
        part = tmp_path / f"{sid}.wav.part"
        part.write_bytes(b"the practitioner's own file")
        with pytest.raises(PastSessionError) as caught:
            store.export_recording(sid, tmp_path, check_destination=_anywhere)
        assert caught.value.reason == "export_part_exists"
        assert part.read_bytes() == b"the practitioner's own file"
        assert not (tmp_path / f"{sid}.wav").exists()
        assert store._read_ledger() == {}

    def test_an_existing_wav_is_never_overwritten(self, tmp_path: Path) -> None:
        store = _export_store(tmp_path)
        sid = _kept(store)
        final = tmp_path / f"{sid}.wav"
        final.write_bytes(b"an earlier export")
        with pytest.raises(PastSessionError) as caught:
            store.export_recording(sid, tmp_path, check_destination=_anywhere)
        assert caught.value.reason == "export_exists"
        assert final.read_bytes() == b"an earlier export"
        assert not (tmp_path / f"{sid}.wav.part").exists()

    def test_an_entry_without_a_kept_recording_writes_nothing(self, tmp_path: Path) -> None:
        store = _export_store(tmp_path)
        sid = _published(store)
        with pytest.raises(PastSessionError) as caught:
            store.export_recording(sid, tmp_path, check_destination=_anywhere)
        assert caught.value.reason == "recording_not_kept"
        assert sorted(p.name for p in tmp_path.iterdir()) == ["past_sessions"]

    def test_a_corrupt_later_chunk_leaves_no_file_and_no_row(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``iter_chunks`` yields earlier plaintext before a later chunk
        fails authentication: the ``.part`` holding it is removed."""
        store = _export_store(tmp_path)
        sid = _kept(store)

        def broken(session_id: str) -> Any:
            yield _PCM[0]
            raise PastSessionError("unreadable")

        monkeypatch.setattr(store, "read_recording", broken)
        folder = tmp_path / "out"
        folder.mkdir()
        with pytest.raises(PastSessionError) as caught:
            store.export_recording(sid, folder, check_destination=_anywhere)
        assert caught.value.reason == "unreadable"
        assert list(folder.iterdir()) == []
        assert store._read_ledger() == {}

    def test_a_real_corrupt_chunk_on_disk_leaves_no_file(self, tmp_path: Path) -> None:
        store = _export_store(tmp_path)
        sid = _kept(store)
        audio = store.root / sid / AUDIO_FILENAME
        blob = bytearray(audio.read_bytes())
        blob[-40] ^= 0xFF  # a later chunk (or the footer) fails authentication
        audio.write_bytes(bytes(blob))
        folder = tmp_path / "out"
        folder.mkdir()
        with pytest.raises(PastSessionError) as caught:
            store.export_recording(sid, folder, check_destination=_anywhere)
        # Review round 22: the recording's damage, never this account's.
        assert caught.value.reason == "recording_unreadable"
        assert "may be damaged" in str(caught.value)
        assert list(folder.iterdir()) == []
        assert store._read_ledger() == {}

    def test_a_failed_rename_leaves_neither_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = _export_store(tmp_path)
        sid = _kept(store)
        folder = tmp_path / "out"
        folder.mkdir()

        def refuse(*_args: Any) -> None:
            raise PermissionError(errno.EACCES, "denied")

        monkeypatch.setattr(past_sessions.os, "rename", refuse)
        with pytest.raises(PastSessionError) as caught:
            store.export_recording(sid, folder, check_destination=_anywhere)
        assert caught.value.reason == "export_failed"
        assert list(folder.iterdir()) == []
        assert store._read_ledger() == {}

    def test_a_part_that_cannot_be_removed_keeps_its_row_for_the_next_start(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = _export_store(tmp_path)
        sid = _kept(store)
        folder = tmp_path / "out"
        folder.mkdir()

        def refuse(*_args: Any) -> None:
            raise PermissionError(errno.EACCES, "denied")

        # Codex round 27 PR-LOW-001: the test's own patches are SCOPED — an
        # ``undo()`` would also lift the conftest's injected ``.part`` kernel.
        with monkeypatch.context() as patched:
            patched.setattr(past_sessions.os, "rename", refuse)
            patched.setattr(past_sessions, "_remove_part", lambda *_args: False)
            with pytest.raises(PastSessionError) as caught:
                store.export_recording(sid, folder, check_destination=_anywhere)
        assert caught.value.reason == "export_cleanup_failed"
        part = folder / f"{sid}.wav.part"
        assert part.is_file()
        assert sid in store._read_ledger()
        # The next start removes it — it is still the file the app created.
        assert _export_store(tmp_path).recover_exports() == past_sessions.ExportRecovery()
        assert not part.exists()
        assert store._read_ledger() == {}

    def test_a_new_export_resolves_an_earlier_unresolved_row_first(self, tmp_path: Path) -> None:
        store = _export_store(tmp_path)
        earlier, sid = _kept(store), _kept(store)
        left = _left_part(store, tmp_path, earlier)
        store.export_recording(sid, tmp_path, check_destination=_anywhere)
        assert not left.exists()
        assert (tmp_path / f"{sid}.wav").is_file()
        assert store._read_ledger() == {}

    def test_a_replaced_part_refuses_the_new_export_and_is_never_deleted(
        self, tmp_path: Path
    ) -> None:
        store = _export_store(tmp_path)
        earlier, sid = _kept(store), _kept(store)
        left = _left_part(store, tmp_path, earlier)
        left.unlink()
        left.write_bytes(b"a different file now")  # a new identity at that name
        with pytest.raises(PastSessionError) as caught:
            store.export_recording(sid, tmp_path, check_destination=_anywhere)
        assert caught.value.reason == "export_unresolved"
        # Review round 21 LOW-005: the refusal names the file to delete.
        assert isinstance(caught.value, past_sessions.ExportUnresolvedError)
        assert caught.value.session_ids == (earlier,)
        assert left.read_bytes() == b"a different file now"
        assert not (tmp_path / f"{sid}.wav.part").exists()
        assert not (tmp_path / f"{sid}.wav").exists()
        assert earlier in store._read_ledger()

    def test_an_undeletable_part_refuses_the_new_export(
        self, tmp_path: Path, part_kernel: Any
    ) -> None:
        store = _export_store(tmp_path)
        earlier, sid = _kept(store), _kept(store)
        left = _left_part(store, tmp_path, earlier)
        part_kernel.refuse_delete = True
        with pytest.raises(PastSessionError) as caught:
            store.export_recording(sid, tmp_path, check_destination=_anywhere)
        assert caught.value.reason == "export_unresolved"
        assert left.is_file()

    def test_an_unreadable_ledger_refuses_an_export_and_writes_nothing(
        self, tmp_path: Path
    ) -> None:
        store = _export_store(tmp_path)
        sid = _kept(store)
        (store.root / past_sessions.EXPORT_LEDGER_FILENAME).write_bytes(b"not a ledger")
        with pytest.raises(PastSessionError) as caught:
            store.export_recording(sid, tmp_path, check_destination=_anywhere)
        assert caught.value.reason == "export_ledger_unreadable"
        assert not (tmp_path / f"{sid}.wav.part").exists()

    def test_a_close_that_fails_after_a_failure_still_removes_the_part(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review round 20 MED-001: the close fails (a full disk fails its
        flush) and so does the clean-up's close — the clean-up still runs,
        and only a ``PastSessionError`` leaves."""
        store = _export_store(tmp_path)
        sid = _kept(store)
        folder = tmp_path / "out"
        folder.mkdir()
        real_fdopen = os.fdopen

        class _CloseFails:
            def __init__(self, real: Any) -> None:
                self._real = real

            def __getattr__(self, name: str) -> Any:
                return getattr(self._real, name)

            def close(self) -> None:
                self._real.close()
                raise OSError(errno.ENOSPC, "full")

        monkeypatch.setattr(
            past_sessions.os, "fdopen", lambda *args: _CloseFails(real_fdopen(*args))
        )
        with pytest.raises(PastSessionError) as caught:
            store.export_recording(sid, folder, check_destination=_anywhere)
        assert caught.value.reason == "export_failed"
        assert list(folder.iterdir()) == []
        assert store._read_ledger() == {}

    def test_a_row_that_cannot_be_written_writes_no_audio(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop import speech

        store = _export_store(tmp_path)
        sid = _kept(store)
        folder = tmp_path / "out"
        folder.mkdir()
        written: list[Any] = []
        monkeypatch.setattr(speech, "write_wav", lambda *args: written.append(args))

        def refuse(_rows: Any) -> None:
            raise OSError(errno.EACCES, "denied")

        monkeypatch.setattr(store, "_write_ledger", refuse)
        with pytest.raises(PastSessionError) as caught:
            store.export_recording(sid, folder, check_destination=_anywhere)
        assert caught.value.reason == "export_unrecorded"
        assert written == []
        assert list(folder.iterdir()) == []  # the empty .part removed

    def test_a_resolution_that_cannot_be_recorded_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = _export_store(tmp_path)
        earlier, sid = _kept(store), _kept(store)
        left = _left_part(store, tmp_path, earlier)
        left.unlink()  # deleted by hand: this export resolves the row

        def refuse(_rows: Any) -> None:
            raise OSError(errno.EACCES, "denied")

        monkeypatch.setattr(store, "_write_ledger", refuse)
        with pytest.raises(PastSessionError) as caught:
            store.export_recording(sid, tmp_path, check_destination=_anywhere)
        assert caught.value.reason == "export_unrecorded"
        assert not (tmp_path / f"{sid}.wav.part").exists()
        assert not (tmp_path / f"{sid}.wav").exists()
        assert earlier in store._read_ledger()

    def test_a_ledger_that_cannot_be_read_this_time_refuses_and_is_never_reset(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review round 20 LOW-004: a transient read error is not damage."""
        store = _export_store(tmp_path)
        earlier, sid = _kept(store), _kept(store)
        left = _left_part(store, tmp_path, earlier)

        real_read = past_sessions._read_capped

        def busy(path: Path, cap: int) -> bytes:
            if path.name == past_sessions.EXPORT_LEDGER_FILENAME:
                raise PermissionError(errno.EACCES, "in use")
            return real_read(path, cap)

        monkeypatch.setattr(past_sessions, "_read_capped", busy)
        with pytest.raises(PastSessionError) as caught:
            store.export_recording(sid, tmp_path, check_destination=_anywhere)
        assert caught.value.reason == "export_ledger_busy"
        assert not (tmp_path / f"{sid}.wav.part").exists()
        assert store.recover_exports() == past_sessions.ExportRecovery(busy=True)
        monkeypatch.undo()
        assert earlier in store._read_ledger()  # never started again
        assert left.is_file()

    @pytest.mark.parametrize("wrapped", [True, False])
    def test_a_ledger_key_that_cannot_be_read_this_time_is_busy_too(
        self, tmp_path: Path, wrapped: bool
    ) -> None:
        """Review round 21 LOW-001: the KEY file locked by a scanner — raw,
        or wrapped in ``KeyCustodyError`` as ``unwrap_key_from_file`` does —
        is busy; the ledger and its row survive."""
        store = _export_store(tmp_path)
        sid = _kept(store)
        left = _left_part(store, tmp_path, sid)

        def locked(_root: Path) -> SessionCrypto:
            error = PermissionError(errno.EACCES, "in use")
            if not wrapped:
                raise error
            raise KeyCustodyError("key custody blob unreadable") from error

        busy = _store(tmp_path, wrap_ledger_key=_fake_ledger_wrap, unwrap_ledger_key=locked)
        assert busy.recover_exports() == past_sessions.ExportRecovery(busy=True)
        assert sid in store._read_ledger()
        assert left.is_file()

    def test_a_damaged_ledger_key_with_no_ledger_is_replaced_at_the_next_export(
        self, tmp_path: Path
    ) -> None:
        """Hardening review round 44 SEC-002: a reset whose key unlink failed
        leaves ``exports-key.dpapi`` with no ``exports.enc``; a key that does
        not unwrap holds no row, so the next export replaces it rather than
        failing every export for good."""
        store = _export_store(tmp_path)
        sid = _kept(store)
        key = store.root / past_sessions.EXPORT_LEDGER_KEY_FILENAME
        key.write_bytes(b"not a ledger key")
        assert not (store.root / past_sessions.EXPORT_LEDGER_FILENAME).exists()
        folder = tmp_path / "out"
        folder.mkdir()
        final = store.export_recording(sid, folder, check_destination=_anywhere)
        assert final == folder / f"{sid}.wav"
        assert key.read_bytes().startswith(_FAKE_LEDGER)  # a fresh key
        assert store._read_ledger() == {}

    def test_a_damaged_ledger_key_beside_a_ledger_is_never_replaced(
        self, tmp_path: Path
    ) -> None:
        """SEC-002's limit: with a ledger present its rows live under that
        key, so a key that does not unwrap still refuses (start-up resets
        both, with its line)."""
        store = _export_store(tmp_path)
        earlier, sid = _kept(store), _kept(store)
        _left_part(store, tmp_path, earlier)
        key = store.root / past_sessions.EXPORT_LEDGER_KEY_FILENAME
        key.write_bytes(b"not a ledger key")
        with pytest.raises(PastSessionError):
            store.export_recording(sid, tmp_path, check_destination=_anywhere)
        assert key.read_bytes() == b"not a ledger key"
        assert (store.root / past_sessions.EXPORT_LEDGER_FILENAME).exists()

    def test_a_missing_ledger_key_is_damage_and_resets(self, tmp_path: Path) -> None:
        store = _export_store(tmp_path)
        sid = _kept(store)
        _left_part(store, tmp_path, sid)
        (store.root / past_sessions.EXPORT_LEDGER_KEY_FILENAME).unlink()
        assert store.recover_exports() == past_sessions.ExportRecovery(reset=True)

    def test_an_identity_that_cannot_be_read_removes_the_part_by_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review round 21 LOW-003: no identity, so no row — the file the
        export created an instant ago goes by its name."""
        store = _export_store(tmp_path)
        sid = _kept(store)
        folder = tmp_path / "out"
        folder.mkdir()

        def refuse(_descriptor: int) -> Any:
            raise OSError(errno.EIO, "fstat")

        monkeypatch.setattr(past_sessions.os, "fstat", refuse)
        with pytest.raises(PastSessionError) as caught:
            store.export_recording(sid, folder, check_destination=_anywhere)
        monkeypatch.undo()
        assert caught.value.reason == "export_failed"
        assert list(folder.iterdir()) == []
        assert store._read_ledger() == {}

    def test_a_row_that_cannot_be_dropped_after_the_rename_is_resolved_later(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review round 21 LOW-003: the export succeeded; the stale row names
        a ``.part`` that is gone, which the next resolution drops — the
        finished ``.wav`` is never touched."""
        store = _export_store(tmp_path)
        sid = _kept(store)
        real_write = store._write_ledger

        def refuse_empty(rows: Any) -> None:
            if not rows:
                raise OSError(errno.EACCES, "denied")
            real_write(rows)

        with monkeypatch.context() as patched:  # codex round 27 PR-LOW-001
            patched.setattr(store, "_write_ledger", refuse_empty)
            final = store.export_recording(sid, tmp_path, check_destination=_anywhere)
        assert final.is_file()
        assert sid in store._read_ledger()
        assert store.recover_exports() == past_sessions.ExportRecovery()
        assert store._read_ledger() == {}
        assert final.is_file()

    def test_a_recovery_that_cannot_be_recorded_is_resolved_again(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review round 21 LOW-003: the ``.part`` is removed but the ledger
        rewrite fails — the row stays, and the next start drops it."""
        store = _export_store(tmp_path)
        sid = _kept(store)
        left = _left_part(store, tmp_path, sid)

        def refuse(_rows: Any) -> None:
            raise OSError(errno.EACCES, "denied")

        with monkeypatch.context() as patched:  # codex round 27 PR-LOW-001
            patched.setattr(store, "_write_ledger", refuse)
            assert store.recover_exports() == past_sessions.ExportRecovery()
        assert not left.exists()
        assert sid in store._read_ledger()
        assert store.recover_exports() == past_sessions.ExportRecovery()
        assert store._read_ledger() == {}

    def test_a_relative_folder_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 22: the folder EXISTS relative to the working directory, so
        only the refusal — not a failing create — keeps it empty."""
        store = _export_store(tmp_path)
        sid = _kept(store)
        (tmp_path / "out").mkdir()
        monkeypatch.chdir(tmp_path)
        with pytest.raises(PastSessionError) as caught:
            store.export_recording(sid, Path("out"), check_destination=_anywhere)
        assert caught.value.reason == "export_failed"
        assert list((tmp_path / "out").iterdir()) == []
        assert store._read_ledger() == {}

    def test_the_resolved_folder_is_exported_into_and_recorded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review round 21 LOW-007, pinned in round 22: through a junction the
        file lands in, and the ledger names, the folder the link resolves to."""
        from scribe_desktop import speech

        store = _export_store(tmp_path)
        sid = _kept(store)
        real = tmp_path / "real"
        real.mkdir()
        link = tmp_path / "via"
        _link("junction", link, real)
        seen: list[str] = []
        real_write = speech.write_wav

        def spy(target: Any, chunks: Any) -> int:
            seen.append(store._read_ledger()[sid].folder)
            return real_write(target, chunks)

        monkeypatch.setattr(speech, "write_wav", spy)
        final = store.export_recording(sid, link, check_destination=_anywhere)
        assert seen == [os.path.realpath(real)]
        assert final == Path(os.path.realpath(real)) / f"{sid}.wav"
        assert (real / f"{sid}.wav").is_file()

    def test_a_folder_that_cannot_be_resolved_writes_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = _export_store(tmp_path)
        sid = _kept(store)

        def refuse(_path: Any) -> str:
            raise OSError(errno.EIO, "cannot resolve")

        monkeypatch.setattr(past_sessions.os.path, "realpath", refuse)
        with pytest.raises(PastSessionError) as caught:
            store.export_recording(sid, tmp_path, check_destination=_anywhere)
        monkeypatch.undo()
        assert caught.value.reason == "export_failed"
        assert not (tmp_path / f"{sid}.wav.part").exists()
        assert store._read_ledger() == {}

    def test_an_export_file_that_cannot_be_opened_as_a_stream_is_removed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review round 22 LOW: nothing that can fail sits between the
        create and the clean-up — a failing ``fdopen`` removes the empty
        file, and only a ``PastSessionError`` leaves."""
        store = _export_store(tmp_path)
        sid = _kept(store)
        folder = tmp_path / "out"
        folder.mkdir()

        def refuse(*_args: Any) -> Any:
            raise OSError(errno.EMFILE, "too many")

        monkeypatch.setattr(past_sessions.os, "fdopen", refuse)
        with pytest.raises(PastSessionError) as caught:
            store.export_recording(sid, folder, check_destination=_anywhere)
        monkeypatch.undo()
        assert caught.value.reason == "export_failed"
        assert list(folder.iterdir()) == []
        assert store._read_ledger() == {}

    def test_a_deleted_export_folder_drops_its_row(self, tmp_path: Path) -> None:
        """Review round 20 LOW-005 (kept): a folder deleted by hand takes its
        partial file with it — the row must not refuse every later export."""
        store = _export_store(tmp_path)
        sid = _kept(store)
        folder = tmp_path / "out"
        folder.mkdir()
        _left_part(store, folder, sid)
        shutil.rmtree(folder)
        assert store.recover_exports() == past_sessions.ExportRecovery()
        assert store._read_ledger() == {}

    @pytest.mark.parametrize("destroyer", ["delete_now", "expiry"])
    def test_the_row_survives_its_entry(self, tmp_path: Path, destroyer: str) -> None:
        """Round 6 PR-MED-061: the ledger is OUTSIDE the entries, so Delete
        now and expiry of the entry never erase the record of its export."""
        store = _export_store(tmp_path)
        sid = _kept(store)
        left = _left_part(store, tmp_path, sid)
        if destroyer == "delete_now":
            store.delete_entry(sid)
        else:
            assert store.sweep(SEVEN, NOW + WINDOW + timedelta(days=1)) == [sid]
        assert not (store.root / sid).exists()
        assert sid in store._read_ledger()
        assert store.recover_exports() == past_sessions.ExportRecovery()
        assert not left.exists()


class TestRecoverExports:
    def test_nothing_to_recover_reads_nothing(self, tmp_path: Path) -> None:
        unwraps = _Unwraps()
        store = _store(
            tmp_path, wrap_ledger_key=_fake_ledger_wrap, unwrap_ledger_key=unwraps
        )
        assert store.recover_exports() == past_sessions.ExportRecovery()
        assert unwraps.calls == 0
        assert not store.root.exists()  # nothing created either

    def test_a_left_over_part_is_deleted_and_a_finished_wav_spared(self, tmp_path: Path) -> None:
        store = _export_store(tmp_path)
        sid, done = _kept(store), _kept(store)
        # Codex round 23 PR-LOW-002: the finished export FIRST — an export
        # resolves earlier rows itself, so a leftover made before it would
        # already be gone and this recovery would prove nothing.
        store.export_recording(done, tmp_path, check_destination=_anywhere)
        finished = tmp_path / f"{done}.wav"
        left = _left_part(store, tmp_path, sid)
        assert left.is_file() and sid in store._read_ledger()  # really left over
        assert store.recover_exports() == past_sessions.ExportRecovery()
        assert not left.exists()
        assert finished.is_file()  # the practitioner's file, never touched
        assert store._read_ledger() == {}

    def test_a_replaced_part_is_spared_and_its_row_kept(self, tmp_path: Path) -> None:
        store = _export_store(tmp_path)
        sid = _kept(store)
        left = _left_part(store, tmp_path, sid)
        left.unlink()
        left.write_bytes(b"not the app's file")
        assert store.recover_exports() == past_sessions.ExportRecovery(kept=(sid,))
        assert left.read_bytes() == b"not the app's file"
        assert sid in store._read_ledger()
        # Deleted by hand: the next start drops the row.
        left.unlink()
        assert store.recover_exports() == past_sessions.ExportRecovery()
        assert store._read_ledger() == {}

    def test_an_undeletable_part_keeps_its_row(
        self, tmp_path: Path, part_kernel: Any
    ) -> None:
        store = _export_store(tmp_path)
        sid = _kept(store)
        left = _left_part(store, tmp_path, sid)
        part_kernel.refuse_delete = True
        assert store.recover_exports() == past_sessions.ExportRecovery(kept=(sid,))
        assert left.is_file()
        assert sid in store._read_ledger()

    def test_a_file_swapped_in_after_the_check_is_never_deleted(
        self, tmp_path: Path, part_kernel: Any
    ) -> None:
        """Codex round 24 PR-MED-001: the deletion goes through the handle
        whose identity was read, never the path — a file put at the path
        after the check is the practitioner's and stays."""
        store = _export_store(tmp_path)
        sid = _kept(store)
        left = _left_part(store, tmp_path, sid)
        part_kernel.swap_after_status = b"the practitioner's own file"
        store.recover_exports()
        assert left.read_bytes() == b"the practitioner's own file"

    def test_a_part_another_program_holds_open_keeps_its_row(
        self, tmp_path: Path, part_kernel: Any
    ) -> None:
        store = _export_store(tmp_path)
        sid = _kept(store)
        left = _left_part(store, tmp_path, sid)
        part_kernel.refuse_open = True
        assert store.recover_exports() == past_sessions.ExportRecovery(kept=(sid,))
        assert left.is_file()
        assert sid in store._read_ledger()

    @pytest.mark.parametrize("damage", ["bytes", "key"])
    def test_an_unreadable_ledger_is_reset_with_one_line(
        self, tmp_path: Path, damage: str
    ) -> None:
        from scribe_desktop.ui import past_sessions_view as view

        store = _export_store(tmp_path)
        sid = _kept(store)
        left = _left_part(store, tmp_path, sid)
        name = (
            past_sessions.EXPORT_LEDGER_FILENAME
            if damage == "bytes"
            else past_sessions.EXPORT_LEDGER_KEY_FILENAME
        )
        (store.root / name).write_bytes(b"damaged")
        recovery = store.recover_exports()
        assert recovery == past_sessions.ExportRecovery(reset=True)
        assert not (store.root / past_sessions.EXPORT_LEDGER_FILENAME).exists()
        assert not (store.root / past_sessions.EXPORT_LEDGER_KEY_FILENAME).exists()
        assert left.is_file()  # unknown now: named by the line, never guessed at
        [line] = view.export_recovery_lines(recovery)
        assert ".wav.part" in line and sid not in line
        # A fresh ledger works afterwards.
        store.export_recording(_kept(store), tmp_path, check_destination=_anywhere)

    def test_the_lines_name_each_kept_part_by_its_session_id(self) -> None:
        from scribe_desktop.ui import past_sessions_view as view

        sid = "a" * 32
        assert view.export_recovery_lines(past_sessions.ExportRecovery(kept=(sid,))) == [
            f"A partial export file {sid}.wav.part could not be removed from the folder you "
            "chose - delete it by hand."
        ]
        assert view.export_recovery_lines(past_sessions.ExportRecovery()) == []

    def test_a_busy_ledger_has_its_own_start_up_line(self) -> None:
        from scribe_desktop.ui import past_sessions_view as view

        [line] = view.export_recovery_lines(past_sessions.ExportRecovery(busy=True))
        assert line.startswith("Clinic Scribe could not open its record of recording exports")
        assert "check again next time" in line

    def test_each_refusal_names_the_file_it_is_about(self) -> None:
        """Review round 21 LOW-005: only the chosen folder is used, so every
        line about a file names it."""
        from scribe_desktop.ui import past_sessions_view as view

        sid, earlier = "a" * 32, "b" * 32
        lines = {
            reason: view.export_recording_failed_line(PastSessionError(reason), sid)
            for reason in ("export_exists", "export_part_exists", "export_cleanup_failed")
        }
        assert f"{sid}.wav is already" in lines["export_exists"]
        assert f"{sid}.wav.part is already" in lines["export_part_exists"]
        assert f"{sid}.wav.part may remain" in lines["export_cleanup_failed"]
        unresolved = view.export_recording_failed_line(
            past_sessions.ExportUnresolvedError((earlier,)), sid
        )
        assert f"delete {earlier}.wav.part by hand first" in unresolved
        assert sid not in unresolved
        assert view.recording_exported_line(sid).startswith(f"Exported as {sid}.wav. ")
        assert "such as Documents" not in view.export_refused_line("x.")
        # Codex round 23 PR-HIGH-001: the store's own refusal reads as the
        # tab's would; a check that could not be made reads "could not check".
        from scribe_desktop.exclusions import EXPORT_ONEDRIVE, EXPORT_UNCHECKED

        refused = past_sessions.ExportDestinationRefused
        assert view.export_recording_failed_line(
            refused(EXPORT_ONEDRIVE), sid
        ) == view.export_refused_line(EXPORT_ONEDRIVE)
        assert view.export_recording_failed_line(refused(None), sid) == view.export_refused_line(
            EXPORT_UNCHECKED
        )

    def test_a_ledger_version_that_is_not_an_integer_is_unreadable(self) -> None:
        with pytest.raises(ValueError):
            past_sessions.ExportLedger.model_validate_json(b'{"schema_version": true, "rows": {}}')
        with pytest.raises(ValueError):  # a stored ledger naming no version
            past_sessions.ExportLedger.model_validate_json(b'{"rows": {}}')
        named = past_sessions.ExportLedger.model_validate_json(b'{"schema_version": 1, "rows": {}}')
        assert named.rows == {}
        with pytest.raises(ValueError):
            past_sessions.ExportLedger.model_validate_json(
                b'{"schema_version": 1, "rows": {"not-an-id": '
                b'{"folder": "C:/x", "identity": {"file_index": 1, "device": 1}}}}'
            )


class _ScriptedKernel:
    """A ``PartKernel`` reporting a given status, for ``_remove_part``'s
    own decisions (codex round 24 PR-MED-001) — every call recorded."""

    def __init__(
        self,
        status: Any,
        *,
        open_error: BaseException | None = None,
        mark_error: BaseException | None = None,
        close_error: BaseException | None = None,
    ) -> None:
        self._status = status
        self.open_error = open_error
        self.mark_error = mark_error
        self.close_error = close_error
        self.calls: list[str] = []

    def open(self, path: Path) -> int:
        self.calls.append("open")
        if self.open_error is not None:
            raise self.open_error
        return 7

    def status(self, descriptor: int) -> Any:
        self.calls.append("status")
        return self._status

    def mark_deleted(self, descriptor: int) -> None:
        self.calls.append("mark")
        if self.mark_error is not None:
            raise self.mark_error

    def close(self, descriptor: int) -> None:
        self.calls.append("close")
        if self.close_error is not None:
            raise self.close_error


class _Status:
    """The fields ``_remove_part`` reads from ``os.fstat``."""

    def __init__(self, mode: int, *, ino: int = 11, dev: int = 22, attributes: int = 0) -> None:
        self.st_mode, self.st_ino, self.st_dev = mode, ino, dev
        self.st_file_attributes = attributes


class TestRemovePart:
    """``_remove_part`` decides from ONE handle and deletes through it —
    both ways for every branch (codex round 24 PR-MED-001; C6: a scripted
    kernel, never the real Windows API)."""

    _ID = past_sessions.ExportIdentity(file_index=11, device=22)

    def test_the_apps_own_file_is_marked_through_its_handle_then_closed(self) -> None:
        kernel = _ScriptedKernel(_Status(stat.S_IFREG))
        assert past_sessions._remove_part(Path("x.wav.part"), self._ID, kernel)
        assert kernel.calls == ["open", "status", "mark", "close"]

    @pytest.mark.parametrize(
        "status",
        [
            _Status(stat.S_IFREG, ino=12),
            _Status(stat.S_IFREG, dev=23),
            _Status(stat.S_IFLNK),
            _Status(stat.S_IFDIR),
            _Status(stat.S_IFREG, attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT),
        ],
        ids=["another-file", "another-volume", "symlink", "folder", "reparse-point"],
    )
    def test_anything_but_the_apps_own_file_is_closed_unmarked(self, status: Any) -> None:
        kernel = _ScriptedKernel(status)
        assert not past_sessions._remove_part(Path("x.wav.part"), self._ID, kernel)
        assert kernel.calls == ["open", "status", "close"]

    def test_absent_is_gone_and_a_refused_open_is_kept(self) -> None:
        absent = _ScriptedKernel(_Status(stat.S_IFREG), open_error=FileNotFoundError())
        assert past_sessions._remove_part(Path("x"), self._ID, absent)
        held = _ScriptedKernel(_Status(stat.S_IFREG), open_error=PermissionError(13, "in use"))
        assert not past_sessions._remove_part(Path("x"), self._ID, held)
        assert held.calls == ["open"]

    def test_a_refused_mark_closes_and_keeps(self) -> None:
        kernel = _ScriptedKernel(_Status(stat.S_IFREG), mark_error=PermissionError(5, "denied"))
        assert not past_sessions._remove_part(Path("x"), self._ID, kernel)
        assert kernel.calls == ["open", "status", "mark", "close"]

    def test_a_close_that_fails_after_the_mark_is_not_counted_gone(self) -> None:
        kernel = _ScriptedKernel(_Status(stat.S_IFREG), close_error=OSError(5, "close"))
        assert not past_sessions._remove_part(Path("x"), self._ID, kernel)

    def test_the_real_kernel_is_never_built_in_a_test(self) -> None:
        assert not isinstance(past_sessions.part_kernel(), past_sessions.Win32PartKernel)

    def test_lifting_the_fixture_refuses_rather_than_reaching_windows(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Codex round 27 PR-LOW-001: ``undo()`` restores the conftest's
        # run-wide refusal, never the real seam.
        monkeypatch.undo()
        with pytest.raises(AssertionError, match="real Win32PartKernel"):
            past_sessions.part_kernel()
        with pytest.raises(AssertionError, match="real Win32PartKernel"):
            past_sessions._remove_part(Path("x"), self._ID)

    def test_the_real_seam_builds_the_windows_kernel(self) -> None:
        from conftest import REAL_PART_KERNEL

        # Built only — it has no constructor and no method is called, so no
        # Windows API runs (C6).
        assert isinstance(REAL_PART_KERNEL(), past_sessions.Win32PartKernel)


@windows_only
class TestRealLedgerKey:
    def test_the_ledger_key_has_its_own_description(self, tmp_path: Path) -> None:
        root = tmp_path / "past_sessions"
        root.mkdir()
        past_sessions._wrap_ledger_key(SessionCrypto(), root)
        assert (root / past_sessions.EXPORT_LEDGER_KEY_FILENAME).is_file()
        assert not (root / KEY_FILENAME).exists()
        past_sessions._unwrap_ledger_key(root).destroy()
        with pytest.raises(KeyCustodyError):
            session_store.unwrap_key_from_file(
                root,
                description=past_sessions.PAST_SESSION_KEY_DESCRIPTION,
                filename=past_sessions.EXPORT_LEDGER_KEY_FILENAME,
            )
