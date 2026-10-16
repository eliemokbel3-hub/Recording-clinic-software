"""Ui-refresh plan D13: the theme is pinned once, never the rendering.

The token sets are complete and well-formed, the stylesheet carries every
role, variant and object id the code uses, no colour, font weight or
``setStyleSheet`` call survives outside ``ui/theme.py``, ``apply_theme`` and
``ensure_applied`` do what D2/D3 say, and ``app.main()`` themes the
application before the single-instance guard (codex round 1 PR-MED-001).
The scheme is chosen only through ``theme.force_scheme`` (C14) — never the
platform's own setting. No pixel or screenshot test.
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

import scribe_desktop
from scribe_desktop.ui import theme

PACKAGE = Path(scribe_desktop.__file__).resolve().parent
THEME_FILE = "ui/theme.py"

_HEX_COLOUR = re.compile(r"#[0-9a-fA-F]{6}(?![0-9a-zA-Z])")
_STYLE_TEXT = re.compile(r"font-weight|setStyleSheet\(")

# The one ``setObjectName`` whose argument is not a literal: ``_LineEditor``
# copies a standard menu action's own name onto its replacement (C3).
_NON_LITERAL_OBJECT_NAMES = {("ui/note.py", "_LineEditor.build_context_menu")}


@pytest.fixture(scope="module")
def qapp() -> Any:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _relative(path: Path) -> str:
    return path.relative_to(PACKAGE).as_posix()


def _package_files() -> list[Path]:
    return sorted(PACKAGE.rglob("*.py"))


def _declarations(qss: str, selector: str) -> dict[str, str]:
    """The declarations ``qss`` gives exactly ``selector`` (one of a rule's
    comma-separated selectors), a later rule's value winning."""
    found: dict[str, str] = {}
    for line in qss.splitlines():
        head, _, body = line.partition(" { ")
        if selector not in head.split(", "):
            continue
        for declaration in body.removesuffix(" }").split(";"):
            name, _, value = declaration.strip().partition(": ")
            if name:
                found[name] = value
    return found


def _border_colour(declarations: dict[str, str]) -> str | None:
    if "border-color" in declarations:
        return declarations["border-color"]
    if "border" in declarations:
        return declarations["border"].split()[-1]
    return None


class _FakeAppSurface:
    """The application's four theme setters and their getters, replaced on
    the ``QApplication`` class for one test (``monkeypatch`` restores them):
    the setters record ``(name, value)``, the getters return what was last
    set. So a test drives ``apply_theme`` through both schemes without
    restyling the session's live widgets — each real setter repolishes every
    one of them, and an earlier whole-app flip cost two minutes late in the
    suite (peer round 6 suite-time line).

    The starting state is built to differ from BOTH schemes — never Qt's
    default ``QPalette()`` / ``QFont()``, which copy the application's
    current palette and font — the themed app's — so a first apply looked
    unchanged and its setters were skipped (the composer's suite after leg
    u1x3: two failures). The constructor asserts the difference."""

    _STATE = {"setPalette": "palette", "setFont": "font", "setStyleSheet": "styleSheet"}

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from PySide6.QtGui import QColor, QFont, QPalette
        from PySide6.QtWidgets import QApplication

        self.calls: list[tuple[str, Any]] = []
        self.state: dict[str, Any] = {
            "palette": QPalette(QColor("#7f007f")),
            "font": QFont("Courier New", 31),
            "styleSheet": "",
        }
        for tokens in (theme.LIGHT, theme.DARK):
            assert self.state["palette"] != theme.build_palette(tokens)
            assert self.state["font"].families() != list(tokens.family)
            assert self.state["font"].pointSize() != tokens.size_body
            assert self.state["styleSheet"] != theme.render_qss(tokens)
        for setter in ("setStyle", *self._STATE):
            monkeypatch.setattr(QApplication, setter, self._setter(setter))
        for getter in self._STATE.values():
            monkeypatch.setattr(QApplication, getter, self._getter(getter))

    def _setter(self, name: str) -> Any:
        def setter(*args: Any, **kwargs: Any) -> None:
            value = args[-1]
            self.calls.append((name, value))
            if name in self._STATE:
                self.state[self._STATE[name]] = value

        return setter

    def _getter(self, name: str) -> Any:
        def getter(*args: Any, **kwargs: Any) -> Any:
            return self.state[name]

        return getter

    def names(self) -> list[str]:
        return [name for name, _ in self.calls]


