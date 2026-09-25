"""Note-learning-and-styles plan Phase 2, Task 2.2: the learned-rule writer.

Pinned here, per the task's Done-when and D5 / D11:
- a bad candidate can never reach disk: an invalid rule (a wording that is
  not one atomic assertion, a trigger with no content tokens, an over-long
  wording) is skipped and reported, the trigger already held by ANY rule is
  a duplicate, and nothing is written when nothing is added;
- exactly one active rule per trigger survives a correction: a wording
  replacement keeps the id and trigger, resets the count, records the
  previous wording, and the file reloads through the real loader;
- loading never breaks: every write is validated by the loader's own rules
  over the exact bytes first; a failed write is typed and leaves the files
  byte-identical; a failed sidecar write after a committed rules write is
  RETURNED, never raised;
- auto-confirm at exactly ``LEARNED_RULE_AUTO_CONFIRM_AFTER`` confirmations;
  ``removed`` demotes and never deletes;
- the trigger heuristic (``propose_rule_trigger``) and the ULID-shaped id.
Written-only-on-Save is the Note tab's contract and lives in
``test_ui_screens.py``.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import scribe_desktop.note_config as note_config_module
from scribe_desktop.logging_setup import _PAYLOAD_SIGNATURES
from scribe_desktop.note import content_tokens
from scribe_desktop.note_config import (
    AUTOFILL_RULES_FILENAME,
    LEARNED_PHRASE_MIN_TOKENS,
    LEARNED_RULE_AUTO_CONFIRM_AFTER,
    LEARNED_RULE_ID_PREFIX,
    LEARNED_RULES_SIDECAR_FILENAME,
    LEARNED_TRIGGER_MAX_TOKENS,
    RULE_WORDING_BLANK,
    RULE_WORDING_HIDDEN_CHARACTER,
    RULE_WORDING_MANY_CLAIMS,
    RULE_WORDING_NOT_ACCEPTED,
    RULE_WORDING_TOO_LONG,
    LearnedRuleCandidate,
    LearnedRuleEntry,
    LearnedRuleHistoryEntry,
    NoteConfigError,
    NoteConfigInvalidError,
    NoteConfigWriteError,
    append_learned_rules,
    delete_learned_rule,
    is_learned_rule_id,
    learned_rule_problem,
    load_learned_rule_entries,
    load_learned_rules,
    load_note_config,
    new_learned_rule_id,
    plain_rule_problem,
    plain_skip_reason,
    propose_rule_trigger,
    record_rule_outcomes,
    refuse_learning_candidate,
    replace_learned_rule_wording,
)
from scribe_desktop.session_store import StoreWriteError

_AT = datetime(2026, 9, 19, 8, 0, tzinfo=UTC)
_LATER = datetime(2026, 9, 19, 9, 0, tzinfo=UTC)
# note._ID_PATTERN restated (the test imports no private name).
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")
_FLOW_2 = "ok we'll put a crack into the neck now"


def _candidate(
    trigger: str = "crack into the neck",
    wording: str = "HVLA Cx",
    section: str = "treatment_performed",
) -> LearnedRuleCandidate:
    return LearnedRuleCandidate(section, trigger, wording)  # type: ignore[arg-type]


def _hand_rule(
    rule_id: str = "r-hep",
    trigger: str = "home exercise",
    wording: str = "Home exercise programme reviewed.",
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "section_key": "advice_home_exercise",
        "trigger_phrase": trigger,
        "expansion": [wording],
    }


def _write_user_rules(root: Path, rules: list[dict[str, Any]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "autofill_rules": rules}
    (root / AUTOFILL_RULES_FILENAME).write_text(json.dumps(payload), encoding="utf-8")


def _rules_by_id(root: Path) -> dict[str, Any]:
    return {rule.rule_id: rule for rule in load_note_config(root).autofill_rules}


def _fail_writes_to(monkeypatch: pytest.MonkeyPatch, filename: str) -> None:
    real = note_config_module.atomic_write_bytes

    def selective(path: Path, blob: bytes, *, error_label: str) -> None:
        if path.name == filename:
            raise StoreWriteError(f"failed writing {error_label}: disk full")
        real(path, blob, error_label=error_label)

    monkeypatch.setattr(note_config_module, "atomic_write_bytes", selective)


def _learn(root: Path, *candidates: LearnedRuleCandidate, at: datetime = _AT) -> list[str]:
    outcome = append_learned_rules(
        candidates or (_candidate(),), config_root=root, learned_at=at
    )
    assert outcome.skipped == ()
    assert outcome.sidecar_error is None
    return [rule.rule_id for rule in outcome.added]


class TestLearnedRuleProblem:
    """Phase H round 24 LOW-005: the edit-time check mirrors the writer's
    validation, so the Note tab's "Will learn" is never withdrawn at Save."""

    def test_a_valid_candidate_has_no_problem(self) -> None:
        assert learned_rule_problem(_candidate()) is None

    def test_an_over_long_wording_names_the_writers_reason(self, tmp_path: Path) -> None:
        invalid = _candidate(wording=("a " * 1100).strip())
        problem = learned_rule_problem(invalid)
        assert problem
        outcome = append_learned_rules([invalid], config_root=tmp_path, learned_at=_AT)
        assert outcome.added == ()
        assert outcome.skipped == ((invalid, f"invalid: {problem}"),)


