"""Step 2: validate the pydantic mirror against the canonical fixtures.

Every valid fixture must parse; every invalid fixture must be rejected;
the constants must match protocol/fixtures/meta.json. The TS mirror runs
the same checks against the same files — drift on either side fails here.

Cliniko workflow safeguards plan Task 4.1 (protocol v2, D2): the bounds in
``meta.json``'s ``limits`` are pinned to ``LIMITS``; the pipe leg (no nonce,
only the three v2 types) is Python-only.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from scribe_desktop.protocol import (
    HOST_NAME,
    LIMITS,
    MAX_FRAME_BYTES,
    MIN_SUPPORTED_VERSION,
    PROTOCOL_VERSION,
    CommandPayload,
    ContextPayload,
    ErrorCode,
    StatePayload,
    make_envelope,
    make_error,
    make_pipe_envelope,
    parse_envelope,
    parse_pipe_envelope,
    typed_payload,
)

FIXTURES = Path(__file__).resolve().parents[2] / "protocol" / "fixtures"
VALID = sorted((FIXTURES / "valid").glob("*.json"))
INVALID = sorted((FIXTURES / "invalid").glob("*.json"))
NONCE = "9f2c4a8e1b7d3f6a5c0e8b2d4f7a9c1e3b5d7f0a2c4e6b8d1f3a5c7e9b0d2f4a"


def _fixture(name: str) -> dict[str, Any]:
    value = json.loads((FIXTURES / "valid" / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_fixture_dirs_are_populated() -> None:
    assert len(VALID) >= 5, "expected one valid fixture per message type"
    assert len(INVALID) >= 5


def test_meta_matches_constants() -> None:
    meta = json.loads((FIXTURES / "meta.json").read_text(encoding="utf-8"))
    assert meta["protocol_version"] == PROTOCOL_VERSION == 2
    assert meta["min_supported_version"] == MIN_SUPPORTED_VERSION == 2
    assert meta["host_name"] == HOST_NAME
    assert meta["max_frame_bytes"] == MAX_FRAME_BYTES
    assert meta["limits"] == LIMITS


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.stem)
def test_valid_fixtures_parse(path: Path) -> None:
    envelope = parse_envelope(json.loads(path.read_text(encoding="utf-8")))
    # The file name is the message type, optionally `__<variant>`.
    assert envelope.type == path.stem.split("__")[0]
    # round-trip: serialising and re-parsing yields an equal envelope
    assert parse_envelope(envelope.model_dump(exclude_none=True)) == envelope


@pytest.mark.parametrize("path", INVALID, ids=lambda p: p.stem)
def test_invalid_fixtures_rejected(path: Path) -> None:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    assert fixture["reason"], "invalid fixtures must document their reason"
    with pytest.raises(ValidationError):
        parse_envelope(fixture["message"])


def test_every_v2_type_has_valid_and_invalid_fixtures() -> None:
    for message_type in ("context", "command", "state"):
        assert any(p.stem.startswith(f"{message_type}__") for p in VALID), message_type
        assert any(p.stem.startswith(f"{message_type}__") for p in INVALID), message_type


def test_make_error_is_valid() -> None:
    envelope = make_error(ErrorCode.BAD_NONCE, "session nonce mismatch", request_id="req-9")
    assert parse_envelope(envelope.model_dump(exclude_none=True)) == envelope


# --- typed payloads ---------------------------------------------------------


def test_typed_payload_returns_the_per_type_model() -> None:
    context = typed_payload(parse_envelope(_fixture("context__note.json")))
    assert isinstance(context, ContextPayload)
    assert (context.patient_id, context.note_id) == ("1001", "2002")
    command = typed_payload(parse_envelope(_fixture("command__start.json")))
    assert isinstance(command, CommandPayload)
    assert command.target is not None and command.target.tab_id == 412
    state = typed_payload(parse_envelope(_fixture("state__refusal.json")))
    assert isinstance(state, StatePayload)
    assert state.last_refusal is not None and state.last_refusal.reason == "not_verified"


def test_a_refusal_travels_in_state_never_as_error() -> None:
    """Constraint 9: a refused command is a `state` with `last_refusal`."""
    envelope = parse_envelope(_fixture("state__refusal.json"))
    assert envelope.type == "state"
    assert envelope.payload["last_refusal"]["action"] == "start"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("seq", True),  # a boolean is not an integer
        ("seq", "7"),  # nor a numeric string
        ("tab_id", LIMITS["max_tab_id"] + 1),
        ("focused", 1),
    ],
)
def test_context_scalars_are_strict(field: str, value: object) -> None:
    message = _fixture("context__note.json")
    message["payload"][field] = value
    with pytest.raises(ValidationError):
        parse_envelope(message)


@pytest.mark.parametrize("action", ["resume", "finish", "resume_previous", "open_review"])
def test_every_session_bound_action_needs_its_ref(action: str) -> None:
    message = _fixture("command__resume.json")
    message["payload"]["action"] = action
    parse_envelope(message)
    del message["payload"]["session_ref"]
    with pytest.raises(ValidationError):
        parse_envelope(message)


def test_pause_may_name_its_session() -> None:
    message = _fixture("command__pause.json")
    message["payload"]["session_ref"] = "AbCdEfGhIjKlMnOpQrStUv_-"
    parse_envelope(message)


def test_confirmed_is_refused_outside_discard() -> None:
    message = _fixture("command__finish.json")
    message["payload"]["confirmed"] = True
    with pytest.raises(ValidationError):
        parse_envelope(message)


def test_a_display_string_of_exactly_the_limit_is_accepted() -> None:
    message = _fixture("state__live.json")
    message["payload"]["report"]["patient_name"] = "A" * LIMITS["max_display_chars"]
    parse_envelope(message)
    message["payload"]["report"]["patient_name"] = "A" * (LIMITS["max_display_chars"] + 1)
    with pytest.raises(ValidationError):
        parse_envelope(message)


def test_lengths_count_characters_not_bytes() -> None:
    # 120 non-ASCII characters (240+ UTF-8 bytes) fit; the TS mirror counts
    # code points the same way.
    message = _fixture("state__live.json")
    message["payload"]["report"]["patient_name"] = "é" * LIMITS["max_display_chars"]
    parse_envelope(message)


def test_an_available_hotkey_names_its_chord() -> None:
    message = _fixture("state__live.json")
    message["payload"]["hotkey"] = {"available": True}
    with pytest.raises(ValidationError):
        parse_envelope(message)


# --- the pipe leg (Python-only: the extension never sees the pipe) -----------


def _without_nonce(message: dict[str, Any]) -> dict[str, Any]:
    stripped = dict(message)
    del stripped["session_nonce"]
    return stripped


@pytest.mark.parametrize(
    "name", ["context__note.json", "command__start.json", "state__live.json"]
)
def test_the_pipe_carries_the_v2_types_without_a_nonce(name: str) -> None:
    message = _fixture(name)
    envelope = parse_pipe_envelope(_without_nonce(message))
    assert envelope.session_nonce is None
    with pytest.raises(ValidationError):
        parse_pipe_envelope(message)  # a nonce never crosses the pipe


@pytest.mark.parametrize("name", ["hello.json", "hello_ack.json", "ping.json", "error.json"])
def test_the_pipe_refuses_the_handshake_types(name: str) -> None:
    message = _fixture(name)
    message.pop("session_nonce", None)
    with pytest.raises(ValidationError):
        parse_pipe_envelope(message)


def test_the_pipe_still_validates_the_payload() -> None:
    message = _without_nonce(_fixture("context__note.json"))
    message["payload"]["patient_id"] = "0123"
    with pytest.raises(ValidationError):
        parse_pipe_envelope(message)


def test_make_pipe_envelope_builds_a_nonce_free_state() -> None:
    payload = _fixture("state__app_not_running.json")["payload"]
    envelope = make_pipe_envelope("state", payload=payload)
    assert envelope.session_nonce is None
    assert envelope.protocol_version == PROTOCOL_VERSION
    with pytest.raises(ValidationError):
        make_envelope("state", payload=payload)  # the Chrome wire needs the nonce
    make_envelope("state", payload=payload, session_nonce=NONCE)
