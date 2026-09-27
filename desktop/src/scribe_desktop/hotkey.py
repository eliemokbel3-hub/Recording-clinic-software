"""The global pause hotkey (Cliniko workflow safeguards plan Task 7.1, D7).

Qt-free. ``GlobalHotkey`` reserves ONE chord for the app's main window with
Windows' ``RegisterHotKey``; Windows then posts ``WM_HOTKEY`` to that window
from anywhere in the session, and the main window's ``nativeEvent`` turns it
into a press. The press itself is the main window's: RECORDING pauses through
``pause_for`` and PAUSED asks the Session screen's guarded Resume, so the
hotkey reaches nothing a Pause or Resume button could not (Constraint 7: a
linked session still resumes only on a current report of its own note).

THE CHORD is Ctrl+Shift+F9 (``MOD_NOREPEAT``: holding it presses it once).
Ctrl+Alt is avoided because it IS AltGr on European layouts, where Ctrl+Alt+
<key> types characters; Alt+Shift switches keyboard layouts; Win+<key> belongs
to Windows. Chrome and Cliniko use no Ctrl+Shift+F9. While the app runs the
chord is reserved for the whole Windows session, so any other program's use
of it stops working — Word's "unlink field" is the known one.

A registration refused by Windows (another program already holds the chord,
error 1409) is shown, never retried in a loop: the status reads "failed" and
the desktop and Chrome's side panel say the hotkey is unavailable.

The ``HotkeyRegistrar`` is the seam: tests pass a fake and never reserve a
real chord on the host. Nothing here logs."""

from __future__ import annotations

import ctypes
import functools
from dataclasses import dataclass
from typing import Any, Final, Literal, Protocol

WM_HOTKEY: Final = 0x0312
# An application's hotkey ids are 0x0000-0xBFFF.
HOTKEY_ID: Final = 0x5C51
MOD_CONTROL: Final = 0x0002
MOD_SHIFT: Final = 0x0004
MOD_NOREPEAT: Final = 0x4000
VK_F9: Final = 0x78
MODIFIERS: Final = MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT
VIRTUAL_KEY: Final = VK_F9
CHORD_TEXT: Final = "Ctrl+Shift+F9"
ERROR_HOTKEY_ALREADY_REGISTERED: Final = 1409

HotkeyState = Literal["not_set_up", "on", "failed"]


class HotkeyRegistrar(Protocol):
    """The two Windows calls. ``register`` returns 0 when the chord was
    reserved, else the Windows error code (never raises for a refusal)."""

    def register(self, hwnd: int, hotkey_id: int, modifiers: int, virtual_key: int) -> int: ...

    def unregister(self, hwnd: int, hotkey_id: int) -> None: ...


@functools.cache
def _user32() -> Any:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.RegisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
    user32.RegisterHotKey.restype = ctypes.c_int
    user32.UnregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user32.UnregisterHotKey.restype = ctypes.c_int
    return user32


class Win32HotkeyRegistrar:
    """``RegisterHotKey`` / ``UnregisterHotKey`` through ctypes, as the
    pipe-peer lookups in ``pipe_server`` call kernel32."""

    def register(self, hwnd: int, hotkey_id: int, modifiers: int, virtual_key: int) -> int:
        user32 = _user32()
        if user32.RegisterHotKey(hwnd, hotkey_id, modifiers, virtual_key):
            return 0
        return ctypes.get_last_error() or -1

    def unregister(self, hwnd: int, hotkey_id: int) -> None:
        _user32().UnregisterHotKey(hwnd, hotkey_id)


@dataclass(frozen=True)
class HotkeyStatus:
    """What the desktop and ``state.hotkey`` show. ``error`` is the Windows
    error code of a refused registration (None otherwise)."""

    state: HotkeyState
    chord: str = CHORD_TEXT
    error: int | None = None

    @property
    def available(self) -> bool:
        return self.state == "on"


NOT_SET_UP: Final = HotkeyStatus("not_set_up")


def is_hotkey_message(message: int, wparam: int) -> bool:
    """A ``WM_HOTKEY`` for this app's id."""
    return message == WM_HOTKEY and wparam == HOTKEY_ID


class GlobalHotkey:
    """The app's one reserved chord (GUI thread). ``register`` and
    ``unregister`` never raise: a failure is a status, and a close must
    never be stopped by the hotkey."""

    def __init__(self, registrar: HotkeyRegistrar) -> None:
        self._registrar = registrar
        self._hwnd: int | None = None
        self._status: HotkeyStatus = NOT_SET_UP

    @property
    def status(self) -> HotkeyStatus:
        return self._status

    def register(self, hwnd: int) -> HotkeyStatus:
        """Reserve the chord for ``hwnd`` (once; a second call reports the
        status it already has)."""
        if self._status.state != "not_set_up":
            return self._status
        try:
            error = self._registrar.register(hwnd, HOTKEY_ID, MODIFIERS, VIRTUAL_KEY)
        except Exception:  # noqa: BLE001 - a failed reservation is a status
            error = -1
        if error == 0:
            self._hwnd = hwnd
            self._status = HotkeyStatus("on")
        else:
            self._status = HotkeyStatus("failed", error=error)
        return self._status

    def unregister(self) -> None:
        """Give the chord back (idempotent; on close)."""
        hwnd, self._hwnd = self._hwnd, None
        self._status = NOT_SET_UP
        if hwnd is None:
            return
        try:
            self._registrar.unregister(hwnd, HOTKEY_ID)
        except Exception:  # noqa: BLE001, S110 - Windows frees it at exit anyway
            pass

    def matches(self, message: int, wparam: int) -> bool:
        """This window's reserved chord was pressed."""
        return self._status.available and is_hotkey_message(message, wparam)
