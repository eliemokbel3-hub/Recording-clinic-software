"""The validation-pass plan's frozen vocabulary (Task 0.8; C3, C6, C7).

Every list the plan freezes is pinned EXACTLY here, in one file, so a change
to any of them — a new dated decision with a repeated validation run — is a
change to this file too: the consultation phrases (moved unchanged from
``voice_commands`` into the leaf module ``consultation_phrases``, D1), the
boundary's look-back (D1), the self-correction markers (D4) and the spoken
hedges (D7). Near misses of the existing words are pinned at phrase level
here and through the live watcher in ``test_hands_free.py``."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from scribe_desktop import consultation_phrases, note, note_check, voice_commands
from scribe_desktop.consultation_phrases import (
    BOUNDARY_SEGMENTS,
    CLOSING_PHRASES,
    GREETING_PHRASES,
)
from scribe_desktop.note import CORRECTION_LEAD_IN, CORRECTION_MARKERS, content_tokens
from scribe_desktop.note_check import HEDGE_PHRASES
from scribe_desktop.voice_commands import phrase_tokens

_LEAF = Path(consultation_phrases.__file__)


def _occurrences(text: str, phrases: tuple[str, ...]) -> int:
    """How many times any of ``phrases`` occurs in ``text`` as whole tokens
    in a row, tokenised as the live watcher tokenises
    (``voice_commands.phrase_tokens``)."""
    tokens = phrase_tokens(text)
    count = 0
    for phrase in phrases:
        wanted = phrase_tokens(phrase)
        size = len(wanted)
        count += sum(
            1 for i in range(len(tokens) - size + 1) if tokens[i : i + size] == wanted
        )
    return count


class TestConsultationPhrases:
    def test_the_lists_are_pinned_exactly(self) -> None:
        """Moved unchanged from ``voice_commands`` (decision 0.2 (a))."""
        assert CLOSING_PHRASES == (
            "see you next week",
            "see you next time",
            "see you soon",
            "see you then",
            "take care",
            "all the best",
            "goodbye",
            "bye",
            "thanks for coming in",
            "thank you for coming in",
            "have a good day",
            "have a nice day",
            "have a great day",
            "have a good weekend",
        )
        assert GREETING_PHRASES == (
            "hello",
            "hi there",
            "good morning",
            "good afternoon",
            "good evening",
            "nice to meet you",
            "come on in",
            "take a seat",
            "have a seat",
            "what brings you in",
            "what brings you here",
            "how have you been",
        )
        assert len(CLOSING_PHRASES) == 14
        assert len(GREETING_PHRASES) == 12

    def test_the_boundary_look_back_is_pinned_apart_from_the_window_budget(self) -> None:
        assert BOUNDARY_SEGMENTS == 3
        assert voice_commands.NEW_CONSULTATION_WINDOWS == 3
        assert "BOUNDARY_SEGMENTS" not in vars(voice_commands)

    def test_the_watcher_reads_the_leaf_modules_lists(self) -> None:
        """C7: ONE list, re-exported — the same objects, not equal copies."""
        assert voice_commands.CLOSING_PHRASES is CLOSING_PHRASES
        assert voice_commands.GREETING_PHRASES is GREETING_PHRASES

    @pytest.mark.parametrize("phrases", [CLOSING_PHRASES, GREETING_PHRASES])
    def test_every_phrase_is_in_whole_word_form_and_unique(
        self, phrases: tuple[str, ...]
    ) -> None:
        assert all(" ".join(phrase_tokens(phrase)) == phrase for phrase in phrases)
        assert len(set(phrases)) == len(phrases)

    def test_d2s_vocabulary_exclusions_hold(self) -> None:
        """D2: no bare time-of-day word, no "welcome" and no "how are you
        going" — the rule a later dated amendment (the practitioner's own
        phrases) must keep, held here apart from the exact pins."""
        bare_times = {"morning", "afternoon", "evening", "night", "day"}
        assert set(GREETING_PHRASES) & bare_times == set()
        assert set(CLOSING_PHRASES) & bare_times == set()
        tokens = {
            token for phrase in (*CLOSING_PHRASES, *GREETING_PHRASES) for token in phrase.split()
        }
        assert "welcome" not in tokens
        assert _occurrences("how are you going", GREETING_PHRASES) == 0

    def test_no_phrase_is_both_a_closing_and_a_greeting(self) -> None:
        assert set(CLOSING_PHRASES) & set(GREETING_PHRASES) == set()

    def test_the_leaf_module_imports_only_note_and_transcription(self) -> None:
        """C6 / D1: the leaf may import ``note`` and ``transcription`` and
        nothing else of the package (today it needs neither)."""
        tree = ast.parse(_LEAF.read_text(encoding="utf-8"))
        package_imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            elif isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            else:
                continue
            package_imports += [n for n in names if n.split(".")[0] == "scribe_desktop"]
        assert set(package_imports) <= {"scribe_desktop.note", "scribe_desktop.transcription"}

    @pytest.mark.parametrize(
        "text",
        [
            "Morning stiffness",
            "hi-fi",
            "You're welcome",
            "how are you going with the exercises",
        ],
    )
    def test_near_misses_of_the_existing_words_match_no_phrase(self, text: str) -> None:
        assert _occurrences(text, GREETING_PHRASES) == 0
        assert _occurrences(text, CLOSING_PHRASES) == 0

    @pytest.mark.parametrize(
        "text, greetings, closings",
        [
            ("Good morning", 1, 0),
            ("Hi there, come on in", 2, 0),
            ("How have you been?", 1, 0),
            ("Thank you for coming in, bye", 0, 2),
        ],
    )
    def test_the_near_misses_twins_do_match(
        self, text: str, greetings: int, closings: int
    ) -> None:
        assert _occurrences(text, GREETING_PHRASES) == greetings
        assert _occurrences(text, CLOSING_PHRASES) == closings


class TestCorrectionMarkers:
    def test_the_markers_are_pinned_exactly(self) -> None:
        assert CORRECTION_MARKERS == ("actually", "i mean", "i meant", "correction")
        assert CORRECTION_LEAD_IN == "well"
        assert len(CORRECTION_MARKERS) == 4

    def test_every_marker_survives_content_tokens(self) -> None:
        """D4 reads CONTENT tokens: no marker or lead-in token is a filler
        ``content_tokens`` would drop, and each is already in its form."""
        for phrase in (*CORRECTION_MARKERS, CORRECTION_LEAD_IN):
            assert " ".join(content_tokens(phrase)) == phrase
            assert set(phrase.split()) & note._FILLER_TOKENS == set()

    def test_the_rejected_openers_are_not_markers(self) -> None:
        """D4's rejected alternatives stay out."""
        for rejected in ("sorry no", "no wait", "sorry", "wait", "no"):
            assert rejected not in CORRECTION_MARKERS


