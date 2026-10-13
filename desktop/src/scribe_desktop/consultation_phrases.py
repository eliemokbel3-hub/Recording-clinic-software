"""The consultation phrase lists (validation-pass plan D1, Task 0.8; C3).

ONE home for the closing and greeting phrases, shared by the live
new-consultation warning (``voice_commands.NewConsultationWatcher``, which
re-exports both lists — Cliniko workflow safeguards plan D8) and, from the
validation-pass plan's Phase 1, the offline next-patient boundary. One list
feeds both, so the warning and the boundary never disagree on vocabulary.

A LEAF module: it may import only ``note`` and ``transcription`` (C6).
``voice_commands`` imports ``session``, which reaches ``note_config``
through ``draft_write``, so the note modules can never import the lists
from there; they import them from here.

THE VOCABULARY IS FROZEN (C3): these lists are the ones the safeguards plan
shipped on 2026-09-28, moved unchanged on 2026-10-13 (the practitioner's
decision 0.2 (a): no phrases of their own yet). Every phrase is lower-case
and already in ``voice_commands.phrase_tokens``'s whole-word form. Any
change is a new dated decision with a repeated validation run, and the
exact pins in ``tests/test_vocabulary.py`` move with it.

Nothing here logs, and nothing here holds transcript text.
"""

from __future__ import annotations

from typing import Final

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
