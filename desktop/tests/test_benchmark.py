"""Tests for the RTF benchmark harness (benchmark math + offline enforcement).

ML-free by design: benchmark.py lazy-imports the ML stack, so everything here
runs without faster-whisper installed. The one test that would touch a real
model is guarded with importorskip + a local-model-cache presence check.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import types
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pytest

from conftest import (
    forbid_network_io,
    real_ml_models_root,
    real_ml_skip_reason,
    use_frozen,
)
from scribe_desktop import benchmark
from scribe_desktop.benchmark import (
    LIVE_WINDOW_SECONDS,
    OFFLINE_ENV,
    RTF_MARGIN,
    RTF_REQUIRED,
    AppShapeTiming,
    BenchmarkResult,
    OfflineEnvError,
    apply_offline_env,
    assert_offline_env,
    classify_rtf,
    compute_rtf,
    list_whisper_candidates,
    live_keeps_up,
    live_window_latency,
    live_window_speed,
    threshold_report,
    time_app_shape,
)
from scribe_desktop.speech import SAMPLE_RATE, TranscribedWord


def _result(rtf: float, name: str = "small") -> BenchmarkResult:
    return BenchmarkResult(
        model_name=name,
        audio_seconds=30.0,
        load_seconds=1.5,
        transcribe_seconds=rtf * 30.0,
        rtf=rtf,
        peak_memory_bytes=512 * 2**20,
        word_count=120,
    )


class TestModuleImport:
    def test_module_importable_without_ml_stack(self) -> None:
        # Lazy imports: importing benchmark must not require faster_whisper,
        # psutil at module scope, or win32com.
        assert "faster_whisper" not in benchmark.__dict__
        assert "win32com" not in benchmark.__dict__


class TestBenchmarkMath:
    def test_compute_rtf(self) -> None:
        assert compute_rtf(15.0, 30.0) == pytest.approx(0.5)

    def test_compute_rtf_rejects_nonpositive_audio(self) -> None:
        with pytest.raises(ValueError):
            compute_rtf(1.0, 0.0)
        with pytest.raises(ValueError):
            compute_rtf(1.0, -3.0)

    @pytest.mark.parametrize(
        ("rtf", "expected"),
        [
            (0.0, "ok"),
            (RTF_MARGIN, "ok"),
            (RTF_MARGIN + 1e-9, "warning"),
            (RTF_REQUIRED - 1e-9, "warning"),
            (RTF_REQUIRED, "fail"),
            (2.5, "fail"),
        ],
    )
    def test_classify_rtf_boundaries(self, rtf: float, expected: str) -> None:
        assert classify_rtf(rtf) == expected

    def test_classify_rtf_rejects_negative(self) -> None:
        with pytest.raises(ValueError):
            classify_rtf(-0.1)

    def test_result_status_property(self) -> None:
        assert _result(0.4).status == "ok"
        assert _result(0.9).status == "warning"
        assert _result(1.2).status == "fail"


class TestThresholdReport:
    def test_report_contains_rows_and_no_cloud_fallback(self) -> None:
        lines = threshold_report([_result(0.4, "small"), _result(1.4, "medium")])
        text = "\n".join(lines)
        assert "small" in text and "medium" in text
        assert "WARNING" in text  # the failing model warns
        assert "no cloud fallback" in text
        assert "cloud" not in text.replace("no cloud fallback", "")

    def test_warning_shape_for_no_margin(self) -> None:
        text = "\n".join(threshold_report([_result(0.9, "small")]))
        assert "NOTE" in text and "margin" in text

    def test_all_ok_report_has_no_warnings(self) -> None:
        text = "\n".join(threshold_report([_result(0.3, "small")]))
        assert "WARNING" not in text and "NOTE" not in text


class TestLiveWindowLatency:
    """Task 1.6: the panel projects each model's RTF onto one live window."""

    def test_latency_and_speed_for_a_fast_model(self) -> None:
        result = _result(0.5)
        assert live_window_latency(result) == pytest.approx(15.0)
        assert live_window_speed(result) == pytest.approx(2.0)

    def test_latency_and_speed_for_a_slow_model(self) -> None:
        result = _result(1.2)
        assert live_window_latency(result) == pytest.approx(36.0)
        assert live_window_speed(result) == pytest.approx(30.0 / 36.0)

    def test_speed_rejects_zero_rtf(self) -> None:
        with pytest.raises(ValueError):
            live_window_speed(_result(0.0))

    @pytest.mark.parametrize(
        ("rtf", "expected"),
        [(0.5, True), (0.9, True), (1.0, False), (1.2, False)],
    )
    def test_live_keeps_up_follows_the_rtf_bar(self, rtf: float, expected: bool) -> None:
        assert live_keeps_up(_result(rtf)) is expected

    def test_report_has_one_live_line_per_result(self) -> None:
        lines = threshold_report([_result(0.5, "small"), _result(1.2, "medium")])
        live_lines = [line for line in lines if "live window latency" in line]
        assert len(live_lines) == 2
        assert live_lines[0] == (
            "small: live window latency 15.0 s per 30 s window (2.00x real time) "
            "- live transcription keeps up on this machine"
        )
        assert live_lines[1] == (
            "medium: live window latency 36.0 s per 30 s window (0.83x real time) "
            "- live transcription would fall behind here; the recording is "
            "transcribed after Finish instead"
        )

    def test_report_names_an_unmeasurable_zero_rtf_instead_of_failing(self) -> None:
        """Round 7 LOW-004: a zero RTF is not a measurement; the panel says so
        for that model and still renders every other line."""
        lines = threshold_report([_result(0.0, "small"), _result(0.5, "medium")])
        assert "small: live window latency not measurable (RTF 0)" in lines
        assert any(line.startswith("medium: live window latency 15.0 s") for line in lines)

    def test_window_seconds_pinned_to_the_live_transcriber(self) -> None:
        # Imported HERE only: benchmark.py must not import transcription
        # (transcription imports benchmark - that would be a cycle).
        from scribe_desktop import transcription

        assert LIVE_WINDOW_SECONDS == transcription.TRANSCRIBE_WINDOW_SECONDS
        assert LIVE_WINDOW_SECONDS == transcription.LIVE_MAX_SEGMENT_SECONDS


