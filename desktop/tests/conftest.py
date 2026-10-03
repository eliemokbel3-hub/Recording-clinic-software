"""Shared test-side helpers: the wire helpers (LOW-002) — the single place
tests build and read native-messaging frames and protocol dicts — the
consent-bearing Start (Cliniko workflow safeguards plan Task 3.3), the
privacy-professional-controls C6 sentinel for the Windows layer and the
exception hooks (Task 4.1), and the installation plan's models-root pin
(Task H.6)."""

import io
import itertools
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


def use_models_root(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """Pin ``install_layout.models_root()`` to ``root`` for this test, in
    place of the conftest's empty folder (``pinned_models_root``) — a network
    root, for a test that a default model path refuses one."""
    monkeypatch.setattr(install_layout, "models_root", lambda of=None: root)


def real_ml_models_root() -> Path | None:
    """Installation plan Task 2.6: the ONE models root every real-ML test leg
    — its skip gate, its body and the child processes it starts — loads
    from: a source run's DEV root (``install_layout.models_root("dev")``,
    ``%LOCALAPPDATA%\\ClinikoScribe-dev\\models``), never the production data
    folder (C8), whatever the channel pin. ``None`` when ``LOCALAPPDATA`` is
    unset. Every other test resolves under its own empty folder
    (``pinned_models_root``, Task H.6)."""
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


@pytest.fixture(scope="session")
def models_root_factory(tmp_path_factory: pytest.TempPathFactory) -> Callable[[], Path]:
    """One numbered ``models`` folder per session under pytest's base
    temporary folder, and a new empty child of it per call (a ``mktemp`` per
    test would rescan the whole base folder every time)."""
    parent = tmp_path_factory.mktemp("models")
    numbers = itertools.count()

    def fresh() -> Path:
        root = parent / str(next(numbers))
        root.mkdir()
        return root

    return fresh


@pytest.fixture(autouse=True)
def pinned_models_root(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    models_root_factory: Callable[[], Path],
) -> Path | None:
    """Installation plan Task H.6 (round 27 PR-MED-022, C6), for EVERY test:
    ``install_layout.models_root()`` — the one resolver behind every model
    path (``benchmark.default_models_root`` and the VAD, whisper, language
    and speaker model paths read it at call time) — is pinned to a fresh,
    EMPTY folder of the test's own, outside its ``tmp_path``, so no test
    stats the host's models folder (full on the development computer, empty
    on CI). A model is
    absent unless the test writes one under ``install_layout.models_root()``.
    A real-ML leg's ``real_ml_models`` pin lands after this one and wins
    (``on_real_ml_root`` restores this pin after its probe). Only the
    resolver's own tests opt out, by class or function, with
    ``@pytest.mark.real_models_root``: they drive ``LOCALAPPDATA`` or the
    install folder and need the real function. Returns the pinned root, or
    ``None`` for a marked test."""
    if request.node.get_closest_marker("real_models_root") is not None:
        return None
    root = models_root_factory()
    use_models_root(monkeypatch, root)
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


NETWORK_IO_METHODS: tuple[str, ...] = (
    "exists",
    "is_file",
    "is_dir",
    "stat",
    "open",
    "read_text",
    "read_bytes",
    "iterdir",
)


def forbid_network_io(monkeypatch: pytest.MonkeyPatch) -> None:
    """Installation plan round 28 PR-LOW-030: for a network-refusal test,
    each ``pathlib.Path`` method in ``NETWORK_IO_METHODS`` RAISES on a network
    path (``install_layout.is_unc_path``) before it reaches the filesystem,
    so a regressed guard whose I/O goes through one of those methods fails
    the test with no SMB I/O; local paths (the test's own ``tmp_path``
    files) pass through.

    Round 30 PR-LOW-034 — what it does NOT cover: direct ``os`` calls
    (``os.stat``, ``os.path.*``), the built-in ``open``, ``Path`` methods not
    listed, and a native library handed a ``str`` path (CTranslate2,
    onnxruntime, llama.cpp — each test stubs that import or factory
    instead). Today every guarded function's post-guard file access is a
    listed method."""
    import pathlib

    for method in NETWORK_IO_METHODS:
        real = getattr(pathlib.Path, method)

        def guarded(
            self: pathlib.Path, *args: Any, _real: Any = real, _method: str = method, **kwargs: Any
        ) -> Any:
            if install_layout.is_unc_path(self):
                raise AssertionError(f"Path.{_method} reached a network path: {self}")
            return _real(self, *args, **kwargs)

        monkeypatch.setattr(pathlib.Path, method, guarded)


def record_path_io(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """Installation plan Task H.6: every path a ``pathlib.Path`` method in
    ``NETWORK_IO_METHODS`` is called on, in order; each call then goes
    through unchanged. Same coverage limits as ``forbid_network_io``."""
    import pathlib

    seen: list[Path] = []
    for method in NETWORK_IO_METHODS:
        real = getattr(pathlib.Path, method)

        def recording(self: pathlib.Path, *args: Any, _real: Any = real, **kwargs: Any) -> Any:
            seen.append(self)
            return _real(self, *args, **kwargs)

        monkeypatch.setattr(pathlib.Path, method, recording)
    return seen


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
