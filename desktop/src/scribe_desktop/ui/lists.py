"""The app's one list widget and one combo box (pilot review rounds 23–24).

Qt's item views copy the current row's text on the Copy shortcut (Ctrl+C,
Ctrl+Insert) with a plain clipboard write — none of the formats that keep
text out of Windows clipboard history and cloud sync (Task 8.2), and no
ratification or shadow check. The app's lists show a patient's name (Past
sessions, the recovery and Unreviewed lists), the practitioner's learned
phrases and rules, and sentences from their sample notes, and a combo box's
popup is such a view too (the Note tab's "Line:" choice shows each
transcript line's first words). So no list or popup may copy: every list in
the app is a ``NoCopyListWidget`` and every combo box a ``NoCopyComboBox``
(``test_shadow_exits.py`` pins that no other is constructed).
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QComboBox, QListWidget, QWidget


def _is_copy(event: QEvent) -> bool:
    return (
        event.type() == QEvent.Type.KeyPress
        and isinstance(event, QKeyEvent)
        and event.matches(QKeySequence.StandardKey.Copy)
    )


class NoCopyListWidget(QListWidget):
    """A ``QListWidget`` whose Copy shortcut does nothing. Every other key
    (moving, selecting, Delete where a tab wires it) is Qt's own."""

    def keyPressEvent(self, event: QKeyEvent, /) -> None:
        if event.matches(QKeySequence.StandardKey.Copy):
            event.accept()  # Qt's own row copy never runs
            return
        super().keyPressEvent(event)


class _DropCopy(QObject):
    """An event filter that swallows the Copy shortcut on the view it is
    installed on (the combo box's popup, whose class is Qt's private one)."""

    def eventFilter(self, watched: QObject, event: QEvent, /) -> bool:
        if _is_copy(event):
            event.accept()
            return True
        return False


class NoCopyComboBox(QComboBox):
    """A ``QComboBox`` whose popup's Copy shortcut does nothing. Its own
    view is kept (Qt's styling) and a filter, installed after the combo
    box's own, drops Copy before the view sees it. Nothing here replaces
    the view, so the filter stays with it."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._drop_copy = _DropCopy(self)
        self.view().installEventFilter(self._drop_copy)
