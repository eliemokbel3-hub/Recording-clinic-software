"""Transcription pipeline (Phase 2 Step 9).

Flow 2 (plan): decrypt chunks streamwise -> VAD segments -> Whisper per
segment (word timestamps + probabilities, ``local_files_only=True``,
explicit local model path) -> uncertainty marks on low-confidence words
PLUS all numbers and proper-name-like tokens -> speaker labels per the
D8 decision (2-speaker clustering over VAD segments, numpy-only spectral
embeddings + 2-means) -> encrypted transcript artifact written ATOMICALLY
(temp + fsync + ``os.replace``) as ``transcript.enc`` under the SAME
session key -> the session machine moves processing -> queued.

Crash-mid-processing: recovery restarts transcription from audio —
``transcribe_session`` is idempotent and a partial/stale ``transcript.enc``
is overwritten atomically. Audio is never deleted here; only the explicit
Complete action (``session_store.complete_session``: fsync transcript ->
verify decrypt round-trip -> delete key) destroys custody.

Constraints honoured (plan Critical Constraints / executor facts):
- Lazy ML imports (numpy / faster_whisper only inside functions) so the
  module stays importable on CI without the ``[ml]`` extra.
- Zero network I/O: models load from explicit local paths with
  ``local_files_only=True``; the offline env kill-switches are asserted
  BEFORE any ML import; UNC model paths are refused outright.
- Transcript content NEVER passes through logging. This module logs
  nothing; the serialized field names (``transcript_segments``,
  ``transcript_words``, ``word_text``) are registered as tripwire
  signatures in ``logging_setup._PAYLOAD_SIGNATURES`` so even a misuse
  elsewhere cannot leak a transcript repr into a log line.
- Plaintext audio/transcript exist only in transient processing memory;
  the pipeline streams the store per segment and never materialises the
  whole recording.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from scribe_desktop.benchmark import (
    assert_offline_env,
    default_models_root,
    whisper_snapshot_complete,
    whisper_snapshot_missing,
)
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import (
    AUDIO_FILENAME,
    TRANSCRIPT_FILENAME,
    StoreCorruptError,
    StoreWriteError,
    iter_chunks,
    read_store_header,
    store_has_footer,
    unwrap_key_from_file,
)
from scribe_desktop.speech import (
    BYTES_PER_SAMPLE,
    SAMPLE_RATE,
    FrameProbabilityFn,
    SpeechError,
    SpeechProvider,
    SpeechSegment,
    TranscribedWord,
    segment_session_audio,
)

# D6 (user decision 2026-07-27): faster-whisper CTranslate2 CPU int8,
# model `small`; `medium` is the recorded quality fallback.
DEFAULT_WHISPER_MODEL = "small"

# Words at or below this backend probability are marked uncertain.
UNCERTAINTY_THRESHOLD = 0.60

# Spelled-out number tokens (cardinals, common ordinals, scale words) —
# plan: uncertainty marks cover low-confidence words, numbers, and names.
_NUMBER_WORDS: frozenset[str] = frozenset(
    """
    zero one two three four five six seven eight nine ten eleven twelve
    thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty
    thirty forty fifty sixty seventy eighty ninety hundred thousand
    million billion half quarter
    first second third fourth fifth sixth seventh eighth ninth tenth
    eleventh twelfth thirteenth fourteenth fifteenth sixteenth seventeenth
    eighteenth nineteenth twentieth thirtieth fortieth fiftieth sixtieth
    seventieth eightieth ninetieth hundredth thousandth
    """.split()
)

_DIGIT_RE = re.compile(r"\d")
_STRIP_PUNCT_RE = re.compile(r"^\W+|\W+$", re.UNICODE)

# PR-round-15: Whisper capitalizes the first word of every (VAD-cut)
# segment, so a blanket segment-initial exemption would hide real names
# spoken at utterance starts. Instead, only these common sentence-opening
# function/filler words are exempt when capitalized segment-initially;
# any other capitalized opener is marked (fail toward marking).
_COMMON_SEGMENT_STARTERS: frozenset[str] = frozenset(
    """
    the a an i it its this that these those there here he she they we you
    and but so or nor because if when while as well okay ok yes no now
    then what who whom whose which how why where am is are was were be
    been being do does did done can could will would shall should may
    might must have has had having not never also just still let's lets
    please right sure thanks thank alright anyway actually basically
    maybe perhaps
    """.split()
)

# Speaker-embedding parameters per the D8 decision block: 24 mel-band log
# powers + a low-band spectral centroid over 25 ms windows, averaged.
_EMBED_WINDOW_SECONDS = 0.025
_EMBED_MEL_BANDS = 24
_EMBED_FFT = 512
_EMBED_LOW_BAND_HZ = 1000.0
_KMEANS_RESTARTS = 10
_KMEANS_ITERATIONS = 30

SPEAKER_1 = "speaker_1"
SPEAKER_2 = "speaker_2"


class TranscriptionError(SpeechError):
    """Base class for transcription-pipeline failures."""


class TranscriptionModelError(TranscriptionError):
    """The Whisper model is missing or unusable at its local path."""


# ---------------------------------------------------------------------------
# Transcript artifact model (typed, serializable).
#
# Field names ``transcript_segments`` / ``transcript_words`` / ``word_text``
# are DELIBERATE: they are registered as logging tripwire signatures so any
# repr/JSON of these models is dropped by the last-line log filter.
# ---------------------------------------------------------------------------


class TranscriptWord(BaseModel):
    """One transcribed word with timing, confidence, and uncertainty mark."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    word_text: str
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    probability: float = Field(ge=0.0, le=1.0)
    uncertain: bool