# What the validator's message carries and the clinician must never be shown
# (Phase H live smoke, item 2): the rule id, the JSON override, pydantic's
# "Value error" prefix and the entry position.
_AUTHORING_TEXT = ("learned-", "{", "Value error", "expansion entry")


class TestPlainRuleProblem:
    """Phase H live smoke item 2 (2026-09-26): the status line says the
    clinician's reason per refusal class; the validator's authoring message
    stays in the writer's record."""

    @pytest.mark.parametrize(
        ("wording", "expected"),
        [
            ("Rest; then ice", RULE_WORDING_MANY_CLAIMS),
            ("Mild knee sprain - rest advised", RULE_WORDING_MANY_CLAIMS),
            ("Rest advised. Ice applied.", RULE_WORDING_MANY_CLAIMS),
            (("a " * 1100).strip(), RULE_WORDING_TOO_LONG),
            ("   ", RULE_WORDING_BLANK),
            ("Mild​sprain", RULE_WORDING_HIDDEN_CHARACTER),
        ],
        ids=["semicolon", "dash", "two-sentences", "over-long", "blank", "hidden"],
    )
    def test_each_refused_wording_has_a_plain_reason(self, wording: str, expected: str) -> None:
        detail = learned_rule_problem(_candidate(wording=wording))
        assert detail is not None  # the validator decides ...
        plain = plain_rule_problem(wording)  # ... this only explains
        assert plain == expected
        assert not any(text in plain for text in _AUTHORING_TEXT)

    def test_the_validators_own_text_is_what_the_plain_form_replaces(self) -> None:
        detail = learned_rule_problem(_candidate(wording="Mild knee sprain - rest advised"))
        assert detail is not None
        assert "expansion entry 1" in detail and "{" in detail  # the authoring message

    def test_a_refusal_no_class_explains_gets_the_closed_fallback(self) -> None:
        # Asked about a wording the checks here accept: never the validator's text.
        assert plain_rule_problem("HVLA Cx") == RULE_WORDING_NOT_ACCEPTED

    def test_the_writers_skip_reasons_render_plain(self) -> None:
        wording = "Rest; then ice"
        detail = learned_rule_problem(_candidate(wording=wording))
        assert plain_skip_reason(f"invalid: {detail}", wording) == RULE_WORDING_MANY_CLAIMS
        assert plain_skip_reason("duplicate", "HVLA Cx") == (
            "that trigger is already in your rules file"
        )
        assert plain_skip_reason("not a learned rule", "HVLA Cx") == "not a learned rule"


