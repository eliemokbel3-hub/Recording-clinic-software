"""Message protocol — hand-mirrored from the canonical fixtures.

The canonical contract lives in `protocol/fixtures/` (plan Key Design
Decision: fixtures-canonical protocol). This module and the TypeScript
mirror (`extension/src/protocol.ts`) are both validated against the same
fixture files; drift is a test failure.

Envelope: protocol_version, type, request_id?, session_nonce?, payload.
Per-type nonce rules: hello forbids it; hello_ack/ping/pong require it;
error allows it. Versions below MIN_SUPPORTED_VERSION are rejected.
"""

from __future__ import annotations

import enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PROTOCOL_VERSION = 1
MIN_SUPPORTED_VERSION = 1
HOST_NAME = "com.scribe.cliniko_host"
# Project policy bound, both directions (platform allows more Chrome->host).
MAX_FRAME_BYTES = 1_048_576

MessageType = Literal["hello", "hello_ack", "ping", "pong", "error"]

# Messages that must NOT carry a session_nonce / that MUST carry one.
NONCE_FORBIDDEN: frozenset[str] = frozenset({"hello"})
NONCE_REQUIRED: frozenset[str] = frozenset({"hello_ack", "ping", "pong"})


class ErrorCode(enum.StrEnum):
    VERSION_BELOW_FLOOR = "version_below_floor"
    BAD_NONCE = "bad_nonce"
    MALFORMED = "malformed"
    OVERSIZED = "oversized"
    INTERNAL = "internal"


class ConnectionState(enum.StrEnum):
    """Phase-1 throwaway connection state (NOT PLAN.md's SessionState —
    that arrives with Phase 2's recording lifecycle; see plan Deferred)."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class Envelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    protocol_version: int = Field(ge=1)
    type: MessageType
    request_id: str | None = Field(default=None, min_length=1, max_length=128)
    session_nonce: str | None = Field(default=None, min_length=16, max_length=128)
    payload: dict[str, Any]

    @model_validator(mode="after")
    def _check_rules(self) -> Envelope:
        if self.protocol_version < MIN_SUPPORTED_VERSION:
            raise ValueError(
                f"protocol_version {self.protocol_version} is below the "
                f"supported floor {MIN_SUPPORTED_VERSION}"
            )
        if self.type in NONCE_FORBIDDEN and self.session_nonce is not None:
            raise ValueError(f"{self.type} must not carry a session_nonce")
        if self.type in NONCE_REQUIRED and self.session_nonce is None:
            raise ValueError(f"{self.type} requires a session_nonce")
        if self.type == "error":
            code = self.payload.get("code")
            message = self.payload.get("message")
            if not isinstance(code, str) or code not in {c.value for c in ErrorCode}:
                raise ValueError("error payload requires a known code")
            if not isinstance(message, str) or not message:
                raise ValueError("error payload requires a message")
        return self


def parse_envelope(data: Any) -> Envelope:
    """Validate an already-decoded JSON value into an Envelope.

    Raises pydantic.ValidationError on any contract violation.
    """
    return Envelope.model_validate(data)


def make_error(code: ErrorCode, message: str, request_id: str | None = None) -> Envelope:
    return Envelope(
        protocol_version=PROTOCOL_VERSION,
        type="error",
        request_id=request_id,
        payload={"code": code.value, "message": message},
    )
