"""Validation-pass plan Phase 4 (D9, decision 0.6 (a); Tasks 4.1 and 4.2):
the clinician's "Remove lines N-end from this recording" on the Transcript
tab — the controller's ONE trim operation and its custody order (the
no-audio marker, then ``generated.enc``, then ``write_transcript``), the
store primitives it orders, the shortened document, every Complete path
keeping no audio once the marker is there (or cannot be ruled out), the
trimmed transcript surviving a restart, and the screen's line, action,
confirmation and refusals.

Synthetic transcripts only (the held-out fixtures' ``build_document``). No
real DPAPI: the session key and the Past-sessions entry keys go through
fakes that write the raw key behind a marker, as ``test_past_sessions.py``
does. Offscreen Qt; no clipboard, no hotkey, no model."""

from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from fixtures.heldout_transcripts import Turn, build_document  # noqa: E402
from scribe_desktop import session as session_module  # noqa: E402
from scribe_desktop import session_store, transcription  # noqa: E402
from scribe_desktop.audio_capture import MockCaptureBackend  # noqa: E402
from scribe_desktop.draft_write import WriteRecord  # noqa: E402
from scribe_desktop.encounter import (  # noqa: E402
    EncounterRecord,
    development_consent,
    unlinked_consent,
    write_encounter_record,
)
from scribe_desktop.note import GeneratedNote, digest_bytes, finalise_note  # noqa: E402
from scribe_desktop.note import transcript_digest as note_transcript_digest  # noqa: E402
from scribe_desktop.note_config import (  # noqa: E402
    NoteConfig,
    load_note_config,
    next_patient_boundary,
)
from scribe_desktop.past_sessions import PENDING_FILENAME, PastSessionStore  # noqa: E402
from scribe_desktop.secure_storage import SessionCrypto  # noqa: E402
from scribe_desktop.session import (  # noqa: E402
    GenerationInProgressError,
    RecordingSession,
    SessionActivityError,
    SessionController,
    SessionState,
    WriteInFlightError,
    store_write_record,
)
from scribe_desktop.session_mode import SessionMode  # noqa: E402
from scribe_desktop.session_store import (  # noqa: E402
    AUDIO_FILENAME,
    GENERATED_FILENAME,
    KEY_FILENAME,
    NO_AUDIO_MARKER_FILENAME,
    NOTE_FILENAME,
    TRANSCRIPT_FILENAME,
    GeneratedRecord,
    SessionChunkStore,
    StoreWriteError,
    artifact_state,
    no_audio_marker_state,
    remove_generated,
    write_generated,
    write_no_audio_marker,
)
from scribe_desktop.speaker_eval import CLINICIAN_LABEL  # noqa: E402
from scribe_desktop.transcription import (  # noqa: E402
    TranscriptDocument,
    read_transcript,
    transcript_before,
    write_transcript,
)
from scribe_desktop.ui import models  # noqa: E402

REPO: Final = Path(__file__).resolve().parents[2]
VALIDATION_CONFIG: Final = REPO / "validation" / "config"
NOW: Final = datetime(2026, 10, 13, 9, 0, tzinfo=UTC)

_C: Final = CLINICIAN_LABEL
_P: Final = "patient"
_N: Final = "next_patient"
# The shapes of ``test_consultation_boundary.py``: a routed patient line (the
# head-case guard's content), a closing, then a greeting at segment 3 — so
# line 4 onward is the possible next patient's.
_TURNS: Final = (
    Turn(_P, "I'm coming in with a sore right shoulder."),
    Turn(_C, "I'll do some massage."),
    Turn(_C, "See you next week."),
    Turn(_C, "Hello, come in."),
    Turn(_N, "My hip is sore again."),
)
_BOUNDARY: Final = 3
_TAIL_WORD: Final = "hip"
_PCM: Final = (b"\x01\x02" * 800, b"\x03\x04" * 500)
_SESSION_KEY: Final = b"FAKE-SESSION-KEY:"
_ENTRY_KEY: Final = b"FAKE-ENTRY-KEY:"


@pytest.fixture(scope="module")
def config() -> NoteConfig:
    """The validation config over the shipped cues (the boundary's cues)."""
    return load_note_config(VALIDATION_CONFIG)


@pytest.fixture(autouse=True)
def fake_session_custody(monkeypatch: pytest.MonkeyPatch) -> None:
    """The adopted session's key comes from the fake blob, never DPAPI."""
    monkeypatch.setattr(session_module, "unwrap_key_from_file", _fake_session_unwrap)


def _fake_session_unwrap(directory: Path) -> SessionCrypto:
    blob = (directory / KEY_FILENAME).read_bytes()
    assert blob.startswith(_SESSION_KEY)
    return SessionCrypto.from_key(blob[len(_SESSION_KEY) :])


def _fake_entry_wrap(crypto: SessionCrypto, directory: Path) -> None:
    (directory / KEY_FILENAME).write_bytes(_ENTRY_KEY + crypto.export_key())


def _fake_entry_unwrap(directory: Path) -> SessionCrypto:
    blob = (directory / KEY_FILENAME).read_bytes()
    assert blob.startswith(_ENTRY_KEY)
    return SessionCrypto.from_key(blob[len(_ENTRY_KEY) :])


def _document(session_id: str, turns: tuple[Turn, ...] = _TURNS) -> TranscriptDocument:
    return build_document(turns).model_copy(update={"session_id": session_id})


def _generated_record(session_id: str) -> GeneratedRecord:
    """An earlier generation's body that quotes the tail (PR-HIGH-001)."""
    return GeneratedRecord(
        session_id=session_id,
        created_at=NOW,
        provider_name="extractive-v1",
        style="verbatim",
        generated_text=f"Subjective: my {_TAIL_WORD} is sore again.",
    )


def _saved_note_plain(document: TranscriptDocument) -> bytes:
    """A saved-note plaintext Complete verifies against ``document``."""
    return GeneratedNote(
        session_id=document.session_id,
        created_at=NOW,
        template_profile_id="clinic-a",
        provider_name="extractive-v1",
        transcript_digest=note_transcript_digest(document),
        config_digest=digest_bytes(b"config"),
    ).to_bytes()


