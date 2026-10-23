"""The next-patient boundary (validation-pass plan Phase 1, Tasks 1.1-1.3:
D1, D2, D3, D5; C4-C7).

What is pinned here:

- D2's rule (``consultation_phrases.consultation_boundary``, reached through
  ``note_config.next_patient_boundary``) shape by shape, with the index each
  shape gives: the head case, a closing and a greeting in one segment (cut at
  the NEXT segment, None at the end or before only empty segments), a closing
  or a greeting alone, a phone call, transparent segments, the window, the
  one-word position rule, suspect phrases and their non-suspect twins, and
  the reading built for a greeting segment holding BOTH a closing of its own
  and a closing in the window (the same-segment pairing — dated on D2 and
  Task 1.1);
- the held-out transcript fixtures (Task 0.9), read as Task 0.9 says: every
  case equals its expectation EXCEPT Task 0.10's seven predicted boundary
  divergences, each asserted to DIVERGE — the frozen-list result and the
  case's expected value both named here (C3: no expectation is edited);
- D3: the request cut keeps absolute indices and the whole document's
  digest, the proposals ignore a trigger or region keyword after the
  boundary, Check 3 still reads the whole transcript, and the request cut,
  ``note_fill`` and Check 6 agree on the boundary (C5);
- D5: Check 6 once per note, role-free, on the first withheld segment;
- C6: the note modules never import ``voice_commands``.

Every transcript here is invented; no test reads a real session.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import pytest

from fixtures.heldout_transcripts import (
    HELD_OUT_CASES,
    HeldOutCase,
    Turn,
    build_document,
    by_case,
    misfiled,
)
from scribe_desktop import note_fill
from scribe_desktop.consultation_phrases import (
    BOUNDARY_SEGMENTS,
    consultation_boundary,
    phrase_events,
    word_tokens,
)
from scribe_desktop.note import (
    DEFAULT_SECTION_CUES,
    NOTE_WARNING_SEVERITY,
    ConfirmationDecision,
    ExtractiveNoteProvider,
    GeneratedNote,
    GeneratedSection,
    NoteAssertion,
    NoteProposal,
    NoteSpan,
    NoteWarning,
    SourceCoords,
    transcript_digest,
)
from scribe_desktop.note_check import (
    _words_for_coords,
    check_note,
    next_patient_warnings,
    provenance_warnings,
)
from scribe_desktop.note_config import (
    AutofillRule,
    NoteConfig,
    PrefillSeedAssertion,
    PrefillTemplate,
    build_note_request,
    load_note_config,
    next_patient_boundary,
)
from scribe_desktop.note_fill import (
    autofill_proposals,
    detect_prefill_candidates,
    prefill_proposals,
)
from scribe_desktop.speaker_eval import CLINICIAN_LABEL
from scribe_desktop.transcription import TranscriptDocument
from scribe_desktop.voice_commands import NewConsultationWatcher

REPO: Final = Path(__file__).resolve().parents[2]
VALIDATION_CONFIG: Final = REPO / "validation" / "config"
PACKAGE: Final = REPO / "desktop" / "src" / "scribe_desktop"

_C = CLINICIAN_LABEL
_P = "patient"
_N = "next_patient"
# A patient line the validation config routes ("coming in with"): the
# clinical content D2's head-case guard looks for before a closing.
_CONTENT: Final = Turn(_P, "I'm coming in with a sore right shoulder.")
_CLOSING: Final = Turn(_C, "See you next week.")
_GREETING: Final = Turn(_C, "Hello, come in.")
_TAIL: Final = Turn(_N, "My hip is sore again.")

# Task 0.10's predicted boundary divergences under the frozen lists (C3):
# held-out set -> case id -> (the case's expected boundary, the frozen-list
# result). Each is asserted BOTH ways below, so a later vocabulary decision
# shows here. Keyed per set since validation-run6 Task 0.11; ``heldout-2``'s
# entries are written by its Task 0.12.
_PREDICTED_BOUNDARY_DIVERGENCES_BY_SET: Final[
    dict[str, dict[str, tuple[int | None, int | None]]]
] = {
    "heldout": {
        "hld-09": (5, None),  # its greeting is not in the frozen greeting list
        "hld-10": (4, 5),  # the next patient's greeting is unlisted; a listed one follows
        "hld-11": (4, None),  # a bare time-of-day greeting (excluded by D2's vocabulary rule)
        "hld-12": (5, None),  # a bare time-of-day greeting
        "hld-14": (5, None),  # a greeting phrase D2's vocabulary rule excludes
        "edge-greeting-third-segment": (5, None),  # its closing is not a frozen closing
        "edge-second-sentence-greeting": (3, None),  # its closing is not a frozen closing
    },
    "heldout-2": {},
}
_PREDICTED_BOUNDARY_DIVERGENCES: Final = by_case(_PREDICTED_BOUNDARY_DIVERGENCES_BY_SET)


@pytest.fixture(scope="module")
def validation_config() -> NoteConfig:
    """The validation config over the shipped cues — the config the held-out
    fixtures' routing preconditions are written against (Task 0.9)."""
    return load_note_config(VALIDATION_CONFIG)


