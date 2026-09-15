"""Voice enrolment capture and embedding (practitioner-profile plan Task 1.3).

A dedicated IN-MEMORY path (plan Design Decision D8): ``record_enrolment``
opens ``CaptureBackend.open_stream`` — the microphone screen's monitor-stream
shape, NOT a ``CaptureWorker`` and NOT ``SessionController.start`` — into a
byte buffer, gates it with the VAD to count speech seconds, and returns the
PCM once the speech target is met or the capture cap is reached; ``enrol``
turns that PCM into one L2-normalised vector (the mean of the per-VAD-segment
embeddings) and the speech seconds it was made from. Neither function creates
a session, touches any store, or writes a file; the caller drops the PCM
after ``enrol`` (the Practitioner tab, Phase 3). On every exit of
``record_enrolment`` — success or failure — the stream is stopped, the
working buffers are cleared and the VAD's recurrent state is reset, so no
PCM-derived state outlives the call inside this module; the returned bytes
object is the caller's to drop.

The whole capture -> embed -> save sequence runs under
``SessionController.begin_enrolment()`` (D15): the controller refuses
Start/Resume while the activity is held, the microphone screen closes its
idle monitor and suppresses the monitor poll, and ``begin_enrolment`` itself
refuses while a session is active, a discard is in flight, or a registered
blocker (the benchmark worker) reports busy. This module does not take the
lease itself — the caller that owns the UI lifecycle does — so a test can
drive it with a mock backend and no controller.

Threading: backend callbacks arrive on the device thread and are queued; the
consumer loop runs on the CALLING thread (a ``TaskThread`` in the app), which
is where ``on_progress`` is invoked — the caller marshals to the GUI thread.
The loop blocks on the queue with a bounded wait, so a stream that never
delivers a block fails typed rather than hanging.
"""

from __future__ import annotations

import queue
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from scribe_desktop.audio_capture import (
    SAMPLE_RATE,
    SAMPLE_WIDTH,
    AudioCaptureError,
    CaptureBackend,
    CaptureOverflowError,
    pcm16_rms_level,
)
from scribe_desktop.benchmark import assert_offline_env
from scribe_desktop.speaker_embedding import SpeakerEmbedder
from scribe_desktop.speech import (
    FRAME_BYTES,
    FRAME_SECONDS,
    START_THRESHOLD,
    FrameProbabilityFn,
    SileroVad,
    segment_pcm,
)

DEFAULT_TARGET_SPEECH_SECONDS: Final = 30.0
DEFAULT_MAX_SECONDS: Final = 90.0
# A stream that delivers nothing for this long is dead, whatever the backend
# says (mirrors the capture worker's control timeout).
_BLOCK_TIMEOUT_S: Final = 10.0
_QUEUE_MAX_BLOCKS: Final = 256  # ~25 s backlog bound; overflow -> failure, never silent loss
_BYTES_PER_SECOND: Final = SAMPLE_RATE * SAMPLE_WIDTH


class EnrolmentError(Exception):
    """Base class for enrolment failures."""


class EnrolmentTooShortError(EnrolmentError):
    """Less speech than the target was captured (or none was found)."""


class EnrolmentCaptureError(EnrolmentError):
    """The device could not be opened, died, overflowed, or went silent."""


class EnrolmentCancelledError(EnrolmentError):
    """The caller's ``should_stop`` predicate ended the capture."""


@dataclass(frozen=True)
class EnrolmentProgress:
    """Numbers only: speech seconds counted so far, seconds captured so far,
    and the last block's normalised level (for a live meter)."""

    speech_seconds: float
    captured_seconds: float
    level: float


class _Failed:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc


def _numpy() -> Any:
    assert_offline_env()  # before EVERY ML-stack import (the binding pattern)
    import numpy

    return numpy


def _reset_of(frame_probability: FrameProbabilityFn) -> Callable[[], None] | None:
    """The backend's ``reset`` when ``frame_probability`` is a bound method of
    a resettable backend (``SileroVad.frame_probability``) — the
    ``speech.segment_pcm`` contract."""
    owner = getattr(frame_probability, "__self__", None)
    reset = getattr(owner, "reset", None)
    return reset if callable(reset) else None


