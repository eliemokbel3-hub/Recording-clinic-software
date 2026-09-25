"""Transcription pipeline (Phase 2 Step 9; windowed batching Step 13).

Flow 2 (plan): decrypt chunks streamwise -> VAD segments -> consecutive
segments PACKED into ~30 s contiguous transcription windows -> Whisper per
WINDOW (word timestamps + probabilities, ``local_files_only=True``,
explicit local model path; window words attributed back to their VAD
segments by midpoint) -> uncertainty marks on low-confidence words
PLUS all numbers and proper-name-like tokens -> speaker labels per the
D8 decision (2-speaker clustering over VAD segments, numpy-only spectral
embeddings + 2-means) -> encrypted transcript artifact written ATOMICALLY
(temp + fsync + ``os.replace``) as ``transcript.enc`` under the SAME
session key -> the session machine moves processing -> queued.

Why windows (Step 13 batching, user decision 2026-07-30): Whisper charges
a full 30 s encoder window per ``transcribe`` call regardless of input
length, so per-VAD-segment calls paid ~10x on short utterances (measured
pipeline RTF up to ~5.3x real time on pause-rich audio — clinically
unusable). Packing consecutive segments into one contiguous window
([first.start, last.end] INCLUDING the silence gaps, so returned word
times stay linear with absolute session time) cuts the call count by the
segments-per-window factor while keeping every downstream contract:
per-VAD-segment speaker attribution, uncertainty marks, and word times.

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
  the pipeline streams the store one transcription window at a time and
  never materialises the whole recording.

Voice attribution (practitioner-profile plan, Phase 2 — Design Decisions
D1, D3, D4, D13): when ``transcribe_session`` is given a ``SpeakerEmbedder``
AND the practitioner's enrolled ``PractitionerProfile`` together, every VAD
segment is ALSO embedded with that model inside the same window its spectral
embedding is computed in (the plaintext bound is unchanged — only one float
per segment is retained from it, the raw cosine against the enrolled vector),
and the labels follow D13 as amended 2026-09-16 (Task 2.6): the
practitioner's cluster is ``speaker_1`` and the WHOLE non-practitioner
remainder is ``speaker_2`` — a third label returns only when D-S1 estimates
the speaker count from the shared recording set. The document then carries
``enrolled_speaker`` / ``enrolment_similarity`` / ``speaker_model_id`` — a
SEPARATE field the Transcript screen auto-confirms from (D4), never a speaker
label itself (D1). Without both inputs the path below runs exactly as before,
byte for byte.
"""

from __future__ import annotations

import enum
import math
import queue
import re
import threading
import time
from collections import deque
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from scribe_desktop.benchmark import (
    assert_offline_env,
    default_models_root,
    whisper_snapshot_complete,
    whisper_snapshot_missing,
)
from scribe_desktop.practitioner_profile import PractitionerProfile
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import (
    AUDIO_FILENAME,
    NOTE_FILENAME,
    SESSION_ID_PATTERN,
    TRANSCRIPT_FILENAME,
    StoreCorruptError,
    StoreWriteError,
    atomic_write_bytes,
    iter_chunks,
    read_store_header,
    store_has_footer,
    unwrap_key_from_file,
)
from scribe_desktop.speaker_embedding import ATTRIBUTION_THRESHOLD, FRAME_LENGTH, SpeakerEmbedder
from scribe_desktop.speech import (
    BYTES_PER_SAMPLE,
    END_THRESHOLD,
    FRAME_BYTES,
    FRAME_SECONDS,
    MIN_SILENCE_SECONDS,
    MIN_SPEECH_SECONDS,
    PAD_SECONDS,
    SAMPLE_RATE,
    START_THRESHOLD,
    FrameProbabilityFn,
    SpeechError,
    SpeechProvider,
    SpeechSegment,
    TranscribedWord,
    segment_session_audio,
)

# D6 (user decision 2026-07-27): faster-whisper CTranslate2 CPU int8,
# model `small`, with `medium` recorded as the quality fallback "if pilot
# transcripts disappoint". REVISED at the Step 13 manual gate (user
# decision 2026-07-28): the pilot transcripts DID disappoint on hard
# words, so `medium` is now the default (single-call benchmark on this
# hardware: RTF 0.498 vs small's 0.151, ~1.8 GiB peak — inside the
# RTF<=0.75 margin). The per-VAD-segment pipeline of stages 6-10 ran WELL
# above the single-call benchmark (each short segment cost a full 30 s
# encoder window); Step 13 batching packs segments into ~30 s windows,
# and the measured end-to-end pipeline RTF is ~0.54-0.60 for
# medium+prompt on an idle machine (~2x the single-call cost, ~2x faster
# than per-segment under identical conditions — see the plan's Step 13
# batching sub-entry, including the machine-load caveat, before quoting
# speed numbers). `small` stays fully supported as the graceful fallback
# when the medium snapshot was never downloaded: degrade VISIBLY (UI
# report names the fallback), never fail outright and never silently.
DEFAULT_WHISPER_MODEL = "medium"
FALLBACK_WHISPER_MODEL = "small"

# ---------------------------------------------------------------------------
# Clinical vocabulary priming (Step 13 user decision 2026-07-28).
#
# faster-whisper passes ``initial_prompt`` to the decoder as left-hand
# context, biasing recognition toward this vocabulary without any
# fine-tuning. ``transcribe_segment`` runs per packed ~30 s transcription
# window (Step 13 batching) with ``condition_on_previous_text=False``, so
# every window receives this primer fresh — it never accumulates with
# transcript text and no transcript content ever feeds back into it.
#
# HARD CONSTRAINTS (all deliberate — keep them when editing):
# - Token budget: faster-whisper keeps only the LAST ``max_length//2 - 1``
#   = 223 prompt tokens (transcribe.py ``get_prompt``, verified against
#   the installed 1.2.1 source) and silently drops the HEAD of an
#   overlong prompt — the first clusters are exactly what would vanish.
#   This text measures 193 tokens with the model's own tokenizer
#   (identical count on small and medium, measured 2026-07-30 the way
#   faster-whisper encodes it: leading space, no special tokens). Clinical
#   latinate terms cost ~3 tokens per word, so word count is a treacherous
#   proxy — RE-MEASURE with the real tokenizer before growing this, and
#   stay under ~210 to keep headroom.
# - NO patient-identifying content, ever. Anatomy, presentations, exam
#   manoeuvres, techniques, medications, and units only. Never add example
#   patient names: a primed name is exactly what Whisper will hallucinate
#   into unclear audio, and the name-like uncertainty heuristic cannot
#   flag what looks contextually plausible.
# - This constant must never pass through logging (tripwire discipline —
#   this module logs nothing; keep it that way).
# - Australian-English clinic-note spellings on purpose (mobilisation,
#   paraesthesia): priming steers output spelling too.
#
# Why each cluster is here (osteopathic/musculoskeletal scribe domain;
# only mangle-prone terms earn their tokens — common words Whisper already
# gets right, e.g. trapezius/hamstrings/ibuprofen, were trimmed to fit):
# - anatomy + muscles: latinate terms Whisper mangles into near-homophones
# - presentations: assessment/diagnosis vocabulary heard in histories
# - exam manoeuvres: multiword test names otherwise get fused or split
# - treatment techniques: osteopathy-specific phrases rare in general text
# - medications: the mangle-prone analgesic/adjunct names
# - units/scores: pain scores are spoken "out of ten"
CLINICAL_INITIAL_PROMPT = (
    "Osteopathic consultation. Cervical, thoracic, lumbar spine, "
    "sacroiliac joint, acromioclavicular, rotator cuff, supraspinatus, "
    "levator scapulae, erector spinae, multifidus, quadratus lumborum, "
    "psoas, piriformis, gastrocnemius, plantar fascia. Low back pain, "
    "sciatica, radiculopathy, paraesthesia, cervicogenic headache, "
    "tendinopathy, bursitis. Palpation, range of motion, flexion, "
    "straight leg raise, Spurling's test, dermatomes, myotomes. "
    "Myofascial release, muscle energy technique, high velocity low "
    "amplitude manipulation, mobilisation, dry needling. Pain seven out "
    "of ten. Meloxicam, amitriptyline."
)

# Windowed batching (Step 13 speed fix). Whisper's encoder always
# processes a full 30 s window, so the packer aims windows at exactly that
# budget: a window spans [first_segment.start, last_segment.end] read
# CONTIGUOUSLY (silence gaps between its segments included — word times
# returned by the model then stay linear with absolute session time).
# ``TRANSCRIBE_WINDOW_SECONDS`` must stay <= 30: faster-whisper applies
# ``initial_prompt`` only to the FIRST internal 30 s window of a call when
# ``condition_on_previous_text=False`` (verified in installed 1.2.1
# transcribe.py: ``prompt_reset_since = len(all_tokens)`` after every
# window), so a longer packed window would silently lose clinical priming
# for its tail. A single VAD segment longer than the budget becomes its
# own window and faster-whisper seeks through it internally — identical
# priming behaviour to the old per-segment call for that segment.
TRANSCRIBE_WINDOW_SECONDS = 30.0
# A silence gap longer than this breaks the window even when the budget
# has room: long dead air buys no accuracy, spends encoder budget, and is
# exactly where Whisper is most prone to hallucinate. Gaps at or under
# this bound are natural speech rhythm and transcribe fine in context.
TRANSCRIBE_WINDOW_MAX_GAP_SECONDS = 3.0

