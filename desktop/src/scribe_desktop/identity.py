"""Canonical identity constants (plan: "never re-derived").

THE single definition site for the extension/host pairing. Everything —
the native host's origin check, the registration script's manifest
generation, the status display, and the integration tests — imports from
here so the allowed_origins / origin-check pairing cannot drift.

The extension ID itself is pinned by extension/KEY.md (plan Step 3).

Installation plan Task 1.4 (D2/D3): the production constants below keep
their names and values (C2). Beside them sit the dev channel's values and
one ACCESSOR per identity; only the accessors are channel-aware
(``install_layout.channel()``, or an explicit ``of``), and every consumer
that must follow the channel calls an accessor. The extension's mirror is
``extension/src/channel.ts`` (cross-checked by ``test_identity.py``).
"""

from __future__ import annotations

from typing import Final

from scribe_desktop import install_layout
from scribe_desktop.install_layout import Channel
from scribe_desktop.protocol import HOST_NAME

EXTENSION_ID = "mbmhglgadhdohpgbmpbjnaifjagfdfid"
EXPECTED_ORIGIN = f"chrome-extension://{EXTENSION_ID}/"
REGISTRY_KEY = rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}"
# The per-user pipe name's prefix (the SID follows); re-exported by
# ``pipe_server`` under the same name.
PIPE_PREFIX: Final = "\\\\.\\pipe\\ClinikoScribe-"

# The dev channel (D3): its own host name, extension (its own key — Task 1.3
# recorded the id) and pipe, so a dev registration never shadows the
# installed link and a dev app never answers the installed extension.
DEV_HOST_NAME: Final = "com.scribe.cliniko_host_dev"
DEV_EXTENSION_ID: Final = "pecfiifdlmdbkifmjkbkeiaflpenfejd"
DEV_PIPE_PREFIX: Final = "\\\\.\\pipe\\ClinikoScribe-dev-"

_REGISTRY_PARENT: Final = r"Software\Google\Chrome\NativeMessagingHosts"

# 32 random bytes hex-encoded (see HostSession.nonce_factory).
NONCE_HEX_LENGTH = 64


def _which(of: Channel | None) -> Channel:
    return of if of is not None else install_layout.channel()


def host_name(of: Channel | None = None) -> str:
    """The native host name Chrome launches for this channel."""
    return HOST_NAME if _which(of) == "production" else DEV_HOST_NAME


def extension_id(of: Channel | None = None) -> str:
    """The extension id the channel's extension build carries."""
    return EXTENSION_ID if _which(of) == "production" else DEV_EXTENSION_ID


def expected_origin(of: Channel | None = None) -> str:
    """The one caller origin the channel's host accepts."""
    return f"chrome-extension://{extension_id(of)}/"


def registry_key(of: Channel | None = None) -> str:
    """The Chrome native-messaging registry key (under HKCU or HKLM) for the
    channel's host name."""
    return rf"{_REGISTRY_PARENT}\{host_name(of)}"


def pipe_prefix(of: Channel | None = None) -> str:
    """The channel's pipe-name prefix; the user's SID follows it."""
    return PIPE_PREFIX if _which(of) == "production" else DEV_PIPE_PREFIX


__all__ = [
    "DEV_EXTENSION_ID",
    "DEV_HOST_NAME",
    "DEV_PIPE_PREFIX",
    "EXPECTED_ORIGIN",
    "EXTENSION_ID",
    "HOST_NAME",
    "NONCE_HEX_LENGTH",
    "PIPE_PREFIX",
    "REGISTRY_KEY",
    "expected_origin",
    "extension_id",
    "host_name",
    "pipe_prefix",
    "registry_key",
]
