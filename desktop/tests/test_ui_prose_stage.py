"""Note-learning-and-styles plan Task 4.4 (D6, D7; C4, C8): the Note tab's
prose stage, offscreen, through ``MockLanguageModel``.

Pinned here:
- Save is DISABLED while a rendering job is in flight (the button and a
  click-time re-check that names the reason) and re-enabled only after the
  completed prose has been DISPLAYED; the note Save then persists is the
  displayed one — display, ``note.enc`` reload and Copy agree (codex
  PR-MED-015);
- a rendering for a section edited while the job ran is DROPPED (the digest
  binding) and the changed section is re-rendered by a second job that asks
  the model only for it;
- every fallback names its reason on the style line: the model could not be
  loaded (a result with a reason — Save re-enabled, nothing unseen), a
  section refused by Check 5 (kept as Clean clinical, the ``style_fallback``
  review warning gates Save until acknowledged), an unexpected stage
  failure;
- ``clear()`` orphans a running job: its late result is dropped, nothing
  crashes, and the thread object is released once it reports;
- the deterministic styles never start a job.

The stage is the REAL ``models.build_prose_stage`` over a mock model, wrapped
so a test can hold the job open on an event.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

import pytest

from scribe_desktop.language_model import LanguageModelError, MockLanguageModel
from scribe_desktop.note import GeneratedNote, bound_rendering, render_note, usable_rendering
from scribe_desktop.session_mode import SessionMode
from scribe_desktop.ui import models


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


def _note_result() -> models.NoteGenerationResult:
    from test_ui_screens import _note_result as build

    return build()


class _Stage:
    """A real narrative stage over ``mock``, held open on ``release`` for
    each job (the event stays set once released); ``calls`` counts jobs."""

    def __init__(self, mock: MockLanguageModel | None = None, *, fail: bool = False) -> None:
        self.mock = mock if mock is not None else MockLanguageModel()
        self.release = threading.Event()
        self.calls = 0
        self.results: list[models.StyleStageResult] = []
        self.fail = fail
        self._real = models.build_prose_stage(
            "narrative", model_factory=lambda: self.mock, cache=None, available=lambda: True
        )
        assert self._real is not None

    def __call__(
        self, note: GeneratedNote, /, *, abort: Callable[[], bool] | None = None
    ) -> models.StyleStageResult:
        self.calls += 1
        assert self.release.wait(10.0), "the test never released the stage"
        if self.fail:
            raise RuntimeError("stage exploded")
        result = self._real(note, abort=abort)
        self.results.append(result)
        return result

    def provider(self, style: Any) -> models.ProseStage | None:
        return self if style in models.PROSE_STYLES else None


def _screen(
    stage: Callable[[Any], models.ProseStage | None] | None,
    *,
    style: str = "narrative",
    copy_enabled: bool = False,
) -> tuple[Any, dict[str, list[Any]]]:
    from scribe_desktop.ui.note import NoteScreen

    record: dict[str, list[Any]] = {"saved": [], "abandoned": [], "cancelled": []}
    screen = NoteScreen(
        note_style_provider=lambda: models.NoteStyleChoice(style, None),  # type: ignore[arg-type]
        prose_stage_provider=stage,
    )
    screen.begin_review(
        _note_result(),
        copy_enabled=copy_enabled,
        on_save=lambda note: record["saved"].append(note),
        on_abandon=lambda: record["abandoned"].append(True),
        on_cancel=lambda: record["cancelled"].append(True),
        template_profile_id="clinic-a",
        mode=SessionMode.NORMAL,
    )
    return screen, record


def _ratify(screen: Any) -> None:
    for proposal in screen._draft.note_proposals:
        screen.confirm_proposal(proposal.proposal_id)
    screen._acknowledge_all()


def _settled(qapp: Any, screen: Any) -> None:
    assert _process_until(
        qapp,
        lambda: not screen.rendering_in_flight
        and not models.sections_to_render(screen._note),
    ), "the stage never settled"


class TestSaveWhileRendering:
    def test_save_waits_for_the_displayed_prose(self, qapp: Any) -> None:
        stage = _Stage()
        screen, record = _screen(stage.provider)
        _ratify(screen)
        assert screen.rendering_in_flight
        assert not screen.save_button.isEnabled()
        assert screen.style_label.text() == models.rendering_in_flight_line("narrative")
        clean_body = render_note(screen._note, "clean")
        assert screen.note_body.toPlainText() == clean_body  # nothing unseen yet
        screen.save()  # the click-time re-check
        assert record["saved"] == []
        assert screen.message_label.text() == models.SAVE_WHILE_RENDERING_MESSAGE

        stage.release.set()
        _settled(qapp, screen)
        assert screen.save_button.isEnabled()
        body = screen.note_body.toPlainText()
        assert body == models.format_note_body(screen._note)
        assert body != clean_body
        assert screen.style_label.text().startswith("Writing style 'Narrative': prose shown for")
        for section in screen._note.note_sections:
            assert usable_rendering(screen._note, section) is not None

        screen.save()
        (saved,) = record["saved"]
        assert models.format_note_body(saved) == body
        assert saved.style_renderings and saved.style == "narrative"
        screen.deleteLater()

    def test_display_reload_and_copy_agree(self, qapp: Any, monkeypatch: Any) -> None:
        # The clipboard stand-in of test_ui_screens (round 70): observable
        # without touching the real Windows clipboard.
        from scribe_desktop.ui import note as note_module

        payloads: list[str] = []

        class _Clipboard:
            def setText(self, text: str) -> None:  # noqa: N802 - Qt spelling
                payloads.append(text)

            def setMimeData(self, mime: Any) -> None:  # noqa: N802 - Qt spelling
                payloads.append(mime.text())  # Task 8.2: the Copy button's route

        class _StubApplication:
            @staticmethod
            def clipboard() -> _Clipboard:
                return _Clipboard()

        monkeypatch.setattr(note_module, "QApplication", _StubApplication)
        stage = _Stage()
        stage.release.set()
        screen, record = _screen(stage.provider, copy_enabled=True)
        _ratify(screen)
        _settled(qapp, screen)
        screen.save()
        (saved,) = record["saved"]
        body = screen.note_body.toPlainText()
        assert saved.style_renderings  # the prose IS in what was persisted
        reloaded = GeneratedNote.from_bytes(saved.to_bytes())
        assert models.format_note_body(reloaded) == body
        assert screen._copy_ready()
        screen._copy_note()
        assert payloads == [body]
        screen.deleteLater()


class TestProseReachesTheBody:
    def test_a_rendered_sections_prose_reaches_the_note_body(self, qapp: Any) -> None:
        """Phase H live smoke (leg h1j): the note body IS the prose pane —
        every usable rendering's text is in it, the `clean` per-line form is
        not, and the body equals the ONE rendering path's output; the
        proposal rows' scroll area shows only with rows."""
        stage = _Stage()
        stage.release.set()
        screen, _record = _screen(stage.provider)
        assert not screen.proposals_scroll.isHidden()  # the fixture draft has proposals
        _ratify(screen)
        _settled(qapp, screen)
        note = screen._note
        body = screen.note_body.toPlainText()
        assert body == render_note(note, "narrative") == models.format_note_body(note)
        rendered = [usable_rendering(note, s) for s in note.note_sections]
        assert any(r is not None for r in rendered)
        for rendering in rendered:
            if rendering is not None:
                assert rendering.prose_text in body
        assert body != render_note(note, "clean")
        assert "prose shown for" in screen.style_label.text()
        screen.clear()
        assert screen.proposals_scroll.isHidden()
        screen.deleteLater()