class TranscriptSegment(BaseModel):
    """One VAD speech segment with its speaker label and words."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    speaker: str
    transcript_words: tuple[TranscriptWord, ...]


class TranscriptDocument(BaseModel):
    """The complete transcript artifact stored in ``transcript.enc``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    session_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    created_at: datetime
    model_name: str
    sample_rate: int = Field(gt=0)
    transcript_segments: tuple[TranscriptSegment, ...]

    def to_bytes(self) -> bytes:
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_bytes(cls, blob: bytes) -> TranscriptDocument:
        return cls.model_validate_json(blob)


# ---------------------------------------------------------------------------
# Uncertainty marking: low-confidence words + numbers + proper-name-like.
# ---------------------------------------------------------------------------


def is_number_token(text: str) -> bool:
    """True for digit-bearing tokens and spelled-out numbers/ordinals,
    including hyphenated compounds ("twenty-one", "one-third")."""
    if _DIGIT_RE.search(text):
        return True
    stripped = _STRIP_PUNCT_RE.sub("", text).lower()
    if stripped in _NUMBER_WORDS:
        return True
    parts = stripped.split("-")
    return len(parts) > 1 and any(part in _NUMBER_WORDS for part in parts)


def is_name_like_token(text: str, *, first_in_segment: bool) -> bool:
    """Proper-name heuristic (fail toward marking — a false uncertainty
    mark costs a review glance, a missed name in a clinical note costs
    accuracy).

    Mid-segment: any capitalized alphabetic token is name-like. Segment
    start: Whisper capitalizes every segment's first word, so a blanket
    mark would be all-noise and a blanket exemption would hide names that
    open an utterance ("Margaret, how is the shoulder?") — instead only
    common sentence-opening function words are exempt; any other
    capitalized opener is marked (PR round 15).
    """
    stripped = _STRIP_PUNCT_RE.sub("", text)
    if not stripped or not stripped[0].isalpha() or not stripped[0].isupper():
        return False
    if not first_in_segment:
        return True
    return stripped.lower() not in _COMMON_SEGMENT_STARTERS


def mark_words(
    words: Iterable[TranscribedWord],
    *,
    threshold: float = UNCERTAINTY_THRESHOLD,
    offset_seconds: float = 0.0,
) -> tuple[TranscriptWord, ...]:
    """Apply uncertainty marks and shift word times by the segment offset."""
    marked: list[TranscriptWord] = []
    for i, word in enumerate(words):
        text = word.text.strip()
        uncertain = (
            word.probability < threshold
            or is_number_token(text)
            or is_name_like_token(text, first_in_segment=i == 0)
        )
        marked.append(
            TranscriptWord(
                word_text=text,
                start_seconds=max(0.0, offset_seconds + word.start_seconds),
                end_seconds=max(0.0, offset_seconds + word.end_seconds),
                probability=min(1.0, max(0.0, word.probability)),
                uncertain=uncertain,
            )
        )
    return tuple(marked)


