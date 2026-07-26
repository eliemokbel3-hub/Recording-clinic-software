"""Step 1 tests: core session types + deliberately-extended logging whitelist."""

from __future__ import annotations

import logging
from datetime import UTC

import pytest
from pydantic import ValidationError

import scribe_desktop.protocol as protocol
from scribe_desktop.logging_setup import (
    _PAYLOAD_SIGNATURES,
    ALLOWED_KEYS,
    PayloadTripwireFilter,
    dropped_record_count,
    log_event,
)
from scribe_desktop.session import (
    ACTIVE_STATES,
    RECOVERABLE_STATES,
    TERMINAL_STATES,
    RecordingSession,
    SessionState,
)


class TestSessionState:
    def test_all_nine_plan_states_exist(self) -> None:
        assert {s.value for s in SessionState} == {
            "idle",
            "recording",
            "paused",
            "processing",
            "queued",
            "written",
            "failed",
            "discarded",
            "expired",
        }

    def test_state_groups_are_consistent(self) -> None:
        # Sweep-protected states are exactly the plan's recording/paused/processing.
        assert ACTIVE_STATES == {
            SessionState.RECORDING,
            SessionState.PAUSED,
            SessionState.PROCESSING,
        }
        assert ACTIVE_STATES <= RECOVERABLE_STATES
        assert not (RECOVERABLE_STATES & TERMINAL_STATES)
        assert SessionState.QUEUED not in TERMINAL_STATES  # key retained while queued

    def test_phase1_connection_state_is_retired(self) -> None:
        assert not hasattr(protocol, "ConnectionState")


class TestRecordingSession:
    def test_defaults(self) -> None:
        session = RecordingSession()
        assert session.state is SessionState.IDLE
        assert len(session.session_id) == 32
        assert session.encounter_context is None
        assert session.key_reference is None
        assert session.created_at.tzinfo is UTC
        assert session.updated_at >= session.created_at

    def test_session_ids_are_unique(self) -> None:
        assert RecordingSession().session_id != RecordingSession().session_id

    @pytest.mark.parametrize(
        "bad_id",
        [
            "../../escape",
            "patient Jane Doe",
            "a" * 31,  # wrong length
            "a" * 33,
            "A" * 32,  # uppercase not canonical uuid4().hex
            "g" * 32,  # non-hex
            "a" * 16 + "/" + "a" * 15,  # path separator
            "",
        ],
    )
    def test_session_id_rejects_non_canonical_values(self, bad_id: str) -> None:
        # PR-MED-002: session_id must be opaque uuid4().hex — safe as a single
        # path segment (sessions/<id>/) and as whitelisted log metadata.
        with pytest.raises(ValidationError):
            RecordingSession(session_id=bad_id)

    def test_frozen_and_extra_forbidden(self) -> None:
        session = RecordingSession()
        with pytest.raises(ValidationError):
            session.state = SessionState.RECORDING  # type: ignore[misc]
        with pytest.raises(ValidationError):
            RecordingSession(bogus="x")  # type: ignore[call-arg]

    def test_with_state_copies_and_touches_updated_at(self) -> None:
        session = RecordingSession()
        moved = session.with_state(SessionState.RECORDING)
        assert moved is not session
        assert session.state is SessionState.IDLE  # original untouched
        assert moved.state is SessionState.RECORDING
        assert moved.updated_at >= session.updated_at
        assert moved.session_id == session.session_id
        assert moved.created_at == session.created_at

    @pytest.mark.parametrize(
        "bad_ref",
        [
            "",
            ".",
            "..\\..\\other.key",
            "../key.dpapi",
            "C:\\Users\\other\\key.dpapi",
            "/etc/key.dpapi",
            "patient Jane Doe.dpapi",
            "sessions/abc/key.dpapi",
        ],
    )
    def test_key_reference_rejects_paths(self, bad_ref: str) -> None:
        # PR-MED-003: key_reference is opaque — only the literal "key.dpapi";
        # Step 2 derives the real path from the validated session_id, so a
        # malformed session can never aim deletion outside its directory.
        with pytest.raises(ValidationError):
            RecordingSession(key_reference=bad_ref)

    def test_key_reference_accepts_canonical_value(self) -> None:
        assert RecordingSession(key_reference="key.dpapi").key_reference == "key.dpapi"

    def test_activity_properties(self) -> None:
        session = RecordingSession()
        assert not session.is_active and not session.is_terminal
        assert session.with_state(SessionState.RECORDING).is_active
        assert session.with_state(SessionState.DISCARDED).is_terminal


class TestSessionLoggingWhitelist:
    """Tripwire tests for the deliberately-extended ALLOWED_KEYS."""

    NEW_KEYS = ("session_id", "session_state", "chunk_index", "sample_rate", "device_id")

    def test_new_keys_are_whitelisted(self) -> None:
        assert set(self.NEW_KEYS) <= ALLOWED_KEYS

    def test_log_event_accepts_new_session_keys(self) -> None:
        logger = logging.getLogger("test_session_keys_ok")
        logger.setLevel(logging.INFO)  # NOTSET would drop before the filter runs
        logger.addHandler(logging.NullHandler())
        logger.addFilter(PayloadTripwireFilter())  # logger-level: runs in Logger.handle
        before = dropped_record_count()
        log_event(
            logger,
            "session_started",
            session_id="a" * 32,
            session_state="recording",
            chunk_index=0,
            sample_rate=16000,
            device_id=1,
        )
        assert dropped_record_count() == before  # tripwire did not fire

    def test_log_event_still_rejects_non_whitelisted_keys(self) -> None:
        logger = logging.getLogger("test_session_keys_bad")
        with pytest.raises(ValueError, match="whitelist"):
            log_event(logger, "session_started", transcript="hello")
        with pytest.raises(ValueError, match="whitelist"):
            log_event(logger, "session_started", audio_chunk=1)

    def test_new_key_renderings_disjoint_from_payload_signatures(self) -> None:
        # log_event renders "key=value"; none of the new keys may collide with
        # a tripwire signature, or every legitimate session log line would drop.
        for key in self.NEW_KEYS:
            rendering = f"{key}="
            assert all(sig not in rendering for sig in _PAYLOAD_SIGNATURES), key

    def test_tripwire_drops_recording_session_representations(self) -> None:
        # PR-MED-001: a logged RecordingSession repr carries encounter_context
        # (patient/booking identifiers) — the tripwire must drop it.
        session = RecordingSession(encounter_context="patient-123")
        tripwire = PayloadTripwireFilter()
        for rendered in (repr(session), str(session.model_dump()), session.model_dump_json()):
            record = logging.LogRecord(
                "test_session_repr", logging.INFO, __file__, 1, rendered, None, None
            )
            before = dropped_record_count()
            assert tripwire.filter(record) is False, rendered
            assert dropped_record_count() == before + 1

    def test_tripwire_still_drops_payload_signatures(self) -> None:
        logger = logging.getLogger("test_session_tripwire")
        logger.setLevel(logging.INFO)
        handler = logging.NullHandler()
        logger.addHandler(handler)
        tripwire = PayloadTripwireFilter()
        record = logging.LogRecord(
            "test_session_tripwire",
            logging.INFO,
            __file__,
            1,
            "session_started payload={'oops': 1}",
            None,
            None,
        )
        before = dropped_record_count()
        assert tripwire.filter(record) is False
        assert dropped_record_count() == before + 1
