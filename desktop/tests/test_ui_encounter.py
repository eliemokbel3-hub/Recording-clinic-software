"""The desktop side of the encounter (Cliniko workflow safeguards plan Tasks
3.3 and 3.4): the live session's clinic for the Clinics tab, the recovery
list's stat-only link line, and the recovered checkout — its one decrypt of
``encounter.enc`` and its D4 re-verification. Offscreen; every Cliniko
answer comes from an injected transport and every key from memory."""

from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from encounter_fakes import (  # noqa: E402
    CLINIC_ID,
    HOST,
    NOTE,
    PATIENT,
    TEMPLATE,
    NoteTransport,
    consent_for,
    context,
    make_registry,
    note_body,
    ok,
    status,
)
from scribe_desktop.clinics import ClinicRefusal, Refused  # noqa: E402
from scribe_desktop.draft_write import record_status  # noqa: E402
from scribe_desktop.encounter import (  # noqa: E402
    RATE_LIMIT_COOLDOWN_SECONDS,
    EncounterRecord,
    NoteRefusal,
    RateLimitLatch,
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
from test_draft_write import (  # noqa: E402
    _HISTORY,
    _IDENTITY,
    Cliniko,
    _content,
    _profile,
    _record,
    _write_note,
)
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


def _window(tmp_path: Path, registry: Any, controller: Any = None, **overrides: Any) -> Any:
    return _main_window(tmp_path, controller, clinic_registry=registry, **overrides)


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

    # --- draft-write Task 1.3 (D13): the one 429 latch -------------------------

    def test_a_cooling_clinic_is_answered_offline_without_a_call(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """A 429 recorded by any caller (the bridge, the write) makes the
        checkout show the existing offline line with no call; reopening the
        row after the minute checks again."""
        now = [0.0]
        latch = RateLimitLatch(lambda: now[0])
        transport = NoteTransport()
        window = _window(tmp_path, _registry(tmp_path, transport=transport), rate_limit_latch=latch)
        latch.record_429(CLINIC_ID, now[0])
        directory, crypto = _recoverable(tmp_path, _linked_record())
        _check_out(window, directory, crypto)
        assert not window.is_reverifying
        assert transport.calls == []
        assert window.transcript_screen.link_label.text() == models.CHECKOUT_OFFLINE_LINE
        assert window.recovered_writeback_target() == WritebackRefused(
            WritebackRefusal.NOT_VERIFIED
        )
        now[0] = RATE_LIMIT_COOLDOWN_SECONDS
        window._begin_checkout(directory.name, _linked_record())  # the row reopened
        _settled(qapp, window)
        assert len(transport.calls) >= 1
        assert window.transcript_screen.link_label.text() == models.CHECKOUT_VERIFIED_LINE
        window.close()

    def test_a_checkout_429_is_recorded_in_the_latch_the_bridge_shares(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        now = [5.0]
        latch = RateLimitLatch(lambda: now[0])
        registry = _registry(tmp_path, transport=NoteTransport(note=status(429)))
        window = _window(tmp_path, registry, rate_limit_latch=latch)
        bridge = window.attach_chrome_link()
        assert bridge._latch is latch  # ONE latch: the bridge reads what the checkout records
        directory, crypto = _recoverable(tmp_path, _linked_record())
        _check_out(window, directory, crypto)
        _settled(qapp, window)
        assert latch.cooling(CLINIC_ID, now[0]) == RATE_LIMIT_COOLDOWN_SECONDS
        window.close()

    def test_a_stale_checkout_429_is_still_recorded(self, qapp: Any, tmp_path: Path) -> None:
        """PR-LOW-008: the checkout is the third producer — its 429 cools the
        clinic even when the view it answered has closed."""
        gate = threading.Event()

        def held() -> Any:
            gate.wait(10)
            return status(429)

        latch = RateLimitLatch(lambda: 0.0)
        window = _window(
            tmp_path,
            _registry(tmp_path, transport=NoteTransport(note=held)),
            rate_limit_latch=latch,
        )
        directory, crypto = _recoverable(tmp_path, _linked_record())
        _check_out(window, directory, crypto)
        window._on_transcript_closed("discarded")  # the answer will be stale
        gate.set()
        _settled(qapp, window)
        assert window.transcript_screen.link_label.text() == ""
        assert latch.cooling(CLINIC_ID, 0.0) == RATE_LIMIT_COOLDOWN_SECONDS
        window.close()

    def test_a_429_is_recorded_before_the_waiting_check_starts(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """PR-LOW-008's ORDER: a check requested while a 429 is in flight is
        answered from the cooldown when that 429 lands — no second call."""
        gate = threading.Event()
        note_reads: list[int] = []

        def held() -> Any:
            note_reads.append(1)
            gate.wait(10)
            return status(429)

        latch = RateLimitLatch(lambda: 0.0)
        window = _window(
            tmp_path,
            _registry(tmp_path, transport=NoteTransport(note=held)),
            rate_limit_latch=latch,
        )
        directory, crypto = _recoverable(tmp_path, _linked_record())
        _check_out(window, directory, crypto)
        window._begin_checkout(directory.name, _linked_record())  # waits behind the first
        gate.set()
        _settled(qapp, window)
        assert note_reads == [1]
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


# ---------------------------------------------------------------------------
# Draft-write Task 5.2 (and Task 5.3's never-call pins): MainWindow's write
# slot — hop 1, the GUI-thread preparation, the attempt row, hop 2 and the
# outcome — over a fake Cliniko transport, a memory write store and the
# test's own template profile. No request ever leaves the process.
# ---------------------------------------------------------------------------


class _MemoryWriteStore:
    """The ``WriteStore`` seam: the saved note and ``write.enc`` in memory.
    ``stored`` keeps every record with the transport's request count at the
    moment it was stored (the attempt row must precede the PATCH)."""

    def __init__(self, note: Any = None, *, identity: str = _IDENTITY) -> None:
        self.note = note if note is not None else _write_note()
        self.identity = identity
        self.record: Any = None
        self.stored: list[tuple[str, int]] = []
        self.fail_on: set[str] = set()
        self.requests: Any = lambda: 0

    def load(self, directory: Path, crypto: SessionCrypto, session_id: str) -> Any:
        return models.WriteInputs(self.record, self.note, self.identity)

    def store(self, directory: Path, crypto: SessionCrypto, session_id: str, record: Any) -> None:
        if record.outcome in self.fail_on:
            raise OSError("disk full")
        self.stored.append((record.outcome, self.requests()))
        self.record = record


class _WriteController(FakeController):
    """A linked (or unlinked) QUEUED session whose write record is the
    store's."""

    def __init__(
        self, store: _MemoryWriteStore, *, linked: bool = True, template_id: str | None = TEMPLATE
    ) -> None:
        super().__init__()
        self.store = store
        ctx = context(template_id=template_id) if linked else None
        consent = consent_for(ctx) if ctx is not None else unlinked_consent()
        self.session_value = RecordingSession(
            consent=consent, encounter_context=ctx
        ).with_state(SessionState.QUEUED)

    def write_record_status(self, session_id: str) -> Any:
        self.calls.append(("write_record_status", session_id))
        return record_status(self.store.record, self.store.identity)


def _count(calls: list[Any], name: str) -> int:
    return sum(1 for call in calls if call[0] == name)


class _Gate:
    """A request held on the worker until the test releases it. ``release``
    runs in the test's ``finally``: it opens the gate and waits for the
    write to end, so a failed assertion never leaves a worker running (round
    34 LOW-013); ``timed_out`` tells a stuck gate from the path under test."""

    def __init__(self) -> None:
        self.gate = threading.Event()
        self.entered = threading.Event()
        self.timed_out = False

    def hold(self) -> None:
        self.entered.set()
        if not self.gate.wait(10):
            self.timed_out = True
            raise RuntimeError("the test never released the gate")

    def release(self, qapp: Any, window: Any) -> None:
        self.gate.set()
        assert _process_until(qapp, lambda: not window.is_writing)
        qapp.processEvents()


def _gated(method: str, prefix: str) -> tuple[Any, _Gate]:
    """A ``Cliniko`` fake whose every ``method`` request under ``prefix``
    waits at the gate."""
    gated = _Gate()
    cliniko = Cliniko()
    answer = cliniko.request

    def blocking(verb: str, host: str, path: str, *args: Any, **kwargs: Any) -> Any:
        if verb == method and path.startswith(prefix):
            gated.hold()
        return answer(verb, host, path, *args, **kwargs)

    cliniko.request = blocking  # type: ignore[method-assign]
    return cliniko, gated


class TestDraftWrite:
    def _window(
        self,
        tmp_path: Path,
        *,
        cliniko: Any = None,
        store: _MemoryWriteStore | None = None,
        linked: bool = True,
        profile: Any = None,
        template_id: str | None = TEMPLATE,
        **overrides: Any,
    ) -> tuple[Any, _WriteController, Any, _MemoryWriteStore]:
        cliniko = cliniko if cliniko is not None else Cliniko()
        store = store if store is not None else _MemoryWriteStore()
        store.requests = lambda: len(cliniko.calls)
        controller = _WriteController(store, linked=linked, template_id=template_id)
        registry = _registry(tmp_path, transport=cliniko)
        window = _window(
            tmp_path,
            registry,
            controller,
            write_store=store,
            write_profile=profile if profile is not None else (lambda note: _profile()),
            **overrides,
        )
        session = controller.session_value
        assert session is not None
        window.note_screen.show_saved_note(
            store.note,
            _document(),
            info="",
            copy_enabled=True,
            write_binding=models.WriteBinding(session.session_id, linked),
        )
        return window, controller, cliniko, store

    def _click(self, qapp: Any, window: Any, controller: Any) -> None:
        window.note_screen.write_requested.emit(controller.session_value.session_id)
        assert _process_until(qapp, lambda: not window.is_writing)
        qapp.processEvents()

    @staticmethod
    def _line(window: Any) -> str | None:
        return window.note_screen._write_line

    def test_a_write_reads_then_records_the_attempt_then_patches(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window, controller, cliniko, store = self._window(tmp_path)
        assert window.note_screen.write_button.isEnabled()
        window.note_screen.write_button.click()
        assert _process_until(qapp, lambda: not window.is_writing)
        qapp.processEvents()
        # D15: hop 1 is ONE note read — no template read.
        assert cliniko.calls == [
            ("GET", f"/v1/treatment_notes/{NOTE}"),
            ("PATCH", f"/v1/treatment_notes/{NOTE}"),
        ]
        # The attempt row was on disk after the read and BEFORE the PATCH.
        assert store.stored == [("attempting", 1), ("written", 2)]
        assert self._line(window) == models.write_line("written_seen")
        assert window.note_screen.write_label.text() == models.write_line("written_seen")
        assert not window.note_screen.write_button.isEnabled()  # seen mode: Complete next
        assert controller.write_releases == 1 and controller.writing_id is None
        assert not window.note_screen.is_busy
        assert window._rate_limit_latch.cooling(CLINIC_ID, 0.0) is None
        window.close()

    def test_a_mock_note_never_calls_the_transport(self, qapp: Any, tmp_path: Path) -> None:
        """D10's second gate (Task 5.3): the slot's ``refuse_before_read``,
        reached here by the slot directly — the tab's own gate never emits."""
        store = _MemoryWriteStore(_write_note(provider_name="mock-provider"))
        window, controller, cliniko, _store = self._window(tmp_path, store=store)
        assert not window.note_screen.write_button.isEnabled()
        window._on_write_requested(controller.session_value.session_id)
        assert not window.is_writing
        assert cliniko.calls == []
        assert self._line(window) == models.write_line("mock_note")
        assert store.stored == []
        assert controller.write_releases == 1
        window.close()

    def test_an_unlinked_session_never_reserves_or_calls(self, qapp: Any, tmp_path: Path) -> None:
        """Constraint 10 (Task 5.3): nothing is reserved, read or sent."""
        window, controller, cliniko, store = self._window(tmp_path, linked=False)
        window._on_write_requested(controller.session_value.session_id)
        assert not window.is_writing
        assert cliniko.calls == []
        assert _count(controller.calls, "reserve_write") == 0
        assert self._line(window) == models.write_line("unlinked")
        assert store.stored == []
        window.close()

    def test_a_patch_403_is_finalised_and_the_next_click_is_forbidden(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window, controller, cliniko, store = self._window(
            tmp_path, cliniko=Cliniko(patch=status(403))
        )
        self._click(qapp, window, controller)
        assert self._line(window) == models.write_line("finalised_before_write")
        assert [outcome for outcome, _ in store.stored] == ["attempting", "refused"]
        # The note still reads as a draft: the repeat guard refuses before
        # any send (R22-02).
        self._click(qapp, window, controller)
        assert self._line(window) == models.write_line("write_forbidden")
        assert _count(cliniko.calls, "PATCH") == 1
        assert controller.write_releases == 2
        window.close()

    def test_an_unknown_outcome_is_reconciled_by_the_next_click(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window, controller, cliniko, store = self._window(
            tmp_path, cliniko=Cliniko(patch=status(503))
        )
        self._click(qapp, window, controller)
        assert self._line(window) == models.write_line("unknown")
        assert [outcome for outcome, _ in store.stored] == ["attempting", "unknown"]
        assert window.note_screen.write_button.isEnabled()  # the click reconciles
        # The write DID land: Cliniko now answers the sent content.
        sent = json.loads(cliniko.bodies[-1] or b"{}")["content"]
        cliniko.answers[("GET", "/v1/treatment_notes/")] = [ok(note_body(content=sent))]
        self._click(qapp, window, controller)
        assert self._line(window) == models.write_line("written_seen")
        assert store.stored[-1][0] == "written"
        assert _count(cliniko.calls, "PATCH") == 1
        window.close()

    def test_a_raise_before_the_attempt_releases_and_sends_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        def broken(_note: Any) -> Any:
            raise RuntimeError("profile config unreadable")

        window, controller, cliniko, store = self._window(tmp_path, profile=broken)
        self._click(qapp, window, controller)
        assert self._line(window) == models.write_line("not_sent")
        assert [call[0] for call in cliniko.calls] == ["GET"]
        assert store.stored == []
        assert controller.write_releases == 1 and controller.writing_id is None
        window.close()

    def test_a_finished_record_that_cannot_be_stored_reads_unknown(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        store = _MemoryWriteStore()
        store.fail_on = {"written"}
        window, controller, _cliniko, _store = self._window(tmp_path, store=store)
        self._click(qapp, window, controller)
        assert self._line(window) == models.write_line("unknown")
        assert store.stored == [("attempting", 1)]  # still open: the next click reconciles
        assert controller.write_releases == 1
        window.close()

    def test_while_writing_the_window_refuses_close_and_blocks_the_screens(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from PySide6.QtGui import QCloseEvent

        cliniko, gated = _gated("PATCH", "/v1/treatment_notes/")
        window, controller, _cliniko, _store = self._window(tmp_path, cliniko=cliniko)
        window.note_screen.write_button.click()
        try:
            assert _process_until(qapp, gated.entered.is_set)
            assert window.is_writing
            assert window.note_screen.is_busy
            assert not window.note_screen.write_button.isEnabled()
            assert window.transcript_screen._write_blocked
            assert window.recovery_screen._write_blocked
            # H1 round 45 LOW-002: the next patient's Start waits for the write.
            assert not window.session_screen.consent_checkbox.isEnabled()
            event = QCloseEvent()
            window.closeEvent(event)
            assert not event.isAccepted()
            assert window.statusBar().currentMessage() == models.write_line("write_in_flight")
            # A second click meets the write in flight: nothing reserved again.
            reserves = _count(controller.calls, "reserve_write")
            window._on_write_requested(controller.session_value.session_id)
            assert self._line(window) == models.write_line("write_in_flight")
            assert _count(controller.calls, "reserve_write") == reserves
        finally:
            gated.release(qapp, window)
        assert not gated.timed_out
        assert self._line(window) == models.write_line("written_seen")
        assert not window.transcript_screen._write_blocked
        assert not window.recovery_screen._write_blocked
        assert window.session_screen.consent_checkbox.isEnabled()
        window.close()

    def test_a_cooling_clinic_is_refused_before_anything_is_reserved(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        latch = RateLimitLatch(clock=lambda: 100.0)
        latch.record_429(CLINIC_ID, 100.0)
        window, controller, cliniko, _store = self._window(tmp_path, rate_limit_latch=latch)
        window._on_write_requested(controller.session_value.session_id)
        assert self._line(window) == models.write_line(
            "rate_limited", seconds=RATE_LIMIT_COOLDOWN_SECONDS
        )
        assert cliniko.calls == []
        assert _count(controller.calls, "reserve_write") == 0
        window.close()

    def test_a_hop_one_429_cools_the_clinic_and_sends_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        latch = RateLimitLatch(clock=lambda: 100.0)
        window, controller, cliniko, store = self._window(
            tmp_path, cliniko=Cliniko(notes=(status(429),)), rate_limit_latch=latch
        )
        self._click(qapp, window, controller)
        assert latch.cooling(CLINIC_ID, 100.0) is not None
        assert self._line(window) == models.write_line(
            "rate_limited", seconds=RATE_LIMIT_COOLDOWN_SECONDS
        )
        assert _count(cliniko.calls, "PATCH") == 0
        assert store.stored == []
        assert controller.write_releases == 1
        window.close()

    def test_a_patch_429_is_unknown_and_cools_the_clinic(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """H1 round 45 LOW-003 (D13: a 429 from EITHER hop is recorded): a
        429 on the PATCH is an unknown outcome AND cools the shared latch,
        so the next click is refused before any request, carrying the open
        attempt's warning."""
        latch = RateLimitLatch(clock=lambda: 100.0)
        window, controller, cliniko, store = self._window(
            tmp_path, cliniko=Cliniko(patch=status(429)), rate_limit_latch=latch
        )
        self._click(qapp, window, controller)
        assert self._line(window) == models.write_line("unknown")
        assert [outcome for outcome, _ in store.stored] == ["attempting", "unknown"]
        assert latch.cooling(CLINIC_ID, 100.0) is not None
        requests = len(cliniko.calls)
        window._on_write_requested(controller.session_value.session_id)
        assert self._line(window) == models.write_line(
            "rate_limited", uncertain=True, seconds=RATE_LIMIT_COOLDOWN_SECONDS
        )
        assert len(cliniko.calls) == requests
        assert _count(controller.calls, "reserve_write") == 1
        window.close()

    def test_a_read_answering_with_another_note_writes_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """H3 round 47 SEC-002: hop 1's answer for this note's URL carries
        another note's id — refused as an unreadable answer, nothing stored,
        no PATCH, the reservation released."""
        window, controller, cliniko, store = self._window(
            tmp_path, cliniko=Cliniko(notes=(ok(note_body(content=_content(), id="2002")),))
        )
        self._click(qapp, window, controller)
        line = self._line(window)
        assert line is not None
        assert models.note_refusal_line(NoteRefusal.ANSWER_UNREADABLE) in line
        assert store.stored == []
        assert _count(cliniko.calls, "PATCH") == 0
        assert controller.write_releases == 1 and controller.writing_id is None
        window.close()

    @pytest.mark.parametrize("open_attempt", [False, True])
    def test_a_cooldown_another_path_records_during_hop_one_stops_hop_two(
        self, qapp: Any, tmp_path: Path, open_attempt: bool
    ) -> None:
        """Codex round 35 PR-MED-038 (D13: a 429 seen by one path stops the
        others): the Chrome bridge or the checkout records a 429 for this
        clinic while hop 1 is on the wire, so the write is refused between
        the hops — nothing stored, no PATCH, the reservation released, and
        an earlier open attempt's warning kept."""
        latch = RateLimitLatch(clock=lambda: 100.0)
        cliniko, gated = _gated("GET", "/v1/treatment_notes/")
        store = _MemoryWriteStore()
        if open_attempt:
            store.record = _record("unknown")
        window, controller, _cliniko, _store = self._window(
            tmp_path, cliniko=cliniko, store=store, rate_limit_latch=latch
        )
        window._on_write_requested(controller.session_value.session_id)
        try:
            assert _process_until(qapp, gated.entered.is_set)
            # Another producer (the bridge's own `record_429`) on the shared latch.
            latch.record_429(CLINIC_ID, 100.0)
        finally:
            gated.release(qapp, window)
        assert not gated.timed_out
        assert self._line(window) == models.write_line(
            "rate_limited", uncertain=open_attempt, seconds=RATE_LIMIT_COOLDOWN_SECONDS
        )
        assert [call[0] for call in cliniko.calls] == ["GET"]
        assert store.stored == []
        assert controller.write_releases == 1 and controller.writing_id is None
        window.close()

    def test_a_recovery_run_or_a_key_check_for_the_clinic_refuses_the_click(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window, controller, cliniko, _store = self._window(tmp_path)
        session_id = controller.session_value.session_id
        window.recovery_screen._busy = True
        window._on_write_requested(session_id)
        assert self._line(window) == models.write_line("recovery_busy")
        window.recovery_screen._busy = False
        window.clinics_screen._pending = SimpleNamespace(clinic_id=CLINIC_ID)
        window._on_write_requested(session_id)
        assert self._line(window) == models.write_line("clinic_busy")
        window.clinics_screen._pending = None
        assert cliniko.calls == []
        assert _count(controller.calls, "reserve_write") == 0
        window.close()

    def test_a_stale_or_written_click_sends_nothing(self, qapp: Any, tmp_path: Path) -> None:
        window, controller, cliniko, _store = self._window(tmp_path)
        window._on_write_requested("not-the-live-session")
        assert self._line(window) == models.write_line("not_sent")
        self._click(qapp, window, controller)
        calls = len(cliniko.calls)
        # Seen mode (D6): a record already written for this note completes
        # on Complete, never by another request.
        window._on_write_requested(controller.session_value.session_id)
        assert self._line(window) == models.write_line("written_seen")
        assert len(cliniko.calls) == calls
        window.close()

    # --- round 33 MED-001: the slot's remaining legs --------------------------

    @pytest.mark.parametrize("template_id", [TEMPLATE, None])
    def test_hop_one_is_one_read_with_or_without_a_template_id(
        self, qapp: Any, tmp_path: Path, template_id: str | None
    ) -> None:
        """D15: the click reads the note ONCE whether or not the linked
        context carries a template id (an offline-started session has none)
        — no discovery read, no template read."""
        window, controller, cliniko, _store = self._window(tmp_path, template_id=template_id)
        self._click(qapp, window, controller)
        assert cliniko.calls == [
            ("GET", f"/v1/treatment_notes/{NOTE}"),
            ("PATCH", f"/v1/treatment_notes/{NOTE}"),
        ]
        assert self._line(window) == models.write_line("written_seen")
        window.close()

    def test_a_note_holding_text_takes_the_draft_below_it(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """D15 through the slot (was ``note_has_text``): the typed answer is
        kept byte-for-byte, one empty line, then the app's text."""
        typed = "<p>L knee pain</p><p>happened 2 months ago</p>"
        cliniko = Cliniko(notes=(ok(note_body(content=_content({_HISTORY: typed}))),))
        window, controller, _cliniko, _store = self._window(tmp_path, cliniko=cliniko)
        self._click(qapp, window, controller)
        assert self._line(window) == models.write_line("written_seen")
        sent = json.loads(cliniko.bodies[-1] or b"{}")["content"]
        answer = sent["sections"][0]["questions"][0]["answer"]
        assert answer.startswith(typed + "<p><br></p>") and len(answer) > len(typed) + 11
        window.close()

    def test_an_open_attempt_prefixes_every_later_refusal(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """PR-MED-017 through the slot: an earlier ``unknown`` attempt puts
        the ``write_uncertain`` warning before the lock's, the cooldown's
        and the unreadable-answer refusals; with no record the lock's line
        is bare."""
        latch = RateLimitLatch(clock=lambda: 100.0)
        window, controller, cliniko, store = self._window(tmp_path, rate_limit_latch=latch)
        session_id = controller.session_value.session_id
        warning = models.WRITE_LINES["write_uncertain"]
        locked = models.chrome_refusal_message("locked")
        window._system_events = SimpleNamespace(lock_state=lambda: "locked")
        window._on_write_requested(session_id)
        assert self._line(window) == locked
        store.record = _record("unknown")
        window._on_write_requested(session_id)
        assert self._line(window) == f"{warning} {locked}"
        window._system_events = None
        latch.record_429(CLINIC_ID, 100.0)
        window._on_write_requested(session_id)
        assert self._line(window) == models.write_line(
            "rate_limited", uncertain=True, seconds=RATE_LIMIT_COOLDOWN_SECONDS
        )
        assert _count(controller.calls, "reserve_write") == 0 and cliniko.calls == []
        window._rate_limit_latch = RateLimitLatch(clock=lambda: 100.0)
        # Round 34 LOW-012: every other pre-reserve refusal too.
        window.recovery_screen._busy = True
        window._on_write_requested(session_id)
        assert self._line(window) == models.write_line("recovery_busy", uncertain=True)
        window.recovery_screen._busy = False
        window.clinics_screen._pending = SimpleNamespace(clinic_id=CLINIC_ID)
        window._on_write_requested(session_id)
        assert self._line(window) == models.write_line("clinic_busy", uncertain=True)
        window.clinics_screen._pending = None
        assert _count(controller.calls, "reserve_write") == 0 and cliniko.calls == []
        # D15: an answer the app cannot read, after the reconcile let the
        # click through (the recorded Diagnosis answer is still as read).
        unreadable = _content({_HISTORY: ["not text"]})
        cliniko.answers[("GET", "/v1/treatment_notes/")] = [ok(note_body(content=unreadable))]
        self._click(qapp, window, controller)
        assert self._line(window) == models.write_line("note_unreadable", uncertain=True)
        assert _count(cliniko.calls, "PATCH") == 0
        # And the clinic gone before the click.
        registry = window._clinic_registry
        assert not isinstance(registry.remove(CLINIC_ID, live_session_clinic=None), Refused)
        window._on_write_requested(session_id)
        assert self._line(window) == models.write_line(
            "check_failed",
            uncertain=True,
            reason=models.writeback_refusal_line(WritebackRefusal.CLINIC_GONE),
        )
        window.close()

    def test_an_attempt_row_that_cannot_be_stored_sends_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Constraint 5: no PATCH without the ``attempting`` row on disk."""
        store = _MemoryWriteStore()
        store.fail_on = {"attempting"}
        window, controller, cliniko, _store = self._window(tmp_path, store=store)
        self._click(qapp, window, controller)
        assert self._line(window) == models.write_line("not_sent")
        assert _count(cliniko.calls, "PATCH") == 0 and store.stored == []
        assert controller.write_releases == 1 and controller.writing_id is None
        window.close()

    def test_a_worker_that_raises_is_not_sent_before_hop_two_and_unknown_after(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.ui import main_window

        def broken(*_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("worker failure text never shown")

        window, controller, cliniko, store = self._window(tmp_path)
        monkeypatch.setattr(main_window, "read_for_write", broken)
        self._click(qapp, window, controller)
        assert self._line(window) == models.write_line("not_sent")
        assert store.stored == [] and cliniko.calls == []
        monkeypatch.undo()
        monkeypatch.setattr(main_window, "write_for_click", broken)
        self._click(qapp, window, controller)
        assert self._line(window) == models.write_line("unknown")
        # The request may have left: the attempt is finished as unknown.
        assert [outcome for outcome, _ in store.stored] == ["attempting", "unknown"]
        assert controller.write_releases == 2 and controller.writing_id is None
        window.close()

    def test_a_clinic_gone_before_the_click_reserves_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window, controller, cliniko, _store = self._window(tmp_path)
        registry = window._clinic_registry
        assert not isinstance(registry.remove(CLINIC_ID, live_session_clinic=None), Refused)
        window._on_write_requested(controller.session_value.session_id)
        assert self._line(window) == models.write_line(
            "check_failed", reason=models.writeback_refusal_line(WritebackRefusal.CLINIC_GONE)
        )
        assert _count(controller.calls, "reserve_write") == 0 and cliniko.calls == []
        window.close()

    def test_a_live_session_replaced_between_the_hops_applies_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        cliniko, gated = _gated("GET", "/v1/treatment_notes/")
        window, controller, _cliniko, store = self._window(tmp_path, cliniko=cliniko)
        window.note_screen.write_button.click()
        try:
            assert _process_until(qapp, gated.entered.is_set)
            ctx = context()
            controller.session_value = RecordingSession(
                consent=consent_for(ctx), encounter_context=ctx
            ).with_state(SessionState.QUEUED)
        finally:
            gated.release(qapp, window)
        # A worker whose gate timed out would ALSO end `not_sent`: rule it out.
        assert not gated.timed_out
        assert self._line(window) == models.write_line("not_sent")
        assert _count(cliniko.calls, "PATCH") == 0 and store.stored == []
        assert controller.write_releases == 1
        window.close()

    def test_the_live_binding_names_the_session_and_its_link(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        window, controller, _cliniko, _store = self._window(tmp_path)
        session = controller.session_value
        assert window._live_write_binding() == models.WriteBinding(session.session_id, True)
        controller.session_value = session.with_state(SessionState.WRITTEN)
        assert window._live_write_binding() is None
        controller.session_value = None
        assert window._live_write_binding() is None
        window.close()
