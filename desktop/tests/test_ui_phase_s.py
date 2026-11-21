"""UI refresh plan Phase S (stage-7): the fixes for the 0.4.0 live smoke's
findings that are about the window as a whole.

- S.2 (F5): while a note is under review or saved, the Review screen folds the
  Generate note group to one row (a speaker label and a profile name, never a
  quoted transcript sentence) with "Change"; the right column scrolls; the
  note body keeps about twelve lines; every review-warning row keeps its
  Acknowledge button at its size hint.
- S.3 (F7): Past sessions' transcript pane has room once "Show transcript"
  is pressed (the heading at the bottom over nothing is the collapsed state).
- S.5 (F6): the note body's right-click menu, delivered as Qt delivers it — a
  real ``QContextMenuEvent`` to the body's viewport, and a real right-button
  click on the window (platform input) under both of Qt's context-menu
  triggers — never by calling the menu builder.
- S.6 (F4): a pause cue leaves the status bar on every Resume and at Finish;
  the hotkey Resume's own line is unchanged.
- S.7 (F3): ``app.main()`` declares the channel's taskbar identity once,
  before the ``QApplication`` (so before any window).
- S.9 (F8): at 150 % on 1920 x 1200 the right column fits across in every
  state it takes — never a sideways scroll bar, nothing cut on either side.
- S.10 (F9): every review warning row shows its whole text, its label at
  least its height for its width, at 150 % and 100 %, folded and unfolded.
- S.11 (F10): every "Lines in the note" row shows its whole text with its
  controls whole under it, and nothing but the column scrolls above it.

The fixes are about what the practitioner sees, so these tests lay windows out
for real (shown, offscreen) where a size matters, and drive real events. Each
window is built here and closed here; the theme is never re-applied to the
whole application. Synthetic transcripts and notes only."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Final

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QObject  # noqa: E402

from conftest import TaskbarGuard, use_channel  # noqa: E402
from scribe_desktop import identity  # noqa: E402
from scribe_desktop.context_rules import PauseReason  # noqa: E402
from scribe_desktop.encounter import unlinked_consent  # noqa: E402
from scribe_desktop.install_layout import Channel  # noqa: E402
from scribe_desktop.session import RecordingSession, SessionState  # noqa: E402
from scribe_desktop.session_mode import SessionMode  # noqa: E402
from scribe_desktop.transcription import SPEAKER_1, SPEAKER_2  # noqa: E402
from scribe_desktop.ui import models, review  # noqa: E402
from test_ui_review import (  # noqa: E402
    _await_draft,
    _queued_controller,
    _ratify_and_save,
    _show_queued,
    _start_generation,
)
from test_ui_review import _window as _review_window  # noqa: E402
from test_ui_screens import (  # noqa: E402
    _NOTE_TURNS,
    FakeController,
    _edit_result,
    _note_document,
    _ps_entry,
)
from test_ui_screens import _main_window as _screens_main_window  # noqa: E402


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


# Codex round 34 PR-LOW-002: every window this module builds is registered
# the moment it exists, so a failing assertion can never leave it — its
# signal connections and workers — alive in the shared application.
_open_windows: list[Any] = []


def _window(tmp_path: Path, controller: Any | None = None) -> Any:
    window = _review_window(tmp_path, controller)
    _open_windows.append(window)
    return window


def _main_window(tmp_path: Path, *args: Any, **kwargs: Any) -> Any:
    window = _screens_main_window(tmp_path, *args, **kwargs)
    _open_windows.append(window)
    return window


def _close(window: Any) -> None:
    """Close and delete a window this module built, once its worker threads
    are done (a running ``QThread`` must never be destroyed). Once only: a
    window the test closed itself is not closed again by the teardown."""
    from PySide6.QtCore import QThread

    if not any(open_window is window for open_window in _open_windows):
        return
    _open_windows[:] = [open_window for open_window in _open_windows if open_window is not window]
    for thread in window.findChildren(QThread):
        thread.wait(5000)
    window.close()
    window.deleteLater()


@pytest.fixture(autouse=True)
def _windows_closed() -> Iterator[None]:
    """Closes whatever window a test left open — on a failed assertion
    above all — with the same worker-aware ``_close``."""
    yield
    for window in list(_open_windows):
        _close(window)


def _shown(widget: Any, window: Any) -> bool:
    return bool(widget.isVisibleTo(window.review_screen))


def _laid_out(qapp: Any, window: Any, width: int, height: int) -> None:
    """Show ``window`` at ``width`` x ``height`` and let Qt lay it out."""
    window.resize(width, height)
    window.show()
    qapp.processEvents()
    qapp.processEvents()


# The next-patient turns of `test_ui_review`'s Check 6 case: a draft with a
# review row that "Acknowledge all" never clears, beside the note's others.
_BOUNDARY_TURNS = (
    *_NOTE_TURNS,
    ("Okay, see you next week.", SPEAKER_2),
    ("Hello, come on in.", SPEAKER_1),
    ("My right shoulder hurts.", SPEAKER_1),
)


# --- S.2: the folded Generate group, the scrolling column -----------------------------


class TestGenerateFold:
    def test_a_draft_folds_generate_to_one_row_of_a_label_and_a_name(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window = _window(tmp_path, _queued_controller())
        screen, transcript = window.review_screen, window.transcript_screen
        _show_queued(qapp, window)
        # No note yet: the group itself, no folded row.
        assert not screen.generate_folded
        assert _shown(transcript.generate_box, window)
        assert not _shown(screen.generate_summary, window)
        _start_generation(qapp, window)
        _await_draft(qapp, window)
        assert screen.generate_folded
        assert not _shown(transcript.generate_box, window)
        assert _shown(screen.generate_summary, window)
        assert _shown(screen.change_generate_button, window)
        assert screen.change_generate_button.text() == models.GENERATE_CHANGE_LABEL
        profile = transcript.profile_combo.currentText()
        assert profile and transcript.selected_profile_id() == "clinic-a"
        text = screen.generate_summary_label.text()
        assert text == models.generate_summary_text(SPEAKER_2, profile)
        # A speaker LABEL and a profile NAME — no quoted transcript sentence,
        # though the clinician's radio quotes one (no new display of
        # transcript text).
        assert '"' not in text
        for sentence, _speaker in _NOTE_TURNS:
            assert sentence not in text
        assert sentence_quoted_in_a_radio(transcript)
        # Folding is visibility only: the group is where it was, unchanged.
        assert screen.generate_holder.isAncestorOf(transcript.generate_box)
        assert not transcript.generate_box.isHidden()
        assert transcript.generate_button.isEnabled() is False  # the lease is held
        _close(window)

    def test_change_unfolds_and_a_new_draft_folds_again(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = _window(tmp_path, _queued_controller())
        screen, transcript, note = (
            window.review_screen,
            window.transcript_screen,
            window.note_screen,
        )
        _show_queued(qapp, window)
        _start_generation(qapp, window)
        _await_draft(qapp, window)
        assert screen.generate_folded
        screen.change_generate_button.click()
        assert not screen.generate_folded
        assert _shown(transcript.generate_box, window)
        assert not _shown(screen.generate_summary, window)
        # Save keeps the unfolded group as it is.
        _ratify_and_save(window, monkeypatch)
        assert not screen.generate_folded
        assert _shown(transcript.generate_box, window)
        assert transcript.generate_button.isEnabled()  # Regenerate is reachable
        # A new draft (Regenerate) folds again.
        _start_generation(qapp, window)
        _await_draft(qapp, window)
        assert screen.generate_folded
        assert note.current_note() is not None
        _close(window)

    def test_a_saved_note_stays_folded_and_cancel_review_unfolds(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = _window(tmp_path, _queued_controller())
        screen, transcript, note = (
            window.review_screen,
            window.transcript_screen,
            window.note_screen,
        )
        _show_queued(qapp, window)
        _start_generation(qapp, window)
        _await_draft(qapp, window)
        _ratify_and_save(window, monkeypatch)
        assert screen.generate_folded  # Save changes nothing about the fold
        # Cancel review and regenerate: the review is cleared, the group back.
        _start_generation(qapp, window)
        _await_draft(qapp, window)
        assert screen.generate_folded
        note.cancel_review()
        assert note.current_note() is None
        assert not screen.generate_folded
        assert _shown(transcript.generate_box, window)
        _close(window)

    def test_a_cleared_review_forgets_change_and_a_discard_unfolds(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window = _window(tmp_path, _queued_controller())
        screen, transcript, note = (
            window.review_screen,
            window.transcript_screen,
            window.note_screen,
        )
        _show_queued(qapp, window)
        _start_generation(qapp, window)
        _await_draft(qapp, window)
        screen.change_generate_button.click()
        assert not screen.generate_folded
        # The review is cleared: "Change" is forgotten, so the next note folds.
        note.cancel_review()
        assert not screen.generate_folded
        _start_generation(qapp, window)
        _await_draft(qapp, window)
        assert screen.generate_folded
        # Discard: the transcript engine hides its group, the row goes too.
        note.cancel_review()
        transcript.on_discard()
        assert transcript.generate_box.isHidden()
        assert not screen.generate_folded
        assert not _shown(screen.generate_summary, window)
        _close(window)

    def test_no_note_and_no_generation_shows_neither(self, qapp: Any, tmp_path: Path) -> None:
        window = _window(tmp_path)
        screen = window.review_screen
        assert not screen.generate_folded
        assert screen.generate_summary.isHidden()
        assert window.transcript_screen.generate_box.isHidden()
        _close(window)


def sentence_quoted_in_a_radio(transcript: Any) -> bool:
    """The clinician radios DO quote a transcript sentence (what the folded
    row must not repeat)."""
    return any('"' in radio.text() for radio in transcript._role_buttons.values())


class TestRightColumn:
    def test_the_column_scrolls_and_the_note_keeps_twelve_lines(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window = _window(tmp_path, _queued_controller())
        screen, note = window.review_screen, window.note_screen
        assert screen.splitter.widget(1) is screen.right_scroll
        assert screen.right_scroll.widget() is screen.right_pane
        assert screen.right_scroll.widgetResizable()
        body = note.note_body
        lines = body.fontMetrics().lineSpacing() * review.NOTE_BODY_MIN_LINES
        assert body.minimumHeight() >= lines
        right = screen.right_pane.layout()
        assert right.stretch(right.indexOf(note)) == 1
        assert right.stretch(right.indexOf(note.edit_group)) == 0
        _close(window)

    @pytest.mark.parametrize(
        ("width", "height"), [(1920, 1200), (1280, 690)], ids=["1920x1200", "1280x690"]
    )
    def test_a_note_with_review_warnings_squeezes_nothing(
        self, qapp: Any, tmp_path: Path, width: int, height: int
    ) -> None:
        """The smoke's F5, laid out for real: after Generate, at the
        practitioner's 1920 x 1200 and at a 1080p screen's 150 % work area,
        the note body shows at least its twelve lines and every review-warning
        row shows its label's whole text and its Acknowledge button at no less
        than its size hint (it collapsed to a sliver before)."""
        from PySide6.QtWidgets import QLabel, QPushButton

        window = _window(tmp_path, _queued_controller())
        note = window.note_screen
        window.session_screen.transcript_ready.emit(_note_document(_BOUNDARY_TURNS))
        qapp.processEvents()
        window._on_draft_ready(_edit_result(_BOUNDARY_TURNS))
        assert window.review_screen.generate_folded
        _laid_out(qapp, window, width, height)
        try:
            assert window.tabs.currentWidget() is window.review_screen
            body = note.note_body
            assert body.height() >= body.minimumHeight()
            assert body.minimumHeight() >= (
                body.fontMetrics().lineSpacing() * review.NOTE_BODY_MIN_LINES
            )
            rows = [note._review_box.itemAt(i).widget() for i in range(note._review_box.count())]
            assert rows
            buttons = [button for row in rows for button in row.findChildren(QPushButton)]
            assert buttons  # at least one row still to acknowledge
            for button in buttons:
                assert button.text() == "Acknowledge"
                assert button.height() >= button.sizeHint().height()
            for row in rows:
                for label in row.findChildren(QLabel):
                    assert label.height() >= label.heightForWidth(label.width())
        finally:
            note.clear()
            _close(window)


# --- S.9: at 150 % the right column never scrolls sideways ------------------------------

# A clinician radio quotes up to 90 characters of its speaker's first line
# (`models.speaker_quotations`); this first line is longer, so the radio is as
# wide as one gets.
_WIDE_TURNS = (
    (
        "My left knee is sore when I walk down the stairs, and it aches at night "
        "after a long day standing at work",
        SPEAKER_1,
    ),
    *_NOTE_TURNS[1:],
)
_WIDE_BOUNDARY_TURNS = (*_WIDE_TURNS, *_BOUNDARY_TURNS[len(_NOTE_TURNS) :])

# The practitioner's 1920 x 1200 screen at 150 % is 1280 x 800 logical; less
# the taskbar, a maximised window is about 1280 x 770 — about 180 average
# characters across and 42 lines down in the app's 10 pt Segoe UI. The window
# is sized in THOSE units of whatever font the test platform has, so it holds
# the same text the practitioner's does (the offscreen font is far wider than
# Segoe UI, so a fixed pixel size would stand in for a much smaller screen).
_AT_150_CHARS_LINES: Final = (180, 42)
# The same screen at 100 %: about 1920 x 1150 px, 274 characters by 64 lines.
_AT_100_CHARS_LINES: Final = (274, 64)


def _stand_in(window: Any, chars_lines: tuple[int, int]) -> tuple[int, int]:
    metrics = window.fontMetrics()
    chars, lines = chars_lines
    return chars * metrics.averageCharWidth(), lines * metrics.lineSpacing()


def _at_150(window: Any) -> tuple[int, int]:
    return _stand_in(window, _AT_150_CHARS_LINES)


class TestRightColumnWidth:
    """F8 (the 2026-10-21 re-check): at 150 % on 1920 x 1200 the right column
    was wider than its pane — a sideways scroll bar, the consent paragraph cut
    mid-word, the Template profile box past the edge — because the scroll
    area asked the splitter for almost no width while the transcript pane's
    legend held its side at one long line. Laid out for real, in every state
    the column takes, its content fits across and each side of the splitter
    has at least its own minimum. The window is the 150 % stand-in in the
    test font's characters and lines (``_at_150``), and the checks compare
    widths with each other, never with a pixel count. With the fix reverted
    the three states that show the clinician radios fail (the radio is wider
    than the column the splitter gave); the folded state holds the fix with a
    note shown."""

    @pytest.mark.parametrize(
        "state", ["before-generate", "next-patient", "note-folded", "note-unfolded"]
    )
    def test_the_column_fits_across_at_150_percent(
        self, qapp: Any, tmp_path: Path, state: str
    ) -> None:
        window = _window(tmp_path, _queued_controller())
        screen, transcript, note = (
            window.review_screen,
            window.transcript_screen,
            window.note_screen,
        )
        try:
            turns = _WIDE_TURNS if state == "before-generate" else _WIDE_BOUNDARY_TURNS
            window.session_screen.transcript_ready.emit(_note_document(turns))
            qapp.processEvents()
            if state.startswith("note-"):
                window._on_draft_ready(_edit_result(turns))
                assert screen.generate_folded
                assert note._review_box.count()  # review warnings are shown
            window.show_page(screen)
            _laid_out(qapp, window, *_at_150(window))
            if state == "note-unfolded":
                # "Change" on the shown window: the column's new, wider
                # minimum has to reach the splitter.
                screen.change_generate_button.click()
                for _ in range(3):
                    qapp.processEvents()
            assert window.tabs.currentWidget() is screen
            radios_shown = state != "note-folded"
            assert screen.generate_folded is not radios_shown
            assert _shown(transcript.next_patient_label, window) is (
                state in {"next-patient", "note-unfolded"}
            )
            if radios_shown:
                assert any(
                    _shown(radio, window) and '..."' in radio.text()
                    for radio in transcript._role_buttons.values()
                )
            scroll = screen.right_scroll
            viewport = scroll.viewport().width()
            # Nothing to scroll sideways to: the content is no wider than
            # what shows of it.
            assert screen.right_pane.width() <= viewport
            assert scroll.horizontalScrollBar().maximum() == 0
            consent = note.consent_reminder_label
            assert _shown(consent, window)
            assert consent.width() <= viewport
            # Each side has at least its own minimum: nothing is cut on the
            # transcript side either, and its legend shows whole.
            assert transcript.width() >= transcript.minimumSizeHint().width()
            assert scroll.width() >= scroll.minimumSizeHint().width()
            legend = transcript.legend_label
            assert legend.height() >= legend.heightForWidth(legend.width())
        finally:
            note.clear()
            _close(window)

    def test_the_longest_chooser_entry_and_count_line_fit_at_150_percent(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Phase M, M.3 (a) (R11): 0.3.4–0.3.7 made the Line chooser's entries
        and the count line longer — `[flagged]`, `[next patient?]` and
        `[suggested: <title>]` before the speaker, and the count line's
        flagged, suggested and not-assessed clauses. The worst case of each,
        in the chooser and the count line when the column is first laid out
        at 150 %, still leaves the column nothing to scroll sideways, and the
        count line shows whole. The app never puts `[next patient?]` and
        `[suggested: …]` on one entry (a suggestion is accepted only before
        the boundary); the entry carries both as the widest possible label.
        With M.3's one production change reverted (the combo sized by a
        minimum contents length), the column's content is wider than its
        viewport and this fails."""
        from scribe_desktop.note import SECTION_TITLES

        window = _window(tmp_path, _queued_controller())
        screen, note = window.review_screen, window.note_screen
        try:
            window.session_screen.transcript_ready.emit(_note_document(_WIDE_BOUNDARY_TURNS))
            qapp.processEvents()
            window._on_draft_ready(_edit_result(_WIDE_BOUNDARY_TURNS))
            longest = max(SECTION_TITLES.values(), key=len)
            words = _WIDE_TURNS[0][0]
            entry = (
                f"99. {models.FLAGGED_LINE_MARK}{models.NEXT_PATIENT_LINE_MARK}"
                f"{models.SUGGESTED_LINE_MARK.format(title=longest)}{SPEAKER_1}: "
                f"{words[:60].rstrip()}..."
            )
            # The first offered line's entry carries the widest label (its
            # segment stays the line's own, so choosing it works as usual).
            combo = note.utterance_combo
            assert combo.count() > 0
            combo.setItemText(0, entry)
            combo.setCurrentIndex(0)
            count_line = models.flagged_count_line(
                {10, 11, 12}, {10}, suggested={20, 21}, not_assessed=7
            )
            note.flagged_count_label.setText(count_line)
            note.flagged_count_label.show()
            window.show_page(screen)
            _laid_out(qapp, window, *_at_150(window))
            for _ in range(3):
                qapp.processEvents()
            assert combo.currentText() == entry
            assert _shown(combo, window)
            # The long entry no longer sets the combo's width (with Qt's
            # default policy it did, at the combo's first show: the column's
            # content was 2909 px in a 2078 px viewport here).
            assert combo.sizeHint().width() < combo.fontMetrics().horizontalAdvance(entry)
            scroll = screen.right_scroll
            assert screen.right_pane.width() <= scroll.viewport().width()
            assert scroll.horizontalScrollBar().maximum() == 0
            label = note.flagged_count_label
            assert _shown(label, window)
            assert label.height() >= label.heightForWidth(label.width())
        finally:
            note.clear()
            _close(window)

    def test_the_lines_that_now_wrap_still_ask_for_one_line(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """The three fixed lines S.9 lets wrap — the transcript pane's legend
        and the Generate group's two — still ASK for their width on one line,
        so the splitter shares the screen out as before at every scale; only
        their minimum falls (a plain word-wrapped label asks for far less)."""
        from PySide6.QtWidgets import QLabel

        window = _window(tmp_path)
        transcript = window.transcript_screen
        confirm = [
            label
            for label in transcript.generate_box.findChildren(QLabel)
            if label.text().startswith("Confirm the clinician and template")
        ]
        assert len(confirm) == 1
        for label in (transcript.legend_label, transcript.role_prompt_label, confirm[0]):
            one_line = label.fontMetrics().size(0, label.text()).width()
            assert label.wordWrap()
            assert label.sizeHint().width() >= one_line
            assert label.minimumSizeHint().width() < one_line
        _close(window)


# --- S.10: every review warning row whole --------------------------------------------

# A patient's hedged line (the unsure mark), a clinician's line with a number
# (the number mark), then a closing and a greeting (the next-patient warning).
_WARNING_TURNS = (
    ("I think my left knee is sore when I walk", SPEAKER_1),
    *_NOTE_TURNS[1:],
    ("The plan is to review you in two weeks", SPEAKER_2),
    ("Okay, see you next week.", SPEAKER_2),
    ("Hello, come on in.", SPEAKER_1),
    ("My right shoulder hurts.", SPEAKER_1),
)


class TestWarningRowsWhole:
    """F9 (the 2026-10-21 re-check, step 4a (b)): at 150 % with the Generate
    group folded, the next-patient row's fourth wrapped line showed half and
    the rest of its sentence not at all. The note engine kept its review side
    inside its own splitter, and a splitter passes no height-for-width
    through, so the scrolling column laid the engine out at its preferred
    height: a row whose wrapped text needs more lines at the column's width
    than its preferred size was cut. Laid out for real, with the note
    delivered on the SHOWN window (as Generate delivers it), every warning
    label is at least its height for its width and ends inside its row, at
    150 % and 100 %, folded and unfolded. With the fix reverted the review
    side's height-for-width no longer reaches the column
    (``note.hasHeightForWidth()`` fails in every case); the row checks fail
    where the wrapped rows need more than their preferred heights altogether,
    as on the practitioner's screen."""

    @pytest.mark.parametrize("unfolded", [False, True], ids=["folded", "unfolded"])
    @pytest.mark.parametrize(
        "chars_lines", [_AT_150_CHARS_LINES, _AT_100_CHARS_LINES], ids=["150", "100"]
    )
    def test_every_warning_row_shows_its_whole_text(
        self, qapp: Any, tmp_path: Path, chars_lines: tuple[int, int], unfolded: bool
    ) -> None:
        from PySide6.QtWidgets import QLabel

        window = _window(tmp_path, _queued_controller())
        screen, note = window.review_screen, window.note_screen
        try:
            window.session_screen.transcript_ready.emit(_note_document(_WARNING_TURNS))
            qapp.processEvents()
            window.show_page(screen)
            _laid_out(qapp, window, *_stand_in(window, chars_lines))
            window._on_draft_ready(_edit_result(_WARNING_TURNS))
            if unfolded:
                screen.change_generate_button.click()
            for _ in range(3):
                qapp.processEvents()
            current = note.current_note()
            assert current is not None
            codes = {warning.note_warning_code for warning in current.note_warnings}
            # Phase M, M.3 (b): 0.3.4's left-out clinician line row too.
            wanted = {
                "possible_next_patient",
                "number_source",
                "hedged_source",
                "clinician_line_omitted",
            }
            assert wanted <= codes, sorted(codes)
            assert screen.generate_folded is not unfolded
            # The review side's height follows its width, up to the column.
            assert note.hasHeightForWidth()
            rows = [note._review_box.itemAt(i).widget() for i in range(note._review_box.count())]
            assert len(rows) >= len(wanted)
            for row in rows:
                assert _shown(row, window)
                [label] = row.findChildren(QLabel)
                needed = label.heightForWidth(label.width())
                assert label.height() >= needed, (label.text()[:48], label.height(), needed)
                assert label.geometry().bottom() <= row.contentsRect().bottom()
            # S.2's note body keeps its minimum.
            assert note.note_body.height() >= note.note_body.minimumHeight()
        finally:
            note.clear()
            _close(window)


# --- S.11: every "Lines in the note" row whole -----------------------------------------


class TestLineRowsWhole:
    """F10 (the 2026-10-21 re-check, step 4a (b)): in "Edit the note", a row of
    "Lines in the note" was squeezed by its controls — at 150 % its text read
    "[check:" over "number]", with a sideways scroll bar under the list; at
    100 % a third wrapped line was cut at the list's foot. Each row held its
    text and its controls on ONE line, so its minimum width was the widest
    word plus every control, and the rows sat in a short scroll box of their
    own. Now the text runs across the whole row with the controls on their
    own line under it, and the rows sit in the group itself, so the column —
    which scrolls down (S.2) and asks for its content's width (S.9) — is the
    only scrolling above them. Laid out for real, with the note delivered on
    the SHOWN window, every row's text is at least its height for its width
    and ends inside its row, every control sits under it whole, nothing but
    the column scrolls above a row, and the column has nothing to scroll
    sideways. With the fix reverted the scroll box and the controls beside
    the text fail it in every case."""

    @pytest.mark.parametrize("unfolded", [False, True], ids=["folded", "unfolded"])
    @pytest.mark.parametrize(
        "chars_lines", [_AT_150_CHARS_LINES, _AT_100_CHARS_LINES], ids=["150", "100"]
    )
    def test_every_line_row_shows_its_whole_text(
        self, qapp: Any, tmp_path: Path, chars_lines: tuple[int, int], unfolded: bool
    ) -> None:
        from PySide6.QtWidgets import QAbstractScrollArea, QComboBox, QLabel, QPushButton

        window = _window(tmp_path, _queued_controller())
        screen, note = window.review_screen, window.note_screen
        try:
            window.session_screen.transcript_ready.emit(_note_document(_WARNING_TURNS))
            qapp.processEvents()
            window.show_page(screen)
            _laid_out(qapp, window, *_stand_in(window, chars_lines))
            window._on_draft_ready(_edit_result(_WARNING_TURNS))
            if unfolded:
                screen.change_generate_button.click()
            for _ in range(3):
                qapp.processEvents()
            rows = [note._lines_box.itemAt(i).widget() for i in range(note._lines_box.count())]
            assert rows
            # A marked line (the long kind the smoke cut) is among them.
            assert any(
                "[check:" in label.text() for row in rows for label in row.findChildren(QLabel)
            )
            for row in rows:
                assert _shown(row, window)
                # Nothing but the column scrolls above a row.
                ancestor = row.parentWidget()
                while ancestor is not None and ancestor is not screen.right_scroll:
                    assert not isinstance(ancestor, QAbstractScrollArea), type(ancestor)
                    ancestor = ancestor.parentWidget()
                assert ancestor is screen.right_scroll
                [text] = [label for label in row.findChildren(QLabel) if label.wordWrap()]
                needed = text.heightForWidth(text.width())
                assert text.height() >= needed, (text.text()[:48], text.height(), needed)
                assert text.geometry().bottom() <= row.contentsRect().bottom()
                controls = [*row.findChildren(QPushButton), *row.findChildren(QComboBox)]
                assert controls
                for control in controls:
                    # Under the text, whole, inside the row.
                    assert control.geometry().top() > text.geometry().bottom()
                    assert control.width() >= control.minimumSizeHint().width()
                    assert control.geometry().right() <= row.contentsRect().right()
            assert screen.right_scroll.horizontalScrollBar().maximum() == 0
        finally:
            note.clear()
            _close(window)


# --- stronger-voice plan Task 1.2: the guided card at 150 % -----------------------------


class TestGuidedCardWidth:
    """The guided enrolment's card (review round 12 LOW-002), laid out for
    real at the 150 % stand-in (``_at_150``): for every part, and the redo's
    heading, the Practitioner tab's content fits across its scroll area (it
    has no sideways bar, so anything wider would be cut off) and each card
    label shows its whole text. A passage label that stopped word-wrapping
    would hold the content at the passage's full width and fail."""

    def test_every_part_fits_across_at_150_percent(self, qapp: Any, tmp_path: Path) -> None:
        window = _main_window(tmp_path)
        screen = window.practitioner_screen
        window.show_page(screen)
        _laid_out(qapp, window, *_at_150(window))
        try:
            assert window.tabs.currentWidget() is screen
            viewport = screen.scroll_area.viewport()
            for index, part in enumerate(models.ENROLMENT_SCRIPT):
                for redo in (False, True):
                    screen._show_part(index, part.target_speech_seconds, redo=redo)  # noqa: SLF001
                    qapp.processEvents()
                    qapp.processEvents()
                    assert screen.passage_label.text() == part.text
                    assert screen.scroll_content.width() <= viewport.width(), (index, redo)
                    for label in screen._card_labels:  # noqa: SLF001
                        assert label.isVisibleTo(screen)
                        assert label.width() <= viewport.width(), (index, label.text()[:24])
                        needed = label.heightForWidth(label.width())
                        assert label.height() >= needed, (index, label.text()[:24])
        finally:
            screen._reset_card()  # noqa: SLF001
            _close(window)


# --- S.3: Past sessions' transcript pane ------------------------------------------------


class TestPastSessionsTranscript:
    def test_show_transcript_gives_the_pane_room_at_the_minimum_window(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """F7: at a 960-wide window (the minimum) the "Transcript" heading sat
        at the bottom over nothing — the COLLAPSED state: the pane is hidden
        until "Show transcript", and the notes take the column. Once shown,
        laid out for real, the pane has room for lines."""
        from PySide6.QtCore import Qt

        window = _main_window(tmp_path)
        screen = window.past_sessions_screen
        sid, _note = _ps_entry(screen._store)
        window.rail.button_for(screen).click()
        item = screen.entry_list.item(0)
        assert item.data(Qt.ItemDataRole.UserRole) == sid
        screen.entry_list.setCurrentItem(item)
        item.setSelected(True)
        _laid_out(qapp, window, 960, 640)
        try:
            view = screen.transcript_view
            assert view.isHidden()  # collapsed until asked
            screen.transcript_button.click()
            qapp.processEvents()
            qapp.processEvents()
            assert view.isVisibleTo(screen)
            assert view.toPlainText() != ""
            assert view.height() >= 3 * view.fontMetrics().lineSpacing()
        finally:
            _close(window)


# --- S.5: the note body's right-click menu, as Qt delivers it -------------------------


class _MenuSpy:
    """The body's ``build_context_menu`` wrapped on the INSTANCE for one test
    (the pattern of `test_ui_screens`' context-menu test): the panel's own
    builder still builds the real menu — its entries' text and enabled state
    are recorded — but ``contextMenuEvent`` gets a stand-in whose ``exec``
    opens nothing. No real popup and no nested event loop ever runs:
    replacing ``QMenu.exec`` on PySide's class did not reach the call, and the
    real offscreen ``exec`` blocked the suite (stage-7 leg u7x2)."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, body: Any) -> None:
        self.opened: list[list[tuple[str, bool]]] = []
        build = body.build_context_menu
        spy = self

        class _StandIn:
            def __init__(self) -> None:
                self._menu = build()
                spy.opened.append(
                    [
                        (action.text().split("\t")[0], action.isEnabled())
                        for action in self._menu.actions()
                    ]
                )

            def exec(self, *_args: Any) -> None:
                return None

            def deleteLater(self) -> None:  # noqa: N802 - Qt spelling
                self._menu.deleteLater()

        monkeypatch.setattr(body, "build_context_menu", _StandIn)


class _EventLog(QObject):
    """An application-wide event filter that records, in order, each press,
    release and context-menu event and the object it was delivered to. It
    never consumes one. A mouse event Qt propagates up the widget chain
    reaches the application's filters once per widget, so the log shows how
    far each one went."""

    _KINDS: Final = {
        QEvent.Type.MouseButtonPress: "press",
        QEvent.Type.MouseButtonRelease: "release",
        QEvent.Type.ContextMenu: "context-menu",
    }

    def __init__(self, body: Any) -> None:
        super().__init__()
        self._body = body
        self._viewport = body.viewport()
        self.seen: list[str] = []

    def eventFilter(self, watched: QObject, event: QEvent, /) -> bool:  # noqa: N802 - Qt's name
        kind = self._KINDS.get(event.type())
        if kind is not None:
            self.seen.append(f"{kind}->{self._name(watched)}")
        return False

    def _name(self, watched: QObject) -> str:
        if watched is self._viewport:
            return "note-body viewport"
        if watched is self._body:
            return "note body"
        name = watched.objectName()
        return f"{type(watched).__name__}#{name}" if name else type(watched).__name__


def _right_click_event(body: Any) -> Any:
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QContextMenuEvent

    viewport = body.viewport()
    local = QPoint(5, 5)
    return QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse, local, viewport.mapToGlobal(local)
    )


class TestNoteBodyMenu:
    @pytest.fixture(autouse=True)
    def _no_real_popup(self, qapp: Any) -> Iterator[None]:
        """A watchdog, never the mechanism: should any real popup open
        anyway (a menu this module did not fake), close it — a nested event
        loop still runs timers — and fail the test, instead of blocking the
        suite."""
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        closed: list[str] = []

        def close_popup() -> None:
            popup = QApplication.activePopupWidget()
            if popup is not None:
                closed.append(type(popup).__name__)
                popup.close()

        timer = QTimer()
        timer.setInterval(100)
        timer.timeout.connect(close_popup)
        timer.start()
        try:
            yield
        finally:
            timer.stop()
        assert closed == [], f"a real popup opened: {closed}"

    def test_a_context_menu_event_on_the_viewport_opens_the_menu(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Delivered to the body's VIEWPORT through Qt's dispatch, inside the
        Review screen: before Save, Copy and Select All are there but off;
        after Save (normal mode, copy on), with a selection, both are on."""
        from PySide6.QtWidgets import QApplication

        monkeypatch.setattr(models, "COPY_TO_CLINIKO_ENABLED", True)
        window = _window(tmp_path, _queued_controller())
        note = window.note_screen
        body = note.note_body
        spy = _MenuSpy(monkeypatch, body)
        _show_queued(qapp, window)
        _start_generation(qapp, window)
        _await_draft(qapp, window)
        QApplication.sendEvent(body.viewport(), _right_click_event(body))
        assert spy.opened == [[("&Copy", False), ("Select &All", False)]]
        _ratify_and_save(window, monkeypatch)
        body.selectAll()
        QApplication.sendEvent(body.viewport(), _right_click_event(body))
        assert spy.opened[-1] == [("&Copy", True), ("Select &All", True)]
        _close(window)

    def test_a_shadow_recordings_menu_refuses_copy(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from PySide6.QtWidgets import QApplication

        monkeypatch.setattr(models, "COPY_TO_CLINIKO_ENABLED", True)
        window = _window(tmp_path, _queued_controller(SessionMode.SHADOW))
        note = window.note_screen
        body = note.note_body
        spy = _MenuSpy(monkeypatch, body)
        _show_queued(qapp, window)
        _start_generation(qapp, window)
        _await_draft(qapp, window)
        _ratify_and_save(window, monkeypatch)
        body.selectAll()
        QApplication.sendEvent(body.viewport(), _right_click_event(body))
        assert spy.opened == [[("&Copy", False), ("Select &All", False)]]
        _close(window)

    @pytest.mark.parametrize("trigger", ["press", "release"])
    def test_a_right_button_click_on_the_shown_window_opens_the_menu(
        self,
        qapp: Any,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        trigger: str,
    ) -> None:
        """The whole route: a real right-button click on the shown window —
        ``QTest`` on the ``QWindow``, through Qt's platform event handling as
        the practitioner's mouse goes — at a point on the note body's
        viewport reaches the panel's context menu. Since Qt 6.8 Qt turns a
        click into a context-menu event only when the press (or, by the
        platform's ``contextMenuTrigger``, the release — Windows' setting)
        was NOT accepted on its way up the widget chain, so this runs under
        BOTH triggers. On failure the message lists every press, release and
        context-menu delivery in order.

        Leg u7x1's other route — the press and release handed to the
        ``QWindow`` with ``QApplication.sendEvent`` — was dropped in leg
        u7x4 as unfaithful: under the press trigger Qt's context-menu event
        went to the rail although the press had climbed, unaccepted, from
        the note body's viewport to the window. That happened only when the
        press skipped the platform handling a real click always takes
        (S.5's task line holds the evidence)."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication

        hints = QGuiApplication.styleHints()
        # Qt 6.8 added the trigger; the project's floor is PySide6 6.8 and the
        # build lock 6.11.1, so its absence is a failure, never a skip.
        assert hasattr(hints, "setContextMenuTrigger"), "QStyleHints.setContextMenuTrigger"
        monkeypatch.setattr(models, "COPY_TO_CLINIKO_ENABLED", True)
        window = _window(tmp_path, _queued_controller())
        note = window.note_screen
        spy = _MenuSpy(monkeypatch, note.note_body)
        _show_queued(qapp, window)
        _start_generation(qapp, window)
        _await_draft(qapp, window)
        _laid_out(qapp, window, 1200, 800)
        previous = hints.contextMenuTrigger()
        log = _EventLog(note.note_body)
        try:
            hints.setContextMenuTrigger(
                Qt.ContextMenuTrigger.Press if trigger == "press" else Qt.ContextMenuTrigger.Release
            )
            body = note.note_body
            viewport = body.viewport()
            window.review_screen.right_scroll.ensureWidgetVisible(body)
            qapp.processEvents()
            visible = viewport.visibleRegion().boundingRect()
            assert not visible.isEmpty()
            point = visible.center()
            local = viewport.mapTo(window, point)
            assert window.childAt(local) is viewport
            handle = window.windowHandle()
            assert handle is not None
            assert QTest.qWaitForWindowExposed(handle)
            QApplication.instance().installEventFilter(log)
            QTest.mouseClick(
                handle, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier, local
            )
            qapp.processEvents()
            assert spy.opened == [[("&Copy", False), ("Select &All", False)]], (
                f"trigger={trigger}: deliveries {log.seen}"
            )
        finally:
            QApplication.instance().removeEventFilter(log)
            hints.setContextMenuTrigger(previous)
            note.clear()
            _close(window)


# --- S.6: the pause cue leaves the status bar -------------------------------------------


def _recording(controller: FakeController) -> None:
    controller.session_value = RecordingSession(consent=unlinked_consent()).with_state(
        SessionState.RECORDING
    )
    controller.state_value = SessionState.RECORDING


class TestPauseCueClears:
    def _hotkey_paused(self, tmp_path: Path) -> tuple[Any, FakeController, str]:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        _recording(controller)
        window.session_screen.refresh()
        window.on_hotkey()
        cue = models.pause_cue_text("hotkey", linked=False)
        assert controller.state_value is SessionState.PAUSED
        assert window.statusBar().currentMessage() == cue
        return window, controller, cue

    def test_the_resume_button_clears_the_hotkey_cue(self, qapp: Any, tmp_path: Path) -> None:
        window, controller, _cue = self._hotkey_paused(tmp_path)
        window.session_screen.resume_button.click()
        assert ("resume",) in controller.calls
        assert window.statusBar().currentMessage() == ""
        _close(window)

    def test_chromes_resume_clears_the_hotkey_cue(self, qapp: Any, tmp_path: Path) -> None:
        """Chrome's Resume reaches the same guarded slot (the bridge's
        ``resume`` command is ``SessionScreen.on_resume``), with the bridge
        attached and its own Resume checks in place."""
        window, controller, _cue = self._hotkey_paused(tmp_path)
        bridge = window.attach_chrome_link()
        assert window.session_screen.on_resume() is True
        assert ("resume",) in controller.calls
        assert window.statusBar().currentMessage() == ""
        bridge.deleteLater()
        _close(window)

    def test_finish_clears_the_hotkey_cue(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Finish's own path, to the transcription it starts — replaced by the
        screen's refresh, which is what that start does first (no worker)."""
        window, controller, _cue = self._hotkey_paused(tmp_path)
        screen = window.session_screen
        monkeypatch.setattr(screen, "_begin_transcription", screen.refresh)
        screen.finish_button.click()
        assert ("finish",) in controller.calls
        assert controller.state_value is SessionState.PROCESSING
        assert window.statusBar().currentMessage() == ""
        _close(window)

    def test_the_hotkey_resume_keeps_its_own_line(self, qapp: Any, tmp_path: Path) -> None:
        window, _controller, _cue = self._hotkey_paused(tmp_path)
        window.on_hotkey()
        assert window.statusBar().currentMessage() == models.HOTKEY_RESUMED_STATUS
        _close(window)

    def test_a_line_shown_after_the_cue_stays(self, qapp: Any, tmp_path: Path) -> None:
        """Only the cue is cleared: a later line (an expiry warning here) is
        left as it is when the recording resumes."""
        window, _controller, _cue = self._hotkey_paused(tmp_path)
        later = "Synthetic status line shown after the pause."
        window.statusBar().showMessage(later)
        window.session_screen.on_resume()
        assert window.statusBar().currentMessage() == later
        _close(window)

    def test_a_system_pause_cue_clears_on_resume_too(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        window = _main_window(tmp_path, controller)
        _recording(controller)
        window.session_screen.refresh()
        window.pause_for(PauseReason.SUSPEND)
        assert window.statusBar().currentMessage() == models.pause_cue_text(
            "suspend", linked=False
        )
        window.session_screen.on_resume()
        assert window.statusBar().currentMessage() == ""
        _close(window)


# --- S.7: the taskbar identity, declared before any window ------------------------------


class _Proceeded(Exception):
    pass


@pytest.mark.parametrize("which", ["production", "dev"])
def test_main_declares_the_channels_taskbar_identity_before_the_application(
    which: Channel,
    qapp: Any,
    monkeypatch: pytest.MonkeyPatch,
    taskbar_ids: list[str],
) -> None:
    """Once, with the channel's id, before ``QApplication`` is constructed —
    so before any window, the two refusal boxes included. The conftest's
    seam records it (no test reaches the Windows API)."""
    import logging

    from PySide6.QtWidgets import QApplication

    from scribe_desktop import app as app_module
    from scribe_desktop.ui import theme

    use_channel(monkeypatch, which)
    order: list[str] = []

    def application(argv: object) -> Any:
        order.append(f"application after {list(taskbar_ids)}")
        return QApplication.instance() or QApplication([])

    def guard(name: object = None, lock_path: object = None) -> Any:
        order.append("guard")
        return app_module.InstanceExclusion("acquired")

    def proceeded(**kwargs: object) -> Any:
        raise _Proceeded

    monkeypatch.setattr(
        app_module, "setup_logging", lambda name: logging.getLogger("test-taskbar-order")
    )
    monkeypatch.setattr(app_module, "install_exception_hooks", lambda logger: lambda: None)
    monkeypatch.setattr(app_module, "apply_offline_env", lambda: None)
    monkeypatch.setattr(app_module, "assert_offline_env", lambda: None)
    monkeypatch.setattr(app_module, "QApplication", application)
    monkeypatch.setattr(app_module, "acquire_instance_exclusion", guard)
    monkeypatch.setattr(app_module, "ImportWarmup", proceeded)
    # The real theme is already on the shared application; never re-applied.
    monkeypatch.setattr(theme, "ensure_applied", lambda app: None)
    with pytest.raises(_Proceeded):
        app_module.main(["scribe-app"])
    expected = identity.app_user_model_id(which)
    assert taskbar_ids == [expected]
    assert order == [f"application after {[expected]}", "guard"]


def test_a_refused_taskbar_identity_never_stops_the_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scribe_desktop import taskbar

    def refuse(app_id: str) -> None:
        raise OSError("refused")

    monkeypatch.setattr(taskbar, "set_process_app_id", refuse)
    assert taskbar.declare_taskbar_identity(identity.APP_USER_MODEL_ID) is False


def test_the_conftest_seam_records_instead_of_calling_windows(taskbar_ids: list[str]) -> None:
    from scribe_desktop import taskbar

    assert taskbar.set_process_app_id is not taskbar._win32_set_process_app_id  # noqa: SLF001
    assert taskbar.declare_taskbar_identity("Synthetic.Id") is True
    assert taskbar_ids == ["Synthetic.Id"]


def test_the_real_call_below_the_seam_fails_closed_in_tests(
    monkeypatch: pytest.MonkeyPatch, taskbar_guard: TaskbarGuard
) -> None:
    """Codex round 34 PR-MED-001: every route to the real implementation —
    a direct call, or the seam pointed back at it (as an alias taken at
    import would be) — reaches the conftest's guard, never Windows. Through
    ``declare_taskbar_identity`` the error is swallowed by design, so the
    guard's record is what fails such a test at teardown; this test reads
    the record and clears it, so it does not fail itself."""
    from scribe_desktop import taskbar

    with pytest.raises(AssertionError, match="real taskbar identity call"):
        taskbar._win32_set_process_app_id("Synthetic.Direct")  # noqa: SLF001
    monkeypatch.setattr(taskbar, "set_process_app_id", taskbar._win32_set_process_app_id)  # noqa: SLF001
    assert taskbar.declare_taskbar_identity("Synthetic.Alias") is False
    assert taskbar_guard.reached == ["shell32", "shell32"]
    taskbar_guard.reached.clear()
