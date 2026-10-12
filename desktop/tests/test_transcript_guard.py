"""Invented-text-guard plan Tasks 1.4 and 4.1 (D3, C3, C4): the transcript
guard's rule and the one helper that applies it.

``guard_features`` (the numbers one VAD segment is judged by) and
``suspect_decision`` (the pure two-of-four rule) were built before the
measurement; ``mark_segment_words`` wires them into both transcription paths
(Phase 4) under decision 0.4's constants. The decision table below gives its
numbers explicitly under this file's own test set; the shipped constants are
pinned in ``TestShippedConstants``. The paths themselves are exercised in
``test_transcription.py``, ``test_attribution.py``,
``test_live_transcription.py`` and ``test_live_session.py``."""

from __future__ import annotations

import dataclasses
import inspect
from typing import Any

import pytest

from scribe_desktop.speech import SpeechSegment, TranscribedWord
from scribe_desktop.transcription import (
    CLINICAL_INITIAL_PROMPT,
    GUARD_MAX_SECONDS,
    GUARD_MEAN_PROBABILITY,
    GUARD_MIN_WORDS,
    GUARD_NO_SPEECH_PROB,
    GUARD_WORDS_PER_SECOND,
    GuardFeatures,
    MarkedSegment,
    TranscriptWord,
    guard_features,
    mark_segment_words,
    mark_words,
    suspect_decision,
)


def _decision(features: GuardFeatures) -> bool:
    """The rule under this file's test constant set (explicit numbers; not
    decision 0.4's): 3 words, 1.5 s, 4.0 words/s, mean probability 0.5,
    no-speech 0.6."""
    return suspect_decision(
        features,
        min_words=3,
        max_seconds=1.5,
        words_per_second=4.0,
        mean_probability=0.5,
        no_speech_prob=0.6,
    )


def _decide(**overrides: Any) -> bool:
    return _decision(dataclasses.replace(_QUIET, **overrides))


def _words(
    texts: list[str],
    *,
    start: float = 0.0,
    step: float = 0.2,
    probability: float = 0.9,
    no_speech: float | None = None,
) -> list[TranscribedWord]:
    return [
        TranscribedWord(
            text,
            start + index * step,
            start + (index + 1) * step,
            probability,
            decode_no_speech_prob=no_speech,
        )
        for index, text in enumerate(texts)
    ]


def _marked(*texts: str) -> MarkedSegment:
    words = tuple(
        TranscriptWord(
            word_text=text, start_seconds=0.0, end_seconds=0.1, probability=0.9, uncertain=False
        )
        for text in texts
    )
    return (SpeechSegment(0.0, 1.0), words)


# A segment that raises no signal under CONSTANTS: 3 words in 1.0 s (3.0
# words/s), mean probability 0.9, no decode number, no echo, previous held text.
_QUIET = guard_features(_words(["one", "two", "three"], step=0.3), SpeechSegment(0.0, 1.0), [])
assert _QUIET.words_per_second == 3.0


