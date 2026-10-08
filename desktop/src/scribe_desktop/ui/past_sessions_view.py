"""The Past sessions tab's Qt-free view logic (privacy-professional-controls
plan Task 3.1; Flow 5; D5, D13, D14), beside ``ui/past_sessions.py`` (the
widgets) on the ``ui/note_review.py`` pattern: every line the tab shows, the
hide-names mask, the retention choices and their warning, the write-outcome
line read from the audit row, and the retention sweep the tab and the app's
timer share (Task 3.2).

What a line may carry: a date, the patient's name as the entry's label holds
it (never when Hide names is on), and authored words. Never an id, a path, a
key or exception text (C3) — a failure names its authored reason only. The
patient's name lives only in the entry's ``label.enc``; this module formats
it for the screen and nothing else (no log, no audit, no CSV).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta, tzinfo
from functools import partial
from pathlib import Path
from typing import Final, NamedTuple, Protocol, runtime_checkable

from scribe_desktop.audit import (
    AUDIT_REASONS,
    AUDIT_RESET_REASONS,
    AuditResetError,
    AuditRow,
    AuditUnavailable,
    PastSessionEvent,
)
from scribe_desktop.exclusions import EXPORT_UNCHECKED
from scribe_desktop.past_sessions import (
    MIN_RETENTION_DAYS,
    PAST_SESSION_REASONS,
    ExportDestinationRefused,
    ExportRecovery,
    ExportUnresolvedError,
    PastSessionError,
    PastSessionLabel,
    PastSessionListing,
    PastSessionStore,
    RetentionSweepReport,
)
from scribe_desktop.session_store import StoreWriteError
from scribe_desktop.ui.models import CUSTODY_UNEXPECTED_REASON

PAST_SESSIONS_TAB_TITLE: Final = "Past sessions"


class _KeepsRows(Protocol):
    """What ``unattended_write`` asks of an audit log."""

    def keeps_rows_of(self, at: datetime) -> bool: ...


@runtime_checkable
class PastSessionsAudit(Protocol):
    """EXACTLY what the Past sessions tab and its retention sweep use of the
    audit record. ``audit.AuditLog`` satisfies it, and mypy checks the
    signatures where ``MainWindow`` hands its log to the tab. A test double
    passed to a ``MainWindow`` must implement every member; the tests pin
    each double with ``isinstance`` against this protocol — a check of each
    member's PRESENCE only (``runtime_checkable`` cannot see signatures), so
    a member the tab starts to use cannot be missing from a pinned double."""

    @property
    def failure_count(self) -> int: ...

    def key_unreadable(self) -> bool: ...

    def reset(self) -> Path | None: ...

    def row_for(self, session_id: str) -> AuditRow | None: ...

    def record_past_session(
        self,
        session_id: str,
        state: PastSessionEvent,
        *,
        created_at: float | None = None,
        create: bool = True,
    ) -> bool: ...

    def export_csv(self, path: Path) -> int: ...

    # Development-recordings review round 16 PR-MED-001: the retention
    # sweep is an UNATTENDED writer (``unattended_write``).
    def keeps_rows_of(self, at: datetime) -> bool: ...

    # Development-recordings plan Task 1.4 (D15): the kept recording's facts.
    # Declared AHEAD of their callers — Delete recording and Export recording
    # (that plan's Tasks 3.2 / 3.3) — so every pinned double carries them
    # from the commit that adds them to ``AuditLog`` (review round 8 LOW-013).
    def record_recording_deleted(
        self, session_id: str, *, created_at: float | None = None, create: bool = True
    ) -> bool: ...

    # Task 2.2 (review round 8 LOW-003): every destroyer of a kept entry
    # here — Delete now, the retention sweep, and (from Task 3.2) Delete
    # recording — records the kept fact first, since a kept Complete's own
    # audit write can fail.
    def record_recording_kept(
        self,
        session_id: str,
        at: datetime,
        *,
        created_at: float | None = None,
        create: bool = True,
    ) -> bool: ...

    def record_recording_exported(
        self, session_id: str, *, created_at: float | None = None
    ) -> bool: ...


# --- the list and the opened entry (Flow 5, D5, D13) ------------------------

PATIENT_HIDDEN: Final = "Patient hidden"
NAME_NOT_AVAILABLE: Final = "Name not available"
DESKTOP_RECORDING: Final = "Desktop recording (no Cliniko note)"
# The list row for an entry whose label cannot be read, and the line shown
# when it is selected (round 16 LOW-011: what to do next). Round 40
# PR-LOW-034: an entry that cannot be read is still kept (it may still be a
# health record — the 7-year minimum), so the next step is NOT "delete it":
# every line that names Delete now for a read failure carries H5's
# made-in-error limit and points at the downtime procedure.
ENTRY_UNREADABLE_ROW: Final = "Cannot be read on this Windows account"
UNREADABLE_DELETE_LIMIT: Final = (
    "Delete now is only for a recording made in error - read the downtime procedure "
    "before deleting it."
)
ENTRY_UNREADABLE: Final = (
    "This past session cannot be read on this Windows account. It is still kept and is "
    f"not deleted by age. {UNREADABLE_DELETE_LIMIT}"
)
NO_ENTRIES: Final = "No past sessions are kept."
LIST_GROUP_TITLE: Final = "Kept sessions"
SETTINGS_GROUP_TITLE: Final = "How long they are kept"
EXPORT_GROUP_TITLE: Final = "Audit record"
GENERATED_NOT_KEPT: Final = "Generated note not kept"
NO_SAVED_NOTE: Final = "No saved note"
GENERATED_HEADING: Final = "Generated note (what the app first produced)"
SAVED_HEADING: Final = "Saved note"
TRANSCRIPT_HEADING: Final = "Transcript"
SHOW_TRANSCRIPT_LABEL: Final = "Show transcript"
HIDE_TRANSCRIPT_LABEL: Final = "Hide transcript"
HIDE_NAMES_LABEL: Final = "Hide names"
COPY_LABEL: Final = "Copy saved note"
COPY_DONE: Final = "Saved note copied."
# Round 16 LOW-002: one reason per cause Copy is unavailable.
COPY_NO_SAVED_NOTE: Final = (
    "No saved note was kept for this session, so there is nothing to copy."
)
COPY_UNRESOLVED: Final = (
    "The saved note has an unresolved error, so it cannot be copied. Read it as shown."
)
COPY_TURNED_OFF: Final = "Copying notes is turned off in this version of Clinic Scribe."
# Pilot plan Task 1.6 (D5): a shadow recording's kept note is never copied,
# and its list row says what it was.
COPY_SHADOW: Final = (
    "This was a shadow recording for the pilot, so its note cannot be copied. Read it "
    "as shown."
)
SHADOW_MARK: Final = "shadow recording"
COPY_NOTHING_OPEN: Final = "Select a past session with a saved note first."
SELECT_FIRST: Final = "Select a past session first."
STORE_UNAVAILABLE: Final = "Past sessions are not set up in this window."
LIST_UNREADABLE: Final = "The Past sessions list could not be read just now. Open the tab again."

# --- Delete now: two clicks (the Session screen's Discard pattern) ----------

DELETE_LABEL: Final = "Delete now"
DELETE_CONFIRM_LABEL: Final = "Confirm delete"
DELETE_CONFIRM_SECONDS: Final = 10.0
# Practitioner decision 2026-10-02: a kept transcript is kept for at least 7
# years, so Delete now is only for a recording made in error. The wording is
# the limit; the behaviour (two clicks, the audit row) is unchanged.
DELETE_HELP: Final = (
    "Use Delete now only for a recording made in error: the wrong patient, a test, or "
    "one recorded without consent."
)
DELETE_CONFIRM_MESSAGE: Final = (
    "Delete this past session now? Use Delete now only for a recording made in error - "
    "the wrong patient, a test, or one recorded without consent - because a kept "
    "transcript must otherwise be kept for at least 7 years. Its notes and transcript "
    "cannot be recovered. Press Confirm delete to delete it."
)
DELETE_DONE: Final = "Past session deleted (its key was destroyed)."

# The named buttons of the two confirmations (design-system Microcopy:
# destructive actions are named for what they do, never Yes / No).
RETENTION_CONFIRM_ACTION: Final = "Delete older sessions"
AUDIT_RESET_CONFIRM_ACTION: Final = "Start a new audit record"
CONFIRM_CANCEL: Final = "Keep things as they are"

# --- retention (Agreed Scope; Flow 4) ---------------------------------------

RETENTION_HEADING: Final = "Keep past sessions for:"
# The offered settings, in the combo's order: "never" first (the default).
# Practitioner decision 2026-10-02: 7 years is the minimum, so it is the only
# other choice (the shorter ones are gone; a file holding one reads as 7
# years — ``past_sessions.LEGACY_RETENTION_DAYS``).
RETENTION_OPTIONS: Final[tuple[tuple[str, int | None], ...]] = (
    ("Until I delete them", None),
    ("7 years", MIN_RETENTION_DAYS),
)
# The plain warning the setting comes with (Agreed Scope), shown under it:
# the health-record warning (round 30 PR-MED-030 Part A), then the 7-year
# minimum and the child rule (practitioner decision 2026-10-02).
RETENTION_WARNING: Final = (
    "A kept transcript becomes part of your health record - under the VIC Health "
    "Records Act 2001, the NSW HRIP Act 2002 and the ACT Health Records (Privacy and "
    "Access) Act 1997, and elsewhere APP 11.2. It can be reached by an APP 12 access "
    "request or a subpoena. Clinic Scribe keeps it, encrypted, only in this Windows "
    "login's data folder and makes no backup of its own - but backup or sync software, "
    "or a folder location it has warned about, can still copy the encrypted files. "
    "Cliniko stays the system of record. A kept transcript is kept for at least 7 "
    "years. If the patient was a child, it must be kept until they turn 25 - Clinic "
    'Scribe does not know a patient\'s age, so choose "Until I delete them" when that '
    "applies."
)
# The settings file held a shorter window an earlier version offered: it now
# reads as 7 years. Shown until the next save writes 7 years (any retention
# choice or Hide names click) — the file is still never written unasked.
RETENTION_RAISED_LINE: Final = (
    "Your earlier Past-sessions setting was shorter than 7 years, the minimum for a "
    "kept transcript, so past sessions are now kept for 7 years. Choose a setting "
    "below to save this."
)
# The retention sweep refused a window under the 7-year minimum (a second
# line behind the settings file, which cannot hold one).
SWEEP_TOO_SHORT_LINE: Final = (
    "The retention setting is shorter than 7 years, so nothing was deleted by age."
)
SETTINGS_UNREADABLE_LINE: Final = (
    "The Past-sessions settings file cannot be read, so nothing is deleted by age and "
    "Hide names cannot be changed. Choose a retention setting to replace the file."
)
HIDE_NAMES_REFUSED: Final = (
    "Hide names cannot be changed while the settings file cannot be read. Choose a "
    "retention setting first - that replaces the file."
)
SETTINGS_NOT_SAVED: Final = "The setting could not be saved, so nothing changed."
HIDE_NAMES_NOT_SAVED: Final = (
    "Hide names could not be saved - it applies on this screen until Clinic Scribe closes."
)
# Round 16 MED-002: a retention sweep that could not finish says so. The
# retry is a later hourly check, and only while the app runs (round 18
# PR-LOW-014: never a promise of "within the hour").
SWEEP_PROBLEM_LINE: Final = (
    "Some past sessions older than the setting could not be deleted. They are kept for "
    "now; Clinic Scribe tries again at a later hourly check while it is running."
)

# --- the audit record on this tab (D9, C2, Flow 5's Export CSV) -------------

EXPORT_LABEL: Final = "Export audit record (CSV)"
EXPORT_DIALOG_TITLE: Final = "Export audit record"
EXPORT_DEFAULT_NAME: Final = "clinic-scribe-audit.csv"
EXPORT_FILTER: Final = "CSV files (*.csv)"
CSV_NOT_ENCRYPTED_LINE: Final = (
    "The CSV holds no patient names or note text, but it is not encrypted: anyone who "
    "can open the file can read it. Keep it somewhere safe and delete it when you are done."
)
EXPORT_WRITE_FAILED: Final = "the file could not be written"
# Round 16 LOW-012: the app's ONE fixed reason for an error it did not author.
UNEXPECTED_REASON: Final = CUSTODY_UNEXPECTED_REASON
AUDIT_RESET_LABEL: Final = "Start a new audit record"
AUDIT_KEY_UNREADABLE_LINE: Final = (
    "The audit record's key cannot be read on this Windows account, so recording "
    "cannot start and the audit record cannot be exported. Press Start a new audit "
    "record - the old record is set aside, unread, and nothing is deleted."
)
AUDIT_RESET_CONFIRM: Final = (
    "Start a new audit record? The old one is set aside, unread, in a folder beside "
    "it - nothing is deleted. Recording can start again afterwards."
)
AUDIT_RESET_DONE: Final = (
    "A new audit record was started. The old one was set aside, unread, beside it."
)


def retention_label(days: int | None) -> str:
    """The combo's words for a setting (an unknown value reads as days)."""
    for label, value in RETENTION_OPTIONS:
        if value == days:
            return label
    return f"{days} days"


