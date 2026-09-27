"""The desktop side of the encounter (Cliniko workflow safeguards plan Tasks
3.3 and 3.4): the live session's clinic for the Clinics tab, the recovery
list's stat-only link line, and the recovered checkout — its one decrypt of
``encounter.enc`` and its D4 re-verification. Offscreen; every Cliniko
answer comes from an injected transport and every key from memory."""

from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from encounter_fakes import (  # noqa: E402
    CLINIC_ID,
    HOST,
    PATIENT,
    NoteTransport,
    consent_for,
    context,
    make_registry,
    note_body,
    ok,
    status,
)
from scribe_desktop.clinics import ClinicRefusal, Refused  # noqa: E402
from scribe_desktop.encounter import (  # noqa: E402
    EncounterRecord,
    NoteRefusal,
    Verification,
    VerifiedTarget,
    WritebackRefusal,
    WritebackRefused,
    reverification_request,
    unlinked_consent,
    verify_note_context,
    write_encounter_record,
)
from scribe_desktop.secure_storage import SessionCrypto  # noqa: E402
from scribe_desktop.session import RecordingSession, SessionState  # noqa: E402
from scribe_desktop.session_store import (  # noqa: E402
    AUDIO_FILENAME,
    KEY_FILENAME,
    SessionChunkStore,
)
from scribe_desktop.transcription import RecoveryOutcome  # noqa: E402
from scribe_desktop.ui import models  # noqa: E402
from test_ui_screens import FakeController, _document, _main_window, _process_until  # noqa: E402


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _registry(tmp_path: Path, **kwargs: Any) -> Any:
    root = tmp_path / "registry"
    root.mkdir(exist_ok=True)
    return make_registry(root, **kwargs)


def _window(tmp_path: Path, registry: Any, controller: Any = None) -> Any:
    return _main_window(tmp_path, controller, clinic_registry=registry)


def _recoverable(root: Path, record: EncounterRecord | None) -> tuple[Path, SessionCrypto]:
    """A crashed session on disk (fake key blob, a finished audio store) and
    its in-memory key, with ``encounter.enc`` when ``record`` is given."""
    session_id = uuid.uuid4().hex
    directory = root / session_id
    directory.mkdir(parents=True)
    (directory / KEY_FILENAME).write_bytes(b"\x01" * 64)
    crypto = SessionCrypto()
    store = SessionChunkStore.create(directory / AUDIO_FILENAME, crypto, session_id)
    store.append_chunk(b"\x00\x01" * 800)
    store.finish()
    store.close()
    if record is not None:
        write_encounter_record(directory, crypto, session_id, record)
    return directory, crypto


def _linked_record() -> EncounterRecord:
    ctx = context()
    return EncounterRecord(consent=consent_for(ctx), context=ctx)


def _check_out(window: Any, directory: Path, crypto: SessionCrypto) -> None:
    outcome = RecoveryOutcome(document=_document(), crypto=crypto, store_finished=True)
    window._on_recovered((directory, outcome))


def _settled(qapp: Any, window: Any) -> None:
    assert _process_until(qapp, lambda: not window.is_reverifying)
    qapp.processEvents()


