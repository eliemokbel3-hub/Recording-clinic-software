"""Message protocol — hand-mirrored from the canonical fixtures.

The canonical contract lives in `protocol/fixtures/` (plan Key Design
Decision: fixtures-canonical protocol). This module and the TypeScript
mirror (`extension/src/protocol.ts`) are both validated against the same
fixture files; drift is a test failure.

Envelope: protocol_version, type, request_id?, session_nonce?, payload.
Per-type nonce rules on the CHROME wire: hello forbids it; hello_ack, ping,
pong, context, command and state require it; error allows it. Versions below
MIN_SUPPORTED_VERSION are rejected.

Protocol v2 (Cliniko workflow safeguards plan D2, Task 4.1) adds three
types, each with a payload model whose every string and array is bounded
(``LIMITS``, pinned in ``meta.json``) and whose extra keys are refused:

- ``context`` (extension -> app): what one tab shows. Cliniko ids are digit
  strings (``^[1-9][0-9]{0,18}$``); a host is present only for a Cliniko
  page; a tab that left the allow-list reports ``not_cliniko`` with NO host
  and no ids, and a closed tab ``closed``. Never a URL.
- ``command`` (extension -> app): a clicked intent. ``start`` carries the
  target and the consent; ``resume``, ``finish``, ``discard``,
  ``resume_previous`` and ``open_review`` carry the ``session_ref`` they act
  on; ``discard`` also carries ``confirmed: true`` (the second click).
- ``state`` (app -> extension): the app's full snapshot. A refused command
  is named in ``last_refusal`` — never an ``error``, which is fatal-only
  (the extension disconnects on it).

THE PIPE (host <-> app, D2): the host strips the nonce from ``context`` and
``command`` before relaying them to the app and stamps it on the app's
``state``, so the app never sees it. ``parse_pipe_envelope`` validates that
leg: only the three v2 types, with NO nonce. The TypeScript mirror never
sees the pipe, so this rule is Python-only (``test_protocol.py``).

Integers are JSON integers. One mirror residue, named: JavaScript cannot
tell ``1.0`` from ``1`` after ``JSON.parse``, so the TypeScript mirror
accepts a fraction-free float where this one refuses it.
"""

from __future__ import annotations

import enum
from typing import Annotated, Any, Final, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StringConstraints,
    ValidationInfo,
    model_validator,
)

PROTOCOL_VERSION = 2
MIN_SUPPORTED_VERSION = 2
HOST_NAME = "com.scribe.cliniko_host"
# Project policy bound, both directions (platform allows more Chrome->host).
MAX_FRAME_BYTES = 1_048_576

MessageType = Literal[
    "hello", "hello_ack", "ping", "pong", "error", "context", "command", "state"
]

# Messages that must NOT carry a session_nonce / that MUST carry one.
NONCE_FORBIDDEN: frozenset[str] = frozenset({"hello"})
NONCE_REQUIRED: frozenset[str] = frozenset(
    {"hello_ack", "ping", "pong", "context", "command", "state"}
)
# The types that cross the host <-> app pipe, always WITHOUT a nonce (D2).
PIPE_TYPES: frozenset[str] = frozenset({"context", "command", "state"})

# Every bound both mirrors enforce, pinned in `protocol/fixtures/meta.json`.
LIMITS: Final[dict[str, int]] = {
    "max_seq": 9_007_199_254_740_991,
    "max_state_rev": 9_007_199_254_740_991,
    "max_tab_id": 2_147_483_647,
    "max_recorded_seconds": 1_000_000,
    "max_banner_count": 99,
    "max_request_id_chars": 128,
    "max_display_chars": 120,
    "max_label_chars": 80,
    "max_message_chars": 300,
    "max_reason_chars": 48,
    "max_timestamp_chars": 40,
    "max_chord_chars": 40,
    "max_allow_list": 16,
    "max_warnings": 8,
    "session_ref_chars": 24,
}

# Shapes shared with the TypeScript mirror (character for character).
ID_PATTERN: Final = r"^[1-9][0-9]{0,18}$"
HOST_PATTERN: Final = r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.[a-z]{2}[0-9]\.cliniko\.com$"
SESSION_REF_PATTERN: Final = r"^[A-Za-z0-9_-]{24}$"
REASON_PATTERN: Final = r"^[a-z][a-z0-9_]{0,47}$"
TIMESTAMP_PATTERN: Final = (
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?"
    r"(Z|[+-][0-9]{2}:[0-9]{2})$"
)
# Display text is one line: no C0 or C1 control character, no DEL.
_TEXT_PATTERN: Final = r"^[^\x00-\x1f\x7f-\x9f]+$"


