"""Step 7 tests: VAD segmentation scaffolding (`scribe_desktop.speech`).

Layers:
- pure segmenter / frame-reassembly unit tests (no ML stack, no model)
- synthetic PCM (tone+silence) through a deterministic amplitude-based
  fake VAD backend — proves the frames->probabilities->segments wiring
  and the session-store decrypt-stream integration without ML
- real-model tests against the downloaded silero_vad.onnx (skip-if-absent
  for CI; SAPI synthesis is Windows-only, and goes through `sapi_fixture`
  so the model hears TRUE 16 kHz — SAPI itself renders 22050 Hz)

No clinical audio anywhere: all fixtures are generated tones/silence or
SAPI text-to-speech of non-clinical text.
"""

from __future__ import annotations

import importlib.util
import math
import struct
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from sapi_fixture import synthesize_speech_pcm
from scribe_desktop.benchmark import OFFLINE_ENV, apply_offline_env
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import KEY_FILENAME, SessionChunkStore
from scribe_desktop.speech import (
    BYTES_PER_SAMPLE,
    FRAME_BYTES,
    FRAME_SECONDS,
    SAMPLE_RATE,
    MockSpeechProvider,
    SileroVad,
    SpeechSegment,
    VadModelError,
    iter_frames,
    segment_pcm,
    segment_probabilities,
    segment_session_audio,
    vad_model_available,
)

# ---------------------------------------------------------------------------
# synthetic PCM helpers (tone = "speech" stand-in for the fake backend)
# ---------------------------------------------------------------------------


def tone_pcm(seconds: float, frequency: float = 440.0, amplitude: float = 0.5) -> bytes:
    count = int(seconds * SAMPLE_RATE)
    scale = amplitude * 32767
    return struct.pack(
        f"<{count}h",
        *(int(scale * math.sin(2 * math.pi * frequency * i / SAMPLE_RATE)) for i in range(count)),
    )


