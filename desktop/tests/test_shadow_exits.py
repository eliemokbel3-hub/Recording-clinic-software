"""Pilot plan Critical Constraint 3 (Task 1.5): every path that carries note
text out is gated in shadow mode — and a NEW one fails here until it is.

Read from the source (no Qt, no clipboard, except the two offscreen list
and combo-box tests at the end):

- the callers of ``ui.note._place_note_text`` (THE placement of note text on
  the clipboard) are exactly the four known ones, each passing ``shadow=``;
- the widgets in ``ui/note.py`` and ``ui/past_sessions.py`` that can hold
  text a user could select (plain-text and line edits, and their
  subclasses) are exactly the known ones, each with its gate named below;
- no text-interaction flag that makes text selectable is set anywhere in
  the package except ``NoteScreen._apply_copy_binding`` (whose predicate is
  ``_copy_allowed``, which refuses a shadow note);
- no Qt call that puts anything on the clipboard or starts a drag
  (``clipboard()``, ``QMimeData``, ``setMimeData``, ``QDrag``) is made
  anywhere in the package except inside the placement (review round 22);
- every list is ``ui.lists.NoCopyListWidget`` and every combo box
  ``ui.lists.NoCopyComboBox``, whose Copy shortcut reaches no clipboard; no
  other Qt item view is built and no popup view replaced; no widget turns
  drag on (review rounds 23–24);
- every construction of a recording's mode passes it explicitly — the
  Start call, the two ``RecordingSession`` and the ``EncounterRecord``
  constructions, the line editor and the four live Completes — so a new one
  cannot fall back on a ``normal`` default (review rounds 22 and 23);
- THE one send to Cliniko (``ClinikoCall.write_draft_note``) is reached
  only from ``draft_write.send_write``, which takes a ``PreparedWrite`` that
  only ``prepare_write`` makes, after refusing a shadow session (pinned in
  ``test_draft_write.py``).

Sites are COUNTED, not just located (peer round 9 PR-MED-A01), and each
count is proven to catch an in-memory added site.
"""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path
from typing import Final

import pytest

import scribe_desktop

PACKAGE = Path(scribe_desktop.__file__).resolve().parent
UI = PACKAGE / "ui"

