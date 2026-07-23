"""Canonical identity constants (plan: "never re-derived").

THE single definition site for the extension/host pairing. Everything —
the native host's origin check, the registration script's manifest
generation, the status display, and the integration tests — imports from
here so the allowed_origins / origin-check pairing cannot drift.

The extension ID itself is pinned by extension/KEY.md (plan Step 3).
"""

from __future__ import annotations

from scribe_desktop.protocol import HOST_NAME

EXTENSION_ID = "mbmhglgadhdohpgbmpbjnaifjagfdfid"
EXPECTED_ORIGIN = f"chrome-extension://{EXTENSION_ID}/"
REGISTRY_KEY = rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}"

# 32 random bytes hex-encoded (see HostSession.nonce_factory).
NONCE_HEX_LENGTH = 64

__all__ = [
    "EXPECTED_ORIGIN",
    "EXTENSION_ID",
    "HOST_NAME",
    "NONCE_HEX_LENGTH",
    "REGISTRY_KEY",
]