def _boundary(turns: tuple[Turn, ...], config: NoteConfig) -> int | None:
    return next_patient_boundary(build_document(turns), config)


def _suspect(document: TranscriptDocument, *indices: int) -> TranscriptDocument:
    """``document`` with every word of the segments at ``indices`` marked
    ``suspect`` (the transcription guard marks whole segments)."""
    segments = tuple(
        segment.model_copy(
            update={
                "transcript_words": tuple(
                    word.model_copy(update={"suspect": True})
                    for word in segment.transcript_words
                )
            }
        )
        if index in indices
        else segment
        for index, segment in enumerate(document.transcript_segments)
    )
    return document.model_copy(update={"transcript_segments": segments})


# --- D2: the rule, shape by shape ---------------------------------------------------


class TestBoundaryShapes:
    def test_a_closing_then_a_greeting_cuts_at_the_greeting(
        self, validation_config: NoteConfig
    ) -> None:
        turns = (_CONTENT, Turn(_C, "I'll do some massage."), _CLOSING, _GREETING, _TAIL)
        assert _boundary(turns, validation_config) == 3

    def test_the_head_case_is_never_cut(self, validation_config: NoteConfig) -> None:
        """D2 condition 3: no clinical content before the closing — a
        recording started while the previous patient leaves."""
        head = (Turn("previous_patient", "See you next week."), _GREETING, _CONTENT, _TAIL)
        assert _boundary(head, validation_config) is None
        # The content must be in a segment BEFORE the closing's own segment.
        same = (Turn(_P, "I'm coming in with a sore knee, see you next week."), _GREETING)
        assert _boundary(same, validation_config) is None

    def test_a_closing_and_a_greeting_in_one_segment_cut_at_the_next_segment(
        self, validation_config: NoteConfig
    ) -> None:
        one = Turn(_C, "See you next week. Hello, come on in.")
        assert _boundary((_CONTENT, one, _TAIL), validation_config) == 2
        # ...the NEXT non-transparent segment, skipping empty ones.
        assert _boundary((_CONTENT, one, Turn(_C, ""), _TAIL), validation_config) == 3

    def test_a_same_segment_pair_with_nothing_after_it_gives_none(
        self, validation_config: NoteConfig
    ) -> None:
        """C4 / peer round 1 PR-MED-003: at the end of the document, or
        followed only by empty segments, there is no segment to cut at."""
        one = Turn(_C, "See you next week. Hello, come on in.")
        assert _boundary((_CONTENT, one), validation_config) is None
        assert _boundary((_CONTENT, one, Turn(_C, ""), Turn(_N, "")), validation_config) is None

    def test_a_greeting_before_the_closing_in_its_segment_is_not_a_pair(
        self, validation_config: NoteConfig
    ) -> None:
        phone = (
            _CONTENT,
            Turn(_C, "Hello, yes, it's the clinic here. Okay, bye."),
            Turn(_C, "Sorry about that, back to your shoulder."),
        )
        assert _boundary(phone, validation_config) is None

    def test_a_closing_alone_or_a_greeting_alone_gives_none(
        self, validation_config: NoteConfig
    ) -> None:
        assert _boundary((_CONTENT, _CLOSING, _TAIL), validation_config) is None
        assert _boundary((_CONTENT, _GREETING, _TAIL), validation_config) is None

    def test_a_phone_call_mid_consultation_gives_none(self, validation_config: NoteConfig) -> None:
        """The greeting of a call comes BEFORE its goodbye, and nothing
        after the goodbye greets."""
        turns = (
            _CONTENT,
            Turn(_C, "Hello, sorry, I have to take this."),
            Turn(_C, "Yes, I'll call you back, bye."),
            Turn(_C, "Sorry, so the shoulder is sore when you lift."),
        )
        assert _boundary(turns, validation_config) is None

    def test_the_window_counts_three_non_transparent_segments(
        self, validation_config: NoteConfig
    ) -> None:
        assert BOUNDARY_SEGMENTS == 3
        filler = Turn(_C, "Just updating the file now.")
        third = (_CONTENT, _CLOSING, filler, filler, _GREETING)
        assert _boundary(third, validation_config) == 4
        fourth = (_CONTENT, _CLOSING, filler, filler, filler, _GREETING)
        assert _boundary(fourth, validation_config) is None

    def test_transparent_segments_are_skipped_and_never_counted(
        self, validation_config: NoteConfig
    ) -> None:
        empty = Turn(_C, "")
        turns = (_CONTENT, _CLOSING, empty, empty, empty, empty, _GREETING)
        assert _boundary(turns, validation_config) == 6

    @pytest.mark.parametrize(
        "greeting, cut",
        [
            ("Hello.", True),  # one word, the whole segment
            ("Hello", True),  # one word, the segment's end follows
            ("Hello, come in.", True),  # first token, punctuation follows
            ("Sorry for the wait. Hello, come through.", True),  # a sentence's first token
            ("Is that everyone? Hello, come through.", True),  # "?" ends a sentence too
            ("Thanks for waiting! Hello, come through.", True),  # and "!"
            ("Hello - come through.", True),  # a word of punctuation alone follows
            ("Sorry for the wait . Hello, come through.", True),  # a lone "." ends one
            ("Hello Sam, come through.", False),  # a name follows, not punctuation
            ("Sorry for the wait - hello, come through.", False),  # a lone "-" ends none
            ("I said hello to her.", False),  # mid-sentence
            ("Sorry for the wait, hello, come through.", False),  # after a comma only
            ("Okay, come on in.", True),  # a longer greeting counts anywhere
            ("Right, good morning to you.", True),  # a longer greeting counts anywhere
            ("My morning stiffness is worse.", False),  # a bare time-of-day word
        ],
    )
    def test_the_one_word_position_rule(
        self, greeting: str, cut: bool, validation_config: NoteConfig
    ) -> None:
        """D2 condition 1: a ONE-word greeting counts only as the first token
        of its segment or of a sentence (after ``.?!``) AND followed by
        punctuation or the segment's end; a longer greeting anywhere."""
        turns = (_CONTENT, _CLOSING, Turn(_N, greeting))
        assert _boundary(turns, validation_config) == (2 if cut else None)

    def test_the_first_qualifying_pair_wins(self, validation_config: NoteConfig) -> None:
        turns = (_CONTENT, _CLOSING, _GREETING, _TAIL, _CLOSING, _GREETING)
        assert _boundary(turns, validation_config) == 2
        # A second greeting right after the first changes nothing.
        second = (_CONTENT, _CLOSING, _GREETING, Turn(_N, "Good morning."))
        assert _boundary(second, validation_config) == 2

    def test_a_same_segment_closing_pairs_before_a_window_closing(
        self, validation_config: NoteConfig
    ) -> None:
        """THE reading built for D2's open case (dated 2026-10-13 on D2 and
        Task 1.1): segment 2 holds a closing BEFORE its greeting AND a closing
        sits in the window (segment 1). The same-segment pairing wins, so the
        cut is the NEXT segment (3) — failing toward inclusion — not segment
        2 itself, which the window pairing alone would give (the reference
        Task 0.10 simulated made the same choice)."""
        both = (_CONTENT, _CLOSING, Turn(_C, "Bye now. Hello, come on in."), _TAIL)
        assert _boundary(both, validation_config) == 3
        window_only = (_CONTENT, _CLOSING, Turn(_C, "Hello, come on in."), _TAIL)
        assert _boundary(window_only, validation_config) == 2

    def test_the_rule_is_role_free(self, validation_config: NoteConfig) -> None:
        turns = (_CONTENT, _CLOSING, _GREETING, _TAIL)
        relabelled = tuple(Turn("speaker_1", turn.text) for turn in turns)
        assert _boundary(turns, validation_config) == _boundary(relabelled, validation_config) == 2


