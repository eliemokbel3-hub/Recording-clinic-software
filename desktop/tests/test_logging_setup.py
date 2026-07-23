"""Step 4: logging enforcement tests — the misuse cases must be blocked."""

import json
import logging
from pathlib import Path

import pytest

from scribe_desktop.logging_setup import (
    dropped_record_count,
    log_event,
    setup_logging,
)


@pytest.fixture()
def logger(tmp_path: Path) -> logging.Logger:
    return setup_logging("test-scribe", log_dir=tmp_path, stderr=False)


def read_log(tmp_path: Path) -> str:
    return (tmp_path / "test-scribe.log").read_text(encoding="utf-8")


def test_log_event_whitelisted_fields(logger: logging.Logger, tmp_path: Path) -> None:
    log_event(logger, "handshake_ok", message_type="hello_ack", protocol_version=1, byte_size=42)
    text = read_log(tmp_path)
    assert "handshake_ok" in text
    assert "message_type=hello_ack" in text


def test_log_event_rejects_unknown_fields(logger: logging.Logger) -> None:
    with pytest.raises(ValueError, match="whitelist"):
        log_event(logger, "oops", transcript="never")


def test_tripwire_drops_interpolated_envelope(logger: logging.Logger, tmp_path: Path) -> None:
    """The classic misuse: formatting a whole message into the log line."""
    envelope = {"protocol_version": 1, "type": "ping", "session_nonce": "n" * 32, "payload": {}}
    before = dropped_record_count()
    logger.info("got %s", json.dumps(envelope))  # bypasses log_event on purpose
    assert dropped_record_count() == before + 1
    assert "session_nonce" not in read_log(tmp_path)


def test_tripwire_passes_clean_records(logger: logging.Logger, tmp_path: Path) -> None:
    logger.info("plain operational note")
    assert "plain operational note" in read_log(tmp_path)


def test_no_stdout_handler(logger: logging.Logger) -> None:
    import sys

    for handler in logger.handlers:
        assert getattr(handler, "stream", None) is not sys.stdout


def test_rotation_configured(logger: logging.Logger) -> None:
    from logging.handlers import RotatingFileHandler

    assert any(isinstance(h, RotatingFileHandler) for h in logger.handlers)
