"""Shared test-side helpers: the wire helpers (LOW-002) — the single place
tests build and read native-messaging frames and protocol dicts — the
consent-bearing Start (Cliniko workflow safeguards plan Task 3.3), the
privacy-professional-controls C6 sentinel for the Windows layer and the
exception hooks (Task 4.1), the installation plan's models-root pin
(Task H.6) and inert ML warm-up importer (round 35 MED-001), and the pilot
plan's speech-engine sentinel for the validation-set builder."""

import io
import itertools
import json
import os
import struct
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from scribe_desktop import (
    exclusions,
    install_layout,
    ml_warmup,
    note_config,
    past_sessions,
    replay_kept,
    validation_set,
)
from scribe_desktop.encounter import unlinked_consent
from scribe_desktop.install_layout import Channel
from scribe_desktop.protocol import PROTOCOL_VERSION

NONCE = "f" * 32

# The real channel and frozen functions, captured before any test pins them,
# for the tests of the functions themselves (test_install_layout.py).
REAL_CHANNEL = install_layout.channel
REAL_IS_FROZEN = install_layout.is_frozen
REAL_MODELS_ROOT = install_layout.models_root
# Pilot plan Task 1.1: the real pilot-settings resolver, for its own test.
REAL_PILOT_SETTINGS_ROOT = note_config.pilot_settings_root
# Development-recordings plan Task 1.1: the real development-settings
# resolver, for its own test.
REAL_DEVELOPMENT_SETTINGS_ROOT = note_config.development_settings_root
# Codex round 27 PR-LOW-001: the real ``.part`` kernel seam, captured before
# ``pytest_configure`` replaces it with ``_no_real_part_kernel``.
REAL_PART_KERNEL = past_sessions.part_kernel
# Development-recordings plan Task 4.1a: the replay tool's real instance
# exclusion (the app's production ``app.lock``), captured before
# ``pytest_configure`` replaces it with ``_no_real_exclusion``.
REAL_REPLAY_EXCLUSION = replay_kept._acquire_exclusion


def _production() -> Channel:
    return "production"


def _not_frozen() -> bool:
    return False


def _no_real_part_kernel() -> past_sessions.PartKernel:
    raise AssertionError(
        "a test reached the real Win32PartKernel (C6) - keep the conftest "
        "part_kernel fixture in place (scope patches with monkeypatch.context())"
    )


def _no_real_exclusion() -> replay_kept.ExclusionLike:
    raise AssertionError(
        "a test reached the replay tool's real instance exclusion (the app's "
        "app.lock) - replace replay_kept._acquire_exclusion in the test"
    )


def pytest_configure(config: pytest.Config) -> None:
    """Installation plan D2, from before collection: a test module's
    import-time code — a ``skipif`` that looks for a local model, a root
    computed at module level — sees the production channel in a source run
    (not frozen), as every test does (``_production_channel`` re-pins both
    per test; a test child process pins them itself, see
    ``test_integration_no_sockets.py``). Neither is read from ``sys.frozen``
    (C6, round 11 PR-LOW-016). The export's ``.part`` kernel seam is replaced
    for the whole run by a refusal (codex round 27 PR-LOW-001): a test that
    lifts the ``part_kernel`` fixture with ``monkeypatch.undo()`` fails
    loudly instead of reaching the real Windows API. So is the replay tool's
    instance exclusion (development-recordings plan Task 4.1a): no test ever
    takes the app's real ``app.lock``."""
    install_layout.channel = _production  # type: ignore[assignment]
    install_layout.is_frozen = _not_frozen  # type: ignore[assignment]
    past_sessions.part_kernel = _no_real_part_kernel
    replay_kept._acquire_exclusion = _no_real_exclusion


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
def pinned_pilot_root(
    monkeypatch: pytest.MonkeyPatch, models_root_factory: Callable[[], Path]
) -> Path:
    """Pilot plan Task 1.1 (Constraint 9), for EVERY test: the default root of
    ``config\\pilot.json`` (``note_config.pilot_settings_root``) is a fresh,
    EMPTY folder of the test's own, so every window a test builds reads shadow
    mode OFF unless the test writes the file there (or passes its own config
    root) — no test reads or writes the host's own pilot setting. Returns the
    pinned root."""
    root = models_root_factory()
    monkeypatch.setattr(note_config, "pilot_settings_root", lambda: root)
    return root


@pytest.fixture(autouse=True)
def pinned_development_root(
    monkeypatch: pytest.MonkeyPatch, models_root_factory: Callable[[], Path]
) -> Path:
    """Development-recordings plan Task 1.1 (C9), for EVERY test: the default
    root of ``config\\development.json``
    (``note_config.development_settings_root``) is a fresh, EMPTY folder of
    the test's own, exactly as ``pinned_pilot_root`` pins ``pilot.json`` — so
    every window a test builds reads "keep recordings" OFF unless the test
    writes the file there (or passes its own config root), and no test reads
    or writes the host's own setting. Returns the pinned root."""
    root = models_root_factory()
    monkeypatch.setattr(note_config, "development_settings_root", lambda: root)
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


