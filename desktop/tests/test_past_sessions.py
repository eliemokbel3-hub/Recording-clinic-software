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
    GENERATED_FILENAME,
    KEY_FILENAME,
    NOTE_FILENAME,
    TRANSCRIPT_FILENAME,
    ArchiveSource,
    ArchiveWriteError,
    GeneratedRecord,
    KeyCustodyError,
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
