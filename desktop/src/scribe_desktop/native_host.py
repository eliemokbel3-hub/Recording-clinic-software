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
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

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
from scribe_desktop.protocol import (
    MIN_SUPPORTED_VERSION,
    NONCE_REQUIRED,
    Envelope,
    ErrorCode,
    make_envelope,
    make_error,
    parse_envelope,
)


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

    def handle(self, envelope: Envelope) -> Envelope:
        """Process one validated inbound envelope; return the reply.

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
        if envelope.type == "ping":
            if envelope.session_nonce != self.session_nonce:
                raise SessionViolation(
                    make_error(ErrorCode.BAD_NONCE, "session nonce mismatch", envelope.request_id)
                )
            return make_envelope(
                "pong",
                payload={},
                request_id=envelope.request_id,
                session_nonce=self.session_nonce,
            )
        # pong / hello_ack / error are not valid inbound messages for the host.
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
    if isinstance(version, int) and version < MIN_SUPPORTED_VERSION:
        return make_error(
            ErrorCode.VERSION_BELOW_FLOOR,
            f"protocol_version below supported floor {MIN_SUPPORTED_VERSION}",
        )
    if raw.get("type") in NONCE_REQUIRED and raw.get("session_nonce") is None:
        return make_error(ErrorCode.BAD_NONCE, "required session_nonce missing")
    return None


def _safe_write(stdout: BinaryIO, envelope: Envelope, logger: logging.Logger) -> bool:
    """Write a reply, tolerating a peer that died mid-session (MED-003)."""
    try:
        write_frame(stdout, envelope.model_dump(exclude_none=True))
        return True
    except (OSError, FramingError):
        log_event(logger, "write_failed", state="peer_gone")
        return False


def run_host(stdin: BinaryIO, stdout: BinaryIO, logger: logging.Logger) -> int:
    """Protocol loop over already-binary streams. Returns the process exit code."""
    session = HostSession()
    while True:
        try:
            raw = read_frame(stdin)
        except EndOfStream:
            log_event(logger, "peer_closed", state="clean_eof")
            return 0
        except FramingError as exc:
            code = ErrorCode(exc.code) if exc.code in ErrorCode else ErrorCode.MALFORMED
            _safe_write(stdout, make_error(code, str(exc)), logger)
            log_event(logger, "framing_violation", error_code=exc.code)
            return 1
        pre_error = _classify_raw(raw)
        if pre_error is not None:
            _safe_write(stdout, pre_error, logger)
            log_event(
                logger, "protocol_violation", error_code=str(pre_error.payload.get("code"))
            )
            return 1
        try:
            envelope = parse_envelope(raw)
        except ValidationError:
            # Never echo the offending content (log whitelisted metadata only).
            reply_error = make_error(ErrorCode.MALFORMED, "envelope failed validation")
            _safe_write(stdout, reply_error, logger)
            log_event(logger, "protocol_violation", error_code="malformed")
            return 1
        try:
            reply = session.handle(envelope)
        except SessionViolation as exc:
            _safe_write(stdout, exc.error, logger)
            log_event(logger, "session_violation", error_code=str(exc.error.payload.get("code")))
            return 1
        if not _safe_write(stdout, reply, logger):
            return 1
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
    return run_host(sys.stdin.buffer, sys.stdout.buffer, logger)


if __name__ == "__main__":
    raise SystemExit(main())
