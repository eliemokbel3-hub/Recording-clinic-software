"""Installation plan Task 1.4 (D2/D3, C2): the per-channel identity
accessors. The production constants never change (their pins live in
``test_protocol.py``, ``test_display_name.py`` and ``test_pipe_server.py``
and pass unchanged); the dev channel has its own host name, extension id,
origin, registry key and pipe prefix; and the extension's own copy of both
channels (``extension/src/channel.ts``) agrees with this one."""

from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path

import pytest

from conftest import use_channel
from scribe_desktop import identity, native_host, pipe_client, pipe_server
from scribe_desktop.install_layout import Channel

REPO = Path(__file__).resolve().parents[2]
_SID = "S-1-5-21-1111111111-2222222222-3333333333-1001"

_PRODUCTION = {
    "host_name": "com.scribe.cliniko_host",
    "extension_id": "mbmhglgadhdohpgbmpbjnaifjagfdfid",
    "expected_origin": "chrome-extension://mbmhglgadhdohpgbmpbjnaifjagfdfid/",
    "registry_key": r"Software\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host",
    "pipe_prefix": "\\\\.\\pipe\\ClinikoScribe-",
}
_DEV = {
    "host_name": "com.scribe.cliniko_host_dev",
    "extension_id": "pecfiifdlmdbkifmjkbkeiaflpenfejd",
    "expected_origin": "chrome-extension://pecfiifdlmdbkifmjkbkeiaflpenfejd/",
    "registry_key": r"Software\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host_dev",
    "pipe_prefix": "\\\\.\\pipe\\ClinikoScribe-dev-",
}


def _accessors(of: Channel | None = None) -> dict[str, str]:
    return {
        "host_name": identity.host_name(of),
        "extension_id": identity.extension_id(of),
        "expected_origin": identity.expected_origin(of),
        "registry_key": identity.registry_key(of),
        "pipe_prefix": identity.pipe_prefix(of),
    }


def test_the_production_constants_are_unchanged() -> None:
    # C2, by value — the accessors' production answers ARE these constants.
    assert identity.HOST_NAME == _PRODUCTION["host_name"]
    assert identity.EXTENSION_ID == _PRODUCTION["extension_id"]
    assert identity.EXPECTED_ORIGIN == _PRODUCTION["expected_origin"]
    assert identity.REGISTRY_KEY == _PRODUCTION["registry_key"]
    assert identity.PIPE_PREFIX == _PRODUCTION["pipe_prefix"]
    assert pipe_server.PIPE_PREFIX == _PRODUCTION["pipe_prefix"]
    assert _accessors("production") == _PRODUCTION


def test_the_dev_channel_has_its_own_values() -> None:
    assert _accessors("dev") == _DEV
    for name in _PRODUCTION:
        assert _DEV[name] != _PRODUCTION[name], name


@pytest.mark.parametrize(("which", "values"), [("production", _PRODUCTION), ("dev", _DEV)])
def test_the_accessors_follow_the_channel(
    monkeypatch: pytest.MonkeyPatch, which: Channel, values: dict[str, str]
) -> None:
    use_channel(monkeypatch, which)
    assert _accessors() == values


@pytest.mark.parametrize(("which", "values"), [("production", _PRODUCTION), ("dev", _DEV)])
def test_the_pipe_follows_the_channel(
    monkeypatch: pytest.MonkeyPatch, which: Channel, values: dict[str, str]
) -> None:
    use_channel(monkeypatch, which)
    assert pipe_server.pipe_name(_SID) == f"{values['pipe_prefix']}{_SID}"

    def unreadable() -> str:
        raise pipe_server.PipeUnavailable("create_failed")

    # The host's connector with no readable SID: still this channel's name.
    monkeypatch.setattr(pipe_client, "current_user_sid", unreadable)
    connector = pipe_client.AppPipeConnector.for_current_user()
    assert connector._name == f"{values['pipe_prefix']}unknown"  # noqa: SLF001


@pytest.mark.parametrize(("which", "other"), [("production", "dev"), ("dev", "production")])
def test_each_host_accepts_only_its_own_extension(
    monkeypatch: pytest.MonkeyPatch, which: Channel, other: Channel
) -> None:
    use_channel(monkeypatch, which)
    own, foreign = identity.expected_origin(which), identity.expected_origin(other)
    assert native_host.verify_origin(["scribe-host", "--parent-window=1", own])
    assert not native_host.verify_origin(["scribe-host", "--parent-window=1", foreign])


def _chrome_id(key: str) -> str:
    digest = hashlib.sha256(base64.b64decode(key)).digest()
    return "".join(chr(97 + (b >> 4)) + chr(97 + (b & 0xF)) for b in digest[:16])


def _channel_ts_block(source: str, channel: str) -> dict[str, str]:
    match = re.search(rf"^  {channel}: \{{\n(?P<body>.*?)^  \}},$", source, re.DOTALL | re.M)
    assert match is not None, channel
    return dict(re.findall(r'^    (\w+): "([^"]*)",$', match.group("body"), re.M))


@pytest.mark.parametrize(("channel_ts", "which"), [("release", "production"), ("dev", "dev")])
def test_the_extensions_channels_agree_with_these(channel_ts: str, which: Channel) -> None:
    """The extension build's key, id and host name for each channel are
    the ones the desktop side registers and verifies."""
    source = (REPO / "extension" / "src" / "channel.ts").read_text(encoding="utf-8")
    block = _channel_ts_block(source, channel_ts)
    assert block["extensionId"] == identity.extension_id(which)
    assert block["hostName"] == identity.host_name(which)
    assert _chrome_id(block["key"]) == identity.extension_id(which)
