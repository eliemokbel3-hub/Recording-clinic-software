"""Practitioner-profile plan, Phase 0 Task 0.3: the script surface.

``scripts/setup-models.py`` and ``scripts/speaker-embedding-smoke.py`` are
not importable by name (hyphenated, outside any package), so they are
loaded from the repository's ``scripts/`` directory through ``importlib``.
Everything here runs WITHOUT network: ``urllib.request.urlopen`` is
replaced by a refusing stub for every test, and the download paths are
driven through fakes. Nothing touches the real model cache - every fetch
is pointed at ``tmp_path``.

Covered:
- ``setup-models.py``: ``--help`` and ``--only`` validation (the new
  ``speaker-embedding`` name accepted, unknown names refused, both before
  the model cache is consulted); candidate mode (no pin: a fetch lands as
  ``.onnx.candidate`` and prints size + SHA-256, is never promoted, an
  existing candidate is re-reported without network, an empty URL and a
  tiny body are refused, the default run skips the entry visibly); pinned
  mode (a matching candidate is promoted, a wrong digest refuses and leaves
  the candidate, ``--candidate-url`` refused, a pinned download verifies).
- the smoke's front-end on synthetic PCM (shape, dtype, determinism, CMN,
  short / odd input refused, both windows, a tone landing in the right
  mel filter) and its cosine matrix; the load contract (offline asserted,
  missing and UNC paths refused BEFORE onnxruntime is imported); the whole
  ``main`` path through a fake session (text-free output).
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import sys
import wave
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from scribe_desktop.benchmark import OFFLINE_ENV, OfflineEnvError, apply_offline_env

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"


def _load_script(stem: str) -> ModuleType:
    path = SCRIPTS / f"{stem}.py"
    spec = importlib.util.spec_from_file_location(stem.replace("-", "_"), path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def setup_models() -> ModuleType:
    return _load_script("setup-models")


@pytest.fixture(scope="module")
def smoke() -> ModuleType:
    return _load_script("speaker-embedding-smoke")


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch, setup_models: ModuleType) -> None:
    def _refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network reached: a urllib opener was built or urlopen called")

    monkeypatch.setattr(setup_models.urllib.request, "urlopen", _refuse)
    monkeypatch.setattr(setup_models.urllib.request, "build_opener", _refuse)


def _fake_build_opener(body: bytes, seen: list[str], handlers: list[Any] | None = None) -> Any:
    """A stand-in for ``urllib.request.build_opener``: records the handler
    classes it was built with and the URLs opened, and serves ``body``."""

    class _Response:
        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def read(self) -> bytes:
            return body

    class _Opener:
        def open(self, url: str) -> _Response:
            seen.append(url)
            return _Response()

    def _build(*installed: Any) -> _Opener:
        if handlers is not None:
            handlers.extend(installed)
        return _Opener()

    return _build


FAKE_MODEL = bytes(range(256)) * (5 * 1024)  # 1.25 MiB, above the size floor
FAKE_SHA = hashlib.sha256(FAKE_MODEL).hexdigest()


class TestSetupModelsCli:
    def test_help_lists_speaker_embedding_and_exits_zero(
        self, setup_models: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            setup_models.main(["--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "speaker-embedding" in out
        assert "--candidate-url" in out

    def test_valid_only_set_gains_speaker_embedding(self, setup_models: ModuleType) -> None:
        assert setup_models.valid_only_names() == {
            "silero-vad",
            "speaker-embedding",
            *setup_models.WHISPER_CANDIDATES,
        }

    def test_unknown_only_is_refused_naming_the_choices(
        self, setup_models: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            setup_models.main(["--only", "bogus"])
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "bogus" in err and "speaker-embedding" in err and "silero-vad" in err

    def test_candidate_url_needs_only_speaker_embedding(
        self, setup_models: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            setup_models.main(["--candidate-url", "https://example.invalid/m.onnx"])
        assert exc.value.code == 2
        assert "--only speaker-embedding" in capsys.readouterr().err

    @pytest.mark.parametrize("argv", [["--help"], ["--only", "bogus"]])
    def test_argument_errors_never_consult_the_model_cache(
        self, setup_models: ModuleType, monkeypatch: pytest.MonkeyPatch, argv: list[str]
    ) -> None:
        def _boom() -> Path:
            raise AssertionError("models_root() reached during argument handling")

        monkeypatch.setattr(setup_models, "models_root", _boom)
        with pytest.raises(SystemExit):
            setup_models.main(argv)

    def test_default_run_skips_the_unpinned_entry_visibly(
        self,
        setup_models: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        calls: list[str] = []
        monkeypatch.setattr(setup_models, "SPEAKER_EMBEDDING_SHA256", "")
        monkeypatch.setattr(setup_models, "models_root", lambda: tmp_path)
        monkeypatch.setattr(setup_models, "fetch_silero_vad", lambda root: calls.append("silero"))
        monkeypatch.setattr(
            setup_models,
            "fetch_whisper",
            lambda root, name, repo, rev: calls.append(f"whisper/{name}"),
        )
        monkeypatch.setattr(
            setup_models,
            "fetch_speaker_embedding",
            lambda root, **kw: calls.append("speaker"),
        )
        assert setup_models.main([]) == 0
        assert "speaker" not in calls
        assert calls[0] == "silero"
        assert {c for c in calls if c.startswith("whisper/")} == {
            f"whisper/{n}" for n in setup_models.WHISPER_CANDIDATES
        }
        out = capsys.readouterr().out
        assert "[skip] speaker-embedding" in out and "--only speaker-embedding" in out
        assert not (tmp_path / "speaker-embedding").exists()

    def test_default_run_includes_the_entry_once_pinned(
        self,
        setup_models: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        calls: list[str] = []
        monkeypatch.setattr(setup_models, "SPEAKER_EMBEDDING_SHA256", FAKE_SHA)
        monkeypatch.setattr(setup_models, "models_root", lambda: tmp_path)
        monkeypatch.setattr(setup_models, "fetch_silero_vad", lambda root: None)
        monkeypatch.setattr(setup_models, "fetch_whisper", lambda *a: None)
        monkeypatch.setattr(
            setup_models,
            "fetch_speaker_embedding",
            lambda root, **kw: calls.append(f"speaker:{kw.get('candidate_url')}"),
        )
        assert setup_models.main([]) == 0
        assert calls == ["speaker:None"]

    def test_only_speaker_embedding_passes_the_candidate_url_through(
        self,
        setup_models: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        calls: list[str] = []
        monkeypatch.setattr(setup_models, "models_root", lambda: tmp_path)
        monkeypatch.setattr(
            setup_models,
            "fetch_silero_vad",
            lambda root: calls.append("silero"),
        )
        monkeypatch.setattr(
            setup_models,
            "fetch_whisper",
            lambda *a: calls.append("whisper"),
        )
        monkeypatch.setattr(
            setup_models,
            "fetch_speaker_embedding",
            lambda root, **kw: calls.append(f"speaker:{kw.get('candidate_url')}:{root}"),
        )
        argv = ["--only", "speaker-embedding", "--candidate-url", "https://example.invalid/m"]
        assert setup_models.main(argv) == 0
        assert calls == [f"speaker:https://example.invalid/m:{tmp_path}"]


class TestSpeakerEmbeddingCandidateMode:
    @pytest.fixture(autouse=True)
    def _unpinned(self, monkeypatch: pytest.MonkeyPatch, setup_models: ModuleType) -> None:
        monkeypatch.setattr(setup_models, "SPEAKER_EMBEDDING_SHA256", "")
        monkeypatch.setattr(setup_models, "SPEAKER_EMBEDDING_URL", "")

    def test_paths(self, setup_models: ModuleType, tmp_path: Path) -> None:
        target, candidate = setup_models.speaker_embedding_paths(tmp_path)
        name = setup_models.SPEAKER_EMBEDDING_NAME
        assert target == tmp_path / "speaker-embedding" / f"{name}.onnx"
        assert candidate == tmp_path / "speaker-embedding" / f"{name}.onnx.candidate"
        assert not setup_models.speaker_embedding_pinned()

    def test_no_url_is_refused_naming_the_flag(
        self, setup_models: ModuleType, tmp_path: Path
    ) -> None:
        with pytest.raises(SystemExit, match="--candidate-url"):
            setup_models.fetch_speaker_embedding(tmp_path)
        assert not (tmp_path / "speaker-embedding").exists()

    def test_non_https_url_is_refused(self, setup_models: ModuleType, tmp_path: Path) -> None:
        with pytest.raises(SystemExit, match="https://"):
            setup_models.fetch_speaker_embedding(
                tmp_path, candidate_url="http://example.invalid/m.onnx"
            )
        assert not (tmp_path / "speaker-embedding").exists()

    def test_download_lands_as_candidate_with_size_and_digest(
        self,
        setup_models: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        seen: list[str] = []
        monkeypatch.setattr(
            setup_models.urllib.request, "build_opener", _fake_build_opener(FAKE_MODEL, seen)
        )
        url = "https://example.invalid/model.onnx"
        setup_models.fetch_speaker_embedding(tmp_path, candidate_url=url)
        target, candidate = setup_models.speaker_embedding_paths(tmp_path)
        assert seen == [url]
        assert candidate.read_bytes() == FAKE_MODEL
        assert not target.exists(), "candidate mode must never promote"
        assert not candidate.with_name(candidate.name + ".part").exists()
        out = capsys.readouterr().out
        assert FAKE_SHA in out
        assert f"{len(FAKE_MODEL)} bytes" in out
        assert ".onnx.candidate" in out and "NOT promoted" in out

    def test_existing_candidate_is_reported_without_network(
        self,
        setup_models: ModuleType,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        target, candidate = setup_models.speaker_embedding_paths(tmp_path)
        candidate.parent.mkdir(parents=True)
        candidate.write_bytes(FAKE_MODEL)
        setup_models.fetch_speaker_embedding(tmp_path)  # no URL needed, no urlopen
        out = capsys.readouterr().out
        assert FAKE_SHA in out and "[skip]" in out
        assert candidate.read_bytes() == FAKE_MODEL
        assert not target.exists()

    def test_tiny_body_is_refused_and_nothing_is_written(
        self,
        setup_models: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            setup_models.urllib.request,
            "build_opener",
            _fake_build_opener(b"<html>login</html>", []),
        )
        with pytest.raises(SystemExit, match="error page or a stub"):
            setup_models.fetch_speaker_embedding(
                tmp_path, candidate_url="https://example.invalid/m.onnx"
            )
        assert not (tmp_path / "speaker-embedding").exists()


class TestSpeakerEmbeddingRedirectPolicy:
    """Peer round 6 PR-HIGH-002. The redirect handler is driven through the
    stdlib's own ``http_error_302`` with a fake ``parent`` opener, so the
    stdlib's default behaviour (an https -> http hop IS followed) and the
    project's handler (refused BEFORE the hop is fetched) are both proven
    without a socket."""

    @staticmethod
    def _drive(
        setup_models: ModuleType, handler: Any, location: str, opened: list[str]
    ) -> None:
        """Feed one 302 with ``Location: location`` to ``handler`` through the
        stdlib's ``http_error_302``; every URL the handler goes on to open
        lands in ``opened`` (the fake parent never touches a socket)."""

        class _Parent:
            def open(self, req: Any, timeout: object = None) -> str:
                opened.append(req.full_url)
                return "opened"

        handler.parent = _Parent()
        req = setup_models.urllib.request.Request("https://example.invalid/model.onnx")
        req.timeout = None  # OpenerDirector.open sets this before handlers run
        handler.http_error_302(req, io.BytesIO(b""), 302, "Found", {"location": location})

    def test_stdlib_default_follows_an_https_to_http_downgrade(
        self, setup_models: ModuleType
    ) -> None:
        # The premise of the finding, proven here rather than assumed.
        opened: list[str] = []
        default = setup_models.urllib.request.HTTPRedirectHandler()
        self._drive(setup_models, default, "http://cdn.example.invalid/model.onnx", opened)
        assert opened == ["http://cdn.example.invalid/model.onnx"]

    def test_project_handler_refuses_a_downgrade_before_fetching_it(
        self, setup_models: ModuleType
    ) -> None:
        opened: list[str] = []
        handler = setup_models._HttpsOnlyRedirectHandler()
        with pytest.raises(SystemExit, match="non-https target") as exc:
            self._drive(setup_models, handler, "http://cdn.example.invalid/model.onnx", opened)
        assert "no candidate was written" in str(exc.value)
        assert opened == [], "the downgraded hop must never be requested"

    def test_project_handler_keeps_ordinary_https_redirects(
        self, setup_models: ModuleType
    ) -> None:
        opened: list[str] = []
        handler = setup_models._HttpsOnlyRedirectHandler()
        self._drive(setup_models, handler, "https://cdn.example.invalid/m.onnx", opened)
        # A relative Location resolves against the https origin and stays https.
        self._drive(setup_models, handler, "/mirror/m.onnx", opened)
        assert opened == [
            "https://cdn.example.invalid/m.onnx",
            "https://example.invalid/mirror/m.onnx",
        ]

    def test_chain_is_refused_at_its_first_non_https_hop(
        self, setup_models: ModuleType
    ) -> None:
        opened: list[str] = []
        handler = setup_models._HttpsOnlyRedirectHandler()
        self._drive(setup_models, handler, "https://hop1.example.invalid/m.onnx", opened)
        with pytest.raises(SystemExit, match="non-https target"):
            self._drive(setup_models, handler, "http://hop2.example.invalid/m.onnx", opened)
        assert opened == ["https://hop1.example.invalid/m.onnx"]

    def test_download_helper_installs_the_handler(
        self,
        setup_models: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        handlers: list[Any] = []
        monkeypatch.setattr(
            setup_models.urllib.request,
            "build_opener",
            _fake_build_opener(FAKE_MODEL, [], handlers),
        )
        assert setup_models._download_speaker_embedding("https://example.invalid/m") == FAKE_MODEL
        assert handlers == [setup_models._HttpsOnlyRedirectHandler]

    def test_refused_download_writes_no_candidate(
        self,
        setup_models: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(setup_models, "SPEAKER_EMBEDDING_SHA256", "")

        class _Opener:
            def open(self, url: str) -> None:
                raise SystemExit("speaker-embedding download refused: non-https target")

        monkeypatch.setattr(setup_models.urllib.request, "build_opener", lambda *h: _Opener())
        with pytest.raises(SystemExit, match="refused"):
            setup_models.fetch_speaker_embedding(
                tmp_path, candidate_url="https://example.invalid/m.onnx"
            )
        assert not (tmp_path / "speaker-embedding").exists()


class TestSpeakerEmbeddingPinnedMode:
    @pytest.fixture(autouse=True)
    def _pinned(self, monkeypatch: pytest.MonkeyPatch, setup_models: ModuleType) -> None:
        monkeypatch.setattr(setup_models, "SPEAKER_EMBEDDING_SHA256", FAKE_SHA)
        monkeypatch.setattr(setup_models, "SPEAKER_EMBEDDING_URL", "https://example.invalid/m")

    def test_matching_candidate_is_promoted(
        self,
        setup_models: ModuleType,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        target, candidate = setup_models.speaker_embedding_paths(tmp_path)
        candidate.parent.mkdir(parents=True)
        candidate.write_bytes(FAKE_MODEL)
        setup_models.fetch_speaker_embedding(tmp_path)
        assert target.read_bytes() == FAKE_MODEL
        assert not candidate.exists()
        out = capsys.readouterr().out
        assert "promoted" in out and FAKE_SHA in out

    def test_wrong_digest_refuses_and_leaves_the_candidate(
        self, setup_models: ModuleType, tmp_path: Path
    ) -> None:
        target, candidate = setup_models.speaker_embedding_paths(tmp_path)
        candidate.parent.mkdir(parents=True)
        candidate.write_bytes(FAKE_MODEL + b"tampered")
        with pytest.raises(SystemExit, match="checksum mismatch") as exc:
            setup_models.fetch_speaker_embedding(tmp_path)
        assert FAKE_SHA in str(exc.value)
        assert candidate.exists() and not target.exists()

    def test_candidate_url_is_refused_once_pinned(
        self, setup_models: ModuleType, tmp_path: Path
    ) -> None:
        with pytest.raises(SystemExit, match="--candidate-url is refused"):
            setup_models.fetch_speaker_embedding(
                tmp_path, candidate_url="https://example.invalid/other"
            )
        assert not (tmp_path / "speaker-embedding").exists()

    def test_present_matching_model_is_skipped(
        self,
        setup_models: ModuleType,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        target, _ = setup_models.speaker_embedding_paths(tmp_path)
        target.parent.mkdir(parents=True)
        target.write_bytes(FAKE_MODEL)
        setup_models.fetch_speaker_embedding(tmp_path)
        assert "[skip] speaker-embedding already present" in capsys.readouterr().out

    def test_pinned_download_verifies_and_writes(
        self,
        setup_models: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        seen: list[str] = []
        monkeypatch.setattr(
            setup_models.urllib.request, "build_opener", _fake_build_opener(FAKE_MODEL, seen)
        )
        setup_models.fetch_speaker_embedding(tmp_path)
        target, candidate = setup_models.speaker_embedding_paths(tmp_path)
        assert seen == ["https://example.invalid/m"]
        assert target.read_bytes() == FAKE_MODEL and not candidate.exists()

    def test_pinned_download_with_wrong_bytes_writes_nothing(
        self,
        setup_models: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            setup_models.urllib.request, "build_opener", _fake_build_opener(FAKE_MODEL[::-1], [])
        )
        with pytest.raises(SystemExit, match="checksum mismatch"):
            setup_models.fetch_speaker_embedding(tmp_path)
        assert not (tmp_path / "speaker-embedding").exists()

    def test_pinned_without_url_is_a_pin_step_error(
        self, setup_models: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(setup_models, "SPEAKER_EMBEDDING_URL", "")
        with pytest.raises(SystemExit, match="no URL recorded"):
            setup_models.fetch_speaker_embedding(tmp_path)


# --- the smoke's front-end -----------------------------------------------------


def _tone_pcm(np: Any, seconds: float, hz: float = 1000.0, amplitude: int = 8000) -> bytes:
    t = np.arange(int(seconds * 16_000), dtype=np.float64) / 16_000.0
    return (amplitude * np.sin(2.0 * np.pi * hz * t)).astype(np.int16).tobytes()


def _noise_pcm(np: Any, samples: int, seed: int = 7) -> bytes:
    rng = np.random.default_rng(seed)
    return rng.integers(-12_000, 12_000, size=samples, dtype=np.int16).tobytes()


class TestSmokeFrontEnd:
    def test_shape_follows_kaldi_snip_edges_framing(self, smoke: ModuleType) -> None:
        np = pytest.importorskip("numpy")
        for samples in (400, 559, 560, 16_000, 16_000 + 159):
            feats = smoke.fbank(_noise_pcm(np, samples))
            assert feats.shape == (1 + (samples - 400) // 160, smoke.MEL_BINS)
            assert feats.dtype == np.float32
            assert np.isfinite(feats).all()

    def test_deterministic_for_identical_input(self, smoke: ModuleType) -> None:
        np = pytest.importorskip("numpy")
        pcm = _noise_pcm(np, 16_000)
        first = smoke.fbank(pcm)
        second = smoke.fbank(bytes(pcm))
        assert np.array_equal(first, second)

    def test_mean_normalised_by_default(self, smoke: ModuleType) -> None:
        np = pytest.importorskip("numpy")
        pcm = _noise_pcm(np, 32_000)
        normalised = smoke.fbank(pcm)
        assert np.allclose(normalised.mean(axis=0), 0.0, atol=1e-3)
        raw = smoke.fbank(pcm, mean_normalise=False)
        assert not np.allclose(raw.mean(axis=0), 0.0, atol=1e-3)
        assert np.allclose(raw - raw.mean(axis=0, keepdims=True), normalised, atol=1e-4)

    def test_short_and_odd_inputs_are_refused(self, smoke: ModuleType) -> None:
        np = pytest.importorskip("numpy")
        with pytest.raises(ValueError, match="at least 400 samples"):
            smoke.fbank(_noise_pcm(np, 399))
        with pytest.raises(ValueError, match="even"):
            smoke.fbank(_noise_pcm(np, 400) + b"\0")
        with pytest.raises(ValueError, match="window"):
            smoke.fbank(_noise_pcm(np, 400), window="rectangular")

    def test_windows_are_kaldi_shaped_and_distinct(self, smoke: ModuleType) -> None:
        np = pytest.importorskip("numpy")
        hamming = smoke.analysis_window("hamming")
        povey = smoke.analysis_window("povey")
        assert hamming.shape == povey.shape == (400,)
        assert np.isclose(hamming[0], 0.08) and np.isclose(hamming[-1], 0.08)
        assert np.isclose(povey[0], 0.0) and np.isclose(povey[199], 1.0, atol=1e-4)
        pcm = _noise_pcm(np, 16_000)
        assert not np.array_equal(smoke.fbank(pcm), smoke.fbank(pcm, window="povey"))

    def test_filterbank_geometry(self, smoke: ModuleType) -> None:
        np = pytest.importorskip("numpy")
        fb = smoke.mel_filterbank()
        assert fb.shape == (smoke.MEL_BINS, smoke.FFT_SIZE // 2)
        assert (fb >= 0).all() and (fb <= 1).all()
        assert (fb.sum(axis=1) > 0).all(), "every filter covers at least one FFT bin"
        centers = smoke.filter_center_frequencies_hz()
        assert centers.shape == (smoke.MEL_BINS,)
        assert np.all(np.diff(centers) > 0)
        assert centers[0] > smoke.LOW_FREQ_HZ and centers[-1] < 8000.0

    def test_pure_tone_peaks_in_the_matching_filter(self, smoke: ModuleType) -> None:
        np = pytest.importorskip("numpy")
        raw = smoke.fbank(_tone_pcm(np, 1.0, hz=1000.0), mean_normalise=False)
        peak = int(np.argmax(raw.mean(axis=0)))
        centers = smoke.filter_center_frequencies_hz()
        assert abs(float(centers[peak]) - 1000.0) < 120.0, centers[peak]

    def test_cosine_matrix(self, smoke: ModuleType) -> None:
        np = pytest.importorskip("numpy")
        a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        c = np.array([1.0, 1.0, 0.0], dtype=np.float32) / np.sqrt(2.0)
        matrix = smoke.cosine_matrix([a, b, c])
        assert matrix.shape == (3, 3)
        assert np.allclose(np.diag(matrix), 1.0)
        assert np.allclose(matrix, matrix.T)
        assert np.isclose(matrix[0, 1], 0.0) and np.isclose(matrix[0, 2], 1 / np.sqrt(2.0))

    def test_render_matrix_is_numbers_and_names_only(self, smoke: ModuleType) -> None:
        np = pytest.importorskip("numpy")
        lines = smoke.render_matrix(["a.wav", "bb.wav"], np.array([[1.0, 0.25], [0.25, 1.0]]))
        assert len(lines) == 3
        assert lines[1].startswith("a.wav") and "1.000" in lines[1] and "0.250" in lines[1]


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
    ) -> None:
        self.feeds: list[Any] = []
        shape = [None, None, feature_dim] if rank == 3 else [None, feature_dim]
        self._inputs = [_Tensor("feats", shape)]
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


class TestSmokeModelContract:
    def test_load_requires_offline_env(
        self, smoke: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        for key in OFFLINE_ENV:
            monkeypatch.delenv(key, raising=False)
        with pytest.raises(OfflineEnvError):
            smoke.load_session(tmp_path / "model.onnx")

    def test_missing_and_unc_paths_refused_before_onnxruntime_import(
        self, smoke: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        apply_offline_env()
        # ``None`` in sys.modules makes ``import onnxruntime`` raise ImportError,
        # so a check that ran AFTER the import would fail this test loudly.
        monkeypatch.setitem(sys.modules, "onnxruntime", None)
        with pytest.raises(smoke.SpeakerModelError, match="setup-models"):
            smoke.load_session(tmp_path / "nope.onnx")
        with pytest.raises(smoke.SpeakerModelError, match="UNC"):
            smoke.load_session(Path(r"\\evil-host\share\model.onnx"))

    def test_present_file_with_onnxruntime_unimportable_is_typed(
        self, smoke: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Round 6 PR-LOW-020: the path checks pass (the file exists), so the
        # failure now happens at the import - it must still be typed.
        apply_offline_env()
        model = tmp_path / "present.onnx"
        model.write_bytes(b"not really a model")
        monkeypatch.setitem(sys.modules, "onnxruntime", None)
        with pytest.raises(smoke.SpeakerModelError, match=r"not importable.*\[ml\]"):
            smoke.load_session(model)

    def test_session_setup_failure_is_typed_and_names_the_step(
        self, smoke: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        apply_offline_env()
        model = tmp_path / "present.onnx"
        model.write_bytes(b"not really a model")

        def _boom() -> None:
            raise RuntimeError("options exploded")

        stub = SimpleNamespace(SessionOptions=_boom)
        monkeypatch.setitem(sys.modules, "onnxruntime", stub)
        with pytest.raises(smoke.SpeakerModelError, match=r"\(session options\)") as exc:
            smoke.load_session(model)
        assert "options exploded" in str(exc.value)

    def test_embed_batches_rank3_and_normalises(self, smoke: ModuleType) -> None:
        np = pytest.importorskip("numpy")
        session = _FakeSession()
        feats = smoke.fbank(_noise_pcm(np, 16_000))
        vector = smoke.embed(session, feats)
        assert session.feeds[0].shape == (1, feats.shape[0], 80)
        assert session.feeds[0].dtype == np.float32
        assert vector.shape == (4,) and np.isclose(np.linalg.norm(vector), 1.0)

    def test_embed_feeds_rank2_unbatched(self, smoke: ModuleType) -> None:
        np = pytest.importorskip("numpy")
        session = _FakeSession(rank=2)
        feats = smoke.fbank(_noise_pcm(np, 16_000))
        smoke.embed(session, feats)
        assert session.feeds[0].shape == feats.shape

    @pytest.mark.parametrize("output_shape", [(4,), (1, 4), (1, 256), (7,)])
    def test_embed_accepts_one_vector_per_utterance(
        self, smoke: ModuleType, output_shape: tuple[int, ...]
    ) -> None:
        np = pytest.importorskip("numpy")
        feats = smoke.fbank(_noise_pcm(np, 16_000))
        vector = smoke.embed(_FakeSession(output_shape=output_shape), feats)
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
        self, smoke: ModuleType, output_shape: tuple[int, ...], reason: str
    ) -> None:
        np = pytest.importorskip("numpy")
        feats = smoke.fbank(_noise_pcm(np, 16_000))
        with pytest.raises(smoke.SpeakerModelError, match="embs"):
            smoke.embed(_FakeSession(output_shape=output_shape), feats)

    def test_cosine_matrix_refuses_mixed_or_non_1d_vectors(self, smoke: ModuleType) -> None:
        np = pytest.importorskip("numpy")
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        with pytest.raises(smoke.SpeakerModelError, match="one dimension"):
            smoke.cosine_matrix([a, b])
        with pytest.raises(smoke.SpeakerModelError, match="1-D"):
            smoke.cosine_matrix([a.reshape(1, 2), a.reshape(1, 2)])

    def test_main_refuses_a_framewise_export_before_any_matrix(
        self,
        smoke: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        np = pytest.importorskip("numpy")
        monkeypatch.setattr(
            smoke, "load_session", lambda path: _FakeSession(output_shape=(1, 3, 4))
        )
        path = tmp_path / "me.wav"
        with wave.open(str(path), "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(16_000)
            writer.writeframes(_tone_pcm(np, 0.5))
        with pytest.raises(SystemExit, match="framewise or multi-vector"):
            smoke.main(["--model", str(tmp_path / "m.onnx"), str(path)])
        assert "Cosine similarity" not in capsys.readouterr().out

    def test_embed_refuses_a_feature_dim_mismatch(self, smoke: ModuleType) -> None:
        np = pytest.importorskip("numpy")
        feats = smoke.fbank(_noise_pcm(np, 16_000))
        with pytest.raises(smoke.SpeakerModelError, match="expects 40 features"):
            smoke.embed(_FakeSession(feature_dim=40), feats)

    def test_help_and_missing_model_argument(
        self, smoke: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            smoke.main(["--help"])
        assert exc.value.code == 0
        assert "--model" in capsys.readouterr().out
        with pytest.raises(SystemExit) as exc:
            smoke.main(["a.wav"])
        assert exc.value.code == 2

    def test_main_reports_dims_and_cosines_text_free(
        self,
        smoke: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        np = pytest.importorskip("numpy")
        session = _FakeSession()
        monkeypatch.setattr(smoke, "load_session", lambda path: session)
        wavs = []
        for name, pcm in (
            ("me-1.wav", _tone_pcm(np, 0.6, hz=300.0)),
            ("me-2.wav", _tone_pcm(np, 0.6, hz=310.0)),
            ("other.wav", _noise_pcm(np, 9_600)),
        ):
            path = tmp_path / name
            with wave.open(str(path), "wb") as writer:
                writer.setnchannels(1)
                writer.setsampwidth(2)
                writer.setframerate(16_000)
                writer.writeframes(pcm)
            wavs.append(str(path))
        assert smoke.main(["--model", str(tmp_path / "m.onnx.candidate"), *wavs]) == 0
        out = capsys.readouterr().out
        assert "input  feats" in out and "output embs" in out
        assert "Embedding dimension: 4" in out
        assert "me-1.wav" in out and "other.wav" in out and "0.6 s" in out
        rows = [line for line in out.splitlines() if line.strip().startswith("me-1.wav")]
        assert any("1.000" in row for row in rows), rows
        assert len(session.feeds) == 3

    def test_main_refuses_a_wrong_format_wav(
        self,
        smoke: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        np = pytest.importorskip("numpy")
        monkeypatch.setattr(smoke, "load_session", lambda path: _FakeSession())
        path = tmp_path / "stereo.wav"
        with wave.open(str(path), "wb") as writer:
            writer.setnchannels(2)
            writer.setsampwidth(2)
            writer.setframerate(16_000)
            writer.writeframes(_noise_pcm(np, 3_200))
        with pytest.raises(SystemExit, match="16 kHz|16kHz|mono|channel"):
            smoke.main(["--model", str(tmp_path / "m.onnx"), str(path)])

    def test_main_surfaces_a_load_failure_as_exit(
        self, smoke: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        with pytest.raises(SystemExit, match="setup-models"):
            smoke.main(["--model", str(tmp_path / "absent.onnx"), str(tmp_path / "a.wav")])
