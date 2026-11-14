"""Suggestion-repair plan Task 0.2: ``scripts/measure-suggestions.py``, the
text-level measurement of the section-suggestion stage (D2, D7; C2-C4).

The script is loaded through importlib (``test_setup_scripts.py``'s way) and
driven with ``MockLanguageModel`` doubles only — the models root is the
conftest's empty pin, so no real model is ever loaded. Every script here is
invented (or one of the synthetic 50); nothing reads a real session.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from conftest import use_channel
from scribe_desktop import note_suggest, validation
from scribe_desktop.language_model import LanguageModelError, MockLanguageModel
from scribe_desktop.note import (
    CANONICAL_SECTION_KEYS,
    GeneratedSection,
    NoteRequest,
    whole_utterance_assertion,
)
from scribe_desktop.note_config import load_note_config
from scribe_desktop.note_suggest import (
    SUGGEST_LINES_END,
    SUGGEST_LINES_HEADER,
    SuggestionInput,
    SuggestionLine,
    build_window_prompt,
    parse_suggestions,
)
from scribe_desktop.ui import models

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "measure-suggestions.py"
CONFIG = REPO / "validation" / "config"
NOW = datetime(2026, 11, 14, tzinfo=UTC)


@pytest.fixture(scope="module")
def tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("measure_suggestions", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves a string annotation through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# --- invented scripts and doubles ---------------------------------------------------------


def _script_data(
    lines: list[tuple[str, str]],
    facts: tuple[dict[str, Any], ...] = (),
    *,
    encounter_id: str = "syn-901",
    synthetic: bool = True,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "schema_version": 1,
        "encounter_id": encounter_id,
        "appointment_type": "initial",
        "axes": ["small_talk"],
        "lines": [{"role": role, "text": text} for role, text in lines],
        "facts": list(facts),
    }
    if synthetic:
        roles = sorted({role for role, _text in lines})
        data["conditions"] = {"voice_slots": {role: slot for slot, role in enumerate(roles)}}
    return data


def _script(
    lines: list[tuple[str, str]], facts: tuple[dict[str, Any], ...] = (), **kwargs: Any
) -> validation.EncounterScript:
    return validation.EncounterScript.model_validate(_script_data(lines, facts, **kwargs))


def _write_set(folder: Path, *scripts: dict[str, Any]) -> Path:
    folder.mkdir(parents=True)
    for data in scripts:
        (folder / f"{data['encounter_id']}.json").write_text(json.dumps(data), encoding="utf-8")
    return folder


class _QuoteClinician:
    """A fake note provider: every clinician line quoted into the presenting
    complaint, every other line left out (so it is asked)."""

    provider_name = "quote-clinician"

    def generate_sections(self, request: NoteRequest) -> tuple[GeneratedSection, ...]:
        assertions = []
        for utterance in request.transcript_utterances:
            if utterance.speaker != "clinician":
                continue
            assertion = whole_utterance_assertion(
                f"q{utterance.segment_index:04d}",
                "presenting_complaint",
                segment_index=utterance.segment_index,
                speaker=utterance.speaker,
                words=utterance.transcript_words,
            )
            if assertion is not None:
                assertions.append(assertion)
        if not assertions:
            return ()
        return (
            GeneratedSection(section_key="presenting_complaint", note_assertions=tuple(assertions)),
        )


def _inputs(tool: ModuleType, *, quote_clinician: bool = True) -> validation.HarnessInputs:
    inputs = tool.harness_inputs(load_note_config(CONFIG))
    if quote_clinician:
        inputs = replace(inputs, note_provider_factory=lambda config: _QuoteClinician())
    return inputs


_ASKED_ROW = re.compile(r"^(\d+)\? ", re.MULTILINE)


def _answering(word: str) -> Callable[[str, str], str]:
    """A responder answering every asked number of a window with ``word``."""

    def respond(system_text: str, user_text: str) -> str:
        return "\n".join(f"{number} {word}" for number in _ASKED_ROW.findall(user_text))

    return respond


def _echoing(system_text: str, user_text: str) -> str:
    """A responder echoing the window's asked prompt rows back."""
    return "\n".join(row for row in user_text.split("\n") if _ASKED_ROW.match(row))


