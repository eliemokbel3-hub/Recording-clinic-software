"""Task 2.3 measurement harness: speaker-cluster and role accuracy on
practitioner-labelled recordings, before and after Task 2.1 (Phase 3A).

What it measures (plan Design Decision "measure the SHIPPED pipeline"):
each ``<name>.wav`` (16 kHz mono 16-bit PCM) is written into a fresh,
temporary, encrypted session store with a real DPAPI-wrapped key and run
through ``transcribe_session`` UNCHANGED — its speaker labels ARE the
"after" condition, exactly what the app would show. The "before" condition
re-embeds the SAME VAD segments with ``label_speakers(...,
cepstral_mean_normalisation=False)``, so the two conditions differ by
precisely the Task 2.1 line. Ground truth is an Audacity label track
(``<name>.txt``) whose labels are ROLE names; ``clinician`` must be one of
them. Results are a Markdown table ready to paste into the plan's Task 2.3.

What this module enforces, and what it does not:

- **No clinical content escapes.** The module logs nothing. Its result
  types carry counts, seconds, labels, verdicts and the recording's file
  stem — no ``TranscriptDocument``, no words — so the report and every
  ``repr`` are text-free by construction; ``SpeakerEvidence`` is text-free
  by design. The one residue is the file stem itself, which the report
  echoes: the practitioner names the files.
- **The temporary store is torn down key-first on every path, and
  whatever survives is reported by path.** ``_destroy_temporary_store``
  runs after success and inside the failure handler alike, and the guard
  begins the moment the in-memory key exists. Every leg is attempted
  whatever the earlier legs did — unlink ``key.dpapi``, destroy the
  in-memory key, remove the session directory, remove the temporary root,
  each reached through a ``finally`` — and destruction of the in-memory
  key is attempted on every exit, a failed attempt being surfaced (the key
  then dies with the process). Every leg failure the OS reports is
  surfaced, even when a later leg recovered the state; a path that is
  already gone is not a failure; a removal that fails stops at its first
  error and leaves the rest to the later legs and the probe. The final
  probe fails closed: only a positive ``FileNotFoundError`` counts as gone.
  Teardown returns normally only when the root is positively gone, the key
  is destroyed and no leg failed; otherwise it raises a ``SpeakerEvalError``
  naming the temporary root (or stating that none was created), the key
  state and every leg failure, chained to whatever exception was already in
  flight; an interrupt inside a leg propagates only after the remaining
  legs ran, chained to any residue fault. On the failure path the
  suspended decrypt-stream generators are released first so an open
  handle cannot pin ``audio.enc``. What this cannot do is delete or
  inspect what the OS refuses: that residue is named for the practitioner
  to remove by hand, never hidden. The practitioner's own WAV and label
  files are never written, moved or deleted; their retention stays the
  practitioner's decision.
- **Runtime offline.** ``main`` applies and asserts the offline
  kill-switches BEFORE any model is constructed (the ``benchmark.main``
  order); the module opens no socket and imports no ML stack at import
  time.
- **Not the app's plaintext bound.** The "before" condition holds every
  VAD segment's PCM in memory at once (``label_speakers`` is a whole-list
  wrapper), unlike the pipeline's one-window bound. The WAV is already
  plaintext on the practitioner's disk, so this widens nothing at rest.

Input contract (practitioner-decided 2026-09-03): one directory of
``<name>.wav`` / ``<name>.txt`` pairs; any other WAV rate, channel count or
sample width is REFUSED per file (no resampling); a lone WAV or lone label
file is reported and skipped.

The **enrolled** condition (practitioner-profile plan Task 2.4): with
``--enrolment <wav>`` (16 kHz mono, refused otherwise) the practitioner's
enrolment vector is produced by the shipped ``enrolment.enrol`` and wrapped in
a synthetic IN-MEMORY ``PractitionerProfile`` that is never written anywhere —
this module imports no profile store and owns none; the teardown contract
above is untouched. Each recording is then run through the SHIPPED
``transcribe_session`` a second time with the shipped embedder and that
profile, over the same temporary store, with the first pass's window
transcriptions replayed from memory (VAD segmentation and window packing are
deterministic over one store, so no second Whisper run is paid; an unseen
window still goes to the real provider); a segmentation that differs between
the passes is a harness fault, never a number. Its labels are the third
condition: ``cluster_metrics`` is computed even when every label is
``speaker_1`` — a one-cluster enrolled output is scored whatever produced it,
every segment matching the profile (the false-positive case the condition
exists to measure) or a degenerate clustering after no segment matched, since
the labels alone do not say which and the legacy "merged" exclusion would hide
exactly the case that matters (the legacy two conditions keep their merged
semantics) — and the auto-confirmed cluster (``enrolled_speaker``, what the Transcript screen
pre-checks under D4) gets its own ``RoleOutcome``. Without ``--enrolment``
and with two or more pairs, the documented fallback enrols each recording
from the clinician-labelled spans of the OTHER recordings (leave-one-out);
with one pair and no enrolment WAV the condition is absent and reported.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import itertools
import math
import os
import secrets
import shutil
import sys
import tempfile
import traceback
import wave
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean
from typing import Final, Literal

from scribe_desktop.benchmark import apply_offline_env, assert_offline_env
from scribe_desktop.enrolment import EnrolmentError, enrol
from scribe_desktop.note import SpeakerRolePreselection, speaker_role
from scribe_desktop.practitioner_profile import ConsentRecord, PractitionerProfile
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import (
    AUDIO_FILENAME,
    KEY_FILENAME,
    SessionChunkStore,
    delete_session_key,
    wrap_key_to_file,
)
from scribe_desktop.speaker_embedding import (
    SpeakerEmbedder,
    SpeakerModelError,
    build_speaker_embedder,
)
from scribe_desktop.speech import (
    BYTES_PER_SAMPLE,
    SAMPLE_RATE,
    FrameProbabilityFn,
    SileroVad,
    SpeechProvider,
    SpeechSegment,
    TranscribedWord,
)
from scribe_desktop.transcription import (
    SPEAKER_1,
    TranscriptDocument,
    WhisperSpeechProvider,
    extract_segment_pcm,
    label_speakers,
    resolve_whisper_model,
    transcribe_session,
)

# The one label every track must carry (compared case-insensitively after
# strip; stored casefolded). Every other label is a free role name.
CLINICIAN_LABEL: Final = "clinician"
# A VAD segment whose majority label covers less than this share of its
# overlapped duration is MIXED: still scored by majority, but counted,
# because it bounds the achievable accuracy.
MIXED_MAJORITY_SHARE: Final = 0.8
# Float-noise tolerances, NOT confidence thresholds: two overlap durations
# within ``_SECONDS_EPSILON`` of each other are a TIE (no majority - a
# spelling may never break it), and a majority share within
# ``_SHARE_EPSILON`` of ``MIXED_MAJORITY_SHARE`` meets it (decimal timestamps
# such as 0.3/0.7/0.8 put a mathematically exact 80 % a few ulps under).
_SECONDS_EPSILON: Final = 1e-9
_SHARE_EPSILON: Final = 1e-9
# Condition names, printed as-is in the report.
BEFORE: Final = "before"
AFTER: Final = "after"
ENROLLED: Final = "enrolled"
# The synthetic in-memory profile's fixed fields (never persisted). The consent
# version is a placeholder that satisfies the record's pattern: attribution never
# reads the consent record, so this value is NOT kept in step with the app's
# current text version (``ui.models.CONSENT_TEXT_VERSION``) and means nothing
# here (round 51 LOW-003).
HARNESS_DEVICE_NAME: Final = "measurement harness (in-memory profile, never saved)"
HARNESS_CONSENT_VERSION: Final = "consent-v1"
# Store chunking for the temporary session (1 s of PCM, the test-suite shape).
STORE_CHUNK_BYTES: Final = SAMPLE_RATE * BYTES_PER_SAMPLE
TEMP_DIR_PREFIX: Final = "scribe-speaker-eval-"
# The LITERALS here and in ``render_report`` are ASCII (``->`` / ``>`` /
# ``x`` / ``\`` where the plan wrote ``→`` / ``▸``) so the table reads the
# same on any code page. That is not what keeps a run alive: the dynamic
# fields - file stems, the practitioner's role labels, the model name - are
# unrestricted Unicode, and ``_configure_output`` (called first thing in
# ``main``) is what stops them raising ``UnicodeEncodeError`` on a
# redirected, code-page-encoded stdout.
WAV_FORMAT_HELP: Final = (
    "16 kHz, mono, 16-bit PCM WAV - in Audacity: Project Rate 16000 -> "
    "Tracks > Mix > Mix Stereo Down to Mono -> Export Audio > WAV 16-bit PCM"
)

RoleVerdict = Literal["CORRECT", "WRONG", "NONE"]


class SpeakerEvalError(Exception):
    """Base class for harness failures."""


class RecordingRefusedError(SpeakerEvalError):
    """One recording's inputs are unusable; the run continues with the rest."""


