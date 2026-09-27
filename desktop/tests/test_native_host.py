"""Step 5: handshake state machine + origin verification + protocol-loop tests."""

import io
import logging
import struct
import sys
from pathlib import Path

import pytest

from conftest import NONCE, frame, hello, ping, read_frames
from scribe_desktop.logging_setup import setup_logging
from scribe_desktop.native_host import (
    EXPECTED_ORIGIN,
    HostSession,
    SessionViolation,
    find_origin,
    run_host,
    verify_origin,
)
from scribe_desktop.protocol import PROTOCOL_VERSION, parse_envelope


def make_session() -> HostSession:
    return HostSession(nonce_factory=lambda: NONCE)


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
        "protocol_version": PROTOCOL_VERSION,
        "type": "pong",
        "request_id": "r",
        "session_nonce": NONCE,
        "payload": {},
    }
    with pytest.raises(SessionViolation):
        session.handle(parse_envelope(bad))


# --- protocol loop over pipes -------------------------------------------


def make_logger(tmp_path: Path) -> logging.Logger:
    return setup_logging("scribe-host-test", log_dir=tmp_path, stderr=False)


def run(data: bytes, tmp_path: Path) -> tuple[int, list[dict]]:
    out = io.BytesIO()
    code = run_host(io.BytesIO(data), out, make_logger(tmp_path))
    return code, read_frames(out.getvalue())


def test_loop_full_handshake_then_eof(tmp_path: Path) -> None:
    code, frames = run(frame(hello()), tmp_path)
    assert code == 0
    assert [f["type"] for f in frames] == ["hello_ack"]


def test_loop_foreign_nonce_gets_typed_error(tmp_path: Path) -> None:
    """The loop issues a random nonce; a ping with a foreign (but present)
    nonce must produce hello_ack then a typed bad_nonce error and exit 1."""
    code, frames = run(frame(hello()) + frame(ping("9" * 32)), tmp_path)
    assert code == 1
    assert [f["type"] for f in frames] == ["hello_ack", "error"]
    assert frames[1]["payload"]["code"] == "bad_nonce"


def test_loop_missing_nonce_gets_bad_nonce(tmp_path: Path) -> None:
    """MED-001 alignment: a ping with NO nonce yields bad_nonce (as TS does)."""
    no_nonce = {
        "protocol_version": PROTOCOL_VERSION,
        "type": "ping",
        "request_id": "r",
        "payload": {},
    }
    code, frames = run(frame(hello()) + frame(no_nonce), tmp_path)
    assert code == 1
    assert frames[1]["payload"]["code"] == "bad_nonce"


@pytest.mark.parametrize("bad_type", [[], {}, ["ping"]], ids=["list", "object", "listed-ping"])
def test_loop_an_unhashable_type_is_a_typed_error_not_a_crash(
    tmp_path: Path, bad_type: object
) -> None:
    """Round 57 SEC-001: a ``type`` that is a list or an object once raised
    ``TypeError`` in the nonce pre-check (a frozenset membership test) and
    left the host without the typed error; it is now ``malformed``."""
    message = {"protocol_version": PROTOCOL_VERSION, "type": bad_type, "payload": {}}
    code, frames = run(frame(hello()) + frame(message), tmp_path)
    assert code == 1
    assert [f["type"] for f in frames] == ["hello_ack", "error"]
    assert frames[1]["payload"]["code"] == "malformed"


def test_loop_framing_violation_sends_typed_error(tmp_path: Path) -> None:
    bad = struct.pack("=I", 0xFFFF_FFF0)
    code, frames = run(bad, tmp_path)
    assert code == 1
    assert frames[0]["type"] == "error"
    assert frames[0]["payload"]["code"] == "oversized"


def test_loop_deeply_nested_json_is_a_typed_error_not_a_hang(tmp_path: Path) -> None:
    """Round 25 LOW-020: the frame is read on the stdin THREAD; a RecursionError
    there once killed that thread silently and left the main loop waiting
    forever. It is now the ordinary ``malformed`` framing fault."""
    depth = 200_000
    body = b"[" * depth + b"]" * depth
    code, frames = run(frame(hello()) + struct.pack("=I", len(body)) + body, tmp_path)
    assert code == 1
    assert [f["type"] for f in frames] == ["hello_ack", "error"]
    assert frames[1]["payload"]["code"] == "malformed"


def test_loop_an_integer_past_the_digit_limit_is_a_typed_error(tmp_path: Path) -> None:
    """Codex round 27 PR-MED-131: the digit-limit ValueError on the stdin
    THREAD is the ordinary ``malformed`` fault, not a silent thread death."""
    body = b'{"n": ' + b"9" * 5000 + b"}"
    previous = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(4300)
    try:
        code, frames = run(frame(hello()) + struct.pack("=I", len(body)) + body, tmp_path)
    finally:
        sys.set_int_max_str_digits(previous)
    assert code == 1
    assert [f["type"] for f in frames] == ["hello_ack", "error"]
    assert frames[1]["payload"]["code"] == "malformed"


def test_loop_invalid_envelope_sends_typed_error(tmp_path: Path) -> None:
    bad = frame({"protocol_version": PROTOCOL_VERSION, "type": "nope", "payload": {}})
    code, frames = run(bad, tmp_path)
    assert code == 1
    assert frames[0]["payload"]["code"] == "malformed"


@pytest.mark.parametrize("version", [0, 1])
def test_loop_version_below_floor_typed_code(tmp_path: Path, version: int) -> None:
    """MED-001: below-floor version yields the version_below_floor code —
    since protocol v2 (Task 4.1) that includes a v1 extension's hello."""
    msg = hello()
    msg["protocol_version"] = version
    code, frames = run(frame(msg), tmp_path)
    assert code == 1
    assert frames[0]["type"] == "error"
    assert frames[0]["payload"]["code"] == "version_below_floor"


@pytest.mark.parametrize("version", [True, False, "2", 2.5])
def test_loop_a_non_integer_version_is_malformed(tmp_path: Path, version: object) -> None:
    """Round 25 LOW-021: a boolean is not below the floor (``True < 2`` in
    Python) — it is no version at all, ``malformed``, as the TypeScript
    mirror classifies it; nor is a numeric string."""
    msg = hello()
    msg["protocol_version"] = version
    code, frames = run(frame(msg), tmp_path)
    assert code == 1
    assert frames[0]["payload"]["code"] == "malformed"


def test_loop_survives_dead_peer_on_write(tmp_path: Path) -> None:
    """MED-003: a broken output pipe is logged and returned, not raised."""

    class BrokenPipe(io.BytesIO):
        def write(self, *_args: object) -> int:
            raise BrokenPipeError()

    code = run_host(io.BytesIO(frame(hello())), BrokenPipe(), make_logger(tmp_path))
    assert code == 1
