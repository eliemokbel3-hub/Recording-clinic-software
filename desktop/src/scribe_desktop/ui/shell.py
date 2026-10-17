"""The window's shell: the navigation rail, the header strip and the Settings
strip (ui-refresh plan D4, D5).

The three sit OUTSIDE the screens and drive the window's one ``QTabWidget``
(its own tab bar hidden). Each asks for a page through its ``page_requested``
signal; the window shows it with ``show_page`` → ``setCurrentWidget``, so
``_on_tab_changed``'s identity rule runs for every navigation (Past sessions
forgets its opened entry on leave, Recovery re-lists on entry), and then tells
each part the current page through ``set_current``, which never emits.

- ``NavigationRail``: the four everyday pages and the Settings gear, each an
  icon over its text (never an icon alone). At most one entry is lit — a
  Settings page lights none — and under the first entry (Record) the cue
  "REC" / "PAUSED" from the state the Session screen shows
  (``models.rail_cue_text``). The icons are drawn in code (``ui/icons.py``)
  and re-tinted when the theme announces a new token set.
- ``HeaderStrip``: the app's name and the Chrome line — the link line and,
  with a clinic on the live view, the live line, both built by
  ``models.header_link_text`` from the Chrome view (never by splitting the
  Session screen's own text); the live line is withheld while Past sessions
  is the current page, so its "Hide names" keeps its meaning there. The
  second place the window shows the Chrome line (the Session screen's own
  lines are the first).
- ``SettingsStrip``: "Settings" and a tab bar over the four setup pages,
  shown only while one of them is current.

Every label is plain text. Nothing here builds a list, combo box, text
widget, clipboard or drag, sets a text-interaction flag or calls the
application (ui-refresh plan C1, C2, C9). ``docs/design-system.md``'s
"Surfaces & layout" section documents the shell (ui-refresh plan Task 5.1).
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import partial
from typing import Final

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QResizeEvent, QScreen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTabBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop.ui import icons, theme
from scribe_desktop.ui.theme import set_role

# The rail's icons, in logical pixels.
RAIL_ICON_SIZE: Final = 22
APP_TITLE: Final = "Clinic Scribe"
SETTINGS_LABEL: Final = "Settings"

# One rail entry: its text, its icon's name (``icons.ICON_NAMES``) and the page.
RailEntry = tuple[str, str, QWidget]
# D4: the window's opening size (its client area), in logical pixels.
OPENING_SIZE: Final = (1200, 800)
# What Windows adds round the client area — the title bar and the frame —
# allowed for in logical pixels (Windows 11's caption is about 32 at every
# scale): before the window is shown Qt cannot measure it, and ``resize``
# sizes the client area only (codex round 13 PR-MED-001).
FRAME_ALLOWANCE: Final = (16, 48)


def opening_size(
    available_width: int,
    available_height: int,
    *,
    frame: tuple[int, int] = FRAME_ALLOWANCE,
) -> tuple[int, int]:
    """D4's opening client size, bounded so the DECORATED window — the client
    area plus ``frame`` — fits the screen's work area: at 150 % display
    scaling a 1080p screen's is about 1280 x 690 logical pixels, so a fixed
    800-pixel height would put the title bar or the bottom row (Review's
    buttons and the status bar) off the screen. The window's minimum still
    wins over a smaller work area (Qt bounds ``resize`` by it)."""
    width, height = OPENING_SIZE
    frame_width, frame_height = frame
    return (
        max(0, min(width, available_width - frame_width)),
        max(0, min(height, available_height - frame_height)),
    )


def opening_size_for(screen: QScreen | None) -> tuple[int, int]:
    """``opening_size`` for ``screen``'s work area; D4's size when there is no
    screen to ask."""
    if screen is None:
        return OPENING_SIZE
    work_area = screen.availableGeometry()
    return opening_size(work_area.width(), work_area.height())


def _plain_label(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    return label


class NavigationRail(QFrame):
    """The everyday pages and the Settings gear down the window's left side."""

    page_requested = Signal(QWidget)

    def __init__(
        self,
        entries: Sequence[RailEntry],
        settings: RailEntry,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("rail")
        tokens = theme.current_tokens()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(tokens.space_1, tokens.space_3, tokens.space_1, tokens.space_3)
        layout.setSpacing(tokens.space_1)
        self._current: QWidget | None = None
        self._tint: tuple[str, str] | None = None
        # The REC / PAUSED cue, under the first entry; hidden while empty.
        self.cue_label = _plain_label()
        self.cue_label.setObjectName("railCue")
        self.cue_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.cue_label.hide()
        self.entries: list[tuple[QToolButton, str, QWidget]] = []
        for index, (text, icon_name, page) in enumerate(entries):
            button = self._button(text)
            # Lit by `set_current` only (a click lands there through the
            # window), never by Qt's own exclusive group, which could not
            # leave every entry unlit.
            button.setCheckable(True)
            button.setAutoExclusive(False)
            button.clicked.connect(partial(self._on_clicked, page))
            layout.addWidget(button)
            self.entries.append((button, icon_name, page))
            if index == 0:
                layout.addWidget(self.cue_label)
        layout.addStretch(1)
        text, self._settings_icon, settings_page = settings
        # The gear opens Settings; it is an action, never a lit entry.
        self.settings_button = self._button(text)
        self.settings_button.clicked.connect(partial(self._on_clicked, settings_page))
        layout.addWidget(self.settings_button)
        self._retint(tokens)
        theme.theme_bus().changed.connect(self._retint)

    @staticmethod
    def _button(text: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName("railButton")
        button.setText(text)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setIconSize(QSize(RAIL_ICON_SIZE, RAIL_ICON_SIZE))
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return button

    def _on_clicked(self, page: QWidget, *_args: object) -> None:
        self.page_requested.emit(page)
        # A click on the lit entry toggled it off and changed no page; light
        # whichever page is current now.
        self.set_current(self._current)

    def _retint(self, tokens: object) -> None:
        """Draw the icons in ``tokens``' colours: muted, and the accent for the
        lit entry. A repeat of the same colours redraws nothing."""
        if not isinstance(tokens, theme.Tokens):
            return
        tint = (tokens.text_muted, tokens.accent)
        if tint == self._tint:
            return
        self._tint = tint
        for button, icon_name, _page in self.entries:
            button.setIcon(
                icons.icon(icon_name, tokens.text_muted, RAIL_ICON_SIZE, checked=tokens.accent)
            )
        self.settings_button.setIcon(
            icons.icon(self._settings_icon, tokens.text_muted, RAIL_ICON_SIZE)
        )

    def set_current(self, page: QWidget | None) -> None:
        """Light the entry for ``page`` and no other; a page without an entry
        (every Settings page) lights none."""
        self._current = page
        for button, _icon_name, entry_page in self.entries:
            button.blockSignals(True)
            button.setChecked(entry_page is page)
            button.blockSignals(False)

    def lit_pages(self) -> list[QWidget]:
        return [page for button, _icon_name, page in self.entries if button.isChecked()]

    def button_for(self, page: QWidget) -> QToolButton | None:
        for button, _icon_name, entry_page in self.entries:
            if entry_page is page:
                return button
        return None

    def set_cue(self, text: str) -> None:
        """The cue under Record (``models.rail_cue_text``); hidden when empty."""
        self.cue_label.setText(text)
        self.cue_label.setVisible(bool(text))


class _ElidedLabel(QLabel):
    """A plain-text label that ends each line it cannot fit with an ellipsis.
    The width comes from the layout, never from the text."""

    def __init__(self) -> None:
        super().__init__()
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setWordWrap(False)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._full = ""

    def full_text(self) -> str:
        return self._full

    def set_full_text(self, text: str) -> None:
        self._full = text
        self._elide()

    def resizeEvent(self, event: QResizeEvent, /) -> None:
        super().resizeEvent(event)
        self._elide()

    def _elide(self) -> None:
        metrics = self.fontMetrics()
        width = self.width()
        # Line by line, for display only: what the lines ARE was decided by
        # `models.header_link_text`.
        self.setText(
            "\n".join(
                metrics.elidedText(line, Qt.TextElideMode.ElideRight, width)
                for line in self._full.split("\n")
            )
        )


class HeaderStrip(QFrame):
    """The app's name and the Chrome line across the top of the window."""

    def __init__(self, withheld_page: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("header")
        tokens = theme.current_tokens()
        self._withheld_page = withheld_page
        self._with_live = ""
        self._without_live = ""
        self._withholding = False
        self.title_label = _plain_label(APP_TITLE)
        self.title_label.setObjectName("appTitle")
        set_role(self.title_label, "title")
        self.link_label = _ElidedLabel()
        self.link_label.hide()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(tokens.space_4, tokens.space_2, tokens.space_4, tokens.space_2)
        layout.setSpacing(tokens.space_5)
        layout.addWidget(self.title_label)
        layout.addWidget(self.link_label, 1)

    def set_chrome_text(self, with_live: str, without_live: str) -> None:
        """The Session screen's ``chrome_view_changed``: the text with the live
        line and the same text without it (both empty with no bridge)."""
        self._with_live = with_live
        self._without_live = without_live
        self._show()

    def set_current(self, page: QWidget | None) -> None:
        """Withhold the live line while ``page`` is the Past sessions page."""
        self._withholding = page is self._withheld_page
        self._show()

    def text(self) -> str:
        """What the Chrome line shows now, before any ellipsis."""
        return self.link_label.full_text()

    def _show(self) -> None:
        text = self._without_live if self._withholding else self._with_live
        self.link_label.set_full_text(text)
        self.link_label.setVisible(bool(text))


class SettingsStrip(QFrame):
    """The "Settings" caption and a tab bar over the setup pages, shown only
    while one of them is current."""

    page_requested = Signal(QWidget)

    def __init__(
        self, pages: Sequence[tuple[str, QWidget]], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("settingsStrip")
        tokens = theme.current_tokens()
        self._pages = [page for _title, page in pages]
        self.caption_label = _plain_label(SETTINGS_LABEL)
        set_role(self.caption_label, "muted")
        self.tab_bar = QTabBar()
        self.tab_bar.setObjectName("settingsTabs")
        self.tab_bar.setDrawBase(False)
        self.tab_bar.setExpanding(False)
        self.tab_bar.setDocumentMode(True)
        for title, _page in pages:
            self.tab_bar.addTab(title)
        # Connected after the tabs exist: adding the first one selects it.
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(tokens.space_4, tokens.space_1, tokens.space_4, 0)
        layout.setSpacing(tokens.space_3)
        layout.addWidget(self.caption_label)
        layout.addWidget(self.tab_bar)
        layout.addStretch(1)
        self.hide()

    def titles(self) -> list[str]:
        return [self.tab_bar.tabText(index) for index in range(self.tab_bar.count())]

    def current_title(self) -> str:
        return self.tab_bar.tabText(self.tab_bar.currentIndex())

    def _on_tab_changed(self, index: int) -> None:
        if 0 <= index < len(self._pages):
            self.page_requested.emit(self._pages[index])

    def set_current(self, page: QWidget | None) -> None:
        """Show the strip on ``page``'s tab when it is a setup page; hide it
        on every other page."""
        index = next((i for i, own in enumerate(self._pages) if own is page), -1)
        if index < 0:
            self.hide()
            return
        self.tab_bar.blockSignals(True)
        self.tab_bar.setCurrentIndex(index)
        self.tab_bar.blockSignals(False)
        self.show()


__all__ = [
    "APP_TITLE",
    "FRAME_ALLOWANCE",
    "HeaderStrip",
    "NavigationRail",
    "OPENING_SIZE",
    "RAIL_ICON_SIZE",
    "SettingsStrip",
    "opening_size",
    "opening_size_for",
]
