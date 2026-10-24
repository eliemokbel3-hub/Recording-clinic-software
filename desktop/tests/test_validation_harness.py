"""Pilot plan Tasks 2.1, 2.2, 2.4 and 2.7 (``run-validation.py``): the custody
helpers' public names, the encounter script format, the runner and its
command line.

The runner legs build a REAL DPAPI-wrapped temporary store (Windows, like
``test_speaker_eval.py``'s) over generated tones with an amplitude VAD and a
scripted speech provider — no real model, no SAPI voice, and the models root
is the conftest's empty pin. No clinical content: invented sentences only.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from conftest import use_channel
from scribe_desktop import install_layout, speaker_eval, validation
from scribe_desktop.benchmark import apply_offline_env
from scribe_desktop.note import GeneratedSection, NoteRequest, whole_utterance_assertion
from scribe_desktop.note_config import load_note_config
from scribe_desktop.speaker_eval import TEMP_DIR_PREFIX, SpeakerEvalError, parse_audacity_labels
from scribe_desktop.speech import BYTES_PER_SAMPLE, SAMPLE_RATE, TranscribedWord
from scribe_desktop.transcription import TranscriptDocument, TranscriptSegment, TranscriptWord
from scribe_desktop.ui import models
from scribe_desktop.validation import (
    EncounterOutcome,
    HarnessInputs,
    PassRule,
    ScriptError,
    find_encounters,
    load_script,
    render_report,
    run_encounters,
)
from scribe_desktop.validation_set import write_wav
from speaker_fakes import FrequencyEmbedder

REPO = Path(__file__).resolve().parents[2]
windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-only")
OPTION_A = PassRule(schema_version=1, rule_name="option-a-proposed")


@pytest.fixture(autouse=True)
def _offline_env() -> None:
    apply_offline_env()


@pytest.fixture(autouse=True)
def _private_temp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The temporary stores land in a folder of this test's own, never the
    shared system temp folder (round 11 LOW-018: a run elsewhere could not
    disturb the before/after comparison)."""
    folder = tmp_path / "system-temp"
    folder.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(folder))
    return folder


# ---------------------------------------------------------------------------
# Task 2.1: the custody helpers keep living in speaker_eval
# ---------------------------------------------------------------------------


class TestCustodyHelperNames:
    def test_the_public_names_are_the_private_objects(self) -> None:
        assert (
            speaker_eval.transcribe_in_temporary_store
            is speaker_eval._transcribe_in_temporary_store
        )
        assert speaker_eval.destroy_temporary_store is speaker_eval._destroy_temporary_store
        assert speaker_eval.transcribe_in_temporary_store.__module__ == speaker_eval.__name__
        assert speaker_eval.destroy_temporary_store.__module__ == speaker_eval.__name__

    def test_the_harness_uses_the_same_objects(self) -> None:
        assert (
            validation.transcribe_in_temporary_store
            is speaker_eval.transcribe_in_temporary_store
        )

    def test_the_provider_factory_has_its_public_name(self) -> None:
        assert models.extractive_provider_from_config is models._extractive_provider_from_config

    def test_no_ml_runtime_at_import_time(self) -> None:
        """In a fresh interpreter (round 11 LOW-004): importing the harness and
        the builder loads none of the model runtimes, so ``main`` applies the
        offline environment before any of them can be imported."""
        runtimes = ("onnxruntime", "faster_whisper", "ctranslate2", "llama_cpp", "av",
                    "huggingface_hub")
        code = (
            "import sys, scribe_desktop.validation, scribe_desktop.validation_set; "
            f"print(','.join(n for n in {runtimes!r} if n in sys.modules))"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, timeout=120, check=True
        )
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# Task 2.2: the encounter script format
# ---------------------------------------------------------------------------


def _valid(**overrides: Any) -> dict[str, Any]:
    script: dict[str, Any] = {
        "schema_version": 1,
        "encounter_id": "syn-001",
        "appointment_type": "follow_up",
        "axes": ["laterality", "noise", "rate", "overlap"],
        "lines": [
            {"role": "clinician", "text": "How is the left knee today?"},
            {"role": "patient", "text": "Much better, thanks."},
        ],
        "facts": [
            {"kind": "laterality", "tokens": ["left", "knee"], "line": 0, "material": True}
        ],
        "expected_warnings": [],
        "conditions": {
            "voice_slots": {"clinician": 0, "patient": 1},
            "rate": 2,
            "snr_db": 20.0,
            "overlap_seconds": 0.3,
            "overlap_lines": [1],
        },
    }
    script.update(overrides)
    return script


def _write_script(folder: Path, data: dict[str, Any], stem: str | None = None) -> Path:
    path = folder / f"{stem or data['encounter_id']}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class TestScriptFormat:
    def test_a_valid_synthetic_script_loads(self, tmp_path: Path) -> None:
        script = load_script(_write_script(tmp_path, _valid()))
        assert script.encounter_id == "syn-001"
        assert script.conditions is not None and script.conditions.rate == 2
        assert script.facts[0].tokens == ("left", "knee")

    def test_a_role_play_script_needs_no_conditions(self, tmp_path: Path) -> None:
        data = _valid(axes=["laterality", "overlap"], conditions=None)
        assert load_script(_write_script(tmp_path, data)).conditions is None

    @pytest.mark.parametrize(
        ("overrides", "named"),
        [
            ({"lines": [{"role": "patient", "text": "Hello."}], "facts": []}, "clinician"),
            (
                {"facts": [{"kind": "laterality", "tokens": ["right", "knee"], "line": 0,
                            "material": True}]},
                "do not occur",
            ),
            (
                {"facts": [{"kind": "present", "tokens": ["much"], "line": 5,
                            "material": True}]},
                "does not exist",
            ),
            (
                {"facts": [{"kind": "laterality", "tokens": ["Left", "knee"], "line": 0,
                            "material": True}]},
                "normalised",
            ),
            ({"axes": ["laterality", "noise", "rate", "overlap", "accents"]}, "axes"),
            ({"axes": ["laterality", "rate", "overlap"]}, "'noise'"),
            ({"axes": ["laterality", "noise", "overlap"]}, "'rate'"),
            ({"expected_warnings": ["reconstruction_mismatch"]}, "expected_warnings"),
            ({"appointment_type": "massage"}, "appointment_type"),
            ({"schema_version": 2}, "schema_version"),
            ({"surprise": True}, "<key>: Extra inputs"),
            # Round 11 LOW-005: every remaining refusal branch.
            (
                {"lines": [{"role": "clinician", "text": "How is the left knee today?"},
                           {"role": "patient", "text": "..."}]},
                "at least one word",
            ),
            ({"axes": ["laterality", "noise", "rate", "overlap", "noise"]}, "axes must be unique"),
            (
                {"expected_warnings": ["contradiction", "contradiction"]},
                "expected_warnings must be unique",
            ),
            (
                {"conditions": {"voice_slots": {"clinician": 0, "patient": 1}, "rate": 2,
                                "snr_db": 20.0, "overlap_seconds": 0.3, "overlap_lines": [0]}},
                "no previous line",
            ),
            ({"axes": ["laterality", "noise", "rate"]}, "'overlap'"),
            # Round 12 LOW-001: an absent fact's uncertainty could be
            # surfaced only by its wrongly reaching the note.
            (
                {"facts": [{"kind": "absent", "tokens": ["left", "knee"], "line": 0,
                            "material": False, "expect_uncertain": True}]},
                "absent fact cannot expect",
            ),
            (
                {"conditions": {"voice_slots": {"clinician": 0, "patient": 1}, "rate": 2,
                                "snr_db": 20.0}},
                "'overlap'",
            ),
            (
                {"conditions": {"voice_slots": {"clinician": 0, "patient": 1}, "rate": 2,
                                "overlap_seconds": 0.3, "overlap_lines": [1]}},
                "'noise'",
            ),
            (
                {"conditions": {"voice_slots": {"clinician": 0, "patient": 1}, "snr_db": 20.0,
                                "overlap_seconds": 0.3, "overlap_lines": [1]}},
                "'rate'",
            ),
        ],
    )
    def test_invalid_scripts_are_refused_by_name(
        self, tmp_path: Path, overrides: dict[str, Any], named: str
    ) -> None:
        with pytest.raises(ScriptError, match="syn-001.json") as info:
            load_script(_write_script(tmp_path, _valid(**overrides)))
        assert named in str(info.value)

    @pytest.mark.parametrize(
        ("conditions", "named"),
        [
            ({"voice_slots": {"clinician": 0}}, "voice_slots"),
            ({"voice_slots": {"clinician": 0, "patient": 0}}, "own voice slot"),
            (
                {"voice_slots": {"clinician": 0, "patient": 1}, "overlap_seconds": 0.3},
                "set together",
            ),
            ({"voice_slots": {"clinician": 0, "Patient": 1}}, "voice_slots keys"),
            ({"voice_slots": {"clinician": 0, "patient": -1}}, "non-negative"),
            (
                {"voice_slots": {"clinician": 0, "patient": 1}, "overlap_seconds": 0.3,
                 "overlap_lines": [3, 1]},
                "ascending",
            ),
            (
                {"voice_slots": {"clinician": 0, "patient": 1}, "overlap_seconds": 0.3,
                 "overlap_lines": [1, 2]},
                "two consecutive lines",
            ),
        ],
    )
    def test_invalid_conditions_are_refused(
        self, tmp_path: Path, conditions: dict[str, Any], named: str
    ) -> None:
        data = _valid(axes=["laterality"], conditions=conditions)
        with pytest.raises(ScriptError, match="syn-001.json") as info:
            load_script(_write_script(tmp_path, data))
        assert named in str(info.value)

    def test_an_unknown_key_is_never_printed(self, tmp_path: Path) -> None:
        with pytest.raises(ScriptError) as info:
            load_script(_write_script(tmp_path, _valid(**{"Margaret Example": True})))
        assert "Margaret" not in str(info.value)
        assert "<key>" in str(info.value)

    def test_an_oversized_script_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "syn-001.json"
        path.write_bytes(b" " * (validation.MAX_SCRIPT_BYTES + 1))
        with pytest.raises(ScriptError, match="syn-001.json: larger than"):
            load_script(path)

    def test_an_overlap_that_continues_the_same_role_is_refused(self, tmp_path: Path) -> None:
        data = _valid(
            lines=[
                {"role": "clinician", "text": "How is the left knee today?"},
                {"role": "clinician", "text": "Any better?"},
            ],
            conditions={"voice_slots": {"clinician": 0}, "rate": 2, "snr_db": 20.0,
                        "overlap_seconds": 0.3, "overlap_lines": [1]},
        )
        with pytest.raises(ScriptError, match="same role"):
            load_script(_write_script(tmp_path, data))

    def test_the_file_stem_must_be_the_encounter_id(self, tmp_path: Path) -> None:
        with pytest.raises(ScriptError, match="different encounter"):
            load_script(_write_script(tmp_path, _valid(), stem="syn-002"))

    def test_unreadable_json_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "syn-001.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(ScriptError, match="syn-001.json"):
            load_script(path)

    def test_the_rejected_text_never_reaches_the_message(self, tmp_path: Path) -> None:
        data = _valid(encounter_id="Margaret Example", lines=[{"role": "Dr Example", "text": "x"}])
        path = _write_script(tmp_path, data, stem="syn-001")
        with pytest.raises(ScriptError) as info:
            load_script(path)
        assert "Margaret" not in str(info.value)
        assert "Dr Example" not in str(info.value)


