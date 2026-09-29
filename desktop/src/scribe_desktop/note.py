"""Note pipeline foundations (Phase 3A, Tasks 1.1-1.3).

This module owns the note artifact's TYPE MODEL, the single tokenisation
source shared by autofill matching and the checkers, and the two providers
that stand behind the ``NoteModelProvider`` seam in 3A.

The safety properties this module is responsible for are STRUCTURAL — they
hold because the types cannot express the unsafe state, not because a
caller behaves (plan Key Design Decisions):

- ``NoteAssertion`` is the unit a section holds, and it carries EXACTLY ONE
  span with EXACTLY ONE contiguous ``(segment_index, first_word_index,
  last_word_index)`` interval. Assembling one assertion out of two
  independently-grounded transcript intervals ("the cervical spine" + "is
  tender") is unrepresentable, not merely checked: span-local coordinate
  reconstruction is exact but does not compose.
- ``NoteProposal`` is a DIFFERENT type from ``NoteAssertion`` and a
  ``GeneratedSection`` holds only assertions, so an unconfirmed proposal
  cannot reach ``note.enc`` by construction.
- Every non-``transcript`` assertion carries its ``proposal_id``, the
  ``shown_text_digest`` of the exact text the clinician was shown, the
  ``config_digest`` it came from, and a confirmed ``ConfirmationDecision``.
  Confirmation is reconstructible from the artifact alone. (The digest is
  re-VERIFIED against the text inside ``write_note`` — Task 6.2 — which is
  why construction requires the record's PRESENCE but does not itself
  recompute the match: the defence-in-depth check must stay testable.)
- Schema v2 (note-learning-and-styles plan, Phase 0 Task 0.2; D4, D5, D7).
  A ``clinician`` assertion is text the clinician TYPED over a note line:
  it carries the same digests and a decision that names the line itself
  (``decided_by="clinician"``; no ``proposal_id`` — nothing proposed it) and
  may record the id of the line it ``replaces``. A line the practitioner's
  OWN config pre-filled keeps its ``autofill``/``prefill`` provenance (the
  text's origin is unchanged) and its decision records
  ``decided_by="config"`` with the digest it was minted under — a config
  decision without that digest is unrepresentable. The note records its
  writing ``style`` and per-section ``style_renderings``; every v2 field
  defaults to the v1 shape, so a v1 ``note.enc`` reads unchanged and a note
  that declares version 1 cannot carry v2 content.
- Provenance proves ATTRIBUTION, never truth. Trigger presence, role
  attribution and provenance say nothing about whether a claim is true of
  this encounter; only a recorded decision does — the clinician's per-line
  confirmation, or (D5) the counted Save that ratifies a config-decided line
  under its mark.

Constraints honoured (plan Critical Constraints):
- No ML imports, no network I/O, no new runtime dependency — this module
  runs on every CI leg, not behind the best-effort ``[ml]`` install.
- Clinical content NEVER passes through logging. The content-bearing field
  names (``note_sections``, ``note_assertions``, ``note_spans``,
  ``span_text``, ``note_excerpt``, ``note_warnings``, ``note_warning_code``,
  ``note_confirmation``, and the reused ``transcript_words`` /
  ``word_text``) are DELIBERATE: each is registered as a tripwire signature
  in ``logging_setup._PAYLOAD_SIGNATURES``, so any repr / ``model_dump`` /
  JSON of a note model is dropped by the last-line log filter — exactly the
  convention ``transcription.py`` established for the transcript artifact.
- Documentation-only: neither provider invents clinical content.
  ``ExtractiveNoteProvider`` emits verbatim transcript spans and nothing
  else; ``MockNoteModelProvider`` fabricates ON PURPOSE and ships only as
  the adversarial instrument the Axis B fixture matrix drives.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from importlib import resources
from typing import TYPE_CHECKING, Final, Literal, NamedTuple, Protocol, Self, final

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scribe_desktop.session_store import SESSION_ID_PATTERN
from scribe_desktop.transcription import (
    # THE single punctuation-stripping rule (plan: one normalisation source;
    # divergent normalisers would make Check 3 raise ``autofill_trigger_absent``
    # errors on rules that legitimately fired). Package-private by name, shared
    # deliberately rather than duplicated.
    _STRIP_PUNCT_RE,
    TranscriptDocument,
    TranscriptWord,
    is_name_like_token,
)

if TYPE_CHECKING:
    # Annotation-only: importing note_config at runtime would be a cycle
    # (note_config imports this module). The pipeline functions below import
    # it at CALL time instead — the same deferred-import convention
    # session_store uses for this module.
    from scribe_desktop.note_config import LearnedRuleEntry, NoteConfig

# ---------------------------------------------------------------------------
# The canonical section set (17, stable keys) — plan Schema / Data Changes.
#
# Sections are referenced BY KEY, never by ordinal: the set has already grown
# once (``progress_since_last_visit``), and ordinal references are how
# off-by-one errors get baked into fixtures. Mapping onto a practitioner's
# real Cliniko template is Task 3.1's config, never a property of this list.
# ---------------------------------------------------------------------------

NoteSectionKey = Literal[
    "presenting_complaint",
    "history_presenting_complaint",
    "progress_since_last_visit",
    "past_medical_history",
    "red_flags_screening",
    "objective_examination",
    "outcome_measures",
    "assessment",
    "diagnosis",
    "treatment_performed",
    "response_to_treatment",
    "advice_home_exercise",
    "management_plan",
    "consent",
    "referrals_investigations",
    "precautions_contraindications",
    "follow_up_review",
]

SectionOwner = Literal["patient", "clinician", "either"]


class CanonicalSection(NamedTuple):
    """One canonical section: its stable key, display title, and who owns it."""

    key: NoteSectionKey
    title: str
    owner: SectionOwner


CANONICAL_SECTIONS: Final[tuple[CanonicalSection, ...]] = (
    CanonicalSection("presenting_complaint", "Presenting complaint", "patient"),
    CanonicalSection(
        "history_presenting_complaint", "History of presenting complaint", "patient"
    ),
    CanonicalSection("progress_since_last_visit", "Progress since last visit", "patient"),
    CanonicalSection("past_medical_history", "Past medical history", "patient"),
    CanonicalSection("red_flags_screening", "Red flags screening", "either"),
    CanonicalSection("objective_examination", "Objective examination", "clinician"),
    CanonicalSection("outcome_measures", "Outcome measures", "either"),
    CanonicalSection("assessment", "Assessment", "clinician"),
    CanonicalSection("diagnosis", "Diagnosis", "clinician"),
    CanonicalSection("treatment_performed", "Treatment performed", "clinician"),
    CanonicalSection("response_to_treatment", "Response to treatment", "either"),
    CanonicalSection("advice_home_exercise", "Advice and home exercise", "clinician"),
    CanonicalSection("management_plan", "Management plan", "clinician"),
    CanonicalSection("consent", "Consent", "clinician"),
    CanonicalSection("referrals_investigations", "Referrals and investigations", "clinician"),
    CanonicalSection(
        "precautions_contraindications", "Precautions and contraindications", "clinician"
    ),
    CanonicalSection("follow_up_review", "Follow-up and review", "clinician"),
)

CANONICAL_SECTION_KEYS: Final[tuple[NoteSectionKey, ...]] = tuple(
    section.key for section in CANONICAL_SECTIONS
)

SECTION_INDEX: Final[Mapping[NoteSectionKey, int]] = {
    section.key: index for index, section in enumerate(CANONICAL_SECTIONS)
}

# Populate ONLY after per-session clinician-role confirmation (Critical
# Constraint); an unresolved role leaves every one of these blank.
CLINICIAN_OWNED_SECTIONS: Final[frozenset[NoteSectionKey]] = frozenset(
    {"assessment", "diagnosis", "advice_home_exercise", "management_plan"}
)

# ---------------------------------------------------------------------------
# Digests.
#
# ``transcript_digest`` is defined ONCE, here, and verified identically by
# ``read_note`` (Task 6.2) and ``complete_session`` (Task 1.5):
#   algorithm  : SHA-256
#   version tag: "sha256-v1" (prefix; a future algorithm change bumps it)
#   byte domain: the DECRYPTED canonical ``TranscriptDocument.to_bytes()``
#                output — i.e. ``model_dump_json().encode("utf-8")``, the
#                exact bytes ``write_transcript`` encrypts. Never ciphertext
#                (which is nonce-randomised and would never compare equal).
# ---------------------------------------------------------------------------

DIGEST_ALGORITHM: Final = "sha256-v1"
DIGEST_PATTERN: Final = r"^sha256-v1:[0-9a-f]{64}$"
_DIGEST_RE: Final = re.compile(DIGEST_PATTERN)

_ID_PATTERN: Final = r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$"
_PROFILE_ID_PATTERN: Final = r"^[a-z0-9][a-z0-9_-]{0,63}$"

# Artifact bound on any single assertion or proposal text. Deliberately far
# above any real utterance (~3 000 words): an extractive assertion is one
# whole VAD segment, and a long unbroken segment must not turn note
# generation into a raw pydantic ValidationError (round 1 LOW-003). This is
# an artifact sanity bound, not a content policy — per-field config limits
# are Task 3.2's.
MAX_ASSERTION_CHARS: Final = 20_000
# Artifact bound on one section's prose rendering (schema v2, D7): a section
# re-phrases several assertions, so it is allowed more than one; the same
# sanity-not-policy caveat applies.
MAX_SECTION_PROSE_CHARS: Final = 40_000


def digest_bytes(blob: bytes) -> str:
    """THE digest primitive: ``"sha256-v1:<hex>"`` over exact bytes."""
    return f"{DIGEST_ALGORITHM}:{hashlib.sha256(blob).hexdigest()}"


def transcript_digest(document: TranscriptDocument) -> str:
    """Digest of a transcript artifact over its canonical serialization."""
    return digest_bytes(document.to_bytes())


def text_digest(text: str) -> str:
    """Digest of exact displayed text (``shown_text_digest``)."""
    return digest_bytes(text.encode("utf-8"))


# ---------------------------------------------------------------------------
# Tokenisation — Task 1.2. ONE implementation, consumed by autofill trigger
# matching (4.1), the structured contradiction checks (5.2), and Check 4
# omission (5.4). NOT by Check 1, which is exact coordinate reconstruction
# and needs no tokenisation at all.
# ---------------------------------------------------------------------------

# Disfluencies only. Negation and hedging words ("not", "no", "never",
# "denies", "maybe") are content: dropping them would make a negated claim
# and its opposite tokenise identically, which is precisely the failure the
# contradiction checks exist to catch.
_FILLER_TOKENS: Final[frozenset[str]] = frozenset(
    {"um", "uh", "uhm", "erm", "er", "ah", "mm", "mmm", "hmm", "mhm"}
)


def strip_token_punctuation(token: str) -> str:
    """The ONE punctuation rule, case PRESERVED: leading and trailing
    punctuation stripped, nothing else changed — ``normalise_token`` is this
    plus lower-casing. For the callers that must keep the original case
    (the refusal filter's vocabulary check, the sample-note learner's
    shorthand split) so no second punctuation rule can appear beside
    ``transcription._STRIP_PUNCT_RE``. Returns "" for a token that is
    entirely punctuation."""
    return _STRIP_PUNCT_RE.sub("", token)


def normalise_token(token: str) -> str:
    """Normalise one token: strip leading/trailing punctuation, lowercase.

    Built on ``transcription._STRIP_PUNCT_RE`` so transcript-side and
    note-side normalisation can never drift apart. Returns "" for a token
    that is entirely punctuation.
    """
    return strip_token_punctuation(token).lower()


def content_tokens(text: str) -> tuple[str, ...]:
    """Normalised content tokens of ``text``: punctuation-only tokens and
    pure disfluencies dropped, everything else preserved in order."""
    tokens: list[str] = []
    for raw in text.split():
        token = normalise_token(raw)
        if token and token not in _FILLER_TOKENS:
            tokens.append(token)
    return tuple(tokens)


def reconstruct_span_text(words: Sequence[TranscriptWord]) -> str:
    """THE canonical rendering of a transcript word range into span text.

    Whisper emits word text with leading spaces, so "exact reconstruction"
    needs one agreed rule or Check 1 (Task 5.1) would fail on whitespace
    alone. The rule: strip each word, drop empties, join with single
    spaces. Providers build span text with this function and Check 1
    rebuilds with the same function, so the comparison is exact.
    """
    return " ".join(stripped for word in words if (stripped := word.word_text.strip()))


# ---------------------------------------------------------------------------
# Warning taxonomy.
#
# Severity is a property of the CODE, not of the emitting site: an `error`
# blocks ``write_note``, copy, and Complete, so a check must not be able to
# emit `mapping_drop` as an error (round 2: an unclearable block deadlocks
# Complete and the 24 h sweep then destroys the session). Later checker
# tasks (5.1, 5.2, 5.4) EXTEND this registry; they never re-grade a code
# already in it.
# ---------------------------------------------------------------------------

NoteWarningSeverity = Literal["error", "review"]

NOTE_WARNING_SEVERITY: Final[Mapping[str, NoteWarningSeverity]] = {
    # Check 1 — exact coordinate reconstruction (Task 5.1).
    "source_coords_invalid": "error",  # coordinates address words the transcript does not have
    "reconstruction_mismatch": "error",  # the span text is not what its coordinates say
    "low_confidence_source": "review",  # an INCLUDED source word below UNCERTAINTY_THRESHOLD
    # Check 2 — structured contradictions (Task 5.2). Three codes because
    # severity is a property of the code: a contradiction resting on
    # transcript evidence whose words fall below UNCERTAINTY_THRESHOLD is
    # graded review — the raw ``probability``, NEVER the ``uncertain`` flag,
    # which also marks every number and name regardless of confidence — and
    # (round 23) a dose-value difference whose SAME-CLINICAL-STATE identity
    # is not mechanically established (dose changes, titrations, inventory
    # strengths and history are ordinary documentation) is `dose_mismatch`:
    # surfaced for review and acknowledgement, never a block. The `error`
    # grade requires identical statement context — the same medication fact
    # with incompatible values.
    "contradiction": "error",
    "contradiction_low_confidence": "review",
    "dose_mismatch": "review",
    # Task H4.1 (round 58, practitioner-ratified 2026-09-03): a differing
    # laterality value is REVIEW, never a block. Five cross-family rounds
    # (48-50, 54-58) each found a new bilateral or correlative wording that
    # clause-splitting made one-sided, and an error-grade `contradiction`
    # then blocked Save, Copy and Complete on a consistent note. The parser
    # cannot mechanically establish shared-anchor bilateral wording, so -
    # exactly as rounds 21-24 drew the line for dose - the signal stays and
    # the block goes: the clinician must acknowledge, and may then save.
    "laterality_mismatch": "review",
    # Check 3 — provenance integrity (Task 5.3).
    "unconfirmed_proposal": "error",
    "autofill_trigger_absent": "error",
    "role_unconfirmed": "error",
    "clinician_asserted": "review",  # unsuppressible; acknowledgement is the exit
    # Never a block (round 2: an error grade would be unclearable and
    # deadlock Complete). Round 45 MED-002: this comment used to say the
    # warning "renders into 'Unmapped content'" — that mapped-output target
    # is Phase 4's and does not exist in 3A. The section itself is still
    # rendered in the note body; only a template FIELD for it is missing.
    "mapping_drop": "review",
    # Check 4 — scoped omission (Task 5.4). Review, never error: a heuristic
    # must not be able to block Complete on a false positive.
    "high_risk_omission": "review",
    # Check 5 — prose fidelity (note-learning-and-styles plan Task 4.2, D6):
    # a section whose language-model prose failed the fidelity gate is shown
    # as `clean` (its confirmed lines, unchanged) and says so. Review, never
    # error: the fallback IS the safe rendering, and the practitioner
    # acknowledges that the section reads as Clean clinical.
    "style_fallback": "review",
}


class SourceCoords(NamedTuple):
    """The ONE contiguous transcript interval a span may cite.

    A plain 3-tuple by design: coordinates are indices, carry no clinical
    content, and serialize as ``[segment, first, last]`` inside the span.
    """

    segment_index: int
    first_word_index: int
    last_word_index: int


# The provenance set (schema v2, D4). ``clinician`` is text the clinician
# TYPED over a note line — neither quoted (no coordinates) nor proposed (no
# rule, no proposal id). A line the practitioner's config PRE-FILLED is NOT a
# provenance of its own: the text still originates in a rule or template, so
# it keeps ``autofill`` / ``prefill`` and the DECISION says ``config`` (D5).
NoteProvenance = Literal["transcript", "autofill", "prefill", "clinician"]
# Who made the recorded decision: the clinician on screen (a per-line
# confirm, or a typed line) or the practitioner's own config, ratified by the
# Save that shows the pre-filled lines (D5).
DecidedBy = Literal["clinician", "config"]
# What a draft's BASE sections may hold (D4): quoted lines from the provider
# and the clinician's typed lines from the review surface. Rule-authored
# ``autofill``/``prefill`` text enters solely as proposals, never as base.
DRAFT_BASE_PROVENANCES: Final[frozenset[str]] = frozenset({"transcript", "clinician"})


class NoteSpan(BaseModel):
    """A single stretch of note text plus where it came from.

    ``provenance`` proves attribution, not truth. ``transcript`` spans carry
    coordinates and are verified by exact reconstruction (Check 1);
    ``autofill`` / ``prefill`` spans are clinician-authored boilerplate and
    ``clinician`` spans are text the clinician typed (schema v2, D4) — none
    of the three carries coordinates, and each is carried by its recorded
    decision alone.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    span_text: str = Field(min_length=1, max_length=MAX_ASSERTION_CHARS)
    provenance: NoteProvenance
    source_coords: SourceCoords | None = None

    @model_validator(mode="after")
    def _check_provenance(self) -> Self:
        if not self.span_text.strip():
            raise ValueError("span_text must not be blank")
        if self.provenance == "transcript":
            coords = self.source_coords
            if coords is None:
                raise ValueError("a transcript span requires source_coords")
            if coords.segment_index < 0 or coords.first_word_index < 0:
                raise ValueError("source_coords indices must be non-negative")
            if coords.last_word_index < coords.first_word_index:
                raise ValueError("source_coords must satisfy first_word_index <= last_word_index")
        elif self.source_coords is not None:
            # autofill, prefill AND clinician: typed text quotes nothing.
            raise ValueError(f"a {self.provenance} span must not carry source_coords")
        return self