def retention_index(days: int | None) -> int:
    """The combo index of a setting; "never" for one not offered."""
    for index, (_label, value) in enumerate(RETENTION_OPTIONS):
        if value == days:
            return index
    return 0


def _span(days: int | None) -> float:
    return math.inf if days is None else float(days)


def is_lowering(old: int | None, new: int | None) -> bool:
    """True when ``new`` keeps sessions for a SHORTER time than ``old``
    ("never" is the longest) — the change that asks first, then sweeps."""
    return _span(new) < _span(old)


def retention_confirm_text(days: int | None) -> str:
    return (
        f"Keep past sessions for only {retention_label(days).lower()}? Every kept session "
        "older than that is deleted now and cannot be recovered."
    )


def retention_changed_line(days: int | None, deleted: int, *, problem: bool = False) -> str:
    """What the tab says after a setting is saved and, when lowered, the
    sweep it ran — including, when that sweep could not delete everything
    due, that it could not (round 16 MED-002)."""
    head = (
        "Past sessions are kept until you delete them."
        if days is None
        else f"Past sessions are kept for {retention_label(days).lower()}."
    )
    if deleted == 1:
        head = f"{head} 1 older session was deleted."
    elif deleted:
        head = f"{head} {deleted} older sessions were deleted."
    return f"{head} {SWEEP_PROBLEM_LINE}" if problem else head


