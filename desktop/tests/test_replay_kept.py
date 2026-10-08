"""The kept-recordings replay tool (development-recordings plan Phase 4,
Tasks 4.1a and 4.1b; D11, C1, C5, C6, C8).

Every entry here is SYNTHETIC: invented sentences and generated tones,
written through the store's own verified ``write_entry`` into pytest's
temporary folders, under the fake entry-key custody of
``test_past_sessions.py``. The app's instance exclusion, the models and the
store are the module's injected seams (the conftest makes the real
exclusion raise), the developer channel is pinned (the tool refuses
production first), and the models root is the conftest's empty pin."""

from __future__ import annotations

import hashlib
import importlib.util
import math
import os
import shutil
import struct
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from conftest import REAL_REPLAY_EXCLUSION, use_channel
from scribe_desktop import install_layout, past_sessions, replay_kept, speaker_eval
from scribe_desktop.benchmark import OFFLINE_ENV, assert_offline_env
from scribe_desktop.enrolment import EnrolmentError
from scribe_desktop.note import (
    GeneratedNote,
    compose_draft,
    content_tokens,
    finalise_note,
)
from scribe_desktop.note_config import load_note_config
from scribe_desktop.past_sessions import (
    AUDIO_KEY_FILENAME,
    LABEL_FILENAME,
    PAST_SESSION_REASONS,
    KeepLabel,
    PastSessionError,
    PastSessionStore,
)
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import (
    KEY_FILENAME,
    TRANSCRIPT_FILENAME,
    ArchiveSource,
    KeyCustodyError,
)
from scribe_desktop.speaker_eval import (
    TEMP_DIR_PREFIX,
    WAV_FORMAT_HELP,
    WavFormatError,
    _ReplayProvider,
)
from scribe_desktop.speech import BYTES_PER_SAMPLE, SAMPLE_RATE, TranscribedWord
from scribe_desktop.transcription import TranscriptDocument, TranscriptSegment, TranscriptWord
from scribe_desktop.ui.models import extractive_provider_from_config
from scribe_desktop.validation import (
    WordErrors,
    align_transcripts,
    confirm_all,
    transcript_wer,
)
from speaker_fakes import FrequencyEmbedder

REPO = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 8, 9, 0, tzinfo=UTC)
LABEL = KeepLabel("Jane Citizen", "linked", "0123456789abcdef", shadow=False)
_FAKE = b"FAKE-ENTRY-KEY:"

# Invented content. The clinician's line routes to a clinician-owned section
# (only with a confirmed clinician); the patient's to the presenting
# complaint (always). The kept transcript has one word the new one lacks.
CLINICIAN = "The plan is gentle home exercise."
PATIENT = "My knee hurts when I walk."
PATIENT_KEPT = "My knee hurts when I walk today."
CONTENT_WORDS = (
    "plan", "gentle", "exercise", "knee", "hurts", "walk", "today", "Jane", "Citizen"
)


def _fake_wrap(crypto: SessionCrypto, directory: Path) -> None:
    (directory / KEY_FILENAME).write_bytes(_FAKE + crypto.export_key())


def _fake_unwrap(directory: Path) -> SessionCrypto:
    blob = (directory / KEY_FILENAME).read_bytes()
    if not blob.startswith(_FAKE):
        raise KeyCustodyError("not an entry key")
    return SessionCrypto.from_key(blob[len(_FAKE) :])


def _store(folder: Path) -> PastSessionStore:
    return PastSessionStore(folder, wrap_key=_fake_wrap, unwrap_key=_fake_unwrap)


def _tone(seconds: float, frequency: float, amplitude: float = 0.5) -> bytes:
    count = int(seconds * SAMPLE_RATE)
    scale = amplitude * 32767
    return struct.pack(
        f"<{count}h",
        *(int(scale * math.sin(2 * math.pi * frequency * i / SAMPLE_RATE)) for i in range(count)),
    )


