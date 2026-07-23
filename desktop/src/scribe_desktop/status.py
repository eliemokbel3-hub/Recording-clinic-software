"""Registration status + self-test logic for the desktop window (plan Step 8).

Kept GUI-free so it is unit-testable; `app.py` renders these results.
The registration display is INFORMATIONAL ONLY — never a security signal
(plan: the excluded status-file design's lesson applies to any UI state).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from scribe_desktop.protocol import HOST_NAME
from scribe_desktop.secure_storage import SecureStorageProvider, SessionCrypto

REGISTRY_KEY = rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}"


@dataclass(frozen=True)
class RegistrationStatus:
    registry_value: str | None
    manifest_exists: bool
    launcher_exists: bool

    @property
    def registered(self) -> bool:
        return self.registry_value is not None and self.manifest_exists and self.launcher_exists


def read_registration_status() -> RegistrationStatus:
    registry_value: str | None = None
    if sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
                value, _ = winreg.QueryValueEx(key, "")
                registry_value = str(value)
        except FileNotFoundError:
            registry_value = None
    manifest = Path(registry_value) if registry_value else None
    launcher_exists = False
    if manifest is not None and manifest.is_file():
        import json

        try:
            launcher_exists = Path(
                json.loads(manifest.read_text(encoding="utf-8"))["path"]
            ).is_file()
        except (ValueError, KeyError, OSError):
            launcher_exists = False
    return RegistrationStatus(
        registry_value=registry_value,
        manifest_exists=manifest is not None and manifest.is_file(),
        launcher_exists=launcher_exists,
    )


@dataclass(frozen=True)
class SelfTestResult:
    name: str
    passed: bool
    detail: str


def run_self_test() -> list[SelfTestResult]:
    """Flow 2: durable-store round-trip (test data) + session-crypto lifecycle."""
    results: list[SelfTestResult] = []

    store = SecureStorageProvider()
    try:
        store.store("test", "probe", "self-test-value")
        fetched = store.retrieve("test", "probe")
        store.delete("test", "probe")
        gone = store.retrieve("test", "probe") is None
        ok = fetched == "self-test-value" and gone
        results.append(
            SelfTestResult("credential_store", ok, "store/retrieve/delete round-trip")
        )
    except Exception as exc:  # noqa: BLE001 - self-test reports, never crashes the UI
        results.append(SelfTestResult("credential_store", False, type(exc).__name__))

    try:
        crypto = SessionCrypto()
        blob = crypto.encrypt(b"self-test payload")
        round_trip = crypto.decrypt(blob) == b"self-test payload"
        crypto.destroy()
        try:
            crypto.decrypt(blob)
            destroyed = False
        except RuntimeError:
            destroyed = True
        results.append(
            SelfTestResult(
                "session_crypto",
                round_trip and destroyed,
                "encrypt/decrypt + post-destruction failure",
            )
        )
    except Exception as exc:  # noqa: BLE001
        results.append(SelfTestResult("session_crypto", False, type(exc).__name__))

    return results
