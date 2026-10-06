"""Installation plan Phase 2 — frozen-runtime support.

- Task 2.1: the packaged build's benchmark worker (``scribe-app.exe
  --benchmark-worker``), its spawn shape and its exact-argv dispatch;
- Task 2.2: the native host's stdio seam (``native_host.binary_stdio``) in
  both shapes, and a None stderr tolerated (Task 0.2: Chrome gives none);
- Task 2.3: the Chrome link read in Chrome's order (D9) — the winning entry,
  the others, the frozen per-user override warning, the host's log lines,
  and the real layer's order over a FAKE ``winreg``;
- Task 2.6: the real-ML legs' models root is the source run's DEV root;
- Task 2.7: a packaged build outside its install folder never starts;
- Task H.6: every other test's models root is the conftest's empty folder,
  and the resolver's own tests opt out (``real_models_root``).

Host state is never read (C6): ``sys.frozen`` (``install_layout.is_frozen``),
the packaged executable's path (``install_layout.executable``),
``LOCALAPPDATA``, the registry and every stream are injected per test. The
one host value used as it is, ``sys.executable``, is read only as the
benchmark spawn's argv[0] — compared as a string, never run (every spawn is
faked)."""

from __future__ import annotations

import ast
import io
import json
import logging
import os
import sys
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from conftest import (
    REAL_MODELS_ROOT,
    forbid_network_io,
    on_real_ml_root,
    real_ml_models_root,
    real_ml_skip_reason,
    use_channel,
    use_frozen,
)
from scribe_desktop import benchmark, exclusions, install_layout, logging_setup, status
from scribe_desktop import native_host as nh
from scribe_desktop.exclusions import HostEntry

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TESTS = Path(__file__).resolve().parent
windows_only = pytest.mark.skipif(sys.platform != "win32", reason="junctions are Windows-only")


class _Proceeded(Exception):
    """Raised by a patched step to prove an entry point went past a check."""


def _proceeds(*_args: Any, **_kwargs: Any) -> Any:
    raise _Proceeded()


def _real(path: Path) -> Path:
    return Path(os.path.realpath(path))


def _frozen_at(monkeypatch: pytest.MonkeyPatch, executable: Path) -> None:
    use_frozen(monkeypatch, True)
    monkeypatch.setattr(install_layout, "executable", lambda: str(executable))


# --- Task 2.1: the benchmark worker ---------------------------------------------------


_TAIL = ["--single", "medium", "--models-root", r"C:\m", "--audio", r"C:\t\s.wav"]


def _worker(root: Path = Path(r"C:\m")) -> list[str]:
    return benchmark.worker_argv("medium", root, Path(r"C:\t\s.wav"), 53.2)


