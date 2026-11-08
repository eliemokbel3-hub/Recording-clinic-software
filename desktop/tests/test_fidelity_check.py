"""Note-learning-and-styles plan Task 4.2 (D6): Check 5, the prose fidelity
GATE, as a CLASS test.

The acceptance the task names: a missing fact, an added content token ("with
paralysis"), an added negation ("no neck pain"), a removed negation, an added
or changed number / medication / laterality token each FAIL; a faithful
rephrase passes. Beyond it: the rule ORDER (the first hit is the verdict),
the multiset rules (c) and (d) on their own (a moved or dropped second
negation, a changed count of a number that is still present, a side that is
still present but swapped in count), the contraction and typographic-
apostrophe folding, empty prose and prose over no inputs, the shared
classifiers (the same functions the learning filters use), the structural
pins (no polarity token is a connective; the warning code is registered as
review), and — pinned deliberately so the docstring cannot drift — the NAMED
RESIDUE: the rules see tokens, not attachment or order, and Check 5 is a
gate, not a certificate. Since the note-content-design plan's Task R.2: the
clinical register's fold (both ways, an interrupted input phrase, durations,
the multiplicity rules reached through it), the speaker frame (rule (b)
only, per section) and the first-person swap (R.0), each by keyword.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable

import pytest

from scribe_desktop import note_check as nc
from scribe_desktop.note import NOTE_WARNING_SEVERITY, NoteSectionKey
from scribe_desktop.note_check import (
    FIRST_PERSON_TOKENS,
    SPEAKER_FRAME_TOKENS,
    FidelityVerdict,
    fidelity_verdict,
    fidelity_verdicts,
    fidelity_warnings,
)
from scribe_desktop.note_config import CLINICAL_EQUIVALENTS, PROSE_CONNECTIVES

INPUTS = ("Patient reports neck pain for three days", "No radiation into the arm")
FAITHFUL = "The patient reports neck pain for three days, with no radiation into the arm."


def _failed(rule: str) -> FidelityVerdict:
    return FidelityVerdict(False, rule)  # type: ignore[arg-type]


class TestTheAcceptanceClass:
    def test_a_faithful_rephrase_passes(self) -> None:
        assert fidelity_verdict(INPUTS, FAITHFUL) == FidelityVerdict(True, None)

    def test_a_missing_fact_fails(self) -> None:
        prose = "The patient reports neck pain, with no radiation into the arm."
        assert fidelity_verdict(INPUTS, prose) == _failed("missing_fact")

    def test_an_added_content_token_fails(self) -> None:
        prose = (
            "The patient reports neck pain with paralysis for three days, with no "
            "radiation into the arm."
        )
        assert fidelity_verdict(INPUTS, prose) == _failed("added_content")

    def test_an_added_negation_fails(self) -> None:
        # "no" is a content token, never a connective: rule (b) refuses it
        # before rule (c) is reached.
        assert fidelity_verdict(("Neck pain on rotation",), "No neck pain on rotation") == (
            _failed("added_content")
        )

    def test_a_removed_negation_fails(self) -> None:
        assert fidelity_verdict(("No radiation into the arm",), "Radiation into the arm") == (
            _failed("missing_fact")
        )

    def test_an_added_number_fails(self) -> None:
        prose = "Neck pain for three days, 2 episodes"
        assert fidelity_verdict(("Neck pain for three days",), prose) == _failed("added_content")

    def test_a_changed_number_fails(self) -> None:
        assert fidelity_verdict(("Neck pain for three days",), "Neck pain for two days") == (
            _failed("missing_fact")
        )

    def test_an_added_medication_fails(self) -> None:
        prose = "Advised paracetamol and ibuprofen"
        assert fidelity_verdict(("Advised paracetamol",), prose) == _failed("added_content")

    def test_a_laterality_flip_fails(self) -> None:
        assert fidelity_verdict(("Left knee pain",), "Right knee pain") == _failed("missing_fact")

    def test_an_added_laterality_fails(self) -> None:
        assert fidelity_verdict(("Knee pain",), "Left knee pain") == _failed("added_content")


class TestTheMultisetRules:
    """Rules (c) and (d) on their own: every token is still PRESENT on both
    sides (rules (a) and (b) pass), and only the COUNT differs."""

    def test_a_dropped_second_negation_is_a_polarity_failure(self) -> None:
        inputs = ("Not tender", "Not swollen")
        assert fidelity_verdict(inputs, "Not tender, swollen") == _failed("polarity")

    def test_an_added_second_negation_is_a_polarity_failure(self) -> None:
        inputs = ("Not tender", "Swollen")
        assert fidelity_verdict(inputs, "Not tender and not swollen") == _failed("polarity")

    def test_a_dropped_contraction_is_a_polarity_failure(self) -> None:
        inputs = ("Doesn't wake at night", "Doesn't sit long")
        assert fidelity_verdict(inputs, "Doesn't wake at night and sit long") == (
            _failed("polarity")
        )

    def test_a_changed_number_count_is_a_protected_failure(self) -> None:
        inputs = ("Pain 3 out of 10", "Sleep 3 hours")
        assert fidelity_verdict(inputs, "Pain 3 out of 10, sleep 10 hours") == (
            _failed("protected")
        )

    def test_a_changed_side_count_is_a_protected_failure(self) -> None:
        inputs = ("Left knee pain", "Left hip stiffness", "Right shoulder")
        prose = "Right knee pain, left hip stiffness, right shoulder"
        assert fidelity_verdict(inputs, prose) == _failed("protected")

    def test_a_changed_medication_count_is_a_protected_failure(self) -> None:
        inputs = ("Continue paracetamol", "Paracetamol at night", "Stop ibuprofen")
        prose = "Continue paracetamol, ibuprofen at night, stop ibuprofen"
        assert fidelity_verdict(inputs, prose) == _failed("protected")

    def test_a_changed_date_is_a_missing_fact(self) -> None:
        # `at` is glue; `on` no longer is (Phase H round 24 MED-004, below).
        assert fidelity_verdict(("Review 12/03",), "Review at 12/03").passed
        assert fidelity_verdict(("Review 12/03",), "Review at 12/04") == _failed("missing_fact")


class TestTokenisationAndEdges:
    def test_case_and_edge_punctuation_are_not_facts(self) -> None:
        assert fidelity_verdict(("HVLA Cx performed.",), "hvla cx performed").passed

    def test_connective_verbs_are_admitted(self) -> None:
        prose = (
            "The patient reported and described neck pain for three days; no radiation "
            "into the arm was noted."
        )
        assert fidelity_verdict(INPUTS, prose).passed

    def test_an_input_connective_may_be_dropped_or_retensed(self) -> None:
        # Rule (a) requires every FACT-BEARING input token; a token on the
        # connective allow-list is glue on both sides (it may be added, so it
        # may be dropped or re-tensed). No polarity or protected token is a
        # connective (pinned below), so no fact leaves through this.
        inputs = ("Reports neck pain for three days",)
        assert fidelity_verdict(inputs, "Neck pain three days").passed
        assert fidelity_verdict(("Reports neck pain",), "Reported neck pain").passed

    def test_empty_prose_over_an_input_is_a_missing_fact(self) -> None:
        assert fidelity_verdict(("Neck pain",), "") == _failed("missing_fact")
        assert fidelity_verdict(("Neck pain",), "   ") == _failed("missing_fact")

    def test_prose_over_no_inputs_is_added_content(self) -> None:
        assert fidelity_verdict((), "Neck pain") == _failed("added_content")

    def test_connectives_alone_over_no_inputs_pass_vacuously(self) -> None:
        # Nothing stated, nothing fabricated: the prose stage never asks this
        # (a note section always has at least one line) — pinned so the
        # vacuous case is a known, not an accidental, outcome.
        assert fidelity_verdict((), "and the").passed

    def test_blank_prose_never_passes_even_over_blank_inputs(self) -> None:
        # Round 20 LOW-002: a line with no content token (punctuation only)
        # and an empty completion must not yield a "passed" rendering with
        # no prose — the schema refuses that shape, so the gate refuses it
        # first.
        assert fidelity_verdict(("...",), "") == _failed("missing_fact")
        assert fidelity_verdict((), "") == _failed("missing_fact")

    def test_a_typographic_apostrophe_is_the_same_polarity_marker(self) -> None:
        assert nc._polarity_mark("doesn’t") == "n't"
        assert nc._polarity_mark("doesn't") == "n't"
        assert nc._polarity_mark("nil") == "nil"
        assert nc._polarity_mark("denies") == "denies"
        assert nc._polarity_mark("knee") is None

    def test_a_repeated_input_token_may_be_stated_once(self) -> None:
        # Rule (a) is SET containment; "pain" twice in the inputs, once in
        # the prose. (Numbers, sides and medications are still counted by
        # rule (d).)
        inputs = ("Neck pain on rotation", "Neck pain on flexion")
        assert fidelity_verdict(inputs, "Neck pain on rotation and flexion").passed


class TestSharedClassifiers:
    @pytest.mark.parametrize(
        ("token", "expected"),
        [
            ("left", "laterality"),
            ("right", "laterality"),
            ("2026", "date"),
            ("12/03", "date"),
            ("march", "date"),
            ("three", "number"),
            ("3", "number"),
            ("paracetamol", "medication"),  # the checker's closed lexicon
            ("atorvastatin", "medication"),  # the learning filter's suffix rule
            ("mg", "medication"),  # a dose unit
            ("knee", None),
            ("spine", None),  # the filter's anatomical exemption holds here too
        ],
    )
    def test_protected_classes_are_the_filters_classes(
        self, token: str, expected: str | None
    ) -> None:
        assert nc._protected_class(token) == expected

    def test_the_connective_set_is_the_shipped_vocabulary(self) -> None:
        assert nc._PROSE_CONNECTIVE_SET == frozenset(PROSE_CONNECTIVES)
        assert len(PROSE_CONNECTIVES) >= 100

    def test_no_polarity_token_is_a_connective(self) -> None:
        # Structural pin: rule (b) must never admit a negation as glue.
        assert nc._POLARITY_TOKENS.isdisjoint(nc._PROSE_CONNECTIVE_SET)
        assert {"no", "not", "never", "denies", "without", "nil", "n't"} <= nc._POLARITY_TOKENS

    def test_no_polarity_bearing_word_is_a_connective(self) -> None:
        # Phase H round 24 MED-004: the antonym function words are facts.
        expected = {"on", "off", "before", "after", "over", "under", "since", "until", "in",
                    "out", "up", "down", "if",
                    # codex round 30 PR-MED-044: modals + temporals
                    "should", "shall", "will", "would",
                    "during", "while", "when", "within", "between"}
        assert nc._POLARITY_BEARING_TOKENS == frozenset(expected)
        assert nc._POLARITY_BEARING_TOKENS.isdisjoint(nc._PROSE_CONNECTIVE_SET)
        assert not expected & set(PROSE_CONNECTIVES)
        assert len(PROSE_CONNECTIVES) == 118

    def test_no_connective_is_a_clinical_abbreviation_folded(self) -> None:
        # Round 28 SEC-001: Check 5 compares FOLDED tokens, so a connective
        # equal to the lower-case form of a shipped abbreviation ("as" / "AS",
        # ankylosing spondylitis) would let a diagnosis drop or appear as
        # glue. The import-time guard in `note_config` is the control; this
        # pins it against the shipped files.
        from scribe_desktop.note_config import CLINICAL_ABBREVIATIONS

        folded = {entry.lower() for entry in CLINICAL_ABBREVIATIONS}
        assert folded.isdisjoint(nc._PROSE_CONNECTIVE_SET)
        assert "AS" in CLINICAL_ABBREVIATIONS and "as" not in PROSE_CONNECTIVES
        assert fidelity_verdict(("AS suspected",), "Suspected") == _failed("missing_fact")
        assert fidelity_verdict(("Suspected",), "AS suspected") == _failed("added_content")

    def test_the_warning_code_is_registered_as_review(self) -> None:
        assert NOTE_WARNING_SEVERITY["style_fallback"] == "review"


class TestPolarityBearingWords:
    """Phase H round 24 MED-004: on/off, before/after, over/under,
    since/until, in/out and `if` reverse a clinical meaning when swapped or
    dropped, so they left the connective allow-list. By rule ORDER the
    protection lands on (a) — the dropped or swapped-away word is a missing
    fact — before (c) is reached; an added one lands on (b). The named
    residue (tokens, not attachment) is pinned too: two such words swapped
    BETWEEN facts keep the set and pass."""

    @pytest.mark.parametrize(
        ("inputs", "prose"),
        [
            (("Off paracetamol",), "On paracetamol"),
            (("Pain before running",), "Pain after running"),
            (("Symptoms over 2 weeks",), "Symptoms under 2 weeks"),
            (("Neck pain since Tuesday",), "Neck pain until Tuesday"),
            (("Fracture ruled out",), "Fracture ruled in"),
            (("Refer if no improvement in 2 weeks",), "Refer, no improvement in 2 weeks"),
            (("Weight down 2 kg",), "Weight up 2 kg"),  # round 28 SEC-002
            # codex round 30 PR-MED-044: a modal dropped turns a
            # recommendation into history; a temporal dropped loses a condition
            (("Should have surgery",), "Has had surgery"),
            (("Will review if worse",), "Reviewed if worse"),
            (("Review when pain settles",), "Review pain settles"),
            (("Pain while walking",), "Pain walking"),
            (("Improve within 2 weeks",), "Improve 2 weeks"),
        ],
        ids=[
            "on-off", "before-after", "over-under", "since-until", "in-out", "if-dropped",
            "down-up", "should-dropped", "will-dropped", "when-dropped", "while-dropped",
            "within-dropped",
        ],
    )
    def test_a_swapped_or_dropped_word_is_a_missing_fact(
        self, inputs: tuple[str, ...], prose: str
    ) -> None:
        assert fidelity_verdict(inputs, prose) == _failed("missing_fact")

    @pytest.mark.parametrize(
        ("inputs", "prose"),
        [
            (("Paracetamol at night",), "On paracetamol at night"),
            # codex round 30 PR-MED-044: an interval or a modal INSERTED
            (("Pain before eating",), "Pain before and during eating"),
            (("Surgery",), "Should have surgery"),
            (("Review 2 weeks",), "Review within 2 weeks"),
            (("Symptoms exercise",), "Symptoms between exercise"),
        ],
        ids=["on-added", "during-added", "should-added", "within-added", "between-added"],
    )
    def test_an_added_word_is_added_content(
        self, inputs: tuple[str, ...], prose: str
    ) -> None:
        assert fidelity_verdict(inputs, prose) == _failed("added_content")

    def test_a_faithful_rephrase_keeping_them_passes(self) -> None:
        inputs = ("Off paracetamol since Tuesday",)
        assert fidelity_verdict(inputs, "Since Tuesday, off paracetamol.").passed

    def test_a_merge_of_two_lines_sharing_one_still_passes(self) -> None:
        # SET semantics, like every fact: the shared `on` stated once.
        inputs = ("Neck pain on rotation", "Neck pain on flexion")
        assert fidelity_verdict(inputs, "Neck pain on rotation and flexion").passed

    def test_two_words_swapped_between_facts_is_the_named_residue(self) -> None:
        inputs = ("Off paracetamol", "On ibuprofen")
        assert fidelity_verdict(inputs, "On paracetamol, off ibuprofen").passed


class TestFidelityWarnings:
    def test_one_warning_per_failing_section_in_canonical_order(self) -> None:
        inputs: dict[NoteSectionKey, tuple[str, ...]] = {
            "presenting_complaint": INPUTS,
            "assessment": ("Cervical HVLA performed",),
            "management_plan": ("Review 12/03",),
        }
        prose: dict[NoteSectionKey, str] = {
            "management_plan": "Review 12/04",  # fails; listed first to prove ordering
            "presenting_complaint": FAITHFUL,
            "assessment": "Cervical HVLA was performed with paralysis",  # fails
        }
        warnings = fidelity_warnings(inputs, prose)
        assert [w.section_key for w in warnings] == ["assessment", "management_plan"]
        assert {w.note_warning_code for w in warnings} == {"style_fallback"}
        assert {w.severity for w in warnings} == {"review"}
        assert all(w.assertion_id is None and w.source_coords is None for w in warnings)
        verdicts = fidelity_verdicts(inputs, prose)
        assert list(verdicts) == ["presenting_complaint", "assessment", "management_plan"]
        assert verdicts["presenting_complaint"].passed
        assert verdicts["assessment"].rule == "added_content"
        assert verdicts["management_plan"].rule == "missing_fact"

    def test_a_section_without_prose_is_not_judged(self) -> None:
        inputs: dict[NoteSectionKey, tuple[str, ...]] = {"assessment": ("Cervical HVLA",)}
        assert fidelity_warnings(inputs, {}) == ()
        assert fidelity_verdicts(inputs, {}) == {}

    def test_a_section_with_prose_and_no_inputs_fails(self) -> None:
        prose: dict[NoteSectionKey, str] = {"assessment": "Cervical HVLA performed"}
        warnings = fidelity_warnings({}, prose)
        assert [w.section_key for w in warnings] == ["assessment"]

    def test_all_passing_yields_no_warning(self) -> None:
        inputs: dict[NoteSectionKey, tuple[str, ...]] = {"presenting_complaint": INPUTS}
        assert fidelity_warnings(inputs, {"presenting_complaint": FAITHFUL}) == ()


class TestGateNotCertificate:
    """The NAMED residue, pinned: these all PASS. Each is a rephrase that
    keeps every token and every count — the rules see tokens, not
    attachment or order — and the practitioner's reading is the control."""

    def test_sides_swapped_between_two_anatomy_words_pass(self) -> None:
        inputs = ("Left knee pain", "Right hip stiffness")
        assert fidelity_verdict(inputs, "Right knee pain and left hip stiffness").passed

    def test_a_negation_moved_between_clauses_passes(self) -> None:
        inputs = ("No pain on rotation", "Stiffness on flexion")
        assert fidelity_verdict(inputs, "Pain on rotation, no stiffness on flexion").passed

    def test_two_numbers_traded_pass(self) -> None:
        inputs = ("3 sets of 5",)
        assert fidelity_verdict(inputs, "5 sets of 3").passed

    def test_a_reversed_comparison_passes(self) -> None:
        inputs = ("Pain worse than stiffness",)
        assert fidelity_verdict(inputs, "Stiffness worse than pain").passed


