"""Past-sessions-backup plan Tasks 3.1 and 3.2 (D8, D9, D12; C5, C6, C14):
Restore's planner (``plan_restore`` / ``classify_entry``, the outcome table)
and the restorer (``restore_backup``, ``PastSessionStore.restore_entry``).

A SOURCE archive and audit store make a backup (``backup_fakes.build``); a
DESTINATION archive and audit store, under the test's own folder with the
same fake key seams, receive it. The test KDF floor; never the host's DPAPI,
data folder or drives (C9). Synthetic content only."""

from __future__ import annotations

import json
import os
import shutil
import sys
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, get_args

import pytest

import backup_fakes as fakes
from scribe_desktop import app as app_module
from scribe_desktop import past_sessions
from scribe_desktop import past_sessions_backup as backup
from scribe_desktop.audit import AuditLog, AuditRow, AuditUnavailable
from scribe_desktop.past_sessions import (
    AUDIO_KEY_FILENAME,
    MIN_RETENTION_DAYS,
    PENDING_FILENAME,
    KeepLabel,
    PastSessionStore,
    RestoreEntryOutcome,
)
from scribe_desktop.past_sessions_backup import (
    REPORT_COUNTS,
    SUMMARY_COUNTS,
    BackupFormatError,
    BackupRunError,
    EntryOutcome,
    OpenedBackup,
    ReportCount,
    RowPlan,
    SummaryCount,
    WriteOutcome,
)
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import (
    AUDIO_FILENAME,
    KEY_FILENAME,
    TRANSCRIPT_FILENAME,
    StoreWriteError,
)

NOW = fakes.NOW
MONTH = "2026-10"


@pytest.fixture(autouse=True)
def fast_kdf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backup, "_kdf_floor_for_tests", backup.KdfFloor())


class Scene:
    """A source archive and audit store, and a destination pair."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.src = fakes.archive(root / "src")
        self.src_log = fakes.audit_log(root / "src")
        self.dst = fakes.archive(root / "dst")
        self.dst_log = fakes.audit_log(root / "dst")
        self.sessions = root / "dst" / "sessions"
        self._made = 0

    def entry(
        self, *, row: bool = True, note: bool = True, generated: bool = True, shadow: bool = False
    ) -> str:
        if shadow:
            source = fakes.source(note=note, generated=generated)
            self.src.write_entry(source, KeepLabel(None, "linked", None, shadow=True))
            assert self.src.commit(source.session_id)
            session_id = source.session_id
        else:
            session_id = fakes.published(self.src, note=note, generated=generated)
        if row:
            fakes.row(self.src_log, session_id=session_id)
        return session_id

    def backup(self, **kwargs: Any) -> OpenedBackup:
        self._made += 1
        folder = self.root / f"b{self._made}"
        built = fakes.build(folder, store=self.src, log=self.src_log, **kwargs)
        path = built.write(folder / "backup.csbk")
        return backup.open_backup(path, fakes.PASSPHRASE)

    def plan(
        self, opened: OpenedBackup, *, retention_days: int | None = None, now: datetime = NOW
    ) -> backup.RestorePlan:
        return backup.plan_restore(
            opened.reader,
            self.dst,
            self.dst_log,
            self.sessions,
            k_b=opened.key,
            retention_days=retention_days,
            now=now,
        )

    def restore(
        self, opened: OpenedBackup, plan: backup.RestorePlan, *, now: datetime = NOW
    ) -> backup.RestoreReport:
        return backup.restore_backup(
            opened.reader, plan, self.dst, self.dst_log, k_b=opened.key, now=now
        )

    def copy_here(self, session_id: str) -> Path:
        """The source entry's folder copied byte for byte into the destination."""
        target = self.dst.root / session_id
        self.dst.root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.src.root / session_id, target)
        return target


@pytest.fixture
def scene(tmp_path: Path) -> Iterator[Scene]:
    yield Scene(tmp_path)


