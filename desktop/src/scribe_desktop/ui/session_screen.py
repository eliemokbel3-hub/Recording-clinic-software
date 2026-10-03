"""Session controls screen: start/pause/resume/finish/discard with
state-driven enablement; Finish drives transcription with progress
indication (plan Step 10, Flows 1-2).

Cliniko workflow safeguards plan Phase 5: Resume asks the Chrome bridge's
guard first (D5 — a linked session resumes only on a current report of its
own note), Discard from this screen takes two clicks (the resolution
block's rule, D1), Start is offered at QUEUED for the next patient unless a
note review holds the generation lease (D6), and a Start that retires a
queued session announces it (``session_retired``) so the Unreviewed
reminder index can take it."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Final

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop.encounter import ConsentAttestation, EncounterContext, unlinked_consent
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import SessionState
from scribe_desktop.transcription import TranscriptDocument
from scribe_desktop.ui import models
from scribe_desktop.ui.tasks import TaskThread

# The second Discard click must come within this long of the first, for the
# same session; otherwise the first click is asked for again.
DISCARD_CONFIRM_SECONDS: Final = 10.0
DISCARD_CONFIRM_LABEL: Final = "Confirm discard"


class SessionScreen(QWidget):
    # Emitted with the TranscriptDocument once a live session reaches
    # queued (the main window routes it to the inspection view).
    transcript_ready = Signal(object)
    # Note-learning plan C8: the live transcription outcome the transcriber
    # callable reports from the PROCESSING thread ("assembled from the live
    # transcription", or the named fallback reason). A queued signal — the
    # slot runs on the GUI thread and the text joins the completion message.
    live_status = Signal(str)
    # Note-learning plan Task 1.4: a successful Discard from THIS screen —
    # the main window clears the Transcript screen's live view on it (the
    # Transcript screen's own Discard already clears itself).
    session_discarded = Signal()
    # Round 7 LOW-003: a SUCCESSFUL Start from this screen — the main window
    # opens the Transcript screen's live view on it (never inside the worker
    # factory, which `start()` calls before the device is even opened: a
    # failed Start must not leave the live header up with no session).
    session_started = Signal()
    # Cliniko workflow safeguards plan Task 5.1: a SUCCESSFUL Resume, from any
    # source — the Chrome bridge re-binds the session's tab and drops the block.
    session_resumed = Signal()
    # Task 5.3 (D6): a successful Start RETIRED the previous tracked session
    # (the RecordingSession as it was, e.g. QUEUED) — the main window adds a
    # linked, reviewable one to the Unreviewed reminder index.
    session_retired = Signal(object)

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
        # Installation plan round 40 LOW-002: a confirmed Discard waiting off
        # the GUI thread for live transcription to stop, and the Chrome
        # bridge's hook for a refusal it ends in.
        self._discard_task: TaskThread | None = None
        self._discarding = False
        self._discard_on_refused: Callable[[], None] | None = None
        self._last_state = controller.state
        self._last_generating = controller.generating
        self._last_writing = controller.writing_session_id() is not None
        self._live_status: str | None = None
        # Task 5.1 (D5): the Chrome bridge's resume check — a refusal message,
        # or None when Resume may run. None: no bridge (Resume as before).
        self._resume_guard: Callable[[], str | None] | None = None
        # H1 round 54 MED-052: the bridge's lock check, run first by every
        # Start from this screen (the desktop button and a Chrome Start).
        self._start_guard: Callable[[], str | None] | None = None
        # Installation plan round 36 MED-001: the start-up warm-up's hold.
        self._start_hold: Callable[[], bool] | None = None
        # Task 5.2: the first Discard click's session ref and time.
        self._discard_armed: tuple[str | None, float] | None = None
        self.live_status.connect(self._on_live_status)

        self.state_label = QLabel()
        # Cliniko workflow safeguards plan Task 3.3: whether the tracked
        # session is bound to a Cliniko note (never which patient).
        self.link_label = QLabel()
        self.link_label.setTextFormat(Qt.TextFormat.PlainText)
        self.link_label.setWordWrap(True)
        # Constraint 4: the consent tick sits directly above Start, carries
        # PLAN.md's wording verbatim, is NEVER pre-ticked, and is cleared
        # after every Start; Start is disabled until it is ticked.
        self.consent_checkbox = QCheckBox(models.RECORDING_CONSENT_LABEL)
        self.consent_checkbox.setChecked(False)
        self.consent_checkbox.toggled.connect(lambda _checked: self.refresh())
        # Task 4.5: the Chrome link, as the bridge reports it (plain text —
        # it may carry a patient's name for the linked live session).
        self.chrome_label = QLabel()
        self.chrome_label.setTextFormat(Qt.TextFormat.PlainText)
        self.chrome_label.setWordWrap(True)
        self.chrome_label.hide()
        self.message_label = QLabel()
        # Round 48 PR-LOW-002: PLAIN TEXT, always. This label renders
        # exception detail (config validation errors, save/compose failures),
        # which reproduces USER-AUTHORED input - config text a clinician
        # edited, or note text. AutoText would interpret anything markup-like
        # in it as rich text. Same discipline as the proposal excerpt label.
        self.message_label.setTextFormat(Qt.TextFormat.PlainText)
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
        self.discard_button.clicked.connect(self.on_discard_clicked)

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
        layout.addWidget(self.link_label)
        layout.addWidget(self.chrome_label)
        layout.addWidget(self.consent_checkbox)
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
        """True while a transcription run or a discard (round 40 LOW-002) is
        in flight (close must wait)."""
        return self._transcribing or self._discarding

    @property
    def is_discarding(self) -> bool:
        """Round 40 LOW-002: a confirmed Discard is waiting for live
        transcription to stop (the main window's "Open for review" waits)."""
        return self._discarding

    def _watch_state(self) -> None:
        armed = self._discard_armed
        if armed is not None and not self._discard_confirmable(armed):
            # Round 32 LOW-026: "Confirm discard" never outlives its window or
            # its session — the next click asks again, under the plain label.
            self._disarm_discard()
        state = self._controller.state
        generating = self._controller.generating
        if generating != self._last_generating:
            self._last_generating = generating
            self.refresh()  # D6: the review lease gates Start at QUEUED
        writing = self._controller.writing_session_id() is not None
        if writing != self._last_writing:
            self._last_writing = writing
            self.refresh()  # draft-write D9: so does a write in flight
        if state == self._last_state:
            return
        previous = self._last_state
        if (
            state == SessionState.FAILED
            and previous in (SessionState.RECORDING, SessionState.PAUSED)
            # Round 40 LOW-002: a discard that live transcription outlasted
            # routes the session to FAILED itself; its own line says why.
            and not self._discarding
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
        self.link_label.setText(models.session_link_line(self._controller.session))
        controls = models.controls_for_state(state)
        busy = self.is_busy
        # D6: Start for the next patient at QUEUED, unless the note review
        # holds the generation lease or a draft write holds the session
        # (draft-write D9, H1 round 45 LOW-002) — the controller refuses both
        # anyway, but only after the consent tick is spent.
        generating = self._controller.generating
        writing = self._controller.writing_session_id() is not None
        self._last_writing = writing
        startable = controls.start and not busy and not generating and not writing
        self.consent_checkbox.setEnabled(startable)
        self.start_button.setEnabled(startable and self.consent_checkbox.isChecked())
        hint = ""
        if controls.start and generating:
            hint = models.REVIEW_OPEN_START_HINT
        elif controls.start and writing:
            hint = models.write_line("write_in_flight")
        self.start_button.setToolTip(hint)
        self.pause_button.setEnabled(controls.pause and not busy)
        self.resume_button.setEnabled(controls.resume and not busy)
        self.finish_button.setEnabled(controls.finish and not busy)
        self.discard_button.setEnabled(controls.discard and not busy)
        if not self.discard_button.isEnabled():
            self._disarm_discard()

    def _show_message(self, text: str) -> None:
        self.message_label.setText(text)

    def show_notice(self, text: str) -> None:
        """A line from elsewhere in the app (the pause rule's desktop cue)."""
        self._show_message(text)

    def set_resume_guard(self, guard: Callable[[], str | None] | None) -> None:
        """Task 5.1 (D5): the check every Resume from this screen's slot runs
        first — the desktop button, a Chrome command and (Phase 7) the
        hotkey. It returns the refusal to show, or None to go ahead."""
        self._resume_guard = guard

    def set_start_guard(self, guard: Callable[[], str | None] | None) -> None:
        """H1 round 54 MED-052 (D5 as amended 2026-09-28): the check every
        Start from this screen runs first — a click already queued when the
        computer locked must not begin a recording behind the lock. It
        returns the refusal to show, or None to go ahead."""
        self._start_guard = guard

    def set_start_hold(self, hold: Callable[[], bool] | None) -> None:
        """Installation plan round 36 MED-001 (the practitioner's option
        (b)): True while the start-up import warm-up runs, within its bound
        (``ml_warmup.ImportWarmup.holds_start``). Every Start — ``on_start``
        and ``start_linked`` (``ChromeBridge`` also asks ``start_held`` first,
        to name the code in the panel) — is then refused BEFORE anything is
        made or the desktop tick cleared. None never holds."""
        self._start_hold = hold

    def start_held(self) -> bool:
        hold = self._start_hold
        return hold is not None and hold()

    def set_chrome_view(self, text: str) -> None:
        """Task 4.5: the bridge's Chrome lines (hidden when empty)."""
        self.chrome_label.setText(text)
        self.chrome_label.setVisible(bool(text))

    def has_input_device(self) -> bool:
        """Whether Start has a microphone (the bridge names a missing one
        as a refusal before it asks for a linked Start)."""
        return self._device_provider() is not None

    def report_live_status(self, text: str) -> None:
        """Thread-safe: called by the transcriber callable on the processing
        thread; the queued ``live_status`` signal delivers it to the slot."""
        self.live_status.emit(text)

    def _on_live_status(self, text: str) -> None:
        self._live_status = text
        if self._transcribing:
            self.progress_label.setText(f"Transcribing locally... {text}")

    # --- controls ---------------------------------------------------------------

    def on_start(self) -> None:
        """The desktop Start: an UNLINKED recording, behind the consent tick
        (Constraint 4). The tick is cleared whatever the outcome — except
        when the start-up warm-up's hold refuses the press (round 36
        MED-001), which keeps it for the next one."""
        if not self.consent_checkbox.isChecked():
            self._show_message(models.CONSENT_REQUIRED_MESSAGE)
            self.refresh()
            return
        if self._refuse_while_held():
            return  # round 36 MED-001: the tick is KEPT for the next press
        if self._discarding:
            return  # round 40 LOW-002: its own line is up; the tick is kept
        self.consent_checkbox.setChecked(False)
        self._start(unlinked_consent(), None)

    def start_linked(self, consent: ConsentAttestation, context: EncounterContext) -> bool:
        """A linked Start, from the Chrome side panel (Task 4.5): the panel's
        own consent tick produced ``consent``, and the context is the one the
        bound report's verification produced. The controller refuses a
        consent that does not name the context's note. True when it started.
        The desktop tick is cleared too (every Start clears it) — but not by
        a Start the warm-up's hold refuses (round 36 MED-001)."""
        if self._refuse_while_held() or self._discarding:
            return False  # the hold, or a discard under way (round 40 LOW-002)
        self.consent_checkbox.setChecked(False)
        return self._start(consent, context)

    def _refuse_while_held(self) -> bool:
        """Round 36 MED-001: name the hold and refuse, or False to go on."""
        if not self.start_held():
            return False
        self._show_message(models.START_GETTING_READY_MESSAGE)
        self.refresh()
        return True

    def _start(self, consent: ConsentAttestation, context: EncounterContext | None) -> bool:
        guard = self._start_guard
        refusal = guard() if guard is not None else None
        if refusal is not None:
            self._show_message(refusal)
            self.refresh()
            return False
        device_id = self._device_provider()
        if device_id is None:
            self._show_message("Select an input device on the Microphone screen first.")
            self.refresh()
            return False
        started = False
        # D6: a Start retires the previous tracked session (QUEUED, FAILED or
        # finished) — read it BEFORE, while it is still the tracked one.
        previous = self._controller.session
        try:
            session = self._controller.start(device_id, consent=consent, context=context)
            started = True
            if (
                previous is not None
                and not previous.is_terminal
                and previous.session_id != session.session_id
            ):
                self.session_retired.emit(previous)
            self.session_started.emit()
            self._show_message("Recording.")
        except Exception as exc:  # noqa: BLE001 - surfaced, never crashes the UI
            self._show_message(f"Start failed: {models.custody_refusal_text(exc)}")
            if (
                previous is not None
                and not previous.is_terminal
                and self._controller.session is None
            ):
                # H1 round 53 LOW-040: the controller retires the previous
                # session BEFORE the new recording's device opens, so a Start
                # that fails there still retired it — it waits for review.
                self.session_retired.emit(previous)
        self.refresh()
        return started

    # Each control below returns True when it did what it says (the Chrome
    # bridge, Task 4.5, reports a False as a refusal); a button ignores it.
    # Round 40 LOW-002: while a discard waits off the GUI thread, every one
    # of them (the pause rule's and the hotkey's included) does nothing.

    def on_pause(self) -> bool:
        if self._discarding:
            return False
        try:
            self._controller.pause()
            self._show_message("Paused.")
        except Exception as exc:  # noqa: BLE001
            self._show_message(f"Pause failed: {models.custody_refusal_text(exc)}")
            self.refresh()
            return False
        self.refresh()
        return True

    def on_resume(self) -> bool:
        if self._discarding:
            return False
        guard = self._resume_guard
        refusal = guard() if guard is not None else None
        if refusal is not None:
            # D5: a linked session never resumes without a current report of
            # its own note — named, and nothing is called.
            self._show_message(refusal)
            self.refresh()
            return False
        try:
            self._controller.resume()
            self._show_message("Recording.")
        except Exception as exc:  # noqa: BLE001
            self._show_message(f"Resume failed: {models.custody_refusal_text(exc)}")
            self.refresh()
            return False
        self.refresh()
        self.session_resumed.emit()
        return True

    def on_finish(self) -> bool:
        if self._discarding:
            return False
        try:
            session = self._controller.finish()
        except Exception as exc:  # noqa: BLE001
            self._show_message(f"Finish failed: {models.custody_refusal_text(exc)}")
            self.refresh()
            return False
        if session.state != SessionState.PROCESSING:
            # Disk failure during the final flush: failed but RECOVERABLE.
            self._show_message(
                "Recording could not be sealed; the session is recoverable "
                "from the Recovery screen after an app restart, or can be discarded."
            )
            self.refresh()
            return False
        self._begin_transcription()
        return True

    def on_discard_clicked(self) -> None:
        """The Discard BUTTON (Task 5.2): the first click asks, the second —
        within ``DISCARD_CONFIRM_SECONDS``, for the same session — discards.
        A Chrome Discard arrives already confirmed by its own second click
        and calls ``on_discard`` directly."""
        armed = self._discard_armed
        if armed is not None and self._discard_confirmable(armed):
            self._disarm_discard()
            self.on_discard()
            return
        self._discard_armed = (self._controller.session_ref, time.monotonic())
        self.discard_button.setText(DISCARD_CONFIRM_LABEL)
        self._show_message(models.DISCARD_CONFIRM_MESSAGE)

    def _discard_confirmable(self, armed: tuple[str | None, float]) -> bool:
        """The first click was for the session still tracked, and recent."""
        token, at = armed
        return (
            token == self._controller.session_ref
            and 0 <= time.monotonic() - at <= DISCARD_CONFIRM_SECONDS
        )

    def _disarm_discard(self) -> None:
        self._discard_armed = None
        self.discard_button.setText("Discard")

    def on_discard(self, *, on_refused: Callable[[], None] | None = None) -> bool:
        """The confirmed Discard. With no live transcription attached it runs
        here, at once. With one attached (installation plan round 40
        LOW-002) the controller's ``discard`` waits — up to
        ``LIVE_STOP_TIMEOUT_SECONDS`` — for it to stop before the key goes, so
        it runs OFF the GUI thread under ``DISCARD_STOPPING_LIVE_LINE``, with
        every control (and every Chrome command, through ``is_busy``) held
        until it ends; True then means it is under way, and ``on_refused``
        (the Chrome bridge's) runs if it ends refused. The custody rule is the
        controller's, unchanged: a discard live transcription outlasts
        deletes nothing and keeps the session, and the line says so."""
        self._disarm_discard()
        if self._discarding:
            return False
        if self._controller.live_transcription_attached:
            self._begin_discard(on_refused)
            return True
        try:
            self._controller.discard()
        except Exception as exc:  # noqa: BLE001
            self._show_message(models.discard_refusal_line(exc))
            self.refresh()
            return False
        self._discarded()
        return True

    def _discarded(self) -> None:
        self.session_discarded.emit()
        self._show_message("Session discarded (audio cryptographically deleted).")
        self.refresh()

    def _begin_discard(self, on_refused: Callable[[], None] | None) -> None:
        self._discarding = True
        self._discard_on_refused = on_refused
        self.progress_label.setText(models.DISCARD_STOPPING_LIVE_LINE)
        self.progress_label.show()
        self.progress_bar.show()
        self._show_message("")
        controller = self._controller
        unexpected = f"Discard failed: {models.CUSTODY_UNEXPECTED_REASON}"

        def job() -> str | None:
            # The outcome crosses to the GUI thread as its LINE only — never
            # the exception, whose traceback would keep the controller's
            # frames (the session's crypto among them) alive.
            try:
                controller.discard()
            except Exception as exc:  # noqa: BLE001 - shown as its line, never raised
                return models.discard_refusal_line(exc)
            except BaseException:  # noqa: BLE001
                # Round 41: whatever ends this thread, a result is sent —
                # otherwise every control (and every Chrome command) would
                # stay held for good. ``TaskThread`` catches ``Exception``
                # only. The line is the fixed reason; custody stays the
                # controller's, unchanged.
                return unexpected
            return None

        task = TaskThread(job, self)
        task.succeeded.connect(self._on_discard_done)
        task.failed.connect(lambda _message: self._on_discard_done(unexpected))
        self._discard_task = task
        self.refresh()
        task.start()

    def _on_discard_done(self, outcome: object) -> None:
        """GUI thread: the off-thread discard ended — ``None`` when it
        discarded, else the line to show."""
        self._discarding = False
        on_refused, self._discard_on_refused = self._discard_on_refused, None
        if self._discard_task is not None:
            self._discard_task.finish()
            self._discard_task = None
        self.progress_bar.hide()
        self.progress_label.hide()
        if outcome is None:
            self._discarded()
            return
        self._show_message(str(outcome))
        self.refresh()
        if on_refused is not None:
            on_refused()

    # --- transcription (Finish -> processing -> queued) -------------------------

    def _begin_transcription(self) -> None:
        if self._task is not None and self._task.isRunning():
            return
        self._transcribing = True
        self._live_status = None
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
            self._task.finish()
            self._task = None
        self.progress_bar.hide()
        self.progress_label.hide()

    def _on_transcribed(self, document: object) -> None:
        self._end_transcription()
        message = "Transcription complete - review the transcript."
        if self._live_status is not None:
            message = f"{message} {self._live_status}"
        self._show_message(message)
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
