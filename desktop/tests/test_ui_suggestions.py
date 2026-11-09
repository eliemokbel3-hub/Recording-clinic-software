"""Note-content-design plan Task C.4 (D6, D8, D9; C1, C8, C13): the Note
tab's section suggestions, offscreen, through ``MockLanguageModel``.

Pinned here, at the screen:
- the job's start: at once with no prose stage and with no renderable
  section; armed behind a style job in flight and started once it reports
  (a success AND a failure); no left-out line → no job, "Nothing to
  suggest.";
- a running job waits between windows while a style job is pending, and
  resumes when it reports;
- what lands is a MARK on the existing chooser and a pre-selected section
  only when the current segment changes (a re-finalise of the same segment
  keeps the carried-over section); the filter tick lists suggested lines;
  Add on a marked line clears ``clinician_line_omitted``; a line added by
  hand meanwhile has no mark, and Undo returns it; a suspect line is asked
  and keeps its prefix; a shadow recording's marks are identical and
  nothing is copied;
- the exit policy: Save is allowed while the job runs; a live job is not
  ``is_busy``; ``clear()`` / Cancel / Delete mid-run cancel the remaining
  windows of a multi-window job, the orphan is busy only until its
  in-flight window returns, then disposed; ``prepare_close`` after Save —
  inside a window and inside a yield wait — aborts and orphans the job;
- every fallback names itself on the line (the model absent, a job that
  raised — by its type name only, a job whose every suggestion the
  ownership rule refused — review round 10 LOW-001).

The stage is the REAL ``models.build_suggestion_stage`` (or, for a
multi-window job, ``note_suggest.run_suggestion_stage`` with a one-line
window) over a mock model whose every window can be held on an event. No
test loads the real model or touches the real clipboard.

Through the REAL ``MainWindow`` (``TestThroughTheWindow``; its stage the same
fake, its presence seam present): Complete, Discard, Cancel and Delete
mid-run; the Recovery tab's open-review refused only through the orphan's
in-flight window; a window close right after Save, inside a window and
inside a yield wait, refused once with the guard's own line and accepted
once the window returns. The window's presence seam is asked BEFORE a job
starts, so with the model absent no thread runs at all (every other window
test). Through the window's REAL ``ChromeBridge`` (stage-2 leg x7): Chrome's
Discard never reaches a note under review — it is refused at QUEUED, the
review and its job untouched — and Chrome's real exit from a saved review is
the next Start (the Session tab's ``_start``, which ``start_linked`` shares),
after which a Chrome Discard of the new recording leaves the Note tab alone.
"""

from __future__ import annotations

import re
import secrets
import threading
import time
from collections.abc import Callable, Iterator
from typing import Any

import pytest

from scribe_desktop.encounter import unlinked_consent
from scribe_desktop.language_model import MockLanguageModel
from scribe_desktop.note import ExtractiveNoteProvider, compose_draft, manual_assertion_id
from scribe_desktop.note_suggest import SuggestionInput, run_suggestion_stage
from scribe_desktop.session import RecordingSession, SessionState
from scribe_desktop.session_mode import SessionMode
from scribe_desktop.transcription import SPEAKER_1, SPEAKER_2
from scribe_desktop.ui import models
from test_ui_screens import (
    _NOTE_TURNS,
    FakeController,
    _acknowledge_everything,
    _main_window,
    _note_config,
    _note_document,
)