# ---------------------------------------------------------------------------
# Note-content-design plan Task R.2 (D2; R.0 decided (a) 2026-11-08): the
# clinical register folds both sides before the four rules, which run
# unchanged; the speaker frame is admitted in rule (b) only, and under it the
# first person is glue in rule (a). Every new parameter is keyword-only with a
# default, so every call above (positional, no register, no frame) stands.
# ---------------------------------------------------------------------------


def _register(inputs: tuple[str, ...], prose: str, *, frame: bool = False) -> FidelityVerdict:
    return fidelity_verdict(inputs, prose, register=CLINICAL_EQUIVALENTS, speaker_frame=frame)


class TestTheRegisterFold:
    def test_a_term_for_its_phrase_passes_only_under_the_register(self) -> None:
        inputs = ("Lower back pain for three weeks",)
        assert _register(inputs, "LBP for 3/52").passed
        assert fidelity_verdict(inputs, "LBP for 3/52") == _failed("missing_fact")

    def test_a_phrase_for_its_term_passes_only_under_the_register(self) -> None:
        inputs = ("LBP for 3/52",)
        assert _register(inputs, "Lower back pain for three weeks").passed
        assert fidelity_verdict(inputs, "Lower back pain for three weeks") == (
            _failed("missing_fact")
        )

    def test_two_phrases_of_one_entry_are_one_fact(self) -> None:
        assert _register(("Low back pain",), "Lower back pain").passed
        assert _register(("Pain on both sides",), "Pain on B/L").passed
        assert _register(("Range of movement reduced",), "ROM reduced").passed

    def test_an_interrupted_input_phrase_meets_a_prose_term_as_a_set(self) -> None:
        # The fold expands a prose `LBP` to {lower, back, pain}, which the
        # spoken words hold as a set; a non-glue word between them (the
        # polarity-bearing `in`) must still appear in the prose.
        assert _register(("Pain across my lower back",), "Pt reports LBP", frame=True).passed
        assert _register(("Pain in my lower back",), "Pt reports LBP", frame=True) == (
            _failed("missing_fact")
        )
        assert _register(("Pain in my lower back",), "Pt reports LBP in", frame=True).passed

    def test_a_changed_duration_is_a_missing_fact(self) -> None:
        inputs = ("Pain for three weeks",)
        assert _register(inputs, "Pain for 2/52") == _failed("missing_fact")
        # Days are not an entry (weeks only): a prose 3/7 loses both tokens.
        assert _register(inputs, "Pain for 3/7") == _failed("missing_fact")

    def test_a_range_of_weeks_is_not_an_entry(self) -> None:
        # "two to three weeks" folds to two, to, 3, weeks; a prose 2-3/52 is
        # one unknown token, so `two` is missing.
        assert _register(("Pain for two to three weeks",), "Pain for 2-3/52") == (
            _failed("missing_fact")
        )

    def test_an_input_date_is_never_a_duration(self) -> None:
        assert _register(("Review 3/9",), "Review 3 weeks") == _failed("missing_fact")

    def test_a_duplicated_duration_reaches_the_protected_rule(self) -> None:
        # Every token present on both sides: only the count of `3` differs.
        assert _register(("Pain for three weeks",), "Pain for 3/52, 3/52") == (
            _failed("protected")
        )

    def test_a_duplicated_negation_reaches_the_polarity_rule(self) -> None:
        assert _register(("No LBP",), "No LBP, no") == _failed("polarity")

    def test_an_ordinary_word_is_never_folded_into_a_diagnosis(self) -> None:
        # D1: `AS` is not a register term (its folded form is `as`), so an
        # invented expansion over an everyday "as" is still added content.
        inputs = ("Symptoms as bad as before",)
        assert _register(inputs, "Ankylosing spondylitis symptoms as bad as before") == (
            _failed("added_content")
        )


