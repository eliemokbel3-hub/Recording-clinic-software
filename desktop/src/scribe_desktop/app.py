"""PySide6 desktop app (`scribe-app`) — Phase 2 Steps 10 + 12.

The Phase-1 status window is now the Status tab of the multi-screen
main window (microphone / session / recovery / transcript-inspection).
Startup order (binding): offline kill-switches set AND asserted before
any ML code can run; then the single-instance guard — the per-user lock
file every instance must hold, behind the named mutex's friendly "already
running" check (a second instance must never run its own controller/sweep
over the shared sessions root);
then the 24-hour expiry sweep (Flow 3) before the recovery screen lists
anything; a periodic sweep re-runs the expiry rule on a best-effort
cadence while the app stays open (round 47 PR-LOW-001 — "keeps the cap
enforced" overstated it: see ``_SWEEP_INTERVAL_MS``). Last, the Chrome link
(Cliniko workflow safeguards plan Tasks 4.2 + 4.5): the named pipe the
native host connects to, behind the single-instance guard.
"""

from __future__ import annotations

import ctypes
import getpass
import logging
import os
import sys
import time
from pathlib import Path
from typing import NamedTuple

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from scribe_desktop.audio_capture import SoundDeviceBackend
from scribe_desktop.benchmark import apply_offline_env, assert_offline_env
from scribe_desktop.logging_setup import log_event, setup_logging
from scribe_desktop.pipe_server import PipeServer, PipeUnavailable, current_user_sid
from scribe_desktop.session import SessionController
from scribe_desktop.session_store import default_sessions_root, sweep_sessions
from scribe_desktop.ui.main_window import MainWindow

if sys.platform == "win32":
    import pywintypes
    import win32security

# PR round 18 (PR8): the sweep CADENCE, not a bound. Round 45 LOW-001 (the
# code-side sibling of the rounds 42-43 docs sweep): this comment used to
# claim 15 minutes "bounds the worst-case overshoot of the 24 h cap to
# minutes". It does not. This is a best-effort GUI-thread ``QTimer`` tick —
# a blocked GUI thread, a suspended/hibernated machine, or an I/O error
# inside the sweep can each delay a successful expiry past the interval, and
# a PROTECTED store (live, queued-under-review, or checked out for recovery)
# is exempt entirely. What holds is: an unprotected store becomes
# expiry-ELIGIBLE at 24 h and is destroyed by the next SUCCESSFUL sweep —
# the wording `docs/security/retention-schedule.md` now carries. The startup
# sweep runs immediately.
_SWEEP_INTERVAL_MS = 15 * 60 * 1000

# Single-instance guard (peer round 18 PR4, priority raised after the
# 2026-07-28 live smoke: two concurrent scribe-app processes shared one
# sessions root — two controllers, two sweeps — and one showed permanently
# stale state). Windows-only, like the rest of the app.
_ERROR_ALREADY_EXISTS = 183

_ALREADY_RUNNING_TEXT = (
    "Clinic Scribe is already running.\n\n"
    "Use the existing window — check the taskbar. If you cannot find it, "
    "end scribe-app.exe in Task Manager, then launch again."
)

_CANNOT_START_TEXT = (
    "Clinic Scribe could not start.\n\n"
    "It could not make sure that only one copy of it is open on this Windows "
    "account, so it did not open. Restart the computer, then launch it again."
)

# Rounds 69-70 (PR-MED-370, PR-MED-380): the per-user lock file, the ONE
# exclusion every admitted instance holds, whatever the named mutex does.
# Opened with NO sharing and kept open for the process lifetime.
_INSTANCE_LOCK_FILENAME = "app.lock"
_ERROR_SHARING_VIOLATION = 32
_GENERIC_READ = 0x80000000
_GENERIC_WRITE = 0x40000000
_OPEN_ALWAYS = 4
_FILE_ATTRIBUTE_NORMAL = 0x80
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
# A virus scanner or indexer may hold the file for a moment: a busy open is
# retried briefly before it is read as another running instance.
_LOCK_FILE_TRIES = 5
_LOCK_FILE_RETRY_S = 0.1


