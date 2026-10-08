"""Pilot plan Task 3.1: the pilot documents in ``docs/pilot/``.

The four files exist; the pilot-log template stays unfilled; and neither the
template nor the findings register (which lives in the public repository) has
a free-text clinical column or anything shaped like a session id or a Cliniko
id (Constraint 7). Every table column is from a fixed list, so a new column
fails here until it is reviewed; every register cell but "Control or fix" is
from the register's closed vocabularies, so a name, a quotation or an id there
fails too. "Control or fix" is the one free-text cell: it is held only to be
short, unquoted and id-free (review round 17) — a name typed into it is not
caught, which the register's rule forbids.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PILOT = REPO / "docs" / "pilot"
TEMPLATE = PILOT / "pilot-log-template.md"
REGISTER = PILOT / "findings-register.md"

# A session id (``session_store.SESSION_ID_PATTERN``), a clinic id or any
# other long hexadecimal run, and a long digit run (a Cliniko id).
_ID_SHAPED = re.compile(r"(?<![0-9A-Za-z])(?:[0-9a-fA-F]{16,}|[0-9]{7,})(?![0-9A-Za-z])")
# Column words that would invite clinical content or an id.
_FORBIDDEN_COLUMN_WORDS = (
    "patient",
    "name",
    "text",
    "transcript",
    "said",
    "quote",
    "description",
    "detail",
    "comment",
    "remark",
    "summary",
    "session",
    "cliniko",
    "birth",
)

LOG_COLUMNS = (
    "Row",
    "Date",
    "Clinic",
    "Mode",
    "App version",
    # Development-recordings plan Task 5.3b (D9): yes / no.
    "Kept",
    "R1",
    "R2",
    "R3",
    "R4",
    "R5",
    "R6",
    "Minutes",
    "Missed",
    "Would sign",
    "Findings",
)
LOG_TOTAL_COLUMNS = (
    "Clinic",
    "Mode",
    "Rows",
    "R1 total",
    "R3 total",
    "R4 total",
    "R6 yes",
    "Median minutes",
    "Missed total",
    "Would sign yes",
)
# Development-recordings plan Task 5.3b (D9): why a kept recording is still
# kept at its 12-month review — closed words, linked by the log's row number
# (or, outside the pilot log, the consultation's date).
LOG_REVIEW_COLUMNS = (
    "Row",
    "Consulted",
    "Reviewed",
    "Outcome",
    "Kept for",
)
REGISTER_COLUMNS = (
    "ID",
    "Found",
    "Clinic",
    "Stage",
    "Encounter",
    "Severity",
    "Category",
    "Part of the app",
    "Status",
    "Control or fix",
    "Closed",
)

_MONTH = r"20[0-9]{2}-[01][0-9]"
REGISTER_CELL_PATTERNS = {
    "ID": r"F-[0-9]{3,}",
    # The month only (review round 17; "Closed" too, round 18): a public row
    # dated to the day of a shadow or reviewed consultation could let a
    # patient recognise theirs, and a finding controlled the day it was found
    # would give that day away.
    "Found": _MONTH,
    "Clinic": r"1|2|—",
    "Stage": r"validation|role-play|shadow|reviewed|everyday|other",
    "Encounter": r"syn-[0-9]{2,}|rp-[0-9]{2,}|—",
    "Severity": r"high|medium|low",
    "Category": (
        r"wrong-side|wrong-dose|negation-flipped|patient-speculation|cross-patient"
        r"|privacy|custody|unsupported|omission|uncertainty|checker|role|quality|workflow"
    ),
    "Part of the app": (
        r"transcription|speaker-labels|note-routing|proposals|checker|prose|copy|write"
        r"|session|past-sessions|audit|install|other"
    ),
    "Status": r"open|resolved|controlled",
    "Closed": rf"(?:{_MONTH})?",
}
# "Control or fix" names a commit, a build version, a setting or a procedure:
# short, no quotation marks (nothing quoted from a note) and no id shape.
_CONTROL_MAX_CHARS = 200


def _control_problems(control: str, status: str, closed: str) -> list[str]:
    """What is wrong with a row's "Control or fix" cell, given its status
    and its "Closed" cell; empty when nothing is."""
    problems = []
    if len(control) > _CONTROL_MAX_CHARS:
        problems.append("too long")
    if set(control) & set("\"“”‘’"):
        problems.append("quotation mark")
    if _ID_SHAPED.findall(control):
        problems.append("id-shaped")
    if (control == "") != (status == "open"):
        problems.append("control and status disagree")
    if (closed == "") != (status == "open"):
        problems.append("closed and status disagree")
    return problems


def _row_problems(row: list[str]) -> list[str]:
    """What is wrong with one register row: a wrong cell count, a cell
    outside its closed vocabulary, or a bad "Control or fix"; empty when
    nothing is."""
    if len(row) != len(REGISTER_COLUMNS):
        return ["cell count"]
    cells = dict(zip(REGISTER_COLUMNS, row, strict=True))
    problems = [
        column
        for column, pattern in REGISTER_CELL_PATTERNS.items()
        if not re.fullmatch(pattern, cells[column])
    ]
    return problems + _control_problems(cells["Control or fix"], cells["Status"], cells["Closed"])


def _tables(path: Path) -> list[list[list[str]]]:
    """Every Markdown table in ``path`` (``_tables_in``)."""
    return _tables_in(path.read_text(encoding="utf-8"))


def _tables_in(text: str) -> list[list[list[str]]]:
    """Every Markdown table in ``text``: rows of stripped cells, the
    separator row dropped. A line is a table line when it starts with ``|``
    after any leading spaces (peer round 20, PR-MED-061): an indented row
    still renders as a row of the table, so it is checked like any other."""
    tables: list[list[list[str]]] = []
    current: list[list[str]] | None = None
    for line in text.splitlines():
        if line.lstrip().startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                continue
            if current is None:
                current = []
                tables.append(current)
            current.append(cells)
        else:
            current = None
    return tables


class TestPilotDocuments:
    def test_the_four_documents_exist(self) -> None:
        for name in ("README.md", "pilot-log-template.md", "findings-register.md", "exit-gate.md"):
            assert (PILOT / name).is_file(), name

    def test_no_id_shaped_string_in_any_pilot_document(self) -> None:
        for path in sorted(PILOT.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            assert _ID_SHAPED.findall(text) == [], path.name

    def test_no_column_invites_clinical_content(self) -> None:
        for path in (TEMPLATE, REGISTER):
            for table in _tables(path):
                for column in table[0]:
                    lowered = column.casefold()
                    assert not [word for word in _FORBIDDEN_COLUMN_WORDS if word in lowered], (
                        path.name,
                        column,
                    )


class TestPilotLogTemplate:
    def test_the_columns_are_the_fixed_list(self) -> None:
        tables = _tables(TEMPLATE)
        assert [tuple(table[0]) for table in tables] == [
            LOG_COLUMNS,
            LOG_TOTAL_COLUMNS,
            LOG_REVIEW_COLUMNS,
        ]

    def test_the_template_stays_unfilled(self) -> None:
        """The filled log lives off the repository (README): the template's
        one row carries only its row number, the totals rows only their
        clinic and mode, and the kept-recordings review row nothing."""
        log, totals, review = _tables(TEMPLATE)
        assert log[1:] == [["1"] + [""] * (len(LOG_COLUMNS) - 1)]
        for row in totals[1:]:
            assert row[0] in {"1", "2"} and row[1] in {"shadow", "normal"}
            assert row[2:] == [""] * (len(LOG_TOTAL_COLUMNS) - 2)
        assert review[1:] == [[""] * len(LOG_REVIEW_COLUMNS)]


class TestFindingsRegister:
    def test_the_columns_are_the_fixed_list(self) -> None:
        tables = _tables(REGISTER)
        assert [tuple(table[0]) for table in tables] == [REGISTER_COLUMNS]

    def test_every_row_uses_the_closed_vocabularies(self) -> None:
        """A row is a finding about the app: every cell but the control is
        from a closed vocabulary, so a name, a quotation or a real id cannot
        be entered without failing here."""
        (register,) = _tables(REGISTER)
        ids = []
        for row in register[1:]:
            assert _row_problems(row) == [], (row[:1], _row_problems(row))
            ids.append(row[0])
        assert len(ids) == len(set(ids))

    def test_an_indented_row_is_checked_too(self) -> None:
        """Peer round 20 (PR-MED-061): a row written with leading spaces
        still shows as a row of the register, so the parser takes it as one
        and the row check refuses the name in it."""
        header = "| " + " | ".join(REGISTER_COLUMNS) + " |"
        separator = "|" + "---|" * len(REGISTER_COLUMNS)
        good = (
            "| F-001 | 2026-10 | 1 | shadow | — | high | wrong-side"
            " | note-routing | open |  |  |"
        )
        indented = (
            "   | F-002 | 2026-10 | 1 | shadow | Jane Citizen | high | wrong-side"
            " | note-routing | open |  |  |"
        )
        (table,) = _tables_in("\n".join((header, separator, good, indented)))
        assert len(table) == 3
        assert _row_problems(table[1]) == []
        assert _row_problems(table[2]) == ["Encounter"]

    def test_the_vocabulary_check_refuses_clinical_content(self) -> None:
        """The check above, both ways: a well-formed row passes and a row
        carrying a name or a quotation in a closed column does not."""
        good = {
            "ID": "F-001",
            "Found": "2026-10",
            "Clinic": "1",
            "Stage": "shadow",
            "Encounter": "—",
            "Severity": "high",
            "Category": "wrong-side",
            "Part of the app": "note-routing",
            "Status": "open",
            "Closed": "",
        }
        assert all(re.fullmatch(REGISTER_CELL_PATTERNS[k], v) for k, v in good.items())
        for column, bad in (
            ("Encounter", "Jane Citizen"),
            ("Category", "left knee said as right"),
            ("Encounter", "0123456789abcdef0123456789abcdef"),
            ("Found", "2026-10-20"),
            ("Closed", "2026-11-02"),
        ):
            assert not re.fullmatch(REGISTER_CELL_PATTERNS[column], bad), column
        assert _ID_SHAPED.findall("session 0123456789abcdef0123456789abcdef")
        assert _ID_SHAPED.findall("note 1234567890123")
        assert not _ID_SHAPED.findall("found 2026-10-20 in syn-07, build 0.2.0")

    def test_the_control_check_both_ways(self) -> None:
        """The "Control or fix" checks (review round 17): a closed row naming
        a build or a short commit passes; an over-long, quoted or id-carrying
        control, and a control or close date that disagrees with the status,
        do not."""
        assert _control_problems("fixed in 0.2.1 (commit a1b2c3d)", "resolved", "2026-11") == []
        assert _control_problems("", "open", "") == []
        assert _control_problems("x" * (_CONTROL_MAX_CHARS + 1), "controlled", "2026-11") == [
            "too long"
        ]
        assert _control_problems("note said “left”", "resolved", "2026-11") == [
            "quotation mark"
        ]
        assert _control_problems("note 1234567890123 rewritten", "resolved", "2026-11") == [
            "id-shaped"
        ]
        assert _control_problems("shadow mode left on", "open", "") == [
            "control and status disagree"
        ]
        assert _control_problems("", "resolved", "") == [
            "control and status disagree",
            "closed and status disagree",
        ]
