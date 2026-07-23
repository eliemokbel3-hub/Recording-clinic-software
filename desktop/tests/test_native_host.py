"""Step 5: handshake state machine + origin verification + protocol-loop tests."""

import io
import json
import struct
from pathlib import Path

import pytest

from scribe_desktop.native_host import (
    EXPECTED_ORIGIN,
    HostSession,
    SessionViolation,
    find_origin,
    run_host,
    verify_origin,
)
from scribe_desktop.protocol import parse_envelope

NONCE = "f" * 32


def make_session() -> HostSession:
    return HostSession(nonce_factory=lambda: NONCE)


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


def frame(value: dict) -> bytes:
    body = json.dumps(value).encode()
    return struct.pack("=I", len(body)) + body


def read_frames(data: bytes) -> list[dict]:
    stream = io.BytesIO(data)
    frames = []
    while True:
        prefix = stream.read(4)
        if not prefix:
            return frames
        (length,) = struct.unpack("=I", prefix)
        frames.append(json.loads(stream.read(length).decode()))


# --- origin verification -------------------------------------------------


def test_origin_found_among_flags() -> None:
    argv = ["scribe-host", "--parent-window=123456", EXPECTED_ORIGIN]
    assert find_origin(argv) == EXPECTED_ORIGIN
    assert verify_origin(argv)


def test_origin_missing_rejected() -> None:
    assert not verify_origin(["scribe-host"])
    assert not verify_origin(["scribe-host", "--parent-window=1"])


def test_origin_unknown_extension_rejected() -> None:
    assert not verify_origin(["scribe-host", "chrome-extension://" + "a" * 32 + "/"])


def test_main_refuses_without_origin_before_reading_stdin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Acceptance criterion: exit non-zero BEFORE touching stdin."""
    import scribe_desktop.native_host as nh

    class ExplodingStdin:
        buffer = property(lambda self: (_ for _ in ()).throw(AssertionError("stdin was read")))

    monkeypatch.setattr(nh.sys, "argv", ["scribe-host"])
    monkeypatch.setattr(nh.sys, "stdin", ExplodingStdin())
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert nh.main() == 2


# --- handshake state machine --------------------------------------------


def test_happy_path_hello_then_ping() -> None:
    session = make_session()
    ack = session.handle(parse_envelope(hello()))
    assert ack.type == "hello_ack"
    assert ack.session_nonce == NONCE
    assert ack.request_id == "req-1"
    pong = session.handle(parse_envelope(ping(NONCE)))
    assert pong.type == "pong"
    assert pong.session_nonce == NONCE
    assert pong.request_id == "req-2"


def test_ping_before_hello_violates() -> None:
    session = make_session()
    with pytest.raises(SessionViolation) as exc:
        session.handle(parse_envelope(ping(NONCE)))
    assert exc.value.error.payload["code"] == "malformed"


def test_wrong_nonce_violates() -> None:
    session = make_session()
    session.handle(parse_envelope(hello()))
    with pytest.raises(SessionViolation) as exc:
        session.handle(parse_envelope(ping("0" * 32)))
    assert exc.value.error.payload["code"] == "bad_nonce"


def test_duplicate_hello_violates() -> None:
    session = make_session()
    session.handle(parse_envelope(hello()))
    with pytest.raises(SessionViolation) as exc:
        session.handle(parse_envelope(hello("req-9")))
    assert exc.value.error.payload["code"] == "malformed"


def test_inbound_pong_violates() -> None:
    session = make_session()
    session.handle(parse_envelope(hello()))
    bad = {
        "protocol_version": 1,
        "type": "pong",
        "request_id": "r",
        "session_nonce": NONCE,
        "payload": {},
    }
    with pytest.raises(SessionViolation):
        session.handle(parse_envelope(bad))


# --- protocol loop over pipes -------------------------------------------


def run(data: bytes, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[int, list[dict]]:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    out = io.BytesIO()
    code = run_host(io.BytesIO(data), out, logger_name="scribe-host-test")
    return code, read_frames(out.getvalue())


def test_loop_full_handshake_then_eof(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code, frames = run(frame(hello()), tmp_path, monkeypatch)
    assert code == 0
    assert [f["type"] for f in frames] == ["hello_ack"]


def test_loop_foreign_nonce_gets_typed_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The loop issues a random nonce; a ping with a foreign nonce must produce
    hello_ack then a typed bad_nonce error and exit 1. (The full hello->ping
    happy path with the issued nonce is covered by the state-machine tests.)"""
    code, frames = run(frame(hello()) + frame(ping("9" * 32)), tmp_path, monkeypatch)
    assert code == 1
    assert [f["type"] for f in frames] == ["hello_ack", "error"]
    assert frames[1]["payload"]["code"] == "bad_nonce"


def test_loop_framing_violation_sends_typed_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = struct.pack("=I", 0xFFFF_FFF0)
    code, frames = run(bad, tmp_path, monkeypatch)
    assert code == 1
    assert frames[0]["type"] == "error"
    assert frames[0]["payload"]["code"] == "oversized"


def test_loop_invalid_envelope_sends_typed_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = frame({"protocol_version": 1, "type": "nope", "payload": {}})
    code, frames = run(bad, tmp_path, monkeypatch)
    assert code == 1
    assert frames[0]["payload"]["code"] == "malformed"


def test_loop_version_below_floor_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    msg = hello()
    msg["protocol_version"] = 0
    code, frames = run(frame(msg), tmp_path, monkeypatch)
    assert code == 1
    assert frames[0]["type"] == "error"
