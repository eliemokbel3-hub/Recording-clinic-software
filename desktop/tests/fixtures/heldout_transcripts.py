"""Validation-pass plan Task 0.9: the HELD-OUT transcript fixtures.

One case per held-out synthetic script (``validation/heldout/hld-NN.json``,
its turns read from the script's own lines, one segment per line) plus a few
pure-transcript edge cases (``edge-*``, their turns written here). Each case
carries its EXPECTED outcome as plain data, derived from the behaviour spec
in words — written by an author who had not seen the phrase lists the
features use, and never tuned to them:

- ``boundary``: the absolute index of the first segment to withhold (a
  possible next consultation starts there), or None for no cut. The rule:
  a closing, then within the next three speech segments a greeting at the
  start of a segment or sentence (a one-word greeting only when followed by
  punctuation or the segment's end); only with clinical content before the
  closing; cut at the greeting's segment, or at the NEXT segment when the
  closing and the greeting share one (no cut when none follows); the first
  qualifying pair; whoever speaks.
- ``corrections``: the segments whose self-correction is carried into the
  section of the same speaker's routed line just before it (a non-clinician
  speaker, a separate following segment, a self-correcting opener, one hop).
- ``unsure``: the segments whose quoted line gets the "unsure" mark (a
  non-clinician hedging about their own state; never the clinician).

An "utterance" here is one segment. ``corrections`` and ``unsure`` assume the
line they name (or the line a correction follows) is quoted in the note; the
held-out scripts give each such patient line a phrase the validation config
routes for a patient (``tingling``, ``since last time``, ``coming in with``).

The rules above are the behaviour spec as the author was given it. Where the
plan words a rule more precisely, the plan governs, and its Task 0.9 records
each reading (review round 8): D2 — only a ONE-word greeting must open its
segment or a sentence (after ``.?!``); segments with no words are skipped and
never counted in the three; the clinical content must be in an EARLIER
segment than the closing. D4 — a correction is carried only when it holds no
section cue of its own (in either cue layer) and the routed line before it is
cue-routed (so a correction after a CARRIED line is a second hop) and not in a
clinician-only section. D7 — the mark is per quoted non-clinician line
holding a hedge, whatever the hedge is about. A case the frozen phrase lists
get "wrong" is a recorded prediction (validation-pass Task 0.10), never a
reason to edit its expectation (C3).

Where a scenario has a next patient, that patient's material lines are NOT
expected facts of the first: the scripts list them as ``absent`` facts (the
script model's own place for content that must not reach the note).

Data and small builders only: nothing here imports a module that does not
exist yet. The text is invented.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from scribe_desktop.speaker_eval import CLINICIAN_LABEL
from scribe_desktop.transcription import TranscriptDocument, TranscriptSegment, TranscriptWord
from scribe_desktop.validation import load_script

REPO: Final = Path(__file__).resolve().parents[3]
HELDOUT_DIR: Final = REPO / "validation" / "heldout"
SCRIPT_CASE_PREFIX: Final = "hld-"
EDGE_CASE_PREFIX: Final = "edge-"

_SESSION_ID: Final = "0123456789abcdef" * 2
_CREATED_AT: Final = datetime(2026, 10, 13, tzinfo=UTC)
_WORD_MS: Final = 300
_GAP_MS: Final = 600
_PROBABILITY: Final = 0.95

NO_CORRECTION: Final = "no routed non-clinician line is followed by that speaker's self-correction"
NO_HEDGE: Final = "no quoted non-clinician line hedges about the speaker's own state"


@dataclass(frozen=True)
class Turn:
    """One segment: its speaker label and its text ("" for a segment with
    no words)."""

    speaker: str
    text: str


def build_document(turns: tuple[Turn, ...]) -> TranscriptDocument:
    """A transcript with one segment per turn, its words split on whitespace,
    every word confident and certain, timed back to back (whole milliseconds,
    so the times are exact)."""
    segments: list[TranscriptSegment] = []
    clock = 0
    for turn in turns:
        start = clock
        words: list[TranscriptWord] = []
        for text in turn.text.split():
            words.append(
                TranscriptWord(
                    word_text=text,
                    start_seconds=clock / 1000,
                    end_seconds=(clock + _WORD_MS) / 1000,
                    probability=_PROBABILITY,
                    uncertain=False,
                )
            )
            clock += _WORD_MS
        segments.append(
            TranscriptSegment(
                start_seconds=start / 1000,
                end_seconds=clock / 1000,
                speaker=turn.speaker,
                transcript_words=tuple(words),
            )
        )
        clock += _GAP_MS
    return TranscriptDocument(
        session_id=_SESSION_ID,
        created_at=_CREATED_AT,
        model_name="heldout-fixture",
        sample_rate=16_000,
        transcript_segments=tuple(segments),
    )


def script_turns(encounter_id: str) -> tuple[Turn, ...]:
    """The held-out script's lines as turns (role as the speaker label)."""
    script = load_script(HELDOUT_DIR / f"{encounter_id}.json")
    return tuple(Turn(line.role, line.text) for line in script.lines)


