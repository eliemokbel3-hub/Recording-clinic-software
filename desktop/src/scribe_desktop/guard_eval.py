"""Invented-text-guard plan Task 1.5 (D7, C12): the transcription-guard
measurement (developer build only, practitioner-run from a normal terminal).

It measures what the SHIPPED pipeline does with sound that is not speech
and with short real utterances, so the guard's constants (decision 0.4)
are chosen from numbers rather than guessed. Every case runs through
``speaker_eval.transcribe_in_temporary_store`` — VAD, window packing, word
assignment and uncertainty marks exactly as a recording gets them — with a
recording provider wrapper that keeps each window's provider words, whose
decode numbers the stored transcript never holds. For every VAD segment the
row is ``transcription.guard_features`` (the rule's own features) plus the
two decode numbers the rule does not read yet; each candidate constant set
is swept through ``transcription.suspect_decision``, so the measured rule is
the shipped rule.

The cases, all synthetic:

- **Beds that are not speech**, synthesised in memory: digital silence;
  Gaussian noise at three absolute levels (``noise_bed``: the set builder's
  ``add_noise`` mixes at a ratio to active speech, which a bed has none
  of); a chord bed (four sines under a slow envelope with short periodic
  bursts); a sung-vowel bed (a harmonic series with vibrato) at two levels.
  Each runs (a) ALONE and (b) PACKED one second after a spoken utterance —
  one transcription window when the VAD finds the bed at all. A bed it
  rejects reaches no decode: alone, the run table counts it as a case
  without a segment; packed, the case shows only its utterance's segment
  (no non-speech row).
- **Short utterances** (``SHORT_UTTERANCES``), spoken by up to three
  installed Windows voices at SAPI rates 0, +5 and +10, so the rate bound
  can sit above the fast tail. Each spoken line goes through the set
  builder's ``sapi_synthesize`` (its per-turn temporary WAV, removed after
  the turn); everything else is in memory.
- **The synthetic set** (``--set``): the validation set's encounters as TRUE
  speech, read through the harness's own readers; a set holding a script
  without synthetic ``conditions`` (a recording of a person) is refused
  before any model loads (C12).

What it enforces: the output is Markdown tables of numbers, yes/no, closed
vocabularies and case ids only — never a word, an utterance or the primer;
an unexpected failure is reported by exception TYPE; a temporary store that
cannot be shown gone stops the run naming its path. The stores' keys live in
memory only (``persist_key=False``). The module opens no file itself, logs
nothing, never reads a Past-sessions folder and refuses a packaged build.
SAPI voices are not human voices: the numbers bound the rule on synthetic
speech only (decision 0.4 states the limit).
"""

from __future__ import annotations

import argparse
import functools
import math
import random
import re
import sys
import tempfile
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, NoReturn, get_args

from scribe_desktop import install_layout
from scribe_desktop.benchmark import apply_offline_env, assert_offline_env
from scribe_desktop.speaker_eval import (
    TEMP_DIR_PREFIX,
    RecordingRefusedError,
    SpeakerEvalError,
    configure_output,
    read_wav_pcm,
    transcribe_in_temporary_store,
)
from scribe_desktop.speech import (
    SAMPLE_RATE,
    FrameProbabilityFn,
    SileroVad,
    SpeechProvider,
    SpeechSegment,
    TranscribedWord,
    vad_model_available,
)
from scribe_desktop.transcription import (
    CLINICAL_INITIAL_PROMPT,
    DEFAULT_WHISPER_MODEL,
    GuardFeatures,
    MarkedSegment,
    TranscriptDocument,
    WhisperSpeechProvider,
    assign_words_to_segments,
    guard_features,
    pack_transcription_windows,
    resolve_whisper_model,
    suspect_decision,
    whisper_model_available,
)
from scribe_desktop.validation import (
    ENCOUNTER_ID_PATTERN,
    EncounterFiles,
    ScriptError,
    _error_type,
    find_encounters,
    load_script,
    read_label_track,
)
from scribe_desktop.validation_set import (
    LEAD_SECONDS,
    TAIL_SECONDS,
    Synthesizer,
    VoiceLister,
    level_turn,
    pcm_samples,
    rms,
    sapi_synthesize,
    sapi_voices,
    to_pcm16,
)

CaseKind = Literal["silence", "noise", "chord", "vowel", "short", "set"]
CASE_KINDS: Final[tuple[str, ...]] = get_args(CaseKind)
_CASE_ID_RE: Final = re.compile(ENCOUNTER_ID_PATTERN)

