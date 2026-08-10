"""Note config engine (Phase 3A, Tasks 3.1-3.3).

This module owns the CONFIG side of the note pipeline: the template-mapping
model (canonical section -> real Cliniko template field), the autofill-rule
and prefill-template schemas, and the validating loader that resolves shipped
defaults against clinician overrides into one immutable ``NoteConfig``.

Config files are clinician-authored boilerplate, NOT patient data (plan
Schema / Data Changes): they live in plaintext under
``%LOCALAPPDATA%\\ClinikoScribe\\config\\``, deliberately outside the
encrypted session store and the 24 h rule, so they survive session
destruction. Nothing in this module touches a session key or a clinical
artifact.

Resolution precedence (Task 3.2 — the specification ``config_digest``
depends on):

- **Per-file, whole-file replacement.** For each of the three config
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

import os
import unicodedata
from collections.abc import Sequence
from importlib import resources
from pathlib import Path
from typing import Annotated, Final, Literal, Self, final

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)
from pydantic_core import PydanticSerializationError

from scribe_desktop.note import (
    # Package-private by name, shared deliberately (the note.py convention):
    # one id grammar, one digest primitive, and one raw request assembler
    # across the note pipeline. ``_assemble_note_request`` is consumed ONLY
    # by ``build_note_request`` below — the generation-facing boundary lives
    # here because the reverse import would be a cycle.
    _ID_PATTERN,
    _PROFILE_ID_PATTERN,
    CANONICAL_SECTION_KEYS,
    GeneratedSection,
    NoteRequest,
    NoteSectionKey,
    NoteWarning,
    _assemble_note_request,
    content_tokens,
    digest_bytes,
)
from scribe_desktop.transcription import TranscriptDocument

CONFIG_DIRNAME: Final = "config"
TEMPLATE_PROFILES_FILENAME: Final = "template_profiles.json"
AUTOFILL_RULES_FILENAME: Final = "autofill_rules.json"
PREFILL_TEMPLATES_FILENAME: Final = "prefill_templates.json"
CONFIG_FILENAMES: Final[tuple[str, ...]] = (
    TEMPLATE_PROFILES_FILENAME,
    AUTOFILL_RULES_FILENAME,
    PREFILL_TEMPLATES_FILENAME,
)

# Shipped defaults travel INSIDE the package (Task 3.3): package data under
# ``scribe_desktop/config_defaults/``, read through ``importlib.resources``
# so a non-editable (wheel) install resolves them identically to the dev
# checkout. Never resolved via ``__file__`` and never via LOCALAPPDATA.
_DEFAULTS_RESOURCE_DIR: Final = "config_defaults"

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
# The tuple type refuses a bare string outright; Task 4.0 adds the
# fix-naming message on top.
# ---------------------------------------------------------------------------


class AutofillRule(BaseModel):
    """One trigger phrase -> a list of atomic assertion texts, all landing in
    one canonical section. Phase 4's matcher is bound by the Critical
    Constraint: a matched trigger may only ever turn each expansion entry
    into a proposal, never an insertion."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str = Field(pattern=_ID_PATTERN)
    section_key: NoteSectionKey
    trigger_phrase: _TriggerText
    expansion: tuple[_AssertionText, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_trigger(self) -> Self:
        if not content_tokens(self.trigger_phrase):
            raise ValueError(
                f"rule {self.rule_id}: trigger_phrase has no content tokens and could never fire"
            )
        return self


class PrefillSeedAssertion(BaseModel):
    """One atomic assertion of a prefill seed, bound to its section."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    section_key: NoteSectionKey
    seed_text: _AssertionText


class PrefillTemplate(BaseModel):
    """A body-region seed: detection keywords plus atomic seed assertions.
    Phase 4's prefill owes one proposal per seed assertion — never an
    assertion directly."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    prefill_id: str = Field(pattern=_ID_PATTERN)
    display_name: _LabelText
    region_keywords: tuple[_TriggerText, ...] = Field(min_length=1)
    seed_assertions: tuple[PrefillSeedAssertion, ...] = Field(min_length=1)


# ---------------------------------------------------------------------------
# The three config FILES (one pydantic model each) and the RESOLVED config.
# ---------------------------------------------------------------------------


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

    @model_validator(mode="after")
    def _check_config(self) -> Self:
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
        # included: config is clinician-EDITED plaintext boilerplate, not
        # clinical content, and "fails loudly" must name what to fix.
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
    profiles_file = _parse_config_blob(
        TemplateProfilesFile, profiles_blob, TEMPLATE_PROFILES_FILENAME, profiles_source
    )
    rules_file = _parse_config_blob(
        AutofillRulesFile, rules_blob, AUTOFILL_RULES_FILENAME, rules_source
    )
    prefills_file = _parse_config_blob(
        PrefillTemplatesFile, prefills_blob, PREFILL_TEMPLATES_FILENAME, prefills_source
    )
    try:
        return NoteConfig(
            template_profiles=profiles_file.template_profiles,
            autofill_rules=rules_file.autofill_rules,
            prefill_templates=prefills_file.prefill_templates,
        )
    except ValidationError as exc:
        raise NoteConfigInvalidError(f"resolved note config is invalid: {exc}") from exc


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
    blocks — round 2 recorded why an error grade would deadlock Complete —
    and Phase 7 owns rendering it under "Unmapped content".
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
