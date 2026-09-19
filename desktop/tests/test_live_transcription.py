"""Note-learning plan Phase 1, Tasks 1.0 + 1.1: the shared document assembly
and the live transcription worker.

Layers:
- ``assemble_transcript`` (Task 1.0): the batch path routes through it and the
  helper is deterministic over the recorded inputs (parity up to
  ``created_at``); the degenerate policy pins
- ``LiveSegmenter``: the VAD determinism pin against ``segment_probabilities``
  (random probability streams, defaults and a merging configuration), the
  D2 forced close at the lowest-probability frame, the retention floor
- ``_LiveWindows``: the incremental packer reproduces
  ``pack_transcription_windows`` under interleaved ticks
- ``LiveTranscriber`` (mock provider, amplitude VAD, no ML stack): live vs
  batch parity over the plan's inputs (empty, one segment, no profile,
  enrolled matches, textless cluster, two windows), the live document passing
  ``read_transcript``, the 90 s forced-close fixture with live posts, the
  queued-PCM cap during a blocked model load, fall-behind, the tee contract
  (``feed`` never raises), pause gating, stop semantics (bounded join, late
  posts dropped, buffers confirmed cleared), a cheap ``seal`` under a blocked
  tail, the last flushed chunk in the drained tail, VAD reset and D3 release

No clinical audio anywhere: fixtures are tones and silence.
"""

from __future__ import annotations

import random
import struct
import threading
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from scribe_desktop import transcription
from scribe_desktop.benchmark import apply_offline_env
from scribe_desktop.practitioner_profile import ConsentRecord, PractitionerProfile
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import KEY_FILENAME, SessionChunkStore
from scribe_desktop.speaker_embedding import MOCK_MODEL_ID, MockSpeakerEmbedder
from scribe_desktop.speech import (
    BYTES_PER_SAMPLE,
    FRAME_BYTES,
    FRAME_SECONDS,
    SAMPLE_RATE,
    MockSpeechProvider,
    SpeechSegment,
    TranscribedWord,
    iter_frames,
    segment_probabilities,
)
from scribe_desktop.transcription import (
    LIVE_SPEAKER_PENDING,
    SPEAKER_1,
    SPEAKER_2,
    LiveFailureKind,
    LiveResult,
    LiveSegmenter,
    LiveTranscriber,
    LiveTranscriptionError,
    LiveTranscriptionFailed,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
    _LiveWindows,
    assemble_transcript,
    extract_segment_pcm,
    pack_transcription_windows,
    read_transcript,
    transcribe_session,
    write_transcript,
)

CHUNK = 32_000  # the store fixture's chunk size (1 s of PCM16 at 16 kHz)


@pytest.fixture(autouse=True)
def _offline_env() -> None:
    apply_offline_env()


# ---------------------------------------------------------------------------
# fixtures (mirror test_transcription.py / test_attribution.py)
# ---------------------------------------------------------------------------


def tone_pcm(seconds: float, frequency: float = 440.0, amplitude: float = 0.5) -> bytes:
    import math

    count = int(seconds * SAMPLE_RATE)
    scale = amplitude * 32767
    return struct.pack(
        f"<{count}h",
        *(int(scale * math.sin(2 * math.pi * frequency * i / SAMPLE_RATE)) for i in range(count)),
    )


def silence_pcm(seconds: float) -> bytes:
    return b"\0" * (int(seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE)


def amplitude_vad(frame: bytes) -> float:
    samples = struct.unpack(f"<{len(frame) // 2}h", frame)
    peak = max(abs(s) for s in samples)
    return 0.95 if peak > 1000 else 0.02


def _chunks(pcm: bytes) -> list[bytes]:
    return [pcm[i : i + CHUNK] for i in range(0, len(pcm), CHUNK)]


def _make_store(session_dir: Path, pcm: bytes) -> SessionCrypto:
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / KEY_FILENAME).write_bytes(b"\0" * 64)
    crypto = SessionCrypto()
    store = SessionChunkStore.create(session_dir / "audio.enc", crypto, session_dir.name)
    for chunk in _chunks(pcm):
        store.append_chunk(chunk)
    store.finish()
    return crypto


E1 = (1.0, 0.0, 0.0, 0.0)
E2 = (0.0, 1.0, 0.0, 0.0)


def _profile(vector: Sequence[float] = E1) -> PractitionerProfile:
    now = datetime.now(UTC)
    return PractitionerProfile(
        model_id=MOCK_MODEL_ID,
        model_sha256="",
        embedding=tuple(float(v) for v in vector),
        embedding_dim=len(vector),
        created_at=now,
        enrolment_speech_seconds=30.0,
        device_name="test",
        consent=ConsentRecord(
            accepted_at=now, consent_text_version="consent-v1", learning_opt_in=False
        ),
    )


def _three_tones(*frequencies: float) -> bytes:
    gap = silence_pcm(1.0)
    pcm = gap
    for frequency in frequencies:
        pcm += tone_pcm(1.5, frequency=frequency) + gap
    return pcm


def _strip_created(document: TranscriptDocument) -> dict[str, Any]:
    data = document.model_dump()
    data.pop("created_at")
    return data


