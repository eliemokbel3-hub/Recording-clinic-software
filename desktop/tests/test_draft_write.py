"""Cliniko draft-write plan, Task 3.1 (D7): the rendering half of
``draft_write`` — ``render_targets`` and ``to_cliniko_answer``.

What is pinned here:
- ``render_targets`` groups the note's apparatus-free lines by the template
  target each section maps to; a target the profile maps several sections to
  gets one ``SECTION_TITLES`` heading line per contributing section, a
  target only one section maps to gets none; an unmapped section, an empty
  section and the attestation target contribute nothing.
- ``to_cliniko_answer``: rich text is one ``<p>`` per line, ``& < > " '``
  escaped (``a<b&c`` -> ``<p>a&lt;b&amp;c</p>``), non-ASCII kept, no tag but
  ``<p>`` / ``<br>``, a whitespace-only line an empty paragraph; plain text
  is the lines joined by newlines, never escaped; an attestation is refused,
  and so are a bare string and a line holding a line break.

The profile is the SHIPPED Template A profile, read from the package's
``config_defaults`` directly — never through the ``%LOCALAPPDATA%`` loader.
"""

from __future__ import annotations

import json
import re
from importlib import resources

import pytest

from scribe_desktop import draft_write
from scribe_desktop.note import (
    CANONICAL_SECTION_KEYS,
    PREFILLED_MARK,
    SECTION_TITLES,
    GeneratedNote,
    GeneratedSection,
    NoteSectionKey,
    StyleRendering,
    section_input_digest,
)
from scribe_desktop.note_config import SectionMapping, TargetType, TemplateProfile
from scribe_desktop.transcription import SPEAKER_1
from scribe_desktop.ui import models
from test_note_render import _config_decided, _note, _quoted


def _template_a() -> TemplateProfile:
    raw = (
        resources.files("scribe_desktop")
        .joinpath("config_defaults/template_profiles.json")
        .read_text(encoding="utf-8")
    )
    (profile,) = json.loads(raw)["template_profiles"]
    return TemplateProfile.model_validate(profile)


def _section(key: NoteSectionKey, *texts: str, start: int = 0) -> GeneratedSection:
    return GeneratedSection(
        section_key=key,
        note_assertions=tuple(
            _quoted(f"{key}-{index}", key, start + index, text, SPEAKER_1)
            for index, text in enumerate(texts)
        ),
    )


def _every_section_note() -> GeneratedNote:
    """A note populating all 17 canonical sections (consent included), one
    line each, named after its section."""
    return _note(
        sections=tuple(
            _section(key, f"line for {key}", start=index)
            for index, key in enumerate(CANONICAL_SECTION_KEYS)
        )
    )


