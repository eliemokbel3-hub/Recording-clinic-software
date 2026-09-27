"""GUI-free view logic for the Step 10 screens (unit-testable without Qt).

Everything here is pure logic or thin composition over the real Phase-2
modules (session/session_store/speech/transcription/benchmark). Nothing
in this module may log or persist clinical text: transcript rendering
returns a string for DISPLAY ONLY.
"""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final, Literal, Protocol

from scribe_desktop.clinics import (
    ClinicRecord,
    ClinicRefusal,
    Committed,
    LoadProblem,
    Refused,
    Removed,
)
from scribe_desktop.context_rules import ReminderEntry
from scribe_desktop.encounter import (
    RECORDING_CONSENT_TEXT,
    ConsentAttestation,
    EncounterContext,
    EncounterRecord,
    NoteRefusal,
    NoteRefused,
    UnverifiedOffline,
    Verification,
    VerificationOutcome,
    Verified,
    read_encounter_record,
)
from scribe_desktop.hotkey import CHORD_TEXT
from scribe_desktop.language_model import (
    LanguageModel,
    LanguageModelError,
    LocalLanguageModel,
    language_model_file_available,
    language_runtime_importable,
)
from scribe_desktop.note import (
    CANONICAL_SECTION_KEYS,
    MAX_ASSERTION_CHARS,
    PREFILLED_MARK,
    SECTION_TITLES,
    ExtractiveNoteProvider,
    GeneratedNote,
    GeneratedSection,
    NoteAssertion,
    NoteDraft,
    NoteModelProvider,
    NoteProposal,
    NoteSectionKey,
    NoteStyle,
    NoteWarning,
    StyleRendering,
    admissible_sections,
    assertion_label,
    attach_style_renderings,
    bound_rendering,
    compose_draft,
    is_prefilled,
    note_input_digest,
    provenance_label,
    reconstruct_span_text,
    render_note,
)
from scribe_desktop.note_config import (
    # ``_no_control_chars`` is package-private by name, shared deliberately
    # (the note.py convention): ONE config-text validator, applied here to
    # typed wording that may become config.
    DEFAULT_NOTE_STYLE,
    LearnedRuleEntry,
    NoteConfig,
    NoteConfigError,
    PractitionerSettings,
    StyleProfile,
    _no_control_chars,
    is_learned_rule_id,
    load_learned_rule_entries,
    load_note_config,
    load_practitioner_settings,
    save_practitioner_settings,
)
from scribe_desktop.practitioner_profile import (
    ConsentRecord,
    PractitionerProfile,
    ProfileUnusableError,
    load_profile,
    load_style_profile,
    style_profile_present,
)
from scribe_desktop.prose_style import (
    PROSE_STYLES,
    ProseInput,
    ProseStyle,
    ProseStyleProvider,
)
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import (
    EnrolmentLease,
    GenerationLease,
    RecordingSession,
    SessionState,
)
from scribe_desktop.session_store import (
    AUDIO_FILENAME,
    ENCOUNTER_FILENAME,
    KEY_FILENAME,
    NOTE_FILENAME,
    RECOVERY_WINDOW,
    SESSION_ID_PATTERN,
    TRANSCRIPT_FILENAME,
    SessionStoreError,
    default_sessions_root,
    earliest_trusted_timestamp,
    key_blob_is_dead,
    read_note,
    read_store_header,
    session_expires_at,
    store_has_footer,
    unwrap_key_from_file,
)
from scribe_desktop.speaker_embedding import (
    SHIPPED_SPEAKER_EMBEDDER,
    EmbedderKind,
    SpeakerEmbedder,
    SpeakerModelError,
    build_speaker_embedder,
    shipped_embedder_identity,
    speaker_embedder_available,
)
from scribe_desktop.speech import SileroVad, vad_model_available
from scribe_desktop.transcription import (
    DEFAULT_WHISPER_MODEL,
    LiveFailure,
    LiveFailureKind,
    LiveTranscriber,
    LiveTranscriptionError,
    LiveTranscriptionFailed,
    RecoveryOutcome,
    TranscriptDocument,
    TranscriptSegment,
    WhisperSpeechProvider,
    read_transcript,
    recover_session_transcription,
    resolve_whisper_model,
    transcribe_session,
    whisper_model_available,
    write_transcript,
)

# Single-sourced session-id format (round 42 LOW-010).
_SESSION_ID_RE = re.compile(SESSION_ID_PATTERN)

# Binding Step-10 note (PR-HIGH-007 residual): shown whenever a recovered
# store carries no complete Finish footer.
UNFINISHED_STORE_WARNING = (
    "Warning: recording did not finish cleanly; the tail may be missing."
)

# Note-learning plan Task 1.4 (Flow 1): the live view's header and its empty
# state. The header is shown ONLY while a recording is in flight — the final
# document replaces the live lines wholesale at queued.
LIVE_TRANSCRIPT_HEADER: Final = "Live — updates while recording"
LIVE_TRANSCRIPT_PLACEHOLDER: Final = (
    "Live transcription appears here as the consultation is recorded."
)

# Cliniko workflow safeguards plan Task 3.3 (Constraint 4, D1): the desktop
# consent tick carries PLAN.md's wording verbatim; it is never pre-ticked and
# is cleared after every Start. The link line says whether the session is
# bound to a Cliniko note — never which patient.
RECORDING_CONSENT_LABEL: Final = RECORDING_CONSENT_TEXT
CONSENT_REQUIRED_MESSAGE: Final = (
    "Tick the consent box above Start first - consent is confirmed for every recording."
)
NOT_LINKED_LABEL: Final = "Not linked to a Cliniko note"
NOT_LINKED_DETAIL: Final = (
    f"{NOT_LINKED_LABEL} - a recording started here cannot be written back to Cliniko."
)
LINKED_VERIFIED_LABEL: Final = (
    "Linked to a Cliniko treatment note - verified with Cliniko at Start."
)
LINKED_UNVERIFIED_LABEL: Final = (
    "Linked to a Cliniko treatment note, not yet verified with Cliniko - write-back "
    "stays blocked until Cliniko verifies the note."
)


# Task 3.4: the recovery list reads the encounter record's PRESENCE only (a
# stat); a present record may be linked or unlinked — that is read on opening.
RECOVERY_NO_ENCOUNTER_LINE: Final = "not linked to a Cliniko note (consent record unavailable)"
RECOVERY_ENCOUNTER_LINE: Final = "Cliniko link checked when opened"
CHECKOUT_CONSENT_UNAVAILABLE_LINE: Final = (
    "Consent record unavailable - this recording is treated as not linked to a Cliniko "
    "note and cannot be written back to Cliniko."
)
CHECKOUT_UNLINKED_LINE: Final = (
    f"{NOT_LINKED_LABEL} - this recording cannot be written back to Cliniko."
)
CHECKOUT_REVERIFYING_LINE: Final = (
    "Linked to a Cliniko treatment note - checking it with Cliniko again before it counts "
    "as linked..."
)
CHECKOUT_VERIFIED_LINE: Final = (
    "Linked to a Cliniko treatment note - Cliniko verified it again just now."
)
CHECKOUT_OFFLINE_LINE: Final = (
    "Linked to a Cliniko treatment note, but Cliniko could not be reached to check it "
    "again - write-back stays blocked until Cliniko verifies the note."
)
# Round 20 LOW-015: no remedy is offered — a clinic added again gets a NEW
# clinic id (ids are never re-minted), so it never matches this record.
CHECKOUT_CLINIC_GONE_LINE: Final = (
    "Linked to a Cliniko treatment note in a clinic that is no longer set up in this app - "
    "this recording cannot be written back to Cliniko."
)
CHECKOUT_CHECK_STOPPED_LINE: Final = (
    "Linked to a Cliniko treatment note - the check with Cliniko stopped unexpectedly; "
    "write-back stays blocked. Open the session again to retry."
)

# Why a note did not verify (D4's named refusals), as the plain reason shown
# beside a refused Start or a refused re-check. No id, name or key.
NOTE_REFUSAL_REASONS: Final[Mapping[NoteRefusal, str]] = {
    NoteRefusal.CLINIC_NOT_SET_UP: (
        "this clinic is not set up - add its key on the Clinics tab"
    ),
    NoteRefusal.CLINIC_MISMATCH: "the note is not in this clinic's Cliniko account",
    NoteRefusal.PATIENT_MISMATCH: "the note belongs to a different patient than the page",
    NoteRefusal.NOTE_FINAL: "the note is already final in Cliniko",
    NoteRefusal.NOTE_ARCHIVED: "the note has been archived or deleted in Cliniko",
    NoteRefusal.WRONG_PRACTITIONER: "the note belongs to another practitioner",
    NoteRefusal.NOTE_NOT_FOUND: "Cliniko has no such note for this key",
    NoteRefusal.KEY_REJECTED: (
        "Cliniko rejected the clinic's API key - replace it on the Clinics tab"
    ),
    NoteRefusal.KEY_UNAVAILABLE: (
        "the clinic's API key could not be read from Windows Credential Manager - "
        "replace it on the Clinics tab"
    ),
    NoteRefusal.CERTIFICATE_REJECTED: "Cliniko's certificate was not trusted",
    NoteRefusal.ANSWER_UNREADABLE: "Cliniko's answer could not be read",
}


def note_refusal_line(reason: NoteRefusal) -> str:
    return NOTE_REFUSAL_REASONS[reason]


def recovery_link_line(has_encounter: bool) -> str:
    return RECOVERY_ENCOUNTER_LINE if has_encounter else RECOVERY_NO_ENCOUNTER_LINE


def checkout_link_line(
    record: EncounterRecord | None,
    *,
    checking: bool,
    outcome: VerificationOutcome | None,
    clinic_known: bool,
) -> str:
    """The recovered checkout's link line (Task 3.4). ``record`` None: the
    encounter record was missing or undecryptable."""
    if record is None:
        return CHECKOUT_CONSENT_UNAVAILABLE_LINE
    if record.context is None:
        return CHECKOUT_UNLINKED_LINE
    if not clinic_known:
        return CHECKOUT_CLINIC_GONE_LINE
    if checking:
        return CHECKOUT_REVERIFYING_LINE
    if isinstance(outcome, Verified):
        return CHECKOUT_VERIFIED_LINE
    if isinstance(outcome, UnverifiedOffline):
        return CHECKOUT_OFFLINE_LINE
    if isinstance(outcome, NoteRefused):
        return (
            "Linked to a Cliniko treatment note, but Cliniko did not verify it: "
            f"{note_refusal_line(outcome.reason)}. Write-back is blocked."
        )
    return CHECKOUT_CHECK_STOPPED_LINE


def session_link_line(session: RecordingSession | None) -> str:
    """The Session screen's link line for the tracked session (ids never
    shown). No session, a finished one, or an unlinked one: not linked."""
    context = session.encounter_context if session is not None else None
    if session is None or session.is_terminal or context is None:
        return NOT_LINKED_DETAIL
    if context.verification is Verification.VERIFIED:
        return LINKED_VERIFIED_LABEL
    return LINKED_UNVERIFIED_LABEL


# Cliniko workflow safeguards plan Task 4.5: the Chrome link on the Session
# screen. Plain text only; the patient's name appears only for the live
# session linked to a note Cliniko verified, and only in memory.
CHROME_WAITING_LINE: Final = (
    "Chrome: not connected - open Cliniko in Chrome with the Cliniko Scribe Companion "
    "extension to record from a treatment note."
)
CHROME_CONNECTED_LINE: Final = "Chrome: connected."
CHROME_UNAVAILABLE_LINE: Final = (
    "Chrome link unavailable - another program is using its channel. Close Cliniko Scribe "
    "and open it again; recording from the Session tab still works."
)
CHROME_SPOKEN_PAUSE_UNAVAILABLE_LINE: Final = (
    "Spoken pause unavailable for this recording - live transcription is off or has stopped."
)
# Tasks 7.1 and 7.2 (D7): the hands-free lines, keyed by the hotkey's status
# (``hotkey.HotkeyStatus.state``) and ``voice_commands.spoken_pause_state``.
HOTKEY_LINES: Final[Mapping[str, str]] = {
    "not_set_up": "Pause hotkey: not set up.",
    "on": "Pause hotkey: {chord} pauses the recording and resumes it.",
    "failed": (
        "Pause hotkey unavailable - Windows would not reserve {chord} (another program may "
        "be using it). Use Pause and Resume here or in Chrome's side panel."
    ),
}
SPOKEN_PAUSE_LINES: Final[Mapping[str, str]] = {
    "idle": 'Spoken pause: say "scribe pause" while recording to pause.',
    "on": (
        'Spoken pause: say "scribe pause" to pause. It takes effect once live transcription '
        "reaches it - usually a few seconds after you stop speaking."
    ),
    "unavailable": CHROME_SPOKEN_PAUSE_UNAVAILABLE_LINE,
}
HOTKEY_FAILED_STATUS: Final = (
    "The pause hotkey {chord} is unavailable - another program may be using it. Pause and "
    "Resume still work on the Session tab and in Chrome's side panel."
)
HOTKEY_RESUMED_STATUS: Final = "Recording resumed by the hotkey."
# D5 as amended 2026-09-28: a registration Windows refused, keyed by
# ``system_events.SystemPauseStatus`` field. Shown only when it failed.
SYSTEM_PAUSE_FAILED_LINES: Final[Mapping[str, str]] = {
    "suspend": (
        "Sleep pause may not work - Windows would not report sleep to Cliniko Scribe. Pause "
        "the recording before the computer sleeps."
    ),
    "lock": (
        "Lock pause unavailable - Windows would not report the screen locking. Pause the "
        "recording before you leave the computer."
    ),
}
# Task 7.3 (D8): a WARNING only — nothing is paused, blocked or changed.
NEW_CONSULTATION_WARNING_LINE: Final = (
    "Warning: this sounds like a new consultation (a goodbye, then a greeting). If the next "
    "patient is in, finish this recording first - nothing has been paused."
)


def hands_free_lines(hotkey: str, chord: str, spoken: str) -> list[str]:
    """The Session screen's hotkey and spoken-pause lines."""
    return [
        HOTKEY_LINES.get(hotkey, HOTKEY_LINES["not_set_up"]).format(chord=chord),
        SPOKEN_PAUSE_LINES.get(spoken, SPOKEN_PAUSE_LINES["idle"]),
    ]
CHROME_RECHECK_LINES: Final[Mapping[str, str]] = {
    "checking": "Checking the note with Cliniko again after Chrome reconnected...",
    "verified": "Cliniko verified the note again after Chrome reconnected.",
    "offline": (
        "Cliniko could not be reached after Chrome reconnected - writing to Cliniko stays "
        "blocked until it verifies the note."
    ),
    "refused": "Cliniko did not verify the note after Chrome reconnected: {reason}.",
    "clinic_gone": (
        "This recording's clinic is no longer set up - it cannot be written back to Cliniko."
    ),
}
# Why a command from Chrome was refused (D2: sent in ``state.last_refusal``,
# never as an error). Each names what to do next.
CHROME_REFUSALS: Final[Mapping[str, str]] = {
    "stale_state": (
        "The side panel was out of date - check the patient shown and press it again."
    ),
    "no_report": "Open the patient's treatment note in Cliniko first.",
    "target_mismatch": (
        "The side panel no longer matches the note on screen - check the patient and press "
        "Start again."
    ),
    "checking": "Still checking the note with Cliniko - wait a moment, then press Start.",
    "not_verified": "Cliniko did not verify this note: {reason}.",
    "session_active": "A recording is already in progress - finish it first.",
    "review_open": "Save or cancel the open note review on the Note tab to start.",
    "no_microphone": "Select an input device on the Microphone tab first.",
    "busy": "The app is still transcribing - wait for it to finish.",
    "session_changed": (
        "That recording has already ended or changed - the side panel shows the current one."
    ),
    "not_allowed_now": "That is not possible for this recording right now.",
    "report_mismatch": (
        "Open this recording's own treatment note in Cliniko to resume it."
    ),
    "pipe_down": (
        "Chrome is not connected - open this recording's own treatment note in Cliniko to "
        "resume it."
    ),
    "not_available": "That action is not available in this version.",
    # D5 as amended 2026-09-28 (codex round 51 PR-MED-300): every Resume —
    # and every Start, Chrome's and the desktop's (H1 rounds 53–54, MED-039 /
    # MED-052) — is refused between a lock and the next unlock; unlocking
    # resumes nothing.
    "locked": "The computer is locked - sign in, then press it again.",
    "lock_unknown": (
        "The computer was locked and Cliniko Scribe cannot confirm it is unlocked - lock it "
        "and sign in again (Windows key + L), then press it again."
    ),
    "failed": "It did not work - see the Session tab in Cliniko Scribe.",
    # Task 5.5 (D6): the banner's "Open for review".
    "review_in_progress": (
        "Save or cancel the note review open on the Note tab first, then open this recording."
    ),
    "cannot_open": (
        "Cliniko Scribe could not open that recording for review - see its Recovery tab."
    ),
}

# Task 5.2 (D1, D5): the Session screen's Discard asks once more.
DISCARD_CONFIRM_MESSAGE: Final = (
    "Discard this recording? This cannot be undone. Press Confirm discard to delete it."
)
# Task 5.3 (D6): why Start waits while a note review is open.
REVIEW_OPEN_START_HINT: Final = (
    "Save or cancel the open note review on the Note tab to start the next recording."
)

