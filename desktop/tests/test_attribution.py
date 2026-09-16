"""Practitioner-profile plan Phase 2 (Tasks 2.1 + 2.2): voice attribution in
the transcription pipeline and the transcript's attribution fields.

Layers:
- pure unit tests (numpy-only): ``attribute_speakers`` / ``enrolled_cluster``
  over synthetic similarities and embeddings — matched cluster + 2-means
  remainder, all matched, none matched, ties, missing similarities
- the transcript model: the three fields round-trip, an old artefact reads
  unchanged, and the validators refuse a lying ``enrolled_speaker``, an
  out-of-range similarity and a partial field set
- mock-provider pipeline tests over encrypted stores with
  ``MockSpeakerEmbedder`` injected (no ML stack): the document fields, the
  D13 label scheme, the degenerate policy, the per-segment embed inside the
  window, both entry points, and the byte-for-byte path without inputs

No clinical audio anywhere: fixtures are tones and silence.
"""

from __future__ import annotations

import json
import math
import struct
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from scribe_desktop.benchmark import apply_offline_env
from scribe_desktop.practitioner_profile import ConsentRecord, PractitionerProfile
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import KEY_FILENAME, SessionChunkStore, wrap_key_to_file
from scribe_desktop.speaker_embedding import MOCK_MODEL_ID, MockSpeakerEmbedder
from scribe_desktop.speech import (
    BYTES_PER_SAMPLE,
    SAMPLE_RATE,
    MockSpeechProvider,
    SpeechSegment,
    TranscribedWord,
)
from scribe_desktop.transcription import (
    MIN_ATTRIBUTION_PCM_BYTES,
    SPEAKER_1,
    SPEAKER_2,
    SPEAKER_3,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
    attribute_speakers,
    enrolled_cluster,
    extract_segment_pcm,
    read_transcript,
    recover_session_transcription,
    segment_has_text,
    transcribe_session,
    words_have_text,
    write_transcript,
)
from scribe_desktop.ui import models

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-only")


@pytest.fixture(autouse=True)
def _offline_env() -> None:
    apply_offline_env()


# ---------------------------------------------------------------------------
# synthetic PCM helpers (mirrors test_transcription.py)
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


def _make_store(session_dir: Path, pcm: bytes, *, real_key: bool = False) -> SessionCrypto:
    """Encrypted store with a stub key file, or (``real_key``) a real
    DPAPI-wrapped one for the recovery entry point."""
    session_dir.mkdir(parents=True, exist_ok=True)
    crypto = SessionCrypto()
    if real_key:
        wrap_key_to_file(crypto, session_dir)
    else:
        (session_dir / KEY_FILENAME).write_bytes(b"\0" * 64)
    store = SessionChunkStore.create(session_dir / "audio.enc", crypto, session_dir.name)
    for i in range(0, len(pcm), 32_000):
        store.append_chunk(pcm[i : i + 32_000])
    store.finish()
    return crypto


E1 = (1.0, 0.0, 0.0, 0.0)
E2 = (0.0, 1.0, 0.0, 0.0)


