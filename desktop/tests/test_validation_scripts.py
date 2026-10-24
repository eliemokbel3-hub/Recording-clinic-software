"""Pilot plan Task 2.6: the repository's synthetic encounter scripts
(``validation/scripts/``) and the note config they are written against
(``validation/config/``).

Every script loads; each axis and each fact kind appears at least three
times; every script is synthetic and renders through the set builder with a
fake voice (no real speech engine); and the validation config's autofill
triggers are spoken only in the scripts that list the warnings they are
written to provoke. The scripts are invented consultations.

Validation-pass plan Task 0.9: the HELD-OUT scripts (``validation/heldout/``)
get their own lint — each loads, is synthetic with ``hld-`` ids and renders
with a fake voice — and so do their transcript fixtures
(``fixtures/heldout_transcripts.py``): one case per script, every expected
index in range and pointing at a segment with words. Since review round 8
the held-out scripts also get the fact-edge, routed-clause and trigger
checks, and each correction and hedge expectation its routing preconditions.
The axis, kind and voice-baseline lints above stay on ``validation/scripts``
only.

Validation-run6 plan Task 0.11: the held-out lints run per set over the
fixture's table (``HELD_OUT_SETS``: ``validation/heldout``,
``validation/heldout-2`` and, since Task 0.17, ``validation/heldout-3``); a
set with no scripts yet passes them vacuously, and a set whose cases are not
yet written gets the script lints only.

Task 0.17 (D16): every lint that reads a held-out script reports through
content-free problem codes, ``<id>:<code>[:<int>]`` — the id a script stem
or a set name, the code from ``PROBLEM_CODES``, the integer a fact index, a
line index or a count — recorded with ``record_property("problems", …)``
before it is asserted empty. ``scripts/lint-held-out-set.py`` runs this
module in a child process and prints only those codes; it is the boundary
that keeps a blind set's words off the console (C12), and the codes are what
goes back to the set's author.
"""

from __future__ import annotations

import functools
import hashlib
import json
import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any, Final

import pytest

from fixtures import heldout_transcripts
from fixtures.heldout_transcripts import (
    EDGE_CASE_PREFIX,
    HELD_OUT_CASES,
    HELD_OUT_SETS,
    NEXT_PATIENT_ROLE,
    SCRIPT_CASE_PREFIXES,
    HeldOutCase,
    HeldOutSet,
    held_out_set,
    script_path,
)
from scribe_desktop.note import (
    CANONICAL_SECTION_KEYS,
    CLINICIAN_OWNED_SECTIONS,
    DEFAULT_SECTION_CUES,
    NoteSectionKey,
    any_cue_matches,
    content_tokens,
    first_matching_section,
    is_interrogative,
    layered_section,
)
from scribe_desktop.note_config import load_note_config
from scribe_desktop.speaker_eval import CLINICIAN_LABEL, parse_audacity_labels
from scribe_desktop.transcription import TranscriptDocument
from scribe_desktop.validation import (
    AXES,
    FACT_KINDS,
    REFERENCE_MODEL_NAME,
    REFERENCE_TAIL_STARTS,
    EncounterScript,
    ScriptError,
    ScriptLine,
    _occurrences,
    document_from_turns,
    load_script,
    reference_document,
)
from scribe_desktop.validation_set import render_encounter, to_pcm16

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "validation" / "scripts"
CONFIG = REPO / "validation" / "config"
MIN_HELDOUT = 16
MIN_PER_AXIS = 3
MIN_PER_KIND = 3
_CLAUSE_END = re.compile(r"(?<=[.?!,;])\s+")
_NEXT_PATIENT_AXIS = "end_and_new_patient"
# The run-of-record set as a set-table row, so its scripts go through the
# same content-free helpers (its folder is ``validation/scripts``).
_RUN_OF_RECORD = HeldOutSet("scripts", "syn-", (), cases_written=False)

# ---------------------------------------------------------------------------
# Task 0.17 (D16): the closed problem grammar. ``scripts/lint_held_out_plugin.py``
# ships the same codes (``CODES``) and validates every recorded entry
# against the same pattern; ``test_lint_held_out_set.py`` pins the two equal.
# ---------------------------------------------------------------------------

PROBLEM_CODES: Final[frozenset[str]] = frozenset(
    {
        "load-error",
        "bad-id",
        "duplicate-id",
        "no-conditions",
        "slot-out-of-range",
        "no-material-fact",
        "fact-borders-edge",
        "uncertain-unrouted",
        "fact-unrouted",
        "trigger-spoken",
        "facts-out-of-bounds",
        "size-out-of-bounds",
        "next-patient-without-axis",
        "tail-disagrees",
        "missing-tail-row",
        "row-without-axis",
        "fact-in-tail-not-absent",
        "absent-fact-before-tail",
        "tail-out-of-range",
        "boundary-disagrees",
        "reference-mismatch",
        "render-mismatch",
    }
)
_STEM = r"(?:syn|hld|h2|h3)-\d{2}"
_SET_NAME = r"(?:heldout(?:-\d{1,2})?|scripts)"
STEM_RE: Final = re.compile(_STEM)
PROBLEM_RE: Final = re.compile(
    rf"(?:{_STEM}|{_SET_NAME}):(?:{'|'.join(sorted(map(re.escape, PROBLEM_CODES)))})"
    r"(?::\d{1,4})?"
)
_MAX_PROBLEM_INT = 9999
_LOAD_CODES: Final = frozenset({"load-error", "bad-id"})

RecordProperty = Callable[[str, object], None]


def _problem(stamp: str, code: str, n: int | None = None) -> str:
    """One problem entry; refuses anything outside the grammar, so a helper
    can never return a string the runner would not print."""
    assert code in PROBLEM_CODES, code
    entry = f"{stamp}:{code}" if n is None else f"{stamp}:{code}:{min(n, _MAX_PROBLEM_INT)}"
    assert PROBLEM_RE.fullmatch(entry), "a problem entry outside the grammar"
    return entry


def _code(entry: str) -> str:
    return entry.split(":")[1]


def _stamp(path: Path, held_out: HeldOutSet) -> str | None:
    """The file's stem when it is a well-formed id of the set's prefix, else
    None (the file then gets ``bad-id`` and no other check)."""
    stem = path.stem
    if STEM_RE.fullmatch(stem) and stem.startswith(held_out.prefix):
        return stem
    return None


def _path_id(path: Path) -> str:
    """A parametrize id that is never author-typed text."""
    return path.stem if STEM_RE.fullmatch(path.stem) else "unnamed"


def _scripts() -> list[EncounterScript]:
    return [load_script(path) for path in sorted(SCRIPTS.glob("*.json"))]