class TestTheSpeakerFrame:
    def test_the_frame_passes_only_with_the_flag(self) -> None:
        inputs = ("Neck pain for two weeks",)
        for prose in ("Pt reports neck pain for 2/52", "The patient reports neck pain for 2/52"):
            assert _register(inputs, prose, frame=True).passed
            assert _register(inputs, prose) == _failed("added_content")

    def test_the_frame_needs_no_register(self) -> None:
        assert fidelity_verdict(("Neck pain",), "Pt reports neck pain", speaker_frame=True).passed

    def test_the_representative_line_passes_under_the_swap(self) -> None:
        inputs = ("I've had this pain in my lower back for about three weeks",)
        prose = "Pt reports pain in lower back for about 3/52"
        assert _register(inputs, prose, frame=True).passed
        assert _register(inputs, prose) == _failed("missing_fact")

    def test_a_spoken_patient_is_a_fact_the_frame_cannot_drop(self) -> None:
        inputs = ("I'm not a patient person",)
        assert _register(inputs, "Pt reports not a person", frame=True) == (
            _failed("missing_fact")
        )
        assert _register(inputs, "Pt reports not a patient person", frame=True).passed

    def test_a_spoken_pt_reused_as_the_frame_is_the_named_residue(self) -> None:
        # Token, not attachment: the folded `pt` is on both sides.
        inputs = ("PT twice a week",)
        assert _register(inputs, "Pt reports twice a week", frame=True).passed
        assert _register(inputs, "Reports twice a week", frame=True) == _failed("missing_fact")

    def test_pt_denies_over_no_is_a_missing_fact(self) -> None:
        # `no` is gone before rule (c) is reached.
        assert _register(("No locking",), "Pt denies locking", frame=True) == (
            _failed("missing_fact")
        )

    def test_equal_token_sets_with_a_different_negation_count_reach_polarity(self) -> None:
        inputs = ("No locking", "No LBP")
        assert _register(inputs, "Pt reports no locking or LBP", frame=True) == (
            _failed("polarity")
        )

    def test_the_swap_set_is_pinned_exactly(self) -> None:
        assert frozenset(
            {"i", "i've", "i'm", "me", "my", "mine", "we", "we've", "our"}
        ) == FIRST_PERSON_TOKENS
        assert frozenset({"pt", "patient"}) == SPEAKER_FRAME_TOKENS
        assert FIRST_PERSON_TOKENS.isdisjoint(nc._PROSE_CONNECTIVE_SET)
        assert SPEAKER_FRAME_TOKENS.isdisjoint(nc._PROSE_CONNECTIVE_SET)
        assert FIRST_PERSON_TOKENS.isdisjoint(nc._POLARITY_BEARING_TOKENS)

    @pytest.mark.parametrize("token", sorted(FIRST_PERSON_TOKENS))
    def test_each_first_person_token_is_droppable_under_the_flag_only(self, token: str) -> None:
        inputs = (f"{token} have neck pain",)
        assert _register(inputs, "Pt reports neck pain", frame=True).passed
        assert _register(inputs, "Pt reports neck pain") == _failed("missing_fact")

    @pytest.mark.parametrize("token", ["i'd", "i'll", "we'd", "we'll"])
    def test_a_modal_contraction_stays_a_fact_under_the_flag(self, token: str) -> None:
        # codex PR-MED-011: their would / will is polarity-bearing.
        assert token not in FIRST_PERSON_TOKENS
        inputs = (f"{token} book a review",)
        assert _register(inputs, "Pt reports book a review", frame=True) == (
            _failed("missing_fact")
        )
        assert _register(inputs, f"Pt reports {token} book a review", frame=True).passed

    def test_the_frame_never_adds_the_first_person(self) -> None:
        assert _register(("Neck pain",), "My neck pain", frame=True) == _failed("added_content")