@dataclass(frozen=True)
class HeldOutCase:
    """One held-out case and its expected outcomes, each with a one-line
    reason. ``explicit_turns`` is empty for a ``hld-`` case (its turns are
    its script's lines, read when asked for, so a broken script fails its
    own lint rather than this module's import)."""

    case_id: str
    boundary: int | None
    boundary_reason: str
    corrections: tuple[int, ...] = ()
    corrections_reason: str = NO_CORRECTION
    unsure: tuple[int, ...] = ()
    unsure_reason: str = NO_HEDGE
    explicit_turns: tuple[Turn, ...] = ()
    clinician_speaker: str = CLINICIAN_LABEL

    def turns(self) -> tuple[Turn, ...]:
        if self.explicit_turns:
            return self.explicit_turns
        return script_turns(self.case_id)

    def document(self) -> TranscriptDocument:
        return build_document(self.turns())


def _t(speaker: str, text: str) -> Turn:
    return Turn(speaker, text)


_C = CLINICIAN_LABEL
_P = "patient"
_N = "next_patient"

SCRIPT_CASES: Final[tuple[HeldOutCase, ...]] = (
    HeldOutCase(
        "hld-01",
        None,
        "closing at 3; 'Morning' opens 4 with a word after it; 'morning' ends 5 and 6",
    ),
    HeldOutCase(
        "hld-02",
        None,
        "the phone's 'Hello' (4) comes before its 'bye' (5); 6-8 after that hold no greeting",
    ),
    HeldOutCase(
        "hld-03",
        None,
        "the partner and clinician greet at 4-5 mid-consultation, with no closing before them",
    ),
    HeldOutCase(
        "hld-04",
        None,
        "receptionist greets at 3 with no closing before; after their 'bye' (5), 6-8 hold none",
    ),
    HeldOutCase(
        "hld-05",
        None,
        "closing at 3; 'Hey,' at 4 is relief at the news, not a start-of-visit greeting",
    ),
    HeldOutCase(
        "hld-06",
        None,
        "closing at 3; 'You're welcome' (5) and the dictation (6-7) are not greetings",
    ),
    HeldOutCase(
        "hld-07",
        None,
        "farewell at 3-4; 5 asks how the exercises are going - a question, not a greeting",
    ),
    HeldOutCase(
        "hld-08",
        None,
        "closing (0-1) and greeting (2) precede any clinical content - the head case is never cut",
    ),
    HeldOutCase(
        "hld-09",
        5,
        "closing at 3, 'G'day,' opens 5 with a comma after it, clinical content at 1-2",
    ),
    HeldOutCase(
        "hld-10",
        4,
        "closing at 3, the next patient's 'Hiya,' opens 4, clinical content at 1-2",
    ),
    HeldOutCase(
        "hld-11",
        4,
        "closing and 'Morning,' share segment 3, so the cut is the next segment, 4",
    ),
    HeldOutCase(
        "hld-12",
        5,
        "closing at 3-4, the one-word 'Afternoon.' is all of 5 and ends in a full stop",
    ),
    HeldOutCase(
        "hld-13",
        5,
        "closing at 3-4, 'Good afternoon' opens 5, clinical content at 1-2",
    ),
    HeldOutCase(
        "hld-14",
        5,
        "closing at 3-4, 'How are you going?' opens 5 as a greeting to the next patient",
    ),
    HeldOutCase(
        "hld-15",
        None,
        "no closing anywhere",
        corrections=(3,),
        corrections_reason=(
            "2 holds a shipped section cue, so it is routed, not carried (D4: no cue);"
            " 3 then follows cue-routed 2 - a first hop (review round 8 MED-001)"
        ),
    ),
    HeldOutCase(
        "hld-16",
        None,
        "no closing anywhere",
        corrections=(2,),
        corrections_reason=(
            "2 opens 'Scratch that' after routed 1; 5's 'I mean' is the clinician, another speaker"
        ),
    ),
    HeldOutCase(
        "hld-17",
        None,
        "no closing anywhere",
        corrections_reason=(
            "2 is an aside ('Sorry, don't write this down'), 5 a request to wait - neither carries"
        ),
    ),
    HeldOutCase(
        "hld-18",
        None,
        "no closing anywhere",
        corrections=(2,),
        corrections_reason=(
            "2 opens 'Make that' after routed 1; 5 opens with 'Yeah', its 'actually' comes later"
        ),
    ),
    HeldOutCase(
        "hld-19",
        None,
        "the closing (7) is the last segment",
        unsure=(3, 5),
        unsure_reason=(
            "patient hedges 'I reckon' (3), 'Hard to say' (5); never the clinician's 'I reckon' (6)"
        ),
    ),
    HeldOutCase(
        "hld-20",
        None,
        "no closing before 'afternoon', which ends its sentence anyway",
        unsure=(3, 5),
        unsure_reason=(
            "patient hedges 'if I had to guess' (3), 'I suppose' (5); 'blurry' vision (1) is not"
        ),
    ),
    HeldOutCase(
        "hld-21",
        None,
        "the closing (7) is the last segment",
        unsure=(3, 5),
        unsure_reason=(
            "patient hedges 'Not too sure' (3), 'I dunno' (5); a 'vague, dull ache' (1) is not one"
        ),
    ),
    HeldOutCase(
        "hld-22",
        None,
        "no closing anywhere",
        corrections=(2,),
        corrections_reason=(
            "2 opens 'I mean' after the filler 'Um', following cue-routed 1;"
            " 3's 'I tell a lie' follows carried 2 - a second hop"
        ),
    ),
)