class _RowLimitedModel(MockLanguageModel):
    """A window text with more than ``rows`` numbered rows overflows any
    budget; every other text counts one token."""

    def __init__(self, rows: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._rows = rows

    def count_tokens(self, text: str) -> int:
        parts = text.split("\n")
        if parts[0] == SUGGEST_LINES_HEADER and SUGGEST_LINES_END in parts:
            return 1_000_000 if parts.index(SUGGEST_LINES_END) - 1 > self._rows else 1
        return 1


class _CharacterModel(MockLanguageModel):
    """One token per character: the longest line is the costliest."""

    def count_tokens(self, text: str) -> int:
        return len(text)


def _measure(
    tool: ModuleType,
    script: validation.EncounterScript,
    model: MockLanguageModel,
    *,
    verbose: bool = False,
) -> Any:
    return tool.measure_script(
        script, _inputs(tool), tool.RecordingModel(model), NOW, verbose=verbose
    )


# --- the shape classifier ------------------------------------------------------------------


def _unless_parsed(line: str, number: int, shape: str) -> str:
    """The shape a tier A variant gets under the SHIPPED parser: valid when
    the parser of the stage under measurement reads it, else ``shape``."""
    parsed = parse_suggestions(line, (number,))
    if parsed is not None and number in parsed:
        return "valid_key" if parsed[number] is not None else "valid_none"
    return shape


class TestClassifier:
    @pytest.mark.parametrize(
        ("line", "shape"),
        [
            ("3 consent", "valid_key"),
            ("3. history_presenting_complaint", "valid_key"),
            ("3 none", "valid_none"),
            ("3 knee_pain", "unknown_key"),
            ("3 Pain", "unknown_key"),
            ("3 consent because the patient agreed", "extra_words"),
            ("3 none of these", "extra_words"),
            ("3", "not_answer"),
            ("3 the knee hurts", "not_answer"),
        ],
    )
    def test_one_case_per_shape(self, tool: ModuleType, line: str, shape: str) -> None:
        assert tool.classify_line(line, {3: 7}) == (3, shape)

    @pytest.mark.parametrize(
        ("line", "shape"),
        [
            ("3? consent", "number_question"),
            ("3? none", "number_question"),
            ("3? Consent.", "number_question"),
            ("3 Consent", "case_or_punctuation"),
            ("3 consent.", "case_or_punctuation"),
            ("3 NONE", "case_or_punctuation"),
        ],
    )
    def test_the_tier_a_variants(self, tool: ModuleType, line: str, shape: str) -> None:
        assert tool.classify_line(line, {3: 7}) == (3, _unless_parsed(line, 3, shape))

    def test_every_shape_is_reported(self, tool: ModuleType) -> None:
        assert [shape for shape, _label in tool.SHAPES] == [
            "valid_key",
            "valid_none",
            "number_question",
            "unknown_key",
            "case_or_punctuation",
            "extra_words",
            "not_answer",
        ]

    def test_an_echo_of_each_prompt_line_shape_is_no_answer(self, tool: ModuleType) -> None:
        lines = (
            SuggestionLine(0, "clinician", True, "objective_examination", "The knee is tender."),
            SuggestionLine(1, "other", False, None, "It hurts when I walk."),
        )
        text, asked = build_window_prompt(lines)
        rows = text.split("\n")
        context_row, asked_row = rows[1], rows[2]
        assert asked == {2: 1}
        assert tool.classify_line(asked_row, asked) == (2, "not_answer")
        # The context shape carries a number the window did not ask.
        assert tool.classify_line(context_row, asked) == (None, tool.UNATTRIBUTABLE)
        # The context shape with an asked number is still no answer.
        echoed = "2 other [placed: consent] It hurts when I walk."
        assert tool.classify_line(echoed, asked) == (2, "not_answer")

    @pytest.mark.parametrize(
        "line", ["consent", "Line two: consent", "- 3 consent", "7 consent", "12345 consent"]
    )
    def test_malformed_and_out_of_window_lines_are_unattributable(
        self, tool: ModuleType, line: str
    ) -> None:
        assert tool.classify_line(line, {3: 7}) == (None, tool.UNATTRIBUTABLE)


# --- the input, the stage and the facts ---------------------------------------------------


class TestTheInput:
    @pytest.mark.parametrize("quote_clinician", [True, False])
    def test_the_input_equals_suggestion_pass_s(
        self, tool: ModuleType, quote_clinician: bool
    ) -> None:
        """The tool's input (the plan's recipe) is the one the harness's
        ``suggestion_pass`` hands the stage, on one of the synthetic 50."""
        script = validation.load_script(REPO / "validation" / "scripts" / "syn-01.json")
        inputs = _inputs(tool, quote_clinician=quote_clinician)
        document, draft, built = tool.build_input(script, inputs, NOW)
        captured: list[SuggestionInput] = []

        def stage(
            suggestion_input: SuggestionInput,
            /,
            *,
            abort: Callable[[], bool] | None = None,
            yield_to: Callable[[], None] | None = None,
        ) -> models.SuggestionStageOutcome:
            captured.append(suggestion_input)
            return models.SuggestionStageOutcome(None, "not run")

        validation.suggestion_pass(document, draft, "clinician", inputs, stage)
        assert captured == ([built] if built.lines_asked else [])
        if quote_clinician:
            assert built.lines_asked == 2  # the two patient lines

    def test_the_measurement_runs_the_shipped_stage_once(self, tool: ModuleType) -> None:
        script = _script(
            [("clinician", "The knee is tender to touch."), ("patient", "It aches a lot.")]
        )
        model = MockLanguageModel(responder=_answering("none"))
        tally = _measure(tool, script, model)
        assert len(model.calls) == 1
        system_text, _user_text, max_tokens = model.calls[0]
        assert system_text == note_suggest.SUGGEST_INSTRUCTION
        assert max_tokens == note_suggest.answer_token_budget(1)
        assert tally.counts["lines_asked"] == 1
        assert tally.counts["model_calls"] == 1
        assert tally.prompt_version == note_suggest.SUGGEST_PROMPT_VERSION
        assert tally.model_id == MockLanguageModel.model_id


class TestTheLostFacts:
    LINES = [
        ("clinician", "On examination the knee is tender to touch."),
        ("patient", "It aches mostly in the evening."),
    ]
    FACT = ({"kind": "present", "tokens": ["aches"], "line": 1, "material": True},)

    @pytest.mark.parametrize(
        ("responder", "reading", "shape", "still_silent"),
        [
            (_answering("history_presenting_complaint"), "key", "valid_key", 0),
            (_answering("none"), "none", "valid_none", 1),
            (_answering("knee_pain"), "unread", "unknown_key", 1),
            # Round 8 MED-001: a line that answers nothing is no answer.
            (_answering("Not sure"), "no_answer", "not_answer", 1),
            (_echoing, "no_answer", "not_answer", 1),
            (lambda system_text, user_text: "", "no_answer", None, 1),
        ],
    )
    def test_how_a_silently_lost_fact_s_line_was_read(
        self,
        tool: ModuleType,
        responder: Callable[[str, str], str],
        reading: str,
        shape: str | None,
        still_silent: int,
    ) -> None:
        model = MockLanguageModel(responder=responder)
        tally = _measure(tool, _script(self.LINES, self.FACT), model)
        assert tally.counts["lost_lines"] == 1
        assert dict(tally.readings) == {reading: 1}
        assert tally.counts["silent_before"] == 1
        assert tally.counts["silent_before_encounters"] == 1
        assert tally.counts["silent_after"] == still_silent
        assert tally.still_silent == (["syn-901"] if still_silent else [])
        assert tally.counts["accepted_u"] == (1 if reading == "key" else 0)
        assert tally.counts["accepted_w"] == 0
        assert tally.counts["wrongly_present"] == 0
        if shape is None:
            assert sum(tally.shapes.values()) == 0
        else:
            assert dict(tally.shapes) == {(shape, "patient"): 1}
        assert tally.counts["no_answer_numbers"] == (1 if reading == "no_answer" else 0)
        assert tally.counts["cut_at_budget"] == 0
        assert tally.counts["refused"] == 0
        # The reply's question is in the note (the provider quoted it).
        assert tally.counts["lost_replies"] == 1
        assert tally.counts["replies_question_absent"] == 0

    @pytest.mark.parametrize(
        ("completion", "cut", "unattributable"),
        [
            # 30 words against a budget of 24 (one asked line), no answer.
            (" ".join(["word"] * 30), 1, 1),
            # As long, but the window's last asked number is answered.
            (" ".join(["word"] * 30) + "\n2 none", 0, 1),
            # Short, unanswered: not cut.
            ("word", 0, 1),
        ],
    )
    def test_cut_at_budget_is_inferred_from_length_and_the_last_number(
        self, tool: ModuleType, completion: str, cut: int, unattributable: int
    ) -> None:
        """D2's inference: the completion's token count reached the budget
        less one AND the last asked number has no answer line."""
        model = MockLanguageModel(responder=lambda system_text, user_text: completion)
        tally = _measure(tool, _script(self.LINES, self.FACT), model)
        assert model.calls[0][2] == note_suggest.answer_token_budget(1) == 24
        assert tally.counts["cut_at_budget"] == cut
        assert tally.counts["unattributable"] == unattributable

    def test_a_failed_call_leaves_every_asked_number_unanswered(self, tool: ModuleType) -> None:
        """Codex round 10 PR-LOW-013: a call that raises answered none of
        the numbers it asked; the failed window is the stage's own count."""
        model = MockLanguageModel(fail_with=LanguageModelError("generation failed"))
        tally = _measure(tool, _script(self.LINES, self.FACT), model)
        assert len(model.calls) == 1
        assert tally.counts["model_calls"] == 1
        assert tally.counts["windows_failed"] == 1
        assert tally.counts["not_assessed"] == 1
        assert tally.counts["no_answer_numbers"] == 1
        assert dict(tally.readings) == {"no_answer": 1}
        assert sum(tally.shapes.values()) == 0
        assert tally.counts["refused"] == 0
        assert tally.counts["silent_after"] == 1

    def test_a_refused_completion_leaves_its_answers_unread(self, tool: ModuleType) -> None:
        """A list marker echoed refuses the whole completion: its answer
        line is counted by shape, but read as nothing."""
        model = MockLanguageModel(
            responder=lambda system_text, user_text: f"{SUGGEST_LINES_END}\n2 consent"
        )
        tally = _measure(tool, _script(self.LINES, self.FACT), model)
        assert tally.counts["refused"] == 1
        assert tally.counts["windows_failed"] == 1
        assert tally.counts["not_assessed"] == 1
        assert tally.counts["unattributable"] == 1  # the marker line
        assert dict(tally.shapes) == {("valid_key", "patient"): 1}
        assert dict(tally.readings) == {"unread": 1}
        assert tally.counts["accepted_u"] == 0
        assert tally.counts["silent_after"] == 1

    def test_counts_are_split_by_speaker_and_role(self, tool: ModuleType) -> None:
        script = _script(
            [
                ("clinician", "The knee is tender to touch."),
                ("patient", "It aches a lot."),
                ("clinician", "We also measured the range."),
                ("carer", "She sleeps badly."),
                ("next_patient", "I came for my shoulder."),
            ]
        )
        # Every clinician line is quoted, so the three others are asked.
        tally = _measure(tool, script, MockLanguageModel(responder=_answering("none")))
        assert dict(tally.shapes) == {
            ("valid_none", "patient"): 1,
            ("valid_none", "other"): 1,
            ("valid_none", "next_patient"): 1,
        }

    def test_an_unattributable_line_is_counted_once_and_in_no_column(
        self, tool: ModuleType
    ) -> None:
        script = _script(
            [("clinician", "The knee is tender to touch."), ("patient", "It aches a lot.")]
        )
        model = MockLanguageModel(
            responder=lambda system_text, user_text: "Answers:\n9 consent\n2 none"
        )
        tally = _measure(tool, script, model)
        assert tally.counts["unattributable"] == 2
        assert dict(tally.shapes) == {("valid_none", "patient"): 1}


class TestFitReductions:
    def test_a_context_only_fitted_prefix_is_a_reduction(self, tool: ModuleType) -> None:
        """Four lines overflow; the halved prefix holds only the two placed
        clinician lines, so no call is made for it; the two asked lines come
        in the next window: one reduction, one call."""
        script = _script(
            [
                ("clinician", "The knee is tender to touch."),
                ("clinician", "We measured the range of movement."),
                ("patient", "It aches a lot."),
                ("patient", "Mostly after work."),
            ]
        )
        model = _RowLimitedModel(2, responder=_answering("none"))
        tally = _measure(tool, script, model)
        assert tally.counts["fit_reductions"] == 1
        assert tally.counts["model_calls"] == 1
        assert len(model.calls) == 1
        assert tally.counts["not_assessed"] == 0

    def test_repeated_reductions_in_one_encounter_are_all_counted(
        self, tool: ModuleType
    ) -> None:
        """Only one-line windows fit: 4 -> 2 -> 1 (context only, no call),
        then 3 -> 1, then 2 -> 1, then 1 — four reductions, three calls."""
        script = _script(
            [
                ("clinician", "The knee is tender to touch."),
                ("patient", "It aches a lot."),
                ("patient", "Mostly after work."),
                ("patient", "Sometimes at the weekend."),
            ]
        )
        model = _RowLimitedModel(1, responder=_answering("none"))
        tally = _measure(tool, script, model)
        assert tally.counts["fit_reductions"] == 4
        assert tally.counts["model_calls"] == 3
        assert tally.counts["lines_asked"] == 3
        assert tally.counts["not_assessed"] == 0
        assert dict(tally.shapes) == {("valid_none", "patient"): 3}

    def test_no_reduction_when_every_window_fits(self, tool: ModuleType) -> None:
        script = _script(
            [("clinician", "The knee is tender to touch."), ("patient", "It aches a lot.")]
        )
        tally = _measure(tool, script, MockLanguageModel(responder=_answering("none")))
        assert tally.counts["fit_reductions"] == 0


# --- the answer budget ---------------------------------------------------------------------


class TestTheBudgetEvidence:
    def test_l_is_taken_by_count_for_each_choice(self, tool: ModuleType) -> None:
        """One token per character: the longest key (29 characters) at a
        two-digit number, with every separator and mark the choice admits."""
        evidence = tool.budget_evidence(_CharacterModel())
        longest = {choices: size for choices, (size, _line) in evidence.longest.items()}
        assert longest[frozenset()] == 34  # "40) precautions_contraindications\n"
        assert longest[frozenset({"question"})] == 35
        assert longest[frozenset({"case"})] == 34
        assert longest[frozenset({"stop"})] == 35
        assert longest[tool.ALL_CHOICES] == 36
        assert len(evidence.plain) == len(CANONICAL_SECTION_KEYS) + 1
        assert [row.asked for row in evidence.rows] == list(range(1, 41))
        last = evidence.rows[-1]
        assert (last.times_longest, last.measured, last.budget) == (
            1440,
            1440,
            note_suggest.answer_token_budget(40),
        )
        report = "\n".join(tool.render_budget(evidence))
        assert f"Largest shortfall: {1440 - note_suggest.answer_token_budget(40)} tokens" in report

    def test_every_form_the_parser_may_admit_is_bounded(self, tool: ModuleType) -> None:
        assert len(tool.FORMS) == 2 * 5 * 3 * 2
        assert tool.answer_line(40, "consent", ("?", ")", "capital", ".")) == "40?) Consent.\n"
        assert tool.form_needs(("", "-", "lower", "")) == frozenset()

    def test_a_measured_answer_over_n_times_l_becomes_the_bound(self, tool: ModuleType) -> None:
        row = tool.BudgetRow(asked=2, times_longest=10, measured=12, budget=32)
        assert row.bound == 12


# --- the command line ----------------------------------------------------------------------


class TestTheCommandLine:
    LINES = [
        ("clinician", "On examination the knee is tender to touch."),
        ("patient", "Zebra crossings remind me of piano lessons."),
    ]

    def _run(
        self,
        tool: ModuleType,
        tmp_path: Path,
        model: MockLanguageModel,
        *extra: str,
        synthetic: bool = True,
    ) -> int:
        folder = _write_set(
            tmp_path / "set", _script_data(self.LINES, synthetic=synthetic)
        )
        result: int = tool.main(
            [str(folder), "--config", str(CONFIG), *extra], model_factory=lambda: model
        )
        return result

    def test_a_script_without_synthetic_conditions_refuses_the_set(
        self, tool: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        use_channel(monkeypatch, "dev")
        built: list[bool] = []

        def factory() -> MockLanguageModel:
            built.append(True)
            return MockLanguageModel()

        folder = _write_set(
            tmp_path / "set",
            _script_data(self.LINES, encounter_id="syn-901"),
            _script_data(self.LINES, encounter_id="syn-902", synthetic=False),
        )
        status = tool.main([str(folder), "--config", str(CONFIG)], model_factory=factory)
        out = capsys.readouterr().out
        assert status == 2
        assert "[refused] syn-902 is not a synthetic encounter" in out
        assert "Zebra" not in out and "knee" not in out
        assert built == []

    def test_the_production_channel_is_refused_before_any_model(
        self, tool: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        built: list[bool] = []

        def factory() -> MockLanguageModel:
            built.append(True)
            return MockLanguageModel()

        folder = _write_set(tmp_path / "set", _script_data(self.LINES))
        status = tool.main([str(folder), "--config", str(CONFIG)], model_factory=factory)
        assert status == 2
        assert "developer build" in capsys.readouterr().out
        assert built == []

    def test_the_app_s_own_config_folder_is_refused_before_any_model(
        self,
        tool: ModuleType,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        use_channel(monkeypatch, "dev")
        monkeypatch.setattr(
            validation, "_own_config_folders", lambda: {validation._normalised(CONFIG)}
        )
        built: list[bool] = []

        def factory() -> MockLanguageModel:
            built.append(True)
            return MockLanguageModel()

        folder = _write_set(tmp_path / "set", _script_data(self.LINES))
        status = tool.main([str(folder), "--config", str(CONFIG)], model_factory=factory)
        assert status == 2
        assert "is the app's own config folder" in capsys.readouterr().out
        assert built == []

    def test_a_source_root_without_the_package_is_refused(
        self, tool: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        model = MockLanguageModel()
        assert self._run(tool, tmp_path, model, "--source-root", str(tmp_path)) == 2
        assert "holds no scribe_desktop package" in capsys.readouterr().out

    @pytest.mark.parametrize("verbose", [False, True])
    def test_the_report_holds_no_line_or_completion_text_unless_verbose(
        self,
        tool: ModuleType,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        verbose: bool,
    ) -> None:
        use_channel(monkeypatch, "dev")
        model = MockLanguageModel(responder=_answering("zebramarker"))
        status = self._run(tool, tmp_path, model, *(["--verbose"] if verbose else []))
        out = capsys.readouterr().out
        assert status == 0
        assert model.calls, "the stage asked the model nothing; the test would be vacuous"
        assert "## set" in out and "## Answer budget" in out
        for text in ("Zebra", "piano", "tender", "knee"):
            assert text not in out
        assert ("zebramarker" in out) is verbose


class TestTiming:
    def test_the_window_holds_forty_asked_lines_and_its_identity(
        self, tool: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        scripts = [
            _script(
                [
                    ("clinician", f"Check number {index} of the knee."),
                    ("patient", f"It aches on day {index}."),
                    ("patient", f"Less so on evening {index}."),
                ],
                encounter_id=f"syn-{index:03d}",
            )
            for index in range(1, 26)
        ]
        inputs = _inputs(tool)
        window = tool.timing_window(scripts, inputs, NOW)
        assert window is not None
        assert sum(1 for line in window if line.asked) == tool.TIMING_ASKED_LINES
        assert len(window) == 60  # 20 scripts: one placed line and two asked each
        assert [line.segment_index for line in window] == list(range(60))
        assert window[-1].asked
        digest = tool.window_digest(window)
        assert tool.window_digest(tool.timing_window(scripts, inputs, NOW)) == digest
        relabelled = tuple(replace(line, speaker="someone") for line in window)
        assert tool.window_digest(relabelled) == digest  # text and placement only

        model = MockLanguageModel(responder=_answering("none"))
        assert tool.run_timing(window, model, verbose=False) == 0
        out = capsys.readouterr().out
        assert f"Module: {note_suggest.__file__}" in out
        assert f"Stage version: {note_suggest.SUGGEST_PROMPT_VERSION}" in out
        assert f"Input SHA-256: {digest}" in out
        assert "Window: 40 asked lines, 60 lines in all" in out
        assert len(model.calls) == 1
        assert "aches" not in out

    def test_too_few_asked_lines_is_a_refusal_before_any_model(
        self,
        tool: ModuleType,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        use_channel(monkeypatch, "dev")
        built: list[bool] = []

        def factory() -> MockLanguageModel:
            built.append(True)
            return MockLanguageModel()

        folder = _write_set(tmp_path / "set", _script_data(TestTheCommandLine.LINES))
        status = tool.main(
            [str(folder), "--config", str(CONFIG), "--timing"], model_factory=factory
        )
        assert status == 2
        assert "fewer than 40 asked lines" in capsys.readouterr().out
        assert built == []


class TestCustody:
    def test_the_script_writes_no_file_and_calls_no_logger(self) -> None:
        """C2, a text scan of the script (not a proof)."""
        source = SCRIPT.read_text(encoding="utf-8")
        for needle in ("logging", "getLogger", "open(", ".write_text(", ".write_bytes("):
            assert needle not in source, needle

    def test_the_model_call_is_outside_the_package(self) -> None:
        """C4: the recorder lives in ``scripts/``, outside the package the
        call-site pin scans."""
        assert SCRIPT.parent.name == "scripts"
        assert "scribe_desktop" not in SCRIPT.parts
