"""Note-learning-and-styles plan Phase 4, Task 4.1: the prose runtime gate.

Four surfaces, none of which needs ``llama_cpp`` to be installed except the
two classes that explicitly ``importorskip`` it:

- the PINS (``TestPins``): the runtime version, wheel URL and wheel SHA-256
  in ``scribe_desktop.language_model`` are the ones - byte for byte - that
  ``desktop/requirements-ml-prose.txt`` installs from, and the model file's
  default path is the shipped cache location.
- the INSTALL/IMPORT gate (``TestInstalledRuntimeGate``): where the runtime
  IS installed, its install RECORD must say it came from the pinned prebuilt
  wheel. pip writes PEP 610 ``direct_url.json`` metadata only for a URL
  install, and records the hash it verified there - so an index-resolved copy
  (which for this project means an sdist that pip BUILT FROM SOURCE, exactly
  what D8 forbids) has no ``direct_url.json``, and a copy from a different
  wheel has a different ``url``/hash. This audits a local record, never the
  installed bytes (codex round 22 PR-LOW-039). The gate skips BY NAME when
  the runtime is absent, never fails: agent shells and CI do not install it.
- the real-model SMOKE (``TestRealModelSmoke``): it needs both the pinned
  wheel and the 2.3 GiB GGUF in the source run's DEV models root
  (``%LOCALAPPDATA%\\ClinikoScribe-dev\\models``, installation plan Task 2.6),
  and skips by name when either is absent, in any shell: a missing runtime
  says the prose runtime is not installed, a missing model names that root.
- the LOAD CONTRACT (``TestLoadContract``) and the test double
  (``TestMockLanguageModel``, ``TestAvailability``), driven entirely through
  a fake runtime class and files under ``tmp_path``: offline env first, UNC
  refused, missing file named with the setup command, size before digest,
  digest before the factory, every runtime failure typed and prompt-free.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from conftest import forbid_network_io, real_ml_skip_reason
from scribe_desktop import language_model as lm
from scribe_desktop.benchmark import OFFLINE_ENV, OfflineEnvError, apply_offline_env

DESKTOP = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[2]


# --- the pins ---------------------------------------------------------------------


def _requirement_lines(text: str) -> list[str]:
    """The logical requirement lines of a pip requirements file: comments and
    blanks dropped, ``\\`` continuations joined."""
    logical: list[str] = []
    buffer = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith("\\"):
            buffer += line[:-1].strip() + " "
            continue
        logical.append((buffer + line).strip())
        buffer = ""
    if buffer:
        logical.append(buffer.strip())
    return logical


class TestPins:
    def test_runtime_constants(self) -> None:
        assert lm.LANGUAGE_RUNTIME_NAME == "llama-cpp-python"
        assert lm.LANGUAGE_RUNTIME_VERSION == "0.3.35"
        assert lm.LANGUAGE_RUNTIME_WHEEL_URL.startswith("https://")
        assert lm.LANGUAGE_RUNTIME_WHEEL_URL.endswith(
            "llama_cpp_python-0.3.35-py3-none-win_amd64.whl"
        )
        sha = lm.LANGUAGE_RUNTIME_WHEEL_SHA256
        assert len(sha) == 64 and int(sha, 16) >= 0

    def test_requirements_file_is_exactly_the_pin(self) -> None:
        path = DESKTOP / "requirements-ml-prose.txt"
        assert lm.LANGUAGE_RUNTIME_REQUIREMENTS == "desktop/requirements-ml-prose.txt"
        assert (REPO / lm.LANGUAGE_RUNTIME_REQUIREMENTS) == path
        lines = _requirement_lines(path.read_text(encoding="utf-8"))
        assert lines == [
            f"llama-cpp-python @ {lm.LANGUAGE_RUNTIME_WHEEL_URL} "
            f"--hash=sha256:{lm.LANGUAGE_RUNTIME_WHEEL_SHA256}"
        ], "one hashed wheel, no second requirement that could arrive unpinned"

    @pytest.mark.real_models_root  # the shipped location, through the resolver (Task H.6)
    def test_default_model_path_under_the_models_root(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert lm.default_language_model_path() == (
            tmp_path
            / "ClinikoScribe"
            / "models"
            / "language-model"
            / "Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
        )


# --- the installed runtime (skipped by name where it is absent) -------------------


class TestInstalledRuntimeGate:
    """D8's check on the INSTALL RECORD (codex round 22 PR-LOW-039): the
    hashed ``--require-hashes`` install verifies the downloaded ARCHIVE; this
    gate reads the PEP 610 ``direct_url.json`` pip wrote and requires the
    pinned wheel URL and hash — so an install that took another ROUTE (an
    index resolve, an sdist built from source) is refused. It is a local audit
    record, not a measurement of the installed bytes: forged metadata over
    locally built bytes is inside the same-user boundary the threat model does
    not defend. Every test skips by name when ``llama_cpp`` is not
    importable."""

    def test_installed_version_is_the_pinned_one(self) -> None:
        pytest.importorskip("llama_cpp", reason="the prose runtime is not installed")
        assert (
            importlib.metadata.version("llama_cpp_python") == lm.LANGUAGE_RUNTIME_VERSION
        )

    def test_installed_copy_came_from_the_pinned_wheel(self) -> None:
        pytest.importorskip("llama_cpp", reason="the prose runtime is not installed")
        dist = importlib.metadata.distribution("llama_cpp_python")
        raw = dist.read_text("direct_url.json")
        assert raw is not None, (
            "no PEP 610 direct_url.json: this copy was resolved from an index "
            "(for this project, an sdist pip BUILT FROM SOURCE) rather than "
            f"installed from {lm.LANGUAGE_RUNTIME_REQUIREMENTS}"
        )
        info = json.loads(raw)
        assert info.get("url") == lm.LANGUAGE_RUNTIME_WHEEL_URL
        assert "vcs_info" not in info, "a VCS install is not the pinned wheel"
        assert "dir_info" not in info, "a local-directory install is not the pinned wheel"
        archive = info.get("archive_info")
        assert isinstance(archive, dict), archive
        recorded: Any = None
        hashes = archive.get("hashes")
        if isinstance(hashes, dict):
            recorded = hashes.get("sha256")
        if recorded is None:
            legacy = str(archive.get("hash", ""))
            if legacy.startswith("sha256="):
                recorded = legacy.split("=", 1)[1]
        assert recorded == lm.LANGUAGE_RUNTIME_WHEEL_SHA256

    def test_imported_module_reports_the_pinned_version(self) -> None:
        llama_cpp = pytest.importorskip(
            "llama_cpp", reason="the prose runtime is not installed"
        )
        assert llama_cpp.__version__ == "0.3.35"


# The class below is the real-model smoke: the only place in this module the
# actual 2.3 GiB GGUF is loaded. It runs wherever the pinned wheel is
# installed and the dev models root holds the model (Task 2.6), and skips by
# name otherwise.
class TestRealModelSmoke:
    """The real-model smoke: it needs the pinned wheel AND the 2.3 GiB GGUF
    in the source run's dev models root (installation plan Task 2.6 -
    ``real_ml_models``); without either it skips by name - a missing runtime
    as "the prose runtime is not installed", a missing model with the reason
    naming that root."""

    @pytest.mark.usefixtures("real_ml_models")
    def test_pinned_model_loads_and_generates(self) -> None:
        pytest.importorskip("llama_cpp", reason="the prose runtime is not installed")
        # Installation plan Task 2.6: the source run's DEV models root
        # (``real_ml_models`` pins every model path there), never production.
        if not lm.language_model_file_available():
            pytest.skip(real_ml_skip_reason("the pinned language model"))
        apply_offline_env()
        model = lm.LocalLanguageModel()
        text = model.complete(
            system_text="You are a text tool.",
            user_text="Reply with the single word: ready",
            max_tokens=8,
        )
        assert text.strip() != ""


# --- the load contract through a fake runtime -------------------------------------


_MODEL_BYTES = b"gguf bytes standing in for the pinned model " * 16
_UNSET: Any = object()


def _write_model(tmp_path: Path, data: bytes = _MODEL_BYTES) -> tuple[Path, str]:
    path = tmp_path / "model.gguf"
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


class _FakeLlama:
    """Stands in for ``llama_cpp.Llama``: records every chat call and returns
    one fixed completion, so the whole load contract runs without the wheel."""

    def __init__(
        self,
        content: Any = "ready",
        *,
        response: Any = _UNSET,
        raises: Exception | None = None,
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self.tokenize_calls: list[tuple[bool, bool]] = []
        self._content = content
        self._response = response
        self._raises = raises

    def create_chat_completion(
        self, messages: Any, max_tokens: int, temperature: float
    ) -> Any:
        self.calls.append(
            {"messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        )
        if self._raises is not None:
            raise self._raises
        if self._response is not _UNSET:
            return self._response
        return {"choices": [{"message": {"content": self._content}}]}

    def tokenize(self, text: bytes, add_bos: bool = True, special: bool = False) -> list[int]:
        """The runtime's tokenizer surface (PR-MED-046): one token per word
        here, recording the call's flags."""
        self.tokenize_calls.append((add_bos, special))
        return list(range(len(text.decode("utf-8").split())))


