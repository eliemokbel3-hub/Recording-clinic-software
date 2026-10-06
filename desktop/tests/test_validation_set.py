"""Pilot plan Task 2.5: the synthetic validation-set builder, on generated
tones only.

No real voice speaks here: the voice list and the synthesizer are injected
(``build_set`` / ``main``), and the fake synthesizer returns a sine tone
whose length follows the line's word count and whose amplitude and pitch
follow the voice — so levelling, placement, overlap, noise, peak limiting
and the label track are checked by arithmetic. Scripts are invented.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from conftest import use_channel
from scribe_desktop import validation_set
from scribe_desktop.speaker_eval import parse_audacity_labels, read_wav_pcm
from scribe_desktop.validation import load_script
from scribe_desktop.validation_set import (
    BUILT_MARKER_SUFFIX,
    GAP_SECONDS,
    LEAD_SECONDS,
    MIN_VOICES,
    PEAK_LIMIT,
    TAIL_SECONDS,
    TARGET_SAMPLE_RATE,
    TURN_RMS,
    BuildError,
    Placement,
    RolePlayScriptError,
    TooFewVoicesError,
    active_samples,
    add_noise,
    build_set,
    encounter_seed,
    label_track,
    level_turn,
    mix_turns,
    pcm_samples,
    place_turns,
    render_encounter,
    rms,
    to_pcm16,
)

REPO = Path(__file__).resolve().parents[2]
RATE = TARGET_SAMPLE_RATE
LEAD = round(LEAD_SECONDS * RATE)
GAP = round(GAP_SECONDS * RATE)
TAIL = round(TAIL_SECONDS * RATE)
# The fake synthesizer: 0.25 s per word, plus 0.02 s per rate step.
SECONDS_PER_WORD = 0.25


def _tone(seconds: float, frequency: float, amplitude: float) -> bytes:
    count = round(seconds * RATE)
    samples = [
        round(amplitude * math.sin(2 * math.pi * frequency * i / RATE)) for i in range(count)
    ]
    return to_pcm16(samples, peak_limit=32767)


class _FakeVoices:
    """A synthesizer seam: voice ``n`` is a tone at ``300 + 100 n`` Hz and
    amplitude ``2000 * (n + 1)`` (so levelling has work to do)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, int, int]] = []

    def __call__(self, text: str, voice: int, rate: int) -> bytes:
        self.calls.append((text, voice, rate))
        words = len(text.split())
        seconds = words * SECONDS_PER_WORD + 0.02 * rate
        return _tone(seconds, 300 + 100 * voice, 2000 * (voice + 1))


def _voices(count: int) -> Any:
    names = tuple(f"Voice {index}" for index in range(count))
    return lambda: names


def _script(
    encounter_id: str = "syn-test",
    *,
    conditions: dict[str, Any] | None | bool = True,
    lines: list[dict[str, str]] | None = None,
    axes: list[str] | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "schema_version": 1,
        "encounter_id": encounter_id,
        "appointment_type": "follow_up",
        "axes": axes or ["laterality"],
        "lines": lines
        or [
            {"role": "clinician", "text": "Which knee is sore today?"},
            {"role": "patient", "text": "The left knee, mostly when walking."},
            {"role": "clinician", "text": "Left knee, noted."},
        ],
        "facts": [{"kind": "laterality", "tokens": ["left", "knee"], "line": 1, "material": True}],
    }
    if conditions is True:
        data["conditions"] = {"voice_slots": {"clinician": 0, "patient": 1}}
    elif isinstance(conditions, dict):
        data["conditions"] = conditions
    return data


def _write(folder: Path, data: dict[str, Any]) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{data['encounter_id']}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# The moved resampler and the launcher
# ---------------------------------------------------------------------------


class TestResamplerMove:
    def test_the_fixture_re_imports_the_moved_resampler(self) -> None:
        import sapi_fixture

        assert sapi_fixture.resample_wav_to_pcm16 is validation_set.resample_wav_to_pcm16
        assert sapi_fixture.TARGET_SAMPLE_RATE == validation_set.TARGET_SAMPLE_RATE == 16_000


