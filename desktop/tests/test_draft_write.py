"""Cliniko draft-write plan, Tasks 3.1–3.4: ``draft_write``.

Task 3.1 (D7), the rendering half — ``render_targets`` and
``to_cliniko_answer``. What is pinned here:
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

Tasks 3.2–3.4 (D3–D5, D14), the decision: normalised comparison, the
name-based template match, the clinic's declared defaults (Option A, the
template's own answer; Option C, the practitioner's file — handed in
already loaded), the typed-text check, the FULL body, the write record's
model and reconcile, ``prepare_write``'s order, hop 1's reads and hop 2's
classification. Every Cliniko answer is P.1-shaped (clinic 1's "Standard
Consultation": three sections, every writable question ``paragraph``, one
checkboxes question) and comes from a fake transport — no socket, ever —
and every key from an in-memory store. The writable profile here is
Template A with every target ``rich_text`` (what P.1 found, and what the
shipped profile declares since the Phase 3 correction — pinned against P.1's
shape in ``TestTemplateMatch``), plus one synthetic ``text`` question for
the plain-text path, which other clinics' templates may need.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import replace
from datetime import timedelta
from importlib import resources
from pathlib import Path
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from encounter_fakes import (
    BOOKING_BODY,
    NOTE,
    NOW,
    OTHER_HOST,
    PATIENT,
    PATIENT_BODY,
    TEMPLATE,
    MemoryKeyStore,
    consent_for,
    make_registry,
    note_body,
    ok,
    request_for,
    status,
)
from encounter_fakes import context as enc_context
from encounter_fakes import target as note_target
from scribe_desktop import cliniko_client as cc
from scribe_desktop import draft_write, encounter, note_config
from scribe_desktop.clinics import KEY_SECRET_NAME, ClinicRegistry
from scribe_desktop.encounter import (
    NoteDisplay,
    NoteRefusal,
    NoteRefused,
    UnverifiedOffline,
    VerificationResult,
    Verified,
    VerifiedTarget,
    WritebackRefusal,
    WritebackRefused,
)
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
from scribe_desktop.note_config import (
    OwnDefaults,
    OwnDefaultsProblem,
    SectionMapping,
    TargetType,
    TemplateProfile,
)
from scribe_desktop.transcription import SPEAKER_1
from scribe_desktop.ui import models
from test_note_render import _config_decided, _note, _quoted


@pytest.fixture(autouse=True)
def _no_config_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """``draft_write`` never reads the disk: any reach for the config root
    (``%LOCALAPPDATA%``) fails the test."""

    def refuse() -> Path:
        raise AssertionError("draft_write must never reach the config root")

    monkeypatch.setattr(note_config, "default_config_root", refuse)


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


# ---------------------------------------------------------------------------
# Tasks 3.2–3.4: P.1-shaped fixtures.
# ---------------------------------------------------------------------------

_HISTORY = "Presenting complaint/patient progress"
_LAYOUT: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("History", (_HISTORY,)),
    ("Examination", ("Assessment", "Informed Consent", "Diagnosis")),
    ("Treatment/Management", ("Treatment", "Response to treatment", "Management/Advice")),
)
# The template's default for the History question, and the SAME visible text
# as a new note carries it — a different HTML representation (P.1 Q1: the
# sanitiser rewrites; comparison is over normalised visible text).
_TEMPLATE_DEFAULT = "<p>Site -</p><p>Chron -</p><p>Agg -</p>"
_NOTE_DEFAULT = "<p>Site -</p>\n<p>Chron -&nbsp; </p>\n<p>Agg -</p>"
_IDENTITY = hashlib.sha256(b"the saved note.enc plaintext").hexdigest()
_OTHER_IDENTITY = hashlib.sha256(b"another saved note").hexdigest()
_API = "https://api.au2.cliniko.com/v1"


def _sections(
    answers: Mapping[str, object], types: Mapping[str, str], *, template: bool
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for section_name, question_names in _LAYOUT:
        questions: list[dict[str, Any]] = []
        for name in question_names:
            if name == "Informed Consent":
                if template:
                    questions.append(
                        {"name": name, "type": "checkboxes", "choices": [{"value": "Given"}]}
                    )
                else:
                    questions.append(
                        {
                            "name": name,
                            "type": "checkboxes",
                            "answers": [{"value": "Given", "selected": True}],
                        }
                    )
                continue
            question: dict[str, Any] = {"name": name, "type": types.get(name, "paragraph")}
            if name in answers:
                question["answer"] = answers[name]
            questions.append(question)
        sections.append({"name": section_name, "questions": questions})
    return sections


def _template(
    answers: Mapping[str, object] | None = None,
    types: Mapping[str, str] | None = None,
    *,
    name: object = "Standard Consultation",
) -> dict[str, Any]:
    answers = {_HISTORY: _TEMPLATE_DEFAULT} if answers is None else answers
    return {
        "id": TEMPLATE,
        "name": name,
        "content": {"sections": _sections(answers, types or {}, template=True)},
    }


def _content(
    answers: Mapping[str, object] | None = None, types: Mapping[str, str] | None = None
) -> dict[str, Any]:
    answers = {_HISTORY: _NOTE_DEFAULT} if answers is None else answers
    return {
        "sections": _sections(answers, types or {}, template=False),
        "future_key": {"kept": True},
    }


def _profile(types: Mapping[str, TargetType] | None = None) -> TemplateProfile:
    """Template A with every writable target ``rich_text`` (P.1: every
    writable question in clinic 1's template is ``paragraph``), unless
    ``types`` says otherwise by target id."""
    raw = _template_a().model_dump()
    for target in raw["template_targets"]:
        if target["target_type"] != "attestation_checkbox":
            target["target_type"] = (types or {}).get(target["target_id"], "rich_text")
    return TemplateProfile.model_validate(raw)


def _write_note(**update: Any) -> GeneratedNote:
    note = _note(
        sections=(
            _section("presenting_complaint", "Neck pain for two weeks"),
            _section("diagnosis", "Left shoulder strain", start=1),
            _section("treatment_performed", "Soft tissue massage", start=2),
        )
    )
    return note.model_copy(update=update) if update else note


def _answers(note: GeneratedNote, profile: TemplateProfile) -> dict[str, str]:
    return {
        target_id: draft_write.to_cliniko_answer(lines, target.target_type)
        for target_id, (target, lines) in draft_write.render_targets(
            note, profile, note.style
        ).items()
    }


def _registry(tmp_path: Path) -> tuple[ClinicRegistry, MemoryKeyStore]:
    store = MemoryKeyStore()
    return make_registry(tmp_path, storage=store), store


def _verified_hop1(
    registry: ClinicRegistry,
    *,
    content: object = None,
    template: Mapping[str, Any] | None = None,
    matches: bool = True,
) -> draft_write.Hop1Result:
    outcome = Verified(enc_context(), NoteDisplay("", None))
    return draft_write.Hop1Result(
        VerificationResult(request_for(registry), outcome),
        template=_template() if template is None else template,
        content=_content() if content is None else content,
        template_matches=matches,
    )


def _refused_hop1(registry: ClinicRegistry, outcome: Any) -> draft_write.Hop1Result:
    return draft_write.Hop1Result(VerificationResult(request_for(registry), outcome))


_UNSET: Any = object()


def _prepare(
    registry: ClinicRegistry,
    hop1: draft_write.Hop1Result | None = None,
    *,
    record: draft_write.WriteRecord | draft_write.RecordUnreadable | None = None,
    note: GeneratedNote | None = None,
    identity: str = _IDENTITY,
    profile: TemplateProfile | None = _UNSET,
    source: Any = "cliniko_template",
    own: OwnDefaults | OwnDefaultsProblem | None = None,
    consent: Any = _UNSET,
    context: Any = _UNSET,
) -> draft_write.PreparedWrite | draft_write.AlreadyWritten | draft_write.WriteRefusal:
    ctx = enc_context() if context is _UNSET else context
    return draft_write.prepare_write(
        _verified_hop1(registry) if hop1 is None else hop1,
        consent=consent_for(enc_context()) if consent is _UNSET else consent,
        context=ctx,
        clinics=registry,
        record=record,
        note=_write_note() if note is None else note,
        note_identity=identity,
        profile=_profile() if profile is _UNSET else profile,
        default_source=source,
        own_defaults=own,
    )


def _record(
    outcome: Any = "unknown",
    *,
    refusal: Any = None,
    digests: Mapping[str, str] | None = None,
    identity: str = _IDENTITY,
    attempt: int = 1,
) -> draft_write.WriteRecord:
    digests = {"diagnosis": "0" * 64} if digests is None else digests
    # Written under the default profile's match (what ``_prepare`` binds).
    match = draft_write.match_template(_profile(), _template(), _content())
    assert isinstance(match, draft_write.Match)
    return draft_write.WriteRecord(
        attempt=attempt,
        started_at=NOW,
        target_ids=tuple(digests),
        note_identity=identity,
        digests=digests,
        match_sha256=draft_write.match_digest(match, tuple(digests)) or "2" * 64,
        body_sha256="1" * 64,
        outcome=outcome,
        refusal=refusal,
        finished_at=None if outcome == "attempting" else NOW + timedelta(seconds=2),
    )


def _own(entry: Mapping[str, Any], name: str = "Standard Consultation") -> OwnDefaults:
    return OwnDefaults.model_validate({"templates": {name: entry}})


def _as_written(prepared: draft_write.PreparedWrite, *, sanitise: bool = True) -> dict[str, Any]:
    """The note as Cliniko would answer it after taking ``prepared``: the
    sent body, its rich text re-represented (P.1 Q1) when ``sanitise``."""
    content = prepared.content.content.model_dump()
    if sanitise:
        for section in content["sections"]:
            for question in section["questions"]:
                answer = question.get("answer")
                if isinstance(answer, str):
                    question["answer"] = answer.replace("</p><p>", "</p>\n<p>")
    return content


class Cliniko:
    """A fake transport answering hop 1's GETs and hop 2's PATCH by method
    and path prefix (a queue per route whose LAST answer repeats); records
    every request. No socket, ever."""

    def __init__(
        self,
        *,
        notes: tuple[Any, ...] = (),
        template: Any = None,
        patch: Any = None,
    ) -> None:
        self.answers: dict[tuple[str, str], list[Any]] = {
            ("GET", "/v1/treatment_notes/"): list(notes) or [ok(note_body(content=_content()))],
            ("GET", "/v1/treatment_note_templates/"): [
                template if template is not None else ok(_template())
            ],
            ("PATCH", "/v1/treatment_notes/"): [patch if patch is not None else ok({"id": NOTE})],
            # The Chrome note check's display reads (the parity test only).
            ("GET", "/v1/patients/"): [ok(PATIENT_BODY)],
            ("GET", "/v1/bookings/"): [ok(BOOKING_BODY)],
        }
        self.calls: list[tuple[str, str]] = []
        self.bodies: list[bytes | None] = []

    def request(
        self,
        method: str,
        host: str,
        path: str,
        headers: Mapping[str, str],
        max_body: int,
        *,
        body: bytes | None = None,
    ) -> cc.RawResponse:
        self.calls.append((method, path))
        self.bodies.append(body)
        route = next(k for k in self.answers if k[0] == method and path.startswith(k[1]))
        queue = self.answers[route]
        answer = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(answer, BaseException):
            raise answer
        assert isinstance(answer, cc.RawResponse)
        return answer


def _template_link(template_id: str) -> dict[str, Any]:
    return {"links": {"self": f"{_API}/treatment_note_templates/{template_id}"}}


# ---------------------------------------------------------------------------
# Task 3.2: normalised comparison.
# ---------------------------------------------------------------------------


class TestNormalisation:
    def test_paragraphs_and_line_breaks_are_lines_never_run_together(self) -> None:
        assert draft_write.normalise_answer("<p>a</p><p>b</p>", "html") == "a\nb"
        assert draft_write.normalise_answer("a<br>b", "html") == "a\nb"
        assert draft_write.normalise_answer("<div>a</div><ul><li>b</li></ul>", "html") == "a\nb"

    def test_a_line_break_inside_html_text_is_whitespace(self) -> None:
        assert draft_write.normalise_answer("<p>left\nshoulder</p>", "html") == "left shoulder"

    def test_html_is_decoded_exactly_once(self) -> None:
        assert draft_write.normalise_answer("&amp;lt;b&amp;gt;", "html") == "&lt;b&gt;"
        assert draft_write.normalise_answer("&lt;b&gt;", "html") == "<b>"

    def test_visible_text_is_never_html_decoded(self) -> None:
        """PR-HIGH-009: a plain-text answer's literal markup is its text."""
        assert draft_write.normalise_answer("&lt;b&gt; <i>x</i>", "visible") == (
            "&lt;b&gt; <i>x</i>"
        )

    def test_nfc_whitespace_and_blank_lines(self) -> None:
        text = "Café   x\n\n \t\n  y  "
        assert draft_write.normalise_visible(text) == "Café x\ny"
        assert draft_write.normalise_answer("<p>  </p><p><br></p>", "html") == ""

    def test_the_sanitised_form_of_a_sent_answer_compares_equal(self) -> None:
        """P.1 Q1: Cliniko rewrote the markup characters, the visible text
        survived one decode."""
        sent = draft_write.to_cliniko_answer(['a<b & "c" \'d\''], "rich_text")
        stored = "<p>a&lt;b &amp; \"c\" 'd'</p>"
        assert sent != stored
        assert draft_write.normalise_answer(sent, "html") == draft_write.normalise_answer(
            stored, "html"
        )

    def test_the_digest_is_sha256_of_the_normalised_text_and_takes_a_lone_surrogate(
        self,
    ) -> None:
        assert draft_write.answer_digest("a\nb") == hashlib.sha256(b"a\nb").hexdigest()
        assert re.fullmatch(r"[0-9a-f]{64}", draft_write.answer_digest("x\ud800"))


# ---------------------------------------------------------------------------
# Task 3.2: the template match (D4).
# ---------------------------------------------------------------------------


class TestTemplateMatch:
    def test_every_writable_target_matches_p1s_template(self) -> None:
        match = draft_write.match_template(_profile(), _template(), _content())
        assert isinstance(match, draft_write.Match)
        assert set(match.questions) == {
            "presenting-progress",
            "assessment",
            "diagnosis",
            "treatment",
            "response-to-treatment",
            "management-advice",
        }
        diagnosis = match.questions["diagnosis"]
        assert (diagnosis.section_name, diagnosis.question_name) == ("Examination", "Diagnosis")
        assert diagnosis.note_position == diagnosis.template_position == (1, 2)
        assert diagnosis.representation == "html"
        assert "informed-consent" not in match.questions

    def test_the_shipped_profile_has_p1s_recorded_shape_and_matches_it(self) -> None:
        """The evidence is Task P.1 (the plan's handoff note, SMOKE RESULTS
        step 6): clinic 1's "Standard Consultation" is three sections of
        1 / 3 / 3 questions, every question ``paragraph`` but one
        ``checkboxes`` (section 2, question 2) — no ``text`` question. The
        shipped Template A therefore declares every writable target
        ``rich_text`` and the checkbox the attestation (the Phase 3 profile
        correction: five targets were ``plain_text``, which D4's type rule
        refused on every real write). Clinic 2's template is NOT verified
        (its P.1 is deferred): the match at write time stays its check."""
        shipped = _template_a()
        by_group: dict[str, list[str]] = {}
        for target in shipped.template_targets:
            by_group.setdefault(target.group, []).append(target.target_type)
        assert by_group == {
            "History": ["rich_text"],
            "Examination": ["rich_text", "attestation_checkbox", "rich_text"],
            "Treatment/Management": ["rich_text", "rich_text", "rich_text"],
        }
        match = draft_write.match_template(shipped, _template(), _content())
        assert isinstance(match, draft_write.Match)
        assert {q.representation for q in match.questions.values()} == {"html"}

    def test_a_plain_text_target_matches_a_text_question_as_visible_text(self) -> None:
        types = {"Diagnosis": "text"}
        match = draft_write.match_template(
            _profile({"diagnosis": "plain_text"}), _template(types=types), _content(types=types)
        )
        assert isinstance(match, draft_write.Match)
        assert match.questions["diagnosis"].representation == "visible"

    @pytest.mark.parametrize("where", ["template", "content"])
    def test_a_type_mismatch_names_the_question(self, where: str) -> None:
        types = {"Diagnosis": "text"}
        template = _template(types=types) if where == "template" else _template()
        content = _content(types=types) if where == "content" else _content()
        assert draft_write.match_template(_profile(), template, content) == (
            draft_write.TemplateMismatch("Diagnosis", "Examination")
        )

    def test_two_targets_naming_one_question_refuse(self) -> None:
        """Round 27 LOW-001: one question, one target — otherwise the second
        answer would overwrite the first in the body while the record lists
        both as written."""
        raw = _profile().model_dump()
        for target in raw["template_targets"]:
            if target["target_id"] == "response-to-treatment":
                target["group"], target["field_label"] = "Examination", "Diagnosis"
        doubled = TemplateProfile.model_validate(raw)
        assert draft_write.match_template(doubled, _template(), _content()) == (
            draft_write.TemplateMismatch("Diagnosis", "Examination")
        )

    def test_no_profile_and_an_unmapped_section_refuse(self) -> None:
        assert draft_write.match_template(None, _template(), _content()) == (
            draft_write.TemplateMismatch()
        )
        oversight = _profile().model_copy(update={"intentionally_unmapped": ()})
        assert oversight.unmapped_section_keys()
        assert draft_write.match_template(oversight, _template(), _content()) == (
            draft_write.TemplateMismatch()
        )

    @pytest.mark.parametrize("where", ["template", "content"])
    def test_a_missing_or_repeated_question_or_section_names_the_target(self, where: str) -> None:
        def edited(edit: Any) -> tuple[dict[str, Any], dict[str, Any]]:
            template, content = _template(), _content()
            edit(template["content"] if where == "template" else content)
            return template, content

        def drop(doc: dict[str, Any]) -> None:
            doc["sections"][2]["questions"].pop(0)  # Treatment

        def repeat(doc: dict[str, Any]) -> None:
            doc["sections"][2]["questions"].append({"name": "Treatment", "type": "paragraph"})

        def repeat_section(doc: dict[str, Any]) -> None:
            doc["sections"].append(json.loads(json.dumps(doc["sections"][2])))

        for edit in (drop, repeat, repeat_section):
            template, content = edited(edit)
            assert draft_write.match_template(_profile(), template, content) == (
                draft_write.TemplateMismatch("Treatment", "Treatment/Management")
            ), edit.__name__

    @pytest.mark.parametrize(
        "sections",
        [None, "sections", [{"name": "History"}], [{"name": "History", "questions": [{}]}]],
    )
    def test_a_malformed_structure_refuses_without_naming(self, sections: object) -> None:
        template = {"name": "Standard Consultation", "content": {"sections": sections}}
        assert draft_write.match_template(_profile(), template, _content()) == (
            draft_write.TemplateMismatch()
        )
        content = {"sections": sections}
        assert draft_write.match_template(_profile(), _template(), content) == (
            draft_write.TemplateMismatch()
        )

    def test_a_template_with_top_level_sections_is_read_as_the_probe_reads_it(self) -> None:
        template = _template()
        flat = {"name": template["name"], "sections": template["content"]["sections"]}
        match = draft_write.match_template(_profile(), flat, _content())
        assert isinstance(match, draft_write.Match)


# ---------------------------------------------------------------------------
# Task 3.2 / D14: the declared defaults and the typed-text check.
# ---------------------------------------------------------------------------


def _match(
    template: Mapping[str, Any] | None = None, content: object = None
) -> draft_write.Match:
    match = draft_write.match_template(
        _profile(),
        _template() if template is None else template,
        _content() if content is None else content,
    )
    assert isinstance(match, draft_write.Match)
    return match


class TestClinikoTemplateDefaults:
    def test_the_templates_own_answer_is_the_default_and_absent_is_empty(self) -> None:
        baseline = draft_write.baseline_defaults(_match(), _template(), "cliniko_template", None)
        assert isinstance(baseline, draft_write.Baseline)
        assert baseline.defaults["presenting-progress"] == "Site -\nChron -\nAgg -"
        assert {v for k, v in baseline.defaults.items() if k != "presenting-progress"} == {""}

    def test_a_null_answer_is_empty_and_any_other_shape_has_no_baseline(self) -> None:
        template = _template({_HISTORY: None})
        baseline = draft_write.baseline_defaults(
            _match(template), template, "cliniko_template", None
        )
        assert isinstance(baseline, draft_write.Baseline)
        assert baseline.defaults["presenting-progress"] == ""
        for bad in (["Site -"], 3, {"text": "Site -"}):
            template = _template({_HISTORY: bad})
            assert draft_write.baseline_defaults(
                _match(template), template, "cliniko_template", None
            ) == draft_write.DefaultsRefusal("no_baseline")

    def test_a_new_note_at_the_template_default_holds_no_text(self) -> None:
        baseline = draft_write.baseline_defaults(_match(), _template(), "cliniko_template", None)
        assert isinstance(baseline, draft_write.Baseline)
        assert not draft_write.note_has_text(_content(), baseline, _match())
        empty = _content({})
        assert not draft_write.note_has_text(empty, baseline, _match(content=empty))

    def test_typed_text_anywhere_targeted_is_text(self) -> None:
        baseline = draft_write.baseline_defaults(_match(), _template(), "cliniko_template", None)
        assert isinstance(baseline, draft_write.Baseline)
        for answers in (
            {_HISTORY: "<p>Site - left knee</p>"},
            {_HISTORY: _NOTE_DEFAULT, "Management/Advice": "<p>Ice</p>"},
        ):
            content = _content(answers)
            assert draft_write.note_has_text(content, baseline, _match(content=content))

    def test_an_answer_that_is_not_text_counts_as_text(self) -> None:
        baseline = draft_write.baseline_defaults(_match(), _template(), "cliniko_template", None)
        assert isinstance(baseline, draft_write.Baseline)
        content = _content({_HISTORY: _NOTE_DEFAULT, "Diagnosis": ["x"]})
        assert draft_write.note_has_text(content, baseline, _match(content=content))

    def test_an_untargeted_question_never_counts(self) -> None:
        """Round 25 LOW-016: an untargeted question holding typed text (a
        paragraph the profile does not map) is not the write's business —
        it round-trips in the full body."""
        template, content = _template(), _content()
        extra = {"name": "Private notes", "type": "paragraph"}
        template["content"]["sections"][0]["questions"].append(dict(extra))
        content["sections"][0]["questions"].append({**extra, "answer": "<p>typed</p>"})
        match = _match(template, content)
        baseline = draft_write.baseline_defaults(match, template, "cliniko_template", None)
        assert isinstance(baseline, draft_write.Baseline)
        assert not draft_write.note_has_text(content, baseline, match)

    def test_a_note_holding_the_template_default_byte_for_byte_holds_no_text(self) -> None:
        content = _content({_HISTORY: _TEMPLATE_DEFAULT})
        baseline = draft_write.baseline_defaults(_match(), _template(), "cliniko_template", None)
        assert isinstance(baseline, draft_write.Baseline)
        assert not draft_write.note_has_text(content, baseline, _match(content=content))

    @pytest.mark.parametrize(
        "extra", ['<img src="x.png">', "<hr>", '<p><img src="x.png"></p>', "<iframe></iframe>"]
    )
    def test_content_that_is_not_text_counts_as_text(self, extra: str) -> None:
        """Round 25 LOW-015: an image or a rule has no visible text, so a
        visible-text comparison alone would call it untyped and overwrite
        it; any tag outside the text-formatting set counts as text."""
        baseline = draft_write.baseline_defaults(_match(), _template(), "cliniko_template", None)
        assert isinstance(baseline, draft_write.Baseline)
        for answers in ({"Diagnosis": extra}, {_HISTORY: _TEMPLATE_DEFAULT + extra}):
            content = _content(answers)
            assert draft_write.note_has_text(content, baseline, _match(content=content))

    def test_formatting_tags_are_still_untyped(self) -> None:
        baseline = draft_write.baseline_defaults(_match(), _template(), "cliniko_template", None)
        assert isinstance(baseline, draft_write.Baseline)
        styled = "<p><strong>Site -</strong></p><p><em>Chron</em> -</p><p><span>Agg -</span></p>"
        content = _content({_HISTORY: styled, "Diagnosis": "<p><br></p>"})
        assert not draft_write.note_has_text(content, baseline, _match(content=content))


class TestPlainText:
    """Round 25 MED-003 (PR-HIGH-009): a ``plain_text`` target on a ``text``
    question is compared as VISIBLE text end to end — its template default,
    the typed-text check, the digests and the body — never HTML-decoded or
    escaped."""

    _TYPES = {"Diagnosis": "text"}

    def _profile(self) -> TemplateProfile:
        return _profile({"diagnosis": "plain_text"})

    def _setup(
        self, template_answers: Mapping[str, object], note_answers: Mapping[str, object]
    ) -> tuple[dict[str, Any], dict[str, Any], draft_write.Match]:
        template = _template(template_answers, self._TYPES)
        content = _content(note_answers, self._TYPES)
        match = draft_write.match_template(self._profile(), template, content)
        assert isinstance(match, draft_write.Match)
        return template, content, match

    def test_the_template_default_of_a_text_question_is_literal(self) -> None:
        template, _content_, match = self._setup({"Diagnosis": "a &amp; <b>x</b>"}, {})
        baseline = draft_write.baseline_defaults(match, template, "cliniko_template", None)
        assert isinstance(baseline, draft_write.Baseline)
        assert baseline.defaults["diagnosis"] == "a &amp; <b>x</b>"

    @pytest.mark.parametrize(
        ("default", "typed"),
        [("left knee", "left <b>knee</b>"), ("a & b", "a &amp; b"), ("a < b", "a &lt; b")],
    )
    def test_literal_markup_is_typed_text(self, default: str, typed: str) -> None:
        template, content, match = self._setup({"Diagnosis": default}, {"Diagnosis": typed})
        baseline = draft_write.baseline_defaults(match, template, "cliniko_template", None)
        assert isinstance(baseline, draft_write.Baseline)
        assert draft_write.note_has_text(content, baseline, match)
        _t, same, same_match = self._setup({"Diagnosis": default}, {"Diagnosis": default})
        assert not draft_write.note_has_text(same, baseline, same_match)
        assert draft_write.answer_digests(content, match)["diagnosis"] != (
            draft_write.answer_digests(same, same_match)["diagnosis"]
        )

    def test_the_body_carries_the_plain_answer_unescaped(self, tmp_path: Path) -> None:
        registry, _ = _registry(tmp_path)
        template, content, _match_ = self._setup({}, {})
        note = _note(style="clean", sections=(_section("diagnosis", "a<b & c"),))
        hop1 = _verified_hop1(registry, content=content, template=template)
        prepared = _prepare(registry, hop1, note=note, profile=self._profile())
        assert isinstance(prepared, draft_write.PreparedWrite)
        body = json.loads(prepared.content.to_body())
        assert body["content"]["sections"][1]["questions"][2]["answer"] == "a<b & c"
        assert prepared.digests["diagnosis"] == draft_write.answer_digest("a<b & c")


class TestUnparseableHtml:
    """Round 25 LOW-001: the stdlib parser can raise on malformed markup,
    and its message can quote the input. Every caller fails closed and no
    answer text reaches an exception."""

    @pytest.fixture(autouse=True)
    def _parser_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def boom(self: object, data: str) -> None:
            raise AssertionError(f"unknown status keyword {data!r}")

        monkeypatch.setattr(draft_write._VisibleText, "feed", boom)

    def test_the_error_is_named_and_carries_nothing(self) -> None:
        with pytest.raises(draft_write.AnswerUnparseable) as info:
            draft_write.html_to_visible("<![SECRET-ANSWER")
        assert "SECRET" not in str(info.value)
        assert info.value.__cause__ is None and info.value.__context__ is None

    def test_a_visible_answer_never_reaches_the_parser(self) -> None:
        assert draft_write.normalise_answer("a <b>", "visible") == "a <b>"

    def test_every_caller_fails_closed(self) -> None:
        match = _match()
        assert draft_write.baseline_defaults(
            match, _template(), "cliniko_template", None
        ) == draft_write.DefaultsRefusal("no_baseline")
        baseline = draft_write.Baseline({target: "" for target in match.questions})
        assert draft_write.note_has_text(_content(), baseline, match)
        assert draft_write.answer_digests(_content(), match) == {}

    def test_prepare_write_refuses_without_raising(self, tmp_path: Path) -> None:
        registry, _ = _registry(tmp_path)
        own = _own({"History": {_HISTORY: "Site -"}})
        assert _prepare(registry, source="own_file", own=own) == draft_write.WriteRefusal(
            "note_has_text"
        )
        empty = _verified_hop1(registry, content=_content({}))
        assert _prepare(registry, empty, source="own_file", own=own) == (
            draft_write.WriteRefusal("answer_unreadable")
        )


class TestOwnDefaults:
    def test_the_file_decides_the_defaults_as_visible_text(self) -> None:
        own = _own({"History": {_HISTORY: ["Site -", "Chron -", "Agg -"]}})
        baseline = draft_write.baseline_defaults(_match(), _template({}), "own_file", own)
        assert isinstance(baseline, draft_write.Baseline)
        assert baseline.defaults["presenting-progress"] == "Site -\nChron -\nAgg -"
        assert not draft_write.note_has_text(_content(), baseline, _match())

    def test_a_transcription_is_never_html_decoded(self) -> None:
        own = _own({"Examination": {"Diagnosis": "a &amp; b"}})
        baseline = draft_write.baseline_defaults(_match(), _template(), "own_file", own)
        assert isinstance(baseline, draft_write.Baseline)
        assert baseline.defaults["diagnosis"] == "a &amp; b"
        stored = _content({_HISTORY: "", "Diagnosis": "<p>a &amp;amp; b</p>"})
        assert not draft_write.note_has_text(stored, baseline, _match(content=stored))
        decoded = _content({_HISTORY: "", "Diagnosis": "<p>a &amp; b</p>"})
        assert draft_write.note_has_text(decoded, baseline, _match(content=decoded))

    def test_the_template_is_never_the_source_under_own_file(self) -> None:
        """The template's own History default is NOT declared by the file, so
        a note still holding it holds text (fail closed)."""
        own = _own({"Examination": {"Diagnosis": "x"}})
        baseline = draft_write.baseline_defaults(_match(), _template(), "own_file", own)
        assert isinstance(baseline, draft_write.Baseline)
        assert baseline.defaults["presenting-progress"] == ""
        assert draft_write.note_has_text(_content(), baseline, _match())

    @pytest.mark.parametrize("kind", ["missing", "unreadable", "too_large", "not_valid"])
    def test_a_loader_problem_is_defaults_unreadable_by_kind(self, kind: Any) -> None:
        problem = OwnDefaultsProblem(kind, "templates > x (value_error)")
        assert draft_write.baseline_defaults(
            _match(), _template(), "own_file", problem
        ) == draft_write.DefaultsRefusal("defaults_unreadable", problem=kind)

    def test_no_loaded_file_is_a_caller_bug(self) -> None:
        """Round 25 LOW-003: never an invented loader problem."""
        with pytest.raises(ValueError, match="loaded file"):
            draft_write.baseline_defaults(_match(), _template(), "own_file", None)

    def test_no_entry_for_the_template_names_it(self) -> None:
        own = _own({"History": {_HISTORY: "x"}}, name="Follow-up")
        assert draft_write.baseline_defaults(
            _match(), _template(), "own_file", own
        ) == draft_write.DefaultsRefusal("defaults_no_template", template="Standard Consultation")

    def test_a_template_with_no_name_has_no_baseline(self) -> None:
        own = _own({"History": {_HISTORY: "x"}})
        template = _template(name=None)
        assert draft_write.baseline_defaults(
            _match(template), template, "own_file", own
        ) == draft_write.DefaultsRefusal("no_baseline")

    def test_an_unmatched_entry_names_the_first_and_counts_the_rest(self) -> None:
        own = _own(
            {
                "History": {_HISTORY: "x", "Aggravating": "y"},
                "Plan": {"Next visit": "z"},
                "Examination": {"Diagnosis": "w", "Palpation": "v"},
            }
        )
        assert draft_write.baseline_defaults(
            _match(), _template(), "own_file", own
        ) == draft_write.DefaultsRefusal(
            "defaults_unmatched", section="History", question="Aggravating", more=2
        )

    def test_a_listed_question_that_is_not_targeted_is_accepted_and_unused(self) -> None:
        own = _own({"Examination": {"Informed Consent": "Given", "Diagnosis": "d"}})
        baseline = draft_write.baseline_defaults(_match(), _template(), "own_file", own)
        assert isinstance(baseline, draft_write.Baseline)
        assert "Given" not in baseline.defaults.values()
        assert baseline.defaults["diagnosis"] == "d"


# ---------------------------------------------------------------------------
# Task 3.2 / 2.1: the FULL body.
# ---------------------------------------------------------------------------


class TestBuildBody:
    def test_only_the_answers_change_and_everything_else_round_trips(self) -> None:
        content = _content()
        before = json.dumps(content)
        body = draft_write.build_body(content, _match(), {"diagnosis": "<p>Strain</p>"})
        assert isinstance(body, cc.DraftContent)
        assert json.dumps(content) == before  # the re-read content is not mutated
        expected = json.loads(before)
        expected["sections"][1]["questions"][2]["answer"] = "<p>Strain</p>"
        assert body.content.model_dump() == expected
        assert json.loads(body.to_body()) == {"content": expected}

    def test_an_answer_is_sent_nfc(self) -> None:
        body = draft_write.build_body(_content(), _match(), {"diagnosis": "<p>Café</p>"})
        assert isinstance(body, cc.DraftContent)
        answer = body.content.model_dump()["sections"][1]["questions"][2]["answer"]
        assert answer == unicodedata.normalize("NFC", "<p>Café</p>") == "<p>Café</p>"

    def test_an_answer_for_an_unmatched_target_is_a_caller_error(self) -> None:
        with pytest.raises(ValueError, match="target"):
            draft_write.build_body(_content(), _match(), {"informed-consent": "ticked"})

    @pytest.mark.parametrize(
        "poison",
        [{"future_key": math.nan}, {"future_key": "x\ud800"}, {"sections": "not a list"}],
    )
    def test_an_unencodable_or_malformed_content_is_answer_unreadable(
        self, poison: dict[str, Any]
    ) -> None:
        content = {**_content(), **poison}
        assert draft_write.build_body(content, _match(), {}) == draft_write.AnswerUnreadable()
        assert draft_write.build_body("content", _match(), {}) == draft_write.AnswerUnreadable()


# ---------------------------------------------------------------------------
# Task 3.3: the write record's model.
# ---------------------------------------------------------------------------


class TestWriteRecord:
    def test_it_round_trips_and_holds_ids_and_digests_only(self) -> None:
        record = _record("refused", refusal="cliniko_rejected")
        assert draft_write.parse_write_record(record.to_bytes()) == record
        assert set(json.loads(record.to_bytes())) == {
            "schema_version",
            "attempt",
            "started_at",
            "target_ids",
            "note_identity",
            "digests",
            "match_sha256",
            "body_sha256",
            "outcome",
            "refusal",
            "finished_at",
        }

    @pytest.mark.parametrize(
        "update",
        [
            {"digests": {"treatment": "0" * 64}},
            {"target_ids": ("diagnosis", "diagnosis")},
            {"refusal": "note_not_found"},
            {"outcome": "refused"},
            {"finished_at": None},
            {"outcome": "attempting"},
            {"note_identity": "not-a-digest"},
            {"match_sha256": "not-a-digest"},
            {"attempt": 0},
            {"target_ids": ()},
            {"started_at": NOW.replace(tzinfo=None)},
            {"extra": 1},
        ],
    )
    def test_an_inconsistent_record_is_refused(self, update: dict[str, Any]) -> None:
        data = {**_record().model_dump(), **update}
        with pytest.raises(ValidationError):
            draft_write.WriteRecord.model_validate(data)

    @pytest.mark.parametrize(
        "plaintext", [b"", b"not json", b"[]", b'{"schema_version": 2}', "é".encode("latin-1")]
    )
    def test_anything_else_is_unreadable_with_no_chained_detail(self, plaintext: bytes) -> None:
        with pytest.raises(draft_write.WriteRecordUnreadable) as info:
            draft_write.parse_write_record(plaintext)
        assert str(info.value) == "the write record is unreadable"
        assert info.value.__cause__ is None and info.value.__context__ is None

    def test_the_transitions_are_revalidated(self) -> None:
        attempting = _record("attempting")
        refused = draft_write.finished_record(
            attempting, draft_write.WriteOutcome("refused", "finalised_before_write"), now=NOW
        )
        assert (refused.outcome, refused.refusal, refused.finished_at) == (
            "refused",
            "finalised_before_write",
            NOW,
        )
        written = draft_write.reconciled_record(_record("unknown"), now=NOW)
        assert (written.outcome, written.refusal) == ("written", None)
        with pytest.raises(ValidationError):
            draft_write.finished_record(attempting, draft_write.WriteOutcome("refused"), now=NOW)

    @pytest.mark.parametrize("outcome", ["unknown", "refused", "written"])
    def test_a_known_outcome_is_never_finished_again(self, outcome: str) -> None:
        """Round 25 LOW-007: only the ``attempting`` row takes hop 2's
        answer."""
        refusal = "note_not_found" if outcome == "refused" else None
        with pytest.raises(ValueError, match="attempting"):
            draft_write.finished_record(
                _record(outcome, refusal=refusal), draft_write.WriteOutcome("unknown"), now=NOW
            )

    @pytest.mark.parametrize("outcome", ["refused", "written"])
    def test_only_an_open_attempt_is_reconciled(self, outcome: str) -> None:
        """A ``refused`` record is never confirmed ``written``."""
        refusal = "cliniko_rejected" if outcome == "refused" else None
        with pytest.raises(ValueError, match="open attempt"):
            draft_write.reconciled_record(_record(outcome, refusal=refusal), now=NOW)
        assert draft_write.reconciled_record(_record("attempting"), now=NOW).outcome == "written"

    def test_the_status_is_content_free(self) -> None:
        status_of = draft_write.record_status
        assert status_of(None, _IDENTITY) == draft_write.WriteRecordStatus("none")
        assert status_of(draft_write.RECORD_UNREADABLE, _IDENTITY) == (
            draft_write.WriteRecordStatus("unreadable")
        )
        written = status_of(_record("written"), _IDENTITY)
        assert written.written and written.note_matches and not written.open_attempt
        assert not status_of(_record("written"), _OTHER_IDENTITY).written
        assert not status_of(_record("written"), None).note_matches
        unknown = status_of(_record("unknown"), _IDENTITY)
        assert unknown.open_attempt and not unknown.written
        assert status_of(_record("attempting"), _IDENTITY).open_attempt
        refused = status_of(_record("refused", refusal="note_not_found"), _IDENTITY)
        assert (refused.outcome, refused.refusal, refused.open_attempt) == (
            "refused",
            "note_not_found",
            False,
        )


# ---------------------------------------------------------------------------
# Task 3.3: reconcile (D5).
# ---------------------------------------------------------------------------


class TestReconcile:
    def _baseline(self) -> draft_write.Baseline:
        baseline = draft_write.baseline_defaults(_match(), _template(), "cliniko_template", None)
        assert isinstance(baseline, draft_write.Baseline)
        return baseline

    def _sent(self, tmp_path: Path) -> draft_write.PreparedWrite:
        registry, _ = _registry(tmp_path)
        prepared = _prepare(registry)
        assert isinstance(prepared, draft_write.PreparedWrite)
        return prepared

    @pytest.mark.parametrize("outcome", ["attempting", "unknown"])
    def test_an_open_attempt_cliniko_holds_is_written(self, tmp_path: Path, outcome: str) -> None:
        prepared = self._sent(tmp_path)
        record = draft_write.attempt_record(prepared, now=NOW)
        if outcome == "unknown":
            record = draft_write.finished_record(
                record, draft_write.WriteOutcome("unknown"), now=NOW
            )
        after = _as_written(prepared)
        verdict = draft_write.reconcile(
            record, after, _match(content=after), self._baseline(), _IDENTITY
        )
        assert verdict == draft_write.ReconciledWritten()

    def test_a_refused_attempt_is_never_written_even_when_its_digests_match(
        self, tmp_path: Path
    ) -> None:
        prepared = self._sent(tmp_path)
        record = draft_write.finished_record(
            draft_write.attempt_record(prepared, now=NOW),
            draft_write.WriteOutcome("refused", "cliniko_rejected"),
            now=NOW,
        )
        after = _as_written(prepared)
        verdict = draft_write.reconcile(
            record, after, _match(content=after), self._baseline(), _IDENTITY
        )
        assert verdict == draft_write.Uncertain()
        assert draft_write.reconcile(record, _content(), _match(), self._baseline(), _IDENTITY) == (
            draft_write.AtBaseline()
        )

    def test_an_open_attempt_at_the_default_is_the_next_attempt_else_uncertain(self) -> None:
        record = _record("unknown")
        assert draft_write.reconcile(record, _content(), _match(), self._baseline(), _IDENTITY) == (
            draft_write.AtBaseline()
        )
        edited = _content({_HISTORY: "<p>typed in Cliniko</p>"})
        assert draft_write.reconcile(
            record, edited, _match(content=edited), self._baseline(), _IDENTITY
        ) == draft_write.Uncertain()

    def test_a_record_of_another_saved_note_is_uncertain_even_when_written(self) -> None:
        for outcome in ("written", "unknown"):
            assert draft_write.reconcile(
                _record(outcome, identity=_OTHER_IDENTITY),
                _content(),
                _match(),
                self._baseline(),
                _IDENTITY,
            ) == draft_write.Uncertain()

    def test_one_differing_target_is_not_written(self, tmp_path: Path) -> None:
        prepared = self._sent(tmp_path)
        record = draft_write.attempt_record(prepared, now=NOW)
        after = _as_written(prepared)
        after["sections"][1]["questions"][2]["answer"] = "<p>Changed in Cliniko</p>"
        assert draft_write.reconcile(
            record, after, _match(content=after), self._baseline(), _IDENTITY
        ) == draft_write.Uncertain()


# ---------------------------------------------------------------------------
# Task 3.4: prepare_write's order.
# ---------------------------------------------------------------------------


class TestPrepareWrite:
    def test_a_clean_draft_takes_the_full_body_of_the_notes_own_style(
        self, tmp_path: Path
    ) -> None:
        registry, _ = _registry(tmp_path)
        prepared = _prepare(registry)
        assert isinstance(prepared, draft_write.PreparedWrite)
        answers = _answers(_write_note(), _profile())
        assert prepared.target_ids == ("presenting-progress", "diagnosis", "treatment")
        assert prepared.attempt == 1 and prepared.note_identity == _IDENTITY
        assert prepared.digests == {
            t: draft_write.answer_digest(draft_write.normalise_answer(answers[t], "html"))
            for t in prepared.target_ids
        }
        body = prepared.content.to_body()
        assert prepared.body_sha256 == hashlib.sha256(body).hexdigest()
        expected = _content()
        expected["sections"][0]["questions"][0]["answer"] = answers["presenting-progress"]
        expected["sections"][1]["questions"][2]["answer"] = answers["diagnosis"]
        expected["sections"][2]["questions"][0]["answer"] = answers["treatment"]
        assert json.loads(body) == {"content": expected}
        assert prepared.target == VerifiedTarget(
            clinic_id=enc_context().clinic_id,
            clinic_host=enc_context().clinic_host,
            patient_id=PATIENT,
            treatment_note_id=NOTE,
            practitioner_id=enc_context().practitioner_id,
            booking_id=enc_context().booking_id,
            template_id=TEMPLATE,
        )

    def test_the_answers_follow_the_notes_own_style(self, tmp_path: Path) -> None:
        registry, _ = _registry(tmp_path)
        note = _write_note()
        diagnosis = note.note_sections[1]
        rendering = StyleRendering(
            section_key="diagnosis",
            prose_text="A left shoulder strain.",
            input_digest=section_input_digest(diagnosis),
            verdict="passed",
        )
        narrative = note.model_copy(update={"style": "narrative", "style_renderings": (rendering,)})
        prepared = _prepare(registry, note=narrative)
        assert isinstance(prepared, draft_write.PreparedWrite)
        body = json.loads(prepared.content.to_body())
        assert body["content"]["sections"][1]["questions"][2]["answer"] == (
            "<p>A left shoulder strain.</p>"
        )

    def test_a_mock_note_is_refused_before_anything_else(self, tmp_path: Path) -> None:
        registry, _ = _registry(tmp_path)
        mock = _write_note(provider_name="mock-extractive")
        assert draft_write.is_mock_note(mock) and not draft_write.is_mock_note(_write_note())
        refused_hop1 = _refused_hop1(registry, NoteRefused(NoteRefusal.NOTE_FINAL))
        for hop1 in (None, refused_hop1):
            result = _prepare(registry, hop1, note=mock, record=draft_write.RECORD_UNREADABLE)
            assert result == draft_write.WriteRefusal("mock_note")

    def test_an_unreadable_record_and_a_written_one_refuse_before_the_check(
        self, tmp_path: Path
    ) -> None:
        registry, _ = _registry(tmp_path)
        refused_hop1 = _refused_hop1(registry, NoteRefused(NoteRefusal.NOTE_FINAL))
        assert _prepare(registry, refused_hop1, record=draft_write.RECORD_UNREADABLE) == (
            draft_write.WriteRefusal("record_unreadable")
        )
        assert _prepare(registry, refused_hop1, record=_record("written")) == (
            draft_write.WriteRefusal("already_written")
        )

    def test_the_refusals_before_any_read_are_one_public_check(self) -> None:
        """Round 25 MED-001: ``refuse_before_read`` is what the click runs
        BEFORE hop 1 (so these cases make no request); a ``written`` record
        of ANOTHER saved note is ``write_uncertain``, never the seen-mode
        line (D5)."""
        check = draft_write.refuse_before_read
        note = _write_note()
        mock = _write_note(provider_name="mock-extractive")
        assert check(mock, None, _IDENTITY) == draft_write.WriteRefusal("mock_note")
        assert check(note, draft_write.RECORD_UNREADABLE, _IDENTITY) == (
            draft_write.WriteRefusal("record_unreadable")
        )
        assert check(note, _record("written"), _IDENTITY) == (
            draft_write.WriteRefusal("already_written")
        )
        assert check(note, _record("written"), _OTHER_IDENTITY) == (
            draft_write.WriteRefusal("write_uncertain")
        )
        for record in (
            None,
            _record("attempting"),
            _record("unknown"),
            _record("refused", refusal="finalised_before_write"),
        ):
            assert check(note, record, _IDENTITY) is None

    def test_a_written_record_of_another_saved_note_is_uncertain_in_prepare_write(
        self, tmp_path: Path
    ) -> None:
        registry, _ = _registry(tmp_path)
        record = _record("written", identity=_OTHER_IDENTITY)
        assert _prepare(registry, record=record) == draft_write.WriteRefusal("write_uncertain")

    def test_a_note_finalised_after_a_refused_write_is_named_final_never_forbidden(
        self, tmp_path: Path
    ) -> None:
        """Round 25 LOW-017 (R22-02's other leg): the repeat guard applies
        only while the note re-reads as a draft."""
        registry, _ = _registry(tmp_path)
        hop1 = _refused_hop1(registry, NoteRefused(NoteRefusal.NOTE_FINAL))
        result = _prepare(
            registry, hop1, record=_record("refused", refusal="finalised_before_write")
        )
        assert isinstance(result, draft_write.WriteRefusal)
        assert result.name == "writeback_refused" and not result.earlier_attempt_open
        assert result.writeback is not None
        assert result.writeback.note_refusal is NoteRefusal.NOTE_FINAL

    def test_an_empty_saved_note_has_nothing_to_write(self, tmp_path: Path) -> None:
        registry, _ = _registry(tmp_path)
        assert _prepare(registry, note=_note(sections=())) == draft_write.WriteRefusal(
            "nothing_to_write"
        )

    def test_hop_one_names_a_429_for_the_latch(self, tmp_path: Path) -> None:
        """Round 25 LOW-004: ``prepare_write`` sees only ``not_verified``;
        the caller reads ``rate_limited`` from hop 1 itself."""
        registry, _ = _registry(tmp_path)
        limited = _refused_hop1(registry, UnverifiedOffline(enc_context(), rate_limited=True))
        offline = _refused_hop1(registry, UnverifiedOffline(enc_context()))
        final = _refused_hop1(registry, NoteRefused(NoteRefusal.NOTE_FINAL))
        assert limited.rate_limited
        assert not offline.rate_limited and not final.rate_limited
        assert not _verified_hop1(registry).rate_limited

    @pytest.mark.parametrize(
        ("outcome", "expected"),
        [
            (
                NoteRefused(NoteRefusal.NOTE_FINAL),
                (WritebackRefusal.REVERIFICATION_REFUSED, NoteRefusal.NOTE_FINAL),
            ),
            (
                NoteRefused(NoteRefusal.KEY_REJECTED),
                (WritebackRefusal.REVERIFICATION_REFUSED, NoteRefusal.KEY_REJECTED),
            ),
            ("offline", (WritebackRefusal.NOT_VERIFIED, None)),
        ],
    )
    def test_the_click_s_own_check_decides_first(
        self, tmp_path: Path, outcome: Any, expected: tuple[Any, Any]
    ) -> None:
        registry, _ = _registry(tmp_path)
        if outcome == "offline":
            outcome = UnverifiedOffline(enc_context(), rate_limited=True)
        result = _prepare(registry, _refused_hop1(registry, outcome), record=_record("unknown"))
        assert isinstance(result, draft_write.WriteRefusal)
        assert result.name == "writeback_refused" and result.earlier_attempt_open
        assert result.writeback is not None
        assert (result.writeback.reason, result.writeback.note_refusal) == expected

    def test_no_consent_or_no_link_is_refused_by_name(self, tmp_path: Path) -> None:
        registry, _ = _registry(tmp_path)
        for kwargs, reason in (
            ({"consent": None}, WritebackRefusal.CONSENT_UNAVAILABLE),
            ({"context": None}, WritebackRefusal.UNLINKED),
        ):
            result = _prepare(registry, **kwargs)
            assert isinstance(result, draft_write.WriteRefusal)
            assert result.writeback is not None and result.writeback.reason is reason

    def test_a_note_re_templated_between_the_reads_is_a_mismatch(self, tmp_path: Path) -> None:
        registry, _ = _registry(tmp_path)
        assert _prepare(registry, _verified_hop1(registry, matches=False)) == (
            draft_write.WriteRefusal("template_mismatch")
        )

    def test_a_template_mismatch_names_the_question(self, tmp_path: Path) -> None:
        registry, _ = _registry(tmp_path)
        # A ``plain_text`` target meeting P.1's ``paragraph`` question.
        mismatched = _profile({"assessment": "plain_text"})
        assert _prepare(registry, profile=mismatched) == draft_write.WriteRefusal(
            "template_mismatch", question="Assessment", section="Examination"
        )
        assert isinstance(_prepare(registry, profile=_template_a()), draft_write.PreparedWrite)
        assert _prepare(registry, profile=None) == draft_write.WriteRefusal("template_mismatch")

    def test_r22_08_an_open_attempt_cliniko_holds_is_written_with_no_baseline(
        self, tmp_path: Path
    ) -> None:
        """The digest check runs BEFORE the defaults: a clinic switched to an
        unreadable own-defaults file still records its earlier write."""
        registry, _ = _registry(tmp_path)
        first = _prepare(registry)
        assert isinstance(first, draft_write.PreparedWrite)
        record = draft_write.attempt_record(first, now=NOW)
        hop1 = _verified_hop1(registry, content=_as_written(first))
        result = _prepare(
            registry,
            hop1,
            record=record,
            source="own_file",
            own=OwnDefaultsProblem("not_valid", "the top of the file"),
        )
        assert result == draft_write.AlreadyWritten(first.target)

    @staticmethod
    def _changed_profile(way: str) -> TemplateProfile:
        """The default profile changed after a diagnosis-only write: the
        Diagnosis SECTION re-pointed at another (empty) question's target —
        target ``diagnosis`` unmapped — or target ``diagnosis`` itself moved
        to another question (the one it replaces dropped)."""
        raw = _profile().model_dump()
        if way == "unmapped":
            for mapping in raw["section_mappings"]:
                if mapping["section_key"] == "diagnosis":
                    mapping["target_id"] = "response-to-treatment"
        else:
            raw["template_targets"] = [
                t for t in raw["template_targets"] if t["target_id"] != "response-to-treatment"
            ]
            for target in raw["template_targets"]:
                if target["target_id"] == "diagnosis":
                    target["group"] = "Treatment/Management"
                    target["field_label"] = "Response to treatment"
            for mapping in raw["section_mappings"]:
                if mapping["target_id"] == "response-to-treatment":
                    mapping["target_id"] = "diagnosis"
        return TemplateProfile.model_validate(raw)

    @pytest.mark.parametrize("way", ["unmapped", "remapped"])
    def test_an_open_attempt_under_a_changed_profile_is_write_uncertain(
        self, tmp_path: Path, way: str
    ) -> None:
        """Peer round 28 PR-MED-036: an OPEN diagnosis-only attempt landed;
        the profile then changed so the current match no longer reads the
        Diagnosis question. Neither the digests nor the retry check can see
        the landed answer there, so a second write would duplicate it —
        refused ``write_uncertain`` on the recorded match digest instead."""
        registry, _ = _registry(tmp_path)
        note = _note(sections=(_section("diagnosis", "Left shoulder strain", start=1),))
        first = _prepare(registry, note=note)
        assert isinstance(first, draft_write.PreparedWrite)
        assert first.target_ids == ("diagnosis",)
        changed = self._changed_profile(way)
        landed = _verified_hop1(registry, content=_as_written(first))
        for record in (
            draft_write.attempt_record(first, now=NOW),
            draft_write.finished_record(
                draft_write.attempt_record(first, now=NOW),
                draft_write.WriteOutcome("unknown"),
                now=NOW,
            ),
        ):
            result = _prepare(registry, landed, record=record, note=note, profile=changed)
            assert result == draft_write.WriteRefusal("write_uncertain", earlier_attempt_open=True)
        # Not vacuous: the changed profile itself writes this note when the
        # earlier attempt was refused (Cliniko applied nothing).
        refused = draft_write.finished_record(
            draft_write.attempt_record(first, now=NOW),
            draft_write.WriteOutcome("refused", "cliniko_rejected"),
            now=NOW,
        )
        assert isinstance(
            _prepare(registry, record=refused, note=note, profile=changed),
            draft_write.PreparedWrite,
        )

    def test_the_match_digest_names_where_targets_are_written(self) -> None:
        match = draft_write.match_template(_profile(), _template(), _content())
        assert isinstance(match, draft_write.Match)
        both = draft_write.match_digest(match, ("diagnosis", "treatment"))
        assert both == draft_write.match_digest(match, ("treatment", "diagnosis"))
        assert both != draft_write.match_digest(match, ("diagnosis",))
        assert draft_write.match_digest(match, ("diagnosis", "absent")) is None
        moved = draft_write.match_template(
            self._changed_profile("remapped"), _template(), _content()
        )
        assert isinstance(moved, draft_write.Match)
        assert draft_write.match_digest(moved, ("diagnosis",)) != draft_write.match_digest(
            match, ("diagnosis",)
        )

    def test_a_record_of_another_saved_note_is_write_uncertain(self, tmp_path: Path) -> None:
        registry, _ = _registry(tmp_path)
        for outcome, refusal in (("unknown", None), ("refused", "cliniko_rejected")):
            result = _prepare(
                registry, record=_record(outcome, refusal=refusal, identity=_OTHER_IDENTITY)
            )
            assert isinstance(result, draft_write.WriteRefusal)
            assert result.name == "write_uncertain"
            assert result.earlier_attempt_open is (outcome == "unknown")

    def test_r22_02_a_draft_that_refused_as_finalised_is_write_forbidden_before_the_defaults(
        self, tmp_path: Path
    ) -> None:
        registry, _ = _registry(tmp_path)
        result = _prepare(
            registry,
            record=_record("refused", refusal="finalised_before_write"),
            source="own_file",
            own=None,
        )
        assert result == draft_write.WriteRefusal("write_forbidden")

    def test_the_defaults_refusals_come_before_any_attempt_and_carry_labels(
        self, tmp_path: Path
    ) -> None:
        registry, _ = _registry(tmp_path)
        assert _prepare(
            registry, source="own_file", own=OwnDefaultsProblem("too_large")
        ) == draft_write.WriteRefusal("defaults_unreadable", problem="too_large")
        own = _own({"History": {"Aggravating": "x"}, "Plan": {"Next": "y"}})
        assert _prepare(
            registry, record=_record("unknown"), source="own_file", own=own
        ) == draft_write.WriteRefusal(
            "defaults_unmatched",
            earlier_attempt_open=True,
            section="History",
            question="Aggravating",
            more=1,
        )
        other = _own({"History": {_HISTORY: "x"}}, name="Follow-up")
        assert _prepare(registry, source="own_file", own=other) == draft_write.WriteRefusal(
            "defaults_no_template", template="Standard Consultation"
        )
        template = _template({_HISTORY: 7})
        assert _prepare(registry, _verified_hop1(registry, template=template)) == (
            draft_write.WriteRefusal("no_baseline")
        )

    def test_typed_text_with_no_record_is_note_has_text(self, tmp_path: Path) -> None:
        registry, _ = _registry(tmp_path)
        content = _content({_HISTORY: _NOTE_DEFAULT, "Treatment": "<p>typed</p>"})
        assert _prepare(registry, _verified_hop1(registry, content=content)) == (
            draft_write.WriteRefusal("note_has_text")
        )

    def test_an_open_attempt_at_the_default_is_the_next_attempt(self, tmp_path: Path) -> None:
        registry, _ = _registry(tmp_path)
        prepared = _prepare(registry, record=_record("unknown", attempt=2))
        assert isinstance(prepared, draft_write.PreparedWrite)
        assert prepared.attempt == 3

    def test_an_open_attempt_over_other_text_is_write_uncertain(self, tmp_path: Path) -> None:
        registry, _ = _registry(tmp_path)
        content = _content({_HISTORY: "<p>typed in Cliniko</p>"})
        assert _prepare(
            registry, _verified_hop1(registry, content=content), record=_record("attempting")
        ) == draft_write.WriteRefusal("write_uncertain", earlier_attempt_open=True)

    def test_a_cleanly_refused_attempt_at_the_default_may_try_again(self, tmp_path: Path) -> None:
        registry, _ = _registry(tmp_path)
        prepared = _prepare(registry, record=_record("refused", refusal="cliniko_rejected"))
        assert isinstance(prepared, draft_write.PreparedWrite)
        assert prepared.attempt == 2

    def test_a_note_with_nothing_mapped_has_nothing_to_write(self, tmp_path: Path) -> None:
        registry, _ = _registry(tmp_path)
        consent_only = _note(sections=(_section("consent", "Consent given"),))
        assert _prepare(registry, note=consent_only) == draft_write.WriteRefusal(
            "nothing_to_write"
        )

    def test_an_unencodable_body_is_answer_unreadable(self, tmp_path: Path) -> None:
        registry, _ = _registry(tmp_path)
        content = {**_content(), "future_key": math.nan}
        assert _prepare(registry, _verified_hop1(registry, content=content)) == (
            draft_write.WriteRefusal("answer_unreadable")
        )

    def test_every_refusal_name_has_a_line(self) -> None:
        """Every ``WriteRefusalName`` resolves through
        ``write_refusal_line`` (the Note tab's one wording)."""
        for name in get_args(draft_write.WriteRefusalName):
            refusal = draft_write.WriteRefusal(
                name,
                writeback=WritebackRefused(WritebackRefusal.NOT_VERIFIED),
                question="Diagnosis",
                section="Examination",
                template="Standard Consultation",
                problem="missing",
            )
            for uncertain in (False, True):
                line = models.write_refusal_line(replace(refusal, earlier_attempt_open=uncertain))
                assert line and "{" not in line, name

    def test_the_uncertain_prefix_reaches_every_refusal_that_invites_copy(self) -> None:
        """PR-MED-017 (tested since round 25): with an earlier attempt open, every refusal
        line but the three that already speak of the write's outcome starts
        with the ``write_uncertain`` warning (PR-MED-017)."""
        warning = models.WRITE_LINES["write_uncertain"]
        unprefixed = {"already_written", "record_unreadable", "write_uncertain"}
        for name in get_args(draft_write.WriteRefusalName):
            refusal = draft_write.WriteRefusal(
                name,
                earlier_attempt_open=True,
                writeback=WritebackRefused(WritebackRefusal.NOT_VERIFIED),
                question="Diagnosis",
                section="Examination",
                template="Standard Consultation",
                problem="missing",
            )
            line = models.write_refusal_line(refusal)
            assert line.startswith(f"{warning} ") is (name not in unprefixed), name

    def test_long_or_broken_cliniko_names_always_format(self) -> None:
        """R22-07 end to end: a 300-character name, and one holding line
        breaks, reach every labelled line without ``write_line`` raising;
        the unmatched line counts the rest."""
        long, broken = "N" * 300, "Standard\nConsult ation"
        for name in ("template_mismatch", "defaults_no_template", "defaults_unmatched"):
            for label in (long, broken):
                refusal = draft_write.WriteRefusal(
                    name, question=label, section=label, template=label, more=7
                )
                line = models.write_refusal_line(refusal)
                assert "\n" not in line and " " not in line
        unmatched = models.write_refusal_line(
            draft_write.WriteRefusal(
                "defaults_unmatched", question="Aggravating", section="History", more=2
            )
        )
        assert "(Aggravating in History and 2 more)" in unmatched
        mismatch = models.write_refusal_line(
            draft_write.WriteRefusal(
                "template_mismatch", question="Assessment", section="Examination"
            )
        )
        assert mismatch.endswith(": Assessment in Examination). Copy the note instead.")


# ---------------------------------------------------------------------------
# Task 3.4: hop 1 — ONE client call, the key read once.
# ---------------------------------------------------------------------------


class TestHopOne:
    def test_a_known_template_is_read_then_the_final_note(self, tmp_path: Path) -> None:
        registry, store = _registry(tmp_path)
        cliniko = Cliniko()
        hop1 = draft_write.read_for_write(
            request_for(registry), TEMPLATE, key_store=store, transport=cliniko, clock=lambda: NOW
        )
        assert cliniko.calls == [
            ("GET", f"/v1/treatment_note_templates/{TEMPLATE}"),
            ("GET", f"/v1/treatment_notes/{NOTE}"),
        ]
        assert store.reads == 1
        assert isinstance(hop1.result.outcome, Verified)
        assert hop1.result.outcome.context.template_id == TEMPLATE
        assert hop1.template == _template() and hop1.content == _content()
        assert hop1.template_matches

    def test_no_template_id_reads_the_note_to_discover_it(self, tmp_path: Path) -> None:
        registry, store = _registry(tmp_path)
        cliniko = Cliniko()
        hop1 = draft_write.read_for_write(
            request_for(registry), None, key_store=store, transport=cliniko
        )
        assert cliniko.calls == [
            ("GET", f"/v1/treatment_notes/{NOTE}"),
            ("GET", f"/v1/treatment_note_templates/{TEMPLATE}"),
            ("GET", f"/v1/treatment_notes/{NOTE}"),
        ]
        assert store.reads == 1 and hop1.template_matches

    def test_the_final_read_not_the_discovery_read_builds_the_write(
        self, tmp_path: Path
    ) -> None:
        """Peer round 28 PR-LOW-037: with the discovery read and the final
        read answering DIFFERENTLY, the body carries the final read's
        untargeted edit (the consent box cleared between the reads) through
        preparation and the PATCH, and text typed into a targeted question
        between the reads refuses the write."""
        registry, store = _registry(tmp_path)
        discovery = ok(note_body(content=_content()))
        edited = _content()
        edited["sections"][1]["questions"][1]["answers"][0]["selected"] = False
        cliniko = Cliniko(notes=(discovery, ok(note_body(content=edited))))
        hop1 = draft_write.read_for_write(
            request_for(registry), None, key_store=store, transport=cliniko
        )
        assert hop1.content == edited
        prepared = _prepare(registry, hop1)
        assert isinstance(prepared, draft_write.PreparedWrite)
        patch = Cliniko()
        outcome = draft_write.write_for_click(
            request_for(registry), prepared, key_store=store, transport=patch
        )
        assert outcome.kind == "written"
        sent = json.loads(patch.bodies[-1] or b"{}")
        consent = sent["content"]["sections"][1]["questions"][1]
        assert consent["answers"] == [{"value": "Given", "selected": False}]
        typed = _content({_HISTORY: _NOTE_DEFAULT, "Diagnosis": "<p>typed in Cliniko</p>"})
        cliniko = Cliniko(notes=(discovery, ok(note_body(content=typed))))
        hop1 = draft_write.read_for_write(
            request_for(registry), None, key_store=store, transport=cliniko
        )
        assert _prepare(registry, hop1) == draft_write.WriteRefusal("note_has_text")

    def test_a_note_with_no_template_reads_no_template(self, tmp_path: Path) -> None:
        registry, store = _registry(tmp_path)
        cliniko = Cliniko(notes=(ok(note_body(treatment_note_template=None)),))
        hop1 = draft_write.read_for_write(
            request_for(registry), None, key_store=store, transport=cliniko
        )
        assert cliniko.calls == [("GET", f"/v1/treatment_notes/{NOTE}")]
        assert isinstance(hop1.result.outcome, Verified) and hop1.template is None
        assert _prepare(registry, hop1) == draft_write.WriteRefusal("template_mismatch")

    @pytest.mark.parametrize(
        ("answer", "expected"),
        [
            (ok(note_body(draft=False)), NoteRefused(NoteRefusal.NOTE_FINAL)),
            (status(403), NoteRefused(NoteRefusal.KEY_REJECTED)),
            (status(404), NoteRefused(NoteRefusal.NOTE_NOT_FOUND)),
        ],
    )
    def test_a_refused_discovery_read_reads_nothing_more(
        self, tmp_path: Path, answer: cc.RawResponse, expected: NoteRefused
    ) -> None:
        """Round 25 LOW-018: with no template id, a discovery read that does
        not verify ends hop 1 after ONE request."""
        registry, store = _registry(tmp_path)
        cliniko = Cliniko(notes=(answer,))
        hop1 = draft_write.read_for_write(
            request_for(registry), None, key_store=store, transport=cliniko
        )
        assert hop1.result.outcome == expected
        assert cliniko.calls == [("GET", f"/v1/treatment_notes/{NOTE}")]

    def test_a_note_re_templated_after_the_template_read_fails_closed(
        self, tmp_path: Path
    ) -> None:
        registry, store = _registry(tmp_path)
        moved = ok(note_body(content=_content(), treatment_note_template=_template_link("4002")))
        hop1 = draft_write.read_for_write(
            request_for(registry), TEMPLATE, key_store=store, transport=Cliniko(notes=(moved,))
        )
        assert isinstance(hop1.result.outcome, Verified) and not hop1.template_matches

    @pytest.mark.parametrize(
        ("overrides", "reason"),
        [
            ({"draft": False}, NoteRefusal.NOTE_FINAL),
            ({"finalized_at": "2026-09-29T01:00:00Z"}, NoteRefusal.NOTE_FINAL),
            ({"archived_at": "2026-09-29T01:00:00Z"}, NoteRefusal.NOTE_ARCHIVED),
            (
                {"patient": {"links": {"self": f"{_API}/patients/1002"}}},
                NoteRefusal.PATIENT_MISMATCH,
            ),
            (
                {"practitioner": {"links": {"self": f"{_API}/practitioners/7654322"}}},
                NoteRefusal.WRONG_PRACTITIONER,
            ),
            ({"patient": None}, NoteRefusal.ANSWER_UNREADABLE),
            ({"draft": "yes"}, NoteRefusal.ANSWER_UNREADABLE),
        ],
    )
    def test_the_final_read_is_the_click_s_verification(
        self, tmp_path: Path, overrides: dict[str, Any], reason: NoteRefusal
    ) -> None:
        registry, store = _registry(tmp_path)
        cliniko = Cliniko(notes=(ok(note_body(content=_content(), **overrides)),))
        hop1 = draft_write.read_for_write(
            request_for(registry), TEMPLATE, key_store=store, transport=cliniko
        )
        assert hop1.result.outcome == NoteRefused(reason)
        assert hop1.template is None and hop1.content is None

    @pytest.mark.parametrize(
        ("answer", "route", "reason"),
        [
            (status(401), "note", NoteRefusal.KEY_REJECTED),
            (status(403), "note", NoteRefusal.KEY_REJECTED),
            (status(403), "template", NoteRefusal.KEY_REJECTED),
            (status(401), "template", NoteRefusal.KEY_REJECTED),
            (status(404), "note", NoteRefusal.NOTE_NOT_FOUND),
            (status(404), "template", NoteRefusal.NOTE_NOT_FOUND),
            (cc.RawResponse(200, None, b"[]"), "note", NoteRefusal.ANSWER_UNREADABLE),
        ],
    )
    def test_a_refused_read_is_named(
        self, tmp_path: Path, answer: cc.RawResponse, route: str, reason: NoteRefusal
    ) -> None:
        """A 401 or 403 on EITHER read is a rejected key (P.1: a finalised
        note still answers its read with 200). A template 404 reads as the
        note's (a named residue: the note's own link named it)."""
        registry, store = _registry(tmp_path)
        cliniko = Cliniko(notes=(answer,)) if route == "note" else Cliniko(template=answer)
        hop1 = draft_write.read_for_write(
            request_for(registry), TEMPLATE, key_store=store, transport=cliniko
        )
        assert hop1.result.outcome == NoteRefused(reason)

    @pytest.mark.parametrize(("code", "rate_limited"), [(429, True), (500, False), (503, False)])
    def test_an_unanswered_read_is_offline(
        self, tmp_path: Path, code: int, rate_limited: bool
    ) -> None:
        registry, store = _registry(tmp_path)
        cliniko = Cliniko(template=status(code))
        hop1 = draft_write.read_for_write(
            request_for(registry), TEMPLATE, key_store=store, transport=cliniko
        )
        assert isinstance(hop1.result.outcome, UnverifiedOffline)
        assert hop1.result.outcome.rate_limited is rate_limited

    def test_no_key_is_key_unavailable_and_nothing_is_sent(self, tmp_path: Path) -> None:
        registry, store = _registry(tmp_path)
        store.keys.clear()
        cliniko = Cliniko()
        hop1 = draft_write.read_for_write(
            request_for(registry), TEMPLATE, key_store=store, transport=cliniko
        )
        assert hop1.result.outcome == NoteRefused(NoteRefusal.KEY_UNAVAILABLE)
        store.fail_read = True
        hop1 = draft_write.read_for_write(
            request_for(registry), TEMPLATE, key_store=store, transport=cliniko
        )
        assert hop1.result.outcome == NoteRefused(NoteRefusal.KEY_UNAVAILABLE)
        assert cliniko.calls == []

    def test_a_host_not_the_clinics_is_refused_before_the_key_is_read(
        self, tmp_path: Path
    ) -> None:
        """Round 26 LOW-001: as the Chrome note check, a clinic whose host is
        not the context's is ``clinic_mismatch`` with no key read and no
        request — never a template GET that could meet a 429."""
        registry, store = _registry(tmp_path)
        cliniko = Cliniko(template=status(429))
        for template_id in (TEMPLATE, None):
            hop1 = draft_write.read_for_write(
                request_for(registry, note_target(host=OTHER_HOST)),
                template_id,
                key_store=store,
                transport=cliniko,
            )
            assert hop1.result.outcome == NoteRefused(NoteRefusal.CLINIC_MISMATCH)
            assert not hop1.rate_limited
        assert cliniko.calls == [] and store.reads == 0

    @pytest.mark.parametrize("route", ["note", "template"])
    def test_a_failure_the_transport_raises_is_classified_on_either_read(
        self, tmp_path: Path, route: str
    ) -> None:
        """Round 26 LOW-006: a failure the transport RAISES (not a status)
        on either read — a lost connection is ``unverified_offline``, never
        rate-limited; an untrusted certificate is its own refusal."""
        registry, store = _registry(tmp_path)
        for failure in (cc.Unreachable(), cc.CertificateRejected()):
            cliniko = Cliniko(notes=(failure,)) if route == "note" else Cliniko(template=failure)
            hop1 = draft_write.read_for_write(
                request_for(registry), TEMPLATE, key_store=store, transport=cliniko
            )
            if isinstance(failure, cc.Unreachable):
                assert isinstance(hop1.result.outcome, UnverifiedOffline)
                assert not hop1.rate_limited
            else:
                assert hop1.result.outcome == NoteRefused(NoteRefusal.CERTIFICATE_REJECTED)

    def test_hop_one_only_reads(self, tmp_path: Path) -> None:
        registry, store = _registry(tmp_path)
        cliniko = Cliniko()
        draft_write.read_for_write(request_for(registry), None, key_store=store, transport=cliniko)
        assert {method for method, _ in cliniko.calls} == {"GET"}
        assert set(cliniko.bodies) == {None}


# ---------------------------------------------------------------------------
# Task 3.4: hop 2 — the PATCH in its OWN call, classified by the answer.
# ---------------------------------------------------------------------------


class TestParityWithTheNoteCheck:
    """Round 25 MED-002: hop 1's final read mirrors ``encounter._check_note``
    (the Chrome note check) — the same checks in the same order — and
    classifies a failed read with the note check's own ``_refusal_for``.
    Both run here over the same Cliniko answers and must agree, so a check
    added to one and not the other fails this test."""

    @pytest.mark.parametrize(
        "answer",
        [
            ok(note_body(content=_content())),
            ok(note_body(draft=False)),
            ok(note_body(finalized_at="2026-09-29T01:00:00Z")),
            ok(note_body(archived_at="2026-09-29T01:00:00Z")),
            ok(note_body(deleted_at="2026-09-29T01:00:00Z")),
            ok(note_body(patient={"links": {"self": f"{_API}/patients/1002"}})),
            ok(note_body(practitioner={"links": {"self": f"{_API}/practitioners/7654322"}})),
            ok(note_body(patient=None)),
            ok(note_body(draft="yes")),
            ok(note_body(treatment_note_template={"links": {"self": "not a link"}})),
            cc.RawResponse(200, None, b"[]"),
            status(401),
            status(403),
            status(404),
            status(429),
            status(500),
            status(302),
            # Round 26 LOW-006: failures the transport raises ...
            cc.Unreachable(),
            cc.CertificateRejected(),
            # ... and two faults at once, so the checks' ORDER is pinned too.
            ok(note_body(draft=False, patient={"links": {"self": f"{_API}/patients/1002"}})),
            ok(
                note_body(
                    archived_at="2026-09-29T01:00:00Z",
                    practitioner={"links": {"self": f"{_API}/practitioners/7654322"}},
                )
            ),
            ok(note_body(patient=None, draft=False)),
            # Round 27 LOW-004: a shape fault beside a patient mismatch —
            # the shape is read first in both.
            ok(note_body(draft="yes", patient={"links": {"self": f"{_API}/patients/1002"}})),
            ok(note_body(practitioner=None, patient={"links": {"self": f"{_API}/patients/1002"}})),
        ],
    )
    def test_the_write_and_the_note_check_agree(
        self, tmp_path: Path, answer: cc.RawResponse | cc.ClinikoError
    ) -> None:
        registry, store = _registry(tmp_path)
        check = encounter.verify_note_context(
            request_for(registry),
            key_store=store,
            transport=Cliniko(notes=(answer,)),
            clock=lambda: NOW,
        ).outcome
        written = draft_write.read_for_write(
            request_for(registry),
            TEMPLATE,
            key_store=store,
            transport=Cliniko(notes=(answer,)),
            clock=lambda: NOW,
        ).result.outcome
        if isinstance(check, Verified):
            assert isinstance(written, Verified)
            assert written.context == check.context
        else:
            assert written == check

    def test_a_missing_key_agrees(self, tmp_path: Path) -> None:
        registry, store = _registry(tmp_path)
        store.keys.clear()
        check = encounter.verify_note_context(
            request_for(registry), key_store=store, transport=Cliniko()
        )
        written = draft_write.read_for_write(
            request_for(registry), TEMPLATE, key_store=store, transport=Cliniko()
        )
        assert written.result.outcome == check.outcome == NoteRefused(NoteRefusal.KEY_UNAVAILABLE)

    def test_a_host_not_the_clinics_agrees_and_sends_nothing(self, tmp_path: Path) -> None:
        """Round 26 LOW-001: both refuse ``clinic_mismatch`` before any
        key read or request."""
        registry, store = _registry(tmp_path)
        stray = request_for(registry, note_target(host=OTHER_HOST))
        cliniko = Cliniko()
        check = encounter.verify_note_context(stray, key_store=store, transport=cliniko)
        written = draft_write.read_for_write(stray, TEMPLATE, key_store=store, transport=cliniko)
        assert written.result.outcome == check.outcome
        assert check.outcome == NoteRefused(NoteRefusal.CLINIC_MISMATCH)
        assert cliniko.calls == [] and store.reads == 0


class TestHopTwo:
    def _prepared(self, registry: ClinicRegistry) -> draft_write.PreparedWrite:
        prepared = _prepare(registry)
        assert isinstance(prepared, draft_write.PreparedWrite)
        return prepared

    def test_a_200_is_written_and_the_body_is_the_prepared_one(self, tmp_path: Path) -> None:
        registry, store = _registry(tmp_path)
        prepared = self._prepared(registry)
        cliniko = Cliniko(patch=cc.RawResponse(200, None, b"not json"))
        outcome = draft_write.write_for_click(
            request_for(registry), prepared, key_store=store, transport=cliniko
        )
        assert outcome == draft_write.WriteOutcome("written")
        assert cliniko.calls == [("PATCH", f"/v1/treatment_notes/{NOTE}")]
        assert cliniko.bodies == [prepared.content.to_body()]
        assert hashlib.sha256(cliniko.bodies[0] or b"").hexdigest() == prepared.body_sha256
        assert store.reads == 1

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            (403, draft_write.WriteOutcome("refused", "finalised_before_write")),
            (401, draft_write.WriteOutcome("refused", "key_rejected")),
            (404, draft_write.WriteOutcome("refused", "note_not_found")),
            (409, draft_write.WriteOutcome("refused", "cliniko_rejected")),
            (429, draft_write.WriteOutcome("unknown", rate_limited=True)),
            (500, draft_write.WriteOutcome("unknown")),
            (302, draft_write.WriteOutcome("unknown")),
            (204, draft_write.WriteOutcome("unknown")),
        ],
    )
    def test_the_answer_decides_the_outcome(
        self, tmp_path: Path, code: int, expected: draft_write.WriteOutcome
    ) -> None:
        registry, store = _registry(tmp_path)
        outcome = draft_write.write_for_click(
            request_for(registry),
            self._prepared(registry),
            key_store=store,
            transport=Cliniko(patch=status(code)),
        )
        assert outcome == expected

    def test_a_422_s_categories_reach_the_outcome(self, tmp_path: Path) -> None:
        """Round 26 LOW-007: the client's fixed D11 categories are carried
        into the outcome (the Note tab words the field categories)."""
        registry, store = _registry(tmp_path)
        body = json.dumps({"errors": {"content": ["is invalid"], "zzz": ["x"]}}).encode()
        outcome = draft_write.write_for_click(
            request_for(registry),
            self._prepared(registry),
            key_store=store,
            transport=Cliniko(patch=cc.RawResponse(422, None, body)),
        )
        assert outcome == draft_write.WriteOutcome(
            "refused", "cliniko_rejected", categories=("content", "other")
        )

    def test_a_transport_failure_is_unknown(self, tmp_path: Path) -> None:
        registry, store = _registry(tmp_path)
        for failure in (cc.Unreachable(), TimeoutError(), RuntimeError("boom")):
            outcome = draft_write.write_for_click(
                request_for(registry),
                self._prepared(registry),
                key_store=store,
                transport=Cliniko(patch=failure),
            )
            assert outcome == draft_write.WriteOutcome("unknown"), type(failure).__name__

    def test_a_key_that_cannot_be_used_sends_nothing(self, tmp_path: Path) -> None:
        registry, store = _registry(tmp_path)
        prepared = self._prepared(registry)
        cliniko = Cliniko()
        store.keys.clear()
        assert draft_write.write_for_click(
            request_for(registry), prepared, key_store=store, transport=cliniko
        ) == draft_write.WriteOutcome("refused", "key_unavailable")
        store.store(enc_context().clinic_id, KEY_SECRET_NAME, "short")
        assert draft_write.write_for_click(
            request_for(registry), prepared, key_store=store, transport=cliniko
        ) == draft_write.WriteOutcome("refused", "key_rejected")
        assert cliniko.calls == []

    @pytest.mark.parametrize(
        "change",
        [
            {"treatment_note_id": "2002"},
            {"clinic_id": "fedcba9876543210"},
            {"clinic_host": "southside.au2.cliniko.com"},
        ],
    )
    def test_a_request_for_another_note_is_refused_before_the_key_is_read(
        self, tmp_path: Path, change: dict[str, str]
    ) -> None:
        """Round 25 LOW-002: the key read is the REQUEST's clinic's and the
        PATCH goes to the PREPARED note; a pair naming different ones is a
        caller bug and sends nothing."""
        registry, store = _registry(tmp_path)
        prepared = self._prepared(registry)
        stray = replace(prepared, target=replace(prepared.target, **change))
        cliniko = Cliniko()
        with pytest.raises(ValueError, match="different notes"):
            draft_write.write_for_click(
                request_for(registry), stray, key_store=store, transport=cliniko
            )
        assert cliniko.calls == [] and store.reads == 0

    def test_each_hop_is_its_own_call_with_its_own_key_read(self, tmp_path: Path) -> None:
        """D3 end to end: hop 1 reads, the GUI step prepares, hop 2 PATCHes
        in a second call — the key read once per hop."""
        registry, store = _registry(tmp_path)
        cliniko = Cliniko()
        hop1 = draft_write.read_for_write(
            request_for(registry), TEMPLATE, key_store=store, transport=cliniko
        )
        prepared = _prepare(registry, hop1)
        assert isinstance(prepared, draft_write.PreparedWrite)
        outcome = draft_write.write_for_click(
            request_for(registry), prepared, key_store=store, transport=cliniko
        )
        assert outcome.kind == "written"
        assert [method for method, _ in cliniko.calls] == ["GET", "GET", "PATCH"]
        assert store.reads == 2

    def test_every_outcome_has_a_line(self) -> None:
        outcomes = [
            draft_write.WriteOutcome("written"),
            draft_write.WriteOutcome("unknown"),
            draft_write.WriteOutcome("unknown", rate_limited=True),
            draft_write.WriteOutcome("refused", "cliniko_rejected", categories=("content",)),
        ]
        outcomes += [
            draft_write.WriteOutcome("refused", refusal)
            for refusal in get_args(draft_write.SendRefusal)
        ]
        for outcome in outcomes:
            line = models.write_outcome_line(outcome)
            assert line and "{" not in line
        assert models.write_outcome_line(
            draft_write.WriteOutcome("refused", "finalised_before_write")
        ) == models.write_line("finalised_before_write")
        with pytest.raises(ValueError, match="names why"):
            models.write_outcome_line(draft_write.WriteOutcome("refused"))


