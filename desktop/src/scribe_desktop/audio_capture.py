"""Audio capture (Phase 2 Step 3).

Capture stack per the plan Design Decision: ``sounddevice``
(PortAudio/WASAPI), 16 kHz mono PCM16, ~1 s chunks, level metering from
the same stream.

Structure:

- :class:`CaptureBackend` protocol — device enumeration + stream opening.
  Two implementations: :class:`SoundDeviceBackend` (real hardware; imports
  ``sounddevice`` LAZILY inside methods so this module imports cleanly on
  machines without the PortAudio DLL — executor fact) and
  :class:`MockCaptureBackend` (CI / unit tests; never touches PortAudio).
- :class:`CaptureWorker` — the SINGLE writer to the session chunk store
  (plan Concurrency model). Backend callbacks enqueue raw PCM blocks; the
  worker thread assembles ~1 s chunks and writes them through the sink
  (``SessionChunkStore.append_chunk``). Control operations (pause/stop)
  synchronize through the same queue via barrier sentinels, so a chunk is
  either fully written or cleanly dropped — never half-written, never
  written after pause()/stop() returns.
- Device loss mid-session surfaces as :class:`DeviceLostError` through the
  worker's ``on_failure`` callback after a best-effort flush of buffered
  audio (never silent data loss); the Step 4 session machine maps it to
  state=``failed`` (recoverable).

Logging goes through ``log_event`` with whitelisted keys only; raw audio
never reaches a logger (Critical Constraint).
"""

from __future__ import annotations

import queue
import threading
from array import array
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final, Protocol

SAMPLE_RATE: Final = 16_000
CHANNELS: Final = 1
SAMPLE_WIDTH: Final = 2  # PCM16
# ~1 s of 16 kHz mono PCM16 per chunk (plan: ~1 s chunks).
CHUNK_BYTES: Final = SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH
# Backend block size: 100 ms keeps level metering responsive.
BLOCK_FRAMES: Final = SAMPLE_RATE // 10

_QUEUE_MAX_BLOCKS: Final = 256  # ~25 s backlog bound; overflow -> failure, never silent loss
_CONTROL_TIMEOUT_S: Final = 10.0


class AudioCaptureError(Exception):
    """Base class for capture failures."""


class DeviceLostError(AudioCaptureError):
    """The input device disappeared or the stream aborted mid-session.

    Recoverable: the session transitions to ``failed``; captured audio
    already flushed to the store survives for recovery."""


class CaptureOverflowError(AudioCaptureError):
    """The worker could not keep up and the block queue overflowed —
    surfaced as a failure rather than silently dropping audio."""


@dataclass(frozen=True)
class AudioDevice:
    """Non-clinical device metadata (safe to log: device_id is whitelisted)."""

    device_id: int
    name: str
    is_default: bool


class CaptureStream(Protocol):
    """A live input stream handle returned by a backend."""

    def stop(self) -> None:
        """Stop callbacks and release the device. Idempotent."""


class CaptureBackend(Protocol):
    """Device enumeration + stream opening (real or mock)."""

    def list_input_devices(self) -> list[AudioDevice]: ...

    def open_stream(
        self,
        device_id: int,
        on_block: Callable[[bytes], None],
        on_error: Callable[[Exception], None],
    ) -> CaptureStream:
        """Open a 16 kHz mono PCM16 input stream on ``device_id``.

        ``on_block`` receives raw PCM byte blocks from the device thread;
        ``on_error`` is invoked once if the stream dies (device loss)."""
        ...


def pcm16_rms_level(block: bytes) -> float:
    """Normalized RMS level (0.0–1.0) of a little-endian PCM16 block."""
    if len(block) < SAMPLE_WIDTH:
        return 0.0
    samples = array("h")
    samples.frombytes(block[: len(block) - (len(block) % SAMPLE_WIDTH)])
    if not samples:
        return 0.0
    mean_square: float = sum(s * s for s in samples) / len(samples)
    return min(1.0, float(mean_square**0.5) / 32768.0)


# --------------------------------------------------------------------------
# Real backend — sounddevice, imported LAZILY (module must import without
# PortAudio; executor fact + CI requirement).
# --------------------------------------------------------------------------


