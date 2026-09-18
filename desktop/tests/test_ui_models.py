"""Step 10: GUI-free view-logic tests (ui.models) — no Qt required."""

from __future__ import annotations

import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from scribe_desktop.note import (
    CANONICAL_SECTION_KEYS,
    CLINICIAN_OWNED_SECTIONS,
    ExtractiveNoteProvider,
    NoteModelProvider,
    admissible_sections,
    compose_draft,
    manual_assertion_id,
    reconstruct_span_text,
    whole_utterance_assertion,
)
from scribe_desktop.note_config import (
    SECTION_CUES_FILENAME,
    AutofillRule,
    NoteConfig,
    load_note_config,
)
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import SessionState
from scribe_desktop.session_store import AUDIO_FILENAME, KEY_FILENAME, SessionChunkStore
from scribe_desktop.speech import SAMPLE_RATE
from scribe_desktop.transcription import (
    SPEAKER_1,
    SPEAKER_2,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
    write_transcript,
)
from scribe_desktop.ui import models

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-only")


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
        truncated = tmp_path / uuid.uuid4().hex
        truncated.mkdir()
        # Round 42 LOW-004: a TRUNCATED blob (< 16 bytes) is the same
        # deadness class as zero-length — custody unwrap and the sweep
        # already treat it as dead; the listing must agree (a listed entry
        # would only offer a Resume that fails with KeyCustodyError).
        (truncated / KEY_FILENAME).write_bytes(b"\x01" * 8)
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

    def test_marginally_future_key_mtime_still_listed(self, tmp_path: Path) -> None:
        """With no store header the 24 h cap has only the key mtime to trust,
        and Windows' coarse clock can put that a few ms ahead of a later
        time.time(). This test used to pass or fail by luck on Python 3.12
        (it read as "future = untrusted" and the session vanished from the
        recovery listing); CLOCK_SKEW_TOLERANCE makes it deterministic."""
        import os
        import time

        session_id = _make_session_dir(tmp_path, finished=False, with_audio=False)
        skewed = time.time() + 0.05  # ~3x the 15.6 ms Windows clock tick
        os.utime(tmp_path / session_id / KEY_FILENAME, (skewed, skewed))
        assert [i.session_id for i in models.list_recoverable_sessions(tmp_path)] == [
            session_id
        ]

    def test_wildly_future_key_mtime_still_fails_closed(self, tmp_path: Path) -> None:
        """Beyond the tolerance a future stamp means a broken or tampered
        clock — the listing must keep failing closed."""
        import os
        import time

        session_id = _make_session_dir(tmp_path, finished=False, with_audio=False)
        future = time.time() + 7 * 86400
        os.utime(tmp_path / session_id / KEY_FILENAME, (future, future))
        assert models.list_recoverable_sessions(tmp_path) == []


def _fake_whisper_snapshot(local_app_data: Path, name: str) -> None:
    """A minimally complete CT2 snapshot dir under a fake LOCALAPPDATA."""
    target = local_app_data / "ClinikoScribe" / "models" / "whisper" / name
    target.mkdir(parents=True, exist_ok=True)
    for filename in ("model.bin", "config.json", "vocabulary.txt"):
        (target / filename).write_bytes(b"x")


