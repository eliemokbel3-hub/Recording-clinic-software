"""The local language model behind the two prose styles (note-learning-and-styles
plan Phase 4, Task 4.1; D6, D8; C1).

ONE pin, defined here and imported by ``scripts/setup-models.py`` (never a
second literal that can drift — the ``speaker_embedding`` pattern): the model
file's name, cache subdirectory, byte size and SHA-256, and the runtime's
version, wheel URL and wheel SHA-256 (Task 4.0, practitioner-decided
2026-09-20 on the Task P.0 preflight). The model is ``Qwen3-4B-Instruct-2507``
at Q4_K_M — the NON-thinking instruct release (no ``<think>`` block to strip),
Apache-2.0 upstream, quantised and published as GGUF by ``unsloth`` (a third
party; the bytes are pinned by SHA-256 taken from the file's LFS record on
2026-09-20, never trusted from the ``resolve/main`` URL).

Offline contract (D8), stated exactly:
- ``LocalLanguageModel`` loads from a LOCAL PATH ONLY — never a Hugging Face
  ``from_pretrained`` — after ``assert_offline_env`` (the app-wide invariant,
  kept even though ``llama-cpp-python`` reads none of the kill-switch
  variables), a UNC refusal, a size check (a fast refusal before the 2.3 GiB
  digest), the streamed SHA-256 against the pin, and a short smoke generation
  at construction so a broken runtime or file fails HERE, never on the first
  note. The ENFORCING offline control for this runtime is the no-sockets
  integration test extended over a prose generation (Task 4.4), not
  ``assert_offline_env``; the runtime itself is installed only from the
  hashed prebuilt wheel (``desktop/requirements-ml-prose.txt``, verified by
  ``tests/test_language_model_runtime.py``).
- The runtime is imported lazily inside ``LocalLanguageModel`` (the module
  imports without it, like ``speech.py``); every failure from the import
  onward is a ``LanguageModelError`` naming the step.
- Nothing here logs. A prompt and a completion are clinical text (C9): the
  model object holds them only for the duration of one ``complete`` call, and
  ``MockLanguageModel`` (test-only) records its calls in memory for the test
  that made them.

``LanguageModel`` is the protocol the prose stage (Task 4.3) talks to:
``complete(system_text=, user_text=, max_tokens=)`` returns the completion
text. ``MockLanguageModel`` is the deterministic, scriptable test double —
by default it ECHOES the confirmed lines it finds in the prompt (between
``PROMPT_LINES_HEADER`` and ``PROMPT_LINES_END``, the markers the prose
stage's prompt builder uses) as one sentence per line, so a faithful
rendering passes Check 5; scripted responses model the adversarial cases.
"""

from __future__ import annotations

import importlib.util
import os
import threading
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Final, Protocol

from scribe_desktop import install_layout
from scribe_desktop.benchmark import assert_offline_env, default_models_root
from scribe_desktop.speaker_embedding import is_unc_path, sha256_of_file

# --- the pinned model (single source; scripts/setup-models.py imports these) ---

LANGUAGE_MODEL_NAME: Final = "Qwen3-4B-Instruct-2507-Q4_K_M"
LANGUAGE_MODEL_FILENAME: Final = f"{LANGUAGE_MODEL_NAME}.gguf"
LANGUAGE_MODEL_SUBDIR: Final = "language-model"
LANGUAGE_MODEL_REPO: Final = "unsloth/Qwen3-4B-Instruct-2507-GGUF"
# The pin: size and SHA-256 from the file's Hugging Face LFS record, taken
# 2026-09-20 (Task 4.0). The digest is what pins the bytes; ``setup-models``
# verifies a download against BOTH before promoting it, and the runtime
# verifies the promoted file again at every load.
LANGUAGE_MODEL_SIZE_BYTES: Final = 2_497_281_120
LANGUAGE_MODEL_SHA256: Final = (
    "3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597"
)
# The identity a rendering was produced under (display and reporting only).
LANGUAGE_MODEL_ID: Final = f"{LANGUAGE_MODEL_REPO}:{LANGUAGE_MODEL_FILENAME}"

# --- the pinned runtime (Task 4.0; installed ONLY from this wheel) -----------

