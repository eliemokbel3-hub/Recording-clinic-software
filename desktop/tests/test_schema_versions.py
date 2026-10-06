"""Pilot plan Tasks 1.2 and 1.8 (D1, D3, D6): the three version-2 schemas,
read both ways.

- COMMITTED v1 bytes — what a 0.1.2 build wrote to ``encounter.enc``, an
  audit row and ``label.enc`` — are read by this build as a NORMAL recording
  (the audit row upgraded in ``_decode`` before validation).
- A NEWER version than this build's is refused the way an older build relies
  on (the Schema / Data Changes table): the audit row is ``_NEWER`` and kept
  byte for byte, the label lists as unreadable and its Copy stays closed, and
  the encounter record is ``EncounterUnavailable`` — the session it belongs
  to cannot be opened, and Start is unaffected.
- The recording's mode is fixed at Start and travels with the encounter
  record: a shadow recording is still shadow after Finish and after
  ``adopt_queued``, through the authorised reader only.

The v1 bytes are literals here on purpose: a later change to a model must
not be able to re-derive (and so silently re-shape) what an older build
wrote."""

from __future__ import annotations

import csv
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final

import pytest

from conftest import start_unlinked
from scribe_desktop import audit as audit_mod
from scribe_desktop import session as session_module
from scribe_desktop.audit import AUDIT_KEY_DESCRIPTION, AuditLog, AuditRow
from scribe_desktop.encounter import (
    EncounterRecord,
    EncounterUnavailable,
    Verification,
    read_encounter_record,
    unlinked_consent,
)
from scribe_desktop.past_sessions import (
    LABEL_FILENAME,
    KeepLabel,
    PastSessionError,
    PastSessionLabel,
    PastSessionStore,
    _label_aad,
)
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import ReviewOpenRefused, SessionController, SessionState
from scribe_desktop.session_mode import SessionMode
from scribe_desktop.session_store import (
    ArchiveSource,
    unwrap_key_from_file,
    write_encounter,
)
from scribe_desktop.transcription import write_transcript
from scribe_desktop.ui import past_sessions_view as view

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI custody is Windows-only")

FIXTURE_SID: Final = "0f1e2d3c4b5a69788796a5b4c3d2e1f0"

# --- the committed v1 bytes (as 0.1.2's ``model_dump_json`` wrote them) ------

ENCOUNTER_V1_LINKED: Final = (
    b'{"schema_version":1,"consent":{"confirmed_at":"2026-09-27T08:00:00Z",'
    b'"text_version":"recording-consent-v1","practitioner_id":"7654321",'
    b'"treatment_note_id":"2001"},"context":{"clinic_id":"0123456789abcdef",'
    b'"clinic_host":"northside.au2.cliniko.com","patient_id":"1001",'
    b'"treatment_note_id":"2001","booking_id":"3001","practitioner_id":"7654321",'
    b'"template_id":"4001","verification":"verified",'
    b'"verified_at":"2026-09-27T08:00:00Z"}}'
)
ENCOUNTER_V1_UNLINKED: Final = (
    b'{"schema_version":1,"consent":{"confirmed_at":"2026-09-27T08:00:00Z",'
    b'"text_version":"recording-consent-v1","practitioner_id":null,'
    b'"treatment_note_id":null},"context":null}'
)
AUDIT_V1: Final = (
    b'{"schema_version":1,"session_id":"0f1e2d3c4b5a69788796a5b4c3d2e1f0",'
    b'"session_date":"2026-10-01","origin":"recorded",'
    b'"consent_confirmed_at":"2026-10-01T07:30:00Z",'
    b'"consent_text_version":"recording-consent-v1","linked":true,'
    b'"verification":"verified","clinic_id":"0123456789abcdef",'
    b'"practitioner_id":"7654321","user_id":"4242","booking_id":"3001",'
    b'"treatment_note_id":"2001","models":null,"write":{"attempts":1,'
    b'"last_outcome":"written","last_refusal":null,'
    b'"written_at":"2026-10-01T08:10:00Z"},"deletion":{"state":"pending","at":null},'
    b'"past_session":{"state":"none","at":null},"note_provenance":null,'
    b'"events":[{"at":"2026-10-01T07:30:00Z","code":"started"}]}'
)
LABEL_V1: Final = (
    b'{"schema_version":1,"session_id":"0f1e2d3c4b5a69788796a5b4c3d2e1f0",'
    b'"completed_at":"2026-10-01T09:00:00Z","started_at":"2026-10-01T08:40:00Z",'
    b'"recording":"linked","clinic_id":"0123456789abcdef",'
    b'"patient_name":"Jane Citizen","has_generated":true,"has_saved":true}'
)