class TestDecisionTable:
    def test_a_quiet_segment_is_not_suspect(self) -> None:
        assert _decide() is False

    def test_rate_alone_never_flags(self) -> None:
        assert _decide(words_per_second=9.0) is False

    def test_rate_with_an_empty_previous_never_flags(self) -> None:
        assert _decide(words_per_second=9.0, previous_empty=True) is False

    def test_low_probability_with_an_empty_previous_never_flags(self) -> None:
        assert _decide(mean_probability=0.2, previous_empty=True) is False

    def test_no_no_no_never_flags(self) -> None:
        # "No, no, no." — 3 words, 0.8 s, probability 0.9: 3.75 words/s.
        features = guard_features(
            _words(["No,", "no,", "no."], step=0.25), SpeechSegment(2.0, 2.8), [_marked("")]
        )
        assert features.word_count == 3
        assert features.words_per_second == pytest.approx(3.75)
        assert features.previous_empty is True  # a cough before it
        assert _decision(features) is False
        # With the rate bound below it, rate DOES fire — and rate plus the
        # cough still never flags (D3).
        assert (
            suspect_decision(
                features,
                min_words=3,
                max_seconds=1.5,
                words_per_second=3.5,
                mean_probability=0.5,
                no_speech_prob=0.6,
            )
            is False
        )

    def test_the_observed_shape_flags(self) -> None:
        # 4 words in a 0.9 s VAD segment (span 0.8 s), mean probability 0.35,
        # directly after a segment with no words: 4.44 words/s + low probability.
        features = guard_features(
            _words(["Four", "out", "of", "ten."], probability=0.35),
            SpeechSegment(5.0, 5.9),
            [_marked("")],
        )
        assert features.word_count == 4
        assert features.vad_seconds == pytest.approx(0.9)
        assert features.word_span_seconds == pytest.approx(0.8)
        assert features.words_per_second == pytest.approx(4 / 0.9)
        assert features.mean_probability == pytest.approx(0.35)
        assert features.no_speech_prob is None
        assert features.previous_empty is True
        assert _decision(features) is True

    def test_rate_and_low_probability_flag(self) -> None:
        assert _decide(words_per_second=5.0, mean_probability=0.3) is True

    def test_echo_with_an_empty_previous_flags(self) -> None:
        assert _decide(primer_echo=True, previous_empty=True) is True

    def test_echo_alone_does_not_flag(self) -> None:
        assert _decide(primer_echo=True) is False

    def test_no_speech_with_an_empty_previous_flags(self) -> None:
        assert _decide(no_speech_prob=0.8, previous_empty=True) is True

    def test_no_speech_alone_does_not_flag(self) -> None:
        assert _decide(no_speech_prob=0.8) is False

    def test_no_speech_at_the_bound_is_no_signal(self) -> None:
        assert _decide(no_speech_prob=0.6, previous_empty=True) is False

    def test_rate_at_the_bound_is_a_signal(self) -> None:
        assert _decide(words_per_second=4.0, mean_probability=0.49) is True

    def test_probability_at_the_bound_is_no_signal(self) -> None:
        assert _decide(words_per_second=4.0, mean_probability=0.5) is False

    def test_none_decode_numbers_contribute_nothing(self) -> None:
        assert _decide(no_speech_prob=None, previous_empty=True) is False
        assert _decide(no_speech_prob=None, primer_echo=True) is False

    def test_too_few_words_is_never_suspect(self) -> None:
        assert (
            _decide(
                word_count=2,
                words_per_second=9.0,
                mean_probability=0.1,
                primer_echo=True,
                no_speech_prob=0.99,
                previous_empty=True,
            )
            is False
        )

    def test_a_long_segment_is_never_suspect(self) -> None:
        assert (
            _decide(
                vad_seconds=1.6,
                words_per_second=9.0,
                mean_probability=0.1,
                primer_echo=True,
                no_speech_prob=0.99,
            )
            is False
        )

    def test_a_segment_at_the_length_bound_is_judged(self) -> None:
        assert _decide(vad_seconds=1.5, words_per_second=9.0, mean_probability=0.1) is True

    def test_a_segment_with_no_words_is_never_suspect(self) -> None:
        features = guard_features([], SpeechSegment(0.0, 0.5), [_marked("")])
        assert features.word_count == 0
        assert features.mean_probability is None
        assert features.words_per_second == 0.0
        assert _decision(features) is False


class TestFeatures:
    def test_rate_uses_the_longer_of_the_vad_and_the_word_span(self) -> None:
        # 3 words stamped across 1.2 s inside a 0.6 s VAD segment: 3 / 1.2.
        features = guard_features(
            _words(["a", "b", "c"], step=0.4), SpeechSegment(0.0, 0.6), []
        )
        assert features.word_span_seconds == pytest.approx(1.2)
        assert features.words_per_second == pytest.approx(2.5)

    def test_blank_words_are_not_counted(self) -> None:
        features = guard_features(
            [*_words(["Yes", "okay"]), TranscribedWord("  ", 0.4, 0.6, 0.1)],
            SpeechSegment(0.0, 1.0),
            [],
        )
        assert features.word_count == 2
        assert features.mean_probability == pytest.approx(0.9)

    def test_no_speech_is_the_maximum_over_the_words(self) -> None:
        words = [
            *_words(["one", "two"], no_speech=0.2),
            *_words(["three"], start=0.4, no_speech=0.8),
            *_words(["four"], start=0.6),
        ]
        features = guard_features(words, SpeechSegment(0.0, 1.0), [])
        assert features.no_speech_prob == pytest.approx(0.8)

    def test_no_previous_segment_is_not_empty(self) -> None:
        assert guard_features(_words(["a"]), SpeechSegment(0.0, 1.0), []).previous_empty is False

    def test_the_last_previous_segment_decides(self) -> None:
        segment = SpeechSegment(3.0, 4.0)
        words = _words(["a"])
        assert guard_features(words, segment, [_marked("x"), _marked("")]).previous_empty is True
        assert guard_features(words, segment, [_marked(""), _marked("x")]).previous_empty is False
        assert guard_features(words, segment, [_marked(" ", "")]).previous_empty is True

    def test_the_forced_cut_second_half_flags_only_with_two_signals(self) -> None:
        # The live forced cut splits a long span unpadded: the second half's
        # previous segment is the first half, which holds text — not empty.
        first_half: MarkedSegment = _marked("the", "long", "span")
        echo_only = guard_features(
            _words(["cervical", "thoracic", "lumbar"]), SpeechSegment(30.0, 31.0), [first_half]
        )
        assert echo_only.previous_empty is False
        assert echo_only.primer_echo is True
        assert _decision(echo_only) is False
        echo_and_no_speech = guard_features(
            _words(["cervical", "thoracic", "lumbar"], no_speech=0.9),
            SpeechSegment(30.0, 31.0),
            [first_half],
        )
        assert _decision(echo_and_no_speech) is True