class ErrorCode(enum.StrEnum):
    VERSION_BELOW_FLOOR = "version_below_floor"
    BAD_NONCE = "bad_nonce"
    MALFORMED = "malformed"
    OVERSIZED = "oversized"
    INTERNAL = "internal"


def _require_true(value: bool) -> bool:
    if value is not True:
        raise ValueError("must be true")
    return value


def _text_constraints(max_chars: int) -> StringConstraints:
    return StringConstraints(
        strict=True, min_length=1, max_length=max_chars, pattern=_TEXT_PATTERN
    )


_Id = Annotated[str, StringConstraints(strict=True, pattern=ID_PATTERN)]
_Host = Annotated[str, StringConstraints(strict=True, pattern=HOST_PATTERN)]
_Ref = Annotated[str, StringConstraints(strict=True, pattern=SESSION_REF_PATTERN)]
_Reason = Annotated[str, StringConstraints(strict=True, pattern=REASON_PATTERN)]
_Timestamp = Annotated[
    str,
    StringConstraints(
        strict=True, max_length=LIMITS["max_timestamp_chars"], pattern=TIMESTAMP_PATTERN
    ),
]
_Display = Annotated[str, _text_constraints(LIMITS["max_display_chars"])]
_Label = Annotated[str, _text_constraints(LIMITS["max_label_chars"])]
_Message = Annotated[str, _text_constraints(LIMITS["max_message_chars"])]
_Chord = Annotated[str, _text_constraints(LIMITS["max_chord_chars"])]
_TabId = Annotated[StrictInt, Field(ge=0, le=LIMITS["max_tab_id"])]
_Seq = Annotated[StrictInt, Field(ge=1, le=LIMITS["max_seq"])]
_StateRev = Annotated[StrictInt, Field(ge=0, le=LIMITS["max_state_rev"])]
_Seconds = Annotated[StrictInt, Field(ge=0, le=LIMITS["max_recorded_seconds"])]
_BannerCount = Annotated[StrictInt, Field(ge=1, le=LIMITS["max_banner_count"])]
_True = Annotated[StrictBool, AfterValidator(_require_true)]

CommandAction = Literal[
    "start", "pause", "resume", "finish", "discard", "resume_previous", "open_review"
]
# The actions that act on ONE session and must name it (D2).
SESSION_BOUND_ACTIONS: frozenset[str] = frozenset(
    {"resume", "finish", "discard", "resume_previous", "open_review"}
)
PageKind = Literal["note", "login", "other_cliniko", "not_cliniko", "closed"]
# Pages that are on an allow-listed host (and so carry it).
HOSTED_PAGES: frozenset[str] = frozenset({"note", "login", "other_cliniko"})


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="before")
    @classmethod
    def _reject_explicit_null(cls, data: Any) -> Any:
        # Mirror alignment: an absent optional field is omitted, never null
        # (the TypeScript mirror refuses a present null, as for the envelope).
        if isinstance(data, dict) and any(value is None for value in data.values()):
            raise ValueError("a payload field must not be an explicit null")
        return data


class EmptyPayload(_Payload):
    """hello, hello_ack, ping and pong carry nothing."""


class ErrorPayload(_Payload):
    code: ErrorCode
    message: Annotated[
        str,
        StringConstraints(strict=True, min_length=1, max_length=LIMITS["max_message_chars"]),
    ]


class ContextPayload(_Payload):
    seq: _Seq
    tab_id: _TabId
    window_id: _TabId
    focused: StrictBool
    page: PageKind
    host: _Host | None = None
    patient_id: _Id | None = None
    note_id: _Id | None = None

    @model_validator(mode="after")
    def _shape(self) -> ContextPayload:
        if (self.page in HOSTED_PAGES) != (self.host is not None):
            raise ValueError("a host is carried exactly by a page on a Cliniko host")
        has_ids = (self.patient_id is not None, self.note_id is not None)
        if has_ids != ((True, True) if self.page == "note" else (False, False)):
            raise ValueError("patient and note ids are carried exactly by a note page")
        return self


class CommandConsent(_Payload):
    confirmed: _True
    text_version: Literal["recording-consent-v1"]