class TestSuspectPhrases:
    """The invented-text guard's D6 (peer round 2 PR-MED-006): a suspect
    closing or greeting supplies no phrase; its twin does."""

    _TURNS: Final = (_CONTENT, _CLOSING, _GREETING, _TAIL)

    def test_a_suspect_closing_or_greeting_gives_no_boundary_and_no_check_6(
        self, validation_config: NoteConfig
    ) -> None:
        twin = build_document(self._TURNS)
        assert next_patient_boundary(twin, validation_config) == 2
        assert len(next_patient_warnings(twin, validation_config)) == 1
        for marked in (1, 2):
            document = _suspect(twin, marked)
            assert next_patient_boundary(document, validation_config) is None, marked
            assert next_patient_warnings(document, validation_config) == (), marked

    def test_suspect_segments_still_count_in_the_window(
        self, validation_config: NoteConfig
    ) -> None:
        noise = Turn(_C, "la la la")
        third = build_document((_CONTENT, _CLOSING, noise, noise, _GREETING))
        assert next_patient_boundary(_suspect(third, 2, 3), validation_config) == 4
        fourth = build_document((_CONTENT, _CLOSING, noise, noise, noise, _GREETING))
        assert next_patient_boundary(_suspect(fourth, 2, 3, 4), validation_config) is None

    def test_the_head_case_cue_test_reads_suspect_words(
        self, validation_config: NoteConfig
    ) -> None:
        """D2: suspect segments stay non-transparent and the head-case cue
        rule is unchanged — it reads every word, as the router does."""
        document = _suspect(build_document(self._TURNS), 0)
        assert next_patient_boundary(document, validation_config) == 2