class TestPrimerEcho:
    def _echo(self, texts: list[str], primer: str | None = CLINICAL_INITIAL_PROMPT) -> bool:
        return guard_features(_words(texts), SpeechSegment(0.0, 1.0), [], primer=primer).primer_echo

    def test_three_contiguous_primer_tokens_are_an_echo(self) -> None:
        assert self._echo(["Cervical,", "thoracic,", "lumbar"]) is True

    def test_case_and_punctuation_do_not_matter(self) -> None:
        assert self._echo(["LUMBAR", "spine.", "Sacroiliac"]) is True

    def test_two_contiguous_primer_tokens_are_not_an_echo(self) -> None:
        assert self._echo(["lumbar", "spine", "today"]) is False

    def test_primer_tokens_out_of_order_are_not_an_echo(self) -> None:
        assert self._echo(["thoracic", "cervical", "lumbar"]) is False

    def test_a_run_inside_a_longer_segment_is_an_echo(self) -> None:
        assert self._echo(["so", "um", "rotator", "cuff", "supraspinatus", "yes"]) is True

    def test_fillers_are_dropped_before_the_run(self) -> None:
        # ``content_tokens`` drops disfluencies, so "um" does not break a run.
        assert self._echo(["rotator", "um", "cuff", "supraspinatus"]) is True

    def test_no_primer_means_no_echo(self) -> None:
        assert self._echo(["Cervical,", "thoracic,", "lumbar"], primer=None) is False

    def test_a_custom_primer_is_the_one_compared(self) -> None:
        custom = "Physiotherapy assessment today."
        assert self._echo(["physiotherapy", "assessment", "today"], primer=custom) is True
        assert self._echo(["Cervical,", "thoracic,", "lumbar"], primer="Physiotherapy.") is False


class TestShippedConstants:
    """Task 4.1: decision 0.4 (candidate c2) is what ``suspect_decision``
    defaults to — and what both paths therefore apply."""

    def test_the_values_are_decision_0_4s(self) -> None:
        assert GUARD_MIN_WORDS == 3
        assert GUARD_MAX_SECONDS == 1.5
        assert GUARD_WORDS_PER_SECOND == 4.0
        assert GUARD_MEAN_PROBABILITY == 0.6
        assert GUARD_NO_SPEECH_PROB == 0.6

    def test_they_are_the_rules_keyword_defaults(self) -> None:
        parameters = inspect.signature(suspect_decision).parameters
        defaults = {
            name: parameter.default
            for name, parameter in parameters.items()
            if parameter.kind is inspect.Parameter.KEYWORD_ONLY
        }
        assert defaults == {
            "min_words": 3,
            "max_seconds": 1.5,
            "words_per_second": 4.0,
            "mean_probability": 0.6,
            "no_speech_prob": 0.6,
        }

    def test_the_observed_shape_flags_under_them(self) -> None:
        # 4 words in a 0.9 s VAD segment, mean probability 0.35, after a
        # segment with no words: 4.44 words/s >= 4.0 and 0.35 < 0.6.
        features = guard_features(
            _words(["Four", "out", "of", "ten."], probability=0.35),
            SpeechSegment(5.0, 5.9),
            [_marked("")],
        )
        assert suspect_decision(features) is True

    def test_the_wider_probability_bound_is_the_one_shipped(self) -> None:
        # Mean probability 0.55 at 4.44 words/s: a signal under 0.6 (c2), none
        # under 0.45 (c1) — c2 was chosen because the incident's is unknown.
        features = guard_features(
            _words(["Four", "out", "of", "ten."], probability=0.55),
            SpeechSegment(5.0, 5.9),
            [_marked("x")],
        )
        assert suspect_decision(features) is True
        assert suspect_decision(features, mean_probability=0.45) is False

    def test_the_measured_fast_real_line_is_not_flagged(self) -> None:
        # The measurement's fastest short line at rate +5: 4 words in 0.68 s
        # (5.88 words/s), mean probability 0.806 — rate alone, never a flag,
        # even after an empty segment.
        features = guard_features(
            _words(["one", "two", "three", "four"], step=0.15, probability=0.806),
            SpeechSegment(1.0, 1.68),
            [_marked("")],
        )
        assert features.words_per_second == pytest.approx(4 / 0.68)
        assert suspect_decision(features) is False

    def test_no_no_no_is_not_flagged_under_them(self) -> None:
        features = guard_features(
            _words(["No,", "no,", "no."], step=0.25), SpeechSegment(2.0, 2.8), [_marked("")]
        )
        assert suspect_decision(features) is False


