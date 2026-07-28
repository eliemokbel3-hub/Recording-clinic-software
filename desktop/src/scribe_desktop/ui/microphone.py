"""Microphone screen: device pick + live level meter + benchmark/model
report panel (plan Step 10; the benchmark is a PANEL here, not a screen)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop.audio_capture import CaptureBackend, CaptureStream, pcm16_rms_level
from scribe_desktop.benchmark import (
    BenchmarkResult,
    default_models_root,
    run_all,
    threshold_report,
)
from scribe_desktop.session import SessionState
from scribe_desktop.ui import models
from scribe_desktop.ui.tasks import TaskThread

_LEVEL_POLL_MS = 100
# Smoke round 21: while a session records/pauses, the CaptureWorker owns the
# device and the meter reads controller.level; in every other state the screen
# opens its OWN monitoring stream so device selection gives live feedback.
_MONITOR_STATES = frozenset(
    s for s in SessionState if s not in (SessionState.RECORDING, SessionState.PAUSED)
)
# ~3 s of near-zero level on an OPEN monitor stream -> actionable hint (a
# privacy-blocked mic typically delivers silent blocks, not an error).
_SILENCE_POLLS = 30
_SILENCE_THRESHOLD = 0.005
_PRIVACY_HINT = (
    "check Windows Settings > Privacy & security > Microphone "
    "(allow desktop apps to access your microphone) and the mic's mute switch."
)


def _default_benchmark_runner() -> list[BenchmarkResult]:
    return run_all(default_models_root())


class MicrophoneScreen(QWidget):
    def __init__(
        self,
        controller: models.SessionControllerLike,
        backend: CaptureBackend,
        *,
        benchmark_runner: Callable[[], list[BenchmarkResult]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._backend = backend
        self._benchmark_runner = (
            benchmark_runner if benchmark_runner is not None else _default_benchmark_runner
        )
        self._benchmark_task: TaskThread | None = None

        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self._on_device_selected)
        self.refresh_button = QPushButton("Refresh devices")
        self.refresh_button.clicked.connect(self.refresh_devices)

        self.level_bar = QProgressBar()
        self.level_bar.setRange(0, 100)
        self.level_bar.setValue(0)
        self.level_bar.setTextVisible(False)

        # Live-monitor state (smoke round 21). _monitor_level/_monitor_dead
        # are written from the device callback thread and read from the GUI
        # timer — single scalar writes, no locking needed.
        self._monitor_stream: CaptureStream | None = None
        self._monitor_device_id: int | None = None
        self._monitor_level: float = 0.0
        self._monitor_dead: str | None = None
        self._monitor_open_error: str | None = None
        self._failed_device_id: int | None = None
        self._silent_polls = 0
        self.level_status_label = QLabel()
        self.level_status_label.setStyleSheet("color: #b00020;")
        self.level_status_label.setWordWrap(True)
        self.level_status_label.hide()

        # Benchmark / model report panel.
        self.model_status_label = QLabel()
        self.benchmark_button = QPushButton("Run hardware benchmark")
        self.benchmark_button.clicked.connect(self.on_run_benchmark)
        self.benchmark_output = QPlainTextEdit()
        self.benchmark_output.setReadOnly(True)
        self.benchmark_output.setPlaceholderText(
            "Benchmark not run yet. Transcription is always local; "
            "there is no cloud fallback."
        )
        self.benchmark_warning_label = QLabel()
        self.benchmark_warning_label.setStyleSheet("color: #b00020; font-weight: bold;")
        self.benchmark_warning_label.setWordWrap(True)
        self.benchmark_warning_label.hide()

        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Input device:"))
        device_row.addWidget(self.device_combo, stretch=1)
        device_row.addWidget(self.refresh_button)

        report_box = QGroupBox("Benchmark / model report")
        report_layout = QVBoxLayout()
        report_layout.addWidget(self.model_status_label)
        report_layout.addWidget(self.benchmark_button)
        report_layout.addWidget(self.benchmark_output)
        report_layout.addWidget(self.benchmark_warning_label)
        report_box.setLayout(report_layout)

        layout = QVBoxLayout()
        layout.addLayout(device_row)
        layout.addWidget(QLabel("Input level:"))
        layout.addWidget(self.level_bar)
        layout.addWidget(self.level_status_label)
        layout.addWidget(report_box)
        layout.addStretch(1)
        self.setLayout(layout)

        self._level_timer = QTimer(self)
        self._level_timer.setInterval(_LEVEL_POLL_MS)
        self._level_timer.timeout.connect(self._poll_level)
        self._level_timer.start()

        # Smoke round 21: the model report must never go permanently stale
        # (a long-lived instance kept showing MISSING after setup-models ran).
        self._model_status_timer = QTimer(self)
        self._model_status_timer.setInterval(5000)
        self._model_status_timer.timeout.connect(self.refresh_model_status)
        self._model_status_timer.start()

        self.refresh_devices()
        self.refresh_model_status()

    # --- devices ------------------------------------------------------------

    def _on_device_selected(self, _index: int) -> None:
        # A fresh selection is an explicit retry: forget the failure latch.
        self._failed_device_id = None
        self._monitor_open_error = None

    def refresh_devices(self) -> None:
        self._failed_device_id = None
        self._monitor_open_error = None
        # Refreshing is also the moment models may have appeared on disk
        # (smoke round 21: the report label must never go permanently stale).
        self.refresh_model_status()
        current = self.selected_device_id()
        self.device_combo.clear()
        try:
            devices = self._backend.list_input_devices()
        except Exception:  # noqa: BLE001 - enumeration failure must not crash the UI
            devices = []
        for device in devices:
            label = device.name + (" (default)" if device.is_default else "")
            self.device_combo.addItem(label, device.device_id)
            if device.is_default and current is None:
                self.device_combo.setCurrentIndex(self.device_combo.count() - 1)
        if current is not None:
            index = self.device_combo.findData(current)
            if index >= 0:
                self.device_combo.setCurrentIndex(index)

    def selected_device_id(self) -> int | None:
        data = self.device_combo.currentData()
        return int(data) if data is not None else None

    # --- level meter ----------------------------------------------------------

    def _poll_level(self) -> None:
        if self._controller.state in _MONITOR_STATES:
            self._poll_monitor_level()
        else:
            # A live CaptureWorker owns the device: meter from the SAME
            # stream that feeds the store (plan decision), monitor closed.
            self.stop_monitor()
            self.level_bar.setValue(round(self._controller.level * 100))
            self._set_level_status(None)

    def _poll_monitor_level(self) -> None:
        dead = self._monitor_dead
        if dead is not None:
            self.stop_monitor()
            self._monitor_dead = None
            self._failed_device_id = self.selected_device_id()
            self._monitor_open_error = f"Microphone monitor stopped ({dead}) - {_PRIVACY_HINT}"
        self._ensure_monitor()
        if self._monitor_stream is None:
            self.level_bar.setValue(0)
            self._set_level_status(self._monitor_open_error)
            return
        level = self._monitor_level
        self.level_bar.setValue(round(level * 100))
        if level < _SILENCE_THRESHOLD:
            self._silent_polls += 1
        else:
            self._silent_polls = 0
        if self._silent_polls >= _SILENCE_POLLS:
            self._set_level_status(f"No signal from the selected microphone - {_PRIVACY_HINT}")
        else:
            self._set_level_status(None)

    def _ensure_monitor(self) -> None:
        device_id = self.selected_device_id()
        if device_id is None:
            self.stop_monitor()
            self._monitor_open_error = (
                "No input device found - check Windows sound settings and " + _PRIVACY_HINT
            )
            return
        if self._monitor_stream is not None and self._monitor_device_id == device_id:
            return
        self.stop_monitor()
        if device_id == self._failed_device_id:
            return  # don't hammer a failing device; Refresh/reselect retries
        self._monitor_level = 0.0
        self._monitor_dead = None
        self._silent_polls = 0
        try:
            self._monitor_stream = self._backend.open_stream(
                device_id, self._on_monitor_block, self._on_monitor_error
            )
        except Exception as exc:  # noqa: BLE001 - must surface in the UI, never crash it
            self._failed_device_id = device_id
            self._monitor_open_error = f"Could not open the microphone ({exc}) - {_PRIVACY_HINT}"
            return
        self._monitor_device_id = device_id
        self._monitor_open_error = None

    def _on_monitor_block(self, block: bytes) -> None:
        # Device callback thread: level only; monitor audio is NEVER stored.
        self._monitor_level = pcm16_rms_level(block)

    def _on_monitor_error(self, exc: Exception) -> None:
        self._monitor_dead = str(exc) or type(exc).__name__

    def stop_monitor(self) -> None:
        """Close the idle-monitor stream (recording handoff / app close)."""
        stream = self._monitor_stream
        self._monitor_stream = None
        self._monitor_device_id = None
        self._monitor_level = 0.0
        if stream is not None:
            try:
                stream.stop()
            except Exception:  # noqa: BLE001, S110 - teardown must never crash the UI
                pass

    def _set_level_status(self, message: str | None) -> None:
        if message is None:
            self.level_status_label.hide()
            self.level_status_label.setText("")
        else:
            self.level_status_label.setText(message)
            self.level_status_label.show()

    # --- benchmark / model report panel ---------------------------------------

    def refresh_model_status(self) -> None:
        self.model_status_label.setText("\n".join(models.model_report_lines()))

    def on_run_benchmark(self) -> None:
        if self._benchmark_task is not None and self._benchmark_task.isRunning():
            return
        self.benchmark_button.setEnabled(False)
        self.benchmark_warning_label.hide()
        self.benchmark_output.setPlainText("Benchmark running (local only)...")
        task = TaskThread(self._benchmark_runner, self)
        task.succeeded.connect(self._on_benchmark_done)
        task.failed.connect(self._on_benchmark_failed)
        self._benchmark_task = task
        task.start()

    @property
    def is_busy(self) -> bool:
        """True while a benchmark run is in flight (close must wait)."""
        return self._benchmark_task is not None and self._benchmark_task.isRunning()

    def _join_task(self) -> None:
        if self._benchmark_task is not None:
            self._benchmark_task.wait(2000)
            self._benchmark_task = None

    def _on_benchmark_done(self, results: object) -> None:
        self._join_task()
        assert isinstance(results, list)
        self.benchmark_output.setPlainText("\n".join(threshold_report(results)))
        failed = [r.model_name for r in results if r.status == "fail"]
        if failed:
            # Plan: warning on failure — NEVER a cloud fallback.
            self.benchmark_warning_label.setText(
                "Benchmark threshold FAILED for: "
                + ", ".join(failed)
                + ". Transcription will run slower than real time on this "
                "machine. It stays local; there is no cloud fallback."
            )
            self.benchmark_warning_label.show()
        self.refresh_model_status()
        self.benchmark_button.setEnabled(True)

    def _on_benchmark_failed(self, message: str) -> None:
        self._join_task()
        self.benchmark_output.setPlainText(f"Benchmark failed: {message}")
        self.refresh_model_status()
        self.benchmark_button.setEnabled(True)
