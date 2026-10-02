r"""Watch the installed Clinic Scribe for network connections (installation
plan Task 3.8; Phase P step 10).

Run it from a normal PowerShell at the repository root, while the INSTALLED
app transcribes a recording and renders a writing style, so its models are
working:

    .venv\Scripts\python.exe scripts\check-installed-sockets.py --seconds 120

It walks the process tree of every ``scribe-app.exe`` and ``scribe-host.exe``
(each program and all its children - lessons: walk the tree) once a second
and reports every internet (IPv4/IPv6) connection any of them holds: the
program, its process id, the state and the remote address. It prints nothing
else - no file name, no window title, no text from the app.

Exit codes: 0 no connection seen; 1 a connection was seen; 2 no Clinic
Scribe process was found; 3 a process could not be read (run it as the same
Windows user as the app; it never needs to be elevated).

The offline contract allows ONE kind of connection: Cliniko's API, when the
app checks a note you opened or a draft write you asked for. During a
transcription and a prose render with no Cliniko page in use, expect none.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

TARGETS = ("scribe-app.exe", "scribe-host.exe")

EXIT_CLEAN = 0
EXIT_CONNECTION = 1
EXIT_NOT_RUNNING = 2
EXIT_UNREADABLE = 3

Errors = tuple[type[BaseException], ...]


class ProcessLike(Protocol):
    """The slice of ``psutil.Process`` the check uses (a fake in tests)."""

    pid: int

    def name(self) -> str: ...

    def children(self, recursive: bool = ...) -> list[Any]: ...

    def net_connections(self, kind: str = ...) -> list[Any]: ...


@dataclass(frozen=True)
class Seen:
    program: str
    pid: int
    status: str
    remote: str

    def line(self) -> str:
        return (
            f"CONNECTION {self.program} pid={self.pid} status={self.status} "
            f"remote={self.remote}"
        )


def _address(value: Any) -> str:
    if not value:
        return "-"
    return f"{value[0]}:{value[1]}"


@dataclass
class Sample:
    targets: int
    seen: list[Seen]
    unreadable: list[int]


def sample(
    processes: Callable[[], Iterable[ProcessLike]], *, gone: Errors, denied: Errors
) -> Sample:
    """One look at every target process and all its descendants. A process
    that ends during the look is simply gone; one that cannot be read is
    reported by id (nothing about it is then proven)."""
    result = Sample(0, [], [])
    tree: dict[int, ProcessLike] = {}
    for process in processes():
        try:
            if process.name().lower() not in TARGETS:
                continue
        except gone:
            continue
        except denied:
            continue  # not readable, so not knowable as ours: never a target
        result.targets += 1
        tree.setdefault(process.pid, process)
        try:
            for child in process.children(recursive=True):
                tree.setdefault(child.pid, child)
        except gone:
            continue
        except denied:
            result.unreadable.append(process.pid)
    for process in tree.values():
        try:
            name = process.name()
            for connection in process.net_connections(kind="inet"):
                result.seen.append(
                    Seen(name, process.pid, str(connection.status), _address(connection.raddr))
                )
        except gone:
            continue
        except denied:
            result.unreadable.append(process.pid)
    return result


def watch(
    processes: Callable[[], Iterable[ProcessLike]],
    *,
    gone: Errors,
    denied: Errors,
    seconds: float,
    interval: float,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    out: Callable[[str], None] = print,
) -> int:
    """Look until ``seconds`` have passed; report each distinct connection
    once, and return the exit code."""
    end = clock() + seconds
    reported: set[Seen] = set()
    found_any = False
    unreadable_any = False
    while True:
        look = sample(processes, gone=gone, denied=denied)
        found_any = found_any or look.targets > 0
        if look.unreadable:
            unreadable_any = True
            out(f"UNREADABLE pids={','.join(str(p) for p in sorted(set(look.unreadable)))}")
        for connection in look.seen:
            if connection not in reported:
                reported.add(connection)
                out(connection.line())
        if clock() >= end:
            break
        sleep(interval)
    if reported:
        out(f"RESULT: {len(reported)} connection(s) seen")
        return EXIT_CONNECTION
    if not found_any:
        out("RESULT: no scribe-app.exe or scribe-host.exe is running")
        return EXIT_NOT_RUNNING
    if unreadable_any:
        out("RESULT: some processes could not be read; nothing is proven")
        return EXIT_UNREADABLE
    out("RESULT: no connection seen")
    return EXIT_CLEAN


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--seconds", type=float, default=60.0, help="how long to watch")
    parser.add_argument("--interval", type=float, default=1.0, help="seconds between looks")
    args = parser.parse_args(argv)
    import psutil

    return watch(
        psutil.process_iter,
        gone=(psutil.NoSuchProcess,),  # ZombieProcess is one too
        denied=(psutil.AccessDenied,),
        seconds=max(args.seconds, 0.0),
        interval=max(args.interval, 0.1),
    )


if __name__ == "__main__":
    sys.exit(main())
