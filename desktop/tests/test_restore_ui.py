"""Past-sessions-backup plan Tasks 3.3 and 3.4 (Flows 2 and 3; D7, D8, D10,
D11; C1, C3): Open a backup... and Restore on the Past sessions page, and
the set-aside button.

A SOURCE archive and audit store make a backup (``backup_fakes.build``) on
a fake removable drive under the test's own folder; the page runs over a
DESTINATION pair with the same fake key seams. The test KDF floor, a fake
``WindowsLayer``, a fake run gate, and every dialog and the worker injected
(no real dialog, thread or clipboard). Synthetic content only."""

from __future__ import annotations

import logging
import os
import shutil
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import backup_fakes as fakes  # noqa: E402
from scribe_desktop import install_layout  # noqa: E402
from scribe_desktop import past_sessions_backup as backup  # noqa: E402
from scribe_desktop.exclusions import BACKUP_SOURCE_REFUSED, DRIVE_REMOVABLE  # noqa: E402
from scribe_desktop.note_config import NoteConfigWriteError, read_backup_settings  # noqa: E402
from scribe_desktop.past_sessions import (  # noqa: E402
    MIN_RETENTION_DAYS,
    KeepLabel,
    PastSessionError,
    PastSessionSettings,
    RetentionSweepReport,
    SetAsideReport,
    save_past_session_settings,
)
from scribe_desktop.session_store import KEY_FILENAME  # noqa: E402
from scribe_desktop.ui import past_sessions as page_module  # noqa: E402
from scribe_desktop.ui import past_sessions_view as view  # noqa: E402
from test_archive_backup_location import VOL_E, Layer  # noqa: E402
from test_backup_ui import FakeGate, Hops, Passphrases, dispose  # noqa: E402

# A plain file's attributes as the fake layer reports them (not a folder,
# not a link).
_PLAIN_FILE = 0x80


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def fast_kdf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backup, "_kdf_floor_for_tests", backup.KdfFloor())


def _answers(blob: bytes) -> str:
    """The set-aside's fake key classifier: the fake entry key opens; a blob
    that starts ``dpapi_refused:`` is one this login can no longer open."""
    if blob.startswith(fakes.ENTRY_FAKE):
        return "ok"
    if blob.startswith(b"dpapi_refused:"):
        return "dpapi_refused"
    return "unexpected"