def _session(
    root: Path,
    *,
    kept: bool = True,
    generated: bool = True,
    note: bool = False,
    mode: SessionMode = SessionMode.NORMAL,
    turns: tuple[Turn, ...] = _TURNS,
) -> tuple[Path, SessionCrypto]:
    """A queued session on disk: the fake key blob, a finished audio store,
    its consent record (with the development consent when ``kept``), the
    transcript, an earlier generation's body and (optionally) a saved note."""
    session_id = uuid.uuid4().hex
    directory = root / session_id
    directory.mkdir(parents=True)
    crypto = SessionCrypto()
    (directory / KEY_FILENAME).write_bytes(_SESSION_KEY + crypto.export_key())
    store = SessionChunkStore.create(directory / AUDIO_FILENAME, crypto, session_id)
    for chunk in _PCM:
        store.append_chunk(chunk)
    store.finish()
    store.close()
    write_encounter_record(
        directory,
        crypto,
        session_id,
        EncounterRecord(
            consent=unlinked_consent(),
            context=None,
            mode=mode,
            development_consent=development_consent(NOW) if kept else None,
        ),
    )
    document = _document(session_id, turns)
    write_transcript(directory, crypto, document)
    if generated:
        write_generated(directory, crypto, _generated_record(session_id))
    if note:
        (directory / NOTE_FILENAME).write_bytes(crypto.encrypt(_saved_note_plain(document)))
    return directory, crypto


class _Audit:
    """The audit seam: what each Complete recorded (the facts only)."""

    def __init__(self) -> None:
        self.completions: list[tuple[str, Any]] = []

    def record_completion(self, session_id: str, facts: Any, **_kwargs: Any) -> bool:
        self.completions.append((session_id, facts))
        return True

    def record_deletion(self, *_args: Any, **_kwargs: Any) -> bool:
        return True


class _Harness:
    def __init__(self, tmp_path: Path) -> None:
        self.root = tmp_path / "sessions"
        self.store = PastSessionStore(
            tmp_path / "past_sessions",
            clock=lambda: NOW,
            wrap_key=_fake_entry_wrap,
            unwrap_key=_fake_entry_unwrap,
        )
        self.audit = _Audit()
        self.controller = SessionController(
            MockCaptureBackend(),
            sessions_root=self.root,
            audit=self.audit,  # type: ignore[arg-type]
            past_sessions=self.store,
        )

    def adopt(self, **kwargs: Any) -> tuple[Path, str]:
        directory, crypto = _session(self.root, **kwargs)
        crypto.destroy()
        self.controller.adopt_queued(directory, lambda _d, _c: None)
        return directory, directory.name

    def trim(self, session_id: str, config: NoteConfig) -> TranscriptDocument:
        return self.controller.trim_transcript(
            session_id,
            boundary=_BOUNDARY,
            boundary_of=lambda document: next_patient_boundary(document, config),
        )


def _files(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in directory.iterdir()}


def _transcript_on_disk(directory: Path) -> TranscriptDocument:
    return read_transcript(directory, _fake_session_unwrap(directory))


def _words(document: TranscriptDocument) -> list[str]:
    return [
        word.word_text.lower().strip(".,")
        for segment in document.transcript_segments
        for word in segment.transcript_words
    ]


# --- the shortened document ----------------------------------------------------------


class TestTranscriptBefore:
    def test_it_keeps_the_segments_before_the_boundary_and_every_other_field(self) -> None:
        document = _document("a" * 32)
        trimmed = transcript_before(document, _BOUNDARY)
        assert trimmed.transcript_segments == document.transcript_segments[:_BOUNDARY]
        assert trimmed.model_dump(exclude={"transcript_segments"}) == document.model_dump(
            exclude={"transcript_segments"}
        )

    @pytest.mark.parametrize("boundary", [-1, 0, len(_TURNS), len(_TURNS) + 1])
    def test_a_boundary_that_keeps_or_removes_nothing_is_refused(self, boundary: int) -> None:
        with pytest.raises(ValueError, match="not inside the transcript"):
            transcript_before(_document("a" * 32), boundary)

    def _attributed(self, speaker: str) -> TranscriptDocument:
        return TranscriptDocument.model_validate(
            {
                **_document("a" * 32).model_dump(),
                "enrolled_speaker": speaker,
                "enrolment_similarity": 0.81,
                "speaker_model_id": "wespeaker-test",
            }
        )

    def test_the_attribution_stays_while_its_speaker_has_text(self) -> None:
        trimmed = transcript_before(self._attributed(_C), _BOUNDARY)
        assert (trimmed.enrolled_speaker, trimmed.enrolment_similarity) == (_C, 0.81)
        assert trimmed.speaker_model_id == "wespeaker-test"

    def test_the_attribution_goes_all_together_with_its_speakers_last_line(self) -> None:
        """The document's own rule: an enrolled speaker with no line left
        would be refused at construction, so its three fields are dropped."""
        trimmed = transcript_before(self._attributed(_N), _BOUNDARY)
        assert (trimmed.enrolled_speaker, trimmed.enrolment_similarity) == (None, None)
        assert trimmed.speaker_model_id is None


# --- the store primitives ------------------------------------------------------------


