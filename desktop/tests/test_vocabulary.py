"""The validation-pass plan's frozen vocabulary (Task 0.8; C3, C6, C7).

Every list the plan freezes is pinned EXACTLY here, in one file, so a change
to any of them — a new dated decision with a repeated validation run — is a
change to this file too: the consultation phrases (moved unchanged from
``voice_commands`` into the leaf module ``consultation_phrases``, D1; widened
once, by validation-run7 Task 0.4 (c) on 2026-10-26), the
boundary's look-back (D1), the self-correction markers (D4) and the spoken
hedges (D7). Near misses of the existing words are pinned at phrase level
here and through the live watcher in ``test_hands_free.py``."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from scribe_desktop import consultation_phrases, note, note_check, validation, voice_commands
from scribe_desktop.consultation_phrases import (
    BOUNDARY_SEGMENTS,
    CLOSING_PHRASES,
    GREETING_PHRASES,
)
from scribe_desktop.note import CORRECTION_LEAD_IN, CORRECTION_MARKERS, content_tokens
from scribe_desktop.note_check import HEDGE_PHRASES
from scribe_desktop.validation import REFERENCE_HEDGES
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


# The lists the safeguards plan shipped on 2026-09-28, moved unchanged from
# ``voice_commands`` (decision 0.2 (a)) — frozen history, and each list's head.
_CLOSINGS_2026_09_28: tuple[str, ...] = (
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
_GREETINGS_2026_09_28: tuple[str, ...] = (
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
# Validation-run7 plan Task 0.4 (c) (2026-10-26, D2): the accepted widening,
# in proposal order, appended to each list.
_CLOSINGS_ADDED_RUN7_0_4: tuple[str, ...] = (
    "bye bye",
    "thank you",
    "is there anything else",
    "any other questions",
    "come back and see me",
    "i'll see you next week",
    "see you",
    "see you later",
    "nice talking to you",
    "bye for now",
    "see ya",
    "see ya later",
    "catch you later",
    "ta ta",
    "cheers mate",
    "look after yourself",
)
_GREETINGS_ADDED_RUN7_0_4: tuple[str, ...] = (
    "hi how are you",
    "what can i do for you",
    "what can i do for you today",
    "what brings you in today",
    "what's new",
    "how can i help",
    "how can i help you today",
    "how are you doing",
    "how's it going",
    "nice to see you",
    "good to see you",
    "nice to see you again",
    "pleased to meet you",
    "g'day mate",
)
# Each added phrase, a line holding it and a neighbouring line holding no
# phrase of either list (Task 0.4 (c), the 0.3.4 Task 0.9 shape).
_ADDED_PHRASE_CASES: list[tuple[str, str, str]] = [
    ("bye bye", "Okay, bye bye.", "Buy a brace and wear it."),
    ("thank you", "Thank you, that helps.", "Thanks, that helps."),
    ("is there anything else", "Is there anything else today?", "Is there any swelling?"),
    ("any other questions", "Any other questions for me?", "Any other pain at night?"),
    ("come back and see me", "Come back and see me in a month.", "Come back to lying down."),
    (
        "i'll see you next week",
        "Great, I'll see you next week.",
        "I'll send you the exercises next week.",
    ),
    ("see you", "Okay, see you.", "I can see your knee is swollen."),
    ("see you later", "See you later, then.", "We'll see, later on."),
    ("nice talking to you", "It was nice talking to you.", "Talking to you helps."),
    ("bye for now", "Bye for now.", "Stand by for now."),
    ("see ya", "See ya, mate.", "Say yeah if it hurts."),
    ("see ya later", "See ya later.", "See the GP later."),
    ("catch you later", "Catch you later.", "Catch your breath."),
    ("ta ta", "Ta ta, take it easy.", "Ta, that helps."),
    ("cheers mate", "Cheers mate, all good.", "Cheers, the brace fits."),
    ("look after yourself", "Look after yourself.", "Look after your knee."),
    ("hi how are you", "Hi, how are you?", "How are you sleeping?"),
    ("what can i do for you", "So, what can I do for you?", "What can I do for the pain?"),
    ("what can i do for you today", "What can I do for you today?", "What can I do today?"),
    ("what brings you in today", "What brings you in today?", "What brings the pain on today?"),
    ("what's new", "Hi, what's new?", "What's the new brace like?"),
    ("how can i help", "How can I help?", "How can I hold it?"),
    ("how can i help you today", "How can I help you today?", "How can you help me today?"),
    ("how are you doing", "How are you doing?", "How are you holding up?"),
    ("how's it going", "How's it going?", "How's it feeling?"),
    ("nice to see you", "Nice to see you.", "Nice to sit down."),
    ("good to see you", "Good to see you.", "Good to sit down."),
    ("nice to see you again", "Nice to see you again.", "Nice to stand again."),
    ("pleased to meet you", "Pleased to meet you.", "Pleased to hear it."),
    ("g'day mate", "G'day mate, come through.", "G'day."),
]


class TestConsultationPhrases:
    def test_the_lists_are_pinned_exactly(self) -> None:
        """The 2026-09-28 lists (decision 0.2 (a)), then validation-run7
        Task 0.4 (c)'s dated widening (2026-10-26) — 14 + 16 closings and
        12 + 14 greetings."""
        assert CLOSING_PHRASES == _CLOSINGS_2026_09_28 + _CLOSINGS_ADDED_RUN7_0_4
        assert GREETING_PHRASES == _GREETINGS_2026_09_28 + _GREETINGS_ADDED_RUN7_0_4
        assert (len(_CLOSINGS_2026_09_28), len(_CLOSINGS_ADDED_RUN7_0_4)) == (14, 16)
        assert (len(_GREETINGS_2026_09_28), len(_GREETINGS_ADDED_RUN7_0_4)) == (12, 14)
        assert len(CLOSING_PHRASES) == 30
        assert len(GREETING_PHRASES) == 26

    def test_no_added_phrase_is_one_word(self) -> None:
        """D2 rule 2: the live watcher reads every greeting wherever it sits
        (``positional=False``), so a new one-word phrase of either kind would
        warn anywhere; the 2026-09-28 one-word phrases are untouched."""
        added = (*_CLOSINGS_ADDED_RUN7_0_4, *_GREETINGS_ADDED_RUN7_0_4)
        assert [phrase for phrase in added if len(phrase_tokens(phrase)) < 2] == []
        one_word = [p for p in (*CLOSING_PHRASES, *GREETING_PHRASES) if len(p.split()) == 1]
        assert one_word == ["goodbye", "bye", "hello"]

    def test_no_added_phrase_is_a_hedge_or_a_correction_marker(self) -> None:
        """D2 rule 3 (D3: the hedge lists and the markers are frozen). Rule 3
        rejected by equality and counted containment (Task 0.4 (b)): none was
        found, and none is held here — no added phrase holds a hedge,
        reference hedge or marker as whole tokens in a row."""
        added = {*_CLOSINGS_ADDED_RUN7_0_4, *_GREETINGS_ADDED_RUN7_0_4}
        guarded = (*HEDGE_PHRASES, *REFERENCE_HEDGES, *CORRECTION_MARKERS)
        assert added & set(guarded) == set()
        assert {phrase for phrase in added if _occurrences(phrase, guarded)} == set()

    def test_the_phrases_held_inside_another_are_recorded(self) -> None:
        """A phrase inside a longer one (whole tokens, in a row) is an event
        of its own kind at its own position. Recorded exactly, so a later
        list change shows here: within each kind, and ACROSS kinds — three
        greetings hold the closing "see you", so "Nice to see you, come on
        in" reads, live, as a closing then a greeting (the threat model's
        HANDS-FREE AND WARNINGS paragraph discloses it)."""

        def inside(longer: str, shorter: str) -> bool:
            return longer != shorter and _occurrences(longer, (shorter,)) > 0

        def pairs(outer: tuple[str, ...], inner: tuple[str, ...]) -> set[tuple[str, str]]:
            return {(o, i) for o in outer for i in inner if inside(o, i)}

        assert pairs(CLOSING_PHRASES, CLOSING_PHRASES) == {
            ("see you next week", "see you"),
            ("see you next time", "see you"),
            ("see you soon", "see you"),
            ("see you then", "see you"),
            ("thank you for coming in", "thank you"),
            ("bye bye", "bye"),
            ("i'll see you next week", "see you next week"),
            ("i'll see you next week", "see you"),
            ("see you later", "see you"),
            ("bye for now", "bye"),
            ("see ya later", "see ya"),
        }
        assert pairs(GREETING_PHRASES, GREETING_PHRASES) == {
            ("what can i do for you today", "what can i do for you"),
            ("what brings you in today", "what brings you in"),
            ("how can i help you today", "how can i help"),
            ("nice to see you again", "nice to see you"),
        }
        assert pairs(GREETING_PHRASES, CLOSING_PHRASES) == {
            ("nice to see you", "see you"),
            ("good to see you", "see you"),
            ("nice to see you again", "see you"),
        }
        assert pairs(CLOSING_PHRASES, GREETING_PHRASES) == set()

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
        nothing else of the package (since Task 1.1 it imports both: the
        boundary's cue test and the transcript types)."""
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
            # 3 since validation-run7 Task 0.4 (c) (2026-10-26): "thank you"
            # is a closing of its own inside "thank you for coming in".
            ("Thank you for coming in, bye", 0, 3),
        ],
    )
    def test_the_near_misses_twins_do_match(
        self, text: str, greetings: int, closings: int
    ) -> None:
        assert _occurrences(text, GREETING_PHRASES) == greetings
        assert _occurrences(text, CLOSING_PHRASES) == closings

    @pytest.mark.parametrize(("phrase", "holding", "near_miss"), _ADDED_PHRASE_CASES)
    def test_each_task_0_4_phrase_against_its_near_miss(
        self, phrase: str, holding: str, near_miss: str
    ) -> None:
        """Validation-run7 plan Task 0.4 (c), the 0.3.4 Task 0.9 shape: every
        added phrase is found once in a line holding it, and a neighbouring
        line matches no phrase of either list (whole tokens, in a row)."""
        assert _occurrences(holding, (phrase,)) == 1
        assert _occurrences(near_miss, CLOSING_PHRASES) == 0
        assert _occurrences(near_miss, GREETING_PHRASES) == 0

    def test_every_added_phrase_has_its_near_miss_case(self) -> None:
        assert [case[0] for case in _ADDED_PHRASE_CASES] == [
            *_CLOSINGS_ADDED_RUN7_0_4,
            *_GREETINGS_ADDED_RUN7_0_4,
        ]

    @pytest.mark.parametrize(
        ("text", "typographic", "plain"),
        [
            # "see you next week" and "see you" still match inside it.
            ("I’ll see you next week", 2, 3),
            ("What’s new?", 0, 1),
            ("How’s it going?", 0, 1),
            ("G’day mate", 0, 1),
        ],
    )
    def test_a_typographic_apostrophe_matches_no_apostrophe_phrase(
        self, text: str, typographic: int, plain: int
    ) -> None:
        """A named residue (the threat model's NEXT PATIENT, residue (a)):
        the phrase tokens fold no apostrophe, so "what’s" is not "what's".
        The four apostrophe phrases are three greetings and a closing that
        holds two closings with no apostrophe in them, so the miss is in
        effect a greeting's — it can move the cut one segment earlier, any
        number of segments later, or remove it (``test_consultation_boundary.py``
        pins both directions).
        The plain apostrophe matches."""
        everything = (*CLOSING_PHRASES, *GREETING_PHRASES)
        assert _occurrences(text, everything) == typographic
        assert _occurrences(text.replace("’", "'"), everything) == plain


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
            # Validation-run6 plan Task 0.9 (2026-10-23).
            "i reckon",
            "i believe",
            "i'm not sure",
            "i am not sure",
            "not completely sure",
            "i don't know",
            "i do not know",
            "if i'm correct",
            "if i am correct",
            "i assume",
            "doubtful",
            "conceivably",
            "arguably",
            "seemingly",
            "potentially",
            "probable",
            "seem",
        )
        assert len(HEDGE_PHRASES) == 33
        assert isinstance(HEDGE_PHRASES, tuple)

    def test_every_hedge_is_in_content_token_form_and_unique(self) -> None:
        assert all(" ".join(content_tokens(phrase)) == phrase for phrase in HEDGE_PHRASES)
        assert len(set(HEDGE_PHRASES)) == len(HEDGE_PHRASES)
        # A plain apostrophe only (validation-run6 Task 0.9: "i'm not sure");
        # the matcher folds the typographic one in the line, never the list.
        assert all("’" not in phrase for phrase in HEDGE_PHRASES)

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


