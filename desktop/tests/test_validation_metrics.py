"""Pilot plan Task 2.3: the validation harness's metric contract (D8), by
hand-computed cases.

Every case the Done-when names is here, each with its alignment worked out
in the docstring or a comment: the empty transcript and the empty note, a
negation flip (deleted and inserted), a left/right swap, a dose change, a
fact the script marks absent, a fact stated twice, an unsupported
non-clinical word, one reference line split across two segments, two lines
merged into one segment and one note line, an unrelated warning in the same
segment as a material omission, a fact deleted by transcription, conflicting
confirmed config proposals for side, dose and negation (through the real
compose -> confirm -> finalise pipeline), an expected contradiction, an
omitted material fact lying between two unrelated omitted high-risk words
(silent, and it fails option (a)), and an overlapped pair of turns — plus
the type-level guard that no result can hold transcript or note text.

No clinical content: invented sentences only.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import textwrap
import typing
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from fixtures.heldout_transcripts import held_out_set
from scribe_desktop import validation
from scribe_desktop.note import (
    ConfirmationDecision,
    ExtractiveNoteProvider,
    GeneratedNote,
    GeneratedSection,
    NoteAssertion,
    NoteRequest,
    NoteSpan,
    NoteWarning,
    SourceCoords,
    compose_draft,
    content_tokens,
    finalise_note,
    normalise_token,
    reconstruct_span_text,
    segment_hedged,
    text_digest,
    text_holds_hedge,
    whole_utterance_assertion,
)
from scribe_desktop.note_check import (
    _LATERALITY_TOKENS,
    _MEDICATION_LEXICON,
    _POLARITY_TOKENS,
    _STRENGTH_UNITS,
    _omission_flag_token,
    clinician_line_omissions,
    omission_warnings,
    reconstruction_warnings,
)
from scribe_desktop.note_config import AutofillRule, NoteConfig, load_note_config
from scribe_desktop.transcription import (
    _NUMBER_WORDS,
    SPEAKER_1,
    SPEAKER_2,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
)
from scribe_desktop.ui.models import OMISSION_CODES
from scribe_desktop.validation import (
    REFERENCE_HEDGES,
    EncounterMetrics,
    EncounterOutcome,
    EncounterScript,
    FactOutcome,
    HarnessInputs,
    PassRule,
    ProseCounts,
    ReferenceReading,
    RuleError,
    WordErrors,
    class_breaches,
    class_counts,
    confirm_all,
    encounter_metrics,
    is_structured_claim_word,
    reference_reading,
    rule_failures,
    run_passed,
    run_passed_v1,
    v1_failures,
    word_errors,
)

SESSION_ID = "c" * 32
DIGEST = "sha256-v1:" + "0" * 64
_NOW = datetime(2026, 10, 4, 21, 0, tzinfo=UTC)
OPTION_A = PassRule(schema_version=1, rule_name="option-a-proposed")


# ---------------------------------------------------------------------------
# builders
# ---------------------------------------------------------------------------


def _fact(
    kind: str, tokens: str, line: int, *, material: bool = True, uncertain: bool = False
) -> dict[str, Any]:
    return {
        "kind": kind,
        "tokens": tokens.split(),
        "line": line,
        "material": material,
        "expect_uncertain": uncertain,
    }


def _script(
    *lines: tuple[str, str],
    facts: Sequence[dict[str, Any]] = (),
    expected_warnings: Sequence[str] = (),
    axes: Sequence[str] = ("negation",),
) -> EncounterScript:
    """``lines`` are ``(role, text)`` in spoken order."""
    return EncounterScript.model_validate(
        {
            "schema_version": 1,
            "encounter_id": "syn-test",
            "appointment_type": "follow_up",
            "axes": list(axes),
            "lines": [{"role": role, "text": text} for role, text in lines],
            "facts": list(facts),
            "expected_warnings": list(expected_warnings),
        }
    )


def _words(text: str) -> tuple[TranscriptWord, ...]:
    """One word per space; a ``?`` prefix marks a low-probability word."""
    words = []
    for index, raw in enumerate(text.split()):
        low = raw.startswith("?")
        words.append(
            TranscriptWord(
                word_text=raw.removeprefix("?"),
                start_seconds=index * 0.3,
                end_seconds=index * 0.3 + 0.25,
                probability=0.3 if low else 0.9,
                uncertain=low,
            )
        )
    return tuple(words)


def _doc(*segments: tuple[str, str]) -> TranscriptDocument:
    """``segments`` are ``(speaker, text)``."""
    return TranscriptDocument(
        session_id=SESSION_ID,
        created_at=_NOW,
        model_name="mock",
        sample_rate=16_000,
        transcript_segments=tuple(
            TranscriptSegment(
                start_seconds=float(index * 10),
                end_seconds=float(index * 10 + 5),
                speaker=speaker,
                transcript_words=_words(text),
            )
            for index, (speaker, text) in enumerate(segments)
        ),
    )


Span = int | tuple[int, int, int]


def _assertions(document: TranscriptDocument, spans: Sequence[Span]) -> list[NoteAssertion]:
    out = []
    for number, span in enumerate(spans):
        if isinstance(span, int):
            last = len(document.transcript_segments[span].transcript_words) - 1
            span = (span, 0, last)
        segment, first, last = span
        words = document.transcript_segments[segment].transcript_words[first : last + 1]
        out.append(
            NoteAssertion(
                assertion_id=f"a{number}",
                section_key="presenting_complaint",
                note_span=NoteSpan(
                    span_text=reconstruct_span_text(words),
                    provenance="transcript",
                    source_coords=SourceCoords(segment, first, last),
                ),
            )
        )
    return out


def _note(
    document: TranscriptDocument,
    *spans: Span,
    warnings: Sequence[NoteWarning] = (),
    authored: Sequence[NoteAssertion] = (),
    clinician: str = SPEAKER_1,
) -> GeneratedNote:
    assertions = (*_assertions(document, spans), *authored)
    return GeneratedNote(
        session_id=SESSION_ID,
        created_at=_NOW,
        template_profile_id="clinic-a",
        provider_name="test",
        clinician_speaker=clinician,
        transcript_digest=DIGEST,
        config_digest=DIGEST,
        note_sections=(
            (GeneratedSection(section_key="presenting_complaint", note_assertions=assertions),)
            if assertions
            else ()
        ),
        note_warnings=tuple(warnings),
    )


def _checked(document: TranscriptDocument, *spans: Span) -> GeneratedNote:
    """The note with the REAL checker's Check 1 and Check 4 warnings — the
    two whose coordinates the metrics read."""
    bare = _note(document, *spans)
    warnings = (*reconstruction_warnings(bare, document), *omission_warnings(bare, document))
    return _note(document, *spans, warnings=warnings)


def _measured(metrics: EncounterMetrics) -> EncounterOutcome:
    return EncounterOutcome(
        "syn-test", "measured", segment_count=1, words=metrics.words, metrics=metrics
    )


def _only_fact(metrics: EncounterMetrics) -> FactOutcome:
    (fact,) = metrics.facts
    return fact


# ---------------------------------------------------------------------------
# structured-claim words: note_check's own classes
# ---------------------------------------------------------------------------


class TestStructuredClaimWords:
    @pytest.mark.parametrize(
        "token",
        ["left", "right", "500", "five", "twenty-one", "500mg", "mg", "ml", "no", "not",
         "never", "denies", "nil", "doesn't", "without"],
    )
    def test_sides_numbers_doses_units_and_negations_are_structured(self, token: str) -> None:
        assert is_structured_claim_word(token)

    @pytest.mark.parametrize("token", ["knee", "pain", "paracetamol", "lower", "today", "sore"])
    def test_other_words_are_not(self, token: str) -> None:
        assert not is_structured_claim_word(token)

    @pytest.mark.parametrize(
        "token",
        ["left", "right", "500", "five", "twenty-one", "500mg", "mg", "ml", "no", "not",
         "never", "denies", "nil", "doesn't", "without", "Left,", "500mg.", "No", "Doesn’t"],
    )
    @pytest.mark.parametrize("clinician", [True, False])
    @pytest.mark.parametrize("first_in_segment", [True, False])
    def test_check_4s_predicate_is_a_superset_on_every_segment(
        self, token: str, clinician: bool, first_in_segment: bool
    ) -> None:
        """C4 (note-routing-omissions plan): every structured-claim word is
        flagged by Check 4 for ANY speaker, so the harness's ``warned`` (the
        metric amendment of 2026-10-09) can never credit less than the
        structured classes the rule's facts are written in."""
        assert is_structured_claim_word(normalise_token(token))
        assert _omission_flag_token(token, first_in_segment=first_in_segment, clinician=clinician)

    def test_every_member_of_every_class_is_flagged_for_any_speaker(self) -> None:
        """C4 by ENUMERATION, not by sample: every member of the closed
        vocabularies behind ``is_structured_claim_word`` (and the medication
        lexicon, the run-1 class Check 4 keeps for every speaker) is flagged
        on a patient's line and on a clinician's, at a segment's start or
        not. Numbers outside the word list are digit-bearing (pinned above)."""
        structured = (
            *_LATERALITY_TOKENS,
            *_STRENGTH_UNITS,
            *_POLARITY_TOKENS,
            *_NUMBER_WORDS,
        )
        for token in structured:
            assert is_structured_claim_word(token), token
        for token in (*structured, *_MEDICATION_LEXICON):
            for clinician in (True, False):
                for first_in_segment in (True, False):
                    assert _omission_flag_token(
                        token, first_in_segment=first_in_segment, clinician=clinician
                    ), token


# ---------------------------------------------------------------------------
# word error rate
# ---------------------------------------------------------------------------


class TestWordErrors:
    def test_exact_transcript_has_no_errors(self) -> None:
        script = _script(("clinician", "My left knee hurts."))
        assert word_errors(_doc((SPEAKER_1, "my left knee hurts")), script) == WordErrors(4, 4, 0)

    def test_punctuation_case_and_fillers_are_normalised_away(self) -> None:
        script = _script(("clinician", "My left knee, um, hurts!"))
        errors = word_errors(_doc((SPEAKER_1, "My LEFT knee hurts.")), script)
        assert errors == WordErrors(4, 4, 0)

    def test_one_substitution_in_four(self) -> None:
        script = _script(("clinician", "my left knee hurts"))
        errors = word_errors(_doc((SPEAKER_1, "my right knee hurts")), script)
        assert errors == WordErrors(4, 4, 1)
        assert errors.rate == pytest.approx(0.25)

    def test_the_script_is_the_reference_and_the_transcript_the_hypothesis(self) -> None:
        """Development-recordings review round 31: unequal lengths pin the
        argument order (the reference count is the script's)."""
        script = _script(("clinician", "my left knee hurts"))
        assert word_errors(_doc((SPEAKER_1, "my knee hurts")), script) == WordErrors(4, 3, 1)


# ---------------------------------------------------------------------------
# the Done-when cases
# ---------------------------------------------------------------------------


class TestEmptyInputs:
    def test_empty_transcript(self) -> None:
        """ref [my, left, knee, hurts], hyp [] -> four deletions; the fact's
        tokens have no aligned word: omitted, not transcribed, not warned."""
        script = _script(
            ("clinician", "my left knee hurts"), facts=[_fact("laterality", "left knee", 0)]
        )
        document = _doc()
        metrics = encounter_metrics(document, _note(document), script)
        assert metrics.words == WordErrors(4, 0, 4)
        assert metrics.words.rate == 1.0
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.not_transcribed, fact.warned) == ("omitted", True, False)
        assert fact.silent_omission
        assert metrics.unsupported_clinical_lines == 0
        assert metrics.transcript_lines == 0 and metrics.config_lines == 0
        assert rule_failures(OPTION_A, _measured(metrics)) == ("silent_omission",)

    def test_empty_note(self) -> None:
        """A perfect transcript and a note with no line: the fact is
        transcribed but carried by nothing, so it is omitted (not 'not
        transcribed'). Since the metric amendment of 2026-10-09 (note-routing-
        omissions plan D3) Check 4 flags the uncovered side "left", so the
        omission is WARNED; under run 1's predicate (numbers, names,
        medications) it stays silent — the comparison column says so."""
        script = _script(
            ("clinician", "my left knee hurts"), facts=[_fact("laterality", "left knee", 0)]
        )
        document = _doc((SPEAKER_1, "my left knee hurts"))
        metrics = encounter_metrics(document, _checked(document), script)
        assert metrics.words == WordErrors(4, 4, 0)
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.not_transcribed, fact.warned) == ("omitted", False, True)
        assert (metrics.silent_omissions, metrics.silent_omissions_v1) == (0, 1)
        assert metrics.checker_tally == (("high_risk_omission", 1),)