class TestLiveSessionClinic:
    """D10's Remove refusal is answered from the live session's context."""

    def _session(self, linked: bool, state: SessionState) -> RecordingSession:
        ctx = context() if linked else None
        consent = consent_for(ctx) if ctx is not None else unlinked_consent()
        return RecordingSession(consent=consent, encounter_context=ctx).with_state(state)

    @pytest.mark.parametrize(
        "state",
        [
            SessionState.RECORDING,
            SessionState.PAUSED,
            SessionState.PROCESSING,
            SessionState.QUEUED,
            SessionState.FAILED,
        ],
    )
    def test_a_linked_live_session_names_its_clinic(
        self, qapp: Any, tmp_path: Path, state: SessionState
    ) -> None:
        controller = FakeController()
        controller.session_value = self._session(True, state)
        window = _window(tmp_path, _registry(tmp_path), controller)
        assert window._live_session_clinic() == CLINIC_ID
        window.close()

    @pytest.mark.parametrize(
        "linked, state",
        [
            (False, SessionState.RECORDING),
            (True, SessionState.WRITTEN),
            (True, SessionState.DISCARDED),
        ],
    )
    def test_unlinked_or_finished_sessions_name_none(
        self, qapp: Any, tmp_path: Path, linked: bool, state: SessionState
    ) -> None:
        controller = FakeController()
        controller.session_value = self._session(linked, state)
        window = _window(tmp_path, _registry(tmp_path), controller)
        assert window._live_session_clinic() is None
        window.close()

    def test_remove_is_refused_while_the_live_session_is_linked(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        controller = FakeController()
        controller.session_value = self._session(True, SessionState.RECORDING)
        registry = _registry(tmp_path)
        window = _window(tmp_path, registry, controller)
        outcome = registry.remove(CLINIC_ID, live_session_clinic=window._live_session_clinic())
        assert outcome == Refused(ClinicRefusal.LINKED_TO_LIVE_SESSION, CLINIC_ID)
        assert registry.record(CLINIC_ID) is not None
        window.close()


class TestRecoveryListLinkLine:
    @pytest.mark.parametrize("has_record", [True, False], ids=["record", "no-record"])
    def test_the_list_says_only_what_the_stat_shows(
        self, qapp: Any, tmp_path: Path, has_record: bool
    ) -> None:
        _recoverable(tmp_path, _linked_record() if has_record else None)
        window = _window(tmp_path, _registry(tmp_path))
        text = window.recovery_screen.session_list.item(0).text()
        expected = (
            models.RECOVERY_ENCOUNTER_LINE if has_record else models.RECOVERY_NO_ENCOUNTER_LINE
        )
        assert expected in text
        for identifier in (HOST, PATIENT, CLINIC_ID):
            assert identifier not in text  # nothing decrypted, nothing named
        window.close()

    def test_refreshing_the_list_never_decrypts(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import scribe_desktop.ui.main_window as main_window_mod

        _recoverable(tmp_path, _linked_record())
        window = _window(tmp_path, _registry(tmp_path))
        calls: list[int] = []
        monkeypatch.setattr(
            main_window_mod, "read_encounter_record", lambda *a: calls.append(1)
        )
        monkeypatch.setattr(
            SessionCrypto, "decrypt", lambda *a, **k: pytest.fail("decrypted on refresh")
        )
        for _ in range(3):
            window.recovery_screen.refresh()
        assert calls == []
        window.close()


class TestRecoveredCheckout:
    def test_a_linked_checkout_decrypts_once_and_reverifies(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import scribe_desktop.ui.main_window as main_window_mod

        transport = NoteTransport()
        window = _window(tmp_path, _registry(tmp_path, transport=transport))
        directory, crypto = _recoverable(tmp_path, _linked_record())
        real = main_window_mod.read_encounter_record
        reads: list[str] = []

        def counting(*args: Any) -> Any:
            reads.append(args[2])
            return real(*args)

        monkeypatch.setattr(main_window_mod, "read_encounter_record", counting)
        _check_out(window, directory, crypto)
        assert reads == [directory.name]  # exactly one decrypt, on checkout
        # Until Cliniko answers, the session does not count as linked.
        _settled(qapp, window)
        # Round 20 LOW-014: the line is on the screen the checkout lands on.
        assert window.tabs.currentWidget() is window.transcript_screen
        assert window.transcript_screen.link_label.text() == models.CHECKOUT_VERIFIED_LINE
        assert [call[2] for call in transport.calls][0].startswith("/v1/treatment_notes/")
        target = window.recovered_writeback_target()
        assert isinstance(target, VerifiedTarget) and target.patient_id == PATIENT
        for _ in range(3):
            window.recovery_screen.refresh()
        assert reads == [directory.name]  # the periodic refresh never decrypts again
        window.close()

    def test_before_the_answer_the_checkout_is_not_linked(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        gate = threading.Event()

        def held() -> Any:
            gate.wait(10)
            return ok(note_body())

        window = _window(tmp_path, _registry(tmp_path, transport=NoteTransport(note=held)))
        directory, crypto = _recoverable(tmp_path, _linked_record())
        _check_out(window, directory, crypto)
        assert window.transcript_screen.link_label.text() == models.CHECKOUT_REVERIFYING_LINE
        assert window.recovered_writeback_target() == WritebackRefused(
            WritebackRefusal.NOT_REVERIFIED
        )
        gate.set()
        _settled(qapp, window)
        assert isinstance(window.recovered_writeback_target(), VerifiedTarget)
        window.close()

    def test_a_finished_check_keeps_no_reference_to_its_request(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 20 LOW-013: the check thread stays a child of the window, so
        its closure must not keep the request — the checkout's patient and
        note ids — once the checkout has ended."""
        from PySide6.QtCore import QThread

        from scribe_desktop.encounter import VerificationRequest
        from test_ui_clinics import _reaches

        window = _window(tmp_path, _registry(tmp_path))
        directory, crypto = _recoverable(tmp_path, _linked_record())
        _check_out(window, directory, crypto)
        _settled(qapp, window)
        window._on_transcript_closed("discarded")
        threads = [
            t
            for t in window.findChildren(QThread)
            if "_run_reverification" in getattr(getattr(t, "_fn", None), "__qualname__", "")
        ]
        assert threads, "no finished check thread found to inspect"
        for thread in threads:
            assert not _reaches(thread._fn, lambda o: isinstance(o, VerificationRequest))
        window.close()

    def test_an_answer_after_the_view_closed_changes_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        gate = threading.Event()

        def held() -> Any:
            gate.wait(10)
            return ok(note_body())

        window = _window(tmp_path, _registry(tmp_path, transport=NoteTransport(note=held)))
        directory, crypto = _recoverable(tmp_path, _linked_record())
        _check_out(window, directory, crypto)
        window._on_transcript_closed("discarded")
        assert window.recovered_writeback_target() is None  # no checkout any more
        gate.set()
        _settled(qapp, window)
        assert window.recovered_writeback_target() is None
        assert window.transcript_screen.link_label.text() == ""
        window.close()

    @pytest.mark.parametrize("released_by", ["start", "live_transcript"])
    @pytest.mark.parametrize("linked", [True, False], ids=["linked", "unlinked"])
    def test_a_checkout_released_without_complete_enters_the_index_if_linked(
        self,
        qapp: Any,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        released_by: str,
        linked: bool,
    ) -> None:
        """H1 round 53 LOW-040's sibling: a recovered session whose view a
        Start or a live transcript replaces is Unreviewed from then on, so a
        LINKED one enters the reminder index (with a reference for its
        banner) at once, as the start-up rebuild would index it — from the
        checkout's own record, never a second decrypt. An unlinked one adds
        nothing (the control)."""
        import scribe_desktop.ui.main_window as main_window_mod

        window = _window(tmp_path, _registry(tmp_path))
        record = _linked_record() if linked else EncounterRecord(consent=unlinked_consent())
        directory, crypto = _recoverable(tmp_path, record)
        _check_out(window, directory, crypto)
        _settled(qapp, window)
        reads: list[str] = []
        real = main_window_mod.read_encounter_record
        monkeypatch.setattr(
            main_window_mod,
            "read_encounter_record",
            lambda *args: reads.append(args[2]) or real(*args),
        )
        if released_by == "start":
            window._on_session_started()
        else:
            window._on_live_transcript(_document())
        assert (directory.name in window.reminders) is linked
        assert (window._controller.session_ref_for(directory.name) is not None) is linked
        assert reads == []
        window.close()

    @pytest.mark.parametrize(
        "record, line, refusal",
        [
            (None, models.CHECKOUT_CONSENT_UNAVAILABLE_LINE, WritebackRefusal.CONSENT_UNAVAILABLE),
            (
                EncounterRecord(consent=unlinked_consent()),
                models.CHECKOUT_UNLINKED_LINE,
                WritebackRefusal.UNLINKED,
            ),
        ],
        ids=["missing-record", "unlinked-record"],
    )
    def test_missing_or_unlinked_means_unlinked_and_no_call(
        self,
        qapp: Any,
        tmp_path: Path,
        record: EncounterRecord | None,
        line: str,
        refusal: WritebackRefusal,
    ) -> None:
        transport = NoteTransport()
        window = _window(tmp_path, _registry(tmp_path, transport=transport))
        directory, crypto = _recoverable(tmp_path, record)
        _check_out(window, directory, crypto)
        assert not window.is_reverifying
        assert window.transcript_screen.link_label.text() == line
        assert window.recovered_writeback_target() == WritebackRefused(refusal)
        assert transport.calls == []
        window.close()

    def test_an_undecryptable_record_is_consent_unavailable(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        transport = NoteTransport()
        window = _window(tmp_path, _registry(tmp_path, transport=transport))
        directory, _crypto = _recoverable(tmp_path, _linked_record())
        _check_out(window, directory, SessionCrypto())  # another key
        assert window.transcript_screen.link_label.text() == (
            models.CHECKOUT_CONSENT_UNAVAILABLE_LINE
        )
        assert window.recovered_writeback_target() == WritebackRefused(
            WritebackRefusal.CONSENT_UNAVAILABLE
        )
        assert transport.calls == []
        window.close()

    def test_a_removed_clinic_means_no_call_and_no_write_back(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        transport = NoteTransport()
        registry = _registry(tmp_path, transport=transport)
        registry.remove(CLINIC_ID, live_session_clinic=None)
        window = _window(tmp_path, registry)
        directory, crypto = _recoverable(tmp_path, _linked_record())
        _check_out(window, directory, crypto)
        assert window.transcript_screen.link_label.text() == models.CHECKOUT_CLINIC_GONE_LINE
        assert window.recovered_writeback_target() == WritebackRefused(
            WritebackRefusal.CLINIC_GONE
        )
        assert transport.calls == []
        window.close()

    def test_a_refused_reverification_names_its_reason(self, qapp: Any, tmp_path: Path) -> None:
        transport = NoteTransport(note=ok(note_body(draft=False)))
        window = _window(tmp_path, _registry(tmp_path, transport=transport))
        directory, crypto = _recoverable(tmp_path, _linked_record())
        _check_out(window, directory, crypto)
        _settled(qapp, window)
        text = window.transcript_screen.link_label.text()
        assert models.note_refusal_line(NoteRefusal.NOTE_FINAL) in text
        assert window.recovered_writeback_target() == WritebackRefused(
            WritebackRefusal.REVERIFICATION_REFUSED, NoteRefusal.NOTE_FINAL
        )
        window.close()

    def test_an_offline_reverification_blocks_write_back(self, qapp: Any, tmp_path: Path) -> None:
        window = _window(tmp_path, _registry(tmp_path, transport=NoteTransport(note=status(503))))
        directory, crypto = _recoverable(tmp_path, _linked_record())
        _check_out(window, directory, crypto)
        _settled(qapp, window)
        assert window.transcript_screen.link_label.text() == models.CHECKOUT_OFFLINE_LINE
        assert window.recovered_writeback_target() == WritebackRefused(
            WritebackRefusal.NOT_VERIFIED
        )
        window.close()

    def test_a_key_replace_voids_the_reverification_and_checks_again(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        transport = NoteTransport()
        registry = _registry(tmp_path, transport=transport)
        window = _window(tmp_path, registry)
        directory, crypto = _recoverable(tmp_path, _linked_record())
        _check_out(window, directory, crypto)
        _settled(qapp, window)
        assert isinstance(window.recovered_writeback_target(), VerifiedTarget)
        calls_before = len(transport.calls)
        registry._bump(CLINIC_ID)  # what Replace key's dispatch does (D9)
        assert window.recovered_writeback_target() == WritebackRefused(
            WritebackRefusal.REVERIFICATION_STALE
        )
        window.clinics_screen.clinics_changed.emit()
        _settled(qapp, window)
        assert len(transport.calls) > calls_before  # checked again under the new rev
        assert isinstance(window.recovered_writeback_target(), VerifiedTarget)
        window.close()

    def test_the_live_writeback_target_follows_the_live_session(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        controller = FakeController()
        registry = _registry(tmp_path)
        window = _window(tmp_path, registry, controller)
        assert window.live_writeback_target() is None
        ctx = context(Verification.UNVERIFIED_OFFLINE)
        controller.session_value = RecordingSession(
            consent=consent_for(ctx), encounter_context=ctx
        ).with_state(SessionState.RECORDING)
        assert window.live_writeback_target() == WritebackRefused(WritebackRefusal.NOT_VERIFIED)
        verified = context()
        controller.session_value = RecordingSession(
            consent=consent_for(verified), encounter_context=verified
        ).with_state(SessionState.QUEUED)
        # Round 20 MED-012: the Start verification alone never yields a target.
        assert window.live_writeback_target() == WritebackRefused(
            WritebackRefusal.NOT_REVERIFIED
        )
        request = reverification_request(verified, registry, seq=1)
        assert request is not None
        reverified = verify_note_context(
            request, key_store=registry.key_store, transport=registry.transport
        )
        assert isinstance(window.live_writeback_target(reverified), VerifiedTarget)
        window.close()
