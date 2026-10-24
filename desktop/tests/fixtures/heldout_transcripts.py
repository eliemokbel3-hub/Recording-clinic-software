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
  speaker — any speaker in ``heldout-2``, whose spec says "a speaker" — a
  separate following segment, a self-correcting opener, one hop).
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

Validation-run6 plan Task 0.11: the held-out SETS are one table,
``HELD_OUT_SETS`` — per set its folder name under ``validation/``, its case
id prefix and its cases (``validation/heldout`` with ``hld-`` and the
``edge-`` cases; ``validation/heldout-2`` with ``h2-``, authored blind in
Task 0.10; its cases written in Task 0.12). A set's ``cases_written`` is
False until its cases exist: such a set holds no case, its scripts — none
while its folder is absent or empty — get the script lints only, and
``HELD_OUT_CASES`` gains nothing from it. Both sets are written now.

Validation-run6 plan Task 0.17 (D16): ``validation/heldout-3`` with ``h3-``,
the blind set, is in the table with ``cases_written=False`` until after run
6 (Task P.4). It is ``tails_by_role`` — an axis script's reference tail start
is the index of its first ``next_patient`` line, so no case boundary is
needed — and ``routed_material`` — every material fact on a non-clinician
line sits in a routed clause. ``script_count`` and ``facts_per_script`` are
its brief's bounds, linted from metadata only. While any ``h3-`` script is
in the tree, the suite runs only through ``scripts/lint-held-out-set.py``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from scribe_desktop.speaker_eval import CLINICIAN_LABEL
from scribe_desktop.transcription import TranscriptDocument
from scribe_desktop.validation import document_from_turns, load_script

REPO: Final = Path(__file__).resolve().parents[3]
VALIDATION_DIR: Final = REPO / "validation"
EDGE_CASE_PREFIX: Final = "edge-"

NO_CORRECTION: Final = "no routed non-clinician line is followed by that speaker's self-correction"
NO_HEDGE: Final = "no quoted non-clinician line hedges about the speaker's own state"


@dataclass(frozen=True)
class Turn:
    """One segment: its speaker label and its text ("" for a segment with
    no words)."""

    speaker: str
    text: str


def build_document(turns: tuple[Turn, ...]) -> TranscriptDocument:
    """The turns as a transcript, through the harness's own builder
    (``validation.document_from_turns``, moved there by validation-run6
    plan Task 0.9 unchanged)."""
    return document_from_turns(turns)


def script_path(encounter_id: str) -> Path:
    """The held-out script a scripted case reads: the set whose prefix the
    id carries (Task 0.11)."""
    for held_out in HELD_OUT_SETS:
        if encounter_id.startswith(held_out.prefix):
            return held_out.folder / f"{encounter_id}.json"
    raise ValueError("no held-out set has this case id's prefix")


def script_turns(encounter_id: str) -> tuple[Turn, ...]:
    """The held-out script's lines as turns (role as the speaker label)."""
    script = load_script(script_path(encounter_id))
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


