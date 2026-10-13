"""The consultation phrase lists and the next-patient boundary
(validation-pass plan D1 and D2, Tasks 0.8 and 1.1; C3, C5, C6).

ONE home for the closing and greeting phrases, shared by the live
new-consultation warning (``voice_commands.NewConsultationWatcher``, which
re-exports both lists — Cliniko workflow safeguards plan D8) and the offline
next-patient boundary (``consultation_boundary``). One list, one word-to-token
function and one phrase-event helper feed both, so the warning and the
boundary never disagree on vocabulary or on what counts as a word.

A LEAF module: it imports only ``note`` and ``transcription`` (C6).
``voice_commands`` imports ``session``, which reaches ``note_config``
through ``draft_write``, so the note modules can never import the lists
from there; they import them from here.

THE VOCABULARY IS FROZEN (C3): these lists are the ones the safeguards plan
shipped on 2026-09-28, moved unchanged on 2026-10-13 (the practitioner's
decision 0.2 (a): no phrases of their own yet). Every phrase is lower-case
and already in ``phrase_tokens``'s whole-word form. Any change is a new
dated decision with a repeated validation run, and the exact pins in
``tests/test_vocabulary.py`` move with it.

THE BOUNDARY (D2). ``consultation_boundary`` returns the absolute index of
the first segment to WITHHOLD from the note — a possible next patient starts
there — or None. It looks for the FIRST non-transparent segment S that holds
a greeting, with a closing earlier in S or in one of the
``BOUNDARY_SEGMENTS`` non-transparent segments before S, and some
non-transparent segment before that closing's segment holding a cue of
either layer (``note.any_cue_matches`` — the head-case guard: a recording
started while the previous patient leaves is never cut). A ONE-word
greeting ("hello") counts only as the first token of its segment or of a
sentence (after a word ending ``.``, ``?`` or ``!``), and only when
punctuation or the segment's end follows it; a longer greeting counts
anywhere in its segment. The cut is S itself when the closing sits in an
earlier segment; when S holds a closing BEFORE one of its greetings the cut
is the NEXT non-transparent segment instead, or None when none follows —
and that same-segment pairing wins even when a window closing exists too
(the reading that fails toward inclusion, dated 2026-10-13 on D2 and Task
1.1). Role-free and deterministic: whoever speaks, from the document and
the cues alone. Transparent segments (no word with text) are skipped and
never counted.

SUSPECT WORDS (the invented-text guard's D6). Phrases are read through the
live watcher's own per-word token function (``word_tokens`` flattens it),
which drops a word the transcription guard marked ``suspect``: a suspect
closing or greeting supplies no phrase. Suspect segments stay
non-transparent, so they still count in the window, and the head-case cue
test reads every word, as the router does. The boundary reads each segment's
tokens ON THEIR OWN, so none of its phrases spans two segments: D2's named
straddle residue (a phrase across a wholly suspect segment) is the live
rules' alone, which read a window's segments as one run.

Nothing here logs, and nothing here returns transcript text: the boundary
is one index.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Literal

from scribe_desktop.note import (
    # Package-private by name, shared deliberately (the note.py convention):
    # the closing quotes and brackets the carry peels off a word before
    # reading its last mark — one set, so the two readers of a word's
    # trailing punctuation cannot drift apart.
    _CLOSING_MARKS,
    NoteSectionKey,
    any_cue_matches,
    content_tokens,
    normalise_token,
    reconstruct_span_text,
)
from scribe_desktop.transcription import TranscriptDocument, TranscriptSegment

CLOSING_PHRASES: Final[tuple[str, ...]] = (
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
GREETING_PHRASES: Final[tuple[str, ...]] = (
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

# The next-patient boundary's look-back (D1, D2 condition 2): a closing phrase
# counts when it sits in the greeting's own segment or in one of this many
# NON-TRANSPARENT segments before it. A separate constant from
# ``voice_commands.NEW_CONSULTATION_WINDOWS``, which counts LIVE WINDOWS — a
# window holds several segments, so the two numbers measure different things.
BOUNDARY_SEGMENTS: Final = 3

Cues = Mapping[NoteSectionKey, tuple[tuple[str, ...], ...]]
PhraseKind = Literal["closing", "greeting"]

# Splits a word into parts only; each part is then normalised by THE one
# normaliser, ``note.normalise_token`` (Task 1.2's single-implementation pin).
_PART_SPLIT_RE: Final = re.compile(r"[\s/\-‐-―]+")
# What ends a sentence for D2's one-word greeting rule (Task 0.9 reading 2).
_SENTENCE_END: Final = ".?!"


def phrase_tokens(text: str) -> list[str]:
    """``text`` as whole-word tokens: split on whitespace, hyphens and
    slashes, each part normalised by ``note.normalise_token`` (its outer
    punctuation stripped, lower-cased); empty parts dropped."""
    return [token for token in map(normalise_token, _PART_SPLIT_RE.split(text)) if token]


def _phrase(text: str) -> tuple[str, ...]:
    return tuple(phrase_tokens(text))


_CLOSINGS: Final = tuple(_phrase(p) for p in CLOSING_PHRASES)
_GREETINGS: Final = tuple(_phrase(p) for p in GREETING_PHRASES)


@dataclass(frozen=True)
class PhraseToken:
    """One whole-word token of a word, with its word's start time on the
    captured-audio timeline and the two position facts D2's one-word
    greeting rule reads, both within the token's own SEGMENT:
    ``sentence_start`` — the first token of the segment, or the first after
    a word ending ``.``, ``?`` or ``!``; ``punctuation_after`` — the word
    ends in punctuation right after this token, or it is the segment's last
    token. Neither is read by the live rules."""

    text: str
    start_seconds: float
    sentence_start: bool = False
    punctuation_after: bool = False


def _segment_tokens(segment: TranscriptSegment) -> list[PhraseToken]:
    out: list[PhraseToken] = []
    starts_sentence = True
    for word in segment.transcript_words:
        if word.suspect:
            continue
        raw = word.word_text.strip().rstrip(_CLOSING_MARKS)
        ends_punctuated = bool(raw) and not raw[-1].isalnum()
        ends_sentence = bool(raw) and raw[-1] in _SENTENCE_END
        parts = phrase_tokens(word.word_text)
        if not parts:
            # A word of punctuation alone ("-", "..."): it punctuates the
            # token before it, and may end a sentence.
            if ends_punctuated and out:
                last = out[-1]
                out[-1] = PhraseToken(last.text, last.start_seconds, last.sentence_start, True)
            if ends_sentence:
                starts_sentence = True
            continue
        for index, part in enumerate(parts):
            out.append(
                PhraseToken(
                    part,
                    word.start_seconds,
                    sentence_start=starts_sentence and index == 0,
                    punctuation_after=index == len(parts) - 1 and ends_punctuated,
                )
            )
        starts_sentence = ends_sentence
    if out:
        last = out[-1]
        out[-1] = PhraseToken(last.text, last.start_seconds, last.sentence_start, True)
    return out


def word_tokens(segments: Iterable[TranscriptSegment]) -> list[PhraseToken]:
    """Every word's tokens in order, each carrying its word's start time —
    except a ``suspect`` word's (invented-text guard D6): words the guard
    marks as possibly not speech never pause the recording, raise the
    new-consultation warning or supply a boundary phrase. A suspect word is
    dropped, not a barrier (unlike ``note_fill``'s trigger match). The guard
    marks whole segments, so dropping one joins the words either side of it:
    across segments, as the live rules read them, a phrase can now match
    across a suspect segment between two real ones ("scribe" | burst |
    "pause") — an extra pause or warning, the safe direction (the threat
    model's surface 5 names it). The boundary reads one segment at a time, so
    it never joins words across segments."""
    return [token for segment in segments for token in _segment_tokens(segment)]


def phrase_starts(tokens: Sequence[PhraseToken], phrase: tuple[str, ...]) -> list[int]:
    """Where ``phrase`` starts in ``tokens`` (whole tokens, in a row)."""
    size = len(phrase)
    texts = [token.text for token in tokens]
    return [i for i in range(len(texts) - size + 1) if tuple(texts[i : i + size]) == phrase]


def phrase_events(
    tokens: Sequence[PhraseToken], *, positional: bool
) -> list[tuple[int, PhraseKind]]:
    """THE phrase-event helper (D1): every closing and greeting phrase in
    ``tokens`` as ``(token position, kind)``, in token order (a closing before
    a greeting at one position). ``positional`` applies D2's one-word rule — a
    ONE-word greeting counts only when it starts its segment or a sentence AND
    punctuation or the segment's end follows it. The live warning passes
    False (its behaviour changes only by the vocabulary commit, C7); the
    boundary passes True."""
    events: list[tuple[int, PhraseKind]] = [
        (i, "closing") for phrase in _CLOSINGS for i in phrase_starts(tokens, phrase)
    ]
    for phrase in _GREETINGS:
        for i in phrase_starts(tokens, phrase):
            if (
                not positional
                or len(phrase) > 1
                or (tokens[i].sentence_start and tokens[i].punctuation_after)
            ):
                events.append((i, "greeting"))
    return sorted(events)


def _spoken(segment: TranscriptSegment) -> bool:
    """Non-transparent (D2): the segment has a word with text — the
    provider's own test for an utterance it can quote."""
    return bool(reconstruct_span_text(segment.transcript_words))


def consultation_boundary(
    document: TranscriptDocument, cues: Cues, fallback_cues: Cues
) -> int | None:
    """THE next-patient boundary (D2; module docstring): the absolute index
    of the first segment to withhold, always a non-transparent segment, or
    None. ``cues`` is the canonical config's own (``normalised_cues()``) and
    ``fallback_cues`` the shipped ones; every consumer reaches this through
    ``note_config.next_patient_boundary`` (C5), never with cues of its own."""
    segments = document.transcript_segments
    spoken = [index for index, segment in enumerate(segments) if _spoken(segment)]
    closings: dict[int, list[int]] = {}
    greetings: dict[int, list[int]] = {}
    # ``content_before[k]``: some spoken segment before ``spoken[k]`` holds a
    # cue of either layer (D2 condition 3, read over every word).
    content_before: list[bool] = []
    seen_cue = False
    for index in spoken:
        events = phrase_events(_segment_tokens(segments[index]), positional=True)
        closings[index] = [at for at, kind in events if kind == "closing"]
        greetings[index] = [at for at, kind in events if kind == "greeting"]
        content_before.append(seen_cue)
        text = reconstruct_span_text(segments[index].transcript_words)
        seen_cue = seen_cue or any_cue_matches(cues, fallback_cues, content_tokens(text))
    for k, index in enumerate(spoken):
        if not greetings[index]:
            continue
        # The NEAREST closing first — the head-case guard only weakens toward
        # it, so when it fails, every earlier closing fails too.
        if closings[index] and min(closings[index]) < max(greetings[index]):
            if content_before[k]:
                return spoken[k + 1] if k + 1 < len(spoken) else None
            continue
        for j in range(k - 1, max(0, k - BOUNDARY_SEGMENTS) - 1, -1):
            if closings[spoken[j]]:
                if content_before[j]:
                    return index
                break
    return None


__all__ = [
    "BOUNDARY_SEGMENTS",
    "CLOSING_PHRASES",
    "GREETING_PHRASES",
    "PhraseKind",
    "PhraseToken",
    "consultation_boundary",
    "phrase_events",
    "phrase_starts",
    "phrase_tokens",
    "word_tokens",
]
