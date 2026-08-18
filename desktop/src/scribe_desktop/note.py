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
- Provenance proves ATTRIBUTION, never truth. Trigger presence, role
  attribution and provenance say nothing about whether a claim is true of
  this encounter; only explicit per-assertion confirmation does.

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
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
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
    from scribe_desktop.note_config import NoteConfig

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


def normalise_token(token: str) -> str:
    """Normalise one token: strip leading/trailing punctuation, lowercase.

    Built on ``transcription._STRIP_PUNCT_RE`` so transcript-side and
    note-side normalisation can never drift apart. Returns "" for a token
    that is entirely punctuation.
    """
    return _STRIP_PUNCT_RE.sub("", token).lower()


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
}


class SourceCoords(NamedTuple):
    """The ONE contiguous transcript interval a span may cite.

    A plain 3-tuple by design: coordinates are indices, carry no clinical
    content, and serialize as ``[segment, first, last]`` inside the span.
    """

    segment_index: int
    first_word_index: int
    last_word_index: int


class NoteSpan(BaseModel):
    """A single stretch of note text plus where it came from.

    ``provenance`` proves attribution, not truth. ``transcript`` spans carry
    coordinates and are verified by exact reconstruction (Check 1);
    ``autofill`` / ``prefill`` spans are clinician-authored boilerplate and
    are carried by explicit per-assertion confirmation alone.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    span_text: str = Field(min_length=1, max_length=MAX_ASSERTION_CHARS)
    provenance: Literal["transcript", "autofill", "prefill"]
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
            raise ValueError(f"a {self.provenance} span must not carry source_coords")
        return self


class ConfirmationDecision(BaseModel):
    """The clinician's recorded decision on one proposal.

    Evidence carried by the artifact, not a caller convention: from
    ``note.enc`` alone it is reconstructible that a human was shown this
    exact text and confirmed it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: str = Field(pattern=_ID_PATTERN)
    note_confirmation: Literal["confirmed", "declined"]
    decided_at: datetime


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

    @property
    def provenance(self) -> Literal["transcript", "autofill", "prefill"]:
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
            return self
        if any(field is None for field in evidence) or self.confirmation is None:
            raise ValueError(
                f"a {self.provenance} assertion requires proposal_id, shown_text_digest, "
                "config_digest and a ConfirmationDecision"
            )
        for label, value in (
            ("shown_text_digest", self.shown_text_digest),
            ("config_digest", self.config_digest),
        ):
            if value is None or not _DIGEST_RE.match(value):
                raise ValueError(f"{label} must match {DIGEST_PATTERN}")
        if self.confirmation.note_confirmation != "confirmed":
            raise ValueError("a declined proposal must never become an assertion")
        if self.confirmation.proposal_id != self.proposal_id:
            raise ValueError("confirmation.proposal_id does not match the assertion's proposal_id")
        return self


class NoteProposal(BaseModel):
    """A CANDIDATE assertion awaiting explicit confirmation of its exact text.

    Structurally distinct from ``NoteAssertion``: a proposal cannot be placed
    in a ``GeneratedSection``, so unconfirmed content cannot reach the saved
    note. One proposal per ATOMIC assertion — a three-claim expansion is
    three proposals, because confirming a block is not evidence about each
    claim inside it.
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


class GeneratedNote(BaseModel):
    """The complete note artifact stored in ``note.enc``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
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
        for section in self.note_sections:
            index = SECTION_INDEX[section.section_key]
            if seen_keys and index <= seen_keys[-1]:
                raise ValueError("note_sections must be unique and in canonical order")
            seen_keys.append(index)
            for assertion in section.note_assertions:
                if assertion.assertion_id in assertion_ids:
                    raise ValueError(f"duplicate assertion_id: {assertion.assertion_id}")
                assertion_ids.add(assertion.assertion_id)
        for warning in self.note_warnings:
            if warning.assertion_id is not None and warning.assertion_id not in assertion_ids:
                raise ValueError(f"warning references unknown assertion: {warning.assertion_id}")
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