def retention_kept_line(days: int | None) -> str:
    """What the tab says when a lowering is declined."""
    return f"Nothing changed: past sessions are still kept as before ({retention_label(days)})."


# --- the list -----------------------------------------------------------------


def _moment(label: PastSessionLabel) -> datetime:
    """The entry's date: when its recording started, else when it completed
    (``PastSessionLabel.moment``, the one definition — hardening round 43
    SIMP-002)."""
    return label.moment


def _local_text(moment: datetime, zone: tzinfo | None) -> str:
    """``YYYY-MM-DD HH:MM`` in the practitioner's zone. Locale-free on
    purpose (``%b`` would follow whatever C locale Qt set). A time this
    computer cannot convert to local time — Windows refuses one before 1970
    — is shown in UTC instead of breaking the tab (round 16 LOW-007)."""
    try:
        return moment.astimezone(zone).strftime("%Y-%m-%d %H:%M")
    except (OSError, OverflowError, ValueError):
        return moment.strftime("%Y-%m-%d %H:%M UTC")


def who_line(label: PastSessionLabel, *, hide_names: bool) -> str:
    """Whose session (D5, D13): a desktop recording has no patient; a name
    the app did not have reads "Name not available"; Hide names masks a
    name with "Patient hidden"."""
    if label.recording == "desktop":
        return DESKTOP_RECORDING
    if label.patient_name is None:
        return NAME_NOT_AVAILABLE
    return PATIENT_HIDDEN if hide_names else label.patient_name


