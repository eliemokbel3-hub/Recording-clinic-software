"""Practitioner-profile plan Phase 1 Task 1.3: ``enrolment`` and the D15
controller activity.

``record_enrolment`` is driven with ``MockCaptureBackend`` from a worker
thread (blocks are fed from the test thread exactly as a device thread
would deliver them) and a level-based VAD stub; ``enrol`` with
``MockSpeakerEmbedder``. The "no PCM persisted" constraint is pinned with a
temporary ``LOCALAPPDATA``: after every path the only thing that may exist
under it is nothing at all. The controller's ``begin_enrolment`` /
``end_enrolment`` are tested in BOTH start orders and against every refusal
D15 names; the microphone screen's poll tick during enrolment is in
``test_ui_screens.py``.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from scribe_desktop import enrolment as enrolment_mod
from scribe_desktop.audio_capture import (
    AudioDevice,
    MockCaptureBackend,
    pcm16_rms_level,
)
from scribe_desktop.benchmark import apply_offline_env
from scribe_desktop.enrolment import (
    EnrolmentCancelledError,
    EnrolmentCaptureError,
    EnrolmentError,
    EnrolmentProgress,
    EnrolmentTooShortError,
    enrol,
    record_enrolment,
)
from scribe_desktop.session import (
    EnrolmentLease,
    SessionActivityError,
    SessionController,
    SessionControllerError,
    SessionState,
)
from scribe_desktop.speaker_embedding import MockSpeakerEmbedder
from scribe_desktop.speech import FRAME_BYTES, segment_pcm

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI custody is Windows-only")

BLOCK_BYTES = 3200  # 100 ms of 16 kHz PCM16, the backend's block size


@pytest.fixture(autouse=True)
def _offline() -> None:
    apply_offline_env()


def _loud(seconds: float) -> bytes:
    return b"\x00\x40" * int(seconds * 16_000)


def _silent(seconds: float) -> bytes:
    return b"\x00\x00" * int(seconds * 16_000)


class _LevelVad:
    """A frame-probability stub: speech iff the frame is not near-silent.
    Resettable like ``SileroVad`` so the reset contract can be observed."""

    def __init__(self) -> None:
        self.resets = 0
        self.frames = 0

    def reset(self) -> None:
        self.resets += 1

    def frame_probability(self, frame: bytes) -> float:
        assert len(frame) == FRAME_BYTES
        self.frames += 1
        return 0.95 if pcm16_rms_level(frame) > 0.01 else 0.0


def _blocks(pcm: bytes) -> list[bytes]:
    return [pcm[i : i + BLOCK_BYTES] for i in range(0, len(pcm), BLOCK_BYTES)]


class _Capture:
    """Runs ``record_enrolment`` on a worker thread and feeds it blocks from
    the test thread while its stream is open."""

    def __init__(self, backend: MockCaptureBackend, vad: _LevelVad, **kw: Any) -> None:
        self.backend = backend
        self.result: bytes | None = None
        self.error: BaseException | None = None
        self.progress: list[EnrolmentProgress] = []
        kw.setdefault("on_progress", self.progress.append)

        def run() -> None:
            try:
                self.result = record_enrolment(
                    backend, 0, frame_probability=vad.frame_probability, **kw
                )
            except BaseException as exc:  # noqa: BLE001 - re-raised by the test
                self.error = exc

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        deadline = time.monotonic() + 5.0
        while not backend.stream_open and self.thread.is_alive():
            if time.monotonic() > deadline:
                raise AssertionError("enrolment never opened the stream")
            time.sleep(0.005)

    def feed(self, pcm: bytes) -> int:
        fed = 0
        for block in _blocks(pcm):
            if not self.backend.stream_open:
                break
            self.backend.feed(block)
            fed += len(block)
        return fed

    def join(self) -> None:
        self.thread.join(timeout=10.0)
        assert not self.thread.is_alive(), "enrolment did not finish"


def _backend() -> MockCaptureBackend:
    return MockCaptureBackend([AudioDevice(device_id=0, name="Mock Microphone", is_default=True)])


# --- record_enrolment --------------------------------------------------------------


class TestRecordEnrolment:
    def test_stops_at_the_speech_target_and_releases_the_device(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        backend = _backend()
        vad = _LevelVad()
        capture = _Capture(backend, vad, target_speech_seconds=1.0, max_seconds=5.0)
        audio = _loud(2.0)
        capture.feed(audio)
        capture.join()
        assert capture.error is None and capture.result is not None
        pcm = capture.result
        assert len(pcm) >= 16_000 * 2  # at least the target second of speech
        assert audio.startswith(pcm)  # exactly what the device delivered, in order
        assert not backend.stream_open  # released on the way out
        assert capture.progress and capture.progress[-1].speech_seconds >= 1.0
        assert capture.progress[-1].captured_seconds >= capture.progress[-1].speech_seconds
        assert 0.0 < capture.progress[-1].level <= 1.0
        assert vad.resets == 2  # before the capture and in the finally
        assert list(tmp_path.rglob("*")) == []  # nothing persisted anywhere

    def test_too_little_speech_at_the_cap_is_typed_and_persists_nothing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        backend = _backend()
        capture = _Capture(backend, _LevelVad(), target_speech_seconds=1.0, max_seconds=1.5)
        capture.feed(_silent(0.5) + _loud(0.3) + _silent(1.0))
        capture.join()
        assert isinstance(capture.error, EnrolmentTooShortError)
        assert "0.3 s of speech" in str(capture.error) and "1 s of speech" in str(capture.error)
        assert not backend.stream_open
        assert list(tmp_path.rglob("*")) == []

    def test_device_loss_is_a_capture_error(self) -> None:
        backend = _backend()
        capture = _Capture(backend, _LevelVad(), target_speech_seconds=1.0, max_seconds=5.0)
        capture.feed(_loud(0.3))
        backend.fail()
        capture.join()
        assert isinstance(capture.error, EnrolmentCaptureError)
        assert "device lost" in str(capture.error)
        assert not backend.stream_open

    def test_open_failure_is_a_capture_error(self) -> None:
        backend = _backend()
        with pytest.raises(EnrolmentCaptureError, match="could not open"):
            record_enrolment(backend, 99, frame_probability=_LevelVad().frame_probability)

    def test_cancellation(self) -> None:
        backend = _backend()
        stop = threading.Event()
        capture = _Capture(
            backend,
            _LevelVad(),
            target_speech_seconds=1.0,
            max_seconds=5.0,
            should_stop=stop.is_set,
        )
        capture.feed(_loud(0.2))
        stop.set()
        capture.feed(_loud(0.1))  # one more block wakes the loop
        capture.join()
        assert isinstance(capture.error, EnrolmentCancelledError)
        assert not backend.stream_open

    def test_cancellation_requested_by_the_target_reaching_progress_callback(self) -> None:
        """Peer round 15 PR-MED-020: ``should_stop`` set synchronously from
        the progress update that reaches the target must be honoured — the
        block is not accepted, no PCM is returned."""
        backend = _backend()
        vad = _LevelVad()
        stop = threading.Event()

        def on_progress(progress: EnrolmentProgress) -> None:
            if progress.speech_seconds >= 0.1:
                stop.set()

        capture = _Capture(
            backend,
            vad,
            target_speech_seconds=0.1,
            max_seconds=5.0,
            on_progress=on_progress,
            should_stop=stop.is_set,
        )
        capture.feed(_loud(0.3))
        capture.join()
        assert capture.result is None
        assert isinstance(capture.error, EnrolmentCancelledError)
        assert not backend.stream_open
        assert vad.resets == 2  # reset before the capture and in the finally

    def test_cancellation_arriving_during_shutdown_still_cancels(self) -> None:
        """A Cancel that lands while the stream is being stopped — after the
        in-loop polls, before the return — is seen by the post-shutdown poll."""
        from scribe_desktop.audio_capture import CaptureStream

        backend = _backend()
        vad = _LevelVad()
        stop = threading.Event()

        class _CancelOnStop:
            def __init__(self, inner: CaptureStream) -> None:
                self._inner = inner

            def stop(self) -> None:
                stop.set()
                self._inner.stop()

        real_open = backend.open_stream

        def _open(device_id: int, on_block: Any, on_error: Any) -> Any:
            return _CancelOnStop(real_open(device_id, on_block, on_error))

        backend.open_stream = _open  # type: ignore[method-assign]
        capture = _Capture(
            backend, vad, target_speech_seconds=0.1, max_seconds=5.0, should_stop=stop.is_set
        )
        capture.feed(_loud(0.3))
        capture.join()
        assert capture.result is None
        assert isinstance(capture.error, EnrolmentCancelledError)
        assert not backend.stream_open
        assert vad.resets == 2

    def test_a_silent_stream_times_out(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(enrolment_mod, "_BLOCK_TIMEOUT_S", 0.05)
        backend = _backend()
        capture = _Capture(backend, _LevelVad(), target_speech_seconds=1.0, max_seconds=5.0)
        capture.join()
        assert isinstance(capture.error, EnrolmentCaptureError)
        assert "no audio arrived" in str(capture.error)
        assert not backend.stream_open

    def test_queue_overflow_is_a_capture_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(enrolment_mod, "_QUEUE_MAX_BLOCKS", 2)
        backend = _backend()
        gate = threading.Event()

        class _SlowVad(_LevelVad):
            def frame_probability(self, frame: bytes) -> float:
                gate.wait(timeout=5.0)
                return super().frame_probability(frame)

        capture = _Capture(backend, _SlowVad(), target_speech_seconds=5.0, max_seconds=10.0)
        for _ in range(6):  # far more than the bounded queue while the consumer is stalled
            if backend.stream_open:
                backend.feed(_loud(0.1))
        gate.set()
        capture.join()
        assert isinstance(capture.error, EnrolmentCaptureError)
        assert "overflow" in str(capture.error)

    def test_failure_reported_behind_the_target_block_still_fails(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Peer round 14 PR-MED-019: the block that reaches the target is
        delivered, THEN the backend reports the failure (the real backend's
        block-then-status ordering). The failure item sits behind the block in
        the queue; success must not be returned over it."""
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        backend = _backend()
        gate = threading.Event()

        class _GatedVad(_LevelVad):
            def frame_probability(self, frame: bytes) -> float:
                gate.wait(timeout=5.0)
                return super().frame_probability(frame)

        capture = _Capture(backend, _GatedVad(), target_speech_seconds=0.1, max_seconds=5.0)
        backend.feed(_loud(0.2))  # this one block alone reaches the target
        backend.fail()  # ...and the device reports its failure right behind it
        gate.set()
        capture.join()
        assert capture.result is None
        assert isinstance(capture.error, EnrolmentCaptureError)
        assert "device lost" in str(capture.error)
        assert not backend.stream_open
        assert list(tmp_path.rglob("*")) == []

    def test_overflow_reported_behind_the_target_block_still_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The overflow producer converges on the same slot: dropped audio
        reported after the target block is a failure, not a success."""
        monkeypatch.setattr(enrolment_mod, "_QUEUE_MAX_BLOCKS", 1)
        backend = _backend()
        gate = threading.Event()

        class _GatedVad(_LevelVad):
            def frame_probability(self, frame: bytes) -> float:
                gate.wait(timeout=5.0)
                return super().frame_probability(frame)

        capture = _Capture(backend, _GatedVad(), target_speech_seconds=0.1, max_seconds=5.0)
        backend.feed(_loud(0.2))  # consumed and gated: alone it reaches the target
        for _ in range(3):  # the bounded queue (1) overflows on the second of these
            if backend.stream_open:
                backend.feed(_loud(0.1))
        gate.set()
        capture.join()
        assert capture.result is None
        assert isinstance(capture.error, EnrolmentCaptureError)
        assert "overflow" in str(capture.error)

    def test_failure_reported_during_shutdown_still_fails(self) -> None:
        """A failure the backend reports while the stream is being stopped —
        after the in-loop check, before the return — is caught by the
        post-shutdown check and wins over the successful return."""
        from scribe_desktop.audio_capture import CaptureOverflowError, CaptureStream

        backend = _backend()

        class _FailOnStop:
            def __init__(self, inner: CaptureStream, on_error: Any) -> None:
                self._inner = inner
                self._on_error = on_error

            def stop(self) -> None:
                self._on_error(CaptureOverflowError("frames dropped at shutdown"))
                self._inner.stop()

        real_open = backend.open_stream

        def _open(device_id: int, on_block: Any, on_error: Any) -> Any:
            return _FailOnStop(real_open(device_id, on_block, on_error), on_error)

        backend.open_stream = _open  # type: ignore[method-assign]
        capture = _Capture(backend, _LevelVad(), target_speech_seconds=0.1, max_seconds=5.0)
        capture.feed(_loud(0.3))
        capture.join()
        assert capture.result is None
        assert isinstance(capture.error, EnrolmentCaptureError)
        assert "dropped at shutdown" in str(capture.error)
        assert not backend.stream_open  # the inner stream was still released

    def test_parameter_validation(self) -> None:
        with pytest.raises(ValueError, match="target_speech_seconds"):
            record_enrolment(
                _backend(),
                0,
                frame_probability=_LevelVad().frame_probability,
                target_speech_seconds=10.0,
                max_seconds=5.0,
            )


# --- enrol -------------------------------------------------------------------------


class TestEnrol:
    def test_mean_of_segment_embeddings_normalised_with_speech_seconds(self) -> None:
        np = pytest.importorskip("numpy")
        vad = _LevelVad()
        pcm = _silent(0.6) + _loud(1.0) + _silent(0.8) + _loud(1.0) + _silent(0.6)
        # The segments the shipped segmenter finds, and an explicit vector per
        # segment, so the expected mean is exact: (1,0,0,0) and (0,1,0,0)
        # average to (0.5, 0.5, 0, 0), normalised to (1, 1, 0, 0) / sqrt 2.
        segments = segment_pcm([pcm], vad.frame_probability)
        assert len(segments) == 2
        pieces = [
            pcm[int(s.start_seconds * 16_000) * 2 : int(s.end_seconds * 16_000) * 2]
            for s in segments
        ]
        embedder = MockSpeakerEmbedder(
            {pieces[0]: (1.0, 0.0, 0.0, 0.0), pieces[1]: (0.0, 1.0, 0.0, 0.0)}
        )
        vector, speech_seconds = enrol(pcm, embedder, frame_probability=vad.frame_probability)
        assert vector.shape == (4,) and vector.dtype == np.float32
        assert np.allclose(vector, [2**-0.5, 2**-0.5, 0.0, 0.0], atol=1e-6)
        assert embedder.embedded_lengths == [len(pieces[0]), len(pieces[1])]
        assert np.isclose(speech_seconds, sum(len(p) for p in pieces) / 32_000)
        assert 1.8 <= speech_seconds <= 2.6  # two 1 s stretches plus the segmenter's padding

    def test_no_speech_is_too_short(self) -> None:
        pytest.importorskip("numpy")
        vad = _LevelVad()
        with pytest.raises(EnrolmentTooShortError, match="no speech"):
            enrol(_silent(2.0), MockSpeakerEmbedder(), frame_probability=vad.frame_probability)
        with pytest.raises(EnrolmentTooShortError, match="no audio"):
            enrol(b"", MockSpeakerEmbedder(), frame_probability=vad.frame_probability)

    def test_cancelling_vectors_are_refused(self) -> None:
        np = pytest.importorskip("numpy")

        class _Flip(MockSpeakerEmbedder):
            """+e1 for odd calls, -e1 for even calls — the SAME unit vector
            with alternating sign, so an even number of segments sums to
            exactly zero. (Flipping the digest-derived vector would not
            cancel: the two segments' bytes differ by their padding.)"""

            def embed(self, pcm16: bytes) -> Any:
                super().embed(pcm16)  # records the length like the real double
                sign = 1.0 if len(self.embedded_lengths) % 2 else -1.0
                return np.array([sign, 0.0, 0.0, 0.0], dtype=np.float32)

        vad = _LevelVad()
        pcm = _silent(0.6) + _loud(1.0) + _silent(0.8) + _loud(1.0) + _silent(0.6)
        assert len(segment_pcm([pcm], vad.frame_probability)) == 2  # an even count cancels
        embedder = _Flip()
        with pytest.raises(EnrolmentError, match="cancel"):
            enrol(pcm, embedder, frame_probability=vad.frame_probability)
        assert len(embedder.embedded_lengths) == 2


# --- the D15 controller activity ------------------------------------------------------


def _controller(tmp_path: Path) -> tuple[SessionController, MockCaptureBackend]:
    backend = MockCaptureBackend()
    return SessionController(backend, sessions_root=tmp_path), backend


class TestEnrolmentActivityTokens:
    def test_second_acquisition_refused_and_release_contract(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        assert not controller.enrolling
        lease = controller.begin_enrolment()
        assert isinstance(lease, EnrolmentLease) and controller.enrolling
        with pytest.raises(SessionActivityError, match="already in progress"):
            controller.begin_enrolment()
        controller.end_enrolment(lease)
        controller.end_enrolment(lease)  # idempotent
        assert not controller.enrolling
        second = controller.begin_enrolment()
        with pytest.raises(SessionControllerError, match="not held"):
            controller.end_enrolment(lease)
        assert controller.enrolling
        controller.end_enrolment(second)

    def test_registered_blocker_refuses_with_its_reason(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        busy = True
        controller.set_enrolment_blocker(lambda: "a benchmark is running" if busy else None)
        with pytest.raises(SessionActivityError, match="benchmark is running"):
            controller.begin_enrolment()
        busy = False
        controller.end_enrolment(controller.begin_enrolment())
        controller.set_enrolment_blocker(None)
        controller.end_enrolment(controller.begin_enrolment())

    def test_discard_reservation_refuses(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        with controller._lock:  # noqa: SLF001 - discard() is the single producer; deliberate injection
            controller._reserve_custody_locked("a" * 32)  # noqa: SLF001
        with pytest.raises(SessionActivityError, match="discard is in flight"):
            controller.begin_enrolment()
        with controller._lock:  # noqa: SLF001
            controller._release_custody_locked("a" * 32)  # noqa: SLF001
        controller.end_enrolment(controller.begin_enrolment())

    def test_resume_refused_while_enrolling_before_any_state_check(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        lease = controller.begin_enrolment()
        with pytest.raises(SessionActivityError, match="resume refused"):
            controller.resume()
        controller.end_enrolment(lease)
        with pytest.raises(SessionActivityError, match="no session"):
            controller.resume()


@windows_only
class TestEnrolmentActivityStartOrders:
    def test_enrolment_then_start(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        lease = controller.begin_enrolment()
        with pytest.raises(SessionActivityError, match="start refused"):
            controller.start(0)
        assert controller.state is SessionState.IDLE
        assert list(tmp_path.iterdir()) == []  # no session directory was created
        controller.end_enrolment(lease)
        assert controller.start(0).state is SessionState.RECORDING
        controller.discard()

    def test_start_then_enrolment(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        controller.start(0)
        with pytest.raises(SessionActivityError, match="recording"):
            controller.begin_enrolment()
        controller.pause()
        with pytest.raises(SessionActivityError, match="paused"):
            controller.begin_enrolment()
        controller.resume()
        controller.finish()
        assert controller.state is SessionState.PROCESSING  # transcription runs here
        with pytest.raises(SessionActivityError, match="processing"):
            controller.begin_enrolment()
        controller.mark_queued()
        lease = controller.begin_enrolment()  # a queued session holds no microphone
        assert controller.enrolling
        with pytest.raises(SessionActivityError, match="start refused"):
            controller.start(0)  # the queued session is NOT retired by the refusal
        assert controller.state is SessionState.QUEUED
        controller.end_enrolment(lease)
        controller.discard()
