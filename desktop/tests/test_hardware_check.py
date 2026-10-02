"""Installation plan Task 2.5 (D11): the hardware check's prose-stage timing
and the verdict for both whisper ``medium`` and the prose stage.

The prose stage is the REAL ``models.build_prose_stage`` over
``MockLanguageModel`` — no test loads a real model (C6) — with the model's
presence and the clocks injected. The panel lines are pinned."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from scribe_desktop import benchmark
from scribe_desktop.benchmark import (
    PROSE_MARGIN_S,
    PROSE_REQUIRED_S,
    BenchmarkResult,
    ProseBenchmark,
    classify_prose,
    hardware_verdict,
    prose_report,
    threshold_report,
)
from scribe_desktop.language_model import (
    LanguageModelError,
    MockLanguageModel,
    echo_prompt_lines,
)
from scribe_desktop.ui import hardware_check, models
from scribe_desktop.ui.hardware_check import (
    PROSE_BENCHMARK_LINES,
    RESTART_ADVICE,
    prose_benchmark_note,
    run_prose_benchmark,
)

_LOAD_FAILED = (
    "the language model could not be loaded (digest mismatch; "
    "restart the app after fixing this)"
)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _clock(*values: float) -> Any:
    remaining = list(values)
    return lambda: remaining.pop(0)


def _medium(rtf: float) -> BenchmarkResult:
    return BenchmarkResult("medium", 50.0, 2.0, rtf * 50.0, rtf, 100 * 2**20, 120)


def _prose(seconds_per_section: float) -> ProseBenchmark:
    return ProseBenchmark(
        sections=3,
        rendered=3,
        load_seconds=6.9,
        model_seconds=3 * seconds_per_section,
        wall_seconds=3 * seconds_per_section + 0.3,
        cpu_seconds=30.0,
    )


def _cache() -> Any:
    """A fresh language-model cache: no test touches the process's one."""
    return models._LanguageModelCache()


class _TooLong(MockLanguageModel):
    """Every section's lines overflow the model's window: refused before
    any call."""

    def count_tokens(self, text: str) -> int:
        return 10**9


# --- the runner -------------------------------------------------------------------------


