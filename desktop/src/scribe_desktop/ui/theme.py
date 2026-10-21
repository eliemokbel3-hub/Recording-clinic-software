"""The app's visual tokens and the one theme that applies them (ui-refresh
plan D1–D3).

Every colour, type size, spacing and radius the desktop app draws with lives
here and nowhere else: ``docs/design-system.md``'s "Tokens" section names the
roles, this module holds the values (``LIGHT`` and ``DARK``). The theme is
Qt's Fusion style (inside ``IndicatorStyle``, which gives every tick box and
radio circle a visible border), a ``QPalette`` built from the tokens (so the parts Qt
paints itself — menus, message boxes, scroll bars, disabled text — match)
and ONE generated stylesheet whose selectors are widget classes, three
dynamic properties (``role`` on a label, ``variant`` on a button, ``card`` on
a frame) and the shell's object ids. ``tests/test_ui_theme.py`` checks that
no colour, font weight or ``setStyleSheet`` call survives anywhere else in
the package.

It is applied in exactly two places (D2): ``app.main()``, on the line after
the ``QApplication`` exists — before the single-instance guard, so its two
refusal boxes are themed too — and the test suite's autouse fixture
(``conftest._themed_qapp``). ``ensure_applied`` follows the Windows app-mode
setting live (D3): ``colorSchemeChanged`` re-applies the palette and the
stylesheet, and Qt repolishes every widget; nothing is re-created, and no
text, enabled state or interaction flag changes. Tests choose the scheme only
through ``force_scheme``, never by changing the platform's own setting.

Emphasis is a role, never rich text: every message label stays ``PlainText``
(user-written text is never read as markup) and gets its weight and colour
from ``set_role``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, fields
from functools import cache
from typing import Final, Literal

from PySide6.QtCore import QCoreApplication, QObject, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QProxyStyle,
    QPushButton,
    QStyle,
    QStyleFactory,
    QStyleOption,
    QWidget,
)

Scheme = Literal["light", "dark"]

# The application property ``apply_theme`` stamps with the scheme it applied
# (the "theme marker" the start-up tests read), and the one ``ensure_applied``
# sets once it follows the Windows scheme.
SCHEME_PROPERTY: Final = "scribe_scheme"
_FOLLOWING_PROPERTY: Final = "scribe_scheme_following"

# The values the three dynamic properties may take; each has its rules in
# ``render_qss``.
ROLES: Final = frozenset({"danger", "error", "strong", "muted", "title", "success"})
VARIANTS: Final = frozenset({"primary", "danger", "link"})
# The shell's object ids (Phase 3 builds the widgets; the rules exist now).
SHELL_IDS: Final = (
    "rail",
    "railButton",
    "railCue",
    "header",
    "appTitle",
    "settingsStrip",
    "settingsTabs",
)


@dataclass(frozen=True)
class Tokens:
    """One scheme's values. Colours are ``#rrggbb``; sizes are points; spacing,
    radii and the rail width are pixels."""

    # Colour roles.
    canvas: str
    surface: str
    surface_alt: str
    border: str
    text: str
    text_muted: str
    text_disabled: str
    accent: str
    accent_hover: str
    on_accent: str
    danger: str
    warning: str
    success: str
    focus: str
    link: str
    rec: str
    paused: str
    hover: str
    pressed: str
    # The border of an empty tick box or radio circle (UI refresh Task S.1).
    indicator: str
    # Type.
    family: tuple[str, ...]
    size_body: int
    size_caption: int
    size_title: int
    size_heading: int
    # Spacing, radii, the rail.
    space_1: int
    space_2: int
    space_3: int
    space_4: int
    space_5: int
    radius_control: int
    radius_card: int
    rail_width: int


_FAMILY: Final = ("Segoe UI Variable Text", "Segoe UI", "Arial")

LIGHT: Final = Tokens(
    canvas="#f3f4f6",
    surface="#ffffff",
    surface_alt="#f9fafb",
    border="#d9dde3",
    text="#111827",
    text_muted="#6b7280",
    text_disabled="#9ca3af",
    accent="#2563eb",
    accent_hover="#1d4ed8",
    on_accent="#ffffff",
    danger="#b91c1c",
    warning="#b45309",
    success="#15803d",
    focus="#2563eb",
    link="#1d4ed8",
    rec="#dc2626",
    paused="#b45309",
    hover="#eef2f7",
    pressed="#e2e8f0",
    indicator="#6b7280",
    family=_FAMILY,
    size_body=10,
    size_caption=9,
    size_title=14,
    size_heading=11,
    space_1=4,
    space_2=8,
    space_3=12,
    space_4=16,
    space_5=24,
    radius_control=6,
    radius_card=10,
    rail_width=84,
)

DARK: Final = Tokens(
    canvas="#111418",
    surface="#1b1f26",
    surface_alt="#232934",
    border="#2f3642",
    text="#e5e7eb",
    text_muted="#9ca3af",
    text_disabled="#6b7280",
    accent="#3b82f6",
    accent_hover="#60a5fa",
    on_accent="#ffffff",
    danger="#f87171",
    warning="#fbbf24",
    success="#4ade80",
    focus="#60a5fa",
    link="#93c5fd",
    rec="#f87171",
    paused="#fbbf24",
    hover="#2a313d",
    pressed="#323a47",
    indicator="#9ca3af",
    family=_FAMILY,
    size_body=10,
    size_caption=9,
    size_title=14,
    size_heading=11,
    space_1=4,
    space_2=8,
    space_3=12,
    space_4=16,
    space_5=24,
    radius_control=6,
    radius_card=10,
    rail_width=84,
)


def tokens_for(scheme: Scheme) -> Tokens:
    return DARK if scheme == "dark" else LIGHT


# Every colour value either token set holds (``colour`` accepts no other).
_TOKEN_COLOURS: Final = frozenset(
    value
    for tokens in (LIGHT, DARK)
    for field in fields(Tokens)
    if isinstance(value := getattr(tokens, field.name), str)
)


def _rule(selector: str, *declarations: str) -> str:
    return f"{selector} {{ {' '.join(f'{d};' for d in declarations)} }}"


@cache
def render_qss(t: Tokens) -> str:
    """The one application stylesheet for ``t``. Every control class that
    gets a colour here also gets its disabled state (C13), so a disabled
    control still reads as disabled; check and radio indicators get a size
    only, so Fusion still draws the tick from the palette (their border is
    ``IndicatorStyle``'s, below)."""
    r, rc = t.radius_control, t.radius_card
    s1, s2, s3 = t.space_1, t.space_2, t.space_3
    inputs = "QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QComboBox"
    rules = [
        _rule(
            "QToolTip",
            f"color: {t.text}",
            f"background-color: {t.surface}",
            f"border: 1px solid {t.border}",
            f"padding: {s1}px",
        ),
        # Every group box is a card (design-system "Surfaces & layout").
        _rule(
            "QGroupBox",
            f"background-color: {t.surface}",
            f"border: 1px solid {t.border}",
            f"border-radius: {rc}px",
            "margin-top: 22px",
            f"padding: {s3}px",
        ),
        _rule(
            "QGroupBox::title",
            "subcontrol-origin: margin",
            "subcontrol-position: top left",
            f"left: {s3}px",
            f"padding: 0px {s1}px",
            f"color: {t.text}",
            "font-weight: 600",
        ),
        _rule("QGroupBox::title:disabled", f"color: {t.text_disabled}"),
        _rule(
            'QFrame[card="true"]',
            f"background-color: {t.surface}",
            f"border: 1px solid {t.border}",
            f"border-radius: {rc}px",
        ),
        # Buttons: the plain one, its states, then the three variants.
        _rule(
            "QPushButton",
            f"color: {t.text}",
            f"background-color: {t.surface}",
            f"border: 1px solid {t.border}",
            f"border-radius: {r}px",
            f"padding: 5px {s3}px",
        ),
        _rule("QPushButton:hover", f"background-color: {t.hover}"),
        _rule("QPushButton:pressed, QPushButton:checked", f"background-color: {t.pressed}"),
        _rule("QPushButton:focus", f"border-color: {t.focus}"),
        _rule(
            "QPushButton:disabled",
            f"color: {t.text_disabled}",
            f"background-color: {t.surface_alt}",
            f"border-color: {t.border}",
        ),
        _rule(
            'QPushButton[variant="primary"]',
            f"color: {t.on_accent}",
            f"background-color: {t.accent}",
            f"border-color: {t.accent}",
        ),
        _rule(
            'QPushButton[variant="primary"]:hover, QPushButton[variant="primary"]:pressed',
            f"background-color: {t.accent_hover}",
            f"border-color: {t.accent_hover}",
        ),
        # The primary button's border is already the accent (which is the
        # focus colour in light), so its focus border is the text colour.
        _rule('QPushButton[variant="primary"]:focus', f"border-color: {t.text}"),
        _rule(
            'QPushButton[variant="primary"]:disabled',
            f"color: {t.text_disabled}",
            f"background-color: {t.surface_alt}",
            f"border-color: {t.border}",
        ),
        _rule(
            'QPushButton[variant="danger"]',
            f"color: {t.danger}",
            f"border-color: {t.danger}",
        ),
        _rule(
            'QPushButton[variant="danger"]:hover, QPushButton[variant="danger"]:pressed',
            f"background-color: {t.hover}",
        ),
        _rule('QPushButton[variant="danger"]:focus', f"border-color: {t.focus}"),
        _rule(
            'QPushButton[variant="danger"]:disabled',
            f"color: {t.text_disabled}",
            f"border-color: {t.border}",
        ),
        _rule(
            'QPushButton[variant="link"]',
            f"color: {t.link}",
            "background-color: transparent",
            # Transparent until focused, so focus never changes the size.
            "border: 1px solid transparent",
            "padding: 0px",
            "text-decoration: underline",
        ),
        _rule(
            'QPushButton[variant="link"]:hover, QPushButton[variant="link"]:pressed',
            f"color: {t.accent}",
            "background-color: transparent",
        ),
        _rule('QPushButton[variant="link"]:focus', f"border-color: {t.focus}"),
        _rule('QPushButton[variant="link"]:disabled', f"color: {t.text_disabled}"),
        # Label roles: emphasis without rich text.
        _rule('QLabel[role="danger"]', f"color: {t.danger}", "font-weight: 600"),
        _rule('QLabel[role="error"]', f"color: {t.danger}"),
        _rule('QLabel[role="strong"]', "font-weight: 600"),
        _rule('QLabel[role="muted"]', f"color: {t.text_muted}"),
        _rule('QLabel[role="title"]', f"font-size: {t.size_title}pt", "font-weight: 600"),
        _rule('QLabel[role="success"]', f"color: {t.success}"),
        _rule(
            'QLabel[role="danger"]:disabled, QLabel[role="error"]:disabled, '
            'QLabel[role="muted"]:disabled, QLabel[role="success"]:disabled',
            f"color: {t.text_disabled}",
        ),
        # Inputs and the combo box's popup (styled here, never by replacing
        # its view — C2).
        _rule(
            inputs,
            f"color: {t.text}",
            f"background-color: {t.surface}",
            f"border: 1px solid {t.border}",
            f"border-radius: {r}px",
            f"padding: {s1}px 6px",
            f"selection-color: {t.on_accent}",
            f"selection-background-color: {t.accent}",
        ),
        _rule(
            "QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, "
            "QComboBox:focus",
            f"border-color: {t.focus}",
        ),
        _rule(
            "QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled, "
            "QSpinBox:disabled, QComboBox:disabled",
            f"color: {t.text_disabled}",
            f"background-color: {t.surface_alt}",
            # The selection colours above out-rank the disabled palette.
            f"selection-color: {t.text_disabled}",
            f"selection-background-color: {t.border}",
        ),
        _rule("QComboBox::drop-down", "border: none", "width: 20px"),
        _rule(
            "QComboBox QAbstractItemView",
            f"color: {t.text}",
            f"background-color: {t.surface}",
            f"border: 1px solid {t.border}",
            f"selection-color: {t.on_accent}",
            f"selection-background-color: {t.accent}",
            "outline: 0px",
        ),
        # Lists keep a usable height in a short window (C6).
        _rule(
            "QListWidget",
            f"color: {t.text}",
            f"background-color: {t.surface}",
            f"border: 1px solid {t.border}",
            f"border-radius: {r}px",
            "min-height: 48px",
            "outline: 0px",
        ),
        # ``outline: 0px`` drops the dotted item focus rectangle, so the
        # list's own border shows where the keyboard focus is.
        _rule("QListWidget:focus", f"border-color: {t.focus}"),
        _rule("QListWidget::item", f"padding: 3px {s1}px"),
        _rule(
            "QListWidget::item:selected",
            f"color: {t.on_accent}",
            f"background-color: {t.accent}",
        ),
        _rule(
            "QListWidget:disabled",
            f"color: {t.text_disabled}",
            f"background-color: {t.surface_alt}",
        ),
        # A disabled list's selected row: the item rule above out-ranks the
        # list's disabled colours, so it gets its own.
        _rule(
            "QListWidget::item:selected:disabled",
            f"color: {t.text_disabled}",
            f"background-color: {t.border}",
        ),
        # Check and radio buttons: a size only — Fusion draws the tick and
        # ``IndicatorStyle`` the border (a border here would stop Fusion
        # drawing the tick).
        _rule("QCheckBox, QRadioButton", f"spacing: {s2}px"),
        _rule("QCheckBox::indicator, QRadioButton::indicator", "width: 16px", "height: 16px"),
        _rule(
            "QProgressBar",
            f"color: {t.text}",
            f"background-color: {t.surface_alt}",
            f"border: 1px solid {t.border}",
            f"border-radius: {r}px",
            "text-align: center",
        ),
        _rule("QProgressBar::chunk", f"background-color: {t.accent}", f"border-radius: {r}px"),
        _rule("QProgressBar:disabled", f"color: {t.text_disabled}"),
        # Scroll bars: every sub-control set, or Qt mixes in the base style's.
        _rule(
            "QScrollBar:vertical",
            f"background-color: {t.canvas}",
            "width: 12px",
            "margin: 0px",
            "border: none",
        ),
        _rule(
            "QScrollBar:horizontal",
            f"background-color: {t.canvas}",
            "height: 12px",
            "margin: 0px",
            "border: none",
        ),
        _rule(
            "QScrollBar::handle:vertical",
            f"background-color: {t.border}",
            "min-height: 24px",
            "border-radius: 4px",
            "margin: 2px",
        ),
        _rule(
            "QScrollBar::handle:horizontal",
            f"background-color: {t.border}",
            "min-width: 24px",
            "border-radius: 4px",
            "margin: 2px",
        ),
        _rule(
            "QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover",
            f"background-color: {t.text_muted}",
        ),
        _rule(
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, "
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal",
            "width: 0px",
            "height: 0px",
            "border: none",
            "background: none",
        ),
        _rule(
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical, "
            "QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal",
            "background: none",
        ),
        _rule("QScrollArea", "border: none"),
        # Tabs: today's tab bar (hidden by the Phase 3 shell) and the Settings strip's.
        _rule("QTabWidget::pane", "border: none"),
        _rule(
            "QTabBar::tab",
            f"color: {t.text_muted}",
            "background-color: transparent",
            "border: none",
            "border-bottom: 2px solid transparent",
            f"padding: 6px {s3}px",
        ),
        _rule("QTabBar::tab:hover", f"color: {t.text}"),
        _rule("QTabBar::tab:selected", f"color: {t.text}", f"border-bottom-color: {t.accent}"),
        _rule("QTabBar::tab:disabled", f"color: {t.text_disabled}"),
        # Menus, message boxes and dialogs: readable in both schemes (C13).
        _rule(
            "QMenu",
            f"color: {t.text}",
            f"background-color: {t.surface}",
            f"border: 1px solid {t.border}",
            f"padding: {s1}px",
        ),
        _rule("QMenu::item", "background-color: transparent", f"padding: 5px 24px 5px {s3}px"),
        _rule(
            "QMenu::item:selected",
            f"color: {t.on_accent}",
            f"background-color: {t.accent}",
        ),
        _rule(
            "QMenu::item:disabled",
            f"color: {t.text_disabled}",
            "background-color: transparent",
        ),
        _rule(
            "QMenu::separator",
            "height: 1px",
            f"background-color: {t.border}",
            f"margin: {s1}px {s2}px",
        ),
        _rule("QDialog, QMessageBox", f"background-color: {t.canvas}"),
        _rule("QMessageBox QLabel, QDialog QLabel", f"color: {t.text}"),
        _rule(
            "QMessageBox QLabel:disabled, QDialog QLabel:disabled",
            f"color: {t.text_disabled}",
        ),
        _rule("QDialogButtonBox QPushButton", "min-width: 72px"),
        _rule(
            "QStatusBar",
            f"color: {t.text_muted}",
            f"background-color: {t.surface}",
            f"border-top: 1px solid {t.border}",
        ),
        _rule("QStatusBar::item", "border: none"),
        # The shell (built in Phase 3).
        _rule(
            "QFrame#rail",
            f"background-color: {t.surface}",
            "border: none",
            f"border-right: 1px solid {t.border}",
            f"min-width: {t.rail_width}px",
            f"max-width: {t.rail_width}px",
        ),
        _rule(
            "QToolButton#railButton",
            f"color: {t.text_muted}",
            "background-color: transparent",
            "border: 1px solid transparent",
            f"border-radius: {r}px",
            f"padding: {s1}px",
            # The caption size keeps each caption line inside the rail's
            # width ("Past sessions" is two lines, ``shell.RAIL_CAPTIONS``).
            f"font-size: {t.size_caption}pt",
        ),
        _rule("QToolButton#railButton:hover", f"color: {t.text}", f"background-color: {t.hover}"),
        _rule(
            "QToolButton#railButton:checked",
            f"color: {t.accent}",
            f"background-color: {t.pressed}",
        ),
        _rule("QToolButton#railButton:focus", f"border-color: {t.focus}"),
        _rule("QToolButton#railButton:disabled", f"color: {t.text_disabled}"),
        _rule(
            "QLabel#railCue",
            f"color: {t.rec}",
            f"font-size: {t.size_caption}pt",
            "font-weight: 600",
        ),
        _rule(
            "QFrame#header",
            f"background-color: {t.surface}",
            "border: none",
            f"border-bottom: 1px solid {t.border}",
        ),
        _rule("QLabel#appTitle", f"font-size: {t.size_title}pt", "font-weight: 600"),
        _rule("QFrame#settingsStrip", f"background-color: {t.canvas}", "border: none"),
        _rule("QTabBar#settingsTabs::tab:selected", f"color: {t.accent}"),
    ]
    return "\n".join(rules)


def build_palette(t: Tokens) -> QPalette:
    """The ``QPalette`` for ``t`` — what Fusion paints with wherever the
    stylesheet sets nothing, the disabled group included."""
    role = QPalette.ColorRole
    palette = QPalette()
    for which, value in (
        (role.Window, t.canvas),
        (role.WindowText, t.text),
        (role.Base, t.surface),
        (role.AlternateBase, t.surface_alt),
        (role.Text, t.text),
        (role.Button, t.surface),
        (role.ButtonText, t.text),
        (role.BrightText, t.on_accent),
        (role.Highlight, t.accent),
        (role.HighlightedText, t.on_accent),
        (role.Accent, t.accent),
        (role.ToolTipBase, t.surface),
        (role.ToolTipText, t.text),
        (role.PlaceholderText, t.text_muted),
        (role.Link, t.link),
        (role.LinkVisited, t.link),
        (role.Light, t.surface),
        (role.Midlight, t.surface_alt),
        (role.Mid, t.border),
        (role.Dark, t.border),
        (role.Shadow, t.border),
    ):
        palette.setColor(which, QColor(value))
    disabled = QPalette.ColorGroup.Disabled
    for which, value in (
        (role.WindowText, t.text_disabled),
        (role.Text, t.text_disabled),
        (role.ButtonText, t.text_disabled),
        (role.PlaceholderText, t.text_disabled),
        (role.Base, t.surface_alt),
        (role.Button, t.surface_alt),
        (role.Highlight, t.border),
        (role.HighlightedText, t.text_disabled),
    ):
        palette.setColor(disabled, which, QColor(value))
    return palette


class ThemeBus(QObject):
    """Announces each applied token set (the Phase 3 rail re-tints its icons)."""

    changed = Signal(object)


_bus: ThemeBus | None = None
_forced: Scheme | None = None
_current: Tokens | None = None
_style: QStyle | None = None


def theme_bus() -> ThemeBus:
    global _bus
    if _bus is None:
        _bus = ThemeBus()
    return _bus


def current_tokens() -> Tokens:
    """The token set ``apply_theme`` last applied (``LIGHT`` before any) —
    what a widget built later draws with until ``theme_bus().changed``
    announces the next one."""
    return _current if _current is not None else LIGHT


def colour(value: str) -> QColor:
    """A token's colour as Qt's value (the code-drawn icons' pen and brush,
    ui-refresh plan D12) — so no other module builds a colour itself. Only a
    value one of the two token sets holds is accepted (review round 11): a
    named colour or any other string would bring a value in from outside
    this module."""
    if value not in _TOKEN_COLOURS:
        raise ValueError(f"not a token colour: {value}")
    return QColor(value)


_INDICATORS: Final = frozenset(
    {QStyle.PrimitiveElement.PE_IndicatorCheckBox, QStyle.PrimitiveElement.PE_IndicatorRadioButton}
)


class IndicatorStyle(QProxyStyle):
    """Fusion with a border that shows on every tick box and radio circle,
    empty or not, in both schemes (UI refresh Task S.1). Fusion outlines an
    indicator in a shade it derives from the window colour, which on the
    dark scheme's near-black window is near-black too — an EMPTY consent
    tick vanished. This draws Fusion's indicator first (its fill and its
    tick or dot, unchanged), then strokes the outline over Fusion's own: the
    ``indicator`` token; ``text_disabled`` for a disabled control, so it
    still reads disabled; ``focus`` while it has keyboard focus, as Fusion's
    own outline does. Painted with the painter Qt hands in — no file asset,
    no QtSvg (C10) — and the tokens are read at each paint, so a scheme
    change shows at Qt's repolish. ``tokens`` is the test seam."""

    def __init__(
        self, base: QStyle | None = None, tokens: Callable[[], Tokens] | None = None
    ) -> None:
        super().__init__(base)
        self._tokens: Callable[[], Tokens] = tokens if tokens is not None else current_tokens

    def drawPrimitive(  # noqa: N802 - Qt's name
        self,
        element: QStyle.PrimitiveElement,
        option: QStyleOption,
        painter: QPainter,
        widget: QWidget | None = None,
    ) -> None:
        super().drawPrimitive(element, option, painter, widget)
        if element in _INDICATORS:
            self._outline(element, option, painter)

    def outline_colour(self, state: QStyle.StateFlag) -> str:
        """The outline's token value for an indicator in ``state``."""
        tokens = self._tokens()
        if not state & QStyle.StateFlag.State_Enabled:
            return tokens.text_disabled
        if state & QStyle.StateFlag.State_HasFocus and state & (
            QStyle.StateFlag.State_KeyboardFocusChange
        ):
            return tokens.focus
        return tokens.indicator

    def _outline(
        self, element: QStyle.PrimitiveElement, option: QStyleOption, painter: QPainter
    ) -> None:
        rect = option.rect
        painter.save()
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(self.outline_colour(option.state))))
            if element == QStyle.PrimitiveElement.PE_IndicatorRadioButton:
                # Fusion's own circle: centred, its radius from the width.
                width = rect.width()
                radius = (width + (width + 1) % 2) / 2.0 - 1
                painter.drawEllipse(QRectF(rect).center(), radius, radius)
            else:
                # Fusion's own box: half-pixel aligned, one pixel in.
                painter.translate(0.5, 0.5)
                painter.drawRect(rect.adjusted(0, 0, -1, -1))
        finally:
            painter.restore()