class TestStorePrimitives:
    def test_the_marker_is_written_read_back_and_content_free(self, tmp_path: Path) -> None:
        assert no_audio_marker_state(tmp_path) is False
        write_no_audio_marker(tmp_path)
        assert no_audio_marker_state(tmp_path) is True
        blob = (tmp_path / NO_AUDIO_MARKER_FILENAME).read_bytes()
        assert blob == session_store._NO_AUDIO_MARKER  # noqa: SLF001 - the fixed bytes
        assert tmp_path.name.encode() not in blob

    def test_a_marker_that_does_not_read_back_is_a_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        real = session_store.atomic_write_bytes

        def other_bytes(path: Path, blob: bytes, *, error_label: str) -> None:
            real(path, b"something else", error_label=error_label)

        monkeypatch.setattr(session_store, "atomic_write_bytes", other_bytes)
        with pytest.raises(StoreWriteError, match="did not read back"):
            write_no_audio_marker(tmp_path)
        # Whatever it holds, a file of that name counts as the marker.
        assert no_audio_marker_state(tmp_path) is True

    def test_an_unreadable_status_is_undetermined_never_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        real = session_store.os.lstat

        def denied(path: Any, *args: Any, **kwargs: Any) -> Any:
            if Path(path).name == NO_AUDIO_MARKER_FILENAME:
                raise PermissionError("access denied")
            return real(path, *args, **kwargs)

        monkeypatch.setattr(session_store.os, "lstat", denied)
        assert no_audio_marker_state(tmp_path) is None
        assert artifact_state(tmp_path, NO_AUDIO_MARKER_FILENAME) is None

    def test_the_generated_note_is_removed_and_its_absence_confirmed(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / GENERATED_FILENAME).write_bytes(b"x")
        remove_generated(tmp_path)
        assert artifact_state(tmp_path, GENERATED_FILENAME) is False
        remove_generated(tmp_path)  # none is fine

    def test_a_removal_that_fails_or_cannot_be_confirmed_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / GENERATED_FILENAME).write_bytes(b"x")
        monkeypatch.setattr(session_store, "artifact_state", lambda _d, _f: None)
        with pytest.raises(StoreWriteError, match="not confirmed"):
            remove_generated(tmp_path)
        monkeypatch.undo()
        _deny_unlink(monkeypatch)
        (tmp_path / GENERATED_FILENAME).write_bytes(b"x")
        with pytest.raises(StoreWriteError, match="not removable"):
            remove_generated(tmp_path)


