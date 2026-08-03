"""Step 9 tests: the transcription pipeline (`scribe_desktop.transcription`).

Layers:
- pure unit tests: uncertainty marking, segment-PCM extraction, speaker
  clustering (numpy-only), transcript artifact model + atomic write
- mock-provider pipeline tests over encrypted stores (no ML stack):
  uncertainty marks, speaker labels, atomic write, custody ordering,
  crash-restart idempotence
- controller integration (Windows: DPAPI custody) for finish -> transcribe
  -> queued -> Complete and the failure -> recoverable path
- one live end-to-end test against the real silero VAD + the RESOLVED
  whisper model (`medium` default, `small` fallback — Step 13 policy;
  skip-if-absent for CI; SAPI synthesis is Windows-only)

No clinical audio anywhere: fixtures are tones/silence or SAPI speech of
non-clinical text.
"""

from __future__ import annotations

import logging
import math
import struct
import sys
from pathlib import Path

import pytest

from scribe_desktop.audio_capture import MockCaptureBackend
from scribe_desktop.benchmark import OFFLINE_ENV, apply_offline_env
from scribe_desktop.logging_setup import PayloadTripwireFilter, dropped_record_count
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import (
    SessionActivityError,
    SessionController,
    SessionState,
)
from scribe_desktop.session_store import (
    KEY_FILENAME,
    TRANSCRIPT_FILENAME,
    SessionChunkStore,
    StoreCorruptError,
    complete_session,
    store_has_footer,
)
from scribe_desktop.speech import (
    BYTES_PER_SAMPLE,
    SAMPLE_RATE,
    MockSpeechProvider,
    SpeechSegment,
    TranscribedWord,
    vad_model_available,
)
from scribe_desktop.transcription import (
    CLINICAL_INITIAL_PROMPT,
    DEFAULT_WHISPER_MODEL,
    FALLBACK_WHISPER_MODEL,
    SPEAKER_1,
    SPEAKER_2,
    TranscriptDocument,
    TranscriptionModelError,
    TranscriptSegment,
    TranscriptWord,
    WhisperSpeechProvider,
    assign_words_to_segments,
    extract_segment_pcm,
    is_name_like_token,
    is_number_token,
    label_speakers,
    mark_words,
    pack_transcription_windows,
    read_transcript,
    recover_session_transcription,
    resolve_whisper_model,
    transcribe_session,
    whisper_model_available,
    write_transcript,
)

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-only")


@pytest.fixture(autouse=True)
def _offline_env() -> None:
    """Offline kill-switches active for every test in this file: the
    pipeline's ML-stack imports (numpy included) assert them (PR round 15)."""
    apply_offline_env()


# ---------------------------------------------------------------------------
# synthetic PCM helpers (mirrors test_speech.py)
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
    samples = struct.unpack(f"<{len(frame) // 2}h", frame)
    peak = max(abs(s) for s in samples)
    return 0.95 if peak > 1000 else 0.02


def _make_store(session_dir: Path, pcm: bytes, *, finish: bool = True) -> SessionCrypto:
    """Encrypted store with a stub key file (store-format tests only)."""
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / KEY_FILENAME).write_bytes(b"\0" * 64)
    crypto = SessionCrypto()
    store = SessionChunkStore.create(session_dir / "audio.enc", crypto, session_dir.name)
    for i in range(0, len(pcm), 32_000):
        store.append_chunk(pcm[i : i + 32_000])
    if finish:
        store.finish()
    else:
        store.close()
    return crypto


def _word(text: str, probability: float = 0.95) -> TranscribedWord:
    return TranscribedWord(
        text=text, start_seconds=0.0, end_seconds=0.2, probability=probability
    )


# ---------------------------------------------------------------------------
# uncertainty marking
# ---------------------------------------------------------------------------


class TestUncertaintyMarking:
    @pytest.mark.parametrize(
        "token",
        ["17", "3.5mg", "seventeen", "fourteenth", "Twenty", "hundred,",
         "twenty-one", "Thirty-fourth,", "one-third"],
    )
    def test_number_tokens(self, token: str) -> None:
        assert is_number_token(token)

    @pytest.mark.parametrize(
        "token", ["hello", "tide.", "returning", "", "well-known", "-"]
    )
    def test_non_number_tokens(self, token: str) -> None:
        assert not is_number_token(token)

    def test_name_like_requires_capital(self) -> None:
        assert is_name_like_token("Margaret", first_in_segment=False)
        assert not is_name_like_token("harbour", first_in_segment=False)
        assert not is_name_like_token("'quoted", first_in_segment=False)

    def test_segment_initial_names_still_marked(self) -> None:
        # PR round 15: an utterance can OPEN with a name; only common
        # sentence-starting function words are exempt at segment start.
        assert is_name_like_token("Margaret,", first_in_segment=True)
        assert not is_name_like_token("The", first_in_segment=True)
        assert not is_name_like_token("Okay", first_in_segment=True)
        assert not is_name_like_token("She", first_in_segment=True)

    def test_low_confidence_marked(self) -> None:
        words = mark_words([_word("harbour", probability=0.3)])
        assert words[0].uncertain
        confident = mark_words([_word("harbour", probability=0.9)])
        assert not confident[0].uncertain

    def test_numbers_and_names_marked_even_when_confident(self) -> None:
        (first, number, name) = mark_words(
            [_word("The"), _word("seventeen"), _word("Margaret")]
        )
        assert not first.uncertain  # common sentence starter, not a name
        assert number.uncertain
        assert name.uncertain
        # a NAME opening the segment is still marked (PR round 15)
        (opener,) = mark_words([_word("Margaret,")])
        assert opener.uncertain

    def test_offset_applied(self) -> None:
        (word,) = mark_words([_word("hello")], offset_seconds=10.0)
        assert word.start_seconds == pytest.approx(10.0)
        assert word.end_seconds == pytest.approx(10.2)
        assert word.word_text == "hello"


# ---------------------------------------------------------------------------
# extract_segment_pcm — streaming span extraction
# ---------------------------------------------------------------------------


