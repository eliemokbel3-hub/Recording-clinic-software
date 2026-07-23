"""Shared test-side wire helpers (LOW-002): the single place tests build and
read native-messaging frames and protocol dicts."""

import io
import json
import struct

NONCE = "f" * 32


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
    return {"protocol_version": 1, "type": "hello", "request_id": request_id, "payload": {}}


def ping(nonce: str, request_id: str = "req-2") -> dict:
    return {
        "protocol_version": 1,
        "type": "ping",
        "request_id": request_id,
        "session_nonce": nonce,
        "payload": {},
    }
