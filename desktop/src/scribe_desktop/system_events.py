"""Windows' suspend and session-lock notifications for the pause rule
(Cliniko workflow safeguards plan D5, as amended by the practitioner on
2026-09-28).

Qt-free. The Phase 5 smoke found that a Modern Standby machine (S0 low power
idle; S3 unavailable) never sent the app's window ``WM_POWERBROADCAST`` /
``PBT_APMSUSPEND``, so "Start -> Power -> Sleep" did not pause a recording.
The practitioner chose "sleep + screen lock":

- ``RegisterSuspendResumeNotification(hwnd, DEVICE_NOTIFY_WINDOW_HANDLE)``
  asks Windows to deliver ``PBT_APMSUSPEND`` to the main window on Modern
  Standby too (the classic broadcast is still handled; either is one pause,
  since a second finds the recording already paused);
- ``WTSRegisterSessionNotification(hwnd, NOTIFY_FOR_THIS_SESSION)`` delivers
  ``WM_WTSSESSION_CHANGE``; a ``WTS_SESSION_LOCK`` (Win+L, a lid close or
  standby with sign-in required) pauses ANY recording. Unlock resumes
  nothing: Resume stays a deliberate press through the guarded path.

LOCKED UNTIL UNLOCK (codex round 51 PR-MED-300). A Resume or "Resume
previous" click already on its way through Chrome when the lock arrives
would otherwise be handled after the lock's pause and restart the recording
behind the locked screen. So the main window sets ``SystemPauseWatch``'s
lock flag the moment the lock message is dispatched (before the queued
pause runs), every Resume path refuses by name while it is set (the
bridge's one resume check), and ``WTS_SESSION_UNLOCK`` clears it — resuming
nothing — once Windows agrees the session is not locked (round 57 SEC-020:
an unlock Windows contradicts is a forged one, and the flag stays). A MISSED
unlock must not refuse Resume forever: once the flag is
older than ``LOCK_RECHECK_AFTER_SECONDS``, a refused Resume asks Windows for
the session's real lock state (``WTSQuerySessionInformationW`` /
``WTSSessionInfoEx`` -> ``SessionFlags``) and clears the flag only when
Windows says unlocked; if Windows cannot say, the Resume stays refused and
the refusal says so (lock and sign in again to clear it). The young-flag
window keeps a query racing the lock itself from reopening the gap. There
is no suspend flag: no Windows signal says a PERSON woke the machine
(``PBT_APMRESUMEAUTOMATIC`` also fires on unattended wakes), and standby with
sign-in locks first, which the lock flag covers.

``SystemPauseWatch`` registers both for the app's main window (once) and
gives them back on close, at quit and after a failed start. Neither call
ever raises: a refusal is a status the desktop shows (the Session screen's
Chrome lines and the status line), never retried in a loop. What no code
here can prove is that Windows DELIVERS these messages on a given machine;
the live smoke is that proof.

The ``SystemEventRegistrar`` is the seam: tests pass a fake and never
register against the real session or power notifications. Nothing here
logs."""

from __future__ import annotations

import ctypes
import functools
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final, Literal, Protocol

from scribe_desktop.context_rules import is_lock_message, is_unlock_message

DEVICE_NOTIFY_WINDOW_HANDLE: Final = 0
NOTIFY_FOR_THIS_SESSION: Final = 0
# ``WTSQuerySessionInformationW`` for this process's own session.
WTS_CURRENT_SERVER_HANDLE: Final = 0
WTS_CURRENT_SESSION: Final = 0xFFFFFFFF
WTS_SESSION_INFO_EX: Final = 25  # WTS_INFO_CLASS.WTSSessionInfoEx
# ``WTSINFOEX_LEVEL1_W.SessionFlags`` (Windows 8 and later; Windows 7 had
# the two values swapped — not a supported platform here).
WTS_SESSIONSTATE_LOCK: Final = 0
WTS_SESSIONSTATE_UNLOCK: Final = 1
# A lock flag younger than this is trusted without asking Windows: a query
# racing the lock notification itself must not clear it (see the docstring).
LOCK_RECHECK_AFTER_SECONDS: Final = 5.0

WatchState = Literal["not_set_up", "on", "failed"]
LockState = Literal["unlocked", "locked", "unknown"]


class SystemEventRegistrar(Protocol):
    """The Windows calls. ``register_suspend`` returns the notification
    handle (0 when Windows refused); ``register_lock`` returns whether
    Windows accepted; ``query_locked`` returns whether this session is
    locked now (None when Windows cannot say). None raises for a refusal."""

    def register_suspend(self, hwnd: int) -> int: ...

    def unregister_suspend(self, handle: int) -> None: ...

    def register_lock(self, hwnd: int) -> bool: ...

    def unregister_lock(self, hwnd: int) -> None: ...

    def query_locked(self) -> bool | None: ...


