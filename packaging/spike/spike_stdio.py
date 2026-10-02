"""Installation plan Phase 0 SPIKE ONLY (Tasks 0.1 / 0.2) — throwaway.

Two jobs, both for frozen (PyInstaller, windowed bootloader) processes:

1. ``stdio_state()`` records, BEFORE anything changes them, whether
   ``sys.stdin`` / ``sys.stdout`` / ``sys.stderr`` are None and whether the
   process's Win32 standard handles are valid. This is the Task 0.1 "are the
   standard streams None under the windowed bootloader?" answer.
2. ``ensure_std_streams()`` is the minimal stdio adaptation Task 0.2 names:
   when ``sys.stdin`` / ``sys.stdout`` is None but the Win32 standard handle
   is valid (Chrome's pipes, ``subprocess`` pipes), a binary-capable text
   stream is rebuilt over ``msvcrt.open_osfhandle(GetStdHandle(...))`` so the
   UNCHANGED ``framing.set_binary_stdio`` (``sys.stdin.fileno()``) and
   ``native_host.run_host(sys.stdin.buffer, sys.stdout.buffer, ...)`` work.
   It is a no-op for a stream that is already present, so the spike entries
   call it UNCONDITIONALLY (simpler than branching on Task 0.1's answer, and
   harmless). Task 2.2 integrates and hardens the proven form.

Nothing here reads or writes clinical data; the result lines are fixed words.
"""

from __future__ import annotations

import ctypes
import io
import os
import sys
from pathlib import Path

_STD_INPUT_HANDLE = -10
_STD_OUTPUT_HANDLE = -11
_STD_ERROR_HANDLE = -12
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

_STREAMS = (
    ("stdin", _STD_INPUT_HANDLE),
    ("stdout", _STD_OUTPUT_HANDLE),
    ("stderr", _STD_ERROR_HANDLE),
)


def _get_std_handle(which: int) -> int | None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetStdHandle.argtypes = [ctypes.c_uint32]
    kernel32.GetStdHandle.restype = ctypes.c_void_p
    handle = kernel32.GetStdHandle(ctypes.c_uint32(which & 0xFFFFFFFF))
    if not handle or handle == _INVALID_HANDLE_VALUE:
        return None
    return int(handle)


def stdio_state() -> str:
    """One line, e.g. ``stdin=None(handle=valid) stdout=present(handle=valid)
    stderr=None(handle=none)``."""
    parts = []
    for name, which in _STREAMS:
        stream = getattr(sys, name)
        handle = _get_std_handle(which)
        parts.append(
            f"{name}={'None' if stream is None else 'present'}"
            f"(handle={'valid' if handle is not None else 'none'})"
        )
    return " ".join(parts)


def _rebuild(name: str, which: int, mode: str) -> str:
    if getattr(sys, name) is not None:
        return f"{name}=kept"
    handle = _get_std_handle(which)
    if handle is None:
        return f"{name}=absent"
    import msvcrt

    flags = (os.O_RDONLY if mode == "rb" else os.O_WRONLY) | os.O_BINARY
    fd = msvcrt.open_osfhandle(handle, flags)
    raw = open(fd, mode, closefd=False)  # noqa: SIM115 - lives for the process
    if mode == "rb":
        setattr(sys, name, io.TextIOWrapper(raw, encoding="utf-8"))
    else:
        setattr(sys, name, io.TextIOWrapper(raw, encoding="utf-8", write_through=True))
    return f"{name}=rebuilt"


def ensure_std_streams() -> str:
    """Rebuild a None stdin/stdout over the valid Win32 handle; returns what
    was done (``stdin=kept stdout=rebuilt`` ...). stderr is left alone: the
    app's logging already tolerates a None stderr (logging_setup)."""
    return " ".join(
        (
            _rebuild("stdin", _STD_INPUT_HANDLE, "rb"),
            _rebuild("stdout", _STD_OUTPUT_HANDLE, "wb"),
        )
    )


def append_result(path: Path, line: str) -> None:
    """Best effort: a spike result line never stops the spike."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line.rstrip("\n") + "\n")
    except OSError:
        pass
