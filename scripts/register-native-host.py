r"""Register (or unregister) the DEV channel's Chrome native-messaging host —
plan Step 6; dev-only since installation plan Task 3.7.

Installs the native-messaging registration into the source checkout's data
folder, %LOCALAPPDATA%\ClinikoScribe-dev, ALWAYS the dev channel (installation
plan Tasks 1.4 and 3.7): the dev host name `com.scribe.cliniko_host_dev` for
the dev extension, a copy of the venv's `scribe-host.exe` plus the host
manifest, then writes and verifies the HKCU registry value. The installed
app's Chrome link is its installer's (HKLM), never this script's. Rerun after
any venv move; registration is per Windows user.

`--unregister` also removes what this script wrote before the installed app
existed: a per-user `com.scribe.cliniko_host` key (it would shadow the
installed link, D9) and that registration's two files in the production data
folder (`com.scribe.cliniko_host.json` and `scribe-host.exe` — only those two
files, never the folder or anything else in it). UNTIL THE APP IS INSTALLED
that key and those files are the source-run app's own LIVE Chrome link (a
checkout of `main` still registers the production name), so `--unregister`
also unlinks it from Chrome: run it only as the installation's step (Phase P
step 2) or when you mean to unlink that app; register it again from its own
checkout to undo.

A file Chrome or the app still holds (Windows error 32) stops the run with
"Close Clinic Scribe and Chrome completely, then run this again".

Two requirements learned at the Phase-1 gate, where a failure was SILENT
(Chrome reports only "Specified native messaging host not found"):
1. The install path is kept free of spaces. At that gate a manifest under
   `C:\Recording clinic software\...` was never resolved — which is why the
   %LOCALAPPDATA% data folder is used instead of the repo. The installation
   plan's Task 0.2 has since linked Chrome to a host in
   `C:\Program Files\ClinikoScribe`, so a space alone is NOT Chrome's rule
   (round 27 PR-LOW-025; the gate's failure was not re-diagnosed). The
   refusal below stays as a conservative guard; the dev folder has no space.
2. The host must be an `.exe` (not `.bat`/`.cmd`). `scribe-host.exe` comes
   from the gui-scripts entry point, so it is windowless and receives
   Chrome's bare origin argv plus `--parent-window` directly. The copy still
   runs the repo's code — the launcher embeds the venv interpreter path.

It also writes the four per-user Windows Error Reporting exclusions
(privacy-professional-controls Task 4.2, D10): DWORD 1 for `pythonw.exe`,
`python.exe`, `scribe-app.exe` and `scribe-host.exe` under
HKCU\Software\Microsoft\Windows\Windows Error Reporting\ExcludedApplications
(what `WerAddExcludedApplication(..., FALSE)` writes; no admin rights, no
HKLM), and verifies each by reading it back — a value that does not read back
as DWORD 1 fails the run. `pythonw.exe` is there because the venv launchers
start the base `pythonw.exe` as a child; it therefore covers every pythonw
process of this Windows user (the agreed breadth). `python.exe` (the
development-recordings plan's hardening, round 45, practitioner decision
2026-10-08) because the replay tool and `measure-speakers.py` read recordings
that may hold a real consultation under it, and refuse to run unless it is
excluded; it covers every python.exe process of this user the same way.
`--unregister` removes those four values only, never the key or anyone else's
values (after it, those two tools refuse again).

RUN IT FROM A NORMAL TERMINAL (PowerShell or cmd), never from an agent shell:
on this machine agent shells are MSIX-virtualized for both %LOCALAPPDATA% and
the HKCU registry (docs/lessons.md), so a write, a read-back "verified : OK" or
a `reg query` from an agent shell proves nothing about what the app and
Chrome see. Only a run and a check from the practitioner's own terminal count.

Usage (from the repo root, inside the project venv):
    .venv/Scripts/python.exe scripts/register-native-host.py
    .venv/Scripts/python.exe scripts/register-native-host.py --unregister
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

# The WER names and key the app's start-up check reads (one definition).
from scribe_desktop.exclusions import (
    WER_EXCLUDED_APPLICATIONS,
    WER_EXCLUDED_KEY,
    WER_EXCLUDED_VALUE,
)

from scribe_desktop import identity, install_layout

REPO = Path(__file__).resolve().parents[1]
# Installation plan Tasks 1.4 and 3.7 (D3): the DEV channel, named outright —
# the dev host name, the dev extension's origin and the dev data folder
# (%LOCALAPPDATA%\ClinikoScribe-dev), whatever channel the importing process
# is pinned to. The installed app's Chrome link is the installer's (HKLM),
# never this script's. The identities come from the same accessors the host
# enforces.
HOST_NAME = identity.host_name("dev")
ALLOWED_ORIGIN = identity.expected_origin("dev")
REGISTRY_KEY = identity.registry_key("dev")
# Install target: stable, outside the repo, kept space-free as a conservative
# guard (see module docstring).
INSTALL_DIR = install_layout.data_root("dev")
MANIFEST_PATH = INSTALL_DIR / f"{HOST_NAME}.json"
INSTALLED_EXE = INSTALL_DIR / "scribe-host.exe"

# Pre-gate artifacts that lived in the repo; removed on register/unregister.
# They were only ever written under the production host name.
LEGACY_ARTIFACTS = (
    REPO / "scripts" / "dev-host-launcher.bat",
    REPO / "scripts" / f"{identity.HOST_NAME}.json",
)

# Task 3.7: what this script wrote before the installed app existed, removed
# by --unregister — the per-user link under the PRODUCTION host name (it
# would shadow the installed HKLM link, D9) and that registration's two files
# in the production data folder.
STRAY_PRODUCTION_KEY = identity.registry_key("production")
STRAY_PRODUCTION_FILES = (
    install_layout.data_root("production") / f"{identity.HOST_NAME}.json",
    install_layout.data_root("production") / "scribe-host.exe",
)

# Windows' ERROR_SHARING_VIOLATION: Chrome (or the app) holds the file open —
# what a COPY over a running host meets (docs/lessons.md, 2026-10-02).
_ERROR_SHARING_VIOLATION = 32
# Windows' ERROR_ACCESS_DENIED: what DELETING a running program's image meets
# (round 22) — `--unregister` with Chrome still running the old host.
_ERROR_ACCESS_DENIED = 5
IN_USE_LINE = "Close Clinic Scribe and Chrome completely, then run this again."


def _in_use(exc: OSError, *, deleting: bool = False) -> bool:
    code = getattr(exc, "winerror", None)
    return code == _ERROR_SHARING_VIOLATION or (deleting and code == _ERROR_ACCESS_DENIED)


def venv_executable() -> Path:
    """The venv's scribe-host.exe, resolved from the running interpreter."""
    return Path(sys.executable).parent / "scribe-host.exe"


