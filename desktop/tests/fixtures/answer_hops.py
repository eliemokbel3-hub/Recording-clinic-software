"""Answers-follow-question plan Task 1.1: the ANSWER-HOP fixture matrix.

Plain expectations, written from the form the plan's Task 0.6 chose (D1's
transition table with the unlimited reach, guard G and switch S): each case
is a small invented transcript and the section every placed segment lands in
under the shipped extractive provider at the shipped cues. A segment absent
from ``placed`` is not in the note. ``TestAnswerHop`` (``test_note.py``)
reads them; the product never imports this module.

The clinician is ``SPEAKER_2`` unless a case says otherwise. ``""`` is a
textless segment; every word of a ``suspect`` segment is marked suspect.

No clinical content: invented sentences only.
"""

from __future__ import annotations

from typing import Final, NamedTuple

from fixtures.joined_runs import split_document
from scribe_desktop.note import NoteSectionKey
from scribe_desktop.transcription import SPEAKER_1, SPEAKER_2, SPEAKER_3, TranscriptDocument

CLINICIAN: Final = SPEAKER_2
PATIENT: Final = SPEAKER_1
OTHER: Final = SPEAKER_3

RED: Final[NoteSectionKey] = "red_flags_screening"
PRESENTING: Final[NoteSectionKey] = "presenting_complaint"
HISTORY: Final[NoteSectionKey] = "history_presenting_complaint"

# The clinician's question: "any numbness" routes it to Red flags (not
# clinician-owned), its one sentence is a question that alone routes there.
QUESTION: Final = "Any numbness in your feet?"
# A reply with no cue of either layer in any section, and not a question.
REPLY: Final = "No, none at all."


class AnswerHopCase(NamedTuple):
    """One cell: ``turns`` are ``(text, speaker)``, one segment each;
    ``placed`` is ``(segment, section)`` for every segment in the note."""

    name: str
    turns: tuple[tuple[str, str], ...]
    placed: tuple[tuple[int, NoteSectionKey], ...]
    clinician: str | None = CLINICIAN
    suspect: tuple[int, ...] = ()

    def document(self) -> TranscriptDocument:
        return split_document(*self.turns, suspect=self.suspect)