class _WTSINFOEX_LEVEL1_W(ctypes.Structure):  # noqa: N801 - the Windows name
    _fields_ = [
        ("SessionId", ctypes.c_uint32),
        ("SessionState", ctypes.c_int32),
        ("SessionFlags", ctypes.c_int32),
        ("WinStationName", ctypes.c_wchar * 33),
        ("UserName", ctypes.c_wchar * 21),
        ("DomainName", ctypes.c_wchar * 18),
        ("LogonTime", ctypes.c_int64),
        ("ConnectTime", ctypes.c_int64),
        ("DisconnectTime", ctypes.c_int64),
        ("LastInputTime", ctypes.c_int64),
        ("CurrentTime", ctypes.c_int64),
        ("IncomingBytes", ctypes.c_uint32),
        ("OutgoingBytes", ctypes.c_uint32),
        ("IncomingFrames", ctypes.c_uint32),
        ("OutgoingFrames", ctypes.c_uint32),
        ("IncomingCompressedBytes", ctypes.c_uint32),
        ("OutgoingCompressedBytes", ctypes.c_uint32),
    ]


class _WTSINFOEX_LEVEL_W(ctypes.Union):  # noqa: N801 - the Windows name
    _fields_ = [("WTSInfoExLevel1", _WTSINFOEX_LEVEL1_W)]


class _WTSINFOEXW(ctypes.Structure):
    """``WTSINFOEXW``: ctypes lays it out as C does (the union is 8-aligned
    by its 64-bit times, so ``Data`` starts at offset 8). Only ``Level`` and
    ``SessionFlags`` are ever read; nothing here is logged or kept."""

    _fields_ = [("Level", ctypes.c_uint32), ("Data", _WTSINFOEX_LEVEL_W)]


def lock_state_from_info(info: _WTSINFOEXW, size: int) -> bool | None:
    """Whether a ``WTSSessionInfoEx`` answer says LOCKED (True), UNLOCKED
    (False), or nothing usable (None: a short buffer, another level, or
    ``WTS_SESSIONSTATE_UNKNOWN``)."""
    if size < ctypes.sizeof(_WTSINFOEXW) or info.Level != 1:
        return None
    flags = info.Data.WTSInfoExLevel1.SessionFlags
    if flags == WTS_SESSIONSTATE_LOCK:
        return True
    if flags == WTS_SESSIONSTATE_UNLOCK:
        return False
    return None


@functools.cache
def _user32() -> Any:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.RegisterSuspendResumeNotification.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    user32.RegisterSuspendResumeNotification.restype = ctypes.c_void_p
    user32.UnregisterSuspendResumeNotification.argtypes = [ctypes.c_void_p]
    user32.UnregisterSuspendResumeNotification.restype = ctypes.c_int
    return user32


@functools.cache
def _wtsapi32() -> Any:
    wtsapi32 = ctypes.WinDLL("wtsapi32", use_last_error=True)
    wtsapi32.WTSRegisterSessionNotification.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    wtsapi32.WTSRegisterSessionNotification.restype = ctypes.c_int
    wtsapi32.WTSUnRegisterSessionNotification.argtypes = [ctypes.c_void_p]
    wtsapi32.WTSUnRegisterSessionNotification.restype = ctypes.c_int
    wtsapi32.WTSQuerySessionInformationW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_uint32),
    ]
    wtsapi32.WTSQuerySessionInformationW.restype = ctypes.c_int
    wtsapi32.WTSFreeMemory.argtypes = [ctypes.c_void_p]
    wtsapi32.WTSFreeMemory.restype = None
    return wtsapi32


class Win32SystemEventRegistrar:
    """The Windows calls through ctypes, as ``hotkey`` calls user32."""

    def query_locked(self) -> bool | None:
        """This session's lock state from ``WTSSessionInfoEx`` (None when
        the call fails or the answer is unusable). Reads ``SessionFlags``
        only, and frees Windows' buffer before returning."""
        wtsapi32 = _wtsapi32()
        buffer = ctypes.c_void_p()
        size = ctypes.c_uint32()
        if not wtsapi32.WTSQuerySessionInformationW(
            WTS_CURRENT_SERVER_HANDLE,
            WTS_CURRENT_SESSION,
            WTS_SESSION_INFO_EX,
            ctypes.byref(buffer),
            ctypes.byref(size),
        ):
            return None
        address = buffer.value
        if not address:
            return None
        try:
            if size.value < ctypes.sizeof(_WTSINFOEXW):
                return None
            return lock_state_from_info(_WTSINFOEXW.from_address(address), size.value)
        finally:
            wtsapi32.WTSFreeMemory(address)

    def register_suspend(self, hwnd: int) -> int:
        handle = _user32().RegisterSuspendResumeNotification(hwnd, DEVICE_NOTIFY_WINDOW_HANDLE)
        return int(handle or 0)

    def unregister_suspend(self, handle: int) -> None:
        _user32().UnregisterSuspendResumeNotification(handle)

    def register_lock(self, hwnd: int) -> bool:
        return bool(_wtsapi32().WTSRegisterSessionNotification(hwnd, NOTIFY_FOR_THIS_SESSION))

    def unregister_lock(self, hwnd: int) -> None:
        _wtsapi32().WTSUnRegisterSessionNotification(hwnd)