def generate_manifest() -> dict[str, object]:
    return {
        "name": HOST_NAME,
        "description": "Cliniko clinical scribe native host (Phase 1)",
        "path": str(INSTALLED_EXE),
        "type": "stdio",
        "allowed_origins": [ALLOWED_ORIGIN],
    }


def register_wer(winreg: Any) -> list[str]:
    """Write the four WER exclusions (HKCU, DWORD 1 each) and read each back.

    Returns the names that did NOT read back as DWORD 1 (empty: all verified).
    ``winreg`` is passed in so tests use a fake; nothing here touches HKLM."""
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, WER_EXCLUDED_KEY) as key:
        for name in WER_EXCLUDED_APPLICATIONS:
            winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, WER_EXCLUDED_VALUE)
    failed: list[str] = []
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WER_EXCLUDED_KEY) as key:
            for name in WER_EXCLUDED_APPLICATIONS:
                try:
                    value, kind = winreg.QueryValueEx(key, name)
                except OSError:
                    failed.append(name)
                    continue
                if kind != winreg.REG_DWORD or value != WER_EXCLUDED_VALUE:
                    failed.append(name)
    except OSError:
        return list(WER_EXCLUDED_APPLICATIONS)
    return failed


def unregister_wer(winreg: Any) -> list[str]:
    """Delete the four WER values this script owns; returns the ones removed.
    The key itself and any other value under it are left alone."""
    removed: list[str] = []
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, WER_EXCLUDED_KEY, 0, winreg.KEY_SET_VALUE
        )
    except FileNotFoundError:
        return removed
    with key:
        for name in WER_EXCLUDED_APPLICATIONS:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                continue
            removed.append(name)
    return removed