LANGUAGE_RUNTIME_NAME: Final = "llama-cpp-python"
LANGUAGE_RUNTIME_VERSION: Final = "0.3.35"
LANGUAGE_RUNTIME_WHEEL_INDEX: Final = "https://abetlen.github.io/llama-cpp-python/whl/cpu"
LANGUAGE_RUNTIME_WHEEL_URL: Final = (
    "https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.35/"
    "llama_cpp_python-0.3.35-py3-none-win_amd64.whl"
)
LANGUAGE_RUNTIME_WHEEL_SHA256: Final = (
    "31590ea000d5aff6f05f1e428048e72318a83709288159a5bd4dabec530080bb"
)
# The hashed requirements file the runtime is installed from (relative to
# the repository root); ``tests/test_language_model_runtime.py`` pins its
# content to the constants above.
LANGUAGE_RUNTIME_REQUIREMENTS: Final = "desktop/requirements-ml-prose.txt"

# --- generation parameters ------------------------------------------------------

# Context window for one section's prompt: the fixed instruction, up to 30
# exemplar sentences (own voice) and one section's confirmed lines fit in a
# fraction of this; the bound keeps the KV cache small on a CPU-only host.
LANGUAGE_MODEL_CONTEXT_TOKENS: Final = 4096
# The smoke generation at construction: a short fixed exchange whose only
# check is a non-empty completion.
LANGUAGE_MODEL_SMOKE_MAX_TOKENS: Final = 8
_SMOKE_SYSTEM_TEXT: Final = "You are a text tool. Follow the instruction exactly."
_SMOKE_USER_TEXT: Final = "Reply with the single word: ready"

# The prompt markers the prose stage (Task 4.3) wraps the confirmed lines in,
# defined HERE so the mock's default echo and the real prompt builder share
# one definition (the mock never imports the prose stage).
PROMPT_LINES_HEADER: Final = "CONFIRMED LINES (one fact per line; rephrase only, add nothing):"
PROMPT_LINES_END: Final = "END OF CONFIRMED LINES"


class LanguageModelError(RuntimeError):
    """The language model could not be loaded, verified or run. The message
    names the step and never carries prompt or completion text."""


class LanguageModel(Protocol):
    """What the prose stage needs from a model: an identity for reporting,
    one deterministic completion call (``max_tokens`` bounds the output) and
    the model's OWN token count of a text (codex round 30 PR-MED-046: the
    prose stage budgets every prompt against the context window with the
    runtime's tokenizer, never a character heuristic)."""

    @property
    def model_id(self) -> str: ...

    def complete(self, *, system_text: str, user_text: str, max_tokens: int) -> str: ...

    def count_tokens(self, text: str) -> int: ...


# --- paths and availability (stat-only; the load contract verifies) -------------


def default_language_model_path() -> Path:
    return default_models_root() / LANGUAGE_MODEL_SUBDIR / LANGUAGE_MODEL_FILENAME


def language_model_file_available(model_path: Path | None = None) -> bool:
    """True when the pinned model FILE exists — a STAT-only probe (mirrors
    ``speaker_model_available``): a UNC-redirected ``LOCALAPPDATA`` must
    cause zero SMB I/O, so UNC paths are refused BEFORE any filesystem touch
    and report unavailable. Presence only — the digest is verified by
    ``LocalLanguageModel`` at load, not here."""
    try:
        path = model_path if model_path is not None else default_language_model_path()
        if is_unc_path(path):
            return False
        return path.is_file()
    except (RuntimeError, OSError, ValueError):  # ValueError: a NUL in LOCALAPPDATA
        return False


def language_runtime_importable() -> bool:
    """Whether ``llama_cpp`` is installed — a ``find_spec`` probe that
    imports nothing (the import itself, with its DLL load, happens only
    inside ``LocalLanguageModel``)."""
    try:
        return importlib.util.find_spec("llama_cpp") is not None
    except (ImportError, ValueError):
        return False


def _import_llama() -> Callable[..., Any]:
    try:
        from llama_cpp import Llama
    except Exception as exc:  # ImportError, or a DLL failure surfacing as OSError
        # Installation plan Task 1.7: a packaged build bundles the runtime, so
        # its remedy is a reinstall, never the source checkout's wheel step.
        remedy = (
            install_layout.FROZEN_REMEDY
            if install_layout.is_frozen()
            else (
                f"install it from the pinned wheel ({LANGUAGE_RUNTIME_REQUIREMENTS}, the "
                "two-step command in AGENTS.md Local Run Steps, step 2)"
            )
        )
        raise LanguageModelError(
            f"the prose runtime ({LANGUAGE_RUNTIME_NAME}) is not importable ({exc}); {remedy}"
        ) from exc
    factory: Callable[..., Any] = Llama
    return factory


