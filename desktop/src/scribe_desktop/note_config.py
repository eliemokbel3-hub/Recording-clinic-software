"""Note config engine (Phase 3A, Tasks 3.1-3.3).

This module owns the CONFIG side of the note pipeline: the template-mapping
model (canonical section -> real Cliniko template field), the autofill-rule
and prefill-template schemas, and the validating loader that resolves shipped
defaults against clinician overrides into one validated, attribute-frozen
``NoteConfig`` (pydantic ``frozen`` refuses reassignment; the cue mapping's
in-place residue is named and bounded on ``NoteConfig.section_cues``).

Config files are INTENDED to be clinician-authored boilerplate rather than
patient data (plan Schema / Data Changes): they live in plaintext under
``%LOCALAPPDATA%\\ClinikoScribe\\config\\``, deliberately outside the
encrypted session store and the 24 h rule, so they survive session
destruction.

Round 47 PR-LOW-002 narrows two claims this docstring used to make flatly,
matching the rounds 40-41 correction already applied to the security docs:

- "NOT patient data" is a POLICY, not an enforced property. Every validator
  below constrains SHAPE and character content — length, control characters,
  the single-claim form, duplicate detection — and none of them classifies
  meaning. A clinician override can put patient data in any accepted string,
  so nothing here may be treated as non-clinical BECAUSE it validated.
- "Nothing in this module touches a session key or a clinical artifact" was
  false in its second half: no session key, correct — but
  ``build_note_request`` below takes a ``TranscriptDocument`` and assembles
  the ``NoteRequest`` that carries the whole transcript across the provider
  boundary. The generation boundary lives here deliberately (the reverse
  import would be a cycle); it is a clinical path and is treated as one.

Resolution precedence (Task 3.2 — the specification ``config_digest``
depends on):

- **Per-file, whole-file replacement.** For each of the four config
  filenames, a user file under the config root REPLACES the shipped default
  of the same name entirely. There is no deep merge: merge semantics are
  where "never partially applies" goes to die, and a clinician editing a
  file owns that whole file.
- **First run:** no config root, or no user file for a name, means the
  shipped default for that name loads. The loader is read-only — it never
  creates the config directory (that is an app/UI concern).
- **Upgrade:** when shipped defaults change under an existing override, the
  override keeps winning for its file; files the clinician never overrode
  pick up the new defaults. ``config_digest`` changes accordingly, which is
  exactly what the digest exists to record.
- **Failure is loud and total.** A user file that exists but is unreadable
  or malformed raises a typed error (mirroring ``read_transcript``'s error
  shape) — it is NEVER silently skipped in favour of the shipped default,
  because that would be a silent partial apply of config the clinician did
  not choose. ``load_note_config`` either returns one fully-validated
  ``NoteConfig`` or raises; it mutates no state either way, so a failed
  load leaves nothing half-applied.

The fourth file (practitioner-profile plan Phase 4): ``section_cues.json``
holds the phrases that route a transcript utterance into a canonical section
— ``ExtractiveNoteProvider``'s cues — as one list per canonical key. It
follows the same precedence (whole-file replacement, first-run default, loud
failure — D6), the same text rule (``_TriggerText``), refuses a phrase with
no content tokens and any normalised duplicate within or across sections,
and enters ``config_digest`` like the other three (D7), so every note is
bound to the cue set that routed it. A key MISSING from the file has no cues
— nothing is routed to that section from cues — and the shipped default
carries every key. Cue phrases never enter a note: they select which
VERBATIM transcript utterance lands in which section.
``NoteConfig.normalised_cues()`` is the provider-shaped accessor, and the
app builds its provider from it (``ui.models.build_note_generator``).

Consented phrase learning (practitioner-profile plan Phase 5) makes the cue
file the ONE config file the app writes itself: ``append_user_cues`` appends
learned phrases (the Note tab's Save), ``delete_user_cue`` removes one (the
Practitioner tab), both validating the exact bytes by this loader's rules
before an atomic replace, with a sidecar ``section_cues.learned.json`` that
records each learned phrase's section and date and that the loader never
reads. ``refuse_learning_candidate`` is the enforcing content control; the
block below states what it refuses and, plainly, what it cannot.

``config_digest`` (Task 3.2, "well-defined"): ``note.digest_bytes`` — the
same ``"sha256-v1:<hex>"`` primitive as ``transcript_digest`` — over the
RESOLVED config's canonical serialization (``model_dump_json()`` bytes of
``NoteConfig``, after precedence). It therefore identifies exactly the
config content that drove a generation run, whichever mix of defaults and
overrides produced it, and slots unchanged into the ``_DIGEST_RE`` checks
on ``NoteAssertion`` / ``NoteProposal`` / ``NoteRequest``.

UNC posture: ``default_config_root`` follows ``default_sessions_root``'s
root-resolution idiom AND its deliberate NO-UNC-refusal decision
(``session_store.py``): a folder-redirected LOCALAPPDATA would place config
on SMB, and refusing would block note generation entirely for a same-user
deployment residual that is already accepted for the far more sensitive
session store.

Safety properties, structural as ever:

- **Never map a canonical section to an attestation-typed target** (plan
  Critical Constraints). The rule keys on TARGET TYPE, not on the section:
  ``TemplateProfile`` refuses AT CONSTRUCTION any mapping whose target is
  ``attestation_checkbox``, so no config file — shipped or user-authored —
  can route note text at a consent checkbox. ``consent`` itself stays
  legitimately mappable to a free-text target in some other template.
- **UNMAPPED is distinct from INTENTIONALLY UNMAPPED.** A populated
  canonical section whose profile silently loses it draws the
  ``mapping_drop`` review warning (``mapping_drop_warnings``); a section
  listed in ``intentionally_unmapped`` is silent. Without the distinction
  ``consent`` would warn on every note where consent was discussed — which
  is most of them — and warning fatigue is this phase's top risk.
- **A session cannot generate a note without a bound profile.**
  ``bind_template_profile`` is the single resolution point: the sole
  configured profile binds automatically (today's reality — both clinics
  share one captured template), an explicit id binds by id, and zero or
  ambiguous profiles raise. A chooser UI appears only when more than one
  profile exists; it must never ask the clinician to choose from a list of
  one.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import Annotated, Final, Literal, NamedTuple, Self, final

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticSerializationError

from scribe_desktop.note import (
    # Package-private by name, shared deliberately (the note.py convention):
    # one id grammar, one digest primitive, and one raw request assembler
    # across the note pipeline. ``_assemble_note_request`` is consumed ONLY
    # by ``build_note_request`` below — the generation-facing boundary lives
    # here because the reverse import would be a cycle.
    _DEFAULTS_RESOURCE_DIR,
    _ID_PATTERN,
    _PROFILE_ID_PATTERN,
    CANONICAL_SECTION_KEYS,
    DEFAULT_SECTION_CUES,
    SECTION_CUES_FILENAME,
    GeneratedSection,
    NoteRequest,
    NoteSectionKey,
    NoteWarning,
    _assemble_note_request,
    content_tokens,
    digest_bytes,
    normalise_token,
)
from scribe_desktop.session_store import StoreWriteError, atomic_write_bytes
from scribe_desktop.transcription import (
    TranscriptDocument,
    is_name_like_token,
    is_number_token,
)

CONFIG_DIRNAME: Final = "config"
TEMPLATE_PROFILES_FILENAME: Final = "template_profiles.json"
AUTOFILL_RULES_FILENAME: Final = "autofill_rules.json"
PREFILL_TEMPLATES_FILENAME: Final = "prefill_templates.json"
CONFIG_FILENAMES: Final[tuple[str, ...]] = (
    TEMPLATE_PROFILES_FILENAME,
    AUTOFILL_RULES_FILENAME,
    PREFILL_TEMPLATES_FILENAME,
    # The fourth file (practitioner-profile plan Phase 4); its name lives in
    # ``note`` because that module derives its default cues from the file.
    SECTION_CUES_FILENAME,
)

# Shipped defaults travel INSIDE the package (Task 3.3): package data under
# ``scribe_desktop/config_defaults/`` (``note._DEFAULTS_RESOURCE_DIR``, the
# one spelling), read through ``importlib.resources`` so a non-editable
# (wheel) install resolves them identically to the dev checkout. Never
# resolved via ``__file__`` and never via LOCALAPPDATA.

# Field bounds — artifact sanity bounds on clinician-authored config text,
# far above real use but low enough that a pasted document fails loudly.
MAX_CONFIG_LABEL_CHARS: Final = 120
MAX_TRIGGER_CHARS: Final = 200
MAX_CONFIG_ASSERTION_CHARS: Final = 2_000


# Round 10 PR-MED-002: beyond C0/DEL/C1, reject Unicode line/paragraph
# separators (Zl/Zp) and invisible format controls (Cf — bidi overrides and
# isolates, zero-width characters). Config text is shown for confirmation as
# the EXACT wording that may enter a note; a character that can reorder or
# conceal rendered wording (e.g. pasted from Word/web) must not survive
# validation. Ordinary printable non-ASCII clinical text is untouched.
_REJECTED_TEXT_CATEGORIES: Final[frozenset[str]] = frozenset({"Zl", "Zp", "Cf"})


def _no_control_chars(text: str) -> str:
    """THE control-character validator (Task 3.2 names exactly one).

    Config text is single-line plain text: C0 controls (including newlines
    and tabs), DEL and C1 controls, Unicode line/paragraph separators and
    invisible format controls (``_REJECTED_TEXT_CATEGORIES``) are rejected,
    and so is text that is blank once stripped — ``min_length`` alone would
    admit ``" "``.
    """
    if not text.strip():
        raise ValueError("config text must not be blank")
    for ch in text:
        code = ord(ch)
        if code < 0x20 or 0x7F <= code <= 0x9F:
            raise ValueError(f"control character U+{code:04X} is not allowed in config text")
        if unicodedata.category(ch) in _REJECTED_TEXT_CATEGORIES:
            raise ValueError(
                f"layout/format control U+{code:04X} is not allowed in config text"
            )
    return text


_LabelText = Annotated[
    str,
    StringConstraints(min_length=1, max_length=MAX_CONFIG_LABEL_CHARS),
    AfterValidator(_no_control_chars),
]
_TriggerText = Annotated[
    str,
    StringConstraints(min_length=1, max_length=MAX_TRIGGER_CHARS),
    AfterValidator(_no_control_chars),
]
_AssertionText = Annotated[
    str,
    StringConstraints(min_length=1, max_length=MAX_CONFIG_ASSERTION_CHARS),
    AfterValidator(_no_control_chars),
]


class NoteConfigError(Exception):
    """Base class for note-config failures (mirrors ``SessionStoreError``)."""


class NoteConfigUnreadableError(NoteConfigError):
    """A config file exists but cannot be read (I/O failure, not content)."""


class NoteConfigInvalidError(NoteConfigError):
    """A config file or the resolved config violates the schema. Nothing was
    applied: the loader returns a complete ``NoteConfig`` or nothing."""


class NoteConfigWriteError(NoteConfigError):
    """A learned-phrase write (practitioner-profile plan Phase 5) failed. Each
    file is replaced atomically, so the file the message names holds either
    its previous content or its new content, never a partial one."""


class TemplateProfileUnboundError(NoteConfigError):
    """No template profile could be bound — a session cannot generate a note
    without one (Task 3.1 Done-when)."""


# ---------------------------------------------------------------------------
# Template mapping (Task 3.1).
#
# The mapping model expresses more than {canonical_key: target_field} (Task
# 1.0's capture): a target carries its GROUP in the real template, a CONTENT
# TYPE — rich text (HTML) vs plain text, because formatting must never be
# emitted into a plain field — and one explicitly non-text type,
# ``attestation_checkbox``, which is structurally unmappable and exists so
# the model can SAY the checkbox is there while making it unwritable.
# ---------------------------------------------------------------------------

TargetType = Literal["rich_text", "plain_text", "attestation_checkbox"]


class TemplateTarget(BaseModel):
    """One field of a real Cliniko treatment-note template."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_id: str = Field(pattern=_ID_PATTERN)
    group: _LabelText
    field_label: _LabelText
    target_type: TargetType