def _colour_fields() -> list[str]:
    return [f.name for f in fields(theme.Tokens) if isinstance(getattr(theme.LIGHT, f.name), str)]


# --- the tokens -----------------------------------------------------------------------


class TestTokens:
    @pytest.mark.parametrize("tokens", [theme.LIGHT, theme.DARK], ids=["light", "dark"])
    def test_every_colour_role_is_a_hex_colour(self, tokens: theme.Tokens) -> None:
        for name in _colour_fields():
            assert re.fullmatch(r"#[0-9a-f]{6}", getattr(tokens, name)), name
        assert tokens.family and all(tokens.family)

    def test_the_colour_roles_are_the_designed_ones(self) -> None:
        # D1's roles (plus the disabled text and the hover/pressed states every
        # coloured control needs, C13).
        assert set(_colour_fields()) == {
            "canvas",
            "surface",
            "surface_alt",
            "border",
            "text",
            "text_muted",
            "text_disabled",
            "accent",
            "accent_hover",
            "on_accent",
            "danger",
            "warning",
            "success",
            "focus",
            "link",
            "rec",
            "paused",
            "hover",
            "pressed",
        }

    def test_light_and_dark_differ_in_their_surfaces_and_text(self) -> None:
        for name in ("canvas", "surface", "surface_alt", "border", "text", "hover", "pressed"):
            assert getattr(theme.LIGHT, name) != getattr(theme.DARK, name), name

    def test_light_and_dark_agree_on_type_spacing_and_radii(self) -> None:
        colours = set(_colour_fields())
        for f in fields(theme.Tokens):
            if f.name not in colours:
                assert getattr(theme.LIGHT, f.name) == getattr(theme.DARK, f.name), f.name

    @pytest.mark.parametrize("tokens", [theme.LIGHT, theme.DARK], ids=["light", "dark"])
    def test_danger_and_rec_stay_red(self, tokens: theme.Tokens) -> None:
        from PySide6.QtGui import QColor

        for name in ("danger", "rec"):
            colour = QColor(getattr(tokens, name))
            assert colour.red() > colour.green() and colour.red() > colour.blue(), name

    def test_tokens_for_names_each_scheme(self) -> None:
        assert theme.tokens_for("light") is theme.LIGHT
        assert theme.tokens_for("dark") is theme.DARK


# --- the stylesheet -------------------------------------------------------------------


