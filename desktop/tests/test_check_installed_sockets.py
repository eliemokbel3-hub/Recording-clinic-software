"""Installation plan Task 3.8: ``scripts/check-installed-sockets.py`` against
a FAKE process table — no real process is listed or read (C6). The real run
is the practitioner's, against the installed app (Phase P step 10)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load() -> ModuleType:
    path = REPO / "scripts" / "check-installed-sockets.py"
    name = "check_installed_sockets_under_test"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolves annotations through it
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def sockets() -> ModuleType:
    return _load()


class Gone(Exception):
    """Stands in for ``psutil.NoSuchProcess``."""


class Denied(Exception):
    """Stands in for ``psutil.AccessDenied``."""


class FakeProcess:
    def __init__(
        self,
        pid: int,
        name: str,
        connections: list[Any] | None = None,
        children: list[FakeProcess] | None = None,
        *,
        fails: type[Exception] | None = None,
    ) -> None:
        self.pid = pid
        self._name = name
        self._connections = connections or []
        self._children = children or []
        self.fails = fails
        self.kinds: list[str] = []

    def name(self) -> str:
        return self._name

    def children(self, recursive: bool = False) -> list[FakeProcess]:
        assert recursive  # the whole tree, never only direct children
        found: list[FakeProcess] = []
        for child in self._children:
            found += [child, *child.children(recursive=True)]
        return found

    def net_connections(self, kind: str = "inet") -> list[Any]:
        self.kinds.append(kind)
        if self.fails is not None:
            raise self.fails()
        return self._connections


def _conn(status: str = "ESTABLISHED", raddr: Any = ("203.0.113.5", 443)) -> Any:
    return SimpleNamespace(status=status, raddr=raddr)


def _watch(
    sockets: ModuleType, table: list[FakeProcess], seconds: float = 0.0
) -> tuple[int, list[str]]:
    lines: list[str] = []
    ticks = iter(range(100))
    code = sockets.watch(
        lambda: table,
        gone=(Gone,),
        denied=(Denied,),
        seconds=seconds,
        interval=1.0,
        clock=lambda: float(next(ticks)),
        sleep=lambda s: None,
        out=lines.append,
    )
    return code, lines


def test_no_connection_is_exit_0(sockets: ModuleType) -> None:
    worker = FakeProcess(11, "scribe-app.exe")
    app = FakeProcess(10, "scribe-app.exe", children=[worker])
    code, lines = _watch(sockets, [app, FakeProcess(20, "chrome.exe", [_conn()])])
    assert code == 0
    assert lines == ["RESULT: no connection seen"]
    assert app.kinds == ["inet"] and worker.kinds == ["inet"]


def test_a_connection_anywhere_in_the_tree_is_reported_once(sockets: ModuleType) -> None:
    grandchild = FakeProcess(12, "scribe-app.exe", [_conn()])
    child = FakeProcess(11, "python.exe", children=[grandchild])
    host = FakeProcess(30, "scribe-host.exe")
    table = [FakeProcess(10, "Scribe-App.EXE", children=[child]), host]
    code, lines = _watch(sockets, table, seconds=3.0)
    assert code == 1
    assert lines == [
        "CONNECTION scribe-app.exe pid=12 status=ESTABLISHED remote=203.0.113.5:443",
        "RESULT: 1 connection(s) seen",
    ]


def test_a_listening_socket_with_no_remote_is_still_reported(sockets: ModuleType) -> None:
    host = FakeProcess(30, "scribe-host.exe", [_conn("LISTEN", ())])
    code, lines = _watch(sockets, [host])
    assert code == 1
    assert lines[0] == "CONNECTION scribe-host.exe pid=30 status=LISTEN remote=-"


def test_no_target_is_exit_2(sockets: ModuleType) -> None:
    code, lines = _watch(sockets, [FakeProcess(20, "chrome.exe", [_conn()])])
    assert code == 2
    assert lines == ["RESULT: no scribe-app.exe or scribe-host.exe is running"]


def test_an_unreadable_process_proves_nothing(sockets: ModuleType) -> None:
    app = FakeProcess(10, "scribe-app.exe", fails=Denied)
    code, lines = _watch(sockets, [app])
    assert code == 3
    assert lines == [
        "UNREADABLE pids=10",
        "RESULT: some processes could not be read; nothing is proven",
    ]


def test_a_process_that_ends_is_gone_not_unreadable(sockets: ModuleType) -> None:
    app = FakeProcess(10, "scribe-app.exe", fails=Gone)
    code, lines = _watch(sockets, [app])
    assert code == 0
    assert lines == ["RESULT: no connection seen"]


def test_the_output_is_text_free(sockets: ModuleType) -> None:
    """Only the program name, a pid, a state and an address — the fields a
    connection line is built from — never anything else of the process."""
    line = sockets.Seen("scribe-app.exe", 1, "ESTABLISHED", "203.0.113.5:443").line()
    assert line == "CONNECTION scribe-app.exe pid=1 status=ESTABLISHED remote=203.0.113.5:443"
    assert sockets.TARGETS == ("scribe-app.exe", "scribe-host.exe")