class _SoundDeviceStream:
    def __init__(self, stream: object) -> None:
        self._stream = stream
        self.stopped_by_us = False

    def stop(self) -> None:
        self.stopped_by_us = True
        stream = self._stream
        if stream is None:
            return
        self._stream = None
        stream.abort()  # type: ignore[attr-defined]
        stream.close()  # type: ignore[attr-defined]


class SoundDeviceBackend:
    """PortAudio/WASAPI capture via ``sounddevice`` (lazy import)."""

    def list_input_devices(self) -> list[AudioDevice]:
        import sounddevice as sd

        default_input = sd.default.device[0]
        devices: list[AudioDevice] = []
        for index, info in enumerate(sd.query_devices()):
            if int(info.get("max_input_channels", 0)) < CHANNELS:
                continue
            devices.append(
                AudioDevice(
                    device_id=index,
                    name=str(info.get("name", f"device {index}")),
                    is_default=index == default_input,
                )
            )
        return devices

    def open_stream(
        self,
        device_id: int,
        on_block: Callable[[bytes], None],
        on_error: Callable[[Exception], None],
    ) -> CaptureStream:
        import sounddevice as sd

        handle: _SoundDeviceStream | None = None

        def callback(indata: Any, frames: int, time_info: object, status: object) -> None:
            # Deliver the block first so already-captured audio is never
            # lost, THEN surface any status flag (input overflow = frames
            # dropped device-side) as a recoverable failure — a consultation
            # must never contain a silent, undetected gap (PR-HIGH-004,
            # plan Critical Constraint: never silent data loss).
            on_block(bytes(indata))
            if status:
                on_error(
                    CaptureOverflowError(f"device reported dropped frames (status: {status})")
                )

        def finished() -> None:
            # PortAudio fires finished_callback when the stream ends. If WE
            # did not stop it, the device died mid-session.
            if handle is not None and not handle.stopped_by_us:
                on_error(DeviceLostError("input stream ended unexpectedly (device lost)"))

        try:
            stream = sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_FRAMES,
                device=device_id,
                channels=CHANNELS,
                dtype="int16",
                callback=callback,
                finished_callback=finished,
            )
            handle = _SoundDeviceStream(stream)
            stream.start()
        except sd.PortAudioError as exc:
            raise DeviceLostError(f"failed opening input device {device_id}: {exc}") from exc
        return handle


# --------------------------------------------------------------------------
# Mock backend — CI / unit tests. Never touches PortAudio.
# --------------------------------------------------------------------------


class _MockStream:
    def __init__(self, backend: MockCaptureBackend) -> None:
        self._backend = backend

    def stop(self) -> None:
        self._backend._detach(self)


class MockCaptureBackend:
    """Test double: the test pushes PCM via :meth:`feed` and simulates
    device loss via :meth:`fail`."""

    def __init__(self, devices: list[AudioDevice] | None = None) -> None:
        self.devices = devices or [AudioDevice(0, "Mock Microphone", True)]
        self._on_block: Callable[[bytes], None] | None = None
        self._on_error: Callable[[Exception], None] | None = None
        self._stream: _MockStream | None = None
        self.opened_device_id: int | None = None

    def list_input_devices(self) -> list[AudioDevice]:
        return list(self.devices)

    def open_stream(
        self,
        device_id: int,
        on_block: Callable[[bytes], None],
        on_error: Callable[[Exception], None],
    ) -> CaptureStream:
        if all(device.device_id != device_id for device in self.devices):
            raise DeviceLostError(f"no such input device {device_id}")
        self.opened_device_id = device_id
        self._on_block = on_block
        self._on_error = on_error
        self._stream = _MockStream(self)
        return self._stream

    def _detach(self, stream: _MockStream) -> None:
        if self._stream is stream:
            self._stream = None
            self._on_block = None
            self._on_error = None

    @property
    def stream_open(self) -> bool:
        return self._stream is not None

    def feed(self, block: bytes) -> None:
        """Deliver a PCM block as if the device produced it."""
        if self._on_block is None:
            raise AssertionError("no open mock stream")
        self._on_block(block)

    def fail(self, exc: Exception | None = None) -> None:
        """Simulate device loss."""
        if self._on_error is None:
            raise AssertionError("no open mock stream")
        self._on_error(exc or DeviceLostError("mock device lost"))


