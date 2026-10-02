"""Installation plan Task 0.1 SPIKE entry for the frozen ``scribe-app.exe`` — throwaway.

Dispatch, in this order, BEFORE any Qt or app code runs:

- ISOLATION GUARD (every mode). The spike runs only against a scratch
  profile: ``LOCALAPPDATA`` must be set and must NOT be (or be inside) this
  Windows user's real Local AppData known folder, read through the Shell
  (``SHGetKnownFolderPath``), which ignores the environment. Otherwise a
  message box says so and the process exits 3 having touched nothing. A
  double-click from Explorer is therefore refused by construction.
- ``-m scribe_desktop.benchmark ...``: the whisper benchmark worker. Today's
  ``benchmark.run_all`` spawns ``[sys.executable, "-m",
  "scribe_desktop.benchmark", "--single", ...]``; frozen, ``sys.executable`` is
  this exe, so without this branch the Microphone tab's benchmark would start
  a second app (D11's ``--benchmark-worker`` entry is the planned fix; this
  prototypes it). The stdio adaptation is applied first: the parent reads the
  worker's JSON from its stdout pipe.
- ``--spike-checks``: the non-GUI checks of Task 0.1 (``spike_checks.py``).
- ``--spike-stdio-echo`` / ``--spike-stdio-echo-raw``: a child the checks
  spawn with stdin/stdout pipes (as Chrome and ``subprocess`` do) — with and
  without the adaptation — to answer the stdio question without Chrome.
- anything else: the real ``scribe_desktop.app.main``.

Result lines go to ``%LOCALAPPDATA%\\spike-results\\`` — the SCRATCH folder.
``stdio.txt`` holds fixed words only; ``checks.txt`` holds fixed words and
numbers plus, for a FAILED check, the exception's type and message, which can
include file paths or library diagnostics. No clinical data exists in a
scratch profile.
"""

from __future__ import annotations

import ctypes
import os
import sys
import uuid
from pathlib import Path

from spike_stdio import append_result, ensure_std_streams, stdio_state

_FOLDERID_LOCAL_APP_DATA = "{F1B32785-6FBA-4FCF-9D55-7B8E7F157091}"


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _real_local_app_data() -> str | None:
    guid = _GUID.from_buffer_copy(uuid.UUID(_FOLDERID_LOCAL_APP_DATA).bytes_le)
    shell32 = ctypes.WinDLL("shell32")
    ole32 = ctypes.WinDLL("ole32")
    shell32.SHGetKnownFolderPath.argtypes = [
        ctypes.POINTER(_GUID),
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_wchar_p),
    ]
    shell32.SHGetKnownFolderPath.restype = ctypes.c_long
    ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    out = ctypes.c_wchar_p()
    if shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out)) != 0:
        return None
    try:
        return out.value
    finally:
        ole32.CoTaskMemFree(ctypes.cast(out, ctypes.c_void_p))


def _norm(path: str) -> str:
    return os.path.normcase(os.path.realpath(path)).rstrip("\\")


def _isolation_problem() -> str | None:
    scratch = os.environ.get("LOCALAPPDATA")
    if not scratch:
        return "LOCALAPPDATA is not set."
    real = _real_local_app_data()
    if real is None:
        return "Windows did not say where your real Local AppData folder is."
    s, r = _norm(scratch), _norm(real)
    if s == r or s.startswith(r + "\\"):
        return "LOCALAPPDATA points at your REAL Local AppData folder."
    return None


def _refuse(problem: str) -> int:
    text = (
        "This is the installation SPIKE build, not Clinic Scribe.\n\n"
        f"{problem}\n\n"
        "It only runs from a PowerShell window where LOCALAPPDATA was set to the "
        "scratch folder first (packaging/spike/RUNBOOK.md, Task 0.1). Nothing was "
        "opened or changed."
    )
    ctypes.WinDLL("user32").MessageBoxW(None, text, "Clinic Scribe spike", 0x10)
    return 3


def _results_dir() -> Path:
    return Path(os.environ["LOCALAPPDATA"]) / "spike-results"


def _stdio_echo(*, adapt: bool) -> int:
    name = "echo-child-adapted" if adapt else "echo-child-raw"
    append_result(_results_dir() / "stdio.txt", f"{name} before: {stdio_state()}")
    if adapt:
        append_result(_results_dir() / "stdio.txt", f"{name} adapt: {ensure_std_streams()}")
    if sys.stdin is None or sys.stdout is None:
        return 5
    data = sys.stdin.buffer.read(4)
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()
    return 0


def _main() -> int:
    before = stdio_state()  # first, before anything can change the streams
    problem = _isolation_problem()
    if problem is not None:
        return _refuse(problem)
    argv = sys.argv[1:]
    results = _results_dir()
    if argv[:2] == ["-m", "scribe_desktop.benchmark"]:
        append_result(results / "stdio.txt", f"benchmark-worker before: {before}")
        append_result(results / "stdio.txt", f"benchmark-worker adapt: {ensure_std_streams()}")
        from scribe_desktop import benchmark

        return benchmark.main(argv[2:])
    if argv[:1] == ["--spike-stdio-echo"]:
        return _stdio_echo(adapt=True)
    if argv[:1] == ["--spike-stdio-echo-raw"]:
        return _stdio_echo(adapt=False)
    if argv[:1] == ["--spike-checks"]:
        from spike_checks import run_checks

        return run_checks(results, before)
    append_result(results / "stdio.txt", f"gui-launch before: {before}")
    from scribe_desktop.app import main

    return main()


if __name__ == "__main__":
    raise SystemExit(_main())
