"""Chrome Native Messaging host (`scribe-host`) — plan Step 5.

Trust model (plan Key Design Decision): Chrome's `allowed_origins` pins which
extension may launch this host; the origin argv check here is defence-in-depth,
and the session nonce is a session/correlation IDENTIFIER, not authentication.

Startup contract:
- binary stdio is set before any pipe I/O (executor facts)
- resolved executable/module/cwd paths are logged as a hijack tripwire
- with a missing or unknown origin argv the host exits non-zero BEFORE
  reading stdin (never enters protocol mode)

Critical Constraint: stdout carries ONLY framed protocol bytes.

THE RELAY (Cliniko workflow safeguards plan Task 4.4, D2). Besides the
handshake it answers itself (hello, ping), the host relays between Chrome
and ``scribe-app``'s named pipe:

- Chrome -> app: a ``context`` or ``command`` whose nonce is this session's
  is forwarded with the nonce STRIPPED (the app never sees it); a wrong or
  missing nonce is the same fatal ``bad_nonce`` as for ``ping``. While the
  app is not connected the message is dropped (the extension shows "not
  running" from the state below); a message whose write to the app fails
  or times out is dropped too and ENDS that connection — never retried,
  never followed on the same stream (codex round 28 PR-MED-141; round 30
  PR-MED-161: the link is non-current at once and a retired connection
  refuses every write before any I/O). Only the relay thread closes its
  link — shutdown never does, even on a join timeout (PR-LOW-160).
- app -> Chrome: each ``state`` from the pipe is re-validated and sent with
  this session's nonce STAMPED. Anything else from the pipe ends that
  connection.
- The host originates exactly one message: ``state{app_running:false}``,
  once each time the pipe is absent, and it keeps re-waiting (one bounded
  attempt at a time, ``pipe_client.WAIT_MS``) instead of exiting.
- A pipe that exists but whose server is not verified
  (``pipe_client.ServerUnverified``: the Task 4.3 (b) contract) is a hard
  error: a typed ``error`` to Chrome and exit 1.

Threads: a stdin reader and the relay's pipe thread feed ONE queue that the
main loop drains, and every write to stdout holds one lock. The host exits
on Chrome-side EOF (0) and stops the relay first. Logging records message
types, states and paths only — never a relayed payload (the tripwire drops
any record that would).
"""

from __future__ import annotations

import logging
import os
import queue
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, Final, Protocol

from pydantic import ValidationError

from scribe_desktop.framing import (
    EndOfStream,
    FramingError,
    read_frame,
    set_binary_stdio,
    write_frame,
)
from scribe_desktop.identity import EXPECTED_ORIGIN
from scribe_desktop.logging_setup import log_event, setup_logging
from scribe_desktop.pipe_client import AppPipeConnector, ServerUnverified
from scribe_desktop.protocol import (
    MIN_SUPPORTED_VERSION,
    NONCE_REQUIRED,
    Envelope,
    ErrorCode,
    make_envelope,
    make_error,
    make_pipe_envelope,
    parse_envelope,
    parse_pipe_envelope,
)

# Chrome -> app types the host relays (D2); every other inbound type is
# either answered here (hello, ping) or a violation.
RELAYED_TYPES: Final = frozenset({"context", "command"})
RETRY_S: Final = 1.0
_RELAY_JOIN_S: Final = 5.0
UNVERIFIED_MESSAGE: Final = "the app's pipe failed verification"
RELAY_FAILED_MESSAGE: Final = "the relay to the app failed"
# The one message the host originates (D2).
APP_NOT_RUNNING: Final[dict[str, Any]] = {
    "state_rev": 0,
    "app_running": False,
    "allow_list": [],
    "hotkey": {"available": False},
    "spoken_pause": False,
    "warnings": [],
}


def find_origin(argv: list[str]) -> str | None:
    """Chrome passes the caller origin as a bare argument (`chrome-extension://<id>/`),
    plus `--parent-window=<HWND>` on Windows (executor facts). Tolerate flags;
    return the first chrome-extension origin, or None."""
    for arg in argv[1:]:
        if arg.startswith("chrome-extension://"):
            return arg
    return None


def verify_origin(argv: list[str]) -> bool:
    return find_origin(argv) == EXPECTED_ORIGIN


class SessionViolation(Exception):
    """A protocol-state violation: send the carried error envelope, then disconnect."""

    def __init__(self, error: Envelope) -> None:
        super().__init__(str(error.payload.get("message")))
        self.error = error