class TestRunProseBenchmark:
    def test_absent_model_is_skipped_with_the_named_line(self) -> None:
        got = run_prose_benchmark(
            available=lambda: False, model_factory=lambda: pytest.fail("loaded"), cache=_cache()
        )
        assert got == ProseBenchmark(skipped=models.language_model_absent_reason())
        assert prose_report(got) == [
            f"Prose stage: not timed - {models.language_model_absent_reason()}"
        ]

    def test_present_model_is_timed_on_the_fixed_lines_only(self) -> None:
        mock = MockLanguageModel()
        cache = _cache()
        got = run_prose_benchmark(
            available=lambda: True,
            model_factory=lambda: mock,
            cache=cache,
            # load start, load end, stage start, stage end (round 14 LOW-002:
            # the load is taken before the stage is clocked)
            wall_clock=_clock(10.0, 12.5, 13.0, 20.0),
            cpu_clock=_clock(1.0, 4.0, 5.0, 8.0),
        )
        assert got.skipped is None and not got.preloaded
        assert (got.sections, got.rendered) == (3, 3)
        assert got.load_seconds == pytest.approx(2.5)
        # Round 13 LOW-001: the sections' wall and CPU exclude the load.
        assert got.wall_seconds == pytest.approx(7.0)
        assert got.cpu_seconds == pytest.approx(3.0)
        assert got.model_seconds >= 0.0
        # One call per section, and the model saw only the fixed lines.
        assert len(mock.calls) == len(PROSE_BENCHMARK_LINES)
        prompts = "\n".join(user for _system, user, _tokens in mock.calls)
        for _key, lines in PROSE_BENCHMARK_LINES:
            for line in lines:
                assert line in prompts
        # Round 13 MED-001: the model stays in the ONE cache it was given.
        assert cache.get(lambda: pytest.fail("loaded twice")) is mock

    def test_a_resident_model_is_used_and_no_load_is_timed(self) -> None:
        # Round 13 MED-001: never a second copy beside the Note tab's.
        mock = MockLanguageModel()
        cache = _cache()
        cache.get(lambda: mock)
        got = run_prose_benchmark(
            available=lambda: True, model_factory=lambda: pytest.fail("loaded"), cache=cache
        )
        assert got.skipped is None and got.preloaded and got.load_seconds == 0.0
        assert len(mock.calls) == len(PROSE_BENCHMARK_LINES)
        assert prose_report(got)[0].startswith(
            "Prose stage (Narrative style): 3 of 3 sections, model already loaded; sections "
        )

    def test_the_default_cache_is_the_note_tabs(self) -> None:
        defaults = run_prose_benchmark.__kwdefaults__
        assert defaults is not None
        assert defaults["cache"] is models._LANGUAGE_MODEL_CACHE

    def test_the_result_is_numbers_only(self) -> None:
        got = run_prose_benchmark(
            available=lambda: True, model_factory=MockLanguageModel, cache=_cache()
        )
        for name, value in vars(got).items():
            assert value is None or isinstance(value, int | float), name

    def test_a_load_failure_is_skipped_with_its_reason(self) -> None:
        def broken() -> Any:
            raise LanguageModelError("digest mismatch")

        cache = _cache()
        got = run_prose_benchmark(available=lambda: True, model_factory=broken, cache=cache)
        # Round 14 LOW-001: the cache now remembers it for the Note tab too,
        # so the line says to restart.
        assert got == ProseBenchmark(skipped=_LOAD_FAILED)
        with pytest.raises(LanguageModelError, match=RESTART_ADVICE):
            cache.get(lambda: pytest.fail("reloaded"))

    def test_a_load_failure_the_cache_remembers_is_the_same_line(self) -> None:
        # Round 14 LOW-001: whichever of the Note tab and the check tried
        # first, one line, and never the Note tab's "this note" wording.
        cache = _cache()

        def broken() -> Any:
            raise LanguageModelError("digest mismatch")

        with pytest.raises(LanguageModelError):
            cache.get(broken)
        got = run_prose_benchmark(
            available=lambda: True, model_factory=lambda: pytest.fail("reloaded"), cache=cache
        )
        assert got == ProseBenchmark(skipped=_LOAD_FAILED)
        assert got.skipped is not None and "this note" not in got.skipped

    @pytest.mark.parametrize("failing", [1, 3])
    def test_a_failed_model_call_is_never_a_verdict(self, failing: int) -> None:
        # Round 13 MED-002: a failed call's time is only the time to fail.
        calls: list[str] = []

        def responder(system_text: str, user_text: str) -> str:
            calls.append(user_text)
            if len(calls) <= failing:
                raise LanguageModelError("decode failed")
            return echo_prompt_lines(system_text, user_text)

        got = run_prose_benchmark(
            available=lambda: True,
            model_factory=lambda: MockLanguageModel(responder=responder),
            cache=_cache(),
        )
        assert got == ProseBenchmark(
            skipped=f"the language model failed on {failing} of 3 sections"
        )
        assert hardware_verdict([_medium(0.5)], got).endswith("prose stage not timed")

    def test_nothing_rendered_is_never_a_verdict(self) -> None:
        got = run_prose_benchmark(available=lambda: True, model_factory=_TooLong, cache=_cache())
        assert got == ProseBenchmark(skipped="no section could be given to the language model")

    def test_the_default_seams_are_the_real_ones(self) -> None:
        defaults = run_prose_benchmark.__kwdefaults__
        assert defaults is not None
        assert defaults["available"] is models.language_model_available
        assert defaults["model_factory"] is hardware_check.LocalLanguageModel


def test_the_lines_are_the_whisper_benchmarks_non_clinical_script() -> None:
    lines = [line for _key, section in PROSE_BENCHMARK_LINES for line in section]
    assert len(lines) == 6
    for line in lines:
        assert line in benchmark.BENCHMARK_TEXT, line
    note = prose_benchmark_note()
    assert [s.section_key for s in note.note_sections] == [k for k, _ in PROSE_BENCHMARK_LINES]
    assert note.style == "narrative"
    assert models.sections_to_render(note) == {k for k, _ in PROSE_BENCHMARK_LINES}


# --- the verdict and the lines ------------------------------------------------------------


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0.0, "ok"),
        (PROSE_MARGIN_S, "ok"),
        (PROSE_MARGIN_S + 0.01, "warning"),
        (PROSE_REQUIRED_S - 0.01, "warning"),
        (PROSE_REQUIRED_S, "fail"),
    ],
)
def test_classify_prose_boundaries(seconds: float, expected: str) -> None:
    assert classify_prose(seconds) == expected


def test_the_prose_bar_is_the_recorded_interpretation() -> None:
    assert (PROSE_MARGIN_S, PROSE_REQUIRED_S) == (5.0, 10.0)
    with pytest.raises(ValueError):
        classify_prose(-1.0)


def test_per_section_figures_and_none_rendered() -> None:
    got = _prose(4.0)
    assert got.seconds_per_section == pytest.approx(4.0)
    assert got.cpu_per_section == pytest.approx(10.0)
    assert ProseBenchmark(sections=3).seconds_per_section == 0.0