@dataclass(frozen=True)
class SystemPauseStatus:
    """Whether Windows accepted each registration (the desktop shows a
    refusal)."""

    suspend: WatchState = "not_set_up"
    lock: WatchState = "not_set_up"

    @property
    def failed(self) -> tuple[str, ...]:
        """The refused registrations, ``suspend`` before ``lock``."""
        return tuple(
            key for key, state in (("suspend", self.suspend), ("lock", self.lock))
            if state == "failed"
        )


NOT_SET_UP: Final = SystemPauseStatus()


class SystemPauseWatch:
    """The main window's two registrations and the lock flag (GUI thread).
    ``register``, ``unregister`` and ``lock_state`` never raise: a failure
    is a status, and a close must never be stopped by a notification."""

    def __init__(
        self, registrar: SystemEventRegistrar, clock: Callable[[], float] | None = None
    ) -> None:
        self._registrar = registrar
        self._clock = clock if clock is not None else time.monotonic
        self._suspend_handle = 0
        self._lock_hwnd: int | None = None
        self._status: SystemPauseStatus = NOT_SET_UP
        # When the lock flag was set (None: not locked, as far as we know).
        self._locked_at: float | None = None

    @property
    def status(self) -> SystemPauseStatus:
        return self._status

    def register(self, hwnd: int) -> SystemPauseStatus:
        """Register both for ``hwnd`` (once; a second call reports the
        status it already has)."""
        if self._status != NOT_SET_UP:
            return self._status
        try:
            handle = int(self._registrar.register_suspend(hwnd))
        except Exception:  # noqa: BLE001 - a refused registration is a status
            handle = 0
        try:
            locked_in = bool(self._registrar.register_lock(hwnd))
        except Exception:  # noqa: BLE001 - a refused registration is a status
            locked_in = False
        self._suspend_handle = handle
        self._lock_hwnd = hwnd if locked_in else None
        self._status = SystemPauseStatus(
            suspend="on" if handle else "failed",
            lock="on" if locked_in else "failed",
        )
        return self._status

    def unregister(self) -> None:
        """Give both back (idempotent; on close, at quit, after a failed
        start)."""
        handle, self._suspend_handle = self._suspend_handle, 0
        hwnd, self._lock_hwnd = self._lock_hwnd, None
        self._status = NOT_SET_UP
        self._locked_at = None  # no notifications now: nothing would clear it
        if handle:
            try:
                self._registrar.unregister_suspend(handle)
            except Exception:  # noqa: BLE001, S110 - Windows frees it at exit anyway
                pass
        if hwnd is not None:
            try:
                self._registrar.unregister_lock(hwnd)
            except Exception:  # noqa: BLE001, S110 - Windows frees it at exit anyway
                pass

    def lock_matches(self, message: int, wparam: int) -> bool:
        """The session locked, and this window is registered for it."""
        return self._status.lock == "on" and is_lock_message(message, wparam)

    def unlock_matches(self, message: int, wparam: int) -> bool:
        """The session unlocked, and this window is registered for it."""
        return self._status.lock == "on" and is_unlock_message(message, wparam)

    # --- the lock flag (codex round 51 PR-MED-300) -------------------------------

    @property
    def locked(self) -> bool:
        """The session locked and no unlock has been seen since."""
        return self._locked_at is not None

    def note_lock(self) -> None:
        """The lock message was dispatched: every Resume is refused from
        now until an unlock (set before the queued pause runs)."""
        self._locked_at = self._clock()

    def note_unlock(self) -> None:
        """The unlock message: the refusal ends — unless Windows still says
        this session is LOCKED (round 57 SEC-020: a same-user process can
        post a forged unlock). The flag then stays with its lock time, so
        ``lock_state``'s re-check clears it once Windows agrees; a real unlock
        whose query raced the message heals itself at the next Resume or
        Start once the lock is ``LOCK_RECHECK_AFTER_SECONDS`` old. An
        unanswered or failed query believes the message, as before. Nothing
        resumes."""
        try:
            answer = self._registrar.query_locked()
        except Exception:  # noqa: BLE001 - an unanswered query believes the unlock
            answer = None
        if answer is True:
            return
        self._locked_at = None

    def lock_state(self) -> LockState:
        """``locked`` while the flag stands; ``unlocked`` without it. A
        flag older than ``LOCK_RECHECK_AFTER_SECONDS`` is checked against
        Windows (a missed unlock must not refuse Resume forever): cleared
        when Windows says unlocked, ``unknown`` when it cannot say."""
        locked_at = self._locked_at
        if locked_at is None:
            return "unlocked"
        if self._clock() - locked_at < LOCK_RECHECK_AFTER_SECONDS:
            return "locked"
        try:
            answer = self._registrar.query_locked()
        except Exception:  # noqa: BLE001 - an unanswered query stays refused
            answer = None
        if answer is False:
            self._locked_at = None
            return "unlocked"
        return "locked" if answer else "unknown"