# Words strictly below this backend probability are marked uncertain
# (``mark_words``: ``probability < threshold``). Step 13 calibration
# check (2026-07-30, recorded in the plan): medium shifts probabilities
# UP on identical audio yet marks neither vanish nor flood at 0.60 —
# KEPT; recalibrate only on evidence from real re-test transcripts.
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
# Defined for D-S1's return (an estimated speaker count); since D13's 2026-09-16
# amendment (Task 2.6) no shipped path emits it — with a profile applied the
# whole non-practitioner remainder is ``speaker_2``.
SPEAKER_3 = "speaker_3"

# The shortest segment slice the speaker embedder is asked to embed: one
# front-end frame (25 ms). A shorter slice — only a padded tail past the
# audio end can be one — gets no similarity rather than a front-end refusal.
MIN_ATTRIBUTION_PCM_BYTES = FRAME_LENGTH * BYTES_PER_SAMPLE


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


def words_have_text(words: Iterable[TranscriptWord]) -> bool:
    """Whether any word is non-blank — the ONE definition of "holds
    transcribed text" the attribution fields, the D13 candidate clusters
    (the pipeline applies it per segment before the document exists) and the
    Transcript screen's radios (built from ``ui.models.speaker_quotations``,
    which quotes the first non-blank utterance per label) all agree on."""
    return any(word.word_text.strip() for word in words)


def segment_has_text(segment: TranscriptSegment) -> bool:
    """``words_have_text`` over a built segment's words."""
    return words_have_text(segment.transcript_words)


