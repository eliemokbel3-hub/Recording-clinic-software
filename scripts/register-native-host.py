r"""Register (or unregister) the Chrome native-messaging host — plan Step 6.

Installs the native-messaging registration into %LOCALAPPDATA%\ClinikoScribe:
a copy of the venv's `scribe-host.exe` plus the host manifest, then writes and
verifies the HKCU registry value. Rerun after any venv move; registration is
per Windows user.

Two hard requirements learned at the Phase-1 gate, both of which fail SILENTLY
(Chrome reports only "Specified native messaging host not found"):
1. The install path must contain NO SPACES. A manifest under
   `C:\Recording clinic software\...` is never resolved by Chrome — which is
   why %LOCALAPPDATA%\ClinikoScribe is used instead of the repo.
2. The host must be an `.exe` (not `.bat`/`.cmd`). `scribe-host.exe` comes
   from the gui-scripts entry point, so it is windowless and receives
   Chrome's bare origin argv plus `--parent-window` directly. The copy still
   runs the repo's code — the launcher embeds the venv interpreter path.

Usage (from the repo root, inside the project venv):
    .venv/Scripts/python.exe scripts/register-native-host.py
    .venv/Scripts/python.exe scripts/register-native-host.py --unregister
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

# Canonical identity constants — the script runs inside the project venv
# (see usage), so it imports the same definitions the host enforces.
from scribe_desktop.identity import EXPECTED_ORIGIN as ALLOWED_ORIGIN
from scribe_desktop.identity import HOST_NAME, REGISTRY_KEY

REPO = Path(__file__).resolve().parents[1]
# Install target: space-free, stable, outside the repo (see module docstring).
INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ClinikoScribe"
MANIFEST_PATH = INSTALL_DIR / f"{HOST_NAME}.json"
INSTALLED_EXE = INSTALL_DIR / "scribe-host.exe"

# Pre-gate artifacts that lived in the repo; removed on register/unregister.
LEGACY_ARTIFACTS = (
    REPO / "scripts" / "dev-host-launcher.bat",
    REPO / "scripts" / f"{HOST_NAME}.json",
)


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
            f"ERROR: install dir {INSTALL_DIR} contains a space; Chrome will not "
            "resolve the host manifest there.",
            file=sys.stderr,
        )
        return 1

    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_exe, INSTALLED_EXE)
    MANIFEST_PATH.write_text(json.dumps(generate_manifest(), indent=2) + "\n", encoding="utf-8")
    for stale in LEGACY_ARTIFACTS:
        if stale.exists():
            stale.unlink()

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(MANIFEST_PATH))

    # Verify what actually landed (plan: write + verify, never assume).
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
        value, _ = winreg.QueryValueEx(key, "")
    ok = value == str(MANIFEST_PATH) and MANIFEST_PATH.is_file() and INSTALLED_EXE.is_file()
    manifest_ok = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) == generate_manifest()

    print(f"host exe : {INSTALLED_EXE}")
    print(f"manifest : {MANIFEST_PATH}")
    print(f"registry : HKCU\\{REGISTRY_KEY} -> {value}")
    print(f"verified : {'OK' if ok and manifest_ok else 'FAIL'}")
    print("note     : registration is per Windows user; rerun after any venv move")
    return 0 if ok and manifest_ok else 1


def unregister() -> int:
    import winreg

    removed = []
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
        removed.append(f"HKCU\\{REGISTRY_KEY}")
    except FileNotFoundError:
        pass
    for path in (MANIFEST_PATH, INSTALLED_EXE, *LEGACY_ARTIFACTS):
        if path.exists():
            path.unlink()
            removed.append(str(path))
    print("removed  : " + ("; ".join(removed) if removed else "nothing (already clean)"))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Register the Chrome native-messaging host.")
    parser.add_argument("--unregister", action="store_true", help="remove registration + generated files")
    args = parser.parse_args()
    if sys.platform != "win32":
        print("ERROR: Windows-only (HKCU registration).", file=sys.stderr)
        return 2
    return unregister() if args.unregister else register()


if __name__ == "__main__":
    raise SystemExit(main())
