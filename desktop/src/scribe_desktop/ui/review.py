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
  transcript pane hidden, over its "Edit the note" group.
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
``QApplication`` call (C1, C2, C9): it only arranges widgets the engines built.
Visibility stays the engines' own (D14): ``generate_box`` shows and hides by
``TranscriptScreen``'s rule, and nothing here hides a widget but the note
engine's duplicate transcript pane.
"""

from __future__ import annotations

from itertools import pairwise

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QBoxLayout,
    QHBoxLayout,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop.ui.note import NoteScreen
from scribe_desktop.ui.transcript import TranscriptScreen


def _adopt(widget: QWidget, layout: QBoxLayout, stretch: int = 0) -> None:
    """Move ``widget`` into ``layout``. ``addWidget`` detaches it from its old
    layout recursively (a nested row included) and reparents it to the
    layout's widget; ``QLayout.removeWidget`` would be a silent no-op for a
    widget in a nested row, so it is never used (C15)."""
    layout.addWidget(widget, stretch)


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
        _adopt(transcript_screen.generate_box, right_layout)
        # The note engine's own transcript pane duplicates the left pane here:
        # hidden, so its review side fills the engine (its widgets and flags
        # are unchanged — full removal is 0.4.1's Task 6.4).
        note_screen.transcript_pane.hide()
        _adopt(note_screen, right_layout, 1)
        _adopt(note_screen.edit_group, right_layout, 1)

        # LEFT: the transcript engine whole.
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(transcript_screen)
        self.splitter.addWidget(self.right_pane)
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
