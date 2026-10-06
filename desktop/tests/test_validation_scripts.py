"""Pilot plan Task 2.6: the repository's synthetic encounter scripts
(``validation/scripts/``) and the note config they are written against
(``validation/config/``).

Every script loads; each axis and each fact kind appears at least three
times; every script is synthetic and renders through the set builder with a
fake voice (no real speech engine); and the validation config's autofill
triggers are spoken only in the scripts that list the warnings they are
written to provoke. The scripts are invented consultations.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

from scribe_desktop.note import (
    CANONICAL_SECTION_KEYS,
    content_tokens,
    first_matching_section,
    is_interrogative,
)
from scribe_desktop.note_config import load_note_config
from scribe_desktop.speaker_eval import CLINICIAN_LABEL, parse_audacity_labels
from scribe_desktop.validation import (
    AXES,
    FACT_KINDS,
    EncounterScript,
    _occurrences,
    load_script,
)
from scribe_desktop.validation_set import render_encounter, to_pcm16

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "validation" / "scripts"
CONFIG = REPO / "validation" / "config"
MIN_PER_AXIS = 3
MIN_PER_KIND = 3
_CLAUSE_END = re.compile(r"(?<=[.?!,;])\s+")


def _scripts() -> list[EncounterScript]:
    return [load_script(path) for path in sorted(SCRIPTS.glob("*.json"))]


def _contains(tokens: tuple[str, ...], needle: tuple[str, ...]) -> bool:
    return bool(_occurrences(tokens, needle))


def _short_turn(text: str, voice: int, rate: int) -> bytes:
    """A fake voice: 20 ms of a square wave per word (fast to mix)."""
    samples = 320 * len(text.split())
    level = 1000 * (voice + 1)
    return to_pcm16([level if (index // 20) % 2 else -level for index in range(samples)])


class TestScripts:
    def test_every_script_loads(self) -> None:
        scripts = _scripts()
        assert len(scripts) >= 40
        assert len({script.encounter_id for script in scripts}) == len(scripts)

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
        offending = []
        for script in _scripts():
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
        assert offending == []

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
        cues = load_note_config(CONFIG).normalised_cues()
        unrouted = []
        for script in _scripts():
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
        assert unrouted == []

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
    def test_every_script_renders_with_two_fake_voices(self, path: Path) -> None:
        script = load_script(path)
        pcm, labels, placement = render_encounter(script, ("Voice 0", "Voice 1"), _short_turn)
        assert len(pcm) == placement.total * 2
        track = parse_audacity_labels(labels)
        assert [span.label for span in track.spans] == [line.role for line in script.lines]