# Task 5.1 (D5): the desktop cue shown with every pause the rule makes (the
# status line and a window flash). Keyed by ``context_rules.PauseReason``.
PAUSE_CUES: Final[Mapping[str, str]] = {
    "note_changed": "Paused - the recording's Cliniko tab opened a different treatment note.",
    "left_note": "Paused - the recording's Cliniko tab left its treatment note.",
    "tab_closed": "Paused - the recording's Cliniko tab was closed.",
    "other_note": "Paused - another treatment note is open in Chrome.",
    "login": "Paused - Cliniko's login page is open in Chrome.",
    "pipe_lost": "Paused - Chrome disconnected from Cliniko Scribe.",
    "new_client": "Paused - Chrome reconnected to Cliniko Scribe.",
    "suspend": "Paused - the computer went to sleep.",
    "locked": "Paused - the computer was locked.",
    "hotkey": "Paused by the hotkey.",
    "spoken": "Paused - \"scribe pause\" was heard.",
}
PAUSE_CUE_LINKED_TAIL: Final = (
    " Resume once this recording's own treatment note is open in Cliniko, or use Finish "
    "or Discard."
)
PAUSE_CUE_UNLINKED_TAIL: Final = " Press Resume to carry on recording."
BLOCK_DESKTOP_LINE: Final = (
    "Chrome is blocked on this recording: resume it on its own treatment note, finish it or "
    "discard it."
)


def pause_cue_text(reason: str, *, linked: bool) -> str:
    """The desktop cue for a pause the rule made (plain text, no name)."""
    cue = PAUSE_CUES.get(reason, "Paused.")
    return cue + (PAUSE_CUE_LINKED_TAIL if linked else PAUSE_CUE_UNLINKED_TAIL)


def chrome_refusal_message(reason: str, note_refusal: NoteRefusal | None = None) -> str:
    """The plain line for a refused Chrome command (``reason`` is a code)."""
    template = CHROME_REFUSALS.get(reason, CHROME_REFUSALS["failed"])
    detail = note_refusal_line(note_refusal) if note_refusal is not None else "no reason given"
    return template.format(reason=detail)


@dataclass(frozen=True)
class ChromeView:
    """What the Session screen shows about the Chrome link (Task 4.5).
    ``link`` is ``off`` (no bridge), ``waiting``, ``connected`` or
    ``unavailable``. ``patient`` is a display string held in memory only."""

    link: str = "off"
    patient: str | None = None
    clinic: str | None = None
    recheck: str | None = None
    recheck_reason: NoteRefusal | None = None
    refusal: str | None = None
    # Phase 5: the linked live session's phase (``recording``, ``paused``,
    # ``finishing`` or ``queued``) and whether Chrome shows the block.
    phase: str | None = None
    blocked: bool = False
    # Phase 7 (D7, D8): the hotkey's status, the spoken pause's
    # (``idle``, ``on`` or ``unavailable``) and the new-consultation warning.
    hotkey: str = "not_set_up"
    hotkey_chord: str = CHORD_TEXT
    spoken_pause: str = "idle"
    new_consultation: bool = False
    # D5 as amended 2026-09-28: which system registrations Windows refused
    # (``suspend`` / ``lock``), in that order.
    system_pause_failed: tuple[str, ...] = ()


def _live_line(who: str, clinic: str, phase: str | None) -> str:
    if phase == "finishing":
        return f"Finishing {who} - {clinic}..."  # D6: the processing tail
    if phase == "queued":
        return f"Ready for review: {who} - {clinic}."
    return f"Recording for {who} - {clinic}."


def chrome_view_text(view: ChromeView) -> str:
    """The Session screen's Chrome lines; empty when there is no bridge."""
    if view.link == "off":
        return ""
    lines = [
        {
            "waiting": CHROME_WAITING_LINE,
            "connected": CHROME_CONNECTED_LINE,
            "unavailable": CHROME_UNAVAILABLE_LINE,
        }.get(view.link, CHROME_WAITING_LINE)
    ]
    if view.clinic is not None:
        who = view.patient if view.patient is not None else "a patient (name not verified)"
        lines.append(_live_line(who, view.clinic, view.phase))
    if view.blocked:
        lines.append(BLOCK_DESKTOP_LINE)
    if view.recheck is not None:
        reason = note_refusal_line(view.recheck_reason) if view.recheck_reason else ""
        lines.append(CHROME_RECHECK_LINES[view.recheck].format(reason=reason))
    lines.extend(hands_free_lines(view.hotkey, view.hotkey_chord, view.spoken_pause))
    lines.extend(
        SYSTEM_PAUSE_FAILED_LINES[key]
        for key in view.system_pause_failed
        if key in SYSTEM_PAUSE_FAILED_LINES
    )
    if view.new_consultation:
        lines.append(NEW_CONSULTATION_WARNING_LINE)
    if view.refusal is not None:
        lines.append(f"Refused from Chrome: {view.refusal}")
    return "\n".join(lines)


class SessionControllerLike(Protocol):
    """The controller surface the screens depend on (fakes in tests)."""

    @property
    def state(self) -> SessionState: ...

    @property
    def level(self) -> float: ...

    @property
    def session(self) -> RecordingSession | None: ...

    # Cliniko workflow safeguards plan Task 4.5 (D2, D7): the tracked
    # session's opaque reference, its recorded time (pauses excluded), and
    # its live transcriber's failure state — read by the Chrome bridge.
    @property
    def session_ref(self) -> str | None: ...

    @property
    def recorded_seconds(self) -> int: ...

    @property
    def live_failure(self) -> LiveFailure | None: ...

    # Task 7.2 (D7): whether a live transcriber is attached at all (with
    # ``live_failure``, the spoken pause's availability).
    @property
    def live_transcription_attached(self) -> bool: ...

    @property
    def generating(self) -> bool: ...

    # Task 5.3 (D2): a retired session removed outside the controller (the
    # Recovery list's Discard, the sweep) stops resolving by its reference.
    def forget_session_ref(self, session_id: str) -> None: ...

    # Task 5.5 (D2, D6): the Unreviewed banner names a session by its
    # reference; an indexed session found at app start is given one.
    def session_ref_for(self, session_id: str) -> str | None: ...

    def register_session_ref(self, session_id: str) -> str: ...

    def resolve_session_ref(self, session_ref: str) -> str | None: ...

    # Task 5.4 (D6, decided option (a)): reinstall a retired session as the
    # live QUEUED session for review; ``reader`` runs before it is installed.
    def adopt_queued[T](
        self, directory: Path, reader: Callable[[Path, SessionCrypto], T]
    ) -> tuple[RecordingSession, T]: ...

    # Cliniko workflow safeguards plan Task 3.3: consent is required on every
    # Start (Constraint 4); ``context`` None is an unlinked recording.
    def start(
        self,
        device_id: int,
        *,
        consent: ConsentAttestation,
        context: EncounterContext | None = None,
    ) -> RecordingSession: ...

    def pause(self) -> RecordingSession: ...

    def resume(self) -> RecordingSession: ...

    def finish(self) -> RecordingSession: ...

    def transcribe(
        self, transcriber: Callable[[Path, SessionCrypto], object]
    ) -> RecordingSession: ...

    def complete(self) -> RecordingSession: ...

    def complete_without_note(self, lease: GenerationLease) -> RecordingSession: ...

    def complete_deleting_saved_note(self) -> RecordingSession: ...

    def discard(self) -> RecordingSession: ...

    def active_session_ids(self) -> frozenset[str]: ...

    # Note-learning plan D2: the live worker's ownership handover to the
    # processing callable (inside ``transcribe``), and the factory the main
    # window registers once the live view exists.
    def claim_live_transcriber(self) -> LiveTranscriber | None: ...

    def set_live_transcriber_factory(
        self, factory: Callable[[], LiveTranscriber] | None
    ) -> None: ...

    # Practitioner-profile plan D15: True while the voice-enrolment activity
    # is held — the microphone screen keeps its idle monitor closed meanwhile.
    @property
    def enrolling(self) -> bool: ...

    # D15, the activity itself: the Practitioner tab acquires the lease before
    # the capture starts and releases it after its own result handler; the
    # main window registers the benchmark worker as the blocker the
    # controller cannot see for itself (Phase 3, Task 3.1/3.2 wiring).

    def begin_enrolment(self) -> EnrolmentLease: ...

    def end_enrolment(self, lease: EnrolmentLease) -> None: ...

    def set_enrolment_blocker(self, blocker: Callable[[], str | None] | None) -> None: ...

    # Task 6.3: the note-generation lease plus the lease-aware custody
    # coordinator the recovered path routes through (never raw
    # complete_session/discard_session/crypto.destroy calls from the UI).

    def begin_generation(self) -> GenerationLease: ...

    def end_generation(self, lease: GenerationLease) -> None: ...

    def reserved_session_ids(self) -> frozenset[str]: ...

    def custody_protected_ids(self) -> frozenset[str]: ...

    def complete_recovered(self, directory: Path, crypto: SessionCrypto) -> None: ...

    def discard_recovered(self, directory: Path, crypto: SessionCrypto | None) -> None: ...

    def destroy_recovered_crypto(self, crypto: SessionCrypto) -> None: ...

    # Task 7.2: the scoped, lease-aware custody access the live-path note
    # generation worker (compose) and the GUI-thread write both run through —
    # no raw directory/crypto accessors (round 25 LOW-002).
    def with_generation_custody[T](
        self, lease: GenerationLease, action: Callable[[Path, SessionCrypto], T]
    ) -> T: ...


# ---------------------------------------------------------------------------
# State-driven control enablement (session screen).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ControlSet:
    start: bool = False
    pause: bool = False
    resume: bool = False
    finish: bool = False
    discard: bool = False


_CONTROLS: dict[SessionState, ControlSet] = {
    SessionState.IDLE: ControlSet(start=True),
    SessionState.RECORDING: ControlSet(pause=True, finish=True, discard=True),
    SessionState.PAUSED: ControlSet(resume=True, finish=True, discard=True),
    # While PROCESSING a transcription run is (or is about to be) in
    # flight: everything stays disabled until it queues or fails
    # (PR-HIGH-006: never race Discard against an in-flight transcribe).
    SessionState.PROCESSING: ControlSet(),
    # Complete/Discard for a queued session live on the transcript view.
    # Cliniko workflow safeguards plan D6 (Task 5.3): Start for the NEXT
    # patient is offered here — it retires this session to the Unreviewed
    # section — unless its note review holds the generation lease, which the
    # Session screen and the Chrome bridge check beside this table.
    SessionState.QUEUED: ControlSet(start=True),
    SessionState.FAILED: ControlSet(discard=True),
    SessionState.WRITTEN: ControlSet(start=True),
    SessionState.DISCARDED: ControlSet(start=True),
    SessionState.EXPIRED: ControlSet(start=True),
}


def controls_for_state(state: SessionState) -> ControlSet:
    return _CONTROLS[state]


# ---------------------------------------------------------------------------
# Recovery screen model (Flow 3: list recoverable stores on disk).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecoverableSessionInfo:
    session_id: str
    directory: Path
    created_at: float | None  # POSIX seconds; None when unreadable
    store_finished: bool  # False -> UNFINISHED_STORE_WARNING must be shown
    has_audio: bool
    # Cliniko workflow safeguards plan Task 3.4 / D6: by STAT only — the
    # listing never decrypts anything (Critical Constraint 7). Whether a
    # present ``encounter.enc`` is LINKED is known only after the checkout
    # decrypts it.
    has_transcript: bool
    has_note: bool
    has_encounter: bool
    # Task 5.4 (D6): when the sweep will first treat it as expired — THE
    # sweep's own timestamp derivation (``session_expires_at``), from the
    # header and file times only.
    expires_at: float | None = None


def list_recoverable_sessions(
    root: Path, active_session_ids: frozenset[str] = frozenset()
) -> list[RecoverableSessionInfo]:
    """Session dirs with live DPAPI custody, excluding the active session.

    Mirrors the sweep's discipline: only well-formed session-id directory
    names are considered, and nothing here deletes anything. A directory
    whose key blob cannot be statted is listed conservatively (the sweep,
    not the UI, decides orphan GC).
    """
    infos: list[RecoverableSessionInfo] = []
    if not root.is_dir():
        return infos
    now = time.time()
    for child in sorted(root.iterdir()):
        if not child.is_dir() or not _SESSION_ID_RE.fullmatch(child.name):
            continue
        if child.name in active_session_ids:
            continue
        key_path = child / KEY_FILENAME
        key_mtime: float | None = None
        try:
            key_stat = key_path.stat()
            if key_blob_is_dead(key_stat.st_size):
                # Cryptographically dead (zero-length/TRUNCATED — the same
                # deadness definition custody and the sweep use, round 42
                # LOW-004); the sweep will GC it. Listing it would only
                # offer a Resume that must fail with KeyCustodyError.
                continue
            key_mtime = key_stat.st_mtime
        except FileNotFoundError:
            continue  # orphan dir; sweep territory
        except OSError:
            pass  # transient stat trouble: list conservatively
        audio_path = child / AUDIO_FILENAME
        has_audio = audio_path.is_file()
        created_at: float | None = None
        store_finished = False
        if has_audio:
            try:
                created_at = read_store_header(audio_path).created_at
            except (SessionStoreError, OSError):
                created_at = None
            try:
                store_finished = store_has_footer(audio_path)
            except (SessionStoreError, OSError):
                store_finished = False
        # PR round 18: the 24 h rule applies to the LISTING too, not only the
        # sweep — a session whose age can be ESTABLISHED past its window is
        # not offered for recovery. The trust core is SHARED with the sweep
        # (round 42 MED-009: earliest_trusted_timestamp), so the two can
        # never disagree about what "trusted" means — including the
        # clock-skew tolerance that keeps a just-created session visible here
        # (round 48 HIGH-001). Readable-but-untrusted values fail closed (not
        # listed). Round 47 PR-LOW-001 — the branch the old "never offer
        # recovery past its window" absolute talked over: when NEITHER
        # timestamp is readable, `readable` is empty, so both tests below are
        # skipped and the session IS listed regardless of age. That is
        # deliberate (the sweep, not the UI, owns orphan/expiry decisions),
        # and it means the listing is conservative, not a window guarantee.
        readable = [t for t in (created_at, key_mtime) if t is not None]
        earliest = earliest_trusted_timestamp(readable, now)
        if earliest is not None:
            if now - earliest >= RECOVERY_WINDOW.total_seconds():
                continue  # expired; the sweep destroys it
        elif readable:
            continue  # untrusted timestamps: fail closed, sweep decides
        infos.append(
            RecoverableSessionInfo(
                session_id=child.name,
                directory=child,
                created_at=created_at,
                store_finished=store_finished,
                has_audio=has_audio,
                has_transcript=(child / TRANSCRIPT_FILENAME).is_file(),
                has_note=(child / NOTE_FILENAME).is_file(),
                has_encounter=(child / ENCOUNTER_FILENAME).is_file(),
                expires_at=session_expires_at(child, now),
            )
        )
    return infos


# ---------------------------------------------------------------------------
# The Unreviewed section (Cliniko workflow safeguards plan D6, Task 5.4).
# ---------------------------------------------------------------------------

UNREVIEWED_HEADER: Final = "Unreviewed recordings - open one to review its note:"
RECOVERABLE_HEADER: Final = "Recoverable sessions (24-hour window):"
OPEN_FOR_REVIEW_LABEL: Final = "Open for review"
REVIEW_OPEN_BUSY_LINE: Final = (
    "A note review is open - save or cancel it before opening another recording."
)
REVIEW_OPEN_RECOVERY_BUSY_LINE: Final = (
    "A recovery is still transcribing - wait for it to finish before opening another "
    "recording."
)
GENERATE_NOTE_LABEL: Final = "Generate note"
REGENERATE_NOTE_LABEL: Final = "Regenerate (replaces the saved note)"
# D6: warn this long before a session's 24-hour window closes.
EXPIRY_WARNING_SECONDS: Final = 2 * 3600
# The on-close list is shown on a first close; a second close inside this
# window quits (a modal box would block every close path, tests included).
CLOSE_CONFIRM_SECONDS: Final = 10.0
SAVED_NOTE_LINE: Final = (
    "Saved note - shown as it was saved. Copy it here; Complete, or Regenerate "
    "(replaces the saved note), on the Transcript screen."
)
SAVED_NOTE_CONFIG_CHANGED_LINE: Final = (
    "This note was saved under a different note configuration from the one now in "
    "use, so it is shown read-only as it was saved. Regenerate on the Transcript "
    "screen to write it under the current configuration."
)
SAVED_NOTE_CONFIG_UNREADABLE_LINE: Final = (
    "The note configuration could not be loaded, so this saved note is shown "
    "read-only as it was saved."
)
_REVIEW_REFUSALS: Final[dict[str, str]] = {
    "no_transcript": "it has no transcript - use Resume processing instead",
    "key_unavailable": "its session key could not be unlocked",
    "consent_unavailable": (
        "its consent record is missing or damaged, so it cannot be reviewed - discard it"
    ),
    "transcript": "its transcript could not be read",
    "note": (
        "its saved note could not be verified against the transcript - the note was "
        "not replaced; discard the session or contact support"
    ),
    "unreadable": "its transcript or saved note could not be read",
}


@dataclass(frozen=True)
class ReviewOpening:
    """What "Open for review" reads under the adopted session's key: the
    transcript and, when ``note.enc`` exists, the SAVED note verified by
    ``session_store.read_note`` (D6). Display only; never persisted here."""

    document: TranscriptDocument
    note: GeneratedNote | None


class ReviewReadError(Exception):
    """``read_for_review`` could not read one artifact: ``kind`` is
    ``transcript`` or ``note``. The message never carries clinical text."""

    def __init__(self, kind: Literal["transcript", "note"]) -> None:
        super().__init__(f"the {kind} could not be read")
        self.kind = kind


