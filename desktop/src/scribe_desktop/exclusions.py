r"""Exclusions and crash hygiene (privacy-professional-controls Task 4.1, D10,
Flow 6).

At start-up, before the window is built, ``app.main`` runs
``startup_exclusions``:

- ``mark_not_indexed`` sets ``FILE_ATTRIBUTE_NOT_CONTENT_INDEXED`` on the app's
  data folder (``%LOCALAPPDATA%\ClinikoScribe``; ``ClinikoScribe-dev`` from a
  source checkout — ``install_layout``) and every folder beneath it,
  BEST EFFORT. Only folders are marked: a file created afterwards in a marked
  folder takes the attribute from it, while a file written before its folder
  was first marked keeps the attribute it had until it is rewritten (a named
  residue). Links and junctions are never followed or marked. A failure is
  one warning line at most, never a start-up refusal.
- ``check_location`` and ``check_wer`` are READ-ONLY and never refuse start-up;
  each returns warning lines. The location check resolves the data folder
  (``realpath``) and warns when it is inside OneDrive, on a network drive (a
  ``\\`` path or a remote drive letter) or in the roaming part of the profile;
  a folder outside ``%USERPROFILE%\AppData\Local`` for any other reason is
  logged (content-free), not shown. The WER check reads the channel's
  ``ExcludedApplications`` values — from a source checkout the three per-user
  ones ``scripts/register-native-host.py`` writes; in the installed build its
  two executables, HKLM then HKCU (installation plan D10) — and checks the
  RUNNING interpreter's file name against them (D10, round 2 PR-MED-006): the
  console launch runs ``python.exe``, which is not excluded.
- ``check_backup_exclusions`` (installation plan D6, Task 2.4), production
  only, READ-ONLY and never refusing: the installer's two HKLM backup and
  snapshot values must name the live sessions and logs.

``install_exception_hooks`` replaces ``sys.excepthook``,
``threading.excepthook`` and ``sys.unraisablehook`` with hooks that log ONLY
``error_code=<the exception type's name>`` (C3): no message, no traceback, no
``exc_info``, no frame locals; the main hook also drops the interpreter's
``sys.last_*`` references, so an uncaught exception's frames are not kept
alive after it. A handler that fails while writing the line reports only the
failure's type (``logging_setup.QuietHandlerErrors``), never the exception
being handled. The hooks they replace are NOT called — the
default ones print the message and traceback to stderr, which is exactly what
must not happen. Each hook keeps the one it replaced (``previous``) so the
returned restore function (and the test sentinel) can put it back; a hook
never raises.

Everything Windows goes through a ``WindowsLayer``: ``Win32WindowsLayer`` in
the app, a fake in every test (C6 — a test never touches the real registry,
WER, ``%LOCALAPPDATA%`` or file attributes; the conftest sentinel makes the
real layer raise in tests). Nothing here opens a socket (C8).
"""

from __future__ import annotations

import ctypes
import functools
import logging
import ntpath
import os
import re
import sys
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Literal, Protocol

from scribe_desktop import install_layout
from scribe_desktop.logging_setup import exception_type_name, log_event

# --- WER (D10) ----------------------------------------------------------------

# Per user (HKCU), DWORD 1 each — what ``WerAddExcludedApplication(..., FALSE)``
# writes. ``pythonw.exe`` because the venv launchers start the BASE
# ``pythonw.exe`` as a child (docs/lessons.md); the breadth (every pythonw
# process of this user) is the agreed residue. The same key path holds the
# machine-wide values under HKLM (installation plan D10).
WER_EXCLUDED_KEY: Final = r"Software\Microsoft\Windows\Windows Error Reporting\ExcludedApplications"
# Installation plan D10 (Task 2.4): the production channel — the installed
# build — runs only its two executables, and the installer excludes them in
# HKLM (a per-user value is accepted too). The dev channel excludes those two
# plus ``pythonw.exe``, per user (H.3 SIMP-003: the two are named once).
WER_PRODUCTION_APPLICATIONS: Final[tuple[str, ...]] = ("scribe-app.exe", "scribe-host.exe")
WER_EXCLUDED_APPLICATIONS: Final[tuple[str, ...]] = (
    "pythonw.exe",
    *WER_PRODUCTION_APPLICATIONS,
)
WER_EXCLUDED_VALUE: Final = 1