class TestNegationFlip:
    def test_a_deleted_negation_makes_the_fact_wrong(self) -> None:
        """ref [there, is, no, swelling], hyp [there, is, swelling]: one
        deletion ("no"). The fact's "swelling" is matched and carried while
        its "no" is gone: the note says the opposite -> ``wrong``. No word
        of the line is substituted or inserted, so the LINE is supported."""
        script = _script(
            ("clinician", "there is no swelling"), facts=[_fact("negation", "no swelling", 0)]
        )
        document = _doc((SPEAKER_1, "there is swelling"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert metrics.words.edit_distance == 1
        assert _only_fact(metrics).verdict == "wrong"
        assert metrics.material_wrong == 1
        assert metrics.unsupported_clinical_lines == 0
        assert rule_failures(OPTION_A, _measured(metrics)) == ("material_wrong",)

    def test_an_inserted_negation_is_an_unsupported_clinical_line(self) -> None:
        """ref [there, is, swelling], hyp [there, is, no, swelling]: the one
        optimal alignment inserts "no", a negation inside a note line ->
        one unsupported clinical line; the fact itself matched -> correct."""
        script = _script(
            ("clinician", "there is swelling"), facts=[_fact("present", "swelling", 0)]
        )
        document = _doc((SPEAKER_1, "there is no swelling"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert metrics.unsupported_clinical_lines == 1
        assert metrics.other_unsupported_words == 0
        assert _only_fact(metrics).verdict == "correct"
        assert rule_failures(OPTION_A, _measured(metrics)) == ("unsupported_clinical_line",)

    def test_the_same_insertion_outside_every_note_line_is_not_a_line(self) -> None:
        script = _script(
            ("clinician", "there is swelling"), facts=[_fact("present", "swelling", 0)]
        )
        document = _doc((SPEAKER_1, "there is no swelling"))
        metrics = encounter_metrics(document, _checked(document), script)
        assert metrics.unsupported_clinical_lines == 0
        assert _only_fact(metrics).verdict == "omitted"


class TestLeftRightSwap:
    def test_the_swap_fails_the_fact_and_the_line(self) -> None:
        """ref [my, left, knee, hurts], hyp [my, right, knee, hurts]: one
        substitution left->right, inside the note line -> the fact is wrong
        and the line holds a substituted side."""
        script = _script(
            ("clinician", "my left knee hurts"), facts=[_fact("laterality", "left knee", 0)]
        )
        document = _doc((SPEAKER_1, "my right knee hurts"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert metrics.words == WordErrors(4, 4, 1)
        assert _only_fact(metrics).verdict == "wrong"
        assert metrics.unsupported_clinical_lines == 1
        assert rule_failures(OPTION_A, _measured(metrics)) == (
            "unsupported_clinical_line",
            "material_wrong",
        )


class TestDoseChange:
    def test_a_changed_dose_number(self) -> None:
        """ref [paracetamol, 500, mg, twice, a, day], hyp with 50 for 500:
        one substitution of a number inside the note line."""
        script = _script(
            ("clinician", "paracetamol 500 mg twice a day"),
            facts=[_fact("dose", "paracetamol 500 mg", 0)],
        )
        document = _doc((SPEAKER_1, "paracetamol 50 mg twice a day"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert metrics.words.edit_distance == 1
        assert _only_fact(metrics).verdict == "wrong"
        assert metrics.unsupported_clinical_lines == 1

    def test_the_same_dose_is_correct(self) -> None:
        script = _script(
            ("clinician", "paracetamol 500 mg twice a day"),
            facts=[_fact("dose", "paracetamol 500 mg", 0)],
        )
        document = _doc((SPEAKER_1, "paracetamol 500 mg twice a day"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert _only_fact(metrics).verdict == "correct"
        assert rule_failures(OPTION_A, _measured(metrics)) == ()


def _all_suspect(document: TranscriptDocument) -> TranscriptDocument:
    """``document`` with every word marked ``suspect`` (invented-text guard)."""
    return document.model_copy(
        update={
            "transcript_segments": tuple(
                segment.model_copy(
                    update={
                        "transcript_words": tuple(
                            word.model_copy(update={"suspect": True})
                            for word in segment.transcript_words
                        )
                    }
                )
                for segment in document.transcript_segments
            )
        }
    )


class TestSuspectWordsAreNeverWarned:
    """Invented-text guard D6 (Task 2.4): Check 4 never flags a suspect word,
    and BOTH harness word-level predicates (``warned`` and run 1's
    ``warned_v1``) mirror it — so a suspect line left out counts as a silent
    omission under both, never a warned one."""

    _LINE = "paracetamol 500 mg for the left knee"

    def _script(self) -> EncounterScript:
        return _script(
            ("clinician", self._LINE),
            facts=[_fact("dose", "paracetamol 500 mg", 0), _fact("laterality", "left knee", 0)],
        )

    def test_a_plain_line_left_out_is_warned_under_both_predicates(self) -> None:
        document = _doc((SPEAKER_1, self._LINE))
        metrics = encounter_metrics(document, _checked(document), self._script())
        assert [w.note_warning_code for w in _checked(document).note_warnings] == [
            "high_risk_omission"
        ]
        assert [(f.verdict, f.warned) for f in metrics.facts] == [
            ("omitted", True),
            ("omitted", True),
        ]
        # Run 1's predicate warns the dose (a number, a medication), not the side.
        assert (metrics.silent_omissions, metrics.silent_omissions_v1) == (0, 1)

    def test_the_same_line_suspect_draws_no_omission_and_is_silent_under_both(self) -> None:
        document = _all_suspect(_doc((SPEAKER_1, self._LINE)))
        assert omission_warnings(_note(document), document) == ()
        metrics = encounter_metrics(document, _checked(document), self._script())
        assert [(f.verdict, f.warned) for f in metrics.facts] == [
            ("omitted", False),
            ("omitted", False),
        ]
        assert (metrics.silent_omissions, metrics.silent_omissions_v1) == (2, 2)

    def test_both_predicates_ignore_a_suspect_word_even_under_a_warning(self) -> None:
        """The harness re-derives ``warned`` per word: a hand-made omission
        warning on the segment still credits no suspect word."""
        document = _all_suspect(_doc((SPEAKER_1, self._LINE)))
        warning = NoteWarning(
            note_warning_code="high_risk_omission",
            severity="review",
            source_coords=SourceCoords(0, 0, 6),
        )
        metrics = encounter_metrics(document, _note(document, warnings=(warning,)), self._script())
        assert [f.warned for f in metrics.facts] == [False, False]
        assert (metrics.silent_omissions, metrics.silent_omissions_v1) == (2, 2)


# ---------------------------------------------------------------------------
# metric amendment 2026-10-11: canonical spelling (note-routing-omissions D10)
# ---------------------------------------------------------------------------


def _canonical(text: str) -> tuple[str, ...]:
    """One script line's canonical tokens (the reference side)."""
    return validation._reference(_script(("clinician", text))).tokens


class TestCanonicalTokens:
    """The canonicaliser by itself: what it rewrites, and the named residue
    it leaves as it is."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("500mg", ("500", "mg")),
            ("2.50mg", ("2.50", "mg")),  # the RAW digits, never format(float)
            ("20min", ("20min",)),  # a suffix outside the unit table
            ("milligrams grams mcg millilitres", ("mg", "g", "mcg", "ml")),
            ("two out of ten", ("2", "out", "of", "10")),
            ("twenty-one twenty one", ("21", "21")),
            ("five hundred", ("500",)),
            ("two thousand", ("2000",)),
            ("fifteen hundred", ("1500",)),
            # The named residue: left as they are, or joined only in part.
            ("a hundred", ("a", "hundred")),
            ("hundred", ("hundred",)),
            ("two hundred and fifty", ("200", "and", "50")),
            ("five hundred twenty", ("500", "20")),
            ("twenty five hundred", ("25", "hundred")),
            ("the second one is half", ("the", "second", "1", "is", "half")),
            ("one-third", ("one-third",)),
            ("two point five", ("2", "point", "5")),
            ("twenty twenty-five", ("20", "25")),
            ("three units", ("3", "units")),
            # A join never crosses punctuation: on the word, as a word of
            # its own, on a dropped filler, or opening the next word.
            ("twenty, one", ("20", "1")),
            ("twenty , one", ("20", "1")),
            ("twenty um, one", ("20", "1")),
            ("twenty (one)", ("20", "1")),
            ("five, hundred", ("5", "hundred")),
        ],
    )
    def test_one_line(self, text: str, expected: tuple[str, ...]) -> None:
        assert _canonical(text) == expected

    def test_a_join_never_crosses_a_line_or_a_segment(self) -> None:
        script = _script(("clinician", "take five"), ("clinician", "hundred mg"))
        assert validation._reference(script).tokens == ("take", "5", "hundred", "mg")
        document = _doc((SPEAKER_1, "take five"), (SPEAKER_1, "hundred mg"))
        assert validation._canonical_hypothesis(document).tokens == ("take", "5", "hundred", "mg")

    def test_the_maps_a_split_and_a_join_return(self) -> None:
        canonical = validation.canonical_tokens(
            [("take", False), ("500mg", False), ("or", False), ("five", False), ("hundred", True)]
        )
        assert canonical.tokens == ("take", "500", "mg", "or", "500")
        # A split repeats its one content token; a join holds both of its.
        assert canonical.consumed == ((0,), (1,), (1,), (2,), (3, 4))
        assert canonical.content_map == ((0, 0), (1, 2), (3, 3), (4, 4), (4, 4))
        assert canonical.rewritten == 3

    def test_the_transcript_keeps_its_word_positions(self) -> None:
        document = _doc((SPEAKER_1, "take 500mg or five hundred"))
        canonical = validation._canonical_hypothesis(document)
        assert canonical.consumed == (
            ((0, 0),), ((0, 1),), ((0, 1),), ((0, 2),), ((0, 3), (0, 4))
        )

    def test_the_content_token_index_space_is_kept(self) -> None:
        """PR-MED-023 / PR-MED-026: with nothing to rewrite, the canonical
        tokens ARE the content tokens — fillers and punctuation-only words
        dropped exactly as ``content_tokens`` drops them — at the (segment,
        word) positions ``_hypothesis`` reports, and a script line's are its
        ``content_tokens``."""
        text = "Um, my LEFT knee - it , hurts."
        document = _doc((SPEAKER_1, text), (SPEAKER_2, "uh okay then"))
        tokens, positions = validation._hypothesis(document)
        canonical = validation._canonical_hypothesis(document)
        assert canonical.tokens == tuple(tokens)
        assert canonical.consumed == tuple((position,) for position in positions)
        assert canonical.rewritten == 0
        assert _canonical(text) == content_tokens(text)


class TestSpellingAmendment:
    """Metric amendment 2026-10-11 (decision (a), note-routing-omissions plan
    D10): the script and the transcript are compared after canonical
    spelling. Pinned BOTH ways through ``encounter_metrics``: a spelling
    difference is no longer an error, a different value still is
    (``TestDoseChange`` above is unchanged)."""

    @pytest.mark.parametrize(
        ("said", "written", "fact"),
        [
            ("pain is two out of ten", "pain is 2 out of 10", "2 out of 10"),
            ("pain is 2 out of 10", "pain is two out of ten", "two out of ten"),
            ("paracetamol 500mg daily", "paracetamol 500 milligrams daily", "500 milligrams"),
            ("paracetamol 75 mg daily", "paracetamol 75 milligrams daily", "75 milligrams"),
            (
                "paracetamol five hundred milligrams daily",
                "paracetamol 500 milligrams daily",
                "500 milligrams",
            ),
            ("for twenty-one days", "for 21 days", "21 days"),
            ("for twenty one days", "for 21 days", "21 days"),
        ],
    )
    def test_a_spelling_difference_is_correct(self, said: str, written: str, fact: str) -> None:
        script = _script(("clinician", written), facts=[_fact("dose", fact, 0)])
        document = _doc((SPEAKER_1, said))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert metrics.words.edit_distance == 0
        assert _only_fact(metrics).verdict == "correct"
        assert metrics.unsupported_clinical_lines == 0
        assert rule_failures(OPTION_A, _measured(metrics)) == ()

    @pytest.mark.parametrize(
        ("said", "written", "fact"),
        [
            ("take 2 tablets", "take 3 tablets", "3 tablets"),
            ("take two tablets", "take 3 tablets", "3 tablets"),
            ("paracetamol 50mg daily", "paracetamol 500 mg daily", "500 mg"),
            ("paracetamol fifty milligrams daily", "paracetamol 500 mg daily", "500 mg"),
        ],
    )
    def test_a_different_value_stays_wrong_and_unsupported(
        self, said: str, written: str, fact: str
    ) -> None:
        script = _script(("clinician", written), facts=[_fact("dose", fact, 0)])
        document = _doc((SPEAKER_1, said))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert metrics.words.edit_distance == 1
        assert _only_fact(metrics).verdict == "wrong"
        assert metrics.unsupported_clinical_lines == 1
        assert rule_failures(OPTION_A, _measured(metrics)) == (
            "unsupported_clinical_line",
            "material_wrong",
        )

    def test_a_comma_between_two_number_words_never_joins_in_the_transcript(self) -> None:
        """hyp [for, 20, 1, days] against ref [for, 21, days]: one
        substitution and one insertion, so the fact is wrong."""
        for said in ("for twenty, one days", "for twenty , one days"):
            script = _script(("clinician", "for 21 days"), facts=[_fact("present", "21 days", 0)])
            document = _doc((SPEAKER_1, said))
            metrics = encounter_metrics(document, _checked(document, 0), script)
            assert metrics.words == WordErrors(3, 4, 2), said
            assert _only_fact(metrics).verdict == "wrong", said

    def test_a_comma_between_two_number_words_never_joins_in_the_script(self) -> None:
        """ref [for, 20, 1, days] against hyp [for, 21, days]: one
        substitution and one deletion."""
        for written in ("for twenty, one days", "for twenty , one days"):
            script = _script(("clinician", written), facts=[_fact("present", "one days", 0)])
            document = _doc((SPEAKER_1, "for 21 days"))
            metrics = encounter_metrics(document, _checked(document, 0), script)
            assert metrics.words == WordErrors(4, 3, 2), written
            assert _only_fact(metrics).verdict == "wrong", written

    def test_ordinals_and_half_are_untouched(self) -> None:
        script = _script(
            ("clinician", "take half a tablet on the second day"),
            facts=[_fact("dose", "half a tablet", 0)],
        )
        document = _doc((SPEAKER_1, "take half a tablet on the second day"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert metrics.spelling_normalised_words == 0
        assert _only_fact(metrics).verdict == "correct"
        assert _canonical("take half a tablet on the second day") == content_tokens(
            "take half a tablet on the second day"
        )

    @pytest.mark.parametrize("fact", ["five", "hundred mg", "five hundred mg"])
    def test_a_fact_whose_span_cuts_a_join_still_resolves(self, fact: str) -> None:
        """The fact is found on the line's content tokens, then widened to
        the whole joined token its span cuts — never an empty lookup."""
        script = _script(
            ("clinician", "take five hundred mg daily"), facts=[_fact("dose", fact, 0)]
        )
        document = _doc((SPEAKER_1, "take 500 mg daily"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert _only_fact(metrics).verdict == "correct"

    @pytest.mark.parametrize(
        "line",
        [
            "i take um five hundred mg daily and the left knee hurts",
            "i take - five hundred mg daily - and the left knee hurts",
        ],
    )
    def test_a_fact_after_a_dropped_word_and_a_join_finds_its_own_span(self, line: str) -> None:
        """PR-MED-023: a removed filler or a punctuation-only word AND a join
        stand before the fact, so its content index, its raw word index and
        its canonical index all differ. Only the canonical span tells the
        right side from the wrong one."""
        script = _script(("clinician", line), facts=[_fact("laterality", "left knee", 0)])
        for said, verdict in (
            ("i take 500 mg daily and the left knee hurts", "correct"),
            ("i take 500 mg daily and the right knee hurts", "wrong"),
        ):
            document = _doc((SPEAKER_1, said))
            fact = _only_fact(encounter_metrics(document, _checked(document, 0), script))
            assert fact.verdict == verdict, said

    @pytest.mark.parametrize(
        ("span", "present", "absent"),
        [
            ((0, 0, 0), "omitted", "correctly_absent"),  # neither word of "five hundred"
            ((0, 0, 1), "wrong", "wrongly_present"),  # "five" only
            ((0, 2, 4), "wrong", "wrongly_present"),  # "hundred" only
            ((0, 0, 4), "correct", "wrongly_present"),  # both
        ],
    )
    def test_a_note_line_holding_part_of_a_joined_number(
        self, span: tuple[int, int, int], present: str, absent: str
    ) -> None:
        """PR-MED-020: the joined "500" (transcript words 1 and 2) is in a
        note line wholly, in part or not at all — never read as all-or-
        nothing by one flag, for a present fact and an absent one."""
        document = _doc((SPEAKER_1, "take five hundred mg daily"))
        for kind, expected in (("dose", present), ("absent", absent)):
            script = _script(("clinician", "take 500 mg daily"), facts=[_fact(kind, "500", 0)])
            fact = _only_fact(encounter_metrics(document, _note(document, span), script))
            assert fact.verdict == expected, kind

    def test_a_low_confidence_second_word_of_a_joined_number_surfaces(self) -> None:
        script = _script(
            ("clinician", "take 500 mg daily"),
            facts=[_fact("dose", "500 mg", 0, uncertain=True)],
        )
        document = _doc((SPEAKER_1, "take five ?hundred mg daily"))
        note = _checked(document, 0)
        # Invented-text guard D5: the quoted line also draws ONE per-line
        # `number_source`, which never counts as surfacing (below).
        assert [(w.note_warning_code, w.source_coords) for w in note.note_warnings] == [
            ("low_confidence_source", SourceCoords(0, 2, 2)),
            ("number_source", SourceCoords(0, 0, 4)),
        ]
        fact = _only_fact(encounter_metrics(document, note, script))
        assert (fact.verdict, fact.uncertainty_surfaced) == ("correct", True)

    def test_the_spelling_count_is_the_transcripts_rewritten_words(self) -> None:
        """Counted per transcript word rewritten: "500mg" 1, "five hundred" 2,
        "milligrams" 1, "500 mg" 0, "500" 0 — the script's own rewrites (its
        two "milligrams") are not counted."""
        script = _script(
            ("clinician", "take 500 milligrams then 500 milligrams then 500 mg then 500")
        )
        document = _doc((SPEAKER_1, "take 500mg then five hundred milligrams then 500 mg then 500"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert metrics.words.edit_distance == 0
        assert metrics.spelling_normalised_words == 4


class TestAbsentFact:
    def _script(self) -> EncounterScript:
        return _script(
            ("clinician", "my left knee hurts"),
            ("patient", "my dog likes the beach"),
            facts=[_fact("laterality", "left knee", 0), _fact("absent", "dog likes the beach", 1)],
        )

    def test_kept_out_of_the_note_is_correctly_absent(self) -> None:
        document = _doc((SPEAKER_1, "my left knee hurts"), (SPEAKER_2, "my dog likes the beach"))
        metrics = encounter_metrics(document, _checked(document, 0), self._script())
        assert [f.verdict for f in metrics.facts] == ["correct", "correctly_absent"]
        assert rule_failures(OPTION_A, _measured(metrics)) == ()

    def test_carried_into_the_note_is_wrongly_present(self) -> None:
        document = _doc((SPEAKER_1, "my left knee hurts"), (SPEAKER_2, "my dog likes the beach"))
        metrics = encounter_metrics(document, _checked(document, 0, 1), self._script())
        assert [f.verdict for f in metrics.facts] == ["correct", "wrongly_present"]
        assert metrics.material_wrong == 1
        assert rule_failures(OPTION_A, _measured(metrics)) == ("material_wrong",)

    def test_not_transcribed_is_still_correctly_absent(self) -> None:
        document = _doc((SPEAKER_1, "my left knee hurts"))
        metrics = encounter_metrics(document, _checked(document, 0), self._script())
        absent = metrics.facts[1]
        assert (absent.verdict, absent.not_transcribed) == ("correctly_absent", True)


class TestFactStatedTwice:
    def _script(self) -> EncounterScript:
        # The fact names line 1, the clinician's restatement.
        return _script(
            ("patient", "my left knee hurts"),
            ("clinician", "so the left knee hurts"),
            facts=[_fact("laterality", "left knee", 1)],
        )

    def _document(self) -> TranscriptDocument:
        return _doc((SPEAKER_2, "my left knee hurts"), (SPEAKER_1, "so the left knee hurts"))

    def test_judged_on_its_own_line(self) -> None:
        document = self._document()
        metrics = encounter_metrics(document, _checked(document, 1), self._script())
        assert _only_fact(metrics).verdict == "correct"

    def test_the_other_statement_carried_does_not_count(self) -> None:
        """Only segment 0 (the line-0 statement) is in the note: the fact's
        own line is not carried, so it is omitted."""
        document = self._document()
        metrics = encounter_metrics(document, _checked(document, 0), self._script())
        assert _only_fact(metrics).verdict == "omitted"

    def test_twice_inside_its_line_takes_the_worse_occurrence(self) -> None:
        """ref [the, left, knee, and, the, left, knee, again], hyp with the
        second "left" as "right": occurrence one is correct, occurrence two
        is wrong -> the fact reports ``wrong`` and ``ambiguous``."""
        script = _script(
            ("clinician", "the left knee and the left knee again"),
            facts=[_fact("laterality", "left knee", 0)],
        )
        document = _doc((SPEAKER_1, "the left knee and the right knee again"))
        fact = _only_fact(encounter_metrics(document, _checked(document, 0), script))
        assert (fact.verdict, fact.ambiguous) == ("wrong", True)


class TestUnsupportedNonClinicalWord:
    def test_counted_not_failing(self) -> None:
        """ref [the, pain, is, in, my, lower, back], hyp with "lowest" for
        "lower": a substituted word that is not a side, number, dose or
        negation -> counted in ``other_unsupported_words`` only."""
        script = _script(
            ("clinician", "the pain is in my lower back"), facts=[_fact("present", "pain", 0)]
        )
        document = _doc((SPEAKER_1, "the pain is in my lowest back"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert metrics.unsupported_clinical_lines == 0
        assert metrics.other_unsupported_words == 1
        assert _only_fact(metrics).verdict == "correct"
        assert rule_failures(OPTION_A, _measured(metrics)) == ()


class TestSegmentBoundaries:
    def test_one_reference_line_split_across_two_segments(self) -> None:
        """One line, two segments: the alignment is word-level, so each fact
        maps to its exact (segment, word) wherever the boundary falls."""
        script = _script(
            ("clinician", "my left knee has been sore for two weeks"),
            facts=[
                _fact("laterality", "left knee", 0),
                _fact("present", "two weeks", 0),
                _fact("present", "been sore", 0),
            ],
        )
        document = _doc((SPEAKER_1, "my left knee has been"), (SPEAKER_1, "sore for two weeks"))
        metrics = encounter_metrics(document, _checked(document, 0, 1), script)
        assert metrics.words == WordErrors(9, 9, 0)
        assert [f.verdict for f in metrics.facts] == ["correct", "correct", "correct"]
        assert metrics.unsupported_clinical_lines == 0

    def test_a_fact_carried_only_in_part_is_wrong(self) -> None:
        """Only segment 1 is in the note: "sore" is carried, "been" is not —
        the note holds part of the fact, which is not the fact."""
        script = _script(
            ("clinician", "my left knee has been sore for two weeks"),
            facts=[_fact("present", "been sore", 0)],
        )
        document = _doc((SPEAKER_1, "my left knee has been"), (SPEAKER_1, "sore for two weeks"))
        metrics = encounter_metrics(document, _checked(document, 1), script)
        assert _only_fact(metrics).verdict == "wrong"

    def test_two_reference_lines_merged_into_one_segment_and_one_note_line(self) -> None:
        """Two lines, one segment, one note line spanning both: judged word
        by word, so the merge itself makes nothing unsupported."""
        script = _script(
            ("patient", "my left knee hurts"),
            ("clinician", "since last week"),
            facts=[_fact("laterality", "left knee", 0), _fact("present", "last week", 1)],
        )
        document = _doc((SPEAKER_1, "my left knee hurts since last week"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert metrics.transcript_lines == 1
        assert metrics.words == WordErrors(7, 7, 0)
        assert [f.verdict for f in metrics.facts] == ["correct", "correct"]
        assert metrics.unsupported_clinical_lines == 0 and metrics.other_unsupported_words == 0


class TestOmissionWarnings:
    def test_an_unrelated_warning_in_the_same_segment_leaves_the_omission_silent(self) -> None:
        """Segment 0 (the PATIENT's, SPEAKER_2) = [rest, the, knee, and, take,
        2, tablets]; nothing is in the note. The real Check 4 warns on the
        uncovered "2" (word 5). The material fact [rest, the, knee] holds no
        high-risk word of its own, so the warning does not count for it: a
        silent omission. The fact [2, tablets] owns the warned word: a warned
        omission. (Since validation-run6 D13 the same line spoken by the
        confirmed clinician credits both facts — ``TestFlaggedLineCredit``;
        a patient's line keeps this rule.)"""
        script = _script(
            ("clinician", "how is it"),
            ("patient", "rest the knee and take 2 tablets"),
            facts=[_fact("present", "rest the knee", 1), _fact("dose", "2 tablets", 1)],
        )
        document = _doc((SPEAKER_1, "how is it"), (SPEAKER_2, "rest the knee and take 2 tablets"))
        note = _checked(document)
        assert [(w.note_warning_code, w.source_coords) for w in note.note_warnings] == [
            ("high_risk_omission", SourceCoords(1, 5, 5))
        ]
        metrics = encounter_metrics(document, note, script)
        rest, dose = metrics.facts
        assert (rest.verdict, rest.warned, rest.silent_omission) == ("omitted", False, True)
        assert (dose.verdict, dose.warned, dose.silent_omission) == ("omitted", True, False)
        assert (metrics.silent_omissions, metrics.warned_omissions) == (1, 1)

    def test_between_two_high_risk_words_is_still_silent_and_fails_option_a(self) -> None:
        """Segment 0 = [use, 2, cold, packs, over, the, sore, calf, 3, times],
        its first word quoted in the note: Check 4's ONE warning spans words
        1..8 (the two numbers). The fact [sore, calf] lies inside that
        interval but holds no high-risk word — an interval proves nothing
        (peer round 4): silent, and option (a) fails the encounter. (The line
        is partly in the note, so validation-run6 D13's whole-line credit
        does not reach it.)"""
        script = _script(
            ("clinician", "use 2 cold packs over the sore calf 3 times"),
            facts=[_fact("present", "sore calf", 0)],
        )
        document = _doc((SPEAKER_1, "use 2 cold packs over the sore calf 3 times"))
        note = _checked(document, (0, 0, 0))
        assert [w.source_coords for w in note.note_warnings] == [SourceCoords(0, 1, 8)]
        metrics = encounter_metrics(document, note, script)
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.warned, fact.silent_omission) == ("omitted", False, True)
        assert rule_failures(OPTION_A, _measured(metrics)) == ("silent_omission",)

    def test_a_warning_on_another_segment_never_counts(self) -> None:
        script = _script(
            ("clinician", "take 2 tablets"),
            ("clinician", "take 3 tablets"),
            facts=[_fact("dose", "2 tablets", 0)],
        )
        document = _doc((SPEAKER_1, "take 2 tablets"), (SPEAKER_1, "take 3 tablets"))
        note = _note(
            document,
            warnings=[
                NoteWarning(
                    note_warning_code="high_risk_omission",
                    severity="review",
                    source_coords=SourceCoords(1, 1, 1),
                )
            ],
        )
        fact = _only_fact(encounter_metrics(document, note, script))
        assert (fact.verdict, fact.warned) == ("omitted", False)


class _RouteNothing:
    """A provider that places nothing — the degenerate case the metric
    amendment must never pass (note-routing-omissions plan D3, PR-MED-004)."""

    @property
    def provider_name(self) -> str:
        return "route-nothing"

    def generate_sections(self, request: NoteRequest) -> tuple[GeneratedSection, ...]:
        return ()


class TestOmissionMetricAmendment:
    """Metric amendment 2026-10-09 (decision 0.2 (b)): ``warned`` reads Check
    4's widened predicate; ``silent (run-1 predicate)`` keeps run 1's."""

    def test_a_side_only_patient_fact_is_warned_and_silent_under_run_1(self) -> None:
        """Segment 1 (the patient, SPEAKER_2) = [my, left, knee, is, sore],
        nothing in the note. Check 4 now flags the patient's uncovered side
        "left" — the fact's own word — so it is a warned omission; run 1
        scoped Check 4 to the clinician, so there it is silent."""
        script = _script(
            ("clinician", "how is it today"),
            ("patient", "my left knee is sore"),
            facts=[_fact("laterality", "left knee", 1)],
        )
        document = _doc((SPEAKER_1, "how is it today"), (SPEAKER_2, "my left knee is sore"))
        note = _checked(document)
        assert [(w.note_warning_code, w.source_coords) for w in note.note_warnings] == [
            ("high_risk_omission", SourceCoords(1, 1, 1))
        ]
        metrics = encounter_metrics(document, note, script)
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.warned, fact.silent_omission) == ("omitted", True, False)
        assert fact.silent_omission_v1
        assert (metrics.silent_omissions, metrics.silent_omissions_v1) == (0, 1)
        # 0.3.3's predicate warned it too (the fact's own flagged word).
        assert metrics.silent_omissions_v033 == 0
        assert rule_failures(OPTION_A, _measured(metrics)) == ()

    def test_the_run_1_column_keeps_run_1s_clinician_only_scope(self) -> None:
        """Peer round 5 (PR-LOW-015): the patient fact's words are ones run
        1's predicate ACCEPTS (a medication and a number), so only the
        clinician-only scope keeps it silent in the run-1 column — run 1 never
        warned a patient segment. Segment 1 (the patient, SPEAKER_2) = [i,
        take, paracetamol, 3, times, a, day]; Check 4 flags words 2..3."""
        script = _script(
            ("clinician", "how often do you take it"),
            ("patient", "i take paracetamol 3 times a day"),
            facts=[_fact("dose", "paracetamol 3 times", 1)],
        )
        document = _doc(
            (SPEAKER_1, "how often do you take it"),
            (SPEAKER_2, "i take paracetamol 3 times a day"),
        )
        note = _checked(document)
        assert [(w.note_warning_code, w.source_coords) for w in note.note_warnings] == [
            ("high_risk_omission", SourceCoords(1, 2, 3))
        ]
        metrics = encounter_metrics(document, note, script)
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.warned, fact.silent_omission) == ("omitted", True, False)
        assert fact.silent_omission_v1
        assert (metrics.silent_omissions, metrics.silent_omissions_v1) == (0, 1)

    def test_a_provider_that_routes_nothing_still_fails_rule_v1(self, tmp_path: Path) -> None:
        """Through the real compose -> confirm -> finalise pipeline with a
        provider that places nothing. Since validation-run6 D13 the
        clinician's wholly uncovered line (it draws ``high_risk_omission`` on
        "2") credits every word on it, so [rest, the, knee] is warned —
        though still silent under the 0.3.3 predicate, which holds no token
        of it. The PATIENT's [worse, at, night] holds no token
        ``_omission_flag_token`` accepts for a patient (no side, number,
        dose, unit, negation, medication, nor a name-like token) and D13
        never reaches a patient line, so it stays SILENT and option (a)
        fails the encounter; the warned facts are never counted as placed.
        The run-1 and 0.3.3 columns can only count as many silent omissions
        or more. (Clinician-only speech routed nowhere would now be fully
        warned — the loosening D15 names (1).)"""
        script = _script(
            ("clinician", "rest the knee and take 2 tablets"),
            ("patient", "it is worse at night"),
            facts=[
                _fact("present", "rest the knee", 0),
                _fact("dose", "2 tablets", 0),
                _fact("present", "worse at night", 1),
            ],
        )
        document = _doc(
            (SPEAKER_2, "rest the knee and take 2 tablets"), (SPEAKER_1, "it is worse at night")
        )
        config = _pipeline_config(tmp_path)
        draft = compose_draft(document, config, _RouteNothing(), clinician_speaker=SPEAKER_2)
        note = finalise_note(draft, confirm_all(draft, _NOW), document, config, created_at=_NOW)
        assert note.note_sections == ()
        assert [
            (w.note_warning_code, w.source_coords)
            for w in note.note_warnings
            if w.note_warning_code in OMISSION_CODES
        ] == [("high_risk_omission", SourceCoords(0, 5, 5))]
        metrics = encounter_metrics(document, note, script)
        rest, dose, night = metrics.facts
        assert (rest.verdict, rest.warned, rest.silent_omission_v033) == ("omitted", True, True)
        assert (dose.verdict, dose.warned, dose.silent_omission_v033) == ("omitted", True, False)
        assert (night.verdict, night.warned, night.silent_omission) == ("omitted", False, True)
        assert (
            metrics.silent_omissions,
            metrics.silent_omissions_v033,
            metrics.silent_omissions_v1,
        ) == (1, 2, 2)
        assert metrics.silent_omissions_v1 >= metrics.silent_omissions
        assert metrics.silent_omissions_v033 >= metrics.silent_omissions
        assert rule_failures(OPTION_A, _measured(metrics)) == ("silent_omission",)


def _warning(code: str, segment: int, first: int, last: int) -> NoteWarning:
    """A hand-made review warning on ``(segment, first..last)``, no section
    and no assertion — a stub checker's mark."""
    return NoteWarning(
        note_warning_code=code,
        severity="review",
        source_coords=SourceCoords(segment, first, last),
    )


class TestFlaggedLineCredit:
    """Metric amendment 2026-10-24 (validation-run6 plan D13, amending D7):
    an omitted fact is ``warned`` when its aligned word lies on a segment
    that (1) an omission warning of either code anchors, (2) the confirmed
    clinician spoke, (3) no note line touches and (4) lies before Check 6's
    boundary — each condition pinned both ways here. 0.3.3's predicate is
    kept for the "Silent (0.3.3 predicate)" column; no rule reads it."""

    _LINE = "rest the knee tonight"

    def _script(self, *lines: tuple[str, str], line: int = 0) -> EncounterScript:
        return _script(*lines, facts=[_fact("present", "rest the knee", line)])

    @pytest.mark.parametrize("code", sorted(OMISSION_CODES))
    def test_a_wholly_uncovered_flagged_clinician_line_is_credited(self, code: str) -> None:
        """Segment 0 (the clinician, SPEAKER_1) = [rest, the, knee, tonight],
        nothing in the note, one warning of ``code`` on the segment. No word
        of the fact is a 0.3.3 flag word, so 0.3.3 and run 1 left it silent;
        D13 credits the whole line."""
        document = _doc((SPEAKER_1, self._LINE))
        note = _note(document, warnings=[_warning(code, 0, 0, 3)])
        metrics = encounter_metrics(document, note, self._script(("clinician", self._LINE)))
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.warned, fact.silent_omission) == ("omitted", True, False)
        assert (fact.silent_omission_v033, fact.silent_omission_v1) == (True, True)
        assert (
            metrics.silent_omissions,
            metrics.silent_omissions_v033,
            metrics.silent_omissions_v1,
        ) == (0, 1, 1)
        assert metrics.warned_omissions == 1
        assert rule_failures(OPTION_A, _measured(metrics)) == ()

    def test_the_real_check_4_code_on_an_uncovered_clinician_line_credits_it(
        self, tmp_path: Path
    ) -> None:
        """Through the real checker: ``clinician_line_omissions`` warns the
        clinician's uncovered line (it holds no high-risk word), and the
        harness credits it."""
        document = _doc((SPEAKER_1, self._LINE))
        bare = _note(document)
        warnings = clinician_line_omissions(bare, document, _pipeline_config(tmp_path))
        assert [(w.note_warning_code, w.source_coords) for w in warnings] == [
            ("clinician_line_omitted", SourceCoords(0, 0, 3))
        ]
        note = _note(document, warnings=warnings)
        fact = _only_fact(
            encounter_metrics(document, note, self._script(("clinician", self._LINE)))
        )
        assert (fact.warned, fact.silent_omission, fact.silent_omission_v033) == (
            True,
            False,
            True,
        )

    def test_a_warning_on_another_segment_credits_nothing(self) -> None:
        """Condition (1): the anchor is the fact's own segment."""
        document = _doc((SPEAKER_1, self._LINE), (SPEAKER_1, "see you soon"))
        note = _note(document, warnings=[_warning("clinician_line_omitted", 1, 0, 2)])
        script = self._script(("clinician", self._LINE), ("clinician", "see you soon"))
        fact = _only_fact(encounter_metrics(document, note, script))
        assert (fact.verdict, fact.warned, fact.silent_omission) == ("omitted", False, True)

    def test_a_line_with_no_omission_warning_credits_nothing(self) -> None:
        """Condition (1): an uncovered clinician line with no omission
        warning at all (a stub checker that raised none) — silent."""
        document = _doc((SPEAKER_1, self._LINE))
        fact = _only_fact(
            encounter_metrics(document, _note(document), self._script(("clinician", self._LINE)))
        )
        assert (fact.warned, fact.silent_omission) == (False, True)

    def test_a_patient_line_is_never_credited(self) -> None:
        """Condition (2): the same warning on the PATIENT's line credits
        nothing — the remedy D13 credits is the clinician's own line."""
        document = _doc((SPEAKER_1, "how is it"), (SPEAKER_2, self._LINE))
        note = _note(document, warnings=[_warning("clinician_line_omitted", 1, 0, 3)])
        script = self._script(("clinician", "how is it"), ("patient", self._LINE), line=1)
        fact = _only_fact(encounter_metrics(document, note, script))
        assert (fact.verdict, fact.warned, fact.silent_omission) == ("omitted", False, True)

    def test_no_confirmed_clinician_credits_nothing(self) -> None:
        """Condition (2): with no clinician confirmed, no line is the
        clinician's."""
        document = _doc((SPEAKER_1, self._LINE))
        note = _note(
            document, warnings=[_warning("clinician_line_omitted", 0, 0, 3)], clinician=None
        )
        fact = _only_fact(
            encounter_metrics(document, note, self._script(("clinician", self._LINE)))
        )
        assert (fact.warned, fact.silent_omission) == (False, True)

    def test_a_partly_covered_line_is_not_credited(self) -> None:
        """Condition (3): the note quotes "tonight" (word 3), so the line is
        not wholly uncovered; the hand-made ``high_risk_omission`` still
        anchors it, but no word of the fact is a flag word — silent."""
        document = _doc((SPEAKER_1, self._LINE))
        note = _note(document, (0, 3, 3), warnings=[_warning("high_risk_omission", 0, 0, 2)])
        fact = _only_fact(
            encounter_metrics(document, note, self._script(("clinician", self._LINE)))
        )
        assert (fact.verdict, fact.warned, fact.silent_omission) == ("omitted", False, True)

    @pytest.mark.parametrize(("boundary", "credited"), [(0, False), (1, True)])
    def test_only_a_line_before_the_next_patient_boundary_is_credited(
        self, boundary: int, credited: bool
    ) -> None:
        """Condition (4): Check 6's ``possible_next_patient`` warning on
        segment 0 puts the line past the boundary (the remedy, adding it,
        would put the next patient's words in this note); on segment 1 the
        line is before it."""
        document = _doc((SPEAKER_1, self._LINE), (SPEAKER_1, "good morning come on in"))
        note = _note(
            document,
            warnings=[
                _warning("clinician_line_omitted", 0, 0, 3),
                _warning("possible_next_patient", boundary, 0, 4 if boundary else 3),
            ],
        )
        script = self._script(("clinician", self._LINE), ("clinician", "good morning come on in"))
        fact = _only_fact(encounter_metrics(document, note, script))
        assert (fact.warned, fact.silent_omission) == (credited, not credited)

    def test_a_suspect_word_is_never_credited(self) -> None:
        """The invented-text guard's invariant (D6) holds for D13 too: the
        harness's ``warned`` never counts a suspect word."""
        document = _all_suspect(_doc((SPEAKER_1, self._LINE)))
        note = _note(document, warnings=[_warning("clinician_line_omitted", 0, 0, 3)])
        fact = _only_fact(
            encounter_metrics(document, note, self._script(("clinician", self._LINE)))
        )
        assert (fact.warned, fact.silent_omission) == (False, True)

    def test_a_wrong_verdict_with_a_0_3_3_silent_alternative(self) -> None:
        """ref [ice], hyp [heat, cold]: two optimal alignments of cost 2 — A
        (ice->heat, insert cold): "heat" is quoted, so the fact is WRONG; B
        (insert heat, ice->cold): "cold" is on segment 1, wholly uncovered
        and anchored by ``clinician_line_omitted`` — omitted, credited under
        D13, silent under 0.3.3. The verdict is A's; only the 0.3.3 column
        counts B's silent omission."""
        script = _script(("clinician", "ice"), facts=[_fact("present", "ice", 0)])
        document = _doc((SPEAKER_1, "heat"), (SPEAKER_1, "cold"))
        note = _note(document, 0, warnings=[_warning("clinician_line_omitted", 1, 0, 0)])
        metrics = encounter_metrics(document, note, script)
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.ambiguous) == ("wrong", True)
        assert (
            metrics.material_wrong,
            metrics.silent_omissions,
            metrics.silent_omissions_v033,
            metrics.silent_omissions_v1,
        ) == (1, 0, 1, 1)

    def test_the_walk_state_holds_ten_flags(self) -> None:
        """D13 and D8 each added a flag to the fact walk's state (0.3.3's
        ``warned`` and R1's review mark): ten flags, so at most 2**10 states
        per alignment cell."""
        assert validation._FactState._fields == (
            "all_matched",
            "all_deleted",
            "in_any",
            "in_all",
            "warned",
            "surfaced",
            "warned_v1",
            "hedged",
            "warned_v033",
            "marked",
        )
        # Flags only (never a history or a position), so equal states merge
        # and a cell holds at most 2**10 — D7's repeated-token bound is the
        # state's shape, pinned here, rather than one measured walk.
        assert set(typing.get_type_hints(validation._FactState).values()) == {bool}


class TestDeletedByTranscription:
    def test_a_fact_deleted_by_transcription(self) -> None:
        """ref [my, left, knee, hurts, and, i, limp], hyp [my, hurts, and, i,
        limp]: the one optimal alignment deletes "left" and "knee". The fact
        has no aligned word: omitted, not transcribed, never warned — even
        though the rest of the line is in the note."""
        script = _script(
            ("clinician", "my left knee hurts and i limp"),
            facts=[_fact("laterality", "left knee", 0)],
        )
        document = _doc((SPEAKER_1, "my hurts and i limp"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert metrics.words == WordErrors(7, 5, 2)
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.not_transcribed, fact.warned) == ("omitted", True, False)
        assert fact.silent_omission


class TestUncertainty:
    def _script(self) -> EncounterScript:
        return _script(
            ("clinician", "paracetamol 500 mg daily"),
            facts=[_fact("dose", "paracetamol 500 mg", 0, uncertain=True)],
        )

    def test_surfaced_by_a_warning_on_the_facts_own_word(self) -> None:
        document = _doc((SPEAKER_1, "paracetamol ?500 mg daily"))
        note = _checked(document, 0)
        assert [(w.note_warning_code, w.source_coords) for w in note.note_warnings] == [
            ("low_confidence_source", SourceCoords(0, 1, 1)),
            ("number_source", SourceCoords(0, 0, 3)),  # invented-text guard D5
        ]
        fact = _only_fact(encounter_metrics(document, note, self._script()))
        assert (fact.verdict, fact.uncertainty_surfaced) == ("correct", True)

    def test_a_warning_elsewhere_in_the_segment_does_not_surface_it(self) -> None:
        document = _doc((SPEAKER_1, "paracetamol 500 mg ?daily"))
        metrics = encounter_metrics(document, _checked(document, 0), self._script())
        assert _only_fact(metrics).uncertainty_surfaced is False
        assert metrics.uncertainty_missed == 1
        assert rule_failures(OPTION_A, _measured(metrics)) == ("uncertainty_not_surfaced",)

    def test_a_per_line_check_code_never_surfaces_it(self) -> None:
        """Invented-text guard Phase 2 (leg ex2): rule v1's surfacing reads
        `low_confidence_source` only. A `number_source` or `suspect_source`
        spans the whole quoted line — the fact's own words included — and
        must not surface its uncertainty, or the metric would move silently
        (pilot plan Constraint 12)."""
        document = _doc((SPEAKER_1, "paracetamol 500 mg daily"))
        clean = _checked(document, 0)
        assert [w.note_warning_code for w in clean.note_warnings] == ["number_source"]
        line_wide = NoteWarning(
            note_warning_code="suspect_source",
            severity="review",
            section_key=clean.note_warnings[0].section_key,
            assertion_id=clean.note_warnings[0].assertion_id,
            source_coords=SourceCoords(0, 0, 3),
        )
        marked = clean.model_copy(update={"note_warnings": (*clean.note_warnings, line_wide)})
        for note in (clean, marked):
            fact = _only_fact(encounter_metrics(document, note, self._script()))
            assert (fact.verdict, fact.uncertainty_surfaced) == ("correct", False)

    def test_every_repeated_statement_must_surface_it(self) -> None:
        """ref = hyp (one optimal alignment, cost 0) with the fact stated twice
        in its line; Check 1 warns on the SECOND statement's "500" only. The
        first statement is correct but not surfaced, so the fact is missed —
        surfacing spans repeated statements as well as equal-cost
        alternatives (round 12 LOW-003, the same conservative rule as the
        worst-of-occurrences verdict)."""
        script = _script(
            ("clinician", "paracetamol 500 mg daily then paracetamol 500 mg at night"),
            facts=[_fact("dose", "paracetamol 500 mg", 0, uncertain=True)],
        )
        document = _doc((SPEAKER_1, "paracetamol 500 mg daily then paracetamol ?500 mg at night"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert metrics.words.edit_distance == 0
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.uncertainty_surfaced) == ("correct", False)
        assert rule_failures(OPTION_A, _measured(metrics)) == ("uncertainty_not_surfaced",)

    def test_not_expected_uncertain_reads_none(self) -> None:
        script = _script(
            ("clinician", "paracetamol 500 mg daily"),
            facts=[_fact("dose", "paracetamol 500 mg", 0)],
        )
        document = _doc((SPEAKER_1, "paracetamol ?500 mg daily"))
        assert _only_fact(
            encounter_metrics(document, _checked(document, 0), script)
        ).uncertainty_surfaced is None


def _hedge_mark(document: TranscriptDocument, segment: int, aid: str) -> NoteWarning:
    """A ``hedged_source`` warning on the whole of ``segment`` (quoted as
    ``aid``), whatever its words — a stub provider's mark."""
    last = len(document.transcript_segments[segment].transcript_words) - 1
    return NoteWarning(
        note_warning_code="hedged_source",
        severity="review",
        section_key="presenting_complaint",
        assertion_id=aid,
        source_coords=SourceCoords(segment, 0, last),
    )


def _text_holds(text: str, phrases: Sequence[str] | None) -> bool:
    return text_holds_hedge(text, phrases=phrases)


# The pin's own reading of "ends mid-sentence" over a script line's TEXT
# (closing quotes and brackets peeled, then a comma, semicolon, colon or an
# en or em dash) — re-spelled here, so the pin does not read the scope
# through the function it checks.
_JOINING_MARKS = ",;:–—"
_CLOSING = "\"')]}”’»"


def _ends_with_a_join(text: str) -> bool:
    stripped = text.rstrip()
    if not stripped:
        return False
    last_word = stripped.split()[-1].rstrip(_CLOSING)
    return bool(last_word) and last_word[-1] in _JOINING_MARKS


# A script needs a clinician line: a patient-only test ends with this one,
# spoken in the transcript as its last SPEAKER_1 segment — no hedge, no
# structured word, no fact and unquoted, so it adds no mark, no warning, no
# word error and no outcome.
_CLINICIAN_CLOSE = "okay let us have a look"


class TestHedgeCreditAmendment:
    """Metric amendment 2026-10-13 (validation-pass plan D7, decision 0.1
    (a)): an ``expect_uncertain`` fact is also surfaced when it is
    ``correct``, its SCRIPT line holds a spoken hedge, and one of its aligned
    words sits under a ``hedged_source`` mark whose OWN words hold one. Every
    pin both ways; the acoustic-only reading is kept beside it. The clinician
    is SPEAKER_1, so SPEAKER_2's lines are the patient's; a patient-only case
    ends with ``_CLINICIAN_CLOSE``."""

    def test_a_hedged_correct_fact_under_the_checkers_mark_is_surfaced(self) -> None:
        script = _script(
            ("patient", "i think my left knee hurts"),
            ("clinician", _CLINICIAN_CLOSE),
            facts=[_fact("laterality", "left knee", 0, uncertain=True)],
        )
        document = _doc(
            (SPEAKER_2, "i think my left knee hurts"), (SPEAKER_1, _CLINICIAN_CLOSE)
        )
        note = _checked(document, 0)
        assert [(w.note_warning_code, w.source_coords) for w in note.note_warnings] == [
            ("hedged_source", SourceCoords(0, 0, 5))
        ]
        metrics = encounter_metrics(document, note, script)
        assert metrics.words.edit_distance == 0
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.uncertainty_surfaced, fact.uncertainty_surfaced_acoustic) == (
            "correct",
            True,
            False,
        )
        assert (metrics.uncertainty_missed, metrics.uncertainty_surfaced_acoustic) == (0, 0)
        assert metrics.hedge_marks_unhedged == 0
        assert rule_failures(OPTION_A, _measured(metrics)) == ()

    def test_an_unhedged_script_line_gains_no_credit_from_a_mark(self) -> None:
        """The recogniser added a hedge the script never said: the line is
        marked (a real hedge in its words) but the fact is not surfaced."""
        script = _script(
            ("patient", "my left knee hurts"),
            ("clinician", _CLINICIAN_CLOSE),
            facts=[_fact("laterality", "left knee", 0, uncertain=True)],
        )
        document = _doc(
            (SPEAKER_2, "i think my left knee hurts"), (SPEAKER_1, _CLINICIAN_CLOSE)
        )
        note = _checked(document, 0)
        assert [w.note_warning_code for w in note.note_warnings] == ["hedged_source"]
        metrics = encounter_metrics(document, note, script)
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.uncertainty_surfaced) == ("correct", False)
        assert metrics.hedge_marks_unhedged == 0  # the marked words DO hedge
        assert rule_failures(OPTION_A, _measured(metrics)) == ("uncertainty_not_surfaced",)

    def test_a_mark_on_words_without_a_hedge_credits_nothing_and_is_counted(self) -> None:
        """The script hedged but the recogniser dropped the hedge; a stub mark
        on the line is re-derived, finds no hedge, and is counted."""
        script = _script(
            ("patient", "i think my left knee hurts"),
            ("clinician", _CLINICIAN_CLOSE),
            facts=[_fact("laterality", "left knee", 0, uncertain=True)],
        )
        document = _doc((SPEAKER_2, "my left knee hurts"), (SPEAKER_1, _CLINICIAN_CLOSE))
        assert [w.note_warning_code for w in _checked(document, 0).note_warnings] == []
        note = _note(document, 0, warnings=[_hedge_mark(document, 0, "a0")])
        metrics = encounter_metrics(document, note, script)
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.uncertainty_surfaced) == ("correct", False)
        assert metrics.hedge_marks_unhedged == 1

    def test_a_hedged_fact_with_no_mark_is_not_surfaced(self) -> None:
        """No mark: the clinician's own hedged line (Check 1 marks only
        someone else's), and the same line with no warnings at all."""
        script = _script(
            ("clinician", "i think the left knee is sprained"),
            facts=[_fact("laterality", "left knee", 0, uncertain=True)],
        )
        document = _doc((SPEAKER_1, "i think the left knee is sprained"))
        for note in (_checked(document, 0), _note(document, 0)):
            assert note.note_warnings == ()
            fact = _only_fact(encounter_metrics(document, note, script))
            assert (fact.verdict, fact.uncertainty_surfaced) == ("correct", False)

    def test_a_wrong_fact_under_a_mark_is_not_surfaced(self) -> None:
        script = _script(
            ("patient", "i think my left knee hurts"),
            ("clinician", _CLINICIAN_CLOSE),
            facts=[_fact("laterality", "left knee", 0, uncertain=True)],
        )
        document = _doc(
            (SPEAKER_2, "i think my right knee hurts"), (SPEAKER_1, _CLINICIAN_CLOSE)
        )
        note = _checked(document, 0)
        assert "hedged_source" in [w.note_warning_code for w in note.note_warnings]
        fact = _only_fact(encounter_metrics(document, note, script))
        assert (fact.verdict, fact.uncertainty_surfaced) == ("wrong", False)

    def test_a_stub_marking_every_line_is_credited_only_where_both_hedge(self) -> None:
        """Lines 0 and 1 hedge in the script; the recogniser kept line 0's
        hedge and dropped line 1's; line 2 never hedged. A stub marks all
        three: only fact 0 is credited, and the two marks on unhedged words
        are counted."""
        script = _script(
            ("patient", "i think my left knee hurts"),
            ("patient", "maybe the right hip is stiff"),
            ("patient", "the left ankle is fine"),
            ("clinician", _CLINICIAN_CLOSE),
            facts=[
                _fact("laterality", "left knee", 0, uncertain=True),
                _fact("laterality", "right hip", 1, uncertain=True),
                _fact("laterality", "left ankle", 2, uncertain=True),
            ],
        )
        document = _doc(
            (SPEAKER_2, "i think my left knee hurts"),
            (SPEAKER_2, "the right hip is stiff"),
            (SPEAKER_2, "the left ankle is fine"),
            (SPEAKER_1, _CLINICIAN_CLOSE),
        )
        marks = [_hedge_mark(document, index, f"a{index}") for index in range(3)]
        metrics = encounter_metrics(document, _note(document, 0, 1, 2, warnings=marks), script)
        assert [f.verdict for f in metrics.facts] == ["correct", "correct", "correct"]
        assert [f.uncertainty_surfaced for f in metrics.facts] == [True, False, False]
        assert metrics.hedge_marks_unhedged == 2
        assert metrics.uncertainty_missed == 2

    def test_a_scope_ii_mark_is_credited(self) -> None:
        """Validation-run6 plan D5: the fact's line ends in a comma and the
        same speaker's next line holds the hedge — in the script and in the
        transcript. Check 1 marks the fact's line through the scope, the mark
        is re-derived through the same scope, and the script term
        (``script_line_hedged``) holds, so the fact is surfaced."""
        script = _script(
            ("patient", "it started in my left knee,"),
            ("patient", "i think"),
            ("clinician", _CLINICIAN_CLOSE),
            facts=[_fact("laterality", "left knee", 0, uncertain=True)],
        )
        document = _doc(
            (SPEAKER_2, "it started in my left knee,"),
            (SPEAKER_2, "i think"),
            (SPEAKER_1, _CLINICIAN_CLOSE),
        )
        assert validation.script_line_hedged(script, 0)
        note = _checked(document, 0, 1)
        assert [(w.note_warning_code, w.source_coords) for w in note.note_warnings] == [
            ("hedged_source", SourceCoords(0, 0, 5)),
            ("hedged_source", SourceCoords(1, 0, 1)),
        ]
        metrics = encounter_metrics(document, note, script)
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.uncertainty_surfaced, fact.uncertainty_surfaced_acoustic) == (
            "correct",
            True,
            False,
        )
        assert (metrics.uncertainty_missed, metrics.hedge_marks_unhedged) == (0, 0)
        assert rule_failures(OPTION_A, _measured(metrics)) == ()

    def test_a_scope_iii_mark_is_not_credited(self) -> None:
        """Scope (iii) (any adjacent same-speaker line, rejected): the fact's
        line ENDS a sentence before the hedge. Check 1 marks only the hedge's
        own line; a stub mark on the fact's line, as a scope-(iii) checker
        would put, is re-derived as unhedged and counted; the script term
        does not hold. Not surfaced either way."""
        script = _script(
            ("patient", "it started in my left knee."),
            ("patient", "i think"),
            ("clinician", _CLINICIAN_CLOSE),
            facts=[_fact("laterality", "left knee", 0, uncertain=True)],
        )
        document = _doc(
            (SPEAKER_2, "it started in my left knee."),
            (SPEAKER_2, "i think"),
            (SPEAKER_1, _CLINICIAN_CLOSE),
        )
        assert not validation.script_line_hedged(script, 0)
        checked = _checked(document, 0, 1)
        assert [(w.note_warning_code, w.source_coords) for w in checked.note_warnings] == [
            ("hedged_source", SourceCoords(1, 0, 1))
        ]
        stub = _note(document, 0, 1, warnings=[_hedge_mark(document, 0, "a0")])
        for note, unhedged in ((checked, 0), (stub, 1)):
            metrics = encounter_metrics(document, note, script)
            fact = _only_fact(metrics)
            assert (fact.verdict, fact.uncertainty_surfaced) == ("correct", False)
            assert (metrics.uncertainty_missed, metrics.hedge_marks_unhedged) == (1, unhedged)

    def test_a_hedge_the_recogniser_split_off_is_not_credited(self) -> None:
        """The script joins the hedge by a comma; the recogniser ended the
        fact's segment with a full stop (D12's named residue, kept a fail by
        D17): the script term holds, but the product puts no mark on the
        fact's line, so nothing is credited."""
        script = _script(
            ("patient", "it started in my left knee,"),
            ("patient", "i think"),
            ("clinician", _CLINICIAN_CLOSE),
            facts=[_fact("laterality", "left knee", 0, uncertain=True)],
        )
        document = _doc(
            (SPEAKER_2, "it started in my left knee."),
            (SPEAKER_2, "i think"),
            (SPEAKER_1, _CLINICIAN_CLOSE),
        )
        assert validation.script_line_hedged(script, 0)
        metrics = encounter_metrics(document, _checked(document, 0, 1), script)
        assert (_only_fact(metrics).uncertainty_surfaced, metrics.uncertainty_missed) == (False, 1)

    @pytest.mark.parametrize(
        "path",
        # Named sets only (written when ``heldout-3`` was blind, C12; the
        # blind set is ``heldout-4`` since validation-run7 Task 0.5).
        [
            path
            for name in ("heldout", "heldout-2")
            for path in held_out_set(name).script_paths()
        ],
        ids=lambda path: path.stem,
    )
    def test_script_line_hedged_is_segment_hedged_on_the_reference_document(
        self, path: Path
    ) -> None:
        """Validation-run6 plan D5's pin: on every seen held-out script, the
        script term equals ``note.segment_hedged`` on
        ``reference_document(script)`` line for line, and both equal the
        scope re-read from the script's TEXT (a line's role, its trailing
        mark, a neighbour's hedge), under both lexicons. No seen held-out
        line ends in a joining mark (checked 2026-10-24, the 50 too), so here
        the pin reads the line's own hedge; the join through a script's
        punctuation and roles is pinned by the synthetic scripts above
        (``test_a_scope_ii_mark_is_credited`` and its two negatives) and below
        (``test_the_reference_document_carries_the_join``)."""
        script = validation.load_script(path)
        reference = validation.reference_document(script)
        lines = script.lines
        for phrases in (None, validation.REFERENCE_HEDGES):
            for index in range(len(lines)):
                by_text = _text_holds(lines[index].text, phrases) or any(
                    0 <= other < len(lines)
                    and lines[other].role == lines[index].role
                    and _text_holds(lines[other].text, phrases)
                    and _ends_with_a_join(lines[min(index, other)].text)
                    for other in (index - 1, index + 1)
                )
                hedged = validation.script_line_hedged(script, index, phrases=phrases)
                assert hedged == segment_hedged(reference, index, phrases=phrases), index
                assert hedged == by_text, index

    def test_the_reference_document_carries_the_join(self) -> None:
        """The pin's text oracle over a script that DOES join: commas, a
        dash, a closing quote, a role change and a full stop — line for line,
        under both lexicons."""
        script = _script(
            ("patient", "it started in my left knee,"),  # 0: joined to 1
            ("patient", "i think"),  # 1: own hedge
            ("patient", 'then the "right one,"'),  # 2: joined to 3 through the quote
            ("patient", "it might be —"),  # 3: reference-only hedge; joined to 4
            ("patient", "worse at night."),  # 4
            ("clinician", "okay maybe,"),  # 5: own hedge
            ("patient", "and the hip."),  # 6: another role before it
            facts=[_fact("laterality", "left knee", 0)],
        )
        reference = validation.reference_document(script)
        expected = {
            None: [True, True, False, False, False, True, False],
            validation.REFERENCE_HEDGES: [True, True, True, True, True, True, False],
        }
        for phrases, wanted in expected.items():
            got = [
                validation.script_line_hedged(script, index, phrases=phrases)
                for index in range(len(script.lines))
            ]
            assert got == wanted, phrases is None
            assert got == [
                segment_hedged(reference, index, phrases=phrases)
                for index in range(len(script.lines))
            ]
            assert got == [
                _text_holds(line.text, phrases)
                or any(
                    0 <= other < len(script.lines)
                    and script.lines[other].role == line.role
                    and _text_holds(script.lines[other].text, phrases)
                    and _ends_with_a_join(script.lines[min(index, other)].text)
                    for other in (index - 1, index + 1)
                )
                for index, line in enumerate(script.lines)
            ]

    def test_the_held_out_sets_read_by_the_pin_are_present(self) -> None:
        """The pin above is not vacuous: both named sets hold scripts."""
        assert len(held_out_set("heldout").script_paths()) == 22
        assert held_out_set("heldout-2").script_paths()

    def test_low_confidence_alone_still_surfaces_and_is_the_acoustic_reading(self) -> None:
        script = _script(
            ("clinician", "paracetamol 500 mg daily"),
            facts=[_fact("dose", "paracetamol 500 mg", 0, uncertain=True)],
        )
        document = _doc((SPEAKER_1, "paracetamol ?500 mg daily"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        fact = _only_fact(metrics)
        assert (fact.uncertainty_surfaced, fact.uncertainty_surfaced_acoustic) == (True, True)
        assert (metrics.uncertainty_missed, metrics.uncertainty_surfaced_acoustic) == (0, 1)

    def test_the_acoustic_reading_is_runs_1_to_4s_predicate(self) -> None:
        """Both readings over one hedged patient fact: the recogniser's
        low-confidence word alone surfaces it acoustically; the hedge mark
        alone surfaces it only under the amendment; a fact not expected
        uncertain reads None in both."""
        script = _script(
            ("patient", "i think my left knee hurts"),
            ("clinician", _CLINICIAN_CLOSE),
            facts=[
                _fact("laterality", "left knee", 0, uncertain=True),
                _fact("present", "hurts", 0),
            ],
        )
        for text, acoustic in (
            ("i think my ?left knee hurts", True),
            ("i think my left knee hurts", False),
        ):
            document = _doc((SPEAKER_2, text), (SPEAKER_1, _CLINICIAN_CLOSE))
            metrics = encounter_metrics(document, _checked(document, 0), script)
            first, second = metrics.facts
            assert (first.uncertainty_surfaced, first.uncertainty_surfaced_acoustic) == (
                True,
                acoustic,
            ), text
            assert (second.uncertainty_surfaced, second.uncertainty_surfaced_acoustic) == (
                None,
                None,
            ), text
            assert metrics.uncertainty_surfaced_acoustic == int(acoustic), text

    def test_the_new_counts_are_validated(self) -> None:
        with pytest.raises(ValueError, match="hedge_marks_unhedged must be"):
            dataclasses.replace(
                encounter_metrics(
                    _doc((SPEAKER_1, "knee")),
                    _note(_doc((SPEAKER_1, "knee"))),
                    _script(("clinician", "knee")),
                ),
                hedge_marks_unhedged=-1,
            )
        with pytest.raises(ValueError, match="uncertainty_surfaced_acoustic must be a flag"):
            FactOutcome(
                fact_index=0,
                kind="present",
                material=True,
                verdict="correct",
                warned=False,
                uncertainty_surfaced=True,
                not_transcribed=False,
                ambiguous=False,
                uncertainty_surfaced_acoustic="yes",  # type: ignore[arg-type]
            )


class TestAmbiguity:
    def test_equal_cost_alternatives_take_the_worse_outcome(self) -> None:
        """ref [the, left, knee], hyp [the, right]: two optimal alignments of
        cost 2 — (left->right, delete knee) and (delete left, knee->right).
        For the fact [knee] the first leaves it unaligned (omitted), the
        second puts a substituted word in the note (wrong): it reports
        ``wrong`` and ``ambiguous``. "right" is substituted on BOTH, so the
        line is unsupported either way."""
        script = _script(("clinician", "the left knee"), facts=[_fact("present", "knee", 0)])
        document = _doc((SPEAKER_1, "the right"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert metrics.words.edit_distance == 2
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.ambiguous) == ("wrong", True)
        assert metrics.unsupported_clinical_lines == 1

    def test_a_silent_omission_on_another_alternative_is_still_counted(self) -> None:
        """ref [rest, ice], hyp [heat] (the peer's case, round 14 PR-MED-056):
        two optimal alignments of cost 2 — A (rest->heat, delete ice): the
        material fact [ice] is omitted and unwarned; B (delete rest,
        ice->heat): it is wrong. The verdict is B's, but A's silent omission
        is counted too, so a rule allowing one material wrong still fails on
        the omission."""
        script = _script(("clinician", "rest ice"), facts=[_fact("present", "ice", 0)])
        document = _doc((SPEAKER_1, "heat"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert metrics.words.edit_distance == 2
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.ambiguous, fact.silently_omitted_somewhere) == (
            "wrong",
            True,
            True,
        )
        assert (metrics.material_wrong, metrics.silent_omissions) == (1, 1)
        loose = PassRule(schema_version=1, rule_name="loose", max_material_wrong=1)
        assert rule_failures(loose, _measured(metrics)) == ("silent_omission",)

    def test_uncertainty_is_surfaced_only_if_every_alternative_surfaces_it(self) -> None:
        """ref [use, ice], hyp [ice, ?daily] (Check 1 warns on "daily"): two
        optimal alignments of cost 2 — A (delete use, match ice, insert
        daily): the fact [ice] is correct but its word is not low-confidence;
        B (use->ice, ice->daily): the fact is wrong, on the low-confidence
        word. The verdict is B's (worse), and the uncertainty counts as
        surfaced only if EVERY alternative surfaces it — A does not, so it is
        missed (round 11 LOW-008: the worst verdict's alternative must not
        hide an uncertainty failure)."""
        script = _script(
            ("clinician", "use ice"),
            facts=[_fact("present", "ice", 0, material=False, uncertain=True)],
        )
        document = _doc((SPEAKER_1, "ice ?daily"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert metrics.words.edit_distance == 2
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.uncertainty_surfaced, fact.ambiguous) == (
            "wrong",
            False,
            True,
        )
        assert rule_failures(OPTION_A, _measured(metrics)) == ("uncertainty_not_surfaced",)


class TestOverlap:
    def test_an_overlapped_pair_of_turns(self) -> None:
        """Line 1 starts before line 0 ends; the transcript interleaves them:
        ref [how, is, the, left, knee, today, much, better, thanks] (spoken
        order by start), hyp [how, is, the, left, knee, much, better, today,
        thanks]. The one optimal alignment (cost 2) deletes the reference
        "today" and inserts the transcript's "today": the laterality fact is
        correct, the displaced "today" reads as not transcribed (the
        conservative direction), and the inserted word is counted, not a
        clinical line."""
        script = _script(
            ("clinician", "how is the left knee today"),
            ("patient", "much better thanks"),
            facts=[_fact("laterality", "left knee", 0), _fact("present", "today", 0)],
        )
        document = _doc((SPEAKER_1, "how is the left knee much better today thanks"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert metrics.words == WordErrors(9, 9, 2)
        laterality, today = metrics.facts
        assert laterality.verdict == "correct"
        assert (today.verdict, today.not_transcribed) == ("omitted", True)
        assert metrics.unsupported_clinical_lines == 0
        assert metrics.other_unsupported_words == 1
        # The residue, pinned (round 11 MED-002): a displaced word every
        # alignment reads as not transcribed is a silent omission when it is
        # material, so a correctly transcribed but reordered overlap fails.
        assert rule_failures(OPTION_A, _measured(metrics)) == ("silent_omission",)

    def test_a_reordered_negation_is_an_unsupported_clinical_line(self) -> None:
        """ref [any, numbness, in, the, fingers, no, numbness] (the answer
        overlaps the question's end), hyp [any, numbness, no, in, the,
        fingers, numbness]: the one optimal alignment (cost 2) inserts the
        transcript's "no" and deletes the reference "no" — so a negation
        word that WAS said, only earlier, is an inserted structured-claim
        word in a note line (unsupported), and the fact [no, numbness] has
        "numbness" carried but "no" deleted (wrong). Measured, not excused
        (round 11 MED-002)."""
        script = _script(
            ("clinician", "any numbness in the fingers"),
            ("patient", "no numbness"),
            facts=[_fact("negation", "no numbness", 1)],
        )
        document = _doc((SPEAKER_1, "any numbness no in the fingers numbness"))
        metrics = encounter_metrics(document, _checked(document, 0), script)
        assert metrics.words == WordErrors(7, 7, 2)
        assert metrics.unsupported_clinical_lines == 1
        assert _only_fact(metrics).verdict == "wrong"
        assert rule_failures(OPTION_A, _measured(metrics)) == (
            "unsupported_clinical_line",
            "material_wrong",
        )


class TestConfigLines:
    def test_counted_separately_and_never_aligned(self) -> None:
        script = _script(("clinician", "my left knee hurts"))
        document = _doc((SPEAKER_1, "my left knee hurts"))
        authored = NoteAssertion(
            assertion_id="p1",
            section_key="presenting_complaint",
            note_span=NoteSpan(span_text="Ice pack use explained.", provenance="autofill"),
            proposal_id="p1",
            shown_text_digest=text_digest("Ice pack use explained."),
            config_digest=DIGEST,
            confirmation=ConfirmationDecision(
                proposal_id="p1", note_confirmation="confirmed", decided_at=_NOW
            ),
        )
        metrics = encounter_metrics(document, _note(document, 0, authored=[authored]), script)
        assert (metrics.transcript_lines, metrics.config_lines) == (1, 1)
        assert metrics.unsupported_clinical_lines == 0


# ---------------------------------------------------------------------------
# the checker tally, through the real compose -> confirm -> finalise pipeline
# ---------------------------------------------------------------------------

# An accurate transcript: every patient line is cue-routed into the note by
# the shipped cues ("sore", "pain in", "hurts"); the clinician's line holds
# the autofill triggers and is routed by "we will".
_PIPELINE_TURNS: tuple[tuple[str, str, str], ...] = (
    ("patient", SPEAKER_1, "my left knee is sore when i walk"),
    ("patient", SPEAKER_1, "i take paracetamol 500 mg daily for the pain in my knee"),
    ("patient", SPEAKER_1, "it hurts and there is swelling"),
    (
        "clinician",
        SPEAKER_2,
        "we will do the strapping and the usual medication and the usual advice",
    ),
)
_PIPELINE_FACTS = [
    _fact("laterality", "left knee", 0),
    _fact("dose", "paracetamol 500 mg", 1),
    _fact("present", "there is swelling", 2),
]
# One conflicting rule per class: side, dose, negation.
_CONFLICTS: dict[str, AutofillRule] = {
    "side": AutofillRule(
        rule_id="rule-side",
        section_key="treatment_performed",
        trigger_phrase="strapping",
        expansion=("Right knee strapped.",),
    ),
    "dose": AutofillRule(
        rule_id="rule-dose",
        section_key="management_plan",
        trigger_phrase="usual medication",
        expansion=("Paracetamol 1000 mg daily.",),
    ),
    "negation": AutofillRule(
        rule_id="rule-negation",
        section_key="objective_examination",
        trigger_phrase="usual advice",
        expansion=("No swelling.",),
    ),
}


def _pipeline_config(tmp_path: Path, *rules: AutofillRule) -> NoteConfig:
    """The shipped defaults (one template profile, the shipped cues) read
    from an EMPTY explicit folder, plus ``rules``."""
    empty = tmp_path / "config"
    empty.mkdir()
    shipped = load_note_config(empty)
    return NoteConfig(
        template_profiles=shipped.template_profiles,
        autofill_rules=rules,
        section_cues=shipped.section_cues,
    )


def _pipeline_metrics(
    tmp_path: Path, rules: Sequence[AutofillRule], expected_warnings: Sequence[str] = ()
) -> EncounterMetrics:
    script = _script(
        *((role, text) for role, _speaker, text in _PIPELINE_TURNS),
        facts=_PIPELINE_FACTS,
        expected_warnings=expected_warnings,
    )
    document = _doc(*((speaker, text) for _role, speaker, text in _PIPELINE_TURNS))
    config = _pipeline_config(tmp_path, *rules)
    draft = compose_draft(
        document, config, ExtractiveNoteProvider(cues=config.normalised_cues()),
        clinician_speaker=SPEAKER_2,
    )
    note = finalise_note(draft, confirm_all(draft, _NOW), document, config, created_at=_NOW)
    return encounter_metrics(document, note, script)


class TestCheckerTally:
    def test_the_accurate_encounter_with_no_conflict_passes(self, tmp_path: Path) -> None:
        metrics = _pipeline_metrics(tmp_path, ())
        assert [f.verdict for f in metrics.facts] == ["correct", "correct", "correct"]
        assert metrics.checker_failures == ()
        assert metrics.unsupported_clinical_lines == 0
        assert rule_failures(OPTION_A, _measured(metrics)) == ()

    @pytest.mark.parametrize(
        ("conflict", "codes"),
        [
            ("side", {"laterality_mismatch"}),
            ("dose", {"dose_mismatch", "contradiction"}),
            ("negation", {"contradiction"}),
        ],
    )
    def test_a_conflicting_confirmed_config_proposal_fails_the_encounter(
        self, tmp_path: Path, conflict: str, codes: set[str]
    ) -> None:
        """The transcript is accurate and every fact is correct, yet the
        confirmed config line contradicts it: ``finalise_note`` returns the
        note WITH the checker's warning, and the tally fails the encounter."""
        metrics = _pipeline_metrics(tmp_path, (_CONFLICTS[conflict],))
        assert [f.verdict for f in metrics.facts] == ["correct", "correct", "correct"]
        assert metrics.config_lines == 1
        assert metrics.checker_failures and set(metrics.checker_failures) <= codes
        assert metrics.checker_failure_count >= 1
        assert rule_failures(OPTION_A, _measured(metrics)) == ("checker_failure",)

    def test_an_expected_contradiction_does_not_fail(self, tmp_path: Path) -> None:
        metrics = _pipeline_metrics(
            tmp_path, (_CONFLICTS["negation"],), expected_warnings=("contradiction",)
        )
        assert dict(metrics.checker_tally)["contradiction"] >= 1
        assert metrics.checker_failures == ()
        assert metrics.expected_warnings_absent == ()
        assert rule_failures(OPTION_A, _measured(metrics)) == ()

    def test_an_expected_warning_the_checker_did_not_raise_is_reported(
        self, tmp_path: Path
    ) -> None:
        metrics = _pipeline_metrics(tmp_path, (), expected_warnings=("laterality_mismatch",))
        assert metrics.expected_warnings_absent == ("laterality_mismatch",)
        assert rule_failures(OPTION_A, _measured(metrics)) == ()


# ---------------------------------------------------------------------------
# the pass rule
# ---------------------------------------------------------------------------


class TestPassRule:
    def test_the_repository_option_a_file_is_every_default(self) -> None:
        path = validation.REPO_ROOT / "validation" / "rules" / "option-a-proposed.json"
        assert validation.load_pass_rule(path) == OPTION_A

    def test_harness_errors_and_unresolved_roles_always_fail(self) -> None:
        assert rule_failures(OPTION_A, EncounterOutcome("syn-a", "error", "OSError")) == (
            "harness_error",
        )
        assert rule_failures(OPTION_A, EncounterOutcome("syn-a", "role_unresolved")) == (
            "role_unresolved",
        )

    def test_a_word_error_rate_ceiling_is_optional(self) -> None:
        script = _script(("clinician", "my left knee hurts"))
        document = _doc((SPEAKER_1, "my right knee hurts"))
        metrics = encounter_metrics(document, _checked(document), script)
        assert "word_error_rate" not in rule_failures(OPTION_A, _measured(metrics))
        ceiling = PassRule(schema_version=1, rule_name="option-b", max_word_error_rate=0.2)
        assert "word_error_rate" in rule_failures(ceiling, _measured(metrics))


# ---------------------------------------------------------------------------
# validation-run6 plan D8 (as amended by D14): the residue classes
# ---------------------------------------------------------------------------

# The run's reading of the script's own words, built by hand: fact 0 right
# on the reference, no boundary there, no tail.
_RIGHT_ON_REFERENCE = ReferenceReading(facts_right=frozenset({0}), boundary=None, tail_start=None)


class TestResidueR1:
    """R1 — a recogniser error: a material fact reported ``wrong`` or a
    silent omission, no alternative of any statement matching every token,
    right on the reference reading, and (for ``wrong``) every wrong
    alternative carrying a review mark. It clears ``material_wrong`` and
    ``silent_omission`` only."""

    _SCRIPT_LINE = "the ankle is swollen"

    def _script(self, **fact: Any) -> EncounterScript:
        return _script(
            ("clinician", self._SCRIPT_LINE), facts=[_fact("present", "ankle", 0, **fact)]
        )

    def _misheard(
        self, *warnings: NoteWarning, reference: ReferenceReading | None = _RIGHT_ON_REFERENCE
    ) -> EncounterMetrics:
        """ref [the, ankle, is, swollen], hyp [the, angle, is, swollen]: one
        optimal alignment (cost 1), ankle->angle inside the quoted line — the
        fact is ``wrong``; "angle" is no structured-claim word, so the line
        stays supported."""
        document = _doc((SPEAKER_1, "the angle is swollen"))
        return encounter_metrics(
            document, _note(document, 0, warnings=warnings), self._script(), reference=reference
        )

    def test_a_marked_mishearing_right_on_the_reference_is_r1(self) -> None:
        metrics = self._misheard(_warning("low_confidence_source", 0, 1, 1))
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.residue_r1, fact.residue_r2, fact.residue_r3) == (
            "wrong",
            True,
            False,
            False,
        )
        assert (metrics.material_wrong, metrics.material_wrong_v2, metrics.r1_facts) == (1, 0, 1)
        assert metrics.unsupported_clinical_lines == 0

    @pytest.mark.parametrize("code", sorted(validation.REVIEW_MARK_CODES))
    def test_every_review_mark_code_counts(self, code: str) -> None:
        assert _only_fact(self._misheard(_warning(code, 0, 0, 3))).residue_r1

    def test_an_unmarked_mishearing_is_not_r1(self) -> None:
        """A confidently misheard word on an unmarked line still fails."""
        fact = _only_fact(self._misheard())
        assert (fact.verdict, fact.residue_r1) == ("wrong", False)

    def test_a_mark_that_is_no_review_mark_is_not_r1(self) -> None:
        fact = _only_fact(self._misheard(_warning("high_risk_omission", 0, 0, 3)))
        assert fact.residue_r1 is False

    def test_wrong_on_the_reference_too_is_not_r1(self) -> None:
        reading = ReferenceReading(facts_right=frozenset(), boundary=None, tail_start=None)
        mark = _warning("low_confidence_source", 0, 1, 1)
        assert _only_fact(self._misheard(mark, reference=reading)).residue_r1 is False

    def test_without_a_reference_reading_no_class_needing_one_holds(self) -> None:
        mark = _warning("low_confidence_source", 0, 1, 1)
        assert _only_fact(self._misheard(mark, reference=None)).residue_r1 is False

    def test_a_non_material_fact_is_never_r1(self) -> None:
        document = _doc((SPEAKER_1, "the angle is swollen"))
        note = _note(document, 0, warnings=[_warning("low_confidence_source", 0, 1, 1)])
        metrics = encounter_metrics(
            document, note, self._script(material=False), reference=_RIGHT_ON_REFERENCE
        )
        assert _only_fact(metrics).residue_r1 is False

    def test_every_token_matched_is_a_routing_error_not_r1(self) -> None:
        """The transcript is right and the note quotes only "the ankle": the
        fact [ankle, is, swollen] is ``wrong`` with every token MATCHED — the
        product's routing, never the recogniser."""
        script = _script(
            ("clinician", self._SCRIPT_LINE), facts=[_fact("present", "ankle is swollen", 0)]
        )
        document = _doc((SPEAKER_1, self._SCRIPT_LINE))
        note = _note(document, (0, 0, 1), warnings=[_warning("low_confidence_source", 0, 1, 1)])
        fact = _only_fact(encounter_metrics(document, note, script, reference=_RIGHT_ON_REFERENCE))
        assert (fact.verdict, fact.residue_r1) == ("wrong", False)

    def test_a_fact_the_recogniser_deleted_is_r1_and_clears_the_silent_omission(self) -> None:
        """ref [the, ankle, is, swollen, today], hyp [the, is, swollen,
        today]: the one alignment deletes "ankle" — not transcribed, a silent
        omission on a quoted line; R1 clears it (no review mark is needed for
        an omission)."""
        script = _script(
            ("clinician", "the ankle is swollen today"), facts=[_fact("present", "ankle", 0)]
        )
        document = _doc((SPEAKER_1, "the is swollen today"))
        metrics = encounter_metrics(
            document, _note(document, 0), script, reference=_RIGHT_ON_REFERENCE
        )
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.not_transcribed, fact.silent_omission) == (
            "omitted",
            True,
            True,
        )
        assert (fact.residue_r1, fact.silent_omission_v2) == (True, False)
        assert (metrics.silent_omissions, metrics.silent_omissions_v2) == (1, 0)

    def test_one_r1_fact_clears_both_raw_counts_and_counts_once(self) -> None:
        """ref [rest, ice], hyp [heat] (the peer's PR-MED-056 case): A
        omits [ice] unwarned, B renders it as the marked "heat" — wrong and
        silent on the raw counts; one R1 fact clears both."""
        script = _script(("clinician", "rest ice"), facts=[_fact("present", "ice", 0)])
        document = _doc((SPEAKER_1, "heat"))
        note = _note(document, 0, warnings=[_warning("low_confidence_source", 0, 0, 0)])
        metrics = encounter_metrics(document, note, script, reference=_RIGHT_ON_REFERENCE)
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.silently_omitted_somewhere, fact.residue_r1) == (
            "wrong",
            True,
            True,
        )
        assert (metrics.material_wrong, metrics.silent_omissions) == (1, 1)
        assert (metrics.material_wrong_v2, metrics.silent_omissions_v2) == (0, 0)
        assert metrics.r1_facts == 1

    @pytest.mark.parametrize(
        ("marks", "r1"), [(((0, 0, 0),), False), (((0, 0, 0), (0, 2, 2)), True)]
    )
    def test_every_statement_wrong_must_be_marked(
        self, marks: tuple[tuple[int, int, int], ...], r1: bool
    ) -> None:
        """The fact stated twice, both misheard (ice->heat twice, one
        alignment of cost 2): one mark leaves the second statement unmarked,
        so the fact is no R1; marks on both make it one."""
        script = _script(("clinician", "ice then ice"), facts=[_fact("present", "ice", 0)])
        document = _doc((SPEAKER_1, "heat then heat"))
        warnings = [_warning("low_confidence_source", *mark) for mark in marks]
        note = _note(document, 0, warnings=warnings)
        fact = _only_fact(encounter_metrics(document, note, script, reference=_RIGHT_ON_REFERENCE))
        assert (fact.verdict, fact.residue_r1) == ("wrong", r1)

    @pytest.mark.parametrize(("marked_segments", "r1"), [((0,), False), ((0, 1), True)])
    def test_every_wrong_alternative_across_segments_must_be_marked(
        self, marked_segments: tuple[int, ...], r1: bool
    ) -> None:
        """ref [ice], hyp [heat | cold] over two quoted segments: two optimal
        alignments of cost 2 — A (ice->heat, insert cold), B (insert heat,
        ice->cold) — both ``wrong``. A mark on "heat" alone leaves B
        unmarked, so the fact is no R1; marks on both make it one."""
        script = _script(("clinician", "ice"), facts=[_fact("present", "ice", 0)])
        document = _doc((SPEAKER_1, "heat"), (SPEAKER_1, "cold"))
        warnings = [_warning("low_confidence_source", s, 0, 0) for s in marked_segments]
        note = _note(document, 0, 1, warnings=warnings)
        fact = _only_fact(encounter_metrics(document, note, script, reference=_RIGHT_ON_REFERENCE))
        assert (fact.verdict, fact.ambiguous, fact.residue_r1) == ("wrong", False, r1)

    def test_r1_does_not_clear_an_unsurfaced_uncertainty(self) -> None:
        """A misheard fact expected uncertain on a line that voices doubt in
        words ("might", a reference hedge): R1 clears the wrong verdict, and
        nothing clears the missed uncertainty (R2 alone may, and the words
        rule it out)."""
        script = _script(
            ("clinician", "the ankle might be swollen"),
            facts=[_fact("present", "ankle", 0, uncertain=True)],
        )
        document = _doc((SPEAKER_1, "the angle might be swollen"))
        note = _note(document, 0, warnings=[_warning("number_source", 0, 0, 4)])
        metrics = encounter_metrics(document, note, script, reference=_RIGHT_ON_REFERENCE)
        fact = _only_fact(metrics)
        assert (fact.residue_r1, fact.residue_r2, fact.uncertainty_surfaced) == (True, False, False)
        assert (metrics.material_wrong_v2, metrics.uncertainty_missed_v2) == (0, 1)

    def test_the_one_alignment_carries_r1(self) -> None:
        """D8: R1 reads ``_Alignment``'s walk, never ``align_transcripts``."""
        tree = ast.parse(textwrap.dedent(inspect.getsource(validation.encounter_metrics)))
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        assert "_Alignment" in names
        assert "align_transcripts" not in names


class TestResidueR2:
    """R2 — doubt carried by tone only: an unsurfaced uncertainty whose
    script line, within the hedge scope, holds no ``REFERENCE_HEDGES``
    phrase. It clears ``uncertainty_not_surfaced`` only, and needs no
    reference reading."""

    def _metrics(
        self, script_line: str, transcript: str, *spans: Span, checked: bool = False
    ) -> EncounterMetrics:
        script = _script(
            ("clinician", script_line), facts=[_fact("present", "ankle", 0, uncertain=True)]
        )
        document = _doc((SPEAKER_1, transcript))
        note = _checked(document, *spans) if checked else _note(document, *spans)
        return encounter_metrics(document, note, script)

    def test_an_unsurfaced_uncertainty_on_an_unhedged_line_is_r2(self) -> None:
        metrics = self._metrics("the ankle is swollen", "the ankle is swollen", 0)
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.uncertainty_surfaced, fact.residue_r2) == (
            "correct",
            False,
            True,
        )
        assert (metrics.uncertainty_missed, metrics.uncertainty_missed_v2, metrics.r2_facts) == (
            1,
            0,
            1,
        )
        assert rule_failures(OPTION_A, _measured(metrics)) == ("uncertainty_not_surfaced",)

    def test_a_reference_only_hedge_rules_r2_out(self) -> None:
        """"might" is in the reference lexicon and not the product's: the
        product cannot credit it, and the words voice the doubt — no R2."""
        line = "the ankle might be swollen"
        assert not text_holds_hedge(line)
        assert text_holds_hedge(line, phrases=REFERENCE_HEDGES)
        metrics = self._metrics(line, line, 0)
        fact = _only_fact(metrics)
        assert (fact.uncertainty_surfaced, fact.residue_r2) == (False, False)
        assert (metrics.uncertainty_missed, metrics.uncertainty_missed_v2) == (1, 1)

    def test_a_surfaced_uncertainty_is_never_r2(self) -> None:
        metrics = self._metrics("the ankle is swollen", "the ?ankle is swollen", 0, checked=True)
        fact = _only_fact(metrics)
        assert (fact.uncertainty_surfaced, fact.residue_r2) == (True, False)
        assert metrics.r2_facts == 0

    def test_a_fact_not_expected_uncertain_is_never_r2(self) -> None:
        script = _script(
            ("clinician", "the ankle is swollen"), facts=[_fact("present", "ankle", 0)]
        )
        document = _doc((SPEAKER_1, "the ankle is swollen"))
        fact = _only_fact(encounter_metrics(document, _note(document, 0), script))
        assert (fact.uncertainty_surfaced, fact.residue_r2) == (None, False)

    def test_r2_does_not_clear_a_silent_omission(self) -> None:
        metrics = self._metrics("the ankle is swollen", "the ankle is swollen")
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.silent_omission, fact.residue_r2) == ("omitted", True, True)
        assert (metrics.silent_omissions_v2, metrics.uncertainty_missed_v2) == (1, 0)
        assert rule_failures(_RULE_V2, _measured(metrics), set_name="gate") == (
            "silent_omission",
        )


class TestResidueR3:
    """R3 — an unbroken next patient (D14): a material fact ``wrongly_present``
    in a next-patient-axis script, on a line at or after the reference tail
    start, with no boundary on the measured transcript (Check 6's warning
    absent) nor on the script's own words. Counted per ENCOUNTER; it clears
    ``material_wrong`` only."""

    _LINES = (
        ("clinician", "see you next week"),
        ("patient", "lovely weather today"),
        ("clinician", "good morning come on in"),
        ("patient", "my wrist hurts"),
    )
    _SPEAKERS = (SPEAKER_1, SPEAKER_2, SPEAKER_1, SPEAKER_2)

    def _metrics(
        self,
        *,
        axes: Sequence[str] = ("end_and_new_patient",),
        reference: ReferenceReading | None = None,
        boundary: int | None = None,
        material: bool = True,
        extra: tuple[tuple[str, str], ...] = (),
    ) -> EncounterMetrics:
        """Every line quoted; facts: absent [weather] (line 1, before the
        tail start 2) and absent [wrist], [hurts] (line 3); ``extra`` lines
        (the clinician's) after them."""
        lines = (*self._LINES, *extra)
        script = _script(
            *lines,
            facts=[
                _fact("absent", "weather", 1, material=material),
                _fact("absent", "wrist", 3, material=material),
                _fact("absent", "hurts", 3, material=material),
            ],
            axes=axes,
        )
        speakers = (*self._SPEAKERS, *(SPEAKER_1 for _line in extra))
        document = _doc(*zip(speakers, (text for _role, text in lines), strict=True))
        warnings = [] if boundary is None else [_warning("possible_next_patient", boundary, 0, 2)]
        note = _note(document, *range(len(lines)), warnings=warnings)
        if reference is None:
            reference = ReferenceReading(frozenset(), boundary=None, tail_start=2)
        return encounter_metrics(document, note, script, reference=reference)

    def test_the_next_patients_facts_after_the_tail_are_r3_once(self) -> None:
        metrics = self._metrics()
        assert [f.verdict for f in metrics.facts] == ["wrongly_present"] * 3
        assert [f.residue_r3 for f in metrics.facts] == [False, True, True]
        assert metrics.r3_event
        assert (metrics.material_wrong, metrics.material_wrong_v2) == (3, 1)
        outcome = _measured(metrics)
        (_r1, _r2, r3) = class_counts(_RULE_V2, [outcome], "gate")
        assert (r3.total, r3.members) == (1, (("syn-test", None),))

    @pytest.mark.parametrize(
        "case",
        ["measured boundary", "reference boundary", "no tail", "no axis"],
    )
    def test_each_condition_is_required(self, case: str) -> None:
        reference = ReferenceReading(
            frozenset(),
            boundary=2 if case == "reference boundary" else None,
            tail_start=None if case == "no tail" else 2,
        )
        metrics = self._metrics(
            axes=("negation",) if case == "no axis" else ("end_and_new_patient",),
            reference=reference,
            boundary=2 if case == "measured boundary" else None,
        )
        assert not any(f.residue_r3 for f in metrics.facts)
        assert (metrics.material_wrong, metrics.material_wrong_v2) == (3, 3)

    def test_a_boundary_that_fired_after_the_fact_still_rules_r3_out(self) -> None:
        """D8 (peer round 3 PR-MED-018): a measured boundary anywhere — here
        on segment 4, after the facts on line 3 — leaves the facts failing,
        the conservative reading."""
        metrics = self._metrics(boundary=4, extra=(("clinician", "it is sore"),))
        assert [f.verdict for f in metrics.facts] == ["wrongly_present"] * 3
        assert not any(f.residue_r3 for f in metrics.facts)
        assert (metrics.material_wrong, metrics.material_wrong_v2) == (3, 3)

    def test_a_non_material_fact_consumes_no_allowance(self) -> None:
        metrics = self._metrics(material=False)
        assert [f.verdict for f in metrics.facts] == ["wrongly_present"] * 3
        assert not any(f.residue_r3 for f in metrics.facts)
        assert not metrics.r3_event
        assert (metrics.material_wrong, metrics.material_wrong_v2) == (0, 0)


# The reference reading's scripts (D8, D14): ``next_patient_boundary`` on the
# script's own words. "On examination" is a shipped cue (the head-case
# guard's earlier content); the closing and the greeting are frozen phrases.
# The patient's reply is "Thanks." — since validation-run7 Task 0.4 (c)
# (2026-10-26) "thank you" is a closing, which would sit in the window.
_CUED = ("clinician", "On examination the left knee is tender.")
_BOUNDARY_CASES = {
    "closing two lines before the greeting": (
        (
            _CUED,
            ("clinician", "See you next week."),
            ("patient", "Thanks."),
            ("clinician", "Good morning, take a seat."),
            ("patient", "My wrist hurts."),
        ),
        3,
    ),
    "a closing with no cued content before it": (
        (
            ("clinician", "See you next week."),
            ("clinician", "Good morning, take a seat."),
            ("patient", "My wrist hurts."),
        ),
        None,
    ),
    "closing and greeting in one line": (
        (
            _CUED,
            ("clinician", "See you next week. Good morning, take a seat."),
            ("patient", "My wrist hurts."),
        ),
        2,
    ),
    "the closing four lines before the greeting": (
        (
            _CUED,
            ("clinician", "See you next week."),
            ("patient", "Thanks."),
            ("clinician", "Fine."),
            ("patient", "Okay."),
            ("clinician", "Good morning, take a seat."),
        ),
        None,
    ),
}
# D14's two gaps (D15's loosening (2)): an unlisted closing before a listed
# greeting, and a listed closing before an unlisted greeting — the product's
# rule finds no boundary in either, so a next patient after it is R3.
_GAP_CASES = {
    "closing gap": (
        _CUED,
        ("clinician", "Right, all done for today."),
        ("clinician", "Good morning, take a seat."),
        ("patient", "My wrist hurts."),
    ),
    "greeting gap": (
        _CUED,
        ("clinician", "See you next week."),
        ("clinician", "Come through, grab a chair."),
        ("patient", "My wrist hurts."),
    ),
}
_BOUNDARY_CASES.update({case: (lines, None) for case, lines in _GAP_CASES.items()})


class _QuoteAll:
    """A note provider quoting every utterance the request carries (the
    boundary's withheld lines are not in it)."""

    provider_name = "quote-all"

    def generate_sections(self, request: NoteRequest) -> tuple[GeneratedSection, ...]:
        assertions = [
            assertion
            for utterance in request.transcript_utterances
            if (
                assertion := whole_utterance_assertion(
                    f"q{utterance.segment_index:04d}",
                    "presenting_complaint",
                    segment_index=utterance.segment_index,
                    speaker=utterance.speaker,
                    words=utterance.transcript_words,
                )
            )
            is not None
        ]
        if not assertions:
            return ()
        return (
            GeneratedSection(section_key="presenting_complaint", note_assertions=tuple(assertions)),
        )


def _reading_inputs(tmp_path: Path) -> HarnessInputs:
    """The shipped pipeline's inputs with no speech model (the reference
    reading transcribes nothing) and a provider that quotes everything."""
    return HarnessInputs(
        provider=typing.cast(Any, None),
        frame_probability=typing.cast(Any, None),
        config=_pipeline_config(tmp_path),
        note_provider_factory=lambda config: _QuoteAll(),
    )


class TestReferenceReading:
    """D8 and D14: the same pipeline over the script's own words — the facts
    it gets right (R1) and the product's boundary rule on those words (R3) —
    with the script's reference tail start."""

    @pytest.mark.parametrize("case", sorted(_BOUNDARY_CASES))
    def test_the_boundary_is_the_products_rule_on_the_scripts_words(
        self, tmp_path: Path, case: str
    ) -> None:
        lines, boundary = _BOUNDARY_CASES[case]
        script = _script(*lines)
        reading = reference_reading(script, _reading_inputs(tmp_path), _NOW)
        assert (reading.boundary, reading.tail_start) == (boundary, None)

    def test_a_fact_the_pipeline_gets_right_on_the_scripts_words(self, tmp_path: Path) -> None:
        lines, _boundary = _BOUNDARY_CASES["closing two lines before the greeting"]
        script = _script(*lines, facts=[_fact("laterality", "left knee", 0)])
        reading = reference_reading(script, _reading_inputs(tmp_path), _NOW)
        assert reading.facts_right == frozenset({0})

    def test_the_tail_start_comes_from_the_table(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(validation, "REFERENCE_TAIL_STARTS", {"syn-test": 3})
        lines, _boundary = _BOUNDARY_CASES["closing two lines before the greeting"]
        script = _script(*lines, axes=("end_and_new_patient",))
        # One set of inputs: ``_pipeline_config`` creates its folder once.
        inputs = _reading_inputs(tmp_path)
        reading = reference_reading(script, inputs, _NOW)
        assert (reading.boundary, reading.tail_start, reading.next_patient_axis) == (3, 3, True)
        assert validation.reference_tail_start(_script(*lines)) is None
        no_axis = reference_reading(_script(*lines), inputs, _NOW)
        assert no_axis.next_patient_axis is False

    @pytest.mark.parametrize("case", sorted(_GAP_CASES))
    def test_a_gap_on_the_scripts_words_makes_the_next_patient_r3(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
    ) -> None:
        """End to end (D14): the reference reading of a closing-gap or a
        greeting-gap script finds no boundary, and the next patient's
        material ``absent`` fact, quoted with no measured boundary, is R3."""
        monkeypatch.setattr(validation, "REFERENCE_TAIL_STARTS", {"syn-test": 3})
        script = _script(
            *_GAP_CASES[case],
            facts=[_fact("absent", "wrist", 3)],
            axes=("end_and_new_patient",),
        )
        reading = reference_reading(script, _reading_inputs(tmp_path), _NOW)
        assert (reading.boundary, reading.tail_start) == (None, 3)
        document = validation.reference_document(script)
        note = _note(document, 0, 1, 2, 3, clinician=validation.CLINICIAN_LABEL)
        fact = _only_fact(encounter_metrics(document, note, script, reference=reading))
        assert (fact.verdict, fact.residue_r3) == ("wrongly_present", True)

    def test_an_axis_script_with_no_row_is_a_harness_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(validation, "REFERENCE_TAIL_STARTS", {})
        lines, _boundary = _BOUNDARY_CASES["closing two lines before the greeting"]
        script = _script(*lines, axes=("end_and_new_patient",))
        with pytest.raises(validation.ResidueTableError):
            validation.reference_tail_start(script)
        with pytest.raises(validation.ResidueTableError):
            reference_reading(script, _reading_inputs(tmp_path), _NOW)

    def test_every_tail_row_is_an_index_or_none(self) -> None:
        for encounter_id, start in validation.REFERENCE_TAIL_STARTS.items():
            assert validation._ENCOUNTER_ID_RE.fullmatch(encounter_id)
            assert start is None or (isinstance(start, int) and start >= 0)


# ---------------------------------------------------------------------------
# validation-run6 plan D8, D15, D17: rule v2 (schema 2) and the set layer
# ---------------------------------------------------------------------------

_RULE_V2 = PassRule.model_validate(
    {
        "schema_version": 2,
        "rule_name": "rule-v2-test",
        "sets": {
            "gate": {"gate": True, "max_r1_facts": 1, "max_r2_facts": 1, "max_r3_encounters": 1},
            "reported": {
                "gate": False,
                "max_r1_facts": 1,
                "max_r3_encounters": 1,
                "require_uncertainty_surfaced": False,
            },
        },
    }
)


def _residue_fact(fact_index: int = 0, **overrides: Any) -> FactOutcome:
    values: dict[str, Any] = {
        "fact_index": fact_index,
        "kind": "present",
        "material": True,
        "verdict": "correct",
        "warned": False,
        "uncertainty_surfaced": None,
        "not_transcribed": False,
        "ambiguous": False,
    }
    values.update(overrides)
    return FactOutcome(**values)


def _residue_outcome(
    encounter_id: str,
    *facts: FactOutcome,
    unsupported: int = 0,
    excused: tuple[tuple[int, int], ...] = (),
) -> EncounterOutcome:
    """One measured encounter holding ``facts``, with ``unsupported``
    unsupported clinical lines among four transcript lines, ``excused`` of
    them by R1 (validation-run7 plan D4)."""
    metrics = EncounterMetrics(
        words=WordErrors(1, 1, 0),
        spelling_normalised_words=0,
        transcript_lines=4,
        config_lines=0,
        unsupported_clinical_lines=unsupported,
        other_unsupported_words=0,
        checker_tally=(),
        checker_failures=(),
        checker_failure_count=0,
        expected_warnings_absent=(),
        facts=facts,
        unsupported_lines_excused_by_r1=excused,
    )
    return EncounterOutcome(
        encounter_id, "measured", segment_count=1, words=metrics.words, metrics=metrics
    )


# One member of each class, as one encounter holds it.
_CLASS_MEMBER: dict[str, FactOutcome] = {
    "R1": _residue_fact(verdict="wrong", residue_r1=True),
    "R2": _residue_fact(uncertainty_surfaced=False, residue_r2=True),
    "R3": _residue_fact(kind="absent", verdict="wrongly_present", residue_r3=True),
}


class TestRuleV2:
    def test_the_repository_rule_v2_file(self) -> None:
        """Decision 0.7 as amended 2026-10-24 (D14, D15, D17): option (a)'s
        top-level fields and four literal set rows."""
        path = validation.REPO_ROOT / "validation" / "rules" / "rule-v2.json"
        rule = validation.load_pass_rule(path)
        assert rule == PassRule.model_validate(
            {
                "schema_version": 2,
                "rule_name": "rule-v2",
                "sets": {
                    "scripts": {
                        "gate": True,
                        "max_r1_facts": 2,
                        "max_r2_facts": 2,
                        "max_r3_encounters": 2,
                    },
                    "heldout": {
                        "gate": False,
                        "max_r1_facts": 1,
                        "max_r2_facts": 1,
                        "max_r3_encounters": 1,
                    },
                    "heldout-2": {
                        "gate": False,
                        "max_r1_facts": 1,
                        "max_r2_facts": 1,
                        "max_r3_encounters": 1,
                    },
                    "heldout-3": {
                        "gate": True,
                        "max_r1_facts": 1,
                        "max_r3_encounters": 1,
                        "require_uncertainty_surfaced": False,
                    },
                },
            }
        )
        assert (rule.max_material_wrong, rule.max_silent_omissions) == (0, 0)
        assert rule.require_uncertainty_surfaced is True
        assert rule.max_word_error_rate is None
        # Unchanged by rule v3 (validation-run7 C2): still schema 2, no
        # exemption field; the newest schema is rule v3's (``TestRuleV3``).
        assert (rule.schema_version, rule.unsupported_line_r1_exemption) == (2, None)

    @pytest.mark.parametrize(
        ("payload", "message"),
        [
            (
                {"schema_version": 1, "sets": {"a": {"gate": True, "max_r1_facts": 0,
                                                     "max_r2_facts": 0,
                                                     "max_r3_encounters": 0}}},
                "a schema-1 rule holds no set ceilings",
            ),
            ({"schema_version": 1, "max_r1_facts": 1}, "Extra inputs are not permitted"),
            ({"schema_version": 2}, "a schema-2 rule names at least one set"),
            ({"schema_version": 2, "sets": {}}, "a schema-2 rule names at least one set"),
            (
                {"schema_version": 2, "sets": {"a": {"max_r1_facts": 0, "max_r2_facts": 0,
                                                     "max_r3_encounters": 0}}},
                "gate",
            ),
            (
                {"schema_version": 2, "sets": {"a": {"gate": True, "max_r1_facts": 0,
                                                     "max_r3_encounters": 0}}},
                "needs max_r2_facts",
            ),
            (
                {"schema_version": 2, "sets": {"a": {"gate": True, "max_r1_facts": 0,
                                                     "max_r2_facts": 0, "max_r3_encounters": 0,
                                                     "require_uncertainty_surfaced": False}}},
                "takes no max_r2_facts",
            ),
            (
                {"schema_version": 2, "sets": {"Held Out": {"gate": True, "max_r1_facts": 0,
                                                            "max_r2_facts": 0,
                                                            "max_r3_encounters": 0}}},
                "set names must match",
            ),
            (
                {"schema_version": 2, "sets": {"a": {"gate": True, "max_r1_facts": -1,
                                                     "max_r2_facts": 0,
                                                     "max_r3_encounters": 0}}},
                "greater than or equal to 0",
            ),
            (
                {"schema_version": 2, "sets": {"a": {"gate": True, "max_r1_facts": 0,
                                                     "max_r2_facts": 0, "max_r3_encounters": 0,
                                                     "max_r4_facts": 0}}},
                "Extra inputs are not permitted",
            ),
            ({"schema_version": 4}, "schema_version"),
            # Validation-run7 D4: the exemption is required at schema 3 and
            # refused at schemas 1 and 2.
            (
                {"schema_version": 1, "unsupported_line_r1_exemption": False},
                "only a schema-3 rule takes unsupported_line_r1_exemption",
            ),
            (
                {"schema_version": 2, "unsupported_line_r1_exemption": True,
                 "sets": {"a": {"gate": True, "max_r1_facts": 0, "max_r2_facts": 0,
                                "max_r3_encounters": 0}}},
                "only a schema-3 rule takes unsupported_line_r1_exemption",
            ),
            (
                {"schema_version": 3, "sets": {"a": {"gate": True, "max_r1_facts": 0,
                                                     "max_r2_facts": 0,
                                                     "max_r3_encounters": 0}}},
                "a schema-3 rule needs unsupported_line_r1_exemption",
            ),
            (
                {"schema_version": 3, "unsupported_line_r1_exemption": None,
                 "sets": {"a": {"gate": True, "max_r1_facts": 0, "max_r2_facts": 0,
                                "max_r3_encounters": 0}}},
                "a schema-3 rule needs unsupported_line_r1_exemption",
            ),
            (
                {"schema_version": 3, "unsupported_line_r1_exemption": True},
                "a schema-3 rule names at least one set",
            ),
            (
                {"schema_version": 3, "unsupported_line_r1_exemption": "sometimes",
                 "sets": {"a": {"gate": True, "max_r1_facts": 0, "max_r2_facts": 0,
                                "max_r3_encounters": 0}}},
                "unsupported_line_r1_exemption",
            ),
        ],
    )
    def test_a_malformed_rule_is_refused(self, payload: dict[str, Any], message: str) -> None:
        with pytest.raises(ValueError, match=message):
            PassRule.model_validate({"rule_name": "test-rule", **payload})

    def test_the_rule_uncertainty_field_is_the_default_a_set_overrides(self) -> None:
        """D17: a set row's ``require_uncertainty_surfaced`` overrides the
        rule's; absent, the rule's holds. Both ways, on one outcome whose
        uncertainty is missed and no R2."""
        missed = _residue_outcome("syn-a", _residue_fact(uncertainty_surfaced=False))
        assert rule_failures(_RULE_V2, missed, set_name="gate") == ("uncertainty_not_surfaced",)
        assert rule_failures(_RULE_V2, missed, set_name="reported") == ()
        relaxed = PassRule.model_validate(
            {
                "schema_version": 2,
                "rule_name": "relaxed",
                "require_uncertainty_surfaced": False,
                "sets": {
                    "inherits": {"gate": True, "max_r1_facts": 0, "max_r3_encounters": 0},
                    "requires": {
                        "gate": True,
                        "max_r1_facts": 0,
                        "max_r2_facts": 0,
                        "max_r3_encounters": 0,
                        "require_uncertainty_surfaced": True,
                    },
                },
            }
        )
        assert rule_failures(relaxed, missed, set_name="inherits") == ()
        assert rule_failures(relaxed, missed, set_name="requires") == (
            "uncertainty_not_surfaced",
        )
        # Rule v1's verdict reads the top-level field alone.
        assert v1_failures(_RULE_V2, missed) == ("uncertainty_not_surfaced",)
        assert v1_failures(relaxed, missed) == ()

    def test_the_set_must_be_one_the_rule_names(self) -> None:
        outcome = _residue_outcome("syn-a", _residue_fact())
        with pytest.raises(RuleError) as info:
            rule_failures(_RULE_V2, outcome, set_name="Margaret")
        assert str(info.value) == "the set must be one the rule names: gate, reported"
        with pytest.raises(RuleError):
            rule_failures(_RULE_V2, outcome)
        with pytest.raises(RuleError, match="a schema-1 rule has no sets"):
            rule_failures(OPTION_A, outcome, set_name="gate")
        with pytest.raises(RuleError):
            class_counts(OPTION_A, [outcome], "gate")

    @pytest.mark.parametrize("residue_class", ["R1", "R2", "R3"])
    @pytest.mark.parametrize(("encounters", "within"), [(1, True), (2, False)])
    def test_each_class_ceiling_at_n_and_n_plus_1(
        self, residue_class: str, encounters: int, within: bool
    ) -> None:
        """The gate set's ceilings are 1: one member passes, two fail at the
        set level, while every encounter passes on its own (each class
        clears its own failure)."""
        member = _CLASS_MEMBER[residue_class]
        outcomes = [_residue_outcome(f"syn-{n}", member) for n in range(encounters)]
        assert all(rule_failures(_RULE_V2, o, set_name="gate") == () for o in outcomes)
        counts = {c.residue_class: c for c in class_counts(_RULE_V2, outcomes, "gate")}
        assert (counts[residue_class].total, counts[residue_class].ceiling) == (encounters, 1)
        assert counts[residue_class].within is within
        breaches = class_breaches(_RULE_V2, outcomes, "gate")
        assert [c.residue_class for c in breaches] == ([] if within else [residue_class])
        assert run_passed(_RULE_V2, outcomes, set_name="gate") is within
        # Rule v1 reads the raw counts: every member fails it.
        assert run_passed_v1(_RULE_V2, outcomes) is False

    def test_r3_counts_encounters_not_facts(self) -> None:
        two_facts = _residue_outcome("syn-a", _CLASS_MEMBER["R3"], _residue_fact(
            1, kind="absent", verdict="wrongly_present", residue_r3=True
        ))
        counts = {c.residue_class: c for c in class_counts(_RULE_V2, [two_facts], "gate")}
        assert (counts["R3"].total, counts["R3"].members) == (1, (("syn-a", None),))
        assert run_passed(_RULE_V2, [two_facts], set_name="gate")

    def test_r2_has_no_ceiling_where_uncertainty_is_only_reported(self) -> None:
        outcomes = [_residue_outcome(f"syn-{n}", _CLASS_MEMBER["R2"]) for n in range(3)]
        counts = {c.residue_class: c for c in class_counts(_RULE_V2, outcomes, "reported")}
        assert (counts["R2"].total, counts["R2"].ceiling, counts["R2"].within) == (3, None, True)
        assert run_passed(_RULE_V2, outcomes, set_name="reported")

    def test_a_class_never_clears_another_classes_failure(self) -> None:
        """R1 clears wrong and silent, R2 unsurfaced, R3 wrong — and nothing
        else: an R2 fact omitted silently still fails."""
        r2_silent = _residue_outcome(
            "syn-a",
            _residue_fact(verdict="omitted", uncertainty_surfaced=False, residue_r2=True),
        )
        assert rule_failures(_RULE_V2, r2_silent, set_name="gate") == ("silent_omission",)
        r1_missed = _residue_outcome(
            "syn-b",
            _residue_fact(verdict="wrong", uncertainty_surfaced=False, residue_r1=True),
        )
        assert rule_failures(_RULE_V2, r1_missed, set_name="gate") == (
            "uncertainty_not_surfaced",
        )

    @pytest.mark.parametrize(
        "overrides",
        [
            {"residue_r1": True},
            {"residue_r1": True, "material": False, "verdict": "wrong"},
            {"residue_r2": True, "uncertainty_surfaced": None},
            {"residue_r2": True, "uncertainty_surfaced": True},
            {"residue_r3": True, "kind": "absent", "verdict": "correctly_absent"},
            {"residue_r3": True, "verdict": "wrong"},
        ],
    )
    def test_a_class_only_ever_names_a_failing_fact(self, overrides: dict[str, Any]) -> None:
        with pytest.raises(ValueError, match="names a"):
            _residue_fact(**overrides)

    def test_the_same_outcomes_fail_rule_v1_and_pass_rule_v2(self) -> None:
        """Through the metrics (an R1 mishearing): rule v1's verdict and the
        raw counts are unchanged; rule v2 excuses the one class member."""
        script = _script(
            ("clinician", "the ankle is swollen"), facts=[_fact("present", "ankle", 0)]
        )
        document = _doc((SPEAKER_1, "the angle is swollen"))
        note = _note(document, 0, warnings=[_warning("low_confidence_source", 0, 1, 1)])
        metrics = encounter_metrics(document, note, script, reference=_RIGHT_ON_REFERENCE)
        outcome = _measured(metrics)
        assert metrics.material_wrong == 1
        assert v1_failures(_RULE_V2, outcome) == ("material_wrong",)
        assert rule_failures(_RULE_V2, outcome, set_name="gate") == ()
        assert run_passed_v1(_RULE_V2, [outcome]) is False
        assert run_passed(_RULE_V2, [outcome], set_name="gate") is True
        assert rule_failures(OPTION_A, outcome) == ("material_wrong",)


# ---------------------------------------------------------------------------
# validation-run7 plan D4: rule v3 (schema 3) and the R1 exemption
# ---------------------------------------------------------------------------

_RULES = validation.REPO_ROOT / "validation" / "rules"
# ``_RULE_V2``'s sets under schema 3, the exemption on.
_RULE_V3 = PassRule.model_validate(
    {
        **_RULE_V2.model_dump(exclude={"unsupported_line_r1_exemption"}),
        "schema_version": 3,
        "rule_name": "rule-v3-test",
        "unsupported_line_r1_exemption": True,
    }
)


_SILENT = _residue_fact(verdict="omitted")  # material, unwarned, no class
_WRONG = _residue_fact(verdict="wrong")  # material, no class
# Run 6's verdicts under rule v2 (``docs/testing/validation-harness.md``,
# "Runs of record"), on FIXED synthetic outcomes of the same shape — run 6's
# own outcomes are not in the repository: the 50 within every ceiling (R1 2,
# R2 1, R3 2) and nothing else failing; ``heldout`` two unclassed wrong
# facts and R2 4 over 1; ``heldout-2`` silent facts and R2 2 over 1;
# ``heldout-3`` an R1 fact on an unsupported line (no exemption in rule v2)
# and R3 2 over 1.
_RUN6_SHAPES: dict[str, tuple[bool, list[EncounterOutcome]]] = {
    "scripts": (
        True,
        [
            _residue_outcome("syn-001", _CLASS_MEMBER["R1"]),
            _residue_outcome(
                "syn-002",
                _CLASS_MEMBER["R1"],
                _residue_fact(1, uncertainty_surfaced=False, residue_r2=True),
            ),
            _residue_outcome("syn-003", _CLASS_MEMBER["R3"]),
            _residue_outcome("syn-004", _CLASS_MEMBER["R3"]),
            _residue_outcome("syn-005", _residue_fact()),
        ],
    ),
    "heldout": (
        False,
        [
            _residue_outcome("hld-001", _WRONG),
            _residue_outcome(
                "hld-002",
                _WRONG,
                *[_residue_fact(n, uncertainty_surfaced=False, residue_r2=True) for n in (1, 2)],
            ),
            _residue_outcome(
                "hld-003",
                *[_residue_fact(n, uncertainty_surfaced=False, residue_r2=True) for n in (0, 1)],
            ),
        ],
    ),
    "heldout-2": (
        False,
        [
            _residue_outcome(
                "h2-001", _SILENT, _residue_fact(1, uncertainty_surfaced=False, residue_r2=True)
            ),
            _residue_outcome(
                "h2-002", _SILENT, _residue_fact(1, uncertainty_surfaced=False, residue_r2=True)
            ),
        ],
    ),
    "heldout-3": (
        False,
        [
            _residue_outcome("h3-001", _CLASS_MEMBER["R1"], unsupported=1),
            _residue_outcome("h3-002", _CLASS_MEMBER["R3"]),
            _residue_outcome("h3-003", _CLASS_MEMBER["R3"]),
        ],
    ),
}


class TestRuleV3:
    def test_the_repository_rule_v3_file(self) -> None:
        """D4 and D5: rule v2's top-level fields and four set rows (but
        ``heldout-3``'s ``gate``), a gate row for ``heldout-4`` no looser than
        ``heldout-3``'s, and the exemption on."""
        rule = validation.load_pass_rule(_RULES / "rule-v3.json")
        assert rule == PassRule.model_validate(
            {
                "schema_version": 3,
                "rule_name": "rule-v3",
                "unsupported_line_r1_exemption": True,
                "sets": {
                    "scripts": {
                        "gate": True,
                        "max_r1_facts": 2,
                        "max_r2_facts": 2,
                        "max_r3_encounters": 2,
                    },
                    "heldout": {
                        "gate": False,
                        "max_r1_facts": 1,
                        "max_r2_facts": 1,
                        "max_r3_encounters": 1,
                    },
                    "heldout-2": {
                        "gate": False,
                        "max_r1_facts": 1,
                        "max_r2_facts": 1,
                        "max_r3_encounters": 1,
                    },
                    "heldout-3": {
                        "gate": False,
                        "max_r1_facts": 1,
                        "max_r3_encounters": 1,
                        "require_uncertainty_surfaced": False,
                    },
                    "heldout-4": {
                        "gate": True,
                        "max_r1_facts": 1,
                        "max_r3_encounters": 1,
                        "require_uncertainty_surfaced": False,
                    },
                },
            }
        )
        sets = rule.sets or {}
        assert {name for name, row in sets.items() if row.gate} == {"scripts", "heldout-4"}
        assert {name for name, row in sets.items() if not row.gate} == {
            "heldout",
            "heldout-2",
            "heldout-3",
        }
        assert rule.exempts_r1_lines is True
        assert validation.RULE_SCHEMA_VERSION == 3

    def test_rule_v3s_seen_rows_are_rule_v2s_but_for_heldout_3s_gate(self) -> None:
        """D4 (peer rounds 1-2, PR-MED-002 and PR-MED-007): every field rule
        v3's verdict reads on the four seen sets equals rule v2's, so "rule v3
        without the R1 exemption" IS rule v2's verdict there."""
        v2 = validation.load_pass_rule(_RULES / "rule-v2.json")
        v3 = validation.load_pass_rule(_RULES / "rule-v3.json")
        for name in (
            "max_material_wrong",
            "max_silent_omissions",
            "require_uncertainty_surfaced",
            "max_word_error_rate",
        ):
            assert getattr(v3, name) == getattr(v2, name)
        v2_sets, v3_sets = v2.sets or {}, v3.sets or {}
        assert set(v3_sets) == set(v2_sets) | {"heldout-4"}
        for name, row in v2_sets.items():
            if name == "heldout-3":
                assert (row.gate, v3_sets[name].gate) == (True, False)
                assert v3_sets[name] == row.model_copy(update={"gate": False})
            else:
                assert v3_sets[name] == row
        # ``heldout-4``'s row is ``heldout-3``'s, gated.
        assert v3_sets["heldout-4"] == v2_sets["heldout-3"]

    def test_the_ratified_rule_v2_constant_is_the_file(self) -> None:
        assert validation.RULE_V2_RATIFIED == validation.load_pass_rule(_RULES / "rule-v2.json")

    def test_rule_v2s_counterpart(self) -> None:
        v3 = validation.load_pass_rule(_RULES / "rule-v3.json")
        for name in ("scripts", "heldout", "heldout-2", "heldout-3"):
            assert validation.rule_v2_counterpart(v3, name) == "same"
        assert validation.rule_v2_counterpart(v3, "heldout-4") == "no_row"
        looser = v3.model_copy(update={"max_material_wrong": 1})
        assert validation.rule_v2_counterpart(looser, "scripts") == "differs"
        # ``_RULE_V3``'s ``gate`` row is not one rule v2 names.
        assert validation.rule_v2_counterpart(_RULE_V3, "gate") == "no_row"
        assert validation.rule_v2_counterpart(_RULE_V3.model_copy(update={"sets": {
            "scripts": (_RULE_V3.sets or {})["gate"]}}), "scripts") == "differs"

    @pytest.mark.parametrize("set_name", sorted(_RUN6_SHAPES))
    def test_rule_v2_gives_run_6s_verdicts_on_fixed_outcomes(self, set_name: str) -> None:
        """Rule v2's file, unchanged (C2), gives run 6's verdict on each
        shape; rule v1 fails every one; and rule v3 without the exemption
        gives the same verdict as rule v2 on every seen set."""
        passed, outcomes = _RUN6_SHAPES[set_name]
        v2 = validation.load_pass_rule(_RULES / "rule-v2.json")
        v3 = validation.load_pass_rule(_RULES / "rule-v3.json")
        assert run_passed(v2, outcomes, set_name=set_name) is passed
        assert run_passed_v1(v2, outcomes) is False
        assert run_passed(v3.without_r1_exemption(), outcomes, set_name=set_name) is passed
        # No line is excused in these shapes, so the exemption moves nothing.
        assert run_passed(v3, outcomes, set_name=set_name) is passed

    def test_heldout_3s_shape_fails_rule_v2_on_the_line_and_the_set(self) -> None:
        _passed, outcomes = _RUN6_SHAPES["heldout-3"]
        v2 = validation.load_pass_rule(_RULES / "rule-v2.json")
        assert rule_failures(v2, outcomes[0], set_name="heldout-3") == (
            "unsupported_clinical_line",
        )
        assert [(c.residue_class, c.total) for c in class_breaches(v2, outcomes, "heldout-3")] == [
            ("R3", 2)
        ]

    @pytest.mark.parametrize(("excused", "v3_passes"), [((), False), (((2, 7),), True)])
    def test_the_exemption_reads_the_excused_lines_only(
        self, excused: tuple[tuple[int, int], ...], v3_passes: bool
    ) -> None:
        """An R1 fact on an unsupported line: rule v3 passes only when the
        line is excused; without the exemption, under rule v2 and under rule
        v1 it fails either way (the raw count is unchanged)."""
        outcome = _residue_outcome("syn-001", _CLASS_MEMBER["R1"], unsupported=1, excused=excused)
        assert outcome.metrics is not None
        assert outcome.metrics.unsupported_clinical_lines == 1
        assert rule_failures(_RULE_V3, outcome, set_name="gate") == (
            () if v3_passes else ("unsupported_clinical_line",)
        )
        assert rule_failures(_RULE_V3.without_r1_exemption(), outcome, set_name="gate") == (
            "unsupported_clinical_line",
        )
        assert rule_failures(_RULE_V2, outcome, set_name="gate") == ("unsupported_clinical_line",)
        assert v1_failures(_RULE_V3, outcome) == ("unsupported_clinical_line", "material_wrong")
        assert run_passed(_RULE_V3, [outcome], set_name="gate") is v3_passes

    def test_an_excused_line_beside_another_unsupported_line_still_fails(self) -> None:
        outcome = _residue_outcome("syn-001", _CLASS_MEMBER["R1"], unsupported=2, excused=((0, 0),))
        assert rule_failures(_RULE_V3, outcome, set_name="gate") == (
            "unsupported_clinical_line",
        )

    def test_without_the_exemption_is_the_field_off(self) -> None:
        plain = _RULE_V3.without_r1_exemption()
        assert (plain.schema_version, plain.unsupported_line_r1_exemption) == (3, False)
        assert plain.exempts_r1_lines is False
        assert plain.without_r1_exemption() is plain
        assert _RULE_V2.without_r1_exemption() is _RULE_V2
        assert _RULE_V2.exempts_r1_lines is False and OPTION_A.exempts_r1_lines is False


class TestR1Exemption:
    """D4's predicate, both ways, on hand-built alignments: a line is
    excused when EVERY flagged structured-claim word in it is (i) never an
    inserted word, (ii) aligned on every optimal alignment that flags it to
    a token of a material R1 fact's own statement, and (iii) itself under a
    review mark."""

    _DOSE = "paracetamol 500 mg twice a day"

    def _dose(
        self,
        transcript: str,
        *warnings: NoteWarning,
        reference: ReferenceReading | None = _RIGHT_ON_REFERENCE,
    ) -> EncounterMetrics:
        """ref [paracetamol, 500, mg, twice, a, day], the fact "paracetamol
        500 mg" (reference rows 0-2), the whole segment quoted."""
        script = _script(("clinician", self._DOSE), facts=[_fact("dose", "paracetamol 500 mg", 0)])
        document = _doc((SPEAKER_1, transcript))
        return encounter_metrics(
            document, _note(document, 0, warnings=warnings), script, reference=reference
        )

    def test_the_r1_facts_own_substitution_under_a_mark_is_excused(self) -> None:
        """hyp [... 50 ...]: one optimal alignment (cost 1), 500->50, "50"
        under a ``number_source`` mark — R1, and its line excused."""
        metrics = self._dose("paracetamol 50 mg twice a day", _warning("number_source", 0, 1, 1))
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.residue_r1) == ("wrong", True)
        assert (metrics.unsupported_clinical_lines, metrics.transcript_lines) == (1, 1)
        assert metrics.unsupported_lines_excused_by_r1 == ((0, 0),)
        assert (metrics.unsupported_lines_excused, metrics.unsupported_clinical_lines_v3) == (1, 0)
        outcome = _measured(metrics)
        assert rule_failures(_RULE_V3, outcome, set_name="gate") == ()
        assert rule_failures(_RULE_V2, outcome, set_name="gate") == ("unsupported_clinical_line",)
        assert v1_failures(_RULE_V3, outcome) == ("unsupported_clinical_line", "material_wrong")

    def test_without_a_reference_reading_nothing_is_excused(self) -> None:
        metrics = self._dose(
            "paracetamol 50 mg twice a day", _warning("number_source", 0, 1, 1), reference=None
        )
        assert _only_fact(metrics).residue_r1 is False
        assert (metrics.unsupported_clinical_lines, metrics.unsupported_lines_excused_by_r1) == (
            1,
            (),
        )

    def test_an_unmarked_misrendering_is_not_excused(self) -> None:
        """The mark on "paracetamol" alone: the fact is still R1 (an aligned
        word is marked), but "50" itself is not under a mark — (iii)."""
        metrics = self._dose(
            "paracetamol 50 mg twice a day", _warning("low_confidence_source", 0, 0, 0)
        )
        assert _only_fact(metrics).residue_r1 is True
        assert (metrics.unsupported_clinical_lines, metrics.unsupported_lines_excused_by_r1) == (
            1,
            (),
        )

    def test_a_mark_that_is_no_review_mark_excuses_nothing(self) -> None:
        metrics = self._dose(
            "paracetamol 50 mg twice a day",
            _warning("low_confidence_source", 0, 0, 0),
            _warning("high_risk_omission", 0, 1, 1),
        )
        # The predicate is reached: the line is unsupported and the fact R1.
        assert (metrics.unsupported_clinical_lines, _only_fact(metrics).residue_r1) == (1, True)
        assert metrics.unsupported_lines_excused_by_r1 == ()

    def test_an_inserted_number_is_not_excused(self) -> None:
        """ref [the, ankle, is, swollen], hyp [the, angle, is, 2, swollen]:
        one optimal alignment (cost 2) — ankle->angle (the R1 fact, marked)
        and "2" INSERTED, under a mark too — (i)."""
        script = _script(
            ("clinician", "the ankle is swollen"), facts=[_fact("present", "ankle", 0)]
        )
        document = _doc((SPEAKER_1, "the angle is 2 swollen"))
        note = _note(document, 0, warnings=[_warning("number_source", 0, 0, 4)])
        metrics = encounter_metrics(document, note, script, reference=_RIGHT_ON_REFERENCE)
        assert _only_fact(metrics).residue_r1 is True
        assert (metrics.unsupported_clinical_lines, metrics.unsupported_lines_excused_by_r1) == (
            1,
            (),
        )
        assert rule_failures(_RULE_V3, _measured(metrics), set_name="gate") == (
            "unsupported_clinical_line",
        )

    @pytest.mark.parametrize(("facts_right", "excused"), [({0}, ()), ({0, 1}, ((1, 1),))])
    def test_a_word_of_a_fact_that_is_not_r1_is_not_excused(
        self, facts_right: set[int], excused: tuple[tuple[int, int], ...]
    ) -> None:
        """Two quoted lines: line 1 (ordinal 0, segment 0) the marked
        ankle->angle, fact 0, R1; line 2 (ordinal 1, segment 1) the marked
        500->50 of fact 1, a material wrong fact that is R1 only when the
        reference reading gets it right — (ii) both ways, and the identity
        ``(1, 1)`` of the second line."""
        script = _script(
            ("clinician", "the ankle is swollen"),
            ("clinician", self._DOSE),
            facts=[_fact("present", "ankle", 0), _fact("dose", "paracetamol 500 mg", 1)],
        )
        document = _doc((SPEAKER_1, "the angle is swollen"), (SPEAKER_1, "paracetamol 50 mg"))
        note = _note(
            document,
            0,
            1,
            warnings=[
                _warning("low_confidence_source", 0, 1, 1),
                _warning("number_source", 1, 1, 1),
            ],
        )
        reading = ReferenceReading(frozenset(facts_right), boundary=None, tail_start=None)
        metrics = encounter_metrics(document, note, script, reference=reading)
        assert [f.residue_r1 for f in metrics.facts] == [True, 1 in facts_right]
        assert metrics.unsupported_clinical_lines == 1
        assert metrics.unsupported_lines_excused_by_r1 == excused

    @pytest.mark.parametrize(("fact_tokens", "excused"), [("500", ()), ("500 20", ((0, 0),))])
    def test_every_optimal_alignment_must_misrender_the_r1_facts_own_token(
        self, fact_tokens: str, excused: tuple[tuple[int, int], ...]
    ) -> None:
        """ref [take, 500, 20], hyp [take, 50]: two optimal alignments (cost
        2) — A 500->50 and 20 deleted, B 500 deleted and 20->50. With the
        fact "500" alone, B's edge comes from "20", outside the fact — not
        excused; with the fact "500 20" both edges lie inside it — excused.
        The fact is R1 either way."""
        script = _script(("clinician", "take 500 20"), facts=[_fact("dose", fact_tokens, 0)])
        document = _doc((SPEAKER_1, "take 50"))
        note = _note(document, 0, warnings=[_warning("number_source", 0, 1, 1)])
        metrics = encounter_metrics(document, note, script, reference=_RIGHT_ON_REFERENCE)
        assert _only_fact(metrics).residue_r1 is True
        assert metrics.unsupported_clinical_lines == 1
        assert metrics.unsupported_lines_excused_by_r1 == excused

    def test_one_other_flagged_structured_word_keeps_the_line_unexcused(self) -> None:
        """hyp [... day, left]: "50" would be excused, but "left" (a side) is
        inserted on the same line."""
        metrics = self._dose(
            "paracetamol 50 mg twice a day left", _warning("number_source", 0, 0, 6)
        )
        assert _only_fact(metrics).residue_r1 is True
        assert (metrics.unsupported_clinical_lines, metrics.unsupported_lines_excused_by_r1) == (
            1,
            (),
        )

    def test_a_flagged_word_that_is_no_structured_claim_does_not_block(self) -> None:
        """hyp [... a, dey]: "dey" for "day" is substituted, but it is no
        side, number, dose or negation — counted in ``other_unsupported_words``
        and outside the predicate, which reads structured-claim words only."""
        metrics = self._dose("paracetamol 50 mg twice a dey", _warning("number_source", 0, 0, 5))
        assert (metrics.other_unsupported_words, metrics.unsupported_clinical_lines) == (1, 1)
        assert metrics.unsupported_lines_excused_by_r1 == ((0, 0),)

    def test_a_supported_line_is_never_listed(self) -> None:
        """The R1 misrendering is no structured-claim word (ankle->angle):
        the line is supported, so nothing is excused."""
        script = _script(
            ("clinician", "the ankle is swollen"), facts=[_fact("present", "ankle", 0)]
        )
        document = _doc((SPEAKER_1, "the angle is swollen"))
        note = _note(document, 0, warnings=[_warning("low_confidence_source", 0, 1, 1)])
        metrics = encounter_metrics(document, note, script, reference=_RIGHT_ON_REFERENCE)
        assert (metrics.unsupported_clinical_lines, metrics.unsupported_lines_excused_by_r1) == (
            0,
            (),
        )


class TestExcusedLineIdentities:
    """``EncounterMetrics.unsupported_lines_excused_by_r1`` (D4, peer round
    1 PR-MED-003): ``(line ordinal, segment index)`` pairs, sorted, one per
    line, every ordinal among the transcript lines, never more than the
    unsupported lines — the count is the length."""

    def _metrics(self, excused: Any, *, lines: int = 3, unsupported: int = 2) -> EncounterMetrics:
        return EncounterMetrics(
            words=WordErrors(1, 1, 0),
            spelling_normalised_words=0,
            transcript_lines=lines,
            config_lines=0,
            unsupported_clinical_lines=unsupported,
            other_unsupported_words=0,
            checker_tally=(),
            checker_failures=(),
            checker_failure_count=0,
            expected_warnings_absent=(),
            facts=(),
            unsupported_lines_excused_by_r1=excused,
        )

    @pytest.mark.parametrize("excused", [(), ((0, 0),), ((0, 4), (2, 1))])
    def test_valid_identities_are_kept_and_counted(
        self, excused: tuple[tuple[int, int], ...]
    ) -> None:
        metrics = self._metrics(excused)
        assert metrics.unsupported_lines_excused_by_r1 == excused
        assert metrics.unsupported_lines_excused == len(excused)
        assert metrics.unsupported_clinical_lines_v3 == 2 - len(excused)

    def test_the_default_is_none_excused(self) -> None:
        metrics = EncounterMetrics(
            words=WordErrors(1, 1, 0),
            spelling_normalised_words=0,
            transcript_lines=1,
            config_lines=0,
            unsupported_clinical_lines=1,
            other_unsupported_words=0,
            checker_tally=(),
            checker_failures=(),
            checker_failure_count=0,
            expected_warnings_absent=(),
            facts=(),
        )
        assert (metrics.unsupported_lines_excused_by_r1, metrics.unsupported_lines_excused) == (
            (),
            0,
        )

    @pytest.mark.parametrize(
        ("excused", "message"),
        [
            (((2, 1), (0, 0)), "must be sorted, one per line"),
            (((1, 1), (1, 1)), "must be sorted, one per line"),
            (((1, 1), (1, 2)), "must be sorted, one per line"),
            (((3, 0),), "names a line the note lacks"),
            (((-1, 0),), "line must be a non-negative count"),
            (((0, -1),), "segment must be a non-negative count"),
            (((True, 0),), "line must be a non-negative count"),
            (((0,),), "must hold \\(line, segment\\) pairs"),
            ([(0, 0)], "must hold \\(line, segment\\) pairs"),
        ],
    )
    def test_malformed_identities_are_refused(self, excused: Any, message: str) -> None:
        with pytest.raises(ValueError, match=message):
            self._metrics(excused)

    def test_more_excused_than_unsupported_is_refused(self) -> None:
        with pytest.raises(ValueError, match="exceeds the unsupported lines"):
            self._metrics(((0, 0), (1, 1)), unsupported=1)
        assert self._metrics(((0, 0),), unsupported=1).unsupported_clinical_lines_v3 == 0


# ---------------------------------------------------------------------------
# Constraint 7: no output type can hold note or transcript text
# ---------------------------------------------------------------------------

SENTENCE = "the patient said her left knee hurts"
# Every str-bearing field of every result type, each validated at
# construction. A new str field fails the structural test until it is
# validated and listed here.
_VALIDATED_STR_FIELDS = {
    ("EncounterOutcome", "encounter_id"),
    ("EncounterOutcome", "status"),
    ("EncounterOutcome", "error_type"),
    ("FactOutcome", "kind"),
    ("FactOutcome", "verdict"),
    ("EncounterMetrics", "checker_tally"),
    ("EncounterMetrics", "checker_failures"),
    ("EncounterMetrics", "expected_warnings_absent"),
}
_RESULT_TYPES = (WordErrors, FactOutcome, EncounterMetrics, EncounterOutcome, ProseCounts)


class TestTextFreeTypes:
    def test_every_str_bearing_field_is_listed(self) -> None:
        found = set()
        for cls in _RESULT_TYPES:
            hints = typing.get_type_hints(cls, vars(validation))
            for field in dataclasses.fields(cls):
                rendered = str(hints[field.name])
                if "str" in rendered or "Literal" in rendered:
                    found.add((cls.__name__, field.name))
        assert found == _VALIDATED_STR_FIELDS

    def _metrics(self, **overrides: Any) -> EncounterMetrics:
        values: dict[str, Any] = {
            "words": WordErrors(1, 1, 0),
            "spelling_normalised_words": 0,
            "transcript_lines": 0,
            "config_lines": 0,
            "unsupported_clinical_lines": 0,
            "other_unsupported_words": 0,
            "checker_tally": (),
            "checker_failures": (),
            "checker_failure_count": 0,
            "expected_warnings_absent": (),
            "facts": (),
        }
        values.update(overrides)
        return EncounterMetrics(**values)

    def test_a_sentence_is_refused_in_every_listed_field(self) -> None:
        with pytest.raises(ValueError):
            EncounterOutcome(SENTENCE, "measured")
        with pytest.raises(ValueError):
            EncounterOutcome("syn-a", SENTENCE)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            EncounterOutcome("syn-a", "error", SENTENCE)
        fact = {
            "fact_index": 0,
            "kind": "present",
            "material": True,
            "verdict": "correct",
            "warned": False,
            "uncertainty_surfaced": None,
            "not_transcribed": False,
            "ambiguous": False,
        }
        for name in ("kind", "verdict"):
            with pytest.raises(ValueError):
                FactOutcome(**{**fact, name: SENTENCE})
        with pytest.raises(ValueError):
            self._metrics(checker_tally=((SENTENCE, 1),))
        with pytest.raises(ValueError):
            self._metrics(checker_failures=(SENTENCE,))
        with pytest.raises(ValueError):
            self._metrics(expected_warnings_absent=(SENTENCE,))

    def test_registered_codes_and_ids_are_accepted(self) -> None:
        self._metrics(checker_tally=(("high_risk_omission", 2),), checker_failures=())
        EncounterOutcome("syn-001", "error", "OSError")