def _single_instance_mutex_name() -> str:
    """Per-user mutex name; `Global\\` spans logon sessions because every
    logon session of the same user shares one %LOCALAPPDATA% sessions root."""
    try:
        user = getpass.getuser()
    except (OSError, KeyError, ImportError):
        # No username env in an exotic service context. Python raises
        # OSError uniformly only since 3.13; on 3.12 (supported) the
        # no-env path raises ImportError (no `pwd` on Windows) or
        # KeyError instead — all must fail open (round 42 LOW-003).
        user = "default"
    # Backslash is the kernel object-namespace separator — sanitize.
    user = user.replace("\\", "_").replace("/", "_")
    return f"Global\\ClinikoScribe-app-{user}"


class _SecurityAttributes(ctypes.Structure):
    """``SECURITY_ATTRIBUTES`` for ``CreateMutexW``."""

    _fields_ = [
        ("nLength", ctypes.c_uint32),
        ("lpSecurityDescriptor", ctypes.c_void_p),
        ("bInheritHandle", ctypes.c_int),
    ]


def _current_sid() -> str | None:
    try:
        return current_user_sid()
    except PipeUnavailable:
        return None


def _user_only_descriptor(sid: str) -> ctypes.c_void_p | None:
    """A self-relative descriptor, ``O:<sid>D:P(A;;GA;;;<sid>)``: this user
    owns the mutex (an elevated start too) and only this user may open it.
    None when Windows refuses it (the caller then creates as before). The
    caller frees it with ``LocalFree``."""
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    convert = advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW
    convert.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
    ]
    convert.restype = ctypes.c_int
    descriptor = ctypes.c_void_p()
    if not convert(f"O:{sid}D:P(A;;GA;;;{sid})", 1, ctypes.byref(descriptor), None):
        return None
    return descriptor


def _mutex_owner_sid(handle: int) -> str | None:
    """The owner SID of the mutex ``handle``; None when it cannot be read."""
    try:
        descriptor = win32security.GetSecurityInfo(
            handle, win32security.SE_KERNEL_OBJECT, win32security.OWNER_SECURITY_INFORMATION
        )
        owner = descriptor.GetSecurityDescriptorOwner()
        if owner is None:
            return None
        return str(win32security.ConvertSidToStringSid(owner))
    except (pywintypes.error, TypeError, ValueError):
        return None


def acquire_single_instance_lock(name: str | None = None) -> tuple[bool, int]:
    """Try to claim the per-user single-instance named mutex.

    Returns ``(True, handle)`` when this process now owns the name — the OS
    handle is deliberately kept open for the process lifetime so the claim
    holds until exit — or ``(False, 0)`` when another scribe-app instance
    already holds it. An unexpected ``CreateMutexW`` failure returns
    ``(True, 0)``: the mutex is only the friendly check in front of the lock
    file (see below), NOT a security boundary (the same-user attacker can
    always squat the name; threat model boundary 2).

    Round 57 SEC-015: the mutex is created OWNED by this user with a
    user-only DACL, and an existing mutex whose owner is ANOTHER account (a
    squat by another standard user of this machine) does not stop the app.
    When the user's SID cannot be read the guard works as before, without the
    owner check.

    Rounds 69-70: ``(True, 0)`` means "not held and not refused" (a foreign
    owner, or ``CreateMutexW`` failed). Nothing here admits an instance on its
    own: ``acquire_instance_exclusion`` requires the per-user lock file in
    every case.
    """
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    mutex_name = name if name is not None else _single_instance_mutex_name()
    sid = _current_sid()
    descriptor = _user_only_descriptor(sid) if sid is not None else None
    try:
        attributes: _SecurityAttributes | None = None
        if descriptor is not None:
            attributes = _SecurityAttributes(
                ctypes.sizeof(_SecurityAttributes), descriptor.value, 0
            )
        handle = kernel32.CreateMutexW(
            ctypes.addressof(attributes) if attributes is not None else None, 0, mutex_name
        )
        already_exists = ctypes.get_last_error() == _ERROR_ALREADY_EXISTS
    finally:
        if descriptor is not None:
            kernel32.LocalFree(descriptor)
    if handle and already_exists:
        # CreateMutexW handed back a handle to the existing mutex — read who
        # owns it, then close it so the name releases the moment its holder
        # exits.
        owner = _mutex_owner_sid(handle) if sid is not None else None
        kernel32.CloseHandle(handle)
        if sid is not None and owner is not None and owner != sid:
            return (True, 0)  # another account's mutex: not our instance
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


