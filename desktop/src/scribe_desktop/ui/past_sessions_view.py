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
from datetime import datetime, tzinfo
from pathlib import Path
from typing import Final, Protocol, runtime_checkable

from scribe_desktop.audit import (
    AUDIT_REASONS,
    AUDIT_RESET_REASONS,
    AuditResetError,
    AuditRow,
    AuditUnavailable,
    PastSessionEvent,
)
from scribe_desktop.past_sessions import (
    MIN_RETENTION_DAYS,
    PAST_SESSION_REASONS,
    PastSessionError,
    PastSessionLabel,
    PastSessionListing,
    PastSessionStore,
    RetentionSweepReport,
)
from scribe_desktop.session_store import StoreWriteError
from scribe_desktop.ui.models import CUSTODY_UNEXPECTED_REASON

PAST_SESSIONS_TAB_TITLE: Final = "Past sessions"


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
        self, session_id: str, state: PastSessionEvent, *, created_at: float | None = None
    ) -> bool: ...

    def export_csv(self, path: Path) -> int: ...


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
    """The entry's date: when its recording started, else when it completed."""
    return label.started_at if label.started_at is not None else label.completed_at


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
    entry is still listed so it can be deleted."""
    label = listing.label
    if label is None:
        return ENTRY_UNREADABLE_ROW
    return f"{_local_text(_moment(label), zone)} - {who_line(label, hide_names=hide_names)}"


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
    *, opened: bool, has_saved: bool, unresolved: bool, copy_enabled: bool
) -> str | None:
    """Why Copy is unavailable — one reason per cause (round 16 LOW-002) —
    or None when it is available."""
    if not copy_enabled:
        return COPY_TURNED_OFF
    if not opened:
        return COPY_NOTHING_OPEN
    if not has_saved:
        return COPY_NO_SAVED_NOTE
    if unresolved:
        return COPY_UNRESOLVED
    return None


def delete_failed_line(exc: BaseException) -> str:
    return f"Delete failed: {failure_reason(exc)}. Nothing else changed - try again."


# --- the retention sweep (Task 3.2; Flow 4) ---------------------------------


def retention_sweep(
    store: PastSessionStore,
    audit: PastSessionsAudit | None,
    retention_days: int | None,
    now: datetime,
) -> RetentionSweepReport:
    """Delete every committed entry older than the setting through the app's
    ONE shared store (round 12 LOW-001: its per-process date cache — never
    ``sweep_past_sessions``), then record each as ``expired`` in its audit
    row, by session id only (C7), with the entry's completion date for a
    row the audit no longer holds (round 16 LOW-005: a ``pre_audit`` row
    then carries the session's date, not today's). "Never" (None) returns
    at once and decrypts nothing. Returns the store's report (what was
    deleted, and whether anything due could not be). Neither call raises."""
    report = store.sweep_report(retention_days, now)
    if audit is not None:
        for session_id, completed in report.expired:
            audit.record_past_session(session_id, "expired", created_at=completed.timestamp())
    return report