# ---------------------------------------------------------------------------
# Segment PCM extraction — single streaming pass over the decrypt-stream.
# ---------------------------------------------------------------------------


def extract_segment_pcm(
    chunks: Iterable[bytes],
    segments: list[SpeechSegment],
    *,
    sample_rate: int = SAMPLE_RATE,
) -> Iterator[bytes]:
    """Yield each segment's PCM16 bytes in order, one streaming pass.

    Segments must be ordered and non-overlapping (the segmenter guarantees
    both). Only one segment's audio is materialised at a time.
    """
    spans: list[tuple[int, int]] = []
    for segment in segments:
        start = int(segment.start_seconds * sample_rate) * BYTES_PER_SAMPLE
        end = int(segment.end_seconds * sample_rate) * BYTES_PER_SAMPLE
        spans.append((start, end))
    for i in range(1, len(spans)):
        if spans[i][0] < spans[i - 1][1]:
            raise ValueError("segments must be ordered and non-overlapping")

    position = 0
    span_index = 0
    buffer = bytearray()
    for chunk in chunks:
        chunk_start, chunk_end = position, position + len(chunk)
        position = chunk_end
        while span_index < len(spans):
            start, end = spans[span_index]
            if chunk_end <= start:
                break  # this chunk is entirely before the current segment
            lo = max(start, chunk_start) - chunk_start
            hi = min(end, chunk_end) - chunk_start
            if hi > lo:
                buffer.extend(chunk[lo:hi])
            if chunk_end >= end:
                yield bytes(buffer)
                buffer.clear()
                span_index += 1
                continue  # the same chunk may open the next segment
            break
    # A final segment may extend past the audio end (VAD zero-pads its last
    # frame): emit what was collected rather than dropping tail speech.
    if span_index < len(spans) and buffer:
        yield bytes(buffer)
        buffer.clear()
        span_index += 1
    while span_index < len(spans):
        yield b""
        span_index += 1


# ---------------------------------------------------------------------------
# Speaker labels — D8: numpy-only spectral embeddings + 2-means clustering.
# ---------------------------------------------------------------------------


def _numpy() -> Any:
    # Offline env asserted before EVERY ML-stack import (binding pattern,
    # PR round 15) — including numpy for the speaker-embedding path, which
    # is reachable without the Whisper provider's own assert.
    assert_offline_env()
    import numpy

    return numpy


def _segment_embedding(pcm: bytes, np: Any, *, sample_rate: int = SAMPLE_RATE) -> Any:
    """24 mel-band log powers + low-band spectral centroid, averaged over
    non-overlapping 25 ms windows (the D8 decision's feature recipe)."""
    window = int(_EMBED_WINDOW_SECONDS * sample_rate)
    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    if len(samples) < window:
        samples = np.pad(samples, (0, window - len(samples)))
    frame_count = len(samples) // window
    frames = samples[: frame_count * window].reshape(frame_count, window)
    frames = frames * np.hanning(window).astype(np.float32)
    spectrum = np.abs(np.fft.rfft(frames, n=_EMBED_FFT, axis=1)) ** 2  # (n, bins)
    freqs = np.fft.rfftfreq(_EMBED_FFT, d=1.0 / sample_rate)

    # Triangular mel filterbank over 0..Nyquist.
    def hz_to_mel(hz: Any) -> Any:
        return 2595.0 * np.log10(1.0 + hz / 700.0)

    def mel_to_hz(mel: Any) -> Any:
        return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)

    mel_points = mel_to_hz(
        np.linspace(hz_to_mel(0.0), hz_to_mel(sample_rate / 2.0), _EMBED_MEL_BANDS + 2)
    )
    filterbank = np.zeros((_EMBED_MEL_BANDS, len(freqs)), dtype=np.float32)
    for band in range(_EMBED_MEL_BANDS):
        left, center, right = mel_points[band : band + 3]
        rising = (freqs - left) / max(center - left, 1e-9)
        falling = (right - freqs) / max(right - center, 1e-9)
        filterbank[band] = np.clip(np.minimum(rising, falling), 0.0, None)

    mel_power = spectrum @ filterbank.T  # (n, bands)
    log_mel = np.log(mel_power + 1e-10).mean(axis=0)  # (bands,)

    low = freqs <= _EMBED_LOW_BAND_HZ
    low_power = spectrum[:, low].mean(axis=0)
    centroid = float((freqs[low] * low_power).sum() / (low_power.sum() + 1e-10))
    return np.concatenate([log_mel, [centroid / _EMBED_LOW_BAND_HZ]]).astype(np.float32)


