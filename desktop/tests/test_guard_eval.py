"""Invented-text-guard plan Task 1.5 (D7, C5, C12): the transcription-guard
measurement (``guard_eval`` + ``scripts/measure-transcription-guard.py``).

The run legs go through the REAL ``transcribe_in_temporary_store`` (a
memory-keyed temporary store, no DPAPI) over generated tones with an
amplitude VAD and a fake speech provider carrying decode numbers — no real
model and no SAPI voice; the models root is the conftest's empty pin. No
clinical content: invented words and a marker only."""

from __future__ import annotations

import ast
import importlib.util
import json
import math
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from conftest import use_channel
from scribe_desktop import guard_eval, install_layout
from scribe_desktop.benchmark import apply_offline_env
from scribe_desktop.guard_eval import (
    CASE_KINDS,
    DEFAULT_CANDIDATES,
    PACKING_UTTERANCE,
    PRIMERS,
    SHORT_UTTERANCES,
    Candidate,
    Case,
    CaseAudio,
    GuardEvalError,
    SegmentRow,
    alone,
    bed_cases,
    chord_bed,
    noise_bed,
    packed,
    parse_candidate,
    render_report,
    run_case,
    run_cases,
    segment_rows,
    short_cases,
    silence_bed,
    spoken,
    synthetic_set,
    vowel_bed,
)
from scribe_desktop.note import content_tokens
from scribe_desktop.speaker_eval import TEMP_DIR_PREFIX, SpeakerEvalError, WavFormatError
from scribe_desktop.speech import BYTES_PER_SAMPLE, SAMPLE_RATE, TranscribedWord
from scribe_desktop.transcription import (
    CLINICAL_INITIAL_PROMPT,
    TRANSCRIBE_WINDOW_MAX_GAP_SECONDS,
    GuardFeatures,
    TranscriptDocument,
)
from scribe_desktop.validation import find_encounters
from scribe_desktop.validation_set import TURN_RMS, write_wav

REPO = Path(__file__).resolve().parents[2]
_MARKER = "SECRETWORDMARKER"
_FULL = 32767.0


@pytest.fixture(autouse=True)
def _offline_env() -> None:
    apply_offline_env()


