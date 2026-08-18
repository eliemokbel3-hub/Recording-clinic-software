"""GUI-free view logic for the Step 10 screens (unit-testable without Qt).

Everything here is pure logic or thin composition over the real Phase-2
modules (session/session_store/speech/transcription/benchmark). Nothing
in this module may log or persist clinical text: transcript rendering
returns a string for DISPLAY ONLY.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol

from scribe_desktop.note import (
    CANONICAL_SECTIONS,
    ExtractiveNoteProvider,
    GeneratedNote,
    NoteDraft,
    NoteModelProvider,
    NoteProposal,
    NoteSectionKey,
    NoteWarning,
    compose_draft,
)
from scribe_desktop.note_config import NoteConfig, load_note_config
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import GenerationLease, RecordingSession, SessionState
from scribe_desktop.session_store import (
    AUDIO_FILENAME,
    KEY_FILENAME,
    RECOVERY_WINDOW,
    SESSION_ID_PATTERN,
    SessionStoreError,
    default_sessions_root,
    earliest_trusted_timestamp,
    key_blob_is_dead,
    read_store_header,
    store_has_footer,
)
from scribe_desktop.speech import SileroVad, vad_model_available
from scribe_desktop.transcription import (
    DEFAULT_WHISPER_MODEL,
    RecoveryOutcome,
    TranscriptDocument,
    WhisperSpeechProvider,
    read_transcript,
    recover_session_transcription,
    resolve_whisper_model,
    transcribe_session,
    whisper_model_available,
)

# Single-sourced session-id format (round 42 LOW-010).
_SESSION_ID_RE = re.compile(SESSION_ID_PATTERN)

# Binding Step-10 note (PR-HIGH-007 residual): shown whenever a recovered
# store carries no complete Finish footer.
UNFINISHED_STORE_WARNING = (
    "Warning: recording did not finish cleanly; the tail may be missing."
)


class SessionControllerLike(Protocol):
    """The controller surface the screens depend on (fakes in tests)."""

    @property
    def state(self) -> SessionState: ...

    @property
    def level(self) -> float: ...

    @property
    def session(self) -> RecordingSession | None: ...

    def start(self, device_id: int) -> RecordingSession: ...

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
    SessionState.QUEUED: ControlSet(),
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
            )
        )
    return infos


# ---------------------------------------------------------------------------
# Transcript rendering (display only — never persisted, never logged).
# ---------------------------------------------------------------------------


def format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


def format_transcript_text(document: TranscriptDocument) -> str:
    """Render a transcript for the inspection view: speaker labels visible
    on every segment, uncertain words marked as ``[word?]``."""
    lines: list[str] = []
    for segment in document.transcript_segments:
        span = (
            f"[{format_timestamp(segment.start_seconds)}"
            f"-{format_timestamp(segment.end_seconds)}]"
        )
        words = " ".join(
            f"[{word.word_text}?]" if word.uncertain else word.word_text
            for word in segment.transcript_words
        )
        lines.append(f"{span} {segment.speaker}: {words}")
    if not lines:
        return "(no speech detected)"
    return "\n".join(lines)


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

# Task 7.1 / 9.1: the note is the RATIFIED copyable surface, but ONLY once
# the Task 9.1 shipping gate passes (the practitioner judging the extractive
# output acceptable over a real-transcript set — plan Shipping Gate). That
# gate has NOT passed, so copy ships DISABLED: the Note tab binds its copy
# affordance to THIS recorded decision, never unconditionally. The transcript
# stays display-only ALWAYS, regardless of this flag (Critical Constraint).
COPY_TO_CLINIKO_ENABLED: Final[bool] = False

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

_SECTION_TITLES: Final[Mapping[NoteSectionKey, str]] = {
    section.key: section.title for section in CANONICAL_SECTIONS
}

_PROVENANCE_LABELS: Final[Mapping[str, str]] = {
    "transcript": "from transcript",
    "autofill": "autofill (clinician-authored)",
    "prefill": "prefill (clinician-authored)",
}


def provenance_label(provenance: str) -> str:
    """Human label distinguishing a line's provenance (Task 7.1: provenance
    visibly distinguished). Autofill and prefill are clinician-authored
    boilerplate; transcript lines are quoted speech verified by reconstruction.
    """
    return _PROVENANCE_LABELS.get(provenance, provenance)


@dataclass(frozen=True)
class RenderedAssertion:
    """One assertion rendered as ONE bullet — never assembled prose (plan
    Critical Constraint: assertions render on hard boundaries)."""

    assertion_id: str
    provenance: str
    provenance_label: str
    text: str


@dataclass(frozen=True)
class RenderedSection:
    section_key: NoteSectionKey
    title: str
    assertions: tuple[RenderedAssertion, ...]


def format_note_body(note: GeneratedNote) -> str:
    """The composed note as display text — canonical sections, each assertion
    ONE bullet with a provenance tag. This is the copyable surface (gated on
    the 9.1 shipping decision); it is display text only, never persisted or
    logged here."""
    blocks: list[str] = []
    for section in render_note_sections(note):
        lines = [f"{section.title}:"]
        for assertion in section.assertions:
            lines.append(f"  - {assertion.text}  [{assertion.provenance_label}]")
        blocks.append("\n".join(lines))
    if not blocks:
        return "(no note content)"
    return "\n\n".join(blocks)


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
                title=_SECTION_TITLES[section.section_key],
                assertions=tuple(
                    RenderedAssertion(
                        assertion_id=assertion.assertion_id,
                        provenance=assertion.provenance,
                        provenance_label=provenance_label(assertion.provenance),
                        text=assertion.text,
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
        section_title=_SECTION_TITLES[proposal.section_key],
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
    "clinician_asserted": WarningCopy(
        "A clinician-authored line was added (autofill or prefill)",
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
    "high_risk_omission": WarningCopy(
        "A number, name or medication the clinician said is not in the note",
        None,
        "Check the transcript beside the note, then acknowledge.",
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
            titles = ", ".join(_SECTION_TITLES[key] for key in dropped)
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


def build_note_generator(
    *,
    clinician_speaker: str,
    template_profile_id: str | None,
    prefill_id: str | None = None,
    config_root: Path | None = None,
    provider_factory: Callable[[], NoteModelProvider] = ExtractiveNoteProvider,
) -> Callable[[Path, SessionCrypto], NoteGenerationResult]:
    """A generation worker for ``SessionController.with_generation_custody``.

    Reads the transcript FROM DISK (the exact on-disk artifact ``write_note``
    re-verifies against), loads the note config, and composes the draft with
    the CONFIRMED role and template profile (Task 7.5 — ``clinician_speaker``
    is required and typed ``str``, so a generator cannot be built without a
    confirmed role). Config load and provider construction happen at call
    time, inside the worker thread, off the GUI thread — mirroring
    ``build_transcriber``. Returns the draft plus the resolved config."""

    def generator(session_dir: Path, crypto: SessionCrypto) -> NoteGenerationResult:
        document = read_transcript(session_dir, crypto)
        config = load_note_config(config_root)
        draft = compose_draft(
            document,
            config,
            provider_factory(),
            template_profile_id=template_profile_id,
            clinician_speaker=clinician_speaker,
            prefill_id=prefill_id,
        )
        return NoteGenerationResult(draft=draft, config=config, document=document)

    return generator


# ---------------------------------------------------------------------------
# Benchmark / model report panel content.
# ---------------------------------------------------------------------------


def model_report_lines() -> list[str]:
    """Model-readiness lines for the microphone screen's report panel.

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
    ]