def _newer(document: bytes) -> bytes:
    """``document`` as a build newer than this one would write it: version 3,
    with a field this build has never heard of."""
    data = json.loads(document)
    data["schema_version"] = 3
    data["something_new"] = "x"
    return json.dumps(data).encode("utf-8")


def _unversioned(document: bytes, mode: str | None = None) -> bytes:
    """``document`` with no ``schema_version`` (peer round 9 PR-HIGH-B01),
    naming ``mode`` when one is given."""
    data = json.loads(document)
    del data["schema_version"]
    if mode is not None:
        data["mode"] = mode
    return json.dumps(data).encode("utf-8")


# ---------------------------------------------------------------------------
# The encounter record (Task 1.2).
# ---------------------------------------------------------------------------


class TestEncounterRecordVersions:
    def test_v1_bytes_read_as_a_normal_recording(self) -> None:
        linked = EncounterRecord.from_bytes(ENCOUNTER_V1_LINKED)
        assert (linked.schema_version, linked.mode) == (1, SessionMode.NORMAL)
        assert linked.context is not None
        assert linked.context.verification is Verification.VERIFIED
        assert linked.consent.treatment_note_id == "2001"
        unlinked = EncounterRecord.from_bytes(ENCOUNTER_V1_UNLINKED)
        assert (unlinked.mode, unlinked.context) == (SessionMode.NORMAL, None)

    def test_a_new_record_is_v2_and_names_its_mode(self) -> None:
        for mode in SessionMode:
            record = EncounterRecord(consent=unlinked_consent(), mode=mode)
            data = json.loads(record.to_bytes())
            assert (data["schema_version"], data["mode"]) == (2, mode.value)
            assert EncounterRecord.from_bytes(record.to_bytes()).mode is mode

    def test_a_v1_record_naming_a_mode_is_refused(self) -> None:
        """Not a record this app wrote — refused, never read as either mode."""
        for mode in ("normal", "shadow"):
            data = json.loads(ENCOUNTER_V1_UNLINKED)
            data["mode"] = mode
            with pytest.raises(EncounterUnavailable):
                EncounterRecord.from_bytes(json.dumps(data).encode())

    def test_a_v2_record_without_a_mode_is_refused(self) -> None:
        data = json.loads(ENCOUNTER_V1_UNLINKED)
        data["schema_version"] = 2
        with pytest.raises(EncounterUnavailable):
            EncounterRecord.from_bytes(json.dumps(data).encode())

    @pytest.mark.parametrize("mode", ["", "Shadow", "practice", None, True])
    def test_a_mode_outside_the_two_is_refused(self, mode: Any) -> None:
        data = json.loads(ENCOUNTER_V1_UNLINKED)
        data.update(schema_version=2, mode=mode)
        with pytest.raises(EncounterUnavailable):
            EncounterRecord.from_bytes(json.dumps(data).encode())

    @pytest.mark.parametrize("version", [True, 1.0, 2.0, "1", "2"])
    def test_a_version_that_is_not_an_integer_is_refused(self, version: Any) -> None:
        """Round 26 (SEC-001): ``true == 1`` in Python — a version only
        equal to 1 or 2 is not one this app wrote, with or without a mode."""
        for mode in (None, "normal"):
            data = json.loads(ENCOUNTER_V1_UNLINKED)
            data["schema_version"] = version
            if mode is not None:
                data["mode"] = mode
            with pytest.raises(EncounterUnavailable):
                EncounterRecord.from_bytes(json.dumps(data).encode())

    def test_a_newer_record_is_unavailable(self) -> None:
        for document in (ENCOUNTER_V1_LINKED, ENCOUNTER_V1_UNLINKED):
            with pytest.raises(EncounterUnavailable):
                EncounterRecord.from_bytes(_newer(document))

    @pytest.mark.parametrize("mode", [None, "normal", "shadow"])
    def test_bytes_naming_no_version_are_refused(self, mode: str | None) -> None:
        """Peer round 9 PR-HIGH-B01: persisted bytes without a
        ``schema_version`` (with or without a mode) are not a record this
        app wrote — refused, never read as a v2 ``normal`` record."""
        for document in (ENCOUNTER_V1_LINKED, ENCOUNTER_V1_UNLINKED):
            with pytest.raises(EncounterUnavailable):
                EncounterRecord.from_bytes(_unversioned(document, mode))

    def test_a_new_record_still_takes_its_defaults(self) -> None:
        """The defaults stay for BUILDING a record (PR-HIGH-B01 moved the
        version requirement to the bytes only)."""
        record = EncounterRecord(consent=unlinked_consent())
        assert (record.schema_version, record.mode) == (2, SessionMode.NORMAL)
        assert EncounterRecord.from_bytes(record.to_bytes()) == record

    def test_v1_bytes_on_disk_read_through_the_authorised_reader(self, tmp_path: Path) -> None:
        directory = tmp_path / FIXTURE_SID
        directory.mkdir()
        crypto = SessionCrypto()
        try:
            write_encounter(directory, crypto, FIXTURE_SID, ENCOUNTER_V1_LINKED)
            record = read_encounter_record(directory, crypto, FIXTURE_SID)
            assert record.mode is SessionMode.NORMAL
            write_encounter(directory, crypto, FIXTURE_SID, _newer(ENCOUNTER_V1_LINKED))
            with pytest.raises(EncounterUnavailable):
                read_encounter_record(directory, crypto, FIXTURE_SID)
        finally:
            crypto.destroy()