# Clinic-smoke plan Task 1.2: one fake voice per slot up to the highest any
# script uses, so a voice's real SAPI index (Task 0.3) never fails the lint.
FAKE_VOICES: tuple[str, ...] = tuple(
    f"Voice {index}"
    for index in range(
        1
        + max(
            slot
            for script in _scripts()
            if script.conditions is not None
            for slot in script.conditions.voice_slots.values()
        )
    )
)
# Task 0.3's baseline: the third installed voice (Hazel, GB) sits at slot 1
# and is the patient of exactly syn-41…50 (D4); syn-01…40 use slots 0 and 2.
THIRD_VOICE_SLOT = 1
THIRD_VOICE_SCRIPTS = frozenset(f"syn-{number}" for number in range(41, 51))
# The baseline pinned on its own (peer round 8 PR-LOW-011): FAKE_VOICES grows
# with the scripts, so it cannot catch a slot drifting past the three
# installed voices. A deliberate remap changes these in the same commit.
OLDER_SCRIPT_SLOTS = frozenset({0, 2})
THIRD_VOICE_SCRIPT_SLOTS = {"clinician": 0, "patient": THIRD_VOICE_SLOT}


def _contains(tokens: tuple[str, ...], needle: tuple[str, ...]) -> bool:
    return bool(_occurrences(tokens, needle))


@functools.cache
def _validation_cues() -> Mapping[NoteSectionKey, tuple[tuple[str, ...], ...]]:
    """The validation config's own cue layer — the table the held-out
    briefs give their authors."""
    return load_note_config(CONFIG).normalised_cues()


@functools.cache
def _trigger_phrases() -> tuple[tuple[str, ...], ...]:
    return tuple(
        content_tokens(rule.trigger_phrase) for rule in load_note_config(CONFIG).autofill_rules
    )


def _facts_bordering_their_edge_word(
    scripts: Iterable[EncounterScript],
) -> list[tuple[str, int]]:
    """(encounter, fact index) for each fact whose neighbouring reference
    token repeats its own first or last token (round 11 MED-001)."""
    offending = []
    for script in scripts:
        stream: list[str] = []
        starts: list[int] = []
        for line in script.lines:
            starts.append(len(stream))
            stream.extend(content_tokens(line.text))
        for index, fact in enumerate(script.facts):
            line_tokens = content_tokens(script.lines[fact.line].text)
            for start in _occurrences(line_tokens, fact.tokens):
                first = starts[fact.line] + start
                after = first + len(fact.tokens)
                if first > 0 and stream[first - 1] == fact.tokens[0]:
                    offending.append((script.encounter_id, index))
                if after < len(stream) and stream[after] == fact.tokens[-1]:
                    offending.append((script.encounter_id, index))
    return offending


def _clause_routes(line: ScriptLine, tokens: tuple[str, ...]) -> bool:
    """Whether a clause of the line holding ``tokens`` routes through the
    provider's own ``first_matching_section`` with the validation config's
    cues, its speaker's role and the question test (round 11 MED-003, round
    12 LOW-016). Clauses split at sentence ends and commas: a synthetic voice
    pauses at both, and the recogniser may split there."""
    return any(
        first_matching_section(
            _validation_cues(),
            content_tokens(clause),
            CANONICAL_SECTION_KEYS,
            speaker=line.role,
            clinician_speaker=CLINICIAN_LABEL,
            # The provider tests the whole utterance; the line may reach it
            # as one segment, so a clause counts as a question if either it
            # or its line is one (round 13 LOW-007) — routing holds under
            # both splits.
            question=is_interrogative(clause) or is_interrogative(line.text),
        )
        is not None
        for clause in _CLAUSE_END.split(line.text)
        if _contains(content_tokens(clause), tokens)
    )


def _uncertain_facts_in_unrouted_clauses(
    scripts: Iterable[EncounterScript],
) -> list[tuple[str, int]]:
    """(encounter, fact index) for each ``expect_uncertain`` fact with no
    clause holding it that routes."""
    return [
        (script.encounter_id, index)
        for script in scripts
        for index, fact in enumerate(script.facts)
        if fact.expect_uncertain and not _clause_routes(script.lines[fact.line], fact.tokens)
    ]


# Task 0.17 (D16): the fact kinds a ``routed_material`` set must route when
# a non-clinician speaks them — ``absent`` facts belong to the next patient.
_ROUTED_KINDS: Final = frozenset({"present", "negation", "laterality", "dose"})


def _material_facts_in_unrouted_clauses(script: EncounterScript) -> list[int]:
    """Fact indices of every material ``present`` / ``negation`` /
    ``laterality`` / ``dose`` fact on a non-clinician line with no routed
    clause holding it."""
    return [
        index
        for index, fact in enumerate(script.facts)
        if fact.material
        and fact.kind in _ROUTED_KINDS
        and script.lines[fact.line].role != CLINICIAN_LABEL
        and not _clause_routes(script.lines[fact.line], fact.tokens)
    ]


def _role_tail(script: EncounterScript) -> int | None:
    """The index of the script's first ``next_patient`` line, or None (D16:
    a ``tails_by_role`` set's reference tail start)."""
    for index, line in enumerate(script.lines):
        if line.role == NEXT_PATIENT_ROLE:
            return index
    return None


def _checked_problems(stamp: str, script: EncounterScript, held_out: HeldOutSet) -> list[str]:
    """Every per-script check after a successful load, as problem codes."""
    problems: list[str] = []
    conditions = script.conditions
    if conditions is None:
        problems.append(_problem(stamp, "no-conditions"))
    elif any(slot >= len(FAKE_VOICES) for slot in conditions.voice_slots.values()):
        problems.append(_problem(stamp, "slot-out-of-range"))
    if not any(fact.material for fact in script.facts):
        problems.append(_problem(stamp, "no-material-fact"))
    for _, index in _facts_bordering_their_edge_word([script]):
        problems.append(_problem(stamp, "fact-borders-edge", index))
    for _, index in _uncertain_facts_in_unrouted_clauses([script]):
        problems.append(_problem(stamp, "uncertain-unrouted", index))
    if held_out is _RUN_OF_RECORD:
        return problems
    if held_out.routed_material:
        for index in _material_facts_in_unrouted_clauses(script):
            problems.append(_problem(stamp, "fact-unrouted", index))
    for line_index, line in enumerate(script.lines):
        tokens = content_tokens(line.text)
        if any(_contains(tokens, trigger) for trigger in _trigger_phrases()):
            # No held-out scenario is about autofill, so a trigger would only
            # add a warning its script does not list.
            problems.append(_problem(stamp, "trigger-spoken", line_index))
    bounds = held_out.facts_per_script
    if bounds is not None and not bounds[0] <= len(script.facts) <= bounds[1]:
        problems.append(_problem(stamp, "facts-out-of-bounds", len(script.facts)))
    if _role_tail(script) is not None and _NEXT_PATIENT_AXIS not in script.axes:
        problems.append(_problem(stamp, "next-patient-without-axis"))
    return problems


def _script_problems(path: Path, held_out: HeldOutSet, index: int) -> list[str]:
    """Task 0.17 (D16): one script's problems as content-free codes. A file
    whose stem is not a well-formed id of the set gets only
    ``<set>:bad-id:<file index>``; a load failure only ``<id>:load-error``
    (``load_script``'s own message is sanitised, but no message is needed)."""
    stamp = _stamp(path, held_out)
    if stamp is None:
        return [_problem(held_out.name, "bad-id", index)]
    try:
        script = load_script(path)
    except ScriptError:
        return [_problem(stamp, "load-error")]
    return _checked_problems(stamp, script, held_out)


