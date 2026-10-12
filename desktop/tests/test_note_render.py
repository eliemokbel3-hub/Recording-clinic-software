"""Note-learning-and-styles plan, Phase 3 Task 3.2: THE one rendering path.

What is pinned here:
- ``render_note(note, "verbatim")`` and ``render_note(note, "clean")`` byte
  for byte over one fixture note carrying all three line kinds — a quoted
  transcript line, a typed ``clinician`` line (D4) and an ``autofill`` line
  the practitioner's own config decided (D5, the pre-filled mark).
- ``ui.models.format_note_body`` IS ``render_note(note, note.style)`` for
  every style in ``models.NOTE_STYLES`` — display, reload and Copy cannot
  disagree.
- The prose styles (D7): a note with no rendering renders exactly as
  ``clean``; a usable rendering replaces ONLY its own section's block; a
  rendering whose ``input_digest`` no longer matches the section, and a
  ``failed`` one, are never shown.
- ``section_input_digest`` is order- and content-sensitive, and the
  re-exported ``models`` names are the ``note`` ones.

The fixture note is assembled directly rather than through ``finalise_note``:
these pins are about rendering an artifact, and the artifact's validators are
pinned in ``test_note_schema_v2.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from scribe_desktop import note as note_module
from scribe_desktop.note import (
    CANONICAL_SECTION_KEYS,
    NO_NOTE_CONTENT,
    PREFILLED_MARK,
    ConfirmationDecision,
    GeneratedNote,
    GeneratedSection,
    NoteAssertion,
    NoteSectionKey,
    NoteSpan,
    NoteStyle,
    NoteWarning,
    SourceCoords,
    StyleRendering,
    StyleVerdict,
    digest_bytes,
    render_note,
    section_input_digest,
    text_digest,
    usable_rendering,
)
from scribe_desktop.note_config import (
    NoteConfig,
    SectionMapping,
    TemplateProfile,
    TemplateTarget,
)
from scribe_desktop.transcription import SPEAKER_1
from scribe_desktop.ui import models
from test_prose_style import FIXTURE_NOTES
from test_prose_style import _note as prose_fixture_note

SESSION_ID = "e" * 32
_NOW = datetime(2026, 9, 19, 8, 0, tzinfo=UTC)
_TRANSCRIPT_DIGEST = digest_bytes(b"a transcript artifact")

PATIENT_SYMPTOM = "the numbness is worse at night"
TYPED_TEXT = "Cervical HVLA performed"
PREFILLED_TEXT = "Ice pack advised"
ASSESSMENT_PROSE = "Cervical HVLA was performed."


def _profile() -> TemplateProfile:
    return TemplateProfile(
        template_profile_id="clinic-a",
        display_name="Clinic A",
        template_targets=(
            TemplateTarget(
                target_id="t-main", group="Notes", field_label="Main", target_type="rich_text"
            ),
        ),
        section_mappings=tuple(
            SectionMapping(section_key=key, target_id="t-main")
            for key in CANONICAL_SECTION_KEYS
            if key != "consent"
        ),
        intentionally_unmapped=("consent",),
    )


_CONFIG = NoteConfig(template_profiles=(_profile(),), autofill_rules=(), prefill_templates=())
CONFIG_DIGEST = _CONFIG.config_digest()


def _quoted(
    aid: str, section: NoteSectionKey, segment: int, text: str, speaker: str
) -> NoteAssertion:
    return NoteAssertion(
        assertion_id=aid,
        section_key=section,
        note_span=NoteSpan(
            span_text=text,
            provenance="transcript",
            source_coords=SourceCoords(segment, 0, len(text.split()) - 1),
        ),
        speaker=speaker,
    )


def _decision(aid: str, *, decided_at: datetime = _NOW) -> ConfirmationDecision:
    return ConfirmationDecision(
        proposal_id=aid, note_confirmation="confirmed", decided_at=decided_at
    )


def _typed(
    text: str = TYPED_TEXT,
    *,
    section: NoteSectionKey = "assessment",
    aid: str = "typed-1",
    replaces: str | None = "q0",
) -> NoteAssertion:
    """A typed ``clinician`` line with complete evidence (D4)."""
    return NoteAssertion(
        assertion_id=aid,
        section_key=section,
        note_span=NoteSpan(span_text=text, provenance="clinician"),
        shown_text_digest=text_digest(text),
        config_digest=CONFIG_DIGEST,
        confirmation=_decision(aid),
        replaces=replaces,
    )


def _config_decided(
    text: str = PREFILLED_TEXT,
    *,
    section: NoteSectionKey = "treatment_performed",
    aid: str = "autofill-1",
) -> NoteAssertion:
    """An ``autofill`` line the practitioner's OWN config pre-filled: the
    decision says ``config`` and carries the digest it was minted under
    (D5), so the line renders with ``PREFILLED_MARK``."""
    return NoteAssertion(
        assertion_id=aid,
        section_key=section,
        note_span=NoteSpan(span_text=text, provenance="autofill"),
        proposal_id=aid,
        shown_text_digest=text_digest(text),
        config_digest=CONFIG_DIGEST,
        confirmation=ConfirmationDecision(
            proposal_id=aid,
            note_confirmation="confirmed",
            decided_at=_NOW,
            decided_by="config",
            config_digest=CONFIG_DIGEST,
            confirmation_count=3,
        ),
    )


def _sections() -> tuple[GeneratedSection, ...]:
    return (
        GeneratedSection(
            section_key="presenting_complaint",
            note_assertions=(_quoted("q0", "presenting_complaint", 1, PATIENT_SYMPTOM, SPEAKER_1),),
        ),
        GeneratedSection(section_key="assessment", note_assertions=(_typed(),)),
        GeneratedSection(
            section_key="treatment_performed", note_assertions=(_config_decided(),)
        ),
    )


def _note(
    *,
    style: NoteStyle = "verbatim",
    style_renderings: tuple[StyleRendering, ...] = (),
    sections: tuple[GeneratedSection, ...] | None = None,
    warnings: tuple[NoteWarning, ...] = (),
) -> GeneratedNote:
    """The fixture note: three populated sections in canonical order, one
    line each — quoted, typed, pre-filled by config."""
    return GeneratedNote(
        session_id=SESSION_ID,
        created_at=_NOW,
        template_profile_id="clinic-a",
        provider_name="extractive-v1",
        clinician_speaker=None,
        transcript_digest=_TRANSCRIPT_DIGEST,
        config_digest=CONFIG_DIGEST,
        note_sections=_sections() if sections is None else sections,
        style=style,
        style_renderings=style_renderings,
        note_warnings=warnings,
    )


def _rendering(
    section: NoteSectionKey,
    *,
    prose_text: str = ASSESSMENT_PROSE,
    input_digest: str | None = None,
    verdict: StyleVerdict = "passed",
) -> StyleRendering:
    if input_digest is None:
        source = {s.section_key: s for s in _sections()}[section]
        input_digest = section_input_digest(source)
    return StyleRendering(
        section_key=section,
        prose_text=prose_text,
        input_digest=input_digest,
        verdict=verdict,
    )


VERBATIM_BODY = (
    "Presenting complaint:\n"
    "  - the numbness is worse at night  [from transcript]\n"
    "\n"
    "Assessment:\n"
    "  - Cervical HVLA performed  [typed (clinician-authored)]\n"
    "\n"
    "Treatment performed:\n"
    "  - Ice pack advised  [pre-filled by your config - autofill (clinician-authored)]"
)

CLEAN_BODY = (
    "Presenting complaint\n"
    "the numbness is worse at night\n"
    "\n"
    "Assessment\n"
    "Cervical HVLA performed\n"
    "\n"
    "Treatment performed\n"
    "Ice pack advised  [pre-filled by your config]"
)


class TestDeterministicStyles:
    def test_verbatim_is_pinned_byte_for_byte(self) -> None:
        assert render_note(_note(), "verbatim") == VERBATIM_BODY

    def test_clean_is_pinned_byte_for_byte(self) -> None:
        assert render_note(_note(), "clean") == CLEAN_BODY

    def test_format_note_body_is_render_note_under_the_notes_own_style(self) -> None:
        note = _note()
        for style in models.NOTE_STYLES:
            copied = note.model_copy(update={"style": style})
            assert models.format_note_body(copied) == render_note(note, style)

    def test_an_empty_note_says_so_under_every_style(self) -> None:
        empty = _note(sections=())
        assert empty.note_sections == ()
        for style in models.NOTE_STYLES:
            assert render_note(empty, style) == NO_NOTE_CONTENT
        assert NO_NOTE_CONTENT == "(no note content)"


class TestProseStyles:
    def test_without_renderings_both_prose_styles_are_clean(self) -> None:
        note = _note()
        assert render_note(note, "own_voice") == CLEAN_BODY
        assert render_note(note, "narrative") == CLEAN_BODY

    def test_a_usable_rendering_replaces_only_its_own_section(self) -> None:
        note = _note(style="own_voice", style_renderings=(_rendering("assessment"),))
        body = render_note(note, "own_voice")
        blocks = body.split("\n\n")
        clean_blocks = CLEAN_BODY.split("\n\n")
        assert blocks[0] == clean_blocks[0]
        assert blocks[1] == f"Assessment\n{ASSESSMENT_PROSE}"
        assert blocks[2] == clean_blocks[2]
        assert models.format_note_body(note) == body

    def test_a_stale_digest_falls_back_to_clean(self) -> None:
        stale = _rendering("assessment", input_digest=text_digest("other"))
        note = _note(style="own_voice", style_renderings=(stale,))
        assert render_note(note, "own_voice") == CLEAN_BODY

    def test_a_failed_rendering_carries_no_prose_and_falls_back_to_clean(self) -> None:
        failed = _rendering("assessment", prose_text="", verdict="failed")
        assert failed.prose_text == ""
        note = _note(style="own_voice", style_renderings=(failed,))
        assert render_note(note, "own_voice") == CLEAN_BODY

    def test_usable_rendering_answers_for_each_case(self) -> None:
        assessment = _sections()[1]
        good = _rendering("assessment")
        note = _note(style="own_voice", style_renderings=(good,))
        assert usable_rendering(note, assessment) == good
        # No rendering for the other sections.
        assert usable_rendering(note, _sections()[0]) is None

        stale = _rendering("assessment", input_digest=text_digest("other"))
        assert usable_rendering(_note(style_renderings=(stale,)), assessment) is None

        failed = _rendering("assessment", prose_text="", verdict="failed")
        assert usable_rendering(_note(style_renderings=(failed,)), assessment) is None

        assert usable_rendering(_note(), assessment) is None


class TestPrefilledMarkInProse:
    def test_a_prose_section_holding_a_prefilled_line_carries_the_section_mark(
        self,
    ) -> None:
        """Codex round 22 PR-MED-035 (D5): a pre-filled line dissolved into a
        paragraph cannot carry its per-line mark, so the prose block carries
        a SECTION-level count built from the same `PREFILLED_MARK`; a prose
        section with no pre-filled line carries none; display, `note.enc`
        reload and Copy share the one rendering path."""
        note = _note(
            style="narrative",
            style_renderings=(
                _rendering("assessment"),
                _rendering("treatment_performed", prose_text="An ice pack was advised."),
            ),
        )
        body = render_note(note, "narrative")
        assert (
            "Treatment performed\nAn ice pack was advised.\n"
            f"[includes 1 line {PREFILLED_MARK}]"
        ) in body
        assert "Assessment\nCervical HVLA was performed.\n\n" in body
        assert body.count(PREFILLED_MARK) == 1
        reloaded = GeneratedNote.from_bytes(note.to_bytes())
        assert models.format_note_body(reloaded) == body
        # Invented-text guard D5: `section_marks_line` replaced
        # `prefilled_section_mark`, the same text for pre-filled lines alone.
        marks = note_module.line_marks_by_assertion(note)
        assert note_module.section_marks_line(note.note_sections[1], marks) is None
        assert note_module.section_marks_line(note.note_sections[2], marks) == (
            f"[includes 1 line {PREFILLED_MARK}]"
        )


def _line_warning(code: str, aid: str = "q0") -> NoteWarning:
    """A per-line check code (invented-text guard D5) on ``aid``."""
    return NoteWarning(note_warning_code=code, severity="review", assertion_id=aid)


_BOTH_MARKS = (_line_warning("number_source"), _line_warning("suspect_source"))
_NUMBERED_TEXT = "two sessions a week"


class TestCheckMarks:
    """Invented-text guard D5 and decision 0.5: a quoted line carrying
    ``number_source`` / ``suspect_source`` renders its check marks by the
    pre-filled mark's convention; Copy (``check_marks=False``) leaves them
    out and keeps the pre-filled mark; the Cliniko body stays bare."""

    def test_clean_puts_each_mark_after_the_line_in_code_order(self) -> None:
        body = render_note(_note(warnings=_BOTH_MARKS), "clean")
        assert body.split("\n\n")[0] == (
            "Presenting complaint\n"
            "the numbness is worse at night  [check: number]  [check: possibly not speech]"
        )
        # The pre-filled line beside it is byte-identical.
        assert body.split("\n\n")[1:] == CLEAN_BODY.split("\n\n")[1:]

    def test_verbatim_prefixes_the_marks_to_the_provenance_label(self) -> None:
        body = render_note(_note(warnings=_BOTH_MARKS), "verbatim")
        assert body.split("\n\n")[0] == (
            "Presenting complaint:\n"
            "  - the numbness is worse at night  "
            "[check: number - check: possibly not speech - from transcript]"
        )
        assert body.split("\n\n")[1:] == VERBATIM_BODY.split("\n\n")[1:]

    def test_one_mark_alone(self) -> None:
        note = _note(warnings=(_line_warning("suspect_source"),))
        assert render_note(note, "clean").startswith(
            "Presenting complaint\nthe numbness is worse at night  [check: possibly not speech]\n"
        )

    @staticmethod
    def _prose_note(*, prefilled: bool = True) -> GeneratedNote:
        """A ``narrative`` note whose treatment section holds a quoted
        numbered line (``number_source``) and, with ``prefilled``, a
        pre-filled line, under a passed prose rendering."""
        numbered = _quoted("q1", "treatment_performed", 2, _NUMBERED_TEXT, SPEAKER_1)
        treatment = GeneratedSection(
            section_key="treatment_performed",
            note_assertions=(_config_decided(), numbered) if prefilled else (numbered,),
        )
        sections = (_sections()[0], _sections()[1], treatment)
        rendering = StyleRendering(
            section_key="treatment_performed",
            prose_text="An ice pack and two sessions a week.",
            input_digest=section_input_digest(treatment),
            verdict="passed",
        )
        return _note(
            style="narrative",
            sections=sections,
            style_renderings=(rendering,),
            warnings=(_line_warning("number_source", "q1"),),
        )

    def test_a_prose_section_counts_its_marks_beside_the_prefilled_count(self) -> None:
        note = self._prose_note()
        body = render_note(note, "narrative")
        assert body.endswith(
            "Treatment performed\nAn ice pack and two sessions a week.\n"
            f"[includes 1 line {PREFILLED_MARK}; 1 line check: number]"
        )
        # Copy keeps the pre-filled count and drops the check count.
        assert render_note(note, "narrative", check_marks=False).endswith(
            f"two sessions a week.\n[includes 1 line {PREFILLED_MARK}]"
        )

    def test_copy_leaves_out_the_check_marks_and_keeps_the_prefilled_mark(self) -> None:
        note = _note(warnings=_BOTH_MARKS)
        assert render_note(note, "verbatim", check_marks=False) == VERBATIM_BODY
        assert render_note(note, "clean", check_marks=False) == CLEAN_BODY
        # The fixture note's own style is verbatim: there the marks prefix the
        # provenance label inside ONE bracket (D5 — the pre-filled mark's
        # convention); Clean gives each its own bracket (above).
        copied = models.format_note_body(note, check_marks=False)
        assert "check:" not in copied
        assert PREFILLED_MARK in copied
        assert "[check: number - check: possibly not speech - from transcript]" in (
            models.format_note_body(note)
        )

    def test_a_selection_never_carries_a_mark_in_any_style(self) -> None:
        """Hardening round 15 LOW-008: the note panel's selection copy
        (``models.unmarked_selection``) over the REAL renderings — Clean and
        Verbatim with both marks beside a pre-filled line, a prose section
        whose marks line holds a check count with and without a pre-filled
        count: the whole selection is the Copy rendering, and every selection
        from the start or to the end is a piece of it with no check mark."""
        cases = [(_note(warnings=_BOTH_MARKS), style) for style in ("clean", "verbatim")]
        cases += [(self._prose_note(prefilled=p), "narrative") for p in (True, False)]
        for note, style in cases:
            shown = render_note(note, style)
            bare = render_note(note, style, check_marks=False)
            assert shown != bare, style
            assert models.unmarked_selection(shown, bare, 0, len(shown)) == bare, style
            for cut in range(len(shown) + 1):
                for start, end in ((0, cut), (cut, len(shown))):
                    text = models.unmarked_selection(shown, bare, start, end)
                    assert text is not None, (style, start, end)
                    assert "check:" not in text and text in bare, (style, start, end)

    def test_a_selection_of_only_a_prose_marks_line_copies_nothing(self) -> None:
        """Hardening round 15 LOW-008: the marks line and its line break hold
        no note text, so nothing is copied (the panel then says so) — never a
        bare line break placed in silence."""
        note = self._prose_note(prefilled=False)
        shown = render_note(note, "narrative")
        bare = render_note(note, "narrative", check_marks=False)
        start = shown.index("[includes 1 line check: number]")
        end = start + len("[includes 1 line check: number]")
        assert models.unmarked_selection(shown, bare, start, end) == ""
        if end < len(shown):  # the line break after it, when one follows
            assert models.unmarked_selection(shown, bare, start, end + 1) == ""
        assert models.unmarked_selection(shown, bare, start - 1, end) == ""

    def test_the_cliniko_body_is_bare(self) -> None:
        note = _note(warnings=_BOTH_MARKS)
        lines = note_module.render_section_lines(
            note, note.note_sections[0], "verbatim", apparatus=False
        )
        assert lines == [PATIENT_SYMPTOM]

    def test_the_marks_survive_a_reload_and_reach_the_rendered_assertion(self) -> None:
        note = _note(warnings=_BOTH_MARKS)
        reloaded = GeneratedNote.from_bytes(note.to_bytes())
        assert render_note(reloaded, "clean") == render_note(note, "clean")
        rendered = models.render_note_sections(note)
        quoted = rendered[0].assertions[0]
        assert quoted.marks == ("check: number", "check: possibly not speech")
        assert quoted.provenance_label == (
            "check: number - check: possibly not speech - from transcript"
        )
        prefilled = rendered[2].assertions[0]
        assert prefilled.marks == (PREFILLED_MARK,)
        assert prefilled.prefilled is True

    def test_a_note_without_check_codes_renders_exactly_as_before(self) -> None:
        assert note_module.line_marks_by_assertion(_note()) == {"autofill-1": (PREFILLED_MARK,)}
        assert render_note(_note(), "verbatim") == VERBATIM_BODY


class TestSectionInputDigest:
    def _section(self, *texts: str) -> GeneratedSection:
        return GeneratedSection(
            section_key="presenting_complaint",
            note_assertions=tuple(
                _quoted(f"q{index}", "presenting_complaint", index, text, SPEAKER_1)
                for index, text in enumerate(texts)
            ),
        )

    def test_order_and_content_both_change_the_digest(self) -> None:
        first = section_input_digest(self._section("one line here", "another line here"))
        reordered = section_input_digest(self._section("another line here", "one line here"))
        shorter = section_input_digest(self._section("one line here"))
        assert first != reordered
        assert first != shorter
        assert reordered != shorter
        assert first == section_input_digest(self._section("one line here", "another line here"))


# ---------------------------------------------------------------------------
# Cliniko draft-write plan, Task 3.1 (D7): ``render_note`` must stay byte for
# byte what it was when ``render_section_lines`` took over its blocks. The
# reference below is a VERBATIM copy of ``note.py``'s renderer as it stood
# before Task 3.1 touched it (``_verbatim_block`` / ``_clean_lines`` /
# ``_clean_block`` / ``_prose_block`` / ``render_note`` at :915-991), captured
# before the edit and never to be changed with the renderer: Copy's text is
# pinned against it for the ten ``scripts/measure-prose-fixtures.py`` notes
# plus this module's three-line-kind note, in all four styles, the prose legs
# with ``style_renderings`` present (passed, failed and absent sections).
# What this oracle pins is the COMPOSITION (the blocks, their order and their
# joins); the reference still calls the live helpers ``assertion_label``,
# ``is_prefilled``, ``usable_rendering`` and ``section_marks_line``, which
# are pinned literally elsewhere — ``VERBATIM_BODY`` / ``CLEAN_BODY`` above and
# the prose-stage tests. [2026-10-12, invented-text guard D5: the reference
# learned the marks — each line's marks come from ``line_marks_by_assertion``
# (the pre-filled mark, unchanged for a note with no check code, and the
# check marks), and ``section_marks_line`` replaced ``prefilled_section_mark``.
# The composition is unchanged; the check marks are pinned literally in
# ``TestCheckMarks`` above.]
# ---------------------------------------------------------------------------


def _reference_verbatim_block(
    section: GeneratedSection, marks: dict[str, tuple[str, ...]]
) -> str:
    lines = [f"{note_module.SECTION_TITLES[section.section_key]}:"]
    for assertion in section.note_assertions:
        label = note_module.assertion_label(assertion, marks.get(assertion.assertion_id, ()))
        lines.append(f"  - {assertion.text}  [{label}]")
    return "\n".join(lines)


def _reference_clean_lines(
    section: GeneratedSection, marks: dict[str, tuple[str, ...]]
) -> list[str]:
    lines: list[str] = []
    for assertion in section.note_assertions:
        text = assertion.text
        for mark in marks.get(assertion.assertion_id, ()):
            text = f"{text}  [{mark}]"
        lines.append(text)
    return lines


def _reference_clean_block(
    section: GeneratedSection, marks: dict[str, tuple[str, ...]]
) -> str:
    return "\n".join(
        [note_module.SECTION_TITLES[section.section_key], *_reference_clean_lines(section, marks)]
    )


def _reference_prose_block(
    note: GeneratedNote, section: GeneratedSection, marks: dict[str, tuple[str, ...]]
) -> str:
    rendering = usable_rendering(note, section)
    if rendering is None:
        return _reference_clean_block(section, marks)
    lines = [note_module.SECTION_TITLES[section.section_key], rendering.prose_text]
    mark = note_module.section_marks_line(section, marks)
    if mark is not None:
        lines.append(mark)
    return "\n".join(lines)


def _reference_render_note(note: GeneratedNote, style: NoteStyle) -> str:
    marks = note_module.line_marks_by_assertion(note)
    blocks: list[str] = []
    for section in note.note_sections:
        if style == "verbatim":
            blocks.append(_reference_verbatim_block(section, marks))
        elif style == "clean":
            blocks.append(_reference_clean_block(section, marks))
        else:
            blocks.append(_reference_prose_block(note, section, marks))
    if not blocks:
        return NO_NOTE_CONTENT
    return "\n\n".join(blocks)


def _with_prose_renderings(note: GeneratedNote) -> GeneratedNote:
    """``note`` carrying a rendering for every populated section but the
    last: a two-paragraph PASSED rendering (a newline inside the prose) for
    even positions, a FAILED one for odd positions — so the prose legs
    exercise a usable rendering, a failed one and an absent one."""
    renderings = []
    populated = [section for section in note.note_sections if section.note_assertions]
    for position, section in enumerate(populated[:-1]):
        digest = section_input_digest(section)
        if position % 2 == 0:
            texts = "; ".join(assertion.text for assertion in section.note_assertions)
            renderings.append(
                StyleRendering(
                    section_key=section.section_key,
                    prose_text=f"{texts}.\nA second paragraph.",
                    input_digest=digest,
                    verdict="passed",
                )
            )
        else:
            renderings.append(
                StyleRendering(
                    section_key=section.section_key,
                    prose_text="",
                    input_digest=digest,
                    verdict="failed",
                )
            )
    return note.model_copy(update={"style_renderings": tuple(renderings)})


def _pinned_notes() -> list[GeneratedNote]:
    notes = [prose_fixture_note(sections, style="clean") for sections in FIXTURE_NOTES]
    notes.append(_note())
    # The three-line-kind note with a passed rendering on the PRE-FILLED
    # section, so the prose legs carry the section-level mark.
    notes.append(
        _note(
            style_renderings=(
                _rendering("assessment"),
                _rendering("treatment_performed", prose_text="An ice pack was advised."),
            )
        )
    )
    return notes


class TestRenderNoteUnchangedByTheSectionRenderer:
    def test_every_style_matches_the_pre_task_renderer_for_every_pinned_note(self) -> None:
        notes = _pinned_notes()
        assert len(notes) == 12
        checked = 0
        for base in notes:
            for note in (base, _with_prose_renderings(base)):
                for style in models.NOTE_STYLES:
                    assert render_note(note, style) == _reference_render_note(note, style), (
                        f"note {checked} style {style}"
                    )
                    checked += 1
        assert checked == 12 * 2 * len(models.NOTE_STYLES)
        assert set(models.NOTE_STYLES) == {"verbatim", "clean", "own_voice", "narrative"}

    def test_the_pinned_prose_legs_really_carry_a_usable_rendering(self) -> None:
        """Guards the pin itself: without a usable rendering the prose legs
        would only re-test ``clean``."""
        note = _with_prose_renderings(_pinned_notes()[0])
        body = render_note(note, "narrative")
        assert "A second paragraph." in body
        assert body != render_note(note, "clean")


class TestRenderSectionLines:
    """Task 3.1 (D7): the per-section renderer with and without the review
    apparatus."""

    def _prose_note(self) -> GeneratedNote:
        return _note(
            style="narrative",
            style_renderings=(
                _rendering("assessment", prose_text="Line one.\nLine two."),
                _rendering("treatment_performed", prose_text="An ice pack was advised."),
            ),
        )

    def test_with_apparatus_the_lines_are_the_blocks_body_without_its_title(self) -> None:
        for note in (_note(), self._prose_note()):
            for style in models.NOTE_STYLES:
                for section in note.note_sections:
                    lines = note_module.render_section_lines(note, section, style, apparatus=True)
                    title = note_module.SECTION_TITLES[section.section_key]
                    heading = f"{title}:" if style == "verbatim" else title
                    assert "\n".join([heading, *lines]) in render_note(note, style)
                    assert title not in lines

    def test_without_apparatus_no_title_mark_tag_bullet_or_includes_line(self) -> None:
        for note in (_note(), self._prose_note()):
            for style in models.NOTE_STYLES:
                for section in note.note_sections:
                    lines = note_module.render_section_lines(
                        note, section, style, apparatus=False
                    )
                    assert lines, (style, section.section_key)
                    text = "\n".join(lines)
                    assert note_module.SECTION_TITLES[section.section_key] not in lines
                    assert PREFILLED_MARK not in text
                    assert "[includes" not in text
                    assert "  - " not in text
                    for label in note_module.PROVENANCE_LABELS.values():
                        assert f"[{label}]" not in text

    def test_verbatim_without_apparatus_is_the_clean_lines(self) -> None:
        note = _note()
        for section in note.note_sections:
            assert note_module.render_section_lines(
                note, section, "verbatim", apparatus=False
            ) == [assertion.text for assertion in section.note_assertions]
        prefilled = note.note_sections[2]
        assert note_module.render_section_lines(note, prefilled, "clean", apparatus=False) == [
            PREFILLED_TEXT
        ]

    def test_prose_without_apparatus_splits_the_rendering_and_drops_the_section_mark(
        self,
    ) -> None:
        note = self._prose_note()
        assessment, treatment = note.note_sections[1], note.note_sections[2]
        assert note_module.render_section_lines(
            note, assessment, "narrative", apparatus=False
        ) == ["Line one.", "Line two."]
        assert note_module.render_section_lines(
            note, treatment, "narrative", apparatus=False
        ) == ["An ice pack was advised."]
        assert note_module.render_section_lines(
            note, treatment, "narrative", apparatus=True
        ) == ["An ice pack was advised.", f"[includes 1 line {PREFILLED_MARK}]"]

    def test_a_prose_section_without_a_usable_rendering_falls_back_to_clean_lines(
        self,
    ) -> None:
        failed = _rendering("assessment", prose_text="", verdict="failed")
        note = _note(style="own_voice", style_renderings=(failed,))
        assessment = note.note_sections[1]
        assert note_module.render_section_lines(
            note, assessment, "own_voice", apparatus=False
        ) == [TYPED_TEXT]

    def test_an_empty_section_renders_no_lines(self) -> None:
        empty = GeneratedSection(section_key="diagnosis")
        note = _note(sections=(empty,))
        for style in models.NOTE_STYLES:
            for apparatus in (True, False):
                assert (
                    note_module.render_section_lines(note, empty, style, apparatus=apparatus)
                    == []
                )


class TestModelsReExports:
    def test_the_marks_and_labels_are_the_note_modules_own(self) -> None:
        assert models.PREFILLED_MARK is note_module.PREFILLED_MARK
        assert PREFILLED_MARK == "pre-filled by your config"
        assert models.provenance_label("clinician") == "typed (clinician-authored)"

    def test_render_note_sections_flags_the_config_decided_line(self) -> None:
        rendered = models.render_note_sections(_note())
        assert [section.section_key for section in rendered] == [
            "presenting_complaint",
            "assessment",
            "treatment_performed",
        ]
        assert [section.title for section in rendered] == [
            "Presenting complaint",
            "Assessment",
            "Treatment performed",
        ]
        flags = [section.assertions[0].prefilled for section in rendered]
        assert flags == [False, False, True]
        assert rendered[2].assertions[0].provenance_label == (
            f"{PREFILLED_MARK} - autofill (clinician-authored)"
        )
        assert rendered[1].assertions[0].provenance_label == "typed (clinician-authored)"