class ConfirmationDecision(BaseModel):
    """The recorded decision on one proposal — or, for a typed line, on the
    line itself (``proposal_id`` then names the assertion: nothing proposed
    it, and the id says what was decided).

    Evidence carried by the artifact, not a caller convention: from
    ``note.enc`` alone it is reconstructible that a human was shown this
    exact text and confirmed it — or (schema v2, D5) that the practitioner's
    OWN config pre-filled it under ``config_digest`` and the counted Save
    ratified it. ``decided_by`` defaults to ``clinician`` so every v1 record
    reads; a ``config`` decision MUST carry the digest it was minted under
    and MAY carry the rule's ``confirmation_count`` (D5's auto-confirm
    evidence); a clinician decision carries neither.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: str = Field(pattern=_ID_PATTERN)
    note_confirmation: Literal["confirmed", "declined"]
    decided_at: datetime
    decided_by: DecidedBy = "clinician"
    config_digest: str | None = None
    confirmation_count: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _check_decider(self) -> Self:
        if self.decided_by == "config":
            if self.config_digest is None or not _DIGEST_RE.match(self.config_digest):
                raise ValueError(
                    f"a config decision requires a config_digest matching {DIGEST_PATTERN}"
                )
            return self
        if self.config_digest is not None or self.confirmation_count is not None:
            raise ValueError(
                "a clinician decision carries no config_digest or confirmation_count"
            )
        return self


class NoteAssertion(BaseModel):
    """ONE atomic clinical claim — the unit a ``GeneratedSection`` holds.

    Exactly one span with exactly one contiguous interval: grammatical
    assembly of two independently-grounded transcript ranges into one
    assertion is prohibited by the type, not by a check.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    assertion_id: str = Field(pattern=_ID_PATTERN)
    section_key: NoteSectionKey
    note_span: NoteSpan
    speaker: str | None = None
    # Non-transcript provenance only — the confirmation evidence chain.
    proposal_id: str | None = None
    shown_text_digest: str | None = None
    config_digest: str | None = None
    confirmation: ConfirmationDecision | None = None
    # ``clinician`` provenance only (schema v2, D4): the id of the note line
    # or proposal this typed text replaced, when it replaced one.
    replaces: str | None = Field(default=None, pattern=_ID_PATTERN)

    @property
    def provenance(self) -> NoteProvenance:
        return self.note_span.provenance

    @property
    def text(self) -> str:
        return self.note_span.span_text

    @model_validator(mode="after")
    def _check_confirmation(self) -> Self:
        evidence = (self.proposal_id, self.shown_text_digest, self.config_digest)
        if self.provenance == "transcript":
            if any(field is not None for field in evidence) or self.confirmation is not None:
                raise ValueError(
                    "a transcript assertion carries no proposal/confirmation evidence"
                )
            if self.replaces is not None:
                raise ValueError("a transcript assertion replaces nothing")
            return self
        confirmation = self.confirmation
        if self.provenance == "clinician":
            # D4: typed text. No proposal existed, so the decision names the
            # line itself; the digests are the same evidence every authored
            # line carries and ``write_note`` verifies them the same way.
            if self.proposal_id is not None:
                raise ValueError(
                    "a clinician assertion carries no proposal_id: nothing proposed it"
                )
            if self.shown_text_digest is None or self.config_digest is None or confirmation is None:
                raise ValueError(
                    "a clinician assertion requires shown_text_digest, config_digest and a "
                    "ConfirmationDecision"
                )
            if confirmation.decided_by != "clinician":
                raise ValueError("a typed line is decided by the clinician, never by config")
            if confirmation.proposal_id != self.assertion_id:
                raise ValueError(
                    "a clinician assertion's decision must name the assertion itself"
                )
            if self.replaces == self.assertion_id:
                raise ValueError("an assertion cannot replace itself")
        else:
            if any(field is None for field in evidence) or confirmation is None:
                raise ValueError(
                    f"a {self.provenance} assertion requires proposal_id, shown_text_digest, "
                    "config_digest and a ConfirmationDecision"
                )
            if confirmation.proposal_id != self.proposal_id:
                raise ValueError(
                    "confirmation.proposal_id does not match the assertion's proposal_id"
                )
            if self.replaces is not None:
                raise ValueError(f"a {self.provenance} assertion replaces nothing")
            # D5: a config decision is evidence about ONE config — the one the
            # pre-filled line was minted under, which is this assertion's.
            if (
                confirmation.decided_by == "config"
                and confirmation.config_digest != self.config_digest
            ):
                raise ValueError(
                    "a config decision's config_digest must be the assertion's config_digest"
                )
        for label, value in (
            ("shown_text_digest", self.shown_text_digest),
            ("config_digest", self.config_digest),
        ):
            if value is None or not _DIGEST_RE.match(value):
                raise ValueError(f"{label} must match {DIGEST_PATTERN}")
        if confirmation.note_confirmation != "confirmed":
            raise ValueError("a declined proposal must never become an assertion")
        return self


class NoteProposal(BaseModel):
    """A CANDIDATE assertion awaiting explicit confirmation of its exact text.

    Structurally distinct from ``NoteAssertion``: a proposal cannot be placed
    in a ``GeneratedSection``, so unconfirmed content cannot reach the saved
    note. One proposal per ATOMIC assertion — a three-claim expansion is
    three proposals, because confirming a block is not evidence about each
    claim inside it. A typed ``clinician`` line is never a proposal (D4):
    nothing proposed it, so it enters the draft base carrying its own
    decision instead.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: str = Field(pattern=_ID_PATTERN)
    section_key: NoteSectionKey
    provenance: Literal["autofill", "prefill"]
    note_excerpt: str = Field(min_length=1, max_length=MAX_ASSERTION_CHARS)
    rule_id: str = Field(pattern=_ID_PATTERN)
    config_digest: str
    trigger_start_seconds: float | None = Field(default=None, ge=0)

    @property
    def shown_text_digest(self) -> str:
        """Digest of the EXACT text the clinician is shown and confirms."""
        return text_digest(self.note_excerpt)

    @model_validator(mode="after")
    def _check_digest(self) -> Self:
        if not self.note_excerpt.strip():
            raise ValueError("note_excerpt must not be blank")
        if not _DIGEST_RE.match(self.config_digest):
            raise ValueError(f"config_digest must match {DIGEST_PATTERN}")
        return self


class NoteWarning(BaseModel):
    """One checker finding. Carries codes and coordinates — never clinical
    text: a warning is rendered beside the content it points at."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    note_warning_code: str
    severity: NoteWarningSeverity
    section_key: NoteSectionKey | None = None
    assertion_id: str | None = None
    source_coords: SourceCoords | None = None
    # RESERVED AND NEVER SET (round 45 LOW-002). Acknowledgement is per-code
    # IN-MEMORY review state owned by the Note tab: it gates Complete, it is
    # deliberately not persisted, and `write_note` deliberately does not
    # require it (plan Task 7 design decision (d)) — so nothing in shipping
    # source or tests ever writes True here. Kept rather than removed
    # because `extra="forbid"` would make every already-written `note.enc`
    # fail `from_bytes` after a removal, blocking Complete on an in-flight
    # session with its key retained. Wire it only alongside a `write_note`
    # check that gives it meaning.
    acknowledged: bool = False

    @model_validator(mode="after")
    def _check_code(self) -> Self:
        expected = NOTE_WARNING_SEVERITY.get(self.note_warning_code)
        if expected is None:
            raise ValueError(f"unregistered warning code: {self.note_warning_code}")
        if expected != self.severity:
            raise ValueError(
                f"warning {self.note_warning_code} is {expected}-severity, not {self.severity}"
            )
        return self


class GeneratedSection(BaseModel):
    """One canonical section of the note and the assertions it holds."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    section_key: NoteSectionKey
    note_assertions: tuple[NoteAssertion, ...] = ()

    @model_validator(mode="after")
    def _check_assertions(self) -> Self:
        for assertion in self.note_assertions:
            if assertion.section_key != self.section_key:
                raise ValueError(
                    f"assertion {assertion.assertion_id} belongs to "
                    f"{assertion.section_key}, not {self.section_key}"
                )
        return self


# The writing styles (schema v2, D7): ``verbatim`` and ``clean`` are
# deterministic renderings of the assertions; ``own_voice`` and ``narrative``
# are prose from the local language model, gated by Check 5 (Phase 4).
NoteStyle = Literal["verbatim", "clean", "own_voice", "narrative"]
StyleVerdict = Literal["passed", "failed"]

# Bumped by schema v2 (note-learning-and-styles plan, Phase 0). Readers accept
# both versions; a note that declares 1 must be v1-SHAPED (the validator
# below refuses v2 content under a v1 label), and an unknown version is
# refused outright rather than read on a guess.
NOTE_SCHEMA_VERSION: Final = 2


class StyleRendering(BaseModel):
    """One section's prose rendering (schema v2, D7): the prose the local
    language model produced for the CONFIRMED assertions of ``section_key``,
    the digest of the exact assertion texts it was given (``input_digest`` —
    the binding the rendering path checks before showing it, so a rendering
    whose inputs no longer match the section is stale and never displayed),
    and the Check 5 fidelity verdict. A ``failed`` rendering carries NO prose:
    the text the gate refused is not persisted (C4), and the section falls
    back to ``clean`` (Phase 4 wires the fallback and its warning). The field
    name ``prose_text`` is deliberately distinctive — it is a tripwire
    signature in ``logging_setup``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    section_key: NoteSectionKey
    prose_text: str = Field(max_length=MAX_SECTION_PROSE_CHARS)
    input_digest: str
    verdict: StyleVerdict

    @model_validator(mode="after")
    def _check_rendering(self) -> Self:
        if not _DIGEST_RE.match(self.input_digest):
            raise ValueError(f"input_digest must match {DIGEST_PATTERN}")
        if self.verdict == "passed":
            if not self.prose_text.strip():
                raise ValueError("a passed rendering must carry prose")
        elif self.prose_text:
            raise ValueError("a failed rendering carries no prose: refused text is not kept")
        return self