class TestTheSectionArguments:
    INPUTS: dict[NoteSectionKey, tuple[str, ...]] = {
        "presenting_complaint": ("Neck pain for two weeks",),
        "assessment": ("Cervical stiffness",),
    }
    PROSE: dict[NoteSectionKey, str] = {
        "presenting_complaint": "Pt reports neck pain for 2/52",
        "assessment": "Pt reports Cx stiffness",
    }

    def test_the_frame_is_per_section_and_the_register_reaches_every_section(self) -> None:
        frame: dict[NoteSectionKey, bool] = {"presenting_complaint": True}
        verdicts = fidelity_verdicts(
            self.INPUTS, self.PROSE, register=CLINICAL_EQUIVALENTS, speaker_frame=frame
        )
        assert verdicts["presenting_complaint"].passed
        assert verdicts["assessment"] == _failed("added_content")
        warnings = fidelity_warnings(
            self.INPUTS, self.PROSE, register=CLINICAL_EQUIVALENTS, speaker_frame=frame
        )
        assert [w.section_key for w in warnings] == ["assessment"]

    def test_the_defaults_are_no_register_and_no_frame(self) -> None:
        verdicts = fidelity_verdicts(self.INPUTS, self.PROSE)
        assert verdicts["presenting_complaint"] == _failed("missing_fact")
        assert verdicts["assessment"] == _failed("missing_fact")
        assert len(fidelity_warnings(self.INPUTS, self.PROSE)) == 2

    @pytest.mark.parametrize("function", [fidelity_verdict, fidelity_verdicts, fidelity_warnings])
    def test_every_new_parameter_is_keyword_only_with_a_default(
        self, function: Callable[..., object]
    ) -> None:
        parameters = inspect.signature(function).parameters
        for name in ("register", "speaker_frame"):
            assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
        assert parameters["register"].default is None