def read_for_review(directory: Path, crypto: SessionCrypto) -> ReviewOpening:
    """The reader ``SessionController.adopt_queued`` runs before it installs
    anything: a note that fails verification refuses the opening (named on
    the row), never a silent regenerate or overwrite (D6)."""
    try:
        document = read_transcript(directory, crypto)
    except Exception as exc:
        raise ReviewReadError("transcript") from exc
    if not (directory / NOTE_FILENAME).is_file():
        return ReviewOpening(document, None)
    try:
        note = read_note(directory, crypto)
    except Exception as exc:
        raise ReviewReadError("note") from exc
    return ReviewOpening(document, note)


def review_refusal_line(reason: str, cause: BaseException | None = None) -> str:
    """The Recovery row's named refusal for ``ReviewOpenRefused``: the
    reader's own ``ReviewReadError`` kind when that is the cause."""
    if reason == "unreadable" and isinstance(cause, ReviewReadError):
        reason = cause.kind
    detail = _REVIEW_REFUSALS.get(reason, _REVIEW_REFUSALS["unreadable"])
    return f"This recording cannot be opened for review: {detail}."


def saved_note_line(note: GeneratedNote, config_loader: Callable[[], NoteConfig]) -> str:
    """The saved note's info line (D6): whether it matches the note config
    now in use. Either way the saved note is shown as it was saved."""
    try:
        config = config_loader()
    except Exception:  # noqa: BLE001 - runs after adoption: never raise (round 32 LOW-025)
        return SAVED_NOTE_CONFIG_UNREADABLE_LINE
    if config.config_digest() != note.config_digest:
        return SAVED_NOTE_CONFIG_CHANGED_LINE
    return SAVED_NOTE_LINE


def _clock_text(timestamp: float) -> str:
    """Local wall-clock time — the practitioner acts on it."""
    return datetime.fromtimestamp(timestamp).strftime("%H:%M on %d %b")


def unreviewed_row_text(info: RecoverableSessionInfo, now: float) -> str:
    """An Unreviewed row: stat-only facts (never a clinic or patient) plus
    when it expires."""
    parts = [f"Recording {info.session_id[:8]}..."]
    parts.append("note saved" if info.has_note else "no note yet")
    parts.append(recovery_link_line(info.has_encounter))
    # The binding Step-10 note, as the recoverable list's rows carry it
    # (codex round 34 PR-MED-190).
    if not info.has_audio:
        parts.append("no audio recorded")
    elif not info.store_finished:
        parts.append("did not finish cleanly")
    if info.expires_at is not None:
        parts.append(expiry_text(info.expires_at, now))
    return " - ".join(parts)


def expiry_text(expires_at: float, now: float) -> str:
    if expires_at <= now:
        return "expiring now"
    return f"expires {_clock_text(expires_at)}"


def expiring_soon(infos: Sequence[RecoverableSessionInfo], now: float) -> list[str]:
    """Session ids inside D6's 2-hour warning window."""
    return [
        info.session_id
        for info in infos
        if info.expires_at is not None and info.expires_at - now <= EXPIRY_WARNING_SECONDS
    ]


def expiry_warning_line(count: int) -> str:
    if count == 1:
        return (
            "1 unreviewed recording expires within 2 hours - open it and Complete it, or "
            "it is deleted when its 24-hour window closes."
        )
    return (
        f"{count} unreviewed recordings expire within 2 hours - open and Complete them, "
        "or they are deleted when their 24-hour windows close."
    )


def close_expiry_message(entries: Sequence[tuple[str, float | None]], now: float) -> str:
    """D6's on-close list: each unreviewed recording and when it expires.
    Ids are shortened; no clinic or patient appears."""
    lines = [
        f"Recording {session_id[:8]}...: "
        + (expiry_text(expires_at, now) if expires_at is not None else "expiry unknown")
        for session_id, expires_at in entries
    ]
    return (
        "Unreviewed recordings stay on this computer until their 24-hour window closes. "
        + "; ".join(lines)
        + f". Close again within {int(CLOSE_CONFIRM_SECONDS)} seconds to quit."
    )


def reconstruct_reminder_entries(
    infos: Sequence[RecoverableSessionInfo],
    *,
    unwrap: Callable[[Path], SessionCrypto] | None = None,
    read_record: Callable[[Path, SessionCrypto, str], EncounterRecord] | None = None,
) -> list[ReminderEntry]:
    """Task 5.5 (D6): rebuild the Unreviewed reminder index at APP START —
    the ONE path besides a checkout or an Unreviewed recording opened for
    review that decrypts ``encounter.enc``, once
    per session on disk that has a transcript and an encounter record. The
    key is unwrapped for that one read and destroyed at once; only the ids
    go on (``ReminderEntry``), never a name. A session whose key or record
    cannot be read is skipped (it stays on the Unreviewed list, where opening
    it names why). Returned OLDEST first, so adding them in order leaves the
    index newest first. The two readers resolve at call time (the spy
    test's seam)."""
    unwrap_key = unwrap if unwrap is not None else unwrap_key_from_file
    read = read_record if read_record is not None else read_encounter_record
    entries: list[tuple[float, ReminderEntry]] = []
    for info in infos:
        if not (info.has_transcript and info.has_encounter):
            continue
        try:
            crypto = unwrap_key(info.directory)
        except Exception:  # noqa: BLE001 - unreadable custody: not indexed
            continue
        try:
            record = read(info.directory, crypto, info.session_id)
        except Exception:  # noqa: BLE001 - EncounterUnavailable or worse: not indexed
            continue
        finally:
            crypto.destroy()
        context = record.context
        if context is None:
            continue
        order = info.expires_at if info.expires_at is not None else float("-inf")
        entries.append(
            (order, ReminderEntry(context.clinic_id, context.treatment_note_id, info.session_id))
        )
    entries.sort(key=lambda pair: pair[0])
    return [entry for _, entry in entries]


# ---------------------------------------------------------------------------
# Transcript rendering (display only — never persisted, never logged).
# ---------------------------------------------------------------------------


def format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


def _segment_span(segment: TranscriptSegment) -> str:
    """The ``[mm:ss-mm:ss]`` span — ONE implementation, shared by the final
    document rendering and the live view (Task 1.4), so the two can never
    drift apart."""
    return (
        f"[{format_timestamp(segment.start_seconds)}"
        f"-{format_timestamp(segment.end_seconds)}]"
    )


def _segment_words(segment: TranscriptSegment) -> str:
    """The segment's words with the ``[word?]`` uncertainty marks — the same
    one implementation for both renderings."""
    return " ".join(
        f"[{word.word_text}?]" if word.uncertain else word.word_text
        for word in segment.transcript_words
    )


def format_transcript_text(document: TranscriptDocument) -> str:
    """Render a transcript for the inspection view: speaker labels visible
    on every segment, uncertain words marked as ``[word?]``."""
    lines: list[str] = []
    for segment in document.transcript_segments:
        lines.append(f"{_segment_span(segment)} {segment.speaker}: {_segment_words(segment)}")
    if not lines:
        return "(no speech detected)"
    return "\n".join(lines)


def format_live_segments(segments: Sequence[TranscriptSegment]) -> list[str]:
    """Render ONE live window's segments for the append-only live view
    (Task 1.4): the same span and ``[word?]`` marks as the final rendering,
    but NO speaker label — every live-posted segment carries
    ``LIVE_SPEAKER_PENDING`` because the speaker pass runs only at the drain,
    so a cluster name here would be a claim the app has not made yet."""
    return [f"{_segment_span(segment)} {_segment_words(segment)}" for segment in segments]


def speaker_quotations(document: TranscriptDocument, *, max_chars: int = 90) -> dict[str, str]:
    """A representative truncated quote per speaker cluster, for the Task 7.5
    role-confirmation control — so the clinician's choice is informed.

    Each speaker's FIRST non-empty utterance, in appearance order. Quoting
    here is deliberate: ``SpeakerEvidence`` carries no text (a role
    preselection is logged/rendered and clinical text must stay out of logs),
    but this screen already holds and displays the transcript, so it quotes
    directly (the plan records exactly this split). Display only."""
    quotes: dict[str, str] = {}
    for segment in document.transcript_segments:
        if segment.speaker in quotes:
            continue
        text = " ".join(word.word_text for word in segment.transcript_words).strip()
        if not text:
            continue
        if len(text) > max_chars:
            text = text[:max_chars].rstrip() + "..."
        quotes[segment.speaker] = text
    return quotes


# ---------------------------------------------------------------------------
# Note review view logic (Tasks 7.1 / 7.4) — pure, offscreen-testable. The
# Note tab widget stays thin: rendering, warning grouping, and Complete
# gating all live here. Nothing below logs or persists clinical text.
# ---------------------------------------------------------------------------

# Task 7.1 / 9.1: the note is the RATIFIED copyable surface. The Note tab
# binds its copy affordance to THIS recorded decision, never unconditionally.
# Practitioner decision 2026-09-27 (Cliniko workflow safeguards plan D12,
# Task 1.4): copy is ENABLED without waiting for the Task 9.1 run, which
# becomes a quality measurement rather than an enablement gate. Ratification
# still gates every copy (`ui/note.py` `_copy_ready`: every proposal decided,
# no blocking error, every warning acknowledged, the note saved), re-checked
# at click time. The transcript stays display-only ALWAYS, regardless of this
# flag (Critical Constraint).
COPY_TO_CLINIKO_ENABLED: Final[bool] = True

# Task 8.2 (Cliniko workflow safeguards plan; practitioner decision
# 2026-09-27, option (a) "keep it out of history and sync"): every copy of
# note text — the Copy button and a copy of the ratified note panel's
# selection (`ui/note.py` `_place_note_text`) — places it together with three
# registered Windows clipboard formats.
# Windows clipboard history and cloud clipboard sync honour them, so the
# copied note is neither kept in history nor uploaded. They do NOT stop any
# same-user process reading the current clipboard (threat-model boundary 2),
# a third-party clipboard manager may ignore
# `ExcludeClipboardContentFromMonitorProcessing`, the note stays on the
# clipboard until something replaces it, and nothing is ever cleared. The
# exclusion format's PRESENCE is the signal; it carries the same zero DWORD
# as the other two so that every format holds a non-empty block. Off Windows
# the formats mean nothing and the text is still what a paste yields.
_CLIPBOARD_DWORD_ZERO: Final[bytes] = (0).to_bytes(4, "little")
CLIPBOARD_EXCLUSION_FORMATS: Final[tuple[tuple[str, bytes], ...]] = (
    ("ExcludeClipboardContentFromMonitorProcessing", _CLIPBOARD_DWORD_ZERO),
    ("CanIncludeInClipboardHistory", _CLIPBOARD_DWORD_ZERO),
    ("CanUploadToCloudClipboard", _CLIPBOARD_DWORD_ZERO),
)


def clipboard_mime_formats() -> dict[str, bytes]:
    """Task 8.2: the registered Windows clipboard formats a copied note
    carries, name -> payload (see `CLIPBOARD_EXCLUSION_FORMATS`). Qt-free;
    ``ui/note.py`` `_copy_note` sets each under `windows_clipboard_mime_type`."""
    return dict(CLIPBOARD_EXCLUSION_FORMATS)


def windows_clipboard_mime_type(format_name: str) -> str:
    """The MIME type under which Qt's Windows clipboard places a REGISTERED
    clipboard format of this name (Qt's `application/x-qt-windows-mime`
    convention)."""
    return f'application/x-qt-windows-mime;value="{format_name}"'

# Task 7.7 (round 45 MED-001) — the third clause of the consent Critical
# Constraint: "the note view renders it as a manual reminder only". The first
# two clauses are structural (`TemplateProfile` refuses attestation-typed
# targets; no proposal path reaches one), and they are exactly WHY this text
# is needed: because the app deliberately never ticks Informed Consent, the
# clinician has to be told to tick it themselves.
#
# Deliberately NOT a warning code: a `NoteWarning` would be acknowledgeable —
# i.e. suppressible — and would need a per-note emitter, whereas this is a
# standing statement about what the app never does. Deliberately
# UNCONDITIONAL rather than shown only when the bound profile carries an
# attestation target: a config-conditional reminder would silently vanish for
# a template that has no such target, and the constraint is categorical.
#
# TWO PRECISION REQUIREMENTS, both from round 47 PR-MED-001 (the cross-family
# peer's audit of the round-45 wording, which got both wrong):
#
# 1. Name the ATTESTATION CHECKBOX, not "Informed Consent" loosely. What is
#    structurally unreachable is an `attestation_checkbox` TARGET
#    (`TemplateProfile._check_profile`) — NOT all consent-related note text:
#    `DEFAULT_SECTION_CUES["consent"]` routes consent speech into the
#    canonical `consent` section, `format_note_body` renders it, and another
#    practitioner's profile may legitimately map `consent` to a FREE-TEXT
#    target. Saying the app "never writes Informed Consent" is therefore
#    false in the direction that matters least but confusing in the direction
#    that matters most.
# 2. State the FULL predicate the clinician is about to attest to. The real
#    checkbox asserts that the working diagnosis, benefits and risks were
#    EXPLAINED *and* that consent was GAINED (plan Critical Constraint,
#    practitioner-ratified 2026-08-04). The round-45 wording asked them to
#    confirm consent alone and then invited a tick — i.e. invited a stronger
#    claim than it asked them to verify, which is the precise failure this
#    whole constraint exists to prevent.
CONSENT_MANUAL_REMINDER: Final[str] = (
    "This app never ticks, writes, or proposes Cliniko's Informed Consent "
    "attestation checkbox - it is a claim about a conversation, not a "
    "finding. Tick it yourself, and only once its full attestation holds: "
    "that you explained the working diagnosis, the benefits and the risks, "
    "AND that consent was gained. (A Consent section may still appear in the "
    "note below, quoting what was said - that is not the attestation.)"
)

# The section titles, the provenance labels, the D5 pre-filled mark and the
# rendering itself live in ``note`` since the note-learning plan's Phase 3
# (Task 3.2: ONE rendering path shared by display, ``note.enc`` reload and
# Copy); this module re-exports them so the screens and tests keep one
# import surface.
@dataclass(frozen=True)
class RenderedAssertion:
    """One assertion rendered as ONE bullet — never assembled prose (plan
    Critical Constraint: assertions render on hard boundaries).
    ``provenance_label`` already carries the pre-filled mark when
    ``prefilled`` is True (``assertion_label``)."""

    assertion_id: str
    provenance: str
    provenance_label: str
    text: str
    prefilled: bool = False


@dataclass(frozen=True)
class RenderedSection:
    section_key: NoteSectionKey
    title: str
    assertions: tuple[RenderedAssertion, ...]


def format_note_body(note: GeneratedNote) -> str:
    """The composed note as display text under the note's OWN ``style`` —
    ``note.render_note(note, note.style)``, THE one rendering path (D7):
    the Note tab's body, a reloaded ``note.enc`` and Copy all read this, so
    display, reload and Copy cannot disagree. This is the copyable surface
    (gated on the recorded copy flag and full ratification — ``ui/note.py``
    ``_copy_ready``); it is display text only, never
    persisted or logged here."""
    return render_note(note, note.style)


def render_note_sections(note: GeneratedNote) -> tuple[RenderedSection, ...]:
    """The note's populated sections in canonical order, each assertion one
    bullet with its provenance. ``note.note_sections`` is already unique and
    canonically ordered (GeneratedNote validator), so this is presentation
    only — no reordering, no joining."""
    rendered: list[RenderedSection] = []
    for section in note.note_sections:
        rendered.append(
            RenderedSection(
                section_key=section.section_key,
                title=SECTION_TITLES[section.section_key],
                assertions=tuple(
                    RenderedAssertion(
                        assertion_id=assertion.assertion_id,
                        provenance=assertion.provenance,
                        provenance_label=assertion_label(assertion),
                        text=assertion.text,
                        prefilled=is_prefilled(assertion),
                    )
                    for assertion in section.note_assertions
                ),
            )
        )
    return tuple(rendered)


@dataclass(frozen=True)
class RenderedProposal:
    """A proposal as its confirm/decline row shows it: the EXACT insertable
    text (never a summary — the digest is computed from what is rendered),
    plus provenance and a plain-English attribution."""

    proposal_id: str
    section_key: NoteSectionKey
    section_title: str
    provenance: str
    provenance_label: str
    excerpt: str
    attribution: str


def render_proposal(proposal: NoteProposal) -> RenderedProposal:
    """Render one proposal's confirm/decline row. Autofill attribution reuses
    ``format_timestamp`` for the trigger time (plan Task 7.4)."""
    if proposal.provenance == "autofill" and proposal.trigger_start_seconds is not None:
        attribution = f"Autofill triggered at {format_timestamp(proposal.trigger_start_seconds)}"
    elif proposal.provenance == "prefill":
        if proposal.trigger_start_seconds is not None:
            attribution = (
                f"Prefill region detected at "
                f"{format_timestamp(proposal.trigger_start_seconds)}"
            )
        else:
            attribution = "Prefill seed (region chosen manually)"
    else:
        attribution = provenance_label(proposal.provenance)
    return RenderedProposal(
        proposal_id=proposal.proposal_id,
        section_key=proposal.section_key,
        section_title=SECTION_TITLES[proposal.section_key],
        provenance=proposal.provenance,
        provenance_label=provenance_label(proposal.provenance),
        excerpt=proposal.note_excerpt,
        attribution=attribution,
    )


# --- warning grouping (fatigue is this phase's top risk) --------------------


@dataclass(frozen=True)
class WarningCopy:
    """Plain-clinical-English copy for one warning code: what it means,
    whether it blocks (and which action), and how to clear it."""

    title: str
    blocks: str | None  # the action this error blocks; None for review codes
    clear_hint: str


