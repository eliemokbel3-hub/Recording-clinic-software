"""Tests for the Task 2.3 speaker-measurement harness (`scribe_desktop.speaker_eval`).

Layers (plan Task 2.3a):
- pure, ML-free: label-track parsing, WAV refusal, alignment, the metrics
  (including the three-true/two-predicted merge), role verdicts, the
  text-free report, the CLI's file pairing and its offline-env-first order
- numpy-gated: the ``cepstral_mean_normalisation`` toggle reproduces the
  pre-Task-2.1 embedding and SPLITS the gain-shifted pair the shipped
  default keeps together
- Windows + numpy: ``evaluate_recording`` end to end through the real
  DPAPI-wrapped temporary store with the mock provider and an amplitude
  VAD, asserting the after-condition labels equal the pipeline's own and
  that the temporary store is gone afterwards - including when the
  provider raises

No clinical audio anywhere: fixtures are tones, harmonic combs and silence.
"""

from __future__ import annotations

import io
import math
import os
import shutil
import struct
import sys
import tempfile
import wave
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scribe_desktop import speaker_eval
from scribe_desktop.benchmark import OFFLINE_ENV, apply_offline_env, assert_offline_env
from scribe_desktop.note import SpeakerEvidence, SpeakerRolePreselection
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import KEY_FILENAME, SessionChunkStore
from scribe_desktop.speaker_embedding import SpeakerModelError
from scribe_desktop.speaker_eval import (
    AFTER,
    BEFORE,
    ENROLLED,
    TEMP_DIR_PREFIX,
    HarnessFaultError,
    LabelSpan,
    LabelTrack,
    LabelTrackError,
    RecordingResult,
    SegmentTruth,
    SpeakerEvalError,
    WavFormatError,
    _destroy_temporary_store,
    _probe,
    align_segments,
    cluster_metrics,
    evaluate_recording,
    find_recording_pairs,
    main,
    parse_audacity_labels,
    read_wav_pcm,
    render_report,
    role_outcome,
    score_document,
)
from scribe_desktop.speech import (
    BYTES_PER_SAMPLE,
    FRAME_BYTES,
    SAMPLE_RATE,
    MockSpeechProvider,
    SpeechSegment,
    TranscribedWord,
)
from scribe_desktop.transcription import (
    SPEAKER_1,
    SPEAKER_2,
    SPEAKER_3,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
    _segment_embedding,
    extract_segment_pcm,
    label_speakers,
    transcribe_session,
)

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-only")


@pytest.fixture(autouse=True)
def _offline_env() -> None:
    """Offline kill-switches active for every test: the clustering path's
    numpy import asserts them, exactly as the pipeline does."""
    apply_offline_env()


# ---------------------------------------------------------------------------
# synthetic PCM helpers (mirrors test_transcription.py)
# ---------------------------------------------------------------------------


def tone_pcm(seconds: float, frequency: float = 440.0, amplitude: float = 0.5) -> bytes:
    count = int(seconds * SAMPLE_RATE)
    scale = amplitude * 32767
    return struct.pack(
        f"<{count}h",
        *(int(scale * math.sin(2 * math.pi * frequency * i / SAMPLE_RATE)) for i in range(count)),
    )


