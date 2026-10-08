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

import dataclasses
import typing
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from scribe_desktop import validation
from scribe_desktop.note import (
    ConfirmationDecision,
    ExtractiveNoteProvider,
    GeneratedNote,
    GeneratedSection,
    NoteAssertion,
    NoteSpan,
    NoteWarning,
    SourceCoords,
    compose_draft,
    finalise_note,
    reconstruct_span_text,
    text_digest,
)
from scribe_desktop.note_check import omission_warnings, reconstruction_warnings
from scribe_desktop.note_config import AutofillRule, NoteConfig, load_note_config
from scribe_desktop.transcription import (
    SPEAKER_1,
    SPEAKER_2,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
)
from scribe_desktop.validation import (
    EncounterMetrics,
    EncounterOutcome,
    EncounterScript,
    FactOutcome,
    PassRule,
    ProseCounts,
    WordErrors,
    confirm_all,
    encounter_metrics,
    is_structured_claim_word,
    rule_failures,
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
) -> EncounterScript:
    """``lines`` are ``(role, text)`` in spoken order."""
    return EncounterScript.model_validate(
        {
            "schema_version": 1,
            "encounter_id": "syn-test",
            "appointment_type": "follow_up",
            "axes": ["negation"],
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
        transcribed'); no omission warning exists, so it is silent."""
        script = _script(
            ("clinician", "my left knee hurts"), facts=[_fact("laterality", "left knee", 0)]
        )
        document = _doc((SPEAKER_1, "my left knee hurts"))
        metrics = encounter_metrics(document, _checked(document), script)
        assert metrics.words == WordErrors(4, 4, 0)
        fact = _only_fact(metrics)
        assert (fact.verdict, fact.not_transcribed, fact.warned) == ("omitted", False, False)
        assert metrics.silent_omissions == 1
        assert metrics.checker_tally == ()


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
        """Segment 0 = [rest, the, knee, and, take, 2, tablets]; nothing is in
        the note. The real Check 4 warns on the uncovered "2" (word 5). The
        material fact [rest, the, knee] holds no high-risk word of its own,
        so the warning does not count for it: a silent omission. The fact
        [2, tablets] owns the warned word: a warned omission."""
        script = _script(
            ("clinician", "rest the knee and take 2 tablets"),
            facts=[_fact("present", "rest the knee", 0), _fact("dose", "2 tablets", 0)],
        )
        document = _doc((SPEAKER_1, "rest the knee and take 2 tablets"))
        note = _checked(document)
        assert [(w.note_warning_code, w.source_coords) for w in note.note_warnings] == [
            ("high_risk_omission", SourceCoords(0, 5, 5))
        ]
        metrics = encounter_metrics(document, note, script)
        rest, dose = metrics.facts
        assert (rest.verdict, rest.warned, rest.silent_omission) == ("omitted", False, True)
        assert (dose.verdict, dose.warned, dose.silent_omission) == ("omitted", True, False)
        assert (metrics.silent_omissions, metrics.warned_omissions) == (1, 1)

    def test_between_two_high_risk_words_is_still_silent_and_fails_option_a(self) -> None:
        """Segment 0 = [use, 2, cold, packs, over, the, sore, calf, 3, times]:
        Check 4's ONE warning spans words 1..8 (the two numbers). The fact
        [sore, calf] lies inside that interval but holds no high-risk word —
        an interval proves nothing (peer round 4): silent, and option (a)
        fails the encounter."""
        script = _script(
            ("clinician", "use 2 cold packs over the sore calf 3 times"),
            facts=[_fact("present", "sore calf", 0)],
        )
        document = _doc((SPEAKER_1, "use 2 cold packs over the sore calf 3 times"))
        note = _checked(document)
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
            ("low_confidence_source", SourceCoords(0, 1, 1))
        ]
        fact = _only_fact(encounter_metrics(document, note, self._script()))
        assert (fact.verdict, fact.uncertainty_surfaced) == ("correct", True)

    def test_a_warning_elsewhere_in_the_segment_does_not_surface_it(self) -> None:
        document = _doc((SPEAKER_1, "paracetamol 500 mg ?daily"))
        metrics = encounter_metrics(document, _checked(document, 0), self._script())
        assert _only_fact(metrics).uncertainty_surfaced is False
        assert metrics.uncertainty_missed == 1
        assert rule_failures(OPTION_A, _measured(metrics)) == ("uncertainty_not_surfaced",)

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