def default_instance_lock_path() -> Path:
    """``%LOCALAPPDATA%\\ClinikoScribe\\app.lock``: inside this user's
    profile, which another standard account can neither open nor create in.
    The file is empty; it is only ever held open."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "ClinikoScribe" / _INSTANCE_LOCK_FILENAME


def _hold_lock_file(path: Path) -> tuple[str, int]:
    """Open ``path`` with no sharing and keep it open.

    ``("held", handle)``; ``("busy", 0)`` while another process has it open
    (after a short retry); ``("failed", 0)`` for any other failure. The
    handle is not inheritable."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return ("failed", 0)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel32.CreateFileW
    create.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    create.restype = ctypes.c_void_p
    for attempt in range(_LOCK_FILE_TRIES):
        handle = create(
            str(path),
            _GENERIC_READ | _GENERIC_WRITE,
            0,  # no sharing: a second open fails while this one lives
            None,
            _OPEN_ALWAYS,
            _FILE_ATTRIBUTE_NORMAL,
            None,
        )
        error = ctypes.get_last_error()
        if handle is not None and handle != _INVALID_HANDLE_VALUE:
            return ("held", int(handle))
        if error != _ERROR_SHARING_VIOLATION:
            return ("failed", 0)
        if attempt + 1 < _LOCK_FILE_TRIES:
            time.sleep(_LOCK_FILE_RETRY_S)
    return ("busy", 0)


class InstanceExclusion(NamedTuple):
    """``state`` is ``acquired``, ``already_running`` or ``unavailable``;
    ``handles`` are kept open for the process lifetime."""

    state: str
    handles: tuple[int, ...] = ()


def acquire_instance_exclusion(
    name: str | None = None, lock_path: Path | None = None
) -> InstanceExclusion:
    """Rounds 69-70 (PR-MED-370, PR-MED-380): the single-instance rule in
    EVERY case, through ONE exclusion every admitted instance shares.

    The per-user lock file is REQUIRED: no instance starts without holding
    it. The named mutex is only the fast, friendly check in front of it —
    it refuses a normal second launch exactly as before, but admits nothing
    on its own (two instances holding DIFFERENT exclusions could otherwise
    overlap: round 70), and a foreign-owned or failed mutex neither admits
    nor refuses by itself:

    - mutex refused (our instance holds it) -> ``already_running``;
    - lock file held -> ``acquired`` (the mutex kept too when it was
      created, so an older build still sees the name);
    - lock file busy -> ``already_running``;
    - lock file failed for any other reason -> ``unavailable``.

    Whenever the result is not ``acquired``, a mutex just created is closed
    again, so the name is not pinned.
    """
    acquired, mutex = acquire_single_instance_lock(name)
    if not acquired:
        return InstanceExclusion("already_running")
    state, lock_file = _hold_lock_file(
        lock_path if lock_path is not None else default_instance_lock_path()
    )
    if state == "held":
        return InstanceExclusion("acquired", tuple(h for h in (mutex, lock_file) if h))
    release_single_instance_lock(mutex)
    if state == "busy":
        return InstanceExclusion("already_running")
    return InstanceExclusion("unavailable")


def release_instance_exclusion(exclusion: InstanceExclusion) -> None:
    """Close every handle (used by tests; the app holds its own to exit)."""
    for handle in exclusion.handles:
        release_single_instance_lock(handle)


def _show_already_running_warning() -> None:
    box = QMessageBox(QMessageBox.Icon.Warning, "Clinic Scribe", _ALREADY_RUNNING_TEXT)
    box.exec()


def _show_cannot_start_warning() -> None:
    box = QMessageBox(QMessageBox.Icon.Warning, "Clinic Scribe", _CANNOT_START_TEXT)
    box.exec()


def sweep_protected_ids(
    controller: SessionController, extra: frozenset[str] = frozenset()
) -> frozenset[str]:
    """Session ids the expiry sweep must skip.

    ONE atomic controller snapshot (round 31 PR-MED-001) of every
    custody-protected id — state-active sessions (the binding Critical
    Constraint), the controller's own session in ANY non-terminal state
    (round 42 MED-001: a queued transcript open for review must not lose
    its key at the 24 h boundary mid-review; PR-round-18 PR2 gave
    recovered checkouts the same courtesy via ``extra``), and every
    in-flight Discard reservation target (round 30: the admitted
    concurrent start() can retire the discarding session from the live
    pointer mid-window) — taken under a SINGLE controller-lock
    acquisition. Round 31's lesson: composing those ids from SEPARATE
    controller reads was itself a race — a Discard-reserve plus admitted
    Start between the reads yielded a set omitting the still-reserved
    target, re-opening exactly the exposure round 30 closed. Ids come
    from the snapshot; the filesystem sweep runs after, with no
    controller lock held.
    """
    return controller.custody_protected_ids() | extra