class TestModelReport:
    def test_report_lines_name_the_default_model(self, tmp_path: Path) -> None:
        from scribe_desktop.transcription import DEFAULT_WHISPER_MODEL

        lines = models.model_report_lines(profile_root=tmp_path)
        assert len(lines) == 4
        assert lines[0].startswith(f"Whisper model ({DEFAULT_WHISPER_MODEL}):")
        assert lines[1].startswith("VAD model (silero):")
        assert lines[2].startswith("Speaker model (")
        assert lines[3] == models.PROFILE_NOT_ENROLLED_LINE
        for line in lines[:2]:
            assert ("ready" in line) or ("setup-models" in line)
        # The speaker line claims presence only (PR-LOW-029); the profile
        # line names the Practitioner tab, not a setup script.
        assert ("installed" in lines[2]) or ("setup-models" in lines[2])

    def test_models_ready_matches_resolved_availability(self) -> None:
        from scribe_desktop.speech import vad_model_available
        from scribe_desktop.transcription import (
            resolve_whisper_model,
            whisper_model_available,
        )

        expected = vad_model_available() and whisper_model_available(
            resolve_whisper_model()
        )
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
        # tokenizer.json must report ready. Exercises the DEFAULT model dir.
        from scribe_desktop.transcription import (
            DEFAULT_WHISPER_MODEL,
            whisper_model_available,
        )

        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert not whisper_model_available()
        _fake_whisper_snapshot(tmp_path, DEFAULT_WHISPER_MODEL)
        assert whisper_model_available()

    # ------------------------------------------------------------------
    # Step 13 fallback policy: medium default, small visible fallback.
    # ------------------------------------------------------------------

    def test_report_ready_when_default_model_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.transcription import DEFAULT_WHISPER_MODEL

        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        _fake_whisper_snapshot(tmp_path, DEFAULT_WHISPER_MODEL)
        line = models.model_report_lines()[0]
        assert line == f"Whisper model ({DEFAULT_WHISPER_MODEL}): ready"

    def test_report_names_fallback_when_only_fallback_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The clinician must SEE the quality degradation, never discover it.
        from scribe_desktop.transcription import (
            DEFAULT_WHISPER_MODEL,
            FALLBACK_WHISPER_MODEL,
        )

        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        _fake_whisper_snapshot(tmp_path, FALLBACK_WHISPER_MODEL)
        line = models.model_report_lines()[0]
        assert f"Whisper model ({DEFAULT_WHISPER_MODEL}):" in line
        assert f"using fallback {FALLBACK_WHISPER_MODEL}" in line
        assert "setup-models" in line  # remedy for getting the default back

    def test_report_missing_when_no_model_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        line = models.model_report_lines()[0]
        assert "MISSING - run scripts/setup-models.py" in line
        assert "fallback" not in line

    def test_models_ready_accepts_fallback_only_cache(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.transcription import FALLBACK_WHISPER_MODEL

        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        vad_dir = tmp_path / "ClinikoScribe" / "models" / "silero-vad"
        vad_dir.mkdir(parents=True)
        (vad_dir / "silero_vad.onnx").write_bytes(b"onnx")
        assert not models.models_ready()  # no whisper model at all
        _fake_whisper_snapshot(tmp_path, FALLBACK_WHISPER_MODEL)
        assert models.models_ready()  # fallback-only cache is usable


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


# ---------------------------------------------------------------------------
# Voice attribution readiness and the pipeline factories (practitioner-profile
# plan Phase 2, D2 / D3 / D16).
# ---------------------------------------------------------------------------


def _profile(model_id: str, model_sha256: str = "", dim: int = 4) -> Any:
    from datetime import UTC, datetime

    from scribe_desktop.practitioner_profile import ConsentRecord, PractitionerProfile

    now = datetime.now(UTC)
    return PractitionerProfile(
        model_id=model_id,
        model_sha256=model_sha256,
        embedding=tuple([1.0] + [0.0] * (dim - 1)),
        embedding_dim=dim,
        created_at=now,
        enrolment_speech_seconds=30.0,
        device_name="test",
        consent=ConsentRecord(
            accepted_at=now, consent_text_version="consent-v1", learning_opt_in=False
        ),
    )


class TestAttributionReadiness:
    def test_no_profile_means_nothing_to_report_and_no_model_probe(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            models, "speaker_embedder_available", lambda *a, **k: pytest.fail("not probed")
        )
        readiness = models.attribution_readiness(profile_root=tmp_path)
        assert readiness == models.AttributionReadiness(
            profile_present=False, profile=None, reason=None
        )

    def test_presence_is_the_loaders_verdict_not_the_first_run_stat(self) -> None:
        """Peer round 19 PR-HIGH-005: the readiness probe never consults the
        D10 stat (``profile_present``), whose zero-byte / stat-refused
        answers would read an unusable profile as never enrolled."""
        assert "profile_present" not in models.__dict__

    def test_model_missing_with_a_usable_profile_names_the_remedy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.speaker_embedding import shipped_embedder_identity

        usable = _profile(*shipped_embedder_identity())
        monkeypatch.setattr(models, "speaker_embedder_available", lambda *a, **k: False)
        monkeypatch.setattr(models, "load_profile", lambda **k: usable)
        readiness = models.attribution_readiness(profile_root=tmp_path)
        assert readiness.profile_present and readiness.profile is None
        assert readiness.reason == models.SPEAKER_MODEL_MISSING_REASON
        assert "setup-models" in models.SPEAKER_MODEL_MISSING_REASON

    @pytest.mark.parametrize("reason", ["blob", "authentication"])
    def test_an_existing_unusable_blob_is_present_not_never_enrolled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reason: str
    ) -> None:
        """PR-HIGH-005: a zero-length or unreadable ``voice.enc`` — states the
        loader reports as unusable — must carry a reason line, whatever a
        size-based stat would have said (and whether or not the model is
        installed: the profile is read first)."""
        from scribe_desktop.practitioner_profile import ProfileUnusableError

        (tmp_path / "voice.enc").write_bytes(b"")  # zero bytes: the D10 stat says "absent"
        monkeypatch.setattr(
            models, "speaker_embedder_available", lambda *a, **k: pytest.fail("not probed")
        )

        def load(**kwargs: Any) -> Any:
            raise ProfileUnusableError(reason, "detail never shown")  # type: ignore[arg-type]

        monkeypatch.setattr(models, "load_profile", load)
        readiness = models.attribution_readiness(profile_root=tmp_path)
        assert readiness.profile_present is True
        assert readiness.profile is None
        assert readiness.reason == models.PROFILE_UNUSABLE_REASON.format(reason=reason)

    @windows_only
    def test_a_real_zero_byte_blob_reads_as_unusable_through_the_real_loader(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The same case end to end: an empty ``voice.enc`` with no key beside
        it is ``key``-unusable to the real loader, so the probe names it."""
        (tmp_path / "voice.enc").write_bytes(b"")
        monkeypatch.setattr(models, "speaker_embedder_available", lambda *a, **k: True)
        readiness = models.attribution_readiness(profile_root=tmp_path)
        assert readiness.profile_present is True
        assert readiness.reason == models.PROFILE_UNUSABLE_REASON.format(reason="key")

    def test_a_profile_from_another_model_needs_re_enrolment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.practitioner_profile import ProfileUnusableError

        (tmp_path / "voice.enc").write_bytes(b"sealed")
        monkeypatch.setattr(models, "speaker_embedder_available", lambda *a, **k: True)

        def load(**kwargs: Any) -> Any:
            raise ProfileUnusableError("model", "different embedder")

        monkeypatch.setattr(models, "load_profile", load)
        readiness = models.attribution_readiness(profile_root=tmp_path)
        assert readiness.profile is None
        assert readiness.reason == models.PROFILE_REENROL_REASON

    @pytest.mark.parametrize("reason", ["key", "blob", "authentication", "malformed"])
    def test_an_unusable_profile_names_only_its_structural_reason(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reason: str
    ) -> None:
        from scribe_desktop.practitioner_profile import ProfileUnusableError

        (tmp_path / "voice.enc").write_bytes(b"sealed")
        monkeypatch.setattr(models, "speaker_embedder_available", lambda *a, **k: True)

        def load(**kwargs: Any) -> Any:
            raise ProfileUnusableError(reason, "detail never shown")  # type: ignore[arg-type]

        monkeypatch.setattr(models, "load_profile", load)
        readiness = models.attribution_readiness(profile_root=tmp_path)
        assert readiness.reason == models.PROFILE_UNUSABLE_REASON.format(reason=reason)
        assert "detail never shown" not in readiness.reason

    def test_a_usable_profile_is_loaded_against_the_shipped_identity(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.speaker_embedding import shipped_embedder_identity

        (tmp_path / "voice.enc").write_bytes(b"sealed")
        monkeypatch.setattr(models, "speaker_embedder_available", lambda *a, **k: True)
        model_id, model_sha256 = shipped_embedder_identity()
        profile = _profile(model_id, model_sha256)
        asked: list[dict[str, Any]] = []

        def load(**kwargs: Any) -> Any:
            asked.append(kwargs)
            return profile

        monkeypatch.setattr(models, "load_profile", load)
        monkeypatch.setattr(
            models, "build_speaker_embedder", lambda *a, **k: pytest.fail("no model on GUI path")
        )
        readiness = models.attribution_readiness(profile_root=tmp_path)
        assert readiness == models.AttributionReadiness(
            profile_present=True, profile=profile, reason=None
        )
        assert asked == [{"root": tmp_path, "model_id": model_id, "model_sha256": model_sha256}]

    def test_the_loaders_none_is_the_only_confirmed_absence(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            models, "speaker_embedder_available", lambda *a, **k: pytest.fail("not probed")
        )
        monkeypatch.setattr(models, "load_profile", lambda **k: None)
        readiness = models.attribution_readiness(profile_root=tmp_path)
        assert readiness.profile_present is False and readiness.reason is None


class TestPractitionerReportLines:
    """The two D2 report lines the Practitioner tab and the microphone
    screen's panel share (Task 3.2), plus the ratified consent text."""

    def test_speaker_model_line_names_the_remedy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.speaker_embedding import shipped_embedder_identity

        monkeypatch.setattr(models, "speaker_embedder_available", lambda *a, **k: False)
        missing = models.speaker_model_report_line()
        assert "MISSING" in missing
        assert "--only speaker-embedding" in missing
        monkeypatch.setattr(models, "speaker_embedder_available", lambda *a, **k: True)
        installed = models.speaker_model_report_line()
        # PR-LOW-029: a stat proves presence, not loadability.
        assert installed.endswith("installed - verified when it loads")
        assert "ready" not in installed
        assert shipped_embedder_identity()[0] in installed
        assert models.speaker_model_report_line("spectral").endswith("ready (built in)")

    def test_profile_line_not_enrolled(self, tmp_path: Path) -> None:
        line = models.voice_profile_report_line(profile_root=tmp_path)
        assert line == models.PROFILE_NOT_ENROLLED_LINE
        assert "Practitioner tab" in line

    @windows_only
    def test_profile_line_enrolled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.practitioner_profile import ConsentRecord, save_profile
        from scribe_desktop.speaker_embedding import shipped_embedder_identity

        model_id, model_sha256 = shipped_embedder_identity()
        profile = _profile(model_id, model_sha256)  # `_profile` records consent-v1
        save_profile(profile, root=tmp_path)
        monkeypatch.setattr(models, "speaker_embedder_available", lambda *a, **k: True)
        # Task 5.0: a readable record carrying an OLDER consent text still
        # attributes; the line says so and points at the Practitioner tab.
        assert models.voice_profile_report_line(profile_root=tmp_path) == (
            f"Voice profile: enrolled {profile.created_at:%Y-%m-%d} (model {model_id})"
            " - consent text updated, confirm it on the Practitioner tab"
        )
        current = profile.model_copy(
            update={
                "consent": ConsentRecord(
                    accepted_at=profile.consent.accepted_at,
                    consent_text_version=models.CONSENT_TEXT_VERSION,
                    learning_opt_in=False,
                )
            }
        )
        save_profile(current, root=tmp_path)
        assert models.voice_profile_report_line(profile_root=tmp_path) == (
            f"Voice profile: enrolled {profile.created_at:%Y-%m-%d} (model {model_id})"
        )
        monkeypatch.setattr(models, "speaker_embedder_available", lambda *a, **k: False)
        assert (
            models.voice_profile_report_line(profile_root=tmp_path)
            == models.SPEAKER_MODEL_MISSING_REASON
        )

    @windows_only
    def test_profile_line_made_by_another_model(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.practitioner_profile import save_profile

        save_profile(_profile("other-model"), root=tmp_path)
        monkeypatch.setattr(models, "speaker_embedder_available", lambda *a, **k: True)
        assert (
            models.voice_profile_report_line(profile_root=tmp_path)
            == models.PROFILE_REENROL_REASON
        )

    def test_consent_text_is_versioned(self) -> None:
        from scribe_desktop.practitioner_profile import ConsentRecord

        assert models.CONSENT_TEXT_VERSION == "consent-v2"
        assert models.CONSENT_TEXT_V2.endswith("Version consent-v2.")
        # v1 stays as HISTORY for the records that still carry it (Task 5.0),
        # with its OWN literal version string.
        assert models.CONSENT_TEXT_V1.endswith("Version consent-v1.")
        # The version string the current text carries is the one a profile records.
        ConsentRecord(
            accepted_at=datetime.now(UTC),
            consent_text_version=models.CONSENT_TEXT_VERSION,
            learning_opt_in=False,
        )
        # The v2 (auto-learn, review-later) promises, verbatim.
        for promise in (
            "never a recording",
            "plain text",
            "lines you add or move",
            "Only your own lines are ever used",
            "names, numbers, dates or medication names",
            "nothing leaves this computer",
            "delete any learned phrase",
        ):
            assert promise in models.CONSENT_TEXT_V2
        assert models.LEARNING_OPT_IN_LABEL == (
            "Also learn my phrasing from lines I add or move during review "
            "(saved when I save the note)"
        )

    def test_the_current_consent_text_is_the_ratified_text_verbatim(self) -> None:
        """Round 54 SEC-001: "a changed text is a new version" has no
        structural enforcement — a record's `consent_text_version` is a string
        compared with `CONSENT_TEXT_VERSION`, so an edit to `CONSENT_TEXT_V2`
        that kept the version string would count every existing v2 record as
        consent to words the practitioner never saw. This pin holds the
        ratified text (plan `Consent text v2`, 2026-09-16) verbatim beside the
        version: to change the text, ratify a v3, add `CONSENT_TEXT_V3`, bump
        `CONSENT_TEXT_VERSION` and pin the new text here — never edit v2."""
        ratified_v2 = (
            "This app can learn your voice and your phrasing to improve your notes. If you "
            "agree, it stores on this computer: a numeric fingerprint of your voice (never a "
            "recording), encrypted; and, if you also turn on phrase learning, short phrases "
            "taken from lines you add or move while reviewing a note, saved automatically "
            "when you save the note and kept as plain text in your own config file until you "
            "delete them. Only your own lines are ever used — never a patient's. The app "
            "cannot tell whether a phrase names a patient, so it refuses phrases containing "
            "names, numbers, dates or medication names, and shows you everything it has "
            "learned on this tab so you can delete any of it. Nothing else about any patient "
            "is stored beyond their session, and nothing leaves this computer. You can "
            "re-record your voice, delete it, or delete any learned phrase at any time from "
            "this tab. Version consent-v2."
        )
        assert models.CONSENT_TEXT_V2 == ratified_v2
        assert models.CONSENT_TEXT_VERSION == "consent-v2"
        # The version a record stores is the one the shipped text ends with.
        assert models.CONSENT_TEXT_V2.endswith(f"Version {models.CONSENT_TEXT_VERSION}.")


class TestAttributionInputs:
    def _ready(self, profile: Any) -> Any:
        return lambda **k: models.AttributionReadiness(
            profile_present=profile is not None, profile=profile, reason=None
        )

    def test_no_usable_profile_builds_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(models, "attribution_readiness", self._ready(None))
        monkeypatch.setattr(
            models, "build_speaker_embedder", lambda *a, **k: pytest.fail("must not build")
        )
        assert models.attribution_inputs() == (None, None)

    def test_a_model_that_refuses_to_load_falls_back_visibly_later(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.speaker_embedding import MOCK_MODEL_ID, SpeakerModelError

        monkeypatch.setattr(models, "attribution_readiness", self._ready(_profile(MOCK_MODEL_ID)))

        def build(*a: Any, **k: Any) -> Any:
            raise SpeakerModelError("not the pinned model")

        monkeypatch.setattr(models, "build_speaker_embedder", build)
        assert models.attribution_inputs() == (None, None)

    def test_the_built_embedder_identity_is_rechecked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.speaker_embedding import MOCK_MODEL_ID, MockSpeakerEmbedder

        embedder = MockSpeakerEmbedder(embedding_dim=4)
        monkeypatch.setattr(models, "build_speaker_embedder", lambda *a, **k: embedder)
        profile = _profile(MOCK_MODEL_ID)
        monkeypatch.setattr(models, "attribution_readiness", self._ready(profile))
        assert models.attribution_inputs() == (embedder, profile)
        mismatched = (
            _profile("other-model-v1"),
            _profile(MOCK_MODEL_ID, "a" * 64),
            _profile(MOCK_MODEL_ID, dim=5),
        )
        for wrong in mismatched:
            monkeypatch.setattr(models, "attribution_readiness", self._ready(wrong))
            assert models.attribution_inputs() == (None, None)


class _InertVad:
    def frame_probability(self, frame: bytes) -> float:
        return 0.0


class _InertProvider:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass


@pytest.mark.parametrize("with_inputs", [True, False])
@pytest.mark.parametrize("factory_name", ["build_transcriber", "build_recovery_runner"])
def test_both_pipeline_factories_pass_the_attribution_inputs(
    factory_name: str, with_inputs: bool, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """D3: BOTH entry points hand the embedder and the profile to the
    pipeline — or ``None`` for both on the D2 fallback — resolved inside the
    worker call, never at construction."""
    from scribe_desktop.speaker_embedding import MOCK_MODEL_ID, MockSpeakerEmbedder

    embedder = MockSpeakerEmbedder(embedding_dim=4)
    profile = _profile(MOCK_MODEL_ID)
    inputs = (embedder, profile) if with_inputs else (None, None)
    resolved: list[int] = []
    seen: list[dict[str, Any]] = []

    def attribution() -> Any:
        resolved.append(1)
        return inputs

    def record(*args: Any, **kwargs: Any) -> Any:
        seen.append(kwargs)
        return object()

    monkeypatch.setattr(models, "SileroVad", _InertVad)
    monkeypatch.setattr(models, "WhisperSpeechProvider", _InertProvider)
    monkeypatch.setattr(models, "resolve_whisper_model", lambda *a, **k: "small")
    monkeypatch.setattr(models, "transcribe_session", record)
    monkeypatch.setattr(models, "recover_session_transcription", record)
    factory = getattr(models, factory_name)
    runner = factory(attribution=attribution)
    assert resolved == []  # resolved at call time, in the worker
    if factory_name == "build_transcriber":
        runner(tmp_path, SessionCrypto())
    else:
        runner(tmp_path)
    assert resolved == [1]
    assert len(seen) == 1
    assert seen[0]["speaker_embedder"] is inputs[0]
    assert seen[0]["enrolled_profile"] is inputs[1]
    assert seen[0]["model_name"] == "small"


# ---------------------------------------------------------------------------
# Practitioner-profile plan Task 4.3 — the generator's provider is built FROM
# the resolved config, so the cue file routes what reaches the note.
# ---------------------------------------------------------------------------

CUE_UTTERANCE = "Your home exercise is the wall slide"


def _cue_document(text: str, speaker: str) -> TranscriptDocument:
    words = text.split()
    transcript_words = tuple(
        TranscriptWord(
            word_text=word,
            start_seconds=index * 0.3,
            end_seconds=index * 0.3 + 0.2,
            probability=0.9,
            uncertain=False,
        )
        for index, word in enumerate(words)
    )
    segment = TranscriptSegment(
        start_seconds=0.0,
        end_seconds=len(words) * 0.3,
        speaker=speaker,
        transcript_words=transcript_words,
    )
    return TranscriptDocument(
        session_id="d" * 32,
        created_at=datetime(2026, 9, 16, 12, 0, tzinfo=UTC),
        model_name="mock",
        sample_rate=SAMPLE_RATE,
        transcript_segments=(segment,),
    )


def _write_cue_file(root: Path, cues: dict[str, list[str]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / SECTION_CUES_FILENAME).write_text(
        json.dumps({"schema_version": 1, "section_cues": cues}), encoding="utf-8"
    )


def _generate(
    tmp_path: Path, config_root: Path, **factory_overrides: Any
) -> models.NoteGenerationResult:
    session_dir = tmp_path / "session"
    session_dir.mkdir(exist_ok=True)
    crypto = SessionCrypto()
    write_transcript(session_dir, crypto, _cue_document(CUE_UTTERANCE, SPEAKER_2))
    generator = models.build_note_generator(
        clinician_speaker=SPEAKER_2,
        template_profile_id="template-a",
        config_root=config_root,
        **factory_overrides,
    )
    return generator(session_dir, crypto)


def _section_keys(result: models.NoteGenerationResult) -> list[str]:
    return [section.section_key for section in result.draft.note_sections]


class TestProviderFromConfig:
    def test_the_shipped_cues_route_through_the_generator(self, tmp_path: Path) -> None:
        result = _generate(tmp_path, tmp_path / "config")
        assert _section_keys(result) == ["advice_home_exercise"]
        assert result.draft.note_sections[0].note_assertions[0].text == CUE_UTTERANCE

    def test_a_user_file_that_drops_the_cue_stops_the_routing(self, tmp_path: Path) -> None:
        shipped = _generate(tmp_path, tmp_path / "config")
        root = tmp_path / "user-config"
        _write_cue_file(root, {"presenting_complaint": ["came in because"]})
        result = _generate(tmp_path, root)
        assert "advice_home_exercise" not in _section_keys(result)
        assert result.draft.note_sections == ()
        assert result.config.config_digest() != shipped.config.config_digest()

    def test_a_user_file_that_adds_a_cue_reroutes_the_utterance(self, tmp_path: Path) -> None:
        root = tmp_path / "user-config"
        _write_cue_file(root, {"treatment_performed": ["wall slide"]})
        result = _generate(tmp_path, root)
        assert _section_keys(result) == ["treatment_performed"]
        assert result.draft.note_sections[0].note_assertions[0].text == CUE_UTTERANCE

    def test_the_factory_receives_the_resolved_config(self, tmp_path: Path) -> None:
        received: list[NoteConfig] = []

        def factory(config: NoteConfig) -> NoteModelProvider:
            received.append(config)
            return ExtractiveNoteProvider(cues=config.normalised_cues())

        result = _generate(tmp_path, tmp_path / "config", provider_factory=factory)
        assert len(received) == 1
        assert received[0] is result.config
        assert received[0].config_digest() == result.config.config_digest()

    def test_the_default_factory_is_the_extractive_provider_from_the_config(
        self, tmp_path: Path
    ) -> None:
        provider = models._extractive_provider_from_config(
            models.load_note_config(tmp_path / "config")
        )
        assert isinstance(provider, ExtractiveNoteProvider)
        assert provider.provider_name == "extractive-v1"


# ---------------------------------------------------------------------------
# Phrase-learning status (practitioner-profile plan Phase 5, D9 as amended +
# Task 5.0's consent-version check).
# ---------------------------------------------------------------------------


def _consent(version: str, *, learning_opt_in: bool) -> Any:
    from scribe_desktop.practitioner_profile import ConsentRecord

    return ConsentRecord(
        accepted_at=datetime.now(UTC),
        consent_text_version=version,
        learning_opt_in=learning_opt_in,
    )


def _current_consent_profile(*, learning_opt_in: bool) -> Any:
    """A readable profile whose consent record carries the CURRENT text."""
    return _profile("mock-speaker-embedder-v1").model_copy(
        update={
            "consent": _consent(models.CONSENT_TEXT_VERSION, learning_opt_in=learning_opt_in)
        }
    )


class TestLearningStatus:
    """Learning is on ONLY for a readable profile carrying the CURRENT consent
    version with the opt-in ticked; every other state names its own hint."""

    def test_no_profile_is_off_and_points_at_the_practitioner_tab(
        self, tmp_path: Path
    ) -> None:
        status = models.learning_status(profile_root=tmp_path)
        assert status == models.LearningStatus(False, models.LEARNING_NO_PROFILE_HINT)
        assert "Practitioner tab" in models.LEARNING_NO_PROFILE_HINT

    def test_an_unusable_profile_names_only_its_structural_reason(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.practitioner_profile import ProfileUnusableError

        def load(**kwargs: Any) -> Any:
            raise ProfileUnusableError("key", "detail never shown")

        monkeypatch.setattr(models, "load_profile", load)
        status = models.learning_status(profile_root=tmp_path)
        assert status == models.LearningStatus(
            False, models.LEARNING_UNUSABLE_HINT.format(reason="key")
        )
        assert "detail never shown" not in (status.reason or "")

    def test_a_stale_consent_record_turns_learning_off(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stale = _profile("mock-speaker-embedder-v1")  # consent-v1
        assert models.consent_is_current(stale) is False
        monkeypatch.setattr(models, "load_profile", lambda **k: stale)
        assert models.learning_status(profile_root=tmp_path) == models.LearningStatus(
            False, models.LEARNING_STALE_CONSENT_HINT
        )

    def test_a_current_record_without_the_opt_in_is_off(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        opted_out = _current_consent_profile(learning_opt_in=False)
        assert models.consent_is_current(opted_out) is True
        monkeypatch.setattr(models, "load_profile", lambda **k: opted_out)
        assert models.learning_status(profile_root=tmp_path) == models.LearningStatus(
            False, models.LEARNING_OPTED_OUT_HINT
        )

    def test_a_current_record_with_the_opt_in_is_on_with_no_hint(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        opted_in = _current_consent_profile(learning_opt_in=True)
        monkeypatch.setattr(models, "load_profile", lambda **k: opted_in)
        assert models.learning_status(profile_root=tmp_path) == models.LearningStatus(
            True, None
        )

    def test_the_status_never_probes_or_loads_the_speaker_model(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Learning needs CONSENT, not the speaker model: a stale-model profile
        still records what was agreed, so no model stat and no model load."""
        monkeypatch.setattr(
            models, "speaker_embedder_available", lambda *a, **k: pytest.fail("not probed")
        )
        monkeypatch.setattr(
            models, "build_speaker_embedder", lambda *a, **k: pytest.fail("not loaded")
        )
        monkeypatch.setattr(
            models, "load_profile", lambda **k: _current_consent_profile(learning_opt_in=True)
        )
        assert models.learning_status(profile_root=tmp_path).enabled is True


# ---------------------------------------------------------------------------
# Review-edit view models (practitioner-profile plan Phase 5, D14 — Tasks 5.1
# and 5.1b): the working draft, the utterance chooser, the line editor.
# ---------------------------------------------------------------------------

_REVIEW_TURNS: tuple[tuple[str, str], ...] = (
    ("My left knee is sore when I walk", SPEAKER_1),  # 0: routed (patient)
    ("On examination the range of motion is limited", SPEAKER_2),  # 1: routed (clinician)
    ("I walked to the shop this morning", SPEAKER_1),  # 2: unrouted patient line
    ("Do you feel pain here?", SPEAKER_2),  # 3: unrouted clinician QUESTION
    ("The knee felt steady on the stairs", SPEAKER_2),  # 4: unrouted clinician statement
    ("", SPEAKER_1),  # 5: no words at all
)


def _review_words(text: str) -> tuple[TranscriptWord, ...]:
    return tuple(
        TranscriptWord(
            word_text=token,
            start_seconds=index * 0.3,
            end_seconds=index * 0.3 + 0.25,
            probability=0.9,
            uncertain=False,
        )
        for index, token in enumerate(text.split())
    )


def _review_document() -> TranscriptDocument:
    return TranscriptDocument(
        session_id="f" * 32,
        created_at=datetime(2026, 9, 16, 12, 0, tzinfo=UTC),
        model_name="mock",
        sample_rate=SAMPLE_RATE,
        transcript_segments=tuple(
            TranscriptSegment(
                start_seconds=float(index * 10),
                end_seconds=float(index * 10 + 5),
                speaker=speaker,
                transcript_words=_review_words(text),
            )
            for index, (text, speaker) in enumerate(_REVIEW_TURNS)
        ),
    )


def _review_draft(tmp_path: Path) -> tuple[Any, TranscriptDocument]:
    """A draft over `_REVIEW_TURNS` routed by the SHIPPED cues (the config the
    loader resolves with no user files present), plus ONE autofill rule so the
    draft carries a proposal the working draft must carry unchanged."""
    document = _review_document()
    shipped = load_note_config(tmp_path / "config")
    config = NoteConfig(
        template_profiles=shipped.template_profiles,
        autofill_rules=(
            AutofillRule(
                rule_id="rule-rom",
                section_key="objective_examination",
                trigger_phrase="range of motion",
                expansion=("Range of motion documented.",),
            ),
        ),
        prefill_templates=shipped.prefill_templates,
        section_cues=shipped.section_cues,
    )
    draft = compose_draft(
        document,
        config,
        ExtractiveNoteProvider(cues=config.normalised_cues()),
        "template-a",
        clinician_speaker=SPEAKER_2,
    )
    assert draft.note_proposals, "the autofill rule must have fired"
    return draft, document


def _manual_line(document: TranscriptDocument, index: int, key: Any) -> Any:
    """One whole utterance as the Note tab's manual addition (`m<segment>`)."""
    segment = document.transcript_segments[index]
    assertion = whole_utterance_assertion(
        manual_assertion_id(index),
        key,
        segment_index=index,
        speaker=segment.speaker,
        words=segment.transcript_words,
    )
    assert assertion is not None
    return assertion


class TestReviewEditModels:
    def test_a_removed_line_is_filtered_and_its_emptied_section_dropped(
        self, tmp_path: Path
    ) -> None:
        draft, _document = _review_draft(tmp_path)
        routed = {
            assertion.assertion_id: section.section_key
            for section in draft.note_sections
            for assertion in section.note_assertions
        }
        assert "x0001" in routed, "the shipped cues must route the examination line"
        working = models.working_draft(draft, removed={"x0001"}, additions=())
        assert routed["x0001"] not in [s.section_key for s in working.note_sections]
        assert all(
            assertion.assertion_id != "x0001"
            for section in working.note_sections
            for assertion in section.note_assertions
        )

    def test_an_addition_lands_after_the_providers_lines_in_canonical_order(
        self, tmp_path: Path
    ) -> None:
        draft, document = _review_draft(tmp_path)
        assert [a.assertion_id for a in draft.note_sections[0].note_assertions] == ["x0000"]
        same_section = _manual_line(document, 2, "presenting_complaint")
        later_section = _manual_line(document, 4, "assessment")
        working = models.working_draft(
            draft, removed=(), additions=(later_section, same_section)
        )
        section = next(
            s for s in working.note_sections if s.section_key == "presenting_complaint"
        )
        assert [a.assertion_id for a in section.note_assertions] == ["x0000", "m0002"]
        keys = [s.section_key for s in working.note_sections]
        assert keys == sorted(keys, key=CANONICAL_SECTION_KEYS.index)
        # The proposals and the digests travel unchanged: the resolution
        # evidence and the check targets keep matching.
        assert working.note_proposals == draft.note_proposals
        assert working.transcript_digest == draft.transcript_digest
        assert working.config_digest == draft.config_digest
        assert working.session_id == draft.session_id
        assert working.template_profile_id == draft.template_profile_id
        assert working.provider_name == draft.provider_name
        assert working.clinician_speaker == draft.clinician_speaker

    def test_a_duplicate_assertion_id_is_refused_by_the_draft_itself(
        self, tmp_path: Path
    ) -> None:
        draft, document = _review_draft(tmp_path)
        segment = document.transcript_segments[2]
        clash = whole_utterance_assertion(
            "x0000",  # the provider's own id for segment 0
            "presenting_complaint",
            segment_index=2,
            speaker=segment.speaker,
            words=segment.transcript_words,
        )
        assert clash is not None
        with pytest.raises(ValidationError, match="duplicate assertion_id"):
            models.working_draft(draft, removed=(), additions=(clash,))

    def test_the_chooser_skips_the_note_and_the_textless_and_labels_each_line(
        self, tmp_path: Path
    ) -> None:
        _draft, document = _review_draft(tmp_path)
        choices = models.eligible_utterances(
            document, clinician_speaker=SPEAKER_2, in_note={0, 1}
        )
        assert [choice.segment_index for choice in choices] == [2, 3, 4]
        for choice in choices:
            segment = document.transcript_segments[choice.segment_index]
            assert choice.label.startswith(f"{choice.segment_index + 1}. {segment.speaker}: ")
            assert choice.allowed_sections == admissible_sections(
                CANONICAL_SECTION_KEYS,
                speaker=segment.speaker,
                clinician_speaker=SPEAKER_2,
                text=reconstruct_span_text(segment.transcript_words),
            )

    def test_the_ownership_rule_shapes_the_sections_each_line_may_enter(
        self, tmp_path: Path
    ) -> None:
        _draft, document = _review_draft(tmp_path)
        by_index = {
            choice.segment_index: choice
            for choice in models.eligible_utterances(
                document, clinician_speaker=SPEAKER_2, in_note=()
            )
        }
        patient = by_index[2].allowed_sections
        assert not set(patient) & CLINICIAN_OWNED_SECTIONS
        assert len(patient) == len(CANONICAL_SECTION_KEYS) - len(CLINICIAN_OWNED_SECTIONS)
        # The confirmed clinician's STATEMENT may enter all 17 sections...
        assert by_index[4].allowed_sections == CANONICAL_SECTION_KEYS
        # ...their QUESTION may not enter a clinician-owned one.
        assert not set(by_index[3].allowed_sections) & CLINICIAN_OWNED_SECTIONS

    def test_editable_lines_carry_their_edit_state(self, tmp_path: Path) -> None:
        draft, document = _review_draft(tmp_path)
        routed = models.editable_lines(draft, document, removed=set(), additions={})
        assert routed
        assert {line.state for line in routed} == {"routed"}
        for line in routed:
            assert line.label.startswith(f"{models.section_title(line.section_key)} - ")
            assert line.section_key not in line.allowed_sections  # a Move needs elsewhere
            assert line.moved_to is None

        removed = models.editable_lines(draft, document, removed={"x0001"}, additions={})
        subtracted = next(line for line in removed if line.assertion_id == "x0001")
        assert subtracted.state == "removed"
        assert subtracted.moved_to is None

        moved_leg = _manual_line(document, 1, "assessment")
        moved = models.editable_lines(
            draft, document, removed={"x0001"}, additions={moved_leg.assertion_id: moved_leg}
        )
        rows = [line for line in moved if line.segment_index == 1]
        assert len(rows) == 1  # the manual leg is NOT a second row
        assert rows[0].assertion_id == "x0001"
        assert rows[0].state == "moved"
        assert rows[0].moved_to == "assessment"

        added_leg = _manual_line(document, 2, "presenting_complaint")
        added = models.editable_lines(
            draft, document, removed=set(), additions={added_leg.assertion_id: added_leg}
        )
        row = next(line for line in added if line.assertion_id == "m0002")
        assert row.state == "added"
        assert row.moved_to is None
        assert row.label.startswith(f"{models.section_title('presenting_complaint')} - ")

    def test_the_omission_copy_names_a_line_the_clinician_removed(self) -> None:
        """Task 5.1b: a REMOVED line raises `high_risk_omission` too, so the
        acknowledgement copy must name that case."""
        copy = models.WARNING_COPY["high_risk_omission"]
        assert "a line you removed" in copy.clear_hint
        assert copy.blocks is None  # review, never a block (D14)
