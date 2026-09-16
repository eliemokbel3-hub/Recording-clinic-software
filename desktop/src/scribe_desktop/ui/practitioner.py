"""The Practitioner tab: voice enrolment, consent, deletion (practitioner-
profile plan Phase 3, Task 3.1).

The tab shows consent text v1 VERBATIM (``models.CONSENT_TEXT_V1``) with the
consent checkbox and the separate phrase-learning opt-in, a microphone pick,
and a read-aloud of about a minute. That read-aloud is captured IN MEMORY by
``enrolment.record_enrolment`` on a ``TaskThread`` (D8): no session is
created, no store is touched, no file is ever written, and the PCM is dropped
as soon as ``enrolment.enrol`` has turned it into one vector — the only thing
saved is the encrypted profile ``save_profile`` writes.

The whole capture -> embed -> save -> result-handler sequence runs under
``SessionController.begin_enrolment()`` (D15), so Start/Resume, the
microphone screen's monitor poll and the benchmark all refuse while it runs,
and Re-record/Delete are disabled meanwhile; the idle monitor itself is
handed over synchronously through ``on_capture_start`` (the main window
passes the microphone screen's ``stop_monitor``) before the worker starts.
The lease is released in the result handler — on EVERY path, success or
failure — never before it, so the status line a handler writes is already
visible when the activity ends.
``record_enrolment``'s ``on_progress`` callback fires on the worker thread,
so it is marshalled to the GUI thread through a Qt signal rather than
touching a widget directly.

Re-record replaces the profile under the existing key; Delete asks for
confirmation and is KEY deletion (``delete_profile``: the key first, which is
the cryptographic death of the blob). "Learned phrases" is a placeholder for
Phase 5's propose-then-approve flow.

Enrolment is disabled only when the SELECTED embedder or the VAD model is
unavailable, and the message names ``scripts/setup-models.py`` (D16).

Nothing here logs, and no label ever renders a field of the profile beyond
its creation date and the embedder's ``model_id``.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop.audio_capture import CaptureBackend
from scribe_desktop.enrolment import (
    DEFAULT_TARGET_SPEECH_SECONDS,
    EnrolmentCancelledError,
    EnrolmentProgress,
    enrol,
    record_enrolment,
)
from scribe_desktop.practitioner_profile import (
    ConsentRecord,
    PractitionerProfile,
    delete_profile,
    save_profile,
)
from scribe_desktop.session import EnrolmentLease, SessionActivityError
from scribe_desktop.session_store import StoreWriteError
from scribe_desktop.speaker_embedding import (
    SHIPPED_SPEAKER_EMBEDDER,
    EmbedderKind,
    SpeakerEmbedder,
    build_speaker_embedder,
    speaker_embedder_available,
)
from scribe_desktop.speech import vad_model_available
from scribe_desktop.ui import models
from scribe_desktop.ui.tasks import TaskThread

_AVAILABILITY_POLL_MS: Final = 5000
DEVICE_NAME_MAX_CHARS: Final = 200  # PractitionerProfile.device_name's bound
UNKNOWN_DEVICE_NAME: Final = "unknown microphone"

CaptureFn = Callable[
    [CaptureBackend, int, Callable[[EnrolmentProgress], None], Callable[[], bool]], bytes
]
EmbedFn = Callable[[bytes, SpeakerEmbedder], tuple[Any, float]]


def _default_capture(
    backend: CaptureBackend,
    device_id: int,
    on_progress: Callable[[EnrolmentProgress], None],
    should_stop: Callable[[], bool],
) -> bytes:
    return record_enrolment(backend, device_id, on_progress=on_progress, should_stop=should_stop)


def _default_embed(pcm: bytes, embedder: SpeakerEmbedder) -> tuple[Any, float]:
    return enrol(pcm, embedder)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def profile_device_name(name: str) -> str:
    """A device name reduced to what ``PractitionerProfile.device_name``
    accepts: printable, single-line, at most ``DEVICE_NAME_MAX_CHARS``. Every
    non-printable character, and every whitespace character other than a plain
    space, becomes a space; an empty result becomes ``UNKNOWN_DEVICE_NAME``.
    So a device name can never fail the profile's validation."""
    cleaned = "".join(
        " " if (not ch.isprintable() or (ch.isspace() and ch != " ")) else ch for ch in name
    )
    cleaned = cleaned.strip()[:DEVICE_NAME_MAX_CHARS]
    return cleaned if cleaned else UNKNOWN_DEVICE_NAME