def _start_chrome_link(window: MainWindow, logger: logging.Logger) -> PipeServer | None:
    """Cliniko workflow safeguards plan Tasks 4.2 + 4.5: the named pipe the
    native host connects to, and the bridge behind it. Created AFTER the
    single-instance guard, so a refused second instance never touches the
    pipe name. A held name is refused, never shared (``PipeUnavailable``):
    the Session screen says so and desktop recording still works. A named
    pipe opens no socket; nothing here contacts Cliniko."""
    bridge = window.attach_chrome_link()
    try:
        server = PipeServer.for_current_user(bridge, logger=logger)
        bridge.attach(server)  # before start: the first client finds a sender
        server.start()
    except PipeUnavailable as exc:
        bridge.set_unavailable()
        log_event(logger, "pipe_server", state=exc.reason)
        return None
    log_event(logger, "pipe_server", state="listening")
    return server


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
    # The handles stay open until the process exits (rounds 69-70: the
    # per-user lock file always, and the mutex when this launch created it).
    exclusion = acquire_instance_exclusion()
    if exclusion.state == "already_running":
        _show_already_running_warning()
        log_event(logger, "app_exit", state="already_running")
        return 0
    if exclusion.state != "acquired":
        _show_cannot_start_warning()
        log_event(logger, "app_exit", state="no_single_instance")
        return 1
    backend = SoundDeviceBackend()
    controller = SessionController(backend, logger=logger)
    sessions_root = default_sessions_root()

    def run_sweep(extra_protected: frozenset[str] = frozenset()) -> None:
        # Skips live sessions by STATE (never mtime), plus the controller's
        # own non-terminal session (round 42 MED-001 — see
        # sweep_protected_ids).
        sweep_sessions(
            sessions_root,
            active_session_ids=sweep_protected_ids(controller, extra_protected),
            logger=logger,
        )

    run_sweep()  # Flow 3: app start -> sweep BEFORE the recovery list renders
    window = MainWindow(controller, backend, sessions_root=sessions_root)
    # Task 5.5 (D6): after the sweep, the reminder index is rebuilt from the
    # sessions left on disk — the one start-up decrypt of `encounter.enc`,
    # once per Unreviewed session. Nothing contacts Cliniko here.
    window.reconstruct_reminders()
    pipe = _start_chrome_link(window, logger)
    if pipe is not None:
        app.aboutToQuit.connect(pipe.stop)
    # Task 7.1 (D7): the pause hotkey, reserved for this window after the
    # single-instance guard; a refusal is shown, never fatal. Given back on
    # close, again at quit, and — if start-up fails after this point — by
    # the ``finally`` (round 42 PR-LOW-240); detach is idempotent.
    hotkey = window.attach_hotkey()
    try:
        log_event(logger, "hotkey", state=hotkey.state)
        app.aboutToQuit.connect(window.detach_hotkey)
        # D5 as amended 2026-09-28 (the practitioner's decision after the
        # Phase 5 smoke on a Modern Standby machine): Windows' suspend and
        # session-lock notifications for this window. A refusal is shown and
        # logged, never fatal; given back like the hotkey (close, quit, and
        # the ``finally`` below if start-up fails after this point).
        system_pause = window.attach_system_pause()
        log_event(logger, "suspend_notification", state=system_pause.suspend)
        log_event(logger, "lock_notification", state=system_pause.lock)
        app.aboutToQuit.connect(window.detach_system_pause)

        sweep_timer = QTimer(window)
        sweep_timer.setInterval(_SWEEP_INTERVAL_MS)

        def periodic_sweep() -> None:
            # PR round 18 (PR2): a resume-processing run and a recovered
            # session awaiting Complete/Discard are protected from the sweep
            # too — the sweep must never destroy a store mid-recovery.
            run_sweep(window.recovery_screen.protected_session_ids())
            window.prune_reminders()  # D6: an expired session's reminder goes too
            window.recovery_screen.refresh()

        sweep_timer.timeout.connect(periodic_sweep)
        sweep_timer.start()

        window.show()
        code = app.exec()
    finally:
        window.detach_hotkey()
        window.detach_system_pause()
    log_event(logger, "app_exit", state="closed")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