Hive = Literal["HKCU", "HKLM"]


def wer_applications(of: install_layout.Channel | None = None) -> tuple[str, ...]:
    """The executables whose crash reports must be excluded for ``of``
    (default: this process's channel) — D10."""
    which = of if of is not None else install_layout.channel()
    return WER_PRODUCTION_APPLICATIONS if which == "production" else WER_EXCLUDED_APPLICATIONS


def wer_hives(of: install_layout.Channel | None = None) -> tuple[Hive, ...]:
    """Where ``check_wer`` reads the values for ``of`` (D10): HKLM then HKCU
    in production, HKCU only in dev."""
    which = of if of is not None else install_layout.channel()
    return ("HKLM", "HKCU") if which == "production" else ("HKCU",)


# --- backup and snapshot exclusions (D6, Task 2.4) -----------------------------

# Under HKLM; each subkey holds one REG_MULTI_SZ value named
# ``install_layout.BACKUP_VALUE_NAME`` that the installer writes (Task 3.4)
# with ``install_layout.backup_exclusion_patterns()``.
BACKUP_RESTORE_KEY: Final = r"SYSTEM\CurrentControlSet\Control\BackupRestore"
BACKUP_EXCLUSION_KEYS: Final[tuple[str, ...]] = ("FilesNotToBackup", "FilesNotToSnapshot")

# --- the Chrome link's registry entries (D9, Task 2.3) --------------------------

# Chrome's lookup order for a native host's registry entry: the per-user hive
# before the machine one (Task 0.2 confirmed HKCU shadows HKLM on this
# computer), and in each the 32-bit registry view before the 64-bit one (as
# Chromium's ``GetManifestPathFromRegistry`` reads them — from its source,
# not observed here). A view whose key or default value cannot be read is
# passed over, as Chrome passes over it.
CHROME_LOOKUP_ORDER: Final[tuple[tuple[Hive, str], ...]] = (
    ("HKCU", "32"),
    ("HKCU", "64"),
    ("HKLM", "32"),
    ("HKLM", "64"),
)


@dataclass(frozen=True)
class HostEntry:
    """One registry entry for the native host's name: where it was found
    and the manifest path it names. Never shown on screen (a path); logged
    by the host as a hijack tripwire."""

    hive: Hive
    view: str
    manifest: str

    @property
    def place(self) -> str:
        """A content-free code for the log: ``hkcu_32`` ... ``hklm_64``."""
        return f"{self.hive.lower()}_{self.view}"

# --- Windows constants ----------------------------------------------------------

DRIVE_REMOTE: Final = 4
FILE_ATTRIBUTE_NOT_CONTENT_INDEXED: Final = 0x2000
# The attributes ``SetFileAttributesW`` accepts; what a folder already carries
# is kept, everything else (DIRECTORY, REPARSE_POINT, ...) is masked off.
_SETTABLE_ATTRIBUTES: Final = 0x1 | 0x2 | 0x4 | 0x20 | 0x100 | 0x1000 | 0x2000

APP_FOLDER_NAME: Final = install_layout.APP_FOLDER_NAME

# --- the warning lines (fixed text; no path is ever shown) --------------------

LOCATION_ONEDRIVE: Final = (
    "Clinic Scribe's data folder is inside OneDrive, which can copy it off this computer."
)
LOCATION_NETWORK: Final = (
    "Clinic Scribe's data folder is on a network drive, so its files are kept off this computer."
)
LOCATION_ROAMING: Final = (
    "Clinic Scribe's data folder is in the roaming part of your Windows profile, "
    "which Windows can copy to other computers."
)
LOCATION_UNCHECKED: Final = "Clinic Scribe could not check where its data folder is kept."