# ---------------------------------------------------------------------------
# The module's shape.
# ---------------------------------------------------------------------------


def test_the_module_is_qt_free_and_touches_no_disk_and_no_log() -> None:
    """A TEXT-level guard over the module's imports and bare calls (not a
    proof — a name built at run time is invisible to it): no Qt, no file,
    path, OS or logging module, no ``open``, project modules by absolute
    ``from … import`` only (a module object imported so is seen by its full
    name), and from ``note_config`` / ``clinics`` only the pinned type and
    constant names — the record and
    the own-defaults file are read and written by the caller (``session`` /
    ``note_config``)."""
    tree = ast.parse(Path(draft_write.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name for alias in node.names}
            # A project module only by ``from … import`` (checked below).
            assert not any(alias.name.startswith("scribe_desktop") for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            # Round 27 LOW-005: absolute only, and each name recorded under
            # its module, so ``from scribe_desktop import session`` is seen
            # as ``scribe_desktop.session``.
            assert node.level == 0 and node.module is not None
            imported.add(node.module)
            imported |= {f"{node.module}.{alias.name}" for alias in node.names}
    banned = {
        "os",
        "io",
        "pathlib",
        "shutil",
        "tempfile",
        "logging",
        "scribe_desktop.session_store",
        "scribe_desktop.secure_storage",
        "scribe_desktop.logging_setup",
        "scribe_desktop.session",
    }
    assert not {m for m in imported if m in banned or m.split(".")[0] == "PySide6"}
    # Round 26 LOW-008: the two modules that also READ the disk
    # (``load_own_template_defaults``, ``default_config_root``, the
    # registry) are imported from by exactly these names — types and
    # constants — so a disk reader imported by name fails here.
    named: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            named.setdefault(node.module, set()).update(a.name for a in node.names)
    assert named["scribe_desktop.note_config"] == {
        "OwnDefaults",
        "OwnDefaultsProblem",
        "OwnDefaultsProblemKind",
        "TargetType",
        "TemplateProfile",
        "TemplateTarget",
    }
    assert named["scribe_desktop.clinics"] == {"KEY_SECRET_NAME", "DefaultSource", "KeyStore"}
    # ... and neither module is imported as a module object.
    assert not {"scribe_desktop.note_config", "scribe_desktop.clinics"} & {
        f"{module}.{name}" for module, names in named.items() for name in names
    }
    bare_calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not bare_calls & {"open", "print", "log_event"}