class GeneratedNote(BaseModel):
    """The complete note artifact stored in ``note.enc``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1, 2] = NOTE_SCHEMA_VERSION
    session_id: str = Field(pattern=SESSION_ID_PATTERN)
    created_at: datetime
    template_profile_id: str = Field(pattern=_PROFILE_ID_PATTERN)
    provider_name: str = Field(min_length=1, max_length=64)
    # The cluster confirmed as the clinician (None = role unresolved; the
    # `role_unconfirmed` check, not this type, decides what that blocks).
    clinician_speaker: str | None = None
    transcript_digest: str
    config_digest: str
    note_sections: tuple[GeneratedSection, ...] = ()
    note_warnings: tuple[NoteWarning, ...] = ()
    # Schema v2 (D7): the writing style the note was rendered under and its
    # per-section prose. The defaults ARE the v1 shape.
    style: NoteStyle = "verbatim"
    style_renderings: tuple[StyleRendering, ...] = ()

    def _carries_v2_content(self) -> bool:
        if self.style != "verbatim" or self.style_renderings:
            return True
        for section in self.note_sections:
            for assertion in section.note_assertions:
                decision = assertion.confirmation
                if assertion.provenance == "clinician" or (
                    decision is not None and decision.decided_by == "config"
                ):
                    return True
        return False

    @model_validator(mode="after")
    def _check_note(self) -> Self:
        for label, value in (
            ("transcript_digest", self.transcript_digest),
            ("config_digest", self.config_digest),
        ):
            if not _DIGEST_RE.match(value):
                raise ValueError(f"{label} must match {DIGEST_PATTERN}")
        seen_keys: list[int] = []
        assertion_ids: set[str] = set()
        populated: set[NoteSectionKey] = set()
        for section in self.note_sections:
            index = SECTION_INDEX[section.section_key]
            if seen_keys and index <= seen_keys[-1]:
                raise ValueError("note_sections must be unique and in canonical order")
            seen_keys.append(index)
            populated.add(section.section_key)
            for assertion in section.note_assertions:
                if assertion.assertion_id in assertion_ids:
                    raise ValueError(f"duplicate assertion_id: {assertion.assertion_id}")
                assertion_ids.add(assertion.assertion_id)
        for warning in self.note_warnings:
            if warning.assertion_id is not None and warning.assertion_id not in assertion_ids:
                raise ValueError(f"warning references unknown assertion: {warning.assertion_id}")
        rendered: list[int] = []
        for rendering in self.style_renderings:
            index = SECTION_INDEX[rendering.section_key]
            if rendered and index <= rendered[-1]:
                raise ValueError("style_renderings must be unique and in canonical order")
            rendered.append(index)
            if rendering.section_key not in populated:
                raise ValueError(
                    f"style rendering for {rendering.section_key} names a section the note "
                    "does not populate"
                )
        if self.schema_version == 1 and self._carries_v2_content():
            raise ValueError(
                "a schema-version-1 note cannot carry schema-version-2 content "
                "(a typed line, a config decision, a style or a rendering)"
            )
        return self

    def blocking_warnings(self) -> tuple[NoteWarning, ...]:
        """Unresolved `error` warnings — these block write, copy, and Complete."""
        return tuple(w for w in self.note_warnings if w.severity == "error")

    def to_bytes(self) -> bytes:
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_bytes(cls, blob: bytes) -> GeneratedNote:
        return cls.model_validate_json(blob)


# ---------------------------------------------------------------------------
# Rendering (note-learning-and-styles plan D7; Phase 3 Task 3.2).
#
# ONE rendering path: ``render_note(note, style)`` is what the Note tab
# displays, what Copy copies and what a reloaded ``note.enc`` shows again —
# ``ui.models.format_note_body`` is ``render_note(note, note.style)`` and
# nothing else renders a note body. Its per-section lines come from
# ``render_section_lines``, which the Cliniko draft write reuses without the
# review apparatus (cliniko-draft-write plan D7). ``verbatim`` and ``clean`` are
# deterministic over the assertions (no substitution, no model); the two
# prose styles read the note's ``style_renderings`` and fall back to
# ``clean`` PER SECTION whenever a section has no rendering, a ``failed``
# one, or one whose ``input_digest`` no longer matches the section's
# confirmed texts — a stale rendering is never shown, persisted or copied.
# ---------------------------------------------------------------------------

SECTION_TITLES: Final[Mapping[NoteSectionKey, str]] = {
    section.key: section.title for section in CANONICAL_SECTIONS
}

PROVENANCE_LABELS: Final[Mapping[str, str]] = {
    "transcript": "from transcript",
    "autofill": "autofill (clinician-authored)",
    "prefill": "prefill (clinician-authored)",
    # Schema v2 (D4): text the clinician typed over a line.
    "clinician": "typed (clinician-authored)",
}

# D5: the DISTINCT mark a line pre-filled by the practitioner's own config
# carries wherever it is rendered — every style's note body and the line
# editor — so the counted Save's label and the marked lines agree.
PREFILLED_MARK: Final = "pre-filled by your config"
NO_NOTE_CONTENT: Final = "(no note content)"


def provenance_label(provenance: str) -> str:
    """Human label distinguishing a line's provenance (Phase 3A Task 7.1:
    provenance visibly distinguished). Autofill and prefill are
    clinician-authored boilerplate; a ``clinician`` line is text the
    clinician typed (schema v2); transcript lines are quoted speech verified
    by reconstruction."""
    return PROVENANCE_LABELS.get(provenance, provenance)


def is_prefilled(assertion: NoteAssertion) -> bool:
    """True for a line the practitioner's OWN config decided
    (``decided_by="config"``) — the lines the counted Save ratifies."""
    decision = assertion.confirmation
    return decision is not None and decision.decided_by == "config"


def assertion_label(assertion: NoteAssertion) -> str:
    """The bracketed label a rendered line carries: its provenance label,
    prefixed by ``PREFILLED_MARK`` when the line arrived pre-filled."""
    label = provenance_label(assertion.provenance)
    return f"{PREFILLED_MARK} - {label}" if is_prefilled(assertion) else label


def input_texts_digest(texts: Sequence[str]) -> str:
    """The digest ``section_input_digest`` is built on, over the texts
    themselves: the exact texts, in order, joined by newlines. The prose
    stage (Phase 4) stamps this on the ``StyleRendering`` it produces from
    exactly those texts, so the two sides of the binding share ONE
    implementation."""
    return text_digest("\n".join(texts))


def section_input_digest(section: GeneratedSection) -> str:
    """THE binding between a section's confirmed assertion texts and a prose
    rendering (D7): ``input_texts_digest`` over the section's texts in
    order. Phase 4's prose stage stamps this on each ``StyleRendering``
    it produces; ``usable_rendering`` recomputes it before any prose is
    shown, so an edit to any line of the section (a different text, an
    added or removed line, a re-ordering) invalidates the rendering."""
    return input_texts_digest([assertion.text for assertion in section.note_assertions])


def bound_rendering(note: GeneratedNote, section: GeneratedSection) -> StyleRendering | None:
    """The section's rendering — ``passed`` OR ``failed`` — when the note
    carries one whose ``input_digest`` is ``section_input_digest(section)``
    now; None otherwise. The prose stage asks this to know which sections
    still need the model (a bound ``failed`` verdict is an answer too: the
    same lines are never asked twice in one review)."""
    for rendering in note.style_renderings:
        if rendering.section_key != section.section_key:
            continue
        if rendering.input_digest != section_input_digest(section):
            return None
        return rendering
    return None


def usable_rendering(note: GeneratedNote, section: GeneratedSection) -> StyleRendering | None:
    """The section's prose rendering, or None when the note carries none for
    it, the verdict is ``failed`` (no prose — C4) or its ``input_digest``
    differs from ``section_input_digest(section)`` (stale — D7)."""
    rendering = bound_rendering(note, section)
    if rendering is None or rendering.verdict != "passed":
        return None
    return rendering


def note_input_digest(note: GeneratedNote) -> str:
    """ONE digest over everything the prose stage renders from — every
    populated section's key and ``section_input_digest`` in order — so a
    rendering job can be bound to the note it was started for and a result
    for a note that has since changed is recognised (Phase 4, D7)."""
    parts = [
        f"{section.section_key}\n{section_input_digest(section)}"
        for section in note.note_sections
        if section.note_assertions
    ]
    return text_digest("\n\n".join(parts))


def attach_style_renderings(
    note: GeneratedNote, renderings: Sequence[StyleRendering]
) -> GeneratedNote:
    """The note with ``renderings`` bound to its sections (Phase 4, D7): a
    rendering is kept ONLY when the note populates its section and its
    ``input_digest`` is that section's ``section_input_digest`` NOW — a
    stale rendering is dropped here, never carried into ``note.enc``; for
    one section the LAST rendering given wins (a caller passes the note's
    still-valid renderings first, then the stage's new ones). The
    ``style_fallback`` review warnings are DERIVED here from the kept
    ``failed`` renderings — one per section — replacing any the note held,
    so the note's warnings and its renderings cannot disagree (Check 5's
    verdict is carried by the failed rendering; ``note_check`` judges, this
    re-emits the carriage). The result is rebuilt through the full
    validators (the ``note.enc`` round trip), never an unvalidated copy."""
    sections = {section.section_key: section for section in note.note_sections}
    chosen: dict[NoteSectionKey, StyleRendering] = {}
    for rendering in renderings:
        section = sections.get(rendering.section_key)
        if section is None or rendering.input_digest != section_input_digest(section):
            continue
        chosen[rendering.section_key] = rendering
    kept = tuple(chosen[key] for key in CANONICAL_SECTION_KEYS if key in chosen)
    others = tuple(w for w in note.note_warnings if w.note_warning_code != "style_fallback")
    fallbacks = tuple(
        NoteWarning(
            note_warning_code="style_fallback",
            severity="review",
            section_key=rendering.section_key,
        )
        for rendering in kept
        if rendering.verdict == "failed"
    )
    updated = note.model_copy(
        update={"style_renderings": kept, "note_warnings": (*others, *fallbacks)}
    )
    return GeneratedNote.from_bytes(updated.to_bytes())


def _clean_lines(section: GeneratedSection, *, marked: bool) -> list[str]:
    """One terse line per assertion, in the note's order: the confirmed
    text exactly as confirmed — no substitution, no bullet, no provenance
    tag (the line editor keeps the per-line provenance; the tag is review
    apparatus, not clinical content). With ``marked`` a pre-filled line
    keeps its D5 mark."""
    lines: list[str] = []
    for assertion in section.note_assertions:
        text = assertion.text
        if marked and is_prefilled(assertion):
            text = f"{text}  [{PREFILLED_MARK}]"
        lines.append(text)
    return lines


def prefilled_section_mark(section: GeneratedSection) -> str | None:
    """D5's mark for a section rendered as PROSE (codex round 22 PR-MED-035):
    a pre-filled line no longer exists as a line inside a paragraph, so the
    prose block carries the mark at SECTION level — how many of its lines
    the practitioner's own config pre-filled — built from the same
    ``PREFILLED_MARK`` text; None when the section holds none. The line
    editor still names the lines themselves, and the counted Save label
    counts the same lines."""
    count = sum(1 for assertion in section.note_assertions if is_prefilled(assertion))
    if count == 0:
        return None
    noun = "line" if count == 1 else "lines"
    return f"[includes {count} {noun} {PREFILLED_MARK}]"


def render_section_lines(
    note: GeneratedNote, section: GeneratedSection, style: NoteStyle, *, apparatus: bool
) -> list[str]:
    """One section's body lines under ``style``, WITHOUT its title — the
    one per-section renderer behind both Copy (``render_note``) and the
    Cliniko draft write (cliniko-draft-write plan D7). Joining the lines
    with newlines gives the section's text; a prose rendering holding a
    newline gives several lines.

    With ``apparatus`` the lines are exactly what the Note tab shows:
    ``verbatim`` — each assertion as ONE bullet with its provenance tag
    (never assembled prose — assertions render on hard boundaries);
    ``clean`` — the confirmed text exactly as confirmed, one line per
    assertion, a pre-filled line keeping its D5 mark; the prose styles —
    the usable rendering (``usable_rendering``) followed by the section-level
    pre-filled mark, or else the section's ``clean`` lines.

    Without ``apparatus`` the lines are the bare clinical text: no bullet,
    tag or mark and no "[includes …]" line — ``verbatim`` renders as
    ``clean`` lines, and a prose style still falls back to ``clean`` per
    section exactly as above. Display text only, never logged here."""
    if style == "verbatim" and apparatus:
        return [
            f"  - {assertion.text}  [{assertion_label(assertion)}]"
            for assertion in section.note_assertions
        ]
    if style in ("own_voice", "narrative"):
        rendering = usable_rendering(note, section)
        if rendering is not None:
            lines = rendering.prose_text.split("\n")
            mark = prefilled_section_mark(section) if apparatus else None
            if mark is not None:
                lines.append(mark)
            return lines
    return _clean_lines(section, marked=apparatus)


def render_note(note: GeneratedNote, style: NoteStyle) -> str:
    """The note body under ``style`` — display text only, never logged here.

    Each section is its title — with a colon under ``verbatim``, without one
    otherwise — followed by ``render_section_lines(..., apparatus=True)``:
    ``verbatim`` the Phase 3A bullets unchanged, ``clean`` one terse line
    per assertion, ``own_voice`` / ``narrative`` per section the usable
    prose rendering or else that section's ``clean`` lines — so a note that
    carries no renderings (no language model — Phase 4) renders exactly as
    ``clean``. Sections are the note's own, already unique and in canonical
    order (``GeneratedNote`` validator); an empty note renders
    ``NO_NOTE_CONTENT``."""
    blocks: list[str] = []
    for section in note.note_sections:
        title = SECTION_TITLES[section.section_key]
        heading = f"{title}:" if style == "verbatim" else title
        lines = render_section_lines(note, section, style, apparatus=True)
        blocks.append("\n".join([heading, *lines]))
    if not blocks:
        return NO_NOTE_CONTENT
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# The provider seam.
#
# A ``NoteRequest`` has NO instruction, prompt, or system-message field, by
# construction: transcript content reaches a provider only inside
# ``transcript_utterances``, a pure data position. Spoken prompt injection
# therefore has no instruction position to reach in 3A, and 3B's model
# provider inherits the same request type.
# ---------------------------------------------------------------------------


class NoteProviderError(Exception):
    """A provider could not produce the requested output."""


class NoteUtterance(BaseModel):
    """One transcript segment as the provider sees it — words intact, so
    per-word ``probability`` stays reachable for the uncertainty obligation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    segment_index: int = Field(ge=0)
    speaker: str
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    transcript_words: tuple[TranscriptWord, ...] = ()

    @property
    def text(self) -> str:
        return reconstruct_span_text(self.transcript_words)