class TestLiveWarningUnchanged:
    def test_the_watcher_still_counts_a_greeting_anywhere(self) -> None:
        """C7: the live warning changed only by the vocabulary commit — it
        reads the SAME token function and event helper with D2's position
        rule OFF, so a mid-sentence "hello" still warns live while the
        boundary does not count it."""
        document = build_document((_CONTENT, _CLOSING, Turn(_C, "Say hello to your mum.")))
        watcher = NewConsultationWatcher()
        assert watcher.feed(document.transcript_segments)
        tokens = word_tokens(document.transcript_segments[2:])
        assert phrase_events(tokens, positional=False) == [(1, "greeting")]
        assert phrase_events(tokens, positional=True) == []
        assert consultation_boundary(document, DEFAULT_SECTION_CUES, DEFAULT_SECTION_CUES) is None


# --- the held-out fixtures (Task 0.9's reading rule) ---------------------------------


def _case_id(case: HeldOutCase) -> str:
    return case.case_id


class TestHeldOutBoundaries:
    @pytest.mark.parametrize("case", HELD_OUT_CASES, ids=_case_id)
    def test_each_case_matches_or_diverges_as_task_0_10_predicted(
        self, case: HeldOutCase, validation_config: NoteConfig
    ) -> None:
        got = next_patient_boundary(case.document(), validation_config)
        if case.case_id in _PREDICTED_BOUNDARY_DIVERGENCES:
            expected, frozen_list_result = _PREDICTED_BOUNDARY_DIVERGENCES[case.case_id]
            assert case.boundary == expected  # the spec's expectation, unedited (C3)
            assert got == frozen_list_result
            assert got != case.boundary
        else:
            assert got == case.boundary

    def test_the_divergences_are_exactly_task_0_10s_seven(self) -> None:
        assert misfiled(_PREDICTED_BOUNDARY_DIVERGENCES_BY_SET) == []
        counts = {
            name: len(cases) for name, cases in _PREDICTED_BOUNDARY_DIVERGENCES_BY_SET.items()
        }
        assert counts == {"heldout": 7, "heldout-2": 0}

    @pytest.mark.parametrize("case", HELD_OUT_CASES, ids=_case_id)
    def test_a_boundary_is_always_a_spoken_segment(
        self, case: HeldOutCase, validation_config: NoteConfig
    ) -> None:
        document = case.document()
        got = next_patient_boundary(document, validation_config)
        if got is not None:
            words = document.transcript_segments[got].transcript_words
            assert any(word.word_text.strip() for word in words)


