"""Step 4: logging enforcement tests — the misuse cases must be blocked."""

import json
import logging
import sys
from pathlib import Path

import pytest

from scribe_desktop.logging_setup import (
    _SCANNED_FIELDS,
    LOG_FORMAT,
    PayloadTripwireFilter,
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


def test_tripwire_drops_pydantic_repr_leak(logger: logging.Logger, tmp_path: Path) -> None:
    """HIGH-003: the promised misuse case — a real Envelope in an f-string —
    renders with UNQUOTED keys and must still be dropped."""
    from scribe_desktop.protocol import Envelope

    envelope = Envelope(
        protocol_version=1,
        type="ping",
        request_id="req-leak",
        session_nonce="n" * 32,
        payload={},
    )
    before = dropped_record_count()
    logger.info(f"got {envelope}")  # noqa: G004 - deliberate misuse under test
    assert dropped_record_count() == before + 1
    assert "n" * 32 not in read_log(tmp_path)


def test_rotation_actually_rolls_over(tmp_path: Path) -> None:
    """LOW-014: exercise a real rollover, not just handler configuration."""
    small = setup_logging("test-rotate", log_dir=tmp_path, stderr=False, max_bytes=500)
    for _ in range(100):
        small.info("operational line with enough length to pass the threshold")
    assert (tmp_path / "test-rotate.log.1").exists()


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


# --------------------------------------------------------------------------
# PR-HIGH-001 (peer round 3): handler filters run BEFORE the formatter appends
# the traceback, so a message-only scan let a caught note-validation error
# persist clinical text into the log with the drop counter untouched.
# --------------------------------------------------------------------------


def test_tripwire_drops_note_validation_traceback(logger: logging.Logger, tmp_path: Path) -> None:
    """The finding's own reproduction, as a regression test: a production
    ``setup_logging()`` logger, a caught ``NoteSpan`` validation error carrying
    a synthetic marker, and ``logger.exception`` — the marker must not reach
    the log and the drop counter must move."""
    from pydantic import ValidationError

    from scribe_desktop.note import NoteSpan

    marker = "SECRETMARKERXYZ"
    before = dropped_record_count()
    try:
        NoteSpan(span_text=f"{marker} left knee is tender", provenance="transcript")
    except ValidationError:
        logger.exception("note validation failed")
    else:  # pragma: no cover - the construction must raise for this test to mean anything
        pytest.fail("NoteSpan accepted a transcript span with no source_coords")

    assert dropped_record_count() == before + 1
    text = read_log(tmp_path)
    assert marker not in text
    assert "Traceback" not in text
    assert "note validation failed" not in text  # the whole record is dropped, not trimmed


def test_tripwire_scans_stack_info() -> None:
    """The other post-filter channel the formatter appends. Driven through a
    synthetic record so the signature lands in ``stack_info`` and nowhere
    else — a real stack rendering would also carry it in the source line."""
    record = logging.LogRecord(
        "test-scribe", logging.INFO, __file__, 1, "routine event", None, None
    )
    record.stack_info = "Stack (most recent call last):\n  span_text='left knee is tender'"
    before = dropped_record_count()

    assert PayloadTripwireFilter().filter(record) is False
    assert dropped_record_count() == before + 1


def test_tripwire_passes_a_clean_operational_exception(
    logger: logging.Logger, tmp_path: Path
) -> None:
    """The fix must not turn every error log into a dropped record: an
    operational failure with no clinical signature still gets written."""
    before = dropped_record_count()
    try:
        raise OSError("no space left on device")
    except OSError:
        logger.exception("write failed")

    assert dropped_record_count() == before
    text = read_log(tmp_path)
    assert "write failed" in text
    assert "no space left on device" in text


def _raise_with_a_signature_in_the_source_line() -> None:
    # The RAISING line is what a traceback frame renders, so the registered
    # signature is carried there and NOWHERE else: the exception message and
    # type stay clean, which is what makes the tuple-vs-value distinction the
    # only thing that can catch it.
    raise RuntimeError("operational failure")  # span_text='left knee is tender'


def test_tripwire_drops_a_precached_exception_text(
    logger: logging.Logger, tmp_path: Path
) -> None:
    """PR-MED-001(a): the formatter treats an already-populated `exc_text` as
    its authoritative exception output, so a record carrying BOTH a clean
    `exc_info` and a signature-bearing cached `exc_text` must still drop —
    and the filter must leave that cache untouched."""
    marker = "PRECACHEDMARKERXYZ"
    try:
        raise OSError("no space left on device")
    except OSError:
        exc_info = sys.exc_info()

    record = logger.makeRecord(
        "test-scribe", logging.ERROR, __file__, 1, "write failed", None, exc_info
    )
    record.exc_text = f"Traceback (most recent call last):\n  span_text='{marker}'"
    cached = record.exc_text
    before = dropped_record_count()

    logger.handle(record)

    assert dropped_record_count() == before + 1
    assert record.exc_text is cached  # the formatter owns the cache; the filter never writes it
    assert marker not in read_log(tmp_path)


def test_tripwire_renders_the_exact_exc_info_tuple(
    logger: logging.Logger, tmp_path: Path
) -> None:
    """PR-MED-001(b): the formatter renders the TUPLE's traceback, so scanning
    only `exc_info[1].__traceback__` misses a frame the log will print. Here
    the signature lives solely in a traceback frame's source line, and the
    exception object's own traceback is detached so the two inputs differ."""
    try:
        _raise_with_a_signature_in_the_source_line()
    except RuntimeError:
        etype, value, tb = sys.exc_info()
    assert value is not None
    value.__traceback__ = None  # the divergence: only the tuple still has the frame
    before = dropped_record_count()

    record = logger.makeRecord(
        "test-scribe", logging.ERROR, __file__, 1, "operation failed", None, (etype, value, tb)
    )
    logger.handle(record)

    assert dropped_record_count() == before + 1
    assert "span_text" not in read_log(tmp_path)


def test_tripwire_scans_a_truthy_exc_info_whose_value_is_none(
    logger: logging.Logger, tmp_path: Path
) -> None:
    """PR-LOW-001: the formatter's predicate is `if record.exc_info:`, so a
    truthy tuple with a None value slot — reachable by passing `exc_info=`
    explicitly — is still rendered and persisted. The filter must select on
    the same truthiness, not on the value slot."""
    try:
        _raise_with_a_signature_in_the_source_line()
    except RuntimeError:
        _etype, _value, tb = sys.exc_info()
    before = dropped_record_count()
    record = logger.makeRecord(
        "test-scribe", logging.ERROR, __file__, 1, "op failed", None, (RuntimeError, None, tb)
    )
    assert record.exc_info  # truthy: exactly what the formatter tests
    tripwire = next(
        f for h in logger.handlers for f in h.filters if isinstance(f, PayloadTripwireFilter)
    )

    # The no-write invariant is asserted against the FILTER, not after a full
    # handle(): pytest's own capture handler formats the record once ours has
    # refused it, and formatting is what legitimately populates the cache.
    assert tripwire.filter(record) is False
    assert record.exc_text is None

    logger.handle(record)  # end to end: nothing reaches the file either
    assert dropped_record_count() == before + 2  # direct call + the handler's own
    assert "span_text" not in read_log(tmp_path)


def test_tripwire_scans_every_field_the_formatter_interpolates() -> None:
    """PR-LOW-001, as a CLASS regression rather than two more cases.

    For every field the configured format string interpolates, a signature
    placed only in that field must be (a) visible in the real formatter's
    output and (b) dropped by the filter. The field list is derived from
    `LOG_FORMAT`, so a future format change extends this test automatically
    instead of silently widening output past the scan — which is how this
    class recurred in rounds 3, 4, 5 and 6.
    """
    marker = "span_text='left knee'"
    formatter = logging.Formatter(LOG_FORMAT)
    tripwire = PayloadTripwireFilter()

    assert _SCANNED_FIELDS  # the derivation must not silently produce nothing
    for field in _SCANNED_FIELDS:
        record = logging.LogRecord("scribe-app", logging.INFO, __file__, 1, "routine", None, None)
        setattr(record, field, marker)
        assert marker in formatter.format(record), field
        before = dropped_record_count()
        assert tripwire.filter(record) is False, field
        assert dropped_record_count() == before + 1, field


def test_asctime_is_regenerated_and_cannot_smuggle_content() -> None:
    """The one interpolated field deliberately excluded from the sweep: the
    formatter overwrites `asctime` from the clock, so a caller cannot place
    content there. Asserted rather than assumed."""
    formatter = logging.Formatter(LOG_FORMAT)
    record = logging.LogRecord("scribe-app", logging.INFO, __file__, 1, "routine", None, None)
    record.asctime = "span_text='left knee'"

    assert "asctime" not in _SCANNED_FIELDS
    assert "span_text" not in formatter.format(record)


def test_both_handlers_share_the_pinned_production_formatter(tmp_path: Path) -> None:
    """Pins the precondition the completeness claim rests on: one stock
    formatter object, built from LOG_FORMAT, on every handler."""
    logger = setup_logging("test-pinned-format", log_dir=tmp_path, stderr=True)
    assert len(logger.handlers) == 2
    assert len({id(handler.formatter) for handler in logger.handlers}) == 1
    for handler in logger.handlers:
        assert handler.formatter is not None
        assert handler.formatter._fmt == LOG_FORMAT


def test_both_production_handlers_share_the_fixed_tripwire(tmp_path: Path) -> None:
    """Pattern siblings: every production handler must route through the ONE
    filter, so fixing it fixes the protocol-envelope, transcript-model and
    note-model exception paths on file and stderr alike."""
    logger = setup_logging("test-shared-tripwire", log_dir=tmp_path, stderr=True)
    assert len(logger.handlers) == 2
    tripwires = [
        f
        for handler in logger.handlers
        for f in handler.filters
        if isinstance(f, PayloadTripwireFilter)
    ]
    assert len(tripwires) == 2
    assert len({id(f) for f in tripwires}) == 1