class TestStaleRenderings:
    def test_an_edit_during_the_job_drops_its_rendering_and_re_renders(
        self, qapp: Any
    ) -> None:
        # Settle a fully rendered, ratified note first (the review's own
        # confirmations change section digests too), then hold the stage.
        stage = _Stage()
        stage.release.set()
        screen, _record = _screen(stage.provider)
        _ratify(screen)
        _settled(qapp, screen)
        settled = screen._note
        section = next(s for s in settled.note_sections if len(s.note_assertions) >= 2)
        line = next(a for a in section.note_assertions if a.provenance == "transcript")
        jobs_before, calls_before = stage.calls, len(stage.mock.calls)
        stage.release.clear()

        # Edit 1 changes ONE section: a job renders that section, held open.
        # (`calls` is incremented on the WORKER thread once it enters the
        # stage — after `start()` returns — so wait for it, never read it raw.)
        assert screen.remove_line(line.assertion_id)
        assert screen.rendering_in_flight
        assert _process_until(qapp, lambda: stage.calls == jobs_before + 1)
        # Edit 2, while the job runs, changes the SAME section again (Undo):
        # no second job starts while one is in flight.
        assert screen.undo_line(line.assertion_id)
        assert screen.rendering_in_flight
        assert not _process_until(qapp, lambda: stage.calls > jobs_before + 1, timeout=0.3)
        stage.release.set()
        _settled(qapp, screen)

        # The held job's rendering was for the removed state: DROPPED, never
        # bound; a second job asked the model for that section alone.
        assert stage.calls == jobs_before + 2
        assert len(stage.mock.calls) == calls_before + 2
        note = screen._note
        final_digests = {r.input_digest for r in note.style_renderings}
        stale = stage.results[-2].renderings
        assert [r.section_key for r in stale] == [section.section_key]
        assert stale[0].input_digest not in final_digests
        assert [r.section_key for r in stage.results[-1].renderings] == [section.section_key]
        for current in note.note_sections:
            assert usable_rendering(note, current) is not None
        assert screen.note_body.toPlainText() == models.format_note_body(note)
        # Every content change clears the acknowledgements (PR-MED-010), so
        # Save waits for the practitioner's re-acknowledgement — not for a
        # rendering: nothing is in flight and every section shows its prose.
        assert not screen.rendering_in_flight
        assert not screen.save_button.isEnabled()
        screen._acknowledge_all()
        assert screen.save_button.isEnabled()
        screen.deleteLater()

    def test_a_late_result_after_clear_is_dropped(self, qapp: Any) -> None:
        stage = _Stage()
        screen, _record = _screen(stage.provider)
        assert screen.rendering_in_flight
        screen.clear()
        assert not screen.rendering_in_flight and screen._orphaned_jobs
        assert screen.style_label.text() == ""
        stage.release.set()
        assert _process_until(qapp, lambda: not screen._orphaned_jobs)
        assert screen._note is None and screen.style_label.text() == ""
        assert screen.note_body.toPlainText() == ""
        screen.deleteLater()

    def test_the_tab_stays_busy_until_an_orphaned_job_has_ended(self, qapp: Any) -> None:
        """Codex round 22 PR-MED-036: Cancel during a rendering releases the
        review, but the thread still runs — `is_busy` (the window's close
        guard) stays True until the thread's own `finished` signal disposes
        it; the object is deleted only after it has ended."""
        stage = _Stage()
        screen, record = _screen(stage.provider)
        assert screen.rendering_in_flight and screen.is_busy
        screen.cancel_review()
        assert record["cancelled"] == [True]
        assert screen._draft is None and not screen.rendering_in_flight
        assert screen.is_busy, "an orphaned rendering thread keeps the tab busy"
        job = screen._orphaned_jobs[0]
        assert not job.isFinished()
        stage.release.set()
        assert _process_until(qapp, lambda: not screen.is_busy)
        assert screen._orphaned_jobs == [] and job.isFinished()
        screen.deleteLater()

    def test_an_orphaned_job_stops_after_the_call_in_progress(self, qapp: Any) -> None:
        """Phase H round 24 MED-002: `clear()` (Abandon, Cancel, Complete,
        Discard) flips the job's abort flag; the provider consults it before
        each section's model call, so the orphan makes no further call —
        the model sees at most the call in progress (the frame keeps the
        note referenced until that call returns — round 31 PR-LOW-047)."""

        class _Blocking(MockLanguageModel):
            def __init__(self) -> None:
                super().__init__()
                self.entered = threading.Event()
                self.held = threading.Event()

            def complete(self, *, system_text: str, user_text: str, max_tokens: int) -> str:
                self.entered.set()
                assert self.held.wait(10.0), "the test never released the model"
                return super().complete(
                    system_text=system_text, user_text=user_text, max_tokens=max_tokens
                )

        mock = _Blocking()
        stage = _Stage(mock)
        stage.release.set()
        screen, _record = _screen(stage.provider)
        populated = [s for s in screen._note.note_sections if s.note_assertions]
        assert len(populated) >= 2
        assert mock.entered.wait(10.0)  # the first section's call is in progress
        screen.clear()
        assert screen._orphaned_jobs and screen.is_busy
        mock.held.set()
        assert _process_until(qapp, lambda: not screen.is_busy)
        assert len(mock.calls) == 1
        screen.deleteLater()

    def test_a_late_refusal_reopens_the_acknowledgement(self, qapp: Any) -> None:
        """Phase H round 24 LOW-003: acknowledgement is per CODE and a stage
        result is the one warning source outside the content-change path —
        a `style_fallback` acknowledged while a job was in flight must not
        cover the section that job then refuses."""
        result = _note_result()
        first_section = result.draft.note_sections[0]
        first_line = first_section.note_assertions[0].text
        refused = {first_line}

        def responder(system_text: str, user_text: str) -> str:
            from scribe_desktop.language_model import echo_prompt_lines, prompt_lines

            lines = prompt_lines(user_text)
            if lines and lines[0] in refused:
                return "Something else entirely."
            return echo_prompt_lines(system_text, user_text)

        stage = _Stage(MockLanguageModel(responder=responder))
        stage.release.set()
        screen, _record = _screen(stage.provider)
        _ratify(screen)
        _settled(qapp, screen)
        note = screen._note
        assert any(w.note_warning_code == "style_fallback" for w in note.note_warnings)
        # A SECOND section, rendered fine so far; its first line will be
        # refused by the job the next edit starts.
        second = next(
            s
            for s in note.note_sections
            if s.section_key != first_section.section_key and len(s.note_assertions) >= 2
        )
        line = next(a for a in second.note_assertions if a.provenance == "transcript")
        remaining = [a.text for a in second.note_assertions if a.assertion_id != line.assertion_id]
        refused.add(remaining[0])
        jobs_before = stage.calls
        stage.release.clear()
        assert screen.remove_line(line.assertion_id)  # acks cleared, a job starts (held)
        assert _process_until(qapp, lambda: stage.calls == jobs_before + 1)
        screen._acknowledge_all()  # the practitioner acknowledges the FIRST refusal now
        assert "style_fallback" in screen._acknowledged
        stage.release.set()
        _settled(qapp, screen)
        refused_now = {
            s.section_key
            for s in screen._note.note_sections
            if (r := bound_rendering(screen._note, s)) is not None and r.verdict == "failed"
        }
        assert second.section_key in refused_now
        assert "style_fallback" not in screen._acknowledged
        assert not screen.save_button.isEnabled()
        screen._acknowledge("style_fallback")
        assert screen.save_button.isEnabled()
        screen.deleteLater()

    def test_a_failed_partial_re_render_names_the_prose_that_still_shows(
        self, qapp: Any
    ) -> None:
        """Codex round 22 PR-LOW-038: after a full render, an edit to one
        section whose re-render then fails with a reason must not label the
        WHOLE note Clean clinical while the other sections still show prose."""
        from scribe_desktop.note import note_input_digest

        stage = _Stage()
        stage.release.set()
        screen, _record = _screen(stage.provider)
        _ratify(screen)
        _settled(qapp, screen)
        reason = models.LANGUAGE_MODEL_LOAD_FAILED_LINE.format(label="Narrative", reason="x")

        def failing_stage(note: Any, /, *, abort: Any = None) -> models.StyleStageResult:
            return models.StyleStageResult(
                "narrative", note_input_digest(note), (), 0, 0, 0, 0.0, reason
            )

        screen._prose_stage = failing_stage
        section = next(s for s in screen._note.note_sections if len(s.note_assertions) >= 2)
        line = next(a for a in section.note_assertions if a.provenance == "transcript")
        assert screen.remove_line(line.assertion_id)
        assert _process_until(qapp, lambda: not screen.rendering_in_flight)
        text = screen.style_label.text()
        assert text.startswith(reason[: -len(" - this note is shown as Clean clinical.")])
        assert "still show the prose rendered earlier" in text
        assert "this note is shown as Clean clinical" not in text
        assert models.with_retained_prose(reason, screen._note) == text
        # A note showing NO prose keeps the plain reason.
        plain = _note_result()
        from scribe_desktop.note import finalise_note

        bare = finalise_note(plain.draft, [], plain.document, plain.config)
        assert models.with_retained_prose(reason, bare) == reason
        screen.deleteLater()