def entry_line(
    listing: PastSessionListing, *, hide_names: bool, zone: tzinfo | None = None
) -> str:
    """One list row: date + name (Flow 5), or the unreadable line — such an
    entry is still listed so it can be deleted. A shadow recording's row
    ends "(shadow recording)" (pilot plan Task 1.6); an entry holding a kept
    recording, "(recording kept)" (development-recordings plan Task 3.1) —
    from the listing's file check, never a decryption, and on the unreadable
    row too, so its recording can still be found and deleted (C3)."""
    label = listing.label
    if label is None:
        line = ENTRY_UNREADABLE_ROW
    else:
        line = f"{_local_text(_moment(label), zone)} - {who_line(label, hide_names=hide_names)}"
        if label.shadow:
            line = f"{line} ({SHADOW_MARK})"
    return f"{line} ({RECORDING_KEPT_MARK})" if listing.recording_kept else line


# --- the kept recording (development-recordings plan Tasks 3.1-3.3) ----------

RECORDING_KEPT_MARK: Final = "recording kept"
# D9: the review is a reminder, at 12 months after the Complete.
REVIEW_AFTER: Final = timedelta(days=365)
# Locale-free month names (``%B`` would follow whatever C locale Qt set).
_MONTHS: Final = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def review_due(label: PastSessionLabel | None, now: datetime) -> bool:
    """D9: a kept recording is due for review once 365 days have passed
    since its Complete — compared as instants (UTC), so the local zone
    never moves it. A label that cannot be read is never due (it has no
    date; its row still says the recording is kept)."""
    if label is None:
        return False
    return label.completed_at.astimezone(UTC) + REVIEW_AFTER <= now.astimezone(UTC)


def _month_text(moment: datetime, zone: tzinfo | None) -> str:
    """``October 2027`` in the practitioner's zone (UTC when this computer
    cannot convert it, as ``_local_text``)."""
    try:
        local = moment.astimezone(zone)
    except (OSError, OverflowError, ValueError):
        local = moment.astimezone(UTC)
    return f"{_MONTHS[local.month - 1]} {local.year}"