def _tone(seconds: float, frequency: float, amplitude: float = 0.5) -> bytes:
    count = int(seconds * SAMPLE_RATE)
    scale = amplitude * 32767
    return struct.pack(
        f"<{count}h",
        *(int(scale * math.sin(2 * math.pi * frequency * i / SAMPLE_RATE)) for i in range(count)),
    )


def _silence(seconds: float) -> bytes:
    return b"\0" * (int(seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE)


def _write_wav(path: Path, pcm: bytes) -> Path:
    write_wav(path, pcm)
    return path


# Two turns: the clinician's tone at 1.0-2.5 s, the patient's at 3.5-5.0 s.
TWO_TURNS_PCM = (
    _silence(1.0) + _tone(1.5, 220.0) + _silence(1.0) + _tone(1.5, 2600.0) + _silence(1.0)
)
TWO_TURNS_LABELS = "1.0\t2.5\tclinician\n3.5\t5.0\tpatient\n"
# The patient's label covers both tones: no cluster is the clinician's.
UNRESOLVED_LABELS = "0.0\t0.5\tclinician\n1.0\t5.0\tpatient\n"


def _set_folder(
    folder: Path, *, labels: str = TWO_TURNS_LABELS, script: dict[str, Any] | None = None
) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    data = script or _two_turn_script()
    _write_script(folder, data)
    _write_wav(folder / f"{data['encounter_id']}.wav", TWO_TURNS_PCM)
    (folder / f"{data['encounter_id']}.txt").write_text(labels, encoding="utf-8")
    return folder


def _two_turn_script() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "encounter_id": "syn-001",
        "appointment_type": "follow_up",
        "axes": ["laterality"],
        "lines": [
            {"role": "clinician", "text": "On examination the left knee is tender."},
            {"role": "patient", "text": "It hurts when I walk."},
        ],
        "facts": [
            {"kind": "laterality", "tokens": ["left", "knee"], "line": 0, "material": True}
        ],
    }


def _synthetic_two_turn_script() -> dict[str, Any]:
    """The two-turn script as the builder's: the clinician on voice slot 0."""
    return {**_two_turn_script(), "conditions": {"voice_slots": {"clinician": 0, "patient": 1}}}


def _enrolment(frequency: float = 220.0) -> speaker_eval.EnrolmentInputs:
    """An in-memory enrolment of a tone (``FrequencyEmbedder``: 220 Hz is the
    clinician's tone, 2600 Hz the patient's)."""
    return speaker_eval.enrolment_inputs(
        _tone(2.0, frequency), FrequencyEmbedder(), amplitude_vad
    )


class TestFindEncounters:
    def test_complete_and_incomplete_stems(self, tmp_path: Path) -> None:
        for name in ("a.json", "a.wav", "a.txt", "b.json", "b.wav", "c.txt", "notes.md"):
            (tmp_path / name).write_bytes(b"")
        complete, incomplete = find_encounters(tmp_path)
        assert [files.encounter_id for files in complete] == ["a"]
        assert incomplete == [("b", "missing .txt"), ("c", "missing .json, .wav")]

    def test_a_file_not_named_as_an_id_is_reported_without_its_name(
        self, tmp_path: Path
    ) -> None:
        """Round 11 MED-006: such a stem could not be reported as an outcome
        (it would crash the run), and its name could be anything — a
        person's name included — so it is counted, never printed."""
        for name in ("syn-001.json", "syn-001.wav", "syn-001.txt", "Margaret Example.wav",
                     "Margaret Example.txt", "SYN-002.json"):
            (tmp_path / name).write_bytes(b"")
        complete, incomplete = find_encounters(tmp_path)
        assert [files.encounter_id for files in complete] == ["syn-001"]
        ((name, problem),) = incomplete
        assert name == validation.UNNAMED_ENCOUNTER
        assert problem.startswith("3 file(s) skipped")
        assert "Margaret" not in name + problem

    def test_a_measure_speakers_folder_loads_once_its_json_is_added(self, tmp_path: Path) -> None:
        """A folder made for ``measure-speakers.py`` (a 16 kHz WAV and its
        Audacity label track) is a set folder once the script is added, with
        nothing else changed."""
        _write_wav(tmp_path / "syn-001.wav", TWO_TURNS_PCM)
        (tmp_path / "syn-001.txt").write_text(TWO_TURNS_LABELS, encoding="utf-8")
        pairs, unpaired = speaker_eval.find_recording_pairs(tmp_path)
        assert len(pairs) == 1 and unpaired == []
        assert find_encounters(tmp_path) == ([], [("syn-001", "missing .json")])
        _write_script(tmp_path, _two_turn_script())
        (files,), incomplete = find_encounters(tmp_path)
        assert incomplete == []
        assert load_script(files.script).encounter_id == "syn-001"
        assert parse_audacity_labels(files.labels.read_text(encoding="utf-8")).labels == (
            "clinician",
            "patient",
        )
        assert speaker_eval.read_wav_pcm(files.wav) == TWO_TURNS_PCM

    def test_the_enrolment_folder_is_never_an_encounter(self, tmp_path: Path) -> None:
        """D11: the builder's ``enrolment/`` subfolder is skipped (a folder,
        not a set file) - never an incomplete or unnamed encounter."""
        folder = _set_folder(tmp_path / "set", script=_synthetic_two_turn_script())
        (folder / validation.ENROLMENT_DIRNAME).mkdir()
        _write_wav(folder / validation.ENROLMENT_DIRNAME / "slot-0.wav", _tone(2.0, 220.0))
        complete, incomplete = find_encounters(folder)
        assert [files.encounter_id for files in complete] == ["syn-001"]
        assert incomplete == []


# ---------------------------------------------------------------------------
# Task 2.4: the runner
# ---------------------------------------------------------------------------


def amplitude_vad(frame: bytes) -> float:
    samples = struct.unpack(f"<{len(frame) // 2}h", frame)
    return 0.95 if max(abs(s) for s in samples) > 1000 else 0.02


class _ScriptedProvider:
    """One packed window holds both turns (the gap is under the 3 s break):
    the window starts at the first tone, so the clinician's words sit at
    0.2-1.2 s and the patient's at 2.7-3.8 s of it."""

    model_name = "scripted"
    CLINICIAN = "On examination the left knee is tender."
    PATIENT = "It hurts when I walk."

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        words: list[TranscribedWord] = []
        for text, start, end in ((self.CLINICIAN, 0.2, 1.2), (self.PATIENT, 2.7, 3.8)):
            tokens = text.split()
            step = (end - start) / len(tokens)
            words += [
                TranscribedWord(token, start + i * step, start + (i + 1) * step, 0.95)
                for i, token in enumerate(tokens)
            ]
        return words


class _RaisingProvider:
    model_name = "raising"

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        raise RuntimeError("provider failed")


class _QuoteEverything:
    """A fake note provider: every utterance quoted into the presenting
    complaint (not clinician-owned), whatever the cues."""

    provider_name = "quote-everything"

    def generate_sections(self, request: NoteRequest) -> tuple[GeneratedSection, ...]:
        assertions = []
        for utterance in request.transcript_utterances:
            assertion = whole_utterance_assertion(
                f"q{utterance.segment_index:04d}",
                "presenting_complaint",
                segment_index=utterance.segment_index,
                speaker=utterance.speaker,
                words=utterance.transcript_words,
            )
            if assertion is not None:
                assertions.append(assertion)
        if not assertions:
            return ()
        return (GeneratedSection(section_key="presenting_complaint",
                                 note_assertions=tuple(assertions)),)


class _ProseResult:
    passed, failed, errored = 1, 2, 0
    reason: str | None = None


class _ProseUnavailable:
    passed, failed, errored = 0, 0, 0
    reason = "the language model could not be loaded"


def _temp_stores() -> set[Path]:
    """The harness stores in this test's private temp folder (``_private_temp``)."""
    return {
        path
        for path in Path(tempfile.gettempdir()).iterdir()
        if path.name.startswith(TEMP_DIR_PREFIX)
    }


def _inputs(tmp_path: Path, provider: Any = None, **overrides: Any) -> HarnessInputs:
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    values: dict[str, Any] = {
        "provider": provider if provider is not None else _ScriptedProvider(),
        "frame_probability": amplitude_vad,
        "config": load_note_config(config_dir),
        "note_provider_factory": lambda config: _QuoteEverything(),
        # The two-turn script is a recorded one (no conditions): runs 1-5's
        # reading. ``TestEnrolledAttribution`` runs the default.
        "attribution": "clustering",
    }
    values.update(overrides)
    return HarnessInputs(**values)