# --- the real model -----------------------------------------------------------------


def _open_devnull_sink() -> int:
    return os.open(os.devnull, os.O_RDWR)


def _give_std_fds_a_sink(
    *,
    dup: Callable[[int], int] = os.dup,
    dup2: Callable[[int, int], int] = os.dup2,
    open_sink: Callable[[], int] = _open_devnull_sink,
    close: Callable[[int], None] = os.close,
) -> tuple[int, ...]:
    """Phase H round 28 SEC-003: the runtime's ``verbose=False`` path
    silences llama.cpp's native log by ``os.dup``-ing file descriptors 1 and
    2 and pointing them at ``devnull`` for the load. A WINDOWED process — the
    shipped ``scribe-app.exe`` is a ``pythonw`` launcher with no console — has
    no valid descriptor there, ``dup`` raises ``OSError`` and the load would
    fail (remembered for the process: both prose styles dead). So before the
    runtime is built, any of the two descriptors that cannot be duplicated is
    given ``devnull`` as its sink; a console process is untouched. Returns
    the descriptors that were given a sink (for the test pin).

    Codex round 30 PR-MED-045: ``open_sink`` returns the LOWEST free
    descriptor, which — when the target itself is closed and every lower one
    is open — is the target: then the opened descriptor IS the sink and is
    kept; only a DISTINCT temporary is duplicated onto the target and closed.
    Closing unconditionally re-closed the descriptor just repaired."""
    given: list[int] = []
    for fd in (1, 2):
        try:
            close(dup(fd))
            continue
        except OSError:
            pass
        sink = open_sink()
        if sink != fd:
            try:
                dup2(sink, fd)
            finally:
                close(sink)
        given.append(fd)
    return tuple(given)


