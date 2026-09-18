"""GUI-free view logic for the Step 10 screens (unit-testable without Qt).

Everything here is pure logic or thin composition over the real Phase-2
modules (session/session_store/speech/transcription/benchmark). Nothing
in this module may log or persist clinical text: transcript rendering
returns a string for DISPLAY ONLY.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, Protocol

from scribe_desktop.note import (
    CANONICAL_SECTION_KEYS,
    CANONICAL_SECTIONS,
    ExtractiveNoteProvider,
    GeneratedNote,
    GeneratedSection,
    NoteAssertion,
    NoteDraft,
    NoteModelProvider,
    NoteProposal,
    NoteSectionKey,
    NoteWarning,
    admissible_sections,
    compose_draft,
    reconstruct_span_text,
)
from scribe_desktop.note_config import NoteConfig, load_note_config
from scribe_desktop.practitioner_profile import (
    PractitionerProfile,
    ProfileUnusableError,
    load_profile,
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
    draft and nothing else changes. The proposals travel unchanged, so the
    resolution evidence keeps matching. Validated on construction: a
    duplicate assertion id or a non-transcript addition is refused by
    ``NoteDraft`` itself."""
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
    )


def section_title(key: NoteSectionKey) -> str:
    return _SECTION_TITLES[key]


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


LineState = Literal["routed", "removed", "moved", "added"]


@dataclass(frozen=True)
class EditableLine:
    """One transcript-provenance line of the working note with its edit
    state (Task 5.1b): ``routed`` (the provider's, in place), ``removed``
    (the provider's, subtracted), ``moved`` (the provider's, subtracted and
    re-added under ``moved_to``) or ``added`` (a manual addition with no
    provider counterpart). ``allowed_sections`` are the sections a Move may
    target — the ownership rule, minus the section it is in."""

    assertion_id: str
    segment_index: int
    section_key: NoteSectionKey
    label: str
    state: LineState
    moved_to: NoteSectionKey | None
    allowed_sections: tuple[NoteSectionKey, ...]


def editable_lines(
    draft: NoteDraft,
    document: TranscriptDocument,
    *,
    removed: Collection[str],
    additions: Mapping[str, NoteAssertion],
) -> tuple[EditableLine, ...]:
    """The rows of the Note tab's line editor: the provider's transcript
    lines in note order (each carrying its remove/move state) followed by
    the manual additions that are not the re-added leg of a move."""
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
                continue
            if coords.segment_index >= len(document.transcript_segments):
                continue  # Check 1's source_coords_invalid owns this line
            segment_index = coords.segment_index
            manual = manual_by_segment.get(segment_index)
            state: LineState = "routed"
            moved_to: NoteSectionKey | None = None
            if assertion.assertion_id in removed:
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
                )
            )
    for assertion in additions.values():
        coords = assertion.note_span.source_coords
        if coords is None or coords.segment_index in covered:
            continue
        if coords.segment_index >= len(document.transcript_segments):
            continue
        lines.append(
            EditableLine(
                assertion.assertion_id,
                coords.segment_index,
                assertion.section_key,
                f"{section_title(assertion.section_key)} - {_lead_words(assertion.text)}",
                "added",
                None,
                allowed_for(coords.segment_index, assertion.section_key),
            )
        )
    return tuple(lines)


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
    "Phrase learning is on: lines you add or move are learned when you press Save note "
    "on this tab."
)
# Shown on the Note tab's learning line while phrases are QUEUED (live smoke
# 2026-09-17: the practitioner read the queue as done and left the review
# without pressing Save note on this tab — nothing is written on any other
# exit, by design, so the line must name the button and the tab).
LEARNING_NOT_ATTRIBUTED_NOTE: Final = (
    "Not learned: this line is not attributed to you - only your own lines are learned."
)


def learning_queued_line(count: int) -> str:
    """The learning line while ``count`` phrases wait for Save: names the
    exact control that writes them and where it is."""
    noun = "phrase" if count == 1 else "phrases"
    return (
        f"Phrase learning is on: {count} {noun} queued - press Save note on this tab to "
        "learn them (Cancel, Delete and Complete learn nothing)."
    )


