"""Step 3 audio-capture tests — mock backend ONLY (CI has no sound
hardware, and the module must be importable without PortAudio)."""

from __future__ import annotations

import importlib
import logging
import re
import sys
import threading
import time
import types
from typing import Any

import pytest

from scribe_desktop.audio_capture import (
    CHUNK_BYTES,
    INPUT_LATENCY_SECONDS,
    AudioCaptureError,
    AudioDevice,
    CaptureOverflowError,
    CaptureWorker,
    DeviceLostError,
    MockCaptureBackend,
    SoundDeviceBackend,
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
            assert failures.exceptions[0].detail_code == "queue_full"  # round 35 MED-001
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
        self.finished = created[0].kwargs["finished_callback"]
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

    @pytest.mark.parametrize(
        ("flags", "code"),
        [
            ({"input_overflow": True}, "status_input_overflow"),
            ({"input_underflow": True}, "status_input_underflow"),
            ({"input_overflow": True, "input_underflow": True}, "status_input_overflow"),
            ({"output_overflow": True}, "status_other"),
        ],
    )
    def test_a_status_flag_names_its_detail_code(
        self, monkeypatch: pytest.MonkeyPatch, flags: dict[str, bool], code: str
    ) -> None:
        """Installation plan round 35 MED-001: the failure carries a fixed
        word for the flag (``sounddevice.CallbackFlags`` attributes), never
        built from the status object's text."""
        import types

        callback, _blocks, errors = self._open_with_fake_sd(monkeypatch)
        status = types.SimpleNamespace(**flags)  # a plain object: truthy
        callback(b"\x01\x02", 1, None, status)
        assert len(errors) == 1 and isinstance(errors[0], CaptureOverflowError)
        assert errors[0].detail_code == code

    def test_an_unnamed_status_reads_as_status_other(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        callback, _blocks, errors = self._open_with_fake_sd(monkeypatch)
        callback(b"\x01\x02", 1, None, "input overflow")  # no flag attributes
        assert errors[0].detail_code == "status_other"

    def test_a_stream_ending_unasked_is_device_lost_stream_ended(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _callback, _blocks, errors = self._open_with_fake_sd(monkeypatch)
        self.finished()
        assert len(errors) == 1 and isinstance(errors[0], DeviceLostError)
        assert errors[0].detail_code == "stream_ended"


class TestDetailCodes:
    def test_an_unknown_detail_code_reads_as_unspecified(self) -> None:
        assert AudioCaptureError("x").detail_code == "unspecified"
        assert DeviceLostError("x", detail_code="made up").detail_code == "unspecified"
        assert DeviceLostError("x", detail_code="open_failed").detail_code == "open_failed"

    def test_a_device_that_will_not_open_is_open_failed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import types

        from scribe_desktop.audio_capture import SoundDeviceBackend

        class _Refusing:
            def __init__(self, **kwargs: Any) -> None:
                raise RuntimeError("Device unavailable")

        fake_sd = types.SimpleNamespace(RawInputStream=_Refusing, PortAudioError=RuntimeError)
        monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)
        with pytest.raises(DeviceLostError, match="Device unavailable") as raised:
            SoundDeviceBackend().open_stream(3, lambda b: None, lambda e: None)
        assert raised.value.detail_code == "open_failed"


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


# --------------------------------------------------------------------------
# Capture-overflow plan (0.4.3), Task 1.4: the recording stream's buffer
# (D1), the one retry (D2), the log lines (D4) and the MME-only list (D8).
# A fake ``sounddevice`` with host queries and a refusable stream; no
# hardware, and the tests above keep their own fake unedited.
# --------------------------------------------------------------------------

_TODAYS_STREAM_ARGUMENTS = {
    "samplerate",
    "blocksize",
    "device",
    "channels",
    "dtype",
    "callback",
    "finished_callback",
}
_STREAM_LINE = re.compile(r"capture_stream( [a-z_]+=[a-z0-9_]+)+")
_FALLBACK_LINE = "capture_stream detail_code=mme device_id=1 state=default_latency"


class _HostedSounddevice:
    """A fake ``sounddevice``: device 0 is an output, devices 1 to 3 are one
    microphone listed under three host APIs. ``refusals`` is consumed one
    word per stream constructed: ``constructor``, ``start`` or ``""``."""

    class PortAudioError(Exception):
        pass

    def __init__(
        self,
        hosts: tuple[str, ...] = ("MME", "Windows DirectSound", "Windows WASAPI"),
        refusals: tuple[str, ...] = (),
    ) -> None:
        self.hosts = hosts
        self.refusals = list(refusals)
        self.created: list[Any] = []
        self.default = types.SimpleNamespace(device=(1, 0))
        name = "Jane Citizen's Headset"
        self.devices: list[dict[str, Any]] = [
            {"name": "Speakers", "max_input_channels": 0, "hostapi": 0},
            *(
                {"name": name, "max_input_channels": 1, "hostapi": index}
                for index in range(len(hosts))
            ),
        ]
        fake = self

        class _Stream:
            def __init__(self, **kwargs: Any) -> None:
                self.kwargs = kwargs
                self.calls: list[str] = []
                self.refusal = fake.refusals.pop(0) if fake.refusals else ""
                fake.created.append(self)
                if self.refusal == "constructor":
                    raise fake.PortAudioError("SECRET-PORTAUDIO-TEXT")

            def start(self) -> None:
                self.calls.append("start")
                if self.refusal == "start":
                    raise fake.PortAudioError("SECRET-PORTAUDIO-TEXT")

            def abort(self) -> None:
                self.calls.append("abort")

            def close(self) -> None:
                self.calls.append("close")

        self.RawInputStream = _Stream

    def query_devices(self, device: int | None = None) -> Any:
        return self.devices if device is None else self.devices[device]

    def query_hostapis(self, index: int) -> dict[str, Any]:
        return {"name": self.hosts[index]}


class _Lines(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def lines() -> Any:
    logger = logging.getLogger("test-audio-capture-stream-lines")
    handler = _Lines()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler.logger = logger  # type: ignore[attr-defined]
    try:
        yield handler
    finally:
        logger.removeHandler(handler)


def _install(monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> _HostedSounddevice:
    fake = _HostedSounddevice(**kwargs)
    monkeypatch.setitem(sys.modules, "sounddevice", fake)
    return fake


class TestTheRecordingBuffer:
    def test_the_decided_value(self) -> None:
        """Task 0.3's decision (2026-11-26). A change is a new dated decision
        with ``scripts/measure-capture-stall.py`` run again (plan D1)."""
        assert INPUT_LATENCY_SECONDS == 2.5

    @pytest.mark.parametrize("asked", [None, 1.5], ids=["the-constant", "another-value"])
    def test_an_mme_recording_stream_requests_the_buffer(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any, asked: float | None
    ) -> None:
        fake = _install(monkeypatch)
        backend = (
            SoundDeviceBackend(logger=lines.logger)
            if asked is None
            else SoundDeviceBackend(logger=lines.logger, input_latency=asked)
        )
        expected = INPUT_LATENCY_SECONDS if asked is None else asked
        backend.open_stream(1, lambda b: None, lambda e: None)
        assert len(fake.created) == 1
        kwargs = fake.created[0].kwargs
        assert kwargs["latency"] == expected
        assert set(kwargs) == _TODAYS_STREAM_ARGUMENTS | {"latency"}
        assert (kwargs["samplerate"], kwargs["blocksize"], kwargs["device"]) == (16_000, 1600, 1)
        assert (kwargs["channels"], kwargs["dtype"]) == (1, "int16")
        assert lines.messages == [
            f"capture_stream detail_code=mme device_id=1 duration_ms={round(expected * 1000)} "
            "state=opened"
        ]

    @pytest.mark.parametrize(
        ("host", "word"),
        [
            ("Windows DirectSound", "directsound"),
            ("Windows WASAPI", "wasapi"),
            ("Windows WDM-KS", "wdmks"),
            ("ASIO", "other"),
        ],
    )
    def test_a_non_mme_stream_opens_with_the_default(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any, host: str, word: str
    ) -> None:
        fake = _install(monkeypatch, hosts=("MME", host))
        SoundDeviceBackend(logger=lines.logger).open_stream(2, lambda b: None, lambda e: None)
        assert len(fake.created) == 1
        assert set(fake.created[0].kwargs) == _TODAYS_STREAM_ARGUMENTS
        assert lines.messages == [
            f"capture_stream detail_code={word} device_id=2 state=default_latency"
        ]

    def test_an_instance_built_without_a_buffer_opens_as_today(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The level monitor's and enrolment's instance (plan D1)."""
        fake = _install(monkeypatch)
        SoundDeviceBackend(input_latency=None).open_stream(1, lambda b: None, lambda e: None)
        assert len(fake.created) == 1
        assert set(fake.created[0].kwargs) == _TODAYS_STREAM_ARGUMENTS

    def test_an_unknown_device_opens_as_today(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A host that cannot be resolved is ``other``: no buffer is asked."""
        fake = _install(monkeypatch)
        SoundDeviceBackend().open_stream(99, lambda b: None, lambda e: None)
        assert set(fake.created[0].kwargs) == _TODAYS_STREAM_ARGUMENTS

    def test_an_instance_without_a_buffer_or_logger_asks_no_host(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Plan D1: the level meter's instance opens exactly as today, without
        PortAudio's two host queries."""
        fake = _install(monkeypatch)
        queries: list[str] = []

        def query_devices(device: int | None = None) -> Any:
            queries.append("query_devices")
            return fake.devices if device is None else fake.devices[device]

        def query_hostapis(index: int) -> dict[str, Any]:
            queries.append("query_hostapis")
            return {"name": fake.hosts[index]}

        monkeypatch.setattr(fake, "query_devices", query_devices)
        monkeypatch.setattr(fake, "query_hostapis", query_hostapis)
        SoundDeviceBackend(input_latency=None).open_stream(1, lambda b: None, lambda e: None)
        assert queries == []
        assert len(fake.created) == 1
        assert set(fake.created[0].kwargs) == _TODAYS_STREAM_ARGUMENTS


class TestTheRetry:
    @pytest.mark.parametrize("refusal", ["constructor", "start"])
    def test_a_refused_buffer_retries_once_with_the_default(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any, refusal: str
    ) -> None:
        fake = _install(monkeypatch, refusals=(refusal,))
        errors: list[Exception] = []
        handle = SoundDeviceBackend(logger=lines.logger).open_stream(
            1, lambda b: None, errors.append
        )
        first, second = fake.created
        assert first.kwargs["latency"] == INPUT_LATENCY_SECONDS
        assert set(second.kwargs) == _TODAYS_STREAM_ARGUMENTS
        # The failed attempt is closed (a refused constructor left no stream).
        assert first.calls == ([] if refusal == "constructor" else ["start", "close"])
        # Its ``finished`` never reads as device loss; the live stream's does.
        first.kwargs["finished_callback"]()
        assert errors == []
        second.kwargs["finished_callback"]()
        assert len(errors) == 1 and isinstance(errors[0], DeviceLostError)
        handle.stop()
        assert second.calls == ["start", "abort", "close"]
        assert "abort" not in first.calls

    def test_a_second_refusal_is_open_failed(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any
    ) -> None:
        fake = _install(monkeypatch, refusals=("start", "constructor", ""))
        with pytest.raises(DeviceLostError, match="SECRET-PORTAUDIO-TEXT") as raised:
            SoundDeviceBackend(logger=lines.logger).open_stream(
                1, lambda b: None, lambda e: None
            )
        assert raised.value.detail_code == "open_failed"
        assert len(fake.created) == 2  # ONE retry, never a third open
        assert lines.messages == []

    @pytest.mark.parametrize(
        ("refusals", "logged"),
        [
            (("constructor",), [_FALLBACK_LINE]),
            (("start",), [_FALLBACK_LINE]),
            (("constructor", "start"), []),
        ],
        ids=["constructor-then-open", "start-then-open", "both-refused"],
    )
    def test_the_fallback_line_is_logged_only_when_the_retry_opens(
        self,
        monkeypatch: pytest.MonkeyPatch,
        lines: Any,
        refusals: tuple[str, ...],
        logged: list[str],
    ) -> None:
        _install(monkeypatch, refusals=refusals)
        backend = SoundDeviceBackend(logger=lines.logger)
        if logged:
            backend.open_stream(1, lambda b: None, lambda e: None)
        else:
            with pytest.raises(DeviceLostError):
                backend.open_stream(1, lambda b: None, lambda e: None)
        assert lines.messages == logged  # never an ``opened`` line for a refused buffer

    def test_a_refused_buffer_whose_close_raises_still_retries(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any
    ) -> None:
        """Plan D2: the failed attempt is closed with errors ignored, and the
        retry with the default still opens."""
        fake = _install(monkeypatch, refusals=("start",))
        base = fake.RawInputStream

        class _CloseRaises(base):
            def close(self) -> None:
                super().close()
                if self.refusal == "start":
                    raise RuntimeError("close refused")

        fake.RawInputStream = _CloseRaises
        SoundDeviceBackend(logger=lines.logger).open_stream(1, lambda b: None, lambda e: None)
        first, second = fake.created
        assert first.kwargs["latency"] == INPUT_LATENCY_SECONDS
        assert first.calls == ["start", "close"]
        assert set(second.kwargs) == _TODAYS_STREAM_ARGUMENTS
        assert second.calls == ["start"]
        assert lines.messages == [_FALLBACK_LINE]

    @pytest.mark.parametrize("refusal", ["constructor", "start"])
    @pytest.mark.parametrize(
        ("hosts", "device_id", "input_latency"),
        [
            (("MME", "Windows DirectSound", "Windows WASAPI"), 1, None),
            (("MME", "Windows WASAPI"), 2, INPUT_LATENCY_SECONDS),
        ],
        ids=["no-buffer-instance", "non-mme-device"],
    )
    def test_a_refusal_without_a_buffer_is_one_attempt(
        self,
        monkeypatch: pytest.MonkeyPatch,
        hosts: tuple[str, ...],
        device_id: int,
        input_latency: float | None,
        refusal: str,
    ) -> None:
        """Plan D2: with no buffer asked there is nothing to retry; the one
        refusal is today's ``open_failed``."""
        fake = _install(monkeypatch, hosts=hosts, refusals=(refusal, ""))
        with pytest.raises(DeviceLostError) as raised:
            SoundDeviceBackend(input_latency=input_latency).open_stream(
                device_id, lambda b: None, lambda e: None
            )
        assert raised.value.detail_code == "open_failed"
        assert len(fake.created) == 1

    class _Interrupted(RuntimeError):
        pass

    @pytest.mark.parametrize("raised_type", [KeyboardInterrupt, _Interrupted])
    def test_an_interrupted_start_closes_the_stream_and_is_never_retried(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any, raised_type: type[BaseException]
    ) -> None:
        """An exception other than PortAudio's during ``start()`` leaves no
        stream open: the stream is closed, the exception propagates unchanged
        and the D2 retry (PortAudio's refusal only) is not taken."""
        fake = _install(monkeypatch)
        base = fake.RawInputStream
        interruption = raised_type()

        class _StartInterrupted(base):
            def start(self) -> None:
                super().start()
                raise interruption

        fake.RawInputStream = _StartInterrupted
        errors: list[Exception] = []
        with pytest.raises(raised_type) as caught:
            SoundDeviceBackend(logger=lines.logger).open_stream(1, lambda b: None, errors.append)
        assert caught.value is interruption
        assert len(fake.created) == 1  # no retry
        (stream,) = fake.created
        assert stream.calls == ["start", "close"]
        # The discarded attempt's ``finished`` never reads as device loss.
        stream.kwargs["finished_callback"]()
        assert errors == []
        assert lines.messages == []


class TestTheCallbackGaps:
    def _open(self, monkeypatch: pytest.MonkeyPatch, logger: Any = None) -> tuple[Any, ...]:
        fake = _install(monkeypatch)
        clock = _Clock()
        errors: list[Exception] = []
        blocks: list[bytes] = []
        handle = SoundDeviceBackend(logger=logger, clock=clock).open_stream(
            1, blocks.append, errors.append
        )
        return fake.created[0].kwargs["callback"], clock, errors, blocks, handle

    @pytest.mark.parametrize(
        ("entries", "expected_ms"),
        [
            # normal, a long gap with a clean status, a short gap with the flag
            ((0.0, 0.125, 2.5, 2.625), 2375),
            # the long gap is on the flagged callback itself
            ((0.0, 0.125, 0.25, 2.5), 2250),
            # the long gap is older than the three most recent: not carried
            ((0.0, 2.5, 2.625, 2.75, 2.875), 125),
            # fewer than three gaps: the largest of those
            ((0.0, 0.5), 500),
        ],
        ids=["before-the-flag", "on-the-flag", "outside-the-window", "one-gap"],
    )
    def test_the_flagged_callback_carries_the_largest_recent_gap(
        self, monkeypatch: pytest.MonkeyPatch, entries: tuple[float, ...], expected_ms: int
    ) -> None:
        callback, clock, errors, blocks, _handle = self._open(monkeypatch)
        for index, entry in enumerate(entries):
            clock.now = entry
            last = index == len(entries) - 1
            status = types.SimpleNamespace(input_overflow=True) if last else None
            callback(b"\x01\x02", 1, None, status)
        assert len(blocks) == len(entries)  # the flagged block is still delivered
        assert len(errors) == 1 and isinstance(errors[0], CaptureOverflowError)
        assert errors[0].detail_code == "status_input_overflow"
        assert errors[0].gap_ms == expected_ms

    def test_a_first_callback_has_no_gap(self, monkeypatch: pytest.MonkeyPatch) -> None:
        callback, _clock, errors, _blocks, _handle = self._open(monkeypatch)
        callback(b"\x01\x02", 1, None, types.SimpleNamespace(input_overflow=True))
        assert len(errors) == 1 and errors[0].gap_ms is None  # type: ignore[attr-defined]

    def test_other_capture_errors_carry_no_gap(self) -> None:
        assert DeviceLostError("x", detail_code="stream_ended").gap_ms is None
        assert AudioCaptureError("x").gap_ms is None

    def test_the_flagged_gap_is_rounded_not_truncated(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Plan D4 "Each figure, exactly": every logged time is ``round``."""
        callback, clock, errors, _blocks, _handle = self._open(monkeypatch)
        entries = (0.0, 0.1, 0.2996, 0.3996)  # recent gaps 0.1, 0.1996, 0.1
        for index, entry in enumerate(entries):
            clock.now = entry
            last = index == len(entries) - 1
            status = types.SimpleNamespace(input_overflow=True) if last else None
            callback(b"\x01\x02", 1, None, status)
        assert len(errors) == 1 and isinstance(errors[0], CaptureOverflowError)
        assert errors[0].gap_ms == 200

    def test_only_a_non_negative_int_gap_is_kept(self) -> None:
        """Plan D4: a bool, a float or a negative number carries no gap."""
        assert AudioCaptureError("x", gap_ms=True).gap_ms is None
        assert CaptureOverflowError("x", gap_ms=1.5).gap_ms is None
        assert AudioCaptureError("x", gap_ms=-1).gap_ms is None
        assert AudioCaptureError("x", gap_ms="3").gap_ms is None  # type: ignore[arg-type]
        assert CaptureOverflowError("x", gap_ms=7).gap_ms == 7


class TestTheStreamLines:
    def _recording(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any, entries: tuple[float, ...] = ()
    ) -> tuple[Any, _Clock, Any]:
        fake = _install(monkeypatch)
        clock = _Clock()
        handle = SoundDeviceBackend(logger=lines.logger, clock=clock).open_stream(
            1, lambda b: None, lambda e: None
        )
        callback = fake.created[0].kwargs["callback"]

        class _Status:
            def __str__(self) -> str:
                return "SECRET-STATUS-TEXT"

        for entry in entries:
            clock.now = entry
            callback(b"\x01\x02", 1, None, _Status())
        return handle, clock, fake

    def test_the_stream_lines_hold_numbers_and_fixed_words_only(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any
    ) -> None:
        """Every line went through ``log_event`` (which refuses any key off
        its whitelist) and holds only fixed words and numbers: never the
        device's name, PortAudio's text or a status object's text."""
        handle, clock, _fake = self._recording(monkeypatch, lines, (0.0, 0.125, 0.25))
        clock.now = 1.0
        handle.stop()
        _install(monkeypatch, hosts=("MME", "Windows WASAPI"))
        SoundDeviceBackend(logger=lines.logger).open_stream(2, lambda b: None, lambda e: None)
        assert [line.rsplit("state=", 1)[1] for line in lines.messages] == [
            "opened",
            "backlog_dropped",
            "closed",
            "default_latency",
        ]
        for line in lines.messages:
            assert _STREAM_LINE.fullmatch(line), line
            assert not any(word in line for word in ("SECRET", "Jane", "Headset", "status:"))

    def test_a_close_inside_a_stall_logs_the_backlog_line(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any
    ) -> None:
        handle, clock, _fake = self._recording(monkeypatch, lines, (0.0, 0.125, 0.25))
        clock.now = 0.75  # the last callback is 0.5 s old at the stop
        handle.stop()
        assert lines.messages[1:] == [
            "capture_stream device_id=1 duration_ms=500 state=backlog_dropped",
            "capture_stream count=3 device_id=1 duration_ms=125 state=closed",
        ]

    def test_a_close_at_the_threshold_logs_no_backlog_line(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any
    ) -> None:
        handle, clock, _fake = self._recording(monkeypatch, lines, (0.0, 0.125, 0.25))
        clock.now = 0.5  # exactly 250 ms old: "strictly more than" is not met
        handle.stop()
        assert lines.messages[1:] == [
            "capture_stream count=3 device_id=1 duration_ms=125 state=closed"
        ]

    def test_a_stream_with_no_callback_closes_with_zeros(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any
    ) -> None:
        handle, clock, _fake = self._recording(monkeypatch, lines)
        clock.now = 30.0
        handle.stop()
        handle.stop()  # idempotent: one closed line per stream
        assert lines.messages[1:] == [
            "capture_stream count=0 device_id=1 duration_ms=0 state=closed"
        ]

    def test_a_stop_that_raises_still_logs_the_closed_line(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any
    ) -> None:
        handle, _clock, fake = self._recording(monkeypatch, lines, (0.0, 0.125))

        def refuse() -> None:
            raise RuntimeError("abort refused")

        fake.created[0].abort = refuse
        with pytest.raises(RuntimeError, match="abort refused"):
            handle.stop()
        assert lines.messages[-1] == (
            "capture_stream count=2 device_id=1 duration_ms=125 state=closed"
        )

    def test_an_abort_that_raises_still_closes_the_stream(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any
    ) -> None:
        """``close()`` is attempted even when ``abort()`` raises, the closed
        line is logged exactly once, and the abort's exception propagates."""
        handle, _clock, fake = self._recording(monkeypatch, lines, (0.0, 0.125))
        stream = fake.created[0]

        def refuse() -> None:
            stream.calls.append("abort")
            raise RuntimeError("abort refused")

        stream.abort = refuse
        with pytest.raises(RuntimeError, match="abort refused"):
            handle.stop()
        handle.stop()  # idempotent: nothing more is closed or logged
        assert stream.calls == ["start", "abort", "close"]
        assert [line for line in lines.messages if line.endswith("state=closed")] == [
            "capture_stream count=2 device_id=1 duration_ms=125 state=closed"
        ]

    def test_no_logger_logs_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import scribe_desktop.audio_capture as module

        calls: list[Any] = []
        monkeypatch.setattr(module, "log_event", lambda *args, **kwargs: calls.append(args))
        fake = _install(monkeypatch, refusals=("start",))
        clock = _Clock()
        handle = SoundDeviceBackend(clock=clock).open_stream(1, lambda b: None, lambda e: None)
        callback = fake.created[1].kwargs["callback"]
        callback(b"\x01\x02", 1, None, None)
        clock.now = 5.0
        handle.stop()
        assert calls == []

    def test_the_closed_line_carries_the_longest_gap_of_the_life(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any
    ) -> None:
        """Plan D4 "Each figure, exactly": the largest gap of the stream's
        life, not the last one."""
        entries = (0.0, 2.5, 2.625, 2.75, 2.875, 3.0)
        handle, clock, _fake = self._recording(monkeypatch, lines, entries)
        clock.now = 3.0
        handle.stop()
        assert lines.messages[1:] == [
            "capture_stream count=6 device_id=1 duration_ms=2500 state=closed"
        ]

    def test_one_callback_closes_with_no_gap(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any
    ) -> None:
        """Plan D4: ``duration_ms`` is 0 with fewer than two callbacks."""
        handle, clock, _fake = self._recording(monkeypatch, lines, (0.0,))
        clock.now = 0.0
        handle.stop()
        assert lines.messages[1:] == [
            "capture_stream count=1 device_id=1 duration_ms=0 state=closed"
        ]

    def test_the_age_is_read_before_abort(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any
    ) -> None:
        """Plan D4: the age of the last callback is read at the top of
        ``stop()``, before ``abort()``; an abort that takes 1 s adds nothing."""
        handle, clock, fake = self._recording(monkeypatch, lines, (0.0, 0.125))

        def slow_abort() -> None:
            clock.now += 1.0

        fake.created[0].abort = slow_abort
        clock.now = 0.225  # the last callback is 0.1 s old at the stop
        handle.stop()
        assert lines.messages[1:] == [
            "capture_stream count=2 device_id=1 duration_ms=125 state=closed"
        ]

    def test_the_closed_gap_is_rounded_not_truncated(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any
    ) -> None:
        """Plan D4 "Each figure, exactly": every logged time is ``round``."""
        handle, clock, _fake = self._recording(monkeypatch, lines, (0.0, 0.1996))
        clock.now = 0.1996
        handle.stop()
        assert lines.messages[1:] == [
            "capture_stream count=2 device_id=1 duration_ms=200 state=closed"
        ]

    def test_two_threads_stopping_at_once_close_the_stream_once(
        self, monkeypatch: pytest.MonkeyPatch, lines: Any
    ) -> None:
        """Plan D4: one closed line per stream, even when ``CaptureWorker``'s
        failure path and its stop call ``stop()`` from two threads."""
        handle, clock, fake = self._recording(monkeypatch, lines, (0.0, 0.125))
        clock.now = 0.125
        aborts: list[str] = []

        def slow_abort() -> None:
            aborts.append("abort")
            time.sleep(0.05)

        fake.created[0].abort = slow_abort
        barrier = threading.Barrier(2)

        def stop() -> None:
            barrier.wait(timeout=5)
            handle.stop()

        threads = [threading.Thread(target=stop) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        assert not any(thread.is_alive() for thread in threads)
        assert aborts == ["abort"]
        assert [line for line in lines.messages if line.endswith("state=closed")] == [
            "capture_stream count=2 device_id=1 duration_ms=125 state=closed"
        ]


class TestTheMicrophoneList:
    def test_the_list_keeps_mme_entries_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Plan D8: each microphone once, under the host that reports dropped
        frames; the ids are PortAudio's own."""
        _install(monkeypatch)
        assert SoundDeviceBackend().list_input_devices() == [
            AudioDevice(device_id=1, name="Jane Citizen's Headset", is_default=True)
        ]

    def test_the_list_is_unfiltered_without_an_mme_entry(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install(monkeypatch, hosts=("Core Audio", "JACK"))
        assert [d.device_id for d in SoundDeviceBackend().list_input_devices()] == [1, 2]

    def test_the_list_is_unfiltered_without_host_information(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _install(monkeypatch)
        monkeypatch.setattr(
            fake, "query_hostapis", lambda index: (_ for _ in ()).throw(RuntimeError("no hosts"))
        )
        assert [d.device_id for d in SoundDeviceBackend().list_input_devices()] == [1, 2, 3]

    def test_the_list_is_unfiltered_when_only_an_output_is_on_mme(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Plan D8: the filter needs an MME INPUT entry; an MME output alone
        leaves every input entry listed."""
        fake = _install(monkeypatch)
        fake.devices[1]["hostapi"] = 1  # the MME input moves to DirectSound
        assert [d.device_id for d in SoundDeviceBackend().list_input_devices()] == [1, 2, 3]