@pytest.mark.parametrize("tokens", [theme.LIGHT, theme.DARK], ids=["light", "dark"])
class TestStylesheet:
    def test_every_role_variant_and_shell_id_has_rules(self, tokens: theme.Tokens) -> None:
        qss = theme.render_qss(tokens)
        for role in theme.ROLES:
            assert f'QLabel[role="{role}"]' in qss, role
        for variant in theme.VARIANTS:
            assert f'QPushButton[variant="{variant}"]' in qss, variant
        for object_id in theme.SHELL_IDS:
            assert f"#{object_id}" in qss, object_id
        assert 'QFrame[card="true"]' in qss

    def test_every_coloured_control_has_a_disabled_state(self, tokens: theme.Tokens) -> None:
        """C13: a control the sheet colours still reads as disabled."""
        qss = theme.render_qss(tokens)
        for control in (
            "QPushButton",
            'QPushButton[variant="primary"]',
            'QPushButton[variant="danger"]',
            'QPushButton[variant="link"]',
            "QLineEdit",
            "QPlainTextEdit",
            "QComboBox",
            "QListWidget",
            "QGroupBox::title",
            "QMenu::item",
            "QTabBar::tab",
            "QProgressBar",
            "QToolButton#railButton",
        ):
            assert f"{control}:disabled" in qss, control

    def test_every_focusable_control_the_sheet_borders_shows_focus(
        self, tokens: theme.Tokens
    ) -> None:
        """Review round 4: a border the sheet sets would otherwise hide where
        the keyboard focus is (and lists drop Qt's item focus rectangle)."""
        qss = theme.render_qss(tokens)
        for control in (
            "QPushButton",
            'QPushButton[variant="primary"]',
            'QPushButton[variant="danger"]',
            'QPushButton[variant="link"]',
            "QLineEdit",
            "QPlainTextEdit",
            "QComboBox",
            "QListWidget",
            "QToolButton#railButton",
        ):
            assert f"{control}:focus" in qss, control

    def test_a_focused_controls_border_differs_from_its_unfocused_border(
        self, tokens: theme.Tokens
    ) -> None:
        """Peer round 6 PR-LOW-001: a focus rule whose colour equals the
        control's own border shows nothing (light's accent IS its focus
        colour, so the primary button's focus border used to vanish)."""
        qss = theme.render_qss(tokens)
        for control in (
            "QPushButton",
            'QPushButton[variant="primary"]',
            'QPushButton[variant="danger"]',
            'QPushButton[variant="link"]',
            "QLineEdit",
            "QPlainTextEdit",
            "QComboBox",
            "QListWidget",
            "QToolButton#railButton",
        ):
            unfocused = _border_colour(_declarations(qss, control))
            focused = _border_colour(_declarations(qss, f"{control}:focus"))
            assert unfocused is not None and focused is not None, control
            assert focused != unfocused, control

    def test_a_disabled_control_keeps_no_enabled_selection_colours(
        self, tokens: theme.Tokens
    ) -> None:
        """Peer round 6 PR-LOW-002 (C13): the sheet's selection colours
        out-rank the disabled palette, so each has a disabled counterpart."""
        qss = theme.render_qss(tokens)
        selected = _declarations(qss, "QListWidget::item:selected")
        disabled_row = _declarations(qss, "QListWidget::item:selected:disabled")
        assert disabled_row["background-color"] != selected["background-color"]
        assert disabled_row["color"] == tokens.text_disabled
        for control in ("QLineEdit", "QPlainTextEdit", "QTextEdit", "QComboBox"):
            enabled = _declarations(qss, control)
            disabled = _declarations(qss, f"{control}:disabled")
            assert disabled["selection-background-color"] != (
                enabled["selection-background-color"]
            ), control
            assert disabled["selection-color"] == tokens.text_disabled, control

    def test_lists_keep_a_usable_height(self, tokens: theme.Tokens) -> None:
        """C6: the Practitioner tab's scroll test reads ``height() >= 40``."""
        lines = theme.render_qss(tokens).splitlines()
        [rule] = [line for line in lines if line.startswith("QListWidget {")]
        assert "min-height: 48px;" in rule

    def test_the_sheet_is_well_formed_and_uses_this_schemes_values(
        self, tokens: theme.Tokens
    ) -> None:
        qss = theme.render_qss(tokens)
        assert qss.count("{") == qss.count("}")
        for line in qss.splitlines():
            assert re.fullmatch(r"[^{}]+ \{ [^{}]+; \}", line), line
        assert tokens.danger in qss and tokens.canvas in qss and tokens.accent in qss
        widths = [int(value) for value in re.findall(r"min-width: (\d+)px", qss)]
        assert widths and max(widths) < 400  # well under the 1200 px window