@final
class NoteRequest(BaseModel):
    """Everything a provider is given — transcript in a data position only.

    The TYPE stays importable for annotations (providers and Phase 6 name
    it), but CONSTRUCTION is not a public shipping API (rounds 11–13
    PR-MED-001): shipping source constructs only through
    ``note_config.build_note_request``, which re-establishes the
    profile/config relation at the boundary; raw assembly is
    ``_assemble_note_request`` below, whose only caller is that boundary.
    Enforcement is an AST guard test rather than the type — a pydantic
    model cannot refuse its own constructor or classmethods — and after
    round 13 the guard confines the REFERENCE, not a spelling list: any
    runtime use of this class as a value in any package module (including
    this one) is refused except the single pinned assembly call;
    annotation-only references stay legal, and ``@final`` additionally
    makes shipping subclasses a mypy-strict error
    (``test_note_config.TestConstructionGuard``). Escape hatches reached
    through a value variable, ``getattr``-by-string, or monkey-patching are
    statically invisible and sit outside the threat model. Test fixtures
    construct directly on purpose; the fixture matrix needs raw requests.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    session_id: str = Field(pattern=SESSION_ID_PATTERN)
    template_profile_id: str = Field(pattern=_PROFILE_ID_PATTERN)
    clinician_speaker: str | None = None
    transcript_digest: str
    config_digest: str
    section_keys: tuple[NoteSectionKey, ...] = CANONICAL_SECTION_KEYS
    transcript_utterances: tuple[NoteUtterance, ...] = ()

    @model_validator(mode="after")
    def _check_request(self) -> Self:
        for label, value in (
            ("transcript_digest", self.transcript_digest),
            ("config_digest", self.config_digest),
        ):
            if not _DIGEST_RE.match(value):
                raise ValueError(f"{label} must match {DIGEST_PATTERN}")
        if not self.section_keys:
            raise ValueError("section_keys must not be empty")
        previous = -1
        for utterance in self.transcript_utterances:
            if utterance.segment_index <= previous:
                raise ValueError("transcript_utterances must be in strict segment order")
            previous = utterance.segment_index
        return self

    def words_for_coords(self, coords: SourceCoords) -> tuple[TranscriptWord, ...] | None:
        """The words a span's coordinates address, or None when unresolvable.

        Coordinates address the SEGMENT INDEX of the immutable transcript,
        not a position in this tuple, so a filtered request still resolves
        correctly.
        """
        for utterance in self.transcript_utterances:
            if utterance.segment_index != coords.segment_index:
                continue
            words = utterance.transcript_words
            if coords.last_word_index >= len(words):
                return None
            return words[coords.first_word_index : coords.last_word_index + 1]
        return None


def _assemble_note_request(
    document: TranscriptDocument,
    *,
    template_profile_id: str,
    config_digest: str,
    clinician_speaker: str | None = None,
    section_keys: tuple[NoteSectionKey, ...] = CANONICAL_SECTION_KEYS,
) -> NoteRequest:
    """RAW assembly of the provider request from a transcript artifact.

    Package-private on purpose (rounds 10–13 PR-MED-001): the id/digest
    strings here are unresolved, so this is not a generation-facing API.
    Generation constructs through ``note_config.build_note_request``, which
    accepts the source ``NoteConfig`` plus the selected id and re-establishes
    the binding itself — canonicalise, bind, derive — before delegating
    here. (``note_config`` imports this function; the boundary lives there
    because the reverse import would be a cycle. The AST guard confines
    every other runtime reference to this symbol.)

    Transcript content lands ONLY in ``transcript_utterances``. Nothing a
    speaker said can reach an instruction position, because the request
    type has none.
    """
    utterances = tuple(
        NoteUtterance(
            segment_index=index,
            speaker=segment.speaker,
            start_seconds=segment.start_seconds,
            end_seconds=segment.end_seconds,
            transcript_words=segment.transcript_words,
        )
        for index, segment in enumerate(document.transcript_segments)
    )
    return NoteRequest(
        session_id=document.session_id,
        template_profile_id=template_profile_id,
        clinician_speaker=clinician_speaker,
        transcript_digest=transcript_digest(document),
        config_digest=config_digest,
        section_keys=section_keys,
        transcript_utterances=utterances,
    )


class NoteModelProvider(Protocol):
    """PLAN.md core type: transcript -> canonical sections, entirely local.

    3A ships ``ExtractiveNoteProvider``; 3B swaps in local ``gpt-oss-20b``
    behind this same seam with no pipeline change.
    """

    @property
    def provider_name(self) -> str:
        ...

    def generate_sections(self, request: NoteRequest) -> tuple[GeneratedSection, ...]:
        ...


# ---------------------------------------------------------------------------
# ExtractiveNoteProvider — the phase's shipping default (no LLM).
# ---------------------------------------------------------------------------

# Shipped config defaults are package data under ``scribe_desktop/config_defaults/``
# (Phase 3A Task 3.3), read through ``importlib.resources`` so a wheel install
# resolves them exactly as the dev checkout does. The directory name and the
# cue file's name are single-sourced HERE because ``note_config`` — the module
# that owns the other three filenames and the loader — imports this one.
_DEFAULTS_RESOURCE_DIR: Final = "config_defaults"
SECTION_CUES_FILENAME: Final = "section_cues.json"

# Cue phrases per canonical section. Since the practitioner-profile plan's
# Phase 4 the ONE source is the packaged ``config_defaults/section_cues.json``
# — the very file ``note_config.load_note_config`` reads as the shipped
# default of the fourth clinician config file — so these defaults and the
# loader's first-run result cannot drift apart. A practitioner's own file
# replaces the shipped one whole (D6) and enters the config digest (D7); the
# provider the app builds takes its cues FROM the loaded config
# (``ui.models.build_note_generator``), and ``DEFAULT_SECTION_CUES`` is what
# a bare ``ExtractiveNoteProvider()`` falls back to. The shipped phrases are a
# FIRST CUT authored against the fixture matrix and ordinary physiotherapy
# vocabulary, NOT clinical evidence — the honesty note ``note_check`` shares.
# Phrases are normalised through ``content_tokens`` at import so cue matching
# and every other tokenisation share one rule. Routing takes the FIRST
# canonical section whose cue matches, so the order of evaluation is the
# request's canonical section order, not the file's.
#
# The read below checks SHAPE and COMPLETENESS, nothing more: a package-data
# read of a file this checkout ships, refused loudly at import
# (``RuntimeError`` — a broken install, not a runtime state) when the payload
# is not an object of canonical keys to lists of strings, when any canonical
# key is missing, or when any list is empty (peer round 32 PR-HIGH-007: an
# emptied-but-valid-JSON package would otherwise import as a zero-cue default
# and route nothing while every status line read healthy). Completeness is a
# rule for the PACKAGED default only — a user override may be sparse or
# empty under D6, and that is the loader's contract, not this one's. Every
# CONTENT rule — blank text, control characters, a phrase with no content
# tokens, a duplicate within or across sections — is
# ``note_config.SectionCuesFile``'s, and the shipped file is validated against
# that model by test; the model cannot live here because ``note_config``
# imports this module.
_SECTION_KEYS_BY_NAME: Final[dict[str, NoteSectionKey]] = {
    key: key for key in CANONICAL_SECTION_KEYS
}


def _parse_shipped_section_cues(
    payload: object,
) -> tuple[tuple[NoteSectionKey, tuple[str, ...]], ...]:
    """The packaged default's shape + completeness rule (comment above),
    over an already-decoded payload so a test can drive every refusal
    without touching the packaged file."""
    cues = payload.get("section_cues") if isinstance(payload, dict) else None
    if not isinstance(cues, dict):
        raise RuntimeError(
            f"shipped {SECTION_CUES_FILENAME} is malformed (broken install): "
            "no section_cues object"
        )
    loaded: list[tuple[NoteSectionKey, tuple[str, ...]]] = []
    for name, phrases in cues.items():
        key = _SECTION_KEYS_BY_NAME.get(name)
        if key is None or not isinstance(phrases, list):
            raise RuntimeError(
                f"shipped {SECTION_CUES_FILENAME} is malformed (broken install): "
                f"section {name!r}"
            )
        if not phrases:
            raise RuntimeError(
                f"shipped {SECTION_CUES_FILENAME} is incomplete (broken install): "
                f"no phrases under {name!r}"
            )
        if not all(isinstance(phrase, str) for phrase in phrases):
            raise RuntimeError(
                f"shipped {SECTION_CUES_FILENAME} is malformed (broken install): "
                f"a non-string phrase under {name!r}"
            )
        loaded.append((key, tuple(phrases)))
    missing = [key for key in CANONICAL_SECTION_KEYS if key not in cues]
    if missing:
        raise RuntimeError(
            f"shipped {SECTION_CUES_FILENAME} is incomplete (broken install): "
            f"no cues for {', '.join(missing)}"
        )
    return tuple(loaded)


def _load_shipped_section_cues() -> tuple[tuple[NoteSectionKey, tuple[str, ...]], ...]:
    resource = resources.files("scribe_desktop") / _DEFAULTS_RESOURCE_DIR / SECTION_CUES_FILENAME
    try:
        payload = json.loads(resource.read_bytes())
    except (OSError, ValueError) as exc:
        raise RuntimeError(
            f"shipped {SECTION_CUES_FILENAME} unreadable (broken install): {exc}"
        ) from exc
    return _parse_shipped_section_cues(payload)


_RAW_SECTION_CUES: Final[tuple[tuple[NoteSectionKey, tuple[str, ...]], ...]] = (
    _load_shipped_section_cues()
)

DEFAULT_SECTION_CUES: Final[Mapping[NoteSectionKey, tuple[tuple[str, ...], ...]]] = {
    key: tuple(content_tokens(phrase) for phrase in phrases) for key, phrases in _RAW_SECTION_CUES
}

# A clinician's QUESTION is not a diagnosis (plan Task 2.2): interrogative
# utterances never populate a clinician-owned section. A trailing "?" is the
# primary signal; the opener rules are the backstop for a transcript that
# lost it.
#
# Auxiliaries are split from WH-words DELIBERATELY (round 1 MED-001): in a
# consultation "do", "have" and "can" open imperatives at least as often as
# questions — "Do your home exercise programme twice a day", "Have a look at
# the stretch sheet" — and treating those as questions dropped real clinician
# advice out of the note entirely. An auxiliary counts only when a pronoun
# subject follows it.
_WH_OPENERS: Final[frozenset[str]] = frozenset(
    {"what", "when", "where", "which", "who", "whom", "whose", "why", "how"}
)
_AUX_OPENERS: Final[frozenset[str]] = frozenset(
    {
        "is", "are", "am", "was", "were", "do", "does", "did", "can", "could",
        "will", "would", "shall", "should", "may", "might", "have", "has", "had",
    }
)
_SUBJECT_TOKENS: Final[frozenset[str]] = frozenset(
    {"you", "we", "i", "he", "she", "they", "it", "there", "that", "this"}
)


def _contains_phrase(tokens: Sequence[str], phrase: Sequence[str]) -> bool:
    """True when ``phrase`` occurs as a contiguous run inside ``tokens``."""
    if not phrase or len(phrase) > len(tokens):
        return False
    span = len(phrase)
    return any(
        tuple(tokens[start : start + span]) == tuple(phrase)
        for start in range(len(tokens) - span + 1)
    )


def is_interrogative(text: str) -> bool:
    """Question heuristic: a trailing '?', a WH-opener, or an auxiliary
    opener followed by a pronoun subject ("do you", "have you", "can we")."""
    if text.rstrip().endswith("?"):
        return True
    tokens = content_tokens(text)
    if not tokens:
        return False
    if tokens[0] in _WH_OPENERS:
        return True
    return tokens[0] in _AUX_OPENERS and len(tokens) > 1 and tokens[1] in _SUBJECT_TOKENS


# ---------------------------------------------------------------------------
# THE ownership rule and the first-match routing it gates (practitioner-
# profile plan Task 5.1): one implementation shared by
# ``ExtractiveNoteProvider._route`` and the Note tab's review edits, so an
# added or moved line can never land where routing would have refused it.
# ---------------------------------------------------------------------------


def spoken_by_confirmed_clinician(speaker: str, clinician_speaker: str | None) -> bool:
    """True when ``speaker`` IS the confirmed clinician cluster. With no
    confirmed role (``None``) nothing is the clinician's — the Critical
    Constraint that leaves clinician-owned sections blank. The phrase learner
    (practitioner-profile plan D9 as amended) uses this same test, so a line
    another speaker said can never reach it."""
    return clinician_speaker is not None and speaker == clinician_speaker


def section_admits_utterance(
    section_key: NoteSectionKey,
    *,
    speaker: str,
    clinician_speaker: str | None,
    question: bool,
) -> bool:
    """The ownership rule: a clinician-owned section admits only the
    confirmed clinician's NON-question utterances; every other section admits
    any utterance."""
    if section_key not in CLINICIAN_OWNED_SECTIONS:
        return True
    return spoken_by_confirmed_clinician(speaker, clinician_speaker) and not question


def admissible_sections(
    section_keys: Sequence[NoteSectionKey],
    *,
    speaker: str,
    clinician_speaker: str | None,
    text: str,
) -> tuple[NoteSectionKey, ...]:
    """The sections (in the given order) an utterance may enter under the
    ownership rule — the Note tab's section chooser for an add or a move."""
    question = is_interrogative(text)
    return tuple(
        key
        for key in section_keys
        if section_admits_utterance(
            key, speaker=speaker, clinician_speaker=clinician_speaker, question=question
        )
    )


