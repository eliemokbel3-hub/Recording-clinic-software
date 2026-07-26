"""Step 3 audio-capture tests — mock backend ONLY (CI has no sound
hardware, and the module must be importable without PortAudio)."""

from __future__ import annotations

import importlib
import sys
import threading
import time
from typing import Any

import pytest

from scribe_desktop.audio_capture import (
    CHUNK_BYTES,
    AudioCaptureError,
    AudioDevice,
    CaptureOverflowError,
    CaptureWorker,
    DeviceLostError,
    MockCaptureBackend,
    pcm16_rms_level,
)


def _pcm(n_bytes: int, value: int = 1000) -> bytes:
    import struct

    sample = struct.pack("<h", value)
    return sample * (n_bytes // 2)


class _Sink:
    """Records chunks; optionally blocks or raises to order concurrency tests."""

    def __init__(self) -> None:
        self.chunks: list[bytes] = []
        self.raise_exc: Exception | None = None
        self.block_event: threading.Event | None = None
        self.entered = threading.Event()

    def __call__(self, data: bytes) -> int:
        self.entered.set()
        if self.block_event is not None:
            assert self.block_event.wait(timeout=10)
        if self.raise_exc is not None:
            raise self.raise_exc
        self.chunks.append(data)
        return len(self.chunks) - 1


class _Failures:
    def __init__(self) -> None:
        self.exceptions: list[Exception] = []
        self.seen = threading.Event()

    def __call__(self, exc: Exception) -> None:
        self.exceptions.append(exc)
        self.seen.set()


def _worker(
    backend: MockCaptureBackend, sink: _Sink, failures: _Failures, **kwargs: Any
) -> CaptureWorker:
    worker = CaptureWorker(backend, 0, sink, on_failure=failures, **kwargs)
    worker.start()
    return worker


class TestLazyImport:
    def test_module_importable_without_sounddevice(self) -> None:
        """Executor fact: sounddevice loads the PortAudio DLL at import time,
        so audio_capture must not import it at module scope."""
        saved_sd = sys.modules.pop("sounddevice", None)
        saved_mod = sys.modules.pop("scribe_desktop.audio_capture", None)

        class _Blocker:
            def find_module(self, fullname: str, path: object = None) -> object:
                return self if fullname == "sounddevice" else None

            def find_spec(self, fullname: str, path: object = None, target: object = None) -> None:
                if fullname == "sounddevice":
                    raise ImportError("sounddevice blocked for lazy-import test")
                return None

        blocker = _Blocker()
        sys.meta_path.insert(0, blocker)
        try:
            module = importlib.import_module("scribe_desktop.audio_capture")
            assert module.MockCaptureBackend().list_input_devices()
        finally:
            sys.meta_path.remove(blocker)
            if saved_sd is not None:
                sys.modules["sounddevice"] = saved_sd
            if saved_mod is not None:
                sys.modules["scribe_desktop.audio_capture"] = saved_mod


class TestDeviceEnumeration:
    def test_mock_lists_devices(self) -> None:
        devices = [AudioDevice(0, "Mic A", True), AudioDevice(3, "Mic B", False)]
        backend = MockCaptureBackend(devices)
        assert backend.list_input_devices() == devices

    def test_open_unknown_device_raises(self) -> None:
        backend = MockCaptureBackend()
        with pytest.raises(DeviceLostError):
            backend.open_stream(99, lambda b: None, lambda e: None)


class TestLevelMetering:
    def test_silence_is_zero(self) -> None:
        assert pcm16_rms_level(b"\x00" * 3200) == 0.0

    def test_full_scale_near_one(self) -> None:
        import struct

        block = struct.pack("<h", -32768) * 1600
        assert pcm16_rms_level(block) == 1.0

    def test_empty_and_sub_sample_blocks(self) -> None:
        assert pcm16_rms_level(b"") == 0.0
        assert pcm16_rms_level(b"\x01") == 0.0

    def test_worker_updates_level_from_stream(self) -> None:
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        worker = _worker(backend, sink, failures)
        assert worker.level == 0.0
        backend.feed(_pcm(3200, 16384))
        assert worker.level == pytest.approx(0.5, abs=0.01)
        worker.stop(flush=False)


class TestChunkAssembly:
    def test_blocks_assemble_into_exact_chunks(self) -> None:
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        worker = _worker(backend, sink, failures)
        # 2.5 chunks worth of 100 ms blocks.
        for _ in range(25):
            backend.feed(_pcm(CHUNK_BYTES // 10))
        worker.pause()  # barrier: all blocks processed
        assert [len(c) for c in sink.chunks] == [CHUNK_BYTES, CHUNK_BYTES]
        worker.stop(flush=True)
        # Final flush writes the remaining half chunk.
        assert [len(c) for c in sink.chunks] == [CHUNK_BYTES, CHUNK_BYTES, CHUNK_BYTES // 2]
        assert failures.exceptions == []

    def test_stop_without_flush_drops_partial(self) -> None:
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        worker = _worker(backend, sink, failures)
        backend.feed(_pcm(CHUNK_BYTES // 2))
        worker.stop(flush=False)
        assert sink.chunks == []

    def test_chunk_content_preserved_in_order(self) -> None:
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        worker = _worker(backend, sink, failures, chunk_bytes=8)
        backend.feed(b"\x01\x02\x03\x04\x05\x06")
        backend.feed(b"\x07\x08\x09\x0a")
        worker.stop(flush=True)
        assert b"".join(sink.chunks) == b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a"
        assert sink.chunks[0] == b"\x01\x02\x03\x04\x05\x06\x07\x08"

    def test_stop_is_idempotent(self) -> None:
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        worker = _worker(backend, sink, failures)
        worker.stop(flush=False)
        worker.stop(flush=False)
        assert not backend.stream_open


class TestPauseResume:
    def test_pause_drops_audio_cleanly_and_resume_captures(self) -> None:
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        worker = _worker(backend, sink, failures, chunk_bytes=8)
        backend.feed(b"\x01" * 8)
        worker.pause()
        assert sink.chunks == [b"\x01" * 8]
        backend.feed(b"\x02" * 8)  # while paused: cleanly dropped
        worker.resume()
        backend.feed(b"\x03" * 8)
        worker.pause()
        assert sink.chunks == [b"\x01" * 8, b"\x03" * 8]
        worker.stop(flush=False)

    def test_pause_waits_for_in_flight_chunk(self) -> None:
        """The plan-mandated synchronization: pause() must not return while a
        chunk write is mid-flight; the chunk lands fully before pause ends."""
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        gate = threading.Event()
        sink.block_event = gate
        worker = _worker(backend, sink, failures, chunk_bytes=8)
        backend.feed(b"\x05" * 8)
        assert sink.entered.wait(timeout=5)  # write is in flight, blocked in sink

        paused = threading.Event()
        pauser = threading.Thread(target=lambda: (worker.pause(), paused.set()))
        pauser.start()
        time.sleep(0.05)
        assert not paused.is_set()  # pause() waits on the in-flight write
        gate.set()  # let the write complete
        pauser.join(timeout=5)
        assert paused.is_set()
        assert sink.chunks == [b"\x05" * 8]  # fully written, exactly once
        worker.stop(flush=False)

    def test_block_raced_past_producer_gate_not_written_after_pause(self) -> None:
        """PR-HIGH-002: a device callback that passed the producer-side pause
        check before pause() set it can still enqueue its block AFTER the
        pause barrier — the worker-local gate must drop it, so no sink write
        ever happens after pause() has returned."""
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        worker = _worker(backend, sink, failures, chunk_bytes=8)
        worker.pause()
        # Simulate the raced callback: enqueue directly, bypassing the
        # producer-side _paused check (as a pre-empted _on_block would).
        worker._queue.put(b"\x09" * 8)  # noqa: SLF001 - deliberate race simulation
        worker.resume()
        worker.pause()  # barrier: the raced block has been processed by now
        assert sink.chunks == []  # dropped by the worker-local gate, never written
        worker.stop(flush=False)

    def test_resume_after_failure_raises(self) -> None:
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        worker = _worker(backend, sink, failures)
        backend.fail()
        assert failures.seen.wait(timeout=5)
        with pytest.raises(AudioCaptureError):
            worker.resume()
        worker.stop(flush=False)


class TestFailurePaths:
    def test_device_loss_flushes_buffer_then_fails(self) -> None:
        """Never silent data loss: audio buffered before the device died is
        flushed to the sink before on_failure fires."""
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        worker = _worker(backend, sink, failures, chunk_bytes=1000)
        backend.feed(b"\x0a" * 96)
        backend.fail()
        assert failures.seen.wait(timeout=5)
        assert isinstance(failures.exceptions[0], DeviceLostError)
        assert sink.chunks == [b"\x0a" * 96]
        assert worker.failed
        worker.stop(flush=False)

    def test_failed_flush_clears_plaintext_buffer(self) -> None:
        """PR-MED-001: when the device-loss flush itself fails, the surviving
        (draining) worker must not retain buffered plaintext PCM in memory."""
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        worker = _worker(backend, sink, failures, chunk_bytes=1000)
        backend.feed(b"\x0b" * 96)
        sink.raise_exc = OSError("disk full at device-loss flush")
        backend.fail()
        assert failures.seen.wait(timeout=5)
        # After a failed flush nothing may ever reach the sink again (and per
        # PR-MED-001 the buffer is cleared — verified at the code level by
        # the finally-clear in the _Fail branch).
        sink.raise_exc = None
        worker.stop(flush=True)
        assert sink.chunks == []
        assert isinstance(failures.exceptions[0], DeviceLostError | OSError)

    def test_sink_write_error_surfaces_once(self) -> None:
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        boom = OSError("disk full")
        sink.raise_exc = boom
        worker = _worker(backend, sink, failures, chunk_bytes=8)
        backend.feed(b"\x01" * 8)
        backend.feed(b"\x02" * 8)
        assert failures.seen.wait(timeout=5)
        worker.stop(flush=False)
        assert failures.exceptions == [boom]

    def test_audio_after_failure_is_not_written(self) -> None:
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        worker = _worker(backend, sink, failures, chunk_bytes=8)
        backend.fail()
        assert failures.seen.wait(timeout=5)
        with pytest.raises(AssertionError):
            backend.feed(b"\x01" * 8)  # stream already closed by the worker
        worker.stop(flush=False)
        assert sink.chunks == []

    def test_flush_failure_at_stop_reports(self) -> None:
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        worker = _worker(backend, sink, failures, chunk_bytes=1000)
        backend.feed(b"\x01" * 8)
        worker.pause()  # ensure buffered
        sink.raise_exc = OSError("disk full at flush")
        worker.stop(flush=True)
        assert failures.exceptions and isinstance(failures.exceptions[0], OSError)

    def test_queue_overflow_is_a_failure_not_silence(self) -> None:
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        gate = threading.Event()
        sink.block_event = gate
        worker = _worker(backend, sink, failures, chunk_bytes=8)
        try:
            # The worker is blocked inside the sink, so the queue fills; the
            # overflow is detected on the producer side and surfaced once the
            # worker resumes.
            for _ in range(300):  # > _QUEUE_MAX_BLOCKS while sink is blocked
                backend.feed(b"\x01" * 8)
            gate.set()
            assert failures.seen.wait(timeout=5)
            assert isinstance(failures.exceptions[0], CaptureOverflowError)
        finally:
            gate.set()
            worker.stop(flush=False)


class TestSoundDeviceBackendCallback:
    def _open_with_fake_sd(self, monkeypatch: pytest.MonkeyPatch) -> tuple[Any, list, list]:
        """Open a SoundDeviceBackend stream against a fake sounddevice module
        and return (captured PortAudio callback, blocks, errors)."""
        import types

        from scribe_desktop.audio_capture import SoundDeviceBackend

        created: list[Any] = []

        class _FakeRawInputStream:
            def __init__(self, **kwargs: Any) -> None:
                self.kwargs = kwargs
                created.append(self)

            def start(self) -> None:
                pass

            def abort(self) -> None:
                pass

            def close(self) -> None:
                pass

        fake_sd = types.SimpleNamespace(
            RawInputStream=_FakeRawInputStream, PortAudioError=RuntimeError
        )
        monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)
        blocks: list[bytes] = []
        errors: list[Exception] = []
        SoundDeviceBackend().open_stream(0, blocks.append, errors.append)
        return created[0].kwargs["callback"], blocks, errors

    def test_overflow_status_surfaces_failure_after_block(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PR-HIGH-004: a truthy PortAudio status (dropped device-side frames)
        must surface as CaptureOverflowError — never a silent gap — and the
        accompanying block is still delivered first (no loss of captured audio)."""
        callback, blocks, errors = self._open_with_fake_sd(monkeypatch)
        callback(b"\x01\x02", 1, None, "input overflow")  # truthy status object
        assert blocks == [b"\x01\x02"]
        assert len(errors) == 1 and isinstance(errors[0], CaptureOverflowError)

    def test_clean_status_does_not_fail(self, monkeypatch: pytest.MonkeyPatch) -> None:
        callback, blocks, errors = self._open_with_fake_sd(monkeypatch)
        callback(b"\x03\x04", 1, None, None)  # falsy status: normal block
        assert blocks == [b"\x03\x04"]
        assert errors == []


class TestWorkerLifecycle:
    def test_double_start_raises(self) -> None:
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        worker = _worker(backend, sink, failures)
        with pytest.raises(AudioCaptureError):
            worker.start()
        worker.stop(flush=False)

    def test_bad_chunk_bytes_rejected(self) -> None:
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        with pytest.raises(ValueError, match="chunk_bytes"):
            CaptureWorker(backend, 0, sink, on_failure=failures, chunk_bytes=0)
        with pytest.raises(ValueError, match="chunk_bytes"):
            CaptureWorker(backend, 0, sink, on_failure=failures, chunk_bytes=7)

    def test_stop_releases_device(self) -> None:
        backend, sink, failures = MockCaptureBackend(), _Sink(), _Failures()
        worker = _worker(backend, sink, failures)
        assert backend.stream_open
        worker.stop(flush=False)
        assert not backend.stream_open