def _load_launcher() -> ModuleType:
    path = REPO / "scripts" / "build-validation-set.py"
    spec = importlib.util.spec_from_file_location("build_validation_set", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestLauncher:
    def test_the_launcher_dispatches_to_the_module(self) -> None:
        assert _load_launcher().main is validation_set.main

    def test_help_prints_usage(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exit_info:
            validation_set.main(["--help"])
        assert exit_info.value.code == 0
        assert "usage" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Signal processing
# ---------------------------------------------------------------------------


class TestSamplesAndLevel:
    def test_pcm_round_trip(self) -> None:
        # Below the peak limit, so no gain applies (full scale is scaled down
        # by design: TestPeak).
        samples = [0, 1, -1, 31_000, -31_000]
        assert pcm_samples(to_pcm16(samples)) == samples

    def test_a_partial_sample_is_refused(self) -> None:
        with pytest.raises(BuildError, match="partial sample"):
            pcm_samples(b"\x00\x00\x01")

    def test_turns_of_different_loudness_reach_one_level(self) -> None:
        quiet = pcm_samples(_tone(0.5, 300, 1000))
        loud = pcm_samples(_tone(0.5, 500, 12000))
        assert rms(level_turn(quiet)) == pytest.approx(TURN_RMS, rel=1e-9)
        assert rms(level_turn(loud)) == pytest.approx(TURN_RMS, rel=1e-9)

    def test_a_silent_turn_is_refused(self) -> None:
        with pytest.raises(BuildError, match="silence"):
            level_turn([0] * 100)


class TestPlacement:
    def test_turns_follow_each_other_after_the_gap(self) -> None:
        placement = place_turns([16_000, 8_000, 8_000])
        # 0.5 s lead = 8000; gap 0.6 s = 9600.
        assert placement.offsets == (8_000, 33_600, 51_200)
        assert placement.total == 51_200 + 8_000 + 8_000
        assert (LEAD, GAP, TAIL) == (8_000, 9_600, 8_000)

    def test_an_overlapped_turn_starts_before_the_previous_one_ends(self) -> None:
        placement = place_turns([16_000, 8_000, 8_000], overlap_lines=[1], overlap_seconds=0.25)
        # Line 1 starts 4000 samples before line 0 ends (24 000); line 2
        # follows the LATEST end (20 000 + 8000 = 28 000) after the gap.
        assert placement.offsets == (8_000, 20_000, 37_600)
        assert placement.lengths == (16_000, 8_000, 8_000)

    def test_an_overlap_longer_than_the_previous_turn_starts_with_it(self) -> None:
        placement = place_turns([4_000, 8_000], overlap_lines=[1], overlap_seconds=1.0)
        assert placement.offsets == (8_000, 8_000)
        assert placement.total == 8_000 + 8_000 + TAIL

    def test_a_short_overlapped_turn_inside_a_long_one_does_not_pull_the_next_turn_back(
        self,
    ) -> None:
        placement = place_turns([16_000, 2_000, 4_000], overlap_lines=[1], overlap_seconds=0.5)
        # Line 1 runs 16 000..18 000 inside line 0 (8000..24 000); line 2
        # follows line 0's end, the latest.
        assert placement.offsets == (8_000, 16_000, 24_000 + GAP)

    def test_mixing_adds_overlapping_turns(self) -> None:
        placement = Placement(offsets=(0, 2), lengths=(4, 4), total=7)
        assert mix_turns([[1.0] * 4, [10.0] * 4], placement) == [1, 1, 11, 11, 10, 10, 0]
        assert active_samples(placement) == [True] * 6 + [False]


class TestNoise:
    def _mix(self) -> tuple[list[float], list[bool]]:
        placement = place_turns([8_000, 8_000])
        turns = [level_turn(pcm_samples(_tone(0.5, 300, 4000))) for _ in range(2)]
        return mix_turns(turns, placement), active_samples(placement)

    @pytest.mark.parametrize("snr_db", [0.0, 10.0, 25.0])
    def test_the_ratio_over_speech_active_samples_is_exact(self, snr_db: float) -> None:
        mix, active = self._mix()
        noisy = add_noise(mix, active, snr_db, seed=7)
        speech = [value for value, on in zip(mix, active, strict=True) if on]
        noise = [n - m for n, m, on in zip(noisy, mix, active, strict=True) if on]
        ratio = sum(v * v for v in speech) / sum(v * v for v in noise)
        assert 10 * math.log10(ratio) == pytest.approx(snr_db, abs=1e-6)

    def test_noise_runs_through_the_silences_too(self) -> None:
        mix, active = self._mix()
        noisy = add_noise(mix, active, 20.0, seed=7)
        assert any(value != 0.0 for value, on in zip(noisy, active, strict=True) if not on)

    def test_the_seed_is_fixed_per_encounter(self) -> None:
        mix, active = self._mix()
        assert encounter_seed("syn-001") == encounter_seed("syn-001")
        assert encounter_seed("syn-001") != encounter_seed("syn-002")
        first = add_noise(mix, active, 15.0, encounter_seed("syn-001"))
        assert add_noise(mix, active, 15.0, encounter_seed("syn-001")) == first
        assert add_noise(mix, active, 15.0, encounter_seed("syn-002")) != first

    def test_no_active_sample_is_refused(self) -> None:
        with pytest.raises(BuildError, match="no turn is active"):
            add_noise([0.0, 0.0], [False, False], 10.0, seed=1)


class TestPeak:
    def test_a_quiet_mix_is_written_unchanged(self) -> None:
        assert pcm_samples(to_pcm16([100.0, -200.4, 300.6])) == [100, -200, 301]

    def test_a_loud_mix_is_scaled_down_as_a_whole(self) -> None:
        samples = pcm_samples(to_pcm16([60_000.0, -30_000.0, 15_000.0]))
        assert max(abs(value) for value in samples) == round(PEAK_LIMIT)
        # One gain: the ratios hold (to rounding).
        assert samples[0] / samples[1] == pytest.approx(-2.0, abs=1e-3)
        assert samples[0] / samples[2] == pytest.approx(4.0, abs=1e-3)


class TestLabelTrack:
    def test_spans_come_from_the_final_sample_offsets_and_parse_back(self) -> None:
        placement = place_turns([16_001, 7_999, 8_000], overlap_lines=[1], overlap_seconds=0.3)
        text = label_track(["clinician", "patient", "clinician"], placement)
        track = parse_audacity_labels(text)
        assert [span.label for span in track.spans] == ["clinician", "patient", "clinician"]
        for span, offset, length in zip(
            track.spans, placement.offsets, placement.lengths, strict=True
        ):
            assert round(span.start_seconds * RATE) == offset
            assert round(span.end_seconds * RATE) == offset + length
            assert span.start_seconds * RATE == pytest.approx(offset, abs=1e-6)


# ---------------------------------------------------------------------------
# One encounter and the set
# ---------------------------------------------------------------------------


class TestRenderEncounter:
    @pytest.fixture(autouse=True)
    def _folder(self, tmp_path: Path) -> None:
        self.folder = tmp_path

    def test_each_turn_is_placed_and_labelled_by_its_role(self) -> None:
        script = load_script(_write(self.folder,_script()))
        synth = _FakeVoices()
        pcm, labels, placement = render_encounter(script, _voices(2)(), synth)
        assert [call[1] for call in synth.calls] == [0, 1, 0]
        # 5, 6 and 3 words at 0.25 s.
        assert placement.lengths == (20_000, 24_000, 12_000)
        assert len(pcm) == placement.total * 2
        track = parse_audacity_labels(labels)
        assert [span.label for span in track.spans] == ["clinician", "patient", "clinician"]
        samples = pcm_samples(pcm)
        for offset, length in zip(placement.offsets, placement.lengths, strict=True):
            assert rms(samples[offset : offset + length]) == pytest.approx(TURN_RMS, rel=1e-3)
        assert all(value == 0 for value in samples[: placement.offsets[0]])

    def test_the_rate_reaches_the_synthesizer(self) -> None:
        data = _script(
            conditions={"voice_slots": {"clinician": 0, "patient": 1}, "rate": 4},
            axes=["laterality", "rate"],
        )
        synth = _FakeVoices()
        render_encounter(load_script(_write(self.folder,data)), _voices(2)(), synth)
        assert {call[2] for call in synth.calls} == {4}

    def test_a_noisy_encounter_is_deterministic(self) -> None:
        data = _script(
            conditions={"voice_slots": {"clinician": 1, "patient": 0}, "snr_db": 12.0},
            axes=["laterality", "noise"],
        )
        script = load_script(_write(self.folder,data))
        first = render_encounter(script, _voices(2)(), _FakeVoices())
        assert render_encounter(script, _voices(2)(), _FakeVoices()) == first
        samples = pcm_samples(first[0])
        assert any(samples[: first[2].offsets[0]])

    def test_an_overlapped_line_is_labelled_where_it_really_starts(self) -> None:
        data = _script(
            conditions={
                "voice_slots": {"clinician": 0, "patient": 1},
                "overlap_seconds": 0.5,
                "overlap_lines": [1],
            },
            axes=["laterality", "overlap"],
        )
        pcm, labels, placement = render_encounter(
            load_script(_write(self.folder,data)), _voices(2)(), _FakeVoices()
        )
        spans = parse_audacity_labels(labels).spans
        assert spans[1].start_seconds == pytest.approx(spans[0].end_seconds - 0.5, abs=1e-6)
        assert placement.offsets[1] == placement.offsets[0] + placement.lengths[0] - 8_000

    def test_every_span_matches_its_samples_after_a_rate_change_and_an_overlap(
        self, tmp_path: Path
    ) -> None:
        """Round 11 LOW-022 (Task 2.5's Done-when, end to end): the label
        track ``build_set`` writes parses back to each turn's exact samples
        when the rate changes every turn's length and a turn overlaps."""
        data = _script(
            conditions={
                "voice_slots": {"clinician": 0, "patient": 1},
                "rate": 4,
                "overlap_seconds": 0.3,
                "overlap_lines": [1],
            },
            axes=["laterality", "rate", "overlap"],
        )
        scripts = tmp_path / "scripts"
        _write(scripts, data)
        out = tmp_path / "set"
        built, errors = build_set(scripts, out, voices=_voices(2), synthesize=_FakeVoices())
        assert errors == 0
        placement = built[0].placement
        expected_lengths = tuple(
            round((len(line["text"].split()) * SECONDS_PER_WORD + 0.02 * 4) * RATE)
            for line in data["lines"]
        )
        assert placement.lengths == expected_lengths
        assert placement.offsets[1] < placement.offsets[0] + placement.lengths[0]
        track = parse_audacity_labels((out / "syn-test.txt").read_text(encoding="utf-8"))
        assert [span.label for span in track.spans] == ["clinician", "patient", "clinician"]
        for span, offset, length in zip(
            track.spans, placement.offsets, placement.lengths, strict=True
        ):
            assert round(span.start_seconds * RATE) == offset
            assert round(span.end_seconds * RATE) == offset + length

    def test_a_voice_slot_beyond_the_installed_voices_is_refused(self) -> None:
        data = _script(conditions={"voice_slots": {"clinician": 0, "patient": 5}})
        with pytest.raises(BuildError, match="voice slot 5, but only 2 voice"):
            render_encounter(load_script(_write(self.folder,data)), _voices(2)(), _FakeVoices())

    def test_a_role_play_script_is_not_built(self) -> None:
        script = load_script(_write(self.folder,_script(conditions=None)))
        with pytest.raises(RolePlayScriptError):
            render_encounter(script, _voices(2)(), _FakeVoices())

    def test_a_silent_voice_is_refused_naming_the_line(self) -> None:
        script = load_script(_write(self.folder,_script()))
        with pytest.raises(BuildError, match="line 0: a turn was synthesised as silence"):
            render_encounter(script, _voices(2)(), lambda text, voice, rate: b"\x00\x00" * 100)


class TestBuildSet:
    @pytest.mark.parametrize("count", [0, 1])
    def test_fewer_than_two_voices_is_refused_before_any_voice_speaks(
        self, tmp_path: Path, count: int
    ) -> None:
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        synth = _FakeVoices()
        with pytest.raises(TooFewVoicesError, match=f"{count} Windows voice"):
            build_set(scripts, tmp_path / "set", voices=_voices(count), synthesize=synth)
        assert synth.calls == []
        assert not (tmp_path / "set").exists()
        assert MIN_VOICES == 2

    def test_two_voices_build_the_triple(self, tmp_path: Path) -> None:
        scripts = tmp_path / "scripts"
        source = _write(scripts, _script())
        out = tmp_path / "set"
        lines: list[str] = []
        built, errors = build_set(
            scripts, out, voices=_voices(2), synthesize=_FakeVoices(), progress=lines.append
        )
        assert errors == 0
        assert [item.encounter_id for item in built] == ["syn-test"]
        assert (out / "syn-test.json").read_bytes() == source.read_bytes()
        pcm = read_wav_pcm(out / "syn-test.wav")
        assert len(pcm) == built[0].placement.total * 2
        track = parse_audacity_labels((out / "syn-test.txt").read_text(encoding="utf-8"))
        assert len(track.spans) == 3
        assert lines == ["[built] syn-test (5.7 s)"]

    def test_role_plays_are_skipped_and_bad_scripts_counted(self, tmp_path: Path) -> None:
        scripts = tmp_path / "scripts"
        _write(scripts, _script("syn-good"))
        _write(scripts, _script("rp-recorded", conditions=None))
        bad = _script("syn-bad")
        bad["facts"][0]["line"] = 9
        _write(scripts, bad)
        lines: list[str] = []
        built, errors = build_set(
            scripts, tmp_path / "set", voices=_voices(2), synthesize=_FakeVoices(),
            progress=lines.append,
        )
        assert [item.encounter_id for item in built] == ["syn-good"]
        assert errors == 1
        assert any(line.startswith("[skip] rp-recorded") for line in lines)
        assert any(line.startswith("[error] syn-bad.json") for line in lines)
        assert not (tmp_path / "set" / "rp-recorded.wav").exists()

    def test_an_unexpected_failure_is_reported_by_type_only(self, tmp_path: Path) -> None:
        scripts = tmp_path / "scripts"
        _write(scripts, _script())

        def explode(text: str, voice: int, rate: int) -> bytes:
            raise RuntimeError(text)

        lines: list[str] = []
        built, errors = build_set(
            scripts, tmp_path / "set", voices=_voices(2), synthesize=explode,
            progress=lines.append,
        )
        assert (built, errors) == ([], 1)
        assert lines == ["[error] syn-test.json: RuntimeError"]

    def test_only_builds_the_named_and_reports_an_unknown_name(self, tmp_path: Path) -> None:
        scripts = tmp_path / "scripts"
        _write(scripts, _script("syn-a"))
        _write(scripts, _script("syn-b"))
        lines: list[str] = []
        built, errors = build_set(
            scripts, tmp_path / "set", voices=_voices(2), synthesize=_FakeVoices(),
            only=["syn-b", "syn-zz"], progress=lines.append,
        )
        assert [item.encounter_id for item in built] == ["syn-b"]
        assert errors == 1
        assert "[error] syn-zz: no script has this exact name" in lines

    def test_only_matches_the_exact_name(self, tmp_path: Path) -> None:
        """Round 11 LOW-010: on Windows the file exists under any case, but
        nothing is built for a differently-cased name, so it is an error."""
        scripts = tmp_path / "scripts"
        _write(scripts, _script("syn-a"))
        lines: list[str] = []
        built, errors = build_set(
            scripts, tmp_path / "set", voices=_voices(2), synthesize=_FakeVoices(),
            only=["SYN-A"], progress=lines.append,
        )
        assert (built, errors) == ([], 1)
        assert lines == ["[error] SYN-A: no script has this exact name"]

    def test_the_output_folder_may_not_be_the_scripts_folder(self, tmp_path: Path) -> None:
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        with pytest.raises(BuildError, match="must not be the scripts folder"):
            build_set(scripts, scripts, voices=_voices(2), synthesize=_FakeVoices())

    def test_a_set_folder_inside_the_repository_is_refused_before_any_voice_speaks(
        self, tmp_path: Path
    ) -> None:
        """Round 11 LOW-006: the set is generated audio and stays outside
        the repository."""
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        repo = tmp_path / "repo"
        repo.mkdir()
        synth = _FakeVoices()
        with pytest.raises(BuildError, match="outside the repository"):
            build_set(
                scripts, repo / "set", voices=_voices(2), synthesize=synth, repo_root=repo
            )
        assert synth.calls == []
        assert not (repo / "set").exists()
        # The other direction: a folder beside the repository is accepted.
        built, errors = build_set(
            scripts, tmp_path / "set", voices=_voices(2), synthesize=synth, repo_root=repo
        )
        assert (len(built), errors) == (1, 0)

    def test_a_set_folder_that_cannot_be_created_is_refused_by_type(
        self, tmp_path: Path
    ) -> None:
        """Round 11 LOW-009: a refusal, not a traceback."""
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        blocker = tmp_path / "set"
        blocker.write_bytes(b"")
        with pytest.raises(BuildError, match=r"cannot be created \(FileExistsError\)"):
            build_set(scripts, blocker, voices=_voices(2), synthesize=_FakeVoices())

    def test_a_build_leaves_no_temporary_file(self, tmp_path: Path) -> None:
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        out = tmp_path / "set"
        build_set(scripts, out, voices=_voices(2), synthesize=_FakeVoices())
        assert sorted(path.name for path in out.iterdir()) == [
            "syn-test.built", "syn-test.json", "syn-test.txt", "syn-test.wav"
        ]
        assert BUILT_MARKER_SUFFIX == ".built"

    def test_a_recording_without_its_script_is_never_overwritten(self, tmp_path: Path) -> None:
        """Peer round 14 (PR-MED-057): a role-play's WAV and label track
        placed before their script carry no ownership mark, so a synthetic
        script of the same name is refused — nothing is replaced."""
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        out = tmp_path / "set"
        out.mkdir()
        (out / "syn-test.wav").write_bytes(b"recorded")
        (out / "syn-test.txt").write_text("0\t1\tclinician\n", encoding="utf-8")
        lines: list[str] = []
        built, errors = build_set(
            scripts, out, voices=_voices(2), synthesize=_FakeVoices(), progress=lines.append
        )
        assert (built, errors) == ([], 1)
        assert lines == [
            "[error] syn-test: syn-test.wav and syn-test.txt already in the set folder without "
            "its script and not written by this builder (a recording?) - nothing was "
            "overwritten; add its script or move the files, then build again"
        ]
        assert (out / "syn-test.wav").read_bytes() == b"recorded"
        assert sorted(path.name for path in out.iterdir()) == ["syn-test.txt", "syn-test.wav"]

    def test_an_interrupted_rebuild_still_rebuilds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The other direction (PR-MED-057): an interruption leaves the WAV
        and the mark without a script, and the next run rebuilds it."""
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        out = tmp_path / "set"
        build_set(scripts, out, voices=_voices(2), synthesize=_FakeVoices())
        real_write = validation_set._write_replacing

        def stop_at_the_label_track(path: Path, data: bytes) -> None:
            if path.suffix == ".txt":
                raise KeyboardInterrupt
            real_write(path, data)

        monkeypatch.setattr(validation_set, "_write_replacing", stop_at_the_label_track)
        with pytest.raises(KeyboardInterrupt):
            build_set(scripts, out, voices=_voices(2), synthesize=_FakeVoices())
        monkeypatch.setattr(validation_set, "_write_replacing", real_write)
        assert not (out / "syn-test.json").exists()
        assert (out / "syn-test.built").exists()
        built, errors = build_set(scripts, out, voices=_voices(2), synthesize=_FakeVoices())
        assert (len(built), errors) == (1, 0)
        assert (out / "syn-test.json").exists()

    def test_a_failed_build_after_an_interruption_clears_the_leftovers(
        self, tmp_path: Path
    ) -> None:
        """A marked WAV and label track without a script are the builder's,
        so a failing rebuild removes them rather than leaving them to be
        reported as an incomplete triple."""
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        out = tmp_path / "set"
        build_set(scripts, out, voices=_voices(2), synthesize=_FakeVoices())
        (out / "syn-test.json").unlink()
        lines: list[str] = []
        build_set(
            scripts, out, voices=_voices(2),
            synthesize=lambda text, voice, rate: b"\x00\x00" * 100,
            progress=lines.append,
        )
        assert lines[0].endswith("; its earlier build was removed")
        assert list(out.iterdir()) == []

    def test_a_failed_rebuild_removes_the_earlier_build(self, tmp_path: Path) -> None:
        """Round 11 LOW-006: a stale triple would otherwise be measured."""
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        out = tmp_path / "set"
        build_set(scripts, out, voices=_voices(2), synthesize=_FakeVoices())
        assert (out / "syn-test.wav").exists()
        lines: list[str] = []
        built, errors = build_set(
            scripts, out, voices=_voices(2),
            synthesize=lambda text, voice, rate: b"\x00\x00" * 100,
            progress=lines.append,
        )
        assert (built, errors) == ([], 1)
        assert lines[0].endswith("; its earlier build was removed")
        assert list(out.iterdir()) == []

    def test_a_first_build_that_fails_to_write_leaves_no_mark(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Peer round 15 (PR-LOW-060): the mark is written first, so a first
        build whose WAV cannot be written would leave it alone — owning
        nothing, yet enough to let a recording later put under this id be
        overwritten. The failure's cleanup removes it."""
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        out = tmp_path / "set"
        real_write = validation_set._write_replacing

        def locked_wav(path: Path, data: bytes) -> None:
            if path.suffix == ".wav":
                raise PermissionError
            real_write(path, data)

        monkeypatch.setattr(validation_set, "_write_replacing", locked_wav)
        lines: list[str] = []
        built, errors = build_set(
            scripts, out, voices=_voices(2), synthesize=_FakeVoices(), progress=lines.append
        )
        assert (built, errors) == ([], 1)
        assert lines == [
            "[error] syn-test: could not be written (PermissionError) - close any program "
            "holding syn-test.wav or syn-test.txt, or delete them, then build again"
            "; its leftover syn-test.built was removed"
        ]
        assert list(out.iterdir()) == []

    def test_an_interrupted_first_build_leaves_a_mark_the_next_failure_removes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An interruption has no cleanup, so a first build stopped before
        its WAV leaves the mark alone; the next failing build for the id
        removes it, and a recording put there afterwards is refused."""
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        out = tmp_path / "set"
        real_write = validation_set._write_replacing

        def stop_at_the_wav(path: Path, data: bytes) -> None:
            if path.suffix == ".wav":
                raise KeyboardInterrupt
            real_write(path, data)

        monkeypatch.setattr(validation_set, "_write_replacing", stop_at_the_wav)
        with pytest.raises(KeyboardInterrupt):
            build_set(scripts, out, voices=_voices(2), synthesize=_FakeVoices())
        monkeypatch.setattr(validation_set, "_write_replacing", real_write)
        assert [path.name for path in out.iterdir()] == ["syn-test.built"]
        lines: list[str] = []
        build_set(
            scripts, out, voices=_voices(2),
            synthesize=lambda text, voice, rate: b"\x00\x00" * 100,
            progress=lines.append,
        )
        assert lines[0].endswith("; its leftover syn-test.built was removed")
        assert list(out.iterdir()) == []
        (out / "syn-test.wav").write_bytes(b"recorded")
        (out / "syn-test.txt").write_text("0\t1\tclinician\n", encoding="utf-8")
        built, errors = build_set(scripts, out, voices=_voices(2), synthesize=_FakeVoices())
        assert (built, errors) == ([], 1)
        assert (out / "syn-test.wav").read_bytes() == b"recorded"

    def test_a_lone_mark_that_cannot_be_removed_is_named(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        out = tmp_path / "set"
        out.mkdir()
        (out / "syn-test.built").write_bytes(b"left over")
        real_unlink = Path.unlink

        def locked_mark(self: Path, missing_ok: bool = False) -> None:
            if self.suffix == BUILT_MARKER_SUFFIX:
                raise PermissionError
            real_unlink(self, missing_ok=missing_ok)

        monkeypatch.setattr(Path, "unlink", locked_mark)
        lines: list[str] = []
        build_set(
            scripts, out, voices=_voices(2),
            synthesize=lambda text, voice, rate: b"\x00\x00" * 100,
            progress=lines.append,
        )
        assert lines[0].endswith(
            "; its leftover build mark could not be removed (PermissionError) - "
            "delete syn-test.built by hand"
        )
        assert (out / "syn-test.built").exists()

    def test_a_failed_build_leaves_a_role_plays_files_alone(self, tmp_path: Path) -> None:
        """The removal reaches only a triple this builder wrote (a synthetic
        script); a recorded role-play under the same name is never deleted."""
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        out = tmp_path / "set"
        _write(out, _script(conditions=None))
        (out / "syn-test.wav").write_bytes(b"recorded")
        (out / "syn-test.txt").write_text("0\t1\tclinician\n", encoding="utf-8")
        lines: list[str] = []
        built, errors = build_set(
            scripts, out, voices=_voices(2),
            synthesize=lambda text, voice, rate: b"\x00\x00" * 100,
            progress=lines.append,
        )
        assert (built, errors) == ([], 1)
        assert not lines[0].endswith("removed")
        assert (out / "syn-test.wav").read_bytes() == b"recorded"
        assert sorted(path.name for path in out.iterdir()) == [
            "syn-test.json", "syn-test.txt", "syn-test.wav"
        ]

    def test_a_successful_build_never_overwrites_a_role_play(self, tmp_path: Path) -> None:
        """Round 12 LOW-005: a synthetic script sharing a recorded role-play's
        name renders but replaces nothing."""
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        out = tmp_path / "set"
        recorded = _write(out, _script(conditions=None)).read_bytes()
        (out / "syn-test.wav").write_bytes(b"recorded")
        (out / "syn-test.txt").write_text("0\t1\tclinician\n", encoding="utf-8")
        lines: list[str] = []
        built, errors = build_set(
            scripts, out, voices=_voices(2), synthesize=_FakeVoices(), progress=lines.append
        )
        assert (built, errors) == ([], 1)
        assert lines == [
            "[error] syn-test: a role-play already holds this name in the set folder - "
            "nothing was overwritten"
        ]
        assert (out / "syn-test.wav").read_bytes() == b"recorded"
        assert (out / "syn-test.json").read_bytes() == recorded

    def test_an_unreadable_script_in_the_set_folder_is_not_overwritten(
        self, tmp_path: Path
    ) -> None:
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        out = tmp_path / "set"
        out.mkdir()
        (out / "syn-test.json").write_text("{half written", encoding="utf-8")
        (out / "syn-test.wav").write_bytes(b"recorded")
        lines: list[str] = []
        built, errors = build_set(
            scripts, out, voices=_voices(2), synthesize=_FakeVoices(), progress=lines.append
        )
        assert (built, errors) == ([], 1)
        assert "an unreadable script already holds this name" in lines[0]
        assert (out / "syn-test.json").read_text(encoding="utf-8") == "{half written"
        assert (out / "syn-test.wav").read_bytes() == b"recorded"

    def test_an_interrupted_rebuild_leaves_no_complete_mixed_triple(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 12 LOW-006: the earlier script goes first and the new one
        is written last, so a stop between the files leaves a triple the
        harness reports as incomplete."""
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        out = tmp_path / "set"
        build_set(scripts, out, voices=_voices(2), synthesize=_FakeVoices())
        real_write = validation_set._write_replacing

        def stop_at_the_label_track(path: Path, data: bytes) -> None:
            if path.suffix == ".txt":
                raise KeyboardInterrupt
            real_write(path, data)

        monkeypatch.setattr(validation_set, "_write_replacing", stop_at_the_label_track)
        with pytest.raises(KeyboardInterrupt):
            build_set(scripts, out, voices=_voices(2), synthesize=_FakeVoices())
        assert not (out / "syn-test.json").exists()
        assert (out / "syn-test.wav").exists()

    def test_a_removal_that_fails_is_reported_not_raised(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 12 LOW-007: a WAV open in another program cannot be
        deleted; the build goes on and the line names what to delete."""
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        out = tmp_path / "set"
        build_set(scripts, out, voices=_voices(2), synthesize=_FakeVoices())
        real_unlink = Path.unlink

        def locked_wav(self: Path, missing_ok: bool = False) -> None:
            if self.suffix == ".wav":
                raise PermissionError
            real_unlink(self, missing_ok=missing_ok)

        monkeypatch.setattr(Path, "unlink", locked_wav)
        lines: list[str] = []
        built, errors = build_set(
            scripts, out, voices=_voices(2),
            synthesize=lambda text, voice, rate: b"\x00\x00" * 100,
            progress=lines.append,
        )
        assert (built, errors) == ([], 1)
        assert lines[0].endswith(
            "; its earlier build could not be removed (PermissionError) - delete "
            "syn-test.wav, syn-test.txt, syn-test.json and syn-test.built by hand"
        )
        # The script went first, so what is left is an incomplete triple.
        assert not (out / "syn-test.json").exists()

    def test_a_write_that_fails_says_what_to_do(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 13 LOW-008: a rebuild over a WAV open in another program
        fails at the write, after the script copy is gone — the line names
        the files to close or delete, and the build goes on."""
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        out = tmp_path / "set"
        build_set(scripts, out, voices=_voices(2), synthesize=_FakeVoices())
        real_write = validation_set._write_replacing

        def locked_wav(path: Path, data: bytes) -> None:
            if path.suffix == ".wav":
                raise PermissionError
            real_write(path, data)

        monkeypatch.setattr(validation_set, "_write_replacing", locked_wav)
        lines: list[str] = []
        built, errors = build_set(
            scripts, out, voices=_voices(2), synthesize=_FakeVoices(), progress=lines.append
        )
        assert (built, errors) == ([], 1)
        # The leftovers are the builder's (the ownership mark), so the
        # removal path clears them (peer round 14, PR-MED-057); with the WAV
        # truly locked it would name them instead.
        assert lines == [
            "[error] syn-test: could not be written (PermissionError) - close any program "
            "holding syn-test.wav or syn-test.txt, or delete them, then build again"
            "; its earlier build was removed"
        ]
        assert list(out.iterdir()) == []

    def test_voices_that_cannot_be_listed_are_refused_by_type(self, tmp_path: Path) -> None:
        def broken() -> tuple[str, ...]:
            raise OSError("the speech service text")

        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        with pytest.raises(BuildError, match=r"^the Windows voices cannot be listed \(OSError\)$"):
            build_set(scripts, tmp_path / "set", voices=broken, synthesize=_FakeVoices())
        assert not (tmp_path / "set").exists()

    def test_the_copied_script_is_the_one_that_was_rendered(self, tmp_path: Path) -> None:
        """Round 12 LOW-008: the script is read once, so an edit made while
        the voices speak never reaches the copy."""
        scripts = tmp_path / "scripts"
        source = _write(scripts, _script())
        rendered = source.read_bytes()
        voices = _FakeVoices()

        def edit_while_speaking(text: str, voice: int, rate: int) -> bytes:
            source.write_text(json.dumps(_script(axes=["negation"])), encoding="utf-8")
            return voices(text, voice, rate)

        out = tmp_path / "set"
        build_set(scripts, out, voices=_voices(2), synthesize=edit_while_speaking)
        assert (out / "syn-test.json").read_bytes() == rendered
        assert source.read_bytes() != rendered

    def test_the_real_speech_engine_is_never_reached_in_tests(
        self, tmp_path: Path, _no_real_speech_engine: list[str]
    ) -> None:
        """Round 11 MED-005 / round 12 LOW-010: the defaults are looked up
        at call time, so the conftest sentinel catches a test that leaves a
        seam out — and records it, so a refusal the builder's own handlers
        catch still fails the test at teardown. This test reaches both on
        purpose, so it clears the record."""
        scripts = tmp_path / "scripts"
        _write(scripts, _script())
        with pytest.raises(BuildError, match=r"cannot be listed \(AssertionError\)"):
            build_set(scripts, tmp_path / "set", synthesize=_FakeVoices())
        lines: list[str] = []
        built, errors = build_set(
            scripts, tmp_path / "set", voices=_voices(2), progress=lines.append
        )
        # The synthesizer's sentinel fires inside the per-script handler, so
        # it is reported by type rather than raised; nothing was spoken.
        assert (built, errors) == ([], 1)
        assert lines == ["[error] syn-test.json: AssertionError"]
        assert _no_real_speech_engine == ["sapi_voices", "sapi_synthesize"]
        _no_real_speech_engine.clear()


class TestMain:
    @pytest.fixture(autouse=True)
    def _developer_build(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # The builder runs only on the developer build; conftest pins every
        # test to production, so these tests pin the dev channel through the
        # same seam (the production refusal below re-pins it).
        use_channel(monkeypatch, "dev")

    def test_a_packaged_build_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        use_channel(monkeypatch, "production")
        code = validation_set.main(
            [str(tmp_path), str(tmp_path / "set")], voices=_voices(2), synthesize=_FakeVoices()
        )
        assert code == 2
        assert "developer build" in capsys.readouterr().out

    def test_a_missing_scripts_folder_is_refused(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = validation_set.main(
            [str(tmp_path / "nope"), str(tmp_path / "set")],
            voices=_voices(2),
            synthesize=_FakeVoices(),
        )
        assert code == 2
        assert "is not a folder" in capsys.readouterr().out

    def test_one_voice_is_refused(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write(tmp_path / "scripts", _script())
        code = validation_set.main(
            [str(tmp_path / "scripts"), str(tmp_path / "set")],
            voices=_voices(1),
            synthesize=_FakeVoices(),
        )
        assert code == 2
        assert "[refused] 1 Windows voice(s) installed" in capsys.readouterr().out

    def test_the_real_synthesizer_without_pyav_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Round 11 LOW-015 (Task 2.7's reading for the builder): it needs no
        model but does need PyAV — without it every script would fail as a
        bare ``ModuleNotFoundError``. Checked only for the real synthesizer;
        an injected one (every other test here) needs no resampler."""
        monkeypatch.setattr(validation_set, "resampler_available", lambda: False)
        _write(tmp_path / "scripts", _script())
        code = validation_set.main(
            [str(tmp_path / "scripts"), str(tmp_path / "set")], voices=_voices(2)
        )
        assert code == 2
        assert "[refused] PyAV" in capsys.readouterr().out
        assert not (tmp_path / "set").exists()

    def test_a_set_folder_inside_the_repository_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``main`` passes the repository root (the module global, read at
        call time): refused before any folder is created. The root is a
        stand-in, so a regression could never write into the real
        repository (round 12 LOW-015)."""
        repo = tmp_path / "repo"
        repo.mkdir()
        monkeypatch.setattr(validation_set, "REPO_ROOT", repo)
        _write(tmp_path / "scripts", _script())
        inside = repo / "validation" / "set"
        code = validation_set.main(
            [str(tmp_path / "scripts"), str(inside)],
            voices=_voices(2),
            synthesize=_FakeVoices(),
        )
        assert code == 2
        assert "[refused] the set folder must be outside the repository" in (
            capsys.readouterr().out
        )
        assert not inside.exists()

    def test_a_clean_build_exits_zero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write(tmp_path / "scripts", _script())
        code = validation_set.main(
            [str(tmp_path / "scripts"), str(tmp_path / "set")],
            voices=_voices(2),
            synthesize=_FakeVoices(),
        )
        assert code == 0
        assert "built 1 encounter(s); 0 error(s)" in capsys.readouterr().out
