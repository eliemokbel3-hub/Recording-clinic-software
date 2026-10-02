"""Installation plan D4 (Task 1.6): the developer build's Cliniko write
guard — ``config\\dev.json`` (``note_config.DevSettings``: the
``PastSessionSettings`` pattern, except that a file it cannot use reads as
writes OFF), ``note_config.dev_writes_allowed`` (production never reads the
file), the Write button's state (``ui.models.write_control``) and the
dev-only Status-tab checkbox. The refusal itself is pinned in
``test_draft_write.py`` (``TestTheDevBuildWriteGuard``) and the click's
audit row in ``test_ui_encounter.py``.

Every file is under ``tmp_path`` (C6)."""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
from typing import Any

import pytest

from conftest import bounded_read_spy, use_channel
from scribe_desktop import note_config
from scribe_desktop.draft_write import WriteRecordStatus
from scribe_desktop.install_layout import Channel
from scribe_desktop.note_config import (
    DEV_SETTINGS_FILENAME,
    MAX_DEV_SETTINGS_BYTES,
    DevSettings,
    NoteConfigError,
    dev_writes_allowed,
    load_dev_settings,
    save_dev_settings,
)
from scribe_desktop.ui import models

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _write(root: Path, blob: bytes | str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / DEV_SETTINGS_FILENAME
    path.write_bytes(blob.encode("utf-8") if isinstance(blob, str) else blob)
    return path


class TestTheSettingsFile:
    def test_an_absent_file_is_writes_off(self, tmp_path: Path) -> None:
        assert load_dev_settings(tmp_path) == DevSettings()
        assert DevSettings().allow_cliniko_writes is False

    def test_a_saved_setting_round_trips(self, tmp_path: Path) -> None:
        path = save_dev_settings(DevSettings(allow_cliniko_writes=True), config_root=tmp_path)
        assert path == tmp_path / "dev.json"
        assert json.loads(path.read_text(encoding="utf-8")) == {
            "schema_version": 1,
            "allow_cliniko_writes": True,
        }
        assert load_dev_settings(tmp_path).allow_cliniko_writes is True

    @pytest.mark.parametrize(
        "blob",
        [
            "{not json",
            "",
            '{"schema_version": 1, "allow_cliniko_writes": true, "extra": 1}',
            '{"schema_version": 2, "allow_cliniko_writes": true}',
            '{"schema_version": 1, "allow_cliniko_writes": 1}',
            '{"schema_version": 1, "allow_cliniko_writes": "true"}',
            "[true]",
            b"\xff\xfe\x00",
        ],
    )
    def test_a_file_it_cannot_use_is_writes_off(self, tmp_path: Path, blob: bytes | str) -> None:
        _write(tmp_path, blob)
        assert load_dev_settings(tmp_path) == DevSettings()

    def test_an_oversized_file_is_writes_off_and_read_bounded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        body = '{"schema_version": 1, "allow_cliniko_writes": true}'
        _write(tmp_path, body + " " * MAX_DEV_SETTINGS_BYTES)
        sizes = bounded_read_spy(monkeypatch, DEV_SETTINGS_FILENAME)
        assert load_dev_settings(tmp_path) == DevSettings()
        assert sizes == [MAX_DEV_SETTINGS_BYTES + 1]

    def test_an_unreadable_file_is_writes_off(self, tmp_path: Path) -> None:
        (tmp_path / DEV_SETTINGS_FILENAME).mkdir(parents=True)  # a folder: open fails
        assert load_dev_settings(tmp_path) == DevSettings()

    def test_a_failed_save_raises_by_type(self, tmp_path: Path) -> None:
        blocker = tmp_path / "config"
        blocker.write_bytes(b"")  # a file where the folder should be
        with pytest.raises(NoteConfigError):
            save_dev_settings(DevSettings(allow_cliniko_writes=True), config_root=blocker)

    def test_the_default_root_is_the_dev_data_folders_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        use_channel(monkeypatch, "dev")
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        path = save_dev_settings(DevSettings(allow_cliniko_writes=True))
        assert path == tmp_path / "ClinikoScribe-dev" / "config" / "dev.json"
        assert not (tmp_path / "ClinikoScribe").exists()


class TestDevWritesAllowed:
    def test_production_never_reads_the_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write(tmp_path, DevSettings(allow_cliniko_writes=True).to_bytes())
        monkeypatch.setattr(
            note_config, "load_dev_settings", lambda *_a, **_k: pytest.fail("read in production")
        )
        assert dev_writes_allowed(tmp_path) is False

    def test_dev_reads_the_setting(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        use_channel(monkeypatch, "dev")
        assert dev_writes_allowed(tmp_path) is False
        _write(tmp_path, DevSettings(allow_cliniko_writes=True).to_bytes())
        assert dev_writes_allowed(tmp_path) is True
        _write(tmp_path, "{garbled")
        assert dev_writes_allowed(tmp_path) is False


class TestTheWriteButton:
    _BINDING = models.WriteBinding("s", True)

    def _control(self, **overrides: object) -> models.WriteControl:
        fields: dict[str, object] = {
            "saved": True,
            "binding": self._BINDING,
            "mock": False,
            "status": WriteRecordStatus("none"),
            "channel": "dev",
            "allow_dev_writes": False,
        }
        fields.update(overrides)
        return models.write_control(**fields)  # type: ignore[arg-type]

    def test_dev_with_writes_off_disables_write_with_the_line(self) -> None:
        line = models.write_line("dev_build_writes_off")
        assert self._control() == models.WriteControl(False, line)
        assert self._control(status=WriteRecordStatus("refused")) == models.WriteControl(
            False, line
        )

    def test_an_open_attempt_prefixes_it(self) -> None:
        """A write allowed, left open, then the setting unticked: the line
        invites Copy, so it carries the ``write_uncertain`` warning
        (PR-MED-017) instead of ``unknown``'s enabled button."""
        prefixed = models.write_line("dev_build_writes_off", uncertain=True)
        assert prefixed.startswith(models.WRITE_LINES["write_uncertain"] + " ")
        for outcome in ("attempting", "unknown"):
            status = WriteRecordStatus(outcome)  # type: ignore[arg-type]
            assert self._control(status=status) == models.WriteControl(False, prefixed)

    def test_the_write_records_own_lines_come_first(self) -> None:
        """An earlier write's line keeps its precedence over the dev guard,
        exactly as in production (``draft_write.refuse_before_read``)."""
        for status in (
            None,
            WriteRecordStatus("unreadable"),
            WriteRecordStatus("written", note_matches=True),
            WriteRecordStatus("written"),
        ):
            production = self._control(status=status, channel="production")
            assert not production.ready and production.line is not None
            assert self._control(status=status) == production

    def test_dev_with_writes_allowed_and_production_are_ready(self) -> None:
        assert self._control(allow_dev_writes=True) == models.WriteControl(True)
        for allow in (False, True):
            assert self._control(channel="production", allow_dev_writes=allow) == (
                models.WriteControl(True)
            )

    def test_the_earlier_reasons_come_first(self) -> None:
        assert self._control(saved=False).line == models.write_line("not_saved")
        unlinked = models.WriteBinding("s", False)
        assert self._control(binding=unlinked).line == models.write_line("unlinked")
        assert self._control(mock=True).line == models.write_line("mock_note")


_SRC = Path(__file__).resolve().parents[1] / "src" / "scribe_desktop"


def _prepared_write_builders(source: str) -> list[str]:
    """The function each ``PreparedWrite(...)`` call in ``source`` sits in
    (``<module>`` at module level)."""
    found: list[str] = []

    def visit(node: ast.AST, owner: str) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            owner = node.name
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if name == "PreparedWrite":
                found.append(owner)
        for child in ast.iter_child_nodes(node):
            visit(child, owner)

    visit(ast.parse(source), "<module>")
    return found


def test_only_prepare_write_builds_a_prepared_write() -> None:
    """Round 10 LOW-005 (defence in depth): hop 2 (``write_for_click`` →
    ``send_write``, the one PATCH) takes a ``PreparedWrite`` and does not
    re-check the dev guard; it holds because ``prepare_write`` — which runs
    ``refuse_before_read`` first — is the only place one is built. A new
    builder anywhere in ``src`` fails here and must carry the guard."""
    builders = {
        f"{path.relative_to(_SRC).as_posix()}:{owner}"
        for path in sorted(_SRC.rglob("*.py"))
        for owner in _prepared_write_builders(path.read_text(encoding="utf-8"))
    }
    assert builders == {"draft_write.py:prepare_write"}
    assert _prepared_write_builders("def f():\n    return dw.PreparedWrite(a)\n") == ["f"]


def _panel(monkeypatch: pytest.MonkeyPatch, config_root: Path, which: Channel) -> Any:
    from scribe_desktop.status import RegistrationStatus
    from scribe_desktop.ui import main_window

    use_channel(monkeypatch, which)
    # Never the real registry (C6).
    monkeypatch.setattr(
        main_window,
        "read_registration_status",
        lambda layer: RegistrationStatus(None, manifest_exists=False, launcher_exists=False),
    )
    return main_window.StatusPanel(config_root=config_root)


class TestTheStatusCheckbox:
    def test_production_has_no_checkbox_and_reads_nothing(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.ui import main_window

        monkeypatch.setattr(
            main_window, "load_dev_settings", lambda *_a, **_k: pytest.fail("read in production")
        )
        panel = _panel(monkeypatch, tmp_path / "config", "production")
        assert panel.dev_writes_checkbox is None
        panel.close()

    def test_dev_shows_it_off_by_default_and_saves_a_tick(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.ui.main_window import DEV_WRITES_CHECKBOX_TEXT

        config = tmp_path / "config"
        panel = _panel(monkeypatch, config, "dev")
        checkbox = panel.dev_writes_checkbox
        assert checkbox is not None
        assert checkbox.text() == DEV_WRITES_CHECKBOX_TEXT
        assert DEV_WRITES_CHECKBOX_TEXT == "Allow Cliniko writes from this developer build"
        assert not checkbox.isChecked()
        changed: list[bool] = []
        panel.dev_writes_changed.connect(lambda: changed.append(True))
        checkbox.setChecked(True)
        assert load_dev_settings(config).allow_cliniko_writes is True
        assert dev_writes_allowed(config) is True
        checkbox.setChecked(False)
        assert load_dev_settings(config).allow_cliniko_writes is False
        assert changed == [True, True]
        panel.close()

    def test_dev_shows_a_saved_tick(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config = tmp_path / "config"
        _write(config, DevSettings(allow_cliniko_writes=True).to_bytes())
        panel = _panel(monkeypatch, config, "dev")
        assert panel.dev_writes_checkbox is not None
        assert panel.dev_writes_checkbox.isChecked()
        panel.close()

    def test_a_failed_save_puts_the_box_back_and_says_so(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.ui.main_window import DEV_WRITES_SAVE_FAILED

        blocker = tmp_path / "config"
        blocker.write_bytes(b"")  # a file where the config folder should be
        panel = _panel(monkeypatch, blocker, "dev")
        checkbox = panel.dev_writes_checkbox
        assert checkbox is not None
        changed: list[bool] = []
        panel.dev_writes_changed.connect(lambda: changed.append(True))
        checkbox.setChecked(True)
        assert not checkbox.isChecked()
        assert panel.dev_writes_label.text() == DEV_WRITES_SAVE_FAILED
        assert not panel.dev_writes_label.isHidden()
        assert changed == [True]  # the Write button re-reads the setting
        assert dev_writes_allowed(blocker) is False
        panel.close()

    def test_a_save_that_landed_then_failed_shows_the_saved_tick(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The box follows the file, not the click: a failure after the
        replace landed leaves the tick shown, as the Write button sees it."""
        from scribe_desktop.ui import main_window

        config = tmp_path / "config"

        def landed_then_failed(settings: DevSettings, *, config_root: Path | None) -> Path:
            save_dev_settings(settings, config_root=config_root)
            raise NoteConfigError("failed after the replace")

        panel = _panel(monkeypatch, config, "dev")
        monkeypatch.setattr(main_window, "save_dev_settings", landed_then_failed)
        checkbox = panel.dev_writes_checkbox
        assert checkbox is not None
        changed: list[bool] = []
        panel.dev_writes_changed.connect(lambda: changed.append(True))
        checkbox.setChecked(True)
        assert checkbox.isChecked()
        assert dev_writes_allowed(config) is True
        assert not panel.dev_writes_label.isHidden()
        assert changed == [True]
        panel.close()
