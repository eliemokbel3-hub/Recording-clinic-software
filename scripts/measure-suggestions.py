"""Measure the section-suggestion stage at text level (suggestion-repair plan
Task 0.2; D2, D4, D7, D9; C1-C4, C9-C11).

For every synthetic script in each named set folder this builds the note the
app would build from the script's OWN words (``validation.reference_document``:
one segment per line, the role as its speaker, so the clinician is
confirmed) exactly as the validation harness's ``--suggestions confirm-all``
pass builds it, asks the SHIPPED stage (``ui.models.build_suggestion_stage``,
unchanged) about every left-out line through a recorder wrapped around the
one loaded model (the ``measure-prose-fixtures.py`` pattern: the recorder
lives HERE, outside the package, so the package's one model call site per
stage stays the only one — C4), accepts every suggestion the chooser's
ownership rule accepts (``validation.suggestion_pass`` itself) and judges the
facts with ``validation.encounter_metrics``. It prints numbers only:

- how each completion line is shaped and how the shipped parser read it,
  split by the confirmed clinician's lines (W) and the others' (U, by role);
- what happened to the lines holding a material fact the reference reading
  leaves out silently, and the facts still silent once every suggestion is
  accepted;
- the harm counts (facts wrongly present via a suggestion; suggestions on a
  next patient's lines with no boundary detected);
- the stage's own counts (lines asked, not assessed, accepted W / U,
  dropped, model calls, fit reductions), its version, the model id, seconds;
- the answer-budget evidence: every answer word's full answer line, and the
  bound ``L`` on one bounded answer line with the budget table for 1 to 40
  asked lines (``answer_token_budget(n)`` beside ``n x L``).

    .venv\\Scripts\\python.exe scripts\\measure-suggestions.py <set folder> [<set folder> ...]
        --config validation\\config [--verbose] [--timing] [--source-root <folder>] < /dev/null

``--timing`` (D7) measures instead ONE completion over a constructed window of
40 asked lines (the named sets' reference lines, in name order, joined until
40 are asked) and prints the seconds, the completion's tokens and three
identity lines: the imported ``note_suggest`` module's file, its
``SUGGEST_PROMPT_VERSION`` and a SHA-256 of the window's lines (text and
placement, before the stage's instruction). A pair of timings counts only
when the two module files differ as intended, the versions are the expected
ones and the two hashes are equal. ``--source-root`` names the package folder
put first on the import path before ``scribe_desktop`` is imported (default:
this repository's ``desktop/src``) — a detached worktree's for the v1 side.

``--verbose`` also prints each window's raw completion (synthetic text) to
the console; run it in the foreground only (C9).

Custody (C1, C2): synthetic scripts only — a set holding any script without
synthetic ``conditions`` is refused whole, naming the id, before any model is
loaded. Developer build only. It reads only the named set and ``--config``
folders and the language model; it writes no file and calls no logger; the
prompts and completions live in memory for one encounter at a time. The
default report holds counts, ids, section keys and the stage's version only.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import string
import sys
import time
from collections import Counter
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from scribe_desktop.language_model import LanguageModel
    from scribe_desktop.note import NoteDraft
    from scribe_desktop.note_config import NoteConfig
    from scribe_desktop.note_suggest import SuggestionInput, SuggestionLine
    from scribe_desktop.speech import TranscribedWord
    from scribe_desktop.transcription import TranscriptDocument
    from scribe_desktop.ui.models import SuggestionStage, SuggestionStageOutcome
    from scribe_desktop.validation import EncounterScript, HarnessInputs

REPO: Final = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_ROOT: Final = REPO / "desktop" / "src"

# D7: the constructed timing window holds this many asked lines.
TIMING_ASKED_LINES: Final = 40
# The two numbers each answer word's full line is counted at (one digit, two).
ONE_DIGIT_NUMBER: Final = 9
TWO_DIGIT_NUMBER: Final = 40


class MeasurementError(Exception):
    """A fixed-text failure of the measurement itself (never a script's or a
    completion's words)."""


def use_source_root(root: Path) -> None:
    """D7: ``root`` first on the import path, before ``scribe_desktop`` is
    imported (a package already imported in this process stays as it is —
    ``--timing``'s module line shows which one ran)."""
    path = str(root.resolve())
    if sys.path[:1] != [path]:
        sys.path.insert(0, path)


# ---------------------------------------------------------------------------
# The recorder (D2): between the shipped stage and the one loaded model.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CountEvent:
    """One ``count_tokens`` call the stage made, in call order."""

    text: str


@dataclass(frozen=True)
class CallEvent:
    """One ``complete`` call the stage made: its user text, its answer
    budget and the completion (None when the call raised)."""

    user_text: str
    max_tokens: int
    completion: str | None


class RecordingModel:
    """The loaded model, with every call the stage makes recorded in order —
    held in memory for one encounter (``measure_script`` clears it), never
    written or logged. ``inner`` is the model itself: the budget evidence and
    the cut-at-budget inference count through it, unrecorded."""

    def __init__(self, inner: LanguageModel) -> None:
        self.inner = inner
        self.events: list[CountEvent | CallEvent] = []

    @property
    def model_id(self) -> str:
        return self.inner.model_id

    def complete(self, *, system_text: str, user_text: str, max_tokens: int) -> str:
        completion: str | None = None
        try:
            completion = self.inner.complete(
                system_text=system_text, user_text=user_text, max_tokens=max_tokens
            )
            return completion
        finally:
            self.events.append(CallEvent(user_text, max_tokens, completion))

    def count_tokens(self, text: str) -> int:
        self.events.append(CountEvent(text))
        return self.inner.count_tokens(text)


class CapturingStage:
    """The shipped stage callable, with the input ``suggestion_pass`` built
    for it and the outcome it returned kept for the measurement."""

    def __init__(self, inner: SuggestionStage) -> None:
        self._inner = inner
        self.suggestion_input: SuggestionInput | None = None
        self.outcome: SuggestionStageOutcome | None = None

    def __call__(
        self,
        suggestion_input: SuggestionInput,
        /,
        *,
        abort: Callable[[], bool] | None = None,
        yield_to: Callable[[], None] | None = None,
    ) -> SuggestionStageOutcome:
        self.suggestion_input = suggestion_input
        self.outcome = self._inner(suggestion_input, abort=abort, yield_to=yield_to)
        return self.outcome


def _window_rows(text: str) -> list[str] | None:
    """The numbered rows of a window's user text, or None for any other text
    the stage counted (its instruction)."""
    from scribe_desktop.note_suggest import SUGGEST_LINES_END, SUGGEST_LINES_HEADER

    rows = text.split("\n")
    if rows[0] != SUGGEST_LINES_HEADER or SUGGEST_LINES_END not in rows:
        return None
    return rows[1 : rows.index(SUGGEST_LINES_END)]


def fit_reductions(events: Sequence[CountEvent | CallEvent]) -> int:
    """Every time ``_fit_window`` shortened a candidate, read from the stage's
    own token counts of window texts: within one candidate's fit, each count
    after the first is one reduction. A reduction is the count straight after
    a window count, with no model call between, whose rows are the first
    half of that window's rows (``_fit_window`` halves and numbers from 1
    again) — so a halved prefix holding only context lines (no call follows)
    and repeated reductions of one candidate are both counted."""
    count = 0
    for before, after in zip(events, events[1:], strict=False):
        if not (isinstance(before, CountEvent) and isinstance(after, CountEvent)):
            continue
        first, second = _window_rows(before.text), _window_rows(after.text)
        if first is None or second is None or len(first) < 2:
            continue
        if second == first[: len(first) // 2]:
            count += 1
    return count


def match_windows(
    calls: Sequence[CallEvent], lines: Sequence[SuggestionLine]
) -> list[dict[int, int]]:
    """Each model call's asked numbers (window number -> segment index), by
    finding the contiguous slice of the input whose prompt
    (``build_window_prompt``, the stage's own builder) is the call's user
    text. Windows run in transcript order, so each search starts where the
    previous window ended."""
    from scribe_desktop.note_suggest import SUGGESTION_WINDOW_SEGMENTS, build_window_prompt

    found: list[dict[int, int]] = []
    cursor = 0
    for call in calls:
        match: tuple[int, int, dict[int, int]] | None = None
        for start in range(cursor, len(lines)):
            for size in range(1, min(SUGGESTION_WINDOW_SEGMENTS, len(lines) - start) + 1):
                text, asked = build_window_prompt(lines[start : start + size])
                if text == call.user_text:
                    match = (start, size, asked)
                    break
            if match is not None:
                break
        if match is None:
            raise MeasurementError("a model call's window does not match the input")
        start, size, asked = match
        found.append(asked)
        cursor = start + size
    return found


# ---------------------------------------------------------------------------
# The shape classifier.
# ---------------------------------------------------------------------------

UNATTRIBUTABLE: Final = "unattributable"
SHAPES: Final[tuple[tuple[str, str], ...]] = (
    ("valid_key", "valid key"),
    ("valid_none", "valid `none`"),
    ("number_question", "number followed by `?`"),
    ("unknown_key", "unknown key"),
    ("case_or_punctuation", "capitals or trailing punctuation on a valid key"),
    ("extra_words", "extra words after a key"),
    ("not_answer", "not an answer line"),
)
_LEADING_NUMBER_RE: Final = re.compile(r"^\s*([0-9]{1,4})(.*)$")
_AFTER_NUMBER_RE: Final = re.compile(r"^\s*(\?)?\s*[.):-]?\s*(.*)$")
_KEY_LIKE_RE: Final = re.compile(r"^[a-z_]+$")
_TRAILING_PUNCTUATION: Final = string.punctuation.replace("_", "")


def classify_line(line: str, asked: Collection[int]) -> tuple[int | None, str]:
    """``(window number, shape)`` for one completion line. The line is
    attributed ONLY through the window's asked numbers: a line with no
    leading number, or a number the window did not ask, is ``(None,
    UNATTRIBUTABLE)``. An attributed line the SHIPPED parser reads is a
    valid key or a valid ``none`` (so the shapes follow the parser of the
    stage under measurement); any other is, in this order: extra words after
    a key or ``none``; the number followed by ``?`` (whatever the key's
    casing or trailing punctuation); capitals or trailing punctuation on a
    key or ``none``; an unknown key (one key-like word); else not an answer
    line — an echo of either prompt line shape among them."""
    from scribe_desktop.note import CANONICAL_SECTION_KEYS
    from scribe_desktop.note_suggest import ANSWER_NONE, parse_suggestions

    leading = _LEADING_NUMBER_RE.match(line)
    if leading is None:
        return None, UNATTRIBUTABLE
    number = int(leading.group(1))
    if number not in asked:
        return None, UNATTRIBUTABLE
    parsed = parse_suggestions(line, (number,))
    if parsed is not None and number in parsed:
        return number, "valid_key" if parsed[number] is not None else "valid_none"
    after = _AFTER_NUMBER_RE.match(leading.group(2))
    if after is None:  # unreachable: the pattern matches any text
        return number, "not_answer"
    words = after.group(2).split()
    if not words:
        return number, "not_answer"
    first, extra = words[0], words[1:]
    core = first.rstrip(_TRAILING_PUNCTUATION).casefold()
    if core == ANSWER_NONE or core in CANONICAL_SECTION_KEYS:
        if extra:
            return number, "extra_words"
        if after.group(1) is not None:
            return number, "number_question"
        if core != first:
            return number, "case_or_punctuation"
        return number, "not_answer"
    if not extra and _KEY_LIKE_RE.fullmatch(core):
        return number, "unknown_key"
    return number, "not_answer"


# ---------------------------------------------------------------------------
# One script.
# ---------------------------------------------------------------------------

COLUMNS: Final[tuple[tuple[str, str], ...]] = (
    ("W", "W"),
    ("patient", "U: patient"),
    ("next_patient", "U: next_patient"),
    ("other", "U: other roles"),
)
READINGS: Final[tuple[tuple[str, str], ...]] = (
    ("key", "got a key"),
    ("none", "got `none`"),
    ("unread", "an unread answer"),
    ("no_answer", "no answer"),
    ("not_asked", "not asked (placed, past the boundary or wordless)"),
)


@dataclass
class Tally:
    """Counts only: one script's, or a set's once added up."""

    scripts: int = 0
    shapes: Counter[tuple[str, str]] = field(default_factory=Counter)
    readings: Counter[str] = field(default_factory=Counter)
    counts: Counter[str] = field(default_factory=Counter)
    still_silent: list[str] = field(default_factory=list)
    stage_seconds: float = 0.0
    model_id: str | None = None
    prompt_version: str | None = None

    def add(self, other: Tally) -> None:
        self.scripts += other.scripts
        self.shapes.update(other.shapes)
        self.readings.update(other.readings)
        self.counts.update(other.counts)
        self.still_silent.extend(other.still_silent)
        self.stage_seconds += other.stage_seconds
        self.model_id = self.model_id or other.model_id
        self.prompt_version = self.prompt_version or other.prompt_version


class _NoSpeech:
    """``HarnessInputs`` needs a speech provider; text level transcribes
    nothing."""

    model_name = "none"

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        raise MeasurementError("the suggestion measurement transcribes nothing")


def _no_frames(frame: bytes) -> float:
    raise MeasurementError("the suggestion measurement reads no audio")


def harness_inputs(config: NoteConfig) -> HarnessInputs:
    """The harness's inputs for text level: the config, the default
    extractive provider, and stubs that raise for the audio seams."""
    from scribe_desktop.validation import HarnessInputs

    return HarnessInputs(provider=_NoSpeech(), frame_probability=_no_frames, config=config)


def build_input(
    script: EncounterScript, inputs: HarnessInputs, now: datetime
) -> tuple[TranscriptDocument, NoteDraft, SuggestionInput]:
    """The reference transcript, its draft and the suggestion input, built as
    ``validation.suggestion_pass`` builds them (the plan's "Building the
    tool's input exactly as the harness does")."""
    from scribe_desktop import validation
    from scribe_desktop.note_config import build_note_request
    from scribe_desktop.note_suggest import SuggestionInput
    from scribe_desktop.speaker_eval import CLINICIAN_LABEL
    from scribe_desktop.ui.models import placed_segments

    document = validation.reference_document(script)
    draft = validation._compose_draft(document, CLINICIAN_LABEL, inputs, now)
    placed = placed_segments(draft.note_sections)
    request = build_note_request(
        document, inputs.config, draft.template_profile_id, clinician_speaker=CLINICIAN_LABEL
    )
    suggestion_input = SuggestionInput.from_request(
        request, in_note=placed, clinician_speaker=CLINICIAN_LABEL
    )
    return document, draft, suggestion_input


def _column(line: SuggestionLine, script: EncounterScript) -> str:
    if line.by_clinician:
        return "W"
    role = script.lines[line.segment_index].role
    return role if role in ("patient", "next_patient") else "other"


def _tally_window(
    call: CallEvent,
    asked: Mapping[int, int],
    by_segment: Mapping[int, SuggestionLine],
    script: EncounterScript,
    model: LanguageModel,
    tally: Tally,
    readings: dict[int, str],
) -> None:
    """One model call's completion: each line's shape, the asked numbers no
    line answered, the cut-at-budget inference (D2: the completion's token
    count reached ``max_tokens - 1`` and the window's last asked number has
    no answer line), the whole-completion refusal, and each asked line's
    reading. An ANSWER line is an attributed line of any shape but "not an
    answer line" (review round 8 MED-001): an echo of a prompt line, or a
    bare number, answers nothing."""
    from scribe_desktop.language_model import LanguageModelError, strip_think_blocks
    from scribe_desktop.note_suggest import parse_suggestions

    completion = call.completion
    if completion is None:
        # The call raised (the stage counts the failed window): every number
        # it asked went unanswered (codex round 10 PR-LOW-013).
        tally.counts["no_answer_numbers"] += len(asked)
        for segment in asked.values():
            readings[segment] = "no_answer"
        return
    stripped = strip_think_blocks(completion)
    body = completion if stripped is None else stripped
    answered: set[int] = set()
    for line in body.splitlines():
        if not line.strip():
            continue
        number, shape = classify_line(line, asked)
        if number is None:
            tally.counts["unattributable"] += 1
            continue
        if shape != "not_answer":
            answered.add(number)
        tally.shapes[(shape, _column(by_segment[asked[number]], script))] += 1
    tally.counts["no_answer_numbers"] += sum(1 for number in asked if number not in answered)
    parsed = parse_suggestions(completion, asked)
    if parsed is None:
        tally.counts["refused"] += 1
    tokens: int | None
    try:
        tokens = model.count_tokens(completion)
    except LanguageModelError:
        tokens = None
    if (
        tokens is not None
        and asked
        and tokens >= call.max_tokens - 1
        and max(asked) not in answered
    ):
        tally.counts["cut_at_budget"] += 1
    for number, segment in asked.items():
        if parsed is not None and number in parsed:
            readings[segment] = "key" if parsed[number] is not None else "none"
        elif number in answered:
            readings[segment] = "unread"
        else:
            readings[segment] = "no_answer"


def _print_completion(encounter_id: str, window: int, call: CallEvent, asked: int) -> None:
    print(f"### {encounter_id} window {window} ({asked} asked)")
    print("```text")
    print(call.completion if call.completion is not None else "(the call raised)")
    print("```")


def measure_script(
    script: EncounterScript,
    inputs: HarnessInputs,
    recorder: RecordingModel,
    now: datetime,
    *,
    verbose: bool = False,
) -> Tally:
    """One script, end to end (see the module docstring). Raises
    ``MeasurementError`` when the input ``suggestion_pass`` built differs
    from this tool's, or a call cannot be matched to its window."""
    from scribe_desktop import validation
    from scribe_desktop.note_config import next_patient_boundary
    from scribe_desktop.speaker_eval import CLINICIAN_LABEL
    from scribe_desktop.ui.models import build_suggestion_stage, placed_segments

    document, draft, expected_input = build_input(script, inputs, now)
    recorder.events.clear()
    stage = CapturingStage(
        build_suggestion_stage(
            model_factory=lambda: recorder, cache=None, available=lambda: True
        )
    )
    try:
        passed = validation.suggestion_pass(document, draft, CLINICIAN_LABEL, inputs, stage)
        captured = stage.suggestion_input
        if captured is None:
            if expected_input.lines_asked:
                raise MeasurementError("the harness asked no line where this tool asks some")
        elif captured != expected_input:
            raise MeasurementError("the tool's input differs from the harness's")
        tally = Tally(scripts=1)
        result = stage.outcome.result if stage.outcome is not None else None
        if stage.outcome is not None and result is None:
            tally.counts["unavailable"] += 1
        if result is not None:
            tally.counts["lines_asked"] += result.lines_asked
            tally.counts["not_assessed"] += result.lines_not_assessed
            tally.counts["model_calls"] += result.windows_run
            tally.counts["windows_failed"] += result.windows_failed
            tally.stage_seconds += result.seconds
            tally.model_id = result.model_id
            tally.prompt_version = result.prompt_version
        tally.counts["accepted_w"] += passed.by_clinician
        tally.counts["accepted_u"] += passed.by_other
        tally.counts["dropped"] += passed.dropped
        tally.counts["fit_reductions"] += fit_reductions(recorder.events)

        lines = captured.asked_lines if captured is not None else ()
        by_segment = {line.segment_index: line for line in lines}
        readings: dict[int, str] = {}
        calls = [event for event in recorder.events if isinstance(event, CallEvent)]
        for window, (call, asked) in enumerate(
            zip(calls, match_windows(calls, lines), strict=True), start=1
        ):
            _tally_window(call, asked, by_segment, script, recorder.inner, tally, readings)
            if verbose:
                _print_completion(script.encounter_id, window, call, len(asked))
    finally:
        recorder.events.clear()

    # The facts: the reference reading (no suggestion) and the note with
    # every accepted suggestion added — the harness's two compositions.
    bare = validation._compose_note(document, CLINICIAN_LABEL, inputs, now, draft=draft)
    before = validation.encounter_metrics(document, bare, script)
    with_suggestions = validation._compose_note(
        document, CLINICIAN_LABEL, inputs, now, draft=draft, additions=passed.additions
    )
    after = validation.encounter_metrics(
        document, with_suggestions, script, suggested_segments=passed.segments
    )
    silent_before = [fact for fact in before.facts if fact.silent_omission]
    silent_after = [fact for fact in after.facts if fact.silent_omission]
    tally.counts["silent_before"] += len(silent_before)
    tally.counts["silent_before_encounters"] += int(bool(silent_before))
    tally.counts["silent_after"] += len(silent_after)
    tally.counts["silent_after_encounters"] += int(bool(silent_after))
    if silent_after:
        tally.still_silent.append(script.encounter_id)
    tally.counts["wrongly_present"] += len(after.facts_wrongly_present_via_suggestion)
    tail = validation.reference_tail_start(script)
    if tail is not None and next_patient_boundary(document, inputs.config) is None:
        tally.counts["tail_suggestions"] += sum(1 for segment in passed.segments if segment >= tail)

    placed = placed_segments(draft.note_sections)
    for line_index in sorted({script.facts[fact.fact_index].line for fact in silent_before}):
        tally.counts["lost_lines"] += 1
        line = by_segment.get(line_index)
        if line is None or not line.asked:
            tally.readings["not_asked"] += 1
        else:
            tally.readings[readings.get(line_index, "no_answer")] += 1
        if script.lines[line_index].role == CLINICIAN_LABEL:
            continue
        question = next(
            (
                index
                for index in range(line_index - 1, -1, -1)
                if script.lines[index].role == CLINICIAN_LABEL
            ),
            None,
        )
        if question is None:
            continue
        tally.counts["lost_replies"] += 1
        if question not in placed and question not in passed.segments:
            tally.counts["replies_question_absent"] += 1
    return tally


# ---------------------------------------------------------------------------
# The answer-budget evidence (Task 0.2's budget table).
# ---------------------------------------------------------------------------

# A bounded answer form: (``?`` or "", separator or "", casing, full stop or "").
AnswerForm = tuple[str, str, str, str]
_QUESTIONS: Final = ("", "?")
_SEPARATORS: Final = ("", ".", ")", ":", "-")
_CASINGS: Final = ("lower", "capital", "upper")
_STOPS: Final = ("", ".")
FORMS: Final[tuple[AnswerForm, ...]] = tuple(
    (question, separator, casing, stop)
    for question in _QUESTIONS
    for separator in _SEPARATORS
    for casing in _CASINGS
    for stop in _STOPS
)
# The tier A choices (D3, Task 0.4) a bounded form may need beyond today's
# parser, and every set of them, today's parser first.
TIER_A_CHOICES: Final[tuple[tuple[frozenset[str], str], ...]] = (
    (frozenset(), "none (today's parser: number, optional separator, lower case)"),
    (frozenset({"question"}), "`?` after the number"),
    (frozenset({"case"}), "case-folding"),
    (frozenset({"stop"}), "a trailing full stop"),
    (frozenset({"question", "case"}), "`?` and case-folding"),
    (frozenset({"question", "stop"}), "`?` and a trailing full stop"),
    (frozenset({"case", "stop"}), "case-folding and a trailing full stop"),
    (frozenset({"question", "case", "stop"}), "all three"),
)
ALL_CHOICES: Final = frozenset({"question", "case", "stop"})


def _cased(word: str, casing: str) -> str:
    if casing == "capital":
        return word[:1].upper() + word[1:]
    if casing == "upper":
        return word.upper()
    return word


def answer_line(number: int, word: str, form: AnswerForm = ("", "", "lower", "")) -> str:
    """One full answer line with its line break: the number, then optionally
    ``?``, then optionally a separator, a space, the word in the form's
    casing, optionally a full stop."""
    question, separator, casing, stop = form
    return f"{number}{question}{separator} {_cased(word, casing)}{stop}\n"


def form_needs(form: AnswerForm) -> frozenset[str]:
    """The tier A choices a parser needs to admit ``form``."""
    question, _separator, casing, stop = form
    needs: set[str] = set()
    if question:
        needs.add("question")
    if casing != "lower":
        needs.add("case")
    if stop:
        needs.add("stop")
    return frozenset(needs)


@dataclass(frozen=True)
class BudgetRow:
    asked: int
    times_longest: int
    measured: int
    budget: int

    @property
    def bound(self) -> int:
        return max(self.times_longest, self.measured)


@dataclass(frozen=True)
class BudgetEvidence:
    """``plain``: each answer word's full line at a one- and a two-digit
    number; ``longest``: per tier A choice set, ``L`` and the line that gave
    it; ``rows``: the table for every asked count, under all three choices."""

    plain: tuple[tuple[str, int, int], ...]
    longest: Mapping[frozenset[str], tuple[int, str]]
    rows: tuple[BudgetRow, ...]


def budget_evidence(model: LanguageModel) -> BudgetEvidence:
    """The answer-budget evidence, from ``model.count_tokens`` alone: ``L``
    is the LARGEST token count of any full answer line over every answer
    word, every window number from 1 to the window size and every bounded
    form a choice set admits — taken by count, never assumed — and the
    cross-check counts a complete answer of ``n`` copies of the line that
    gave ``L`` under all three choices."""
    from scribe_desktop.note import CANONICAL_SECTION_KEYS
    from scribe_desktop.note_suggest import (
        ANSWER_NONE,
        SUGGESTION_WINDOW_SEGMENTS,
        answer_token_budget,
    )

    words = (*CANONICAL_SECTION_KEYS, ANSWER_NONE)
    plain = tuple(
        (
            word,
            model.count_tokens(answer_line(ONE_DIGIT_NUMBER, word)),
            model.count_tokens(answer_line(TWO_DIGIT_NUMBER, word)),
        )
        for word in words
    )
    longest: dict[frozenset[str], tuple[int, str]] = {}
    for form in FORMS:
        needs = form_needs(form)
        for number in range(1, SUGGESTION_WINDOW_SEGMENTS + 1):
            for word in words:
                line = answer_line(number, word, form)
                tokens = model.count_tokens(line)
                for choices, _label in TIER_A_CHOICES:
                    if needs <= choices and (
                        choices not in longest or tokens > longest[choices][0]
                    ):
                        longest[choices] = (tokens, line)
    size, line = longest[ALL_CHOICES]
    rows = tuple(
        BudgetRow(asked, asked * size, model.count_tokens(line * asked), answer_token_budget(asked))
        for asked in range(1, SUGGESTION_WINDOW_SEGMENTS + 1)
    )
    return BudgetEvidence(plain, longest, rows)


# ---------------------------------------------------------------------------
# The report (numbers-only Markdown).
# ---------------------------------------------------------------------------


def _table(header: Sequence[str], rows: Iterable[Sequence[object]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return lines


def render_set(name: str, tally: Tally, wall_seconds: float) -> list[str]:
    counts = tally.counts
    out = [
        "",
        f"## {name}",
        "",
        f"Scripts: {tally.scripts}. Stage version: {tally.prompt_version or 'not run'}. "
        f"Model: {tally.model_id or 'not run'}. Stage seconds: {tally.stage_seconds:.1f}. "
        f"Wall seconds: {wall_seconds:.1f}.",
        "",
        "### Completion lines by shape",
        "",
    ]
    shape_rows = []
    for shape, label in SHAPES:
        cells = [tally.shapes[(shape, column)] for column, _ in COLUMNS]
        shape_rows.append([label, cells[0], sum(cells[1:]), *cells[1:]])
    out += _table(["Shape", "W", "U", *(label for _, label in COLUMNS[1:])], shape_rows)
    out += [
        "",
        f"Unattributable lines (no leading number, or a number the window did not ask; "
        f"counted once, in no column): {counts['unattributable']}. Asked numbers with no "
        f"answer line: {counts['no_answer_numbers']}. Completions cut at their budget "
        f"(inferred: token count at least the budget less one and the last asked number "
        f"unanswered): {counts['cut_at_budget']}. Completions refused (marker echo or think "
        f"tag): {counts['refused']}.",
        "",
        "### Lines holding a silently lost material fact (the reference reading)",
        "",
    ]
    out += _table(
        ["Lines", *(label for _, label in READINGS)],
        [[counts["lost_lines"], *(tally.readings[key] for key, _ in READINGS)]],
    )
    out += ["", "### Facts", ""]
    out += _table(
        ["Silent material omissions", "Facts", "Encounters"],
        [
            ["Before suggestions (the reference reading)", counts["silent_before"],
             counts["silent_before_encounters"]],
            ["After accepting every suggestion", counts["silent_after"],
             counts["silent_after_encounters"]],
        ],
    )
    still = ", ".join(tally.still_silent) if tally.still_silent else "none"
    out += [
        "",
        f"Encounters still silent: {still}.",
        f"Facts wrongly present via a suggestion: {counts['wrongly_present']}. Suggestions "
        f"accepted at or after the reference tail start with no boundary detected: "
        f"{counts['tail_suggestions']}.",
        f"Lost-fact lines by others after a clinician line (replies): {counts['lost_replies']}; "
        f"of them, the nearest earlier clinician line neither in the note nor added by an "
        f"accepted suggestion: {counts['replies_question_absent']}.",
        "",
        "### The stage's own counts",
        "",
    ]
    out += _table(
        ["Lines asked", "Not assessed", "Accepted W", "Accepted U", "Dropped", "Model calls",
         "Windows failed", "Fit reductions", "Stage unavailable"],
        [[counts["lines_asked"], counts["not_assessed"], counts["accepted_w"],
          counts["accepted_u"], counts["dropped"], counts["model_calls"],
          counts["windows_failed"], counts["fit_reductions"], counts["unavailable"]]],
    )
    return out


def render_budget(evidence: BudgetEvidence) -> list[str]:
    from scribe_desktop.note_suggest import SUGGESTION_WINDOW_SEGMENTS

    out = [
        "",
        "## Answer budget (the model's token counts)",
        "",
        "Each answer word written as a full answer line (`<n> <word>` and its line break):",
        "",
    ]
    out += _table(
        ["Answer word", f"At {ONE_DIGIT_NUMBER}", f"At {TWO_DIGIT_NUMBER}"],
        [[f"`{word}`", one, two] for word, one, two in evidence.plain],
    )
    out += [
        "",
        f"L, the largest full answer line over every answer word, every window number 1 to "
        f"{SUGGESTION_WINDOW_SEGMENTS} and every bounded form (a number, then optionally `?`, "
        "then optionally one of `.` `)` `:` `-`, a space, the word in lower case, with a "
        "capital first letter or in capitals, then optionally a full stop, then the line "
        "break) the choice admits. A casing outside those three stays parseable but is not "
        "bounded; a completion that still runs out is caught by \"cut at budget\".",
        "",
    ]
    out += _table(
        ["Tier A forms admitted", "L", "The line that gave L"],
        [
            [label, evidence.longest[choices][0], f"`{evidence.longest[choices][1].rstrip()}`"]
            for choices, label in TIER_A_CHOICES
        ],
    )
    size = evidence.longest[ALL_CHOICES][0]
    out += [
        "",
        f"The budget table, all three choices admitted (L = {size}); the bound is n x L, or "
        "the measured complete answer when it is larger:",
        "",
    ]
    out += _table(
        ["Asked (n)", "n x L", "Measured: n copies", "Bound", "answer_token_budget(n)",
         "Budget less bound"],
        [
            [row.asked, row.times_longest, row.measured, row.bound, row.budget,
             row.budget - row.bound]
            for row in evidence.rows
        ],
    )
    over = [row.asked for row in evidence.rows if row.measured > row.times_longest]
    worst = max(evidence.rows, key=lambda row: row.bound - row.budget)
    out.append("")
    if over:
        out.append(
            "The measured complete answer exceeds n x L at n = "
            + ", ".join(str(asked) for asked in over)
            + "; there the measured figure is the bound."
        )
    if worst.bound > worst.budget:
        out.append(
            f"Largest shortfall: {worst.bound - worst.budget} tokens at n = {worst.asked}."
        )
    else:
        out.append(
            f"No shortfall: the budget covers the bound at every n (smallest margin "
            f"{worst.budget - worst.bound} tokens at n = {worst.asked})."
        )
    return out


# ---------------------------------------------------------------------------
# --timing (D7).
# ---------------------------------------------------------------------------


def timing_window(
    scripts: Sequence[EncounterScript], inputs: HarnessInputs, now: datetime
) -> tuple[SuggestionLine, ...] | None:
    """The scripts' suggestion lines (asked and placed), in order, joined
    until ``TIMING_ASKED_LINES`` are asked, renumbered so each segment index
    is its own; None when the scripts hold fewer asked lines."""
    lines: list[SuggestionLine] = []
    asked = 0
    for script in scripts:
        _document, _draft, suggestion_input = build_input(script, inputs, now)
        for line in suggestion_input.asked_lines:
            lines.append(replace(line, segment_index=len(lines)))
            if line.asked:
                asked += 1
                if asked == TIMING_ASKED_LINES:
                    return tuple(lines)
    return None


def window_digest(window: Sequence[SuggestionLine]) -> str:
    """D7's input hash: each line's placement and text, before the stage's
    instruction and labels."""
    digest = hashlib.sha256()
    for line in window:
        digest.update(f"{line.placed or ''}\t{line.suggestion_text}\n".encode())
    return digest.hexdigest()


def run_timing(window: Sequence[SuggestionLine], model: LanguageModel, *, verbose: bool) -> int:
    from scribe_desktop import note_suggest
    from scribe_desktop.language_model import LanguageModelError

    user_text, asked = note_suggest.build_window_prompt(window)
    budget = note_suggest.answer_token_budget(len(asked))
    failure: str | None = None
    completion = ""
    started = time.perf_counter()
    try:
        completion = model.complete(
            system_text=note_suggest.SUGGEST_INSTRUCTION, user_text=user_text, max_tokens=budget
        )
    except LanguageModelError as exc:
        failure = type(exc).__name__
    seconds = time.perf_counter() - started
    print("## Timing (D7)")
    print("")
    print(f"Module: {note_suggest.__file__}")
    print(f"Stage version: {note_suggest.SUGGEST_PROMPT_VERSION}")
    print(f"Input SHA-256: {window_digest(window)}")
    print(f"Window: {len(asked)} asked lines, {len(window)} lines in all; answer budget {budget}")
    if failure is not None:
        print(f"[error] the timing call failed ({failure})")
        return 1
    print(f"Seconds: {seconds:.1f}. Completion tokens: {model.count_tokens(completion)}.")
    if verbose:
        print("```text")
        print(completion)
        print("```")
    return 0


# ---------------------------------------------------------------------------
# The command line.
# ---------------------------------------------------------------------------


def load_set(set_dir: Path) -> tuple[list[EncounterScript], str | None]:
    """The set's scripts — every ``*.json`` whose stem is an encounter id, in
    name order — or a text-free refusal: an unusable script (the loader's
    own refusal), a script without synthetic conditions (C2, naming the id),
    or a next-patient script with no reference tail start."""
    from scribe_desktop.validation import (
        ENCOUNTER_ID_PATTERN,
        ResidueTableError,
        ScriptError,
        load_script,
        reference_tail_start,
    )

    paths = sorted(
        path
        for path in set_dir.glob("*.json")
        if path.is_file() and re.fullmatch(ENCOUNTER_ID_PATTERN, path.stem)
    )
    if not paths:
        return [], f"{set_dir} holds no encounter scripts"
    scripts: list[EncounterScript] = []
    for path in paths:
        refusal: str | None = None
        try:
            script = load_script(path)
        except ScriptError as exc:
            refusal = str(exc)  # the loader's own text-free refusal
        if refusal is not None:
            return [], refusal
        if script.conditions is None:
            return [], (
                f"{script.encounter_id} is not a synthetic encounter (its script has no "
                "conditions) - this measurement reads synthetic encounters only"
            )
        try:
            reference_tail_start(script)
        except ResidueTableError:
            refusal = f"{script.encounter_id}: a next-patient script has no reference tail start"
        if refusal is not None:
            return [], refusal
        scripts.append(script)
    return scripts, None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "set_dirs", nargs="+", type=Path, metavar="SET", help="a folder of synthetic scripts"
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="an explicit note-config folder (validation\\config); never the app's own",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="also print each window's raw completion (synthetic text; foreground only)",
    )
    parser.add_argument(
        "--timing",
        action="store_true",
        help="time ONE completion over a constructed window of 40 asked lines instead (D7)",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=DEFAULT_SOURCE_ROOT,
        help="the folder holding scribe_desktop, put first on the import path (D7)",
    )
    return parser


def _default_model() -> LanguageModel:
    """The one pinned model, loaded as the app loads it: the offline
    kill-switches applied and asserted first."""
    from scribe_desktop.benchmark import apply_offline_env, assert_offline_env
    from scribe_desktop.language_model import LocalLanguageModel

    apply_offline_env()
    assert_offline_env()
    return LocalLanguageModel()


def main(
    argv: list[str] | None = None,
    *,
    model_factory: Callable[[], LanguageModel] | None = None,
) -> int:
    """Exit 0 when every set was measured; 2 for a refusal before any model
    call (a source root without the package, a packaged build, a missing
    folder, the app's own config, an unusable config, an unusable or
    non-synthetic script, too few asked lines for ``--timing``, the model
    absent or not loadable); 1 when a script's measurement failed.
    ``model_factory`` is the tests' seam (default: the pinned local model,
    loaded once for the whole run)."""
    args = _parser().parse_args(argv)
    source_root: Path = args.source_root
    if not (source_root / "scribe_desktop" / "__init__.py").is_file():
        print(f"[refused] --source-root {source_root} holds no scribe_desktop package")
        return 2
    use_source_root(source_root)

    from scribe_desktop import install_layout, validation
    from scribe_desktop.note_config import (
        NoteConfigError,
        bind_template_profile,
        load_note_config,
    )
    from scribe_desktop.speaker_eval import configure_output
    from scribe_desktop.ui.models import language_model_available

    configure_output()
    if install_layout.channel() != "dev":
        print("[refused] the suggestion measurement runs only on the developer build")
        return 2
    set_dirs: list[Path] = args.set_dirs
    config_dir: Path = args.config
    for set_dir in set_dirs:
        if not set_dir.is_dir():
            print(f"[refused] {set_dir} is not a folder")
            return 2
    if not config_dir.is_dir():
        print(f"[refused] --config {config_dir} is not a folder")
        return 2
    if validation._normalised(config_dir) in validation._own_config_folders():
        print(f"[refused] --config {config_dir} is the app's own config folder")
        return 2
    config_failure: str | None = None
    try:
        config = load_note_config(config_dir)
        bind_template_profile(config, None)
    except NoteConfigError as exc:
        config_failure = type(exc).__name__  # its text can reproduce the file
    if config_failure is not None:
        print(f"[refused] --config {config_dir}: unusable ({config_failure})")
        return 2
    if validation._carries_learned_content(config_dir, config):
        print(f"[refused] --config {config_dir} carries the app's learned phrases or rules")
        return 2
    sets: list[tuple[Path, list[EncounterScript]]] = []
    for set_dir in set_dirs:
        scripts, refusal = load_set(set_dir)
        if refusal is not None:
            print(f"[refused] {refusal}")
            return 2
        sets.append((set_dir, scripts))

    inputs = harness_inputs(config)
    now = datetime.now(UTC)
    window: tuple[SuggestionLine, ...] | None = None
    if args.timing:
        window = timing_window([s for _dir, scripts in sets for s in scripts], inputs, now)
        if window is None:
            print(
                f"[refused] --timing: the named sets hold fewer than {TIMING_ASKED_LINES} "
                "asked lines - name another set folder too"
            )
            return 2

    load_failure: str | None = None
    started = time.perf_counter()
    if model_factory is None:
        if not language_model_available():
            print(
                "[refused] the language model is not installed: "
                + install_layout.model_remedy("language-model")
            )
            return 2
        model_factory = _default_model
    try:
        model = model_factory()
    except Exception as exc:  # noqa: BLE001 - by type: a load error's text names paths
        load_failure = type(exc).__name__
    if load_failure is not None:
        print(f"[refused] the language model could not be loaded ({load_failure})")
        return 2
    load_seconds = time.perf_counter() - started

    if window is not None:
        return run_timing(window, model, verbose=args.verbose)

    print("# Suggestion measurement (text level)")
    print("")
    print(f"Model: {model.model_id}. Model load seconds: {load_seconds:.1f}.")
    recorder = RecordingModel(model)
    for set_dir, scripts in sets:
        tally = Tally()
        set_started = time.perf_counter()
        for script in scripts:
            failure: str | None = None
            try:
                tally.add(measure_script(script, inputs, recorder, now, verbose=args.verbose))
            except MeasurementError as exc:
                failure = str(exc)  # fixed text
            except Exception as exc:  # noqa: BLE001 - reported by type, never by text
                failure = type(exc).__name__
            if failure is not None:
                print(f"[error] {script.encounter_id}: {failure}")
                return 1
        print("\n".join(render_set(set_dir.name, tally, time.perf_counter() - set_started)))
    print("\n".join(render_budget(budget_evidence(model))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