def wer_not_excluded_line() -> str:
    """The missing-WER-exclusion warning with this build's remedy
    (installation plan Task 1.7: ``install_layout.registration_remedy``)."""
    return (
        "Crash reports are not excluded for Clinic Scribe — "
        f"{install_layout.registration_remedy()}, then restart Clinic Scribe."
    )


WER_UNCHECKED: Final = "Clinic Scribe could not check whether crash reports are excluded."
# D6 / C5: the values are a best-effort request to Windows backup and
# snapshot tools, so the lines say "marked to be left out", never "excluded".
BACKUP_NOT_EXCLUDED: Final = (
    "Clinic Scribe's live recordings and logs are not marked to be left out of Windows "
    f"backups and snapshots (a best-effort setting) — {install_layout.FROZEN_REMEDY}."
)
BACKUP_UNCHECKED: Final = (
    "Clinic Scribe could not check whether its live recordings and logs are marked to be "
    "left out of Windows backups and snapshots."
)
NOT_INDEXED_FAILED: Final = (
    "Some of Clinic Scribe's folders could not be marked to stay out of Windows Search."
)
# D10, verbatim for the documented console launch.
_UNCOVERED_LAUNCH: Final = (
    "Crash reports are not excluded for this launch ({name}) — start the app with scribe-app.exe."
)
# A file name shown in the line only when it is a plain one.
_PLAIN_FILE_NAME: Final = re.compile(r"[A-Za-z0-9._-]{1,64}")


def uncovered_launch_line(executable_name: str) -> str:
    """D10's uncovered-launch warning for ``executable_name`` (``python.exe``
    for the console launch). A name that is not a plain file name reads
    "this program"."""
    name = executable_name if _PLAIN_FILE_NAME.fullmatch(executable_name) else "this program"
    return _UNCOVERED_LAUNCH.format(name=name)


@dataclass(frozen=True)
class ExclusionWarning:
    """One warning: a content-free ``code`` for the log and its fixed line."""

    code: str
    line: str


# --- the Windows layer ----------------------------------------------------------


class WindowsLayer(Protocol):
    """Every Windows call the start-up checks make (C6: a fake in tests)."""

    def environ(self, name: str) -> str | None:
        """An environment variable; None when unset or empty."""
        ...

    def realpath(self, path: str) -> str:
        """``os.path.realpath`` (links and junctions resolved)."""
        ...

    def drive_type(self, root: str) -> int:
        """``GetDriveTypeW`` of a drive root such as ``C:\\``."""
        ...

    def file_attributes(self, path: str) -> int:
        """The file attributes of ``path`` itself (a link is not followed);
        raises ``OSError`` when they cannot be read."""
        ...

    def set_file_attributes(self, path: str, attributes: int) -> bool:
        """``SetFileAttributesW``; False when Windows refused (never raises)."""
        ...

    def wer_exclusions(self, hive: Hive = "HKCU") -> dict[str, int]:
        """The DWORD values present under ``<hive>\\<WER_EXCLUDED_KEY>`` for
        the names in ``WER_EXCLUDED_APPLICATIONS`` (an absent key or value, or
        a value of another type, is simply missing). Raises ``OSError`` when
        the key exists but cannot be read."""
        ...

    def backup_exclusions(self) -> dict[str, tuple[str, ...]]:
        """For each of ``BACKUP_EXCLUSION_KEYS`` under
        ``HKLM\\<BACKUP_RESTORE_KEY>``, the strings of its REG_MULTI_SZ value
        ``install_layout.BACKUP_VALUE_NAME`` (an absent key or value, or a
        value of another type, is simply missing). Raises ``OSError`` when a
        key exists but cannot be read."""
        ...

    def native_host_entries(self, key: str) -> tuple[HostEntry, ...]:
        """The native host's registry entries — the default (string) value
        of ``key`` under HKCU and HKLM, each in both registry views — in
        ``CHROME_LOOKUP_ORDER``, so the first is the one Chrome uses. A view
        that cannot be read is passed over (Chrome passes over it too); the
        same value found in both views of one hive (HKCU is shared between
        them) is listed once."""
        ...