# Two invented patient lines no cue routes, after the fixture's four (its
# left-out line is segment 3, the clinician's "Please use an ice pack tonight").
_WIDE_TURNS: tuple[tuple[str, str], ...] = (
    *_NOTE_TURNS,
    ("The weather was lovely on Sunday", SPEAKER_1),
    ("We had a lovely lunch by the sea", SPEAKER_1),
)
# Nothing here routes: the note has no section a prose stage could render.
_BLAND_TURNS: tuple[tuple[str, str], ...] = (
    ("The weather was lovely on Sunday", SPEAKER_1),
    ("We had a lovely lunch by the sea", SPEAKER_2),
)
_ICE = 3  # the fixture's left-out clinician line


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _process_until(qapp: Any, predicate: Callable[[], bool], timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qapp.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


class _Held:
    """Every screen and event a test made: torn down by releasing every
    event and draining every job BEFORE the screen goes — a QThread
    destroyed while it runs would abort the whole process."""

    def __init__(self) -> None:
        self.screens: list[Any] = []
        self.windows: list[Any] = []
        self.events: list[threading.Event] = []


@pytest.fixture
def held(qapp: Any) -> Iterator[_Held]:
    registry = _Held()
    yield registry
    for event in registry.events:
        event.set()
    for screen in registry.screens:
        _process_until(qapp, lambda s=screen: _idle(s), timeout=15.0)
        screen.deleteLater()
    for window in registry.windows:
        note_screen = window.note_screen
        _process_until(qapp, lambda s=note_screen: _idle(s), timeout=15.0)
        note_screen.clear()
        _process_until(qapp, lambda s=note_screen: _idle(s), timeout=15.0)
        window.close()
    qapp.processEvents()


def _idle(screen: Any) -> bool:
    return (
        not screen.suggestion_in_flight
        and not screen.rendering_in_flight
        and not screen._orphaned_jobs
    )


def _result(
    turns: tuple[tuple[str, str], ...] = _NOTE_TURNS, *, suspect: int | None = None
) -> models.NoteGenerationResult:
    document = _note_document(turns)
    if suspect is not None:
        segments = list(document.transcript_segments)
        words = tuple(
            word.model_copy(update={"suspect": True})
            for word in segments[suspect].transcript_words
        )
        segments[suspect] = segments[suspect].model_copy(update={"transcript_words": words})
        document = document.model_copy(update={"transcript_segments": tuple(segments)})
    config = _note_config()
    draft = compose_draft(document, config, ExtractiveNoteProvider(), clinician_speaker=SPEAKER_2)
    return models.NoteGenerationResult(draft=draft, config=config, document=document)


class _Suggestions:
    """A suggestion stage over ``MockLanguageModel``: the REAL builder, or
    (``window_segments``) the stage function with a small window. Each
    window's call waits on ``release``; it answers every asked line by its
    speaker role. ``windows`` counts the calls, ``asked`` each job's
    ``lines_asked`` (a test proves the worker is inside the screen's yield
    wait with ``_watch_yield_wait``, on the wait itself)."""

    def __init__(
        self,
        held: _Held,
        *,
        clinician_key: str = "advice_home_exercise",
        other_key: str = "history_presenting_complaint",
        window_segments: int | None = None,
        hold: bool = False,
        fail: bool = False,
    ) -> None:
        self.release = threading.Event()
        held.events.append(self.release)
        if not hold:
            self.release.set()
        self.windows = 0
        self.asked: list[int] = []
        self.prompts: list[str] = []
        self.fail = fail
        self._keys = {"clinician": clinician_key, "other": other_key}
        self._window_segments = window_segments
        self.model = MockLanguageModel(responder=self._respond)
        self._real = models.build_suggestion_stage(
            model_factory=lambda: self.model, cache=None, available=lambda: True
        )

    def _respond(self, _system: str, user_text: str) -> str:
        self.windows += 1
        self.prompts.append(user_text)
        assert self.release.wait(10.0), "the test never released the window"
        rows = re.findall(r"^(\d+)\? (clinician|other) ", user_text, flags=re.MULTILINE)
        return "\n".join(f"{number} {self._keys[role]}" for number, role in rows)

    def __call__(
        self,
        suggestion_input: SuggestionInput,
        /,
        *,
        abort: Callable[[], bool] | None = None,
        yield_to: Callable[[], None] | None = None,
    ) -> models.SuggestionStageOutcome:
        self.asked.append(suggestion_input.lines_asked)
        if self.fail:
            raise RuntimeError("the stage exploded over some invented words")
        if self._window_segments is None:
            return self._real(suggestion_input, abort=abort, yield_to=yield_to)
        return models.SuggestionStageOutcome(
            run_suggestion_stage(
                suggestion_input,
                self.model,
                abort=abort,
                yield_to=yield_to,
                window_segments=self._window_segments,
            )
        )


def _watch_yield_wait(screen: Any) -> threading.Event:
    """Codex rounds 11–12 (PR-LOW-051, PR-LOW-086): an event the WORKER sets
    inside the screen's real yield wait — the live job's own abort flag's
    ``wait``, the one primitive the Note tab's ``yield_to`` blocks in
    (``ui/note.py`` ``_start_suggestion_job``) — on a call made while a prose
    job is pending and the abort is unset (the wait loop's own condition,
    so the worker is past it). Installed on that flag while the worker is
    held inside window 1, before it can reach any wait; test-local, no
    production seam. A test waits on the event, then closes or releases."""
    abort = screen._suggest_slot.abort
    assert abort is not None, "no live suggestion job to watch"
    pending = screen._prose_pending
    entered = threading.Event()
    real_wait = abort.wait

    def wait(timeout: float | None = None) -> bool:
        if pending.is_set() and not abort.is_set():
            entered.set()
        return real_wait(timeout)

    abort.wait = wait
    return entered


def _screen(
    held: _Held,
    stage: Any,
    *,
    result: models.NoteGenerationResult | None = None,
    prose: Callable[[Any], models.ProseStage | None] | None = None,
    style: str = "clean",
    copy_enabled: bool = False,
    mode: SessionMode = SessionMode.NORMAL,
    present: Callable[[], bool] | None = None,
) -> tuple[Any, dict[str, list[Any]]]:
    from scribe_desktop.ui.note import NoteScreen

    record: dict[str, list[Any]] = {"saved": [], "abandoned": [], "cancelled": []}
    screen = NoteScreen(
        note_style_provider=lambda: models.NoteStyleChoice(style, None),  # type: ignore[arg-type]
        prose_stage_provider=prose,
        suggestion_stage=stage,
        suggestion_model_present=present,
    )
    held.screens.append(screen)
    screen.begin_review(
        result if result is not None else _result(),
        copy_enabled=copy_enabled,
        on_save=lambda note: record["saved"].append(note),
        on_abandon=lambda: record["abandoned"].append(True),
        on_cancel=lambda: record["cancelled"].append(True),
        template_profile_id="clinic-a",
        mode=mode,
    )
    return screen, record


def _landed(qapp: Any, screen: Any) -> None:
    assert _process_until(
        qapp, lambda: not screen.suggestion_in_flight and screen._suggest_outcome is not None
    ), "the suggestion job never landed"


def _chooser(screen: Any) -> dict[int, str]:
    combo = screen.utterance_combo
    return {combo.itemData(i): combo.itemText(i) for i in range(combo.count())}


def _select(screen: Any, segment: int) -> None:
    combo = screen.utterance_combo
    index = combo.findData(segment)
    assert index >= 0, f"segment {segment} is not offered"
    combo.setCurrentIndex(index)


def _ratify_all(screen: Any) -> None:
    """Every proposal confirmed, then every review code acknowledged —
    "Acknowledge all" and each separately acknowledged code by its row."""
    for proposal in screen._draft.note_proposals:
        screen.confirm_proposal(proposal.proposal_id)
    screen._acknowledge_all()
    for code in {w.note_warning_code for w in screen._note.note_warnings}:
        screen._acknowledge(code)


def _mark(key: Any) -> str:
    return models.suggested_line_mark(key)


class TestTheStart:
    def test_the_job_starts_at_once_with_no_prose_stage_and_marks_land(
        self, qapp: Any, held: _Held
    ) -> None:
        suggestions = _Suggestions(held, hold=True)
        screen, _record = _screen(held, suggestions)
        assert screen.suggestion_in_flight and not screen.rendering_in_flight
        assert screen.suggestion_label.text() == models.suggestion_in_flight_line(1)
        assert not screen.suggestion_label.isHidden()
        assert _mark("advice_home_exercise") not in _chooser(screen)[_ICE]
        suggestions.release.set()
        _landed(qapp, screen)
        assert suggestions.asked == [1]
        assert screen._suggested == {_ICE: "advice_home_exercise"}
        label = _chooser(screen)[_ICE]
        assert label.startswith(f"{_ICE + 1}. ")
        assert f"{_mark('advice_home_exercise')}speaker_2: " in label
        assert "1 line has a suggested section." in screen.flagged_count_label.text()
        # The count line carries it now: the job's own line is hidden.
        assert screen.suggestion_label.isHidden()

    def test_with_no_renderable_section_it_starts_at_once(
        self, qapp: Any, held: _Held
    ) -> None:
        from test_ui_prose_stage import _Stage

        stage = _Stage()
        held.events.append(stage.release)
        suggestions = _Suggestions(held)
        screen, _record = _screen(
            held, suggestions, result=_result(_BLAND_TURNS), prose=stage.provider, style="narrative"
        )
        assert not screen.rendering_in_flight and stage.calls == 0
        _landed(qapp, screen)
        assert suggestions.asked == [2]
        assert len(screen._suggested) == 2

    def test_armed_behind_a_style_job_it_starts_once_that_job_reports(
        self, qapp: Any, held: _Held
    ) -> None:
        from test_ui_prose_stage import _Stage

        stage = _Stage()
        held.events.append(stage.release)
        suggestions = _Suggestions(held)
        screen, _record = _screen(held, suggestions, prose=stage.provider, style="narrative")
        assert screen.rendering_in_flight and not screen.suggestion_in_flight
        # Armed: the line already says it is coming; nothing has run.
        assert screen.suggestion_label.text() == models.suggestion_in_flight_line(1)
        assert not _process_until(qapp, lambda: bool(suggestions.asked), timeout=0.3)
        stage.release.set()
        _landed(qapp, screen)
        assert suggestions.asked == [1]
        assert _ICE in screen._suggested

    def test_armed_behind_a_style_job_that_failed_it_still_starts(
        self, qapp: Any, held: _Held
    ) -> None:
        from test_ui_prose_stage import _Stage

        stage = _Stage(fail=True)
        held.events.append(stage.release)
        suggestions = _Suggestions(held)
        screen, _record = _screen(held, suggestions, prose=stage.provider, style="narrative")
        assert screen.rendering_in_flight
        stage.release.set()
        _landed(qapp, screen)
        assert "rendering failed" in screen.style_label.text()
        assert suggestions.asked == [1]

    def test_no_left_out_line_no_job_and_nothing_to_suggest(
        self, qapp: Any, held: _Held
    ) -> None:
        suggestions = _Suggestions(held)
        screen, _record = _screen(held, suggestions, result=_result(_NOTE_TURNS[:3]))
        assert screen.eligible_utterances() == ()
        assert not screen.suggestion_in_flight
        assert screen.suggestion_label.text() == models.SUGGESTION_NOTHING_LINE
        assert not _process_until(qapp, lambda: bool(suggestions.asked), timeout=0.2)

    def test_a_screen_without_a_stage_runs_no_job(self, qapp: Any, held: _Held) -> None:
        screen, _record = _screen(held, None)
        assert not screen.suggestion_in_flight and screen._suggest_outcome is None
        assert screen.suggestion_label.isHidden()
        assert screen.flagged_only_checkbox.text() == models.FLAGGED_FILTER_LABEL


class TestTheYield:
    def test_a_running_job_waits_while_a_style_job_runs_and_resumes(
        self, qapp: Any, held: _Held
    ) -> None:
        from test_ui_prose_stage import _Stage

        stage = _Stage()
        stage.release.set()
        held.events.append(stage.release)
        suggestions = _Suggestions(held, window_segments=1, hold=True)
        screen, _record = _screen(
            held, suggestions, result=_result(_WIDE_TURNS), prose=stage.provider, style="narrative"
        )
        assert _process_until(qapp, lambda: suggestions.windows == 1)
        asked = suggestions.asked[0]
        assert asked >= 2, "the wide fixture must leave at least two lines out"
        waiting = _watch_yield_wait(screen)  # window 1 is held: the worker is in it
        # An edit while window 1 is held starts a new (held) prose job.
        stage.release.clear()
        patient_line = next(
            seg for seg, label in _chooser(screen).items() if seg != _ICE and "speaker_1" in label
        )
        assert screen.add_line(patient_line, "history_presenting_complaint")
        assert screen.rendering_in_flight
        assert screen._prose_pending.is_set()
        suggestions.release.set()  # window 1 returns: the job must now wait
        # PR-LOW-086: the worker is INSIDE the screen's real yield wait while
        # the prose job is pending — the timeout is a failure bound only —
        # and window 2 starts only once that wait returns.
        assert _process_until(qapp, waiting.is_set)
        assert suggestions.windows == 1 and screen.suggestion_in_flight
        stage.release.set()  # the prose job reports: the job resumes
        _landed(qapp, screen)
        assert suggestions.windows == asked
        assert screen._suggest_outcome.result.windows_run == asked


class TestTheMarks:
    def test_a_changed_segment_pre_selects_and_add_clears_the_omission(
        self, qapp: Any, held: _Held
    ) -> None:
        suggestions = _Suggestions(held)
        screen, _record = _screen(held, suggestions, result=_result(_WIDE_TURNS))
        _landed(qapp, screen)
        assert any(
            w.note_warning_code == "clinician_line_omitted" for w in screen._note.note_warnings
        )
        other = next(seg for seg in _chooser(screen) if seg != _ICE)
        _select(screen, other)
        assert screen.section_combo.currentData() == "history_presenting_complaint"
        _select(screen, _ICE)
        assert screen.section_combo.currentData() == "advice_home_exercise"
        screen._on_add_clicked()
        assert _ICE not in _chooser(screen)
        assert not any(
            w.note_warning_code == "clinician_line_omitted" for w in screen._note.note_warnings
        )

    def test_a_refinalise_of_the_same_segment_keeps_the_carried_section(
        self, qapp: Any, held: _Held
    ) -> None:
        suggestions = _Suggestions(held)
        screen, _record = _screen(held, suggestions, result=_result(_WIDE_TURNS))
        _landed(qapp, screen)
        other = next(seg for seg in _chooser(screen) if seg != _ICE)
        _select(screen, other)
        _select(screen, _ICE)
        assert screen.section_combo.currentData() == "advice_home_exercise"
        combo = screen.section_combo
        combo.setCurrentIndex(combo.findData("presenting_complaint"))
        proposal = screen._draft.note_proposals[0]
        screen.confirm_proposal(proposal.proposal_id)  # a re-finalise
        assert screen.utterance_combo.currentData() == _ICE
        assert screen.section_combo.currentData() == "presenting_complaint"

    def test_a_line_added_by_hand_meanwhile_has_no_mark_and_undo_returns_it(
        self, qapp: Any, held: _Held
    ) -> None:
        suggestions = _Suggestions(held, hold=True)
        screen, _record = _screen(held, suggestions)
        assert _process_until(qapp, lambda: suggestions.windows == 1)
        assert screen.add_line(_ICE, "advice_home_exercise")
        suggestions.release.set()
        _landed(qapp, screen)
        assert screen._suggested == {_ICE: "advice_home_exercise"}
        assert _ICE not in _chooser(screen)
        assert screen._accepted_suggestions == {}
        # The job suggested something: its line stays hidden, never "No suggestions."
        assert screen.suggestion_label.isHidden()
        assert screen.undo_line(manual_assertion_id(_ICE))
        assert _mark("advice_home_exercise") in _chooser(screen)[_ICE]

    def test_a_job_whose_every_suggestion_is_refused_says_no_suggestions(
        self, qapp: Any, held: _Held
    ) -> None:
        """Review round 10 LOW-001 (C8): the model gave the clinician's line
        no section and the patient's lines a clinician-owned one — the
        ownership rule refuses both, so nothing is marked, the count line has
        no suggestion clause, and the job's own line says so."""
        suggestions = _Suggestions(held, clinician_key="none", other_key="diagnosis")
        screen, _record = _screen(held, suggestions, result=_result(_WIDE_TURNS))
        _landed(qapp, screen)
        assert screen._suggested and set(screen._suggested.values()) == {"diagnosis"}
        assert screen._accepted_suggestions == {}
        assert all("[suggested:" not in label for label in _chooser(screen).values())
        assert "suggested section" not in screen.flagged_count_label.text()
        assert screen.suggestion_label.text() == models.SUGGESTION_NONE_LINE
        assert not screen.suggestion_label.isHidden()

    def test_the_filter_tick_lists_flagged_or_suggested_lines(
        self, qapp: Any, held: _Held
    ) -> None:
        for other_key in ("none", "history_presenting_complaint"):
            suggestions = _Suggestions(held, other_key=other_key)
            screen, _record = _screen(held, suggestions, result=_result(_WIDE_TURNS))
            _landed(qapp, screen)
            offered = set(_chooser(screen))
            expected = {
                c.segment_index
                for c in screen.eligible_utterances()
                if c.flagged or c.suggested is not None
            }
            screen.flagged_only_checkbox.setChecked(True)
            assert set(_chooser(screen)) == expected
            if other_key == "none":
                assert _ICE in expected and expected != offered
            else:
                assert expected == offered
            screen.flagged_only_checkbox.setChecked(False)
            assert set(_chooser(screen)) == offered

    def test_a_suspect_line_is_asked_and_keeps_its_prefix(
        self, qapp: Any, held: _Held
    ) -> None:
        suspect = len(_WIDE_TURNS) - 1
        suggestions = _Suggestions(held)
        screen, _record = _screen(held, suggestions, result=_result(_WIDE_TURNS, suspect=suspect))
        _landed(qapp, screen)
        assert suspect in screen._suggested
        label = _chooser(screen)[suspect]
        assert f"{_mark('history_presenting_complaint')}speaker_1: [possibly not speech] " in label
        # Asked with its words: the window's row carries the line.
        assert any("lovely lunch" in prompt for prompt in suggestions.prompts)

    def test_a_shadow_recordings_marks_are_identical_and_nothing_is_copied(
        self, qapp: Any, held: _Held, monkeypatch: Any
    ) -> None:
        from scribe_desktop.ui import note as note_module

        payloads: list[str] = []

        class _Clipboard:
            def setText(self, text: str) -> None:  # noqa: N802 - Qt spelling
                payloads.append(text)

            def setMimeData(self, mime: Any) -> None:  # noqa: N802 - Qt spelling
                payloads.append(mime.text())

        class _StubApplication:
            @staticmethod
            def clipboard() -> _Clipboard:
                return _Clipboard()

        monkeypatch.setattr(note_module, "QApplication", _StubApplication)
        labels: dict[SessionMode, dict[int, str]] = {}
        for mode in (SessionMode.NORMAL, SessionMode.SHADOW):
            suggestions = _Suggestions(held)
            screen, _record = _screen(
                held, suggestions, result=_result(_WIDE_TURNS), copy_enabled=True, mode=mode
            )
            _landed(qapp, screen)
            labels[mode] = _chooser(screen)
            if mode is SessionMode.SHADOW:
                _ratify_all(screen)
                screen._copy_note()
                assert screen.message_label.text() == models.SHADOW_COPY_REFUSED
        assert labels[SessionMode.SHADOW] == labels[SessionMode.NORMAL]
        assert any("[suggested:" in label for label in labels[SessionMode.SHADOW].values())
        assert payloads == []


class TestTheExitPolicy:
    @pytest.mark.parametrize("exit_name", ["clear", "cancel_review", "abandon"])
    def test_an_exit_mid_run_cancels_the_remaining_windows(
        self, qapp: Any, held: _Held, exit_name: str
    ) -> None:
        suggestions = _Suggestions(held, window_segments=1, hold=True)
        screen, record = _screen(held, suggestions, result=_result(_WIDE_TURNS))
        assert _process_until(qapp, lambda: suggestions.windows == 1)
        assert suggestions.asked[0] >= 2
        getattr(screen, exit_name)()
        assert not screen.suggestion_in_flight
        assert screen._orphaned_jobs and screen.is_busy  # the in-flight window
        suggestions.release.set()
        assert _process_until(qapp, lambda: not screen._orphaned_jobs)
        assert suggestions.windows == 1  # the remaining windows never ran
        assert not screen.is_busy
        assert screen.utterance_combo.count() == 0
        assert screen.suggestion_label.isHidden()
        assert screen._suggested == {}
        if exit_name == "cancel_review":
            assert record["cancelled"] == [True]
        if exit_name == "abandon":
            assert record["abandoned"] == [True]

    def test_save_is_allowed_and_a_live_job_is_not_busy(self, qapp: Any, held: _Held) -> None:
        suggestions = _Suggestions(held, window_segments=1, hold=True)
        screen, record = _screen(held, suggestions, result=_result(_WIDE_TURNS))
        assert _process_until(qapp, lambda: suggestions.windows == 1)
        _ratify_all(screen)
        assert screen.suggestion_in_flight
        assert screen.save_button.isEnabled()
        screen.save()
        assert len(record["saved"]) == 1
        assert screen.suggestion_in_flight and not screen.is_busy
        suggestions.release.set()
        _landed(qapp, screen)
        # PR-LOW-050: the result lands before the thread's `finished` disposes
        # it — wait for the disposal itself, then the screen is not busy.
        assert _process_until(qapp, lambda: not screen._orphaned_jobs)
        assert not screen.is_busy
        assert suggestions.windows == suggestions.asked[0]

    def test_prepare_close_after_save_inside_a_window(self, qapp: Any, held: _Held) -> None:
        suggestions = _Suggestions(held, window_segments=1, hold=True)
        screen, record = _screen(held, suggestions, result=_result(_WIDE_TURNS))
        assert _process_until(qapp, lambda: suggestions.windows == 1)
        _ratify_all(screen)
        screen.save()
        assert record["saved"] and not screen.is_busy
        screen.prepare_close()
        assert not screen.suggestion_in_flight
        assert screen.is_busy  # the orphan's in-flight window holds the close
        assert screen.suggestion_label.text() == models.SUGGESTION_STOPPED_LINE
        suggestions.release.set()
        assert _process_until(qapp, lambda: not screen.is_busy)
        assert suggestions.windows == 1

    def test_prepare_close_after_save_inside_a_yield_wait(self, qapp: Any, held: _Held) -> None:
        suggestions = _Suggestions(held, window_segments=1, hold=True)
        screen, record = _screen(held, suggestions, result=_result(_WIDE_TURNS))
        assert _process_until(qapp, lambda: suggestions.windows == 1)
        _ratify_all(screen)
        screen.save()
        assert record["saved"]
        waiting = _watch_yield_wait(screen)  # window 1 is held: the worker is in it
        screen._prose_pending.set()  # as a pending prose job would
        suggestions.release.set()  # window 1 returns into the yield wait
        # PR-LOW-086: the abort lands INSIDE the screen's real yield wait,
        # never before it (the timeout is a failure bound only).
        assert _process_until(qapp, waiting.is_set)
        assert suggestions.windows == 1
        assert screen.suggestion_in_flight and not screen.is_busy
        screen.prepare_close()
        assert _process_until(qapp, lambda: not screen.is_busy, timeout=3.0)
        assert suggestions.windows == 1
        screen._prose_pending.clear()

    def test_prepare_close_with_no_job_changes_nothing(self, qapp: Any, held: _Held) -> None:
        suggestions = _Suggestions(held)
        screen, _record = _screen(held, suggestions)
        _landed(qapp, screen)
        before = (screen._suggest_outcome, dict(screen._suggested))
        screen.prepare_close()
        assert (screen._suggest_outcome, screen._suggested) == before
        assert _mark("advice_home_exercise") in _chooser(screen)[_ICE]


class TestTheFallbackLines:
    def test_the_model_absent_names_the_c8_line(self, qapp: Any, held: _Held) -> None:
        loads: list[None] = []

        def factory() -> MockLanguageModel:
            loads.append(None)
            return MockLanguageModel()

        stage = models.build_suggestion_stage(
            model_factory=factory, cache=None, available=lambda: False
        )
        screen, _record = _screen(held, stage)
        _landed(qapp, screen)
        assert screen.suggestion_label.text() == models.suggestion_model_absent_line()
        assert loads == [] and screen._suggested == {}

    def test_the_presence_seam_answers_before_any_thread_runs(
        self, qapp: Any, held: _Held
    ) -> None:
        """Stage-2 leg x6: the screen asks the window's presence seam on its
        own thread first — absent, the line names it and NO job starts (so
        nothing queued can hold `is_busy` after the review ends); present, the
        job runs as before. Asked per review, never kept."""
        asks: list[bool] = []
        present = {"value": False}

        def seam() -> bool:
            asks.append(present["value"])
            return present["value"]

        suggestions = _Suggestions(held)
        screen, _record = _screen(held, suggestions, present=seam)
        assert asks == [False]
        assert not screen.suggestion_in_flight and not screen._orphaned_jobs
        assert suggestions.asked == []
        assert screen.suggestion_label.text() == models.suggestion_model_absent_line()
        screen.clear()
        assert not screen.is_busy  # nothing was ever started
        present["value"] = True
        screen.begin_review(
            _result(),
            on_save=lambda _note: None,
            on_abandon=lambda: None,
            template_profile_id="clinic-a",
            mode=SessionMode.NORMAL,
        )
        assert asks == [False, True]
        _landed(qapp, screen)
        assert suggestions.asked == [1] and _ICE in screen._suggested

    def test_a_job_that_raised_names_its_type_only(self, qapp: Any, held: _Held) -> None:
        suggestions = _Suggestions(held, fail=True)
        screen, _record = _screen(held, suggestions)
        _landed(qapp, screen)
        line = screen.suggestion_label.text()
        assert line == models.SUGGESTION_FAILED_LINE.format(reason="RuntimeError")
        assert "invented" not in line
        assert screen._suggested == {}


# --- through the REAL MainWindow (stage-2 leg x6; D8's exit policy) ---------------


_WORK_IN_PROGRESS = "Work in progress - "


def _window_review(
    qapp: Any, tmp_path: Any, monkeypatch: Any, held: _Held, stage: _Suggestions
) -> Any:
    """A review reached the way the app reaches one (`TestNoteWiring.
    _generate_through_window`'s route, over a rooted window): a queued NORMAL
    recording, a live transcript, role and profile confirmed, Generate. The
    window's own suggestion stage is the fake (`build_suggestion_stage` is
    called at construction), and its presence seam says present — the
    model itself is never loaded."""
    monkeypatch.setattr(models, "build_suggestion_stage", lambda **_kwargs: stage)
    controller = FakeController()
    controller.state_value = SessionState.QUEUED
    controller.session_value = RecordingSession(consent=unlinked_consent()).with_state(
        SessionState.QUEUED
    )
    window = _main_window(
        tmp_path,
        controller,
        profile_root=tmp_path / "profile",
        language_model_available=lambda: True,
    )
    held.windows.append(window)
    result = _result(_WIDE_TURNS)
    window.transcript_screen._config_loader = _note_config
    window.transcript_screen._note_generator_factory = (
        lambda **_kwargs: lambda _directory, _crypto: result
    )
    window.session_screen.transcript_ready.emit(result.document)
    qapp.processEvents()
    window.transcript_screen.set_role(SPEAKER_2)
    window.transcript_screen.set_profile("clinic-a")
    window.transcript_screen.generate()
    assert _process_until(qapp, lambda: window.note_screen.current_note() is not None)
    assert _process_until(qapp, lambda: stage.windows == 1), "window 1 never started"
    assert stage.asked[0] >= 2, "the wide fixture must leave at least two lines out"
    return window


def _fake_note_write(monkeypatch: Any) -> None:
    """Save travels the window's own route (`MainWindow._on_note_save` ->
    `TranscriptScreen.save_note` under the held lease) without touching disk
    (`TestNoteWiring._fake_write_note`'s shape)."""

    def fake_write(
        directory: Any, crypto: Any, note: Any, config: Any, **_provenance: Any
    ) -> Any:
        return directory / "note.enc"

    monkeypatch.setattr("scribe_desktop.ui.transcript.write_saved_note", fake_write)


def _save_through_window(window: Any) -> None:
    note_screen = window.note_screen
    for proposal in note_screen._draft.note_proposals:
        note_screen.confirm_proposal(proposal.proposal_id)
    _acknowledge_everything(note_screen)
    for code in {w.note_warning_code for w in note_screen._note.note_warnings}:
        note_screen._acknowledge(code)
    assert note_screen.save_button.isEnabled()
    note_screen.save()
    assert note_screen._note_saved, note_screen.message_label.text()


def _close(window: Any) -> bool:
    from PySide6.QtGui import QCloseEvent

    event = QCloseEvent()
    window.closeEvent(event)
    return event.isAccepted()


def _chrome_link(qapp: Any, window: Any) -> Any:
    """The window's REAL bridge (`MainWindow.attach_chrome_link`, as
    `app.main` builds it) over the bridge suite's recording fake sender —
    no pipe — with one client connected."""
    from test_ui_bridge import FakeSender

    bridge = window.attach_chrome_link()
    sender = FakeSender()
    bridge.attach(sender)
    bridge.connected(1)
    qapp.processEvents()
    qapp.processEvents()
    return sender


def _chrome_command(qapp: Any, window: Any, action: str, **fields: Any) -> None:
    from scribe_desktop.protocol import make_pipe_envelope

    bridge = window.chrome_bridge
    payload: dict[str, Any] = {"action": action, "state_rev": bridge.state_rev, **fields}
    bridge.message(1, make_pipe_envelope("command", payload=payload))
    qapp.processEvents()
    qapp.processEvents()


def _chrome_refusal(sender: Any) -> tuple[str, str] | None:
    refusal = sender.last.last_refusal
    return None if refusal is None else (refusal.action, refusal.reason)


class TestThroughTheWindow:
    @pytest.mark.parametrize("exit_name", ["completed", "discarded", "cancel", "delete"])
    def test_an_exit_mid_run_cancels_the_remaining_windows(
        self, qapp: Any, tmp_path: Any, monkeypatch: Any, held: _Held, exit_name: str
    ) -> None:
        """Complete and Discard reach the Note tab through the transcript
        screen's `closed` signal (`MainWindow._on_transcript_closed`, the one
        funnel both of the Transcript tab's buttons take — Chrome has no
        Complete, and its Discard never reaches a queued session, pinned
        below); Cancel and Delete through the tab's own callbacks
        (`_on_note_cancel`, `_on_note_abandon`)."""
        stage = _Suggestions(held, window_segments=1, hold=True)
        window = _window_review(qapp, tmp_path, monkeypatch, held, stage)
        note_screen = window.note_screen
        if exit_name in ("completed", "discarded"):
            window.transcript_screen.closed.emit(exit_name)
        elif exit_name == "cancel":
            note_screen.cancel_review()
        else:
            note_screen.abandon()
        assert note_screen.current_note() is None
        assert not note_screen.suggestion_in_flight
        assert note_screen.is_busy  # the orphan's in-flight window
        stage.release.set()
        assert _process_until(qapp, lambda: not note_screen.is_busy)
        assert stage.windows == 1  # the remaining windows never ran
        assert note_screen._suggested == {}

    def test_a_recovery_open_review_waits_only_for_the_orphans_window(
        self, qapp: Any, tmp_path: Any, monkeypatch: Any, held: _Held
    ) -> None:
        from pathlib import Path

        stage = _Suggestions(held, window_segments=1, hold=True)
        window = _window_review(qapp, tmp_path, monkeypatch, held, stage)
        window.note_screen.cancel_review()  # the lease released, the tab cleared
        assert not window.transcript_screen.is_busy
        info = models.RecoverableSessionInfo(
            session_id="d" * 32,
            directory=Path("d" * 32),
            created_at=None,
            store_finished=False,
            has_audio=False,
            has_transcript=True,
            has_note=False,
            has_encounter=True,
            expires_at=None,
        )
        assert window._on_review_requested(info) is False
        assert window.recovery_screen.message_label.text() == models.REVIEW_OPEN_BUSY_LINE
        stage.release.set()
        assert _process_until(qapp, lambda: not window.note_screen.is_busy)
        # Past the Note tab's check now: a LATER refusal (an open recovered
        # transcript, set for this read only) proves the busy one let it by.
        window._transcript_source = "e" * 32
        try:
            assert window._on_review_requested(info) is False
            assert window.recovery_screen.message_label.text().startswith(
                "Finish the open recovered transcript first"
            )
        finally:
            window._transcript_source = None
        assert stage.windows == 1

    def test_a_close_after_save_inside_a_window(
        self, qapp: Any, tmp_path: Any, monkeypatch: Any, held: _Held
    ) -> None:
        _fake_note_write(monkeypatch)
        stage = _Suggestions(held, window_segments=1, hold=True)
        window = _window_review(qapp, tmp_path, monkeypatch, held, stage)
        note_screen = window.note_screen
        _save_through_window(window)
        assert note_screen.suggestion_in_flight and not note_screen.is_busy
        # The close guard calls `prepare_close` first: the job is aborted and
        # orphaned, and the close refused ONCE with the guard's own message.
        assert not _close(window)
        assert window.statusBar().currentMessage().startswith(_WORK_IN_PROGRESS)
        assert not note_screen.suggestion_in_flight and note_screen.is_busy
        assert note_screen.suggestion_label.text() == models.SUGGESTION_STOPPED_LINE
        stage.release.set()
        assert _process_until(qapp, lambda: not note_screen.is_busy)
        assert stage.windows == 1
        # Once the window returned the close goes through (a second close
        # answers the Unreviewed list's own confirmation for the queued
        # recording, D6 — never the work-in-progress line again).
        assert _close(window) or _close(window)
        assert not window.statusBar().currentMessage().startswith(_WORK_IN_PROGRESS)

    def test_a_close_after_save_inside_a_yield_wait(
        self, qapp: Any, tmp_path: Any, monkeypatch: Any, held: _Held
    ) -> None:
        _fake_note_write(monkeypatch)
        stage = _Suggestions(held, window_segments=1, hold=True)
        window = _window_review(qapp, tmp_path, monkeypatch, held, stage)
        note_screen = window.note_screen
        _save_through_window(window)
        waiting = _watch_yield_wait(note_screen)  # window 1 is held: the worker is in it
        note_screen._prose_pending.set()  # as a pending prose job would
        stage.release.set()  # window 1 returns into the yield wait
        # PR-LOW-086: the close's abort lands INSIDE the screen's real yield
        # wait, never before it (the timeout is a failure bound only).
        assert _process_until(qapp, waiting.is_set)
        assert stage.windows == 1
        assert note_screen.suggestion_in_flight and not note_screen.is_busy
        assert not _close(window)  # the abort breaks the wait; the orphan is not yet gone
        assert window.statusBar().currentMessage().startswith(_WORK_IN_PROGRESS)
        assert _process_until(qapp, lambda: not note_screen.is_busy, timeout=3.0)
        assert stage.windows == 1
        note_screen._prose_pending.clear()
        assert _close(window) or _close(window)
        assert not window.statusBar().currentMessage().startswith(_WORK_IN_PROGRESS)

    def test_a_chrome_discard_never_reaches_a_note_under_review(
        self, qapp: Any, tmp_path: Any, monkeypatch: Any, held: _Held
    ) -> None:
        """Stage-2 leg x7 (the exit policy's dated correction): Chrome's
        Discard is the Session tab's discard of the LIVE recording
        (`bridge.py:970-973`), admitted only while it records, is paused or
        failed (`bridge.py:961-963`, `models.py:1398-1416`); a note is reviewed
        on a QUEUED session, which can never fail (`session.py:378-380`). So
        through the window's real bridge, with the live reference, it is
        refused `not_allowed_now`, the controller is never asked, and the
        review and its live job run on untouched."""
        stage = _Suggestions(held, window_segments=1, hold=True)
        window = _window_review(qapp, tmp_path, monkeypatch, held, stage)
        controller = window._controller
        controller.session_ref = secrets.token_urlsafe(18)
        sender = _chrome_link(qapp, window)
        note_screen = window.note_screen
        _chrome_command(qapp, window, "discard", session_ref=controller.session_ref, confirmed=True)
        assert _chrome_refusal(sender) == ("discard", "not_allowed_now")
        assert ("discard",) not in controller.calls
        assert controller.state is SessionState.QUEUED
        assert note_screen.current_note() is not None
        assert note_screen.suggestion_in_flight and not note_screen._orphaned_jobs
        stage.release.set()
        _landed(qapp, note_screen)
        assert stage.windows == stage.asked[0]  # every window ran: nothing aborted it
        assert _ICE in note_screen._suggested

    def test_chromes_exit_from_a_saved_review_is_the_next_start(
        self, qapp: Any, tmp_path: Any, monkeypatch: Any, held: _Held
    ) -> None:
        """Stage-2 leg x7: the path Chrome really has to the Note tab's
        `clear()` once a review is saved (Start is refused while the review
        holds the lease) is the NEXT Start — `start_linked` and the desktop's
        `on_start` share `SessionScreen._start`, whose `session_started`
        reaches `MainWindow._on_session_started` (`main_window.py:1597`). That
        Start orphans the job mid-window; a Chrome Discard of the NEW
        recording then reaches only the Session tab (its `session_discarded`
        clears the live view, `main_window.py:781`) — the Note tab is not
        cleared again and the orphan still holds only its in-flight window."""
        _fake_note_write(monkeypatch)
        stage = _Suggestions(held, window_segments=1, hold=True)
        window = _window_review(qapp, tmp_path, monkeypatch, held, stage)
        controller = window._controller
        note_screen = window.note_screen
        sender = _chrome_link(qapp, window)
        _save_through_window(window)
        assert note_screen.suggestion_in_flight and not note_screen.is_busy
        session_screen = window.session_screen
        session_screen._device_provider = lambda: 7
        session_screen.consent_checkbox.setChecked(True)
        session_screen.on_start()
        assert ("start", 7) in controller.calls
        assert controller.state is SessionState.RECORDING
        assert note_screen.current_note() is None
        assert not note_screen.suggestion_in_flight and note_screen.is_busy
        orphans = list(note_screen._orphaned_jobs)
        assert len(orphans) == 1
        clears: list[int] = []
        real_clear = note_screen.clear

        def counted_clear() -> None:
            clears.append(1)
            real_clear()

        monkeypatch.setattr(note_screen, "clear", counted_clear)
        controller.session_ref = secrets.token_urlsafe(18)  # the new recording's
        _chrome_command(qapp, window, "discard", session_ref=controller.session_ref, confirmed=True)
        assert _chrome_refusal(sender) is None
        assert ("discard",) in controller.calls
        assert clears == []
        assert note_screen._orphaned_jobs == orphans and note_screen.is_busy
        stage.release.set()
        assert _process_until(qapp, lambda: not note_screen.is_busy)
        assert stage.windows == 1  # the remaining windows never ran
        assert note_screen._suggested == {}