class LabelTrackError(RecordingRefusedError):
    """The Audacity label track is malformed or carries no ``clinician``."""


class WavFormatError(RecordingRefusedError):
    """The WAV is not 16 kHz mono 16-bit PCM (no resampling is performed)."""


class HarnessFaultError(SpeakerEvalError):
    """``label_speakers`` disagreed with the pipeline over identical segments
    (the two sites must mirror one degenerate-case policy, round 42 LOW-011),
    or the enrolled pass segmented the same store differently from the plain
    pass: a harness/pipeline drift, not a measurement."""


# ---------------------------------------------------------------------------
# Inputs: Audacity label tracks and WAV files.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LabelSpan:
    """One labelled stretch, seconds from the start of the recording."""

    start_seconds: float
    end_seconds: float
    label: str


@dataclass(frozen=True)
class LabelTrack:
    """A parsed label track: spans in file order plus the distinct labels."""

    spans: tuple[LabelSpan, ...]
    labels: tuple[str, ...]
    point_labels_ignored: int


def parse_audacity_labels(text: str) -> LabelTrack:
    """Parse an Audacity exported label track (``start<TAB>end<TAB>label``).

    Rows beginning with ``\\`` (spectral-selection rows) are ignored; a point
    label (``start == end``) is ignored and counted; blank lines are skipped.
    Any other malformed row refuses the file, naming its line number.
    Labels are stripped and casefolded; exactly one distinct label must
    equal ``clinician``. Two spellings of ANY role that differ only by case
    are refused rather than silently scored as two speakers — a stricter
    reading than the task's clinician-only rule, chosen because the
    alternative is a wrong speaker count with no signal. Overlapping or
    gapped spans are data, not errors.
    """
    spans: list[LabelSpan] = []
    point_labels = 0
    for number, raw in enumerate(text.splitlines(), start=1):
        if raw.startswith("\\") or not raw.strip():
            continue
        parts = raw.split("\t")
        if len(parts) != 3:
            raise LabelTrackError(
                f"line {number}: expected start<TAB>end<TAB>label, found {len(parts)} field(s)"
            )
        try:
            start, end = float(parts[0]), float(parts[1])
        except ValueError:
            raise LabelTrackError(f"line {number}: start and end must be seconds") from None
        label = parts[2].strip()
        if not label:
            raise LabelTrackError(f"line {number}: empty label")
        if not (math.isfinite(start) and math.isfinite(end)) or start < 0 or end < start:
            raise LabelTrackError(f"line {number}: a label span must satisfy 0 <= start <= end")
        if start == end:
            point_labels += 1
            continue
        spans.append(LabelSpan(start, end, label))

    spellings: dict[str, list[str]] = {}
    for spelling in sorted({span.label for span in spans}):
        spellings.setdefault(spelling.casefold(), []).append(spelling)
    found = ", ".join(sorted(spelling for group in spellings.values() for spelling in group))
    collisions = [group for group in spellings.values() if len(group) > 1]
    if collisions:
        raise LabelTrackError(
            "labels that differ only by case are refused (one role, one spelling): "
            + "; ".join(" / ".join(group) for group in collisions)
            + f"; labels found: {found}"
        )
    if CLINICIAN_LABEL not in spellings:
        raise LabelTrackError(
            f"no {CLINICIAN_LABEL!r} label in the track; labels found: {found or '(none)'}"
        )
    return LabelTrack(
        spans=tuple(
            LabelSpan(span.start_seconds, span.end_seconds, span.label.casefold())
            for span in spans
        ),
        labels=tuple(sorted(spellings)),
        point_labels_ignored=point_labels,
    )


def read_wav_pcm(path: Path) -> bytes:
    """The PCM16 bytes of a 16 kHz mono 16-bit WAV; anything else is refused
    with the required format and the Audacity conversion recipe. Every
    accepted recording is a non-empty run of COMPLETE frames: a header-only
    (zero-frame) file is refused, and the read asks ``wave`` for one frame
    MORE than the header declares, so a partial trailing sample (which
    ``wave`` floors out of its frame count) comes back as a longer read and
    a truncated data chunk as a shorter one — both refused."""
    try:
        with wave.open(str(path), "rb") as reader:
            channels = reader.getnchannels()
            width = reader.getsampwidth()
            rate = reader.getframerate()
            if (channels, width, rate) != (1, BYTES_PER_SAMPLE, SAMPLE_RATE):
                raise WavFormatError(
                    f"{path.name} is {rate} Hz, {channels} channel(s), {width * 8}-bit; "
                    f"required: {WAV_FORMAT_HELP}"
                )
            frames = reader.getnframes()
            if frames == 0:
                raise WavFormatError(
                    f"{path.name} holds no audio frames; required: {WAV_FORMAT_HELP}"
                )
            # ``readframes`` reads up to the END of the data chunk, so asking
            # for one frame more than declared exposes a partial final frame.
            pcm = reader.readframes(frames + 1)
            expected = frames * BYTES_PER_SAMPLE
            if len(pcm) > expected:
                raise WavFormatError(
                    f"{path.name} ends with a partial sample ({len(pcm) - expected} stray "
                    f"byte(s) after {frames} frames); re-export it ({WAV_FORMAT_HELP})"
                )
            if len(pcm) < expected:
                raise WavFormatError(
                    f"{path.name} is truncated: its header declares {frames} frames but "
                    f"only {len(pcm) // BYTES_PER_SAMPLE} could be read; re-export it "
                    f"({WAV_FORMAT_HELP})"
                )
            return pcm
    except (wave.Error, EOFError) as exc:
        # The stdlib's own message is deliberately NOT echoed: this module's
        # refusal text is built only from names, formats and paths (see main).
        raise WavFormatError(
            f"{path.name} is not a readable WAV file; required: {WAV_FORMAT_HELP}"
        ) from exc


# ---------------------------------------------------------------------------
# Alignment: VAD segments -> ground-truth labels.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SegmentTruth:
    """One VAD segment's ground truth. ``true_label`` is None when no label
    overlaps it (UNLABELLED — excluded from every metric but counted) and
    when the top two labels TIE (``tied``: no majority exists and no
    spelling may invent one, so the segment is MIXED, counted, and scored
    by nobody). ``majority_share`` is the leading label's overlap over the
    segment's total overlapped duration; under ``MIXED_MAJORITY_SHARE`` (by
    more than ``_SHARE_EPSILON``) it is MIXED."""

    start_seconds: float
    end_seconds: float
    true_label: str | None
    majority_share: float
    mixed: bool
    tied: bool = False

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


def _total(values: Iterable[float]) -> float:
    """The correctly rounded sum of finite durations. ``math.fsum``
    accumulates exactly and rounds once, so its result does not depend on
    the order the values arrive in — which is what keeps every reported
    number independent of label spelling, segment order and permutation
    order (round 65 PR-LOW-009). No sorting is needed, and none would add
    anything: the guarantee is ``fsum``'s, not an ordering's."""
    return math.fsum(values)