REVIEW_DUE_MARK: Final = "Review due."


def recording_line(
    label: PastSessionLabel | None, *, now: datetime, zone: tzinfo | None = None
) -> str:
    """The opened entry's line for a kept recording (Task 3.1): when its
    review falls due and, once it has, "Review due." No name (the heading
    above carries the masked one) and no id."""
    if label is None:
        return "Recording kept for development."
    due = _month_text(label.completed_at + REVIEW_AFTER, zone)
    line = f"Recording kept for development - review due {due}."
    return f"{line} {REVIEW_DUE_MARK}" if review_due(label, now) else line


def review_due_line(count: int) -> str:
    """D9's status line: how many kept recordings are due for review."""
    if count == 1:
        return (
            "1 kept recording is due for review - delete it or note in the pilot log why "
            "it is kept."
        )
    return (
        f"{count} kept recordings are due for review - delete each or note in the pilot "
        "log why it is kept."
    )


RECORDING_GROUP_TITLE: Final = "Recording kept for development"

# Task 3.2 (D8): Delete recording, two clicks like Delete now.
DELETE_RECORDING_LABEL: Final = "Delete recording"
DELETE_RECORDING_CONFIRM_LABEL: Final = "Confirm delete recording"
DELETE_RECORDING_HELP: Final = (
    "Delete recording deletes the kept recording only - the transcript and notes stay. "
    "Use it when the patient withdraws consent for the recording, or at its review."
)
DELETE_RECORDING_CONFIRM_MESSAGE: Final = (
    "Delete this recording? The transcript and notes stay. Use it when the patient "
    "withdraws consent for the recording, or at its review. The recording cannot be "
    "recovered. Press Confirm delete recording to delete it."
)
DELETE_RECORDING_DONE: Final = "Recording deleted."
NO_KEPT_RECORDING: Final = "Select a past session whose recording is kept first."


def recording_delete_failed_line(exc: BaseException) -> str:
    return (
        f"The recording could not be deleted: {failure_reason(exc)}. The transcript and "
        "notes are unchanged - try again."
    )


# Task 3.3 (D7, D10, C2): Export recording.
EXPORT_RECORDING_LABEL: Final = "Export recording (WAV)"
EXPORT_RECORDING_DIALOG_TITLE: Final = "Export recording"
EXPORT_RECORDING_FILTER: Final = "WAV audio (*.wav)"
EXPORT_RECORDING_HELP: Final = (
    "Export makes one unencrypted copy of the recording, for labelling who is speaking. "
    "It must stay on this computer's own drive - delete it when you have finished."
)


def recording_exported_line(session_id: str) -> str:
    """Export's success, naming the file it wrote (review round 21 LOW-005:
    only the chosen FOLDER is used, so a name typed in the dialog is not)."""
    return (
        f"Exported as {session_id}.wav. The file is not encrypted - delete it when you have "
        "finished labelling it."
    )


EXPORT_RECORDING_NO_LAYER: Final = (
    "The recording was not exported: Clinic Scribe cannot check where a file would go in "
    "this window."
)
# D7: the only question Export ever asks (a destination is refused, never asked).
EXPORT_SHADOW_CONFIRM: Final = (
    "This was a shadow recording; the file will hold the whole consultation unencrypted. "
    "Export it?"
)
# Review round 20 LOW: an entry whose label cannot be read is asked too
# (fail closed), but never told it WAS a shadow recording.
EXPORT_UNKNOWN_CONFIRM: Final = (
    "Clinic Scribe cannot tell whether this was a shadow recording; the file will hold the "
    "whole consultation unencrypted. Export it?"
)
EXPORT_SHADOW_ACTION: Final = "Export the recording"
# Review round 21 LOW-006: no example folder — Documents itself is inside
# OneDrive (refused) on many Windows 11 computers.
EXPORT_CHOOSE_LOCAL: Final = "Choose a folder on this computer's own drive."


def export_confirm_question(label: PastSessionLabel | None) -> str | None:
    """D7: the question Export asks first — for a shadow recording, and for
    one whose label cannot be read — or None (no question)."""
    if label is None:
        return EXPORT_UNKNOWN_CONFIRM
    return EXPORT_SHADOW_CONFIRM if label.shadow else None


def export_refused_line(reason: str) -> str:
    """A destination ``exclusions.check_export_location`` refused: its fixed
    reason, then where to choose instead (round 1 PR-HIGH-002: refused,
    never "export anyway")."""
    return f"The recording was not exported: {reason} {EXPORT_CHOOSE_LOCAL}"