# --- D3: the request cut, the proposals, Check 3 ------------------------------------

_ICE_RULE: Final = AutofillRule(
    rule_id="rule-ice",
    section_key="advice_home_exercise",
    trigger_phrase="ice pack",
    expansion=("Ice pack use explained.",),
)
_KNEE_PREFILL: Final = PrefillTemplate(
    prefill_id="knee-exam",
    display_name="Knee examination",
    region_keywords=("knee",),
    seed_assertions=(
        PrefillSeedAssertion(section_key="objective_examination", seed_text="Knee assessed."),
    ),
)
# The trigger and the region keyword are said only by the next patient.
_TAIL_WITH_TRIGGERS: Final = Turn(_N, "My knee is sore and I use an ice pack.")
_CUT_TURNS: Final = (
    _CONTENT,
    Turn(_C, "I'll do some massage through the shoulder."),
    _CLOSING,
    _GREETING,
    _TAIL_WITH_TRIGGERS,
)
# The same recording with no closing: nothing is cut.
_WHOLE_TURNS: Final = (*_CUT_TURNS[:2], Turn(_C, "All done for today."), *_CUT_TURNS[3:])


@pytest.fixture(scope="module")
def proposal_config(validation_config: NoteConfig) -> NoteConfig:
    """The validation config's profiles and cues with one autofill rule and
    one prefill region, so ``note_fill`` has something to match."""
    return NoteConfig(
        template_profiles=validation_config.template_profiles,
        autofill_rules=(_ICE_RULE,),
        prefill_templates=(_KNEE_PREFILL,),
        section_cues=validation_config.section_cues,
    )


def _profile_id(config: NoteConfig) -> str:
    return config.template_profiles[0].template_profile_id