# One entry per registered note.NOTE_WARNING_SEVERITY code. Blocking `error`
# codes NAME the action they block and the way to clear it (plan Task 7.1);
# `review` codes carry blocks=None and an acknowledge-after-checking hint.
WARNING_COPY: Final[Mapping[str, WarningCopy]] = {
    # Round 35 PR-MED-003: base-assertion errors (source_coords_invalid /
    # reconstruction_mismatch) attach to provider transcript lines that have
    # NO proposal row and cannot be retracted — their only clear-path is the
    # non-destructive "Cancel review and regenerate" control.
    "source_coords_invalid": WarningCopy(
        "A quoted line does not line up with the recording",
        "saving the note",
        "Use Cancel review and regenerate to rebuild the note.",
    ),
    "reconstruction_mismatch": WarningCopy(
        "A quoted line does not match the transcript exactly",
        "saving the note",
        "Use Cancel review and regenerate to rebuild the note.",
    ),
    "contradiction": WarningCopy(
        "A confirmed line contradicts the transcript",
        "saving the note",
        "Decline the contradicting proposed line, or Cancel review and regenerate.",
    ),
    "unconfirmed_proposal": WarningCopy(
        "A proposed line has not been confirmed or declined",
        "saving the note and completing",
        "Confirm or decline every proposed line below.",
    ),
    "autofill_trigger_absent": WarningCopy(
        "A confirmed autofill line no longer matches its trigger",
        "saving the note",
        "Decline the affected proposed line, or Cancel review and regenerate.",
    ),
    "role_unconfirmed": WarningCopy(
        "The clinician speaker is not confirmed for a clinician-owned section",
        "saving the note",
        "Cancel review, confirm the clinician on the Transcript screen, then regenerate.",
    ),
    "low_confidence_source": WarningCopy(
        "A quoted line includes a word the transcription was unsure about",
        None,
        "Check it against the transcript beside the note, then acknowledge.",
    ),
    "contradiction_low_confidence": WarningCopy(
        "A possible contradiction rests on an uncertain transcript word",
        None,
        "Check it against the transcript, then acknowledge.",
    ),
    "dose_mismatch": WarningCopy(
        "Two dose mentions differ and could not be confirmed as the same",
        None,
        "Check the doses against the transcript, then acknowledge.",
    ),
    # Round 59 PR-LOW-001: SOURCE-NEUTRAL on purpose. This code serves TWO
    # emitter populations - an authored line against the transcript, and two
    # authored lines against each other (no transcript evidence at all,
    # `source_coords is None`). A title that says "from the transcript" claims
    # a comparison the checker never made for the second population, and
    # could misdirect the acknowledgement of a wrong-side line.
    "laterality_mismatch": WarningCopy(
        "The note names different sides for the same body area",
        None,
        "Check the side against the transcript beside the note, then acknowledge.",
    ),
    # Schema v2 (note-learning plan D4): a typed ``clinician`` line draws this
    # review too, so the title names all three authored provenances.
    "clinician_asserted": WarningCopy(
        "A clinician-authored line was added (autofill, prefill or typed)",
        None,
        "Confirm the wording is right for this patient, then acknowledge.",
    ),
    # Round 45 MED-002: the hint must name only affordances that EXIST. It
    # previously sent the clinician to an "Unmapped content" surface — the
    # round-2 mapped-OUTPUT target, which is Phase 4's and is not built in
    # 3A, so there is no such heading anywhere in this app. The section is
    # still rendered in the note body (`format_note_body` emits every
    # populated canonical section); what the chosen template lacks is a
    # FIELD to carry it.
    "mapping_drop": WarningCopy(
        "A populated section has no place in the chosen template",
        None,
        "The section is still shown in the note below, but the chosen "
        "template has no field for it - carry it across by hand if it is "
        "needed, then acknowledge.",
    ),
    # Practitioner-profile plan Task 5.1b: a line the clinician REMOVED during
    # review raises this too (its words are no longer carried by any
    # assertion) — the copy names that case so the acknowledgement reads
    # right; review severity, never a block (D14).
    "high_risk_omission": WarningCopy(
        "A number, name or medication the clinician said is not in the note",
        None,
        "Check the transcript beside the note (a line you removed can raise this too), "
        "then acknowledge.",
    ),
    # Note-learning plan Task 4.2 (D6, C8): the prose the language model
    # wrote for a section did not pass the fidelity check, so that section is
    # shown as Clean clinical — its confirmed lines, unchanged. The copy names
    # the fallback the practitioner is looking at; the check is a gate, not a
    # certificate, and nothing here reproduces the refused wording.
    "style_fallback": WarningCopy(
        "A section is shown as Clean clinical because its prose did not pass "
        "the fidelity check",
        None,
        "Read that section as shown (its confirmed lines, unchanged), then acknowledge.",
    ),
}


@dataclass(frozen=True)
class WarningGroup:
    """One code's warnings, counted and summarised (never one row per
    finding — that is the fatigue the plan warns about)."""

    code: str
    severity: str
    count: int
    title: str
    blocks: str | None
    clear_hint: str
    section_keys: tuple[NoteSectionKey, ...]


@dataclass(frozen=True)
class WarningSummary:
    """Blocking errors and review warnings, grouped and kept DISTINCT (plan
    Task 7.1: blocking errors presented distinctly from review warnings)."""

    blocking: tuple[WarningGroup, ...] = ()
    review: tuple[WarningGroup, ...] = ()

    @property
    def blocking_count(self) -> int:
        return sum(group.count for group in self.blocking)

    @property
    def review_count(self) -> int:
        return sum(group.count for group in self.review)


def _fallback_copy(code: str) -> WarningCopy:
    return WarningCopy(code.replace("_", " "), None, "Review this finding.")


def summarise_warnings(warnings: Sequence[NoteWarning]) -> WarningSummary:
    """Group warnings by code — blocking `error` codes apart from `review`
    codes — with counts and the touched sections, so the Note tab summarises
    rather than lists a flat wall of findings (plan Task 7.1)."""
    order: list[str] = []
    by_code: dict[str, list[NoteWarning]] = {}
    for warning in warnings:
        if warning.note_warning_code not in by_code:
            order.append(warning.note_warning_code)
            by_code[warning.note_warning_code] = []
        by_code[warning.note_warning_code].append(warning)
    blocking: list[WarningGroup] = []
    review: list[WarningGroup] = []
    for code in order:
        found = by_code[code]
        copy = WARNING_COPY.get(code) or _fallback_copy(code)
        sections = tuple(
            dict.fromkeys(key for w in found if (key := w.section_key) is not None)
        )
        group = WarningGroup(
            code=code,
            severity=found[0].severity,
            count=len(found),
            title=copy.title,
            blocks=copy.blocks,
            clear_hint=copy.clear_hint,
            section_keys=sections,
        )
        (blocking if found[0].severity == "error" else review).append(group)
    return WarningSummary(blocking=tuple(blocking), review=tuple(review))


# --- Complete gating (Flow 2) ----------------------------------------------


@dataclass(frozen=True)
class NoteReviewState:
    """What the Transcript screen needs to gate Complete (Flow 2). Complete
    is refused while generating, while any proposal is unconfirmed, while an
    `error` is unresolved, or while a `review` warning is unacknowledged.

    ``has_note`` is False when the clinician generated no note at all —
    transcript-only Complete stays available, unchanged from Phase 2."""

    generating: bool = False
    has_note: bool = False
    unconfirmed_proposals: int = 0
    blocking_errors: int = 0
    unacknowledged_reviews: int = 0
    note_saved: bool = False


def complete_block_reason(state: NoteReviewState) -> str | None:
    """The reason Complete is blocked in ``state``, or None when it may
    proceed. Drives the Transcript screen's Complete enablement AND its
    message — a blocked Complete says why and how to clear it."""
    if state.generating:
        return "A note is being reviewed - save it or delete it before completing."
    if not state.has_note:
        return None
    if state.unconfirmed_proposals > 0:
        return "Confirm or decline every proposed line before completing."
    if state.blocking_errors > 0:
        return "Resolve the blocking note warnings before completing."
    if not state.note_saved:
        return "Save the note (or delete it) before completing."
    if state.unacknowledged_reviews > 0:
        return "Acknowledge the note review warnings before completing."
    return None


# --- read-only config viewer report (Task 7.4) -----------------------------


def config_report_lines(
    config: NoteConfig, template_profile_id: str | None = None
) -> list[str]:
    """A read-only summary of the config that drove (or would drive) a note:
    which template profile is in use, how many autofill rules and prefill
    regions are configured, and which populated-capable canonical sections
    the selected profile would drop.

    Counts and canonical section titles are non-clinical by construction. The
    one USER-AUTHORED field here is the profile's ``display_name``, and round
    47 PR-LOW-002 is why that is worth saying: config is only INTENDED to be
    non-patient boilerplate, and ``note_config`` validates its structure, not
    its meaning — so this is safe to DISPLAY on the local review surface, and
    is not thereby log-safe. (The config editor UI itself is deferred
    post-3B.)"""
    lines = [
        f"Template profiles configured: {len(config.template_profiles)}",
        f"Autofill rules: {len(config.autofill_rules)}",
        f"Prefill regions: {len(config.prefill_templates)}",
    ]
    selected = None
    if template_profile_id is not None:
        for profile in config.template_profiles:
            if profile.template_profile_id == template_profile_id:
                selected = profile
                break
    elif len(config.template_profiles) == 1:
        selected = config.template_profiles[0]
    if selected is not None:
        lines.append(f"Active template: {selected.display_name}")
        dropped = selected.unmapped_section_keys()
        if dropped:
            titles = ", ".join(SECTION_TITLES[key] for key in dropped)
            lines.append(f"Sections with no template mapping: {titles}")
    return lines


# --- generation worker factory (Task 7.4) ----------------------------------


@dataclass(frozen=True)
class NoteGenerationResult:
    """The compose worker's output: the unchecked draft, the resolved config
    it was composed under, and the on-disk transcript it was composed from.

    Carrying all three keeps the review DIGEST-CONSISTENT: ``finalise_note``
    re-checks the note against this exact document and config (never a
    separately-loaded copy that could round-trip to a different digest), and
    the GUI-thread write reuses the same config. The document is also the
    Task 7.6 transcript shown beside the note."""

    draft: NoteDraft
    config: NoteConfig
    document: TranscriptDocument
    # Note-learning plan Phase 2: one-line notes about how the draft was
    # composed that the Note tab shows beside the config report (today: a
    # learned-rule sidecar that could not be read, so every learned rule
    # proposed). Display text; never clinical content.
    notes: tuple[str, ...] = ()


# --- review edits (practitioner-profile plan Phase 5, D14) ------------------


def working_draft(
    draft: NoteDraft,
    *,
    removed: Collection[str],
    additions: Sequence[NoteAssertion],
) -> NoteDraft:
    """The draft the Note tab finalises: the generated draft with the
    assertions in ``removed`` filtered out and ``additions`` appended to
    their sections, sections in canonical order (D14). Every check then runs
    over the EDITED note exactly as over the generated one — reconstruction,
    contradiction, provenance, omission — because ``finalise_note`` takes a
    draft and nothing else changes. The proposals AND the config decisions
    the emitter minted travel unchanged, so the resolution evidence keeps
    matching. Validated on construction: a duplicate assertion id or a
    rule-authored (autofill / prefill) addition is refused by ``NoteDraft``
    itself; a quoted line and a typed ``clinician`` line (schema v2, D4) are
    the admitted additions."""
    grouped: dict[NoteSectionKey, list[NoteAssertion]] = {}
    for section in draft.note_sections:
        kept = [a for a in section.note_assertions if a.assertion_id not in removed]
        if kept:
            grouped[section.section_key] = kept
    for assertion in additions:
        grouped.setdefault(assertion.section_key, []).append(assertion)
    return NoteDraft(
        session_id=draft.session_id,
        template_profile_id=draft.template_profile_id,
        provider_name=draft.provider_name,
        clinician_speaker=draft.clinician_speaker,
        transcript_digest=draft.transcript_digest,
        config_digest=draft.config_digest,
        note_sections=tuple(
            GeneratedSection(section_key=key, note_assertions=tuple(grouped[key]))
            for key in CANONICAL_SECTION_KEYS
            if key in grouped
        ),
        note_proposals=draft.note_proposals,
        config_decisions=draft.config_decisions,
    )


def section_title(key: NoteSectionKey) -> str:
    return SECTION_TITLES[key]


def _lead_words(text: str, *, max_chars: int = 60) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


@dataclass(frozen=True)
class UtteranceChoice:
    """One entry of the Note tab's utterance chooser (Task 5.1): the
    segment, its display label (index, speaker label, first words — display
    only, like the transcript panel) and the sections it may enter under the
    ownership rule (``note.admissible_sections``, the router's own rule)."""

    segment_index: int
    label: str
    allowed_sections: tuple[NoteSectionKey, ...]


def eligible_utterances(
    document: TranscriptDocument,
    *,
    clinician_speaker: str | None,
    in_note: Collection[int],
) -> tuple[UtteranceChoice, ...]:
    """The utterances the clinician may ADD: every segment with quotable
    text whose index is not already carried by the working note (a line
    present anywhere in the note is refused — D14), in transcript order."""
    choices: list[UtteranceChoice] = []
    for index, segment in enumerate(document.transcript_segments):
        if index in in_note:
            continue
        text = reconstruct_span_text(segment.transcript_words)
        if not text:
            continue
        allowed = admissible_sections(
            CANONICAL_SECTION_KEYS,
            speaker=segment.speaker,
            clinician_speaker=clinician_speaker,
            text=text,
        )
        choices.append(
            UtteranceChoice(index, f"{index + 1}. {segment.speaker}: {_lead_words(text)}", allowed)
        )
    return tuple(choices)


LineState = Literal["routed", "removed", "moved", "added", "replaced"]


@dataclass(frozen=True)
class EditableLine:
    """One transcript-provenance line of the working note with its edit
    state (Task 5.1b): ``routed`` (the provider's, in place), ``removed``
    (the provider's, subtracted), ``moved`` (the provider's, subtracted and
    re-added under ``moved_to``), ``added`` (a manual addition with no
    provider counterpart) or ``replaced`` (subtracted in favour of the typed
    line ``replaced_by`` — note-learning plan Task 2.1). ``allowed_sections``
    are the sections a Move may target — the ownership rule, minus the
    section it is in."""

    assertion_id: str
    segment_index: int
    section_key: NoteSectionKey
    label: str
    state: LineState
    moved_to: NoteSectionKey | None
    allowed_sections: tuple[NoteSectionKey, ...]
    replaced_by: str | None = None


def editable_lines(
    draft: NoteDraft,
    document: TranscriptDocument,
    *,
    removed: Collection[str],
    additions: Mapping[str, NoteAssertion],
    replaced: Mapping[str, str] = {},
) -> tuple[EditableLine, ...]:
    """The rows of the Note tab's line editor: the provider's transcript
    lines in note order (each carrying its remove/move state) followed by
    the manual additions that are not the re-added leg of a move. A line in
    ``replaced`` (its id -> the typed line's id) renders as ``replaced``
    whether it is a provider line in ``removed`` or a manual addition still
    listed in ``additions``."""
    manual_by_segment: dict[int, NoteAssertion] = {}
    for assertion in additions.values():
        coords = assertion.note_span.source_coords
        if coords is not None:
            manual_by_segment[coords.segment_index] = assertion

    def allowed_for(segment_index: int, current: NoteSectionKey) -> tuple[NoteSectionKey, ...]:
        segment = document.transcript_segments[segment_index]
        return tuple(
            key
            for key in admissible_sections(
                CANONICAL_SECTION_KEYS,
                speaker=segment.speaker,
                clinician_speaker=draft.clinician_speaker,
                text=reconstruct_span_text(segment.transcript_words),
            )
            if key != current
        )

    lines: list[EditableLine] = []
    covered: set[int] = set()
    for section in draft.note_sections:
        for assertion in section.note_assertions:
            coords = assertion.note_span.source_coords
            if assertion.provenance != "transcript" or coords is None:
                # Not a quoted line: a typed ``clinician`` line (schema v2)
                # has no segment to move or remove by — its own row is the
                # note-learning plan's Task 2.1.
                continue
            if coords.segment_index >= len(document.transcript_segments):
                continue  # Check 1's source_coords_invalid owns this line
            segment_index = coords.segment_index
            manual = manual_by_segment.get(segment_index)
            state: LineState = "routed"
            moved_to: NoteSectionKey | None = None
            replaced_by = replaced.get(assertion.assertion_id)
            if replaced_by is not None:
                state = "replaced"
            elif assertion.assertion_id in removed:
                if manual is not None:
                    state, moved_to = "moved", manual.section_key
                    covered.add(segment_index)
                else:
                    state = "removed"
            lines.append(
                EditableLine(
                    assertion.assertion_id,
                    segment_index,
                    section.section_key,
                    f"{section_title(section.section_key)} - {_lead_words(assertion.text)}",
                    state,
                    moved_to,
                    allowed_for(segment_index, section.section_key),
                    replaced_by,
                )
            )
    for assertion in additions.values():
        coords = assertion.note_span.source_coords
        if coords is None or coords.segment_index in covered:
            # No coordinates = a typed ``clinician`` addition (schema v2):
            # no row here — ``typed_lines`` lists it (Task 2.1).
            continue
        if coords.segment_index >= len(document.transcript_segments):
            continue
        replaced_by = replaced.get(assertion.assertion_id)
        lines.append(
            EditableLine(
                assertion.assertion_id,
                coords.segment_index,
                assertion.section_key,
                f"{section_title(assertion.section_key)} - {_lead_words(assertion.text)}",
                "replaced" if replaced_by is not None else "added",
                None,
                allowed_for(coords.segment_index, assertion.section_key),
                replaced_by,
            )
        )
    return tuple(lines)


