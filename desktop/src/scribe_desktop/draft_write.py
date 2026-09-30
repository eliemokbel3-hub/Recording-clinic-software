"""The Qt-free Cliniko draft write (cliniko-draft-write plan D3–D10, D15).

One click on the Note tab's "Write draft to Cliniko" fills the OPEN Cliniko
draft the recording is linked to with the saved note, through the client's
one write (``ClinikoCall.write_draft_note`` — drafts only, by construction,
D1). This module is the whole decision; the Qt wiring (Task 5.2) only moves
its results between the GUI thread and two workers:

- HOP 1 (worker, ``read_for_write``): ONE client call, the key read once,
  ONE request — the note read, which IS the click's verification
  (``verify_note_for_write``: the note's patient, its open-draft state and
  its practitioner; no template, patient or booking read — D15). Never
  raises: a failure is a ``VerificationResult`` refusal or
  ``unverified_offline``.
- GUI thread (``prepare_write``): ``writeback_context`` over hop 1's result
  — never a stored or bridge verification (Constraint 3) — then the match
  on the note's own content, the write record's reconcile, the append and
  the FULL body, in D15's order.
- The ``attempting`` row goes to ``write.enc`` (the caller, through
  ``with_write_custody``) BEFORE hop 2 is dispatched (Constraint 5).
- HOP 2 (worker, ``write_for_click``): the PATCH alone, in its OWN client
  call; classified by the HTTP answer only (``send_write``) — a 200 is
  never relabelled, a PATCH 403 is ``finalised_before_write``.

RENDERING (Task 3.1, D7): every line comes from ``note.render_section_lines``
— the same per-section renderer behind Copy's ``render_note`` — with the
review apparatus off, under the note's OWN style (Copy's), so the chart never
receives a bullet, a provenance tag, the pre-filled mark or an "[includes …]"
line, and Copy and the write share one source for every line.

What the structure enforces: an attestation target is never yielded or
answered; the app's own rich-text answer holds no tag but ``<p>`` /
``<br>``; the body is the click's own re-read ``content`` with only the
matched questions' answers changed (every other question, checkbox array and
unknown field round-trips); a matched question's answer as read is never
removed or rewritten — an empty one receives the app's text, anything else
(typed text, a template's starting prompts, an image) is kept byte-for-byte
with ONE empty line and the app's text below it, and one the app cannot read
refuses the write (D15, ``appended_answer``); a resend after an unknown
outcome never appends twice (``write.enc`` v2's expected final digests,
which ``prepare_write`` keeps different from the before digests for every
written target); a mock note never writes (D10).

Named residues (Task 7.4 carries them to the security docs): Cliniko
documents no conditional write, so an edit saved in the Cliniko editor
between the note read and the PATCH — to ANY question — is reverted by the
full body, and text typed into a targeted question in that window is lost
because the append was built from the earlier read (P.1 Q6); an
already-open Cliniko editor's later save overwrites the written draft (P.1
Q5 — why completion is SEEN, D6); Cliniko's sanitiser rewrites rich text
(P.1 Q1) — it may rewrite or drop the empty separator paragraph — so
comparisons are over normalised visible text; an edit between an unknown
attempt and the retry makes the retry ``write_uncertain`` (fail closed); a
PATCH 403 is read as "finalised" (P.1's finalised leg), and a key that may
read but not edit notes is named by the repeat guard (``write_forbidden``)
on the next click.

Nothing here logs. No refusal, hop-2 outcome or record carries a key, a URL,
an id of a patient or practitioner, or answer text: refusals are names,
labels are template labels, the record holds ids and digests. The prepared
write and ``AlreadyWritten`` carry the verified target (the ids the PATCH
and the record need) and the prepared write the body; both are hidden from
their repr — a residue for any caller that formats a field directly.
"""

from __future__ import annotations

import copy
import hashlib
import html
import json
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Annotated, Any, Final, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)

from scribe_desktop.clinics import KEY_SECRET_NAME, KeyStore
from scribe_desktop.cliniko_client import (
    ClinikoCall,
    ClinikoClient,
    ClinikoError,
    ClinikoRejected,
    CredentialsRejected,
    DraftContent,
    DraftUnencodable,
    InvalidKey,
    NoteContent,
    NotFound,
    RateLimited,
    Transport,
)
from scribe_desktop.encounter import (
    AnswerShapeError,
    ClinicDirectory,
    ConsentAttestation,
    EncounterContext,
    NoteDisplay,
    NoteRefusal,
    NoteRefused,
    UnverifiedOffline,
    Verification,
    VerificationOutcome,
    VerificationRequest,
    VerificationResult,
    Verified,
    VerifiedTarget,
    WritebackRefused,
    WritebackSubject,
    # Package-private by name, shared deliberately (round 25 MED-002): hop 1
    # classifies a failed read exactly as the Chrome note check does.
    _offline_context,
    _refusal_for,
    check_note_id,
    link_id,
    note_state,
    writeback_context,
)
from scribe_desktop.note import (
    # Package-private by name, shared deliberately (the note.py convention):
    # the record's target ids use the profile's own id grammar.
    _ID_PATTERN,
    SECTION_TITLES,
    GeneratedNote,
    NoteStyle,
    render_section_lines,
)
from scribe_desktop.note_config import (
    TargetType,
    TemplateProfile,
    TemplateTarget,
)

# A rich-text answer's only markup: one paragraph per line; an empty line is
# kept as an empty paragraph so a blank line between prose paragraphs
# survives Cliniko's editor. It is also the ONE empty line the append puts
# between an answer already in the note and the app's text (D15) — the empty
# line Cliniko's editor itself makes.
_EMPTY_PARAGRAPH = "<p><br></p>"
# The append's empty line in a ``text`` (plain) answer (D15).
_EMPTY_LINE_PLAIN = "\n\n"
# The Cliniko question type each writable target type is (D4): a type
# mismatch refuses the write.
_QUESTION_TYPES: Final[Mapping[TargetType, str]] = {
    "rich_text": "paragraph",
    "plain_text": "text",
}
# How an answer's value is represented: a ``paragraph`` answer is HTML, a
# ``text`` answer is visible text.
Representation = Literal["html", "visible"]
_REPRESENTATIONS: Final[Mapping[str, Representation]] = {
    "paragraph": "html",
    "text": "visible",
}
_MOCK_PROVIDER_PREFIX: Final = "mock-"
_SHA256_PATTERN: Final = r"^[0-9a-f]{64}$"


# ---------------------------------------------------------------------------
# Rendering (Task 3.1, D7).
# ---------------------------------------------------------------------------


