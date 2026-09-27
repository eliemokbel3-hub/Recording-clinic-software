"""Shared test-side helpers: the wire helpers (LOW-002) — the single place
tests build and read native-messaging frames and protocol dicts — and the
consent-bearing Start (Cliniko workflow safeguards plan Task 3.3)."""

import io
import json
import struct
from typing import Any

from scribe_desktop.encounter import unlinked_consent
from scribe_desktop.protocol import PROTOCOL_VERSION

NONCE = "f" * 32


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