def record_enrolment(
    backend: CaptureBackend,
    device_id: int,
    *,
    frame_probability: FrameProbabilityFn | None = None,
    target_speech_seconds: float = DEFAULT_TARGET_SPEECH_SECONDS,
    max_seconds: float = DEFAULT_MAX_SECONDS,
    on_progress: Callable[[EnrolmentProgress], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> bytes:
    """Capture until ``target_speech_seconds`` of VAD-detected speech have
    been heard, returning the whole captured PCM (16 kHz mono PCM16, speech
    and pauses alike — ``enrol`` re-segments it). Speech is counted per VAD
    frame at the segmenter's start threshold, a running estimate for the
    progress meter; the authoritative figure is ``enrol``'s.

    Raises ``EnrolmentTooShortError`` when ``max_seconds`` of audio arrive
    with less speech than the target, ``EnrolmentCaptureError`` when the
    device cannot be opened, dies, overflows the queue or delivers nothing
    for ten seconds, and ``EnrolmentCancelledError`` when ``should_stop``
    returns True. ``frame_probability`` defaults to a fresh ``SileroVad``
    (the offline kill-switches must already be asserted).
    """
    if not 0.0 < target_speech_seconds <= max_seconds:
        raise ValueError("need 0 < target_speech_seconds <= max_seconds")
    probability = (
        frame_probability if frame_probability is not None else SileroVad().frame_probability
    )
    reset = _reset_of(probability)
    if reset is not None:
        reset()
    blocks: queue.Queue[bytes | _Failed] = queue.Queue(maxsize=_QUEUE_MAX_BLOCKS)
    # Peer round 14 PR-MED-019: the FIRST capture failure, held OUTSIDE the
    # queue (written under the queue's mutex before the wake-up item is
    # enqueued) so a failure reported behind pending audio cannot be bypassed
    # by an earlier block reaching the target — every decision exit and the
    # post-shutdown check consult this slot, never only the queue.
    failure: list[Exception] = []

    def on_error(exc: Exception) -> None:
        # Bypass the bounded put: the failure must reach the consumer even
        # when the queue is full of audio blocks (the capture worker's idiom).
        with blocks.mutex:
            if not failure:
                failure.append(exc)
            blocks.queue.append(_Failed(exc))
            blocks.not_empty.notify()

    def on_block(block: bytes) -> None:
        try:
            blocks.put_nowait(block)
        except queue.Full:
            on_error(CaptureOverflowError("enrolment capture queue overflowed"))

    def raise_if_failed() -> None:
        with blocks.mutex:
            pending = failure[0] if failure else None
        if pending is not None:
            raise EnrolmentCaptureError(f"microphone failed: {pending}") from pending

    def raise_if_cancelled() -> None:
        # Peer round 15 PR-MED-020: polled at the loop top, again before both
        # decision exits (a Cancel requested from the target-reaching
        # ``on_progress`` is honoured, not returned over) and again after
        # shutdown on the success path. Called OUTSIDE the queue mutex — the
        # caller's predicate may take its own locks.
        if should_stop is not None and should_stop():
            raise EnrolmentCancelledError("enrolment cancelled")

    buffer = bytearray()
    remainder = bytearray()  # a partial VAD frame carried between blocks
    speech_seconds = 0.0
    max_bytes = int(max_seconds * SAMPLE_RATE) * SAMPLE_WIDTH
    succeeded = False
    try:
        stream = backend.open_stream(device_id, on_block, on_error)
    except AudioCaptureError as exc:
        raise EnrolmentCaptureError(f"could not open the microphone: {exc}") from exc
    try:
        while True:
            raise_if_cancelled()
            try:
                item = blocks.get(timeout=_BLOCK_TIMEOUT_S)
            except queue.Empty:
                raise EnrolmentCaptureError(
                    f"no audio arrived from the microphone for {_BLOCK_TIMEOUT_S:.0f} s"
                ) from None
            if isinstance(item, _Failed):
                raise EnrolmentCaptureError(f"microphone failed: {item.exc}") from item.exc
            buffer.extend(item)
            remainder.extend(item)
            while len(remainder) >= FRAME_BYTES:
                frame = bytes(remainder[:FRAME_BYTES])
                del remainder[:FRAME_BYTES]
                if probability(frame) >= START_THRESHOLD:
                    speech_seconds += FRAME_SECONDS
            captured_seconds = len(buffer) / _BYTES_PER_SECOND
            if on_progress is not None:
                on_progress(
                    EnrolmentProgress(speech_seconds, captured_seconds, pcm16_rms_level(item))
                )
            # A failure reported while this block was being processed takes
            # precedence over BOTH decisions below (target reached, cap hit);
            # a cancellation requested meanwhile (``on_progress`` may set it
            # synchronously) comes next, before either decision.
            raise_if_failed()
            raise_if_cancelled()
            if speech_seconds >= target_speech_seconds:
                succeeded = True
                return bytes(buffer)
            if len(buffer) >= max_bytes:
                raise EnrolmentTooShortError(
                    f"only {speech_seconds:.1f} s of speech in {captured_seconds:.0f} s of "
                    f"audio; {target_speech_seconds:.0f} s of speech are needed - try "
                    "again closer to the microphone"
                )
    finally:
        try:
            stream.stop()
        finally:
            # PR-MED-001 discipline: no plaintext PCM (or PCM-derived VAD
            # state) survives this call inside the module, whatever the exit.
            buffer.clear()
            remainder.clear()
            if reset is not None:
                reset()
        if succeeded:
            # Checked AFTER shutdown: no callback can fire once the stream is
            # stopped, so a failure recorded between the in-loop check and the
            # stop is the last one possible — and it wins over the successful
            # return; a cancellation that arrived meanwhile wins next. On a
            # failing exit the original error stands.
            raise_if_failed()
            raise_if_cancelled()


def enrol(
    pcm16: bytes,
    embedder: SpeakerEmbedder,
    *,
    frame_probability: FrameProbabilityFn | None = None,
) -> tuple[Any, float]:
    """``(vector, speech_seconds)``: the L2-normalised mean of the embedder's
    vectors over every VAD segment of ``pcm16`` (``speech.segment_pcm`` with
    its shipped thresholds), and the seconds of speech those segments hold.
    ``EnrolmentTooShortError`` when no speech is detected; ``EnrolmentError``
    when the segment vectors cancel to a zero mean (no usable direction).
    Holds no reference to the PCM after returning."""
    if len(pcm16) < FRAME_BYTES:
        raise EnrolmentTooShortError("no audio to enrol from")
    probability = (
        frame_probability if frame_probability is not None else SileroVad().frame_probability
    )
    segments = segment_pcm([pcm16], probability)
    if not segments:
        raise EnrolmentTooShortError("no speech detected in the enrolment audio")
    np = _numpy()
    vectors: list[Any] = []
    speech_seconds = 0.0
    for segment in segments:
        start = int(segment.start_seconds * SAMPLE_RATE) * SAMPLE_WIDTH
        end = min(int(segment.end_seconds * SAMPLE_RATE) * SAMPLE_WIDTH, len(pcm16))
        piece = pcm16[start:end]
        if len(piece) < FRAME_BYTES:
            continue  # a padded tail past the audio end: nothing to embed
        vectors.append(np.asarray(embedder.embed(piece), dtype=np.float32))
        speech_seconds += len(piece) / _BYTES_PER_SECOND
    if not vectors:
        raise EnrolmentTooShortError("no speech detected in the enrolment audio")
    mean = np.stack(vectors).mean(axis=0)
    norm = float(np.linalg.norm(mean))
    if not norm > 0.0 or not np.isfinite(norm):
        raise EnrolmentError("the enrolment vectors cancel out; record again")
    return (mean / norm).astype(np.float32), speech_seconds


__all__ = [
    "DEFAULT_MAX_SECONDS",
    "DEFAULT_TARGET_SPEECH_SECONDS",
    "EnrolmentCancelledError",
    "EnrolmentCaptureError",
    "EnrolmentError",
    "EnrolmentProgress",
    "EnrolmentTooShortError",
    "enrol",
    "record_enrolment",
]