def align_segments(
    segments: Sequence[SpeechSegment], track: LabelTrack
) -> tuple[SegmentTruth, ...]:
    """Ground truth per segment: the label with the largest overlap duration
    against ``[start, end)``. Overlaps of one label across several spans
    add up; the share denominator is the sum over ALL labels' overlaps, so
    two roles labelled over the same stretch split it (and read as MIXED).
    A tie for the lead (within ``_SECONDS_EPSILON``) has no majority: the
    segment carries no ``true_label``, is MIXED and ``tied``, and is scored
    by nobody — ground truth is never decided by a spelling. The 80 %
    boundary is met to within ``_SHARE_EPSILON``."""
    truths: list[SegmentTruth] = []
    for segment in segments:
        overlap: dict[str, list[float]] = {}
        for span in track.spans:
            seconds = min(segment.end_seconds, span.end_seconds) - max(
                segment.start_seconds, span.start_seconds
            )
            if seconds > 0:
                overlap.setdefault(span.label, []).append(seconds)
        if not overlap:
            truths.append(
                SegmentTruth(segment.start_seconds, segment.end_seconds, None, 0.0, False)
            )
            continue
        totals = {label: _total(parts) for label, parts in overlap.items()}
        ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
        (label, seconds), *rest = ranked
        share = seconds / _total(totals.values())
        tied = bool(rest) and seconds - rest[0][1] <= _SECONDS_EPSILON
        truths.append(
            SegmentTruth(
                segment.start_seconds,
                segment.end_seconds,
                None if tied else label,
                share,
                tied or share < MIXED_MAJORITY_SHARE - _SHARE_EPSILON,
                tied=tied,
            )
        )
    return tuple(truths)


# ---------------------------------------------------------------------------
# Metrics (label-set agnostic: nothing here assumes two clusters).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClusterMetrics:
    """Cluster accuracy over the LABELLED segments of one condition.

    ``mapping`` is the best injective predicted->true assignment by
    duration; both accuracies are scored under that one mapping (the
    unweighted count is reported for the same mapping, not re-optimised).
    A predicted cluster left out of the mapping — more clusters than true
    speakers — scores every segment wrong. ``predicted_speaker_count`` is
    taken over ALL segments; ``true_speaker_count`` over the labelled ones.
    """

    predicted_labels: tuple[str, ...]
    true_labels: tuple[str, ...]
    mapping: tuple[tuple[str, str], ...]
    accuracy_seconds: float
    accuracy_count: float
    correct_count: int
    labelled_count: int
    labelled_seconds: float
    confusion_seconds: tuple[tuple[str, str, float], ...]
    purity: tuple[tuple[str, float], ...]
    predicted_speaker_count: int
    true_speaker_count: int

    def seconds(self, predicted: str, true: str) -> float:
        """Confusion-matrix cell: labelled seconds predicted as ``predicted``
        whose ground truth is ``true``."""
        return next(
            (s for p, t, s in self.confusion_seconds if p == predicted and t == true), 0.0
        )


def cluster_metrics(predicted: Sequence[str], truths: Sequence[SegmentTruth]) -> ClusterMetrics:
    """Score one condition's labels against the aligned ground truth.
    Requires at least one labelled segment (``ValueError`` otherwise)."""
    if len(predicted) != len(truths):
        raise ValueError("one predicted label per segment")
    # Every float below is a ``_total`` over a collected multiset of
    # per-segment durations, so no reported number depends on the order
    # segments, labels or permutations are visited in (round 65 PR-LOW-009).
    durations: dict[tuple[str, str], list[float]] = {}
    counts: dict[tuple[str, str], int] = {}
    for label, truth in zip(predicted, truths, strict=True):
        if truth.true_label is None:
            continue
        key = (label, truth.true_label)
        durations.setdefault(key, []).append(truth.duration_seconds)
        counts[key] = counts.get(key, 0) + 1
    if not durations:
        raise ValueError("no labelled segments to score")
    confusion = {key: _total(parts) for key, parts in durations.items()}

    predicted_labels = sorted({p for p, _ in confusion})
    true_labels = sorted({t for _, t in confusion})
    labelled_seconds = _total(confusion.values())
    labelled_count = sum(counts.values())

    # Best injective mapping by duration; ``None`` pads the target list when
    # there are more predicted clusters than true speakers (those clusters
    # map to nothing). Small label sets make the enumeration trivial.
    targets: list[str | None] = [*true_labels]
    targets += [None] * max(0, len(predicted_labels) - len(true_labels))
    # Objective, computed over the SET of candidate mappings so that no
    # reported number depends on the order permutations are visited in
    # (round 64 PR-MED-007 - a moving epsilon anchor is not transitive):
    #   S*   = the maximum seconds over all candidates
    #   band = every candidate within ``_SECONDS_EPSILON`` of that FIXED S*
    #   K*   = the maximum segment count within the band
    #   s*   = the maximum exact seconds among the count winners
    # Each step is a function of the set, never of its traversal. Finalists
    # with identical s* and K* differ only in their label pairing, which is
    # presentation: the smallest pairs tuple is shown - a lexical choice
    # that touches no number.
    candidates: list[tuple[float, int, tuple[tuple[str, str], ...]]] = []
    for assignment in itertools.permutations(targets, len(predicted_labels)):
        pairs = tuple(
            (p, t) for p, t in zip(predicted_labels, assignment, strict=True) if t is not None
        )
        seconds = _total(confusion.get(pair, 0.0) for pair in pairs)
        count = sum(counts.get(pair, 0) for pair in pairs)
        candidates.append((seconds, count, pairs))
    top_seconds = max(seconds for seconds, _, _ in candidates)
    band = [c for c in candidates if c[0] >= top_seconds - _SECONDS_EPSILON]
    top_count = max(count for _, count, _ in band)
    finalists = [c for c in band if c[1] == top_count]
    top_exact = max(seconds for seconds, _, _ in finalists)
    best_seconds, best_count, best_mapping = min(
        (c for c in finalists if c[0] == top_exact), key=lambda c: c[2]
    )
    correct_count = best_count

    purity: list[tuple[str, float]] = []
    for p in predicted_labels:
        row = [confusion.get((p, t), 0.0) for t in true_labels]
        purity.append((p, max(row) / _total(row)))

    return ClusterMetrics(
        predicted_labels=tuple(predicted_labels),
        true_labels=tuple(true_labels),
        mapping=best_mapping,
        accuracy_seconds=best_seconds / labelled_seconds,
        accuracy_count=correct_count / labelled_count,
        correct_count=correct_count,
        labelled_count=labelled_count,
        labelled_seconds=labelled_seconds,
        confusion_seconds=tuple((p, t, s) for (p, t), s in sorted(confusion.items())),
        purity=tuple(purity),
        predicted_speaker_count=len(set(predicted)),
        true_speaker_count=len(true_labels),
    )


@dataclass(frozen=True)
class RoleOutcome:
    """The role verdict for one condition (plan Design Decision: judged
    against the preselected cluster's majority true speaker, never through
    a cluster-to-speaker mapping, so it is defined for any speaker count).

    CORRECT when the preselected cluster's duration-weighted majority true
    label is ``clinician``; WRONG otherwise — including a preselected
    cluster with no labelled segment at all, or whose top two true labels
    TIE (within ``_SECONDS_EPSILON``: no majority exists and a spelling may
    not break it), in both of which ``majority_true_label`` reads None so
    the reader can see that the labels, not the preselection, decided;
    NONE when there was no preselection.
    ``clinician_cluster_talk_time_share`` is ``SpeakerEvidence.talk_time_share``
    of the cluster whose majority IS the clinician — the one holding the most
    clinician seconds when several do, and None when the top two hold him
    equally (within ``_SECONDS_EPSILON``): an ambiguity is exposed, never
    settled by a cluster's name; ``clinician_labelled_share`` is the
    clinician's share of all labelled seconds — Task 2.2's talk-time
    DIRECTION assumption, measured directly.

    For the enrolled condition's AUTO-CONFIRM outcome (``auto_confirm_outcome``)
    the same verdict is judged for the cluster the voice profile confirmed
    (``TranscriptDocument.enrolled_speaker``), and ``margin`` carries that
    document's ``enrolment_similarity`` — the number the practitioner sees
    on the confirmation line — rather than a heuristic score gap; the
    report labels the column accordingly.
    """

    verdict: RoleVerdict
    preselected_speaker: str | None
    majority_true_label: str | None
    margin: float
    clinician_cluster_talk_time_share: float | None
    clinician_labelled_share: float | None


