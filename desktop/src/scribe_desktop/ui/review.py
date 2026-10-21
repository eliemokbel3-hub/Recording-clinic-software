"""The Review screen (UI refresh plan D6, D14; Phase 2): one page in place of
the Transcript and Note tabs — the transcript on the left, the note on the
right, one button row and one status strip under both. The design system
records it under "Review screen" (`docs/design-system.md`, written by the
plan's Task 5.1).

A LITE COMPOSITION of the two existing screens. Both engines are kept whole —
every widget keeps its object, owner, signals and enablement logic, and the
main window and the tests still read ``transcript_screen.<attr>`` and
``note_screen.<attr>``:

- LEFT: the ``TranscriptScreen`` whole — once its "Generate note" group, its
  Complete and Discard buttons and its message line are taken out, what is left
  is the warning, the live header, the display-only transcript, the legend and
  the attribution, link and shadow lines, top to bottom.
- RIGHT: the transcript engine's ``generate_box`` (its first row is the
  next-patient line and "Remove lines N-end from this recording...", which
  travel with it), over the ``NoteScreen`` whole with its own duplicate
  transcript pane hidden — its review side lifted, whole, out of the engine's
  own splitter into the engine's own layout (Task S.10) — over its "Edit the
  note" group.
- Then ONE row — Save note, Write draft to Cliniko, Copy note, then Complete and
  Discard on the right — and the status strip: the transcript engine's message
  line, the note engine's message line, the write line and the note's shadow
  line. "Cancel review and regenerate" and "Delete note and complete without
  one" stay in the note engine's own row (decision 0.2, option (a) as built,
  open for the practitioner at the Phase 2 smoke).

Adoption is ``layout.addWidget`` only, once, here, before the window is shown
(C15): Qt detaches the widget from its old layout recursively and reparents it,
so nothing calls ``removeWidget`` or ``setParent(None)`` and nothing is adopted
again at run time. The note engine's review side is never split. This module
constructs no text widget, list, combo box, clipboard or drag call and makes no
``QApplication`` call (C1, C2, C9): beside the engines' widgets it builds only
the folded Generate row (a label and a button), its holder and the column's
scroll area.
Visibility stays the engines' own (D14): ``generate_box`` shows and hides by
``TranscriptScreen``'s rule. Two things here hide: the note engine's duplicate
transcript pane (with the engine's splitter it is left alone in, Task S.10),
and — UI refresh Task S.2, the practitioner's choice of
2026-10-20 — the holder ``generate_box`` sits in, while a note is under review
or saved: the group folds to ONE row naming the chosen clinician's speaker
label and the template profile's name (never the radio's quoted transcript
sentence), with "Change" to show the group again. A cleared review (Cancel
review and regenerate, Complete, Discard, a new recording) shows it again.
Folding changes nothing the group does. The right column scrolls, and the
note body keeps about twelve lines, so a note with many review warnings never
squeezes the note or a warning row's Acknowledge button. Task S.9: the column
asks the splitter for the width its content needs, so it scrolls DOWN only
wherever the window can give both sides their minimum.
"""

from __future__ import annotations

from itertools import pairwise
from typing import Final