class TestRenderTargets:
    def test_the_attestation_and_the_unmapped_consent_section_never_appear(self) -> None:
        profile = _template_a()
        note = _every_section_note()
        for style in models.NOTE_STYLES:
            targets = draft_write.render_targets(note, profile, style)
            assert "informed-consent" not in targets
            assert all(t.target_type != "attestation_checkbox" for t, _ in targets.values())
            assert set(targets) == {
                "presenting-progress",
                "assessment",
                "diagnosis",
                "treatment",
                "response-to-treatment",
                "management-advice",
            }
            rendered = "\n".join(line for _, lines in targets.values() for line in lines)
            assert "line for consent" not in rendered

    def test_an_attestation_target_is_filtered_even_when_a_profile_maps_to_it(
        self,
    ) -> None:
        """Round 16: the profile validator already refuses such a mapping, so
        this bypasses it (``model_copy`` does not validate) to reach the
        second filter the module docstring claims."""
        profile = _template_a()
        (attestation,) = (
            t for t in profile.template_targets if t.target_type == "attestation_checkbox"
        )
        mapped = profile.model_copy(
            update={
                "section_mappings": (
                    *profile.section_mappings,
                    SectionMapping(section_key="consent", target_id=attestation.target_id),
                )
            }
        )
        assert mapped.target_for("consent") == attestation
        targets = draft_write.render_targets(_every_section_note(), mapped, "clean")
        assert attestation.target_id not in targets
        rendered = "\n".join(line for _, lines in targets.values() for line in lines)
        assert "line for consent" not in rendered

    def test_a_five_section_target_gets_five_headings_and_a_one_section_target_none(
        self,
    ) -> None:
        targets = draft_write.render_targets(_every_section_note(), _template_a(), "clean")
        target, lines = targets["assessment"]
        assert target.field_label == "Assessment"
        folded = (
            "red_flags_screening",
            "objective_examination",
            "outcome_measures",
            "assessment",
            "precautions_contraindications",
        )
        expected: list[str] = []
        for key in CANONICAL_SECTION_KEYS:
            if key in folded:
                expected += [SECTION_TITLES[key], f"line for {key}"]
        assert lines == expected
        assert sum(1 for line in lines if line in SECTION_TITLES.values()) == 5
        assert targets["diagnosis"][1] == ["line for diagnosis"]
        assert targets["treatment"][1] == ["line for treatment_performed"]

    def test_a_shared_target_keeps_its_heading_when_only_one_of_its_sections_has_lines(
        self,
    ) -> None:
        """The heading follows the PROFILE's sharing, not how many sections
        this note happens to populate."""
        note = _note(sections=(_section("history_presenting_complaint", "Neck pain"),))
        targets = draft_write.render_targets(note, _template_a(), "clean")
        assert targets == {
            "presenting-progress": (
                targets["presenting-progress"][0],
                [SECTION_TITLES["history_presenting_complaint"], "Neck pain"],
            )
        }

    def test_a_line_break_inside_a_rendered_line_becomes_lines_the_answer_accepts(
        self,
    ) -> None:
        """Round 17 PR-MED-029: the note's types admit a line break inside an
        assertion or a passed rendering (LF, CRLF, CR). The grouper splits it
        into lines, blank lines kept, so the composition renderer -> grouper
        -> answer never raises on validated note data."""
        section = _section("diagnosis", "Left\r\nshoulder\rstrain\nsuspected")
        rendering = StyleRendering(
            section_key="diagnosis",
            prose_text="First.\r\nSecond.\rThird.\n\nFourth.",
            input_digest=section_input_digest(section),
            verdict="passed",
        )
        note = _note(sections=(section,))
        prose = note.model_copy(update={"style_renderings": (rendering,)})
        clean = draft_write.render_targets(note, _template_a(), "clean")["diagnosis"][1]
        assert clean == ["Left", "shoulder", "strain", "suspected"]
        narrative = draft_write.render_targets(prose, _template_a(), "narrative")["diagnosis"][1]
        assert narrative == ["First.", "Second.", "Third.", "", "Fourth."]
        for lines in (clean, narrative):
            assert "\n" not in draft_write.to_cliniko_answer(lines, "rich_text")
            assert draft_write.to_cliniko_answer(lines, "plain_text") == "\n".join(lines)
        assert draft_write.to_cliniko_answer(narrative, "rich_text") == (
            "<p>First.</p><p>Second.</p><p>Third.</p><p><br></p><p>Fourth.</p>"
        )

    def test_a_trailing_line_break_keeps_its_blank_line(self) -> None:
        """Round 18 PR-LOW-031: an assertion ENDING in a break keeps the blank
        line after it — the blank line Copy shows before the next one — in
        both line-break kinds, and at the section's end too."""
        section = _section("diagnosis", "First.\n", "Second.", "Third.\r\n")
        lines = draft_write.render_targets(_note(sections=(section,)), _template_a(), "clean")[
            "diagnosis"
        ][1]
        assert lines == ["First.", "", "Second.", "Third.", ""]
        assert draft_write.to_cliniko_answer(lines, "rich_text") == (
            "<p>First.</p><p><br></p><p>Second.</p><p>Third.</p><p><br></p>"
        )

    def test_the_targets_are_in_the_order_the_note_first_reaches_them(self) -> None:
        targets = draft_write.render_targets(_every_section_note(), _template_a(), "clean")
        assert list(targets) == [
            "presenting-progress",
            "assessment",
            "diagnosis",
            "treatment",
            "response-to-treatment",
            "management-advice",
        ]

    def test_empty_and_unmapped_sections_contribute_nothing(self) -> None:
        note = _note(
            sections=(
                _section("presenting_complaint", "Neck pain"),
                GeneratedSection(section_key="diagnosis"),
                _section("consent", "Consent given", start=5),
            )
        )
        targets = draft_write.render_targets(note, _template_a(), "clean")
        assert list(targets) == ["presenting-progress"]
        assert draft_write.render_targets(_note(sections=()), _template_a(), "clean") == {}

    def test_the_lines_carry_no_review_apparatus_in_any_style(self) -> None:
        note = _note(
            sections=(
                _section("presenting_complaint", "Neck pain"),
                GeneratedSection(
                    section_key="treatment_performed", note_assertions=(_config_decided(),)
                ),
            )
        )
        treatment = note.note_sections[1]
        rendering = StyleRendering(
            section_key="treatment_performed",
            prose_text="An ice pack was advised.",
            input_digest=section_input_digest(treatment),
            verdict="passed",
        )
        prose = note.model_copy(update={"style_renderings": (rendering,)})
        for candidate in (note, prose):
            for style in models.NOTE_STYLES:
                targets = draft_write.render_targets(candidate, _template_a(), style)
                text = "\n".join(line for _, lines in targets.values() for line in lines)
                assert PREFILLED_MARK not in text
                assert "[includes" not in text
                assert "  - " not in text
                assert "[from transcript]" not in text
                assert "Neck pain" in text
        assert draft_write.render_targets(prose, _template_a(), "narrative")["treatment"][1] == [
            "An ice pack was advised."
        ]


