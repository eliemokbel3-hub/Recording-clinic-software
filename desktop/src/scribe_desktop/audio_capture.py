"""Audio capture (Phase 2 Step 3).

Capture stack per the plan Design Decision: ``sounddevice`` (PortAudio;
on Windows its default host API is MME, which is what the app's streams
were measured on — capture-overflow plan Task 0.2), 16 kHz mono PCM16,
~1 s chunks, level metering from the same stream.

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

import contextlib
import logging
import queue
import threading
import time
from array import array
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final, Protocol

from scribe_desktop.logging_setup import log_event

SAMPLE_RATE: Final = 16_000
CHANNELS: Final = 1
SAMPLE_WIDTH: Final = 2  # PCM16
# ~1 s of 16 kHz mono PCM16 per chunk (plan: ~1 s chunks).
CHUNK_BYTES: Final = SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH
# Backend block size: 100 ms keeps level metering responsive.
BLOCK_FRAMES: Final = SAMPLE_RATE // 10

_QUEUE_MAX_BLOCKS: Final = 256  # ~25 s backlog bound; overflow -> failure, never silent loss
_CONTROL_TIMEOUT_S: Final = 10.0

# Capture-overflow plan D1 (decided 2026-11-26, Task 0.3, from the Task 0.2
# measurement): the input buffer asked of PortAudio for a RECORDING's stream
# on an MME device. On MME the buffer count is ceil(latency / 0.1 s) + 1, so
# a callback may run about this late before a frame is dropped; the default
# (0.18 s) allows about 0.2 s. The value changes only by a new dated
# decision with ``scripts/measure-capture-stall.py`` run again.
INPUT_LATENCY_SECONDS: Final = 2.5
# D4: a failure carries the largest of this many most recent callback gaps.
_RECENT_GAPS: Final = 3
# D4: a stop whose last callback is older than this dropped a backlog.
_BACKLOG_AGE_SECONDS: Final = 0.25
# D4: PortAudio's host API names, as this module's fixed words.
_HOST_WORDS: Final[dict[str, str]] = {
    "MME": "mme",
    "Windows DirectSound": "directsound",
    "Windows WASAPI": "wasapi",
    "Windows WDM-KS": "wdmks",
}


# Installation plan round 35 MED-001: which capture path raised, as a fixed
# word. ``SessionController`` logs it beside the exception's type name when a
# recording fails — never the message, which can carry PortAudio's text.
CAPTURE_DETAIL_CODES: Final[frozenset[str]] = frozenset(
    {
        "unspecified",
        "open_failed",  # the device would not open
        "stream_ended",  # PortAudio ended the stream (device lost)
        "queue_full",  # the worker fell ~25 s behind
        "status_input_overflow",  # PortAudio dropped input frames
        "status_input_underflow",
        "status_other",  # a status flag this module does not name
    }
)


class AudioCaptureError(Exception):
    """Base class for capture failures. ``detail_code`` is one of
    ``CAPTURE_DETAIL_CODES`` (any other value reads as ``unspecified``).
    ``gap_ms`` (capture-overflow plan D4) is the largest recent gap between
    two callbacks when the failure was a status flag, else ``None``."""

    def __init__(
        self, *args: object, detail_code: str = "unspecified", gap_ms: int | None = None
    ) -> None:
        super().__init__(*args)
        self.detail_code = detail_code if detail_code in CAPTURE_DETAIL_CODES else "unspecified"
        self.gap_ms = gap_ms if type(gap_ms) is int and gap_ms >= 0 else None


def status_detail_code(status: object) -> str:
    """The detail code for a truthy PortAudio callback status: the input
    flag it carries (``sounddevice.CallbackFlags`` attributes), else
    ``status_other``. Built from this module's words, never ``str(status)``."""
    if bool(getattr(status, "input_overflow", False)):
        return "status_input_overflow"
    if bool(getattr(status, "input_underflow", False)):
        return "status_input_underflow"
    return "status_other"


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


def _milliseconds(seconds: float) -> int:
    return round(seconds * 1000)


def _host_word(sd: Any, info: Any) -> str:
    """The fixed word for one device entry's host API; ``other`` for
    anything unresolved (a fake module, a name this module does not list)."""
    try:
        name = sd.query_hostapis(int(info["hostapi"]))["name"]
    except Exception:  # unresolved, whatever the reason: the caller opens as before
        return "other"
    return _HOST_WORDS.get(str(name), "other")


