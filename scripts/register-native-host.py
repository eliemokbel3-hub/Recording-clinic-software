"""Register (or unregister) the Chrome native-messaging host — plan Step 6.

Generates BOTH the host manifest and the launcher from the CURRENT
interpreter path (executor facts / Config Impact: never hand-edit; rerun
after any venv move; registration is per Windows user via HKCU), writes the
registry value, and verifies what actually landed.

Launcher rules (plan executor facts): @echo off, absolute venv pythonw path,
explicit working directory, %* forwarding so Chrome's origin argv and
--parent-window reach the host.

Usage (from the repo root, inside the project venv):
    .venv/Scripts/python.exe scripts/register-native-host.py
    .venv/Scripts/python.exe scripts/register-native-host.py --unregister
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HOST_NAME = "com.scribe.cliniko_host"
EXTENSION_ID = "mbmhglgadhdohpgbmpbjnaifjagfdfid"  # extension/KEY.md
ALLOWED_ORIGIN = f"chrome-extension://{EXTENSION_ID}/"
REGISTRY_KEY = rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}"

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
MANIFEST_PATH = SCRIPTS / f"{HOST_NAME}.json"
LAUNCHER_PATH = SCRIPTS / "dev-host-launcher.bat"


def generate_launcher() -> str:
    python = Path(sys.executable)
    if python.name.lower() == "python.exe":
        pythonw = python.with_name("pythonw.exe")
        if pythonw.exists():
            python = pythonw
    return (
        "@echo off\r\n"
        f'cd /d "{REPO}"\r\n'
        f'"{python}" -m scribe_desktop.native_host %*\r\n'
    )


def generate_manifest() -> dict[str, object]:
    return {
        "name": HOST_NAME,
        "description": "Cliniko clinical scribe native host (Phase 1)",
        "path": str(LAUNCHER_PATH),
        "type": "stdio",
        "allowed_origins": [ALLOWED_ORIGIN],
    }


def register() -> int:
    import winreg

    LAUNCHER_PATH.write_bytes(generate_launcher().encode("ascii"))
    MANIFEST_PATH.write_text(json.dumps(generate_manifest(), indent=2) + "\n", encoding="utf-8")

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(MANIFEST_PATH))

    # Verify what actually landed (plan: write + verify, never assume).
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
        value, _ = winreg.QueryValueEx(key, "")
    ok = value == str(MANIFEST_PATH) and MANIFEST_PATH.is_file() and LAUNCHER_PATH.is_file()
    manifest_ok = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) == generate_manifest()

    print(f"launcher : {LAUNCHER_PATH}")
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
    for path in (MANIFEST_PATH, LAUNCHER_PATH):
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