def _silence(seconds: float) -> bytes:
    return b"\0" * (int(seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE)


# Two turns: the clinician's tone at 1.0-2.5 s, the patient's at 3.5-5.0 s.
PCM = _silence(1.0) + _tone(1.5, 220.0) + _silence(1.0) + _tone(1.5, 2600.0) + _silence(1.0)
SECONDS = len(PCM) / (SAMPLE_RATE * BYTES_PER_SAMPLE)


def amplitude_vad(frame: bytes) -> float:
    samples = struct.unpack(f"<{len(frame) // 2}h", frame)
    return 0.95 if max(abs(s) for s in samples) > 1000 else 0.02


class _ScriptedProvider:
    """One packed window holds both turns (the gap is under the break): the
    window starts at the first tone, so the clinician's words sit at
    0.2-1.2 s and the patient's at 2.7-3.8 s of it."""

    model_name = "scripted"

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        words: list[TranscribedWord] = []
        for text, start, end in ((CLINICIAN, 0.2, 1.2), (PATIENT, 2.7, 3.8)):
            tokens = text.split()
            step = (end - start) / len(tokens)
            words += [
                TranscribedWord(token, start + i * step, start + (i + 1) * step, 0.95)
                for i, token in enumerate(tokens)
            ]
        return words


def _words(text: str, *, low: frozenset[str] = frozenset()) -> tuple[TranscriptWord, ...]:
    return tuple(
        TranscriptWord(
            word_text=token,
            start_seconds=index * 0.1,
            end_seconds=index * 0.1 + 0.08,
            probability=0.3 if token in low else 0.95,
            uncertain=token in low,
        )
        for index, token in enumerate(text.split())
    )


def _document(
    session_id: str,
    patient: str = PATIENT_KEPT,
    *,
    low: frozenset[str] = frozenset(),
    model_name: str = "small",
    clinician: str = CLINICIAN,
    speakers: tuple[str, str] = ("speaker_1", "speaker_2"),
) -> TranscriptDocument:
    return TranscriptDocument(
        session_id=session_id,
        created_at=NOW,
        model_name=model_name,
        sample_rate=SAMPLE_RATE,
        transcript_segments=(
            TranscriptSegment(
                start_seconds=1.0,
                end_seconds=2.5,
                speaker=speakers[0],
                transcript_words=_words(clinician, low=low),
            ),
            TranscriptSegment(
                start_seconds=3.5,
                end_seconds=5.0,
                speaker=speakers[1],
                transcript_words=_words(patient, low=low),
            ),
        ),
    )


def _saved_note(document: TranscriptDocument) -> GeneratedNote:
    """The clinician's saved note, as the app would have made it with the
    clinician confirmed (shipped defaults)."""
    # A folder that does not exist holds no override: shipped defaults.
    config = load_note_config(Path(tempfile.gettempdir()) / "replay-test-no-config")
    draft = compose_draft(
        document,
        config,
        extractive_provider_from_config(config),
        None,
        clinician_speaker="speaker_1",
        decided_at=NOW,
    )
    return finalise_note(draft, confirm_all(draft, NOW), document, config, created_at=NOW)


def _present(note: GeneratedNote) -> set[str]:
    return {s.section_key for s in note.note_sections if s.note_assertions}


def _kept_entry(
    store: PastSessionStore,
    *,
    audio: bool = True,
    saved: bool = True,
    commit: bool = True,
    document: TranscriptDocument | None = None,
) -> str:
    session_id = os.urandom(16).hex() if document is None else document.session_id
    document = _document(session_id) if document is None else document
    source = ArchiveSource(
        session_id=session_id,
        created_at=NOW.timestamp() - 1200,
        transcript_plain=document.to_bytes(),
        note_plain=_saved_note(document).to_bytes() if saved else None,
        generated_plain=None,
        audio_chunks=iter([PCM[i : i + 32_000] for i in range(0, len(PCM), 32_000)])
        if audio
        else None,
    )
    store.write_entry(source, LABEL)
    if commit:
        assert store.commit(session_id)
    return session_id


@dataclass
class _Exclusion:
    state: str
    released: list[str] = field(default_factory=list)


@pytest.fixture(autouse=True)
def _dev_and_private_temp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The developer channel (the tool's only one) and a private system temp
    folder, so the temporary stores are this test's own."""
    use_channel(monkeypatch, "dev")
    folder = tmp_path / "system-temp"
    folder.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(folder))
    return folder


def _temp_stores() -> set[Path]:
    return {p for p in Path(tempfile.gettempdir()).iterdir() if p.name.startswith(TEMP_DIR_PREFIX)}


class _Seams:
    """The injected exclusion, store and models for one test."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, state: str = "acquired") -> None:
        self.exclusion = _Exclusion(state)
        self.acquired = 0
        self.loaded = 0
        self.enrolment: speaker_eval.EnrolmentInputs | None = None
        # Every entry key the run unwrapped, by session id (round 29 MED-001:
        # only a replayed entry is opened).
        self.unwrapped: list[str] = []

        def acquire() -> _Exclusion:
            self.acquired += 1
            return self.exclusion

        def release(exclusion: Any) -> None:
            exclusion.released.append("released")

        def unwrap(directory: Path) -> SessionCrypto:
            assert not self.exclusion.released, "the exclusion was released mid-run"
            self.unwrapped.append(directory.name)
            return _fake_unwrap(directory)

        def open_store(folder: Path) -> PastSessionStore:
            return PastSessionStore(folder, wrap_key=_fake_wrap, unwrap_key=unwrap)

        def load(model_name: str, enrolment_wav: Path | None) -> replay_kept.ReplayModels:
            assert_offline_env()  # no model is built before the switches are on
            # Round 31 MED-004: the exclusion is HELD while the run works.
            assert not self.exclusion.released, "the exclusion was released mid-run"
            self.loaded += 1
            return replay_kept.ReplayModels(
                _ReplayProvider(_ScriptedProvider()), amplitude_vad, model_name, self.enrolment
            )

        def no_key_file(*args: object, **kwargs: object) -> None:
            raise AssertionError("the replay's temporary store must keep its key in memory")

        monkeypatch.setattr(replay_kept, "_acquire_exclusion", acquire)
        monkeypatch.setattr(replay_kept, "_release_exclusion", release)
        monkeypatch.setattr(replay_kept, "_open_store", open_store)
        # Round 30 MED-003: the call site's ``persist_key=False`` is pinned —
        # a replay that wrapped its temporary key to disk fails every run.
        monkeypatch.setattr(speaker_eval, "wrap_key_to_file", no_key_file)
        monkeypatch.setattr(replay_kept, "_load_models", load)
        monkeypatch.setattr(replay_kept, "whisper_model_available", lambda name: True)
        monkeypatch.setattr(replay_kept, "vad_model_available", lambda: True)

    @property
    def released(self) -> int:
        return len(self.exclusion.released)


def _no_content(out: str) -> None:
    for word in CONTENT_WORDS:
        assert word not in out


def _output(capsys: pytest.CaptureFixture[str]) -> str:
    """Both streams (round 29 LOW-012): nothing may leak on stderr either."""
    captured = capsys.readouterr()
    return captured.out + captured.err


def _snapshot(folder: Path) -> dict[str, tuple[int, str] | None]:
    """Every path under ``folder`` with its size and content hash (round 29
    LOW-010: the tool must change no byte, not merely no name)."""
    return {
        str(path.relative_to(folder)): (
            (path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest())
            if path.is_file()
            else None
        )
        for path in folder.rglob("*")
    }


def _run_lines(out: str) -> list[str]:
    return [line for line in out.splitlines() if line.startswith("[run ] ")]


# ---------------------------------------------------------------------------
# The metrics on fixed inputs
# ---------------------------------------------------------------------------


class TestTranscriptWer:
    def test_a_substitution_and_a_deletion(self) -> None:
        words = transcript_wer(["a", "b", "c", "d"], ["a", "x", "c"])
        assert words == WordErrors(4, 3, 2)
        assert words.rate == 0.5

    def test_identical_and_empty_sequences(self) -> None:
        assert transcript_wer(["a", "b"], ["a", "b"]) == WordErrors(2, 2, 0)
        assert transcript_wer([], ["a"]) == WordErrors(0, 1, 1)
        assert transcript_wer([], []) == WordErrors(0, 0, 0)

    def test_one_optimal_path_pairs_aligned_words(self) -> None:
        alignment = align_transcripts(["a", "b", "c", "d"], ["a", "x", "c"])
        assert alignment.words == WordErrors(4, 3, 2)
        assert alignment.pairs == ((0, 0), (1, 1), (2, 2))
        inserted = align_transcripts(["a", "c"], ["a", "b", "c"])
        assert inserted.pairs == ((0, 0), (1, 2))
        assert align_transcripts([], []).pairs == ()

    def test_the_backtrace_prefers_the_diagonal_then_a_deletion(self) -> None:
        """Round 30 LOW: two optimal paths — substitute b/c and delete a
        (diagonal first), or delete b and substitute a/c."""
        assert align_transcripts(["a", "b"], ["c"]).pairs == ((1, 0),)
        assert align_transcripts(["c"], ["a", "b"]).pairs == ((0, 1),)
        # Round 31 LOW: at the end no diagonal is optimal but a deletion and
        # an insertion both are — the deletion is taken (an insertion first
        # would give ((1, 0), (2, 1))).
        assert align_transcripts(["a", "b", "a"], ["b", "a", "b"]).pairs == ((0, 1), (1, 2))
        assert transcript_wer(["a", "b"], ["c"]) == WordErrors(2, 1, 2)


class TestLabelAgreement:
    def test_the_best_one_to_one_mapping_is_used(self) -> None:
        swapped = [
            ("speaker_1", "speaker_2"),
            ("speaker_1", "speaker_2"),
            ("speaker_2", "speaker_1"),
        ]
        assert replay_kept.label_agreement(swapped) == 1.0
        assert replay_kept.label_agreement([("a", "x"), ("a", "y"), ("b", "x")]) == 2 / 3

    def test_unequal_label_counts(self) -> None:
        assert replay_kept.label_agreement([("a", "x"), ("a", "y"), ("a", "y")]) == 2 / 3
        assert replay_kept.label_agreement([("a", "x"), ("b", "x"), ("c", "x")]) == 1 / 3

    def test_nothing_aligned_or_too_many_labels_is_none(self) -> None:
        assert replay_kept.label_agreement([]) is None
        many = [(f"k{i}", f"n{i}") for i in range(replay_kept.MAX_MAPPED_LABELS + 1)]
        assert replay_kept.label_agreement(many) is None

    def test_the_limit_is_inclusive_and_either_side_exceeding_it_is_none(self) -> None:
        """Round 30 LOW: the boundary — exactly ``MAX_MAPPED_LABELS`` a
        side is mapped; one more on EITHER side is not."""
        limit = replay_kept.MAX_MAPPED_LABELS
        assert replay_kept.label_agreement([(f"k{i}", f"n{i}") for i in range(limit)]) == 1.0
        assert replay_kept.label_agreement([(f"k{i}", "n") for i in range(limit + 1)]) is None
        assert replay_kept.label_agreement([("k", f"n{i}") for i in range(limit + 1)]) is None


class TestNoteDrift:
    """Task 4.1b: the harness's own pipeline over shipped defaults."""

    def _config(self, tmp_path: Path) -> Any:
        empty = tmp_path / "empty-config"
        empty.mkdir()
        return load_note_config(empty)

    def test_extraction_reaches_a_section_and_both_role_policies(self, tmp_path: Path) -> None:
        config = self._config(tmp_path)
        document = _document("a" * 32)
        saved = _saved_note(document)
        assert _present(saved) >= {"presenting_complaint"}
        assert len(_present(saved)) == 2  # the clinician's line reached its own section
        unresolved = replay_kept.note_drift(
            document, config, saved, clinician_speaker=None, now=NOW
        )
        confirmed = replay_kept.note_drift(
            document, config, saved, clinician_speaker="speaker_1", now=NOW
        )
        # Without a confirmed clinician the clinician-owned section stays
        # empty; the patient's line still reaches the presenting complaint.
        assert unresolved == replay_kept.NoteDrift(errors=0, reviews=0, sections_missing=1)
        assert confirmed == replay_kept.NoteDrift(errors=0, reviews=0, sections_missing=0)

    def test_no_saved_note_is_a_dash_not_a_number(self, tmp_path: Path) -> None:
        drift = replay_kept.note_drift(
            _document("a" * 32), self._config(tmp_path), None, clinician_speaker=None, now=NOW
        )
        assert drift.sections_missing is None

    def test_checker_warnings_are_counted_by_severity(self, tmp_path: Path) -> None:
        """A low-confidence word carried into the note draws Check 1's
        ``low_confidence_source`` review warning."""
        document = _document("a" * 32, low=frozenset({"hurts"}))
        drift = replay_kept.note_drift(
            document, self._config(tmp_path), None, clinician_speaker="speaker_1", now=NOW
        )
        assert (drift.errors, drift.reviews) == (0, 1)

    def test_errors_and_reviews_are_counted_apart(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 29 LOW-014: a non-zero error count reaches the row (the
        synthetic content draws no error-severity warning of its own)."""
        warnings = [SimpleNamespace(severity=s) for s in ("error", "review", "error")]
        monkeypatch.setattr(replay_kept, "check_note", lambda note, document, config: warnings)
        drift = replay_kept.note_drift(
            _document("a" * 32), self._config(tmp_path), None, clinician_speaker=None, now=NOW
        )
        assert (drift.errors, drift.reviews) == (2, 1)

    def test_the_detected_prefill_is_passed_to_the_draft(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 31 LOW: the harness's own step — the earliest detected
        prefill (the shipped defaults detect none, so a stand-in is used)."""
        document = _document("a" * 32)
        config = self._config(tmp_path)
        seen: list[object] = []

        class _Stop(Exception):
            pass

        def detect(doc: TranscriptDocument, cfg: object) -> str:
            seen.append(doc)
            return "stand-in-prefill"

        def draft(*args: object, **kwargs: object) -> object:
            seen.append(kwargs["prefill_id"])
            raise _Stop

        monkeypatch.setattr(replay_kept, "first_detected_prefill", detect)
        monkeypatch.setattr(replay_kept, "compose_draft", draft)
        with pytest.raises(_Stop):
            replay_kept.note_drift(document, config, None, clinician_speaker=None, now=NOW)
        assert seen == [document, "stand-in-prefill"]


class TestKeptSessionIds:
    """Round 29 MED-001: the tool lists the kept recordings without opening
    any entry (the label holds the patient's name)."""

    def test_listing_unwraps_no_entry_key(self, tmp_path: Path) -> None:
        folder = tmp_path / "past_sessions"
        store = _store(folder)
        kept = _kept_entry(store)
        _kept_entry(store, audio=False)
        unwrapped: list[Path] = []

        def counted(directory: Path) -> SessionCrypto:
            unwrapped.append(directory)
            return _fake_unwrap(directory)

        listing = PastSessionStore(folder, wrap_key=_fake_wrap, unwrap_key=counted)
        assert listing.kept_session_ids() == [kept]
        assert unwrapped == []

    def test_only_a_committed_entry_still_holding_its_recording_is_listed(
        self, tmp_path: Path
    ) -> None:
        """Round 30 MED-004: a pending entry, a deleted recording (its audio
        key zeroed, or gone beside its audio) and an entry with no entry key
        are not replayed."""
        folder = tmp_path / "past_sessions"
        store = _store(folder)
        kept = _kept_entry(store)
        _kept_entry(store, commit=False)  # pending
        zeroed = _kept_entry(store)
        key = folder / zeroed / AUDIO_KEY_FILENAME
        key.write_bytes(b"\0" * len(key.read_bytes()))
        gone = _kept_entry(store)
        (folder / gone / AUDIO_KEY_FILENAME).unlink()
        keyless = _kept_entry(store)
        (folder / keyless / KEY_FILENAME).unlink()
        assert store.kept_session_ids() == [kept]

    def test_a_missing_archive_is_empty_and_an_unlistable_one_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _store(tmp_path / "absent").kept_session_ids() == []
        folder = tmp_path / "past_sessions"
        store = _store(folder)
        _kept_entry(store)
        real_iterdir = Path.iterdir

        def refuse(self: Path) -> Any:
            if self.name == folder.name:  # by name: the store may normalise the path
                raise PermissionError("denied")
            return real_iterdir(self)

        monkeypatch.setattr(Path, "iterdir", refuse)
        with pytest.raises(PastSessionError) as info:
            store.kept_session_ids()
        assert info.value.reason == "unreadable"


class TestReadReplayInputs:
    """Round 31 MED-001: the replay's reader — the transcript and the saved
    note, never the label (the patient's name) or the generated note, and the
    entry key destroyed on every path."""

    def _store(self, folder: Path, handed: list[SessionCrypto]) -> PastSessionStore:
        def unwrap(directory: Path) -> SessionCrypto:
            crypto = _fake_unwrap(directory)
            handed.append(crypto)
            return crypto

        return PastSessionStore(folder, wrap_key=_fake_wrap, unwrap_key=unwrap)

    def test_the_transcript_and_saved_note_and_nothing_else(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        folder = tmp_path / "past_sessions"
        with_note = _kept_entry(_store(folder))
        without = _kept_entry(_store(folder), saved=False)
        handed: list[SessionCrypto] = []
        store = self._store(folder, handed)

        def never(*args: object) -> object:
            raise AssertionError("the replay reader decrypted the label or the generated note")

        monkeypatch.setattr(PastSessionStore, "_decode_label", staticmethod(never))
        monkeypatch.setattr(past_sessions, "read_generated", never)
        transcript, saved = store.read_replay_inputs(with_note)
        assert transcript.session_id == with_note and saved is not None
        transcript, saved = store.read_replay_inputs(without)
        assert transcript.session_id == without and saved is None
        assert len(handed) == 2 and all(crypto.destroyed for crypto in handed)

    def test_its_refusals_and_the_key_destroyed_on_failure(self, tmp_path: Path) -> None:
        folder = tmp_path / "past_sessions"
        pending = _kept_entry(_store(folder), commit=False)
        damaged = _kept_entry(_store(folder))
        (folder / damaged / TRANSCRIPT_FILENAME).write_bytes(b"\0" * 64)
        handed: list[SessionCrypto] = []
        store = self._store(folder, handed)
        for session_id, reason in (
            ("f" * 32, "not_found"),
            (pending, "pending"),
            (damaged, "unreadable"),
        ):
            with pytest.raises(PastSessionError) as info:
                store.read_replay_inputs(session_id)
            assert info.value.reason == reason
        assert len(handed) == 1 and handed[0].destroyed  # only the damaged one opened

    def test_a_key_that_does_not_unwrap_is_unreadable(self, tmp_path: Path) -> None:
        folder = tmp_path / "past_sessions"
        sid = _kept_entry(_store(folder))
        (folder / sid / KEY_FILENAME).write_bytes(b"not an entry key")
        with pytest.raises(PastSessionError) as info:
            _store(folder).read_replay_inputs(sid)
        assert info.value.reason == "unreadable"


class TestReport:
    def _row(self, **overrides: Any) -> replay_kept.ReplayRow:
        values: dict[str, Any] = {
            "session_id": "a" * 32,
            "seconds": 6.0,
            "kept_model": "small",
            "new_model": "medium",
            "kept_words": 10,
            "new_words": 9,
            "edit_distance": 1,
            "agreement": 1.0,
            "note": replay_kept.NoteDrift(0, 2, None),
        }
        values.update(overrides)
        return replay_kept.ReplayRow(**values)

    def test_the_header_says_drift_and_shipped_defaults(self) -> None:
        report = replay_kept.render_report(
            [self._row()], folder=Path("X:/f"), model_name="medium", enrolled=False,
            errors=0, skipped=0,
        )
        assert "DRIFT, not accuracy" in report
        assert "shipped defaults - drift includes your learned cues" in report
        assert "unresolved (no --enrolment" in report
        row = f"| {'a' * 32} | 6.0 | small | medium | 10 | 9 | 1 | 0.100 | 1.000 | - | 0 | 2 |"
        assert row in report
        assert "pooled drift WER 0.100 (1 edits over 10 kept words)" in report

    def test_the_totals_pool_edits_over_kept_words(self) -> None:
        """Round 30 LOW: pooled over the rows' words, not the mean of rates
        (which would read 0.050 here)."""
        report = replay_kept.render_report(
            [self._row(), self._row(session_id="b" * 32, kept_words=30, edit_distance=0)],
            folder=Path("X:/f"), model_name="medium", enrolled=False, errors=1, skipped=2,
        )
        assert (
            "Totals: 2 replayed, 1 error(s), 2 skipped; 12.0 s of audio; pooled drift WER "
            "0.025 (1 edits over 40 kept words)."
        ) in report

    def test_a_model_name_not_shaped_as_one_is_not_printed(self) -> None:
        report = replay_kept.render_report(
            [self._row(kept_model="Jane Citizen", kept_words=0, agreement=None)],
            folder=Path("X:/f"), model_name="medium", enrolled=True, errors=0, skipped=0,
        )
        assert "Jane" not in report and "(unnamed)" in report
        assert "the practitioner-attributed label (--enrolment)" in report
        assert "| 0 | 9 | 1 | - | - |" in report  # no kept words: no rate


# ---------------------------------------------------------------------------
# main: the run and its refusals
# ---------------------------------------------------------------------------


def _load_launcher() -> ModuleType:
    path = REPO / "scripts" / "replay-kept-recordings.py"
    spec = importlib.util.spec_from_file_location("replay_kept_recordings", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestMain:
    def test_the_launcher_is_thin_and_prints_usage(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        launcher = _load_launcher()
        assert launcher.main is replay_kept.main
        with pytest.raises(SystemExit) as info:
            launcher.main(["--help"])
        assert info.value.code == 0
        out = capsys.readouterr().out
        assert "usage:" in out and "ClinikoScribe" not in out

    def test_a_kept_recording_is_replayed_into_a_numbers_only_row(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pytest.importorskip("numpy")
        folder = tmp_path / "past_sessions"
        store = _store(folder)
        sid = _kept_entry(store)
        _kept_entry(store, audio=False)  # an entry with no kept recording is not replayed
        seams = _Seams(monkeypatch)
        configs: list[tuple[Path, list[str]]] = []
        real_load_config = replay_kept.load_note_config

        def spy(directory: Path) -> Any:
            configs.append((directory, sorted(p.name for p in directory.iterdir())))
            return real_load_config(directory)

        monkeypatch.setattr(replay_kept, "load_note_config", spy)
        before = _snapshot(folder)
        assert replay_kept.main([str(folder)]) == 0
        out = _output(capsys)
        kept = len(content_tokens(CLINICIAN)) + len(content_tokens(PATIENT_KEPT))
        row = (
            f"| {sid} | {SECONDS:.1f} | small | scripted | {kept} | {kept - 1} | 1 "
            f"| {1 / kept:.3f} | 1.000 | 1 | 0 | 0 |"
        )
        assert row in out
        assert out.count(" | small | scripted | ") == 1
        assert "Totals: 1 replayed, 0 error(s), 0 skipped" in out
        _no_content(out)
        assert _snapshot(folder) == before  # not a byte changed in the folder
        assert _temp_stores() == set()  # the temporary store is gone
        assert (seams.acquired, seams.released) == (1, 1)
        # Round 29 MED-001: only the replayed entry's key was unwrapped.
        assert set(seams.unwrapped) == {sid}
        # Round 29 LOW-014: the note config is the shipped defaults — an
        # EMPTY temporary folder of the tool's own, gone afterwards.
        [(config_dir, contents)] = configs
        assert config_dir.name.startswith(replay_kept.CONFIG_TEMP_PREFIX)
        assert contents == [] and not config_dir.exists()

    @pytest.mark.parametrize("one_kept_speaker", [True, False])
    def test_the_row_compares_the_kept_labels_with_the_new_and_the_note_uses_the_new(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        one_kept_speaker: bool,
    ) -> None:
        """Round 30 MED-001/MED-002: an extra kept word EARLY offsets the
        aligned pairs (i != j), and the note leg must be handed the NEW
        transcript. With ONE kept speaker the new labels must be read (the
        agreement is below 1); with the kept speakers matching the new ones
        (round 31 MED-002) the KEPT label must be read at the kept index — at
        the new index the first patient word would read "today"'s label."""
        pytest.importorskip("numpy")
        folder = tmp_path / "past_sessions"
        sid = os.urandom(16).hex()
        kept_doc = _document(
            sid,
            patient=PATIENT,
            clinician="The plan is gentle home exercise today.",
            speakers=("speaker_1", "speaker_1" if one_kept_speaker else "speaker_2"),
        )
        _kept_entry(_store(folder), document=kept_doc)
        _Seams(monkeypatch)
        handed: list[tuple[str, str | None]] = []
        real_drift = replay_kept.note_drift

        def spy(document: TranscriptDocument, *args: Any, **kwargs: Any) -> replay_kept.NoteDrift:
            handed.append((document.model_name, kwargs["clinician_speaker"]))
            return real_drift(document, *args, **kwargs)

        monkeypatch.setattr(replay_kept, "note_drift", spy)
        assert replay_kept.main([str(folder)]) == 0
        out = _output(capsys)
        clinician, patient = len(content_tokens(CLINICIAN)), len(content_tokens(PATIENT))
        new = clinician + patient
        line = next(line for line in out.splitlines() if line.startswith(f"| {sid} |"))
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert cells[4:8] == [str(new + 1), str(new), "1", f"{1 / (new + 1):.3f}"]
        if one_kept_speaker:
            # Every new word aligned; the one kept label maps to the larger turn.
            assert cells[8] == f"{max(clinician, patient) / new:.3f}"
            assert float(cells[8]) < 1.0
        else:
            assert cells[8] == "1.000"
        assert handed == [("scripted", None)]

    def test_an_unreadable_name_label_does_not_stop_a_replay(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Round 30: the replay never decrypts the label (the patient's
        name), so a damaged one changes nothing."""
        pytest.importorskip("numpy")
        folder = tmp_path / "past_sessions"
        sid = _kept_entry(_store(folder))
        (folder / sid / LABEL_FILENAME).write_bytes(b"\0" * 64)
        _Seams(monkeypatch)
        assert replay_kept.main([str(folder)]) == 0
        assert f"| {sid} |" in _output(capsys)

    def test_with_enrolment_the_clinician_is_the_attributed_label(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pytest.importorskip("numpy")
        folder = tmp_path / "past_sessions"
        sid = _kept_entry(_store(folder))
        seams = _Seams(monkeypatch)
        seams.enrolment = speaker_eval.enrolment_inputs(  # the clinician's tone
            _tone(2.0, 220.0), FrequencyEmbedder(), amplitude_vad
        )
        handed: list[tuple[str | None, str | None]] = []
        real_drift = replay_kept.note_drift

        def spy(document: TranscriptDocument, *args: Any, **kwargs: Any) -> replay_kept.NoteDrift:
            handed.append((document.enrolled_speaker, kwargs["clinician_speaker"]))
            return real_drift(document, *args, **kwargs)

        monkeypatch.setattr(replay_kept, "note_drift", spy)
        assert replay_kept.main([str(folder)]) == 0
        out = _output(capsys)
        assert "the practitioner-attributed label (--enrolment)" in out
        line = next(line for line in out.splitlines() if line.startswith(f"| {sid} |"))
        assert line.endswith("| 1.000 | 0 | 0 | 0 |")  # nothing missing from the saved note
        _no_content(out)
        # Round 31 MED-003: the note is made from the ENROLLED document (the
        # plain one names no enrolled speaker), its clinician that speaker.
        [(enrolled_speaker, clinician)] = handed
        assert enrolled_speaker is not None and clinician == enrolled_speaker

    def test_only_selects_and_reports_an_id_with_no_kept_recording(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pytest.importorskip("numpy")
        folder = tmp_path / "past_sessions"
        store = _store(folder)
        first, second = _kept_entry(store), _kept_entry(store)
        absent = "f" * 32
        _Seams(monkeypatch)
        assert replay_kept.main([str(folder), "--only", second, "--only", absent]) == 0
        out = _output(capsys)
        assert f"| {second} |" in out and f"| {first} |" not in out
        assert f"[skip] {absent}: no kept recording in this folder" in out
        assert "1 skipped" in out

    def test_a_repeated_only_id_is_counted_once(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pytest.importorskip("numpy")
        folder = tmp_path / "past_sessions"
        sid = _kept_entry(_store(folder))
        _Seams(monkeypatch)
        absent = "f" * 32
        argv = [str(folder), "--only", sid, "--only", sid, "--only", absent, "--only", absent]
        assert replay_kept.main(argv) == 0
        out = _output(capsys)
        assert _run_lines(out) == [f"[run ] {sid}"]
        assert out.count(f"[skip] {absent}") == 1
        assert "Totals: 1 replayed, 0 error(s), 1 skipped" in out

    def test_an_entry_with_no_saved_note_is_replayed_with_a_dash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Round 31 MED-001: a kept entry completed without a saved note."""
        pytest.importorskip("numpy")
        folder = tmp_path / "past_sessions"
        sid = _kept_entry(_store(folder), saved=False)
        _Seams(monkeypatch)
        assert replay_kept.main([str(folder)]) == 0
        line = next(
            line for line in _output(capsys).splitlines() if line.startswith(f"| {sid} |")
        )
        assert line.endswith("| - | 0 | 0 |")

    def test_only_naming_no_kept_recording_replays_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        folder = tmp_path / "past_sessions"
        _kept_entry(_store(folder))
        seams = _Seams(monkeypatch)
        absent = "f" * 32
        assert replay_kept.main([str(folder), "--only", absent]) == 1
        out = _output(capsys)
        assert f"[skip] {absent}: no kept recording in this folder" in out
        assert "[error] no kept recordings to replay in " in out
        assert _run_lines(out) == [] and seams.unwrapped == [] and seams.released == 1

    def test_a_listing_failure_of_another_kind_is_refused_by_type(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        folder = tmp_path / "past_sessions"
        _kept_entry(_store(folder))
        seams = _Seams(monkeypatch)

        def refuse(self: PastSessionStore) -> list[str]:
            raise ValueError("Jane Citizen")

        monkeypatch.setattr(PastSessionStore, "kept_session_ids", refuse)
        assert replay_kept.main([str(folder)]) == 2
        out = _output(capsys)
        assert "cannot be listed (ValueError)" in out and "Jane" not in out
        assert seams.released == 1

    def test_a_reason_outside_the_closed_set_is_printed_as_its_type(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        folder = tmp_path / "past_sessions"
        sid = _kept_entry(_store(folder))
        _Seams(monkeypatch)

        def refuse(self: PastSessionStore, session_id: str) -> Any:
            raise PastSessionError("Jane Citizen")

        monkeypatch.setattr(PastSessionStore, "read_replay_inputs", refuse)
        assert replay_kept.main([str(folder)]) == 1
        out = _output(capsys)
        assert f"[error] {sid}: PastSessionError" in out and "Jane" not in out

    def test_an_unreadable_recording_is_an_error_by_reason_and_the_run_goes_on(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pytest.importorskip("numpy")
        folder = tmp_path / "past_sessions"
        store = _store(folder)
        broken, good = _kept_entry(store), _kept_entry(store)
        audio = folder / broken / "audio.enc"
        audio.write_bytes(audio.read_bytes()[:-40])  # a damaged tail
        _Seams(monkeypatch)
        assert replay_kept.main([str(folder)]) == 1
        out = _output(capsys)
        (error,) = [line for line in out.splitlines() if line.startswith(f"[error] {broken}: ")]
        assert error.removeprefix(f"[error] {broken}: ") in PAST_SESSION_REASONS
        assert f"| {good} |" in out
        assert "Totals: 1 replayed, 1 error(s), 0 skipped" in out
        _no_content(out)

    def test_any_other_failure_is_reported_by_type_and_the_run_goes_on(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Round 29 LOW-013: the exception's text (here a name) is never
        printed — only its type."""
        pytest.importorskip("numpy")
        folder = tmp_path / "past_sessions"
        store = _store(folder)
        first, second = sorted((_kept_entry(store), _kept_entry(store)))
        seams = _Seams(monkeypatch)
        real_drift = replay_kept.note_drift
        calls: list[int] = []

        def drift_once_failing(*args: Any, **kwargs: Any) -> replay_kept.NoteDrift:
            calls.append(1)
            if len(calls) == 1:
                raise ValueError("Jane Citizen")
            return real_drift(*args, **kwargs)

        monkeypatch.setattr(replay_kept, "note_drift", drift_once_failing)
        assert replay_kept.main([str(folder)]) == 1
        out = _output(capsys)
        assert f"[error] {first}: ValueError" in out
        assert f"| {second} |" in out and f"| {first} |" not in out
        assert "Totals: 1 replayed, 1 error(s), 0 skipped" in out
        _no_content(out)
        assert _temp_stores() == set()  # the failing entry's store went too
        assert seams.released == 1

    def test_a_teardown_failure_stops_the_run_naming_the_path_only(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """C6's one named exception: the custody diagnostic ``speaker_eval``
        composes — the temporary path, the key state, delete it by hand. The
        run STOPS: a second entry is never started (round 29 LOW-009)."""
        pytest.importorskip("numpy")
        folder = tmp_path / "past_sessions"
        store = _store(folder)
        _kept_entry(store)
        _kept_entry(store)
        seams = _Seams(monkeypatch)

        def refuse(path: Path) -> None:
            raise PermissionError("refused")

        monkeypatch.setattr(speaker_eval, "_remove_tree", refuse)
        assert replay_kept.main([str(folder)]) == 1
        out = _output(capsys)
        assert len(_run_lines(out)) == 1
        assert "[custody] the run stopped: temporary store not fully removed:" in out
        assert TEMP_DIR_PREFIX in out and "delete the directory by hand now" in out
        assert "its key was destroyed; what remains is ciphertext" in out
        assert "| " not in out  # no report
        _no_content(out)
        assert seams.released == 1
        roots = _temp_stores()
        assert len(roots) == 1
        for root in roots:
            assert not list(root.rglob(KEY_FILENAME))  # memory-only: no key on disk
            shutil.rmtree(root)

    def test_an_interrupt_mid_run_prints_no_report_and_releases(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Round 29 LOW-013: Ctrl+C during a replay."""
        folder = tmp_path / "past_sessions"
        store = _store(folder)
        _kept_entry(store)
        _kept_entry(store)
        seams = _Seams(monkeypatch)

        def interrupted(*args: object) -> replay_kept.ReplayRow:
            raise KeyboardInterrupt

        monkeypatch.setattr(replay_kept, "_replay_entry", interrupted)
        assert replay_kept.main([str(folder)]) == 1
        out = _output(capsys)
        assert len(_run_lines(out)) == 1
        assert "[stopped] the run was interrupted, so there is no report" in out
        assert f"(%TEMP%) for a {TEMP_DIR_PREFIX}* folder" in out
        assert "| " not in out and "Totals:" not in out
        assert seams.released == 1

    def test_an_interrupt_while_the_models_load_runs_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        folder = tmp_path / "past_sessions"
        _kept_entry(_store(folder))
        seams = _Seams(monkeypatch)

        def interrupted(model_name: str, enrolment_wav: Path | None) -> replay_kept.ReplayModels:
            raise KeyboardInterrupt

        monkeypatch.setattr(replay_kept, "_load_models", interrupted)
        assert replay_kept.main([str(folder)]) == 1
        out = _output(capsys)
        assert "[stopped] the run was interrupted while the models loaded" in out
        assert _run_lines(out) == [] and "| " not in out
        assert seams.unwrapped == [] and seams.released == 1

    def test_the_offline_switches_are_applied_before_the_models_load(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Round 29 LOW-011: EVERY switch absent and a forbidden override
        inherited — the load seam asserts the offline contract itself."""
        pytest.importorskip("numpy")
        folder = tmp_path / "past_sessions"
        _kept_entry(_store(folder))
        seams = _Seams(monkeypatch)
        for key in OFFLINE_ENV:
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("LLAMA_CPP_LIB_PATH", str(tmp_path / "elsewhere"))
        assert replay_kept.main([str(folder)]) == 0
        assert all(os.environ.get(key) == value for key, value in OFFLINE_ENV.items())
        assert "LLAMA_CPP_LIB_PATH" not in os.environ
        assert seams.loaded == 1 and seams.released == 1
        _no_content(_output(capsys))


class TestRefusals:
    def test_a_folder_holding_no_entry_key_is_not_a_past_sessions_folder(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        seams = _Seams(monkeypatch)
        folder = tmp_path / "not-an-archive"
        (folder / ("a" * 32)).mkdir(parents=True)  # an id-shaped folder with no key
        (folder / "notes.txt").write_text("x", encoding="utf-8")
        assert replay_kept.main([str(folder)]) == 2
        assert "is not a Past-sessions folder" in _output(capsys)
        assert seams.acquired == 0  # refused before the exclusion is taken

    def test_a_path_that_is_not_a_folder_is_refused_and_never_echoed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Round 30: a mistyped folder argument could be anything — a name."""
        seams = _Seams(monkeypatch)
        assert replay_kept.main([str(tmp_path / "Jane Citizen")]) == 2
        out = _output(capsys)
        assert "[refused] the path given is not a folder" in out and "Jane" not in out
        assert seams.acquired == 0

    def test_a_non_id_folder_holding_a_key_is_not_an_entry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        seams = _Seams(monkeypatch)
        folder = tmp_path / "not-an-archive"
        (folder / "some-folder").mkdir(parents=True)
        (folder / "some-folder" / KEY_FILENAME).write_bytes(b"x")
        assert replay_kept.main([str(folder)]) == 2
        assert "is not a Past-sessions folder" in _output(capsys)
        assert seams.acquired == 0

    def test_a_folder_that_cannot_be_scanned_is_refused_by_type(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        folder = tmp_path / "past_sessions"
        _kept_entry(_store(folder))
        seams = _Seams(monkeypatch)

        def refuse(path: object) -> Any:
            raise PermissionError("Jane Citizen")

        monkeypatch.setattr(replay_kept.os, "scandir", refuse)
        assert replay_kept.main([str(folder)]) == 2
        out = _output(capsys)
        assert "cannot be listed (PermissionError)" in out and "Jane" not in out
        assert seams.acquired == 0

    @pytest.mark.parametrize(
        ("argv", "expected"),
        [
            # Round 30 LOW: which refusal wins when several apply.
            (["--only", "Jane Citizen", "--model", "..\\x"], "--only (a value not shaped"),
            (["--model", "..\\x", "--enrolment", "absent.wav"], "--model: not a Whisper"),
            (["--enrolment", "absent.wav"], "--enrolment: not a file"),
        ],
    )
    def test_the_refusals_come_in_order(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        argv: list[str],
        expected: str,
    ) -> None:
        seams = _Seams(monkeypatch)
        # The folder is missing too: every case is refused before it.
        assert replay_kept.main([str(tmp_path / "absent"), *argv]) == 2
        out = _output(capsys)
        assert out.count("[refused]") == 1 and expected in out
        assert "absent" not in out and "Jane" not in out
        assert seams.acquired == 0

    def test_the_packaged_build_is_refused_before_any_other_input(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        use_channel(monkeypatch, "production")
        _Seams(monkeypatch)
        argv = [str(tmp_path / "absent"), "--only", "Jane Citizen", "--model", "..\\x"]
        assert replay_kept.main(argv) == 2
        out = _output(capsys)
        assert out.count("[refused]") == 1 and "only on the developer build" in out

    @pytest.mark.parametrize("state", ["already_running", "unavailable"])
    def test_only_an_acquired_exclusion_proceeds(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        state: str,
    ) -> None:
        folder = tmp_path / "past_sessions"
        _kept_entry(_store(folder))
        seams = _Seams(monkeypatch, state)

        def never(*args: object) -> int:
            raise AssertionError("nothing may run without the exclusion")

        monkeypatch.setattr(replay_kept, "_run", never)
        assert replay_kept.main([str(folder)]) == 2
        out = _output(capsys)
        assert "close Clinic Scribe first" in out and f"({state})" in out
        assert seams.released == 1

    def test_the_exclusion_is_released_when_the_run_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        folder = tmp_path / "past_sessions"
        _kept_entry(_store(folder))
        seams = _Seams(monkeypatch)

        def boom(*args: object) -> int:
            raise RuntimeError("unexpected")

        monkeypatch.setattr(replay_kept, "_run", boom)
        with pytest.raises(RuntimeError):
            replay_kept.main([str(folder)])
        assert seams.released == 1

    def test_a_non_id_only_value_is_refused_and_never_echoed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        folder = tmp_path / "past_sessions"
        _kept_entry(_store(folder))
        seams = _Seams(monkeypatch)
        assert replay_kept.main([str(folder), "--only", "Jane Citizen"]) == 2
        out = _output(capsys)
        assert replay_kept.UNNAMED_SESSION in out and "Jane" not in out
        assert seams.acquired == 0

    def test_a_model_value_that_is_not_a_name_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        folder = tmp_path / "past_sessions"
        _kept_entry(_store(folder))
        seams = _Seams(monkeypatch)
        assert replay_kept.main([str(folder), "--model", "..\\..\\x"]) == 2
        assert "--model: not a Whisper model name" in _output(capsys)
        assert seams.acquired == 0

    def test_a_command_line_it_cannot_parse_is_never_echoed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Round 29 LOW-001: an unquoted ``--only Jane Citizen`` leaves
        ``Citizen`` unparsed; argparse's own error would repeat it."""
        folder = tmp_path / "past_sessions"
        _kept_entry(_store(folder))
        seams = _Seams(monkeypatch)
        with pytest.raises(SystemExit) as info:
            replay_kept.main([str(folder), "--only", "Jane", "Citizen"])
        assert info.value.code == 2
        captured = capsys.readouterr()
        # Round 30 LOW: the usage (option names only) and the refusal, both
        # on stderr; nothing on stdout.
        assert captured.out == ""
        assert captured.err.startswith("usage:")
        assert "[refused] the command line was not understood - see --help" in captured.err
        assert "Jane" not in captured.err and "Citizen" not in captured.err
        assert seams.acquired == 0

    @pytest.mark.parametrize("missing", ["whisper", "whisper-named", "vad"])
    def test_a_missing_model_is_refused_without_a_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        missing: str,
    ) -> None:
        """Round 29 LOW-003: the remedy, never the models folder's path; and
        (round 30) a ``--model`` value is never echoed — only the default is
        named."""
        folder = tmp_path / "past_sessions"
        _kept_entry(_store(folder))
        seams = _Seams(monkeypatch)
        argv = [str(folder)]
        if missing == "vad":
            monkeypatch.setattr(replay_kept, "vad_model_available", lambda: False)
        else:
            monkeypatch.setattr(replay_kept, "whisper_model_available", lambda name: False)
        if missing == "whisper-named":
            argv += ["--model", "JaneCitizen"]
        assert replay_kept.main(argv) == 2
        out = _output(capsys)
        assert "is not installed in the developer build's models folder" in out
        assert str(install_layout.models_root()) not in out
        if missing == "whisper":
            assert "Whisper `medium` is not installed" in out
        if missing == "whisper-named":
            assert "Whisper named by --model is not installed" in out and "Jane" not in out
        assert seams.loaded == 0 and seams.released == 1

    def test_a_models_folder_that_cannot_be_located_is_refused_by_type(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        folder = tmp_path / "past_sessions"
        _kept_entry(_store(folder))
        seams = _Seams(monkeypatch)

        def refuse() -> Path:
            raise RuntimeError("C:\\Users\\Jane Citizen")

        monkeypatch.setattr(replay_kept.install_layout, "models_root", refuse)
        assert replay_kept.main([str(folder)]) == 2
        out = _output(capsys)
        assert "[refused] the models folder cannot be located (RuntimeError)" in out
        assert "Jane" not in out and seams.loaded == 0 and seams.released == 1

    def test_a_shipped_config_that_cannot_be_loaded_is_refused_by_type(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        folder = tmp_path / "past_sessions"
        _kept_entry(_store(folder))
        seams = _Seams(monkeypatch)

        def refuse(directory: Path) -> Any:
            raise OSError("C:\\Users\\Jane Citizen")

        monkeypatch.setattr(replay_kept, "load_note_config", refuse)
        assert replay_kept.main([str(folder)]) == 2
        out = _output(capsys)
        assert "[refused] the shipped default note config cannot be loaded (OSError)" in out
        assert "Jane" not in out and seams.loaded == 0 and seams.released == 1

    @pytest.mark.parametrize(
        ("raised", "expected"),
        [
            # Round 30 MED-005: model construction's own text could hold a path.
            (OSError("C:\\Users\\Jane Citizen\\models"), "(OSError)"),
            (EnrolmentError("too little speech: 1.2 s"), "(EnrolmentError): too little"),
        ],
    )
    def test_a_model_that_cannot_be_loaded_is_refused_by_type(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        raised: Exception,
        expected: str,
    ) -> None:
        folder = tmp_path / "past_sessions"
        _kept_entry(_store(folder))
        seams = _Seams(monkeypatch)

        def refuse(model_name: str, enrolment_wav: Path | None) -> replay_kept.ReplayModels:
            raise raised

        monkeypatch.setattr(replay_kept, "_load_models", refuse)
        assert replay_kept.main([str(folder)]) == 2
        out = _output(capsys)
        assert f"[refused] the models could not be loaded {expected}" in out
        assert "Jane" not in out and seams.unwrapped == [] and seams.released == 1

    def test_a_missing_enrolment_file_is_refused_before_anything_runs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Round 30: a mistyped WAV path must not read as a broken model."""
        folder = tmp_path / "past_sessions"
        _kept_entry(_store(folder))
        seams = _Seams(monkeypatch)
        wav = tmp_path / "Jane Citizen.wav"
        assert replay_kept.main([str(folder), "--enrolment", str(wav)]) == 2
        out = _output(capsys)
        assert "[refused] --enrolment: not a file" in out and "Jane" not in out
        assert seams.acquired == 0 and seams.loaded == 0

    def test_an_unusable_enrolment_wav_names_the_format_not_the_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Round 29 LOW-002: ``read_wav_pcm``'s text names the file."""
        folder = tmp_path / "past_sessions"
        _kept_entry(_store(folder))
        seams = _Seams(monkeypatch)

        def refuse(model_name: str, enrolment_wav: Path | None) -> replay_kept.ReplayModels:
            raise WavFormatError("Jane Citizen.wav: 44100 Hz stereo")

        monkeypatch.setattr(replay_kept, "_load_models", refuse)
        wav = tmp_path / "Jane Citizen.wav"
        wav.write_bytes(b"RIFF")  # present: the format is what is refused
        assert replay_kept.main([str(folder), "--enrolment", str(wav)]) == 2
        out = _output(capsys)
        assert "[refused] the models could not be loaded (WavFormatError): " in out
        assert f"the --enrolment WAV must be a {WAV_FORMAT_HELP}" in out
        assert "Jane" not in out and seams.unwrapped == [] and seams.released == 1

    def test_an_archive_that_cannot_be_listed_is_refused_by_reason(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        folder = tmp_path / "past_sessions"
        _kept_entry(_store(folder))
        seams = _Seams(monkeypatch)
        real_iterdir = Path.iterdir

        def refuse(self: Path) -> Any:
            if self.name == folder.name:  # by name: the store may normalise the path
                raise PermissionError("denied")
            return real_iterdir(self)

        monkeypatch.setattr(Path, "iterdir", refuse)
        assert replay_kept.main([str(folder)]) == 2
        out = _output(capsys)
        assert "cannot be listed (unreadable)" in out and "denied" not in out
        assert seams.unwrapped == [] and seams.released == 1

    def test_the_packaged_build_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        use_channel(monkeypatch, "production")
        seams = _Seams(monkeypatch)
        assert replay_kept.main([str(tmp_path)]) == 2
        assert "only on the developer build" in _output(capsys)
        assert seams.acquired == 0

    def test_the_real_exclusion_is_a_refusal_in_tests(self) -> None:
        """The conftest's sentinel: no test takes the app's real ``app.lock``."""
        with pytest.raises(AssertionError, match="real instance exclusion"):
            replay_kept._acquire_exclusion()

    def test_the_real_seams_pair_with_the_apps_exclusion(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 29 LOW-014: the unpatched seams take and release THE app's
        exclusion (its functions faked: no real ``app.lock`` is touched)."""
        from scribe_desktop import app

        held = app.InstanceExclusion("acquired", (7,))
        released: list[object] = []
        monkeypatch.setattr(app, "acquire_instance_exclusion", lambda: held)
        monkeypatch.setattr(app, "release_instance_exclusion", released.append)
        assert REAL_REPLAY_EXCLUSION() is held
        replay_kept._release_exclusion(held)
        assert released == [held]
        replay_kept._release_exclusion(_Exclusion("acquired"))  # not the app's: untouched
        assert released == [held]