def export_recording_failed_line(exc: BaseException, session_id: str) -> str:
    """An export the store refused or could not finish — its authored
    reason; a partial file that could not be removed says so first, NAMED
    (review round 20 LOW: its session id is the only way to find it) — as
    is every file a refusal is about (review round 21 LOW-005)."""
    reason = exc.reason if isinstance(exc, PastSessionError) else None
    if isinstance(exc, ExportDestinationRefused):
        # Codex round 23 PR-HIGH-001: the store's own check, on the resolved
        # folder, refused — the same line as the tab's check would show.
        return export_refused_line(exc.line or EXPORT_UNCHECKED)
    if reason == "export_cleanup_failed":
        return (
            "The recording could not be exported. A partial unencrypted file "
            f"{session_id}.wav.part may remain in the folder you chose - delete it by hand now."
        )
    if reason == "export_exists":
        return (
            f"The recording was not exported: {session_id}.wav is already in the folder you "
            "chose, and it is never replaced."
        )
    if reason == "export_part_exists":
        return (
            f"The recording was not exported: a partial export file {session_id}.wav.part is "
            "already in the folder you chose - delete it by hand first."
        )
    if isinstance(exc, ExportUnresolvedError) and exc.session_ids:
        names = ", ".join(f"{sid}.wav.part" for sid in exc.session_ids)
        return (
            "The recording was not exported: a partial file from an earlier export could not "
            f"be removed from the folder it was exported to - delete {names} by hand first."
        )
    return f"The recording was not exported: {failure_reason(exc)}."


def export_recovery_lines(recovery: ExportRecovery) -> list[str]:
    """The start-up lines ``PastSessionStore.recover_exports`` owes (Task
    3.3): one per partial export file it could not remove — named by its
    session id, the only way to find it — one when the export record could
    not be read and was started again, and one when it could not be opened
    this time."""
    lines = [
        f"A partial export file {session_id}.wav.part could not be removed from the folder "
        "you chose - delete it by hand."
        for session_id in recovery.kept
    ]
    if recovery.reset:
        lines.append(
            "Clinic Scribe's record of recording exports could not be read and was started "
            "again, so a partial export file (its name ends .wav.part) may remain in a folder "
            "you exported to - delete it by hand."
        )
    if recovery.busy:
        # Review round 21 LOW-011: a record that can never be opened is not
        # silent at start-up.
        lines.append(
            "Clinic Scribe could not open its record of recording exports, so it could not "
            "check for a partial export file (its name ends .wav.part) left by an interrupted "
            "export - it will check again next time."
        )
    return lines


def sorted_listings(listings: Sequence[PastSessionListing]) -> list[PastSessionListing]:
    """Newest first; entries whose label cannot be read last. A Sequence,
    not any iterable: it is read twice, and a generator would silently drop
    the unreadable entries (H2 round 34 SIMP-006)."""
    dated = [(item, item.label) for item in listings if item.label is not None]
    unreadable = [item for item in listings if item.label is None]
    dated.sort(key=lambda pair: _moment(pair[1]).timestamp(), reverse=True)
    return [item for item, _label in dated] + unreadable


def started_epoch(label: PastSessionLabel | None) -> float | None:
    """A ``pre_audit`` row's date for an audit update (D8), from the label."""
    if label is None:
        return None
    return _moment(label).timestamp()


def audit_moment(label: PastSessionLabel | None) -> datetime | None:
    """The moment an audit row for ``label``'s session is filed and judged
    by — its START (``begin`` files the row in the local month the session
    started), else its completion; None with no label."""
    return None if label is None else _moment(label)


class UnattendedWrite(NamedTuple):
    """How an unattended audit writer writes one session's row: the
    ``created_at`` and ``create`` to pass to every ``record_*`` call."""

    created_at: float | None
    create: bool


def unattended_write(audit: _KeepsRows, moment: datetime | None) -> UnattendedWrite | None:
    """THE rule for every UNATTENDED audit writer — the start-up repairs and
    every sweep tick (``app.record_reconciled_commit``, ``repair_kept_facts``,
    ``record_deleted_recordings``) and the retention sweep (its kept and
    deletion facts and its ``expired`` outcome) — so the class of
    development-recordings review rounds 11, 14, 15 and 16 cannot recur at
    a new site: ``moment`` is the session's ``audit_moment``. A month the
    audit prune has passed (``keeps_rows_of`` False) → None: write nothing,
    never re-make a row the prune removed. No moment (no readable label) →
    the EXISTING row only (``create=False``): there is no date to judge the
    window by. Otherwise a missing row is re-made in the session's own month
    (D8). A DELIBERATE practitioner action (Delete now, and from Task 3.2
    Delete recording and Export) records its event instead — it makes a row
    even then (review round 15 PR-MED-003). NEVER raises (None)."""
    if moment is None:
        return UnattendedWrite(None, create=False)
    try:
        if not audit.keeps_rows_of(moment):
            return None
        return UnattendedWrite(moment.timestamp(), create=True)
    except Exception:  # noqa: BLE001 - fail towards making nothing
        return None