class TestExtractSegmentPcm:
    def test_exact_spans_across_odd_chunks(self) -> None:
        pcm = bytes(range(256)) * 250  # 64 000 B = 2.0 s
        chunks = [pcm[i : i + 7_333] for i in range(0, len(pcm), 7_333)]
        segments = [
            SpeechSegment(start_seconds=0.25, end_seconds=0.75),
            SpeechSegment(start_seconds=1.0, end_seconds=1.5),
        ]
        extracted = list(extract_segment_pcm(chunks, segments))
        for segment, data in zip(segments, extracted, strict=True):
            lo = int(segment.start_seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE
            hi = int(segment.end_seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE
            assert data == pcm[lo:hi]

    def test_segment_past_audio_end_yields_partial(self) -> None:
        pcm = b"\x01" * 32_000  # 1.0 s
        segments = [SpeechSegment(start_seconds=0.5, end_seconds=1.5)]
        (data,) = list(extract_segment_pcm([pcm], segments))
        assert data == b"\x01" * 16_000  # what exists on disk

    def test_no_segments(self) -> None:
        assert list(extract_segment_pcm([b"\x01" * 100], [])) == []

    def test_overlapping_segments_rejected(self) -> None:
        segments = [
            SpeechSegment(start_seconds=0.0, end_seconds=1.0),
            SpeechSegment(start_seconds=0.5, end_seconds=1.5),
        ]
        with pytest.raises(ValueError, match="non-overlapping"):
            list(extract_segment_pcm([b"\0" * 64_000], segments))


# ---------------------------------------------------------------------------
# window packing + word->segment attribution (Step 13 batching, pure)
# ---------------------------------------------------------------------------


def _seg(start: float, end: float) -> SpeechSegment:
    return SpeechSegment(start_seconds=start, end_seconds=end)


class TestPackTranscriptionWindows:
    def test_empty(self) -> None:
        assert pack_transcription_windows([]) == []

    def test_single_segment(self) -> None:
        assert pack_transcription_windows([_seg(1.0, 4.0)]) == [(0, 1)]

    def test_packs_consecutive_segments_within_budget(self) -> None:
        segments = [_seg(0.0, 10.0), _seg(11.0, 20.0), _seg(21.0, 29.0)]
        assert pack_transcription_windows(segments) == [(0, 3)]

    def test_budget_overflow_starts_new_window(self) -> None:
        # fourth segment would stretch the span past 30 s from the first
        segments = [
            _seg(0.0, 10.0),
            _seg(11.0, 20.0),
            _seg(21.0, 29.0),
            _seg(29.5, 31.0),
        ]
        assert pack_transcription_windows(segments) == [(0, 3), (3, 4)]

    def test_span_exactly_at_budget_is_packed(self) -> None:
        segments = [_seg(0.0, 15.0), _seg(16.0, 30.0)]
        assert pack_transcription_windows(segments) == [(0, 2)]

    def test_gap_over_max_breaks_window(self) -> None:
        segments = [_seg(0.0, 2.0), _seg(2.5, 4.0), _seg(10.0, 12.0)]  # 6 s gap
        assert pack_transcription_windows(segments) == [(0, 2), (2, 3)]

    def test_gap_exactly_at_max_is_packed(self) -> None:
        segments = [_seg(0.0, 2.0), _seg(5.0, 6.0)]  # gap == 3.0 default
        assert pack_transcription_windows(segments) == [(0, 2)]

    def test_oversized_segment_gets_its_own_window(self) -> None:
        segments = [_seg(0.0, 1.0), _seg(2.0, 40.0), _seg(40.5, 41.0)]
        assert pack_transcription_windows(segments) == [(0, 1), (1, 2), (2, 3)]

    def test_oversized_first_segment(self) -> None:
        segments = [_seg(0.0, 45.0), _seg(45.5, 46.0)]
        assert pack_transcription_windows(segments) == [(0, 1), (1, 2)]

    def test_windows_partition_all_segments(self) -> None:
        segments = [_seg(i * 4.0, i * 4.0 + 2.0) for i in range(25)]
        windows = pack_transcription_windows(segments)
        covered = [i for first, last in windows for i in range(first, last)]
        assert covered == list(range(len(segments)))  # each exactly once, in order
        for first, last in windows:
            span = segments[last - 1].end_seconds - segments[first].start_seconds
            assert last - first == 1 or span <= 30.0

    def test_custom_budget_and_gap(self) -> None:
        segments = [_seg(0.0, 4.0), _seg(5.0, 9.0), _seg(10.0, 14.0)]
        assert pack_transcription_windows(segments, window_seconds=10.0) == [
            (0, 2),
            (2, 3),
        ]
        assert pack_transcription_windows(segments, max_gap_seconds=0.5) == [
            (0, 1),
            (1, 2),
            (2, 3),
        ]

    def test_invalid_parameters_rejected(self) -> None:
        with pytest.raises(ValueError, match="window_seconds"):
            pack_transcription_windows([_seg(0.0, 1.0)], window_seconds=0.0)
        with pytest.raises(ValueError, match="max_gap_seconds"):
            pack_transcription_windows([_seg(0.0, 1.0)], max_gap_seconds=-1.0)


class TestAssignWordsToSegments:
    @staticmethod
    def _tw(start: float, end: float, text: str = "w") -> TranscribedWord:
        return TranscribedWord(
            text=text, start_seconds=start, end_seconds=end, probability=0.9
        )

    def test_containment_attribution(self) -> None:
        segments = [_seg(10.0, 12.0), _seg(13.0, 15.0)]
        # window starts at 10.0; word times are window-relative
        words = [self._tw(0.2, 0.6, "a"), self._tw(3.2, 3.8, "b")]
        assigned = assign_words_to_segments(words, segments, window_start_seconds=10.0)
        assert [[w.text for w in group] for group in assigned] == [["a"], ["b"]]

    def test_gap_word_goes_to_nearest_segment_never_dropped(self) -> None:
        segments = [_seg(0.0, 2.0), _seg(4.0, 6.0)]
        words = [
            self._tw(2.0, 2.4, "near_left"),   # midpoint 2.2 -> left (0.2 vs 1.8)
            self._tw(3.4, 4.0, "near_right"),  # midpoint 3.7 -> right (1.7 vs 0.3)
        ]
        assigned = assign_words_to_segments(words, segments, window_start_seconds=0.0)
        assert [w.text for w in assigned[0]] == ["near_left"]
        assert [w.text for w in assigned[1]] == ["near_right"]

    def test_equidistant_gap_word_goes_to_earlier_segment(self) -> None:
        segments = [_seg(0.0, 2.0), _seg(4.0, 6.0)]
        words = [self._tw(2.8, 3.2, "middle")]  # midpoint 3.0: 1.0 vs 1.0
        assigned = assign_words_to_segments(words, segments, window_start_seconds=0.0)
        assert [w.text for w in assigned[0]] == ["middle"]
        assert assigned[1] == []

    def test_words_outside_window_ends_clamp_to_edge_segments(self) -> None:
        segments = [_seg(5.0, 6.0), _seg(7.0, 8.0)]
        words = [self._tw(-0.4, -0.2, "before"), self._tw(3.5, 3.9, "after")]
        assigned = assign_words_to_segments(words, segments, window_start_seconds=5.0)
        assert [w.text for w in assigned[0]] == ["before"]
        assert [w.text for w in assigned[1]] == ["after"]

    def test_partition_no_loss_no_duplication_order_kept(self) -> None:
        segments = [_seg(0.0, 1.0), _seg(1.5, 2.5), _seg(3.0, 4.0)]
        words = [self._tw(i * 0.25, i * 0.25 + 0.2, f"w{i}") for i in range(16)]
        assigned = assign_words_to_segments(words, segments, window_start_seconds=0.0)
        flattened = [w.text for group in assigned for w in group]
        assert flattened == [w.text for w in words]  # every word exactly once, ordered

    def test_empty_words(self) -> None:
        segments = [_seg(0.0, 1.0), _seg(2.0, 3.0)]
        assert assign_words_to_segments([], segments, window_start_seconds=0.0) == [
            [],
            [],
        ]

    def test_empty_segments_rejected(self) -> None:
        with pytest.raises(ValueError, match="must contain segments"):
            assign_words_to_segments([], [], window_start_seconds=0.0)


class TestWindowPcmSliceIdentity:
    def test_window_slices_equal_per_segment_extraction(self) -> None:
        """The pipeline slices per-segment PCM for the D8 embeddings out of
        the window buffer; those slices must be BIT-IDENTICAL to what the
        old per-segment ``extract_segment_pcm`` produced, so speaker
        clustering input is unchanged by batching."""
        pcm = bytes(range(256)) * 500  # 128 000 B = 4.0 s
        segments = [
            _seg(0.25, 0.75),
            _seg(1.0, 1.5),
            _seg(2.125, 3.0),
        ]
        per_segment = list(
            extract_segment_pcm([pcm], segments)
        )
        window = SpeechSegment(
            start_seconds=segments[0].start_seconds,
            end_seconds=segments[-1].end_seconds,
        )
        (window_pcm,) = list(extract_segment_pcm([pcm], [window]))
        window_byte_start = int(window.start_seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE
        for segment, expected in zip(segments, per_segment, strict=True):
            lo = (
                int(segment.start_seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE
                - window_byte_start
            )
            hi = (
                int(segment.end_seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE
                - window_byte_start
            )
            assert window_pcm[lo:hi] == expected


# ---------------------------------------------------------------------------
# speaker labels — D8 numpy-only clustering
# ---------------------------------------------------------------------------


class TestLabelSpeakers:
    def test_empty(self) -> None:
        assert label_speakers([]) == []

    def test_single_segment_single_speaker(self) -> None:
        assert label_speakers([tone_pcm(1.0)]) == [SPEAKER_1]

    def test_identical_segments_collapse_to_one_speaker(self) -> None:
        pytest.importorskip("numpy")
        pcm = tone_pcm(1.0)
        assert label_speakers([pcm, pcm, pcm]) == [SPEAKER_1] * 3

    def test_two_distinct_voices_alternating(self) -> None:
        pytest.importorskip("numpy")
        low = tone_pcm(1.0, frequency=220.0)
        high = tone_pcm(1.0, frequency=2600.0)
        labels = label_speakers([low, high, low, high])
        assert labels == [SPEAKER_1, SPEAKER_2, SPEAKER_1, SPEAKER_2]

    def test_first_segment_is_always_speaker_one(self) -> None:
        pytest.importorskip("numpy")
        labels = label_speakers(
            [tone_pcm(1.0, frequency=2600.0), tone_pcm(1.0, frequency=220.0)]
        )
        assert labels[0] == SPEAKER_1

    def test_empty_segment_pcm_degrades_to_single_speaker(self) -> None:
        assert label_speakers([tone_pcm(1.0), b""]) == [SPEAKER_1, SPEAKER_1]


# ---------------------------------------------------------------------------
# transcript artifact: model, atomic write, read path, tripwire
# ---------------------------------------------------------------------------


def _document(session_id: str = "a" * 32) -> TranscriptDocument:
    from datetime import UTC, datetime

    return TranscriptDocument(
        session_id=session_id,
        created_at=datetime.now(UTC),
        model_name="mock",
        sample_rate=SAMPLE_RATE,
        transcript_segments=(
            TranscriptSegment(
                start_seconds=1.0,
                end_seconds=2.0,
                speaker=SPEAKER_1,
                transcript_words=(
                    TranscriptWord(
                        word_text="seventeen",
                        start_seconds=1.1,
                        end_seconds=1.4,
                        probability=0.9,
                        uncertain=True,
                    ),
                ),
            ),
        ),
    )


class TestTranscriptArtifact:
    def test_serialization_round_trip(self) -> None:
        document = _document()
        assert TranscriptDocument.from_bytes(document.to_bytes()) == document

    def test_write_and_read_encrypted(self, tmp_path: Path) -> None:
        crypto = SessionCrypto()
        document = _document()
        write_transcript(tmp_path, crypto, document)
        assert (tmp_path / TRANSCRIPT_FILENAME).is_file()
        assert not (tmp_path / (TRANSCRIPT_FILENAME + ".tmp")).exists()
        assert read_transcript(tmp_path, crypto) == document

    def test_atomic_overwrite_of_stale_partial(self, tmp_path: Path) -> None:
        crypto = SessionCrypto()
        (tmp_path / TRANSCRIPT_FILENAME).write_bytes(b"partial garbage from a crash")
        document = _document()
        write_transcript(tmp_path, crypto, document)
        assert read_transcript(tmp_path, crypto).session_id == document.session_id

    def test_wrong_key_raises_corrupt(self, tmp_path: Path) -> None:
        write_transcript(tmp_path, SessionCrypto(), _document())
        with pytest.raises(StoreCorruptError, match="authentication"):
            read_transcript(tmp_path, SessionCrypto())

    def test_malformed_payload_raises_corrupt(self, tmp_path: Path) -> None:
        crypto = SessionCrypto()
        (tmp_path / TRANSCRIPT_FILENAME).write_bytes(crypto.encrypt(b'{"nope": 1}'))
        with pytest.raises(StoreCorruptError, match="malformed"):
            read_transcript(tmp_path, crypto)

    def test_tripwire_drops_transcript_representations(self) -> None:
        logger = logging.getLogger("test-transcript-tripwire")
        logger.setLevel(logging.INFO)
        logger.addHandler(logging.NullHandler())
        logger.addFilter(PayloadTripwireFilter())
        try:
            document = _document()
            before = dropped_record_count()
            logger.info("%s", repr(document))
            logger.info("%s", document.model_dump_json())
            logger.info("%s", repr(document.transcript_segments[0]))
            logger.info("%s", repr(document.transcript_segments[0].transcript_words[0]))
            assert dropped_record_count() - before == 4
        finally:
            logger.filters.clear()
            logger.handlers.clear()


class TestStoreHasFooter:
    def test_finished_store(self, tmp_path: Path) -> None:
        session_dir = tmp_path / ("d" * 32)
        _make_store(session_dir, tone_pcm(1.0), finish=True)
        assert store_has_footer(session_dir / "audio.enc")

    def test_unfinished_store(self, tmp_path: Path) -> None:
        session_dir = tmp_path / ("e" * 32)
        _make_store(session_dir, tone_pcm(1.0), finish=False)
        assert not store_has_footer(session_dir / "audio.enc")

    def test_truncated_footer(self, tmp_path: Path) -> None:
        session_dir = tmp_path / ("f" * 32)
        _make_store(session_dir, tone_pcm(1.0), finish=True)
        path = session_dir / "audio.enc"
        path.write_bytes(path.read_bytes()[:-10])
        assert not store_has_footer(path)

    def test_missing_file(self, tmp_path: Path) -> None:
        assert not store_has_footer(tmp_path / "nope.enc")


# ---------------------------------------------------------------------------
# mock-provider pipeline over encrypted stores
# ---------------------------------------------------------------------------


class TestTranscribeSessionMock:
    def test_full_pipeline_on_finished_store(self, tmp_path: Path) -> None:
        session_dir = tmp_path / ("1" * 32)
        pcm = silence_pcm(1.0) + tone_pcm(2.0) + silence_pcm(1.0)
        crypto = _make_store(session_dir, pcm)
        document = transcribe_session(
            session_dir, crypto, MockSpeechProvider(), amplitude_vad
        )

        assert document.session_id == session_dir.name
        assert document.sample_rate == SAMPLE_RATE
        assert len(document.transcript_segments) == 1
        segment = document.transcript_segments[0]
        assert segment.start_seconds == pytest.approx(1.0, abs=0.15)
        assert segment.end_seconds == pytest.approx(3.0, abs=0.15)
        assert segment.speaker == SPEAKER_1
        assert segment.transcript_words  # mock produced words
        for word in segment.transcript_words:
            # word times are offset into session time, inside the segment
            assert segment.start_seconds - 0.01 <= word.start_seconds
            assert word.end_seconds <= segment.end_seconds + 0.01
            assert word.uncertain  # "mock0" carries a digit -> number mark

        # artifact is on disk, decrypts under the SAME key, no temp residue
        assert read_transcript(session_dir, crypto) == document
        assert not (session_dir / (TRANSCRIPT_FILENAME + ".tmp")).exists()

    def test_silence_only_yields_empty_document(self, tmp_path: Path) -> None:
        session_dir = tmp_path / ("2" * 32)
        crypto = _make_store(session_dir, silence_pcm(2.0))
        document = transcribe_session(
            session_dir, crypto, MockSpeechProvider(), amplitude_vad
        )
        assert document.transcript_segments == ()
        assert read_transcript(session_dir, crypto) == document

    def test_two_voices_get_two_speakers(self, tmp_path: Path) -> None:
        pytest.importorskip("numpy")
        session_dir = tmp_path / ("3" * 32)
        gap = silence_pcm(1.0)
        pcm = (
            gap
            + tone_pcm(1.5, frequency=220.0)
            + gap
            + tone_pcm(1.5, frequency=2600.0)
            + gap
            + tone_pcm(1.5, frequency=220.0)
            + gap
        )
        crypto = _make_store(session_dir, pcm)
        document = transcribe_session(
            session_dir, crypto, MockSpeechProvider(), amplitude_vad
        )
        speakers = [s.speaker for s in document.transcript_segments]
        assert speakers == [SPEAKER_1, SPEAKER_2, SPEAKER_1]

    def test_post_finish_truncation_detected(self, tmp_path: Path) -> None:
        session_dir = tmp_path / ("4" * 32)
        crypto = _make_store(session_dir, tone_pcm(1.0))
        path = session_dir / "audio.enc"
        path.write_bytes(path.read_bytes()[:-40])  # chop the footer
        with pytest.raises(StoreCorruptError):
            transcribe_session(session_dir, crypto, MockSpeechProvider(), amplitude_vad)
        assert not (session_dir / TRANSCRIPT_FILENAME).exists()

    def test_unfinished_store_transcribes_without_footer(self, tmp_path: Path) -> None:
        session_dir = tmp_path / ("5" * 32)
        pcm = silence_pcm(0.5) + tone_pcm(1.0) + silence_pcm(0.5)
        crypto = _make_store(session_dir, pcm, finish=False)
        document = transcribe_session(
            session_dir, crypto, MockSpeechProvider(), amplitude_vad, require_footer=False
        )
        assert len(document.transcript_segments) == 1

    def test_crash_restart_is_idempotent(self, tmp_path: Path) -> None:
        session_dir = tmp_path / ("6" * 32)
        pcm = silence_pcm(0.5) + tone_pcm(1.0) + silence_pcm(0.5)
        crypto = _make_store(session_dir, pcm)
        # simulate a crash mid-processing: partial garbage transcript on disk
        (session_dir / TRANSCRIPT_FILENAME).write_bytes(b"\xde\xad partial")
        first = transcribe_session(session_dir, crypto, MockSpeechProvider(), amplitude_vad)
        assert read_transcript(session_dir, crypto) == first
        # and a SECOND restart still converges to an equivalent artifact
        second = transcribe_session(session_dir, crypto, MockSpeechProvider(), amplitude_vad)
        assert second.transcript_segments == first.transcript_segments

    def test_complete_ordering_after_pipeline(self, tmp_path: Path) -> None:
        session_dir = tmp_path / ("7" * 32)
        crypto = _make_store(session_dir, silence_pcm(0.5) + tone_pcm(1.0))
        transcribe_session(session_dir, crypto, MockSpeechProvider(), amplitude_vad)
        # Complete: fsync -> verify decrypt round-trip -> delete key custody
        complete_session(session_dir, crypto)
        assert not (session_dir / KEY_FILENAME).exists()
        assert crypto.destroyed

    def test_complete_keeps_key_when_transcript_tampered(self, tmp_path: Path) -> None:
        session_dir = tmp_path / ("8" * 32)
        crypto = _make_store(session_dir, silence_pcm(0.5) + tone_pcm(1.0))
        transcribe_session(session_dir, crypto, MockSpeechProvider(), amplitude_vad)
        path = session_dir / TRANSCRIPT_FILENAME
        blob = bytearray(path.read_bytes())
        blob[-1] ^= 0xFF
        path.write_bytes(bytes(blob))
        with pytest.raises(StoreCorruptError):
            complete_session(session_dir, crypto)
        assert (session_dir / KEY_FILENAME).exists()  # key retained
        assert not crypto.destroyed


class _CountingProvider:
    """Wraps a SpeechProvider and records the PCM length of every call —
    the batching regression pin (calls per WINDOW, not per segment)."""

    def __init__(self, inner: MockSpeechProvider) -> None:
        self._inner = inner
        self.call_pcm_lengths: list[int] = []

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        self.call_pcm_lengths.append(len(pcm))
        return self._inner.transcribe_segment(pcm, sample_rate)


class TestWindowedPipeline:
    """Step 13 batching: the pipeline transcribes per packed window while
    every per-segment contract (attribution, marks, speakers, no word
    loss) holds."""

    def test_provider_called_once_per_window_not_per_segment(
        self, tmp_path: Path
    ) -> None:
        session_dir = tmp_path / ("a1" * 16)
        gap = silence_pcm(1.0)  # 1 s gaps: same window (<= 3 s, span < 30 s)
        pcm = gap + tone_pcm(1.5) + gap + tone_pcm(1.5) + gap + tone_pcm(1.5) + gap
        crypto = _make_store(session_dir, pcm)
        provider = _CountingProvider(MockSpeechProvider())
        document = transcribe_session(session_dir, crypto, provider, amplitude_vad)
        assert len(document.transcript_segments) == 3
        assert len(provider.call_pcm_lengths) == 1  # ONE window call, was 3
        # the window PCM is the contiguous span incl. gaps: > sum of segments
        assert provider.call_pcm_lengths[0] > 3 * len(tone_pcm(1.5))

    def test_large_gap_splits_into_two_windows(self, tmp_path: Path) -> None:
        session_dir = tmp_path / ("b2" * 16)
        pcm = tone_pcm(1.0) + silence_pcm(5.0) + tone_pcm(1.0)  # 5 s > max gap
        crypto = _make_store(session_dir, pcm)
        provider = _CountingProvider(MockSpeechProvider())
        document = transcribe_session(session_dir, crypto, provider, amplitude_vad)
        assert len(document.transcript_segments) == 2
        assert len(provider.call_pcm_lengths) == 2
        # SECOND-window words must be offset by the SECOND window's start
        # (peer round 41): offsetting every window by the first window's
        # start would leave them stranded near t=0. The mock spans each
        # window's PCM, so its words must land inside their own segment.
        for segment in document.transcript_segments:
            assert segment.transcript_words, "each window produced words"
            for word in segment.transcript_words:
                assert segment.start_seconds - 0.01 <= word.start_seconds
                assert word.end_seconds <= segment.end_seconds + 0.01

    def test_no_word_loss_or_duplication_across_window(self, tmp_path: Path) -> None:
        session_dir = tmp_path / ("c3" * 16)
        gap = silence_pcm(1.0)
        pcm = gap + tone_pcm(1.5) + gap + tone_pcm(1.5) + gap
        crypto = _make_store(session_dir, pcm)
        provider = _CountingProvider(MockSpeechProvider())
        document = transcribe_session(session_dir, crypto, provider, amplitude_vad)

        # the mock emitted words across the WHOLE window (gaps included);
        # every one of them must appear exactly once in the document —
        # gap-centered words are attributed to the nearest segment, never
        # dropped, never duplicated
        (window_pcm_len,) = provider.call_pcm_lengths
        expected = MockSpeechProvider().transcribe_segment(
            b"\0" * window_pcm_len, SAMPLE_RATE
        )
        emitted = [
            w.word_text
            for seg in document.transcript_segments
            for w in seg.transcript_words
        ]
        assert emitted == [w.text for w in expected]

    def test_word_times_absolute_and_monotone(self, tmp_path: Path) -> None:
        session_dir = tmp_path / ("d4" * 16)
        gap = silence_pcm(1.0)
        pcm = gap + tone_pcm(1.5) + gap + tone_pcm(1.5) + gap
        crypto = _make_store(session_dir, pcm)
        document = transcribe_session(
            session_dir, crypto, MockSpeechProvider(), amplitude_vad
        )
        words = [
            w for seg in document.transcript_segments for w in seg.transcript_words
        ]
        assert words
        # absolute session time: first word starts at/after the first
        # segment's window start (~1 s), NOT at zero
        first_segment = document.transcript_segments[0]
        assert words[0].start_seconds >= first_segment.start_seconds - 0.01
        starts = [w.start_seconds for w in words]
        assert starts == sorted(starts)

    def test_speaker_labels_survive_batching(self, tmp_path: Path) -> None:
        """Alternating voices in ONE window still get per-segment D8 labels
        (embeddings come from window slices, bit-identical to the old
        per-segment extraction)."""
        pytest.importorskip("numpy")
        session_dir = tmp_path / ("e5" * 16)
        gap = silence_pcm(1.0)
        pcm = (
            gap
            + tone_pcm(1.5, frequency=220.0)
            + gap
            + tone_pcm(1.5, frequency=2600.0)
            + gap
            + tone_pcm(1.5, frequency=220.0)
            + gap
        )
        crypto = _make_store(session_dir, pcm)
        provider = _CountingProvider(MockSpeechProvider())
        document = transcribe_session(session_dir, crypto, provider, amplitude_vad)
        assert len(provider.call_pcm_lengths) == 1  # all three segments batched
        speakers = [s.speaker for s in document.transcript_segments]
        assert speakers == [SPEAKER_1, SPEAKER_2, SPEAKER_1]

    def test_oversized_segment_transcribed_in_own_window(self, tmp_path: Path) -> None:
        session_dir = tmp_path / ("f6" * 16)
        # one continuous 31 s tone -> a single VAD segment over the budget
        pcm = tone_pcm(31.0) + silence_pcm(0.5) + tone_pcm(1.0)
        crypto = _make_store(session_dir, pcm)
        provider = _CountingProvider(MockSpeechProvider())
        document = transcribe_session(session_dir, crypto, provider, amplitude_vad)
        segments = document.transcript_segments
        assert len(segments) >= 1
        assert segments[0].end_seconds - segments[0].start_seconds > 30.0
        assert segments[0].transcript_words  # words attributed, none lost
        # the oversized segment occupied a window by itself
        assert provider.call_pcm_lengths[0] >= int(30.0 * SAMPLE_RATE) * BYTES_PER_SAMPLE

    def test_capitalized_opener_exemption_is_per_segment_not_per_window(
        self, tmp_path: Path
    ) -> None:
        """Round 42 LOW-017 (lens C): `first_in_segment` (the name
        heuristic's capitalized-opener exemption) must apply to the first
        word ATTRIBUTED to each segment. A bug applying it only to the
        window's first word would mark the second segment's opening
        starter word ("Okay") — and every prior windowed test used
        lowercase digit-bearing mock words, so it would have passed."""
        session_dir = tmp_path / ("a7" * 16)
        pcm = (
            silence_pcm(1.0)
            + tone_pcm(1.5)
            + silence_pcm(1.0)
            + tone_pcm(1.5)
            + silence_pcm(0.5)
        )
        crypto = _make_store(session_dir, pcm)

        class _ScriptedProvider:
            """Fixed window-relative words: one for segment 1, two for
            segment 2 (positions chosen well inside each tone span)."""

            def transcribe_segment(
                self, pcm: bytes, sample_rate: int
            ) -> list[TranscribedWord]:
                def word(text: str, start: float, end: float) -> TranscribedWord:
                    return TranscribedWord(
                        text=text,
                        start_seconds=start,
                        end_seconds=end,
                        probability=0.99,
                    )

                return [
                    word("hello", 0.5, 0.7),  # segment 1 (lowercase)
                    word("Okay", 2.8, 3.0),  # segment 2 OPENER: starter word
                    word("Margaret", 3.1, 3.3),  # segment 2, mid-segment name
                ]

        document = transcribe_session(
            session_dir, crypto, _ScriptedProvider(), amplitude_vad
        )
        assert len(document.transcript_segments) == 2
        assert len(document.transcript_segments[0].transcript_words) == 1
        second = document.transcript_segments[1]
        texts = [w.word_text for w in second.transcript_words]
        assert texts == ["Okay", "Margaret"]
        by_text = {w.word_text: w for w in second.transcript_words}
        # Segment-2's OPENER is a common starter: exempt from the
        # capitalized-name mark (would be marked if the exemption were
        # window-global, since window-globally it is word index 1).
        assert by_text["Okay"].uncertain is False
        # A mid-segment capitalized non-starter is name-like: marked.
        assert by_text["Margaret"].uncertain is True


# ---------------------------------------------------------------------------
# WhisperSpeechProvider guards (no ML stack needed — guards fire first)
# ---------------------------------------------------------------------------


class TestWhisperProviderGuards:
    def test_requires_offline_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scribe_desktop.benchmark import OfflineEnvError

        for key in OFFLINE_ENV:
            monkeypatch.delenv(key, raising=False)
        with pytest.raises(OfflineEnvError):
            WhisperSpeechProvider(model_dir=Path("irrelevant"))

    def test_missing_model_raises_before_ml_import(self, tmp_path: Path) -> None:
        apply_offline_env()
        with pytest.raises(TranscriptionModelError, match="setup-models"):
            WhisperSpeechProvider(model_dir=tmp_path / "no-model")

    def test_unc_model_path_rejected(self) -> None:
        apply_offline_env()
        with pytest.raises(TranscriptionModelError, match="UNC"):
            WhisperSpeechProvider(model_dir=Path(r"\\evil-host\share\whisper"))


# ---------------------------------------------------------------------------
# Step 13 model policy: medium default, small visible fallback, clinical
# vocabulary priming.
# ---------------------------------------------------------------------------


def _fake_snapshot(local_app_data: Path, name: str) -> Path:
    """Minimally complete CT2 snapshot under a fake LOCALAPPDATA."""
    target = local_app_data / "ClinikoScribe" / "models" / "whisper" / name
    target.mkdir(parents=True, exist_ok=True)
    for filename in ("model.bin", "config.json", "vocabulary.txt"):
        (target / filename).write_bytes(b"x")
    return target


class TestModelPolicy:
    def test_step13_user_decision_pinned(self) -> None:
        # USER DECISION 2026-07-28 (Step 13 manual gate): default medium,
        # small retained as the fallback. A drive-by edit of either constant
        # must trip a test, not slip through.
        assert DEFAULT_WHISPER_MODEL == "medium"
        assert FALLBACK_WHISPER_MODEL == "small"

    def test_resolves_default_when_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        _fake_snapshot(tmp_path, DEFAULT_WHISPER_MODEL)
        assert resolve_whisper_model() == DEFAULT_WHISPER_MODEL

    def test_resolves_fallback_when_default_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        _fake_snapshot(tmp_path, FALLBACK_WHISPER_MODEL)
        assert resolve_whisper_model() == FALLBACK_WHISPER_MODEL

    def test_prefers_default_when_both_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        _fake_snapshot(tmp_path, DEFAULT_WHISPER_MODEL)
        _fake_snapshot(tmp_path, FALLBACK_WHISPER_MODEL)
        assert resolve_whisper_model() == DEFAULT_WHISPER_MODEL

    def test_returns_preferred_name_when_nothing_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # No usable model: return the PREFERRED name unchanged so the
        # provider's error message names it and its setup-models remedy.
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert resolve_whisper_model() == DEFAULT_WHISPER_MODEL

    def test_explicit_request_honoured_before_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        _fake_snapshot(tmp_path, "distil-small.en")
        _fake_snapshot(tmp_path, FALLBACK_WHISPER_MODEL)
        assert resolve_whisper_model("distil-small.en") == "distil-small.en"
        # ... but an absent explicit request still degrades to the fallback.
        assert resolve_whisper_model("distil-medium.en") == FALLBACK_WHISPER_MODEL

    def test_unc_localappdata_reports_unavailable_without_io(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Peer round 36 (PR-MED-012 pattern extended): availability probes
        # STAT the LOCALAPPDATA-derived path, so a UNC-redirected
        # LOCALAPPDATA must short-circuit to False BEFORE any filesystem
        # touch (no SMB I/O), for the default, the fallback, and the
        # resolver; the provider then raises its explicit UNC error.
        monkeypatch.setenv("LOCALAPPDATA", r"\\evil-host\share")
        assert not whisper_model_available()
        assert not whisper_model_available(FALLBACK_WHISPER_MODEL)
        assert resolve_whisper_model() == DEFAULT_WHISPER_MODEL
        apply_offline_env()
        with pytest.raises(TranscriptionModelError, match="UNC"):
            WhisperSpeechProvider()


class TestClinicalPrompt:
    def test_prompt_is_nonempty_prose(self) -> None:
        assert CLINICAL_INITIAL_PROMPT.strip()
        assert CLINICAL_INITIAL_PROMPT.isascii()

    def test_prompt_stays_inside_whisper_token_budget_proxy(self) -> None:
        # faster-whisper keeps only the LAST 223 prompt tokens and silently
        # drops the head of an overlong prompt. The real tokenizer measured
        # 193 tokens for this 66-word / 602-char text (2026-07-30; measured
        # density ~3.1 chars per token for this vocabulary). ML-free
        # proxies keep a guard runnable on CI: BOTH bounds must hold, and
        # the char bound is the tighter one (650 chars at ~3.1 chars/token
        # ≈ 208 tokens, under the documented 210 headroom bar). Peer round
        # 36: proxies cannot be exact — the test below runs the REAL
        # tokenizer whenever the model files are present (the dev
        # machine), which is the binding check.
        assert len(CLINICAL_INITIAL_PROMPT.split()) <= 70
        assert len(CLINICAL_INITIAL_PROMPT) <= 650

    @pytest.mark.skipif(
        not whisper_model_available(resolve_whisper_model()),
        reason="exact token count needs a local whisper snapshot's tokenizer",
    )
    def test_prompt_token_count_exact_with_real_tokenizer(self) -> None:
        # The binding budget check (peer round 36): measure the prompt the
        # exact way faster-whisper encodes it (leading space, no special
        # tokens) with the resolved model's own tokenizer file; 210 is the
        # documented headroom bar under the hard 223-token keep-window.
        tokenizers = pytest.importorskip("tokenizers")

        from scribe_desktop.transcription import default_whisper_model_dir

        model_dir = default_whisper_model_dir(resolve_whisper_model())
        tokenizer_path = model_dir / "tokenizer.json"
        if not tokenizer_path.is_file():
            pytest.skip("snapshot has no tokenizer.json (vocabulary layout)")
        tokenizer = tokenizers.Tokenizer.from_file(str(tokenizer_path))
        ids = tokenizer.encode(
            " " + CLINICAL_INITIAL_PROMPT.strip(), add_special_tokens=False
        ).ids
        assert len(ids) <= 210, (
            f"CLINICAL_INITIAL_PROMPT measures {len(ids)} tokens - over the "
            "documented 210 headroom bar (hard truncation at 223)"
        )

    def test_prompt_carries_no_patient_identifying_content(self) -> None:
        # Structural hygiene only (a test cannot judge semantics): no
        # digits (dates/DOBs/phone numbers) and none of the honorific
        # patterns that would smuggle an example patient name in.
        assert not any(ch.isdigit() for ch in CLINICAL_INITIAL_PROMPT)
        lowered = CLINICAL_INITIAL_PROMPT.lower()
        for honorific in ("mr ", "mr.", "mrs", "ms ", "ms.", "miss ", "dr ", "dr."):
            assert honorific not in lowered

    def test_prompt_covers_the_documented_clusters(self) -> None:
        # One sentinel per documented cluster: anatomy, presentation, exam
        # manoeuvre, technique, medication, units/scores.
        lowered = CLINICAL_INITIAL_PROMPT.lower()
        for sentinel in (
            "supraspinatus",
            "radiculopathy",
            "spurling",
            "mobilisation",
            "meloxicam",
            "out of ten",
        ):
            assert sentinel in lowered


class _RecordingWhisperModel:
    """Stands in for faster_whisper.WhisperModel: records transcribe kwargs."""

    calls: list[dict[str, object]] = []

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def transcribe(self, audio: object, **kwargs: object) -> tuple[list[object], None]:
        type(self).calls.append(dict(kwargs))
        return [], None


class TestProviderPromptWiring:
    """The provider must pass the priming prompt through to faster-whisper.

    Uses a recording fake injected as ``faster_whisper`` so the wiring is
    provable on CI without models; the live e2e below covers the real lib.
    """

    def _provider(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        **provider_kwargs: object,
    ) -> WhisperSpeechProvider:
        pytest.importorskip("numpy")  # provider's _numpy() is real
        apply_offline_env()
        import types

        snapshot = _fake_snapshot(tmp_path, "fake-model")
        fake = types.ModuleType("faster_whisper")
        fake.WhisperModel = _RecordingWhisperModel  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "faster_whisper", fake)
        _RecordingWhisperModel.calls = []
        return WhisperSpeechProvider(model_dir=snapshot, **provider_kwargs)  # type: ignore[arg-type]

    def test_default_passes_clinical_prompt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = self._provider(tmp_path, monkeypatch)
        assert provider.transcribe_segment(b"\x00\x00" * 160, 16_000) == []
        (call,) = _RecordingWhisperModel.calls
        assert call["initial_prompt"] == CLINICAL_INITIAL_PROMPT
        # Uncertainty marking still depends on these — priming must not
        # have disturbed them.
        assert call["word_timestamps"] is True
        assert call["condition_on_previous_text"] is False

    def test_none_disables_priming(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = self._provider(tmp_path, monkeypatch, initial_prompt=None)
        provider.transcribe_segment(b"\x00\x00" * 160, 16_000)
        (call,) = _RecordingWhisperModel.calls
        assert call["initial_prompt"] is None

    def test_custom_prompt_overrides(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = self._provider(
            tmp_path, monkeypatch, initial_prompt="physiotherapy assessment"
        )
        provider.transcribe_segment(b"\x00\x00" * 160, 16_000)
        (call,) = _RecordingWhisperModel.calls
        assert call["initial_prompt"] == "physiotherapy assessment"


# ---------------------------------------------------------------------------
# SessionController integration (DPAPI custody: Windows-only)
# ---------------------------------------------------------------------------


@windows_only
class TestControllerTranscription:
    def _finished_controller(self, tmp_path: Path) -> tuple[SessionController, str]:
        backend = MockCaptureBackend()
        controller = SessionController(backend, sessions_root=tmp_path)
        session = controller.start(0)
        backend.feed(silence_pcm(0.5) + tone_pcm(1.0) + silence_pcm(0.5))
        controller.finish()
        return controller, session.session_id

    def test_finish_transcribe_queue_complete(self, tmp_path: Path) -> None:
        controller, session_id = self._finished_controller(tmp_path)
        provider = MockSpeechProvider()

        result = controller.transcribe(
            lambda directory, crypto: transcribe_session(
                directory, crypto, provider, amplitude_vad
            )
        )
        assert result.state is SessionState.QUEUED
        session_dir = tmp_path / session_id
        assert (session_dir / TRANSCRIPT_FILENAME).is_file()

        completed = controller.complete()
        assert completed.state is SessionState.WRITTEN
        assert not (session_dir / KEY_FILENAME).exists()  # cryptographic deletion
        assert (session_dir / TRANSCRIPT_FILENAME).is_file()  # artifact retained

    def test_transcriber_failure_routes_to_recoverable_failed(
        self, tmp_path: Path
    ) -> None:
        controller, session_id = self._finished_controller(tmp_path)

        def broken(directory: Path, crypto: SessionCrypto) -> None:
            raise RuntimeError("model exploded")

        with pytest.raises(RuntimeError, match="model exploded"):
            controller.transcribe(broken)
        assert controller.state is SessionState.FAILED
        session_dir = tmp_path / session_id
        assert (session_dir / KEY_FILENAME).is_file()  # key retained
        assert (session_dir / "audio.enc").is_file()  # audio retained

    def test_transcribe_requires_processing_state(self, tmp_path: Path) -> None:
        controller = SessionController(MockCaptureBackend(), sessions_root=tmp_path)
        controller.start(0)  # recording, not processing
        with pytest.raises(SessionActivityError, match="processing"):
            controller.transcribe(lambda d, c: None)

    def test_recovery_restarts_transcription_from_audio(self, tmp_path: Path) -> None:
        # crash-mid-processing sim: session finished (footered store) but the
        # process died before/half-way through the transcript write.
        _controller, session_id = self._finished_controller(tmp_path)
        session_dir = tmp_path / session_id
        (session_dir / TRANSCRIPT_FILENAME).write_bytes(b"half a transcript")

        outcome = recover_session_transcription(
            session_dir, MockSpeechProvider(), amplitude_vad
        )
        assert outcome.store_finished  # footered store keeps enforcement
        assert outcome.document.session_id == session_id
        assert read_transcript(session_dir, outcome.crypto) == outcome.document
        # custody flow still closes normally afterwards
        complete_session(session_dir, outcome.crypto)
        assert not (session_dir / KEY_FILENAME).exists()

    def test_recovery_of_unfinished_store_tolerates_missing_footer(
        self, tmp_path: Path
    ) -> None:
        # crash-mid-recording sim: no Finish, no footer — recovery must
        # transcribe the durably written chunks without footer enforcement.
        from scribe_desktop.session_store import wrap_key_to_file

        session_dir = tmp_path / ("9" * 32)
        session_dir.mkdir()
        crypto = SessionCrypto()
        wrap_key_to_file(crypto, session_dir)
        store = SessionChunkStore.create(session_dir / "audio.enc", crypto, "9" * 32)
        pcm = silence_pcm(0.5) + tone_pcm(1.0) + silence_pcm(0.5)
        for i in range(0, len(pcm), 32_000):
            store.append_chunk(pcm[i : i + 32_000])
        store.close()  # crash: no footer

        outcome = recover_session_transcription(
            session_dir, MockSpeechProvider(), amplitude_vad
        )
        assert not outcome.store_finished  # UI must warn: tail may be missing
        assert len(outcome.document.transcript_segments) == 1
        assert read_transcript(session_dir, outcome.crypto) == outcome.document

    def test_concurrent_transcribe_refused_while_in_flight(
        self, tmp_path: Path
    ) -> None:
        # PR-HIGH-006 regression: a second transcribe() during an in-flight
        # run must be refused — never race on the transcript temp path.
        import threading

        controller, _session_id = self._finished_controller(tmp_path)
        started = threading.Event()
        release = threading.Event()

        def slow_transcriber(directory: Path, crypto: SessionCrypto) -> None:
            started.set()
            assert release.wait(timeout=10.0)

        worker = threading.Thread(
            target=lambda: controller.transcribe(slow_transcriber)
        )
        worker.start()
        try:
            assert started.wait(timeout=10.0)
            with pytest.raises(SessionActivityError, match="already in progress"):
                controller.transcribe(lambda d, c: None)
        finally:
            release.set()
            worker.join(timeout=10.0)
        assert controller.state is SessionState.QUEUED  # first run completed

    def test_discard_refused_while_transcribing(self, tmp_path: Path) -> None:
        # Round 42 MED-003: discard() must honour the same in-flight guard
        # as transcribe()/mark_queued() — a discard mid-run would destroy
        # the key under the live transcriber (PR-HIGH-006 family).
        import threading

        controller, _session_id = self._finished_controller(tmp_path)
        started = threading.Event()
        release = threading.Event()

        def slow_transcriber(directory: Path, crypto: SessionCrypto) -> None:
            started.set()
            assert release.wait(timeout=10.0)

        worker = threading.Thread(
            target=lambda: controller.transcribe(slow_transcriber)
        )
        worker.start()
        try:
            assert started.wait(timeout=10.0)
            with pytest.raises(SessionActivityError, match="in progress"):
                controller.discard()
        finally:
            release.set()
            worker.join(timeout=10.0)
        assert controller.state is SessionState.QUEUED  # run completed intact

    def test_mark_queued_refused_while_transcribing(self, tmp_path: Path) -> None:
        # PR-HIGH-008 regression: mark_queued must not bypass the in-flight
        # guard — queued would unlock Complete (key deletion) mid-write.
        import threading

        controller, _session_id = self._finished_controller(tmp_path)
        started = threading.Event()
        release = threading.Event()

        def slow_transcriber(directory: Path, crypto: SessionCrypto) -> None:
            started.set()
            assert release.wait(timeout=10.0)

        worker = threading.Thread(
            target=lambda: controller.transcribe(slow_transcriber)
        )
        worker.start()
        try:
            assert started.wait(timeout=10.0)
            with pytest.raises(SessionActivityError, match="in progress"):
                controller.mark_queued()
        finally:
            release.set()
            worker.join(timeout=10.0)
        assert controller.state is SessionState.QUEUED


# ---------------------------------------------------------------------------
# live end-to-end: real silero VAD + the RESOLVED whisper model (medium
# default, small fallback — mirrors production composition; skip-if-absent)
# ---------------------------------------------------------------------------

requires_live_stack = pytest.mark.skipif(
    sys.platform != "win32"
    or not vad_model_available()
    or not whisper_model_available(resolve_whisper_model()),
    reason="live e2e needs Windows (SAPI) + local silero and a whisper model "
    "(medium, or the small fallback)",
)


@requires_live_stack
class TestLiveEndToEnd:
    def test_record_transcribe_verify(self, tmp_path: Path) -> None:
        # offline env BEFORE any ML import (PR-MED-009/-014 pattern)
        apply_offline_env()
        pytest.importorskip("numpy")
        pytest.importorskip("onnxruntime")
        pytest.importorskip("faster_whisper")
        from sapi_fixture import synthesize_speech_pcm
        from scribe_desktop.speech import SileroVad

        speech = synthesize_speech_pcm(
            "Margaret counted seventeen boats near the lighthouse on Tuesday "
            "the fourteenth of March."
        )
        session_dir = tmp_path / ("a" * 32)
        pcm = silence_pcm(1.0) + speech + silence_pcm(1.0)
        crypto = _make_store(session_dir, pcm)

        vad = SileroVad()
        # Production composition: the resolved model (medium, or small on a
        # fallback-only machine) with the clinical priming default active.
        provider = WhisperSpeechProvider(model_name=resolve_whisper_model())
        document = transcribe_session(
            session_dir, crypto, provider, vad.frame_probability
        )

        assert document.transcript_segments, "no speech detected in live fixture"
        words = [
            word
            for segment in document.transcript_segments
            for word in segment.transcript_words
        ]
        assert len(words) >= 8, "whisper produced implausibly few words"
        text = " ".join(w.word_text.lower().strip(".,") for w in words)
        assert "seventeen" in text or "17" in text
        # numbers must carry uncertainty marks (plan: words, numbers, names)
        number_words = [w for w in words if is_number_token(w.word_text)]
        assert number_words and all(w.uncertain for w in number_words)
        # word probabilities are real (not all saturated placeholder 1.0)
        assert any(w.probability < 1.0 for w in words)
        # timestamps are ordered inside the session timeline
        assert all(w.end_seconds >= w.start_seconds for w in words)

        # transcript decrypts under the SAME session key; custody closes
        assert read_transcript(session_dir, crypto) == document
        complete_session(session_dir, crypto)
        assert not (session_dir / KEY_FILENAME).exists()
