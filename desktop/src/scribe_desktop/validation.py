"""Pilot plan Phase 2: the validation harness (developer build only).

An offline batch run of the SHIPPED pipeline over synthetic and recorded
encounters, scored against each encounter's own script (pilot plan D8, D9).
"Role-play" in this module's names means a recorded script — one without
synthetic ``conditions`` (the clinic 1 smoke retired the role-play set,
``plan-clinic-smoke.md`` D1; the behaviour is unchanged):

- **The encounter script** (Task 2.2, ``EncounterScript``): the reference
  lines in spoken order, the expected facts with the reference line that
  states each, the checker warnings the encounter is written to provoke, and
  the conditions the synthetic set builder (``validation_set``) applies. A
  set folder holds, for every encounter, ``<id>.json`` + ``<id>.wav`` (the
  ``speaker_eval.read_wav_pcm`` contract) + ``<id>.txt`` (the Audacity label
  track ``docs/testing/speaker-measurement.md`` defines), so a folder of
  recorded encounters made for ``measure-speakers.py`` loads once its JSON
  is added
  (its file names must be encounter ids: lower-case letters, digits and
  hyphens).
- **The metrics** (Task 2.3, ``encounter_metrics``): ONE word-level
  alignment between the script's reference tokens and the transcript's words
  — the edit-distance alignment that yields the word error rate — carries
  every judgement; nothing is decided per segment. Since the metric
  amendment of 2026-10-11 both sides are compared after canonical spelling
  (``canonical_tokens``: "500mg", "500 milligrams" and "five hundred mg"
  all read "500 mg"); the replay tool's alignment never is. Pure
  functions; outputs are numbers, flags and closed-vocabulary verdicts
  only.
- **The runner** (Task 2.4, ``evaluate_encounter`` / ``main``): per
  encounter, transcription in a temporary encrypted store torn down key-first
  (``speaker_eval.transcribe_in_temporary_store``, reused IN PLACE), the
  clinician attributed as the app does — with an enrolment of the script's
  clinician voice (the builder's passage, ``<set>/enrolment/``; metric
  amendment 2026-10-23, validation-run6 plan D11) — and CONFIRMED by the
  timed label track (``speaker_eval.align_segments``), or, with
  ``--attribution clustering``, chosen from the label track alone (runs
  1-5's reading), ``compose_draft`` with the extractive
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
  shown gone stops the run with the path named. The enrolment profiles live
  in this process only (``speaker_eval.EnrolmentInputs``; never a profile
  store, never printed). No audit row and no
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
import tempfile
from array import array
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, NamedTuple, Protocol, get_args

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from scribe_desktop import install_layout
from scribe_desktop.benchmark import apply_offline_env, assert_offline_env
from scribe_desktop.enrolment import EnrolmentError
from scribe_desktop.note import (
    NOTE_WARNING_SEVERITY,
    GeneratedNote,
    NoteDraft,
    NoteModelProvider,
    ProposalResolution,
    compose_draft,
    content_tokens,
    finalise_note,
    strip_token_punctuation,
    text_holds_hedge,
    words_hold_hedge,
)

# Package-private by name, shared deliberately (the note.py convention):
# the structured-claim word classes and the omission check's predicates
# are READ here, never re-spelled, so the harness and the checker cannot
# disagree about what a side, a dose or a negation is. Since the metric
# amendment of 2026-10-09 (note-routing-omissions plan D3, decision 0.2
# (b)) ``warned`` reads Check 4's predicate ``_omission_flag_token``;
# ``_is_high_risk_token`` stays for the run-1 comparison column. The
# metric amendment of 2026-10-11 (D10) reads the strength-unit table and
# the number-with-suffix pattern for its canonical spelling. The metric
# amendment of 2026-10-13 (D7) reads a hedge mark's words through the
# checker's own coordinate resolver (stage-9 simplify round 29 SIMP-001).
# Validation-run6 Task 0.9 reads ``HEDGE_PHRASES`` as the head of the
# reference lexicon ``REFERENCE_HEDGES``.
from scribe_desktop.note_check import (
    _LATERALITY_TOKENS,
    _NUMBER_WITH_SUFFIX_RE,
    _STRENGTH_UNITS,
    HEDGE_PHRASES,
    _dose_quantity,
    _is_high_risk_token,
    _omission_flag_token,
    _polarity_mark,
    _words_for_coords,
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
from scribe_desktop.speaker_embedding import build_speaker_embedder, speaker_model_available
from scribe_desktop.speaker_eval import (
    CLINICIAN_LABEL,
    TEMP_DIR_PREFIX,
    WAV_FORMAT_HELP,
    EnrolmentInputs,
    LabelTrack,
    LabelTrackError,
    RecordingRefusedError,
    SpeakerEvalError,
    WavFormatError,
    align_segments,
    configure_output,
    enrolment_inputs,
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
    TranscriptSegment,
    TranscriptWord,
    WhisperSpeechProvider,
    is_number_token,
    resolve_whisper_model,
    whisper_model_available,
    words_hold_suspect,
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
# Round 26: the other two files a run reads whole are capped too.
MAX_RULE_BYTES: Final = 64 * 1024
MAX_LABEL_TRACK_BYTES: Final = 4 * 1024 * 1024

# The axes of PLAN.md's AI-quality list (L188-201). ``noise``, ``overlap``
# and ``rate`` are applied by the synthetic conditions. Accent is a property
# of the voice, not an axis: a third installed voice carries it in the
# synthetic set, and real-speech accents are the clinic 1 smoke's aggregate
# count (``plan-clinic-smoke.md`` D4).
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
    script (a "role-play" in this module's names)."""

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


# ---------------------------------------------------------------------------
# Validation-run6 plan D8 — the reference transcript (one builder, two
# adapters; moved from the held-out fixture in Task 0.9, unchanged).
# ---------------------------------------------------------------------------

_REFERENCE_SESSION_ID: Final = "0123456789abcdef" * 2
_REFERENCE_CREATED_AT: Final = datetime(2026, 10, 13, tzinfo=UTC)
_REFERENCE_WORD_MS: Final = 300
_REFERENCE_GAP_MS: Final = 600
_REFERENCE_PROBABILITY: Final = 0.95
REFERENCE_MODEL_NAME: Final = "heldout-fixture"


class SpokenTurn(Protocol):
    """One segment's speaker label and text ("" for a segment with no
    words) — the held-out fixture's ``Turn`` satisfies it."""

    @property
    def speaker(self) -> str: ...

    @property
    def text(self) -> str: ...


@dataclass(frozen=True)
class _LineTurn:
    speaker: str
    text: str


def document_from_turns(turns: Iterable[SpokenTurn]) -> TranscriptDocument:
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
                    end_seconds=(clock + _REFERENCE_WORD_MS) / 1000,
                    probability=_REFERENCE_PROBABILITY,
                    uncertain=False,
                )
            )
            clock += _REFERENCE_WORD_MS
        segments.append(
            TranscriptSegment(
                start_seconds=start / 1000,
                end_seconds=clock / 1000,
                speaker=turn.speaker,
                transcript_words=tuple(words),
            )
        )
        clock += _REFERENCE_GAP_MS
    return TranscriptDocument(
        session_id=_REFERENCE_SESSION_ID,
        created_at=_REFERENCE_CREATED_AT,
        model_name=REFERENCE_MODEL_NAME,
        sample_rate=16_000,
        transcript_segments=tuple(segments),
    )


def reference_document(script: EncounterScript) -> TranscriptDocument:
    """The script's own words as a transcript: one segment per line, the
    line's role as its speaker label (D8's reference for R1)."""
    return document_from_turns(_LineTurn(line.role, line.text) for line in script.lines)