class PractitionerScreen(QWidget):
    # Emitted from the CAPTURE WORKER thread; delivered queued to the GUI slot
    # (`record_enrolment` calls `on_progress` on the thread it runs on).
    _progress_reported = Signal(object)

    def __init__(
        self,
        controller: models.SessionControllerLike,
        backend: CaptureBackend,
        *,
        profile_root: Path | None = None,
        embedder_kind: EmbedderKind = SHIPPED_SPEAKER_EMBEDDER,
        embedder_factory: Callable[[EmbedderKind], SpeakerEmbedder] = build_speaker_embedder,
        embedder_available: Callable[[EmbedderKind], bool] = speaker_embedder_available,
        vad_available: Callable[[], bool] = vad_model_available,
        capture: CaptureFn = _default_capture,
        embed: EmbedFn = _default_embed,
        readiness_provider: Callable[[], models.AttributionReadiness] | None = None,
        confirm_delete: Callable[[], bool] | None = None,
        clock: Callable[[], datetime] = _utc_now,
        on_capture_start: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._backend = backend
        # Peer round 27 PR-MED-022: the main window passes the microphone
        # screen's `stop_monitor` so the idle monitor is handed over
        # SYNCHRONOUSLY, before the worker can open the device.
        self._on_capture_start = on_capture_start
        self._profile_root = profile_root
        self._embedder_kind = embedder_kind
        self._embedder_factory = embedder_factory
        self._embedder_available = embedder_available
        self._vad_available = vad_available
        self._capture = capture
        self._embed = embed
        self._readiness_provider: Callable[[], models.AttributionReadiness] = (
            readiness_provider
            if readiness_provider is not None
            else (
                lambda: models.attribution_readiness(
                    profile_root=profile_root, kind=embedder_kind
                )
            )
        )
        self._confirm_delete = confirm_delete if confirm_delete is not None else self._ask_delete
        self._clock = clock

        self._task: TaskThread | None = None
        self._lease: EnrolmentLease | None = None
        self._cancel_requested = threading.Event()
        self._available = False
        self._profile_present = False
        self._profile: PractitionerProfile | None = None
        self._device_names: dict[int, str] = {}

        # --- first-run banner (D10: first run ASKS, never blocks) -----------
        self.banner_label = QLabel()
        self.banner_label.setTextFormat(Qt.TextFormat.PlainText)
        self.banner_label.setWordWrap(True)
        self.banner_label.setStyleSheet("font-weight: bold;")
        self.banner_label.hide()

        # --- profile state --------------------------------------------------
        self.profile_status_label = QLabel()
        self.profile_status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.profile_status_label.setWordWrap(True)
        profile_box = QGroupBox("Voice profile")
        profile_layout = QVBoxLayout()
        profile_layout.addWidget(self.profile_status_label)
        profile_box.setLayout(profile_layout)

        # --- consent (v1 text VERBATIM) -------------------------------------
        self.consent_text_label = QLabel(models.CONSENT_TEXT_V1)
        self.consent_text_label.setTextFormat(Qt.TextFormat.PlainText)
        self.consent_text_label.setWordWrap(True)
        self.consent_checkbox = QCheckBox(models.CONSENT_CHECKBOX_LABEL)
        self.consent_checkbox.setChecked(False)
        self.consent_checkbox.toggled.connect(lambda *_: self._update_controls())
        self.learning_checkbox = QCheckBox(models.LEARNING_OPT_IN_LABEL)
        self.learning_checkbox.setChecked(False)
        self.learning_note_label = QLabel(
            "Applies when you next record your voice (the saved choice stands until then)."
        )
        self.learning_note_label.setWordWrap(True)
        self.learning_note_label.hide()
        consent_box = QGroupBox("Consent")
        consent_layout = QVBoxLayout()
        consent_layout.addWidget(self.consent_text_label)
        consent_layout.addWidget(self.consent_checkbox)
        consent_layout.addWidget(self.learning_checkbox)
        consent_layout.addWidget(self.learning_note_label)
        consent_box.setLayout(consent_layout)

        # --- the read-aloud --------------------------------------------------
        self.device_combo = QComboBox()
        self.refresh_devices_button = QPushButton("Refresh devices")
        self.refresh_devices_button.clicked.connect(self.refresh_devices)
        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Microphone:"))
        device_row.addWidget(self.device_combo, stretch=1)
        device_row.addWidget(self.refresh_devices_button)

        self.availability_label = QLabel()
        self.availability_label.setTextFormat(Qt.TextFormat.PlainText)
        self.availability_label.setWordWrap(True)
        self.availability_label.setStyleSheet("color: #b00020;")
        self.availability_label.hide()

        self.record_button = QPushButton("Record my voice (about a minute)")
        self.record_button.clicked.connect(self.on_record)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.on_stop)
        self.stop_button.hide()
        button_row = QHBoxLayout()
        button_row.addWidget(self.record_button)
        button_row.addWidget(self.stop_button)

        self.level_bar = QProgressBar()
        self.level_bar.setRange(0, 100)
        self.level_bar.setValue(0)
        self.level_bar.setTextVisible(False)
        self.progress_label = QLabel(self._progress_text(0.0))
        self.enrolment_status_label = QLabel()
        self.enrolment_status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.enrolment_status_label.setWordWrap(True)
        self.enrolment_status_label.hide()

        record_box = QGroupBox("Record your voice")
        record_layout = QVBoxLayout()
        record_layout.addLayout(device_row)
        record_layout.addWidget(self.availability_label)
        record_layout.addLayout(button_row)
        record_layout.addWidget(QLabel("Input level:"))
        record_layout.addWidget(self.level_bar)
        record_layout.addWidget(self.progress_label)
        record_layout.addWidget(self.enrolment_status_label)
        record_box.setLayout(record_layout)

        # --- deletion ---------------------------------------------------------
        self.delete_button = QPushButton("Delete voice profile")
        self.delete_button.clicked.connect(self.on_delete)

        # --- learned phrases (Phase 5 placeholder) -----------------------------
        self.learned_phrases_list = QListWidget()
        self.learned_phrases_list.setEnabled(False)
        self.learned_phrases_note_label = QLabel(
            "No learned phrases yet. Phrase learning arrives with a later update."
        )
        self.learned_phrases_note_label.setWordWrap(True)
        phrases_box = QGroupBox("Learned phrases")
        phrases_layout = QVBoxLayout()
        phrases_layout.addWidget(self.learned_phrases_list)
        phrases_layout.addWidget(self.learned_phrases_note_label)
        phrases_box.setLayout(phrases_layout)

        layout = QVBoxLayout()
        layout.addWidget(self.banner_label)
        layout.addWidget(profile_box)
        layout.addWidget(consent_box)
        layout.addWidget(record_box)
        layout.addWidget(self.delete_button)
        layout.addWidget(phrases_box)
        layout.addStretch(1)
        self.setLayout(layout)

        self._progress_reported.connect(self._on_progress)

        self._availability_timer = QTimer(self)
        self._availability_timer.setInterval(_AVAILABILITY_POLL_MS)
        self._availability_timer.timeout.connect(self.refresh_availability)
        self._availability_timer.start()

        self.refresh_devices()
        self.refresh_availability()
        self.refresh_profile_state()

    # --- text helpers --------------------------------------------------------

    def _progress_text(self, speech_seconds: float) -> str:
        return (
            f"Speech heard: {speech_seconds:.0f} s of "
            f"{DEFAULT_TARGET_SPEECH_SECONDS:.0f} s"
        )

    def _ask_delete(self) -> bool:
        return (
            QMessageBox.question(
                self,
                "Delete voice profile",
                "Delete your voice profile? Consultations go back to the manual "
                "clinician confirmation until you record again.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        )

    # --- devices --------------------------------------------------------------

    def refresh_devices(self) -> None:
        current = self.device_combo.currentData()
        self.device_combo.clear()
        try:
            devices = self._backend.list_input_devices()
        except Exception:  # noqa: BLE001 - enumeration failure must not crash the UI
            devices = []
        for device in devices:
            self._device_names[device.device_id] = device.name
            label = device.name + (" (default)" if device.is_default else "")
            self.device_combo.addItem(label, device.device_id)
            if device.is_default and current is None:
                self.device_combo.setCurrentIndex(self.device_combo.count() - 1)
        if current is not None:
            index = self.device_combo.findData(current)
            if index >= 0:
                self.device_combo.setCurrentIndex(index)
        self._update_controls()

    def selected_device(self) -> tuple[int, str] | None:
        """``(device_id, raw device name)`` for the selected microphone."""
        data = self.device_combo.currentData()
        if data is None:
            return None
        device_id = int(data)
        return device_id, self._device_names.get(device_id, UNKNOWN_DEVICE_NAME)

    # --- model availability (D16) ---------------------------------------------

    def refresh_availability(self) -> None:
        model_ok = self._embedder_available(self._embedder_kind)
        vad_ok = self._vad_available()
        lines: list[str] = []
        if not model_ok:
            lines.append(
                "Voice enrolment is unavailable: the speaker model is not installed - "
                "run scripts/setup-models.py --only speaker-embedding."
            )
        if not vad_ok:
            lines.append(
                "Voice enrolment is unavailable: the VAD model (silero) is not "
                "installed - run scripts/setup-models.py."
            )
        self._available = model_ok and vad_ok
        self.availability_label.setText("\n".join(lines))
        if lines:
            self.availability_label.show()
        else:
            self.availability_label.hide()
        self._update_controls()

    # --- profile state ---------------------------------------------------------

    def refresh_profile_state(self) -> None:
        """Re-read the profile store (one profile read, no model loaded) and
        re-render everything that depends on it."""
        previously_readable = self._profile is not None
        readiness = self._readiness_provider()
        self._profile_present = readiness.profile_present
        self._profile = readiness.profile
        if not readiness.profile_present:
            self.profile_status_label.setText("No voice profile yet.")
        elif readiness.profile is not None:
            profile = readiness.profile
            self.profile_status_label.setText(
                f"Voice profile saved {profile.created_at:%Y-%m-%d} "
                f"(model {profile.model_id})."
            )
        else:
            self.profile_status_label.setText(
                readiness.reason or models.ATTRIBUTION_DID_NOT_RUN_REASON
            )
        if readiness.profile_present:
            if self._profile is not None:
                # A READABLE profile carries the consent record ticked when it
                # was saved: that record is what pre-ticks the box (peer round
                # 27 PR-HIGH-006). An unreadable blob is NOT evidence of
                # consent — its box stays as it is (unticked on construction)
                # and enabled, so recording over it needs a fresh tick; Delete
                # stays available either way.
                self.consent_checkbox.setChecked(True)
                self.learning_checkbox.setChecked(self._profile.consent.learning_opt_in)
                self.learning_note_label.show()
            else:
                if previously_readable:
                    # The tick on show came from a record that is now
                    # unreadable (an interrupted Delete in this session): it
                    # is withdrawn with the record; a tick the practitioner
                    # made over an already-unreadable blob is kept.
                    self.consent_checkbox.setChecked(False)
                self.learning_note_label.hide()
            self.record_button.setText("Re-record my voice")
            self.banner_label.hide()
        else:
            # The checkboxes are left AS THEY ARE: a failed enrolment must not
            # make the practitioner tick consent again.
            self.learning_note_label.hide()
            self.record_button.setText("Record my voice (about a minute)")
        self._update_controls()

    @property
    def profile_present(self) -> bool:
        return self._profile_present

    @property
    def is_busy(self) -> bool:
        """True while the enrolment worker runs (close must wait — D15)."""
        return self._task is not None and self._task.isRunning()

    def show_first_run_banner(self) -> None:
        self.banner_label.setText(models.FIRST_RUN_BANNER)
        self.banner_label.show()

    # --- enablement --------------------------------------------------------------

    def _update_controls(self) -> None:
        busy = self.is_busy
        self.record_button.setEnabled(
            not busy
            and self._available
            and self.consent_checkbox.isChecked()
            and self.selected_device() is not None
        )
        self.stop_button.setVisible(busy)
        self.stop_button.setEnabled(busy and not self._cancel_requested.is_set())
        self.delete_button.setEnabled(not busy and self._profile_present)
        self.device_combo.setEnabled(not busy)
        self.refresh_devices_button.setEnabled(not busy)
        # Consent is fixed while a READABLE profile exists (withdrawal is
        # Delete); an unreadable blob leaves it editable (PR-HIGH-006). The
        # learning opt-in stays editable whenever idle — its value applies at
        # the next (re-)record (PR-MED-021).
        self.consent_checkbox.setEnabled(not busy and self._profile is None)
        self.learning_checkbox.setEnabled(not busy)

    def _set_enrolment_status(self, message: str | None) -> None:
        if message is None:
            self.enrolment_status_label.setText("")
            self.enrolment_status_label.hide()
        else:
            self.enrolment_status_label.setText(message)
            self.enrolment_status_label.show()

    # --- enrolment ----------------------------------------------------------------

    def on_record(self) -> None:
        if self.is_busy:
            return
        device = self.selected_device()
        if device is None:
            self._set_enrolment_status("No microphone selected - pick one above.")
            return
        if not self.consent_checkbox.isChecked():
            self._set_enrolment_status("Tick the consent box to record your voice.")
            return
        if not self._available:
            return  # the availability label already names the remedy
        try:
            lease = self._controller.begin_enrolment()
        except SessionActivityError as exc:
            self._set_enrolment_status(f"Cannot record now - {exc}")
            return
        self._lease = lease
        if self._on_capture_start is not None:
            # PR-MED-022: hand the microphone over on THIS (GUI) thread before
            # the worker starts; the microphone screen's poll guard keeps the
            # monitor closed afterwards. A failing handoff releases the lease
            # and starts nothing.
            try:
                self._on_capture_start()
            except Exception as exc:  # noqa: BLE001 - surfaced, the lease released
                self._release_lease()
                self._set_enrolment_status(f"Cannot record now - {type(exc).__name__}: {exc}")
                return
        self._cancel_requested.clear()
        device_id, device_name = device
        learning_opt_in = self.learning_checkbox.isChecked()
        kind = self._embedder_kind
        backend, capture, embed = self._backend, self._capture, self._embed
        embedder_factory, clock, root = self._embedder_factory, self._clock, self._profile_root
        saved_device_name = profile_device_name(device_name)
        emit_progress = self._progress_reported.emit
        should_stop = self._cancel_requested.is_set

        def raise_if_stopped() -> None:
            # Round 25 MED-001: the capture honours Stop only while it runs;
            # a Stop pressed after it returned must not end in a saved
            # profile. Checked again before the embedding and after it —
            # once that final check has passed, the profile is built and
            # ``save_profile`` runs regardless (round 28 PR-LOW-032: the
            # residue starts at the final check, not at the save); it is
            # then shown, and Delete removes it.
            if should_stop():
                raise EnrolmentCancelledError("enrolment cancelled")

        def work() -> None:  # WORKER THREAD (TaskThread) — no widget access here
            embedder = embedder_factory(kind)  # BEFORE the read-aloud: load failures fail fast
            pcm = capture(backend, device_id, emit_progress, should_stop)
            try:
                raise_if_stopped()
                vector, speech_seconds = embed(pcm, embedder)
            finally:
                del pcm  # D8: the only reference this thread holds is dropped here
            raise_if_stopped()
            now = clock()
            profile = PractitionerProfile(
                model_id=embedder.model_id,
                model_sha256=embedder.model_sha256,
                embedding=tuple(float(v) for v in vector),
                embedding_dim=len(vector),
                created_at=now,
                enrolment_speech_seconds=speech_seconds,
                device_name=saved_device_name,
                consent=ConsentRecord(
                    accepted_at=now,
                    consent_text_version=models.CONSENT_TEXT_VERSION,
                    learning_opt_in=learning_opt_in,
                ),
            )
            save_profile(profile, root=root)

        self._set_enrolment_status("Listening - read aloud in your normal voice.")
        self.level_bar.setValue(0)
        self.progress_label.setText(self._progress_text(0.0))
        task = TaskThread(work, self)
        task.succeeded.connect(self._on_enrolment_done)
        task.failed.connect(self._on_enrolment_failed)
        self._task = task
        # `is_busy` reads `QThread.isRunning()`, which is only true once
        # `start()` has been called — so the busy enablement is applied AFTER
        # the start, never before it (the result handler cannot have run yet:
        # its delivery is queued to this, the GUI, thread).
        task.start()
        self._update_controls()

    def _on_progress(self, progress: object) -> None:
        # GUI thread (queued delivery of `_progress_reported`).
        assert isinstance(progress, EnrolmentProgress)
        self.level_bar.setValue(round(progress.level * 100))
        self.progress_label.setText(self._progress_text(progress.speech_seconds))

    def on_stop(self) -> None:
        if not self.is_busy:
            return
        self._cancel_requested.set()
        self._set_enrolment_status("Stopping...")
        self._update_controls()

    def _join_task(self) -> None:
        if self._task is not None:
            self._task.finish()
            self._task = None

    def _release_lease(self) -> None:
        lease = self._lease
        self._lease = None
        if lease is not None:
            self._controller.end_enrolment(lease)

    def _on_enrolment_done(self, _result: object) -> None:
        try:
            self._join_task()
            self._set_enrolment_status("Voice profile saved.")
            self.refresh_profile_state()  # re-read from disk: the status line proves the save
            self.level_bar.setValue(0)
            self._update_controls()
        finally:
            self._release_lease()  # D15: released only after this handler, on every path

    def _on_enrolment_failed(self, message: str) -> None:
        try:
            self._join_task()
            if message.startswith("EnrolmentCancelledError"):
                text = "Enrolment stopped - nothing was saved."
            else:
                text = f"Enrolment did not complete - {message}"
            self._set_enrolment_status(text)
            self.refresh_profile_state()  # a failed re-enrolment leaves the previous one usable
            self.level_bar.setValue(0)
            self.progress_label.setText(self._progress_text(0.0))
            self._update_controls()
        finally:
            self._release_lease()

    # --- deletion -------------------------------------------------------------------

    def on_delete(self) -> None:
        if self.is_busy or not self._profile_present:
            return
        if not self._confirm_delete():
            return
        try:
            delete_profile(root=self._profile_root)
        except StoreWriteError as exc:
            self._set_enrolment_status(f"Could not delete the voice profile - {exc}")
            self.refresh_profile_state()
            return
        self.consent_checkbox.setChecked(False)
        self.learning_checkbox.setChecked(False)
        self._set_enrolment_status("Voice profile deleted.")
        self.refresh_profile_state()


__all__ = [
    "DEVICE_NAME_MAX_CHARS",
    "UNKNOWN_DEVICE_NAME",
    "PractitionerScreen",
    "profile_device_name",
]
