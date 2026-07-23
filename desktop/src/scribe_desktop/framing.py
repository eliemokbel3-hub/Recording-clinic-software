"""Native-messaging stdio framing (plan Step 4).

Frame format: 4-byte native-byte-order unsigned length prefix + UTF-8 JSON
(executor facts: native order resolves to little-endian on our x64 target).
Project policy bounds frames at MAX_FRAME_BYTES in BOTH directions — the
platform allows more Chrome->host, but this codebase never accepts it.

Windows binary-stdio fix (the classic native-host killer): text-mode stdio
translates \\n to \\r\\n and corrupts frames. `set_binary_stdio()` must be
called once at host startup, and all I/O goes through the `.buffer` streams.

Critical Constraint: an oversized DECLARED length is rejected WITHOUT
allocating the buffer.
"""

from __future__ import annotations

import json
import struct
import sys
from typing import Any, BinaryIO

from scribe_desktop.protocol import MAX_FRAME_BYTES

_LENGTH = struct.Struct("=I")  # 4-byte native-order unsigned


class FramingError(Exception):
    """Raised on any framing-level violation; carries a protocol error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class EndOfStream(Exception):
    """Clean EOF before a length prefix — the peer closed the pipe."""


def set_binary_stdio() -> None:
    """Put stdin/stdout into binary mode on Windows (no-op elsewhere)."""
    if sys.platform == "win32":
        import msvcrt
        import os

        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)


def _read_exact(stream: BinaryIO, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            raise FramingError("malformed", "stream truncated mid-frame")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_frame(stream: BinaryIO) -> Any:
    """Read one frame; returns the decoded JSON value.

    Raises EndOfStream on clean EOF, FramingError on any violation.
    Handles back-to-back frames naturally (reads exactly one frame's bytes).
    """
    prefix = stream.read(_LENGTH.size)
    if prefix == b"":
        raise EndOfStream()
    if len(prefix) < _LENGTH.size:
        raise FramingError("malformed", "truncated length prefix")
    (length,) = _LENGTH.unpack(prefix)
    if length > MAX_FRAME_BYTES:
        # Reject BEFORE allocating (a 4-byte prefix can declare ~4 GB).
        raise FramingError("oversized", f"declared frame length {length} exceeds policy bound")
    if length == 0:
        raise FramingError("malformed", "zero-length frame")
    body = _read_exact(stream, length)
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FramingError("malformed", "frame body is not valid UTF-8") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise FramingError("malformed", "frame body is not valid JSON") from exc


def write_frame(stream: BinaryIO, value: Any) -> None:
    """Encode and write one frame, enforcing the policy bound."""
    body = json.dumps(value, separators=(",", ":")).encode("utf-8")
    if len(body) > MAX_FRAME_BYTES:
        raise FramingError("oversized", f"outgoing frame of {len(body)} bytes exceeds policy bound")
    stream.write(_LENGTH.pack(len(body)))
    stream.write(body)
    stream.flush()
