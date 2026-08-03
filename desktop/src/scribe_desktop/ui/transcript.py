"""Transcript-inspection view: decrypted transcript display (uncertainty
marks + speaker labels visible) with the explicit Phase-2 Complete and
Discard actions (plan Flow 2 custody ordering).

The transcript is DISPLAYED only. It is never written to disk, logged,
or copied anywhere by this widget; the display is cleared as soon as the
session is completed or discarded.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop.transcription import TranscriptDocument
from scribe_desktop.ui import models


class TranscriptScreen(QWidget):
    # Emitted after a successful Complete ("completed") or Discard ("discarded").
    closed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_complete: Callable[[], object] | None = None
        self._on_discard: Callable[[], object] | None = None

        self.warning_label = QLabel()
        self.warning_label.setStyleSheet("color: #b00020; font-weight: bold;")
        self.warning_label.setWordWrap(True)
        self.warning_label.hide()

        self.transcript_view = QPlainTextEdit()
        self.transcript_view.setReadOnly(True)
        self.transcript_view.setPlaceholderText("No transcript loaded.")
        # PR round 18 (PR5->MED, defense-in-depth at the same-user boundary):
        # no selection/copy — Windows clipboard history / cloud clipboard
        # sync must never receive transcript text from this view.
        self.transcript_view.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )

        self.legend_label = QLabel("Uncertain words are shown as [word?] - verify them.")

        self.complete_button = QPushButton("Complete")
        self.complete_button.setToolTip(
            "Verify the encrypted transcript, then cryptographically delete "
            "the session (audio becomes unrecoverable)."
        )
        self.discard_button = QPushButton("Discard")
        self.complete_button.clicked.connect(self.on_complete)
        self.discard_button.clicked.connect(self.on_discard)

        self.message_label = QLabel()
        self.message_label.setWordWrap(True)

        buttons = QHBoxLayout()
        buttons.addWidget(self.complete_button)
        buttons.addWidget(self.discard_button)
        buttons.addStretch(1)

        layout = QVBoxLayout()
        layout.addWidget(self.warning_label)
        layout.addWidget(self.transcript_view)
        layout.addWidget(self.legend_label)
        layout.addLayout(buttons)
        layout.addWidget(self.message_label)
        self.setLayout(layout)
        self._update_controls()

    # --- loading -----------------------------------------------------------

    def show_document(
        self,
        document: TranscriptDocument,
        *,
        on_complete: Callable[[], object],
        on_discard: Callable[[], object],
        store_finished: bool = True,
    ) -> None:
        """Display a decrypted transcript with its custody callbacks.

        ``on_complete`` must implement the binding Flow 2 ordering
        (fsync -> verify decrypt round-trip -> delete key custody);
        ``on_discard`` deletes the key FIRST. Both are supplied by the
        caller so live (controller) and recovered (custody-primitive)
        sessions share this one view.
        """
        self._on_complete = on_complete
        self._on_discard = on_discard
        self.transcript_view.setPlainText(models.format_transcript_text(document))
        self.message_label.setText("")
        if store_finished:
            self.warning_label.hide()
        else:
            # Binding Step-10 note (PR-HIGH-007 residual).
            self.warning_label.setText(models.UNFINISHED_STORE_WARNING)
            self.warning_label.show()
        self._update_controls()

    def _update_controls(self) -> None:
        loaded = self._on_complete is not None
        self.complete_button.setEnabled(loaded)
        self.discard_button.setEnabled(loaded)

    def _clear(self) -> None:
        self._on_complete = None
        self._on_discard = None
        self.transcript_view.setPlainText("")
        self.warning_label.hide()
        self._update_controls()

    # --- actions -----------------------------------------------------------

    def on_complete(self) -> None:
        if self._on_complete is None:
            return
        try:
            self._on_complete()
        except Exception as exc:  # noqa: BLE001 - key custody kept on any failure
            # Round 42 LOW-001: state only what THIS action verified — the
            # Complete primitive deleted nothing on failure, but the key may
            # be gone for another reason (e.g. the 24 h sweep at expiry).
            self.message_label.setText(
                f"Complete failed: {type(exc).__name__}: {exc}. "
                "No key deletion was performed by this action; if the "
                "session is still within its 24-hour window it remains "
                "available."
            )
            return
        self._clear()
        self.message_label.setText(
            "Session completed: transcript verified and the session key "
            "destroyed (cryptographic deletion)."
        )
        self.closed.emit("completed")

    def on_discard(self) -> None:
        if self._on_discard is None:
            return
        try:
            self._on_discard()
        except Exception as exc:  # noqa: BLE001
            self.message_label.setText(f"Discard failed: {type(exc).__name__}: {exc}")
            return
        self._clear()
        self.message_label.setText("Session discarded (audio cryptographically deleted).")
        self.closed.emit("discarded")
