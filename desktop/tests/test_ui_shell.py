"""UI refresh plan Phase 3 (D4, D5, D12; Tasks 3.1-3.5): the window's shell.

The rail, the header strip and the Settings strip sit outside the screens and
drive the one ``QTabWidget`` (its tab bar hidden) through ``show_page`` →
``setCurrentWidget``, so ``_on_tab_changed``'s identity rule keeps working.
These tests pin the navigation (a rail click lands on its page; a Settings
page lights no entry and shows the strip), the REC / PAUSED cue and its
survival of a status-bar message, the header's Chrome line and its
withholding on Past sessions, and the code-drawn icons (non-empty and
non-uniform at both scales, tinted by the colour given).

Offscreen Qt against the fakes of ``test_ui_screens.py``; synthetic data
only. Every window is built here and closed here; the theme is never
re-applied to the whole application (Phase 1's suite-time lesson) — the rail's
re-tint is driven through ``theme.theme_bus()`` alone."""

from __future__ import annotations

import ast
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import scribe_desktop  # noqa: E402
import test_ui_bridge as bridge_tests  # noqa: E402
from scribe_desktop.session import SessionState  # noqa: E402
from scribe_desktop.ui import icons, models, shell, theme  # noqa: E402
from test_ui_screens import FakeController, _main_window, _ps_entry  # noqa: E402

PACKAGE = Path(scribe_desktop.__file__).resolve().parent
_EVERYDAY_TITLES = ["Record", "Review", "Past sessions", "Recovery"]
_SETTINGS_TITLES = ["Microphone", "Practitioner", "Clinics", "Status"]


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _close(window: Any) -> None:
    """Close and delete a window this module built, once its worker threads
    are done (a running ``QThread`` must never be destroyed)."""
    from PySide6.QtCore import QThread

    for thread in window.findChildren(QThread):
        thread.wait(5000)
    window.close()
    window.deleteLater()


def _everyday_pages(window: Any) -> list[Any]:
    return [
        window.session_screen,
        window.review_screen,
        window.past_sessions_screen,
        window.recovery_screen,
    ]


def _settings_pages(window: Any) -> list[Any]:
    return [
        window.microphone_screen,
        window.practitioner_screen,
        window.clinics_screen,
        window.status_panel,
    ]


# --- Task 3.1: the icons -----------------------------------------------------------------


def _pixels(pixmap: Any) -> set[int]:
    image = pixmap.toImage()
    return {image.pixel(x, y) for x in range(image.width()) for y in range(image.height())}


class TestIcons:
    @pytest.mark.parametrize("name", icons.ICON_NAMES)
    @pytest.mark.parametrize("scale", icons.SCALES)
    def test_each_icon_draws_at_both_scales(self, qapp: Any, name: str, scale: int) -> None:
        pixmap = icons.pixmap(name, theme.LIGHT.text_muted, 22, scale)
        assert not pixmap.isNull()
        assert (pixmap.width(), pixmap.height()) == (22 * scale, 22 * scale)
        assert pixmap.devicePixelRatio() == scale
        pixels = _pixels(pixmap)
        assert len(pixels) > 1  # non-uniform
        assert 0 in pixels  # a transparent background
        assert any(pixel >> 24 > 0x80 for pixel in pixels)  # and a drawn shape

    def test_the_colour_given_is_the_colour_drawn(self, qapp: Any) -> None:
        for name in icons.ICON_NAMES:
            muted = icons.pixmap(name, theme.LIGHT.text_muted, 22).toImage()
            accent = icons.pixmap(name, theme.LIGHT.accent, 22).toImage()
            assert muted != accent, name

    def test_an_unknown_name_is_refused(self, qapp: Any) -> None:
        with pytest.raises(ValueError):
            icons.pixmap("no-such-icon", theme.LIGHT.text, 22)

    @pytest.mark.parametrize("value", ["red", "#123456", "", "transparent"])
    def test_only_a_token_colour_is_drawn(self, qapp: Any, value: str) -> None:
        """Review round 11: ``theme.colour`` — the one place a colour becomes
        Qt's value outside ``ui/theme.py``'s own palette — takes token values
        only, so no colour reaches an icon from outside the theme."""
        with pytest.raises(ValueError):
            theme.colour(value)
        with pytest.raises(ValueError):
            icons.pixmap("record", value, 22)

    def test_every_token_colour_is_accepted(self, qapp: Any) -> None:
        from dataclasses import fields

        for tokens in (theme.LIGHT, theme.DARK):
            for field in fields(theme.Tokens):
                value = getattr(tokens, field.name)
                if isinstance(value, str):
                    assert theme.colour(value).isValid(), field.name

    def test_an_icon_carries_a_checked_state_when_asked(self, qapp: Any) -> None:
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QIcon

        plain = icons.icon("record", theme.LIGHT.text_muted, 22)
        lit = icons.icon("record", theme.LIGHT.text_muted, 22, checked=theme.LIGHT.accent)
        assert not plain.isNull() and not lit.isNull()
        off = lit.pixmap(QSize(22, 22), QIcon.Mode.Normal, QIcon.State.Off).toImage()
        on = lit.pixmap(QSize(22, 22), QIcon.Mode.Normal, QIcon.State.On).toImage()
        assert off != on

    def test_the_app_icon_has_its_sizes(self, qapp: Any) -> None:
        app_icon = icons.app_icon()
        assert not app_icon.isNull()
        widths = {size.width() for size in app_icon.availableSizes()}
        assert {16, 32, 256} <= widths