def force_scheme(scheme: Scheme | None) -> None:
    """The test seam (D3, C14): ``apply_theme`` uses ``scheme`` in place of the
    platform's setting until it is reset with ``None``. Never the platform's
    own ``setColorScheme`` — that would change it for the whole process."""
    global _forced
    _forced = scheme


def detect_scheme(app: QApplication) -> Scheme:
    """Windows' app mode as Qt reports it: dark only when Qt says Dark;
    light for Light, Unknown (the offscreen test platform) or a Qt without
    the call."""
    color_scheme = getattr(app.styleHints(), "colorScheme", None)
    if color_scheme is None:
        return "light"
    return "dark" if color_scheme() == Qt.ColorScheme.Dark else "light"


def apply_theme(app: QApplication, scheme: Scheme | None = None) -> Tokens:
    """Apply one scheme's tokens to ``app``: Fusion (once), the palette, the
    font and the stylesheet, in that order; stamp ``SCHEME_PROPERTY`` and
    announce the tokens on ``theme_bus().changed``. ``scheme`` defaults to
    the forced scheme, then the platform's.

    Each of the four is set only when it differs from what the application
    already has: every one of them restyles EVERY live widget, so a repeat
    of the same scheme costs nothing (a scheme change still sets the
    palette and the stylesheet; the font never changes between schemes)."""
    global _current
    chosen: Scheme = scheme or _forced or detect_scheme(app)
    tokens = tokens_for(chosen)
    _current = tokens
    if app.property(SCHEME_PROPERTY) is None:
        global _style
        fusion = QStyleFactory.create("Fusion")
        if fusion is not None:
            # Task S.1: Fusion inside the indicator border. Held here too, so
            # the Python override lives as long as the application uses it.
            _style = IndicatorStyle(fusion)
            app.setStyle(_style)
    palette = build_palette(tokens)
    if app.palette() != palette:
        app.setPalette(palette)
    font = QFont()
    font.setFamilies(list(tokens.family))
    font.setPointSize(tokens.size_body)
    if app.font() != font:
        app.setFont(font)
    stylesheet = render_qss(tokens)
    if app.styleSheet() != stylesheet:
        app.setStyleSheet(stylesheet)
    app.setProperty(SCHEME_PROPERTY, chosen)
    theme_bus().changed.emit(tokens)
    return tokens