class SectionMapping(BaseModel):
    """One canonical section routed to one template target."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    section_key: NoteSectionKey
    target_id: str = Field(pattern=_ID_PATTERN)


class TemplateProfile(BaseModel):
    """One clinic template's canonical->target mapping.

    Collapsing several canonical sections into one target is legal and is
    Template A's normal shape (four history sections share one rich-text
    field). Mapping one canonical section twice is not. Mapping ANY section
    to an attestation-typed target is refused at construction — the app
    never writes, ticks, or proposes a consent attestation (Critical
    Constraint), and that rule keys on the TARGET TYPE so it holds for any
    future template, not just Template A's checkbox.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    template_profile_id: str = Field(pattern=_PROFILE_ID_PATTERN)
    display_name: _LabelText
    template_targets: tuple[TemplateTarget, ...] = Field(min_length=1)
    section_mappings: tuple[SectionMapping, ...] = ()
    # UNMAPPED-by-oversight draws `mapping_drop`; INTENTIONALLY unmapped is
    # silent. The shipped profile lists `consent` here: Template A's only
    # consent target is the attestation checkbox, which is never written.
    intentionally_unmapped: tuple[NoteSectionKey, ...] = ()

    @model_validator(mode="after")
    def _check_profile(self) -> Self:
        targets: dict[str, TemplateTarget] = {}
        for target in self.template_targets:
            if target.target_id in targets:
                raise ValueError(f"duplicate target_id: {target.target_id}")
            targets[target.target_id] = target
        mapped: set[NoteSectionKey] = set()
        for mapping in self.section_mappings:
            if mapping.section_key in mapped:
                raise ValueError(f"section {mapping.section_key} is mapped more than once")
            mapped.add(mapping.section_key)
            target_for_key = targets.get(mapping.target_id)
            if target_for_key is None:
                raise ValueError(
                    f"mapping for {mapping.section_key} references "
                    f"unknown target {mapping.target_id}"
                )
            if target_for_key.target_type == "attestation_checkbox":
                raise ValueError(
                    f"section {mapping.section_key} maps to attestation-typed target "
                    f"{mapping.target_id}: an attestation is never written by this app"
                )
        silent: set[NoteSectionKey] = set()
        for key in self.intentionally_unmapped:
            if key in silent:
                raise ValueError(f"duplicate intentionally_unmapped section: {key}")
            silent.add(key)
            if key in mapped:
                raise ValueError(f"section {key} is both mapped and intentionally unmapped")
        return self

    def target_for(self, section_key: NoteSectionKey) -> TemplateTarget | None:
        """The mapped target for a canonical section, or None (unmapped —
        deliberately or not; ``mapping_drop_warnings`` tells them apart)."""
        for mapping in self.section_mappings:
            if mapping.section_key == section_key:
                for target in self.template_targets:
                    if target.target_id == mapping.target_id:
                        return target
        return None

    def unmapped_section_keys(self) -> tuple[NoteSectionKey, ...]:
        """Canonical sections that are neither mapped nor intentionally
        unmapped, in canonical order — the ``mapping_drop`` candidates."""
        mapped = {mapping.section_key for mapping in self.section_mappings}
        silent = set(self.intentionally_unmapped)
        return tuple(
            key for key in CANONICAL_SECTION_KEYS if key not in mapped and key not in silent
        )


# ---------------------------------------------------------------------------
# Autofill rules and prefill templates (schemas only — the matching engine is
# Phase 4's `note_fill.py`).
#
# Expansions and seeds are authored as explicit LISTS of atomic assertions
# (Task 4.0's principle, honoured from the first schema version): runtime
# decomposition of clinical prose would itself be an unverified inference.
# The tuple type refuses a bare string outright; the ``mode="before"``
# validators below (Task 4.0) turn that refusal into a message that NAMES
# THE FIX, because the person reading it is a clinician editing JSON, not a
# developer reading a pydantic type error.
# ---------------------------------------------------------------------------


def _refuse_prose_blob(value: object, field_name: str, example: str) -> object:
    """Task 4.0's fix-naming refusal of a single-string authoring mistake.

    This catches the OUTER-shape mistake only — a whole field authored as one
    string instead of a list. Entry-LEVEL atomicity (one entry carrying two
    claims, or one claim authored twice) is enforced separately by the
    rounds-15/16 guards: the ``_is_atomic_shape`` allow-list plus the
    duplicate checks in ``AutofillRule`` / ``PrefillSeedAssertion`` /
    ``PrefillTemplate``.
    Runtime decomposition of clinical prose is forbidden either way, so the
    only correct response is to send the author back to the file with
    instructions. Everything that is not a bare string falls through to the
    normal tuple validation.
    """
    if isinstance(value, str | bytes):
        raise ValueError(
            f"{field_name} is a single string; it must be a JSON list of atomic "
            f"assertions, one entry per claim — for example {example}. This app "
            "never splits prose into claims at runtime (splitting would itself "
            "be an unverified inference), so each claim must be authored as its "
            "own list entry."
        )
    return value