def first_matching_section(
    cues: Mapping[NoteSectionKey, tuple[tuple[str, ...], ...]],
    tokens: Sequence[str],
    section_keys: Sequence[NoteSectionKey],
    *,
    speaker: str,
    clinician_speaker: str | None,
    question: bool,
) -> NoteSectionKey | None:
    """First-match routing: the first admissible section (in ``section_keys``
    order) one of whose cues occurs as a contiguous run in ``tokens``, or
    None. The provider routes with it; the learner dry-runs a proposed cue set
    through it to say when an earlier section would still win."""
    if not tokens:
        return None
    for key in section_keys:
        if not section_admits_utterance(
            key, speaker=speaker, clinician_speaker=clinician_speaker, question=question
        ):
            continue
        if any(_contains_phrase(tokens, phrase) for phrase in cues.get(key, ())):
            return key
    return None


def provider_assertion_id(segment_index: int) -> str:
    """The extractive provider's id for the utterance at ``segment_index``."""
    return f"x{segment_index:04d}"


def manual_assertion_id(segment_index: int) -> str:
    """The id of a line the clinician ADDED during review (practitioner-profile
    plan D14) — a scheme distinct from the provider's, so the two can never
    collide in one note and a review edit is recognisable by its id."""
    return f"m{segment_index:04d}"


def whole_utterance_assertion(
    assertion_id: str,
    section_key: NoteSectionKey,
    *,
    segment_index: int,
    speaker: str,
    words: Sequence[TranscriptWord],
) -> NoteAssertion | None:
    """One whole utterance as a ``transcript`` assertion with contiguous
    coordinates over every word, built with the same reconstruction rule
    Check 1 rebuilds by — so it reconstructs byte-identically. None for an
    utterance with no words or no text once stripped (nothing to quote)."""
    if not words:
        return None
    text = reconstruct_span_text(words)
    if not text:
        return None
    return NoteAssertion(
        assertion_id=assertion_id,
        section_key=section_key,
        speaker=speaker,
        note_span=NoteSpan(
            span_text=text,
            provenance="transcript",
            source_coords=SourceCoords(segment_index, 0, len(words) - 1),
        ),
    )


# ---------------------------------------------------------------------------
# Role PRESELECTION (plan Task 2.2) — a DEFAULT for the mandatory confirmation
# in Task 7.5, never an authority.
#
# The Critical Constraint this sits next to is that the clinician-owned
# sections (`assessment`, `diagnosis`, `advice_home_exercise`,
# `management_plan`) populate ONLY from confirmed-clinician utterances, and
# that an unresolved or merged clustering leaves them blank rather than
# guessing. Nothing here can weaken that: it is enforced one layer down by
# ``ExtractiveNoteProvider._route``, which refuses those sections outright
# whenever ``NoteRequest.clinician_speaker`` is None.
#
# What keeps this a preselection rather than an authority is the RETURN TYPE.
# ``speaker_role`` hands back a ``SpeakerRolePreselection``, not the ``str``
# that ``clinician_speaker`` accepts, so reaching the label costs an explicit
# ``.preselected_clinician_speaker`` — visible at the call site, and not
# something mypy strict lets a caller skip past. Task 7.5 owns the control
# that turns a preselection into a confirmed role; no pipeline code may feed
# this result straight into ``note_config.build_note_request``.
# ---------------------------------------------------------------------------

# Descending order of trust. The weights are a first cut authored against
# consultation structure, NOT against measured data — Task 2.3 measures role
# accuracy on labelled human recordings and is what confirms or reverses them.
_ROLE_QUESTION_WEIGHT: Final = 0.60
_ROLE_FIRST_SPEAKER_WEIGHT: Final = 0.25
_ROLE_TALK_TIME_WEIGHT: Final = 0.15
# Additive smoothing on the question rate: one interrogative utterance is a
# 100% rate, and without damping a speaker who said a single sentence would
# outrank a clinician who asked eight questions in twelve turns.
_ROLE_QUESTION_SMOOTHING: Final = 1.0
# Float-noise tolerance on the winning margin, NOT a confidence threshold.
# Two clusters that are genuinely tied can miss exact equality by an ulp or
# two once the weights are summed, and a preselection decided by float dust
# is a coin flip wearing a number. There is deliberately no "too close to
# call" threshold above this: what a real one should be is a question about
# measured accuracy, which is Task 2.3's to answer.
_ROLE_TIE_EPSILON: Final = 1e-9


class SpeakerEvidence(NamedTuple):
    """Per-speaker signals behind a preselection — COUNTS AND SECONDS ONLY.

    Deliberately carries no transcript text. A role preselection is exactly
    the kind of value a UI renders and a diagnostic logs, and the Critical
    Constraint keeps clinical content out of logs. Candidate QUOTATIONS for
    the Task 7.5 confirmation control are absent for the same reason — that
    screen already holds the transcript and can quote from it directly.

    ``question_rate`` is the RAW rate a human would check (``question_count``
    over ``utterance_count``). Scoring uses a smoothed rate instead; see
    ``speaker_role``.
    """

    speaker: str
    speech_seconds: float
    talk_time_share: float
    utterance_count: int
    question_count: int
    question_rate: float
    spoke_first: bool
    score: float


class SpeakerRolePreselection(NamedTuple):
    """A proposed clinician cluster plus the evidence for it.

    ``preselected_clinician_speaker`` is None when no preselection is
    possible: an empty transcript, a MERGED clustering with a single speaker
    label (there is no second cluster to choose against), or a tie between
    the top two — a tie meaning within ``_ROLE_TIE_EPSILON``, not exact
    equality.
    ``margin`` is the winner's score less the runner-up's — Task 7.5 decides
    how to present a weak one; it is NOT a threshold this function applies.
    """

    preselected_clinician_speaker: str | None
    margin: float
    speaker_evidence: tuple[SpeakerEvidence, ...]


def speaker_role(document: TranscriptDocument) -> SpeakerRolePreselection:
    """Preselect which diarization cluster is the clinician. Pure function.

    Three signals, in descending order of how far they are trusted:

    - **Question-asking rate** (0.60). Clinicians ask, patients answer. This
      is the signal most specific to the role, so it carries the most weight.
      Smoothed as ``questions / (utterances + 1)`` for the reason recorded on
      ``_ROLE_QUESTION_SMOOTHING``.
    - **First speaker** (0.25). The practitioner starts the recording and
      usually opens the consultation.
    - **Talk-time share** (0.15). The weakest, and the only one whose
      DIRECTION is an assumption rather than an observation: history-taking
      means the patient talks more, while explanation and exercise
      instruction mean the clinician does. Weighted to break near-ties, not
      to decide, and flagged for Task 2.3 to confirm or reverse.

    Segments that transcribed to no text are excluded from both signals, so
    the two rates are measured over the same population of utterances rather
    than one counting turns the other cannot see.
    """
    speech_seconds: dict[str, float] = {}
    utterance_count: dict[str, int] = {}
    question_count: dict[str, int] = {}
    first_speaker: str | None = None
    first_start: float | None = None

    for segment in document.transcript_segments:
        text = reconstruct_span_text(segment.transcript_words)
        if not text:
            continue
        speaker = segment.speaker
        speech_seconds[speaker] = speech_seconds.get(speaker, 0.0) + max(
            segment.end_seconds - segment.start_seconds, 0.0
        )
        utterance_count[speaker] = utterance_count.get(speaker, 0) + 1
        question_count[speaker] = question_count.get(speaker, 0) + int(
            is_interrogative(text)
        )
        if first_start is None or segment.start_seconds < first_start:
            first_start = segment.start_seconds
            first_speaker = speaker

    total_seconds = sum(speech_seconds.values())
    evidence: list[SpeakerEvidence] = []
    for speaker in sorted(utterance_count):
        utterances = utterance_count[speaker]
        questions = question_count[speaker]
        share = speech_seconds[speaker] / total_seconds if total_seconds > 0 else 0.0
        spoke_first = speaker == first_speaker
        score = (
            _ROLE_QUESTION_WEIGHT * (questions / (utterances + _ROLE_QUESTION_SMOOTHING))
            + _ROLE_FIRST_SPEAKER_WEIGHT * float(spoke_first)
            + _ROLE_TALK_TIME_WEIGHT * share
        )
        evidence.append(
            SpeakerEvidence(
                speaker=speaker,
                speech_seconds=speech_seconds[speaker],
                talk_time_share=share,
                utterance_count=utterances,
                question_count=questions,
                question_rate=questions / utterances,
                spoke_first=spoke_first,
                score=score,
            )
        )

    if len(evidence) < 2:
        # No transcript, or a merged cluster: there is no second cluster to
        # choose against, so there is nothing to preselect.
        return SpeakerRolePreselection(None, 0.0, tuple(evidence))
    ranked = sorted(evidence, key=lambda candidate: candidate.score, reverse=True)
    margin = ranked[0].score - ranked[1].score
    if margin <= _ROLE_TIE_EPSILON:
        return SpeakerRolePreselection(None, margin, tuple(evidence))
    return SpeakerRolePreselection(ranked[0].speaker, margin, tuple(evidence))


class ExtractiveNoteProvider:
    """Cue-matched VERBATIM transcript spans — no generation, no paraphrase.

    Every emitted assertion is one whole utterance quoted exactly, carrying
    that utterance's contiguous coordinates, so Check 1 reconstructs it
    byte-identically. Clinician-owned sections are populated only from
    utterances spoken by the CONFIRMED clinician cluster and never from a
    question; with no confirmed role they stay blank (Critical Constraint).
    """

    def __init__(
        self,
        cues: Mapping[NoteSectionKey, tuple[tuple[str, ...], ...]] = DEFAULT_SECTION_CUES,
    ) -> None:
        self._cues = cues

    @property
    def provider_name(self) -> str:
        return "extractive-v1"

    def _route(self, request: NoteRequest, utterance: NoteUtterance) -> NoteSectionKey | None:
        return first_matching_section(
            self._cues,
            content_tokens(utterance.text),
            request.section_keys,
            speaker=utterance.speaker,
            clinician_speaker=request.clinician_speaker,
            question=is_interrogative(utterance.text),
        )

    def generate_sections(self, request: NoteRequest) -> tuple[GeneratedSection, ...]:
        routed: dict[NoteSectionKey, list[NoteAssertion]] = {}
        for utterance in request.transcript_utterances:
            words = utterance.transcript_words
            if not words:
                continue
            key = self._route(request, utterance)
            if key is None:
                continue
            assertion = whole_utterance_assertion(
                provider_assertion_id(utterance.segment_index),
                key,
                segment_index=utterance.segment_index,
                speaker=utterance.speaker,
                words=words,
            )
            if assertion is None:
                continue
            routed.setdefault(key, []).append(assertion)
        return tuple(
            GeneratedSection(section_key=key, note_assertions=tuple(routed[key]))
            for key in CANONICAL_SECTION_KEYS
            if key in routed
        )


# ---------------------------------------------------------------------------
# MockNoteModelProvider — the deterministic adversarial instrument (Axis B).
#
# It fabricates ON PURPOSE. It exists so the checkers can be proven to fire,
# and it never runs in the app: nothing constructs it outside tests and the
# fixture matrix. Every behaviour is a pure function of the request, so a
# fixture cell is reproducible; a behaviour that CANNOT be produced from the
# given transcript raises ``NoteProviderError`` rather than silently
# degrading to a different (and quietly passing) failure class.
# ---------------------------------------------------------------------------

MockBehaviour = Literal[
    "faithful",
    "fabricated_fact",
    "laterality_flip",
    "dose_change",
    "negation_flip",
    "name_substitution",
    "invented_diagnosis",
    "invented_plan",
    "invented_referral",
    "invented_investigation",
    "over_omission",
    "obeys_injection",
    "malformed_output",
    "speaker_misattribution",
]