def _set_problems(held_out: HeldOutSet, paths: list[Path] | None = None) -> list[str]:
    """Set-level problems: an id the run-of-record set also uses, and a
    populated set outside its size bounds (``script_count`` when given,
    otherwise ``MIN_HELDOUT`` once a set has scripts or its cases are
    written). ``paths`` defaults to the set's own scripts."""
    if paths is None:
        paths = held_out.script_paths()
    problems: list[str] = []
    if held_out is not _RUN_OF_RECORD:
        run_of_record = {path.stem for path in SCRIPTS.glob("*.json")}
        for path in paths:
            stamp = _stamp(path, held_out)
            if stamp is not None and stamp in run_of_record:
                problems.append(_problem(stamp, "duplicate-id"))
        minimum_only = held_out.script_count is None
        if minimum_only and (held_out.cases_written or paths) and len(paths) < MIN_HELDOUT:
            problems.append(_problem(held_out.name, "size-out-of-bounds", len(paths)))
    bounds = held_out.script_count
    if paths and bounds is not None and not bounds[0] <= len(paths) <= bounds[1]:
        problems.append(_problem(held_out.name, "size-out-of-bounds", len(paths)))
    return problems


@functools.cache
def _all_script_problems(name: str) -> tuple[str, ...]:
    held_out = _RUN_OF_RECORD if name == _RUN_OF_RECORD.name else held_out_set(name)
    return tuple(
        problem
        for index, path in enumerate(held_out.script_paths())
        for problem in _script_problems(path, held_out, index)
    )


def _codes(held_out: HeldOutSet, wanted: Iterable[str]) -> list[str]:
    """The set's script problems with one of the wanted codes, plus every
    load failure (a script that does not load cannot pass any lint)."""
    keep = _LOAD_CODES | frozenset(wanted)
    return [entry for entry in _all_script_problems(held_out.name) if _code(entry) in keep]


def _loaded(held_out: HeldOutSet) -> list[EncounterScript]:
    """The set's scripts that have a well-formed id and load; the others
    are reported by the load lint."""
    scripts = []
    for path in held_out.script_paths():
        if _stamp(path, held_out) is None:
            continue
        try:
            scripts.append(load_script(path))
        except ScriptError:
            continue
    return scripts


def _reference_mismatches(
    stamp: str, script: EncounterScript, document: TranscriptDocument
) -> list[str]:
    """Where the document is not the script's own lines: one
    ``reference-mismatch:<line>`` per line whose speaker or words differ or
    hold an uncertain word, and a bare ``reference-mismatch`` for a segment
    count or model name that differs."""
    segments = document.transcript_segments
    problems: list[str] = []
    if len(segments) != len(script.lines) or document.model_name != REFERENCE_MODEL_NAME:
        problems.append(_problem(stamp, "reference-mismatch"))
    for index, (line, segment) in enumerate(zip(script.lines, segments, strict=False)):
        words = [word.word_text for word in segment.transcript_words]
        if (
            segment.speaker != line.role
            or words != line.text.split()
            or any(word.uncertain for word in segment.transcript_words)
        ):
            problems.append(_problem(stamp, "reference-mismatch", index))
    return problems