class TestNewModulesKeepTheConstraints:
    """C1, C2, C9, C10 for the two new modules (``test_shadow_exits.py`` and
    ``test_ui_theme.py`` check the whole package; this names the shell's own
    limits where a reader looks first)."""

    _FORBIDDEN_CALLS = frozenset(
        {
            "begin",
            "clipboard",
            "QMimeData",
            "QDrag",
            "QListWidget",
            "QComboBox",
            "QListView",
            "QTreeView",
            "QTableView",
            "QPlainTextEdit",
            "QTextEdit",
            "QTextBrowser",
            "QLineEdit",
            "setTextInteractionFlags",
            "setStyleSheet",
        }
    )

    @pytest.mark.parametrize("relative", ["ui/icons.py", "ui/shell.py"])
    def test_no_forbidden_call_import_or_application_use(self, relative: str) -> None:
        tree = ast.parse((PACKAGE / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
                assert name not in self._FORBIDDEN_CALLS, f"{relative}:{node.lineno} {name}"
            if isinstance(node, ast.ImportFrom):
                assert "QtSvg" not in (node.module or ""), relative
                assert all(alias.name != "QApplication" for alias in node.names), relative
            if isinstance(node, ast.Name):
                assert node.id != "QApplication", f"{relative}:{node.lineno}"


# --- Tasks 3.2 / 3.3 / 3.5: the rail, the strip and the window ----------------------------


class _FakeScreen:
    """A screen reporting an injected work area (never this host's)."""

    def __init__(self, width: int, height: int) -> None:
        self._size = (width, height)

    def availableGeometry(self) -> Any:  # noqa: N802 - Qt's name
        from PySide6.QtCore import QRect

        return QRect(0, 0, *self._size)


class TestOpeningSize:
    """Review rounds 11 and 13 (C14 both ways): the opening size from an
    injected work area and frame — a large screen keeps D4's 1200 x 800; on a
    small one the DECORATED window (client area plus the frame) fits."""

    @pytest.mark.parametrize(
        "work_area, frame, expected",
        [
            ((2560, 1400), (16, 48), (1200, 800)),
            ((1920, 1040), (16, 48), (1200, 800)),
            ((1280, 690), (16, 48), (1200, 642)),  # 1080p at 150 %
            ((1280, 690), (0, 0), (1200, 690)),  # no frame: the client fills it
            ((1280, 690), (20, 60), (1200, 630)),  # a taller frame: below the minimum
            ((1093, 574), (16, 48), (1077, 526)),  # 1366 x 768 at 125 %
        ],
    )
    def test_the_decorated_window_fits_the_work_area(
        self,
        work_area: tuple[int, int],
        frame: tuple[int, int],
        expected: tuple[int, int],
    ) -> None:
        width, height = shell.opening_size(*work_area, frame=frame)
        assert (width, height) == expected
        assert width + frame[0] <= work_area[0] and height + frame[1] <= work_area[1]
        assert shell.OPENING_SIZE == (1200, 800)

    def test_the_default_frame_allowance_keeps_the_minimum_on_1080p_at_150(self) -> None:
        width, height = shell.opening_size(1280, 690)
        assert (width, height) == (1200, 642)
        assert width >= 960 and height >= 640  # the decorated window fits, unshrunk

    def test_a_screen_is_asked_for_its_work_area(self) -> None:
        assert shell.opening_size_for(_FakeScreen(1280, 690)) == (1200, 642)  # type: ignore[arg-type]
        assert shell.opening_size_for(_FakeScreen(2560, 1400)) == (1200, 800)  # type: ignore[arg-type]

    def test_no_screen_opens_at_the_default_size(self) -> None:
        assert shell.opening_size_for(None) == shell.OPENING_SIZE


class TestWindowShell:
    def test_the_tab_bar_is_hidden_and_the_window_has_its_icon_and_minimum(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from PySide6.QtCore import QSize

        window = _main_window(tmp_path)
        assert window.tabs.tabBar().isHidden()
        assert window.tabs.documentMode()
        assert window.windowTitle() == "Clinic Scribe"
        assert not window.windowIcon().isNull()
        assert window.minimumSize() == QSize(960, 640)
        # Review rounds 11 and 13: the opening size is the one its own screen's
        # work area gives (whatever this host's is), then the minimum.
        bound = QSize(*shell.opening_size_for(window.screen())).expandedTo(window.minimumSize())
        assert window.width() <= bound.width() and window.height() <= bound.height()
        assert window.rail.isAncestorOf(window.rail.settings_button)
        assert window.centralWidget().isAncestorOf(window.tabs)
        _close(window)

    def test_the_rail_has_the_four_everyday_entries_and_the_gear(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window = _main_window(tmp_path)
        rail = window.rail
        assert [button.text() for button, _name, _page in rail.entries] == _EVERYDAY_TITLES
        assert [page for _button, _name, page in rail.entries] == _everyday_pages(window)
        assert all(not button.icon().isNull() for button, _name, _page in rail.entries)
        assert rail.settings_button.text() == "Settings"
        assert not rail.settings_button.isCheckable()
        assert not rail.settings_button.icon().isNull()
        # The Settings strip carries the four setup titles the container has.
        assert window.settings_strip.titles() == _SETTINGS_TITLES
        _close(window)

    def test_a_rail_click_lands_on_its_page_and_lights_only_it(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window = _main_window(tmp_path)
        for button, _name, page in window.rail.entries:
            button.click()
            assert window.tabs.currentWidget() is page
            assert window.rail.lit_pages() == [page]
            assert not window.settings_strip.isVisibleTo(window)
            button.click()  # the lit entry again: still lit, still there
            assert window.tabs.currentWidget() is page
            assert window.rail.lit_pages() == [page]
        _close(window)

    def test_the_gear_opens_settings_with_no_lit_entry(self, qapp: Any, tmp_path: Path) -> None:
        window = _main_window(tmp_path)
        window.rail.button_for(window.session_screen).click()
        assert window.rail.lit_pages() == [window.session_screen]
        window.rail.settings_button.click()
        assert window.tabs.currentWidget() is window.microphone_screen
        assert window.rail.lit_pages() == []
        assert not window.rail.settings_button.isChecked()
        assert window.settings_strip.isVisibleTo(window)
        assert window.settings_strip.current_title() == "Microphone"
        _close(window)

    def test_a_settings_page_lights_no_entry_and_shows_the_strip(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window = _main_window(tmp_path)
        window.show_page(window.review_screen)
        window.tabs.setCurrentWidget(window.practitioner_screen)
        assert window.rail.lit_pages() == []
        assert window.settings_strip.isVisibleTo(window)
        assert window.settings_strip.current_title() == "Practitioner"
        # The strip hides when a rail entry is chosen.
        window.rail.button_for(window.recovery_screen).click()
        assert window.tabs.currentWidget() is window.recovery_screen
        assert not window.settings_strip.isVisibleTo(window)
        _close(window)

    def test_the_strip_switches_between_the_setup_pages(self, qapp: Any, tmp_path: Path) -> None:
        window = _main_window(tmp_path)
        window.rail.settings_button.click()
        strip = window.settings_strip
        for index, page in enumerate(_settings_pages(window)):
            strip.tab_bar.setCurrentIndex(index)
            assert window.tabs.currentWidget() is page
            assert strip.current_title() == _SETTINGS_TITLES[index]
            assert window.rail.lit_pages() == []
            assert strip.isVisibleTo(window)
        _close(window)

    def test_a_window_without_a_profile_opens_on_practitioner_with_no_lit_entry(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """The 0.4.0 landing rule, unchanged (D5): first run is Settings →
        Practitioner, so the strip shows it and no rail entry is lit."""
        window = _main_window(tmp_path)
        assert window.tabs.currentWidget() is window.practitioner_screen
        assert window.rail.lit_pages() == []
        assert window.settings_strip.isVisibleTo(window)
        assert window.settings_strip.current_title() == "Practitioner"
        _close(window)

    def test_leaving_past_sessions_through_the_rail_still_clears_it(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """C7: the identity rule holds through the rail — the opened entry's
        text and the listed names leave the widgets."""
        from PySide6.QtCore import Qt

        window = _main_window(tmp_path)
        screen = window.past_sessions_screen
        sid, _ = _ps_entry(screen._store)
        window.rail.button_for(screen).click()
        assert window.tabs.currentWidget() is screen
        assert screen.entry_list.count() == 1
        item = screen.entry_list.item(0)
        assert item.data(Qt.ItemDataRole.UserRole) == sid
        screen.entry_list.setCurrentItem(item)
        item.setSelected(True)
        assert screen.generated_view.toPlainText() != ""
        window.rail.button_for(window.session_screen).click()
        assert window.tabs.currentWidget() is window.session_screen
        assert screen.generated_view.toPlainText() == ""
        assert screen._open_entry is None
        assert screen.entry_list.count() == 0 and screen._listings == []
        _close(window)

    def test_recovery_still_has_exactly_five_push_buttons(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from PySide6.QtWidgets import QPushButton

        window = _main_window(tmp_path)
        assert len(window.recovery_screen.findChildren(QPushButton)) == 5
        _close(window)

    def test_the_rail_retints_when_the_theme_announces_new_tokens(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """D3/D12 and C14 both ways: light → dark → light through the theme's
        bus alone (nothing re-applies the application's theme)."""
        from PySide6.QtCore import QSize

        window = _main_window(tmp_path)
        button = window.rail.button_for(window.session_screen)
        assert button is not None

        def drawn() -> Any:
            return button.icon().pixmap(QSize(22, 22)).toImage()

        before = theme.current_tokens()
        try:
            theme.theme_bus().changed.emit(theme.LIGHT)
            light = drawn()
            theme.theme_bus().changed.emit(theme.DARK)
            dark = drawn()
            assert dark != light
            theme.theme_bus().changed.emit(theme.LIGHT)
            assert drawn() == light
        finally:
            theme.theme_bus().changed.emit(before)
        _close(window)


# --- Task 3.4 / 3.5: the REC / PAUSED cue -----------------------------------------------


class TestRailCue:
    def test_the_cue_follows_the_shown_state(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        cue = window.rail.cue_label
        assert cue.isHidden()  # idle: no cue
        shown: list[object] = []
        window.session_screen.state_shown.connect(shown.append)
        controller.state_value = SessionState.RECORDING
        window.session_screen.refresh()
        assert cue.text() == "REC" and cue.isVisibleTo(window)
        window.session_screen.refresh()  # the same state again: not announced again
        assert shown == [SessionState.RECORDING]
        controller.state_value = SessionState.PAUSED
        window.session_screen.refresh()
        assert cue.text() == "PAUSED" and cue.isVisibleTo(window)
        controller.state_value = SessionState.PROCESSING
        window.session_screen.refresh()
        assert cue.text() == "" and cue.isHidden()
        assert shown == [SessionState.RECORDING, SessionState.PAUSED, SessionState.PROCESSING]
        _close(window)

    def test_a_window_opened_mid_recording_shows_the_cue(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        controller.state_value = SessionState.RECORDING
        window = _main_window(tmp_path, controller)
        assert window.rail.cue_label.text() == "REC"
        assert window.rail.cue_label.isVisibleTo(window)
        _close(window)

    def test_a_status_bar_message_leaves_the_cue_visible(self, qapp: Any, tmp_path: Path) -> None:
        """The regression the dropped status-bar label would have had: a
        message with no timeout replaces non-permanent status-bar widgets, so
        the cue lives on the rail (pinned deliberately)."""
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        controller.state_value = SessionState.PAUSED
        window.session_screen.refresh()
        window.statusBar().showMessage(models.pause_cue_text("hotkey", linked=False))
        qapp.processEvents()
        assert window.statusBar().currentMessage().startswith("Paused by the hotkey.")
        assert window.rail.cue_label.text() == "PAUSED"
        assert window.rail.cue_label.isVisibleTo(window)
        _close(window)

    def test_the_failed_line_still_reads_the_last_state(self, qapp: Any, tmp_path: Path) -> None:
        """``state_shown`` keeps its own field: ``_watch_state``'s FAILED line
        (a recording that died) still fires after the cue has been shown."""
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        screen = window.session_screen
        controller.state_value = SessionState.RECORDING
        screen.refresh()
        controller.state_value = SessionState.FAILED
        screen._watch_state()
        assert screen.message_label.text().startswith("Recording failed")
        assert window.rail.cue_label.isHidden()
        _close(window)


# --- Task 3.4 / 3.5: the header's Chrome line --------------------------------------------


class TestHeader:
    _VIEW = models.ChromeView(
        link="connected",
        patient="Jan Citizen",
        clinic="Northside",
        phase="recording",
        hotkey="not_set_up",
        refusal="Open the patient's treatment note in Cliniko first.",
    )
    _LIVE = "Recording for Jan Citizen - Northside."

    def test_no_bridge_no_chrome_line(self, qapp: Any, tmp_path: Path) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QLabel

        window = _main_window(tmp_path)
        header = window.header_strip
        assert header.text() == ""
        assert header.link_label.isHidden()
        assert header.title_label.text() == "Clinic Scribe"
        # Every label the shell builds is plain text (C5, C8).
        for part in (window.header_strip, window.rail, window.settings_strip):
            for label in part.findChildren(QLabel):
                assert label.textFormat() == Qt.TextFormat.PlainText
        _close(window)

    def test_the_link_line_then_the_live_line_with_a_clinic(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window = _main_window(tmp_path)
        header = window.header_strip
        window.show_page(window.session_screen)
        window.session_screen.set_header_view(models.ChromeView(link="connected"))
        assert header.text() == models.CHROME_CONNECTED_LINE
        assert header.link_label.isVisibleTo(window)
        window.session_screen.set_header_view(self._VIEW)
        assert header.text().split("\n") == [models.CHROME_CONNECTED_LINE, self._LIVE]
        assert "Refused from Chrome" not in header.text()
        assert models.HOTKEY_LINES["not_set_up"] not in header.text()
        # No bridge again: empty and hidden.
        window.session_screen.set_header_view(models.ChromeView())
        assert header.text() == "" and header.link_label.isHidden()
        _close(window)

    def test_the_live_line_is_withheld_on_past_sessions(self, qapp: Any, tmp_path: Path) -> None:
        window = _main_window(tmp_path)
        header = window.header_strip
        window.show_page(window.session_screen)
        window.session_screen.set_header_view(self._VIEW)
        window.rail.button_for(window.past_sessions_screen).click()
        assert header.text() == models.CHROME_CONNECTED_LINE
        assert "Jan Citizen" not in header.link_label.text()
        # A new view while Past sessions is current stays withheld too.
        window.session_screen.set_header_view(self._VIEW)
        assert header.text() == models.CHROME_CONNECTED_LINE
        window.rail.button_for(window.review_screen).click()
        assert header.text().split("\n") == [models.CHROME_CONNECTED_LINE, self._LIVE]
        _close(window)

    def test_the_bridge_feeds_the_header_from_its_view(self, qapp: Any, tmp_path: Path) -> None:
        """The bridge's own refresh passes the view: a verified, linked
        recording's two lines, and the link line alone without the live one."""
        h = bridge_tests.Harness(qapp, tmp_path)
        try:
            announced: list[tuple[str, str]] = []
            h.screen.chrome_view_changed.connect(lambda full, bare: announced.append((full, bare)))
            h.verified_report()
            h.start()
            full, bare = announced[-1]
            assert full.split("\n") == [
                models.CHROME_CONNECTED_LINE,
                f"Recording for {bridge_tests.PATIENT_NAME} - Northside.",
            ]
            assert bare == models.CHROME_CONNECTED_LINE
        finally:
            h.close()