# --- the write outcome, from the audit row (Flow 5) -------------------------

WRITE_NO_ROW: Final = "Cliniko write: no audit record is kept for this session."
WRITE_ROW_UNAVAILABLE: Final = "Cliniko write: the audit record cannot be read just now."
WRITE_NOT_ATTEMPTED: Final = "Cliniko write: not attempted."
WRITE_REFUSED_BEFORE: Final = "Cliniko write: not sent - it was refused before anything was sent."
WRITE_REFUSED: Final = "Cliniko write: refused by Cliniko"
WRITE_UNCONFIRMED: Final = (
    "Cliniko write: the outcome was not confirmed - check the note in Cliniko."
)


def write_outcome_line(
    row: AuditRow | None, *, unavailable: bool = False, zone: tzinfo | None = None
) -> str:
    """The Cliniko draft write as the session's audit row last recorded it
    (Task 1.4) — the outcome and, once written, when. Never a refusal code
    or an id."""
    if unavailable:
        return WRITE_ROW_UNAVAILABLE
    if row is None:
        return WRITE_NO_ROW
    write = row.write
    attempts = f" ({write.attempts} attempts)" if write.attempts > 1 else ""
    if write.last_outcome == "written":
        when = (
            f" on {_local_text(write.written_at, zone)}" if write.written_at is not None else ""
        )
        return f"Cliniko write: written as a draft{when}{attempts}."
    if write.last_outcome == "refused":
        return f"{WRITE_REFUSED}{attempts}."
    if write.last_outcome in ("attempting", "unknown"):
        return WRITE_UNCONFIRMED
    if write.last_refusal is not None:
        return WRITE_REFUSED_BEFORE
    return WRITE_NOT_ATTEMPTED


# --- the status lines ---------------------------------------------------------


def audit_failures_line(count: int) -> str:
    """C2's "counted and shown": the audit updates that failed since start."""
    noun = "update" if count == 1 else "updates"
    return (
        f"{count} audit record {noun} could not be saved since Clinic Scribe started. "
        "Your recordings and notes were not affected."
    )


def undated_line(count: int) -> str:
    """Round 17 LOW-020: entries whose date this account cannot read are
    kept whatever the retention setting — the tab says so, and (round 40
    PR-LOW-034) that Delete now is only for a recording made in error."""
    if count == 1:
        return (
            "1 past session cannot be read on this Windows account, so it is not deleted "
            f"by age and is still kept. {UNREADABLE_DELETE_LIMIT}"
        )
    return (
        f"{count} past sessions cannot be read on this Windows account, so they are not "
        "deleted by age and are still kept. Delete now is only for a recording made in "
        "error - read the downtime procedure before deleting them."
    )


def export_done_line(count: int) -> str:
    """No file name (round 16 LOW-001): a name the practitioner typed is free
    text, and a status line carries authored words only (C3)."""
    rows = "1 audit row" if count == 1 else f"{count} audit rows"
    return f"Exported {rows} to the file you chose. The file is not encrypted."


def failure_reason(exc: BaseException) -> str:
    """The plain sentence for a refusal this tab shows — the ONE code-to-
    sentence mapping, so the screen and its tests agree on every line: a
    known ``PastSessionError``, ``AuditUnavailable`` or ``AuditResetError``
    code reads its store's authored sentence; anything else, an unknown code
    included, reads the app's one fixed line. Never a raw code or exception
    text (C3)."""
    if isinstance(exc, PastSessionError):
        return PAST_SESSION_REASONS.get(exc.reason, UNEXPECTED_REASON)
    if isinstance(exc, AuditUnavailable):
        return AUDIT_REASONS.get(exc.reason, UNEXPECTED_REASON)
    if isinstance(exc, AuditResetError):
        return AUDIT_RESET_REASONS.get(exc.reason, UNEXPECTED_REASON)
    return UNEXPECTED_REASON