EDGE_CASES: Final[tuple[HeldOutCase, ...]] = (
    HeldOutCase(
        "edge-same-segment-then-empty",
        None,
        "closing and greeting share 1 and only empty segments follow - no segment to cut at",
        explicit_turns=(
            _t(_P, "There's tingling in my right foot since last time."),
            _t(_C, "Okay, see you next week. Hi, come on in."),
            _t(_C, ""),
            _t(_N, ""),
        ),
    ),
    HeldOutCase(
        "edge-same-segment-at-end",
        None,
        "closing and greeting share the last segment - no segment follows",
        explicit_turns=(
            _t(_P, "Since last time the tingling in my left hand is worse."),
            _t(_C, "I'll do some needles through the forearm."),
            _t(_C, "Alright, see you Friday. Hello, come on in."),
        ),
    ),
    HeldOutCase(
        "edge-pair-at-very-end",
        3,
        "closing at 2, the one-word 'Hello.' is the whole last segment",
        explicit_turns=(
            _t(_P, "I'm coming in with a sore right knee."),
            _t(_C, "I'll do some massage and send you some exercises."),
            _t(_C, "See you next week."),
            _t(_N, "Hello."),
        ),
    ),
    HeldOutCase(
        "edge-greeting-third-segment",
        5,
        "closing at 2, greeting opens 5 - the third segment after it, inside the window",
        explicit_turns=(
            _t(_P, "Since last time the neck is moving a bit better."),
            _t(_C, "I'll do some massage through the upper traps."),
            _t(_C, "All done, see you next Tuesday."),
            _t(_P, "Thanks."),
            _t(_C, "Just updating the file now."),
            _t(_C, "Hello, come in."),
        ),
    ),
    HeldOutCase(
        "edge-greeting-fourth-segment",
        None,
        "closing at 2, the greeting opens 6 - the fourth segment after it, outside the window",
        explicit_turns=(
            _t(_P, "Since last time the neck is moving a bit better."),
            _t(_C, "I'll do some massage through the upper traps."),
            _t(_C, "All done, see you next Tuesday."),
            _t(_C, "Just updating the file now."),
            _t(_C, "Plan is to keep the same treatment."),
            _t(_C, "Neck range is improving week to week."),
            _t(_C, "Hello, come in."),
        ),
    ),
    HeldOutCase(
        "edge-name-after-one-word-greeting",
        None,
        "'Hi' opens 3 but a name, not punctuation, follows it: the one-word rule does not count",
        explicit_turns=(
            _t(_P, "I'm coming in with a sore lower back."),
            _t(_C, "I'll do some massage and send you some exercises."),
            _t(_C, "Good stuff, see you next week."),
            _t(_C, "Hi Sam come in."),
            _t(_N, "My shoulder is sore again."),
        ),
    ),
    HeldOutCase(
        "edge-second-sentence-greeting",
        3,
        "closing at 2, 'Hello,' opens the second sentence of 3",
        explicit_turns=(
            _t(_P, "Since last time the tingling has settled."),
            _t(_C, "I'll send you some exercises for the hip."),
            _t(_C, "See you in two weeks."),
            _t(_C, "Sorry for the wait. Hello, come through."),
        ),
    ),
    HeldOutCase(
        "edge-greeting-mid-sentence",
        None,
        "closing at 2; 'hello' in 3 sits mid-sentence, not at a segment or sentence start",
        explicit_turns=(
            _t(_P, "Since last time my back is moving a bit better."),
            _t(_C, "I'll send you some exercises for the back."),
            _t(_C, "See you next week."),
            _t(_C, "Say hello to your mum for me."),
            _t(_P, "Will do, bye."),
        ),
    ),
    HeldOutCase(
        "edge-first-pair-wins",
        3,
        "two qualifying pairs (2-3 and 5-6); the first is used",
        explicit_turns=(
            _t(_P, "I'm coming in with a sore left ankle."),
            _t(_C, "I'll do some massage around the ankle."),
            _t(_C, "See you next week."),
            _t(_C, "Hello, come in."),
            _t(_N, "My right hip is sore."),
            _t(_C, "Okay, see you next week."),
            _t(_C, "Hello, come in."),
        ),
    ),
    HeldOutCase(
        "edge-head-then-real",
        5,
        "the head pair (0-1) has no clinical content before it; the next pair (4-5) does",
        explicit_turns=(
            _t("previous_patient", "See you next week."),
            _t(_C, "Hello, come in."),
            _t(_P, "I'm coming in with a sore neck."),
            _t(_C, "I'll do some massage through the neck."),
            _t(_C, "See you next week."),
            _t(_C, "Hello, come on through."),
        ),
    ),
)

HELD_OUT_CASES: Final[tuple[HeldOutCase, ...]] = SCRIPT_CASES + EDGE_CASES