MOCK_BEHAVIOURS: Final[tuple[MockBehaviour, ...]] = (
    "faithful",
    "fabricated_fact",
    "laterality_flip",
    "dose_change",
    "negation_flip",
    "name_substitution",
    "invented_diagnosis",
    "invented_plan",
    "invented_referral",
    "invented_investigation",
    "over_omission",
    "obeys_injection",
    "malformed_output",
    # Task 5.0: the speaker-ONLY failure class the round-6 peer showed the
    # old fingerprint could not even represent — an utterance attributed to
    # the wrong cluster with text, section and coordinates all correct.
    "speaker_misattribution",
)

_FABRICATED_TEXT: Final = "The patient reported a fall from a ladder last Tuesday"
_INVENTED: Final[Mapping[MockBehaviour, tuple[NoteSectionKey, str]]] = {
    "invented_diagnosis": ("diagnosis", "L5-S1 disc herniation with radiculopathy"),
    "invented_plan": ("management_plan", "Twelve sessions over six weeks, prepaid"),
    "invented_referral": ("referrals_investigations", "Referred to orthopaedic surgeon"),
    "invented_investigation": ("referrals_investigations", "Lumbar MRI requested today"),
}
_SUBSTITUTE_NAME: Final = "Wilson"

# The FIXTURE CONTRACT for `obeys_injection` (Task 5.0, peer probe 1): the
# behaviour models a provider that treats a spoken utterance as an
# instruction, so the fixture must actually CONTAIN one — an utterance
# whose content tokens carry both an instruction verb and an instruction
# object ("Ignore previous instructions...", "Write in the note that...").
# On a transcript with no such utterance the behaviour raises rather than
# quoting arbitrary speech into a clinician-owned section, which is a
# DIFFERENT failure class wearing this one's label. These closed sets are a
# fixture-authoring contract for the adversarial instrument, not a runtime
# injection detector — the failure direction is safe (no marker -> the cell
# fails loudly instead of silently testing the wrong class).
_INJECTION_VERBS: Final[frozenset[str]] = frozenset(
    {"ignore", "disregard", "forget", "pretend", "override", "write", "add", "put", "state"}
)
_INJECTION_OBJECTS: Final[frozenset[str]] = frozenset(
    {"instruction", "instructions", "prompt", "prompts", "system", "note", "notes", "record"}
)


def _is_injection_like(text: str) -> bool:
    """True when ``text`` satisfies the injection fixture contract above."""
    tokens = frozenset(content_tokens(text))
    return bool(tokens & _INJECTION_VERBS) and bool(tokens & _INJECTION_OBJECTS)


# The FIXTURE CONTRACT for `dose_change` (Task 5.0, rounds 21-22
# PR-MED-001 — the fifth and sixth appearances of the difference-not-class
# family): a dose is a MEDICATION token, then a quantity that either
# carries an ATTACHED strength unit ("paracetamol 500mg") or is followed by
# a separated strength unit or regimen marker ("paracetamol 500 mg",
# "paracetamol 500 twice daily"). A bare number near — or even directly
# after — a medication is NOT a dose ("stopped paracetamol 2 days ago" is a
# time interval), a pain score, duration or date is not one either, and a
# COUNT quantity is not one at all ("2 tablets remaining" is stock — round
# 22 removed the tablet/capsule words from the marker set because a
# prescribed count and an inventory count are mechanically inseparable, so
# count fixtures fail toward the loud raise). Like the injection sets
# above, these are closed instrument vocabularies for AUTHORING fixtures,
# not a runtime classifier: the failure direction is safe — a fixture
# outside the contract makes the behaviour raise loudly instead of
# silently exercising the wrong class. ("daily" is a marker; "days"
# deliberately is not.)
_DOSE_MEDICATIONS: Final[frozenset[str]] = frozenset(
    {
        "paracetamol", "panadol", "ibuprofen", "nurofen", "aspirin",
        "naproxen", "diclofenac", "voltaren", "codeine", "tramadol",
    }
)
_DOSE_MARKERS: Final[frozenset[str]] = frozenset(
    {
        "mg", "milligram", "milligrams", "mcg", "g", "gram", "grams", "ml",
        "twice", "daily", "nightly", "hourly", "weekly",
    }
)
_ATTACHED_STRENGTH_RE: Final = re.compile(r"^\d+(?:\.\d+)?(?:mg|mcg|g|ml)$")


def _same_statement(left: str, right: str) -> bool:
    """True when two texts are the SAME clinical statement for the mock's
    purposes — equal under the module's one shared normalisation.

    THE semantic predicate for "did this behaviour actually produce its named
    failure class?", asked identically at every site. Punctuation, case and
    whitespace are not Axis B failure classes, so a change confined to them
    has produced nothing, however byte-different it serializes (round 5
    PR-MED-001: `"...last Tuesday."` -> `"...last Tuesday"` counted as a
    fabrication, and `"Wilson,"` -> `"Wilson"` as a name substitution).
    """
    return content_tokens(left) == content_tokens(right)


_MUTATION_REQUIREMENT: Final[Mapping[str, str]] = {
    "laterality_flip": "a left/right token",
    "dose_change": (
        "a medication-anchored dose (a strength unit attached to the "
        "quantity, or a separated unit/regimen marker) whose quantity "
        "changes when doubled"
    ),
    "negation_flip": "a negation token",
    "name_substitution": f"a name-like token other than {_SUBSTITUTE_NAME}",
}
_NEGATIONS: Final[frozenset[str]] = frozenset({"not", "no", "never", "denies", "denied", "without"})
_LATERALITY: Final[Mapping[str, str]] = {"left": "right", "right": "left"}
_DIGITS_RE: Final = re.compile(r"\d+")


class MockNoteModelProvider:
    """Deterministic, ML-free ``NoteModelProvider`` producing one Axis B
    behaviour per instance (mirrors ``speech.MockSpeechProvider``)."""

    def __init__(self, behaviour: MockBehaviour = "faithful") -> None:
        if behaviour not in MOCK_BEHAVIOURS:
            raise ValueError(f"unknown behaviour: {behaviour}")
        self._behaviour: MockBehaviour = behaviour

    @property
    def provider_name(self) -> str:
        return f"mock-{self._behaviour}"

    @property
    def behaviour(self) -> MockBehaviour:
        return self._behaviour

    def _base_key(self, request: NoteRequest, utterance: NoteUtterance) -> NoteSectionKey:
        """Speaker-driven routing: no cue matching, so a fixture's expected
        output stays a property of the fixture, not of the cue table."""
        if (
            request.clinician_speaker is not None
            and utterance.speaker == request.clinician_speaker
        ):
            return "objective_examination"
        return "presenting_complaint"

    def generate_sections(self, request: NoteRequest) -> tuple[GeneratedSection, ...]:
        assertions = self._base_assertions(request)
        faithful = self._as_sections(assertions)
        if self._behaviour == "faithful":
            return faithful
        if self._behaviour == "malformed_output":
            assertions = [self._malformed_assertion(request)]
        elif self._behaviour == "over_omission":
            if len(assertions) < 2:
                # Same loud-failure rule as the mutations: with nothing to
                # omit this behaviour is byte-identical to `faithful`, and a
                # fixture cell would pass while testing nothing (round 1
                # LOW-001).
                raise NoteProviderError("over_omission needs more than one utterance")
            assertions = assertions[:1]
        elif self._behaviour == "fabricated_fact":
            assertions = self._fabricate(assertions)
        elif self._behaviour in _INVENTED:
            assertions = [*assertions, self._invented_assertion(request)]
        elif self._behaviour == "obeys_injection":
            assertions = [*assertions, self._injected_assertion(request)]
        elif self._behaviour == "speaker_misattribution":
            assertions = self._misattribute_speaker(request, assertions)
        else:
            assertions = self._mutate(assertions)
        sections = self._as_sections(assertions)
        # THE structural backstop, and the reason this class should now be
        # closed: every behaviour above must leave a semantically different
        # result, and a behaviour that did not says so LOUDLY here rather
        # than returning faithful output under an adversarial label. Any
        # behaviour a later phase adds inherits this by construction — the
        # guarantee lives at the one exit, not in N branches.
        if self._fingerprint(sections) == self._fingerprint(faithful):
            raise NoteProviderError(
                f"{self._behaviour} produced output that is not distinguishable from faithful"
            )
        return sections

    def _fingerprint(
        self, sections: tuple[GeneratedSection, ...]
    ) -> tuple[tuple[str, tuple[str, ...], SourceCoords | None, str | None], ...]:
        """What makes two mock outputs the same ADVERSARIAL result: which
        section, which statement, which coordinates were cited, and which
        SPEAKER the assertion is attributed to.

        Blind to punctuation and case (not failure classes) and deliberately
        SENSITIVE to `source_coords`, because a correctly-worded assertion
        citing the wrong interval is a genuine failure class a future
        behaviour may want to produce. ``speaker`` joined the projection with
        Task 5.0: without it, `speaker_misattribution` — a real Axis B class
        whose ONLY difference is the attributed cluster — would be wrongly
        REJECTED at the single exit as indistinguishable from faithful (the
        round-6 peer's gap, recorded on Task 5.0).
        """
        return tuple(
            (
                assertion.section_key,
                content_tokens(assertion.text),
                assertion.note_span.source_coords,
                assertion.speaker,
            )
            for section in sections
            for assertion in section.note_assertions
        )

    # -- helpers ---------------------------------------------------------

    def _base_assertions(self, request: NoteRequest) -> list[NoteAssertion]:
        assertions: list[NoteAssertion] = []
        for utterance in request.transcript_utterances:
            words = utterance.transcript_words
            text = reconstruct_span_text(words)
            if not words or not text:
                continue
            assertions.append(
                NoteAssertion(
                    assertion_id=f"m{utterance.segment_index:04d}",
                    section_key=self._base_key(request, utterance),
                    speaker=utterance.speaker,
                    note_span=NoteSpan(
                        span_text=text,
                        provenance="transcript",
                        source_coords=SourceCoords(utterance.segment_index, 0, len(words) - 1),
                    ),
                )
            )
        if not assertions:
            raise NoteProviderError("the transcript has no usable utterance")
        return assertions

    def _retext(self, assertion: NoteAssertion, text: str) -> NoteAssertion:
        """Same coordinates, different text — Check 1's reconstruction fails.

        FRESH VALIDATING construction, not ``model_copy`` (Task 5.0, peer
        probe 2): ``model_copy`` skips validators, so a mutator that emitted
        empty text shipped a structurally INVALID span under an adversarial
        label — different from faithful for the wrong reason. Rebuilding
        through the real constructors makes any future mutator's invalid
        output die loudly here instead.
        """
        return NoteAssertion.model_validate(
            {
                **assertion.model_dump(),
                "note_span": {**assertion.note_span.model_dump(), "span_text": text},
            }
        )

    def _fabricate(self, assertions: list[NoteAssertion]) -> list[NoteAssertion]:
        """Replace the first assertion the fabrication would actually change.

        A transcript already equal to `_FABRICATED_TEXT` made this behaviour a
        no-op returning faithful output (round 4 PR-MED-002); raising is the
        honest outcome when no utterance differs from the fabricated sentence.
        """
        for index, assertion in enumerate(assertions):
            if _same_statement(assertion.text, _FABRICATED_TEXT):
                continue
            return [
                *assertions[:index],
                self._retext(assertion, _FABRICATED_TEXT),
                *assertions[index + 1 :],
            ]
        raise NoteProviderError("no utterance differs from the fabricated sentence")

    def _mutate(self, assertions: list[NoteAssertion]) -> list[NoteAssertion]:
        """Mutate the FIRST assertion that can carry this behaviour's failure
        class, and raise only when NO utterance can express it. Scanning just
        the first assertion made a fixture whose target token sat further down
        fail with a message blaming the whole transcript (round 1 LOW-002)."""
        mutator = {
            "laterality_flip": self._flip_laterality,
            "dose_change": self._change_dose,
            "negation_flip": self._flip_negation,
            "name_substitution": self._substitute_name,
        }[self._behaviour]
        for index, assertion in enumerate(assertions):
            mutated = mutator(assertion.text.split())
            if mutated is None:
                continue
            text = " ".join(mutated)
            # The choke point, now SEMANTIC (round 4 PR-MED-002, widened by
            # round 5 PR-MED-001): a mutation that changed nothing — or
            # changed only punctuation, case or spacing — is not a mutation,
            # so the scan continues to a later utterance that can carry the
            # class instead of stopping on a cosmetic difference.
            if _same_statement(text, assertion.text):
                continue
            # Task 5.0 (peer probe 2): a mutation that ERASED the utterance
            # ("No." minus its negation) has not expressed the class either —
            # it would ship an invalid empty span, not a flipped statement.
            # The scan continues; `_retext`'s validating construction is the
            # backstop for any other invalid shape.
            if not text.strip():
                continue
            return [
                *assertions[:index],
                self._retext(assertion, text),
                *assertions[index + 1 :],
            ]
        raise NoteProviderError(
            f"no utterance contains {_MUTATION_REQUIREMENT[self._behaviour]}"
        )

    def _flip_laterality(self, tokens: list[str]) -> list[str] | None:
        for index, token in enumerate(tokens):
            core = normalise_token(token)
            flipped = _LATERALITY.get(core)
            if flipped is not None:
                # Splice the core case-INSENSITIVELY, keeping any surrounding
                # punctuation. Matching the lowercased core against the raw
                # token silently no-opped on "Left", and Whisper capitalises
                # every segment-initial word — so the mutation vanished in the
                # common case and the Axis B laterality cell tested nothing
                # (round 1 MED-002).
                start = token.lower().index(core)
                tokens[index] = token[:start] + flipped + token[start + len(core) :]
                return tokens
        return None

    def _change_dose(self, tokens: list[str]) -> list[str] | None:
        """Double a MEDICATION-ANCHORED dose quantity that actually changes.

        Rounds 21-22 PR-MED-001 (the fifth and sixth difference-not-class
        instances): the old scan doubled the first digit run ANYWHERE, so a
        pain score or a duration "exercised" the dosage class while no dose
        changed — and round 22 showed a stock count ("2 tablets remaining")
        doing the same. The mutation now applies only to a quantity in the
        fixture contract's dose shape — an ATTACHED strength
        (``_ATTACHED_STRENGTH_RE``) or a quantity followed by a
        unit/regimen marker (``_DOSE_MEDICATIONS`` / ``_DOSE_MARKERS``
        above; count words are deliberately absent) — and every dose site
        is tried before giving up. A zero quantity doubles to itself
        (round 4 PR-MED-002), so the scan moves past it; ``0.5`` is mutable
        via its ``5``. No dose site anywhere means the fixture cannot
        express this class, and ``_mutate`` raises.
        """
        for index, token in enumerate(tokens):
            if normalise_token(token) not in _DOSE_MEDICATIONS:
                continue
            if index + 1 >= len(tokens):
                continue
            quantity = tokens[index + 1]
            attached = _ATTACHED_STRENGTH_RE.match(normalise_token(quantity)) is not None
            marked = (
                index + 2 < len(tokens)
                and normalise_token(tokens[index + 2]) in _DOSE_MARKERS
            )
            if not attached and not marked:
                continue
            for match in _DIGITS_RE.finditer(quantity):
                doubled = str(int(match.group()) * 2)
                replaced = quantity[: match.start()] + doubled + quantity[match.end() :]
                if replaced == quantity:
                    continue
                tokens[index + 1] = replaced
                return tokens
        return None

    def _flip_negation(self, tokens: list[str]) -> list[str] | None:
        for index, token in enumerate(tokens):
            if normalise_token(token) in _NEGATIONS:
                del tokens[index]
                return tokens
        return None

    def _substitute_name(self, tokens: list[str]) -> list[str] | None:
        """Substitute the first name-like token that is not ALREADY the
        substitute, comparing NORMALISED forms.

        Round 4 skipped only the exact token `"Wilson"`, so `"Wilson,"` and
        `"WILSON"` were "substituted" into `"Wilson"` — a punctuation/case
        edit reported as a name substitution (round 5 PR-MED-001). Surrounding
        punctuation is now preserved on a real substitution, like
        `_flip_laterality`, so the only thing that changes is the name.
        """
        substitute = normalise_token(_SUBSTITUTE_NAME)
        for index, token in enumerate(tokens):
            if normalise_token(token) == substitute:
                continue
            if not is_name_like_token(token, first_in_segment=index == 0):
                continue
            core = _STRIP_PUNCT_RE.sub("", token)
            start = token.index(core)
            tokens[index] = token[:start] + _SUBSTITUTE_NAME + token[start + len(core) :]
            return tokens
        return None

    def _invented_assertion(self, request: NoteRequest) -> NoteAssertion:
        key, text = _INVENTED[self._behaviour]
        first = request.transcript_utterances[0]
        return NoteAssertion(
            assertion_id="minv0",
            section_key=key,
            speaker=request.clinician_speaker,
            note_span=NoteSpan(
                span_text=text,
                provenance="transcript",
                source_coords=SourceCoords(first.segment_index, 0, 0),
            ),
        )

    def _injected_assertion(self, request: NoteRequest) -> NoteAssertion:
        """Quote the LAST injection-like utterance verbatim into a
        clinician-owned section.

        Deliberately grounded: it reconstructs exactly, so the defence must
        come from role ownership and confirmation, never from grounding.
        The quoted utterance must satisfy the `_is_injection_like` fixture
        contract (Task 5.0, peer probe 1): a transcript containing NO
        injected instruction cannot express this class, and quoting ordinary
        speech instead would be a wrong-class result — mis-sectioned
        content, not obedience to an instruction — so the honest outcome is
        the same loud refusal the mutations use.
        """
        injected = [
            utterance
            for utterance in request.transcript_utterances
            if utterance.transcript_words and _is_injection_like(utterance.text)
        ]
        if not injected:
            raise NoteProviderError(
                "obeys_injection needs an utterance containing an injected instruction"
            )
        last = injected[-1]
        words = last.transcript_words
        return NoteAssertion(
            assertion_id="minj0",
            section_key="management_plan",
            speaker=last.speaker,
            note_span=NoteSpan(
                span_text=last.text,
                provenance="transcript",
                source_coords=SourceCoords(last.segment_index, 0, len(words) - 1),
            ),
        )

    def _misattribute_speaker(
        self, request: NoteRequest, assertions: list[NoteAssertion]
    ) -> list[NoteAssertion]:
        """Reattribute ONE assertion to a different existing cluster — text,
        section and coordinates all stay correct (Task 5.0).

        The class this expresses: an utterance carried faithfully but
        credited to the wrong voice, which is what a diarization merge or a
        provider attribution error looks like downstream. A single-cluster
        transcript cannot express it (there is no wrong cluster to pick), so
        it raises — the same loud-failure rule as the mutations.
        """
        labels: list[str] = []
        for utterance in request.transcript_utterances:
            if utterance.speaker not in labels:
                labels.append(utterance.speaker)
        for index, assertion in enumerate(assertions):
            other = next((label for label in labels if label != assertion.speaker), None)
            if other is None:
                continue
            swapped = NoteAssertion.model_validate(
                {**assertion.model_dump(), "speaker": other}
            )
            return [*assertions[:index], swapped, *assertions[index + 1 :]]
        raise NoteProviderError(
            "speaker_misattribution needs at least two speaker labels"
        )

    def _malformed_assertion(self, request: NoteRequest) -> NoteAssertion:
        """Coordinates addressing a segment the transcript does not have."""
        beyond = max(u.segment_index for u in request.transcript_utterances) + 1
        return NoteAssertion(
            assertion_id="mbad0",
            section_key="presenting_complaint",
            note_span=NoteSpan(
                span_text="unverifiable content",
                provenance="transcript",
                source_coords=SourceCoords(beyond, 0, 0),
            ),
        )

    def _as_sections(self, assertions: Sequence[NoteAssertion]) -> tuple[GeneratedSection, ...]:
        routed: dict[NoteSectionKey, list[NoteAssertion]] = {}
        for assertion in assertions:
            routed.setdefault(assertion.section_key, []).append(assertion)
        return tuple(
            GeneratedSection(section_key=key, note_assertions=tuple(routed[key]))
            for key in CANONICAL_SECTION_KEYS
            if key in routed
        )