@functools.cache
def _kernel32() -> Any:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetDriveTypeW.argtypes = [ctypes.c_wchar_p]
    kernel32.GetDriveTypeW.restype = ctypes.c_uint
    kernel32.SetFileAttributesW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
    kernel32.SetFileAttributesW.restype = ctypes.c_int
    return kernel32


class Win32WindowsLayer:
    """The real layer: ``os.environ``, ``os.path.realpath``, one
    ``GetDriveTypeW``, ``os.stat``'s attributes, one ``SetFileAttributesW`` and
    read-only ``winreg`` reads. Never built in tests (the conftest sentinel
    makes it raise)."""

    def environ(self, name: str) -> str | None:
        return os.environ.get(name) or None

    def realpath(self, path: str) -> str:
        return os.path.realpath(path)

    def drive_type(self, root: str) -> int:
        return int(_kernel32().GetDriveTypeW(root))

    def file_attributes(self, path: str) -> int:
        return os.stat(path, follow_symlinks=False).st_file_attributes

    def set_file_attributes(self, path: str, attributes: int) -> bool:
        return bool(_kernel32().SetFileAttributesW(path, attributes))

    def wer_exclusions(self, hive: Hive = "HKCU") -> dict[str, int]:
        if sys.platform != "win32":
            return {}
        import winreg

        root = winreg.HKEY_LOCAL_MACHINE if hive == "HKLM" else winreg.HKEY_CURRENT_USER
        try:
            key = winreg.OpenKey(
                root, WER_EXCLUDED_KEY, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY
            )
        except FileNotFoundError:
            return {}
        values: dict[str, int] = {}
        with key:
            for name in WER_EXCLUDED_APPLICATIONS:
                try:
                    value, kind = winreg.QueryValueEx(key, name)
                except FileNotFoundError:
                    continue
                if kind == winreg.REG_DWORD and isinstance(value, int):
                    values[name] = value
        return values

    def backup_exclusions(self) -> dict[str, tuple[str, ...]]:
        if sys.platform != "win32":
            return {}
        import winreg

        found: dict[str, tuple[str, ...]] = {}
        for subkey in BACKUP_EXCLUSION_KEYS:
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    f"{BACKUP_RESTORE_KEY}\\{subkey}",
                    0,
                    winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
                )
            except FileNotFoundError:
                continue
            with key:
                try:
                    value, kind = winreg.QueryValueEx(key, install_layout.BACKUP_VALUE_NAME)
                except FileNotFoundError:
                    continue
            if kind == winreg.REG_MULTI_SZ and isinstance(value, list):
                found[subkey] = tuple(str(item) for item in value)
        return found

    def native_host_entries(self, key: str) -> tuple[HostEntry, ...]:
        if sys.platform != "win32":
            return ()
        import winreg

        hives = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}
        views = {"32": winreg.KEY_WOW64_32KEY, "64": winreg.KEY_WOW64_64KEY}
        entries: list[HostEntry] = []
        # Chromium opens these keys with KEY_QUERY_VALUE (round 13 LOW-005):
        # a query-only ACL that Chrome can use is read here too.
        access = winreg.KEY_QUERY_VALUE
        for hive, view in CHROME_LOOKUP_ORDER:
            try:
                with winreg.OpenKey(hives[hive], key, 0, access | views[view]) as handle:
                    value, kind = winreg.QueryValueEx(handle, "")
            except OSError:
                continue  # absent or unreadable: Chrome passes over it too
            if kind == winreg.REG_EXPAND_SZ and isinstance(value, str):
                value = winreg.ExpandEnvironmentStrings(value)
            elif kind != winreg.REG_SZ or not isinstance(value, str):
                continue
            entry = HostEntry(hive, view, value)
            if not any(e.hive == hive and e.manifest == value for e in entries):
                entries.append(entry)
        return tuple(entries)