class FsPartKernel:
    """The test double of ``past_sessions.PartKernel`` (codex round 24
    PR-MED-001; C6): the same contract over the test's own files with plain
    ``os`` calls — ``open`` refuses an absent file (or folder) with
    ``FileNotFoundError``, ``status`` is the path's ``lstat`` (a link reads
    as itself), and a file marked for deletion is unlinked when it is
    closed. ``refuse_open`` / ``refuse_delete`` make a test's Windows say
    no; ``swap_after_status`` replaces the file at the path after its
    identity was read (what a same-handle delete must survive)."""

    def __init__(self) -> None:
        self.refuse_open = False
        self.refuse_delete = False
        self.swap_after_status: bytes | None = None
        self._open: dict[int, Path] = {}
        self._marked: set[int] = set()
        self._next = itertools.count(1000)

    def open(self, path: Path) -> int:
        os.lstat(path)  # FileNotFoundError when it, or its folder, is absent
        if self.refuse_open:
            raise PermissionError(13, "in use")
        descriptor = next(self._next)
        self._open[descriptor] = path
        return descriptor

    def status(self, descriptor: int) -> os.stat_result:
        path = self._open[descriptor]
        status = os.lstat(path)
        if self.swap_after_status is not None:
            # The same handle still names the ORIGINAL file: a real
            # exclusive handle refuses the swap, so the double keeps the
            # identity it read and leaves the new file at the path alone.
            path.unlink()
            path.write_bytes(self.swap_after_status)
            self._open[descriptor] = path.with_name(path.name + ".swapped-away")
        return status

    def mark_deleted(self, descriptor: int) -> None:
        if self.refuse_delete:
            raise PermissionError(5, "access denied")
        self._marked.add(descriptor)

    def close(self, descriptor: int) -> None:
        path = self._open.pop(descriptor)
        if descriptor in self._marked:
            self._marked.discard(descriptor)
            path.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def part_kernel(monkeypatch: pytest.MonkeyPatch) -> FsPartKernel:
    """Codex round 24 PR-MED-001 (C6), for EVERY test: the export's
    same-handle removal runs on ``FsPartKernel``, never the real Windows
    API; a test takes this fixture to make it refuse."""
    kernel = FsPartKernel()
    monkeypatch.setattr(past_sessions, "part_kernel", lambda: kernel)
    return kernel


@pytest.fixture(autouse=True)
def _no_real_speech_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    """Pilot plan Constraint 9 (round 11 MED-005), for EVERY test: the set
    builder's real Windows voice list and synthesizer refuse, so a builder
    test must inject both seams (``build_set`` / ``main`` look the defaults
    up at call time, so this pin covers an omitted argument). The refusal
    can be caught by the builder's own per-script handler, so every call is
    also RECORDED and fails the test at teardown (round 12 LOW-010, as
    ``_no_real_windows_layer`` does for the exception hooks); the one test
    that reaches them on purpose clears the record it is handed. The shared
    SAPI fixture leg (``sapi_fixture``) does not go through them."""
    reached: list[str] = []

    def refusing(name: str) -> Callable[..., Any]:
        def refuse(*args: object, **kwargs: object) -> Any:
            reached.append(name)
            raise AssertionError(
                "a test reached the real speech engine (Constraint 9) - inject voices= and "
                "synthesize="
            )

        return refuse

    monkeypatch.setattr(validation_set, "sapi_voices", refusing("sapi_voices"))
    monkeypatch.setattr(validation_set, "sapi_synthesize", refusing("sapi_synthesize"))
    yield reached
    if reached:
        pytest.fail(f"a test reached the real speech engine: {', '.join(reached)} (Constraint 9)")


class InertWarmup:
    """An ``ImportWarmup`` that does nothing and is always finished — for an
    ``app.main`` test that does not test the warm-up itself (no thread, no
    offline-environment check)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def start(self) -> None:
        pass

    def is_finished(self) -> bool:
        return True

    def holds_start(self) -> bool:
        return False


class _InertModule:
    """What the pinned warm-up importer hands back: onnxruntime's one call."""

    def disable_telemetry_events(self) -> None:
        pass


@pytest.fixture(autouse=True)
def _no_real_ml_warmup_imports(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Installation plan round 35 MED-001 (C6), for EVERY test (every
    ``app.main`` test starts the warm-up): the warm-up's default importer
    records the module names and imports nothing, so no test depends on
    whether the ML stack is installed. A test of the warm-up passes its own
    importer. Returns the recorded names."""
    imported: list[str] = []

    def record(name: str) -> Any:
        imported.append(name)
        return _InertModule()

    monkeypatch.setattr(ml_warmup, "_import_module", record)
    return imported


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