class _Buffer:
    """A token buffer with numpy's in-place ``fill``."""

    def __init__(self, values: list[int]) -> None:
        self.values = values

    def fill(self, value: int) -> None:
        self.values = [value] * len(self.values)


class _Ctx:
    def __init__(self) -> None:
        self.cleared = 0

    def kv_cache_clear(self) -> None:
        self.cleared += 1


class _StatefulFakeLlama(_FakeLlama):
    """The runtime's state surface as ``llama_cpp.Llama`` 0.3.35 exposes it:
    ``reset()``, ``_ctx.kv_cache_clear()``, ``input_ids`` / ``scores``."""

    def __init__(self) -> None:
        super().__init__()
        self.reset_calls = 0
        self.reset_raises: Exception | None = None
        self.raises: Exception | None = None
        self._ctx = _Ctx()
        self.input_ids = _Buffer([1, 2, 3])
        self.scores = _Buffer([5, 6])

    @property
    def ctx(self) -> _Ctx:
        return self._ctx

    def reset(self) -> None:
        if self.reset_raises is not None:
            raise self.reset_raises
        self.reset_calls += 1

    def create_chat_completion(
        self, messages: Any, max_tokens: int, temperature: float
    ) -> Any:
        self.input_ids.values = [1, 2, 3]
        if self.raises is not None:
            raise self.raises
        return super().create_chat_completion(messages, max_tokens, temperature)


