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
  the model cache is consulted); candidate mode (an entry with an EMPTY pin,
  monkeypatched - the route the shipped entry took at Task 0.4: a fetch
  lands as ``.onnx.candidate`` and prints size + SHA-256, is never promoted,
  an existing candidate is re-reported without network, an empty URL and a
  tiny body are refused, the default run skips the entry visibly); pinned
  mode with a fake pin (a matching candidate is promoted, a wrong digest
  refuses and leaves the candidate, ``--candidate-url`` refused, a pinned
  download verifies); and the SHIPPED pin as of Task 0.5 (2026-09-15): the
  constants are a real https URL, the recorded size and a 64-hex digest, the
  default run includes the entry, a wrong-digest candidate is refused
  against the real pin and left un-promoted, ``--candidate-url`` is refused
  through the CLI, and a pinned download of wrong bytes writes nothing.
- the smoke: since Task 1.1 its front-end, loader and embed step are
  ``scribe_desktop.speaker_embedding``'s (pinned by identity here; their
  behaviour is tested in ``test_speaker_embedding.py``); its cosine matrix
  and text-free rendering; the whole ``main`` path through a fake session.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import wave
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

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

    def test_default_run_includes_the_entry_under_the_shipped_pin(
        self,
        setup_models: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        # No pin monkeypatch: the constants as shipped (Task 0.5) decide.
        calls: list[str] = []
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


class TestShippedSpeakerEmbeddingPin:
    """Task 0.5 (2026-09-15): the entry ships PINNED. Nothing here monkeypatches
    the pin constants - these tests hold against the values in the script."""

    def test_constants_are_a_real_pin(self, setup_models: ModuleType) -> None:
        assert setup_models.speaker_embedding_pinned()
        assert setup_models.SPEAKER_EMBEDDING_URL.startswith("https://huggingface.co/")
        assert setup_models.SPEAKER_EMBEDDING_URL.endswith(".onnx")
        sha = setup_models.SPEAKER_EMBEDDING_SHA256
        assert len(sha) == 64 and int(sha, 16) >= 0
        size = setup_models.SPEAKER_EMBEDDING_SIZE_BYTES
        assert size == 26_530_309
        assert size > setup_models.SPEAKER_EMBEDDING_MIN_BYTES
        assert str(size) in setup_models.SPEAKER_EMBEDDING_EXPECTED_SIZE

    def test_wrong_digest_candidate_is_refused_and_left_unpromoted(
        self, setup_models: ModuleType, tmp_path: Path
    ) -> None:
        # The pin test the task names: a candidate whose bytes do not hash to
        # the shipped pin is refused, named with both digests, never promoted.
        target, candidate = setup_models.speaker_embedding_paths(tmp_path)
        candidate.parent.mkdir(parents=True)
        candidate.write_bytes(FAKE_MODEL)
        with pytest.raises(SystemExit, match="checksum mismatch") as exc:
            setup_models.fetch_speaker_embedding(tmp_path)
        assert setup_models.SPEAKER_EMBEDDING_SHA256 in str(exc.value)
        assert FAKE_SHA in str(exc.value)
        assert candidate.read_bytes() == FAKE_MODEL and not target.exists()

    def test_candidate_url_is_refused_through_the_cli(
        self,
        setup_models: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(setup_models, "models_root", lambda: tmp_path)
        argv = ["--only", "speaker-embedding", "--candidate-url", "https://example.invalid/m"]
        with pytest.raises(SystemExit, match="--candidate-url is refused"):
            setup_models.main(argv)  # the real fetch function; refuses before any opener
        assert not (tmp_path / "speaker-embedding").exists()

    def test_pinned_download_of_wrong_bytes_writes_nothing(
        self,
        setup_models: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        seen: list[str] = []
        monkeypatch.setattr(
            setup_models.urllib.request, "build_opener", _fake_build_opener(FAKE_MODEL, seen)
        )
        with pytest.raises(SystemExit, match="checksum mismatch"):
            setup_models.fetch_speaker_embedding(tmp_path)
        assert seen == [setup_models.SPEAKER_EMBEDDING_URL]
        assert not (tmp_path / "speaker-embedding").exists()


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
    """Task 1.1 ("one front-end, one load contract"): the smoke's front-end,
    loader and embed step ARE the runtime module's objects, so the D-P1
    evidence and the shipped code are one piece of code. Their behaviour is
    tested once, in ``test_speaker_embedding.py``; here only the identity
    and the smoke's own matrix rendering are pinned."""

    def test_front_end_and_load_contract_are_the_modules(self, smoke: ModuleType) -> None:
        from scribe_desktop import speaker_embedding

        assert smoke.fbank is speaker_embedding.fbank
        assert smoke.load_session is speaker_embedding.load_onnx_session
        assert smoke.embed is speaker_embedding.embed_features
        assert smoke.SpeakerModelError is speaker_embedding.SpeakerModelError
        assert smoke.DEFAULT_WINDOW == speaker_embedding.DEFAULT_WINDOW == "povey"
        assert "hamming" in smoke.WINDOWS  # the Task 0.4 matrix stays reproducible

    def test_help_defaults_to_the_shipped_window(
        self, smoke: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit):
            smoke.main(["--help"])
        out = capsys.readouterr().out
        assert "povey" in out and "hamming" in out

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
    """The smoke's ``main`` path through a fake session. The load contract
    and the embed step themselves are the module's and are tested in
    ``test_speaker_embedding.py`` (Task 1.1)."""

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