# --------------------------------------------------------------------------
# Capture worker — the single writer (plan Concurrency model).
# --------------------------------------------------------------------------


class _SetPaused:
    """Queue sentinel: the worker sets `done` when it reaches it — every
    block enqueued before the sentinel has been assembled/written — and
    flips its worker-local paused gate to ``paused``. PR-HIGH-002: the
    worker-local gate (not the producer-side event alone) decides whether
    a block is written, so a device callback that raced past the producer
    check can never cause a sink write after pause() has returned."""

    def __init__(self, paused: bool) -> None:
        self.paused = paused
        self.done = threading.Event()


class _Stop:
    def __init__(self, flush: bool) -> None:
        self.flush = flush
        self.done = threading.Event()


class _Fail:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc


class CaptureWorker:
    """Owns the capture stream and is the ONLY writer through ``sink``.

    ``sink`` is ``SessionChunkStore.append_chunk`` (or equivalent): it may
    raise ``StoreWriteError`` on disk failure — surfaced once through
    ``on_failure`` (the session machine maps it to ``failed``).

    Threading contract:
    - backend callbacks enqueue blocks (device thread);
    - one worker thread assembles chunks and calls ``sink`` — single writer;
    - ``pause()``/``resume()``/``stop()`` are called from the controller
      thread and synchronize via queue sentinels: when ``pause()`` returns,
      no further ``sink`` call will happen until ``resume()``; when
      ``stop()`` returns, the worker thread has exited.
    - ``on_failure`` is invoked at most once, from the worker thread.
    """

    def __init__(
        self,
        backend: CaptureBackend,
        device_id: int,
        sink: Callable[[bytes], int],
        *,
        on_failure: Callable[[Exception], None],
        on_level: Callable[[float], None] | None = None,
        chunk_bytes: int = CHUNK_BYTES,
    ) -> None:
        if chunk_bytes <= 0 or chunk_bytes % SAMPLE_WIDTH != 0:
            raise ValueError("chunk_bytes must be a positive multiple of the sample width")
        self._backend = backend
        self._device_id = device_id
        self._sink = sink
        self._on_failure = on_failure
        self._on_level = on_level
        self._chunk_bytes = chunk_bytes
        self._queue: queue.Queue[bytes | _SetPaused | _Stop | _Fail] = queue.Queue(
            maxsize=_QUEUE_MAX_BLOCKS
        )
        self._paused = threading.Event()
        self._failed = threading.Event()
        self._stopped = False
        # PR-HIGH-003: serializes stop() so a concurrent/retried stop can
        # never return while the worker thread is still alive.
        self._stop_lock = threading.Lock()
        self._level = 0.0
        self._stream: CaptureStream | None = None
        self._thread: threading.Thread | None = None

    @property
    def level(self) -> float:
        """Most recent normalized input level (0.0–1.0), metered from the
        SAME stream that feeds the store (plan decision)."""
        return self._level

    @property
    def failed(self) -> bool:
        return self._failed.is_set()

    @property
    def paused(self) -> bool:
        return self._paused.is_set()

    def start(self) -> None:
        if self._thread is not None:
            raise AudioCaptureError("capture worker already started")
        self._stream = self._backend.open_stream(self._device_id, self._on_block, self._on_error)
        self._thread = threading.Thread(
            target=self._run, name="scribe-capture-worker", daemon=True
        )
        self._thread.start()

    # --- backend-thread callbacks -----------------------------------------

    def _on_block(self, block: bytes) -> None:
        self._level = pcm16_rms_level(block)
        if self._paused.is_set() or self._failed.is_set() or self._stopped:
            return  # cleanly dropped — pause/stop means no more writes
        try:
            self._queue.put_nowait(block)
        except queue.Full:
            # Never silently drop audio mid-recording: surface as a failure.
            self._on_error(CaptureOverflowError("capture queue overflowed"))

    def _on_error(self, exc: Exception) -> None:
        if self._failed.is_set() or self._stopped:
            return
        # Bypass the bounded put: control items must reach the worker even
        # when the queue is full of audio blocks.
        with self._queue.mutex:
            self._queue.queue.append(_Fail(exc))
            self._queue.not_empty.notify()

    # --- controller-thread API --------------------------------------------

    def pause(self) -> None:
        """Gate off new blocks, then wait until every already-enqueued block
        has been processed — after this returns, no sink write happens until
        resume() (in-flight chunk either fully written or cleanly dropped)."""
        if self._stopped:
            raise AudioCaptureError("cannot pause a stopped capture worker")
        self._paused.set()
        self._wait_barrier(paused=True)

    def resume(self) -> None:
        if self._failed.is_set():
            raise AudioCaptureError("cannot resume a failed capture worker")
        # PR-HIGH-002: sentinel BEFORE clearing the producer gate, so any
        # block that passes the cleared gate lands after the sentinel and is
        # processed with the worker-local gate already open.
        self._queue.put(_SetPaused(False))
        self._paused.clear()

    def stop(self, *, flush: bool) -> None:
        """Stop the stream and join the worker thread.

        ``flush=True`` (Finish): any buffered partial chunk is written as a
        final short chunk so no captured audio is lost. ``flush=False``
        (Discard/failure teardown): buffered audio is dropped.

        PR-HIGH-003: atomic and retry-safe — concurrent callers serialize on
        ``_stop_lock`` and every caller (including a retry after a join
        timeout) waits for the worker thread to actually exit before
        returning, so storage/key teardown can never race a live writer."""
        with self._stop_lock:
            if not self._stopped:
                self._stopped = True
                if self._stream is not None:
                    self._stream.stop()
                    self._stream = None
                self._queue.put(_Stop(flush))
            thread = self._thread
            if thread is not None:
                thread.join(timeout=_CONTROL_TIMEOUT_S)
                if thread.is_alive():
                    raise AudioCaptureError("capture worker failed to stop in time")
                self._thread = None

    def _wait_barrier(self, *, paused: bool) -> None:
        barrier = _SetPaused(paused)
        self._queue.put(barrier)
        if not barrier.done.wait(timeout=_CONTROL_TIMEOUT_S):
            raise AudioCaptureError("capture worker did not acknowledge control barrier")

    # --- worker thread ----------------------------------------------------

    def _run(self) -> None:
        buffer = bytearray()
        paused = False  # worker-local authoritative pause gate (PR-HIGH-002)
        try:
            while True:
                item = self._queue.get()
                if isinstance(item, _SetPaused):
                    paused = item.paused
                    item.done.set()
                    continue
                if isinstance(item, _Stop):
                    if item.flush and buffer and not self._failed.is_set():
                        try:
                            self._sink(bytes(buffer))
                        except Exception as exc:  # noqa: BLE001 - surfaced via on_failure
                            self._fail(exc)
                    item.done.set()
                    return
                if isinstance(item, _Fail):
                    # Device loss: best-effort flush of buffered audio so
                    # nothing already captured is silently lost, THEN fail.
                    if buffer and not self._failed.is_set():
                        try:
                            self._sink(bytes(buffer))
                        except Exception:  # noqa: BLE001, S110 - original failure wins
                            pass
                        finally:
                            # PR-MED-001: the failed worker survives until
                            # stop() — never retain plaintext PCM in memory
                            # past the flush attempt, even when it fails.
                            buffer.clear()
                    self._fail(item.exc)
                    continue
                if self._failed.is_set():
                    continue  # drain audio after failure
                if paused:
                    continue  # straggler block raced past the producer gate: drop
                buffer.extend(item)
                while len(buffer) >= self._chunk_bytes:
                    chunk = bytes(buffer[: self._chunk_bytes])
                    del buffer[: self._chunk_bytes]
                    try:
                        self._sink(chunk)
                    except Exception as exc:  # noqa: BLE001 - surfaced via on_failure
                        self._fail(exc)
                        buffer.clear()  # PR-MED-001: no plaintext retention post-failure
                        break
        finally:
            self._release_waiters()

    def _fail(self, exc: Exception) -> None:
        if self._failed.is_set():
            return
        self._failed.set()
        if self._stream is not None:
            self._stream.stop()
            self._stream = None
        self._on_failure(exc)

    def _release_waiters(self) -> None:
        """On worker exit, drain the queue so no controller thread hangs on
        a barrier/stop sentinel that will never be processed."""
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                return
            if isinstance(item, _SetPaused | _Stop):
                item.done.set()
