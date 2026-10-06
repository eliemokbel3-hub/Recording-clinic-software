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
        from scribe_desktop.transcription import TranscriptDocument, TranscriptSegment

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
        argv = _argv(tmp_path)
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
        argv = _argv(tmp_path)
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

    @pytest.mark.parametrize("site", ["rule", "config", "profile", "models", "listing", "custody"])
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
        argv = _argv(tmp_path)
        _set_folder(tmp_path / "set")
        if site == "rule":
            _rule_file(tmp_path).write_text("{}", encoding="utf-8")
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
        argv = _argv(tmp_path)
        _set_folder(tmp_path / "set")
        assert validation.main(argv, repo_root=tmp_path) == 0
        out = capsys.readouterr().out
        assert "[run ] syn-001" in out
        assert "- PASS" in out
        assert "commit `unknown`" in out and "manifest SHA-256 `absent`" in out
        # A file not named as an encounter id: reported without its name, a
        # set-level error, and the run still completes (round 11 MED-006).
        (tmp_path / "set" / "Margaret Example.wav").write_bytes(b"")
        assert validation.main(argv, repo_root=tmp_path) == 1
        out = capsys.readouterr().out
        assert f"[error] {validation.UNNAMED_ENCOUNTER}: 1 file(s) skipped" in out
        assert "Margaret" not in out
        assert "[run ] syn-001" in out and "- FAIL" in out


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

    @pytest.mark.parametrize("slot", ["words", "metrics", "prose"])
    def test_an_outcome_holds_only_its_validated_types(self, slot: str) -> None:
        """Round 12 LOW-002 (Constraint 7 at run time): a string where the
        rule and the report read a result is refused at construction."""
        with pytest.raises(ValueError, match=f"{slot} must be a"):
            EncounterOutcome("syn-001", "error", "OSError", **{slot: "said out loud"})
