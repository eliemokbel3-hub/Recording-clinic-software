"""The Past-sessions backup's two dialogs (past-sessions-backup plan Task 2.2;
D3, D4, D10; C3).

- The passphrase dialog: two ``Password`` fields for Back up (entered twice,
  at least ``PASSPHRASE_MINIMUM`` characters, no composition rules), one for
  Open a backup. The decision is the Qt-free ``passphrase_decision``.
- The summary dialog of Open a backup: authored lines (counts and dates only,
  no verdict — decision 0.14), with Close (the default: nothing is written)
  and Restore. Parented to the main window, never to a page, so it stays
  usable while the run gate disables every page (D11).

What the passphrase fields never do (C3): their own signals are blocked from
construction — ``textChanged`` and ``textEdited`` would carry the text to any
connected slot — and the accepted value is read synchronously, handed over as
a ``bytearray`` the caller's run object zeroes, and the fields are cleared on
accept, reject and close. Copy and Cut, by shortcut and by context menu, place
nothing: the shortcuts are swallowed before Qt sees them and the field has no
context menu (asserted with guards before native Qt, not assumed from the
echo mode); drag stays off, Qt's default for a line edit. Named residue: Qt's
own widget text and the pagefile may hold the passphrase while it is typed
(the threat model, as for every secret in memory).

These are the only text inputs of the backup flows (``test_shadow_exits.py``
pins text widgets in the Review and Past-sessions engines only). No selectable
text, list, item view or combo box; every visual value comes from
``ui/theme.py``."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QContextMenuEvent, QKeyEvent, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop.ui.theme import set_role

# D3 (decision 0.3): a chosen passphrase, at least 20 characters.
PASSPHRASE_MINIMUM: Final = 20

BACKUP_PASSPHRASE_TITLE: Final = "Back up past sessions"
OPEN_PASSPHRASE_TITLE: Final = "Open a backup"
BACKUP_PASSPHRASE_INTRO: Final = (
    f"Choose a passphrase of at least {PASSPHRASE_MINIMUM} characters and enter it twice. "
    "The passphrase is never stored. Without it the backup cannot be opened by anyone, "
    "including you."
)
OPEN_PASSPHRASE_INTRO: Final = "Enter the passphrase this backup was made with."
PASSPHRASE_LABEL: Final = "Passphrase"
PASSPHRASE_AGAIN_LABEL: Final = "Passphrase again"
BACKUP_CONTINUE: Final = "Continue"
OPEN_CONTINUE: Final = "Open"
PASSPHRASE_CANCEL: Final = "Cancel"
PASSPHRASE_EMPTY: Final = "Enter the passphrase."
PASSPHRASE_MISMATCH: Final = "The two passphrases are not the same - enter them again."

SUMMARY_TITLE: Final = "Open a backup"
SUMMARY_CLOSE: Final = "Close"
SUMMARY_RESTORE: Final = "Restore"


def passphrase_too_short(minimum: int) -> str:
    return f"The passphrase must be at least {minimum} characters - enter it again."


def passphrase_decision(first: str, second: str | None, *, minimum: int) -> str | None:
    """Why the passphrase cannot be used (a line), or None when it can: empty,
    shorter than ``minimum`` characters, or — when ``second`` is given (Back
    up enters it twice) — not the same as ``second``. No composition rules
    (D3). Never echoes either value."""
    if not first:
        return PASSPHRASE_EMPTY
    if len(first) < minimum:
        return passphrase_too_short(minimum)
    if second is not None and first != second:
        return PASSPHRASE_MISMATCH
    return None


def _plain_label(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    return label


class PassphraseField(QLineEdit):
    """A ``Password`` field whose own signals are blocked from construction,
    with no context menu, no drag (the default) and Copy and Cut swallowed by
    shortcut."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.blockSignals(True)
        self.setEchoMode(QLineEdit.EchoMode.Password)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        # Drag stays at QLineEdit's default (off): no setDragEnabled call, so
        # ``test_shadow_exits.py``'s one-call pin holds (``dragEnabled()`` is
        # asserted False in the tests).
        self.setAcceptDrops(False)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt's name
        if event.matches(QKeySequence.StandardKey.Copy) or event.matches(
            QKeySequence.StandardKey.Cut
        ):
            event.accept()  # nothing is placed anywhere
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # noqa: N802 - Qt's name
        event.accept()  # no menu, so no menu Copy or Cut

    def wipe(self) -> None:
        """Clear the text (its signals stay blocked, so nothing carries it)."""
        self.blockSignals(True)
        self.clear()