def export_failed_line(exc: BaseException) -> str:
    """A file the export could not write (the store's ``StoreWriteError``, or
    the OS's own error naming the path) reads ``EXPORT_WRITE_FAILED``."""
    reason = (
        EXPORT_WRITE_FAILED
        if isinstance(exc, (StoreWriteError, OSError))
        else failure_reason(exc)
    )
    return f"The audit record could not be exported: {reason}."


def reset_failed_line(exc: BaseException) -> str:
    return (
        f"A new audit record could not be started: {failure_reason(exc)}. "
        "Nothing was deleted."
    )


def open_failed_line(exc: BaseException) -> str:
    """An entry that cannot be opened (round 40 PR-LOW-034): the reason, then
    the made-in-error limit — never "delete it" as the remedy for a read
    failure. No "still kept" claim: the reason may be that it is gone."""
    return f"This past session cannot be opened: {failure_reason(exc)}. {UNREADABLE_DELETE_LIMIT}"


def copy_unavailable_reason(
    *, opened: bool, has_saved: bool, unresolved: bool, copy_enabled: bool, shadow: bool
) -> str | None:
    """Why Copy is unavailable — one reason per cause (round 16 LOW-002) —
    or None when it is available. A shadow recording's entry (pilot plan
    Task 1.6) is refused before anything about its note."""
    if not copy_enabled:
        return COPY_TURNED_OFF
    if not opened:
        return COPY_NOTHING_OPEN
    if shadow:
        return COPY_SHADOW
    if not has_saved:
        return COPY_NO_SAVED_NOTE
    if unresolved:
        return COPY_UNRESOLVED
    return None


def delete_failed_line(exc: BaseException) -> str:
    return f"Delete failed: {failure_reason(exc)}. Nothing else changed - try again."


# --- the retention sweep (Task 3.2; Flow 4) ---------------------------------


def _record_kept(
    audit: PastSessionsAudit,
    session_id: str,
    completed: datetime,
    started: datetime,
    recording_gone: bool,
) -> bool:
    """The retention sweep's kept fact (``kept_at`` = the completion) — and,
    for a recording already deleted but not yet tidied (review round 15
    PR-MED-002), that deletion too — under the unattended rule (review
    round 16 PR-MED-001: judged and dated by the session's start; a row the
    prune removed is never re-made, and nothing is then owed). True when
    every write landed or none was owed."""
    write = unattended_write(audit, started)
    if write is None:
        return True
    kept = audit.record_recording_kept(
        session_id, completed, created_at=write.created_at, create=write.create
    )
    if not recording_gone:
        return kept
    deleted = audit.record_recording_deleted(
        session_id, created_at=write.created_at, create=write.create
    )
    return deleted and kept


def retention_sweep(
    store: PastSessionStore,
    audit: PastSessionsAudit | None,
    retention_days: int | None,
    now: datetime,
) -> RetentionSweepReport:
    """Delete every committed entry older than the setting through the app's
    ONE shared store (round 12 LOW-001: its per-process date cache — never
    ``sweep_past_sessions``), then record each as ``expired`` in its audit
    row, by session id only (C7), under the unattended rule
    (``unattended_write``; development-recordings review round 16
    PR-MED-001): a row the audit no longer holds is re-made dated by the
    session's START (privacy round 16 LOW-005: the session's date, not
    today's) — unless the prune removed it, when nothing is written: an
    expiry is the scheduled end of the retention minimum, reached together
    with the audit's own seven years, not an early destruction the audit
    must show (Delete now records itself, review round 15). "Never" (None) returns
    at once and decrypts nothing. Returns the store's report (what was
    deleted, and whether anything due could not be). Neither call raises.
    Development-recordings plan Task 2.2 (review round 8 LOW-003): an
    expiring entry that holds a kept recording first gets its row's
    ``recording.kept_at`` — idempotent — so the ``expired`` outcome can
    record ``recording.deleted_at`` even when the Complete's own audit write
    failed; review round 14 PR-MED-003: recorded BEFORE the entry is deleted
    (``before_held_delete``), never after, so no interruption between the
    two loses it; round 15 PR-MED-002: a recording already deleted but not
    yet tidied gets its deletion recorded there too, and the entry is held
    (retention is a minimum) while that cannot be recorded. The ``expired``
    outcome follows the deletion (it is true only once the entry is
    gone)."""
    report = store.sweep_report(
        retention_days,
        now,
        before_held_delete=None if audit is None else partial(_record_kept, audit),
    )
    if audit is not None:
        started = dict(report.started)
        for session_id, completed in report.expired:
            write = unattended_write(audit, started.get(session_id, completed))
            if write is not None:
                audit.record_past_session(
                    session_id, "expired", created_at=write.created_at, create=write.create
                )
    return report