def _device_host_word(sd: Any, device_id: int) -> str:
    try:
        info = sd.query_devices(device_id)
    except Exception:  # as ``_host_word``
        return "other"
    return _host_word(sd, info)


class _SoundDeviceStream:
    """One open attempt's handle: the stream, whether WE stopped it, and the
    callback gaps of its life (capture-overflow plan D4). The gaps are
    stamped on PortAudio's thread and read on the caller's; every value is
    a number, and the closed line is written once per stream, in a
    ``finally`` after ``abort()`` and ``close()``."""

    def __init__(
        self,
        device_id: int,
        clock: Callable[[], float],
        logger: logging.Logger | None,
    ) -> None:
        self._stream: Any = None
        self.attached = False
        self.stopped_by_us = False
        self._device_id = device_id
        self._clock = clock
        self._logger = logger
        self._count = 0
        self._last_entry: float | None = None
        self._recent: deque[float] = deque(maxlen=_RECENT_GAPS)
        self._longest = 0.0
        self._stop_lock = threading.Lock()

    def attach(self, stream: object) -> None:
        self._stream = stream
        self.attached = True

    def stamp(self) -> None:
        """Called first in every callback: count it and record its gap."""
        now = self._clock()
        last = self._last_entry
        if last is not None:
            gap = now - last
            self._recent.append(gap)
            if gap > self._longest:
                self._longest = gap
        self._last_entry = now
        self._count += 1

    def recent_gap_ms(self) -> int | None:
        """The largest of the most recent gaps, this callback's included;
        ``None`` before the second callback."""
        return _milliseconds(max(self._recent)) if self._recent else None

    def discard(self) -> None:
        """Give up an attempt that would not open (D2): its ``finished``
        callback must not read as device loss, and it logs nothing."""
        with self._stop_lock:
            self.stopped_by_us = True
            stream, self._stream = self._stream, None
        if stream is not None:
            with contextlib.suppress(Exception):
                stream.close()

    def stop(self) -> None:
        with self._stop_lock:
            self.stopped_by_us = True
            stream, self._stream = self._stream, None
        if stream is None:
            return
        now = self._clock()
        last = self._last_entry
        age = None if last is None else now - last
        try:
            stream.abort()
        finally:
            try:
                stream.close()
            finally:
                self._log_closed(age)

    def _log_closed(self, age: float | None) -> None:
        if self._logger is None:
            return
        if age is not None and age > _BACKLOG_AGE_SECONDS:
            # D3's residue: audio still waiting behind a late callback was
            # dropped by this stop.
            log_event(
                self._logger,
                "capture_stream",
                state="backlog_dropped",
                device_id=self._device_id,
                duration_ms=_milliseconds(age),
            )
        log_event(
            self._logger,
            "capture_stream",
            state="closed",
            device_id=self._device_id,
            count=self._count,
            duration_ms=_milliseconds(self._longest),
        )