# --- the data folder ------------------------------------------------------------


def app_data_root(layer: WindowsLayer) -> Path:
    """``%LOCALAPPDATA%\\ClinikoScribe`` (``ClinikoScribe-dev`` for the dev
    channel) — the rule every store's default root follows (``LOCALAPPDATA``,
    else the home folder), read through the layer
    (``install_layout.app_data_root_via``)."""
    return install_layout.app_data_root_via(layer)


def _normalised(path: str) -> str:
    r"""A Windows path for comparison: ``\\?\X:\`` reduced to ``X:\``,
    ``\\?\UNC\server`` to ``\\server``, case folded, no trailing separator."""
    text = path.replace("/", "\\")
    if text.startswith("\\\\?\\UNC\\"):
        text = "\\\\" + text[len("\\\\?\\UNC\\") :]
    elif text.startswith("\\\\?\\"):
        text = text[len("\\\\?\\") :]
    text = ntpath.normcase(text)
    if len(text) > 3:  # keep a drive root's own separator ("c:\")
        text = text.rstrip("\\")
    return text


def _contains(base: str, path: str) -> bool:
    """``path`` is ``base`` or inside it (both ``_normalised``)."""
    if not base:
        return False
    return path == base or path.startswith(base.rstrip("\\") + "\\")


def _is_network(layer: WindowsLayer, real: str) -> bool:
    if real.startswith("\\\\"):
        return True
    drive, _rest = ntpath.splitdrive(real)
    if len(drive) == 2 and drive[1] == ":":
        return layer.drive_type(drive.upper() + "\\") == DRIVE_REMOTE
    return False


def check_location(
    layer: WindowsLayer, root: Path, logger: logging.Logger | None = None
) -> list[ExclusionWarning]:
    """D10's location check of the resolved data folder. Read-only. A folder
    outside ``%USERPROFILE%\\AppData\\Local`` that none of the three named
    conditions explains is logged as ``location_unusual``, never shown."""
    real = _normalised(layer.realpath(str(root)))
    warnings: list[ExclusionWarning] = []
    for variable in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer"):
        base = layer.environ(variable)
        if base and _contains(_normalised(layer.realpath(base)), real):
            warnings.append(ExclusionWarning("location_onedrive", LOCATION_ONEDRIVE))
            break
    if _is_network(layer, real):
        warnings.append(ExclusionWarning("location_network", LOCATION_NETWORK))
    roaming = layer.environ("APPDATA")
    if roaming and _contains(_normalised(layer.realpath(roaming)), real):
        warnings.append(ExclusionWarning("location_roaming", LOCATION_ROAMING))
    profile = layer.environ("USERPROFILE")
    expected = (
        _normalised(layer.realpath(ntpath.join(profile, "AppData", "Local")))
        if profile
        else ""
    )
    if not warnings and not _contains(expected, real) and logger is not None:
        try:
            log_event(logger, "exclusions", detail_code="location_unusual")
        except Exception:  # noqa: BLE001 - a log failure is not a failed check
            pass
    return warnings


def check_wer(layer: WindowsLayer, executable: str) -> list[ExclusionWarning]:
    """D10's WER check. Read-only. Warns when any of the channel's exclusions
    (``wer_applications``) is missing (or not DWORD 1) in every hive the
    channel reads (``wer_hives``: HKLM then HKCU in production, HKCU in
    dev), and when the RUNNING interpreter's file name is not one of them —
    the console launch (``python.exe``) — whatever the registry holds. Each
    hive is read on its own (round 14 LOW-003): the hives that could be read
    give the answer, and only when they leave an executable uncovered AND a
    hive could not be read is it "could not check"."""
    names = wer_applications()
    warnings: list[ExclusionWarning] = []
    found: list[dict[str, int]] = []
    unreadable = False
    for hive in wer_hives():
        try:
            found.append(layer.wer_exclusions(hive))
        except OSError:
            unreadable = True
    if any(all(values.get(name) != WER_EXCLUDED_VALUE for values in found) for name in names):
        if unreadable:
            warnings.append(ExclusionWarning("wer_unchecked", WER_UNCHECKED))
        else:
            warnings.append(ExclusionWarning("wer_not_excluded", wer_not_excluded_line()))
    name = ntpath.basename(executable)
    if name.casefold() not in names:
        warnings.append(ExclusionWarning("wer_uncovered_launch", uncovered_launch_line(name)))
    return warnings


