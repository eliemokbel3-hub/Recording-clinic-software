"""Shared test-side helpers: the wire helpers (LOW-002) — the single place
tests build and read native-messaging frames and protocol dicts — the
consent-bearing Start (Cliniko workflow safeguards plan Task 3.3), and the
privacy-professional-controls C6 sentinel for the Windows layer and the
exception hooks (Task 4.1)."""

import io
import json
import struct
from collections.abc import Iterator
from typing import Any

import pytest

from scribe_desktop import exclusions
from scribe_desktop.encounter import unlinked_consent
from scribe_desktop.protocol import PROTOCOL_VERSION

NONCE = "f" * 32


@pytest.fixture(autouse=True)
def _no_real_windows_layer(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """C6, for EVERY test (every ``MainWindow`` and ``app.main`` test
    included): building the real ``Win32WindowsLayer`` — the registry, WER,
    ``%LOCALAPPDATA%`` and file-attribute calls — fails the test loudly, so
    a test must inject a fake. The class itself is patched, so every import
    binding of it is covered. And a test that leaves one of the app's
    exception hooks installed (``app.main`` installs them; a test must patch
    ``install_exception_hooks`` or restore inside its own fixture) fails at
    teardown — after the hooks are unwound, so the next test runs with
    pytest's own."""

    def refuse(self: object, *args: object, **kwargs: object) -> None:
        raise AssertionError(
            "a test reached the real Win32WindowsLayer (C6) - inject a fake WindowsLayer"
        )

    monkeypatch.setattr(exclusions.Win32WindowsLayer, "__init__", refuse)
    yield
    if exclusions.remove_exception_hooks():
        pytest.fail("a test left the app's exception hooks installed (C6)")


def bounded_read_spy(monkeypatch: pytest.MonkeyPatch, name: str) -> list[int]:
    """Privacy-professional-controls round 37 PR-LOW-031: record the size
    every ``read`` asks for on a binary stream opened (``Path.open("rb")``)
    for a file called ``name``; an UNBOUNDED read (no size, or a negative
    one — what ``Path.read_bytes`` does) fails the test before anything is
    read. A size-cap test asserts on the recorded sizes, so a reader reverted
    to a whole-file read fails even where its oversized fixture would also
    fail authentication or parsing. Only ``tmp_path`` files are opened (C6)."""
    import pathlib

    sizes: list[int] = []
    real_open = pathlib.Path.open

    class _Spy:
        def __init__(self, stream: Any) -> None:
            self._stream = stream

        def __enter__(self) -> "_Spy":
            return self

        def __exit__(self, *exc: object) -> None:
            self._stream.close()

        def read(self, size: int | None = -1) -> bytes:
            if size is None or size < 0:
                raise AssertionError(f"an unbounded read of {name}")
            sizes.append(size)
            return self._stream.read(size)

        def __getattr__(self, attr: str) -> Any:
            return getattr(self._stream, attr)

    def spying_open(self: pathlib.Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        stream = real_open(self, mode, *args, **kwargs)
        return _Spy(stream) if self.name == name and mode == "rb" else stream

    monkeypatch.setattr(pathlib.Path, "open", spying_open)
    return sizes


def start_unlinked(controller: Any, device_id: int = 0) -> Any:
    """``controller.start`` as a desktop Start: an UNLINKED recording with a
    fresh consent attestation (Constraint 4 — start() refuses without one)."""
    return controller.start(device_id, consent=unlinked_consent())


def frame(value: object) -> bytes:
    body = json.dumps(value).encode("utf-8")
    return struct.pack("=I", len(body)) + body


def read_frames(data: bytes) -> list[dict]:
    stream = io.BytesIO(data)
    frames: list[dict] = []
    while True:
        prefix = stream.read(4)
        if not prefix:
            return frames
        (length,) = struct.unpack("=I", prefix)
        frames.append(json.loads(stream.read(length).decode("utf-8")))


def hello(request_id: str = "req-1") -> dict:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "type": "hello",
        "request_id": request_id,
        "payload": {},
    }


def ping(nonce: str, request_id: str = "req-2") -> dict:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "type": "ping",
        "request_id": request_id,
        "session_nonce": nonce,
        "payload": {},
    }