# Rounds 15-16 (PR-HIGH-001, PR-MED-001): list shape is not proof of
# atomicity — and two review rounds proved a DENY-list of separator forms is
# not either: each round found a separator the previous list missed (". " in
# round 15; ";" without a space in round 16; ".Capital" in round 16's
# verification). This is the semantic-surface lesson (docs/lessons.md,
# 2026-08-10: confine the whole surface with an allow-list minus explicit
# exceptions; never enumerate specific forms) applied to authoring: an entry
# is accepted as ONE claim only if EVERY character matches the conservative
# single-claim shape below, so any separator this code has never heard of —
# a colon, a dash, an interpunct, a fullwidth stop, anything — fails CLOSED
# into the fix-naming message and the explicit per-entry ``single_claim``
# override. The shape is purely LEXICAL and positional: no sentence-meaning
# inference and no word-list of known abbreviations (a shape rule may permit
# an internal '.' in specific mechanical positions; it may never name words).
#
# The shape, exactly (what a human author may rely on):
# - letters (any script), decimal digits, plain spaces;
# - in-claim punctuation  , ( ) / % ' " + & ° = < > ~  and curly quotes;
# - ASCII hyphen with a letter/digit on BOTH sides (mid-back, X-ray, 90-110);
#   any other dash only BETWEEN digits (10–15) — a spaced or word-joining
#   dash is a clause joiner and refuses;
# - '.' between digits (1.5), or inside a letter-dot abbreviation chain of
#   at least two single-letter pairs (q.i.d., e.g.) — and the chain must END
#   the entry (its final dot is the trailing terminator). ANY text after the
#   chain-final dot — lowercase, digit, or Capital — refuses (round 17: the
#   continuation-vs-new-claim distinction is semantic, so "q.i.d. as
#   directed" needs the override and "Dr. Smith" refuses, both by design);
# - ':' between digits (14:30);
# - a trailing run of  . ! ? ; : …  (and their fullwidth forms) ends the
#   entry and joins nothing.
#
# Residue, COMPLETE-BY-CONSTRUCTION rather than enumerated. A hand-written
# residue list has now been falsified FOUR times (rounds 15-18: each prose
# enumeration omitted a reachable class), which is the semantic-surface
# lesson (docs/lessons.md, 2026-08-10) applied to the DOCUMENTATION itself:
# the residue is defined by REFERENCE to the shape's own permissive
# branches, so it cannot be under-stated by omission again. The residue is:
#
#   two independently-confirmable claims joined ONLY by material the shape
#   accepts — that is, joined through ANY permissive branch above with no
#   caught separator present: EVERY member of ``_ALLOWED_IN_CLAIM_PUNCT``
#   at any position (slash, plus, ampersand, parentheses, quotes, comma,
#   operators, ... — the SET is the source of truth, not this sentence),
#   plain words/conjunctions and spaces, hyphen-between-alphanumerics, and
#   digit-boundary adjacency — plus an author mis-marking a genuine
#   compound ``single_claim``.
#
# Every one of those characters and positions is accepted BY DESIGN:
# legitimate clinical wording needs them (mmol/L, 3/10, drug + drug, A&E,
# (2x), 50%, <3/10, 90°, ~10 reps, quoted patient speech), and telling a
# join apart from that wording would require the semantic parsing this
# project forbids. The compensating controls for the WHOLE residue are
# Phase 7's per-assertion confirmation UI (the clinician sees and confirms
# the exact wording) and Phase 5's checking stage — which must not be
# assumed to semantically decompose entries either; it checks, it does not
# split. ``test_note_config`` pins BOTH sides mechanically: every member of
# ``_ALLOWED_IN_CLAIM_PUNCT`` is accepted mid-claim (so narrowing the set
# without revisiting this text fails a test), and this comment's
# by-reference form is itself asserted. The emitters never split, join, or
# deduplicate either way.
_ALLOWED_IN_CLAIM_PUNCT: Final[frozenset[str]] = frozenset(",()/'\"%&+°=<>~‘’“”")
_TERMINAL_PUNCT: Final[frozenset[str]] = frozenset(".!?;:…。！？；：")


def _abbreviation_chain_dot(entry: str, index: int) -> bool:
    """True when the ``'.'`` at ``index`` is an INTERIOR dot of a letter-dot
    abbreviation chain (>= 2 single-letter pairs: q.i.d., e.g.).

    Single-letter pairs only — a multi-letter word before the dot ("Dr.",
    "advised.") always reads as a sentence end. Interior means the dot binds
    a following single letter that is itself dotted; the chain's FINAL dot
    is not this function's to allow — it passes only through
    ``_is_atomic_shape``'s trailing-terminator branch, i.e. the chain must
    END the entry. Round 17 (fix-induced) removed the continuation
    allowance that used to sit here: whether text after "q.i.d. " is the
    same claim running on or a second terse claim is a SEMANTIC question,
    so any continuation — lowercase, digit, or Capital — now fails closed
    into the explicit per-entry override.
    """
    if index == 0 or not entry[index - 1].isalpha():
        return False
    if index >= 2 and entry[index - 2].isalnum():
        return False
    after = entry[index + 1 : index + 2]
    return after.isalpha() and entry[index + 2 : index + 3] == "."


def _is_atomic_shape(text: str) -> bool:
    """True when every character of ``text`` matches the single-claim shape
    documented above. Anything else — known or unforeseen — is not atomic
    and fails closed at the caller."""
    entry = text.strip()
    last = len(entry) - 1
    for index, ch in enumerate(entry):
        if ch.isalpha() or ch.isdecimal() or ch == " " or ch in _ALLOWED_IN_CLAIM_PUNCT:
            continue
        if ch == "-":
            if 0 < index < last and entry[index - 1].isalnum() and entry[index + 1].isalnum():
                continue
            return False
        if ch in _TERMINAL_PUNCT:
            if all(c in _TERMINAL_PUNCT or c == " " for c in entry[index:]):
                continue  # trailing terminator run — ends the entry
            if (
                ch in {".", ":"}
                and 0 < index < last
                and entry[index - 1].isdecimal()
                and entry[index + 1].isdecimal()
            ):
                continue  # decimal / time / ratio
            if ch == "." and _abbreviation_chain_dot(entry, index):
                continue
            return False
        if unicodedata.category(ch) == "Pd":
            if 0 < index < last and entry[index - 1].isdecimal() and entry[index + 1].isdecimal():
                continue  # digit range with a typographic dash (10–15)
            return False
        return False  # any character outside the allowed surface
    return True


def _atomicity_message(owner: str, entry_label: str, override_hint: str) -> str:
    return (
        f"{owner}: {entry_label} does not match the conservative single-claim "
        "shape, so it may contain more than one claim (extra sentences, an "
        "internal ';' or ':', a dash between words, or unusual punctuation). "
        "Author one list entry per claim, in plain wording with a single "
        f"trailing terminator. If this really is ONE assertion, {override_hint} "
        "— the app never splits prose into claims at runtime, so the split (or "
        "the explicit override) must be authored."
    )