# The text-holding widget classes Qt offers (a QLabel is not here: the app's
# labels are plain, non-selectable text, pinned by the flag check below).
_TEXT_WIDGETS = frozenset({"QPlainTextEdit", "QTextEdit", "QTextBrowser", "QLineEdit"})


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _scoped_nodes(tree: ast.Module) -> list[tuple[str, ast.AST]]:
    """Every node with its enclosing ``Class.function`` (or function) name."""
    found: list[tuple[str, ast.AST]] = []

    def walk(node: ast.AST, scope: tuple[str, ...]) -> None:
        for child in ast.iter_child_nodes(node):
            inner = scope
            if isinstance(child, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
                inner = (*scope, child.name)
            found.append((".".join(inner), child))
            walk(child, inner)

    walk(tree, ())
    return found


def _callee(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _relative(path: Path) -> str:
    return path.relative_to(PACKAGE).as_posix()


# Peer round 9 PR-MED-A01: the expected sites below are COUNTED — a second
# widget or call at a location already listed fails as surely as a new
# location does.
_PLACEMENT_CALLERS: Counter[tuple[str, str]] = Counter(
    {
        ("ui/note.py", "_NotePanel.copy_selection"): 1,  # gated by `_copy_allowed`
        ("ui/note.py", "NoteScreen._copy_note"): 1,  # refused by name first
        ("ui/past_sessions.py", "PastSessionsScreen.on_copy"): 1,  # `_copy_reason`
        # Review round 22 MED-001: the line editor's own Copy and Cut,
        # refused before the placement for a shadow recording.
        ("ui/note.py", "_LineEditor._place_selection"): 1,
    }
)
_BUILT_WIDGETS: Counter[tuple[str, str, str]] = Counter(
    {
        # The transcript: never selectable.
        ("ui/note.py", "NoteScreen.__init__", "QPlainTextEdit"): 1,
        ("ui/note.py", "NoteScreen.__init__", "_NotePanel"): 1,
        ("ui/note.py", "NoteScreen._build_editor_row", "_LineEditor"): 1,
        # Every Past-sessions panel: display-only, never selectable.
        ("ui/past_sessions.py", "_display_panel", "QPlainTextEdit"): 1,
    }
)
# THE one send, in the one function that takes only a `PreparedWrite` —
# which only `prepare_write` makes, after refusing a shadow session.
_SEND_CALLERS: Counter[tuple[str, str]] = Counter({("draft_write.py", "send_write"): 1})


def _placement_calls(sources: dict[str, ast.Module]) -> list[tuple[str, str, ast.Call]]:
    return [
        (relative, scope, node)
        for relative, tree in sources.items()
        for scope, node in _scoped_nodes(tree)
        if isinstance(node, ast.Call) and _callee(node) == "_place_note_text"
    ]


def _built_widgets(sources: dict[str, ast.Module]) -> Counter[tuple[str, str, str]]:
    built: Counter[tuple[str, str, str]] = Counter()
    for relative, tree in sources.items():
        local = _local_text_widgets(tree)
        for scope, node in _scoped_nodes(tree):
            if isinstance(node, ast.Call):
                name = _callee(node)
                if name in _TEXT_WIDGETS or name in local:
                    built[(relative, scope, str(name))] += 1
    return built


def _send_callers(sources: dict[str, ast.Module]) -> Counter[tuple[str, str]]:
    return Counter(
        (relative, scope)
        for relative, tree in sources.items()
        for scope, node in _scoped_nodes(tree)
        if isinstance(node, ast.Call) and _callee(node) == "write_draft_note"
    )


def _local_text_widgets(tree: ast.Module) -> set[str]:
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        and any(isinstance(b, ast.Name) and b.id in _TEXT_WIDGETS for b in node.bases)
    }


def _package_sources() -> dict[str, ast.Module]:
    return {_relative(path): _tree(path) for path in sorted(PACKAGE.rglob("*.py"))}


def _tab_sources() -> dict[str, ast.Module]:
    return {_relative(path): _tree(path) for path in (UI / "note.py", UI / "past_sessions.py")}


def _with_extra(
    sources: dict[str, ast.Module], relative: str, function: str, statement: str
) -> dict[str, ast.Module]:
    """``sources`` with ``statement`` appended to ``function`` in ``relative``
    (a ``Class.method`` or a module-level function), parsed afresh — the
    in-memory mutation each guard must catch."""
    tree = ast.parse(ast.unparse(sources[relative]))
    *owner, name = function.split(".")
    body: list[ast.stmt] = tree.body
    for part in owner:
        [klass] = [n for n in body if isinstance(n, ast.ClassDef) and n.name == part]
        body = klass.body
    [target] = [n for n in body if isinstance(n, ast.FunctionDef) and n.name == name]
    target.body.extend(ast.parse(statement).body)
    return {**sources, relative: tree}


def test_the_placement_has_exactly_the_known_callers_and_each_passes_shadow() -> None:
    calls = _placement_calls(_package_sources())
    assert Counter((relative, scope) for relative, scope, _ in calls) == _PLACEMENT_CALLERS
    for _relative_path, _scope, call in calls:
        assert [kw.arg for kw in call.keywords] == ["shadow"]


def test_a_second_placement_at_a_known_caller_fails_the_count() -> None:
    sources = _with_extra(
        _package_sources(),
        "ui/note.py",
        "NoteScreen._copy_note",
        "_place_note_text('x', shadow=False)",
    )
    found = Counter((relative, scope) for relative, scope, _ in _placement_calls(sources))
    assert found != _PLACEMENT_CALLERS
    assert found[("ui/note.py", "NoteScreen._copy_note")] == 2


def test_every_text_widget_in_the_two_tabs_is_a_known_gated_one() -> None:
    subclasses: set[tuple[str, str, str]] = set()
    sources = _tab_sources()
    for relative, tree in sources.items():
        local = _local_text_widgets(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in local:
                [base] = [b.id for b in node.bases if isinstance(b, ast.Name)]
                subclasses.add((relative, node.name, base))
    assert subclasses == {
        # The editor: Copy and Cut through the placement, refused (and drag
        # off) in shadow or with the copy flag off (`_LineEditor._refused`).
        ("ui/note.py", "_LineEditor", "QLineEdit"),
        # The note body: display-only unless `_copy_allowed`; its copies go
        # through the placement.
        ("ui/note.py", "_NotePanel", "QPlainTextEdit"),
    }
    assert _built_widgets(sources) == _BUILT_WIDGETS


def test_a_second_widget_at_a_known_site_fails_the_count() -> None:
    """PR-MED-A01's case: another default-selectable ``QPlainTextEdit()`` in
    ``NoteScreen.__init__`` — the transcript's own site — is caught."""
    sources = _with_extra(
        _tab_sources(), "ui/note.py", "NoteScreen.__init__", "extra = QPlainTextEdit()"
    )
    built = _built_widgets(sources)
    assert built != _BUILT_WIDGETS
    assert built[("ui/note.py", "NoteScreen.__init__", "QPlainTextEdit")] == 2


def test_text_is_made_selectable_only_by_the_copy_binding() -> None:
    """Across the whole package (review round 22: it read the two tabs only)."""
    selectable = {
        "TextSelectableByMouse",
        "TextSelectableByKeyboard",
        "TextEditorInteraction",
        "TextBrowserInteraction",
        "TextEditable",
    }
    where: set[tuple[str, str]] = set()
    for relative, tree in _package_sources().items():
        for scope, node in _scoped_nodes(tree):
            if isinstance(node, ast.Attribute) and node.attr in selectable:
                where.add((relative, scope))
    assert where == {("ui/note.py", "NoteScreen._apply_copy_binding")}


# Review round 22: the Qt calls that place anything on the clipboard or start
# a drag, COUNTED across the whole package — only the placement makes them.
_CLIPBOARD_CALLEES = frozenset({"clipboard", "QMimeData", "setMimeData", "QDrag"})
_CLIPBOARD_CALLS: Counter[tuple[str, str, str]] = Counter(
    {
        ("ui/note.py", "_place_note_text", "clipboard"): 1,
        ("ui/note.py", "_place_note_text", "QMimeData"): 1,
        ("ui/note.py", "_place_note_text", "setMimeData"): 1,
    }
)


def _clipboard_calls(sources: dict[str, ast.Module]) -> Counter[tuple[str, str, str]]:
    found: Counter[tuple[str, str, str]] = Counter()
    for relative, tree in sources.items():
        for scope, node in _scoped_nodes(tree):
            if isinstance(node, ast.Call) and (name := _callee(node)) in _CLIPBOARD_CALLEES:
                found[(relative, scope, str(name))] += 1
    return found


def test_only_the_placement_touches_the_clipboard_or_starts_a_drag() -> None:
    assert _clipboard_calls(_package_sources()) == _CLIPBOARD_CALLS


@pytest.mark.parametrize(
    "statement", ["QApplication.clipboard().setText('x')", "QDrag(self).exec()"]
)
def test_a_clipboard_write_or_drag_elsewhere_fails_the_count(statement: str) -> None:
    sources = _with_extra(
        _package_sources(), "ui/past_sessions.py", "PastSessionsScreen.on_copy", statement
    )
    assert _clipboard_calls(sources) != _CLIPBOARD_CALLS


# Review round 22: every construction of a recording's mode names it — the
# defaults (``normal``) exist for tests building records, so a NEW production
# construction relying on one would silently be a normal recording.
_START: Final = "_controller.start"
_MODE_KEYWORD: Final[dict[str, str]] = {
    "RecordingSession": "mode",
    "EncounterRecord": "mode",
    "_LineEditor": "shadow",
    "_complete_locked": "mode",
    _START: "mode",
}
_MODE_CONSTRUCTIONS: Counter[tuple[str, str]] = Counter(
    {
        ("session.py", "RecordingSession"): 2,  # Start; adopt_queued
        ("session.py", "EncounterRecord"): 1,  # Start's encounter.enc
        ("ui/main_window.py", "EncounterRecord"): 1,  # `_open_adopted`'s checkout record
        ("ui/note.py", "_LineEditor"): 1,
        # Round 23: the four live Completes pass the live mode (the kept
        # label is forced shadow by it); `complete_recovered` has no live
        # session — its label comes from the encounter record's mode.
        ("session.py", "_complete_locked"): 5,
        ("ui/session_screen.py", _START): 1,  # the one Start funnel
    }
)
# The one construction that names no mode, by design (above).
_MODELESS: Final = [("session.py", "_complete_locked")]


def _mode_constructions(
    sources: dict[str, ast.Module], keywords: dict[str, str] = _MODE_KEYWORD
) -> list[tuple[str, str, ast.Call]]:
    """Every call to a callee of ``keywords`` (and every Start, when the map
    names ``_START``)."""
    found: list[tuple[str, str, ast.Call]] = []
    for relative, tree in sources.items():
        for _scope, node in _scoped_nodes(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _callee(node)
            func = node.func
            if name in keywords:
                found.append((relative, str(name), node))
            elif _START in keywords and name == "start" and (
                # Round 23: any `.start(` carrying a consent is a Start too.
                "consent" in [kw.arg for kw in node.keywords]
                or (
                    isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Attribute)
                    and func.value.attr == "_controller"
                )
            ):
                found.append((relative, _START, node))
    return found


def _without_mode(
    found: list[tuple[str, str, ast.Call]], keywords: dict[str, str] = _MODE_KEYWORD
) -> list[tuple[str, str]]:
    """The calls in ``found`` that do not name their ``keywords`` keyword."""
    return [
        (relative, name)
        for relative, name, call in found
        if keywords[name] not in [kw.arg for kw in call.keywords]
    ]


def test_every_construction_of_a_mode_names_it() -> None:
    found = _mode_constructions(_package_sources())
    assert Counter((relative, name) for relative, name, _ in found) == _MODE_CONSTRUCTIONS
    assert _without_mode(found) == _MODELESS


# Development-recordings plan Task 1.5 (C3, D2): every construction of a
# recording, its encounter record, the Start call and the audit row's
# ``begin`` names the DEVELOPMENT consent explicitly — the defaults (None, not
# kept) exist for tests building records, so a new production site relying on
# one would silently drop a consent, or (after a refactor) keep a recording
# nobody decided to keep. No exemptions. Task 2.1 adds
# ``_complete_locked`` → ``kept`` to this map in its own commit.
_CONSENT_KEYWORD: Final[dict[str, str]] = {
    "RecordingSession": "development_consent",
    "EncounterRecord": "development_consent",
    _START: "development_consent",
    "begin": "development_consent_version",
}
_CONSENT_CONSTRUCTIONS: Counter[tuple[str, str]] = Counter(
    {
        ("session.py", "RecordingSession"): 2,  # Start; adopt_queued (from the record)
        ("session.py", "EncounterRecord"): 1,  # Start's encounter.enc
        ("ui/main_window.py", "EncounterRecord"): 1,  # `_open_adopted`'s checkout record
        ("ui/session_screen.py", _START): 1,  # the one Start funnel
        ("session.py", "begin"): 1,  # Start's audit row
    }
)


def test_every_construction_names_its_development_consent() -> None:
    found = _mode_constructions(_package_sources(), _CONSENT_KEYWORD)
    assert Counter((relative, name) for relative, name, _ in found) == _CONSENT_CONSTRUCTIONS
    assert _without_mode(found, _CONSENT_KEYWORD) == []


@pytest.mark.parametrize(
    ("statement", "missing"),
    [
        (
            "RecordingSession(key_reference='key.dpapi', consent=None, mode=None)",
            "RecordingSession",
        ),
        ("EncounterRecord(consent=None, mode=None)", "EncounterRecord"),
        ("other.start(0, consent=None, mode=None)", _START),
        ("self._audit.begin('x', consent=None, mode=None)", "begin"),
    ],
)
def test_a_site_omitting_the_development_consent_fails(statement: str, missing: str) -> None:
    sources = _with_extra(_package_sources(), "session.py", "SessionController.discard", statement)
    found = _mode_constructions(sources, _CONSENT_KEYWORD)
    assert Counter((relative, name) for relative, name, _ in found) != _CONSENT_CONSTRUCTIONS
    assert _without_mode(found, _CONSENT_KEYWORD) == [("session.py", missing)]


@pytest.mark.parametrize(
    ("relative", "name"),
    [
        ("session.py", "RecordingSession"),
        ("session.py", "EncounterRecord"),
        ("ui/main_window.py", "EncounterRecord"),
        ("ui/session_screen.py", _START),
        ("session.py", "begin"),
    ],
)
def test_each_existing_site_dropping_the_keyword_fails(relative: str, name: str) -> None:
    """Every counted site in turn, with its keyword removed in memory: the
    check names exactly that site."""
    sources = dict(_package_sources())
    tree = ast.parse(ast.unparse(sources[relative]))
    stripped = 0
    for _scope, node in _scoped_nodes(tree):
        if not isinstance(node, ast.Call):
            continue
        callee = _callee(node)
        hit = callee == name or (
            name == _START
            and callee == "start"
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "_controller"
        )
        if hit and stripped == 0:
            node.keywords = [kw for kw in node.keywords if kw.arg != _CONSENT_KEYWORD[name]]
            stripped += 1
    assert stripped == 1
    sources[relative] = tree
    found = _mode_constructions(sources, _CONSENT_KEYWORD)
    assert _without_mode(found, _CONSENT_KEYWORD) == [(relative, name)]


@pytest.mark.parametrize(
    ("statement", "missing"),
    [
        ("RecordingSession(key_reference='key.dpapi', consent=None)", "RecordingSession"),
        ("self._complete_locked(directory, crypto, label=None)", "_complete_locked"),
        ("other.start(0, consent=None)", _START),
    ],
)
def test_a_construction_relying_on_the_default_fails(statement: str, missing: str) -> None:
    sources = _with_extra(_package_sources(), "session.py", "SessionController.discard", statement)
    found = _mode_constructions(sources)
    assert Counter((relative, name) for relative, name, _ in found) != _MODE_CONSTRUCTIONS
    assert sorted(_without_mode(found)) == sorted([*_MODELESS, ("session.py", missing)])


# Review rounds 23–24: Qt's item views — a combo box's popup among them —
# copy the current row with a plain clipboard write on Ctrl+C, so every list
# and combo box is the one that refuses it, and no other item view is built.
_ITEM_VIEWS: Final = frozenset(
    {
        "QListWidget",
        "QListView",
        "QTreeWidget",
        "QTreeView",
        "QTableWidget",
        "QTableView",
        "QColumnView",
        "QComboBox",
        "QFontComboBox",
    }
)


def _base_name(base: ast.expr) -> str | None:
    """A base class's own name, bare (``QListWidget``) or qualified
    (``QtWidgets.QListWidget``; peer round 27 PR-MED-064)."""
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return None


def _list_classes(sources: dict[str, ast.Module]) -> tuple[set[str], Counter[str]]:
    """The Qt item-view and combo-box subclasses defined, and every
    construction of one of Qt's own (or a ``setView``) by file."""
    defined: set[str] = set()
    built: Counter[str] = Counter()
    for relative, tree in sources.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(
                _base_name(b) in _ITEM_VIEWS for b in node.bases
            ):
                defined.add(f"{relative}:{node.name}")
            if isinstance(node, ast.Call) and (
                _callee(node) in _ITEM_VIEWS or _callee(node) == "setView"
            ):
                built[relative] += 1
    return defined, built


def test_every_list_and_combo_box_is_the_one_that_refuses_copy() -> None:
    assert _list_classes(_package_sources()) == (
        {"ui/lists.py:NoCopyListWidget", "ui/lists.py:NoCopyComboBox"},
        Counter(),
    )


@pytest.mark.parametrize(
    "statement", ["QListWidget()", "QComboBox()", "QTableView()", "self.combo.setView(None)"]
)
def test_a_plain_list_or_combo_box_fails_the_check(statement: str) -> None:
    sources = _with_extra(
        _package_sources(), "ui/past_sessions.py", "PastSessionsScreen.on_copy", statement
    )
    assert _list_classes(sources)[1] == Counter({"ui/past_sessions.py": 1})


@pytest.mark.parametrize(
    "base",
    ["QListWidget", "QtWidgets.QListWidget", "QtWidgets.QComboBox", "QtWidgets.QTableView"],
)
def test_a_new_list_or_combo_box_subclass_fails_the_check(base: str) -> None:
    """Bare or qualified, a new subclass is named (peer round 27 PR-MED-064)."""
    sources = _with_extra(
        _package_sources(),
        "ui/past_sessions.py",
        "PastSessionsScreen.on_copy",
        f"class ExtraView({base}):\n    pass\nExtraView()",
    )
    assert _list_classes(sources) == (
        {
            "ui/lists.py:NoCopyListWidget",
            "ui/lists.py:NoCopyComboBox",
            "ui/past_sessions.py:ExtraView",
        },
        Counter(),
    )


def test_no_widget_turns_drag_on() -> None:
    """Every ``setDragEnabled`` call passes a literal ``False`` (round 23)."""
    calls = [
        (relative, scope, node)
        for relative, tree in _package_sources().items()
        for scope, node in _scoped_nodes(tree)
        if isinstance(node, ast.Call) and _callee(node) == "setDragEnabled"
    ]
    assert [(relative, scope) for relative, scope, _ in calls] == [
        ("ui/note.py", "_LineEditor.__init__")
    ]
    for _relative_path, _scope, call in calls:
        [argument] = call.args
        assert isinstance(argument, ast.Constant) and argument.value is False


@pytest.mark.parametrize("plain", [False, True])
def test_the_list_copy_shortcut_reaches_no_clipboard(plain: bool) -> None:
    """Offscreen Qt (its clipboard is in-process): Ctrl+C and Ctrl+Insert on
    a ``NoCopyListWidget`` leave a sentinel in place — and on a plain
    ``QListWidget`` they replace it, so the check can fail."""
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QGuiApplication, QKeyEvent
    from PySide6.QtWidgets import QApplication, QListWidget

    from scribe_desktop.ui.lists import NoCopyListWidget

    QApplication.instance() or QApplication([])
    assert QGuiApplication.platformName() == "offscreen"
    clipboard = QGuiApplication.clipboard()
    widget = QListWidget() if plain else NoCopyListWidget()
    widget.addItem("row text")
    widget.setCurrentRow(0)
    control = Qt.KeyboardModifier.ControlModifier
    for key in (Qt.Key.Key_C, Qt.Key.Key_Insert):
        clipboard.setText("sentinel")
        widget.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, key, control))
        assert clipboard.text() == ("row text" if plain else "sentinel")
    widget.deleteLater()