def role_outcome(
    preselection: SpeakerRolePreselection,
    predicted: Sequence[str],
    truths: Sequence[SegmentTruth],
) -> RoleOutcome:
    if len(predicted) != len(truths):
        raise ValueError("one predicted label per segment")
    per_cluster: dict[str, dict[str, float]] = {}
    clinician_seconds = 0.0
    labelled_seconds = 0.0
    for label, truth in zip(predicted, truths, strict=True):
        if truth.true_label is None:
            continue
        labelled_seconds += truth.duration_seconds
        if truth.true_label == CLINICIAN_LABEL:
            clinician_seconds += truth.duration_seconds
        bucket = per_cluster.setdefault(label, {})
        bucket[truth.true_label] = bucket.get(truth.true_label, 0.0) + truth.duration_seconds

    def majority(cluster: str) -> str | None:
        ranked = sorted(
            per_cluster.get(cluster, {}).items(), key=lambda item: item[1], reverse=True
        )
        if not ranked:
            return None
        if len(ranked) > 1 and ranked[0][1] - ranked[1][1] <= _SECONDS_EPSILON:
            return None  # a tie is not a majority, and no spelling may break it
        return ranked[0][0]

    clinician_clusters = sorted(
        (c for c in per_cluster if majority(c) == CLINICIAN_LABEL),
        key=lambda c: per_cluster[c][CLINICIAN_LABEL],
        reverse=True,
    )
    clinician_cluster: str | None = clinician_clusters[0] if clinician_clusters else None
    if len(clinician_clusters) > 1:
        lead = (
            per_cluster[clinician_clusters[0]][CLINICIAN_LABEL]
            - per_cluster[clinician_clusters[1]][CLINICIAN_LABEL]
        )
        if lead <= _SECONDS_EPSILON:
            clinician_cluster = None  # two clusters hold the clinician equally: no name decides
    cluster_share = next(
        (
            evidence.talk_time_share
            for evidence in preselection.speaker_evidence
            if evidence.speaker == clinician_cluster
        ),
        None,
    )
    labelled_share = clinician_seconds / labelled_seconds if labelled_seconds > 0 else None

    chosen = preselection.preselected_clinician_speaker
    if chosen is None:
        return RoleOutcome("NONE", None, None, preselection.margin, cluster_share, labelled_share)
    majority_true = majority(chosen)
    verdict: RoleVerdict = "CORRECT" if majority_true == CLINICIAN_LABEL else "WRONG"
    return RoleOutcome(
        verdict, chosen, majority_true, preselection.margin, cluster_share, labelled_share
    )


def auto_confirm_outcome(
    document: TranscriptDocument,
    predicted: Sequence[str],
    truths: Sequence[SegmentTruth],
) -> RoleOutcome:
    """The enrolled condition's verdict for the cluster the voice profile
    confirmed (D4's pre-check, ``enrolled_speaker``): CORRECT when that
    cluster's duration-weighted majority true label is ``clinician``, WRONG
    otherwise, NONE when the document carries no attribution. Judged by the
    same rule as the heuristic outcome (``role_outcome``), with the
    document's ``enrolment_similarity`` in ``margin`` and the heuristic's
    evidence supplying the talk-time shares."""
    evidence = speaker_role(document).speaker_evidence
    similarity = document.enrolment_similarity
    if similarity is None:
        similarity = 0.0
    return role_outcome(
        SpeakerRolePreselection(document.enrolled_speaker, similarity, evidence),
        predicted,
        truths,
    )


# ---------------------------------------------------------------------------
# Per-recording results.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConditionResult:
    """One condition over one recording. ``metrics`` is None when the
    clustering MERGED (all ``speaker_1`` over two or more segments — reported,
    not scored) or when no segment is labelled; ``role`` is always present
    because ``speaker_role`` is defined on either (a merged clustering
    yields NONE, which is what the app would show). The ``ENROLLED``
    condition is never ``merged``: one cluster there is scored whatever
    produced it — every segment matching the profile (the false-positive
    case PR-MED-014 wants measured) or a degenerate clustering after no
    match; the labels alone do not say which, the ``auto_confirm`` verdict
    and ``enrolment_similarity`` (carried by this condition alone) do."""

    condition: str
    predicted_labels: tuple[str, ...]
    merged: bool
    metrics: ClusterMetrics | None
    role: RoleOutcome
    auto_confirm: RoleOutcome | None = None
    enrolment_similarity: float | None = None


@dataclass(frozen=True)
class RecordingResult:
    """Everything the report prints for one recording — counts, seconds,
    labels and verdicts only; no transcript content is held here.
    ``unlabelled_count`` is zero-overlap segments only; a tied segment
    (no majority) is counted under ``mixed_count`` and ``tied_count``."""

    name: str
    segment_count: int
    unlabelled_count: int
    mixed_count: int
    tied_count: int
    label_names: tuple[str, ...]
    point_labels_ignored: int
    conditions: tuple[ConditionResult, ...]

    def has_condition(self, name: str) -> bool:
        return any(c.condition == name for c in self.conditions)

    def condition(self, name: str) -> ConditionResult:
        """The ``BEFORE``, ``AFTER`` or (when measured) ``ENROLLED``
        condition of this recording; ``KeyError`` for an absent one."""
        for candidate in self.conditions:
            if candidate.condition == name:
                return candidate
        raise KeyError(name)


def _segments_and_labels(document: TranscriptDocument) -> tuple[list[SpeechSegment], list[str]]:
    """The document's VAD segments and its speaker labels, index-aligned -
    the ONE derivation both the scorer and the self-check build on."""
    segments = [
        SpeechSegment(start_seconds=s.start_seconds, end_seconds=s.end_seconds)
        for s in document.transcript_segments
    ]
    return segments, [s.speaker for s in document.transcript_segments]


def _relabelled(document: TranscriptDocument, labels: Sequence[str]) -> TranscriptDocument:
    """A copy of ``document`` carrying ``labels`` as its speaker labels (the
    "before" condition's input to ``speaker_role``)."""
    return document.model_copy(
        update={
            "transcript_segments": tuple(
                segment.model_copy(update={"speaker": label})
                for segment, label in zip(document.transcript_segments, labels, strict=True)
            )
        }
    )


def _score_condition(
    name: str,
    labels: Sequence[str],
    truths: Sequence[SegmentTruth],
    document: TranscriptDocument,
    *,
    enrolled: bool = False,
) -> ConditionResult:
    merged = not enrolled and len(labels) >= 2 and set(labels) == {SPEAKER_1}
    scorable = not merged and any(truth.true_label is not None for truth in truths)
    return ConditionResult(
        condition=name,
        predicted_labels=tuple(labels),
        merged=merged,
        metrics=cluster_metrics(labels, truths) if scorable else None,
        role=role_outcome(speaker_role(document), labels, truths),
        auto_confirm=auto_confirm_outcome(document, labels, truths) if enrolled else None,
        enrolment_similarity=document.enrolment_similarity if enrolled else None,
    )


