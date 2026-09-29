"""Cliniko workflow safeguards plan Task 5.4 (D6, decided option (a)): the
Unreviewed section's "Open for review". The controller's ``adopt_queued``
reinstalls a retired session as the live queued session — its refusals, its
one decrypt, its custody consumers — and the window opens it on the live
path: the transcript with generation, or the SAVED note as it was saved with
"Regenerate (replaces the saved note)". Also the expiry warning and the
on-close list. Offscreen; real DPAPI custody (Windows-only) where a session
key is unwrapped; no pipe, no socket, no model."""

from __future__ import annotations

import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from conftest import start_unlinked  # noqa: E402
from scribe_desktop import session as session_module  # noqa: E402
from scribe_desktop.audio_capture import MockCaptureBackend  # noqa: E402
from scribe_desktop.encounter import (  # noqa: E402
    EncounterRecord,
    linked_consent,
    unlinked_consent,
    write_encounter_record,
)
from scribe_desktop.note import (  # noqa: E402
    ExtractiveNoteProvider,
    GeneratedNote,
    compose_draft,
    finalise_note,
)
from scribe_desktop.note_config import NoteConfigError  # noqa: E402
from scribe_desktop.secure_storage import SessionCrypto  # noqa: E402
from scribe_desktop.session import (  # noqa: E402
    GenerationInProgressError,
    ReviewOpenRefused,
    SessionActivityError,
    SessionController,
    SessionState,
)
from scribe_desktop.session_store import (  # noqa: E402
    AUDIO_FILENAME,
    ENCOUNTER_FILENAME,
    KEY_FILENAME,
    NOTE_FILENAME,
    TRANSCRIPT_FILENAME,
    SessionChunkStore,
    session_expires_at,
    wrap_key_to_file,
    write_note,
)
from scribe_desktop.transcription import SPEAKER_2, write_transcript  # noqa: E402
from scribe_desktop.ui import models  # noqa: E402
from test_note_pipeline import _NOW, PIPELINE_CONFIG, _resolve  # noqa: E402
from test_note_pipeline import _document as _pipeline_document  # noqa: E402
from test_ui_screens import _linked_context, _main_window  # noqa: E402

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI custody is Windows-only")


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _saved_note(session_id: str) -> GeneratedNote:
    document = _pipeline_document(session_id)
    draft = compose_draft(
        document, PIPELINE_CONFIG, ExtractiveNoteProvider(), clinician_speaker=SPEAKER_2
    )
    resolutions = [_resolve(proposal) for proposal in draft.note_proposals]
    return finalise_note(draft, resolutions, document, PIPELINE_CONFIG, created_at=_NOW)


def _write_session(
    directory: Path,
    crypto: SessionCrypto,
    *,
    linked: bool = False,
    note: bool = False,
    encounter: bool = True,
) -> None:
    session_id = directory.name
    if encounter:
        context = _linked_context() if linked else None
        consent = linked_consent(context) if context is not None else unlinked_consent()
        write_encounter_record(
            directory, crypto, session_id, EncounterRecord(consent=consent, context=context)
        )
    write_transcript(directory, crypto, _pipeline_document(session_id))
    if note:
        write_note(directory, crypto, _saved_note(session_id), PIPELINE_CONFIG)


def _unreviewed(root: Path, *, finished: bool = True, **kwargs: Any) -> Path:
    """A retired session on disk: a real DPAPI-wrapped key, a one-chunk
    audio store — sealed with its Finish footer, or (``finished=False``) left
    without one, as a crash-recovered store is — its consent record, its
    transcript and (optionally) a saved note."""
    directory = root / uuid.uuid4().hex
    directory.mkdir(parents=True)
    crypto = SessionCrypto()
    wrap_key_to_file(crypto, directory)
    store = SessionChunkStore.create(directory / AUDIO_FILENAME, crypto, directory.name)
    store.append_chunk(b"\x00" * 3200)
    if finished:
        store.finish()
    else:
        store.close()
    _write_session(directory, crypto, **kwargs)
    crypto.destroy()
    return directory


def _controller(root: Path) -> SessionController:
    return SessionController(MockCaptureBackend(), sessions_root=root)


def _read(directory: Path, crypto: SessionCrypto) -> str:
    return directory.name


# ---------------------------------------------------------------------------
# The controller: adopt_queued.
# ---------------------------------------------------------------------------