class SingleClaimEntry(BaseModel):
    """An expansion entry the author EXPLICITLY marks as one assertion
    despite not matching the atomic shape (rounds 15-16's authoring-time
    control). ``single_claim`` is ``Literal[True]`` with no default: the
    author must write ``"single_claim": true`` in the file — the override is
    a per-entry human statement, never ambient. It exempts the entry from
    the ``_is_atomic_shape`` check ONLY; text bounds and the duplicate check
    still apply."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    assertion_text: _AssertionText
    single_claim: Literal[True]


class AutofillRule(BaseModel):
    """One trigger phrase -> a list of atomic assertion texts, all landing in
    one canonical section. Phase 4's matcher is bound by the Critical
    Constraint: a matched trigger may only ever turn each expansion entry
    into a proposal, never an insertion.

    Entry atomicity (rounds 15-16): a bare-string entry is accepted only
    when it MATCHES the conservative single-claim shape
    (``_is_atomic_shape`` — an allow-list, so unforeseen separators fail
    closed; override via ``SingleClaimEntry``), and two entries that are
    the same assertion under the single shared normalisation are refused —
    a repeated entry would become two separately-confirmable proposals of
    one claim.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str = Field(pattern=_ID_PATTERN)
    section_key: NoteSectionKey
    trigger_phrase: _TriggerText
    expansion: tuple[_AssertionText | SingleClaimEntry, ...] = Field(min_length=1)

    @field_validator("expansion", mode="before")
    @classmethod
    def _expansion_is_authored_list(cls, value: object) -> object:
        return _refuse_prose_blob(
            value, "expansion", '["Advice given to rest.", "Ice pack use explained."]'
        )

    def expansion_texts(self) -> tuple[str, ...]:
        """Entry texts in authored order, override entries unwrapped — what
        the emitter maps one-to-one onto proposals."""
        return tuple(
            entry if isinstance(entry, str) else entry.assertion_text
            for entry in self.expansion
        )

    @model_validator(mode="after")
    def _check_trigger(self) -> Self:
        if not content_tokens(self.trigger_phrase):
            raise ValueError(
                f"rule {self.rule_id}: trigger_phrase has no content tokens and could never fire"
            )
        return self

    @model_validator(mode="after")
    def _check_expansion_atomicity(self) -> Self:
        seen: dict[tuple[str, ...], int] = {}
        for position, entry in enumerate(self.expansion, start=1):
            if isinstance(entry, str):
                if not _is_atomic_shape(entry):
                    raise ValueError(
                        _atomicity_message(
                            f"rule {self.rule_id}",
                            f"expansion entry {position}",
                            'replace the entry with {"assertion_text": "...", '
                            '"single_claim": true}',
                        )
                    )
                text = entry
            else:
                text = entry.assertion_text
            key = content_tokens(text)
            earlier = seen.get(key)
            if earlier is not None:
                raise ValueError(
                    f"rule {self.rule_id}: expansion entries {earlier} and {position} "
                    "are the same assertion once normalised — a repeated entry would "
                    "become two separately-confirmable proposals of one claim; remove "
                    "the duplicate"
                )
            seen[key] = position
        return self


class PrefillSeedAssertion(BaseModel):
    """One atomic assertion of a prefill seed, bound to its section.

    ``single_claim`` (rounds 15-16) is the seed-side per-entry override: it
    exempts a legitimately-shaped single assertion from the
    ``_is_atomic_shape`` allow-list only — a human statement in the file,
    defaulting off.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    section_key: NoteSectionKey
    seed_text: _AssertionText
    single_claim: bool = False

    @model_validator(mode="after")
    def _check_atomicity(self) -> Self:
        if not self.single_claim and not _is_atomic_shape(self.seed_text):
            raise ValueError(
                _atomicity_message(
                    f"seed for section {self.section_key}",
                    "seed_text",
                    'set "single_claim": true on this seed',
                )
            )
        return self


class PrefillTemplate(BaseModel):
    """A body-region seed: detection keywords plus atomic seed assertions.
    Phase 4's prefill owes one proposal per seed assertion — never an
    assertion directly."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    prefill_id: str = Field(pattern=_ID_PATTERN)
    display_name: _LabelText
    region_keywords: tuple[_TriggerText, ...] = Field(min_length=1)
    seed_assertions: tuple[PrefillSeedAssertion, ...] = Field(min_length=1)

    @field_validator("seed_assertions", mode="before")
    @classmethod
    def _seeds_are_an_authored_list(cls, value: object) -> object:
        return _refuse_prose_blob(
            value,
            "seed_assertions",
            '[{"section_key": "objective_examination", "seed_text": "Knee inspected."}]',
        )

    @model_validator(mode="after")
    def _check_keywords(self) -> Self:
        # The AutofillRule trigger rule, applied to detection keywords: a
        # keyword with no content tokens under the module's one shared
        # normalisation could never match a transcript and would silently
        # disable the region it was meant to detect.
        for keyword in self.region_keywords:
            if not content_tokens(keyword):
                raise ValueError(
                    f"prefill {self.prefill_id}: region keyword {keyword!r} has no "
                    "content tokens and could never fire"
                )
        return self

    @model_validator(mode="after")
    def _check_seed_duplicates(self) -> Self:
        # Round 15: the same assertion authored twice IN ONE SECTION would
        # become two separately-confirmable proposals of one claim. The key
        # is (section, normalised text) — the same wording in two DIFFERENT
        # sections is legitimately two distinct assertions.
        seen: dict[tuple[NoteSectionKey, tuple[str, ...]], int] = {}
        for position, seed in enumerate(self.seed_assertions, start=1):
            key = (seed.section_key, content_tokens(seed.seed_text))
            earlier = seen.get(key)
            if earlier is not None:
                raise ValueError(
                    f"prefill {self.prefill_id}: seed_assertions {earlier} and "
                    f"{position} carry the same assertion for section "
                    f"{seed.section_key} once normalised — remove the duplicate"
                )
            seen[key] = position
        return self


# ---------------------------------------------------------------------------
# The four config FILES (one pydantic model each) and the RESOLVED config.
# ---------------------------------------------------------------------------


def _check_section_cues(cues: Mapping[NoteSectionKey, tuple[str, ...]]) -> None:
    """THE cue-phrase validator (practitioner-profile plan Task 4.2), called
    by ``SectionCuesFile`` — so a malformed user file names ITS file — and
    again by ``NoteConfig``, so a config assembled without the file model is
    held to the same rule. A phrase with no content tokens could never route
    anything; two phrases that are the same under the module's one shared
    normalisation — within a section or across two — would make which
    section wins an accident of canonical order (routing takes the first
    match), so both are refused at authoring time.
    """
    seen: dict[tuple[str, ...], tuple[str, int]] = {}
    for key, phrases in cues.items():
        for position, phrase in enumerate(phrases, start=1):
            tokens = content_tokens(phrase)
            if not tokens:
                raise ValueError(
                    f"section_cues {key}: phrase {position} has no content tokens "
                    "and could never route an utterance"
                )
            earlier = seen.get(tokens)
            if earlier is not None:
                raise ValueError(
                    f"section_cues {key}: phrase {position} is the same phrase as "
                    f"{earlier[0]} phrase {earlier[1]} once normalised - remove the duplicate"
                )
            seen[tokens] = (key, position)


class SectionCuesFile(BaseModel):
    """On-disk shape of ``section_cues.json`` (practitioner-profile plan
    Phase 4): ``{"schema_version": 1, "section_cues": {<canonical key>:
    [phrase, ...]}}``.

    Keys are canonical section keys (an unknown key is refused by the
    ``Literal``), phrases are ``_TriggerText`` (the autofill trigger's own
    bound and control-character rule), and ``_check_section_cues`` refuses a
    phrase that could never fire and any normalised duplicate. A key that is
    absent simply has no cues — nothing is routed to that section from this
    file — and the shipped default carries every key. ``frozen`` here means
    no attribute reassignment; the mapping itself is a plain dict (the
    residue ``NoteConfig.section_cues`` names and bounds).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    section_cues: Mapping[NoteSectionKey, tuple[_TriggerText, ...]] = {}

    @model_validator(mode="after")
    def _check_cues(self) -> Self:
        _check_section_cues(self.section_cues)
        return self


class TemplateProfilesFile(BaseModel):
    """On-disk shape of ``template_profiles.json``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Literal, unlike the artifact models' plain ints: config is hand-edited,
    # so an unknown version must fail loudly rather than parse as version 1.
    schema_version: Literal[1] = 1
    template_profiles: tuple[TemplateProfile, ...] = ()


class AutofillRulesFile(BaseModel):
    """On-disk shape of ``autofill_rules.json``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    autofill_rules: tuple[AutofillRule, ...] = ()


class PrefillTemplatesFile(BaseModel):
    """On-disk shape of ``prefill_templates.json``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    prefill_templates: tuple[PrefillTemplate, ...] = ()


