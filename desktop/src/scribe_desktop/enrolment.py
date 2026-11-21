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

The guided enrolment (stronger-voice plan D3, Task 1.1) records the script's
parts one ``record_enrolment`` call at a time and embeds each with
``enrol_part`` (``enrol`` unchanged inside it, its segment vectors kept). The
pure functions below turn the parts into the stored vector
(``combine_parts``: the normalised equal-weight mean), the part-consistency
figures and the part to record again (``part_consistency``,
``weakest_part``), and the strength share shown after saving
(``strength_share``). They are plain-Python arithmetic over numbers, so they
need neither numpy nor the offline kill-switches.
"""

from __future__ import annotations

import math
import queue
from collections.abc import Callable, Sequence
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
from scribe_desktop.speaker_embedding import ATTRIBUTION_THRESHOLD, SpeakerEmbedder
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
# Stronger-voice plan D3 and Validation (dated decision): the part-consistency
# figure, calibrated at Task 0.5b (2026-11-21) by the derivation frozen at
# Task 0.2 — the lowest part-against-the-rest cosine over the practitioner's
# two takes (0.701) less 0.05, never below 0.50. A part scoring under it is
# recorded again, once. A calibration, not a bar: a new value is a new dated
# decision with the measurement repeated.
PART_CONSISTENCY_FIGURE: Final = 0.651


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
            on_error(
                CaptureOverflowError(
                    "enrolment capture queue overflowed", detail_code="queue_full"
                )
            )

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


# --- the guided enrolment's parts (stronger-voice plan D3, Task 1.1) ----------------


@dataclass(frozen=True)
class PartEmbedding:
    """One script part's embedding, numbers only: ``vector`` is the part's
    L2-normalised mean (``enrol``'s), ``speech_seconds`` ``enrol``'s figure
    (the one stored), and ``segment_vectors`` the per-segment vectors that
    mean was made from (for the strength share)."""

    vector: Any
    speech_seconds: float
    segment_vectors: tuple[Any, ...]


class _SegmentVectorRecorder:
    """An embedder wrapper that keeps each vector it returns, so ``enrol``
    runs unchanged and its per-segment vectors are kept beside its mean.
    It holds vectors only, never the PCM it is asked to embed."""

    def __init__(self, inner: SpeakerEmbedder) -> None:
        self._inner = inner
        self.vectors: list[Any] = []

    @property
    def model_id(self) -> str:
        return self._inner.model_id

    @property
    def model_sha256(self) -> str:
        return self._inner.model_sha256

    @property
    def embedding_dim(self) -> int:
        return self._inner.embedding_dim

    def embed(self, pcm16: bytes) -> Any:
        np = _numpy()
        vector = np.asarray(self._inner.embed(pcm16), dtype=np.float32)
        self.vectors.append(vector)
        return vector


def enrol_part(
    pcm16: bytes,
    embedder: SpeakerEmbedder,
    *,
    frame_probability: FrameProbabilityFn | None = None,
) -> PartEmbedding:
    """``enrol`` over one part's PCM, with its per-segment vectors kept. The
    same errors as ``enrol``; holds no reference to the PCM after returning."""
    recorder = _SegmentVectorRecorder(embedder)
    vector, speech_seconds = enrol(pcm16, recorder, frame_probability=frame_probability)
    return PartEmbedding(
        vector=vector, speech_seconds=speech_seconds, segment_vectors=tuple(recorder.vectors)
    )


def _finite_floats(vector: Any) -> tuple[float, ...] | None:
    values = tuple(float(value) for value in vector)
    return values if all(math.isfinite(value) for value in values) else None


def _unit(values: Sequence[float]) -> tuple[float, ...] | None:
    """The unit vector, or None when it has no direction (zero or non-finite)."""
    try:
        norm = math.sqrt(math.fsum(value * value for value in values))
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(norm) or norm == 0.0:
        return None
    return tuple(value / norm for value in values)


def _unit_mean(vectors: Sequence[Any]) -> tuple[float, ...] | None:
    """The unit equal-weight mean of ``vectors``; None when there are none, a
    vector is not finite, or the mean has no direction."""
    rows: list[tuple[float, ...]] = []
    for vector in vectors:
        values = _finite_floats(vector)
        if values is None:
            return None
        rows.append(values)
    if not rows:
        return None
    if any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("the part vectors differ in length")
    try:
        mean = [math.fsum(column) / len(rows) for column in zip(*rows, strict=True)]
    except (OverflowError, ValueError):
        return None
    return _unit(mean)


def _cosine(vector: Any, reference_unit: Sequence[float]) -> float:
    """The pipeline's cosine rule (``transcription._cosine``): -1 for a vector
    with no direction, bounded to [-1, 1] only against float dust."""
    values = _finite_floats(vector)
    unit = _unit(values) if values is not None else None
    if unit is None:
        return -1.0
    if len(unit) != len(reference_unit):
        raise ValueError("a segment vector and the reference differ in length")
    value = math.fsum(a * b for a, b in zip(unit, reference_unit, strict=True))
    if not math.isfinite(value):
        return -1.0
    return max(-1.0, min(1.0, value))


def combine_parts(vectors: Sequence[Any]) -> tuple[float, ...]:
    """The stored profile vector (D3): the normalised equal-weight mean of the
    captured parts' vectors (final attempts only). A left-out part is absent,
    so the others keep equal weights; speech seconds never weight a part.
    ``EnrolmentError`` when there is no part, or the mean is zero or not
    finite."""
    mean = _unit_mean(vectors)
    if mean is None:
        raise EnrolmentError("the part vectors give no usable voice profile; record again")
    return mean


def part_consistency(vectors: Sequence[Any]) -> tuple[float, ...]:
    """Each captured part's cosine against the unit mean of the OTHER captured
    parts' vectors, in part order; -1 where the others have no direction (a
    lone part has no others)."""
    figures: list[float] = []
    for index, vector in enumerate(vectors):
        others = [other for position, other in enumerate(vectors) if position != index]
        reference = _unit_mean(others)
        figures.append(-1.0 if reference is None else _cosine(vector, reference))
    return tuple(figures)


def weakest_part(
    figures: Sequence[float], figure: float = PART_CONSISTENCY_FIGURE
) -> int | None:
    """The position of the lowest figure under ``figure`` (the earlier on a
    tie), or None when no figure is under it. A figure equal to ``figure`` is
    not under it."""
    lowest: int | None = None
    for index, value in enumerate(figures):
        if value < figure and (lowest is None or value < figures[lowest]):
            lowest = index
    return lowest


def strength_share(parts: Sequence[PartEmbedding]) -> float:
    """The strength line's one number (D3), computed in memory and never
    stored: the share of the parts' segment vectors scoring at or above the
    shipped pass mark (``ATTRIBUTION_THRESHOLD``) against the profile built
    WITHOUT their own part (leave one part out). 0.0 when no segment exists."""
    matched = 0
    total = 0
    for index, part in enumerate(parts):
        others = [other.vector for position, other in enumerate(parts) if position != index]
        reference = _unit_mean(others)
        for segment in part.segment_vectors:
            total += 1
            if reference is not None and _cosine(segment, reference) >= ATTRIBUTION_THRESHOLD:
                matched += 1
    return matched / total if total else 0.0


__all__ = [
    "DEFAULT_MAX_SECONDS",
    "DEFAULT_TARGET_SPEECH_SECONDS",
    "PART_CONSISTENCY_FIGURE",
    "EnrolmentCancelledError",
    "EnrolmentCaptureError",
    "EnrolmentError",
    "EnrolmentProgress",
    "EnrolmentTooShortError",
    "PartEmbedding",
    "combine_parts",
    "enrol",
    "enrol_part",
    "part_consistency",
    "record_enrolment",
    "strength_share",
    "weakest_part",
]