def check_backup_exclusions(layer: WindowsLayer) -> list[ExclusionWarning]:
    """D6's check (Task 2.4). Read-only, and production only — the dev
    channel never reads or warns about these machine-wide values. Warns
    when either HKLM value (``BACKUP_EXCLUSION_KEYS``) is missing or does
    not hold every pattern ``install_layout.backup_exclusion_patterns()``
    names (live sessions and logs; compared without case or surrounding
    space); a value that cannot be read is said so."""
    if install_layout.channel() != "production":
        return []
    try:
        values = layer.backup_exclusions()
    except OSError:
        return [ExclusionWarning("backup_unchecked", BACKUP_UNCHECKED)]
    wanted = {pattern.casefold() for pattern in install_layout.backup_exclusion_patterns()}
    for subkey in BACKUP_EXCLUSION_KEYS:
        held = {item.strip().casefold() for item in values.get(subkey, ())}
        if not wanted <= held:
            return [ExclusionWarning("backup_not_excluded", BACKUP_NOT_EXCLUDED)]
    return []


def mark_not_indexed(layer: WindowsLayer, root: Path) -> int:
    """Set NOT_CONTENT_INDEXED on ``root`` and every folder beneath it that
    lacks it, best effort; returns how many could not be marked (or read).

    Folders only (files take the attribute from their folder when they are
    created); links and junctions — the root included — are never followed
    or marked. Never raises."""
    failures = 0
    try:
        if os.path.islink(root) or os.path.isjunction(root) or not root.is_dir():
            return 0
    except OSError:
        return 1
    pending: list[Path] = [root]
    while pending:
        folder = pending.pop()
        try:
            attributes = layer.file_attributes(str(folder))
            if not attributes & FILE_ATTRIBUTE_NOT_CONTENT_INDEXED:
                wanted = (attributes & _SETTABLE_ATTRIBUTES) | FILE_ATTRIBUTE_NOT_CONTENT_INDEXED
                if not layer.set_file_attributes(str(folder), wanted):
                    failures += 1
            with os.scandir(folder) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False) and not entry.is_junction():
                        pending.append(Path(entry.path))
        except Exception:  # noqa: BLE001 - best effort: counted, never raised
            failures += 1
    return failures


def startup_exclusions(
    layer: WindowsLayer,
    *,
    executable: str,
    logger: logging.Logger,
    root: Path | None = None,
) -> tuple[str, ...]:
    """Flow 6 at start-up: mark the data folder, then the location, WER and
    (production only) backup-exclusion checks. Returns the warning lines to
    show (Status tab and Past sessions);
    each warning is logged by its code only. Never raises and never refuses
    start-up: a check that fails unexpectedly says it could not check."""
    warnings: list[ExclusionWarning] = []
    try:
        folder = root if root is not None else app_data_root(layer)
        if mark_not_indexed(layer, folder):
            warnings.append(ExclusionWarning("not_indexed_failed", NOT_INDEXED_FAILED))
        warnings.extend(check_location(layer, folder, logger))
    except Exception:  # noqa: BLE001 - a read-only check never refuses start-up
        warnings.append(ExclusionWarning("location_unchecked", LOCATION_UNCHECKED))
    try:
        warnings.extend(check_wer(layer, executable))
    except Exception:  # noqa: BLE001
        warnings.append(ExclusionWarning("wer_unchecked", WER_UNCHECKED))
    try:
        warnings.extend(check_backup_exclusions(layer))
    except Exception:  # noqa: BLE001 - only ever a warning (Task 2.4)
        warnings.append(ExclusionWarning("backup_unchecked", BACKUP_UNCHECKED))
    try:
        for warning in warnings:
            log_event(logger, "exclusions", detail_code=warning.code)
        log_event(logger, "exclusions", state="checked", count=len(warnings))
    except Exception:  # noqa: BLE001 - the lines are still shown
        pass
    return tuple(warning.line for warning in warnings)