@dataclass
class HostSession:
    """Handshake state machine: AWAIT_HELLO -> READY (hello_ack issued)."""

    nonce_factory: Callable[[], str] = field(default=lambda: os.urandom(32).hex())
    session_nonce: str | None = None

    @property
    def ready(self) -> bool:
        return self.session_nonce is not None

    def handle(self, envelope: Envelope) -> Envelope | None:
        """Process one validated inbound envelope; return the reply, or None
        for a ``context``/``command`` the caller relays to the app.

        Raises SessionViolation when the session must terminate.
        """
        if envelope.type == "hello":
            if self.ready:
                raise SessionViolation(
                    make_error(ErrorCode.MALFORMED, "duplicate hello", envelope.request_id)
                )
            # Version negotiation: parse_envelope already enforced the floor;
            # reply with OUR version — the peer decides whether to proceed.
            self.session_nonce = self.nonce_factory()
            return make_envelope(
                "hello_ack",
                payload={},
                request_id=envelope.request_id,
                session_nonce=self.session_nonce,
            )
        if not self.ready:
            raise SessionViolation(
                make_error(ErrorCode.MALFORMED, "message before hello", envelope.request_id)
            )
        if envelope.type == "ping" or envelope.type in RELAYED_TYPES:
            if envelope.session_nonce != self.session_nonce:
                raise SessionViolation(
                    make_error(ErrorCode.BAD_NONCE, "session nonce mismatch", envelope.request_id)
                )
            if envelope.type in RELAYED_TYPES:
                return None
            return make_envelope(
                "pong",
                payload={},
                request_id=envelope.request_id,
                session_nonce=self.session_nonce,
            )
        # pong / hello_ack / error / state are not valid inbound messages for
        # the host (a `state` only ever flows app -> Chrome).
        raise SessionViolation(
            make_error(
                ErrorCode.MALFORMED,
                f"unexpected inbound type {envelope.type}",
                envelope.request_id,
            )
        )


def _classify_raw(raw: object) -> Envelope | None:
    """Pre-validation alignment checks (MED-001): classify violations that
    pydantic would report generically so both mirrors emit the same codes.

    Returns an error envelope to send, or None if no pre-check fires.
    """
    if not isinstance(raw, dict):
        return None
    version = raw.get("protocol_version")
    # A boolean is no version (malformed, as the TypeScript mirror says).
    if (
        isinstance(version, int)
        and not isinstance(version, bool)
        and version < MIN_SUPPORTED_VERSION
    ):
        return make_error(
            ErrorCode.VERSION_BELOW_FLOOR,
            f"protocol_version below supported floor {MIN_SUPPORTED_VERSION}",
        )
    if raw.get("type") in NONCE_REQUIRED and raw.get("session_nonce") is None:
        return make_error(ErrorCode.BAD_NONCE, "required session_nonce missing")
    return None


class ChromeOut:
    """Every frame to Chrome goes through here, under ONE lock (the main
    loop and the relay thread both write; stdout carries only frames)."""

    def __init__(self, stream: BinaryIO, logger: logging.Logger) -> None:
        self._stream = stream
        self._logger = logger
        self._lock = threading.Lock()

    def write(self, envelope: Envelope) -> bool:
        """Write one frame, tolerating a peer that died mid-session (MED-003)."""
        with self._lock:
            try:
                write_frame(self._stream, envelope.model_dump(exclude_none=True))
                return True
            except (OSError, FramingError):
                log_event(self._logger, "write_failed", state="peer_gone")
                return False


class PipeLink(Protocol):
    """One verified connection to the app (``pipe_client.PipeConnection``).
    Only the relay thread — the reader — calls ``close``; any other thread
    ends it with ``retire`` (codex round 28 PR-MED-140/141)."""

    def read_frame(self) -> Any: ...

    def write_frame(self, value: Any) -> bool: ...

    def retire(self) -> None: ...

    def close(self) -> None: ...


class Connector(Protocol):
    """How the relay reaches the app (``pipe_client.AppPipeConnector``):
    ``connect`` makes one bounded attempt — a link, None (absent or busy),
    or ``ServerUnverified``; ``stop`` releases a blocked read."""

    def connect(self) -> PipeLink | None: ...

    def stop(self) -> None: ...