def _kmeans_two(features: Any, np: Any) -> Any:
    """Plain 2-means with seeded restarts; returns per-row labels (0/1)."""
    count = features.shape[0]
    best_labels = np.zeros(count, dtype=np.int64)
    best_inertia = None
    for seed in range(_KMEANS_RESTARTS):
        rng = np.random.default_rng(seed)
        centers = features[rng.choice(count, size=2, replace=False)].copy()
        labels = np.zeros(count, dtype=np.int64)
        for iteration in range(_KMEANS_ITERATIONS):
            distances = ((features[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
            new_labels = distances.argmin(axis=1)
            for k in range(2):
                if not (new_labels == k).any():
                    # Empty cluster: seize the point farthest from its center.
                    farthest = distances[np.arange(count), new_labels].argmax()
                    new_labels[farthest] = k
            if iteration > 0 and (new_labels == labels).all():
                break
            labels = new_labels
            for k in range(2):
                centers[k] = features[labels == k].mean(axis=0)
        inertia = float(((features - centers[labels]) ** 2).sum())
        if best_inertia is None or inertia < best_inertia:
            best_inertia = inertia
            best_labels = labels.copy()
    return best_labels


def _cluster_embeddings(embeddings: list[Any], np: Any) -> list[str]:
    """2-means over per-segment embeddings (len >= 2); stable label order."""
    features = np.stack(embeddings)
    std = features.std(axis=0)
    if not (std > 1e-6).any():
        return [SPEAKER_1] * len(embeddings)
    features = (features - features.mean(axis=0)) / (std + 1e-9)
    labels = _kmeans_two(features, np)
    if (labels == labels[0]).all():
        return [SPEAKER_1] * len(embeddings)
    first = labels[0]
    return [SPEAKER_1 if label == first else SPEAKER_2 for label in labels]


def label_speakers(segment_pcms: list[bytes], *, sample_rate: int = SAMPLE_RATE) -> list[str]:
    """Speaker label per segment via D8's 2-means over spectral embeddings.

    Fewer than two non-empty segments, or degenerate (identical) features,
    yield a single speaker. Labels are stable: the first segment is always
    ``speaker_1``.
    """
    if not segment_pcms:
        return []
    if len(segment_pcms) < 2 or any(len(pcm) == 0 for pcm in segment_pcms):
        return [SPEAKER_1] * len(segment_pcms)
    np = _numpy()
    embeddings = [
        _segment_embedding(pcm, np, sample_rate=sample_rate) for pcm in segment_pcms
    ]
    return _cluster_embeddings(embeddings, np)


# ---------------------------------------------------------------------------
# WhisperSpeechProvider — the real SpeechProvider (D6: faster-whisper,
# CTranslate2 CPU int8, model `small`).
# ---------------------------------------------------------------------------


def default_whisper_model_dir(model_name: str = DEFAULT_WHISPER_MODEL) -> Path:
    return default_models_root() / "whisper" / model_name


def whisper_model_available(model_name: str = DEFAULT_WHISPER_MODEL) -> bool:
    """True when the local whisper snapshot looks complete (skip-if-absent)."""
    try:
        model_dir = default_whisper_model_dir(model_name)
    except (RuntimeError, OSError):
        return False
    return whisper_snapshot_complete(model_dir)


class WhisperSpeechProvider:
    """Local faster-whisper transcription over one speech segment.

    Loads the CTranslate2 model from an EXPLICIT local path with
    ``local_files_only=True``; the offline env kill-switches are asserted
    before any ML import (plan: Runtime offline enforcement). Word
    timestamps and word probabilities are always requested — the
    uncertainty marking depends on them.
    """

    def __init__(
        self,
        model_dir: Path | None = None,
        *,
        model_name: str = DEFAULT_WHISPER_MODEL,
        language: str | None = "en",
    ) -> None:
        assert_offline_env()
        path = model_dir if model_dir is not None else default_whisper_model_dir(model_name)
        # Defense-in-depth (PR-MED-012 precedent): refuse UNC paths so a
        # misconfigured model path cannot cause SMB network I/O.
        if str(path).startswith(("\\\\", "//")):
            raise TranscriptionModelError(
                f"whisper model path must be a local path, not UNC: {path}"
            )
        missing = whisper_snapshot_missing(path)
        if missing:
            raise TranscriptionModelError(
                f"whisper model at {path} is missing {', '.join(missing)} - "
                "run scripts/setup-models.py"
            )
        self._np = _numpy()
        from faster_whisper import WhisperModel

        self._language = language
        self._model_name = path.name
        try:
            self._model = WhisperModel(
                str(path), device="cpu", compute_type="int8", local_files_only=True
            )
        except Exception as exc:
            raise TranscriptionModelError(
                f"failed to load whisper model at {path}: {exc}"
            ) from exc

    @property
    def model_name(self) -> str:
        return self._model_name

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        if sample_rate != SAMPLE_RATE:
            raise ValueError(f"pipeline audio must be {SAMPLE_RATE} Hz PCM16")
        if not pcm:
            return []
        np = self._np
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _info = self._model.transcribe(
            audio,
            word_timestamps=True,
            language=self._language,
            beam_size=5,
            condition_on_previous_text=False,
        )
        words: list[TranscribedWord] = []
        for segment in segments:
            for word in segment.words or []:
                text = word.word.strip()
                if not text:
                    continue
                start = float(word.start)
                end = float(word.end)
                words.append(
                    TranscribedWord(
                        text=text,
                        start_seconds=start,
                        end_seconds=max(end, start),
                        probability=min(1.0, max(0.0, float(word.probability))),
                    )
                )
        return words


# ---------------------------------------------------------------------------
# Transcript artifact I/O — atomic write under the SAME session key.
# ---------------------------------------------------------------------------


def write_transcript(
    session_dir: Path, crypto: SessionCrypto, document: TranscriptDocument
) -> Path:
    """Encrypt and write ``transcript.enc`` ATOMICALLY (temp + fsync +
    ``os.replace``) under the session key. Idempotent: a partial or stale
    transcript from a crashed processing run is overwritten in one atomic
    step (Flow 2 crash-mid-processing contract).

    No AAD: the Complete ordering primitive (``complete_session``) verifies
    the round-trip with a plain decrypt — the two must stay in agreement.
    """
    blob = crypto.encrypt(document.to_bytes())
    transcript_path = session_dir / TRANSCRIPT_FILENAME
    tmp_path = session_dir / (TRANSCRIPT_FILENAME + ".tmp")
    try:
        with tmp_path.open("wb") as stream:
            stream.write(blob)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_path, transcript_path)
    except OSError as exc:
        raise StoreWriteError(f"failed writing transcript artifact: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)
    return transcript_path


def read_transcript(session_dir: Path, crypto: SessionCrypto) -> TranscriptDocument:
    """Decrypt and parse ``transcript.enc`` (the inspection view's read path)."""
    transcript_path = session_dir / TRANSCRIPT_FILENAME
    try:
        blob = transcript_path.read_bytes()
    except OSError as exc:
        raise StoreWriteError(f"transcript artifact unreadable: {exc}") from exc
    try:
        plain = crypto.decrypt(blob)
    except InvalidTag as exc:
        raise StoreCorruptError("transcript failed authentication") from exc
    try:
        return TranscriptDocument.from_bytes(plain)
    except ValidationError as exc:
        raise StoreCorruptError("transcript artifact is malformed") from exc


# ---------------------------------------------------------------------------
# The pipeline.
# ---------------------------------------------------------------------------


def transcribe_session(
    session_dir: Path,
    crypto: SessionCrypto,
    provider: SpeechProvider,
    frame_probability: FrameProbabilityFn,
    *,
    require_footer: bool = True,
    model_name: str = "",
    uncertainty_threshold: float = UNCERTAINTY_THRESHOLD,
) -> TranscriptDocument:
    """Flow 2: VAD -> Whisper per segment -> uncertainty marks -> speaker
    labels -> ``transcript.enc`` written atomically under the session key.

    Idempotent by construction: rerunning after a crash mid-processing
    reproduces and atomically replaces the transcript. ``require_footer``
    stays True for Finished stores (post-Finish truncation must fail);
    pass False only when recovering a store that never reached Finish.
    """
    audio_path = session_dir / AUDIO_FILENAME
    header = read_store_header(audio_path)
    if header.sample_rate != SAMPLE_RATE:
        raise TranscriptionError(
            f"store sample rate {header.sample_rate} is not the pipeline rate {SAMPLE_RATE}"
        )
    segments = segment_session_audio(
        audio_path, crypto, frame_probability, require_footer=require_footer
    )

    # PR round 15: segment PCM is processed and DROPPED per iteration —
    # only the 25-float speaker embedding is retained, never the plaintext
    # audio of the whole consultation.
    np = _numpy() if len(segments) >= 2 else None
    marked_segments: list[tuple[SpeechSegment, tuple[TranscriptWord, ...]]] = []
    embeddings: list[Any] = []
    saw_empty_segment = False
    pcm_stream = extract_segment_pcm(
        iter_chunks(audio_path, crypto, require_footer=require_footer), segments
    )
    for segment, pcm in zip(segments, pcm_stream, strict=True):
        raw_words = provider.transcribe_segment(pcm, SAMPLE_RATE)
        words = mark_words(
            raw_words,
            threshold=uncertainty_threshold,
            offset_seconds=segment.start_seconds,
        )
        marked_segments.append((segment, words))
        if np is not None:
            if pcm:
                embeddings.append(_segment_embedding(pcm, np))
            else:
                saw_empty_segment = True

    if np is None or saw_empty_segment or len(embeddings) < 2:
        speakers = [SPEAKER_1] * len(segments)
    else:
        speakers = _cluster_embeddings(embeddings, np)
    document = TranscriptDocument(
        session_id=header.session_id,
        created_at=datetime.now(UTC),
        model_name=model_name or getattr(provider, "model_name", type(provider).__name__),
        sample_rate=SAMPLE_RATE,
        transcript_segments=tuple(
            TranscriptSegment(
                start_seconds=segment.start_seconds,
                end_seconds=segment.end_seconds,
                speaker=speaker,
                transcript_words=words,
            )
            for (segment, words), speaker in zip(marked_segments, speakers, strict=True)
        ),
    )
    write_transcript(session_dir, crypto, document)
    return document


@dataclass(frozen=True)
class RecoveryOutcome:
    """Result of a Flow 3 resume-processing run.

    ``store_finished`` is False when the audio store carries no complete
    footer. Session state is not persisted across a crash, so a store
    from a crash mid-recording and a (threat-model-external) post-Finish
    truncation are indistinguishable here — the recovery UI MUST surface
    "recording did not finish cleanly; the tail may be missing" whenever
    this flag is False, and the user reviews the transcript before
    Complete (PR round 15 residual, recorded in the plan).
    """

    document: TranscriptDocument
    crypto: SessionCrypto
    store_finished: bool


def recover_session_transcription(
    session_dir: Path,
    provider: SpeechProvider,
    frame_probability: FrameProbabilityFn,
    *,
    model_name: str = "",
) -> RecoveryOutcome:
    """Flow 3 resume-processing: unwrap the DPAPI key custody and restart
    transcription from audio (idempotent; a partial transcript is replaced
    atomically). A store that reached Finish keeps footer enforcement; a
    store without a footer is transcribed from its durably written chunks
    (truncated tail tolerated as expected crash behaviour) and flagged via
    ``RecoveryOutcome.store_finished`` for the recovery UI.

    The returned crypto lets the caller drive queued -> Complete (which
    destroys the crypto) or Discard.
    """
    crypto = unwrap_key_from_file(session_dir)
    store_finished = store_has_footer(session_dir / AUDIO_FILENAME)
    document = transcribe_session(
        session_dir,
        crypto,
        provider,
        frame_probability,
        require_footer=store_finished,
        model_name=model_name,
    )
    return RecoveryOutcome(document=document, crypto=crypto, store_finished=store_finished)


__all__ = [
    "DEFAULT_WHISPER_MODEL",
    "SPEAKER_1",
    "SPEAKER_2",
    "UNCERTAINTY_THRESHOLD",
    "RecoveryOutcome",
    "TranscriptDocument",
    "TranscriptSegment",
    "TranscriptWord",
    "TranscriptionError",
    "TranscriptionModelError",
    "WhisperSpeechProvider",
    "default_whisper_model_dir",
    "extract_segment_pcm",
    "is_name_like_token",
    "is_number_token",
    "label_speakers",
    "mark_words",
    "read_transcript",
    "recover_session_transcription",
    "transcribe_session",
    "whisper_model_available",
    "write_transcript",
]
