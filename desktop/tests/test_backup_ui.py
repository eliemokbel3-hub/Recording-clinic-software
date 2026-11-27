"""Past-sessions-backup plan Tasks 2.2-2.4 (Flow 1; D3, D4, D6, D7, D10,
D11; C1, C3): the two dialogs, Back up... on the Past sessions page, the
backup reminder and the wording a backup changes.

Fakes only (C9): an archive and an audit store with fake key seams under the
test's own folder, the test KDF floor, a fake ``WindowsLayer``, a fake run
gate, the dialogs and the worker injected (no real dialog, thread or
clipboard). Synthetic content only."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import backup_fakes as fakes  # noqa: E402
from scribe_desktop import past_sessions_backup as backup  # noqa: E402
from scribe_desktop.exclusions import (  # noqa: E402
    BACKUP_SAME_DISK,
    DRIVE_FIXED,
    DRIVE_REMOTE,
    DRIVE_REMOVABLE,
    EXPORT_NETWORK,
)
from scribe_desktop.note_config import (  # noqa: E402
    BackupSettings,
    NoteConfigWriteError,
    read_backup_settings,
    save_backup_settings,
)
from scribe_desktop.past_sessions import AUDIO_KEY_FILENAME  # noqa: E402
from scribe_desktop.past_sessions_backup import (  # noqa: E402
    BackupReport,
    BackupRunError,
    LeftOut,
)
from scribe_desktop.session_store import KEY_FILENAME  # noqa: E402
from scribe_desktop.ui import backup_dialog  # noqa: E402
from scribe_desktop.ui import past_sessions as page_module  # noqa: E402
from scribe_desktop.ui import past_sessions_view as view  # noqa: E402
from scribe_desktop.ui.past_sessions import ArchiveRun  # noqa: E402
from test_archive_backup_location import VOL_E, Layer  # noqa: E402

PASSPHRASE = "correct horse battery staple, twenty+"
# The data folder's volume as the fake layer names it (its LOCALAPPDATA is on
# C:), for the same-disk warning.
_DATA_VOLUME = "\\\\?\\Volume{letter-C}\\"


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def fast_kdf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backup, "_kdf_floor_for_tests", backup.KdfFloor())


# ---------------------------------------------------------------------------
# Seams.
# ---------------------------------------------------------------------------


class FakeGate:
    """``MainWindow``'s run gate as the page uses it: a refusal at the click
    and at ``begin``, and every run it held and released."""

    def __init__(self, *, refusal: str | None = None, begin_refusal: str | None = None) -> None:
        self.refusal = refusal
        self.begin_refusal = begin_refusal
        self.asked = 0
        self.begun: list[ArchiveRun] = []
        self.released: list[ArchiveRun] = []
        self.held: ArchiveRun | None = None

    def archive_run_refusal(self) -> str | None:
        self.asked += 1
        return self.refusal

    def begin_archive_run(self, run: ArchiveRun) -> str | None:
        if self.begin_refusal is not None:
            return self.begin_refusal
        self.begun.append(run)
        self.held = run
        run.hold_gate(self._release)
        return None

    def _release(self, run: ArchiveRun) -> None:
        self.released.append(run)
        self.held = None


class Hops:
    """The worker seam: runs each hop at once, or (``deferred``) keeps it
    until ``run_all`` — so a test can look at the page mid-run."""

    def __init__(self, *, deferred: bool = False) -> None:
        self.deferred = deferred
        self.pending: list[tuple[Callable[[], object], Callable[[object], None]]] = []
        self.count = 0

    def __call__(self, work: Callable[[], object], done: Callable[[object], None]) -> None:
        self.count += 1
        if self.deferred:
            self.pending.append((work, done))
            return
        done(work())

    def run_all(self) -> None:
        while self.pending:
            work, done = self.pending.pop(0)
            done(work())


class Passphrases:
    """The passphrase seam: hands over a fresh ``bytearray`` (kept, so a test
    can see it zeroed) or None for a cancel."""

    def __init__(self, value: str | None = PASSPHRASE) -> None:
        self.value = value
        self.given: list[bytearray] = []
        self.asked: list[bool] = []

    def __call__(self, twice: bool) -> bytearray | None:
        self.asked.append(twice)
        if self.value is None:
            return None
        buffer = bytearray(self.value, "utf-8")
        self.given.append(buffer)
        return buffer


class World:
    """An archive and an audit store (fake keys), a destination folder on a
    removable volume the fake layer knows, and the page over them."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.store = fakes.archive(root)
        self.log = fakes.audit_log(root)
        self.dest = root / "dest"
        self.dest.mkdir()
        self.config = root / "config"
        self.layer = Layer(volumes={str(self.dest).casefold(): (VOL_E, DRIVE_REMOVABLE)})
        self.gate = FakeGate()
        self.hops = Hops()
        self.passphrases = Passphrases()
        self.paths: list[tuple[Path | None, str]] = []
        self.chosen: Path | None = self.dest / "anything.csbk"
        self.confirmed: list[tuple[str, str]] = []
        self.confirm_answer = True
        self.clock = fakes.NOW
        self.screen: Any = None

    def choose(self, start: Path | None, proposed: str) -> Path | None:
        self.paths.append((start, proposed))
        return self.chosen

    def confirm(self, text: str, action: str) -> bool:
        self.confirmed.append((text, action))
        return self.confirm_answer

    def build(
        self,
        *,
        audit: Any = "log",
        layer: Any = "layer",
        real_runner: bool = False,
        logger: Any = None,
    ) -> Any:
        from scribe_desktop.ui.past_sessions import PastSessionsScreen

        screen = PastSessionsScreen(
            self.store,
            audit=self.log if audit == "log" else audit,
            config_root=self.config,
            clock=lambda: self.clock,
            monotonic=lambda: 100.0,
            local_zone=UTC,
            confirm=self.confirm,
            choose_csv_path=lambda: pytest.fail("a CSV save dialog"),
            choose_wav_path=lambda _sid: pytest.fail("a WAV save dialog"),
            windows_layer=self.layer if layer == "layer" else layer,
            ask_passphrase=self.passphrases,
            choose_backup_path=self.choose,
            # ``real_runner``: the page's own ``_run_task`` (a test then fakes
            # ``TaskThread.start``; no thread is ever started).
            run_hop=None if real_runner else self.hops,
            logger=logger,
        )
        screen.set_archive_gate(self.gate)
        self.screen = screen
        return screen

    def published(self) -> list[Path]:
        return sorted(self.dest.iterdir())