class _StyleCalls(ast.NodeVisitor):
    """Every call named ``set_role`` / ``set_variant`` / ``mark_card`` /
    ``setObjectName`` in one file, with its enclosing ``Class.function``."""

    _NAMES = {"set_role", "set_variant", "mark_card", "setObjectName"}

    def __init__(self) -> None:
        self.scope: list[str] = []
        self.calls: list[tuple[str, str, ast.Call]] = []

    def _scoped(self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_ClassDef = _scoped
    visit_FunctionDef = _scoped
    visit_AsyncFunctionDef = _scoped

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        name = (
            func.id
            if isinstance(func, ast.Name)
            else func.attr
            if isinstance(func, ast.Attribute)
            else None
        )
        if name in self._NAMES:
            self.calls.append((name, ".".join(self.scope), node))
        self.generic_visit(node)


def _style_calls() -> list[tuple[str, str, str, ast.Call]]:
    found: list[tuple[str, str, str, ast.Call]] = []
    for path in _package_files():
        relative = _relative(path)
        if relative == THEME_FILE:
            continue
        visitor = _StyleCalls()
        visitor.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        found += [(relative, scope, name, call) for name, scope, call in visitor.calls]
    return found


class TestTheCodeAndTheSheetAgree:
    def test_every_role_variant_card_and_object_name_used_has_its_rule(self) -> None:
        """D13: derived from the whole package — every literal the code passes
        is a known value with its selector in BOTH schemes' sheets; a
        non-literal role or variant fails (it could not be checked)."""
        sheets = [theme.render_qss(theme.LIGHT), theme.render_qss(theme.DARK)]
        roles_used: set[str] = set()
        for relative, scope, name, call in _style_calls():
            where = f"{relative} {scope} {name}"
            if name == "mark_card":
                selector = 'QFrame[card="true"]'
            else:
                argument = call.args[-1] if call.args else None
                literal = isinstance(argument, ast.Constant) and isinstance(argument.value, str)
                if name == "setObjectName":
                    if not literal:
                        assert (relative, scope) in _NON_LITERAL_OBJECT_NAMES, where
                        continue
                    assert isinstance(argument, ast.Constant)
                    selector = f"#{argument.value}"
                else:
                    assert literal and len(call.args) == 2, where
                    assert isinstance(argument, ast.Constant)
                    value = argument.value
                    if name == "set_role":
                        assert value in theme.ROLES, where
                        roles_used.add(value)
                        selector = f'QLabel[role="{value}"]'
                    else:
                        assert value in theme.VARIANTS, where
                        selector = f'QPushButton[variant="{value}"]'
            for sheet in sheets:
                assert selector in sheet, where
        # The 16 retired ad-hoc styles (Task 1.3) became these roles.
        assert {"danger", "error", "strong"} <= roles_used

    def test_no_colour_weight_or_widget_stylesheet_outside_the_theme(self) -> None:
        """D1/D13: values live in ``ui/theme.py`` — the whole package is
        searched, only that one file is exempt."""
        offenders: list[str] = []
        for path in _package_files():
            relative = _relative(path)
            if relative == THEME_FILE:
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if _HEX_COLOUR.search(line) or _STYLE_TEXT.search(line):
                    offenders.append(f"{relative}:{number}")
        assert offenders == []

    def test_no_visual_value_or_setter_outside_the_theme(self) -> None:
        """D1 (review round 4): beyond the text search above, no module but
        ``ui/theme.py`` imports Qt's value classes for colour, font, palette or
        style, or calls a widget- or application-wide visual setter — so a
        named colour (``QColor("red")``) or a per-widget font cannot slip past
        the ``#rrggbb`` search either."""
        value_classes = {"QColor", "QFont", "QPalette", "QBrush", "QStyleFactory"}
        setters = {
            "setStyleSheet",
            "setPalette",
            "setFont",
            "setStyle",
            "setForeground",
            "setBackground",
            "setAutoFillBackground",
        }
        offenders: list[str] = []
        for path in _package_files():
            relative = _relative(path)
            if relative == THEME_FILE:
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("PySide6"):
                    offenders += [
                        f"{relative}:{node.lineno} imports {alias.name}"
                        for alias in node.names
                        if alias.name in value_classes
                    ]
                elif isinstance(node, ast.Attribute) and node.attr in value_classes | setters:
                    offenders.append(f"{relative}:{node.lineno} uses {node.attr}")
        assert offenders == []

    def test_the_theme_is_applied_only_from_app_main(self) -> None:
        """D2/C9: ``app.py`` applies the theme; ``ui/note.py`` and
        ``ui/main_window.py`` (and every other module) never do."""
        callers: set[str] = set()
        for path in _package_files():
            relative = _relative(path)
            if relative == THEME_FILE:
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute | ast.Name)
                    and (node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id)
                    in {"apply_theme", "ensure_applied", "force_scheme"}
                ):
                    callers.add(relative)
        assert callers == {"app.py"}