def _tree(folder: Path) -> dict[str, bytes]:
    """Every file under ``folder`` by relative path, with its bytes."""
    if not folder.exists():
        return {}
    return {
        str(path.relative_to(folder)): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def _audit_key(log: AuditLog) -> bytes:
    return (log.root / KEY_FILENAME).read_bytes()[len(fakes.AUDIT_FAKE) :]


def _put_row(log: AuditLog, row: AuditRow, month: str = MONTH) -> Path:
    """Write ``row`` into ``log`` under its key (the store made first)."""
    if not (log.root / KEY_FILENAME).exists():
        fakes.row(log)
    folder = log.root / month
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{row.session_id}.enc"
    crypto = SessionCrypto.from_key(_audit_key(log))
    path.write_bytes(crypto.encrypt(row.to_bytes(), b"audit:" + row.session_id.encode()))
    return path


def _put_plain_row(log: AuditLog, session_id: str, plain: bytes, month: str = MONTH) -> None:
    if not (log.root / KEY_FILENAME).exists():
        fakes.row(log)
    folder = log.root / month
    folder.mkdir(parents=True, exist_ok=True)
    crypto = SessionCrypto.from_key(_audit_key(log))
    (folder / f"{session_id}.enc").write_bytes(
        crypto.encrypt(plain, b"audit:" + session_id.encode())
    )


def _bare_pre_audit(session_id: str) -> AuditRow:
    return AuditRow(session_id=session_id, session_date=date(2026, 10, 1), origin="pre_audit")


# ---------------------------------------------------------------------------
# The outcome table (D8).
# ---------------------------------------------------------------------------


class TestTheOutcomeTable:
    def test_every_planner_outcome_has_exactly_one_summary_count(self) -> None:
        planner = {*get_args(EntryOutcome), *get_args(RowPlan)}
        assert set(SUMMARY_COUNTS) == planner
        assert set(SUMMARY_COUNTS.values()) <= set(get_args(SummaryCount))
        assert set(SUMMARY_COUNTS.values()) == set(get_args(SummaryCount))

    def test_every_write_outcome_has_exactly_one_report_count(self) -> None:
        assert set(REPORT_COUNTS) == set(get_args(WriteOutcome))
        assert set(REPORT_COUNTS.values()) == set(get_args(ReportCount))
        assert set(get_args(RestoreEntryOutcome)) <= set(get_args(WriteOutcome))

    def test_the_counts_cover_every_outcome_with_zeroes(self, scene: Scene) -> None:
        scene.entry()
        plan = scene.plan(scene.backup())
        counts = plan.counts()
        assert set(counts) == set(get_args(SummaryCount))
        assert counts["to_add"] == 1 and counts["rows_to_add"] == 1
        assert sum(counts.values()) == 2


# ---------------------------------------------------------------------------
# The planner's classifications, in their order (Task 3.1).
# ---------------------------------------------------------------------------


class TestThePlanner:
    def test_an_absent_entry_is_add_and_its_row_add_row(self, scene: Scene) -> None:
        session_id = scene.entry()
        plan = scene.plan(scene.backup())
        assert plan.entries == {session_id: "add"}
        assert plan.rows == {session_id: "add_row"}

    def test_a_live_session_folder_is_skipped_live(self, scene: Scene) -> None:
        session_id = scene.entry()
        (scene.sessions / session_id).mkdir(parents=True)
        assert scene.plan(scene.backup()).entries[session_id] == "skipped_live"

    def test_live_comes_before_anything_at_the_entry_path(self, scene: Scene) -> None:
        session_id = scene.entry()
        scene.copy_here(session_id)
        (scene.sessions / session_id).mkdir(parents=True)
        assert scene.plan(scene.backup()).entries[session_id] == "skipped_live"

    def test_an_unreadable_link_state_is_uninspectable(
        self, scene: Scene, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        session_id = scene.entry()
        opened = scene.backup()
        target = scene.dst.root / session_id
        real = backup.link_state

        def unreadable(path: Path) -> bool | None:
            return None if Path(path) == target else real(path)

        monkeypatch.setattr(backup, "link_state", unreadable)
        assert scene.plan(opened).entries[session_id] == "skipped_uninspectable"

    def test_an_existence_that_cannot_be_told_is_uninspectable(
        self, scene: Scene, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        session_id = scene.entry()
        opened = scene.backup()
        target = scene.dst.root / session_id
        real = os.lstat

        def refused(path: Any, *args: Any, **kwargs: Any) -> Any:
            if Path(path) == target:
                raise PermissionError("refused")
            return real(path, *args, **kwargs)

        monkeypatch.setattr(backup, "link_state", lambda _path: False)
        monkeypatch.setattr(backup.os, "lstat", refused)
        assert scene.plan(opened).entries[session_id] == "skipped_uninspectable"

    @pytest.mark.skipif(sys.platform != "win32", reason="a directory junction is Windows-only")
    def test_a_junction_where_the_entry_would_be_is_skipped_linked(self, scene: Scene) -> None:
        import _winapi

        session_id = scene.entry()
        opened = scene.backup()
        elsewhere = scene.root / "elsewhere"
        shutil.copytree(scene.src.root / session_id, elsewhere)
        before = _tree(elsewhere)
        scene.dst.root.mkdir(parents=True)
        _winapi.CreateJunction(str(elsewhere), str(scene.dst.root / session_id))
        plan = scene.plan(opened)
        assert plan.entries[session_id] == "skipped_linked"
        scene.restore(opened, plan)
        assert _tree(elsewhere) == before

    def test_a_listed_entry_that_opens_is_present_whatever_the_rows_say(
        self, scene: Scene
    ) -> None:
        session_id = scene.entry()
        scene.src_log.record_past_session(session_id, "deleted_early")
        scene.copy_here(session_id)
        assert scene.plan(scene.backup()).entries[session_id] == "skipped_present"

    @pytest.mark.parametrize("how", ["key", "label"])
    def test_a_listed_entry_that_does_not_open_is_not_readable_and_untouched(
        self, scene: Scene, how: str
    ) -> None:
        session_id = scene.entry()
        folder = scene.copy_here(session_id)
        if how == "key":
            (folder / KEY_FILENAME).write_bytes(b"a key this login refuses")
        else:
            label = folder / "label.enc"
            blob = bytearray(label.read_bytes())
            blob[-1] ^= 0x01
            label.write_bytes(bytes(blob))
        before = _tree(folder)
        opened = scene.backup()
        plan = scene.plan(opened)
        assert plan.entries[session_id] == "skipped_not_readable"
        report = scene.restore(opened, plan)
        assert _tree(folder) == before
        assert not (scene.dst.staging_root / session_id).exists()
        assert report.restored == 0

    @pytest.mark.parametrize("kind", ["pending", "keyless"])
    def test_an_unlisted_folder_is_a_leftover_and_untouched(self, scene: Scene, kind: str) -> None:
        session_id = scene.entry()
        folder = scene.copy_here(session_id)
        if kind == "pending":
            (folder / PENDING_FILENAME).write_bytes(b"")
        else:
            (folder / KEY_FILENAME).unlink()
        before = _tree(folder)
        opened = scene.backup()
        plan = scene.plan(opened)
        assert plan.entries[session_id] == "skipped_leftover"
        scene.restore(opened, plan)
        assert _tree(folder) == before
        assert not (scene.dst.staging_root / session_id).exists()

    def test_the_local_row_unreadable_is_unknown(self, scene: Scene) -> None:
        session_id = scene.entry(row=False)
        fakes.row(scene.dst_log, session_id=session_id)
        path = scene.dst_log.root / MONTH / f"{session_id}.enc"
        path.write_bytes(b"does not authenticate")
        before = path.read_bytes()
        opened = scene.backup()
        plan = scene.plan(opened)
        assert plan.entries[session_id] == "skipped_unknown_row"
        scene.restore(opened, plan)
        assert path.read_bytes() == before

    def test_a_local_row_of_a_newer_schema_is_unknown(self, scene: Scene) -> None:
        session_id = scene.entry(row=False)
        _put_plain_row(scene.dst_log, session_id, json.dumps({"schema_version": 99}).encode())
        assert scene.plan(scene.backup()).entries[session_id] == "skipped_unknown_row"

    def test_an_id_the_backup_lists_unknown_is_unknown_on_an_empty_destination(
        self, scene: Scene
    ) -> None:
        session_id = scene.entry(row=False)

        def unknown(doc: dict[str, Any]) -> None:
            doc["rows_unknown"] = [session_id]

        opened = scene.backup(manifest=unknown)
        assert scene.plan(opened).entries[session_id] == "skipped_unknown_row"

    @pytest.mark.parametrize(
        "plain", [json.dumps({"schema_version": 99}).encode(), b'{"schema_version": 3}']
    )
    def test_the_backups_row_newer_or_undecodable_is_unknown(
        self, scene: Scene, plain: bytes
    ) -> None:
        session_id = scene.entry(row=False)
        _put_plain_row(scene.src_log, session_id, plain)
        plan = scene.plan(scene.backup())
        assert plan.entries[session_id] == "skipped_unknown_row"
        expected = "add_row" if b"99" in plain else "skipped_undecodable_row"
        assert plan.rows[session_id] == expected

    def test_a_deletion_in_the_backups_row_is_deleted(self, scene: Scene) -> None:
        session_id = scene.entry()
        scene.src_log.record_past_session(session_id, "deleted_early")
        assert scene.plan(scene.backup()).entries[session_id] == "skipped_deleted"

    def test_a_deletion_in_the_local_row_is_deleted(self, scene: Scene) -> None:
        session_id = scene.entry()
        fakes.row(scene.dst_log, session_id=session_id)
        scene.dst_log.record_past_session(session_id, "expired")
        assert scene.plan(scene.backup()).entries[session_id] == "skipped_deleted"

    def test_an_old_entry_restores_until_deleted_and_expires_under_seven_years(
        self, scene: Scene
    ) -> None:
        session_id = scene.entry()
        opened = scene.backup()
        # Past the 7-year minimum AND past the audit month's prune.
        later = NOW + timedelta(days=MIN_RETENTION_DAYS + 400)
        assert scene.plan(opened, retention_days=None, now=later).entries[session_id] == "add"
        seven = scene.plan(opened, retention_days=MIN_RETENTION_DAYS, now=later)
        assert seven.entries[session_id] == "skipped_expired"
        assert seven.rows[session_id] == "skipped_pruned_row"

    def test_a_young_entry_restores_under_seven_years(self, scene: Scene) -> None:
        session_id = scene.entry()
        plan = scene.plan(scene.backup(), retention_days=MIN_RETENTION_DAYS)
        assert plan.entries[session_id] == "add"

    def test_an_unlistable_archive_refuses_the_plan(
        self, scene: Scene, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        scene.entry()
        opened = scene.backup()

        def unlistable() -> list[Any]:
            raise past_sessions.PastSessionError("unreadable")

        monkeypatch.setattr(scene.dst, "list_entries", unlistable)
        with pytest.raises(BackupRunError) as raised:
            scene.plan(opened)
        assert raised.value.code == "archive_unreadable"

    def test_the_archive_is_listed_once_however_many_entries(
        self, scene: Scene, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for _ in range(3):
            scene.entry()
        opened = scene.backup()
        calls: list[int] = []
        real = scene.dst.list_entries

        def counted() -> Any:
            calls.append(1)
            return real()

        monkeypatch.setattr(scene.dst, "list_entries", counted)
        plan = scene.plan(opened)
        report = scene.restore(opened, plan)
        assert report.restored == 3
        assert len(calls) == 1

    def test_the_plan_writes_nothing(self, scene: Scene) -> None:
        scene.entry()
        opened = scene.backup()
        scene.plan(opened)
        assert not scene.dst.root.exists()
        assert not scene.dst_log.root.exists()

    def test_with_the_local_audit_key_unreadable_the_plan_still_computes(
        self, scene: Scene
    ) -> None:
        session_id = scene.entry()
        fakes.row(scene.dst_log, session_id=session_id)
        (scene.dst_log.root / KEY_FILENAME).write_bytes(b"not this store's key")
        before = _tree(scene.dst_log.root)
        plan = scene.plan(scene.backup())
        assert plan.entries[session_id] == "skipped_unknown_row"
        assert plan.rows[session_id] == "skipped_unreadable_row"
        assert _tree(scene.dst_log.root) == before


class TestTheRowPlan:
    def test_a_present_readable_row_is_kept(self, scene: Scene) -> None:
        session_id = scene.entry()
        fakes.row(scene.dst_log, session_id=session_id)
        assert scene.plan(scene.backup()).rows[session_id] == "skipped_present_row"

    def test_a_bare_same_month_pre_audit_row_is_provenance(self, scene: Scene) -> None:
        session_id = scene.entry()
        _put_row(scene.dst_log, _bare_pre_audit(session_id))
        assert scene.plan(scene.backup()).rows[session_id] == "provenance_recovered"

    def test_a_pre_audit_row_holding_facts_is_a_conflict(self, scene: Scene) -> None:
        session_id = scene.entry()
        _put_row(scene.dst_log, _bare_pre_audit(session_id).with_event("started", NOW))
        assert scene.plan(scene.backup()).rows[session_id] == "conflict_row"

    def test_a_pre_audit_row_in_another_month_is_a_conflict(self, scene: Scene) -> None:
        session_id = scene.entry()
        _put_row(scene.dst_log, _bare_pre_audit(session_id), month="2026-09")
        assert scene.plan(scene.backup()).rows[session_id] == "conflict_row"

    def test_a_key_that_cannot_be_opened_just_now_plans_no_row(
        self, scene: Scene, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review round 32 LOW-004: what ``restore_row`` would do — it fails."""
        session_id = scene.entry()
        fakes.row(scene.dst_log)

        def unavailable(*, create: bool = True) -> SessionCrypto:
            raise AuditUnavailable("unavailable")

        monkeypatch.setattr(scene.dst_log, "_open_key", unavailable)
        assert scene.plan(scene.backup()).rows[session_id] == "skipped_unreadable_row"

    def test_a_key_lost_after_the_plan_counts_the_row_as_not_restored(
        self, scene: Scene, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review round 33: the recheck meets a key that cannot be opened —
        not restored, never "left as it is" (which says a row is here)."""
        session_id = scene.entry()
        fakes.row(scene.dst_log)
        opened = scene.backup()
        plan = scene.plan(opened)
        assert plan.rows[session_id] == "add_row"

        def unavailable(*, create: bool = True) -> SessionCrypto:
            raise AuditUnavailable("unavailable")

        monkeypatch.setattr(scene.dst_log, "_open_key", unavailable)
        report = scene.restore(opened, plan)
        assert (report.rows_restored, report.left, report.not_restored) == (0, 0, 1)
        assert scene.dst_log.row_state(session_id) == "none"

    @pytest.mark.skipif(sys.platform != "win32", reason="a directory junction is Windows-only")
    def test_a_linked_month_folder_is_not_a_row_to_add(self, scene: Scene) -> None:
        import _winapi

        session_id = scene.entry()
        # The store and its key, from a row in ANOTHER month.
        fakes.row(scene.dst_log, started_at=NOW - timedelta(days=60))
        elsewhere = scene.root / "month-elsewhere"
        elsewhere.mkdir()
        _winapi.CreateJunction(str(elsewhere), str(scene.dst_log.root / MONTH))
        opened = scene.backup()
        plan = scene.plan(opened)
        assert plan.rows[session_id] == "skipped_unreadable_row"
        scene.restore(opened, plan)
        assert list(elsewhere.iterdir()) == []


# ---------------------------------------------------------------------------
# The restorer (Task 3.2).
# ---------------------------------------------------------------------------


class TestAnAdd:
    def test_an_entry_is_published_without_pending_and_verified_by_the_readers(
        self, scene: Scene
    ) -> None:
        session_id = scene.entry()
        opened = scene.backup()
        report = scene.restore(opened, scene.plan(opened))
        assert (report.restored, report.rows_restored) == (1, 1)
        folder = scene.dst.root / session_id
        assert not (folder / PENDING_FILENAME).exists()
        assert [item.session_id for item in scene.dst.list_entries()] == [session_id]
        entry = scene.dst.read_entry(session_id)
        assert entry.saved_note is not None and entry.generated is not None
        for kind, blob in fakes.entry_files(scene.src, session_id).items():
            assert (folder / f"{kind}.enc").read_bytes() == blob
        assert not (scene.dst.staging_root / session_id).exists()

    def test_only_the_files_its_label_names_and_never_a_recording(self, scene: Scene) -> None:
        session_id = scene.entry(note=False, generated=False)
        opened = scene.backup()
        scene.restore(opened, scene.plan(opened))
        folder = scene.dst.root / session_id
        assert sorted(path.name for path in folder.iterdir()) == sorted(
            [KEY_FILENAME, "label.enc", TRANSCRIPT_FILENAME]
        )
        assert scene.dst.recording_state(session_id) == "none"
        before = _tree(folder)
        scene.dst.tidy_dead_recordings()
        assert _tree(folder) == before

    def test_the_key_is_wrapped_again_for_this_login(self, scene: Scene) -> None:
        wrapped: list[Path] = []

        def wrap(crypto: SessionCrypto, directory: Path) -> None:
            wrapped.append(directory)
            fakes.fake_entry_wrap(crypto, directory)

        scene.dst = fakes.archive(scene.root / "dst", wrap_key=wrap)
        session_id = scene.entry()
        opened = scene.backup()
        scene.restore(opened, scene.plan(opened))
        assert [path.name for path in wrapped] == [session_id]
        assert fakes.entry_key(scene.dst, session_id) == fakes.entry_key(scene.src, session_id)

    def test_rows_are_re_encrypted_under_the_local_key_into_the_month(
        self, scene: Scene
    ) -> None:
        session_id = scene.entry()
        fakes.row(scene.dst_log)  # a local store with its OWN key
        opened = scene.backup()
        scene.restore(opened, scene.plan(opened))
        restored = scene.dst_log.root / MONTH / f"{session_id}.enc"
        source = scene.src_log.root / MONTH / f"{session_id}.enc"
        assert restored.read_bytes() != source.read_bytes()
        row = scene.dst_log.row_for(session_id)
        source_row = scene.src_log.row_for(session_id)
        assert row is not None and source_row is not None
        # The only difference: the restored entry's ``archived`` mark (D8) —
        # its state and the event the mark appends.
        assert (row.past_session.state, source_row.past_session.state) == ("archived", "none")
        assert row.events[:-1] == source_row.events
        assert row.events[-1].code == "past_session_archived"
        unmarked = row.model_copy(
            update={"past_session": source_row.past_session, "events": source_row.events}
        )
        assert unmarked == source_row

    def test_a_newer_row_is_kept_byte_for_byte_in_plaintext(self, scene: Scene) -> None:
        session_id = fakes.sid()
        plain = json.dumps({"schema_version": 99, "anything": 1}).encode()
        _put_plain_row(scene.src_log, session_id, plain)
        opened = scene.backup(entries=0)
        report = scene.restore(opened, scene.plan(opened))
        assert report.rows_restored >= 1
        crypto = SessionCrypto.from_key(_audit_key(scene.dst_log))
        blob = (scene.dst_log.root / MONTH / f"{session_id}.enc").read_bytes()
        assert crypto.decrypt(blob, b"audit:" + session_id.encode()) == plain
        assert scene.dst_log.row_state(session_id) == "newer"

    def test_an_undecodable_row_is_skipped_and_everything_else_restored(
        self, scene: Scene
    ) -> None:
        session_id = scene.entry()  # first, so the odd row makes no extra row
        odd = fakes.sid()
        _put_plain_row(scene.src_log, odd, b'{"schema_version": 3}')
        opened = scene.backup()
        plan = scene.plan(opened)
        assert plan.rows[odd] == "skipped_undecodable_row"
        report = scene.restore(opened, plan)
        assert (report.restored, report.rows_restored) == (1, 1)
        assert scene.dst_log.row_state(odd) == "none"
        assert scene.dst_log.row_state(session_id) == "readable"

    def test_a_bare_pre_audit_row_is_replaced_and_a_retry_leaves_one_row(
        self, scene: Scene
    ) -> None:
        session_id = scene.entry()
        _put_row(scene.dst_log, _bare_pre_audit(session_id))
        opened = scene.backup()
        report = scene.restore(opened, scene.plan(opened))
        assert report.rows_restored == 1
        row = scene.dst_log.row_for(session_id)
        assert row is not None and row.origin == "recorded"
        again = scene.restore(opened, scene.plan(opened))
        assert again.rows_restored == 0
        assert len(list(scene.dst_log.root.rglob(f"{session_id}.enc"))) == 1

    def test_a_shadow_entry_stays_a_shadow_entry(self, scene: Scene) -> None:
        session_id = scene.entry(shadow=True)
        opened = scene.backup()
        scene.restore(opened, scene.plan(opened))
        assert scene.dst.read_entry(session_id).label.shadow is True

    def test_a_v1_label_still_reads_as_normal(self, scene: Scene) -> None:
        session_id = scene.entry()
        folder = scene.src.root / session_id
        label = {
            "schema_version": 1,
            "session_id": session_id,
            "completed_at": NOW.isoformat(),
            "started_at": None,
            "recording": "linked",
            "clinic_id": None,
            "patient_name": None,
            "has_generated": True,
            "has_saved": True,
        }
        crypto = SessionCrypto.from_key(fakes.entry_key(scene.src, session_id))
        (folder / "label.enc").write_bytes(
            crypto.encrypt(json.dumps(label).encode(), b"past-label:" + session_id.encode())
        )
        opened = scene.backup()
        scene.restore(opened, scene.plan(opened))
        restored = scene.dst.read_entry(session_id).label
        assert restored.schema_version == 1 and restored.shadow is False


class TestTheStagingRule:
    @pytest.mark.skipif(sys.platform != "win32", reason="a directory junction is Windows-only")
    def test_a_linked_staging_refuses_the_whole_restore(self, scene: Scene) -> None:
        import _winapi

        session_id = scene.entry()
        opened = scene.backup()
        plan = scene.plan(opened)
        target = scene.root / "staging-elsewhere"
        target.mkdir()
        (target / KEY_FILENAME).write_bytes(b"another folder's key")
        scene.dst.root.mkdir(parents=True)
        _winapi.CreateJunction(str(target), str(scene.dst.staging_root))
        with pytest.raises(BackupRunError) as raised:
            scene.restore(opened, plan)
        assert raised.value.code == "staging_unusable"
        assert (target / KEY_FILENAME).read_bytes() == b"another folder's key"
        assert not (scene.dst.root / session_id).exists()
        assert not scene.dst_log.root.exists()  # nothing written, rows included

    @pytest.mark.skipif(sys.platform != "win32", reason="a directory junction is Windows-only")
    def test_a_linked_staging_child_skips_that_entry_only(self, scene: Scene) -> None:
        import _winapi

        linked = scene.entry()
        other = scene.entry()
        opened = scene.backup()
        plan = scene.plan(opened)
        target = scene.root / "child-elsewhere"
        target.mkdir()
        (target / KEY_FILENAME).write_bytes(b"another folder's key")
        scene.dst.staging_root.mkdir(parents=True)
        _winapi.CreateJunction(str(target), str(scene.dst.staging_root / linked))
        report = scene.restore(opened, plan)
        assert (target / KEY_FILENAME).read_bytes() == b"another folder's key"
        assert not (scene.dst.root / linked).exists()
        assert (scene.dst.root / other).is_dir()
        assert (report.restored, report.left) == (1, 1)

    def test_a_staging_copy_left_over_is_removed_key_first(self, scene: Scene) -> None:
        session_id = scene.entry()
        opened = scene.backup()
        plan = scene.plan(opened)
        stale = scene.dst.staging_root / session_id
        stale.mkdir(parents=True)
        (stale / KEY_FILENAME).write_bytes(b"stale")
        (stale / "junk.enc").write_bytes(b"junk")
        assert scene.restore(opened, plan).restored == 1
        assert not stale.exists()


class TestFailures:
    def test_a_destination_that_appears_after_staging_is_kept(
        self, scene: Scene, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        session_id = scene.entry()
        opened = scene.backup()
        plan = scene.plan(opened)
        intruder = scene.dst.root / session_id
        real = scene.dst._verify_restored

        def then_appears(staging: Path, sid: str, files: dict[str, bytes]) -> None:
            real(staging, sid, files)
            intruder.mkdir(parents=True)
            (intruder / KEY_FILENAME).write_bytes(b"its own key")

        monkeypatch.setattr(scene.dst, "_verify_restored", then_appears)
        report = scene.restore(opened, plan)
        assert _tree(intruder) == {KEY_FILENAME: b"its own key"}
        assert not (scene.dst.staging_root / session_id).exists()
        assert (report.restored, report.left) == (0, 1)

    @pytest.mark.skipif(sys.platform != "win32", reason="a rename onto a folder refuses on Windows")
    def test_a_destination_appearing_at_the_rename_is_kept(
        self, scene: Scene, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review round 32 LOW-001: past the absence check, the rename meets
        it (``FileExistsError``) — a collision, left as it is."""
        session_id = scene.entry()
        opened = scene.backup()
        plan = scene.plan(opened)
        intruder = scene.dst.root / session_id
        real_rename = os.rename

        def appears_first(source: Any, target: Any) -> None:
            if Path(target) == intruder:
                intruder.mkdir()
                (intruder / KEY_FILENAME).write_bytes(b"its own key")
            real_rename(source, target)

        monkeypatch.setattr(past_sessions.os, "rename", appears_first)
        report = scene.restore(opened, plan)
        assert _tree(intruder) == {KEY_FILENAME: b"its own key"}
        assert not (scene.dst.staging_root / session_id).exists()
        assert (report.restored, report.left, report.not_restored) == (0, 1, 0)

    def test_a_key_read_back_that_differs_fails_verification(self, scene: Scene) -> None:
        scene.dst = fakes.archive(scene.root / "dst", unwrap_key=lambda _d: SessionCrypto())
        session_id = scene.entry()
        opened = scene.backup()
        report = scene.restore(opened, scene.plan(opened))
        assert (report.restored, report.not_restored) == (0, 1)
        assert not (scene.dst.root / session_id).exists()
        assert not (scene.dst.staging_root / session_id).exists()

    def test_a_staged_write_that_differs_fails_verification(
        self, scene: Scene, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        session_id = scene.entry()
        opened = scene.backup()
        plan = scene.plan(opened)
        real = past_sessions.atomic_write_bytes

        def altered(path: Path, blob: bytes, **kwargs: Any) -> None:
            if path.name == TRANSCRIPT_FILENAME:
                blob = blob[:-1] + bytes([blob[-1] ^ 0x01])
            real(path, blob, **kwargs)

        monkeypatch.setattr(past_sessions, "atomic_write_bytes", altered)
        report = scene.restore(opened, plan)
        assert report.not_restored == 1
        assert not (scene.dst.root / session_id).exists()
        assert not (scene.dst.staging_root / session_id).exists()

    def test_a_write_that_fails_is_counted_and_the_next_tried(
        self, scene: Scene, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        first = scene.entry(row=False)
        second = scene.entry(row=False)
        opened = scene.backup()
        plan = scene.plan(opened)
        order = list(plan.entries)
        failing = order[0]
        real = past_sessions.atomic_write_bytes

        def full_disk(path: Path, blob: bytes, **kwargs: Any) -> None:
            if path.parent.name == failing:
                raise StoreWriteError("disk full")
            real(path, blob, **kwargs)

        monkeypatch.setattr(past_sessions, "atomic_write_bytes", full_disk)
        report = scene.restore(opened, plan)
        assert (report.restored, report.not_restored) == (1, 1)
        kept = order[1]
        assert (scene.dst.root / kept).is_dir()
        assert not (scene.dst.root / failing).exists()
        assert {first, second} == set(order)

    def test_a_row_write_that_fails_is_counted_and_the_rest_tried(
        self, scene: Scene, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for _ in range(2):
            scene.entry()
        opened = scene.backup()
        plan = scene.plan(opened)
        first_row = next(iter(plan.rows))
        real = scene.dst_log.restore_row

        def refused(plain: bytes, sid: str, month: str, *, now: datetime) -> Any:
            if sid == first_row:
                return "failed_row_write"
            return real(plain, sid, month, now=now)

        monkeypatch.setattr(scene.dst_log, "restore_row", refused)
        report = scene.restore(opened, plan)
        assert (report.rows_restored, report.restored, report.not_restored) == (1, 2, 1)

    def test_a_row_mismatch_from_restore_row_is_not_restored(
        self, scene: Scene, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        scene.entry()
        opened = scene.backup()
        plan = scene.plan(opened)
        monkeypatch.setattr(scene.dst_log, "restore_row", lambda *a, **k: "row_mismatch")
        report = scene.restore(opened, plan)
        assert (report.rows_restored, report.not_restored, report.restored) == (0, 1, 1)


class TestTheRecheck:
    def test_an_id_the_plan_skipped_is_never_written(self, scene: Scene) -> None:
        session_id = scene.entry()
        live = scene.sessions / session_id
        live.mkdir(parents=True)
        opened = scene.backup()
        plan = scene.plan(opened)
        assert plan.entries[session_id] == "skipped_live"
        live.rmdir()  # the recheck would now say add
        report = scene.restore(opened, plan)
        assert report.restored == 0
        assert not (scene.dst.root / session_id).exists()

    def test_a_planned_add_that_is_now_live_is_withdrawn(self, scene: Scene) -> None:
        session_id = scene.entry(row=False)
        opened = scene.backup()
        plan = scene.plan(opened)
        (scene.sessions / session_id).mkdir(parents=True)
        report = scene.restore(opened, plan)
        assert (report.restored, report.left) == (0, 1)
        assert not (scene.dst.root / session_id).exists()

    def test_a_planned_row_that_changed_is_withdrawn(self, scene: Scene) -> None:
        session_id = scene.entry(row=True)
        opened = scene.backup()
        plan = scene.plan(opened)
        assert plan.rows[session_id] == "add_row"
        _put_row(scene.dst_log, _bare_pre_audit(session_id))
        report = scene.restore(opened, plan)
        assert report.rows_restored == 0 and report.left >= 1
        row = scene.dst_log.row_for(session_id)
        assert row is not None and row.origin == "pre_audit"

    def test_a_second_restore_of_a_finished_backup_reports_all_zero(
        self, scene: Scene
    ) -> None:
        for _ in range(2):
            scene.entry()
        opened = scene.backup()
        scene.restore(opened, scene.plan(opened))
        rows_before = _tree(scene.dst_log.root)
        again = scene.restore(opened, scene.plan(opened))
        assert again == backup.RestoreReport()
        assert _tree(scene.dst_log.root) == rows_before


class TestTheArchivedMark:
    def test_a_kept_local_row_reading_none_is_archived_after_the_publish(
        self, scene: Scene
    ) -> None:
        session_id = scene.entry()
        fakes.row(scene.dst_log, session_id=session_id)
        opened = scene.backup()
        report = scene.restore(opened, scene.plan(opened))
        assert report.restored == 1 and report.unmarked == 0
        row = scene.dst_log.row_for(session_id)
        assert row is not None and row.past_session.state == "archived"

    def test_no_mark_when_the_publish_failed(
        self, scene: Scene, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        session_id = scene.entry()
        fakes.row(scene.dst_log, session_id=session_id)
        opened = scene.backup()
        plan = scene.plan(opened)
        monkeypatch.setattr(scene.dst, "restore_entry", lambda *a, **k: "failed_write")
        scene.restore(opened, plan)
        row = scene.dst_log.row_for(session_id)
        assert row is not None and row.past_session.state == "none"

    def test_an_interruption_is_completed_by_a_retry(self, scene: Scene) -> None:
        session_id = scene.entry()
        fakes.row(scene.dst_log, session_id=session_id)
        scene.copy_here(session_id)  # published, then interrupted before the mark
        opened = scene.backup()
        plan = scene.plan(opened)
        assert plan.entries[session_id] == "skipped_present"
        report = scene.restore(opened, plan)
        assert report == backup.RestoreReport()  # a skipped item is not counted
        row = scene.dst_log.row_for(session_id)
        assert row is not None and row.past_session.state == "archived"

    def test_restore_never_makes_a_row_for_an_entry(self, scene: Scene) -> None:
        session_id = scene.entry(row=False)
        opened = scene.backup()
        scene.restore(opened, scene.plan(opened))
        assert scene.dst_log.row_state(session_id) == "none"

    def test_a_failed_mark_is_counted_apart(
        self, scene: Scene, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        session_id = scene.entry()
        fakes.row(scene.dst_log, session_id=session_id)
        present = scene.entry()
        fakes.row(scene.dst_log, session_id=present)
        scene.copy_here(present)
        opened = scene.backup()
        plan = scene.plan(opened)
        monkeypatch.setattr(scene.dst_log, "record_past_session", lambda *a, **k: False)
        report = scene.restore(opened, plan)
        assert report.restored == 1
        assert report.unmarked == 2


class TestTheFileChanging:
    def test_a_file_changed_after_open_is_refused_before_any_write(self, scene: Scene) -> None:
        scene.entry()
        opened = scene.backup()
        path = scene.root / "b1" / "backup.csbk"
        blob = bytearray(path.read_bytes())
        blob[200] ^= 0x01
        path.write_bytes(bytes(blob))
        with pytest.raises(BackupRunError) as raised:
            backup.reverify_backup(path, opened.key, opened.reader.facts.file_sha256)
        assert raised.value.code == "source_changed"

    def test_the_same_file_reverifies(self, scene: Scene) -> None:
        scene.entry()
        opened = scene.backup()
        path = scene.root / "b1" / "backup.csbk"
        facts = backup.reverify_backup(path, opened.key, opened.reader.facts.file_sha256)
        assert facts.file_sha256 == opened.reader.facts.file_sha256

    def test_a_member_changed_mid_restore_stops_the_run_with_exact_totals(
        self, scene: Scene, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for _ in range(3):
            scene.entry(row=False)
        opened = scene.backup()
        plan = scene.plan(opened)
        order = list(plan.entries)
        real = opened.reader.read_member

        def changed(name: str) -> bytes:
            if name.startswith(f"entries/{order[1]}/"):
                raise BackupRunError("source_changed")
            return real(name)

        monkeypatch.setattr(opened.reader, "read_member", changed)
        report = scene.restore(opened, plan)
        assert report.source_changed
        assert (report.restored, report.not_restored, report.left) == (1, 2, 0)
        assert (scene.dst.root / order[0]).is_dir()
        assert not (scene.dst.root / order[1]).exists()
        assert not (scene.dst.root / order[2]).exists()


class TestOpenRefusals:
    def test_another_channels_file_is_refused(self, scene: Scene) -> None:
        scene.entry()
        built = fakes.build(scene.root / "b", store=scene.src, log=scene.src_log)
        path = built.write(scene.root / "b" / "backup.csbk")
        other = "production" if built.header.channel == "dev" else "dev"
        with pytest.raises(BackupFormatError) as raised:
            backup.open_backup(path, fakes.PASSPHRASE, channel=other)
        assert raised.value.code == "other_channel"

    def test_a_newer_format_is_refused(self, scene: Scene) -> None:
        scene.entry()

        def newer(doc: dict[str, Any]) -> None:
            doc["format_version"] = 2

        built = fakes.build(scene.root / "b", store=scene.src, log=scene.src_log, header=newer)
        path = built.write(scene.root / "b" / "backup.csbk")
        with pytest.raises(BackupFormatError) as raised:
            backup.open_backup(path, fakes.PASSPHRASE)
        assert raised.value.code == "format_newer"

    def test_an_id_paired_with_another_entrys_key_is_refused_at_open(
        self, scene: Scene
    ) -> None:
        first = scene.entry()
        second = scene.entry()

        def swap(payload: list[tuple[str, bytes]]) -> None:
            keys = {name: blob for name, blob in payload if name.startswith("keys/")}
            a, b = backup.key_member(first), backup.key_member(second)
            for index, (name, _blob) in enumerate(payload):
                if name == a:
                    payload[index] = (name, keys[b])
                elif name == b:
                    payload[index] = (name, keys[a])

        def rehash(doc: dict[str, Any]) -> None:
            entries = doc["entries"]
            entries[first]["key"], entries[second]["key"] = (
                entries[second]["key"],
                entries[first]["key"],
            )

        built = fakes.build(
            scene.root / "b", store=scene.src, log=scene.src_log, members=swap, manifest=rehash
        )
        path = built.write(scene.root / "b" / "backup.csbk")
        with pytest.raises(BackupFormatError):
            backup.open_backup(path, fakes.PASSPHRASE)
        assert not scene.dst.staging_root.exists()


class TestNoStoreOrAuditOnAWorker:
    def test_the_open_and_reverify_workers_call_no_store_or_audit_method(
        self, scene: Scene, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        scene.entry()
        built = fakes.build(scene.root / "b", store=scene.src, log=scene.src_log)
        path = built.write(scene.root / "b" / "backup.csbk")

        def forbidden(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError("a store or audit method ran on a worker")

        with monkeypatch.context() as patch:
            for owner in (PastSessionStore, AuditLog):
                for name in dir(owner):
                    if not name.startswith("__") and callable(getattr(owner, name)):
                        patch.setattr(owner, name, forbidden)
            opened = backup.open_backup(path, fakes.PASSPHRASE)
            backup.reverify_backup(path, opened.key, opened.reader.facts.file_sha256)


class TestTheNamedResidue:
    """D12 (peer round 17): after a new audit record, the start-up repair of a
    deleted recording whose label cannot be read finds no row, records
    nothing and clears the files; the row a Restore brings back afterwards
    shows the recording kept with no deletion date."""

    def test_a_restored_row_can_show_a_recording_kept_and_never_deleted(
        self, scene: Scene
    ) -> None:
        session_id = scene.entry()
        scene.src_log.record_recording_kept(session_id, NOW)
        opened = scene.backup()
        # Here: the session, its key refused, with a deleted recording's files.
        folder = scene.copy_here(session_id)
        (folder / KEY_FILENAME).write_bytes(b"a key this login refuses")
        (folder / AUDIO_KEY_FILENAME).write_bytes(bytes(60))
        (folder / AUDIO_FILENAME).write_bytes(b"dead audio")
        cleared = app_module.record_deleted_recordings(scene.dst, scene.dst_log)
        assert session_id in cleared
        assert scene.dst_log.row_state(session_id) == "none"  # nothing recorded
        scene.dst.tidy_dead_recordings(cleared=cleared)
        assert not (folder / AUDIO_FILENAME).exists()
        plan = scene.plan(opened)
        assert plan.entries[session_id] == "skipped_not_readable"
        scene.restore(opened, plan)
        row = scene.dst_log.row_for(session_id)
        assert row is not None
        assert row.recording.kept_at is not None and row.recording.deleted_at is None