def _deny_unlink(monkeypatch: pytest.MonkeyPatch) -> None:
    real = Path.unlink

    def unlink(self: Path, missing_ok: bool = False) -> None:
        if self.name == GENERATED_FILENAME:
            raise PermissionError("access denied")
        real(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", unlink)


# --- the controller's one operation (Task 4.1; PR-HIGH-001 / PR-HIGH-002) -----------


class TestTrimTranscript:
    def test_the_trim_writes_the_marker_removes_the_generated_note_and_shortens(
        self, tmp_path: Path, config: NoteConfig
    ) -> None:
        harness = _Harness(tmp_path)
        directory, session_id = harness.adopt()
        assert next_patient_boundary(_transcript_on_disk(directory), config) == _BOUNDARY
        trimmed = harness.trim(session_id, config)
        assert len(trimmed.transcript_segments) == _BOUNDARY
        assert _transcript_on_disk(directory) == trimmed
        assert _TAIL_WORD not in _words(trimmed)
        assert no_audio_marker_state(directory) is True
        assert artifact_state(directory, GENERATED_FILENAME) is False
        # The session stays the live QUEUED one; nothing else changed.
        assert harness.controller.state is SessionState.QUEUED
        assert (directory / AUDIO_FILENAME).is_file()

    def test_complete_after_a_trim_archives_no_removed_text_and_keeps_no_audio(
        self, tmp_path: Path, config: NoteConfig
    ) -> None:
        """PR-HIGH-001: an earlier generation that quoted the tail, then
        Cancel review, the trim and Complete with no regeneration — the
        entry holds the shortened transcript and no generated note; and,
        decision 0.6 (a), no audio although the development consent was
        given."""
        harness = _Harness(tmp_path)
        directory, session_id = harness.adopt()
        trimmed = harness.trim(session_id, config)
        harness.controller.complete()
        entry = harness.store.read_entry(session_id)
        assert entry.transcript == trimmed
        assert entry.generated is None
        assert _TAIL_WORD not in _words(entry.transcript)
        assert harness.controller.last_completion_kept() is False
        assert harness.store.recording_kept(session_id) is False
        [(recorded, facts)] = harness.audit.completions
        assert (recorded, facts.recording_kept) == (session_id, False)
        assert not directory.exists()

    def test_the_untrimmed_twin_keeps_its_audio_and_generated_note(self, tmp_path: Path) -> None:
        """The control: the same session without a trim keeps both."""
        harness = _Harness(tmp_path)
        _directory, session_id = harness.adopt()
        harness.controller.complete()
        assert harness.controller.last_completion_kept() is True
        assert harness.store.recording_kept(session_id) is True
        assert harness.store.read_entry(session_id).generated is not None

    def test_a_regeneration_whose_generated_write_fails_archives_no_removed_text(
        self, tmp_path: Path, config: NoteConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        harness = _Harness(tmp_path)
        directory, session_id = harness.adopt()
        trimmed = harness.trim(session_id, config)
        real = session_store.atomic_write_bytes

        def no_generated(path: Path, blob: bytes, *, error_label: str) -> None:
            if path.name == GENERATED_FILENAME:
                raise StoreWriteError("failed writing generated note: disk full")
            real(path, blob, error_label=error_label)

        monkeypatch.setattr(session_store, "atomic_write_bytes", no_generated)
        lease = harness.controller.begin_generation()
        with pytest.raises(StoreWriteError):
            harness.controller.with_generation_custody(
                lease, lambda d, c: write_generated(d, c, _generated_record(session_id))
            )
        harness.controller.end_generation(lease)
        harness.controller.complete()
        entry = harness.store.read_entry(session_id)
        assert entry.transcript == trimmed and entry.generated is None
        assert not directory.exists()

    def test_trim_then_generate_gives_no_check_6_and_a_matching_digest(
        self, tmp_path: Path, config: NoteConfig
    ) -> None:
        """PR-MED-003: the shortened transcript recomputes to no boundary, so
        the next generation carries no ``possible_next_patient`` and its
        digest is the shortened transcript's — and before the trim the same
        generation did carry it (the control)."""
        harness = _Harness(tmp_path)
        _directory, session_id = harness.adopt()
        generator = models.build_note_generator(
            clinician_speaker=_C,
            template_profile_id=config.template_profiles[0].template_profile_id,
            config_root=VALIDATION_CONFIG,
        )

        def codes() -> tuple[list[str], models.NoteGenerationResult]:
            lease = harness.controller.begin_generation()
            try:
                result = harness.controller.with_generation_custody(lease, generator)
            finally:
                harness.controller.end_generation(lease)
            note = finalise_note(result.draft, [], result.document, result.config, created_at=NOW)
            return [w.note_warning_code for w in note.note_warnings], result

        before, _ = codes()
        assert "possible_next_patient" in before
        trimmed = harness.trim(session_id, config)
        after, result = codes()
        assert "possible_next_patient" not in after
        assert next_patient_boundary(trimmed, config) is None
        assert result.draft.transcript_digest == note_transcript_digest(trimmed)

    def test_a_shadow_session_trims_the_same(self, tmp_path: Path, config: NoteConfig) -> None:
        harness = _Harness(tmp_path)
        directory, session_id = harness.adopt(mode=SessionMode.SHADOW)
        trimmed = harness.trim(session_id, config)
        assert _transcript_on_disk(directory) == trimmed
        assert no_audio_marker_state(directory) is True

    @pytest.mark.parametrize(
        "refusal",
        [
            "lease",
            "saved_note",
            "note_undetermined",
            "another_session",
            "boundary_moved",
            "write_in_flight",
            "discard_in_flight",
        ],
    )
    def test_every_refusal_changes_nothing(
        self,
        tmp_path: Path,
        config: NoteConfig,
        monkeypatch: pytest.MonkeyPatch,
        refusal: str,
    ) -> None:
        harness = _Harness(tmp_path)
        controller = harness.controller
        directory, session_id = harness.adopt(note=refusal == "saved_note")
        boundary_of = lambda document: next_patient_boundary(document, config)  # noqa: E731
        target = session_id
        expected: type[Exception] = SessionActivityError
        if refusal == "lease":
            controller.begin_generation()
            expected = GenerationInProgressError
        elif refusal == "note_undetermined":
            monkeypatch.setattr(session_module, "artifact_state", lambda _d, _f: None)
        elif refusal == "another_session":
            target = uuid.uuid4().hex
        elif refusal == "boundary_moved":
            boundary_of = lambda _document: _BOUNDARY + 1  # noqa: E731
        elif refusal == "write_in_flight":
            controller.reserve_write(session_id)
            expected = WriteInFlightError
        elif refusal == "discard_in_flight":
            with controller._lock:  # noqa: SLF001 - discard() is the producer; injected
                controller._reserve_custody_locked(session_id)  # noqa: SLF001
        before = _files(directory)
        with pytest.raises(expected):
            controller.trim_transcript(target, boundary=_BOUNDARY, boundary_of=boundary_of)
        assert _files(directory) == before

    def test_refused_without_a_queued_live_session(
        self, tmp_path: Path, config: NoteConfig
    ) -> None:
        controller = SessionController(MockCaptureBackend(), sessions_root=tmp_path)
        with pytest.raises(SessionActivityError, match="no session"):
            controller.trim_transcript(
                "a" * 32,
                boundary=_BOUNDARY,
                boundary_of=lambda document: next_patient_boundary(document, config),
            )

    # Failure injected at each step (PR-HIGH-002): before the marker nothing
    # changes; from the marker on it stays, the transcript stays the old one,
    # and Complete then keeps no audio (Task 4.2: "a marker written but a
    # later trim step failed").

    def _fail_marker_write(self, monkeypatch: pytest.MonkeyPatch) -> None:
        real = session_store.atomic_write_bytes

        def failing(path: Path, blob: bytes, *, error_label: str) -> None:
            if path.name == NO_AUDIO_MARKER_FILENAME:
                raise StoreWriteError("failed writing no-audio marker: disk full")
            real(path, blob, error_label=error_label)

        monkeypatch.setattr(session_store, "atomic_write_bytes", failing)

    def _fail_marker_read_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        real = session_store.atomic_write_bytes

        def other(path: Path, blob: bytes, *, error_label: str) -> None:
            if path.name == NO_AUDIO_MARKER_FILENAME:
                blob = b"torn"
            real(path, blob, error_label=error_label)

        monkeypatch.setattr(session_store, "atomic_write_bytes", other)

    def _fail_generated_removal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _deny_unlink(monkeypatch)

    def _fail_generated_confirmation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        real = session_store.artifact_state

        def unsure(directory: Path, filename: str) -> bool | None:
            return None if filename == GENERATED_FILENAME else real(directory, filename)

        monkeypatch.setattr(session_store, "artifact_state", unsure)

    def _fail_transcript_write(self, monkeypatch: pytest.MonkeyPatch) -> None:
        real = transcription.atomic_write_bytes

        def failing(path: Path, blob: bytes, *, error_label: str) -> None:
            if path.name == TRANSCRIPT_FILENAME:
                raise StoreWriteError("failed writing transcript artifact: disk full")
            real(path, blob, error_label=error_label)

        monkeypatch.setattr(transcription, "atomic_write_bytes", failing)

    @pytest.mark.parametrize(
        ("step", "marker", "generated_left"),
        [
            ("marker_write", False, True),
            ("marker_read_back", True, True),
            ("generated_removal", True, True),
            ("generated_confirmation", True, False),
            ("transcript_write", True, False),
        ],
    )
    def test_a_failure_at_each_step_leaves_the_documented_state(
        self,
        tmp_path: Path,
        config: NoteConfig,
        monkeypatch: pytest.MonkeyPatch,
        step: str,
        marker: bool,
        generated_left: bool,
    ) -> None:
        harness = _Harness(tmp_path)
        directory, session_id = harness.adopt()
        original = (directory / TRANSCRIPT_FILENAME).read_bytes()
        getattr(self, f"_fail_{step}")(monkeypatch)
        with pytest.raises(StoreWriteError):
            harness.trim(session_id, config)
        monkeypatch.undo()
        monkeypatch.setattr(session_module, "unwrap_key_from_file", _fake_session_unwrap)
        assert (directory / TRANSCRIPT_FILENAME).read_bytes() == original
        assert (no_audio_marker_state(directory) is True) is marker
        # The unconfirmed removal did unlink the file; the failed one did not.
        assert (artifact_state(directory, GENERATED_FILENAME) is True) is generated_left
        assert harness.controller.state is SessionState.QUEUED
        harness.controller.complete()
        assert harness.controller.last_completion_kept() is not marker
        assert harness.store.recording_kept(session_id) is not marker


# --- an interrupted Complete's unfinished entry (peer Round 22 PR-MED-001) -----------


def _fail_key_deletion_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Complete publishes its entry, then its key deletion fails: the
    session stays QUEUED with an unfinished (pending) entry holding the
    UNTRIMMED transcript, the generated note and the kept audio."""
    real = session_store.delete_session_key
    calls = {"n": 0}

    def failing(session_dir: Path) -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            raise PermissionError("the key file is in use")
        real(session_dir)

    monkeypatch.setattr(session_store, "delete_session_key", failing)


class TestAnInterruptedCompletesEntryGoesWithTheTail:
    def _interrupted(self, harness: _Harness) -> tuple[Path, str, Path, Path]:
        directory, session_id = harness.adopt()
        with pytest.raises(PermissionError):
            harness.controller.complete()
        assert harness.controller.state is SessionState.QUEUED
        entry = harness.store.root / session_id
        assert (entry / PENDING_FILENAME).is_file()
        assert (entry / AUDIO_FILENAME).is_file()  # the consented audio, untrimmed
        assert (entry / GENERATED_FILENAME).is_file()  # quoting the tail
        # A staging copy an interrupted write left behind goes too.
        staging = harness.store.staging_root / session_id
        shutil.copytree(entry, staging)
        return directory, session_id, entry, staging

    def test_trim_after_a_failed_key_deletion_leaves_only_the_trimmed_entry(
        self, tmp_path: Path, config: NoteConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        harness = _Harness(tmp_path)
        _fail_key_deletion_once(monkeypatch)
        directory, session_id, entry, staging = self._interrupted(harness)
        trimmed = harness.trim(session_id, config)
        assert not entry.exists() and not staging.exists()
        harness.controller.complete()
        kept = harness.store.read_entry(session_id)
        assert kept.transcript == trimmed and kept.generated is None
        assert _TAIL_WORD not in _words(kept.transcript)
        assert harness.controller.last_completion_kept() is False
        assert harness.store.recording_kept(session_id) is False
        assert not (entry / AUDIO_FILENAME).exists()
        assert not directory.exists()

    def test_the_same_across_a_restart(
        self, tmp_path: Path, config: NoteConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A restart's reconciliation never commits the unfinished entry
        while the source key exists; the reopened session's trim removes it."""
        harness = _Harness(tmp_path)
        _fail_key_deletion_once(monkeypatch)
        directory, session_id, entry, _staging = self._interrupted(harness)
        assert harness.store.reconcile_pending(harness.root) == []
        assert (entry / PENDING_FILENAME).is_file()
        restarted = SessionController(
            MockCaptureBackend(),
            sessions_root=harness.root,
            audit=harness.audit,  # type: ignore[arg-type]
            past_sessions=harness.store,
        )
        restarted.adopt_queued(directory, lambda _d, _c: None)
        trimmed = restarted.trim_transcript(
            session_id,
            boundary=_BOUNDARY,
            boundary_of=lambda document: next_patient_boundary(document, config),
        )
        assert not entry.exists()
        restarted.complete()
        kept = harness.store.read_entry(session_id)
        assert kept.transcript == trimmed and kept.generated is None
        assert harness.store.recording_kept(session_id) is False

    def test_a_cleanup_failure_refuses_and_leaves_the_transcript(
        self, tmp_path: Path, config: NoteConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        harness = _Harness(tmp_path)
        _fail_key_deletion_once(monkeypatch)
        directory, session_id, entry, _staging = self._interrupted(harness)
        original = (directory / TRANSCRIPT_FILENAME).read_bytes()
        monkeypatch.setattr(harness.store, "remove_pending_entry", lambda _id: False)
        with pytest.raises(SessionActivityError, match="unfinished Past-sessions copy"):
            harness.trim(session_id, config)
        assert (directory / TRANSCRIPT_FILENAME).read_bytes() == original
        assert no_audio_marker_state(directory) is True  # never removed
        assert (entry / PENDING_FILENAME).is_file()
        assert harness.controller.state is SessionState.QUEUED

    def test_the_entry_goes_after_the_marker_and_before_the_transcript(
        self, tmp_path: Path, config: NoteConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D9's order with the new step: marker, generated note, the
        unfinished entry, then the transcript."""
        harness = _Harness(tmp_path)
        _directory, session_id = harness.adopt()
        order: list[str] = []

        def spy(name: str, real: Any) -> Any:
            def call(*args: Any, **kwargs: Any) -> Any:
                order.append(name)
                return real(*args, **kwargs)

            return call

        for name in ("write_no_audio_marker", "remove_generated", "write_transcript"):
            monkeypatch.setattr(session_module, name, spy(name, getattr(session_module, name)))
        monkeypatch.setattr(
            harness.store,
            "remove_pending_entry",
            spy("remove_pending_entry", harness.store.remove_pending_entry),
        )
        harness.trim(session_id, config)
        assert order == [
            "write_no_audio_marker",
            "remove_generated",
            "remove_pending_entry",
            "write_transcript",
        ]


# --- the kept recording (Task 4.2, decision 0.6 (a)) --------------------------------

_PATHS: Final = (
    "complete",
    "complete_without_note",
    "complete_deleting_saved_note",
    "complete_after_write",
    "complete_recovered",
)


def _written_record(identity: str) -> WriteRecord:
    return WriteRecord(
        attempt=1,
        started_at=NOW,
        target_ids=("diagnosis",),
        note_identity=identity,
        digests={"diagnosis": "0" * 64},
        before_digests={"diagnosis": "3" * 64},
        match_sha256="2" * 64,
        body_sha256="1" * 64,
        outcome="written",
        refusal=None,
        finished_at=NOW,
    )


class TestEveryCompletePathKeepsNoAudioAfterATrim:
    @pytest.mark.parametrize("marker", ["absent", "present", "undetermined"])
    @pytest.mark.parametrize("path", _PATHS)
    def test_the_marker_or_any_doubt_about_it_keeps_no_audio(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path: str, marker: str
    ) -> None:
        """``_complete_locked`` overrides ``kept`` on all five paths, live and
        recovered — present, or undeterminable (fail closed). The absent
        twin keeps the audio: the fixture would otherwise be kept."""
        harness = _Harness(tmp_path)
        controller = harness.controller
        note = path in ("complete_deleting_saved_note", "complete_after_write")
        directory, crypto = _session(harness.root, note=note)
        session_id = directory.name
        if marker == "present":
            write_no_audio_marker(directory)
        elif marker == "undetermined":
            monkeypatch.setattr(session_module, "no_audio_marker_state", lambda _d: None)
        if path == "complete_recovered":
            controller.complete_recovered(directory, crypto, kept=True)
        else:
            plain_note = None
            if path == "complete_after_write":
                plain_note = crypto.decrypt((directory / NOTE_FILENAME).read_bytes())
            crypto.destroy()
            controller.adopt_queued(directory, lambda _d, _c: None)
            if path == "complete":
                controller.complete()
            elif path == "complete_without_note":
                controller.complete_without_note(controller.begin_generation())
            elif path == "complete_deleting_saved_note":
                controller.complete_deleting_saved_note()
            else:
                assert plain_note is not None
                record = _written_record(hashlib.sha256(plain_note).hexdigest())
                reservation = controller.reserve_write(session_id)
                controller.with_write_custody(
                    reservation, lambda d, c: store_write_record(d, c, session_id, record)
                )
                reservation.release()
                controller.complete_after_write(controller.reserve_write(session_id))
        kept = marker == "absent"
        assert controller.last_completion_kept() is kept
        assert harness.store.recording_kept(session_id) is kept
        [(recorded, facts)] = harness.audit.completions
        assert (recorded, facts.recording_kept) == (session_id, kept)


# --- the trimmed transcript across a restart (Task 4.2, D9) -------------------------


class TestTheTrimSurvivesARestart:
    def test_recovery_reads_the_trimmed_transcript_and_offers_no_retranscription(
        self, tmp_path: Path, config: NoteConfig
    ) -> None:
        """Recovery never re-transcribes a session that has a transcript
        (``ui/recovery.py``: such a session is listed under Unreviewed, whose
        only actions are Open for review and Discard), so the removed tail
        cannot come back from ``audio.enc``."""
        harness = _Harness(tmp_path)
        directory, session_id = harness.adopt()
        trimmed = harness.trim(session_id, config)
        restarted = SessionController(MockCaptureBackend(), sessions_root=harness.root)
        [info] = models.list_recoverable_sessions(
            harness.root, restarted.custody_protected_ids()
        )
        assert info.session_id == session_id
        assert info.has_transcript and info.has_audio and not info.has_note
        session, opening = restarted.adopt_queued(directory, models.read_for_review)
        assert session.state is SessionState.QUEUED
        assert opening.document == trimmed
        assert next_patient_boundary(opening.document, config) is None

    def test_an_undeterminable_transcript_is_still_listed_for_review(
        self, tmp_path: Path, config: NoteConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Stage-9 review round 28 LOW-002: the listing asks ONE lstat
        (``artifact_state``), and an answer it cannot get counts as a
        transcript — so a trimmed session an access error hides is offered
        for review, never re-transcription from ``audio.enc``."""
        harness = _Harness(tmp_path)
        _directory, session_id = harness.adopt()
        harness.trim(session_id, config)
        real = models.artifact_state

        def unreadable_transcript(session_dir: Path, filename: str) -> bool | None:
            return None if filename == TRANSCRIPT_FILENAME else real(session_dir, filename)

        monkeypatch.setattr(models, "artifact_state", unreadable_transcript)
        restarted = SessionController(MockCaptureBackend(), sessions_root=harness.root)
        [info] = models.list_recoverable_sessions(
            harness.root, restarted.custody_protected_ids()
        )
        assert info.session_id == session_id
        assert info.has_transcript


# --- the Transcript tab (Task 4.1)---------------------------------------------------


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _TrimController(  # noqa: N802 - reads as the fake's class at each use
    document: TranscriptDocument, mode: SessionMode = SessionMode.NORMAL
) -> Any:
    """``test_ui_screens.FakeController`` plus the trim: its live session is
    the document's, it checks the session id as the real one does, records
    the call and returns the shortened document (or raises ``error``)."""
    from test_ui_screens import FakeController

    class Controller(FakeController):
        def __init__(self) -> None:
            super().__init__()
            self.document = document
            self.error: Exception | None = None
            self.state_value = SessionState.QUEUED
            self.session_value = RecordingSession(
                session_id=document.session_id, consent=unlinked_consent(), mode=mode
            ).with_state(SessionState.QUEUED)

        def trim_transcript(
            self, session_id: str, *, boundary: int, boundary_of: Any
        ) -> TranscriptDocument:
            self.calls.append(("trim_transcript", session_id, boundary))
            if self.error is not None:
                raise self.error
            live = self.session_value
            if live is None or live.session_id != session_id:
                raise SessionActivityError("remove lines refused: that session is not the live one")
            assert boundary_of(self.document) == boundary
            self.document = transcript_before(self.document, boundary)
            return self.document

    return Controller()


def _trim_calls(controller: Any) -> list[tuple[Any, ...]]:
    return [call for call in controller.calls if call[0] == "trim_transcript"]


class _Confirm:
    def __init__(self, answer: bool = True, during: Any = None) -> None:
        self.answer = answer
        self.questions: list[str] = []
        self.during = during

    def __call__(self, question: str) -> bool:
        self.questions.append(question)
        if self.during is not None:
            self.during()
        return self.answer


def _screen(
    controller: Any,
    config: NoteConfig,
    *,
    confirm: _Confirm | None = None,
    can_generate: bool = True,
    note_committed: bool = False,
    recovery_busy: bool = False,
) -> Any:
    from scribe_desktop.ui.transcript import TranscriptScreen

    screen = TranscriptScreen(
        controller,
        config_loader=lambda: config,
        recovery_busy_provider=lambda: recovery_busy,
        confirm_remove=confirm if confirm is not None else _Confirm(),
    )
    screen.show_document(
        controller.document,
        on_complete=controller.complete,
        on_discard=controller.discard,
        can_generate=can_generate,
        note_committed=note_committed,
    )
    return screen


def _shown(screen: Any) -> bool:
    return not screen.next_patient_label.isHidden() and not screen.remove_tail_button.isHidden()


class TestTranscriptTab:
    def test_the_line_and_action_name_the_boundary(self, qapp: Any, config: NoteConfig) -> None:
        controller = _TrimController(_document("a" * 32))
        screen = _screen(controller, config)
        assert _shown(screen)
        assert screen.next_patient_label.text() == models.next_patient_transcript_line(
            controller.document, _BOUNDARY
        )
        assert screen.next_patient_label.text().startswith(
            "A possible next patient starts at line 4 ["
        )
        assert screen.remove_tail_button.text() == "Remove lines 4-end from this recording..."
        assert screen.remove_tail_button.isEnabled()
        assert screen.remove_tail_button.toolTip() == models.REMOVE_TAIL_TOOLTIP
        screen.deleteLater()

    @pytest.mark.parametrize(
        "turns",
        [
            _TURNS[:3] + _TURNS[4:],  # a closing, no greeting
            # A same-segment pair at the end, and followed only by an empty
            # segment (PR-MED-003): no segment to cut at, so no action.
            (_TURNS[0], Turn(_C, "See you next week. Hello, come on in.")),
            (_TURNS[0], Turn(_C, "See you next week. Hello, come on in."), Turn(_N, "")),
        ],
        ids=["no_greeting", "pair_at_the_end", "pair_then_empty"],
    )
    def test_shown_only_when_the_rule_fires(
        self, qapp: Any, config: NoteConfig, turns: tuple[Turn, ...]
    ) -> None:
        controller = _TrimController(_document("a" * 32, turns))
        screen = _screen(controller, config)
        assert not _shown(screen)
        screen.remove_tail()
        assert _trim_calls(controller) == []
        screen.deleteLater()

    def test_a_recovered_view_has_no_action(self, qapp: Any, config: NoteConfig) -> None:
        controller = _TrimController(_document("a" * 32))
        screen = _screen(controller, config, can_generate=False)
        assert not _shown(screen)
        screen.deleteLater()

    def test_declining_the_question_changes_nothing(self, qapp: Any, config: NoteConfig) -> None:
        controller = _TrimController(_document("a" * 32))
        confirm = _Confirm(answer=False)
        screen = _screen(controller, config, confirm=confirm)
        text = screen.transcript_view.toPlainText()
        screen.remove_tail()
        assert confirm.questions == [models.remove_tail_question(_BOUNDARY, len(_TURNS))]
        assert _trim_calls(controller) == []
        assert screen.transcript_view.toPlainText() == text
        assert _shown(screen)
        screen.deleteLater()

    def test_removing_shows_the_shorter_transcript_and_refreshes_the_controls(
        self, qapp: Any, config: NoteConfig
    ) -> None:
        controller = _TrimController(_document("a" * 32))
        screen = _screen(controller, config)
        assert _N in screen._role_buttons  # noqa: SLF001 - the radios before
        assert _TAIL_WORD in screen.transcript_view.toPlainText()
        screen.remove_tail()
        session = controller.session_value
        assert _trim_calls(controller) == [("trim_transcript", session.session_id, _BOUNDARY)]
        assert _TAIL_WORD not in screen.transcript_view.toPlainText()
        assert not _shown(screen)  # the shortened transcript has no boundary
        assert _N not in screen._role_buttons  # noqa: SLF001 - refreshed radios
        assert screen.prefill_combo.count() >= 1  # refilled ("No prefill" first)
        assert screen.message_label.text() == models.remove_tail_done_line(
            _BOUNDARY, len(_TURNS)
        )
        screen.deleteLater()

    def test_refused_while_a_review_holds_the_lease(self, qapp: Any, config: NoteConfig) -> None:
        from test_ui_screens import _note_result, _process_until

        controller = _TrimController(_document("a" * 32))
        result = _note_result()

        from scribe_desktop.ui.transcript import TranscriptScreen

        screen = TranscriptScreen(
            controller,
            note_generator_factory=lambda **_kw: lambda _d, _c: result,
            config_loader=lambda: config,
            confirm_remove=_Confirm(),
        )
        screen.show_document(
            controller.document,
            on_complete=controller.complete,
            on_discard=controller.discard,
            can_generate=True,
        )
        drafts: list[Any] = []
        screen.draft_ready.connect(drafts.append)
        screen.set_role(_C)
        screen.set_profile(config.template_profiles[0].template_profile_id)
        screen.generate()
        assert _process_until(qapp, lambda: bool(drafts))
        assert screen.is_busy
        assert not screen.remove_tail_button.isEnabled()
        assert screen.remove_tail_button.toolTip() == models.REMOVE_TAIL_REVIEW_OPEN
        screen.remove_tail()
        assert screen.message_label.text() == models.REMOVE_TAIL_REVIEW_OPEN
        assert _trim_calls(controller) == []
        screen.cancel_note_review()
        assert screen.remove_tail_button.isEnabled()
        screen.deleteLater()

    def test_refused_after_save(self, qapp: Any, config: NoteConfig) -> None:
        controller = _TrimController(_document("a" * 32))
        screen = _screen(controller, config, note_committed=True)
        assert _shown(screen) and not screen.remove_tail_button.isEnabled()
        assert screen.remove_tail_button.toolTip() == models.REMOVE_TAIL_NOTE_SAVED
        screen.remove_tail()
        assert screen.message_label.text() == models.REMOVE_TAIL_NOTE_SAVED
        assert _trim_calls(controller) == []
        screen.deleteLater()

    def test_refused_while_a_recovery_runs(self, qapp: Any, config: NoteConfig) -> None:
        controller = _TrimController(_document("a" * 32))
        screen = _screen(controller, config, recovery_busy=True)
        assert not screen.remove_tail_button.isEnabled()
        assert screen.remove_tail_button.toolTip() == models.REMOVE_TAIL_RECOVERY
        screen.deleteLater()

    def test_refused_while_a_draft_write_holds_the_session(
        self, qapp: Any, config: NoteConfig
    ) -> None:
        controller = _TrimController(_document("a" * 32))
        screen = _screen(controller, config)
        screen.set_write_blocked(True)
        assert not screen.remove_tail_button.isEnabled()
        assert screen.remove_tail_button.toolTip() == models.write_line("write_in_flight")
        screen.deleteLater()

    def test_refused_when_the_session_changed_while_it_asked(
        self, qapp: Any, config: NoteConfig
    ) -> None:
        """The id is read BEFORE the question; a different live session at
        the click is refused by the controller, and the view stays."""
        controller = _TrimController(_document("a" * 32))

        def swap() -> None:
            controller.session_value = RecordingSession(consent=unlinked_consent()).with_state(
                SessionState.QUEUED
            )

        screen = _screen(controller, config, confirm=_Confirm(during=swap))
        text = screen.transcript_view.toPlainText()
        screen.remove_tail()
        assert len(_trim_calls(controller)) == 1
        assert screen.message_label.text().startswith("Lines were not removed: ")
        assert "not the live one" in screen.message_label.text()
        assert screen.transcript_view.toPlainText() == text
        assert _shown(screen)
        screen.deleteLater()

    def test_the_trim_names_the_shown_documents_session(
        self, qapp: Any, config: NoteConfig
    ) -> None:
        """Review round 20 LOW-001: the id the trim names is the SHOWN
        document's, not whichever session the controller holds by the click —
        so a live session that changed under an unchanged view is refused,
        never trimmed in the shown one's place."""
        controller = _TrimController(_document("a" * 32))
        screen = _screen(controller, config)
        controller.session_value = RecordingSession(consent=unlinked_consent()).with_state(
            SessionState.QUEUED
        )
        text = screen.transcript_view.toPlainText()
        screen.remove_tail()
        assert _trim_calls(controller) == [("trim_transcript", "a" * 32, _BOUNDARY)]
        assert "not the live one" in screen.message_label.text()
        assert screen.transcript_view.toPlainText() == text
        screen.deleteLater()

    @pytest.mark.parametrize("speaker", [_C, _N])
    def test_a_dropped_attribution_is_said_not_misreported(
        self, qapp: Any, config: NoteConfig, speaker: str
    ) -> None:
        """Review round 20 LOW-002: when the removed lines held every line of
        the voice-matched speaker, the shortened transcript has no attribution
        (``transcript_before``); the screen says to choose the clinician by
        hand instead of the "attribution did not run" fallback. The control:
        a speaker with lines left keeps it and no line is added."""
        from scribe_desktop.ui.transcript import TranscriptScreen

        document = TranscriptDocument.model_validate(
            {
                **_document("a" * 32).model_dump(),
                "enrolled_speaker": speaker,
                "enrolment_similarity": 0.81,
                "speaker_model_id": "wespeaker-test",
            }
        )
        controller = _TrimController(document)
        screen = TranscriptScreen(
            controller,
            config_loader=lambda: config,
            attribution_readiness_provider=lambda: models.AttributionReadiness(
                profile_present=True, profile=None, reason=None
            ),
            confirm_remove=_Confirm(),
        )
        screen.show_document(
            document,
            on_complete=controller.complete,
            on_discard=controller.discard,
            can_generate=True,
        )
        screen.remove_tail()
        done = models.remove_tail_done_line(_BOUNDARY, len(_TURNS))
        dropped = speaker == _N
        assert controller.document.enrolled_speaker == (None if dropped else _C)
        assert screen.attribution_status_label.isHidden()
        assert screen.message_label.text() == (
            f"{done} {models.REMOVE_TAIL_ATTRIBUTION_DROPPED}" if dropped else done
        )
        screen.deleteLater()

    def test_a_failure_never_shows_the_errors_own_text(
        self, qapp: Any, config: NoteConfig
    ) -> None:
        controller = _TrimController(_document("a" * 32))
        controller.error = StoreWriteError("failed writing transcript artifact: C:/x/y")
        screen = _screen(controller, config)
        screen.remove_tail()
        assert screen.message_label.text() == (
            f"Lines were not removed: {models.CUSTODY_UNEXPECTED_REASON}. "
            "The transcript is unchanged."
        )
        screen.deleteLater()

    def test_a_shadow_session_behaves_the_same(self, qapp: Any, config: NoteConfig) -> None:
        controller = _TrimController(_document("a" * 32), SessionMode.SHADOW)
        screen = _screen(controller, config)
        assert _shown(screen)
        screen.remove_tail()
        assert len(_trim_calls(controller)) == 1
        assert not _shown(screen)
        screen.deleteLater()


class TestCopy:
    def test_the_question_and_lines(self) -> None:
        # Stage-9 round 28 LOW-001: the view numbers no line, so the line also
        # names line N's span exactly as the view prints it.
        document = _document("a" * 32)
        span = models.format_transcript_text(document).splitlines()[3].split(" ", 1)[0]
        assert span.startswith("[") and span.endswith("]")
        assert models.next_patient_transcript_line(document, 3) == (
            f"A possible next patient starts at line 4 {span}."
        )
        assert models.remove_tail_label(3) == "Remove lines 4-end from this recording..."
        assert models.remove_tail_question(3, 5) == (
            "Remove lines 4-5 from this recording? Use this only when they belong to another "
            "patient. They are taken out of the transcript for good: no note, Past-sessions "
            "copy or replay will hold them, and this recording's audio will not be kept for "
            "development. This cannot be undone."
        )
        assert models.remove_tail_done_line(3, 5) == (
            "Lines 4-5 were removed from this recording. Generate the note from what is left."
        )
        assert models.REMOVE_TAIL_ATTRIBUTION_DROPPED == (
            "None of the lines left were matched to your voice, so choose the clinician "
            "speaker before you generate."
        )
