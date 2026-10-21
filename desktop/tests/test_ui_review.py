"""UI refresh plan Phase 2 (D6, D14; Tasks 2.1-2.4): the Review screen.

The Review page is a lite composition of the two existing engines: the
Transcript engine whole on the left, its "Generate note" group over the Note
engine (its duplicate transcript pane hidden) over "Edit the note" on the
right, then one button row and one status strip. These tests pin the routing
(every route to either engine lands on the Review page, through
``setCurrentWidget``), the row and strip order, the adoption shape, and the
state matrix driven through the window: each state's controls are the engines'
own enablement, unchanged by the move.

Offscreen Qt against the fakes of ``test_ui_screens.py``; synthetic
transcripts only. Every window is built here and closed here; the theme is
never re-applied to the whole application (Phase 1's suite-time lesson)."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import test_transcript_trim as trim  # noqa: E402
from scribe_desktop.encounter import unlinked_consent  # noqa: E402
from scribe_desktop.note_config import load_note_config  # noqa: E402
from scribe_desktop.secure_storage import SessionCrypto  # noqa: E402
from scribe_desktop.session import RecordingSession, SessionState  # noqa: E402
from scribe_desktop.session_mode import SessionMode  # noqa: E402
from scribe_desktop.transcription import SPEAKER_1, SPEAKER_2, RecoveryOutcome  # noqa: E402
from scribe_desktop.ui import models  # noqa: E402
from test_ui_screens import (  # noqa: E402
    _NOTE_TURNS,
    _PLAN_INDEX,
    FakeController,
    _document,
    _edit_result,
    _main_window,
    _note_config,
    _note_document,
    _note_result,
    _process_until,
    _routed_line,
)


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


def _queued_controller(mode: SessionMode = SessionMode.NORMAL) -> FakeController:
    """A live QUEUED recording of ``mode`` behind the window (pilot plan D3:
    a review with no live session is a shadow one)."""
    controller = FakeController()
    controller.state_value = SessionState.QUEUED
    controller.session_value = RecordingSession(
        consent=unlinked_consent(), mode=mode
    ).with_state(SessionState.QUEUED)
    return controller


def _window(tmp_path: Path, controller: Any | None = None) -> Any:
    """A window whose Transcript engine reads the fixture config — never the
    default loader (no real store is read)."""
    window = _main_window(
        tmp_path, controller if controller is not None else FakeController(),
        profile_root=tmp_path / "profile",
    )
    window.transcript_screen._config_loader = _note_config
    return window


def _show_queued(qapp: Any, window: Any) -> None:
    window.session_screen.transcript_ready.emit(_note_document())
    qapp.processEvents()


def _start_generation(qapp: Any, window: Any) -> None:
    """Confirm the clinician and the template and press Generate; the draft is
    composed on the worker and has NOT been delivered yet."""
    result = _note_result()
    window.transcript_screen._note_generator_factory = (
        lambda **_kwargs: lambda _directory, _crypto: result
    )
    window.transcript_screen.set_role(SPEAKER_2)
    window.transcript_screen.set_profile("clinic-a")
    window.transcript_screen.generate()


def _await_draft(qapp: Any, window: Any) -> None:
    assert _process_until(qapp, lambda: window.note_screen.current_note() is not None)


def _ratify_and_save(window: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Confirm every proposal, acknowledge every warning and Save through the
    window's own route, with the on-disk note write faked."""
    from scribe_desktop.note import LINE_MARK_CODES

    def fake_write(directory: Path, *_args: Any, **_kwargs: Any) -> Path:
        return directory / "note.enc"

    monkeypatch.setattr("scribe_desktop.ui.transcript.write_saved_note", fake_write)
    note_screen = window.note_screen
    for proposal in note_screen._draft.note_proposals:
        note_screen.confirm_proposal(proposal.proposal_id)
    note_screen._acknowledge_all()
    note = note_screen.current_note()
    assert note is not None
    for code in LINE_MARK_CODES:
        if code in {warning.note_warning_code for warning in note.note_warnings}:
            note_screen._acknowledge(code)
    note_screen.save()


def _row_widgets(review: Any) -> list[Any]:
    row = review.button_row
    return [row.itemAt(index).widget() for index in range(row.count())]