def silence_pcm(seconds: float) -> bytes:
    return b"\0" * (int(seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE)


def comb_pcm(
    seconds: float,
    *,
    amplitude: float = 0.5,
    rolloff: float = 1.0,
    fundamental: float = 125.0,
) -> bytes:
    """The Task 2.1 voiced-speech surrogate (see test_transcription.py): a
    harmonic comb with energy in every mel band, ``rolloff`` as the voice."""
    period_samples = SAMPLE_RATE / fundamental
    if period_samples != int(period_samples):
        raise ValueError("fundamental must divide the sample rate evenly")
    period = int(period_samples)
    harmonics = range(1, period // 2)
    weights = [k**-rolloff for k in harmonics]
    scale = amplitude * 32767 / sum(weights)
    one_period = [
        int(
            scale
            * sum(
                weight * math.sin(2 * math.pi * k * i / period)
                for k, weight in zip(harmonics, weights, strict=True)
            )
        )
        for i in range(period)
    ]
    count = int(seconds * SAMPLE_RATE)
    samples = (one_period * (count // period + 1))[:count]
    return struct.pack(f"<{count}h", *samples)


def amplitude_vad(frame: bytes) -> float:
    samples = struct.unpack(f"<{len(frame) // 2}h", frame)
    peak = max(abs(s) for s in samples)
    return 0.95 if peak > 1000 else 0.02


def _make_store(session_dir: Path, pcm: bytes) -> SessionCrypto:
    """Encrypted store with a stub key file — the reference pipeline run
    only (``transcribe_session`` never unwraps the blob)."""
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / KEY_FILENAME).write_bytes(b"\0" * 64)
    crypto = SessionCrypto()
    store = SessionChunkStore.create(session_dir / "audio.enc", crypto, session_dir.name)
    for i in range(0, len(pcm), 32_000):
        store.append_chunk(pcm[i : i + 32_000])
    store.finish()
    return crypto


def _write_wav(
    path: Path,
    frames: bytes,
    *,
    channels: int = 1,
    rate: int = SAMPLE_RATE,
    width: int = BYTES_PER_SAMPLE,
) -> Path:
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(width)
        writer.setframerate(rate)
        writer.writeframes(frames)
    return path


def _raw_wav(pcm: bytes) -> bytes:
    """A 16 kHz mono 16-bit WAV built by hand so the data chunk may carry an
    odd byte count - something ``wave``'s writer will never produce."""
    fmt = struct.pack("<IHHIIHH", 16, 1, 1, SAMPLE_RATE, SAMPLE_RATE * 2, 2, 16)
    data_size = struct.pack("<I", len(pcm))
    riff_size = struct.pack("<I", 4 + 8 + 16 + 8 + len(pcm))
    return b"RIFF" + riff_size + b"WAVE" + b"fmt " + fmt + b"data" + data_size + pcm


def _track(*rows: tuple[float, float, str]) -> LabelTrack:
    return parse_audacity_labels("".join(f"{s}\t{e}\t{label}\n" for s, e, label in rows))


def _truths(*rows: tuple[float, float, str | None]) -> list[SegmentTruth]:
    return [
        SegmentTruth(start, end, label, 1.0 if label else 0.0, False) for start, end, label in rows
    ]


def _words(text: str) -> tuple[TranscriptWord, ...]:
    return tuple(
        TranscriptWord(
            word_text=token,
            start_seconds=index * 0.3,
            end_seconds=index * 0.3 + 0.25,
            probability=0.9,
            uncertain=False,
        )
        for index, token in enumerate(text.split())
    )


def _document(rows: Sequence[tuple[float, float, str, str]]) -> TranscriptDocument:
    """``rows`` are ``(start, end, speaker, text)``."""
    return TranscriptDocument(
        session_id="a" * 32,
        created_at=datetime(2026, 9, 4, 9, 0, tzinfo=UTC),
        model_name="mock",
        sample_rate=SAMPLE_RATE,
        transcript_segments=tuple(
            TranscriptSegment(
                start_seconds=start,
                end_seconds=end,
                speaker=speaker,
                transcript_words=_words(text),
            )
            for start, end, speaker, text in rows
        ),
    )


def _evidence(speaker: str, share: float) -> SpeakerEvidence:
    return SpeakerEvidence(
        speaker=speaker,
        speech_seconds=share * 10.0,
        talk_time_share=share,
        utterance_count=1,
        question_count=0,
        question_rate=0.0,
        spoke_first=False,
        score=0.0,
    )


def _preselection(
    speaker: str | None,
    *,
    margin: float = 0.2,
    shares: Sequence[tuple[str, float]] = ((SPEAKER_1, 0.6), (SPEAKER_2, 0.4)),
) -> SpeakerRolePreselection:
    return SpeakerRolePreselection(
        speaker, margin, tuple(_evidence(label, share) for label, share in shares)
    )


def _two_voice_pcm() -> bytes:
    """The ``test_two_voices_get_two_speakers`` fixture: the pipeline labels
    it ``speaker_1, speaker_2, speaker_1``."""
    gap = silence_pcm(1.0)
    return (
        gap
        + tone_pcm(1.5, frequency=220.0)
        + gap
        + tone_pcm(1.5, frequency=2600.0)
        + gap
        + tone_pcm(1.5, frequency=220.0)
        + gap
    )


# Role labels over the three tones above (the gaps stay unlabelled).
TWO_VOICE_LABELS = "1.0\t2.5\tclinician\n3.5\t5.0\tpatient\n6.0\t7.5\tclinician\n"


def _temp_stores() -> set[Path]:
    """Every harness temporary root currently in the system temp dir."""
    return {
        path
        for path in Path(tempfile.gettempdir()).iterdir()
        if path.name.startswith(TEMP_DIR_PREFIX)
    }


# ---------------------------------------------------------------------------
# module import
# ---------------------------------------------------------------------------


class TestModuleImport:
    def test_imports_no_ml_stack_at_import_time(self) -> None:
        assert "numpy" not in speaker_eval.__dict__
        assert "onnxruntime" not in speaker_eval.__dict__
        assert "faster_whisper" not in speaker_eval.__dict__


# ---------------------------------------------------------------------------
# label tracks
# ---------------------------------------------------------------------------


class TestParseAudacityLabels:
    def test_tab_rows_parse_in_order(self) -> None:
        track = parse_audacity_labels("0.0\t1.5\tclinician\n1.5\t3.0\tpatient\n")
        assert track.spans == (LabelSpan(0.0, 1.5, "clinician"), LabelSpan(1.5, 3.0, "patient"))
        assert track.labels == ("clinician", "patient")
        assert track.point_labels_ignored == 0

    def test_spectral_selection_rows_are_ignored(self) -> None:
        text = "0.0\t1.0\tclinician\n\\\t200.0\t4000.0\n1.0\t2.0\tpatient\n"
        track = parse_audacity_labels(text)
        assert [span.label for span in track.spans] == ["clinician", "patient"]

    def test_point_labels_are_ignored_and_counted(self) -> None:
        text = "0.0\t1.0\tclinician\n2.5\t2.5\tpatient\n3.0\t3.0\tclinician\n"
        track = parse_audacity_labels(text)
        assert len(track.spans) == 1
        assert track.point_labels_ignored == 2

    def test_blank_lines_and_crlf_are_tolerated(self) -> None:
        track = parse_audacity_labels("0.0\t1.0\tclinician\r\n\r\n1.0\t2.0\tpatient\r\n")
        assert track.labels == ("clinician", "patient")

    def test_missing_clinician_is_refused_naming_the_labels_found(self) -> None:
        with pytest.raises(LabelTrackError, match="clinician") as info:
            parse_audacity_labels("0.0\t1.0\tpatient\n1.0\t2.0\tparent\n")
        assert "patient" in str(info.value)
        assert "parent" in str(info.value)

    def test_an_empty_track_is_refused(self) -> None:
        with pytest.raises(LabelTrackError, match="clinician"):
            parse_audacity_labels("")

    def test_two_spellings_of_clinician_are_refused(self) -> None:
        with pytest.raises(LabelTrackError) as info:
            parse_audacity_labels("0.0\t1.0\tclinician\n1.0\t2.0\tClinician\n2.0\t3.0\tpatient\n")
        assert "clinician" in str(info.value)
        assert "Clinician" in str(info.value)

    def test_case_and_surrounding_whitespace_are_normalised(self) -> None:
        track = parse_audacity_labels("0.0\t1.0\t  CLINICIAN \n1.0\t2.0\tPatient\n")
        assert track.labels == ("clinician", "patient")
        assert [span.label for span in track.spans] == ["clinician", "patient"]

    def test_case_variants_of_any_role_are_refused_rather_than_split(self) -> None:
        # Stricter than the task's clinician-only rule, on purpose: the
        # alternative is scoring one role as two speakers with no signal.
        with pytest.raises(LabelTrackError) as info:
            parse_audacity_labels("0.0\t1.0\tclinician\n1.0\t2.0\tpatient\n2.0\t3.0\tPatient\n")
        assert "patient" in str(info.value)
        assert "Patient" in str(info.value)

    @pytest.mark.parametrize(
        "row",
        [
            "0.0\t1.0",
            "abc\t1.0\tclinician",
            "1.0\t0.5\tclinician",
            "-1.0\t0.5\tclinician",
            "nan\t0.5\tclinician",
            "0.0\t1.0\t   ",
        ],
    )
    def test_malformed_rows_are_refused_with_the_line_number(self, row: str) -> None:
        with pytest.raises(LabelTrackError, match="line 2"):
            parse_audacity_labels("0.0\t1.0\tclinician\n" + row + "\n")

    def test_overlapping_and_gapped_spans_are_data(self) -> None:
        track = parse_audacity_labels(
            "0.0\t2.0\tclinician\n1.0\t3.0\tpatient\n10.0\t11.0\tclinician\n"
        )
        assert len(track.spans) == 3


# ---------------------------------------------------------------------------
# WAV input
# ---------------------------------------------------------------------------


class TestReadWavPcm:
    def test_reads_16k_mono_16bit_pcm_exactly(self, tmp_path: Path) -> None:
        pcm = tone_pcm(0.5)
        assert read_wav_pcm(_write_wav(tmp_path / "a.wav", pcm)) == pcm

    @pytest.mark.parametrize(
        ("channels", "rate", "width"),
        [(2, SAMPLE_RATE, 2), (1, 44_100, 2), (1, SAMPLE_RATE, 3)],
        ids=["stereo", "44k1", "24bit"],
    )
    def test_other_formats_are_refused_with_the_conversion_recipe(
        self, tmp_path: Path, channels: int, rate: int, width: int
    ) -> None:
        path = _write_wav(
            tmp_path / "a.wav", b"\0" * (100 * channels * width), channels=channels,
            rate=rate, width=width,
        )
        with pytest.raises(WavFormatError) as info:
            read_wav_pcm(path)
        message = str(info.value)
        assert "a.wav" in message
        assert "16 kHz" in message and "mono" in message and "16-bit" in message
        assert "Project Rate 16000" in message
        assert "Mix Stereo Down to Mono" in message

    def test_non_wav_bytes_are_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "x.wav"
        path.write_bytes(b"not a wav file at all")
        with pytest.raises(WavFormatError, match="16 kHz"):
            read_wav_pcm(path)

    def test_a_header_only_wav_is_refused(self, tmp_path: Path) -> None:
        """Round 62 PR-MED-003: zero frames is not a recording."""
        path = _write_wav(tmp_path / "empty.wav", b"")
        with pytest.raises(WavFormatError, match="no audio frames") as info:
            read_wav_pcm(path)
        assert "empty.wav" in str(info.value)
        assert "Project Rate 16000" in str(info.value)

    def test_a_truncated_data_chunk_is_refused(self, tmp_path: Path) -> None:
        """Round 62 PR-MED-003: the header's frame count must be fully readable."""
        path = _write_wav(tmp_path / "cut.wav", tone_pcm(0.5))
        data = path.read_bytes()
        path.write_bytes(data[:-1000])
        with pytest.raises(WavFormatError, match="truncated") as info:
            read_wav_pcm(path)
        assert "cut.wav" in str(info.value)

    def test_a_partial_trailing_sample_is_refused(self, tmp_path: Path) -> None:
        """Round 63 PR-LOW-002: an odd data-chunk byte is a partial frame, not
        silently floored away - detected through the public ``wave`` API."""
        odd = tmp_path / "odd.wav"
        odd.write_bytes(_raw_wav(tone_pcm(0.1) + b"\x7f"))
        with pytest.raises(WavFormatError, match="partial sample") as info:
            read_wav_pcm(odd)
        assert "odd.wav" in str(info.value)
        assert "Project Rate 16000" in str(info.value)
        # the same hand-built layout with an even payload reads back exactly
        even = tmp_path / "even.wav"
        even.write_bytes(_raw_wav(tone_pcm(0.1)))
        assert read_wav_pcm(even) == tone_pcm(0.1)


# ---------------------------------------------------------------------------
# alignment
# ---------------------------------------------------------------------------


class TestAlignSegments:
    def test_the_majority_label_wins_and_a_weak_majority_is_mixed(self) -> None:
        track = _track((0.0, 3.0, "clinician"), (3.0, 4.0, "patient"))
        (truth,) = align_segments([SpeechSegment(0.0, 4.0)], track)
        assert truth.true_label == "clinician"
        assert truth.majority_share == pytest.approx(0.75)
        assert truth.mixed

    def test_zero_overlap_is_unlabelled(self) -> None:
        track = _track((0.0, 1.0, "clinician"))
        (truth,) = align_segments([SpeechSegment(5.0, 6.0)], track)
        assert truth.true_label is None
        assert truth.majority_share == 0.0
        assert not truth.mixed

    def test_the_eighty_percent_boundary(self) -> None:
        exact = _track((0.0, 4.0, "clinician"), (4.0, 5.0, "patient"))
        (truth,) = align_segments([SpeechSegment(0.0, 5.0)], exact)
        assert truth.true_label == "clinician"
        assert truth.majority_share == pytest.approx(0.8)
        assert not truth.mixed  # exactly 80 % is not "under 80 %"

        under = _track((0.0, 3.9, "clinician"), (3.9, 5.0, "patient"))
        (truth,) = align_segments([SpeechSegment(0.0, 5.0)], under)
        assert truth.true_label == "clinician"
        assert truth.mixed

    def test_share_is_over_the_overlapped_duration_not_the_segment(self) -> None:
        track = _track((0.0, 1.0, "clinician"))
        (truth,) = align_segments([SpeechSegment(0.0, 2.0)], track)
        assert truth.majority_share == 1.0
        assert not truth.mixed

    def test_overlaps_of_one_label_accumulate_across_spans(self) -> None:
        track = _track((0.0, 1.0, "clinician"), (2.0, 3.0, "clinician"), (1.0, 2.0, "patient"))
        (truth,) = align_segments([SpeechSegment(0.0, 3.0)], track)
        assert truth.true_label == "clinician"
        assert truth.majority_share == pytest.approx(2 / 3)

    def test_an_exact_tie_has_no_majority(self) -> None:
        """Round 62 PR-MED-002: a tie is scored by nobody, never by spelling."""
        track = _track((0.0, 1.0, "patient"), (1.0, 2.0, "clinician"))
        (truth,) = align_segments([SpeechSegment(0.0, 2.0)], track)
        assert truth.true_label is None
        assert truth.tied
        assert truth.mixed
        assert truth.majority_share == pytest.approx(0.5)

    def test_a_lead_beyond_float_noise_is_not_a_tie(self) -> None:
        track = _track((0.0, 1.0, "patient"), (1.0, 2.001, "clinician"))
        (truth,) = align_segments([SpeechSegment(0.0, 2.001)], track)
        assert truth.true_label == "clinician"
        assert not truth.tied

    def test_exact_eighty_percent_from_decimal_timestamps_is_not_mixed(self) -> None:
        """Round 62 PR-LOW-001: 0.3/0.7/0.8 put an exact 80 % a few ulps under."""
        track = _track((0.3, 0.7, "clinician"), (0.7, 0.8, "patient"))
        (truth,) = align_segments([SpeechSegment(0.3, 0.8)], track)
        assert truth.true_label == "clinician"
        assert truth.majority_share == pytest.approx(0.8)
        assert not truth.mixed
        under = _track((0.3, 0.69, "clinician"), (0.69, 0.8, "patient"))
        (truth,) = align_segments([SpeechSegment(0.3, 0.8)], under)
        assert truth.mixed

    def test_one_truth_per_segment_in_order(self) -> None:
        track = _track((0.0, 1.0, "clinician"), (2.0, 3.0, "patient"))
        truths = align_segments(
            [SpeechSegment(0.0, 1.0), SpeechSegment(1.2, 1.8), SpeechSegment(2.0, 3.0)], track
        )
        assert [truth.true_label for truth in truths] == ["clinician", None, "patient"]


# ---------------------------------------------------------------------------
# cluster metrics
# ---------------------------------------------------------------------------


class TestClusterMetrics:
    def test_perfect_clustering_scores_one(self) -> None:
        truths = _truths((0, 1, "clinician"), (1, 3, "patient"), (3, 4, "clinician"))
        metrics = cluster_metrics([SPEAKER_1, SPEAKER_2, SPEAKER_1], truths)
        assert metrics.accuracy_seconds == pytest.approx(1.0)
        assert metrics.accuracy_count == pytest.approx(1.0)
        assert metrics.correct_count == 3 and metrics.labelled_count == 3
        assert metrics.labelled_seconds == pytest.approx(4.0)
        assert metrics.mapping == ((SPEAKER_1, "clinician"), (SPEAKER_2, "patient"))
        assert metrics.predicted_speaker_count == 2 and metrics.true_speaker_count == 2
        assert dict(metrics.purity) == {SPEAKER_1: 1.0, SPEAKER_2: 1.0}

    def test_cluster_names_do_not_matter(self) -> None:
        truths = _truths((0, 1, "clinician"), (1, 3, "patient"), (3, 4, "clinician"))
        swapped = cluster_metrics([SPEAKER_2, SPEAKER_1, SPEAKER_2], truths)
        assert swapped.accuracy_seconds == pytest.approx(1.0)
        assert swapped.mapping == ((SPEAKER_1, "patient"), (SPEAKER_2, "clinician"))

    def test_duration_weighting_differs_from_the_count(self) -> None:
        truths = _truths((0, 1, "clinician"), (1, 2, "clinician"), (2, 10, "patient"))
        metrics = cluster_metrics([SPEAKER_1] * 3, truths)
        assert metrics.mapping == ((SPEAKER_1, "patient"),)
        assert metrics.accuracy_seconds == pytest.approx(0.8)
        assert metrics.accuracy_count == pytest.approx(1 / 3)

    def test_three_true_two_predicted_shows_the_merge(self) -> None:
        # clinician 10 s alone in cluster 1; patient 6 s + parent 4 s merged in cluster 2
        truths = _truths((0, 10, "clinician"), (10, 16, "patient"), (16, 20, "parent"))
        metrics = cluster_metrics([SPEAKER_1, SPEAKER_2, SPEAKER_2], truths)
        assert metrics.true_speaker_count == 3
        assert metrics.predicted_speaker_count == 2
        # the confusion matrix is where the third voice's merge is visible
        assert metrics.seconds(SPEAKER_2, "patient") == pytest.approx(6.0)
        assert metrics.seconds(SPEAKER_2, "parent") == pytest.approx(4.0)
        assert metrics.seconds(SPEAKER_1, "parent") == 0.0
        # accuracy is bounded by the third speaker's share of labelled time
        assert metrics.accuracy_seconds == pytest.approx(16 / 20)
        assert metrics.accuracy_seconds <= 1.0 - 4 / 20 + 1e-9
        assert metrics.mapping == ((SPEAKER_1, "clinician"), (SPEAKER_2, "patient"))
        assert dict(metrics.purity)[SPEAKER_2] == pytest.approx(0.6)

    def test_unlabelled_segments_are_excluded_from_every_metric(self) -> None:
        truths = _truths((0, 1, "clinician"), (1, 2, None), (2, 3, "patient"))
        metrics = cluster_metrics([SPEAKER_1, SPEAKER_2, SPEAKER_2], truths)
        assert metrics.labelled_count == 2
        assert metrics.labelled_seconds == pytest.approx(2.0)
        assert metrics.accuracy_seconds == pytest.approx(1.0)
        assert metrics.seconds(SPEAKER_2, "patient") == pytest.approx(1.0)
        assert sum(seconds for _, _, seconds in metrics.confusion_seconds) == pytest.approx(2.0)

    def test_more_clusters_than_speakers_leaves_one_unmapped(self) -> None:
        truths = _truths((0, 3, "clinician"), (3, 4, "clinician"), (4, 6, "patient"))
        metrics = cluster_metrics([SPEAKER_1, "speaker_3", SPEAKER_2], truths)
        assert metrics.mapping == ((SPEAKER_1, "clinician"), (SPEAKER_2, "patient"))
        assert metrics.accuracy_seconds == pytest.approx(5 / 6)
        assert metrics.predicted_speaker_count == 3

    def test_a_duration_tie_between_mappings_prefers_the_count_whatever_the_spelling(
        self,
    ) -> None:
        """Round 63 PR-MED-005: the peer's matrix - two 3-second mappings whose
        segment counts are 11 and 2. Renaming the true roles so they sort the
        other way must not change which count is reported."""
        for first, second in (("alpha", "beta"), ("beta", "alpha")):
            predicted = ["p1", "p1", "p2", *(["p2"] * 10)]
            truths = _truths(
                (0, 2, first),  # p1 -> first: 2 s, 1 segment
                (2, 3, second),  # p1 -> second: 1 s, 1 segment
                (3, 5, first),  # p2 -> first: 2 s, 1 segment
                *((5 + i * 0.1, 5.1 + i * 0.1, second) for i in range(10)),  # p2 -> second
            )
            metrics = cluster_metrics(predicted, truths)
            assert metrics.correct_count == 11
            assert metrics.accuracy_count == pytest.approx(11 / 13)
            assert metrics.accuracy_seconds == pytest.approx(0.5)
            assert metrics.mapping == (("p1", first), ("p2", second))

    # The peer's round-64 matrix under two namings whose every sort order is
    # reversed - BOTH the predicted clusters and the true labels (round 65).
    MATRIX_NAMINGS = (
        (("p1", "p2", "p3"), ("a", "b", "c")),
        (("q3", "q2", "q1"), ("c", "b", "a")),
    )

    def test_a_three_cluster_near_tie_chain_is_traversal_independent(self) -> None:
        """Round 64 PR-MED-007 / round 65 PR-LOW-009: the peer's matrix - three
        mappings within a chain of sub-epsilon steps that is not transitive.
        A moving anchor reported 80/212 one way and 100/212 the other; the
        set-based objective over correctly rounded totals reports identical
        numbers - every field, every purity, every cell - whichever way the
        predicted and true labels sort."""
        e = speaker_eval._SECONDS_EPSILON
        seconds = (
            (10.0, 10 - 10 * e, 10 + 1.5 * e),
            (10 - 10 * e, 10.0, 10 + 0.75 * e),
            (10.0, 10.0, 10.0),
        )
        counts = ((30, 1, 20), (1, 30, 30), (30, 30, 40))
        results = []
        for clusters, names in self.MATRIX_NAMINGS:
            predicted: list[str] = []
            rows: list[tuple[float, float, str | None]] = []
            for row, cluster in enumerate(clusters):
                for column, name in enumerate(names):
                    total, n = seconds[row][column], counts[row][column]
                    predicted += [cluster] * n
                    rows += [(0.0, total / n, name)] * n
            results.append(cluster_metrics(predicted, _truths(*rows)))
        first, second = results
        assert first.correct_count == second.correct_count == 90
        assert first.accuracy_count == second.accuracy_count == pytest.approx(90 / 212)
        assert first.accuracy_seconds == second.accuracy_seconds
        assert first.labelled_seconds == second.labelled_seconds
        assert first.labelled_count == second.labelled_count == 212
        assert first.predicted_speaker_count == second.predicted_speaker_count == 3
        assert first.true_speaker_count == second.true_speaker_count == 3
        (clusters_a, names_a), (clusters_b, names_b) = self.MATRIX_NAMINGS
        for row in range(3):
            assert dict(first.purity)[clusters_a[row]] == dict(second.purity)[clusters_b[row]]
            for column in range(3):
                assert first.seconds(clusters_a[row], names_a[column]) == second.seconds(
                    clusters_b[row], names_b[column]
                )

    def test_summation_order_cannot_move_a_metric(self) -> None:
        """Round 65 PR-LOW-009: 746.67 + 411.27 + 541.32 differs by an ulp
        between forward and reversed IEEE-754 order; a correctly rounded
        total does not, so a rename cannot move ``accuracy_seconds`` and a
        perfect mapping scores exactly 1.0."""
        durations = (746.67, 411.27, 541.32)
        results = []
        for clusters, names in self.MATRIX_NAMINGS:
            rows = [(0.0, d, name) for d, name in zip(durations, names, strict=True)]
            results.append(cluster_metrics(list(clusters), _truths(*rows)))
        first, second = results
        assert first.accuracy_seconds == second.accuracy_seconds == 1.0
        assert first.labelled_seconds == second.labelled_seconds == math.fsum(durations)

    def test_no_labelled_segments_cannot_be_scored(self) -> None:
        with pytest.raises(ValueError, match="labelled"):
            cluster_metrics([SPEAKER_1], _truths((0, 1, None)))

    def test_length_mismatch_is_refused(self) -> None:
        with pytest.raises(ValueError):
            cluster_metrics([SPEAKER_1], _truths((0, 1, "clinician"), (1, 2, "patient")))


# ---------------------------------------------------------------------------
# role outcome
# ---------------------------------------------------------------------------


class TestRoleOutcome:
    TRUTHS = _truths((0, 10, "clinician"), (10, 12, "patient"), (12, 20, "patient"))
    PREDICTED = [SPEAKER_1, SPEAKER_1, SPEAKER_2]  # cluster 1 = 10 s clinician + 2 s patient

    def test_correct_when_the_preselected_cluster_is_mostly_the_clinician(self) -> None:
        outcome = role_outcome(_preselection(SPEAKER_1), self.PREDICTED, self.TRUTHS)
        assert outcome.verdict == "CORRECT"
        assert outcome.preselected_speaker == SPEAKER_1
        assert outcome.majority_true_label == "clinician"
        assert outcome.margin == 0.2
        assert outcome.clinician_cluster_talk_time_share == 0.6
        assert outcome.clinician_labelled_share == pytest.approx(0.5)

    def test_wrong_when_it_is_mostly_someone_else(self) -> None:
        outcome = role_outcome(_preselection(SPEAKER_2), self.PREDICTED, self.TRUTHS)
        assert outcome.verdict == "WRONG"
        assert outcome.majority_true_label == "patient"
        # the clinician's cluster is still identified and its share recorded
        assert outcome.clinician_cluster_talk_time_share == 0.6

    def test_none_when_there_is_no_preselection(self) -> None:
        outcome = role_outcome(_preselection(None, margin=0.0), self.PREDICTED, self.TRUTHS)
        assert outcome.verdict == "NONE"
        assert outcome.preselected_speaker is None
        assert outcome.majority_true_label is None
        assert outcome.clinician_labelled_share == pytest.approx(0.5)

    def test_the_majority_is_duration_weighted(self) -> None:
        truths = _truths((0, 1, "clinician"), (1, 2, "clinician"), (2, 10, "patient"))
        preselection = _preselection(SPEAKER_1, shares=((SPEAKER_1, 1.0),))
        outcome = role_outcome(preselection, [SPEAKER_1] * 3, truths)
        assert outcome.verdict == "WRONG"  # two short clinician turns lose to one long turn
        assert outcome.majority_true_label == "patient"
        assert outcome.clinician_cluster_talk_time_share is None

    def test_wrong_when_the_preselected_cluster_has_no_labelled_segment(self) -> None:
        truths = _truths((0, 1, "clinician"), (1, 2, None))
        outcome = role_outcome(_preselection(SPEAKER_2), [SPEAKER_1, SPEAKER_2], truths)
        assert outcome.verdict == "WRONG"
        assert outcome.majority_true_label is None

    def test_unlabelled_segments_do_not_vote(self) -> None:
        truths = _truths((0, 1, "clinician"), (1, 9, None))
        outcome = role_outcome(_preselection(SPEAKER_1), [SPEAKER_1, SPEAKER_1], truths)
        assert outcome.verdict == "CORRECT"
        assert outcome.clinician_labelled_share == pytest.approx(1.0)

    @pytest.mark.parametrize("other", ["patient", "assistant"])
    def test_a_tied_preselected_cluster_is_wrong_whatever_the_spelling(self, other: str) -> None:
        """Round 62 PR-MED-002: equal clinician/other seconds is no majority.
        ``assistant`` sorts BEFORE ``clinician`` and ``patient`` after it -
        the verdict must not depend on which."""
        truths = _truths((0, 5, "clinician"), (5, 10, other))
        outcome = role_outcome(_preselection(SPEAKER_1), [SPEAKER_1, SPEAKER_1], truths)
        assert outcome.verdict == "WRONG"
        assert outcome.majority_true_label is None
        assert outcome.clinician_cluster_talk_time_share is None

    def test_a_three_label_top_tie_is_wrong(self) -> None:
        truths = _truths((0, 4, "clinician"), (4, 8, "patient"), (8, 12, "parent"))
        outcome = role_outcome(_preselection(SPEAKER_1), [SPEAKER_1] * 3, truths)
        assert outcome.verdict == "WRONG"
        assert outcome.majority_true_label is None

    def test_a_lead_beyond_float_noise_is_a_majority(self) -> None:
        truths = _truths((0, 5, "clinician"), (5, 9.999, "patient"))
        outcome = role_outcome(_preselection(SPEAKER_1), [SPEAKER_1, SPEAKER_1], truths)
        assert outcome.verdict == "CORRECT"
        assert outcome.majority_true_label == "clinician"

    def test_two_clusters_holding_the_clinician_equally_report_no_share(self) -> None:
        """Round 63 PR-MED-005: an exact clinician-seconds tie between clusters
        is exposed as None, never settled by the cluster's name."""
        preselection = _preselection(SPEAKER_1, shares=((SPEAKER_1, 0.7), (SPEAKER_2, 0.3)))
        clusters = [SPEAKER_1, SPEAKER_2]
        tied = _truths((0, 5, "clinician"), (5, 10, "clinician"))
        outcome = role_outcome(preselection, clusters, tied)
        assert outcome.verdict == "CORRECT"  # the preselected cluster is all clinician
        assert outcome.clinician_cluster_talk_time_share is None
        led = _truths((0, 5, "clinician"), (5, 9, "clinician"))
        outcome = role_outcome(preselection, clusters, led)
        assert outcome.clinician_cluster_talk_time_share == 0.7


# ---------------------------------------------------------------------------
# scoring a document and rendering the report
# ---------------------------------------------------------------------------


class TestScoreDocumentAndReport:
    def test_report_and_result_carry_no_transcript_text(self) -> None:
        sentinel = "zebrafruit"
        document = _document(
            [
                (0.0, 2.0, SPEAKER_1, f"how is the {sentinel} today?"),
                (2.0, 5.0, SPEAKER_2, f"the {sentinel} is fine"),
            ]
        )
        track = _track((0.0, 2.0, "clinician"), (2.0, 5.0, "patient"))
        result = score_document("rec-one", document, track, [SPEAKER_1, SPEAKER_1])
        report = render_report([result], model_name="whisper-medium-test")

        assert sentinel not in report
        assert sentinel not in repr(result)
        assert "whisper-medium-test" in report
        assert "rec-one" in report

        after = result.condition(AFTER)
        assert after.predicted_labels == (SPEAKER_1, SPEAKER_2)
        assert after.metrics is not None
        assert after.metrics.accuracy_seconds == pytest.approx(1.0)
        assert after.role.verdict == "CORRECT"  # speaker_1 asks and speaks first
        assert after.role.preselected_speaker == SPEAKER_1

        before = result.condition(BEFORE)
        assert before.merged
        assert before.metrics is None
        assert before.role.verdict == "NONE"  # a merged clustering has nothing to choose against

        assert "| merged |" in report
        assert "| CORRECT |" in report
        assert "| NONE |" in report
        assert "### Aggregate per condition" in report
        assert f"| {AFTER} | 1 | 1 | 0 | 1.000 |" in report
        assert f"| {BEFORE} | 1 | 0 | 1 | - | - | 0 | 0 | 1 |" in report

    def test_unlabelled_mixed_and_point_label_counts_are_reported(self) -> None:
        document = _document(
            [
                (0.0, 1.0, SPEAKER_1, "one"),
                (5.0, 6.0, SPEAKER_2, "two"),
                (10.0, 14.0, SPEAKER_1, "three"),
            ]
        )
        track = parse_audacity_labels(
            "0.0\t1.0\tclinician\n10.0\t13.0\tpatient\n"
            "13.0\t14.0\tclinician\n20.0\t20.0\tpatient\n"
        )
        result = score_document("rec", document, track, [SPEAKER_1, SPEAKER_2, SPEAKER_1])
        assert result.segment_count == 3
        assert result.unlabelled_count == 1
        assert result.mixed_count == 1
        assert result.point_labels_ignored == 1
        report = render_report([result], model_name="m")
        assert "| rec | 3 | 1 | 1 | clinician, patient |" in report
        assert "rec: 1 point label(s) ignored" in report

    def test_a_tied_segment_is_mixed_not_unlabelled_and_scored_by_nobody(self) -> None:
        """Round 62 PR-MED-002 at the recording level."""
        document = _document([(0.0, 2.0, SPEAKER_1, "one")])
        track = _track((0.0, 1.0, "clinician"), (1.0, 2.0, "patient"))
        result = score_document("tie", document, track, [SPEAKER_1])
        assert result.unlabelled_count == 0
        assert result.mixed_count == 1
        assert result.tied_count == 1
        assert result.condition(AFTER).metrics is None  # nobody is credited
        assert result.condition(AFTER).role.verdict == "NONE"  # one cluster: nothing to choose
        report = render_report([result], model_name="m")
        assert "tie: 1 tied segment(s) - no majority" in report

    def test_no_labelled_segments_is_unscored_not_an_error(self) -> None:
        document = _document([(0.0, 1.0, SPEAKER_1, "one"), (2.0, 3.0, SPEAKER_2, "two")])
        track = _track((50.0, 60.0, "clinician"))
        result = score_document("rec", document, track, [SPEAKER_1, SPEAKER_2])
        after = result.condition(AFTER)
        assert after.metrics is None
        assert not after.merged
        assert "unscored" in render_report([result], model_name="m")

    def test_confusion_block_and_mapping_are_rendered(self) -> None:
        document = _document(
            [
                (0.0, 10.0, SPEAKER_1, "a"),
                (10.0, 16.0, SPEAKER_2, "b"),
                (16.0, 20.0, SPEAKER_2, "c"),
            ]
        )
        track = _track((0.0, 10.0, "clinician"), (10.0, 16.0, "patient"), (16.0, 20.0, "parent"))
        result = score_document("three", document, track, [SPEAKER_1, SPEAKER_2, SPEAKER_2])
        report = render_report([result], model_name="m")
        assert f"### three - {AFTER}: confusion in seconds" in report
        assert "| speaker_2 | 0.0 | 4.0 | 6.0 | 0.600 |" in report
        assert "Mapping: speaker_1 -> clinician, speaker_2 -> patient" in report

    def test_before_label_count_must_match(self) -> None:
        document = _document([(0.0, 1.0, SPEAKER_1, "one")])
        with pytest.raises(ValueError):
            score_document("rec", document, _track((0.0, 1.0, "clinician")), [])

    def test_an_empty_run_still_renders(self) -> None:
        report = render_report([], model_name="m")
        assert "Recordings scored: 0" in report
        assert f"| {AFTER} | 0 | 0 | 0 | - | - | 0 | 0 | 0 |" in report


# ---------------------------------------------------------------------------
# the normalisation toggle (numpy-gated) — the pin that the "before"
# condition is the real pre-Task-2.1 behaviour
# ---------------------------------------------------------------------------


class TestNormalisationToggle:
    def test_off_reproduces_the_pre_task_2_1_embedding(self) -> None:
        np = pytest.importorskip("numpy")
        pcm = comb_pcm(0.4, amplitude=0.5)
        on = _segment_embedding(pcm, np)
        off = _segment_embedding(pcm, np, cepstral_mean_normalisation=False)
        # the toggle is exactly the per-segment mean subtraction on the mel block
        assert np.allclose(on[:-1], off[:-1] - off[:-1].mean(), atol=1e-5)
        # and the centroid is untouched by either
        assert on[-1] == off[-1]
        # 20 dB of gain shifts EVERY un-normalised mel band by ~2 ln 10 = 4.6
        quiet_off = _segment_embedding(
            comb_pcm(0.4, amplitude=0.05), np, cepstral_mean_normalisation=False
        )
        assert float(np.abs(off[:-1] - quiet_off[:-1]).min()) > 4.0

    def test_off_splits_the_gain_shifted_pair_the_default_keeps_together(self) -> None:
        """The mirror of ``test_a_gain_shifted_copy_clusters_with_its_original``:
        with normalisation off, the 20 dB-quieter copy of the SAME voice no
        longer clusters with its original — loudness, not voice, decides."""
        pytest.importorskip("numpy")
        loud = comb_pcm(0.4, amplitude=0.5, rolloff=1.0)
        other = comb_pcm(0.4, amplitude=0.5, rolloff=1.35)
        quiet = comb_pcm(0.4, amplitude=0.05, rolloff=1.0)
        assert label_speakers([loud, other, quiet]) == [SPEAKER_1, SPEAKER_2, SPEAKER_1]
        before = label_speakers([loud, other, quiet], cepstral_mean_normalisation=False)
        assert before[0] != before[2]

    def test_the_default_is_the_shipped_behaviour(self) -> None:
        pytest.importorskip("numpy")
        pcms = [
            tone_pcm(1.0, frequency=220.0),
            tone_pcm(1.0, frequency=2600.0),
            tone_pcm(1.0, frequency=220.0),
        ]
        expected = [SPEAKER_1, SPEAKER_2, SPEAKER_1]
        assert label_speakers(pcms) == expected
        assert label_speakers(pcms, cepstral_mean_normalisation=True) == expected


# ---------------------------------------------------------------------------
# evaluate_recording: input refusals (CI-safe) and the end-to-end run
# (Windows: the temporary store carries a REAL DPAPI-wrapped key)
# ---------------------------------------------------------------------------


class TestEvaluateRecordingInputs:
    def test_a_bad_label_track_is_refused_before_any_store_exists(self, tmp_path: Path) -> None:
        wav = _write_wav(tmp_path / "r.wav", tone_pcm(0.2))
        labels = tmp_path / "r.txt"
        labels.write_text("0.0\t0.2\tpatient\n", encoding="utf-8")
        stores_before = _temp_stores()
        with pytest.raises(LabelTrackError, match="clinician"):
            evaluate_recording(wav, labels, MockSpeechProvider(), amplitude_vad)
        assert _temp_stores() == stores_before

    def test_a_wrong_format_wav_is_refused_before_any_store_exists(self, tmp_path: Path) -> None:
        wav = _write_wav(tmp_path / "r.wav", b"\0" * 400, rate=44_100)
        labels = tmp_path / "r.txt"
        labels.write_text("0.0\t0.2\tclinician\n", encoding="utf-8")
        stores_before = _temp_stores()
        with pytest.raises(WavFormatError, match="Project Rate 16000"):
            evaluate_recording(wav, labels, MockSpeechProvider(), amplitude_vad)
        assert _temp_stores() == stores_before

    def test_a_utf8_bom_on_the_label_file_is_tolerated(self, tmp_path: Path) -> None:
        wav = _write_wav(tmp_path / "r.wav", b"\0" * 400, rate=44_100)  # refused AFTER labels
        labels = tmp_path / "r.txt"
        labels.write_bytes(b"\xef\xbb\xbf0.0\t0.2\tclinician\n")
        with pytest.raises(WavFormatError):
            evaluate_recording(wav, labels, MockSpeechProvider(), amplitude_vad)


class _RaisingProvider:
    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        raise RuntimeError("provider failed")


def _refuse_unlink(_session_dir: Path) -> None:
    raise PermissionError("locked")


def _keep(*args: object, **kwargs: object) -> None:
    """A ``shutil.rmtree`` stand-in that removes nothing."""


class _RaiseOn:
    """A ``shutil.rmtree`` stand-in that raises for ONE target path (the way
    an audit hook would) and delegates every other call to the real one."""

    def __init__(self, target: Path) -> None:
        self.target = target
        self.calls: list[Path] = []
        self.real = shutil.rmtree

    def __call__(self, path: Path, *args: object, **kwargs: object) -> None:
        self.calls.append(path)
        if path == self.target:
            raise RuntimeError("audit hook")
        self.real(path, *args, **kwargs)


class _HonourFlag:
    """A ``shutil.rmtree`` stand-in that models CPython's contract for ONE
    target path - silent under ``ignore_errors=True``, a raised
    ``PermissionError`` otherwise - and delegates every other call to the
    real one. It records the flag each targeted call was given."""

    def __init__(self, target: Path) -> None:
        self.target = target
        self.real = shutil.rmtree
        self.flags: list[bool] = []

    def __call__(
        self, path: Path, *args: object, ignore_errors: bool = False, **kwargs: object
    ) -> None:
        if path == self.target:
            self.flags.append(ignore_errors)
            if ignore_errors:
                return
            raise PermissionError("locked")
        self.real(path, *args, ignore_errors=ignore_errors, **kwargs)


class _StubbornCrypto(SessionCrypto):
    def destroy(self) -> None:
        raise RuntimeError("destroy failed")


def _tracking_crypto(monkeypatch: pytest.MonkeyPatch) -> list[SessionCrypto]:
    """Route ``SessionCrypto()`` through a factory that records each instance
    so a test can assert ``destroyed`` on the key the harness built."""
    created: list[SessionCrypto] = []

    def factory() -> SessionCrypto:
        crypto = SessionCrypto()
        created.append(crypto)
        return crypto

    monkeypatch.setattr(speaker_eval, "SessionCrypto", factory)
    return created


class TestProbe:
    """Round 64 PR-MED-008: the residue probe fails closed."""

    def test_gone_present_and_unreadable(self, tmp_path: Path) -> None:
        assert _probe(tmp_path / "missing") == "gone"
        assert _probe(tmp_path) == "present"

        def refused(_: Path) -> object:
            raise PermissionError("denied")

        assert _probe(tmp_path, stat=refused) == "unreadable"


class TestDestroyTemporaryStore:
    """Round 63 PR-MED-006 / round 64 PR-MED-008: every teardown leg runs
    whatever the earlier legs did, and whatever survives is reported by path."""

    def _store(self, tmp_path: Path) -> tuple[Path, Path]:
        temp_root = tmp_path / f"{TEMP_DIR_PREFIX}test"
        session_dir = temp_root / ("c" * 32)
        session_dir.mkdir(parents=True)
        (session_dir / KEY_FILENAME).write_bytes(b"\0" * 64)
        (session_dir / "audio.enc").write_bytes(b"ciphertext")
        return temp_root, session_dir

    def test_a_raising_key_destruction_still_removes_the_store_and_is_reported(
        self, tmp_path: Path
    ) -> None:
        temp_root, session_dir = self._store(tmp_path)
        crypto = _StubbornCrypto()
        with pytest.raises(SpeakerEvalError) as info:
            _destroy_temporary_store(temp_root, session_dir, crypto)
        assert not temp_root.exists()  # the removal legs still ran
        assert "in-memory session key was NOT destroyed" in str(info.value)
        assert "in-memory key destruction: RuntimeError" in str(info.value)
        assert f"removed ({temp_root})" in str(info.value)  # the path, even with no residue

    @pytest.mark.parametrize("target", ["session_dir", "temp_root"])
    def test_each_removal_leg_raising_independently(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str
    ) -> None:
        temp_root, session_dir = self._store(tmp_path)
        stub = _RaiseOn(session_dir if target == "session_dir" else temp_root)
        monkeypatch.setattr(speaker_eval.shutil, "rmtree", stub)
        crypto = SessionCrypto()
        if target == "session_dir":
            # the root removal still runs and takes everything with it - and
            # the failed leg is still surfaced (round 65 PR-LOW-010)
            with pytest.raises(SpeakerEvalError) as info:
                _destroy_temporary_store(temp_root, session_dir, crypto)
            assert stub.calls == [session_dir, temp_root]
            assert not temp_root.exists()
            assert "session directory removal: RuntimeError" in str(info.value)
            assert "nothing to remove by hand" in str(info.value)
        else:
            with pytest.raises(SpeakerEvalError) as info:
                _destroy_temporary_store(temp_root, session_dir, crypto)
            assert stub.calls == [session_dir, temp_root]
            assert "temporary root removal: RuntimeError" in str(info.value)
            assert str(temp_root) in str(info.value)
            stub.real(temp_root)  # the test's own by-hand removal
        assert crypto.destroyed

    def test_an_unreadable_root_is_a_fault_not_an_absence(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        temp_root, session_dir = self._store(tmp_path)
        monkeypatch.setattr(speaker_eval, "_probe", lambda path, **kwargs: "unreadable")
        crypto = SessionCrypto()
        with pytest.raises(SpeakerEvalError, match="could not be confirmed removed") as info:
            _destroy_temporary_store(temp_root, session_dir, crypto)
        assert crypto.destroyed
        assert str(temp_root) in str(info.value)
        assert "treat the store as recoverable" in str(info.value)

    def test_a_raising_mkdtemp_still_destroys_the_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        wav = _write_wav(tmp_path / "r.wav", tone_pcm(0.2))
        labels = tmp_path / "r.txt"
        labels.write_text("0.0\t0.2\tclinician\n", encoding="utf-8")
        created = _tracking_crypto(monkeypatch)

        def no_temp(*args: object, **kwargs: object) -> str:
            raise OSError("no temp")

        monkeypatch.setattr(speaker_eval.tempfile, "mkdtemp", no_temp)
        stores_before = _temp_stores()
        with pytest.raises(OSError, match="no temp"):
            evaluate_recording(wav, labels, MockSpeechProvider(), amplitude_vad)
        assert created[0].destroyed
        assert _temp_stores() == stores_before

    def test_a_raising_token_hex_still_removes_the_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        wav = _write_wav(tmp_path / "r.wav", tone_pcm(0.2))
        labels = tmp_path / "r.txt"
        labels.write_text("0.0\t0.2\tclinician\n", encoding="utf-8")
        created = _tracking_crypto(monkeypatch)

        def no_id(_: int) -> str:
            raise RuntimeError("no entropy")

        monkeypatch.setattr(speaker_eval.secrets, "token_hex", no_id)
        stores_before = _temp_stores()
        with pytest.raises(RuntimeError, match="no entropy"):
            evaluate_recording(wav, labels, MockSpeechProvider(), amplitude_vad)
        assert created[0].destroyed
        assert _temp_stores() == stores_before

    def test_a_refused_key_unlink_is_surfaced_even_though_the_root_leg_recovered(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 65 PR-LOW-010: the later legs still run and remove the store,
        and the refused leg is still a fault - one that says nothing is left."""
        temp_root, session_dir = self._store(tmp_path)
        monkeypatch.setattr(speaker_eval, "delete_session_key", _refuse_unlink)
        crypto = SessionCrypto()
        with pytest.raises(SpeakerEvalError) as info:
            _destroy_temporary_store(temp_root, session_dir, crypto)
        assert crypto.destroyed
        assert not temp_root.exists()
        message = str(info.value)
        assert "key unlink: PermissionError" in message
        assert f"removed ({temp_root})" in message
        assert "nothing to remove by hand" in message

    def test_a_fault_before_any_root_says_so(self) -> None:
        with pytest.raises(SpeakerEvalError) as info:
            _destroy_temporary_store(None, None, _StubbornCrypto())
        assert "no temporary root was created" in str(info.value)
        assert "in-memory session key was NOT destroyed" in str(info.value)

    def test_a_recovered_removal_failure_is_recorded_under_rmtrees_real_contract(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 66 PR-LOW-012: the stand-in honours the flag the way CPython
        does - silent under ``ignore_errors=True`` (the pre-fix silence),
        raising otherwise - so this passes only when the leg calls ``rmtree``
        without the flag and the recovered failure is surfaced."""
        temp_root, session_dir = self._store(tmp_path)
        stub = _HonourFlag(session_dir)
        monkeypatch.setattr(speaker_eval.shutil, "rmtree", stub)
        crypto = SessionCrypto()
        with pytest.raises(SpeakerEvalError) as info:
            _destroy_temporary_store(temp_root, session_dir, crypto)
        assert stub.flags == [False]  # the leg passed no ignore_errors
        assert not temp_root.exists()  # the root leg (the real rmtree) removed everything
        assert crypto.destroyed
        assert "session directory removal: PermissionError" in str(info.value)
        assert f"removed ({temp_root})" in str(info.value)
        assert "nothing to remove by hand" in str(info.value)

    def test_a_never_created_session_directory_is_not_a_failure(self, tmp_path: Path) -> None:
        """Round 66 PR-LOW-012: ``session_dir`` is assigned before ``mkdir``;
        a teardown after an early setup failure must not report it."""
        temp_root = tmp_path / f"{TEMP_DIR_PREFIX}bare"
        temp_root.mkdir()
        crypto = SessionCrypto()
        _destroy_temporary_store(temp_root, temp_root / ("d" * 32), crypto)  # returns normally
        assert crypto.destroyed
        assert not temp_root.exists()

    @pytest.mark.parametrize("key_unlink_refused", [True, False])
    def test_residue_is_reported_by_path_with_the_key_state(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key_unlink_refused: bool
    ) -> None:
        temp_root, session_dir = self._store(tmp_path)
        if key_unlink_refused:
            monkeypatch.setattr(speaker_eval, "delete_session_key", _refuse_unlink)
        monkeypatch.setattr(speaker_eval.shutil, "rmtree", _keep)
        crypto = SessionCrypto()
        with pytest.raises(SpeakerEvalError) as info:
            _destroy_temporary_store(temp_root, session_dir, crypto)
        assert crypto.destroyed  # unconditional, even when the unlink was refused
        message = str(info.value)
        assert str(temp_root) in message
        if key_unlink_refused:
            assert "STILL PRESENT" in message
            assert "key unlink: PermissionError" in message
            assert (session_dir / KEY_FILENAME).exists()
        else:
            assert "ciphertext" in message
            assert "STILL PRESENT" not in message
            assert not (session_dir / KEY_FILENAME).exists()

    def test_the_key_is_created_before_any_directory_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        wav = _write_wav(tmp_path / "r.wav", tone_pcm(0.2))
        labels = tmp_path / "r.txt"
        labels.write_text("0.0\t0.2\tclinician\n", encoding="utf-8")

        class _Boom(Exception):
            pass

        def failing_crypto() -> SessionCrypto:
            raise _Boom

        monkeypatch.setattr(speaker_eval, "SessionCrypto", failing_crypto)
        stores_before = _temp_stores()
        with pytest.raises(_Boom):
            evaluate_recording(wav, labels, MockSpeechProvider(), amplitude_vad)
        assert _temp_stores() == stores_before


@windows_only
class TestEvaluateRecording:
    def _inputs(self, tmp_path: Path) -> tuple[Path, Path, bytes]:
        pcm = _two_voice_pcm()
        wav = _write_wav(tmp_path / "two-voices.wav", pcm)
        labels = tmp_path / "two-voices.txt"
        labels.write_text(TWO_VOICE_LABELS, encoding="utf-8")
        return wav, labels, pcm

    def test_after_condition_equals_the_pipelines_labels(self, tmp_path: Path) -> None:
        pytest.importorskip("numpy")
        wav, labels, pcm = self._inputs(tmp_path)
        stores_before = _temp_stores()
        result = evaluate_recording(wav, labels, MockSpeechProvider(), amplitude_vad)
        assert _temp_stores() == stores_before  # the temporary store is gone

        # Independent reference: the shipped pipeline over a store of the same PCM.
        session_dir = tmp_path / ("b" * 32)
        crypto = _make_store(session_dir, pcm)
        document = transcribe_session(session_dir, crypto, MockSpeechProvider(), amplitude_vad)
        pipeline_labels = tuple(s.speaker for s in document.transcript_segments)
        assert pipeline_labels == (SPEAKER_1, SPEAKER_2, SPEAKER_1)
        after = result.condition(AFTER)
        assert after.predicted_labels == pipeline_labels

        # The before condition is label_speakers(..., False) over the SAME segments.
        segments = [
            SpeechSegment(start_seconds=s.start_seconds, end_seconds=s.end_seconds)
            for s in document.transcript_segments
        ]
        expected_before = label_speakers(
            list(extract_segment_pcm([pcm], segments)), cepstral_mean_normalisation=False
        )
        assert result.condition(BEFORE).predicted_labels == tuple(expected_before)

        assert result.name == "two-voices"
        assert result.segment_count == 3
        assert result.unlabelled_count == 0 and result.mixed_count == 0
        assert result.label_names == ("clinician", "patient")
        assert after.metrics is not None
        assert after.metrics.accuracy_seconds == pytest.approx(1.0)
        assert after.metrics.predicted_speaker_count == 2
        assert after.metrics.true_speaker_count == 2
        assert after.role.verdict == "CORRECT"
        assert after.role.preselected_speaker == SPEAKER_1
        report = render_report([result], model_name="whisper-test")
        assert "mock0" not in report  # the provider's word text never reaches the report

    def test_temporary_store_is_destroyed_when_the_provider_raises(self, tmp_path: Path) -> None:
        pytest.importorskip("numpy")
        wav, labels, _pcm = self._inputs(tmp_path)
        stores_before = _temp_stores()
        with pytest.raises(RuntimeError, match="provider failed"):
            evaluate_recording(wav, labels, _RaisingProvider(), amplitude_vad)
        assert _temp_stores() == stores_before

    def test_residue_on_the_failure_path_supersedes_and_chains_the_provider_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 63 PR-MED-006: with the directory legs failing, the key is
        still unlinked and destroyed, the residue fault names the path, and
        the provider's exception survives as its context."""
        pytest.importorskip("numpy")
        wav, labels, _pcm = self._inputs(tmp_path)
        real_rmtree = shutil.rmtree
        monkeypatch.setattr(speaker_eval.shutil, "rmtree", _keep)
        stores_before = _temp_stores()
        try:
            with pytest.raises(SpeakerEvalError, match="ciphertext") as info:
                evaluate_recording(wav, labels, _RaisingProvider(), amplitude_vad)
            assert isinstance(info.value.__context__, RuntimeError)
            leftovers = _temp_stores() - stores_before
            assert len(leftovers) == 1
            (leftover,) = leftovers
            assert str(leftover) in str(info.value)
            assert not list(leftover.rglob(KEY_FILENAME))  # the key leg ran first
        finally:
            for path in _temp_stores() - stores_before:
                real_rmtree(path)
        assert _temp_stores() == stores_before

    @pytest.mark.parametrize("provider_fails", [False, True])
    def test_an_unreadable_probe_is_a_fault_on_both_paths(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, provider_fails: bool
    ) -> None:
        """Round 64 PR-MED-008: the store is really removed here, but the OS
        'refuses' to confirm it - that is a fault, never a clean return; on
        the provider-failure path the provider's error is its context."""
        pytest.importorskip("numpy")
        wav, labels, _pcm = self._inputs(tmp_path)
        monkeypatch.setattr(speaker_eval, "_probe", lambda path, **kwargs: "unreadable")
        stores_before = _temp_stores()
        provider = _RaisingProvider() if provider_fails else MockSpeechProvider()
        with pytest.raises(SpeakerEvalError, match="could not be confirmed removed") as info:
            evaluate_recording(wav, labels, provider, amplitude_vad)
        if provider_fails:
            assert isinstance(info.value.__context__, RuntimeError)
        else:
            assert info.value.__context__ is None
        assert _temp_stores() == stores_before  # the removal legs did run

    def test_harness_fault_when_the_wrapper_disagrees_with_the_pipeline(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pytest.importorskip("numpy")
        wav, labels, _pcm = self._inputs(tmp_path)

        def disagreeing(
            pcms: list[bytes], *, cepstral_mean_normalisation: bool = True
        ) -> list[str]:
            return [SPEAKER_2] * len(pcms)

        # Only the self-check's wrapper is patched: the pipeline inside still
        # clusters for real, so the two sites now disagree by construction.
        monkeypatch.setattr(speaker_eval, "label_speakers", disagreeing)
        stores_before = _temp_stores()
        with pytest.raises(HarnessFaultError, match="round 42"):
            evaluate_recording(wav, labels, MockSpeechProvider(), amplitude_vad)
        assert _temp_stores() == stores_before


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestFindRecordingPairs:
    def test_pairs_by_stem_and_reports_the_rest(self, tmp_path: Path) -> None:
        for name in ("a.wav", "a.txt", "b.WAV", "c.txt", "notes.md"):
            (tmp_path / name).write_bytes(b"")
        (tmp_path / "sub").mkdir()
        pairs, unpaired = find_recording_pairs(tmp_path)
        assert pairs == [(tmp_path / "a.wav", tmp_path / "a.txt")]
        assert unpaired == [tmp_path / "b.WAV", tmp_path / "c.txt"]


class _NeverBuilt:
    def __init__(self, *args: object, **kwargs: object) -> None:
        raise AssertionError("no model may be constructed on this path")


class _InertVad:
    """Stands in for ``SileroVad`` when ``evaluate_recording`` itself is faked."""

    def frame_probability(self, frame: bytes) -> float:
        return 0.0


class _InertProvider:
    def __init__(self, *args: object, **kwargs: object) -> None:
        pass


def _scored(name: str) -> RecordingResult:
    return score_document(
        name,
        _document([(0.0, 1.0, SPEAKER_1, "one"), (2.0, 3.0, SPEAKER_2, "two")]),
        _track((0.0, 1.0, "clinician"), (2.0, 3.0, "patient")),
        [SPEAKER_1, SPEAKER_2],
    )


class TestMain:
    def test_unpaired_files_are_reported_and_no_model_is_built(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "a.wav").write_bytes(b"")
        (tmp_path / "b.txt").write_text("", encoding="utf-8")
        monkeypatch.setattr(speaker_eval, "SileroVad", _NeverBuilt)
        monkeypatch.setattr(speaker_eval, "WhisperSpeechProvider", _NeverBuilt)
        assert main([str(tmp_path)]) == 1
        out = capsys.readouterr().out
        assert "[skip] a.wav: no matching a.txt label track" in out
        assert "[skip] b.txt: no matching b.wav recording" in out
        assert "no recording/label pairs" in out

    def test_offline_env_is_applied_and_asserted_before_any_model_is_built(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for key in OFFLINE_ENV:
            monkeypatch.delenv(key, raising=False)
        _write_wav(tmp_path / "a.wav", tone_pcm(0.1))
        (tmp_path / "a.txt").write_text("0.0\t0.1\tclinician\n", encoding="utf-8")

        class _Stop(Exception):
            pass

        class _Vad:
            def __init__(self) -> None:
                assert_offline_env()  # OfflineEnvError here would mean main skipped the apply
                raise _Stop

        monkeypatch.setattr(speaker_eval, "SileroVad", _Vad)
        monkeypatch.setattr(speaker_eval, "WhisperSpeechProvider", _NeverBuilt)
        with pytest.raises(_Stop):
            main([str(tmp_path)])
        for key, value in OFFLINE_ENV.items():
            assert os.environ[key] == value

    def test_a_missing_directory_is_a_usage_error(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit) as info:
            main([str(tmp_path / "nope")])
        assert info.value.code == 2

    def _pairs(self, tmp_path: Path, *stems: str) -> None:
        for stem in stems:
            (tmp_path / f"{stem}.wav").write_bytes(b"")
            (tmp_path / f"{stem}.txt").write_text("", encoding="utf-8")

    def test_one_failing_recording_does_not_lose_the_others(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 60 MED-001: a per-recording failure is reported, the run
        continues, the table still prints, and the exit status says so.
        Round 62 PR-MED-001: an unaudited exception's TEXT never reaches
        stdout (type only); this module's own exceptions may echo theirs."""
        sentinel = "zebrafruit"
        self._pairs(tmp_path, "a", "b", "c")

        def evaluate(wav_path: Path, *args: object, **kwargs: object) -> RecordingResult:
            if wav_path.stem == "a":
                raise RuntimeError(f"model blew up on {sentinel}")
            if wav_path.stem == "c":
                raise SpeakerEvalError("temporary store not fully removed: x")
            return _scored(wav_path.stem)

        monkeypatch.setattr(speaker_eval, "SileroVad", _InertVad)
        monkeypatch.setattr(speaker_eval, "WhisperSpeechProvider", _InertProvider)
        monkeypatch.setattr(speaker_eval, "build_speaker_embedder", _no_speaker_model)
        monkeypatch.setattr(speaker_eval, "evaluate_recording", evaluate)
        assert main([str(tmp_path)]) == 1
        out = capsys.readouterr().out
        assert "[error] a.wav: RuntimeError\n" in out
        assert sentinel not in out
        assert "[error] c.wav: temporary store not fully removed: x" in out
        assert "| b | 2 | 0 | 0 | clinician, patient |" in out
        assert "### Aggregate per condition" in out

    def test_unicode_names_and_labels_survive_a_code_page_stdout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 62 PR-MED-004: a Unicode stem or role label must never abort
        the run on a redirected, code-page-encoded stdout."""
        stem = "recō"  # 'o' with macron: outside cp1252
        label = "patiēnt"  # 'e' with macron: likewise
        self._pairs(tmp_path, stem)
        scored = score_document(
            stem,
            _document([(0.0, 1.0, SPEAKER_1, "one"), (2.0, 3.0, SPEAKER_2, "two")]),
            _track((0.0, 1.0, "clinician"), (2.0, 3.0, label)),
            [SPEAKER_1, SPEAKER_2],
        )
        sink = io.BytesIO()
        monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(sink, encoding="cp1252"))
        monkeypatch.setattr(speaker_eval, "SileroVad", _InertVad)
        monkeypatch.setattr(speaker_eval, "WhisperSpeechProvider", _InertProvider)
        monkeypatch.setattr(speaker_eval, "evaluate_recording", lambda *args, **kwargs: scored)
        assert main([str(tmp_path)]) == 0
        sys.stdout.flush()
        text = sink.getvalue().decode("utf-8")
        assert f"[run ] {stem}.wav" in text
        assert f"| {stem} | 2 | 0 | 0 | clinician, {label} |" in text

    def test_a_fully_scored_run_exits_zero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._pairs(tmp_path, "a", "b")

        def evaluate(wav_path: Path, *args: object, **kwargs: object) -> RecordingResult:
            return _scored(wav_path.stem)

        monkeypatch.setattr(speaker_eval, "SileroVad", _InertVad)
        monkeypatch.setattr(speaker_eval, "WhisperSpeechProvider", _InertProvider)
        monkeypatch.setattr(speaker_eval, "build_speaker_embedder", _no_speaker_model)
        monkeypatch.setattr(speaker_eval, "evaluate_recording", evaluate)
        assert main([str(tmp_path)]) == 0
        out = capsys.readouterr().out
        assert "[error]" not in out
        assert "| a | 2 |" in out and "| b | 2 |" in out
        # Two pairs and no --enrolment: the leave-one-out fallback wanted the
        # speaker model, which is absent here — said visibly, never an error.
        assert f"[skip] {ENROLLED} condition:" in out


# ---------------------------------------------------------------------------
# the enrolled condition (practitioner-profile plan Task 2.4)
# ---------------------------------------------------------------------------


def _no_speaker_model(*args: object, **kwargs: object) -> object:
    raise SpeakerModelError("speaker model not found - run scripts/setup-models.py")


class _FrequencyEmbedder:
    """An ML-free ``SpeakerEmbedder`` for the enrolled condition: the unit
    vector e1 for a low-pitched tone (zero-crossing rate under 1000/s), e2
    otherwise — so a 220 Hz voice matches an e1 profile and a 2600 Hz voice
    does not, deterministically, with no model file."""

    @property
    def model_id(self) -> str:
        return "mock-frequency-v1"

    @property
    def model_sha256(self) -> str:
        return ""

    @property
    def embedding_dim(self) -> int:
        return 2

    def embed(self, pcm16: bytes) -> object:
        import numpy as np

        samples = struct.unpack(f"<{len(pcm16) // 2}h", pcm16)
        pairs = zip(samples, samples[1:], strict=False)
        crossings = sum(1 for a, b in pairs if (a < 0) != (b < 0))
        rate = crossings / (len(samples) / SAMPLE_RATE)
        return np.asarray([1.0, 0.0] if rate < 1000 else [0.0, 1.0], dtype=np.float32)


def _build_frequency_embedder(*args: object, **kwargs: object) -> _FrequencyEmbedder:
    return _FrequencyEmbedder()


def _enrolment(frequency: float = 220.0) -> speaker_eval.EnrolmentInputs:
    return speaker_eval.enrolment_inputs(
        tone_pcm(2.0, frequency=frequency), _FrequencyEmbedder(), amplitude_vad
    )


def _attributed(
    rows: Sequence[tuple[float, float, str, str]], enrolled: str | None, sim: float
) -> TranscriptDocument:
    fields = (
        {}
        if enrolled is None
        else {
            "enrolled_speaker": enrolled,
            "enrolment_similarity": sim,
            "speaker_model_id": "mock-frequency-v1",
        }
    )
    return _document(rows).model_copy(update=fields)


class TestEnrolmentInputs:
    def test_the_profile_records_the_embedder_and_lives_in_memory_only(self) -> None:
        pytest.importorskip("numpy")
        inputs = _enrolment()
        profile = inputs.profile
        assert inputs.embedder.model_id == profile.model_id == "mock-frequency-v1"
        assert profile.model_sha256 == ""
        assert profile.embedding == (1.0, 0.0)
        assert profile.embedding_dim == 2
        assert profile.enrolment_speech_seconds > 0
        assert profile.device_name == speaker_eval.HARNESS_DEVICE_NAME
        assert profile.consent.consent_text_version == speaker_eval.HARNESS_CONSENT_VERSION
        assert profile.consent.learning_opt_in is False
        # The inputs render without the vector (repr=False on both fields).
        rendered = repr(inputs)
        assert "embedding" not in rendered and "1.0" not in rendered
        # No profile store anywhere in the harness: nothing can be written.
        assert "save_profile" not in speaker_eval.__dict__
        assert "delete_profile" not in speaker_eval.__dict__
        assert "default_profile_root" not in speaker_eval.__dict__

    def test_audio_without_speech_is_an_enrolment_error(self) -> None:
        pytest.importorskip("numpy")
        from scribe_desktop.enrolment import EnrolmentError

        with pytest.raises(EnrolmentError):
            speaker_eval.enrolment_inputs(silence_pcm(2.0), _FrequencyEmbedder(), amplitude_vad)

    def test_clinician_pcm_takes_clinician_spans_in_order_clipped_to_the_audio(self) -> None:
        pcm = bytes(range(256)) * 250  # 64 000 bytes = 2.0 s
        track = _track((0.0, 0.5, "clinician"), (0.5, 1.0, "patient"), (1.5, 3.0, "clinician"))
        expected = pcm[: 8000 * 2] + pcm[24000 * 2 :]
        assert speaker_eval.clinician_pcm(pcm, track) == expected
        overlapping = _track((0.0, 1.0, "clinician"), (0.0, 1.0, "patient"))
        assert speaker_eval.clinician_pcm(pcm, overlapping) == pcm[:32000]


class TestAutoConfirmOutcome:
    def _rows(self) -> list[tuple[float, float, str, str]]:
        return [(0.0, 2.0, SPEAKER_1, "how is it"), (2.0, 5.0, SPEAKER_2, "sore")]

    def _truths(self) -> list[SegmentTruth]:
        return _truths((0.0, 2.0, "clinician"), (2.0, 5.0, "patient"))

    def test_correct_when_the_confirmed_cluster_is_mostly_the_clinician(self) -> None:
        document = _attributed(self._rows(), SPEAKER_1, 0.8)
        outcome = speaker_eval.auto_confirm_outcome(
            document, [SPEAKER_1, SPEAKER_2], self._truths()
        )
        assert outcome.verdict == "CORRECT"
        assert outcome.preselected_speaker == SPEAKER_1
        assert outcome.margin == 0.8  # the similarity, per the RoleOutcome docstring

    def test_wrong_when_it_is_the_patient(self) -> None:
        document = _attributed(self._rows(), SPEAKER_2, 0.55)
        outcome = speaker_eval.auto_confirm_outcome(
            document, [SPEAKER_1, SPEAKER_2], self._truths()
        )
        assert outcome.verdict == "WRONG"
        assert outcome.majority_true_label == "patient"

    def test_none_without_attribution(self) -> None:
        document = _attributed(self._rows(), None, 0.0)
        outcome = speaker_eval.auto_confirm_outcome(
            document, [SPEAKER_1, SPEAKER_2], self._truths()
        )
        assert outcome.verdict == "NONE"
        assert outcome.preselected_speaker is None


class TestScoreDocumentEnrolled:
    def _inputs(self) -> tuple[TranscriptDocument, LabelTrack]:
        rows = [(0.0, 2.0, SPEAKER_1, "how is it"), (2.0, 5.0, SPEAKER_2, "sore")]
        return _document(rows), _track((0.0, 2.0, "clinician"), (2.0, 5.0, "patient"))

    def test_third_condition_with_its_own_verdicts(self) -> None:
        document, track = self._inputs()
        enrolled = _attributed(
            [(0.0, 2.0, SPEAKER_1, "how is it"), (2.0, 5.0, SPEAKER_2, "sore")], SPEAKER_1, 0.8
        )
        result = score_document(
            "rec", document, track, [SPEAKER_1, SPEAKER_2], enrolled_document=enrolled
        )
        assert [c.condition for c in result.conditions] == [BEFORE, AFTER, ENROLLED]
        assert result.has_condition(ENROLLED)
        cond = result.condition(ENROLLED)
        assert cond.predicted_labels == (SPEAKER_1, SPEAKER_2)
        assert cond.metrics is not None and cond.metrics.accuracy_seconds == pytest.approx(1.0)
        assert cond.auto_confirm is not None and cond.auto_confirm.verdict == "CORRECT"
        assert cond.enrolment_similarity == 0.8
        assert result.condition(AFTER).auto_confirm is None
        assert result.condition(AFTER).enrolment_similarity is None
        report = render_report([result], model_name="m")
        assert f"| {ENROLLED} | 2/2 | 1.000 | 1.000 (2/2) |" in report
        assert "| CORRECT | speaker_1 | 0.800 |" in report
        assert f"| {ENROLLED} | 1 | 1 | 0 | 1.000 | 1.000 | 1 | 0 | 0 | 1 | 0 | 0 |" in report
        assert f"| {AFTER} | 1 | 1 | 0 | 1.000 | 1.000 | 1 | 0 | 0 | - | - | - |" in report

    def test_all_speaker_1_is_scored_as_all_matched_not_merged(self) -> None:
        """PR-MED-014: the legacy conditions report all-speaker_1 as merged;
        the enrolled condition scores it (every segment matched the profile)."""
        document, track = self._inputs()
        enrolled = _attributed(
            [(0.0, 2.0, SPEAKER_1, "how is it"), (2.0, 5.0, SPEAKER_1, "sore")], SPEAKER_1, 0.9
        )
        result = score_document(
            "rec", document, track, [SPEAKER_1, SPEAKER_1], enrolled_document=enrolled
        )
        assert result.condition(BEFORE).merged
        assert result.condition(BEFORE).metrics is None
        cond = result.condition(ENROLLED)
        assert not cond.merged
        assert cond.metrics is not None
        assert cond.metrics.predicted_speaker_count == 1
        # ``cluster_metrics`` is label-name agnostic: the ONE predicted cluster
        # maps to whichever true role it covers longest (the patient's 3 s of
        # 5), so the accuracy reads 0.6 — the false-positive match is exposed by
        # the 1/2 cluster count and the auto-confirm verdict, not by the mapping.
        assert cond.metrics.mapping == ((SPEAKER_1, "patient"),)
        assert cond.metrics.accuracy_seconds == pytest.approx(3.0 / 5.0)
        assert cond.auto_confirm is not None and cond.auto_confirm.verdict == "WRONG"
        report = render_report([result], model_name="m")
        assert f"| {ENROLLED} | 1/2 |" in report

    def test_absent_condition_is_absent_from_the_report(self) -> None:
        document, track = self._inputs()
        result = score_document("rec", document, track, [SPEAKER_1, SPEAKER_2])
        assert not result.has_condition(ENROLLED)
        with pytest.raises(KeyError):
            result.condition(ENROLLED)
        report = render_report([result], model_name="m")
        assert f"| {ENROLLED} |" not in report
        assert f"| {AFTER} | 1 | 1 | 0 | 1.000 | 1.000 | 1 | 0 | 0 | - | - | - |" in report

    def test_enrolled_label_count_must_match(self) -> None:
        document, track = self._inputs()
        enrolled = _document([(0.0, 2.0, SPEAKER_1, "one")])
        with pytest.raises(ValueError, match="enrolled-condition"):
            score_document(
                "rec", document, track, [SPEAKER_1, SPEAKER_2], enrolled_document=enrolled
            )

    def test_enrolled_report_rows_carry_no_transcript_text(self) -> None:
        sentinel = "zebrafruit"
        rows = [(0.0, 2.0, SPEAKER_1, f"the {sentinel}"), (2.0, 5.0, SPEAKER_2, sentinel)]
        document = _document(rows)
        enrolled = _attributed(rows, SPEAKER_1, 0.7)
        track = _track((0.0, 2.0, "clinician"), (2.0, 5.0, "patient"))
        result = score_document(
            "rec", document, track, [SPEAKER_1, SPEAKER_2], enrolled_document=enrolled
        )
        assert sentinel not in render_report([result], model_name="m")
        assert sentinel not in repr(result)


@windows_only
class TestEvaluateRecordingEnrolled:
    def _inputs(self, tmp_path: Path) -> tuple[Path, Path]:
        wav = _write_wav(tmp_path / "two-voices.wav", _two_voice_pcm())
        labels = tmp_path / "two-voices.txt"
        labels.write_text(TWO_VOICE_LABELS, encoding="utf-8")
        return wav, labels

    def test_enrolled_condition_runs_the_shipped_pipeline_with_the_profile(
        self, tmp_path: Path
    ) -> None:
        pytest.importorskip("numpy")
        wav, labels = self._inputs(tmp_path)
        stores_before = _temp_stores()
        counting = _CountingProvider()
        result = evaluate_recording(wav, labels, counting, amplitude_vad, enrolment=_enrolment())
        assert _temp_stores() == stores_before
        after = result.condition(AFTER)
        assert after.predicted_labels == (SPEAKER_1, SPEAKER_2, SPEAKER_1)  # unchanged
        enrolled = result.condition(ENROLLED)
        assert enrolled.predicted_labels == (SPEAKER_1, SPEAKER_2, SPEAKER_1)
        assert enrolled.enrolment_similarity == pytest.approx(1.0)
        assert enrolled.auto_confirm is not None
        assert enrolled.auto_confirm.verdict == "CORRECT"
        assert enrolled.auto_confirm.preselected_speaker == SPEAKER_1
        assert enrolled.metrics is not None and enrolled.metrics.accuracy_seconds == 1.0
        # One window in this fixture, transcribed ONCE: the enrolled pass replayed it.
        assert counting.calls == 1

    def test_a_profile_of_the_other_voice_confirms_the_patient_visibly(
        self, tmp_path: Path
    ) -> None:
        pytest.importorskip("numpy")
        wav, labels = self._inputs(tmp_path)
        result = evaluate_recording(
            wav, labels, MockSpeechProvider(), amplitude_vad, enrolment=_enrolment(2600.0)
        )
        enrolled = result.condition(ENROLLED)
        # The 2600 Hz segment matched the (wrong) profile and is speaker_1;
        # the two 220 Hz segments are the remainder, split by D13's 2-means
        # into speaker_2 / speaker_3 (not byte-identical slices — the D-S1
        # residue, exactly as the no-profile path splits two segments today).
        assert enrolled.predicted_labels == (SPEAKER_2, SPEAKER_1, SPEAKER_3)
        assert enrolled.auto_confirm is not None
        assert enrolled.auto_confirm.verdict == "WRONG"
        assert enrolled.auto_confirm.preselected_speaker == SPEAKER_1

    def test_a_failing_enrolled_pass_still_tears_the_store_down(self, tmp_path: Path) -> None:
        pytest.importorskip("numpy")
        wav, labels = self._inputs(tmp_path)

        class _Exploding(_FrequencyEmbedder):
            def embed(self, pcm16: bytes) -> object:
                raise RuntimeError("embedder failed")

        inputs = _enrolment()
        broken = speaker_eval.EnrolmentInputs(embedder=_Exploding(), profile=inputs.profile)
        stores_before = _temp_stores()
        with pytest.raises(RuntimeError, match="embedder failed"):
            evaluate_recording(wav, labels, MockSpeechProvider(), amplitude_vad, enrolment=broken)
        assert _temp_stores() == stores_before

    def test_a_second_pass_that_segments_differently_is_a_harness_fault(
        self, tmp_path: Path
    ) -> None:
        pytest.importorskip("numpy")
        wav, labels = self._inputs(tmp_path)
        passes = {"frames": 0}
        first_pass_frames = len(_two_voice_pcm()) // FRAME_BYTES + 8

        def drifting_vad(frame: bytes) -> float:
            passes["frames"] += 1
            if passes["frames"] > first_pass_frames:
                return 0.02  # the second pass hears silence: different segments
            return amplitude_vad(frame)

        stores_before = _temp_stores()
        with pytest.raises(HarnessFaultError, match="segmented the same store differently"):
            evaluate_recording(
                wav, labels, MockSpeechProvider(), drifting_vad, enrolment=_enrolment()
            )
        assert _temp_stores() == stores_before


class _CountingProvider(MockSpeechProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        self.calls += 1
        return super().transcribe_segment(pcm, sample_rate)


class _AmplitudeVad:
    """Stands in for ``SileroVad`` where ``main`` itself enrols: the harness
    hands the run's VAD to ``enrol``, so the stub must hear the tone
    fixtures as speech (the inert stub hears nothing and would refuse them)."""

    def frame_probability(self, frame: bytes) -> float:
        return amplitude_vad(frame)


class TestMainEnrolled:
    def _pair(self, tmp_path: Path, stem: str, pcm: bytes, labels: str) -> None:
        _write_wav(tmp_path / f"{stem}.wav", pcm)
        (tmp_path / f"{stem}.txt").write_text(labels, encoding="utf-8")

    def _capture(self, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
        seen: dict[str, object] = {}

        def evaluate(wav_path: Path, *args: object, **kwargs: object) -> RecordingResult:
            seen[wav_path.stem] = kwargs.get("enrolment")
            return _scored(wav_path.stem)

        monkeypatch.setattr(speaker_eval, "SileroVad", _AmplitudeVad)
        monkeypatch.setattr(speaker_eval, "WhisperSpeechProvider", _InertProvider)
        monkeypatch.setattr(speaker_eval, "evaluate_recording", evaluate)
        return seen

    def test_enrolment_wav_builds_one_in_memory_profile_for_every_recording(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pytest.importorskip("numpy")
        self._pair(tmp_path, "a", tone_pcm(0.1), "0.0\t0.1\tclinician\n")
        seen = self._capture(monkeypatch)
        monkeypatch.setattr(speaker_eval, "build_speaker_embedder", _build_frequency_embedder)
        (tmp_path / "enrol").mkdir()
        me = _write_wav(tmp_path / "enrol" / "me.wav", tone_pcm(2.0, frequency=220.0))
        assert main([str(tmp_path), "--enrolment", str(me)]) == 0
        enrolment = seen["a"]
        assert isinstance(enrolment, speaker_eval.EnrolmentInputs)
        assert enrolment.profile.embedding == (1.0, 0.0)
        assert "[info] no --enrolment" not in capsys.readouterr().out

    def test_enrolment_wav_is_refused_like_a_recording(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._pair(tmp_path, "a", tone_pcm(0.1), "0.0\t0.1\tclinician\n")
        seen = self._capture(monkeypatch)
        monkeypatch.setattr(speaker_eval, "build_speaker_embedder", _build_frequency_embedder)
        (tmp_path / "enrol").mkdir()
        stereo = _write_wav(tmp_path / "enrol" / "me.wav", tone_pcm(0.5) * 2, channels=2)
        assert main([str(tmp_path), "--enrolment", str(stereo)]) == 1
        assert "[error] --enrolment me.wav:" in capsys.readouterr().out
        assert seen == {}  # nothing was evaluated

    def test_enrolment_wav_without_the_speaker_model_is_an_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._pair(tmp_path, "a", tone_pcm(0.1), "0.0\t0.1\tclinician\n")
        seen = self._capture(monkeypatch)
        monkeypatch.setattr(speaker_eval, "build_speaker_embedder", _no_speaker_model)
        (tmp_path / "enrol").mkdir()
        me = _write_wav(tmp_path / "enrol" / "me.wav", tone_pcm(2.0))
        assert main([str(tmp_path), "--enrolment", str(me)]) == 1
        assert "[error] --enrolment: speaker model not found" in capsys.readouterr().out
        assert seen == {}

    def test_leave_one_out_enrols_each_recording_from_the_others(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pytest.importorskip("numpy")
        # a's clinician is the LOW voice, b's clinician is the HIGH voice.
        self._pair(tmp_path, "a", tone_pcm(2.0, frequency=220.0), "0.0\t2.0\tclinician\n")
        self._pair(tmp_path, "b", tone_pcm(2.0, frequency=2600.0), "0.0\t2.0\tclinician\n")
        seen = self._capture(monkeypatch)
        monkeypatch.setattr(speaker_eval, "build_speaker_embedder", _build_frequency_embedder)
        assert main([str(tmp_path)]) == 0
        a, b = seen["a"], seen["b"]
        assert isinstance(a, speaker_eval.EnrolmentInputs)
        assert isinstance(b, speaker_eval.EnrolmentInputs)
        assert a.profile.embedding == (0.0, 1.0)  # enrolled from b's clinician spans
        assert b.profile.embedding == (1.0, 0.0)  # enrolled from a's clinician spans
        assert "[info] no --enrolment given" in capsys.readouterr().out

    def test_leave_one_out_needs_two_recordings(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._pair(tmp_path, "a", tone_pcm(0.1), "0.0\t0.1\tclinician\n")
        seen = self._capture(monkeypatch)
        monkeypatch.setattr(speaker_eval, "build_speaker_embedder", _no_speaker_model)
        assert main([str(tmp_path)]) == 0
        assert seen == {"a": None}
        assert f"[skip] {ENROLLED} condition: give --enrolment" in capsys.readouterr().out

    def test_an_undecodable_label_track_does_not_abort_the_leave_one_out_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Peer round 19 PR-REG-003: pool preparation runs before the
        per-recording error boundary; a label file that is not UTF-8 raises
        ``UnicodeDecodeError`` (not an ``OSError``) and used to abort the
        whole run. Now the pool skips it, the evaluation reports that pair
        once by TYPE, the other recording is scored and the exit is non-zero."""
        pytest.importorskip("numpy")
        self._pair(tmp_path, "a", tone_pcm(2.0, frequency=220.0), "0.0\t2.0\tclinician\n")
        _write_wav(tmp_path / "b.wav", tone_pcm(2.0, frequency=2600.0))
        (tmp_path / "b.txt").write_bytes(b"0.0\t2.0\tclinician\n\xff\xfe")  # not UTF-8
        seen: dict[str, object] = {}

        def evaluate(
            wav_path: Path, labels_path: Path, *args: object, **kwargs: object
        ) -> RecordingResult:
            labels_path.read_text(encoding="utf-8-sig")  # the real path's first read
            seen[wav_path.stem] = kwargs.get("enrolment")
            return _scored(wav_path.stem)

        monkeypatch.setattr(speaker_eval, "SileroVad", _AmplitudeVad)
        monkeypatch.setattr(speaker_eval, "WhisperSpeechProvider", _InertProvider)
        monkeypatch.setattr(speaker_eval, "evaluate_recording", evaluate)
        monkeypatch.setattr(speaker_eval, "build_speaker_embedder", _build_frequency_embedder)
        assert main([str(tmp_path)]) == 1
        out = capsys.readouterr().out
        assert "[info] no --enrolment given" in out
        assert "[error] b.wav: UnicodeDecodeError\n" in out  # type only
        assert "\\xff" not in out and "invalid" not in out
        assert "| a | 2 |" in out  # the valid recording was still scored
        assert seen == {"a": None}  # b never contributed a pool, so a had none
        assert f"[skip] a.wav: {ENROLLED} condition not measured" in out

    def test_an_unexpected_enrolment_failure_is_reported_by_type_and_the_run_continues(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """PR-REG-003, the per-recording enrolment step: a failure that is not
        an ``EnrolmentError`` used to escape the loop; now it is isolated like
        an evaluation failure — the recording is still measured, the type
        alone is printed, and the exit status says an error happened."""
        pytest.importorskip("numpy")
        sentinel = "zebrafruit"
        self._pair(tmp_path, "a", tone_pcm(2.0, frequency=220.0), "0.0\t2.0\tclinician\n")
        self._pair(tmp_path, "b", tone_pcm(2.0, frequency=2600.0), "0.0\t2.0\tclinician\n")
        seen = self._capture(monkeypatch)

        class _Exploding(_FrequencyEmbedder):
            def embed(self, pcm16: bytes) -> object:
                raise RuntimeError(f"embedder failed on {sentinel}")

        monkeypatch.setattr(speaker_eval, "build_speaker_embedder", lambda *a, **k: _Exploding())
        assert main([str(tmp_path)]) == 1
        out = capsys.readouterr().out
        assert f"[error] a.wav: {ENROLLED} condition failed - RuntimeError\n" in out
        assert f"[error] b.wav: {ENROLLED} condition failed - RuntimeError\n" in out
        assert sentinel not in out
        assert "| a | 2 |" in out and "| b | 2 |" in out  # both still measured
        assert seen == {"a": None, "b": None}

    def test_an_oversized_label_timestamp_does_not_abort_the_leave_one_out_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Peer round 20 PR-REG-004: the parser admits any finite timestamp,
        so ``1e305`` seconds reads fine, but its sample index overflows
        (``int(inf)``) in ``clinician_pcm`` — which used to run outside the
        pool's guard and abort the run. The evaluation never converts these
        timestamps, so it cannot report this pair itself: the pool builder
        reports it once, by type, the run continues, both recordings are
        still measured, and the exit is non-zero."""
        pytest.importorskip("numpy")
        self._pair(tmp_path, "a", tone_pcm(2.0, frequency=220.0), "0.0\t2.0\tclinician\n")
        self._pair(tmp_path, "b", tone_pcm(2.0, frequency=2600.0), "0.0\t1e305\tclinician\n")
        seen = self._capture(monkeypatch)
        monkeypatch.setattr(speaker_eval, "build_speaker_embedder", _build_frequency_embedder)
        assert main([str(tmp_path)]) == 1
        out = capsys.readouterr().out
        assert f"[error] b.wav: {ENROLLED} pool preparation failed - OverflowError\n" in out
        assert "infinity" not in out  # type only, never the message
        assert "| a | 2 |" in out and "| b | 2 |" in out  # both still measured
        assert seen["a"] is None  # b contributed no pool, so a had none
        assert f"[skip] a.wav: {ENROLLED} condition not measured" in out
        assert isinstance(seen["b"], speaker_eval.EnrolmentInputs)  # enrolled from a's spans

    def test_leave_one_out_with_no_usable_pool_skips_that_recording_only(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pytest.importorskip("numpy")
        # b's "clinician" span is silence: a's pool holds no speech.
        self._pair(tmp_path, "a", tone_pcm(2.0, frequency=220.0), "0.0\t2.0\tclinician\n")
        self._pair(tmp_path, "b", silence_pcm(2.0), "0.0\t2.0\tclinician\n")
        seen = self._capture(monkeypatch)
        monkeypatch.setattr(speaker_eval, "build_speaker_embedder", _build_frequency_embedder)
        assert main([str(tmp_path)]) == 0
        assert seen["a"] is None
        assert isinstance(seen["b"], speaker_eval.EnrolmentInputs)
        assert f"[skip] a.wav: {ENROLLED} condition not measured" in capsys.readouterr().out
