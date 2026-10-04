"""Pilot plan Critical Constraint 3 (Task 1.5): every path that carries note
text out is gated in shadow mode — and a NEW one fails here until it is.

Read from the source (no Qt, no clipboard):

- the callers of ``ui.note._place_note_text`` (THE placement of note text on
  the clipboard) are exactly the three known ones, each passing ``shadow=``;
- the widgets in ``ui/note.py`` and ``ui/past_sessions.py`` that can hold
  text a user could select (plain-text and line edits, and their
  subclasses) are exactly the known ones, each with its gate named below;
- no text-interaction flag that makes text selectable is set anywhere in
  those two modules except ``NoteScreen._apply_copy_binding`` (whose
  predicate is ``_copy_allowed``, which refuses a shadow note);
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
        # The editor: Copy, Cut and drag refused in shadow (`_LineEditor.shadow`).
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
    selectable = {
        "TextSelectableByMouse",
        "TextSelectableByKeyboard",
        "TextEditorInteraction",
        "TextBrowserInteraction",
        "TextEditable",
    }
    where: set[tuple[str, str]] = set()
    for path in (UI / "note.py", UI / "past_sessions.py"):
        for scope, node in _scoped_nodes(_tree(path)):
            if isinstance(node, ast.Attribute) and node.attr in selectable:
                where.add((_relative(path), scope))
    assert where == {("ui/note.py", "NoteScreen._apply_copy_binding")}


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