def _strip_widgets(review: Any) -> list[Any]:
    layout = review.status_strip.layout()
    return [layout.itemAt(index).widget() for index in range(layout.count())]


def _shown(widget: Any, window: Any) -> bool:
    """D14: an adopted widget's visibility is read against the Review page."""
    return bool(widget.isVisibleTo(window.review_screen))


# --- Task 2.1: the page and its routing ----------------------------------------------


class TestPageAndRouting:
    def test_review_is_one_page_holding_both_engines(self, qapp: Any, tmp_path: Path) -> None:
        window = _window(tmp_path)
        review = window.review_screen
        tabs = window.tabs
        assert tabs.indexOf(review) >= 0
        assert tabs.tabText(tabs.indexOf(review)) == "Review"
        # The engines are children of the page, not pages themselves.
        for engine in (window.transcript_screen, window.note_screen):
            assert tabs.indexOf(engine) == -1
            assert review.isAncestorOf(engine)
        assert review.transcript_screen is window.transcript_screen
        assert review.note_screen is window.note_screen
        _close(window)

    def test_show_page_lands_on_the_page_that_holds_the_widget(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from PySide6.QtWidgets import QLabel

        window = _window(tmp_path)
        tabs = window.tabs
        for target in (window.transcript_screen, window.note_screen, window.note_screen.note_body):
            window.show_page(window.session_screen)
            assert tabs.currentWidget() is window.session_screen
            window.show_page(target)
            assert tabs.currentWidget() is window.review_screen
        window.show_page(window.recovery_screen)
        assert tabs.currentWidget() is window.recovery_screen
        stray = QLabel()  # outside the window: nothing to show
        window.show_page(stray)
        assert tabs.currentWidget() is window.recovery_screen
        stray.deleteLater()
        _close(window)

    def test_each_route_to_an_engine_lands_on_review(self, qapp: Any, tmp_path: Path) -> None:
        """The live transcript, a recovered one, a draft and Cancel review
        all land on the Review page (four of the seven routing sites; the
        adopted-session and closing sites are pinned in ``test_ui_screens.py``
        and ``test_unreviewed_review.py``)."""
        window = _window(tmp_path, _queued_controller())
        tabs = window.tabs
        _show_queued(qapp, window)
        assert tabs.currentWidget() is window.review_screen
        window.show_page(window.session_screen)
        window._on_draft_ready(_note_result())
        assert tabs.currentWidget() is window.review_screen
        window.show_page(window.session_screen)
        window.note_screen.cancel_review()
        assert tabs.currentWidget() is window.review_screen
        window.transcript_screen.on_discard()
        window.show_page(window.session_screen)
        outcome = RecoveryOutcome(document=_document(), crypto=SessionCrypto(), store_finished=True)
        window.recovery_screen.recovered.emit((tmp_path / uuid.uuid4().hex, outcome))
        qapp.processEvents()
        assert tabs.currentWidget() is window.review_screen
        _close(window)

    def test_leaving_past_sessions_for_review_still_clears_it(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """C7: ``_on_tab_changed``'s identity rule holds through ``show_page``."""
        window = _window(tmp_path)
        left: list[str] = []
        window.past_sessions_screen.on_left = lambda: left.append("left")
        window.tabs.setCurrentWidget(window.past_sessions_screen)
        left.clear()
        window.show_page(window.note_screen)
        assert window.tabs.currentWidget() is window.review_screen
        assert left == ["left"]
        _close(window)


# --- Task 2.2: the button row and the status strip -------------------------------------


class TestRowAndStrip:
    def test_the_row_holds_the_five_everyday_buttons_in_order(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window = _window(tmp_path)
        note, transcript = window.note_screen, window.transcript_screen
        assert _row_widgets(window.review_screen) == [
            note.save_button,
            note.write_button,
            note.copy_button,
            None,  # the stretch: Complete and Discard sit on the right
            transcript.complete_button,
            transcript.discard_button,
        ]
        # Decision 0.2, option (a) as built: the two review escapes stay in the
        # note engine's own row, beside each other, never on the bottom row.
        for escape in (note.cancel_button, note.abandon_button):
            assert note.isAncestorOf(escape)
            assert escape not in _row_widgets(window.review_screen)
        for button in _row_widgets(window.review_screen):
            if button is not None:
                assert not note.isAncestorOf(button)
                assert not transcript.isAncestorOf(button)
        _close(window)

    def test_keyboard_order_follows_the_row(self, qapp: Any, tmp_path: Path) -> None:
        window = _window(tmp_path)
        buttons = [b for b in _row_widgets(window.review_screen) if b is not None]
        for first, second in pairwise(buttons):
            assert first.nextInFocusChain() is second
        _close(window)

    def test_the_strip_holds_the_four_lines_in_order(self, qapp: Any, tmp_path: Path) -> None:
        window = _window(tmp_path)
        note, transcript = window.note_screen, window.transcript_screen
        assert _strip_widgets(window.review_screen) == [
            transcript.message_label,
            note.message_label,
            note.write_label,
            note.shadow_label,
        ]
        _close(window)

    def test_the_adopted_widgets_keep_their_text_and_wiring(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """The move changes no text, tooltip or connection: a click still
        reaches the engine that owns the button."""
        window = _window(tmp_path, _queued_controller())
        note, transcript = window.note_screen, window.transcript_screen
        assert note.save_button.text() == models.SAVE_BUTTON_LABEL
        assert note.copy_button.text() == "Copy note"
        assert transcript.complete_button.text() == "Complete"
        assert transcript.complete_button.toolTip() == models.COMPLETE_TOOLTIP
        assert transcript.discard_button.text() == "Discard"
        _show_queued(qapp, window)
        transcript.discard_button.click()
        assert ("discard",) in window._controller.calls
        assert transcript.message_label.text() == (
            "Session discarded (audio cryptographically deleted)."
        )
        _close(window)


# --- Task 2.3: the panes ------------------------------------------------------------------


class TestPanes:
    def test_the_right_column_is_generate_over_the_note_over_edit(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window = _window(tmp_path)
        review = window.review_screen
        note, transcript = window.note_screen, window.transcript_screen
        right = review.right_pane.layout()
        order = [right.itemAt(index).widget() for index in range(right.count())]
        # Task S.2: the Generate group's holder, its folded row, the note, Edit.
        assert order == [review.generate_holder, review.generate_summary, note, note.edit_group]
        assert review.generate_holder.isAncestorOf(transcript.generate_box)
        # The left pane is the Transcript engine whole, its display-only view
        # still its own; the note engine's duplicate pane is hidden. The right
        # column scrolls (Task S.2).
        assert review.splitter.widget(0) is transcript
        assert review.splitter.widget(1) is review.right_scroll
        assert review.right_scroll.widget() is review.right_pane
        assert transcript.isAncestorOf(transcript.transcript_view)
        assert note.transcript_pane.isHidden()
        assert note.transcript_pane.isAncestorOf(note.transcript_view)
        assert not note.transcript_pane.isAncestorOf(note.edit_group)
        # The next-patient row travels inside the Generate group (R1, R9).
        for widget in (transcript.next_patient_label, transcript.remove_tail_button):
            assert transcript.generate_box.isAncestorOf(widget)
        # Check 4's tools travel inside "Edit the note" (R1).
        for widget in (note.flagged_only_checkbox, note.flagged_count_label):
            assert note.edit_group.isAncestorOf(widget)
        _close(window)

    def test_the_hidden_duplicate_keeps_its_display_only_flags(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from PySide6.QtCore import Qt

        window = _window(tmp_path)
        none = Qt.TextInteractionFlag.NoTextInteraction
        assert window.note_screen.transcript_view.textInteractionFlags() == none
        assert window.transcript_screen.transcript_view.textInteractionFlags() == none
        _close(window)


class TestStateMatrix:
    """Task 2.3's states, through the window. Each control's state is the
    engines' own logic; the matrix shows the move changed none of it."""

    def test_no_session(self, qapp: Any, tmp_path: Path) -> None:
        window = _window(tmp_path)
        note, transcript = window.note_screen, window.transcript_screen
        assert transcript.transcript_view.placeholderText() == "No transcript loaded."
        assert transcript.transcript_view.toPlainText() == ""
        assert transcript.generate_box.isHidden()
        assert not _shown(transcript.generate_box, window)
        for button in (note.save_button, note.copy_button):
            assert not button.isEnabled()
        assert note.write_button.isHidden()
        assert not transcript.complete_button.isEnabled()
        assert not transcript.discard_button.isEnabled()
        _close(window)

    def test_recording(self, qapp: Any, tmp_path: Path) -> None:
        window = _window(tmp_path)
        transcript = window.transcript_screen
        window.session_screen.session_started.emit()
        assert _shown(transcript.live_header_label, window)
        assert transcript.generate_box.isHidden()
        assert not transcript.complete_button.isEnabled()
        assert not transcript.discard_button.isEnabled()
        assert not window.note_screen.save_button.isEnabled()
        window.session_screen.session_discarded.emit()
        assert not _shown(transcript.live_header_label, window)
        _close(window)

    def test_queued_with_no_note(self, qapp: Any, tmp_path: Path) -> None:
        window = _window(tmp_path, _queued_controller())
        note, transcript = window.note_screen, window.transcript_screen
        _show_queued(qapp, window)
        assert _shown(transcript.generate_box, window)
        assert transcript.generate_button.text() == models.GENERATE_NOTE_LABEL
        assert transcript.complete_button.isEnabled()
        assert transcript.discard_button.isEnabled()
        assert not note.save_button.isEnabled()
        assert not note.copy_button.isEnabled()
        assert note.write_button.isHidden()  # unlinked: no Cliniko note to write
        _close(window)

    def test_generating_then_a_draft_under_review(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(models, "COPY_TO_CLINIKO_ENABLED", True)
        window = _window(tmp_path, _queued_controller())
        note, transcript = window.note_screen, window.transcript_screen
        _show_queued(qapp, window)
        _start_generation(qapp, window)
        # Generating: the lease is held, nothing completes or discards.
        assert transcript.is_busy
        assert not transcript.complete_button.isEnabled()
        assert not transcript.discard_button.isEnabled()
        _await_draft(qapp, window)
        # The draft under review: the note on the right, Save per ratification.
        assert window.tabs.currentWidget() is window.review_screen
        assert note.note_body.toPlainText() != ""
        assert _shown(note.note_body, window)
        assert _shown(note.edit_group, window)
        assert not note.save_button.isEnabled()  # proposals pending
        assert not note.copy_button.isEnabled()  # not saved
        # Write is bound to the live session: shown, disabled, with its line.
        assert not note.write_button.isHidden()
        assert not note.write_button.isEnabled()
        assert note.write_label.text() == models.write_line("not_saved")
        assert _shown(note.write_label, window)
        assert not transcript.complete_button.isEnabled()
        reason = transcript.complete_button.toolTip()
        assert reason and reason != models.COMPLETE_TOOLTIP
        assert note.cancel_button.isEnabled()
        assert note.abandon_button.isEnabled()
        _close(window)

    def test_saved(self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from PySide6.QtCore import Qt

        monkeypatch.setattr(models, "COPY_TO_CLINIKO_ENABLED", True)
        window = _window(tmp_path, _queued_controller())
        note, transcript = window.note_screen, window.transcript_screen
        _show_queued(qapp, window)
        _start_generation(qapp, window)
        _await_draft(qapp, window)
        _ratify_and_save(window, monkeypatch)
        assert not transcript.is_busy  # the lease went with the write
        assert note.copy_button.isEnabled()
        assert note.note_body.textInteractionFlags() != Qt.TextInteractionFlag.NoTextInteraction
        assert transcript.complete_button.isEnabled()
        # D14 as changed by Task S.2 (practitioner, 2026-10-20): beside the
        # saved note Generate is folded to one row, and reachable by Change.
        assert not _shown(transcript.generate_box, window)
        assert _shown(window.review_screen.generate_summary, window)
        window.review_screen.change_generate_button.click()
        assert _shown(transcript.generate_box, window)
        # As on 0.3.3's Note tab (`test_an_unlinked_session_never_reads_the_
        # record`): a live session's note is bound, so Write shows, disabled,
        # with the unlinked line — hidden only with no binding.
        assert not note.write_button.isHidden()
        assert not note.write_button.isEnabled()
        assert note.write_label.text() == models.write_line("unlinked")
        assert note.write_button.toolTip() == models.write_line("unlinked")
        _close(window)

    def test_written(self, qapp: Any, tmp_path: Path) -> None:
        from scribe_desktop.draft_write import WriteRecordStatus

        controller = _queued_controller()
        controller.write_status = WriteRecordStatus("written", note_matches=True)
        window = _window(tmp_path, controller)
        transcript = window.transcript_screen
        window.session_screen.transcript_ready.emit(_document())
        qapp.processEvents()
        transcript.complete_button.click()
        qapp.processEvents()
        assert ("complete_after_write",) in controller.calls
        assert ("complete",) not in controller.calls
        assert window.session_screen.message_label.text() == models.write_line("written_done")
        assert window.tabs.currentWidget() is window.session_screen
        _close(window)

    def test_recovered(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        window = _window(tmp_path, controller)
        transcript = window.transcript_screen
        directory = tmp_path / uuid.uuid4().hex
        outcome = RecoveryOutcome(document=_document(), crypto=SessionCrypto(), store_finished=True)
        window.recovery_screen.recovered.emit((directory, outcome))
        qapp.processEvents()
        assert window.tabs.currentWidget() is window.review_screen
        assert "[Margaret?]" in transcript.transcript_view.toPlainText()
        assert transcript.generate_box.isHidden()  # no generation on the recovered path
        assert transcript.complete_button.isEnabled()
        assert transcript.discard_button.isEnabled()
        transcript.discard_button.click()  # one click
        assert ("discard_recovered", directory) in controller.calls
        _close(window)

    def test_shadow(self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from PySide6.QtCore import Qt

        monkeypatch.setattr(models, "COPY_TO_CLINIKO_ENABLED", True)
        window = _window(tmp_path, _queued_controller(SessionMode.SHADOW))
        note = window.note_screen
        _show_queued(qapp, window)
        _start_generation(qapp, window)
        _await_draft(qapp, window)
        assert note.shadow
        assert _shown(note.shadow_label, window)
        assert note.shadow_label.text() == models.SHADOW_NOTE_LINE
        _ratify_and_save(window, monkeypatch)
        assert not note.copy_button.isEnabled()
        assert note.copy_button.toolTip() == models.SHADOW_COPY_REFUSED
        assert note.note_body.textInteractionFlags() == Qt.TextInteractionFlag.NoTextInteraction
        _close(window)


class TestReconciliationRows:
    """R6: where the 0.3.1-0.3.3 elements sit on the Review screen."""

    def _boundary_window(self, qapp: Any, tmp_path: Path) -> tuple[Any, Any, Any]:
        config = load_note_config(trim.VALIDATION_CONFIG)
        document = trim._document(uuid.uuid4().hex)
        controller = trim._TrimController(document)
        window = _main_window(tmp_path, controller, profile_root=tmp_path / "profile")
        window.transcript_screen._config_loader = lambda: config
        window.transcript_screen._confirm_remove = trim._Confirm()
        window.session_screen.transcript_ready.emit(document)
        qapp.processEvents()
        return window, controller, config

    def test_a_boundary_shows_the_line_and_the_removal_at_the_top_right(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """(a): the next-patient line and Remove lines... show at the top of
        the right column, inside the Generate group; the trim's done line is
        in the strip."""
        window, controller, _config = self._boundary_window(qapp, tmp_path)
        transcript = window.transcript_screen
        right = window.review_screen.right_pane.layout()
        assert right.itemAt(0).widget() is window.review_screen.generate_holder  # Task S.2
        assert window.review_screen.generate_holder.isAncestorOf(transcript.generate_box)
        assert _shown(transcript.next_patient_label, window)
        assert _shown(transcript.remove_tail_button, window)
        assert transcript.next_patient_label.text().startswith(
            f"A possible next patient starts at line {trim._BOUNDARY + 1} ["
        )
        assert transcript.remove_tail_button.isEnabled()
        transcript.remove_tail_button.click()
        assert [call for call in controller.calls if call[0] == "trim_transcript"]
        assert transcript.message_label.text() == models.remove_tail_done_line(
            trim._BOUNDARY, len(trim._TURNS)
        )
        assert window.review_screen.status_strip.isAncestorOf(transcript.message_label)
        _close(window)

    def test_a_boundary_removal_is_refused_while_a_review_is_open(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window, controller, config = self._boundary_window(qapp, tmp_path)
        transcript = window.transcript_screen
        result = _note_result()
        transcript._note_generator_factory = lambda **_kw: lambda _d, _c: result
        transcript.set_role(trim._C)
        transcript.set_profile(config.template_profiles[0].template_profile_id)
        transcript.generate()
        _await_draft(qapp, window)
        # Task S.2: the review folds the group; Change shows it as it is.
        assert not _shown(transcript.remove_tail_button, window)
        window.review_screen.change_generate_button.click()
        assert _shown(transcript.remove_tail_button, window)
        assert not transcript.remove_tail_button.isEnabled()
        assert transcript.remove_tail_button.toolTip() == models.REMOVE_TAIL_REVIEW_OPEN
        assert not [call for call in controller.calls if call[0] == "trim_transcript"]
        _close(window)

    def test_check_6_survives_acknowledge_all_and_the_chooser_is_marked(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """(b): the possible-next-patient row stays after "Acknowledge all",
        and every chooser entry from the boundary on carries the front mark."""
        from PySide6.QtWidgets import QLabel

        turns = (
            *_NOTE_TURNS,
            ("Okay, see you next week.", SPEAKER_2),  # 4: the closing
            ("Hello, come on in.", SPEAKER_1),  # 5: the greeting - the boundary
            ("My right shoulder hurts.", SPEAKER_1),  # 6
        )
        boundary = 5
        window = _window(tmp_path, _queued_controller())
        window._on_draft_ready(_edit_result(turns))
        note = window.note_screen
        assert window.tabs.currentWidget() is window.review_screen
        note._acknowledge_all()
        assert "possible_next_patient" not in note._acknowledged
        title = models.WARNING_COPY["possible_next_patient"].title
        rows = [note._review_box.itemAt(i).widget() for i in range(note._review_box.count())]
        texts = [label.text() for row in rows for label in row.findChildren(QLabel)]
        assert any(text.startswith(title) for text in texts)
        assert all(_shown(row, window) for row in rows)
        combo = note.utterance_combo
        assert _shown(combo, window)
        for position in range(combo.count()):
            index = combo.itemData(position)
            marked = models.NEXT_PATIENT_LINE_MARK in combo.itemText(position)
            assert marked is (index >= boundary)
        note.clear()
        _close(window)

    def test_check_4_tools_sit_under_the_note(self, qapp: Any, tmp_path: Path) -> None:
        """(c): the flagged rows, the filter and the count line are in "Edit
        the note", under the note in the right column."""
        window = _window(tmp_path, _queued_controller())
        window._on_draft_ready(_edit_result())
        note = window.note_screen
        line = _routed_line(note, _PLAN_INDEX)
        assert note.remove_line(line.assertion_id) is True
        assert _shown(note.flagged_count_label, window)
        assert _shown(note.flagged_only_checkbox, window)
        right = window.review_screen.right_pane.layout()
        assert right.indexOf(note) < right.indexOf(note.edit_group)
        rows = [note._lines_box.itemAt(i).widget() for i in range(note._lines_box.count())]
        assert rows and all(note.edit_group.isAncestorOf(row) for row in rows)
        note.clear()
        _close(window)


# --- Task 2.4: variants --------------------------------------------------------------------


def test_the_everyday_and_destructive_buttons_carry_their_variants(
    qapp: Any, tmp_path: Path
) -> None:
    """Task 2.4 (C5, C13): the variant is a property only — every text stays."""
    window = _window(tmp_path)
    primary = {
        window.session_screen.start_button: "Start",
        window.note_screen.save_button: models.SAVE_BUTTON_LABEL,
        window.clinics_screen.validate_button: "Validate",
    }
    danger = {
        window.session_screen.discard_button: "Discard",
        window.transcript_screen.discard_button: "Discard",
        window.past_sessions_screen.delete_button: "Delete now",
        window.past_sessions_screen.delete_recording_button: "Delete recording",
        window.practitioner_screen.delete_button: "Delete voice profile",
        window.practitioner_screen.delete_style_button: "Delete learned style",
    }
    for buttons, variant in ((primary, "primary"), (danger, "danger")):
        for button, text in buttons.items():
            assert button.property("variant") == variant
            assert button.text() == text
    assert window.transcript_screen.change_role_button.property("variant") == "link"
    _close(window)
