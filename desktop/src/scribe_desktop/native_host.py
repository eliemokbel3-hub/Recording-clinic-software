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

import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import BinaryIO

from pydantic import ValidationError

from scribe_desktop.framing import (
    EndOfStream,
    FramingError,
    read_frame,
    set_binary_stdio,
    write_frame,
)
from scribe_desktop.logging_setup import log_event, setup_logging
from scribe_desktop.protocol import (
    PROTOCOL_VERSION,
    Envelope,
    ErrorCode,
    make_error,
    parse_envelope,
)

# Pinned extension identity — see extension/KEY.md (plan Step 3).
EXTENSION_ID = "mbmhglgadhdohpgbmpbjnaifjagfdfid"
EXPECTED_ORIGIN = f"chrome-extension://{EXTENSION_ID}/"


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
            return Envelope(
                protocol_version=PROTOCOL_VERSION,
                type="hello_ack",
                request_id=envelope.request_id,
                session_nonce=self.session_nonce,
                payload={},
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
            return Envelope(
                protocol_version=PROTOCOL_VERSION,
                type="pong",
                request_id=envelope.request_id,
                session_nonce=self.session_nonce,
                payload={},
            )
        # pong / hello_ack / error are not valid inbound messages for the host.
        raise SessionViolation(
            make_error(
                ErrorCode.MALFORMED,
                f"unexpected inbound type {envelope.type}",
                envelope.request_id,
            )
        )


def run_host(stdin: BinaryIO, stdout: BinaryIO, logger_name: str = "scribe-host") -> int:
    """Protocol loop over already-binary streams. Returns the process exit code."""
    logger = setup_logging(logger_name)
    session = HostSession()
    while True:
        try:
            raw = read_frame(stdin)
        except EndOfStream:
            log_event(logger, "peer_closed", state="clean_eof")
            return 0
        except FramingError as exc:
            code = ErrorCode(exc.code) if exc.code in ErrorCode else ErrorCode.MALFORMED
            write_frame(stdout, make_error(code, str(exc)).model_dump(exclude_none=True))
            log_event(logger, "framing_violation", error_code=exc.code)
            return 1
        try:
            envelope = parse_envelope(raw)
        except ValidationError:
            # Never echo the offending content (log whitelisted metadata only).
            write_frame(
                stdout,
                make_error(ErrorCode.MALFORMED, "envelope failed validation").model_dump(
                    exclude_none=True
                ),
            )
            log_event(logger, "protocol_violation", error_code="malformed")
            return 1
        try:
            reply = session.handle(envelope)
        except SessionViolation as exc:
            write_frame(stdout, exc.error.model_dump(exclude_none=True))
            log_event(logger, "session_violation", error_code=str(exc.error.payload.get("code")))
            return 1
        write_frame(stdout, reply.model_dump(exclude_none=True))
        log_event(
            logger,
            "message_handled",
            message_type=envelope.type,
            protocol_version=envelope.protocol_version,
        )


def main() -> int:
    logger = setup_logging("scribe-host")
    log_event(logger, "host_start", path=sys.executable, pid=os.getpid())
    log_event(logger, "host_module", path=os.path.abspath(__file__))
    log_event(logger, "host_cwd", path=os.getcwd())

    if not verify_origin(sys.argv):
        # Exit BEFORE reading stdin: never enter protocol mode without a
        # valid caller origin (plan Step 5 acceptance criterion).
        log_event(logger, "origin_rejected", state="refused", count=len(sys.argv) - 1)
        return 2

    set_binary_stdio()
    log_event(logger, "origin_verified", state="ok")
    return run_host(sys.stdin.buffer, sys.stdout.buffer)


if __name__ == "__main__":
    raise SystemExit(main())