class TestToClinikoAnswer:
    def test_rich_text_escapes_the_markup_characters(self) -> None:
        assert draft_write.to_cliniko_answer(["a<b&c"], "rich_text") == "<p>a&lt;b&amp;c</p>"
        assert (
            draft_write.to_cliniko_answer(['say "no" & it\'s <b>fine</b>'], "rich_text")
            == "<p>say &quot;no&quot; &amp; it&#x27;s &lt;b&gt;fine&lt;/b&gt;</p>"
        )

    def test_rich_text_is_one_paragraph_per_line_and_keeps_non_ascii(self) -> None:
        answer = draft_write.to_cliniko_answer(
            ["Café — ß über", "", "Second"], "rich_text"
        )
        assert answer == "<p>Café — ß über</p><p><br></p><p>Second</p>"

    def test_rich_text_emits_no_tag_but_p_and_br(self) -> None:
        answer = draft_write.to_cliniko_answer(
            ["<script>x</script>", "<a href='y'>z</a>", "", "<br>", "plain"], "rich_text"
        )
        tags = set(re.findall(r"</?([A-Za-z][A-Za-z0-9]*)", answer))
        assert tags == {"p", "br"}
        assert answer.count("<br>") == 1

    def test_plain_text_joins_lines_and_never_escapes(self) -> None:
        assert draft_write.to_cliniko_answer(["a<b&c", "Café"], "plain_text") == "a<b&c\nCafé"
        assert draft_write.to_cliniko_answer([], "plain_text") == ""

    def test_an_attestation_is_never_answered(self) -> None:
        with pytest.raises(ValueError, match="attestation"):
            draft_write.to_cliniko_answer(["ticked"], "attestation_checkbox")

    def test_a_whitespace_only_line_is_an_empty_paragraph(self) -> None:
        assert draft_write.to_cliniko_answer(["a", "   ", "\t", "b"], "rich_text") == (
            "<p>a</p><p><br></p><p><br></p><p>b</p>"
        )

    @pytest.mark.parametrize("target_type", ["rich_text", "plain_text"])
    def test_lines_must_be_lines(self, target_type: TargetType) -> None:
        """Round 16: a bare string would be one paragraph per character, and a
        line break inside a line would lose a paragraph inside one ``<p>``."""
        with pytest.raises(ValueError, match="sequence of lines"):
            draft_write.to_cliniko_answer("one string", target_type)
        for line in ("first\nsecond", "first\rsecond", "first\r\nsecond"):
            with pytest.raises(ValueError, match="line break"):
                draft_write.to_cliniko_answer([line], target_type)