class RWorld:
    """A source pair that makes backups, the page's destination pair, a fake
    removable drive the backup file sits on, and the page's seams."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.src = fakes.archive(root / "src")
        self.src_log = fakes.audit_log(root / "src")
        self.probe: Callable[[], bool] = lambda: True
        self.dst = fakes.archive(
            root / "dst", classify_key_blob=_answers, dpapi_probe=lambda: self.probe()
        )
        self.dst_log = fakes.audit_log(root / "dst")
        self.sessions = root / "sessions"
        self.config = root / "config"
        self.drive = root / "drive"
        self.drive.mkdir()
        self.layer = Layer(volumes={str(self.drive).casefold(): (VOL_E, DRIVE_REMOVABLE)})
        self.gate = FakeGate()
        self.hops = Hops()
        self.passphrases = Passphrases(fakes.PASSPHRASE.decode("utf-8"))
        self.chosen: Path | None = None
        self.starts: list[Path | None] = []
        self.summaries: list[tuple[list[str], bool]] = []
        self.answer = True
        self.on_summary: Callable[[], None] | None = None
        self.confirmed: list[tuple[str, str]] = []
        self.confirm_answer = True
        self.screen: Any = None
        self._made = 0

    # --- the source ---------------------------------------------------------

    def entry(self, *, shadow: bool = False, row: bool = True) -> str:
        if shadow:
            source = fakes.source()
            self.src.write_entry(source, KeepLabel(None, "linked", None, shadow=True))
            assert self.src.commit(source.session_id)
            session_id = source.session_id
        else:
            session_id = fakes.published(self.src)
        if row:
            fakes.row(self.src_log, session_id=session_id)
        return session_id

    def backup_file(self, **kwargs: Any) -> Path:
        """The source pair as a backup on the drive, chosen in the open dialog."""
        self._made += 1
        folder = self.root / f"b{self._made}"
        built = fakes.build(folder, store=self.src, log=self.src_log, **kwargs)
        path = built.write(self.drive / f"backup-{self._made}.csbk")
        self.layer.attributes[str(path).casefold()] = _PLAIN_FILE
        self.chosen = path
        return path

    # --- the seams ----------------------------------------------------------

    def choose_file(self, start: Path | None) -> Path | None:
        self.starts.append(start)
        return self.chosen

    def summary(self, lines: Sequence[str], restore_enabled: bool) -> bool:
        self.summaries.append((list(lines), restore_enabled))
        if self.on_summary is not None:
            self.on_summary()
        return self.answer

    def confirm(self, text: str, action: str) -> bool:
        self.confirmed.append((text, action))
        return self.confirm_answer

    def build(
        self,
        *,
        store: Any = "dst",
        audit: Any = "log",
        layer: Any = "layer",
        real_runner: bool = False,
        logger: logging.Logger | None = None,
    ) -> Any:
        from scribe_desktop.ui.past_sessions import PastSessionsScreen

        screen = PastSessionsScreen(
            self.dst if store == "dst" else store,
            audit=self.dst_log if audit == "log" else audit,
            config_root=self.config,
            clock=lambda: fakes.NOW,
            monotonic=lambda: 100.0,
            local_zone=UTC,
            confirm=self.confirm,
            choose_csv_path=lambda: pytest.fail("a CSV save dialog"),
            choose_wav_path=lambda _sid: pytest.fail("a WAV save dialog"),
            windows_layer=self.layer if layer == "layer" else layer,
            ask_passphrase=self.passphrases,
            choose_backup_path=lambda _start, _name: pytest.fail("a backup save dialog"),
            run_hop=None if real_runner else self.hops,
            logger=logger,
            choose_backup_file=self.choose_file,
            show_backup_summary=self.summary,
            sessions_root=self.sessions,
        )
        screen.set_archive_gate(self.gate)
        screen.refresh()
        self.screen = screen
        return screen

    # --- what the destination holds -----------------------------------------

    def here(self) -> dict[str, bytes]:
        """Every file of the destination pair (and the sessions folder) by
        relative path, with its bytes."""
        found: dict[str, bytes] = {}
        for top in (self.root / "dst", self.sessions):
            if top.exists():
                for path in sorted(top.rglob("*")):
                    if path.is_file():
                        found[str(path.relative_to(self.root))] = path.read_bytes()
        return found

    def listed(self) -> list[str]:
        return sorted(listing.session_id for listing in self.dst.list_entries())

    def message(self) -> str:
        return str(self.screen.message_label.text())


@pytest.fixture
def world(qapp: Any, tmp_path: Path) -> Iterator[RWorld]:
    root = tmp_path / "w"
    root.mkdir()
    made = RWorld(root)
    yield made
    if made.screen is not None:
        dispose(made.screen)
        made.screen = None


def _closed_cleanly(world: RWorld) -> None:
    """Every exit of a run: the passphrase zeroed, the gate (if taken)
    released, the run's key and reader dropped, and both buttons back."""
    for given in world.passphrases.given:
        assert given == bytearray(len(given))
    assert world.gate.held is None
    assert world.gate.released == world.gate.begun
    for run in world.gate.begun:
        assert run.closed and run.backup_key is None and run.passphrase is None
        assert run.reader is None
    screen = world.screen
    assert screen._run is None
    assert screen.backup_button.isEnabled() and screen.open_backup_button.isEnabled()


def _other_channel() -> str:
    return "production" if install_layout.channel() == "dev" else "dev"


# ---------------------------------------------------------------------------
# The buttons.
# ---------------------------------------------------------------------------


