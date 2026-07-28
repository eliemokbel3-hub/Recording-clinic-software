"""Tests for the RTF benchmark harness (benchmark math + offline enforcement).

ML-free by design: benchmark.py lazy-imports the ML stack, so everything here
runs without faster-whisper installed. The one test that would touch a real
model is guarded with importorskip + a local-model-cache presence check.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scribe_desktop import benchmark
from scribe_desktop.benchmark import (
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


@pytest.mark.skipif(
    not (
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "ClinikoScribe"
        / "models"
        / "whisper"
        / "small"
        / "model.bin"
    ).is_file(),
    reason="local model cache absent (run scripts/setup-models.py)",
)
class TestRealModelSmoke:
    def test_small_model_loads_offline(self) -> None:
        # Offline kill-switches BEFORE the ML import: the import itself must
        # already be network-inert (peer round 10, PR-MED-009).
        apply_offline_env()
        assert_offline_env()
        faster_whisper = pytest.importorskip("faster_whisper")
        model_dir = (
            Path(os.environ["LOCALAPPDATA"]) / "ClinikoScribe" / "models" / "whisper" / "small"
        )
        model = faster_whisper.WhisperModel(
            str(model_dir), device="cpu", compute_type="int8", local_files_only=True
        )
        assert model is not None