def render_targets(
    note: GeneratedNote, profile: TemplateProfile, style: NoteStyle
) -> dict[str, tuple[TemplateTarget, list[str]]]:
    """The note's lines grouped by the template target each section maps to,
    keyed by ``target_id`` in the order the targets are first reached (the
    note's canonical section order).

    Each section contributes ``render_section_lines(note, section, style,
    apparatus=False)``. When the PROFILE maps several sections to one
    target (Template A folds up to five into one question), each
    contributing section's lines are preceded by its ``SECTION_TITLES``
    heading line, so the clinician can tell them apart in the chart; a
    target only one section maps to gets no heading. A section with no
    lines, and a section the profile does not map (intentionally or by
    oversight — the template match decides whether an oversight refuses the
    write), contribute nothing. An ``attestation_checkbox`` target is never
    yielded. Every yielded line is ONE line: a line break inside a rendered
    line (LF, CRLF, CR or any other ``str.splitlines`` boundary — the note's
    types admit one, though no current producer writes one) splits it into
    lines here, every blank line kept — the one after a trailing break
    included (``_as_lines``) — so ``to_cliniko_answer`` receives only what it
    accepts. Copy's ``render_note`` is untouched by this."""
    shared: dict[str, int] = {}
    for mapping in profile.section_mappings:
        shared[mapping.target_id] = shared.get(mapping.target_id, 0) + 1
    grouped: dict[str, tuple[TemplateTarget, list[str]]] = {}
    for section in note.note_sections:
        target = profile.target_for(section.section_key)
        if target is None or target.target_type == "attestation_checkbox":
            continue
        lines = _as_lines(render_section_lines(note, section, style, apparatus=False))
        if not lines:
            continue
        if shared.get(target.target_id, 0) > 1:
            lines = [SECTION_TITLES[section.section_key], *lines]
        if target.target_id in grouped:
            grouped[target.target_id][1].extend(lines)
        else:
            grouped[target.target_id] = (target, list(lines))
    return grouped


def _as_lines(lines: Sequence[str]) -> list[str]:
    """The lines Copy's text of these lines shows: ``lines`` joined with
    newlines — exactly as ``render_note`` joins them — then split ONCE on
    every line boundary, every blank line kept. Splitting the joined text,
    not each line, keeps a CRLF that ``render_section_lines`` split in two
    (its prose branch splits on ``"\\n"`` alone, leaving ``"First.\\r"``)
    ONE break; and a text ENDING in a break keeps the empty line after it
    (``str.splitlines`` alone drops it). So ``"First.\\n"`` then
    ``"Second."`` gives ``["First.", "", "Second."]`` — the blank line Copy
    shows between them."""
    if not lines:
        return []
    text = "\n".join(lines)
    split = text.splitlines() or [""]
    if text and text.splitlines(keepends=True)[-1] != split[-1]:
        split.append("")
    return split


def to_cliniko_answer(lines: Sequence[str], target_type: TargetType) -> str:
    """One target's lines as the answer Cliniko stores for its question.

    ``rich_text`` (a Cliniko ``paragraph`` question, stored as sanitised
    HTML): one ``<p>`` per line with the text escaped by
    ``html.escape(text, quote=True)`` — ``&``, ``<``, ``>``, ``"`` and ``'``
    never reach the chart as markup — and an empty or whitespace-only line as
    ``<p><br></p>``; no other tag is ever emitted. ``plain_text`` (a ``text``
    question): the lines joined by newlines, never HTML-escaped. An
    ``attestation_checkbox`` is refused: the app never answers an
    attestation.

    ``lines`` must be LINES: a bare string (one ``<p>`` per character) and a
    line holding a line break (a paragraph break lost inside one ``<p>``)
    raise ``ValueError``. ``render_section_lines`` can yield a line holding a
    break (the note's types admit one); ``render_targets`` splits it before
    the lines get here."""
    if isinstance(lines, str):
        raise ValueError("an answer is built from a sequence of lines, not one string")
    if any("\n" in line or "\r" in line for line in lines):
        raise ValueError("an answer line must not hold a line break")
    if target_type == "rich_text":
        return "".join(
            f"<p>{html.escape(line, quote=True)}</p>" if line.strip() else _EMPTY_PARAGRAPH
            for line in lines
        )
    if target_type == "plain_text":
        return "\n".join(lines)
    raise ValueError("an attestation target is never answered by this app")


# ---------------------------------------------------------------------------
# Normalised comparison (Task 3.2, D4 — PR-HIGH-009, PR-MED-016; D15).
# ---------------------------------------------------------------------------

# The tags whose boundary is a line break in the visible text: block elements
# and ``<br>``.
_BREAK_TAGS: Final = frozenset(
    {
        "p", "div", "br", "li", "ul", "ol", "blockquote", "pre",
        "h1", "h2", "h3", "h4", "h5", "h6", "table", "tr", "td", "th",
    }
)  # fmt: skip
# The tags that only format TEXT. Any other tag (an image, a rule, an embed)
# may be content with no text, so an answer holding one is never "empty"
# (``appended_answer`` keeps it and appends below it — D15). A link's target
# and a formatting change are not text either way — D4 compares visible text
# only.
_TEXT_TAGS: Final = _BREAK_TAGS | frozenset(
    {
        "span", "strong", "b", "em", "i", "u", "s", "strike", "sub", "sup",
        "a", "code", "mark", "small", "font", "tbody", "thead", "tfoot",
    }
)  # fmt: skip


class AnswerUnparseable(ValueError):
    """An HTML answer the parser could not read. Fixed text, raised outside
    any handler: the parser's own error can quote the answer."""

    def __init__(self) -> None:
        super().__init__("an answer could not be read as HTML")


