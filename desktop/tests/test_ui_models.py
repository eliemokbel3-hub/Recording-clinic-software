"""Step 10: GUI-free view-logic tests (ui.models) — no Qt required."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import SessionState
from scribe_desktop.session_store import AUDIO_FILENAME, KEY_FILENAME, SessionChunkStore
from scribe_desktop.transcription import (
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
)
from scribe_desktop.ui import models


def _word(text: str, *, uncertain: bool = False) -> TranscriptWord:
    return TranscriptWord(
        word_text=text,
        start_seconds=0.0,
        end_seconds=0.5,
        probability=0.9,
        uncertain=uncertain,
    )


def _document(segments: tuple[TranscriptSegment, ...]) -> TranscriptDocument:
    return TranscriptDocument(
        session_id=uuid.uuid4().hex,
        created_at=datetime.now(UTC),
        model_name="small",
        sample_rate=16_000,
        transcript_segments=segments,
    )


class TestControlsForState:
    def test_idle_offers_only_start(self) -> None:
        controls = models.controls_for_state(SessionState.IDLE)
        assert controls == models.ControlSet(start=True)

    def test_recording_offers_pause_finish_discard(self) -> None:
        controls = models.controls_for_state(SessionState.RECORDING)
        assert controls == models.ControlSet(pause=True, finish=True, discard=True)

    def test_paused_offers_resume_finish_discard(self) -> None:
        controls = models.controls_for_state(SessionState.PAUSED)
        assert controls == models.ControlSet(resume=True, finish=True, discard=True)

    def test_processing_and_queued_disable_all_session_buttons(self) -> None:
        # PROCESSING: a transcribe run owns the session (PR-HIGH-006);
        # QUEUED: Complete/Discard live on the transcript view.
        assert models.controls_for_state(SessionState.PROCESSING) == models.ControlSet()
        assert models.controls_for_state(SessionState.QUEUED) == models.ControlSet()

    def test_failed_offers_only_discard(self) -> None:
        assert models.controls_for_state(SessionState.FAILED) == models.ControlSet(discard=True)

    def test_terminal_states_offer_start(self) -> None:
        for state in (SessionState.WRITTEN, SessionState.DISCARDED, SessionState.EXPIRED):
            assert models.controls_for_state(state) == models.ControlSet(start=True)

    def test_every_state_has_an_entry(self) -> None:
        for state in SessionState:
            models.controls_for_state(state)  # KeyError would fail the test


class TestFormatTranscript:
    def test_speaker_labels_and_uncertainty_marks_visible(self) -> None:
        document = _document(
            (
                TranscriptSegment(
                    start_seconds=0.0,
                    end_seconds=61.0,
                    speaker="speaker_1",
                    transcript_words=(
                        _word("Hello"),
                        _word("Margaret", uncertain=True),
                    ),
                ),
                TranscriptSegment(
                    start_seconds=62.0,
                    end_seconds=65.0,
                    speaker="speaker_2",
                    transcript_words=(_word("Yes"),),
                ),
            )
        )
        text = models.format_transcript_text(document)
        lines = text.splitlines()
        assert lines[0] == "[00:00-01:01] speaker_1: Hello [Margaret?]"
        assert lines[1] == "[01:02-01:05] speaker_2: Yes"

    def test_empty_document_renders_placeholder(self) -> None:
        assert models.format_transcript_text(_document(())) == "(no speech detected)"

    def test_timestamp_formatting(self) -> None:
        assert models.format_timestamp(0.0) == "00:00"
        assert models.format_timestamp(59.9) == "00:59"
        assert models.format_timestamp(600.0) == "10:00"
        assert models.format_timestamp(-1.0) == "00:00"


def _make_session_dir(root: Path, *, finished: bool, with_audio: bool = True) -> str:
    session_id = uuid.uuid4().hex
    directory = root / session_id
    directory.mkdir(parents=True)
    (directory / KEY_FILENAME).write_bytes(b"\x01" * 64)  # fake wrapped key blob
    if with_audio:
        crypto = SessionCrypto()
        store = SessionChunkStore.create(directory / AUDIO_FILENAME, crypto, session_id)
        store.append_chunk(b"\x00\x01" * 800)
        if finished:
            store.finish()
        store.close()
        crypto.destroy()
    return session_id


class TestListRecoverableSessions:
    def test_missing_root_returns_empty(self, tmp_path: Path) -> None:
        assert models.list_recoverable_sessions(tmp_path / "nope") == []

    def test_lists_sessions_with_custody_and_flags_unfinished(self, tmp_path: Path) -> None:
        finished_id = _make_session_dir(tmp_path, finished=True)
        crashed_id = _make_session_dir(tmp_path, finished=False)
        infos = {i.session_id: i for i in models.list_recoverable_sessions(tmp_path)}
        assert set(infos) == {finished_id, crashed_id}
        assert infos[finished_id].store_finished is True
        assert infos[crashed_id].store_finished is False
        assert infos[finished_id].has_audio and infos[crashed_id].has_audio
        assert infos[finished_id].created_at is not None

    def test_active_session_excluded(self, tmp_path: Path) -> None:
        session_id = _make_session_dir(tmp_path, finished=False)
        assert models.list_recoverable_sessions(tmp_path, frozenset({session_id})) == []

    def test_orphan_and_dead_custody_and_foreign_dirs_skipped(self, tmp_path: Path) -> None:
        orphan = tmp_path / uuid.uuid4().hex
        orphan.mkdir()
        dead = tmp_path / uuid.uuid4().hex
        dead.mkdir()
        (dead / KEY_FILENAME).write_bytes(b"")  # zero-length: cryptographically dead
        (tmp_path / "not-a-session").mkdir()
        assert models.list_recoverable_sessions(tmp_path) == []

    def test_expired_session_not_listed(self, tmp_path: Path) -> None:
        """PR round 18 (PR8): the 24 h cap applies to the LISTING too —
        never offer recovery of a session past its window."""
        import os
        import time

        session_id = _make_session_dir(tmp_path, finished=False)
        old = time.time() - 25 * 3600
        os.utime(tmp_path / session_id / KEY_FILENAME, (old, old))
        assert models.list_recoverable_sessions(tmp_path) == []

    def test_fresh_session_still_listed_with_old_looking_ids(self, tmp_path: Path) -> None:
        session_id = _make_session_dir(tmp_path, finished=True)
        infos = models.list_recoverable_sessions(tmp_path)
        assert [i.session_id for i in infos] == [session_id]

    def test_keyed_dir_without_audio_listed_without_store_flags(self, tmp_path: Path) -> None:
        session_id = _make_session_dir(tmp_path, finished=False, with_audio=False)
        (info,) = models.list_recoverable_sessions(tmp_path)
        assert info.session_id == session_id
        assert info.has_audio is False
        assert info.store_finished is False
        assert info.created_at is None


class TestModelReport:
    def test_report_lines_name_both_models(self) -> None:
        lines = models.model_report_lines()
        assert len(lines) == 2
        assert lines[0].startswith("Whisper model (small):")
        assert lines[1].startswith("VAD model (silero):")
        for line in lines:
            assert ("ready" in line) or ("setup-models" in line)

    def test_models_ready_matches_availability(self) -> None:
        from scribe_desktop.speech import vad_model_available
        from scribe_desktop.transcription import whisper_model_available

        expected = vad_model_available() and whisper_model_available()
        assert models.models_ready() == expected

    def test_vad_availability_is_a_file_presence_check(self, tmp_path: Path) -> None:
        # Smoke round 21: silero presence regression alongside the whisper
        # layout checks (test_benchmark.TestSnapshotCompleteness).
        from scribe_desktop.speech import vad_model_available

        assert not vad_model_available(tmp_path / "silero_vad.onnx")
        model = tmp_path / "silero_vad.onnx"
        model.write_bytes(b"onnx")
        assert vad_model_available(model)

    def test_whisper_availability_accepts_vocabulary_layout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Smoke round 21: the UI report uses the SAME checker as the
        # benchmark/provider — a vocabulary.txt (Systran CT2) layout with no
        # tokenizer.json must report ready.
        from scribe_desktop.transcription import whisper_model_available

        target = tmp_path / "ClinikoScribe" / "models" / "whisper" / "small"
        target.mkdir(parents=True)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert not whisper_model_available()
        for name in ("model.bin", "config.json", "vocabulary.txt"):
            (target / name).write_bytes(b"x")
        assert whisper_model_available()


class TestUnfinishedWarningText:
    def test_binding_warning_wording(self) -> None:
        # Step-10 binding note: the exact user-facing caution must mention
        # the unclean finish and the possibly-missing tail.
        assert "did not finish cleanly" in models.UNFINISHED_STORE_WARNING
        assert "tail may be missing" in models.UNFINISHED_STORE_WARNING


@pytest.mark.parametrize("factory_name", ["build_transcriber", "build_recovery_runner"])
def test_pipeline_factories_are_lazy(factory_name: str) -> None:
    """Factories must not touch the ML stack at construction time — models
    load inside the returned callable (worker thread)."""
    factory = getattr(models, factory_name)
    runner = factory()  # must not raise even with no models cached
    assert callable(runner)