class CommandTarget(_Payload):
    tab_id: _TabId
    clinic_host: _Host
    patient_id: _Id
    note_id: _Id


class CommandPayload(_Payload):
    action: CommandAction
    state_rev: _StateRev
    session_ref: _Ref | None = None
    consent: CommandConsent | None = None
    target: CommandTarget | None = None
    confirmed: _True | None = None

    @model_validator(mode="after")
    def _shape(self) -> CommandPayload:
        start = self.action == "start"
        if (self.target is not None, self.consent is not None) != (start, start):
            raise ValueError("start carries exactly a target and a consent")
        if start and self.session_ref is not None:
            raise ValueError("start acts on no session")
        if self.action in SESSION_BOUND_ACTIONS and self.session_ref is None:
            raise ValueError(f"{self.action} must name the session it acts on")
        if (self.confirmed is not None) != (self.action == "discard"):
            raise ValueError("discard, and only discard, carries the confirming second click")
        return self


VerificationView = Literal["checking", "verified", "unverified_offline", "refused"]
LivePhase = Literal["recording", "paused", "finishing", "queued"]


class ReportState(_Payload):
    """The bound report as the app sees it."""

    tab_id: _TabId
    clinic_host: _Host
    patient_id: _Id
    note_id: _Id
    verification: VerificationView
    refusal: _Reason | None = None
    clinic_label: _Label | None = None
    patient_name: _Display | None = None
    appointment_starts_at: _Timestamp | None = None

    @model_validator(mode="after")
    def _shape(self) -> ReportState:
        if (self.refusal is not None) != (self.verification == "refused"):
            raise ValueError("a refusal is carried exactly by a refused verification")
        if self.verification != "verified" and (
            self.patient_name is not None or self.appointment_starts_at is not None
        ):
            raise ValueError("display strings come only from a verified note")
        return self


class LiveState(_Payload):
    """The app's live session (never a directory name: ``session_ref``)."""

    session_ref: _Ref
    phase: LivePhase
    linked: StrictBool
    recorded_seconds: _Seconds
    consent_confirmed_at: _Timestamp
    clinic_host: _Host | None = None
    patient_id: _Id | None = None
    note_id: _Id | None = None
    verification: Literal["verified", "unverified_offline"] | None = None
    clinic_label: _Label | None = None
    patient_name: _Display | None = None

    @model_validator(mode="after")
    def _shape(self) -> LiveState:
        ids = (self.clinic_host, self.patient_id, self.note_id, self.verification)
        if self.linked and any(value is None for value in ids):
            raise ValueError("a linked session names its clinic, patient, note and verification")
        if not self.linked and any(
            value is not None for value in (*ids, self.clinic_label, self.patient_name)
        ):
            raise ValueError("an unlinked session names no clinic or patient")
        return self


class BlockState(_Payload):
    """The resolution block (Phase 5): the recording's own clinic and patient."""

    reason: _Reason
    session_ref: _Ref
    clinic_host: _Host
    clinic_label: _Label
    patient_name: _Display | None = None


class BannerState(_Payload):
    """The Unreviewed reminder (Phase 5) for one note."""

    session_ref: _Ref
    clinic_host: _Host
    note_id: _Id
    count: _BannerCount
    patient_name: _Display | None = None


class HotkeyState(_Payload):
    available: StrictBool
    chord: _Chord | None = None

    @model_validator(mode="after")
    def _shape(self) -> HotkeyState:
        if (self.chord is not None) != self.available:
            raise ValueError("an available hotkey names its chord")
        return self


class RefusalState(_Payload):
    action: CommandAction
    reason: _Reason
    message: _Message


class StatePayload(_Payload):
    state_rev: _StateRev
    app_running: StrictBool
    allow_list: Annotated[list[_Host], Field(max_length=LIMITS["max_allow_list"])]
    hotkey: HotkeyState
    spoken_pause: StrictBool
    warnings: Annotated[list[_Reason], Field(max_length=LIMITS["max_warnings"])]
    report: ReportState | None = None
    live: LiveState | None = None
    block: BlockState | None = None
    banner: BannerState | None = None
    notice: _Reason | None = None
    last_refusal: RefusalState | None = None

    @model_validator(mode="after")
    def _shape(self) -> StatePayload:
        if not self.app_running and (
            self.allow_list
            or any(
                value is not None
                for value in (
                    self.report,
                    self.live,
                    self.block,
                    self.banner,
                    self.notice,
                    self.last_refusal,
                )
            )
        ):
            raise ValueError("an app that is not running reports nothing else")
        return self


