"""PySide6 desktop app (`scribe-app`) — Phase 2 Steps 10 + 12.

The Phase-1 status window is now the Status tab of the multi-screen
main window (microphone / session / recovery / transcript-inspection).
Startup order (binding): offline kill-switches set AND asserted before
any ML code can run; then the single-instance guard (a second instance
must never run its own controller/sweep over the shared sessions root);
then the 24-hour expiry sweep (Flow 3) before the recovery screen lists
anything; a periodic sweep keeps the cap enforced while the app stays
open.
"""

from __future__ import annotations

import ctypes
import getpass

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from scribe_desktop.audio_capture import SoundDeviceBackend
from scribe_desktop.benchmark import apply_offline_env, assert_offline_env
from scribe_desktop.logging_setup import log_event, setup_logging
from scribe_desktop.session import SessionController
from scribe_desktop.session_store import default_sessions_root, sweep_sessions
from scribe_desktop.ui.main_window import MainWindow

# PR round 18 (PR8): 15-minute cadence bounds the worst-case overshoot of
# the 24 h cap to minutes, not an hour. The startup sweep runs immediately.
_SWEEP_INTERVAL_MS = 15 * 60 * 1000

# Single-instance guard (peer round 18 PR4, priority raised after the
# 2026-07-28 live smoke: two concurrent scribe-app processes shared one
# sessions root — two controllers, two sweeps — and one showed permanently
# stale state). Windows-only, like the rest of the app.
_ERROR_ALREADY_EXISTS = 183

_ALREADY_RUNNING_TEXT = (
    "Cliniko Scribe is already running.\n\n"
    "Use the existing window — check the taskbar. If you cannot find it, "
    "end scribe-app.exe in Task Manager, then launch again."
)


def _single_instance_mutex_name() -> str:
    """Per-user mutex name; `Global\\` spans logon sessions because every
    logon session of the same user shares one %LOCALAPPDATA% sessions root."""
    try:
        user = getpass.getuser()
    except OSError:  # no username env in an exotic service context
        user = "default"
    # Backslash is the kernel object-namespace separator — sanitize.
    user = user.replace("\\", "_").replace("/", "_")
    return f"Global\\ClinikoScribe-app-{user}"


def acquire_single_instance_lock(name: str | None = None) -> tuple[bool, int]:
    """Try to claim the per-user single-instance named mutex.

    Returns ``(True, handle)`` when this process now owns the name — the OS
    handle is deliberately kept open for the process lifetime so the claim
    holds until exit — or ``(False, 0)`` when another scribe-app instance
    already holds it. Fail-open: an unexpected ``CreateMutexW`` failure
    returns ``(True, 0)`` because this is a convenience guard against
    confusing double launches, NOT a security boundary (the same-user
    attacker can always squat the name; threat model boundary 2).
    """
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    mutex_name = name if name is not None else _single_instance_mutex_name()
    handle = kernel32.CreateMutexW(None, 0, mutex_name)
    already_exists = ctypes.get_last_error() == _ERROR_ALREADY_EXISTS
    if handle and already_exists:
        # CreateMutexW handed back a handle to the OTHER instance's mutex —
        # close it so the name releases the moment that instance exits.
        kernel32.CloseHandle(handle)
        return (False, 0)
    if not handle:
        return (True, 0)
    return (True, int(handle))


def release_single_instance_lock(handle: int) -> None:
    """Close a mutex handle (used by tests; the app holds its own to exit)."""
    if not handle:
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    kernel32.CloseHandle(handle)


def _show_already_running_warning() -> None:
    box = QMessageBox(QMessageBox.Icon.Warning, "Cliniko Scribe", _ALREADY_RUNNING_TEXT)
    box.exec()


def main() -> int:
    logger = setup_logging("scribe-app")
    # Offline kill-switches: set AND asserted before any ML code can run
    # (plan Design Decision "Runtime offline enforcement").
    apply_offline_env()
    assert_offline_env()
    log_event(logger, "app_start", state="starting")

    app = QApplication([])
    # The guard runs BEFORE any controller or sweep exists: a refused second
    # instance must never touch the shared sessions root.
    acquired, _mutex_handle = acquire_single_instance_lock()
    if not acquired:
        _show_already_running_warning()
        log_event(logger, "app_exit", state="already_running")
        return 0
    backend = SoundDeviceBackend()
    controller = SessionController(backend, logger=logger)
    sessions_root = default_sessions_root()

    def run_sweep(extra_protected: frozenset[str] = frozenset()) -> None:
        # Skips live sessions by STATE via active_session_ids (never mtime).
        sweep_sessions(
            sessions_root,
            active_session_ids=controller.active_session_ids() | extra_protected,
            logger=logger,
        )

    run_sweep()  # Flow 3: app start -> sweep BEFORE the recovery list renders
    window = MainWindow(controller, backend, sessions_root=sessions_root)

    sweep_timer = QTimer(window)
    sweep_timer.setInterval(_SWEEP_INTERVAL_MS)

    def periodic_sweep() -> None:
        # PR round 18 (PR2): a resume-processing run and a recovered session
        # awaiting Complete/Discard are protected from the sweep too — the
        # sweep must never destroy a store mid-recovery.
        run_sweep(window.recovery_screen.protected_session_ids())
        window.recovery_screen.refresh()

    sweep_timer.timeout.connect(periodic_sweep)
    sweep_timer.start()

    window.show()
    code = app.exec()
    log_event(logger, "app_exit", state="closed")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
