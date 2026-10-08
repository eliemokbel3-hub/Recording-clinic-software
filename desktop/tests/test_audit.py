"""The audit record (privacy-professional-controls plan Tasks 1.2 / 1.3; D7,
D8, D9; C2, C3): the encrypted row store, its fail-closed rules, the prune,
the CSV, the unreadable-key reset, and ``app.main``'s wiring of it.

Store tests use the real DPAPI custody path under ``tmp_path`` (Windows-only,
like every custody test); nothing here touches the real ``%LOCALAPPDATA%``."""

from __future__ import annotations

import csv
import dataclasses
import io
import json
import logging
import math
import os
import sys
import uuid
from datetime import UTC, date, datetime, timedelta, timezone, tzinfo
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from conftest import InertWarmup
from encounter_fakes import CLINIC_ID, NOTE, PRACTITIONER, consent_for, context
from scribe_desktop import audit as audit_mod
from scribe_desktop.audit import (
    AUDIT_KEY_DESCRIPTION,
    CSV_COLUMNS,
    MAX_EVENTS,
    AuditLog,
    AuditModels,
    AuditResetError,
    AuditRow,
    AuditUnavailable,
    AuditWriteError,
    RecordingRecord,
    csv_cell,
    month_prune_at,
)
from scribe_desktop.encounter import Verification, unlinked_consent
from scribe_desktop.logging_setup import _PAYLOAD_SIGNATURES, ALLOWED_KEYS, PayloadTripwireFilter
from scribe_desktop.past_sessions import ExportRecovery
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import SessionControllerError
from scribe_desktop.session_mode import SessionMode
from scribe_desktop.session_store import (
    KEY_FILENAME,
    SESSION_KEY_DESCRIPTION,
    CompletionFacts,
    StoreWriteError,
    SweepResult,
    unwrap_key_from_file,
    wrap_key_to_file,
)

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI custody is Windows-only")

USER = "4242"
T0 = datetime(2026, 10, 1, 7, 30, tzinfo=UTC)


def _sid() -> str:
    return uuid.uuid4().hex


class _Clock:
    def __init__(self, now: datetime = T0) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def _log(tmp_path: Path, clock: _Clock | None = None, **kwargs: Any) -> AuditLog:
    # A fixed zone (UTC unless a test names one), so no expectation depends on
    # the host's own zone.
    kwargs.setdefault("local_zone", UTC)
    return AuditLog(tmp_path / "audit", clock=clock or _Clock(), **kwargs)


VERSION = "0.2.0"
DEVELOPMENT = "development-consent-v1"
# Pilot plan Task 1.3 and development-recordings Task 1.4: the v2 and v3
# arguments every Start passes.
V2: dict[str, Any] = {
    "mode": SessionMode.NORMAL,
    "app_version": VERSION,
    "development_consent_version": None,
}


def _begin_linked(
    log: AuditLog,
    session_id: str | None = None,
    *,
    mode: SessionMode = SessionMode.NORMAL,
    development: str | None = None,
) -> str:
    sid = session_id or _sid()
    ctx = context()
    log.begin(
        sid,
        consent=consent_for(ctx),
        context=ctx,
        user_id=USER,
        started_at=T0,
        mode=mode,
        app_version=VERSION,
        development_consent_version=development,
    )
    return sid


def _begin_unlinked(
    log: AuditLog,
    *,
    started_at: datetime = T0,
    mode: SessionMode = SessionMode.NORMAL,
    development: str | None = None,
) -> str:
    sid = _sid()
    log.begin(
        sid,
        consent=unlinked_consent(T0),
        context=None,
        user_id=None,
        started_at=started_at,
        mode=mode,
        app_version=VERSION,
        development_consent_version=development,
    )
    return sid


def _row_path(log: AuditLog, sid: str) -> Path:
    found = list(log.root.glob(f"*/{sid}.enc"))
    assert len(found) == 1, found
    return found[0]


def _only_row(log: AuditLog, sid: str) -> AuditRow:
    rows = [row for row in log.rows().rows if row.session_id == sid]
    assert len(rows) == 1
    return rows[0]


def _seal(log: AuditLog, sid: str, document: dict[str, Any], month: str = "2026-10") -> Path:
    """A row file sealed under the store's OWN key and AAD (for rows this
    build cannot have written: a newer schema)."""
    crypto = unwrap_key_from_file(log.root, description=AUDIT_KEY_DESCRIPTION)
    try:
        path = log.root / month / f"{sid}.enc"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            crypto.encrypt(json.dumps(document).encode(), b"audit:" + sid.encode())
        )
    finally:
        crypto.destroy()
    return path


# ---------------------------------------------------------------------------
# C3 — the row can hold no free text, by construction.
# ---------------------------------------------------------------------------


def _string_leaves(schema: dict[str, Any], defs: dict[str, Any]) -> list[dict[str, Any]]:
    """Every string-typed leaf of a JSON schema, through $ref / anyOf."""
    leaves: list[dict[str, Any]] = []
    stack: list[Any] = [schema]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if "$ref" in node:
                stack.append(defs[node["$ref"].rsplit("/", 1)[-1]])
                continue
            if node.get("type") == "string":
                leaves.append(node)
            for key in ("properties", "items", "prefixItems", "anyOf", "allOf", "oneOf"):
                value = node.get(key)
                if isinstance(value, dict):
                    stack.extend(value.values() if key == "properties" else [value])
                elif isinstance(value, list):
                    stack.extend(value)
        elif isinstance(node, list):
            stack.extend(node)
    return leaves


class TestNoContentByConstruction:
    """C3 as a DERIVED check (the no-content-escapes lesson): every string
    the row can hold is a pattern, an enumeration or a date — never a free
    string — so no field can carry a name, a sentence or note text."""

    def test_every_string_field_is_constrained(self) -> None:
        schema = AuditRow.model_json_schema()
        leaves = _string_leaves(schema, schema.get("$defs", {}))
        assert len(leaves) > 20, "the walk found too few string fields to mean anything"
        free = [
            leaf
            for leaf in leaves
            if not ({"pattern", "enum", "const"} & set(leaf) or leaf.get("format") in {
                "date", "date-time"
            })
        ]
        assert free == []

    def test_the_row_has_no_field_for_a_patient_or_text(self) -> None:
        schema = AuditRow.model_json_schema()
        fields = set(schema["properties"])
        for model in schema.get("$defs", {}).values():
            fields |= set(model.get("properties", {}))
        assert not {
            name
            for name in fields
            if any(part in name for part in ("patient", "text", "audio", "display", "words"))
            and name != "consent_text_version"
        }

    def test_every_rendering_of_a_row_is_dropped_by_the_log_tripwire(self) -> None:
        row = AuditRow(session_id=_sid(), session_date=date(2026, 10, 1), origin="pre_audit")
        tripwire = PayloadTripwireFilter()
        for rendered in (repr(row), str(row.model_dump()), row.model_dump_json()):
            record = logging.LogRecord("t", logging.INFO, __file__, 1, rendered, None, None)
            assert tripwire.filter(record) is False, rendered

    def test_the_new_signatures_never_match_a_log_event_key(self) -> None:
        for key in ALLOWED_KEYS:
            assert all(sig not in f"{key}=" for sig in _PAYLOAD_SIGNATURES), key
        for name in ("past_session", "note_provenance", "consent_confirmed_at"):
            assert f"{name}=" in _PAYLOAD_SIGNATURES

    def test_the_id_patterns_are_the_encounters(self) -> None:
        """Round 6 LOW-004: the row's id patterns are copies (as the clinic
        registry's are); a drift would refuse every linked Start."""
        from scribe_desktop import encounter

        assert audit_mod._CLINIKO_ID_PATTERN == encounter._ID_PATTERN  # noqa: SLF001
        clinic = AuditRow.model_json_schema()["properties"]["clinic_id"]["anyOf"][0]
        assert clinic["pattern"] == encounter._CLINIC_ID_PATTERN  # noqa: SLF001

    def test_every_refusal_code_fits_the_rows_code_pattern(self) -> None:
        """Round 7 LOW-016: ``last_refusal`` takes the pre-send
        ``WriteRefusalName`` and Cliniko's ``SendRefusal`` codes — a name
        outside the row's pattern would fail every such record silently."""
        import re
        from typing import get_args

        from scribe_desktop.draft_write import SendRefusal, WriteRefusalName

        codes = get_args(WriteRefusalName) + get_args(SendRefusal)
        assert len(codes) > 10
        assert [c for c in codes if not re.fullmatch(audit_mod._CODE_PATTERN, c)] == []  # noqa: SLF001

    def test_every_model_field_is_a_completion_fact(self) -> None:
        """Round 6 LOW-001: the row's models are read from the facts BY
        NAME, so every model field must be a fact (a fact a later task adds
        is then either recorded or knowingly left out here).

        Left out of ``models`` on purpose: ``note_provenance`` and
        ``past_session`` have their own row fields; ``commit_deferred``
        (Task 2.3) is NOT recorded at all — the row's ``past_session`` reads
        ``archived`` either way (the entry was published, verified, before
        the key went), and a deferred marker is a transient the next
        reconciliation clears, which no row update would follow. It feeds
        only Flow 3 step 4's status line. ``recording_kept``
        (development-recordings Task 1.4) is recorded as the row's
        ``recording.kept_at``, set in the same completion write."""
        facts = {field.name for field in dataclasses.fields(CompletionFacts)}
        assert set(AuditModels.model_fields) <= facts
        assert facts - set(AuditModels.model_fields) == {
            "note_provenance",
            "past_session",
            "commit_deferred",
            "recording_kept",
        }
        row_fields = set(AuditRow.model_fields)
        assert {"note_provenance", "past_session", "recording"} <= row_fields
        assert "commit_deferred" not in row_fields
        assert "recording_kept" not in row_fields

    def test_the_write_error_is_a_controller_error(self) -> None:
        """D12: the Start refusal's text reaches every screen."""
        error = AuditWriteError("write_failed")
        assert isinstance(error, SessionControllerError)
        assert str(error) == (
            "the audit record could not be saved (the audit folder could not be "
            "written). Nothing was recorded."
        )

    def test_the_start_refusal_line_as_the_session_screen_shows_it(self) -> None:
        """Round 6 LOW-003: the Session screen prefixes "Start failed: " to
        ``custody_refusal_text``, which — as for every authored controller
        error — names the type (smoke P.4's expected line)."""
        from scribe_desktop.ui import models

        text = models.custody_refusal_text(AuditWriteError("key_unreadable"))
        assert f"Start failed: {text}" == (
            "Start failed: AuditWriteError: the audit record could not be saved "
            "(its key cannot be read on this Windows account - start a new audit "
            "record on the Past sessions tab). Nothing was recorded."
        )