@dataclass(frozen=True)
class TypedLine:
    """One typed ``clinician`` line of the working note (note-learning plan
    Task 2.1): what it says, where it sits and what it replaced — a provider
    or manual transcript line, a proposal, or nothing (``replaces`` None
    is unreachable through the Note tab, which types only OVER a line)."""

    assertion_id: str
    section_key: NoteSectionKey
    text: str
    label: str
    replaces: str | None


def typed_lines(additions: Mapping[str, NoteAssertion]) -> tuple[TypedLine, ...]:
    """The typed rows of the line editor, in insertion order: every
    coordinate-free ``clinician`` addition."""
    return tuple(
        TypedLine(
            assertion.assertion_id,
            assertion.section_key,
            assertion.text,
            f"{section_title(assertion.section_key)} - {_lead_words(assertion.text)}",
            assertion.replaces,
        )
        for assertion in additions.values()
        if assertion.provenance == "clinician"
    )


PrefilledState = Literal["prefilled", "removed", "replaced"]


@dataclass(frozen=True)
class PrefilledLine:
    """One line the practitioner's OWN config pre-filled (note-learning plan
    D5, Task 2.4): the proposal the emitter minted a config decision for,
    with its review state — ``prefilled`` (in the note, marked), ``removed``
    (the clinician's Remove: declined at Save, the rule demoted) or
    ``replaced`` (edited into the typed line ``replaced_by``). ``learned``
    says whether Remove or Edit reaches a learned rule's count or wording."""

    proposal_id: str
    section_key: NoteSectionKey
    text: str
    label: str
    state: PrefilledState
    learned: bool
    replaced_by: str | None = None


def prefilled_lines(
    draft: NoteDraft,
    *,
    removed: Collection[str],
    replaced: Mapping[str, str],
) -> tuple[PrefilledLine, ...]:
    """The pre-filled rows of the line editor, in proposal order: one per
    config decision the draft carries."""
    decided = {decision.proposal_id for decision in draft.config_decisions}
    lines: list[PrefilledLine] = []
    for proposal in draft.note_proposals:
        if proposal.proposal_id not in decided:
            continue
        replaced_by = replaced.get(proposal.proposal_id)
        state: PrefilledState = "prefilled"
        if replaced_by is not None:
            state = "replaced"
        elif proposal.proposal_id in removed:
            state = "removed"
        lines.append(
            PrefilledLine(
                proposal.proposal_id,
                proposal.section_key,
                proposal.note_excerpt,
                f"{section_title(proposal.section_key)} - "
                f"{_lead_words(proposal.note_excerpt)} [{PREFILLED_MARK}]",
                state,
                proposal.provenance == "autofill" and is_learned_rule_id(proposal.rule_id),
                replaced_by,
            )
        )
    return tuple(lines)


SAVE_BUTTON_LABEL: Final = "Save note"


def save_button_label(prefilled_count: int) -> str:
    """The Save button's text (D5): with pre-filled lines in the note the
    button SAYS it confirms them, counted, so one Save is a visible act of
    ratification; with none it is the plain ``SAVE_BUTTON_LABEL``."""
    if prefilled_count <= 0:
        return SAVE_BUTTON_LABEL
    noun = "line" if prefilled_count == 1 else "lines"
    return f"Save - confirms the {prefilled_count} pre-filled {noun} shown"


# --- phrase learning status (practitioner-profile plan Task 5.2) -----------

LEARNING_NO_PROFILE_HINT: Final = (
    "Phrase learning is off: no voice profile - set one up on the Practitioner tab."
)
LEARNING_UNUSABLE_HINT: Final = (
    "Phrase learning is off: your voice profile cannot be read ({reason}) - re-enrol or "
    "delete it on the Practitioner tab."
)
LEARNING_STALE_CONSENT_HINT: Final = (
    "Phrase learning is off until you confirm the updated consent text on the Practitioner "
    "tab."
)
LEARNING_OPTED_OUT_HINT: Final = (
    "Phrase learning is off - turn it on on the Practitioner tab."
)
LEARNING_ON_LINE: Final = (
    "Phrase learning is on: lines you add or move, and shorthand you type over your own "
    "lines, are learned when you press Save note on this tab."
)
# Shown on the Note tab's learning line while phrases are QUEUED (live smoke
# 2026-09-17: the practitioner read the queue as done and left the review
# without pressing Save note on this tab — nothing is written on any other
# exit, by design, so the line must name the button and the tab).
LEARNING_NOT_ATTRIBUTED_NOTE: Final = (
    "Not learned: this line is not attributed to you - only your own lines are learned."
)


def _queued_nouns(phrases: int, rules: int, *, queued_first: bool) -> str:
    """``"1 phrase queued"`` / ``"1 queued phrase"``, ``"2 phrases and 1
    shorthand rule queued"`` — the queued phrases (cue learning) and the
    queued shorthand rules (note-learning plan Phase 2), named separately so
    the practitioner knows what Save writes."""
    counted: list[tuple[int, str]] = []
    if phrases:
        counted.append((phrases, "phrase" if phrases == 1 else "phrases"))
    if rules:
        counted.append((rules, "shorthand rule" if rules == 1 else "shorthand rules"))
    if queued_first:
        return " and ".join(f"{count} queued {noun}" for count, noun in counted)
    return " and ".join(f"{count} {noun}" for count, noun in counted) + " queued"


def learning_queued_line(count: int, rules: int = 0) -> str:
    """The learning line while ``count`` phrases and ``rules`` shorthand
    rules wait for Save: names the exact control that writes them and where
    it is."""
    nouns = _queued_nouns(count, rules, queued_first=False)
    return (
        f"Phrase learning is on: {nouns} - press Save note on this tab to learn them "
        "(Cancel, Delete and Complete learn nothing)."
    )


def unlearned_on_exit_line(count: int, rules: int = 0) -> str:
    """The sentence the Transcript screen appends after a review left with
    ``count`` phrases (and ``rules`` shorthand rules) still queued
    (practitioner-profile plan Task 5.6; note-learning plan Task 2.3): the
    queue is written by Save note only, so every other exit drops it — said
    once, where the practitioner lands, never a modal."""
    verb = "was" if count + rules == 1 else "were"
    nouns = _queued_nouns(count, rules, queued_first=True)
    return f"{nouns} {verb} not learned - only Save note on the Note tab learns them."


def check_typed_text(text: str) -> str | None:
    """Why ``text`` may not be typed over a note line (note-learning plan
    Task 2.1), or None when it may: blank, over ``MAX_ASSERTION_CHARS``, or
    carrying a control / layout / invisible-format character — the ONE
    config-text validator (``note_config._no_control_chars``), because the
    same words may become a learned rule's wording and must be exactly what
    is shown. The refusal filters (names, numbers, dates, medications) are
    NOT applied here: they decide what is LEARNED, never what the clinician
    may write in their own note."""
    stripped = text.strip()
    if not stripped:
        return "Type the line's wording first."
    if len(stripped) > MAX_ASSERTION_CHARS:
        return f"The line is too long (over {MAX_ASSERTION_CHARS} characters)."
    try:
        _no_control_chars(stripped)
    except ValueError:
        return "The line carries a hidden control or layout character - retype it."
    return None


@dataclass(frozen=True)
class LearningStatus:
    """Whether the Note tab may learn from this review: ``enabled`` only when
    a READABLE profile carries the CURRENT consent version with the learning
    opt-in ticked (D9 as amended; Task 5.0's version check). ``reason`` is
    the one-line hint pointing at the Practitioner tab when it is off."""

    enabled: bool
    reason: str | None


def learning_status(*, profile_root: Path | None = None) -> LearningStatus:
    """One profile read (no embedder identity — learning needs consent, not
    the speaker model; a stale-model profile still records what was agreed).
    Safe on the GUI thread: a DPAPI unwrap and one decrypt."""
    try:
        profile = load_profile(root=profile_root)
    except ProfileUnusableError as exc:
        return LearningStatus(False, LEARNING_UNUSABLE_HINT.format(reason=exc.reason))
    if profile is None:
        return LearningStatus(False, LEARNING_NO_PROFILE_HINT)
    if not consent_is_current(profile):
        return LearningStatus(False, LEARNING_STALE_CONSENT_HINT)
    if not profile.consent.learning_opt_in:
        return LearningStatus(False, LEARNING_OPTED_OUT_HINT)
    return LearningStatus(True, None)


def _extractive_provider_from_config(config: NoteConfig) -> NoteModelProvider:
    """The shipping provider built FROM the loaded config (practitioner-profile
    plan Task 4.3): the cues that route utterances are the config's own —
    the fourth clinician config file, digest-bound (D7) — never the module
    defaults, so a practitioner's ``section_cues.json`` is what routes."""
    return ExtractiveNoteProvider(cues=config.normalised_cues())


def build_note_generator(
    *,
    clinician_speaker: str,
    template_profile_id: str | None,
    prefill_id: str | None = None,
    config_root: Path | None = None,
    provider_factory: Callable[[NoteConfig], NoteModelProvider] = (
        _extractive_provider_from_config
    ),
) -> Callable[[Path, SessionCrypto], NoteGenerationResult]:
    """A generation worker for ``SessionController.with_generation_custody``.

    Reads the transcript FROM DISK (the exact on-disk artifact ``write_note``
    re-verifies against), loads the note config, and composes the draft with
    the CONFIRMED role and template profile (Task 7.5 — ``clinician_speaker``
    is required and typed ``str``, so a generator cannot be built without a
    confirmed role). Config load and provider construction happen at call
    time, inside the worker thread, off the GUI thread — mirroring
    ``build_transcriber``; the provider is built FROM the resolved config
    (``provider_factory(config)``), so the cues it routes by are the ones the
    draft's ``config_digest`` binds. Returns the draft plus the resolved
    config."""

    def generator(session_dir: Path, crypto: SessionCrypto) -> NoteGenerationResult:
        document = read_transcript(session_dir, crypto)
        config = load_note_config(config_root)
        learned, notes = learned_rule_states(config_root)
        draft = compose_draft(
            document,
            config,
            provider_factory(config),
            template_profile_id=template_profile_id,
            clinician_speaker=clinician_speaker,
            prefill_id=prefill_id,
            learned_rules=learned,
        )
        return NoteGenerationResult(draft=draft, config=config, document=document, notes=notes)

    return generator


LEARNED_RULES_UNREADABLE_NOTE: Final = (
    "The learned-shorthand record could not be read ({reason}), so every learned rule "
    "is proposed for confirmation this time; check it on the Practitioner tab."
)


def learned_rule_states(
    config_root: Path | None,
) -> tuple[dict[str, LearnedRuleEntry], tuple[str, ...]]:
    """The learned-rule sidecar for the emitter (note-learning plan D5), read
    fail-SAFE: a malformed or unreadable sidecar yields no entries — so every
    learned rule proposes and needs its click, never the reverse — plus the
    one-line note the Note tab shows. The config itself still loads loudly
    through ``load_note_config``; only the metadata sidecar is soft here."""
    try:
        return load_learned_rule_entries(config_root), ()
    except NoteConfigError as exc:
        reason = f"{type(exc).__name__}: {exc}"
        return {}, (LEARNED_RULES_UNREADABLE_NOTE.format(reason=reason),)


# ---------------------------------------------------------------------------
# Benchmark / model report panel content.
# ---------------------------------------------------------------------------


def model_file_report_lines(kind: EmbedderKind = SHIPPED_SPEAKER_EMBEDDER) -> list[str]:
    """The three model-FILE lines of the microphone screen's report panel,
    from stats alone — the whisper snapshot, the VAD model and the speaker
    model — so the screen may recompute them on its 5 s poll (round 51
    MED-001: the poll must never read the profile; that line is
    ``voice_profile_report_line``'s, taken separately).

    Step 13 fallback policy: when the default (medium) snapshot is absent
    but the fallback (small) is present, the pipeline degrades to the
    fallback and this report says so VISIBLY — the clinician must never
    discover the quality difference by surprise.
    """
    resolved = resolve_whisper_model()
    missing = "MISSING - run scripts/setup-models.py"
    if whisper_model_available(DEFAULT_WHISPER_MODEL):
        whisper_line = f"Whisper model ({DEFAULT_WHISPER_MODEL}): ready"
    elif resolved != DEFAULT_WHISPER_MODEL and whisper_model_available(resolved):
        whisper_line = (
            f"Whisper model ({DEFAULT_WHISPER_MODEL}): MISSING - using "
            f"fallback {resolved}; run scripts/setup-models.py for "
            f"{DEFAULT_WHISPER_MODEL}"
        )
    else:
        whisper_line = f"Whisper model ({DEFAULT_WHISPER_MODEL}): {missing}"
    vad_ready = vad_model_available()
    return [
        whisper_line,
        "VAD model (silero): " + ("ready" if vad_ready else missing),
        speaker_model_report_line(kind),
    ]


def model_report_lines(
    *, profile_root: Path | None = None, kind: EmbedderKind = SHIPPED_SPEAKER_EMBEDDER
) -> list[str]:
    """Every line of the microphone screen's report panel: the three
    model-file lines plus the voice profile's state.

    Practitioner-profile plan D2 (Task 3.2, the surface Task 0.6 deferred
    to): two further lines name the speaker model's presence and the voice
    profile's state, so a consultation that will run WITHOUT attribution is
    visible before it is recorded — the same shape as the whisper fallback
    line. The file lines come from stats; the profile line costs ONE profile
    read (``attribution_readiness``: a DPAPI unwrap and a decrypt, no model
    loaded on the GUI thread), which is why the microphone screen takes it
    through ``voice_profile_report_line`` only at construction, on a device
    refresh, when the Practitioner tab changes the profile and — because the
    line's text folds the speaker model's presence in — when that presence
    flips between two polls (peer round 55 PR-REG-006); otherwise the poll
    re-renders the file lines alone (round 51 MED-001). The profile line
    renders a date and a model id, never a field of the profile.
    """
    return [
        *model_file_report_lines(kind),
        voice_profile_report_line(profile_root=profile_root, kind=kind),
    ]


def speaker_model_report_line(kind: EmbedderKind = SHIPPED_SPEAKER_EMBEDDER) -> str:
    """The speaker model's presence (a stat — D16: spectral has no file and
    is always available; onnx iff the pinned file is present). The line
    claims only what the stat establishes (peer round 27 PR-LOW-029): the
    file is INSTALLED; its digest and I/O contract are verified when the
    worker loads it, and a failure there is reported on the Transcript
    screen (``ATTRIBUTION_DID_NOT_RUN_REASON``)."""
    model_id, _sha = shipped_embedder_identity(kind)
    if kind == "spectral":
        return f"Speaker model ({model_id}): ready (built in)"
    if speaker_embedder_available(kind):
        return f"Speaker model ({model_id}): installed - verified when it loads"
    return (
        f"Speaker model ({model_id}): MISSING - run scripts/setup-models.py "
        "--only speaker-embedding (voice attribution is off until then)"
    )


PROFILE_NOT_ENROLLED_LINE: Final = (
    "Voice profile: not enrolled - set it up on the Practitioner tab (recording works "
    "without it)"
)


def voice_profile_report_line(
    *, profile_root: Path | None = None, kind: EmbedderKind = SHIPPED_SPEAKER_EMBEDDER
) -> str:
    """The voice profile's state as ``attribution_readiness`` sees it: not
    enrolled, enrolled (its creation date and the embedder's ``model_id``),
    or the D2 fallback line naming why a present profile will not be applied
    (model absent, made by another model, unusable)."""
    readiness = attribution_readiness(profile_root=profile_root, kind=kind)
    if not readiness.profile_present:
        return PROFILE_NOT_ENROLLED_LINE
    profile = readiness.profile
    if profile is None:
        return readiness.reason or ATTRIBUTION_DID_NOT_RUN_REASON
    line = f"Voice profile: enrolled {profile.created_at:%Y-%m-%d} (model {profile.model_id})"
    if not consent_is_current(profile):
        # Task 5.0: a readable record carrying an older consent text — the
        # profile still attributes, the tab asks for a fresh tick.
        line += " - consent text updated, confirm it on the Practitioner tab"
    return line


def models_ready() -> bool:
    """True when a USABLE whisper model (default or fallback) and the VAD
    model are both locally complete."""
    return whisper_model_available(resolve_whisper_model()) and vad_model_available()


# ---------------------------------------------------------------------------
# Practitioner tab copy (practitioner-profile plan Tasks 0.2 / 3.1 / 3.2).
# ---------------------------------------------------------------------------