from PySide6.QtCore import QEvent, QObject, QSize, Qt
from PySide6.QtWidgets import (
    QBoxLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop.ui import models
from scribe_desktop.ui.note import NoteScreen
from scribe_desktop.ui.theme import mark_card
from scribe_desktop.ui.transcript import TranscriptScreen

# Task S.2: the note body never shows fewer lines than this.
NOTE_BODY_MIN_LINES: Final = 12


def _adopt(widget: QWidget, layout: QBoxLayout, stretch: int = 0) -> None:
    """Move ``widget`` into ``layout``. ``addWidget`` detaches it from its old
    layout recursively (a nested row included) and reparents it to the
    layout's widget; ``QLayout.removeWidget`` would be a silent no-op for a
    widget in a nested row, so it is never used (C15)."""
    layout.addWidget(widget, stretch)


class _ColumnScroll(QScrollArea):
    """Task S.9 (F8): the right column's scroll area. A plain ``QScrollArea``
    asks for almost no width, so at 150 % the splitter gave the column less
    than its content's minimum and the content ran past the pane (the consent
    paragraph and the Template profile box cut at the right edge). This one
    asks for its content's minimum width, its frame and a vertical scroll
    bar's width — so, given that, the content fits across whether or not the
    column scrolls down — and re-asks the splitter whenever the content lays itself
    out again (the clinician radios filled in, the Generate group folded or
    unfolded). Its height asks for nothing more: the column still scrolls
    down (Task S.2)."""

    def __init__(self, content: QWidget) -> None:
        super().__init__()
        self.setWidgetResizable(True)
        # ``setWidget`` installs this area as the content's event filter.
        self.setWidget(content)

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        content = self.widget()
        if content is None:
            return hint
        width = (
            max(content.minimumSizeHint().width(), content.minimumWidth())
            + 2 * self.frameWidth()
            + self.verticalScrollBar().sizeHint().width()
        )
        return QSize(max(hint.width(), width), hint.height())

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.widget() and event.type() == QEvent.Type.LayoutRequest:
            self.updateGeometry()
        return super().eventFilter(watched, event)


class ReviewScreen(QWidget):
    """The Review page: the two engines side by side, one button row, one
    status strip (D6). Construct it once, in ``MainWindow.__init__``, before
    the window is shown."""

    def __init__(
        self,
        transcript_screen: TranscriptScreen,
        note_screen: NoteScreen,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.transcript_screen = transcript_screen
        self.note_screen = note_screen
        # The engines sit inside this page now; their own outer margins would
        # double the page's.
        for engine in (transcript_screen, note_screen):
            engine_layout = engine.layout()
            if engine_layout is not None:
                engine_layout.setContentsMargins(0, 0, 0, 0)

        # RIGHT: Generate over the note over "Edit the note". The pane's layout
        # is built parented, so every adoption reparents into the pane.
        self.right_pane = QWidget()
        right_layout = QVBoxLayout(self.right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)
        # Task S.2: the Generate group sits in a holder this screen folds;
        # the group's own visibility stays the transcript engine's.
        self.generate_holder = QWidget()
        holder_layout = QVBoxLayout(self.generate_holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        _adopt(transcript_screen.generate_box, holder_layout)
        right_layout.addWidget(self.generate_holder)
        # ...and its folded form: one row, shown in its place.
        self.generate_summary = QFrame()
        mark_card(self.generate_summary)
        summary_layout = QHBoxLayout(self.generate_summary)
        self.generate_summary_label = QLabel()
        self.generate_summary_label.setTextFormat(Qt.TextFormat.PlainText)
        self.generate_summary_label.setWordWrap(True)
        self.change_generate_button = QPushButton(models.GENERATE_CHANGE_LABEL)
        self.change_generate_button.setToolTip(models.GENERATE_CHANGE_TOOLTIP)
        self.change_generate_button.clicked.connect(self.unfold_generate)
        summary_layout.addWidget(self.generate_summary_label, 1)
        summary_layout.addWidget(self.change_generate_button)
        right_layout.addWidget(self.generate_summary)
        # The note engine's own transcript pane duplicates the left pane here:
        # hidden, so its review side fills the engine (its widgets and flags
        # are unchanged — full removal is 0.4.1's Task 6.4).
        note_screen.transcript_pane.hide()
        # Task S.10 (F9): the engine's review side leaves the engine's own
        # splitter — which then holds only that hidden pane, so it hides too
        # — for the engine's own layout, whole. A splitter passes no
        # height-for-width through, and the scrolling column takes its height
        # from it (S.2), so a warning row whose wrapped text needed more lines
        # at the column's width than its preferred size was cut. Same widget,
        # same owner, same place on screen.
        panes = note_screen.review_side.parentWidget()
        engine_layout = note_screen.layout()
        assert isinstance(engine_layout, QBoxLayout)
        _adopt(note_screen.review_side, engine_layout, 1)
        if isinstance(panes, QSplitter):
            panes.hide()
        # Task S.2: the note takes the column's spare height; "Edit the note"
        # keeps its own.
        _adopt(note_screen, right_layout, 1)
        _adopt(note_screen.edit_group, right_layout)
        self._hold_note_body_height()
        # Task S.2: the column scrolls down rather than squeeze anything in
        # it; Task S.9: never sideways.
        self.right_scroll = _ColumnScroll(self.right_pane)

        # LEFT: the transcript engine whole.
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(transcript_screen)
        self.splitter.addWidget(self.right_scroll)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)

        # The one button row: the note's actions, then the custody actions on
        # the right.
        self.button_row = QHBoxLayout()
        row_buttons = (
            note_screen.save_button,
            note_screen.write_button,
            note_screen.copy_button,
            transcript_screen.complete_button,
            transcript_screen.discard_button,
        )
        for button in row_buttons[:3]:
            _adopt(button, self.button_row)
        self.button_row.addStretch(1)
        for button in row_buttons[3:]:
            _adopt(button, self.button_row)

        # The status strip: custody and generation lines, then the note's.
        # Every line keeps its own text and its own setText callers.
        self.status_strip = QWidget()
        strip_layout = QVBoxLayout(self.status_strip)
        strip_layout.setContentsMargins(0, 0, 0, 0)
        for label in (
            transcript_screen.message_label,
            note_screen.message_label,
            note_screen.write_label,
            note_screen.shadow_label,
        ):
            _adopt(label, strip_layout)

        outer = QVBoxLayout(self)
        outer.addWidget(self.splitter, 1)
        outer.addLayout(self.button_row)
        outer.addWidget(self.status_strip)

        # Keyboard order follows the row, left to right.
        for first, second in pairwise(row_buttons):
            QWidget.setTabOrder(first, second)

        # Task S.2: the fold follows the note engine (a note shown, or
        # cleared) and the transcript engine's close (Complete, Discard).
        self._unfolded = False
        note_screen.review_changed.connect(self._sync_generate_fold)
        transcript_screen.closed.connect(self._sync_generate_fold)
        self._sync_generate_fold()

    def _hold_note_body_height(self) -> None:
        """Task S.2: the note body keeps about ``NOTE_BODY_MIN_LINES`` lines of
        its own font — a layout minimum, not a theme value."""
        body = self.note_screen.note_body
        body.ensurePolished()
        margins = body.contentsMargins()
        frame = (
            2 * body.frameWidth()
            + 2 * int(body.document().documentMargin())
            + margins.top()
            + margins.bottom()
        )
        body.setMinimumHeight(body.fontMetrics().lineSpacing() * NOTE_BODY_MIN_LINES + frame)

    @property
    def generate_folded(self) -> bool:
        """True while the Generate note group is folded to its one row."""
        return not self.generate_summary.isHidden()

    def unfold_generate(self) -> None:
        """The "Change" button: show the Generate note group again, as it is,
        until the note leaves the screen (a new note folds it once more)."""
        self._unfolded = True
        self._sync_generate_fold()

    def _sync_generate_fold(self, *_args: object) -> None:
        """Fold the group while a note is under review or saved and the
        transcript engine offers generation; otherwise show it. A cleared
        review forgets "Change"."""
        note = self.note_screen
        shown = note.current_note() is not None or note.showing_saved_note
        if not shown:
            self._unfolded = False
        folded = (
            shown
            and not self._unfolded
            and not self.transcript_screen.generate_box.isHidden()
        )
        if folded:
            role, profile = self.transcript_screen.generation_choice()
            self.generate_summary_label.setText(models.generate_summary_text(role, profile))
        self.generate_holder.setVisible(not folded)
        self.generate_summary.setVisible(folded)