class TranscriptDocument(BaseModel):
    """The complete transcript artifact stored in ``transcript.enc``.

    Voice attribution (practitioner-profile plan Phase 2, D1/D3/D13): the
    three OPTIONAL fields are set TOGETHER when an enrolled profile was
    applied and the document holds transcribed speech, and are all ``None``
    otherwise — no profile, no segments, or no segment with text — so an
    artefact written before they existed reads unchanged (``schema_version``
    stays 1; additive, defaulted). ``enrolled_speaker`` is the cluster label
    the Transcript screen auto-confirms as the clinician (D4) and MUST be the
    label of a segment that has transcribed text (``segment_has_text``): a
    textless cluster has no radio and cannot be confirmed, and a document
    naming a label its segments do not carry is refused at construction, so
    the UI never sees one (the lying-field defence). ``enrolment_similarity``
    is the RAW mean cosine of that cluster's segments against the enrolled
    vector — finite, in [-1, 1], never a 0–1 clamp; ``speaker_model_id``
    names the embedder that produced it. Cluster labels stay opaque (D1):
    ``enrolled_speaker`` is a pre-check for a UI selection, not a value the
    note pipeline accepts as the confirmed role.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    session_id: str = Field(pattern=SESSION_ID_PATTERN)
    created_at: datetime
    model_name: str
    sample_rate: int = Field(gt=0)
    transcript_segments: tuple[TranscriptSegment, ...]
    enrolled_speaker: str | None = None
    enrolment_similarity: float | None = None
    speaker_model_id: str | None = Field(default=None, min_length=1)

    @field_validator("enrolment_similarity")
    @classmethod
    def _similarity_is_a_cosine(cls, value: float | None) -> float | None:
        if value is not None and not (math.isfinite(value) and -1.0 <= value <= 1.0):
            raise ValueError("enrolment_similarity must be a finite cosine in [-1, 1]")
        return value

    @model_validator(mode="after")
    def _attribution_fields_agree(self) -> TranscriptDocument:
        present = [
            value is not None
            for value in (self.enrolled_speaker, self.enrolment_similarity, self.speaker_model_id)
        ]
        if any(present) and not all(present):
            raise ValueError(
                "enrolled_speaker, enrolment_similarity and speaker_model_id are set "
                "together or not at all"
            )
        if self.enrolled_speaker is not None and self.enrolled_speaker not in {
            segment.speaker for segment in self.transcript_segments if segment_has_text(segment)
        }:
            raise ValueError(
                "enrolled_speaker must be the label of a segment with transcribed text"
            )
        return self

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
# Window packing + word->segment attribution (Step 13 batching, pure).
# ---------------------------------------------------------------------------


def pack_transcription_windows(
    segments: Sequence[SpeechSegment],
    *,
    window_seconds: float = TRANSCRIBE_WINDOW_SECONDS,
    max_gap_seconds: float = TRANSCRIBE_WINDOW_MAX_GAP_SECONDS,
) -> list[tuple[int, int]]:
    """Group consecutive VAD segments into contiguous transcription windows.

    Returns ``[start, stop)`` index pairs into ``segments``. Greedy packing:
    a window grows while the NEXT segment (a) keeps the window's contiguous
    span ``[first.start, next.end]`` within ``window_seconds`` and (b) sits
    within ``max_gap_seconds`` of the previous segment's end. Every segment
    lands in exactly one window; a single segment longer than the budget
    becomes its own (oversized) window — the provider seeks through it
    internally, exactly as the old per-segment call did.
    """
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")
    if max_gap_seconds < 0:
        raise ValueError("max_gap_seconds must be non-negative")
    windows: list[tuple[int, int]] = []
    i = 0
    while i < len(segments):
        j = i + 1
        while j < len(segments):
            fits = (
                segments[j].end_seconds - segments[i].start_seconds <= window_seconds
            )
            gap = segments[j].start_seconds - segments[j - 1].end_seconds
            if not fits or gap > max_gap_seconds:
                break
            j += 1
        windows.append((i, j))
        i = j
    return windows


def assign_words_to_segments(
    words: Sequence[TranscribedWord],
    segments: Sequence[SpeechSegment],
    *,
    window_start_seconds: float,
) -> list[list[TranscribedWord]]:
    """Attribute window-transcribed words back to the window's VAD segments.

    ``words`` carry times relative to the window's PCM; ``segments`` are the
    window's VAD segments in absolute session time. Each word goes to the
    segment whose ``[start, end]`` contains its absolute midpoint; a word
    whose midpoint lands in a gap between segments goes to the NEAREST
    segment (earlier one on a tie). No word is ever dropped or duplicated —
    the returned lists partition ``words`` in order, one list per segment.
    """
    if not segments:
        raise ValueError("a transcription window must contain segments")
    assigned: list[list[TranscribedWord]] = [[] for _ in segments]
    for word in words:
        midpoint = window_start_seconds + (word.start_seconds + word.end_seconds) / 2.0
        best_index = 0
        best_distance = float("inf")
        for index, segment in enumerate(segments):
            distance = max(
                segment.start_seconds - midpoint, midpoint - segment.end_seconds, 0.0
            )
            if distance < best_distance:
                best_index = index
                best_distance = distance
            if distance == 0.0:
                break  # containment: no later segment can beat it
        assigned[best_index].append(word)
    return assigned


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


def _segment_embedding(
    pcm: bytes,
    np: Any,
    *,
    sample_rate: int = SAMPLE_RATE,
    cepstral_mean_normalisation: bool = True,
) -> Any:
    """24 mel-band log powers + low-band spectral centroid, averaged over
    non-overlapping 25 ms windows (the D8 decision's feature recipe), with
    the mel part CEPSTRAL-MEAN-NORMALISED per segment so the feature carries
    spectral shape and not loudness (Phase 3A Task 2.1).

    ``cepstral_mean_normalisation=False`` skips exactly that one subtraction
    and reproduces the pre-Task-2.1 embedding. It exists for the Task 2.3
    measurement harness (``speaker_eval``), whose "before" condition must
    differ from the shipped pipeline by precisely the Task 2.1 line; the
    pipeline's own call in ``transcribe_session`` never passes it.
    """
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

    # Per-segment cepstral mean normalisation (Task 2.1). A gain ``g`` on the
    # samples scales every power by ``g**2``, so it adds the SAME constant
    # ``2*ln(g)`` to every log-mel band. Subtracting this segment's mean
    # across bands removes that constant, leaving spectral SHAPE — what
    # actually distinguishes two voices — and dropping the loudness nuisance
    # that otherwise lets one loud and one quiet speaker separate as two
    # clusters (a speaker who turns away from the microphone is the everyday
    # case). Equivalent to removing the mean per frame and then averaging
    # over frames, because the two means commute; done on the already-averaged
    # vector because that is cheaper and identical.
    #
    # The removal is exact only while every band sits above the ``1e-10``
    # floor added above — a band pinned AT the floor does not move with gain,
    # so its share of the offset survives. That bound is not binding for real
    # audio: int16 quantisation noise alone puts a mel band around ``1e-8``,
    # two orders up, and digital silence never reaches here (VAD emits
    # speech, and both callers refuse empty PCM).
    #
    # Only the mel block is normalised. The centroid below is a power RATIO,
    # so gain cancels there to within its own ``1e-10`` stabiliser — measured
    # at 1.7e-4 over 20 dB, against 4.61 per un-normalised mel band — and
    # folding it into this mean would mix two units and reintroduce a level
    # dependence.
    if cepstral_mean_normalisation:
        log_mel = log_mel - log_mel.mean()

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


def label_speakers(
    segment_pcms: list[bytes],
    *,
    sample_rate: int = SAMPLE_RATE,
    cepstral_mean_normalisation: bool = True,
) -> list[str]:
    """Speaker label per segment via D8's 2-means over spectral embeddings.

    Fewer than two non-empty segments, or degenerate (identical) features,
    yield a single speaker. Labels are stable: the first segment is always
    ``speaker_1``.

    PAIRED with the inline windowed path in ``transcribe_session`` (round
    42 LOW-011): the pipeline computes embeddings incrementally per window
    to bound plaintext, so it cannot call this whole-list wrapper — both
    sites encode the SAME degenerate-case policy (all ``speaker_1`` when
    fewer than two non-empty segments / any empty PCM); change them
    together. Tests exercise this wrapper; the pipeline path is pinned by
    the windowed-batching tests.

    ``cepstral_mean_normalisation=False`` is the Task 2.3 measurement
    harness's "before Task 2.1" condition (see ``_segment_embedding``);
    the default is the shipped behaviour and nothing in the app passes
    ``False``.
    """
    if not segment_pcms:
        return []
    if len(segment_pcms) < 2 or any(len(pcm) == 0 for pcm in segment_pcms):
        return [SPEAKER_1] * len(segment_pcms)
    np = _numpy()
    embeddings = [
        _segment_embedding(
            pcm,
            np,
            sample_rate=sample_rate,
            cepstral_mean_normalisation=cepstral_mean_normalisation,
        )
        for pcm in segment_pcms
    ]
    return _cluster_embeddings(embeddings, np)


# ---------------------------------------------------------------------------
# Voice attribution against the enrolled profile (practitioner-profile plan
# D3 / D13). Pure numpy functions over per-segment values; the pipeline
# computes the values inside its windowed loop and calls these at the end.
# ---------------------------------------------------------------------------


def _unit_vector(values: Sequence[float], np: Any) -> Any:
    vector = np.asarray(values, dtype=np.float64).reshape(-1)
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm) or norm == 0.0:
        raise ValueError("the enrolled vector has no direction")
    return vector / norm


def _cosine(embedding: Any, reference_unit: Any, np: Any) -> float:
    """RAW cosine similarity in [-1, 1] between a segment embedding and the
    unit-normalised enrolled vector (D3): a zero-norm or non-finite embedding
    scores -1 (no direction to compare), and the result is bounded to
    [-1, 1] only against float dust from two unit vectors — this is not a
    0–1 clamp and the threshold is compared on this scale."""
    vector = np.asarray(embedding, dtype=np.float64).reshape(-1)
    if vector.shape[0] != reference_unit.shape[0]:
        raise ValueError(
            f"segment embedding has {vector.shape[0]} elements; the enrolled vector has "
            f"{reference_unit.shape[0]}"
        )
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm) or norm == 0.0:
        return -1.0
    value = float(np.dot(vector / norm, reference_unit))
    if not math.isfinite(value):
        return -1.0
    return max(-1.0, min(1.0, value))


def enrolled_cluster(
    labels: Sequence[str],
    similarities: Sequence[float | None],
    has_text: Sequence[bool],
) -> tuple[str, float] | None:
    """The cluster the profile confirms as the practitioner and its mean
    similarity (D3/D13, PR-MED-008): among the labels holding at least one
    segment with transcribed text AND at least one computed similarity, the
    one with the highest mean similarity — ties go to the label that
    appears first. ``None`` when no label qualifies (no text, or no segment
    could be embedded), in which case the document carries no attribution
    fields. The mean is a ``math.fsum`` over the label's similarities, so
    segment order cannot move it."""
    if not (len(labels) == len(similarities) == len(has_text)):
        raise ValueError("one label, similarity and text flag per segment")
    scored: dict[str, list[float]] = {}
    textual: set[str] = set()
    first_index: dict[str, int] = {}
    for index, (label, similarity, text) in enumerate(
        zip(labels, similarities, has_text, strict=True)
    ):
        first_index.setdefault(label, index)
        if text:
            textual.add(label)
        if similarity is not None:
            scored.setdefault(label, []).append(similarity)
    candidates = {
        label: math.fsum(values) / len(values)
        for label, values in scored.items()
        if label in textual
    }
    if not candidates:
        return None
    best = max(candidates, key=lambda label: (candidates[label], -first_index[label]))
    return best, max(-1.0, min(1.0, candidates[best]))


def attribute_speakers(
    similarities: Sequence[float | None],
    embeddings: Sequence[Any],
    has_text: Sequence[bool],
    np: Any,
    *,
    threshold: float = ATTRIBUTION_THRESHOLD,
) -> list[str]:
    """Speaker labels with a profile applied (D3 / D13), one per segment.

    A segment MATCHES when its similarity is at or above ``threshold`` (a
    raw cosine; a segment without a similarity never matches). With at
    least one match the matched segments are ``speaker_1`` and the WHOLE
    remainder is ``speaker_2`` (D13 as amended 2026-09-16, Task 2.6): the
    remainder is not clustered, because a 2-means over two or more
    non-identical segments always yields two clusters and so split one
    other voice into two labels in every ordinary two-person consultation;
    a third label (``SPEAKER_3``) returns only when D-S1 estimates the
    speaker count, which needs the shared recording set — until then a
    second other voice is merged into ``speaker_2``, exactly as the
    no-profile path merges it today. With NO match the ordinary 2-means
    over every segment runs and the cluster with the higher mean
    similarity — among clusters holding a segment with transcribed text
    (``enrolled_cluster``) — is ``speaker_1``, the other ``speaker_2``; when
    no cluster holds text the clustering's own first-appearance order
    stands. Callers keep the pipeline's degenerate policy (fewer than two
    embeddable segments -> all ``speaker_1``) BEFORE calling this, exactly
    as ``label_speakers`` mirrors it.
    """
    count = len(similarities)
    if not (len(embeddings) == len(has_text) == count):
        raise ValueError("one similarity, embedding and text flag per segment")
    if count == 0:
        return []
    matched = {i for i, s in enumerate(similarities) if s is not None and s >= threshold}
    if matched:
        return [SPEAKER_1 if i in matched else SPEAKER_2 for i in range(count)]
    labels = _cluster_embeddings(list(embeddings), np) if count >= 2 else [SPEAKER_1]
    chosen = enrolled_cluster(labels, similarities, has_text)
    if chosen is not None and chosen[0] == SPEAKER_2:
        swapped = {SPEAKER_1: SPEAKER_2, SPEAKER_2: SPEAKER_1}
        labels = [swapped[label] for label in labels]
    return labels


# ---------------------------------------------------------------------------
# WhisperSpeechProvider — the real SpeechProvider (D6 as revised at the
# Step 13 gate: faster-whisper, CTranslate2 CPU int8, model `medium`
# by default with `small` as the visible fallback).
# ---------------------------------------------------------------------------


def default_whisper_model_dir(model_name: str = DEFAULT_WHISPER_MODEL) -> Path:
    return default_models_root() / "whisper" / model_name


def whisper_model_available(model_name: str = DEFAULT_WHISPER_MODEL) -> bool:
    """True when the local whisper snapshot looks complete (skip-if-absent).

    Peer round 36: a UNC-redirected ``LOCALAPPDATA`` must not cause SMB
    I/O here — this probe STATS the path, so it applies the same UNC
    refusal as the provider (PR-MED-012 pattern) BEFORE touching the
    filesystem and reports such a model as simply unavailable.
    """
    try:
        model_dir = default_whisper_model_dir(model_name)
    except (RuntimeError, OSError):
        return False
    if str(model_dir).startswith(("\\\\", "//")):
        return False  # UNC: never stat (no SMB I/O); unusable by policy
    return whisper_snapshot_complete(model_dir)


def resolve_whisper_model(model_name: str = DEFAULT_WHISPER_MODEL) -> str:
    """The model the pipeline should actually load (Step 13 fallback policy).

    Returns ``model_name`` when its local snapshot is complete; otherwise
    ``FALLBACK_WHISPER_MODEL`` when THAT snapshot is complete (degrade to
    ``small`` visibly — the UI report names the fallback — rather than
    fail on a machine that never downloaded ``medium``); otherwise
    ``model_name`` unchanged, so the provider's missing-snapshot error
    names the PREFERRED model and its setup-models remedy.

    Resolution is composition-layer policy: ``WhisperSpeechProvider``
    itself stays strict and loads exactly the model it is asked for.
    """
    if whisper_model_available(model_name):
        return model_name
    if model_name != FALLBACK_WHISPER_MODEL and whisper_model_available(
        FALLBACK_WHISPER_MODEL
    ):
        return FALLBACK_WHISPER_MODEL
    return model_name


class WhisperSpeechProvider:
    """Local faster-whisper transcription over one contiguous audio span
    (a packed ~30 s transcription window, or a lone VAD segment).

    Loads the CTranslate2 model from an EXPLICIT local path with
    ``local_files_only=True``; the offline env kill-switches are asserted
    before any ML import (plan: Runtime offline enforcement). Word
    timestamps and word probabilities are always requested — the
    uncertainty marking depends on them.

    The provider is STRICT about the requested model: it loads exactly
    ``model_name`` (or ``model_dir``) or raises. The medium→small
    fallback policy lives in ``resolve_whisper_model`` at the
    composition layer (``ui.models`` factories), never in here.

    ``initial_prompt`` (default: ``CLINICAL_INITIAL_PROMPT``) primes the
    decoder with clinical vocabulary per call — i.e. per packed window,
    which is why windows stay <= 30 s (see ``TRANSCRIBE_WINDOW_SECONDS``);
    pass ``None`` to disable priming, or a custom string to replace it.
    """

    def __init__(
        self,
        model_dir: Path | None = None,
        *,
        model_name: str = DEFAULT_WHISPER_MODEL,
        language: str | None = "en",
        initial_prompt: str | None = CLINICAL_INITIAL_PROMPT,
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
        self._initial_prompt = initial_prompt
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
            # Clinical vocabulary priming (Step 13): fresh left-context per
            # call — one packed <=30 s window (or one oversized lone
            # segment); None disables cleanly (faster-whisper default).
            initial_prompt=self._initial_prompt,
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

    A stale ``note.enc`` is unlinked FIRST (Task 6.2): a re-transcription
    must not leave a note describing a superseded transcript beside the new
    one. Fail-closed ordering — if the stale note cannot be removed, the new
    transcript is NOT written (the hazard is exactly the pairing; Complete
    would refuse the mismatched pair anyway, and the note stays regenerable
    while the key lives). The unlink-then-write pair is not atomic, and round
    45 LOW-003 corrects what that costs: if the unlink SUCCEEDS and the write
    then fails (or the process dies between them), the transcript on disk is
    the OLD one — not superseded at all — and its ratified note is gone. The
    loss is bounded and the direction is still safe: the key is retained, the
    transcript is intact, and the note is regenerable by generating again.
    Reachable only on the resume-processing path, since a queued session
    holding a saved note cannot transition back to processing.
    """
    try:
        (session_dir / NOTE_FILENAME).unlink(missing_ok=True)
    except OSError as exc:
        raise StoreWriteError(f"stale note not removable: {exc}") from exc
    blob = crypto.encrypt(document.to_bytes())
    transcript_path = session_dir / TRANSCRIPT_FILENAME
    # Round 42 MED-008: the binding temp+fsync+replace idiom is implemented
    # ONCE (session_store.atomic_write_bytes) for key.dpapi and this file.
    atomic_write_bytes(transcript_path, blob, error_label="transcript artifact")
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