def score_document(
    name: str,
    document: TranscriptDocument,
    track: LabelTrack,
    before_labels: Sequence[str],
    *,
    enrolled_document: TranscriptDocument | None = None,
) -> RecordingResult:
    """Score a transcribed document against its label track. ``document``
    carries the "after" labels (the pipeline's own); ``before_labels`` are
    the re-clustered ones; ``enrolled_document``, when given, is the shipped
    pipeline's output WITH the embedder and profile over the same segments
    (one label per segment of ``document``, ``ValueError`` otherwise) and
    yields the third condition. Pure and ML-free — the CI-testable half of
    ``evaluate_recording``."""
    segments, after_labels = _segments_and_labels(document)
    if len(before_labels) != len(segments):
        raise ValueError("one before-condition label per segment")
    truths = align_segments(segments, track)
    before_document = _relabelled(document, before_labels)
    conditions = [
        _score_condition(BEFORE, before_labels, truths, before_document),
        _score_condition(AFTER, after_labels, truths, document),
    ]
    if enrolled_document is not None:
        _enrolled_segments, enrolled_labels = _segments_and_labels(enrolled_document)
        if len(enrolled_labels) != len(segments):
            raise ValueError("one enrolled-condition label per segment")
        conditions.append(
            _score_condition(ENROLLED, enrolled_labels, truths, enrolled_document, enrolled=True)
        )
    return RecordingResult(
        name=name,
        segment_count=len(segments),
        unlabelled_count=sum(1 for t in truths if t.true_label is None and not t.tied),
        mixed_count=sum(1 for truth in truths if truth.mixed),
        tied_count=sum(1 for truth in truths if truth.tied),
        label_names=track.labels,
        point_labels_ignored=track.point_labels_ignored,
        conditions=tuple(conditions),
    )


# ---------------------------------------------------------------------------
# The enrolled condition's inputs: an in-memory profile, never a store.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnrolmentInputs:
    """What the enrolled condition passes to the shipped pipeline: the
    embedder and a synthetic profile built by ``enrolment_inputs``. The
    profile lives in this process only — the harness imports no profile
    store and never writes one (the teardown contract covers the temporary
    session store alone, because nothing else is ever created). Neither
    field takes part in ``repr``: the profile's rendering carries the
    enrolment vector, and this module's result types stay renderable
    without it (the text-free contract in the module docstring)."""

    embedder: SpeakerEmbedder = field(repr=False)
    profile: PractitionerProfile = field(repr=False)


def enrolment_inputs(
    pcm: bytes, embedder: SpeakerEmbedder, frame_probability: FrameProbabilityFn
) -> EnrolmentInputs:
    """The shipped ``enrolment.enrol`` over ``pcm`` (an enrolment WAV, or the
    leave-one-out pool of clinician spans), wrapped in an in-memory
    ``PractitionerProfile`` recording the embedder's identity, so the
    pipeline applies it exactly as it would the practitioner's stored
    profile. Raises ``EnrolmentError`` (numbers only) when the audio holds
    no usable speech."""
    vector, speech_seconds = enrol(pcm, embedder, frame_probability=frame_probability)
    now = datetime.now(UTC)
    embedding = tuple(float(value) for value in vector)
    profile = PractitionerProfile(
        model_id=embedder.model_id,
        model_sha256=embedder.model_sha256,
        embedding=embedding,
        embedding_dim=len(embedding),
        created_at=now,
        enrolment_speech_seconds=speech_seconds,
        device_name=HARNESS_DEVICE_NAME,
        consent=ConsentRecord(
            accepted_at=now, consent_text_version=HARNESS_CONSENT_VERSION, learning_opt_in=False
        ),
    )
    return EnrolmentInputs(embedder=embedder, profile=profile)


