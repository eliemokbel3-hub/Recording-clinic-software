"""The Qt-free Cliniko draft write (cliniko-draft-write plan D3–D7).

This module grows task by task. Today it holds the RENDERING half (Task 3.1,
D7): which lines of a saved note go into which question of the clinic's
treatment-note template, and how those lines become a Cliniko answer. Every
line comes from ``note.render_section_lines`` — the same per-section renderer
behind Copy's ``render_note`` — with the review apparatus off, so the chart
never receives a bullet, a provenance tag, the pre-filled mark or an
"[includes …]" line, and Copy and the write share one source for every line.

What the structure enforces here: an attestation target is never yielded (the
profile already refuses a mapping to one; ``render_targets`` filters again and
``to_cliniko_answer`` refuses the type), and a rich-text answer contains no
tag but ``<p>`` / ``<br>`` — the text's markup-significant characters
(``& < > " '``) are HTML-escaped.
What it does not decide: whether the template still matches the profile, what
the note already holds, or whether anything is sent — those are the write's
later stages. Nothing here logs or touches the network.
"""

from __future__ import annotations

import html
from collections.abc import Sequence

from scribe_desktop.note import (
    SECTION_TITLES,
    GeneratedNote,
    NoteStyle,
    render_section_lines,
)
from scribe_desktop.note_config import TargetType, TemplateProfile, TemplateTarget

# A rich-text answer's only markup: one paragraph per line; an empty line is
# kept as an empty paragraph so a blank line between prose paragraphs
# survives Cliniko's editor.
_EMPTY_PARAGRAPH = "<p><br></p>"


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