class NoteConfig(BaseModel):
    """The fully-resolved config — what ``config_digest`` is defined over."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    template_profiles: tuple[TemplateProfile, ...] = ()
    autofill_rules: tuple[AutofillRule, ...] = ()
    prefill_templates: tuple[PrefillTemplate, ...] = ()
    # The cue set that routes utterances (practitioner-profile plan Phase 4,
    # D7): part of ``to_bytes()`` and therefore of ``config_digest``. The
    # model default is EMPTY like the other three fields' — the first-run
    # default is the loader's, which reads the shipped file. Residue, named:
    # ``frozen=True`` refuses attribute REASSIGNMENT only; the mapping is a
    # plain dict, so an in-place mutation is not refused by construction as
    # it is for the three tuple fields. The bound, stated exactly (peer round
    # 32 PR-LOW-034): no shipped path mutates it — the loader,
    # ``normalised_cues``, ``_check_section_cues`` and the provider factory
    # only read it; ``_canonical_config`` re-validates whatever the field
    # holds NOW, and ``check_note`` rejects a config whose digest disagrees
    # with the one the draft RECORDED — so a change made after the draft's
    # digest was taken is rejected at check time, while one made before it
    # (between the factory's ``normalised_cues()`` snapshot and
    # ``compose_draft``) would not be detected; nothing in the shipped
    # worker sits in that window. Neither mechanism is general immutability.
    section_cues: Mapping[NoteSectionKey, tuple[_TriggerText, ...]] = {}

    @model_validator(mode="after")
    def _check_config(self) -> Self:
        _check_section_cues(self.section_cues)
        profile_ids: set[str] = set()
        for profile in self.template_profiles:
            if profile.template_profile_id in profile_ids:
                raise ValueError(f"duplicate template_profile_id: {profile.template_profile_id}")
            profile_ids.add(profile.template_profile_id)
        rule_ids: set[str] = set()
        # THE duplicate-trigger validator (Task 3.2 names exactly one): two
        # rules whose triggers are the same phrase under the module's one
        # shared normalisation would race for the same match, and which fired
        # would be an implementation accident.
        triggers: dict[tuple[str, ...], str] = {}
        for rule in self.autofill_rules:
            if rule.rule_id in rule_ids:
                raise ValueError(f"duplicate rule_id: {rule.rule_id}")
            rule_ids.add(rule.rule_id)
            trigger_tokens = content_tokens(rule.trigger_phrase)
            earlier = triggers.get(trigger_tokens)
            if earlier is not None:
                raise ValueError(
                    f"rules {earlier} and {rule.rule_id} share the same "
                    f"normalised trigger phrase"
                )
            triggers[trigger_tokens] = rule.rule_id
        prefill_ids: set[str] = set()
        for prefill in self.prefill_templates:
            if prefill.prefill_id in prefill_ids:
                raise ValueError(f"duplicate prefill_id: {prefill.prefill_id}")
            prefill_ids.add(prefill.prefill_id)
        return self

    def normalised_cues(self) -> Mapping[NoteSectionKey, tuple[tuple[str, ...], ...]]:
        """The cue set in ``ExtractiveNoteProvider``'s shape — every phrase
        normalised through ``content_tokens``, the derivation
        ``note.DEFAULT_SECTION_CUES`` applies to the shipped file. A section
        absent from the file is absent here, and the provider's
        ``self._cues.get(key, ())`` then routes nothing to it."""
        return {
            key: tuple(content_tokens(phrase) for phrase in phrases)
            for key, phrases in self.section_cues.items()
        }

    def to_bytes(self) -> bytes:
        """Canonical serialization — the byte domain of ``config_digest``."""
        return self.model_dump_json().encode("utf-8")

    def config_digest(self) -> str:
        """``"sha256-v1:<hex>"`` over the resolved config's canonical bytes —
        the value ``GeneratedNote`` / ``NoteRequest`` carry as
        ``config_digest``, defined here and nowhere else."""
        return digest_bytes(self.to_bytes())


# ---------------------------------------------------------------------------
# The loader (Task 3.2) — read-only, loud, all-or-nothing.
# ---------------------------------------------------------------------------


def default_config_root() -> Path:
    # Same root idiom AND same deliberate no-UNC-refusal posture as
    # default_sessions_root (module docstring records why).
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "ClinikoScribe" / CONFIG_DIRNAME


def _read_config_blob(config_root: Path, filename: str) -> tuple[bytes, str]:
    """One filename's bytes plus its source (``"user"`` / ``"default"``).

    A user file wins whole-file. Only its ABSENCE falls through to the
    shipped default: an existing-but-unreadable user file raises, because
    silently loading the default in its place would apply config the
    clinician did not choose. Try-read rather than exists()-then-read, so
    there is no window and no reliance on ``exists()`` suppressing errors.
    """
    user_path = config_root / filename
    try:
        return user_path.read_bytes(), "user"
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise NoteConfigUnreadableError(f"user config {filename} unreadable: {exc}") from exc
    try:
        resource = resources.files("scribe_desktop") / _DEFAULTS_RESOURCE_DIR / filename
        return resource.read_bytes(), "default"
    except OSError as exc:
        raise NoteConfigUnreadableError(
            f"shipped default config {filename} unreadable (broken install): {exc}"
        ) from exc


def _parse_config_blob[FileModelT: BaseModel](
    model: type[FileModelT], blob: bytes, filename: str, source: str
) -> FileModelT:
    try:
        return model.model_validate_json(blob)
    except ValidationError as exc:
        # Unlike read_transcript's terse message, the validation detail is
        # included: config is clinician-EDITED plaintext the author has to be
        # able to repair, and "fails loudly" must name what to fix.
        #
        # BOUNDED DESTINATION, not a safety class (round 47 PR-LOW-002): the
        # rendered pydantic detail reproduces the REJECTED INPUT, and config
        # is only intended-non-patient — structure is all that is validated
        # (module docstring). So this string is safe for the LOCAL UI surface
        # it is shown on; it is NOT log-safe, it carries no registered
        # tripwire signature, and no future call site may log it on the
        # strength of "config is not clinical content".
        raise NoteConfigInvalidError(f"{source} config {filename} is malformed: {exc}") from exc


def load_note_config(config_root: Path | None = None) -> NoteConfig:
    """Resolve shipped defaults + user overrides into one ``NoteConfig``.

    Precedence, first-run and upgrade behaviour are specified in the module
    docstring. Returns a complete validated config or raises a typed
    ``NoteConfigError``; it never partially applies (pure function — no
    state is written either way, and no directory is created).
    """
    root = config_root if config_root is not None else default_config_root()
    profiles_blob, profiles_source = _read_config_blob(root, TEMPLATE_PROFILES_FILENAME)
    rules_blob, rules_source = _read_config_blob(root, AUTOFILL_RULES_FILENAME)
    prefills_blob, prefills_source = _read_config_blob(root, PREFILL_TEMPLATES_FILENAME)
    cues_blob, cues_source = _read_config_blob(root, SECTION_CUES_FILENAME)
    profiles_file = _parse_config_blob(
        TemplateProfilesFile, profiles_blob, TEMPLATE_PROFILES_FILENAME, profiles_source
    )
    rules_file = _parse_config_blob(
        AutofillRulesFile, rules_blob, AUTOFILL_RULES_FILENAME, rules_source
    )
    prefills_file = _parse_config_blob(
        PrefillTemplatesFile, prefills_blob, PREFILL_TEMPLATES_FILENAME, prefills_source
    )
    cues_file = _parse_config_blob(SectionCuesFile, cues_blob, SECTION_CUES_FILENAME, cues_source)
    try:
        return NoteConfig(
            template_profiles=profiles_file.template_profiles,
            autofill_rules=rules_file.autofill_rules,
            prefill_templates=prefills_file.prefill_templates,
            section_cues=cues_file.section_cues,
        )
    except ValidationError as exc:
        raise NoteConfigInvalidError(f"resolved note config is invalid: {exc}") from exc


# ---------------------------------------------------------------------------
# Consented phrase learning (practitioner-profile plan Phase 5, D9 as
# amended 2026-09-16): the refusal filter — THE enforcing control — the
# phrase proposer, and the ONLY writer of the user cue file.
#
# What learning stores is a routing cue: the leading content tokens of a line
# the practitioner ADDED or MOVED during review, appended to the section they
# chose. The app cannot classify meaning, so the filter refuses a candidate
# whose SOURCE tokens — the original-case transcript words, checked BEFORE
# ``content_tokens`` lowercases them — are name-like, numeric, date-shaped or
# medication-shaped; everything else is the practitioner's to review after
# the fact on the Practitioner tab. The eligibility rule (the utterance is the
# confirmed clinician's — ``note.spoken_by_confirmed_clinician``) is applied
# by the Note tab BEFORE a candidate reaches this module; nothing here can
# tell whose line it was, so the tab's test is the structural gate and this
# filter the content gate. Residue, named: a benign-looking phrase that IS
# patient-identifying in context passes the filter; a drug name without a
# listed suffix and no unit within two tokens passes it too; a benign word
# that ends in a listed suffix is refused (two anatomical words are exempted
# by name — an exemption ADMITS, so a new form still fails toward refusal);
# and the name heuristic at an utterance's first word exempts only the
# transcript's listed common openers, so a line opening with any other
# capitalised word ("On examination…") is refused and never teaches — the
# safe direction, named because it narrows what learning can pick up.
# ---------------------------------------------------------------------------

LEARNED_SIDECAR_FILENAME: Final = "section_cues.learned.json"
LEARNED_PHRASE_MIN_TOKENS: Final = 2
LEARNED_PHRASE_MAX_TOKENS: Final = 4
RECENTLY_LEARNED_LIMIT: Final = 20
# The dose-unit rule looks this many raw words past the candidate's last word.
_UNIT_WINDOW: Final = 2

RefusalClass = Literal["name", "number", "date", "medication"]

_DATE_NUMERIC_RE: Final = re.compile(r"\d{1,2}[/.\-]\d{1,2}")
_YEAR_RE: Final = re.compile(r"\d{4}")
_MONTH_NAMES: Final[frozenset[str]] = frozenset(
    """
    january february march april may june july august september october
    november december jan feb mar apr jun jul aug sep sept oct nov dec
    """.split()
)
_MEDICATION_SUFFIXES: Final[tuple[str, ...]] = (
    "mab", "nib", "pril", "olol", "statin", "cillin", "mycin", "azole", "pine", "sartan",
)
# Anatomical words a physiotherapist says constantly that end in "-pine".
# An exemption ADMITS a named form only; every other suffix match refuses.
_MEDICATION_SUFFIX_EXEMPT: Final[frozenset[str]] = frozenset({"spine", "supine"})
_DOSE_UNITS: Final[frozenset[str]] = frozenset({"mg", "mcg", "ml"})


def _is_date_shaped(raw: str) -> bool:
    """``12/03``, ``12-03``, ``12.03``, a four-digit run (a year), or a month
    name / abbreviation (``May`` is a month here — fail toward refusal)."""
    if _DATE_NUMERIC_RE.search(raw) or _YEAR_RE.search(raw):
        return True
    return normalise_token(raw) in _MONTH_NAMES


def _is_medication_shaped(raw: str) -> bool:
    """A dose unit, or an alphabetic word ending in a listed drug suffix and
    longer than the suffix itself (bar the named anatomical exemptions)."""
    token = normalise_token(raw)
    if token in _DOSE_UNITS:
        return True
    if not token.isalpha() or token in _MEDICATION_SUFFIX_EXEMPT:
        return False
    return any(
        token.endswith(suffix) and len(token) > len(suffix) for suffix in _MEDICATION_SUFFIXES
    )


def refuse_learning_candidate(
    tokens: Sequence[str],
    *,
    first_in_segment: bool,
    following: Sequence[str] = (),
) -> RefusalClass | None:
    """THE refusal filter (practitioner-profile plan Task 5.2; round 1
    PR-HIGH-001 / round 2 PR-MED-016). ``tokens`` are the candidate's SOURCE
    words in original case and original order — checked before any
    normalisation, so a capitalised name is still capitalised here;
    ``first_in_segment`` says whether ``tokens[0]`` opens its utterance (the
    name heuristic exempts common sentence openers only in that position —
    any other capitalised opener is refused as name-like, so such a line never
    teaches; the safe direction, and a known narrowing);
    ``following`` holds the raw words that follow the candidate in its
    utterance, of which the first ``_UNIT_WINDOW`` are searched for a dose
    unit. Returns the refusal class, or None when every token passes:

    - ``name``: ``transcription.is_name_like_token`` on any token;
    - ``date``: a ``d/d``, ``d-d``, ``d.d`` pair, a four-digit run, or a
      month name;
    - ``number``: ``transcription.is_number_token`` (digits, number words,
      ordinals, hyphenated compounds);
    - ``medication``: a listed drug suffix, or a dose unit anywhere in the
      candidate or within ``_UNIT_WINDOW`` words after it.

    Checked in that order; the first class hit is reported.
    """
    for index, raw in enumerate(tokens):
        if is_name_like_token(raw, first_in_segment=first_in_segment and index == 0):
            return "name"
    for raw in tokens:
        if _is_date_shaped(raw):
            return "date"
    for raw in tokens:
        if is_number_token(raw):
            return "number"
    for raw in (*tokens, *following[:_UNIT_WINDOW]):
        if _is_medication_shaped(raw):
            return "medication"
    return None


class LearningCandidate(NamedTuple):
    """What ``propose_learning_phrase`` derives from one utterance: the
    phrase that would be stored (normalised), the raw words it came from
    (for the refusal filter), whether the first of those raw words is the
    utterance's REAL first word (peer round 36 PR-HIGH-008: the name
    heuristic's opener exemption belongs to segment position 0 only — a
    dropped leading filler must not move it onto the next word), and the raw
    words that follow the candidate (for the dose-unit window)."""

    phrase: str
    source_words: tuple[str, ...]
    first_in_segment: bool
    following: tuple[str, ...]


def propose_learning_phrase(word_texts: Sequence[str]) -> LearningCandidate | None:
    """The candidate phrase for an utterance: its leading content tokens —
    at most ``LEARNED_PHRASE_MAX_TOKENS``, and None when fewer than
    ``LEARNED_PHRASE_MIN_TOKENS`` exist (nothing to route by). Each word is
    admitted or dropped by ``content_tokens`` itself (punctuation-only and
    disfluency words are skipped exactly as the router skips them), so the
    stored phrase matches the way the router will read the next utterance.
    ``first_in_segment`` is True only when the first chosen word sits at
    index 0 of ``word_texts`` — the position the refusal filter's opener
    exemption is defined for."""
    chosen: list[tuple[int, str, str]] = []
    for index, raw in enumerate(word_texts):
        tokens = content_tokens(raw)
        if not tokens:
            continue
        chosen.append((index, raw, tokens[0]))
        if len(chosen) == LEARNED_PHRASE_MAX_TOKENS:
            break
    if len(chosen) < LEARNED_PHRASE_MIN_TOKENS:
        return None
    first_index = chosen[0][0]
    last_index = chosen[-1][0]
    return LearningCandidate(
        phrase=" ".join(token for _, _, token in chosen),
        source_words=tuple(raw for _, raw, _ in chosen),
        first_in_segment=first_index == 0,
        following=tuple(word_texts[last_index + 1 : last_index + 1 + _UNIT_WINDOW]),
    )


class LearnedEntry(BaseModel):
    """One sidecar record: where a learned phrase went and when. A naive
    ``learned_at`` (a hand-edited sidecar) is read as UTC so the newest-first
    ordering never compares naive with aware stamps."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    section: NoteSectionKey
    learned_at: datetime

    @field_validator("learned_at")
    @classmethod
    def _learned_at_aware(cls, value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class LearnedSidecarFile(BaseModel):
    """On-disk shape of ``section_cues.learned.json``: ``{"schema_version":
    1, "learned": {<stored phrase>: {"section": ..., "learned_at": ...}}}``.
    Written beside the user cue file by the learner and read ONLY by the
    Practitioner tab's "Recently learned" list — never by the loader, so it
    can never affect routing or the config digest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    learned: Mapping[str, LearnedEntry] = {}


class AppendedCues(NamedTuple):
    """``append_user_cues``'s report: what was written and what was skipped
    (``(section, phrase, reason)`` — ``duplicate`` or ``empty``).
    ``sidecar_error`` is set when the cue file WAS replaced but the sidecar
    write then failed (peer round 36 PR-MED-023): the phrases ARE learned
    and listed under "Learned phrases", with no date under "Recently
    learned" — reported, never raised, so the caller can say so."""

    added: tuple[tuple[NoteSectionKey, str], ...]
    skipped: tuple[tuple[NoteSectionKey, str, str], ...]
    sidecar_error: str | None = None


class LearnedPhrase(NamedTuple):
    phrase: str
    section_key: NoteSectionKey
    learned_at: datetime


class LearnedPhrases(NamedTuple):
    """What the Practitioner tab lists (Task 5.3): the most recent
    ``RECENTLY_LEARNED_LIMIT`` sidecar entries that still exist in the user
    cue file, newest first, and every phrase in the user cue file that the
    shipped default does not carry, grouped by section in canonical order."""

    recent: tuple[LearnedPhrase, ...]
    by_section: tuple[tuple[NoteSectionKey, tuple[str, ...]], ...]


def _current_cues_file(root: Path) -> tuple[SectionCuesFile, str]:
    blob, source = _read_config_blob(root, SECTION_CUES_FILENAME)
    return _parse_config_blob(SectionCuesFile, blob, SECTION_CUES_FILENAME, source), source


def _serialise_cues_file(cues: Mapping[NoteSectionKey, Sequence[str]]) -> bytes:
    payload = {
        "schema_version": 1,
        "section_cues": {key: list(cues[key]) for key in CANONICAL_SECTION_KEYS if key in cues},
    }
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _validate_cues_bytes(blob: bytes) -> None:
    """The loader's two validations over the EXACT bytes about to be written
    — the file model, then the resolved-config rule — so a failure leaves the
    file on disk untouched."""
    parsed = _parse_config_blob(SectionCuesFile, blob, SECTION_CUES_FILENAME, "learned")
    try:
        NoteConfig(section_cues=parsed.section_cues)
    except ValidationError as exc:
        raise NoteConfigInvalidError(
            f"learned {SECTION_CUES_FILENAME} would not resolve: {exc}"
        ) from exc


def _read_sidecar(root: Path) -> dict[str, LearnedEntry]:
    path = root / LEARNED_SIDECAR_FILENAME
    try:
        blob = path.read_bytes()
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise NoteConfigUnreadableError(
            f"user {LEARNED_SIDECAR_FILENAME} unreadable: {exc}"
        ) from exc
    parsed = _parse_config_blob(LearnedSidecarFile, blob, LEARNED_SIDECAR_FILENAME, "user")
    return dict(parsed.learned)


def _serialise_sidecar(entries: Mapping[str, LearnedEntry]) -> bytes:
    payload = {
        "schema_version": 1,
        "learned": {
            phrase: {"section": entry.section, "learned_at": entry.learned_at.isoformat()}
            for phrase, entry in sorted(entries.items())
        },
    }
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _write_config_file(root: Path, filename: str, blob: bytes) -> None:
    """The ONE write path into the config directory (the loader stays
    read-only): the directory is created if absent, the file replaced
    atomically (``session_store.atomic_write_bytes``: temp + fsync +
    ``os.replace``), and EVERY failure is typed with the filename — the
    writer's own ``StoreWriteError`` and any raw ``OSError`` that escapes it
    (peer round 37 PR-MED-025: the writer's temp-file cleanup runs in an
    unguarded ``finally``, so a write that fails AND a temp file that then
    cannot be unlinked surfaces the cleanup's raw error in place of the
    typed one; folded here, at this boundary, so a post-cue sidecar failure
    of any shape reaches the committed-cue outcome and a deletion failure
    reaches the tab's retryable branch). The file at ``path`` is never
    partial either way (the writer replaces or leaves it)."""
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise NoteConfigWriteError(f"failed creating the config directory: {exc}") from exc
    try:
        atomic_write_bytes(root / filename, blob, error_label=f"config {filename}")
    except StoreWriteError as exc:
        raise NoteConfigWriteError(str(exc)) from exc
    except OSError as exc:
        raise NoteConfigWriteError(f"failed writing config {filename}: {exc}") from exc


def append_user_cues(
    pairs: Sequence[tuple[NoteSectionKey, str]],
    *,
    config_root: Path | None = None,
    learned_at: datetime,
) -> AppendedCues:
    """Append learned phrases to the user ``section_cues.json`` (Task 5.2).

    The file is read through the loader's own precedence — the user file, or
    the shipped default when there is none, which then becomes the user file
    with the phrases appended (D6: whole-file replacement, so the practitioner
    keeps every shipped cue). Each phrase is stored NORMALISED (its content
    tokens joined by single spaces); a phrase with no content tokens, or one
    already present in ANY section under the loader's normalisation, is
    skipped and reported. The exact bytes to be written are validated by the
    loader's two rules BEFORE anything is written; a validation failure, an
    unreadable or malformed file, or a failed CUE write raises typed with
    nothing changed. The cue file is replaced atomically first, then the
    sidecar (``learned_at`` recorded per phrase) — two atomic writes, not
    one: a sidecar write that fails AFTER the cue file was replaced is
    RETURNED as ``sidecar_error`` rather than raised (peer round 36
    PR-MED-023), because the phrases are on disk — the tab lists them under
    "Learned phrases" (derived from the cue file) but not under "Recently
    learned". Nothing is written when no phrase is added."""
    root = config_root if config_root is not None else default_config_root()
    current, _source = _current_cues_file(root)
    cues: dict[NoteSectionKey, list[str]] = {
        key: list(phrases) for key, phrases in current.section_cues.items()
    }
    known: dict[tuple[str, ...], NoteSectionKey] = {
        content_tokens(phrase): key for key, phrases in cues.items() for phrase in phrases
    }
    added: list[tuple[NoteSectionKey, str]] = []
    skipped: list[tuple[NoteSectionKey, str, str]] = []
    for section, phrase in pairs:
        tokens = content_tokens(phrase)
        if not tokens:
            skipped.append((section, phrase, "empty"))
            continue
        if tokens in known:
            skipped.append((section, phrase, "duplicate"))
            continue
        stored = " ".join(tokens)
        cues.setdefault(section, []).append(stored)
        known[tokens] = section
        added.append((section, stored))
    if not added:
        return AppendedCues((), tuple(skipped))
    blob = _serialise_cues_file(cues)
    _validate_cues_bytes(blob)
    sidecar = _read_sidecar(root)
    for section, stored in added:
        sidecar[stored] = LearnedEntry(section=section, learned_at=learned_at)
    sidecar_blob = _serialise_sidecar(sidecar)
    _write_config_file(root, SECTION_CUES_FILENAME, blob)
    try:
        _write_config_file(root, LEARNED_SIDECAR_FILENAME, sidecar_blob)
    except NoteConfigWriteError as exc:
        return AppendedCues(tuple(added), tuple(skipped), sidecar_error=str(exc))
    return AppendedCues(tuple(added), tuple(skipped))


def load_learned_phrases(config_root: Path | None = None) -> LearnedPhrases:
    """What the Practitioner tab shows (Task 5.3). With no user cue file
    nothing has been learned (the shipped default is in force) and any
    sidecar is ignored. Otherwise "learned" is every user-file phrase whose
    normalised form the shipped default carries in no section, grouped by
    the section the cue file holds it in NOW; "recent" is the sidecar's
    entries that still name such a phrase — an entry whose phrase is no
    longer in the cue file is dropped on read — newest first, capped at
    ``RECENTLY_LEARNED_LIMIT``. A malformed or unreadable cue file or
    sidecar raises the loader's typed errors (loud, never a silent empty)."""
    root = config_root if config_root is not None else default_config_root()
    current, source = _current_cues_file(root)
    if source != "user":
        return LearnedPhrases((), ())
    shipped = {tokens for phrases in DEFAULT_SECTION_CUES.values() for tokens in phrases}
    learned: dict[tuple[str, ...], tuple[NoteSectionKey, str]] = {}
    by_section: list[tuple[NoteSectionKey, tuple[str, ...]]] = []
    for key in CANONICAL_SECTION_KEYS:
        phrases = tuple(
            phrase
            for phrase in current.section_cues.get(key, ())
            if content_tokens(phrase) not in shipped
        )
        for phrase in phrases:
            learned[content_tokens(phrase)] = (key, phrase)
        if phrases:
            by_section.append((key, phrases))
    recent: list[LearnedPhrase] = []
    for phrase, entry in _read_sidecar(root).items():
        hit = learned.get(content_tokens(phrase))
        if hit is None:
            continue
        recent.append(LearnedPhrase(hit[1], hit[0], entry.learned_at))
    recent.sort(key=lambda item: (item.learned_at, item.phrase), reverse=True)
    return LearnedPhrases(tuple(recent[:RECENTLY_LEARNED_LIMIT]), tuple(by_section))


def delete_user_cue(phrase: str, *, config_root: Path | None = None) -> bool:
    """Remove ``phrase`` (matched under the loader's normalisation, from
    whichever section holds it) from the user cue file AND from the sidecar
    (Task 5.3), each representation on its own account (peer round 36
    PR-MED-024): a matching sidecar entry is removed even when the cue is
    already absent — so a retry after a cue-removed / sidecar-failed attempt
    finishes the job — and every sidecar rewrite also prunes entries whose
    phrase is no longer in the cue file, so no orphan outlives the next
    delete. Returns True when the phrase was held by either representation
    (the request did something); False, with nothing written unless an
    orphan was pruned, when neither held it. The cue bytes are validated
    before either atomic write, the cue file first; a user cue file is never
    CREATED here; an emptied section keeps its key with an empty list, which
    the loader reads as "no cues"."""
    root = config_root if config_root is not None else default_config_root()
    tokens = content_tokens(phrase)
    current, source = _current_cues_file(root)
    cues: dict[NoteSectionKey, list[str]] = {}
    cue_changed = False
    if source == "user":
        for key, phrases in current.section_cues.items():
            kept = [candidate for candidate in phrases if content_tokens(candidate) != tokens]
            cue_changed = cue_changed or len(kept) != len(phrases)
            cues[key] = kept
    remaining = {content_tokens(kept) for phrases in cues.values() for kept in phrases}
    sidecar = _read_sidecar(root)
    matched_in_sidecar = any(content_tokens(stored) == tokens for stored in sidecar)
    sidecar_kept = {
        stored: entry
        for stored, entry in sidecar.items()
        if content_tokens(stored) != tokens and content_tokens(stored) in remaining
    }
    sidecar_changed = sidecar_kept.keys() != sidecar.keys()
    if cue_changed:
        blob = _serialise_cues_file(cues)
        _validate_cues_bytes(blob)
        _write_config_file(root, SECTION_CUES_FILENAME, blob)
    if sidecar_changed:
        _write_config_file(root, LEARNED_SIDECAR_FILENAME, _serialise_sidecar(sidecar_kept))
    return cue_changed or matched_in_sidecar


# ---------------------------------------------------------------------------
# Profile binding and the mapping_drop warning (Task 3.1).
# ---------------------------------------------------------------------------


@final
class BoundTemplateProfile(BaseModel):
    """A profile selection RESOLVED against its canonicalised source config
    — selection EVIDENCE for the UI, mapping, and persistence layers.

    RELATIONAL, the ``TemplateProfile._check_profile`` pattern: the model
    stores the source config plus the selected id, a validator requires
    membership, and the profile and digest are exposed only as properties
    derived from the stored config. HONEST BOUNDARY (round 12 PR-MED-001):
    those guarantees hold for VALIDATING construction. Pydantic's
    validator-skipping escape hatches (``model_construct``,
    ``model_copy(update=...)``) and runtime subclasses overriding the
    properties can still present lies, which is exactly why this value is
    NOT generation authority: ``build_note_request`` re-establishes
    membership and re-derives the digest itself from canonicalised field
    data and never trusts an incoming binding. ``@final`` makes
    shipping-source subclassing a mypy-strict error, and the AST guard
    (``TestConstructionGuard``) refuses a subclass definition in shipping
    source outright.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_config: NoteConfig
    template_profile_id: str = Field(pattern=_PROFILE_ID_PATTERN)

    @model_validator(mode="after")
    def _check_membership(self) -> Self:
        ids = [p.template_profile_id for p in self.source_config.template_profiles]
        if self.template_profile_id not in ids:
            raise ValueError(
                f"template_profile_id {self.template_profile_id} is not a member "
                "of the source config"
            )
        return self

    @property
    def template_profile(self) -> TemplateProfile:
        """The selected profile, derived from the source config."""
        for profile in self.source_config.template_profiles:
            if profile.template_profile_id == self.template_profile_id:
                return profile
        raise AssertionError("unreachable: membership is validated at construction")

    @property
    def config_digest(self) -> str:
        """The digest of the exact config the profile was resolved from —
        derived, never supplied, so it cannot disagree with the profile."""
        return self.source_config.config_digest()


def _canonical_config(config: NoteConfig) -> NoteConfig:
    """Round-trip ``config`` through ``NoteConfig``'s OWN schema serializer
    and full re-validation, yielding an exact ``NoteConfig`` rebuilt from
    field data alone (round 12 PR-MED-001).

    The trust boundary's answer to pydantic's escape hatches: the BASE
    class serializer reads validated field data — never an overridden
    method, property, or subclass serializer — and re-validation re-runs
    every validator, so neither a lying subclass nor a validator-skipping
    construction (``model_construct``, ``model_copy(update=...)``)
    survives to the derived digest. Anything that cannot round-trip
    cleanly fails closed with the typed ``NoteConfigInvalidError``. For an
    honestly validated config the round-trip is a byte-stable identity, so
    ``config_digest`` is unchanged.
    """
    try:
        blob = NoteConfig.__pydantic_serializer__.to_json(config)
        return NoteConfig.model_validate_json(blob)
    except (ValidationError, PydanticSerializationError) as exc:
        raise NoteConfigInvalidError(
            f"config presented at the generation boundary is invalid: {exc}"
        ) from exc


def bind_template_profile(
    config: NoteConfig, template_profile_id: str | None = None
) -> BoundTemplateProfile:
    """THE single resolution of a session's template profile.

    A session cannot generate a note without a bound profile: zero profiles
    raise, an unknown explicit id raises, and more than one profile without
    an explicit choice raises (that — and only that — is the case where a
    chooser UI appears; it must never ask the clinician to pick from a list
    of one). The sole configured profile binds automatically, which is
    today's reality: both clinics share one captured template.

    The input config is CANONICALISED first (``_canonical_config``), so the
    returned binding's stored config is always an exact, fully re-validated
    ``NoteConfig`` and everything the binding derives — profile, digest —
    derives from validated field data, even when the caller's object was a
    subclass or skipped validation.
    """
    config = _canonical_config(config)
    profiles = config.template_profiles
    if template_profile_id is not None:
        for profile in profiles:
            if profile.template_profile_id == template_profile_id:
                return BoundTemplateProfile(
                    source_config=config, template_profile_id=template_profile_id
                )
        raise TemplateProfileUnboundError(
            f"unknown template_profile_id: {template_profile_id}"
        )
    if not profiles:
        raise TemplateProfileUnboundError(
            "no template profiles are configured; a session cannot generate a note "
            "without a bound profile"
        )
    if len(profiles) == 1:
        return BoundTemplateProfile(
            source_config=config,
            template_profile_id=profiles[0].template_profile_id,
        )
    raise TemplateProfileUnboundError(
        f"{len(profiles)} template profiles are configured; an explicit "
        "template_profile_id is required"
    )


def build_note_request(
    document: TranscriptDocument,
    config: NoteConfig,
    template_profile_id: str | None = None,
    *,
    clinician_speaker: str | None = None,
    section_keys: tuple[NoteSectionKey, ...] = CANONICAL_SECTION_KEYS,
) -> NoteRequest:
    """THE generation-facing request constructor (Task 3.1 Done-when: a
    session cannot generate a note without a bound profile; rounds 10–12
    PR-MED-001).

    Accepts the source config plus the selected id and RE-ESTABLISHES the
    binding itself, inside the boundary: the config is canonicalised to an
    exact re-validated ``NoteConfig``, membership is resolved by
    ``bind_template_profile``, and the digest is derived locally from that
    canonical config's field data. No caller-supplied wrapper is trusted —
    round 12 showed a binding's virtual properties can lie — so a
    zero/unknown/unselected profile state or a profile/digest cross-pair
    fails here for every argument VALUE, including subclasses and
    validator-skipping constructions.

    What this boundary deliberately does NOT claim: Python has no defence
    against runtime monkey-patching of this module or direct ``__dict__``
    tampering, and an already-built request's own pydantic escape hatches
    reached through a VARIABLE (e.g. ``request.model_copy``) are invisible
    to static analysis. Those routes sit outside the threat model
    (same-user posture, plan trust boundary). In shipping source, ANY
    runtime reference to ``NoteRequest`` (or the raw assembler) outside
    annotations and the single pinned internal call — whatever the pydantic
    API spelling, adapter, or alias shape — is refused by the AST
    reference-confinement guard (``TestConstructionGuard``), fixtures
    excepted (round 13 PR-MED-001).
    """
    binding = bind_template_profile(config, template_profile_id)
    return _assemble_note_request(
        document,
        template_profile_id=binding.template_profile_id,
        config_digest=binding.source_config.config_digest(),
        clinician_speaker=clinician_speaker,
        section_keys=section_keys,
    )


def mapping_drop_warnings(
    profile: TemplateProfile, note_sections: Sequence[GeneratedSection]
) -> tuple[NoteWarning, ...]:
    """`mapping_drop` review warnings for populated sections this profile
    would silently lose (Task 3.1 Done-when: warn rather than discard).

    Fires only for sections that are POPULATED and unmapped by OVERSIGHT:
    empty sections drop nothing, and ``intentionally_unmapped`` sections are
    silent by design. The registered severity is ``review``, which never
    blocks — round 2 recorded why an error grade would deadlock Complete.

    Round 45 MED-002: this docstring used to say "Phase 7 owns rendering it
    under 'Unmapped content'". It does not, and did not: the round-2
    "Unmapped content" target belongs to the MAPPED OUTPUT, which is Phase
    4's, and the shipped Template A drops nothing anyway. In 3A the dropped
    section is still rendered in the note body like any other populated
    canonical section — the warning says the chosen template has no FIELD to
    carry it, not that the content is hidden.
    """
    dropped = frozenset(profile.unmapped_section_keys())
    return tuple(
        NoteWarning(
            note_warning_code="mapping_drop",
            severity="review",
            section_key=section.section_key,
        )
        for section in note_sections
        if section.note_assertions and section.section_key in dropped
    )