def _controller(root: Path) -> SessionController:
    from scribe_desktop.audio_capture import MockCaptureBackend

    return SessionController(MockCaptureBackend(), sessions_root=root)


def _queued_on_disk(controller: SessionController, root: Path, mode: SessionMode) -> Path:
    """A recording started in ``mode``, finished, queued with a transcript,
    then retired by the next Start (which is discarded) — on disk, Unreviewed."""
    from test_note_pipeline import _document as _pipeline_document

    first = controller.start(0, consent=unlinked_consent(), mode=mode)
    assert first.mode is mode
    directory = root / first.session_id
    controller.finish()
    assert controller.session is not None and controller.session.mode is mode
    controller.mark_queued()
    crypto = session_module.unwrap_key_from_file(directory)
    try:
        write_transcript(directory, crypto, _pipeline_document(first.session_id))
    finally:
        crypto.destroy()
    start_unlinked(controller)  # retires the queued one
    controller.discard()
    return directory


def _read_name(directory: Path, _crypto: SessionCrypto) -> str:
    return directory.name


@windows_only
class TestModeTravelsWithTheRecording:
    """D1: fixed at Start, written into the encounter record, and read back
    by the authorised readers only — never re-derived from the setting."""

    @pytest.mark.parametrize("mode", list(SessionMode))
    def test_the_mode_survives_finish_and_adopt_queued(
        self, tmp_path: Path, mode: SessionMode, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        controller = _controller(tmp_path)
        directory = _queued_on_disk(controller, tmp_path, mode)
        real = session_module.read_encounter_record
        reads: list[str] = []

        def counting(*args: Any) -> Any:
            reads.append(args[2])
            return real(*args)

        monkeypatch.setattr(session_module, "read_encounter_record", counting)
        session, _ = controller.adopt_queued(directory, _read_name)
        assert session.mode is mode
        assert session.state is SessionState.QUEUED
        assert reads == [directory.name]  # the one authorised decrypt, unchanged
        controller.discard()

    def test_the_record_on_disk_names_the_mode(self, tmp_path: Path) -> None:
        controller = _controller(tmp_path)
        session = controller.start(0, consent=unlinked_consent(), mode=SessionMode.SHADOW)
        directory = tmp_path / session.session_id
        crypto = unwrap_key_from_file(directory)
        try:
            record = read_encounter_record(directory, crypto, session.session_id)
        finally:
            crypto.destroy()
        assert (record.schema_version, record.mode) == (2, SessionMode.SHADOW)
        controller.discard()

    def test_an_unknown_value_is_refused_at_start(self, tmp_path: Path) -> None:
        controller = _controller(tmp_path)
        with pytest.raises(session_module.SessionControllerError):
            controller.start(0, consent=unlinked_consent(), mode="shadow")  # type: ignore[arg-type]
        assert controller.session is None or controller.session.is_terminal

    def test_v1_bytes_adopt_as_normal(self, tmp_path: Path) -> None:
        controller = _controller(tmp_path)
        directory = _queued_on_disk(controller, tmp_path, SessionMode.SHADOW)
        crypto = unwrap_key_from_file(directory)
        try:
            write_encounter(directory, crypto, directory.name, ENCOUNTER_V1_UNLINKED)
        finally:
            crypto.destroy()
        session, _ = controller.adopt_queued(directory, _read_name)
        assert session.mode is SessionMode.NORMAL
        controller.discard()

    def test_a_newer_record_refuses_the_open_and_start_is_unaffected(
        self, tmp_path: Path
    ) -> None:
        controller = _controller(tmp_path)
        directory = _queued_on_disk(controller, tmp_path, SessionMode.NORMAL)
        crypto = unwrap_key_from_file(directory)
        try:
            write_encounter(directory, crypto, directory.name, _newer(ENCOUNTER_V1_UNLINKED))
        finally:
            crypto.destroy()
        with pytest.raises(ReviewOpenRefused) as refused:
            controller.adopt_queued(directory, _read_name)
        assert refused.value.reason == "consent_unavailable"
        started = start_unlinked(controller)
        assert started.state is SessionState.RECORDING
        controller.discard()

    def test_an_unversioned_record_refuses_the_open(self, tmp_path: Path) -> None:
        """Peer round 9 PR-HIGH-B01: a shadow recording whose record lost
        its version is never adopted as a normal one."""
        controller = _controller(tmp_path)
        directory = _queued_on_disk(controller, tmp_path, SessionMode.SHADOW)
        crypto = unwrap_key_from_file(directory)
        try:
            write_encounter(directory, crypto, directory.name, _unversioned(ENCOUNTER_V1_UNLINKED))
        finally:
            crypto.destroy()
        with pytest.raises(ReviewOpenRefused) as refused:
            controller.adopt_queued(directory, _read_name)
        assert refused.value.reason == "consent_unavailable"
        started = start_unlinked(controller)
        assert started.state is SessionState.RECORDING
        controller.discard()


# ---------------------------------------------------------------------------
# The audit row (Task 1.3).
# ---------------------------------------------------------------------------


def _audit_log(tmp_path: Path) -> AuditLog:
    log = AuditLog(
        tmp_path / "audit", clock=lambda: datetime(2026, 10, 1, 7, 30, tzinfo=UTC), local_zone=UTC
    )
    # A first Start creates the store's key (the fixture row is sealed under it).
    log.begin(
        "a" * 32,
        consent=unlinked_consent(datetime(2026, 10, 1, 7, 30, tzinfo=UTC)),
        context=None,
        user_id=None,
        started_at=datetime(2026, 10, 1, 7, 30, tzinfo=UTC),
        mode=SessionMode.NORMAL,
        app_version="0.2.0",
    )
    return log


def _seal_raw(log: AuditLog, sid: str, plaintext: bytes) -> Path:
    crypto = unwrap_key_from_file(log.root, description=AUDIT_KEY_DESCRIPTION)
    try:
        path = log.root / "2026-10" / f"{sid}.enc"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(crypto.encrypt(plaintext, b"audit:" + sid.encode("ascii")))
    finally:
        crypto.destroy()
    return path


class TestAuditRowVersions:
    def test_v1_bytes_decode_as_a_normal_row_with_no_version(self) -> None:
        row = audit_mod._decode(AUDIT_V1)  # noqa: SLF001
        assert isinstance(row, AuditRow)
        assert (row.schema_version, row.mode, row.app_version) == (2, SessionMode.NORMAL, None)
        assert (row.treatment_note_id, row.write.last_outcome) == ("2001", "written")
        assert [event.code for event in row.events] == ["started"]

    def test_v1_bytes_are_refused_by_the_model_itself(self) -> None:
        """Constraint 2: the upgrade lives in ``_decode``, before validation."""
        with pytest.raises(ValueError):
            AuditRow.model_validate_json(AUDIT_V1)

    def test_newer_bytes_are_newer(self) -> None:
        assert audit_mod._decode(_newer(AUDIT_V1)) is audit_mod._NEWER  # noqa: SLF001

    def test_bytes_naming_no_version_or_a_v2_row_naming_no_mode_are_refused(self) -> None:
        """Review round 22 (the encounter record's peer round 9 rule): the
        model alone would read either as a v2 row with no mode."""
        written = audit_mod._decode(AUDIT_V1)  # noqa: SLF001
        assert isinstance(written, AuditRow)
        stored = json.loads(written.to_bytes())
        assert audit_mod._decode(json.dumps(stored).encode()) == written  # noqa: SLF001
        for key in ("schema_version", "mode"):
            missing = {name: value for name, value in stored.items() if name != key}
            with pytest.raises(ValueError):
                audit_mod._decode(json.dumps(missing).encode())  # noqa: SLF001

    @pytest.mark.parametrize("version", [True, 1.0, 2.0, "1", "2"])
    def test_a_version_that_is_not_an_integer_is_refused(self, version: Any) -> None:
        """Peer round 27 (PR-LOW-065, round 26 SEC-001's rule): ``2.0 == 2``
        and ``true == 1`` — a version only equal to one is not one this app
        wrote, on a v1 row or on a v2 row naming its mode."""
        written = audit_mod._decode(AUDIT_V1)  # noqa: SLF001
        assert isinstance(written, AuditRow)
        for data in (json.loads(AUDIT_V1), json.loads(written.to_bytes())):
            data["schema_version"] = version
            with pytest.raises(ValueError):
                audit_mod._decode(json.dumps(data).encode())  # noqa: SLF001

    @windows_only
    def test_v1_bytes_on_disk_list_export_and_update(self, tmp_path: Path) -> None:
        log = _audit_log(tmp_path)
        path = _seal_raw(log, FIXTURE_SID, AUDIT_V1)
        rows = {row.session_id: row for row in log.rows().rows}
        assert rows[FIXTURE_SID].mode is SessionMode.NORMAL
        assert rows[FIXTURE_SID].app_version is None
        # The export: mode "normal", an empty version.
        exported = tmp_path / "audit.csv"
        assert log.export_csv(exported) == 2
        with exported.open(encoding="utf-8-sig", newline="") as handle:
            by_id = {row["session_id"]: row for row in csv.DictReader(handle)}
        assert (by_id[FIXTURE_SID]["mode"], by_id[FIXTURE_SID]["app_version"]) == ("normal", "")
        # An update re-writes the row as v2, the rest unchanged (review round
        # 23: the sealed bytes change and the update is in them).
        before = path.read_bytes()
        assert log.record_deletion(FIXTURE_SID, "discarded")
        assert path.read_bytes() != before
        rows = {row.session_id: row for row in log.rows().rows}
        updated = rows[FIXTURE_SID]
        assert (
            updated.schema_version,
            updated.mode,
            updated.treatment_note_id,
            updated.deletion.state,
        ) == (2, SessionMode.NORMAL, "2001", "discarded")

    @windows_only
    def test_newer_bytes_on_disk_are_kept_and_start_is_unaffected(self, tmp_path: Path) -> None:
        log = _audit_log(tmp_path)
        path = _seal_raw(log, FIXTURE_SID, _newer(AUDIT_V1))
        before = path.read_bytes()
        assert log.record_deletion(FIXTURE_SID, "discarded") is False
        assert path.read_bytes() == before
        assert log.rows().newer == 1
        log.begin(
            "b" * 32,
            consent=unlinked_consent(),
            context=None,
            user_id=None,
            started_at=datetime(2026, 10, 1, 8, 0, tzinfo=UTC),
            mode=SessionMode.SHADOW,
            app_version="0.2.0",
        )
        assert {row.session_id for row in log.rows().rows} == {"a" * 32, "b" * 32}


# ---------------------------------------------------------------------------
# The Past-sessions label (Task 1.6).
# ---------------------------------------------------------------------------

_FAKE = b"FAKE-ENTRY-KEY:"
_NOW = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


def _fake_wrap(crypto: SessionCrypto, directory: Path) -> None:
    (directory / "key.dpapi").write_bytes(_FAKE + crypto.export_key())


def _fake_unwrap(directory: Path) -> SessionCrypto:
    blob = (directory / "key.dpapi").read_bytes()
    assert blob.startswith(_FAKE)
    return SessionCrypto.from_key(blob[len(_FAKE) :])


def _published_fixture_entry(tmp_path: Path, label_plain: bytes) -> PastSessionStore:
    """A committed entry for ``FIXTURE_SID`` whose label is then replaced by
    ``label_plain``, sealed under the entry's own key and associated data."""
    from test_past_sessions import _generated, _note, _transcript

    store = PastSessionStore(
        tmp_path / "past_sessions",
        clock=lambda: _NOW,
        wrap_key=_fake_wrap,
        unwrap_key=_fake_unwrap,
    )
    transcript = _transcript(FIXTURE_SID)
    source = ArchiveSource(
        session_id=FIXTURE_SID,
        created_at=(_NOW - timedelta(minutes=20)).timestamp(),
        transcript_plain=transcript,
        note_plain=_note(FIXTURE_SID, transcript),
        generated_plain=_generated(FIXTURE_SID).to_bytes(),
    )
    store.write_entry(source, KeepLabel("Jane Citizen", "linked", "0123456789abcdef", shadow=True))
    assert store.commit(FIXTURE_SID)
    entry = store.root / FIXTURE_SID
    crypto = _fake_unwrap(entry)
    try:
        (entry / LABEL_FILENAME).write_bytes(
            crypto.encrypt(label_plain, _label_aad(FIXTURE_SID))
        )
    finally:
        crypto.destroy()
    return store


def _copy_reason(store: PastSessionStore) -> str | None:
    """What the Past sessions tab's Copy says, for the store's one entry."""
    try:
        entry = store.read_entry(FIXTURE_SID)
    except PastSessionError:
        entry = None
    saved = entry.saved_note if entry is not None else None
    return view.copy_unavailable_reason(
        opened=entry is not None,
        has_saved=saved is not None,
        unresolved=saved is not None and bool(saved.blocking_warnings()),
        copy_enabled=True,
        shadow=entry is not None and entry.label.shadow,
    )


class TestPastSessionLabelVersions:
    def test_v1_bytes_read_as_not_shadow(self) -> None:
        label = PastSessionLabel.model_validate_json(LABEL_V1)
        assert (label.schema_version, label.shadow, label.patient_name) == (
            1,
            False,
            "Jane Citizen",
        )

    def test_a_v1_label_naming_shadow_and_a_v2_label_without_it_are_refused(self) -> None:
        data = json.loads(LABEL_V1)
        for value in (True, False):
            with pytest.raises(ValueError):
                PastSessionLabel.model_validate({**data, "shadow": value})
        with pytest.raises(ValueError):
            PastSessionLabel.model_validate({**data, "schema_version": 2})
        with pytest.raises(ValueError):
            PastSessionLabel.model_validate({**data, "schema_version": 2, "shadow": "true"})

    def test_newer_bytes_are_refused(self) -> None:
        with pytest.raises(ValueError):
            PastSessionLabel.model_validate_json(_newer(LABEL_V1))

    @pytest.mark.parametrize("version", [True, 1.0, 2.0, "1", "2"])
    def test_a_version_that_is_not_an_integer_is_refused(self, version: Any) -> None:
        """Round 26 (SEC-001): with or without a shadow flag."""
        data = json.loads(LABEL_V1)
        for extra in ({}, {"shadow": False}, {"shadow": True}):
            with pytest.raises(ValueError):
                PastSessionLabel.model_validate_json(
                    json.dumps({**data, **extra, "schema_version": version})
                )

    def test_a_v1_entry_lists_opens_and_copies(self, tmp_path: Path) -> None:
        store = _published_fixture_entry(tmp_path, LABEL_V1)
        (listing,) = store.list_entries()
        assert listing.label is not None and listing.label.shadow is False
        assert not view.entry_line(listing, hide_names=True).endswith(f"({view.SHADOW_MARK})")
        assert store.read_entry(FIXTURE_SID).label.shadow is False
        assert _copy_reason(store) is None

    def test_a_newer_entry_is_unreadable_and_its_copy_stays_closed(self, tmp_path: Path) -> None:
        store = _published_fixture_entry(tmp_path, _newer(LABEL_V1))
        (listing,) = store.list_entries()
        assert listing.label is None
        assert view.entry_line(listing, hide_names=False) == view.ENTRY_UNREADABLE_ROW
        with pytest.raises(PastSessionError) as unreadable:
            store.read_entry(FIXTURE_SID)
        assert unreadable.value.reason == "unreadable"
        assert _copy_reason(store) == view.COPY_NOTHING_OPEN

    def test_a_v2_shadow_entry_is_marked_and_its_copy_refused(self, tmp_path: Path) -> None:
        data = json.loads(LABEL_V1)
        data.update(schema_version=2, shadow=True)
        store = _published_fixture_entry(tmp_path, json.dumps(data).encode())
        (listing,) = store.list_entries()
        assert view.entry_line(listing, hide_names=True).endswith(f"({view.SHADOW_MARK})")
        assert _copy_reason(store) == view.COPY_SHADOW

    @pytest.mark.parametrize("shadow", [None, False, True])
    def test_label_bytes_naming_no_version_are_unreadable(
        self, tmp_path: Path, shadow: bool | None
    ) -> None:
        """Review round 22 (the encounter record's peer round 9 rule): every
        label this app wrote names its ``schema_version``, so stored bytes
        naming none — which the model alone would read as v2 not shadow —
        are unreadable, and Copy stays closed."""
        data = json.loads(LABEL_V1)
        del data["schema_version"]
        if shadow is not None:
            data["shadow"] = shadow
        store = _published_fixture_entry(tmp_path, json.dumps(data).encode())
        (listing,) = store.list_entries()
        assert listing.label is None
        with pytest.raises(PastSessionError) as unreadable:
            store.read_entry(FIXTURE_SID)
        assert unreadable.value.reason == "unreadable"
        assert _copy_reason(store) == view.COPY_NOTHING_OPEN


class TestTheKeptLabelFollowsTheSession:
    """Review round 22: a live session's own mode forces the kept label's
    shadow flag on (``session.keep_label_for_mode``), whatever the UI
    resolved."""

    def test_a_shadow_session_keeps_a_shadow_label(self) -> None:
        resolved = KeepLabel("Jane Citizen", "linked", "0123456789abcdef", shadow=False)
        kept = session_module.keep_label_for_mode(resolved, SessionMode.SHADOW)
        assert kept == KeepLabel("Jane Citizen", "linked", "0123456789abcdef", shadow=True)

    def test_anything_else_is_kept_as_given(self) -> None:
        normal = KeepLabel(None, "desktop", None, shadow=False)
        shadow = KeepLabel(None, "desktop", None, shadow=True)
        assert session_module.keep_label_for_mode(normal, SessionMode.NORMAL) is normal
        assert session_module.keep_label_for_mode(normal, None) is normal  # a recovered one
        assert session_module.keep_label_for_mode(shadow, SessionMode.NORMAL) is shadow
        assert session_module.keep_label_for_mode(None, SessionMode.SHADOW) is None
