"""Step 4: framing edge-case tests (plan Validation list)."""

import io
import json
import struct
import sys

import pytest

from conftest import frame as frame_bytes
from scribe_desktop.framing import EndOfStream, FramingError, read_frame, write_frame
from scribe_desktop.protocol import MAX_FRAME_BYTES, PROTOCOL_VERSION


def test_round_trip() -> None:
    out = io.BytesIO()
    write_frame(out, {"protocol_version": PROTOCOL_VERSION, "type": "hello", "payload": {}})
    assert read_frame(io.BytesIO(out.getvalue())) == {
        "protocol_version": PROTOCOL_VERSION,
        "type": "hello",
        "payload": {},
    }


def test_clean_eof_raises_end_of_stream() -> None:
    with pytest.raises(EndOfStream):
        read_frame(io.BytesIO(b""))


def test_truncated_prefix() -> None:
    with pytest.raises(FramingError, match="truncated length prefix"):
        read_frame(io.BytesIO(b"\x01\x00"))


def test_truncated_body() -> None:
    body = json.dumps({"a": 1}).encode()
    data = struct.pack("=I", len(body) + 10) + body
    with pytest.raises(FramingError, match="truncated mid-frame"):
        read_frame(io.BytesIO(data))


def test_zero_length_frame_rejected() -> None:
    with pytest.raises(FramingError, match="zero-length"):
        read_frame(io.BytesIO(struct.pack("=I", 0)))


def test_oversized_declared_length_rejected_without_allocation() -> None:
    """A 4-byte prefix can declare ~4 GB; must reject before allocating."""
    data = struct.pack("=I", 0xFFFF_FFF0)
    with pytest.raises(FramingError, match="oversized|exceeds policy"):
        read_frame(io.BytesIO(data))


def test_exact_boundary_accepted() -> None:
    # A frame whose body is exactly MAX_FRAME_BYTES is the largest legal frame.
    padding = "x" * (MAX_FRAME_BYTES - len('{"p":""}'))
    body = ('{"p":"' + padding + '"}').encode("utf-8")
    assert len(body) == MAX_FRAME_BYTES
    data = struct.pack("=I", len(body)) + body
    assert read_frame(io.BytesIO(data)) == {"p": padding}


def test_one_over_boundary_rejected_on_write() -> None:
    padding = "x" * (MAX_FRAME_BYTES - len('{"p":""}') + 1)
    with pytest.raises(FramingError, match="oversized|exceeds policy"):
        write_frame(io.BytesIO(), {"p": padding})


def test_invalid_utf8_rejected() -> None:
    body = b"\xff\xfe\xfd\xfc"
    data = struct.pack("=I", len(body)) + body
    with pytest.raises(FramingError, match="not valid UTF-8"):
        read_frame(io.BytesIO(data))


def test_malformed_json_rejected() -> None:
    body = b"{not json"
    data = struct.pack("=I", len(body)) + body
    with pytest.raises(FramingError, match="not valid JSON"):
        read_frame(io.BytesIO(data))


def test_json_nested_past_the_recursion_limit_is_a_framing_fault() -> None:
    """Round 25 LOW-020: within the size bound, deep nesting makes the JSON
    decoder raise RecursionError — which must surface as the ordinary
    ``malformed`` fault every reader handles, not escape a reader thread."""
    depth = 200_000
    body = b"[" * depth + b"]" * depth
    assert len(body) <= MAX_FRAME_BYTES
    data = struct.pack("=I", len(body)) + body
    with pytest.raises(FramingError, match="nested too deeply") as caught:
        read_frame(io.BytesIO(data))
    assert caught.value.code == "malformed"


def test_an_integer_past_the_digit_limit_is_a_framing_fault() -> None:
    """Codex round 27 PR-MED-131: past the int-string digit limit the JSON
    decoder raises a plain ValueError (not a JSONDecodeError) — the LOW-020
    class's sibling. The limit is pinned to the interpreter default (the
    host could move it) and restored, as ``test_cliniko_client`` does."""
    body = b'{"n": ' + b"9" * 5000 + b"}"
    data = struct.pack("=I", len(body)) + body
    previous = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(4300)
    try:
        with pytest.raises(FramingError, match="not valid JSON") as caught:
            read_frame(io.BytesIO(data))
    finally:
        sys.set_int_max_str_digits(previous)
    assert caught.value.code == "malformed"
    assert "9999" not in str(caught.value)


def test_back_to_back_frames_in_one_stream() -> None:
    stream = io.BytesIO(frame_bytes({"n": 1}) + frame_bytes({"n": 2}) + frame_bytes({"n": 3}))
    assert read_frame(stream) == {"n": 1}
    assert read_frame(stream) == {"n": 2}
    assert read_frame(stream) == {"n": 3}
    with pytest.raises(EndOfStream):
        read_frame(stream)