@pytest.fixture(autouse=True)
def _private_temp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The temporary stores land in this test's own folder (the harness's
    ``_private_temp``)."""
    folder = tmp_path / "system-temp"
    folder.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(folder))
    return folder


def _rms(samples: list[float]) -> float:
    return math.sqrt(math.fsum(value * value for value in samples) / len(samples))


def _tone(seconds: float, frequency: float = 440.0, amplitude: float = 0.3) -> bytes:
    count = round(seconds * SAMPLE_RATE)
    scale = amplitude * _FULL
    return struct.pack(
        f"<{count}h",
        *(round(scale * math.sin(2 * math.pi * frequency * i / SAMPLE_RATE)) for i in range(count)),
    )


def _tone_floats(seconds: float, amplitude: float = 5000.0) -> list[float]:
    count = round(seconds * SAMPLE_RATE)
    return [amplitude * math.sin(2 * math.pi * 330.0 * i / SAMPLE_RATE) for i in range(count)]


def amplitude_vad(frame: bytes) -> float:
    samples = struct.unpack(f"<{len(frame) // 2}h", frame)
    return 0.95 if max(abs(s) for s in samples) > 1000 else 0.02


def _fake_synthesize(text: str, voice: int, rate: int) -> bytes:
    # A tone stands in for SAPI speech: 0.8 s, never the text.
    return _tone(0.8, 300.0 + 20 * voice + rate)


# ---------------------------------------------------------------------------
# The beds and the case shapes
# ---------------------------------------------------------------------------


class TestBeds:
    def test_silence_is_all_zero_at_the_pipeline_rate(self) -> None:
        bed = silence_bed(1.5)
        assert len(bed) == 24_000
        assert set(bed) == {0.0}

    def test_noise_has_its_level_and_a_fixed_seed(self) -> None:
        bed = noise_bed(2.0, -40)
        assert len(bed) == 32_000
        assert _rms(bed) == pytest.approx(_FULL * 0.01, rel=1e-9)  # -40 dBFS
        assert noise_bed(2.0, -40) == bed
        assert noise_bed(2.0, -40, seed=7) != bed

    @pytest.mark.parametrize(("level", "expected"), [(-20, _FULL * 0.1), (-30, _FULL * 10**-1.5)])
    def test_the_music_beds_have_their_levels(self, level: int, expected: float) -> None:
        for bed in (chord_bed(1.0, level), vowel_bed(1.0, level)):
            assert len(bed) == 16_000
            assert _rms(bed) == pytest.approx(expected, rel=1e-9)
            assert max(abs(value) for value in bed) < 0.95 * _FULL  # no clipping

    def test_the_chord_bed_bursts_every_second(self) -> None:
        bed = chord_bed(2.0, -20)
        # The burst doubles the envelope (~1.18 average over 1.00-1.12 s
        # against ~0.73 over 1.20-1.32 s, where the slow envelope is higher).
        burst = _rms(bed[1 * SAMPLE_RATE : round(1.12 * SAMPLE_RATE)])
        after = _rms(bed[round(1.2 * SAMPLE_RATE) : round(1.32 * SAMPLE_RATE)])
        assert burst > 1.4 * after

    def test_alone_pads_with_the_sets_lead_and_tail(self) -> None:
        audio = alone(_tone_floats(1.0))
        assert len(audio.pcm) == (8_000 + 16_000 + 8_000) * BYTES_PER_SAMPLE
        assert audio.speech_spans == ()

    def test_packed_puts_the_bed_one_second_after_the_utterance(self) -> None:
        audio = packed(_tone(1.0), _tone_floats(2.0))
        # lead 0.5 + utterance 1.0 + gap 1.0 + bed 2.0 + tail 0.5 = 5.0 s.
        assert len(audio.pcm) == 80_000 * BYTES_PER_SAMPLE
        assert audio.speech_spans == ((0.5, 1.5),)
        assert guard_eval.PACK_GAP_SECONDS == 1.0
        assert guard_eval.PACK_GAP_SECONDS < TRANSCRIBE_WINDOW_MAX_GAP_SECONDS

    def test_the_utterance_is_levelled_like_a_set_turn(self) -> None:
        audio = spoken(_tone(0.8, amplitude=0.6))
        samples = struct.unpack(f"<{len(audio.pcm) // 2}h", audio.pcm)
        turn = [float(v) for v in samples[8_000 : 8_000 + 12_800]]
        assert _rms(turn) == pytest.approx(TURN_RMS, rel=1e-3)
        assert audio.speech_spans == ((0.5, 1.3),)


class TestCases:
    def test_the_bed_cases_and_their_ids(self) -> None:
        cases = bed_cases(_fake_synthesize)
        assert [case.case_id for case in cases] == [
            "silence-alone",
            "silence-packed",
            "noise-50-alone",
            "noise-50-packed",
            "noise-40-alone",
            "noise-40-packed",
            "noise-30-alone",
            "noise-30-packed",
            "chord-20-alone",
            "chord-20-packed",
            "vowel-20-alone",
            "vowel-20-packed",
            "chord-30-alone",
            "chord-30-packed",
            "vowel-30-alone",
            "vowel-30-packed",
        ]
        assert [case.kind for case in cases[:4]] == ["silence", "silence", "noise", "noise"]

    def test_a_packed_case_speaks_the_packing_utterance_in_voice_0_at_rate_0(self) -> None:
        heard: list[tuple[str, int, int]] = []

        def synthesize(text: str, voice: int, rate: int) -> bytes:
            heard.append((text, voice, rate))
            return _tone(0.8)

        cases = {case.case_id: case for case in bed_cases(synthesize)}
        assert heard == []  # nothing is synthesised before a case runs
        cases["chord-20-packed"].load()
        assert heard == [(PACKING_UTTERANCE, 0, 0)]
        cases["chord-20-alone"].load()
        assert len(heard) == 1

    def test_short_cases_cover_every_utterance_rate_and_voice(self) -> None:
        cases = short_cases(_fake_synthesize, 2)
        assert len(cases) == 6 * 3 * 2
        assert cases[0].case_id == "short-1-r0-v0"
        assert cases[1].case_id == "short-1-r0-v1"
        assert cases[2].case_id == "short-1-r5-v0"
        assert cases[-1].case_id == "short-6-r10-v1"
        assert {case.kind for case in cases} == {"short"}
        assert len(short_cases(_fake_synthesize, 7)) == 6 * 3 * 3  # at most three voices
        assert len(SHORT_UTTERANCES) == 6

    def test_one_short_line_echoes_the_primer(self) -> None:
        # The echo signal's false-positive path is measured on real speech:
        # exactly one fixed line shares a 3-token run with the primer.
        from scribe_desktop.transcription import _primer_echo

        echoes = [_primer_echo(text, CLINICAL_INITIAL_PROMPT) for text in SHORT_UTTERANCES]
        assert echoes == [False, False, False, False, False, True]

    def test_a_short_case_speaks_its_utterance_at_its_rate(self) -> None:
        heard: list[tuple[str, int, int]] = []

        def synthesize(text: str, voice: int, rate: int) -> bytes:
            heard.append((text, voice, rate))
            return _tone(0.8)

        (case,) = [c for c in short_cases(synthesize, 3) if c.case_id == "short-3-r10-v2"]
        case.load()
        assert heard == [(SHORT_UTTERANCES[2], 2, 10)]

    @pytest.mark.parametrize("bad", ["Has Space", "UPPER", "", "-lead", "x" * 65])
    def test_a_case_id_must_be_id_shaped(self, bad: str) -> None:
        with pytest.raises(GuardEvalError):
            Case(bad, "short", lambda: CaseAudio(b"", ()))

    def test_an_unknown_kind_is_refused(self) -> None:
        with pytest.raises(GuardEvalError):
            Case("x-1", "music", lambda: CaseAudio(b"", ()))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# The synthetic set (C12)
# ---------------------------------------------------------------------------


def _script(encounter_id: str = "syn-001", *, synthetic: bool = True) -> dict[str, Any]:
    data: dict[str, Any] = {
        "schema_version": 1,
        "encounter_id": encounter_id,
        "appointment_type": "follow_up",
        "axes": ["laterality"],
        "lines": [
            {"role": "clinician", "text": "The left knee is tender."},
            {"role": "patient", "text": "It aches on the stairs."},
        ],
    }
    if synthetic:
        data["conditions"] = {"voice_slots": {"clinician": 0, "patient": 1}}
    return data


def _set_folder(folder: Path, *scripts: dict[str, Any]) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for data in scripts or (_script(),):
        stem = data["encounter_id"]
        (folder / f"{stem}.json").write_text(json.dumps(data), encoding="utf-8")
        write_wav(folder / f"{stem}.wav", b"\0" * 8_000 + _tone(1.5) + b"\0" * 8_000)
        (folder / f"{stem}.txt").write_text(
            "0.25\t1.75\tclinician\n", encoding="utf-8"
        )
    return folder


class TestSyntheticSet:
    def test_a_synthetic_set_becomes_set_cases(self, tmp_path: Path) -> None:
        folder = _set_folder(tmp_path / "set", _script("syn-001"), _script("syn-002"))
        encounters, incomplete = find_encounters(folder)
        assert incomplete == []
        cases, refusal = synthetic_set(encounters)
        assert refusal is None
        assert [(case.case_id, case.kind) for case in cases] == [
            ("syn-001", "set"),
            ("syn-002", "set"),
        ]
        audio = cases[0].load()
        assert len(audio.pcm) == (4_000 + 24_000 + 4_000) * BYTES_PER_SAMPLE
        assert audio.speech_spans == ((0.25, 1.75),)

    def test_a_script_without_conditions_refuses_the_set(self, tmp_path: Path) -> None:
        folder = _set_folder(
            tmp_path / "set", _script("syn-001"), _script("rp-002", synthetic=False)
        )
        cases, refusal = synthetic_set(find_encounters(folder)[0])
        assert cases == []
        assert refusal is not None
        assert refusal.startswith("rp-002 is not a synthetic encounter")

    def test_an_unusable_script_refuses_the_set_without_its_text(self, tmp_path: Path) -> None:
        bad = _script("syn-001")
        bad["lines"] = [{"role": "patient", "text": f"{_MARKER} only."}]
        folder = _set_folder(tmp_path / "set", bad)
        cases, refusal = synthetic_set(find_encounters(folder)[0])
        assert cases == []
        assert refusal is not None and refusal.startswith("syn-001.json:")
        assert _MARKER not in refusal


# ---------------------------------------------------------------------------
# Running a case and its rows
# ---------------------------------------------------------------------------


class _PlacedProvider:
    """Answers every window with words at fixed times RELATIVE to the window
    start, each carrying the given decode numbers."""

    model_name = "placed"

    def __init__(self, placed: list[tuple[str, float, float, float]], **decode: float) -> None:
        self._placed = placed
        self._decode = decode
        self.calls = 0

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        self.calls += 1
        return [
            TranscribedWord(
                text,
                start,
                end,
                probability,
                decode_no_speech_prob=self._decode.get("no_speech"),
                decode_avg_logprob=self._decode.get("avg_logprob"),
                decode_compression_ratio=self._decode.get("compression"),
            )
            for text, start, end, probability in self._placed
        ]


class _RaisingProvider:
    model_name = "raising"

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        raise RuntimeError(f"{_MARKER} Pain seven out of ten")


def _temp_stores() -> set[Path]:
    return {
        path
        for path in Path(tempfile.gettempdir()).iterdir()
        if path.name.startswith(TEMP_DIR_PREFIX)
    }


# The packed shape: the utterance (a tone) at 0.5-1.5 s, the "bed" (a tone)
# at 2.5-3.5 s — two VAD segments 1.0 s apart, so ONE window. The provider
# puts one word in the utterance and three low-probability words in the bed.
_PACKED_WORDS = [
    ("Okay", 0.2, 0.4, 0.95),
    (_MARKER, 2.3, 2.5, 0.3),
    ("seven", 2.5, 2.7, 0.3),
    ("ten", 2.7, 2.9, 0.3),
]


def _packed_case() -> Case:
    return Case("chord-20-packed", "chord", lambda: packed(_tone(1.0), _tone_floats(1.0)))


class TestRunCase:
    def test_a_packed_case_is_one_window_with_the_bed_marked_non_speech(self) -> None:
        pytest.importorskip("numpy")
        provider = _PlacedProvider(_PACKED_WORDS, no_speech=0.8, avg_logprob=-1.4, compression=2.6)
        rows = run_case(_packed_case(), provider, amplitude_vad, CLINICAL_INITIAL_PROMPT)
        assert provider.calls == 1  # case (b): the bed shares the utterance's window
        assert [(row.index, row.speech, row.features.word_count) for row in rows] == [
            (0, True, 1),
            (1, False, 3),
        ]
        bed = rows[1]
        assert bed.case_id == "chord-20-packed" and bed.kind == "chord"
        assert bed.features.mean_probability == pytest.approx(0.3)
        assert bed.features.no_speech_prob == pytest.approx(0.8)
        assert bed.avg_logprob == pytest.approx(-1.4)
        assert bed.compression_ratio == pytest.approx(2.6)
        assert bed.features.previous_empty is False  # the utterance held a word
        assert bed.features.word_span_seconds == pytest.approx(0.6)
        assert 1.0 <= bed.features.vad_seconds <= 1.5
        assert _temp_stores() == set()

    def test_an_empty_previous_segment_is_seen_across_segments(self) -> None:
        pytest.importorskip("numpy")
        provider = _PlacedProvider([w for w in _PACKED_WORDS if w[1] > 1.0], no_speech=0.8)
        rows = run_case(_packed_case(), provider, amplitude_vad, CLINICAL_INITIAL_PROMPT)
        assert [(row.features.word_count, row.features.previous_empty) for row in rows] == [
            (0, False),
            (3, True),
        ]

    def test_the_primer_echo_follows_the_primer_given(self) -> None:
        pytest.importorskip("numpy")
        words = [
            ("Okay", 0.2, 0.4, 0.95),
            ("rotator", 2.3, 2.5, 0.9),
            ("cuff", 2.5, 2.7, 0.9),
            ("supraspinatus", 2.7, 2.9, 0.9),
        ]
        primer = PRIMERS["shipped"]
        shipped = run_case(_packed_case(), _PlacedProvider(words), amplitude_vad, primer)
        assert [row.features.primer_echo for row in shipped] == [False, True]
        other = run_case(_packed_case(), _PlacedProvider(words), amplitude_vad, "Physiotherapy.")
        assert [row.features.primer_echo for row in other] == [False, False]

    def test_no_decode_numbers_read_as_none(self) -> None:
        pytest.importorskip("numpy")
        rows = run_case(_packed_case(), _PlacedProvider(_PACKED_WORDS), amplitude_vad, "")
        assert rows[1].features.no_speech_prob is None
        assert rows[1].avg_logprob is None and rows[1].compression_ratio is None

    def test_a_silent_case_has_no_rows_and_no_window(self) -> None:
        provider = _PlacedProvider(_PACKED_WORDS)
        case = Case("silence-alone", "silence", lambda: alone(silence_bed(1.0)))
        assert run_case(case, provider, amplitude_vad, CLINICAL_INITIAL_PROMPT) == []
        assert provider.calls == 0
        assert _temp_stores() == set()

    def test_calls_that_do_not_match_the_windows_are_a_fault(self) -> None:
        document = TranscriptDocument.model_validate(
            {
                "session_id": "a" * 32,
                "created_at": "2026-10-12T00:00:00Z",
                "model_name": "placed",
                "sample_rate": SAMPLE_RATE,
                "transcript_segments": [
                    {
                        "start_seconds": 0.5,
                        "end_seconds": 1.5,
                        "speaker": "speaker_1",
                        "transcript_words": [],
                    }
                ],
            }
        )
        with pytest.raises(GuardEvalError, match="do not match"):
            segment_rows(_packed_case(), document, [], (), CLINICAL_INITIAL_PROMPT)

    def test_rebuilt_words_that_do_not_match_a_segment_are_a_fault(self) -> None:
        # One window, one call — but the call's ONE word against the
        # segment's TWO stored words: the re-derivation drifted.
        stored = [
            {
                "word_text": text,
                "start_seconds": start,
                "end_seconds": start + 0.1,
                "probability": 0.9,
                "uncertain": False,
            }
            for text, start in (("one", 0.6), ("two", 0.8))
        ]
        document = TranscriptDocument.model_validate(
            {
                "session_id": "a" * 32,
                "created_at": "2026-10-12T00:00:00Z",
                "model_name": "placed",
                "sample_rate": SAMPLE_RATE,
                "transcript_segments": [
                    {
                        "start_seconds": 0.5,
                        "end_seconds": 1.5,
                        "speaker": "speaker_1",
                        "transcript_words": stored,
                    }
                ],
            }
        )
        calls = [[TranscribedWord("one", 0.1, 0.2, 0.9)]]
        with pytest.raises(GuardEvalError, match="rebuilt words"):
            segment_rows(_packed_case(), document, calls, (), CLINICAL_INITIAL_PROMPT)


class TestRunCases:
    def test_a_failing_case_is_reported_by_type_and_the_run_continues(self) -> None:
        pytest.importorskip("numpy")
        lines: list[str] = []
        cases = [
            Case("short-1-r0-v0", "short", lambda: spoken(_tone(0.8))),
            _packed_case(),
        ]
        rows, errors = run_cases(
            cases, _RaisingProvider(), amplitude_vad, "", progress=lines.append
        )
        assert rows == []
        assert errors == [("short-1-r0-v0", "RuntimeError"), ("chord-20-packed", "RuntimeError")]
        assert lines == [
            "[run ] short-1-r0-v0",
            "[error] short-1-r0-v0: RuntimeError",
            "[run ] chord-20-packed",
            "[error] chord-20-packed: RuntimeError",
        ]
        assert _temp_stores() == set()

    def test_a_refused_wav_is_reported_by_type(self) -> None:
        def refused() -> CaseAudio:
            raise WavFormatError(f"{_MARKER}.wav is not a readable WAV file")

        lines: list[str] = []
        rows, errors = run_cases(
            [Case("syn-001", "set", refused)], _RaisingProvider(), amplitude_vad, "",
            progress=lines.append,
        )
        assert errors == [("syn-001", "WavFormatError")]
        assert _MARKER not in "\n".join(lines)

    def test_a_custody_fault_stops_the_run(self) -> None:
        def custody() -> CaseAudio:
            raise SpeakerEvalError("a temporary store could not be shown gone: C:\\x")

        later: list[str] = []

        def never() -> CaseAudio:
            later.append("ran")
            return CaseAudio(b"", ())

        cases = [Case("syn-001", "set", custody), Case("syn-002", "set", never)]
        with pytest.raises(SpeakerEvalError):
            run_cases(cases, _RaisingProvider(), amplitude_vad, "", progress=lambda line: None)
        assert later == []


# ---------------------------------------------------------------------------
# Candidates and the report (text-free)
# ---------------------------------------------------------------------------


def _features(**values: Any) -> GuardFeatures:
    base: dict[str, Any] = {
        "word_count": 4,
        "vad_seconds": 0.9,
        "word_span_seconds": 0.8,
        "words_per_second": 4 / 0.9,
        "mean_probability": 0.35,
        "no_speech_prob": None,
        "primer_echo": False,
        "previous_empty": True,
    }
    base.update(values)
    return GuardFeatures(**base)


def _row(case_id: str, kind: str, index: int, speech: bool, **values: Any) -> SegmentRow:
    return SegmentRow(case_id, kind, index, speech, _features(**values), None, None)  # type: ignore[arg-type]


_ROWS = [
    _row("chord-20-alone", "chord", 0, False),  # the observed shape
    _row("chord-20-alone", "chord", 1, False, word_count=0, mean_probability=None),
    _row("short-3-r10-v0", "short", 0, True, words_per_second=3.75, mean_probability=0.9),
    _row("syn-001", "set", 0, True, words_per_second=2.5, mean_probability=0.92),
    _row("syn-001", "set", 1, True, words_per_second=5.1, mean_probability=0.4, primer_echo=True),
]


class TestCandidates:
    def test_parse_a_candidate(self) -> None:
        assert parse_candidate("3,1.5,4.5,0.5,0.6") == Candidate(3, 1.5, 4.5, 0.5, 0.6)

    @pytest.mark.parametrize("bad", ["3,1.5,4.5,0.5", "x,1.5,4.5,0.5,0.6", "0,1,1,1,1",
                                     "3,1.5,nan,0.5,0.6", "3,-1,4.5,0.5,0.6",
                                     "3,1.5,4.5,1.5,0.6", "3,1.5,4.5,0.5,1.2"])
    def test_a_bad_candidate_is_refused(self, bad: str) -> None:
        import argparse

        with pytest.raises(argparse.ArgumentTypeError):
            parse_candidate(bad)

    def test_the_proposed_sweep(self) -> None:
        assert DEFAULT_CANDIDATES == (
            Candidate(3, 1.5, 4.0, 0.45, 0.6),
            Candidate(3, 1.5, 4.0, 0.6, 0.6),
            Candidate(3, 1.5, 4.5, 0.45, 0.6),
            Candidate(3, 1.5, 4.5, 0.6, 0.6),
            Candidate(3, 1.5, 5.5, 0.45, 0.6),
            Candidate(3, 1.5, 5.5, 0.6, 0.6),
            Candidate(3, 1.5, 6.5, 0.45, 0.6),
            Candidate(3, 1.5, 6.5, 0.6, 0.6),
        )

    def test_the_sweep_can_catch_the_observed_shape(self) -> None:
        # 4 words in 0.9 s (4.44 words/s), mean 0.35, previous empty, no
        # decode number: only the 4.0 words/s sets flag it (rate + low
        # probability); above 4.44 it is probability alone.
        observed = _features()
        assert [c.decide(observed) for c in DEFAULT_CANDIDATES] == [
            True, True, False, False, False, False, False, False,
        ]

    def test_a_candidate_decides_through_the_shipped_rule(self) -> None:
        observed = _features()
        assert Candidate(3, 1.5, 4.0, 0.5, 0.6).decide(observed) is True
        assert Candidate(3, 1.5, 4.5, 0.5, 0.6).decide(observed) is False  # probability alone
        assert Candidate(5, 1.5, 4.0, 0.5, 0.6).decide(observed) is False  # too few words


def _report_lines(text: str) -> list[list[str]]:
    return [
        [cell.strip() for cell in line.strip("|").split("|")]
        for line in text.splitlines()
        if line.startswith("|") and not line.startswith("|---")
    ]


_HEADINGS = {
    "",
    "# Transcription guard measurement",
    "## Segments",
    "## The synthetic set's speech segments",
    "## Candidates (flagged / segments with words)",
    "## Errors",
}
_VOCABULARY = (
    set(guard_eval.SEGMENT_HEADER)
    | set(guard_eval.SET_SUMMARY_HEADER)
    | set(guard_eval.CANDIDATE_HEADER)
    | set(guard_eval.RUN_HEADER)
    | {"case", "error"}
    | set(CASE_KINDS)
    | set(PRIMERS)
    | {"yes", "no", "—"}
)
_NUMBER_CELL = re.compile(r"^-?\d+(\.\d+)?$|^\d+/\d+$|^c\d+$")


_ERROR_LINE = re.compile(r"^\[error\] (\S+): ([A-Za-z]+)$")


def _assert_text_free(text: str, ids: set[str], extra: frozenset[str] = frozenset()) -> None:
    """Every line a heading, a ``[run ]`` or ``[error]`` line naming a case
    id (an error by a type in ``extra``) or a table row; every cell a
    closed word, a case id, a name in ``extra`` or a number."""
    for line in text.splitlines():
        if line.startswith("|"):
            continue
        error = _ERROR_LINE.match(line)
        if error is not None:
            assert error.group(1) in ids and error.group(2) in extra, line
            continue
        assert line in _HEADINGS or line.removeprefix("[run ] ") in ids, line
    for cells in _report_lines(text):
        for cell in cells:
            assert cell in _VOCABULARY or cell in ids or cell in extra or _NUMBER_CELL.match(
                cell
            ), cell


class TestReport:
    def test_the_report_counts_flagged_segments_per_candidate(self) -> None:
        text = render_report(
            _ROWS,
            [Candidate(3, 1.5, 4.0, 0.5, 0.6), Candidate(3, 1.5, 5.0, 0.5, 0.6)],
            [],
            whisper_model="medium",
            primer_name="shipped",
            cases=3,
        )
        tables = _report_lines(text)
        assert tables[0] == [
            "whisper model", "primer", "cases", "errors", "cases without a segment"
        ]
        assert tables[1] == ["medium", "shipped", "3", "0", "0"]
        candidates = [cells for cells in tables if cells[0] in {"c1", "c2"}]
        assert candidates[0] == [
            "c1", "3", "1.500", "4.000", "0.500", "0.600",
            "1/1", "1/3", "0/0", "0/0", "1/1", "0/0", "0/1", "1/2",
        ]
        assert candidates[1] == [
            "c2", "3", "1.500", "5.000", "0.500", "0.600",
            "0/1", "1/3", "0/0", "0/0", "0/1", "0/0", "0/1", "1/2",
        ]

    def test_set_rows_are_summarised_unless_all_rows(self) -> None:
        def segment_cases(text: str) -> list[str]:
            header = list(guard_eval.SEGMENT_HEADER)
            return [cells[0] for cells in _report_lines(text) if len(cells) == len(header)
                    and cells != header]

        common: dict[str, Any] = {"whisper_model": "medium", "primer_name": "shipped", "cases": 3}
        summary = render_report(_ROWS, [], [], **common)
        assert segment_cases(summary) == ["chord-20-alone", "chord-20-alone", "short-3-r10-v0"]
        everything = render_report(_ROWS, [], [], all_rows=True, **common)
        assert segment_cases(everything)[-2:] == ["syn-001", "syn-001"]
        (set_summary,) = [cells for cells in _report_lines(summary) if cells[0] == "2"]
        assert set_summary == ["2", "2", "5.100", "5.100", "5.100", "0.400", "0.400", "—",
                               "1", "2"]

    def test_the_report_is_text_free(self) -> None:
        errors = [("syn-002", "RuntimeError")]
        text = render_report(
            _ROWS, DEFAULT_CANDIDATES, errors, whisper_model="medium", primer_name="0.3.1",
            cases=4, all_rows=True,
        )
        assert "## Errors" in text
        ids = {"chord-20-alone", "short-3-r10-v0", "syn-001", "syn-002"}
        _assert_text_free(text, ids, frozenset({"medium", "RuntimeError"}))

    def test_cases_without_a_segment_are_counted(self) -> None:
        # 6 cases: 3 with rows, 1 errored, so 2 ran and found nothing to decode.
        text = render_report(
            _ROWS, [], [("syn-002", "RuntimeError")], whisper_model="medium",
            primer_name="shipped", cases=6,
        )
        assert _report_lines(text)[1] == ["medium", "shipped", "6", "1", "2"]

    def test_the_percentile_is_the_nearest_rank(self) -> None:
        values = [float(i) for i in range(20, 0, -1)]  # 20 values, unsorted
        assert guard_eval._percentile(values, 0.95) == 19.0
        assert guard_eval._percentile(values, 0.99) == 20.0
        assert guard_eval._percentile(values, 0.05) == 1.0
        assert guard_eval._percentile(values, 0.5) == 10.0
        assert guard_eval._percentile([], 0.5) is None


# ---------------------------------------------------------------------------
# main and the launcher
# ---------------------------------------------------------------------------


def _load_launcher(name: str) -> ModuleType:
    path = REPO / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py").replace("-", "_"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _NeverBuilt:
    def __init__(self, *args: object, **kwargs: object) -> None:
        raise AssertionError("no model may be constructed on this path")


class _FakeVad:
    def __init__(self) -> None:
        self.frame_probability = amplitude_vad


class _FakeWhisper:
    """Answers every window with invented words — the marker, a short
    utterance's words and primer words — at the window's start."""

    prompts: list[str | None] = []

    def __init__(self, *, model_name: str, initial_prompt: str | None) -> None:
        type(self).prompts.append(initial_prompt)

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        texts = [_MARKER, "Four", "out", "of", "ten.", "rotator", "cuff", "supraspinatus"]
        return [
            TranscribedWord(text, 0.05 * i, 0.05 * (i + 1), 0.3, decode_no_speech_prob=0.7)
            for i, text in enumerate(texts)
        ]


def _voices() -> tuple[str, ...]:
    return ("Voice A", "Voice B")


class TestMain:
    @pytest.fixture(autouse=True)
    def _dev_and_no_models_built(self, monkeypatch: pytest.MonkeyPatch) -> None:
        use_channel(monkeypatch, "dev")
        monkeypatch.setattr(guard_eval, "SileroVad", _NeverBuilt)
        monkeypatch.setattr(guard_eval, "WhisperSpeechProvider", _NeverBuilt)

    def _models_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(guard_eval, "resolve_whisper_model", lambda: "medium")
        monkeypatch.setattr(guard_eval, "whisper_model_available", lambda name: True)
        monkeypatch.setattr(guard_eval, "vad_model_available", lambda: True)

    def _argv(self, tmp_path: Path, *extra: str) -> list[str]:
        return ["--set", str(_set_folder(tmp_path / "set")), *extra]

    def test_the_launcher_is_thin_and_prints_usage_without_models(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        launcher = _load_launcher("measure-transcription-guard.py")
        assert launcher.main is guard_eval.main
        with pytest.raises(SystemExit) as info:
            launcher.main(["--help"])
        assert info.value.code == 0
        assert "usage:" in capsys.readouterr().out

    @pytest.mark.parametrize(
        "argv",
        [
            ["--set", "unused", "--primer", f"{_MARKER} Pain seven out of ten."],
            ["--set", "unused", f"--{_MARKER.lower()}", "out"],
            ["--set", "unused", _MARKER],
            ["--set", "unused", "--candidates", f"{_MARKER},1.5,4.5,0.5,0.6"],
        ],
        ids=["invalid-choice", "unknown-option", "unknown-argument", "bad-candidate"],
    )
    def test_a_command_line_error_echoes_nothing_it_was_given(
        self, argv: list[str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Peer round 3 PR-LOW-001: argparse's own diagnostics quote the
        # rejected value; the tool prints fixed text and the usage instead.
        with pytest.raises(SystemExit) as info:
            guard_eval.main(argv)
        assert info.value.code == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err.startswith("usage:")
        assert captured.err.endswith(
            "[refused] the command line was not understood - see --help\n"
        )
        output = captured.out + captured.err
        assert _MARKER not in output and _MARKER.lower() not in output
        assert "Pain" not in output and "invalid choice" not in output

    def test_a_packaged_build_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        use_channel(monkeypatch, "production")
        assert guard_eval.main(self._argv(tmp_path)) == 2
        assert "only on the developer build" in capsys.readouterr().out

    def test_the_offline_environment_is_applied_first(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import os

        monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
        # Refused at the very next step (the set folder), so applied before it.
        assert guard_eval.main(["--set", str(tmp_path / "absent")]) == 2
        assert os.environ.get("HF_HUB_OFFLINE") == "1"

    def test_a_missing_set_folder_is_refused(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert guard_eval.main(["--set", str(tmp_path / "absent")]) == 2
        assert "is not a folder" in capsys.readouterr().out

    def test_an_empty_models_folder_is_refused_by_name(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert guard_eval.main(self._argv(tmp_path)) == 2
        out = capsys.readouterr().out
        assert "[refused] no Whisper model is installed in" in out
        assert str(install_layout.models_root()) in out

    def test_small_is_refused_without_allow_small(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._models_present(monkeypatch)
        monkeypatch.setattr(guard_eval, "resolve_whisper_model", lambda: "small")
        assert guard_eval.main(self._argv(tmp_path), voices=_voices) == 2
        assert "--allow-small" in capsys.readouterr().out

    def test_a_non_synthetic_set_is_refused_before_any_model(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._models_present(monkeypatch)
        folder = _set_folder(tmp_path / "set", _script("syn-001"), _script("rp-1", synthetic=False))
        assert guard_eval.main(["--set", str(folder)], voices=_voices) == 2
        assert "[refused] rp-1 is not a synthetic encounter" in capsys.readouterr().out

    def test_an_incomplete_set_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._models_present(monkeypatch)
        folder = _set_folder(tmp_path / "set")
        (folder / "syn-001.txt").unlink()
        assert guard_eval.main(["--set", str(folder)], voices=_voices) == 2
        out = capsys.readouterr().out
        assert "[refused] syn-001: missing .txt" in out
        assert "[refused] no complete encounters" in out

    def test_no_voice_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._models_present(monkeypatch)
        assert guard_eval.main(self._argv(tmp_path), voices=lambda: ()) == 2
        assert "[refused] no Windows voice is installed" in capsys.readouterr().out

    def test_a_voice_listing_failure_is_refused_by_type(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._models_present(monkeypatch)

        def broken() -> tuple[str, ...]:
            raise OSError(f"{_MARKER} voice")

        assert guard_eval.main(self._argv(tmp_path), voices=broken) == 2
        out = capsys.readouterr().out
        assert "cannot be listed (OSError)" in out
        assert _MARKER not in out

    def test_a_model_load_failure_is_refused_by_type(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._models_present(monkeypatch)
        monkeypatch.setattr(guard_eval, "SileroVad", _FakeVad)

        def broken(**kwargs: object) -> object:
            raise RuntimeError(f"{_MARKER} at C:\\models")

        monkeypatch.setattr(guard_eval, "WhisperSpeechProvider", broken)
        assert guard_eval.main(self._argv(tmp_path), voices=_voices) == 2
        captured = capsys.readouterr()
        assert "[refused] the models could not be loaded (RuntimeError)" in captured.out
        assert _MARKER not in captured.out + captured.err

    @pytest.mark.parametrize("primer", ["shipped", "0.3.1"])
    def test_a_full_run_prints_only_numbers_and_closed_words(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        primer: str,
    ) -> None:
        pytest.importorskip("numpy")
        self._models_present(monkeypatch)
        monkeypatch.setattr(guard_eval, "SileroVad", _FakeVad)
        monkeypatch.setattr(guard_eval, "WhisperSpeechProvider", _FakeWhisper)
        monkeypatch.setattr(guard_eval, "BED_SECONDS", 1.0)  # a quicker run
        _FakeWhisper.prompts = []
        argv = [*self._argv(tmp_path), "--primer", primer, "--all-rows"]
        assert guard_eval.main(argv, voices=_voices, synthesize=_fake_synthesize) == 0
        assert _FakeWhisper.prompts == [PRIMERS[primer]]
        captured = capsys.readouterr()
        output = captured.out + captured.err
        ids = {case.case_id for case in bed_cases(_fake_synthesize)}
        ids |= {case.case_id for case in short_cases(_fake_synthesize, 2)}
        ids.add("syn-001")
        _assert_text_free(captured.out, ids, frozenset({"medium"}))
        assert captured.err == ""
        _assert_no_text(output)
        tables = _report_lines(captured.out)
        # 16 bed cases + 6 utterances x 3 rates x 2 voices + 1 set encounter;
        # silence-alone at least finds no segment.
        assert tables[1][:4] == ["medium", primer, "53", "0"]
        assert int(tables[1][4]) >= 1
        # The provider's words reached segments, so the text checks above
        # ran over real rows: the set's one segment holds words.
        (set_summary,) = [
            cells for cells in tables
            if len(cells) == len(guard_eval.SET_SUMMARY_HEADER)
            and cells != list(guard_eval.SET_SUMMARY_HEADER)
        ]
        assert int(set_summary[1]) >= 1
        assert _temp_stores() == set()

    def test_a_failing_provider_prints_no_text(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pytest.importorskip("numpy")
        self._models_present(monkeypatch)
        monkeypatch.setattr(guard_eval, "SileroVad", _FakeVad)

        class _Failing(_FakeWhisper):
            def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
                raise ValueError(f"{_MARKER} {PACKING_UTTERANCE} {SHORT_UTTERANCES[3]}")

        monkeypatch.setattr(guard_eval, "WhisperSpeechProvider", _Failing)
        monkeypatch.setattr(guard_eval, "BED_SECONDS", 1.0)
        assert guard_eval.main(self._argv(tmp_path), voices=_voices,
                               synthesize=_fake_synthesize) == 1
        captured = capsys.readouterr()
        _assert_no_text(captured.out + captured.err)
        ids = {case.case_id for case in bed_cases(_fake_synthesize)}
        ids |= {case.case_id for case in short_cases(_fake_synthesize, 2)}
        ids.add("syn-001")
        # Every line and cell, the [error] lines included: no short word leaks.
        _assert_text_free(captured.out, ids, frozenset({"medium", "ValueError"}))
        # And nothing on stderr at all, so no word of any length leaks there
        # (peer round 3 PR-LOW-002; the successful run asserts the same).
        assert captured.err == ""
        assert "[error] syn-001: ValueError" in captured.out
        assert "| syn-001 | ValueError |" in captured.out
        assert _temp_stores() == set()

    def test_a_missing_vad_model_is_refused_by_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._models_present(monkeypatch)
        monkeypatch.setattr(guard_eval, "vad_model_available", lambda: False)
        assert guard_eval.main(self._argv(tmp_path), voices=_voices) == 2
        assert "[refused] the silero VAD model is not installed in" in capsys.readouterr().out

    def test_an_unlocatable_models_folder_is_refused_by_type(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def broken() -> Path:
            raise RuntimeError(f"{_MARKER} models")

        monkeypatch.setattr(install_layout, "models_root", broken)
        assert guard_eval.main(self._argv(tmp_path), voices=_voices) == 2
        out = capsys.readouterr().out
        assert "[refused] the models folder cannot be located (RuntimeError)" in out
        assert _MARKER not in out

    def test_a_custody_fault_stops_main_without_a_report(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._models_present(monkeypatch)
        monkeypatch.setattr(guard_eval, "SileroVad", _FakeVad)
        monkeypatch.setattr(guard_eval, "WhisperSpeechProvider", _FakeWhisper)

        def custody(*args: object, **kwargs: object) -> object:
            raise SpeakerEvalError("a temporary store could not be shown gone: C:\\x")

        monkeypatch.setattr(guard_eval, "run_cases", custody)
        assert guard_eval.main(self._argv(tmp_path), voices=_voices) == 1
        out = capsys.readouterr().out
        assert "[custody] the run stopped: a temporary store could not be shown gone" in out
        assert "# Transcription guard measurement" not in out

    def test_an_interrupted_run_prints_no_report(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._models_present(monkeypatch)
        monkeypatch.setattr(guard_eval, "SileroVad", _FakeVad)
        monkeypatch.setattr(guard_eval, "WhisperSpeechProvider", _FakeWhisper)

        def interrupted(*args: object, **kwargs: object) -> object:
            raise KeyboardInterrupt

        monkeypatch.setattr(guard_eval, "run_cases", interrupted)
        assert guard_eval.main(self._argv(tmp_path), voices=_voices) == 1
        out = capsys.readouterr().out
        assert "[stopped] the run was interrupted, so there is no report" in out
        assert "# Transcription guard measurement" not in out


def _assert_no_text(output: str) -> None:
    """No word the fake provider returned, no utterance and no primer token
    (of four letters or more, as a whole word) in ``output``."""
    assert _MARKER not in output
    for utterance in (*SHORT_UTTERANCES, PACKING_UTTERANCE):
        assert utterance not in output
    words = set(content_tokens(CLINICAL_INITIAL_PROMPT)) | set(
        content_tokens(guard_eval.PRIMER_0_3_1)
    )
    for utterance in (*SHORT_UTTERANCES, PACKING_UTTERANCE):
        words |= set(content_tokens(utterance))
    for word in sorted(w for w in words if len(w) >= 4):
        assert not re.search(rf"\b{re.escape(word)}\b", output, re.IGNORECASE), word


# ---------------------------------------------------------------------------
# Pins: what the module may not touch (C5, C12)
# ---------------------------------------------------------------------------

_SOURCE = Path(guard_eval.__file__).read_text(encoding="utf-8")
_FORBIDDEN_NAMES = frozenset(
    {
        "wave",
        "write_wav",
        "wav_bytes",
        "read_recording",
        "_recording_chunks",
        "_audio_chunks",
        "open",
        "read_bytes",
        "read_text",
        "write_bytes",
        "write_text",
        "logging",
        "log_event",
        "getLogger",
    }
)


def test_the_module_opens_no_file_and_references_no_recording_or_writer() -> None:
    found = []
    for node in ast.walk(ast.parse(_SOURCE)):
        name = None
        if isinstance(node, ast.Name):
            name = node.id
        elif isinstance(node, ast.Attribute):
            name = node.attr
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            name = node.value
        elif isinstance(node, ast.alias):
            name = node.name.split(".")[-1]
        if name in _FORBIDDEN_NAMES:
            found.append(f"{name}:{getattr(node, 'lineno', '?')}")
    assert found == []


def test_the_module_never_names_the_past_sessions_store() -> None:
    assert "past_sessions" not in _SOURCE
    assert "replay_kept" not in _SOURCE


def test_no_ml_runtime_at_import_time() -> None:
    runtimes = (
        "onnxruntime", "faster_whisper", "ctranslate2", "llama_cpp", "av", "huggingface_hub"
    )
    code = (
        "import sys, scribe_desktop.guard_eval; "
        f"print(','.join(n for n in {runtimes!r} if n in sys.modules))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=120, check=True
    )
    assert result.stdout.strip() == ""