class TestFallbackReasons:
    def test_an_absent_model_is_a_stat_and_never_a_remembered_failure(self) -> None:
        """Round 20 MED-002: while the file or runtime is absent the stage
        answers from the same stat the Practitioner tab's poll uses, calls
        no factory and remembers nothing — so a model installed while the
        app runs is loaded at the next finalisation, never "restart"."""
        from scribe_desktop.note import finalise_note

        calls: list[str] = []
        present = {"value": False}

        def factory() -> Any:
            calls.append("load")
            raise LanguageModelError("digest mismatch")

        cache = models._LanguageModelCache()
        stage = models.build_prose_stage(
            "narrative", model_factory=factory, cache=cache, available=lambda: present["value"]
        )
        assert stage is not None
        result = _note_result()
        note = finalise_note(result.draft, [], result.document, result.config)
        outcome = stage(note)
        assert outcome.reason == models.style_fallback_line("narrative")
        assert calls == [] and cache._failure is None
        present["value"] = True
        outcome = stage(note)  # the file appeared: the load is attempted now
        assert calls == ["load"]
        assert outcome.reason is not None and "digest mismatch" in outcome.reason
        assert cache._failure is not None  # a real load failure IS remembered
        assert stage(note).reason is not None and calls == ["load"]  # not re-probed

    def test_a_stale_style_consent_keeps_clean_and_names_it(self) -> None:
        """Phase H round 24 LOW-001: the style store's own consent record
        gates USE — a profile learned under an older text is not
        conditioning material until the practitioner re-agrees on the tab."""
        from scribe_desktop.note import finalise_note
        from scribe_desktop.practitioner_profile import ConsentRecord
        from test_prose_style import _NOW, _style_profile

        current = _style_profile()
        stale = current.model_copy(
            update={
                "consent": ConsentRecord(
                    accepted_at=_NOW, consent_text_version="consent-v2", learning_opt_in=True
                )
            }
        )
        result = _note_result()
        note = finalise_note(result.draft, [], result.document, result.config)
        for profile, expects_calls in ((stale, False), (current, True)):
            mock = MockLanguageModel()
            stage = models.build_prose_stage(
                "own_voice",
                model_factory=lambda mock=mock: mock,
                cache=None,
                available=lambda: True,
                profile_loader=lambda root=None, profile=profile: profile,
            )
            assert stage is not None
            outcome = stage(note)
            if expects_calls:
                assert outcome.reason is None and mock.calls
            else:
                assert outcome.reason == models.STYLE_PROFILE_MISSING_LINE.format(
                    label="Own voice", reason=models.STYLE_CONSENT_STALE_REASON
                )
                assert mock.calls == []

    def test_a_model_that_cannot_load_names_itself_and_frees_save(self, qapp: Any) -> None:
        def broken() -> Any:
            raise LanguageModelError("no such file")

        real = models.build_prose_stage(
            "narrative", model_factory=broken, cache=None, available=lambda: True
        )
        assert real is not None
        screen, _record = _screen(lambda style: real if style == "narrative" else None)
        _ratify(screen)
        assert _process_until(qapp, lambda: not screen.rendering_in_flight)
        line = screen.style_label.text()
        assert line == models.LANGUAGE_MODEL_LOAD_FAILED_LINE.format(
            label="Narrative", reason="no such file"
        )
        assert screen.save_button.isEnabled()  # nothing unseen: the body is Clean clinical
        assert screen.note_body.toPlainText() == render_note(screen._note, "clean")
        screen.deleteLater()

    def test_a_refused_section_keeps_clean_and_draws_the_review_warning(
        self, qapp: Any
    ) -> None:
        result = _note_result()
        first_section = result.draft.note_sections[0]
        first_line = first_section.note_assertions[0].text
        obeying = MockLanguageModel(responses={first_line: "Something else entirely."})
        stage = _Stage(obeying)
        stage.release.set()
        screen, _record = _screen(stage.provider)
        _ratify(screen)
        _settled(qapp, screen)
        note = screen._note
        assert usable_rendering(note, note.note_sections[0]) is None
        assert any(w.note_warning_code == "style_fallback" for w in note.note_warnings)
        assert "shown as Clean clinical (the fidelity check refused" in screen.style_label.text()
        assert first_line in screen.note_body.toPlainText()
        assert "Something else" not in screen.note_body.toPlainText()
        # The warning gates Save until acknowledged, like every review code.
        assert not screen.save_button.isEnabled()
        screen._acknowledge("style_fallback")
        assert screen.save_button.isEnabled()
        screen.deleteLater()

    def test_an_unexpected_stage_failure_names_itself_and_frees_save(self, qapp: Any) -> None:
        stage = _Stage(fail=True)
        stage.release.set()
        screen, _record = _screen(stage.provider)
        _ratify(screen)
        assert _process_until(qapp, lambda: not screen.rendering_in_flight)
        assert "rendering failed (RuntimeError: stage exploded)" in screen.style_label.text()
        assert screen.save_button.isEnabled()
        screen.deleteLater()

    def test_the_deterministic_styles_start_no_job(self, qapp: Any) -> None:
        stage = _Stage()
        for style in ("verbatim", "clean"):
            screen, _record = _screen(stage.provider, style=style)
            assert not screen.rendering_in_flight and stage.calls == 0
            assert screen.style_label.text() == ""
            screen.deleteLater()