# ---------------------------------------------------------------------------
# The two-stage pipeline (Task 6.1) — Flow 1's ordering, made structural:
#
#   compose_draft()  -> base note PLUS proposals; runs NO checks
#   (clinician confirms/declines each proposal — Phase 7's Note tab)
#   finalise_note()  -> composes CONFIRMED proposals into assertions, runs
#                       EVERY check, assembles the GeneratedNote
#
# Checks never run before confirmation, and confirmation evidence rides the
# ARTIFACT (proposal_id + shown_text_digest + ConfirmationDecision on every
# composed assertion), never the call. An emitted-but-unresolved proposal is
# not an exception here: it flows into ``check_note(pending_proposals=...)``
# and comes back as an ``unconfirmed_proposal`` ERROR riding the note, so
# the refusal is an ACTION STATE (``blocking_warnings()`` non-empty;
# ``write_note`` refuses) exactly as global property 4 words it.
# ---------------------------------------------------------------------------


class NotePipelineError(Exception):
    """A pipeline-stage precondition failed (compose/finalise misuse)."""


class ProposalEvidenceError(NotePipelineError):
    """Confirmation evidence does not correspond to the draft's proposals —
    a resolution for a proposal the draft never emitted, two resolutions for
    one proposal, or a confirmed text digest that is not the digest of the
    text the proposal would insert."""


class ProviderOutputError(NotePipelineError):
    """A provider returned an assertion that is not transcript-provenance —
    fabricated evidence about a decision nobody made (round 28 PR-MED-001,
    enforced at ingestion since schema v2)."""


class NoteDraft(BaseModel):
    """Stage-one output: the base note plus its proposals, UNCHECKED.

    In-memory hand-off between ``compose_draft`` and ``finalise_note`` only —
    never persisted, never rendered as prose.

    The confinement this type ENFORCES (round 28 PR-MED-001, widened by
    schema v2 D4): base sections hold ``DRAFT_BASE_PROVENANCES`` only —
    TRANSCRIPT-provenance assertions and the clinician's typed ``clinician``
    lines. A rule-authored ``autofill``/``prefill`` assertion is refused by
    the validator however complete its evidence fields look — confirmation
    evidence is a record of a RECORDED decision (the clinician's per-line
    one, or since D5 a ``decided_by="config"`` resolution minted at the
    emitter and ratified by the counted Save), and provider output must
    never bypass the proposal-resolution loop that creates one.
    ``finalise_note`` re-establishes the same confinement, so a
    validator-skipping (``model_construct``) draft cannot bypass it either.
    Because a typed line is admitted here, this validator is no longer the
    control for what a PROVIDER returns: ``compose_draft`` confines the
    provider's output to transcript-provenance at ingestion, before any
    draft exists, and a typed line enters only afterwards through the review
    surface (``ui.models.working_draft``). Every ``autofill``/``prefill``
    assertion in a final note therefore originates in ``finalise_note``'s
    resolution loop: one emitted proposal, one confirmed resolution,
    digest-verified; every ``clinician`` assertion carries the decision that
    names it.

    Residue, named rather than implied: ``GeneratedSection`` itself stays
    BROAD — final notes legitimately hold composed clinician-authored
    assertions — so a hand-built ``GeneratedNote`` handed straight to
    ``write_note`` is outside this confinement (``write_note`` verifies
    evidence self-consistency, not proposal membership: the artifact carries
    no proposal set). Same-user hand-crafting sits outside the threat model
    (the rounds 12-13 convention), and the review surface (a per-line row
    for a proposal; the D5 mark plus the counted Save for a config-decided
    line) plus Check 3 remain the compensating controls. Phase 3B's
    model-authored provenance gets its OWN explicit contract when it
    arrives; it does not widen this path.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str = Field(pattern=SESSION_ID_PATTERN)
    template_profile_id: str = Field(pattern=_PROFILE_ID_PATTERN)
    provider_name: str = Field(min_length=1, max_length=64)
    clinician_speaker: str | None = None
    transcript_digest: str
    config_digest: str
    note_sections: tuple[GeneratedSection, ...] = ()
    note_proposals: tuple[NoteProposal, ...] = ()
    # Note-learning plan Phase 2 (D4, D5): the decisions the practitioner's
    # OWN config made, MINTED AT THE EMITTER (``note_fill.config_decisions``)
    # and carried with the draft — one per proposal that arrives pre-filled,
    # ``decided_by="config"`` under this draft's digest. The review surface
    # passes them to ``finalise_note`` as the counted Save's ratification;
    # ``finalise_note`` accepts a config decision ONLY when it is one of
    # these, so no review surface can mint one of its own.
    config_decisions: tuple[ProposalResolution, ...] = ()

    @model_validator(mode="after")
    def _check_draft(self) -> Self:
        for label, value in (
            ("transcript_digest", self.transcript_digest),
            ("config_digest", self.config_digest),
        ):
            if not _DIGEST_RE.match(value):
                raise ValueError(f"{label} must match {DIGEST_PATTERN}")
        by_proposal = {proposal.proposal_id: proposal for proposal in self.note_proposals}
        decided: set[str] = set()
        for decision in self.config_decisions:
            proposal = by_proposal.get(decision.proposal_id)
            if proposal is None:
                raise ValueError(
                    f"config decision names a proposal the draft never emitted: "
                    f"{decision.proposal_id}"
                )
            if decision.proposal_id in decided:
                raise ValueError(f"duplicate config decision for {decision.proposal_id}")
            decided.add(decision.proposal_id)
            confirmation = decision.confirmation
            if confirmation.decided_by != "config":
                raise ValueError("a draft carries config decisions only, never clinician ones")
            if confirmation.note_confirmation != "confirmed":
                raise ValueError("a config decision pre-fills a line; it cannot decline one")
            if confirmation.config_digest != self.config_digest:
                raise ValueError(
                    "a config decision must be minted under the draft's own config_digest"
                )
            if decision.shown_text_digest != proposal.shown_text_digest:
                raise ValueError(
                    "a config decision must name the digest of the text its proposal inserts"
                )
        seen_keys: list[int] = []
        assertion_ids: set[str] = set()
        for section in self.note_sections:
            index = SECTION_INDEX[section.section_key]
            if seen_keys and index <= seen_keys[-1]:
                raise ValueError("note_sections must be unique and in canonical order")
            seen_keys.append(index)
            for assertion in section.note_assertions:
                # Round 28 PR-MED-001, widened by D4: quoted lines and typed
                # clinician lines only; rule-authored text is a proposal.
                if assertion.note_span.provenance not in DRAFT_BASE_PROVENANCES:
                    raise ValueError(
                        "a draft base section may hold transcript-provenance "
                        "assertions and typed clinician lines only; rule-authored "
                        f"content enters solely as proposals (assertion "
                        f"{assertion.assertion_id})"
                    )
                if assertion.assertion_id in assertion_ids:
                    raise ValueError(f"duplicate assertion_id: {assertion.assertion_id}")
                assertion_ids.add(assertion.assertion_id)
        proposal_ids: set[str] = set()
        for proposal in self.note_proposals:
            if proposal.proposal_id in proposal_ids:
                raise ValueError(f"duplicate proposal_id: {proposal.proposal_id}")
            proposal_ids.add(proposal.proposal_id)
        return self


class ProposalResolution(BaseModel):
    """The clinician's recorded resolution of ONE proposal.

    Flow 1's confirmation evidence, exactly as the plan words it: the
    ``proposal_id`` (inside the decision), the exact-text digest of what was
    DISPLAYED, and the ``ConfirmationDecision``. ``shown_text_digest`` is
    supplied by the review surface from the text it actually rendered —
    deliberately NOT copied from the proposal — so a UI that displayed
    something other than the proposal's exact text produces evidence that
    ``finalise_note`` refuses instead of evidence that lies.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    shown_text_digest: str
    confirmation: ConfirmationDecision

    @property
    def proposal_id(self) -> str:
        return self.confirmation.proposal_id

    @model_validator(mode="after")
    def _check_resolution(self) -> Self:
        if not _DIGEST_RE.match(self.shown_text_digest):
            raise ValueError(f"shown_text_digest must match {DIGEST_PATTERN}")
        return self