class _VisibleText(HTMLParser):
    """HTML to the text an editor shows: a block or ``<br>`` boundary is a
    line break, every other tag is dropped, character references are
    decoded ONCE (``convert_charrefs``), and a line break inside text data
    is whitespace — as HTML renders it. ``opaque``: a tag outside
    ``_TEXT_TAGS`` was seen."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.opaque = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in _TEXT_TAGS:
            self.opaque = True
        if tag in _BREAK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _BREAK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data.replace("\r", " ").replace("\n", " "))


def _parsed(value: str) -> _VisibleText:
    """``value`` through ``_VisibleText``; ``AnswerUnparseable`` for any
    parser failure (a malformed declaration can make the stdlib parser
    raise, quoting the input)."""
    parser = _VisibleText()
    failed = False
    try:
        parser.feed(value)
        parser.close()
    except Exception:  # noqa: BLE001 - any parser failure: fail closed, content-free
        failed = True
    if failed:
        raise AnswerUnparseable()  # outside the except: no chained detail
    return parser


def html_to_visible(value: str) -> str:
    """An API ``paragraph`` answer (an HTML REPRESENTATION) as visible text,
    decoded exactly once: ``<p>a</p><p>b</p>`` and ``a<br>b`` both give
    lines ``a`` and ``b``, never ``ab``; ``&amp;lt;`` gives ``&lt;``.
    ``AnswerUnparseable`` when the parser fails."""
    return "".join(_parsed(value).parts)


def holds_opaque_content(value: str, representation: Representation) -> bool:
    """True when an HTML answer holds a tag that is not text formatting (an
    image, a rule, an embed) — content the visible text does not show.
    ``AnswerUnparseable`` when the parser fails."""
    return representation == "html" and _parsed(value).opaque


def normalise_visible(text: str) -> str:
    """Visible text for comparison: NFC, whitespace within each line
    collapsed to single spaces, blank lines dropped, lines joined by
    ``\\n``. Never HTML-decodes."""
    text = unicodedata.normalize("NFC", text)
    lines = (" ".join(line.split()) for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def normalise_answer(value: str, representation: Representation) -> str:
    """THE comparison form of an answer — emptiness and digests alike (D4,
    D15): an HTML representation is converted to visible text ONCE; visible
    text (a ``text`` answer) never is; then ``normalise_visible``. Only a
    comparison form: nothing written is ever built from it.
    ``AnswerUnparseable`` from the HTML parser — every caller here fails
    closed on it."""
    if representation == "html":
        value = html_to_visible(value)
    return normalise_visible(value)


def answer_digest(normalised: str) -> str:
    """SHA-256 hex of a normalised answer — what the write record keeps
    instead of the text (D5). ``surrogatepass`` so a lone surrogate from a
    JSON escape digests instead of raising."""
    return hashlib.sha256(normalised.encode("utf-8", "surrogatepass")).hexdigest()


# ---------------------------------------------------------------------------
# The template match (Task 3.2, D4; on the note's own content only — D15).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MatchedQuestion:
    """One writable target found, exactly once and of its type, in the
    note's own content."""

    target: TemplateTarget
    section_name: str
    question_name: str
    representation: Representation
    # (section index, question index) in the note's content.
    note_position: tuple[int, int]


@dataclass(frozen=True)
class Match:
    """Every writable target of the profile, matched — keyed by target id."""

    questions: Mapping[str, MatchedQuestion]


@dataclass(frozen=True)
class TemplateMismatch:
    """The note's content does not match the profile. ``question`` and
    ``section`` name the target that failed (the profile's own labels) when
    one did; both None for a profile or structure problem."""

    question: str | None = None
    section: str | None = None


def _structure(sections: object) -> list[dict[str, Any]] | None:
    """``sections`` as a list of sections each with a string ``name`` and a
    ``questions`` list of objects each with a string ``name`` and ``type``;
    None for any other shape (fail closed)."""
    if not isinstance(sections, list):
        return None
    for section in sections:
        if not isinstance(section, dict) or not isinstance(section.get("name"), str):
            return None
        questions = section.get("questions")
        if not isinstance(questions, list):
            return None
        for question in questions:
            if not (
                isinstance(question, dict)
                and isinstance(question.get("name"), str)
                and isinstance(question.get("type"), str)
            ):
                return None
    return sections


def _note_sections(note_content: object) -> list[dict[str, Any]] | None:
    return _structure(note_content.get("sections")) if isinstance(note_content, dict) else None


def _find(
    sections: list[dict[str, Any]], section_name: str, question_name: str
) -> tuple[int, int, str] | None:
    """The one (section index, question index, type) named so; None when the
    section or the question is absent or named more than once."""
    matches = [index for index, s in enumerate(sections) if s["name"] == section_name]
    if len(matches) != 1:
        return None
    section_index = matches[0]
    questions = sections[section_index]["questions"]
    found = [index for index, q in enumerate(questions) if q["name"] == question_name]
    if len(found) != 1:
        return None
    question_index = found[0]
    return section_index, question_index, questions[question_index]["type"]


def match_template(
    profile: TemplateProfile | None, note_content: object
) -> Match | TemplateMismatch:
    """Name-based match (D4) of every WRITABLE target the profile maps — by
    (section name, question name) — in the note's own ``content`` (D15: the
    template itself is never read). Refused (``TemplateMismatch``): no
    profile; a canonical section the profile leaves unmapped by oversight
    (``unmapped_section_keys``); content that is not a well-formed section
    list; and, naming the target, a section or question missing or named
    twice, a question whose Cliniko type is not the target's (``paragraph``
    for rich text, ``text`` for plain text), or a question an earlier target
    of the profile already names (one question, one target). The attestation
    target is never matched: its question round-trips untouched."""
    if profile is None or profile.unmapped_section_keys():
        return TemplateMismatch()
    note_secs = _note_sections(note_content)
    if note_secs is None:
        return TemplateMismatch()
    mapped = {mapping.target_id for mapping in profile.section_mappings}
    questions: dict[str, MatchedQuestion] = {}
    # Two targets naming ONE question would have the second answer overwrite
    # the first in the body while the record lists both (round 27 LOW-001).
    taken: set[tuple[int, int]] = set()
    for target in profile.template_targets:
        if target.target_id not in mapped or target.target_type == "attestation_checkbox":
            continue
        expected = _QUESTION_TYPES[target.target_type]
        in_note = _find(note_secs, target.group, target.field_label)
        if in_note is None or in_note[2] != expected or in_note[:2] in taken:
            return TemplateMismatch(target.field_label, target.group)
        taken.add(in_note[:2])
        questions[target.target_id] = MatchedQuestion(
            target=target,
            section_name=target.group,
            question_name=target.field_label,
            representation=_REPRESENTATIONS[expected],
            note_position=(in_note[0], in_note[1]),
        )
    return Match(questions=questions)