class _TextlessProvider:
    """Words for every window except the SECOND (a textless cluster)."""

    def __init__(self) -> None:
        self._inner = MockSpeechProvider()
        self.calls = 0

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        self.calls += 1
        if self.calls == 2:
            return []
        return self._inner.transcribe_segment(pcm, sample_rate)


class _BlockingProvider:
    """Every ``transcribe_segment`` waits on ``gate`` first."""

    def __init__(self, gate: threading.Event) -> None:
        self._gate = gate
        self._inner = MockSpeechProvider()
        self.calls = 0
        self.entered = threading.Event()

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        self.calls += 1
        self.entered.set()
        self._gate.wait()
        return self._inner.transcribe_segment(pcm, sample_rate)


class _ResettableVad:
    def __init__(self) -> None:
        self.resets = 0

    def reset(self) -> None:
        self.resets += 1

    def frame_probability(self, frame: bytes) -> float:
        return amplitude_vad(frame)


def _live(
    *,
    provider: Any = None,
    provider_factory: Callable[[], Any] | None = None,
    on_window: Callable[[tuple[TranscriptSegment, ...]], None] | None = None,
    attribution: Callable[[], Any] | None = None,
    **options: Any,
) -> LiveTranscriber:
    def default_factory() -> Any:
        return provider if provider is not None else MockSpeechProvider()

    factory = provider_factory or default_factory
    kwargs: dict[str, Any] = {}
    if attribution is not None:
        kwargs["attribution_factory"] = attribution
    return LiveTranscriber(
        provider_factory=factory,
        vad_factory=lambda: amplitude_vad,
        on_window=on_window,
        **kwargs,
        **options,
    )


def _run_live(pcm: bytes, live: LiveTranscriber) -> LiveResult:
    live.start()
    for chunk in _chunks(pcm):
        live.feed(chunk)
    live.seal()
    return live.drain()