def compose_draft(
    document: TranscriptDocument,
    config: NoteConfig,
    provider: NoteModelProvider,
    template_profile_id: str | None = None,
    *,
    clinician_speaker: str | None = None,
    prefill_id: str | None = None,
    learned_rules: Mapping[str, LearnedRuleEntry] | None = None,
    decided_at: datetime | None = None,
) -> NoteDraft:
    """Stage one of Flow 1: compose the base note and its proposals.

    Note-learning plan Phase 2 (D5): the emitters also MINT the config
    decisions (``note_fill.config_decisions``) for the proposals that arrive
    pre-filled — every hand-authored rule and prefill entry, and every
    learned rule whose sidecar record (``learned_rules``, keyed by rule id;
    None or absent = "not auto-confirmed", so the rule proposes) says
    ``auto_confirmed`` — stamped ``decided_at`` (now by default) and carried
    on the draft for the review surface's counted Save.

    Runs NO checks — checking before the clinician has confirmed each
    proposal was the original pipeline-ordering defect (compose -> confirm ->
    CHECK -> write; plan Flow 1). Both confirmed inputs are consumed here:
    the request is constructed ONLY through ``note_config.build_note_request``
    (canonicalise + bind + derive, rounds 10-13), and ``clinician_speaker``
    must be the CONFIRMED role — Task 7.5 owns the control; passing a raw
    ``speaker_role()`` preselection through requires writing
    ``.preselected_clinician_speaker`` in plain sight, which is the guard.

    ``prefill_id`` is the clinician's explicit region choice;
    ``PrefillSelectionAmbiguousError`` propagates as the chooser case and
    ``UnknownPrefillError`` as a caller bug (``note_fill`` semantics).

    Provider output is CONFINED at ingestion (round 28 PR-MED-001; since
    schema v2 the check is ``_confine_provider_output``, run on the returned
    sections BEFORE any draft exists): a provider returns
    transcript-provenance assertions only, so it cannot smuggle
    clinician-authored content — a rule-authored line OR a fabricated typed
    line — past the proposal-resolution loop, however complete the
    fabricated evidence looks. The refusal is typed ``ProviderOutputError``.
    """
    from scribe_desktop.note_config import build_note_request
    from scribe_desktop.note_fill import (
        autofill_proposals,
        config_decisions,
        prefill_proposals,
    )

    request = build_note_request(
        document, config, template_profile_id, clinician_speaker=clinician_speaker
    )
    sections = provider.generate_sections(request)
    _confine_provider_output(sections)
    proposals = (
        *autofill_proposals(document, config),
        *prefill_proposals(document, config, prefill_id),
    )
    decisions = config_decisions(
        proposals,
        learned=learned_rules if learned_rules is not None else {},
        decided_at=decided_at if decided_at is not None else datetime.now(UTC),
    )
    return NoteDraft(
        session_id=request.session_id,
        template_profile_id=request.template_profile_id,
        provider_name=provider.provider_name,
        clinician_speaker=request.clinician_speaker,
        transcript_digest=request.transcript_digest,
        config_digest=request.config_digest,
        note_sections=sections,
        note_proposals=proposals,
        config_decisions=decisions,
    )


def _confine_provider_output(sections: Sequence[GeneratedSection]) -> None:
    """THE provider boundary (round 28 PR-MED-001, moved here by schema v2
    D4): a provider returns QUOTED lines only. The draft base also admits
    the clinician's typed lines — added by the review surface AFTER
    composition — so the draft validator can no longer tell a provider's
    smuggled ``clinician`` line from a typed one; this check runs on the
    provider's output itself, before a draft exists, and is the control."""
    for section in sections:
        for assertion in section.note_assertions:
            if assertion.note_span.provenance != "transcript":
                raise ProviderOutputError(
                    "a provider may return transcript-provenance assertions only; "
                    f"assertion {assertion.assertion_id} is {assertion.provenance}"
                )


def _merge_confirmed(
    base_sections: tuple[GeneratedSection, ...],
    confirmed: Sequence[NoteAssertion],
) -> tuple[GeneratedSection, ...]:
    """Base sections plus confirmed assertions, in canonical section order.

    Within a section the provider's assertions keep their order and confirmed
    proposals append after them in draft order — deterministic, so the same
    inputs always assemble the same artifact.
    """
    grouped: dict[NoteSectionKey, list[NoteAssertion]] = {
        section.section_key: list(section.note_assertions) for section in base_sections
    }
    for assertion in confirmed:
        grouped.setdefault(assertion.section_key, []).append(assertion)
    return tuple(
        GeneratedSection(section_key=key, note_assertions=tuple(grouped[key]))
        for key in CANONICAL_SECTION_KEYS
        if key in grouped
    )


def finalise_note(
    draft: NoteDraft,
    resolutions: Sequence[ProposalResolution],
    document: TranscriptDocument,
    config: NoteConfig,
    *,
    created_at: datetime | None = None,
) -> GeneratedNote:
    """Stage two of Flow 1: compose confirmed proposals, run EVERY check,
    assemble the ``GeneratedNote`` with its warnings attached.

    Evidence discipline (each refusal typed ``ProposalEvidenceError``):
    - a resolution naming a proposal the draft never emitted is refused —
      confirmation evidence about nothing must not exist;
    - two resolutions for one proposal are refused — which one the clinician
      meant would be an implementation accident;
    - a resolution — confirmed OR declined — whose ``shown_text_digest`` is
      not the digest of the proposal's exact insertable text is refused
      (Task 6.1 Done-when, widened decision-agnostic in round 25): the
      clinician decided about words that are not the words this proposal
      inserts, so the evidence backs nothing — and a mis-rendered decline
      must not silently resolve a proposal the clinician never saw.

    A DECLINED proposal is resolved and composes nothing (the type also pins
    this: a declined decision cannot construct an assertion). A proposal with
    NO resolution is pending: it is passed to ``check_note`` as
    ``pending_proposals`` and comes back as an ``unconfirmed_proposal`` error
    riding the artifact — the plan's action-state refusal (property 4), which
    ``write_note`` then enforces. A stale ``document`` or ``config`` dies in
    ``check_note``'s digest gate (``CheckTargetMismatchError``), deliberately
    not re-verified here — one gate, one owner.

    The base confinement is RE-ESTABLISHED here (round 28 PR-MED-001, widened
    by schema v2 D4): a draft base assertion outside
    ``DRAFT_BASE_PROVENANCES`` is refused even when the draft skipped
    validation (``NoteDraft.model_construct``), and a typed ``clinician``
    line must carry a clinician decision, so the only route by which a
    rule-authored assertion reaches the assembled note is the resolution loop
    below — one emitted proposal, one confirmed resolution — and a typed line
    reaches it only with the decision that names it. A resolution's decision
    may be ``decided_by="config"`` (D5): the assertion built from it carries
    that decision, and the type pins its digest to the assertion's — and
    (Phase 2) such a resolution is accepted ONLY when it is, field for
    field, one the draft carries in ``config_decisions``: the emitter mints
    config decisions, the review surface can only pass them on or replace
    them with the clinician's own.
    """
    from scribe_desktop.note_check import check_note

    for section in draft.note_sections:
        for assertion in section.note_assertions:
            if assertion.note_span.provenance not in DRAFT_BASE_PROVENANCES:
                raise ProposalEvidenceError(
                    f"draft base assertion {assertion.assertion_id} is not "
                    "transcript-provenance or a typed clinician line; rule-authored "
                    "content enters a note only through the proposal-resolution loop"
                )
            decision = assertion.confirmation
            if assertion.note_span.provenance == "clinician" and (
                decision is None or decision.decided_by != "clinician"
            ):
                raise ProposalEvidenceError(
                    f"typed line {assertion.assertion_id} carries no clinician decision"
                )
    by_id: dict[str, ProposalResolution] = {}
    for supplied in resolutions:
        proposal_id = supplied.confirmation.proposal_id
        if proposal_id in by_id:
            raise ProposalEvidenceError(f"duplicate resolution for proposal {proposal_id}")
        by_id[proposal_id] = supplied
    draft_ids = {proposal.proposal_id for proposal in draft.note_proposals}
    for proposal_id in by_id:
        if proposal_id not in draft_ids:
            raise ProposalEvidenceError(
                f"resolution names a proposal the draft never emitted: {proposal_id}"
            )
    minted = {decision.proposal_id: decision for decision in draft.config_decisions}
    pending: list[NoteProposal] = []
    confirmed: list[NoteAssertion] = []
    for proposal in draft.note_proposals:
        resolution = by_id.get(proposal.proposal_id)
        if resolution is None:
            pending.append(proposal)
            continue
        if resolution.confirmation.decided_by == "config" and (
            minted.get(proposal.proposal_id) != resolution
        ):
            raise ProposalEvidenceError(
                f"the config decision for proposal {proposal.proposal_id} is not the one "
                "the emitter minted for this draft"
            )
        # Decision-AGNOSTIC (round 25 LOW-001): a decline recorded against
        # text the UI never displayed is not a resolution either — treating
        # it as one would let a rendering bug silently drop a proposal the
        # clinician never actually saw. Verified before the declined branch.
        if resolution.shown_text_digest != proposal.shown_text_digest:
            raise ProposalEvidenceError(
                f"the shown-text digest recorded for proposal {proposal.proposal_id} is "
                "not the digest of the text this proposal inserts"
            )
        if resolution.confirmation.note_confirmation == "declined":
            continue
        confirmed.append(
            NoteAssertion(
                assertion_id=proposal.proposal_id,
                section_key=proposal.section_key,
                note_span=NoteSpan(
                    span_text=proposal.note_excerpt, provenance=proposal.provenance
                ),
                proposal_id=proposal.proposal_id,
                shown_text_digest=proposal.shown_text_digest,
                config_digest=proposal.config_digest,
                confirmation=resolution.confirmation,
            )
        )
    sections = _merge_confirmed(draft.note_sections, confirmed)
    stamp = created_at if created_at is not None else datetime.now(UTC)

    def _assemble(warnings: tuple[NoteWarning, ...]) -> GeneratedNote:
        return GeneratedNote(
            session_id=draft.session_id,
            created_at=stamp,
            template_profile_id=draft.template_profile_id,
            provider_name=draft.provider_name,
            clinician_speaker=draft.clinician_speaker,
            transcript_digest=draft.transcript_digest,
            config_digest=draft.config_digest,
            note_sections=sections,
            note_warnings=warnings,
        )

    unchecked = _assemble(())
    warnings = check_note(unchecked, document, config, pending_proposals=pending)
    return _assemble(warnings)


if TYPE_CHECKING:
    # Static conformance proof, checked by mypy and free at runtime: mypy is
    # configured over ``src`` only, so a test-side annotation would not
    # actually verify that these two classes satisfy the Protocol.
    _EXTRACTIVE_IS_A_PROVIDER: NoteModelProvider = ExtractiveNoteProvider()
    _MOCK_IS_A_PROVIDER: NoteModelProvider = MockNoteModelProvider()


__all__ = [
    "CANONICAL_SECTIONS",
    "CANONICAL_SECTION_KEYS",
    "CLINICIAN_OWNED_SECTIONS",
    "DEFAULT_SECTION_CUES",
    "DIGEST_ALGORITHM",
    "DIGEST_PATTERN",
    "DRAFT_BASE_PROVENANCES",
    "MAX_ASSERTION_CHARS",
    "MAX_SECTION_PROSE_CHARS",
    "MOCK_BEHAVIOURS",
    "NOTE_SCHEMA_VERSION",
    "NOTE_WARNING_SEVERITY",
    "NO_NOTE_CONTENT",
    "PREFILLED_MARK",
    "PROVENANCE_LABELS",
    "SECTION_CUES_FILENAME",
    "SECTION_INDEX",
    "SECTION_TITLES",
    "CanonicalSection",
    "ConfirmationDecision",
    "DecidedBy",
    "ExtractiveNoteProvider",
    "GeneratedNote",
    "GeneratedSection",
    "MockBehaviour",
    "MockNoteModelProvider",
    "NoteAssertion",
    "NoteDraft",
    "NoteModelProvider",
    "NotePipelineError",
    "NoteProposal",
    "NoteProvenance",
    "NoteProviderError",
    "NoteSectionKey",
    "NoteSpan",
    "NoteStyle",
    "NoteUtterance",
    "NoteWarning",
    "NoteWarningSeverity",
    "ProposalEvidenceError",
    "ProposalResolution",
    "ProviderOutputError",
    "SectionOwner",
    "SourceCoords",
    "SpeakerEvidence",
    "SpeakerRolePreselection",
    "StyleRendering",
    "StyleVerdict",
    "admissible_sections",
    "assertion_label",
    "compose_draft",
    "content_tokens",
    "digest_bytes",
    "finalise_note",
    "first_matching_section",
    "is_interrogative",
    "is_prefilled",
    "manual_assertion_id",
    "normalise_token",
    "provenance_label",
    "provider_assertion_id",
    "reconstruct_span_text",
    "render_note",
    "section_admits_utterance",
    "section_input_digest",
    "speaker_role",
    "spoken_by_confirmed_clinician",
    "strip_token_punctuation",
    "text_digest",
    "transcript_digest",
    "usable_rendering",
    "whole_utterance_assertion",
]
