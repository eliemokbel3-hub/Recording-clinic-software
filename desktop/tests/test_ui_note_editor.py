"""The Note tab's inline line editor and its pre-filled rows (note-learning
and styles plan Phase 2, Tasks 2.1 and 2.4 — the UI half).

Offscreen, like every other screen test: no real audio, no ML, no provider
beyond the extractive stub. What is pinned here is the SURFACE — Edit opens a
one-line editor inside the row it edits (Enter/Apply applies, Escape/Cancel
cancels), a typed line replaces the line or proposal it stands in for and
Undo restores it, a pre-filled line renders marked with Remove and Edit but
no confirm/decline row while the Save button counts it, and every editor
control freezes at Save.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from scribe_desktop.note import (  # noqa: E402
    CANONICAL_SECTION_KEYS,
    ExtractiveNoteProvider,
    compose_draft,
)
from scribe_desktop.note_config import (  # noqa: E402
    AutofillRule,
    NoteConfig,
    PrefillSeedAssertion,
    PrefillTemplate,
    SectionMapping,
    TemplateProfile,
    TemplateTarget,
)
from scribe_desktop.transcription import (  # noqa: E402
    SPEAKER_1,
    SPEAKER_2,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
)
from scribe_desktop.ui import models  # noqa: E402

_SESSION_ID = "e" * 32
# A learned rule's id (the ``learned-`` prefix is the ONE test): with no
# sidecar record saying auto-confirmed, such a rule PROPOSES rather than
# pre-filling, which is how this file gets a pending proposal row.
_LEARNED_RULE_ID = "learned-01J0000000000000000000000A"
_ICE_TEXT = "Ice pack use explained."
_KNEE_TEXT = "Knee effusion assessed."
_TYPED_TEXT = "Knee stable, full range restored."
_OTHER_TYPED_TEXT = "Ice advice given as discussed."
_PREFILLED_LABEL = "pre-filled by your config - autofill (clinician-authored)"


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


# --- fixtures (self-contained: tests/ is not a package) --------------------


def _note_config(*, ice_rule_id: str = "rule-ice") -> NoteConfig:
    profile = TemplateProfile(
        template_profile_id="clinic-a",
        display_name="Clinic A",
        template_targets=(
            TemplateTarget(
                target_id="t-main", group="Notes", field_label="Main", target_type="rich_text"
            ),
        ),
        section_mappings=tuple(
            SectionMapping(section_key=key, target_id="t-main")
            for key in CANONICAL_SECTION_KEYS
            if key != "consent"
        ),
        intentionally_unmapped=("consent",),
    )
    return NoteConfig(
        template_profiles=(profile,),
        autofill_rules=(
            AutofillRule(
                rule_id=ice_rule_id,
                section_key="advice_home_exercise",
                trigger_phrase="ice pack",
                expansion=(_ICE_TEXT,),
            ),
        ),
        prefill_templates=(
            PrefillTemplate(
                prefill_id="knee-exam",
                display_name="Knee examination",
                region_keywords=("knee",),
                seed_assertions=(
                    PrefillSeedAssertion(
                        section_key="objective_examination", seed_text=_KNEE_TEXT
                    ),
                ),
            ),
        ),
    )


def _note_words(text: str) -> tuple[TranscriptWord, ...]:
    return tuple(
        TranscriptWord(
            word_text=token,
            start_seconds=index * 0.3,
            end_seconds=index * 0.3 + 0.25,
            probability=0.9,
            uncertain=False,
        )
        for index, token in enumerate(text.split())
    )


_EDIT_TURNS: tuple[tuple[str, str], ...] = (
    ("My left knee is sore when I walk", SPEAKER_1),
    ("On examination the range of motion is limited", SPEAKER_2),
    ("The diagnosis is a mild knee sprain", SPEAKER_2),
    ("Please use an ice pack tonight", SPEAKER_2),
    ("I walked to the shop this morning", SPEAKER_1),
    ("The knee felt steady on the stairs", SPEAKER_2),
    ("The plan is to review you in two weeks", SPEAKER_2),
)


def _note_document(turns: tuple[tuple[str, str], ...] = _EDIT_TURNS) -> TranscriptDocument:
    return TranscriptDocument(
        session_id=_SESSION_ID,
        created_at=datetime.now(UTC),
        model_name="mock",
        sample_rate=16_000,
        transcript_segments=tuple(
            TranscriptSegment(
                start_seconds=float(index * 10),
                end_seconds=float(index * 10 + 5),
                speaker=speaker,
                transcript_words=_note_words(text),
            )
            for index, (text, speaker) in enumerate(turns)
        ),
    )


def _edit_result(config: NoteConfig | None = None) -> models.NoteGenerationResult:
    document = _note_document()
    resolved = config if config is not None else _note_config()
    draft = compose_draft(
        document, resolved, ExtractiveNoteProvider(), clinician_speaker=SPEAKER_2
    )
    return models.NoteGenerationResult(draft=draft, config=resolved, document=document)


def _screen(
    tmp_path: Path, result: models.NoteGenerationResult | None = None
) -> tuple[Any, dict[str, list[Any]]]:
    from scribe_desktop.ui.note import NoteScreen

    record: dict[str, list[Any]] = {"saved": [], "abandoned": [], "cancelled": []}
    screen = NoteScreen(config_root=tmp_path / "config")
    screen.begin_review(
        result if result is not None else _edit_result(),
        on_save=lambda note: record["saved"].append(note),
        on_abandon=lambda: record["abandoned"].append(True),
        on_cancel=lambda: record["cancelled"].append(True),
        template_profile_id="clinic-a",
    )
    return screen, record


# --- row helpers -----------------------------------------------------------


def _rows(screen: Any) -> list[Any]:
    """The line-editor rows, in build order: transcript lines, then the
    pre-filled lines, then the typed lines."""
    items = [screen._lines_box.itemAt(index) for index in range(screen._lines_box.count())]
    return [item.widget() for item in items if item is not None and item.widget() is not None]


def _row_for_line(screen: Any, assertion_id: str) -> Any:
    ids = [line.assertion_id for line in screen.editable_lines()]
    return _rows(screen)[ids.index(assertion_id)]


def _row_for_prefilled(screen: Any, proposal_id: str) -> Any:
    ids = [line.proposal_id for line in screen.prefilled_lines()]
    return _rows(screen)[len(screen.editable_lines()) + ids.index(proposal_id)]


def _row_for_typed(screen: Any, assertion_id: str) -> Any:
    ids = [line.assertion_id for line in screen.typed_lines()]
    offset = len(screen.editable_lines()) + len(screen.prefilled_lines())
    return _rows(screen)[offset + ids.index(assertion_id)]


def _button(row: Any, text: str) -> Any:
    from PySide6.QtWidgets import QPushButton

    for button in row.findChildren(QPushButton):
        if button.text() == text:
            return button
    raise AssertionError(f"no '{text}' button in this row")


def _first_routed(screen: Any) -> Any:
    line = next((item for item in screen.editable_lines() if item.state == "routed"), None)
    assert line is not None, "the fixture must have routed a transcript line"
    return line


def _line_state(screen: Any, assertion_id: str) -> str:
    states = {line.assertion_id: line.state for line in screen.editable_lines()}
    return str(states[assertion_id])


def _prefilled_state(screen: Any, proposal_id: str) -> str:
    states = {line.proposal_id: line.state for line in screen.prefilled_lines()}
    return str(states[proposal_id])


def _working_text(screen: Any, assertion_id: str) -> str:
    for section in screen._working.note_sections:
        for assertion in section.note_assertions:
            if assertion.assertion_id == assertion_id:
                return str(assertion.text)
    raise AssertionError(f"no line {assertion_id} in the working note")


def _escape(qapp: Any, widget: Any) -> None:
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent

    qapp.sendEvent(
        widget,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
    )


# --- (a) Edit over a routed transcript line --------------------------------


def test_edit_on_a_routed_row_opens_the_editor_and_apply_types_over_the_line(
    qapp: Any, tmp_path: Path
) -> None:
    screen, _record = _screen(tmp_path)
    routed = _first_routed(screen)
    full_text = _working_text(screen, routed.assertion_id)

    _button(_row_for_line(screen, routed.assertion_id), "Edit").click()

    assert screen._editor is not None
    target_id, field = screen._editor
    assert target_id == routed.assertion_id
    # The editor renders INSIDE that row, carrying the line's FULL text (the
    # row's own label is truncated to its leading words).
    assert field.parentWidget() is _row_for_line(screen, routed.assertion_id)
    assert field.text() == full_text
    assert field.text() != routed.label

    field.setText(_TYPED_TEXT)
    assert screen.commit_editor() is True

    body = screen.note_body.toPlainText()
    assert f"{_TYPED_TEXT}  [typed (clinician-authored)]" in body
    typed = screen.typed_lines()
    assert len(typed) == 1
    assert typed[0].text == _TYPED_TEXT
    assert typed[0].replaces == routed.assertion_id
    assert screen._editor is None  # the row rebuild closed it
    assert screen._editor_request is None
    assert _line_state(screen, routed.assertion_id) == "replaced"

    _button(_row_for_line(screen, routed.assertion_id), "Undo").click()

    assert screen.typed_lines() == ()
    assert _line_state(screen, routed.assertion_id) == "routed"
    assert full_text in screen.note_body.toPlainText()
    assert _TYPED_TEXT not in screen.note_body.toPlainText()
    screen.deleteLater()


# --- (b) cancelling, and a refused apply -----------------------------------


def test_escape_and_cancel_close_the_editor_and_a_blank_apply_keeps_it_open(
    qapp: Any, tmp_path: Path
) -> None:
    screen, _record = _screen(tmp_path)
    routed = _first_routed(screen)
    full_text = _working_text(screen, routed.assertion_id)
    before = screen.note_body.toPlainText()

    screen.open_editor(routed.assertion_id, full_text)
    assert screen._editor is not None
    _escape(qapp, screen._editor[1])
    assert screen._editor is None
    assert screen._editor_request is None
    assert screen.typed_lines() == ()
    assert screen.note_body.toPlainText() == before

    screen.open_editor(routed.assertion_id, full_text)
    assert screen._editor is not None
    _button(_row_for_line(screen, routed.assertion_id), "Cancel").click()
    assert screen._editor is None
    assert screen._editor_request is None
    assert screen.typed_lines() == ()
    assert screen.note_body.toPlainText() == before

    screen.open_editor(routed.assertion_id, full_text)
    assert screen._editor is not None
    screen._editor[1].setText("   ")
    assert screen.commit_editor() is False
    assert screen._editor is not None  # still open, carrying what was typed
    assert screen.edit_status_label.text() == models.check_typed_text("")
    assert screen.typed_lines() == ()
    assert screen.note_body.toPlainText() == before
    screen.deleteLater()


# --- (c) pre-filled rows, the counted Save, Remove / Undo / Edit -----------


def test_pre_filled_rows_are_marked_counted_and_removable_without_a_confirm_row(
    qapp: Any, tmp_path: Path
) -> None:
    screen, _record = _screen(tmp_path)
    decisions = screen._draft.config_decisions
    assert decisions, "the hand-authored config must pre-fill its lines"
    prefilled = screen.prefilled_lines()
    assert len(prefilled) == len(decisions)
    assert f"{_ICE_TEXT}  [{_PREFILLED_LABEL}]" in screen.note_body.toPlainText()
    assert screen.save_button.text() == models.save_button_label(len(prefilled))
    assert screen.save_button.text().startswith("Save - confirms the ")
    assert str(len(prefilled)) in screen.save_button.text()
    # A pre-filled line has NO confirm/decline row: nothing rendered it.
    assert not (set(screen._rendered_excerpt) & {line.proposal_id for line in prefilled})

    ice = next(line for line in prefilled if line.text == _ICE_TEXT)
    assert ice.label.endswith(f"[{models.PREFILLED_MARK}]")
    _button(_row_for_prefilled(screen, ice.proposal_id), "Remove line").click()
    assert _prefilled_state(screen, ice.proposal_id) == "removed"
    assert screen.save_button.text() == models.save_button_label(len(prefilled) - 1)
    assert _ICE_TEXT not in screen.note_body.toPlainText()

    _button(_row_for_prefilled(screen, ice.proposal_id), "Undo").click()
    assert _prefilled_state(screen, ice.proposal_id) == "prefilled"
    assert screen.save_button.text() == models.save_button_label(len(prefilled))
    assert f"{_ICE_TEXT}  [{_PREFILLED_LABEL}]" in screen.note_body.toPlainText()

    _button(_row_for_prefilled(screen, ice.proposal_id), "Edit").click()
    assert screen._editor is not None
    assert screen._editor[0] == ice.proposal_id
    assert screen._editor[1].text() == _ICE_TEXT
    screen._editor[1].setText(_OTHER_TYPED_TEXT)
    assert screen.commit_editor() is True
    typed = screen.typed_lines()
    assert len(typed) == 1
    assert typed[0].replaces == ice.proposal_id
    assert _prefilled_state(screen, ice.proposal_id) == "replaced"
    assert f"{_OTHER_TYPED_TEXT}  [typed (clinician-authored)]" in screen.note_body.toPlainText()
    screen.deleteLater()


# --- (d) Save freezes the editor -------------------------------------------


def test_save_freezes_every_editor_control_and_refuses_a_new_editor(
    qapp: Any, tmp_path: Path
) -> None:
    from PySide6.QtWidgets import QPushButton

    screen, record = _screen(tmp_path)
    for proposal in screen._draft.note_proposals:
        if proposal.proposal_id in screen._rendered_excerpt:  # pre-filled lines have no row
            screen.confirm_proposal(proposal.proposal_id)
    screen._acknowledge_all()
    routed = _first_routed(screen)
    screen.open_editor(routed.assertion_id, _working_text(screen, routed.assertion_id))
    assert screen._editor is not None

    screen.save()

    assert len(record["saved"]) == 1
    labels = {
        widget.text() for widget in screen._line_widgets if isinstance(widget, QPushButton)
    }
    assert {"Edit", "Apply", "Cancel"} <= labels
    assert all(not widget.isEnabled() for widget in screen._line_widgets)

    screen.open_editor(routed.assertion_id, "Something else entirely.")
    assert "edits are closed" in screen.edit_status_label.text()
    assert screen.commit_editor() is False
    assert screen.typed_lines() == ()
    screen.deleteLater()


# --- (e) Edit over a proposal still awaiting a decision --------------------


def test_edit_on_a_pending_proposal_replaces_it_until_the_typed_line_is_undone(
    qapp: Any, tmp_path: Path
) -> None:
    screen, _record = _screen(
        tmp_path, result=_edit_result(_note_config(ice_rule_id=_LEARNED_RULE_ID))
    )
    assert screen.current_review_state().unconfirmed_proposals == 1
    pending = [
        proposal
        for proposal in screen._draft.note_proposals
        if proposal.proposal_id in screen._rendered_excerpt
    ]
    assert len(pending) == 1
    proposal_id = pending[0].proposal_id

    edit = next(button for button in screen._proposal_buttons if button.text() == "Edit")
    edit.click()
    assert screen._editor is not None
    assert screen._editor[0] == proposal_id
    assert screen._editor[1].text() == models.render_proposal(pending[0]).excerpt

    screen._editor[1].setText(_OTHER_TYPED_TEXT)
    assert screen.commit_editor() is True
    assert screen.current_review_state().unconfirmed_proposals == 0
    assert (
        screen._state_labels[proposal_id].text()
        == "Replaced by your typed line - Undo it to decide again."
    )
    typed = screen.typed_lines()
    assert len(typed) == 1
    assert typed[0].replaces == proposal_id

    _button(_row_for_typed(screen, typed[0].assertion_id), "Undo").click()
    assert screen.typed_lines() == ()
    assert screen.current_review_state().unconfirmed_proposals == 1
    assert screen._state_labels[proposal_id].text() == "Not yet confirmed or declined."
    screen.deleteLater()