@windows_only
class TestRunner:
    def test_a_measured_encounter_and_its_report(self, tmp_path: Path) -> None:
        pytest.importorskip("numpy")
        encounters, _ = find_encounters(_set_folder(tmp_path / "set"))
        before = _temp_stores()
        lines: list[str] = []
        (outcome,) = run_encounters(encounters, _inputs(tmp_path), progress=lines.append)
        assert _temp_stores() == before  # the temporary store is gone
        assert lines == ["[run ] syn-001"]
        assert outcome.status == "measured" and outcome.segment_count == 2
        assert outcome.suspect_segments == 0  # each turn is one rate signal at most (D3)
        metrics = outcome.metrics
        assert metrics is not None
        assert metrics.words.edit_distance == 0 and metrics.words.reference_tokens == 12
        assert [fact.verdict for fact in metrics.facts] == ["correct"]
        assert metrics.transcript_lines == 2
        assert validation.rule_failures(OPTION_A, outcome) == ()
        info = validation.RunInfo("medium", False, "silero", None, "a" * 40, "b" * 64)
        report = render_report([outcome], OPTION_A, info)
        assert "rule `option-a-proposed` - PASS" in report
        assert "| syn-001 | measured | 2 | 12 | 0.000 |" in report
        assert "| syn-001 | 0 | laterality | yes | correct | no | - | no | no |" in report
        for text in ("examination", "tender", "hurts", "walk", "knee"):
            assert text not in report  # no transcript or script text

    def test_the_suspect_count_is_the_transcripts_own(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review round 5 LOW-004: the outcome and its report cell carry
        ``suspect_segment_count`` of the transcript the run made — the guard
        is not wired before Phase 4, so the count is stood in for."""
        pytest.importorskip("numpy")
        counted: list[int] = []

        def count(document: Any) -> int:
            counted.append(len(document.transcript_segments))
            return 7

        monkeypatch.setattr(validation, "suspect_segment_count", count)
        encounters, _ = find_encounters(_set_folder(tmp_path / "set"))
        (outcome,) = run_encounters(encounters, _inputs(tmp_path), progress=lambda line: None)
        assert outcome.suspect_segments == 7 and counted == [2]
        info = validation.RunInfo("medium", False, "silero", None, "a" * 40, "b" * 64)
        report = render_report([outcome], OPTION_A, info)
        row = next(line for line in report.splitlines() if line.startswith("| syn-001 | measured"))
        assert row.endswith("| 7 | 0.0 | 0.0 | - | PASS |")

    def test_the_prose_stage_counts_are_reported(self, tmp_path: Path) -> None:
        pytest.importorskip("numpy")
        encounters, _ = find_encounters(_set_folder(tmp_path / "set"))
        seen: list[Any] = []

        def stage(note: Any, /, **kwargs: Any) -> _ProseResult:
            seen.append(note)
            return _ProseResult()

        inputs = _inputs(tmp_path, prose_stage=stage)
        (outcome,) = run_encounters(encounters, inputs, progress=lambda line: None)
        assert outcome.prose == validation.ProseCounts(1, 2, 0)
        assert len(seen) == 1

    def test_a_prose_stage_that_could_not_run_fails_the_run(self, tmp_path: Path) -> None:
        """Round 11 MED-007: a stage that never ran (the model missing or not
        loading) is reported as unavailable and fails the run, never as a
        clean 0/0/0."""
        pytest.importorskip("numpy")
        encounters, _ = find_encounters(_set_folder(tmp_path / "set"))
        inputs = _inputs(tmp_path, prose_stage=lambda note, **kwargs: _ProseUnavailable())
        (outcome,) = run_encounters(encounters, inputs, progress=lambda line: None)
        assert outcome.prose == validation.ProseCounts(0, 0, 0, unavailable=True)
        assert validation.rule_failures(OPTION_A, outcome) == ("prose_unavailable",)
        info = validation.RunInfo("medium", False, "silero", "narrative", None, None)
        report = render_report([outcome], OPTION_A, info)
        assert "| unavailable | FAIL: prose_unavailable |" in report
        assert "- FAIL" in report

    def test_the_extractive_provider_is_the_default(self, tmp_path: Path) -> None:
        pytest.importorskip("numpy")
        encounters, _ = find_encounters(_set_folder(tmp_path / "set"))
        inputs = _inputs(tmp_path, note_provider_factory=models.extractive_provider_from_config)
        (outcome,) = run_encounters(encounters, inputs, progress=lambda line: None)
        assert outcome.metrics is not None
        # The shipped cues route both turns ("on examination", "hurts").
        assert outcome.metrics.transcript_lines == 2
        assert HarnessInputs.__dataclass_fields__["note_provider_factory"].default is (
            models.extractive_provider_from_config
        )

    def test_role_unresolved_is_reported_never_skipped(self, tmp_path: Path) -> None:
        pytest.importorskip("numpy")
        encounters, _ = find_encounters(_set_folder(tmp_path / "set", labels=UNRESOLVED_LABELS))
        (outcome,) = run_encounters(encounters, _inputs(tmp_path), progress=lambda line: None)
        assert outcome.status == "role_unresolved"
        assert outcome.metrics is None and outcome.words is not None
        # Invented-text guard D8: a transcript was made, so it is counted.
        assert outcome.suspect_segments == 0
        # Validation-run6 D14: the reference reading, taken first, is kept.
        assert outcome.reference == validation.ReferenceReading(
            frozenset({0}), boundary=None, tail_start=None
        )
        assert validation.rule_failures(OPTION_A, outcome) == ("role_unresolved",)
        assert not validation.run_passed(OPTION_A, [outcome])

    def test_a_provider_error_is_an_error_outcome_and_leaves_no_store(
        self, tmp_path: Path
    ) -> None:
        pytest.importorskip("numpy")
        encounters, _ = find_encounters(_set_folder(tmp_path / "set"))
        before = _temp_stores()
        lines: list[str] = []
        (outcome,) = run_encounters(
            encounters, _inputs(tmp_path, _RaisingProvider()), progress=lines.append
        )
        assert _temp_stores() == before
        assert (outcome.status, outcome.error_type) == ("error", "RuntimeError")
        assert lines[-1] == "[error] syn-001: RuntimeError"  # the type, never the message

    def test_a_teardown_failure_stops_the_run_naming_the_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pytest.importorskip("numpy")
        encounters, _ = find_encounters(_set_folder(tmp_path / "set"))
        real_rmtree = shutil.rmtree

        def keep(*args: object, **kwargs: object) -> None:
            return None

        monkeypatch.setattr(speaker_eval.shutil, "rmtree", keep)
        before = _temp_stores()
        try:
            with pytest.raises(SpeakerEvalError, match="ciphertext") as info:
                run_encounters(encounters, _inputs(tmp_path), progress=lambda line: None)
            (leftover,) = _temp_stores() - before
            assert str(leftover) in str(info.value)
        finally:
            for path in _temp_stores() - before:
                real_rmtree(path)

    def test_a_refused_wav_is_an_error_before_any_store(self, tmp_path: Path) -> None:
        folder = _set_folder(tmp_path / "set")
        (folder / "syn-001.wav").write_bytes(b"not a wav")
        encounters, _ = find_encounters(folder)
        before = _temp_stores()
        (outcome,) = run_encounters(encounters, _inputs(tmp_path), progress=lambda line: None)
        assert _temp_stores() == before
        assert (outcome.status, outcome.error_type) == ("error", "WavFormatError")

    def test_a_refused_label_track_is_reported_by_type_only(self, tmp_path: Path) -> None:
        """Round 11 LOW-007: a label-track refusal can quote the labels typed
        in the file, so only its type is printed."""
        folder = _set_folder(tmp_path / "set", labels="1.0\t2.5\tDr Example\n")
        encounters, _ = find_encounters(folder)
        lines: list[str] = []
        (outcome,) = run_encounters(encounters, _inputs(tmp_path), progress=lines.append)
        assert (outcome.status, outcome.error_type) == ("error", "LabelTrackError")
        assert lines[-1].startswith("[error] syn-001: LabelTrackError: the label track")
        assert "example" not in "\n".join(lines).lower()

    def test_a_refused_script_is_an_error(self, tmp_path: Path) -> None:
        folder = _set_folder(tmp_path / "set")
        (folder / "syn-001.json").write_text("{}", encoding="utf-8")
        encounters, _ = find_encounters(folder)
        lines: list[str] = []
        (outcome,) = run_encounters(encounters, _inputs(tmp_path), progress=lines.append)
        assert (outcome.status, outcome.error_type) == ("error", "ScriptError")
        assert lines[-1].startswith("[error] syn-001.json:")

    def test_a_next_patient_script_with_no_tail_row_is_an_error_before_any_store(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Validation-run6 D8/D14: a script carrying ``end_and_new_patient``
        with no ``REFERENCE_TAIL_STARTS`` row is a harness error, never an
        R3 — raised by the reference reading, which runs before the label
        track, the WAV or any store."""
        monkeypatch.setattr(validation, "REFERENCE_TAIL_STARTS", {})
        script = {**_two_turn_script(), "axes": ["laterality", "end_and_new_patient"]}
        encounters, _ = find_encounters(_set_folder(tmp_path / "set", script=script))
        before = _temp_stores()
        lines: list[str] = []
        (outcome,) = run_encounters(encounters, _inputs(tmp_path), progress=lines.append)
        assert _temp_stores() == before
        assert (outcome.status, outcome.error_type) == ("error", "ResidueTableError")
        assert lines[-1] == "[error] syn-001: ResidueTableError"

    def test_an_error_type_no_outcome_can_hold_is_reported_as_exception(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review round 22: an over-long type name is reported as
        ``Exception`` — never a second raise inside the handler, whose
        traceback would chain the first one's message."""
        unreportable = type("Unreportable" + "X" * 64, (Exception,), {})

        def raising(*args: object, **kwargs: object) -> None:
            raise unreportable("the note said something")

        monkeypatch.setattr(validation, "evaluate_encounter", raising)
        encounters, _ = find_encounters(_set_folder(tmp_path / "set"))
        lines: list[str] = []
        (outcome,) = run_encounters(encounters, _inputs(tmp_path), progress=lines.append)
        assert (outcome.status, outcome.error_type) == ("error", "Exception")
        assert lines[-1] == "[error] syn-001: Exception"


class TestRound26Bounds:
    """Review round 26 (H3): the two other whole-file reads are capped, and
    an error line that cannot be written chains nothing."""

    def test_an_oversized_label_track_is_refused_before_any_store(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(validation, "MAX_LABEL_TRACK_BYTES", 8)
        encounters, _ = find_encounters(_set_folder(tmp_path / "set"))
        before = _temp_stores()
        lines: list[str] = []
        (outcome,) = run_encounters(encounters, _inputs(tmp_path), progress=lines.append)
        assert _temp_stores() == before
        assert (outcome.status, outcome.error_type) == ("error", "LabelTrackError")
        assert lines[-1].startswith("[error] syn-001: LabelTrackError: the label track was refused")

    def test_an_oversized_rule_file_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(validation, "MAX_RULE_BYTES", 8)
        with pytest.raises(validation.RuleError, match="^the rule file: larger than 8 bytes$"):
            validation.load_pass_rule(_rule_file(tmp_path))

    def test_an_error_line_that_cannot_be_written_chains_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def raising(*args: object, **kwargs: object) -> None:
            raise ValueError("the note said something")

        def progress(line: str) -> None:
            if line.startswith("[error]"):
                raise BrokenPipeError

        monkeypatch.setattr(validation, "evaluate_encounter", raising)
        encounters, _ = find_encounters(_set_folder(tmp_path / "set"))
        with pytest.raises(BrokenPipeError) as info:
            run_encounters(encounters, _inputs(tmp_path), progress=progress)
        assert info.value.__context__ is None  # the pipeline's message is not chained


class TestClinicianSpeaker:
    def test_the_majority_clinician_cluster(self) -> None:

        def segment(start: float, end: float, speaker: str) -> TranscriptSegment:
            return TranscriptSegment(
                start_seconds=start, end_seconds=end, speaker=speaker, transcript_words=()
            )

        document = TranscriptDocument(
            session_id="d" * 32,
            created_at=validation._default_now(),
            model_name="mock",
            sample_rate=SAMPLE_RATE,
            transcript_segments=(
                segment(0.0, 2.0, "speaker_1"),
                segment(3.0, 5.0, "speaker_2"),
                segment(6.0, 7.0, "speaker_1"),
            ),
        )
        track = parse_audacity_labels("0.0\t2.0\tpatient\n3.0\t5.0\tclinician\n6.0\t7.0\tpatient\n")
        assert validation.clinician_speaker(document, track) == "speaker_2"
        tied = parse_audacity_labels("0.0\t2.0\tclinician\n3.0\t5.0\tclinician\n")
        assert validation.clinician_speaker(document, tied) is None
        nobody = parse_audacity_labels("0.0\t0.5\tclinician\n0.6\t9.0\tpatient\n")
        assert validation.clinician_speaker(document, nobody) is None


def _document(
    *segments: tuple[float, float, str], enrolled: str | None = "speaker_1"
) -> TranscriptDocument:
    return TranscriptDocument(
        session_id="d" * 32,
        created_at=validation._default_now(),
        model_name="mock",
        sample_rate=SAMPLE_RATE,
        transcript_segments=tuple(
            TranscriptSegment(
                start_seconds=start,
                end_seconds=end,
                speaker=speaker,
                transcript_words=(
                    TranscriptWord(
                        word_text="word",
                        start_seconds=start,
                        end_seconds=end,
                        probability=0.9,
                        uncertain=False,
                    ),
                ),
            )
            for start, end, speaker in segments
        ),
        enrolled_speaker=enrolled,
        enrolment_similarity=None if enrolled is None else 0.9,
        speaker_model_id=None if enrolled is None else "fake-speaker",
    )


class TestEnrolledClinician:
    """Metric amendment 2026-10-23 (D11): the enrolled speaker confirmed by
    the label track, on hand-built documents."""

    def test_the_enrolled_speaker_confirmed_by_the_track(self) -> None:
        document = _document((0.0, 2.0, "speaker_1"), (3.0, 5.0, "speaker_2"))
        track = parse_audacity_labels("0.0\t2.0\tclinician\n3.0\t5.0\tpatient\n")
        assert validation.enrolled_clinician(document, track) == "speaker_1"
        assert validation.attribution_seconds(document, track, "speaker_1") == (0.0, 0.0)

    def test_an_enrolled_speaker_whose_majority_is_not_the_clinician(self) -> None:
        document = _document((0.0, 2.0, "speaker_1"), (3.0, 5.0, "speaker_2"))
        track = parse_audacity_labels("0.0\t2.0\tpatient\n3.0\t5.0\tclinician\n")
        assert validation.clinician_speaker(document, track) == "speaker_2"
        assert validation.enrolled_clinician(document, track) is None

    def test_no_enrolled_speaker_is_role_unresolved(self) -> None:
        document = _document((0.0, 2.0, "speaker_1"), (3.0, 5.0, "speaker_2"), enrolled=None)
        track = parse_audacity_labels("0.0\t2.0\tclinician\n3.0\t5.0\tpatient\n")
        assert validation.clinician_speaker(document, track) == "speaker_1"
        assert validation.enrolled_clinician(document, track) is None

    def test_a_tie_is_role_unresolved(self) -> None:
        document = _document((0.0, 2.0, "speaker_1"), (2.0, 4.0, "speaker_1"))
        track = parse_audacity_labels("0.0\t2.0\tclinician\n2.0\t4.0\tpatient\n")
        assert validation.enrolled_clinician(document, track) is None

    def test_whole_segment_weighting_never_confirms_a_minority(self) -> None:
        """Peer round 8 PR-MED-027: one 10 s segment at 5.1 / 4.9 seconds
        clinician / patient and a 9 s patient segment in the enrolled
        cluster. ``clinician_speaker`` totals whole segments under their
        winning label (10 vs 9) and names the cluster - runs 1-5's reading,
        unchanged - while its actual overlaps are 5.1 vs 13.9: on the
        enrolled path, role unresolved."""
        document = _document(
            (0.0, 10.0, "speaker_1"), (10.0, 19.0, "speaker_1"), (20.0, 21.0, "speaker_2")
        )
        track = parse_audacity_labels(
            "0.0\t5.1\tclinician\n5.1\t19.0\tpatient\n20.0\t21.0\tpatient\n"
        )
        assert validation.clinician_speaker(document, track) == "speaker_1"
        assert validation.overlap_by_label(document.transcript_segments[0], track) == (
            pytest.approx({"clinician": 5.1, "patient": 4.9})
        )
        assert validation.enrolled_clinician(document, track) is None

    def test_both_seconds_columns_on_a_mixed_cluster(self) -> None:
        """Peer round 7 PR-MED-025: every segment matched the enrolment, so
        the enrolled cluster holds the patient's turn too - confirmed (a
        clinician majority), the patient's seconds in the second column; a
        clinician turn the enrolment missed is in the first."""
        document = _document(
            (0.0, 6.0, "speaker_1"), (7.0, 9.0, "speaker_1"), (10.0, 11.5, "speaker_2")
        )
        track = parse_audacity_labels(
            "0.0\t6.0\tclinician\n7.0\t9.0\tpatient\n10.0\t11.5\tclinician\n"
        )
        assert validation.enrolled_clinician(document, track) == "speaker_1"
        assert validation.attribution_seconds(document, track, "speaker_1") == (1.5, 2.0)


# The body of the report (rows on) that ``c5f3179`` — the commit before
# D11 — rendered for ``TestEnrolledAttribution``'s set under the
# clustering path (peer round 17 PR-LOW-014; taken by loading that commit's
# ``validation.py`` beside the current one on the same fake inputs).
_CLUSTERING_BASELINE_C5F3179: tuple[str, ...] = (
    "| syn-001 | measured | 2 | 12 | 0.000 | 0 | 0 | 0 | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 "
    "| 0 | 0 | 0 | 0 | 0 | 0 | - | PASS |",
    "| TOTAL | 1 measured | - | 12 | 0.000 | 0 | 0 | 0 | - | - | 1 | 1 | 0 | 0 | 0 | 0 | 0 "
    "| 0 | 0 | 0 | 0 | 0 | 0 | - | PASS |",
    "",
    "### Checker warnings (code = count)",
    "",
    "- syn-001: none",
    "",
    "### Facts",
    "",
    "| Encounter | Fact | Kind | Material | Verdict | Warned | Uncertainty surfaced "
    "| Not transcribed | Ambiguous |",
    "|---|---|---|---|---|---|---|---|---|",
    "| syn-001 | 0 | laterality | yes | correct | no | - | no | no |",
)


@windows_only
class TestEnrolledAttribution:
    """D11 through the runner: the default attribution enrols the script's
    clinician voice slot and judges the enrolled document."""

    def _set(self, tmp_path: Path) -> list[Any]:
        folder = _set_folder(tmp_path / "set", script=_synthetic_two_turn_script())
        encounters, _ = find_encounters(folder)
        return encounters

    def test_the_enrolled_speaker_confirmed_is_measured(self, tmp_path: Path) -> None:
        pytest.importorskip("numpy")
        encounters = self._set(tmp_path)
        before = _temp_stores()
        inputs = _inputs(tmp_path, attribution="enrolment", enrolments={0: _enrolment()})
        (outcome,) = run_encounters(encounters, inputs, progress=lambda line: None)
        assert _temp_stores() == before
        assert outcome.status == "measured" and outcome.segment_count == 2
        assert outcome.metrics is not None
        assert outcome.metrics.words.edit_distance == 0  # the replayed words
        assert [fact.verdict for fact in outcome.metrics.facts] == ["correct"]
        assert (outcome.clinician_as_other_seconds, outcome.other_as_clinician_seconds) == (
            0.0,
            0.0,
        )
        report = render_report(
            [outcome], OPTION_A, validation.RunInfo("medium", False, "silero", None, None, None)
        )
        assert "Attribution `enrolment`, metric amendment 2026-10-23" in report
        assert "| 0 | 0.0 | 0.0 | - | PASS |" in report

    def test_clustering_ignores_the_enrolments_and_reads_as_runs_1_to_5(
        self, tmp_path: Path
    ) -> None:
        """``--attribution clustering`` is today's path: the same outcome on
        the same inputs whatever enrolment is supplied (here the patient's)."""
        pytest.importorskip("numpy")
        encounters = self._set(tmp_path)
        plain = run_encounters(encounters, _inputs(tmp_path), progress=lambda line: None)
        given = run_encounters(
            encounters,
            _inputs(tmp_path, enrolments={0: _enrolment(2600.0)}),
            progress=lambda line: None,
        )
        assert plain == given
        assert plain[0].status == "measured"
        # Peer round 17 PR-LOW-014: against a FIXED baseline, not the current
        # code — the report's rows and fact table as ``c5f3179`` (before D11)
        # rendered these inputs, the two new seconds cells removed; and since
        # validation-run6 D7/D13 and D8 the 0.3.3 silent column (a 0 here)
        # and the facts table's residue-class cell (a ``-``) removed too.
        report = render_report(
            plain,
            OPTION_A,
            validation.RunInfo("medium", False, "silero", None, None, None, "clustering"),
        ).splitlines()
        rows = report[6:8]
        for index, row in enumerate(rows):
            cells = row.split(" | ")
            assert cells[24:26] == ["0.0", "0.0"]
            del cells[24:26]
            assert cells[16] == "0"
            del cells[16]
            rows[index] = " | ".join(cells)
        facts = report[8:]
        header, separator, fact_row = facts[-3:]
        assert header.endswith("| Ambiguous | Residue class |")
        assert separator == "|" + "---|" * 10
        assert fact_row.endswith("| no | - |")
        facts[-3:] = [
            header.removesuffix(" Residue class |"),
            "|" + "---|" * 9,
            fact_row.removesuffix(" - |"),
        ]
        assert [*rows, *facts] == list(_CLUSTERING_BASELINE_C5F3179)

    def test_an_enrolment_that_matches_the_patient_is_role_unresolved(
        self, tmp_path: Path
    ) -> None:
        pytest.importorskip("numpy")
        encounters = self._set(tmp_path)
        inputs = _inputs(tmp_path, attribution="enrolment", enrolments={0: _enrolment(2600.0)})
        (outcome,) = run_encounters(encounters, inputs, progress=lambda line: None)
        assert outcome.status == "role_unresolved"
        assert outcome.metrics is None and outcome.words is not None
        assert outcome.clinician_as_other_seconds is None
        assert outcome.other_as_clinician_seconds is None

    @pytest.mark.parametrize("recorded", [True, False])
    def test_no_enrolment_for_the_script_is_an_error_before_any_store(
        self, tmp_path: Path, recorded: bool
    ) -> None:
        """A recorded script (no voice slot) or a slot without an enrolment:
        the fixed refusal, before any store exists."""
        script = _two_turn_script() if recorded else _synthetic_two_turn_script()
        encounters, _ = find_encounters(_set_folder(tmp_path / "set", script=script))
        before = _temp_stores()
        lines: list[str] = []
        inputs = _inputs(tmp_path, attribution="enrolment", enrolments={1: _enrolment()})
        (outcome,) = run_encounters(encounters, inputs, progress=lines.append)
        assert _temp_stores() == before
        assert (outcome.status, outcome.error_type) == ("error", "EnrolmentMissingError")
        assert lines[-1] == (
            "[error] syn-001: EnrolmentMissingError: no enrolment for this script's clinician "
            "voice - a recorded script is measured with --attribution clustering"
        )

    def test_the_enrolments_are_never_rendered(self) -> None:
        inputs = HarnessInputs(
            provider=_ScriptedProvider(),
            frame_probability=amplitude_vad,
            config=None,  # type: ignore[arg-type]
            enrolments={0: object()},  # type: ignore[dict-item]
        )
        assert "enrolments" not in repr(inputs)
        assert inputs.attribution == "enrolment"  # the default (D11)


# ---------------------------------------------------------------------------
# Task 2.7: run-validation.py and main
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


def _rule_file(tmp_path: Path) -> Path:
    path = tmp_path / "rule.json"
    path.write_text(json.dumps({"schema_version": 1, "rule_name": "test-rule"}), encoding="utf-8")
    return path


def _rule_v2_file(tmp_path: Path) -> Path:
    """``_rule_file``'s path rewritten as ``_rule_v2()`` (validation-run6
    D8) — called after ``_argv``, which writes the schema-1 file."""
    path = tmp_path / "rule.json"
    path.write_text(_rule_v2().model_dump_json(), encoding="utf-8")
    return path


def _argv(tmp_path: Path, *extra: str, config: Path | None = None) -> list[str]:
    set_dir = tmp_path / "set"
    set_dir.mkdir(exist_ok=True)
    if config is None:
        config = tmp_path / "config"
        config.mkdir(exist_ok=True)
    return [str(set_dir), "--config", str(config), "--rule", str(_rule_file(tmp_path)), *extra]


class TestRunValidationMain:
    @pytest.fixture(autouse=True)
    def _no_models_built(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # The harness runs only on the developer build; conftest pins every
        # test to production, so these tests pin the dev channel through the
        # same seam (and the production refusal is tested through it too).
        use_channel(monkeypatch, "dev")
        monkeypatch.setattr(validation, "SileroVad", _NeverBuilt)
        monkeypatch.setattr(validation, "WhisperSpeechProvider", _NeverBuilt)

    def test_the_launcher_is_thin_and_prints_usage_without_models(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        launcher = _load_launcher("run-validation.py")
        assert launcher.main is validation.main
        with pytest.raises(SystemExit) as info:
            launcher.main(["--help"])
        assert info.value.code == 0
        assert "usage:" in capsys.readouterr().out

    def test_an_empty_models_folder_is_refused_by_name(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert validation.main(_argv(tmp_path)) == 2
        out = capsys.readouterr().out
        assert "[refused] no Whisper model is installed in" in out
        assert str(install_layout.models_root()) in out

    def test_a_packaged_build_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        use_channel(monkeypatch, "production")
        assert validation.main(_argv(tmp_path)) == 2
        assert "only on the developer build" in capsys.readouterr().out

    def test_the_offline_environment_is_applied_first(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
        assert validation.main(_argv(tmp_path)) == 2  # refused later, at the models
        assert os.environ.get("HF_HUB_OFFLINE") == "1"

    @pytest.mark.parametrize("channel", ["production", "dev"])
    def test_the_apps_own_config_folder_is_refused(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        channel: install_layout.Channel,
    ) -> None:
        """Both channels' folders (round 11 LOW-020) — the production one is
        the clinic app's own config."""
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
        own = install_layout.data_root(channel) / "config"
        own.mkdir(parents=True)
        assert validation.main(_argv(tmp_path, config=own)) == 2
        out = capsys.readouterr().out
        assert "the app's own config folder" in out
        assert "never a copy" in out

    @pytest.mark.parametrize(
        ("filename", "content"),
        [
            ("section_cues.learned.json", "{}"),
            ("autofill_rules.learned.json", "{}"),
            (
                "autofill_rules.json",
                json.dumps(
                    {
                        "schema_version": 1,
                        "autofill_rules": [
                            {
                                "rule_id": "learned-01J0000000000000000000000A",
                                "section_key": "treatment_performed",
                                "trigger_phrase": "usual taping",
                                "expansion": ["Ankle taped."],
                            }
                        ],
                    }
                ),
            ),
        ],
    )
    def test_a_copy_of_the_apps_learned_content_is_refused(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], filename: str, content: str
    ) -> None:
        """Round 11 MED-008: ``confirm_all`` would confirm a learned rule's
        proposals, so a folder carrying the app's learned content is refused."""
        config = tmp_path / "copied"
        config.mkdir()
        (config / filename).write_text(content, encoding="utf-8")
        assert validation.main(_argv(tmp_path, config=config)) == 2
        assert "learned phrases or rules" in capsys.readouterr().out

    def test_a_malformed_config_is_refused_by_type_only(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Round 11 LOW-001: the loader's detail reproduces the rejected file
        text, so only the error's type is printed."""
        config = tmp_path / "config"
        config.mkdir()
        (config / "autofill_rules.json").write_text(
            '{"schema_version": 1, "autofill_rules": [{"rule_id": "x", "Margaret": 1}]}',
            encoding="utf-8",
        )
        assert validation.main(_argv(tmp_path, config=config)) == 2
        out = capsys.readouterr().out
        assert "NoteConfigInvalidError" in out
        assert "Margaret" not in out

    def test_prose_without_the_language_model_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(validation, "resolve_whisper_model", lambda: "medium")
        monkeypatch.setattr(validation, "whisper_model_available", lambda name: True)
        monkeypatch.setattr(validation, "vad_model_available", lambda: True)
        assert validation.main(_argv(tmp_path, "--prose")) == 2
        assert "[refused] --prose: the language model is not installed" in (
            capsys.readouterr().out
        )

    def test_an_unknown_template_profile_is_refused_before_any_model(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Round 12 LOW-009: refused at the config, not as an error on every
        encounter after a full transcription. The other direction — the
        config's only profile bound by default — is every other test here
        reaching the models refusals."""
        assert validation.main(_argv(tmp_path, "--template-profile", "no-such-profile")) == 2
        out = capsys.readouterr().out
        assert "no template profile can be bound (TemplateProfileUnboundError)" in out
        assert "Whisper" not in out

    def test_a_small_fallback_is_refused_unless_allowed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(validation, "resolve_whisper_model", lambda: "small")
        monkeypatch.setattr(validation, "whisper_model_available", lambda name: True)
        assert validation.main(_argv(tmp_path)) == 2
        assert "--allow-small" in capsys.readouterr().out
        # Allowed: the next refusal is the VAD's (still before any model).
        assert validation.main(_argv(tmp_path, "--allow-small")) == 2
        assert "silero VAD model is not installed" in capsys.readouterr().out

    def test_a_bad_rule_is_refused(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        argv = _argv(tmp_path)
        _rule_file(tmp_path).write_text("{}", encoding="utf-8")
        assert validation.main(argv) == 2
        out = capsys.readouterr().out
        assert "[refused] the rule file: " in out
        assert "rule.json" not in out  # peer round 27 (PR-HIGH-068): never its name

    def test_set_is_refused_with_a_schema_1_rule(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Validation-run6 D17: a schema-1 rule has no sets, so ``--set`` is a
        refusal, not ignored."""
        assert validation.main(_argv(tmp_path, "--set", "scripts")) == 2
        out = capsys.readouterr().out
        assert "[refused] --set is taken only with a schema-2 rule" in out
        assert "Whisper" not in out

    @pytest.mark.parametrize("given", [None, "Margaret"])
    def test_a_schema_2_rule_needs_one_of_its_sets(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], given: str | None
    ) -> None:
        """D17: missing, or a name the rule does not hold — refused before
        any model, naming the rule's sets and never the typed name."""
        argv = _argv(tmp_path) if given is None else _argv(tmp_path, "--set", given)
        _rule_v2_file(tmp_path)
        assert validation.main(argv) == 2
        out = capsys.readouterr().out
        assert "[refused] a schema-2 rule needs --set naming one of its sets: heldout, " in out
        assert "heldout-3, scripts" in out
        assert "Margaret" not in out
        assert "Whisper" not in out

    def test_a_schema_2_rule_and_one_of_its_sets_go_on(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        argv = _argv(tmp_path, "--set", "heldout-3")
        _rule_v2_file(tmp_path)
        assert validation.main(argv) == 2  # refused later, at the models
        assert "[refused] no Whisper model is installed in" in capsys.readouterr().out

    def test_an_interrupted_run_prints_no_traceback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Review round 22: Ctrl+C mid-run is one fixed line and exit 1 — no
        traceback chaining what the pipeline was raising."""

        class _Model:
            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

            def frame_probability(self, frame: bytes) -> float:
                return 0.0

        def interrupted(*args: object, **kwargs: object) -> None:
            raise KeyboardInterrupt

        monkeypatch.setattr(validation, "resolve_whisper_model", lambda: "medium")
        monkeypatch.setattr(validation, "whisper_model_available", lambda name: True)
        monkeypatch.setattr(validation, "vad_model_available", lambda: True)
        monkeypatch.setattr(validation, "SileroVad", _Model)
        monkeypatch.setattr(validation, "WhisperSpeechProvider", _Model)
        monkeypatch.setattr(validation, "run_encounters", interrupted)
        argv = _argv(tmp_path, "--attribution", "clustering")
        _set_folder(tmp_path / "set")
        assert validation.main(argv, repo_root=tmp_path) == 1
        out = capsys.readouterr().out
        assert "[stopped] the run was interrupted" in out
        assert f"{TEMP_DIR_PREFIX}*" in out
        assert tempfile.gettempdir() in out  # round 26: the folder the stores are made in

    @pytest.mark.parametrize("raised", ["error", "interrupt"])
    def test_models_that_cannot_be_loaded_are_refused_by_type(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        raised: str,
    ) -> None:
        """Round 26: a model error's text (its path, the library's message)
        is never printed, and an interrupt while loading prints one line."""
        model_error = type("VadModelError", (Exception,), {})

        def failing(*args: object, **kwargs: object) -> None:
            if raised == "interrupt":
                raise KeyboardInterrupt
            raise model_error("C:/models/silero.onnx: the library said something")

        monkeypatch.setattr(validation, "resolve_whisper_model", lambda: "medium")
        monkeypatch.setattr(validation, "whisper_model_available", lambda name: True)
        monkeypatch.setattr(validation, "vad_model_available", lambda: True)
        monkeypatch.setattr(validation, "SileroVad", failing)
        argv = _argv(tmp_path, "--attribution", "clustering")
        _set_folder(tmp_path / "set")
        code = validation.main(argv, repo_root=tmp_path)
        out = capsys.readouterr().out
        assert "silero.onnx" not in out and "library said" not in out
        if raised == "interrupt":
            assert code == 1
            assert "[stopped] the run was interrupted while the models loaded" in out
        else:
            assert code == 2
            assert "[refused] the models could not be loaded (VadModelError)" in out

    @pytest.mark.parametrize(
        "site",
        [
            "rule",
            "set",
            "config",
            "profile",
            "models",
            "speaker",
            "listing",
            "slot",
            "enrol",
            "custody",
        ],
    )
    def test_a_refusal_that_cannot_be_written_chains_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, site: str
    ) -> None:
        """Peer round 27 (PR-HIGH-066): each of ``main``'s refusals is printed
        after its handler ends, so a closed output pipe chains no handled
        exception — a config error's text reproduces the rejected input, and
        a custody fault carries the pipeline's exception as its context."""

        class _Model:
            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

            def frame_probability(self, frame: bytes) -> float:
                return 0.0

        def custody_fault(*args: object, **kwargs: object) -> None:
            try:
                raise ValueError("the note said something")
            except ValueError:
                raise SpeakerEvalError("a temporary store was not shown gone") from None

        def unlistable(*args: object, **kwargs: object) -> None:
            raise OSError("the note said something")

        def broken_print(*args: object, **kwargs: object) -> None:
            if args and str(args[0]).startswith(("[refused]", "[custody]")):
                raise BrokenPipeError

        monkeypatch.setattr(validation, "resolve_whisper_model", lambda: "medium")
        monkeypatch.setattr(validation, "whisper_model_available", lambda name: True)
        monkeypatch.setattr(validation, "vad_model_available", lambda: True)
        monkeypatch.setattr(validation, "SileroVad", _Model)
        monkeypatch.setattr(validation, "WhisperSpeechProvider", _Model)
        monkeypatch.setattr(validation, "run_encounters", custody_fault)
        enrolled = site in ("speaker", "slot", "enrol")
        argv = _argv(tmp_path) if enrolled else _argv(tmp_path, "--attribution", "clustering")
        _set_folder(tmp_path / "set", script=_synthetic_two_turn_script())
        if site != "speaker":
            monkeypatch.setattr(validation, "speaker_model_available", lambda: True)
        if site == "enrol":
            (tmp_path / "set" / "enrolment").mkdir()
            _write_wav(tmp_path / "set" / "enrolment" / "slot-0.wav", _tone(2.0, 220.0))
            monkeypatch.setattr(validation, "build_speaker_embedder", unlistable)
        if site == "rule":
            _rule_file(tmp_path).write_text("{}", encoding="utf-8")
        elif site == "set":
            _rule_v2_file(tmp_path)  # schema 2 and no --set (validation-run6 D17)
        elif site == "config":
            (tmp_path / "config" / "autofill_rules.json").write_text(
                '{"schema_version": 1, "autofill_rules": [{"rule_id": "x", "Margaret": 1}]}',
                encoding="utf-8",
            )
        elif site == "profile":
            argv = [*argv, "--template-profile", "no-such-profile"]
        elif site == "models":
            monkeypatch.setattr(install_layout, "models_root", unlistable)
        elif site == "listing":
            monkeypatch.setattr(validation, "find_encounters", unlistable)
        monkeypatch.setattr(validation, "print", broken_print, raising=False)
        with pytest.raises(BrokenPipeError) as info:
            validation.main(argv, repo_root=tmp_path)
        assert info.value.__context__ is None

    @windows_only
    def test_a_full_run_with_fake_models(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pytest.importorskip("numpy")

        class _Vad:
            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

            def frame_probability(self, frame: bytes) -> float:
                return amplitude_vad(frame)

        class _Whisper(_ScriptedProvider):
            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

        monkeypatch.setattr(validation, "resolve_whisper_model", lambda: "medium")
        monkeypatch.setattr(validation, "whisper_model_available", lambda name: True)
        monkeypatch.setattr(validation, "vad_model_available", lambda: True)
        monkeypatch.setattr(validation, "SileroVad", _Vad)
        monkeypatch.setattr(validation, "WhisperSpeechProvider", _Whisper)
        argv = _argv(tmp_path, "--attribution", "clustering")
        _set_folder(tmp_path / "set")
        assert validation.main(argv, repo_root=tmp_path) == 0
        out = capsys.readouterr().out
        assert "[run ] syn-001" in out
        assert "- PASS" in out
        assert "commit `unknown`" in out and "manifest SHA-256 `absent`" in out
        assert "Attribution `clustering`" in out
        # A file not named as an encounter id: reported without its name, a
        # set-level error, and the run still completes (round 11 MED-006).
        (tmp_path / "set" / "Margaret Example.wav").write_bytes(b"")
        assert validation.main(argv, repo_root=tmp_path) == 1
        out = capsys.readouterr().out
        assert f"[error] {validation.UNNAMED_ENCOUNTER}: 1 file(s) skipped" in out
        assert "Margaret" not in out
        assert "[run ] syn-001" in out and "- FAIL" in out

    @windows_only
    def test_a_full_run_under_rule_v2_names_its_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Validation-run6 D8, D17 through ``main``: ``--set`` picks the
        rule's row, and the report carries both verdicts and the set layer."""
        pytest.importorskip("numpy")
        _FakeModels.install(monkeypatch)
        argv = _argv(tmp_path, "--attribution", "clustering", "--set", "scripts")
        _rule_v2_file(tmp_path)
        _set_folder(tmp_path / "set")
        assert validation.main(argv, repo_root=tmp_path) == 0
        out = capsys.readouterr().out
        assert "- set `scripts` - rule v2 PASS, rule v1 PASS" in out
        assert "### Residue classes (rule v2, set `scripts`, a gate set)" in out
        assert "- R1: none" in out and "- R3: none" in out


class _FakeModels:
    """``main``'s models as fakes: the amplitude VAD and the scripted
    provider (D11's tests)."""

    class Vad:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def frame_probability(self, frame: bytes) -> float:
            return amplitude_vad(frame)

    class Whisper(_ScriptedProvider):
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

    @classmethod
    def install(cls, monkeypatch: pytest.MonkeyPatch, *, speaker: bool = True) -> None:
        monkeypatch.setattr(validation, "resolve_whisper_model", lambda: "medium")
        monkeypatch.setattr(validation, "whisper_model_available", lambda name: True)
        monkeypatch.setattr(validation, "vad_model_available", lambda: True)
        monkeypatch.setattr(validation, "speaker_model_available", lambda: speaker)
        monkeypatch.setattr(validation, "SileroVad", cls.Vad)
        monkeypatch.setattr(validation, "WhisperSpeechProvider", cls.Whisper)
        monkeypatch.setattr(validation, "build_speaker_embedder", FrequencyEmbedder)


class TestEnrolmentMain:
    """D11's three refusals in ``main``, each before any encounter runs, and
    an enrolled full run with fake models."""

    @pytest.fixture(autouse=True)
    def _dev_channel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        use_channel(monkeypatch, "dev")

    def _enrolled_set(self, tmp_path: Path, enrolment_wav: bytes | None) -> Path:
        folder = _set_folder(tmp_path / "set", script=_synthetic_two_turn_script())
        if enrolment_wav is not None:
            (folder / "enrolment").mkdir()
            (folder / "enrolment" / "slot-0.wav").write_bytes(enrolment_wav)
        return folder

    def test_the_speaker_model_not_installed_is_refused_by_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _FakeModels.install(monkeypatch, speaker=False)
        monkeypatch.setattr(validation, "SileroVad", _NeverBuilt)
        argv = _argv(tmp_path)
        self._enrolled_set(tmp_path, None)
        assert validation.main(argv, repo_root=tmp_path) == 2
        out = capsys.readouterr().out
        assert "[refused] the speaker-embedding model is not installed in" in out
        assert str(install_layout.models_root()) in out
        assert "setup-models.py" in out
        assert "[run ]" not in out
        # Runs 1-5's reading needs no speaker model: it goes on to load the
        # models (here refused by ``_NeverBuilt``).
        assert validation.main([*argv, "--attribution", "clustering"], repo_root=tmp_path) == 2
        out = capsys.readouterr().out
        assert "speaker-embedding" not in out
        assert "[refused] the models could not be loaded" in out

    def test_a_missing_enrolment_wav_is_refused_by_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _FakeModels.install(monkeypatch)
        monkeypatch.setattr(validation, "SileroVad", _NeverBuilt)
        argv = _argv(tmp_path)
        self._enrolled_set(tmp_path, None)
        assert validation.main(argv, repo_root=tmp_path) == 2
        out = capsys.readouterr().out
        assert "lacks slot-0.wav, which the set's scripts need - rebuild the set" in out
        assert "[run ]" not in out

    @pytest.mark.parametrize("problem", ["not a wav", "silence", "model"])
    def test_an_enrolment_that_cannot_be_made_is_refused_by_type(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        problem: str,
    ) -> None:
        pytest.importorskip("numpy")
        _FakeModels.install(monkeypatch)
        argv = _argv(tmp_path)
        folder = self._enrolled_set(
            tmp_path, b"RIFF nonsense" if problem == "not a wav" else b""
        )
        wav = folder / "enrolment" / "slot-0.wav"
        if problem != "not a wav":
            _write_wav(wav, _silence(2.0) if problem == "silence" else _tone(2.0, 220.0))
        if problem == "model":
            model_error = type("SpeakerModelError", (Exception,), {})

            def failing() -> None:
                raise model_error("C:/models/speaker.onnx: the library said something")

            monkeypatch.setattr(validation, "build_speaker_embedder", failing)
        assert validation.main(argv, repo_root=tmp_path) == 2
        out = capsys.readouterr().out
        assert "[run ]" not in out
        assert str(folder) not in out and "library said" not in out
        if problem == "not a wav":
            assert (
                "[refused] slot-0.wav could not be enrolled (WavFormatError): it must be a"
            ) in out
            assert "rebuild the set" in out
        elif problem == "silence":
            assert (
                "[refused] slot-0.wav could not be enrolled (EnrolmentTooShortError): "
                "no speech detected in the enrolment audio"
            ) in out
        else:
            assert "[refused] the speaker model could not be loaded (SpeakerModelError)" in out

    @windows_only
    def test_a_full_enrolled_run_with_fake_models(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pytest.importorskip("numpy")
        _FakeModels.install(monkeypatch)
        argv = _argv(tmp_path)
        folder = self._enrolled_set(tmp_path, b"")
        _write_wav(folder / "enrolment" / "slot-0.wav", _tone(2.0, 220.0))
        assert validation.main(argv, repo_root=tmp_path) == 0
        out = capsys.readouterr().out
        assert "[run ] syn-001" in out and "- PASS" in out
        assert "Attribution `enrolment`, metric amendment 2026-10-23" in out
        assert "| 0.0 | 0.0 | - | PASS |" in out


class TestBuildInformation:
    def test_the_commit_is_read_from_git_files(self, tmp_path: Path) -> None:
        git = tmp_path / ".git"
        (git / "refs" / "heads").mkdir(parents=True)
        (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
        (git / "refs" / "heads" / "main").write_text("a" * 40 + "\n", encoding="ascii")
        assert validation.read_commit(tmp_path) == "a" * 40

    def test_a_packed_ref_and_a_detached_head(self, tmp_path: Path) -> None:
        git = tmp_path / ".git"
        git.mkdir()
        (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
        (git / "packed-refs").write_text(
            "# pack-refs\n" + "b" * 40 + " refs/heads/main\n", encoding="ascii"
        )
        assert validation.read_commit(tmp_path) == "b" * 40
        (git / "HEAD").write_text("c" * 40 + "\n", encoding="ascii")
        assert validation.read_commit(tmp_path) == "c" * 40

    def test_unknown_when_absent(self, tmp_path: Path) -> None:
        assert validation.read_commit(tmp_path) is None
        assert validation.models_manifest_sha256(tmp_path) is None

    def test_the_repository_manifest_is_hashed(self) -> None:
        digest = validation.models_manifest_sha256(REPO)
        assert digest is not None and len(digest) == 64


def _rule_v2() -> PassRule:
    """A schema-2 rule of three sets (validation-run6 D8, D15, D17): two
    gate sets — one requiring uncertainty surfaced, one only reporting it —
    and one reported set."""
    return PassRule.model_validate(
        {
            "schema_version": 2,
            "rule_name": "rule-v2-test",
            "sets": {
                "scripts": {
                    "gate": True,
                    "max_r1_facts": 1,
                    "max_r2_facts": 1,
                    "max_r3_encounters": 1,
                },
                "heldout": {
                    "gate": False,
                    "max_r1_facts": 1,
                    "max_r2_facts": 1,
                    "max_r3_encounters": 1,
                },
                "heldout-3": {
                    "gate": True,
                    "max_r1_facts": 1,
                    "max_r3_encounters": 1,
                    "require_uncertainty_surfaced": False,
                },
            },
        }
    )


def _fact_outcome(fact_index: int = 0, **overrides: Any) -> validation.FactOutcome:
    values: dict[str, Any] = {
        "fact_index": fact_index,
        "kind": "present",
        "material": True,
        "verdict": "correct",
        "warned": False,
        "uncertainty_surfaced": None,
        "not_transcribed": False,
        "ambiguous": False,
    }
    values.update(overrides)
    return validation.FactOutcome(**values)


def _metrics_of(*facts: validation.FactOutcome, **overrides: Any) -> validation.EncounterMetrics:
    values: dict[str, Any] = {
        "words": validation.WordErrors(1, 1, 0),
        "spelling_normalised_words": 0,
        "transcript_lines": 1,
        "config_lines": 0,
        "unsupported_clinical_lines": 0,
        "other_unsupported_words": 0,
        "checker_tally": (),
        "checker_failures": (),
        "checker_failure_count": 0,
        "expected_warnings_absent": (),
        "facts": facts,
    }
    values.update(overrides)
    return validation.EncounterMetrics(**values)


def _measured_outcome(
    encounter_id: str,
    *facts: validation.FactOutcome,
    reference: validation.ReferenceReading | None = None,
    **overrides: Any,
) -> EncounterOutcome:
    metrics = _metrics_of(*facts, **overrides)
    return EncounterOutcome(
        encounter_id,
        "measured",
        segment_count=1,
        words=metrics.words,
        metrics=metrics,
        reference=reference,
    )


def _axis_reading(boundary: int | None, tail_start: int | None) -> validation.ReferenceReading:
    """A next-patient script's reference reading (D14's recorded check)."""
    return validation.ReferenceReading(
        frozenset(), boundary=boundary, tail_start=tail_start, next_patient_axis=True
    )


def _residue_outcomes() -> list[EncounterOutcome]:
    """``syn-001``: one R1 fact (a material wrong one); ``syn-002``: a
    correct fact and one R3 fact on a next-patient script whose reference
    reading found no boundary (tail start 4)."""
    return [
        _measured_outcome(
            "syn-001",
            _fact_outcome(verdict="wrong", residue_r1=True),
            checker_tally=(("clinician_line_omitted", 3),),
        ),
        _measured_outcome(
            "syn-002",
            _fact_outcome(),
            _fact_outcome(1, kind="absent", verdict="wrongly_present", residue_r3=True),
            checker_tally=(("clinician_line_omitted", 2),),
            next_patient_axis=True,
            reference_tail_start=4,
            reference=_axis_reading(None, 4),
        ),
    ]


class TestReport:
    def test_errors_and_set_level_errors_fail_the_run(self) -> None:
        outcomes = [EncounterOutcome("syn-001", "error", "OSError")]
        info = validation.RunInfo("small", True, "silero", "narrative", None, None)
        report = render_report(outcomes, OPTION_A, info, errors=1)
        assert "- FAIL" in report
        assert "(FALLBACK - --allow-small)" in report
        assert "| syn-001 | error (OSError) |" in report
        assert not validation.run_passed(OPTION_A, [])

    def test_every_exported_name_exists(self) -> None:
        assert set(validation.__all__) <= set(dir(validation))

    def test_the_run_1_predicate_column_sits_beside_silent_and_rows_align(self) -> None:
        """Metric amendment 2026-10-09 (note-routing-omissions plan D3,
        PR-LOW-013): one more column after ``Silent omissions``; since the
        metric amendment of 2026-10-11 (D10) one more after ``WER``; since the
        invented-text guard (D8) one more, ``Suspect segments``, before the
        prose cell; since the metric amendment of 2026-10-13 (validation-pass
        plan D7) two more after ``Uncertainty missed``; since the metric
        amendment of 2026-10-23 (validation-run6 plan D11) the two attribution
        seconds after ``Suspect segments``; since the metric amendments of
        2026-10-22 and 2026-10-24 (validation-run6 plan D7, D13) ``Silent
        (0.3.3 predicate)`` after the run-1 column — so the header, the
        separator, a measured row, an unmeasured row and the totals all carry
        28 cells."""
        fact = validation.FactOutcome(
            fact_index=0,
            kind="present",
            material=True,
            verdict="omitted",
            warned=True,
            uncertainty_surfaced=None,
            not_transcribed=False,
            ambiguous=False,
            silently_omitted_v1=True,
        )
        metrics = validation.EncounterMetrics(
            words=validation.WordErrors(4, 4, 0),
            spelling_normalised_words=3,
            transcript_lines=0,
            config_lines=0,
            unsupported_clinical_lines=0,
            other_unsupported_words=0,
            checker_tally=(("high_risk_omission", 1),),
            checker_failures=(),
            checker_failure_count=0,
            expected_warnings_absent=(),
            facts=(fact,),
            hedge_marks_unhedged=3,
        )
        assert (metrics.silent_omissions, metrics.silent_omissions_v1) == (0, 1)
        outcomes = [
            EncounterOutcome(
                "syn-001",
                "measured",
                segment_count=1,
                words=metrics.words,
                metrics=metrics,
                suspect_segments=2,
                clinician_as_other_seconds=1.5,
                other_as_clinician_seconds=2.0,
            ),
            EncounterOutcome("syn-002", "error", "OSError"),
        ]
        info = validation.RunInfo("medium", False, "silero", None, None, None)
        report = render_report(outcomes, OPTION_A, info)
        table = [line for line in report.splitlines() if line.startswith("|")]
        header, separator, measured, unmeasured, total = table[:5]
        assert (
            "| Silent omissions | Silent (run-1 predicate) | Silent (0.3.3 predicate) "
            "| Warned omissions |"
        ) in header
        # Validation-run6 D5, D7 and D13: the header line names the
        # amendments and their dates.
        assert "metric amendment 2026-10-22 (validation-run6 D5)" in report
        assert (
            "metric amendments 2026-10-22 and 2026-10-24 (validation-run6 D7, D13; 0.3.3's "
            "reading: Silent (0.3.3 predicate))"
        ) in report
        # PR-LOW-016 is rule v2's report only (Task 4.3): not cited here.
        assert "a measured zero reads 0" not in report
        # Metric amendment 2026-10-11 (D10): one more column right after WER,
        # and the header line names the amendment.
        assert "| WER | Spelling-normalised words | Unsupported clinical lines |" in header
        assert "canonical spelling, metric amendment 2026-10-11" in report
        # Invented-text guard D8: the suspect-segment count before the prose
        # cell; metric amendment 2026-10-13 (D7): the acoustic-only surfacing
        # and the unhedged-mark count after "Uncertainty missed" — 25 cells in
        # every row, and the header line names the amendment.
        assert (
            "| Checker failures | Suspect segments | Clinician speech labelled other (s) "
            "| Other speech labelled clinician (s) | Prose p/f/e | Rule |"
        ) in header
        # Metric amendment 2026-10-23 (D11): the header line names the
        # attribution policy (``RunInfo``'s default) and the amendment.
        assert (
            "Attribution `enrolment`, metric amendment 2026-10-23: the clinician is the "
            "enrolled speaker"
        ) in report
        assert (
            "| Uncertainty missed | Surfaced (acoustic only) "
            "| Hedge marks on unhedged segments | Ambiguous facts |"
        ) in header
        assert "metric amendment 2026-10-13" in report
        assert separator == "|" + "---|" * 28
        for row in (header, separator, measured, unmeasured, total):
            assert len(row.strip().strip("|").split("|")) == 28
        # Missed, acoustic, unhedged, ambiguous, checker, suspect, the two
        # attribution seconds, prose, rule.
        assert measured.endswith("| 0 | 0 | 3 | 0 | 0 | 2 | 1.5 | 2.0 | - | PASS |")
        assert unmeasured.endswith(
            "| - | - | - | - | - | - | - | - | - | FAIL: harness_error |"
        )
        # The run fails on syn-002's error.
        assert total.endswith("| 0 | 0 | 3 | 0 | 0 | 2 | 1.5 | 2.0 | - | FAIL |")
        clustering = render_report(
            outcomes,
            OPTION_A,
            validation.RunInfo("medium", False, "silero", None, None, None, "clustering"),
        )
        assert "Attribution `clustering`, metric amendment 2026-10-23" in clustering
        # Peer round 17 PR-LOW-013: a seconds TOTAL with no measured row is
        # "-", and a measured zero stays 0.0.
        unresolved = render_report([EncounterOutcome("syn-001", "role_unresolved")], OPTION_A, info)
        (unresolved_total,) = [
            line for line in unresolved.splitlines() if line.startswith("| TOTAL")
        ]
        assert unresolved_total.endswith("| - | - | - | FAIL |")
        zero = EncounterOutcome(
            "syn-001",
            "measured",
            segment_count=1,
            words=metrics.words,
            metrics=metrics,
            suspect_segments=0,
            clinician_as_other_seconds=0.0,
            other_as_clinician_seconds=0.0,
        )
        zero_report = render_report([zero], OPTION_A, info)
        (zero_total,) = [line for line in zero_report.splitlines() if line.startswith("| TOTAL")]
        assert zero_total.endswith("| 0.0 | 0.0 | - | PASS |")
        # Omitted, silent, silent (run-1), silent (0.3.3), warned — in that
        # order.
        assert "| 1 | 0 | 1 | 0 | 1 |" in measured
        assert "| 1 | 0 | 1 | 0 | 1 |" in total
        # WER, then the spelling count (a measured cell and its total).
        assert "| 0.000 | 3 | 0 |" in measured
        assert "| 0.000 | 3 | 0 |" in total
        assert "| - | - | - |" in unmeasured
        # The rule reads ``silent_omissions`` only (C1): the run-1 column
        # never fails an encounter, and neither does an unhedged hedge mark.
        assert validation.rule_failures(OPTION_A, outcomes[0]) == ()

    def test_an_unmeasured_total_reads_dash_and_a_measured_zero_reads_0(self) -> None:
        """Peer round 18 PR-LOW-016 (deferred to validation-run6 Task 4.3,
        rule v2's report only): an error outcome made no transcript, so its
        row and every total read ``-`` — never 0; a role-unresolved
        encounter's transcription supplies the word totals and the suspect
        total (a measured 0), while the note-level totals stay ``-``. A
        schema-1 report keeps runs 1-5's zeros."""
        info = validation.RunInfo("medium", False, "silero", None, None, None)
        error = EncounterOutcome("syn-001", "error", "OSError")
        legacy = render_report([error], OPTION_A, info).splitlines()
        assert any(line.startswith("| syn-001 | error (OSError) | 0 | - | - |") for line in legacy)
        assert any(
            line.startswith("| TOTAL | 0 measured | - | 0 | - | 0 | 0 | 0 | - | - | 0 |")
            for line in legacy
        )
        rule = _rule_v2()
        errored = render_report([error], rule, info, set_name="scripts")
        assert "A cell or total nothing measured reads `-`; a measured zero reads 0." in errored
        table = [line for line in errored.splitlines() if line.startswith("| syn-001")]
        assert table == ["| syn-001 | error (OSError) | " + " | ".join(["-"] * 25)
                         + " | FAIL: harness_error |"]
        (total,) = [line for line in errored.splitlines() if line.startswith("| TOTAL")]
        assert total == "| TOTAL | 0 measured | " + " | ".join(["-"] * 25) + " | FAIL |"
        unresolved = EncounterOutcome(
            "syn-001",
            "role_unresolved",
            segment_count=2,
            words=validation.WordErrors(4, 4, 0),
            suspect_segments=0,
        )
        report = render_report([unresolved], rule, info, set_name="scripts")
        (row,) = [line for line in report.splitlines() if line.startswith("| syn-001")]
        assert row.startswith("| syn-001 | role_unresolved | 2 | 4 | 0.000 | - |")
        (total,) = [line for line in report.splitlines() if line.startswith("| TOTAL")]
        assert total == (
            "| TOTAL | 0 measured | - | 4 | 0.000 | "
            + " | ".join(["-"] * 18)
            + " | 0 | - | - | - | FAIL |"
        )

    def test_a_schema_2_report_names_both_verdicts_and_the_set_layer(self) -> None:
        """Validation-run6 D8, D14, D15, D17 (Task 4.3): the heading carries
        rule v2's verdict for the named set beside rule v1's; the verdict
        lines name the failing encounters, the set-level breaches and the
        gate and reported sets; the residue section lists each class against
        its ceiling with its members, the adjusted totals beside the raw,
        "Surfaced / expected", the ``clinician_line_omitted`` load and the
        reference-boundary record — ids and integers only."""
        rule = _rule_v2()
        outcomes = _residue_outcomes()
        info = validation.RunInfo("medium", False, "silero", None, None, None)
        report = render_report(outcomes, rule, info, set_name="scripts")
        lines = report.splitlines()
        assert lines[0] == (
            "## Validation run - rule `rule-v2-test` - set `scripts` - rule v2 PASS, rule v1 FAIL"
        )
        assert lines[2] == (
            "- Rule v2 verdict, set `scripts` (a gate set): PASS. Failing encounters: none; "
            "set-level: none; set-level errors: 0. The gate is a rule v2 pass on every gate "
            "set (`heldout-3`, `scripts`); the other sets are reported in full (`heldout`)."
        )
        assert lines[3] == (
            "- Rule v1 verdict (the same outcomes on the raw counts, no residue class): FAIL. "
            "Failing encounters: syn-001 (material_wrong); syn-002 (material_wrong)."
        )
        assert "Rule v2 (schema 2; decision 0.7 of 2026-10-22, amended 2026-10-24" in report
        # The per-encounter Rule cell reads rule v2 (both excused), the raw
        # tables are unchanged (two material wrong facts).
        assert "| syn-001 | 0 | present | yes | wrong | no | - | no | no | R1 |" in lines
        assert "| syn-002 | 1 | absent | yes | wrongly_present | no | - | no | no | R3 |" in lines
        rows = [line for line in lines if line.startswith("| syn-00")]
        assert all(row.endswith("| PASS |") for row in rows[:2])
        tail = lines[lines.index("### Residue classes (rule v2, set `scripts`, a gate set)"):]
        assert tail == [
            "### Residue classes (rule v2, set `scripts`, a gate set)",
            "",
            "| Class | Count | Unit | Ceiling | Within |",
            "|---|---|---|---|---|",
            "| R1 recogniser | 1 | facts | 1 | yes |",
            "| R2 tone only | 0 | facts | 1 | yes |",
            "| R3 unbroken next patient | 1 | encounters | 1 | yes |",
            "",
            "- R1: syn-001/f0",
            "- R2: none",
            "- R3: syn-002",
            "- After the classes (the counts rule v2 reads): material wrong 0 (raw 2), silent "
            "omissions 0 (raw 0), uncertainty missed 0 (raw 0).",
            "- Surfaced / expected: 0 / 0 (required in this set).",
            "- clinician_line_omitted per measured encounter: total 5, median 2.5, maximum 3.",
            "- Reference boundary on the script's own words, every next-patient script the "
            "run read, measured or role unresolved (id: reference boundary, tail start): "
            "syn-002: none, 4. Mismatches (a reference boundary that is neither none nor "
            "the tail start; never R3, a finding): none.",
        ]

    @pytest.mark.parametrize("status", ["error", "role_unresolved"])
    def test_a_residue_section_with_nothing_measured_reads_dash(self, status: str) -> None:
        """Peer round 46 PR-LOW-001 (PR-LOW-016's convention): with no
        measured encounter — every outcome an error, or every one role
        unresolved — each class count, its Within flag, the adjusted and raw
        totals, "Surfaced / expected" and the load read ``-``, never a
        measured 0; a measured zero stays 0 (the schema-2 report test)."""
        outcome = (
            EncounterOutcome("syn-001", "error", "OSError")
            if status == "error"
            else EncounterOutcome(
                "syn-001",
                "role_unresolved",
                segment_count=1,
                words=validation.WordErrors(1, 1, 0),
                reference=_axis_reading(None, 4),
            )
        )
        info = validation.RunInfo("medium", False, "silero", None, None, None)
        lines = render_report([outcome], _rule_v2(), info, set_name="scripts").splitlines()
        tail = lines[lines.index("| Class | Count | Unit | Ceiling | Within |") + 2 :]
        assert tail[:3] == [
            "| R1 recogniser | - | facts | 1 | - |",
            "| R2 tone only | - | facts | 1 | - |",
            "| R3 unbroken next patient | - | encounters | 1 | - |",
        ]
        assert tail[4:7] == [f"- R{n}: - (no encounter measured)" for n in (1, 2, 3)]
        assert tail[7] == (
            "- After the classes (the counts rule v2 reads): material wrong - (raw -), "
            "silent omissions - (raw -), uncertainty missed - (raw -)."
        )
        assert tail[8] == "- Surfaced / expected: - / - (required in this set)."
        assert tail[9] == (
            "- clinician_line_omitted per measured encounter: total -, median -, maximum -."
        )
        # D14's record still lists a role-unresolved next-patient script.
        expected = "syn-001: none, 4" if status == "role_unresolved" else "tail start): none"
        assert expected in tail[10]

    def test_the_reference_boundary_record_covers_every_script_the_run_read(self) -> None:
        """D14's recorded check: a role-unresolved next-patient encounter keeps
        its reference reading (taken before the label track), so it is
        recorded too; a script without the axis is not; a reference boundary
        that is neither none nor the tail start is named as a mismatch; an
        error outcome carries none."""
        unresolved = EncounterOutcome(
            "syn-003",
            "role_unresolved",
            segment_count=1,
            words=validation.WordErrors(1, 1, 0),
            reference=_axis_reading(5, 4),
        )
        no_axis = _measured_outcome(
            "syn-004",
            _fact_outcome(),
            reference=validation.ReferenceReading(frozenset({0}), boundary=None, tail_start=None),
        )
        outcomes = [
            *_residue_outcomes(),
            unresolved,
            no_axis,
            EncounterOutcome("syn-005", "error", "OSError"),
        ]
        info = validation.RunInfo("medium", False, "silero", None, None, None)
        report = render_report(outcomes, _rule_v2(), info, set_name="scripts")
        (record,) = [line for line in report.splitlines() if "Reference boundary" in line]
        assert "syn-002: none, 4; syn-003: 5, 4. Mismatches" in record
        assert record.endswith("never R3, a finding): syn-003.")
        assert "syn-004" not in record and "syn-005" not in record

    def test_a_reported_set_and_a_breach(self) -> None:
        """D17: the held-out set reports uncertainty (no R2 ceiling); D8: a
        class over its ceiling fails rule v2 at the set level, named."""
        rule = _rule_v2()
        info = validation.RunInfo("medium", False, "silero", None, None, None)
        outcomes = _residue_outcomes()
        report = render_report(outcomes, rule, info, set_name="heldout-3")
        assert "| R2 tone only | 0 | facts | none (reported) | yes |" in report
        assert "- Surfaced / expected: 0 / 0 (reported, not required, in this set)." in report
        breach = [
            *outcomes,
            _measured_outcome("syn-003", _fact_outcome(verdict="wrong", residue_r1=True)),
        ]
        report = render_report(breach, rule, info, set_name="scripts")
        assert report.splitlines()[0].endswith("- rule v2 FAIL, rule v1 FAIL")
        assert "set-level: R1 2 over the ceiling of 1;" in report
        assert "| R1 recogniser | 2 | facts | 1 | no |" in report
        assert "- R1: syn-001/f0, syn-003/f0" in report
        assert not validation.run_passed(rule, breach, set_name="scripts")
        assert validation.run_passed(rule, outcomes, set_name="scripts")

    @pytest.mark.parametrize("slot", ["words", "metrics", "prose", "reference"])
    def test_an_outcome_holds_only_its_validated_types(self, slot: str) -> None:
        """Round 12 LOW-002 (Constraint 7 at run time): a string where the
        rule and the report read a result is refused at construction."""
        with pytest.raises(ValueError, match=f"{slot} must be a"):
            EncounterOutcome("syn-001", "error", "OSError", **{slot: "said out loud"})

    @pytest.mark.parametrize("value", [-1, True, 1.5, "2"])
    def test_the_suspect_count_is_a_non_negative_count(self, value: Any) -> None:
        """Invented-text guard D8: the outcome holds a count, or None."""
        with pytest.raises(ValueError, match="suspect_segments must be a non-negative count"):
            EncounterOutcome("syn-001", "measured", suspect_segments=value)
        assert EncounterOutcome("syn-001", "measured", suspect_segments=0).suspect_segments == 0
        assert EncounterOutcome("syn-001", "error", "OSError").suspect_segments is None

    @pytest.mark.parametrize("value", [-0.5, math.inf, math.nan, 2, True, "1.0"])
    @pytest.mark.parametrize("name", ["clinician_as_other_seconds", "other_as_clinician_seconds"])
    def test_the_attribution_seconds_are_non_negative_seconds(
        self, name: str, value: Any
    ) -> None:
        """D11: each attribution number is a finite, non-negative float, or
        None (no clinician confirmed)."""
        with pytest.raises(ValueError, match=f"{name} must be a non-negative number of seconds"):
            EncounterOutcome("syn-001", "measured", **{name: value})
        assert getattr(EncounterOutcome("syn-001", "measured", **{name: 0.0}), name) == 0.0
        assert getattr(EncounterOutcome("syn-001", "error", "OSError"), name) is None