# Cue phrases per canonical section, authored as readable phrases and
# normalised through ``content_tokens`` at import so cue matching and every
# other tokenisation share one rule. Routing takes the FIRST canonical
# section whose cue matches, so the table's order of evaluation is the
# canonical order, not this literal's order.
_RAW_SECTION_CUES: Final[tuple[tuple[NoteSectionKey, tuple[str, ...]], ...]] = (
    (
        "presenting_complaint",
        (
            "came in because",
            "here for",
            "here about",
            "the problem is",
            "complaining of",
            "pain in",
            "sore",
            "hurts",
        ),
    ),
    (
        "history_presenting_complaint",
        ("started", "began", "first noticed", "ever since", "it came on", "weeks ago", "days ago"),
    ),
    (
        "progress_since_last_visit",
        (
            "since last time",
            "since the last visit",
            "since last session",
            "since i saw you",
            "compared to last",
            "better since",
            "worse since",
        ),
    ),
    (
        "past_medical_history",
        ("history of", "previously had", "past surgery", "operated on", "diagnosed with"),
    ),
    (
        "red_flags_screening",
        (
            "any numbness",
            "any tingling",
            "weight loss",
            "night pain",
            "bladder",
            "bowel",
            "fever",
            "saddle",
        ),
    ),
    (
        "objective_examination",
        (
            "on examination",
            "range of motion",
            "palpation",
            "tender to touch",
            "i can feel",
            "test is",
            "straight leg raise",
        ),
    ),
    (
        "outcome_measures",
        ("out of ten", "pain score", "scale of", "degrees of", "score is"),
    ),
    (
        "assessment",
        ("my assessment is", "clinically this is", "this presents as", "consistent with"),
    ),
    (
        "diagnosis",
        ("the diagnosis is", "you have", "this is a", "working diagnosis"),
    ),
    (
        "treatment_performed",
        (
            "today we did",
            "i treated",
            "we mobilised",
            "soft tissue",
            "dry needling",
            "manipulation",
            "i released",
        ),
    ),
    (
        "response_to_treatment",
        ("feels better now", "eased off", "after treatment", "responded well", "less sore now"),
    ),
    (
        "advice_home_exercise",
        ("home exercise", "exercises to do", "stretch", "advice is", "avoid lifting"),
    ),
    (
        "management_plan",
        ("the plan is", "we will", "next few weeks", "course of treatment", "management plan"),
    ),
    (
        "consent",
        ("happy to proceed", "consent", "explained the risks", "is that okay with you"),
    ),
    (
        "referrals_investigations",
        ("refer you", "referral", "imaging", "x ray", "scan", "blood test", "gp letter"),
    ),
    (
        "precautions_contraindications",
        ("be careful", "avoid", "do not", "precaution", "contraindicated"),
    ),
    (
        "follow_up_review",
        ("see you in", "book in", "next appointment", "follow up", "review you in"),
    ),
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
        tokens = content_tokens(utterance.text)
        if not tokens:
            return None
        is_clinician = (
            request.clinician_speaker is not None
            and utterance.speaker == request.clinician_speaker
        )
        question = is_interrogative(utterance.text)
        for key in request.section_keys:
            if key in CLINICIAN_OWNED_SECTIONS and (not is_clinician or question):
                continue
            if any(_contains_phrase(tokens, phrase) for phrase in self._cues.get(key, ())):
                return key
        return None

    def generate_sections(self, request: NoteRequest) -> tuple[GeneratedSection, ...]:
        routed: dict[NoteSectionKey, list[NoteAssertion]] = {}
        for utterance in request.transcript_utterances:
            words = utterance.transcript_words
            if not words:
                continue
            key = self._route(request, utterance)
            if key is None:
                continue
            text = reconstruct_span_text(words)
            if not text:
                continue
            assertion = NoteAssertion(
                assertion_id=f"x{utterance.segment_index:04d}",
                section_key=key,
                speaker=utterance.speaker,
                note_span=NoteSpan(
                    span_text=text,
                    provenance="transcript",
                    source_coords=SourceCoords(utterance.segment_index, 0, len(words) - 1),
                ),
            )
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


class NoteDraft(BaseModel):
    """Stage-one output: the base note plus its proposals, UNCHECKED.

    In-memory hand-off between ``compose_draft`` and ``finalise_note`` only —
    never persisted, never rendered as prose.

    The confinement this type ENFORCES (round 28 PR-MED-001): base sections
    hold TRANSCRIPT-provenance assertions ONLY. A provider-returned
    ``autofill``/``prefill`` assertion is refused by the validator however
    complete its evidence fields look — confirmation evidence is a record of
    a CLINICIAN decision, and provider output must never bypass the
    proposal-resolution loop that creates one. ``finalise_note``
    re-establishes the same confinement, so a validator-skipping
    (``model_construct``) draft cannot bypass it either. Every
    non-``transcript`` assertion in a final note therefore originates in
    ``finalise_note``'s resolution loop: one emitted proposal, one confirmed
    resolution, digest-verified.

    Residue, named rather than implied: ``GeneratedSection`` itself stays
    BROAD — final notes legitimately hold composed clinician-authored
    assertions — so a hand-built ``GeneratedNote`` handed straight to
    ``write_note`` is outside this confinement (``write_note`` verifies
    evidence self-consistency, not proposal membership: the artifact carries
    no proposal set). Same-user hand-crafting sits outside the threat model
    (the rounds 12-13 convention), and per-assertion confirmation in Phase
    7's UI plus Check 3 remain the compensating controls. Phase 3B's
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

    @model_validator(mode="after")
    def _check_draft(self) -> Self:
        for label, value in (
            ("transcript_digest", self.transcript_digest),
            ("config_digest", self.config_digest),
        ):
            if not _DIGEST_RE.match(value):
                raise ValueError(f"{label} must match {DIGEST_PATTERN}")
        seen_keys: list[int] = []
        assertion_ids: set[str] = set()
        for section in self.note_sections:
            index = SECTION_INDEX[section.section_key]
            if seen_keys and index <= seen_keys[-1]:
                raise ValueError("note_sections must be unique and in canonical order")
            seen_keys.append(index)
            for assertion in section.note_assertions:
                # Round 28 PR-MED-001: the provider-boundary confinement.
                if assertion.note_span.provenance != "transcript":
                    raise ValueError(
                        "a draft base section may hold transcript-provenance "
                        "assertions only; clinician-authored content enters "
                        f"solely as proposals (assertion {assertion.assertion_id})"
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
) -> NoteDraft:
    """Stage one of Flow 1: compose the base note and its proposals.

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

    Provider output is CONFINED at ingestion (round 28 PR-MED-001): the
    returned sections become ``NoteDraft.note_sections``, whose validator
    refuses any non-``transcript`` assertion — a provider cannot smuggle
    clinician-authored content past the proposal-resolution loop, however
    complete the fabricated evidence looks. The refusal is the type's own
    ``ValidationError``, consistent with this module's structural refusals.
    """
    from scribe_desktop.note_config import build_note_request
    from scribe_desktop.note_fill import autofill_proposals, prefill_proposals

    request = build_note_request(
        document, config, template_profile_id, clinician_speaker=clinician_speaker
    )
    sections = provider.generate_sections(request)
    proposals = (
        *autofill_proposals(document, config),
        *prefill_proposals(document, config, prefill_id),
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

    The provider-boundary confinement is RE-ESTABLISHED here (round 28
    PR-MED-001): a draft base assertion that is not transcript-provenance is
    refused even when the draft skipped validation
    (``NoteDraft.model_construct``), so the only route by which a
    non-``transcript`` assertion reaches the assembled note is the
    resolution loop below — one emitted proposal, one confirmed resolution.
    """
    from scribe_desktop.note_check import check_note

    for section in draft.note_sections:
        for assertion in section.note_assertions:
            if assertion.note_span.provenance != "transcript":
                raise ProposalEvidenceError(
                    f"draft base assertion {assertion.assertion_id} is not "
                    "transcript-provenance; clinician-authored content enters a "
                    "note only through the proposal-resolution loop"
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
    pending: list[NoteProposal] = []
    confirmed: list[NoteAssertion] = []
    for proposal in draft.note_proposals:
        resolution = by_id.get(proposal.proposal_id)
        if resolution is None:
            pending.append(proposal)
            continue
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
    "MAX_ASSERTION_CHARS",
    "MOCK_BEHAVIOURS",
    "NOTE_WARNING_SEVERITY",
    "SECTION_INDEX",
    "CanonicalSection",
    "ConfirmationDecision",
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
    "NoteProviderError",
    "NoteSectionKey",
    "NoteSpan",
    "NoteUtterance",
    "NoteWarning",
    "NoteWarningSeverity",
    "ProposalEvidenceError",
    "ProposalResolution",
    "SectionOwner",
    "SourceCoords",
    "SpeakerEvidence",
    "SpeakerRolePreselection",
    "compose_draft",
    "content_tokens",
    "digest_bytes",
    "finalise_note",
    "is_interrogative",
    "normalise_token",
    "reconstruct_span_text",
    "speaker_role",
    "text_digest",
    "transcript_digest",
]