MarkedSegment = tuple[SpeechSegment, tuple[TranscriptWord, ...]]


def assemble_transcript(
    *,
    session_id: str,
    model_name: str,
    marked_segments: Sequence[MarkedSegment],
    embeddings: Sequence[Any],
    similarities: Sequence[float | None],
    saw_empty_segment: bool,
    attributing: bool,
    speaker_model_id: str | None,
    np: Any,
) -> TranscriptDocument:
    """The speaker pass and document build shared by BOTH transcription
    drivers (note-learning plan Task 1.0, codex PR-MED-005): the batch
    ``transcribe_session`` below and the live ``LiveTranscriber`` drain.
    Extracted verbatim from the batch tail — the per-window loop collects
    the inputs, this decides the labels and builds the artefact; the caller
    writes it. ``np`` is the numpy module the caller already imported for
    the embeddings, or ``None`` when the batch loop skipped them (fewer than
    two segments and no profile); ``speaker_model_id`` is the embedder's id
    whenever one was supplied (recorded on the document only when a cluster
    is actually enrolled).

    Degenerate-case policy mirrors ``label_speakers`` — change together
    (round 42 LOW-011). With a profile applied the SAME degenerate cases
    still yield a single ``speaker_1`` cluster; only the non-degenerate
    clustering is replaced by D13's attribution. ``created_at`` is the wall
    clock, so two documents assembled from equal inputs are equal up to it.
    """
    has_text = [words_have_text(words) for _, words in marked_segments]
    if np is None or saw_empty_segment or len(embeddings) < 2:
        speakers = [SPEAKER_1] * len(marked_segments)
    elif attributing:
        speakers = attribute_speakers(similarities, embeddings, has_text, np)
    else:
        speakers = _cluster_embeddings(list(embeddings), np)
    enrolled = enrolled_cluster(speakers, similarities, has_text) if attributing else None
    return TranscriptDocument(
        session_id=session_id,
        created_at=datetime.now(UTC),
        model_name=model_name,
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
        enrolled_speaker=enrolled[0] if enrolled is not None else None,
        enrolment_similarity=enrolled[1] if enrolled is not None else None,
        speaker_model_id=speaker_model_id if enrolled is not None else None,
    )