class TestHedgePhrases:
    def test_the_hedges_are_pinned_exactly(self) -> None:
        assert HEDGE_PHRASES == (
            "i think",
            "as far as i can tell",
            "probably",
            "maybe",
            "perhaps",
            "possibly",
            "likely",
            "unlikely",
            "seems",
            "seemed",
            "i guess",
            "i suppose",
            "i suspect",
            "i doubt",
            "uncertain",
            "to my knowledge",
        )
        assert len(HEDGE_PHRASES) == 16
        assert isinstance(HEDGE_PHRASES, tuple)

    def test_every_hedge_is_in_content_token_form_and_unique(self) -> None:
        assert all(" ".join(content_tokens(phrase)) == phrase for phrase in HEDGE_PHRASES)
        assert len(set(HEDGE_PHRASES)) == len(HEDGE_PHRASES)
        assert all("'" not in phrase and "’" not in phrase for phrase in HEDGE_PHRASES)

    def test_the_selection_rules_exclusions_hold(self) -> None:
        """Task 0.8's selection rule. (i) No hedge IS a modal verb — a fixed
        phrase that contains one ("as far as i can tell", Prince et al.'s
        plausibility shield) is not a modal verb and stays. (ii)-(iii) No
        hedge holds a frequency, sensation, quantity, degree, description or
        attribution word as any of its tokens."""
        modals = {"may", "might", "could", "would", "should", "can", "will", "shall", "must"}
        assert set(HEDGE_PHRASES) & modals == set()
        excluded_tokens = {
            "often", "sometimes", "usually", "generally", "frequently",
            "feel", "felt", "about", "around", "approximately", "some",
            "sort", "kind", "bit", "quite", "rather", "somewhat",
            "apparently", "presumably", "according",
            # Peer round 6 PR-MED-001: "unclear" describes speech or vision,
            # and "it's unclear" is impersonal, not the speaker's own certainty.
            "unclear",
        }
        tokens = {token for phrase in HEDGE_PHRASES for token in phrase.split()}
        assert tokens & excluded_tokens == set()
        assert [p for p in HEDGE_PHRASES if set(p.split()) & modals] == ["as far as i can tell"]

    def test_no_hedge_is_a_correction_marker_or_a_consultation_phrase(self) -> None:
        others = {*CORRECTION_MARKERS, *CLOSING_PHRASES, *GREETING_PHRASES}
        assert set(HEDGE_PHRASES) & others == set()

    def test_the_hedges_live_in_note_check(self) -> None:
        assert "HEDGE_PHRASES" in note_check.__all__