def _wait(predicate: Callable[[], bool], timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("condition not reached in time")
        time.sleep(0.005)


# ---------------------------------------------------------------------------
# Task 1.0 — assemble_transcript
# ---------------------------------------------------------------------------


_BATCH_FIXTURES: dict[str, bytes] = {
    "silence": silence_pcm(2.0),
    "one_segment": silence_pcm(1.0) + tone_pcm(2.0) + silence_pcm(1.0),
    "one_window": _three_tones(440.0, 440.0, 440.0),
    "two_windows": tone_pcm(1.0) + silence_pcm(5.0) + tone_pcm(1.0),
    "two_voices": _three_tones(220.0, 2600.0, 220.0),
    "oversized": tone_pcm(31.0) + silence_pcm(0.5) + tone_pcm(1.0),
}


class TestAssembleTranscript:
    @pytest.mark.parametrize("name", sorted(_BATCH_FIXTURES))
    def test_batch_routes_through_the_helper_and_the_helper_is_deterministic(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
    ) -> None:
        """The batch document IS ``assemble_transcript`` over the loop's
        products: recording the call and replaying it through the real helper
        reproduces the document up to ``created_at``."""
        pytest.importorskip("numpy")
        recorded: list[dict[str, Any]] = []
        real = transcription.assemble_transcript

        def recording(**kwargs: Any) -> TranscriptDocument:
            recorded.append(kwargs)
            return real(**kwargs)

        monkeypatch.setattr(transcription, "assemble_transcript", recording)
        session_dir = tmp_path / ("a" * 32)
        crypto = _make_store(session_dir, _BATCH_FIXTURES[name])
        document = transcribe_session(session_dir, crypto, MockSpeechProvider(), amplitude_vad)
        assert len(recorded) == 1
        replayed = real(**recorded[0])
        assert _strip_created(replayed) == _strip_created(document)
        assert read_transcript(session_dir, crypto) == document

    def test_the_batch_signature_is_unchanged(self) -> None:
        import inspect

        parameters = list(inspect.signature(transcribe_session).parameters)
        assert parameters == [
            "session_dir",
            "crypto",
            "provider",
            "frame_probability",
            "require_footer",
            "model_name",
            "uncertainty_threshold",
            "speaker_embedder",
            "enrolled_profile",
        ]

    def _marked(self, count: int) -> list[Any]:
        return [
            (
                SpeechSegment(start_seconds=float(i), end_seconds=i + 0.5),
                (
                    TranscriptWord(
                        word_text=f"w{i}",
                        start_seconds=float(i),
                        end_seconds=i + 0.1,
                        probability=0.9,
                        uncertain=True,
                    ),
                ),
            )
            for i in range(count)
        ]

    def test_degenerate_policy_without_numpy_is_a_single_speaker(self) -> None:
        document = assemble_transcript(
            session_id="b" * 32,
            model_name="mock",
            marked_segments=self._marked(3),
            embeddings=[],
            similarities=[],
            saw_empty_segment=False,
            attributing=False,
            speaker_model_id=None,
            np=None,
        )
        assert [s.speaker for s in document.transcript_segments] == [SPEAKER_1] * 3
        assert document.enrolled_speaker is None
        assert document.model_name == "mock"

    def test_an_empty_slice_or_a_lone_embedding_degrades_to_a_single_speaker(self) -> None:
        np = pytest.importorskip("numpy")
        one = np.zeros(25, dtype=np.float32)
        two = np.ones(25, dtype=np.float32)
        for embeddings, saw_empty in ([one, two], True), ([one], False):
            document = assemble_transcript(
                session_id="c" * 32,
                model_name="mock",
                marked_segments=self._marked(len(embeddings)),
                embeddings=embeddings,
                similarities=[],
                saw_empty_segment=saw_empty,
                attributing=False,
                speaker_model_id=None,
                np=np,
            )
            assert {s.speaker for s in document.transcript_segments} == {SPEAKER_1}

    def test_attributing_labels_and_the_model_id_only_when_a_cluster_is_enrolled(self) -> None:
        np = pytest.importorskip("numpy")
        embeddings = [np.zeros(25, dtype=np.float32), np.ones(25, dtype=np.float32)]
        document = assemble_transcript(
            session_id="d" * 32,
            model_name="mock",
            marked_segments=self._marked(2),
            embeddings=embeddings,
            similarities=[0.1, 0.9],
            saw_empty_segment=False,
            attributing=True,
            speaker_model_id="model-x",
            np=np,
        )
        assert [s.speaker for s in document.transcript_segments] == [SPEAKER_2, SPEAKER_1]
        assert document.enrolled_speaker == SPEAKER_1
        assert document.speaker_model_id == "model-x"
        # No similarity at all: nothing is enrolled, so the id is NOT recorded.
        plain = assemble_transcript(
            session_id="d" * 32,
            model_name="mock",
            marked_segments=self._marked(2),
            embeddings=embeddings,
            similarities=[None, None],
            saw_empty_segment=False,
            attributing=True,
            speaker_model_id="model-x",
            np=np,
        )
        assert plain.speaker_model_id is None
        assert plain.enrolled_speaker is None


# ---------------------------------------------------------------------------
# LiveSegmenter — the VAD determinism pin and the forced close
# ---------------------------------------------------------------------------


def _random_probabilities(seed: int, frames: int) -> list[float]:
    """Bursty speech-like probabilities: runs of high and low values with
    jitter, so hysteresis, short dips and short spans all occur."""
    rng = random.Random(seed)
    probabilities: list[float] = []
    while len(probabilities) < frames:
        high = rng.random() < 0.5
        run = rng.randint(1, 40)
        for _ in range(run):
            base = 0.8 if high else 0.1
            probabilities.append(min(1.0, max(0.0, base + rng.uniform(-0.35, 0.35))))
    return probabilities[:frames]


def _stream(segmenter: LiveSegmenter, probabilities: Sequence[float]) -> list[SpeechSegment]:
    out: list[SpeechSegment] = []
    for probability in probabilities:
        out.extend(segmenter.push(probability))
    out.extend(segmenter.finish())
    return out


class TestLiveSegmenter:
    @pytest.mark.parametrize("seed", range(40))
    def test_same_frames_same_segments_with_the_shipped_parameters(self, seed: int) -> None:
        probabilities = _random_probabilities(seed, 600)
        expected = segment_probabilities(probabilities)
        assert _stream(LiveSegmenter(max_segment_seconds=10_000.0), probabilities) == expected

    @pytest.mark.parametrize("seed", range(40))
    def test_same_frames_same_segments_when_padding_merges(self, seed: int) -> None:
        """A configuration where padded segments DO touch and merge (large
        pad, short minimum silence) — the held-until-unmergeable rule must
        reproduce the batch merge exactly."""
        probabilities = _random_probabilities(seed, 600)
        options = {"pad_seconds": 0.5, "min_silence_seconds": 0.1, "min_speech_seconds": 0.05}
        expected = segment_probabilities(probabilities, **options)
        live = LiveSegmenter(max_segment_seconds=10_000.0, **options)
        assert _stream(live, probabilities) == expected

    def test_a_merge_across_padding_is_reproduced(self) -> None:
        options = {"pad_seconds": 0.5, "min_silence_seconds": 0.1, "min_speech_seconds": 0.05}
        probabilities = [0.9] * 10 + [0.0] * 6 + [0.9] * 10 + [0.0] * 40
        expected = segment_probabilities(probabilities, **options)
        assert len(expected) == 1  # the two spans touch once padded: ONE segment
        assert _stream(LiveSegmenter(max_segment_seconds=10_000.0, **options), probabilities) == (
            expected
        )

    def test_a_release_never_lags_beyond_the_padding(self) -> None:
        """Each segment is released no later than ``pad`` past its end, so
        the live view lags the batch decision by at most the padding."""
        probabilities = _random_probabilities(7, 600)
        segmenter = LiveSegmenter(max_segment_seconds=10_000.0)
        for index, probability in enumerate(probabilities):
            for segment in segmenter.push(probability):
                now = (index + 1) * FRAME_SECONDS
                assert segment.end_seconds <= now + 0.1 + 1e-9

    def test_the_forced_close_cuts_at_the_lowest_probability_frame_of_the_last_five_seconds(
        self,
    ) -> None:
        segmenter = LiveSegmenter()
        frames_to_cut = 0
        probabilities: list[float] = []
        # 40 s of speech at 1.0 with ONE dip at 27.0 s (inside the last 5 s of
        # the first span when the 30 s bound is reached).
        dip_frame = int(27.0 / FRAME_SECONDS)
        for index in range(int(40.0 / FRAME_SECONDS)):
            probabilities.append(0.6 if index == dip_frame else 1.0)
        released: list[SpeechSegment] = []
        for index, probability in enumerate(probabilities):
            out = segmenter.push(probability)
            if out and not frames_to_cut:
                frames_to_cut = index + 1
            released.extend(out)
        released.extend(segmenter.finish())
        assert len(released) == 2
        first, second = released
        assert first.start_seconds == 0.0
        assert first.end_seconds == pytest.approx(dip_frame * FRAME_SECONDS)
        assert second.start_seconds == first.end_seconds  # hard boundary: no padding
        assert first.duration_seconds < 30.0
        # released as soon as the bound was reached, not at the end of audio
        assert frames_to_cut * FRAME_SECONDS < 31.0

    def test_ninety_seconds_of_speech_yields_at_least_three_bounded_segments(self) -> None:
        probabilities = [0.95] * int(90.0 / FRAME_SECONDS)
        segments = _stream(LiveSegmenter(), probabilities)
        assert len(segments) >= 3
        assert all(s.duration_seconds <= 30.0 + 1e-9 for s in segments)
        for a, b in zip(segments, segments[1:], strict=False):
            assert b.start_seconds == a.end_seconds
        assert pack_transcription_windows(segments) == [(i, i + 1) for i in range(len(segments))]
        assert segments[-1].end_seconds == pytest.approx(90.0, abs=FRAME_SECONDS)

    def test_the_second_half_does_not_merge_back_into_the_first(self) -> None:
        probabilities = [0.95] * int(31.0 / FRAME_SECONDS)
        segments = _stream(LiveSegmenter(), probabilities)
        assert len(segments) == 2
        assert segments[0].end_seconds == segments[1].start_seconds

    def test_retention_floor_never_exceeds_a_later_released_start(self) -> None:
        probabilities = _random_probabilities(3, 600)
        segmenter = LiveSegmenter(max_segment_seconds=10_000.0)
        floor = 0.0
        for probability in probabilities:
            for segment in segmenter.push(probability):
                assert segment.start_seconds >= floor
            floor = segmenter.retention_floor_seconds
        for segment in segmenter.finish():
            assert segment.start_seconds >= floor

    def test_invalid_parameters_and_reuse_are_refused(self) -> None:
        with pytest.raises(ValueError):
            LiveSegmenter(start_threshold=0.2, end_threshold=0.5)
        with pytest.raises(ValueError):
            LiveSegmenter(max_segment_seconds=4.0, cut_search_seconds=5.0)
        segmenter = LiveSegmenter()
        segmenter.finish()
        with pytest.raises(LiveTranscriptionError):
            segmenter.push(0.5)
        with pytest.raises(LiveTranscriptionError):
            segmenter.finish()


class TestLiveWindows:
    @pytest.mark.parametrize("seed", range(20))
    def test_incremental_packing_matches_the_batch_packer(self, seed: int) -> None:
        rng = random.Random(seed)
        segments: list[SpeechSegment] = []
        clock = 0.0
        for _ in range(rng.randint(0, 30)):
            clock += rng.choice([0.2, 0.5, 1.0, 2.9, 3.1, 6.0])
            length = rng.choice([0.4, 1.0, 5.0, 12.0, 20.0, 31.0])
            segments.append(SpeechSegment(start_seconds=clock, end_seconds=clock + length))
            clock += length
        expected = [segments[a:b] for a, b in pack_transcription_windows(segments)]
        windows = _LiveWindows(window_seconds=30.0, max_gap_seconds=3.0)
        for index, segment in enumerate(segments):
            # ticks between segments with a bound the NEXT segment honours
            for _ in range(3):
                bound = rng.uniform(
                    segments[index - 1].end_seconds if index else 0.0, segment.start_seconds
                )
                windows.tick(bound)
            windows.add(segment)
        windows.flush()
        assert list(windows.ready) == expected

    def test_an_early_flush_happens_when_no_future_segment_could_join(self) -> None:
        windows = _LiveWindows(window_seconds=30.0, max_gap_seconds=3.0)
        windows.add(SpeechSegment(start_seconds=1.0, end_seconds=2.0))
        windows.tick(5.0)  # a segment starting at 5.0 has gap exactly 3.0: joins
        assert len(windows.ready) == 0
        windows.tick(5.5)  # gap 3.5: nothing later can join
        assert len(windows.ready) == 1
        wide = _LiveWindows(window_seconds=30.0, max_gap_seconds=1000.0)
        wide.add(SpeechSegment(start_seconds=6.0, end_seconds=7.0))
        wide.tick(36.0)  # a segment starting at 36.0 ends after it: span > 30
        assert len(wide.ready) == 0  # ... but only strictly: 36.0 - 6.0 == 30.0
        wide.tick(36.5)
        assert len(wide.ready) == 1


# ---------------------------------------------------------------------------
# LiveTranscriber — parity with the batch path
# ---------------------------------------------------------------------------


_PARITY_FIXTURES: dict[str, bytes] = {
    "empty": silence_pcm(2.0),
    "one_segment": silence_pcm(1.0) + tone_pcm(2.0) + silence_pcm(1.0),
    "no_profile_two_voices": _three_tones(220.0, 2600.0, 220.0),
    "two_windows": tone_pcm(1.0) + silence_pcm(5.0) + tone_pcm(1.0),
    "trailing_speech": silence_pcm(0.5) + tone_pcm(1.7),
    "odd_chunk_boundaries": silence_pcm(0.7) + tone_pcm(1.3) + silence_pcm(0.9) + tone_pcm(0.6),
}


class TestLiveParity:
    @pytest.fixture(autouse=True)
    def _numpy(self) -> None:
        pytest.importorskip("numpy")

    @pytest.mark.parametrize("name", sorted(_PARITY_FIXTURES))
    def test_live_and_batch_agree(self, tmp_path: Path, name: str) -> None:
        pcm = _PARITY_FIXTURES[name]
        session_dir = tmp_path / ("e" * 32)
        crypto = _make_store(session_dir, pcm)
        batch = transcribe_session(session_dir, crypto, MockSpeechProvider(), amplitude_vad)
        result = _run_live(pcm, _live())
        live = result.assemble(session_dir.name)
        assert _strip_created(live) == _strip_created(batch)
        # the live document passes every invariant the artefact read enforces
        write_transcript(session_dir, crypto, live)
        assert read_transcript(session_dir, crypto) == live

    def test_enrolled_matches_agree(self, tmp_path: Path) -> None:
        pcm = _three_tones(220.0, 2600.0, 220.0)
        session_dir = tmp_path / ("f" * 32)
        crypto = _make_store(session_dir, pcm)
        plain = transcribe_session(session_dir, crypto, MockSpeechProvider(), amplitude_vad)
        segments = [
            SpeechSegment(start_seconds=s.start_seconds, end_seconds=s.end_seconds)
            for s in plain.transcript_segments
        ]
        slices = list(extract_segment_pcm([pcm], segments))
        vectors = dict(zip(slices, [E1, E2, E1], strict=True))
        batch_embedder = MockSpeakerEmbedder(vectors)
        batch = transcribe_session(
            session_dir,
            crypto,
            MockSpeechProvider(),
            amplitude_vad,
            speaker_embedder=batch_embedder,
            enrolled_profile=_profile(),
        )
        live_embedder = MockSpeakerEmbedder(vectors)
        result = _run_live(pcm, _live(attribution=lambda: (live_embedder, _profile())))
        live = result.assemble(session_dir.name)
        assert _strip_created(live) == _strip_created(batch)
        assert live.enrolled_speaker == SPEAKER_1
        assert live.speaker_model_id == MOCK_MODEL_ID
        # the SAME slices were embedded, once each, in order
        assert live_embedder.embedded_lengths == batch_embedder.embedded_lengths

    def test_textless_cluster_agrees(self, tmp_path: Path) -> None:
        pcm = tone_pcm(1.0, frequency=220.0) + silence_pcm(5.0) + tone_pcm(1.0, frequency=2600.0)
        session_dir = tmp_path / ("a1" * 16)
        crypto = _make_store(session_dir, pcm)
        batch = transcribe_session(session_dir, crypto, _TextlessProvider(), amplitude_vad)
        assert not batch.transcript_segments[1].transcript_words
        result = _run_live(pcm, _live(provider=_TextlessProvider()))
        assert _strip_created(result.assemble(session_dir.name)) == _strip_created(batch)

    def test_the_forced_close_is_the_only_departure(self, tmp_path: Path) -> None:
        """31 s of speech: the batch keeps one oversized segment, the live
        path two bounded halves — the same words, all attributed."""
        pcm = tone_pcm(31.0) + silence_pcm(0.5) + tone_pcm(1.0)
        session_dir = tmp_path / ("b2" * 16)
        crypto = _make_store(session_dir, pcm)
        batch = transcribe_session(session_dir, crypto, MockSpeechProvider(), amplitude_vad)
        oversized = batch.transcript_segments[0]
        assert oversized.end_seconds - oversized.start_seconds > 30.0
        result = _run_live(pcm, _live())
        live = result.assemble(session_dir.name)
        assert len(live.transcript_segments) == len(batch.transcript_segments) + 1
        assert all(
            s.end_seconds - s.start_seconds <= 30.0 + 1e-9 for s in live.transcript_segments
        )
        assert live.transcript_segments[-1].end_seconds == pytest.approx(
            batch.transcript_segments[-1].end_seconds
        )


# ---------------------------------------------------------------------------
# LiveTranscriber — the worker's contract
# ---------------------------------------------------------------------------


class TestLiveTranscriber:
    def test_ninety_seconds_of_speech_posts_bounded_segments_as_it_goes(self) -> None:
        pytest.importorskip("numpy")
        posts: list[tuple[TranscriptSegment, ...]] = []
        live = _live(on_window=posts.append)
        live.start()
        for chunk in _chunks(tone_pcm(90.0)):
            live.feed(chunk)
        _wait(lambda: len(posts) >= 2, timeout=20.0)  # live updates BEFORE seal
        live.seal()
        result = live.drain()
        assert len(posts) >= 3
        posted = [s for window in posts for s in window]
        assert all(s.speaker == LIVE_SPEAKER_PENDING for s in posted)
        assert all(s.transcript_words for s in posted)
        assert len(result.marked_segments) == len(posted) >= 3
        assert len(result.window_timings) == len(posts)
        assert all(audio > 0 and wall >= 0 for audio, wall in result.window_timings)
        assert live.buffers_cleared
        assert not live.models_loaded  # D3: released on exit

    def test_queued_pcm_cap_during_a_blocked_model_load_fails_then_falls_back(self) -> None:
        gate = threading.Event()

        def blocked_provider() -> MockSpeechProvider:
            gate.wait()
            return MockSpeechProvider()

        live = _live(provider_factory=blocked_provider, queue_cap_bytes=CHUNK * 3)
        live.start()
        for _ in range(3):
            live.feed(b"\0" * CHUNK)
        assert live.failed_reason is None
        live.feed(b"\0" * CHUNK)  # the fourth chunk crosses the cap
        failure = live.failed_reason
        assert failure is not None and failure.kind == LiveFailureKind.FELL_BEHIND
        live.feed(b"\0" * CHUNK)  # dropped silently after failure
        gate.set()
        live.seal()
        with pytest.raises(LiveTranscriptionFailed) as excinfo:
            live.drain()
        assert excinfo.value.failure.kind == LiveFailureKind.FELL_BEHIND
        _wait(lambda: not live.running)
        assert live.buffers_cleared
        assert not live.models_loaded

    def test_a_provider_slower_than_the_feed_trips_the_queue_cap(self) -> None:
        """D2's fall-behind in practice (peer round 10): with the drain
        yielding at every ready window, audio a slow provider cannot keep up
        with accumulates in the QUEUE, and the feed-time cap stops the worker
        itself — the worker fails, the batch path takes over."""
        pytest.importorskip("numpy")
        gate = threading.Event()
        provider = _BlockingProvider(gate)
        utterance = tone_pcm(1.0) + silence_pcm(5.0)
        live = _live(provider=provider, queue_cap_bytes=len(utterance) * 3)
        live.start()
        for chunk in _chunks(utterance):
            live.feed(chunk)
        assert provider.entered.wait(5.0)  # blocked in the first window
        assert live.failed_reason is None
        # Three more windows' worth plus one chunk while nothing is being
        # ingested: the cap is crossed (the first utterance's last chunk is
        # still queued too) and the worker stops ITSELF at feed time.
        for chunk in _chunks(utterance * 3 + b"\0" * CHUNK):
            live.feed(chunk)
        failure = live.failed_reason
        assert failure is not None and failure.kind == LiveFailureKind.FELL_BEHIND
        gate.set()
        live.seal()
        with pytest.raises(LiveTranscriptionFailed) as excinfo:
            live.drain()
        assert excinfo.value.failure.kind == LiveFailureKind.FELL_BEHIND
        assert provider.calls == 1
        assert live.buffers_cleared

    def test_a_single_chunk_closing_many_windows_trips_the_defensive_backlog_bound(
        self,
    ) -> None:
        """The windows-behind rule as a DEFENSIVE bound: one oversized chunk
        (30 s, five utterances 5 s apart, under the queue cap) closes four
        ready windows inside a single ingestion — more than the permitted
        backlog — so the worker fails before any provider call."""
        pytest.importorskip("numpy")
        provider = MockSpeechProvider()
        calls: list[int] = []

        class _Counting:
            def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
                calls.append(1)
                return provider.transcribe_segment(pcm, sample_rate)

        live = _live(provider=_Counting())
        live.start()
        live.feed((tone_pcm(1.0) + silence_pcm(5.0)) * 5)  # ONE chunk, five windows
        _wait(lambda: live.failed_reason is not None)
        failure = live.failed_reason
        assert failure is not None and failure.kind == LiveFailureKind.FELL_BEHIND
        assert calls == []
        live.seal()
        with pytest.raises(LiveTranscriptionFailed):
            live.drain()
        assert live.buffers_cleared

    def test_a_queued_backlog_is_processed_window_by_window_with_bounded_retention(
        self,
    ) -> None:
        """Peer round 9 PR-MED-018 → round 10 PR-LOW-022: audio queued ahead
        of the worker (twelve utterances, 72 s, inside the 90 s queue cap,
        waiting behind a blocked model load) is NOT ingested in one pass —
        the drain yields at every ready window, which is transcribed before
        more chunks are ingested, so the retained plaintext peaks at one
        window plus the open span plus one chunk and every window is
        transcribed."""
        pytest.importorskip("numpy")
        gate = threading.Event()

        def blocked_load() -> Any:
            gate.wait()
            return MockSpeechProvider()

        posts: list[tuple[TranscriptSegment, ...]] = []
        live = _live(provider_factory=blocked_load, on_window=posts.append)
        peak = 0
        original = live._trim

        def trimming() -> None:
            nonlocal peak
            original()
            peak = max(peak, len(live._pcm))

        live._trim = trimming  # type: ignore[method-assign]
        live.start()
        utterance = tone_pcm(1.0) + silence_pcm(5.0)  # one window each (gap > 3 s)
        for chunk in _chunks(utterance * 12):
            live.feed(chunk)
        assert live.failed_reason is None  # under the queue cap
        gate.set()
        live.seal()
        result = live.drain()
        assert len(result.marked_segments) == 12 == len(posts)
        assert peak <= len(utterance) + CHUNK + 0.2 * SAMPLE_RATE * BYTES_PER_SAMPLE

    def test_a_ready_window_followed_by_long_silence_does_not_pin_the_buffer(self) -> None:
        """Peer round 10 PR-LOW-022's schedule: one utterance becomes a ready
        window and prolonged silence keeps arriving behind it — the window is
        processed before the silence is ingested, so the retention floor
        moves on and the retained plaintext stays bounded."""
        pytest.importorskip("numpy")
        gate = threading.Event()

        def blocked_load() -> Any:
            gate.wait()
            return MockSpeechProvider()

        live = _live(provider_factory=blocked_load)
        peak = 0
        original = live._trim

        def trimming() -> None:
            nonlocal peak
            original()
            peak = max(peak, len(live._pcm))

        live._trim = trimming  # type: ignore[method-assign]
        live.start()
        fed = tone_pcm(1.0) + silence_pcm(60.0)  # one window, then a minute of silence
        for chunk in _chunks(fed):
            live.feed(chunk)
        gate.set()
        live.seal()
        result = live.drain()
        assert len(result.marked_segments) == 1
        assert peak < len(fed) // 4  # never the whole recording
        assert peak <= int(6.0 * SAMPLE_RATE) * BYTES_PER_SAMPLE  # the window + its flush gap

    def test_a_sealed_backlog_drains_in_full_instead_of_falling_behind(self) -> None:
        """Peer round 10 PR-LOW-023: Finish while the provider is busy with
        the first window and five more utterances are queued — the seal is
        REQUESTED before those chunks are ingested, so the cut-off never
        counts them and all six windows drain."""
        pytest.importorskip("numpy")
        gate = threading.Event()
        provider = _BlockingProvider(gate)
        live = _live(provider=provider)
        live.start()
        utterance = tone_pcm(1.0) + silence_pcm(5.0)
        for chunk in _chunks(utterance):
            live.feed(chunk)
        assert provider.entered.wait(5.0)
        for chunk in _chunks(utterance * 5):
            live.feed(chunk)
        live.seal()  # the sentinel sits BEHIND the five queued utterances
        gate.set()
        result = live.drain()
        assert live.failed_reason is None
        assert len(result.marked_segments) == 6
        assert provider.calls == 6

    def test_a_model_load_failure_names_its_reason(self) -> None:
        def broken() -> MockSpeechProvider:
            raise RuntimeError("no snapshot")

        live = _live(provider_factory=broken)
        live.start()
        _wait(lambda: live.failed_reason is not None)
        failure = live.failed_reason
        assert failure is not None
        assert failure.kind == LiveFailureKind.MODEL_LOAD
        assert "RuntimeError" in failure.detail and "no snapshot" in failure.detail
        live.seal()
        with pytest.raises(LiveTranscriptionFailed):
            live.drain()

    def test_feed_never_raises(self) -> None:
        live = _live()
        live.feed(b"\0" * CHUNK)  # before start
        failure = live.failed_reason
        assert failure is not None and failure.kind == LiveFailureKind.WORKER_ERROR
        another = _live()
        another.start()
        another.feed(object())  # type: ignore[arg-type]
        failure = another.failed_reason
        assert failure is not None and failure.kind == LiveFailureKind.WORKER_ERROR
        another.stop()

    def test_audio_while_paused_is_a_failed_worker_not_a_misaligned_timeline(self) -> None:
        live = _live()
        live.start()
        live.pause()
        assert live.paused
        live.feed(b"\0" * CHUNK)
        failure = live.failed_reason
        assert failure is not None and failure.kind == LiveFailureKind.WORKER_ERROR
        live.stop()

    def test_pause_and_resume_keep_the_timeline_when_honoured(self) -> None:
        pytest.importorskip("numpy")
        live = _live()
        live.start()
        chunks = _chunks(silence_pcm(1.0) + tone_pcm(2.0) + silence_pcm(1.0))
        live.feed(chunks[0])
        live.pause()
        live.resume()
        for chunk in chunks[1:]:
            live.feed(chunk)
        live.seal()
        result = live.drain()
        assert len(result.marked_segments) == 1
        assert result.marked_segments[0][0].start_seconds == pytest.approx(1.0, abs=0.15)

    def test_stop_during_recording_clears_the_buffers_and_drops_late_posts(self) -> None:
        pytest.importorskip("numpy")
        posts: list[tuple[TranscriptSegment, ...]] = []
        live = _live(on_window=posts.append)
        live.start()
        for chunk in _chunks(silence_pcm(0.5) + tone_pcm(2.0)):
            live.feed(chunk)
        assert live.stop() is True
        assert live.buffers_cleared
        assert not live.running
        assert not live.models_loaded
        before = len(posts)
        time.sleep(0.05)
        assert len(posts) == before

    def test_a_join_timeout_is_reported_never_counted_as_cleared(self) -> None:
        pytest.importorskip("numpy")
        gate = threading.Event()
        provider = _BlockingProvider(gate)
        posts: list[tuple[TranscriptSegment, ...]] = []
        live = _live(provider=provider, on_window=posts.append)
        live.start()
        for chunk in _chunks(tone_pcm(1.0) + silence_pcm(5.0)):
            live.feed(chunk)
        assert provider.entered.wait(5.0)
        assert live.stop(timeout=0.2) is False  # blocked in the provider
        assert live.running
        gate.set()
        _wait(lambda: not live.running)
        assert posts == []  # the window that completed after stop was dropped
        assert live.stop() is True
        assert live.buffers_cleared

    def test_seal_is_cheap_under_a_blocked_tail(self) -> None:
        pytest.importorskip("numpy")
        gate = threading.Event()
        provider = _BlockingProvider(gate)
        live = _live(provider=provider)
        live.start()
        for chunk in _chunks(tone_pcm(1.0) + silence_pcm(5.0) + tone_pcm(1.0)):
            live.feed(chunk)
        assert provider.entered.wait(5.0)
        started = time.perf_counter()
        live.seal()
        assert time.perf_counter() - started < 0.1
        assert live.sealed
        gate.set()
        result = live.drain()
        assert len(result.marked_segments) == 2

    def test_the_last_flushed_chunk_is_in_the_drained_tail(self) -> None:
        pytest.importorskip("numpy")
        live = _live()
        live.start()
        pcm = silence_pcm(1.0) + tone_pcm(1.0)
        chunks = _chunks(pcm[:-4000]) + [pcm[-4000:]]  # a short final partial chunk
        for chunk in chunks:
            live.feed(chunk)
        live.seal()
        result = live.drain()
        segment, words = result.marked_segments[-1]
        assert segment.end_seconds == pytest.approx(2.0, abs=0.15)
        assert words

    def test_vad_is_reset_at_start_and_on_exit_and_models_are_released(self) -> None:
        pytest.importorskip("numpy")
        vad = _ResettableVad()
        live = LiveTranscriber(
            provider_factory=MockSpeechProvider, vad_factory=lambda: vad.frame_probability
        )
        live.start()
        for chunk in _chunks(silence_pcm(0.5) + tone_pcm(1.0)):
            live.feed(chunk)
        live.seal()
        live.drain()
        assert vad.resets == 2
        assert not live.models_loaded

    def test_misuse_is_refused(self) -> None:
        live = _live()
        with pytest.raises(LiveTranscriptionError):
            live.drain()  # before seal
        live.start()
        with pytest.raises(LiveTranscriptionError):
            live.start()
        live.stop()
        with pytest.raises(ValueError):
            _live(queue_cap_bytes=0)

    def test_the_live_pcm_bound_is_one_window_plus_the_open_span(self) -> None:
        """D1/D2: PCM is dropped per window. With a provider that keeps pace
        (each utterance is fed only after the previous window was posted),
        the retained plaintext peaks at the window in progress plus the open
        span — never the consultation. Fed faster than real time the buffer
        instead holds the READY windows, bounded by the fall-behind cap and
        the queue cap (the fixture avoids that regime on purpose)."""
        pytest.importorskip("numpy")
        peak = 0
        posts: list[tuple[TranscriptSegment, ...]] = []
        live = _live(on_window=posts.append)
        original = live._trim

        def trimming() -> None:
            nonlocal peak
            original()
            peak = max(peak, len(live._pcm))

        live._trim = trimming  # type: ignore[method-assign]
        live.start()
        utterance = tone_pcm(2.0) + silence_pcm(4.0)  # one window per utterance
        for index in range(20):  # 120 s in total
            for chunk in _chunks(utterance):
                live.feed(chunk)
            expected = index + 1
            _wait(lambda: len(posts) >= expected)  # noqa: B023 - the provider kept pace
        live.seal()
        result = live.drain()
        assert len(result.marked_segments) == 20
        bytes_per_second = SAMPLE_RATE * BYTES_PER_SAMPLE
        assert peak <= int(len(utterance) + 0.2 * bytes_per_second)  # this fixture's window
        assert peak <= int((30.0 + 30.0) * bytes_per_second)  # one window + the open span
        assert peak < len(utterance) * 20 // 10

    def test_frames_seen_by_the_worker_equal_the_batch_framing(self) -> None:
        """The worker frames the chunk stream exactly like ``iter_frames``
        (zero-padded final partial frame included)."""
        seen: list[bytes] = []

        def vad(frame: bytes) -> float:
            seen.append(frame)
            return amplitude_vad(frame)

        live = LiveTranscriber(provider_factory=MockSpeechProvider, vad_factory=lambda: vad)
        live.start()
        pcm = silence_pcm(0.3) + tone_pcm(0.7) + b"\0" * 100
        for chunk in [pcm[:5000], pcm[5000:20_001], pcm[20_001:]]:
            live.feed(chunk)
        live.seal()
        live.drain()
        assert seen == list(iter_frames([pcm]))
        assert all(len(frame) == FRAME_BYTES for frame in seen)
