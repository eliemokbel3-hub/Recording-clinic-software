"""Speech pipeline scaffolding: VAD segmentation + the SpeechProvider seam.

Phase 2 Step 7 (plan): silero-VAD over the decrypted chunk stream from the
session store, producing speech segments with timestamps. The full
transcription pipeline (Whisper, uncertainty marks, speaker labels,
``transcript.enc``) is Step 9; this module provides:

- ``SpeechSegment`` / ``TranscribedWord`` value types and the
  ``SpeechProvider`` interface (PLAN.md core type — "implemented initially
  by local Whisper"; Step 9 supplies the real implementation).
- ``MockSpeechProvider`` for CI and UI scaffolding (no ML stack needed).
- ``SileroVad``: the downloaded silero-vad ONNX model (v5 signature:
  ``input`` = 64-sample context + 512-sample frame, recurrent ``state``)
  run through onnxruntime with the offline kill-switches asserted BEFORE
  any ML import (plan Design Decision "Runtime offline enforcement").
- A pure-Python hysteresis segmenter (``segment_probabilities``) that is
  fully unit-testable without the model, plus ``segment_pcm`` /
  ``segment_session_audio`` wiring frames -> probabilities -> segments,
  the latter fed from ``session_store.iter_chunks`` (decrypt-stream).

Constraints honoured (plan Critical Constraints / executor facts):
- Lazy ML imports: this module imports numpy/onnxruntime only inside
  functions, so it stays importable on CI without the ``[ml]`` extra.
- Zero network I/O: the model is loaded from an explicit local path; the
  offline env kill-switches are asserted before onnxruntime is imported.
- No clinical data in logs: nothing in this module logs audio, PCM, or
  transcript content — only ``log_event``-whitelisted keys would ever be
  used, and this scaffolding logs nothing at all.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from scribe_desktop.benchmark import assert_offline_env, default_models_root
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import iter_chunks

# Silero VAD v5 contract for 16 kHz input: 512-sample frames with a
# 64-sample rolling context prepended (matches the upstream OnnxWrapper).
SAMPLE_RATE = 16_000
FRAME_SAMPLES = 512
CONTEXT_SAMPLES = 64
BYTES_PER_SAMPLE = 2  # PCM16
FRAME_BYTES = FRAME_SAMPLES * BYTES_PER_SAMPLE
FRAME_SECONDS = FRAME_SAMPLES / SAMPLE_RATE

# Hysteresis defaults, tuned on the SAPI-synthesized probe (speech frames
# score ~0.7 mean / ~1.0 peaks, silence < 0.02 against the cached model).
# RE-VERIFIED 2026-07-31 on TRUE-speed audio: the original probe was fed SAPI's
# 22050 Hz output as if it were 16 kHz (0.726x speed — see tests/sapi_fixture.py).
# Re-probed at the correct rate over three fixtures, the distribution is
# unchanged — frames above start threshold mean 0.98 (min 0.52), whole-span mean
# 0.66-0.77, silence floor mean 0.003 / max 0.012, and detected coverage of the
# spoken span rose slightly (81->83%, 72->75%, 87->88%). Thresholds UNCHANGED.
START_THRESHOLD = 0.50
END_THRESHOLD = 0.35
MIN_SPEECH_SECONDS = 0.25
MIN_SILENCE_SECONDS = 0.35
PAD_SECONDS = 0.10


class SpeechError(Exception):
    """Base class for speech-pipeline failures."""


class VadModelError(SpeechError):
    """The VAD model is missing or unusable."""


@dataclass(frozen=True)
class SpeechSegment:
    """A detected span of speech, in seconds from the start of the audio."""

    start_seconds: float
    end_seconds: float

    def __post_init__(self) -> None:
        if self.start_seconds < 0 or self.end_seconds <= self.start_seconds:
            raise ValueError("segment must satisfy 0 <= start < end")

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


@dataclass(frozen=True)
class TranscribedWord:
    """One transcribed word with timing and backend confidence (Step 9 fills
    uncertainty marking on top of ``probability``)."""

    text: str
    start_seconds: float
    end_seconds: float
    probability: float


class SpeechProvider(Protocol):
    """PLAN.md core type: local speech-to-text over one contiguous audio
    span — a packed ~30 s transcription window of consecutive VAD segments
    (Step 13 batching), or a lone segment.

    Implemented initially by local Whisper (Step 9); ``MockSpeechProvider``
    stands in for CI and scaffolding. ``pcm`` is 16 kHz mono PCM16; word
    times in the result are relative to the START of the given ``pcm``.
    """

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        ...


class MockSpeechProvider:
    """Deterministic, ML-free SpeechProvider for CI and UI scaffolding."""

    def __init__(self, words_per_second: float = 2.0, text: str = "mock") -> None:
        if words_per_second <= 0:
            raise ValueError("words_per_second must be positive")
        self._wps = words_per_second
        self._text = text

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        duration = len(pcm) / (BYTES_PER_SAMPLE * sample_rate)
        count = max(1, int(duration * self._wps)) if pcm else 0
        step = duration / count if count else 0.0
        return [
            TranscribedWord(
                text=f"{self._text}{i}",
                start_seconds=i * step,
                end_seconds=(i + 1) * step,
                probability=1.0,
            )
            for i in range(count)
        ]


def iter_frames(chunks: Iterable[bytes]) -> Iterator[bytes]:
    """Reassemble arbitrary-sized PCM16 chunks into exact VAD frames.

    Yields ``FRAME_BYTES``-sized frames; a final partial frame is
    zero-padded (silence) so no tail audio is dropped.
    """
    buffer = bytearray()
    for chunk in chunks:
        buffer.extend(chunk)
        while len(buffer) >= FRAME_BYTES:
            yield bytes(buffer[:FRAME_BYTES])
            del buffer[:FRAME_BYTES]
    if buffer:
        yield bytes(buffer) + b"\0" * (FRAME_BYTES - len(buffer))


# A frame-probability backend: PCM16 frame bytes -> speech probability.
FrameProbabilityFn = Callable[[bytes], float]


class SileroVad:
    """Silero VAD v5 (ONNX) frame-probability backend.

    Loads the model from the local cache only (never the network); the
    offline kill-switches are asserted BEFORE onnxruntime is imported.
    Stateful across frames (recurrent state + 64-sample context) — call
    ``reset()`` between independent audio streams.
    """

    def __init__(self, model_path: Path | None = None) -> None:
        assert_offline_env()
        path = model_path if model_path is not None else default_vad_model_path()
        # Defense-in-depth (PR-MED-012→LOW): refuse UNC paths outright so a
        # misconfigured model path cannot cause SMB network I/O. Mapped
        # network drives are not cheaply distinguishable and stay a
        # documented same-user-boundary residual; runtime always uses the
        # LOCALAPPDATA default.
        if str(path).startswith(("\\\\", "//")):
            raise VadModelError(f"VAD model path must be a local path, not UNC: {path}")
        if not path.is_file():
            raise VadModelError(
                f"silero VAD model not found at {path} - run scripts/setup-models.py"
            )
        import numpy
        import onnxruntime

        self._np = numpy
        options = onnxruntime.SessionOptions()
        options.inter_op_num_threads = 1
        options.intra_op_num_threads = 1
        # Telemetry off (plan: onnxruntime telemetry disabled at runtime).
        onnxruntime.disable_telemetry_events()
        # PR-MED-013: a present-but-unusable model (corrupt bytes, wrong
        # architecture) must surface as VadModelError, not a raw
        # onnxruntime exception mid-session.
        try:
            self._session = onnxruntime.InferenceSession(
                str(path), sess_options=options, providers=["CPUExecutionProvider"]
            )
        except Exception as exc:
            raise VadModelError(f"failed to load VAD model at {path}: {exc}") from exc
        input_names = {i.name for i in self._session.get_inputs()}
        if not {"input", "state", "sr"} <= input_names:
            raise VadModelError(
                f"model at {path} does not match the silero VAD v5 signature "
                f"(inputs: {sorted(input_names)})"
            )
        self._sr = numpy.array(SAMPLE_RATE, dtype=numpy.int64)
        self._state: Any = None
        self._context: Any = None
        self.reset()
        # PR-MED-015: smoke-infer one silent frame at LOAD time so a model
        # that passes the signature check but is shape/type-incompatible
        # fails here as VadModelError — never on the first clinical frame.
        try:
            smoke = self.frame_probability(b"\0" * FRAME_BYTES)
        except Exception as exc:
            raise VadModelError(
                f"model at {path} failed smoke inference: {exc}"
            ) from exc
        if not 0.0 <= smoke <= 1.0:
            raise VadModelError(
                f"model at {path} returned a non-probability ({smoke}) on smoke inference"
            )
        self.reset()

    def reset(self) -> None:
        """Clear recurrent state and context between audio streams."""
        np = self._np
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, CONTEXT_SAMPLES), dtype=np.float32)

    def frame_probability(self, frame: bytes) -> float:
        """Speech probability for one exact ``FRAME_BYTES`` PCM16 frame."""
        if len(frame) != FRAME_BYTES:
            raise ValueError(f"frame must be exactly {FRAME_BYTES} bytes")
        np = self._np
        samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32768.0
        samples = samples.reshape(1, -1)
        model_input = np.concatenate([self._context, samples], axis=1)
        output, self._state = self._session.run(
            None, {"input": model_input, "state": self._state, "sr": self._sr}
        )
        self._context = samples[:, -CONTEXT_SAMPLES:]
        return float(output[0, 0])


def default_vad_model_path() -> Path:
    return default_models_root() / "silero-vad" / "silero_vad.onnx"


def segment_probabilities(
    probabilities: Iterable[float],
    *,
    frame_seconds: float = FRAME_SECONDS,
    start_threshold: float = START_THRESHOLD,
    end_threshold: float = END_THRESHOLD,
    min_speech_seconds: float = MIN_SPEECH_SECONDS,
    min_silence_seconds: float = MIN_SILENCE_SECONDS,
    pad_seconds: float = PAD_SECONDS,
) -> list[SpeechSegment]:
    """Hysteresis segmenter over per-frame speech probabilities.

    Pure Python and deterministic (unit-testable without the model):
    - speech starts when probability >= ``start_threshold``
    - speech ends after >= ``min_silence_seconds`` below ``end_threshold``
      (short dips inside speech are bridged)
    - segments shorter than ``min_speech_seconds`` are discarded
    - surviving segments are padded by ``pad_seconds`` each side, clamped
      to the audio bounds, and merged when padding makes them touch
    """
    if not 0.0 < end_threshold <= start_threshold <= 1.0:
        raise ValueError("thresholds must satisfy 0 < end <= start <= 1")
    min_silence_frames = max(1, round(min_silence_seconds / frame_seconds))

    raw: list[tuple[int, int]] = []  # [start_frame, end_frame) spans
    in_speech = False
    start_frame = 0
    silence_run = 0
    total_frames = 0
    for i, prob in enumerate(probabilities):
        total_frames = i + 1
        if not in_speech:
            if prob >= start_threshold:
                in_speech = True
                start_frame = i
                silence_run = 0
        elif prob < end_threshold:
            silence_run += 1
            if silence_run >= min_silence_frames:
                raw.append((start_frame, i + 1 - silence_run))
                in_speech = False
        else:
            silence_run = 0
    if in_speech:
        raw.append((start_frame, total_frames - silence_run))

    total_seconds = total_frames * frame_seconds
    segments: list[SpeechSegment] = []
    for first, last in raw:
        start = first * frame_seconds
        end = last * frame_seconds
        if end - start < min_speech_seconds:
            continue
        start = max(0.0, start - pad_seconds)
        end = min(total_seconds, end + pad_seconds)
        if segments and start <= segments[-1].end_seconds:
            previous = segments.pop()
            start = previous.start_seconds
        segments.append(SpeechSegment(start_seconds=start, end_seconds=end))
    return segments


def segment_pcm(
    chunks: Iterable[bytes],
    frame_probability: FrameProbabilityFn,
    **segmenter_options: float,
) -> list[SpeechSegment]:
    """PCM16 chunk stream -> speech segments via a frame-probability backend.

    When ``frame_probability`` is a bound method of a resettable backend
    (``SileroVad.frame_probability``), the backend is reset before AND
    after segmentation (in a ``finally``), so consecutive audio streams
    never contaminate each other and no PCM-derived recurrent state
    outlives the call — even on failure (PR-MED-011).
    """
    owner = getattr(frame_probability, "__self__", None)
    reset = getattr(owner, "reset", None)
    if callable(reset):
        reset()
    try:
        probabilities = (frame_probability(frame) for frame in iter_frames(chunks))
        return segment_probabilities(probabilities, **segmenter_options)
    finally:
        if callable(reset):
            reset()


def segment_session_audio(
    audio_path: Path,
    crypto: SessionCrypto,
    frame_probability: FrameProbabilityFn,
    *,
    require_footer: bool = False,
    **segmenter_options: float,
) -> list[SpeechSegment]:
    """Segment a session's encrypted audio via the decrypt-stream API.

    Streams ``session_store.iter_chunks`` (plaintext exists only in the
    per-chunk byte buffers) through the VAD; never materialises the whole
    recording in memory. Pass ``require_footer=True`` for a Finished store
    (the Step 9 pipeline does) so post-Finish truncation is detected;
    leave it False only for crash-recovery scans of unfinished stores.
    """
    return segment_pcm(
        iter_chunks(audio_path, crypto, require_footer=require_footer),
        frame_probability,
        **segmenter_options,
    )


def vad_model_available(model_path: Path | None = None) -> bool:
    """True when the local silero model file exists (skip-if-absent guard).

    Mirrors ``whisper_model_available`` (peer round 36 / round 42 MED-004):
    a UNC-redirected ``LOCALAPPDATA`` must not cause SMB I/O from this stat
    probe — UNC paths are refused BEFORE any filesystem touch and report
    unavailable (the ``SileroVad`` constructor keeps its own explicit UNC
    error).
    """
    try:
        path = model_path if model_path is not None else default_vad_model_path()
    except (RuntimeError, OSError):
        return False
    if str(path).startswith(("\\\\", "//")):
        return False  # UNC: never stat (no SMB I/O); unusable by policy
    return path.is_file()


__all__ = [
    "BYTES_PER_SAMPLE",
    "CONTEXT_SAMPLES",
    "END_THRESHOLD",
    "FRAME_BYTES",
    "FRAME_SAMPLES",
    "FRAME_SECONDS",
    "FrameProbabilityFn",
    "MIN_SILENCE_SECONDS",
    "MIN_SPEECH_SECONDS",
    "MockSpeechProvider",
    "PAD_SECONDS",
    "SAMPLE_RATE",
    "START_THRESHOLD",
    "SileroVad",
    "SpeechError",
    "SpeechProvider",
    "SpeechSegment",
    "TranscribedWord",
    "VadModelError",
    "default_vad_model_path",
    "iter_frames",
    "segment_pcm",
    "segment_probabilities",
    "segment_session_audio",
    "vad_model_available",
]