def match_digest(match: Match, target_ids: Sequence[str]) -> str | None:
    """The SHA-256 of WHERE ``target_ids`` are written under ``match``: each
    target's (section name, question name, representation), sorted by target
    id — template labels, hashed, never answer text (D5's content-free
    record). None when a target is not in the match. An open attempt's
    record carries the one it was written under, so a profile change between
    the attempt and the retry — a written target unmapped, or moved to
    another question — is seen (peer round 28 PR-MED-036)."""
    rows: list[list[str]] = []
    for target_id in sorted(target_ids):
        matched = match.questions.get(target_id)
        if matched is None:
            return None
        rows.append(
            [target_id, matched.section_name, matched.question_name, matched.representation]
        )
    canonical = json.dumps(rows, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def _answer_at(sections: list[dict[str, Any]], position: tuple[int, int]) -> object:
    return sections[position[0]]["questions"][position[1]].get("answer")


# ---------------------------------------------------------------------------
# The append (D15): an answer already in the note is kept, never replaced.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NoteUnreadable:
    """A matched question's answer the app cannot read — neither a string
    nor null, or HTML the parser cannot read: the app never appends to what
    it cannot read, so nothing is sent (D15, ``note_unreadable``)."""


def appended_answer(
    existing: object, new: str, representation: Representation
) -> str | NoteUnreadable:
    """The FINAL answer of one matched question (D15, Constraint 4), with
    ``existing`` its answer as the click's note read returned it and ``new``
    the app's answer (``to_cliniko_answer``, NFC):

    - EMPTY — absent or null, or a string whose visible text
      (``normalise_answer``) is empty and that holds no opaque content
      (``holds_opaque_content``; a blank paragraph or whitespace is not
      writing): ``new``;
    - NON-EMPTY — any other string, typed text and a template's starting
      prompts alike, an image or a rule included: ``existing``
      BYTE-FOR-BYTE (never re-rendered, never normalised), then ONE empty
      line — ``<p><br></p>`` for an HTML answer, ``"\\n\\n"`` for a plain
      one — then ``new``;
    - UNREADABLE — anything else, or HTML the parser cannot read:
      ``NoteUnreadable``.

    The normalised form decides emptiness only; nothing written is built
    from it."""
    if existing is None:
        return new
    if not isinstance(existing, str):
        return NoteUnreadable()
    try:
        empty = not normalise_answer(existing, representation) and not holds_opaque_content(
            existing, representation
        )
    except AnswerUnparseable:
        return NoteUnreadable()
    if empty:
        return new
    separator = _EMPTY_PARAGRAPH if representation == "html" else _EMPTY_LINE_PLAIN
    return existing + separator + new


def answer_digests(note_content: object, match: Match) -> dict[str, str]:
    """The digest of each matched target's normalised answer in the note —
    reconcile's comparison with the record's final and before digests (D5,
    D15); an absent or null answer digests as empty. A target whose answer
    is neither a string nor null, or is HTML the parser cannot read, has no
    digest here, so it never compares equal."""
    sections = _note_sections(note_content)
    if sections is None:
        return {}
    digests: dict[str, str] = {}
    for target_id, matched in match.questions.items():
        answer = _answer_at(sections, matched.note_position)
        if answer is None:
            answer = ""
        if not isinstance(answer, str):
            continue
        try:
            digests[target_id] = answer_digest(normalise_answer(answer, matched.representation))
        except AnswerUnparseable:
            continue
    return digests


@dataclass(frozen=True)
class AnswerUnreadable:
    """The body could not be built as strict UTF-8 JSON (a lone surrogate, a
    NaN anywhere in the content): nothing is sent (D4)."""


def build_body(
    note_content: object, match: Match, answers: Mapping[str, str]
) -> DraftContent | AnswerUnreadable:
    """The FULL body (Task 2.1): the click's re-read ``content`` with only
    ``answers`` (target id → final Cliniko answer) put into their matched
    questions, EXACTLY as given — never normalised here, because a final
    answer can begin with the note's own answer, kept byte-for-byte (D15);
    the caller NFC-normalises the app's part (``prepare_write``). Every
    other key, question, checkbox array and unknown field is kept as read.
    Built and ENCODED here (strict UTF-8, no NaN) so an unencodable body
    refuses before any attempt row is written. ``ValueError`` for an answer
    naming a target the match lacks."""
    if not isinstance(note_content, dict) or _note_sections(note_content) is None:
        return AnswerUnreadable()
    content = copy.deepcopy(note_content)
    sections = content["sections"]
    for target_id, answer in answers.items():
        matched = match.questions.get(target_id)
        if matched is None:
            raise ValueError("an answer names a target the template match does not hold")
        section_index, question_index = matched.note_position
        sections[section_index]["questions"][question_index]["answer"] = answer
    try:
        body = DraftContent(content=NoteContent.model_validate(content))
        body.to_body()
    except (DraftUnencodable, ValidationError):
        return AnswerUnreadable()
    return body


# ---------------------------------------------------------------------------
# The write record ``write.enc`` (Task 3.3, D5).
# ---------------------------------------------------------------------------

RecordOutcome = Literal["attempting", "written", "refused", "unknown"]
# Why hop 2's PATCH was not applied (``refused``): Cliniko's clean answer, or
# nothing sent at all (``key_unavailable``, ``key_rejected`` for a key
# refused before any request).
SendRefusal = Literal[
    "finalised_before_write",
    "key_rejected",
    "key_unavailable",
    "note_not_found",
    "cliniko_rejected",
]
_OPEN_OUTCOMES: Final[frozenset[str]] = frozenset({"attempting", "unknown"})
_Sha256 = Annotated[str, StringConstraints(pattern=_SHA256_PATTERN)]
_TargetId = Annotated[str, StringConstraints(pattern=_ID_PATTERN)]


class WriteRecord(BaseModel):
    """``write.enc``'s ONE document (D5; schema v2 — D15): the attempt
    number, when it started, the targets written, the saved note's identity
    (SHA-256 of the saved ``note.enc`` plaintext), per target the digest of
    the EXPECTED FINAL answer (``digests``: the answer as read with the app's
    text appended, normalised) and of the answer AS READ by the click that
    built the attempt (``before_digests``; an empty answer digests ``""``),
    the digest of WHERE they were written (``match_digest``: the questions'
    labels, hashed), the body's digest, the outcome and — for ``refused`` —
    why, and when it finished. Ids and digests only: never note text, never
    Cliniko's answer. A trailing ``attempting`` (a crash before the outcome)
    is read as ``unknown``. A schema-v1 document (Phases 3–6: default
    digests, no before digests) is not this schema: unreadable, fail
    closed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[2] = 2
    attempt: int = Field(ge=1)
    started_at: AwareDatetime
    target_ids: tuple[_TargetId, ...] = Field(min_length=1)
    note_identity: _Sha256
    digests: Mapping[_TargetId, _Sha256]
    before_digests: Mapping[_TargetId, _Sha256]
    match_sha256: _Sha256
    body_sha256: _Sha256
    outcome: RecordOutcome
    refusal: SendRefusal | None = None
    finished_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def _consistent(self) -> WriteRecord:
        written = set(self.target_ids)
        if (
            set(self.digests) != written
            or set(self.before_digests) != written
            or len(written) != len(self.target_ids)
        ):
            raise ValueError("the digests name exactly the written targets")
        if (self.refusal is not None) != (self.outcome == "refused"):
            raise ValueError("a refusal is recorded exactly for a refused outcome")
        if (self.finished_at is None) != (self.outcome == "attempting"):
            raise ValueError("an attempt is finished exactly when its outcome is known")
        return self

    @property
    def open_attempt(self) -> bool:
        """An outcome the app never learned: ``attempting`` or ``unknown``."""
        return self.outcome in _OPEN_OUTCOMES

    def to_bytes(self) -> bytes:
        return self.model_dump_json().encode("utf-8")


class WriteRecordUnreadable(Exception):
    """``write.enc`` exists but cannot be read, authenticated or parsed —
    its outcome cannot be known (D5's ``record_unreadable``). Terse on
    purpose."""

    def __init__(self) -> None:
        super().__init__("the write record is unreadable")


def parse_write_record(plaintext: bytes) -> WriteRecord:
    """``write.enc``'s decrypted document; ``WriteRecordUnreadable`` (with
    no chained detail — pydantic's would echo the document) for anything
    that is not this schema."""
    try:
        return WriteRecord.model_validate_json(plaintext)
    except (ValidationError, ValueError):
        pass
    raise WriteRecordUnreadable()  # outside the except: no chained detail


class RecordUnreadable:
    """A loaded-record marker for a ``write.enc`` that exists but cannot be
    read (``WriteRecordUnreadable``) — what ``prepare_write`` and
    ``record_status`` receive in its place."""


RECORD_UNREADABLE: Final = RecordUnreadable()

StatusOutcome = Literal["none", "unreadable", "attempting", "unknown", "refused", "written"]


@dataclass(frozen=True)
class WriteRecordStatus:
    """What the session's write record says, CONTENT-FREE (D5, R22-03): its
    outcome (``none`` — no ``write.enc``; ``unreadable``), whether its
    ``note_identity`` equals the saved note's, and for ``refused`` why."""

    outcome: StatusOutcome
    note_matches: bool = False
    refusal: SendRefusal | None = None

    @property
    def open_attempt(self) -> bool:
        return self.outcome in _OPEN_OUTCOMES

    @property
    def written(self) -> bool:
        """A write Cliniko took, for THIS saved note — the only record a
        seen-mode Complete consumes (D6)."""
        return self.outcome == "written" and self.note_matches


def record_status(
    record: WriteRecord | RecordUnreadable | None, saved_note_identity: str | None
) -> WriteRecordStatus:
    """The content-free status of a loaded record (D5): ``none`` for no
    record, ``unreadable`` for one that could not be read; otherwise its
    outcome, whether its ``note_identity`` is ``saved_note_identity`` (None:
    the saved note could not be read — never a match), and why for
    ``refused``."""
    if isinstance(record, RecordUnreadable):
        return WriteRecordStatus("unreadable")
    if record is None:
        return WriteRecordStatus("none")
    matches = saved_note_identity is not None and saved_note_identity == record.note_identity
    return WriteRecordStatus(record.outcome, matches, record.refusal)


@dataclass(frozen=True)
class ReconciledWritten:
    """Cliniko already holds this session's write: no second PATCH (D5)."""


@dataclass(frozen=True)
class NextAttempt:
    """Nothing of the earlier attempt landed (an open attempt whose answers
    are still as that attempt read them) or Cliniko applied nothing (a
    ``refused`` attempt): the write may proceed as the next attempt, built
    from the CURRENT read (D15)."""


@dataclass(frozen=True)
class Uncertain:
    """An earlier write may have reached Cliniko (or the record is not this
    saved note's): never write again, never a bare Copy suggestion."""


def _digests_equal(expected: Mapping[str, str], note_content: object, match: Match) -> bool:
    current = answer_digests(note_content, match)
    return bool(expected) and all(
        current.get(target_id) == digest for target_id, digest in expected.items()
    )


def confirm_written(
    record: WriteRecord, note_content: object, match: Match, saved_note_identity: str
) -> ReconciledWritten | Uncertain | None:
    """Reconcile's first half (D5, D15):

    - a record that is not this saved note's (``note_identity`` differs) is
      ``Uncertain`` — never written, never completed;
    - a ``written`` record is ``ReconciledWritten``;
    - an OPEN record (``attempting`` / ``unknown``) written under another
      match — a recorded target no longer matched, or matched to another
      question (``match_digest`` differs: the profile changed since) — is
      ``Uncertain``: the earlier answer may sit in a question the current
      match no longer reads, so neither the digests nor the retry check
      could see it (peer round 28 PR-MED-036);
    - an OPEN record whose recorded targets all digest equal to their
      EXPECTED FINAL answers (``digests``) — and there is at least one — is
      ``ReconciledWritten``: the earlier PATCH landed, so a resend would
      append the text twice (D15); a ``refused`` one never is (Cliniko
      applied nothing, so a changed match is harmless there);
    - None: not decided here (``retry_verdict`` decides)."""
    if record.note_identity != saved_note_identity:
        return Uncertain()
    if record.outcome == "written":
        return ReconciledWritten()
    if record.open_attempt and match_digest(match, record.target_ids) != record.match_sha256:
        return Uncertain()
    if record.open_attempt and _digests_equal(record.digests, note_content, match):
        return ReconciledWritten()
    return None


def retry_verdict(
    record: WriteRecord, note_content: object, match: Match
) -> NextAttempt | Uncertain:
    """Reconcile's second half, for a record ``confirm_written`` left
    undecided (D15): a ``refused`` record is ``NextAttempt`` (Cliniko
    applied nothing); an OPEN record whose recorded targets all digest equal
    to their answers AS THAT ATTEMPT READ THEM (``before_digests``: nothing
    landed and nothing changed) is ``NextAttempt``; any other open record
    is ``Uncertain`` — something changed since, and the app cannot tell
    whether it was its own write (fail closed; Copy remains). The next
    attempt is rebuilt from the current read, so an edit is never lost to
    a stale append."""
    if not record.open_attempt:
        return NextAttempt()
    if _digests_equal(record.before_digests, note_content, match):
        return NextAttempt()
    return Uncertain()


def attempt_record(prepared: PreparedWrite, *, now: datetime) -> WriteRecord:
    """The ``attempting`` row written BEFORE hop 2 (Constraint 5)."""
    return WriteRecord(
        attempt=prepared.attempt,
        started_at=now,
        target_ids=prepared.target_ids,
        note_identity=prepared.note_identity,
        digests=prepared.digests,
        before_digests=prepared.before_digests,
        match_sha256=prepared.match_sha256,
        body_sha256=prepared.body_sha256,
        outcome="attempting",
    )


def _updated(record: WriteRecord, **update: object) -> WriteRecord:
    """``record`` with ``update`` applied and RE-VALIDATED (``model_copy``
    skips validation, so a transition could otherwise break the record's
    own consistency rules)."""
    return WriteRecord.model_validate({**record.model_dump(), **update})


def finished_record(record: WriteRecord, outcome: WriteOutcome, *, now: datetime) -> WriteRecord:
    """The ``attempting`` record once hop 2 answered: its outcome, and why
    for refused. ``ValueError`` for any other record (a finished outcome is
    never overwritten)."""
    if record.outcome != "attempting":
        raise ValueError("only an attempting record is finished")
    return _updated(record, outcome=outcome.kind, refusal=outcome.refusal, finished_at=now)


def reconciled_record(record: WriteRecord, *, now: datetime) -> WriteRecord:
    """An OPEN record reconcile found written: ``written``, no PATCH.
    ``ValueError`` for a record whose outcome is known (``refused`` is never
    confirmed ``written``)."""
    if not record.open_attempt:
        raise ValueError("only an open attempt is reconciled")
    return _updated(record, outcome="written", refusal=None, finished_at=now)


# ---------------------------------------------------------------------------
# Hop 1: the click's own read (Task 3.4, D3 as amended by D15).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NoteRead:
    """The note read: the click's verification and the note's raw
    ``content`` (None unless verified)."""

    outcome: VerificationOutcome
    content: object = field(default=None, repr=False)


def verify_note_for_write(
    call: ClinikoCall, request: VerificationRequest, clock: Callable[[], datetime] | None = None
) -> NoteRead:
    """Hop 1's ONE request, the note read — the click's verification (D3,
    D15): the answer must carry the requested note's own ``id`` (H3 round 47
    SEC-002), the note's patient link must be the context's, the note an open
    draft (``note_state``), its practitioner the clinic's. No template,
    patient or booking read, so it sits as close to the PATCH as the design
    allows. Raises the client's named errors and ``AnswerShapeError`` for
    the caller to map.

    The checks and their ORDER mirror ``encounter._check_note`` (the Chrome
    note check), which also reads the patient and booking for display; the
    two cannot share code without that read. ``test_draft_write.py``'s
    parity test runs both over the same answers and pins the same outcome."""
    clinic = request.clinic
    target = request.target
    if clinic.host != target.clinic_host:
        return NoteRead(NoteRefused(NoteRefusal.CLINIC_MISMATCH))
    note = call.get_treatment_note(target.note_id)
    check_note_id(note, target.note_id)  # H3 round 47 SEC-002
    state = note_state(note)
    patient_id = link_id(note, "patient", "patients")
    practitioner_id = link_id(note, "practitioner", "practitioners")
    if patient_id is None or practitioner_id is None:
        raise AnswerShapeError()
    if patient_id != target.patient_id:
        return NoteRead(NoteRefused(NoteRefusal.PATIENT_MISMATCH))
    if state is not None:
        return NoteRead(NoteRefused(state))
    if practitioner_id != clinic.practitioner_id:
        return NoteRead(NoteRefused(NoteRefusal.WRONG_PRACTITIONER))
    now = clock() if clock is not None else datetime.now(UTC)
    context = EncounterContext(
        clinic_id=clinic.clinic_id,
        clinic_host=target.clinic_host,
        patient_id=target.patient_id,
        treatment_note_id=target.note_id,
        booking_id=link_id(note, "booking", None),
        practitioner_id=practitioner_id,
        template_id=link_id(note, "treatment_note_template", None),
        verification=Verification.VERIFIED,
        verified_at=now,
    )
    # Display strings are never read for a write (no patient read): empty.
    verified = Verified(context, NoteDisplay("", None))
    return NoteRead(verified, note.get("content"))


@dataclass(frozen=True)
class Hop1Result:
    """What hop 1 hands the GUI thread. ``result`` is the click's
    verification (the note read), a named refusal, or ``unverified_offline``
    (``rate_limited`` for a 429). ``content`` is set only when the note
    verified."""

    result: VerificationResult
    content: object = field(default=None, repr=False)

    @property
    def rate_limited(self) -> bool:
        """Hop 1 met a 429: the caller records it in the latch (D13) and
        shows ``rate_limited`` — ``prepare_write`` would only see an
        unverified note (``not_verified``)."""
        outcome = self.result.outcome
        return isinstance(outcome, UnverifiedOffline) and outcome.rate_limited


class _KeyUnavailable(Exception):
    pass


def _key_reader(key_store: KeyStore, clinic_id: str) -> Callable[[], str | None]:
    def read_key() -> str | None:
        try:
            key = key_store.retrieve(clinic_id, KEY_SECRET_NAME)
        except Exception as exc:  # noqa: BLE001 - keyring backends raise their own types
            raise _KeyUnavailable() from exc
        if not key:
            raise _KeyUnavailable()
        return key

    return read_key


def read_for_write(
    request: VerificationRequest,
    *,
    key_store: KeyStore,
    transport: Transport | None = None,
    clock: Callable[[], datetime] | None = None,
) -> Hop1Result:
    """Worker thread: HOP 1 as ONE client call, the key read once, ONE
    request — the note read (``verify_note_for_write``; D3 as amended by
    D15). A clinic whose host is not the context's is ``clinic_mismatch``
    before the key read. Never raises: a missing key is ``key_unavailable``,
    a client error the note check's own classification
    (``encounter._refusal_for``: a 401 or 403 is a rejected key — P.1
    showed a finalised note still answers its read with 200 — and a
    connection failure, 5xx or 429 ``unverified_offline``), anything else
    ``answer_unreadable``."""
    outcome: VerificationOutcome
    try:
        return _hop1(request, key_store, transport, clock)
    except _KeyUnavailable:
        outcome = NoteRefused(NoteRefusal.KEY_UNAVAILABLE)
    except ClinikoError as error:
        reason = _refusal_for(error)
        outcome = (
            UnverifiedOffline(
                _offline_context(request), rate_limited=isinstance(error, RateLimited)
            )
            if reason is None
            else NoteRefused(reason)
        )
    except Exception:  # noqa: BLE001 - AnswerShapeError, InvalidId, the unforeseen: never raise
        outcome = NoteRefused(NoteRefusal.ANSWER_UNREADABLE)
    # Only the outcome leaves: the exception, whose frames hold the key, goes
    # with its block (threat-model Cliniko residue (6)).
    return Hop1Result(VerificationResult(request=request, outcome=outcome))


def _hop1(
    request: VerificationRequest,
    key_store: KeyStore,
    transport: Transport | None,
    clock: Callable[[], datetime] | None,
) -> Hop1Result:
    # As ``encounter._verify``: a clinic whose host is not the context's is
    # refused before the key is read or anything is sent (round 26 LOW-001).
    if request.clinic.host != request.target.clinic_host:
        return Hop1Result(VerificationResult(request, NoteRefused(NoteRefusal.CLINIC_MISMATCH)))
    client = ClinikoClient(contact_email=request.contact_email, transport=transport)
    with client.call(_key_reader(key_store, request.clinic.clinic_id)) as call:
        read = verify_note_for_write(call, request, clock)
    result = VerificationResult(request=request, outcome=read.outcome)
    if not isinstance(read.outcome, Verified):
        return Hop1Result(result)
    return Hop1Result(result, content=read.content)


# ---------------------------------------------------------------------------
# The GUI-thread step between the hops (Task 3.4).
# ---------------------------------------------------------------------------


WriteRefusalName = Literal[
    "mock_note",
    "record_unreadable",
    "already_written",
    "writeback_refused",
    "template_mismatch",
    "write_uncertain",
    "write_forbidden",
    "nothing_to_write",
    "note_unreadable",
    "answer_unreadable",
]


@dataclass(frozen=True)
class WriteRefusal:
    """Why a click writes nothing, by name (``ui.models.write_refusal_line``
    words it). ``earlier_attempt_open``: the record holds an EARLIER
    ``attempting`` / ``unknown`` attempt, so the line is prefixed by the
    ``write_uncertain`` warning (PR-MED-017). ``question`` / ``section``
    (``template_mismatch``) are the profile's labels of the question and its
    section, apart. Names only, never answer text."""

    name: WriteRefusalName
    earlier_attempt_open: bool = False
    writeback: WritebackRefused | None = None
    question: str | None = None
    section: str | None = None


@dataclass(frozen=True)
class PreparedWrite:
    """Everything hop 2 and the ``attempting`` row need: the verified
    target (repr-hidden: it holds the patient's and practitioner's ids), the
    FULL body (repr-hidden: it is note text), the attempt number, the
    targets written with the digests of their expected final answers and of
    their answers as read (D15), where they are written (``match_digest``),
    the body's digest and the saved note's identity."""

    target: VerifiedTarget = field(repr=False)
    content: DraftContent = field(repr=False)
    attempt: int
    target_ids: tuple[str, ...]
    digests: Mapping[str, str]
    before_digests: Mapping[str, str]
    match_sha256: str
    body_sha256: str
    note_identity: str


@dataclass(frozen=True)
class AlreadyWritten:
    """Reconcile found this session's earlier write in Cliniko: record it
    ``written`` (``reconciled_record``) — no PATCH (D5). ``target`` is
    repr-hidden: it holds the patient's and practitioner's ids."""

    target: VerifiedTarget = field(repr=False)


def is_mock_note(note: GeneratedNote) -> bool:
    """D10: a note from the test provider never reaches a chart."""
    return note.provider_name.startswith(_MOCK_PROVIDER_PREFIX)


def refuse_before_read(
    note: GeneratedNote,
    record: WriteRecord | RecordUnreadable | None,
    note_identity: str,
) -> WriteRefusal | None:
    """The refusals that need no Cliniko read (D5, D10): a mock note
    (``mock_note``); an unreadable record (``record_unreadable``); a record
    already ``written`` — for THIS saved note ``already_written`` (the
    seen-mode line), for another ``write_uncertain`` (never completed).
    None: the click may read.

    The click (Task 5.2) must run this BEFORE dispatching hop 1 — that is
    what keeps those cases free of any request. ``prepare_write`` runs it
    again first, so a direct caller gets the same answer; by then hop 1's
    reads have already been made."""
    if is_mock_note(note):
        return WriteRefusal("mock_note")
    if isinstance(record, RecordUnreadable):
        return WriteRefusal("record_unreadable")
    if record is not None and record.outcome == "written":
        if record.note_identity != note_identity:
            return WriteRefusal("write_uncertain")
        return WriteRefusal("already_written")
    return None


def prepare_write(
    hop1: Hop1Result,
    *,
    consent: ConsentAttestation | None,
    context: EncounterContext | None,
    clinics: ClinicDirectory,
    record: WriteRecord | RecordUnreadable | None,
    note: GeneratedNote,
    note_identity: str,
    profile: TemplateProfile | None,
) -> PreparedWrite | AlreadyWritten | WriteRefusal:
    """GUI thread, between the hops: the whole decision, in D15's order,
    after ``refuse_before_read`` (which the click must already have run
    before hop 1 — see there):

    1. ``writeback_context`` over hop 1's OWN result (never a stored one);
    2. the match on the note's own content (``match_template``);
    3. ``confirm_written``: the saved note's identity (a mismatch is
       ``write_uncertain``) and, for an OPEN record, the match it was
       written under (another is ``write_uncertain``) and the expected
       final digests — which establish ``written`` with no PATCH, so a
       resend never appends twice;
    4. the repeat guard: a record refused ``finalised_before_write`` whose
       note re-reads as a draft is ``write_forbidden`` (R22-02);
    5. ``retry_verdict``: an open record whose answers are still as its
       attempt read them, or a ``refused`` one → the next attempt; any
       other open record → ``write_uncertain``;
    6. the answers (the note's OWN style — Copy's), each appended to the
       answer as read (``appended_answer``) and digested: nothing writable →
       ``nothing_to_write``; an answer the app cannot read, or one whose
       appended form does not read as the answer as read followed by the
       app's own lines (its text would not show, and the final and before
       digests might not tell a landed attempt apart) → ``note_unreadable``;
    7. the full body; unencodable → ``answer_unreadable``.

    Never raises for Cliniko's answers."""
    early = refuse_before_read(note, record, note_identity)
    if early is not None:
        return early
    assert not isinstance(record, RecordUnreadable)  # refuse_before_read refused it
    open_attempt = record is not None and record.open_attempt

    def refused(name: WriteRefusalName, **detail: Any) -> WriteRefusal:
        return WriteRefusal(name, earlier_attempt_open=open_attempt, **detail)

    subject = WritebackSubject(consent, context, live=True, reverification=hop1.result)
    target = writeback_context(subject, clinics)
    if isinstance(target, WritebackRefused):
        return refused("writeback_refused", writeback=target)
    match = match_template(profile, hop1.content)
    if isinstance(match, TemplateMismatch):
        return refused("template_mismatch", question=match.question, section=match.section)
    if record is not None:
        confirmed = confirm_written(record, hop1.content, match, note_identity)
        if isinstance(confirmed, Uncertain):
            return refused("write_uncertain")
        if isinstance(confirmed, ReconciledWritten):
            return AlreadyWritten(target)
        if record.outcome == "refused" and record.refusal == "finalised_before_write":
            return refused("write_forbidden")
        if isinstance(retry_verdict(record, hop1.content, match), Uncertain):
            return refused("write_uncertain")
    assert profile is not None  # match_template refused a missing profile
    # Each target's answer and its normalised visible text (``own`` below).
    new_answers: dict[str, tuple[str, str]] = {}
    for target_id, (rendered, lines) in render_targets(note, profile, note.style).items():
        matched = match.questions.get(target_id)
        if matched is None:
            # Unreachable: ``render_targets`` yields only mapped writable
            # targets, and ``match_template`` matched every one or refused.
            # Never a silent drop of a section's text (round 26 LOW-002).
            raise ValueError("a rendered target the template match does not hold")
        # NFC here, the app's part only: an answer already in the note is
        # kept byte-for-byte (``build_body`` normalises nothing — D15).
        answer = unicodedata.normalize("NFC", to_cliniko_answer(lines, rendered.target_type))
        try:
            visible = normalise_answer(answer, matched.representation)
        except AnswerUnparseable:
            return refused("answer_unreadable")
        if visible:
            new_answers[target_id] = (answer, visible)
    if not new_answers:
        return refused("nothing_to_write")
    sections = _note_sections(hop1.content)
    assert sections is not None  # match_template refused malformed content
    answers: dict[str, str] = {}
    digests: dict[str, str] = {}
    before_digests: dict[str, str] = {}
    for target_id, (new, own) in new_answers.items():
        matched = match.questions[target_id]
        existing = _answer_at(sections, matched.note_position)
        final = appended_answer(existing, new, matched.representation)
        if isinstance(final, NoteUnreadable):
            return refused("note_unreadable")
        # ``appended_answer`` admitted only a string or null (read once
        # already), so the answer as read normalises here as it did there.
        as_read = existing if isinstance(existing, str) else ""
        try:
            before = normalise_answer(as_read, matched.representation)
            expected = normalise_answer(final, matched.representation)
        except AnswerUnparseable:
            return refused("note_unreadable")
        if expected != "\n".join(part for part in (before, own) if part):
            # The final answer must read as the answer as read, then the
            # app's own lines: reconcile tells a landed attempt from one that
            # did not land by these two digests (D15), so they must differ,
            # and the app's text must show as written. Markup in the answer
            # as read that hides what follows it (an unterminated comment)
            # or takes it in as its own text (an unterminated ``<script>``,
            # an unclosed attribute quote) breaks that: the app never
            # appends there (round 40 LOW-001, H1 round 45 LOW-001).
            return refused("note_unreadable")
        answers[target_id] = final
        digests[target_id] = answer_digest(expected)
        before_digests[target_id] = answer_digest(before)
    body = build_body(hop1.content, match, answers)
    if isinstance(body, AnswerUnreadable):
        return refused("answer_unreadable")
    where = match_digest(match, tuple(answers))
    assert where is not None  # every answered target is in the match (above)
    return PreparedWrite(
        target=target,
        content=body,
        attempt=record.attempt + 1 if record is not None else 1,
        target_ids=tuple(answers),
        digests=digests,
        before_digests=before_digests,
        match_sha256=where,
        body_sha256=hashlib.sha256(body.to_body()).hexdigest(),
        note_identity=note_identity,
    )


# ---------------------------------------------------------------------------
# Hop 2: the PATCH (Task 3.4, D3 / D5).
# ---------------------------------------------------------------------------

OutcomeKind = Literal["written", "refused", "unknown"]


@dataclass(frozen=True)
class WriteOutcome:
    """Hop 2's answer, by the HTTP answer only (D5): ``written`` for a 200
    (never relabelled); ``refused`` when Cliniko applied nothing — or no
    request was sent — with ``refusal`` naming why (``categories`` for a
    422: the client's fixed D11 set); ``unknown`` for everything else.
    ``rate_limited``: the answer was a 429 (the caller records it in the
    latch)."""

    kind: OutcomeKind
    refusal: SendRefusal | None = None
    categories: tuple[str, ...] = ()
    rate_limited: bool = False


def send_write(call: ClinikoCall, prepared: PreparedWrite) -> WriteOutcome:
    """The PATCH of ``prepared``'s body to ``prepared``'s OWN target — the
    note the body was built from — classified (D5). The client is
    unchanged: it raises ``CredentialsRejected`` for 401 and 403 alike, and
    this is where the two part — a 403 just after hop 1 verified the note with the same key
    is ``finalised_before_write``, a 401 ``key_rejected``. 404
    ``note_not_found``; ``ClinikoRejected`` ``cliniko_rejected``; a 429
    ``unknown`` and rate-limited; every other failure ``unknown`` (the
    client's own classification of "not applied")."""
    try:
        call.write_draft_note(prepared.target.treatment_note_id, prepared.content)
    except CredentialsRejected as error:
        refusal: SendRefusal = (
            "finalised_before_write" if error.status == 403 else "key_rejected"
        )
        return WriteOutcome("refused", refusal)
    except NotFound:
        return WriteOutcome("refused", "note_not_found")
    except ClinikoRejected as error:
        return WriteOutcome("refused", "cliniko_rejected", categories=error.categories)
    except RateLimited:
        return WriteOutcome("unknown", rate_limited=True)
    except ClinikoError:
        return WriteOutcome("unknown")
    return WriteOutcome("written")


def write_for_click(
    request: VerificationRequest,
    prepared: PreparedWrite,
    *,
    key_store: KeyStore,
    transport: Transport | None = None,
) -> WriteOutcome:
    """Worker thread: HOP 2 in its OWN client call (D3 — hop 1's call closed
    on exit), reading the same stored key again (D9 refuses Replace key and
    Remove for the writing clinic meanwhile). A key that cannot be read, or
    is refused before any request, is ``refused`` (nothing was sent); any
    unforeseen failure is ``unknown`` (the request may have left).

    ``ValueError`` — raised before the key is read, so nothing is sent —
    when ``request`` (whose clinic's key is read) and ``prepared`` (whose
    note is written) name different clinics or notes: a caller bug that
    would otherwise PATCH one clinic's note under another clinic's key.
    Nothing else raises."""
    target = prepared.target
    if (
        request.clinic.clinic_id != target.clinic_id
        or request.target.clinic_host != target.clinic_host
        or request.target.note_id != target.treatment_note_id
    ):
        raise ValueError("the write request and the prepared write name different notes")
    try:
        client = ClinikoClient(contact_email=request.contact_email, transport=transport)
        with client.call(_key_reader(key_store, request.clinic.clinic_id)) as call:
            return send_write(call, prepared)
    except _KeyUnavailable:
        return WriteOutcome("refused", "key_unavailable")
    except (CredentialsRejected, InvalidKey):
        # Raised by ``call()`` itself, before any request (a missing or
        # malformed key).
        return WriteOutcome("refused", "key_rejected")
    except Exception:  # noqa: BLE001 - the unforeseen: never claim "not applied"
        return WriteOutcome("unknown")
