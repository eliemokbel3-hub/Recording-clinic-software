"""Pilot plan Task 1.1 (D1-D3): the pilot setting ``config\\pilot.json``
(``note_config.PilotSettings`` / ``read_pilot_settings`` — absent is shadow
OFF, present but unusable is shadow ON and named), the Status tab's "Shadow
mode (pilot)" checkbox in both channels, and its app-version line.

Every file is under ``tmp_path`` or the conftest's pinned pilot root
(``pinned_pilot_root``, Constraint 9)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from conftest import REAL_PILOT_SETTINGS_ROOT, bounded_read_spy, use_channel
from scribe_desktop import __version__, note_config
from scribe_desktop.install_layout import Channel
from scribe_desktop.note_config import (
    MAX_PILOT_SETTINGS_BYTES,
    PILOT_SETTINGS_FILENAME,
    NoteConfigError,
    PilotSettings,
    PilotSettingsRead,
    read_pilot_settings,
    save_pilot_settings,
    shadow_mode_on,
)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

OFF = PilotSettingsRead(shadow_mode=False, unreadable=False)
ON = PilotSettingsRead(shadow_mode=True, unreadable=False)
UNREADABLE = PilotSettingsRead(shadow_mode=True, unreadable=True)


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _write(root: Path, blob: bytes | str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / PILOT_SETTINGS_FILENAME
    path.write_bytes(blob.encode("utf-8") if isinstance(blob, str) else blob)
    return path


class TestTheSettingsFile:
    def test_an_absent_file_is_shadow_off(self, tmp_path: Path) -> None:
        assert read_pilot_settings(tmp_path) == OFF
        assert shadow_mode_on(tmp_path) is False

    def test_valid_on_and_valid_off(self, tmp_path: Path) -> None:
        path = save_pilot_settings(PilotSettings(shadow_mode=True), config_root=tmp_path)
        assert path == tmp_path / "pilot.json"
        assert json.loads(path.read_text(encoding="utf-8")) == {
            "schema_version": 1,
            "shadow_mode": True,
        }
        assert read_pilot_settings(tmp_path) == ON
        assert shadow_mode_on(tmp_path) is True
        save_pilot_settings(PilotSettings(shadow_mode=False), config_root=tmp_path)
        assert read_pilot_settings(tmp_path) == OFF

    @pytest.mark.parametrize(
        "blob",
        [
            "{not json",
            "",
            '{"schema_version": 1, "shadow_mode": false, "extra": 1}',
            '{"schema_version": 2, "shadow_mode": false}',
            '{"schema_version": 1, "shadow_mode": 0}',
            '{"schema_version": 1, "shadow_mode": "false"}',
            "[false]",
            "null",  # review round 22
            b"\xff\xfe\x00",
            # Peer round 9 PR-HIGH-B02: present but naming no setting.
            "{}",
            '{"schema_version": 1}',
        ],
    )
    def test_a_file_it_cannot_use_is_shadow_on_and_named(
        self, tmp_path: Path, blob: bytes | str
    ) -> None:
        """D3: a corrupt file never silently re-enables Copy and Write."""
        _write(tmp_path, blob)
        assert read_pilot_settings(tmp_path) == UNREADABLE
        assert shadow_mode_on(tmp_path) is True

    def test_an_oversized_file_is_shadow_on_and_read_bounded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        body = '{"schema_version": 1, "shadow_mode": false}'
        _write(tmp_path, body + " " * MAX_PILOT_SETTINGS_BYTES)
        sizes = bounded_read_spy(monkeypatch, PILOT_SETTINGS_FILENAME)
        assert read_pilot_settings(tmp_path) == UNREADABLE
        assert sizes == [MAX_PILOT_SETTINGS_BYTES + 1]

    def test_a_file_that_cannot_be_opened_is_shadow_on(self, tmp_path: Path) -> None:
        (tmp_path / PILOT_SETTINGS_FILENAME).mkdir(parents=True)  # a folder: open fails
        assert read_pilot_settings(tmp_path) == UNREADABLE

    def test_a_failed_save_raises_by_type(self, tmp_path: Path) -> None:
        blocker = tmp_path / "config"
        blocker.write_bytes(b"")  # a file where the folder should be
        with pytest.raises(NoteConfigError):
            save_pilot_settings(PilotSettings(shadow_mode=True), config_root=blocker)


class TestTheDefaultRoot:
    def test_the_real_resolver_is_the_config_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert REAL_PILOT_SETTINGS_ROOT() == note_config.default_config_root()
        assert REAL_PILOT_SETTINGS_ROOT() == tmp_path / "ClinikoScribe" / "config"

    def test_every_test_reads_an_empty_pinned_root(self, pinned_pilot_root: Path) -> None:
        """Constraint 9: with no root passed, the read lands in the test's
        own empty folder (shadow off), never the host's config — and a
        save lands there too, in both directions."""
        assert note_config.pilot_settings_root() == pinned_pilot_root
        assert list(pinned_pilot_root.iterdir()) == []
        assert read_pilot_settings() == OFF
        save_pilot_settings(PilotSettings(shadow_mode=True))
        assert (pinned_pilot_root / PILOT_SETTINGS_FILENAME).is_file()
        assert read_pilot_settings() == ON
        assert shadow_mode_on() is True


def _panel(
    monkeypatch: pytest.MonkeyPatch,
    config_root: Path | None,
    which: Channel = "production",
    **kwargs: Any,
) -> Any:
    from scribe_desktop.status import RegistrationStatus
    from scribe_desktop.ui import main_window

    use_channel(monkeypatch, which)
    # Never the real registry (C6).
    monkeypatch.setattr(
        main_window,
        "read_registration_status",
        lambda layer: RegistrationStatus(None, manifest_exists=False, launcher_exists=False),
    )
    return main_window.StatusPanel(config_root=config_root, **kwargs)


class TestTheStatusCheckbox:
    @pytest.mark.parametrize("which", ["production", "dev"])
    def test_both_channels_show_it_off_by_default_and_save_a_tick(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, which: Channel
    ) -> None:
        from scribe_desktop.ui.main_window import SHADOW_MODE_CHECKBOX_TEXT

        config = tmp_path / "config"
        panel = _panel(monkeypatch, config, which)
        checkbox = panel.shadow_checkbox
        assert checkbox.text() == SHADOW_MODE_CHECKBOX_TEXT == "Shadow mode (pilot)"
        assert not checkbox.isChecked()
        assert panel.shadow_label.isHidden()
        changed: list[bool] = []
        panel.shadow_mode_changed.connect(lambda: changed.append(True))
        checkbox.setChecked(True)
        assert read_pilot_settings(config) == ON
        checkbox.setChecked(False)
        assert read_pilot_settings(config) == OFF
        assert changed == [True, True]
        panel.close()

    def test_it_shows_a_saved_tick(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config = tmp_path / "config"
        _write(config, PilotSettings(shadow_mode=True).to_bytes())
        panel = _panel(monkeypatch, config)
        assert panel.shadow_checkbox.isChecked()
        assert panel.shadow_label.isHidden()
        panel.close()

    def test_an_unreadable_file_shows_the_box_ticked_and_names_it(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.ui.main_window import SHADOW_MODE_UNREADABLE

        config = tmp_path / "config"
        _write(config, "{garbled")
        panel = _panel(monkeypatch, config)
        assert panel.shadow_checkbox.isChecked()
        assert panel.shadow_label.text() == SHADOW_MODE_UNREADABLE
        assert not panel.shadow_label.isHidden()
        # Unticking saves a readable file: off, and the line goes.
        panel.shadow_checkbox.setChecked(False)
        assert read_pilot_settings(config) == OFF
        assert panel.shadow_label.isHidden()
        panel.close()

    def test_a_failed_save_puts_the_box_back_and_says_so(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.ui import main_window
        from scribe_desktop.ui.main_window import SHADOW_MODE_SAVE_FAILED

        config = tmp_path / "config"

        def refused(settings: PilotSettings, *, config_root: Path | None) -> Path:
            raise NoteConfigError("refused")

        panel = _panel(monkeypatch, config)
        monkeypatch.setattr(main_window, "save_pilot_settings", refused)
        changed: list[bool] = []
        panel.shadow_mode_changed.connect(lambda: changed.append(True))
        panel.shadow_checkbox.setChecked(True)
        assert not panel.shadow_checkbox.isChecked()
        assert panel.shadow_label.text() == SHADOW_MODE_SAVE_FAILED
        assert not panel.shadow_label.isHidden()
        assert changed == [True]
        assert read_pilot_settings(config) == OFF
        panel.close()

    def test_a_save_that_landed_then_failed_shows_the_saved_tick(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.ui import main_window

        config = tmp_path / "config"

        def landed_then_failed(settings: PilotSettings, *, config_root: Path | None) -> Path:
            save_pilot_settings(settings, config_root=config_root)
            raise NoteConfigError("failed after the replace")

        panel = _panel(monkeypatch, config)
        monkeypatch.setattr(main_window, "save_pilot_settings", landed_then_failed)
        panel.shadow_checkbox.setChecked(True)
        assert panel.shadow_checkbox.isChecked()
        assert read_pilot_settings(config) == ON
        panel.close()

    def test_no_root_reads_the_pinned_root_both_ways(
        self, qapp: Any, pinned_pilot_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Constraint 9: a window built with no config root reads the
        conftest's empty folder — off — and a ticked file written there."""
        panel = _panel(monkeypatch, None)
        assert not panel.shadow_checkbox.isChecked()
        panel.close()
        _write(pinned_pilot_root, PilotSettings(shadow_mode=True).to_bytes())
        panel = _panel(monkeypatch, None)
        assert panel.shadow_checkbox.isChecked()
        panel.close()


