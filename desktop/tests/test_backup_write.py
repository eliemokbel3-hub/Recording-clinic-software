"""The Past-sessions backup's writer (past-sessions-backup plan Task 1.5; D1,
D5, D6; C4): hop B's snapshot and plan, hop C's proved copy, the one-handle
write, the read-back, the publish and the ``.part`` rules. Synthetic content
only, fake key seams (never the host's DPAPI), the test KDF floor (D15) and
the conftest's ``.part`` kernel double."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import backup_fakes as fakes
from conftest import FsPartKernel
from scribe_desktop import audit as audit_mod
from scribe_desktop import past_sessions, past_sessions_backup
from scribe_desktop import past_sessions_backup as backup
from scribe_desktop.audit import AuditLog
from scribe_desktop.past_sessions import (
    AUDIO_KEY_FILENAME,
    LABEL_FILENAME,
    PENDING_FILENAME,
    KeepLabel,
    PastSessionLabel,
    PastSessionStore,
    _label_aad,
)
from scribe_desktop.past_sessions_backup import (
    BackupPlan,
    BackupReport,
    BackupRunError,
    HandleSource,
)
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import AUDIO_FILENAME, KEY_FILENAME, TRANSCRIPT_FILENAME
from scribe_desktop.transcription import TranscriptDocument


@pytest.fixture(autouse=True)
def fast_kdf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backup, "_kdf_floor_for_tests", backup.KdfFloor())


class Run:
    """The run's key holder (D4's ``ArchiveRun`` stand-in): hop A's key and
    the KDF parameters it was derived with."""

    def __init__(self) -> None:
        self.backup_kdf: backup.KdfParams | None = backup.new_kdf_params()
        self.backup_key: bytearray | None = backup.derive_key(
            fakes.PASSPHRASE, self.backup_kdf
        )


class World:
    """An archive, an audit store and a destination folder under the test's
    own folder."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.store: PastSessionStore = fakes.archive(root)
        self.log: AuditLog = fakes.audit_log(root)
        self.dest = root / "dest"
        self.dest.mkdir()
        self.run = Run()

    def entry(self, **kwargs: Any) -> str:
        session_id = fakes.published(self.store, **kwargs)
        return session_id

    def row(self) -> str:
        return fakes.row(self.log)

    def folder(self, session_id: str) -> Path:
        return self.store.root / session_id

    def plan(self) -> BackupPlan:
        return backup.prepare_backup(self.store, self.log, self.run, made_at=fakes.NOW)

    def write(
        self, plan: BackupPlan | None = None, *, check: Callable[[Path], bool] | None = None
    ) -> BackupReport:
        plan = plan if plan is not None else self.plan()
        assert self.run.backup_key is not None
        return backup.write_backup_file(
            plan,
            self.run.backup_key,
            self.dest,
            check_location=check if check is not None else (lambda folder: True),
        )

    def opened(self, report: BackupReport) -> backup.BackupFacts:
        path = self.dest / report.file_name
        return backup.open_backup(path, fakes.PASSPHRASE).reader.facts

    def entry_key(self, session_id: str) -> bytes:
        return fakes.entry_key(self.store, session_id)


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World(tmp_path)


def _refused(code: str, action: Callable[[], object]) -> BackupRunError:
    with pytest.raises(BackupRunError) as info:
        action()
    assert info.value.code == code
    return info.value


def _tree(root: Path) -> dict[str, str]:
    """Every file under ``root`` by relative path and SHA-256."""
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _name(n: int = 1) -> str:
    day = fakes.NOW.astimezone().strftime("%Y-%m-%d")
    suffix = "" if n == 1 else f"-{n}"
    return f"{backup.BACKUP_FILENAME_PREFIX}{day}{suffix}.csbk"


def _members(world: World, report: BackupReport) -> set[str]:
    return set(world.opened(report).members)