def _profile(
    vector: Sequence[float] = E1, *, model_id: str = MOCK_MODEL_ID, model_sha256: str = ""
) -> PractitionerProfile:
    now = datetime.now(UTC)
    return PractitionerProfile(
        model_id=model_id,
        model_sha256=model_sha256,
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


def _segment_pcms(tmp_path: Path, name: str, pcm: bytes) -> list[bytes]:
    """The pipeline's own per-segment slices (a plain run first): the exact
    bytes ``MockSpeakerEmbedder``'s map is keyed by. ``name`` must be HEX —
    the directory name is the store's session id (32 lowercase hex chars)."""
    assert all(ch in "0123456789abcdef" for ch in name), "session ids are hex"
    session_dir = tmp_path / (name + "0" * (32 - len(name)))
    crypto = _make_store(session_dir, pcm)
    document = transcribe_session(session_dir, crypto, MockSpeechProvider(), amplitude_vad)
    segments = [
        SpeechSegment(start_seconds=s.start_seconds, end_seconds=s.end_seconds)
        for s in document.transcript_segments
    ]
    return list(extract_segment_pcm([pcm], segments))


def _attributed_run(
    tmp_path: Path,
    name: str,
    pcm: bytes,
    vectors: Sequence[Sequence[float]],
    *,
    profile: PractitionerProfile | None = None,
    provider: Any = None,
) -> tuple[TranscriptDocument, MockSpeakerEmbedder, Path, SessionCrypto]:
    slices = _segment_pcms(tmp_path, name, pcm)
    assert len(slices) == len(vectors), "one vector per pipeline segment"
    embedder = MockSpeakerEmbedder(dict(zip(slices, vectors, strict=True)))
    session_dir = tmp_path / (name + "1" * (32 - len(name)))
    crypto = _make_store(session_dir, pcm)
    document = transcribe_session(
        session_dir,
        crypto,
        provider if provider is not None else MockSpeechProvider(),
        amplitude_vad,
        speaker_embedder=embedder,
        enrolled_profile=profile if profile is not None else _profile(),
    )
    assert embedder.embedded_lengths == [len(s) for s in slices]  # once each, in order
    return document, embedder, session_dir, crypto


# ---------------------------------------------------------------------------
# pure attribution (numpy-only)
# ---------------------------------------------------------------------------


class TestAttributeSpeakers:
    @pytest.fixture(autouse=True)
    def _np(self) -> None:
        self.np = pytest.importorskip("numpy")

    def _rows(self, *rows: Sequence[float]) -> list[Any]:
        return [self.np.asarray(row, dtype=self.np.float32) for row in rows]

    def test_empty_input_is_empty(self) -> None:
        assert attribute_speakers([], [], [], self.np) == []

    def test_matched_segments_are_speaker_1_and_a_lone_remainder_is_speaker_2(self) -> None:
        labels = attribute_speakers(
            [0.9, 0.1, 0.8], self._rows((0, 0), (5, 5), (0, 0)), [True, True, True], self.np
        )
        assert labels == [SPEAKER_1, SPEAKER_2, SPEAKER_1]

    def test_the_whole_remainder_is_speaker_2_even_when_its_features_differ(self) -> None:
        """D13 as amended (Task 2.6): the unmatched segments are NOT clustered
        among themselves — two clearly different remainder embeddings still
        share ``speaker_2``; ``speaker_3`` waits for D-S1."""
        labels = attribute_speakers(
            [0.9, 0.1, 0.2, 0.1],
            self._rows((0, 0), (5, 5), (-5, -5), (5, 5)),
            [True] * 4,
            self.np,
        )
        assert labels == [SPEAKER_1, SPEAKER_2, SPEAKER_2, SPEAKER_2]
        assert SPEAKER_3 not in labels

    def test_a_degenerate_remainder_is_all_speaker_2(self) -> None:
        labels = attribute_speakers(
            [0.9, 0.1, 0.1], self._rows((0, 0), (5, 5), (5, 5)), [True] * 3, self.np
        )
        assert labels == [SPEAKER_1, SPEAKER_2, SPEAKER_2]

    def test_threshold_is_inclusive_and_a_missing_similarity_never_matches(self) -> None:
        labels = attribute_speakers(
            [0.5, None], self._rows((0, 0), (5, 5)), [True, True], self.np, threshold=0.5
        )
        assert labels == [SPEAKER_1, SPEAKER_2]
        labels = attribute_speakers(
            [None, None], self._rows((0, 0), (5, 5)), [True, True], self.np
        )
        assert labels == [SPEAKER_1, SPEAKER_2]  # zero matches: ordinary 2-means

    def test_zero_matches_takes_the_higher_similarity_cluster_as_speaker_1(self) -> None:
        # Cluster A = rows 0 and 2 (appears first), cluster B = row 1; B has the
        # higher mean similarity, so B is the practitioner despite appearing second.
        labels = attribute_speakers(
            [0.1, 0.4, 0.2], self._rows((0, 0), (5, 5), (0, 0)), [True] * 3, self.np
        )
        assert labels == [SPEAKER_2, SPEAKER_1, SPEAKER_2]

    def test_zero_matches_chooses_among_clusters_with_text_only(self) -> None:
        # B has the higher similarity but no text: A stays speaker_1.
        labels = attribute_speakers(
            [0.1, 0.4, 0.2], self._rows((0, 0), (5, 5), (0, 0)), [True, False, True], self.np
        )
        assert labels == [SPEAKER_1, SPEAKER_2, SPEAKER_1]

    def test_zero_matches_and_no_text_keeps_the_clustering_order(self) -> None:
        labels = attribute_speakers(
            [0.1, 0.4], self._rows((0, 0), (5, 5)), [False, False], self.np
        )
        assert labels == [SPEAKER_1, SPEAKER_2]

    def test_single_segment_without_a_match_is_speaker_1(self) -> None:
        assert attribute_speakers([0.1], self._rows((0, 0)), [True], self.np) == [SPEAKER_1]

    def test_length_mismatch_is_refused(self) -> None:
        with pytest.raises(ValueError):
            attribute_speakers([0.1], self._rows((0, 0), (1, 1)), [True], self.np)


class TestEnrolledCluster:
    def test_highest_mean_among_textual_labels_with_an_fsum_mean(self) -> None:
        chosen = enrolled_cluster(
            [SPEAKER_1, SPEAKER_2, SPEAKER_1], [0.2, 0.9, 0.4], [True, True, True]
        )
        assert chosen == (SPEAKER_2, 0.9)
        chosen = enrolled_cluster(
            [SPEAKER_1, SPEAKER_2, SPEAKER_1], [0.2, 0.9, 0.4], [True, False, True]
        )
        assert chosen is not None
        assert chosen[0] == SPEAKER_1
        assert chosen[1] == math.fsum([0.2, 0.4]) / 2

    def test_ties_go_to_the_first_appearing_label(self) -> None:
        assert enrolled_cluster([SPEAKER_2, SPEAKER_1], [0.5, 0.5], [True, True]) == (
            SPEAKER_2,
            0.5,
        )

    def test_none_when_no_label_has_text_or_no_similarity_exists(self) -> None:
        assert enrolled_cluster([SPEAKER_1, SPEAKER_2], [0.9, 0.1], [False, False]) is None
        assert enrolled_cluster([SPEAKER_1, SPEAKER_2], [None, None], [True, True]) is None
        assert enrolled_cluster([], [], []) is None

    def test_a_textual_label_without_a_similarity_is_not_a_candidate(self) -> None:
        assert enrolled_cluster([SPEAKER_1, SPEAKER_2], [None, 0.1], [True, True]) == (
            SPEAKER_2,
            0.1,
        )

    def test_float_dust_is_bounded_to_the_cosine_range_only(self) -> None:
        chosen = enrolled_cluster([SPEAKER_1], [1.0 + 1e-12], [True])
        assert chosen == (SPEAKER_1, 1.0)
        chosen = enrolled_cluster([SPEAKER_1], [-0.7], [True])
        assert chosen == (SPEAKER_1, -0.7)  # raw cosines stay negative: no 0-1 clamp

    def test_length_mismatch_is_refused(self) -> None:
        with pytest.raises(ValueError):
            enrolled_cluster([SPEAKER_1], [0.1, 0.2], [True])


# ---------------------------------------------------------------------------
# the transcript model's attribution fields (no numpy)
# ---------------------------------------------------------------------------


def _word(text: str) -> TranscriptWord:
    return TranscriptWord(
        word_text=text, start_seconds=0.0, end_seconds=0.2, probability=0.9, uncertain=False
    )


def _document(
    rows: Sequence[tuple[str, str]] = ((SPEAKER_1, "hello there"), (SPEAKER_2, "hi")),
    **fields: Any,
) -> TranscriptDocument:
    return TranscriptDocument(
        session_id="a" * 32,
        created_at=datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
        model_name="mock",
        sample_rate=SAMPLE_RATE,
        transcript_segments=tuple(
            TranscriptSegment(
                start_seconds=float(i),
                end_seconds=float(i) + 0.5,
                speaker=speaker,
                transcript_words=tuple(_word(t) for t in text.split()),
            )
            for i, (speaker, text) in enumerate(rows)
        ),
        **fields,
    )


ATTRIBUTED = {
    "enrolled_speaker": SPEAKER_2,
    "enrolment_similarity": 0.83,
    "speaker_model_id": MOCK_MODEL_ID,
}


class TestTranscriptDocumentAttributionFields:
    def test_defaults_are_none_and_the_schema_version_is_unchanged(self) -> None:
        document = _document()
        assert document.schema_version == 1
        assert document.enrolled_speaker is None
        assert document.enrolment_similarity is None
        assert document.speaker_model_id is None

    def test_round_trip_through_bytes_and_the_encrypted_artefact(self, tmp_path: Path) -> None:
        document = _document(**ATTRIBUTED)
        assert TranscriptDocument.from_bytes(document.to_bytes()) == document
        crypto = SessionCrypto()
        write_transcript(tmp_path, crypto, document)
        read = read_transcript(tmp_path, crypto)
        assert read == document
        assert read.enrolled_speaker == SPEAKER_2
        assert read.enrolment_similarity == 0.83
        assert read.speaker_model_id == MOCK_MODEL_ID

    def test_an_artefact_written_before_the_fields_reads_unchanged(self) -> None:
        payload = json.loads(_document().to_bytes())
        for field in ATTRIBUTED:
            payload.pop(field, None)
        read = TranscriptDocument.from_bytes(json.dumps(payload).encode("utf-8"))
        assert read == _document()

    def test_enrolled_speaker_must_name_a_segment_with_text(self) -> None:
        with pytest.raises(ValidationError, match="transcribed text"):
            _document(**{**ATTRIBUTED, "enrolled_speaker": "speaker_9"})
        rows = ((SPEAKER_1, "hello"), (SPEAKER_2, ""))  # speaker_2 exists but is textless
        with pytest.raises(ValidationError, match="transcribed text"):
            _document(rows, **ATTRIBUTED)
        # ...and the same label WITH text is accepted.
        assert _document(**ATTRIBUTED).enrolled_speaker == SPEAKER_2

    @pytest.mark.parametrize("value", [1.5, -1.0000001, math.nan, math.inf, -math.inf])
    def test_similarity_must_be_a_finite_cosine(self, value: float) -> None:
        with pytest.raises(ValidationError, match="cosine"):
            _document(**{**ATTRIBUTED, "enrolment_similarity": value})

    @pytest.mark.parametrize("value", [-1.0, 1.0, 0.0, -0.25])
    def test_the_whole_cosine_range_is_accepted_never_a_unit_interval(self, value: float) -> None:
        document = _document(**{**ATTRIBUTED, "enrolment_similarity": value})
        assert document.enrolment_similarity == value

    @pytest.mark.parametrize("dropped", sorted(ATTRIBUTED))
    def test_the_fields_are_set_together_or_not_at_all(self, dropped: str) -> None:
        partial = {k: v for k, v in ATTRIBUTED.items() if k != dropped}
        with pytest.raises(ValidationError, match="together"):
            _document(**partial)
        with pytest.raises(ValidationError, match="together"):
            _document(**{dropped: ATTRIBUTED[dropped]})

    def test_an_empty_model_id_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _document(**{**ATTRIBUTED, "speaker_model_id": ""})

    def test_segment_has_text_agrees_with_the_radios_source(self) -> None:
        rows = ((SPEAKER_1, "hello"), (SPEAKER_2, ""), (SPEAKER_3, "yes"))
        document = _document(rows)
        textual = {s.speaker for s in document.transcript_segments if segment_has_text(s)}
        assert textual == set(models.speaker_quotations(document))
        blank = TranscriptSegment(
            start_seconds=0.0,
            end_seconds=1.0,
            speaker=SPEAKER_1,
            transcript_words=(_word("   "),),
        )
        assert not segment_has_text(blank)
        assert segment_has_text(blank) == words_have_text(blank.transcript_words)
        assert not words_have_text(())


# ---------------------------------------------------------------------------
# the pipeline with MockSpeakerEmbedder injected (numpy-only, no ML stack)
# ---------------------------------------------------------------------------


class TestAttributedPipeline:
    @pytest.fixture(autouse=True)
    def _numpy(self) -> None:
        pytest.importorskip("numpy")

    def test_matched_cluster_is_speaker_1_and_the_document_carries_the_fields(
        self, tmp_path: Path
    ) -> None:
        pcm = _three_tones(220.0, 2600.0, 220.0)
        document, embedder, session_dir, crypto = _attributed_run(
            tmp_path, "aa", pcm, [E1, E2, E1]
        )
        assert [s.speaker for s in document.transcript_segments] == [
            SPEAKER_1,
            SPEAKER_2,
            SPEAKER_1,
        ]
        assert document.enrolled_speaker == SPEAKER_1
        assert document.enrolment_similarity == pytest.approx(1.0)
        assert document.speaker_model_id == embedder.model_id == MOCK_MODEL_ID
        assert read_transcript(session_dir, crypto) == document  # written with the fields

    def test_the_practitioner_is_speaker_1_even_when_heard_second(self, tmp_path: Path) -> None:
        """D13: the no-profile path would label these speaker_1, speaker_2,
        speaker_1 (first heard is speaker_1); with the profile the MATCHED
        voice is speaker_1 wherever it first appears, and the two unmatched
        segments — the same tone, not byte-identical slices — are ONE
        ``speaker_2`` (D13 as amended, Task 2.6: the remainder is no longer
        2-means-clustered, which used to split them into two labels)."""
        pcm = _three_tones(2600.0, 220.0, 2600.0)
        document, _embedder, _dir, _crypto = _attributed_run(tmp_path, "ab", pcm, [E2, E1, E2])
        assert [s.speaker for s in document.transcript_segments] == [
            SPEAKER_2,
            SPEAKER_1,
            SPEAKER_2,
        ]
        assert document.enrolled_speaker == SPEAKER_1

    def test_all_matched_is_all_speaker_1_with_the_fields_set(self, tmp_path: Path) -> None:
        pcm = _three_tones(220.0, 2600.0, 220.0)
        document, _embedder, _dir, _crypto = _attributed_run(tmp_path, "ac", pcm, [E1, E1, E1])
        assert {s.speaker for s in document.transcript_segments} == {SPEAKER_1}
        assert document.enrolled_speaker == SPEAKER_1
        assert document.enrolment_similarity == pytest.approx(1.0)

    def test_zero_matches_runs_ordinary_two_means_and_takes_the_higher_similarity(
        self, tmp_path: Path
    ) -> None:
        """D3: nothing clears 0.50, so the spectral 2-means decides the
        clusters (220 Hz vs 2600 Hz) and the cluster with the higher mean
        similarity — the MIDDLE tone here — becomes speaker_1."""
        low = (0.1, math.sqrt(1 - 0.1**2), 0.0, 0.0)  # cosine 0.1 against E1
        mid = (0.4, math.sqrt(1 - 0.4**2), 0.0, 0.0)  # cosine 0.4 against E1
        pcm = _three_tones(220.0, 2600.0, 220.0)
        document, _embedder, _dir, _crypto = _attributed_run(
            tmp_path, "ad", pcm, [low, mid, low]
        )
        assert [s.speaker for s in document.transcript_segments] == [
            SPEAKER_2,
            SPEAKER_1,
            SPEAKER_2,
        ]
        assert document.enrolled_speaker == SPEAKER_1
        assert document.enrolment_similarity == pytest.approx(0.4, abs=1e-6)

    def test_the_whole_remainder_is_speaker_2_whatever_its_voices(self, tmp_path: Path) -> None:
        """D13 as amended (Task 2.6): two clearly different unmatched tones
        (2600 Hz and 700 Hz) still share ``speaker_2`` — a second other voice
        is merged, as the no-profile path merges it today, until D-S1."""
        pcm = _three_tones(220.0, 2600.0, 700.0)
        document, _embedder, _dir, _crypto = _attributed_run(tmp_path, "ae", pcm, [E1, E2, E2])
        assert [s.speaker for s in document.transcript_segments] == [
            SPEAKER_1,
            SPEAKER_2,
            SPEAKER_2,
        ]
        assert document.enrolled_speaker == SPEAKER_1
        # Exactly two labels render and the manual-path radios have one each.
        assert set(models.speaker_quotations(document)) == {SPEAKER_1, SPEAKER_2}
        assert "speaker_3" not in models.format_transcript_text(document)

    def test_single_segment_is_speaker_1_with_its_own_similarity(self, tmp_path: Path) -> None:
        pcm = silence_pcm(1.0) + tone_pcm(1.5, frequency=220.0) + silence_pcm(1.0)
        document, _embedder, _dir, _crypto = _attributed_run(tmp_path, "af", pcm, [E1])
        assert [s.speaker for s in document.transcript_segments] == [SPEAKER_1]
        assert document.enrolled_speaker == SPEAKER_1
        assert document.enrolment_similarity == pytest.approx(1.0)

    def test_similarities_are_raw_cosines_and_a_negative_match_is_kept(
        self, tmp_path: Path
    ) -> None:
        anti = (-1.0, 0.0, 0.0, 0.0)
        pcm = _three_tones(220.0, 2600.0, 220.0)
        document, _embedder, _dir, _crypto = _attributed_run(
            tmp_path, "b1", pcm, [anti, anti, anti]
        )
        assert document.enrolment_similarity == pytest.approx(-1.0)
        assert document.enrolled_speaker == SPEAKER_1  # the tie falls to the first label

    def test_a_matched_but_textless_cluster_cannot_be_the_enrolled_speaker(
        self, tmp_path: Path
    ) -> None:
        """PR-MED-008: the first tone matches the profile but transcribed to
        nothing, so it has no radio; the confirmed cluster is the best of
        the clusters WITH text, at its own (low) similarity — visible."""

        class _SecondSegmentOnly:
            def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
                word = TranscribedWord(
                    text="hello", start_seconds=3.0, end_seconds=3.2, probability=0.9
                )
                return [word]

        pcm = silence_pcm(1.0) + tone_pcm(1.5, frequency=220.0) + silence_pcm(1.0)
        pcm += tone_pcm(1.5, frequency=2600.0) + silence_pcm(1.0)
        document, _embedder, _dir, _crypto = _attributed_run(
            tmp_path, "b2", pcm, [E1, E2], provider=_SecondSegmentOnly()
        )
        assert [s.speaker for s in document.transcript_segments] == [SPEAKER_1, SPEAKER_2]
        assert not segment_has_text(document.transcript_segments[0])
        assert document.enrolled_speaker == SPEAKER_2
        assert document.enrolment_similarity == pytest.approx(0.0)

    def test_no_transcribed_text_at_all_carries_no_attribution_fields(
        self, tmp_path: Path
    ) -> None:
        class _Silent:
            def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
                return []

        pcm = _three_tones(220.0, 2600.0, 220.0)
        document, embedder, _dir, _crypto = _attributed_run(
            tmp_path, "b3", pcm, [E1, E2, E1], provider=_Silent()
        )
        assert len(document.transcript_segments) == 3
        assert embedder.embedded_lengths  # attribution ran...
        assert document.enrolled_speaker is None  # ...but nothing can be confirmed
        assert document.enrolment_similarity is None
        assert document.speaker_model_id is None

    def test_no_segments_carries_no_attribution_fields_and_embeds_nothing(
        self, tmp_path: Path
    ) -> None:
        session_dir = tmp_path / ("b4" + "0" * 30)
        crypto = _make_store(session_dir, silence_pcm(3.0))
        embedder = MockSpeakerEmbedder()
        document = transcribe_session(
            session_dir,
            crypto,
            MockSpeechProvider(),
            amplitude_vad,
            speaker_embedder=embedder,
            enrolled_profile=_profile(),
        )
        assert document.transcript_segments == ()
        assert embedder.embedded_lengths == []
        assert document.enrolled_speaker is None
        assert document.speaker_model_id is None

    def test_without_both_inputs_the_document_is_byte_identical_to_the_plain_path(
        self, tmp_path: Path
    ) -> None:
        pcm = _three_tones(220.0, 2600.0, 220.0)
        plain_dir = tmp_path / ("b5" + "0" * 30)
        crypto = _make_store(plain_dir, pcm)
        plain = transcribe_session(plain_dir, crypto, MockSpeechProvider(), amplitude_vad)
        again_dir = tmp_path / ("b5" + "1" * 30)
        crypto2 = _make_store(again_dir, pcm)
        again = transcribe_session(
            again_dir,
            crypto2,
            MockSpeechProvider(),
            amplitude_vad,
            speaker_embedder=None,
            enrolled_profile=None,
        )
        assert again.transcript_segments == plain.transcript_segments
        assert [s.speaker for s in plain.transcript_segments] == [SPEAKER_1, SPEAKER_2, SPEAKER_1]
        for document in (plain, again):
            assert document.enrolled_speaker is None
            assert document.enrolment_similarity is None
            assert document.speaker_model_id is None

    def test_one_input_without_the_other_is_refused(self, tmp_path: Path) -> None:
        session_dir = tmp_path / ("b6" + "0" * 30)
        crypto = _make_store(session_dir, tone_pcm(1.0))
        with pytest.raises(ValueError, match="together"):
            transcribe_session(
                session_dir,
                crypto,
                MockSpeechProvider(),
                amplitude_vad,
                speaker_embedder=MockSpeakerEmbedder(),
            )
        with pytest.raises(ValueError, match="together"):
            transcribe_session(
                session_dir,
                crypto,
                MockSpeechProvider(),
                amplitude_vad,
                enrolled_profile=_profile(),
            )

    @pytest.mark.parametrize(
        "profile",
        [
            _profile(model_id="another-embedder-v1"),
            _profile(model_sha256="a" * 64),
            _profile((1.0, 0.0, 0.0, 0.0, 0.0)),
        ],
        ids=["model_id", "model_sha256", "embedding_dim"],
    )
    def test_a_profile_from_a_different_embedder_is_refused(
        self, tmp_path: Path, profile: PractitionerProfile
    ) -> None:
        session_dir = tmp_path / ("b7" + "0" * 30)
        crypto = _make_store(session_dir, tone_pcm(1.0))
        with pytest.raises(ValueError, match="different speaker embedder"):
            transcribe_session(
                session_dir,
                crypto,
                MockSpeechProvider(),
                amplitude_vad,
                speaker_embedder=MockSpeakerEmbedder(),
                enrolled_profile=profile,
            )

    def test_the_minimum_embed_slice_is_one_front_end_frame(self, tmp_path: Path) -> None:
        """The pipeline never asks the embedder for less than one 25 ms
        front-end frame (a shorter slice gets no similarity instead of a
        refusal); every VAD segment is far longer, so real slices are always
        embedded."""
        assert MIN_ATTRIBUTION_PCM_BYTES == 400 * BYTES_PER_SAMPLE
        pcm = _three_tones(220.0, 2600.0, 220.0)
        slices = _segment_pcms(tmp_path, "b8", pcm)
        assert all(len(s) >= MIN_ATTRIBUTION_PCM_BYTES for s in slices)

    @windows_only
    def test_recovery_entry_point_applies_the_profile(self, tmp_path: Path) -> None:
        pcm = _three_tones(220.0, 2600.0, 220.0)
        slices = _segment_pcms(tmp_path, "b9", pcm)
        embedder = MockSpeakerEmbedder(dict(zip(slices, [E1, E2, E1], strict=True)))
        session_dir = tmp_path / ("b9" + "1" * 30)
        _make_store(session_dir, pcm, real_key=True)
        outcome = recover_session_transcription(
            session_dir,
            MockSpeechProvider(),
            amplitude_vad,
            speaker_embedder=embedder,
            enrolled_profile=_profile(),
        )
        assert outcome.store_finished
        assert outcome.document.enrolled_speaker == SPEAKER_1
        assert outcome.document.speaker_model_id == MOCK_MODEL_ID
        assert read_transcript(session_dir, outcome.crypto) == outcome.document
        outcome.crypto.destroy()