class TestTheButtons:
    def test_both_are_enabled_on_a_fresh_store_and_set_aside_is_hidden(
        self, world: RWorld
    ) -> None:
        screen = world.build()
        assert screen.open_backup_button.text() == view.OPEN_BACKUP_LABEL
        assert screen.backup_button.isEnabled() and screen.open_backup_button.isEnabled()
        assert screen.set_aside_button.isHidden()

    def test_without_an_archive_open_is_disabled_and_refused(self, world: RWorld) -> None:
        screen = world.build(store=None)
        assert not screen.open_backup_button.isEnabled()
        screen.on_open_backup()
        assert world.message() == view.OPEN_NOT_AVAILABLE
        assert world.starts == [] and world.passphrases.asked == []

    def test_both_are_disabled_while_a_run_holds_the_page(self, world: RWorld) -> None:
        world.entry()
        world.backup_file()
        world.hops = Hops(deferred=True)
        screen = world.build()
        screen.on_open_backup()
        assert world.message() == view.OPEN_RUNNING
        assert not screen.open_backup_button.isEnabled()
        assert not screen.backup_button.isEnabled()
        screen.on_open_backup()  # the page's own run refuses a second
        assert world.message() == view.OPEN_NOT_AVAILABLE
        world.answer = False
        world.hops.run_all()
        assert len(world.gate.begun) == 1
        _closed_cleanly(world)


# ---------------------------------------------------------------------------
# Open a backup... and the summary (Flow 2).
# ---------------------------------------------------------------------------