class PassphraseDialog(QDialog):
    """The passphrase prompt (D3, D10): twice for Back up (``confirm``), once
    for Open a backup. ``take_passphrase`` hands the accepted value over
    ONCE, as a ``bytearray``; the fields are empty after every exit."""

    def __init__(self, *, confirm: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._confirm = confirm
        self._minimum = PASSPHRASE_MINIMUM if confirm else 1
        self._value: bytearray | None = None
        self.setWindowTitle(BACKUP_PASSPHRASE_TITLE if confirm else OPEN_PASSPHRASE_TITLE)
        self.setModal(True)
        self.intro_label = _plain_label(
            BACKUP_PASSPHRASE_INTRO if confirm else OPEN_PASSPHRASE_INTRO
        )
        self.first_field = PassphraseField()
        self.second_field: PassphraseField | None = PassphraseField() if confirm else None
        self.error_label = _plain_label()
        set_role(self.error_label, "error")
        self.error_label.hide()
        self.continue_button = QPushButton(BACKUP_CONTINUE if confirm else OPEN_CONTINUE)
        self.cancel_button = QPushButton(PASSPHRASE_CANCEL)
        self.continue_button.setDefault(True)
        self.continue_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.continue_button)
        buttons.addWidget(self.cancel_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.intro_label)
        layout.addWidget(_plain_label(PASSPHRASE_LABEL))
        layout.addWidget(self.first_field)
        if self.second_field is not None:
            layout.addWidget(_plain_label(PASSPHRASE_AGAIN_LABEL))
            layout.addWidget(self.second_field)
        layout.addWidget(self.error_label)
        layout.addLayout(buttons)

    def fields(self) -> tuple[PassphraseField, ...]:
        if self.second_field is None:
            return (self.first_field,)
        return (self.first_field, self.second_field)

    def _wipe(self) -> None:
        for field in self.fields():
            field.wipe()

    def accept(self) -> None:
        first = self.first_field.text()
        second = self.second_field.text() if self.second_field is not None else None
        refusal = passphrase_decision(first, second, minimum=self._minimum)
        if refusal is not None:
            self._wipe()
            self.error_label.setText(refusal)
            self.error_label.show()
            self.first_field.setFocus()
            return
        self._value = bytearray(first, "utf-8")
        self._wipe()
        super().accept()

    def reject(self) -> None:
        self._wipe()
        super().reject()

    def done(self, result: int) -> None:
        self._wipe()
        super().done(result)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt's name
        self._wipe()
        super().closeEvent(event)

    def take_passphrase(self) -> bytearray | None:
        """The accepted passphrase, ONCE (the caller's run object owns and
        zeroes it from here); None when the dialog was not accepted."""
        value, self._value = self._value, None
        return value


def ask_passphrase(parent: QWidget | None, *, confirm: bool) -> bytearray | None:
    """Show the passphrase dialog (production only; tests inject a seam):
    the passphrase as a ``bytearray``, or None when cancelled."""
    dialog = PassphraseDialog(confirm=confirm, parent=parent)
    try:
        dialog.exec()
        return dialog.take_passphrase()
    finally:
        dialog.deleteLater()


class SummaryDialog(QDialog):
    """What a backup holds and what Restore would do here (D10): authored
    lines only, Close the default button (nothing is written) and Restore —
    disabled, with its reason as one more line, when Restore cannot run."""

    def __init__(
        self,
        lines: Sequence[str],
        *,
        restore_enabled: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(SUMMARY_TITLE)
        self.setModal(True)
        self.line_labels = [_plain_label(line) for line in lines]
        self.close_button = QPushButton(SUMMARY_CLOSE)
        self.restore_button = QPushButton(SUMMARY_RESTORE)
        self.restore_button.setEnabled(restore_enabled)
        self.close_button.setDefault(True)
        self.close_button.setAutoDefault(True)
        self.restore_button.setAutoDefault(False)
        self.close_button.clicked.connect(self.reject)
        self.restore_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.restore_button)
        buttons.addWidget(self.close_button)
        layout = QVBoxLayout(self)
        for label in self.line_labels:
            layout.addWidget(label)
        layout.addLayout(buttons)


def show_summary(parent: QWidget, lines: Sequence[str], *, restore_enabled: bool) -> bool:
    """Show the summary dialog, parented to ``parent``'s window (never a
    page). True only when Restore was pressed (production only; tests inject
    a seam)."""
    dialog = SummaryDialog(lines, restore_enabled=restore_enabled, parent=parent.window())
    try:
        return dialog.exec() == QDialog.DialogCode.Accepted
    finally:
        dialog.deleteLater()