# ---------------------------------------------------------------------------
# The store.
# ---------------------------------------------------------------------------


@windows_only
class TestRowStore:
    def test_a_linked_row_round_trips_encrypted(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        assert not log.root.exists()  # construction touched nothing
        sid = _begin_linked(log)
        path = _row_path(log, sid)
        assert path.parent.name == "2026-10"
        raw = path.read_bytes()
        for plain in (NOTE.encode(), CLINIC_ID.encode(), USER.encode(), b"verified"):
            assert plain not in raw
        row = _only_row(log, sid)
        assert row.origin == "recorded"
        assert row.linked is True and row.verification == "verified"
        assert (row.clinic_id, row.practitioner_id, row.user_id, row.treatment_note_id) == (
            CLINIC_ID,
            PRACTITIONER,
            USER,
            NOTE,
        )
        assert row.consent_text_version == "recording-consent-v1"
        assert row.deletion.state == "pending" and row.past_session.state == "none"
        assert [event.code for event in row.events] == ["started"]

    def test_an_unlinked_row_names_no_clinic(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        sid = _begin_unlinked(log)
        row = _only_row(log, sid)
        assert row.linked is False and row.verification == "unlinked"
        assert (row.clinic_id, row.user_id, row.treatment_note_id) == (None, None, None)

    def test_an_offline_start_is_recorded_as_such(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        ctx = context(Verification.UNVERIFIED_OFFLINE)
        sid = _sid()
        log.begin(sid, consent=consent_for(ctx), context=ctx, user_id=None, started_at=T0, **V2)
        assert _only_row(log, sid).verification == "unverified_offline"

    def test_a_date_the_platform_cannot_convert_is_the_authored_refusal(
        self, tmp_path: Path
    ) -> None:
        """Round 7 LOW-005: MED-001's class at ``begin``'s own date: an
        ``OverflowError`` / ``OSError`` from the local-time conversion is
        ``AuditWriteError``, never a raw error on the Session screen."""

        class Unconvertible(tzinfo):
            def utcoffset(self, _dt: datetime | None) -> timedelta:
                raise OverflowError("date value out of range")

            def dst(self, _dt: datetime | None) -> timedelta:
                return timedelta(0)

        log = _log(tmp_path, local_zone=Unconvertible())
        with pytest.raises(AuditWriteError) as raised:
            _begin_unlinked(log)
        assert raised.value.reason == "write_failed"
        assert list(log.root.glob("*/*.enc")) == []

    def test_a_malformed_user_id_is_left_out_not_refused(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        ctx = context()
        sid = _sid()
        log.begin(
            sid, consent=consent_for(ctx), context=ctx, user_id="Jane", started_at=T0, **V2
        )
        assert _only_row(log, sid).user_id is None

    def test_a_row_moved_onto_another_id_is_unreadable(self, tmp_path: Path) -> None:
        """AAD ``audit:<id>``: a row renamed to another session fails
        authentication — counted, never read as that session's, never
        overwritten."""
        log = _log(tmp_path)
        sid = _begin_linked(log)
        other = _sid()
        moved = _row_path(log, sid).with_name(f"{other}.enc")
        moved.write_bytes(_row_path(log, sid).read_bytes())
        before = moved.read_bytes()
        listing = log.rows()
        assert listing.unreadable == 1 and [r.session_id for r in listing.rows] == [sid]
        assert log.record_deletion(other, "discarded") is False
        assert moved.read_bytes() == before
        assert log.failure_count == 1

    def test_a_key_wrapped_for_another_store_is_refused(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        log.root.mkdir(parents=True)
        wrap_key_to_file(SessionCrypto(), log.root, description=SESSION_KEY_DESCRIPTION)
        with pytest.raises(AuditWriteError) as raised:
            _begin_linked(log)
        assert raised.value.reason == "key_unreadable"
        assert log.key_unreadable()
        assert list(log.root.glob("*/*.enc")) == []

    def test_a_key_that_cannot_be_read_right_now_is_not_unreadable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 7 LOW-007: a key file held by another program (its read
        fails with an OS error) refuses Start as ``unavailable`` and never
        offers D9's reset."""
        log = _log(tmp_path)
        _begin_unlinked(log)
        real_read = Path.read_bytes

        def held(self: Path) -> bytes:
            if self.name == KEY_FILENAME:
                raise PermissionError(32, "being used by another process")
            return real_read(self)

        monkeypatch.setattr(Path, "read_bytes", held)
        with pytest.raises(AuditWriteError) as raised:
            _begin_unlinked(log)
        assert raised.value.reason == "unavailable"
        assert not log.key_unreadable()
        monkeypatch.undo()
        _begin_unlinked(log)

    def test_a_dead_key_is_refused(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        log.root.mkdir(parents=True)
        (log.root / KEY_FILENAME).write_bytes(b"")
        with pytest.raises(AuditWriteError) as raised:
            _begin_unlinked(log)
        assert raised.value.reason == "key_unreadable"

    def test_a_missing_key_beside_rows_is_refused_never_replaced(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        sid = _begin_linked(log)
        (log.root / KEY_FILENAME).unlink()
        with pytest.raises(AuditWriteError) as raised:
            _begin_linked(log)
        assert raised.value.reason == "key_missing"
        assert not (log.root / KEY_FILENAME).exists()  # no new key orphaning the rows
        assert log.key_unreadable()
        assert log.record_deletion(sid, "discarded") is False

    def test_begin_refuses_a_second_row_for_one_session(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        sid = _begin_linked(log)
        before = _row_path(log, sid).read_bytes()
        with pytest.raises(AuditWriteError) as raised:
            _begin_linked(log, sid)
        assert raised.value.reason == "exists"
        assert _row_path(log, sid).read_bytes() == before

    def test_begin_is_refused_by_the_actual_write(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """C2 / round 1 PR-MED-002: the real row write is the check — a
        writable store whose write fails still refuses, leaving no row."""
        log = _log(tmp_path)
        _begin_unlinked(log)  # the store (and its key) exist and are writable

        def full_disk(*_args: Any, **_kwargs: Any) -> None:
            raise StoreWriteError("failed writing audit row: disk full")

        monkeypatch.setattr(audit_mod, "atomic_write_bytes", full_disk)
        sid = _sid()
        with pytest.raises(AuditWriteError) as raised:
            log.begin(
                sid,
                consent=unlinked_consent(T0),
                context=None,
                user_id=None,
                started_at=T0,
                **V2,
            )
        assert raised.value.reason == "write_failed"
        assert "disk full" not in str(raised.value)  # authored words, never OS text
        assert list(log.root.glob(f"*/{sid}*")) == []

    def test_a_newer_row_is_kept_byte_for_byte(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        _begin_unlinked(log)
        sid = _sid()
        path = _seal(log, sid, {"schema_version": 4, "session_id": sid, "anything": [1, 2]})
        before = path.read_bytes()
        assert log.record_deletion(sid, "expired") is False
        assert log.record_start_failed(sid) is False
        assert path.read_bytes() == before
        assert log.rows().newer == 1
        assert log.failure_count == 2

    def test_an_unreadable_row_is_counted_and_never_overwritten(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        _begin_unlinked(log)
        sid = _sid()
        path = log.root / "2026-10" / f"{sid}.enc"
        path.write_bytes(b"\x00" * 80)
        assert log.record_deletion(sid, "discarded") is False
        assert path.read_bytes() == b"\x00" * 80
        assert log.rows().unreadable == 1

    def test_update_never_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        logger = logging.getLogger("test-audit-never-raises")
        log = _log(tmp_path, logger=logger)
        sid = _begin_unlinked(log)
        # PR-LOW-007: every injected failure carries text that must never
        # reach a log — only the fixed event and its stage code may.
        secret = "Jane Citizen C:\\Users\\jane\\note text"

        def refusing_change(_row: AuditRow, _now: datetime) -> AuditRow:
            raise RuntimeError(secret)

        with caplog.at_level(logging.DEBUG):
            assert log.update(sid, refusing_change, stage="completion") is False
            monkeypatch.setattr(
                audit_mod,
                "atomic_write_bytes",
                lambda *a, **k: (_ for _ in ()).throw(StoreWriteError(secret)),
            )
            assert log.record_deletion(sid, "discarded") is False
            monkeypatch.undo()
            (log.root / KEY_FILENAME).write_bytes(b"")  # a dead key
            assert (
                log.record_write(sid, attempt=1, outcome="attempting", finished_at=None) is False
            )
            assert log.update("not-a-session-id", refusing_change, stage="write") is False
        assert log.failure_count == 4
        messages = [r.getMessage() for r in caplog.records if r.name == logger.name]
        assert messages == [
            "audit_update_failed detail_code=completion",
            "audit_update_failed detail_code=discarded",
            "audit_update_failed detail_code=write",
            "audit_update_failed detail_code=write",
        ]
        for record in caplog.records:  # every logger, not only the audit's
            assert record.exc_info is None and record.exc_text is None and record.stack_info is None
            assert secret not in record.getMessage()
            assert all(secret not in str(value) for value in vars(record).values())
        assert secret not in caplog.text

    def test_the_sink_is_resolved_per_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The lessons rule for a never-raising wrapper: a store failure
        patched in AFTER construction still reaches ``update``."""
        log = _log(tmp_path)
        sid = _begin_unlinked(log)
        monkeypatch.setattr(
            audit_mod,
            "atomic_write_bytes",
            lambda *a, **k: (_ for _ in ()).throw(StoreWriteError("late failure")),
        )
        assert log.record_deletion(sid, "discarded") is False
        assert log.failure_count == 1

    def test_the_end_is_recorded_only_from_pending(self, tmp_path: Path) -> None:
        """An ``orphan_gc`` of a directory a Complete already ended (its
        removal failed) never overwrites that Complete."""
        log = _log(tmp_path)
        sid = _begin_linked(log)
        assert log.record_completion(sid, CompletionFacts(), deletion="completed")
        assert log.record_deletion(sid, "orphan_gc")
        row = _only_row(log, sid)
        assert row.deletion.state == "completed"
        assert [event.code for event in row.events] == ["started", "completed"]

    @pytest.mark.parametrize("end", ["completed", "discarded", "expired"])
    def test_a_start_failure_still_takes_the_sessions_real_end(
        self, tmp_path: Path, end: str
    ) -> None:
        """Round 7 LOW-003: a Start whose cleanup failed can leave a
        recoverable session; its later Complete, Discard or expiry is still
        recorded (D6: "Complete, not the earlier failure, decides") — and a
        second Start failure never overwrites a real end."""
        log = _log(tmp_path)
        sid = _begin_linked(log)
        assert log.record_start_failed(sid)
        if end == "completed":
            assert log.record_completion(sid, CompletionFacts(), deletion="completed")
        else:
            assert log.record_deletion(sid, end)  # type: ignore[arg-type]
        assert log.record_start_failed(sid)
        row = _only_row(log, sid)
        assert row.deletion.state == end
        assert [event.code for event in row.events] == ["started", "start_failed", end]

    def test_a_completion_records_models_deletion_and_past_session(
        self, tmp_path: Path
    ) -> None:
        clock = _Clock()
        log = _log(tmp_path, clock)
        sid = _begin_linked(log)
        clock.now = T0 + timedelta(minutes=20)
        facts = CompletionFacts(
            transcription_model="small",
            speaker_model="wespeaker-resnet34",
            note_provider="extractive-v1",
            note_schema_version="2",
            template_profile="clinic-a",
            note_style="clean",
            language_model_id="qwen3-4b",
            prompt_version="narrative-v2",
            note_provenance="known",
        )
        assert log.record_completion(sid, facts, deletion="completed_without_note")
        row = _only_row(log, sid)
        assert row.deletion.state == "completed_without_note"
        assert row.deletion.at == clock.now
        assert row.past_session.state == "none"
        assert row.note_provenance == "known"
        assert row.models is not None
        assert (row.models.transcription_model, row.models.note_style) == ("small", "clean")
        assert (row.models.language_model_id, row.models.prompt_version) == (
            "qwen3-4b",
            "narrative-v2",
        )
        assert row.models.generated_provider == "unknown"  # Task 2.1 fills it

    def test_a_fact_the_row_refuses_is_counted_never_raised(self, tmp_path: Path) -> None:
        """Round 6 LOW-001: the completion is recorded after the key is gone,
        so even a fact that is not a token is a counted failure — never an
        exception into Complete."""
        log = _log(tmp_path)
        sid = _begin_linked(log)
        facts = CompletionFacts(note_provider="Jane Citizen")  # not one token
        assert log.record_completion(sid, facts, deletion="completed") is False
        assert log.failure_count == 1
        assert _only_row(log, sid).deletion.state == "pending"

    def test_the_write_result_is_recorded(self, tmp_path: Path) -> None:
        clock = _Clock()
        log = _log(tmp_path, clock)
        sid = _begin_linked(log)
        assert log.record_write(sid, attempt=1, outcome="attempting", finished_at=None)
        assert _only_row(log, sid).write.last_outcome == "attempting"
        finished = T0 + timedelta(minutes=3)
        assert log.record_write(sid, attempt=1, outcome="written", finished_at=finished)
        assert log.record_write_refusal(sid, "write_forbidden")
        write = _only_row(log, sid).write
        assert (write.attempts, write.last_outcome, write.written_at) == (1, "written", finished)
        assert write.last_refusal == "write_forbidden"

    def test_clinikos_refusal_code_and_a_pre_audit_date(self, tmp_path: Path) -> None:
        """Round 6 LOW-006: a ``refused`` transition records Cliniko's fixed
        code; LOW-007: a write that is a pre-audit session's first touch
        dates the row by the session's own creation time."""
        log = _log(tmp_path)
        sid = _sid()
        created = datetime(2026, 9, 30, 9, 0, tzinfo=UTC).timestamp()
        assert log.record_write(
            sid,
            attempt=1,
            outcome="refused",
            finished_at=T0,
            refusal="finalised_before_write",
            created_at=created,
        )
        row = _only_row(log, sid)
        assert (row.origin, row.session_date) == ("pre_audit", date(2026, 9, 30))
        assert row.write.last_refusal == "finalised_before_write"
        other = _sid()
        assert log.record_write_refusal(other, "write_forbidden", created_at=created)
        assert _only_row(log, other).session_date == date(2026, 9, 30)

    def test_the_dev_build_refusal_is_recorded(self, tmp_path: Path) -> None:
        """Installation plan Task 1.6 (round 9): the dev write guard's code
        is a refusal code the real store accepts, not only the fake one."""
        log = _log(tmp_path)
        sid = _begin_linked(log)
        assert log.record_write_refusal(sid, "dev_build_writes_off")
        assert _only_row(log, sid).write.last_refusal == "dev_build_writes_off"

    def test_a_refusal_code_that_is_not_a_code_is_refused(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        sid = _begin_linked(log)
        assert log.record_write_refusal(sid, "Could not write the note for Jane") is False
        assert _only_row(log, sid).write.last_refusal is None

    def test_events_are_capped(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        sid = _begin_linked(log)
        for attempt in range(1, MAX_EVENTS + 5):
            assert log.record_write(sid, attempt=attempt, outcome="refused", finished_at=T0)
        events = _only_row(log, sid).events
        assert len(events) == MAX_EVENTS
        assert events[-1].code == "write_refused"

    def test_past_session_outcomes_after_the_complete(self, tmp_path: Path) -> None:
        """Tasks 3.1 / 3.2 and round 12 LOW-002: a reconciled commit fills
        only a row the Complete never reached; Delete now and expiry follow
        an entry that existed; a deletion or a mock outcome is never
        rewritten."""
        clock = _Clock()
        log = _log(tmp_path, clock)
        # A Complete interrupted before its audit update: reconciliation fills it.
        crashed = _begin_linked(log)
        clock.now = T0 + timedelta(minutes=5)
        assert log.record_past_session(crashed, "archived")
        row = _only_row(log, crashed)
        assert (row.past_session.state, row.past_session.at) == ("archived", clock.now)
        assert row.deletion.state == "pending"  # the Complete's own outcome is not guessed
        assert row.events[-1].code == "past_session_archived"
        # An archived row is not re-archived (no write); a later Delete now is kept.
        events = len(row.events)
        assert log.record_past_session(crashed, "archived")
        assert len(_only_row(log, crashed).events) == events
        clock.now = T0 + timedelta(days=1)
        assert log.record_past_session(crashed, "deleted_early")
        row = _only_row(log, crashed)
        assert (row.past_session.state, row.past_session.at) == ("deleted_early", clock.now)
        assert row.events[-1].code == "past_session_deleted_early"
        deleted_at, events = row.past_session.at, len(row.events)
        # Round 19 PR-LOW-017: a repeated outcome writes nothing — the same
        # event count and the first timestamp, however much later.
        clock.now = T0 + timedelta(days=2)
        assert log.record_past_session(crashed, "deleted_early")
        assert log.record_past_session(crashed, "expired")  # nothing left to expire
        row = _only_row(log, crashed)
        assert (row.past_session.state, row.past_session.at) == ("deleted_early", deleted_at)
        assert len(row.events) == events
        # A completed, archived row expires; a mock one is never touched.
        expired = _begin_linked(log)
        assert log.record_completion(
            expired, CompletionFacts(past_session="archived"), deletion="completed"
        )
        assert log.record_past_session(expired, "expired")
        row = _only_row(log, expired)
        assert (row.past_session.state, row.past_session.at) == ("expired", clock.now)
        assert row.events[-1].code == "past_session_expired"
        expired_at, events = row.past_session.at, len(row.events)
        clock.now = T0 + timedelta(days=3)
        assert log.record_past_session(expired, "expired")
        assert log.record_past_session(expired, "deleted_early")
        row = _only_row(log, expired)
        assert (row.past_session.state, row.past_session.at) == ("expired", expired_at)
        assert len(row.events) == events
        mock = _begin_linked(log)
        assert log.record_completion(
            mock, CompletionFacts(past_session="not_kept_mock"), deletion="completed"
        )
        assert log.record_past_session(mock, "archived")
        assert log.record_past_session(mock, "deleted_early")
        assert _only_row(log, mock).past_session.state == "not_kept_mock"
        assert log.failure_count == 0

    def test_row_for_reads_one_row_and_creates_nothing(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        assert log.row_for(_sid()) is None  # no store at all
        assert not log.root.exists()
        sid = _begin_linked(log)
        assert log.record_write(sid, attempt=1, outcome="written", finished_at=T0)
        row = log.row_for(sid)
        assert row is not None and row.write.last_outcome == "written"
        assert log.row_for(_sid()) is None  # no row for that session
        # A newer-format row is never shown (D8).
        newer = _sid()
        _seal(log, newer, {"schema_version": 4, "session_id": newer})
        assert log.row_for(newer) is None
        # Round 16 LOW-006: one id in two month folders is never "no record".
        twice = _sid()
        _seal(log, twice, {"schema_version": 4, "session_id": twice}, month="2026-09")
        _seal(log, twice, {"schema_version": 4, "session_id": twice}, month="2026-10")
        with pytest.raises(AuditUnavailable) as twice_info:
            log.row_for(twice)
        assert twice_info.value.reason == "unavailable"
        # A missing key beside rows is the documented refusal, not a fresh key.
        (log.root / KEY_FILENAME).unlink()
        with pytest.raises(AuditUnavailable) as info:
            log.row_for(sid)
        assert info.value.reason == "key_missing"
        assert not (log.root / KEY_FILENAME).exists()


@windows_only
class TestPreAuditRows:
    """D8 / round 1 PR-MED-004: a session started before the audit existed
    gets a ``pre_audit`` row the first time it is touched."""

    def test_dated_by_the_sessions_own_creation_time(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        sid = _sid()
        created = datetime(2026, 9, 12, 23, 30, tzinfo=UTC).timestamp()
        assert log.record_deletion(sid, "expired", created_at=created)
        row = _only_row(log, sid)
        assert row.origin == "pre_audit"
        assert row.session_date == date(2026, 9, 12)
        assert _row_path(log, sid).parent.name == "2026-09"
        assert row.deletion.state == "expired"
        assert row.consent_confirmed_at is None and row.linked is None

    @pytest.mark.parametrize(
        "created",
        [
            None,
            -math.inf,
            math.nan,
            (T0 + timedelta(days=3)).timestamp(),
            0.0,  # round 7 LOW-004: a corrupt header / reset clock (1970)
            -1e12,  # before any date Windows can convert
            datetime(2025, 12, 31, 23, 59, tzinfo=UTC).timestamp(),  # before the audit's plan
        ],
    )
    def test_a_missing_or_untrusted_date_is_the_sweep_time(
        self, tmp_path: Path, created: float | None
    ) -> None:
        log = _log(tmp_path)
        sid = _sid()
        assert log.record_deletion(sid, "orphan_gc", created_at=created)
        assert _only_row(log, sid).session_date == T0.date()

    def test_a_pre_audit_row_names_no_mode_or_version(self, tmp_path: Path) -> None:
        """Pilot plan Task 1.3: nothing recorded the mode of a session with
        no row, so the row does not claim one."""
        log = _log(tmp_path)
        sid = _sid()
        assert log.record_deletion(sid, "expired")
        row = _only_row(log, sid)
        assert (row.mode, row.app_version) == (None, None)


def _v1_document(row: AuditRow) -> dict[str, Any]:
    """``row`` as the v1 schema (before 0.2.0) stored it: no mode, no
    version, ``schema_version`` 1."""
    document = json.loads(row.model_dump_json())
    del document["mode"], document["app_version"]
    del document["development_consent_version"], document["recording"]
    document["schema_version"] = 1
    return document


def _v2_document(row: AuditRow) -> dict[str, Any]:
    """``row`` as the v2 schema (0.2.0) stored it: no development consent
    version, no recording record, ``schema_version`` 2."""
    document = json.loads(row.model_dump_json())
    del document["development_consent_version"], document["recording"]
    document["schema_version"] = 2
    return document


@windows_only
class TestAuditRowV2:
    """Pilot plan Task 1.3 (D6, D7): ``mode`` and ``app_version`` on every
    Start's row, a v1 row upgraded in ``_decode`` BEFORE validation, and a
    newer row (v4 since development-recordings Task 1.4) read as newer
    (Start unaffected)."""

    def test_begin_records_the_mode_and_the_version(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        shadow = _begin_linked(log, mode=SessionMode.SHADOW)
        normal = _begin_unlinked(log)
        assert _only_row(log, shadow).mode is SessionMode.SHADOW
        assert _only_row(log, normal).mode is SessionMode.NORMAL
        for sid in (shadow, normal):
            row = _only_row(log, sid)
            assert (row.schema_version, row.app_version) == (3, VERSION)

    @pytest.mark.parametrize("bad", ["0.2", "0.2.0-dev", "v0.2.0", "0.2.0\n", "", "0. 2.0"])
    def test_a_version_the_row_cannot_hold_is_left_out_not_refused(
        self, tmp_path: Path, bad: str
    ) -> None:
        log = _log(tmp_path)
        sid = _sid()
        log.begin(
            sid,
            consent=unlinked_consent(T0),
            context=None,
            user_id=None,
            started_at=T0,
            mode=SessionMode.NORMAL,
            app_version=bad,
            development_consent_version=None,
        )
        assert _only_row(log, sid).app_version is None

    def test_the_version_field_refuses_free_text(self) -> None:
        with pytest.raises(ValueError):
            AuditRow(
                session_id=_sid(),
                session_date=date(2026, 10, 1),
                origin="recorded",
                app_version="Jane Citizen",
            )
        with pytest.raises(ValueError):
            AuditRow(
                session_id=_sid(),
                session_date=date(2026, 10, 1),
                origin="recorded",
                mode="practice",  # type: ignore[arg-type]
            )

    def test_a_v1_row_reads_as_normal_with_no_version(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        sid = _begin_linked(log)
        _seal(log, sid, _v1_document(_only_row(log, sid)))
        row = _only_row(log, sid)
        assert (row.schema_version, row.mode, row.app_version) == (3, SessionMode.NORMAL, None)
        assert row.treatment_note_id == NOTE  # the rest of the row as stored
        assert (row.development_consent_version, row.recording) == (None, RecordingRecord())

    def test_a_v1_row_is_upgraded_before_validation(self) -> None:
        """Constraint 2: ``_decode`` upgrades; ``AuditRow`` itself takes the
        current version only (a v1 document handed to the model directly is
        refused)."""
        row = AuditRow(session_id=_sid(), session_date=date(2026, 10, 1), origin="recorded")
        document = _v1_document(row)
        with pytest.raises(ValueError):
            AuditRow.model_validate(document)
        decoded = audit_mod._decode(json.dumps(document).encode())  # noqa: SLF001
        assert isinstance(decoded, AuditRow) and decoded.mode is SessionMode.NORMAL

    @pytest.mark.parametrize("field", ["mode", "app_version"])
    def test_a_v1_row_naming_a_v2_field_is_unreadable(self, tmp_path: Path, field: str) -> None:
        log = _log(tmp_path)
        sid = _begin_linked(log)
        document = _v1_document(_only_row(log, sid))
        document[field] = "normal" if field == "mode" else VERSION
        path = _seal(log, sid, document)
        before = path.read_bytes()
        assert log.rows().unreadable == 1
        assert log.record_deletion(sid, "discarded") is False
        assert path.read_bytes() == before

    def test_an_updated_v1_row_is_written_back_as_v3(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        sid = _begin_unlinked(log)
        _seal(log, sid, _v1_document(_only_row(log, sid)))
        assert log.record_deletion(sid, "discarded")
        crypto = unwrap_key_from_file(log.root, description=AUDIT_KEY_DESCRIPTION)
        try:
            stored = json.loads(
                crypto.decrypt(_row_path(log, sid).read_bytes(), b"audit:" + sid.encode())
            )
        finally:
            crypto.destroy()
        assert (stored["schema_version"], stored["mode"], stored["app_version"]) == (
            3,
            "normal",
            None,
        )
        assert stored["development_consent_version"] is None
        assert _only_row(log, sid).deletion.state == "discarded"

    def test_a_v1_row_exports_as_normal_with_an_empty_version(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        sid = _begin_linked(log)
        _seal(log, sid, _v1_document(_only_row(log, sid)))
        target = tmp_path / "export.csv"
        assert log.export_csv(target) == 1
        rows = list(csv.reader(io.StringIO(target.read_text(encoding="utf-8-sig"))))
        exported = dict(zip(CSV_COLUMNS, rows[1], strict=True))
        assert (exported["mode"], exported["app_version"]) == ("normal", "")

    def test_a_v4_row_is_newer_and_start_is_unaffected(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        _begin_unlinked(log)
        sid = _sid()
        path = _seal(log, sid, {"schema_version": 4, "session_id": sid, "mode": "pilot"})
        before = path.read_bytes()
        assert log.record_deletion(sid, "discarded") is False
        assert path.read_bytes() == before
        assert log.rows().newer == 1
        _begin_unlinked(log)  # a newer row never refuses another Start
        assert len(log.rows().rows) == 2


def _decode_document(document: dict[str, Any]) -> Any:
    return audit_mod._decode(json.dumps(document).encode())  # noqa: SLF001


class TestAuditRowV3Decode:
    """Development-recordings plan Task 1.4 (D15): the v3 row's decoding
    rules, without DPAPI."""

    def _row(self) -> AuditRow:
        return AuditRow(session_id=_sid(), session_date=date(2026, 10, 7), origin="recorded")

    def test_a_v2_row_upgrades_to_v3_with_the_defaults(self) -> None:
        decoded = _decode_document(_v2_document(self._row()))
        assert isinstance(decoded, AuditRow)
        assert decoded.schema_version == 3
        assert (decoded.development_consent_version, decoded.recording) == (
            None,
            RecordingRecord(),
        )

    def test_a_v1_row_chains_through_v2_to_v3(self) -> None:
        decoded = _decode_document(_v1_document(self._row()))
        assert isinstance(decoded, AuditRow)
        assert (decoded.schema_version, decoded.mode, decoded.recording) == (
            3,
            SessionMode.NORMAL,
            RecordingRecord(),
        )

    @pytest.mark.parametrize("field", ["development_consent_version", "recording"])
    def test_a_v2_row_naming_a_v3_field_is_refused(self, field: str) -> None:
        document = _v2_document(self._row())
        document[field] = None if field == "development_consent_version" else {}
        with pytest.raises(ValueError):
            _decode_document(document)

    def test_a_v3_row_naming_no_development_consent_version_is_refused(self) -> None:
        """Mirrors the v2 ``mode`` rule: the default is for building a row."""
        row = self._row()
        document = json.loads(row.to_bytes())
        assert _decode_document(document) == row
        del document["development_consent_version"]
        with pytest.raises(ValueError):
            _decode_document(document)

    def test_a_v3_row_naming_no_mode_is_refused(self) -> None:
        document = json.loads(self._row().to_bytes())
        del document["mode"]
        with pytest.raises(ValueError):
            _decode_document(document)

    def test_a_v3_row_naming_no_recording_record_is_refused(self) -> None:
        """Review round 8 LOW-006: every v3 row this app writes names its
        ``recording`` record — the default is for building a row."""
        document = json.loads(self._row().to_bytes())
        del document["recording"]
        with pytest.raises(ValueError):
            _decode_document(document)

    @pytest.mark.parametrize("version", [3.0, True, "3"])
    def test_a_version_that_is_not_an_integer_is_refused(self, version: Any) -> None:
        document = json.loads(self._row().to_bytes())
        document["schema_version"] = version
        with pytest.raises(ValueError):
            _decode_document(document)

    def test_v4_is_newer(self) -> None:
        document = json.loads(self._row().to_bytes())
        document["schema_version"] = 4
        assert _decode_document(document) is audit_mod._NEWER  # noqa: SLF001

    def test_the_new_fields_refuse_content(self) -> None:
        for update in (
            {"development_consent_version": "Jane Citizen"},
            {"recording": {"exports": -1}},
            {"recording": {"kept_at": "2026-10-07T09:00:00"}},  # naive
            {"recording": {"note": "x"}},
        ):
            with pytest.raises(ValueError):
                AuditRow.model_validate({**self._row().model_dump(), **update})

    def test_a_rendering_of_the_recording_record_alone_is_dropped(self) -> None:
        """C6: the nested record can be rendered without any of the row's
        other names, so its own distinctive name is registered."""
        record = RecordingRecord(kept_at=T0, exports=2)
        tripwire = PayloadTripwireFilter()
        for rendered in (repr(record), str(record.model_dump()), record.model_dump_json()):
            log_record = logging.LogRecord("t", logging.INFO, __file__, 1, rendered, None, None)
            assert tripwire.filter(log_record) is False, rendered
        assert "kept_at=" in _PAYLOAD_SIGNATURES


@windows_only
class TestAuditRowV3:
    """Development-recordings plan Task 1.4 (D3, D15): the development
    consent's version on Start's row, and the kept recording's three facts —
    fields, never events."""

    def test_begin_records_the_development_consent_version(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        kept = _begin_linked(log, development=DEVELOPMENT)
        not_kept = _begin_unlinked(log)
        assert _only_row(log, kept).development_consent_version == DEVELOPMENT
        assert _only_row(log, not_kept).development_consent_version is None
        for sid in (kept, not_kept):
            assert _only_row(log, sid).recording == RecordingRecord()

    def test_a_version_the_row_cannot_hold_refuses_start(self, tmp_path: Path) -> None:
        """Unlike the app version (left out), the consent version comes from
        the app's own constant: a value the token refuses is a failed Start,
        and nothing is written."""
        log = _log(tmp_path)
        with pytest.raises(AuditWriteError):
            _begin_unlinked(log, development="Jane Citizen")
        assert log.rows().rows == ()

    def test_a_v2_row_on_disk_reads_and_is_written_back_as_v3(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        sid = _begin_linked(log)
        _seal(log, sid, _v2_document(_only_row(log, sid)))
        row = _only_row(log, sid)
        assert (row.schema_version, row.development_consent_version) == (3, None)
        assert log.record_deletion(sid, "discarded")
        assert _only_row(log, sid).deletion.state == "discarded"

    @pytest.mark.parametrize("kept", [True, False])
    def test_the_completion_write_sets_kept_at(self, tmp_path: Path, kept: bool) -> None:
        clock = _Clock()
        log = _log(tmp_path, clock)
        sid = _begin_linked(log, development=DEVELOPMENT if kept else None)
        clock.now = T0 + timedelta(minutes=30)
        facts = CompletionFacts(past_session="archived", recording_kept=kept)
        assert log.record_completion(sid, facts, deletion="completed")
        row = _only_row(log, sid)
        assert row.recording == RecordingRecord(kept_at=clock.now if kept else None)
        assert [event.code for event in row.events] == ["started", "completed"]

    def test_the_kept_repair_is_idempotent_and_never_moves_an_earlier_time(
        self, tmp_path: Path
    ) -> None:
        clock = _Clock()
        log = _log(tmp_path, clock)
        sid = _begin_linked(log, development=DEVELOPMENT)
        completed = T0 + timedelta(minutes=30)
        assert log.record_recording_kept(sid, completed)
        assert _only_row(log, sid).recording.kept_at == completed
        path = _row_path(log, sid)
        before = path.read_bytes()
        assert log.record_recording_kept(sid, completed + timedelta(days=1))
        assert path.read_bytes() == before  # nothing written the second time
        assert _only_row(log, sid).recording.kept_at == completed

    def test_a_row_the_repair_has_to_make_is_dated_by_the_entry(self, tmp_path: Path) -> None:
        """Review round 8 LOW-002: with no row (a reset set the store aside),
        the repair's ``pre_audit`` row lands in the session's month, not
        today's; an Export's and a Delete recording's take ``created_at``."""
        log = _log(tmp_path)  # the clock reads T0, 2026-10-01
        _begin_unlinked(log)  # the store's key
        kept, exported, deleted = _sid(), _sid(), _sid()
        completed = datetime(2026, 8, 15, 9, 0, tzinfo=UTC)
        assert log.record_recording_kept(kept, completed)
        row = _only_row(log, kept)
        assert (row.origin, row.session_date) == ("pre_audit", date(2026, 8, 15))
        assert row.recording.kept_at == completed
        assert _row_path(log, kept).parent.name == "2026-08"
        started = datetime(2026, 7, 2, 9, 0, tzinfo=UTC).timestamp()
        assert log.record_recording_exported(exported, created_at=started)
        assert log.record_recording_deleted(deleted, created_at=started)
        for sid in (exported, deleted):
            assert _only_row(log, sid).session_date == date(2026, 7, 2)

    def test_delete_recording_sets_deleted_at_once(self, tmp_path: Path) -> None:
        clock = _Clock()
        log = _log(tmp_path, clock)
        sid = _begin_linked(log, development=DEVELOPMENT)
        assert log.record_recording_kept(sid, T0)
        clock.now = T0 + timedelta(days=2)
        assert log.record_recording_deleted(sid)
        clock.now = T0 + timedelta(days=3)
        assert log.record_recording_deleted(sid)
        assert _only_row(log, sid).recording.deleted_at == T0 + timedelta(days=2)

    def test_exports_count_up_and_never_evict_the_events(self, tmp_path: Path) -> None:
        """D15: 40 exports — more than ``MAX_EVENTS`` — leave ``started``
        in the events and the count exact."""
        log = _log(tmp_path)
        sid = _begin_linked(log, development=DEVELOPMENT)
        for _ in range(MAX_EVENTS + 8):
            assert log.record_recording_exported(sid)
        row = _only_row(log, sid)
        assert row.recording.exports == MAX_EVENTS + 8
        assert [event.code for event in row.events] == ["started"]

    @pytest.mark.parametrize("state", ["deleted_early", "expired"])
    def test_delete_now_and_expiry_record_a_kept_recordings_deletion(
        self, tmp_path: Path, state: Any
    ) -> None:
        """Round 3 PR-MED-032: those paths destroy the audio with the entry
        key, so ``recording.deleted_at`` follows — on a kept row only, and
        never moving an earlier audio-only deletion."""
        clock = _Clock()
        log = _log(tmp_path, clock)
        kept, unkept, earlier = (_begin_linked(log) for _ in range(3))
        for sid in (kept, earlier):
            assert log.record_recording_kept(sid, T0)
        clock.now = T0 + timedelta(days=1)
        assert log.record_recording_deleted(earlier)
        clock.now = T0 + timedelta(days=5)
        for sid in (kept, unkept, earlier):
            assert log.record_past_session(sid, state)
        assert _only_row(log, kept).recording.deleted_at == clock.now
        assert _only_row(log, unkept).recording == RecordingRecord()
        assert _only_row(log, earlier).recording.deleted_at == T0 + timedelta(days=1)
        for sid in (kept, unkept, earlier):
            assert _only_row(log, sid).past_session.state == state

    def test_an_archived_reconciliation_leaves_the_recording_alone(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        sid = _begin_linked(log)
        assert log.record_recording_kept(sid, T0)
        assert log.record_past_session(sid, "archived")
        assert _only_row(log, sid).recording == RecordingRecord(kept_at=T0)

    def test_export_names_the_four_v3_columns_last(self, tmp_path: Path) -> None:
        assert CSV_COLUMNS[-4:] == (
            "development_consent_version",
            "recording.kept_at",
            "recording.deleted_at",
            "recording.exports",
        )
        clock = _Clock()
        log = _log(tmp_path, clock)
        kept = _begin_linked(log, development=DEVELOPMENT)
        plain = _begin_unlinked(log)
        assert log.record_recording_kept(kept, T0)
        clock.now = T0 + timedelta(days=1)
        assert log.record_recording_deleted(kept)
        assert log.record_recording_exported(kept)
        target = tmp_path / "export.csv"
        assert log.export_csv(target) == 2
        rows = list(csv.reader(io.StringIO(target.read_text(encoding="utf-8-sig"))))
        by_id = {row[0]: dict(zip(CSV_COLUMNS, row, strict=True)) for row in rows[1:]}
        assert [by_id[kept][name] for name in CSV_COLUMNS[-4:]] == [
            DEVELOPMENT,
            "2026-10-01T07:30:00+00:00",
            "2026-10-02T07:30:00+00:00",
            "1",
        ]
        assert [by_id[plain][name] for name in CSV_COLUMNS[-4:]] == ["", "", "", "0"]


@windows_only
class TestLocalDate:
    """Round 6 MED-002: ``session_date`` (and the month folder) is the
    practitioner's calendar date, not the UTC one."""

    AEST = timezone(timedelta(hours=10))
    # 08:00 on 1 Oct in Melbourne (standard time) is 22:00 on 30 Sep UTC.
    MORNING = datetime(2026, 10, 1, 8, 0, tzinfo=AEST)

    def test_a_morning_session_is_dated_its_own_local_day(self, tmp_path: Path) -> None:
        log = _log(tmp_path, local_zone=self.AEST)
        sid = _begin_unlinked(log, started_at=self.MORNING.astimezone(UTC))
        assert _only_row(log, sid).session_date == date(2026, 10, 1)
        assert _row_path(log, sid).parent.name == "2026-10"

    def test_a_pre_audit_row_and_its_fallback_are_local_too(self, tmp_path: Path) -> None:
        log = _log(tmp_path, _Clock(self.MORNING.astimezone(UTC)), local_zone=self.AEST)
        dated, undated = _sid(), _sid()
        assert log.record_deletion(dated, "expired", created_at=self.MORNING.timestamp())
        assert log.record_deletion(undated, "orphan_gc", created_at=None)
        assert _only_row(log, dated).session_date == date(2026, 10, 1)
        assert _only_row(log, undated).session_date == date(2026, 10, 1)

    def test_the_default_zone_is_this_computers(self, tmp_path: Path) -> None:
        """Round 7 LOW-010: a moment whose local date and UTC date DIFFER on
        this host, so a default silently read as UTC would fail."""
        offset = datetime(2026, 10, 1, 12).astimezone().utcoffset()
        if not offset:
            pytest.skip("this host's zone is UTC on the day")
        # Just after local midnight east of UTC, just before it west of UTC.
        wall = datetime(2026, 10, 1, 0, 30) if offset > timedelta(0) else datetime(
            2026, 10, 1, 23, 30
        )
        started = wall.astimezone().astimezone(UTC)
        assert started.date() != date(2026, 10, 1)
        log = AuditLog(tmp_path / "audit", clock=_Clock())
        sid = _begin_unlinked(log, started_at=started)
        assert _only_row(log, sid).session_date == date(2026, 10, 1)


@windows_only
class TestPrune:
    def test_a_month_goes_at_its_end_plus_seven_years(self, tmp_path: Path) -> None:
        clock = _Clock(datetime(2019, 9, 20, tzinfo=UTC))
        log = _log(tmp_path, clock)
        old = _begin_unlinked(log, started_at=datetime(2019, 9, 20, tzinfo=UTC))
        clock.now = T0
        recent = _begin_unlinked(log)
        (log.root / "not-a-month").mkdir()
        # The month's end + 7 years + the one-day local-calendar margin.
        assert month_prune_at(2019, 9) == datetime(2026, 10, 2, tzinfo=UTC)
        clock.now = datetime(2026, 10, 1, 23, 59, 59, tzinfo=UTC)
        assert log.prune() == 0
        assert _only_row(log, old).session_id == old
        clock.now = datetime(2026, 10, 2, tzinfo=UTC)
        assert log.prune() == 1
        assert not (log.root / "2019-09").exists()
        assert [row.session_id for row in log.rows().rows] == [recent]
        assert (log.root / KEY_FILENAME).is_file()
        assert (log.root / "not-a-month").is_dir()

    def test_december_rolls_into_the_next_year(self) -> None:
        assert month_prune_at(2020, 12) == datetime(2028, 1, 2, tzinfo=UTC)

    def test_prune_never_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        log = _log(tmp_path, _Clock(datetime(2019, 3, 1, tzinfo=UTC)))
        _begin_unlinked(log, started_at=datetime(2019, 3, 1, tzinfo=UTC))
        log._clock = _Clock(datetime(2030, 1, 1, tzinfo=UTC))  # noqa: SLF001

        def locked(*_args: Any, **_kwargs: Any) -> None:
            raise PermissionError("in use")

        monkeypatch.setattr(audit_mod.shutil, "rmtree", locked)
        assert log.prune() == 0
        assert log.failure_count == 1

    def test_a_folder_no_date_can_hold_is_skipped_not_fatal(self, tmp_path: Path) -> None:
        """Round 6 LOW-009: a month folder whose prune date overflows is left
        alone — skipped, not a failure that ends the prune."""
        log = _log(tmp_path, _Clock(datetime(2030, 1, 1, tzinfo=UTC)))
        for month in ("2019-01", "9999-12"):
            (log.root / month).mkdir(parents=True)
        assert log.prune() == 1
        assert not (log.root / "2019-01").exists()
        assert (log.root / "9999-12").is_dir()
        assert log.failure_count == 0

    def test_prune_needs_no_key(self, tmp_path: Path) -> None:
        log = _log(tmp_path, _Clock(datetime(2030, 1, 1, tzinfo=UTC)))
        (log.root / "2019-01").mkdir(parents=True)
        (log.root / "2019-01" / f"{_sid()}.enc").write_bytes(b"sealed")
        assert log.prune() == 1
        assert not (log.root / KEY_FILENAME).exists()


@windows_only
class TestCsv:
    @pytest.mark.parametrize("lead", ["=", "+", "-", "@", "\t", "\r"])
    def test_the_formula_guard(self, lead: str) -> None:
        assert csv_cell(f"{lead}HYPERLINK(1)") == f"'{lead}HYPERLINK(1)"

    def test_plain_cells(self) -> None:
        assert csv_cell(None) == ""
        assert csv_cell(True) == "yes" and csv_cell(False) == "no"
        assert csv_cell(3) == "3"
        assert csv_cell(T0) == "2026-10-01T07:30:00+00:00"

    def test_export_writes_every_readable_row(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        linked = _begin_linked(log)
        _begin_unlinked(log)
        log.record_write_refusal(linked, "write_forbidden")
        target = tmp_path / "export.csv"
        assert log.export_csv(target) == 2
        raw = target.read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf")  # a BOM, for Excel
        rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
        assert tuple(rows[0]) == CSV_COLUMNS
        by_id = {row[0]: dict(zip(CSV_COLUMNS, row, strict=True)) for row in rows[1:]}
        assert by_id[linked]["treatment_note_id"] == NOTE
        assert by_id[linked]["write.last_refusal"] == "write_forbidden"
        assert by_id[linked]["linked"] == "yes"
        assert (by_id[linked]["deletion.state"], by_id[linked]["past_session.state"]) == (
            "pending",
            "none",
        )

    def test_export_names_the_mode_and_the_version(self, tmp_path: Path) -> None:
        """Pilot plan Task 1.3: the two v2 columns, filled per row — last
        until development-recordings Task 1.4's four v3 columns followed."""
        assert CSV_COLUMNS[-6:-4] == ("mode", "app_version")
        log = _log(tmp_path)
        shadow = _begin_linked(log, mode=SessionMode.SHADOW)
        normal = _begin_unlinked(log)
        target = tmp_path / "export.csv"
        assert log.export_csv(target) == 2
        rows = list(csv.reader(io.StringIO(target.read_text(encoding="utf-8-sig"))))
        by_id = {row[0]: dict(zip(CSV_COLUMNS, row, strict=True)) for row in rows[1:]}
        assert (by_id[shadow]["mode"], by_id[shadow]["app_version"]) == ("shadow", VERSION)
        assert (by_id[normal]["mode"], by_id[normal]["app_version"]) == ("normal", VERSION)

    def test_export_of_an_empty_store_is_the_header(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        target = tmp_path / "empty.csv"
        assert log.export_csv(target) == 0
        assert target.read_text(encoding="utf-8-sig").splitlines() == [",".join(CSV_COLUMNS)]

    def test_a_folder_that_cannot_be_listed_is_the_documented_refusal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 7 LOW-006: an OS error while walking the rows is
        ``AuditUnavailable`` (for the tab and Export CSV), never raw."""
        log = _log(tmp_path)
        _begin_unlinked(log)

        def walk() -> Any:
            yield from ()
            raise PermissionError(13, "in use", str(log.root / "2026-10"))

        monkeypatch.setattr(log, "_row_paths", walk)
        monkeypatch.setattr(log, "_has_rows", lambda: True)
        with pytest.raises(AuditUnavailable) as raised:
            log.rows()
        assert raised.value.reason == "unavailable"
        with pytest.raises(AuditUnavailable):
            log.export_csv(tmp_path / "x.csv")

    def test_export_refuses_an_unreadable_key(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        _begin_unlinked(log)
        (log.root / KEY_FILENAME).write_bytes(b"")
        with pytest.raises(AuditUnavailable):
            log.export_csv(tmp_path / "x.csv")

    def test_export_never_touches_a_users_own_tmp_file(self, tmp_path: Path) -> None:
        """H3 round 35 SEC-004: the export lands in a folder the USER chose,
        so its temp file is a fresh name — never ``<name>.tmp``, which may be
        theirs — and none is left behind."""
        log = _log(tmp_path)
        _begin_unlinked(log)
        out = tmp_path / "out"
        out.mkdir()
        theirs = out / "export.csv.tmp"
        theirs.write_bytes(b"mine")
        assert log.export_csv(out / "export.csv") == 1
        assert theirs.read_bytes() == b"mine"
        assert sorted(p.name for p in out.iterdir()) == ["export.csv", "export.csv.tmp"]

    def test_a_failed_export_is_terse_and_leaves_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        log = _log(tmp_path)
        _begin_unlinked(log)
        out = tmp_path / "out"
        out.mkdir()

        def refuse(*_args: object) -> None:
            raise PermissionError(13, "denied", str(out / "export.csv"))

        monkeypatch.setattr(audit_mod.os, "replace", refuse)
        with pytest.raises(StoreWriteError) as raised:
            log.export_csv(out / "export.csv")
        assert str(raised.value) == "failed writing audit export"
        assert raised.value.__cause__ is None
        assert list(out.iterdir()) == []


@windows_only
class TestStoreBounds:
    """H3 round 35 SEC-003 / SEC-005: an oversized row is never read whole,
    and a linked month folder is never read, written or pruned."""

    def test_an_oversized_row_is_unreadable_and_never_read_whole(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 37 PR-LOW-031: a padded row would also fail authentication,
        so the bound is shown on an otherwise-VALID row — one byte over the
        cap it is unreadable, at the cap it reads — and no read asks for
        more than cap + 1 bytes."""
        from conftest import bounded_read_spy

        log = _log(tmp_path)
        sid = _begin_unlinked(log)
        [row_path] = log.root.glob(f"*/{sid}.enc")
        size = row_path.stat().st_size
        sizes = bounded_read_spy(monkeypatch, row_path.name)
        monkeypatch.setattr(audit_mod, "MAX_ROW_FILE_BYTES", size - 1)
        listing = log.rows()
        assert (listing.rows, listing.unreadable) == ((), 1)
        monkeypatch.setattr(audit_mod, "MAX_ROW_FILE_BYTES", size)
        assert [row.session_id for row in log.rows().rows] == [sid]
        assert sizes == [size, size + 1]

    @pytest.mark.parametrize("kind", ["junction", "symlink"])
    def test_a_linked_month_folder_is_never_followed(self, tmp_path: Path, kind: str) -> None:
        from test_past_sessions import _link

        log = _log(tmp_path)
        kept = _begin_unlinked(log, started_at=T0 - timedelta(days=40))  # 2026-08
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        _link(kind, log.root / "2026-10", elsewhere)
        old = tmp_path / "old"
        old.mkdir()
        (old / f"{_sid()}.enc").write_bytes(b"theirs")
        _link(kind, log.root / "2020-01", old)

        with pytest.raises(AuditWriteError) as raised:
            _begin_unlinked(log)  # this month's folder is the link
        assert raised.value.reason == "unavailable"
        assert log.update(
            _sid(), lambda row, _now: row, stage="test", created_at=T0.timestamp()
        ) is False
        assert list(elsewhere.iterdir()) == []
        assert [row.session_id for row in log.rows().rows] == [kept]
        assert log.prune() == 0  # 2020-01 is long past its prune date, but a link
        assert [p.name.endswith(".enc") for p in old.iterdir()] == [True]
        assert os.path.lexists(log.root / "2020-01")


@windows_only
class TestReset:
    """D9 (round 4 PR-LOW-002): nothing is ever deleted; a quarantine name
    is never reused; a failure after the rename leaves the store absent."""

    @staticmethod
    def _snapshot(folder: Path) -> dict[str, bytes]:
        return {
            str(path.relative_to(folder)): path.read_bytes()
            for path in sorted(folder.rglob("*"))
            if path.is_file()
        }

    def test_two_resets_in_one_second_then_a_failed_key_then_a_retry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        log = _log(tmp_path)  # the clock stands still: every reset in one second
        _begin_linked(log)
        first = log.reset()
        assert first is not None and first.name.startswith("audit.unreadable-20261001-073000-")
        first_files = self._snapshot(first)
        assert any(name.endswith(".enc") for name in first_files)
        assert (log.root / KEY_FILENAME).is_file() and log.rows().rows == ()
        _begin_unlinked(log)
        second = log.reset()
        assert second is not None and second != first
        second_files = self._snapshot(second)

        def no_key(*_args: Any, **_kwargs: Any) -> Any:
            raise StoreWriteError("failed writing key custody blob: disk full")

        monkeypatch.setattr(audit_mod, "wrap_key_to_file", no_key)
        with pytest.raises(AuditResetError):
            log.reset()
        monkeypatch.undo()
        quarantines = sorted(p for p in tmp_path.iterdir() if p.name.startswith("audit.unread"))
        assert len(quarantines) == 3
        assert not log.root.exists()  # absent, as D9 states
        # A retry (or the next Start) makes a fresh store; nothing old is touched.
        assert log.reset() is None
        assert (log.root / KEY_FILENAME).is_file()
        _begin_unlinked(log)
        assert self._snapshot(first) == first_files
        assert self._snapshot(second) == second_files

    def test_a_dpapi_failure_is_the_authored_error_everywhere(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 6 MED-001: DPAPI raises ``pywintypes.error``, which is not
        OSError-rooted — a key that cannot be wrapped is still Start's
        authored refusal, and still ``AuditResetError`` after the rename
        (the store root then absent, as D9 states)."""

        class DpapiError(Exception):  # stands in for pywintypes.error
            pass

        def refused(*_args: Any, **_kwargs: Any) -> Any:
            raise DpapiError(-2146893813, "CryptProtectData", "Key not valid")

        monkeypatch.setattr(audit_mod, "wrap_key_to_file", refused)
        log = _log(tmp_path)
        with pytest.raises(AuditWriteError) as raised:
            _begin_unlinked(log)
        assert raised.value.reason == "write_failed"
        assert list(log.root.glob("*/*.enc")) == []
        monkeypatch.undo()
        _begin_unlinked(log)
        monkeypatch.setattr(audit_mod, "wrap_key_to_file", refused)
        with pytest.raises(AuditResetError):
            log.reset()
        assert not log.root.exists()
        assert len([p for p in tmp_path.iterdir() if p.name.startswith("audit.unread")]) == 1

    def test_a_reset_with_no_store_just_creates_one(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        assert log.reset() is None
        assert (log.root / KEY_FILENAME).is_file()
        assert not log.key_unreadable()

    def test_a_reset_clears_an_unreadable_key(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        _begin_unlinked(log)
        (log.root / KEY_FILENAME).write_bytes(b"")
        assert log.key_unreadable()
        with pytest.raises(AuditWriteError):
            _begin_unlinked(log)
        log.reset()
        assert not log.key_unreadable()
        _begin_unlinked(log)

    def test_an_existing_quarantine_name_is_never_reused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        log = _log(tmp_path)
        _begin_unlinked(log)
        taken = tmp_path / "audit.unreadable-20261001-073000-aaaaaaaa"
        taken.mkdir()
        (taken / "keep").write_bytes(b"old")
        tokens = iter(["aaaaaaaa", "bbbbbbbb"])
        monkeypatch.setattr(audit_mod.secrets, "token_hex", lambda _n: next(tokens))
        quarantine = log.reset()
        assert quarantine == tmp_path / "audit.unreadable-20261001-073000-bbbbbbbb"
        assert (taken / "keep").read_bytes() == b"old"


# ---------------------------------------------------------------------------
# app.main's wiring (Task 1.3: "wired in app.main with a test pinning it").
# ---------------------------------------------------------------------------


class _StopMain(Exception):
    pass


class TestAppWiring:
    def test_main_gives_the_controller_and_window_one_audit_and_prunes_first(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        from scribe_desktop import app as app_module

        events: list[Any] = []

        class FakeAudit:
            def __init__(self, **kwargs: Any) -> None:
                events.append(("audit", sorted(kwargs)))

            def prune(self) -> int:
                events.append(("prune",))
                return 0

            def record_deletion(self, session_id: str, state: str, **kwargs: Any) -> bool:
                events.append(("record", session_id, state, kwargs))
                return True

        class FakePastSessions:
            """Privacy-professional-controls Task 2.3: never the real archive
            root (C6) — the staging clean-up, the C1 hook and the
            reconciliation are recorded instead."""

            def __init__(self, **kwargs: Any) -> None:
                events.append(("past", sorted(kwargs)))

            # Development-recordings Task 3.3: an interrupted export is
            # resolved FIRST at start-up; what it kept is named on screen.
            def recover_exports(self) -> ExportRecovery:
                events.append(("exports",))
                return ExportRecovery(kept=("c" * 32,))

            def clean_staging(self) -> int:
                events.append(("staging",))
                return 0

            def remove_pending_entry(self, session_id: str) -> bool:
                return True

            def reconcile_pending(self, sessions_root: Path) -> list[str]:
                events.append(("reconcile", sessions_root))
                return []

            def entry_label(self, session_id: str) -> Any:  # review round 15 PR-MED-001
                return None

            def kept_entries(self) -> list[Any]:
                events.append(("kept",))
                return []

            def deleted_recordings(self) -> list[Any]:
                events.append(("deleted",))
                return []

            def tidy_dead_recordings(self, *, cleared: frozenset[str] | None = None) -> int:
                events.append(("tidy",))
                return 0

        class FakeController:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                events.append(("controller", kwargs["audit"], kwargs["past_sessions"]))

            def custody_protected_ids(self) -> frozenset[str]:
                return frozenset()

            def set_clinic_user_resolver(self, resolver: Any) -> None:
                events.append(("resolver", resolver))

        window_kwargs: dict[str, Any] = {}

        class FakeWindow:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                window_kwargs.update(kwargs)
                events.append(("window", kwargs["audit"], kwargs["past_sessions"]))

            def clinic_user_id(self, clinic_id: str) -> str | None:
                return None

            def reconstruct_reminders(self) -> None:
                raise _StopMain()

        expired = "e" * 32
        results = [
            SweepResult(expired, "expired", 1_700_000_000.0),
            SweepResult("f" * 32, "orphan_gc", -math.inf),
            SweepResult("a" * 32, "kept"),
            SweepResult("b" * 32, "error"),
        ]

        def sweep(*_args: Any, **kwargs: Any) -> list[SweepResult]:
            events.append(("sweep", kwargs["before_destroy"]))
            return results

        for name, value in {
            "setup_logging": lambda name: logging.getLogger("test-audit-main"),
            # Task 4.1 (C6): never this process's hooks or the real layer.
            "install_exception_hooks": lambda logger: lambda: None,
            "Win32WindowsLayer": lambda: None,
            "startup_exclusions": lambda *args, **kwargs: (),
            "apply_offline_env": lambda: None,
            "assert_offline_env": lambda: None,
            "QApplication": lambda argv: QApplication.instance() or QApplication(argv),
            "acquire_instance_exclusion": lambda name=None, lock_path=None: (
                app_module.InstanceExclusion("acquired")
            ),
            "SoundDeviceBackend": lambda: object(),
            "ImportWarmup": InertWarmup,  # round 35 MED-001: no warm-up thread
            "AuditLog": FakeAudit,
            "PastSessionStore": FakePastSessions,
            "SessionController": FakeController,
            "default_sessions_root": lambda: tmp_path / "sessions",
            "sweep_sessions": sweep,
            "MainWindow": FakeWindow,
        }.items():
            monkeypatch.setattr(app_module, name, value)
        with pytest.raises(_StopMain):
            app_module.main()
        kinds = [event[0] for event in events]
        assert kinds == [
            "audit",
            "past",
            "controller",
            "prune",
            "exports",  # development-recordings Task 3.3: FIRST of the store's
            "staging",
            "sweep",
            "reconcile",
            "kept",  # development-recordings Task 2.2: the start-up repair
            "deleted",  # review round 11 LOW-004: deleted, not yet tidied
            "tidy",
            "record",
            "record",
            "window",
            "resolver",
        ]
        assert events[0] == ("audit", ["logger"])
        assert events[1] == ("past", ["logger"])
        _kind, audit, past = events[2]
        assert isinstance(audit, FakeAudit) and isinstance(past, FakePastSessions)
        assert events[13][1:] == (audit, past)  # the window gets the same two
        # C1: the sweep's hook is the archive's unfinished-entry removal, and
        # the reconciliation runs over the same sessions root, after it.
        assert events[6][1] == past.remove_pending_entry
        assert events[7] == ("reconcile", tmp_path / "sessions")
        assert events[11] == ("record", expired, "expired", {"created_at": 1_700_000_000.0})
        assert events[12][2] == "orphan_gc"
        assert getattr(events[14][1], "__name__", "") == "clinic_user_id"
        # The partial export the recovery could not remove is named on the
        # Past sessions status line (by its session id only).
        assert window_kwargs["export_recovery_lines"] == [
            f"A partial export file {'c' * 32}.wav.part could not be removed from the folder "
            "you chose - delete it by hand."
        ]

    def test_main_runs_the_retention_sweep_at_start_up_and_records_reconciled_commits(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Task 3.2: the start-up retention sweep runs through the Past
        sessions tab after the window and its reminder rebuild; round 12
        LOW-002: every entry ``reconcile_pending`` commits is recorded in the
        audit as ``archived``."""
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        from scribe_desktop import app as app_module

        events: list[Any] = []
        committed = "c" * 32
        kept = [
            (committed, datetime(2026, 10, 7, 4, 0, tzinfo=UTC)),
            ("b" * 32, datetime(2026, 9, 1, 4, 0, tzinfo=UTC)),
        ]
        # Review round 11 LOW-003: a row the audit prune already removed is
        # never re-made by the repair.
        pruned_at = datetime(2018, 1, 1, 4, 0, tzinfo=UTC)
        deleted = ("9" * 32, datetime(2026, 8, 3, 4, 0, tzinfo=UTC))
        # Round 13 LOW-013: started in the month before it completed — every
        # re-made row is dated by the START.
        deleted_started = datetime(2026, 7, 31, 23, 0, tzinfo=UTC)

        def label(completed: datetime, started: datetime | None = None) -> Any:
            # ``moment`` as ``PastSessionLabel.moment`` defines it (hardening
            # round 43 SIMP-002).
            return SimpleNamespace(
                completed_at=completed,
                started_at=started,
                moment=started if started is not None else completed,
            )

        # Review round 15 PR-MED-001: each reconciled commit's ``archived`` is
        # dated by its label's START, skipped when that month is pruned, and
        # made on an existing row only when the label cannot be read.
        committed_started = datetime(2026, 9, 30, 23, 0, tzinfo=UTC)
        reconciled: dict[str, Any] = {
            committed: label(kept[0][1], started=committed_started),
            "e" * 32: None,
            "4" * 32: label(pruned_at),
        }
        repairing: list[bool] = []  # set once the kept-fact repair begins

        class FakeAudit:
            def __init__(self, **kwargs: Any) -> None:
                pass

            def prune(self) -> int:
                return 0

            def keeps_rows_of(self, at: datetime) -> bool:
                return at != pruned_at

            def record_deletion(self, *args: Any, **kwargs: Any) -> bool:
                return True

            def record_past_session(self, session_id: str, state: str, **kwargs: Any) -> bool:
                # Review round 15 PR-MED-001: a reconciled commit's write
                # shows how it was dated (or that it may make no row).
                shown = kwargs if session_id in reconciled and not repairing else {}
                events.append(("past_session", session_id, state, *([shown] if shown else [])))
                return True

            # Development-recordings Task 1.4 (review round 8 LOW-004).
            def record_recording_kept(self, session_id: str, at: datetime, **kwargs: Any) -> bool:
                events.append(("kept_fact", session_id, at))
                return True

            def record_recording_deleted(self, session_id: str, **kwargs: Any) -> bool:
                events.append(("recording_deleted", session_id, kwargs))
                return session_id != "8" * 32  # this one's write is refused

            def record_recording_exported(self, *args: Any, **kwargs: Any) -> bool:
                return True

        class FakePastSessions:
            def __init__(self, **kwargs: Any) -> None:
                pass

            def recover_exports(self) -> ExportRecovery:
                events.append(("exports",))
                return ExportRecovery()

            def clean_staging(self) -> int:
                events.append(("staging",))
                return 0

            def deleted_recordings(self) -> list[Any]:
                return [
                    SimpleNamespace(
                        session_id=deleted[0], label=label(deleted[1], started=deleted_started)
                    ),
                    SimpleNamespace(session_id="8" * 32, label=None),
                    SimpleNamespace(session_id="7" * 32, label=label(pruned_at)),
                ]

            def remove_pending_entry(self, session_id: str) -> bool:
                return True

            def reconcile_pending(self, sessions_root: Path) -> list[str]:
                events.append(("reconcile",))
                return list(reconciled)

            def entry_label(self, session_id: str) -> Any:
                return reconciled[session_id]

            # Development-recordings Task 2.2: the kept-fact repair covers
            # EVERY kept entry, not only the newly committed one.
            def kept_entries(self) -> list[Any]:
                repairing.append(True)
                return [
                    SimpleNamespace(session_id=sid, label=label(at)) for sid, at in kept
                ] + [
                    SimpleNamespace(session_id="d" * 32, label=None),
                    SimpleNamespace(session_id="6" * 32, label=label(pruned_at)),
                    # Review round 12 LOW-001: started in a pruned month and
                    # completed in a kept one — judged by its START, skipped.
                    SimpleNamespace(
                        session_id="5" * 32,
                        label=label(datetime(2026, 8, 1, 1, 0, tzinfo=UTC), started=pruned_at),
                    ),
                ]

            def tidy_dead_recordings(self, *, cleared: frozenset[str] | None = None) -> int:
                events.append(("tidy", cleared))
                return 0

        class FakeController:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            def custody_protected_ids(self) -> frozenset[str]:
                return frozenset()

            def set_clinic_user_resolver(self, resolver: Any) -> None:
                pass

        class FakeTab:
            def run_retention_sweep(self) -> list[str]:
                events.append(("retention",))
                return []

        class FakeWindow:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self.past_sessions_screen = FakeTab()
                events.append(("window",))

            def clinic_user_id(self, clinic_id: str) -> str | None:
                return None

            def reconstruct_reminders(self) -> None:
                events.append(("reminders",))

        def stop(*_args: Any) -> None:
            events.append(("chrome",))
            raise _StopMain()

        for name, value in {
            "setup_logging": lambda name: logging.getLogger("test-audit-main"),
            # Task 4.1 (C6): never this process's hooks or the real layer.
            "install_exception_hooks": lambda logger: lambda: None,
            "Win32WindowsLayer": lambda: None,
            "startup_exclusions": lambda *args, **kwargs: (),
            "apply_offline_env": lambda: None,
            "assert_offline_env": lambda: None,
            "QApplication": lambda argv: QApplication.instance() or QApplication(argv),
            "acquire_instance_exclusion": lambda name=None, lock_path=None: (
                app_module.InstanceExclusion("acquired")
            ),
            "SoundDeviceBackend": lambda: object(),
            "ImportWarmup": InertWarmup,  # round 35 MED-001: no warm-up thread
            "AuditLog": FakeAudit,
            "PastSessionStore": FakePastSessions,
            "SessionController": FakeController,
            "default_sessions_root": lambda: tmp_path / "sessions",
            "sweep_sessions": lambda *args, **kwargs: [],
            "MainWindow": FakeWindow,
            "_start_chrome_link": stop,
        }.items():
            monkeypatch.setattr(app_module, name, value)
        with pytest.raises(_StopMain):
            app_module.main()
        # Development-recordings Task 2.2, the start-up order:
        # `recover_exports` (Task 3.3: FIRST) -> `clean_staging` ->
        # `reconcile_pending` -> the kept-fact repair (an entry whose label
        # cannot be read is left for the next start) -> the deletion record
        # (rounds 11-13) -> `tidy_dead_recordings` -> the retention sweep.
        assert events == [
            ("exports",),
            ("staging",),
            ("reconcile",),
            # Review round 16 PR-MED-001: every unattended write passes the
            # shared rule's ``created_at`` and ``create`` (`unattended_write`).
            (
                "past_session",
                committed,
                "archived",
                {"created_at": committed_started.timestamp(), "create": True},
            ),
            ("past_session", "e" * 32, "archived", {"created_at": None, "create": False}),
            *[
                event
                for sid, at in kept
                for event in (("kept_fact", sid, at), ("past_session", sid, "archived"))
            ],
            # Review round 11 LOW-004: a deleted-but-untidied recording's
            # deletion is recorded (after its kept fact) BEFORE tidy.
            ("kept_fact", deleted[0], deleted[1]),
            ("past_session", deleted[0], "archived"),
            (
                "recording_deleted",
                deleted[0],
                {"created_at": deleted_started.timestamp(), "create": True},
            ),
            # Round 13 LOW-012: an unreadable label's deletion is recorded
            # alone (no dates) — refused here, so tidy is not cleared for it.
            # Round 14 PR-MED-001: an existing row only.
            ("recording_deleted", "8" * 32, {"created_at": None, "create": False}),
            # Round 17 PR-MED-001: tidy gets POSITIVE clearance — the
            # recorded one and the pruned one (nothing owed), never the
            # refused one.
            ("tidy", frozenset({deleted[0], "7" * 32})),
            ("window",),
            ("reminders",),
            ("retention",),
            ("chrome",),
        ]

    def test_the_retention_sweep_runs_at_most_hourly_on_the_sweep_tick(self) -> None:
        """Task 3.2's cadence, by an injected clock (never by sleeping): the
        15-minute timer runs it once an hour has passed since the last one."""
        from scribe_desktop.app import (
            _RETENTION_SWEEP_INTERVAL_S,
            _SWEEP_INTERVAL_MS,
            retention_sweep_if_due,
        )

        runs: list[int] = []

        def sweep() -> list[str]:
            runs.append(1)
            return []

        assert _RETENTION_SWEEP_INTERVAL_S == 60 * 60
        tick = _SWEEP_INTERVAL_MS / 1000
        last = 1000.0  # the start-up sweep
        now = last
        for _ in range(3):  # 15, 30 and 45 minutes: not yet
            now += tick
            last = retention_sweep_if_due(sweep, last, now)
        assert (runs, last) == ([], 1000.0)
        now += tick  # 60 minutes
        last = retention_sweep_if_due(sweep, last, now)
        assert (runs, last) == ([1], now)
        assert retention_sweep_if_due(sweep, last, now + tick) == last
        assert runs == [1]

    def test_the_periodic_tick_runs_each_step_in_order_on_its_own_cadence(self) -> None:
        """Round 16 LOW-016: the timer's body, out of ``main``. Every tick
        sweeps sessions (with the recovery list's protected ids), prunes the
        reminders and re-lists Recovery; the audit prune and the retention
        sweep follow their own monotonic intervals."""
        from scribe_desktop.app import (
            _AUDIT_PRUNE_INTERVAL_S,
            _RETENTION_SWEEP_INTERVAL_S,
            _SWEEP_INTERVAL_MS,
            PeriodicSweep,
        )

        events: list[Any] = []
        protected = frozenset({"a" * 32})

        class Recovery:
            def protected_session_ids(self) -> frozenset[str]:
                return protected

            def refresh(self) -> None:
                events.append("recovery")

        class Tab:
            def run_retention_sweep(self) -> list[str]:
                events.append("retention")
                return []

        class Window:
            recovery_screen = Recovery()
            past_sessions_screen = Tab()

            def prune_reminders(self) -> None:
                events.append("reminders")

        class Audit:
            def prune(self) -> int:
                events.append("prune")
                return 0

        clock = [1000.0]
        tick = PeriodicSweep(
            Window(),  # type: ignore[arg-type]
            Audit(),  # type: ignore[arg-type]
            lambda ids: events.append(("sweep", ids)),
            last_prune=1000.0,
            last_retention_sweep=1000.0,
            monotonic=lambda: clock[0],
        )
        clock[0] += _SWEEP_INTERVAL_MS / 1000
        tick()
        assert events == [("sweep", protected), "reminders", "recovery"]
        events.clear()
        clock[0] = 1000.0 + _RETENTION_SWEEP_INTERVAL_S
        tick()
        assert events == [("sweep", protected), "reminders", "recovery", "retention"]
        assert tick.last_retention_sweep == clock[0]
        events.clear()
        clock[0] = 1000.0 + _AUDIT_PRUNE_INTERVAL_S
        tick()
        assert events == [("sweep", protected), "reminders", "recovery", "prune", "retention"]

    def test_a_failing_session_sweep_still_prunes_and_sweeps_retention(self) -> None:
        """H1 round 32 LOW-003: an unlistable sessions root fails the session
        sweep, but the audit prune and the retention deletion still run on
        their cadence; the first failure is raised again for the hook."""
        from scribe_desktop.app import _AUDIT_PRUNE_INTERVAL_S, PeriodicSweep

        events: list[str] = []

        class Recovery:
            def protected_session_ids(self) -> frozenset[str]:
                return frozenset()

            def refresh(self) -> None:
                events.append("recovery")

        class Tab:
            def run_retention_sweep(self) -> list[str]:
                events.append("retention")
                raise RuntimeError("second failure")

        class Window:
            recovery_screen = Recovery()
            past_sessions_screen = Tab()

            def prune_reminders(self) -> None:
                events.append("reminders")

        class Audit:
            def prune(self) -> int:
                events.append("prune")
                return 0

        def unlistable(_ids: frozenset[str]) -> None:
            raise PermissionError("sessions root")

        now = 1000.0 + _AUDIT_PRUNE_INTERVAL_S
        tick = PeriodicSweep(
            Window(),  # type: ignore[arg-type]
            Audit(),  # type: ignore[arg-type]
            unlistable,
            last_prune=1000.0,
            last_retention_sweep=1000.0,
            monotonic=lambda: now,
        )
        with pytest.raises(PermissionError):  # the FIRST failure
            tick()
        assert events == ["prune", "retention"]
        assert tick.last_prune == now

    def test_record_sweep_results_tolerates_no_results(self) -> None:
        from scribe_desktop.app import record_sweep_results

        calls: list[Any] = []

        class Recorder:
            def record_deletion(self, *args: Any, **kwargs: Any) -> bool:
                calls.append(args)
                return True

        recorder: Any = Recorder()
        record_sweep_results(recorder, None)
        record_sweep_results(recorder, [SweepResult("a" * 32, "skipped_active")])
        assert calls == []

    def test_the_audit_prune_runs_once_a_day_on_the_sweep_tick(self) -> None:
        """Round 6 LOW-012: Flow 4's 24 h cadence, by an injected clock."""
        from scribe_desktop.app import _AUDIT_PRUNE_INTERVAL_S, prune_audit_if_due

        pruned: list[int] = []

        class Pruner:
            def prune(self) -> int:
                pruned.append(1)
                return 0

        audit: Any = Pruner()
        day = float(_AUDIT_PRUNE_INTERVAL_S)
        assert day == 24 * 60 * 60
        last = prune_audit_if_due(audit, 100.0, 100.0 + day - 1)
        assert (last, pruned) == (100.0, [])
        last = prune_audit_if_due(audit, last, 100.0 + day)
        assert (last, pruned) == (100.0 + day, [1])
        assert prune_audit_if_due(audit, last, last + 900.0) == last
        assert pruned == [1]