# Validation-run6 plan Task 0.12 (2026-10-24): one case per ``heldout-2``
# script, its expectations read off the author's behaviour spec
# (``validation/heldout-2/SPEC.md``) and notes (``AUTHOR-NOTES.md``) under the
# readings above, never off the frozen phrase lists. Two readings the set's
# spec adds: a fix by ANY speaker is a correction (D4 names "same speaker"
# only), and doubt voiced in a SEPARATE line marks the line holding the fact
# it doubts (the spec's "mark that line"), not the doubting line.
HELDOUT_2_CASES: Final[tuple[HeldOutCase, ...]] = (
    HeldOutCase(
        "h2-01",
        13,
        "closing at 12, the next patient welcomed at 13 ('Hiya, come on through'), content at 1-10",
        unsure=(3,),
        unsure_reason="patient doubts the tingling (3); the clinician never hedges",
    ),
    HeldOutCase(
        "h2-02",
        None,
        "the closing (6) is the last segment; no one new is welcomed",
        corrections=(2,),
        corrections_reason="2 fixes 1's side, opening with a filler and an apology",
    ),
    HeldOutCase(
        "h2-03",
        None,
        "the head greeting (0) has no closing before it; the closing (11) is the last segment",
        unsure=(1,),
        unsure_reason=(
            "2 doubts 1's day in a separate line, so 1 (the fact's line) is the line to mark;"
            " 2 is doubt only, not a fix"
        ),
    ),
    HeldOutCase(
        "h2-04",
        None,
        "the partner's 'Hello!' (3) has no closing before it and is not a new patient",
        unsure=(5,),
        unsure_reason="the partner doubts the sleeping (5); 6's 'absolutely certain' is not doubt",
    ),
    HeldOutCase(
        "h2-05",
        12,
        "closing at 11, 'Good afternoon' opens 12's second sentence, content at 1-10",
        unsure=(1,),
        unsure_reason="patient guesses the frequency mid-line (1); the clinician's hunch (6) isn't",
    ),
    HeldOutCase(
        "h2-06",
        None,
        "the closing (5) is the last segment; 'waved hello' (4) is small talk, before it",
    ),
    HeldOutCase(
        "h2-07",
        10,
        "closing at 9 ('ta-ra'), 'come in' welcomes the next patient at 10, content at 1-7",
    ),
    HeldOutCase(
        "h2-08",
        None,
        "the closing (9) is the last segment",
        corrections=(2,),
        corrections_reason="2 fixes 1's number, opening with a filler ('Er, no')",
        unsure=(7,),
        unsure_reason="patient doubts the year (7, 'don't quote me on that')",
    ),
    HeldOutCase(
        "h2-09",
        9,
        "closing at 8, 'Come on in' (9) welcomes the next one, content at 1-7",
    ),
    HeldOutCase(
        "h2-10",
        None,
        "the receptionist (2) interrupts with no greeting; the closing (10) is the last segment",
        unsure=(1,),
        unsure_reason="patient doubts the count (1); 5's 'definitely' and 'positive' are not doubt",
    ),
    HeldOutCase(
        "h2-11",
        12,
        "closing at 10-11, 'Hello,' opens 12's second sentence with a comma after it",
        corrections_reason=(
            "2 fixes 1's time but routes on its own cue, so it is quoted, not carried"
        ),
    ),
    HeldOutCase(
        "h2-12",
        None,
        "the head greeting (0) has no closing before it; the closing (8) is the last segment",
        unsure=(2,),
        unsure_reason=(
            "3 doubts 2 in a separate line, so 2 (the fact's line) is the line to mark;"
            " 7's 'I'm sure' is not doubt"
        ),
    ),
    HeldOutCase(
        "h2-13",
        None,
        "'welcome to week six' (2) is mid-consultation; the closing (11-12) ends the recording",
        unsure=(3,),
        unsure_reason="patient doubts the tingling (3); the clinician's 'probably' (5) is not",
    ),
    HeldOutCase(
        "h2-14",
        8,
        "closing at 7 ('cheerio'), 'hello there' welcomes the next patient at 8, content at 1-5",
    ),
    HeldOutCase(
        "h2-15",
        None,
        "no closing before the last segment (11)",
        corrections_reason=(
            "2 opens 'Actually' but adds new information - not a fix (the author's deliberate"
            " non-fix)"
        ),
        unsure=(1,),
        unsure_reason=(
            "patient doubts the spread (1); 4's 'No doubt about it' and 10's 'I'm sure' are not"
        ),
    ),
    HeldOutCase(
        "h2-16",
        None,
        "the same patient comes back after the closing (4-5); no one new is welcomed",
        corrections_reason="6 opens 'Oh, sorry' but is an afterthought, not a fix",
    ),
    HeldOutCase(
        "h2-17",
        10,
        "closing at 9, 'Hello, hello, come in' opens 10, content at 1-7",
        unsure=(3,),
        unsure_reason="patient doubts the tingling's cause (3, 'I don't know')",
    ),
    HeldOutCase(
        "h2-18",
        None,
        "the head greeting (0) has no closing before it; the closing (18-19) ends the recording",
        unsure=(1, 6),
        unsure_reason=(
            "patient doubts the duration (1) and the surgery (6); 3's 'I'm certain' is not doubt"
        ),
    ),
    HeldOutCase(
        "h2-19",
        None,
        "the closing (6) is the last segment",
        corrections=(3,),
        corrections_reason="the clinician's 3 fixes 2's side, opening with a filler and an apology",
    ),
    HeldOutCase(
        "h2-20",
        None,
        "no closing before the last segment (11)",
        unsure=(4,),
        unsure_reason="patient hedges the cause (4, 'I reckon'), a hedge whatever it is about (D7)",
    ),
    HeldOutCase(
        "h2-21",
        None,
        "the relayed 'good morning' (11) has no closing before it; the closing is in 12",
        unsure=(4,),
        unsure_reason="patient doubts the duration (4); the clinician's 'Possibly' (10) is not",
    ),
    HeldOutCase(
        "h2-22",
        10,
        "closing at 9, the one-word 'Morning,' opens 10 with a comma after it, content at 3-8",
        corrections_reason=(
            "4 fixes 3's day, but 3 routes nowhere, so there is no section to carry it into"
        ),
    ),
)


