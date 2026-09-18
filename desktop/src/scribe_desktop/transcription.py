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

import math
import re
from collections.abc import Iterable, Iterator, Sequence
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
    SAMPLE_RATE,
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
    marked_segments: list[tuple[SpeechSegment, tuple[TranscriptWord, ...]]] = []
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

    # Degenerate-case policy mirrors label_speakers — change together
    # (round 42 LOW-011). With a profile applied the SAME degenerate cases
    # still yield a single ``speaker_1`` cluster; only the non-degenerate
    # clustering is replaced by D13's attribution.
    has_text = [words_have_text(words) for _, words in marked_segments]
    if np is None or saw_empty_segment or len(embeddings) < 2:
        speakers = [SPEAKER_1] * len(segments)
    elif attributing:
        speakers = attribute_speakers(similarities, embeddings, has_text, np)
    else:
        speakers = _cluster_embeddings(embeddings, np)
    enrolled = enrolled_cluster(speakers, similarities, has_text) if attributing else None
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
        enrolled_speaker=enrolled[0] if enrolled is not None else None,
        enrolment_similarity=enrolled[1] if enrolled is not None else None,
        speaker_model_id=(
            speaker_embedder.model_id
            if enrolled is not None and speaker_embedder is not None
            else None
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


__all__ = [
    "CLINICAL_INITIAL_PROMPT",
    "DEFAULT_WHISPER_MODEL",
    "FALLBACK_WHISPER_MODEL",
    "MIN_ATTRIBUTION_PCM_BYTES",
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