def _reseal(world: World, session_id: str, name: str, plaintext: bytes, aad: bytes | None) -> None:
    crypto = SessionCrypto.from_key(world.entry_key(session_id))
    try:
        (world.folder(session_id) / name).write_bytes(crypto.encrypt(plaintext, aad))
    finally:
        crypto.destroy()


def _replace_same_bytes(path: Path) -> None:
    """A same-size, same-bytes replacement: a new file (a new file number)."""
    blob = path.read_bytes()
    spare = path.with_name(path.name + ".new")
    spare.write_bytes(blob)
    os.replace(spare, path)


# ---------------------------------------------------------------------------
# What is backed up (D1).
# ---------------------------------------------------------------------------


class TestInclusion:
    def test_entries_and_rows_round_trip_and_nothing_else_is_copied(self, world: World) -> None:
        saved = world.entry()
        bare = world.entry(note=False, generated=False)
        row = world.row()
        pending = fakes.source()
        world.store.write_entry(pending, fakes.LINKED)  # staged and published, never committed
        (world.store.root / ".staging").mkdir(exist_ok=True)
        (world.store.root / "exports.enc").write_bytes(b"synthetic ledger")
        report = world.write()
        assert report.file_name == _name()
        assert (report.entries, report.rows) == (2, 1)
        assert report.nothing_left_out and report.holds_recording == 0
        every_kind = ("label", "transcript", "note", "generated")
        assert _members(world, report) == {
            backup.HEADER_MEMBER,
            backup.MANIFEST_MEMBER,
            backup.AUDIT_KEY_MEMBER,
            backup.key_member(saved),
            backup.key_member(bare),
            *(backup.entry_member(saved, kind) for kind in every_kind),
            *(backup.entry_member(bare, kind) for kind in ("label", "transcript")),
            backup.row_member("2026-10", row),
        }
        facts = world.opened(report)
        assert set(facts.completed) == {saved, bare}
        assert (world.dest / report.file_name).is_file()
        assert not list(world.dest.glob("*.part"))

    def test_the_bytes_copied_are_the_archives_own(self, world: World) -> None:
        session_id = world.entry()
        report = world.write()
        path = world.dest / report.file_name
        reader = backup.open_backup(path, fakes.PASSPHRASE).reader
        assert reader.entry_files(session_id) == fakes.entry_files(world.store, session_id)
        assert report.file_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()

    def test_the_archive_and_the_audit_store_are_untouched(self, world: World) -> None:
        world.entry()
        world.row()
        before = (_tree(world.store.root), _tree(world.log.root))
        world.write()
        assert (_tree(world.store.root), _tree(world.log.root)) == before

    def test_a_shadow_entry_is_copied_as_any_entry(self, world: World) -> None:
        entry = fakes.source()
        world.store.write_entry(entry, KeepLabel("Jane Citizen", "linked", None, shadow=True))
        assert world.store.commit(entry.session_id)
        report = world.write()
        assert report.entries == 1


# ---------------------------------------------------------------------------
# Kept recordings (D12): never in a backup.
# ---------------------------------------------------------------------------


class TestRecordings:
    def test_a_live_recording_key_leaves_the_entry_out(self, world: World) -> None:
        held = world.entry()
        (world.folder(held) / AUDIO_KEY_FILENAME).write_bytes(b"\x01" * 60)
        (world.folder(held) / AUDIO_FILENAME).write_bytes(b"synthetic audio")
        world.entry()
        report = world.write()
        assert report.entries == 1 and report.holds_recording == 1
        assert report.nothing_left_out  # only the recording: the line says nothing was left out

    def test_a_live_key_beside_a_missing_transcript_is_holds_recording(self, world: World) -> None:
        held = world.entry()
        (world.folder(held) / AUDIO_KEY_FILENAME).write_bytes(b"\x01" * 60)
        (world.folder(held) / TRANSCRIPT_FILENAME).unlink()
        world.row()
        report = world.write()
        assert report.left_out.entries == {"holds_recording": 1}

    def test_a_zeroed_key_is_backed_up_without_its_audio(self, world: World) -> None:
        gone = world.entry()
        (world.folder(gone) / AUDIO_KEY_FILENAME).write_bytes(b"\0" * 60)
        (world.folder(gone) / AUDIO_FILENAME).write_bytes(b"synthetic audio")
        report = world.write()
        assert report.entries == 1
        names = _members(world, report)
        assert not any("audio" in name for name in names if name != backup.AUDIT_KEY_MEMBER)

    def test_a_recording_key_that_cannot_be_inspected(self, world: World) -> None:
        odd = world.entry()
        (world.folder(odd) / AUDIO_KEY_FILENAME).write_bytes(b"\x01" * 61)
        world.row()
        assert world.write().left_out.entries == {"uninspectable": 1}

    def test_a_recording_key_that_appears_before_the_copy(self, world: World) -> None:
        later = world.entry()
        world.row()
        plan = world.plan()
        (world.folder(later) / AUDIO_KEY_FILENAME).write_bytes(b"\x01" * 60)
        report = world.write(plan)
        assert report.left_out.entries == {"changed": 1}