class TestOpenAndClose:
    def test_close_writes_nothing(self, world: RWorld) -> None:
        world.entry()
        world.backup_file()
        world.answer = False
        screen = world.build()
        before = world.here()
        screen.on_open_backup()
        assert world.passphrases.asked == [False]  # once
        assert len(world.summaries) == 1 and world.summaries[0][1] is True
        assert world.here() == before
        assert world.listed() == []
        assert world.message() == view.OPEN_CLOSED
        assert read_backup_settings(world.config).settings.last_backup_at is None
        _closed_cleanly(world)

    def test_the_summary_counts_what_restore_would_add(self, world: RWorld) -> None:
        world.entry()
        world.backup_file()
        world.answer = False
        world.build().on_open_backup()
        lines, enabled = world.summaries[0]
        assert enabled
        assert lines[0].startswith(f"This backup opens: {view._sessions(1)} from ")
        assert f"{view._rows(1)}, made on " in lines[0]
        assert any(
            line.startswith(f"To add: {view._sessions(1)}, {view._rows(1)}.") for line in lines
        )
        assert view.RESTORE_NEVER_REPLACES not in lines

    def test_an_audit_only_backup(self, world: RWorld) -> None:
        fakes.row(world.src_log)
        world.backup_file()
        world.build().on_open_backup()
        lines, enabled = world.summaries[0]
        assert enabled
        assert lines[0].startswith(f"This backup opens: no sessions and {view._rows(1)}")
        to_add = f"To add: {view._sessions(0)}, {view._rows(1)}."
        assert any(line.startswith(to_add) for line in lines)
        assert world.listed() == []
        assert world.message().startswith(f"Restored {view._sessions(0)} and {view._rows(1)}.")
        _closed_cleanly(world)

    def test_a_session_here_that_cannot_be_read_names_the_set_aside(
        self, world: RWorld
    ) -> None:
        sid = world.entry()
        world.backup_file()
        world.dst.root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(world.src.root / sid, world.dst.root / sid)
        (world.dst.root / sid / KEY_FILENAME).write_bytes(b"dpapi_refused:" + b"x" * 40)
        world.answer = False
        world.build().on_open_backup()
        lines, _enabled = world.summaries[0]
        assert view.RESTORE_NEVER_REPLACES in lines

    def test_restore_is_disabled_while_the_audit_key_cannot_be_read(
        self, world: RWorld
    ) -> None:
        world.entry()
        world.backup_file()
        fakes.row(world.dst_log)
        (world.dst_log.root / KEY_FILENAME).unlink()  # rows present, key missing
        screen = world.build()
        before = world.here()
        screen.on_open_backup()  # the answer would be Restore: it is disabled
        lines, enabled = world.summaries[0]
        assert not enabled and lines[-1] == view.RESTORE_NEEDS_AUDIT
        assert world.here() == before
        assert world.message() == view.OPEN_CLOSED
        _closed_cleanly(world)

    def test_restore_is_disabled_while_the_retention_setting_cannot_be_read(
        self, world: RWorld
    ) -> None:
        world.entry()
        world.backup_file()
        world.config.mkdir(parents=True, exist_ok=True)
        (world.config / "past_sessions.json").write_bytes(b"not a settings file")
        screen = world.build()
        before = world.here()
        screen.on_open_backup()
        lines, enabled = world.summaries[0]
        assert not enabled and lines[-1] == view.RESTORE_NEEDS_RETENTION
        # The ages cannot be judged: the sessions to add are not counted.
        assert any(line.startswith(f"To add: {view._rows(1)}.") for line in lines)
        assert world.here() == before
        _closed_cleanly(world)

    def test_every_reason_restore_is_disabled_is_its_own_line(self, world: RWorld) -> None:
        """Review round 32 LOW-007."""
        world.entry()
        world.backup_file()
        fakes.row(world.dst_log)
        (world.dst_log.root / KEY_FILENAME).unlink()
        world.config.mkdir(parents=True, exist_ok=True)
        (world.config / "past_sessions.json").write_bytes(b"not a settings file")
        world.build().on_open_backup()
        lines, enabled = world.summaries[0]
        assert not enabled
        assert lines[-2:] == [view.RESTORE_NEEDS_AUDIT, view.RESTORE_NEEDS_RETENTION]
        _closed_cleanly(world)

    def test_an_audit_check_that_raises_disables_restore(
        self, world: RWorld, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review round 32 LOW-009: Restore fails closed. The stand-in raises
        from the check Restore itself calls (``key_unopenable``, since round
        33 — stage-4 leg x3: patching ``key_unreadable`` no longer reached
        it)."""
        world.entry()
        world.backup_file()
        screen = world.build()
        asked: list[str] = []

        def broken() -> bool:
            asked.append("asked")
            raise RuntimeError("synthetic")

        monkeypatch.setattr(world.dst_log, "key_unopenable", broken)
        before = world.here()
        screen.on_open_backup()
        assert asked  # the product's own check was the one that raised
        lines, enabled = world.summaries[0]
        assert not enabled and lines[-1] == view.RESTORE_NEEDS_AUDIT
        assert world.here() == before
        _closed_cleanly(world)

    def test_a_retention_check_that_raises_disables_restore(
        self, world: RWorld, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Stage-4 leg x3, the sibling: the retention setting's check that
        raises reads as unreadable — Restore disabled with its own line, the
        ages not judged, nothing written, the run closed."""
        world.entry()
        world.backup_file()
        screen = world.build()
        asked: list[str] = []

        def broken(*_args: Any, **_kwargs: Any) -> Any:
            asked.append("asked")
            raise RuntimeError("synthetic")

        monkeypatch.setattr(page_module, "read_past_session_settings", broken)
        before = world.here()
        screen.on_open_backup()
        assert asked
        lines, enabled = world.summaries[0]
        assert not enabled and lines[-1] == view.RESTORE_NEEDS_RETENTION
        assert any(line.startswith(f"To add: {view._rows(1)}.") for line in lines)
        assert world.here() == before
        _closed_cleanly(world)

    def test_a_key_that_cannot_be_opened_just_now_disables_restore(
        self, world: RWorld, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review round 33: a passing key problem disables Restore too (no row
        could be written), though it offers no reset."""
        from scribe_desktop.audit import AuditUnavailable

        world.entry()
        world.backup_file()
        fakes.row(world.dst_log)
        screen = world.build()

        def unavailable(*, create: bool = True) -> Any:
            raise AuditUnavailable("unavailable")

        monkeypatch.setattr(world.dst_log, "_open_key", unavailable)
        assert not world.dst_log.key_unreadable()
        before = world.here()
        screen.on_open_backup()
        lines, enabled = world.summaries[0]
        assert not enabled and lines[-1] == view.RESTORE_NEEDS_AUDIT
        assert world.here() == before
        _closed_cleanly(world)

    def test_what_was_left_out_names_both_parts(self, world: RWorld) -> None:
        """Review round 32 LOW-008: D10's words, a zero part included."""
        world.entry()

        def two_rows_left_out(doc: dict[str, Any]) -> None:
            doc["left_out"]["rows"] = 2

        world.backup_file(manifest=two_rows_left_out)
        world.answer = False
        world.build().on_open_backup()
        lines, _enabled = world.summaries[0]
        assert f"Left out when it was made: {view._sessions(0)}, {view._rows(2)}." in lines


class TestOpenRefusals:
    """Every refusal by name; one taken before the passphrase opens no run."""

    def test_the_gate_refuses_at_the_click(self, world: RWorld) -> None:
        world.gate.refusal = "Finish the recording first."
        screen = world.build()
        screen.on_open_backup()
        assert world.message() == "Finish the recording first."
        assert world.starts == [] and world.passphrases.asked == []

    def test_no_layer_refuses(self, world: RWorld) -> None:
        screen = world.build(layer=None)
        screen.on_open_backup()
        assert world.message() == view.OPEN_NO_LAYER
        assert world.starts == []

    def test_a_cancelled_file_dialog_does_nothing(self, world: RWorld) -> None:
        screen = world.build()
        screen.on_open_backup()
        assert len(world.starts) == 1
        assert world.passphrases.asked == [] and world.message() == ""

    def test_a_refused_source_is_never_read(self, world: RWorld) -> None:
        world.entry()
        path = world.backup_file()
        world.layer.attributes[str(path).casefold()] = 0x10  # a folder
        screen = world.build()
        screen.on_open_backup()
        assert world.message() == view.open_refused_line(BACKUP_SOURCE_REFUSED)
        assert world.passphrases.asked == [] and world.gate.begun == []

    def test_a_damaged_file_is_refused_before_the_passphrase(self, world: RWorld) -> None:
        path = world.drive / "damaged.csbk"
        path.write_bytes(b"not a backup at all")
        world.layer.attributes[str(path).casefold()] = _PLAIN_FILE
        world.chosen = path
        with pytest.raises(backup.BackupFormatError) as raised:
            backup.read_backup_header(path)
        screen = world.build()
        screen.on_open_backup()
        assert world.message() == view.backup_open_failed_line(view.hop_failure(raised.value))
        assert world.passphrases.asked == [] and world.gate.begun == []

    def test_another_channels_file_names_that_channel(self, world: RWorld) -> None:
        other = _other_channel()
        world.backup_file(header=lambda doc: doc.update(channel=other))
        screen = world.build()
        screen.on_open_backup()
        assert world.message() == f"This backup was made by {view.channel_words(other)}."
        assert world.passphrases.asked == []

    def test_a_cancelled_passphrase_opens_no_run(self, world: RWorld) -> None:
        world.entry()
        world.backup_file()
        world.passphrases.value = None
        screen = world.build()
        screen.on_open_backup()
        assert world.gate.begun == [] and screen._run is None
        assert world.summaries == []

    def test_a_wrong_passphrase(self, world: RWorld) -> None:
        world.entry()
        world.backup_file()
        world.passphrases.value = "not the passphrase it was made with"
        screen = world.build()
        screen.on_open_backup()
        assert world.message() == view.backup_open_failed_line(view.HopFailed("passphrase"))
        assert world.summaries == []
        _closed_cleanly(world)

    def test_the_gate_refuses_at_begin(self, world: RWorld) -> None:
        world.entry()
        world.backup_file()
        world.gate.begin_refusal = "Finish the recording first."
        screen = world.build()
        screen.on_open_backup()
        assert world.message() == "Finish the recording first."
        assert world.hops.count == 0 and world.summaries == []
        for given in world.passphrases.given:
            assert given == bytearray(len(given))
        assert screen._run is None


# ---------------------------------------------------------------------------
# Restore (Flow 3).
# ---------------------------------------------------------------------------


class TestRestore:
    def test_restore_adds_re_lists_and_advances_the_date(self, world: RWorld) -> None:
        sid = world.entry()
        world.backup_file()
        screen = world.build()
        screen.on_open_backup()
        assert world.listed() == [sid]
        assert [item.session_id for item in screen._listings] == [sid]  # re-listed
        assert world.message() == " ".join(
            [f"Restored {view._sessions(1)} and {view._rows(1)}.", view.RESTORE_CLINIC_KEYS]
        )
        assert read_backup_settings(world.config).settings.last_backup_at == fakes.NOW
        _closed_cleanly(world)

    def test_a_second_restore_changes_nothing(self, world: RWorld) -> None:
        world.entry()
        world.backup_file()
        screen = world.build()
        screen.on_open_backup()
        after_first = world.here()
        screen.on_open_backup()
        assert world.here() == after_first
        assert world.message() == f"Restored {view._sessions(0)} and {view._rows(0)}."
        lines, _enabled = world.summaries[1]
        to_add = f"To add: {view._sessions(0)}, {view._rows(0)}."
        assert any(line.startswith(to_add) for line in lines)
        _closed_cleanly(world)

    def test_a_restored_shadow_entry_refuses_copy(self, world: RWorld) -> None:
        sid = world.entry(shadow=True)
        world.backup_file()
        screen = world.build()
        screen.on_open_backup()
        screen.open_entry(sid)
        assert screen._copy_reason() == view.COPY_SHADOW
        assert not screen.copy_button.isEnabled()

    def test_a_failed_archived_mark_is_reported_and_finished_by_a_second_restore(
        self, world: RWorld, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        world.entry()
        world.backup_file()
        screen = world.build()
        real = world.dst_log.record_past_session
        monkeypatch.setattr(world.dst_log, "record_past_session", lambda *_a, **_k: False)
        screen.on_open_backup()
        assert f"{view._sessions(1)} {view.RESTORE_UNMARKED_TAIL}" in world.message()
        monkeypatch.setattr(world.dst_log, "record_past_session", real)
        screen.on_open_backup()
        assert view.RESTORE_UNMARKED_TAIL not in world.message()
        _closed_cleanly(world)

    def test_the_date_not_saved_is_one_sentence(
        self, world: RWorld, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sid = world.entry()
        world.backup_file()

        def refuse(*_args: Any, **_kwargs: Any) -> None:
            raise NoteConfigWriteError("synthetic")

        monkeypatch.setattr(page_module, "save_backup_settings", refuse)
        screen = world.build()
        screen.on_open_backup()
        assert world.listed() == [sid]
        assert view.RESTORE_DATE_NOT_SAVED in world.message()
        _closed_cleanly(world)

    def test_a_settings_file_that_cannot_be_read_is_left_as_it_is(self, world: RWorld) -> None:
        """Review round 32 LOW-005: never rewritten without its folder or
        with an earlier date."""
        sid = world.entry()
        world.backup_file()
        world.config.mkdir(parents=True, exist_ok=True)
        settings = world.config / "backup.json"
        settings.write_bytes(b"not a backup settings file")
        screen = world.build()
        screen.on_open_backup()
        assert world.listed() == [sid]
        assert view.RESTORE_DATE_NOT_SAVED in world.message()
        assert settings.read_bytes() == b"not a backup settings file"
        _closed_cleanly(world)

    def test_a_file_that_changed_after_open_restores_nothing(self, world: RWorld) -> None:
        world.entry()
        path = world.backup_file()
        world.entry()
        replacement = world.root / "replacement.csbk"
        fakes.build(world.root / "b-other", store=world.src, log=world.src_log).write(replacement)

        def swap() -> None:
            path.write_bytes(replacement.read_bytes())

        world.on_summary = swap
        screen = world.build()
        before = world.here()
        screen.on_open_backup()
        assert world.message() == view.restore_failed_line(view.HopFailed("source_changed"))
        assert world.here() == before
        _closed_cleanly(world)


class _Records(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


class TestEveryExitClosesTheRun:
    @pytest.fixture
    def records(self) -> Iterator[tuple[logging.Logger, _Records]]:
        logger = logging.getLogger("scribe-test-restore-diagnostic")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        handler = _Records()
        logger.addHandler(handler)
        yield logger, handler
        logger.removeHandler(handler)

    @staticmethod
    def _raise(*_args: Any, **_kwargs: Any) -> Any:
        raise KeyError("synthetic text that must not be logged")

    def test_an_unforeseen_planner_failure(
        self,
        world: RWorld,
        records: tuple[logging.Logger, _Records],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        logger, handler = records
        world.entry()
        world.backup_file()
        monkeypatch.setattr(page_module, "plan_restore", self._raise)
        world.build(logger=logger).on_open_backup()
        assert handler.lines == ["backup_unexpected detail_code=plan error_code=KeyError"]
        assert world.message() == view.backup_open_failed_line(view.HopFailed("unexpected"))
        assert world.summaries == []
        _closed_cleanly(world)

    def test_a_file_that_changed_before_the_plan_has_its_own_line(
        self,
        world: RWorld,
        records: tuple[logging.Logger, _Records],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Review round 32 LOW-010: a named failure, not logged."""
        logger, handler = records
        world.entry()
        world.backup_file()

        def changed(*_args: Any, **_kwargs: Any) -> Any:
            raise backup.BackupRunError("source_changed")

        monkeypatch.setattr(page_module, "plan_restore", changed)
        world.build(logger=logger).on_open_backup()
        line = view.backup_open_failed_line(view.HopFailed("source_changed"))
        assert line != view.backup_open_failed_line(view.HopFailed("unexpected"))
        assert world.message() == line
        assert handler.lines == [] and world.summaries == []
        _closed_cleanly(world)

    def test_an_unforeseen_restorer_failure(
        self,
        world: RWorld,
        records: tuple[logging.Logger, _Records],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        logger, handler = records
        world.entry()
        world.backup_file()
        monkeypatch.setattr(page_module, "restore_backup", self._raise)
        world.build(logger=logger).on_open_backup()
        assert handler.lines == ["backup_unexpected detail_code=restore error_code=KeyError"]
        assert world.message() == view.restore_failed_line(view.HopFailed("unexpected"))
        _closed_cleanly(world)

    def test_a_summary_dialog_that_raises(self, world: RWorld) -> None:
        world.entry()
        world.backup_file()

        def broken() -> None:
            raise RuntimeError("synthetic")

        world.on_summary = broken
        world.hops = Hops(deferred=True)  # the handler runs as from the event loop
        screen = world.build()
        before = world.here()
        screen.on_open_backup()
        with pytest.raises(RuntimeError):
            world.hops.run_all()  # re-raised for the exception hook
        assert world.here() == before
        _closed_cleanly(world)

    def test_a_worker_that_cannot_start(
        self, world: RWorld, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.ui.tasks import TaskThread

        started: list[Any] = []

        def refuse(task: Any) -> None:
            started.append(task)
            raise RuntimeError("synthetic")

        monkeypatch.setattr(TaskThread, "start", refuse)
        world.entry()
        world.backup_file()
        screen = world.build(real_runner=True)
        screen.on_open_backup()
        assert len(started) == 1
        assert world.message() == view.backup_open_failed_line(view.HopFailed("unexpected"))
        assert screen._hops == [] and screen._pending_hops == {}
        _closed_cleanly(world)


# ---------------------------------------------------------------------------
# The set-aside (Task 3.4).
# ---------------------------------------------------------------------------


def _refuse_key(world: RWorld, session_id: str) -> None:
    (world.dst.root / session_id / KEY_FILENAME).write_bytes(b"dpapi_refused:" + b"x" * 40)


class TestSetAside:
    def test_the_button_shows_only_while_a_label_cannot_be_read(self, world: RWorld) -> None:
        readable = fakes.published(world.dst)
        screen = world.build()
        assert screen.set_aside_button.isHidden()
        refused = fakes.published(world.dst)
        _refuse_key(world, refused)
        screen.refresh()
        assert not screen.set_aside_button.isHidden()
        assert screen.set_aside_button.text() == view.SET_ASIDE_LABEL
        assert screen.set_aside_button.isEnabled()
        screen.on_set_aside()
        assert world.confirmed == [(view.SET_ASIDE_CONFIRM, view.SET_ASIDE_ACTION)]
        assert world.message() == view.set_aside_line(SetAsideReport(moved=(refused,)))
        assert [item.session_id for item in screen._listings] == [readable]  # re-listed
        assert screen.set_aside_button.isHidden()

    def test_a_declined_confirmation_moves_nothing(self, world: RWorld) -> None:
        refused = fakes.published(world.dst)
        _refuse_key(world, refused)
        world.confirm_answer = False
        screen = world.build()
        screen.on_set_aside()
        assert world.listed() == [refused]
        assert world.gate.asked == 0

    def test_an_admission_refusal_moves_nothing(self, world: RWorld) -> None:
        refused = fakes.published(world.dst)
        _refuse_key(world, refused)
        world.gate.refusal = "Finish the recording first."
        screen = world.build()
        before = world.here()
        screen.on_set_aside()
        assert world.message() == "Finish the recording first."
        assert world.here() == before and world.listed() == [refused]

    def test_refused_while_a_run_holds_the_page(self, world: RWorld) -> None:
        refused = fakes.published(world.dst)
        _refuse_key(world, refused)
        world.entry()
        world.backup_file()
        world.hops = Hops(deferred=True)
        screen = world.build()
        screen.on_open_backup()
        assert not screen.set_aside_button.isEnabled()
        screen.on_set_aside()
        assert world.message() == view.SET_ASIDE_NOT_AVAILABLE
        assert world.confirmed == [] and world.listed() == [refused]
        world.answer = False
        world.hops.run_all()
        _closed_cleanly(world)

    def test_without_an_archive(self, world: RWorld) -> None:
        screen = world.build(store=None)
        assert screen.set_aside_button.isHidden()
        screen.on_set_aside()
        assert world.message() == view.SET_ASIDE_NOT_AVAILABLE

    def test_a_failed_probe_is_refused_by_name(self, world: RWorld) -> None:
        refused = fakes.published(world.dst)
        _refuse_key(world, refused)
        world.probe = lambda: False
        screen = world.build()
        screen.on_set_aside()
        assert world.message() == view.set_aside_failed_line(PastSessionError("dpapi_unavailable"))
        assert world.listed() == [refused]

    def test_the_sweeps_undated_count_is_lowered(self, world: RWorld) -> None:
        save_past_session_settings(
            PastSessionSettings(retention_days=MIN_RETENTION_DAYS), config_root=world.config
        )
        refused = fakes.published(world.dst)
        _refuse_key(world, refused)
        screen = world.build()
        screen._last_sweep = (MIN_RETENTION_DAYS, RetentionSweepReport(undated=2))
        screen.on_set_aside()
        swept = screen._current_sweep()
        assert swept is not None and swept.undated == 1

    @pytest.mark.parametrize(
        ("report", "expected"),
        [
            (SetAsideReport(), view.SET_ASIDE_NOTHING),
            (
                SetAsideReport(moved=("a" * 32,)),
                "Set aside 1 session that this Windows login can no longer open. Nothing was "
                "deleted. Open a backup to see how many sessions it can add back.",
            ),
            (
                SetAsideReport(moved=("a" * 32, "b" * 32), held=1, left=2, failed=1),
                "Set aside 2 sessions that this Windows login can no longer open. Nothing was "
                "deleted. Open a backup to see how many sessions it can add back. 1 was not "
                "moved: a recording file is still present, or could not be ruled out. 2 others "
                "were left as they are: they could not be safely assessed. 1 could not be moved.",
            ),
            (
                SetAsideReport(held=2, left=1),
                "No session was set aside. 2 were not moved: a recording file is still "
                "present, or could not be ruled out. 1 other was left as it is: it could not "
                "be safely assessed.",
            ),
        ],
    )
    def test_each_form_of_the_line(self, report: SetAsideReport, expected: str) -> None:
        assert view.set_aside_line(report) == expected

    @pytest.mark.parametrize("reason", ["dpapi_unavailable", "set_aside_unavailable", "unreadable"])
    def test_each_refusal_has_its_line(self, reason: str) -> None:
        line = view.set_aside_failed_line(PastSessionError(reason))
        assert "nothing was moved" in line.casefold() or line == view.LIST_UNREADABLE
        assert reason not in line


class TestTheRowFits:
    @pytest.mark.parametrize("width", ["150", "narrowest"])
    def test_open_a_backup_fits(self, qapp: Any, tmp_path: Path, width: str) -> None:
        from test_ui_phase_s import _AT_150_CHARS_LINES, _laid_out, _stand_in
        from test_ui_screens import _main_window

        window = _main_window(tmp_path)
        try:
            window.show_page(window.past_sessions_screen)
            if width == "150":
                _laid_out(qapp, window, *_stand_in(window, _AT_150_CHARS_LINES))
            else:
                _laid_out(qapp, window, 960, 640)
            backup_button = window.past_sessions_screen.backup_button
            open_button = window.past_sessions_screen.open_backup_button
            for button in (backup_button, open_button):
                assert button.isVisible()
                assert button.width() >= button.minimumSizeHint().width()
                left = button.mapTo(window, button.rect().topLeft()).x()
                assert 0 <= left and left + button.width() <= window.width()
            # One above the other (side by side they overflow the narrowest).
            top = backup_button.mapTo(window, backup_button.rect().topLeft()).y()
            assert open_button.mapTo(window, open_button.rect().topLeft()).y() > top
        finally:
            window.close()
            dispose(window)