# D8's R2 reference lexicon, frozen in Task 0.9 (2026-10-23) by the same
# BLIND session as the widened ``HEDGE_PHRASES``, harness-only: a script
# line holding one of these (whole tokens in a row, as
# ``note.text_holds_hedge`` reads) voices its doubt in WORDS, so a fact on it
# is never "tone only". The product's list plus what its selection rule
# keeps out of the app but which still voices doubt: the session's
# unverified or self-rendered entries, the four possibility modals and the
# attribution shields of the sources, and statements of the limits of
# knowledge. Approximators, frequency words, fillers and words with a common
# plain sense stay out of both — they mark imprecision, not doubt (Prince,
# Frader & Bosk's shield/approximator split). Sources: Namsaraev (1997),
# Shomoossi & Shokrpour (2024), Fraser (2010), Hyland (2005) and Coates
# (2013) for the modals; Prince, Frader & Bosk (1982) for the attribution
# shields; Huddleston & Pullum (2002) and Biber et al. (1999) for the
# evidential adverbs; Visser et al. (2020) for the knowledge limits;
# Kärkkäinen (2003) for the two stance phrases. Never read by the app.
_REFERENCE_ONLY_HEDGES: Final[tuple[str, ...]] = (
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
REFERENCE_HEDGES: Final[tuple[str, ...]] = (*HEDGE_PHRASES, *_REFERENCE_ONLY_HEDGES)


# D8's R3 reference provenance, frozen in Task 0.9 (synthetic scripts only;
# ``heldout-2`` joins in Task 0.12): for EVERY script carrying the axis
# ``end_and_new_patient``, the line holding the next patient's greeting and
# the first line withheld — two tables, since a closing and a greeting can
# share a line (``hld-11``). None means the script has no next patient (a
# negative), so no fact of it is ever R3; a script with the axis and no
# entry is a harness error. The tail starts equal the held-out fixture's
# ``boundary`` wherever it has one.
REFERENCE_GREETING_LINES: Final[Mapping[str, int | None]] = {
    "syn-06": 4,
    "syn-20": 4,
    "syn-21": 4,
    "syn-38": 4,
    "syn-43": 6,
    "syn-46": 4,
    "hld-01": None,
    "hld-02": None,
    "hld-03": None,
    "hld-04": None,
    "hld-05": None,
    "hld-06": None,
    "hld-07": None,
    "hld-08": None,
    "hld-09": 5,
    "hld-10": 4,
    "hld-11": 3,
    "hld-12": 5,
    "hld-13": 5,
    "hld-14": 5,
}
REFERENCE_TAIL_STARTS: Final[Mapping[str, int | None]] = {
    "syn-06": 4,
    "syn-20": 4,
    "syn-21": 4,
    "syn-38": 4,
    "syn-43": 6,
    "syn-46": 4,
    "hld-01": None,
    "hld-02": None,
    "hld-03": None,
    "hld-04": None,
    "hld-05": None,
    "hld-06": None,
    "hld-07": None,
    "hld-08": None,
    "hld-09": 5,
    "hld-10": 4,
    "hld-11": 4,
    "hld-12": 5,
    "hld-13": 5,
    "hld-14": 5,
}


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
    """The word error rate's parts: reference tokens, hypothesis tokens and
    the edit distance between them (substitution, insertion and deletion
    each cost one), counted over the token sequences the caller aligned —
    canonical spelling for the harness (the script against the transcript,
    metric amendment 2026-10-11), ``note.content_tokens`` normalisation
    alone for the kept-recordings replay (the kept transcript against the
    new one)."""

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
    reported (peer round 14, PR-MED-056). ``silently_omitted_v1``: the same
    as ``silently_omitted_somewhere`` under run 1's omission predicate and
    clinician-only scope — the report's comparison column only, never read
    by a rule (metric amendment 2026-10-09, note-routing-omissions plan
    D3). ``uncertainty_surfaced_acoustic``: ``uncertainty_surfaced`` under
    runs 1-4's predicate alone (a ``low_confidence_source`` warning on an
    aligned word, with no hedge credit) — the report's comparison column
    only, never read by a rule (metric amendment 2026-10-13, validation-pass
    plan D7); None as ``uncertainty_surfaced`` is."""

    fact_index: int
    kind: FactKind
    material: bool
    verdict: FactVerdict
    warned: bool
    uncertainty_surfaced: bool | None
    not_transcribed: bool
    ambiguous: bool
    silently_omitted_somewhere: bool = False
    silently_omitted_v1: bool = False
    uncertainty_surfaced_acoustic: bool | None = None

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
            "silently_omitted_v1",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be a flag")
        for name in ("uncertainty_surfaced", "uncertainty_surfaced_acoustic"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, bool):
                raise ValueError(f"{name} must be a flag or None")

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
    def silent_omission_v1(self) -> bool:
        """``silent_omission`` read with run 1's predicate and scope (the
        report's ``silent (run-1 predicate)`` column). Every run-1 warning
        is also a current one (the predicate is a pinned superset), so a
        current silent omission is always a run-1 one too — kept true by
        construction here as well."""
        return self.silent_omission or (self.material and self.silently_omitted_v1)

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
    (reported, never failing). ``spelling_normalised_words``: the
    transcript's content tokens that canonical spelling rewrote (metric
    amendment 2026-10-11 — "500mg" counts 1, "five hundred" 2, "500" 0;
    the script's rewrites are not counted), reported, never failing.
    ``hedge_marks_unhedged`` (metric amendment 2026-10-13, validation-pass
    plan D7): the note's ``hedged_source`` warnings whose marked words hold
    no spoken hedge (``note.words_hold_hedge``, re-derived) — expected 0 from
    the shipped checker; reported, never failing, and never credited."""

    words: WordErrors
    spelling_normalised_words: int
    transcript_lines: int
    config_lines: int
    unsupported_clinical_lines: int
    other_unsupported_words: int
    checker_tally: tuple[tuple[str, int], ...]
    checker_failures: tuple[str, ...]
    checker_failure_count: int
    expected_warnings_absent: tuple[str, ...]
    facts: tuple[FactOutcome, ...]
    hedge_marks_unhedged: int = 0

    def __post_init__(self) -> None:
        for name in (
            "spelling_normalised_words",
            "transcript_lines",
            "config_lines",
            "unsupported_clinical_lines",
            "other_unsupported_words",
            "checker_failure_count",
            "hedge_marks_unhedged",
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
    def silent_omissions_v1(self) -> int:
        """Run 1's silent-omission count (the comparison column; no rule
        reads it — metric amendment 2026-10-09)."""
        return sum(1 for fact in self.facts if fact.silent_omission_v1)

    @property
    def warned_omissions(self) -> int:
        return sum(1 for fact in self.facts if fact.verdict == "omitted" and fact.warned)

    @property
    def uncertainty_missed(self) -> int:
        return sum(1 for fact in self.facts if fact.uncertainty_surfaced is False)

    @property
    def uncertainty_surfaced_acoustic(self) -> int:
        """How many ``expect_uncertain`` facts runs 1-4's predicate alone
        surfaces (the report's "Surfaced (acoustic only)" column; no rule
        reads it — metric amendment 2026-10-13)."""
        return sum(1 for fact in self.facts if fact.uncertainty_surfaced_acoustic)

    @property
    def ambiguous_facts(self) -> int:
        return sum(1 for fact in self.facts if fact.ambiguous)


class _WordInfo(NamedTuple):
    """What one canonical transcript token means to the fact walk — flags
    only, over the transcript words it was made from (metric amendment
    2026-10-11: a joined "five hundred" is one token made from two words).
    ``covered_any``: one of those words is inside a note line (the walk's
    "some aligned word in a note line"); ``covered_all``: every one is (its
    "every aligned word in a note line") — so a note line holding one word
    of a joined number carries the token in part, never wholly and never
    not at all (PR-MED-020). ``warned``, ``warned_v1``,
    ``low_confidence`` and ``hedged`` hold when they hold for ANY of the
    words. ``warned_v1`` is ``warned`` under run 1's predicate and
    clinician-only scope (the report's comparison column, metric amendment
    2026-10-09). ``hedged`` (metric amendment 2026-10-13): the word sits
    under a ``hedged_source`` mark whose marked words hold a spoken hedge."""

    covered_any: bool
    covered_all: bool
    warned: bool
    warned_v1: bool
    low_confidence: bool
    hedged: bool


def _merged(words: Sequence[_WordInfo]) -> _WordInfo:
    """One canonical token's flags from the flags of the words it consumed."""
    return _WordInfo(
        covered_any=any(word.covered_any for word in words),
        covered_all=all(word.covered_all for word in words),
        warned=any(word.warned for word in words),
        warned_v1=any(word.warned_v1 for word in words),
        low_confidence=any(word.low_confidence for word in words),
        hedged=any(word.hedged for word in words),
    )


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
        forward = _forward_table(reference, hypothesis)
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


def _forward_table(reference: Sequence[str], hypothesis: Sequence[str]) -> list[array[int]]:
    """The alignment's forward cost table (Levenshtein, each edit costing
    one): ``table[i][j]`` is the edit distance between the first ``i``
    reference tokens and the first ``j`` hypothesis tokens. ONE definition,
    shared by ``_Alignment`` and ``align_transcripts``."""
    n, m = len(reference), len(hypothesis)
    forward = [array("i", [0]) * (m + 1) for _ in range(n + 1)]
    forward[0] = array("i", range(m + 1))
    for i in range(1, n + 1):
        row, previous, token = forward[i], forward[i - 1], reference[i - 1]
        row[0] = i
        for j in range(1, m + 1):
            diagonal = previous[j - 1] + (0 if token == hypothesis[j - 1] else 1)
            row[j] = min(diagonal, previous[j] + 1, row[j - 1] + 1)
    return forward


def _one_path(
    forward: Sequence[array[int]], reference: Sequence[str], hypothesis: Sequence[str]
) -> list[tuple[int, int]]:
    """The (reference, hypothesis) index pairs aligned word to word — a
    match or a substitution — on ONE optimal alignment, in order: the
    deterministic backtrace over the forward table that prefers the
    diagonal, then a deletion, then an insertion (development-recordings
    plan Task 4.1a: the replay tool's speaker-label agreement)."""
    pairs: list[tuple[int, int]] = []
    i, j = len(reference), len(hypothesis)
    while i > 0 or j > 0:
        here = forward[i][j]
        if i > 0 and j > 0:
            cost = 0 if reference[i - 1] == hypothesis[j - 1] else 1
            if forward[i - 1][j - 1] + cost == here:
                i, j = i - 1, j - 1
                pairs.append((i, j))
                continue
        if i > 0 and forward[i - 1][j] + 1 == here:
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    return pairs


@dataclass(frozen=True)
class TranscriptAlignment:
    """Two token sequences aligned once (development-recordings plan Task
    4.1a): the word error rate's parts and ONE optimal alignment's aligned
    index pairs. Indices and counts only — never a token."""

    words: WordErrors
    pairs: tuple[tuple[int, int], ...]


def align_transcripts(
    reference_words: Sequence[str], hypothesis_words: Sequence[str]
) -> TranscriptAlignment:
    """The alignment between two already-normalised token sequences
    (``note.content_tokens``), computed once over the harness's own forward
    table (``_forward_table``): its word error parts and one optimal path's
    aligned pairs. Only the forward table is built — the replay needs no
    "every optimal alignment" query, so ``_Alignment``'s backward table
    would double the memory and the time for nothing (review round 29
    LOW-004: a long consultation is a table of tens of millions of cells)."""
    forward = _forward_table(reference_words, hypothesis_words)
    total = forward[len(reference_words)][len(hypothesis_words)]
    return TranscriptAlignment(
        WordErrors(len(reference_words), len(hypothesis_words), total),
        tuple(_one_path(forward, reference_words, hypothesis_words)),
    )


def transcript_wer(reference_words: Sequence[str], hypothesis_words: Sequence[str]) -> WordErrors:
    """The word error rate's parts between two token sequences — public for
    the kept-recordings replay tool (development-recordings plan Task 4.1a),
    where the reference is the KEPT transcript and the hypothesis the new
    one, so the rate is DRIFT, not accuracy — and the harness's own
    ``word_errors``. ``align_transcripts(...).words`` without the path: the
    forward table alone (review round 30)."""
    forward = _forward_table(reference_words, hypothesis_words)
    total = forward[len(reference_words)][len(hypothesis_words)]
    return WordErrors(len(reference_words), len(hypothesis_words), total)


# The fact walk's state: (every token matched, every token deleted, some
# aligned word in a note line, every aligned word in a note line, warned,
# uncertainty surfaced by the recogniser, warned under run 1's predicate, some
# aligned word under a hedge mark — metric amendment 2026-10-13). Eight
# flags, so at most 256 states per cell.
_FactState = tuple[bool, bool, bool, bool, bool, bool, bool, bool]
_INITIAL_STATE: Final[_FactState] = (True, True, False, True, False, False, False, False)


def _after_word(state: _FactState, matched: bool, info: _WordInfo) -> _FactState:
    all_matched, _deleted, in_any, in_all, warned, surfaced, warned_v1, hedged = state
    return (
        all_matched and matched,
        False,
        in_any or info.covered_any,
        in_all and info.covered_all,
        warned or info.warned,
        surfaced or info.low_confidence,
        warned_v1 or info.warned_v1,
        hedged or info.hedged,
    )


def _after_deletion(state: _FactState) -> _FactState:
    _matched, deleted, in_any, in_all, warned, surfaced, warned_v1, hedged = state
    return (False, deleted, in_any, in_all, warned, surfaced, warned_v1, hedged)


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
    warned_v1: bool
    surfaced_acoustic: bool | None


def _judge(
    state: _FactState, kind: FactKind, expect_uncertain: bool, *, script_hedged: bool
) -> _Judged:
    """One alternative's outcome. Its uncertainty is surfaced by the
    recogniser (``low_confidence_source`` on an aligned word — runs 1-4's
    predicate, kept as ``surfaced_acoustic``) or, since the metric amendment
    of 2026-10-13 (validation-pass plan D7), by the hedge credit: the
    verdict is ``correct``, the fact's SCRIPT line holds a spoken hedge
    (``script_hedged``) AND an aligned word sits under a ``hedged_source``
    mark whose own words hold one (``_WordInfo.hedged``)."""
    all_matched, all_deleted, in_any, in_all, warned, surfaced, warned_v1, hedged = state
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
    if not expect_uncertain:
        return _Judged(verdict, warned, None, all_deleted, warned_v1, None)
    credited = hedged and script_hedged and verdict == "correct"
    return _Judged(verdict, warned, surfaced or credited, all_deleted, warned_v1, surfaced)


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


# ---------------------------------------------------------------------------
# Metric amendment 2026-10-11 — canonical spelling (note-routing-omissions
# plan D10, decision (a)). The harness's OWN comparison only: the provider's
# cue matching, the checker and the replay tool's alignment never use it.
# ---------------------------------------------------------------------------

# Spelled CARDINALS only. ``transcription._NUMBER_WORDS`` is a membership set
# that also holds ordinals, "half", "quarter" and "second", so it is not the
# source. "hundred" and "thousand" are not here: they are rewritten only
# after a spelled number ("five hundred" -> "500"), never on their own.
_UP_TO_TWENTY: Final = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen twenty"
).split()
_TENS: Final = ("twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
_CARDINALS: Final[Mapping[str, int]] = {
    **{word: value for value, word in enumerate(_UP_TO_TWENTY)},
    **{word: 20 + 10 * step for step, word in enumerate(_TENS)},
}
_MULTIPLIERS: Final[Mapping[str, int]] = {"hundred": 100, "thousand": 1000}


def _bounded_tokens(texts: Sequence[str]) -> list[tuple[str, bool, int]]:
    """``note.content_tokens`` over ``texts`` — one script line (a single
    text) or one transcript segment (one text per word) — as ``(token,
    boundary, text index)``. Inclusion and normalisation are
    ``content_tokens``' own, applied one whitespace word at a time, so the
    tokens are exactly the content-token sequence the loader and the fact
    lookup index (PR-MED-023); only the JOIN BOUNDARY flag is added
    (PR-MED-026). ``boundary`` is True when punctuation stands between the
    token and the next one kept — on the end of its own word, on a word
    dropped between them (a lone comma or dash, or a filler carrying a
    mark) or on the start of the next word, by the ONE punctuation rule
    (``strip_token_punctuation``) — and on the last token, so a join never
    crosses a script line or a transcript segment."""
    flagged: list[tuple[str, bool, int]] = []

    def close_previous() -> None:
        if flagged:
            token, _boundary, index = flagged[-1]
            flagged[-1] = (token, True, index)

    for index, text in enumerate(texts):
        for raw in text.split():
            core = strip_token_punctuation(raw)
            if not core or not raw.startswith(core):
                close_previous()
            kept = content_tokens(raw)
            trailing = not raw.endswith(core)
            for token in kept:
                flagged.append((token, trailing, index))
            if not kept and trailing:
                close_previous()
    close_previous()
    return flagged


class CanonicalTokens(NamedTuple):
    """A content-token sequence after canonical spelling (D10). ``tokens``:
    the canonical tokens. ``consumed``: per canonical token, the indices of
    the content tokens it was made from (a split repeats one index, a join
    holds two), so ``len(tokens) == len(consumed)``. ``content_map``: per
    content token, the first and last canonical index made from it (a join's
    two content tokens map to the same one). ``rewritten``: how many content
    tokens belong to a rewrite whose output differs from its input."""

    tokens: tuple[str, ...]
    consumed: tuple[tuple[int, ...], ...]
    content_map: tuple[tuple[int, int], ...]
    rewritten: int


def _rewrite(token: str, following: str | None) -> tuple[tuple[str, ...], int]:
    """The canonical tokens for ``token`` (and ``following``, the next
    content token when no join boundary separates them) and how many
    content tokens they consume."""
    glued = _NUMBER_WITH_SUFFIX_RE.match(token)
    if glued is not None and glued.group(2) in _STRENGTH_UNITS:
        # The RAW digits: "2.50mg" stays "2.50", never ``_dose_quantity``'s
        # ``format(float)``.
        return (glued.group(1), _STRENGTH_UNITS[glued.group(2)]), 1
    if token in _STRENGTH_UNITS:
        return (_STRENGTH_UNITS[token],), 1
    value = _CARDINALS.get(token)
    if value is not None:
        if following is not None:
            if following in _MULTIPLIERS:
                return (str(value * _MULTIPLIERS[following]),), 2
            if token in _TENS and 1 <= _CARDINALS.get(following, 0) <= 9:
                return (str(value + _CARDINALS[following]),), 2
        return (str(value),), 1
    tens, hyphen, unit_word = token.partition("-")
    if hyphen and tens in _TENS and 1 <= _CARDINALS.get(unit_word, 0) <= 9:
        return (str(_CARDINALS[tens] + _CARDINALS[unit_word]),), 1
    return (token,), 1


def canonical_tokens(tokens: Sequence[tuple[str, bool]]) -> CanonicalTokens:
    """Canonical spelling over a content-token sequence, each token with its
    join-boundary flag (metric amendment 2026-10-11, D10), left to right:

    - a glued dose SPLITS: "500mg" -> "500" "mg" (a number with a suffix in
      ``note_check._STRENGTH_UNITS``; the digits kept as written);
    - a UNIT word reads as its short form through that same table
      ("milligrams" -> "mg");
    - a spelled CARDINAL reads as digits ("two" -> "2", "ten" -> "10"), and
      two shapes join: a tens word with a unit word ("twenty one" and
      "twenty-one" -> "21") and a spelled number with "hundred" or
      "thousand" ("five hundred" -> "500"). A join never crosses a boundary
      (punctuation, a script line or a transcript segment) and never runs
      through "and".

    Left as they are (the named residue): "hundred" or "thousand" with no
    spelled number before them ("a hundred"), ordinals, fractions, "half",
    spelled decimals, years, "N hundred M" and "hundred and N" (only the
    "N hundred" part joins), "twenty five hundred" (only "twenty five"
    joins), and units outside the table ("units", "tablets")."""
    out: list[str] = []
    consumed: list[tuple[int, ...]] = []
    content_map: list[tuple[int, int]] = []
    rewritten = 0
    index = 0
    while index < len(tokens):
        token, boundary = tokens[index]
        following = None if boundary or index + 1 == len(tokens) else tokens[index + 1][0]
        group, width = _rewrite(token, following)
        span = tuple(range(index, index + width))
        if group != tuple(tokens[i][0] for i in span):
            rewritten += width
        first = len(out)
        for piece in group:
            out.append(piece)
            consumed.append(span)
        content_map.extend([(first, len(out) - 1)] * width)
        index += width
    return CanonicalTokens(tuple(out), tuple(consumed), tuple(content_map), rewritten)


class _Reference(NamedTuple):
    """The script side of the alignment: the canonical tokens in spoken
    order, each line's first CONTENT-token index (the index space a fact's
    ``_occurrences`` lookup uses, as the loader does) and the content ->
    canonical map that carries a fact's span across."""

    tokens: tuple[str, ...]
    line_offsets: tuple[int, ...]
    content_map: tuple[tuple[int, int], ...]


def _reference(script: EncounterScript) -> _Reference:
    """The reference after canonical spelling (metric amendment 2026-10-11),
    each line canonicalised on its own."""
    flagged: list[tuple[str, bool]] = []
    offsets: list[int] = []
    for line in script.lines:
        offsets.append(len(flagged))
        flagged.extend((token, boundary) for token, boundary, _ in _bounded_tokens([line.text]))
    canonical = canonical_tokens(flagged)
    return _Reference(canonical.tokens, tuple(offsets), canonical.content_map)


class _CanonicalHypothesis(NamedTuple):
    """The transcript side of the alignment: the canonical tokens in segment
    order, per token the (segment, word) of every transcript word it was
    made from (the coordinates note lines and warnings address), and how
    many content tokens canonical spelling rewrote."""

    tokens: tuple[str, ...]
    consumed: tuple[tuple[tuple[int, int], ...], ...]
    rewritten: int


def _canonical_hypothesis(document: TranscriptDocument) -> _CanonicalHypothesis:
    """The transcript after canonical spelling (metric amendment 2026-10-11),
    each segment canonicalised on its own. ``_hypothesis`` stays the
    content-token form: the kept-recordings replay aligns that one (C11)."""
    flagged: list[tuple[str, bool]] = []
    positions: list[tuple[int, int]] = []
    for segment_index, segment in enumerate(document.transcript_segments):
        texts = [word.word_text for word in segment.transcript_words]
        for token, boundary, word_index in _bounded_tokens(texts):
            flagged.append((token, boundary))
            positions.append((segment_index, word_index))
    canonical = canonical_tokens(flagged)
    return _CanonicalHypothesis(
        canonical.tokens,
        tuple(tuple(positions[i] for i in span) for span in canonical.consumed),
        canonical.rewritten,
    )


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
    encounter still reports it), over canonical spelling as
    ``encounter_metrics`` counts them."""
    # The forward table only: the backward table answers "every optimal
    # alignment" queries this count never asks (review round 30).
    return transcript_wer(_reference(script).tokens, _canonical_hypothesis(document).tokens)


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
      segment boundaries fall. Since the metric amendment of 2026-10-11 both
      sides are aligned after canonical spelling (``canonical_tokens``), so
      every count and verdict below is over canonical tokens: a canonical
      token made from two words ("five hundred") is in a note line wholly
      when both are, in part when one is; it is warned, or low-confidence,
      when either word is. A fact is found on its line's content tokens as
      the loader finds it, and its span is carried to canonical tokens,
      widened to a whole joined token it cuts.
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
      aligned words is outside every note line, flagged by the omission
      check's predicate for its speaker (``_omission_flag_token`` since the
      metric amendment of 2026-10-09), and its segment carries a
      ``high_risk_omission`` warning — a warning's interval proves nothing,
      and a warning elsewhere in the segment never counts. Run 1's predicate
      with its clinician-only scope is kept beside it for the report's
      ``silent (run-1 predicate)`` column, which no rule reads.
      ``uncertainty_surfaced`` (for ``expect_uncertain`` facts): a
      ``low_confidence_source`` warning sits on one of the fact's aligned
      words, or (the metric amendment of 2026-10-13, validation-pass plan
      D7) the fact is ``correct``, its script line holds a spoken hedge
      (``note.text_holds_hedge``) and one of its aligned words sits under a
      ``hedged_source`` warning whose marked words hold one too
      (``note.words_hold_hedge``, re-derived as ``warned`` re-derives its
      predicate). The first reading alone is kept as
      ``uncertainty_surfaced_acoustic`` for the report's "Surfaced (acoustic
      only)" column, which no rule reads; a ``hedged_source`` warning whose
      words hold no hedge credits nothing and is counted
      (``hedge_marks_unhedged``).
    - Ambiguity is conservative: across equal-cost alignments, and across
      repeated occurrences of the tokens inside the fact's line, the fact
      takes the worse outcome (``ambiguous`` says alternatives differed in
      a reported outcome — never in a comparison flag alone),
      and its uncertainty counts as surfaced only when every alternative
      surfaces it, and it counts as a silent omission when any alternative
      omits it unwarned (peer round 14, PR-MED-056).
    """
    reference = _reference(script)
    hypothesis = _canonical_hypothesis(document)
    alignment = _Alignment(reference.tokens, hypothesis.tokens)
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
    # Metric amendment 2026-10-13 (D7): a hedge mark credits only the words
    # under it, and only when those words hold a hedge (re-derived, never
    # trusted from the warning); any other mark is counted, never credited.
    hedged: set[tuple[int, int]] = set()
    hedge_marks_unhedged = 0
    for warning in note.note_warnings:
        coords = warning.source_coords
        if warning.note_warning_code != "hedged_source" or coords is None:
            continue
        marked = _words_for_coords(document, coords)
        if marked and words_hold_hedge(marked):
            hedged.update(
                (coords.segment_index, index)
                for index in range(coords.first_word_index, coords.last_word_index + 1)
            )
        else:
            hedge_marks_unhedged += 1

    def word_info(position: tuple[int, int]) -> _WordInfo:
        """One transcript word's flags, read from its RAW text."""
        segment_index, word_index = position
        word = segments[segment_index].transcript_words[word_index]
        word_text = word.word_text
        first_in_segment = word_index == 0
        clinician = segments[segment_index].speaker == note.clinician_speaker
        # The note's OWN warning on the segment is required either way, so a
        # provider is never credited for a flag it did not raise. A suspect
        # word is never flaggable — Check 4 excludes it (invented-text guard
        # D6), so both predicates mirror the checker.
        flaggable = (
            position not in covered and segment_index in omission_segments and not word.suspect
        )
        return _WordInfo(
            covered_any=position in covered,
            covered_all=position in covered,
            warned=flaggable
            and _omission_flag_token(
                word_text, first_in_segment=first_in_segment, clinician=clinician
            ),
            # Run 1's predicate AND its clinician-only scope (D3).
            warned_v1=flaggable
            and clinician
            and _is_high_risk_token(word_text, first_in_segment=first_in_segment),
            low_confidence=position in low_confidence,
            hedged=position in hedged,
        )

    # PR-MED-020: any/all over every word a canonical token consumed.
    infos = [
        _merged([word_info(position) for position in consumed])
        for consumed in hypothesis.consumed
    ]

    unsupported = alignment.possibly_unsupported()
    by_word: dict[tuple[int, int], set[int]] = {}
    for j, consumed in enumerate(hypothesis.consumed):
        for position in consumed:
            by_word.setdefault(position, set()).add(j)
    unsupported_lines = 0
    other_words: set[int] = set()
    for line in lines:
        flagged = {j for position in line for j in by_word.get(position, ()) if unsupported[j]}
        if any(is_structured_claim_word(hypothesis.tokens[j]) for j in flagged):
            unsupported_lines += 1
        other_words.update(
            j for j in flagged if not is_structured_claim_word(hypothesis.tokens[j])
        )

    facts: list[FactOutcome] = []
    for index, fact in enumerate(script.facts):
        # Found on the line's CONTENT tokens exactly as the loader finds it,
        # then carried to canonical rows (PR-MED-023) — a span that cuts a
        # join takes the whole joined token.
        line_tokens = content_tokens(script.lines[fact.line].text)
        # D7: the SCRIPT line's own hedge, one of the credit's three terms.
        script_hedged = text_holds_hedge(script.lines[fact.line].text)
        judged: set[_Judged] = set()
        for start in _occurrences(line_tokens, fact.tokens):
            first_content = reference.line_offsets[fact.line] + start
            first = reference.content_map[first_content][0]
            last = reference.content_map[first_content + len(fact.tokens) - 1][1]
            for state in _fact_end_states(alignment, first, last, infos):
                judged.add(
                    _judge(state, fact.kind, fact.expect_uncertain, script_hedged=script_hedged)
                )
        worst = max(judged, key=_severity)
        # Round 11 LOW-008: surfacing is judged on its own, conservatively —
        # the worst verdict's alternative may surface the uncertainty while
        # an equal-cost alternative does not; it is surfaced only if every
        # alternative surfaces it. The acoustic-only comparison likewise.
        surfaced = all(j.surfaced for j in judged) if fact.expect_uncertain else None
        surfaced_acoustic = (
            all(j.surfaced_acoustic for j in judged) if fact.expect_uncertain else None
        )
        # Ambiguity is judged on the reported metric only: alternatives that
        # differ in nothing but a comparison flag (run 1's omission predicate,
        # the acoustic-only surfacing) are not ambiguous.
        outcomes = {j._replace(warned_v1=False, surfaced_acoustic=None) for j in judged}
        facts.append(
            FactOutcome(
                fact_index=index,
                kind=fact.kind,
                material=fact.material,
                verdict=worst.verdict,
                warned=worst.warned,
                uncertainty_surfaced=surfaced,
                not_transcribed=worst.not_transcribed,
                ambiguous=len(outcomes) > 1,
                # Peer round 14 (PR-MED-056): the silent-omission tally is
                # conservative on its own, like surfacing above.
                silently_omitted_somewhere=any(
                    j.verdict == "omitted" and not j.warned for j in judged
                ),
                silently_omitted_v1=any(
                    j.verdict == "omitted" and not j.warned_v1 for j in judged
                ),
                uncertainty_surfaced_acoustic=surfaced_acoustic,
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
        words=WordErrors(len(reference.tokens), len(hypothesis.tokens), alignment.total),
        spelling_normalised_words=hypothesis.rewritten,
        transcript_lines=len(lines),
        config_lines=config_lines,
        unsupported_clinical_lines=unsupported_lines,
        other_unsupported_words=len(other_words),
        checker_tally=tuple(sorted(tally.items())),
        checker_failures=tuple(failing),
        checker_failure_count=sum(tally[code] for code in failing),
        expected_warnings_absent=tuple(sorted(expected - set(tally))),
        facts=tuple(facts),
        hedge_marks_unhedged=hedge_marks_unhedged,
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
    # Peer round 27 (PR-HIGH-068): "the rule file", never its name — the
    # round-22 rule that a name not an encounter id is never printed.
    try:
        with path.open("rb") as handle:
            blob = handle.read(MAX_RULE_BYTES + 1)
    except OSError as exc:
        raise RuleError(f"the rule file: unreadable ({type(exc).__name__})") from None
    if len(blob) > MAX_RULE_BYTES:
        raise RuleError(f"the rule file: larger than {MAX_RULE_BYTES} bytes")
    try:
        return PassRule.model_validate_json(blob)
    except ValidationError as exc:
        raise RuleError(f"the rule file: {_validation_error_text(exc)}") from None


# ---------------------------------------------------------------------------
# Task 2.4 — the runner.
# ---------------------------------------------------------------------------

EncounterStatus = Literal["measured", "role_unresolved", "error"]
_STATUSES: Final[tuple[str, ...]] = get_args(EncounterStatus)
# Two clusters holding the clinician's seconds within this are a tie: no
# cluster is chosen by its name (the speaker_eval float-noise tolerance).
ROLE_TIE_SECONDS: Final = 1e-9
# Metric amendment 2026-10-23 (validation-run6 plan D11): how the clinician
# is attributed. ``enrolment`` (the default) is the app's live condition —
# the enrolled pass's ``enrolled_speaker``, confirmed by the label track;
# ``clustering`` is runs 1-5's reading — the label track names the cluster.
Attribution = Literal["enrolment", "clustering"]
ATTRIBUTIONS: Final[tuple[str, ...]] = get_args(Attribution)
# The set folder's enrolment WAVs, one per clinician voice slot, written by
# the builder (``validation_set``) and read by ``main``.
ENROLMENT_DIRNAME: Final = "enrolment"


def enrolment_wav_name(slot: int) -> str:
    """The set's enrolment WAV for clinician voice ``slot``
    (``<set>/enrolment/slot-<n>.wav``)."""
    return f"slot-{slot}.wav"


class EnrolmentMissingError(RecordingRefusedError):
    """Under ``enrolment`` attribution the script names no enrolled clinician
    voice: a recorded script (no synthetic conditions) is measured with
    ``--attribution clustering``. Fixed text only."""


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
    # Invented-text guard D8: the transcript's segments holding a suspect
    # word (``suspect_segment_count``); None when no transcript was made. A
    # count only — no rule reads it.
    suspect_segments: int | None = None
    # Metric amendment 2026-10-23 (D11): the label track's clinician seconds
    # on segments not labelled as the confirmed clinician, and its other
    # speakers' seconds on segments labelled as it (``attribution_seconds``);
    # None when no clinician was confirmed. Recorded; no rule reads them.
    clinician_as_other_seconds: float | None = None
    other_as_clinician_seconds: float | None = None

    def __post_init__(self) -> None:
        if not _ENCOUNTER_ID_RE.fullmatch(self.encounter_id):
            raise ValueError("encounter_id must match the id pattern")
        _require_member(self.status, _STATUSES, "status")
        if self.error_type is not None and not _ERROR_TYPE_RE.fullmatch(self.error_type):
            raise ValueError("error_type must be an exception type name")
        _require_count(self.segment_count, "segment_count")
        if self.suspect_segments is not None:
            _require_count(self.suspect_segments, "suspect_segments")
        for name in ("clinician_as_other_seconds", "other_as_clinician_seconds"):
            seconds = getattr(self, name)
            if seconds is not None and (
                not isinstance(seconds, float) or not math.isfinite(seconds) or seconds < 0
            ):
                raise ValueError(f"{name} must be a non-negative number of seconds")
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


def overlap_by_label(segment: TranscriptSegment, track: LabelTrack) -> dict[str, float]:
    """``segment``'s ACTUAL overlap seconds with each label of ``track`` —
    every span's overlap summed per label, never the segment's whole
    duration under one winning label (D11)."""
    parts: dict[str, list[float]] = {}
    for span in track.spans:
        seconds = min(segment.end_seconds, span.end_seconds) - max(
            segment.start_seconds, span.start_seconds
        )
        if seconds > 0:
            parts.setdefault(span.label, []).append(seconds)
    return {label: math.fsum(values) for label, values in parts.items()}


def enrolled_clinician(document: TranscriptDocument, track: LabelTrack) -> str | None:
    """Metric amendment 2026-10-23 (D11): the enrolled pass's
    ``enrolled_speaker``, CONFIRMED by the label track — ``clinician_speaker``
    must name the same cluster, AND that cluster's actual overlap seconds
    (``overlap_by_label``) must give the clinician more than all other
    labels together, by more than ``ROLE_TIE_SECONDS`` (peer round 8
    PR-MED-027: ``clinician_speaker`` totals whole segments under their
    winning label, so a cluster of one 10 s segment at 5.1 / 4.9 seconds and
    a 9 s patient segment would confirm as 10 vs 9). Anything else — no
    ``enrolled_speaker``, a different cluster, a tie, an overlap majority
    that is not the clinician — is None, "role unresolved": never a
    guess."""
    enrolled = document.enrolled_speaker
    if enrolled is None or clinician_speaker(document, track) != enrolled:
        return None
    clinician: list[float] = []
    others: list[float] = []
    for segment in document.transcript_segments:
        if segment.speaker != enrolled:
            continue
        for label, seconds in overlap_by_label(segment, track).items():
            (clinician if label == CLINICIAN_LABEL else others).append(seconds)
    if math.fsum(clinician) - math.fsum(others) <= ROLE_TIE_SECONDS:
        return None
    return enrolled


def attribution_seconds(
    document: TranscriptDocument, track: LabelTrack, clinician: str
) -> tuple[float, float]:
    """D11's two recorded numbers for the confirmed ``clinician`` label:
    ``(clinician seconds on segments not labelled clinician, other
    speakers' seconds on segments labelled clinician)``, from the actual
    overlaps (``overlap_by_label``). Speech no segment covers counts in
    neither."""
    as_other: list[float] = []
    as_clinician: list[float] = []
    for segment in document.transcript_segments:
        overlaps = overlap_by_label(segment, track)
        if segment.speaker == clinician:
            as_clinician.extend(s for label, s in overlaps.items() if label != CLINICIAN_LABEL)
        else:
            as_other.append(overlaps.get(CLINICIAN_LABEL, 0.0))
    return math.fsum(as_other), math.fsum(as_clinician)


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
    the config's own cues), the optional prose stage and, since the metric
    amendment of 2026-10-23 (D11), the attribution policy with its enrolments
    — clinician voice slot -> the in-memory profile, never a store, never
    rendered (``repr=False``)."""

    provider: SpeechProvider
    frame_probability: FrameProbabilityFn
    config: NoteConfig
    template_profile_id: str | None = None
    note_provider_factory: Callable[[NoteConfig], NoteModelProvider] = (
        extractive_provider_from_config
    )
    prose_stage: ProseStage | None = None
    now: Callable[[], datetime] = _default_now
    attribution: Attribution = "enrolment"
    enrolments: Mapping[int, EnrolmentInputs] = field(default_factory=dict, repr=False)


def read_label_track(labels: Path) -> LabelTrack:
    """An encounter's ``<id>.txt`` label track, read whole up to
    ``MAX_LABEL_TRACK_BYTES`` (round 26) and parsed; the harness's one reader
    of it, shared with the transcription-guard measurement (invented-text-guard
    plan Task 1.5)."""
    with labels.open("rb") as handle:
        track_bytes = handle.read(MAX_LABEL_TRACK_BYTES + 1)
    if len(track_bytes) > MAX_LABEL_TRACK_BYTES:
        raise LabelTrackError(f"larger than {MAX_LABEL_TRACK_BYTES} bytes")  # round 26
    return parse_audacity_labels(track_bytes.decode("utf-8-sig"))


def suspect_segment_count(document: TranscriptDocument) -> int:
    """How many of ``document``'s segments hold a ``suspect`` word — the
    invented-text guard's ONE count (D8), shared with the kept-recordings
    replay. A number only; it reads no word text."""
    return sum(
        1
        for segment in document.transcript_segments
        if words_hold_suspect(segment.transcript_words)
    )


def evaluate_encounter(
    encounter_id: str, script: EncounterScript, wav: Path, labels: Path, inputs: HarnessInputs
) -> EncounterOutcome:
    """One encounter through the shipped pipeline (Task 2.4). Raises
    ``SpeakerEvalError`` when the temporary store cannot be shown gone
    (custody: the caller stops the run) and any input or pipeline error as
    itself; the label track, the script's enrolment and the WAV are
    validated BEFORE any store exists.

    Attribution (metric amendment 2026-10-23, D11): under ``enrolment`` the
    script's clinician voice slot picks its profile from
    ``inputs.enrolments`` (none: ``EnrolmentMissingError``), the store is
    transcribed twice — the enrolled pass replays the plain pass's words, so
    every word-level number is the same — and the ENROLLED document is
    judged, its clinician confirmed by ``enrolled_clinician``; under
    ``clustering`` it is runs 1-5's path exactly (``clinician_speaker`` on
    the plain document)."""
    track = read_label_track(labels)
    enrolment: EnrolmentInputs | None = None
    if inputs.attribution == "enrolment":
        conditions = script.conditions
        slot = None if conditions is None else conditions.voice_slots[CLINICIAN_LABEL]
        enrolment = None if slot is None else inputs.enrolments.get(slot)
        if enrolment is None:
            raise EnrolmentMissingError(
                "no enrolment for this script's clinician voice - a recorded script "
                "is measured with --attribution clustering"
            )
    pcm = read_wav_pcm(wav)
    plain, enrolled = transcribe_in_temporary_store(
        pcm, inputs.provider, inputs.frame_probability, enrolment=enrolment
    )
    del pcm
    if enrolment is None:
        document = plain
        clinician = clinician_speaker(document, track)
    else:
        # ``enrolled`` is set whenever an enrolment is given; a missing one
        # judges the plain document, whose absent ``enrolled_speaker`` is
        # "role unresolved".
        document = plain if enrolled is None else enrolled
        clinician = enrolled_clinician(document, track)
    segment_count = len(document.transcript_segments)
    suspect_segments = suspect_segment_count(document)
    if clinician is None:
        return EncounterOutcome(
            encounter_id,
            "role_unresolved",
            segment_count=segment_count,
            words=word_errors(document, script),
            suspect_segments=suspect_segments,
        )
    as_other, as_clinician = attribution_seconds(document, track, clinician)
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
    # One alignment per encounter (review round 25): the metrics carry the
    # word errors ``word_errors`` would compute from the same inputs.
    metrics = encounter_metrics(document, note, script)
    return EncounterOutcome(
        encounter_id,
        "measured",
        segment_count=segment_count,
        words=metrics.words,
        metrics=metrics,
        prose=prose,
        suspect_segments=suspect_segments,
        clinician_as_other_seconds=as_other,
        other_as_clinician_seconds=as_clinician,
    )


def _error_type(exc: BaseException) -> str:
    """``exc``'s type name as an outcome can hold it, else ``Exception``
    (review round 22): built inside an ``except``, an outcome refusing an
    over-long name would raise there, and the traceback would chain the
    original exception's message — which may quote note text."""
    name = type(exc).__name__
    return name if _ERROR_TYPE_RE.fullmatch(name) else "Exception"


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
    # Round 26: every error line is written AFTER its ``except`` block ends —
    # a failed write inside one (a closed output pipe) would chain the
    # pipeline's exception, whose message may quote note text.
    outcomes: list[EncounterOutcome] = []
    for files in encounters:
        progress(f"[run ] {files.encounter_id}")
        script_refusal: str | None = None
        try:
            script = load_script(files.script)
        except ScriptError as exc:
            script_refusal = str(exc)  # the loader's own text-free refusal
        if script_refusal is not None:
            progress(f"[error] {script_refusal}")
            outcomes.append(EncounterOutcome(files.encounter_id, "error", "ScriptError"))
            continue
        failure: str | None = None
        detail: str | None = None
        try:
            outcomes.append(
                evaluate_encounter(files.encounter_id, script, files.wav, files.labels, inputs)
            )
        except RecordingRefusedError as exc:
            # A label track or WAV refused before any store existed. A WAV
            # refusal's text is speaker_eval's own (formats and the remedy);
            # a label-track refusal can quote the labels typed in the file,
            # so only its type is printed (round 11 LOW-007).
            failure = _error_type(exc)
            detail = (
                "the label track was refused - check it against "
                "docs/testing/speaker-measurement.md"
                if isinstance(exc, LabelTrackError)
                else str(exc)
            )
        except SpeakerEvalError:
            raise  # custody: a temporary store not shown gone stops the run
        except Exception as exc:  # noqa: BLE001 - reported by TYPE only, run continues
            failure = _error_type(exc)
        if failure is not None:
            line = f"[error] {files.encounter_id}: {failure}"
            progress(line if detail is None else f"{line}: {detail}")
            outcomes.append(EncounterOutcome(files.encounter_id, "error", failure))
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
    attribution: Attribution = "enrolment"


def run_passed(rule: PassRule, outcomes: Sequence[EncounterOutcome], *, errors: int = 0) -> bool:
    """The run passes when at least one encounter ran, no set-level error
    occurred and every encounter passes ``rule``."""
    return bool(outcomes) and not errors and all(not rule_failures(rule, o) for o in outcomes)


def _rate(value: float) -> str:
    return f"{value:.3f}"


def _flag(value: bool | None) -> str:
    return "-" if value is None else ("yes" if value else "no")


def _seconds(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f}"


def _seconds_total(values: Sequence[float]) -> str:
    """A seconds column's TOTAL: ``-`` when no row has a value (peer round
    17 PR-LOW-013: an unmeasured column is never shown as zero)."""
    return _seconds(math.fsum(values) if values else None)


# The header's attribution sentence, per policy (metric amendment
# 2026-10-23, D11).
_ATTRIBUTION_TEXT: Final[dict[str, str]] = {
    "enrolment": (
        "the clinician is the enrolled speaker (an enrolment of each script's clinician "
        "voice), confirmed by the label track"
    ),
    "clustering": (
        "the clinician is the cluster the label track names, without an enrolment "
        "(--attribution clustering: runs 1-5's reading)"
    ),
}


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
        f"set-level errors: {errors}. Words compared after canonical spelling, metric "
        "amendment 2026-10-11: Ref words, WER and every fact verdict are over canonical "
        "tokens (read beside runs 1-2, not compared with them). Uncertainty is also "
        "surfaced by a hedge mark on a correct, hedged line, metric amendment 2026-10-13 "
        "(the recogniser's alone: Surfaced (acoustic only)). Attribution "
        f"`{info.attribution}`, metric amendment 2026-10-23: "
        f"{_ATTRIBUTION_TEXT[info.attribution]}; the two seconds columns show the "
        "attribution residue both ways (recorded, never failing).",
        "",
        "| Encounter | Status | Segments | Ref words | WER | Spelling-normalised words "
        "| Unsupported clinical lines "
        "| Other unsupported words | Transcript lines | Config lines | Facts | Correct "
        "| Wrong (material) | Omitted | Silent omissions | Silent (run-1 predicate) "
        "| Warned omissions | Uncertainty missed | Surfaced (acoustic only) "
        "| Hedge marks on unhedged segments | Ambiguous facts | Checker failures "
        "| Suspect segments | Clinician speech labelled other (s) "
        "| Other speech labelled clinician (s) | Prose p/f/e | Rule |",
        "|" + "---|" * 27,
    ]
    totals = Counter[str]()
    as_other_total: list[float] = []
    as_clinician_total: list[float] = []
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
            cells = ["-"] * 18
        else:
            facts = metrics.facts
            counts = {
                "spelling": metrics.spelling_normalised_words,
                "unsupported": metrics.unsupported_clinical_lines,
                "other": metrics.other_unsupported_words,
                "facts": len(facts),
                "correct": sum(1 for f in facts if f.verdict in ("correct", "correctly_absent")),
                "wrong": metrics.material_wrong,
                "omitted": sum(1 for f in facts if f.verdict == "omitted"),
                "silent": metrics.silent_omissions,
                "silent_v1": metrics.silent_omissions_v1,
                "warned": metrics.warned_omissions,
                "missed": metrics.uncertainty_missed,
                "acoustic": metrics.uncertainty_surfaced_acoustic,
                "unhedged": metrics.hedge_marks_unhedged,
                "ambiguous": metrics.ambiguous_facts,
                "checker": metrics.checker_failure_count,
            }
            totals.update(counts)
            prose = outcome.prose
            cells = [
                str(counts["spelling"]),
                str(counts["unsupported"]),
                str(counts["other"]),
                str(metrics.transcript_lines),
                str(metrics.config_lines),
                str(counts["facts"]),
                str(counts["correct"]),
                str(counts["wrong"]),
                str(counts["omitted"]),
                str(counts["silent"]),
                str(counts["silent_v1"]),
                str(counts["warned"]),
                str(counts["missed"]),
                # Metric amendment 2026-10-13 (D7): the comparison columns.
                str(counts["acoustic"]),
                str(counts["unhedged"]),
                str(counts["ambiguous"]),
                str(counts["checker"]),
                "-"
                if prose is None
                else "unavailable"
                if prose.unavailable
                else f"{prose.passed}/{prose.failed}/{prose.errored}",
            ]
        # Invented-text guard D8: the count sits before the prose cell and is
        # shown whenever a transcript was made (a role-unresolved encounter
        # too), so the total covers every transcribed encounter.
        suspect = outcome.suspect_segments
        if suspect is not None:
            totals["suspect"] += suspect
        cells.insert(17, "-" if suspect is None else str(suspect))
        # Metric amendment 2026-10-23 (D11): after the suspect count, before
        # the prose cell; "-" where no clinician was confirmed.
        as_other = outcome.clinician_as_other_seconds
        as_clinician = outcome.other_as_clinician_seconds
        if as_other is not None:
            as_other_total.append(as_other)
        if as_clinician is not None:
            as_clinician_total.append(as_clinician)
        cells[18:18] = [_seconds(as_other), _seconds(as_clinician)]
        status = outcome.status + (f" ({outcome.error_type})" if outcome.error_type else "")
        lines.append(
            f"| {outcome.encounter_id} | {status} | {outcome.segment_count} | {ref} | {wer} | "
            + " | ".join(cells)
            + f" | {'PASS' if not failures else 'FAIL: ' + ', '.join(failures)} |"
        )
    total_wer = _rate(totals["distance"] / totals["ref"]) if totals["ref"] else "-"
    lines.append(
        f"| TOTAL | {sum(1 for o in outcomes if o.status == 'measured')} measured | - "
        f"| {totals['ref']} | {total_wer} | {totals['spelling']} | {totals['unsupported']} "
        f"| {totals['other']} | - | - "
        f"| {totals['facts']} | {totals['correct']} | {totals['wrong']} | {totals['omitted']} "
        f"| {totals['silent']} | {totals['silent_v1']} | {totals['warned']} | {totals['missed']} "
        f"| {totals['acoustic']} | {totals['unhedged']} "
        f"| {totals['ambiguous']} | {totals['checker']} | {totals['suspect']} "
        f"| {_seconds_total(as_other_total)} | {_seconds_total(as_clinician_total)} "
        f"| - | {verdict} |"
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
    parser.add_argument(
        "--attribution",
        choices=ATTRIBUTIONS,
        default="enrolment",
        help=(
            "how the clinician is attributed: `enrolment` (default; the app's live condition, "
            "with the set's enrolment WAVs, confirmed by the label track) or `clustering` "
            "(runs 1-5's reading: the label track names the cluster)"
        ),
    )
    return parser


def needed_enrolment_slots(encounters: Sequence[EncounterFiles]) -> list[int]:
    """Every clinician voice slot the set's synthetic scripts use, read with
    ``load_script``; a script that does not load, or a recorded one, adds
    nothing (each is reported when its encounter runs)."""
    slots: set[int] = set()
    for files in encounters:
        try:
            script = load_script(files.script)
        except ScriptError:
            continue
        if script.conditions is not None:
            slots.add(script.conditions.voice_slots[CLINICIAN_LABEL])
    return sorted(slots)


def main(argv: list[str] | None = None, *, repo_root: Path = REPO_ROOT) -> int:
    """Exit status 0 only when the run passed; 2 for a refusal before any
    encounter runs; 1 otherwise. Refusals, in order: a packaged build
    (``install_layout.channel``, read at call time — the tests' seam), a
    missing set or config folder, the app's own config folder, an unusable
    rule or config, a config carrying the app's learned content, a template
    profile that cannot be bound, then the models (by name, before any is
    constructed; under ``enrolment`` attribution the speaker model too), an
    unreadable set folder, an enrolment WAV the set's scripts need missing
    from ``<set>/enrolment/`` (D11), models that cannot be loaded (by
    exception type — round 26), and an enrolment WAV that cannot be enrolled
    (by type, naming the slot's file)."""
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
    # Peer round 27 (PR-HIGH-066): every refusal below is printed AFTER its
    # ``except`` block ends, as in ``run_encounters`` — a failed write inside
    # one would chain the handled exception (a config error's text reproduces
    # the rejected input; a custody fault carries the pipeline's exception).
    rule_refusal: str | None = None
    try:
        rule = load_pass_rule(args.rule)
    except RuleError as exc:
        rule_refusal = str(exc)
    if rule_refusal is not None:
        print(f"[refused] {rule_refusal}")
        return 2
    config_failure: str | None = None
    try:
        config = load_note_config(config_dir)
    except NoteConfigError as exc:
        # The loader's detail reproduces the rejected file text (not
        # log-safe, note_config's own warning): the type only (round 11
        # LOW-001).
        config_failure = type(exc).__name__
    if config_failure is not None:
        print(
            f"[refused] --config {config_dir}: a config file is unreadable or malformed "
            f"({config_failure}) - check each JSON file against the shipped defaults"
        )
        return 2
    if _carries_learned_content(config_dir, config):
        print(
            f"[refused] --config {config_dir} carries the app's learned phrases or rules (a "
            "copy of the app's own config); use validation\\config or a folder you wrote"
        )
        return 2
    bind_failure: str | None = None
    try:
        # The profile ``compose_draft`` will bind, resolved now so a bad
        # ``--template-profile`` (or several profiles and none chosen) is a
        # refusal before any model is built, not an error on every
        # encounter after a full transcription (round 12 LOW-009).
        bind_template_profile(config, args.template_profile)
    except NoteConfigError as exc:
        bind_failure = type(exc).__name__
    if bind_failure is not None:
        print(
            f"[refused] --config {config_dir}: no template profile can be bound "
            f"({bind_failure}) - pass --template-profile with one of the config's "
            "profile ids"
        )
        return 2

    models_failure: str | None = None
    try:
        models = install_layout.models_root()
    except (OSError, RuntimeError) as exc:
        models_failure = type(exc).__name__
    if models_failure is not None:
        print(f"[refused] the models folder cannot be located ({models_failure})")
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
    attribution: Attribution = args.attribution
    if attribution == "enrolment" and not speaker_model_available():
        print(
            f"[refused] the speaker-embedding model is not installed in {models} (the "
            "harness attributes the clinician with an enrolment): "
            f"{install_layout.model_remedy('speaker-embedding')}"
        )
        return 2

    listing_failure: str | None = None
    try:
        encounters, incomplete = find_encounters(set_dir)
    except OSError as exc:
        listing_failure = type(exc).__name__
    if listing_failure is not None:
        print(f"[refused] {set_dir} cannot be listed ({listing_failure})")
        return 2
    errors = 0
    for name, problem in incomplete:
        errors += 1
        print(f"[error] {name}: {problem}")
    if not encounters:
        print(f"[error] no complete encounters in {set_dir}")
        return 1
    slots = needed_enrolment_slots(encounters) if attribution == "enrolment" else []
    enrolment_dir = set_dir / ENROLMENT_DIRNAME
    missing = [slot for slot in slots if not (enrolment_dir / enrolment_wav_name(slot)).is_file()]
    if missing:
        names = ", ".join(enrolment_wav_name(slot) for slot in missing)
        print(
            f"[refused] {enrolment_dir} lacks {names}, which the set's scripts need - "
            "rebuild the set (scripts/build-validation-set.py)"
        )
        return 2

    load_failure: str | None = None
    load_interrupted = False
    try:
        vad = SileroVad()
        provider = WhisperSpeechProvider(model_name=whisper)
        prose_stage = build_prose_stage("narrative") if args.prose else None
    except KeyboardInterrupt:
        load_interrupted = True
    except Exception as exc:  # noqa: BLE001 - reported by TYPE (round 26)
        # A model error's text names its path and the library's message:
        # refused by type, like every other refusal before a model runs.
        load_failure = _error_type(exc)
    if load_interrupted:
        print("[stopped] the run was interrupted while the models loaded; nothing was run")
        return 1
    if load_failure is not None:
        print(f"[refused] the models could not be loaded ({load_failure})")
        return 2
    # D11: one profile per needed slot, in memory only, under ONE embedder.
    enrolments: dict[int, EnrolmentInputs] = {}
    enrol_slot: int | None = None
    enrol_failure: str | None = None
    enrol_detail: str | None = None
    try:
        if slots:
            embedder = build_speaker_embedder()
            for enrol_slot in slots:
                enrolments[enrol_slot] = enrolment_inputs(
                    read_wav_pcm(enrolment_dir / enrolment_wav_name(enrol_slot)),
                    embedder,
                    vad.frame_probability,
                )
    except KeyboardInterrupt:
        load_interrupted = True
    except WavFormatError as exc:
        # ``read_wav_pcm``'s text names the path: the fixed help instead.
        enrol_failure = _error_type(exc)
        enrol_detail = f"it must be a {WAV_FORMAT_HELP} - rebuild the set"
    except EnrolmentError as exc:
        enrol_failure = _error_type(exc)
        enrol_detail = str(exc)  # enrolment's own fixed, numbers-only text
    except Exception as exc:  # noqa: BLE001 - reported by TYPE (round 26)
        enrol_failure = _error_type(exc)
    if load_interrupted:
        print("[stopped] the run was interrupted while the models loaded; nothing was run")
        return 1
    if enrol_failure is not None:
        line = (
            f"[refused] the speaker model could not be loaded ({enrol_failure})"
            if enrol_slot is None
            else f"[refused] {enrolment_wav_name(enrol_slot)} could not be enrolled "
            f"({enrol_failure})"
        )
        print(line if enrol_detail is None else f"{line}: {enrol_detail}")
        return 2
    inputs = HarnessInputs(
        provider=provider,
        frame_probability=vad.frame_probability,
        config=config,
        template_profile_id=args.template_profile,
        prose_stage=prose_stage,
        attribution=attribution,
        enrolments=enrolments,
    )
    custody: str | None = None
    interrupted = False
    try:
        outcomes = run_encounters(encounters, inputs)
    except SpeakerEvalError as exc:
        custody = str(exc)  # module-own text naming the path
    except KeyboardInterrupt:
        interrupted = True
    if custody is not None:
        print(f"[custody] the run stopped: {custody}")
        return 1
    if interrupted:
        # Review round 22: no traceback — it would chain whatever the
        # pipeline was raising, whose message may quote note text. Round 26:
        # the folder named is the one the stores are made in.
        print(
            "[stopped] the run was interrupted, so there is no report - look in "
            f"{tempfile.gettempdir()} for a {TEMP_DIR_PREFIX}* folder an interrupted "
            "teardown may have left (it may still hold its key), and delete it"
        )
        return 1
    info = RunInfo(
        whisper_model=whisper,
        whisper_fallback=fallback,
        vad_model="silero",
        prose="narrative" if args.prose else None,
        commit=read_commit(repo_root),
        models_manifest_sha256=models_manifest_sha256(repo_root),
        attribution=attribution,
    )
    print()
    print(render_report(outcomes, rule, info, errors=errors))
    return 0 if run_passed(rule, outcomes, errors=errors) else 1


__all__ = [
    "AXES",
    "ATTRIBUTIONS",
    "CONTRADICTION_CODES",
    "ENCOUNTER_ID_PATTERN",
    "ENROLMENT_DIRNAME",
    "FACT_KINDS",
    "FACT_VERDICTS",
    "REFERENCE_GREETING_LINES",
    "REFERENCE_HEDGES",
    "REFERENCE_MODEL_NAME",
    "REFERENCE_TAIL_STARTS",
    "REPO_ROOT",
    "ROLE_TIE_SECONDS",
    "SCRIPT_SCHEMA_VERSION",
    "UNNAMED_ENCOUNTER",
    "Attribution",
    "CanonicalTokens",
    "EncounterFiles",
    "EncounterMetrics",
    "EncounterOutcome",
    "EncounterScript",
    "EnrolmentMissingError",
    "ExpectedFact",
    "FactOutcome",
    "HarnessInputs",
    "PassRule",
    "ProseCounts",
    "RuleError",
    "RunInfo",
    "ScriptError",
    "ScriptLine",
    "SpokenTurn",
    "SyntheticConditions",
    "TranscriptAlignment",
    "ValidationHarnessError",
    "WordErrors",
    "align_transcripts",
    "attribution_seconds",
    "canonical_tokens",
    "clinician_speaker",
    "confirm_all",
    "document_from_turns",
    "enrolled_clinician",
    "enrolment_wav_name",
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
    "needed_enrolment_slots",
    "overlap_by_label",
    "read_commit",
    "read_label_track",
    "reference_document",
    "render_report",
    "rule_failures",
    "run_encounters",
    "run_passed",
    "suspect_segment_count",
    "transcript_wer",
    "word_errors",
]


if __name__ == "__main__":
    sys.exit(main())