def clinician_pcm(pcm: bytes, track: LabelTrack) -> bytes:
    """The PCM under every ``clinician``-labelled span of one recording,
    concatenated in track order and clipped to the audio — the leave-one-out
    fallback's raw material. Overlapping clinician spans repeat their
    overlap; that only weights the enrolment mean, never the measured
    recording, which is always left out of its own pool."""
    parts: list[bytes] = []
    for span in track.spans:
        if span.label != CLINICIAN_LABEL:
            continue
        start = int(span.start_seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE
        end = min(int(span.end_seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE, len(pcm))
        if end > start:
            parts.append(pcm[start:end])
    return b"".join(parts)


# ---------------------------------------------------------------------------
# The measurement path: a temporary encrypted store through the real pipeline.
# ---------------------------------------------------------------------------


def _write_store(session_dir: Path, crypto: SessionCrypto, session_id: str, pcm: bytes) -> None:
    store = SessionChunkStore.create(session_dir / AUDIO_FILENAME, crypto, session_id)
    try:
        for offset in range(0, len(pcm), STORE_CHUNK_BYTES):
            store.append_chunk(pcm[offset : offset + STORE_CHUNK_BYTES])
        store.finish()
    finally:
        store.close()


def _attempt_all(legs: Sequence[tuple[str, Callable[[], object]]], failures: list[str]) -> None:
    """Run every leg. A later leg runs whatever an earlier one raised (each
    is reached through a ``finally``); a leg's ``Exception`` is recorded by
    type name in ``failures`` instead of propagating; only a
    ``BaseException`` (an interrupt) propagates — and only after the
    remaining legs have still run."""
    if not legs:
        return
    (name, leg), rest = legs[0], legs[1:]
    try:
        try:
            leg()
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}")
    finally:
        _attempt_all(rest, failures)


def _remove_tree(path: Path) -> None:
    """Remove ``path`` recursively under ``shutil.rmtree``'s normal raising
    contract — no ``ignore_errors`` — so every failure the OS reports
    propagates to ``_attempt_all`` and is surfaced. ``FileNotFoundError``,
    and only that, is treated as "nothing there": the same positive signal
    the probe trusts, and what a never-created ``session_dir`` yields (the
    path is assigned before ``mkdir``). A removal that fails stops at its
    first error and leaves the rest to the later legs and the probe."""
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        pass


def _probe(path: Path, *, stat: Callable[[Path], object] = os.stat) -> str:
    """Fail-closed existence probe: ``"gone"`` only on a positive
    ``FileNotFoundError``, ``"present"`` when ``stat`` succeeds, and
    ``"unreadable"`` for any other ``OSError`` — the OS refused to say, and
    that is never read as absent."""
    try:
        stat(path)
    except FileNotFoundError:
        return "gone"
    except OSError:
        return "unreadable"
    return "present"


def _raise_if_residue(
    temp_root: Path | None, session_dir: Path | None, crypto: SessionCrypto, failures: list[str]
) -> None:
    """Return only when the temporary root is positively gone AND the
    in-memory key is destroyed AND no leg failed; otherwise raise a
    ``SpeakerEvalError`` naming the temporary root (or stating that none
    was created), the key-blob state and every leg failure — even when a
    later leg recovered the state, so an OS anomaly on the custody path is
    never hidden. A recovered state says so, so nobody is sent to delete
    a directory that is gone."""
    root_state = "gone" if temp_root is None else _probe(temp_root)
    if root_state == "gone" and crypto.destroyed and not failures:
        return
    parts: list[str] = []
    if root_state == "gone":
        parts.append(
            "no temporary root was created"
            if temp_root is None
            else f"temporary store removed ({temp_root}) but a teardown leg failed - "
            "nothing to remove by hand; rerun this recording"
        )
    else:
        key_state = "gone" if session_dir is None else _probe(session_dir / KEY_FILENAME)
        if key_state == "present":
            store = (
                "its key blob is STILL PRESENT, so the store is recoverable by this Windows user"
            )
        elif key_state == "unreadable":
            store = (
                "its key blob could not be inspected (the OS refused), so treat the store "
                "as recoverable"
            )
        else:
            store = "its key was destroyed; what remains is ciphertext"
        verb = (
            "not fully removed"
            if root_state == "present"
            else "could not be confirmed removed (the OS refused to inspect it)"
        )
        parts.append(
            f"temporary store {verb}: {temp_root} - {store}; delete the directory by hand now"
        )
    if not crypto.destroyed:
        parts.append("the in-memory session key was NOT destroyed (it dies with this process)")
    if failures:
        parts.append("leg failures: " + "; ".join(failures))
    raise SpeakerEvalError("; ".join(parts))


def _destroy_temporary_store(
    temp_root: Path | None, session_dir: Path | None, crypto: SessionCrypto
) -> None:
    """Tear the temporary store down key-first. Every leg is attempted
    whatever the earlier legs did — unlink ``key.dpapi``, destroy the
    in-memory key, remove the session directory, remove the temporary root,
    each reached through a ``finally`` — and destruction of the in-memory
    key is attempted on every exit, a failed attempt being surfaced (the
    key then dies with the process). Every leg failure the OS reports is
    surfaced, even when a later leg recovered the state; a path that is
    already gone is not a failure; a removal that fails stops at its first
    error and leaves the rest to the later legs and the probe. The final
    probe fails closed: only a positive ``FileNotFoundError`` counts as
    gone. Teardown returns normally only when the root is positively gone,
    the key is destroyed and no leg failed; otherwise it raises a
    ``SpeakerEvalError`` naming the temporary root (or stating that none
    was created), the key state and every leg failure, chained to whatever
    exception was already in flight; an interrupt inside a leg propagates
    only after the remaining legs ran, chained to any residue fault. What
    this cannot do is delete or inspect what the OS refuses: that residue
    is named for the practitioner to remove by hand, never hidden. A root
    that never came to exist is passed as None and its legs are skipped."""
    failures: list[str] = []
    legs: list[tuple[str, Callable[[], object]]] = []
    if session_dir is not None:
        legs.append(("key unlink", functools.partial(delete_session_key, session_dir)))
    legs.append(("in-memory key destruction", crypto.destroy))
    if session_dir is not None:
        legs.append(("session directory removal", functools.partial(_remove_tree, session_dir)))
    if temp_root is not None:
        legs.append(("temporary root removal", functools.partial(_remove_tree, temp_root)))
    try:
        _attempt_all(legs, failures)
    finally:
        _raise_if_residue(temp_root, session_dir, crypto, failures)


class _ReplayProvider:
    """The real provider for the plain pass, a memory for the enrolled pass:
    every window the inner provider transcribes is remembered by the SHA-256
    of its PCM, and a window seen again is answered from that memory, so the
    enrolled pass over the same store costs no second Whisper run (VAD and
    window packing are deterministic over one store). An unseen window still
    goes to the inner provider — a difference in segmentation is then caught
    as a harness fault by ``evaluate_recording``. What it holds, for one
    recording at a time and never beyond the process: the transcribed words
    per window — the same plaintext the practitioner's WAV already is on
    disk (module docstring: not the app's plaintext bound)."""

    def __init__(self, inner: SpeechProvider) -> None:
        self._inner = inner
        self._seen: dict[bytes, list[TranscribedWord]] = {}

    @property
    def model_name(self) -> str:
        return str(getattr(self._inner, "model_name", type(self._inner).__name__))

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        key = hashlib.sha256(pcm).digest()
        words = self._seen.get(key)
        if words is None:
            words = list(self._inner.transcribe_segment(pcm, sample_rate))
            self._seen[key] = words
        return list(words)


def _transcribe_in_temporary_store(
    pcm: bytes,
    provider: SpeechProvider,
    frame_probability: FrameProbabilityFn,
    *,
    enrolment: EnrolmentInputs | None = None,
) -> tuple[TranscriptDocument, TranscriptDocument | None]:
    """``pcm`` -> fresh store under a real DPAPI-wrapped key -> the shipped
    ``transcribe_session`` (twice when ``enrolment`` is given: the plain
    pass, then the same store with the embedder and profile through a
    ``_ReplayProvider``) -> ``_destroy_temporary_store`` on every path.
    Returns ``(plain document, enrolled document or None)``.
    The guard begins the moment the in-memory key exists: a failure
    anywhere after it — ``mkdtemp`` included — still reaches the teardown,
    with a root that never came to exist passed as None and a session
    directory that never came to exist (it is assigned before ``mkdir``)
    handled by ``_remove_tree``'s "nothing there" rule. On the failure
    path a residue fault (module-own text naming the path) supersedes the
    original exception, which stays attached as its ``__context__``; with
    no residue the original propagates unchanged."""
    crypto = SessionCrypto()
    temp_root: Path | None = None
    session_dir: Path | None = None
    enrolled_document: TranscriptDocument | None = None
    try:
        temp_root = Path(tempfile.mkdtemp(prefix=TEMP_DIR_PREFIX))
        session_id = secrets.token_hex(16)
        session_dir = temp_root / session_id
        session_dir.mkdir()
        wrap_key_to_file(crypto, session_dir)
        _write_store(session_dir, crypto, session_id, pcm)
        try:
            if enrolment is None:
                document = transcribe_session(session_dir, crypto, provider, frame_probability)
            else:
                replay = _ReplayProvider(provider)
                document = transcribe_session(session_dir, crypto, replay, frame_probability)
                enrolled_document = transcribe_session(
                    session_dir,
                    crypto,
                    replay,
                    frame_probability,
                    speaker_embedder=enrolment.embedder,
                    enrolled_profile=enrolment.profile,
                )
        except BaseException as exc:
            # The pipeline streams ``audio.enc`` through suspended generators
            # (``iter_chunks`` -> ``extract_segment_pcm``). An exception's
            # traceback keeps their frames — and the open file handle —
            # alive until the exception is handled, which on Windows would
            # defeat the directory removal below. Clearing the traceback's
            # frame locals finalises the generators (closing the handle)
            # while keeping the stack lines for the report.
            if exc.__traceback__ is not None:
                traceback.clear_frames(exc.__traceback__)
            raise
    except BaseException:
        _destroy_temporary_store(temp_root, session_dir, crypto)
        raise
    _destroy_temporary_store(temp_root, session_dir, crypto)
    return document, enrolled_document


def evaluate_recording(
    wav_path: Path,
    labels_path: Path,
    provider: SpeechProvider,
    frame_probability: FrameProbabilityFn,
    *,
    enrolment: EnrolmentInputs | None = None,
) -> RecordingResult:
    """Measure one recording: both legacy conditions, plus the enrolled one
    when ``enrolment`` is given. Inputs are validated BEFORE any store is
    built. Raises ``LabelTrackError`` / ``WavFormatError`` for unusable
    inputs and ``HarnessFaultError`` when ``label_speakers`` with the default
    does not reproduce the pipeline's labels over the same segments (both
    sites must mirror one policy, round 42 LOW-011) or when the enrolled
    pass segmented the store differently from the plain pass."""
    track = parse_audacity_labels(labels_path.read_text(encoding="utf-8-sig"))
    pcm = read_wav_pcm(wav_path)
    document, enrolled_document = _transcribe_in_temporary_store(
        pcm, provider, frame_probability, enrolment=enrolment
    )

    segments, after_labels = _segments_and_labels(document)
    # The same floor arithmetic the pipeline slices its windows with
    # (``TestWindowPcmSliceIdentity`` pins the identity), so both conditions
    # embed byte-identical segment PCM.
    segment_pcms = list(extract_segment_pcm([pcm], segments))
    if label_speakers(segment_pcms) != after_labels:
        raise HarnessFaultError(
            "label_speakers() over the pipeline's own segments did not reproduce the "
            "pipeline's labels - the two sites must mirror one policy (round 42 LOW-011); "
            "fix the drift before measuring"
        )
    if enrolled_document is not None:
        enrolled_segments, _labels = _segments_and_labels(enrolled_document)
        if enrolled_segments != segments:
            raise HarnessFaultError(
                "the enrolled pass segmented the same store differently from the plain "
                "pass - VAD segmentation must be deterministic over one store; fix the "
                "drift before measuring"
            )
    before_labels = label_speakers(segment_pcms, cepstral_mean_normalisation=False)
    return score_document(
        wav_path.stem, document, track, before_labels, enrolled_document=enrolled_document
    )


# ---------------------------------------------------------------------------
# Report.
# ---------------------------------------------------------------------------


def _share(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


def render_report(results: Sequence[RecordingResult], *, model_name: str) -> str:
    """The Markdown table (per recording and condition, confusion matrices,
    aggregate per condition), headed by the whisper model name. Everything
    printed comes from ``RecordingResult`` fields — no transcript text.
    Its literals are ASCII; its dynamic fields (recording stems, role
    labels, the model name) are whatever Unicode the inputs carried, and
    stream safety belongs to ``main``'s ``_configure_output``, not to this
    string (see the note on ``WAV_FORMAT_HELP``)."""
    lines = [
        f"## Speaker measurement (Task 2.3) - whisper model `{model_name}`",
        "",
        f"Recordings scored: {len(results)}. Conditions: `{BEFORE}` = Task 2.1 cepstral mean "
        f"normalisation OFF over the same VAD segments; `{AFTER}` = the shipped pipeline; "
        f"`{ENROLLED}` (when measured) = the shipped pipeline with the speaker embedder and "
        "an enrolment vector applied (practitioner-profile plan), where a one-cluster "
        "output is scored rather than reported as merged (every segment matched, or a "
        "degenerate clustering after none did - the labels alone do not say which). "
        "Cluster accuracy is the best injective predicted->true mapping, duration-weighted "
        "(s) and by segment count (n), over labelled segments only. `Auto-confirm` is the "
        "verdict for the cluster the voice profile confirmed (what the Transcript screen "
        "pre-checks) and `Similarity` its mean cosine against the enrolment vector.",
        "",
        "| Recording | Segments | Unlabelled | Mixed | Labels | Condition | Clusters pred/true "
        "| Cluster acc. (s) | Cluster acc. (n) | Role | Preselected | Majority true | Margin "
        "| Clinician cluster talk share | Clinician labelled share | Auto-confirm "
        "| Auto-confirmed | Similarity |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for result in results:
        for cond in result.conditions:
            metrics = cond.metrics
            if cond.merged:
                clusters, acc_s, acc_n = "merged", "-", "-"
            elif metrics is None:
                clusters, acc_s, acc_n = "unscored (no labelled segments)", "-", "-"
            else:
                clusters = f"{metrics.predicted_speaker_count}/{metrics.true_speaker_count}"
                acc_s = f"{metrics.accuracy_seconds:.3f}"
                acc_n = (
                    f"{metrics.accuracy_count:.3f} "
                    f"({metrics.correct_count}/{metrics.labelled_count})"
                )
            role = cond.role
            auto = cond.auto_confirm
            auto_verdict = auto.verdict if auto is not None else "-"
            auto_speaker = (auto.preselected_speaker or "-") if auto is not None else "-"
            lines.append(
                f"| {result.name} | {result.segment_count} | {result.unlabelled_count} "
                f"| {result.mixed_count} | {', '.join(result.label_names)} | {cond.condition} "
                f"| {clusters} | {acc_s} | {acc_n} | {role.verdict} "
                f"| {role.preselected_speaker or '-'} | {role.majority_true_label or '-'} "
                f"| {role.margin:.3f} | {_share(role.clinician_cluster_talk_time_share)} "
                f"| {_share(role.clinician_labelled_share)} | {auto_verdict} | {auto_speaker} "
                f"| {_share(cond.enrolment_similarity)} |"
            )

    notes: list[str] = []
    for result in results:
        if result.point_labels_ignored:
            notes.append(f"- {result.name}: {result.point_labels_ignored} point label(s) ignored")
        if result.tied_count:
            notes.append(
                f"- {result.name}: {result.tied_count} tied segment(s) - no majority, "
                "counted as mixed, scored by nobody"
            )
    if notes:
        lines += ["", "Notes:", *notes]

    for result in results:
        for cond in result.conditions:
            metrics = cond.metrics
            if metrics is None:
                continue
            lines += [
                "",
                f"### {result.name} - {cond.condition}: confusion in seconds (predicted x true)",
                "",
                "| predicted \\ true | " + " | ".join(metrics.true_labels) + " | purity |",
                "|---|" + "---|" * (len(metrics.true_labels) + 1),
            ]
            purity = dict(metrics.purity)
            for p in metrics.predicted_labels:
                cells = " | ".join(f"{metrics.seconds(p, t):.1f}" for t in metrics.true_labels)
                lines.append(f"| {p} | {cells} | {purity[p]:.3f} |")
            lines.append(
                "Mapping: " + ", ".join(f"{p} -> {t}" for p, t in metrics.mapping)
            )

    lines += [
        "",
        "### Aggregate per condition",
        "",
        "| Condition | Recordings | Scored | Merged | Mean cluster acc. (s) "
        "| Mean cluster acc. (n) | Role CORRECT | Role WRONG | Role NONE "
        "| Auto-confirm CORRECT | Auto-confirm WRONG | Auto-confirm NONE |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name in (BEFORE, AFTER, ENROLLED):
        conds = [result.condition(name) for result in results if result.has_condition(name)]
        if name == ENROLLED and not conds:
            continue  # not measured on this run: no row rather than a row of zeros
        scored = [c.metrics for c in conds if c.metrics is not None]
        verdicts = Counter(c.role.verdict for c in conds)
        auto_counts = Counter(
            c.auto_confirm.verdict for c in conds if c.auto_confirm is not None
        )
        mean_s = f"{fmean([m.accuracy_seconds for m in scored]):.3f}" if scored else "-"
        mean_n = f"{fmean([m.accuracy_count for m in scored]):.3f}" if scored else "-"
        auto_cells = (
            f"{auto_counts['CORRECT']} | {auto_counts['WRONG']} | {auto_counts['NONE']}"
            if name == ENROLLED
            else "- | - | -"
        )
        lines.append(
            f"| {name} | {len(conds)} | {len(scored)} | {sum(1 for c in conds if c.merged)} "
            f"| {mean_s} | {mean_n} | {verdicts['CORRECT']} | {verdicts['WRONG']} "
            f"| {verdicts['NONE']} | {auto_cells} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI (the ``benchmark.main`` shape). Run by the PRACTITIONER from a normal
# terminal: agent shells cannot see the user's model cache (docs/lessons.md).
# ---------------------------------------------------------------------------


def find_recording_pairs(directory: Path) -> tuple[list[tuple[Path, Path]], list[Path]]:
    """``(pairs, unpaired)``: ``<name>.wav`` + ``<name>.txt`` pairs in name
    order, and every lone WAV or label file (reported and skipped)."""
    wavs: dict[str, Path] = {}
    labels: dict[str, Path] = {}
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".wav":
            wavs[path.stem] = path
        elif path.suffix.lower() == ".txt":
            labels[path.stem] = path
    pairs = [(wavs[stem], labels[stem]) for stem in sorted(wavs) if stem in labels]
    unpaired = [wavs[stem] for stem in sorted(wavs) if stem not in labels]
    unpaired += [labels[stem] for stem in sorted(labels) if stem not in wavs]
    return pairs, unpaired


def _configure_output() -> None:
    """Reconfigure stdout and stderr to UTF-8 with ``backslashreplace`` so
    no dynamic field (a Unicode file stem, role label or model name) can
    abort a run with ``UnicodeEncodeError`` on a redirected, code-page-
    encoded stream; a redirected table is then a UTF-8 Markdown file. A
    stream without ``reconfigure`` (a replaced ``StringIO``) is left as it
    is — this helper can only configure a ``TextIOWrapper``."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")


def _leave_one_out_pool(
    pairs: Sequence[tuple[Path, Path]],
) -> tuple[dict[str, bytes], dict[str, str]]:
    """``(pool, failures)``: recording stem -> its clinician-labelled PCM for
    every pair that prepares, and WAV name -> exception type name for every
    pair whose clinician-span extraction failed. Every input-dependent step
    of preparing one entry sits inside the per-pair boundary (peer rounds 19
    PR-REG-003 / 20 PR-REG-004: preparation must never abort the run before
    a recording is scored). Two failure classes, reported once each: a pair
    whose READ or PARSE fails is skipped silently here, because the
    per-recording evaluation re-reads the same inputs and reports that pair
    by type; a pair that reads but whose EXTRACTION fails (an accepted label
    timestamp too large for a sample index, ``OverflowError``) is returned in
    ``failures`` because the evaluation, which compares timestamps as floats,
    would never trip on it — ``main`` reports it by type and counts it
    towards the exit status."""
    pool: dict[str, bytes] = {}
    failures: dict[str, str] = {}
    for wav_path, labels_path in pairs:
        try:
            track = parse_audacity_labels(labels_path.read_text(encoding="utf-8-sig"))
            pcm = read_wav_pcm(wav_path)
        except Exception:  # noqa: BLE001 - the evaluation loop reports it, type only
            continue
        try:
            pool[wav_path.stem] = clinician_pcm(pcm, track)
        except Exception as exc:  # noqa: BLE001 - reported by main, type only
            failures[wav_path.name] = type(exc).__name__
    return pool, failures


def main(argv: list[str] | None = None) -> int:
    """Exit status 0 only when at least one recording was scored and none
    errored; a refused or unpaired file is reported, not an error. An
    unusable ``--enrolment`` WAV or an absent speaker model under
    ``--enrolment`` is an error (the practitioner asked for that condition);
    without the flag the leave-one-out fallback needs the speaker model and
    two or more pairs, and says so when it cannot run."""
    _configure_output()
    parser = argparse.ArgumentParser(
        description=(
            "Measure speaker-cluster and clinician-role accuracy on labelled recordings "
            "(Task 2.3), before and after Task 2.1, through the shipped pipeline - and, "
            "with an enrolment WAV (or two or more recordings), with the practitioner's "
            "voice profile applied."
        )
    )
    parser.add_argument(
        "recordings_dir",
        type=Path,
        help=(
            "directory of <name>.wav (16 kHz mono 16-bit PCM) + <name>.txt "
            "(Audacity label track; labels are role names, one must be 'clinician') pairs"
        ),
    )
    parser.add_argument(
        "--enrolment",
        type=Path,
        default=None,
        metavar="WAV",
        help=(
            f"a {WAV_FORMAT_HELP} of the practitioner reading aloud (about 30 s of speech); "
            f"adds the '{ENROLLED}' condition with that voice profile applied in memory. "
            "Without it, given two or more recordings, each recording is enrolled from the "
            "clinician-labelled spans of the OTHER recordings (leave-one-out)."
        ),
    )
    args = parser.parse_args(argv)

    apply_offline_env()
    assert_offline_env()
    directory: Path = args.recordings_dir
    if not directory.is_dir():
        parser.error(f"{directory} is not a directory")

    pairs, unpaired = find_recording_pairs(directory)
    for path in unpaired:
        wanted = ".txt label track" if path.suffix.lower() == ".wav" else ".wav recording"
        print(f"[skip] {path.name}: no matching {path.stem}{wanted}")
    if not pairs:
        print(f"no recording/label pairs found in {directory}")
        return 1

    model_name = resolve_whisper_model()
    vad = SileroVad()
    provider = WhisperSpeechProvider(model_name=model_name)
    enrolment_wav: Path | None = args.enrolment
    embedder: SpeakerEmbedder | None = None
    if enrolment_wav is not None or len(pairs) >= 2:
        try:
            embedder = build_speaker_embedder()
        except SpeakerModelError as exc:
            if enrolment_wav is not None:
                print(f"[error] --enrolment: {exc}")
                return 1
            print(f"[skip] {ENROLLED} condition: {exc}")
    fixed_enrolment: EnrolmentInputs | None = None
    pool: dict[str, bytes] = {}
    pool_failures: dict[str, str] = {}
    if embedder is not None and enrolment_wav is not None:
        try:
            fixed_enrolment = enrolment_inputs(
                read_wav_pcm(enrolment_wav), embedder, vad.frame_probability
            )
        except (WavFormatError, EnrolmentError, OSError) as exc:
            # WavFormatError / EnrolmentError text is this module's or numbers
            # only; an OSError names the path the practitioner typed.
            print(f"[error] --enrolment {enrolment_wav.name}: {exc}")
            return 1
    elif embedder is not None:
        pool, pool_failures = _leave_one_out_pool(pairs)
        print(
            f"[info] no --enrolment given: the {ENROLLED} condition enrols each recording "
            "from the clinician-labelled spans of the other recordings (leave-one-out)"
        )
    elif len(pairs) < 2:
        print(f"[skip] {ENROLLED} condition: give --enrolment <wav> or two or more recordings")
    results: list[RecordingResult] = []
    errors = 0
    for wav_name, failure in pool_failures.items():
        # PR-REG-004: an extraction-only failure is reported here, once, by
        # TYPE (the evaluation below cannot re-hit it), and counts towards
        # the exit status like any other per-recording failure.
        errors += 1
        print(f"[error] {wav_name}: {ENROLLED} pool preparation failed - {failure}")
    for wav_path, labels_path in pairs:
        enrolment = fixed_enrolment
        if embedder is not None and fixed_enrolment is None:
            others = b"".join(pcm for stem, pcm in pool.items() if stem != wav_path.stem)
            try:
                enrolment = enrolment_inputs(others, embedder, vad.frame_probability)
            except EnrolmentError as exc:
                print(f"[skip] {wav_path.name}: {ENROLLED} condition not measured - {exc}")
                enrolment = None
            except Exception as exc:  # noqa: BLE001 - isolated exactly like the evaluation
                # PR-REG-003: the same per-recording isolation as the
                # evaluation below — the recording is still measured on the
                # legacy conditions, the failure counts towards the exit
                # status, and only the exception TYPE is printed (its text is
                # unaudited for content, Critical Constraint).
                errors += 1
                failure = type(exc).__name__
                print(f"[error] {wav_path.name}: {ENROLLED} condition failed - {failure}")
                enrolment = None
        print(f"[run ] {wav_path.name}", flush=True)
        try:
            results.append(
                evaluate_recording(
                    wav_path, labels_path, provider, vad.frame_probability, enrolment=enrolment
                )
            )
        except RecordingRefusedError as exc:
            print(f"[skip] {wav_path.name}: {exc}")
        except HarnessFaultError as exc:
            errors += 1
            print(f"[harness-fault] {wav_path.name}: {exc}")
        except SpeakerEvalError as exc:
            errors += 1
            print(f"[error] {wav_path.name}: {exc}")
        except Exception as exc:
            # One failing recording (a model error on one file, a store
            # fault, an unreadable path) must not discard the recordings
            # already scored: report it, keep going, print the table, and
            # exit non-zero at the end. TYPE ONLY, never the message: the
            # three branches above echo text this module itself builds from
            # file names, label spellings, formats and paths; any other
            # exception's text is unaudited for transcript content and is
            # confined here rather than described (Critical Constraint).
            errors += 1
            print(f"[error] {wav_path.name}: {type(exc).__name__}")
    print()
    print(render_report(results, model_name=model_name))
    return 0 if results and not errors else 1


__all__ = [
    "AFTER",
    "BEFORE",
    "CLINICIAN_LABEL",
    "ENROLLED",
    "HARNESS_CONSENT_VERSION",
    "HARNESS_DEVICE_NAME",
    "MIXED_MAJORITY_SHARE",
    "TEMP_DIR_PREFIX",
    "WAV_FORMAT_HELP",
    "ClusterMetrics",
    "ConditionResult",
    "EnrolmentInputs",
    "HarnessFaultError",
    "LabelSpan",
    "LabelTrack",
    "LabelTrackError",
    "RecordingRefusedError",
    "RecordingResult",
    "RoleOutcome",
    "SegmentTruth",
    "SpeakerEvalError",
    "WavFormatError",
    "align_segments",
    "auto_confirm_outcome",
    "clinician_pcm",
    "cluster_metrics",
    "enrolment_inputs",
    "evaluate_recording",
    "find_recording_pairs",
    "main",
    "parse_audacity_labels",
    "read_wav_pcm",
    "render_report",
    "role_outcome",
    "score_document",
]


if __name__ == "__main__":
    sys.exit(main())
