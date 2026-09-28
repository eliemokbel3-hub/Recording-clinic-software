"""The Chrome-side text tables stay in step with each other and with the
desktop's codes (H2a SIMP-004 / SIMP-005, round 67).

- The block's reason text is held twice on the Chrome side — the page
  script (``page.ts`` ``REASONS``) and the side panel (``panel-view.ts``
  ``BLOCK_REASONS``); one copy has drifted before (round 53 LOW-043). Both
  must read the same, and cover exactly the pause reasons that draw a block.
  The desktop's own ``PAUSE_CUES`` is deliberately worded for the desktop and
  is key-pinned to ``PauseReason`` in ``test_ui_models.py``.
- The note-refusal text is worded per surface on purpose (the panel names
  "Clinic Scribe's Clinics tab"; the desktop is the app), so only the CODES
  are pinned: the panel's ``NOTE_REFUSALS`` and the desktop's
  ``NOTE_REFUSAL_REASONS`` both cover exactly ``NoteRefusal``. A code added on
  one side then fails here, instead of reading "no reason given" in the panel.

A TEXT-MATCHING reader over the TypeScript source, not a parser: each table
must be written one ``key: "value",`` entry per line (comment lines allowed);
any other line inside a table fails the read, so a multi-line or computed
entry cannot slip past unseen."""

from __future__ import annotations

import json
import re
from pathlib import Path

from scribe_desktop.context_rules import PauseReason
from scribe_desktop.encounter import NoteRefusal
from scribe_desktop.ui import models

REPO = Path(__file__).resolve().parents[2]
EXTENSION = REPO / "extension" / "src"
_ENTRY = re.compile(r'^\s*([a-z_]+):\s*("(?:[^"\\]|\\.)*"),?\s*$')
# The two reasons that pause without ever drawing a block (context_rules).
_NO_BLOCK = frozenset({PauseReason.HOTKEY.value, PauseReason.SPOKEN.value})


def _table(file_name: str, const_name: str) -> dict[str, str]:
    """The ``const <const_name> ... = {`` table in ``extension/src/<file>``."""
    lines = (EXTENSION / file_name).read_text(encoding="utf-8").splitlines()
    opener = re.compile(rf"^(export )?const {const_name}\b")
    starts = [i for i, line in enumerate(lines) if opener.match(line)]
    assert len(starts) == 1, f"{file_name}: expected one `const {const_name}`"
    assert lines[starts[0]].rstrip().endswith("{"), f"{const_name} must open on its own line"
    table: dict[str, str] = {}
    for line in lines[starts[0] + 1 :]:
        if line.strip() == "};":
            return table
        if line.strip().startswith("//"):
            continue
        match = _ENTRY.match(line)
        assert match, f"{file_name} {const_name}: unreadable entry line {line!r}"
        key, value = match.group(1), json.loads(match.group(2))
        assert key not in table, f"{file_name} {const_name}: duplicate key {key}"
        table[key] = value
    raise AssertionError(f"{file_name} {const_name}: no closing `}};`")


def test_the_page_and_the_panel_give_the_same_block_reasons() -> None:
    page = _table("page.ts", "REASONS")
    panel = _table("panel-view.ts", "BLOCK_REASONS")
    assert page == panel


def test_the_block_reasons_cover_exactly_the_reasons_that_block() -> None:
    expected = {reason.value for reason in PauseReason} - _NO_BLOCK
    assert set(_table("panel-view.ts", "BLOCK_REASONS")) == expected


def test_the_panels_note_refusals_cover_exactly_the_desktops_codes() -> None:
    assert set(_table("panel-view.ts", "NOTE_REFUSALS")) == {code.value for code in NoteRefusal}


def test_the_desktops_note_refusal_text_covers_every_code() -> None:
    assert set(models.NOTE_REFUSAL_REASONS) == set(NoteRefusal)