# Consent texts, each RATIFIED by the practitioner and shipped VERBATIM. The
# CURRENT version's string is stored in the profile's consent record
# (``ConsentRecord.consent_text_version``); a record carrying an OLDER version
# is readable but NOT current — the Practitioner tab asks for a fresh tick and
# phrase learning stays off until the practitioner re-consents (Task 5.0).
# Earlier texts stay here as history for the records that carry them.
CONSENT_TEXT_VERSION: Final = "consent-v3"
# v1 — ratified 2026-09-05 (Task 0.2); the propose-then-approve terms.
CONSENT_TEXT_V1: Final = (
    "This app can learn your voice and your phrasing to improve your notes. If you agree, "
    "it stores on this computer: a numeric fingerprint of your voice (never a recording), "
    "encrypted; and, if you also turn on phrase learning, the short phrases you approve "
    "during review, kept as plain text in your own config file until you delete them. The "
    "app cannot tell whether a phrase names a patient — only you can — so it shows you "
    "every phrase before saving it, refuses names and numbers, and asks you to confirm it "
    "contains no patient information; keep phrases general. Nothing else about any patient "
    "is stored beyond their session, and nothing leaves this computer. You can re-record "
    "your voice, delete it, or delete any learned phrase at any time from this tab. "
    "Version consent-v1."
)
# v2 — ratified 2026-09-16 (the auto-learn, review-later terms; D9 as amended).
# The plan's blockquote emphasises "you" with markdown asterisks; the label is
# plain text, so the word is shipped without the markup.
CONSENT_TEXT_V2: Final = (
    "This app can learn your voice and your phrasing to improve your notes. If you agree, "
    "it stores on this computer: a numeric fingerprint of your voice (never a recording), "
    "encrypted; and, if you also turn on phrase learning, short phrases taken from lines "
    "you add or move while reviewing a note, saved automatically when you save the note "
    "and kept as plain text in your own config file until you delete them. Only your own "
    "lines are ever used — never a patient's. The app cannot tell whether a phrase names a "
    "patient, so it refuses phrases containing names, numbers, dates or medication names, "
    "and shows you everything it has learned on this tab so you can delete any of it. "
    "Nothing else about any patient is stored beyond their session, and nothing leaves "
    "this computer. You can re-record your voice, delete it, or delete any learned phrase "
    "at any time from this tab. "
    "Version consent-v2."
)
# v3 — the note-learning-and-styles plan (Phase 0, D12): REWRITTEN by data
# class rather than appended, because v2's "refuses phrases containing names,
# numbers, dates or medication names" and "Nothing else about any patient is
# stored beyond their session" both stop being true once typed shorthand (a
# narrower filter, no name check), learned rules, the learned style and its
# exemplar sentences exist. Each earlier text carries its OWN literal version
# string so history never interpolates the mutable constant above.
CONSENT_TEXT_V3: Final = (
    "This app can learn your voice, your phrasing and your note style to improve your "
    "notes. Everything it learns is stored on this computer only, and nothing leaves it. "
    "If you agree, it stores: (1) A numeric fingerprint of your voice (never a "
    "recording), encrypted. (2) If you also turn on learning: short phrases from lines "
    "you add or move while reviewing a note, and shorthand rules made from wording you "
    "type over a note line, both saved automatically when you save the note and kept as "
    "plain text in your own config files until you delete them. Only your own lines are "
    "ever used — never a patient's. The app checks the shape of words, not their meaning: "
    "a phrase or rule trigger taken from what you said is refused if it looks like it "
    "contains a name, a number, a date or a medication name; wording you type yourself "
    "is refused only for numbers, dates and medication names, so keeping patient names "
    "out of your own shorthand is up to you. (3) If you choose to teach the app your "
    "note style from past notes you upload: what it derives from them — your section "
    "order and headings, your shorthand, a few measures of how you write, and up to 30 "
    "example sentences, each kept only when it passes the same check unchanged and is "
    "shown to you first — stored encrypted until you delete it. The notes you upload are "
    "read, never copied, and are deleted only if you say so. Lines the app pre-fills "
    "from your own rules are marked in the note, and saving the note confirms them. "
    "Everything learned is shown on this tab so you can delete any of it — your voice, "
    "any phrase or rule, or the learned style — at any time. "
    "Version consent-v3."
)
CONSENT_CHECKBOX_LABEL: Final = (
    "I agree - store an encrypted fingerprint of my voice on this computer"
)
# The second checkbox, off by default (Config / Environment / Deployment Impact).
# Consent v3 widens what the opt-in covers to the shorthand rules learned from
# typed edits (the same Save, the same review-later list).
LEARNING_OPT_IN_LABEL: Final = (
    "Also learn my phrasing and shorthand from lines I add, move or edit during review "
    "(saved when I save the note)"
)
# Shown on the Practitioner tab when a readable profile's consent record
# carries an older text version (Task 5.0): the box is left unticked and
# editable, Record needs a fresh tick, and learning is off until re-consent.
CONSENT_STALE_NOTICE: Final = (
    "The consent text has changed - please read it and tick again. Phrase learning stays "
    "off until you confirm."
)
CONFIRM_CONSENT_BUTTON_LABEL: Final = "Confirm consent"


def consent_is_current(record: PractitionerProfile | StyleProfile | ConsentRecord) -> bool:
    """True when the consent record carries the CURRENT text version — the
    only record that pre-ticks the consent box or enables learning (Task
    5.0). Accepts the voice profile, the style profile (note-learning plan
    D9: sample learning at first run needs no voice profile, so the style
    store carries its own record) or a bare ``ConsentRecord``; a record
    carrying an older version is readable but not current on either side."""
    consent = record if isinstance(record, ConsentRecord) else record.consent
    return consent.consent_text_version == CONSENT_TEXT_VERSION


# D10: first run ASKS, never blocks — shown on the Practitioner tab, which the
# main window selects at startup when no profile exists.
FIRST_RUN_BANNER: Final = (
    "Set up your voice profile so the app always knows which words are yours - you can "
    "still record without it."
)
# Note-learning plan Flow 4 (Task 3.4): the banner's second line, shown with
# the first while no learned style exists either — optional, never blocking.
FIRST_RUN_STYLE_LINE: Final = (
    "Optional: teach the scribe your note style from 1-5 past notes."
)


def first_run_banner_text(*, style_present: bool) -> str:
    """The first-run banner: the voice-profile line, plus the sample-note
    line while no learned style exists (``style_profile_present`` — a stat,
    never a decrypt)."""
    if style_present:
        return FIRST_RUN_BANNER
    return f"{FIRST_RUN_BANNER}\n{FIRST_RUN_STYLE_LINE}"


# ---------------------------------------------------------------------------
# Writing styles (note-learning plan D7; Phase 3 Tasks 3.1 / 3.2 / 3.5).
# ---------------------------------------------------------------------------

NOTE_STYLES: Final[tuple[NoteStyle, ...]] = ("verbatim", "clean", "own_voice", "narrative")
STYLE_LABELS: Final[Mapping[NoteStyle, str]] = {
    "verbatim": "Verbatim",
    "clean": "Clean clinical",
    "own_voice": "Own voice",
    "narrative": "Narrative",
}
# C8: every disabled option and every fallback names its reason on screen.
LANGUAGE_MODEL_ABSENT_REASON: Final = (
    "needs the local language model, which is not installed - run "
    "scripts/setup-models.py --only language-model from a normal terminal and install "
    "the prose runtime (AGENTS.md Local Run Steps)"
)
STYLE_PROFILE_EMPTY_REASON: Final = (
    "needs a learned style - teach the scribe your note style below first"
)
STYLE_CONSENT_STALE_REASON: Final = (
    "needs your consent to the current text - the learned style was saved under an "
    "older consent text; read it, tick the consent box and press Confirm consent on the "
    "Practitioner tab"
)
STYLE_SETTING_UNREADABLE_LINE: Final = (
    "Writing style setting unreadable ({reason}) - notes are shown as Clean clinical until "
    "it is fixed or deleted."
)


def language_model_available() -> bool:
    """Whether the local language model the two prose styles need is
    installed (Phase 4, Task 4.4): the prose runtime is importable (a
    ``find_spec`` probe, no import) AND the pinned model FILE is present (a
    stat, UNC refused — ``language_model_file_available``). Never a decrypt
    and never a load, so the Practitioner tab's 5 s poll may ask it; the
    digest is verified by ``LocalLanguageModel`` when the prose stage first
    loads the model. False keeps the prose radios disabled with
    ``LANGUAGE_MODEL_ABSENT_REASON`` (C8)."""
    return language_runtime_importable() and language_model_file_available()


@dataclass(frozen=True)
class StyleOption:
    """One "Writing style" radio: the style, its label, whether it can be
    chosen now and — when it cannot — the reason line (C8)."""

    style: NoteStyle
    label: str
    enabled: bool
    reason: str | None
    # The bare reasons the line above was built from (Phase H round 24
    # MED-005: the tab's fallback line names THESE, never a fixed one).
    reasons: tuple[str, ...] = ()


def style_options(
    *,
    style_root: Path | None = None,
    model_available: Callable[[], bool] = language_model_available,
    style_present: Callable[[Path | None], bool] | None = None,
) -> tuple[StyleOption, ...]:
    """The four options in display order (Flow 3). ``verbatim`` and
    ``clean`` are always available; ``own_voice`` and ``narrative`` need the
    language model, and ``own_voice`` also a non-empty style profile —
    presence by STAT (``style_profile_present``), never a decrypt, so the
    tab may recompute this freely."""
    present = (
        style_present(style_root)
        if style_present is not None
        else style_profile_present(root=style_root)
    )
    model = model_available()
    options: list[StyleOption] = []
    for style in NOTE_STYLES:
        reasons: list[str] = []
        if style in ("own_voice", "narrative") and not model:
            reasons.append(LANGUAGE_MODEL_ABSENT_REASON)
        if style == "own_voice" and not present:
            reasons.append(STYLE_PROFILE_EMPTY_REASON)
        reason = None if not reasons else f"{STYLE_LABELS[style]} {'; '.join(reasons)}."
        options.append(
            StyleOption(style, STYLE_LABELS[style], not reasons, reason, tuple(reasons))
        )
    return tuple(options)


def style_fallback_line(
    style: NoteStyle, reasons: Sequence[str] = (LANGUAGE_MODEL_ABSENT_REASON,)
) -> str | None:
    """The C8 line for a note whose chosen style is a prose style the app
    cannot render now: it renders as ``clean`` and says WHY. The default
    reason is the absent language model — the Note tab's and the stage's
    case, where that is the one reason; the Practitioner tab passes the
    disabled option's own ``reasons`` (Phase H round 24 MED-005: a saved
    Own voice with the model installed but no learned style must name the
    learned style, not the model). None for the two deterministic styles."""
    if style in ("verbatim", "clean"):
        return None
    return (
        f"Writing style '{STYLE_LABELS[style]}' {'; '.join(reasons)} - this note "
        "is shown as Clean clinical."
    )


@dataclass(frozen=True)
class NoteStyleChoice:
    """What the Note tab renders under: the style from
    ``practitioner_settings.json`` (or the default when the file is absent)
    and, when the file could not be read, the one-line reason."""

    style: NoteStyle
    reason: str | None


def read_note_style(config_root: Path | None = None) -> NoteStyleChoice:
    """The saved writing style. An unreadable or malformed settings file is
    a typed error from the loader; here it becomes the DEFAULT style plus a
    reason line for the tab (C8) — the note still renders, and the setting
    is never silently rewritten."""
    try:
        settings = load_practitioner_settings(config_root)
    except NoteConfigError as exc:
        reason = STYLE_SETTING_UNREADABLE_LINE.format(reason=f"{type(exc).__name__}: {exc}")
        return NoteStyleChoice(DEFAULT_NOTE_STYLE, reason)
    return NoteStyleChoice(settings.note_style, None)


def save_note_style(style: NoteStyle, *, config_root: Path | None = None) -> Path:
    """Persist the writing style (``save_practitioner_settings``, atomic);
    the loader's typed errors propagate to the tab, which shows them."""
    settings = PractitionerSettings(note_style=style)
    return save_practitioner_settings(settings, config_root=config_root)


# --- the prose stage (note-learning-and-styles plan Task 4.4; D6, D7; C4, C8) ---
#
# After each finalisation the Note tab runs ONE stage job on a TaskThread for
# a prose style: it loads the language model (once per process, on that
# worker thread — the D3 pattern), reads the style profile for ``own_voice``,
# asks ``ProseStyleProvider`` for exactly the sections the note has no bound
# rendering for, and returns the renderings; the tab binds them to the note
# it holds NOW through ``attach_style_renderings`` (stale ones drop there),
# displays the body and only then re-enables Save. Every fallback names its
# reason on screen (C8) through the lines below; no clinical text rides any
# of them.

LANGUAGE_MODEL_LOAD_FAILED_LINE: Final = (
    "Writing style '{label}': the language model could not be loaded ({reason}) - this "
    "note is shown as Clean clinical."
)
STYLE_PROFILE_MISSING_LINE: Final = (
    "Writing style '{label}' {reason} - this note is shown as Clean clinical."
)
RENDERING_IN_FLIGHT_LINE: Final = (
    "Writing style '{label}': rendering the prose now - Save note is available once the "
    "prose is shown."
)
RENDERING_DONE_LINE: Final = "Writing style '{label}': {summary} ({seconds:.1f} s)."
SAVE_WHILE_RENDERING_MESSAGE: Final = (
    "The prose is still being rendered - Save note is available once it is shown."
)


@dataclass(frozen=True)
class StyleStageResult:
    """One stage job's outcome: the renderings for the sections it was asked
    about (``passed`` with prose, ``failed`` without — Check 5's verdict),
    the counts for the tab's line, the model's wall seconds, and — when
    NOTHING could be rendered — the C8 ``reason`` line. ``note_digest`` is
    ``note_input_digest`` of the note the job was started for, so the tab can
    tell a result for a note that has since changed."""

    style: ProseStyle
    note_digest: str
    renderings: tuple[StyleRendering, ...]
    passed: int
    failed: int
    errored: int
    seconds: float
    reason: str | None = None
    # Of `errored`, the sections refused BEFORE any call because their lines
    # alone overflow the model's window (codex round 30 PR-MED-046).
    too_long: int = 0


class ProseStage(Protocol):
    """The stage callable the Note tab runs on its TaskThread: the note it
    was started for, plus ``abort`` — consulted by the provider before each
    section's model call (Phase H round 24 MED-002: a job orphaned by
    ``clear()`` stops after the call in progress instead of rendering the
    rest of a note whose review has ended)."""

    def __call__(
        self, note: GeneratedNote, /, *, abort: Callable[[], bool] | None = None
    ) -> StyleStageResult: ...