# The primers a run can decode with: the shipped one (D1, the decision 0.4
# input) or 0.3.1's, which carried an example sentence — for comparison only.
PRIMER_0_3_1: Final = (
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
PRIMERS: Final[dict[str, str]] = {"shipped": CLINICAL_INITIAL_PROMPT, "0.3.1": PRIMER_0_3_1}

# Invented short lines a real speaker says quickly — never printed; a row
# names an utterance by its 1-based position here.
SHORT_UTTERANCES: Final[tuple[str, ...]] = (
    "Yes.",
    "Okay.",
    "No, no, no.",
    "Four out of ten.",
    "One, two, three, four, five.",
    # A real line that echoes the primer ("low back pain"): the echo
    # signal's false-positive path is measured on speech too.
    "Low back pain again.",
)
# The utterance a packed bed follows (never printed).
PACKING_UTTERANCE: Final = "The shoulder has been stiff since the weekend."
SPEAKING_RATES: Final[tuple[int, ...]] = (0, 5, 10)
MAX_VOICES: Final = 3

BED_SECONDS: Final = 6.0
# The packed bed starts this long after the utterance ends: under the 3 s
# gap that closes a transcription window, so both share one window.
PACK_GAP_SECONDS: Final = 1.0
# Levels in dB relative to full scale (speech turns sit at -20 dBFS).
NOISE_LEVELS_DBFS: Final[tuple[int, ...]] = (-50, -40, -30)
MUSIC_LEVELS_DBFS: Final[tuple[int, ...]] = (-20, -30)
_FULL_SCALE: Final = 32767.0
_NOISE_SEED: Final = 20261012
CHORD_HZ: Final[tuple[float, ...]] = (220.0, 277.18, 329.63, 440.0)
CHORD_ENVELOPE_HZ: Final = 0.25
BURST_EVERY_SECONDS: Final = 1.0
BURST_SECONDS: Final = 0.12
VOWEL_F0_HZ: Final = 220.0
VOWEL_HARMONICS: Final = 10
VIBRATO_HZ: Final = 5.5
VIBRATO_DEPTH: Final = 0.03
# Formant centres and width of an open vowel, for the harmonic weights.
VOWEL_FORMANTS_HZ: Final[tuple[float, ...]] = (800.0, 1200.0)
VOWEL_FORMANT_WIDTH_HZ: Final = 250.0


class GuardEvalError(Exception):
    """A measurement fault (names and numbers only)."""


@dataclass(frozen=True)
class Candidate:
    """One candidate constant set for ``suspect_decision`` (D3)."""

    min_words: int
    max_seconds: float
    words_per_second: float
    mean_probability: float
    no_speech_prob: float

    def decide(self, features: GuardFeatures) -> bool:
        return suspect_decision(
            features,
            min_words=self.min_words,
            max_seconds=self.max_seconds,
            words_per_second=self.words_per_second,
            mean_probability=self.mean_probability,
            no_speech_prob=self.no_speech_prob,
        )


# The executor's proposed sweep (Task 3.1), from Task 1.4's decision table:
# the preconditions fixed at 3 words / 1.5 s; rate bounds from 4.0 (the
# observed shape's 4.4 words/s flags with low probability) to above the
# brisk real lines (~4-5 words/s); two probability bounds.
DEFAULT_CANDIDATES: Final[tuple[Candidate, ...]] = tuple(
    Candidate(3, 1.5, rate, probability, 0.6)
    for rate in (4.0, 4.5, 5.5, 6.5)
    for probability in (0.45, 0.6)
)


def parse_candidate(text: str) -> Candidate:
    """``min_words,max_seconds,words_per_second,mean_probability,no_speech``."""
    parts = text.split(",")
    if len(parts) != 5:
        raise argparse.ArgumentTypeError(
            "a candidate is five numbers: min words, max seconds, words per second, "
            "mean probability, no-speech probability"
        )
    try:
        min_words = int(parts[0])
        numbers = [float(part) for part in parts[1:]]
    except ValueError:
        raise argparse.ArgumentTypeError("a candidate's fields must be numbers") from None
    if min_words < 1 or not all(math.isfinite(n) and n >= 0 for n in numbers):
        raise argparse.ArgumentTypeError(
            "a candidate's min words must be at least 1 and its numbers finite and not negative"
        )
    if numbers[2] > 1 or numbers[3] > 1:
        raise argparse.ArgumentTypeError("a candidate's probabilities must be at most 1")
    return Candidate(min_words, *numbers)


# ---------------------------------------------------------------------------
# The beds (pure; samples at 16 kHz as floats on the PCM16 scale).
# ---------------------------------------------------------------------------


def _count(seconds: float) -> int:
    return round(seconds * SAMPLE_RATE)


def _scaled(samples: list[float], level_dbfs: float) -> list[float]:
    level = rms(samples)
    if level == 0.0:
        return samples
    gain = _FULL_SCALE * 10 ** (level_dbfs / 20) / level
    return [value * gain for value in samples]


def silence_bed(seconds: float) -> list[float]:
    return [0.0] * _count(seconds)


def noise_bed(seconds: float, level_dbfs: float, seed: int = _NOISE_SEED) -> list[float]:
    """Gaussian noise from a fixed seed at ``level_dbfs`` RMS."""
    generator = random.Random(seed)
    return _scaled([generator.gauss(0.0, 1.0) for _ in range(_count(seconds))], level_dbfs)


def chord_bed(seconds: float, level_dbfs: float) -> list[float]:
    """Four sines under a slow raised-cosine envelope, with a short burst at
    twice the amplitude every ``BURST_EVERY_SECONDS`` (a strummed or
    percussive accent)."""
    out: list[float] = []
    for index in range(_count(seconds)):
        t = index / SAMPLE_RATE
        envelope = 0.55 - 0.45 * math.cos(2 * math.pi * CHORD_ENVELOPE_HZ * t)
        if (t % BURST_EVERY_SECONDS) < BURST_SECONDS:
            envelope *= 2.0
        out.append(envelope * sum(math.sin(2 * math.pi * hz * t) for hz in CHORD_HZ))
    return _scaled(out, level_dbfs)


def vowel_bed(seconds: float, level_dbfs: float) -> list[float]:
    """A sung open vowel: ``VOWEL_HARMONICS`` harmonics of a fundamental
    with vibrato, weighted 1/k and by two formant bumps."""
    weights = [
        (1.0 / k)
        * (
            0.2
            + sum(
                math.exp(-(((k * VOWEL_F0_HZ - centre) / VOWEL_FORMANT_WIDTH_HZ) ** 2))
                for centre in VOWEL_FORMANTS_HZ
            )
        )
        for k in range(1, VOWEL_HARMONICS + 1)
    ]
    out: list[float] = []
    phase = 0.0
    for index in range(_count(seconds)):
        t = index / SAMPLE_RATE
        f0 = VOWEL_F0_HZ * (1.0 + VIBRATO_DEPTH * math.sin(2 * math.pi * VIBRATO_HZ * t))
        phase += 2 * math.pi * f0 / SAMPLE_RATE
        out.append(sum(w * math.sin(k * phase) for k, w in enumerate(weights, start=1)))
    return _scaled(out, level_dbfs)


@dataclass(frozen=True)
class CaseAudio:
    """One case's PCM and the spans (seconds) where speech is known to be."""

    pcm: bytes
    speech_spans: tuple[tuple[float, float], ...]


def alone(bed: Sequence[float]) -> CaseAudio:
    """``bed`` between the set's lead and tail silences, no speech."""
    samples = [*silence_bed(LEAD_SECONDS), *bed, *silence_bed(TAIL_SECONDS)]
    return CaseAudio(to_pcm16(samples), ())


def packed(utterance_pcm: bytes, bed: Sequence[float]) -> CaseAudio:
    """The utterance (levelled like a set turn) after the lead silence, then
    ``PACK_GAP_SECONDS`` of silence, then ``bed`` — one window (case (b))."""
    turn = level_turn(pcm_samples(utterance_pcm))
    start = LEAD_SECONDS
    end = start + len(turn) / SAMPLE_RATE
    samples = [
        *silence_bed(LEAD_SECONDS),
        *turn,
        *silence_bed(PACK_GAP_SECONDS),
        *bed,
        *silence_bed(TAIL_SECONDS),
    ]
    return CaseAudio(to_pcm16(samples), ((start, end),))


def spoken(utterance_pcm: bytes) -> CaseAudio:
    """A short utterance alone (levelled like a set turn)."""
    turn = level_turn(pcm_samples(utterance_pcm))
    samples = [*silence_bed(LEAD_SECONDS), *turn, *silence_bed(TAIL_SECONDS)]
    return CaseAudio(to_pcm16(samples), ((LEAD_SECONDS, LEAD_SECONDS + len(turn) / SAMPLE_RATE),))


# ---------------------------------------------------------------------------
# The cases.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Case:
    """A case id (the encounter-id pattern: never text), its kind and a
    loader called only when the case runs (so a SAPI or WAV failure is that
    case's error, and one case's audio is held at a time)."""

    case_id: str
    kind: CaseKind
    load: Callable[[], CaseAudio]

    def __post_init__(self) -> None:
        if not _CASE_ID_RE.fullmatch(self.case_id):
            raise GuardEvalError("a case id must match the encounter-id pattern")
        if self.kind not in CASE_KINDS:
            raise GuardEvalError("unknown case kind")


def bed_cases(synthesize: Synthesizer) -> list[Case]:
    """Silence, the three noise levels and both music beds at both levels,
    each alone and packed after ``PACKING_UTTERANCE`` (voice 0, rate 0)."""
    beds: list[tuple[str, CaseKind, Callable[[], list[float]]]] = [
        ("silence", "silence", functools.partial(silence_bed, BED_SECONDS))
    ]
    for level in NOISE_LEVELS_DBFS:
        beds.append((f"noise-{-level}", "noise", functools.partial(noise_bed, BED_SECONDS, level)))
    for level in MUSIC_LEVELS_DBFS:
        beds.append((f"chord-{-level}", "chord", functools.partial(chord_bed, BED_SECONDS, level)))
        beds.append((f"vowel-{-level}", "vowel", functools.partial(vowel_bed, BED_SECONDS, level)))
    cases: list[Case] = []
    for name, kind, make in beds:
        cases.append(Case(f"{name}-alone", kind, functools.partial(_alone_case, make)))
        cases.append(
            Case(f"{name}-packed", kind, functools.partial(_packed_case, synthesize, make))
        )
    return cases


def _alone_case(make: Callable[[], list[float]]) -> CaseAudio:
    return alone(make())


def _packed_case(synthesize: Synthesizer, make: Callable[[], list[float]]) -> CaseAudio:
    return packed(synthesize(PACKING_UTTERANCE, 0, 0), make())


def _spoken_case(synthesize: Synthesizer, text: str, voice: int, rate: int) -> CaseAudio:
    return spoken(synthesize(text, voice, rate))


def short_cases(synthesize: Synthesizer, voices: int) -> list[Case]:
    """Every short utterance at every rate in every voice slot (up to
    ``MAX_VOICES``): ``short-<n>-r<rate>-v<slot>``."""
    return [
        Case(
            f"short-{number}-r{rate}-v{voice}",
            "short",
            functools.partial(_spoken_case, synthesize, text, voice, rate),
        )
        for number, text in enumerate(SHORT_UTTERANCES, start=1)
        for rate in SPEAKING_RATES
        for voice in range(min(voices, MAX_VOICES))
    ]


def set_case(files: EncounterFiles) -> Case:
    """One synthetic encounter: its WAV through ``read_wav_pcm`` and every
    label span (any role) as speech, through the harness's reader."""

    def load() -> CaseAudio:
        track = read_label_track(files.labels)
        pcm = read_wav_pcm(files.wav)
        return CaseAudio(
            pcm, tuple((span.start_seconds, span.end_seconds) for span in track.spans)
        )

    return Case(files.encounter_id, "set", load)


def synthetic_set(encounters: Sequence[EncounterFiles]) -> tuple[list[Case], str | None]:
    """The set's cases, or a refusal (text-free) when any script is unusable
    or not synthetic (C12: a script without ``conditions`` is a recording of
    a person and is never measured here)."""
    cases: list[Case] = []
    for files in encounters:
        refusal: str | None = None
        try:
            script = load_script(files.script)
        except ScriptError as exc:
            refusal = str(exc)  # the loader's own text-free refusal
        if refusal is not None:
            return [], refusal
        if script.conditions is None:
            return [], (
                f"{files.encounter_id} is not a synthetic encounter (its script has no "
                "conditions) - this measurement reads synthetic encounters only"
            )
        cases.append(set_case(files))
    return cases, None


# ---------------------------------------------------------------------------
# Running a case and its rows.
# ---------------------------------------------------------------------------


class _RecordingProvider:
    """The real provider, with each window's provider words kept in call
    order for one case at a time — the decode numbers the transcript never
    stores (the ``speaker_eval._ReplayProvider`` shape). Never printed."""

    def __init__(self, inner: SpeechProvider) -> None:
        self._inner = inner
        self.calls: list[list[TranscribedWord]] = []

    @property
    def model_name(self) -> str:
        return str(getattr(self._inner, "model_name", type(self._inner).__name__))

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        words = list(self._inner.transcribe_segment(pcm, sample_rate))
        self.calls.append(words)
        return list(words)


@dataclass(frozen=True)
class SegmentRow:
    """One VAD segment's numbers (no text): whether it overlaps a known
    speech span, the guard's features, and the two decode numbers the rule
    does not read (the worst over the words: the lowest mean log-probability
    and the highest compression ratio)."""

    case_id: str
    kind: CaseKind
    index: int
    speech: bool
    features: GuardFeatures
    avg_logprob: float | None
    compression_ratio: float | None


def _overlaps(segment: SpeechSegment, spans: Iterable[tuple[float, float]]) -> bool:
    return any(
        start < segment.end_seconds and segment.start_seconds < end for start, end in spans
    )


def segment_rows(
    case: Case,
    document: TranscriptDocument,
    calls: Sequence[Sequence[TranscribedWord]],
    speech_spans: Sequence[tuple[float, float]],
    primer: str,
) -> list[SegmentRow]:
    """Rebuild each VAD segment's provider words the way the pipeline does —
    the SAME packing over the document's segments, one provider call per
    window, the SAME assignment — and compute the guard's features with the
    previous segments as the pipeline accumulates them. A call count that
    differs from the window count, or a segment whose rebuilt words differ
    in number from its stored ones, is a harness fault (that case's error,
    by type)."""
    segments = [
        SpeechSegment(segment.start_seconds, segment.end_seconds)
        for segment in document.transcript_segments
    ]
    windows = pack_transcription_windows(segments)
    if len(windows) != len(calls):
        raise GuardEvalError("the provider calls do not match the transcription windows")
    rows: list[SegmentRow] = []
    previous: list[MarkedSegment] = []
    for (first, last), words in zip(windows, calls, strict=True):
        group = segments[first:last]
        assigned = assign_words_to_segments(
            words, group, window_start_seconds=group[0].start_seconds
        )
        for offset, (segment, seg_words) in enumerate(zip(group, assigned, strict=True)):
            index = first + offset
            stored = document.transcript_segments[index].transcript_words
            if len(seg_words) != len(stored):
                raise GuardEvalError("the rebuilt words do not match the transcript's segments")
            logprobs = [w.decode_avg_logprob for w in seg_words if w.decode_avg_logprob is not None]
            ratios = [
                w.decode_compression_ratio
                for w in seg_words
                if w.decode_compression_ratio is not None
            ]
            rows.append(
                SegmentRow(
                    case_id=case.case_id,
                    kind=case.kind,
                    index=index,
                    speech=_overlaps(segment, speech_spans),
                    features=guard_features(seg_words, segment, previous, primer=primer),
                    avg_logprob=min(logprobs) if logprobs else None,
                    compression_ratio=max(ratios) if ratios else None,
                )
            )
            previous.append((segment, stored))
    return rows


def run_case(
    case: Case,
    provider: SpeechProvider,
    frame_probability: FrameProbabilityFn,
    primer: str,
) -> list[SegmentRow]:
    """One case through the shipped pipeline in a memory-keyed temporary
    store (``persist_key=False``); its audio and provider words are dropped
    once its rows exist."""
    audio = case.load()
    recorder = _RecordingProvider(provider)
    document, _enrolled = transcribe_in_temporary_store(
        audio.pcm, recorder, frame_probability, persist_key=False
    )
    rows = segment_rows(case, document, recorder.calls, audio.speech_spans, primer)
    del audio, document
    recorder.calls.clear()
    return rows


def run_cases(
    cases: Sequence[Case],
    provider: SpeechProvider,
    frame_probability: FrameProbabilityFn,
    primer: str,
    *,
    progress: Callable[[str], None] = print,
) -> tuple[list[SegmentRow], list[tuple[str, str]]]:
    """Every case in turn: ``(rows, errors)``. A case's failure is reported
    by exception TYPE and the run continues; a temporary store that cannot
    be shown gone (``SpeakerEvalError``) propagates and stops it. Every line
    is written after its ``except`` block ends (the harness's round 26)."""
    rows: list[SegmentRow] = []
    errors: list[tuple[str, str]] = []
    for case in cases:
        progress(f"[run ] {case.case_id}")
        failure: str | None = None
        try:
            rows += run_case(case, provider, frame_probability, primer)
        except RecordingRefusedError as exc:
            failure = _error_type(exc)  # a WAV or label refusal: its type only
        except SpeakerEvalError:
            raise  # custody: a temporary store not shown gone stops the run
        except Exception as exc:  # noqa: BLE001 - reported by TYPE only, run continues
            failure = _error_type(exc)
        if failure is not None:
            progress(f"[error] {case.case_id}: {failure}")
            errors.append((case.case_id, failure))
    return rows, errors


# ---------------------------------------------------------------------------
# The report: Markdown tables of numbers, yes/no, closed vocabularies, ids.
# ---------------------------------------------------------------------------

NONE_CELL: Final = "—"
RUN_HEADER: Final[tuple[str, ...]] = (
    "whisper model",
    "primer",
    "cases",
    "errors",
    "cases without a segment",
)
SEGMENT_HEADER: Final[tuple[str, ...]] = (
    "case",
    "kind",
    "segment",
    "speech",
    "seconds",
    "words",
    "words/s",
    "mean p",
    "no-speech",
    "avg logprob",
    "compression",
    "previous empty",
    "echo",
)
SET_SUMMARY_HEADER: Final[tuple[str, ...]] = (
    "speech segments",
    "with words",
    "words/s max",
    "words/s p99",
    "words/s p95",
    "mean p min",
    "mean p p5",
    "no-speech max",
    "echo",
    "previous empty",
)
CANDIDATE_HEADER: Final[tuple[str, ...]] = (
    "candidate",
    "min words",
    "max s",
    "words/s",
    "mean p",
    "no-speech",
    "non-speech flagged",
    "speech flagged",
    *CASE_KINDS,
)


def _number(value: float | None) -> str:
    return NONE_CELL if value is None else f"{value:.3f}"


def _yes(value: bool) -> str:
    return "yes" if value else "no"


def _table(header: Sequence[str], rows: Iterable[Sequence[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


def _segment_cells(row: SegmentRow) -> tuple[str, ...]:
    f = row.features
    return (
        row.case_id,
        row.kind,
        str(row.index),
        _yes(row.speech),
        _number(f.vad_seconds),
        str(f.word_count),
        _number(f.words_per_second),
        _number(f.mean_probability),
        _number(f.no_speech_prob),
        _number(row.avg_logprob),
        _number(row.compression_ratio),
        _yes(f.previous_empty),
        _yes(f.primer_echo),
    )


def _percentile(values: Sequence[float], share: float) -> float | None:
    """The nearest-rank percentile (``share`` in (0, 1]); None for none."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(share * len(ordered)) - 1)]


def _set_summary(rows: Sequence[SegmentRow]) -> tuple[str, ...]:
    speech = [row for row in rows if row.kind == "set" and row.speech]
    worded = [row for row in speech if row.features.word_count > 0]
    rates = [row.features.words_per_second for row in worded]
    means = [p for row in worded if (p := row.features.mean_probability) is not None]
    no_speech = [p for row in worded if (p := row.features.no_speech_prob) is not None]
    return (
        str(len(speech)),
        str(len(worded)),
        _number(max(rates) if rates else None),
        _number(_percentile(rates, 0.99)),
        _number(_percentile(rates, 0.95)),
        _number(min(means) if means else None),
        _number(_percentile(means, 0.05)),
        _number(max(no_speech) if no_speech else None),
        str(sum(row.features.primer_echo for row in worded)),
        str(sum(row.features.previous_empty for row in worded)),
    )


def _flagged(rows: Iterable[SegmentRow], candidate: Candidate) -> str:
    """``flagged/with words`` over ``rows``."""
    worded = [row for row in rows if row.features.word_count > 0]
    flagged = sum(candidate.decide(row.features) for row in worded)
    return f"{flagged}/{len(worded)}"


def _candidate_cells(
    number: int, candidate: Candidate, rows: Sequence[SegmentRow]
) -> tuple[str, ...]:
    return (
        f"c{number}",
        str(candidate.min_words),
        _number(candidate.max_seconds),
        _number(candidate.words_per_second),
        _number(candidate.mean_probability),
        _number(candidate.no_speech_prob),
        _flagged((row for row in rows if not row.speech), candidate),
        _flagged((row for row in rows if row.speech), candidate),
        *(_flagged((row for row in rows if row.kind == kind), candidate) for kind in CASE_KINDS),
    )


def render_report(
    rows: Sequence[SegmentRow],
    candidates: Sequence[Candidate],
    errors: Sequence[tuple[str, str]],
    *,
    whisper_model: str,
    primer_name: str,
    cases: int,
    all_rows: bool = False,
) -> str:
    """The text-free report. The run table counts the cases without a
    segment (ran, no error, no row: the VAD found nothing to decode — an
    errored case has no row either). Segment rows for every case but the
    set's (all of them with ``all_rows``); the set's speech segments
    summarised; one candidate row per constant set: ``flagged/with words``
    among non-speech segments, speech segments and each case kind."""
    segmentless = cases - len({row.case_id for row in rows}) - len(errors)
    lines = [
        "# Transcription guard measurement",
        "",
        *_table(
            RUN_HEADER,
            [(whisper_model, primer_name, str(cases), str(len(errors)), str(segmentless))],
        ),
        "",
        "## Segments",
        "",
        *_table(
            SEGMENT_HEADER,
            (_segment_cells(row) for row in rows if all_rows or row.kind != "set"),
        ),
        "",
        "## The synthetic set's speech segments",
        "",
        *_table(SET_SUMMARY_HEADER, [_set_summary(rows)]),
        "",
        "## Candidates (flagged / segments with words)",
        "",
        *_table(
            CANDIDATE_HEADER,
            (
                _candidate_cells(number, candidate, rows)
                for number, candidate in enumerate(candidates, start=1)
            ),
        ),
    ]
    if errors:
        lines += ["", "## Errors", "", *_table(("case", "error"), errors)]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The command line.
# ---------------------------------------------------------------------------


class _QuietParser(argparse.ArgumentParser):
    """argparse's own errors quote what they could not parse (``invalid
    choice: …``, ``unrecognized arguments: …``), so a command-line error is
    fixed text, with the usage (option names only) on stderr — the house
    shape of the kept-recordings replay tool (peer round 3 PR-LOW-001)."""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, "[refused] the command line was not understood - see --help\n")


def _parser() -> argparse.ArgumentParser:
    parser = _QuietParser(
        description=(
            "Measure the transcription guard's features (invented-text-guard plan D7) over "
            "synthesised beds, short synthetic utterances and a synthetic validation set, "
            "through the shipped pipeline, and print text-free tables. Developer build only."
        )
    )
    parser.add_argument(
        "--set",
        dest="set_dir",
        type=Path,
        required=True,
        help="a synthetic validation-set folder (scripts\\build-validation-set.py makes one)",
    )
    parser.add_argument(
        "--candidates",
        type=parse_candidate,
        nargs="+",
        default=list(DEFAULT_CANDIDATES),
        help=(
            "constant sets to sweep, each 'min_words,max_seconds,words_per_second,"
            "mean_probability,no_speech' (default: the proposed sweep)"
        ),
    )
    parser.add_argument(
        "--primer",
        choices=sorted(PRIMERS),
        default="shipped",
        help="decode with the shipped primer (default) or 0.3.1's, for comparison only",
    )
    parser.add_argument(
        "--allow-small",
        action="store_true",
        help="measure with whisper `small` when `medium` is not installed (the report says so)",
    )
    parser.add_argument(
        "--all-rows",
        action="store_true",
        help="also print every segment row of the synthetic set",
    )
    return parser


def main(
    argv: list[str] | None = None,
    *,
    voices: VoiceLister = sapi_voices,
    synthesize: Synthesizer = sapi_synthesize,
) -> int:
    """Exit status 0 when every case ran; 2 for a refusal before any case
    runs; 1 otherwise. Refusals, in ``validation.main``'s order: a packaged
    build (``install_layout.channel``, read at call time), then the offline
    environment is applied and asserted, a missing set folder, the models
    (by name, before any is constructed), an unreadable set, a set holding
    an unusable or non-synthetic script, no installed voice, and models that
    cannot be loaded (by exception type)."""
    configure_output()
    args = _parser().parse_args(argv)
    if install_layout.channel() != "dev":
        print("[refused] the guard measurement runs only on the developer build")
        return 2
    apply_offline_env()
    assert_offline_env()
    set_dir: Path = args.set_dir
    if not set_dir.is_dir():
        print(f"[refused] --set {set_dir} is not a folder")
        return 2

    models_failure: str | None = None
    try:
        models = install_layout.models_root()
    except (OSError, RuntimeError) as exc:
        models_failure = type(exc).__name__
    if models_failure is not None:
        print(f"[refused] the models folder cannot be located ({models_failure})")
        return 2
    whisper = resolve_whisper_model()
    if not whisper_model_available(whisper):
        print(
            f"[refused] no Whisper model is installed in {models}: "
            f"{install_layout.model_remedy()}"
        )
        return 2
    if whisper != DEFAULT_WHISPER_MODEL and not args.allow_small:
        print(
            f"[refused] Whisper `{DEFAULT_WHISPER_MODEL}` is not installed in {models} (only "
            f"`{whisper}` is): {install_layout.model_remedy()}, or pass --allow-small to "
            "measure with it"
        )
        return 2
    if not vad_model_available():
        print(
            f"[refused] the silero VAD model is not installed in {models}: "
            f"{install_layout.model_remedy()}"
        )
        return 2

    listing_failure: str | None = None
    try:
        encounters, incomplete = find_encounters(set_dir)
    except OSError as exc:
        listing_failure = type(exc).__name__
    if listing_failure is not None:
        print(f"[refused] {set_dir} cannot be listed ({listing_failure})")
        return 2
    if incomplete or not encounters:
        for name, problem in incomplete:
            print(f"[refused] {name}: {problem}")
        if not encounters:
            print(f"[refused] no complete encounters in {set_dir}")
        return 2
    set_cases, refusal = synthetic_set(encounters)
    if refusal is not None:
        print(f"[refused] {refusal}")
        return 2

    voice_failure: str | None = None
    voice_count = 0
    try:
        voice_count = len(voices())
    except Exception as exc:  # noqa: BLE001 - reported by TYPE
        voice_failure = _error_type(exc)
    if voice_failure is not None:
        print(f"[refused] the Windows voices cannot be listed ({voice_failure})")
        return 2
    if voice_count == 0:
        print("[refused] no Windows voice is installed")
        return 2

    primer = PRIMERS[args.primer]
    load_failure: str | None = None
    load_interrupted = False
    try:
        vad = SileroVad()
        provider = WhisperSpeechProvider(model_name=whisper, initial_prompt=primer)
    except KeyboardInterrupt:
        load_interrupted = True
    except Exception as exc:  # noqa: BLE001 - reported by TYPE
        load_failure = _error_type(exc)
    if load_interrupted:
        print("[stopped] the run was interrupted while the models loaded; nothing was run")
        return 1
    if load_failure is not None:
        print(f"[refused] the models could not be loaded ({load_failure})")
        return 2

    cases = [*bed_cases(synthesize), *short_cases(synthesize, voice_count), *set_cases]
    custody: str | None = None
    interrupted = False
    try:
        rows, errors = run_cases(cases, provider, vad.frame_probability, primer)
    except SpeakerEvalError as exc:
        custody = str(exc)  # module-own text naming the path
    except KeyboardInterrupt:
        interrupted = True
    if custody is not None:
        print(f"[custody] the run stopped: {custody}")
        return 1
    if interrupted:
        print(
            "[stopped] the run was interrupted, so there is no report - look in "
            f"{tempfile.gettempdir()} for a {TEMP_DIR_PREFIX}* folder an interrupted "
            "teardown may have left, and delete it"
        )
        return 1
    print()
    print(
        render_report(
            rows,
            args.candidates,
            errors,
            whisper_model=whisper,
            primer_name=args.primer,
            cases=len(cases),
            all_rows=args.all_rows,
        )
    )
    return 0 if not errors else 1


__all__ = [
    "CASE_KINDS",
    "DEFAULT_CANDIDATES",
    "PACKING_UTTERANCE",
    "PRIMERS",
    "PRIMER_0_3_1",
    "SHORT_UTTERANCES",
    "Candidate",
    "Case",
    "CaseAudio",
    "GuardEvalError",
    "SegmentRow",
    "alone",
    "bed_cases",
    "chord_bed",
    "main",
    "noise_bed",
    "packed",
    "parse_candidate",
    "render_report",
    "run_case",
    "run_cases",
    "segment_rows",
    "set_case",
    "short_cases",
    "silence_bed",
    "spoken",
    "synthetic_set",
    "vowel_bed",
]
