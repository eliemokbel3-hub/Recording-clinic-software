"""Step 10: GUI-free view-logic tests (ui.models) — no Qt required."""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
    def test_report_lines_name_the_default_model(self) -> None:
        from scribe_desktop.transcription import DEFAULT_WHISPER_MODEL

        lines = models.model_report_lines()
        assert len(lines) == 2
        assert lines[0].startswith(f"Whisper model ({DEFAULT_WHISPER_MODEL}):")
        assert lines[1].startswith("VAD model (silero):")
        for line in lines:
            assert ("ready" in line) or ("setup-models" in line)

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
