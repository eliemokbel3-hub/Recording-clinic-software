"""Phrase rules over the live transcript (Cliniko workflow safeguards plan
Tasks 7.2 and 7.3; D7 and D8).

Qt-free and GUI-thread-only: the main window feeds each live window (the
``TranscriptScreen.live_window`` signal's tuple of segments) to both rules
and applies what they decide. Nothing here touches the controller, a key or
the disk, nothing here logs, and nothing here changes the transcript — the
spoken phrase stays in it like any other words.

THE SPOKEN PAUSE (D7). ``SpokenPauseDetector`` finds the phrase "scribe
pause" in the words' tokens: each token is a whole word (a word split only
at whitespace, hyphens and slashes, each part normalised by the app's one
normaliser, ``note.normalise_token`` — outer punctuation stripped,
lower-cased), so "prescribe, pause" — whose first token
is "prescribe" — never matches, and neither does "scribe paused". A match
counts only if the phrase's FIRST word starts at or after the resume cutoff:
the captured-audio time of the last Resume plus one capture chunk (up to a
chunk of audio from before the Pause is still buffered in the capture worker
at the Resume, and it reaches the transcript AFTER the Resume). The window's
own end time is never the test, because one window can span a Pause and a
Resume. A phrase split across two windows is found through the one token
carried from the previous window, when its two words start no more than
``CARRY_MAX_GAP_SECONDS`` apart — a window closed by a longer silence never
joins the next. The speaker is never checked: anyone in the
room can say it, and all it can do is pause.

LATENCY. The phrase is heard only when live transcription reaches it: its
speech segment must end, its window must close (after a silence of more than
``TRANSCRIBE_WINDOW_MAX_GAP_SECONDS``, or when ``TRANSCRIBE_WINDOW_SECONDS`` of
speech has built up), and the window must be transcribed. So the pause comes
a few seconds after the practitioner stops speaking, and up to about half a
minute plus the transcription time when speech runs on; what is said in
between is recorded. A Resume always needs the hotkey or a click.

THE NEW-CONSULTATION WARNING (D8). ``NewConsultationWatcher`` raises once per
recording when a closing phrase is followed, in the same window or within
``NEW_CONSULTATION_WINDOWS`` windows after it, by a greeting. It is a WARNING
only: it never pauses, blocks or changes a session.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final, Literal

from scribe_desktop.audio_capture import CHANNELS, CHUNK_BYTES, SAMPLE_RATE, SAMPLE_WIDTH
from scribe_desktop.consultation_phrases import CLOSING_PHRASES as CLOSING_PHRASES
from scribe_desktop.consultation_phrases import GREETING_PHRASES as GREETING_PHRASES
from scribe_desktop.consultation_phrases import (
    PhraseToken,
    phrase_events,
    phrase_starts,
    word_tokens,
)
from scribe_desktop.consultation_phrases import phrase_tokens as phrase_tokens
from scribe_desktop.session import CAPTURING_STATES, SessionState
from scribe_desktop.transcription import (
    TRANSCRIBE_WINDOW_MAX_GAP_SECONDS,
    LiveFailure,
    TranscriptSegment,
)

SPOKEN_PAUSE_PHRASE: Final[tuple[str, ...]] = ("scribe", "pause")
# One capture chunk (~1 s): the most pre-Pause audio the capture worker can
# still hold when Resume returns.
RESUME_CUTOFF_MARGIN_SECONDS: Final = CHUNK_BYTES / (SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH)
# The carried word joins the next window's first word only across a gap no
# longer than the silence that would have closed a window (round 41 LOW-033).
CARRY_MAX_GAP_SECONDS: Final = TRANSCRIBE_WINDOW_MAX_GAP_SECONDS

NEW_CONSULTATION_WARNING: Final = "new_consultation"
NEW_CONSULTATION_WINDOWS: Final = 3
# ``CLOSING_PHRASES``, ``GREETING_PHRASES`` and ``phrase_tokens`` live in the
# leaf module ``consultation_phrases`` (validation-pass plan D1) and are
# re-exported from the imports above; both rules here read words through its
# ``word_tokens`` (a ``suspect`` word dropped — invented-text guard D6) and
# the watcher reads phrases through its ``phrase_events``, so the live
# warning and the offline next-patient boundary share one list, one token
# function and one event helper.

SpokenPauseState = Literal["idle", "on", "unavailable"]


def spoken_pause_state(
    state: SessionState, *, attached: bool, failure: LiveFailure | None
) -> SpokenPauseState:
    """D7's availability: ``idle`` with no recording, ``on`` while a
    recording's live transcriber runs, else ``unavailable`` (live
    transcription off for this recording, or it has stopped)."""
    if state not in CAPTURING_STATES:
        return "idle"
    return "on" if attached and failure is None else "unavailable"


class SpokenPauseDetector:
    """D7's matcher for ONE recording (``reset`` at every Start)."""

    def __init__(self) -> None:
        self._cutoff = 0.0
        self._carry: PhraseToken | None = None

    @property
    def cutoff_seconds(self) -> float:
        return self._cutoff

    def reset(self) -> None:
        self._cutoff = 0.0
        self._carry = None

    def note_resume(self, captured_seconds: float) -> None:
        """A Resume succeeded with ``captured_seconds`` of audio written:
        nothing said before it may pause the recording again."""
        self._cutoff = max(self._cutoff, captured_seconds + RESUME_CUTOFF_MARGIN_SECONDS)
        self._carry = None

    def feed(self, segments: Iterable[TranscriptSegment]) -> bool:
        """True when this window holds the phrase spoken after the cutoff."""
        tokens = word_tokens(segments)
        carry = self._carry
        if (
            carry is not None
            and tokens
            and tokens[0].start_seconds - carry.start_seconds > CARRY_MAX_GAP_SECONDS
        ):
            carry = None  # a silence closed the last window: not one phrase
        stream = ([carry] if carry is not None else []) + tokens
        if tokens:
            self._carry = tokens[-1]
        return any(
            stream[i].start_seconds >= self._cutoff
            for i in phrase_starts(stream, SPOKEN_PAUSE_PHRASE)
        )


class NewConsultationWatcher:
    """D8's rule for ONE recording (``reset`` at every Start)."""

    def __init__(self, windows: int = NEW_CONSULTATION_WINDOWS) -> None:
        self._windows = windows
        self._index = 0
        self._closing_at: int | None = None
        self._raised = False

    @property
    def raised(self) -> bool:
        return self._raised

    def reset(self) -> None:
        self._index = 0
        self._closing_at = None
        self._raised = False

    def feed(self, segments: Iterable[TranscriptSegment]) -> bool:
        """True exactly once: when a greeting follows a closing phrase within
        the window budget."""
        # Every greeting counts here, wherever it sits: D2's one-word position
        # rule is the boundary's alone (C7 — the live warning is unchanged).
        events = phrase_events(word_tokens(segments), positional=False)
        index = self._index
        self._index += 1
        for _position, kind in events:
            if kind == "closing":
                self._closing_at = index
            elif (
                not self._raised
                and self._closing_at is not None
                and index - self._closing_at <= self._windows
            ):
                self._raised = True
                return True
        return False
