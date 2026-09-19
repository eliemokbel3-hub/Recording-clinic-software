"""Note-learning-and-styles plan Phase 0 Task 0.4: the typed-wording filter.

``refuse_typed_wording`` is the SECOND, narrower admission filter (D11): for
practitioner-TYPED wording only, it shares the date / number / medication
classifiers with ``refuse_learning_candidate`` and runs no name heuristic.
Pinned as a class: what it accepts (the plan's "HVLA Cx"), what it refuses
(the plan's "paracetamol 500 mg" and "3/4/26" and one case per shared
classifier), that it agrees with the transcript filter wherever no name is
involved, and that a capitalised name passes it — the deliberate, consented
difference. Plus the D5 auto-confirm threshold constant.
"""

from __future__ import annotations

import pytest

from scribe_desktop.note_config import (
    LEARNED_RULE_AUTO_CONFIRM_AFTER,
    refuse_learning_candidate,
    refuse_typed_wording,
)


class TestRefuseTypedWording:
    @pytest.mark.parametrize(
        "text",
        [
            "HVLA Cx",
            "ROM limited",
            "Hx of LBP",
            "NAD on palpation",
            "Cx spine mobs",  # "spine" is the named -pine exemption
            "Gentle mobilisation Lx",
            "",
            "   ",
        ],
    )
    def test_accepts_clinical_shorthand(self, text: str) -> None:
        assert refuse_typed_wording(text) is None

    @pytest.mark.parametrize(
        ("text", "refusal"),
        [
            ("paracetamol 500 mg", "number"),  # the plan's case: the number is hit first
            ("3/4/26", "date"),  # the plan's case
            ("due 12-03", "date"),
            ("since 2024", "date"),
            ("review in May", "date"),
            ("Review in two weeks", "number"),
            ("500mg", "number"),
            ("mg", "medication"),
            ("atorvastatin", "medication"),
            ("amoxicillin course", "medication"),
        ],
    )
    def test_refuses_numbers_dates_and_medications(self, text: str, refusal: str) -> None:
        assert refuse_typed_wording(text) == refusal

    def test_no_name_heuristic_by_decision(self) -> None:
        """D11 (practitioner decision 2026-09-18): typed wording is the
        practitioner's own, so a capitalised word is NOT refused as a name —
        the same words ARE refused when they come from the transcript."""
        assert refuse_typed_wording("Margaret seen today") is None
        assert refuse_typed_wording("Dr Smith reviewed") is None
        assert refuse_learning_candidate(["Margaret", "seen", "today"], first_in_segment=False) == (
            "name"
        )

    @pytest.mark.parametrize(
        "text",
        ["3/4/26", "500 mg", "atorvastatin", "two weeks", "ice pack use", "gentle mobs", "mcg"],
    )
    def test_agrees_with_the_transcript_filter_where_no_name_is_involved(self, text: str) -> None:
        """The three classes are the SAME classifiers, not a re-implementation:
        over name-free text the two filters return the same verdict."""
        assert refuse_typed_wording(text) == refuse_learning_candidate(
            text.split(), first_in_segment=False
        )

    def test_the_first_class_hit_is_reported_in_a_fixed_order(self) -> None:
        assert refuse_typed_wording("500 mg on 12/03") == "date"
        assert refuse_typed_wording("500 mg") == "number"
        assert refuse_typed_wording("mg only") == "medication"


def test_the_auto_confirm_threshold_is_three() -> None:
    """D5: a learned rule's lines arrive pre-filled after exactly three
    unchanged confirmations."""
    assert LEARNED_RULE_AUTO_CONFIRM_AFTER == 3
