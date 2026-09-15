"""Practitioner-profile plan Phase 1 Task 1.1: ``speaker_embedding``.

The front-end tests moved here from ``test_setup_scripts.py`` (Task 1.1's
"one front-end, one load contract" sub-bullet): the smoke imports the
module's ``fbank`` / ``load_onnx_session`` / ``embed_features``, so the
shipped front-end and the D-P1 evidence are one piece of code and it is
tested once, here. Everything runs without the real model: the load
contract is driven through ``sys.modules`` stubs (an un-importable
``onnxruntime``, a fake session factory) against files under ``tmp_path``,
and the real-model tests are skip-marked when the local cache is absent
(agent shells cannot see the practitioner's cache — ``docs/lessons.md``).
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from scribe_desktop import speaker_embedding as se
from scribe_desktop.benchmark import OFFLINE_ENV, OfflineEnvError, apply_offline_env
from scribe_desktop.speaker_embedding import (
    ATTRIBUTION_THRESHOLD,
    DEFAULT_WINDOW,
    MEL_BINS,
    SHIPPED_SPEAKER_EMBEDDER,
    SPEAKER_MODEL_SHA256,
    MockSpeakerEmbedder,
    OnnxSpeakerEmbedder,
    SpeakerModelError,
    SpectralSpeakerEmbedder,
    build_speaker_embedder,
    default_speaker_model_path,
    embed_features,
    fbank,
    load_onnx_session,
    speaker_embedder_available,
    speaker_model_available,
)

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _offline() -> None:
    # The front-end asserts the kill-switches before it imports numpy (the
    # transcription module's binding pattern); every test here starts offline.
    apply_offline_env()


def _tone_pcm(np: Any, seconds: float, hz: float = 1000.0, amplitude: int = 8000) -> bytes:
    t = np.arange(int(seconds * 16_000), dtype=np.float64) / 16_000.0
    return (amplitude * np.sin(2.0 * np.pi * hz * t)).astype(np.int16).tobytes()


def _noise_pcm(np: Any, samples: int, seed: int = 7) -> bytes:
    rng = np.random.default_rng(seed)
    return rng.integers(-12_000, 12_000, size=samples, dtype=np.int16).tobytes()


# --- the D-P1 constants -----------------------------------------------------------


class TestDecisionConstants:
    def test_d_p1_choice_and_threshold(self) -> None:
        assert SHIPPED_SPEAKER_EMBEDDER == "onnx"
        assert ATTRIBUTION_THRESHOLD == 0.50
        assert DEFAULT_WINDOW == "povey"

    def test_pin_is_single_sourced_with_the_setup_script(self) -> None:
        """The setup script imports the module's constants (never a second
        literal that can drift): the two surfaces are the SAME objects."""
        path = REPO / "scripts" / "setup-models.py"
        spec = importlib.util.spec_from_file_location("setup_models_for_pin_test", path)
        assert spec is not None and spec.loader is not None
        module: ModuleType = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.SPEAKER_EMBEDDING_SHA256 is se.SPEAKER_MODEL_SHA256
        assert module.SPEAKER_EMBEDDING_NAME is se.SPEAKER_MODEL_NAME
        assert module.SPEAKER_EMBEDDING_SIZE_BYTES is se.SPEAKER_MODEL_SIZE_BYTES
        promoted, _candidate = module.speaker_embedding_paths(Path("root"))
        assert promoted == Path("root") / se.SPEAKER_MODEL_SUBDIR / (
            f"{se.SPEAKER_MODEL_NAME}.onnx"
        )

    def test_pin_shape(self) -> None:
        assert len(SPEAKER_MODEL_SHA256) == 64 and int(SPEAKER_MODEL_SHA256, 16)
        assert se.SPEAKER_MODEL_SIZE_BYTES == 26_530_309

    def test_default_model_path_under_the_models_root(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert default_speaker_model_path() == (
            tmp_path
            / "ClinikoScribe"
            / "models"
            / "speaker-embedding"
            / "wespeaker-voxceleb-resnet34-LM.onnx"
        )


# --- the front-end (moved from test_setup_scripts.py) -------------------------------


class TestFrontEnd:
    def test_shape_follows_kaldi_snip_edges_framing(self) -> None:
        np = pytest.importorskip("numpy")
        for samples in (400, 559, 560, 16_000, 16_000 + 159):
            feats = fbank(_noise_pcm(np, samples))
            assert feats.shape == (1 + (samples - 400) // 160, MEL_BINS)
            assert feats.dtype == np.float32
            assert np.isfinite(feats).all()

    def test_deterministic_for_identical_input(self) -> None:
        np = pytest.importorskip("numpy")
        pcm = _noise_pcm(np, 16_000)
        first = fbank(pcm)
        second = fbank(bytes(pcm))
        assert np.array_equal(first, second)

    def test_mean_normalised_by_default(self) -> None:
        np = pytest.importorskip("numpy")
        pcm = _noise_pcm(np, 32_000)
        normalised = fbank(pcm)
        assert np.allclose(normalised.mean(axis=0), 0.0, atol=1e-3)
        raw = fbank(pcm, mean_normalise=False)
        assert not np.allclose(raw.mean(axis=0), 0.0, atol=1e-3)
        assert np.allclose(raw - raw.mean(axis=0, keepdims=True), normalised, atol=1e-4)

    def test_short_and_odd_inputs_are_refused(self) -> None:
        np = pytest.importorskip("numpy")
        with pytest.raises(ValueError, match="at least 400 samples"):
            fbank(_noise_pcm(np, 399))
        with pytest.raises(ValueError, match="even"):
            fbank(_noise_pcm(np, 400) + b"\0")
        with pytest.raises(ValueError, match="window"):
            fbank(_noise_pcm(np, 400), window="rectangular")

    def test_windows_are_kaldi_shaped_and_distinct(self) -> None:
        np = pytest.importorskip("numpy")
        hamming = se.analysis_window("hamming")
        povey = se.analysis_window("povey")
        assert hamming.shape == povey.shape == (400,)
        assert np.isclose(hamming[0], 0.08) and np.isclose(hamming[-1], 0.08)
        assert np.isclose(povey[0], 0.0) and np.isclose(povey[199], 1.0, atol=1e-4)
        pcm = _noise_pcm(np, 16_000)
        assert not np.array_equal(fbank(pcm, window="hamming"), fbank(pcm, window="povey"))

    def test_default_window_is_the_d_p1_povey_pin(self) -> None:
        np = pytest.importorskip("numpy")
        pcm = _noise_pcm(np, 16_000)
        assert np.array_equal(fbank(pcm), fbank(pcm, window="povey"))

    def test_cached_geometry_is_read_only(self) -> None:
        np = pytest.importorskip("numpy")
        for array in (se.mel_filterbank(), se.analysis_window("povey")):
            assert not array.flags.writeable
            with pytest.raises(ValueError):
                array[0] = 1.0
        assert se.mel_filterbank() is se.mel_filterbank()
        assert np.array_equal(se.analysis_window("povey"), se.analysis_window("povey"))

    def test_filterbank_geometry(self) -> None:
        np = pytest.importorskip("numpy")
        fb = se.mel_filterbank()
        assert fb.shape == (MEL_BINS, se.FFT_SIZE // 2)
        assert (fb >= 0).all() and (fb <= 1).all()
        assert (fb.sum(axis=1) > 0).all(), "every filter covers at least one FFT bin"
        centers = se.filter_center_frequencies_hz()
        assert centers.shape == (MEL_BINS,)
        assert np.all(np.diff(centers) > 0)
        assert centers[0] > se.LOW_FREQ_HZ and centers[-1] < 8000.0

    def test_pure_tone_peaks_in_the_matching_filter(self) -> None:
        np = pytest.importorskip("numpy")
        raw = fbank(_tone_pcm(np, 1.0, hz=1000.0), mean_normalise=False)
        peak = int(np.argmax(raw.mean(axis=0)))
        centers = se.filter_center_frequencies_hz()
        assert abs(float(centers[peak]) - 1000.0) < 120.0, centers[peak]

    def test_front_end_requires_the_offline_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in OFFLINE_ENV:
            monkeypatch.delenv(key, raising=False)
        with pytest.raises(OfflineEnvError):
            fbank(b"\0" * 800)


# --- fakes for the load contract ----------------------------------------------------


class _Tensor:
    def __init__(self, name: str, shape: list[Any], type_: str = "tensor(float)") -> None:
        self.name = name
        self.shape = shape
        self.type = type_


class _FakeSession:
    """Rank-3 ``(batch, frames, 80)`` in, ``(1, 4)`` out by default; the
    embedding is a deterministic function of the features so different audio
    separates. ``output_shape`` reshapes/tiles that vector into any layout so
    the output-validation contract can be exercised (round 6 PR-MED-018)."""

    def __init__(
        self,
        feature_dim: Any = 80,
        rank: int = 3,
        output_shape: tuple[int, ...] = (1, 4),
        inputs: int = 1,
    ) -> None:
        self.feeds: list[Any] = []
        shape = [None, None, feature_dim] if rank == 3 else [None, feature_dim]
        self._inputs = [_Tensor(f"feats{i or ''}", shape) for i in range(inputs)]
        self._output_shape = output_shape

    def get_inputs(self) -> list[_Tensor]:
        return self._inputs

    def get_outputs(self) -> list[_Tensor]:
        return [_Tensor("embs", list(self._output_shape))]

    def run(self, _names: object, feeds: dict[str, Any]) -> list[Any]:
        import numpy as np

        feats = feeds["feats"]
        self.feeds.append(feats)
        flat = feats.reshape(-1, feats.shape[-1])
        vector = np.array(
            [flat[:, :20].std(), flat[:, 20:40].std(), flat[:, 40:60].std(), 1.0],
            dtype=np.float32,
        )
        size = int(np.prod(self._output_shape))
        return [np.resize(vector, size).reshape(self._output_shape)]


def _fake_onnxruntime(session_factory: Any) -> SimpleNamespace:
    """A stand-in ``onnxruntime`` module: options, telemetry opt-out and a
    session constructor that returns ``session_factory()``."""
    calls: list[str] = []

    class _Options:
        inter_op_num_threads = 0
        intra_op_num_threads = 0

    def _session(path: str, sess_options: Any, providers: list[str]) -> Any:
        calls.append(f"session:{providers}")
        return session_factory()

    return SimpleNamespace(
        SessionOptions=_Options,
        disable_telemetry_events=lambda: calls.append("telemetry-off"),
        InferenceSession=_session,
        calls=calls,
    )


def _pinned_fake_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fake model file whose digest IS the (monkeypatched) pin."""
    model = tmp_path / "model.onnx"
    model.write_bytes(b"fake model bytes " * 64)
    monkeypatch.setattr(se, "SPEAKER_MODEL_SHA256", hashlib.sha256(model.read_bytes()).hexdigest())
    return model