def register() -> int:
    import winreg

    source_exe = venv_executable()
    if not source_exe.is_file():
        print(
            f"ERROR: {source_exe} not found — run `pip install -e desktop` in this "
            "venv so the scribe-host launcher is generated.",
            file=sys.stderr,
        )
        return 1
    if " " in str(INSTALL_DIR):
        print(
            f"ERROR: install dir {INSTALL_DIR} contains a space; the developer "
            "build keeps its Chrome link in a space-free folder.",
            file=sys.stderr,
        )
        return 1

    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(source_exe, INSTALLED_EXE)
        MANIFEST_PATH.write_text(
            json.dumps(generate_manifest(), indent=2) + "\n", encoding="utf-8"
        )
        for stale in LEGACY_ARTIFACTS:
            if stale.exists():
                stale.unlink()
    except OSError as exc:
        if not _in_use(exc):
            raise
        print(f"ERROR: {IN_USE_LINE}", file=sys.stderr)
        return 1

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(MANIFEST_PATH))

    # Verify what actually landed (plan: write + verify, never assume).
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
        value, _ = winreg.QueryValueEx(key, "")
    ok = value == str(MANIFEST_PATH) and MANIFEST_PATH.is_file() and INSTALLED_EXE.is_file()
    manifest_ok = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) == generate_manifest()

    # Task 4.2 (D10): the crash-report exclusions, written and read back.
    wer_failed = register_wer(winreg)

    print(f"host exe : {INSTALLED_EXE}")
    print(f"manifest : {MANIFEST_PATH}")
    print(f"registry : HKCU\\{REGISTRY_KEY} -> {value}")
    print(f"wer      : HKCU\\{WER_EXCLUDED_KEY} -> {', '.join(WER_EXCLUDED_APPLICATIONS)}")
    if wer_failed:
        print(
            "ERROR: these crash-report exclusions did not read back as DWORD 1: "
            + ", ".join(wer_failed),
            file=sys.stderr,
        )
    verified = ok and manifest_ok and not wer_failed
    print(f"verified : {'OK' if verified else 'FAIL'}")
    print("note     : registration is per Windows user; rerun after any venv move")
    print("note     : run from a normal terminal; an agent shell's run or check proves nothing")
    return 0 if verified else 1


def unregister() -> int:
    import winreg

    removed = []
    # Task 3.7: the dev key, and a stray per-user key under the production
    # name (an HKCU key only — the installed HKLM link is never touched).
    for key in (REGISTRY_KEY, STRAY_PRODUCTION_KEY):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
            removed.append(f"HKCU\\{key}")
        except FileNotFoundError:
            pass
    removed.extend(f"WER exclusion {name}" for name in unregister_wer(winreg))
    for path in (MANIFEST_PATH, INSTALLED_EXE, *LEGACY_ARTIFACTS, *STRAY_PRODUCTION_FILES):
        try:
            if path.exists():
                path.unlink()
                removed.append(str(path))
        except OSError as exc:
            if not _in_use(exc, deleting=True):
                raise
            print("removed  : " + ("; ".join(removed) if removed else "nothing"))
            print(f"ERROR: {IN_USE_LINE}", file=sys.stderr)
            return 1
    print("removed  : " + ("; ".join(removed) if removed else "nothing (already clean)"))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Register the DEV channel's Chrome native-messaging host and the four "
            "per-user crash-report (WER) exclusions (the installed app's link is its "
            "installer's). Run it from a normal terminal: a run or check from an agent "
            "shell proves nothing on this machine."
        )
    )
    parser.add_argument(
        "--unregister",
        action="store_true",
        help="remove the dev registration, its generated files and the four WER values, "
        "plus the per-user link under the installed app's name and its two files - until "
        "the app is installed, that is the source-run app's live Chrome link (Phase P "
        "step 2 removes it on purpose)",
    )
    args = parser.parse_args()
    if sys.platform != "win32":
        print("ERROR: Windows-only (HKCU registration).", file=sys.stderr)
        return 2
    return unregister() if args.unregister else register()


if __name__ == "__main__":
    raise SystemExit(main())