@pytest.fixture
def world(qapp: Any, tmp_path: Path) -> Iterator[World]:
    root = tmp_path / "w"
    root.mkdir()
    made = World(root)
    yield made
    if made.screen is not None:
        made.screen.deleteLater()


def _settings(world: World) -> BackupSettings:
    return read_backup_settings(world.config).settings


def _closed_cleanly(world: World) -> None:
    """Every exit: the run's buffers zeroed and the gate (if taken) released."""
    for given in world.passphrases.given:
        assert given == bytearray(len(given))
    assert world.gate.held is None
    assert world.gate.released == world.gate.begun
    for run in world.gate.begun:
        assert run.closed and run.backup_key is None and run.passphrase is None
    assert world.screen._run is None
    assert world.screen.backup_button.isEnabled()


def _name() -> str:
    day = fakes.NOW.astimezone().strftime("%Y-%m-%d")
    return f"{backup.BACKUP_FILENAME_PREFIX}{day}.csbk"


# ---------------------------------------------------------------------------
# The passphrase decision and the dialogs (Task 2.2).
# ---------------------------------------------------------------------------


class TestPassphraseDecision:
    @pytest.mark.parametrize(
        ("first", "second", "minimum", "expected"),
        [
            ("", "", 20, backup_dialog.PASSPHRASE_EMPTY),
            ("x" * 19, "x" * 19, 20, backup_dialog.passphrase_too_short(20)),
            ("x" * 20, "x" * 21, 20, backup_dialog.PASSPHRASE_MISMATCH),
            ("x" * 20, "x" * 20, 20, None),
            ("a b c d e f g h i j k", "a b c d e f g h i j k", 20, None),  # no composition
            ("short", None, 1, None),  # Open: once, any length
            ("", None, 1, backup_dialog.PASSPHRASE_EMPTY),
        ],
    )
    def test_each_outcome(
        self, first: str, second: str | None, minimum: int, expected: str | None
    ) -> None:
        assert backup_dialog.passphrase_decision(first, second, minimum=minimum) == expected

    def test_no_refusal_echoes_the_passphrase(self) -> None:
        secret = "a secret passphrase"
        for second in ("different value here!", None):
            line = backup_dialog.passphrase_decision(secret, second, minimum=40)
            assert line is not None and secret not in line

    def test_the_minimum_is_twenty(self) -> None:
        assert backup_dialog.PASSPHRASE_MINIMUM == 20
        assert backup_dialog.BACKUP_PASSPHRASE_INTRO.endswith(
            "The passphrase is never stored. Without it the backup cannot be opened by "
            "anyone, including you."
        )


def _type(field: Any, text: str) -> None:
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication

    for ch in text:
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier, ch)
        QApplication.sendEvent(field, event)


