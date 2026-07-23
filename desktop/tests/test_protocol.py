"""Step 2: validate the pydantic mirror against the canonical fixtures.

Every valid fixture must parse; every invalid fixture must be rejected;
the constants must match protocol/fixtures/meta.json. The TS mirror runs
the same checks against the same files — drift on either side fails here.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from scribe_desktop.protocol import (
    HOST_NAME,
    MAX_FRAME_BYTES,
    MIN_SUPPORTED_VERSION,
    PROTOCOL_VERSION,
    ErrorCode,
    make_error,
    parse_envelope,
)

FIXTURES = Path(__file__).resolve().parents[2] / "protocol" / "fixtures"
VALID = sorted((FIXTURES / "valid").glob("*.json"))
INVALID = sorted((FIXTURES / "invalid").glob("*.json"))


def test_fixture_dirs_are_populated() -> None:
    assert len(VALID) >= 5, "expected one valid fixture per message type"
    assert len(INVALID) >= 5


def test_meta_matches_constants() -> None:
    meta = json.loads((FIXTURES / "meta.json").read_text(encoding="utf-8"))
    assert meta["protocol_version"] == PROTOCOL_VERSION
    assert meta["min_supported_version"] == MIN_SUPPORTED_VERSION
    assert meta["host_name"] == HOST_NAME
    assert meta["max_frame_bytes"] == MAX_FRAME_BYTES


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.stem)
def test_valid_fixtures_parse(path: Path) -> None:
    envelope = parse_envelope(json.loads(path.read_text(encoding="utf-8")))
    assert envelope.type == path.stem  # fixture filename must match its message type
    # round-trip: serialising and re-parsing yields an equal envelope
    assert parse_envelope(envelope.model_dump(exclude_none=True)) == envelope


@pytest.mark.parametrize("path", INVALID, ids=lambda p: p.stem)
def test_invalid_fixtures_rejected(path: Path) -> None:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    assert fixture["reason"], "invalid fixtures must document their reason"
    with pytest.raises(ValidationError):
        parse_envelope(fixture["message"])


def test_make_error_is_valid() -> None:
    envelope = make_error(ErrorCode.BAD_NONCE, "session nonce mismatch", request_id="req-9")
    assert parse_envelope(envelope.model_dump(exclude_none=True)) == envelope
