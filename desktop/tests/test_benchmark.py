"""Tests for the RTF benchmark harness (benchmark math + offline enforcement).

ML-free by design: benchmark.py lazy-imports the ML stack, so everything here
runs without faster-whisper installed. The one test that would touch a real
model is guarded with importorskip + a local-model-cache presence check.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from conftest import real_ml_models_root, real_ml_skip_reason
from scribe_desktop import benchmark
from scribe_desktop.benchmark import (
    LIVE_WINDOW_SECONDS,
    OFFLINE_ENV,
    RTF_MARGIN,
    RTF_REQUIRED,
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
)


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