# ---------------------------------------------------------------------------
# Each left-out reason (D1, D5).
# ---------------------------------------------------------------------------


class TestLeftOut:
    def _alone(self, world: World) -> BackupReport:
        world.row()  # so the run publishes even when the entry is left out
        return world.write()

    def test_a_key_that_does_not_unwrap_is_unreadable(self, world: World) -> None:
        broken = world.entry()
        (world.folder(broken) / KEY_FILENAME).write_bytes(b"not a key at all")
        assert self._alone(world).left_out.entries == {"unreadable": 1}

    def test_an_authentic_label_naming_another_id_is_unreadable(self, world: World) -> None:
        moved = world.entry()
        crypto = SessionCrypto.from_key(world.entry_key(moved))
        blob = (world.folder(moved) / LABEL_FILENAME).read_bytes()
        label = PastSessionLabel.model_validate_json(crypto.decrypt(blob, _label_aad(moved)))
        crypto.destroy()
        other = label.model_copy(update={"session_id": fakes.sid()})
        _reseal(world, moved, LABEL_FILENAME, other.to_bytes(), _label_aad(moved))
        assert self._alone(world).left_out.entries == {"unreadable": 1}

    def test_a_missing_required_file_is_incomplete(self, world: World) -> None:
        missing = world.entry()
        (world.folder(missing) / TRANSCRIPT_FILENAME).unlink()
        assert self._alone(world).left_out.entries == {"incomplete": 1}

    def test_a_file_the_label_does_not_call_for_is_incomplete(self, world: World) -> None:
        extra = world.entry(note=False)
        (world.folder(extra) / "note.enc").write_bytes(b"synthetic")
        assert self._alone(world).left_out.entries == {"incomplete": 1}

    def test_corrupted_ciphertext_is_damaged(self, world: World) -> None:
        corrupt = world.entry()
        path = world.folder(corrupt) / TRANSCRIPT_FILENAME
        blob = bytearray(path.read_bytes())
        blob[-1] ^= 0x01
        path.write_bytes(bytes(blob))
        assert self._alone(world).left_out.entries == {"damaged": 1}

    def test_a_saved_note_beside_another_revisions_transcript_is_damaged(
        self, world: World
    ) -> None:
        revised = world.entry()
        other = TranscriptDocument(
            session_id=revised,
            created_at=fakes.NOW,
            model_name="medium",
            sample_rate=16_000,
            transcript_segments=(),
        ).to_bytes()
        _reseal(world, revised, TRANSCRIPT_FILENAME, other, None)
        assert self._alone(world).left_out.entries == {"damaged": 1}

    def test_a_same_size_replacement_between_the_snapshot_and_the_copy(
        self, world: World
    ) -> None:
        swapped = world.entry()
        world.row()
        plan = world.plan()
        _replace_same_bytes(world.folder(swapped) / TRANSCRIPT_FILENAME)
        assert world.write(plan).left_out.entries == {"changed": 1}

    def test_a_hard_linked_file_is_uninspectable(self, world: World) -> None:
        linked = world.entry()
        os.link(world.folder(linked) / TRANSCRIPT_FILENAME, world.root / "second-name")
        assert self._alone(world).left_out.entries == {"uninspectable": 1}

    def test_an_unreadable_link_state_is_uninspectable(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        odd = world.entry()
        real = past_sessions.link_state
        target = world.folder(odd) / TRANSCRIPT_FILENAME

        def unreadable(path: Path) -> bool | None:
            return None if Path(path) == target else real(path)

        monkeypatch.setattr(past_sessions, "link_state", unreadable)
        assert self._alone(world).left_out.entries == {"uninspectable": 1}

    @pytest.mark.skipif(sys.platform != "win32", reason="a directory junction is Windows-only")
    def test_a_linked_entry_folder_is_uninspectable(self, world: World) -> None:
        import _winapi

        target = world.entry()
        elsewhere = world.root / "elsewhere"
        os.rename(world.folder(target), elsewhere)
        _winapi.CreateJunction(str(elsewhere), str(world.folder(target)))
        assert self._alone(world).left_out.entries == {"uninspectable": 1}

    def test_not_entries_are_skipped_silently(self, world: World) -> None:
        keyless = world.store.root / fakes.sid()
        keyless.mkdir(parents=True)
        (keyless / TRANSCRIPT_FILENAME).write_bytes(b"a leftover")
        pending = world.entry()
        (world.folder(pending) / PENDING_FILENAME).write_bytes(b"")
        world.entry()
        report = self._alone(world)
        assert report.entries == 1 and report.nothing_left_out


# ---------------------------------------------------------------------------
# Refusals before any file exists.
# ---------------------------------------------------------------------------


class TestRefusals:
    def test_an_unlistable_archive_refuses(self, world: World) -> None:
        world.store.root.parent.mkdir(parents=True, exist_ok=True)
        world.store.root.write_bytes(b"a file where the archive should be")
        world.row()
        _refused("archive_unreadable", world.plan)

    def test_an_unavailable_audit_record_refuses_with_nothing_written(
        self, world: World
    ) -> None:
        world.entry()
        world.row()
        (world.log.root / KEY_FILENAME).unlink()  # rows with no key
        _refused("audit_unavailable", world.plan)
        assert list(world.dest.iterdir()) == []

    def test_nothing_to_back_up(self, world: World) -> None:
        _refused("nothing_to_back_up", world.plan)

    def test_too_large_before_any_file_exists(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world.entry()
        monkeypatch.setattr(backup, "MAX_BACKUP_BYTES", 1024)
        _refused("too_large", world.plan)
        assert list(world.dest.iterdir()) == []

    def test_an_entry_file_over_its_bound_is_too_large_before_anything_is_read(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 25 PR-LOW-2501: D2's per-file bound is the planner's, before
        any file exists and before the copy or the open check. At the bound
        the backup is written and opens."""
        session_id = world.entry()
        largest = max(
            identity.size
            for kind, identity in world.plan().entries[0].files.items()
            if kind != "label"
        )
        monkeypatch.setattr(backup, "MAX_ENTRY_FILE_BYTES", largest - 1)

        def never(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError("the open check ran")

        with monkeypatch.context() as patch:
            patch.setattr(past_sessions_backup, "entry_opens", never)
            _refused("too_large", world.plan)
        assert list(world.dest.iterdir()) == []
        monkeypatch.setattr(backup, "MAX_ENTRY_FILE_BYTES", largest)
        report = world.write()
        assert report.entries == 1
        assert set(world.opened(report).manifest.entries) == {session_id}

    def test_the_header_carries_the_kdf_the_key_was_derived_with(self, world: World) -> None:
        """The passphrase derives ``K_b`` again from the file's own header."""
        world.entry()
        plan = world.plan()
        assert plan.header.kdf == world.run.backup_kdf
        assert world.run.backup_key is not None
        again = backup.derive_key(fakes.PASSPHRASE, plan.header.kdf)
        assert again == world.run.backup_key

    @pytest.mark.parametrize("missing", ["backup_key", "backup_kdf"])
    def test_a_run_without_its_key_or_kdf_is_refused(self, world: World, missing: str) -> None:
        world.entry()
        setattr(world.run, missing, None)
        _refused("unexpected", world.plan)

    def test_the_planned_keys_are_wrapped_and_the_plain_bytes_zeroed(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world.entry()
        world.row()
        seen: list[bytearray] = []
        real_snapshot = world.store.backup_snapshot

        def recording() -> past_sessions.ArchiveSnapshot:
            snapshot = real_snapshot()
            seen.extend(entry.key for entry in snapshot.entries)
            return snapshot

        monkeypatch.setattr(world.store, "backup_snapshot", recording)
        plan = world.plan()
        assert seen and all(not any(key) for key in seen)
        assert all(len(entry.wrapped_key) == backup.WRAPPED_KEY_BYTES for entry in plan.entries)

    def test_a_snapshot_that_fails_after_an_entry_zeroes_that_entrys_key(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 23 PR-MED-2301: a key leaves only inside a returned
        snapshot; a failure on the next entry zeroes the ones already taken."""
        world.entry()
        world.entry()
        taken: list[bytearray] = []
        real_entry = world.store._snapshot_entry

        def second_fails(child: Path) -> Any:
            if taken:
                raise MemoryError
            answer = real_entry(child)
            assert isinstance(answer, past_sessions.SnapshotEntry)
            taken.append(answer.key)
            return answer

        monkeypatch.setattr(world.store, "_snapshot_entry", second_fails)
        with pytest.raises(MemoryError):
            world.store.backup_snapshot()
        assert len(taken) == 1 and len(taken[0]) > 0
        assert taken[0] == bytearray(len(taken[0]))

    def test_an_entry_that_fails_as_it_is_returned_zeroes_its_own_key(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world.entry()
        keys: list[bytearray] = []

        def fails(session_id: str, key: bytearray, *args: Any) -> Any:
            keys.append(key)
            raise MemoryError

        monkeypatch.setattr(past_sessions, "SnapshotEntry", fails)
        with pytest.raises(MemoryError):
            world.store.backup_snapshot()
        assert len(keys) == 1 and len(keys[0]) > 0
        assert keys[0] == bytearray(len(keys[0]))

    def test_no_audit_key_beside_a_month_that_cannot_be_inspected_refuses(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 23 PR-MED-2303, through the planner: an audit store whose
        month cannot be inspected is not EMPTY, even with no key."""
        world.entry()
        world.row()
        (world.log.root / KEY_FILENAME).unlink()
        real = audit_mod.link_state

        def month_unknown(path: Path) -> bool | None:
            return None if audit_mod.valid_month(path.name) is not None else real(path)

        monkeypatch.setattr(audit_mod, "link_state", month_unknown)
        _refused("audit_unavailable", world.plan)
        assert list(world.dest.iterdir()) == []
        assert not (world.log.root / KEY_FILENAME).exists()

    def test_nothing_could_be_read_publishes_nothing(self, world: World) -> None:
        corrupt = world.entry()
        path = world.folder(corrupt) / TRANSCRIPT_FILENAME
        blob = bytearray(path.read_bytes())
        blob[-1] ^= 0x01
        path.write_bytes(bytes(blob))
        error = _refused("nothing_could_be_read", world.write)
        assert error.left_out is not None and error.left_out.entries == {"damaged": 1}
        assert not error.part_may_remain
        assert list(world.dest.iterdir()) == []

    def test_the_destination_rechecked_before_the_create(self, world: World) -> None:
        world.entry()
        error = _refused("destination_refused", lambda: world.write(check=lambda f: False))
        assert not error.part_may_remain
        assert list(world.dest.iterdir()) == []

        def raising(folder: Path) -> bool:
            raise OSError("cannot check")

        _refused("destination_refused", lambda: world.write(check=raising))
        assert list(world.dest.iterdir()) == []


# ---------------------------------------------------------------------------
# The audit record (D1, D9).
# ---------------------------------------------------------------------------


def _seal_row(log: AuditLog, session_id: str, plaintext: bytes, month: str) -> Path:
    crypto = fakes.fake_audit_unwrap(log.root)
    try:
        path = log.root / month / f"{session_id}.enc"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(crypto.encrypt(plaintext, b"audit:" + session_id.encode()))
        return path
    finally:
        crypto.destroy()


def _row_path(log: AuditLog, session_id: str) -> Path:
    return log.root / "2026-10" / f"{session_id}.enc"


def _flip_last_byte(path: Path) -> None:
    blob = bytearray(path.read_bytes())
    blob[-1] ^= 0x01
    path.write_bytes(bytes(blob))


class TestRows:
    def test_rows_that_cannot_be_copied_are_left_out_and_listed_unknown(
        self, world: World
    ) -> None:
        world.entry()
        good = world.row()
        doubled = world.row()
        twin = _row_path(world.log, doubled)
        (world.log.root / "2026-09").mkdir()
        (world.log.root / "2026-09" / twin.name).write_bytes(twin.read_bytes())
        bad_month = world.row()
        (world.log.root / "2026-13").mkdir()
        thirteenth = world.log.root / "2026-13" / f"{bad_month}.enc"
        os.replace(_row_path(world.log, bad_month), thirteenth)
        forged = world.row()
        _flip_last_byte(_row_path(world.log, forged))
        undecodable = fakes.sid()
        _seal_row(world.log, undecodable, b"not a row", "2026-10")
        elsewhere = world.row()
        plaintext_holder = _row_path(world.log, elsewhere)
        os.replace(plaintext_holder, world.log.root / "2026-09" / plaintext_holder.name)
        report = world.write()
        facts = world.opened(report)
        assert set(facts.manifest.rows) == {good}
        assert set(facts.manifest.rows_unknown) == {
            doubled, bad_month, forged, undecodable, elsewhere
        }
        assert report.left_out.rows == 5 and not report.nothing_left_out

    def test_an_audit_only_archive_of_unreadable_rows_is_nothing_could_be_read(
        self, world: World
    ) -> None:
        forged = world.row()
        _flip_last_byte(_row_path(world.log, forged))
        error = _refused("nothing_could_be_read", world.write)
        assert error.left_out is not None and error.left_out.rows == 1
        assert list(world.dest.iterdir()) == []

    def test_a_newer_row_is_copied_byte_for_byte(self, world: World) -> None:
        world.row()  # the store and its key
        newer = fakes.sid()
        path = _seal_row(world.log, newer, b'{"schema_version": 99, "x": 1}', "2026-10")
        report = world.write()
        reader = backup.open_backup(world.dest / report.file_name, fakes.PASSPHRASE).reader
        assert reader.read_member(backup.row_member("2026-10", newer)) == path.read_bytes()
        assert newer in reader.facts.importable_rows

    def test_not_restorable_counts_written_entries_whose_row_cannot_be_read(
        self, world: World
    ) -> None:
        session_id = world.entry()
        world.row()  # the audit store and its key
        _seal_row(world.log, session_id, b"not a row", "2026-10")
        report = world.write()
        assert report.entries == 1 and report.not_restorable == 1
        assert not report.nothing_left_out

    def test_a_row_nested_past_the_stack_is_left_out_and_the_rest_copied(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 24 PR-LOW-2401: the parser's ``RecursionError`` (injected)
        is that row's own outcome, never the run's."""
        too_deep = b'{"stands_for": "a row nested past the parser\'s stack"}'
        session_id = world.entry()
        other = world.row()
        _seal_row(world.log, session_id, too_deep, "2026-10")
        real = json.loads
        seen: list[bytes] = []

        def loads(text: Any, *args: Any, **kwargs: Any) -> Any:
            if text == too_deep:
                seen.append(text)
                raise RecursionError
            return real(text, *args, **kwargs)

        monkeypatch.setattr(audit_mod.json, "loads", loads)
        report = world.write()
        assert seen
        assert report.entries == 1 and report.rows == 1 and report.not_restorable == 1
        manifest = world.opened(report).manifest
        assert session_id in manifest.rows_unknown
        assert set(manifest.rows) == {other}

    def test_a_row_that_failed_during_the_copy_makes_its_entry_not_restorable(
        self, world: World
    ) -> None:
        session_id = world.entry()
        fakes.row(world.log, session_id=session_id)  # reads at the snapshot
        world.row()
        plan = world.plan()
        assert not any(entry.row_not_restorable for entry in plan.entries)
        own = _row_path(world.log, session_id)
        blob = bytearray(own.read_bytes())
        blob[-1] ^= 0x01
        own.write_bytes(bytes(blob))
        report = world.write(plan)
        assert session_id in world.opened(report).manifest.rows_unknown
        assert report.not_restorable == 1


# ---------------------------------------------------------------------------
# The file: the name, the one handle, the publish (D6).
# ---------------------------------------------------------------------------


class TestTheFile:
    def test_an_existing_part_and_backup_survive_and_the_run_takes_the_next_suffix(
        self, world: World
    ) -> None:
        world.entry()
        stranger = world.dest / (_name(1) + ".part")
        stranger.write_bytes(b"maybe a whole backup")
        report = world.write()
        assert report.file_name == _name(2)
        older = world.dest / _name(2)
        assert stranger.read_bytes() == b"maybe a whole backup"
        report_3 = world.write()
        assert report_3.file_name == _name(3)
        assert hashlib.sha256(older.read_bytes()).hexdigest() == report.file_sha256

    def test_the_file_is_verified_through_the_writing_handle(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world.entry()
        sources: list[object] = []
        real = backup.verify_backup

        def spy(source: Any, key: Any, **kwargs: Any) -> backup.BackupFacts:
            sources.append(source)
            return real(source, key, **kwargs)

        monkeypatch.setattr(past_sessions_backup, "verify_backup", spy)
        world.write()
        assert len(sources) == 1 and isinstance(sources[0], HandleSource)

    def test_a_final_file_that_differs_after_the_rename_is_unverified(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world.entry()
        real_rename = os.rename

        def rename_then_change(source: Any, target: Any) -> None:
            real_rename(source, target)
            with open(target, "ab") as stream:
                stream.write(b"!")

        with monkeypatch.context() as patch:
            patch.setattr(backup.os, "rename", rename_then_change)
            error = _refused("publish_unverified", world.write)
        assert (world.dest / _name()).is_file()  # left alone
        assert not error.part_may_remain

    def test_a_failure_removes_this_runs_part(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world.entry()

        def failing(*args: Any, **kwargs: Any) -> backup.BackupFacts:
            raise backup.BackupFormatError("member_hash")

        monkeypatch.setattr(past_sessions_backup, "verify_backup", failing)
        error = _refused("write_failed", world.write)
        assert not error.part_may_remain
        assert list(world.dest.iterdir()) == []

    def test_a_part_whose_identity_cannot_be_read_is_left_and_said_to_remain(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 23 PR-LOW-2304: ``fstat`` fails just after the exclusive
        create. The descriptor is closed and the file left (it cannot be
        removed by identity), with the closed code and the partial-file flag."""
        world.entry()
        plan = world.plan()
        stranger = world.dest / "unrelated.txt"
        stranger.write_bytes(b"left alone")
        opened: list[int] = []
        real_open = os.open

        def recording_open(*args: Any, **kwargs: Any) -> int:
            descriptor = real_open(*args, **kwargs)
            opened.append(descriptor)
            return descriptor

        def no_identity(descriptor: int) -> Any:
            raise OSError("no identity")

        with monkeypatch.context() as patch:
            patch.setattr(backup.os, "open", recording_open)
            patch.setattr(backup.os, "fstat", no_identity)
            error = _refused("write_failed", lambda: world.write(plan))
        assert error.part_may_remain
        assert sorted(path.name for path in world.dest.iterdir()) == sorted(
            [_name() + ".part", "unrelated.txt"]
        )
        assert stranger.read_bytes() == b"left alone"
        assert len(opened) == 1
        with pytest.raises(OSError):
            os.fstat(opened[0])  # closed

    def test_a_failed_handover_to_the_stream_closes_and_removes_the_part(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world.entry()
        plan = world.plan()
        opened: list[int] = []
        real_open = os.open

        def recording_open(*args: Any, **kwargs: Any) -> int:
            descriptor = real_open(*args, **kwargs)
            opened.append(descriptor)
            return descriptor

        def no_stream(*args: Any, **kwargs: Any) -> Any:
            raise OSError("no stream")

        with monkeypatch.context() as patch:
            patch.setattr(backup.os, "open", recording_open)
            patch.setattr(backup.os, "fdopen", no_stream)
            error = _refused("write_failed", lambda: world.write(plan))
        assert not error.part_may_remain
        assert list(world.dest.iterdir()) == []
        assert len(opened) == 1
        with pytest.raises(OSError):
            os.fstat(opened[0])  # closed

    def test_a_failure_while_the_rows_are_copied_zeroes_the_audit_key(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """C3: the copy suspended between two rows still holds the plain
        audit key; the run closes it on the failure, which zeroes it."""
        world.entry()
        world.row()
        world.row()
        keys: list[bytearray] = []
        real_unwrap = backup.unwrap_key

        def recording(k_b: Any, blob: bytes, aad: bytes) -> bytearray:
            key = real_unwrap(k_b, blob, aad)
            if aad == backup._AUDIT_KEY_AAD:
                keys.append(key)
            return key

        def fails_after_a_row(stream: Any, header: bytes, payload: Any, *args: Any) -> None:
            for name, _blob in payload:
                if name.startswith("audit/"):
                    raise OSError("the drive went away")

        plan = world.plan()
        monkeypatch.setattr(past_sessions_backup, "unwrap_key", recording)
        monkeypatch.setattr(past_sessions_backup, "write_container", fails_after_a_row)
        error = _refused("write_failed", lambda: world.write(plan))
        assert not error.part_may_remain
        assert len(keys) == 1 and keys[0] == bytearray(len(keys[0]))

    def test_a_part_whose_identity_cannot_be_confirmed_is_left(
        self, world: World, monkeypatch: pytest.MonkeyPatch, part_kernel: FsPartKernel
    ) -> None:
        world.entry()
        part_kernel.refuse_open = True

        def failing(*args: Any, **kwargs: Any) -> backup.BackupFacts:
            raise OSError("the drive went away")

        monkeypatch.setattr(past_sessions_backup, "verify_backup", failing)
        error = _refused("write_failed", world.write)
        assert error.part_may_remain
        assert [path.name for path in world.dest.iterdir()] == [_name() + ".part"]

    def test_a_folder_that_cannot_be_listed_after_the_removal_may_remain(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world.entry()

        def failing(*args: Any, **kwargs: Any) -> backup.BackupFacts:
            raise OSError("the drive went away")

        monkeypatch.setattr(past_sessions_backup, "verify_backup", failing)
        monkeypatch.setattr(past_sessions_backup, "_listable", lambda folder: False)
        assert _refused("write_failed", world.write).part_may_remain

    def test_no_store_or_audit_method_runs_in_hop_c(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world.entry()
        world.row()
        plan = world.plan()

        def forbidden(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError("a store or audit method ran in hop C")

        with monkeypatch.context() as patch:
            for owner in (PastSessionStore, AuditLog):
                for name in dir(owner):
                    if not name.startswith("__") and callable(getattr(owner, name)):
                        patch.setattr(owner, name, forbidden)
            report = world.write(plan)
        assert (report.entries, report.rows) == (1, 1)