class LocalLanguageModel:
    """The pinned GGUF model over ``llama-cpp-python``, loaded from the local
    path only under the contract in the module docstring. Construction runs
    on the caller's thread and takes seconds (the digest of a 2.3 GiB file,
    then the load) — the prose stage constructs it on its worker thread, never
    the GUI thread (the D3 pattern). ``complete`` is serialised by a lock: the
    runtime object is not thread-safe, and the Note tab runs one rendering
    job at a time anyway.

    ``llama_factory`` is the test seam for the runtime class (a fake stands in
    for ``llama_cpp.Llama`` so the load contract is testable without the
    wheel); ``smoke=False`` skips the construction-time generation."""

    def __init__(
        self,
        model_path: Path | None = None,
        *,
        expected_sha256: str = LANGUAGE_MODEL_SHA256,
        expected_size: int | None = LANGUAGE_MODEL_SIZE_BYTES,
        context_tokens: int = LANGUAGE_MODEL_CONTEXT_TOKENS,
        threads: int | None = None,
        smoke: bool = True,
        llama_factory: Callable[..., Any] | None = None,
    ) -> None:
        assert_offline_env()
        path = model_path if model_path is not None else default_language_model_path()
        if is_unc_path(path):
            raise LanguageModelError(
                f"language model path must be a local path, not UNC: {path}"
            )
        if not path.is_file():
            raise LanguageModelError(
                f"language model not found at {path} - "
                f"{install_layout.model_remedy('language-model')}"
            )
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise LanguageModelError(f"language model at {path} is unreadable: {exc}") from exc
        if expected_size is not None and size != expected_size:
            raise LanguageModelError(
                f"language model at {path} is {size} bytes, not the pinned "
                f"{expected_size} - {install_layout.model_remedy('language-model')}"
            )
        try:
            actual = sha256_of_file(path)
        except OSError as exc:
            raise LanguageModelError(f"language model at {path} is unreadable: {exc}") from exc
        if actual != expected_sha256:
            raise LanguageModelError(
                f"language model at {path} is not the pinned model: expected SHA-256 "
                f"{expected_sha256}, got {actual} - "
                f"{install_layout.model_remedy('language-model')}"
            )
        factory = llama_factory if llama_factory is not None else _import_llama()
        _give_std_fds_a_sink()  # SEC-003: before the runtime dup()s fds 1 and 2
        try:
            self._llama = factory(
                model_path=str(path),
                n_ctx=context_tokens,
                n_threads=threads,
                verbose=False,
            )
        except Exception as exc:
            raise LanguageModelError(
                f"failed to load the language model at {path} (model load): "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        self._path = path
        self._lock = threading.Lock()
        if smoke:
            text = self.complete(
                system_text=_SMOKE_SYSTEM_TEXT,
                user_text=_SMOKE_USER_TEXT,
                max_tokens=LANGUAGE_MODEL_SMOKE_MAX_TOKENS,
            )
            if not text.strip():
                raise LanguageModelError(
                    f"the language model at {path} loaded but its smoke generation "
                    "returned no text"
                )

    @property
    def model_id(self) -> str:
        return LANGUAGE_MODEL_ID

    @property
    def model_path(self) -> Path:
        return self._path

    def complete(self, *, system_text: str, user_text: str, max_tokens: int) -> str:
        """One greedy (temperature 0) chat completion, bounded by
        ``max_tokens``. A runtime failure is a ``LanguageModelError`` naming
        the exception type only — never the prompt."""
        messages = [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ]
        with self._lock:
            try:
                response = self._llama.create_chat_completion(
                    messages=messages, max_tokens=max_tokens, temperature=0.0
                )
            except Exception as exc:
                raise LanguageModelError(
                    f"language model generation failed ({type(exc).__name__})"
                ) from exc
            finally:
                self._clear_inference_state()
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LanguageModelError(
                "language model generation returned no completion"
            ) from exc
        if not isinstance(content, str):
            raise LanguageModelError("language model generation returned a non-text completion")
        return content

    def count_tokens(self, text: str) -> int:
        """The runtime's own token count of ``text`` (``Llama.tokenize``, no
        BOS, special tokens counted) — the prose stage's prompt budget (codex
        round 30 PR-MED-046). A tokenizer failure is a ``LanguageModelError``
        naming the exception type only."""
        with self._lock:
            try:
                return len(self._llama.tokenize(text.encode("utf-8"), add_bos=False, special=True))
            except Exception as exc:
                raise LanguageModelError(
                    f"language model tokenisation failed ({type(exc).__name__})"
                ) from exc

    def _clear_inference_state(self) -> None:
        """Drop what one completion left in the RESIDENT runtime (codex round
        22 PR-MED-034): the runtime's own ``reset()`` (its token counter, and
        the recurrent-model memory), the KV cache (``_ctx.kv_cache_clear``,
        the call the runtime itself makes before a fresh evaluation) and the
        two token buffers ``input_ids`` / ``scores`` zeroed in place — so the
        prompt's and the completion's tokens live for ONE call, never until
        the next. Weights are untouched (no reload). Each hook is looked up
        by name and skipped when the runtime lacks it, so a fake runtime
        needs none of them; a hook that RAISES is a ``LanguageModelError``
        (the section then counts as a model error). Residue, named: the
        zeroing is best-effort process memory like every other plaintext
        buffer here, and the runtime's internal scratch (its batch and
        logits arrays) is not enumerated."""
        llama = self._llama
        try:
            reset = getattr(llama, "reset", None)
            if callable(reset):
                reset()
            clear_cache = getattr(getattr(llama, "_ctx", None), "kv_cache_clear", None)
            if callable(clear_cache):
                clear_cache()
            for name in ("input_ids", "scores"):
                fill = getattr(getattr(llama, name, None), "fill", None)
                if callable(fill):
                    fill(0)
        except Exception as exc:
            raise LanguageModelError(
                f"language model state could not be cleared ({type(exc).__name__})"
            ) from exc


# --- the test double ------------------------------------------------------------------


def prompt_lines(user_text: str) -> tuple[str, ...]:
    """The confirmed lines a prompt carries: every non-blank line between
    ``PROMPT_LINES_HEADER`` and ``PROMPT_LINES_END`` with a leading ``- ``
    bullet stripped; empty when the markers are absent. Shared by the mock's
    default echo and the tests that read a prompt back."""
    lines: list[str] = []
    inside = False
    for raw in user_text.splitlines():
        line = raw.strip()
        if line == PROMPT_LINES_HEADER:
            inside = True
            continue
        if line == PROMPT_LINES_END:
            break
        if inside and line:
            lines.append(line[2:] if line.startswith("- ") else line)
    return tuple(lines)


def echo_prompt_lines(system_text: str, user_text: str) -> str:
    """The default mock behaviour: one sentence per confirmed line, each
    line's words unchanged with a full stop appended — a faithful rendering
    by construction (every input token present, nothing added)."""
    return " ".join(f"{line.rstrip('.')}." for line in prompt_lines(user_text))


class MockLanguageModel:
    """Deterministic, ML-free ``LanguageModel`` for tests (never shipped as a
    provider). Behaviour, in precedence order:

    - ``fail_with``: every ``complete`` raises that exception (a runtime
      failure mid-stage);
    - ``responder``: ``responder(system_text, user_text)`` is the completion;
    - ``responses``: a SEQUENCE is consumed one completion per call in order
      (a call past the end raises ``LanguageModelError``); a MAPPING is keyed
      by the first confirmed line of the prompt (``prompt_lines(...)[0]``) so
      a scripted section can be targeted by content, falling back to the echo
      for sections it does not name;
    - otherwise ``echo_prompt_lines`` — the faithful rendering.

    Every call is recorded in ``calls`` as ``(system_text, user_text,
    max_tokens)`` — prompt text held in memory by a TEST double for the test
    that made it; nothing here logs."""

    model_id: str = "mock-language-model"

    def __init__(
        self,
        *,
        responder: Callable[[str, str], str] | None = None,
        responses: Sequence[str] | Mapping[str, str] | None = None,
        fail_with: Exception | None = None,
    ) -> None:
        self._responder = responder
        self._queue: list[str] | None = None
        self._by_first_line: Mapping[str, str] | None = None
        if isinstance(responses, Mapping):
            self._by_first_line = dict(responses)
        elif responses is not None:
            self._queue = list(responses)
        self._fail_with = fail_with
        self.calls: list[tuple[str, str, int]] = []

    def complete(self, *, system_text: str, user_text: str, max_tokens: int) -> str:
        self.calls.append((system_text, user_text, max_tokens))
        if self._fail_with is not None:
            raise self._fail_with
        if self._responder is not None:
            return self._responder(system_text, user_text)
        if self._queue is not None:
            if not self._queue:
                raise LanguageModelError("mock language model: scripted responses exhausted")
            return self._queue.pop(0)
        if self._by_first_line is not None:
            lines = prompt_lines(user_text)
            if lines and lines[0] in self._by_first_line:
                return self._by_first_line[lines[0]]
        return echo_prompt_lines(system_text, user_text)

    def count_tokens(self, text: str) -> int:
        """Whitespace-separated words — a deterministic stand-in for the
        runtime's tokenizer, so the prompt budget is testable exactly."""
        return len(text.split())


__all__ = [
    "LANGUAGE_MODEL_CONTEXT_TOKENS",
    "LANGUAGE_MODEL_FILENAME",
    "LANGUAGE_MODEL_ID",
    "LANGUAGE_MODEL_NAME",
    "LANGUAGE_MODEL_REPO",
    "LANGUAGE_MODEL_SHA256",
    "LANGUAGE_MODEL_SIZE_BYTES",
    "LANGUAGE_MODEL_SMOKE_MAX_TOKENS",
    "LANGUAGE_MODEL_SUBDIR",
    "LANGUAGE_RUNTIME_NAME",
    "LANGUAGE_RUNTIME_REQUIREMENTS",
    "LANGUAGE_RUNTIME_VERSION",
    "LANGUAGE_RUNTIME_WHEEL_INDEX",
    "LANGUAGE_RUNTIME_WHEEL_SHA256",
    "LANGUAGE_RUNTIME_WHEEL_URL",
    "PROMPT_LINES_END",
    "PROMPT_LINES_HEADER",
    "LanguageModel",
    "LanguageModelError",
    "LocalLanguageModel",
    "MockLanguageModel",
    "default_language_model_path",
    "echo_prompt_lines",
    "language_model_file_available",
    "language_runtime_importable",
    "prompt_lines",
]