# --- applying it ----------------------------------------------------------------------


class TestApply:
    def test_apply_sets_fusion_once_the_font_and_the_marker(
        self, qapp: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from PySide6.QtWidgets import QStyleFactory

        created: list[str] = []
        real_create = QStyleFactory.create

        def spy(key: str) -> Any:
            created.append(key)
            return real_create(key)

        monkeypatch.setattr(theme.QStyleFactory, "create", spy)
        surface = _FakeAppSurface(monkeypatch)
        saved = qapp.property(theme.SCHEME_PROPERTY)
        qapp.setProperty(theme.SCHEME_PROPERTY, None)
        try:
            tokens = theme.apply_theme(qapp, "light")
            assert tokens is theme.LIGHT
            assert created == ["Fusion"]
            # D2's order: style, palette, font, stylesheet.
            assert surface.names() == ["setStyle", "setPalette", "setFont", "setStyleSheet"]
            font = surface.state["font"]
            assert font.families()[0] == theme.LIGHT.family[0]
            assert font.pointSize() == theme.LIGHT.size_body
            assert surface.state["styleSheet"] == theme.render_qss(theme.LIGHT)
            assert qapp.property(theme.SCHEME_PROPERTY) == "light"
            theme.apply_theme(qapp, "light")
            assert created == ["Fusion"]  # the style is set once
            assert len(surface.calls) == 4  # and an equal repeat sets nothing
        finally:
            qapp.setProperty(theme.SCHEME_PROPERTY, saved)

    def test_force_scheme_switches_light_dark_light(
        self, qapp: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D3, C14 (peer round 6 PR-LOW-003): BOTH schemes injected through
        the seam, light → dark → light, whatever the host reports; each
        switch sets that scheme's palette and stylesheet and announces its
        tokens; the font is set once."""
        from PySide6.QtGui import QPalette

        surface = _FakeAppSurface(monkeypatch)
        announced: list[object] = []

        def record(tokens: object) -> None:
            announced.append(tokens)

        bus = theme.theme_bus()
        bus.changed.connect(record)
        saved = qapp.property(theme.SCHEME_PROPERTY)
        try:
            for scheme, tokens in (
                ("light", theme.LIGHT),
                ("dark", theme.DARK),
                ("light", theme.LIGHT),
            ):
                theme.force_scheme(scheme)
                assert theme.apply_theme(qapp) is tokens
                assert qapp.property(theme.SCHEME_PROPERTY) == scheme
        finally:
            bus.changed.disconnect(record)
            theme.force_scheme(None)
            qapp.setProperty(theme.SCHEME_PROPERTY, saved)
        windows = [
            value.color(QPalette.ColorRole.Window).name()
            for name, value in surface.calls
            if name == "setPalette"
        ]
        assert windows == [theme.LIGHT.canvas, theme.DARK.canvas, theme.LIGHT.canvas]
        sheets = [value for name, value in surface.calls if name == "setStyleSheet"]
        assert sheets == [
            theme.render_qss(theme.LIGHT),
            theme.render_qss(theme.DARK),
            theme.render_qss(theme.LIGHT),
        ]
        assert surface.names().count("setFont") == 1
        assert announced == [theme.LIGHT, theme.DARK, theme.LIGHT]

    def test_an_existing_label_restyles_in_place_light_dark_light(self, qapp: Any) -> None:
        """Flow 3: a widget already built follows a sheet change without being
        re-created. Measured on its own small tree (the sheet set on a
        container), never by restyling the whole session's widgets."""
        from PySide6.QtGui import QPalette
        from PySide6.QtWidgets import QLabel, QWidget

        container = QWidget()
        label = QLabel("text", container)
        theme.set_role(label, "danger")
        seen: list[str] = []
        for tokens in (theme.LIGHT, theme.DARK, theme.LIGHT):
            container.setStyleSheet(theme.render_qss(tokens))
            label.ensurePolished()
            seen.append(label.palette().color(QPalette.ColorRole.WindowText).name())
        assert seen == [theme.LIGHT.danger, theme.DARK.danger, theme.LIGHT.danger]
        container.deleteLater()

    def test_the_palette_has_a_disabled_group(self) -> None:
        from PySide6.QtGui import QPalette

        palette = theme.build_palette(theme.LIGHT)
        disabled = QPalette.ColorGroup.Disabled
        text = palette.color(disabled, QPalette.ColorRole.WindowText).name()
        assert text == theme.LIGHT.text_disabled
        assert palette.color(QPalette.ColorRole.WindowText).name() == theme.LIGHT.text

    def test_ensure_applied_is_idempotent(self, qapp: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        """One application, one theme, one connection — however often called."""
        applied: list[object] = []
        followed: list[object] = []

        def stamping(app: Any, scheme: object = None) -> None:
            # As the real ``apply_theme`` does, minus restyling the session's
            # widgets: it stamps the marker idempotency keys on.
            applied.append(app)
            app.setProperty(theme.SCHEME_PROPERTY, "light")

        monkeypatch.setattr(theme, "apply_theme", stamping)
        monkeypatch.setattr(theme, "_follow_scheme_changes", followed.append)
        names = (theme.SCHEME_PROPERTY, theme._FOLLOWING_PROPERTY)
        saved = {name: qapp.property(name) for name in names}
        for name in names:
            qapp.setProperty(name, None)
        try:
            for _ in range(3):
                theme.ensure_applied(qapp)
            assert followed == [qapp]
            assert applied == [qapp]
        finally:
            for name, value in saved.items():
                qapp.setProperty(name, value)

    def test_ensure_applied_without_an_application_does_nothing(self) -> None:
        theme.ensure_applied(None)

    def test_a_repeat_of_the_same_scheme_restyles_nothing(
        self, qapp: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Each application-wide setter restyles every live widget, so
        ``apply_theme`` skips a value the application already has."""
        from PySide6.QtWidgets import QApplication

        current = qapp.property(theme.SCHEME_PROPERTY)
        assert current in ("light", "dark")
        calls: list[str] = []
        for setter in ("setStyle", "setPalette", "setFont", "setStyleSheet"):
            monkeypatch.setattr(
                QApplication, setter, lambda *args, _name=setter, **kwargs: calls.append(_name)
            )
        assert theme.apply_theme(qapp, current) is theme.tokens_for(current)
        assert calls == []

    def test_a_scheme_change_applies_to_the_current_application(
        self, qapp: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D3: the ``colorSchemeChanged`` slot looks the application up (it
        holds no reference to it) and re-applies the theme there."""
        applied: list[object] = []
        monkeypatch.setattr(theme, "apply_theme", lambda app, scheme=None: applied.append(app))
        theme._on_scheme_changed(object())
        assert applied == [qapp]


class TestRolesAndVariants:
    def test_a_role_is_readable_after_the_repolish(self, qapp: Any) -> None:
        from PySide6.QtWidgets import QLabel

        label = QLabel("text")
        theme.set_role(label, "muted")
        assert label.property("role") == "muted"
        with pytest.raises(ValueError):
            theme.set_role(label, "loud")
        label.deleteLater()

    def test_a_variant_and_a_card_are_readable(self, qapp: Any) -> None:
        from PySide6.QtWidgets import QFrame, QPushButton

        button = QPushButton("Save note")
        theme.set_variant(button, "primary")
        assert button.property("variant") == "primary"
        with pytest.raises(ValueError):
            theme.set_variant(button, "shiny")
        frame = QFrame()
        theme.mark_card(frame)
        assert frame.property("card") is True
        button.deleteLater()
        frame.deleteLater()

    def test_the_link_button_keeps_its_flat_look_and_hand_cursor(self) -> None:
        """Task 1.3: ``change_role_button`` is the link variant, still flat,
        still the hand cursor."""
        text = (PACKAGE / "ui" / "transcript.py").read_text(encoding="utf-8")
        assert 'set_variant(self.change_role_button, "link")' in text
        assert "self.change_role_button.setFlat(True)" in text
        assert "self.change_role_button.setCursor(Qt.CursorShape.PointingHandCursor)" in text


# --- app.main(): themed before the guard (D2, PR-MED-001) -----------------------------


class _Proceeded(Exception):
    pass


@pytest.mark.parametrize(
    ("state", "after_guard"),
    [("acquired", "proceeded"), ("already_running", "running"), ("unavailable", "cannot")],
)
def test_main_themes_the_app_before_the_guard_and_its_refusal_boxes(
    state: str, after_guard: str, qapp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each guard outcome: the application already carries the theme marker
    when the guard runs and when its refusal box (or, once acquired, the next
    start-up step) is reached. The marker is cleared first, so the check is
    of ``main()``'s own call, not the suite's fixture; ``apply_theme`` is a
    stub that stamps it (``TestApply`` tests the real one), so the test
    restyles none of the session's widgets."""
    import logging

    from PySide6.QtWidgets import QApplication

    from scribe_desktop import app as app_module

    seen: list[tuple[str, object]] = []

    def marker() -> object:
        return qapp.property(theme.SCHEME_PROPERTY)

    def guard(name: object = None, lock_path: object = None) -> Any:
        seen.append(("guard", marker()))
        return app_module.InstanceExclusion(state)

    def proceeded(**kwargs: object) -> Any:
        seen.append(("proceeded", marker()))
        raise _Proceeded

    monkeypatch.setattr(
        app_module, "setup_logging", lambda name: logging.getLogger("test-theme-order")
    )
    # Privacy-professional-controls Task 4.1 (C6): never this process's hooks.
    monkeypatch.setattr(app_module, "install_exception_hooks", lambda logger: lambda: None)
    monkeypatch.setattr(app_module, "apply_offline_env", lambda: None)
    monkeypatch.setattr(app_module, "assert_offline_env", lambda: None)
    monkeypatch.setattr(
        app_module, "QApplication", lambda argv: QApplication.instance() or QApplication(argv)
    )
    monkeypatch.setattr(app_module, "acquire_instance_exclusion", guard)
    monkeypatch.setattr(
        app_module, "_show_already_running_warning", lambda: seen.append(("running", marker()))
    )
    monkeypatch.setattr(
        app_module, "_show_cannot_start_warning", lambda: seen.append(("cannot", marker()))
    )
    monkeypatch.setattr(app_module, "ImportWarmup", proceeded)

    def stamping(app: Any, scheme: object = None) -> None:
        seen.append(("themed", None))
        app.setProperty(theme.SCHEME_PROPERTY, "light")

    monkeypatch.setattr(theme, "apply_theme", stamping)
    saved = marker()
    qapp.setProperty(theme.SCHEME_PROPERTY, None)
    try:
        if state == "acquired":
            with pytest.raises(_Proceeded):
                app_module.main(["scribe-app"])
        else:
            app_module.main(["scribe-app"])
    finally:
        qapp.setProperty(theme.SCHEME_PROPERTY, saved)
    assert [step for step, _ in seen] == ["themed", "guard", after_guard]
    assert [value for _, value in seen[1:]] == ["light", "light"]