class AppRelay:
    """The pipe side of the host (module docstring, THE RELAY). Its thread
    starts once the handshake has issued the session nonce."""

    def __init__(
        self,
        connector: Connector,
        out: ChromeOut,
        logger: logging.Logger,
        *,
        on_fatal: Callable[[], None],
        retry_s: float = RETRY_S,
    ) -> None:
        self._connector = connector
        self._out = out
        self._logger = logger
        self._on_fatal = on_fatal
        self._retry_s = retry_s
        self._nonce: str | None = None
        self._stopping = threading.Event()
        self._lock = threading.Lock()
        self._link: PipeLink | None = None
        self._thread: threading.Thread | None = None

    def start(self, nonce: str) -> None:
        if self._thread is not None:
            return
        self._nonce = nonce
        self._thread = threading.Thread(target=self._run, name="scribe-host-relay", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = _RELAY_JOIN_S) -> bool:
        """Stop the relay (Chrome has gone). True once its thread has ended.

        The connector's stop releases the relay thread's read; that thread
        then closes its own link once the read has settled (codex round 28
        PR-MED-140: closing it here raced the reader's cancel-and-settle on
        the same handle). This method NEVER closes the link — not even when
        the thread outlives ``timeout`` (codex round 30 PR-LOW-160): then it
        logs and returns False, and the handle is released by its reader
        once the read settles or, at the latest, by Windows at process exit
        (a terminating thread's pending I/O is cancelled and the process's
        handles are closed) — ``run_host`` returns right after this."""
        self._stopping.set()
        self._connector.stop()
        thread = self._thread
        if thread is None:
            return True
        thread.join(timeout)
        if not thread.is_alive():
            return True
        log_event(self._logger, "relay_stop", state="join_timeout")
        return False

    def forward(self, envelope: Envelope) -> None:
        """Chrome -> app (main thread): the same payload, nonce stripped.
        Dropped while the app is not connected."""
        with self._lock:
            link = self._link
        if link is None:
            log_event(self._logger, "relay_dropped", state="app_not_connected")
            return
        stripped = make_pipe_envelope(envelope.type, payload=envelope.payload)
        if not link.write_frame(stripped.model_dump(exclude_none=True)):
            # Codex round 28 PR-MED-141: a failed or timed-out write may have
            # left part of a frame on the pipe, so the stream is no longer
            # trusted — retire the connection (never reuse it, never replay
            # the message). The relay thread closes it, tells Chrome the app
            # is not running and reconnects; the app sees a new connection.
            # Codex round 30 PR-MED-161: the link stops being current AT ONCE
            # — a later message drops as ``app_not_connected`` instead of
            # reaching this stream before the relay thread has ended it (and
            # ``PipeConnection.write_frame`` refuses a retired link anyway).
            log_event(self._logger, "relay_dropped", state="write_failed")
            link.retire()
            with self._lock:
                if self._link is link:
                    self._link = None

    # --- the relay thread ---------------------------------------------------

    def _announce_not_running(self) -> bool:
        """``state{app_running:false}`` to Chrome; False when Chrome has gone."""
        stamped = make_envelope("state", payload=dict(APP_NOT_RUNNING), session_nonce=self._nonce)
        return self._out.write(stamped)

    def _fatal(self, state: str, message: str) -> None:
        log_event(self._logger, "relay_refused", state=state)
        self._out.write(make_error(ErrorCode.INTERNAL, message))
        self._on_fatal()

    def _run(self) -> None:
        announced = False
        while not self._stopping.is_set():
            try:
                link = self._connector.connect()
            except ServerUnverified as exc:
                self._fatal(exc.reason, UNVERIFIED_MESSAGE)
                return
            except Exception as exc:  # noqa: BLE001 - a dead relay must be loud
                self._fatal(f"error_{type(exc).__name__}", RELAY_FAILED_MESSAGE)
                return
            if link is None:
                if not announced:
                    if not self._announce_not_running():
                        return  # Chrome has gone: the main loop exits on its EOF
                    announced = True
                self._stopping.wait(self._retry_s)
                continue
            with self._lock:
                if self._stopping.is_set():
                    link.close()
                    return
                self._link = link
            log_event(self._logger, "relay_connected", state="connected")
            reason = self._pump(link)
            with self._lock:
                self._link = None
            link.close()
            log_event(self._logger, "relay_disconnected", state=reason)
            if self._stopping.is_set() or reason == "chrome_gone":
                return
            if not self._announce_not_running():
                return
            announced = True

    def _pump(self, link: PipeLink) -> str:
        """App -> Chrome until the connection ends; returns why it ended."""
        while True:
            try:
                raw = link.read_frame()
            except EndOfStream:
                return "closed"
            except FramingError:
                return "framing"
            try:
                envelope = parse_pipe_envelope(raw)
            except ValidationError:
                return "malformed"
            if envelope.type != "state":
                return "unexpected_type"
            try:
                stamped = make_envelope(
                    "state", payload=envelope.payload, session_nonce=self._nonce
                )
            except ValidationError:
                return "malformed"
            if not self._out.write(stamped):
                return "chrome_gone"


RelayFactory = Callable[[ChromeOut, Callable[[], None], logging.Logger], AppRelay]


def app_relay_factory(name: str | None = None) -> RelayFactory:
    """The production relay: the per-user pipe (or ``name``, for tests)."""

    def build(out: ChromeOut, on_fatal: Callable[[], None], logger: logging.Logger) -> AppRelay:
        connector = (
            AppPipeConnector.for_current_user(logger=logger)
            if name is None
            else AppPipeConnector(name, logger=logger)
        )
        return AppRelay(connector, out, logger, on_fatal=on_fatal)

    return build