class TestTheVersionLine:
    def test_it_shows_the_app_version(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.ui.main_window import version_line

        panel = _panel(monkeypatch, tmp_path)
        assert panel.version_label.text() == version_line(__version__)
        assert panel.version_label.text() == f"Clinic Scribe version {__version__}"
        panel.close()

    def test_the_version_is_a_seam(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        panel = _panel(monkeypatch, tmp_path, app_version="9.8.7")
        assert panel.version_label.text() == "Clinic Scribe version 9.8.7"
        panel.close()


# ---------------------------------------------------------------------------
# Tasks 1.2 and 1.7: Start takes the setting at the click; the Session tab says so.
# ---------------------------------------------------------------------------


def _tracking_controller() -> Any:
    """``FakeController`` whose Start makes the tracked session (of the mode
    it was given), as the real controller does."""
    from scribe_desktop.session import RecordingSession, SessionState
    from scribe_desktop.session_mode import SessionMode
    from test_ui_screens import FakeController

    class _Tracking(FakeController):
        def start(self, device_id: int, **kwargs: Any) -> Any:
            super().start(device_id, **kwargs)
            mode = kwargs.get("mode", SessionMode.NORMAL)
            self.session_value = RecordingSession(
                consent=kwargs["consent"],
                encounter_context=kwargs.get("context"),
                mode=mode,
            ).with_state(SessionState.RECORDING)
            return self.session_value

        def finish(self) -> Any:
            super().finish()
            assert self.session_value is not None
            self.session_value = self.session_value.with_state(SessionState.PROCESSING)
            return self.session_value

    return _Tracking()


def _session_screen(controller: Any, setting: dict[str, bool]) -> Any:
    from scribe_desktop.ui.session_screen import SessionScreen

    return SessionScreen(
        controller,
        device_provider=lambda: 7,
        transcriber_factory=lambda: (lambda _d, _c: None),  # type: ignore[arg-type,return-value]
        shadow_mode=lambda: setting["on"],
    )


def _start(screen: Any) -> None:
    screen.consent_checkbox.setChecked(True)
    screen.start_button.click()


class TestTheSessionTab:
    def test_the_line_follows_the_setting(self, qapp: Any) -> None:
        from scribe_desktop.ui import models

        setting = {"on": False}
        screen = _session_screen(_tracking_controller(), setting)
        assert screen.shadow_label.isHidden()
        setting["on"] = True
        screen.refresh()
        assert not screen.shadow_label.isHidden()
        assert screen.shadow_label.text() == models.SHADOW_SETTING_LINE
        setting["on"] = False
        screen.refresh()
        assert screen.shadow_label.isHidden()
        screen.deleteLater()

    def test_a_start_takes_the_setting_at_the_click_and_keeps_it(self, qapp: Any) -> None:
        """D1: the mode is fixed at Start; turning the setting off during
        the recording changes nothing, and the recording stays labelled."""
        from scribe_desktop.session_mode import SessionMode
        from scribe_desktop.ui import models

        controller = _tracking_controller()
        setting = {"on": True}
        screen = _session_screen(controller, setting)
        _start(screen)
        assert controller.started_modes == [SessionMode.SHADOW]
        assert controller.session.mode is SessionMode.SHADOW
        assert screen.shadow_label.text() == "\n".join(
            (models.SHADOW_RECORDING_LINE, models.SHADOW_SETTING_LINE)
        )
        setting["on"] = False  # turned off mid-recording
        screen.refresh()
        assert controller.session.mode is SessionMode.SHADOW
        assert screen.shadow_label.text() == models.SHADOW_RECORDING_LINE
        assert not screen.shadow_label.isHidden()
        controller.finish()  # the recording goes on to processing, still shadow
        screen.refresh()
        assert controller.session.mode is SessionMode.SHADOW
        assert screen.shadow_label.text() == models.SHADOW_RECORDING_LINE
        screen.deleteLater()

    def test_a_normal_start_is_normal_and_unlabelled(self, qapp: Any) -> None:
        from scribe_desktop.session_mode import SessionMode
        from scribe_desktop.ui import models

        controller = _tracking_controller()
        setting = {"on": False}
        screen = _session_screen(controller, setting)
        _start(screen)
        assert controller.started_modes == [SessionMode.NORMAL]
        assert screen.shadow_label.isHidden()
        setting["on"] = True  # turned on mid-recording: only NEW recordings
        screen.refresh()
        assert controller.session.mode is SessionMode.NORMAL
        assert screen.shadow_label.text() == models.SHADOW_SETTING_LINE
        screen.deleteLater()

    @pytest.mark.parametrize("on", [True, False])
    def test_a_chrome_start_takes_the_setting_too(self, qapp: Any, on: bool) -> None:
        """Round 7 LOW-002: the side panel's linked Start (``start_linked``)
        takes the setting at its click exactly as the desktop Start does."""
        from scribe_desktop.encounter import linked_consent
        from scribe_desktop.session_mode import SessionMode
        from test_ui_screens import _linked_context

        controller = _tracking_controller()
        screen = _session_screen(controller, {"on": on})
        context = _linked_context()
        assert screen.start_linked(linked_consent(context), context) is True
        expected = SessionMode.SHADOW if on else SessionMode.NORMAL
        assert controller.started_modes == [expected]
        assert controller.session.mode is expected
        assert controller.session.encounter_context == context
        assert screen.shadow_label.isHidden() is (not on)
        screen.deleteLater()

    @pytest.mark.parametrize("blob", ["{garbled", "{}", '{"schema_version": 1}'])
    def test_an_unreadable_setting_starts_a_shadow_recording(
        self, qapp: Any, tmp_path: Path, blob: str
    ) -> None:
        """D3 through the real reader: a garbled file, or one naming no
        setting (peer round 9 PR-HIGH-B02), is shadow ON."""
        from scribe_desktop.session_mode import SessionMode
        from scribe_desktop.ui.session_screen import SessionScreen

        _write(tmp_path, blob)
        controller = _tracking_controller()
        screen = SessionScreen(
            controller,
            device_provider=lambda: 7,
            shadow_mode=lambda: shadow_mode_on(tmp_path),
        )
        _start(screen)
        assert controller.started_modes == [SessionMode.SHADOW]
        screen.deleteLater()

    def test_the_default_reads_the_pinned_root(self, qapp: Any, pinned_pilot_root: Path) -> None:
        """Constraint 9: a screen built without the seam reads the conftest's
        empty folder (normal), then a ticked file written there (shadow)."""
        from scribe_desktop.session_mode import SessionMode
        from scribe_desktop.ui.session_screen import SessionScreen

        controller = _tracking_controller()
        screen = SessionScreen(controller, device_provider=lambda: 7)
        _start(screen)
        assert controller.started_modes == [SessionMode.NORMAL]
        screen.deleteLater()
        _write(pinned_pilot_root, PilotSettings(shadow_mode=True).to_bytes())
        controller = _tracking_controller()
        screen = SessionScreen(controller, device_provider=lambda: 7)
        _start(screen)
        assert controller.started_modes == [SessionMode.SHADOW]
        screen.deleteLater()

    def test_the_status_tick_refreshes_the_session_tab(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The window wires ``shadow_mode_changed`` to the Session tab, so
        the line appears and goes at the tick."""
        from scribe_desktop.status import RegistrationStatus
        from scribe_desktop.ui import main_window, models
        from test_ui_screens import _main_window

        monkeypatch.setattr(
            main_window,
            "read_registration_status",
            lambda layer: RegistrationStatus(None, manifest_exists=False, launcher_exists=False),
        )
        window = _main_window(tmp_path, _tracking_controller())
        label = window.session_screen.shadow_label
        assert label.isHidden()
        window.status_panel.shadow_checkbox.setChecked(True)
        assert not label.isHidden() and label.text() == models.SHADOW_SETTING_LINE
        window.status_panel.shadow_checkbox.setChecked(False)
        assert label.isHidden()
        window.close()
