"""Session controls screen: start/pause/resume/finish/discard with
state-driven enablement; Finish drives transcription with progress
indication (plan Step 10, Flows 1-2)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import SessionState
from scribe_desktop.transcription import TranscriptDocument
from scribe_desktop.ui import models
from scribe_desktop.ui.tasks import TaskThread


class SessionScreen(QWidget):
    # Emitted with the TranscriptDocument once a live session reaches
    # queued (the main window routes it to the inspection view).
    transcript_ready = Signal(object)

    def __init__(
        self,
        controller: models.SessionControllerLike,
        *,
        device_provider: Callable[[], int | None],
        transcriber_factory: Callable[
            [], Callable[[Path, SessionCrypto], TranscriptDocument]
        ] = models.build_transcriber,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._device_provider = device_provider
        self._transcriber_factory = transcriber_factory
        self._task: TaskThread | None = None
        self._transcribing = False
        self._last_state = controller.state

        self.state_label = QLabel()
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)

        self.start_button = QPushButton("Start")
        self.pause_button = QPushButton("Pause")
        self.resume_button = QPushButton("Resume")
        self.finish_button = QPushButton("Finish")
        self.discard_button = QPushButton("Discard")
        self.start_button.clicked.connect(self.on_start)
        self.pause_button.clicked.connect(self.on_pause)
        self.resume_button.clicked.connect(self.on_resume)
        self.finish_button.clicked.connect(self.on_finish)
        self.discard_button.clicked.connect(self.on_discard)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.hide()
        self.progress_label = QLabel()
        self.progress_label.hide()

        buttons = QHBoxLayout()
        for button in (
            self.start_button,
            self.pause_button,
            self.resume_button,
            self.finish_button,
            self.discard_button,
        ):
            buttons.addWidget(button)

        layout = QVBoxLayout()
        layout.addWidget(self.state_label)
        layout.addLayout(buttons)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.message_label)
        layout.addStretch(1)
        self.setLayout(layout)
        self.refresh()

        # PR round 18 (PR3->MED): capture failure flips the controller to
        # failed from the worker thread with no UI notification path — poll
        # so the screen never claims "recording" after capture died.
        self._state_timer = QTimer(self)
        self._state_timer.setInterval(500)
        self._state_timer.timeout.connect(self._watch_state)
        self._state_timer.start()

    # --- enablement -----------------------------------------------------------

    @property
    def is_busy(self) -> bool:
        """True while a transcription run is in flight (close must wait)."""
        return self._transcribing

    def _watch_state(self) -> None:
        state = self._controller.state
        if state == self._last_state:
            return
        previous = self._last_state
        if state == SessionState.FAILED and previous in (
            SessionState.RECORDING,
            SessionState.PAUSED,
        ):
            self._show_message(
                "Recording failed (device lost or disk full). The audio "
                "captured so far is kept and recoverable; you can also "
                "discard it."
            )
        self.refresh()

    def refresh(self) -> None:
        state = self._controller.state
        self._last_state = state
        self.state_label.setText(f"Session state: {state.value}")
        controls = models.controls_for_state(state)
        busy = self._transcribing
        self.start_button.setEnabled(controls.start and not busy)
        self.pause_button.setEnabled(controls.pause and not busy)
        self.resume_button.setEnabled(controls.resume and not busy)
        self.finish_button.setEnabled(controls.finish and not busy)
        self.discard_button.setEnabled(controls.discard and not busy)

    def _show_message(self, text: str) -> None:
        self.message_label.setText(text)

    # --- controls ---------------------------------------------------------------

    def on_start(self) -> None:
        device_id = self._device_provider()
        if device_id is None:
            self._show_message("Select an input device on the Microphone screen first.")
            return
        try:
            self._controller.start(device_id)
            self._show_message("Recording.")
        except Exception as exc:  # noqa: BLE001 - surfaced, never crashes the UI
            self._show_message(f"Start failed: {type(exc).__name__}: {exc}")
        self.refresh()

    def on_pause(self) -> None:
        try:
            self._controller.pause()
            self._show_message("Paused.")
        except Exception as exc:  # noqa: BLE001
            self._show_message(f"Pause failed: {type(exc).__name__}: {exc}")
        self.refresh()

    def on_resume(self) -> None:
        try:
            self._controller.resume()
            self._show_message("Recording.")
        except Exception as exc:  # noqa: BLE001
            self._show_message(f"Resume failed: {type(exc).__name__}: {exc}")
        self.refresh()

    def on_finish(self) -> None:
        try:
            session = self._controller.finish()
        except Exception as exc:  # noqa: BLE001
            self._show_message(f"Finish failed: {type(exc).__name__}: {exc}")
            self.refresh()
            return
        if session.state != SessionState.PROCESSING:
            # Disk failure during the final flush: failed but RECOVERABLE.
            self._show_message(
                "Recording could not be sealed; the session is recoverable "
                "from the Recovery screen after an app restart, or can be discarded."
            )
            self.refresh()
            return
        self._begin_transcription()

    def on_discard(self) -> None:
        try:
            self._controller.discard()
            self._show_message("Session discarded (audio cryptographically deleted).")
        except Exception as exc:  # noqa: BLE001
            self._show_message(f"Discard failed: {type(exc).__name__}: {exc}")
        self.refresh()

    # --- transcription (Finish -> processing -> queued) -------------------------

    def _begin_transcription(self) -> None:
        if self._task is not None and self._task.isRunning():
            return
        self._transcribing = True
        self.progress_label.setText("Transcribing locally... this can take a while.")
        self.progress_label.show()
        self.progress_bar.show()
        self._show_message("")
        raw = self._transcriber_factory()
        holder: list[TranscriptDocument] = []

        def wrapped(session_dir: Path, crypto: SessionCrypto) -> TranscriptDocument:
            document = raw(session_dir, crypto)
            holder.append(document)
            return document

        def job() -> TranscriptDocument:
            self._controller.transcribe(wrapped)
            # PR round 18 (PR7): pop, don't index — the closure must not
            # retain a plaintext transcript reference after the run ends.
            return holder.pop()

        task = TaskThread(job, self)
        task.succeeded.connect(self._on_transcribed)
        task.failed.connect(self._on_transcription_failed)
        self._task = task
        self.refresh()
        task.start()

    def _end_transcription(self) -> None:
        self._transcribing = False
        # PR round 18 (PR6/PR7): join the finished worker, then drop the
        # closure chain so no plaintext transcript reference is retained.
        if self._task is not None:
            self._task.wait(2000)
            self._task = None
        self.progress_bar.hide()
        self.progress_label.hide()

    def _on_transcribed(self, document: object) -> None:
        self._end_transcription()
        self._show_message("Transcription complete - review the transcript.")
        self.refresh()
        assert isinstance(document, TranscriptDocument)
        self.transcript_ready.emit(document)

    def _on_transcription_failed(self, message: str) -> None:
        self._end_transcription()
        # The controller routed the session to failed (RECOVERABLE):
        # key + audio retained; Flow 3 offers resume-processing or discard.
        self._show_message(
            f"Transcription failed ({message}). The recording is kept and "
            "recoverable: resume processing from the Recovery screen after "
            "an app restart, or discard it below."
        )
        self.refresh()