# --- the exception hooks (C3) ---------------------------------------------------
# A handler that fails to write the hook's line reports only the failure's
# type (``logging_setup.QuietHandlerErrors``, round 23 PR-MED-020), so a
# logging failure cannot print the exception being handled either.


_LAST_EXCEPTION_ATTRIBUTES: Final = ("last_exc", "last_type", "last_value", "last_traceback")


def _drop_last_exception() -> None:
    """Remove the interpreter's ``sys.last_*`` references to the last
    uncaught exception (they exist only for interactive debugging)."""
    for name in _LAST_EXCEPTION_ATTRIBUTES:
        if hasattr(sys, name):
            delattr(sys, name)


class ExceptionHook:
    """One installed hook: logs ``uncaught_exception error_code=<type name>
    detail_code=<where>`` and nothing else. ``previous`` is the hook it
    replaced (never called — see the module docstring). Never raises."""

    def __init__(self, logger: logging.Logger, where: str, previous: Callable[..., Any]) -> None:
        self.logger = logger
        self.where = where
        self.previous = previous

    def __call__(self, *args: Any) -> None:
        try:
            if self.where == "main":
                exc_type = args[0]
            else:  # thread / unraisable: one argument object with ``exc_type``
                exc_type = getattr(args[0], "exc_type", None)
                if self.where == "thread" and exc_type is SystemExit:
                    return  # as threading's own hook: a thread's SystemExit is silent
            log_event(
                self.logger,
                "uncaught_exception",
                error_code=exception_type_name(exc_type),
                detail_code=self.where,
            )
        except Exception:  # noqa: BLE001 - a hook must never raise
            pass
        if self.where == "main":
            # Round 21 LOW-001: ``PyErr_Print`` (a Qt slot's exception goes
            # through it) stores the exception in ``sys.last_exc`` and its
            # legacy triple BEFORE calling this hook, keeping its traceback —
            # and every frame's locals, which may hold transcript or note
            # text — alive until the next one. Nothing here needs them.
            try:
                _drop_last_exception()
            except Exception:  # noqa: BLE001 - a hook must never raise
                pass


def _hook_slots() -> Iterable[tuple[str, Callable[[], Any], Callable[[Any], None]]]:
    def set_main(hook: Any) -> None:
        sys.excepthook = hook

    def set_thread(hook: Any) -> None:
        threading.excepthook = hook

    def set_unraisable(hook: Any) -> None:
        sys.unraisablehook = hook

    return (
        ("main", lambda: sys.excepthook, set_main),
        ("thread", lambda: threading.excepthook, set_thread),
        ("unraisable", lambda: sys.unraisablehook, set_unraisable),
    )


def install_exception_hooks(logger: logging.Logger) -> Callable[[], None]:
    """Install the three hooks; returns ``restore``, which puts back each
    replaced hook while ours is still the one installed (a hook someone
    installed after ours is left alone). ``restore`` never raises."""
    installed: list[tuple[ExceptionHook, Callable[[], Any], Callable[[Any], None]]] = []
    for where, get, put in _hook_slots():
        hook = ExceptionHook(logger, where, get())
        put(hook)
        installed.append((hook, get, put))

    def restore() -> None:
        for hook, get, put in installed:
            if get() is hook:
                put(hook.previous)

    return restore


def remove_exception_hooks() -> bool:
    """Unwind every ``ExceptionHook`` still installed in any of the three
    slots (to the first hook that is not one); True when one was found. The
    test sentinel's clean-up."""
    found = False
    for _where, get, put in _hook_slots():
        current = get()
        while isinstance(current, ExceptionHook):
            found = True
            put(current.previous)
            current = get()
    return found
