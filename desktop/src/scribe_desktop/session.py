"""Core recording-session types (PLAN.md core types; Phase 2 Step 1).

`SessionState` is the real session lifecycle enum from PLAN.md — it
supersedes Phase 1's throwaway `ConnectionState` (now retired). The
state MACHINE (legal transitions, controls, concurrency) arrives in
Step 4; this module defines only the types.

`RecordingSession` carries the PLAN.md fields: session identifier,
encounter context, encryption-key reference and timestamps. In Phase 2
there is no Chrome-side encounter context yet (that is Phase 5), so
`encounter_context` is optional. `key_reference` is a REFERENCE to the
DPAPI-wrapped key blob (a filesystem path string) — never key material.

Critical Constraint: nothing in this module may hold or log clinical
data; all logging of session events goes through `log_event` with
whitelisted keys only.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class SessionState(enum.StrEnum):
    """PLAN.md session lifecycle states (all nine; machine lands in Step 4)."""

    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    PROCESSING = "processing"
    QUEUED = "queued"
    WRITTEN = "written"
    FAILED = "failed"
    DISCARDED = "discarded"
    EXPIRED = "expired"


# States during which the expiry sweep must never touch a session
# (plan Critical Constraint: sweep skips recording/paused/processing).
ACTIVE_STATES: frozenset[SessionState] = frozenset(
    {SessionState.RECORDING, SessionState.PAUSED, SessionState.PROCESSING}
)

# States a crashed session may be recovered from (recovery screen lists these).
RECOVERABLE_STATES: frozenset[SessionState] = frozenset(
    {SessionState.RECORDING, SessionState.PAUSED, SessionState.PROCESSING, SessionState.FAILED}
)

# Terminal states: no further transitions, key custody already destroyed
# or scheduled for destruction.
TERMINAL_STATES: frozenset[SessionState] = frozenset(
    {SessionState.WRITTEN, SessionState.DISCARDED, SessionState.EXPIRED}
)


def _new_session_id() -> str:
    return uuid.uuid4().hex


def _utc_now() -> datetime:
    return datetime.now(UTC)


class RecordingSession(BaseModel):
    """PLAN.md core type: identifier, encounter context, key reference,
    timestamps. Immutable value object — state transitions produce copies
    via `with_state` so concurrent readers never see partial mutation
    (the single transition lock arrives with the Step 4 machine)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Opaque, non-clinical identifier — exactly uuid4().hex. The strict
    # pattern keeps it safe as a single filesystem path segment
    # (sessions/<id>/) and as whitelisted log metadata (PR-MED-002).
    session_id: str = Field(default_factory=_new_session_id, pattern=r"^[0-9a-f]{32}$")
    # Phase 5 delivers the real EncounterContext from Chrome; until then an
    # opaque optional reference keeps the PLAN.md shape without inventing data.
    encounter_context: str | None = Field(default=None, max_length=256)
    # Opaque reference to the DPAPI-wrapped session key blob. NEVER key
    # material, and NEVER a caller-supplied path (PR-MED-003): the only legal
    # value is the literal filename "key.dpapi"; Step 2 resolves it strictly
    # as <sessions root>/<validated session_id>/key.dpapi, so a malformed
    # session can never point deletion outside its own directory.
    key_reference: str | None = Field(default=None, pattern=r"^key\.dpapi$")
    state: SessionState = SessionState.IDLE
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    def with_state(self, state: SessionState) -> RecordingSession:
        """Return a copy in `state` with a fresh `updated_at` timestamp.

        Transition LEGALITY is not enforced here — that is the Step 4
        state machine's job; this is a pure data operation.
        """
        return self.model_copy(update={"state": state, "updated_at": _utc_now()})

    @property
    def is_active(self) -> bool:
        return self.state in ACTIVE_STATES

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES
