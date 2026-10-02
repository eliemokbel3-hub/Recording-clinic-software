"""Installation plan Task 0.2 SPIKE entry for the frozen ``scribe-host.exe`` — throwaway.

Chrome starts this exe with its stdin/stdout pipes. Before the REAL, unchanged
``scribe_desktop.native_host.main`` runs, the stdio adaptation from
``spike_stdio.py`` is applied UNCONDITIONALLY: it rebuilds ``sys.stdin`` /
``sys.stdout`` over the Win32 standard handles only when the windowed
bootloader left them None, and is a no-op otherwise — so this one build works
whatever Task 0.1 found, and the result line says which case happened.

Unlike the app spike there is no isolation guard: the host runs under
Chrome's environment and writes only what today's host writes (its
content-free log in the real ``%LOCALAPPDATA%\\ClinikoScribe\\logs``), plus one
fixed-word stdio line in ``%TEMP%\\scribe-spike-host-stdio.txt``.
"""

from __future__ import annotations

import os
from pathlib import Path

from spike_stdio import append_result, ensure_std_streams, stdio_state


def _main() -> int:
    before = stdio_state()  # first, before anything can change the streams
    adapted = ensure_std_streams()
    temp = os.environ.get("TEMP") or os.environ.get("TMP")
    if temp:
        append_result(
            Path(temp) / "scribe-spike-host-stdio.txt",
            f"host before: {before} | adapt: {adapted}",
        )
    from scribe_desktop.native_host import main

    return main()


if __name__ == "__main__":
    raise SystemExit(_main())