def _factory(record: list[dict[str, Any]], llama: Any) -> Callable[..., Any]:
    def _make(**kwargs: Any) -> Any:
        record.append(kwargs)
        return llama

    return _make


def _raising_factory(record: list[dict[str, Any]], exc: Exception) -> Callable[..., Any]:
    def _make(**kwargs: Any) -> Any:
        record.append(kwargs)
        raise exc

    return _make


class TestLoadContract:
    @pytest.fixture(autouse=True)
    def _offline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Every test here starts with the kill-switches on; the one that is
        # ABOUT them deletes them again.
        for key, value in OFFLINE_ENV.items():
            monkeypatch.setenv(key, value)

    def test_offline_env_is_required_before_anything_else(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        for key in OFFLINE_ENV:
            monkeypatch.delenv(key, raising=False)
        path, sha = _write_model(tmp_path)
        record: list[dict[str, Any]] = []
        with pytest.raises(OfflineEnvError):
            lm.LocalLanguageModel(
                path,
                expected_sha256=sha,
                expected_size=len(_MODEL_BYTES),
                llama_factory=_factory(record, _FakeLlama()),
            )
        assert record == []

    def test_std_fds_get_a_sink_only_when_they_cannot_be_duplicated(self) -> None:
        """Round 28 SEC-003: a windowed launcher (pythonw, no console) has no
        valid fds 1/2; the runtime's verbose=False path dup()s them and would
        fail the load. The helper gives exactly the failing ones devnull."""
        calls: list[tuple[int, int]] = []

        def failing_dup(fd: int) -> int:
            raise OSError(9, "Bad file descriptor")

        def record_dup2(src: int, dst: int) -> int:
            calls.append((src, dst))
            return dst

        opened = iter([50, 51])
        closed: list[int] = []
        given = lm._give_std_fds_a_sink(
            dup=failing_dup, dup2=record_dup2, open_sink=lambda: next(opened),
            close=closed.append,
        )
        assert given == (1, 2)
        assert calls == [(50, 1), (51, 2)]
        assert closed == [50, 51]  # only the DISTINCT temporaries are closed
        # A console process: both duplicate fine, nothing is touched.
        calls.clear()
        assert lm._give_std_fds_a_sink(dup2=record_dup2) == ()
        assert calls == []

    def test_count_tokens_is_the_runtimes_tokenizer_without_bos(self, tmp_path: Path) -> None:
        """Codex round 30 PR-MED-046: the prompt budget uses the model's own
        token count — `tokenize` with no BOS and special tokens counted; a
        tokenizer failure is a typed error naming the type only."""
        llama = _FakeLlama()
        model = self._loaded(tmp_path, llama)
        assert model.count_tokens("neck pain for three days") == 5
        assert llama.tokenize_calls[-1] == (False, True)

        class _Broken(_FakeLlama):
            def tokenize(self, text: bytes, add_bos: bool = True, special: bool = False) -> Any:
                raise RuntimeError("secret prompt text must not appear")

        broken = self._loaded(tmp_path, _Broken())
        with pytest.raises(lm.LanguageModelError) as exc:
            broken.count_tokens("x")
        assert "RuntimeError" in str(exc.value) and "secret" not in str(exc.value)

    def test_a_sink_that_is_the_target_descriptor_is_kept_open(self) -> None:
        """Codex round 30 PR-MED-045: with the target closed and every lower
        descriptor open, `os.open` returns the target ITSELF — it is the
        sink, so it is neither duplicated onto itself nor closed."""
        calls: list[tuple[int, int]] = []
        closed: list[int] = []

        def failing_dup(fd: int) -> int:
            raise OSError(9, "Bad file descriptor")

        def record_dup2(src: int, dst: int) -> int:
            calls.append((src, dst))
            return dst

        opened = iter([1, 2])  # the lowest free descriptor IS the target
        given = lm._give_std_fds_a_sink(
            dup=failing_dup, dup2=record_dup2, open_sink=lambda: next(opened),
            close=closed.append,
        )
        assert given == (1, 2)
        assert calls == [] and closed == []
        # The mixed shape: fd 1 aliased, fd 2 repaired through a temporary.
        opened = iter([1, 7])
        closed.clear()
        given = lm._give_std_fds_a_sink(
            dup=failing_dup, dup2=record_dup2, open_sink=lambda: next(opened),
            close=closed.append,
        )
        assert given == (1, 2) and calls == [(7, 2)] and closed == [7]

    def test_the_load_gives_the_std_fds_a_sink_before_the_factory(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        order: list[str] = []
        monkeypatch.setattr(lm, "_give_std_fds_a_sink", lambda: order.append("sink") or ())
        path, sha = _write_model(tmp_path)

        def factory(**kwargs: Any) -> Any:
            order.append("factory")
            return _FakeLlama()

        lm.LocalLanguageModel(
            path, expected_sha256=sha, expected_size=len(_MODEL_BYTES), llama_factory=factory
        )
        assert order == ["sink", "factory"]

    def test_a_native_library_override_is_refused_before_the_factory(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Codex round 22 PR-MED-033: `llama_cpp` loads its DLL from
        `LLAMA_CPP_LIB_PATH` when set; the offline contract refuses the
        variable by NAME — its value is never read as a path — before the
        runtime is imported or any factory is called, and `apply_offline_env`
        deletes it so app startup cannot inherit it."""
        from scribe_desktop.benchmark import FORBIDDEN_NATIVE_OVERRIDES, assert_offline_env

        assert "LLAMA_CPP_LIB_PATH" in FORBIDDEN_NATIVE_OVERRIDES
        monkeypatch.setenv("LLAMA_CPP_LIB_PATH", str(tmp_path / "never-touched"))
        with pytest.raises(OfflineEnvError, match="LLAMA_CPP_LIB_PATH"):
            assert_offline_env()
        path, sha = _write_model(tmp_path)
        record: list[dict[str, Any]] = []
        with pytest.raises(OfflineEnvError, match="LLAMA_CPP_LIB_PATH"):
            lm.LocalLanguageModel(
                path,
                expected_sha256=sha,
                expected_size=len(_MODEL_BYTES),
                llama_factory=_factory(record, _FakeLlama()),
            )
        assert record == []
        assert not (tmp_path / "never-touched").exists()
        apply_offline_env()
        assert "LLAMA_CPP_LIB_PATH" not in os.environ
        assert_offline_env()

    def test_unc_path_is_refused_before_the_factory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Installation plan round 29 PR-LOW-033: the presence check runs
        # before the factory, so a regressed UNC guard must fail at the
        # filesystem call, not reach the share.
        forbid_network_io(monkeypatch)
        record: list[dict[str, Any]] = []
        with pytest.raises(lm.LanguageModelError, match="UNC"):
            lm.LocalLanguageModel(
                Path(r"\\server\share\m.gguf"),
                llama_factory=_factory(record, _FakeLlama()),
            )
        assert record == []

    def test_missing_file_names_the_setup_command(self, tmp_path: Path) -> None:
        record: list[dict[str, Any]] = []
        with pytest.raises(lm.LanguageModelError, match="--only language-model") as exc:
            lm.LocalLanguageModel(
                tmp_path / "absent.gguf", llama_factory=_factory(record, _FakeLlama())
            )
        assert "setup-models.py" in str(exc.value)
        assert record == []

    def test_wrong_size_is_refused_before_the_digest_and_the_factory(
        self, tmp_path: Path
    ) -> None:
        path, sha = _write_model(tmp_path)
        record: list[dict[str, Any]] = []
        with pytest.raises(lm.LanguageModelError, match="bytes") as exc:
            lm.LocalLanguageModel(
                path,
                expected_sha256=sha,
                expected_size=len(_MODEL_BYTES) + 1,
                llama_factory=_factory(record, _FakeLlama()),
            )
        assert str(len(_MODEL_BYTES) + 1) in str(exc.value)
        assert record == []

    def test_wrong_digest_names_both_and_never_loads(self, tmp_path: Path) -> None:
        path, sha = _write_model(tmp_path)
        record: list[dict[str, Any]] = []
        with pytest.raises(lm.LanguageModelError, match="not the pinned model") as exc:
            lm.LocalLanguageModel(
                path,
                expected_sha256="0" * 64,
                expected_size=len(_MODEL_BYTES),
                llama_factory=_factory(record, _FakeLlama()),
            )
        assert "0" * 64 in str(exc.value) and sha in str(exc.value)
        assert record == []

    def test_expected_size_none_skips_the_size_check(self, tmp_path: Path) -> None:
        # A file of the WRONG length reaches the digest check, which refuses it.
        path, sha = _write_model(tmp_path)
        record: list[dict[str, Any]] = []
        with pytest.raises(lm.LanguageModelError, match="not the pinned model"):
            lm.LocalLanguageModel(
                path,
                expected_sha256="1" * 64,
                expected_size=None,
                llama_factory=_factory(record, _FakeLlama()),
            )
        assert sha != "1" * 64 and record == []

    def test_a_factory_that_raises_is_typed_and_names_the_step(self, tmp_path: Path) -> None:
        path, sha = _write_model(tmp_path)
        record: list[dict[str, Any]] = []
        with pytest.raises(lm.LanguageModelError, match="model load") as exc:
            lm.LocalLanguageModel(
                path,
                expected_sha256=sha,
                expected_size=len(_MODEL_BYTES),
                llama_factory=_raising_factory(record, RuntimeError("runtime exploded")),
            )
        assert "RuntimeError" in str(exc.value)
        assert len(record) == 1

    def test_good_load_passes_the_pinned_parameters_and_smokes_once(
        self, tmp_path: Path
    ) -> None:
        path, sha = _write_model(tmp_path)
        record: list[dict[str, Any]] = []
        llama = _FakeLlama()
        model = lm.LocalLanguageModel(
            path,
            expected_sha256=sha,
            expected_size=len(_MODEL_BYTES),
            llama_factory=_factory(record, llama),
        )
        assert record == [
            {
                "model_path": str(path),
                "n_ctx": 4096,
                "n_threads": None,
                "verbose": False,
            }
        ]
        assert len(llama.calls) == 1, "the construction smoke generates exactly once"
        call = llama.calls[0]
        assert call["max_tokens"] == 8 and call["temperature"] == 0.0
        assert [m["role"] for m in call["messages"]] == ["system", "user"]
        assert model.model_id == lm.LANGUAGE_MODEL_ID
        assert model.model_path == path

    def test_smoke_false_generates_nothing_at_construction(self, tmp_path: Path) -> None:
        path, sha = _write_model(tmp_path)
        llama = _FakeLlama()
        lm.LocalLanguageModel(
            path,
            expected_sha256=sha,
            expected_size=len(_MODEL_BYTES),
            smoke=False,
            llama_factory=_factory([], llama),
        )
        assert llama.calls == []

    def test_empty_smoke_completion_fails_the_load(self, tmp_path: Path) -> None:
        path, sha = _write_model(tmp_path)
        with pytest.raises(lm.LanguageModelError, match="smoke"):
            lm.LocalLanguageModel(
                path,
                expected_sha256=sha,
                expected_size=len(_MODEL_BYTES),
                llama_factory=_factory([], _FakeLlama("   ")),
            )

    def _loaded(self, tmp_path: Path, llama: Any) -> lm.LocalLanguageModel:
        path, sha = _write_model(tmp_path)
        return lm.LocalLanguageModel(
            path,
            expected_sha256=sha,
            expected_size=len(_MODEL_BYTES),
            smoke=False,
            llama_factory=_factory([], llama),
        )

    def test_every_completion_clears_the_runtimes_inference_state(
        self, tmp_path: Path
    ) -> None:
        """Codex round 22 PR-MED-034: the resident runtime keeps the last
        prompt's and completion's tokens in its token buffers and KV cache;
        after EVERY `complete` — success or failure — the runtime's `reset()`,
        its `_ctx.kv_cache_clear()` and the two token buffers are cleared,
        weights untouched (no reload); a hook that raises is typed."""
        llama = _StatefulFakeLlama()
        model = self._loaded(tmp_path, llama)
        model.complete(system_text="tool", user_text="line", max_tokens=4)
        assert llama.reset_calls == 1 and llama.ctx.cleared == 1
        assert llama.input_ids.values == [0, 0, 0] and llama.scores.values == [0, 0]
        llama.input_ids.values = [7, 8, 9]
        llama.raises = RuntimeError("mid-generation")
        with pytest.raises(lm.LanguageModelError, match="generation failed"):
            model.complete(system_text="tool", user_text="line", max_tokens=4)
        assert llama.reset_calls == 2 and llama.ctx.cleared == 2
        assert llama.input_ids.values == [0, 0, 0]
        llama.raises = None
        llama.reset_raises = RuntimeError("clear exploded")
        with pytest.raises(lm.LanguageModelError, match="state could not be cleared"):
            model.complete(system_text="tool", user_text="line", max_tokens=4)

    def test_a_runtime_without_the_state_hooks_is_left_alone(self, tmp_path: Path) -> None:
        model = self._loaded(tmp_path, _FakeLlama())
        assert model.complete(system_text="tool", user_text="line", max_tokens=4) == "ready"

    def test_a_generation_failure_never_carries_the_prompt(self, tmp_path: Path) -> None:
        failure = ValueError("secret prompt")
        model = self._loaded(tmp_path, _FakeLlama(raises=failure))
        with pytest.raises(lm.LanguageModelError) as exc:
            model.complete(
                system_text="you are a tool", user_text="secret prompt", max_tokens=4
            )
        assert "ValueError" in str(exc.value)
        assert "secret prompt" not in str(exc.value)
        assert exc.value.__cause__ is failure

    def test_a_malformed_response_is_typed(self, tmp_path: Path) -> None:
        model = self._loaded(tmp_path, _FakeLlama(response={}))
        with pytest.raises(lm.LanguageModelError, match="no completion"):
            model.complete(system_text="s", user_text="u", max_tokens=4)

    def test_a_non_text_completion_is_typed(self, tmp_path: Path) -> None:
        model = self._loaded(tmp_path, _FakeLlama(123))
        with pytest.raises(lm.LanguageModelError, match="non-text"):
            model.complete(system_text="s", user_text="u", max_tokens=4)


# --- the test double ---------------------------------------------------------------


def _prompt(*lines: str, markers: bool = True) -> str:
    body = "\n".join(f"- {line}" for line in lines)
    if not markers:
        return f"ignored preamble\n{body}\nignored trailer"
    return (
        "ignored preamble\n"
        f"{lm.PROMPT_LINES_HEADER}\n"
        f"{body}\n"
        "\n"
        f"{lm.PROMPT_LINES_END}\n"
        "ignored trailer"
    )


class TestMockLanguageModel:
    def test_prompt_lines_reads_only_between_the_markers(self) -> None:
        text = _prompt("pain in the left knee", "worse on stairs")
        assert lm.prompt_lines(text) == ("pain in the left knee", "worse on stairs")
        assert lm.prompt_lines(_prompt("a", markers=False)) == ()
        assert lm.prompt_lines("no markers at all") == ()

    def test_echo_is_one_sentence_per_line_without_doubling_a_full_stop(self) -> None:
        text = _prompt("pain in the left knee", "worse on stairs.")
        assert lm.echo_prompt_lines("sys", text) == (
            "pain in the left knee. worse on stairs."
        )

    def test_default_mock_echoes_the_confirmed_lines(self) -> None:
        text = _prompt("pain in the left knee")
        model = lm.MockLanguageModel()
        assert model.complete(system_text="s", user_text=text, max_tokens=64) == (
            "pain in the left knee."
        )
        assert model.model_id == "mock-language-model"

    def test_calls_are_recorded(self) -> None:
        model = lm.MockLanguageModel()
        model.complete(system_text="sys", user_text=_prompt("a line"), max_tokens=32)
        assert model.calls == [("sys", _prompt("a line"), 32)]

    def test_a_sequence_is_consumed_in_order_then_exhausted(self) -> None:
        model = lm.MockLanguageModel(responses=["one", "two"])
        text = _prompt("a line")
        assert model.complete(system_text="s", user_text=text, max_tokens=8) == "one"
        assert model.complete(system_text="s", user_text=text, max_tokens=8) == "two"
        with pytest.raises(lm.LanguageModelError, match="exhausted"):
            model.complete(system_text="s", user_text=text, max_tokens=8)

    def test_a_mapping_targets_by_first_confirmed_line_and_echoes_otherwise(self) -> None:
        model = lm.MockLanguageModel(responses={"pain in the knee": "scripted prose"})
        named = _prompt("pain in the knee", "worse on stairs")
        other = _prompt("no swelling")
        assert model.complete(system_text="s", user_text=named, max_tokens=8) == (
            "scripted prose"
        )
        assert model.complete(system_text="s", user_text=other, max_tokens=8) == (
            "no swelling."
        )

    def test_responder_wins_over_responses(self) -> None:
        model = lm.MockLanguageModel(
            responder=lambda system_text, user_text: "from the responder",
            responses=["never used"],
        )
        text = _prompt("a line")
        assert model.complete(system_text="s", user_text=text, max_tokens=8) == (
            "from the responder"
        )

    def test_fail_with_raises_that_exception(self) -> None:
        failure = RuntimeError("the runtime died mid-stage")
        model = lm.MockLanguageModel(fail_with=failure)
        with pytest.raises(RuntimeError) as exc:
            model.complete(system_text="s", user_text=_prompt("a line"), max_tokens=8)
        assert exc.value is failure
        assert model.calls, "the call is recorded before the failure"


class TestAvailability:
    def test_file_probe_is_presence_only(self, tmp_path: Path) -> None:
        assert lm.language_model_file_available(tmp_path / "absent.gguf") is False
        present = tmp_path / "present.gguf"
        present.write_bytes(b"not really a model")
        assert lm.language_model_file_available(present) is True

    def test_unc_path_reports_unavailable_without_touching_it(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Installation plan round 29 PR-LOW-033: "without touching it" is
        # enforced through the probe's file access — each `Path` method in
        # `NETWORK_IO_METHODS` raises on the network path (round 30).
        forbid_network_io(monkeypatch)
        assert lm.language_model_file_available(Path(r"\\server\share\m.gguf")) is False

    def test_default_path_probe_follows_the_models_root(self) -> None:
        # The conftest's empty models root (Task H.6); the LOCALAPPDATA
        # mapping is the exempt tests' business.
        assert lm.language_model_file_available() is False
        pinned = lm.default_language_model_path()
        pinned.parent.mkdir(parents=True)
        pinned.write_bytes(b"not really a model")
        assert lm.language_model_file_available() is True

    @pytest.mark.real_models_root  # the resolver's unset-LOCALAPPDATA contract (Task H.6)
    def test_localappdata_unset_reports_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        assert lm.language_model_file_available() is False