# ---------------------------------------------------------------------------
# The trigger heuristic (D11) and the id.
# ---------------------------------------------------------------------------


class TestProposeRuleTrigger:
    def test_flow_2s_utterance_yields_its_tail_without_the_discourse_word(self) -> None:
        candidate = propose_rule_trigger(_FLOW_2.split())
        assert candidate is not None
        assert candidate.phrase == "put a crack into the neck"
        assert candidate.source_words == ("put", "a", "crack", "into", "the", "neck")
        assert candidate.first_in_segment is False
        assert candidate.following == ("now",)
        assert (
            refuse_learning_candidate(
                candidate.source_words,
                first_in_segment=candidate.first_in_segment,
                following=candidate.following,
            )
            is None
        )

    def test_a_short_utterance_is_the_whole_trigger_from_its_real_first_word(self) -> None:
        candidate = propose_rule_trigger(["Rest", "the", "shoulder"])
        assert candidate is not None
        assert candidate.phrase == "rest the shoulder"
        assert candidate.first_in_segment is True
        assert candidate.following == ()

    @pytest.mark.parametrize(
        "words",
        [["Rest"], ["um", "ok", "now"], [], ["...", "!!"]],
        ids=["one-token", "discourse-only", "empty", "punctuation"],
    )
    def test_fewer_than_the_minimum_yields_nothing(self, words: list[str]) -> None:
        assert LEARNED_PHRASE_MIN_TOKENS == 2
        assert propose_rule_trigger(words) is None

    def test_the_trigger_is_capped_at_the_last_six_content_tokens(self) -> None:
        words = "so today we are going to mobilise the thoracic spine gently".split()
        candidate = propose_rule_trigger(words)
        assert candidate is not None
        assert len(candidate.phrase.split()) == LEARNED_TRIGGER_MAX_TOKENS == 6
        assert candidate.phrase == "to mobilise the thoracic spine gently"
        assert candidate.first_in_segment is False

    def test_the_filter_still_refuses_a_name_in_the_tail(self) -> None:
        candidate = propose_rule_trigger("give Margaret the sheet now".split())
        assert candidate is not None
        assert refuse_learning_candidate(
            candidate.source_words,
            first_in_segment=candidate.first_in_segment,
            following=candidate.following,
        ) == "name"


class TestLearnedRuleId:
    def test_shape_prefix_and_grammar(self) -> None:
        rule_id = new_learned_rule_id(now=_AT)
        assert rule_id.startswith(LEARNED_RULE_ID_PREFIX)
        assert len(rule_id) == len(LEARNED_RULE_ID_PREFIX) + 26
        assert _ID_RE.match(rule_id)
        assert is_learned_rule_id(rule_id)
        assert not is_learned_rule_id("r-hep")

    def test_ids_sort_by_learning_time_and_never_repeat(self) -> None:
        earlier = new_learned_rule_id(now=_AT)
        later = new_learned_rule_id(now=_LATER)
        assert earlier < later
        assert len({new_learned_rule_id(now=_AT) for _ in range(200)}) == 200


# ---------------------------------------------------------------------------
# append_learned_rules — validated and duplicate-checked BEFORE the write.
# ---------------------------------------------------------------------------


