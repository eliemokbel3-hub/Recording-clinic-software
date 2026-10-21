"""The app process's Windows taskbar identity (UI refresh Task S.7).

Without an explicit AppUserModelID Windows groups the app's taskbar button
under the program that launched it — ``python.exe`` for the developer build,
the bare executable for the installed one — so the button shows that
program's icon while the title bar shows the app mark. ``app.main()`` calls
``declare_taskbar_identity`` with the channel's id
(``identity.app_user_model_id``) before the ``QApplication`` exists, so before
any window; the installer's Start-menu shortcut carries the same production
id, so a pinned button and the running window are one.

``set_process_app_id`` is the seam: the one place the Windows API is called.
The test suite replaces it for every test (``conftest``), so no test calls
Windows. A refusal never stops the app — only the taskbar grouping is lost —
so ``declare_taskbar_identity`` never raises and logs nothing.
"""

from __future__ import annotations

import ctypes
from collections.abc import Callable

# Windows' success code for the call (an HRESULT).
_S_OK = 0


def _win32_set_process_app_id(app_id: str) -> None:
    """``SetCurrentProcessExplicitAppUserModelID``; raises ``OSError`` when
    Windows refuses it."""
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    function = shell32.SetCurrentProcessExplicitAppUserModelID
    function.argtypes = [ctypes.c_wchar_p]
    function.restype = ctypes.c_long
    result = function(app_id)
    if result != _S_OK:
        raise OSError("the taskbar identity was refused")


# The seam (C6-style): the conftest replaces it in every test.
set_process_app_id: Callable[[str], None] = _win32_set_process_app_id


def declare_taskbar_identity(app_id: str) -> bool:
    """Declare ``app_id`` as this process's taskbar identity through the
    seam: True when declared, False when Windows refused it or there is no
    Windows API here (never raises)."""
    try:
        set_process_app_id(app_id)
    except Exception:  # noqa: BLE001 - a lost taskbar grouping never stops the app
        return False
    return True


__all__ = ["declare_taskbar_identity", "set_process_app_id"]