class TestOfflineEnv:
    def test_apply_then_assert_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for key in OFFLINE_ENV:
            monkeypatch.delenv(key, raising=False)
        apply_offline_env()
        assert_offline_env()
        for key, value in OFFLINE_ENV.items():
            assert os.environ[key] == value

    def test_assert_raises_when_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        apply_offline_env()
        monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
        with pytest.raises(OfflineEnvError, match="HF_HUB_OFFLINE"):
            assert_offline_env()

    def test_assert_raises_when_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        apply_offline_env()
        monkeypatch.setenv("TRANSFORMERS_OFFLINE", "0")
        with pytest.raises(OfflineEnvError, match="TRANSFORMERS_OFFLINE"):
            assert_offline_env()

    def test_run_single_asserts_offline_before_ml_import(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # With the kill-switches absent, run_single must fail BEFORE any ML
        # import (so this test needs no ML stack installed).
        for key in OFFLINE_ENV:
            monkeypatch.delenv(key, raising=False)
        with pytest.raises(OfflineEnvError):
            benchmark.run_single(tmp_path / "whisper" / "small", tmp_path / "a.wav", 1.0)


def _snapshot(root: Path, name: str, *files: str) -> Path:
    target = root / "whisper" / name
    target.mkdir(parents=True, exist_ok=True)
    for filename in files:
        (target / filename).write_bytes(b"x")
    return target


class TestCandidateDiscovery:
    def test_lists_only_complete_snapshots(self, tmp_path: Path) -> None:
        _snapshot(tmp_path, "small", "model.bin", "config.json", "vocabulary.txt")
        _snapshot(tmp_path, "binonly", "model.bin")
        (tmp_path / "whisper" / "incomplete").mkdir()
        assert list_whisper_candidates(tmp_path) == ["small"]

    def test_empty_when_cache_missing(self, tmp_path: Path) -> None:
        assert list_whisper_candidates(tmp_path / "nope") == []

    @pytest.mark.parametrize("root", [r"\\h\s\models", r"\/h/s/models"])
    def test_a_network_root_is_never_touched(
        self, root: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Round 27 PR-MED-021: no stat or listing of a network share (C1).
        def refuse(self: Path, *args: object, **kwargs: object) -> object:
            raise AssertionError(f"touched {self}")

        monkeypatch.setattr(Path, "is_dir", refuse)
        monkeypatch.setattr(Path, "iterdir", refuse)
        assert list_whisper_candidates(Path(root)) == []


class TestNetworkPathsRefused:
    """Round 27 PR-MED-021: the benchmark refuses a network (UNC) path before
    any filesystem touch or ML import, like the other model loaders."""

    @pytest.mark.parametrize(
        ("model_dir", "audio"),
        [
            (r"\\h\s\whisper\small", r"C:\t\a.wav"),
            (r"C:\m\whisper\small", "//h/s/a.wav"),
        ],
    )
    def test_run_single_refuses_a_network_path(
        self, model_dir: str, audio: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for key, value in OFFLINE_ENV.items():
            monkeypatch.setenv(key, value)
        for key in benchmark.FORBIDDEN_NATIVE_OVERRIDES + benchmark.FORBIDDEN_TLS_OVERRIDES:
            monkeypatch.delenv(key, raising=False)
        # Round 28 PR-LOW-030: a regressed guard fails at the import
        # (ImportError, not the RuntimeError) before `WhisperModel` could open
        # the network path, and no `Path` method in `NETWORK_IO_METHODS`
        # reaches it either (round 30).
        monkeypatch.setitem(sys.modules, "faster_whisper", None)
        forbid_network_io(monkeypatch)
        with pytest.raises(RuntimeError, match="not UNC"):
            benchmark.run_single(Path(model_dir), Path(audio), 1.0)

    def test_run_all_refuses_a_network_root(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            benchmark, "list_whisper_candidates", lambda root: pytest.fail("listed")
        )
        monkeypatch.setattr(
            benchmark, "generate_speech_sample", lambda target: pytest.fail("sampled")
        )
        with pytest.raises(RuntimeError, match="not UNC"):
            benchmark.run_all(Path(r"\\h\s\models"))

    @pytest.mark.parametrize("source", ["tempdir", "TMPDIR", "TEMP", "TMP"])
    def test_run_all_refuses_a_network_temporary_folder(
        self, source: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Round 28 PR-LOW-029: refused from the values, before tempfile probes
        # a candidate folder or the sample is written.
        unc = r"\\h\s\temp"
        if source == "tempdir":
            monkeypatch.setattr(tempfile, "tempdir", unc)
        else:
            monkeypatch.setenv(source, unc)
        monkeypatch.setattr(benchmark, "list_whisper_candidates", lambda root: ["small"])
        monkeypatch.setattr(
            benchmark.tempfile,
            "TemporaryDirectory",
            lambda *args, **kwargs: pytest.fail("temporary folder made"),
        )
        monkeypatch.setattr(
            benchmark, "generate_speech_sample", lambda target: pytest.fail("sampled")
        )
        with pytest.raises(RuntimeError, match="not UNC"):
            benchmark.run_all(Path(r"C:\m"))

    @pytest.mark.parametrize("target", [r"\\h\s\a.wav", r"\/h/s/a.wav"])
    def test_the_sample_writer_refuses_a_network_target(
        self, target: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Round 28 PR-LOW-029: refused before SAPI is reached — the import
        # fails the test (ImportError, not the RuntimeError) if it is.
        monkeypatch.setitem(sys.modules, "win32com.client", None)
        with pytest.raises(RuntimeError, match="not UNC"):
            benchmark.generate_speech_sample(Path(target))


class TestSnapshotCompleteness:
    """Smoke round 21: BOTH CT2 export layouts are complete — tokenizer.json
    (distil-*) OR vocabulary.txt / vocabulary.json (Systran small/medium)."""

    def test_tokenizer_json_layout_complete(self, tmp_path: Path) -> None:
        target = _snapshot(tmp_path, "d", "model.bin", "config.json", "tokenizer.json")
        assert benchmark.whisper_snapshot_complete(target)
        assert benchmark.whisper_snapshot_missing(target) == []

    def test_vocabulary_txt_layout_complete(self, tmp_path: Path) -> None:
        target = _snapshot(tmp_path, "s", "model.bin", "config.json", "vocabulary.txt")
        assert benchmark.whisper_snapshot_complete(target)

    def test_vocabulary_json_layout_complete(self, tmp_path: Path) -> None:
        target = _snapshot(tmp_path, "j", "model.bin", "config.json", "vocabulary.json")
        assert benchmark.whisper_snapshot_complete(target)

    def test_missing_tokenizer_reported(self, tmp_path: Path) -> None:
        target = _snapshot(tmp_path, "m", "model.bin", "config.json")
        missing = benchmark.whisper_snapshot_missing(target)
        assert missing == ["tokenizer.json or vocabulary.txt or vocabulary.json"]

    def test_empty_files_not_complete(self, tmp_path: Path) -> None:
        target = tmp_path / "whisper" / "z"
        target.mkdir(parents=True)
        for name in ("model.bin", "config.json", "tokenizer.json"):
            (target / name).touch()  # zero bytes
        assert not benchmark.whisper_snapshot_complete(target)

    def test_missing_model_bin_reported(self, tmp_path: Path) -> None:
        target = _snapshot(tmp_path, "n", "config.json", "vocabulary.txt")
        assert "model.bin" in benchmark.whisper_snapshot_missing(target)


# --- larger-model plan D8: the app-shape RTF and the mel check ------------------------

_PANEL_HEADER = "model" + " " * 19 + "RTF  load s  audio s  peak MiB  words  status"
_APP_HEADER = "model" + " " * 19 + "RTF  app RTF  load s  audio s  peak MiB  words  status"


def _app(rtf: float, app_rtf: float | None, name: str = "medium") -> BenchmarkResult:
    return replace(_result(rtf, name), app_rtf=app_rtf)


class TestAppShapeReport:
    """D8: ``threshold_report`` prints an ``app RTF`` column beside the
    panel's and classifies the app-shape RTF when present; without one (the
    Microphone tab's panel) nothing changes."""

    def test_the_panel_report_is_unchanged(self) -> None:
        lines = threshold_report([_result(0.4, "small")])
        assert lines[1] == _PANEL_HEADER
        assert lines[2].split() == ["small", "0.400", "1.50", "30.0", "512.0", "120", "OK"]
        assert _result(0.4).app_rtf is None
        assert _result(0.4).classified_rtf == 0.4

    def test_the_app_column_sits_beside_the_panels(self) -> None:
        lines = threshold_report([_app(0.4, 0.9), _result(0.3, "small")])
        assert lines[1] == _APP_HEADER
        assert lines[2].split() == [
            "medium", "0.400", "0.900", "1.50", "30.0", "512.0", "120", "WARNING",
        ]
        # A result without one, in a table with the column, shows "-".
        assert lines[3].split() == ["small", "0.300", "-", "1.50", "30.0", "512.0", "120", "OK"]
        # The cells line up under the header: the app column ends where its
        # heading ends, in both rows.
        end = _APP_HEADER.index("app RTF") + len("app RTF")
        assert lines[2][end - 5 : end] == "0.900"
        assert lines[3][end - 1 : end] == "-"

    @pytest.mark.parametrize(
        ("rtf", "app_rtf", "status"),
        [(0.4, 0.9, "warning"), (0.4, 1.2, "fail"), (1.2, 0.5, "ok"), (0.9, None, "warning")],
    )
    def test_the_status_reads_the_app_rtf_when_present(
        self, rtf: float, app_rtf: float | None, status: str
    ) -> None:
        result = _app(rtf, app_rtf)
        assert result.status == status
        assert result.classified_rtf == (app_rtf if app_rtf is not None else rtf)

    def test_the_lines_after_the_table_read_the_app_rtf(self) -> None:
        lines = threshold_report([_app(0.4, 1.2)])
        assert lines[3] == (
            "medium: live window latency 36.0 s per 30 s window (0.83x real time) "
            "- live transcription would fall behind here; the recording is "
            "transcribed after Finish instead"
        )
        assert lines[4] == (
            "WARNING: medium transcribes slower than real time (app RTF 1.20 >= 1.00) on "
            "this machine. Transcription stays local; there is no cloud fallback."
        )
        assert len(lines) == 5

    def test_a_note_names_the_app_rtf(self) -> None:
        lines = threshold_report([_app(1.4, 0.9)])
        assert lines[-1] == (
            "NOTE: medium meets the real-time bar without margin (app RTF 0.90 > 0.75); "
            "slower clinic hardware may fall behind real time."
        )
        assert not any(line.startswith("WARNING") for line in lines)

    def test_a_panel_note_still_names_the_rtf(self) -> None:
        assert threshold_report([_result(0.9, "small")])[-1] == (
            "NOTE: small meets the real-time bar without margin (RTF 0.90 > 0.75); "
            "slower clinic hardware may fall behind real time."
        )

    def test_the_live_latency_follows_the_app_rtf(self) -> None:
        assert live_window_latency(_app(0.2, 0.5)) == pytest.approx(15.0)
        assert live_window_speed(_app(0.2, 0.5)) == pytest.approx(2.0)
        assert live_keeps_up(_app(0.2, 1.0)) is False


class _ScriptedProvider:
    """A ``SpeechProvider`` that records each call's PCM length and rate and
    returns a scripted number of words per call."""

    def __init__(self, words_per_call: list[int]) -> None:
        self._words = list(words_per_call)
        self.calls: list[tuple[int, int]] = []

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        self.calls.append((len(pcm), sample_rate))
        count = self._words.pop(0)
        return [TranscribedWord(f"w{i}", 0.0, 0.1, 0.9) for i in range(count)]


def _speech_then_silence_then_speech() -> bytes:
    """625 speech frames (20.0 s), 32 silent frames (1.024 s), 625 speech
    frames: two VAD segments whose span (41.024 s) exceeds one 30 s window."""
    frame = 512 * 2
    return b"\x01\x00" * (625 * 512) + b"\x00" * (32 * frame) + b"\x01\x00" * (625 * 512)


def _nonzero_frame(frame: bytes) -> float:
    return 1.0 if any(frame) else 0.0


def _clock(readings: list[float]) -> Any:
    values = iter(readings)
    return lambda: next(values)


class TestTimeAppShape:
    """D8: one provider call per packed window, the decode time summed over
    the summed window audio — driven by a scripted provider and clock."""

    def test_one_call_per_packed_window_summed(self) -> None:
        provider = _ScriptedProvider([3, 4])
        timing = time_app_shape(
            _speech_then_silence_then_speech(),
            _nonzero_frame,
            provider,
            clock=_clock([0.0, 5.0, 5.0, 17.0]),
        )
        # seg 1: [0, 20.1] (20.0 s + 0.1 s pad); seg 2: [20.924, 41.024] (the
        # pad clamped at the audio end) - each its own window.
        assert [rate for _length, rate in provider.calls] == [SAMPLE_RATE, SAMPLE_RATE]
        lengths = [length for length, _rate in provider.calls]
        assert [length / (2 * SAMPLE_RATE) for length in lengths] == [
            pytest.approx(20.1, abs=1e-3),
            pytest.approx(20.1, abs=1e-3),
        ]
        assert timing.windows == 2
        assert timing.word_count == 7
        assert timing.transcribe_seconds == 17.0
        assert timing.audio_seconds == pytest.approx(sum(lengths) / (2 * SAMPLE_RATE))
        assert timing.rtf == pytest.approx(17.0 / timing.audio_seconds)
        assert timing.rtf == pytest.approx(17.0 / 40.2, abs=1e-4)

    def test_a_short_sample_is_one_window(self) -> None:
        provider = _ScriptedProvider([2])
        pcm = b"\x00" * (8 * 1024) + b"\x01\x00" * (100 * 512) + b"\x00" * (20 * 1024)
        timing = time_app_shape(pcm, _nonzero_frame, provider, clock=_clock([1.0, 3.5]))
        assert timing.windows == 1 and len(provider.calls) == 1
        assert timing.transcribe_seconds == 2.5

    def test_no_speech_is_refused_and_nothing_is_timed(self) -> None:
        provider = _ScriptedProvider([])
        with pytest.raises(RuntimeError, match="no speech"):
            time_app_shape(b"\x00" * (50 * 1024), _nonzero_frame, provider, clock=_clock([]))
        assert provider.calls == []

    def test_the_timing_round_trips_as_the_workers_json(self) -> None:
        timing = AppShapeTiming(
            windows=2, audio_seconds=40.2, transcribe_seconds=17.0, word_count=7
        )
        payload = json.loads(json.dumps(asdict(timing)))
        assert payload == {
            "windows": 2,
            "audio_seconds": 40.2,
            "transcribe_seconds": 17.0,
            "word_count": 7,
        }
        assert AppShapeTiming(**payload) == timing


def _snapshot_dir(root: Path) -> Path:
    target = root / "whisper" / "fake-model"
    target.mkdir(parents=True)
    for filename in ("model.bin", "config.json", "vocabulary.txt"):
        (target / filename).write_bytes(b"x")
    return target


def _fake_whisper_module(
    monkeypatch: pytest.MonkeyPatch, *, filters: int, n_mels: int, samples: Any = None
) -> list[dict[str, object]]:
    """Install a ``faster_whisper`` stand-in: a ``WhisperModel`` with the
    given mel counts recording every ``transcribe`` call's arguments, and a
    ``decode_audio`` serving ``samples``. Returns the call list."""
    calls: list[dict[str, object]] = []

    class _Model:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.feature_extractor = types.SimpleNamespace(
                mel_filters=types.SimpleNamespace(shape=(filters, 201))
            )
            self.model = types.SimpleNamespace(n_mels=n_mels)

        def transcribe(self, audio: object, **kwargs: object) -> tuple[list[object], None]:
            calls.append({"audio": audio, **kwargs})
            return [], None

    def _decode_audio(path: str, sampling_rate: int) -> Any:
        calls.append({"decode": path, "sampling_rate": sampling_rate})
        return samples

    fake = types.ModuleType("faster_whisper")
    fake.WhisperModel = _Model  # type: ignore[attr-defined]
    fake.decode_audio = _decode_audio  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "faster_whisper", fake)
    return calls


class TestRunAppShape:
    """D8: the app-shape worker decodes the sample, runs silero VAD and
    times ``WhisperSpeechProvider``'s own call — the app's primer and decode
    parameters, fresh each window."""

    def test_each_window_is_the_providers_own_call_with_the_primer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        np = pytest.importorskip("numpy")
        from scribe_desktop import speech
        from scribe_desktop.transcription import CLINICAL_INITIAL_PROMPT

        apply_offline_env()
        speech_samples = np.full(625 * 512, 0.5, dtype=np.float32)
        samples = np.concatenate(
            [speech_samples, np.zeros(32 * 512, dtype=np.float32), speech_samples]
        )
        calls = _fake_whisper_module(monkeypatch, filters=128, n_mels=128, samples=samples)
        vads: list[Path] = []

        class _Vad:
            def __init__(self, path: Path) -> None:
                vads.append(path)

            def reset(self) -> None:
                pass

            def frame_probability(self, frame: bytes) -> float:
                return _nonzero_frame(frame)

        monkeypatch.setattr(speech, "SileroVad", _Vad)
        model_dir = _snapshot_dir(tmp_path)
        audio = tmp_path / "sample.wav"
        vad_path = tmp_path / "silero-vad" / "silero_vad.onnx"
        timing = benchmark.run_app_shape(model_dir, audio, vad_path)

        assert calls[0] == {"decode": str(audio), "sampling_rate": SAMPLE_RATE}
        assert vads == [vad_path]
        windows = calls[1:]
        assert len(windows) == timing.windows == 2
        for call in windows:
            assert call["initial_prompt"] == CLINICAL_INITIAL_PROMPT
            assert call["language"] == "en"
            assert call["beam_size"] == 5
            assert call["word_timestamps"] is True
            assert call["condition_on_previous_text"] is False
            # 0.5 restored to the 16-bit sample 16384 exactly, then the
            # provider's own conversion back (0.0: each window's 0.1 s pad
            # of the silence between the two segments).
            assert set(np.unique(call["audio"]).tolist()) == {0.0, 0.5}
        assert timing.audio_seconds == pytest.approx(40.2, abs=1e-3)

    def test_an_unequal_mel_count_is_refused_before_any_window(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        np = pytest.importorskip("numpy")
        from scribe_desktop import speech
        from scribe_desktop.transcription import TranscriptionModelError

        apply_offline_env()
        calls = _fake_whisper_module(
            monkeypatch, filters=80, n_mels=128, samples=np.full(512, 0.5, dtype=np.float32)
        )
        monkeypatch.setattr(speech, "SileroVad", lambda path: types.SimpleNamespace())
        with pytest.raises(TranscriptionModelError, match="preprocessor_config.json"):
            benchmark.run_app_shape(
                _snapshot_dir(tmp_path), tmp_path / "s.wav", tmp_path / "v.onnx"
            )
        assert [call for call in calls if "audio" in call] == []

    @pytest.mark.parametrize("which", [0, 1, 2])
    def test_a_network_path_is_refused_before_any_ml_import(
        self, monkeypatch: pytest.MonkeyPatch, which: int
    ) -> None:
        apply_offline_env()
        monkeypatch.setitem(sys.modules, "faster_whisper", None)
        forbid_network_io(monkeypatch)
        paths = [Path(r"C:\m\whisper\x"), Path(r"C:\t\a.wav"), Path(r"C:\m\v.onnx")]
        paths[which] = Path(r"\\h\s\x")
        with pytest.raises(RuntimeError, match="not UNC"):
            benchmark.run_app_shape(*paths)

    def test_the_offline_env_is_asserted_first(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        for key in OFFLINE_ENV:
            monkeypatch.delenv(key, raising=False)
        with pytest.raises(OfflineEnvError):
            benchmark.run_app_shape(tmp_path, tmp_path / "a.wav", tmp_path / "v.onnx")


class TestRunSingleMelCheck:
    """D8: the benchmark worker's own load is checked like the provider's,
    before the sample is transcribed."""

    @pytest.mark.parametrize(("filters", "n_mels"), [(80, 128), (128, 80)])
    def test_an_unequal_count_is_refused_naming_the_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, filters: int, n_mels: int
    ) -> None:
        from scribe_desktop.transcription import TranscriptionModelError

        apply_offline_env()
        calls = _fake_whisper_module(monkeypatch, filters=filters, n_mels=n_mels)
        with pytest.raises(TranscriptionModelError) as exc:
            benchmark.run_single(_snapshot_dir(tmp_path), tmp_path / "a.wav", 10.0)
        assert "preprocessor_config.json is missing or wrong" in str(exc.value)
        assert f"expects {n_mels} mel filters" in str(exc.value)
        assert calls == [], "the sample is never transcribed"

    @pytest.mark.parametrize("mels", [80, 128])
    def test_an_equal_count_is_benchmarked(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mels: int
    ) -> None:
        apply_offline_env()
        calls = _fake_whisper_module(monkeypatch, filters=mels, n_mels=mels)
        result = benchmark.run_single(_snapshot_dir(tmp_path), tmp_path / "a.wav", 10.0)
        assert result.model_name == "fake-model"
        assert result.audio_seconds == 10.0 and result.word_count == 0
        assert result.app_rtf is None
        assert calls == [{"audio": str(tmp_path / "a.wav"), "word_timestamps": True}]


_TIMING = AppShapeTiming(windows=2, audio_seconds=50.0, transcribe_seconds=40.0, word_count=128)


class TestAppShapeWorker:
    """D8: the app-shape timing runs in its own fresh worker per model, a
    source run's option only; ``run_all`` joins it to the panel's result."""

    _ARGS = ("medium", Path(r"C:\m"), Path(r"C:\t\s.wav"), 53.2)

    def test_a_source_run_appends_the_flag(self) -> None:
        argv = benchmark.worker_argv(*self._ARGS, app_shape=True)
        assert argv == [*benchmark.worker_argv(*self._ARGS), "--app-shape"]
        assert argv[:3] == [sys.executable, "-m", "scribe_desktop.benchmark"]

    def test_a_packaged_build_refuses_it_and_keeps_its_shape(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        use_frozen(monkeypatch, True)
        with pytest.raises(RuntimeError, match="source checkout only"):
            benchmark.worker_argv(*self._ARGS, app_shape=True)
        assert benchmark.is_worker_argv(benchmark.worker_argv(*self._ARGS))
        assert not benchmark.is_worker_argv(
            [*benchmark.worker_argv(*self._ARGS), "--app-shape"]
        )

    @pytest.mark.parametrize("app_shape", [False, True])
    def test_run_all_joins_the_app_rtf(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, app_shape: bool
    ) -> None:
        panel = BenchmarkResult("medium", 53.2, 4.0, 26.6, 0.5, 2 * 2**30, 130)
        timing = _TIMING
        spawned: list[list[str]] = []

        def fake_run(argv: list[str], *, env: dict[str, str], **kwargs: Any) -> Any:
            spawned.append(argv)
            payload = asdict(timing) if argv[-1] == "--app-shape" else asdict(panel)
            return types.SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

        monkeypatch.setattr(benchmark, "list_whisper_candidates", lambda root: ["medium"])
        monkeypatch.setattr(benchmark, "generate_speech_sample", lambda target: 53.2)
        monkeypatch.setattr(benchmark.subprocess, "run", fake_run)
        [result] = benchmark.run_all(tmp_path, app_shape=app_shape)
        assert [argv[-1] == "--app-shape" for argv in spawned] == (
            [False, True] if app_shape else [False]
        )
        assert result == (replace(panel, app_rtf=0.8) if app_shape else panel)
        assert result.status == ("warning" if app_shape else "ok")

    def test_a_failed_app_shape_worker_names_the_model(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        panel = BenchmarkResult("medium", 53.2, 4.0, 26.6, 0.5, 1, 1)

        def fake_run(argv: list[str], *, env: dict[str, str], **kwargs: Any) -> Any:
            if argv[-1] == "--app-shape":
                return types.SimpleNamespace(returncode=1, stdout="", stderr="VadModelError")
            return types.SimpleNamespace(returncode=0, stdout=json.dumps(asdict(panel)), stderr="")

        monkeypatch.setattr(benchmark, "list_whisper_candidates", lambda root: ["medium"])
        monkeypatch.setattr(benchmark, "generate_speech_sample", lambda target: 53.2)
        monkeypatch.setattr(benchmark.subprocess, "run", fake_run)
        with pytest.raises(
            RuntimeError, match="benchmark subprocess for medium failed: VadModelError"
        ):
            benchmark.run_all(tmp_path, app_shape=True)

    def test_main_passes_the_flag_to_run_all_and_prints_the_column(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        given: list[tuple[Path, list[str] | None, bool]] = []

        def fake_run_all(
            root: Path, names: list[str] | None = None, *, app_shape: bool = False
        ) -> list[BenchmarkResult]:
            given.append((root, names, app_shape))
            return [_app(0.4, 0.6)]

        monkeypatch.setattr(benchmark, "run_all", fake_run_all)
        assert benchmark.main(["--app-shape", "--models", "medium"]) == 0
        assert given == [(benchmark.default_models_root(), ["medium"], True)]
        assert capsys.readouterr().out.split("\n")[1] == _APP_HEADER
        given.clear()
        assert benchmark.main(["--models", "medium"]) == 0
        assert given[0][2] is False

    def test_the_worker_times_the_app_shape_with_the_vad_beside_its_models(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from scribe_desktop import speech

        monkeypatch.setenv(benchmark._WORKER_ENV, "1")
        timing = _TIMING
        given: list[tuple[Path, Path, Path]] = []

        def fake_run_app_shape(model_dir: Path, audio: Path, vad: Path) -> AppShapeTiming:
            given.append((model_dir, audio, vad))
            return timing

        monkeypatch.setattr(benchmark, "run_app_shape", fake_run_app_shape)
        monkeypatch.setattr(benchmark, "run_single", lambda *a: pytest.fail("panel timed"))
        argv = ["--single", "medium", "--audio", r"C:\t\s.wav", "--audio-seconds", "53.2"]
        assert benchmark.main([*argv, "--app-shape"]) == 0
        root = benchmark.default_models_root()
        # The VAD path is the one the app loads (``speech.default_vad_model_path``).
        assert given == [
            (root / "whisper" / "medium", Path(r"C:\t\s.wav"), speech.default_vad_model_path())
        ]
        assert json.loads(capsys.readouterr().out) == asdict(timing)


# Installation plan Task 2.6: the source run's DEV models root, never the
# production data folder (C8).
_REAL_ML_ROOT = real_ml_models_root()


@pytest.mark.skipif(
    _REAL_ML_ROOT is None or not (_REAL_ML_ROOT / "whisper" / "small" / "model.bin").is_file(),
    reason=real_ml_skip_reason("whisper small"),
)
class TestRealModelSmoke:
    def test_small_model_loads_offline(self) -> None:
        # Offline kill-switches BEFORE the ML import: the import itself must
        # already be network-inert (peer round 10, PR-MED-009).
        apply_offline_env()
        assert_offline_env()
        faster_whisper = pytest.importorskip("faster_whisper")
        assert _REAL_ML_ROOT is not None  # the skip gate above
        model_dir = _REAL_ML_ROOT / "whisper" / "small"
        model = faster_whisper.WhisperModel(
            str(model_dir), device="cpu", compute_type="int8", local_files_only=True
        )
        assert model is not None
