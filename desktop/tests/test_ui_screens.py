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
from scribe_desktop.note import (  # noqa: E402
    CANONICAL_SECTION_KEYS,
    CLINICIAN_OWNED_SECTIONS,
    NOTE_WARNING_SEVERITY,
    ConfirmationDecision,
    ExtractiveNoteProvider,
    GeneratedNote,
    ProposalResolution,
    compose_draft,
    finalise_note,
    text_digest,
)
from scribe_desktop.note_config import (  # noqa: E402
    AutofillRule,
    NoteConfig,
    PrefillSeedAssertion,
    PrefillTemplate,
    SectionMapping,
    TemplateProfile,
    TemplateTarget,
)
from scribe_desktop.secure_storage import SessionCrypto  # noqa: E402
from scribe_desktop.session import (  # noqa: E402
    GenerationInProgressError,
    GenerationLease,
    RecordingSession,
    SessionActivityError,
    SessionState,
)
from scribe_desktop.session_store import (  # noqa: E402
    AUDIO_FILENAME,
    KEY_FILENAME,
    SessionChunkStore,
)
from scribe_desktop.transcription import (  # noqa: E402
    SPEAKER_1,
    SPEAKER_2,
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
        # Task 6.3: when set, every lease-guarded custody op refuses with it
        # (simulates a held generation lease — or, round 30, a held discard
        # reservation — in the real controller).
        self.generation_error: Exception | None = None
        self.lease: GenerationLease | None = None
        # Round 30: ids an in-flight discard has reserved (the real
        # controller's reserved_session_ids source).
        self.reserved_ids: frozenset[str] = frozenset()
        # Phase 7: the (directory, crypto) the scoped generation op hands to
        # its action. Tests point these at a real session dir when they want
        # the action (write_note) to actually run.
        self.generation_dir = Path("unused")
        self.generation_crypto: SessionCrypto | None = None

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

    def complete_without_note(self, lease: GenerationLease) -> RecordingSession:
        self.calls.append(("complete_without_note",))
        if self.generation_error is not None:
            raise self.generation_error  # failure -> lease stays held (not consumed)
        if self.lease is lease:
            self.lease = None  # consume the lease only on success
        self.state_value = SessionState.WRITTEN
        return self._session()

    def complete_deleting_saved_note(self) -> RecordingSession:
        self.calls.append(("complete_deleting_saved_note",))
        if self.generation_error is not None:
            raise self.generation_error
        self.state_value = SessionState.WRITTEN
        return self._session()

    def discard(self) -> RecordingSession:
        self.calls.append(("discard",))
        self.state_value = SessionState.DISCARDED
        return self._session()

    def active_session_ids(self) -> frozenset[str]:
        return frozenset()

    # Task 6.3: the lease + the lease-aware recovered-custody coordinator.

    def begin_generation(self) -> GenerationLease:
        self.calls.append(("begin_generation",))
        if self.generation_error is not None:
            raise self.generation_error
        lease = GenerationLease()
        self.lease = lease
        return lease

    def end_generation(self, lease: GenerationLease) -> None:
        self.calls.append(("end_generation",))
        if self.lease is lease:
            self.lease = None

    def reserved_session_ids(self) -> frozenset[str]:
        return self.reserved_ids

    def custody_protected_ids(self) -> frozenset[str]:
        # Mirrors the real controller's atomic snapshot semantics (round 31):
        # reservations plus the non-terminal live session.
        ids = self.reserved_ids
        if self.session_value is not None and not self.session_value.is_terminal:
            ids = ids | {self.session_value.session_id}
        return ids

    def complete_recovered(self, directory: Path, crypto: SessionCrypto) -> None:
        self.calls.append(("complete_recovered", directory))
        if self.generation_error is not None:
            raise self.generation_error
        crypto.destroy()

    def discard_recovered(self, directory: Path, crypto: SessionCrypto | None) -> None:
        self.calls.append(("discard_recovered", directory))
        if self.generation_error is not None:
            raise self.generation_error
        if crypto is not None:
            crypto.destroy()

    def destroy_recovered_crypto(self, crypto: SessionCrypto) -> None:
        self.calls.append(("destroy_recovered_crypto",))
        if self.generation_error is not None:
            raise self.generation_error
        crypto.destroy()

    def with_generation_custody(
        self, lease: GenerationLease, action: Callable[[Path, SessionCrypto], Any]
    ) -> Any:
        self.calls.append(("with_generation_custody",))
        if self.generation_error is not None:
            raise self.generation_error
        crypto = self.generation_crypto if self.generation_crypto is not None else SessionCrypto()
        return action(self.generation_dir, crypto)


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
        assert window.tabs.count() == 6
        titles = [window.tabs.tabText(i) for i in range(window.tabs.count())]
        assert titles == [
            "Microphone",
            "Session",
            "Recovery",
            "Transcript",
            "Note",
            "Status",
        ]
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

    def _recovered_window(
        self, tmp_path: Path
    ) -> tuple[Any, FakeController, Path, SessionCrypto]:
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
        outcome = RecoveryOutcome(document=_document(), crypto=crypto, store_finished=True)
        window._on_recovered((directory, outcome))
        return window, controller, directory, crypto

    def test_recovered_custody_routes_through_the_coordinator(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Task 6.3: the recovered transcript view's Complete/Discard run
        through the controller's lease-aware coordinator, never through raw
        store primitives."""
        window, controller, directory, crypto = self._recovered_window(tmp_path)
        window.transcript_screen.on_complete()
        assert ("complete_recovered", directory) in controller.calls
        assert crypto.destroyed
        window.close()

    def test_recovered_discard_routes_through_the_coordinator(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window, controller, directory, crypto = self._recovered_window(tmp_path)
        window.transcript_screen.on_discard()
        assert ("discard_recovered", directory) in controller.calls
        assert crypto.destroyed
        window.close()

    def test_recovered_complete_refused_while_generating(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """A held generation lease blocks recovered Complete: the refusal
        surfaces in the view, custody survives, the view stays open."""
        window, controller, directory, crypto = self._recovered_window(tmp_path)
        controller.generation_error = GenerationInProgressError(
            "complete refused: a note generation is in progress"
        )
        window.transcript_screen.on_complete()
        assert ("complete_recovered", directory) in controller.calls
        assert not crypto.destroyed
        assert "Complete failed" in window.transcript_screen.message_label.text()
        # The view did not close: its custody callbacks are still armed.
        assert window.transcript_screen.complete_button.isEnabled()
        window.close()

    def test_destroy_recovered_crypto_retained_while_generating(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Task 6.3 Done-when: `_destroy_recovered_crypto`-during-generation.
        The coordinator refuses, the in-memory key survives for the worker,
        and the retained reference is cleaned up on the next (post-release)
        pass."""
        window, controller, _directory, crypto = self._recovered_window(tmp_path)
        controller.generation_error = GenerationInProgressError(
            "recovered-key destruction refused: a note generation is in progress"
        )
        window._destroy_recovered_crypto()
        assert not crypto.destroyed
        assert window._recovered_crypto is crypto  # reference retained for cleanup
        controller.generation_error = None  # generation released
        window._destroy_recovered_crypto()
        assert crypto.destroyed
        assert window._recovered_crypto is None
        window.close()

    def test_destroy_recovered_crypto_retained_while_discard_reserved(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 30: the coordinator's coarse reservation refusal
        (SessionActivityError) is caught the same way as the generation
        refusal — key retained, cleaned up after release."""
        window, controller, _directory, crypto = self._recovered_window(tmp_path)
        controller.generation_error = SessionActivityError(
            "recovered-key destruction refused: a discard is in flight"
        )
        window._destroy_recovered_crypto()
        assert not crypto.destroyed
        assert window._recovered_crypto is crypto
        controller.generation_error = None
        window._destroy_recovered_crypto()
        assert crypto.destroyed
        window.close()

    def test_live_session_ids_include_reserved_discard_targets(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 30: the recovery-list exclusion is sourced from the
        controller's RESERVATION SET, not only the mutable live session."""
        from scribe_desktop.ui.main_window import MainWindow

        reserved_id = uuid.uuid4().hex
        controller = FakeController()
        controller.reserved_ids = frozenset({reserved_id})
        window = MainWindow(
            controller,
            FakeBackend(),
            sessions_root=tmp_path,
            benchmark_runner=list,
            recovery_runner=lambda d: pytest.fail("not called"),
        )
        assert reserved_id in window._live_session_ids()
        window.close()

    def test_stale_recovery_resume_refused_at_click_time(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 30: the rendered list can be stale — a session reserved by
        an in-flight discard AFTER listing must be refused at resume time,
        BEFORE any key unwrap."""
        from scribe_desktop.ui.main_window import MainWindow

        recovered_id = _make_recoverable(tmp_path, finished=True)
        controller = FakeController()
        window = MainWindow(
            controller,
            FakeBackend(),
            sessions_root=tmp_path,
            benchmark_runner=list,
            recovery_runner=lambda d: pytest.fail("must never unwrap"),
        )
        assert window.recovery_screen.session_list.count() == 1
        window.recovery_screen.session_list.setCurrentRow(0)
        controller.reserved_ids = frozenset({recovered_id})  # discard begins now
        window.recovery_screen.on_resume_processing()
        assert not window.recovery_screen.is_busy  # refused before any unwrap
        assert "busy elsewhere" in window.recovery_screen.message_label.text()
        window.close()

    def test_live_session_ids_is_one_atomic_snapshot(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 31: the exclusion set is ONE controller snapshot — the
        window must not compose split reserved/live reads, because a
        Discard-reserve + admitted Start between two reads yields a set
        omitting the still-reserved session."""
        from scribe_desktop.ui.main_window import MainWindow

        controller = FakeController()
        window = MainWindow(
            controller,
            FakeBackend(),
            sessions_root=tmp_path,
            benchmark_runner=list,
            recovery_runner=lambda d: pytest.fail("not called"),
        )
        snap_id = uuid.uuid4().hex
        calls: list[str] = []

        def atomic() -> frozenset[str]:
            calls.append("snapshot")
            return frozenset({snap_id})

        def split_read() -> frozenset[str]:
            pytest.fail("split read: a consumer composed reserved_session_ids")

        controller.custody_protected_ids = atomic  # type: ignore[method-assign]
        controller.reserved_session_ids = split_read  # type: ignore[method-assign]
        assert window._live_session_ids() == frozenset({snap_id})
        assert calls == ["snapshot"]
        window.close()

    def test_stale_recovery_discard_refused_at_click_time(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from scribe_desktop.ui.main_window import MainWindow

        recovered_id = _make_recoverable(tmp_path, finished=True)
        controller = FakeController()
        window = MainWindow(
            controller,
            FakeBackend(),
            sessions_root=tmp_path,
            benchmark_runner=list,
            recovery_runner=lambda d: pytest.fail("not called"),
        )
        assert window.recovery_screen.session_list.count() == 1
        window.recovery_screen.session_list.setCurrentRow(0)
        controller.reserved_ids = frozenset({recovered_id})
        window.recovery_screen.on_discard()
        assert (tmp_path / recovered_id).exists()  # custody untouched
        assert "busy elsewhere" in window.recovery_screen.message_label.text()
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


# ---------------------------------------------------------------------------
# Phase 7 note-review fixtures + tests.
# ---------------------------------------------------------------------------

_NOTE_SESSION_ID = "e" * 32


def _note_config() -> NoteConfig:
    profile = TemplateProfile(
        template_profile_id="clinic-a",
        display_name="Clinic A",
        template_targets=(
            TemplateTarget(
                target_id="t-main", group="Notes", field_label="Main", target_type="rich_text"
            ),
        ),
        section_mappings=tuple(
            SectionMapping(section_key=key, target_id="t-main")
            for key in CANONICAL_SECTION_KEYS
            if key != "consent"
        ),
        intentionally_unmapped=("consent",),
    )
    return NoteConfig(
        template_profiles=(profile,),
        autofill_rules=(
            AutofillRule(
                rule_id="rule-ice",
                section_key="advice_home_exercise",
                trigger_phrase="ice pack",
                expansion=("Ice pack use explained.",),
            ),
        ),
        prefill_templates=(
            PrefillTemplate(
                prefill_id="knee-exam",
                display_name="Knee examination",
                region_keywords=("knee",),
                seed_assertions=(
                    PrefillSeedAssertion(
                        section_key="objective_examination", seed_text="Knee effusion assessed."
                    ),
                ),
            ),
        ),
    )


def _note_words(text: str, *, probability: float = 0.9) -> tuple[TranscriptWord, ...]:
    return tuple(
        TranscriptWord(
            word_text=token,
            start_seconds=index * 0.3,
            end_seconds=index * 0.3 + 0.25,
            probability=probability,
            uncertain=probability < 0.60,
        )
        for index, token in enumerate(text.split())
    )


_NOTE_TURNS: tuple[tuple[str, str], ...] = (
    ("My left knee is sore when I walk", SPEAKER_1),
    ("On examination the range of motion is limited", SPEAKER_2),
    ("The diagnosis is a mild knee sprain", SPEAKER_2),
    ("Please use an ice pack tonight", SPEAKER_2),
)


def _note_document(turns: tuple[tuple[str, str], ...] = _NOTE_TURNS) -> TranscriptDocument:
    return TranscriptDocument(
        session_id=_NOTE_SESSION_ID,
        created_at=datetime.now(UTC),
        model_name="mock",
        sample_rate=16_000,
        transcript_segments=tuple(
            TranscriptSegment(
                start_seconds=float(index * 10),
                end_seconds=float(index * 10 + 5),
                speaker=speaker,
                transcript_words=_note_words(text),
            )
            for index, (text, speaker) in enumerate(turns)
        ),
    )


def _note_result(clinician: str | None = SPEAKER_2) -> models.NoteGenerationResult:
    document = _note_document()
    config = _note_config()
    draft = compose_draft(
        document, config, ExtractiveNoteProvider(), clinician_speaker=clinician
    )
    return models.NoteGenerationResult(draft=draft, config=config, document=document)


def _low_confidence_result() -> tuple[models.NoteGenerationResult, str]:
    """A result whose transcript carries a low-`probability` word in a patient
    utterance that matches no cue — omitted from the note, but reachable in
    the transcript panel (Task 7.6)."""
    marked_word = "wobbly"
    words = (
        TranscriptWord(
            word_text="It", start_seconds=0.0, end_seconds=0.2, probability=0.95, uncertain=False
        ),
        TranscriptWord(
            word_text="felt", start_seconds=0.2, end_seconds=0.4, probability=0.95, uncertain=False
        ),
        TranscriptWord(
            word_text=marked_word,
            start_seconds=0.4,
            end_seconds=0.7,
            probability=0.30,
            uncertain=True,
        ),
    )
    document = TranscriptDocument(
        session_id=_NOTE_SESSION_ID,
        created_at=datetime.now(UTC),
        model_name="mock",
        sample_rate=16_000,
        transcript_segments=(
            TranscriptSegment(
                start_seconds=0.0, end_seconds=1.0, speaker=SPEAKER_1, transcript_words=words
            ),
            TranscriptSegment(
                start_seconds=10.0,
                end_seconds=15.0,
                speaker=SPEAKER_2,
                transcript_words=_note_words("On examination the range of motion is limited"),
            ),
        ),
    )
    config = _note_config()
    draft = compose_draft(document, config, ExtractiveNoteProvider(), clinician_speaker=SPEAKER_2)
    return models.NoteGenerationResult(draft=draft, config=config, document=document), marked_word


# ---------------------------------------------------------------------------
# models view-logic (Task 7.4).
# ---------------------------------------------------------------------------


class TestNoteViewModels:
    def test_provenance_labels_distinguish_sources(self) -> None:
        assert models.provenance_label("transcript") == "from transcript"
        assert "clinician-authored" in models.provenance_label("autofill")
        assert "clinician-authored" in models.provenance_label("prefill")

    def test_summarise_warnings_splits_and_groups(self) -> None:
        result = _note_result()
        # Nothing confirmed: every proposal is pending -> unconfirmed_proposal.
        note = finalise_note(result.draft, [], result.document, result.config)
        summary = models.summarise_warnings(note.note_warnings)
        assert summary.blocking  # unconfirmed_proposal errors, grouped
        assert all(group.severity == "error" for group in summary.blocking)
        assert all(group.severity == "review" for group in summary.review)
        # Grouped by code, not one row per finding.
        codes = [group.code for group in summary.blocking]
        assert len(codes) == len(set(codes))

    def test_every_registered_warning_code_has_copy(self) -> None:
        # No fallback copy may be reachable in shipping: `_fallback_copy`
        # renders a raw code and no clear-path, which is exactly the
        # fictitious/absent-clear-path class rounds 35 and 45 both hit.
        assert set(models.WARNING_COPY) == set(NOTE_WARNING_SEVERITY)
        for code, severity in NOTE_WARNING_SEVERITY.items():
            copy = models.WARNING_COPY[code]
            assert copy.clear_hint.strip()
            # An `error` names the action it blocks; a `review` blocks nothing.
            assert (copy.blocks is not None) is (severity == "error")

    def test_clear_hints_name_no_unbuilt_surface(self) -> None:
        """Round 45 MED-002 regression pin.

        `mapping_drop`'s hint used to send the clinician to an "Unmapped
        content" heading — the round-2 MAPPED-OUTPUT target, which is Phase
        4's and exists nowhere in this app. The dropped section is rendered
        in the note body like any other populated canonical section, so the
        hint must describe the missing TEMPLATE FIELD, never a missing view.
        """
        for copy in models.WARNING_COPY.values():
            assert "unmapped content" not in copy.clear_hint.lower()
        hint = models.WARNING_COPY["mapping_drop"].clear_hint
        assert "shown in the note" in hint

    def test_complete_block_reason(self) -> None:
        assert models.complete_block_reason(models.NoteReviewState()) is None
        assert models.complete_block_reason(
            models.NoteReviewState(generating=True)
        ) is not None
        assert models.complete_block_reason(
            models.NoteReviewState(has_note=True, unconfirmed_proposals=1)
        ) is not None
        assert models.complete_block_reason(
            models.NoteReviewState(has_note=True, blocking_errors=1)
        ) is not None
        assert models.complete_block_reason(
            models.NoteReviewState(has_note=True, note_saved=False)
        ) is not None
        assert models.complete_block_reason(
            models.NoteReviewState(
                has_note=True, note_saved=True, unacknowledged_reviews=1
            )
        ) is not None
        assert models.complete_block_reason(
            models.NoteReviewState(has_note=True, note_saved=True)
        ) is None

    def test_config_report_lines(self) -> None:
        lines = models.config_report_lines(_note_config(), "clinic-a")
        joined = "\n".join(lines)
        assert "Autofill rules: 1" in joined
        assert "Prefill regions: 1" in joined
        assert "Clinic A" in joined

    def test_render_proposal_reuses_format_timestamp(self) -> None:
        result = _note_result()
        autofill = next(
            p for p in result.draft.note_proposals if p.provenance == "autofill"
        )
        rendered = models.render_proposal(autofill)
        assert rendered.excerpt == autofill.note_excerpt
        # Attribution reuses format_timestamp (mm:ss) for the trigger time.
        assert ":" in rendered.attribution

    def test_speaker_quotations_one_per_cluster(self) -> None:
        quotes = models.speaker_quotations(_note_document())
        assert set(quotes) == {SPEAKER_1, SPEAKER_2}
        assert quotes[SPEAKER_1].startswith("My left knee")


# ---------------------------------------------------------------------------
# Note tab (Task 7.1 + 7.6).
# ---------------------------------------------------------------------------


class TestNoteScreen:
    def _screen(
        self, *, copy_enabled: bool = False, result: models.NoteGenerationResult | None = None
    ) -> tuple[Any, dict[str, list[Any]]]:
        from scribe_desktop.ui.note import NoteScreen

        record: dict[str, list[Any]] = {
            "saved": [],
            "abandoned": [],
            "cancelled": [],
            "states": [],
        }
        screen = NoteScreen()
        screen.begin_review(
            result if result is not None else _note_result(),
            copy_enabled=copy_enabled,
            on_save=lambda note: record["saved"].append(note),
            on_abandon=lambda: record["abandoned"].append(True),
            on_cancel=lambda: record["cancelled"].append(True),
            on_state_changed=lambda state: record["states"].append(state),
            template_profile_id="clinic-a",
        )
        return screen, record

    def _confirm_all(self, screen: Any) -> None:
        for proposal in screen._draft.note_proposals:
            screen.confirm_proposal(proposal.proposal_id)

    def test_consent_manual_reminder_is_always_rendered(self, qapp: Any) -> None:
        """Task 7.7 / round 45 MED-001 — the consent Critical Constraint's
        third clause: "the note view renders it as a manual reminder only".

        The reminder states what the app NEVER does, so it must survive
        `clear()` and be readable on an empty tab — it cannot be conditional
        on a loaded note, and it must never become an acknowledgeable
        warning (that would make it suppressible).
        """
        from scribe_desktop.ui.note import NoteScreen

        text = models.CONSENT_MANUAL_REMINDER
        assert "Informed Consent" in text
        # Round 47 PR-MED-001 semantic pin. The copy must name the ATTESTATION
        # CHECKBOX (what is structurally unreachable is an
        # `attestation_checkbox` target, not all consent-related note text —
        # `DEFAULT_SECTION_CUES["consent"]` legitimately routes consent speech
        # into the rendered `consent` section), and it must carry the FULL
        # predicate the checkbox asserts. Reducing it to consent-alone invites
        # the clinician to attest more than the reminder asked them to verify.
        assert "attestation" in text.lower()
        lowered = text.lower()
        for clause in ("working diagnosis", "benefits", "risks", "consent was gained"):
            assert clause in lowered, clause

        empty = NoteScreen()  # no note ever loaded
        assert empty.consent_reminder_label.text() == text

        screen, _ = self._screen()
        assert screen.consent_reminder_label.text() == text
        screen.clear()
        assert screen.consent_reminder_label.text() == text

        # A standing statement, never a warning: no code, no acknowledgement.
        assert "consent" not in NOTE_WARNING_SEVERITY
        assert not any(
            "informed consent" in copy.clear_hint.lower()
            for copy in models.WARNING_COPY.values()
        )

    def test_sections_render_in_canonical_order(self, qapp: Any) -> None:
        screen, _record = self._screen()
        note = screen.current_note()
        assert note is not None
        keys = [section.section_key for section in note.note_sections]
        indexed = [CANONICAL_SECTION_KEYS.index(key) for key in keys]
        assert indexed == sorted(indexed)  # canonical order
        screen.deleteLater()

    def test_provenance_visible_after_confirming(self, qapp: Any) -> None:
        screen, _record = self._screen()
        self._confirm_all(screen)
        body = screen.note_body.toPlainText()
        assert "from transcript" in body
        assert "autofill (clinician-authored)" in body
        assert "prefill (clinician-authored)" in body
        screen.deleteLater()

    def test_proposals_show_exact_text_and_confirm_inserts(self, qapp: Any) -> None:
        screen, _record = self._screen()
        autofill = next(
            p for p in screen._draft.note_proposals if p.provenance == "autofill"
        )
        assert autofill.note_excerpt not in screen.note_body.toPlainText()
        screen.confirm_proposal(autofill.proposal_id)
        assert autofill.note_excerpt in screen.note_body.toPlainText()
        screen.deleteLater()

    def test_unconfirmed_proposals_block_saving(self, qapp: Any) -> None:
        screen, _record = self._screen()
        # Pending proposals -> unconfirmed_proposal blocking error -> Save off.
        assert not screen.save_button.isEnabled()
        state = screen.current_review_state()
        assert state.unconfirmed_proposals > 0
        assert state.blocking_errors > 0
        screen.deleteLater()

    def test_confirming_all_then_acknowledge_enables_save(self, qapp: Any) -> None:
        screen, _record = self._screen()
        self._confirm_all(screen)
        state = screen.current_review_state()
        assert state.unconfirmed_proposals == 0
        assert state.blocking_errors == 0
        # Confirmed clinician-authored assertions draw the unsuppressible
        # clinician_asserted review warnings.
        assert state.unacknowledged_reviews > 0
        # Round 36 PR-MED-002: Save requires acknowledgement (plan Flow 1), so
        # it stays DISABLED until every review warning is acknowledged.
        assert not screen.save_button.isEnabled()
        screen._acknowledge_all()
        assert screen.save_button.isEnabled()
        screen.deleteLater()

    def test_decline_keeps_proposal_out_of_note(self, qapp: Any) -> None:
        screen, _record = self._screen()
        autofill = next(
            p for p in screen._draft.note_proposals if p.provenance == "autofill"
        )
        screen.decline_proposal(autofill.proposal_id)
        assert autofill.note_excerpt not in screen.note_body.toPlainText()
        screen.deleteLater()

    def test_retract_confirmed_assertion_refinalises(self, qapp: Any) -> None:
        screen, _record = self._screen()
        autofill = next(
            p for p in screen._draft.note_proposals if p.provenance == "autofill"
        )
        screen.confirm_proposal(autofill.proposal_id)
        assert autofill.note_excerpt in screen.note_body.toPlainText()
        screen.retract_proposal(autofill.proposal_id)
        assert autofill.note_excerpt not in screen.note_body.toPlainText()
        screen.deleteLater()

    def test_acknowledge_all_clears_unacknowledged(self, qapp: Any) -> None:
        screen, _record = self._screen()
        self._confirm_all(screen)
        assert screen.current_review_state().unacknowledged_reviews > 0
        screen._acknowledge_all()
        assert screen.current_review_state().unacknowledged_reviews == 0
        screen.deleteLater()

    def test_save_calls_callback_when_ratified(self, qapp: Any) -> None:
        screen, record = self._screen()
        self._confirm_all(screen)
        screen._acknowledge_all()  # Save now requires acknowledgement (Flow 1)
        screen.save()
        assert len(record["saved"]) == 1
        assert isinstance(record["saved"][0], GeneratedNote)
        assert not screen.save_button.isEnabled()  # already saved
        screen.deleteLater()

    def test_save_requires_acknowledgement(self, qapp: Any) -> None:
        """Round 36 PR-MED-002: a note cannot be saved (finalised) while a
        review warning is unacknowledged — the plan's Flow 1 precondition, so
        a committed note.enc is always Complete-ready."""
        screen, record = self._screen()
        self._confirm_all(screen)
        assert screen.current_review_state().unacknowledged_reviews > 0
        assert not screen.save_button.isEnabled()
        screen.save()  # click-time guard also refuses
        assert record["saved"] == []
        screen.deleteLater()

    def test_delete_note_and_complete_calls_abandon(self, qapp: Any) -> None:
        screen, record = self._screen()
        assert screen.abandon_button.isEnabled()
        screen.abandon()
        assert record["abandoned"] == [True]
        assert screen.current_note() is None  # cleared
        screen.deleteLater()

    def test_cancel_review_calls_callback_and_clears(self, qapp: Any) -> None:
        """Round 35 PR-MED-003: the non-destructive escape invokes on_cancel
        and clears the Note-tab plaintext."""
        screen, record = self._screen()
        assert screen.cancel_button.isEnabled()  # draft under review, not saved
        screen.cancel_review()
        assert record["cancelled"] == [True]
        assert record["abandoned"] == []  # NOT the destructive path
        assert screen.current_note() is None  # cleared
        screen.deleteLater()

    def test_cancel_disabled_after_save(self, qapp: Any) -> None:
        screen, _record = self._screen()
        self._confirm_all(screen)
        screen._acknowledge_all()  # Save requires acknowledgement (Flow 1)
        screen.save()
        assert not screen.cancel_button.isEnabled()  # cancel is a pre-commit escape
        screen.deleteLater()

    def test_copy_disabled_when_gate_not_passed(self, qapp: Any) -> None:
        from PySide6.QtCore import Qt

        screen, _record = self._screen(copy_enabled=False)
        assert not screen.copy_button.isEnabled()
        assert (
            screen.note_body.textInteractionFlags() == Qt.TextInteractionFlag.NoTextInteraction
        )
        screen.deleteLater()

    def test_copy_enabled_only_for_a_ratified_note(self, qapp: Any) -> None:
        """Round 35 PR-MED-002: the 9.1 gate is necessary but NOT sufficient —
        copy shares Complete's ratification bar. An unresolved-error / pending
        / unsaved note is never copyable, even with the gate on."""
        from PySide6.QtCore import Qt

        screen, _record = self._screen(copy_enabled=True)
        # Gate on, but proposals pending -> copy stays disabled + display-only.
        assert not screen.copy_button.isEnabled()
        assert (
            screen.note_body.textInteractionFlags() == Qt.TextInteractionFlag.NoTextInteraction
        )
        # Ratify the note: confirm all -> acknowledge all -> save.
        self._confirm_all(screen)
        assert not screen.copy_button.isEnabled()  # unacknowledged reviews still block
        screen._acknowledge_all()
        assert not screen.copy_button.isEnabled()  # not yet saved
        screen.save()
        assert screen.copy_button.isEnabled()  # fully ratified
        flags = screen.note_body.textInteractionFlags()
        assert flags & Qt.TextInteractionFlag.TextSelectableByMouse
        screen.deleteLater()

    def test_default_copy_binding_ships_disabled(self, qapp: Any) -> None:
        # The recorded 9.1 decision (COPY_TO_CLINIKO_ENABLED) is False.
        assert models.COPY_TO_CLINIKO_ENABLED is False
        from scribe_desktop.ui.note import NoteScreen

        screen = NoteScreen()
        screen.begin_review(
            _note_result(),
            on_save=lambda note: None,
            on_abandon=lambda: None,
        )
        assert not screen.copy_button.isEnabled()
        screen.deleteLater()

    def test_cleared_on_close(self, qapp: Any) -> None:
        screen, _record = self._screen()
        assert screen.note_body.toPlainText() != ""
        screen.clear()
        assert screen.note_body.toPlainText() == ""
        assert screen.transcript_view.toPlainText() == ""
        assert screen.current_note() is None
        screen.deleteLater()

    def test_transcript_visible_beside_note(self, qapp: Any) -> None:
        """Task 7.6: the full uncertainty-marked transcript is beside the note
        and is display-only."""
        from PySide6.QtCore import Qt

        screen, _record = self._screen()
        text = screen.transcript_view.toPlainText()
        assert "My left knee is sore" in text
        assert (
            screen.transcript_view.textInteractionFlags()
            == Qt.TextInteractionFlag.NoTextInteraction
        )
        screen.deleteLater()

    def test_low_confidence_word_reachable_though_omitted(self, qapp: Any) -> None:
        """Task 7.6 Done-when: a low-`probability` word cue routing omitted is
        still REACHABLE in the transcript panel at review time."""
        result, marked = _low_confidence_result()
        screen, _record = self._screen(result=result)
        note = screen.current_note()
        assert note is not None
        # The word is not in the note (patient utterance, no cue)...
        assert marked not in screen.note_body.toPlainText()
        # ...but it is reachable in the transcript panel, marked uncertain.
        assert f"[{marked}?]" in screen.transcript_view.toPlainText()
        screen.deleteLater()

    def test_clinician_owned_sections_empty_without_confirmed_role(self, qapp: Any) -> None:
        """Task 7.5 Done-when: a note composed without a confirmed role leaves
        clinician-owned sections empty — the diagnosis utterance never lands."""
        screen, _record = self._screen(result=_note_result(clinician=None))
        note = screen.current_note()
        assert note is not None
        present = {section.section_key for section in note.note_sections}
        assert not (present & CLINICIAN_OWNED_SECTIONS)
        screen.deleteLater()


# ---------------------------------------------------------------------------
# Transcript screen generation controls (Task 7.2 + 7.5).
# ---------------------------------------------------------------------------


class TestTranscriptGeneration:
    def _screen(self, controller: FakeController) -> tuple[Any, models.NoteGenerationResult]:
        from scribe_desktop.ui.transcript import TranscriptScreen

        result = _note_result()

        def factory(**_kwargs: Any) -> Callable[[Path, Any], models.NoteGenerationResult]:
            return lambda _directory, _crypto: result

        screen = TranscriptScreen(
            controller, note_generator_factory=factory, config_loader=_note_config
        )
        screen.show_document(
            _note_document(),
            on_complete=controller.complete,
            on_discard=controller.discard,
            can_generate=True,
        )
        return screen, result

    def test_generate_disabled_until_role_and_profile_confirmed(self, qapp: Any) -> None:
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, _result = self._screen(controller)
        assert not screen.generate_button.isEnabled()
        screen.set_role(SPEAKER_2)
        assert not screen.generate_button.isEnabled()  # profile still unconfirmed
        screen.set_profile("clinic-a")
        assert screen.generate_button.isEnabled()
        screen.deleteLater()

    def test_generate_composes_draft_on_a_task_thread(self, qapp: Any) -> None:
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, result = self._screen(controller)
        drafts: list[Any] = []
        screen.draft_ready.connect(drafts.append)
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert screen.is_busy  # lease held from the start of generation
        assert _process_until(qapp, lambda: bool(drafts))
        assert drafts[0] is result
        assert ("begin_generation",) in controller.calls
        assert ("with_generation_custody",) in controller.calls
        assert screen.is_busy  # still held through review
        screen.deleteLater()

    def test_complete_refused_while_generating(self, qapp: Any) -> None:
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, _result = self._screen(controller)
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert not screen.complete_button.isEnabled()
        assert not screen.discard_button.isEnabled()
        screen.deleteLater()

    def test_complete_gated_on_note_review_state(self, qapp: Any) -> None:
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, _result = self._screen(controller)
        # No generation: Complete is available (transcript-only complete).
        assert screen.complete_button.isEnabled()
        screen.set_note_review_state(
            models.NoteReviewState(has_note=True, unconfirmed_proposals=1)
        )
        assert not screen.complete_button.isEnabled()
        screen.set_note_review_state(
            models.NoteReviewState(has_note=True, note_saved=True)
        )
        assert screen.complete_button.isEnabled()
        screen.deleteLater()

    def test_save_note_runs_write_on_gui_thread_and_releases_lease(
        self, qapp: Any, monkeypatch: Any
    ) -> None:
        import threading

        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, result = self._screen(controller)
        writes: list[str] = []

        def fake_write(directory: Path, crypto: Any, note: Any, config: Any) -> Path:
            writes.append(threading.current_thread().name)
            return directory / "note.enc"

        monkeypatch.setattr("scribe_desktop.ui.transcript.write_note", fake_write)
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert _process_until(qapp, lambda: screen._generation_result is not None)
        note = finalise_note(
            result.draft,
            [
                ProposalResolution(
                    shown_text_digest=text_digest(p.note_excerpt),
                    confirmation=ConfirmationDecision(
                        proposal_id=p.proposal_id,
                        note_confirmation="declined",
                        decided_at=datetime.now(UTC),
                    ),
                )
                for p in result.draft.note_proposals
            ],
            result.document,
            result.config,
        )
        screen.save_note(note)
        assert writes == [threading.current_thread().name]  # GUI (calling) thread
        assert ("with_generation_custody",) in controller.calls
        assert not screen.is_busy  # lease released after the write
        assert ("end_generation",) in controller.calls
        assert screen._note_committed  # round 36: note.enc is on disk
        screen.deleteLater()

    def test_abandon_note_and_complete_without_one(self, qapp: Any) -> None:
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, _result = self._screen(controller)
        closed: list[str] = []
        screen.closed.connect(closed.append)
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert _process_until(qapp, lambda: screen._generation_result is not None)
        screen.abandon_note_and_complete()
        assert ("complete_without_note",) in controller.calls
        assert not screen.is_busy  # lease released AFTER completion succeeded
        assert closed == ["completed"]
        screen.deleteLater()

    def test_abandon_failure_keeps_the_lease(self, qapp: Any) -> None:
        """Round 35 PR-MED-001: a completion failure must leave the lease and
        review HELD (never an unleased QUEUED session mid-review)."""
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, _result = self._screen(controller)
        closed: list[str] = []
        screen.closed.connect(closed.append)
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert _process_until(qapp, lambda: screen._generation_result is not None)
        controller.generation_error = SessionActivityError("complete failed")
        with pytest.raises(SessionActivityError):
            screen.abandon_note_and_complete()
        assert screen.is_busy  # lease STILL held
        assert closed == []  # not completed; recovery stays blocked
        screen.deleteLater()

    def test_cancel_note_review_is_non_destructive(self, qapp: Any) -> None:
        """Round 35 PR-MED-003: cancel releases the lease and drops the draft
        WITHOUT completing/discarding/deleting — the transcript, session key,
        and Generate stay available for a fresh generation."""
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, _result = self._screen(controller)
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert _process_until(qapp, lambda: screen._generation_result is not None)
        assert screen.is_busy
        screen.cancel_note_review()
        assert not screen.is_busy  # lease released
        assert screen._generation_result is None
        # Non-destructive: no completion/discard/delete happened.
        assert ("complete_without_note",) not in controller.calls
        assert ("complete",) not in controller.calls
        assert ("discard",) not in controller.calls
        assert ("end_generation",) in controller.calls  # deliberate lease release
        # Generate is available again (role + profile still confirmed).
        assert screen.generate_button.isEnabled()
        screen.deleteLater()

    def test_committed_note_survives_cancel_of_replacement(self, qapp: Any) -> None:
        """Round 36 PR-MED-002: after Save A, generating then canceling B must
        NOT forget A — `_note_committed` stays True, so the Complete gate's
        has_note agrees with disk and A (ratified at Save) stays completable."""
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        screen, _result = self._screen(controller)
        # Simulate a committed note.enc A (a prior successful save).
        screen._note_committed = True
        # Regenerate a replacement B, then cancel it.
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        screen.generate()
        assert _process_until(qapp, lambda: screen._generation_result is not None)
        screen.cancel_note_review()
        assert screen._note_committed  # A is NOT forgotten by cancel
        assert screen.complete_button.isEnabled()  # committed, ratified A stays completable
        screen.deleteLater()

    def test_recovered_transcript_has_no_generation_controls(self, qapp: Any) -> None:
        controller = FakeController()
        screen, _result = self._screen(controller)
        # Re-show as a recovered transcript (no generation).
        screen.show_document(
            _note_document(),
            on_complete=lambda: None,
            on_discard=lambda: None,
            can_generate=False,
        )
        assert not screen.generate_box.isVisibleTo(screen)
        screen.deleteLater()

    def test_generate_refused_while_recovery_in_flight(self, qapp: Any) -> None:
        """Round 33 MED-001: a note generation must NOT start while a recovery
        resume is in flight (mutual exclusion — otherwise the resume's
        completion would release the lease mid-generation and swap the view).
        """
        from scribe_desktop.ui.transcript import TranscriptScreen

        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        result = _note_result()
        busy = [True]
        screen = TranscriptScreen(
            controller,
            note_generator_factory=lambda **_k: (lambda _d, _c: result),
            config_loader=_note_config,
            recovery_busy_provider=lambda: busy[0],
        )
        screen.show_document(
            _note_document(),
            on_complete=controller.complete,
            on_discard=controller.discard,
            can_generate=True,
        )
        screen.set_role(SPEAKER_2)
        screen.set_profile("clinic-a")
        # Recovery busy -> Generate disabled AND the click-time guard refuses.
        assert not screen.generate_button.isEnabled()
        screen.generate()
        assert screen._lease is None
        assert ("begin_generation",) not in controller.calls
        # Recovery finishes -> generation is available again.
        busy[0] = False
        screen._update_controls()
        assert screen.generate_button.isEnabled()
        screen.deleteLater()


# ---------------------------------------------------------------------------
# Main window note wiring (Task 7.3).
# ---------------------------------------------------------------------------


class TestNoteWiring:
    def _window(self, tmp_path: Path, controller: FakeController) -> Any:
        from scribe_desktop.ui.main_window import MainWindow

        return MainWindow(
            controller,
            FakeBackend(),
            sessions_root=tmp_path,
            benchmark_runner=list,
            recovery_runner=lambda d: pytest.fail("not called"),
        )

    def test_draft_ready_routes_to_note_tab(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        window = self._window(tmp_path, controller)
        window._on_draft_ready(_note_result())
        assert window.note_screen.current_note() is not None
        assert window.tabs.currentWidget() is window.note_screen
        window.close()

    def test_new_live_transcript_clears_stale_note(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        window = self._window(tmp_path, controller)
        window._on_draft_ready(_note_result())
        assert window.note_screen.current_note() is not None
        window.session_screen.transcript_ready.emit(_note_document())
        qapp.processEvents()
        assert window.note_screen.current_note() is None  # cleared
        window.close()

    def test_generation_active_blocks_recovery(self, qapp: Any, tmp_path: Path) -> None:
        controller = FakeController()
        window = self._window(tmp_path, controller)
        window._on_generation_active(True)
        assert window.recovery_screen._generation_blocked is True
        window._on_generation_active(False)
        assert window.recovery_screen._generation_blocked is False
        window.close()

    def test_new_generation_invalidates_stale_note_tab(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 36 PR-MED-001: a new generation synchronously clears the stale
        (post-Save) Note tab, so its delete-and-complete action can never route
        through the new generation's lease."""
        controller = FakeController()
        controller.state_value = SessionState.QUEUED
        window = self._window(tmp_path, controller)
        window._on_draft_ready(_note_result())
        assert window.note_screen.current_note() is not None
        assert window.note_screen.abandon_button.isEnabled()
        # A new generation starts -> the stale Note tab is invalidated.
        window._on_generation_active(True)
        assert window.note_screen.current_note() is None  # cleared
        assert not window.note_screen.abandon_button.isEnabled()  # no stale action
        window.close()

    def test_close_refused_while_note_under_review(self, qapp: Any, tmp_path: Path) -> None:
        from PySide6.QtGui import QCloseEvent

        controller = FakeController()
        window = self._window(tmp_path, controller)
        window._on_draft_ready(_note_result())  # note under review, not saved
        assert window.note_screen.is_busy
        event = QCloseEvent()
        window.closeEvent(event)
        assert not event.isAccepted()
        window.note_screen.clear()
        event2 = QCloseEvent()
        window.closeEvent(event2)
        assert event2.isAccepted()
