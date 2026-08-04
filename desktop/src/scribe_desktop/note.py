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
from datetime import datetime
from typing import TYPE_CHECKING, Final, Literal, NamedTuple, Protocol, Self

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
    # Check 3 — provenance integrity (Task 5.3).
    "unconfirmed_proposal": "error",
    "autofill_trigger_absent": "error",
    "role_unconfirmed": "error",
    "clinician_asserted": "review",  # unsuppressible; acknowledgement is the exit
    "mapping_drop": "review",  # renders into "Unmapped content"; never a block
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


class NoteRequest(BaseModel):
    """Everything a provider is given — transcript in a data position only."""

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


def build_note_request(
    document: TranscriptDocument,
    *,
    template_profile_id: str,
    config_digest: str,
    clinician_speaker: str | None = None,
    section_keys: tuple[NoteSectionKey, ...] = CANONICAL_SECTION_KEYS,
) -> NoteRequest:
    """Assemble the provider request from a transcript artifact.

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
)

_FABRICATED_TEXT: Final = "The patient reported a fall from a ladder last Tuesday"
_INVENTED: Final[Mapping[MockBehaviour, tuple[NoteSectionKey, str]]] = {
    "invented_diagnosis": ("diagnosis", "L5-S1 disc herniation with radiculopathy"),
    "invented_plan": ("management_plan", "Twelve sessions over six weeks, prepaid"),
    "invented_referral": ("referrals_investigations", "Referred to orthopaedic surgeon"),
    "invented_investigation": ("referrals_investigations", "Lumbar MRI requested today"),
}
_SUBSTITUTE_NAME: Final = "Wilson"


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
    "dose_change": "a numeric token that changes when doubled",
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
    ) -> tuple[tuple[str, tuple[str, ...], SourceCoords | None], ...]:
        """What makes two mock outputs the same ADVERSARIAL result: which
        section, which statement, and which coordinates were cited.

        Blind to punctuation and case (not failure classes) and deliberately
        SENSITIVE to `source_coords`, because a correctly-worded assertion
        citing the wrong interval is a genuine failure class a future
        behaviour may want to produce.
        """
        return tuple(
            (
                assertion.section_key,
                content_tokens(assertion.text),
                assertion.note_span.source_coords,
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
        """Same coordinates, different text — Check 1's reconstruction fails."""
        return assertion.model_copy(
            update={"note_span": assertion.note_span.model_copy(update={"span_text": text})}
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
        """Double the first digit run that ACTUALLY changes when doubled.

        A zero run doubles to itself, so `search` + unconditional return made
        `"0 mg daily"` and the leading zero of `"0.5 mg daily"` report success
        while leaving the dose identical (round 4 PR-MED-002). Every run in
        every token is tried before giving up — `0.5` is mutable via its `5`.
        """
        for index, token in enumerate(tokens):
            for match in _DIGITS_RE.finditer(token):
                doubled = str(int(match.group()) * 2)
                replaced = token[: match.start()] + doubled + token[match.end() :]
                if replaced == token:
                    continue
                tokens[index] = replaced
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
        """Quote the LAST utterance verbatim into a clinician-owned section.

        Deliberately grounded: it reconstructs exactly, so the defence must
        come from role ownership and confirmation, never from grounding.
        """
        last = request.transcript_utterances[-1]
        words = last.transcript_words
        text = reconstruct_span_text(words)
        if not words or not text:
            raise NoteProviderError("obeys_injection needs a non-empty final utterance")
        return NoteAssertion(
            assertion_id="minj0",
            section_key="management_plan",
            speaker=last.speaker,
            note_span=NoteSpan(
                span_text=text,
                provenance="transcript",
                source_coords=SourceCoords(last.segment_index, 0, len(words) - 1),
            ),
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
    "NoteModelProvider",
    "NoteProposal",
    "NoteProviderError",
    "NoteRequest",
    "NoteSectionKey",
    "NoteSpan",
    "NoteUtterance",
    "NoteWarning",
    "NoteWarningSeverity",
    "SectionOwner",
    "SourceCoords",
    "build_note_request",
    "content_tokens",
    "digest_bytes",
    "is_interrogative",
    "normalise_token",
    "reconstruct_span_text",
    "text_digest",
    "transcript_digest",
]