class TestWorkerArgv:
    def test_a_source_run_spawns_the_module(self) -> None:
        assert install_layout.is_frozen() is False  # the conftest pin
        assert _worker() == [
            sys.executable,
            "-m",
            "scribe_desktop.benchmark",
            *_TAIL,
            "--audio-seconds",
            "53.2",
        ]

    def test_a_packaged_build_spawns_its_own_exe_with_the_flag(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        use_frozen(monkeypatch, True)
        assert _worker() == [
            sys.executable,
            "--benchmark-worker",
            *_TAIL,
            "--audio-seconds",
            "53.2",
        ]
        assert benchmark.WORKER_FLAG == "--benchmark-worker"

    @pytest.mark.parametrize("frozen", [False, True])
    def test_run_all_spawns_the_worker_argv_with_the_worker_env(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, frozen: bool
    ) -> None:
        use_frozen(monkeypatch, frozen)
        spawned: list[tuple[list[str], dict[str, str]]] = []
        result = benchmark.BenchmarkResult("medium", 10.0, 1.0, 2.0, 0.2, 1, 5)

        def fake_run(argv: list[str], *, env: dict[str, str], **kwargs: Any) -> Any:
            spawned.append((argv, env))
            return SimpleNamespace(returncode=0, stdout=json.dumps(asdict(result)), stderr="")

        monkeypatch.setattr(benchmark, "list_whisper_candidates", lambda root: ["medium"])
        monkeypatch.setattr(benchmark, "generate_speech_sample", lambda target: 10.0)
        monkeypatch.setattr(benchmark.subprocess, "run", fake_run)
        assert benchmark.run_all(tmp_path) == [result]
        [(argv, env)] = spawned
        assert argv[0] == sys.executable
        assert (argv[1] == benchmark.WORKER_FLAG) is frozen
        assert env[benchmark._WORKER_ENV] == "1"
        if frozen:
            assert benchmark.is_worker_argv(argv)


class TestWorkerDispatch:
    def test_the_exact_frozen_shape_is_the_worker(self, monkeypatch: pytest.MonkeyPatch) -> None:
        use_frozen(monkeypatch, True)
        assert benchmark.is_worker_argv(_worker())

    @pytest.mark.parametrize(
        "argv",
        [
            ["scribe-app.exe"],
            ["scribe-app.exe", "--benchmark-worker"],
            # the dev shape is not the frozen worker
            [sys.executable, "-m", "scribe_desktop.benchmark", *_TAIL, "--audio-seconds", "1"],
            # an extra argument
            ["x", "--benchmark-worker", *_TAIL, "--audio-seconds", "1", "--models"],
            # a missing option
            ["x", "--benchmark-worker", *_TAIL],
            # reordered options
            ["x", "--benchmark-worker", "--models-root", r"C:\m", "--single", "medium",
             "--audio", "a", "--audio-seconds", "1"],
            # a repeated option in place of another
            ["x", "--benchmark-worker", "--single", "a", "--single", "b", "--audio", "a",
             "--audio-seconds", "1"],
            # a value that is itself an option, or empty
            ["x", "--benchmark-worker", "--single", "--models", "--models-root", r"C:\m",
             "--audio", "a", "--audio-seconds", "1"],
            ["x", "--benchmark-worker", "--single", "", "--models-root", r"C:\m",
             "--audio", "a", "--audio-seconds", "1"],
            # the flag anywhere but first
            ["x", *_TAIL, "--benchmark-worker", "--audio-seconds", "1"],
            # round 24: seconds the worker's parser would refuse (exit 2)
            ["x", "--benchmark-worker", *_TAIL, "--audio-seconds", "abc"],
            # round 27 PR-MED-021: a network value of any path option
            ["x", "--benchmark-worker", "--single", "medium", "--models-root", r"\\h\s",
             "--audio", r"C:\t\s.wav", "--audio-seconds", "1"],
            ["x", "--benchmark-worker", "--single", "medium", "--models-root", r"C:\m",
             "--audio", "//h/s/a.wav", "--audio-seconds", "1"],
            ["x", "--benchmark-worker", "--single", r"\/h/s/medium", "--models-root", r"C:\m",
             "--audio", r"C:\t\s.wav", "--audio-seconds", "1"],
        ],
    )
    def test_anything_else_is_not_the_worker(self, argv: list[str]) -> None:
        assert not benchmark.is_worker_argv(argv)

    def test_a_packaged_build_never_spawns_a_network_worker(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Round 27 PR-MED-021: the frozen worker_argv refuses its own UNC shape.
        use_frozen(monkeypatch, True)
        with pytest.raises(RuntimeError, match="not admissible"):
            _worker(Path(r"\\h\s\models"))

    def test_run_worker_needs_the_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        use_frozen(monkeypatch, True)
        monkeypatch.delenv(benchmark._WORKER_ENV, raising=False)
        monkeypatch.setattr(benchmark, "main", lambda argv: pytest.fail("worker started"))
        assert benchmark.run_worker(_worker()) is None
        monkeypatch.setenv(benchmark._WORKER_ENV, "0")
        assert benchmark.run_worker(_worker()) is None

    def test_run_worker_runs_main_on_the_options(self, monkeypatch: pytest.MonkeyPatch) -> None:
        use_frozen(monkeypatch, True)
        monkeypatch.setenv(benchmark._WORKER_ENV, "1")
        given: list[list[str]] = []
        monkeypatch.setattr(benchmark, "main", lambda argv: given.append(argv) or 7)
        assert benchmark.run_worker(_worker()) == 7
        assert given == [[*_TAIL, "--audio-seconds", "53.2"]]
        assert benchmark.run_worker([*_worker(), "--extra"]) is None
        assert len(given) == 1

    def test_a_worker_exception_is_one_type_name_line(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Round 13 MED-003 (C3): no traceback, no message, no bootloader box.
        use_frozen(monkeypatch, True)
        monkeypatch.setenv(benchmark._WORKER_ENV, "1")

        def broken(argv: list[str]) -> int:
            raise ValueError("Jane Citizen")

        monkeypatch.setattr(benchmark, "main", broken)
        assert benchmark.run_worker(_worker()) == 1
        captured = capsys.readouterr()
        assert captured.err == "benchmark_worker error_code=ValueError\n"
        assert captured.out == ""

    def test_a_worker_exception_with_no_stderr_is_still_exit_1(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        use_frozen(monkeypatch, True)
        monkeypatch.setenv(benchmark._WORKER_ENV, "1")
        monkeypatch.setattr(sys, "stderr", None)
        monkeypatch.setattr(benchmark, "main", lambda argv: 1 // 0)
        assert benchmark.run_worker(_worker()) == 1

    def test_an_argparse_exit_passes_through(self, monkeypatch: pytest.MonkeyPatch) -> None:
        use_frozen(monkeypatch, True)
        monkeypatch.setenv(benchmark._WORKER_ENV, "1")

        def exits(argv: list[str]) -> int:
            raise SystemExit(2)

        monkeypatch.setattr(benchmark, "main", exits)
        with pytest.raises(SystemExit):
            benchmark.run_worker(_worker())

    @pytest.mark.parametrize("name", ["-x", "--models", ""])
    def test_a_packaged_build_refuses_a_shape_its_dispatch_would_not_take(
        self, monkeypatch: pytest.MonkeyPatch, name: str
    ) -> None:
        # Round 13 LOW-004: never a second app with an "already running" box.
        use_frozen(monkeypatch, True)
        with pytest.raises(RuntimeError, match="not admissible"):
            benchmark.worker_argv(name, Path(r"C:\m"), Path(r"C:\t\s.wav"), 1.0)
        use_frozen(monkeypatch, False)
        assert benchmark.worker_argv(name, Path(r"C:\m"), Path(r"C:\t\s.wav"), 1.0)[4] == name

    def test_app_main_dispatches_before_logging_and_qt(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop import app as app_module

        use_frozen(monkeypatch, True)
        monkeypatch.setattr(app_module.install_layout, "outside_install_folder", lambda: None)
        monkeypatch.setenv(benchmark._WORKER_ENV, "1")
        monkeypatch.setattr(benchmark, "main", lambda argv: 0)
        monkeypatch.setattr(app_module, "setup_logging", lambda *a, **k: pytest.fail("logged"))
        monkeypatch.setattr(app_module, "QApplication", lambda argv: pytest.fail("Qt"))
        monkeypatch.setattr(
            app_module, "acquire_instance_exclusion", lambda *a, **k: pytest.fail("guard")
        )
        assert app_module.main(_worker()) == 0

    def test_app_main_ignores_the_flag_without_the_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop import app as app_module

        use_frozen(monkeypatch, True)
        monkeypatch.setattr(app_module.install_layout, "outside_install_folder", lambda: None)
        monkeypatch.delenv(benchmark._WORKER_ENV, raising=False)
        monkeypatch.setattr(benchmark, "main", lambda argv: pytest.fail("worker started"))
        monkeypatch.setattr(app_module, "setup_logging", _proceeds)
        with pytest.raises(_Proceeded):
            app_module.main(_worker())


# --- Task 3.5: the build audit's offline self-check ----------------------------------


_SELF_CHECK = ["scribe-app.exe", "--self-check-offline"]


class TestOfflineSelfCheck:
    """``scribe-app.exe --self-check-offline`` (installation plan Task 3.5):
    exit-code only, run by ``build-release.py --audit`` against a fresh
    bundle with every offline variable set wrong."""

    @pytest.fixture(autouse=True)
    def _restore_the_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The check really applies the offline environment: every variable
        it sets or removes is registered with ``monkeypatch`` first, so the
        test process is restored afterwards."""
        for name in benchmark.OFFLINE_ENV:
            monkeypatch.setenv(name, os.environ.get(name, "1"))
        for name in ("SSLKEYLOGFILE", "LLAMA_CPP_LIB_PATH"):
            monkeypatch.delenv(name, raising=False)

    def _absent(self, name: str) -> None:
        return None

    def test_it_applies_the_offline_environment_over_hostile_values(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop import app as app_module

        for name in benchmark.OFFLINE_ENV:
            monkeypatch.setenv(name, "0")
        monkeypatch.setenv("SSLKEYLOGFILE", r"C:\nowhere\keys.log")
        monkeypatch.setenv("LLAMA_CPP_LIB_PATH", r"C:\nowhere")
        assert app_module.run_offline_self_check(_SELF_CHECK, self._absent) == 0
        assert all(os.environ[name] == "1" for name in benchmark.OFFLINE_ENV)
        assert "SSLKEYLOGFILE" not in os.environ and "LLAMA_CPP_LIB_PATH" not in os.environ

    def test_a_failed_assertion_is_exit_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scribe_desktop import app as app_module

        def broken() -> None:
            raise benchmark.OfflineEnvError("offline kill-switches not active")

        monkeypatch.setattr(app_module, "assert_offline_env", broken)
        assert app_module.run_offline_self_check(_SELF_CHECK, self._absent) == 1

    @pytest.mark.parametrize("module", ["PySide6.QtNetwork", "PySide6.QtWebSockets"])
    def test_a_findable_qt_network_module_is_exit_2(
        self, monkeypatch: pytest.MonkeyPatch, module: str
    ) -> None:
        from scribe_desktop import app as app_module

        def find(name: str) -> object | None:
            return object() if name == module else None

        assert app_module.run_offline_self_check(_SELF_CHECK, find) == 2

    def test_a_find_that_raises_is_not_absent(self) -> None:
        from scribe_desktop import app as app_module

        def find(name: str) -> None:
            raise ImportError(name)

        assert app_module.run_offline_self_check(_SELF_CHECK, find) == 2

    def test_the_default_finder_is_importlibs_at_call_time(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With no finder given, the check asks ``importlib.util.find_spec`` —
        resolved when it runs — so a findable Qt networking module is exit 2.
        Round 20 PR-MED-018: the finder is a fake, never this venv's packages
        (C6); the real discovery is the packaged audit's (Task 3.5)."""
        from scribe_desktop import app as app_module

        asked: list[str] = []

        def find(name: str) -> object | None:
            asked.append(name)
            return object() if name == "PySide6.QtNetwork" else None

        monkeypatch.setattr(app_module.importlib.util, "find_spec", find)
        assert app_module.run_offline_self_check(_SELF_CHECK) == 2
        assert asked == ["PySide6.QtNetwork"]

    @pytest.mark.parametrize(
        "argv",
        [
            ["scribe-app.exe"],
            ["scribe-app.exe", "--self-check-offline", "--extra"],
            ["scribe-app.exe", "--extra", "--self-check-offline"],
            ["scribe-app.exe", "--self-check"],
        ],
    )
    def test_anything_else_is_not_the_check(self, argv: list[str]) -> None:
        from scribe_desktop import app as app_module

        assert app_module.run_offline_self_check(argv, lambda n: pytest.fail("checked")) is None

    def test_app_main_answers_before_the_install_folder_logging_and_qt(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop import app as app_module

        _frozen_at(monkeypatch, Path(r"C:\Users\x\Downloads\dist\scribe\scribe-app.exe"))
        monkeypatch.setattr(
            app_module.install_layout, "outside_install_folder", lambda: pytest.fail("checked")
        )
        monkeypatch.setattr(app_module, "setup_logging", lambda *a, **k: pytest.fail("logged"))
        monkeypatch.setattr(app_module, "QApplication", lambda argv: pytest.fail("Qt"))
        monkeypatch.setattr(app_module, "run_benchmark_worker", lambda argv: pytest.fail("w"))
        monkeypatch.setattr(app_module.importlib.util, "find_spec", lambda name: None)
        assert app_module.main(_SELF_CHECK) == 0


# --- Task 2.7: a packaged build outside its install folder ---------------------------


def _entry(which: str) -> Callable[[], int]:
    if which == "app":
        from scribe_desktop import app as app_module

        return lambda: app_module.main(["scribe-app.exe"])
    return nh.main


def _patch_refusal(
    monkeypatch: pytest.MonkeyPatch, which: str, calls: list[str]
) -> logging.Logger:
    """Record the refusal's logging and box; make proceeding observable."""
    logger = logging.getLogger(f"test-not-installed-{which}")
    module: Any
    if which == "app":
        from PySide6.QtWidgets import QApplication

        from scribe_desktop import app as module

        monkeypatch.setattr(
            module, "QApplication", lambda argv: QApplication.instance() or QApplication(argv)
        )
        monkeypatch.setattr(module, "_show_not_installed_warning", lambda: calls.append("box"))
    else:
        module = nh

    def setup(name: str, **kwargs: Any) -> logging.Logger:
        if kwargs != {"file": False}:
            raise _Proceeded()
        calls.append(f"log:{name}")
        return logger

    monkeypatch.setattr(module, "setup_logging", setup)
    return logger


@pytest.mark.parametrize("which", ["app", "host"])
class TestOutsideTheInstallFolder:
    def test_a_copy_elsewhere_is_refused_touching_no_data_root(
        self,
        which: str,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        use_channel(monkeypatch, "production")
        local = tmp_path / "Local"
        local.mkdir()
        monkeypatch.setenv("LOCALAPPDATA", str(local))
        _frozen_at(monkeypatch, _real(tmp_path) / "Downloads" / "scribe-app.exe")
        monkeypatch.setattr(install_layout, "INSTALL_ROOTS", (str(_real(tmp_path) / "Install"),))
        calls: list[str] = []
        logger = _patch_refusal(monkeypatch, which, calls)
        caplog.set_level(logging.INFO, logger=logger.name)
        code = _entry(which)()
        assert code == (1 if which == "app" else 3)
        expected = [f"log:scribe-{which}"] + (["box"] if which == "app" else [])
        assert calls == expected
        assert list(local.iterdir()) == []  # no data root, log or lock (C8 / Task 2.7)
        event = "app_exit" if which == "app" else "host_exit"
        assert [r.getMessage() for r in caplog.records if r.name == logger.name] == [
            f"{event} error_code=InstallLayoutError state=not_installed"
        ]

    def test_the_install_folder_proceeds(
        self, which: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = _real(tmp_path) / "Install"
        root.mkdir()
        _frozen_at(monkeypatch, root / "scribe-app.exe")
        monkeypatch.setattr(install_layout, "INSTALL_ROOTS", (str(root),))
        monkeypatch.delenv(benchmark._WORKER_ENV, raising=False)
        _patch_refusal(monkeypatch, which, [])
        with pytest.raises(_Proceeded):
            _entry(which)()

    def test_a_source_run_never_reads_the_executable(
        self, which: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(install_layout, "executable", lambda: pytest.fail("read"))
        monkeypatch.delenv(benchmark._WORKER_ENV, raising=False)
        _patch_refusal(monkeypatch, which, [])
        with pytest.raises(_Proceeded):
            _entry(which)()

    @windows_only
    def test_a_link_into_the_install_folder_proceeds(
        self, which: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import _winapi

        root = _real(tmp_path) / "Install"
        root.mkdir()
        link = _real(tmp_path) / "Shortcut"
        _winapi.CreateJunction(str(root), str(link))
        _frozen_at(monkeypatch, link / "scribe-app.exe")
        monkeypatch.setattr(install_layout, "INSTALL_ROOTS", (str(root),))
        monkeypatch.delenv(benchmark._WORKER_ENV, raising=False)
        _patch_refusal(monkeypatch, which, [])
        with pytest.raises(_Proceeded):
            _entry(which)()

    @windows_only
    def test_a_link_at_the_install_path_pointing_elsewhere_is_refused(
        self, which: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import _winapi

        elsewhere = _real(tmp_path) / "Elsewhere"
        elsewhere.mkdir()
        root = _real(tmp_path) / "Install"
        _winapi.CreateJunction(str(elsewhere), str(root))
        _frozen_at(monkeypatch, root / "scribe-app.exe")
        monkeypatch.setattr(install_layout, "INSTALL_ROOTS", (str(root),))
        calls: list[str] = []
        _patch_refusal(monkeypatch, which, calls)
        assert _entry(which)() == (1 if which == "app" else 3)
        assert calls[0] == f"log:scribe-{which}"


def test_the_refusal_line_and_the_helper() -> None:
    assert install_layout.NOT_INSTALLED_LINE == (
        "Clinic Scribe is not running from its install folder — reinstall Clinic Scribe."
    )
    assert install_layout.outside_install_folder() is None  # a source run (pinned)


def test_stderr_only_logging_creates_no_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    logger = logging_setup.setup_logging("test-file-false", file=False)
    try:
        assert not any(isinstance(h, logging.FileHandler) for h in logger.handlers)
        assert list(tmp_path.iterdir()) == []
    finally:
        for handler in logger.handlers:
            handler.close()
        logger.handlers.clear()


# --- Task 2.2: the native host's stdio -------------------------------------------------


class TestBinaryStdio:
    def test_present_streams_give_their_buffers(self) -> None:
        stdin, stdout = io.BytesIO(), io.BytesIO()
        got = nh.binary_stdio(
            SimpleNamespace(buffer=stdin),
            SimpleNamespace(buffer=stdout),
            open_std=lambda name: pytest.fail("opened a handle"),
        )
        assert got == (stdin, stdout)

    def test_absent_streams_are_opened_over_the_standard_handles(self) -> None:
        opened: dict[str, io.BytesIO] = {}

        def open_std(name: str) -> io.BytesIO:
            opened[name] = io.BytesIO()
            return opened[name]

        got = nh.binary_stdio(None, None, open_std=open_std)
        assert list(opened) == ["stdin", "stdout"]
        assert got == (opened["stdin"], opened["stdout"])

    def test_one_present_and_one_opened(self) -> None:
        stdin, stdout = io.BytesIO(), io.BytesIO()
        got = nh.binary_stdio(SimpleNamespace(buffer=stdin), None, open_std=lambda name: stdout)
        assert got == (stdin, stdout)

    @pytest.mark.parametrize("missing", ["stdin", "stdout"])
    def test_no_handle_is_none(self, missing: str) -> None:
        got = nh.binary_stdio(
            None, None, open_std=lambda name: None if name == missing else io.BytesIO()
        )
        assert got is None

    @pytest.mark.skipif(sys.platform != "win32", reason="msvcrt is Windows-only")
    @pytest.mark.parametrize("which", ["stdin", "stdout"])
    def test_a_handle_the_c_runtime_refuses_is_none(
        self, monkeypatch: pytest.MonkeyPatch, which: str
    ) -> None:
        # Round 13 LOW-002: a stale non-null handle is "no stream", not a
        # crash. Neither the real GetStdHandle nor a real handle is used (C6).
        import ctypes
        import msvcrt

        def get_std_handle(which_id: Any) -> int:
            return 1234

        kernel32 = SimpleNamespace(GetStdHandle=get_std_handle)
        monkeypatch.setattr(ctypes, "WinDLL", lambda *a, **k: kernel32)

        def refuse(handle: int, flags: int) -> int:
            assert handle == 1234
            raise OSError(9, "bad handle")

        monkeypatch.setattr(msvcrt, "open_osfhandle", refuse)
        assert nh.open_std_stream(which) is None


def _host_past_origin(monkeypatch: pytest.MonkeyPatch, events: list[Any]) -> logging.Logger:
    logger = logging.getLogger("test-host-stdio")
    monkeypatch.setattr(nh, "setup_logging", lambda name: logger)
    monkeypatch.setattr(nh, "install_exception_hooks", lambda given: None)
    monkeypatch.setattr(nh, "_log_registration_paths", lambda given: None)
    monkeypatch.setattr(nh, "verify_origin", lambda argv: True)
    monkeypatch.setattr(nh, "app_relay_factory", lambda: "relay")
    monkeypatch.setattr(nh, "set_binary_stdio", lambda a, b: events.append(("binary", a, b)))
    monkeypatch.setattr(
        nh, "run_host", lambda a, b, lg, relay_factory: events.append(("run", a, b)) or 0
    )
    return logger


def test_the_host_speaks_over_the_streams_it_obtained(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[Any] = []
    _host_past_origin(monkeypatch, events)
    stdin, stdout = io.BytesIO(), io.BytesIO()
    monkeypatch.setattr(nh, "binary_stdio", lambda a, b: (stdin, stdout))
    assert nh.main() == 0
    assert events == [("binary", stdin, stdout), ("run", stdin, stdout)]


def test_a_host_with_no_streams_exits_before_protocol_mode(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    events: list[Any] = []
    logger = _host_past_origin(monkeypatch, events)
    caplog.set_level(logging.INFO, logger=logger.name)
    monkeypatch.setattr(nh, "binary_stdio", lambda a, b: None)
    assert nh.main() == 4
    assert events == []
    assert "host_stdio state=absent" in [r.getMessage() for r in caplog.records]


@pytest.mark.skipif(sys.platform != "win32", reason="msvcrt is Windows-only")
def test_set_binary_stdio_applies_to_the_streams_given(monkeypatch: pytest.MonkeyPatch) -> None:
    import msvcrt

    from scribe_desktop import framing

    modes: list[tuple[int, int]] = []
    monkeypatch.setattr(msvcrt, "setmode", lambda fd, mode: modes.append((fd, mode)))
    framing.set_binary_stdio(
        SimpleNamespace(fileno=lambda: 41), SimpleNamespace(fileno=lambda: 42)
    )
    assert modes == [(41, os.O_BINARY), (42, os.O_BINARY)]


def test_a_none_stderr_is_tolerated_by_the_logging_and_the_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Task 0.2 found stderr None under Chrome: the host's logging builds no
    stderr handler, the exception hook still logs its one line to the file,
    and a failing handler's report has nowhere to go and does not raise."""
    monkeypatch.setattr(sys, "stderr", None)
    logger = logging_setup.setup_logging("test-none-stderr", log_dir=tmp_path)
    try:
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.FileHandler)
        restore = exclusions.install_exception_hooks(logger)
        try:
            sys.excepthook(ValueError, ValueError("Jane Citizen"), None)
        finally:
            restore()
        logger.handlers[0].handleError(logging.makeLogRecord({}))  # never raises
    finally:
        for handler in logger.handlers:
            handler.close()
        logger.handlers.clear()
    text = (tmp_path / "test-none-stderr.log").read_text(encoding="utf-8")
    assert "uncaught_exception detail_code=main error_code=ValueError" in text
    assert "Jane" not in text


# --- Task 2.3: the Chrome link in Chrome's order --------------------------------------


class _Layer:
    def __init__(self, entries: tuple[HostEntry, ...] = (), *, broken: bool = False) -> None:
        self.entries = entries
        self.broken = broken
        self.keys: list[str] = []

    def native_host_entries(self, key: str) -> tuple[HostEntry, ...]:
        self.keys.append(key)
        if self.broken:
            raise OSError("denied")
        return self.entries


def _manifest(tmp_path: Path, name: str, *, launcher: bool = True) -> str:
    folder = tmp_path / name
    folder.mkdir()
    exe = folder / "scribe-host.exe"
    if launcher:
        exe.write_bytes(b"MZ")
    path = folder / "host.json"
    path.write_text(json.dumps({"path": str(exe)}), encoding="utf-8")
    return str(path)


class TestRegistrationStatus:
    def test_no_layer_reads_nothing(self) -> None:
        got = status.read_registration_status(None)
        assert not got.checked and not got.registered
        assert status.registration_lines(got) == ("Registration: not checked",)

    def test_a_failing_layer_is_not_checked(self) -> None:
        assert not status.read_registration_status(_Layer(broken=True)).checked

    def test_none_found(self) -> None:
        layer = _Layer()
        got = status.read_registration_status(layer)
        assert got.checked and not got.registered and got.winner is None
        assert layer.keys == [nh.identity.registry_key()]
        assert status.registration_lines(got) == (
            "Registration: NOT registered — "
            "run scripts/register-native-host.py again from a normal terminal",
        )

    def test_hkcu_only(self, tmp_path: Path) -> None:
        entry = HostEntry("HKCU", "32", _manifest(tmp_path, "u"))
        got = status.read_registration_status(_Layer((entry,)))
        assert got.registered and got.winner == entry and got.others == ()
        assert status.registration_lines(got) == (
            "Registration: registered ✓ (per-user Chrome link)",
        )

    def test_hklm_only(self, tmp_path: Path) -> None:
        entry = HostEntry("HKLM", "64", _manifest(tmp_path, "m"))
        got = status.read_registration_status(_Layer((entry,)))
        assert got.registered and got.winner == entry
        assert status.registration_lines(got) == (
            "Registration: registered ✓ (this computer's Chrome link)",
        )

    def test_both_the_per_user_entry_wins(self, tmp_path: Path) -> None:
        user = HostEntry("HKCU", "32", _manifest(tmp_path, "u"))
        machine = HostEntry("HKLM", "64", _manifest(tmp_path, "m"))
        got = status.read_registration_status(_Layer((user, machine)))
        assert got.winner == user and got.others == (machine,)
        assert got.registry_value == user.manifest
        assert status.registration_lines(got) == (
            "Registration: registered ✓ (per-user Chrome link; 1 other link found, not used)",
        )

    def test_the_32_bit_view_only(self, tmp_path: Path) -> None:
        # The reader's half; the real layer's half (only the 32-bit view
        # populated) is `TestRealLayerOverAFakeWinreg` (round 13 LOW-008).
        entry = HostEntry("HKLM", "32", _manifest(tmp_path, "m32"))
        got = status.read_registration_status(_Layer((entry,)))
        assert got.registered and got.winner is not None and got.winner.place == "hklm_32"
        assert status.registration_lines(got) == (
            "Registration: registered ✓ (this computer's Chrome link)",
        )

    def test_the_winner_decides_even_when_another_entry_is_good(self, tmp_path: Path) -> None:
        # Chrome uses the first entry it finds: a broken winner is NOT
        # rescued by a working machine-wide one.
        broken = HostEntry("HKCU", "32", _manifest(tmp_path, "u", launcher=False))
        good = HostEntry("HKLM", "64", _manifest(tmp_path, "m"))
        got = status.read_registration_status(_Layer((broken, good)))
        assert not got.registered and got.winner == broken
        assert status.registration_lines(got)[0].startswith("Registration: NOT registered")

    def test_a_frozen_build_warns_of_a_per_user_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        user = HostEntry("HKCU", "32", _manifest(tmp_path, "u"))
        machine = HostEntry("HKLM", "64", _manifest(tmp_path, "m"))
        assert not status.read_registration_status(_Layer((user, machine))).per_user_override
        use_frozen(monkeypatch, True)
        got = status.read_registration_status(_Layer((user, machine)))
        assert got.per_user_override
        assert status.registration_lines(got)[1] == status.PER_USER_OVERRIDE_LINE
        assert status.PER_USER_OVERRIDE_LINE == (
            "Warning: a per-user Chrome link overrides the installed one."
        )
        assert not status.read_registration_status(_Layer((machine,))).per_user_override

    def test_a_broken_per_user_winner_is_not_told_to_reinstall(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Round 23: the installer writes HKLM only, so "reinstall" cannot fix
        # a broken per-user entry that Chrome uses.
        broken = HostEntry("HKCU", "32", _manifest(tmp_path, "u", launcher=False))
        good = HostEntry("HKLM", "64", _manifest(tmp_path, "m"))
        use_frozen(monkeypatch, True)
        got = status.read_registration_status(_Layer((broken, good)))
        assert not got.registered and got.per_user_override
        assert status.registration_lines(got) == (
            "Registration: NOT registered — the per-user Chrome link that Chrome uses is "
            "broken, and reinstalling does not remove it",
            status.PER_USER_OVERRIDE_LINE,
        )
        # With no per-user entry the installed app's remedy is still a reinstall.
        missing = HostEntry("HKLM", "64", _manifest(tmp_path, "m2", launcher=False))
        lines = status.registration_lines(status.read_registration_status(_Layer((missing,))))
        assert lines == ("Registration: NOT registered — reinstall Clinic Scribe",)

    @pytest.mark.parametrize(
        "unc",
        [
            r"\\host\share\host.json",
            "//host/share/host.json",
            # Round 27 PR-MED-020: the mixed-separator forms Windows reads as UNC.
            r"\/host/share/host.json",
            "/\\host\\share\\host.json",
        ],
    )
    def test_a_network_manifest_is_never_touched(
        self, unc: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # H.4 SEC-003: no stat or read of a network-share path (no SMB I/O at
        # start-up, C1); it reads as not registered. Round 28 PR-LOW-030: a
        # regressed guard fails here at its first listed `Path` call.
        forbid_network_io(monkeypatch)
        got = status.read_registration_status(_Layer((HostEntry("HKCU", "32", unc),)))
        assert got.checked and not got.registered and not got.manifest_exists

    @pytest.mark.parametrize(
        "launcher",
        [r"\\host\share\scribe-host.exe", r"\/host/share/scribe-host.exe"],
    )
    def test_a_network_launcher_is_never_touched(
        self, launcher: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        manifest = tmp_path / "host.json"
        manifest.write_text(json.dumps({"path": launcher}), "utf-8")
        # Round 28 PR-LOW-030: the local manifest is read; the network
        # launcher fails the test at its first listed `Path` call if reached.
        forbid_network_io(monkeypatch)
        got = status.read_registration_status(_Layer((HostEntry("HKLM", "64", str(manifest)),)))
        assert got.manifest_exists and not got.launcher_exists and not got.registered

    @pytest.mark.parametrize("body", ['["x"]', '{"path": 7}', '"text"', "not json"])
    def test_a_malformed_manifest_is_not_registered_never_a_crash(
        self, tmp_path: Path, body: str
    ) -> None:
        # Round 13 LOW-011.
        manifest = tmp_path / "host.json"
        manifest.write_text(body, encoding="utf-8")
        got = status.read_registration_status(_Layer((HostEntry("HKLM", "64", str(manifest)),)))
        assert got.manifest_exists and not got.launcher_exists and not got.registered

    def test_no_line_ever_shows_a_path(self, tmp_path: Path) -> None:
        user = HostEntry("HKCU", "32", _manifest(tmp_path, "u"))
        got = status.read_registration_status(_Layer((user,)))
        assert str(tmp_path) not in "\n".join(status.registration_lines(got))


def test_the_status_panel_reads_through_the_layer_it_was_given(
    qapp: Any, tmp_path: Path
) -> None:
    from scribe_desktop.ui.main_window import StatusPanel

    entry = HostEntry("HKLM", "64", _manifest(tmp_path, "m"))
    panel = StatusPanel(config_root=tmp_path / "config", windows_layer=_Layer((entry,)))
    assert panel.registration_label.text() == (
        "Registration: registered ✓ (this computer's Chrome link)"
    )
    assert StatusPanel(config_root=tmp_path / "config").registration_label.text() == (
        "Registration: not checked"
    )


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


class TestHostRegistrationLog:
    def _messages(self, caplog: pytest.LogCaptureFixture, layer: Any) -> list[str]:
        logger = logging.getLogger("test-host-registration")
        caplog.set_level(logging.INFO, logger=logger.name)
        nh._log_registration_paths(logger, layer)
        return [r.getMessage() for r in caplog.records if r.name == logger.name]

    def test_the_winner_then_the_others_then_the_launcher(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        user = HostEntry("HKCU", "32", _manifest(tmp_path, "u"))
        machine = HostEntry("HKLM", "64", _manifest(tmp_path, "m"))
        assert self._messages(caplog, _Layer((user, machine))) == [
            f"host_manifest count=2 detail_code=hkcu_32 path={user.manifest}",
            f"host_manifest_other detail_code=hklm_64 path={machine.manifest}",
            f"host_launcher path={tmp_path / 'u' / 'scribe-host.exe'}",
        ]

    def test_none_found(self, caplog: pytest.LogCaptureFixture) -> None:
        assert self._messages(caplog, _Layer()) == ["host_manifest state=absent"]

    @pytest.mark.parametrize("which", ["production", "dev"])
    def test_it_reads_this_channels_key(
        self, which: install_layout.Channel, monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # Round 22 (D9): the host log and the Status line read the SAME key —
        # this channel's host name — so the log's winner is Chrome's.
        use_channel(monkeypatch, which)
        layer = _Layer()
        self._messages(caplog, layer)
        status_layer = _Layer()
        status.read_registration_status(status_layer)
        assert layer.keys == status_layer.keys == [nh.identity.registry_key(which)]

    def test_anything_unreadable_is_one_line_never_a_crash(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        assert self._messages(caplog, _Layer(broken=True)) == ["host_manifest state=unreadable"]
        missing = HostEntry("HKLM", "64", str(tmp_path / "absent.json"))
        assert self._messages(caplog, _Layer((missing,)))[-1] == "host_manifest state=unreadable"

    @pytest.mark.parametrize(
        "unc",
        [
            r"\\host\share\host.json",
            "//host/share/host.json",
            r"\/host/share/host.json",
            "/\\host\\share\\host.json",
        ],
    )
    def test_a_network_manifest_is_logged_never_opened(
        self, unc: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        # H.4 SEC-003: a planted network-share value causes no SMB I/O.
        def refuse(self: Path, *args: Any, **kwargs: Any) -> str:
            raise AssertionError(f"opened {self}")

        monkeypatch.setattr(Path, "read_text", refuse)
        assert self._messages(caplog, _Layer((HostEntry("HKCU", "32", unc),))) == [
            f"host_manifest count=1 detail_code=hkcu_32 path={unc}",
            "host_manifest state=network_path",
        ]

    def test_reaching_the_real_layer_is_never_swallowed(self) -> None:
        # Round 13 LOW-003: the conftest's C6 sentinel fails loudly, not as
        # a `state=unreadable` line.
        with pytest.raises(AssertionError, match="real Win32WindowsLayer"):
            nh._log_registration_paths(logging.getLogger("test-host-registration"))


class _FakeKey:
    def __init__(self, values: dict[str, tuple[Any, int]]) -> None:
        self.values = values

    def __enter__(self) -> _FakeKey:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class FakeWinreg:
    """Just enough ``winreg`` for the real layer's reads; ``keys`` maps
    ``(hive, view, path)`` to values, ``denied`` raises PermissionError."""

    HKEY_CURRENT_USER = "HKCU"
    HKEY_LOCAL_MACHINE = "HKLM"
    KEY_READ = 0x20019
    KEY_QUERY_VALUE = 0x0001
    KEY_WOW64_32KEY = 0x0200
    KEY_WOW64_64KEY = 0x0100
    REG_SZ = 1
    REG_EXPAND_SZ = 2
    REG_DWORD = 4
    REG_MULTI_SZ = 7

    def __init__(self) -> None:
        self.keys: dict[tuple[str, str, str], dict[str, tuple[Any, int]]] = {}
        self.denied: set[tuple[str, str, str]] = set()
        self.opened: list[tuple[str, str, str]] = []
        self.access: dict[tuple[str, str, str], int] = {}

    def OpenKey(  # noqa: N802 - winreg's name
        self, hive: str, path: str, reserved: int = 0, access: int = 0
    ) -> _FakeKey:
        view = "32" if access & self.KEY_WOW64_32KEY else "64"
        where = (hive, view, path)
        self.opened.append(where)
        self.access[where] = access & ~(self.KEY_WOW64_32KEY | self.KEY_WOW64_64KEY)
        if where in self.denied:
            raise PermissionError("denied")
        if where not in self.keys:
            raise FileNotFoundError(path)
        return _FakeKey(self.keys[where])

    def QueryValueEx(self, key: _FakeKey, name: str) -> tuple[Any, int]:  # noqa: N802
        if name not in key.values:
            raise FileNotFoundError(name)
        return key.values[name]

    def ExpandEnvironmentStrings(self, value: str) -> str:  # noqa: N802
        return value.replace("%X%", "expanded")


@pytest.mark.skipif(sys.platform != "win32", reason="the real layer reads winreg on Windows")
class TestRealLayerOverAFakeWinreg:
    """The real ``Win32WindowsLayer`` methods over a FAKE ``winreg`` module
    (nothing real is read; ``__init__`` — the conftest sentinel — is not
    run: the methods use no instance state)."""

    KEY = r"Software\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host"

    @pytest.fixture
    def registry(self, monkeypatch: pytest.MonkeyPatch) -> FakeWinreg:
        fake = FakeWinreg()
        monkeypatch.setitem(sys.modules, "winreg", fake)
        return fake

    def _layer(self) -> Any:
        return object.__new__(exclusions.Win32WindowsLayer)

    def test_chromes_order_hkcu_then_hklm_32_bit_view_first(self, registry: FakeWinreg) -> None:
        for hive, view in exclusions.CHROME_LOOKUP_ORDER:
            registry.keys[(hive, view, self.KEY)] = {"": (f"{hive}-{view}.json", 1)}
        entries = self._layer().native_host_entries(self.KEY)
        assert [(e.hive, e.view, e.manifest) for e in entries] == [
            ("HKCU", "32", "HKCU-32.json"),
            ("HKCU", "64", "HKCU-64.json"),
            ("HKLM", "32", "HKLM-32.json"),
            ("HKLM", "64", "HKLM-64.json"),
        ]
        assert exclusions.CHROME_LOOKUP_ORDER == (
            ("HKCU", "32"), ("HKCU", "64"), ("HKLM", "32"), ("HKLM", "64"),
        )
        # Round 13 LOW-005: query-only, as Chromium opens them.
        assert set(registry.access.values()) == {registry.KEY_QUERY_VALUE}

    @pytest.mark.parametrize("hive", ["HKCU", "HKLM"])
    def test_a_32_bit_view_only_entry_wins(self, registry: FakeWinreg, hive: str) -> None:
        # Round 13 LOW-008: the real layer, only the 32-bit view populated.
        registry.keys[(hive, "32", self.KEY)] = {"": ("only32.json", 1)}
        entries = self._layer().native_host_entries(self.KEY)
        assert [(e.place, e.manifest) for e in entries] == [
            (f"{hive.lower()}_32", "only32.json")
        ]
        assert len(registry.opened) == 4  # every view was looked at

    def test_the_shared_hkcu_value_is_listed_once(self, registry: FakeWinreg) -> None:
        for view in ("32", "64"):
            registry.keys[("HKCU", view, self.KEY)] = {"": ("same.json", 1)}
        registry.keys[("HKLM", "64", self.KEY)] = {"": ("same.json", 1)}
        entries = self._layer().native_host_entries(self.KEY)
        assert [e.place for e in entries] == ["hkcu_32", "hklm_64"]

    def test_unreadable_absent_and_non_string_views_are_passed_over(
        self, registry: FakeWinreg
    ) -> None:
        registry.denied.add(("HKCU", "32", self.KEY))
        registry.keys[("HKCU", "64", self.KEY)] = {}  # no default value
        registry.keys[("HKLM", "32", self.KEY)] = {"": (7, 4)}  # a DWORD
        registry.keys[("HKLM", "64", self.KEY)] = {"": (r"%X%\host.json", 2)}
        entries = self._layer().native_host_entries(self.KEY)
        assert [(e.place, e.manifest) for e in entries] == [("hklm_64", r"expanded\host.json")]

    def test_wer_reads_the_hive_asked(self, registry: FakeWinreg) -> None:
        registry.keys[("HKLM", "64", exclusions.WER_EXCLUDED_KEY)] = {
            "scribe-app.exe": (1, 4),
            "scribe-host.exe": ("1", 1),  # not a DWORD: missing
        }
        layer = self._layer()
        assert layer.wer_exclusions("HKLM") == {"scribe-app.exe": 1}
        assert layer.wer_exclusions("HKCU") == {}

    def test_backup_values_are_read_from_hklm(self, registry: FakeWinreg) -> None:
        patterns = list(install_layout.backup_exclusion_patterns())
        base = exclusions.BACKUP_RESTORE_KEY
        registry.keys[("HKLM", "64", base + r"\FilesNotToBackup")] = {
            install_layout.BACKUP_VALUE_NAME: (patterns, 7)
        }
        registry.keys[("HKLM", "64", base + r"\FilesNotToSnapshot")] = {
            install_layout.BACKUP_VALUE_NAME: ("not multi", 1)
        }
        assert self._layer().backup_exclusions() == {"FilesNotToBackup": tuple(patterns)}
        registry.denied.add(("HKLM", "64", base + r"\FilesNotToBackup"))
        with pytest.raises(PermissionError):
            self._layer().backup_exclusions()


# --- Task 2.6: the real-ML legs' models root -------------------------------------------


@pytest.mark.real_models_root  # asserts the real resolver's answers (Task H.6)
class TestRealMlModelsRoot:
    @pytest.mark.parametrize("which", ["production", "dev"])
    def test_it_is_the_dev_root_whatever_the_pin(
        self, which: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        use_channel(monkeypatch, which)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert real_ml_models_root() == tmp_path / "ClinikoScribe-dev" / "models"
        assert install_layout.models_root("dev") == tmp_path / "ClinikoScribe-dev" / "models"

    def test_unset_localappdata_is_none_and_every_gate_closed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        assert real_ml_models_root() is None
        assert on_real_ml_root(lambda: pytest.fail("probed")) is False

    def test_a_gate_probes_under_the_dev_root_then_the_pin_returns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        seen: list[Path] = []

        def probe() -> bool:
            seen.append(install_layout.models_root())
            seen.append(benchmark.default_models_root())
            return True

        assert on_real_ml_root(probe) is True
        dev = tmp_path / "ClinikoScribe-dev" / "models"
        assert seen == [dev, dev]
        # The production pin is back for every other test (C8).
        assert install_layout.models_root() == tmp_path / "ClinikoScribe" / "models"

    def test_the_skip_reason_names_the_dev_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        reason = real_ml_skip_reason("silero VAD model")
        assert reason.startswith("silero VAD model not found under the source run's dev")
        assert str(tmp_path / "ClinikoScribe-dev" / "models") in reason

    def test_the_body_fixture_pins_every_model_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
    ) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        root = request.getfixturevalue("real_ml_models")
        assert root == tmp_path / "ClinikoScribe-dev" / "models"
        from scribe_desktop.speech import default_vad_model_path

        assert default_vad_model_path() == root / "silero-vad" / "silero_vad.onnx"

    def test_frozen_the_install_root_still_wins(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = _real(tmp_path) / "Install"
        _frozen_at(monkeypatch, root / "scribe-app.exe")
        monkeypatch.setattr(install_layout, "INSTALL_ROOTS", (str(root),))
        assert REAL_MODELS_ROOT("dev") == root / "models"


# --- Task H.6: every other test's models root is the conftest's empty folder ------------


class TestModelsRootPin:
    """Round 27 PR-MED-022 (C6): the conftest's ``pinned_models_root``."""

    @pytest.mark.parametrize("run", ["first", "second"])
    def test_an_unmarked_test_resolves_every_model_under_its_own_empty_folder(
        self,
        run: str,
        pinned_models_root: Path | None,
        tmp_path: Path,
        tmp_path_factory: pytest.TempPathFactory,
    ) -> None:
        from scribe_desktop.language_model import default_language_model_path
        from scribe_desktop.speaker_embedding import default_speaker_model_path
        from scribe_desktop.speech import default_vad_model_path
        from scribe_desktop.transcription import default_whisper_model_dir

        root = pinned_models_root
        assert root is not None
        assert install_layout.models_root() == root
        assert install_layout.models_root("dev") == root
        assert benchmark.default_models_root() == root
        assert root.is_relative_to(tmp_path_factory.getbasetemp())
        assert not root.is_relative_to(tmp_path)
        # Empty and the test's own: each run finds it empty, then writes to
        # it, so a folder shared between tests fails whichever run is second.
        assert list(root.iterdir()) == []
        (root / run).write_bytes(b"")
        # Every model path the app builds (`test_every_models_root_caller_is_known`).
        for path in (
            default_vad_model_path(),
            default_whisper_model_dir(),
            default_language_model_path(),
            default_speaker_model_path(),
        ):
            assert path.is_relative_to(root), path

    def test_a_real_ml_body_pin_lands_after_and_wins(
        self, real_ml_models: Path, pinned_models_root: Path | None
    ) -> None:
        # The conftest pin was applied, and the body's pin replaced it.
        assert pinned_models_root is not None
        assert install_layout.models_root() == real_ml_models_root() == real_ml_models


@pytest.mark.real_models_root
class TestTheMarkerOptsOut:
    def test_a_marked_class_keeps_the_real_resolver(
        self, pinned_models_root: Path | None
    ) -> None:
        assert pinned_models_root is None
        assert install_layout.models_root is REAL_MODELS_ROOT


@pytest.mark.real_models_root
def test_a_marked_function_keeps_the_real_resolver(pinned_models_root: Path | None) -> None:
    assert pinned_models_root is None
    assert install_layout.models_root is REAL_MODELS_ROOT


# Every function that starts a model path at the resolver, by module (from
# the code: ``MODELS_DIRNAME`` is read only in ``install_layout.models_root``).
# The four path builders are the ones the pin test above resolves; the rest
# hand the root itself on, which ``benchmark.default_models_root`` covers
# (``validation.main`` only names it in its model refusals — pilot plan
# Task 2.4).
_MODELS_ROOT_CALLERS = frozenset(
    {
        ("install_layout.py", "models_root"),
        ("benchmark.py", "default_models_root"),
        ("benchmark.py", "main"),
        ("language_model.py", "default_language_model_path"),
        ("speaker_embedding.py", "default_speaker_model_path"),
        ("speech.py", "default_vad_model_path"),
        ("transcription.py", "default_whisper_model_dir"),
        ("ui/microphone.py", "_default_benchmark_runner"),
        ("validation.py", "main"),
        ("scripts/setup-models.py", "models_root"),
        ("scripts/setup-models.py", "main"),
    }
)
_RESOLVER_NAMES = frozenset({"models_root", "default_models_root"})


def _models_root_callers(source: str, module: str) -> set[tuple[str, str]]:
    """``(module, enclosing function)`` for each call of a resolver name and
    each read of ``MODELS_DIRNAME`` in ``source``."""
    found: set[tuple[str, str]] = set()

    def visit(node: ast.AST, owner: str) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            owner = node.name
        called = isinstance(node, ast.Call) and _called_name(node) in _RESOLVER_NAMES
        read = (
            isinstance(node, (ast.Name, ast.Attribute))
            and isinstance(node.ctx, ast.Load)
            and (node.id if isinstance(node, ast.Name) else node.attr) == "MODELS_DIRNAME"
        )
        if called or read:
            found.add((module, owner))
        for child in ast.iter_child_nodes(node):
            visit(child, owner)

    visit(ast.parse(source), "<module>")
    return found


def test_every_models_root_caller_is_known() -> None:
    """Task H.6, a source scan of the app and the scripts: the pin test's
    four model paths are every path built from the resolver (a scan, not a
    proof: a resolver reached through another name is unseen)."""
    src = TESTS.parent / "src" / "scribe_desktop"
    scripts = TESTS.parents[1] / "scripts"
    files = [(p.relative_to(src).as_posix(), p) for p in sorted(src.rglob("*.py"))]
    files += [(f"scripts/{p.name}", p) for p in sorted(scripts.glob("*.py"))]
    assert len(files) > 40, "the scan found too few files to mean anything"
    found: set[tuple[str, str]] = set()
    for module, path in files:
        found |= _models_root_callers(path.read_text(encoding="utf-8"), module)
    assert found == _MODELS_ROOT_CALLERS


@pytest.mark.parametrize(
    "source",
    [
        "def f():\n    return install_layout.models_root() / 'x'\n",
        "def f():\n    return default_models_root()\n",
        "def f(base):\n    return base / MODELS_DIRNAME\n",
        "def f(base):\n    return base / install_layout.MODELS_DIRNAME\n",
    ],
)
def test_the_models_root_scan_sees_each_form(source: str) -> None:
    assert _models_root_callers(source, "x.py") == {("x.py", "f")}


# Task H.6 step 2: the ONLY tests that opt out of the pin — the resolver's own,
# by class or function (a module-level opt-out was rejected) — plus the two
# marker tripwires above.
_REAL_MODELS_ROOT_MARKED = frozenset(
    {
        ("test_install_layout.py", "TestModelsRoot"),
        ("test_install_layout.py", "test_every_store_is_under_the_channels_folder"),
        ("test_frozen_runtime.py", "TestRealMlModelsRoot"),
        ("test_frozen_runtime.py", "TestTheMarkerOptsOut"),
        ("test_frozen_runtime.py", "test_a_marked_function_keeps_the_real_resolver"),
        ("test_language_model_runtime.py", "test_default_model_path_under_the_models_root"),
        ("test_language_model_runtime.py", "test_localappdata_unset_reports_unavailable"),
        ("test_speaker_embedding.py", "test_default_model_path_under_the_models_root"),
    }
)


def _marked_opt_outs(source: str, module: str) -> set[tuple[str, str]]:
    """``(module, class or function)`` for each one whose decorators name the
    ``real_models_root`` marker, and ``(module, "<elsewhere>")`` for any other
    mention of it (a module ``pytestmark``, for one)."""
    tree = ast.parse(source)
    found: set[tuple[str, str]] = set()
    in_decorators: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                marks = {
                    id(part)
                    for part in ast.walk(decorator)
                    if isinstance(part, ast.Attribute) and part.attr == "real_models_root"
                }
                if marks:
                    found.add((module, node.name))
                    in_decorators |= marks
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "real_models_root"
            and id(node) not in in_decorators
        ):
            found.add((module, "<elsewhere>"))
    return found


def test_only_the_resolvers_own_tests_opt_out() -> None:
    """Task H.6, a source scan of every test module: the opt-out never widens
    past step 2's set (a scan, not a proof: a marker applied at run time, by
    ``request.applymarker`` or a string, is unseen)."""
    found: set[tuple[str, str]] = set()
    for path in sorted(TESTS.glob("test_*.py")):
        found |= _marked_opt_outs(path.read_text(encoding="utf-8"), path.name)
    assert found == _REAL_MODELS_ROOT_MARKED


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("@pytest.mark.real_models_root\nclass TestX:\n    pass\n", "TestX"),
        ("@pytest.mark.real_models_root\ndef test_x():\n    pass\n", "test_x"),
        ("pytestmark = pytest.mark.real_models_root\n", "<elsewhere>"),
        ("pytestmark = [pytest.mark.slow, pytest.mark.real_models_root]\n", "<elsewhere>"),
    ],
)
def test_the_opt_out_scan_sees_each_form(source: str, expected: str) -> None:
    assert _marked_opt_outs(source, "x.py") == {("x.py", expected)}


_REAL_MODEL_CONSTRUCTORS = (
    "SileroVad(",
    "WhisperSpeechProvider(",
    "OnnxSpeakerEmbedder(",
    "LocalLanguageModel",
)
_CHILD_PIN = 'install_layout.models_root("dev")'


def _child_sources() -> dict[str, str]:
    tree = ast.parse((TESTS / "test_integration_no_sockets.py").read_text(encoding="utf-8"))
    found: dict[str, str] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id.endswith("_CHILD")
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            found[node.targets[0].id] = node.value.value
    return found


def test_every_real_model_child_loads_from_the_dev_root() -> None:
    """Task 2.6, class-closed over the integration module's child scripts:
    every child that constructs a real model pins its models root to the
    source run's dev root AFTER its channel pin."""
    children = _child_sources()
    real = {
        name
        for name, source in children.items()
        if any(marker in source for marker in _REAL_MODEL_CONSTRUCTORS)
    }
    assert real == {"_REAL_TRANSCRIBE_CHILD", "_REAL_PROSE_CHILD", "_STUBBED_NETWORK_CHILD"}
    for name in real:
        source = children[name]
        assert _CHILD_PIN in source, name
        assert source.index('install_layout.channel = lambda: "production"') < source.index(
            _CHILD_PIN
        ), name
    for name in set(children) - real:
        assert _CHILD_PIN not in children[name], name


# The one child that is the source run's own native host (the dev channel by
# design: the parent speaks the dev origin to it, as Chrome would to a dev host).
_DEV_HOST_CHILDREN = frozenset({"_HOST_RELAY_CHILD"})


def test_every_app_child_proves_the_production_channel() -> None:
    """Round 22 (D2): the no-sockets proof children run the app as it SHIPS,
    so each pins the production channel and a source run's ``is_frozen``,
    class-closed over the integration module's child scripts."""
    children = _child_sources()
    assert _DEV_HOST_CHILDREN <= set(children)
    for name in set(children) - _DEV_HOST_CHILDREN:
        source = children[name]
        assert 'install_layout.channel = lambda: "production"' in source, name
        assert "install_layout.is_frozen = lambda: False" in source, name
    for name in _DEV_HOST_CHILDREN:
        assert "install_layout.channel = lambda" not in children[name], name


_REAL_MODEL_PROBES = frozenset(
    {
        "models_ready",
        "vad_model_available",
        "whisper_model_available",
        "speaker_model_available",
        "language_model_file_available",
        "language_model_available",
    }
)


def _called_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _gate_offences(source: str, module: str) -> list[str]:
    """Each ``skipif`` in ``source`` whose condition refers to a
    model-presence probe — by name or as an attribute — OUTSIDE an
    ``on_real_ml_root(...)`` argument (round 13 LOW-006: every probe must
    be guarded, not merely sit beside a guarded one)."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and _called_name(node) == "skipif" and node.args):
            continue
        condition = node.args[0]
        guarded: set[int] = set()
        for inner in ast.walk(condition):
            if isinstance(inner, ast.Call) and _called_name(inner) == "on_real_ml_root":
                for arg in inner.args:
                    guarded |= {id(part) for part in ast.walk(arg)}
        for part in ast.walk(condition):
            probe = (
                part.id
                if isinstance(part, ast.Name)
                else part.attr
                if isinstance(part, ast.Attribute)
                else None
            )
            if probe in _REAL_MODEL_PROBES and id(part) not in guarded:
                found.append(f"{module}:{node.lineno} ({probe})")
    return found


def test_every_real_model_skip_gate_looks_in_the_dev_root() -> None:
    """Task 2.6, a source scan of every test module: every model-presence
    probe in a ``skipif`` condition sits inside an ``on_real_ml_root``
    argument (a scan, not a proof: an in-body ``pytest.skip`` gate is
    enumerated by hand — the two language-model legs — and a gate on a raw
    path, ``test_benchmark.py``'s, uses ``real_ml_models_root`` itself)."""
    offences: list[str] = []
    for path in sorted(TESTS.glob("test_*.py")):
        offences += _gate_offences(path.read_text(encoding="utf-8"), path.name)
    assert offences == []


@pytest.mark.parametrize(
    ("source", "flagged"),
    [
        ("pytest.mark.skipif(not models_ready(), reason='x')", True),
        ("pytest.mark.skipif(not lm.language_model_file_available(), reason='x')", True),
        # an unguarded probe beside a guarded one
        (
            "pytest.mark.skipif(not on_real_ml_root(models_ready)"
            " or not vad_model_available(), reason='x')",
            True,
        ),
        ("pytest.mark.skipif(not on_real_ml_root(models_ready), reason='x')", False),
        (
            "pytest.mark.skipif(not on_real_ml_root(lambda: lm.speaker_model_available()),"
            " reason='x')",
            False,
        ),
        ("pytest.mark.skipif(sys.platform != 'win32', reason='x')", False),
    ],
)
def test_the_gate_scan_sees_what_it_claims(source: str, flagged: bool) -> None:
    assert bool(_gate_offences(source, "x.py")) is flagged