class TestRequestCut:
    def test_the_request_stops_at_the_boundary_with_absolute_indices(
        self, proposal_config: NoteConfig
    ) -> None:
        document = build_document(_CUT_TURNS)
        profile = _profile_id(proposal_config)
        assert next_patient_boundary(document, proposal_config) == 3
        request = build_note_request(document, proposal_config, profile, clinician_speaker=_C)
        assert [u.segment_index for u in request.transcript_utterances] == [0, 1, 2]
        # The digest stays the WHOLE document's (D3).
        assert request.transcript_digest == transcript_digest(document)
        whole = build_note_request(build_document(_WHOLE_TURNS), proposal_config, profile)
        assert [u.segment_index for u in whole.transcript_utterances] == [0, 1, 2, 3, 4]

    def test_coordinates_resolve_the_same_through_the_request_and_the_document(
        self, proposal_config: NoteConfig
    ) -> None:
        document = build_document(_CUT_TURNS)
        request = build_note_request(
            document, proposal_config, _profile_id(proposal_config), clinician_speaker=_C
        )
        provider = ExtractiveNoteProvider(cues=proposal_config.normalised_cues())
        quoted = [
            a for section in provider.generate_sections(request) for a in section.note_assertions
        ]
        # Segment 0 ("coming in with"), 1 ("massage") and 2 (the validation
        # config's follow-up cue "see you next week") are quoted; 3 and 4 are
        # withheld.
        assert sorted(
            a.note_span.source_coords.segment_index
            for a in quoted
            if a.note_span.source_coords is not None
        ) == [0, 1, 2]
        for assertion in quoted:
            coords = assertion.note_span.source_coords
            assert coords is not None
            assert request.words_for_coords(coords) == _words_for_coords(document, coords)
        # A withheld segment is absent from the request, present in the document.
        tail = SourceCoords(4, 0, 0)
        assert request.words_for_coords(tail) is None
        assert _words_for_coords(document, tail) is not None


class TestProposalsStopAtTheBoundary:
    def test_a_trigger_after_the_boundary_proposes_nothing(
        self, proposal_config: NoteConfig
    ) -> None:
        assert autofill_proposals(build_document(_CUT_TURNS), proposal_config) == ()
        whole = autofill_proposals(build_document(_WHOLE_TURNS), proposal_config)
        assert [p.rule_id for p in whole] == ["rule-ice"]

    def test_a_region_keyword_after_the_boundary_detects_nothing(
        self, proposal_config: NoteConfig
    ) -> None:
        cut = build_document(_CUT_TURNS)
        assert detect_prefill_candidates(cut, proposal_config) == ()
        assert prefill_proposals(cut, proposal_config) == ()
        # The clinician's explicit choice still wins, with no trigger time.
        chosen = prefill_proposals(cut, proposal_config, "knee-exam")
        assert [p.trigger_start_seconds for p in chosen] == [None]
        whole = build_document(_WHOLE_TURNS)
        assert [c.prefill_id for c in detect_prefill_candidates(whole, proposal_config)] == [
            "knee-exam"
        ]
        [whole_seed] = prefill_proposals(whole, proposal_config, "knee-exam")
        assert whole_seed.trigger_start_seconds is not None


def _confirmed(proposal: NoteProposal) -> NoteAssertion:
    return NoteAssertion(
        assertion_id="c0",
        section_key=proposal.section_key,
        note_span=NoteSpan(span_text=proposal.note_excerpt, provenance=proposal.provenance),
        proposal_id=proposal.proposal_id,
        shown_text_digest=proposal.shown_text_digest,
        config_digest=proposal.config_digest,
        confirmation=ConfirmationDecision(
            proposal_id=proposal.proposal_id,
            note_confirmation="confirmed",
            decided_at=datetime(2026, 10, 13, tzinfo=UTC),
        ),
    )


def _note(
    document: TranscriptDocument,
    config: NoteConfig,
    sections: tuple[GeneratedSection, ...],
    *,
    clinician_speaker: str | None = _C,
) -> GeneratedNote:
    return GeneratedNote(
        session_id=document.session_id,
        created_at=document.created_at,
        template_profile_id=_profile_id(config),
        provider_name="boundary-test",
        clinician_speaker=clinician_speaker,
        transcript_digest=transcript_digest(document),
        config_digest=config.config_digest(),
        note_sections=sections,
    )


