"""Shared test-side helpers: the wire helpers (LOW-002) — the single place
tests build and read native-messaging frames and protocol dicts — the
consent-bearing Start (Cliniko workflow safeguards plan Task 3.3), and the
privacy-professional-controls C6 sentinel for the Windows layer and the
exception hooks (Task 4.1)."""

import io
import json
import struct
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from scribe_desktop import exclusions, install_layout
from scribe_desktop.encounter import unlinked_consent
from scribe_desktop.install_layout import Channel
from scribe_desktop.protocol import PROTOCOL_VERSION

NONCE = "f" * 32

# The real channel and frozen functions, captured before any test pins them,
# for the tests of the functions themselves (test_install_layout.py).
REAL_CHANNEL = install_layout.channel
REAL_IS_FROZEN = install_layout.is_frozen
REAL_MODELS_ROOT = install_layout.models_root


def _production() -> Channel:
    return "production"


def _not_frozen() -> bool:
    return False


def pytest_configure(config: pytest.Config) -> None:
    """Installation plan D2, from before collection: a test module's
    import-time code — a ``skipif`` that looks for a local model, a root
    computed at module level — sees the production channel in a source run
    (not frozen), as every test does (``_production_channel`` re-pins both
    per test; a test child process pins them itself, see
    ``test_integration_no_sockets.py``). Neither is read from ``sys.frozen``
    (C6, round 11 PR-LOW-016)."""
    install_layout.channel = _production  # type: ignore[assignment]
    install_layout.is_frozen = _not_frozen  # type: ignore[assignment]


@pytest.fixture(autouse=True)
def _production_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Installation plan D2, for EVERY test: the channel is pinned to
    production, so the existing tests and pins test what ships (the
    production data folder name, host name, extension id, pipe prefix, and
    no dev write guard). ``is_frozen()`` is pinned to ``False`` — a source
    run, so the models root and the remedies are a source checkout's — and
    never read from the host's ``sys.frozen`` (C6, round 11 PR-LOW-016). A
    test that needs the dev channel calls ``use_channel(monkeypatch, "dev")``;
    one that needs a packaged build calls ``use_frozen(monkeypatch, True)``
    (with the channel too, for the whole scenario). A subprocess a test
    starts is a real source run, so it is the dev channel unless it pins
    itself."""
    use_channel(monkeypatch, "production")
    use_frozen(monkeypatch, False)


def use_channel(monkeypatch: pytest.MonkeyPatch, which: Channel) -> None:
    """Pin ``install_layout.channel()`` to ``which`` for this test."""
    monkeypatch.setattr(install_layout, "channel", lambda: which)


def use_frozen(monkeypatch: pytest.MonkeyPatch, frozen: bool) -> None:
    """Pin ``install_layout.is_frozen()`` to ``frozen`` for this test (it is
    ``False`` unless a test says otherwise; the channel stays as pinned: pin
    both for a packaged-build scenario)."""
    monkeypatch.setattr(install_layout, "is_frozen", lambda: frozen)


def real_ml_models_root() -> Path | None:
    """Installation plan Task 2.6: the ONE models root every real-ML test leg
    — its skip gate, its body and the child processes it starts — loads
    from: a source run's DEV root (``install_layout.models_root("dev")``,
    ``%LOCALAPPDATA%\\ClinikoScribe-dev\\models``), never the production data
    folder (C8), whatever the channel pin. ``None`` when ``LOCALAPPDATA`` is
    unset. Every other test stays on the production pin."""
    try:
        return REAL_MODELS_ROOT("dev")
    except RuntimeError:
        return None


def on_real_ml_root(probe: Callable[[], bool]) -> bool:
    """A real-ML gate's presence ``probe``, run with every model path
    resolving under ``real_ml_models_root()`` (False when there is none).
    Safe at import time (a module-level ``skipif``)."""
    root = real_ml_models_root()
    if root is None:
        return False
    pinned = install_layout.models_root
    install_layout.models_root = lambda of=None: root  # type: ignore[assignment]
    try:
        return probe()
    finally:
        install_layout.models_root = pinned  # type: ignore[assignment]


def real_ml_skip_reason(what: str) -> str:
    """A real-ML gate's skip reason, naming the dev root it looked in."""
    return (
        f"{what} not found under the source run's dev models root "
        f"{real_ml_models_root()} (installation plan Task 2.6: copy or fetch the "
        "models there from a normal terminal)"
    )


@pytest.fixture
def real_ml_models(monkeypatch: pytest.MonkeyPatch) -> Path:
    """For a real-ML leg's BODY (``usefixtures``): every model path resolves
    under ``real_ml_models_root()``, as its gate looked (Task 2.6)."""
    root = real_ml_models_root()
    if root is None:
        pytest.skip("LOCALAPPDATA is not set; no dev models root")
    monkeypatch.setattr(install_layout, "models_root", lambda of=None: root)
    return root


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