class TestAppendLearnedRules:
    def test_a_first_append_creates_both_files_and_loads_as_one_rule(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        outcome = append_learned_rules([_candidate()], config_root=root, learned_at=_AT)
        [added] = outcome.added
        assert outcome.skipped == () and outcome.sidecar_error is None
        assert is_learned_rule_id(added.rule_id)
        assert (root / AUTOFILL_RULES_FILENAME).is_file()
        assert (root / LEARNED_RULES_SIDECAR_FILENAME).is_file()
        rules = _rules_by_id(root)
        assert list(rules) == [added.rule_id]
        rule = rules[added.rule_id]
        assert rule.section_key == "treatment_performed"
        assert rule.trigger_phrase == "crack into the neck"
        assert rule.expansion_texts() == ("HVLA Cx",)
        entry = load_learned_rule_entries(root)[added.rule_id]
        assert entry == LearnedRuleEntry(learned_at=_AT)
        assert entry.confirmations == 0 and entry.auto_confirmed is False
        assert entry.trigger_source == "typed_edit"
        learned = load_learned_rules(root)
        assert [r.rule_id for r in learned.recent] == [added.rule_id]
        assert learned.recent[0].typed_wording == ("HVLA Cx",)
        assert learned.recent[0].learned_at == _AT
        assert learned.by_section == (("treatment_performed", (learned.recent[0],)),)

    def test_hand_authored_rules_survive_the_whole_file_replacement(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        _write_user_rules(root, [_hand_rule()])
        [learned_id] = _learn(root)
        rules = _rules_by_id(root)
        assert set(rules) == {"r-hep", learned_id}
        assert rules["r-hep"].expansion_texts() == ("Home exercise programme reviewed.",)
        assert not is_learned_rule_id("r-hep")
        assert [r.rule_id for r in load_learned_rules(root).recent] == [learned_id]

    def test_a_trigger_already_held_is_a_duplicate_and_nothing_is_written(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        _write_user_rules(root, [_hand_rule()])
        before = (root / AUTOFILL_RULES_FILENAME).read_bytes()
        against_hand = _candidate(trigger="Home  exercise,")  # same under normalisation
        outcome = append_learned_rules([against_hand], config_root=root, learned_at=_AT)
        assert outcome.added == ()
        assert outcome.skipped == ((against_hand, "duplicate"),)
        assert (root / AUTOFILL_RULES_FILENAME).read_bytes() == before
        assert not (root / LEARNED_RULES_SIDECAR_FILENAME).exists()
        # ...against a learned rule, and within one call: one rule per trigger.
        _learn(root)
        twice = append_learned_rules(
            [_candidate(wording="Cervical HVLA"), _candidate(trigger="ice the knee"),
             _candidate(trigger="ice the knee", wording="Ice advised")],
            config_root=root,
            learned_at=_LATER,
        )
        assert [rule.trigger_phrase for rule in twice.added] == ["ice the knee"]
        assert [reason for _, reason in twice.skipped] == ["duplicate", "duplicate"]
        triggers = [content_tokens(r.trigger_phrase) for r in load_note_config(root).autofill_rules]
        assert len(triggers) == len(set(triggers)) == 3

    @pytest.mark.parametrize(
        ("candidate", "expected"),
        [
            (_candidate(wording="Rest; then ice"), "invalid:"),
            (_candidate(trigger="..."), "invalid:"),
            (_candidate(wording="aa " * 1_000), "invalid:"),
            (_candidate(wording="   "), "invalid:"),
        ],
        ids=["two-claims", "empty-trigger", "over-long", "blank"],
    )
    def test_an_invalid_candidate_never_reaches_disk(
        self, tmp_path: Path, candidate: LearnedRuleCandidate, expected: str
    ) -> None:
        root = tmp_path / "config"
        outcome = append_learned_rules([candidate], config_root=root, learned_at=_AT)
        assert outcome.added == ()
        [(skipped, reason)] = outcome.skipped
        assert skipped == candidate
        assert reason.startswith(expected)
        assert not root.exists()
        assert load_note_config(root).autofill_rules == ()  # loading never breaks

    def test_a_write_failure_is_typed_and_leaves_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "config"
        _fail_writes_to(monkeypatch, AUTOFILL_RULES_FILENAME)
        with pytest.raises(NoteConfigWriteError, match=AUTOFILL_RULES_FILENAME):
            append_learned_rules([_candidate()], config_root=root, learned_at=_AT)
        assert not (root / AUTOFILL_RULES_FILENAME).exists()
        assert not (root / LEARNED_RULES_SIDECAR_FILENAME).exists()

    def test_a_sidecar_failure_after_the_rules_write_is_returned_not_raised(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "config"
        _fail_writes_to(monkeypatch, LEARNED_RULES_SIDECAR_FILENAME)
        outcome = append_learned_rules([_candidate()], config_root=root, learned_at=_AT)
        [added] = outcome.added
        assert outcome.sidecar_error is not None
        assert LEARNED_RULES_SIDECAR_FILENAME in outcome.sidecar_error
        assert added.rule_id in _rules_by_id(root)
        assert not (root / LEARNED_RULES_SIDECAR_FILENAME).exists()
        learned = load_learned_rules(root)
        assert learned.recent == ()  # undated...
        [(_key, (listed,))] = learned.by_section  # ...but listed, and deletable
        assert listed.rule_id == added.rule_id and listed.learned_at is None
        assert listed.auto_confirmed is False

    def test_a_malformed_user_rules_file_raises_and_is_left_alone(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        root.mkdir(parents=True)
        (root / AUTOFILL_RULES_FILENAME).write_text("{not json", encoding="utf-8")
        with pytest.raises(NoteConfigInvalidError, match=re.escape(AUTOFILL_RULES_FILENAME)):
            append_learned_rules([_candidate()], config_root=root, learned_at=_AT)
        assert (root / AUTOFILL_RULES_FILENAME).read_text(encoding="utf-8") == "{not json"
        assert not (root / LEARNED_RULES_SIDECAR_FILENAME).exists()

    def test_a_learned_rule_is_a_real_rule_and_moves_the_digest(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        shipped = load_note_config(tmp_path / "shipped").config_digest()
        _learn(root)
        assert load_note_config(root).config_digest() != shipped


# ---------------------------------------------------------------------------
# replace_learned_rule_wording — one active expansion per trigger (D5).
# ---------------------------------------------------------------------------


class TestReplaceLearnedRuleWording:
    def test_a_correction_replaces_in_place_and_reloads_as_one_rule(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        [rule_id] = _learn(root)
        replaced = replace_learned_rule_wording(
            rule_id, "Cervical HVLA", config_root=root, replaced_at=_LATER
        )
        assert replaced.replaced is True and replaced.reason is None
        rules = _rules_by_id(root)
        assert list(rules) == [rule_id]
        assert rules[rule_id].trigger_phrase == "crack into the neck"
        assert rules[rule_id].expansion_texts() == ("Cervical HVLA",)
        entry = load_learned_rule_entries(root)[rule_id]
        assert entry.learned_at == _AT
        assert entry.confirmations == 0 and entry.auto_confirmed is False
        assert entry.history == (
            LearnedRuleHistoryEntry(replaced_at=_LATER, previous_expansion=("HVLA Cx",)),
        )
        [listed] = load_learned_rules(root).recent
        assert listed.typed_wording == ("Cervical HVLA",)

    def test_a_correction_demotes_an_auto_confirmed_rule(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        [rule_id] = _learn(root)
        for _ in range(LEARNED_RULE_AUTO_CONFIRM_AFTER):
            record_rule_outcomes({rule_id: "confirmed"}, config_root=root)
        assert load_learned_rule_entries(root)[rule_id].auto_confirmed is True
        replace_learned_rule_wording(rule_id, "Cx HVLA", config_root=root, replaced_at=_LATER)
        entry = load_learned_rule_entries(root)[rule_id]
        assert (entry.confirmations, entry.auto_confirmed) == (0, False)
        assert len(entry.history) == 1

    def test_only_a_learned_rule_in_the_user_file_is_replaced(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        _write_user_rules(root, [_hand_rule()])
        before = (root / AUTOFILL_RULES_FILENAME).read_bytes()
        hand = replace_learned_rule_wording("r-hep", "Rest", config_root=root, replaced_at=_AT)
        assert hand.replaced is False and hand.reason == "not a learned rule"
        unknown = replace_learned_rule_wording(
            new_learned_rule_id(now=_AT), "Rest", config_root=root, replaced_at=_AT
        )
        assert unknown.replaced is False
        assert unknown.reason == "not a learned rule in your rules file"
        assert (root / AUTOFILL_RULES_FILENAME).read_bytes() == before
        assert not (root / LEARNED_RULES_SIDECAR_FILENAME).exists()

    def test_an_invalid_wording_changes_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        [rule_id] = _learn(root)
        before = (root / AUTOFILL_RULES_FILENAME).read_bytes()
        sidecar_before = (root / LEARNED_RULES_SIDECAR_FILENAME).read_bytes()
        outcome = replace_learned_rule_wording(
            rule_id, "Rest; then ice", config_root=root, replaced_at=_LATER
        )
        assert outcome.replaced is False
        assert outcome.reason is not None and outcome.reason.startswith("invalid:")
        assert (root / AUTOFILL_RULES_FILENAME).read_bytes() == before
        assert (root / LEARNED_RULES_SIDECAR_FILENAME).read_bytes() == sidecar_before

    def test_a_rules_write_failure_keeps_the_old_wording_with_a_reset_count(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The safe ordering: the sidecar's reset lands first, so a failed
        rules write leaves the OLD wording needing its three confirmations
        again — never a NEW wording that pre-fills unconfirmed."""
        root = tmp_path / "config"
        [rule_id] = _learn(root)
        for _ in range(LEARNED_RULE_AUTO_CONFIRM_AFTER):
            record_rule_outcomes({rule_id: "confirmed"}, config_root=root)
        _fail_writes_to(monkeypatch, AUTOFILL_RULES_FILENAME)
        outcome = replace_learned_rule_wording(
            rule_id, "Cervical HVLA", config_root=root, replaced_at=_LATER
        )
        assert outcome.replaced is False
        assert outcome.rules_file_error is not None
        assert AUTOFILL_RULES_FILENAME in outcome.rules_file_error
        assert _rules_by_id(root)[rule_id].expansion_texts() == ("HVLA Cx",)
        entry = load_learned_rule_entries(root)[rule_id]
        assert (entry.confirmations, entry.auto_confirmed) == (0, False)


# ---------------------------------------------------------------------------
# record_rule_outcomes — auto-confirm at exactly three; removed demotes.
# ---------------------------------------------------------------------------


class TestRecordRuleOutcomes:
    def test_auto_confirm_at_exactly_three_unchanged_confirmations(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        [rule_id] = _learn(root)
        assert LEARNED_RULE_AUTO_CONFIRM_AFTER == 3
        for expected in (1, 2):
            report = record_rule_outcomes({rule_id: "confirmed"}, config_root=root)
            # An ordinary increment is REPORTED as an update (peer round 14
            # PR-LOW-024) though it is neither a promotion nor a demotion.
            assert report == ((), (), (rule_id,))
            entry = load_learned_rule_entries(root)[rule_id]
            assert (entry.confirmations, entry.auto_confirmed) == (expected, False)
        report = record_rule_outcomes({rule_id: "confirmed"}, config_root=root)
        assert report.auto_confirmed == (rule_id,) and report.demoted == ()
        assert report.updated == (rule_id,)
        entry = load_learned_rule_entries(root)[rule_id]
        assert (entry.confirmations, entry.auto_confirmed) == (3, True)
        # A fourth counts on but is not "newly" auto-confirmed.
        report = record_rule_outcomes({rule_id: "confirmed"}, config_root=root)
        assert report == ((), (), (rule_id,))
        assert load_learned_rule_entries(root)[rule_id].confirmations == 4
        assert load_learned_rules(root).recent[0].auto_confirmed is True

    def test_removed_demotes_to_proposing_and_never_deletes(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        [rule_id] = _learn(root)
        for _ in range(LEARNED_RULE_AUTO_CONFIRM_AFTER):
            record_rule_outcomes({rule_id: "confirmed"}, config_root=root)
        report = record_rule_outcomes({rule_id: "removed"}, config_root=root)
        assert report.demoted == (rule_id,) and report.auto_confirmed == ()
        entry = load_learned_rule_entries(root)[rule_id]
        assert (entry.confirmations, entry.auto_confirmed) == (0, False)
        assert rule_id in _rules_by_id(root)  # still a rule: it proposes again
        sidecar_before = (root / LEARNED_RULES_SIDECAR_FILENAME).stat().st_mtime_ns
        again = record_rule_outcomes({rule_id: "removed"}, config_root=root)
        assert again == ((), (), ())  # already proposing: nothing to demote...
        # ...and nothing rewritten (round 12 LOW-001).
        assert (root / LEARNED_RULES_SIDECAR_FILENAME).stat().st_mtime_ns == sidecar_before

    def test_unknown_or_hand_authored_ids_count_nothing_and_write_nothing(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        _write_user_rules(root, [_hand_rule()])
        [rule_id] = _learn(root)
        rules_before = (root / AUTOFILL_RULES_FILENAME).read_bytes()
        sidecar_before = (root / LEARNED_RULES_SIDECAR_FILENAME).read_bytes()
        report = record_rule_outcomes(
            {"r-hep": "confirmed", new_learned_rule_id(now=_AT): "confirmed"}, config_root=root
        )
        assert report == ((), (), ())
        assert (root / LEARNED_RULES_SIDECAR_FILENAME).read_bytes() == sidecar_before
        assert record_rule_outcomes({}, config_root=root) == ((), (), ())
        # Counting never touches the rules file or the digest.
        digest = load_note_config(root).config_digest()
        record_rule_outcomes({rule_id: "confirmed"}, config_root=root)
        assert (root / AUTOFILL_RULES_FILENAME).read_bytes() == rules_before
        assert load_note_config(root).config_digest() == digest

    def test_a_rule_without_a_sidecar_record_never_auto_confirms(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "config"
        _fail_writes_to(monkeypatch, LEARNED_RULES_SIDECAR_FILENAME)
        [added] = append_learned_rules([_candidate()], config_root=root, learned_at=_AT).added
        monkeypatch.undo()
        for _ in range(LEARNED_RULE_AUTO_CONFIRM_AFTER + 1):
            assert record_rule_outcomes({added.rule_id: "confirmed"}, config_root=root) == (
                (),
                (),
                (),
            )
        assert load_learned_rule_entries(root) == {}
        assert load_learned_rules(root).by_section[0][1][0].auto_confirmed is False


# ---------------------------------------------------------------------------
# delete_learned_rule / load_learned_rules — the review-later surface.
# ---------------------------------------------------------------------------


class TestDeleteLearnedRule:
    def test_a_learned_rule_is_removed_from_both_files(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        _write_user_rules(root, [_hand_rule()])
        first, second = _learn(root, _candidate(), _candidate(trigger="ice the knee"))
        assert delete_learned_rule(first, config_root=root) is True
        assert set(_rules_by_id(root)) == {"r-hep", second}
        assert set(load_learned_rule_entries(root)) == {second}
        assert [r.rule_id for r in load_learned_rules(root).recent] == [second]
        assert delete_learned_rule(first, config_root=root) is False

    def test_a_hand_authored_rule_is_never_deleted_here(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        _write_user_rules(root, [_hand_rule()])
        before = (root / AUTOFILL_RULES_FILENAME).read_bytes()
        assert delete_learned_rule("r-hep", config_root=root) is False
        assert (root / AUTOFILL_RULES_FILENAME).read_bytes() == before

    def test_a_failed_sidecar_write_is_repaired_by_the_retry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "config"
        [rule_id] = _learn(root)
        _fail_writes_to(monkeypatch, LEARNED_RULES_SIDECAR_FILENAME)
        with pytest.raises(NoteConfigWriteError, match=LEARNED_RULES_SIDECAR_FILENAME):
            delete_learned_rule(rule_id, config_root=root)
        assert rule_id not in _rules_by_id(root)  # the rules file went first
        raw = json.loads((root / LEARNED_RULES_SIDECAR_FILENAME).read_text(encoding="utf-8"))
        assert rule_id in raw["entries"]  # the orphan the retry removes
        assert load_learned_rules(root) == ((), ())  # dropped on read meanwhile
        monkeypatch.undo()
        assert delete_learned_rule(rule_id, config_root=root) is True
        assert load_learned_rule_entries(root) == {}

    def test_a_later_delete_prunes_any_orphaned_sidecar_entry(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        first, second = _learn(root, _candidate(), _candidate(trigger="ice the knee"))
        # The practitioner hand-removed the first rule from the file.
        kept = [
            rule.model_dump(mode="json")
            for rule in load_note_config(root).autofill_rules
            if rule.rule_id != first
        ]
        _write_user_rules(root, kept)
        assert delete_learned_rule(second, config_root=root) is True
        assert load_learned_rule_entries(root) == {}


class TestLoadLearnedRules:
    def test_no_user_file_means_nothing_learned_even_with_a_sidecar(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        root.mkdir(parents=True)
        payload = {"schema_version": 1, "entries": {"learned-X": {"learned_at": _AT.isoformat()}}}
        (root / LEARNED_RULES_SIDECAR_FILENAME).write_text(json.dumps(payload), encoding="utf-8")
        assert load_learned_rules(root) == ((), ())
        assert load_learned_rule_entries(tmp_path / "absent") == {}

    def test_a_malformed_sidecar_raises_naming_the_sidecar(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        _learn(root)
        (root / LEARNED_RULES_SIDECAR_FILENAME).write_text("{not json", encoding="utf-8")
        with pytest.raises(NoteConfigError, match=re.escape(LEARNED_RULES_SIDECAR_FILENAME)):
            load_learned_rules(root)
        with pytest.raises(NoteConfigError, match=re.escape(LEARNED_RULES_SIDECAR_FILENAME)):
            load_learned_rule_entries(root)
        assert len(load_note_config(root).autofill_rules) == 1  # the loader never reads it

    def test_recent_is_newest_first_and_capped(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        stamps = [datetime(2026, 9, 1 + day, tzinfo=UTC) for day in range(25)]
        for day, stamp in enumerate(stamps):
            _learn(root, _candidate(trigger=f"trigger number {day} here"), at=stamp)
        learned = load_learned_rules(root)
        assert len(learned.recent) == note_config_module.RECENTLY_LEARNED_LIMIT == 20
        dates = [rule.learned_at for rule in learned.recent]
        assert dates == sorted(stamps, reverse=True)[:20]
        assert sum(len(rules) for _, rules in learned.by_section) == 25


# ---------------------------------------------------------------------------
# C9 — typed wording never reaches a log line.
# ---------------------------------------------------------------------------


class TestTripwire:
    def test_the_new_fields_are_registered_and_renderings_are_caught(self) -> None:
        assert '"typed_wording"' in _PAYLOAD_SIGNATURES
        assert "previous_expansion=" in _PAYLOAD_SIGNATURES
        history = LearnedRuleHistoryEntry(replaced_at=_AT, previous_expansion=("HVLA Cx",))
        for rendering in (
            repr(_candidate()),
            repr(load_learned_rules.__module__),  # a module name renders nothing clinical
            repr(history),
            history.model_dump_json(),
            json.dumps(history.model_dump(mode="json")),
        ):
            if "HVLA" in rendering:
                assert any(sig in rendering for sig in _PAYLOAD_SIGNATURES), rendering