ANSWER_HOP_CASES: Final[tuple[AnswerHopCase, ...]] = (
    # --- Row 3: a reply joins its question's section ------------------------------
    AnswerHopCase(
        "joins",
        ((QUESTION, CLINICIAN), (REPLY, PATIENT)),
        placed=((0, RED), (1, RED)),
    ),
    AnswerHopCase(
        # The reach is unlimited: every line of the reply speaker's turn joins.
        "joins-the-whole-turn",
        (
            (QUESTION, CLINICIAN),
            (REPLY, PATIENT),
            ("Not even at night.", PATIENT),
            ("Only the usual aches.", PATIENT),
        ),
        placed=((0, RED), (1, RED), (2, RED), (3, RED)),
    ),
    AnswerHopCase(
        # D1's row 4 at the unlimited reach: the second half of a reply the
        # recogniser split at a comma joins as a line of its own.
        "joins-a-reply-split-at-a-comma",
        (
            (QUESTION, CLINICIAN),
            ("No, not really,", PATIENT),
            ("only in the mornings.", PATIENT),
        ),
        placed=((0, RED), (1, RED), (2, RED)),
    ),
    AnswerHopCase(
        # "Yes." is never kept while "Actually …" is dropped.
        "joins-a-correction-after-a-reply",
        (
            (QUESTION, CLINICIAN),
            ("No.", PATIENT),
            ("Actually, a little in the left foot.", PATIENT),
        ),
        placed=((0, RED), (1, RED), (2, RED)),
    ),
    AnswerHopCase(
        # D1 (b): any speaker other than the confirmed clinician may reply.
        "joins-another-speakers-reply",
        ((QUESTION, CLINICIAN), ("None that I know of.", OTHER)),
        placed=((0, RED), (1, RED)),
    ),
    AnswerHopCase(
        # D2's named limit of G: with no sentence-ending mark between the
        # question and the statement the line is one sentence, so G repeats
        # D1's own tests and passes it.
        "joins-after-an-unmarked-question-and-statement",
        (("Do you have any numbness, I see it was there last time.", CLINICIAN), (REPLY, PATIENT)),
        placed=((0, RED), (1, RED)),
    ),
    AnswerHopCase(
        # D2's other named limit of G: "Dr." cuts a sentence, leaving a last
        # fragment that opens like a question and still holds the cue.
        "joins-after-an-abbreviation-leaves-a-question",
        (("Do you have any pain? Tell Dr. how your knee is sore.", CLINICIAN), (REPLY, PATIENT)),
        placed=((0, PRESENTING), (1, PRESENTING)),
    ),
    AnswerHopCase(
        # Task 0.6's accepted residue (3), pinned as behaviour: a patient's
        # "don't write this down" given as the FIRST reply is quoted.
        "joins-a-first-reply-dont-write-this-down",
        ((QUESTION, CLINICIAN), ("Sorry, no, don't write this down.", PATIENT)),
        placed=((0, RED), (1, RED)),
    ),
    AnswerHopCase(
        # The same instruction as a LATER line of the reply turn, after an
        # uncued first reply: the unlimited reach quotes it too. Pinned as
        # behaviour (review round 15 SEC-001); a named residue reported for
        # the practitioner's word at D.4, beside accepted residue (3).
        "joins-a-later-reply-dont-write-this-down",
        (
            (QUESTION, CLINICIAN),
            (REPLY, PATIENT),
            ("And please don't write this down.", PATIENT),
        ),
        placed=((0, RED), (1, RED), (2, RED)),
    ),
    # --- Row 3 refused: what does not join, and closes the window ------------------
    AnswerHopCase(
        # D1 (b): the clinician's own line is no reply; dropped, it closes
        # the window (row 5), so the reply after it is not joined.
        "the-clinicians-line-is-no-reply",
        ((QUESTION, CLINICIAN), ("Okay, good.", CLINICIAN), (REPLY, PATIENT)),
        placed=((0, RED),),
    ),
    AnswerHopCase(
        # From the second joined line on, only the first reply's speaker.
        "a-second-reply-speaker-closes",
        (
            (QUESTION, CLINICIAN),
            (REPLY, PATIENT),
            ("She has had none.", OTHER),
            ("Not even at night.", PATIENT),
        ),
        placed=((0, RED), (1, RED)),
    ),
    AnswerHopCase(
        # D1 (c): a reply that is itself a question is never quoted.
        "a-question-reply-closes",
        ((QUESTION, CLINICIAN), ("Why do you ask?", PATIENT), (REPLY, PATIENT)),
        placed=((0, RED),),
    ),
    AnswerHopCase(
        # D1 (c): a reply holding a suspect word is never quoted.
        "a-suspect-reply-closes",
        ((QUESTION, CLINICIAN), (REPLY, PATIENT), ("Not even at night.", PATIENT)),
        placed=((0, RED),),
        suspect=(1,),
    ),
    AnswerHopCase(
        # D1 (c): a cue of any section, even one routing refuses, keeps the
        # reply out (the ``ex-spoken-injection`` shape).
        "a-reply-with-a-refused-cue-closes",
        (
            (QUESTION, CLINICIAN),
            ("No, the diagnosis is fine.", PATIENT),
            ("Not even at night.", PATIENT),
        ),
        placed=((0, RED),),
    ),
    # --- Rows 1, 2 and 5 ----------------------------------------------------------
    AnswerHopCase(
        # Row 1: a textless segment is transparent.
        "a-textless-line-is-transparent",
        ((QUESTION, CLINICIAN), ("", OTHER), (REPLY, PATIENT)),
        placed=((0, RED), (2, RED)),
    ),
    AnswerHopCase(
        # Row 2: a cue routes the reply, as today, and the window closes.
        "a-cued-reply-routes-and-closes",
        (
            (QUESTION, CLINICIAN),
            ("It started two weeks ago.", PATIENT),
            (REPLY, PATIENT),
        ),
        placed=((0, RED), (1, HISTORY)),
    ),
    AnswerHopCase(
        # Row 2: the clinician's next cued question opens a window of its own.
        "a-cued-question-opens-its-own-window",
        (
            (QUESTION, CLINICIAN),
            ("Any tingling in your hands?", CLINICIAN),
            ("No, neither.", PATIENT),
        ),
        placed=((0, RED), (1, RED), (2, RED)),
    ),
    AnswerHopCase(
        # Row 5 and the scratch's reading (round 11 point 1): a joined reply
        # closes the bounded carry's chain, so the clinician's comma-split
        # second half after it is dropped, not carried across the reply.
        "a-joined-reply-closes-the-carry-chain",
        (
            ("Do you have any numbness,", CLINICIAN),
            ("No,", PATIENT),
            ("or tingling in your hands?", CLINICIAN),
        ),
        placed=((0, RED), (1, RED)),
    ),
    # --- D1 (a): where no window opens --------------------------------------------
    AnswerHopCase(
        # No confirmed clinician: the question still routes, nothing joins.
        "no-confirmed-clinician",
        ((QUESTION, CLINICIAN), (REPLY, PATIENT)),
        placed=((0, RED),),
        clinician=None,
    ),
    AnswerHopCase(
        # Inverted roles: a patient's question opens nothing.
        "a-patients-question-opens-nothing",
        ((QUESTION, PATIENT), (REPLY, CLINICIAN)),
        placed=((0, RED),),
    ),
    AnswerHopCase(
        # A question holding a suspect word still routes, and opens nothing.
        "a-suspect-question-opens-nothing",
        ((QUESTION, CLINICIAN), (REPLY, PATIENT)),
        placed=((0, RED),),
        suspect=(0,),
    ),
    AnswerHopCase(
        # A cue-routed statement opens nothing.
        "a-statement-opens-nothing",
        (("Any numbness in your feet.", CLINICIAN), (REPLY, PATIENT)),
        placed=((0, RED),),
    ),
    # --- Guard G ------------------------------------------------------------------
    AnswerHopCase(
        # The line is a question, but its last sentence is a statement.
        "g-a-last-statement-refuses",
        (("Do you have any numbness? I see it was there last time.", CLINICIAN), (REPLY, PATIENT)),
        placed=((0, RED),),
    ),
    AnswerHopCase(
        # The last sentence is a question, but alone it routes elsewhere.
        "g-a-last-question-routing-elsewhere-refuses",
        (("So the knee is sore. Any numbness?", CLINICIAN), (REPLY, PATIENT)),
        placed=((0, PRESENTING),),
    ),
    AnswerHopCase(
        # "Dr." cuts a sentence; here that usually makes G refuse.
        "g-an-abbreviation-usually-refuses",
        (("Do you have any pain in your knee, Dr. Lee asked.", CLINICIAN), (REPLY, PATIENT)),
        placed=((0, PRESENTING),),
    ),
    # --- Switch S -----------------------------------------------------------------
    AnswerHopCase(
        # The cue-routed line is a statement and its carried piece the
        # question: either piece makes the question, read as one line.
        "s-the-carried-piece-is-the-question",
        (
            ("Any numbness in your feet,", CLINICIAN),
            ("or in your hands?", CLINICIAN),
            ("No, neither.", PATIENT),
        ),
        placed=((0, RED), (1, RED), (2, RED)),
    ),
    AnswerHopCase(
        "s-the-cue-routed-piece-is-the-question",
        (
            ("Do you get any numbness,", CLINICIAN),
            ("mostly in the mornings.", CLINICIAN),
            ("No, never.", PATIENT),
        ),
        placed=((0, RED), (1, RED), (2, RED)),
    ),
    AnswerHopCase(
        # Its twin with a suspect word in the carried piece (review round 17
        # PR-LOW-020): the piece is still carried, but S opens no window when
        # any piece holds a suspect word, so the reply is dropped.
        "s-a-suspect-carried-piece-opens-nothing",
        (
            ("Do you get any numbness,", CLINICIAN),
            ("mostly in the mornings.", CLINICIAN),
            ("No, never.", PATIENT),
        ),
        placed=((0, RED), (1, RED)),
        suspect=(1,),
    ),
    AnswerHopCase(
        # With G, the two pieces are read as one line: a carried correction
        # ending in a statement is that line's last sentence, so G refuses.
        "s-the-guard-reads-both-pieces",
        (
            (QUESTION, CLINICIAN),
            ("Actually, I mean in your hands.", CLINICIAN),
            (REPLY, PATIENT),
        ),
        placed=((0, RED), (1, RED)),
    ),
)
