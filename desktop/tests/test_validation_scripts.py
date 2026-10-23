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
fixture's table (``HELD_OUT_SETS``: ``validation/heldout`` and
``validation/heldout-2``); a set with no scripts yet passes them vacuously,
and a set whose cases are not yet written gets the script lints only.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

import pytest

from fixtures import heldout_transcripts
from fixtures.heldout_transcripts import (
    EDGE_CASE_PREFIX,
    HELD_OUT_CASES,
    HELD_OUT_SETS,
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
    REFERENCE_GREETING_LINES,
    REFERENCE_MODEL_NAME,
    REFERENCE_TAIL_STARTS,
    EncounterScript,
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


def _uncertain_facts_in_unrouted_clauses(
    scripts: Iterable[EncounterScript],
) -> list[tuple[str, int]]:
    """(encounter, fact index) for each ``expect_uncertain`` fact with no
    clause holding it that routes (round 11 MED-003, round 12 LOW-016)."""
    cues = load_note_config(CONFIG).normalised_cues()
    unrouted = []
    for script in scripts:
        for index, fact in enumerate(script.facts):
            if not fact.expect_uncertain:
                continue
            line = script.lines[fact.line]
            routed = [
                first_matching_section(
                    cues,
                    content_tokens(clause),
                    CANONICAL_SECTION_KEYS,
                    speaker=line.role,
                    clinician_speaker=CLINICIAN_LABEL,
                    # The provider tests the whole utterance; the line
                    # may reach it as one segment, so a clause counts as
                    # a question if either it or its line is one (round
                    # 13 LOW-007) — routing holds under both splits.
                    question=is_interrogative(clause) or is_interrogative(line.text),
                )
                for clause in _CLAUSE_END.split(line.text)
                if _contains(content_tokens(clause), fact.tokens)
            ]
            if not any(key is not None for key in routed):
                unrouted.append((script.encounter_id, index))
    return unrouted


def _short_turn(text: str, voice: int, rate: int) -> bytes:
    """A fake voice: 20 ms of a square wave per word (fast to mix)."""
    samples = 320 * len(text.split())
    level = 1000 * (voice + 1)
    return to_pcm16([level if (index // 20) % 2 else -level for index in range(samples)])


class TestScripts:
    def test_every_script_loads(self) -> None:
        scripts = _scripts()
        assert len(scripts) >= 50
        assert len({script.encounter_id for script in scripts}) == len(scripts)

    def test_every_slot_is_in_range_and_the_third_voice_is_the_new_scripts_patient(
        self,
    ) -> None:
        used: dict[str, dict[str, int]] = {}
        for script in _scripts():
            assert script.conditions is not None, script.encounter_id
            used[script.encounter_id] = script.conditions.voice_slots
        assert all(
            slot < len(FAKE_VOICES) for slots in used.values() for slot in slots.values()
        )
        third = {
            encounter_id: [role for role, slot in slots.items() if slot == THIRD_VOICE_SLOT]
            for encounter_id, slots in used.items()
            if THIRD_VOICE_SLOT in slots.values()
        }
        assert third == {encounter_id: ["patient"] for encounter_id in THIRD_VOICE_SCRIPTS}

    def test_every_script_uses_the_current_voice_baseline(self) -> None:
        for script in _scripts():
            assert script.conditions is not None, script.encounter_id
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

    def test_every_script_is_synthetic_with_material_facts(self) -> None:
        for script in _scripts():
            assert script.conditions is not None, script.encounter_id
            assert any(fact.material for fact in script.facts), script.encounter_id

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
        cues = load_note_config(CONFIG).normalised_cues()
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
        triggers = [
            content_tokens(rule.trigger_phrase) for rule in load_note_config(CONFIG).autofill_rules
        ]
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
    @pytest.mark.parametrize("path", sorted(SCRIPTS.glob("*.json")), ids=lambda path: path.stem)
    def test_every_script_renders_with_fake_voices(self, path: Path) -> None:
        script = load_script(path)
        pcm, labels, placement = render_encounter(script, FAKE_VOICES, _short_turn)
        assert len(pcm) == placement.total * 2
        track = parse_audacity_labels(labels)
        assert [span.label for span in track.spans] == [line.role for line in script.lines]


def _heldout_paths() -> list[Path]:
    """Every held-out set's scripts (Task 0.11)."""
    return [path for held_out in HELD_OUT_SETS for path in held_out.script_paths()]


def _heldout_scripts(held_out: HeldOutSet) -> list[EncounterScript]:
    return [load_script(path) for path in held_out.script_paths()]


def _set_name(held_out: HeldOutSet) -> str:
    return held_out.name


# Review round 8 LOW-005 (routed to the held-out author, not edited here —
# C3): an uncertain fact whose clause has no cue of its own, so a recogniser
# split at the comma leaves it unquoted. Pinned exactly, so a revision of
# the script fails this lint until the entry is removed. Empty since the
# author's revision (stage-2 leg vy3): ``hld-21`` line 5's fact now sits in
# its routed clause.
_HELD_OUT_UNROUTED_PENDING: list[tuple[str, int]] = []


class TestHeldOutScripts:
    """Validation-pass plan Task 0.9: the held-out set is never tuned to, so
    its lint checks only that it is usable — not its axis or kind counts,
    and the same alignment, routing and trigger checks as the run-of-record
    set (review round 8 LOW-004). Since validation-run6 Task 0.11 each lint
    runs per held-out set."""

    def test_the_sets_have_distinct_folders_and_prefixes(self) -> None:
        names = [held_out.name for held_out in HELD_OUT_SETS]
        assert names == ["heldout", "heldout-2"]
        assert len(set(SCRIPT_CASE_PREFIXES)) == len(SCRIPT_CASE_PREFIXES)
        for prefix in (*SCRIPT_CASE_PREFIXES, EDGE_CASE_PREFIX):
            others = [p for p in (*SCRIPT_CASE_PREFIXES, EDGE_CASE_PREFIX) if p != prefix]
            assert not any(other.startswith(prefix) for other in others), prefix

    @pytest.mark.parametrize("held_out", HELD_OUT_SETS, ids=_set_name)
    def test_no_held_out_fact_borders_a_repeat_of_its_own_edge_word(
        self, held_out: HeldOutSet
    ) -> None:
        assert _facts_bordering_their_edge_word(_heldout_scripts(held_out)) == []

    @pytest.mark.parametrize("held_out", HELD_OUT_SETS, ids=_set_name)
    def test_every_held_out_uncertain_fact_sits_in_a_routed_clause(
        self, held_out: HeldOutSet
    ) -> None:
        unrouted = _uncertain_facts_in_unrouted_clauses(_heldout_scripts(held_out))
        pending = [
            item for item in _HELD_OUT_UNROUTED_PENDING
            if item[0].startswith(held_out.prefix)
        ]
        assert unrouted == pending

    @pytest.mark.parametrize("held_out", HELD_OUT_SETS, ids=_set_name)
    def test_no_held_out_script_speaks_an_autofill_trigger(self, held_out: HeldOutSet) -> None:
        # No held-out scenario is about autofill, so a trigger would only
        # add a warning its script does not list.
        triggers = [
            content_tokens(rule.trigger_phrase) for rule in load_note_config(CONFIG).autofill_rules
        ]
        spoken = [
            (script.encounter_id, index)
            for script in _heldout_scripts(held_out)
            for index, line in enumerate(script.lines)
            if any(_contains(content_tokens(line.text), trigger) for trigger in triggers)
        ]
        assert spoken == []

    @pytest.mark.parametrize("held_out", HELD_OUT_SETS, ids=_set_name)
    def test_every_held_out_script_loads_with_a_held_out_id(self, held_out: HeldOutSet) -> None:
        paths = held_out.script_paths()
        ids = [load_script(path).encounter_id for path in paths]
        # A set whose cases are not yet written may have no scripts yet
        # (Task 0.10 authors ``heldout-2``); once it has any, the minimum holds.
        if held_out.cases_written or ids:
            assert len(ids) >= MIN_HELDOUT
        assert len(set(ids)) == len(ids)
        assert ids == [path.stem for path in paths]
        assert [i for i in ids if not i.startswith(held_out.prefix)] == []
        assert not set(ids) & {path.stem for path in SCRIPTS.glob("*.json")}

    def test_the_first_held_out_set_is_present(self) -> None:
        """A missing ``validation/heldout`` folder would pass the per-set
        lints vacuously; its cases are written, so its scripts must exist."""
        assert len(held_out_set("heldout").script_paths()) == 22

    @pytest.mark.parametrize("held_out", HELD_OUT_SETS, ids=_set_name)
    def test_every_held_out_script_is_synthetic_with_material_facts(
        self, held_out: HeldOutSet
    ) -> None:
        for path in held_out.script_paths():
            script = load_script(path)
            assert script.conditions is not None, script.encounter_id
            slots = script.conditions.voice_slots.values()
            assert all(slot < len(FAKE_VOICES) for slot in slots), script.encounter_id
            assert any(fact.material for fact in script.facts), script.encounter_id

    @pytest.mark.parametrize("path", _heldout_paths(), ids=lambda path: path.stem)
    def test_every_held_out_script_renders_with_fake_voices(self, path: Path) -> None:
        script = load_script(path)
        pcm, labels, placement = render_encounter(script, FAKE_VOICES, _short_turn)
        assert len(pcm) == placement.total * 2
        track = parse_audacity_labels(labels)
        assert [span.label for span in track.spans] == [line.role for line in script.lines]


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
        filed under the wrong set are each named."""
        first = HELD_OUT_CASES[0].case_id
        good = {"heldout": {first: None}, "heldout-2": {}}
        assert heldout_transcripts.misfiled(good) == []
        assert heldout_transcripts.misfiled({"heldout": {}}) == ["set heldout-2"]
        extra = {**good, "heldout-9": {}}
        assert heldout_transcripts.misfiled(extra) == ["set heldout-9"]
        wrong = {"heldout": {}, "heldout-2": {first: None}}
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
            assert all(turns[index].speaker != case.clinician_speaker for index in indices)
            # Nothing at or after the cut reaches the note to be marked or carried.
            assert case.boundary is None or all(index < case.boundary for index in indices)
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
        cues = load_note_config(CONFIG).normalised_cues()
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
_NEXT_PATIENT_AXIS = "end_and_new_patient"


def _held_out_documents_sha256() -> str:
    digest = hashlib.sha256()
    for case in HELD_OUT_CASES:
        digest.update(case.case_id.encode())
        digest.update(b"\0")
        digest.update(case.document().model_dump_json().encode())
        digest.update(b"\0")
    return digest.hexdigest()


def _written_heldout_scripts() -> list[EncounterScript]:
    """The scripts of the held-out sets whose cases are written: a set's R3
    table entries are written with its cases (Task 0.12 for ``heldout-2``)."""
    return [
        script
        for held_out in HELD_OUT_SETS
        if held_out.cases_written
        for script in _heldout_scripts(held_out)
    ]


def _axis_scripts() -> list[EncounterScript]:
    return [
        script
        for script in [*_scripts(), *_written_heldout_scripts()]
        if _NEXT_PATIENT_AXIS in script.axes
    ]


class TestReferenceDocument:
    """Validation-run6 plan D8: one turn-level builder in the harness
    (``document_from_turns``), the script adapter ``reference_document``,
    and the fixture a thin call of the same builder."""

    def test_the_moved_builder_gives_every_held_out_case_the_same_document(self) -> None:
        assert len(HELD_OUT_CASES) == 32
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

    @pytest.mark.parametrize("path", _heldout_paths(), ids=lambda path: path.stem)
    def test_the_reference_document_is_the_scripts_own_lines(self, path: Path) -> None:
        script = load_script(path)
        document = reference_document(script)
        segments = document.transcript_segments
        assert [segment.speaker for segment in segments] == [line.role for line in script.lines]
        for line, segment in zip(script.lines, segments, strict=True):
            assert [word.word_text for word in segment.transcript_words] == line.text.split()
            assert not any(word.uncertain for word in segment.transcript_words)
        assert document.model_name == REFERENCE_MODEL_NAME

    def test_every_run_of_record_script_has_a_reference_document(self) -> None:
        for script in _scripts():
            segments = reference_document(script).transcript_segments
            assert len(segments) == len(script.lines), script.encounter_id


class TestNextPatientReferenceTables:
    """D8's R3 provenance: both tables name exactly the scripts carrying the
    axis, a negative (no next patient) is None in both, the greeting line is
    the tail start or the line before it (a shared closing-and-greeting
    line), and the tail starts equal the held-out fixture's boundary."""

    def test_both_tables_name_exactly_the_scripts_with_the_axis(self) -> None:
        ids = {script.encounter_id for script in _axis_scripts()}
        assert set(REFERENCE_GREETING_LINES) == ids
        assert set(REFERENCE_TAIL_STARTS) == ids

    def test_the_tail_starts_equal_the_held_out_boundaries(self) -> None:
        boundaries = {case.case_id: case.boundary for case in HELD_OUT_CASES}
        for encounter_id, tail in REFERENCE_TAIL_STARTS.items():
            if encounter_id.startswith(SCRIPT_CASE_PREFIXES):
                assert tail == boundaries[encounter_id], encounter_id

    def test_the_greeting_line_is_the_tail_start_or_shares_the_closing_line(self) -> None:
        shared = []
        for script in _axis_scripts():
            greeting = REFERENCE_GREETING_LINES[script.encounter_id]
            tail = REFERENCE_TAIL_STARTS[script.encounter_id]
            assert (greeting is None) == (tail is None), script.encounter_id
            if greeting is None or tail is None:
                continue
            assert 0 < tail < len(script.lines), script.encounter_id
            assert greeting in (tail - 1, tail), script.encounter_id
            if greeting == tail - 1:
                shared.append(script.encounter_id)
        assert shared == ["hld-11"]

    def test_every_material_absent_fact_lies_in_a_tail(self) -> None:
        for script in _axis_scripts():
            tail = REFERENCE_TAIL_STARTS[script.encounter_id]
            for fact in script.facts:
                if fact.kind == "absent" and fact.material:
                    assert tail is not None and fact.line >= tail, script.encounter_id

    def test_every_fact_in_a_tail_is_a_material_absent_fact(self) -> None:
        """The other side, read off the facts rather than the table: nothing
        the note should hold lies at or after a tail start, so a tail start
        placed on a first-patient fact's line fails. A start moved onto a
        fact-free line, or a pair moved one line late, passes here and is
        caught by the boundary equality (held-out) or the exact pin of the
        six run-of-record pairs (Task 0.9 review)."""
        for script in _axis_scripts():
            tail = REFERENCE_TAIL_STARTS[script.encounter_id]
            if tail is None:
                continue
            for fact in script.facts:
                if fact.line >= tail:
                    assert fact.kind == "absent" and fact.material, script.encounter_id

    def test_the_run_of_record_pairs_are_pinned_exactly(self) -> None:
        """The six run-of-record scripts have no held-out boundary to equal,
        so a pair moved one line late (onto the next patient's fact) would
        pass every structural pin above (Task 0.9 review, peer round 13
        PR-LOW-010): each pair is pinned as read off its script's greeting
        line on 2026-10-23; a change is a dated decision (C3)."""
        run_of_record = {
            encounter_id: (REFERENCE_GREETING_LINES[encounter_id], tail)
            for encounter_id, tail in REFERENCE_TAIL_STARTS.items()
            if not encounter_id.startswith(SCRIPT_CASE_PREFIXES)
        }
        assert run_of_record == {
            "syn-06": (4, 4),
            "syn-20": (4, 4),
            "syn-21": (4, 4),
            "syn-38": (4, 4),
            "syn-43": (6, 6),
            "syn-46": (4, 4),
        }

    def test_both_ways(self) -> None:
        tails = list(REFERENCE_TAIL_STARTS.values())
        assert tails.count(None) >= 3 and len(tails) - tails.count(None) >= 3