def _read_stdin(stdin: BinaryIO, events: queue.Queue[tuple[str, Any]]) -> None:
    """The stdin thread: every Chrome frame, then how the stream ended."""
    while True:
        try:
            raw = read_frame(stdin)
        except EndOfStream:
            events.put(("eof", None))
            return
        except FramingError as exc:
            events.put(("framing", exc))
            return
        except OSError:
            events.put(("eof", None))
            return
        events.put(("frame", raw))


def run_host(
    stdin: BinaryIO,
    stdout: BinaryIO,
    logger: logging.Logger,
    *,
    relay_factory: RelayFactory | None = None,
) -> int:
    """Protocol loop over already-binary streams. Returns the process exit
    code. With no ``relay_factory`` a ``context``/``command`` is accepted and
    dropped (the handshake-only host of the Phase 1 tests)."""
    out = ChromeOut(stdout, logger)
    events: queue.Queue[tuple[str, Any]] = queue.Queue()
    threading.Thread(
        target=_read_stdin, args=(stdin, events), name="scribe-host-stdin", daemon=True
    ).start()
    relay = (
        relay_factory(out, lambda: events.put(("fatal", None)), logger)
        if relay_factory is not None
        else None
    )
    try:
        return _main_loop(events, out, logger, relay)
    finally:
        if relay is not None:
            relay.stop()


def _main_loop(
    events: queue.Queue[tuple[str, Any]],
    out: ChromeOut,
    logger: logging.Logger,
    relay: AppRelay | None,
) -> int:
    session = HostSession()
    while True:
        kind, value = events.get()
        if kind == "eof":
            log_event(logger, "peer_closed", state="clean_eof")
            return 0
        if kind == "fatal":
            return 1  # the relay has written the error and logged why
        if kind == "framing":
            code = ErrorCode(value.code) if value.code in ErrorCode else ErrorCode.MALFORMED
            out.write(make_error(code, str(value)))
            log_event(logger, "framing_violation", error_code=value.code)
            return 1
        raw = value
        pre_error = _classify_raw(raw)
        if pre_error is not None:
            out.write(pre_error)
            log_event(
                logger, "protocol_violation", error_code=str(pre_error.payload.get("code"))
            )
            return 1
        try:
            envelope = parse_envelope(raw)
        except ValidationError:
            # Never echo the offending content (log whitelisted metadata only).
            out.write(make_error(ErrorCode.MALFORMED, "envelope failed validation"))
            log_event(logger, "protocol_violation", error_code="malformed")
            return 1
        try:
            reply = session.handle(envelope)
        except SessionViolation as exc:
            out.write(exc.error)
            log_event(logger, "session_violation", error_code=str(exc.error.payload.get("code")))
            return 1
        if reply is None:
            if relay is not None:
                relay.forward(envelope)
            else:
                log_event(logger, "relay_dropped", state="no_relay")
        else:
            if not out.write(reply):
                return 1
            if reply.type == "hello_ack" and relay is not None and session.session_nonce:
                relay.start(session.session_nonce)
        log_event(
            logger,
            "message_handled",
            message_type=envelope.type,
            protocol_version=envelope.protocol_version,
        )


def _log_registration_paths(logger: logging.Logger) -> None:
    """Hijack tripwire (MED-007): log the registry-resolved manifest path and
    the launcher path it points at, alongside our own executable paths."""
    if sys.platform != "win32":
        return
    import json
    import winreg

    from scribe_desktop.identity import REGISTRY_KEY

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
            manifest_path, _ = winreg.QueryValueEx(key, "")
        log_event(logger, "host_manifest", path=str(manifest_path))
        launcher = json.loads(Path(manifest_path).read_text(encoding="utf-8")).get("path", "")
        log_event(logger, "host_launcher", path=str(launcher))
    except (OSError, ValueError):
        log_event(logger, "host_manifest", state="unreadable")


def main() -> int:
    logger = setup_logging("scribe-host")
    log_event(logger, "host_start", path=sys.executable, pid=os.getpid())
    log_event(logger, "host_module", path=os.path.abspath(__file__))
    log_event(logger, "host_cwd", path=os.getcwd())
    _log_registration_paths(logger)

    if not verify_origin(sys.argv):
        # Exit BEFORE reading stdin: never enter protocol mode without a
        # valid caller origin (plan Step 5 acceptance criterion).
        log_event(logger, "origin_rejected", state="refused", count=len(sys.argv) - 1)
        return 2

    set_binary_stdio()
    log_event(logger, "origin_verified", state="ok")
    return run_host(
        sys.stdin.buffer, sys.stdout.buffer, logger, relay_factory=app_relay_factory()
    )


if __name__ == "__main__":
    raise SystemExit(main())
