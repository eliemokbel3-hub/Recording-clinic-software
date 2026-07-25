"""Register (or unregister) the Chrome native-messaging host — plan Step 6.

Generates the host manifest pointing at the venv's `scribe-host.exe`, resolved
from the CURRENT interpreter path (never hand-edit; rerun after any venv move;
registration is per Windows user via HKCU), writes the registry value, and
verifies what actually landed.

The host MUST be an .exe: current Chrome silently refuses to launch .bat/.cmd
native messaging hosts — the process is never spawned. `scribe-host.exe` comes
from the gui-scripts entry point, so it also shows no console window and
receives Chrome's origin argv directly.

Usage (from the repo root, inside the project venv):
    .venv/Scripts/python.exe scripts/register-native-host.py
    .venv/Scripts/python.exe scripts/register-native-host.py --unregister
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Canonical identity constants — the script runs inside the project venv
# (see usage), so it imports the same definitions the host enforces.
from scribe_desktop.identity import EXPECTED_ORIGIN as ALLOWED_ORIGIN
from scribe_desktop.identity import HOST_NAME, REGISTRY_KEY

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
MANIFEST_PATH = SCRIPTS / f"{HOST_NAME}.json"
LEGACY_LAUNCHER = SCRIPTS / "dev-host-launcher.bat"  # removed by --unregister


def host_executable() -> Path:
    """The venv's scribe-host.exe, resolved from the running interpreter."""
    return Path(sys.executable).parent / "scribe-host.exe"


def generate_manifest() -> dict[str, object]:
    return {
        "name": HOST_NAME,
        "description": "Cliniko clinical scribe native host (Phase 1)",
        "path": str(host_executable()),
        "type": "stdio",
        "allowed_origins": [ALLOWED_ORIGIN],
    }


def register() -> int:
    import winreg

    exe = host_executable()
    if not exe.is_file():
        print(
            f"ERROR: {exe} not found — run `pip install -e desktop` in this venv "
            "so the scribe-host launcher is generated.",
            file=sys.stderr,
        )
        return 1
    if LEGACY_LAUNCHER.exists():
        LEGACY_LAUNCHER.unlink()  # Chrome cannot launch .bat hosts; remove stale copies
    MANIFEST_PATH.write_text(json.dumps(generate_manifest(), indent=2) + "\n", encoding="utf-8")

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(MANIFEST_PATH))

    # Verify what actually landed (plan: write + verify, never assume).
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
        value, _ = winreg.QueryValueEx(key, "")
    ok = value == str(MANIFEST_PATH) and MANIFEST_PATH.is_file() and exe.is_file()
    manifest_ok = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) == generate_manifest()

    print(f"host exe : {exe}")
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
    for path in (MANIFEST_PATH, LEGACY_LAUNCHER):
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
