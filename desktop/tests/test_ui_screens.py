"""Step 10: offscreen smoke tests for the UI screens — construction,
state-driven enablement, and signal wiring against fakes. No real audio
or ML in CI (mock backends and canned transcripts only)."""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from scribe_desktop.audio_capture import AudioDevice  # noqa: E402
from scribe_desktop.benchmark import BenchmarkResult  # noqa: E402
from scribe_desktop.secure_storage import SessionCrypto  # noqa: E402
from scribe_desktop.session import RecordingSession, SessionState  # noqa: E402
from scribe_desktop.session_store import (  # noqa: E402
    AUDIO_FILENAME,
    KEY_FILENAME,
    SessionChunkStore,
)
from scribe_desktop.transcription import (  # noqa: E402
    RecoveryOutcome,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
)
from scribe_desktop.ui import models  # noqa: E402


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _process_until(qapp: Any, predicate: Callable[[], bool], timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qapp.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def _document() -> TranscriptDocument:
    return TranscriptDocument(
        session_id=uuid.uuid4().hex,
        created_at=datetime.now(UTC),
        model_name="small",
        sample_rate=16_000,
        transcript_segments=(
            TranscriptSegment(
                start_seconds=0.0,
                end_seconds=2.0,
                speaker="speaker_1",
                transcript_words=(
                    TranscriptWord(
                        word_text="Hello",
                        start_seconds=0.0,
                        end_seconds=0.5,
                        probability=0.95,
                        uncertain=False,
                    ),
                    TranscriptWord(
                        word_text="Margaret",
                        start_seconds=0.6,
                        end_seconds=1.0,
                        probability=0.40,
                        uncertain=True,
                    ),
                ),
            ),
        ),
    )


class FakeBackend:
    def __init__(self, devices: list[AudioDevice] | None = None) -> None:
        self.devices = devices if devices is not None else [
            AudioDevice(device_id=1, name="Mic A", is_default=False),
            AudioDevice(device_id=7, name="Mic B", is_default=True),
        ]

    def list_input_devices(self) -> list[AudioDevice]:
        return list(self.devices)

    def open_stream(self, device_id: int, on_block: Any, on_error: Any) -> Any:
        # Smoke round 21: the microphone screen MAY open an idle-monitor
        # stream; this fake refuses, exercising the visible-failure path.
        raise AssertionError("fake backend cannot open streams")


class FakeController:
    """Duck-typed SessionControllerLike recording every call."""

    def __init__(self) -> None:
        self.state_value = SessionState.IDLE
        self.level_value = 0.25
        self.calls: list[tuple[Any, ...]] = []
        self.transcribe_error: Exception | None = None
        self.session_value: RecordingSession | None = None

    @property
    def state(self) -> SessionState:
        return self.state_value

    @property
    def level(self) -> float:
        return self.level_value

    @property
    def session(self) -> RecordingSession | None:
        return self.session_value

    def _session(self) -> RecordingSession:
        return RecordingSession().with_state(self.state_value)

    def start(self, device_id: int) -> RecordingSession:
        self.calls.append(("start", device_id))
        self.state_value = SessionState.RECORDING
        return self._session()

    def pause(self) -> RecordingSession:
        self.calls.append(("pause",))
        self.state_value = SessionState.PAUSED
        return self._session()

    def resume(self) -> RecordingSession:
        self.calls.append(("resume",))
        self.state_value = SessionState.RECORDING
        return self._session()

    def finish(self) -> RecordingSession:
        self.calls.append(("finish",))
        self.state_value = SessionState.PROCESSING
        return self._session()

    def transcribe(self, transcriber: Callable[[Path, Any], object]) -> RecordingSession:
        self.calls.append(("transcribe",))
        try:
            transcriber(Path("unused"), SessionCrypto())
        except Exception:
            self.state_value = SessionState.FAILED
            raise
        if self.transcribe_error is not None:
            self.state_value = SessionState.FAILED
            raise self.transcribe_error
        self.state_value = SessionState.QUEUED
        return self._session()

    def complete(self) -> RecordingSession:
        self.calls.append(("complete",))
        self.state_value = SessionState.WRITTEN
        return self._session()

    def discard(self) -> RecordingSession:
        self.calls.append(("discard",))
        self.state_value = SessionState.DISCARDED
        return self._session()

    def active_session_ids(self) -> frozenset[str]:
        return frozenset()


# ---------------------------------------------------------------------------
# Microphone screen.
# ---------------------------------------------------------------------------


class TestMicrophoneScreen:
    def test_devices_populated_and_default_selected(self, qapp: Any) -> None:
        from scribe_desktop.ui.microphone import MicrophoneScreen

        screen = MicrophoneScreen(FakeController(), FakeBackend(), benchmark_runner=list)
        assert screen.device_combo.count() == 2
        assert screen.selected_device_id() == 7  # default device preferred
        screen.deleteLater()

    def test_level_meter_polls_controller_while_recording(self, qapp: Any) -> None:
        from scribe_desktop.ui.microphone import MicrophoneScreen

        controller = FakeController()
        controller.state_value = SessionState.RECORDING
        controller.level_value = 0.5
        screen = MicrophoneScreen(controller, FakeBackend(), benchmark_runner=list)
        screen._poll_level()
        assert screen.level_bar.value() == 50
        assert not screen.level_status_label.isVisibleTo(screen)
        screen.deleteLater()

    def test_idle_monitor_streams_live_level(self, qapp: Any) -> None:
        """Smoke round 21: selecting a device while IDLE must give live
        level feedback from a monitoring stream (not controller.level)."""
        from scribe_desktop.audio_capture import MockCaptureBackend
        from scribe_desktop.ui.microphone import MicrophoneScreen

        backend = MockCaptureBackend(
            [AudioDevice(device_id=3, name="Mock Mic", is_default=True)]
        )
        screen = MicrophoneScreen(FakeController(), backend, benchmark_runner=list)
        screen._poll_level()  # opens the monitor
        assert backend.stream_open and backend.opened_device_id == 3
        backend.feed(b"\x00\x40" * 1600)  # loud-ish PCM16 block
        screen._poll_level()
        assert screen.level_bar.value() > 0
        assert not screen.level_status_label.isVisibleTo(screen)
        screen.stop_monitor()
        assert not backend.stream_open
        screen.deleteLater()

    def test_monitor_open_failure_shows_actionable_message(self, qapp: Any) -> None:
        from scribe_desktop.ui.microphone import MicrophoneScreen

        screen = MicrophoneScreen(FakeController(), FakeBackend(), benchmark_runner=list)
        screen._poll_level()
        assert screen.level_bar.value() == 0
        assert screen.level_status_label.isVisibleTo(screen)
        assert "Privacy" in screen.level_status_label.text()
        # The failure is latched: polling again must not hammer the device.
        screen._poll_level()
        assert screen.level_status_label.isVisibleTo(screen)
        screen.deleteLater()

    def test_monitor_silence_shows_privacy_hint(self, qapp: Any) -> None:
        from scribe_desktop.audio_capture import MockCaptureBackend
        from scribe_desktop.ui import microphone as mic_module
        from scribe_desktop.ui.microphone import MicrophoneScreen

        backend = MockCaptureBackend(
            [AudioDevice(device_id=3, name="Mock Mic", is_default=True)]
        )
        screen = MicrophoneScreen(FakeController(), backend, benchmark_runner=list)
        screen._poll_level()
        for _ in range(mic_module._SILENCE_POLLS):
            backend.feed(b"\x00\x00" * 1600)  # pure silence
            screen._poll_level()
        assert screen.level_status_label.isVisibleTo(screen)
        assert "No signal" in screen.level_status_label.text()
        # Signal returning clears the hint.
        backend.feed(b"\x00\x40" * 1600)
        screen._poll_level()
        assert not screen.level_status_label.isVisibleTo(screen)
        screen.deleteLater()

    def test_monitor_device_loss_surfaces_and_recording_takes_over(
        self, qapp: Any
    ) -> None:
        from scribe_desktop.audio_capture import MockCaptureBackend
        from scribe_desktop.ui.microphone import MicrophoneScreen

        controller = FakeController()
        backend = MockCaptureBackend(
            [AudioDevice(device_id=3, name="Mock Mic", is_default=True)]
        )
        screen = MicrophoneScreen(controller, backend, benchmark_runner=list)
        screen._poll_level()
        backend.fail()  # device lost mid-monitor
        screen._poll_level()
        assert screen.level_status_label.isVisibleTo(screen)
        assert "Privacy" in screen.level_status_label.text()
        # Recording state: meter switches to controller.level, monitor closed.
        controller.state_value = SessionState.RECORDING
        controller.level_value = 0.8
        screen._poll_level()
        assert screen.level_bar.value() == 80
        assert not screen.level_status_label.isVisibleTo(screen)
        screen.deleteLater()

    def test_model_report_panel_shows_status_lines(self, qapp: Any) -> None:
        from scribe_desktop.ui.microphone import MicrophoneScreen

        screen = MicrophoneScreen(FakeController(), FakeBackend(), benchmark_runner=list)
        text = screen.model_status_label.text()
        assert "Whisper model" in text and "VAD model" in text
        screen.deleteLater()

    def test_benchmark_failure_threshold_shows_warning(self, qapp: Any) -> None:
        from scribe_desktop.ui.microphone import MicrophoneScreen

        slow = BenchmarkResult(
            model_name="small",
            audio_seconds=50.0,
            load_seconds=1.0,
            transcribe_seconds=100.0,
            rtf=2.0,
            peak_memory_bytes=500 * 2**20,
            word_count=100,
        )
        screen = MicrophoneScreen(
            FakeController(), FakeBackend(), benchmark_runner=lambda: [slow]
        )
        screen.on_run_benchmark()
        assert _process_until(qapp, lambda: screen.benchmark_button.isEnabled())
        assert "FAIL" in screen.benchmark_output.toPlainText()
        assert screen.benchmark_warning_label.isVisibleTo(screen)
        warning = screen.benchmark_warning_label.text()
        assert "no cloud fallback" in warning
        screen.deleteLater()

    def test_benchmark_ok_shows_no_warning(self, qapp: Any) -> None:
        from scribe_desktop.ui.microphone import MicrophoneScreen

        fast = BenchmarkResult(
            model_name="small",
            audio_seconds=50.0,
            load_seconds=1.0,
            transcribe_seconds=5.0,
            rtf=0.1,
            peak_memory_bytes=500 * 2**20,
            word_count=100,
        )
        screen = MicrophoneScreen(
            FakeController(), FakeBackend(), benchmark_runner=lambda: [fast]
        )
        screen.on_run_benchmark()
        assert _process_until(qapp, lambda: screen.benchmark_button.isEnabled())
        assert "OK" in screen.benchmark_output.toPlainText()
        assert not screen.benchmark_warning_label.isVisibleTo(screen)
        screen.deleteLater()


# ---------------------------------------------------------------------------
# Session screen.
# ---------------------------------------------------------------------------


def _session_screen(
    controller: FakeController,
    *,
    device: int | None = 7,
    transcriber: Callable[[Path, Any], TranscriptDocument] | None = None,
) -> Any:
    from scribe_desktop.ui.session_screen import SessionScreen

    factory = (lambda: transcriber) if transcriber is not None else (
        lambda: (lambda d, c: _document())
    )
    return SessionScreen(
        controller,
        device_provider=lambda: device,
        transcriber_factory=factory,  # type: ignore[arg-type]
    )


class TestSessionScreen:
    def test_idle_enablement(self, qapp: Any) -> None:
        screen = _session_screen(FakeController())
        assert screen.start_button.isEnabled()
        for button in (
            screen.pause_button,
            screen.resume_button,
            screen.finish_button,
            screen.discard_button,
        ):
            assert not button.isEnabled()
        screen.deleteLater()

    def test_start_uses_selected_device_and_updates_enablement(self, qapp: Any) -> None:
        controller = FakeController()
        screen = _session_screen(controller, device=7)
        screen.on_start()
        assert ("start", 7) in controller.calls
        assert not screen.start_button.isEnabled()
        assert screen.pause_button.isEnabled()
        assert screen.finish_button.isEnabled()
        assert screen.discard_button.isEnabled()
        screen.deleteLater()

    def test_start_without_device_shows_message(self, qapp: Any) -> None:
        controller = FakeController()
        screen = _session_screen(controller, device=None)
        screen.on_start()
        assert controller.calls == []
        assert "Microphone screen" in screen.message_label.text()
        screen.deleteLater()

    def test_pause_resume_wiring(self, qapp: Any) -> None:
        controller = FakeController()
        screen = _session_screen(controller)
        screen.on_start()
        screen.on_pause()
        assert ("pause",) in controller.calls
        assert screen.resume_button.isEnabled() and not screen.pause_button.isEnabled()
        screen.on_resume()
        assert ("resume",) in controller.calls
        assert screen.pause_button.isEnabled()
        screen.deleteLater()

    def test_finish_drives_transcription_and_emits_document(self, qapp: Any) -> None:
        controller = FakeController()
        screen = _session_screen(controller)
        received: list[TranscriptDocument] = []
        screen.transcript_ready.connect(received.append)
        screen.on_start()
        screen.on_finish()
        assert _process_until(qapp, lambda: bool(received))
        assert ("transcribe",) in controller.calls
        assert controller.state_value == SessionState.QUEUED
        assert isinstance(received[0], TranscriptDocument)
        assert not screen.progress_bar.isVisibleTo(screen)
        screen.deleteLater()

    def test_transcription_failure_reports_recoverable(self, qapp: Any) -> None:
        controller = FakeController()

        def broken(_d: Path, _c: Any) -> TranscriptDocument:
            raise RuntimeError("model exploded")

        screen = _session_screen(controller, transcriber=broken)
        screen.on_start()
        screen.on_finish()
        assert _process_until(
            qapp, lambda: "recoverable" in screen.message_label.text()
        )
        assert controller.state_value == SessionState.FAILED
        assert screen.discard_button.isEnabled()  # failed -> discard only
        screen.deleteLater()

    def test_state_watcher_surfaces_async_capture_failure(self, qapp: Any) -> None:
        """PR round 18 (PR3): device loss flips the controller to failed from
        the worker thread; the poll must refresh enablement + message."""
        controller = FakeController()
        screen = _session_screen(controller)
        screen.on_start()
        controller.state_value = SessionState.FAILED  # async failure
        screen._watch_state()
        assert "Recording failed" in screen.message_label.text()
        assert screen.discard_button.isEnabled()
        assert not screen.pause_button.isEnabled()
        screen.deleteLater()

    def test_transcription_task_reference_dropped_after_success(self, qapp: Any) -> None:
        """PR round 18 (PR7): no closure chain retaining the plaintext
        document survives the run."""
        controller = FakeController()
        screen = _session_screen(controller)
        received: list[TranscriptDocument] = []
        screen.transcript_ready.connect(received.append)
        screen.on_start()
        screen.on_finish()
        assert _process_until(qapp, lambda: bool(received))
        assert screen._task is None
        assert screen.is_busy is False
        screen.deleteLater()

    def test_discard_wiring(self, qapp: Any) -> None:
        controller = FakeController()
        screen = _session_screen(controller)
        screen.on_start()
        screen.on_discard()
        assert ("discard",) in controller.calls
        assert "cryptographically deleted" in screen.message_label.text()
        assert screen.start_button.isEnabled()
        screen.deleteLater()


# ---------------------------------------------------------------------------
# Recovery screen.
# ---------------------------------------------------------------------------


def _make_recoverable(root: Path, *, finished: bool) -> str:
    session_id = uuid.uuid4().hex
    directory = root / session_id
    directory.mkdir(parents=True)
    (directory / KEY_FILENAME).write_bytes(b"\x01" * 64)
    crypto = SessionCrypto()
    store = SessionChunkStore.create(directory / AUDIO_FILENAME, crypto, session_id)
    store.append_chunk(b"\x00\x01" * 800)
    if finished:
        store.finish()
    store.close()
    crypto.destroy()
    return session_id


class TestRecoveryScreen:
    def test_lists_sessions_and_warns_on_unfinished_store(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.ui.recovery import RecoveryScreen

        _make_recoverable(tmp_path, finished=False)
        screen = RecoveryScreen(
            tmp_path, recovery_runner=lambda d: pytest.fail("not called")
        )
        assert screen.session_list.count() == 1
        screen.session_list.setCurrentRow(0)
        qapp.processEvents()
        # Binding Step-10 note: warn whenever store_finished is False.
        assert screen.warning_label.isVisibleTo(screen)
        assert screen.warning_label.text() == models.UNFINISHED_STORE_WARNING
        assert screen.resume_button.isEnabled()
        screen.deleteLater()

    def test_finished_store_shows_no_warning(self, qapp: Any, tmp_path: Path) -> None:
        from scribe_desktop.ui.recovery import RecoveryScreen

        _make_recoverable(tmp_path, finished=True)
        screen = RecoveryScreen(
            tmp_path, recovery_runner=lambda d: pytest.fail("not called")
        )
        screen.session_list.setCurrentRow(0)
        qapp.processEvents()
        assert not screen.warning_label.isVisibleTo(screen)
        screen.deleteLater()

    def test_resume_processing_emits_outcome(self, qapp: Any, tmp_path: Path) -> None:
        from scribe_desktop.ui.recovery import RecoveryScreen

        session_id = _make_recoverable(tmp_path, finished=False)
        outcome = RecoveryOutcome(
            document=_document(), crypto=SessionCrypto(), store_finished=False
        )
        received: list[object] = []
        screen = RecoveryScreen(tmp_path, recovery_runner=lambda d: outcome)
        screen.recovered.connect(received.append)
        screen.session_list.setCurrentRow(0)
        screen.on_resume_processing()
        assert _process_until(qapp, lambda: bool(received))
        directory, got = received[0]  # type: ignore[misc]
        assert directory == tmp_path / session_id
        assert got is outcome
        screen.deleteLater()

    def test_discard_deletes_key_first_and_refreshes(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.ui.recovery import RecoveryScreen

        session_id = _make_recoverable(tmp_path, finished=True)
        screen = RecoveryScreen(
            tmp_path, recovery_runner=lambda d: pytest.fail("not called")
        )
        screen.session_list.setCurrentRow(0)
        screen.on_discard()
        assert not (tmp_path / session_id / KEY_FILENAME).exists()
        assert screen.session_list.count() == 0
        screen.deleteLater()

    def test_active_session_never_listed(self, qapp: Any, tmp_path: Path) -> None:
        from scribe_desktop.ui.recovery import RecoveryScreen

        session_id = _make_recoverable(tmp_path, finished=False)
        screen = RecoveryScreen(
            tmp_path,
            active_ids_provider=lambda: frozenset({session_id}),
            recovery_runner=lambda d: pytest.fail("not called"),
        )
        assert screen.session_list.count() == 0
        screen.deleteLater()

    def test_recovered_session_checked_out_until_released(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """PR round 18 (PR1): a recovered session must vanish from the list
        while its transcript view holds custody, and return on release
        (its key custody is still intact until Complete/Discard)."""
        from scribe_desktop.ui.recovery import RecoveryScreen

        session_id = _make_recoverable(tmp_path, finished=True)
        outcome = RecoveryOutcome(
            document=_document(), crypto=SessionCrypto(), store_finished=True
        )
        received: list[object] = []
        screen = RecoveryScreen(tmp_path, recovery_runner=lambda d: outcome)
        screen.recovered.connect(received.append)
        screen.session_list.setCurrentRow(0)
        screen.on_resume_processing()
        assert _process_until(qapp, lambda: bool(received))
        assert screen.session_list.count() == 0  # checked out, not listed
        assert screen.protected_session_ids() == frozenset({session_id})
        screen.release_checkouts()
        assert screen.protected_session_ids() == frozenset()
        assert screen.session_list.count() == 1  # key custody still live
        screen.deleteLater()

    def test_second_resume_refused_while_checkout_open(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """PR round 19 (MED): a second resume while a recovered transcript
        is still open must be refused — it would overwrite the open view's
        custody callbacks."""
        from scribe_desktop.ui.recovery import RecoveryScreen

        _make_recoverable(tmp_path, finished=True)
        _make_recoverable(tmp_path, finished=True)
        outcomes: list[object] = []
        calls: list[Path] = []

        def runner(directory: Path) -> RecoveryOutcome:
            calls.append(directory)
            return RecoveryOutcome(
                document=_document(), crypto=SessionCrypto(), store_finished=True
            )

        screen = RecoveryScreen(tmp_path, recovery_runner=runner)
        screen.recovered.connect(outcomes.append)
        screen.session_list.setCurrentRow(0)
        screen.on_resume_processing()
        assert _process_until(qapp, lambda: bool(outcomes))
        assert len(calls) == 1
        # One session remains listed; resume must now be refused.
        assert screen.session_list.count() == 1
        screen.session_list.setCurrentRow(0)
        qapp.processEvents()
        assert not screen.resume_button.isEnabled()
        screen.on_resume_processing()  # direct call also refused
        assert len(calls) == 1
        assert "Finish the open recovered transcript" in screen.message_label.text()
        screen.release_checkouts()
        screen.session_list.setCurrentRow(0)
        qapp.processEvents()
        assert screen.resume_button.isEnabled()
        screen.deleteLater()

    def test_failed_recovery_releases_protection(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.ui.recovery import RecoveryScreen

        _make_recoverable(tmp_path, finished=True)

        def broken(_d: Path) -> RecoveryOutcome:
            raise RuntimeError("model exploded")

        screen = RecoveryScreen(tmp_path, recovery_runner=broken)
        screen.session_list.setCurrentRow(0)
        screen.on_resume_processing()
        assert _process_until(
            qapp, lambda: "Recovery failed" in screen.message_label.text()
        )
        assert screen.protected_session_ids() == frozenset()
        assert screen.session_list.count() == 1  # still recoverable
        screen.deleteLater()

    def test_no_resume_recording_control_exists(self, qapp: Any, tmp_path: Path) -> None:
        """Flow 3 Critical Constraint: recovery offers resume-PROCESSING and
        discard only — never resume recording."""
        from PySide6.QtWidgets import QPushButton

        from scribe_desktop.ui.recovery import RecoveryScreen

        screen = RecoveryScreen(
            tmp_path, recovery_runner=lambda d: pytest.fail("not called")
        )
        labels = [b.text().lower() for b in screen.findChildren(QPushButton)]
        assert labels == ["resume processing", "discard", "refresh"]
        screen.deleteLater()


# ---------------------------------------------------------------------------
# Transcript-inspection view.
# ---------------------------------------------------------------------------


class TestTranscriptScreen:
    def test_renders_marks_and_speakers_and_completes(self, qapp: Any) -> None:
        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen()
        assert not screen.complete_button.isEnabled()
        completed: list[str] = []
        calls: list[str] = []
        screen.closed.connect(completed.append)
        screen.show_document(
            _document(),
            on_complete=lambda: calls.append("complete"),
            on_discard=lambda: calls.append("discard"),
        )
        text = screen.transcript_view.toPlainText()
        assert "speaker_1" in text
        assert "[Margaret?]" in text  # uncertainty mark visible
        assert "Hello" in text
        assert not screen.warning_label.isVisibleTo(screen)
        screen.on_complete()
        assert calls == ["complete"]
        assert completed == ["completed"]
        assert screen.transcript_view.toPlainText() == ""  # display cleared
        assert not screen.complete_button.isEnabled()
        screen.deleteLater()

    def test_transcript_view_has_no_text_interaction(self, qapp: Any) -> None:
        """PR round 18 (PR5): no selection/copy — transcript text must not
        reach the Windows clipboard (history / cloud sync)."""
        from PySide6.QtCore import Qt

        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen()
        flags = screen.transcript_view.textInteractionFlags()
        assert flags == Qt.TextInteractionFlag.NoTextInteraction
        screen.deleteLater()

    def test_unfinished_store_warning_shown(self, qapp: Any) -> None:
        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen()
        screen.show_document(
            _document(),
            on_complete=lambda: None,
            on_discard=lambda: None,
            store_finished=False,
        )
        assert screen.warning_label.isVisibleTo(screen)
        assert screen.warning_label.text() == models.UNFINISHED_STORE_WARNING
        screen.deleteLater()

    def test_failed_complete_keeps_session_available(self, qapp: Any) -> None:
        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen()

        def failing() -> None:
            raise RuntimeError("verify failed")

        screen.show_document(
            _document(), on_complete=failing, on_discard=lambda: None
        )
        screen.on_complete()
        assert "Complete failed" in screen.message_label.text()
        # Round 42 LOW-001: the message states only what THIS action
        # verified — the sweep may have destroyed the key independently, so
        # the old unconditional "key was kept" claim was rewritten.
        assert "No key deletion was performed by this action" in (
            screen.message_label.text()
        )
        assert screen.complete_button.isEnabled()  # still actionable
        assert screen.transcript_view.toPlainText() != ""
        screen.deleteLater()

    def test_discard_emits_closed(self, qapp: Any) -> None:
        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen()
        outcomes: list[str] = []
        screen.closed.connect(outcomes.append)
        screen.show_document(
            _document(), on_complete=lambda: None, on_discard=lambda: None
        )
        screen.on_discard()
        assert outcomes == ["discarded"]
        assert screen.transcript_view.toPlainText() == ""
        screen.deleteLater()


# ---------------------------------------------------------------------------
# Main window wiring.
# ---------------------------------------------------------------------------


class TestMainWindow:
    def test_constructs_all_screens(self, qapp: Any, tmp_path: Path) -> None:
        from scribe_desktop.ui.main_window import MainWindow

        window = MainWindow(
            FakeController(),
            FakeBackend(),
            sessions_root=tmp_path,
            benchmark_runner=list,
            recovery_runner=lambda d: pytest.fail("not called"),
        )
        assert window.tabs.count() == 5
        titles = [window.tabs.tabText(i) for i in range(window.tabs.count())]
        assert titles == ["Microphone", "Session", "Recovery", "Transcript", "Status"]
        window.close()

    def test_live_transcript_routed_to_inspection_view(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.ui.main_window import MainWindow

        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        window = MainWindow(
            controller,
            FakeBackend(),
            sessions_root=tmp_path,
            benchmark_runner=list,
            recovery_runner=lambda d: pytest.fail("not called"),
        )
        window.session_screen.transcript_ready.emit(_document())
        qapp.processEvents()
        assert window.tabs.currentWidget() is window.transcript_screen
        assert "[Margaret?]" in window.transcript_screen.transcript_view.toPlainText()
        # Complete routes to the controller (live custody path).
        window.transcript_screen.on_complete()
        assert ("complete",) in controller.calls
        window.close()

    def test_close_refused_while_transcribing(self, qapp: Any, tmp_path: Path) -> None:
        """PR round 18 (PR6): closing must not destroy a running worker."""
        from PySide6.QtGui import QCloseEvent

        from scribe_desktop.ui.main_window import MainWindow

        window = MainWindow(
            FakeController(),
            FakeBackend(),
            sessions_root=tmp_path,
            benchmark_runner=list,
            recovery_runner=lambda d: pytest.fail("not called"),
        )
        window.session_screen._transcribing = True
        event = QCloseEvent()
        window.closeEvent(event)
        assert not event.isAccepted()
        window.session_screen._transcribing = False
        event2 = QCloseEvent()
        window.closeEvent(event2)
        assert event2.isAccepted()

    def test_close_refused_while_recording(self, qapp: Any, tmp_path: Path) -> None:
        """Round 42 MED-002 (guard-only, pending user ratification): closing
        mid-recording would kill the daemon capture worker and silently drop
        the buffered tail of a live consultation — refuse, like the PR6
        thread guard refuses for a running benchmark."""
        from PySide6.QtGui import QCloseEvent

        from scribe_desktop.ui.main_window import MainWindow

        controller = FakeController()
        window = MainWindow(
            controller,
            FakeBackend(),
            sessions_root=tmp_path,
            benchmark_runner=list,
            recovery_runner=lambda d: pytest.fail("not called"),
        )
        for blocked_state in (SessionState.RECORDING, SessionState.PAUSED):
            controller.state_value = blocked_state
            event = QCloseEvent()
            window.closeEvent(event)
            assert not event.isAccepted(), blocked_state
        controller.state_value = SessionState.IDLE
        event2 = QCloseEvent()
        window.closeEvent(event2)
        assert event2.isAccepted()

    def test_benchmark_refused_while_session_active(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 42 LOW-002 (guard-only, pending user ratification): the
        benchmark saturates the CPU for minutes and can starve live capture
        into a queue-overflow failure — never startable during an active
        session."""
        from scribe_desktop.ui.microphone import MicrophoneScreen

        controller = FakeController()
        screen = MicrophoneScreen(
            controller,
            FakeBackend(),
            benchmark_runner=lambda: pytest.fail("benchmark must not start"),
        )
        for active_state in (
            SessionState.RECORDING,
            SessionState.PAUSED,
            SessionState.PROCESSING,
        ):
            controller.state_value = active_state
            screen.on_run_benchmark()
            assert not screen.is_busy, active_state
            assert "unavailable while a session is active" in (
                screen.benchmark_output.toPlainText()
            )
        screen.stop_monitor()

    def test_recovered_checkout_crypto_destroyed_on_live_overwrite(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 42 LOW-006: when a live transcript overwrites an open
        recovered checkout, the checkout's unwrapped in-memory key must be
        zeroized (its custody callbacks are unreachable; disk custody stays
        for a post-restart recovery)."""
        from scribe_desktop.ui.main_window import MainWindow

        controller = FakeController()
        window = MainWindow(
            controller,
            FakeBackend(),
            sessions_root=tmp_path,
            benchmark_runner=list,
            recovery_runner=lambda d: pytest.fail("not called"),
        )
        crypto = SessionCrypto()
        directory = tmp_path / uuid.uuid4().hex
        directory.mkdir()
        outcome = RecoveryOutcome(
            document=_document(), crypto=crypto, store_finished=True
        )
        window._on_recovered((directory, outcome))
        assert not crypto.destroyed  # checkout open: key usable for custody
        controller.state_value = SessionState.QUEUED
        window.session_screen.transcript_ready.emit(_document())
        qapp.processEvents()
        assert crypto.destroyed  # overwritten checkout's key copy zeroized
        # disk custody untouched by the in-memory destroy (no key file was
        # ever created here — the destroy must not try to touch disk)
        assert not (directory / KEY_FILENAME).exists()
        window.close()

    def test_live_controller_session_excluded_from_recovery_list(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """PR round 18 (PR1): a queued/failed session the controller still
        owns must not be offered through the recovery custody path."""
        from scribe_desktop.ui.main_window import MainWindow

        session_id = _make_recoverable(tmp_path, finished=True)
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        controller.session_value = RecordingSession.model_construct(
            session_id=session_id,
            encounter_context=None,
            key_reference="key.dpapi",
            state=SessionState.QUEUED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        window = MainWindow(
            controller,
            FakeBackend(),
            sessions_root=tmp_path,
            benchmark_runner=list,
            recovery_runner=lambda d: pytest.fail("not called"),
        )
        assert window.recovery_screen.session_list.count() == 0
        controller.session_value = None
        window.recovery_screen.refresh()
        assert window.recovery_screen.session_list.count() == 1
        window.close()

    def test_live_transcript_close_never_releases_recovered_checkout(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """PR round 20 (PR-HIGH-009): closing a LIVE transcript must not
        strip an open recovered session's sweep/relist protection; closing
        the recovered transcript releases exactly its own checkout."""
        from scribe_desktop.ui.main_window import MainWindow

        recovered_id = _make_recoverable(tmp_path, finished=True)
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        window = MainWindow(
            controller,
            FakeBackend(),
            sessions_root=tmp_path,
            benchmark_runner=list,
            recovery_runner=lambda d: pytest.fail("not called"),
        )
        # Simulate an open recovered transcript (checked out).
        window.recovery_screen._protected.add(recovered_id)
        outcome = RecoveryOutcome(
            document=_document(), crypto=SessionCrypto(), store_finished=True
        )
        window.recovery_screen.recovered.emit((tmp_path / recovered_id, outcome))
        qapp.processEvents()
        assert recovered_id in window.recovery_screen.protected_session_ids()
        # A live transcript replaces the view, then closes.
        window.session_screen.transcript_ready.emit(_document())
        qapp.processEvents()
        window.transcript_screen.on_complete()  # live path -> controller
        qapp.processEvents()
        assert ("complete",) in controller.calls
        # The recovered session's protection survives the live closure.
        assert recovered_id in window.recovery_screen.protected_session_ids()
        window.close()

    def test_recovered_transcript_close_releases_only_itself(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.ui.main_window import MainWindow

        recovered_id = _make_recoverable(tmp_path, finished=True)
        other_id = uuid.uuid4().hex
        window = MainWindow(
            FakeController(),
            FakeBackend(),
            sessions_root=tmp_path,
            benchmark_runner=list,
            recovery_runner=lambda d: pytest.fail("not called"),
        )
        window.recovery_screen._protected.update({recovered_id, other_id})
        crypto = SessionCrypto()
        outcome = RecoveryOutcome(
            document=_document(), crypto=crypto, store_finished=True
        )
        window.recovery_screen.recovered.emit((tmp_path / recovered_id, outcome))
        qapp.processEvents()
        window.transcript_screen.on_discard()  # discards the recovered store
        qapp.processEvents()
        protected = window.recovery_screen.protected_session_ids()
        assert recovered_id not in protected
        assert other_id in protected  # scoped release: others untouched
        window.close()

    def test_recovered_transcript_carries_unfinished_warning(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.ui.main_window import MainWindow

        window = MainWindow(
            FakeController(),
            FakeBackend(),
            sessions_root=tmp_path,
            benchmark_runner=list,
            recovery_runner=lambda d: pytest.fail("not called"),
        )
        outcome = RecoveryOutcome(
            document=_document(), crypto=SessionCrypto(), store_finished=False
        )
        window.recovery_screen.recovered.emit((tmp_path / uuid.uuid4().hex, outcome))
        qapp.processEvents()
        assert window.tabs.currentWidget() is window.transcript_screen
        assert window.transcript_screen.warning_label.isVisibleTo(
            window.transcript_screen
        )
        window.close()
