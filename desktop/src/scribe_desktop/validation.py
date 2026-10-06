"""Pilot plan Phase 2: the validation harness (developer build only).

An offline batch run of the SHIPPED pipeline over synthetic and role-play
encounters, scored against each encounter's own script (pilot plan D8, D9):

- **The encounter script** (Task 2.2, ``EncounterScript``): the reference
  lines in spoken order, the expected facts with the reference line that
  states each, the checker warnings the encounter is written to provoke, and
  the conditions the synthetic set builder (``validation_set``) applies. A
  set folder holds, for every encounter, ``<id>.json`` + ``<id>.wav`` (the
  ``speaker_eval.read_wav_pcm`` contract) + ``<id>.txt`` (the Audacity label
  track ``docs/testing/speaker-measurement.md`` defines), so a role-play
  folder made for ``measure-speakers.py`` loads once its JSON is added
  (its file names must be encounter ids: lower-case letters, digits and
  hyphens).
- **The metrics** (Task 2.3, ``encounter_metrics``): ONE word-level
  alignment between the script's reference tokens and the transcript's words
  — the edit-distance alignment that yields the word error rate — carries
  every judgement; nothing is decided per segment. Pure functions; outputs
  are numbers, flags and closed-vocabulary verdicts only.
- **The runner** (Task 2.4, ``evaluate_encounter`` / ``main``): per
  encounter, transcription in a temporary encrypted store torn down key-first
  (``speaker_eval.transcribe_in_temporary_store``, reused IN PLACE), the
  clinician cluster chosen from the timed label track
  (``speaker_eval.align_segments``), ``compose_draft`` with the extractive
  provider built from the explicit config folder, every proposal confirmed
  (``ui.note_review.build_resolutions``), ``finalise_note``, optionally the
  narrative prose stage, then the metrics and the pass rule (data).

What this module enforces, and what it does not:

- **Text-free outputs.** Every result type holds counts, flags, closed
  vocabularies (fact kinds, verdicts, registered warning codes, exception
  TYPE names) and pattern-constrained encounter ids, validated at
  construction, so no transcript, note or script text can be held in a
  result, a report line or an error this module builds. The module logs
  nothing. The script's own text is read into memory to align against; it is
  synthetic or mock content by the plan's Constraint 8.
- **Custody.** The only store is the temporary one ``speaker_eval`` builds
  and destroys key-first with its fail-closed probe; a store that cannot be
  shown gone stops the run with the path named. No audit row and no
  Past-sessions entry is written: nothing here calls a store, audit or
  Past-sessions function (``ui.models``, imported for the provider factory
  and the prose stage, imports those modules; nothing here uses them).
- **Offline.** ``main`` applies and asserts the offline kill-switches before
  any model is constructed; the module opens no socket.
- **Developer build only.** ``main`` refuses a packaged build, refuses a
  ``small`` fallback unless ``--allow-small``, and reads only the explicit
  ``--config`` folder — the app's own config folders are refused by path,
  and so is a folder carrying the app's learned phrases or rules (a copy
  of the app's own). Learned phrases already merged into a copied
  ``section_cues.json`` cannot be told apart; the docs say never to copy.
- **Not a certificate.** The metrics measure the pipeline against what the
  script says was said. They do not judge clinical materiality beyond the
  script's own ``material`` marks, and the checker (``note_check``) is read,
  never changed (Constraint 12): a failure here is a finding.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import os
import re
import sys
from array import array
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, NamedTuple, get_args

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from scribe_desktop import install_layout
from scribe_desktop.benchmark import apply_offline_env, assert_offline_env
from scribe_desktop.note import (
    NOTE_WARNING_SEVERITY,
    GeneratedNote,
    NoteDraft,
    NoteModelProvider,
    ProposalResolution,
    compose_draft,
    content_tokens,
    finalise_note,
)
from scribe_desktop.note_check import (
    # Package-private by name, shared deliberately (the note.py convention):
    # the structured-claim word classes and the omission check's high-risk
    # predicate are READ here, never re-spelled, so the harness and the
    # checker cannot disagree about what a side, a dose or a negation is.
    _LATERALITY_TOKENS,
    _STRENGTH_UNITS,
    _dose_quantity,
    _is_high_risk_token,
    _polarity_mark,
)
from scribe_desktop.note_config import (
    CONFIG_DIRNAME,
    LEARNED_RULES_SIDECAR_FILENAME,
    LEARNED_SIDECAR_FILENAME,
    NoteConfig,
    NoteConfigError,
    bind_template_profile,
    is_learned_rule_id,
    load_note_config,
)
from scribe_desktop.note_fill import detect_prefill_candidates
from scribe_desktop.speaker_eval import (
    CLINICIAN_LABEL,
    LabelTrack,
    LabelTrackError,
    RecordingRefusedError,
    SpeakerEvalError,
    align_segments,
    configure_output,
    parse_audacity_labels,
    read_wav_pcm,
    transcribe_in_temporary_store,
)
from scribe_desktop.speech import (
    FrameProbabilityFn,
    SileroVad,
    SpeechProvider,
    SpeechSegment,
    vad_model_available,
)
from scribe_desktop.transcription import (
    DEFAULT_WHISPER_MODEL,
    TranscriptDocument,
    WhisperSpeechProvider,
    is_number_token,
    resolve_whisper_model,
    whisper_model_available,
)
from scribe_desktop.ui.models import (
    ProseStage,
    build_prose_stage,
    extractive_provider_from_config,
    language_model_available,
)
from scribe_desktop.ui.note_review import ProposalDecision, build_resolutions, prefilled_ids

# ---------------------------------------------------------------------------
# Task 2.2 — the encounter script format.
# ---------------------------------------------------------------------------

SCRIPT_SCHEMA_VERSION: Final = 1
RULE_SCHEMA_VERSION: Final = 1
# Ids are the only names a report prints: lower-case, digits and hyphens.
ENCOUNTER_ID_PATTERN: Final = r"^[a-z0-9][a-z0-9-]{0,63}$"
ROLE_PATTERN: Final = r"^[a-z][a-z_]{0,31}$"
RULE_NAME_PATTERN: Final = r"^[a-z0-9][a-z0-9-]{0,63}$"
# An exception TYPE name — the only part of an unexpected failure printed.
_ERROR_TYPE_PATTERN: Final = r"^[A-Za-z_][A-Za-z0-9_]{0,63}$"
_ENCOUNTER_ID_RE: Final = re.compile(ENCOUNTER_ID_PATTERN)
_ERROR_TYPE_RE: Final = re.compile(_ERROR_TYPE_PATTERN)
MAX_SCRIPT_BYTES: Final = 256 * 1024
MAX_LINE_CHARS: Final = 2_000

# The axes of PLAN.md's AI-quality list (L188-201). ``noise``, ``overlap``
# and ``rate`` are applied by the synthetic conditions; accents cannot be
# synthesised and are left to the role-plays.
Axis = Literal[
    "negation",
    "laterality",
    "numbers",
    "small_talk",
    "uncertain",
    "contradictory",
    "scribe_instruction",
    "end_and_new_patient",
    "noise",
    "overlap",
    "rate",
]
AXES: Final[tuple[str, ...]] = get_args(Axis)
FactKind = Literal["laterality", "dose", "negation", "absent", "present"]
FACT_KINDS: Final[tuple[str, ...]] = get_args(FactKind)
AppointmentType = Literal[
    "initial", "follow_up", "acute", "chronic", "post_operative", "discharge"
]
# The four contradiction-class codes a script may expect (Task 2.3's checker
# tally): listing one exempts it, and only it, from failing the encounter.
ContradictionCode = Literal[
    "contradiction", "contradiction_low_confidence", "laterality_mismatch", "dose_mismatch"
]
CONTRADICTION_CODES: Final[frozenset[str]] = frozenset(get_args(ContradictionCode))

_SCRIPT_CONFIG = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class ValidationHarnessError(Exception):
    """Base class for harness failures (messages are built from names,
    paths, field locations and numbers only)."""


class ScriptError(ValidationHarnessError):
    """An encounter script is unusable; it is refused by file name and field."""


class RuleError(ValidationHarnessError):
    """The pass-rule file is unusable."""


def _occurrences(tokens: Sequence[str], needle: Sequence[str]) -> list[int]:
    """Every start index at which ``needle`` occurs contiguously in ``tokens``."""
    width = len(needle)
    return [
        start
        for start in range(len(tokens) - width + 1)
        if tuple(tokens[start : start + width]) == tuple(needle)
    ]


class ScriptLine(BaseModel):
    """One reference line: who says it (a role name, the label-track
    vocabulary) and what is said. Lines are listed in START-TIME order —
    the builder places them in that order, overlapped turns included."""

    model_config = _SCRIPT_CONFIG

    role: str = Field(pattern=ROLE_PATTERN)
    text: str = Field(min_length=1, max_length=MAX_LINE_CHARS)

    @model_validator(mode="after")
    def _has_words(self) -> ScriptLine:
        if not content_tokens(self.text):
            raise ValueError("a line must carry at least one word")
        return self


class ExpectedFact(BaseModel):
    """One expected fact (Task 2.3's per-fact verdict). ``tokens`` are
    normalised content tokens (``note.content_tokens``) that occur
    contiguously in reference line ``line``; ``kind`` ``absent`` marks content
    that must NOT reach the note (small talk, a spoken instruction, the next
    patient). ``material`` facts drive the pass rule; ``expect_uncertain``
    facts must have their uncertainty surfaced."""

    model_config = _SCRIPT_CONFIG

    kind: FactKind
    tokens: tuple[str, ...] = Field(min_length=1, max_length=12)
    line: int = Field(ge=0)
    material: bool
    expect_uncertain: bool = False

    @model_validator(mode="after")
    def _tokens_are_normalised(self) -> ExpectedFact:
        if content_tokens(" ".join(self.tokens)) != self.tokens:
            raise ValueError(
                "fact tokens must be single normalised words (lower case, no surrounding "
                "punctuation, no filler words)"
            )
        # Round 12 LOW-001: ``low_confidence_source`` sits only on words in
        # the note, so an absent fact could be "surfaced" only by wrongly
        # reaching it — the right outcome would fail the uncertainty test.
        if self.kind == "absent" and self.expect_uncertain:
            raise ValueError("an absent fact cannot expect its uncertainty surfaced")
        return self


class SyntheticConditions(BaseModel):
    """What the synthetic set builder applies (Task 2.5): one installed
    voice slot per role (distinct), the speaking rate, the signal-to-noise
    ratio of the mixed-in noise (None = clean), and the lines that start
    ``overlap_seconds`` before the previous line ends. Absent on a recorded
    role-play."""

    model_config = _SCRIPT_CONFIG

    voice_slots: dict[str, int]
    rate: int = Field(default=0, ge=-10, le=10)
    snr_db: float | None = Field(default=None, ge=0.0, le=60.0)
    overlap_seconds: float = Field(default=0.0, ge=0.0, le=5.0)
    overlap_lines: tuple[int, ...] = ()

    @model_validator(mode="after")
    def _check_conditions(self) -> SyntheticConditions:
        for role, slot in self.voice_slots.items():
            if not re.fullmatch(ROLE_PATTERN, role):
                raise ValueError(f"voice_slots keys must match {ROLE_PATTERN}")
            if slot < 0:
                raise ValueError("a voice slot is a non-negative index")
        if len(set(self.voice_slots.values())) != len(self.voice_slots):
            raise ValueError("each role needs its own voice slot")
        if list(self.overlap_lines) != sorted(set(self.overlap_lines)):
            raise ValueError("overlap_lines must be unique and ascending")
        # Two overlapped lines in a row could start the second before the
        # turn two back ends — the same speaker over themselves when those
        # two share a role (round 11 LOW-003).
        lines = self.overlap_lines
        if any(b - a == 1 for a, b in zip(lines, lines[1:], strict=False)):
            raise ValueError("overlap_lines must not hold two consecutive lines")
        if bool(self.overlap_lines) != (self.overlap_seconds > 0):
            raise ValueError("overlap_seconds and overlap_lines are set together")
        return self


class EncounterScript(BaseModel):
    """One encounter (Task 2.2). Validation refuses, by field: a fact whose
    tokens its line does not contain, a fact line out of range, a script with
    no ``clinician`` line, an overlapped line that continues the same role,
    a role without a voice slot (synthetic), and an axis tag the synthetic
    conditions contradict (``noise`` with no ratio, a ratio without
    ``noise``, and the same for ``overlap`` and ``rate``)."""

    model_config = _SCRIPT_CONFIG

    schema_version: Literal[1]
    encounter_id: str = Field(pattern=ENCOUNTER_ID_PATTERN)
    appointment_type: AppointmentType
    axes: tuple[Axis, ...] = Field(min_length=1)
    lines: tuple[ScriptLine, ...] = Field(min_length=1)
    facts: tuple[ExpectedFact, ...] = ()
    expected_warnings: tuple[ContradictionCode, ...] = ()
    conditions: SyntheticConditions | None = None

    @model_validator(mode="after")
    def _check_script(self) -> EncounterScript:
        if len(set(self.axes)) != len(self.axes):
            raise ValueError("axes must be unique")
        if len(set(self.expected_warnings)) != len(self.expected_warnings):
            raise ValueError("expected_warnings must be unique")
        roles = [line.role for line in self.lines]
        if CLINICIAN_LABEL not in roles:
            raise ValueError(f"at least one line must be spoken by {CLINICIAN_LABEL!r}")
        for index, fact in enumerate(self.facts):
            if fact.line >= len(self.lines):
                raise ValueError(f"fact {index} names line {fact.line}, which does not exist")
            if not _occurrences(content_tokens(self.lines[fact.line].text), fact.tokens):
                raise ValueError(f"fact {index}: its tokens do not occur in line {fact.line}")
        conditions = self.conditions
        if conditions is None:
            return self
        if set(conditions.voice_slots) != set(roles):
            raise ValueError("voice_slots must name exactly the roles the lines use")
        for line_index in conditions.overlap_lines:
            if not 1 <= line_index < len(self.lines):
                raise ValueError(f"overlap line {line_index} has no previous line")
            if roles[line_index] == roles[line_index - 1]:
                raise ValueError(f"overlap line {line_index} continues the same role")
        for axis, applied in (
            ("noise", conditions.snr_db is not None),
            ("overlap", bool(conditions.overlap_lines)),
            ("rate", conditions.rate != 0),
        ):
            if (axis in self.axes) != applied:
                raise ValueError(f"axis {axis!r} and the synthetic conditions disagree")
        return self


def _schema_field_names() -> frozenset[str]:
    return frozenset(
        name
        for model in (ScriptLine, ExpectedFact, SyntheticConditions, EncounterScript, PassRule)
        for name in model.model_fields
    )


def _validation_error_text(exc: ValidationError) -> str:
    """Field locations and messages only — ``hide_input_in_errors`` keeps the
    rejected value (which could be script text) out of every message, and a
    location part that is not a schema field name or a list index (an
    unknown key, a ``voice_slots`` role) prints as ``<key>`` (round 11
    LOW-007: a key is author-typed text)."""
    known = _schema_field_names()
    parts = []
    for error in exc.errors()[:3]:
        location = ".".join(
            str(part) if isinstance(part, int) or part in known else "<key>"
            for part in error["loc"]
        )
        parts.append(f"{location or '(file)'}: {error['msg']}")
    return "; ".join(parts)


def load_script(path: Path) -> EncounterScript:
    """One ``<id>.json`` script, refused by file name and field — never with
    the rejected text. The file's stem must be its ``encounter_id``."""
    return load_script_with_bytes(path)[0]


def load_script_with_bytes(path: Path) -> tuple[EncounterScript, bytes]:
    """``load_script`` plus the exact bytes it validated, read once — so a
    caller that copies the script (the set builder) copies what it rendered,
    even if the file changes meanwhile (round 12 LOW-008)."""
    try:
        with path.open("rb") as handle:
            blob = handle.read(MAX_SCRIPT_BYTES + 1)
    except OSError as exc:
        raise ScriptError(f"{path.name}: unreadable ({type(exc).__name__})") from None
    if len(blob) > MAX_SCRIPT_BYTES:
        raise ScriptError(f"{path.name}: larger than {MAX_SCRIPT_BYTES} bytes")
    try:
        script = EncounterScript.model_validate_json(blob)
    except ValidationError as exc:
        raise ScriptError(f"{path.name}: {_validation_error_text(exc)}") from None
    if script.encounter_id != path.stem:
        raise ScriptError(f"{path.name}: its encounter_id names a different encounter")
    return script, blob


class EncounterFiles(NamedTuple):
    """One complete encounter in a set folder."""

    encounter_id: str
    script: Path
    wav: Path
    labels: Path


_SET_SUFFIXES: Final = (".json", ".wav", ".txt")


# Stands in for a file name that is not an encounter id: such a name is
# never printed (it could be anything, a person's name included).
UNNAMED_ENCOUNTER: Final = "(a file not named as an encounter id)"


def find_encounters(directory: Path) -> tuple[list[EncounterFiles], list[tuple[str, str]]]:
    """``(complete, incomplete)``: every encounter-id stem holding all of
    ``<id>.json``, ``<id>.wav`` and ``<id>.txt``, in name order, and
    ``(name, problem)`` for every other set file — an id stem missing some
    of the three, or (once, as ``UNNAMED_ENCOUNTER``) any ``.json`` /
    ``.wav`` / ``.txt`` whose name is not an encounter id (round 11
    MED-006: such a stem could not even be reported as an outcome). Other
    files are ignored."""
    found: dict[str, dict[str, Path]] = {}
    unnamed = 0
    for path in sorted(directory.iterdir()):
        suffix = path.suffix.lower()
        if not (path.is_file() and suffix in _SET_SUFFIXES):
            continue
        if _ENCOUNTER_ID_RE.fullmatch(path.stem):
            found.setdefault(path.stem, {})[suffix] = path
        else:
            unnamed += 1
    complete: list[EncounterFiles] = []
    incomplete: list[tuple[str, str]] = []
    for stem in sorted(found):
        files = found[stem]
        missing = [suffix for suffix in _SET_SUFFIXES if suffix not in files]
        if missing:
            incomplete.append((stem, "missing " + ", ".join(missing)))
        else:
            complete.append(EncounterFiles(stem, files[".json"], files[".wav"], files[".txt"]))
    if unnamed:
        incomplete.append(
            (
                UNNAMED_ENCOUNTER,
                f"{unnamed} file(s) skipped - rename each to its encounter id (lower-case "
                "letters, digits and hyphens)",
            )
        )
    return complete, incomplete


# ---------------------------------------------------------------------------
# Task 2.3 — the metrics (pilot plan D8). Pure; text-free outputs.
# ---------------------------------------------------------------------------

FactVerdict = Literal["correct", "wrong", "omitted", "correctly_absent", "wrongly_present"]
FACT_VERDICTS: Final[tuple[str, ...]] = get_args(FactVerdict)


def is_structured_claim_word(token: str) -> bool:
    """A side, a number, a dose or unit, or a negation — recognised by
    ``note_check``'s own classes (Constraint 12: read, never changed):
    ``_LATERALITY_TOKENS``; ``transcription.is_number_token`` (digits and
    spelled numbers); ``_dose_quantity`` and ``_STRENGTH_UNITS`` (a strength
    atom or a unit word); ``_polarity_mark`` (the negation vocabulary plus
    ``nil`` and any ``n't`` contraction). ``token`` is one normalised token."""
    return (
        token in _LATERALITY_TOKENS
        or is_number_token(token)
        or _dose_quantity(token) is not None
        or token in _STRENGTH_UNITS
        or _polarity_mark(token) is not None
    )


def _require_member(value: object, allowed: Iterable[object], name: str) -> None:
    if value not in set(allowed):
        raise ValueError(f"{name} is outside its closed vocabulary")


def _require_count(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative count")


@dataclass(frozen=True)
class WordErrors:
    """The word error rate's parts: reference tokens (the script), hypothesis
    tokens (the transcript) and the edit distance between them over
    ``note.content_tokens`` normalisation (substitution, insertion and
    deletion each cost one)."""

    reference_tokens: int
    hypothesis_tokens: int
    edit_distance: int

    def __post_init__(self) -> None:
        for name in ("reference_tokens", "hypothesis_tokens", "edit_distance"):
            _require_count(getattr(self, name), name)

    @property
    def rate(self) -> float:
        """Edit distance over reference tokens; 0.0 for an empty reference
        (a script is never empty — ``ScriptLine`` refuses a wordless line)."""
        return self.edit_distance / self.reference_tokens if self.reference_tokens else 0.0


@dataclass(frozen=True)
class FactOutcome:
    """One expected fact's outcome (Task 2.3). ``fact_index`` is the fact's
    position in the script. ``warned`` and ``uncertainty_surfaced`` are
    decided at WORD level; ``uncertainty_surfaced`` is None for a fact not
    marked ``expect_uncertain``. ``not_transcribed``: every token was deleted
    by transcription. ``ambiguous``: the fact's judged outcomes differed —
    across the alignment's equal-cost alternatives OR across repeated
    statements of the fact in its line — and the worse one is reported
    (round 13 LOW-006). ``silently_omitted_somewhere``: SOME alternative or
    statement left the fact omitted and unwarned, whatever verdict is
    reported (peer round 14, PR-MED-056)."""

    fact_index: int
    kind: FactKind
    material: bool
    verdict: FactVerdict
    warned: bool
    uncertainty_surfaced: bool | None
    not_transcribed: bool
    ambiguous: bool
    silently_omitted_somewhere: bool = False

    def __post_init__(self) -> None:
        _require_count(self.fact_index, "fact_index")
        _require_member(self.kind, FACT_KINDS, "kind")
        _require_member(self.verdict, FACT_VERDICTS, "verdict")
        for name in (
            "material",
            "warned",
            "not_transcribed",
            "ambiguous",
            "silently_omitted_somewhere",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be a flag")
        if self.uncertainty_surfaced is not None and not isinstance(
            self.uncertainty_surfaced, bool
        ):
            raise ValueError("uncertainty_surfaced must be a flag or None")

    @property
    def silent_omission(self) -> bool:
        """``omitted`` and ``material`` and not ``warned`` (Task 2.3) — on
        the reported outcome OR on any equal-cost alternative. Each tally is
        conservative on its own, as ``uncertainty_surfaced`` is (round 11
        LOW-008): a fact reported ``wrong`` whose other co-optimal alignment
        omits it unwarned counts in BOTH ``material_wrong`` and
        ``silent_omissions``, so a rule that allows one cannot hide the other
        (peer round 14, PR-MED-056)."""
        if not self.material:
            return False
        reported = self.verdict == "omitted" and not self.warned
        return reported or self.silently_omitted_somewhere

    @property
    def material_wrong(self) -> bool:
        return self.material and self.verdict in ("wrong", "wrongly_present")


@dataclass(frozen=True)
class EncounterMetrics:
    """Everything Task 2.3 measures for one encounter — counts, flags and
    registered warning codes only. ``checker_tally`` is ``(code, count)`` per
    warning code on the finalised note; ``checker_failures`` the codes that
    fail the encounter (any error-severity code, and any contradiction-class
    code the script does not list in ``expected_warnings``) and
    ``checker_failure_count`` how many warnings carry them;
    ``expected_warnings_absent`` the listed codes the checker did not raise
    (reported, never failing)."""

    words: WordErrors
    transcript_lines: int
    config_lines: int
    unsupported_clinical_lines: int
    other_unsupported_words: int
    checker_tally: tuple[tuple[str, int], ...]
    checker_failures: tuple[str, ...]
    checker_failure_count: int
    expected_warnings_absent: tuple[str, ...]
    facts: tuple[FactOutcome, ...]

    def __post_init__(self) -> None:
        for name in (
            "transcript_lines",
            "config_lines",
            "unsupported_clinical_lines",
            "other_unsupported_words",
            "checker_failure_count",
        ):
            _require_count(getattr(self, name), name)
        for code, count in self.checker_tally:
            _require_member(code, NOTE_WARNING_SEVERITY, "checker_tally code")
            _require_count(count, "checker_tally count")
        for code in (*self.checker_failures, *self.expected_warnings_absent):
            _require_member(code, NOTE_WARNING_SEVERITY, "warning code")
        # Round 11 LOW-012: the nested results are the validated types, so
        # Constraint 7 holds at run time, not only under mypy.
        if not isinstance(self.words, WordErrors):
            raise ValueError("words must be a WordErrors")
        if not all(isinstance(fact, FactOutcome) for fact in self.facts):
            raise ValueError("facts must be FactOutcome results")

    @property
    def material_wrong(self) -> int:
        return sum(1 for fact in self.facts if fact.material_wrong)

    @property
    def silent_omissions(self) -> int:
        return sum(1 for fact in self.facts if fact.silent_omission)

    @property
    def warned_omissions(self) -> int:
        return sum(1 for fact in self.facts if fact.verdict == "omitted" and fact.warned)

    @property
    def uncertainty_missed(self) -> int:
        return sum(1 for fact in self.facts if fact.uncertainty_surfaced is False)

    @property
    def ambiguous_facts(self) -> int:
        return sum(1 for fact in self.facts if fact.ambiguous)


class _WordInfo(NamedTuple):
    """What one transcript word means to the fact walk — flags only."""

    covered: bool
    warned: bool
    low_confidence: bool


class _Alignment:
    """THE word-level alignment (D8): Levenshtein over normalised tokens,
    with the forward and backward cost tables kept so that EVERY optimal
    alignment is visible — an edge lies on some optimal alignment exactly
    when ``forward + edge cost + backward == total``. Holds tokens in memory
    for one encounter; never returned or rendered. The tables are rows of
    machine ints (``array('i')``, 4 bytes a cell): a 10-minute role-play of
    about 1,500 tokens a side is two tables of about 9 MB each."""

    def __init__(self, reference: Sequence[str], hypothesis: Sequence[str]) -> None:
        self.reference = reference
        self.hypothesis = hypothesis
        n, m = len(reference), len(hypothesis)
        self.n, self.m = n, m
        forward = [array("i", [0]) * (m + 1) for _ in range(n + 1)]
        forward[0] = array("i", range(m + 1))
        for i in range(1, n + 1):
            row, previous, token = forward[i], forward[i - 1], reference[i - 1]
            row[0] = i
            for j in range(1, m + 1):
                diagonal = previous[j - 1] + (0 if token == hypothesis[j - 1] else 1)
                row[j] = min(diagonal, previous[j] + 1, row[j - 1] + 1)
        backward = [array("i", [0]) * (m + 1) for _ in range(n + 1)]
        backward[n] = array("i", (m - j for j in range(m + 1)))
        for i in range(n - 1, -1, -1):
            row, following, token = backward[i], backward[i + 1], reference[i]
            row[m] = n - i
            for j in range(m - 1, -1, -1):
                diagonal = following[j + 1] + (0 if token == hypothesis[j] else 1)
                row[j] = min(diagonal, following[j] + 1, row[j + 1] + 1)
        self.forward, self.backward = forward, backward
        self.total = forward[n][m]

    def on_optimal(self, i: int, j: int) -> bool:
        return self.forward[i][j] + self.backward[i][j] == self.total

    def diagonal(self, i: int, j: int) -> bool:
        """Reference token ``i`` aligned to hypothesis token ``j``
        (a match, or a substitution) on some optimal alignment."""
        cost = 0 if self.reference[i] == self.hypothesis[j] else 1
        return self.forward[i][j] + cost + self.backward[i + 1][j + 1] == self.total

    def deletion(self, i: int, j: int) -> bool:
        """Reference token ``i`` deleted (at hypothesis position ``j``)."""
        return self.forward[i][j] + 1 + self.backward[i + 1][j] == self.total

    def insertion(self, i: int, j: int) -> bool:
        """Hypothesis token ``j`` inserted (at reference position ``i``)."""
        return self.forward[i][j] + 1 + self.backward[i][j + 1] == self.total

    def possibly_unsupported(self) -> list[bool]:
        """Per hypothesis token: substituted or inserted on SOME optimal
        alignment — the conservative reading, so an equal-cost alternative
        can never hide a substituted clinical word."""
        flags = [False] * self.m
        for j in range(self.m):
            for i in range(self.n + 1):
                if self.insertion(i, j) or (
                    i < self.n
                    and self.reference[i] != self.hypothesis[j]
                    and self.diagonal(i, j)
                ):
                    flags[j] = True
                    break
        return flags


# The fact walk's state: (every token matched, every token deleted, some
# aligned word in a note line, every aligned word in a note line, warned,
# uncertainty surfaced). Six flags, so at most 64 states per cell.
_FactState = tuple[bool, bool, bool, bool, bool, bool]
_INITIAL_STATE: Final[_FactState] = (True, True, False, True, False, False)


def _after_word(state: _FactState, matched: bool, info: _WordInfo) -> _FactState:
    all_matched, _deleted, in_any, in_all, warned, surfaced = state
    return (
        all_matched and matched,
        False,
        in_any or info.covered,
        in_all and info.covered,
        warned or info.warned,
        surfaced or info.low_confidence,
    )


def _after_deletion(state: _FactState) -> _FactState:
    _matched, deleted, in_any, in_all, warned, surfaced = state
    return (False, deleted, in_any, in_all, warned, surfaced)


def _fact_end_states(
    alignment: _Alignment, first: int, last: int, words: Sequence[_WordInfo]
) -> set[_FactState]:
    """Every outcome state reachable over the optimal alignments for
    reference rows ``first..last``: a fact's tokens are judged JOINTLY on
    each alignment, and every co-optimal alignment is kept so the caller can
    take the worse outcome (Task 2.3: ambiguity is conservative)."""
    m = alignment.m
    current: dict[int, set[_FactState]] = {
        j: {_INITIAL_STATE} for j in range(m + 1) if alignment.on_optimal(first, j)
    }
    for i in range(first, last + 1):
        # Insertions before reference token ``i`` keep the state, move right.
        for j in range(m):
            if j in current and alignment.insertion(i, j):
                current.setdefault(j + 1, set()).update(current[j])
        following: dict[int, set[_FactState]] = {}
        for j, states in current.items():
            if alignment.deletion(i, j):
                following.setdefault(j, set()).update(_after_deletion(s) for s in states)
            if j < m and alignment.diagonal(i, j):
                matched = alignment.reference[i] == alignment.hypothesis[j]
                info = words[j]
                following.setdefault(j + 1, set()).update(
                    _after_word(s, matched, info) for s in states
                )
        current = following
    reached: set[_FactState] = set()
    for states in current.values():
        reached |= states
    return reached


class _Judged(NamedTuple):
    verdict: FactVerdict
    warned: bool
    surfaced: bool | None
    not_transcribed: bool


def _judge(state: _FactState, kind: FactKind, expect_uncertain: bool) -> _Judged:
    all_matched, all_deleted, in_any, in_all, warned, surfaced = state
    verdict: FactVerdict
    if kind == "absent":
        verdict = "wrongly_present" if in_any else "correctly_absent"
    elif not in_any:
        verdict = "omitted"
    elif all_matched and in_all:
        verdict = "correct"
    else:
        # Some of the fact's words are in a note line, but not all of them
        # matched and carried: the note states something other than the fact.
        verdict = "wrong"
    return _Judged(verdict, warned, surfaced if expect_uncertain else None, all_deleted)


# Outcomes from best to worst. A warned omission is better than a silent one
# (the clinician was told); a wrong or wrongly-present fact is worst.
_OUTCOME_ORDER: Final = ("as_expected", "omitted_warned", "omitted_silent", "wrong")
_OUTCOME_OF_VERDICT: Final[Mapping[str, str]] = {
    "correct": "as_expected",
    "correctly_absent": "as_expected",
    "wrong": "wrong",
    "wrongly_present": "wrong",
}


def _severity(judged: _Judged) -> tuple[int, bool, bool, bool, str]:
    """Larger is worse: the outcome (``_OUTCOME_ORDER``), then uncertainty
    NOT surfaced, then not warned, then not transcribed; the verdict last.
    ``surfaced`` True and None share a key value, but one fact's outcomes
    never mix them (``expect_uncertain`` is fixed per fact), so the order
    is total within a fact and the reported outcome never depends on set
    iteration order. Since round 11 LOW-008 the reported
    ``uncertainty_surfaced`` is judged separately (over every alternative);
    here it only picks which alternative supplies ``warned`` and
    ``not_transcribed`` (round 12 LOW-004)."""
    if judged.verdict == "omitted":
        outcome = "omitted_warned" if judged.warned else "omitted_silent"
    else:
        outcome = _OUTCOME_OF_VERDICT[judged.verdict]
    return (
        _OUTCOME_ORDER.index(outcome),
        judged.surfaced is False,
        not judged.warned,
        judged.not_transcribed,
        judged.verdict,
    )


def _reference(script: EncounterScript) -> tuple[list[str], list[int]]:
    """The reference tokens in spoken order and each line's first index."""
    tokens: list[str] = []
    offsets: list[int] = []
    for line in script.lines:
        offsets.append(len(tokens))
        tokens.extend(content_tokens(line.text))
    return tokens, offsets


def _hypothesis(document: TranscriptDocument) -> tuple[list[str], list[tuple[int, int]]]:
    """The transcript's tokens in segment order and the (segment, word) each
    came from — the coordinates note lines and warnings address."""
    tokens: list[str] = []
    positions: list[tuple[int, int]] = []
    for segment_index, segment in enumerate(document.transcript_segments):
        for word_index, word in enumerate(segment.transcript_words):
            for token in content_tokens(word.word_text):
                tokens.append(token)
                positions.append((segment_index, word_index))
    return tokens, positions


def word_errors(document: TranscriptDocument, script: EncounterScript) -> WordErrors:
    """The word error rate's parts without a note (a role-unresolved
    encounter still reports it)."""
    reference, _ = _reference(script)
    hypothesis, _ = _hypothesis(document)
    alignment = _Alignment(reference, hypothesis)
    return WordErrors(len(reference), len(hypothesis), alignment.total)


def _note_lines(
    note: GeneratedNote, document: TranscriptDocument
) -> tuple[list[set[tuple[int, int]]], int]:
    """The (segment, word) set of every transcript note line whose
    coordinates resolve (an unresolvable one is the checker's
    ``source_coords_invalid`` error), and the count of config lines."""
    lines: list[set[tuple[int, int]]] = []
    config_lines = 0
    segments = document.transcript_segments
    for section in note.note_sections:
        for assertion in section.note_assertions:
            coords = assertion.note_span.source_coords
            if assertion.provenance != "transcript" or coords is None:
                config_lines += 1
                continue
            if coords.segment_index >= len(segments) or coords.last_word_index >= len(
                segments[coords.segment_index].transcript_words
            ):
                continue
            lines.append(
                {
                    (coords.segment_index, word_index)
                    for word_index in range(coords.first_word_index, coords.last_word_index + 1)
                }
            )
    return lines, config_lines


def encounter_metrics(
    document: TranscriptDocument, note: GeneratedNote, script: EncounterScript
) -> EncounterMetrics:
    """Task 2.3's metric contract over one encounter (D8), exactly:

    - ONE word-level alignment of the script's reference tokens (spoken
      order) to the transcript's words, the one the word error rate comes
      from; every fact maps to exact (segment, word) positions wherever the
      segment boundaries fall.
    - An UNSUPPORTED CLINICAL LINE is a transcript note line holding a
      structured-claim word (``is_structured_claim_word``) that the alignment
      marks substituted or inserted — on ANY optimal alignment, so a tie
      cannot hide one. Judged word by word, so a line spanning several
      reference lines is never unsupported by the merge itself. Other such
      words in note lines are counted (``other_unsupported_words``, distinct
      words). Config lines (no coordinates) are counted separately and
      judged through the checker tally.
    - The CHECKER TALLY counts each warning code on the finalised note.
    - Per expected fact, judged JOINTLY over its tokens on each optimal
      alignment: ``correct`` when every token matched a word inside a note
      line; ``omitted`` when no aligned word is inside a note line (all
      tokens deleted = ``not_transcribed``); ``wrong`` otherwise (the note
      carries some of the fact's words but not the fact). An ``absent``
      fact is ``wrongly_present`` when any aligned word is inside a note
      line, else ``correctly_absent``. ``warned``: one of the fact's own
      aligned words is outside every note line, high-risk by the omission
      check's predicate, and its segment carries a ``high_risk_omission``
      warning — a warning's interval proves nothing, and a warning elsewhere
      in the segment never counts. ``uncertainty_surfaced`` (for
      ``expect_uncertain`` facts): a ``low_confidence_source`` warning sits
      on one of the fact's aligned words.
    - Ambiguity is conservative: across equal-cost alignments, and across
      repeated occurrences of the tokens inside the fact's line, the fact
      takes the worse outcome (``ambiguous`` says alternatives differed),
      and its uncertainty counts as surfaced only when every alternative
      surfaces it, and it counts as a silent omission when any alternative
      omits it unwarned (peer round 14, PR-MED-056).
    """
    reference, offsets = _reference(script)
    hypothesis, positions = _hypothesis(document)
    alignment = _Alignment(reference, hypothesis)
    segments = document.transcript_segments

    lines, config_lines = _note_lines(note, document)
    covered: set[tuple[int, int]] = set()
    for line in lines:
        covered |= line
    omission_segments = {
        warning.source_coords.segment_index
        for warning in note.note_warnings
        if warning.note_warning_code == "high_risk_omission" and warning.source_coords is not None
    }
    low_confidence: set[tuple[int, int]] = set()
    for warning in note.note_warnings:
        coords = warning.source_coords
        if warning.note_warning_code == "low_confidence_source" and coords is not None:
            low_confidence.update(
                (coords.segment_index, index)
                for index in range(coords.first_word_index, coords.last_word_index + 1)
            )

    infos: list[_WordInfo] = []
    for segment_index, word_index in positions:
        position = (segment_index, word_index)
        word_text = segments[segment_index].transcript_words[word_index].word_text
        is_covered = position in covered
        infos.append(
            _WordInfo(
                covered=is_covered,
                warned=not is_covered
                and segment_index in omission_segments
                and _is_high_risk_token(word_text, first_in_segment=word_index == 0),
                low_confidence=position in low_confidence,
            )
        )

    unsupported = alignment.possibly_unsupported()
    by_word: dict[tuple[int, int], list[int]] = {}
    for j, position in enumerate(positions):
        by_word.setdefault(position, []).append(j)
    unsupported_lines = 0
    other_words: set[int] = set()
    for line in lines:
        flagged = [j for position in line for j in by_word.get(position, ()) if unsupported[j]]
        if any(is_structured_claim_word(hypothesis[j]) for j in flagged):
            unsupported_lines += 1
        other_words.update(j for j in flagged if not is_structured_claim_word(hypothesis[j]))

    facts: list[FactOutcome] = []
    for index, fact in enumerate(script.facts):
        line_tokens = content_tokens(script.lines[fact.line].text)
        judged: set[_Judged] = set()
        for start in _occurrences(line_tokens, fact.tokens):
            first = offsets[fact.line] + start
            for state in _fact_end_states(alignment, first, first + len(fact.tokens) - 1, infos):
                judged.add(_judge(state, fact.kind, fact.expect_uncertain))
        worst = max(judged, key=_severity)
        # Round 11 LOW-008: surfacing is judged on its own, conservatively —
        # the worst verdict's alternative may surface the uncertainty while
        # an equal-cost alternative does not; it is surfaced only if every
        # alternative surfaces it.
        surfaced = all(j.surfaced for j in judged) if fact.expect_uncertain else None
        facts.append(
            FactOutcome(
                fact_index=index,
                kind=fact.kind,
                material=fact.material,
                verdict=worst.verdict,
                warned=worst.warned,
                uncertainty_surfaced=surfaced,
                not_transcribed=worst.not_transcribed,
                ambiguous=len(judged) > 1,
                # Peer round 14 (PR-MED-056): the silent-omission tally is
                # conservative on its own, like surfacing above.
                silently_omitted_somewhere=any(
                    j.verdict == "omitted" and not j.warned for j in judged
                ),
            )
        )

    tally = Counter(warning.note_warning_code for warning in note.note_warnings)
    expected = set(script.expected_warnings)
    failing = sorted(
        code
        for code in tally
        if code not in expected
        and (NOTE_WARNING_SEVERITY[code] == "error" or code in CONTRADICTION_CODES)
    )
    return EncounterMetrics(
        words=WordErrors(len(reference), len(hypothesis), alignment.total),
        transcript_lines=len(lines),
        config_lines=config_lines,
        unsupported_clinical_lines=unsupported_lines,
        other_unsupported_words=len(other_words),
        checker_tally=tuple(sorted(tally.items())),
        checker_failures=tuple(failing),
        checker_failure_count=sum(tally[code] for code in failing),
        expected_warnings_absent=tuple(sorted(expected - set(tally))),
        facts=tuple(facts),
    )


# ---------------------------------------------------------------------------
# The pass rule (data — decision 3.5 ratifies one) and its evaluation.
# ---------------------------------------------------------------------------

RuleFailure = Literal[
    "harness_error",
    "role_unresolved",
    "unsupported_clinical_line",
    "checker_failure",
    "material_wrong",
    "silent_omission",
    "uncertainty_not_surfaced",
    "word_error_rate",
    "prose_unavailable",
]


class PassRule(BaseModel):
    """The pass rule, as data (Task 2.4). Five failures are fixed by the
    metric contract and design, not by the rule: a harness error and an
    unresolved role (D9), any unsupported clinical line and any checker
    failure (Task 2.3), and a requested prose stage that could not run. The
    rule sets the rest; option (a) of decision 3.5 is every default here."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    schema_version: Literal[1]
    rule_name: str = Field(pattern=RULE_NAME_PATTERN)
    max_material_wrong: int = Field(default=0, ge=0)
    max_silent_omissions: int = Field(default=0, ge=0)
    require_uncertainty_surfaced: bool = True
    max_word_error_rate: float | None = Field(default=None, ge=0.0)


def load_pass_rule(path: Path) -> PassRule:
    try:
        blob = path.read_bytes()
    except OSError as exc:
        raise RuleError(f"{path.name}: unreadable ({type(exc).__name__})") from None
    try:
        return PassRule.model_validate_json(blob)
    except ValidationError as exc:
        raise RuleError(f"{path.name}: {_validation_error_text(exc)}") from None


# ---------------------------------------------------------------------------
# Task 2.4 — the runner.
# ---------------------------------------------------------------------------

EncounterStatus = Literal["measured", "role_unresolved", "error"]
_STATUSES: Final[tuple[str, ...]] = get_args(EncounterStatus)
# Two clusters holding the clinician's seconds within this are a tie: no
# cluster is chosen by its name (the speaker_eval float-noise tolerance).
ROLE_TIE_SECONDS: Final = 1e-9


@dataclass(frozen=True)
class ProseCounts:
    """The optional narrative prose stage: sections passed, failed (Check 5
    kept ``clean``) and errored, and ``unavailable`` when the stage could
    not run at all (the model missing or failing to load — round 11
    MED-007: a stage that never ran must not read as ``0/0/0``). Counts
    only — no prose is kept."""

    passed: int
    failed: int
    errored: int
    unavailable: bool = False

    def __post_init__(self) -> None:
        for name in ("passed", "failed", "errored"):
            _require_count(getattr(self, name), name)
        if not isinstance(self.unavailable, bool):
            raise ValueError("unavailable must be a flag")


@dataclass(frozen=True)
class EncounterOutcome:
    """One encounter's result: its id (pattern-constrained), its status, the
    exception TYPE name for an ``error``, the word errors when a transcript
    exists, the metrics when a note was finalised, and the prose counts."""

    encounter_id: str
    status: EncounterStatus
    error_type: str | None = None
    segment_count: int = 0
    words: WordErrors | None = None
    metrics: EncounterMetrics | None = None
    prose: ProseCounts | None = None

    def __post_init__(self) -> None:
        if not _ENCOUNTER_ID_RE.fullmatch(self.encounter_id):
            raise ValueError("encounter_id must match the id pattern")
        _require_member(self.status, _STATUSES, "status")
        if self.error_type is not None and not _ERROR_TYPE_RE.fullmatch(self.error_type):
            raise ValueError("error_type must be an exception type name")
        _require_count(self.segment_count, "segment_count")
        # Round 12 LOW-002 (Constraint 7 at run time, as round 11 LOW-012
        # did for ``EncounterMetrics``): what the rule and the report read
        # is the validated type, never a string.
        for name, kind in (
            ("words", WordErrors),
            ("metrics", EncounterMetrics),
            ("prose", ProseCounts),
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, kind):
                raise ValueError(f"{name} must be a {kind.__name__}")


def rule_failures(rule: PassRule, outcome: EncounterOutcome) -> tuple[RuleFailure, ...]:
    """Why ``outcome`` fails ``rule`` — empty when it passes."""
    if outcome.status == "error":
        return ("harness_error",)
    if outcome.status == "role_unresolved":
        return ("role_unresolved",)
    metrics = outcome.metrics
    if metrics is None:
        return ("harness_error",)
    failures: list[RuleFailure] = []
    if metrics.unsupported_clinical_lines:
        failures.append("unsupported_clinical_line")
    if metrics.checker_failure_count:
        failures.append("checker_failure")
    if metrics.material_wrong > rule.max_material_wrong:
        failures.append("material_wrong")
    if metrics.silent_omissions > rule.max_silent_omissions:
        failures.append("silent_omission")
    if rule.require_uncertainty_surfaced and metrics.uncertainty_missed:
        failures.append("uncertainty_not_surfaced")
    if rule.max_word_error_rate is not None and metrics.words.rate > rule.max_word_error_rate:
        failures.append("word_error_rate")
    if outcome.prose is not None and outcome.prose.unavailable:
        # Asked for (--prose) and not measured: the run did not do its job.
        failures.append("prose_unavailable")
    return tuple(failures)


def clinician_speaker(document: TranscriptDocument, track: LabelTrack) -> str | None:
    """The cluster confirmed as the clinician, from the timed label track
    (D9): the cluster whose duration-weighted majority true label is
    ``clinician`` (``speaker_eval.align_segments`` gives each segment its
    truth). None — "role unresolved" — when no cluster's majority is the
    clinician, or when the two leading such clusters hold the clinician's
    seconds equally (within ``ROLE_TIE_SECONDS``): never a guess."""
    segments = [
        SpeechSegment(start_seconds=s.start_seconds, end_seconds=s.end_seconds)
        for s in document.transcript_segments
    ]
    truths = align_segments(segments, track)
    seconds: dict[str, dict[str, list[float]]] = {}
    for segment, truth in zip(document.transcript_segments, truths, strict=True):
        if truth.true_label is None:
            continue
        seconds.setdefault(segment.speaker, {}).setdefault(truth.true_label, []).append(
            truth.duration_seconds
        )
    clinician_clusters: list[tuple[float, str]] = []
    for cluster, by_label in seconds.items():
        totals = sorted(
            ((math.fsum(parts), label) for label, parts in by_label.items()), reverse=True
        )
        lead_seconds, lead_label = totals[0]
        if len(totals) > 1 and lead_seconds - totals[1][0] <= ROLE_TIE_SECONDS:
            continue  # a tie is not a majority
        if lead_label == CLINICIAN_LABEL:
            clinician_clusters.append((lead_seconds, cluster))
    if not clinician_clusters:
        return None
    clinician_clusters.sort(reverse=True)
    if (
        len(clinician_clusters) > 1
        and clinician_clusters[0][0] - clinician_clusters[1][0] <= ROLE_TIE_SECONDS
    ):
        return None
    return clinician_clusters[0][1]


def confirm_all(draft: NoteDraft, now: datetime) -> list[ProposalResolution]:
    """D9's declared proposal policy, through the review surface's own
    ``build_resolutions``: every proposal with a row is CONFIRMED with the
    digest of its exact text, and every pre-filled line the config decided
    stands (its minted decision passes on), as when the practitioner confirms
    every row and removes nothing. Because this confirms what a clinician
    might decline, the checker's warnings on the finalised note count
    against the encounter (the checker tally)."""
    prefilled = prefilled_ids(draft)
    decisions: dict[str, ProposalDecision] = {
        proposal.proposal_id: "confirmed"
        for proposal in draft.note_proposals
        if proposal.proposal_id not in prefilled
    }
    return build_resolutions(
        draft,
        resolutions=decisions,
        removed=(),
        edited_proposals=(),
        rendered_excerpt={p.proposal_id: p.note_excerpt for p in draft.note_proposals},
        now=now,
    )


def first_detected_prefill(document: TranscriptDocument, config: NoteConfig) -> str | None:
    """D9's declared region policy: the EARLIEST detected body-region prefill
    (``note_fill.detect_prefill_candidates`` order), so several detections
    choose the first rather than stopping at the chooser; None when none."""
    candidates = detect_prefill_candidates(document, config)
    return candidates[0].prefill_id if candidates else None


def _default_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class HarnessInputs:
    """Everything one run needs, injected so tests run no real model: the
    speech provider and VAD frame probability, the config loaded from the
    explicit folder, the template profile (None = the config's only one),
    the note-provider factory (default: the extractive provider built from
    the config's own cues) and the optional prose stage."""

    provider: SpeechProvider
    frame_probability: FrameProbabilityFn
    config: NoteConfig
    template_profile_id: str | None = None
    note_provider_factory: Callable[[NoteConfig], NoteModelProvider] = (
        extractive_provider_from_config
    )
    prose_stage: ProseStage | None = None
    now: Callable[[], datetime] = _default_now


def evaluate_encounter(
    encounter_id: str, script: EncounterScript, wav: Path, labels: Path, inputs: HarnessInputs
) -> EncounterOutcome:
    """One encounter through the shipped pipeline (Task 2.4). Raises
    ``SpeakerEvalError`` when the temporary store cannot be shown gone
    (custody: the caller stops the run) and any input or pipeline error as
    itself; the label track and WAV are validated BEFORE any store exists."""
    track = parse_audacity_labels(labels.read_text(encoding="utf-8-sig"))
    pcm = read_wav_pcm(wav)
    document, _enrolled = transcribe_in_temporary_store(
        pcm, inputs.provider, inputs.frame_probability
    )
    del pcm
    words = word_errors(document, script)
    segment_count = len(document.transcript_segments)
    clinician = clinician_speaker(document, track)
    if clinician is None:
        return EncounterOutcome(
            encounter_id, "role_unresolved", segment_count=segment_count, words=words
        )
    config = inputs.config
    now = inputs.now()
    draft = compose_draft(
        document,
        config,
        inputs.note_provider_factory(config),
        inputs.template_profile_id,
        clinician_speaker=clinician,
        prefill_id=first_detected_prefill(document, config),
        learned_rules=None,
        decided_at=now,
    )
    note = finalise_note(draft, confirm_all(draft, now), document, config, created_at=now)
    prose: ProseCounts | None = None
    if inputs.prose_stage is not None:
        result = inputs.prose_stage(note)
        # ``reason`` is set exactly when nothing could be rendered (the
        # model missing or failing to load) — never for a section verdict.
        prose = ProseCounts(
            result.passed, result.failed, result.errored, unavailable=result.reason is not None
        )
    return EncounterOutcome(
        encounter_id,
        "measured",
        segment_count=segment_count,
        words=words,
        metrics=encounter_metrics(document, note, script),
        prose=prose,
    )


def run_encounters(
    encounters: Sequence[EncounterFiles],
    inputs: HarnessInputs,
    *,
    progress: Callable[[str], None] = print,
) -> list[EncounterOutcome]:
    """Every encounter in turn. A script, input or pipeline failure becomes
    an ``error`` outcome reported by exception TYPE (never its text) and the
    run continues; a custody fault (``SpeakerEvalError``: a temporary store
    that cannot be shown gone) propagates and stops the run, naming the
    path."""
    outcomes: list[EncounterOutcome] = []
    for files in encounters:
        progress(f"[run ] {files.encounter_id}")
        try:
            script = load_script(files.script)
        except ScriptError as exc:
            progress(f"[error] {exc}")
            outcomes.append(EncounterOutcome(files.encounter_id, "error", "ScriptError"))
            continue
        try:
            outcomes.append(
                evaluate_encounter(files.encounter_id, script, files.wav, files.labels, inputs)
            )
        except RecordingRefusedError as exc:
            # A label track or WAV refused before any store existed. A WAV
            # refusal's text is speaker_eval's own (formats and the remedy);
            # a label-track refusal can quote the labels typed in the file,
            # so only its type is printed (round 11 LOW-007).
            detail = (
                "the label track was refused - check it against "
                "docs/testing/speaker-measurement.md"
                if isinstance(exc, LabelTrackError)
                else str(exc)
            )
            progress(f"[error] {files.encounter_id}: {type(exc).__name__}: {detail}")
            outcomes.append(EncounterOutcome(files.encounter_id, "error", type(exc).__name__))
        except SpeakerEvalError:
            raise  # custody: a temporary store not shown gone stops the run
        except Exception as exc:  # noqa: BLE001 - reported by TYPE only, run continues
            progress(f"[error] {files.encounter_id}: {type(exc).__name__}")
            outcomes.append(EncounterOutcome(files.encounter_id, "error", type(exc).__name__))
    return outcomes


# ---------------------------------------------------------------------------
# The report (text-free: ids, numbers, flags and closed vocabularies).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunInfo:
    """What the report's header names: the models and the build."""

    whisper_model: str
    whisper_fallback: bool
    vad_model: str
    prose: str | None
    commit: str | None
    models_manifest_sha256: str | None


def run_passed(rule: PassRule, outcomes: Sequence[EncounterOutcome], *, errors: int = 0) -> bool:
    """The run passes when at least one encounter ran, no set-level error
    occurred and every encounter passes ``rule``."""
    return bool(outcomes) and not errors and all(not rule_failures(rule, o) for o in outcomes)


def _rate(value: float) -> str:
    return f"{value:.3f}"


def _flag(value: bool | None) -> str:
    return "-" if value is None else ("yes" if value else "no")


def render_report(
    outcomes: Sequence[EncounterOutcome], rule: PassRule, info: RunInfo, *, errors: int = 0
) -> str:
    """The Markdown report. Every printed field comes from the result types
    (numbers, flags, closed vocabularies, synthetic ids), the rule and the
    run information — no transcript, note or script text."""
    verdict = "PASS" if run_passed(rule, outcomes, errors=errors) else "FAIL"
    lines = [
        f"## Validation run - rule `{rule.rule_name}` - {verdict}",
        "",
        f"Whisper model `{info.whisper_model}`"
        + (" (FALLBACK - --allow-small)" if info.whisper_fallback else "")
        + f"; VAD `{info.vad_model}`; prose stage `{info.prose or 'off'}`; "
        f"commit `{info.commit or 'unknown'}`; models manifest SHA-256 "
        f"`{info.models_manifest_sha256 or 'absent'}`. Encounters: {len(outcomes)}; "
        f"set-level errors: {errors}.",
        "",
        "| Encounter | Status | Segments | Ref words | WER | Unsupported clinical lines "
        "| Other unsupported words | Transcript lines | Config lines | Facts | Correct "
        "| Wrong (material) | Omitted | Silent omissions | Warned omissions "
        "| Uncertainty missed | Ambiguous facts | Checker failures | Prose p/f/e | Rule |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    totals = Counter[str]()
    for outcome in outcomes:
        failures = rule_failures(rule, outcome)
        words = outcome.words
        metrics = outcome.metrics
        wer = _rate(words.rate) if words is not None else "-"
        ref = str(words.reference_tokens) if words is not None else "-"
        if words is not None:
            totals["ref"] += words.reference_tokens
            totals["distance"] += words.edit_distance
        if metrics is None:
            cells = ["-"] * 14
        else:
            facts = metrics.facts
            counts = {
                "unsupported": metrics.unsupported_clinical_lines,
                "other": metrics.other_unsupported_words,
                "facts": len(facts),
                "correct": sum(1 for f in facts if f.verdict in ("correct", "correctly_absent")),
                "wrong": metrics.material_wrong,
                "omitted": sum(1 for f in facts if f.verdict == "omitted"),
                "silent": metrics.silent_omissions,
                "warned": metrics.warned_omissions,
                "missed": metrics.uncertainty_missed,
                "ambiguous": metrics.ambiguous_facts,
                "checker": metrics.checker_failure_count,
            }
            totals.update(counts)
            prose = outcome.prose
            cells = [
                str(counts["unsupported"]),
                str(counts["other"]),
                str(metrics.transcript_lines),
                str(metrics.config_lines),
                str(counts["facts"]),
                str(counts["correct"]),
                str(counts["wrong"]),
                str(counts["omitted"]),
                str(counts["silent"]),
                str(counts["warned"]),
                str(counts["missed"]),
                str(counts["ambiguous"]),
                str(counts["checker"]),
                "-"
                if prose is None
                else "unavailable"
                if prose.unavailable
                else f"{prose.passed}/{prose.failed}/{prose.errored}",
            ]
        status = outcome.status + (f" ({outcome.error_type})" if outcome.error_type else "")
        lines.append(
            f"| {outcome.encounter_id} | {status} | {outcome.segment_count} | {ref} | {wer} | "
            + " | ".join(cells)
            + f" | {'PASS' if not failures else 'FAIL: ' + ', '.join(failures)} |"
        )
    total_wer = _rate(totals["distance"] / totals["ref"]) if totals["ref"] else "-"
    lines.append(
        f"| TOTAL | {sum(1 for o in outcomes if o.status == 'measured')} measured | - "
        f"| {totals['ref']} | {total_wer} | {totals['unsupported']} | {totals['other']} | - | - "
        f"| {totals['facts']} | {totals['correct']} | {totals['wrong']} | {totals['omitted']} "
        f"| {totals['silent']} | {totals['warned']} | {totals['missed']} "
        f"| {totals['ambiguous']} | {totals['checker']} | - | {verdict} |"
    )

    lines += ["", "### Checker warnings (code = count)", ""]
    for outcome in outcomes:
        if outcome.metrics is None:
            continue
        metrics = outcome.metrics
        tally = ", ".join(f"{code}={count}" for code, count in metrics.checker_tally) or "none"
        extra = ""
        if metrics.checker_failures:
            extra += "; failing: " + ", ".join(metrics.checker_failures)
        if metrics.expected_warnings_absent:
            extra += "; expected but absent: " + ", ".join(metrics.expected_warnings_absent)
        lines.append(f"- {outcome.encounter_id}: {tally}{extra}")

    lines += [
        "",
        "### Facts",
        "",
        "| Encounter | Fact | Kind | Material | Verdict | Warned | Uncertainty surfaced "
        "| Not transcribed | Ambiguous |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for outcome in outcomes:
        if outcome.metrics is None:
            continue
        for fact in outcome.metrics.facts:
            lines.append(
                f"| {outcome.encounter_id} | {fact.fact_index} | {fact.kind} "
                f"| {_flag(fact.material)} | {fact.verdict} | {_flag(fact.warned)} "
                f"| {_flag(fact.uncertainty_surfaced)} | {_flag(fact.not_transcribed)} "
                f"| {_flag(fact.ambiguous)} |"
            )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The command line (the ``speaker_eval.main`` shape). Run by the PRACTITIONER
# from a normal terminal on the developer build (docs/lessons.md: agent
# shells cannot see the user's model folder).
# ---------------------------------------------------------------------------

# validation.py -> scribe_desktop -> src -> desktop -> the repository.
REPO_ROOT: Final = Path(__file__).resolve().parents[3]
MODELS_MANIFEST: Final = Path("packaging") / "models-manifest.json"
_COMMIT_RE: Final = re.compile(r"^[0-9a-f]{40}$")


def read_commit(repo_root: Path) -> str | None:
    """The checked-out commit, read from ``.git`` files (no process is
    started): ``HEAD`` itself, or the branch it names, loose or packed.
    None when it cannot be read — the report then says ``unknown``. It
    cannot say whether the working tree differs from the commit."""
    git = repo_root / ".git"
    try:
        head = (git / "HEAD").read_text(encoding="ascii").strip()
        if not head.startswith("ref: "):
            return head if _COMMIT_RE.fullmatch(head) else None
        ref = head.removeprefix("ref: ").strip()
        try:
            value = (git / ref).read_text(encoding="ascii").strip()
        except FileNotFoundError:
            value = ""
            for line in (git / "packed-refs").read_text(encoding="ascii").splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1] == ref:
                    value = parts[0]
        return value if _COMMIT_RE.fullmatch(value) else None
    except (OSError, UnicodeDecodeError):
        return None


def models_manifest_sha256(repo_root: Path) -> str | None:
    """SHA-256 of the committed ``packaging/models-manifest.json`` (the model
    set a release pins), or None when it is absent or unreadable."""
    try:
        return hashlib.sha256((repo_root / MODELS_MANIFEST).read_bytes()).hexdigest()
    except OSError:
        return None


def _carries_learned_content(config_dir: Path, config: NoteConfig) -> bool:
    """Whether ``config_dir`` looks like a copy of the app's own config: it
    holds a learned-phrase or learned-rule sidecar, or a ``learned-`` rule
    (round 11 MED-008 — ``confirm_all`` would confirm a learned rule's
    proposals). Learned phrases already merged into a copied
    ``section_cues.json`` carry no mark and cannot be detected."""
    if any(
        (config_dir / name).exists()
        for name in (LEARNED_SIDECAR_FILENAME, LEARNED_RULES_SIDECAR_FILENAME)
    ):
        return True
    return any(is_learned_rule_id(rule.rule_id) for rule in config.autofill_rules)


def _own_config_folders() -> set[str]:
    """The app's own config folders, both channels — the folders D9 says
    the harness never reads."""
    channels: tuple[install_layout.Channel, ...] = ("production", "dev")
    folders: set[str] = set()
    for channel in channels:
        try:
            folders.add(_normalised(install_layout.data_root(channel) / CONFIG_DIRNAME))
        except (OSError, RuntimeError):
            continue
    return folders


def _normalised(path: Path) -> str:
    """Absolute and case-folded, by string only — no filesystem read, so a
    link to the app's folder under another name is not recognised (the
    plan's same-user residue)."""
    return os.path.normcase(os.path.abspath(path))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the validation harness (pilot plan Phase 2) over a set folder of "
            "<id>.json + <id>.wav + <id>.txt encounters, through the shipped pipeline, and "
            "print a text-free report scored against the pass rule. Developer build only."
        )
    )
    parser.add_argument("set_dir", type=Path, help="folder of encounter files (see the docs)")
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help=(
            "an explicit note-config folder (files absent from it fall back to the shipped "
            "defaults); never the app's own config folder"
        ),
    )
    parser.add_argument("--rule", type=Path, required=True, help="the pass-rule JSON file")
    parser.add_argument(
        "--template-profile", default=None, help="template profile id (default: the only one)"
    )
    parser.add_argument(
        "--allow-small",
        action="store_true",
        help="measure with whisper `small` when `medium` is not installed (the report says so)",
    )
    parser.add_argument(
        "--prose",
        action="store_true",
        help="also run the narrative prose stage and report its section counts",
    )
    return parser


def main(argv: list[str] | None = None, *, repo_root: Path = REPO_ROOT) -> int:
    """Exit status 0 only when the run passed; 2 for a refusal before any
    model is built; 1 otherwise. Refusals, in order: a packaged build
    (``install_layout.channel``, read at call time — the tests' seam), a
    missing set or config folder, the app's own config folder, an unusable
    rule or config, a config carrying the app's learned content, a template
    profile that cannot be bound, then the models (by name, before any is
    constructed) and an unreadable set folder."""
    configure_output()
    args = _parser().parse_args(argv)
    if install_layout.channel() != "dev":
        print("[refused] the validation harness runs only on the developer build")
        return 2
    apply_offline_env()
    assert_offline_env()
    set_dir: Path = args.set_dir
    config_dir: Path = args.config
    if not set_dir.is_dir():
        print(f"[refused] {set_dir} is not a folder")
        return 2
    if not config_dir.is_dir():
        print(f"[refused] --config {config_dir} is not a folder")
        return 2
    if _normalised(config_dir) in _own_config_folders():
        print(
            f"[refused] --config {config_dir} is the app's own config folder; use "
            "validation\\config or a folder of files you wrote for the run (never a copy of "
            "the app's own: it carries learned phrases and rules)"
        )
        return 2
    try:
        rule = load_pass_rule(args.rule)
    except RuleError as exc:
        print(f"[refused] {exc}")
        return 2
    try:
        config = load_note_config(config_dir)
    except NoteConfigError as exc:
        # The loader's detail reproduces the rejected file text (not
        # log-safe, note_config's own warning): the type only (round 11
        # LOW-001).
        print(
            f"[refused] --config {config_dir}: a config file is unreadable or malformed "
            f"({type(exc).__name__}) - check each JSON file against the shipped defaults"
        )
        return 2
    if _carries_learned_content(config_dir, config):
        print(
            f"[refused] --config {config_dir} carries the app's learned phrases or rules (a "
            "copy of the app's own config); use validation\\config or a folder you wrote"
        )
        return 2
    try:
        # The profile ``compose_draft`` will bind, resolved now so a bad
        # ``--template-profile`` (or several profiles and none chosen) is a
        # refusal before any model is built, not an error on every
        # encounter after a full transcription (round 12 LOW-009).
        bind_template_profile(config, args.template_profile)
    except NoteConfigError as exc:
        print(
            f"[refused] --config {config_dir}: no template profile can be bound "
            f"({type(exc).__name__}) - pass --template-profile with one of the config's "
            "profile ids"
        )
        return 2

    try:
        models = install_layout.models_root()
    except (OSError, RuntimeError) as exc:
        print(f"[refused] the models folder cannot be located ({type(exc).__name__})")
        return 2
    whisper = resolve_whisper_model()
    if not whisper_model_available(whisper):
        print(
            f"[refused] no Whisper model is installed in {models}: "
            f"{install_layout.model_remedy()}"
        )
        return 2
    fallback = whisper != DEFAULT_WHISPER_MODEL
    if fallback and not args.allow_small:
        print(
            f"[refused] Whisper `{DEFAULT_WHISPER_MODEL}` is not installed in {models} (only "
            f"`{whisper}` is): {install_layout.model_remedy()}, or pass --allow-small to "
            "measure with it"
        )
        return 2
    if not vad_model_available():
        print(
            f"[refused] the silero VAD model is not installed in {models}: "
            f"{install_layout.model_remedy()}"
        )
        return 2
    if args.prose and not language_model_available():
        print(
            f"[refused] --prose: the language model is not installed in {models}: "
            f"{install_layout.model_remedy('language-model')}"
        )
        return 2

    try:
        encounters, incomplete = find_encounters(set_dir)
    except OSError as exc:
        print(f"[refused] {set_dir} cannot be listed ({type(exc).__name__})")
        return 2
    errors = 0
    for name, problem in incomplete:
        errors += 1
        print(f"[error] {name}: {problem}")
    if not encounters:
        print(f"[error] no complete encounters in {set_dir}")
        return 1

    vad = SileroVad()
    inputs = HarnessInputs(
        provider=WhisperSpeechProvider(model_name=whisper),
        frame_probability=vad.frame_probability,
        config=config,
        template_profile_id=args.template_profile,
        prose_stage=build_prose_stage("narrative") if args.prose else None,
    )
    try:
        outcomes = run_encounters(encounters, inputs)
    except SpeakerEvalError as exc:
        print(f"[custody] the run stopped: {exc}")
        return 1
    info = RunInfo(
        whisper_model=whisper,
        whisper_fallback=fallback,
        vad_model="silero",
        prose="narrative" if args.prose else None,
        commit=read_commit(repo_root),
        models_manifest_sha256=models_manifest_sha256(repo_root),
    )
    print()
    print(render_report(outcomes, rule, info, errors=errors))
    return 0 if run_passed(rule, outcomes, errors=errors) else 1


__all__ = [
    "AXES",
    "CONTRADICTION_CODES",
    "ENCOUNTER_ID_PATTERN",
    "FACT_KINDS",
    "FACT_VERDICTS",
    "REPO_ROOT",
    "ROLE_TIE_SECONDS",
    "SCRIPT_SCHEMA_VERSION",
    "UNNAMED_ENCOUNTER",
    "EncounterFiles",
    "EncounterMetrics",
    "EncounterOutcome",
    "EncounterScript",
    "ExpectedFact",
    "FactOutcome",
    "HarnessInputs",
    "PassRule",
    "ProseCounts",
    "RuleError",
    "RunInfo",
    "ScriptError",
    "ScriptLine",
    "SyntheticConditions",
    "ValidationHarnessError",
    "WordErrors",
    "clinician_speaker",
    "confirm_all",
    "encounter_metrics",
    "evaluate_encounter",
    "find_encounters",
    "first_detected_prefill",
    "is_structured_claim_word",
    "load_pass_rule",
    "load_script",
    "load_script_with_bytes",
    "main",
    "models_manifest_sha256",
    "read_commit",
    "render_report",
    "rule_failures",
    "run_encounters",
    "run_passed",
    "word_errors",
]


if __name__ == "__main__":
    sys.exit(main())