class TestCheck3StaysWhole:
    def test_an_autofill_line_whose_trigger_is_in_the_tail_is_not_absent(
        self, proposal_config: NoteConfig
    ) -> None:
        """D3: Check 3 re-verifies against the WHOLE transcript. The rule's
        proposal comes from the uncut recording (the same session, so the
        same proposal id); checked against the cut one, whose trigger sits
        after the boundary, it is still found — and against a recording with
        no trigger at all it is absent (the control)."""
        [proposal] = autofill_proposals(build_document(_WHOLE_TURNS), proposal_config)
        line = _confirmed(proposal)
        section = (GeneratedSection(section_key=line.section_key, note_assertions=(line,)),)

        def codes(turns: tuple[Turn, ...]) -> list[str]:
            document = build_document(turns)
            note = _note(document, proposal_config, section)
            return [
                w.note_warning_code for w in provenance_warnings(note, document, proposal_config)
            ]

        assert "autofill_trigger_absent" not in codes(_CUT_TURNS)
        no_trigger = (*_CUT_TURNS[:4], Turn(_N, "My knee is sore."))
        assert "autofill_trigger_absent" in codes(no_trigger)


# --- C5: one boundary, every consumer -----------------------------------------------


def _agreement_documents() -> list[tuple[str, TranscriptDocument]]:
    documents = [(case.case_id, case.document()) for case in HELD_OUT_CASES]
    twin = build_document((_CONTENT, _CLOSING, _GREETING, _TAIL))
    documents += [
        ("suspect-twin", twin),
        ("suspect-closing", _suspect(twin, 1)),
        ("suspect-greeting", _suspect(twin, 2)),
        ("cut-with-triggers", build_document(_CUT_TURNS)),
    ]
    return documents