def models_ready() -> bool:
    """True when a USABLE whisper model (default or fallback) and the VAD
    model are both locally complete."""
    return whisper_model_available(resolve_whisper_model()) and vad_model_available()


# ---------------------------------------------------------------------------
# Pipeline factories (constructed lazily, inside the worker thread).
# ---------------------------------------------------------------------------


def build_transcriber(
    model_name: str | None = None,
) -> Callable[[Path, SessionCrypto], TranscriptDocument]:
    """A ``SessionController.transcribe`` transcriber over the real ML stack.

    Models load inside the call (worker thread) so the GUI thread never
    blocks on CTranslate2/onnxruntime initialisation. ``model_name=None``
    (the default) applies the Step 13 fallback policy at call time via
    ``resolve_whisper_model``; the resolved name is recorded in the
    transcript document so the artifact says which model actually ran.
    """

    def transcriber(session_dir: Path, crypto: SessionCrypto) -> TranscriptDocument:
        name = model_name if model_name is not None else resolve_whisper_model()
        vad = SileroVad()
        provider = WhisperSpeechProvider(model_name=name)
        return transcribe_session(
            session_dir,
            crypto,
            provider,
            vad.frame_probability,
            require_footer=True,
            model_name=name,
        )

    return transcriber


def build_recovery_runner(
    model_name: str | None = None,
) -> Callable[[Path], RecoveryOutcome]:
    """Flow 3 resume-processing over the real ML stack (worker thread).

    Same Step 13 call-time model resolution as ``build_transcriber``.
    """

    def runner(session_dir: Path) -> RecoveryOutcome:
        name = model_name if model_name is not None else resolve_whisper_model()
        vad = SileroVad()
        provider = WhisperSpeechProvider(model_name=name)
        return recover_session_transcription(
            session_dir, provider, vad.frame_probability, model_name=name
        )

    return runner


__all__ = [
    "CONSENT_MANUAL_REMINDER",
    "COPY_TO_CLINIKO_ENABLED",
    "UNFINISHED_STORE_WARNING",
    "WARNING_COPY",
    "ControlSet",
    "NoteGenerationResult",
    "NoteReviewState",
    "RecoverableSessionInfo",
    "RenderedAssertion",
    "RenderedProposal",
    "RenderedSection",
    "SessionControllerLike",
    "WarningCopy",
    "WarningGroup",
    "WarningSummary",
    "build_note_generator",
    "build_recovery_runner",
    "build_transcriber",
    "complete_block_reason",
    "config_report_lines",
    "controls_for_state",
    "default_sessions_root",
    "format_note_body",
    "format_timestamp",
    "format_transcript_text",
    "list_recoverable_sessions",
    "model_report_lines",
    "models_ready",
    "provenance_label",
    "render_note_sections",
    "render_proposal",
    "speaker_quotations",
    "summarise_warnings",
]