class SoundDeviceBackend:
    """PortAudio capture via ``sounddevice`` (lazy import); MME on Windows.

    Capture-overflow plan: ``input_latency`` is the buffer asked for on an
    MME device (D1; ``None`` opens exactly as before — the level monitor's
    and enrolment's instance). ``logger`` receives the ``capture_stream``
    lines (D4; none without one). ``clock`` stamps the callbacks."""

    def __init__(
        self,
        logger: logging.Logger | None = None,
        input_latency: float | None = INPUT_LATENCY_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._logger = logger
        self._input_latency = input_latency
        self._clock = clock

    def list_input_devices(self) -> list[AudioDevice]:
        """The input entries. Capture-overflow plan D8: when any of them is
        on MME only those are listed (each microphone once, and every listed
        entry reports dropped frames); otherwise every entry, as before.
        The ids are PortAudio's own either way."""
        import sounddevice as sd

        default_input = sd.default.device[0]
        entries: list[tuple[AudioDevice, str]] = []
        for index, info in enumerate(sd.query_devices()):
            if int(info.get("max_input_channels", 0)) < CHANNELS:
                continue
            entries.append(
                (
                    AudioDevice(
                        device_id=index,
                        name=str(info.get("name", f"device {index}")),
                        is_default=index == default_input,
                    ),
                    _host_word(sd, info),
                )
            )
        if any(host == "mme" for _device, host in entries):
            return [device for device, host in entries if host == "mme"]
        return [device for device, _host in entries]

    def open_stream(
        self,
        device_id: int,
        on_block: Callable[[bytes], None],
        on_error: Callable[[Exception], None],
    ) -> CaptureStream:
        import sounddevice as sd

        # Host unused without a buffer or logger: the level meter opens as before.
        host = (
            _device_host_word(sd, device_id)
            if (self._input_latency is not None or self._logger is not None)
            else "other"
        )
        latency = self._input_latency if host == "mme" else None
        if latency is not None:
            try:
                handle = self._open(sd, device_id, on_block, on_error, latency)
            except sd.PortAudioError:
                # D2, never worse than before: ONE more open, with the default.
                pass
            else:
                self._log_open("opened", host, device_id, duration_ms=_milliseconds(latency))
                return handle
        try:
            handle = self._open(sd, device_id, on_block, on_error, None)
        except sd.PortAudioError as exc:
            raise DeviceLostError(
                f"failed opening input device {device_id}: {exc}", detail_code="open_failed"
            ) from exc
        self._log_open("default_latency", host, device_id)
        return handle

    def _log_open(self, state: str, host: str, device_id: int, **fields: int) -> None:
        if self._logger is not None:
            log_event(
                self._logger,
                "capture_stream",
                state=state,
                detail_code=host,
                device_id=device_id,
                **fields,
            )

    def _open(
        self,
        sd: Any,
        device_id: int,
        on_block: Callable[[bytes], None],
        on_error: Callable[[Exception], None],
        latency: float | None,
    ) -> _SoundDeviceStream:
        """One open attempt with its own handle. ``sd.PortAudioError`` from
        the constructor or from ``start()`` leaves nothing open."""
        handle = _SoundDeviceStream(device_id, self._clock, self._logger)

        def callback(indata: Any, frames: int, time_info: object, status: object) -> None:
            handle.stamp()
            # Deliver the block first so already-captured audio is never
            # lost, THEN surface any status flag (input overflow = frames
            # dropped device-side) as a recoverable failure — a consultation
            # must never contain a silent, undetected gap (PR-HIGH-004,
            # plan Critical Constraint: never silent data loss).
            on_block(bytes(indata))
            if status:
                on_error(
                    CaptureOverflowError(
                        f"device reported dropped frames (status: {status})",
                        detail_code=status_detail_code(status),
                        gap_ms=handle.recent_gap_ms(),
                    )
                )

        def finished() -> None:
            # PortAudio fires finished_callback when the stream ends. If WE
            # did not stop it, the device died mid-session.
            if handle.attached and not handle.stopped_by_us:
                on_error(
                    DeviceLostError(
                        "input stream ended unexpectedly (device lost)",
                        detail_code="stream_ended",
                    )
                )

        arguments: dict[str, Any] = {
            "samplerate": SAMPLE_RATE,
            "blocksize": BLOCK_FRAMES,
            "device": device_id,
            "channels": CHANNELS,
            "dtype": "int16",
            "callback": callback,
            "finished_callback": finished,
        }
        if latency is not None:
            arguments["latency"] = latency
        try:
            stream = sd.RawInputStream(**arguments)
            handle.attach(stream)
            stream.start()
        except BaseException:  # a refusal (PortAudioError) or an interruption
            handle.discard()
            raise
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
            raise DeviceLostError(f"no such input device {device_id}", detail_code="open_failed")
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
        self._on_error(exc or DeviceLostError("mock device lost", detail_code="stream_ended"))


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
        chunk_bytes: int = CHUNK_BYTES,
    ) -> None:
        # Round 42 MED-007: the never-invoked `on_level` callback parameter
        # was removed — level metering is poll-based via the `level`
        # property (the SessionController reads it).
        if chunk_bytes <= 0 or chunk_bytes % SAMPLE_WIDTH != 0:
            raise ValueError("chunk_bytes must be a positive multiple of the sample width")
        self._backend = backend
        self._device_id = device_id
        self._sink = sink
        self._on_failure = on_failure
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
            self._on_error(
                CaptureOverflowError("capture queue overflowed", detail_code="queue_full")
            )

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