class TestReportLines:
    def test_an_ok_stage(self) -> None:
        assert prose_report(_prose(4.0)) == [
            "Prose stage (Narrative style): 3 of 3 sections, load 6.9 s; sections 12.3 s wall, "
            "30.0 s CPU; 4.0 s wall and 10.0 s CPU per section  OK"
        ]

    def test_a_stage_without_margin(self) -> None:
        lines = prose_report(_prose(7.0))
        assert lines[0].endswith("  WARNING")
        assert lines[1:] == [
            "NOTE: the prose styles take 7.0 s per section (> 5 s) on this machine; "
            "a long note waits longer for them."
        ]

    def test_a_slow_stage(self) -> None:
        lines = prose_report(_prose(12.0))
        assert lines[0].endswith("  FAIL")
        assert lines[1:] == [
            "WARNING: the prose styles take 12.0 s per section (>= 10 s) on this machine. "
            "They stay local; the Clean clinical style does not use the language model."
        ]

    def test_the_verdict_for_both(self) -> None:
        assert hardware_verdict([_medium(0.5)], _prose(4.0)) == (
            "Hardware check: whisper medium RTF 0.50 OK; prose stage 4.0 s per section OK"
        )
        assert hardware_verdict([_medium(1.27)], ProseBenchmark(skipped="x")) == (
            "Hardware check: whisper medium RTF 1.27 FAIL; prose stage not timed"
        )
        small = BenchmarkResult("small", 50.0, 1.0, 10.0, 0.2, 1, 1)
        assert hardware_verdict([small], _prose(12.0)) == (
            "Hardware check: whisper medium not measured (not installed); "
            "prose stage 12.0 s per section FAIL"
        )

    def test_threshold_report_appends_the_prose_lines_and_the_verdict(self) -> None:
        whisper_only = threshold_report([_medium(0.5)])
        both = threshold_report([_medium(0.5)], _prose(4.0))
        assert both[: len(whisper_only)] == whisper_only
        assert both[len(whisper_only) :] == [
            *prose_report(_prose(4.0)),
            hardware_verdict([_medium(0.5)], _prose(4.0)),
        ]
        assert not any("Prose stage" in line for line in whisper_only)


# --- the Microphone tab -----------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _screen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> Any:
    from scribe_desktop.ui.microphone import MicrophoneScreen
    from test_ui_screens import FakeBackend, FakeController

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))  # the model report's stats (C6)
    return MicrophoneScreen(FakeController(), FakeBackend(), profile_root=tmp_path, **kwargs)


def _run(qapp: Any, screen: Any) -> None:
    from test_ui_screens import _process_until

    screen.on_run_benchmark()
    assert _process_until(qapp, lambda: screen.benchmark_button.isEnabled())


class TestMicrophonePanel:
    def test_the_panel_shows_both_and_warns_of_a_slow_prose_stage(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.ui.microphone import PROSE_SLOW_WARNING

        screen = _screen(
            tmp_path,
            monkeypatch,
            benchmark_runner=lambda: [_medium(0.5)],
            prose_runner=lambda: _prose(12.0),
        )
        _run(qapp, screen)
        assert screen.benchmark_output.toPlainText().split("\n") == threshold_report(
            [_medium(0.5)], _prose(12.0)
        )
        assert screen.benchmark_warning_label.isVisibleTo(screen)
        assert screen.benchmark_warning_label.text() == PROSE_SLOW_WARNING
        screen.deleteLater()

    def test_an_absent_model_is_named_and_warns_of_nothing(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        skipped = ProseBenchmark(skipped=models.language_model_absent_reason())
        screen = _screen(
            tmp_path,
            monkeypatch,
            benchmark_runner=lambda: [_medium(0.5)],
            prose_runner=lambda: skipped,
        )
        _run(qapp, screen)
        text = screen.benchmark_output.toPlainText()
        assert f"Prose stage: not timed - {models.language_model_absent_reason()}" in text
        assert text.endswith("prose stage not timed")
        assert not screen.benchmark_warning_label.isVisibleTo(screen)
        screen.deleteLater()

    def test_both_failures_share_the_warning_label(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop.ui.microphone import PROSE_SLOW_WARNING

        screen = _screen(
            tmp_path,
            monkeypatch,
            benchmark_runner=lambda: [_medium(1.27)],
            prose_runner=lambda: _prose(12.0),
        )
        _run(qapp, screen)
        label = screen.benchmark_warning_label.text()
        assert label.startswith("Benchmark threshold FAILED for: medium.")
        assert label.endswith(PROSE_SLOW_WARNING)
        screen.deleteLater()

    def test_the_real_prose_runner_comes_only_with_the_real_whisper_runner(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        defaults = _screen(tmp_path, monkeypatch)
        assert defaults._prose_runner is run_prose_benchmark
        whisper_only = _screen(tmp_path, monkeypatch, benchmark_runner=list)
        assert whisper_only._prose_runner is None
        _run(qapp, whisper_only)
        assert "Prose stage" not in whisper_only.benchmark_output.toPlainText()
        for screen in (defaults, whisper_only):
            screen.deleteLater()
