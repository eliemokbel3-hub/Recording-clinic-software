"""Registration status + self-test logic for the desktop window (plan Step 8).

Kept GUI-free so it is unit-testable; `app.py` renders these results.
The registration display is INFORMATIONAL ONLY — never a security signal
(plan: the excluded status-file design's lesson applies to any UI state).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scribe_desktop import identity, install_layout
from scribe_desktop.exclusions import HostEntry, WindowsLayer
from scribe_desktop.secure_storage import SecureStorageProvider, SessionCrypto


@dataclass(frozen=True)
class RegistrationStatus:
    """The Chrome link as Chrome would find it (installation plan D9, Task
    2.3): ``registry_value`` is the WINNING entry's manifest path, ``winner``
    that entry and ``others`` every other entry found; ``per_user_override``
    is a packaged build with an HKCU entry for its host name (which shadows
    the installed, machine-wide one); ``checked`` is False when the
    registry was not read."""

    registry_value: str | None
    manifest_exists: bool
    launcher_exists: bool
    winner: HostEntry | None = None
    others: tuple[HostEntry, ...] = ()
    per_user_override: bool = False
    checked: bool = True

    @property
    def registered(self) -> bool:
        return self.registry_value is not None and self.manifest_exists and self.launcher_exists


def read_registration_status(layer: WindowsLayer | None) -> RegistrationStatus:
    """Read through ``layer`` (C6) in Chrome's order. ``None`` — no layer,
    as in a test window — reads nothing (``checked=False``); so does a layer
    that fails (LOW-010: it must not crash the app)."""
    if layer is None:
        return RegistrationStatus(None, False, False, checked=False)
    try:
        entries = layer.native_host_entries(identity.registry_key())
    except Exception:  # noqa: BLE001 - informational only, never a crash
        return RegistrationStatus(None, False, False, checked=False)
    winner = entries[0] if entries else None
    registry_value = winner.manifest if winner is not None else None
    manifest = Path(registry_value) if registry_value else None
    launcher_exists = False
    if manifest is not None and manifest.is_file():
        import json

        try:
            launcher_exists = Path(
                json.loads(manifest.read_text(encoding="utf-8"))["path"]
            ).is_file()
        # TypeError (round 13 LOW-011): a manifest that is not a JSON object,
        # or whose "path" is not a string — never a crash of the Status tab.
        except (ValueError, KeyError, TypeError, OSError):
            launcher_exists = False
    return RegistrationStatus(
        registry_value=registry_value,
        manifest_exists=manifest is not None and manifest.is_file(),
        launcher_exists=launcher_exists,
        winner=winner,
        others=tuple(entries[1:]),
        per_user_override=install_layout.is_frozen()
        and any(entry.hive == "HKCU" for entry in entries),
    )


_WHERE: dict[str, str] = {"HKCU": "per-user", "HKLM": "this computer's"}

# D9's Status warning, verbatim in meaning: the installed app's link is
# shadowed by a per-user one (Task 0.2 confirmed Chrome uses the HKCU entry).
PER_USER_OVERRIDE_LINE = "Warning: a per-user Chrome link overrides the installed one."


def registration_lines(status: RegistrationStatus) -> tuple[str, ...]:
    """The Status tab's registration text (no path is ever shown): the
    winning entry's verdict and where it is, how many other entries Chrome
    does not use, and D9's warning when a per-user entry shadows the
    installed link."""
    if not status.checked:
        return ("Registration: not checked",)
    if status.registered and status.winner is not None:
        detail = f"{_WHERE[status.winner.hive]} Chrome link"
        if status.others:
            count = len(status.others)
            detail += f"; {count} other link{'s' if count > 1 else ''} found, not used"
        first = f"Registration: registered ✓ ({detail})"
    else:
        first = f"Registration: NOT registered — {install_layout.registration_remedy()}"
    if status.per_user_override:
        return (first, PER_USER_OVERRIDE_LINE)
    return (first,)


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