@dataclass(frozen=True)
class HeldOutSet:
    """One held-out set (Task 0.11): ``name`` is its folder under
    ``validation/`` (and the harness's set name), ``prefix`` its scripts'
    and scripted cases' id prefix, ``cases`` one per script, ``edge_cases``
    the explicit-turn cases authored with it. ``cases_written`` False: no
    case yet (the set's scripts get the script lints only). Task 0.17:
    ``tails_by_role`` — the tails come from the ``next_patient`` role;
    ``routed_material`` — every material fact on a non-clinician line is
    routed; ``script_count`` / ``facts_per_script`` — inclusive bounds, or
    None for none."""

    name: str
    prefix: str
    cases: tuple[HeldOutCase, ...]
    edge_cases: tuple[HeldOutCase, ...] = ()
    cases_written: bool = True
    tails_by_role: bool = False
    routed_material: bool = False
    script_count: tuple[int, int] | None = None
    facts_per_script: tuple[int, int] | None = None

    @property
    def folder(self) -> Path:
        return VALIDATION_DIR / self.name

    def script_paths(self) -> list[Path]:
        """The set's scripts; none while its folder is absent."""
        return sorted(self.folder.glob("*.json"))

    def all_cases(self) -> tuple[HeldOutCase, ...]:
        return self.cases + self.edge_cases


HELD_OUT_SETS: Final[tuple[HeldOutSet, ...]] = (
    HeldOutSet("heldout", "hld-", SCRIPT_CASES, EDGE_CASES),
    # Authored blind in Task 0.10; its ``h2-NN`` cases written in Task 0.12.
    HeldOutSet("heldout-2", "h2-", HELDOUT_2_CASES),
    # Task 0.17: authored blind; never read before run 6 (D16, C12).
    HeldOutSet(
        "heldout-3",
        "h3-",
        (),
        cases_written=False,
        tails_by_role=True,
        routed_material=True,
        script_count=(20, 25),
        facts_per_script=(3, 6),
    ),
)
NEXT_PATIENT_ROLE: Final = "next_patient"
SCRIPT_CASE_PREFIXES: Final[tuple[str, ...]] = tuple(s.prefix for s in HELD_OUT_SETS)

HELD_OUT_CASES: Final[tuple[HeldOutCase, ...]] = tuple(
    case for held_out in HELD_OUT_SETS for case in held_out.all_cases()
)


def held_out_set(name: str) -> HeldOutSet:
    """The set of that name in the table."""
    (held_out,) = (s for s in HELD_OUT_SETS if s.name == name)
    return held_out


def by_case[V](per_set: Mapping[str, Mapping[str, V]]) -> dict[str, V]:
    """A per-set table (set name -> case id -> entry; the tests' predicted
    divergences, Task 0.11) flattened to case id -> entry."""
    return {case_id: entry for entries in per_set.values() for case_id, entry in entries.items()}


def misfiled(per_set: Mapping[str, Mapping[str, object]]) -> list[str]:
    """What is wrong with a per-set table's keys: a set name it lacks or
    adds, and each case id filed under a set that does not hold that case.
    Empty when well formed."""
    names = [held_out.name for held_out in HELD_OUT_SETS]
    problems = [f"set {name}" for name in names if name not in per_set]
    problems += [f"set {name}" for name in per_set if name not in names]
    for held_out in HELD_OUT_SETS:
        own = {case.case_id for case in held_out.all_cases()}
        problems += [case_id for case_id in per_set.get(held_out.name, {}) if case_id not in own]
    return problems