def _short_turn(text: str, voice: int, rate: int) -> bytes:
    """A fake voice: 20 ms of a square wave per word (fast to mix)."""
    samples = 320 * len(text.split())
    level = 1000 * (voice + 1)
    return to_pcm16([level if (index // 20) % 2 else -level for index in range(samples)])


def _render_problems(stamp: str, script: EncounterScript) -> list[str]:
    pcm, labels, placement = render_encounter(script, FAKE_VOICES, _short_turn)
    track = parse_audacity_labels(labels)
    rendered = [span.label for span in track.spans] == [line.role for line in script.lines]
    if len(pcm) == placement.total * 2 and rendered:
        return []
    return [_problem(stamp, "render-mismatch")]


def _record(record_property: RecordProperty, problems: list[str]) -> list[str]:
    record_property("problems", problems)
    return problems


class TestScripts:
    def test_every_script_loads(self) -> None:
        scripts = _scripts()
        assert len(scripts) >= 50
        assert len({script.encounter_id for script in scripts}) == len(scripts)

    def test_every_slot_is_in_range_and_the_third_voice_is_the_new_scripts_patient(
        self, record_property: RecordProperty
    ) -> None:
        problems = _record(
            record_property, _codes(_RUN_OF_RECORD, {"no-conditions", "slot-out-of-range"})
        )
        assert problems == []
        used = {
            script.encounter_id: script.conditions.voice_slots
            for script in _scripts()
            if script.conditions is not None
        }
        third = {
            encounter_id: [role for role, slot in slots.items() if slot == THIRD_VOICE_SLOT]
            for encounter_id, slots in used.items()
            if THIRD_VOICE_SLOT in slots.values()
        }
        assert third == {encounter_id: ["patient"] for encounter_id in THIRD_VOICE_SCRIPTS}

    def test_every_script_uses_the_current_voice_baseline(
        self, record_property: RecordProperty
    ) -> None:
        problems = _record(record_property, _codes(_RUN_OF_RECORD, {"no-conditions"}))
        assert problems == []
        for script in _scripts():
            if script.conditions is None:
                continue
            slots = script.conditions.voice_slots
            if script.encounter_id in THIRD_VOICE_SCRIPTS:
                assert slots == THIRD_VOICE_SCRIPT_SLOTS, script.encounter_id
            else:
                assert set(slots.values()) == OLDER_SCRIPT_SLOTS, script.encounter_id

    def test_each_axis_appears_at_least_three_times(self) -> None:
        counts = Counter(axis for script in _scripts() for axis in script.axes)
        assert {axis: counts[axis] for axis in AXES if counts[axis] < MIN_PER_AXIS} == {}

    def test_each_fact_kind_appears_at_least_three_times(self) -> None:
        counts = Counter(fact.kind for script in _scripts() for fact in script.facts)
        assert {kind: counts[kind] for kind in FACT_KINDS if counts[kind] < MIN_PER_KIND} == {}

    def test_every_appointment_type_is_used(self) -> None:
        used = {script.appointment_type for script in _scripts()}
        assert used == {"initial", "follow_up", "acute", "chronic", "post_operative", "discharge"}

    def test_every_script_is_synthetic_with_material_facts(
        self, record_property: RecordProperty
    ) -> None:
        problems = _record(
            record_property, _codes(_RUN_OF_RECORD, {"no-conditions", "no-material-fact"})
        )
        assert problems == []

    def test_some_facts_expect_their_uncertainty_surfaced(self) -> None:
        marked = [fact for script in _scripts() for fact in script.facts if fact.expect_uncertain]
        assert len(marked) >= 3

    def test_no_fact_borders_a_repeat_of_its_own_edge_word(self) -> None:
        """Round 11 MED-001: "no, no numbness" against a transcript that
        drops one "no" has two equal-cost alignments, and the worse one
        deletes the fact's own word — a false ``wrong`` on a faithful note
        (and the mirror case reads as an inserted negation). The reference
        token just before a fact must differ from its first token, and the
        one just after from its last, across line boundaries too."""
        assert _facts_bordering_their_edge_word(_scripts()) == []

    def test_every_uncertain_fact_sits_in_a_routed_clause(self) -> None:
        """Round 11 MED-003: Check 1's ``low_confidence_source`` reaches
        only words already in the note, and the extractive provider quotes
        an utterance only when it routes to a section — so a fact marked
        ``expect_uncertain`` in an unrouted utterance could never be
        surfaced. The CLAUSE holding it (split at sentence ends and commas:
        a synthetic voice pauses at both, and the recogniser may split
        there) must route through the provider's own ``first_matching_section``
        with the validation config's cues, its speaker's role and the
        question test — so a patient clause whose only cue is in a
        clinician-owned section does not count (round 12 LOW-016)."""
        assert _uncertain_facts_in_unrouted_clauses(_scripts()) == []

    def test_consent_is_spoken_and_routed_in_at_least_three_scripts(self) -> None:
        """Peer round 14 (PR-MED-058): PLAN.md's validation set covers
        consent, so at least three scripts hold a material fact in a clause
        the provider routes to the consent section — the same clause split,
        speaker and question test as the routed-clause check above."""
        cues = _validation_cues()
        covered: set[str] = set()
        for script in _scripts():
            for fact in script.facts:
                if not fact.material:
                    continue
                line = script.lines[fact.line]
                for clause in _CLAUSE_END.split(line.text):
                    if not _contains(content_tokens(clause), fact.tokens):
                        continue
                    key = first_matching_section(
                        cues,
                        content_tokens(clause),
                        CANONICAL_SECTION_KEYS,
                        speaker=line.role,
                        clinician_speaker=CLINICIAN_LABEL,
                        question=is_interrogative(clause) or is_interrogative(line.text),
                    )
                    if key == "consent":
                        covered.add(script.encounter_id)
        assert len(covered) >= MIN_PER_AXIS, sorted(covered)


class TestValidationConfig:
    def test_the_config_loads(self) -> None:
        config = load_note_config(CONFIG)
        assert len(config.autofill_rules) == 3

    def test_triggers_are_spoken_only_where_their_warnings_are_expected(self) -> None:
        triggers = _trigger_phrases()
        for script in _scripts():
            spoken = [
                trigger
                for trigger in triggers
                for line in script.lines
                if _contains(content_tokens(line.text), trigger)
            ]
            clinician_spoken = [
                trigger
                for trigger in triggers
                for line in script.lines
                if line.role == CLINICIAN_LABEL and _contains(content_tokens(line.text), trigger)
            ]
            assert spoken == clinician_spoken, script.encounter_id
            assert bool(spoken) == bool(script.expected_warnings), script.encounter_id


class TestRenderable:
    @pytest.mark.parametrize("path", sorted(SCRIPTS.glob("*.json")), ids=_path_id)
    def test_every_script_renders_with_fake_voices(self, path: Path) -> None:
        script = load_script(path)
        pcm, labels, placement = render_encounter(script, FAKE_VOICES, _short_turn)
        assert len(pcm) == placement.total * 2
        track = parse_audacity_labels(labels)
        assert [span.label for span in track.spans] == [line.role for line in script.lines]


def _heldout_paths() -> list[Path]:
    """Every held-out set's scripts (Task 0.11)."""
    return [path for held_out in HELD_OUT_SETS for path in held_out.script_paths()]


def _owner(path: Path) -> HeldOutSet:
    """The held-out set whose folder holds the path."""
    (held_out,) = (s for s in HELD_OUT_SETS if s.folder == path.parent)
    return held_out


def _set_name(held_out: HeldOutSet) -> str:
    return held_out.name


# Review round 8 LOW-005 (routed to the held-out author, not edited here —
# C3): an uncertain fact whose clause has no cue of its own, so a recogniser
# split at the comma leaves it unquoted. Pinned exactly as problem entries,
# so a revision of the script fails this lint until the entry is removed.
# Empty since the author's revision (stage-2 leg vy3): ``hld-21`` line 5's
# fact now sits in its routed clause.
_HELD_OUT_UNROUTED_PENDING: list[str] = []


class TestHeldOutScripts:
    """Validation-pass plan Task 0.9: the held-out set is never tuned to, so
    its lint checks only that it is usable — not its axis or kind counts,
    and the same alignment, routing and trigger checks as the run-of-record
    set (review round 8 LOW-004). Since validation-run6 Task 0.11 each lint
    runs per held-out set; since Task 0.17 each reports problem codes only."""

    def test_the_sets_have_distinct_folders_and_prefixes(self) -> None:
        names = [held_out.name for held_out in HELD_OUT_SETS]
        assert names == ["heldout", "heldout-2", "heldout-3"]
        assert len(set(SCRIPT_CASE_PREFIXES)) == len(SCRIPT_CASE_PREFIXES)
        for prefix in (*SCRIPT_CASE_PREFIXES, EDGE_CASE_PREFIX):
            others = [p for p in (*SCRIPT_CASE_PREFIXES, EDGE_CASE_PREFIX) if p != prefix]
            assert not any(other.startswith(prefix) for other in others), prefix
        # Every set's ids and its name fit the problem grammar.
        for held_out in HELD_OUT_SETS:
            assert STEM_RE.fullmatch(f"{held_out.prefix}01"), held_out.name
            assert PROBLEM_RE.fullmatch(f"{held_out.name}:bad-id:0"), held_out.name

    @pytest.mark.parametrize("held_out", HELD_OUT_SETS, ids=_set_name)
    def test_no_held_out_fact_borders_a_repeat_of_its_own_edge_word(
        self, held_out: HeldOutSet, record_property: RecordProperty
    ) -> None:
        problems = _record(record_property, _codes(held_out, {"fact-borders-edge"}))
        assert problems == []

    @pytest.mark.parametrize("held_out", HELD_OUT_SETS, ids=_set_name)
    def test_every_held_out_uncertain_fact_sits_in_a_routed_clause(
        self, held_out: HeldOutSet, record_property: RecordProperty
    ) -> None:
        problems = _record(record_property, _codes(held_out, {"uncertain-unrouted"}))
        pending = [
            entry for entry in _HELD_OUT_UNROUTED_PENDING if entry.startswith(held_out.prefix)
        ]
        assert problems == pending

    @pytest.mark.parametrize("held_out", HELD_OUT_SETS, ids=_set_name)
    def test_every_material_patient_fact_sits_in_a_routed_clause(
        self, held_out: HeldOutSet, record_property: RecordProperty
    ) -> None:
        """Task 0.17 (D16): in a ``routed_material`` set every material
        ``present`` / ``negation`` / ``laterality`` / ``dose`` fact a
        non-clinician speaks sits in a clause that routes — the brief's
        "say it with one of the cue phrases of a section open to that
        speaker". Uncued CLINICIAN lines are D1's test and stay."""
        problems = _record(record_property, _codes(held_out, {"fact-unrouted"}))
        assert problems == []

    @pytest.mark.parametrize("held_out", HELD_OUT_SETS, ids=_set_name)
    def test_no_held_out_script_speaks_an_autofill_trigger(
        self, held_out: HeldOutSet, record_property: RecordProperty
    ) -> None:
        problems = _record(record_property, _codes(held_out, {"trigger-spoken"}))
        assert problems == []

    @pytest.mark.parametrize("held_out", HELD_OUT_SETS, ids=_set_name)
    def test_every_held_out_script_loads_with_a_held_out_id(
        self, held_out: HeldOutSet, record_property: RecordProperty
    ) -> None:
        """Each file's stem is a well-formed id of the set's prefix and its
        ``encounter_id`` (the loader refuses a different one), no id is the
        run-of-record set's, and the script loads."""
        problems = _codes(held_out, set()) + [
            entry for entry in _set_problems(held_out) if _code(entry) == "duplicate-id"
        ]
        assert _record(record_property, problems) == []

    @pytest.mark.parametrize("held_out", HELD_OUT_SETS, ids=_set_name)
    def test_every_held_out_set_is_within_its_size_bounds(
        self, held_out: HeldOutSet, record_property: RecordProperty
    ) -> None:
        """At least ``MIN_HELDOUT`` scripts once a set has any (or its cases
        are written — Task 0.10 authors a set before its cases); Task 0.17
        (D16): ``heldout-3``'s 20–25 scripts and 3–6 facts per script, read
        from the scripts' metadata only. The absent and empty states pass."""
        problems = _codes(held_out, {"facts-out-of-bounds"}) + [
            entry for entry in _set_problems(held_out) if _code(entry) == "size-out-of-bounds"
        ]
        assert _record(record_property, problems) == []

    def test_the_first_held_out_set_is_present(self) -> None:
        """A missing ``validation/heldout`` folder would pass the per-set
        lints vacuously; its cases are written, so its scripts must exist."""
        assert len(held_out_set("heldout").script_paths()) == 22

    @pytest.mark.parametrize("held_out", HELD_OUT_SETS, ids=_set_name)
    def test_every_held_out_script_is_synthetic_with_material_facts(
        self, held_out: HeldOutSet, record_property: RecordProperty
    ) -> None:
        problems = _codes(held_out, {"no-conditions", "slot-out-of-range", "no-material-fact"})
        assert _record(record_property, problems) == []

    @pytest.mark.parametrize("held_out", HELD_OUT_SETS, ids=_set_name)
    def test_a_next_patient_line_needs_the_next_patient_axis(
        self, held_out: HeldOutSet, record_property: RecordProperty
    ) -> None:
        """Task 0.17 (D16), the role lint's first rule: a script with a
        ``next_patient`` line carries the axis ``end_and_new_patient``
        (every held-out set; the converse — an axis script with no such
        line — is a boundary negative, not a failure)."""
        problems = _codes(held_out, {"next-patient-without-axis"})
        assert _record(record_property, problems) == []

    @pytest.mark.parametrize("path", _heldout_paths(), ids=_path_id)
    def test_every_held_out_script_renders_with_fake_voices(
        self, path: Path, record_property: RecordProperty
    ) -> None:
        held_out = _owner(path)
        index = held_out.script_paths().index(path)
        problems = [
            entry
            for entry in _script_problems(path, held_out, index)
            if _code(entry) in _LOAD_CODES
        ]
        stamp = _stamp(path, held_out)
        if stamp is not None and not problems:
            problems = _render_problems(stamp, load_script(path))
        assert _record(record_property, problems) == []


def _case_id(case: HeldOutCase) -> str:
    return case.case_id


class TestHeldOutTranscripts:
    """The held-out transcript fixtures: one case per held-out script (its
    turns are the script's lines) plus ``edge-`` cases, and every expected
    index well-formed."""

    def test_the_cases_are_unique_and_every_one_is_scripted_or_an_edge_case(self) -> None:
        ids = [case.case_id for case in HELD_OUT_CASES]
        assert len(set(ids)) == len(ids)
        assert [i for i in ids if not i.startswith((*SCRIPT_CASE_PREFIXES, EDGE_CASE_PREFIX))] == []
        for case in HELD_OUT_CASES:
            # A scripted case reads its script's lines; an edge case has its own.
            assert bool(case.explicit_turns) == case.case_id.startswith(EDGE_CASE_PREFIX)

    @pytest.mark.parametrize("held_out", HELD_OUT_SETS, ids=_set_name)
    def test_one_case_per_held_out_script_of_each_set(self, held_out: HeldOutSet) -> None:
        """Task 0.11: a set's scripted cases are exactly its scripts, under its
        own prefix; a set whose cases are not yet written holds no case."""
        if not held_out.cases_written:
            assert held_out.all_cases() == ()
            return
        scripted = [case.case_id for case in held_out.cases]
        assert set(scripted) == {path.stem for path in held_out.script_paths()}
        assert all(case_id.startswith(held_out.prefix) for case_id in scripted)
        for case in held_out.edge_cases:
            assert case.case_id.startswith(EDGE_CASE_PREFIX), case.case_id

    def test_a_misfiled_divergence_table_is_named(self) -> None:
        """Task 0.11: the per-set divergence tables' check, both ways — a
        well-formed table passes; a missing set, an extra set and a case
        filed under the wrong set are each named. Task 0.17: the tables are
        derived from ``HELD_OUT_SETS``, so a new set row needs no edit here."""
        names = [held_out.name for held_out in HELD_OUT_SETS]
        first = HELD_OUT_CASES[0].case_id
        (owner,) = (
            s.name for s in HELD_OUT_SETS if first in {case.case_id for case in s.all_cases()}
        )
        good: dict[str, dict[str, object]] = {
            name: ({first: None} if name == owner else {}) for name in names
        }
        assert heldout_transcripts.misfiled(good) == []
        for name in names:
            missing = {key: value for key, value in good.items() if key != name}
            assert heldout_transcripts.misfiled(missing) == [f"set {name}"]
        extra: dict[str, dict[str, object]] = {**good, "heldout-99": {}}
        assert heldout_transcripts.misfiled(extra) == ["set heldout-99"]
        other = next(name for name in names if name != owner)
        wrong: dict[str, dict[str, object]] = {**good, owner: {}, other: {first: None}}
        assert heldout_transcripts.misfiled(wrong) == [first]

    @pytest.mark.parametrize("case", HELD_OUT_CASES, ids=_case_id)
    def test_the_case_builds_its_transcript(self, case: HeldOutCase) -> None:
        turns = case.turns()
        document = case.document()
        segments = document.transcript_segments
        assert len(segments) == len(turns)
        for turn, segment in zip(turns, segments, strict=True):
            assert segment.speaker == turn.speaker
            assert [word.word_text for word in segment.transcript_words] == turn.text.split()
        assert any(turn.speaker == case.clinician_speaker for turn in turns)
        assert TranscriptDocument.from_bytes(document.to_bytes()) == document

    @pytest.mark.parametrize("case", HELD_OUT_CASES, ids=_case_id)
    def test_the_expectations_are_well_formed(self, case: HeldOutCase) -> None:
        turns = case.turns()

        def spoken(index: int) -> bool:
            return 0 <= index < len(turns) and bool(turns[index].text.split())

        if case.boundary is not None:
            # A cut needs clinical content before it, so it is never segment 0.
            assert case.boundary > 0 and spoken(case.boundary)
        for indices in (case.corrections, case.unsure):
            assert list(indices) == sorted(set(indices))
            assert all(spoken(index) for index in indices)
            # Nothing at or after the cut reaches the note to be marked or carried.
            assert case.boundary is None or all(index < case.boundary for index in indices)
        # The mark is never the clinician's (D7); a correction may be, since D4
        # carries any speaker and ``heldout-2``'s spec says "a speaker" (Task 0.12).
        assert all(turns[index].speaker != case.clinician_speaker for index in case.unsure)
        for index in case.corrections:
            # The same speaker's routed line is the segment just before.
            assert index > 0 and turns[index - 1].speaker == turns[index].speaker
        for reason in (case.boundary_reason, case.corrections_reason, case.unsure_reason):
            assert reason.strip() and "\n" not in reason

    @pytest.mark.parametrize("case", HELD_OUT_CASES, ids=_case_id)
    def test_corrections_and_hedges_can_reach_the_note(self, case: HeldOutCase) -> None:
        """Review round 8: the routing preconditions D4 and D7 state, with the
        validation config's cues over the shipped ones (the app's two
        layers) — never the phrase lists the features read. A correction
        holds no cue of either layer and follows its speaker's cue-routed
        line in a section the clinician does not own (one hop); a hedged
        line is quoted: it routes, or it is a correction."""
        cues = _validation_cues()
        turns = case.turns()

        def route(index: int) -> NoteSectionKey | None:
            turn = turns[index]
            return layered_section(
                cues,
                DEFAULT_SECTION_CUES,
                content_tokens(turn.text),
                CANONICAL_SECTION_KEYS,
                speaker=turn.speaker,
                clinician_speaker=case.clinician_speaker,
                question=is_interrogative(turn.text),
            )

        for index in case.corrections:
            tokens = content_tokens(turns[index].text)
            assert not any_cue_matches(cues, DEFAULT_SECTION_CUES, tokens), (case.case_id, index)
            assert index - 1 not in case.corrections, (case.case_id, index)
            previous = route(index - 1)
            assert previous is not None, (case.case_id, index)
            assert previous not in CLINICIAN_OWNED_SECTIONS, (case.case_id, index)
        for index in case.unsure:
            assert index in case.corrections or route(index) is not None, (case.case_id, index)

    def test_the_next_patients_lines_are_never_facts_of_the_first(self) -> None:
        for case in HELD_OUT_CASES:
            if case.boundary is None or case.explicit_turns:
                continue
            script = load_script(script_path(case.case_id))
            withheld = [fact.kind for fact in script.facts if fact.line >= case.boundary]
            assert set(withheld) <= {"absent"}, case.case_id

    def test_each_expectation_is_exercised_both_ways(self) -> None:
        for expected in (
            [case.boundary is not None for case in HELD_OUT_CASES],
            [bool(case.corrections) for case in HELD_OUT_CASES],
            [bool(case.unsure) for case in HELD_OUT_CASES],
        ):
            assert sum(expected) >= 3 and expected.count(False) >= 3


# Validation-run6 plan Task 0.9 (peer round 5 PR-MED-022): the fixture's
# builder moved into the harness unchanged — the SHA-256 over every case's
# id and document JSON, captured before the move. A change to the builder,
# a case id or anything a case's document is built from (a held-out script's
# lines, a case's explicit turns) changes it, and is a dated decision (C3);
# a case's expectations and a script's facts are not in the document, so
# this pin does not cover them.
_HELD_OUT_DOCUMENTS_SHA256 = "88d190e841448fe0088936ebfcf9bd0f2ca51372a19b9c2678577818e824a1ff"


def _held_out_documents_sha256() -> str:
    """Over the ``heldout`` set's cases, the ones the builder moved under
    (``heldout-2``'s cases, written in Task 0.12, came after the move)."""
    digest = hashlib.sha256()
    for case in held_out_set("heldout").all_cases():
        digest.update(case.case_id.encode())
        digest.update(b"\0")
        digest.update(case.document().model_dump_json().encode())
        digest.update(b"\0")
    return digest.hexdigest()


def _table_sets() -> list[HeldOutSet]:
    """The sets whose axis scripts have rows in the R3 table: the
    run-of-record set, every held-out set whose cases are written (its rows
    are written with them — Task 0.12 for ``heldout-2``), and every
    ``tails_by_role`` set (its rows are the role tails — Task 0.17)."""
    return [
        _RUN_OF_RECORD,
        *(s for s in HELD_OUT_SETS if s.cases_written or s.tails_by_role),
    ]


def _axis_scripts() -> list[tuple[HeldOutSet, EncounterScript]]:
    return [
        (held_out, script)
        for held_out in _table_sets()
        for script in _loaded(held_out)
        if _NEXT_PATIENT_AXIS in script.axes
    ]


def _tail_problems(
    held_out: HeldOutSet,
    script: EncounterScript,
    rows: Mapping[str, int | None],
    boundaries: Mapping[str, int | None],
) -> list[str]:
    """One axis script's R3-table problems (D8, D14, D16), as codes:
    ``missing-tail-row``; ``tail-disagrees`` (a ``tails_by_role`` set's row
    is not its first ``next_patient`` line); ``boundary-disagrees`` (a set
    with written cases: the row is not the case's boundary);
    ``tail-out-of-range``; ``fact-in-tail-not-absent:<fact>``; and
    ``absent-fact-before-tail:<fact>`` (a material absent fact before the
    tail — not applied to a ``tails_by_role`` set, whose welcome line may
    hold one, D16)."""
    stamp = script.encounter_id
    if stamp not in rows:
        return [_problem(stamp, "missing-tail-row")]
    tail = rows[stamp]
    problems: list[str] = []
    if held_out.tails_by_role:
        if tail != _role_tail(script):
            problems.append(_problem(stamp, "tail-disagrees"))
    elif held_out.cases_written and held_out is not _RUN_OF_RECORD:
        if tail != boundaries.get(stamp):
            problems.append(_problem(stamp, "boundary-disagrees"))
    if tail is not None and not 0 < tail < len(script.lines):
        problems.append(_problem(stamp, "tail-out-of-range"))
    for index, fact in enumerate(script.facts):
        in_tail = tail is not None and fact.line >= tail
        if in_tail and fact.kind != "absent":
            problems.append(_problem(stamp, "fact-in-tail-not-absent", index))
        if not held_out.tails_by_role and fact.kind == "absent" and fact.material and not in_tail:
            problems.append(_problem(stamp, "absent-fact-before-tail", index))
    return problems


@functools.cache
def _all_tail_problems() -> tuple[str, ...]:
    boundaries = {case.case_id: case.boundary for case in HELD_OUT_CASES}
    axis_ids = {script.encounter_id for _, script in _axis_scripts()}
    problems = [
        problem
        for held_out, script in _axis_scripts()
        for problem in _tail_problems(held_out, script, REFERENCE_TAIL_STARTS, boundaries)
    ]
    problems += [
        _problem(encounter_id, "row-without-axis")
        for encounter_id in REFERENCE_TAIL_STARTS
        if encounter_id not in axis_ids
    ]
    return tuple(problems)


def _tail_codes(wanted: Iterable[str]) -> list[str]:
    keep = frozenset(wanted)
    return [entry for entry in _all_tail_problems() if _code(entry) in keep]


class TestReferenceDocument:
    """Validation-run6 plan D8: one turn-level builder in the harness
    (``document_from_turns``), the script adapter ``reference_document``,
    and the fixture a thin call of the same builder."""

    def test_the_moved_builder_gives_every_held_out_case_the_same_document(self) -> None:
        assert len(held_out_set("heldout").all_cases()) == 32
        assert _held_out_documents_sha256() == _HELD_OUT_DOCUMENTS_SHA256

    def test_the_fixture_builds_through_the_harness(self) -> None:
        for case in HELD_OUT_CASES:
            assert case.document() == document_from_turns(case.turns()), case.case_id

    def test_the_fixture_delegates_to_the_harness_builder(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Equal documents would also pass a restored copy of the old
        builder; the fixture must CALL the harness's one builder (peer round
        14 PR-LOW-012)."""
        seen: list[object] = []
        sentinel = object()

        def fake(turns: object) -> object:
            seen.append(turns)
            return sentinel

        monkeypatch.setattr(heldout_transcripts, "document_from_turns", fake)
        turns = HELD_OUT_CASES[0].turns()
        assert heldout_transcripts.build_document(turns) is sentinel
        assert seen == [turns]

    @pytest.mark.parametrize("path", _heldout_paths(), ids=_path_id)
    def test_the_reference_document_is_the_scripts_own_lines(
        self, path: Path, record_property: RecordProperty
    ) -> None:
        held_out = _owner(path)
        index = held_out.script_paths().index(path)
        problems = [
            entry
            for entry in _script_problems(path, held_out, index)
            if _code(entry) in _LOAD_CODES
        ]
        stamp = _stamp(path, held_out)
        if stamp is not None and not problems:
            script = load_script(path)
            problems = _reference_mismatches(stamp, script, reference_document(script))
        assert _record(record_property, problems) == []

    def test_every_run_of_record_script_has_a_reference_document(self) -> None:
        for script in _scripts():
            segments = reference_document(script).transcript_segments
            assert len(segments) == len(script.lines), script.encounter_id


class TestNextPatientReferenceTables:
    """D8's R3 provenance (D14 since Task 0.17: one table, the tail starts):
    the table names exactly the scripts carrying the axis, a negative (no
    next patient) is None, the tail starts equal the held-out fixture's
    boundary where a set's cases are written, and a ``tails_by_role`` set's
    rows are its first ``next_patient`` lines."""

    def test_the_table_names_exactly_the_scripts_with_the_axis(
        self, record_property: RecordProperty
    ) -> None:
        problems = _tail_codes({"missing-tail-row", "row-without-axis"})
        assert _record(record_property, problems) == []

    def test_the_tail_starts_equal_the_held_out_boundaries(
        self, record_property: RecordProperty
    ) -> None:
        problems = _tail_codes({"boundary-disagrees"})
        assert _record(record_property, problems) == []

    def test_the_rows_equal_the_role_tails(self, record_property: RecordProperty) -> None:
        """Task 0.17 (D16): a ``tails_by_role`` set's row is the index of
        its first ``next_patient`` line, or None when it has none — so a
        non-null row exists exactly when such a line does, and an axis
        script without one is a boundary negative. The copy from the roles
        into the table is machine-checked here."""
        problems = _tail_codes({"tail-disagrees"})
        assert _record(record_property, problems) == []

    def test_every_material_absent_fact_lies_in_a_tail(
        self, record_property: RecordProperty
    ) -> None:
        """Not applied to a ``tails_by_role`` set (peer round 25): a
        material absent fact on the clinician's welcome line precedes the
        role tail, and is then never R3 (D16's stated cost)."""
        problems = _tail_codes({"absent-fact-before-tail"})
        assert _record(record_property, problems) == []

    def test_every_fact_in_a_tail_is_an_absent_fact(self, record_property: RecordProperty) -> None:
        """The other side, read off the facts rather than the table: nothing
        the note should hold lies at or after a tail start, so a tail start
        placed on a first-patient fact's line fails. A start moved onto a
        fact-free line, or one moved a line late, passes here and is caught
        by the boundary equality (held-out), the role tails (``tails_by_role``)
        or the exact pin of the six run-of-record rows (Task 0.9 review).
        Task 0.12 (2026-10-24): ABSENT, not material absent — ``heldout-2``
        puts nonmaterial absent facts in its tails (the note should hold none
        of them either); R3 still counts the material ones only. A tail is
        never line 0 and always names a line."""
        problems = _tail_codes({"fact-in-tail-not-absent", "tail-out-of-range"})
        assert _record(record_property, problems) == []

    def test_the_run_of_record_rows_are_pinned_exactly(self) -> None:
        """The six run-of-record scripts have no held-out boundary to equal,
        so a row moved one line late (onto the next patient's fact) would
        pass every structural pin above (Task 0.9 review, peer round 13
        PR-LOW-010): each tail start is pinned as read off its script on
        2026-10-23; a change is a dated decision (C3). Task 0.17 (D14): the
        greeting-line half of the old pairs is gone with its table."""
        run_of_record = {
            encounter_id: tail
            for encounter_id, tail in REFERENCE_TAIL_STARTS.items()
            if not encounter_id.startswith(SCRIPT_CASE_PREFIXES)
        }
        assert run_of_record == {
            "syn-06": 4,
            "syn-20": 4,
            "syn-21": 4,
            "syn-38": 4,
            "syn-43": 6,
            "syn-46": 4,
        }

    def test_both_ways(self) -> None:
        tails = list(REFERENCE_TAIL_STARTS.values())
        assert tails.count(None) >= 3 and len(tails) - tails.count(None) >= 3


# ---------------------------------------------------------------------------
# Task 0.17 (D16): the helpers' own output is content-free. A sentinel word
# planted at the start, middle and end of lines, as an unknown key and in a
# fed document must never appear in a returned code or a loader message.
# ---------------------------------------------------------------------------

_SENTINEL = "zqxsentinelwordqz"
_BLIND = HeldOutSet(
    "heldout-9",
    "h3-",
    (),
    cases_written=False,
    tails_by_role=True,
    routed_material=True,
    script_count=(20, 25),
    facts_per_script=(3, 6),
)


def _sentinel_script(encounter_id: str) -> dict[str, Any]:
    """A well-formed synthetic script with the sentinel at the start, middle
    and end of its lines, a routed patient fact (the validation config's
    ``coming in with`` cue) and a next patient."""
    return {
        "schema_version": 1,
        "encounter_id": encounter_id,
        "appointment_type": "follow_up",
        "axes": ["end_and_new_patient"],
        "lines": [
            {"role": "clinician", "text": f"{_SENTINEL} how is the knee today"},
            {"role": "patient", "text": f"I am coming in with {_SENTINEL} pain in my left knee"},
            {"role": "clinician", "text": f"thanks, see you next week {_SENTINEL}"},
            {"role": "next_patient", "text": f"hello, I have a sore {_SENTINEL} shoulder"},
        ],
        "facts": [
            {"kind": "laterality", "tokens": ["left", "knee"], "line": 1, "material": True},
            {"kind": "present", "tokens": ["knee"], "line": 0, "material": True},
            {"kind": "absent", "tokens": ["shoulder"], "line": 3, "material": True},
        ],
        "conditions": {"voice_slots": {"clinician": 0, "patient": 1, "next_patient": 2}},
    }


class TestProblemCodesAreContentFree:
    def _write(self, folder: Path, name: str, body: object) -> Path:
        path = folder / f"{name}.json"
        path.write_text(json.dumps(body), encoding="utf-8")
        return path

    def test_a_broken_set_reports_codes_only(self, tmp_path: Path) -> None:
        unknown_key = {**_sentinel_script("h3-01"), _SENTINEL: 1}
        no_conditions = {
            key: value for key, value in _sentinel_script("h3-02").items() if key != "conditions"
        }
        unrouted = _sentinel_script("h3-03")
        unrouted["lines"][1] = {"role": "patient", "text": f"{_SENTINEL} left knee {_SENTINEL}"}
        absent_tokens = _sentinel_script("h3-04")
        absent_tokens["facts"] = [
            {"kind": "present", "tokens": [_SENTINEL, "elbow"], "line": 1, "material": True}
        ]
        paths = [
            self._write(tmp_path, "h3-01", unknown_key),
            self._write(tmp_path, "h3-02", no_conditions),
            self._write(tmp_path, "h3-03", unrouted),
            self._write(tmp_path, "h3-04", absent_tokens),
            self._write(tmp_path, f"h3-{_SENTINEL}", _sentinel_script("h3-05")),
        ]
        problems = [
            problem
            for index, path in enumerate(paths)
            for problem in _script_problems(path, _BLIND, index)
        ]
        codes = {(entry.split(":")[0], _code(entry)) for entry in problems}
        assert ("h3-01", "load-error") in codes
        assert ("h3-02", "no-conditions") in codes
        assert ("h3-03", "fact-unrouted") in codes
        assert ("h3-04", "load-error") in codes
        assert "heldout-9:bad-id:4" in problems
        assert all(PROBLEM_RE.fullmatch(entry) for entry in problems)
        assert not any(_SENTINEL in entry for entry in problems)
        for path in paths[:4]:
            try:
                load_script(path)
            except ScriptError as exc:
                assert _SENTINEL not in str(exc)

    def test_a_well_formed_script_has_no_problem(self, tmp_path: Path) -> None:
        path = self._write(tmp_path, "h3-06", _sentinel_script("h3-06"))
        assert _script_problems(path, _BLIND, 0) == []

    def test_a_fed_reference_mismatch_and_a_disagreeing_row_report_codes_only(
        self, tmp_path: Path
    ) -> None:
        script = load_script(self._write(tmp_path, "h3-07", _sentinel_script("h3-07")))
        turns = [(line.role, f"{line.text} {_SENTINEL}") for line in script.lines]
        document = document_from_turns(
            heldout_transcripts.Turn(speaker, text) for speaker, text in turns
        )
        mismatches = _reference_mismatches("h3-07", script, document)
        assert mismatches == [f"h3-07:reference-mismatch:{index}" for index in range(4)]
        assert _reference_mismatches("h3-07", script, reference_document(script)) == []
        rows = {"h3-07": 2}
        disagreeing = _tail_problems(_BLIND, script, rows, {})
        assert disagreeing == ["h3-07:tail-disagrees"]
        assert _tail_problems(_BLIND, script, {"h3-07": 3}, {}) == []
        assert _tail_problems(_BLIND, script, {}, {}) == ["h3-07:missing-tail-row"]
        for entry in [*mismatches, *disagreeing]:
            assert PROBLEM_RE.fullmatch(entry) and _SENTINEL not in entry

    def test_the_blind_set_lints_fire(self, tmp_path: Path) -> None:
        """Round 32 MED-001: the lints that only ``heldout-3`` carries each
        fire on a synthetic negative (the blind set is never inspected, so a
        lint that wrongly passed there would go unseen)."""
        two_facts = _sentinel_script("h3-11")
        two_facts["facts"] = two_facts["facts"][:2]
        seven_facts = _sentinel_script("h3-12")
        seven_facts["facts"] = (
            seven_facts["facts"]
            + [{"kind": "present", "tokens": ["knee"], "line": 0, "material": False}] * 4
        )
        no_axis = {**_sentinel_script("h3-13"), "axes": ["laterality"]}
        found = [
            _script_problems(self._write(tmp_path, stem, body), _BLIND, 0)
            for stem, body in (("h3-11", two_facts), ("h3-12", seven_facts), ("h3-13", no_axis))
        ]
        assert "h3-11:facts-out-of-bounds:2" in found[0]
        assert "h3-12:facts-out-of-bounds:7" in found[1]
        assert "h3-13:next-patient-without-axis" in found[2]

        early_absent = _sentinel_script("h3-14")
        early_absent["facts"].append(
            {"kind": "absent", "tokens": ["knee"], "line": 0, "material": True}
        )
        script = load_script(self._write(tmp_path, "h3-14", early_absent))
        rows = {"h3-14": 3}
        assert _tail_problems(_BLIND, script, rows, {}) == []
        seen = HeldOutSet("heldout-8", "h3-", (), cases_written=False)
        assert _tail_problems(seen, script, rows, {}) == ["h3-14:absent-fact-before-tail:3"]

        def paths(count: int) -> list[Path]:
            return [tmp_path / f"h3-{index:02d}.json" for index in range(1, count + 1)]

        assert _set_problems(_BLIND, paths(19)) == ["heldout-9:size-out-of-bounds:19"]
        assert _set_problems(_BLIND, paths(26)) == ["heldout-9:size-out-of-bounds:26"]
        assert _set_problems(_BLIND, paths(10)) == ["heldout-9:size-out-of-bounds:10"]
        assert _set_problems(_BLIND, paths(20)) == []
        assert _set_problems(_BLIND, paths(25)) == []
        assert _set_problems(_BLIND, []) == []

    def test_the_grammar_refuses_anything_else(self) -> None:
        for bad in (
            f"h3-01:{_SENTINEL}",
            "h3-01:load-error:12345",
            f"{_SENTINEL}:load-error",
            "h3-001:load-error",
            "edge-01:load-error",
            "h3-01:load-error ",
        ):
            assert not PROBLEM_RE.fullmatch(bad)
        with pytest.raises(AssertionError):
            _problem("h3-01", _SENTINEL)
        with pytest.raises(AssertionError):
            _problem(_SENTINEL, "load-error")
        assert _problem("h3-01", "facts-out-of-bounds", 123456) == "h3-01:facts-out-of-bounds:9999"