@pytest.mark.parametrize("plain", [False, True])
def test_a_combo_boxs_popup_copy_reaches_no_clipboard(plain: bool) -> None:
    """Round 24: the same through a combo box's popup view, delivered as Qt
    delivers it (``sendEvent``, so event filters run) — the sentinel stays
    for a ``NoCopyComboBox`` and is replaced for a plain ``QComboBox``."""
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QGuiApplication, QKeyEvent
    from PySide6.QtWidgets import QApplication, QComboBox

    from scribe_desktop.ui.lists import NoCopyComboBox

    app = QApplication.instance() or QApplication([])
    assert QGuiApplication.platformName() == "offscreen"
    clipboard = QGuiApplication.clipboard()
    combo = QComboBox() if plain else NoCopyComboBox()
    combo.addItem("row text")
    view = combo.view()
    view.setCurrentIndex(combo.model().index(0, 0))
    control = Qt.KeyboardModifier.ControlModifier
    for key in (Qt.Key.Key_C, Qt.Key.Key_Insert):
        clipboard.setText("sentinel")
        app.sendEvent(view, QKeyEvent(QEvent.Type.KeyPress, key, control))
        assert clipboard.text() == ("row text" if plain else "sentinel")
    combo.deleteLater()


def test_the_one_send_is_reached_only_through_draft_write() -> None:
    assert _send_callers(_package_sources()) == _SEND_CALLERS


@pytest.mark.parametrize("function", ["send_write", "prepare_write"])
def test_a_second_send_in_draft_write_fails_the_count(function: str) -> None:
    """PR-MED-A01's case: another ``write_draft_note`` call anywhere in
    ``draft_write.py`` — beside the one send or outside it — is caught."""
    sources = _with_extra(
        _package_sources(), "draft_write.py", function, "call.write_draft_note('1', None)"
    )
    assert _send_callers(sources) != _SEND_CALLERS