# --- the load contract --------------------------------------------------------------


class TestLoadContract:
    def test_load_requires_offline_env(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        for key in OFFLINE_ENV:
            monkeypatch.delenv(key, raising=False)
        with pytest.raises(OfflineEnvError):
            load_onnx_session(tmp_path / "model.onnx")

    def test_missing_and_unc_paths_refused_before_onnxruntime_import(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # ``None`` in sys.modules makes ``import onnxruntime`` raise ImportError,
        # so a check that ran AFTER the import would fail this test loudly.
        monkeypatch.setitem(sys.modules, "onnxruntime", None)
        with pytest.raises(SpeakerModelError, match="setup-models"):
            load_onnx_session(tmp_path / "nope.onnx")
        with pytest.raises(SpeakerModelError, match="UNC"):
            load_onnx_session(Path(r"\\evil-host\share\model.onnx"))

    def test_digest_mismatch_refused_before_onnxruntime_import(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Round 1 PR-MED-003: a shape-compatible substitute cannot pass as the
        pinned model — the file's bytes are digested and compared BEFORE the
        runtime is even imported, and the message names both digests."""
        monkeypatch.setitem(sys.modules, "onnxruntime", None)
        model = tmp_path / "substitute.onnx"
        model.write_bytes(b"not the pinned bytes")
        actual = hashlib.sha256(model.read_bytes()).hexdigest()
        with pytest.raises(SpeakerModelError, match="not the pinned model") as exc:
            load_onnx_session(model, expected_sha256=SPEAKER_MODEL_SHA256)
        assert SPEAKER_MODEL_SHA256 in str(exc.value) and actual in str(exc.value)
        with pytest.raises(SpeakerModelError, match="not the pinned model"):
            OnnxSpeakerEmbedder(model)

    def test_present_file_with_onnxruntime_unimportable_is_typed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Round 6 PR-LOW-020: the path checks pass (the file exists), so the
        # failure now happens at the import - it must still be typed.
        model = tmp_path / "present.onnx"
        model.write_bytes(b"not really a model")
        monkeypatch.setitem(sys.modules, "onnxruntime", None)
        with pytest.raises(SpeakerModelError, match=r"not importable.*\[ml\]"):
            load_onnx_session(model)

    def test_session_setup_failure_is_typed_and_names_the_step(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        model = tmp_path / "present.onnx"
        model.write_bytes(b"not really a model")

        def _boom() -> None:
            raise RuntimeError("options exploded")

        monkeypatch.setitem(sys.modules, "onnxruntime", SimpleNamespace(SessionOptions=_boom))
        with pytest.raises(SpeakerModelError, match=r"\(session options\)") as exc:
            load_onnx_session(model)
        assert "options exploded" in str(exc.value)

    def test_session_is_cpu_only_with_telemetry_off(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        model = tmp_path / "present.onnx"
        model.write_bytes(b"x")
        fake = _fake_onnxruntime(_FakeSession)
        monkeypatch.setitem(sys.modules, "onnxruntime", fake)
        load_onnx_session(model)
        assert fake.calls == ["telemetry-off", "session:['CPUExecutionProvider']"]

    def test_embed_batches_rank3_and_normalises(self) -> None:
        np = pytest.importorskip("numpy")
        session = _FakeSession()
        feats = fbank(_noise_pcm(np, 16_000))
        vector = embed_features(session, feats)
        assert session.feeds[0].shape == (1, feats.shape[0], 80)
        assert session.feeds[0].dtype == np.float32
        assert vector.shape == (4,) and np.isclose(np.linalg.norm(vector), 1.0)

    def test_embed_feeds_rank2_unbatched(self) -> None:
        np = pytest.importorskip("numpy")
        session = _FakeSession(rank=2)
        feats = fbank(_noise_pcm(np, 16_000))
        embed_features(session, feats)
        assert session.feeds[0].shape == feats.shape

    @pytest.mark.parametrize("output_shape", [(4,), (1, 4), (1, 256), (7,)])
    def test_embed_accepts_one_vector_per_utterance(self, output_shape: tuple[int, ...]) -> None:
        np = pytest.importorskip("numpy")
        feats = fbank(_noise_pcm(np, 16_000))
        vector = embed_features(_FakeSession(output_shape=output_shape), feats)
        assert vector.shape == (output_shape[-1],)
        assert np.isclose(np.linalg.norm(vector), 1.0)

    @pytest.mark.parametrize(
        ("output_shape", "reason"),
        [
            ((1, 3, 4), "framewise"),
            ((2, 4), "multi-vector"),
            ((1, 1, 4), "rank 3 even with a singleton batch"),
            ((1,), "scalar"),
            ((1, 1), "one element"),
        ],
    )
    def test_embed_refuses_outputs_that_are_not_one_vector(
        self, output_shape: tuple[int, ...], reason: str
    ) -> None:
        np = pytest.importorskip("numpy")
        feats = fbank(_noise_pcm(np, 16_000))
        with pytest.raises(SpeakerModelError, match="embs"):
            embed_features(_FakeSession(output_shape=output_shape), feats)

    def test_embed_refuses_a_feature_dim_mismatch_and_multi_input_models(self) -> None:
        np = pytest.importorskip("numpy")
        feats = fbank(_noise_pcm(np, 16_000))
        with pytest.raises(SpeakerModelError, match="expects 40 features"):
            embed_features(_FakeSession(feature_dim=40), feats)
        with pytest.raises(SpeakerModelError, match="single-input"):
            embed_features(_FakeSession(inputs=2), feats)


# --- OnnxSpeakerEmbedder through a fake runtime ------------------------------------------


class TestOnnxSpeakerEmbedder:
    def test_construction_probes_shape_and_smoke_infers_once(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        np = pytest.importorskip("numpy")
        model = _pinned_fake_model(tmp_path, monkeypatch)
        session = _FakeSession()
        monkeypatch.setitem(sys.modules, "onnxruntime", _fake_onnxruntime(lambda: session))
        embedder = OnnxSpeakerEmbedder(model)
        assert len(session.feeds) == 1, "load must smoke-infer exactly once"
        assert session.feeds[0].shape == (1, 1 + (16_000 - 400) // 160, 80)
        assert embedder.embedding_dim == 4
        assert embedder.model_id == se.ONNX_MODEL_ID == "wespeaker-voxceleb-resnet34-LM"
        assert embedder.model_sha256 == se.SPEAKER_MODEL_SHA256
        assert embedder.model_path == model
        vector = embedder.embed(_noise_pcm(np, 16_000))
        assert vector.shape == (4,) and np.isclose(np.linalg.norm(vector), 1.0)
        assert vector.dtype == np.float32

    @pytest.mark.parametrize("output_shape", [(1, 3, 4), (2, 4), (1,)])
    def test_incompatible_output_layout_fails_at_load(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, output_shape: tuple[int, ...]
    ) -> None:
        model = _pinned_fake_model(tmp_path, monkeypatch)
        monkeypatch.setitem(
            sys.modules,
            "onnxruntime",
            _fake_onnxruntime(lambda: _FakeSession(output_shape=output_shape)),
        )
        with pytest.raises(SpeakerModelError, match="embs"):
            OnnxSpeakerEmbedder(model)

    def test_wrong_feature_axis_fails_at_load(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        model = _pinned_fake_model(tmp_path, monkeypatch)
        monkeypatch.setitem(
            sys.modules, "onnxruntime", _fake_onnxruntime(lambda: _FakeSession(feature_dim=40))
        )
        with pytest.raises(SpeakerModelError, match="expects 40 features"):
            OnnxSpeakerEmbedder(model)

    def test_a_run_that_raises_fails_at_load_as_smoke_inference(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        model = _pinned_fake_model(tmp_path, monkeypatch)

        class _Broken(_FakeSession):
            def run(self, _names: object, feeds: dict[str, Any]) -> list[Any]:
                raise RuntimeError("shape mismatch")

        monkeypatch.setitem(sys.modules, "onnxruntime", _fake_onnxruntime(_Broken))
        with pytest.raises(SpeakerModelError, match="smoke inference"):
            OnnxSpeakerEmbedder(model)

    def test_default_path_is_the_models_cache(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        monkeypatch.setitem(sys.modules, "onnxruntime", None)
        with pytest.raises(SpeakerModelError, match="setup-models") as exc:
            OnnxSpeakerEmbedder()
        assert str(default_speaker_model_path()) in str(exc.value)


# --- the file-less embedders ------------------------------------------------------------


class TestSpectralSpeakerEmbedder:
    def test_identity_and_shape(self) -> None:
        np = pytest.importorskip("numpy")
        embedder = SpectralSpeakerEmbedder()
        assert embedder.model_id == "spectral-cmn-v1"
        assert embedder.model_sha256 == ""
        assert embedder.embedding_dim == 25
        vector = embedder.embed(_noise_pcm(np, 16_000))
        assert vector.shape == (25,) and vector.dtype == np.float32
        assert np.isclose(np.linalg.norm(vector), 1.0)

    def test_is_the_pipelines_cmn_embedding(self) -> None:
        np = pytest.importorskip("numpy")
        from scribe_desktop.transcription import _segment_embedding

        pcm = _tone_pcm(np, 0.5, hz=440.0)
        raw = _segment_embedding(pcm, np)
        assert np.allclose(SpectralSpeakerEmbedder().embed(pcm), raw / np.linalg.norm(raw))

    def test_refuses_empty_or_odd_pcm(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            SpectralSpeakerEmbedder().embed(b"")
        with pytest.raises(ValueError, match="even"):
            SpectralSpeakerEmbedder().embed(b"\0")


class TestMockSpeakerEmbedder:
    def test_mapped_vectors_are_returned_normalised(self) -> None:
        np = pytest.importorskip("numpy")
        embedder = MockSpeakerEmbedder({b"aa": (3.0, 0.0, 0.0, 0.0)})
        vector = embedder.embed(b"aa")
        assert np.allclose(vector, [1.0, 0.0, 0.0, 0.0])
        assert embedder.model_id == "mock-speaker-embedder-v1" and embedder.embedding_dim == 4

    def test_unmapped_pcm_embeds_deterministically_and_distinctly(self) -> None:
        np = pytest.importorskip("numpy")
        embedder = MockSpeakerEmbedder(embedding_dim=8)
        first = embedder.embed(b"\x01\x02" * 100)
        again = embedder.embed(b"\x01\x02" * 100)
        other = embedder.embed(b"\x03\x04" * 100)
        assert np.array_equal(first, again)
        assert not np.allclose(first, other)
        assert first.shape == (8,) and np.isclose(np.linalg.norm(first), 1.0)

    def test_holds_only_the_callers_map_and_the_lengths_it_embedded(self) -> None:
        """Round 12 LOW-001: the double keeps the caller-supplied map (its
        keys are PCM the test chose) and the LENGTH of what it embedded —
        embedding never adds bytes to anything it holds."""
        pytest.importorskip("numpy")
        embedder = MockSpeakerEmbedder({b"aa": (3.0, 0.0, 0.0, 0.0)})
        embedder.embed(b"aa")
        embedder.embed(b"\x01\x02" * 50)
        assert embedder.embedded_lengths == [2, 100]
        assert set(embedder._vectors) == {b"aa"}  # noqa: SLF001 - the retention claim under test
        retained = [v for v in vars(embedder).values() if isinstance(v, bytes | bytearray)]
        assert retained == []

    def test_refuses_a_mismatched_map_or_tiny_dim(self) -> None:
        with pytest.raises(ValueError, match="embedding_dim"):
            MockSpeakerEmbedder({b"a": (1.0, 0.0)})
        with pytest.raises(ValueError, match="at least 2"):
            MockSpeakerEmbedder(embedding_dim=1)


# --- availability and the factory (D16) -------------------------------------------------


class TestAvailabilityAndFactory:
    def test_spectral_is_always_available_and_built(self) -> None:
        assert speaker_embedder_available("spectral") is True
        assert isinstance(build_speaker_embedder("spectral"), SpectralSpeakerEmbedder)

    def test_onnx_availability_is_a_stat_of_the_pinned_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert speaker_embedder_available("onnx") is False
        assert speaker_embedder_available() is False  # the shipped kind
        path = default_speaker_model_path()
        path.parent.mkdir(parents=True)
        path.write_bytes(b"present (the digest is checked at load, not here)")
        assert speaker_embedder_available("onnx") is True

    def test_unc_availability_probe_refuses_without_io(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _boom(self: Path) -> bool:
            raise AssertionError("stat/is_file reached on a UNC path")

        monkeypatch.setattr(Path, "is_file", _boom)
        assert speaker_model_available(Path(r"\\evil-host\share\model.onnx")) is False
        monkeypatch.setenv("LOCALAPPDATA", r"\\evil-host\share")
        assert speaker_model_available() is False

    def test_factory_builds_the_onnx_embedder_and_never_substitutes(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Round 1 PR-MED-005: with the model absent the factory RAISES; the
        spectral embedder is never handed back in its place."""
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        monkeypatch.setitem(sys.modules, "onnxruntime", None)
        with pytest.raises(SpeakerModelError, match="setup-models"):
            build_speaker_embedder()


# --- the real model, when the cache is visible ------------------------------------------


@pytest.mark.skipif(
    not speaker_model_available(),
    reason="local model cache absent (run scripts/setup-models.py --only speaker-embedding)",
)
class TestRealModel:
    def test_pinned_model_loads_and_embeds(self) -> None:
        np = pytest.importorskip("numpy")
        pytest.importorskip("onnxruntime")
        embedder = OnnxSpeakerEmbedder()
        assert embedder.embedding_dim == 256
        assert embedder.model_sha256 == SPEAKER_MODEL_SHA256
        a = embedder.embed(_tone_pcm(np, 1.0, hz=220.0))
        b = embedder.embed(_tone_pcm(np, 1.0, hz=220.0))
        assert np.allclose(a, b)
        assert np.isclose(np.linalg.norm(a), 1.0, atol=1e-5)