class TestMarkSegmentWords:
    """Task 4.1 (D3, D4, C3): the ONE helper both paths call — ``mark_words``
    then the rule; a suspect segment keeps every word, each marked."""

    _OBSERVED = ("so", "we", "go", "on")

    def _marked_and_guarded(
        self, probability: float, previous: list[MarkedSegment]
    ) -> tuple[tuple[TranscriptWord, ...], tuple[TranscriptWord, ...]]:
        words = _words(list(self._OBSERVED), start=0.05, probability=probability)
        segment = SpeechSegment(10.0, 10.9)
        guarded = mark_segment_words(
            words, segment, previous, threshold=0.6, offset_seconds=10.0
        )
        plain = mark_words(words, threshold=0.6, offset_seconds=10.0)
        return guarded, plain

    def test_a_segment_that_is_not_suspect_is_exactly_mark_words(self) -> None:
        guarded, plain = self._marked_and_guarded(0.95, [_marked("")])
        assert guarded == plain
        assert not any(word.suspect for word in guarded)

    def test_a_suspect_segment_keeps_every_word_each_marked(self) -> None:
        guarded, plain = self._marked_and_guarded(0.35, [_marked("")])
        assert len(guarded) == len(plain) == 4  # nothing dropped (C3)
        assert all(word.suspect for word in guarded)
        assert [word.model_copy(update={"suspect": False}) for word in guarded] == list(plain)
        # The offset and the uncertainty marks are mark_words' own.
        assert guarded[0].start_seconds == pytest.approx(10.05)
        assert all(word.uncertain for word in guarded)  # probability 0.35 < 0.6

    def test_a_blank_word_in_a_suspect_segment_is_kept_too(self) -> None:
        words = [
            *_words(list(self._OBSERVED), probability=0.35),
            TranscribedWord(" ", 0.8, 0.85, 0.1),
        ]
        guarded = mark_segment_words(
            words, SpeechSegment(0.0, 0.9), [_marked("")], threshold=0.6, offset_seconds=0.0
        )
        assert len(guarded) == 5
        assert all(word.suspect for word in guarded)

    def test_the_previous_list_is_read_not_changed(self) -> None:
        previous = [_marked("x"), _marked("")]
        mark_segment_words(
            _words(list(self._OBSERVED), probability=0.35),
            SpeechSegment(0.0, 0.9),
            previous,
            threshold=0.6,
            offset_seconds=0.0,
        )
        assert previous == [_marked("x"), _marked("")]

    def test_one_echo_flags_only_after_an_empty_segment(self) -> None:
        # 3 primer words in a 1.4 s segment (2.1 words/s), probability 0.95:
        # the echo is the one signal, so the previous segment decides.
        echo = _words(["Cervical,", "thoracic,", "lumbar"], step=0.4, probability=0.95)
        segment = SpeechSegment(0.0, 1.4)

        def guarded(previous: list[MarkedSegment]) -> bool:
            words = mark_segment_words(
                echo, segment, previous, threshold=0.6, offset_seconds=0.0
            )
            return all(word.suspect for word in words)

        assert guarded([_marked("")]) is True
        assert guarded([_marked("x")]) is False
        assert guarded([]) is False  # no previous segment is not empty