def unlearned_on_exit_line(count: int) -> str:
    """The sentence the Transcript screen appends after a review left with
    ``count`` phrases still queued (practitioner-profile plan Task 5.6): the
    queue is written by Save note only, so every other exit drops it — said
    once, where the practitioner lands, never a modal."""
    if count == 1:
        return "1 queued phrase was not learned - only Save note on the Note tab learns them."
    return (
        f"{count} queued phrases were not learned - only Save note on the Note tab learns "
        "them."
    )


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
        draft = compose_draft(
            document,
            config,
            provider_factory(config),
            template_profile_id=template_profile_id,
            clinician_speaker=clinician_speaker,
            prefill_id=prefill_id,
        )
        return NoteGenerationResult(draft=draft, config=config, document=document)

    return generator


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
CONSENT_TEXT_VERSION: Final = "consent-v2"
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
    f"Version {CONSENT_TEXT_VERSION}."
)
CONSENT_CHECKBOX_LABEL: Final = (
    "I agree - store an encrypted fingerprint of my voice on this computer"
)
# The second checkbox, off by default (Config / Environment / Deployment Impact).
LEARNING_OPT_IN_LABEL: Final = (
    "Also learn my phrasing from lines I add or move during review (saved when I save "
    "the note)"
)
# Shown on the Practitioner tab when a readable profile's consent record
# carries an older text version (Task 5.0): the box is left unticked and
# editable, Record needs a fresh tick, and learning is off until re-consent.
CONSENT_STALE_NOTICE: Final = (
    "The consent text has changed - please read it and tick again. Phrase learning stays "
    "off until you confirm."
)
CONFIRM_CONSENT_BUTTON_LABEL: Final = "Confirm consent"


def consent_is_current(profile: PractitionerProfile) -> bool:
    """True when the profile's consent record carries the CURRENT text
    version — the only record that pre-ticks the consent box or enables
    phrase learning (Task 5.0)."""
    return profile.consent.consent_text_version == CONSENT_TEXT_VERSION


# D10: first run ASKS, never blocks — shown on the Practitioner tab, which the
# main window selects at startup when no profile exists.
FIRST_RUN_BANNER: Final = (
    "Set up your voice profile so the app always knows which words are yours - you can "
    "still record without it."
)


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


def build_transcriber(
    model_name: str | None = None,
    *,
    attribution: Callable[[], AttributionInputs] = attribution_inputs,
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
    """

    def transcriber(session_dir: Path, crypto: SessionCrypto) -> TranscriptDocument:
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


__all__ = [
    "ATTRIBUTION_DID_NOT_RUN_REASON",
    "CONFIRM_CONSENT_BUTTON_LABEL",
    "CONSENT_CHECKBOX_LABEL",
    "CONSENT_MANUAL_REMINDER",
    "CONSENT_STALE_NOTICE",
    "CONSENT_TEXT_V1",
    "CONSENT_TEXT_V2",
    "CONSENT_TEXT_VERSION",
    "COPY_TO_CLINIKO_ENABLED",
    "FIRST_RUN_BANNER",
    "LEARNING_NO_PROFILE_HINT",
    "LEARNING_NOT_ATTRIBUTED_NOTE",
    "LEARNING_ON_LINE",
    "LEARNING_OPTED_OUT_HINT",
    "LEARNING_OPT_IN_LABEL",
    "LEARNING_STALE_CONSENT_HINT",
    "LEARNING_UNUSABLE_HINT",
    "PROFILE_NOT_ENROLLED_LINE",
    "PROFILE_REENROL_REASON",
    "PROFILE_UNUSABLE_REASON",
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
    "RecoverableSessionInfo",
    "RenderedAssertion",
    "RenderedProposal",
    "RenderedSection",
    "SessionControllerLike",
    "UtteranceChoice",
    "WarningCopy",
    "WarningGroup",
    "WarningSummary",
    "attribution_inputs",
    "attribution_readiness",
    "build_note_generator",
    "build_recovery_runner",
    "build_transcriber",
    "complete_block_reason",
    "config_report_lines",
    "consent_is_current",
    "controls_for_state",
    "default_sessions_root",
    "editable_lines",
    "eligible_utterances",
    "format_note_body",
    "format_timestamp",
    "format_transcript_text",
    "learning_queued_line",
    "learning_status",
    "list_recoverable_sessions",
    "model_file_report_lines",
    "model_report_lines",
    "models_ready",
    "provenance_label",
    "render_note_sections",
    "render_proposal",
    "section_title",
    # Re-exported (like ``default_sessions_root``): the microphone screen reads
    # the speaker-model stat THROUGH this module so one monkeypatch reaches its
    # transition check and the readiness probe alike (peer round 55 PR-REG-006).
    "speaker_embedder_available",
    "speaker_model_report_line",
    "speaker_quotations",
    "summarise_warnings",
    "unlearned_on_exit_line",
    "voice_profile_report_line",
    "working_draft",
]