def silence_pcm(seconds: float) -> bytes:
    return b"\0" * (int(seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE)


def amplitude_vad(frame: bytes) -> float:
    """Deterministic fake backend: loud frame -> 0.95, quiet -> 0.02."""
    samples = struct.unpack(f"<{len(frame) // 2}h", frame)
    peak = max(abs(s) for s in samples)
    return 0.95 if peak > 1000 else 0.02


# ---------------------------------------------------------------------------
# segment_probabilities — pure unit tests
# ---------------------------------------------------------------------------


class TestSegmentProbabilities:
    def test_empty_input(self) -> None:
        assert segment_probabilities([]) == []

    def test_all_silence(self) -> None:
        assert segment_probabilities([0.01] * 200) == []

    def test_single_speech_burst_boundaries(self) -> None:
        probs = [0.0] * 50 + [0.9] * 50 + [0.0] * 50
        (seg,) = segment_probabilities(probs, pad_seconds=0.0)
        assert seg.start_seconds == pytest.approx(50 * FRAME_SECONDS)
        assert seg.end_seconds == pytest.approx(100 * FRAME_SECONDS)

    def test_short_blip_discarded(self) -> None:
        # 2 frames (~64 ms) of speech < MIN_SPEECH_SECONDS
        probs = [0.0] * 50 + [0.9] * 2 + [0.0] * 50
        assert segment_probabilities(probs) == []

    def test_short_dip_bridged(self) -> None:
        # a 3-frame dip (~96 ms) inside speech is bridged (min silence 0.35 s)
        probs = [0.0] * 20 + [0.9] * 30 + [0.1] * 3 + [0.9] * 30 + [0.0] * 30
        segments = segment_probabilities(probs, pad_seconds=0.0)
        assert len(segments) == 1
        assert segments[0].end_seconds == pytest.approx(83 * FRAME_SECONDS)

    def test_long_gap_splits_segments(self) -> None:
        gap = int(1.0 / FRAME_SECONDS)  # 1 s of silence
        probs = [0.9] * 30 + [0.0] * gap + [0.9] * 30
        segments = segment_probabilities(probs, pad_seconds=0.0)
        assert len(segments) == 2
        assert segments[0].end_seconds == pytest.approx(30 * FRAME_SECONDS)
        assert segments[1].start_seconds == pytest.approx((30 + gap) * FRAME_SECONDS)

    def test_speech_running_to_end_is_closed(self) -> None:
        probs = [0.0] * 10 + [0.9] * 40
        (seg,) = segment_probabilities(probs, pad_seconds=0.0)
        assert seg.end_seconds == pytest.approx(50 * FRAME_SECONDS)

    def test_trailing_short_silence_trimmed(self) -> None:
        # stream ends mid-silence-run: the run is trimmed from the segment
        probs = [0.9] * 40 + [0.0] * 5
        (seg,) = segment_probabilities(probs, pad_seconds=0.0)
        assert seg.end_seconds == pytest.approx(40 * FRAME_SECONDS)

    def test_padding_clamped_to_bounds(self) -> None:
        probs = [0.9] * 20
        (seg,) = segment_probabilities(probs, pad_seconds=5.0)
        assert seg.start_seconds == 0.0
        assert seg.end_seconds == pytest.approx(20 * FRAME_SECONDS)

    def test_padding_merges_touching_segments(self) -> None:
        gap = int(0.5 / FRAME_SECONDS)  # 0.5 s gap, 0.3 s padding each side
        probs = [0.9] * 30 + [0.0] * gap + [0.9] * 30
        segments = segment_probabilities(probs, pad_seconds=0.3)
        assert len(segments) == 1

    def test_hysteresis_between_thresholds_keeps_speech(self) -> None:
        # 0.4 sits between end (0.35) and start (0.5): continues speech,
        # never starts it
        assert segment_probabilities([0.4] * 100) == []
        probs = [0.9] * 20 + [0.4] * 40 + [0.0] * 20
        (seg,) = segment_probabilities(probs, pad_seconds=0.0)
        assert seg.end_seconds == pytest.approx(60 * FRAME_SECONDS)

    def test_invalid_thresholds_rejected(self) -> None:
        with pytest.raises(ValueError):
            segment_probabilities([0.5], start_threshold=0.3, end_threshold=0.4)

    def test_segment_type_invariants(self) -> None:
        with pytest.raises(ValueError):
            SpeechSegment(start_seconds=1.0, end_seconds=1.0)
        with pytest.raises(ValueError):
            SpeechSegment(start_seconds=-0.1, end_seconds=1.0)


# ---------------------------------------------------------------------------
# iter_frames — reassembly
# ---------------------------------------------------------------------------


class TestIterFrames:
    def test_empty(self) -> None:
        assert list(iter_frames([])) == []

    def test_exact_multiple(self) -> None:
        frames = list(iter_frames([b"\x01" * FRAME_BYTES * 3]))
        assert [len(f) for f in frames] == [FRAME_BYTES] * 3

    def test_reassembly_across_odd_chunks(self) -> None:
        data = bytes(range(256)) * 20  # 5120 bytes = 5 frames
        chunks = [data[i : i + 333] for i in range(0, len(data), 333)]
        frames = list(iter_frames(chunks))
        assert b"".join(frames) == data
        assert all(len(f) == FRAME_BYTES for f in frames)

    def test_partial_tail_zero_padded(self) -> None:
        frames = list(iter_frames([b"\x7f" * (FRAME_BYTES + 10)]))
        assert len(frames) == 2
        assert frames[1] == b"\x7f" * 10 + b"\0" * (FRAME_BYTES - 10)


# ---------------------------------------------------------------------------
# segment_pcm with the fake backend on tone+silence fixtures
# ---------------------------------------------------------------------------


class TestSegmentPcmSynthetic:
    def test_tone_between_silence(self) -> None:
        pcm = silence_pcm(1.0) + tone_pcm(2.0) + silence_pcm(1.0)
        chunks = [pcm[i : i + 32_000] for i in range(0, len(pcm), 32_000)]
        (seg,) = segment_pcm(chunks, amplitude_vad)
        assert seg.start_seconds == pytest.approx(1.0, abs=0.15)
        assert seg.end_seconds == pytest.approx(3.0, abs=0.15)

    def test_two_bursts(self) -> None:
        pcm = (
            silence_pcm(0.5)
            + tone_pcm(1.0)
            + silence_pcm(1.0)
            + tone_pcm(1.0)
            + silence_pcm(0.5)
        )
        segments = segment_pcm([pcm], amplitude_vad)
        assert len(segments) == 2
        assert segments[0].start_seconds == pytest.approx(0.5, abs=0.15)
        assert segments[1].start_seconds == pytest.approx(2.5, abs=0.15)

    def test_pure_silence(self) -> None:
        assert segment_pcm([silence_pcm(3.0)], amplitude_vad) == []


# ---------------------------------------------------------------------------
# session-store decrypt-stream integration (fake backend, no ML)
# ---------------------------------------------------------------------------


class TestSegmentSessionAudio:
    def test_segments_from_encrypted_store(self, tmp_path: Path) -> None:
        session_dir = tmp_path / ("a" * 32)
        session_dir.mkdir()
        (session_dir / KEY_FILENAME).write_bytes(b"\0" * 64)  # store-format stub
        crypto = SessionCrypto()
        store = SessionChunkStore.create(session_dir / "audio.enc", crypto, "a" * 32)
        pcm = silence_pcm(1.0) + tone_pcm(1.5) + silence_pcm(1.0)
        for i in range(0, len(pcm), 32_000):  # ~1 s chunks, capture-shaped
            store.append_chunk(pcm[i : i + 32_000])
        store.finish()

        (seg,) = segment_session_audio(session_dir / "audio.enc", crypto, amplitude_vad)
        assert seg.start_seconds == pytest.approx(1.0, abs=0.15)
        assert seg.end_seconds == pytest.approx(2.5, abs=0.15)

    def test_require_footer_detects_post_finish_truncation(self, tmp_path: Path) -> None:
        from scribe_desktop.session_store import StoreCorruptError

        session_dir = tmp_path / ("c" * 32)
        session_dir.mkdir()
        (session_dir / KEY_FILENAME).write_bytes(b"\0" * 64)
        crypto = SessionCrypto()
        path = session_dir / "audio.enc"
        store = SessionChunkStore.create(path, crypto, "c" * 32)
        store.append_chunk(tone_pcm(1.0))
        store.finish()
        data = path.read_bytes()
        path.write_bytes(data[:-40])  # chop the footer off a Finished store
        # recovery-style scan tolerates the truncation...
        assert segment_session_audio(path, crypto, amplitude_vad)
        # ...but the Finished-store path must detect it
        with pytest.raises(StoreCorruptError):
            segment_session_audio(path, crypto, amplitude_vad, require_footer=True)

    def test_wrong_key_propagates_corrupt_error(self, tmp_path: Path) -> None:
        from scribe_desktop.session_store import StoreCorruptError

        session_dir = tmp_path / ("b" * 32)
        session_dir.mkdir()
        (session_dir / KEY_FILENAME).write_bytes(b"\0" * 64)
        crypto = SessionCrypto()
        store = SessionChunkStore.create(session_dir / "audio.enc", crypto, "b" * 32)
        store.append_chunk(tone_pcm(1.0))
        store.finish()
        with pytest.raises(StoreCorruptError):
            segment_session_audio(session_dir / "audio.enc", SessionCrypto(), amplitude_vad)


# ---------------------------------------------------------------------------
# MockSpeechProvider
# ---------------------------------------------------------------------------


class TestMockSpeechProvider:
    def test_word_count_scales_with_duration(self) -> None:
        provider = MockSpeechProvider(words_per_second=2.0)
        words = provider.transcribe_segment(tone_pcm(3.0), SAMPLE_RATE)
        assert len(words) == 6
        assert words[0].start_seconds == 0.0
        assert words[-1].end_seconds == pytest.approx(3.0)
        assert all(0.0 <= w.probability <= 1.0 for w in words)

    def test_empty_audio_gives_no_words(self) -> None:
        assert MockSpeechProvider().transcribe_segment(b"", SAMPLE_RATE) == []


# ---------------------------------------------------------------------------
# SileroVad — offline enforcement + real-model tests (skip-if-absent)
# ---------------------------------------------------------------------------


def _make_recording_session(np: object) -> object:
    """Fake onnxruntime session matching the silero v5 signature that
    records every ``run()`` feed dict and returns a DISTINCTIVE non-zero
    recurrent state, so state leaking across reset() is detectable."""

    class _Input:
        def __init__(self, name: str) -> None:
            self.name = name

    class _RecordingSession:
        def __init__(self) -> None:
            self.calls: list[dict] = []  # type: ignore[type-arg]

        def get_inputs(self) -> list[_Input]:
            return [_Input("input"), _Input("state"), _Input("sr")]

        def run(self, output_names: object, feeds: dict) -> list:  # type: ignore[type-arg]
            self.calls.append({k: v.copy() for k, v in feeds.items()})
            output = np.full((1, 1), 0.5, dtype=np.float32)  # type: ignore[attr-defined]
            new_state = np.full((2, 1, 128), 7.0, dtype=np.float32)  # type: ignore[attr-defined]
            return [output, new_state]

    return _RecordingSession()


class TestSileroVadOffline:
    def test_init_requires_offline_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scribe_desktop.benchmark import OfflineEnvError

        for key in OFFLINE_ENV:
            monkeypatch.delenv(key, raising=False)
        with pytest.raises(OfflineEnvError):
            SileroVad()

    def test_missing_model_raises_before_ml_import(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        apply_offline_env()
        with pytest.raises(VadModelError, match="setup-models"):
            SileroVad(model_path=tmp_path / "nope.onnx")

    def test_unc_model_path_rejected(self) -> None:
        apply_offline_env()
        with pytest.raises(VadModelError, match="UNC"):
            SileroVad(model_path=Path(r"\\evil-host\share\model.onnx"))

    def test_corrupt_model_raises_vad_model_error(self, tmp_path: Path) -> None:
        # offline env BEFORE any ML import (PR-MED-009/-014 pattern)
        apply_offline_env()
        pytest.importorskip("onnxruntime")
        bogus = tmp_path / "corrupt.onnx"
        bogus.write_bytes(b"not an onnx model at all")
        with pytest.raises(VadModelError, match="failed to load"):
            SileroVad(model_path=bogus)


    def test_incompatible_model_fails_smoke_inference(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A session whose run() raises (signature OK, shapes incompatible)
        # must fail at LOAD as VadModelError, not on the first real frame.
        apply_offline_env()
        onnxruntime = pytest.importorskip("onnxruntime")

        class _Input:
            def __init__(self, name: str) -> None:
                self.name = name

        class _BrokenSession:
            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

            def get_inputs(self) -> list[_Input]:
                return [_Input("input"), _Input("state"), _Input("sr")]

            def run(self, *args: object, **kwargs: object) -> object:
                raise RuntimeError("shape mismatch")

        monkeypatch.setattr(onnxruntime, "InferenceSession", _BrokenSession)
        with pytest.raises(VadModelError, match="smoke inference"):
            SileroVad(model_path=Path(__file__))  # any existing file

    def test_smoke_inference_uses_v5_input_and_state_shapes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # PR-MED-015 coverage: the load-time smoke inference must exercise
        # the exact silero v5 signature — 64-sample context + 512-sample
        # frame as float32 ``input``, a (2, 1, 128) float32 recurrent
        # ``state`` of zeros, and an int64 ``sr`` scalar of 16000.
        apply_offline_env()
        onnxruntime = pytest.importorskip("onnxruntime")
        np = pytest.importorskip("numpy")
        from scribe_desktop.speech import CONTEXT_SAMPLES, FRAME_SAMPLES

        session = _make_recording_session(np)
        monkeypatch.setattr(
            onnxruntime, "InferenceSession", lambda *a, **k: session
        )
        SileroVad(model_path=Path(__file__))  # any existing file

        assert len(session.calls) == 1, "load must smoke-infer exactly once"
        feeds = session.calls[0]
        assert feeds["input"].shape == (1, CONTEXT_SAMPLES + FRAME_SAMPLES)
        assert feeds["input"].dtype == np.float32
        assert not feeds["input"].any()  # silent frame + zero context
        assert feeds["state"].shape == (2, 1, 128)
        assert feeds["state"].dtype == np.float32
        assert not feeds["state"].any()  # fresh recurrent state
        assert feeds["sr"].dtype == np.int64
        assert int(feeds["sr"]) == SAMPLE_RATE

    def test_first_real_inference_after_load_sees_pristine_state(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # PR-MED-015 coverage: the post-smoke reset() must leave the first
        # REAL inference with all-zero recurrent state and context, exactly
        # as if the smoke inference had never happened. The fake session
        # returns a distinctive non-zero state so any leak is detectable.
        apply_offline_env()
        onnxruntime = pytest.importorskip("onnxruntime")
        np = pytest.importorskip("numpy")
        from scribe_desktop.speech import CONTEXT_SAMPLES

        session = _make_recording_session(np)
        monkeypatch.setattr(
            onnxruntime, "InferenceSession", lambda *a, **k: session
        )
        vad = SileroVad(model_path=Path(__file__))
        vad.frame_probability(tone_pcm(0.5)[:FRAME_BYTES])

        assert len(session.calls) == 2  # smoke + first real
        first_real = session.calls[1]
        # recurrent state is pristine zeros, not the smoke run's output
        assert not first_real["state"].any()
        # rolling context (leading 64 samples of input) is pristine zeros
        assert not first_real["input"][:, :CONTEXT_SAMPLES].any()
        # and the frame itself made it in (tone is non-silent)
        assert first_real["input"][:, CONTEXT_SAMPLES:].any()


class TestSegmentPcmResetContract:
    def test_backend_reset_before_and_after_even_on_failure(self) -> None:
        class FakeBackend:
            def __init__(self) -> None:
                self.resets = 0

            def reset(self) -> None:
                self.resets += 1

            def frame_probability(self, frame: bytes) -> float:
                raise RuntimeError("boom")

        backend = FakeBackend()
        with pytest.raises(RuntimeError, match="boom"):
            segment_pcm([tone_pcm(0.5)], backend.frame_probability)
        assert backend.resets == 2  # before + finally

    def test_plain_function_backend_needs_no_reset(self) -> None:
        # module-level function: no __self__, no reset — must still work
        assert segment_pcm([silence_pcm(1.0)], amplitude_vad) == []


requires_real_model = pytest.mark.skipif(
    not vad_model_available(), reason="silero VAD model not in local cache"
)
requires_sapi_fixture = pytest.mark.skipif(
    sys.platform != "win32" or importlib.util.find_spec("av") is None,
    reason="SAPI speech fixtures need Windows (SAPI COM) plus av, which ships "
    "with faster-whisper and does the true-16 kHz resample",
)


@requires_real_model
class TestSileroVadRealModel:
    @pytest.fixture()
    def vad(self) -> Iterator[SileroVad]:
        # offline env BEFORE any ML import (PR-MED-009/-014 pattern)
        apply_offline_env()
        pytest.importorskip("onnxruntime")
        pytest.importorskip("numpy")
        yield SileroVad()

    def test_silence_only_yields_no_segments(self, vad: SileroVad) -> None:
        assert segment_pcm([silence_pcm(3.0)], vad.frame_probability) == []

    @requires_sapi_fixture
    def test_speech_boundaries_against_real_model(self, vad: SileroVad) -> None:
        speech = synthesize_speech_pcm(
            "The lighthouse keeper counted eleven boats returning with the tide."
        )
        speech_seconds = len(speech) / (BYTES_PER_SAMPLE * SAMPLE_RATE)
        pcm = silence_pcm(1.5) + speech + silence_pcm(1.5)
        chunks = [pcm[i : i + 32_000] for i in range(0, len(pcm), 32_000)]
        segments = segment_pcm(chunks, vad.frame_probability)

        assert segments, "real model detected no speech in a spoken fixture"
        # All detected speech lies inside the spoken span (with padding slack)
        assert segments[0].start_seconds >= 1.0
        assert segments[-1].end_seconds <= 1.5 + speech_seconds + 0.5
        # And covers a meaningful share of it (SAPI inserts natural pauses)
        covered = sum(s.duration_seconds for s in segments)
        assert covered >= 0.5 * speech_seconds

    @requires_sapi_fixture
    def test_consecutive_streams_are_independent(self, vad: SileroVad) -> None:
        # segment_pcm auto-resets the bound backend (PR-MED-011): two runs
        # of the same audio through the SAME instance must agree without
        # any manual reset between them.
        speech = synthesize_speech_pcm("A short reset check sentence.")
        first = segment_pcm([speech], vad.frame_probability)
        second = segment_pcm([speech], vad.frame_probability)
        assert first and second
        assert second[0].start_seconds == pytest.approx(first[0].start_seconds, abs=0.2)