class TestOneBoundaryEveryConsumer:
    @pytest.mark.parametrize(
        "name, document", _agreement_documents(), ids=[name for name, _ in _agreement_documents()]
    )
    def test_the_request_cut_note_fill_and_check_6_agree(
        self,
        name: str,
        document: TranscriptDocument,
        proposal_config: NoteConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        boundary = next_patient_boundary(document, proposal_config)
        # The request cut.
        request = build_note_request(document, proposal_config, _profile_id(proposal_config))
        kept = [u.segment_index for u in request.transcript_utterances]
        total = len(document.transcript_segments)
        assert kept == list(range(total if boundary is None else boundary)), name
        # note_fill: every phrase walk its three entry points make is limited
        # to the same boundary.
        limits: list[int | None] = []
        original = note_fill._first_phrase_match

        def spy(
            document_: TranscriptDocument, tokens: tuple[str, ...], *, limit: Any = None
        ) -> Any:
            limits.append(limit)
            return original(document_, tokens, limit=limit)

        monkeypatch.setattr(note_fill, "_first_phrase_match", spy)
        autofill_proposals(document, proposal_config)
        detect_prefill_candidates(document, proposal_config)
        prefill_proposals(document, proposal_config, "knee-exam")
        assert limits and set(limits) == {boundary}, name
        # Check 6.
        warnings = next_patient_warnings(document, proposal_config)
        located = [w.source_coords.segment_index for w in warnings if w.source_coords is not None]
        assert located == ([] if boundary is None else [boundary]), name


# --- D5: Check 6 --------------------------------------------------------------------


def _generated(
    turns: tuple[Turn, ...], config: NoteConfig, *, clinician_speaker: str | None = _C
) -> tuple[GeneratedNote, TranscriptDocument]:
    document = build_document(turns)
    request = build_note_request(
        document, config, _profile_id(config), clinician_speaker=clinician_speaker
    )
    sections = ExtractiveNoteProvider(cues=config.normalised_cues()).generate_sections(request)
    return _note(document, config, sections, clinician_speaker=clinician_speaker), document


class TestCheck6:
    def test_the_code_is_registered_as_review(self) -> None:
        assert NOTE_WARNING_SEVERITY["possible_next_patient"] == "review"

    def test_once_per_note_on_the_whole_first_withheld_segment(
        self, proposal_config: NoteConfig
    ) -> None:
        turns = (_CONTENT, _CLOSING, _GREETING, _TAIL, _CLOSING, _GREETING)
        note, document = _generated(turns, proposal_config)
        warnings = check_note(note, document, proposal_config)
        found = [w for w in warnings if w.note_warning_code == "possible_next_patient"]
        # "Hello, come in." is three words: coordinates (2, 0, 2), no section.
        assert found == [
            NoteWarning(
                note_warning_code="possible_next_patient",
                severity="review",
                source_coords=SourceCoords(2, 0, 2),
            )
        ]
        assert warnings[-1] == found[0]  # appended last (D5)

    def test_a_same_segment_pair_points_at_the_segment_after_it(
        self, proposal_config: NoteConfig
    ) -> None:
        turns = (_CONTENT, Turn(_C, "See you next week. Hello, come on in."), _TAIL)
        note, document = _generated(turns, proposal_config)
        [found] = [
            w
            for w in check_note(note, document, proposal_config)
            if w.note_warning_code == "possible_next_patient"
        ]
        # "My hip is sore again." — five words, and no greeting in it.
        assert found.source_coords == SourceCoords(2, 0, 4)

    def test_role_free_with_no_confirmed_clinician(self, proposal_config: NoteConfig) -> None:
        note, document = _generated(
            (_CONTENT, _CLOSING, _GREETING, _TAIL), proposal_config, clinician_speaker=None
        )
        codes = [w.note_warning_code for w in check_note(note, document, proposal_config)]
        assert codes.count("possible_next_patient") == 1
        # Check 4 is silent with no role; Check 6 is not.
        assert "high_risk_omission" not in codes

    def test_no_boundary_no_warning(self, proposal_config: NoteConfig) -> None:
        note, document = _generated((_CONTENT, _CLOSING, _TAIL), proposal_config)
        codes = [w.note_warning_code for w in check_note(note, document, proposal_config)]
        assert "possible_next_patient" not in codes

    def test_check_4_still_flags_the_withheld_lines(self, proposal_config: NoteConfig) -> None:
        """Decision 0.5 (a): Check 4 is unchanged over the tail, so a
        withheld claim word still draws ``high_risk_omission``."""
        tail = Turn(_N, "My left hip is sore again.")
        note, document = _generated((_CONTENT, _CLOSING, _GREETING, tail), proposal_config)
        omitted = [
            w.source_coords.segment_index
            for w in check_note(note, document, proposal_config)
            if w.note_warning_code == "high_risk_omission" and w.source_coords is not None
        ]
        assert 3 in omitted

    def test_a_stored_warning_reads_back_as_itself(self, proposal_config: NoteConfig) -> None:
        note, document = _generated((_CONTENT, _CLOSING, _GREETING, _TAIL), proposal_config)
        warnings = check_note(note, document, proposal_config)
        stored = GeneratedNote.model_validate(
            {**note.model_dump(), "note_warnings": [w.model_dump() for w in warnings]}
        )
        reloaded = GeneratedNote.from_bytes(stored.to_bytes())
        assert "possible_next_patient" in [w.note_warning_code for w in reloaded.note_warnings]


# --- C6: the import cycle -----------------------------------------------------------

_NOTE_MODULES: Final = ("note", "note_config", "note_fill", "note_check", "consultation_phrases")


class TestNoImportOfVoiceCommands:
    def test_importing_the_note_modules_never_imports_voice_commands(self) -> None:
        """C6: ``voice_commands`` imports ``session``, which reaches
        ``note_config`` through ``draft_write``; importing the note modules
        in a fresh interpreter must not load it."""
        modules = ", ".join(f"scribe_desktop.{name}" for name in _NOTE_MODULES)
        code = (
            f"import sys; import {modules}; "
            "print('scribe_desktop.voice_commands' in sys.modules)"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, timeout=120, check=False
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "False"

    @pytest.mark.parametrize("name", _NOTE_MODULES)
    def test_no_note_module_names_voice_commands_in_an_import(self, name: str) -> None:
        tree = ast.parse((PACKAGE / f"{name}.py").read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
                imported += [f"{node.module}.{alias.name}" for alias in node.names]
            elif isinstance(node, ast.Import):
                imported += [alias.name for alias in node.names]
        assert not [n for n in imported if "voice_commands" in n], name