class _LanguageModelCache:
    """The resident language model, built ONCE per process on the first stage
    job's worker thread and reused by every later note (a 2.3 GiB load takes
    tens of seconds; two copies must never be resident). A failed load is
    remembered for the process — the C8 line names it and tells the
    practitioner to restart after fixing the install — so a broken runtime
    is not re-probed on every edit."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model: LanguageModel | None = None
        self._failure: str | None = None

    def get(self, factory: Callable[[], LanguageModel]) -> LanguageModel:
        with self._lock:
            if self._model is not None:
                return self._model
            if self._failure is not None:
                raise LanguageModelError(self._failure)
            try:
                self._model = factory()
            except LanguageModelError as exc:
                self._failure = f"{exc}; restart the app after fixing this"
                raise
            return self._model

    def reset(self) -> None:
        with self._lock:
            self._model = None
            self._failure = None


_LANGUAGE_MODEL_CACHE: Final = _LanguageModelCache()


def reset_language_model_cache() -> None:
    """Drop the resident model and any remembered failure (tests)."""
    _LANGUAGE_MODEL_CACHE.reset()


def sections_to_render(note: GeneratedNote) -> set[NoteSectionKey]:
    """The populated sections with no rendering bound to their CURRENT
    texts — passed or failed (a bound ``failed`` verdict is an answer: the
    same lines are never asked twice in one review)."""
    return {
        section.section_key
        for section in note.note_sections
        if section.note_assertions and bound_rendering(note, section) is None
    }


def build_prose_stage(
    style: NoteStyle,
    *,
    style_root: Path | None = None,
    model_factory: Callable[[], LanguageModel] = LocalLanguageModel,
    profile_loader: Callable[..., StyleProfile | None] = load_style_profile,
    cache: _LanguageModelCache | None = _LANGUAGE_MODEL_CACHE,
    available: Callable[[], bool] = language_model_available,
) -> ProseStage | None:
    """The stage callable for ``style``, or None for the two deterministic
    styles (nothing to run). The callable runs on the Note tab's TaskThread:
    it never touches a widget, never logs, and returns a
    ``StyleStageResult`` for the note it was given — the tab decides what to
    bind. ``model_factory`` (default ``LocalLanguageModel``: the pinned file,
    digest-checked, smoke-tested), ``profile_loader`` and ``available`` (the
    presence stat, default ``language_model_available``) are the test
    seams; ``cache=None`` builds a fresh model per job (tests)."""
    if style not in PROSE_STYLES:
        return None
    prose_style: ProseStyle = "own_voice" if style == "own_voice" else "narrative"
    label = STYLE_LABELS[style]

    def stage(
        note: GeneratedNote, /, *, abort: Callable[[], bool] | None = None
    ) -> StyleStageResult:
        digest = note_input_digest(note)

        def nothing(reason: str) -> StyleStageResult:
            return StyleStageResult(prose_style, digest, (), 0, 0, 0, 0.0, reason)

        # Round 20 MED-002: presence is a STAT, answered the same way the
        # Practitioner tab's poll answers it, and never remembered — the
        # model can be installed while the app runs, and the next
        # finalisation must then try the load. Only a LOAD that failed with
        # the file present (a digest mismatch, a broken runtime) is
        # remembered for the process, because those need a fix and a restart.
        if not available():
            return nothing(style_fallback_line(style) or "")
        try:
            model = cache.get(model_factory) if cache is not None else model_factory()
        except LanguageModelError as exc:
            return nothing(LANGUAGE_MODEL_LOAD_FAILED_LINE.format(label=label, reason=exc))
        profile: StyleProfile | None = None
        if prose_style == "own_voice":
            try:
                profile = profile_loader(root=style_root)
            except ProfileUnusableError as exc:
                reason = STYLE_UNUSABLE_LINE.format(reason=exc.reason)
                return nothing(STYLE_PROFILE_MISSING_LINE.format(label=label, reason=reason))
            if profile is None:
                return nothing(
                    STYLE_PROFILE_MISSING_LINE.format(
                        label=label, reason=STYLE_PROFILE_EMPTY_REASON
                    )
                )
            # Phase H round 24 LOW-001: the style store's OWN consent record
            # (D9) gates USE as well as display — a profile learned under an
            # older text is not conditioning material until the practitioner
            # re-agrees on the tab, exactly as the voice side goes dark
            # (`learning_status`). Dormant while every record is current.
            if not consent_is_current(profile):
                return nothing(
                    STYLE_PROFILE_MISSING_LINE.format(
                        label=label, reason=STYLE_CONSENT_STALE_REASON
                    )
                )
        provider = ProseStyleProvider(model, style=prose_style, profile=profile)
        result = provider.render(
            ProseInput.from_note(note), only=sections_to_render(note), abort=abort
        )
        return StyleStageResult(
            prose_style,
            digest,
            result.renderings,
            len(result.passed_sections),
            len(result.failed_sections),
            len(result.errored_sections),
            result.seconds,
            too_long=len(result.too_long_sections),
        )

    return stage


def rendering_in_flight_line(style: NoteStyle) -> str:
    return RENDERING_IN_FLIGHT_LINE.format(label=STYLE_LABELS[style])


_WHOLE_NOTE_CLEAN_TAIL: Final = " - this note is shown as Clean clinical."


def _sections_showing_prose(note: GeneratedNote) -> int:
    return sum(
        1
        for section in note.note_sections
        if (rendering := bound_rendering(note, section)) is not None
        and rendering.verdict == "passed"
    )


def with_retained_prose(reason: str, note: GeneratedNote) -> str:
    """A fallback ``reason`` made truthful for the note AS DISPLAYED (codex
    round 22 PR-LOW-038): when ``note`` still shows prose rendered earlier
    (a partial re-render failed after an edit), the whole-note clause
    "this note is shown as Clean clinical" is replaced by the mixture —
    which sections are Clean clinical and how many still show prose. A
    reason over a note with no prose is returned unchanged."""
    shown = _sections_showing_prose(note)
    if shown == 0:
        return reason
    mixture = (
        " - the sections without a rendering are shown as Clean clinical; "
        f"{shown} section{'s' if shown != 1 else ''} still show"
        f"{'' if shown != 1 else 's'} the prose rendered earlier."
    )
    if reason.endswith(_WHOLE_NOTE_CLEAN_TAIL):
        return reason[: -len(_WHOLE_NOTE_CLEAN_TAIL)] + mixture
    return reason.rstrip() + mixture


def style_stage_line(result: StyleStageResult, note: GeneratedNote) -> str:
    """The Note tab's one line after a stage job landed on ``note`` (C8):
    the reason when nothing was rendered (made truthful for any prose the
    note still shows — ``with_retained_prose``), else how many sections now
    show prose, how many are shown as Clean clinical because the fidelity
    check refused their prose, and how many could not be rendered at all —
    counted over the NOTE as it stands, not the job alone, so the line and
    the body agree after a partial re-render."""
    label = STYLE_LABELS[result.style]
    if result.reason is not None:
        return with_retained_prose(result.reason, note)
    shown = 0
    refused = 0
    for section in note.note_sections:
        rendering = bound_rendering(note, section)
        if rendering is None:
            continue
        if rendering.verdict == "passed":
            shown += 1
        else:
            refused += 1
    unrendered = sum(
        1
        for section in note.note_sections
        if section.note_assertions and bound_rendering(note, section) is None
    )
    parts = [f"prose shown for {shown} section{'s' if shown != 1 else ''}"]
    if refused:
        parts.append(
            f"{refused} section{'s' if refused != 1 else ''} shown as Clean clinical "
            "(the fidelity check refused the prose)"
        )
    too_long = min(result.too_long, unrendered)
    failed_calls = unrendered - too_long
    if failed_calls:
        parts.append(
            f"{failed_calls} section{'s' if failed_calls != 1 else ''} could not be rendered "
            "(language model error) and shown as Clean clinical"
        )
    if too_long:
        parts.append(
            f"{too_long} section{'s' if too_long != 1 else ''} too long for the model's "
            "window and shown as Clean clinical"
        )
    return RENDERING_DONE_LINE.format(
        label=label, summary=", ".join(parts), seconds=result.seconds
    )


def bind_stage_result(note: GeneratedNote, result: StyleStageResult) -> GeneratedNote:
    """The note with the job's renderings bound where their digests still
    match (``attach_style_renderings`` — the note's own still-valid
    renderings first, so a job's rendering for a section replaces an older
    one only when it is for the same texts, and a stale one never lands)."""
    return attach_style_renderings(note, (*note.style_renderings, *result.renderings))


def carry_renderings(note: GeneratedNote, previous: GeneratedNote | None) -> GeneratedNote:
    """A re-finalised note with the PREVIOUS note's renderings carried over
    where the section's texts are unchanged (the digest binding decides;
    ``attach_style_renderings`` drops the rest and re-derives the
    ``style_fallback`` warnings), so an edit to one section re-renders only
    that section."""
    if previous is None or not previous.style_renderings:
        return attach_style_renderings(note, ())
    return attach_style_renderings(note, previous.style_renderings)


STYLE_NOT_LEARNED_LINE: Final = (
    "Learned style: none yet - teach the scribe your note style from 1-5 past notes."
)
STYLE_UNUSABLE_LINE: Final = (
    "Learned style: cannot be read ({reason}) - delete it and learn again."
)


def style_profile_line(profile: StyleProfile | None) -> str:
    """The learned style's state in one line (Task 3.5) for an ALREADY-LOADED
    profile (None = not learned): a date, a source count and an exemplar
    count, never a field's text; an unusable store is named by the caller
    through ``STYLE_UNUSABLE_LINE``. The ONE style-store read behind it (a
    DPAPI unwrap and a decrypt on the GUI thread) is the Practitioner tab's
    own (``refresh_style_profile_state``, at construction and on its learn /
    remove / delete / consent-renewal events ONLY); no poll reads the STYLE
    store (round 51
    MED-001: the microphone screen's 5 s poll renders
    ``model_file_report_lines``, stats alone, re-reading the voice profile
    only on a speaker-model presence transition — round 55 PR-REG-006; the
    Practitioner tab's 5 s availability poll reads no store). This module
    deliberately exports no helper that decrypts the store on the caller's
    behalf (Phase H round 24 LOW-009 removed the unused one)."""
    if profile is None:
        return STYLE_NOT_LEARNED_LINE
    notes = "note" if profile.source_count == 1 else "notes"
    count = len(profile.exemplars)
    sentences = "sentence" if count == 1 else "sentences"
    line = (
        f"Learned style: learned {profile.learned_at:%Y-%m-%d} from {profile.source_count} "
        f"{notes}, {count} example {sentences}"
    )
    if not consent_is_current(profile):
        line += " - consent text updated, confirm it on this tab"
    return line


# ---------------------------------------------------------------------------
# Voice attribution readiness (practitioner-profile plan D2 / D3 / D16).
# ---------------------------------------------------------------------------

# The D2 fallback lines. Plain clinical English, each naming the remedy.
SPEAKER_MODEL_MISSING_REASON: Final = (
    "Voice attribution is off: the speaker model is not installed - run "
    "scripts/setup-models.py --only speaker-embedding."
)
PROFILE_REENROL_REASON: Final = (
    "Voice attribution is off: your voice profile was made with a different speaker "
    "model - re-enrol on the Practitioner tab."
)
PROFILE_UNUSABLE_REASON: Final = (
    "Voice attribution is off: your voice profile cannot be read ({reason}) - re-enrol "
    "or delete it on the Practitioner tab."
)
ATTRIBUTION_DID_NOT_RUN_REASON: Final = (
    "Voice attribution did not run for this transcript: the speaker model could not be "
    "loaded - run scripts/setup-models.py --only speaker-embedding, then re-check on the "
    "Practitioner tab."
)


@dataclass(frozen=True)
class AttributionReadiness:
    """Whether the shipped voice-attribution path can run, decided from one
    profile read and a model-file stat only — no model is loaded, so this
    is safe on the GUI thread. ``profile_present``: a ``voice.enc`` exists
    (usable or not — an existing profile that cannot be used is PRESENT and
    carries a ``reason``, never "never enrolled");
    ``profile``: the loaded profile when it records the shipped embedder's
    identity (``shipped_embedder_identity``) and the model file is present —
    attribution WILL be attempted by the worker; ``reason``: the visible D2
    fallback line when a profile is present but attribution cannot run
    (model absent, profile made by another model, profile unusable). What
    this cannot see is a model FILE that is present but not the pinned bytes
    or otherwise unloadable — the worker discovers that at load and falls
    back; the Transcript screen then reads the fallback off the DOCUMENT
    (no attribution fields with a profile present) and shows
    ``ATTRIBUTION_DID_NOT_RUN_REASON``."""

    profile_present: bool
    profile: PractitionerProfile | None
    reason: str | None


def attribution_readiness(
    *, profile_root: Path | None = None, kind: EmbedderKind = SHIPPED_SPEAKER_EMBEDDER
) -> AttributionReadiness:
    """See ``AttributionReadiness``. Presence is decided by ``load_profile``'s
    own distinction — ``None`` is a CONFIRMED absence (no ``voice.enc``), a
    ``ProfileUnusableError`` is a profile that exists but cannot be used —
    never by the D10 first-run stat (peer round 19 PR-HIGH-005: a zero-length
    or stat-refused blob must read as needing attention, not as never
    enrolled). Order: the profile read against the shipped identity (D3: a
    profile whose ``model_id`` / ``model_sha256`` differ from the shipped
    embedder's is ABSENT for attribution and reported as needing
    re-enrolment; any other unusable state is reported with its structural
    reason word — never a field of the profile) → model presence (a stat,
    UNC-safe) for a usable profile."""
    model_id, model_sha256 = shipped_embedder_identity(kind)
    try:
        profile = load_profile(root=profile_root, model_id=model_id, model_sha256=model_sha256)
    except ProfileUnusableError as exc:
        reason = (
            PROFILE_REENROL_REASON
            if exc.reason == "model"
            else PROFILE_UNUSABLE_REASON.format(reason=exc.reason)
        )
        return AttributionReadiness(profile_present=True, profile=None, reason=reason)
    if profile is None:
        return AttributionReadiness(profile_present=False, profile=None, reason=None)
    if not speaker_embedder_available(kind):
        return AttributionReadiness(
            profile_present=True, profile=None, reason=SPEAKER_MODEL_MISSING_REASON
        )
    return AttributionReadiness(profile_present=True, profile=profile, reason=None)


AttributionInputs = tuple[SpeakerEmbedder | None, PractitionerProfile | None]


def attribution_inputs(kind: EmbedderKind = SHIPPED_SPEAKER_EMBEDDER) -> AttributionInputs:
    """WORKER-THREAD step: the ``(embedder, profile)`` pair both pipeline
    factories pass to ``transcribe_session`` / ``recover_session_transcription``
    (D3: both entry points apply the profile), or ``(None, None)`` for the
    D2 fallback — no profile, model absent, profile made by another model or
    unusable (``attribution_readiness``), or a model file present but
    refusing to load (``SpeakerModelError``: not the pinned bytes, an
    incompatible export, a broken runtime). The embedder is BUILT here, off
    the GUI thread, and the profile is re-checked against the identity the
    built embedder reports — the readiness probe compared the pin, this
    compares what actually loaded. A load failure never blocks the
    consultation: the transcript is produced without attribution and the
    Transcript screen names the fallback. An ``OfflineEnvError`` is NOT
    caught — the Whisper provider would refuse on the same precondition."""
    readiness = attribution_readiness(kind=kind)
    profile = readiness.profile
    if profile is None:
        return None, None
    try:
        embedder = build_speaker_embedder(kind)
    except SpeakerModelError:
        return None, None
    if not profile.made_by(embedder):
        return None, None
    return embedder, profile


# ---------------------------------------------------------------------------
# Pipeline factories (constructed lazily, inside the worker thread).
# ---------------------------------------------------------------------------

# Note-learning plan C8: every live fallback names its reason on screen.
# Keyed by the worker's failure kind; the detail is appended in parentheses
# by the transcriber callable (an exception type and message from a stage
# function — never transcript text).
LIVE_FALLBACK_STATUS: Final[dict[LiveFailureKind, str]] = {
    LiveFailureKind.MODEL_LOAD: (
        "The live transcription model failed to load; "
        "transcribing after the recording instead."
    ),
    LiveFailureKind.FELL_BEHIND: (
        "Live transcription could not keep up; transcribing after the recording instead."
    ),
    LiveFailureKind.WORKER_ERROR: (
        "Live transcription stopped; transcribing after the recording instead."
    ),
}
LIVE_ASSEMBLED_STATUS: Final = "Transcript assembled from the live transcription."

LiveTranscriberSource = Callable[[], LiveTranscriber | None]


def build_live_transcriber(
    *,
    on_window: Callable[[tuple[TranscriptSegment, ...]], None] | None,
    model_name: str | None = None,
    attribution: Callable[[], AttributionInputs] = attribution_inputs,
) -> LiveTranscriber:
    """The live worker ``SessionController.start`` attaches (note-learning
    plan D1–D3). Its VAD, Whisper provider and attribution inputs are built
    by the factories BELOW on the worker's own thread at start — the same
    call-time model resolution as ``build_transcriber`` — so the GUI thread
    never blocks on a model load and a load failure becomes the worker's
    ``model_load`` reason, never an exception at Start. ``on_window`` is
    invoked on the worker thread with each transcribed window's segments
    (the Transcript screen marshals it to the GUI thread).
    """

    def provider() -> WhisperSpeechProvider:
        name = model_name if model_name is not None else resolve_whisper_model()
        return WhisperSpeechProvider(model_name=name)

    def vad() -> Callable[[bytes], float]:
        return SileroVad().frame_probability

    return LiveTranscriber(
        provider_factory=provider,
        vad_factory=vad,
        attribution_factory=attribution,
        on_window=on_window,
    )


def _live_transcript(
    worker: LiveTranscriber,
    session_dir: Path,
    crypto: SessionCrypto,
    on_status: Callable[[str], None] | None,
) -> TranscriptDocument | None:
    """Drain the claimed live worker on the processing thread and write the
    assembled document (D2). ``None`` means the batch closure must run: the
    worker failed (its C8 reason reported) or its drain/assembly raised a
    live-path error. The worker is stopped on every exit — its models were
    released when its thread exited (D3), and ``stop`` confirms the buffers
    are gone — BEFORE the caller constructs the batch provider, so two
    models are never resident. A store write failure propagates exactly as
    it would from the batch path. The verdict of ``stop`` is CONSULTED
    (Phase H round 24 LOW-002): a worker that did not confirm its buffers
    cleared raises ``LiveTranscriptionError`` out of the transcriber instead
    of admitting the batch path — a second model beside a possibly-alive
    worker is exactly what this ordering exists to prevent. Unreachable by
    construction (``finish`` seals before PROCESSING and ``drain`` refuses
    an unsealed worker before its join), so the raise is the fail-closed
    shape of a claim, not an expected path."""
    document: TranscriptDocument | None = None
    try:
        try:
            result = worker.drain()
            header = read_store_header(session_dir / AUDIO_FILENAME)
            document = result.assemble(header.session_id)
        except LiveTranscriptionFailed as exc:
            if on_status is not None:
                on_status(f"{LIVE_FALLBACK_STATUS[exc.failure.kind]} ({exc.failure.detail})")
        except (LiveTranscriptionError, ValueError) as exc:
            if on_status is not None:
                on_status(
                    f"{LIVE_FALLBACK_STATUS[LiveFailureKind.WORKER_ERROR]} "
                    f"({type(exc).__name__}: {exc})"
                )
    finally:
        cleared = worker.stop()
    if not cleared:
        raise LiveTranscriptionError(
            "the live worker did not confirm its buffers cleared; the batch path is refused"
        )
    if document is None:
        return None
    write_transcript(session_dir, crypto, document)
    if on_status is not None:
        on_status(LIVE_ASSEMBLED_STATUS)
    return document


def build_transcriber(
    model_name: str | None = None,
    *,
    attribution: Callable[[], AttributionInputs] = attribution_inputs,
    live_source: LiveTranscriberSource | None = None,
    on_status: Callable[[str], None] | None = None,
) -> Callable[[Path, SessionCrypto], TranscriptDocument]:
    """A ``SessionController.transcribe`` transcriber over the real ML stack.

    Models load inside the call (worker thread) so the GUI thread never
    blocks on CTranslate2/onnxruntime initialisation. ``model_name=None``
    (the default) applies the Step 13 fallback policy at call time via
    ``resolve_whisper_model``; the resolved name is recorded in the
    transcript document so the artifact says which model actually ran.
    ``attribution`` (default ``attribution_inputs``) resolves the speaker
    embedder and the enrolled profile inside the same call — both entry
    points pass them (D3), or ``(None, None)`` for the visible D2 fallback.

    Note-learning plan Task 1.3: ``live_source`` (the controller's
    ``claim_live_transcriber``, called INSIDE the run so the ``transcribing``
    guard already covers Discard) hands over the sealed live worker; the
    callable drains it here on the processing thread, assembles through
    ``assemble_transcript`` and writes ``transcript.enc`` once. Any live
    failure reports its C8 line through ``on_status`` (processing thread —
    the screen marshals it) and runs the batch closure below unchanged.
    ``SessionController.transcribe``'s signature is untouched.
    """

    def transcriber(session_dir: Path, crypto: SessionCrypto) -> TranscriptDocument:
        worker = live_source() if live_source is not None else None
        if worker is not None:
            document = _live_transcript(worker, session_dir, crypto, on_status)
            if document is not None:
                return document
        name = model_name if model_name is not None else resolve_whisper_model()
        vad = SileroVad()
        provider = WhisperSpeechProvider(model_name=name)
        embedder, profile = attribution()
        return transcribe_session(
            session_dir,
            crypto,
            provider,
            vad.frame_probability,
            require_footer=True,
            model_name=name,
            speaker_embedder=embedder,
            enrolled_profile=profile,
        )

    return transcriber


def build_recovery_runner(
    model_name: str | None = None,
    *,
    attribution: Callable[[], AttributionInputs] = attribution_inputs,
) -> Callable[[Path], RecoveryOutcome]:
    """Flow 3 resume-processing over the real ML stack (worker thread).

    Same Step 13 call-time model resolution — and the same attribution
    resolution (D3: the recovery path applies the profile too) — as
    ``build_transcriber``.
    """

    def runner(session_dir: Path) -> RecoveryOutcome:
        name = model_name if model_name is not None else resolve_whisper_model()
        vad = SileroVad()
        provider = WhisperSpeechProvider(model_name=name)
        embedder, profile = attribution()
        return recover_session_transcription(
            session_dir,
            provider,
            vad.frame_probability,
            model_name=name,
            speaker_embedder=embedder,
            enrolled_profile=profile,
        )

    return runner


# ---------------------------------------------------------------------------
# Clinics tab copy (Cliniko workflow safeguards plan Task 2.2, D10). Every
# line names what happened and the control that fixes it; none carries the
# key (the tab never shows it after entry).
# ---------------------------------------------------------------------------

ClinicOperation = Literal["add", "replace", "remove"]

CLINICS_INTRO: Final = (
    "Add each clinic's Cliniko API key so the scribe can check, with Cliniko, that "
    "a recording belongs to the treatment note open in Cliniko. The key is kept in "
    "Windows Credential Manager and is never shown again. Nothing is sent to Cliniko "
    "until you press Validate or Replace key."
)
CLINIC_KEY_CLIPBOARD_ADVICE: Final = (
    "If you paste the key, Windows can keep a copy in clipboard history (Windows key + V) "
    "and, with clipboard sync on, on your other devices - clear it there once the key is "
    "validated."
)
CLINIC_ADDRESS_HINT: Final = (
    "Clinic web address - only needed if the scribe asks for it: copy "
    "yourclinic.au2.cliniko.com from the address bar while Cliniko is open."
)
CLINIC_CHECKING_LINE: Final = "Checking the key with Cliniko..."
CLINIC_CHECK_STOPPED_LINE: Final = (
    "The check with Cliniko stopped unexpectedly, so nothing was saved - press the same "
    "button again."
)
CLINIC_NO_SELECTION_LINE: Final = "Select a clinic in the list first."
CLINIC_REMOVE_CONFIRM_LABEL: Final = "Confirm remove"
CLINIC_REMOVE_LABEL: Final = "Remove"

_CLINIC_REFUSAL_COPY: Final[Mapping[ClinicRefusal, str]] = {
    ClinicRefusal.NAME_INVALID: (
        "Type a name for the clinic (one line, up to 60 characters), then press Validate."
    ),
    ClinicRefusal.EMAIL_INVALID: (
        "Type your contact email as a plain address (name@example.com) - Cliniko asks for "
        "it with every request."
    ),
    ClinicRefusal.KEY_FORMAT: (
        "That is not a Cliniko API key - a key ends in its region, such as -au2. Copy it "
        "again from your Cliniko user's API keys page and paste it in."
    ),
    ClinicRefusal.ADDRESS_INVALID: (
        "The clinic web address should look like yourclinic.au2.cliniko.com - copy it from "
        "the address bar while Cliniko is open."
    ),
    ClinicRefusal.TOO_MANY_CLINICS: (
        "Two clinics are already set up - remove one before adding another."
    ),
    ClinicRefusal.KEY_REJECTED: (
        "Cliniko refused this key. Check it is the current key of your own Cliniko user, "
        "then paste it again. Nothing was saved."
    ),
    ClinicRefusal.USER_INACTIVE: (
        "This key's Cliniko user is inactive - use the key of your own active user. "
        "Nothing was saved."
    ),
    ClinicRefusal.NO_PRACTITIONER_RECORD: (
        "Cliniko has no practitioner record for this key's user (a reception or "
        "bookkeeping login has none) - use the key of your own login, the one your "
        "treatment notes are written under. Nothing was saved."
    ),
    ClinicRefusal.SEVERAL_PRACTITIONER_RECORDS: (
        "Cliniko lists more than one practitioner record for this key's user, so the "
        "scribe cannot tell which is yours. Nothing was saved."
    ),
    ClinicRefusal.PRACTITIONER_INACTIVE: (
        "This key's practitioner record is inactive in Cliniko - make it active there, "
        "or use the key of your own active practitioner login. Nothing was saved."
    ),
    ClinicRefusal.ADDRESS_NEEDED: (
        "Cliniko did not share this clinic's web address with this key. Type it in the "
        "clinic web address field, paste the key again and press Validate - the address "
        "is confirmed the first time a note is checked with Cliniko. Nothing was saved."
    ),
    ClinicRefusal.SHARD_MISMATCH: (
        "The web address and the key are for different Cliniko regions - check both are "
        "for the same clinic. Nothing was saved."
    ),
    ClinicRefusal.ADDRESS_MISMATCH: (
        "The web address you typed does not match this key's clinic - check you pasted "
        "the right clinic's key, or clear the web address field. Nothing was saved."
    ),
    ClinicRefusal.DIFFERENT_ACCOUNT: (
        "This key is for a different Cliniko account than {clinic} - add it with Validate "
        "as a new clinic instead. Nothing was changed."
    ),
    ClinicRefusal.DUPLICATE_SUBDOMAIN: (
        "That Cliniko account is already set up as another clinic. Nothing was added."
    ),
    ClinicRefusal.UNREACHABLE: (
        "Cliniko could not be reached - check the internet connection and press the same "
        "button again. Nothing was saved."
    ),
    ClinicRefusal.RATE_LIMITED: (
        "Cliniko is limiting requests right now - wait a minute and press the same button "
        "again. Nothing was saved."
    ),
    ClinicRefusal.CERTIFICATE_REJECTED: (
        "Cliniko's security certificate was not trusted, so the key was not checked - "
        "check the network (a proxy or a hotel/guest sign-in page) and try again. Nothing "
        "was saved."
    ),
    ClinicRefusal.ANSWER_UNREADABLE: (
        "Cliniko's answer was not what the scribe expected, so nothing was saved - try "
        "again, and if it repeats the scribe may need an update."
    ),
    ClinicRefusal.SUPERSEDED: (
        "The clinic changed while its key was being checked, so that check's result was "
        "not used and nothing was changed by it."
    ),
    ClinicRefusal.CLINIC_GONE: (
        "That clinic is no longer set up, so the result was not used and nothing was "
        "changed by it."
    ),
    ClinicRefusal.KEY_STORE_FAILED: (
        "The key could not be saved in Windows Credential Manager - press the same button "
        "again. If a new clinic still shows in the list, Remove it before adding it again."
    ),
    ClinicRefusal.REGISTRY_UNREADABLE: (
        "The clinic list could not be read, so clinics cannot be changed here - fix or "
        "delete {path}, then restart the scribe."
    ),
    ClinicRefusal.LINKED_TO_LIVE_SESSION: (
        "Finish or discard the recording for {clinic} first."
    ),
    ClinicRefusal.KEY_DELETE_FAILED: (
        "The key could not be deleted from Windows Credential Manager, so {clinic} was "
        "kept - press Remove again."
    ),
}
_CLINIC_WRITE_FAILED_COPY: Final[Mapping[ClinicOperation, str]] = {
    "add": "The clinic list could not be saved, so nothing was added - press Validate again.",
    "replace": (
        "The new key was saved, but the clinic list could not be updated - press Replace "
        "key again."
    ),
    "remove": (
        "The key was deleted, but {clinic} could not be taken off the list - press Remove "
        "again."
    ),
}
_CLINIC_LOAD_PROBLEM_COPY: Final[Mapping[LoadProblem, str]] = {
    LoadProblem.UNREADABLE: "The clinic list at {path} could not be opened.",
    LoadProblem.TOO_LARGE: "The clinic list at {path} is too large to be a clinic list.",
    LoadProblem.NOT_VALID: "The clinic list at {path} is damaged or not in the expected form.",
}


def clinic_refusal_line(
    refusal: Refused, *, operation: ClinicOperation, clinic_name: str, path: Path
) -> str:
    """The status line for a refused Validate / Replace key / Remove."""
    if refusal.reason is ClinicRefusal.REGISTRY_WRITE_FAILED:
        template = _CLINIC_WRITE_FAILED_COPY[operation]
    else:
        template = _CLINIC_REFUSAL_COPY[refusal.reason]
    return template.format(clinic=clinic_name or "that clinic", path=path)


def clinic_load_problem_line(problem: LoadProblem, path: Path) -> str:
    return (
        _CLINIC_LOAD_PROBLEM_COPY[problem].format(path=path)
        + " "
        + _CLINIC_REFUSAL_COPY[ClinicRefusal.REGISTRY_UNREADABLE].format(path=path)
    )


def clinic_row(record: ClinicRecord) -> str:
    """One clinic in the list: never the key, never an id."""
    row = f"{record.display_name} - {record.host} - checked {record.validated_at:%Y-%m-%d}"
    if not record.subdomain_confirmed:
        row += " - web address not yet confirmed by a note"
    return row


def clinic_success_line(outcome: Committed | Removed) -> str:
    if isinstance(outcome, Removed):
        return (
            f"{outcome.record.display_name} removed, and its key deleted from Windows "
            "Credential Manager."
        )
    record = outcome.record
    if outcome.replaced:
        return f"The key for {record.display_name} was replaced and checked with Cliniko."
    if record.subdomain_confirmed:
        return (
            f"{record.display_name} added - Cliniko confirmed the key, your practitioner "
            f"record and {record.host}."
        )
    return (
        f"{record.display_name} added with the typed address {record.host} - it is "
        "confirmed the first time a note is checked with Cliniko."
    )


def clinic_remove_prompt(clinic_name: str) -> str:
    return (
        f"Press {CLINIC_REMOVE_CONFIRM_LABEL} to remove {clinic_name} and delete its key "
        "from this computer."
    )


__all__ = [
    "ATTRIBUTION_DID_NOT_RUN_REASON",
    "CLINICS_INTRO",
    "CLINIC_ADDRESS_HINT",
    "CLINIC_CHECKING_LINE",
    "CLINIC_CHECK_STOPPED_LINE",
    "CLINIC_KEY_CLIPBOARD_ADVICE",
    "CLINIC_NO_SELECTION_LINE",
    "CLINIC_REMOVE_CONFIRM_LABEL",
    "CLINIC_REMOVE_LABEL",
    "ClinicOperation",
    "clinic_load_problem_line",
    "clinic_refusal_line",
    "clinic_remove_prompt",
    "clinic_row",
    "clinic_success_line",
    "CONFIRM_CONSENT_BUTTON_LABEL",
    "CONSENT_CHECKBOX_LABEL",
    "CONSENT_MANUAL_REMINDER",
    "CONSENT_STALE_NOTICE",
    "CONSENT_TEXT_V1",
    "CONSENT_TEXT_V2",
    "CONSENT_TEXT_V3",
    "CONSENT_TEXT_VERSION",
    "COPY_TO_CLINIKO_ENABLED",
    "FIRST_RUN_BANNER",
    "FIRST_RUN_STYLE_LINE",
    "LANGUAGE_MODEL_ABSENT_REASON",
    "LANGUAGE_MODEL_LOAD_FAILED_LINE",
    "NOTE_STYLES",
    "PROSE_STYLES",
    "RENDERING_DONE_LINE",
    "RENDERING_IN_FLIGHT_LINE",
    "SAVE_WHILE_RENDERING_MESSAGE",
    "STYLE_PROFILE_MISSING_LINE",
    "ProseStage",
    "StyleStageResult",
    "bind_stage_result",
    "build_prose_stage",
    "carry_renderings",
    "rendering_in_flight_line",
    "reset_language_model_cache",
    "sections_to_render",
    "style_stage_line",
    "with_retained_prose",
    "STYLE_LABELS",
    "STYLE_NOT_LEARNED_LINE",
    "STYLE_PROFILE_EMPTY_REASON",
    "STYLE_SETTING_UNREADABLE_LINE",
    "STYLE_UNUSABLE_LINE",
    "NoteStyleChoice",
    "StyleOption",
    "first_run_banner_text",
    "language_model_available",
    "read_note_style",
    "save_note_style",
    "style_fallback_line",
    "style_options",
    "style_profile_line",
    "STYLE_CONSENT_STALE_REASON",
    "LEARNING_NO_PROFILE_HINT",
    "LEARNING_NOT_ATTRIBUTED_NOTE",
    "LEARNING_ON_LINE",
    "LEARNING_OPTED_OUT_HINT",
    "LEARNING_OPT_IN_LABEL",
    "LIVE_ASSEMBLED_STATUS",
    "LIVE_FALLBACK_STATUS",
    "LIVE_TRANSCRIPT_HEADER",
    "LIVE_TRANSCRIPT_PLACEHOLDER",
    "RECORDING_CONSENT_LABEL",
    "CONSENT_REQUIRED_MESSAGE",
    "NOT_LINKED_LABEL",
    "NOT_LINKED_DETAIL",
    "LINKED_VERIFIED_LABEL",
    "LINKED_UNVERIFIED_LABEL",
    "session_link_line",
    "CHROME_WAITING_LINE",
    "CHROME_CONNECTED_LINE",
    "CHROME_UNAVAILABLE_LINE",
    "CHROME_SPOKEN_PAUSE_UNAVAILABLE_LINE",
    "HOTKEY_LINES",
    "SPOKEN_PAUSE_LINES",
    "HOTKEY_FAILED_STATUS",
    "HOTKEY_RESUMED_STATUS",
    "NEW_CONSULTATION_WARNING_LINE",
    "hands_free_lines",
    "CHROME_RECHECK_LINES",
    "CHROME_REFUSALS",
    "chrome_refusal_message",
    "ChromeView",
    "chrome_view_text",
    "DISCARD_CONFIRM_MESSAGE",
    "REVIEW_OPEN_START_HINT",
    "PAUSE_CUES",
    "PAUSE_CUE_LINKED_TAIL",
    "PAUSE_CUE_UNLINKED_TAIL",
    "BLOCK_DESKTOP_LINE",
    "pause_cue_text",
    "RECOVERY_NO_ENCOUNTER_LINE",
    "RECOVERY_ENCOUNTER_LINE",
    "CHECKOUT_CONSENT_UNAVAILABLE_LINE",
    "CHECKOUT_UNLINKED_LINE",
    "CHECKOUT_REVERIFYING_LINE",
    "CHECKOUT_VERIFIED_LINE",
    "CHECKOUT_OFFLINE_LINE",
    "CHECKOUT_CLINIC_GONE_LINE",
    "CHECKOUT_CHECK_STOPPED_LINE",
    "NOTE_REFUSAL_REASONS",
    "note_refusal_line",
    "recovery_link_line",
    "checkout_link_line",
    "UNREVIEWED_HEADER",
    "RECOVERABLE_HEADER",
    "OPEN_FOR_REVIEW_LABEL",
    "REVIEW_OPEN_BUSY_LINE",
    "GENERATE_NOTE_LABEL",
    "REGENERATE_NOTE_LABEL",
    "EXPIRY_WARNING_SECONDS",
    "CLOSE_CONFIRM_SECONDS",
    "SAVED_NOTE_LINE",
    "SAVED_NOTE_CONFIG_CHANGED_LINE",
    "SAVED_NOTE_CONFIG_UNREADABLE_LINE",
    "ReviewOpening",
    "ReviewReadError",
    "read_for_review",
    "review_refusal_line",
    "saved_note_line",
    "unreviewed_row_text",
    "expiry_text",
    "expiring_soon",
    "expiry_warning_line",
    "close_expiry_message",
    "reconstruct_reminder_entries",
    "LiveTranscriberSource",
    "LEARNING_STALE_CONSENT_HINT",
    "LEARNING_UNUSABLE_HINT",
    "LEARNED_RULES_UNREADABLE_NOTE",
    "PREFILLED_MARK",
    "PROFILE_NOT_ENROLLED_LINE",
    "PROFILE_REENROL_REASON",
    "PROFILE_UNUSABLE_REASON",
    "SAVE_BUTTON_LABEL",
    "SPEAKER_MODEL_MISSING_REASON",
    "UNFINISHED_STORE_WARNING",
    "WARNING_COPY",
    "AttributionInputs",
    "AttributionReadiness",
    "ControlSet",
    "EditableLine",
    "LearningStatus",
    "NoteGenerationResult",
    "NoteReviewState",
    "PrefilledLine",
    "PrefilledState",
    "RecoverableSessionInfo",
    "RenderedAssertion",
    "RenderedProposal",
    "RenderedSection",
    "SessionControllerLike",
    "TypedLine",
    "UtteranceChoice",
    "WarningCopy",
    "WarningGroup",
    "WarningSummary",
    "assertion_label",
    "attribution_inputs",
    "attribution_readiness",
    "build_note_generator",
    "build_live_transcriber",
    "build_recovery_runner",
    "build_transcriber",
    "check_typed_text",
    "complete_block_reason",
    "config_report_lines",
    "consent_is_current",
    "controls_for_state",
    "default_sessions_root",
    "editable_lines",
    "eligible_utterances",
    "format_live_segments",
    "format_note_body",
    "format_timestamp",
    "format_transcript_text",
    "is_prefilled",
    "learned_rule_states",
    "learning_queued_line",
    "learning_status",
    "list_recoverable_sessions",
    "model_file_report_lines",
    "model_report_lines",
    "models_ready",
    "prefilled_lines",
    "provenance_label",
    "render_note_sections",
    "render_proposal",
    "save_button_label",
    "section_title",
    # Re-exported (like ``default_sessions_root``): the microphone screen reads
    # the speaker-model stat THROUGH this module so one monkeypatch reaches its
    # transition check and the readiness probe alike (peer round 55 PR-REG-006).
    "speaker_embedder_available",
    "speaker_model_report_line",
    "speaker_quotations",
    "summarise_warnings",
    "typed_lines",
    "unlearned_on_exit_line",
    "voice_profile_report_line",
    "working_draft",
]