def transcribe_session(
    session_dir: Path,
    crypto: SessionCrypto,
    provider: SpeechProvider,
    frame_probability: FrameProbabilityFn,
    *,
    require_footer: bool = True,
    model_name: str = "",
    uncertainty_threshold: float = UNCERTAINTY_THRESHOLD,
    speaker_embedder: SpeakerEmbedder | None = None,
    enrolled_profile: PractitionerProfile | None = None,
) -> TranscriptDocument:
    """Flow 2: VAD -> Whisper per ~30 s window of consecutive segments ->
    word->segment attribution -> uncertainty marks -> speaker labels ->
    ``transcript.enc`` written atomically under the session key.

    Idempotent by construction: rerunning after a crash mid-processing
    reproduces and atomically replaces the transcript. ``require_footer``
    stays True for Finished stores (post-Finish truncation must fail);
    pass False only when recovering a store that never reached Finish.

    ``speaker_embedder`` and ``enrolled_profile`` are supplied TOGETHER (one
    without the other is a ``ValueError``, as is a profile made by a
    different embedder — the composition layer, ``ui.models``, loads the
    profile against the embedder's identity and reports the D2 fallback
    instead of calling this). With both, each segment slice is also embedded
    by the model inside its window and scored against the enrolled vector,
    labels follow ``attribute_speakers`` and the document carries the
    attribution fields (``TranscriptDocument``); without them nothing below
    changes. An embedder failure on a segment propagates like any pipeline
    failure (the session becomes recoverable) — the load contract's smoke
    inference at construction is what keeps that off the consultation path.
    """
    if (speaker_embedder is None) != (enrolled_profile is None):
        raise ValueError("speaker_embedder and enrolled_profile must be supplied together")
    if (
        speaker_embedder is not None
        and enrolled_profile is not None
        and not enrolled_profile.made_by(speaker_embedder)
    ):
        raise ValueError("the enrolled profile was made by a different speaker embedder")
    attributing = speaker_embedder is not None and enrolled_profile is not None
    audio_path = session_dir / AUDIO_FILENAME
    header = read_store_header(audio_path)
    if header.sample_rate != SAMPLE_RATE:
        raise TranscriptionError(
            f"store sample rate {header.sample_rate} is not the pipeline rate {SAMPLE_RATE}"
        )
    segments = segment_session_audio(
        audio_path, crypto, frame_probability, require_footer=require_footer
    )

    # Step 13 batching: consecutive segments are packed into ~30 s windows
    # and the provider runs ONCE per window over the contiguous PCM span
    # [first.start, last.end] (gaps included), so word times stay linear
    # with absolute session time. Per-segment PCM for the D8 embeddings is
    # SLICED out of the same window buffer — the slice arithmetic floors
    # exactly like ``extract_segment_pcm``, so embeddings stay bit-identical
    # to the old per-segment path and speaker attribution is unchanged.
    #
    # PR round 15 invariant, restated for windows: plaintext PCM is bounded
    # by ONE window per iteration (packed windows are <= 30 s ~= 960 KB at
    # 16 kHz mono; a lone VAD segment longer than the budget materialises
    # whole — exactly as the old per-segment path did) and DROPPED at loop
    # advance — only the 25-float speaker embeddings (and, with a profile
    # applied, one similarity float per segment) are retained, never the
    # plaintext audio of the whole consultation. The model embedding for
    # attribution is computed on the SAME slice inside the SAME window and
    # reduced to that one float before the loop advances (plan Critical
    # Constraint: the windowed plaintext bound is unchanged).
    np = _numpy() if len(segments) >= 2 or attributing else None
    reference_unit = (
        _unit_vector(enrolled_profile.embedding, np)
        if attributing and enrolled_profile is not None
        else None
    )
    marked_segments: list[MarkedSegment] = []
    embeddings: list[Any] = []
    similarities: list[float | None] = []
    saw_empty_segment = False
    window_spans = pack_transcription_windows(segments)
    window_segments = [
        SpeechSegment(
            start_seconds=segments[first].start_seconds,
            end_seconds=segments[last - 1].end_seconds,
        )
        for first, last in window_spans
    ]
    pcm_stream = extract_segment_pcm(
        iter_chunks(audio_path, crypto, require_footer=require_footer), window_segments
    )
    for (first, last), window, window_pcm in zip(
        window_spans, window_segments, pcm_stream, strict=True
    ):
        raw_words = provider.transcribe_segment(window_pcm, SAMPLE_RATE)
        window_group = segments[first:last]
        per_segment_words = assign_words_to_segments(
            raw_words, window_group, window_start_seconds=window.start_seconds
        )
        window_byte_start = int(window.start_seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE
        for segment, seg_words in zip(window_group, per_segment_words, strict=True):
            # ``first_in_segment`` (the name heuristic's capitalized-opener
            # exemption) now means "first word ATTRIBUTED to this segment":
            # window-initial words are still model-capitalized exactly like
            # per-segment calls were; mid-window segment openers are only
            # capitalized when the model starts a sentence there, which the
            # same exemption list handles (fail-toward-marking preserved).
            words = mark_words(
                seg_words,
                threshold=uncertainty_threshold,
                offset_seconds=window.start_seconds,
            )
            marked_segments.append((segment, words))
            if np is not None:
                lo = (
                    int(segment.start_seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE
                    - window_byte_start
                )
                hi = (
                    int(segment.end_seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE
                    - window_byte_start
                )
                segment_pcm = window_pcm[lo:hi]
                if segment_pcm:
                    embeddings.append(_segment_embedding(segment_pcm, np))
                else:
                    # Beyond-audio-end segment (VAD zero-pads its last
                    # frame): same degradation as the old per-segment path.
                    saw_empty_segment = True
                if speaker_embedder is not None and reference_unit is not None:
                    # Same slice, same window; reduced to one float here so
                    # the model embedding never outlives the iteration.
                    similarities.append(
                        _cosine(speaker_embedder.embed(segment_pcm), reference_unit, np)
                        if len(segment_pcm) >= MIN_ATTRIBUTION_PCM_BYTES
                        else None
                    )

    document = assemble_transcript(
        session_id=header.session_id,
        model_name=model_name or getattr(provider, "model_name", type(provider).__name__),
        marked_segments=marked_segments,
        embeddings=embeddings,
        similarities=similarities,
        saw_empty_segment=saw_empty_segment,
        attributing=attributing,
        speaker_model_id=speaker_embedder.model_id if speaker_embedder is not None else None,
        np=np,
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
    speaker_embedder: SpeakerEmbedder | None = None,
    enrolled_profile: PractitionerProfile | None = None,
) -> RecoveryOutcome:
    """Flow 3 resume-processing: unwrap the DPAPI key custody and restart
    transcription from audio (idempotent; a partial transcript is replaced
    atomically). A store that reached Finish keeps footer enforcement; a
    store without a footer is transcribed from its durably written chunks
    (truncated tail tolerated as expected crash behaviour) and flagged via
    ``RecoveryOutcome.store_finished`` for the recovery UI.

    ``speaker_embedder`` / ``enrolled_profile`` are passed straight to
    ``transcribe_session`` (D3: both transcription entry points apply the
    profile). The returned crypto lets the caller drive queued -> Complete
    (which destroys the crypto) or Discard.
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
        speaker_embedder=speaker_embedder,
        enrolled_profile=enrolled_profile,
    )
    return RecoveryOutcome(document=document, crypto=crypto, store_finished=store_finished)


# ---------------------------------------------------------------------------
# Live transcription (note-learning plan Phase 1, D1–D3).
#
# The live worker is a DRIVER over plaintext PCM fed by a tee wrapped around
# the capture sink BEFORE encryption. It runs the same stage functions as
# ``transcribe_session`` one window at a time — the streaming segmenter
# below replicates ``speech.segment_probabilities`` frame by frame, the
# packer replicates ``pack_transcription_windows`` greedily, and the per-
# window work (provider, ``assign_words_to_segments``, ``mark_words``, the
# spectral embedding and the enrolment cosine) is the batch loop's, so the
# drained ``LiveResult`` assembles through ``assemble_transcript`` into the
# same document the batch path would produce for the same segments. It never
# holds ``SessionCrypto``, never reads the store and never writes a file
# (D1); the provider, VAD and embedder are constructed on ITS thread at
# start and released on exit, before any batch fallback builds its own (D3).
# ---------------------------------------------------------------------------

# D2 bounds. An open VAD span is force-closed once its padded length would
# reach LIVE_MAX_SEGMENT_SECONDS, at the lowest-probability frame of its last
# LIVE_CUT_SEARCH_SECONDS (the halves are separate, unpadded at the cut, so
# ``pack_transcription_windows`` never sees an oversized live segment).
LIVE_MAX_SEGMENT_SECONDS = 30.0
LIVE_CUT_SEARCH_SECONDS = 5.0
# Plaintext PCM queued by the tee but not yet consumed by the worker — model
# load included — is capped at this many windows' worth of audio; more than
# LIVE_MAX_WINDOWS_BEHIND packed-but-untranscribed windows waiting behind the
# one in progress stops the worker too ("could not keep up").
LIVE_MAX_QUEUED_WINDOWS = 3
LIVE_MAX_WINDOWS_BEHIND = 2
LIVE_QUEUE_CAP_BYTES = int(
    LIVE_MAX_QUEUED_WINDOWS * TRANSCRIBE_WINDOW_SECONDS * SAMPLE_RATE
) * BYTES_PER_SAMPLE
# ``stop()`` joins the worker for at most this long; a timeout is REPORTED
# (the caller never counts the buffers as cleared) — the daemon thread drops
# them itself when its blocked provider call returns.
LIVE_STOP_TIMEOUT_SECONDS = 10.0
# The label a live-posted segment carries: the speaker pass runs only at the
# drain, so a live view must render this as "no speaker yet", never as a
# cluster. The final document replaces every live segment wholesale.
LIVE_SPEAKER_PENDING = "pending"


class LiveFailureKind(enum.StrEnum):
    """Why live mode switched itself off (C8: every fallback names its reason)."""

    MODEL_LOAD = "model_load"
    FELL_BEHIND = "fell_behind"
    WORKER_ERROR = "worker_error"


@dataclass(frozen=True)
class LiveFailure:
    """The first failure a ``LiveTranscriber`` recorded. ``detail`` is the
    exception's type and message (or a fixed phrase) for the status line —
    never transcript text, which no stage function puts in an exception."""

    kind: LiveFailureKind
    detail: str


class LiveTranscriptionError(TranscriptionError):
    """Misuse of the live worker (a programming error, not a fallback)."""


class LiveTranscriptionFailed(LiveTranscriptionError):
    """``drain()`` found the worker failed: the caller runs the batch path."""

    def __init__(self, failure: LiveFailure) -> None:
        super().__init__(f"{failure.kind.value}: {failure.detail}")
        self.failure = failure


class LiveSegmenter:
    """Streaming replica of ``speech.segment_probabilities`` with carried
    state (note-learning plan Task 1.1, D2).

    Same hysteresis, minimum-speech filter, padding, clamping and merge rule
    as the batch segmenter, applied one probability at a time: ``push``
    returns the segments RELEASED by that frame and ``finish`` the remainder,
    and for any probability sequence without a forced close the concatenated
    releases equal ``segment_probabilities`` over the same sequence (the VAD
    determinism pin). A padded segment is held until no later span could
    merge into it: while a span is OPEN whose padded start lies inside the
    held end (it merges when it closes), and until the earliest padded start
    of a future span exceeds that end. With the shipped parameters the
    minimum silence (0.35 s) exceeds twice the padding (0.2 s), so no merge
    is reachable and a release lags the batch decision by zero frames; the
    hold matters only under a configuration where padded spans touch. The
    forced close below bounds the RAW open span, so under such a
    configuration a merged live segment can exceed the bound by the held
    part (unreachable with the shipped parameters).

    The one deliberate departure is the D2 forced close: an open span whose
    padded length would reach ``max_segment_seconds`` is cut at the lowest-
    probability frame of its last ``cut_search_seconds`` (the FIRST minimum on
    a tie). The cut is a hard boundary — neither half is padded at it and the
    second half never merges back — so the batch path, which keeps the whole
    span, differs from the live path exactly there and nowhere else. A second
    half shorter than the minimum speech length at the end of the audio is
    dropped by the same filter that drops any short raw span (residue: up to
    ``min_speech_seconds`` of tail speech after a cut is not transcribed
    live; the batch fallback would keep it).
    """

    def __init__(
        self,
        *,
        frame_seconds: float = FRAME_SECONDS,
        start_threshold: float = START_THRESHOLD,
        end_threshold: float = END_THRESHOLD,
        min_speech_seconds: float = MIN_SPEECH_SECONDS,
        min_silence_seconds: float = MIN_SILENCE_SECONDS,
        pad_seconds: float = PAD_SECONDS,
        max_segment_seconds: float = LIVE_MAX_SEGMENT_SECONDS,
        cut_search_seconds: float = LIVE_CUT_SEARCH_SECONDS,
    ) -> None:
        if not 0.0 < end_threshold <= start_threshold <= 1.0:
            raise ValueError("thresholds must satisfy 0 < end <= start <= 1")
        if frame_seconds <= 0:
            raise ValueError("frame_seconds must be positive")
        if not 0.0 < cut_search_seconds < max_segment_seconds:
            raise ValueError("cut_search_seconds must lie inside max_segment_seconds")
        self._frame_seconds = frame_seconds
        self._start_threshold = start_threshold
        self._end_threshold = end_threshold
        self._min_speech_seconds = min_speech_seconds
        self._min_silence_frames = max(1, round(min_silence_seconds / frame_seconds))
        self._pad_seconds = pad_seconds
        self._max_segment_seconds = max_segment_seconds
        self._cut_search_frames = max(1, round(cut_search_seconds / frame_seconds))
        self._total_frames = 0
        self._in_speech = False
        self._start_frame = 0
        self._hard_start = False
        self._silence_run = 0
        self._recent: deque[tuple[int, float]] = deque(maxlen=self._cut_search_frames)
        self._pending: SpeechSegment | None = None
        self._pending_hard_end = False
        self._finished = False

    @property
    def total_frames(self) -> int:
        return self._total_frames

    @property
    def retention_floor_seconds(self) -> float:
        """A lower bound on the start of every segment not yet released — the
        earliest audio the caller must still hold: a held (pending) segment,
        the open span's padded start, or the earliest padded start a future
        span could have. Used both for PCM retention and by the window packer
        to decide when no future segment can join its open window."""
        floor = max(0.0, self._total_frames * self._frame_seconds - self._pad_seconds)
        if self._pending is not None:
            floor = min(floor, self._pending.start_seconds)
        if self._in_speech:
            lead = 0.0 if self._hard_start else self._pad_seconds
            floor = min(floor, max(0.0, self._start_frame * self._frame_seconds - lead))
        return floor

    def push(self, probability: float) -> list[SpeechSegment]:
        """Consume one frame's speech probability; return released segments."""
        if self._finished:
            raise LiveTranscriptionError("segmenter already finished")
        index = self._total_frames
        self._total_frames = index + 1
        released: list[SpeechSegment] = []
        if not self._in_speech:
            if probability >= self._start_threshold:
                self._in_speech = True
                self._start_frame = index
                self._hard_start = False
                self._silence_run = 0
                self._recent.clear()
        elif probability < self._end_threshold:
            self._silence_run += 1
            if self._silence_run >= self._min_silence_frames:
                released.extend(
                    self._close(self._start_frame, index + 1 - self._silence_run, hard_end=False)
                )
                self._in_speech = False
        else:
            self._silence_run = 0
        if self._in_speech:
            self._recent.append((index, probability))
            released.extend(self._maybe_cut(index))
        released.extend(self._release_pending(final=False))
        return released

    def finish(self) -> list[SpeechSegment]:
        """End of audio: close an open span and release the remainder."""
        if self._finished:
            raise LiveTranscriptionError("segmenter already finished")
        self._finished = True
        released: list[SpeechSegment] = []
        if self._in_speech:
            last = self._total_frames - self._silence_run
            released.extend(self._close(self._start_frame, last, hard_end=False))
            self._in_speech = False
        released.extend(self._release_pending(final=True))
        return released

    def _maybe_cut(self, index: int) -> list[SpeechSegment]:
        span_frames = index + 1 - self._start_frame
        lead = 0.0 if self._hard_start else self._pad_seconds
        if span_frames * self._frame_seconds + lead < self._max_segment_seconds:
            return []
        cut_frame, _probability = min(self._recent, key=lambda entry: entry[1])
        cut_frame = max(cut_frame, self._start_frame + 1)
        released = self._close(self._start_frame, cut_frame, hard_end=True)
        kept = [entry for entry in self._recent if entry[0] >= cut_frame]
        self._start_frame = cut_frame
        self._hard_start = True
        self._recent = deque(kept, maxlen=self._cut_search_frames)
        run = 0
        for _index, probability in reversed(kept):
            if probability >= self._end_threshold:
                break
            run += 1
        self._silence_run = run
        return released

    def _close(self, first: int, last: int, *, hard_end: bool) -> list[SpeechSegment]:
        """Close the raw span ``[first, last)`` of the CURRENT open span (its
        start kind is ``self._hard_start``); returns anything released."""
        start_raw = first * self._frame_seconds
        end_raw = last * self._frame_seconds
        if end_raw - start_raw < self._min_speech_seconds:
            return []
        lead = 0.0 if self._hard_start else self._pad_seconds
        start = max(0.0, start_raw - lead)
        end = end_raw if hard_end else end_raw + self._pad_seconds
        released: list[SpeechSegment] = []
        if self._pending is not None:
            mergeable = (
                not self._hard_start
                and not self._pending_hard_end
                and start <= self._pending.end_seconds
            )
            if mergeable:
                start = self._pending.start_seconds
            else:
                released.append(self._pending)
        self._pending = SpeechSegment(start_seconds=start, end_seconds=end)
        self._pending_hard_end = hard_end
        return released

    def _release_pending(self, *, final: bool) -> list[SpeechSegment]:
        pending = self._pending
        if pending is None:
            return []
        if final:
            total_seconds = self._total_frames * self._frame_seconds
            self._pending = None
            return [
                SpeechSegment(
                    start_seconds=pending.start_seconds,
                    end_seconds=min(total_seconds, pending.end_seconds),
                )
            ]
        if self._pending_hard_end:
            self._pending = None
            return [pending]
        if self._in_speech and not self._hard_start:
            # The OPEN span merges into the pending segment when it closes
            # if its padded start lies inside the pending end — hold until
            # it closes (the batch pass sees both before deciding).
            open_start = max(0.0, self._start_frame * self._frame_seconds - self._pad_seconds)
            if open_start <= pending.end_seconds:
                return []
        earliest_next_start = max(
            0.0, self._total_frames * self._frame_seconds - self._pad_seconds
        )
        if earliest_next_start > pending.end_seconds:
            self._pending = None
            return [pending]
        return []


class _LiveWindows:
    """Incremental ``pack_transcription_windows``: the same greedy predicate
    applied as segments arrive, plus an early flush when the segmenter's
    retention floor proves that no future segment could join the open
    window. Produces the partition the batch packer would over the same
    segment list."""

    def __init__(self, *, window_seconds: float, max_gap_seconds: float) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if max_gap_seconds < 0:
            raise ValueError("max_gap_seconds must be non-negative")
        self._window_seconds = window_seconds
        self._max_gap_seconds = max_gap_seconds
        self._open: list[SpeechSegment] = []
        self.ready: deque[list[SpeechSegment]] = deque()

    def add(self, segment: SpeechSegment) -> None:
        if self._open:
            fits = segment.end_seconds - self._open[0].start_seconds <= self._window_seconds
            gap = segment.start_seconds - self._open[-1].end_seconds
            if not fits or gap > self._max_gap_seconds:
                self.ready.append(self._open)
                self._open = []
        self._open.append(segment)

    def tick(self, next_start_lower_bound: float) -> None:
        """Flush the open window once no segment starting at or after
        ``next_start_lower_bound`` (and ending after it) could join it."""
        if not self._open:
            return
        # Strict on both: a future segment ends AFTER the bound, so its
        # ``end - first.start`` exceeds the bound's — the batch predicate
        # (``<= window_seconds``) then fails for certain, never on a tie.
        cannot_fit = next_start_lower_bound - self._open[0].start_seconds > self._window_seconds
        gap_too_big = next_start_lower_bound - self._open[-1].end_seconds > self._max_gap_seconds
        if cannot_fit or gap_too_big:
            self.ready.append(self._open)
            self._open = []

    def flush(self) -> None:
        if self._open:
            self.ready.append(self._open)
            self._open = []

    @property
    def retention_floor_seconds(self) -> float | None:
        if self.ready:
            return self.ready[0][0].start_seconds
        if self._open:
            return self._open[0].start_seconds
        return None

    def clear(self) -> None:
        self._open = []
        self.ready.clear()


@dataclass(frozen=True)
class LiveResult:
    """Everything the drained live worker hands the processing thread: the
    batch loop's per-segment products, assembled into the document by
    ``assemble`` (= ``assemble_transcript``). ``window_timings`` pairs each
    window's audio seconds with the provider's wall seconds for the benchmark
    panel's live-latency line — numbers only, no text."""

    model_name: str
    marked_segments: tuple[MarkedSegment, ...]
    embeddings: tuple[Any, ...]
    similarities: tuple[float | None, ...]
    saw_empty_segment: bool
    attributing: bool
    speaker_model_id: str | None
    np: Any
    window_timings: tuple[tuple[float, float], ...]

    def assemble(self, session_id: str) -> TranscriptDocument:
        return assemble_transcript(
            session_id=session_id,
            model_name=self.model_name,
            marked_segments=self.marked_segments,
            embeddings=self.embeddings,
            similarities=self.similarities,
            saw_empty_segment=self.saw_empty_segment,
            attributing=self.attributing,
            speaker_model_id=self.speaker_model_id,
            np=self.np,
        )


class _LiveSeal:
    __slots__ = ()


class _LiveWake:
    """Queue sentinel that only wakes the worker (stop or failure)."""

    __slots__ = ()


AttributionFactory = Callable[[], tuple[SpeakerEmbedder | None, PractitionerProfile | None]]
LiveWindowCallback = Callable[[tuple[TranscriptSegment, ...]], None]


def _no_attribution() -> tuple[SpeakerEmbedder | None, PractitionerProfile | None]:
    return None, None


class LiveTranscriber:
    """The queue-fed live transcription worker (note-learning plan Task 1.1).

    Lifecycle: ``start()`` spawns the worker thread, which constructs the VAD,
    the provider and the attribution inputs on ITSELF (D3) — the capture sink
    may already be feeding, and the queue cap covers that period. ``feed``
    (the tee, capture writer thread) never raises: any error flips the worker
    to failed. ``pause``/``resume`` gate feeding — audio arriving while paused
    is a broken control ordering and fails the worker rather than misaligning
    the timeline. ``seal`` is cheap (a sentinel) and is all ``finish()`` does
    on the GUI thread; ``drain`` (the processing thread) waits for the worker
    to transcribe the tail and returns the ``LiveResult``, or raises
    ``LiveTranscriptionFailed`` with the reason for the batch fallback.
    ``stop`` abandons: it joins for a bounded time and reports whether the
    buffers are confirmed cleared. After ``stop`` returns no live-view update
    is delivered (``on_window`` runs under the post lock ``stop`` takes).

    The worker holds no ``SessionCrypto``, no store handle and no path (D1,
    C7); its plaintext is the retention buffer (the open window plus the
    open span, dropped per window), the queued chunks (capped) and the
    per-segment products the result carries. Nothing here logs.
    """

    def __init__(
        self,
        *,
        provider_factory: Callable[[], SpeechProvider],
        vad_factory: Callable[[], FrameProbabilityFn],
        attribution_factory: AttributionFactory = _no_attribution,
        on_window: LiveWindowCallback | None = None,
        model_name: str = "",
        uncertainty_threshold: float = UNCERTAINTY_THRESHOLD,
        window_seconds: float = TRANSCRIBE_WINDOW_SECONDS,
        max_gap_seconds: float = TRANSCRIBE_WINDOW_MAX_GAP_SECONDS,
        max_segment_seconds: float = LIVE_MAX_SEGMENT_SECONDS,
        queue_cap_bytes: int = LIVE_QUEUE_CAP_BYTES,
        max_windows_behind: int = LIVE_MAX_WINDOWS_BEHIND,
        stop_timeout: float = LIVE_STOP_TIMEOUT_SECONDS,
    ) -> None:
        if queue_cap_bytes <= 0 or max_windows_behind < 0 or stop_timeout <= 0:
            raise ValueError(
                "queue_cap_bytes and stop_timeout must be positive; max_windows_behind >= 0"
            )
        self._stop_timeout = stop_timeout
        self._provider_factory = provider_factory
        self._vad_factory = vad_factory
        self._attribution_factory = attribution_factory
        self._on_window = on_window
        self._model_name = model_name
        self._uncertainty_threshold = uncertainty_threshold
        self._segmenter = LiveSegmenter(max_segment_seconds=max_segment_seconds)
        self._windows = _LiveWindows(
            window_seconds=window_seconds, max_gap_seconds=max_gap_seconds
        )
        self._queue_cap_bytes = queue_cap_bytes
        self._max_windows_behind = max_windows_behind

        self._queue: queue.Queue[bytes | _LiveSeal | _LiveWake] = queue.Queue()
        self._account_lock = threading.Lock()
        self._queued_bytes = 0
        self._state_lock = threading.Lock()
        self._post_lock = threading.Lock()
        self._stop_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._failure: LiveFailure | None = None
        self._paused = False
        self._sealed = False
        self._stop_requested = False
        self._seal_seen = False

        # Worker-thread state (touched by the caller only after a join).
        self._vad: FrameProbabilityFn | None = None
        self._provider: SpeechProvider | None = None
        self._embedder: SpeakerEmbedder | None = None
        self._reference_unit: Any = None
        self._np: Any = None
        self._resolved_model_name = ""
        self._pcm = bytearray()
        self._origin_bytes = 0
        self._audio_bytes = 0
        self._framed_bytes = 0
        self._marked: list[MarkedSegment] = []
        self._embeddings: list[Any] = []
        self._similarities: list[float | None] = []
        self._saw_empty_segment = False
        self._window_timings: list[tuple[float, float]] = []
        self._result: LiveResult | None = None

    # --- observers ---------------------------------------------------------

    @property
    def failed_reason(self) -> LiveFailure | None:
        return self._failure

    @property
    def sealed(self) -> bool:
        return self._sealed

    @property
    def stopped(self) -> bool:
        return self._stop_requested

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    @property
    def models_loaded(self) -> bool:
        """True while the worker holds its provider (D3: released on exit,
        before any batch fallback constructs its own)."""
        return self._provider is not None

    @property
    def buffers_cleared(self) -> bool:
        """Inspected, not flagged: no queued chunk, no retained PCM, no
        per-segment product and no undrained result. Meaningful once the
        worker thread has exited (``stop`` returned True, or ``drain``)."""
        with self._queue.mutex:
            queued_pcm = any(isinstance(item, bytes) for item in self._queue.queue)
        return (
            not queued_pcm
            and not self._pcm
            and not self._marked
            and not self._embeddings
            and not self._similarities
            and self._windows.retention_floor_seconds is None
            and self._result is None
        )

    # --- controls (any thread) ----------------------------------------------

    def start(self) -> None:
        with self._state_lock:
            if self._thread is not None:
                raise LiveTranscriptionError("live transcriber already started")
            thread = threading.Thread(
                target=self._run, name="scribe-live-transcriber", daemon=True
            )
            self._thread = thread
        thread.start()

    def feed(self, data: bytes) -> None:
        """Hand one captured chunk to the worker. NEVER raises (the capture
        sink's exception path fails the whole session); every error flips
        this worker to failed instead."""
        try:
            if self._failure is not None or self._stop_requested or self._sealed:
                return
            if self._thread is None:
                self._fail(LiveFailureKind.WORKER_ERROR, "audio arrived before start")
                return
            if self._paused:
                self._fail(LiveFailureKind.WORKER_ERROR, "audio arrived while paused")
                return
            with self._account_lock:
                total = self._queued_bytes + len(data)
                if total > self._queue_cap_bytes:
                    over = True
                else:
                    over = False
                    self._queued_bytes = total
            if over:
                self._fail(
                    LiveFailureKind.FELL_BEHIND,
                    "queued audio exceeded the live transcription cap",
                )
                return
            self._queue.put(bytes(data))
        except Exception as exc:  # noqa: BLE001 - the tee must never raise
            self._fail(LiveFailureKind.WORKER_ERROR, f"{type(exc).__name__}: {exc}")

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def fail(self, detail: str) -> None:
        """Flip the worker to failed (``worker_error``) from any thread
        WITHOUT joining it — the tee's last resort. Never raises."""
        try:
            self._fail(LiveFailureKind.WORKER_ERROR, detail)
        except Exception:  # noqa: BLE001, S110 - a failure record must not raise
            pass

    def seal(self) -> None:
        """No more input. Cheap: the tail is transcribed on the worker and
        collected by ``drain`` — never on the caller's thread."""
        with self._state_lock:
            if self._sealed:
                return
            self._sealed = True
        self._queue.put(_LiveSeal())

    def drain(self) -> LiveResult:
        """Wait for the sealed worker to finish its tail and take its result.
        Raises ``LiveTranscriptionFailed`` when the worker failed (or was
        stopped) — the caller then runs the batch path with the reason."""
        if not self._sealed:
            raise LiveTranscriptionError("drain() requires seal() first")
        thread = self._thread
        if thread is not None:
            thread.join()
        failure = self._failure
        if failure is not None:
            raise LiveTranscriptionFailed(failure)
        result = self._result
        self._result = None
        if result is None:
            raise LiveTranscriptionFailed(
                LiveFailure(LiveFailureKind.WORKER_ERROR, "the live worker produced no result")
            )
        return result

    def stop(self, timeout: float | None = None) -> bool:
        """Abandon: stop the worker, join it for at most ``timeout`` seconds
        (default: the constructor's ``stop_timeout``) and drop every buffer.
        Returns True only when the thread has exited and the buffers are
        CONFIRMED cleared; False on a join timeout (a reported failure — the
        worker clears them itself when its blocked call returns).
        Idempotent; concurrent callers serialize."""
        with self._stop_lock:
            with self._post_lock:
                self._stop_requested = True
            self._queue.put(_LiveWake())
            thread = self._thread
            if thread is not None:
                thread.join(timeout=self._stop_timeout if timeout is None else timeout)
                if thread.is_alive():
                    return False
            self._result = None
            self._clear_buffers()
            return self.buffers_cleared

    # --- failure -----------------------------------------------------------

    def _fail(self, kind: LiveFailureKind, detail: str) -> None:
        with self._state_lock:
            if self._failure is not None:
                return
            self._failure = LiveFailure(kind, detail)
        self._queue.put(_LiveWake())

    # --- worker thread -------------------------------------------------------

    def _run(self) -> None:
        try:
            if not self._load_models():
                return
            while self._failure is None and not self._stop_requested:
                if not self._handle(self._queue.get()):
                    return
                if not self._drain_queue():
                    return
                if not self._process_ready():
                    return
                if self._seal_seen:
                    self._result = self._build_result()
                    return
        except Exception as exc:  # noqa: BLE001 - surfaced through failed_reason
            self._fail(LiveFailureKind.WORKER_ERROR, f"{type(exc).__name__}: {exc}")
        finally:
            self._exit_cleanup()

    def _load_models(self) -> bool:
        try:
            vad = self._vad_factory()
            provider = self._provider_factory()
            embedder, profile = self._attribution_factory()
            np = _numpy()  # the embedding stack is part of the live load
        except Exception as exc:  # noqa: BLE001 - the C8 model-load reason
            self._fail(LiveFailureKind.MODEL_LOAD, f"{type(exc).__name__}: {exc}")
            return False
        if (embedder is None) != (profile is None):
            raise ValueError("speaker_embedder and enrolled_profile must be supplied together")
        if embedder is not None and profile is not None and not profile.made_by(embedder):
            raise ValueError("the enrolled profile was made by a different speaker embedder")
        self._vad = vad
        self._provider = provider
        self._embedder = embedder
        self._np = np
        self._reference_unit = (
            _unit_vector(profile.embedding, self._np) if profile is not None else None
        )
        self._resolved_model_name = self._model_name or getattr(
            provider, "model_name", type(provider).__name__
        )
        self._reset_vad()
        return self._failure is None and not self._stop_requested

    def _reset_vad(self) -> None:
        owner = getattr(self._vad, "__self__", None)
        reset = getattr(owner, "reset", None)
        if callable(reset):
            reset()

    def _handle(self, item: bytes | _LiveSeal | _LiveWake) -> bool:
        """One queue item; False when the worker must exit."""
        if self._failure is not None or self._stop_requested:
            return False
        if isinstance(item, _LiveWake):
            return True
        if isinstance(item, _LiveSeal):
            if not self._seal_seen:
                self._seal_seen = True
                self._finalise_segments()
            return True
        with self._account_lock:
            self._queued_bytes -= len(item)
        if self._seal_seen:
            return True  # never fed after seal; defensive
        self._ingest(item)
        return True

    def _drain_queue(self) -> bool:
        """Ingest queued items until the queue is empty OR a window is ready
        (peer round 10 PR-LOW-022): a ready window is handed to
        ``_process_ready`` BEFORE more chunks are ingested, so the retention
        floor never sits on a deferred window while later audio piles up
        behind it — the retained plaintext is at most the window in
        progress, the open span and one chunk, whatever the producer's pace
        (``_process_ready`` re-drains after every window)."""
        while True:
            if self._windows.ready:
                return self._failure is None and not self._stop_requested
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                return self._failure is None and not self._stop_requested
            if not self._handle(item):
                return False

    def _process_ready(self) -> bool:
        while self._windows.ready:
            if self._failure is not None or self._stop_requested:
                return False
            group = self._windows.ready.popleft()
            behind = len(self._windows.ready)  # waiting behind the one in progress
            # ``_sealed`` (requested), not ``_seal_seen`` (peer round 10
            # PR-LOW-023): once Finish sealed, every remaining queued chunk
            # is a finite tail already bounded by the queue cap — it drains
            # in full and never counts as falling behind.
            if not self._sealed and behind > self._max_windows_behind:
                self._fail(
                    LiveFailureKind.FELL_BEHIND,
                    f"live transcription fell {behind} windows behind",
                )
                return False
            self._transcribe_window(group)
            self._trim()
            if not self._drain_queue():
                return False
        return True

    def _ingest(self, data: bytes) -> None:
        self._pcm.extend(data)
        self._audio_bytes += len(data)
        while self._audio_bytes - self._framed_bytes >= FRAME_BYTES:
            lo = self._framed_bytes - self._origin_bytes
            self._framed_bytes += FRAME_BYTES
            self._push_frame(bytes(self._pcm[lo : lo + FRAME_BYTES]))
        self._trim()
        # Peer round 9 PR-MED-018 / round 10 PR-LOW-022+023: the same
        # windows-behind rule as the pop-time check, evaluated per ingested
        # chunk. With ``_drain_queue`` yielding at the first ready window this
        # is a DEFENSIVE bound — it can fire only when a single ingested chunk
        # closes more than ``max_windows_behind + 1`` windows (an oversized
        # chunk; the capture worker's are one second) — and it honours a
        # requested seal like the pop-time check (a sealed tail drains in
        # full). In practice a provider slower than the feed trips the
        # queue cap in ``feed`` instead.
        behind = len(self._windows.ready) - 1
        if not self._sealed and behind > self._max_windows_behind:
            self._fail(
                LiveFailureKind.FELL_BEHIND,
                f"live transcription fell {behind} windows behind",
            )

    def _push_frame(self, frame: bytes) -> None:
        assert self._vad is not None
        for segment in self._segmenter.push(self._vad(frame)):
            self._windows.add(segment)
        self._windows.tick(self._segmenter.retention_floor_seconds)

    def _finalise_segments(self) -> None:
        remainder = self._audio_bytes - self._framed_bytes
        if remainder > 0:
            lo = self._framed_bytes - self._origin_bytes
            tail = bytes(self._pcm[lo : lo + remainder])
            self._framed_bytes = self._audio_bytes
            self._push_frame(tail + b"\0" * (FRAME_BYTES - remainder))
        for segment in self._segmenter.finish():
            self._windows.add(segment)
        self._windows.flush()

    def _trim(self) -> None:
        floor = self._segmenter.retention_floor_seconds
        window_floor = self._windows.retention_floor_seconds
        if window_floor is not None:
            floor = min(floor, window_floor)
        floor_bytes = int(floor * SAMPLE_RATE) * BYTES_PER_SAMPLE
        drop = min(floor_bytes - self._origin_bytes, len(self._pcm))
        if drop > 0:
            del self._pcm[:drop]
            self._origin_bytes += drop

    def _slice(self, start_bytes: int, end_bytes: int) -> bytes:
        if start_bytes < self._origin_bytes:
            raise LiveTranscriptionError("live PCM retention floor moved past a window")
        lo = start_bytes - self._origin_bytes
        hi = min(end_bytes, self._audio_bytes) - self._origin_bytes
        return bytes(self._pcm[lo:hi]) if hi > lo else b""

    def _transcribe_window(self, group: list[SpeechSegment]) -> None:
        """The batch loop's per-window body over the retained PCM."""
        assert self._provider is not None
        np = self._np
        window = SpeechSegment(
            start_seconds=group[0].start_seconds, end_seconds=group[-1].end_seconds
        )
        window_byte_start = int(window.start_seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE
        window_byte_end = int(window.end_seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE
        window_pcm = self._slice(window_byte_start, window_byte_end)
        started = time.perf_counter()
        raw_words = self._provider.transcribe_segment(window_pcm, SAMPLE_RATE)
        self._window_timings.append(
            (window.duration_seconds, time.perf_counter() - started)
        )
        per_segment_words = assign_words_to_segments(
            raw_words, group, window_start_seconds=window.start_seconds
        )
        posted: list[TranscriptSegment] = []
        for segment, seg_words in zip(group, per_segment_words, strict=True):
            words = mark_words(
                seg_words,
                threshold=self._uncertainty_threshold,
                offset_seconds=window.start_seconds,
            )
            self._marked.append((segment, words))
            lo = int(segment.start_seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE - window_byte_start
            hi = int(segment.end_seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE - window_byte_start
            segment_pcm = window_pcm[lo:hi]
            if segment_pcm:
                self._embeddings.append(_segment_embedding(segment_pcm, np))
            else:
                self._saw_empty_segment = True
            if self._embedder is not None and self._reference_unit is not None:
                self._similarities.append(
                    _cosine(self._embedder.embed(segment_pcm), self._reference_unit, np)
                    if len(segment_pcm) >= MIN_ATTRIBUTION_PCM_BYTES
                    else None
                )
            posted.append(
                TranscriptSegment(
                    start_seconds=segment.start_seconds,
                    end_seconds=segment.end_seconds,
                    speaker=LIVE_SPEAKER_PENDING,
                    transcript_words=words,
                )
            )
        self._post(tuple(posted))

    def _post(self, segments: tuple[TranscriptSegment, ...]) -> None:
        if self._on_window is None:
            return
        with self._post_lock:
            if self._stop_requested:
                return  # a late update after stop() is dropped
            self._on_window(segments)

    def _build_result(self) -> LiveResult:
        result = LiveResult(
            model_name=self._resolved_model_name,
            marked_segments=tuple(self._marked),
            embeddings=tuple(self._embeddings),
            similarities=tuple(self._similarities),
            saw_empty_segment=self._saw_empty_segment,
            attributing=self._embedder is not None,
            speaker_model_id=self._embedder.model_id if self._embedder is not None else None,
            np=self._np,
            window_timings=tuple(self._window_timings),
        )
        self._marked.clear()
        self._embeddings.clear()
        self._similarities.clear()
        return result

    def _exit_cleanup(self) -> None:
        try:
            self._reset_vad()
        except Exception:  # noqa: BLE001, S110 - releasing anyway
            pass
        self._vad = None
        self._provider = None
        self._embedder = None
        self._reference_unit = None
        self._drop_pcm()
        if self._failure is not None or self._stop_requested:
            self._result = None
            self._clear_buffers()

    def _drop_pcm(self) -> None:
        """Every byte of plaintext PCM the worker holds — the open span, the
        packed windows, the queued chunks and their account — gone. Shared by
        every exit (Phase H round 27 SIMP-004: one block, not two copies that
        could drift)."""
        self._pcm = bytearray()
        self._windows.clear()
        with self._account_lock:
            self._queued_bytes = 0
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                return

    def _clear_buffers(self) -> None:
        """The PCM plus every per-segment product (marks, embeddings,
        similarities, timings) — a failed or stopped worker keeps nothing."""
        self._drop_pcm()
        self._marked.clear()
        self._embeddings.clear()
        self._similarities.clear()
        self._window_timings.clear()


__all__ = [
    "CLINICAL_INITIAL_PROMPT",
    "DEFAULT_WHISPER_MODEL",
    "FALLBACK_WHISPER_MODEL",
    "LIVE_CUT_SEARCH_SECONDS",
    "LIVE_MAX_QUEUED_WINDOWS",
    "LIVE_MAX_SEGMENT_SECONDS",
    "LIVE_MAX_WINDOWS_BEHIND",
    "LIVE_QUEUE_CAP_BYTES",
    "LIVE_SPEAKER_PENDING",
    "LIVE_STOP_TIMEOUT_SECONDS",
    "LiveFailure",
    "LiveFailureKind",
    "LiveResult",
    "LiveSegmenter",
    "LiveTranscriber",
    "LiveTranscriptionError",
    "LiveTranscriptionFailed",
    "MIN_ATTRIBUTION_PCM_BYTES",
    "MarkedSegment",
    "SPEAKER_1",
    "SPEAKER_2",
    "SPEAKER_3",
    "TRANSCRIBE_WINDOW_MAX_GAP_SECONDS",
    "TRANSCRIBE_WINDOW_SECONDS",
    "UNCERTAINTY_THRESHOLD",
    "RecoveryOutcome",
    "TranscriptDocument",
    "TranscriptSegment",
    "TranscriptWord",
    "TranscriptionError",
    "TranscriptionModelError",
    "WhisperSpeechProvider",
    "assemble_transcript",
    "assign_words_to_segments",
    "attribute_speakers",
    "default_whisper_model_dir",
    "enrolled_cluster",
    "extract_segment_pcm",
    "is_name_like_token",
    "is_number_token",
    "label_speakers",
    "mark_words",
    "pack_transcription_windows",
    "read_transcript",
    "recover_session_transcription",
    "resolve_whisper_model",
    "segment_has_text",
    "transcribe_session",
    "whisper_model_available",
    "words_have_text",
    "write_transcript",
]