class TestThePassphraseDialog:
    def test_accept_hands_a_bytearray_once_and_empties_the_fields(self, qapp: Any) -> None:
        dialog = backup_dialog.PassphraseDialog(confirm=True)
        for field in dialog.fields():
            field.setText(PASSPHRASE)
        dialog.accept()
        value = dialog.take_passphrase()
        assert isinstance(value, bytearray) and value == bytearray(PASSPHRASE, "utf-8")
        assert dialog.take_passphrase() is None  # once
        assert all(field.text() == "" for field in dialog.fields())
        dialog.deleteLater()

    def test_a_refused_accept_empties_the_fields_and_says_why(self, qapp: Any) -> None:
        dialog = backup_dialog.PassphraseDialog(confirm=True)
        assert dialog.second_field is not None
        dialog.first_field.setText(PASSPHRASE)
        dialog.second_field.setText(PASSPHRASE + "!")
        dialog.accept()
        assert dialog.take_passphrase() is None
        assert dialog.error_label.text() == backup_dialog.PASSPHRASE_MISMATCH
        assert all(field.text() == "" for field in dialog.fields())
        dialog.deleteLater()

    @pytest.mark.parametrize("exit_by", ["reject", "close"])
    def test_reject_and_close_empty_the_fields(self, qapp: Any, exit_by: str) -> None:
        dialog = backup_dialog.PassphraseDialog(confirm=True)
        for field in dialog.fields():
            field.setText(PASSPHRASE)
        if exit_by == "reject":
            dialog.reject()
        else:
            dialog.show()
            dialog.close()
        assert dialog.take_passphrase() is None
        assert all(field.text() == "" for field in dialog.fields())
        dialog.deleteLater()

    def test_open_asks_once(self, qapp: Any) -> None:
        dialog = backup_dialog.PassphraseDialog(confirm=False)
        assert dialog.second_field is None and len(dialog.fields()) == 1
        dialog.first_field.setText("x")
        dialog.accept()
        assert dialog.take_passphrase() == bytearray(b"x")
        dialog.deleteLater()

    def test_neither_text_signal_delivers_a_value(self, qapp: Any) -> None:
        field = backup_dialog.PassphraseField()
        seen: list[str] = []
        field.textChanged.connect(seen.append)
        field.textEdited.connect(seen.append)
        _type(field, "secret")
        field.setText("another secret")
        field.wipe()
        assert seen == []
        assert field.echoMode() == field.EchoMode.Password
        field.deleteLater()

    def test_copy_and_cut_place_nothing_by_shortcut_or_context_menu(
        self, qapp: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Asserted, not assumed from the echo mode: Copy and Cut keys never
        reach Qt's own handling (a guard on the base class fails if they do,
        before native Qt runs), ``copy`` and ``cut`` are never called, the
        field has no context menu (Qt's menu builder is never called) and drag
        is off. The platform is ``offscreen`` (Qt's in-process clipboard,
        never the Windows one), and the guards keep even that untouched."""
        from PySide6.QtCore import QEvent, QPoint, Qt
        from PySide6.QtGui import QContextMenuEvent, QGuiApplication, QKeyEvent, QKeySequence
        from PySide6.QtWidgets import QApplication, QLineEdit

        assert QGuiApplication.platformName() == "offscreen"
        monkeypatch.setattr(QLineEdit, "copy", lambda _self: pytest.fail("copy was called"))
        monkeypatch.setattr(QLineEdit, "cut", lambda _self: pytest.fail("cut was called"))
        native = QLineEdit.keyPressEvent

        def guard(widget: Any, event: Any) -> None:
            if event.matches(QKeySequence.StandardKey.Copy) or event.matches(
                QKeySequence.StandardKey.Cut
            ):
                raise AssertionError("a Copy or Cut key reached Qt's own handling")
            native(widget, event)

        monkeypatch.setattr(QLineEdit, "keyPressEvent", guard)
        monkeypatch.setattr(
            QLineEdit,
            "createStandardContextMenu",
            lambda _self: pytest.fail("a context menu was built"),
        )
        field = backup_dialog.PassphraseField()
        field.setText(PASSPHRASE)
        field.selectAll()
        control = Qt.KeyboardModifier.ControlModifier
        for key in (Qt.Key.Key_C, Qt.Key.Key_X):
            QApplication.sendEvent(field, QKeyEvent(QEvent.Type.KeyPress, key, control))
        QApplication.sendEvent(
            field, QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(2, 2))
        )
        assert field.text() == PASSPHRASE  # Cut removed nothing either
        assert field.contextMenuPolicy() == Qt.ContextMenuPolicy.NoContextMenu
        assert not field.dragEnabled()
        field.deleteLater()


class TestTheSummaryDialog:
    def test_close_is_the_default_and_restore_follows_its_flag(self, qapp: Any) -> None:
        lines = ["This backup opens: no sessions and 2 audit rows.", "To add: 2 audit rows."]
        dialog = backup_dialog.SummaryDialog(lines, restore_enabled=False)
        assert [label.text() for label in dialog.line_labels] == lines
        assert dialog.close_button.isDefault()
        assert not dialog.restore_button.isDefault()
        assert not dialog.restore_button.isEnabled()
        dialog.deleteLater()
        dialog = backup_dialog.SummaryDialog(lines, restore_enabled=True)
        assert dialog.restore_button.isEnabled() and dialog.close_button.isDefault()
        dialog.deleteLater()

    def test_show_summary_is_parented_to_the_window_not_the_page(
        self, qapp: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from PySide6.QtWidgets import QDialog, QWidget

        parents: list[Any] = []

        def record(dialog: Any) -> int:
            parents.append(dialog.parentWidget())
            return int(QDialog.DialogCode.Rejected)

        monkeypatch.setattr(backup_dialog.SummaryDialog, "exec", record)
        window = QWidget()
        page = QWidget(window)
        assert backup_dialog.show_summary(page, ["x"], restore_enabled=True) is False
        assert parents == [window]
        window.deleteLater()


class TestTheDialogsHoldNoCopyableWidget:
    def _dialogs(self) -> list[Any]:
        return [
            backup_dialog.PassphraseDialog(confirm=True),
            backup_dialog.PassphraseDialog(confirm=False),
            backup_dialog.SummaryDialog(["a line"], restore_enabled=True),
        ]

    def test_no_selectable_text_list_item_view_or_combo_box(self, qapp: Any) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QAbstractItemView,
            QComboBox,
            QLabel,
            QLineEdit,
            QPlainTextEdit,
            QTextEdit,
        )

        selectable = (
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        for dialog in self._dialogs():
            assert dialog.findChildren(QAbstractItemView) == []
            assert dialog.findChildren(QComboBox) == []
            assert dialog.findChildren(QPlainTextEdit) == []
            assert dialog.findChildren(QTextEdit) == []
            for label in dialog.findChildren(QLabel):
                assert not label.textInteractionFlags() & selectable
            for field in dialog.findChildren(QLineEdit):
                assert isinstance(field, backup_dialog.PassphraseField)
            dialog.deleteLater()

    def test_both_dialogs_render_in_light_and_dark(self, qapp: Any) -> None:
        from scribe_desktop.ui import theme

        saved = qapp.property(theme.SCHEME_PROPERTY)
        try:
            for scheme in ("light", "dark"):
                theme.force_scheme(scheme)
                theme.apply_theme(qapp)
                for dialog in self._dialogs():
                    dialog.show()
                    qapp.processEvents()
                    assert not dialog.grab().isNull()
                    if isinstance(dialog, backup_dialog.PassphraseDialog):
                        assert dialog.error_label.property("role") == "error"
                    dialog.close()
                    dialog.deleteLater()
        finally:
            # The application is left exactly as it was: its palette, sheet,
            # token set and scheme marker all the saved scheme's again (a
            # marker restored alone would disagree with a dark palette, so the
            # next same-scheme apply would restyle — test_ui_theme's pin).
            theme.force_scheme(None)
            if saved in ("light", "dark"):
                theme.apply_theme(qapp, saved)
            else:
                qapp.setProperty(theme.SCHEME_PROPERTY, saved)


# ---------------------------------------------------------------------------
# Back up... (Task 2.3).
# ---------------------------------------------------------------------------


class TestBackUp:
    def test_the_button_is_enabled_on_a_fresh_store(self, world: World) -> None:
        screen = world.build()
        screen.refresh()
        assert screen.backup_button.isEnabled()
        assert screen.backup_button.text() == view.BACKUP_LABEL

    def test_an_empty_store_answers_nothing_to_back_up_from_its_snapshot(
        self, world: World
    ) -> None:
        screen = world.build()
        screen.on_backup()
        assert screen.message_label.text() == view.BACKUP_NOTHING == "Nothing to back up yet."
        assert world.published() == []
        assert not (world.config / "backup.json").exists()
        _closed_cleanly(world)

    def test_a_backup_is_written_and_says_nothing_eligible_was_left_out(
        self, world: World
    ) -> None:
        session_id = fakes.published(world.store)
        fakes.row(world.log, session_id=session_id)
        screen = world.build()
        screen.on_backup()
        assert [path.name for path in world.published()] == [_name()]
        assert screen.message_label.text() == (
            f"Backup written: {_name()} - 1 session, 1 audit row. Nothing eligible was "
            "left out. Keep the passphrase somewhere other than the drive."
        )
        settings = _settings(world)
        assert settings.last_backup_at == fakes.NOW
        assert settings.folder == str(world.dest)
        assert world.passphrases.asked == [True]
        assert len(world.gate.begun) == 1
        _closed_cleanly(world)
        # The file opens with the passphrase (hop A's salt is the header's).
        opened = backup.open_backup(world.published()[0], PASSPHRASE.encode())
        try:
            assert list(opened.reader.manifest.entries) == [session_id]
        finally:
            backup.zero(opened.key)

    def test_a_left_out_session_gives_the_left_out_form(self, world: World) -> None:
        fakes.published(world.store)
        broken = fakes.published(world.store)
        (world.store.root / broken / KEY_FILENAME).write_bytes(b"not a key")
        screen = world.build()
        screen.on_backup()
        assert screen.message_label.text() == (
            f"Backup written: {_name()} - 1 session, 0 audit rows. Left out: 1 session. "
            "Keep the passphrase somewhere other than the drive."
        )
        _closed_cleanly(world)

    def test_a_session_holding_a_recording_is_counted_apart(self, world: World) -> None:
        fakes.published(world.store)
        held = fakes.published(world.store)
        (world.store.root / held / AUDIO_KEY_FILENAME).write_bytes(b"\x01" * 60)  # live
        screen = world.build()
        screen.on_backup()
        assert screen.message_label.text() == (
            f"Backup written: {_name()} - 1 session, 0 audit rows. Nothing eligible was "
            "left out. 1 session is not in a backup because a kept recording or its key is "
            "still present. Keep the passphrase somewhere other than the drive."
        )
        _closed_cleanly(world)

    def test_a_name_typed_in_the_dialog_never_reaches_the_drive(self, world: World) -> None:
        fakes.published(world.store)
        world.chosen = world.dest / "a typed name.csbk"
        screen = world.build()
        screen.on_backup()
        assert [path.name for path in world.published()] == [_name()]
        assert world.paths == [(None, view.backup_default_name(fakes.NOW, UTC))]

    def test_the_second_backup_of_the_day_takes_the_next_suffix(self, world: World) -> None:
        fakes.published(world.store)
        screen = world.build()
        screen.on_backup()
        screen.on_backup()
        second = _name().replace(".csbk", "-2.csbk")
        assert [path.name for path in world.published()] == sorted([_name(), second])
        assert screen.message_label.text().startswith(f"Backup written: {second} - ")

    def test_the_date_is_saved_only_after_a_verified_published_file(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fakes.published(world.store)

        def unverified(*_args: Any, **_kwargs: Any) -> BackupReport:
            raise BackupRunError("publish_unverified")

        monkeypatch.setattr(page_module, "write_backup_file", unverified)
        screen = world.build()
        screen.on_backup()
        assert screen.message_label.text() == view.backup_failed_line(
            view.HopFailed("publish_unverified")
        )
        assert not (world.config / "backup.json").exists()
        _closed_cleanly(world)

    def test_a_settings_write_that_fails_keeps_the_success_line(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fakes.published(world.store)

        def refuse(*_args: Any, **_kwargs: Any) -> Path:
            raise NoteConfigWriteError("synthetic")

        monkeypatch.setattr(page_module, "save_backup_settings", refuse)
        screen = world.build()
        screen.on_backup()
        assert screen.message_label.text() == (
            f"Backup written: {_name()} - 1 session, 0 audit rows. Nothing eligible was "
            "left out. Keep the passphrase somewhere other than the drive. The backup date "
            "could not be saved - the reminder will not know about this backup."
        )
        assert len(world.published()) == 1
        _closed_cleanly(world)

    def test_the_audit_record_unreadable_refuses_with_nothing_written(
        self, world: World
    ) -> None:
        fakes.published(world.store)
        fakes.row(world.log)
        (world.log.root / KEY_FILENAME).write_bytes(b"not this store's key")
        screen = world.build()
        screen.on_backup()
        assert screen.message_label.text() == (
            "The audit record cannot be read - see Past sessions problems in the downtime "
            "procedure."
        )
        assert world.published() == []
        _closed_cleanly(world)

    # --- every exit closes the run (D4) ---------------------------------------

    def test_a_refused_admission_asks_for_nothing(self, world: World) -> None:
        world.gate.refusal = view.ARCHIVE_LIVE_LINE
        screen = world.build()
        screen.on_backup()
        assert screen.message_label.text() == view.ARCHIVE_LIVE_LINE
        assert world.passphrases.asked == [] and world.paths == []

    def test_a_cancelled_passphrase_holds_nothing(self, world: World) -> None:
        world.passphrases.value = None
        screen = world.build()
        screen.on_backup()
        assert world.paths == [] and world.gate.begun == []
        assert screen._run is None and screen.backup_button.isEnabled()

    def test_a_cancelled_save_dialog_closes_the_run(self, world: World) -> None:
        world.chosen = None
        screen = world.build()
        screen.on_backup()
        assert world.gate.begun == [] and world.hops.count == 0
        _closed_cleanly(world)

    def test_a_refused_location_is_never_written(self, world: World) -> None:
        fakes.published(world.store)
        world.layer.drives["Z:\\"] = DRIVE_REMOTE
        world.chosen = Path("Z:\\backups\\x.csbk")
        screen = world.build()
        screen.on_backup()
        assert screen.message_label.text() == view.backup_refused_line(EXPORT_NETWORK)
        assert world.gate.begun == [] and world.hops.count == 0
        _closed_cleanly(world)

    def test_no_windows_layer_refuses_before_asking(self, world: World) -> None:
        screen = world.build(layer=None)
        screen.on_backup()
        assert screen.message_label.text() == view.BACKUP_NO_LAYER
        assert world.passphrases.asked == []

    @pytest.mark.parametrize("answer", [False, True])
    def test_the_same_disk_warning_is_asked(self, world: World, answer: bool) -> None:
        fakes.published(world.store)
        world.layer.volumes[str(world.dest).casefold()] = (_DATA_VOLUME, DRIVE_FIXED)
        world.confirm_answer = answer
        screen = world.build()
        screen.on_backup()
        assert world.confirmed == [
            (f"{BACKUP_SAME_DISK} Back up to this folder anyway?", "Back up here")
        ]
        assert bool(world.published()) is answer
        _closed_cleanly(world)

    def test_a_refusal_at_begin_closes_the_run(self, world: World) -> None:
        world.gate.begin_refusal = view.ARCHIVE_RECOVERY_LINE
        screen = world.build()
        screen.on_backup()
        assert screen.message_label.text() == view.ARCHIVE_RECOVERY_LINE
        assert world.hops.count == 0
        _closed_cleanly(world)

    def test_hop_a_failing_by_memory_is_named(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def no_memory(*_args: Any, **_kwargs: Any) -> bytes:
            raise MemoryError

        monkeypatch.setattr(backup, "argon2id_derive", no_memory)
        screen = world.build()
        screen.on_backup()
        assert screen.message_label.text() == view.backup_failed_line(
            view.HopFailed("kdf_memory")
        )
        _closed_cleanly(world)

    def test_a_worker_reporting_unexpected_closes_the_run(self, world: World) -> None:
        fakes.published(world.store)
        screen = world.build()
        screen._run_hop = lambda _work, done: done(view.HopFailed("unexpected"))
        screen.on_backup()
        assert screen.message_label.text() == (
            "The backup was not made: an unexpected problem on this computer stopped it."
        )
        _closed_cleanly(world)

    def test_a_failed_dispatch_closes_the_run(self, world: World) -> None:
        screen = world.build()

        def refuse(_work: Any, _done: Any) -> None:
            raise RuntimeError("no thread")

        screen._run_hop = refuse
        screen.on_backup()
        assert screen.message_label.text() == view.backup_failed_line(
            view.HopFailed("unexpected")
        )
        _closed_cleanly(world)

    def test_a_raise_after_the_passphrase_closes_the_run(self, world: World) -> None:
        """Review round 27 LOW-001: an unforeseen raise between the dialogs
        closes the run (zeroed, released) and still reaches the hook."""
        world.layer.volumes[str(world.dest).casefold()] = (_DATA_VOLUME, DRIVE_FIXED)

        def broken(_text: str, _action: str) -> bool:
            raise RuntimeError("synthetic")

        world.confirm = broken
        screen = world.build()
        with pytest.raises(RuntimeError):
            screen.on_backup()
        _closed_cleanly(world)
        assert screen.message_label.text() == view.backup_failed_line(
            view.HopFailed("unexpected")
        )

    def test_a_handler_that_raises_closes_the_run(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review round 27 LOW-001: hop D raising something unforeseen still
        ends the run with the fixed line and releases the gate."""
        fakes.published(world.store)

        def broken(*_args: Any, **_kwargs: Any) -> Path:
            raise RuntimeError("synthetic")

        monkeypatch.setattr(page_module, "save_backup_settings", broken)
        screen = world.build()
        screen.on_backup()
        assert screen.message_label.text() == view.backup_failed_line(
            view.HopFailed("unexpected")
        )
        assert len(world.gate.begun) == 1
        _closed_cleanly(world)

    def test_hop_c_failing_closes_the_run_and_says_a_part_may_remain(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fakes.published(world.store)

        def failed(*_args: Any, **_kwargs: Any) -> BackupReport:
            raise BackupRunError("write_failed", part_may_remain=True)

        monkeypatch.setattr(page_module, "write_backup_file", failed)
        screen = world.build()
        screen.on_backup()
        assert screen.message_label.text() == (
            "The backup could not be written to that folder - check the drive and try "
            "again. A partial backup file may remain on the drive."
        )
        _closed_cleanly(world)

    def test_the_gate_is_held_across_the_hops_and_the_passphrase_goes_after_hop_a(
        self, world: World
    ) -> None:
        fakes.published(world.store)
        world.hops = Hops(deferred=True)
        screen = world.build()
        screen.on_backup()
        [run] = world.gate.begun
        assert world.gate.held is run and run.passphrase is not None
        assert not screen.backup_button.isEnabled()
        work, done = world.hops.pending.pop(0)
        done(work())  # hop A
        assert run.passphrase is None and run.backup_key is not None
        assert world.passphrases.given[0] == bytearray(len(world.passphrases.given[0]))
        assert world.gate.held is run  # hop C still to come
        world.hops.run_all()
        assert world.gate.held is None and run.backup_key is None
        assert len(world.published()) == 1

    def test_the_remembered_folder_is_proposed_only_while_it_passes(
        self, world: World
    ) -> None:
        save_backup_settings(BackupSettings(folder=str(world.dest)), config_root=world.config)
        world.chosen = None
        screen = world.build()
        screen.on_backup()
        save_backup_settings(BackupSettings(folder="Z:\\gone"), config_root=world.config)
        world.layer.drives["Z:\\"] = DRIVE_REMOTE
        screen.on_backup()
        assert [start for start, _name in world.paths] == [world.dest, None]
        assert ("realpath", "Z:\\gone") not in world.layer.touched  # text-first


class TestTheProductionWorker:
    """The real ``run_hop``'s bookkeeping, without starting a thread: ``done``
    is called exactly once — with the result, or, when the worker ended with
    neither result signal, with ``unexpected`` (D4's fallback)."""

    def test_a_worker_that_ends_without_a_result_reports_unexpected(
        self, world: World
    ) -> None:
        from scribe_desktop.ui.tasks import TaskThread

        screen = world.build()
        seen: list[object] = []
        task = TaskThread(lambda: None)
        screen._pending_hops[task] = seen.append
        screen._hops.append(task)
        assert screen.is_busy
        screen._hop_ended(task)
        assert seen == [view.HopFailed("unexpected")]
        assert not screen.is_busy

    def test_a_result_then_the_end_reports_once(self, world: World) -> None:
        from scribe_desktop.ui.tasks import TaskThread

        screen = world.build()
        seen: list[object] = []
        task = TaskThread(lambda: None)
        screen._pending_hops[task] = seen.append
        screen._hops.append(task)
        screen._deliver(task, True)
        screen._hop_ended(task)
        assert seen == [True]


class TestAFailedWorkerStart:
    """Peer round 29 PR-LOW-201: the real dispatcher, with a ``start`` that
    raises before any thread runs — the run closes, its registration goes
    with it, and the page is not left busy (a later run is admitted and a
    close is not refused)."""

    @pytest.fixture
    def refused_start(self, monkeypatch: pytest.MonkeyPatch) -> list[Any]:
        from scribe_desktop.ui.tasks import TaskThread

        started: list[Any] = []

        def refuse(task: Any) -> None:
            started.append(task)
            raise RuntimeError("synthetic")

        monkeypatch.setattr(TaskThread, "start", refuse)
        return started

    def _nothing_registered(self, screen: Any) -> None:
        assert screen._hops == [] and screen._pending_hops == {}
        assert not screen.is_busy

    def test_hop_a_whose_worker_cannot_start(self, world: World, refused_start: list[Any]) -> None:
        screen = world.build(real_runner=True)
        screen.on_backup()
        assert len(refused_start) == 1
        assert screen.message_label.text() == view.backup_failed_line(
            view.HopFailed("unexpected")
        )
        _closed_cleanly(world)
        self._nothing_registered(screen)
        screen.on_backup()  # admitted again: nothing holds the page busy
        assert len(world.gate.begun) == 2 and len(refused_start) == 2
        _closed_cleanly(world)
        self._nothing_registered(screen)

    def test_hop_c_whose_worker_cannot_start(self, world: World, refused_start: list[Any]) -> None:
        fakes.published(world.store)
        world.hops = Hops(deferred=True)
        screen = world.build()
        screen.on_backup()  # hop A held by the fake runner
        screen._run_hop = screen._run_task  # hop C goes to the real dispatcher
        world.hops.run_all()
        assert len(refused_start) == 1
        assert screen.message_label.text() == view.backup_failed_line(
            view.HopFailed("unexpected")
        )
        assert world.published() == []
        _closed_cleanly(world)
        self._nothing_registered(screen)

    def test_the_window_admits_and_closes_after_a_worker_that_never_ran(
        self, qapp: Any, tmp_path: Path, refused_start: list[Any]
    ) -> None:
        """What ``closeEvent`` and the admission read: no gate held and the
        page not busy, so neither refuses on the backup's account."""
        from test_ui_screens import _main_window

        root = tmp_path / "w"
        root.mkdir()
        world = World(root)
        window = _main_window(
            tmp_path,
            past_sessions=world.store,
            audit=world.log,
            windows_layer=world.layer,
            past_sessions_passphrase=world.passphrases,
            past_sessions_backup_path=world.choose,
            past_sessions_run_hop=None,
            config_root=world.config,
        )
        try:
            window.show_page(window.past_sessions_screen)
            window.past_sessions_screen.on_backup()
            assert len(refused_start) == 1
            assert not window.archive_running
            assert not window.past_sessions_screen.is_busy
            assert window.archive_run_refusal() is None
        finally:
            run = window._archive_run
            if run is not None:
                run.close()
            window.close()
            window.deleteLater()


class _Records(logging.Handler):
    """Every formatted message the page's logger receives."""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


class TestTheUnforeseenFailureIsLoggedByType:
    """Peer round 29 PR-LOW-202 (D4, C3): an unforeseen exception at each
    boundary — hop A's worker, hop B's snapshot, hop C's worker, the
    dispatch — is logged ONCE, as its stage and type name only; the line is
    the fixed one, the run closes, and a named failure logs nothing."""

    @pytest.fixture
    def records(self) -> Iterator[tuple[logging.Logger, _Records]]:
        logger = logging.getLogger("scribe-test-backup-diagnostic")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        handler = _Records()
        logger.addHandler(handler)
        yield logger, handler
        logger.removeHandler(handler)

    def _unforeseen(self, kind: type[Exception]) -> Callable[..., Any]:
        def raise_it(*_args: Any, **_kwargs: Any) -> Any:
            raise kind("synthetic text that must not be logged")

        return raise_it

    def _assert_logged_once(
        self, world: World, handler: _Records, stage: str, type_name: str
    ) -> None:
        assert handler.lines == [f"backup_unexpected detail_code={stage} error_code={type_name}"]
        assert world.screen.message_label.text() == view.backup_failed_line(
            view.HopFailed("unexpected")
        )
        assert not any("synthetic" in line for line in handler.lines)
        _closed_cleanly(world)

    def test_hop_a(
        self,
        world: World,
        records: tuple[logging.Logger, _Records],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        logger, handler = records
        monkeypatch.setattr(page_module, "new_kdf_params", self._unforeseen(KeyError))
        world.build(logger=logger).on_backup()
        self._assert_logged_once(world, handler, "derive", "KeyError")

    def test_hop_b(
        self,
        world: World,
        records: tuple[logging.Logger, _Records],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        logger, handler = records
        monkeypatch.setattr(page_module, "prepare_backup", self._unforeseen(ZeroDivisionError))
        world.build(logger=logger).on_backup()
        self._assert_logged_once(world, handler, "snapshot", "ZeroDivisionError")

    def test_hop_c(
        self,
        world: World,
        records: tuple[logging.Logger, _Records],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        logger, handler = records
        fakes.published(world.store)
        monkeypatch.setattr(page_module, "write_backup_file", self._unforeseen(LookupError))
        world.build(logger=logger).on_backup()
        self._assert_logged_once(world, handler, "write", "LookupError")
        assert world.published() == []

    @pytest.mark.parametrize("removed", [True, False])
    def test_inside_the_real_writer(
        self,
        world: World,
        records: tuple[logging.Logger, _Records],
        monkeypatch: pytest.MonkeyPatch,
        part_kernel: Any,
        removed: bool,
    ) -> None:
        """Peer round 30 PR-LOW-301: the REAL ``write_backup_file`` and the
        page's worker body; an operation inside the writer's guarded pipeline
        (its publish) raises something unforeseen. Its type survives the
        writer's ``unexpected`` translation and cleanup rethrow, is logged
        once at the write boundary, and the partial-file sentence follows
        the removal's outcome."""
        logger, handler = records
        fakes.published(world.store)
        part_kernel.refuse_open = not removed  # the ``.part`` removal fails
        monkeypatch.setattr(backup, "_publish", self._unforeseen(KeyError))
        world.build(logger=logger).on_backup()
        assert handler.lines == ["backup_unexpected detail_code=write error_code=KeyError"]
        line = view.backup_failed_line(view.HopFailed("unexpected", part_may_remain=not removed))
        assert world.screen.message_label.text() == line
        assert line.endswith(view.BACKUP_PART_MAY_REMAIN) is not removed
        assert not any("synthetic" in record for record in handler.lines)
        assert not any(path.suffix == ".csbk" for path in world.published())
        _closed_cleanly(world)

    def test_the_dispatch(self, world: World, records: tuple[logging.Logger, _Records]) -> None:
        logger, handler = records
        screen = world.build(logger=logger)
        screen._run_hop = self._unforeseen(RuntimeError)
        screen.on_backup()
        self._assert_logged_once(world, handler, "dispatch", "RuntimeError")

    def test_a_named_failure_logs_nothing(
        self,
        world: World,
        records: tuple[logging.Logger, _Records],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        logger, handler = records

        def no_memory(*_args: Any, **_kwargs: Any) -> bytes:
            raise MemoryError

        monkeypatch.setattr(backup, "argon2id_derive", no_memory)
        world.build(logger=logger).on_backup()
        assert world.screen.message_label.text() == view.backup_failed_line(
            view.HopFailed("kdf_memory")
        )
        assert handler.lines == []
        _closed_cleanly(world)

    def test_no_logger_logs_nothing_and_still_closes(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(page_module, "new_kdf_params", self._unforeseen(KeyError))
        world.build().on_backup()
        _closed_cleanly(world)


class TestBackUpInTheWindow:
    """The flow against the real ``MainWindow`` gate: the rail, the Settings
    strip and every page are disabled while a hop runs, and enabled again —
    with the success line — once the run ends."""

    def test_the_window_is_disabled_mid_run_and_enabled_after(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from test_ui_screens import _main_window

        root = tmp_path / "w"
        root.mkdir()
        world = World(root)
        fakes.published(world.store)
        hops = Hops(deferred=True)
        window = _main_window(
            tmp_path,
            past_sessions=world.store,
            audit=world.log,
            windows_layer=world.layer,
            past_sessions_passphrase=world.passphrases,
            past_sessions_backup_path=world.choose,
            past_sessions_run_hop=hops,
            config_root=world.config,
        )
        try:
            window.show_page(window.past_sessions_screen)
            window.past_sessions_screen.on_backup()
            assert window.archive_running
            assert not window.tabs.isEnabled() and not window.rail.isEnabled()
            assert not window.settings_strip.isEnabled()
            hops.run_all()
            assert not window.archive_running
            assert window.tabs.isEnabled() and window.rail.isEnabled()
            assert window.past_sessions_screen.message_label.text().startswith(
                "Backup written: "
            )
        finally:
            run = window._archive_run
            if run is not None:
                run.close()
            window.close()
            window.deleteLater()

    def test_a_close_waits_for_a_backup_worker_still_ending(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Review round 27 MED-001: after a run released the gate, its last
        hop's thread can still be ending; a close then is refused (destroying
        a running QThread aborts the process)."""
        from PySide6.QtGui import QCloseEvent

        from scribe_desktop.ui.tasks import TaskThread
        from test_ui_screens import _main_window

        window = _main_window(tmp_path)
        screen = window.past_sessions_screen
        task = TaskThread(lambda: None)
        screen._hops.append(task)
        try:
            assert not window.archive_running and screen.is_busy
            event = QCloseEvent()
            window.closeEvent(event)
            assert not event.isAccepted()
            assert window.statusBar().currentMessage().startswith("Work in progress")
        finally:
            screen._hops.remove(task)
            task.deleteLater()
            window.close()
            window.deleteLater()

    @pytest.mark.parametrize("width", ["150", "narrowest"])
    def test_the_backup_row_fits(self, qapp: Any, tmp_path: Path, width: str) -> None:
        from test_ui_phase_s import _AT_150_CHARS_LINES, _laid_out, _stand_in
        from test_ui_screens import _main_window

        window = _main_window(tmp_path)
        try:
            window.show_page(window.past_sessions_screen)
            if width == "150":
                _laid_out(qapp, window, *_stand_in(window, _AT_150_CHARS_LINES))
            else:
                _laid_out(qapp, window, 960, 640)
            button = window.past_sessions_screen.backup_button
            assert button.isVisible()
            assert button.width() >= button.minimumSizeHint().width()
            left = button.mapTo(window, button.rect().topLeft()).x()
            assert 0 <= left and left + button.width() <= window.width()
        finally:
            window.close()
            window.deleteLater()


# ---------------------------------------------------------------------------
# The lines (Tasks 2.3 and 2.4).
# ---------------------------------------------------------------------------


def _report(
    *,
    entries: int = 2,
    rows: int = 3,
    left_out: LeftOut | None = None,
    not_restorable: int = 0,
) -> BackupReport:
    return BackupReport(
        file_name="ClinikoScribe-backup-2026-10-01.csbk",
        made_at=fakes.NOW,
        entries=entries,
        rows=rows,
        left_out=left_out if left_out is not None else LeftOut(),
        not_restorable=not_restorable,
        file_sha256="0" * 64,
    )


# Every code a backup run can end with: the run codes but the restore's
# ``source_changed``, and hop A's two KDF codes.
_BACKUP_CODES = (backup.RUN_CODES - {"source_changed"}) | {"kdf_memory", "kdf_unavailable"}


class TestTheBackupLines:
    def test_the_two_forms_of_the_success_line(self) -> None:
        assert view.backup_success_line(_report()) == (
            "Backup written: ClinikoScribe-backup-2026-10-01.csbk - 2 sessions, 3 audit "
            "rows. Nothing eligible was left out. Keep the passphrase somewhere other than "
            "the drive."
        )
        left = LeftOut(entries={"damaged": 1, "unreadable": 2}, rows=1)
        assert view.backup_success_line(_report(left_out=left, not_restorable=4)) == (
            "Backup written: ClinikoScribe-backup-2026-10-01.csbk - 2 sessions, 3 audit "
            "rows. Left out: 3 sessions, 1 audit row. Cannot be restored by this version: "
            "4. Keep the passphrase somewhere other than the drive."
        )

    def test_a_zero_part_is_omitted_and_not_restorable_alone_is_not_clean(self) -> None:
        assert view.backup_success_line(_report(not_restorable=1)) == (
            "Backup written: ClinikoScribe-backup-2026-10-01.csbk - 2 sessions, 3 audit "
            "rows. Cannot be restored by this version: 1. Keep the passphrase somewhere "
            "other than the drive."
        )
        assert view.backup_success_line(_report(left_out=LeftOut(rows=2))) == (
            "Backup written: ClinikoScribe-backup-2026-10-01.csbk - 2 sessions, 3 audit "
            "rows. Left out: 2 audit rows. Keep the passphrase somewhere other than the "
            "drive."
        )

    def test_sessions_holding_a_recording_are_said_apart(self) -> None:
        left = LeftOut(entries={"holds_recording": 2})
        assert view.backup_success_line(_report(left_out=left)) == (
            "Backup written: ClinikoScribe-backup-2026-10-01.csbk - 2 sessions, 3 audit "
            "rows. Nothing eligible was left out. 2 sessions are not in a backup because a "
            "kept recording or its key is still present. Keep the passphrase somewhere "
            "other than the drive."
        )

    def test_no_line_gives_a_verdict_or_keep_or_destroy_advice(self) -> None:
        """Decision 0.14: the app reports facts; the rule is the documents'."""
        lines = [
            view.backup_success_line(_report()),
            view.backup_success_line(_report(left_out=LeftOut(rows=1), not_restorable=1)),
            *(view.backup_failed_line(view.HopFailed(code)) for code in _BACKUP_CODES),
        ]
        for line in lines:
            lowered = line.lower()
            for word in ("complete", "safe", "destroy", "delete", "older backup", "keep this"):
                assert word not in lowered, (word, line)

    def test_every_code_a_backup_can_end_with_has_its_own_line(self) -> None:
        lines = {code: view.backup_failed_line(view.HopFailed(code)) for code in _BACKUP_CODES}
        assert len(set(lines.values())) == len(lines)
        assert lines["nothing_to_back_up"] == "Nothing to back up yet."
        assert view.backup_failed_line(view.HopFailed("no-such-code")) == lines["unexpected"]

    def test_nothing_could_be_read_gives_its_counts(self) -> None:
        failure = view.HopFailed(
            "nothing_could_be_read",
            left_out=LeftOut(entries={"damaged": 1, "holds_recording": 1}, rows=2),
        )
        assert view.backup_failed_line(failure) == (
            "The backup was not made: no session or audit row could be read. Left out: 1 "
            "session, 2 audit rows. 1 session is not in a backup because a kept recording "
            "or its key is still present."
        )

    def test_the_failure_of_a_hop_is_a_closed_code(self) -> None:
        assert view.hop_failure(BackupRunError("too_large")) == view.HopFailed("too_large")
        assert view.hop_failure(backup.BackupFormatError("kdf_memory")) == view.HopFailed(
            "kdf_memory"
        )
        # Peer round 29 PR-LOW-202: anything else is ``unexpected`` with its
        # TYPE name only (never the text), and the line is the fixed one.
        unforeseen = view.hop_failure(RuntimeError("C:\\a path"))
        assert unforeseen == view.HopFailed("unexpected", error_type="RuntimeError")
        assert view.backup_failed_line(unforeseen) == view.backup_failed_line(
            view.HopFailed("unexpected")
        )
        assert "path" not in repr(unforeseen)
        named = view.hop_failure(BackupRunError("write_failed", part_may_remain=True))
        assert named.error_type is None

    def test_the_proposed_name_is_the_apps_own(self) -> None:
        assert view.backup_default_name(fakes.NOW, UTC) == (
            "ClinikoScribe-backup-2026-10-01.csbk"
        )


class TestTheChangedWording:
    """Task 2.4 (D10): the strings a backup changes, exactly."""

    def test_the_delete_lines(self) -> None:
        assert view.DELETE_DONE == "Session deleted from Past sessions."
        assert "An earlier backup may still hold them - the downtime procedure says when " \
            "older backups may be destroyed." in view.DELETE_CONFIRM_MESSAGE
        assert "cannot be recovered" not in view.DELETE_CONFIRM_MESSAGE

    def test_the_shorter_retention_confirmation(self) -> None:
        assert view.retention_confirm_text(2557) == (
            "Keep past sessions for only 7 years? Kept sessions older than that are deleted "
            "now from Past sessions; one whose completion date cannot be read, or whose "
            "deletion fails, is kept and counted. An earlier backup may still hold them."
        )

    def test_the_retention_warning_names_the_backup(self) -> None:
        assert "makes no backup of its own" not in view.RETENTION_WARNING
        assert (
            "Clinic Scribe keeps it, encrypted, in this Windows login's data folder, and in "
            "any passphrase-protected backup you make onto a drive attached to this "
            "computer - a backup is never sent anywhere, and never holds a kept development "
            "recording or a session that still holds one."
        ) in view.RETENTION_WARNING

    def test_the_delete_failed_line_is_unchanged(self) -> None:
        assert view.delete_failed_line(RuntimeError("x")) == (
            "Delete failed: an unexpected problem on this computer stopped it. Nothing else "
            "changed - try again."
        )

    def test_the_admission_lines(self) -> None:
        assert view.ARCHIVE_LIVE_LINE == "Finish or discard the current recording first."
        assert view.ARCHIVE_RECOVERY_LINE == (
            "Review or discard the recordings on the Recovery page first."
        )
        assert view.ARCHIVE_ENROLMENT_LINE == (
            "Voice enrolment is running - wait for it to finish, or Stop it, first."
        )
        assert view.ARCHIVE_BUSY_LINE == "Wait for the current work to finish."
        assert view.ARCHIVE_CLOSE_LINE == (
            "A backup or restore is running - wait for it to finish before closing."
        )


# ---------------------------------------------------------------------------
# The backup reminder (Task 2.4).
# ---------------------------------------------------------------------------

_DAY = timedelta(days=1)


class TestTheBackupStatusLine:
    def test_nothing_on_the_first_day(self) -> None:
        now = fakes.NOW
        assert view.backup_status_line(None, [now - _DAY], now) is None

    def test_with_no_date_it_shows_from_the_oldest_after_seven_days(self) -> None:
        now = fakes.NOW
        dates = [now - 7 * _DAY, now - _DAY]
        assert view.backup_status_line(None, dates, now) == (
            "No backup date recorded - 2 sessions kept."
        )
        assert view.backup_status_line(None, [now - 7 * _DAY + timedelta(seconds=1)], now) is None

    def test_with_a_date_it_counts_only_later_sessions(self) -> None:
        now = fakes.NOW
        last = now - 8 * _DAY
        dates = [now - 9 * _DAY, now - 2 * _DAY, now - _DAY]
        assert view.backup_status_line(last, dates, now, zone=UTC) == (
            "Last backup 2026-09-23 - 2 sessions kept since."
        )

    def test_the_seven_day_boundary(self) -> None:
        now = fakes.NOW
        dates = [now - _DAY]
        assert view.backup_status_line(now - 7 * _DAY, dates, now, zone=UTC) == (
            "Last backup 2026-09-24 - 1 session kept since."
        )
        assert view.backup_status_line(now - 6 * _DAY, dates, now, zone=UTC) is None

    def test_nothing_since_the_last_backup_shows_nothing(self) -> None:
        now = fakes.NOW
        assert view.backup_status_line(now - 30 * _DAY, [now - 40 * _DAY], now) is None
        assert view.backup_status_line(None, [], now) is None

    def test_the_page_shows_it_from_its_listing_and_skips_an_unreadable_entry(
        self, world: World
    ) -> None:
        fakes.published(world.store)
        unreadable = fakes.published(world.store)
        (world.store.root / unreadable / KEY_FILENAME).write_bytes(b"not a key")
        world.clock = fakes.NOW + 8 * _DAY
        screen = world.build()
        assert not any("backup" in line.lower() for line in screen.status_lines())
        screen.refresh()  # the reminder follows the listing
        assert "No backup date recorded - 1 session kept." in screen.status_lines()
        screen.on_left()
        assert "No backup date recorded - 1 session kept." not in screen.status_lines()

    def test_a_backup_clears_the_reminder(self, world: World) -> None:
        fakes.published(world.store)
        world.clock = fakes.NOW + 8 * _DAY
        screen = world.build()
        screen.refresh()
        assert "No backup date recorded - 1 session kept." in screen.status_lines()
        screen.on_backup()
        assert screen.message_label.text().startswith("Backup written: ")
        assert not any("backup" in line.lower() for line in screen.status_lines())
        assert _settings(world).last_backup_at == fakes.NOW + 8 * _DAY

    def test_an_unreadable_settings_file_reads_as_no_date(self, world: World) -> None:
        fakes.published(world.store)
        world.config.mkdir()
        (world.config / "backup.json").write_text("{not json", encoding="utf-8")
        world.clock = fakes.NOW + 8 * _DAY
        screen = world.build()
        screen.refresh()
        assert "No backup date recorded - 1 session kept." in screen.status_lines()


def test_the_backup_file_name_prefix_lives_once() -> None:
    """The proposed name is built from the container's one prefix (D2)."""
    assert view.backup_default_name(datetime(2026, 1, 2, tzinfo=UTC), UTC).startswith(
        backup.BACKUP_FILENAME_PREFIX
    )