class TestReferenceHedges:
    """Validation-run6 plan D8's R2 lexicon (Task 0.9, 2026-10-23): the
    harness-only reference, pinned exactly and as a SUPERSET of
    ``HEDGE_PHRASES``, never read by the app."""

    def test_the_reference_hedges_are_the_hedges_and_these_pinned_exactly(self) -> None:
        assert REFERENCE_HEDGES[: len(HEDGE_PHRASES)] == HEDGE_PHRASES
        assert REFERENCE_HEDGES[len(HEDGE_PHRASES) :] == (
            "presumably",
            "i don't think",
            "i do not think",
            "don't know for sure",
            "may",
            "might",
            "could",
            "would",
            "apparently",
            "apparent",
            "evidently",
            "allegedly",
            "reportedly",
            "it is believed",
            "it is said",
            "according to",
            "we don't know",
            "we do not know",
            "nobody knows",
        )
        assert len(REFERENCE_HEDGES) == 52
        assert isinstance(REFERENCE_HEDGES, tuple)

    def test_the_reference_is_a_superset_of_the_hedges(self) -> None:
        assert set(HEDGE_PHRASES) <= set(REFERENCE_HEDGES)
        assert set(REFERENCE_HEDGES) - set(HEDGE_PHRASES)

    def test_every_reference_hedge_is_in_content_token_form_and_unique(self) -> None:
        assert all(" ".join(content_tokens(p)) == p for p in REFERENCE_HEDGES)
        assert len(set(REFERENCE_HEDGES)) == len(REFERENCE_HEDGES)
        assert all("’" not in phrase for phrase in REFERENCE_HEDGES)

    def test_no_approximator_frequency_or_filler_word_is_a_reference_hedge(self) -> None:
        excluded = {
            "about", "around", "approximately", "roughly", "some", "somewhat",
            "sort", "kind", "bit", "often", "sometimes", "usually", "generally",
            "feel", "felt", "like", "mean", "know",
        }
        loose = {p for p in REFERENCE_HEDGES if set(p.split()) & excluded}
        # "know" only inside a statement of not knowing.
        assert loose == {
            "i don't know", "i do not know", "don't know for sure",
            "we don't know", "we do not know",
        }

    def test_the_known_failure_phrases_membership_is_recorded(self) -> None:
        """Task 0.9 records it either way: a phrase enters only when a named
        source holds it."""
        membership = {
            phrase: (phrase in HEDGE_PHRASES, phrase in REFERENCE_HEDGES)
            for phrase in ("not too sure", "i dunno", "i reckon", "not sure", "i don't know")
        }
        assert membership == {
            "not too sure": (False, False),
            "i dunno": (False, False),
            "i reckon": (True, True),
            "not sure": (False, False),
            "i don't know": (True, True),
        }

    def test_the_app_never_reads_the_reference(self) -> None:
        """By AST, so a comment naming it (``note_check``'s pointer) is not a
        read."""

        def names(path: Path) -> set[str]:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            found: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    found.add(node.id)
                elif isinstance(node, ast.Attribute):
                    found.add(node.attr)
                elif isinstance(node, ast.alias):
                    found.add(node.name)
            return found

        package = Path(validation.__file__).parent
        readers = sorted(
            path.relative_to(package).as_posix()
            for path in package.rglob("*.py")
            if "REFERENCE_HEDGES" in names(path)
        )
        assert readers == ["validation.py"]