PAYLOAD_MODELS: Final[dict[str, type[_Payload]]] = {
    "hello": EmptyPayload,
    "hello_ack": EmptyPayload,
    "ping": EmptyPayload,
    "pong": EmptyPayload,
    "error": ErrorPayload,
    "context": ContextPayload,
    "command": CommandPayload,
    "state": StatePayload,
}

_PIPE_CONTEXT: Final = {"link": "pipe"}


class Envelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    # Strict, as every v2 integer (round 25 LOW-021): a numeric string or a
    # boolean is refused on both mirrors.
    protocol_version: StrictInt = Field(ge=1)
    type: MessageType
    request_id: str | None = Field(
        default=None, min_length=1, max_length=LIMITS["max_request_id_chars"]
    )
    session_nonce: str | None = Field(default=None, min_length=16, max_length=128)
    payload: dict[str, Any]

    @model_validator(mode="before")
    @classmethod
    def _reject_explicit_null(cls, data: Any) -> Any:
        # Mirror alignment (MED-001): TS rejects an explicit JSON null for
        # optional string fields; pydantic would otherwise coerce it to
        # "absent". Same wire input must classify identically on both sides.
        if isinstance(data, dict):
            for field_name in ("session_nonce", "request_id"):
                if field_name in data and data[field_name] is None:
                    raise ValueError(f"{field_name} must not be an explicit null")
        return data

    @model_validator(mode="after")
    def _check_rules(self, info: ValidationInfo) -> Envelope:
        if self.protocol_version < MIN_SUPPORTED_VERSION:
            raise ValueError(
                f"protocol_version {self.protocol_version} is below the "
                f"supported floor {MIN_SUPPORTED_VERSION}"
            )
        pipe = isinstance(info.context, dict) and info.context.get("link") == "pipe"
        if pipe:
            if self.type not in PIPE_TYPES:
                raise ValueError(f"{self.type} does not cross the pipe")
            if self.session_nonce is not None:
                raise ValueError("the pipe never carries the session nonce")
        else:
            if self.type in NONCE_FORBIDDEN and self.session_nonce is not None:
                raise ValueError(f"{self.type} must not carry a session_nonce")
            if self.type in NONCE_REQUIRED and self.session_nonce is None:
                raise ValueError(f"{self.type} requires a session_nonce")
        # Raises (a ValidationError is a ValueError) on any payload fault.
        PAYLOAD_MODELS[self.type].model_validate(self.payload)
        return self


def parse_envelope(data: Any) -> Envelope:
    """Validate an already-decoded JSON value from the CHROME wire.

    Raises pydantic.ValidationError on any contract violation.
    """
    return Envelope.model_validate(data)


def parse_pipe_envelope(data: Any) -> Envelope:
    """Validate an already-decoded JSON value from the host <-> app PIPE:
    only ``context``, ``command`` or ``state``, and never a nonce (D2)."""
    return Envelope.model_validate(data, context=_PIPE_CONTEXT)


def typed_payload(envelope: Envelope) -> BaseModel:
    """The envelope's payload as its per-type model (already validated)."""
    return PAYLOAD_MODELS[envelope.type].model_validate(envelope.payload)


def make_envelope(
    message_type: MessageType,
    *,
    payload: dict[str, Any],
    request_id: str | None = None,
    session_nonce: str | None = None,
) -> Envelope:
    """Build an outbound envelope, OMITTING absent optional fields — an
    explicit null is a wire-contract violation (see _reject_explicit_null)."""
    kwargs: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "type": message_type,
        "payload": payload,
    }
    if request_id is not None:
        kwargs["request_id"] = request_id
    if session_nonce is not None:
        kwargs["session_nonce"] = session_nonce
    return Envelope(**kwargs)


def make_pipe_envelope(message_type: MessageType, *, payload: dict[str, Any]) -> Envelope:
    """Build a pipe envelope (no nonce, one of ``PIPE_TYPES``)."""
    return parse_pipe_envelope(
        {"protocol_version": PROTOCOL_VERSION, "type": message_type, "payload": payload}
    )


def make_error(code: ErrorCode, message: str, request_id: str | None = None) -> Envelope:
    return make_envelope(
        "error",
        payload={"code": code.value, "message": message},
        request_id=request_id,
    )