def _on_scheme_changed(_scheme: object) -> None:
    # Looks the application up when Windows' mode changes, so the connection
    # holds no reference that would keep the application alive.
    app = QApplication.instance()
    if isinstance(app, QApplication):
        apply_theme(app)


def _follow_scheme_changes(app: QApplication) -> None:
    app.styleHints().colorSchemeChanged.connect(_on_scheme_changed)


def ensure_applied(app: QCoreApplication | None) -> None:
    """Theme ``app`` if it is not themed yet and follow the Windows scheme
    from now on — idempotent through two application properties (one
    connection per application, however often it is called). Does nothing
    without a ``QApplication``; never creates one."""
    if not isinstance(app, QApplication):
        return
    if app.property(_FOLLOWING_PROPERTY) is not True:
        _follow_scheme_changes(app)
        app.setProperty(_FOLLOWING_PROPERTY, True)
    if app.property(SCHEME_PROPERTY) is None:
        apply_theme(app)


def _repolish(widget: QWidget) -> None:
    # Qt does not restyle a widget when only a dynamic property changes. A
    # widget not yet polished (one still being built) needs nothing: Qt
    # polishes it, property included, before it is first shown.
    if not widget.testAttribute(Qt.WidgetAttribute.WA_WState_Polished):
        return
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def set_role(widget: QWidget, role: str) -> None:
    """Give a label its role (``ROLES``) — its colour and weight."""
    if role not in ROLES:
        raise ValueError(f"unknown role: {role}")
    widget.setProperty("role", role)
    _repolish(widget)


def set_variant(button: QPushButton, variant: str) -> None:
    """Give a push button its variant (``VARIANTS``)."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant: {variant}")
    button.setProperty("variant", variant)
    _repolish(button)


def mark_card(frame: QFrame) -> None:
    """Draw a frame as a card (the surface, a border and the card radius)."""
    frame.setProperty("card", True)
    _repolish(frame)