@windows_only
class TestAdoptQueued:
    def test_it_installs_the_session_queued_from_its_consent_record(
        self, tmp_path: Path
    ) -> None:
        directory = _unreviewed(tmp_path, linked=True)
        controller = _controller(tmp_path)
        session, value = controller.adopt_queued(directory, _read)
        assert value == directory.name
        assert session.session_id == directory.name
        assert session.state is SessionState.QUEUED
        context, expected = session.encounter_context, _linked_context()
        assert context is not None
        assert (context.clinic_id, context.treatment_note_id, context.patient_id) == (
            expected.clinic_id,
            expected.treatment_note_id,
            expected.patient_id,
        )
        assert session.consent.treatment_note_id == expected.treatment_note_id
        assert controller.session == session
        ref = controller.session_ref
        assert ref is not None and controller.resolve_session_ref(ref) == directory.name
        # D6 consumer 7: the live adopted session is protected from the sweep
        # and excluded from the Recovery listing (no second custody path).
        assert directory.name in controller.custody_protected_ids()
        listed = models.list_recoverable_sessions(tmp_path, controller.custody_protected_ids())
        assert listed == []

    def test_it_decrypts_the_consent_record_exactly_once(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        directory = _unreviewed(tmp_path, linked=True)
        real = session_module.read_encounter_record
        reads: list[str] = []

        def counting(*args: Any) -> Any:
            reads.append(args[2])
            return real(*args)

        monkeypatch.setattr(session_module, "read_encounter_record", counting)
        _controller(tmp_path).adopt_queued(directory, _read)
        assert reads == [directory.name]

    def test_the_adopted_session_is_the_live_path_through_complete(
        self, tmp_path: Path
    ) -> None:
        """Consumers 2 and 5: the lease and the scoped custody serve it, and
        Complete verifies the saved note against the transcript, deletes the
        key and forgets the reference."""
        directory = _unreviewed(tmp_path, note=True)
        controller = _controller(tmp_path)
        _session, opening = controller.adopt_queued(directory, models.read_for_review)
        assert opening.note is not None and opening.note.session_id == directory.name
        lease = controller.begin_generation()
        seen = controller.with_generation_custody(lease, lambda d, _c: d)
        assert seen == directory
        controller.end_generation(lease)
        ref = controller.session_ref
        assert ref is not None
        assert controller.complete().state is SessionState.WRITTEN
        assert not (directory / KEY_FILENAME).exists()
        assert controller.resolve_session_ref(ref) is None
        assert controller.session is None

    def test_it_keeps_the_reference_the_session_already_had(self, tmp_path: Path) -> None:
        """D2: a ref minted at Start survives retirement and adoption, so a
        panel or banner holding it still names this session."""
        controller = _controller(tmp_path)
        first = start_unlinked(controller)
        directory = tmp_path / first.session_id
        first_ref = controller.session_ref
        controller.finish()
        controller.mark_queued()
        crypto = session_module.unwrap_key_from_file(directory)
        write_transcript(directory, crypto, _pipeline_document(first.session_id))
        crypto.destroy()
        start_unlinked(controller)  # retires the first (queued) session
        controller.discard()
        assert first_ref is not None
        assert controller.resolve_session_ref(first_ref) == first.session_id
        session, _ = controller.adopt_queued(directory, _read)
        assert session.session_id == first.session_id
        assert controller.session_ref == first_ref

    def test_a_live_queued_session_is_retired_like_a_start_retires_it(
        self, tmp_path: Path
    ) -> None:
        first = _unreviewed(tmp_path)
        second = _unreviewed(tmp_path)
        controller = _controller(tmp_path)
        controller.adopt_queued(first, _read)
        first_ref = controller.session_ref
        session, _ = controller.adopt_queued(second, _read)
        assert controller.session == session and session.session_id == second.name
        # The retired one keeps its key on disk and its reference (D2).
        assert (first / KEY_FILENAME).is_file()
        assert first_ref is not None and controller.resolve_session_ref(first_ref) == first.name
        listed = models.list_recoverable_sessions(tmp_path, controller.custody_protected_ids())
        assert [info.session_id for info in listed] == [first.name]

    def test_refused_while_the_generation_lease_is_held(self, tmp_path: Path) -> None:
        first = _unreviewed(tmp_path)
        second = _unreviewed(tmp_path)
        controller = _controller(tmp_path)
        controller.adopt_queued(first, _read)
        controller.begin_generation()
        with pytest.raises(GenerationInProgressError, match="open for review"):
            controller.adopt_queued(second, _read)
        assert controller.session is not None and controller.session.session_id == first.name

    def test_refused_while_a_session_is_active(self, tmp_path: Path) -> None:
        directory = _unreviewed(tmp_path)
        controller = _controller(tmp_path)
        recording = start_unlinked(controller)
        with pytest.raises(SessionActivityError, match="single-active-session"):
            controller.adopt_queued(directory, _read)
        assert controller.session is not None
        assert controller.session.session_id == recording.session_id
        controller.discard()

    def test_refused_while_a_discard_holds_a_reservation(self, tmp_path: Path) -> None:
        directory = _unreviewed(tmp_path)
        controller = _controller(tmp_path)
        controller._custody_reservations[directory.name] = 1
        with pytest.raises(SessionActivityError, match="discard"):
            controller.adopt_queued(directory, _read)
        assert controller.session is None

    def test_refused_outside_its_root_and_for_the_live_session(self, tmp_path: Path) -> None:
        elsewhere = _unreviewed(tmp_path / "elsewhere")
        directory = _unreviewed(tmp_path / "root")
        controller = _controller(tmp_path / "root")
        with pytest.raises(SessionActivityError, match="not a session of this app"):
            controller.adopt_queued(elsewhere, _read)
        controller.adopt_queued(directory, _read)
        with pytest.raises(SessionActivityError, match="already open"):
            controller.adopt_queued(directory, _read)

    @pytest.mark.parametrize(
        "damage, reason",
        [
            ("transcript", "no_transcript"),
            ("encounter", "consent_unavailable"),
            ("key", "key_unavailable"),
        ],
    )
    def test_a_session_that_cannot_open_is_named_and_nothing_is_installed(
        self, tmp_path: Path, damage: str, reason: str
    ) -> None:
        live = _unreviewed(tmp_path)
        directory = _unreviewed(tmp_path)
        if damage == "key":
            (directory / KEY_FILENAME).write_bytes(b"")  # cryptographically dead
        elif damage == "encounter":
            (directory / ENCOUNTER_FILENAME).unlink()
        else:
            (directory / TRANSCRIPT_FILENAME).unlink()
        controller = _controller(tmp_path)
        controller.adopt_queued(live, _read)
        with pytest.raises(ReviewOpenRefused) as refused:
            controller.adopt_queued(directory, _read)
        assert refused.value.reason == reason
        assert controller.session is not None and controller.session.session_id == live.name

    def test_a_reader_failure_refuses_and_destroys_the_unwrapped_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        directory = _unreviewed(tmp_path)
        real = session_module.unwrap_key_from_file
        unwrapped: list[SessionCrypto] = []

        def capturing(*args: Any, **kwargs: Any) -> SessionCrypto:
            crypto = real(*args, **kwargs)
            unwrapped.append(crypto)
            return crypto

        monkeypatch.setattr(session_module, "unwrap_key_from_file", capturing)

        def failing(_d: Path, _c: SessionCrypto) -> None:
            raise models.ReviewReadError("note")

        controller = _controller(tmp_path)
        with pytest.raises(ReviewOpenRefused) as refused:
            controller.adopt_queued(directory, failing)
        assert refused.value.reason == "unreadable"
        assert isinstance(refused.value.__cause__, models.ReviewReadError)
        assert [crypto.destroyed for crypto in unwrapped] == [True]
        assert controller.session is None
        assert (directory / KEY_FILENAME).is_file()  # disk custody untouched


# ---------------------------------------------------------------------------
# The models layer.
# ---------------------------------------------------------------------------


class TestReadForReview:
    def _session(self, tmp_path: Path, **kwargs: Any) -> tuple[Path, SessionCrypto]:
        directory = tmp_path / uuid.uuid4().hex
        directory.mkdir()
        crypto = SessionCrypto()
        _write_session(directory, crypto, **kwargs)
        return directory, crypto

    def test_a_transcript_alone_opens_with_no_note(self, tmp_path: Path) -> None:
        directory, crypto = self._session(tmp_path)
        opening = models.read_for_review(directory, crypto)
        assert opening.note is None
        assert opening.document.session_id == directory.name

    def test_a_saved_note_opens_verified(self, tmp_path: Path) -> None:
        directory, crypto = self._session(tmp_path, note=True)
        opening = models.read_for_review(directory, crypto)
        assert opening.note == _saved_note(directory.name)

    def test_a_note_that_fails_verification_is_a_note_refusal(self, tmp_path: Path) -> None:
        directory, crypto = self._session(tmp_path, note=True)
        (directory / NOTE_FILENAME).write_bytes(crypto.encrypt(b"not a note"))
        with pytest.raises(models.ReviewReadError) as refused:
            models.read_for_review(directory, crypto)
        assert refused.value.kind == "note"
        assert "note" in models.review_refusal_line("unreadable", refused.value)
        assert "not replaced" in models.review_refusal_line("unreadable", refused.value)

    def test_an_unreadable_transcript_is_a_transcript_refusal(self, tmp_path: Path) -> None:
        directory, crypto = self._session(tmp_path)
        (directory / TRANSCRIPT_FILENAME).write_bytes(b"garbage")
        with pytest.raises(models.ReviewReadError) as refused:
            models.read_for_review(directory, crypto)
        assert refused.value.kind == "transcript"


class TestReviewCopy:
    @pytest.mark.parametrize(
        "reason", ["no_transcript", "key_unavailable", "consent_unavailable", "unreadable"]
    )
    def test_every_refusal_is_named(self, reason: str) -> None:
        line = models.review_refusal_line(reason)
        assert line.startswith("This recording cannot be opened for review: ")

    def test_the_saved_note_line_follows_the_config(self, tmp_path: Path) -> None:
        note = _saved_note("a" * 32)
        assert models.saved_note_line(note, lambda: PIPELINE_CONFIG) == models.SAVED_NOTE_LINE

        def other() -> Any:
            return PIPELINE_CONFIG.model_copy(update={"autofill_rules": ()})

        assert models.saved_note_line(note, other) == models.SAVED_NOTE_CONFIG_CHANGED_LINE

        def broken() -> Any:
            raise NoteConfigError("bad")

        assert models.saved_note_line(note, broken) == models.SAVED_NOTE_CONFIG_UNREADABLE_LINE

        def broken_install() -> Any:
            raise RuntimeError("shipped defaults unreadable")

        # Round 32 LOW-025: it runs after the adoption, so it never raises.
        assert (
            models.saved_note_line(note, broken_install)
            == models.SAVED_NOTE_CONFIG_UNREADABLE_LINE
        )

    def _info(self, session_id: str, expires_at: float | None) -> models.RecoverableSessionInfo:
        return models.RecoverableSessionInfo(
            session_id=session_id,
            directory=Path(session_id),
            created_at=None,
            store_finished=False,
            has_audio=False,
            has_transcript=True,
            has_note=False,
            has_encounter=True,
            expires_at=expires_at,
        )

    def test_the_two_hour_window(self) -> None:
        now = 1_000_000.0
        infos = [
            self._info("a" * 32, now + models.EXPIRY_WARNING_SECONDS - 1),
            self._info("b" * 32, now + models.EXPIRY_WARNING_SECONDS + 60),
            self._info("c" * 32, None),
        ]
        assert models.expiring_soon(infos, now) == ["a" * 32]
        assert "1 unreviewed recording expires" in models.expiry_warning_line(1)
        assert "2 unreviewed recordings expire" in models.expiry_warning_line(2)

    def test_rows_and_the_close_list_name_no_full_id(self) -> None:
        now = 1_000_000.0
        session_id = "d" * 32
        row = models.unreviewed_row_text(self._info(session_id, now + 3600), now)
        message = models.close_expiry_message([(session_id, now + 3600), ("e" * 32, None)], now)
        for text in (row, message):
            assert session_id not in text
            assert "d" * 8 in text
        assert "expiry unknown" in message
        assert "expiring now" in models.expiry_text(now - 1, now)

    def test_the_expiry_is_the_sweeps_own(self, tmp_path: Path) -> None:
        directory = tmp_path / uuid.uuid4().hex
        directory.mkdir()
        (directory / KEY_FILENAME).write_bytes(b"\x01" * 64)
        now = time.time()
        expires = session_expires_at(directory, now)
        assert abs(expires - (directory / KEY_FILENAME).stat().st_mtime - 24 * 3600) < 1


# ---------------------------------------------------------------------------
# The Recovery screen's Unreviewed section.
# ---------------------------------------------------------------------------


def _row_dir(root: Path, *, transcript: bool, note: bool = False) -> Path:
    """A stat-only row: a fake (non-dead) key blob plus marker files — the
    listing never decrypts, so their content is irrelevant here."""
    directory = root / uuid.uuid4().hex
    directory.mkdir(parents=True)
    (directory / KEY_FILENAME).write_bytes(b"\x01" * 64)
    if transcript:
        (directory / TRANSCRIPT_FILENAME).write_bytes(b"x")
    if note:
        (directory / NOTE_FILENAME).write_bytes(b"x")
    return directory


class TestUnreviewedSection:
    def _screen(self, root: Path, **kwargs: Any) -> Any:
        from scribe_desktop.ui.recovery import RecoveryScreen

        return RecoveryScreen(
            root, recovery_runner=lambda d: pytest.fail("not called"), **kwargs
        )

    def test_a_row_with_a_transcript_is_unreviewed_never_resumable(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        reviewable = _row_dir(tmp_path, transcript=True, note=True)
        _row_dir(tmp_path, transcript=False)
        screen = self._screen(tmp_path)
        assert screen.unreviewed_list.count() == 1
        assert screen.session_list.count() == 1
        text = screen.unreviewed_list.item(0).text()
        assert "note saved" in text and reviewable.name not in text
        assert [info.session_id for info in screen.unreviewed_infos()] == [reviewable.name]
        screen.deleteLater()

    def test_open_asks_the_window_and_the_blocks_apply(self, qapp: Any, tmp_path: Path) -> None:
        directory = _row_dir(tmp_path, transcript=True)
        screen = self._screen(tmp_path)
        asked: list[Any] = []
        screen.review_requested.connect(asked.append)
        assert not screen.open_button.isEnabled()  # nothing selected
        screen.unreviewed_list.setCurrentRow(0)
        assert screen.open_button.isEnabled() and screen.unreviewed_discard_button.isEnabled()
        for block in ("generation", "checkout"):
            if block == "generation":
                screen.set_generation_blocked(True)
            else:
                screen._protected.add("f" * 32)
                screen._update_controls()
            assert not screen.open_button.isEnabled(), block
            screen.on_open_for_review()
            assert asked == [], block
            screen.set_generation_blocked(False)
            screen._protected.clear()
            screen.refresh()
            screen.unreviewed_list.setCurrentRow(0)
        screen.open_button.click()
        assert [info.session_id for info in asked] == [directory.name]
        screen.deleteLater()

    def test_a_stale_row_is_refused_at_click_time(self, qapp: Any, tmp_path: Path) -> None:
        directory = _row_dir(tmp_path, transcript=True)
        protected: set[str] = set()
        screen = self._screen(tmp_path, active_ids_provider=lambda: frozenset(protected))
        asked: list[Any] = []
        screen.review_requested.connect(asked.append)
        screen.unreviewed_list.setCurrentRow(0)
        protected.add(directory.name)  # became live / reserved since the listing
        screen.on_open_for_review()
        assert asked == []
        assert screen.unreviewed_list.count() == 0  # refreshed away
        screen.deleteLater()

    def test_discard_removes_the_row_and_says_so(self, qapp: Any, tmp_path: Path) -> None:
        directory = _row_dir(tmp_path, transcript=True)
        screen = self._screen(tmp_path)
        removed: list[str] = []
        screen.session_removed.connect(removed.append)
        screen.unreviewed_list.setCurrentRow(0)
        screen.unreviewed_discard_button.click()
        assert removed == [directory.name]
        assert not (directory / KEY_FILENAME).exists()
        assert screen.unreviewed_list.count() == 0
        screen.deleteLater()

    def test_the_expiry_warning_shows_and_cues_once(self, qapp: Any, tmp_path: Path) -> None:
        directory = _row_dir(tmp_path, transcript=True)
        mtime = (directory / KEY_FILENAME).stat().st_mtime
        # 23 h after the key was written: inside the 2-hour window.
        clock = [mtime + 23 * 3600]
        screen = self._screen(tmp_path, clock=lambda: clock[0])
        cues: list[str] = []
        screen.expiry_warning.connect(cues.append)
        assert screen.expiry_label.isVisibleTo(screen)
        screen.refresh()  # the constructor's listing already counted it
        assert cues == []
        screen._warned.clear()
        screen.refresh()
        assert cues == [models.expiry_warning_line(1)]
        screen.refresh()
        assert len(cues) == 1  # once per session entering the window
        clock[0] = mtime + 3600  # well outside the window
        screen.refresh()
        assert not screen.expiry_label.isVisibleTo(screen)
        screen.deleteLater()


# ---------------------------------------------------------------------------
# The main window: Open for review, end to end with the real controller.
# ---------------------------------------------------------------------------


def _close(window: Any) -> None:
    """Close twice: the first close may be the on-close expiry list."""
    window.close()
    window.close()


def _open_row(window: Any, session_id: str) -> None:
    screen = window.recovery_screen
    screen.refresh()
    from PySide6.QtCore import Qt

    for row in range(screen.unreviewed_list.count()):
        info = screen.unreviewed_list.item(row).data(Qt.ItemDataRole.UserRole)
        if info.session_id == session_id:
            screen.unreviewed_list.setCurrentRow(row)
            screen.open_button.click()
            return
    pytest.fail("row not listed")


@windows_only
class TestOpenForReview:
    def test_a_transcript_opens_with_generation_on_the_live_path(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        directory = _unreviewed(tmp_path)
        controller = _controller(tmp_path)
        window = _main_window(tmp_path, controller)
        _open_row(window, directory.name)
        session = controller.session
        assert session is not None and session.session_id == directory.name
        assert session.state is SessionState.QUEUED
        assert window.tabs.currentWidget() is window.transcript_screen
        assert window.transcript_screen.generate_box.isVisibleTo(window.transcript_screen)
        assert window.transcript_screen.generate_button.text() == models.GENERATE_NOTE_LABEL
        assert window._transcript_source == "live"
        assert window.recovery_screen.unreviewed_list.count() == 0  # live now, not listed
        assert window.recovery_screen.protected_session_ids() == frozenset()
        window.transcript_screen.on_discard()
        assert controller.session is None
        assert not (directory / KEY_FILENAME).exists()
        _close(window)

    def test_a_saved_note_opens_as_saved_with_copy_and_regenerate(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        directory = _unreviewed(tmp_path, note=True)
        controller = _controller(tmp_path)
        window = _main_window(tmp_path, controller)
        _open_row(window, directory.name)
        note_screen = window.note_screen
        assert window.tabs.currentWidget() is note_screen
        assert note_screen.showing_saved_note
        assert note_screen.note_body.toPlainText() == models.format_note_body(
            _saved_note(directory.name)
        )
        assert note_screen.copy_button.isEnabled() is models.COPY_TO_CLINIKO_ENABLED
        assert not note_screen.save_button.isEnabled()
        assert not note_screen.cancel_button.isEnabled()
        assert not note_screen.is_busy
        transcript = window.transcript_screen
        assert transcript.generate_button.text() == models.REGENERATE_NOTE_LABEL
        # The saved note counts for Complete exactly as after a Save.
        assert transcript.complete_button.isEnabled()
        transcript.on_complete()
        assert controller.session is None
        assert not (directory / KEY_FILENAME).exists()
        _close(window)

    @pytest.mark.parametrize("finished", [False, True], ids=["unfinished", "finished"])
    def test_an_unfinished_store_keeps_its_warning_on_the_row_and_when_opened(
        self, qapp: Any, tmp_path: Path, finished: bool
    ) -> None:
        """Codex round 34 PR-MED-190: a crash-recovered store with no Finish
        footer carries the binding Step-10 warning on its Unreviewed row, on
        that row's selection and on the reopened transcript; a sealed one
        carries none of them."""
        directory = _unreviewed(tmp_path, finished=finished)
        controller = _controller(tmp_path)
        window = _main_window(tmp_path, controller)
        screen = window.recovery_screen
        screen.refresh()
        assert ("did not finish cleanly" in screen.unreviewed_list.item(0).text()) is not finished
        screen.unreviewed_list.setCurrentRow(0)
        assert screen.warning_label.isVisibleTo(screen) is not finished
        _open_row(window, directory.name)
        label = window.transcript_screen.warning_label
        assert label.isVisibleTo(window.transcript_screen) is not finished
        if not finished:
            assert label.text() == models.UNFINISHED_STORE_WARNING
        window.transcript_screen.on_discard()
        assert controller.session is None
        _close(window)

    def test_delete_note_and_complete_from_the_saved_view(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        directory = _unreviewed(tmp_path, note=True)
        controller = _controller(tmp_path)
        window = _main_window(tmp_path, controller)
        _open_row(window, directory.name)
        assert window.note_screen.abandon_button.isEnabled()
        window.note_screen.abandon()
        assert controller.session is None
        assert not (directory / NOTE_FILENAME).exists()
        assert not (directory / KEY_FILENAME).exists()
        _close(window)

    def test_a_note_that_fails_verification_is_refused_on_the_row(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        directory = _unreviewed(tmp_path, note=True)
        damaged = (directory / NOTE_FILENAME).read_bytes()[:-4] + b"\x00\x00\x00\x00"
        (directory / NOTE_FILENAME).write_bytes(damaged)
        controller = _controller(tmp_path)
        window = _main_window(tmp_path, controller)
        _open_row(window, directory.name)
        assert controller.session is None  # nothing adopted
        message = window.recovery_screen.message_label.text()
        assert "saved note could not be verified" in message
        assert (directory / NOTE_FILENAME).read_bytes() == damaged  # never rewritten
        assert window.recovery_screen.unreviewed_list.count() == 1
        _close(window)

    def test_a_missing_consent_record_is_refused_never_fabricated(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        directory = _unreviewed(tmp_path, encounter=False)
        controller = _controller(tmp_path)
        window = _main_window(tmp_path, controller)
        _open_row(window, directory.name)
        assert controller.session is None
        assert "consent record" in window.recovery_screen.message_label.text()
        _close(window)

    def test_the_previous_queued_session_is_retired_into_the_index(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        first = _unreviewed(tmp_path, linked=True)
        second = _unreviewed(tmp_path)
        controller = _controller(tmp_path)
        window = _main_window(tmp_path, controller)
        _open_row(window, first.name)
        assert first.name not in window.reminders  # in review, not waiting
        _open_row(window, second.name)
        assert controller.session is not None and controller.session.session_id == second.name
        assert first.name in window.reminders  # D6: retired, waiting again
        assert [info.session_id for info in window.recovery_screen.unreviewed_infos()] == [
            first.name
        ]
        _open_row(window, first.name)
        assert first.name not in window.reminders
        _close(window)

    def test_refused_while_a_note_review_holds_the_lease(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        first = _unreviewed(tmp_path)
        second = _unreviewed(tmp_path)
        controller = _controller(tmp_path)
        window = _main_window(tmp_path, controller)
        _open_row(window, first.name)
        lease = controller.begin_generation()
        window.recovery_screen.set_generation_blocked(False)  # a stale enabled row
        window._on_review_requested(
            next(
                info
                for info in models.list_recoverable_sessions(tmp_path)
                if info.session_id == second.name
            )
        )
        assert controller.session is not None and controller.session.session_id == first.name
        assert "cannot be opened for review now" in window.recovery_screen.message_label.text()
        controller.end_generation(lease)
        _close(window)

    def test_an_adopted_session_is_never_decrypted_twice_and_writes_through_live(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import scribe_desktop.ui.main_window as main_window_mod

        directory = _unreviewed(tmp_path, linked=True)
        controller = _controller(tmp_path)
        window = _main_window(tmp_path, controller)
        monkeypatch.setattr(
            main_window_mod,
            "read_encounter_record",
            lambda *a: pytest.fail("the adopted session's record was decrypted again"),
        )
        _open_row(window, directory.name)
        assert window._checkout.adopted and window._checkout.session_id == directory.name
        assert window.transcript_screen.link_label.text() != ""
        assert window.recovered_writeback_target() is None  # the live entry governs
        _close(window)

    def test_a_start_retires_the_adopted_session_and_ends_its_checkout(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        directory = _unreviewed(tmp_path, linked=True)
        controller = _controller(tmp_path)
        window = _main_window(tmp_path, controller)
        _open_row(window, directory.name)
        # What the Session screen's `_start` does (pinned in TestStartAtQueued):
        # read the tracked session, start, announce the retirement and the start.
        previous = controller.session
        start_unlinked(controller)
        window.session_screen.session_retired.emit(previous)
        window.session_screen.session_started.emit()
        assert controller.state is SessionState.RECORDING
        assert window._checkout.session_id is None
        assert directory.name in window.reminders
        assert window.note_screen.current_note() is None
        controller.discard()
        _close(window)


@windows_only
class TestReconstruction:
    """Task 5.5 (D6): app start rebuilds the reminder index — the one
    start-up decrypt of ``encounter.enc``, once per Unreviewed session."""

    def test_app_start_decrypts_each_record_once_and_indexes_linked_ones(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        older = _unreviewed(tmp_path, linked=True)
        newer = _unreviewed(tmp_path, linked=True)
        unlinked = _unreviewed(tmp_path)
        os.utime(older / KEY_FILENAME, (time.time() - 3600, time.time() - 3600))
        no_transcript = _row_dir(tmp_path, transcript=False)
        controller = _controller(tmp_path)
        window = _main_window(tmp_path, controller)
        real = models.read_encounter_record
        reads: list[str] = []

        def counting(*args: Any) -> Any:
            reads.append(args[2])
            return real(*args)

        monkeypatch.setattr(models, "read_encounter_record", counting)
        window.reconstruct_reminders()
        assert sorted(reads) == sorted([older.name, newer.name, unlinked.name])
        assert no_transcript.name not in reads
        context = _linked_context()
        assert window.reminders.sessions_for(context.clinic_id, context.treatment_note_id) == (
            newer.name,
            older.name,
        )
        assert unlinked.name not in window.reminders
        for directory in (older, newer):
            ref = controller.session_ref_for(directory.name)
            assert ref is not None and controller.resolve_session_ref(ref) == directory.name
        # The listing, the periodic refresh and the sweep never decrypt again.
        for _ in range(3):
            window.recovery_screen.refresh()
        window.prune_reminders()
        assert len(reads) == 3
        _close(window)

    def test_an_unreadable_record_is_skipped_not_fatal(self, qapp: Any, tmp_path: Path) -> None:
        damaged = _unreviewed(tmp_path, linked=True)
        (damaged / ENCOUNTER_FILENAME).write_bytes(b"not a record")
        window = _main_window(tmp_path, _controller(tmp_path))
        window.reconstruct_reminders()
        assert len(window.reminders) == 0
        assert window.recovery_screen.unreviewed_list.count() == 1  # still reviewable (named)
        _close(window)

    def test_open_unreviewed_opens_exactly_that_session(self, qapp: Any, tmp_path: Path) -> None:
        first = _unreviewed(tmp_path, linked=True)
        second = _unreviewed(tmp_path, linked=True)
        controller = _controller(tmp_path)
        window = _main_window(tmp_path, controller)
        window.reconstruct_reminders()
        assert window.open_unreviewed(uuid.uuid4().hex) == "session_changed"
        assert controller.session is None
        assert window.open_unreviewed(first.name) is None
        assert controller.session is not None and controller.session.session_id == first.name
        assert first.name not in window.reminders and second.name in window.reminders
        assert window.tabs.currentWidget() is window.transcript_screen
        _close(window)

    def test_the_chrome_route_keeps_the_unfinished_store_warning(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Codex round 34 PR-MED-190's class: ``open_unreviewed`` (the
        banner's route) shares the adoption display, warning included."""
        directory = _unreviewed(tmp_path, linked=True, finished=False)
        controller = _controller(tmp_path)
        window = _main_window(tmp_path, controller)
        window.reconstruct_reminders()
        assert window.open_unreviewed(directory.name) is None
        label = window.transcript_screen.warning_label
        assert label.isVisibleTo(window.transcript_screen)
        assert label.text() == models.UNFINISHED_STORE_WARNING
        window.transcript_screen.on_discard()
        _close(window)

    def test_an_open_refused_by_the_controller_is_cannot_open(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        first = _unreviewed(tmp_path, linked=True)
        second = _unreviewed(tmp_path, linked=True)
        controller = _controller(tmp_path)
        window = _main_window(tmp_path, controller)
        window.reconstruct_reminders()
        assert window.open_unreviewed(first.name) is None
        lease = controller.begin_generation()
        assert window.open_unreviewed(second.name) == "cannot_open"
        assert controller.session is not None and controller.session.session_id == first.name
        assert window.tabs.currentWidget() is window.recovery_screen  # the refusal, named
        controller.end_generation(lease)
        _close(window)

    def test_refused_while_a_draft_write_holds_the_live_session(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Draft-write plan D9 (Task 4.1): "Open for review" would retire the
        session a draft write holds — refused on ``is_writing`` with the
        write-in-flight line before the controller is asked; the writing
        clinic is the one the Clinics tab's Replace key refuses; after the
        release the open proceeds."""
        first = _unreviewed(tmp_path, linked=True)
        second = _unreviewed(tmp_path, linked=True)
        controller = _controller(tmp_path)
        window = _main_window(tmp_path, controller)
        window.reconstruct_reminders()
        assert window.open_unreviewed(first.name) is None
        assert not window.is_writing and window._writing_clinic() is None
        # The window's own refusal must come BEFORE the controller is asked
        # (the controller refuses too, with the same line — round 14 LOW).
        real_adopt = controller.adopt_queued
        asked: list[str] = []

        def spy(directory: Path, reader: Any) -> Any:
            asked.append(directory.name)
            return real_adopt(directory, reader)

        monkeypatch.setattr(controller, "adopt_queued", spy)
        reservation = controller.reserve_write(first.name)
        assert window.is_writing
        live = controller.session
        assert live is not None and live.encounter_context is not None
        assert window._writing_clinic() == live.encounter_context.clinic_id
        # Round 15: the Clinics tab really asks the WINDOW (its Replace-key
        # refusal reads this provider).
        assert window.clinics_screen._writing_clinic() == live.encounter_context.clinic_id
        assert window.open_unreviewed(second.name) == "cannot_open"
        assert asked == []
        assert window.recovery_screen.message_label.text() == models.write_line(
            "write_in_flight"
        )
        assert controller.session is not None and controller.session.session_id == first.name
        reservation.release()
        assert not window.is_writing and window._writing_clinic() is None
        assert window.clinics_screen._writing_clinic() is None
        assert window.open_unreviewed(second.name) is None
        assert asked == [second.name]
        assert controller.session is not None and controller.session.session_id == second.name
        _close(window)

    def test_refused_while_a_recovery_is_transcribing(self, qapp: Any, tmp_path: Path) -> None:
        """Round 32 LOW-024: the Chrome route honours the Recovery screen's
        own block — the resume would land on the adopted session's view."""
        directory = _unreviewed(tmp_path, linked=True)
        controller = _controller(tmp_path)
        window = _main_window(tmp_path, controller)
        window.reconstruct_reminders()
        window.recovery_screen._busy = True  # a resume-processing run in flight
        assert window.open_unreviewed(directory.name) == "cannot_open"
        assert controller.session is None
        assert (
            window.recovery_screen.message_label.text()
            == models.REVIEW_OPEN_RECOVERY_BUSY_LINE
        )
        window.recovery_screen._busy = False
        _close(window)

    def test_restart_banner_then_open_review_opens_the_right_session(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Task 5.5's verification: after a restart the banner names the
        indexed session, and its "Open for review" opens exactly it."""
        from encounter_fakes import make_registry
        from scribe_desktop.protocol import make_pipe_envelope
        from test_ui_bridge import FakeSender
        from test_ui_screens import _process_until

        other = _unreviewed(tmp_path, linked=True)
        target = _unreviewed(tmp_path, linked=True)
        os.utime(other / KEY_FILENAME, (time.time() - 3600, time.time() - 3600))
        registry_root = tmp_path / "registry"
        registry_root.mkdir()
        controller = _controller(tmp_path)
        window = _main_window(
            tmp_path, controller, clinic_registry=make_registry(registry_root)
        )
        window.reconstruct_reminders()  # the restart's reconstruction
        bridge = window.attach_chrome_link()
        sender = FakeSender()
        bridge.attach(sender)
        bridge.connected(1)
        qapp.processEvents()
        context = _linked_context()
        bridge.message(
            1,
            make_pipe_envelope(
                "context",
                payload={
                    "seq": 1,
                    "tab_id": 5,
                    "window_id": 1,
                    "focused": True,
                    "page": "note",
                    "host": context.clinic_host,
                    "patient_id": context.patient_id,
                    "note_id": context.treatment_note_id,
                },
            ),
        )
        assert _process_until(qapp, lambda: not bridge.is_busy)
        qapp.processEvents()
        banner = sender.last.banner
        assert banner is not None and banner.count == 2
        assert banner.session_ref == controller.session_ref_for(target.name)  # newest
        bridge.message(
            1,
            make_pipe_envelope(
                "command",
                payload={
                    "action": "open_review",
                    "state_rev": bridge.state_rev,
                    "session_ref": banner.session_ref,
                },
            ),
        )
        qapp.processEvents()
        qapp.processEvents()
        assert controller.session is not None and controller.session.session_id == target.name
        assert sender.last.last_refusal is None
        assert _process_until(qapp, lambda: not bridge.is_busy and not window.is_reverifying)
        _close(window)


@windows_only
class TestCloseList:
    def test_the_first_close_lists_expiries_and_the_second_quits(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        from PySide6.QtGui import QCloseEvent

        directory = _unreviewed(tmp_path)
        window = _main_window(tmp_path, _controller(tmp_path))
        event = QCloseEvent()
        window.closeEvent(event)
        assert not event.isAccepted()
        message = window.statusBar().currentMessage()
        assert directory.name[:8] in message and directory.name not in message
        assert "Close again" in message
        assert window.tabs.currentWidget() is window.recovery_screen
        event2 = QCloseEvent()
        window.closeEvent(event2)
        assert event2.isAccepted()

    def test_the_live_queued_session_is_listed_too(self, qapp: Any, tmp_path: Path) -> None:
        from PySide6.QtGui import QCloseEvent

        directory = _unreviewed(tmp_path)
        controller = _controller(tmp_path)
        window = _main_window(tmp_path, controller)
        _open_row(window, directory.name)
        event = QCloseEvent()
        window.closeEvent(event)
        assert not event.isAccepted()
        assert directory.name[:8] in window.statusBar().currentMessage()
        _close(window)

    def test_an_open_recovered_checkout_is_listed_too(self, qapp: Any, tmp_path: Path) -> None:
        """Round 32 LOW-027: a checked-out recovered session is excluded from
        the listing as protected, and still named on close."""
        from PySide6.QtGui import QCloseEvent

        directory = _unreviewed(tmp_path)
        window = _main_window(tmp_path, _controller(tmp_path))
        window.recovery_screen._protected.add(directory.name)  # its view is open
        window._transcript_source = directory.name
        event = QCloseEvent()
        window.closeEvent(event)
        assert not event.isAccepted()
        assert directory.name[:8] in window.statusBar().currentMessage()
        window._transcript_source = None
        window.recovery_screen.release_checkout(directory.name)
        _close(window)

    def test_nothing_unreviewed_closes_at_once(self, qapp: Any, tmp_path: Path) -> None:
        from PySide6.QtGui import QCloseEvent

        window = _main_window(tmp_path, _controller(tmp_path))
        event = QCloseEvent()
        window.closeEvent(event)
        assert event.isAccepted()
