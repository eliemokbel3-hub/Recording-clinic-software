"""The Past sessions tab (privacy-professional-controls plan Task 3.1; Flow 5;
D3, D5, D9, D13, D14; C2, C3, C5).

What the archive kept at each non-mock Complete, opened one entry at a time:
the generated note (what the app first produced) beside the saved note, the
Cliniko write outcome from the session's audit row, Copy of the SAVED note
only, and the transcript behind "Show transcript". Around the list: the
retention setting with its warning (lowering it asks first, then sweeps;
"Until I delete them" or 7 years — the 7-year minimum, practitioner decision
2026-10-02), Hide names, a two-click Delete now (worded for a recording made
in error only), Export of the audit record as CSV, the intended-use line
(D14) and a persistent status line (an unreadable setting, a removed shorter
setting read as 7 years, a sweep that refused a window under 7 years, a
retention sweep that could not finish, an unreadable audit key with D9's
"Start a new audit record", the audit updates that failed, and Task 4.1's
start-up exclusion warnings — fixed lines ``app.main`` computed once).

Custody and content rules:
- Everything runs on the GUI thread (C5), like the stores it reads.
- Opening the tab re-reads the settings file and lists the entries
  (``label.enc`` only, one key unwrap each); opening an entry decrypts that
  entry and its one audit row. Leaving the tab (``on_left``) drops the
  opened entry's text AND every listed name from the widgets and from
  memory, so clinical text and names are held only while the tab is in
  front.
- The retention sweep (``run_retention_sweep`` — at start-up and at most
  hourly from ``app.main``'s timer, and after a lowered setting) loads the
  setting, sweeps the shared store and records ``expired``; it decrypts no
  label under "never" (the store returns at once) and re-lists nothing:
  deleted rows are dropped from the list in memory.
- The settings file (D13): an unreadable one deletes nothing, HIDES names
  (fail toward hiding) and is never overwritten except by an explicit
  retention choice; a Hide names choice that could not be saved is kept for
  the rest of the run, whatever later reloads read.
- Every copy goes through ``ui.note._place_note_text`` (the three Windows
  formats that keep it out of clipboard history and cloud sync — the threat
  model's Phase 3A surface 4), only for a kept saved note with no unresolved
  error, and only under the recorded copy flag. The panels are display-only
  (``NoTextInteraction``), so nothing bypasses that placement.
- Display strings are set as plain text. No name, path or exception text
  reaches a log record or the audit (C3); failures show authored reasons.
  Named residue: Hide names masks the entry's LABEL; a name spoken in the
  transcript or written in a note is shown as it was kept.
- The confirmations and the save dialogs are injected seams (``confirm``,
  ``choose_csv_path``, ``choose_wav_path``), so a test never opens a real
  dialog (C6).

A KEPT recording (development-recordings plan Phase 3; D7-D10): its row
ends "(recording kept)" (two files' presence and a zero-check, never a
decryption); the opened entry says when its 12-month review falls due, and
the status line counts the ones due (D9). "Delete recording" (two clicks,
like Delete now) deletes the audio ALONE and records the deletion through
the store's ``on_destroyed`` hook (D8). "Export recording" writes ONE
unencrypted ``<session id>.wav`` through the store's export custody, to a
folder ``exclusions.check_export_location`` admits — synced, network,
roaming, removable or unknown drives and either app data folder are
REFUSED, never asked; with no ``WindowsLayer`` Export is refused (fail
closed); a shadow recording asks first (D7); the audit's export count rises
only after the file is in place. Both are DELIBERATE writers: each records
its own event, making a row if none exists (review round 15 PR-MED-003).

Back up... (past-sessions-backup plan Flow 1; D4-D7, D10, D11): the run
gate's admission, the passphrase dialog (twice), the save dialog (only its
FOLDER is used), the location rule (refused, or the same-disk warning asked),
then ``begin_archive_run`` takes the gate — the window's pages, rail and
Settings strip disabled — and four hops run: A derives the key on a worker
(written INTO the run object, never carried by a signal), B snapshots the
archive and the audit record here on the GUI thread, C copies, proves,
writes and verifies the file on a worker, and D records the last-backup date
(``config\\backup.json``) and shows the success line. ``ArchiveRun.close``
zeroes the passphrase and the key and releases the gate on EVERY exit. The
dialogs and the worker are seams (``ask_passphrase``, ``choose_backup_path``,
``run_hop``), so a test opens no real dialog and starts no thread.

Open a backup... (Flows 2 and 3; D7, D8, D10, D11): the admission, the open
dialog, the SOURCE rule (a refused file is never read), the header pre-check,
the passphrase once, then the gate; hop A derives the key and verifies the
whole file on a worker; the restore plan is computed here (one archive
listing); the summary dialog offers Close (nothing written) or Restore — which
verifies the whole file again on a worker, then restores here, advances the
last-backup date, re-lists the page and shows the report. Restore is disabled
while the audit key or the retention setting cannot be read. The open dialog
and the summary are seams too (``choose_backup_file``, ``show_backup_summary``).

Set aside sessions that cannot be opened... (D8, D10): shown only while the
list holds a session whose label cannot be read; one confirmation, the run
gate's admission, then ``PastSessionStore.set_aside_refused`` as ONE call that
never yields (it takes no gate), the page re-listed and the sweep's undated
count lowered by the number moved.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime, tzinfo
from functools import partial
from pathlib import Path
from typing import Protocol

from PySide6.QtCore import QStandardPaths, Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop.audit import AuditRow
from scribe_desktop.exclusions import (
    WindowsLayer,
    check_archive_backup_location,
    check_backup_source,
    check_export_location,
    proposed_backup_folder,
)
from scribe_desktop.logging_setup import log_event
from scribe_desktop.note_config import (
    BackupSettings,
    NoteConfigError,
    read_backup_settings,
    save_backup_settings,
)
from scribe_desktop.past_sessions import (
    PastSessionEntry,
    PastSessionError,
    PastSessionListing,
    PastSessionSettings,
    PastSessionSettingsError,
    PastSessionStore,
    RetentionSweepReport,
    read_past_session_settings,
    save_past_session_settings,
)
from scribe_desktop.past_sessions_backup import (
    BackupFacts,
    BackupPlan,
    BackupReader,
    BackupReport,
    KdfParams,
    RestorePlan,
    derive_key,
    new_kdf_params,
    plan_restore,
    prepare_backup,
    read_backup_header,
    restore_backup,
    reverify_backup,
    verify_backup,
    write_backup_file,
    zero,
)
from scribe_desktop.session_store import default_sessions_root
from scribe_desktop.ui import backup_dialog, models
from scribe_desktop.ui import past_sessions_view as view
from scribe_desktop.ui.lists import NoCopyComboBox, NoCopyListWidget
from scribe_desktop.ui.note import _place_note_text
from scribe_desktop.ui.tasks import TaskThread
from scribe_desktop.ui.theme import set_variant

# How often the tab re-checks what changes without a click: the Delete now
# arming's expiry and the audit's in-memory failure count (no disk, no key).
_TICK_MS = 1000

# ``confirm(text, action)``: the question and the name of the button that
# goes ahead (the other one keeps things as they are). True to go ahead.
Confirm = Callable[[str, str], bool]
ChooseCsvPath = Callable[[], Path | None]
# Development-recordings Task 3.3: the recording export's save dialog, given
# the session id (the proposed file name); only the chosen FOLDER is used.
ChooseWavPath = Callable[[str], Path | None]
# Past-sessions-backup plan Task 2.3: the passphrase dialog (``True``: Back up,
# entered twice) — the passphrase as a ``bytearray``, or None when cancelled;
# and the backup's save dialog, given the folder to start in (None: the
# system drive's root) and the proposed file name — only the chosen FOLDER is
# used.
AskPassphrase = Callable[[bool], bytearray | None]
ChooseBackupPath = Callable[[Path | None, str], Path | None]
# Task 3.3: Open a backup's open dialog, given the folder to start in (None:
# the system drive's root); and the summary dialog, given its lines and
# whether Restore is enabled — True only when Restore was pressed.
ChooseBackupFile = Callable[[Path | None], Path | None]
ShowBackupSummary = Callable[[Sequence[str], bool], bool]
# ``run_hop(work, done)``: run ``work`` off the GUI thread and call ``done``
# with its result on the GUI thread — exactly once, whatever happens (a
# worker that ends with neither result is ``unexpected``, D4).
HopDone = Callable[[object], None]
RunHop = Callable[[Callable[[], object], HopDone], None]


class ArchiveRun:
    """ONE backup or restore run's secrets and gate (past-sessions-backup plan
    D4), on the GUI thread. Created when the passphrase dialog is accepted;
    it holds the passphrase and — once hop A has derived it — the backup key
    ``K_b`` as ``bytearray``s, and, once ``MainWindow.begin_archive_run`` has
    admitted it, the run gate (D11). ``close`` is idempotent and is called on
    EVERY exit: it zeroes both buffers and releases the gate (the window then
    re-enables itself and refreshes what the gate held back). Hop A's worker
    writes the key IN through ``accept_key``; no signal ever carries a key,
    a passphrase or anything derived from them. Residue (D4): ``bytes()``
    and ``AESGCM`` make immutable copies that cannot be zeroed — "zeroed"
    means these ``bytearray``s."""

    def __init__(self, passphrase: bytearray) -> None:
        self._passphrase: bytearray | None = passphrase
        self._key: bytearray | None = None
        self._kdf: KdfParams | None = None
        self._release: Callable[[ArchiveRun], None] | None = None
        self._closed = False
        # Open a backup (D4): the opened, verified file — key-free.
        self._reader: BackupReader | None = None

    @property
    def reader(self) -> BackupReader | None:
        return self._reader

    def attach_reader(self, reader: BackupReader) -> None:
        """Hop A of Open verified the file: the run owns its reader until it
        closes (a closed run keeps nothing)."""
        if not self._closed:
            self._reader = reader

    @property
    def passphrase(self) -> bytearray | None:
        return self._passphrase

    @property
    def backup_key(self) -> bytearray | None:
        return self._key

    @property
    def backup_kdf(self) -> KdfParams | None:
        return self._kdf

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def holds_gate(self) -> bool:
        return self._release is not None

    def accept_key(self, key: bytearray, kdf: KdfParams) -> None:
        """Hop A's worker hands the derived key in (a closed run zeroes it at
        once and keeps nothing)."""
        if self._closed:
            zero(key)
            return
        zero(self._key)
        self._key = key
        self._kdf = kdf

    def drop_passphrase(self) -> None:
        """Zeroed as soon as hop A returns: nothing after it needs it."""
        zero(self._passphrase)
        self._passphrase = None

    def hold_gate(self, release: Callable[[ArchiveRun], None]) -> None:
        """``MainWindow.begin_archive_run`` admitted this run: ``release`` is
        called once, by ``close``."""
        self._release = release

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.drop_passphrase()
        zero(self._key)
        self._key = None
        self._reader = None
        release, self._release = self._release, None
        if release is not None:
            release(self)


class ArchiveGate(Protocol):
    """The main window's run gate as the page uses it (D11)."""

    def archive_run_refusal(self) -> str | None: ...

    def begin_archive_run(self, run: ArchiveRun) -> str | None: ...


def _derive_backup_key(run: ArchiveRun) -> object:
    """Hop A's worker body for Back up: a fresh salt and D3's parameters, the
    key derived from the run's passphrase and written INTO the run. Returns
    nothing derived — True, or the closed failure (D4: every worker body
    catches ``Exception``)."""
    try:
        passphrase = run.passphrase
        if passphrase is None:
            return view.HopFailed("unexpected")
        kdf = new_kdf_params()
        run.accept_key(derive_key(passphrase, kdf), kdf)
    except Exception as exc:  # noqa: BLE001 - a closed code, never exception text (C3)
        return view.hop_failure(exc)
    return True


def _as_failure(result: object) -> view.HopFailed:
    """A hop's result that is not its success: the worker's own closed
    failure, else ``unexpected``."""
    return result if isinstance(result, view.HopFailed) else view.HopFailed("unexpected")


def _write_backup(
    plan: BackupPlan, run: ArchiveRun, folder: Path, admit: Callable[[Path], bool]
) -> object:
    """Hop C's worker body: the proved copy, the write, the read-back and the
    publish (``write_backup_file``). Returns the key-free report, or the
    closed failure."""
    try:
        key = run.backup_key
        if key is None:
            return view.HopFailed("unexpected")
        return write_backup_file(plan, key, folder, check_location=admit)
    except Exception as exc:  # noqa: BLE001 - a closed code, never exception text (C3)
        return view.hop_failure(exc)


def _open_backup(run: ArchiveRun, path: Path, kdf: KdfParams) -> object:
    """Hop A's worker body for Open a backup (Flow 2): the key derived from
    the run's passphrase with the header's parameters and written INTO the
    run, then the whole file verified with it (D2's reader, the open check
    included). Returns the key-free facts, or the closed failure (D4)."""
    try:
        passphrase = run.passphrase
        if passphrase is None:
            return view.HopFailed("unexpected")
        run.accept_key(derive_key(passphrase, kdf), kdf)
        key = run.backup_key
        if key is None:
            return view.HopFailed("unexpected")
        return verify_backup(path, key)
    except Exception as exc:  # noqa: BLE001 - a closed code, never exception text (C3)
        return view.hop_failure(exc)


def _reverify_backup(run: ArchiveRun, path: Path, expected_sha256: str) -> object:
    """Restore's first hop, on a worker (Flow 3): the whole file verified
    again with the held key and its SHA-256 equal to Open's. True, or the
    closed failure (``source_changed``)."""
    try:
        key = run.backup_key
        if key is None:
            return view.HopFailed("unexpected")
        reverify_backup(path, key, expected_sha256)
    except Exception as exc:  # noqa: BLE001 - a closed code, never exception text (C3)
        return view.hop_failure(exc)
    return True


def _record_deletion(
    audit: view.PastSessionsAudit,
    session_id: str,
    created_at: float | None,
    *,
    kept_recorded: bool,
) -> bool:
    """Delete recording's ``on_destroyed``: the deletion recorded, and True
    only when the kept fact was recorded too (review round 21 LOW-002)."""
    deleted = audit.record_recording_deleted(session_id, created_at=created_at)
    return kept_recorded and deleted


def _destination_check(layer: WindowsLayer) -> Callable[[Path], str | None]:
    """Export's location check as the store takes it (codex round 23
    PR-HIGH-001): the refusal's line, or None for a folder it admits."""

    def check(folder: Path) -> str | None:
        refusal = check_export_location(layer, folder)
        return None if refusal is None else refusal.line

    return check


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _display_panel() -> QPlainTextEdit:
    """A read-only, display-only text panel (no selection, so no native copy)."""
    panel = QPlainTextEdit()
    panel.setReadOnly(True)
    panel.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    return panel


def _plain_label(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    return label


class PastSessionsScreen(QWidget):
    """The tab. ``store`` None (a window built without the archive) shows the
    not-set-up line and touches no disk. ``audit`` is the
    ``past_sessions_view.PastSessionsAudit`` surface — ``AuditLog`` in the
    app; None records nothing and disables the export."""

    def __init__(
        self,
        store: PastSessionStore | None,
        *,
        audit: view.PastSessionsAudit | None = None,
        config_root: Path | None = None,
        clock: Callable[[], datetime] = _utc_now,
        monotonic: Callable[[], float] = time.monotonic,
        local_zone: tzinfo | None = None,
        confirm: Confirm | None = None,
        choose_csv_path: ChooseCsvPath | None = None,
        exclusion_warnings: Sequence[str] = (),
        choose_wav_path: ChooseWavPath | None = None,
        windows_layer: WindowsLayer | None = None,
        export_recovery_lines: Sequence[str] = (),
        ask_passphrase: AskPassphrase | None = None,
        choose_backup_path: ChooseBackupPath | None = None,
        run_hop: RunHop | None = None,
        logger: logging.Logger | None = None,
        choose_backup_file: ChooseBackupFile | None = None,
        show_backup_summary: ShowBackupSummary | None = None,
        sessions_root: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        # Task 3.3: Open a backup's open dialog and summary (seams; None: the
        # real ones), and the sessions folder Restore's planner checks for a
        # live recording (None: the default one).
        self._choose_backup_file: ChooseBackupFile = (
            choose_backup_file if choose_backup_file is not None else self._ask_backup_file
        )
        self._show_backup_summary: ShowBackupSummary = (
            show_backup_summary if show_backup_summary is not None else self._show_real_summary
        )
        self._sessions_root = (
            sessions_root if sessions_root is not None else default_sessions_root()
        )
        # The line an unforeseen failure of the current run ends with (Back up
        # or Open a backup).
        self._run_failed_line: Callable[[view.HopFailed], str] = view.backup_failed_line
        # Peer round 29 PR-LOW-202 (D4, C3): an unforeseen backup failure's
        # TYPE name, logged once through ``log_event`` (None: not logged).
        self._logger = logger
        # Past-sessions-backup plan Task 2.3: the two dialogs and the worker
        # are seams (None: the real ones), and the main window's run gate is
        # set after the window is built (``set_archive_gate``; None refuses
        # every run — fail closed).
        self._ask_passphrase: AskPassphrase = (
            ask_passphrase if ask_passphrase is not None else self._ask_real_passphrase
        )
        self._choose_backup_path: ChooseBackupPath = (
            choose_backup_path if choose_backup_path is not None else self._ask_backup_path
        )
        self._run_hop: RunHop = run_hop if run_hop is not None else self._run_task
        self._archive_gate: ArchiveGate | None = None
        self._run: ArchiveRun | None = None
        self._hops: list[TaskThread] = []
        self._pending_hops: dict[TaskThread, HopDone] = {}
        # D10: the last backup's ``made_at`` from ``config\backup.json``, re-read
        # when the page is opened and after a backup (None: none recorded).
        self._last_backup_at: datetime | None = None
        # Task 4.1 (Flow 6): the start-up exclusion warnings — fixed for the
        # run (computed before the window was built), so the derived status
        # line always carries them.
        self._exclusion_warnings = tuple(exclusion_warnings)
        # Development-recordings Task 3.3: the start-up lines of
        # ``PastSessionStore.recover_exports`` (fixed for the run), and the
        # layer the export location check reads — None refuses every export.
        self._export_recovery_lines = tuple(export_recovery_lines)
        self._windows_layer = windows_layer
        self._choose_wav_path: ChooseWavPath = (
            choose_wav_path if choose_wav_path is not None else self._ask_wav_path
        )
        self._recording_delete_armed: tuple[str, float] | None = None
        self._audit = audit
        self._config_root = config_root
        self._clock = clock
        self._monotonic = monotonic
        # The zone dates are shown in: None is this computer's own.
        self._zone = local_zone
        self._confirm: Confirm = confirm if confirm is not None else self._ask
        self._choose_csv_path: ChooseCsvPath = (
            choose_csv_path if choose_csv_path is not None else self._ask_csv_path
        )
        self._listings: list[PastSessionListing] = []
        # Whether the list holds a listing at all (False until the tab is
        # first opened, and again once it is left): no placeholder before.
        self._listed = False
        self._open_id: str | None = None
        self._open_entry: PastSessionEntry | None = None
        self._delete_armed: tuple[str, float] | None = None
        self._audit_key_unreadable = False
        self._shown_failures = 0
        self._shown_review: tuple[int, bool] = (0, False)
        self._shown_backup: str | None = None
        # The latest retention sweep's report and the retention it ran under
        # (round 16 MED-002, round 17 LOW-020): its status lines are DERIVED
        # from it while that setting is still current (``_current_sweep``,
        # round 18 PR-LOW-014), never kept as flags a later change contradicts.
        self._last_sweep: tuple[int | None, RetentionSweepReport] | None = None
        self._settings_unreadable = False
        # The file holds a shorter window an earlier version offered, read as
        # 7 years (practitioner decision 2026-10-02) — until a save rewrites it.
        self._retention_raised = False
        # Round 16 MED-001: a Hide names choice the file did not take, kept
        # for the rest of the run over whatever a later reload reads.
        self._hide_override: bool | None = None
        self._settings = PastSessionSettings()
        self._load_settings()

        self.intended_use_label = _plain_label(models.INTENDED_USE_LINE)
        self.status_label = _plain_label()
        self.reset_audit_button = QPushButton(view.AUDIT_RESET_LABEL)
        self.reset_audit_button.clicked.connect(self.on_reset_audit)
        self.message_label = _plain_label()

        # Left: the list, Delete now, the settings and the export.
        self.entry_list = NoCopyListWidget()
        self.entry_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.delete_button = QPushButton(view.DELETE_LABEL)
        set_variant(self.delete_button, "danger")  # UI refresh plan Task 2.4
        self.delete_button.clicked.connect(self.on_delete_clicked)
        self.delete_help_label = _plain_label(view.DELETE_HELP)
        list_box = QGroupBox(view.LIST_GROUP_TITLE)
        list_layout = QVBoxLayout()
        list_layout.addWidget(self.entry_list, 1)
        list_layout.addWidget(self.delete_button)
        list_layout.addWidget(self.delete_help_label)
        list_box.setLayout(list_layout)

        self.retention_combo = NoCopyComboBox()
        for label, _days in view.RETENTION_OPTIONS:
            self.retention_combo.addItem(label)
        self.retention_combo.activated.connect(self.on_retention_chosen)
        self.retention_warning_label = _plain_label(view.RETENTION_WARNING)
        self.hide_names_checkbox = QCheckBox(view.HIDE_NAMES_LABEL)
        self.hide_names_checkbox.clicked.connect(self.on_hide_names)
        settings_box = QGroupBox(view.SETTINGS_GROUP_TITLE)
        settings_layout = QVBoxLayout()
        settings_layout.addWidget(_plain_label(view.RETENTION_HEADING))
        settings_layout.addWidget(self.retention_combo)
        settings_layout.addWidget(self.retention_warning_label)
        settings_layout.addWidget(self.hide_names_checkbox)
        settings_box.setLayout(settings_layout)

        self.export_button = QPushButton(view.EXPORT_LABEL)
        self.export_button.clicked.connect(self.on_export)
        self.csv_line_label = _plain_label(view.CSV_NOT_ENCRYPTED_LINE)
        export_box = QGroupBox(view.EXPORT_GROUP_TITLE)
        export_layout = QVBoxLayout()
        export_layout.addWidget(self.export_button)
        export_layout.addWidget(self.csv_line_label)
        export_box.setLayout(export_layout)

        # Past-sessions-backup plan D10: Back up... and Open a backup... under
        # the export, one above the other (side by side they overflow the
        # narrowest window); the set-aside below them, shown only while the
        # list holds a session that cannot be read.
        self.backup_button = QPushButton(view.BACKUP_LABEL)
        self.backup_button.clicked.connect(self.on_backup)
        self.open_backup_button = QPushButton(view.OPEN_BACKUP_LABEL)
        self.open_backup_button.clicked.connect(self.on_open_backup)
        self.backup_help_label = _plain_label(view.BACKUP_HELP)
        self.set_aside_button = QPushButton(view.SET_ASIDE_LABEL)
        self.set_aside_button.clicked.connect(self.on_set_aside)
        self.set_aside_button.setVisible(False)
        self.backup_box = QGroupBox(view.BACKUP_GROUP_TITLE)
        backup_layout = QVBoxLayout()
        backup_layout.addWidget(self.backup_button)
        backup_layout.addWidget(self.open_backup_button)
        backup_layout.addWidget(self.backup_help_label)
        backup_layout.addWidget(self.set_aside_button)
        self.backup_box.setLayout(backup_layout)

        left = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(list_box, 1)
        left_layout.addWidget(settings_box)
        left_layout.addWidget(export_box)
        left_layout.addWidget(self.backup_box)
        left.setLayout(left_layout)

        # Right: the opened entry.
        self.heading_label = _plain_label()
        self.write_line_label = _plain_label()
        self.generated_view = _display_panel()
        self.saved_view = _display_panel()
        self.transcript_view = _display_panel()
        self.transcript_view.setVisible(False)
        self.copy_button = QPushButton(view.COPY_LABEL)
        self.copy_button.clicked.connect(self.on_copy)
        self.transcript_button = QPushButton(view.SHOW_TRANSCRIPT_LABEL)
        self.transcript_button.clicked.connect(self.on_toggle_transcript)
        # The reason Copy is unavailable, as a persistent line under the
        # buttons (the Note tab's Write-button pattern).
        self.copy_reason_label = _plain_label()

        # Development-recordings Phase 3: the selected entry's kept recording
        # — shown only while the selected entry holds one (its label may be
        # unreadable: the recording can still be deleted).
        self.recording_line_label = _plain_label()
        self.delete_recording_button = QPushButton(view.DELETE_RECORDING_LABEL)
        set_variant(self.delete_recording_button, "danger")
        self.delete_recording_button.clicked.connect(self.on_delete_recording_clicked)
        self.export_recording_button = QPushButton(view.EXPORT_RECORDING_LABEL)
        self.export_recording_button.clicked.connect(self.on_export_recording)
        recording_buttons = QHBoxLayout()
        recording_buttons.addWidget(self.delete_recording_button)
        recording_buttons.addWidget(self.export_recording_button)
        recording_buttons.addStretch(1)
        self.recording_box = QGroupBox(view.RECORDING_GROUP_TITLE)
        recording_layout = QVBoxLayout()
        recording_layout.addWidget(self.recording_line_label)
        recording_layout.addLayout(recording_buttons)
        recording_layout.addWidget(_plain_label(view.DELETE_RECORDING_HELP))
        recording_layout.addWidget(_plain_label(view.EXPORT_RECORDING_HELP))
        self.recording_box.setLayout(recording_layout)
        self.recording_box.setVisible(False)

        notes = QSplitter(Qt.Orientation.Horizontal)
        for heading, panel in (
            (view.GENERATED_HEADING, self.generated_view),
            (view.SAVED_HEADING, self.saved_view),
        ):
            column = QWidget()
            column_layout = QVBoxLayout()
            column_layout.setContentsMargins(0, 0, 0, 0)
            column_layout.addWidget(_plain_label(heading))
            column_layout.addWidget(panel)
            column.setLayout(column_layout)
            notes.addWidget(column)
        buttons = QHBoxLayout()
        buttons.addWidget(self.copy_button)
        buttons.addWidget(self.transcript_button)
        buttons.addStretch(1)

        right = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.heading_label)
        right_layout.addWidget(self.write_line_label)
        right_layout.addWidget(self.recording_box)
        right_layout.addWidget(notes, 2)
        right_layout.addLayout(buttons)
        right_layout.addWidget(self.copy_reason_label)
        right_layout.addWidget(_plain_label(view.TRANSCRIPT_HEADING))
        right_layout.addWidget(self.transcript_view, 1)
        right.setLayout(right_layout)

        body = QSplitter(Qt.Orientation.Horizontal)
        body.addWidget(left)
        body.addWidget(right)
        body.setStretchFactor(1, 2)

        layout = QVBoxLayout()
        layout.addWidget(self.intended_use_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.reset_audit_button)
        layout.addWidget(body, 1)
        layout.addWidget(self.message_label)
        self.setLayout(layout)

        self._render_settings()
        self.close_entry()
        self._render_list()
        self._render_status()

        self._timer = QTimer(self)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # --- listing --------------------------------------------------------------

    def refresh(self) -> None:
        """On every opening of the tab: re-read the settings file (round 16
        MED-001), re-list the archive (each label decrypted once) and
        re-check the audit key. Drops any opened entry and any stale line."""
        self.close_entry()
        self._disarm_delete()
        self._disarm_recording_delete()
        self._show_message("")
        self._reload_settings()
        self._load_last_backup()
        listed = True
        if self._store is not None:
            try:
                self._listings = view.sorted_listings(self._store.list_entries())
            except Exception:  # noqa: BLE001 - authored line, never OS text (C3)
                # Round 16 LOW-003: an archive that cannot be listed is never
                # shown as "none kept".
                self._listings = []
                listed = False
                self._show_message(view.LIST_UNREADABLE)
        self._listed = listed
        self._render_list()
        self._recheck_audit_key()

    def on_left(self) -> None:
        """The tab was left (round 16 LOW-008): the opened entry's text and
        every listed name leave the widgets and memory; opening the tab
        again re-lists."""
        self.close_entry()
        self._disarm_delete()
        self._disarm_recording_delete()
        self._listings = []
        self._listed = False
        self._render_list()
        self._render_status()  # the review-due count follows the listings

    def _check_audit_key(self) -> bool:
        if self._audit is None:
            return False
        try:
            return self._audit.key_unreadable()
        except Exception:  # noqa: BLE001 - a passing problem offers no reset
            return False

    def _render_list(self) -> None:
        hide = self._settings.hide_names
        selected = self._open_id
        self.entry_list.blockSignals(True)
        try:
            self.entry_list.clear()
            for listing in self._listings:
                item = QListWidgetItem(
                    view.entry_line(listing, hide_names=hide, zone=self._zone)
                )
                item.setData(Qt.ItemDataRole.UserRole, listing.session_id)
                self.entry_list.addItem(item)
                if listing.session_id == selected:
                    item.setSelected(True)
            if not self._listings and (self._listed or self._store is None):
                empty = QListWidgetItem(
                    view.STORE_UNAVAILABLE if self._store is None else view.NO_ENTRIES
                )
                empty.setFlags(Qt.ItemFlag.NoItemFlags)
                self.entry_list.addItem(empty)
        finally:
            self.entry_list.blockSignals(False)
        self._render_controls()

    def _selected_id(self) -> str | None:
        items = self.entry_list.selectedItems()
        if not items:
            return None
        value = items[0].data(Qt.ItemDataRole.UserRole)
        return value if isinstance(value, str) else None

    def _listing(self, session_id: str) -> PastSessionListing | None:
        for listing in self._listings:
            if listing.session_id == session_id:
                return listing
        return None

    def _selected_listing(self) -> PastSessionListing | None:
        session_id = self._selected_id()
        return self._listing(session_id) if session_id is not None else None

    def _on_selection_changed(self) -> None:
        self._disarm_delete()
        self._disarm_recording_delete()
        session_id = self._selected_id()
        if session_id is None:
            self.close_entry()
            return
        self.open_entry(session_id)

    # --- the opened entry -----------------------------------------------------

    def open_entry(self, session_id: str) -> None:
        """Decrypt one entry (its label, transcript and notes) and its audit
        row, and show them. An entry that cannot be opened says why (its
        authored reason) and can still be deleted."""
        self.close_entry()
        self._open_id = session_id
        listing = self._listing(session_id)
        if listing is None or listing.label is None or self._store is None:
            self.heading_label.setText(view.ENTRY_UNREADABLE)
            self._render_controls()
            return
        try:
            entry = self._store.read_entry(session_id)
        except Exception as exc:  # noqa: BLE001 - the view maps it to an authored line (C3)
            self.heading_label.setText(view.open_failed_line(exc))
            self._render_controls()
            return
        self._open_entry = entry
        self._render_entry()
        self.write_line_label.setText(self._write_line(session_id))
        self._render_controls()

    def _write_line(self, session_id: str) -> str:
        if self._audit is None:
            return view.write_outcome_line(None)
        row: AuditRow | None
        try:
            row = self._audit.row_for(session_id)
        except Exception:  # noqa: BLE001 - AuditUnavailable or a disk problem
            self._recheck_audit_key()
            return view.write_outcome_line(None, unavailable=True)
        return view.write_outcome_line(row, zone=self._zone)

    def _recheck_audit_key(self) -> None:
        """Round 17 LOW-021: an audit read that failed may mean the key went
        unreadable since the tab was opened — re-check it, so D9's "Start a
        new audit record" appears at once (and Export follows)."""
        self._audit_key_unreadable = self._check_audit_key()
        self._render_status()

    def _render_entry(self) -> None:
        entry = self._open_entry
        if entry is None:
            return
        hide = self._settings.hide_names
        listed = self._listing(entry.label.session_id)
        listing = PastSessionListing(
            entry.label.session_id,
            entry.label,
            recording_kept=listed is not None and listed.recording_kept,
        )
        self.heading_label.setText(view.entry_line(listing, hide_names=hide, zone=self._zone))
        self.generated_view.setPlainText(
            entry.generated.generated_text
            if entry.generated is not None
            else view.GENERATED_NOT_KEPT
        )
        self.saved_view.setPlainText(
            models.format_note_body(entry.saved_note)
            if entry.saved_note is not None
            else view.NO_SAVED_NOTE
        )
        if self.transcript_view.isVisibleTo(self):
            self.transcript_view.setPlainText(models.format_transcript_text(entry.transcript))

    def close_entry(self) -> None:
        """Drop the opened entry's text from every panel (called when the tab
        is left, re-listed, or the entry deleted)."""
        self._open_id = None
        self._open_entry = None
        self.heading_label.setText("")
        self.write_line_label.setText("")
        self.generated_view.setPlainText("")
        self.saved_view.setPlainText("")
        self.transcript_view.setPlainText("")
        self.transcript_view.setVisible(False)
        self.transcript_button.setText(view.SHOW_TRANSCRIPT_LABEL)
        self._render_controls()

    def on_toggle_transcript(self) -> None:
        entry = self._open_entry
        if entry is None:
            return
        if self.transcript_view.isVisibleTo(self):
            self.transcript_view.setPlainText("")
            self.transcript_view.setVisible(False)
            self.transcript_button.setText(view.SHOW_TRANSCRIPT_LABEL)
            return
        self.transcript_view.setPlainText(models.format_transcript_text(entry.transcript))
        self.transcript_view.setVisible(True)
        self.transcript_button.setText(view.HIDE_TRANSCRIPT_LABEL)

    def _copy_reason(self) -> str | None:
        """Why the kept saved note cannot be copied, or None when it can: the
        recorded copy flag is on and the note carries no unresolved error (a
        saved note met the full ratification bar when it was saved —
        ``ui/note.py`` ``_copy_ready``'s reopened-note rule, re-checked here
        all the same). Pilot plan Task 1.6: a shadow recording's entry is
        refused by name."""
        entry = self._open_entry
        saved = entry.saved_note if entry is not None else None
        return view.copy_unavailable_reason(
            opened=entry is not None,
            has_saved=saved is not None,
            unresolved=saved is not None and bool(saved.blocking_warnings()),
            copy_enabled=models.COPY_TO_CLINIKO_ENABLED,
            shadow=entry is not None and entry.label.shadow,
        )

    def on_copy(self) -> None:
        """Copy the SAVED note only, through the one placement (Task 8.2's
        formats). Re-checked at click time (fail closed); the placement
        itself refuses a shadow recording's note too (pilot plan D5)."""
        entry = self._open_entry
        reason = self._copy_reason()
        if reason is not None or entry is None or entry.saved_note is None:
            self._show_message(reason or view.COPY_NOTHING_OPEN)
            return
        # Invented-text guard decision 0.5: a copy carries no check mark.
        if _place_note_text(
            models.format_note_body(entry.saved_note, check_marks=False),
            shadow=entry.label.shadow,
        ):
            self._show_message(view.COPY_DONE)

    # --- Delete now (two clicks) ------------------------------------------

    def on_delete_clicked(self) -> None:
        """The first click asks; a second within ``DELETE_CONFIRM_SECONDS``
        for the same entry deletes it — the entry's key first (D3)."""
        session_id = self._selected_id()
        if session_id is None or self._store is None:
            self._show_message(view.SELECT_FIRST)
            return
        self._disarm_recording_delete()
        armed = self._delete_armed
        if armed is not None and self._delete_confirmable(armed, session_id):
            self._disarm_delete()
            self._delete(session_id)
            return
        self._delete_armed = (session_id, self._monotonic())
        self.delete_button.setText(view.DELETE_CONFIRM_LABEL)
        self._show_message(view.DELETE_CONFIRM_MESSAGE)

    def _delete_confirmable(self, armed: tuple[str, float], session_id: str) -> bool:
        armed_id, at = armed
        return (
            armed_id == session_id
            and 0 <= self._monotonic() - at <= view.DELETE_CONFIRM_SECONDS
        )

    def _disarm_delete(self) -> None:
        """Back to one click; the "Press Confirm delete" line goes with the
        arming (round 16 LOW-004)."""
        self._delete_armed = None
        self.delete_button.setText(view.DELETE_LABEL)
        if self.message_label.text() == view.DELETE_CONFIRM_MESSAGE:
            self._show_message("")

    def _delete(self, session_id: str) -> None:
        store = self._store
        if store is None:
            return
        listing = self._listing(session_id)
        # Development-recordings Task 2.2 (review round 8 LOW-003): whether it
        # held a kept recording, read from the files before its key goes.
        # Round 13 LOW-001 / round 15 PR-MED-002: held = kept, or deleted but
        # not yet tidied (``gone``: perhaps held back by tidy because its
        # deletion record failed) — decided from ONE read (round 17 PR-MED-001).
        recording = store.recording_state(session_id)
        held_recording = recording != "none"
        recording_gone = recording == "gone"
        label = listing.label if listing else None
        created_at = view.started_epoch(label)
        if self._audit is not None and held_recording and label is not None:
            # The kept fact first (idempotent), so `deleted_early` can record
            # the recording's deletion even when the Complete's own audit
            # write failed — and BEFORE the entry goes (review round 14
            # PR-MED-003): a true fact whether or not the deletion succeeds,
            # so no interruption between the two loses it.
            self._audit.record_recording_kept(session_id, label.completed_at, created_at=created_at)
        if self._audit is not None and recording_gone:
            # Round 15 PR-MED-002: that deletion is ALREADY a fact, so it is
            # recorded before its evidence goes too. A refused write never
            # holds the Delete now (only `begin` may refuse; C2): the entry
            # goes, as every Delete now does during an audit outage.
            self._audit.record_recording_deleted(session_id, created_at=created_at)
        try:
            store.delete_entry(session_id)
        except Exception as exc:  # noqa: BLE001 - the view maps it to an authored line (C3)
            self._show_message(view.delete_failed_line(exc))
            return
        if self._audit is not None:
            if held_recording and label is None and not recording_gone:
                # Review round 12 LOW-004: no label, so no completion time for
                # the kept fact — the deletion itself is recorded (it needs no
                # `kept_at`, `audit._recording_deleted`). Like `deleted_early`
                # beside it, a deliberate destruction is a NEW event the audit
                # records, so with no row it makes one dated now (D8; review
                # round 15 PR-MED-003, accepted) — unlike the unattended repair
                # (`app.record_deleted_recordings`, `create=False`).
                self._audit.record_recording_deleted(session_id)
            self._audit.record_past_session(session_id, "deleted_early", created_at=created_at)
        self._drop([session_id])
        swept = self._current_sweep()
        if listing is not None and listing.label is None and swept is not None and swept.undated:
            # One of the undated entries the sweep kept is gone (LOW-020).
            self._last_sweep = (
                self._settings.retention_days,
                replace(swept, undated=swept.undated - 1),
            )
            self._render_status()
        self._show_message(view.DELETE_DONE)

    def _drop(self, session_ids: list[str]) -> None:
        """Remove deleted entries from the list IN MEMORY — no re-listing, so
        a sweep decrypts nothing beyond what it needed."""
        gone = set(session_ids)
        if self._open_id in gone:
            self.close_entry()
        if self._delete_armed is not None and self._delete_armed[0] in gone:
            self._disarm_delete()
        armed = self._recording_delete_armed
        if armed is not None and armed[0] in gone:
            self._disarm_recording_delete()
        self._listings = [item for item in self._listings if item.session_id not in gone]
        self._render_list()
        self._render_status()  # a deleted kept recording leaves the due count

    # --- the kept recording (development-recordings plan Tasks 3.2-3.3) -----

    def on_delete_recording_clicked(self) -> None:
        """Delete recording (D8): the first click asks; a second within
        ``DELETE_CONFIRM_SECONDS`` for the same entry deletes the recording
        ALONE — the transcript and notes stay."""
        listing = self._selected_listing()
        if self._store is None or listing is None or not listing.recording_kept:
            self._show_message(view.NO_KEPT_RECORDING)
            return
        self._disarm_delete()
        armed = self._recording_delete_armed
        if armed is not None and self._delete_confirmable(armed, listing.session_id):
            self._disarm_recording_delete()
            self._delete_recording(listing)
            return
        self._recording_delete_armed = (listing.session_id, self._monotonic())
        self.delete_recording_button.setText(view.DELETE_RECORDING_CONFIRM_LABEL)
        self._show_message(view.DELETE_RECORDING_CONFIRM_MESSAGE)

    def _disarm_recording_delete(self) -> None:
        self._recording_delete_armed = None
        self.delete_recording_button.setText(view.DELETE_RECORDING_LABEL)
        if self.message_label.text() == view.DELETE_RECORDING_CONFIRM_MESSAGE:
            self._show_message("")

    def _delete_recording(self, listing: PastSessionListing) -> None:
        """The deletion: the kept fact first (true either way; Task 2.2's
        amendment), then the store zeroes the audio key, and the deletion is
        recorded THROUGH ``on_destroyed`` — after the verified zeros, before
        the unlinks (review round 12 LOW-003): a record that fails leaves the
        zeroed files for the next run's deletion record. A DELIBERATE writer
        (review round 15 PR-MED-003): dated by the session's start, and
        making a row when there is none (dated now with no readable label).
        The deletion counts as recorded only when the kept fact was too
        (review round 21 LOW-002): otherwise the zeroed files stay as the
        evidence the next run's full record (``app.record_deleted_recordings``)
        needs — the rule the unattended path already keeps."""
        store = self._store
        if store is None:
            return
        session_id, label, audit = listing.session_id, listing.label, self._audit
        created_at = view.started_epoch(label)
        on_destroyed: Callable[[], object] | None = None
        if audit is not None:
            kept_recorded = True
            if label is not None:
                kept_recorded = audit.record_recording_kept(
                    session_id, label.completed_at, created_at=created_at
                )
            on_destroyed = partial(
                _record_deletion, audit, session_id, created_at, kept_recorded=kept_recorded
            )
        try:
            store.delete_recording(session_id, on_destroyed=on_destroyed)
        except Exception as exc:  # noqa: BLE001 - the view maps it to an authored line (C3)
            self._show_message(view.recording_delete_failed_line(exc))
            return
        self._listings = [
            replace(item, recording_kept=False) if item.session_id == session_id else item
            for item in self._listings
        ]
        self._render_list()
        self._render_entry()
        self._render_status()
        self._show_message(view.DELETE_RECORDING_DONE)

    def on_export_recording(self) -> None:
        """Export recording (D10, D7, C2): the save dialog, then the location
        check — a destination it positively identifies as off this computer
        or outside custody is REFUSED, never asked — then, for a shadow
        recording (or one whose label cannot be read), the one question
        Export asks; then the store's export custody, which runs the same
        check AGAIN on the resolved folder just before it creates the file
        (codex round 23 PR-HIGH-001). The audit's export count rises only
        once the file is in place."""
        listing = self._selected_listing()
        store = self._store
        if store is None or listing is None or not listing.recording_kept:
            self._show_message(view.NO_KEPT_RECORDING)
            return
        self._disarm_delete()
        self._disarm_recording_delete()
        layer = self._windows_layer
        if layer is None:  # fail closed: an unchecked destination is never written
            self._show_message(view.EXPORT_RECORDING_NO_LAYER)
            return
        session_id, label = listing.session_id, listing.label
        path = self._choose_wav_path(session_id)
        if path is None:
            return
        folder = path.parent
        refusal = check_export_location(layer, folder)
        if refusal is not None:
            self._show_message(view.export_refused_line(refusal.line))
            return
        question = view.export_confirm_question(label)
        if question is not None and not self._confirm(question, view.EXPORT_SHADOW_ACTION):
            self._show_message("")
            return
        try:
            # Codex round 23 PR-HIGH-001: the store checks the RESOLVED folder
            # again, after the question above waited on the user.
            store.export_recording(
                session_id, folder, check_destination=_destination_check(layer)
            )
        except Exception as exc:  # noqa: BLE001 - the view maps it to an authored line (C3)
            self._show_message(view.export_recording_failed_line(exc, session_id))
            return
        if self._audit is not None:
            self._audit.record_recording_exported(
                session_id, created_at=view.started_epoch(label)
            )
        self._show_message(view.recording_exported_line(session_id))

    # --- Back up (past-sessions-backup plan Flow 1; D4-D7, D10, D11) -------

    @property
    def is_busy(self) -> bool:
        """A backup or restore hop's worker is running — "the Past sessions
        page itself" in the run gate's admission (D11)."""
        return bool(self._hops)

    def set_archive_gate(self, gate: ArchiveGate | None) -> None:
        """The main window's run gate (D11), set once the window is built."""
        self._archive_gate = gate

    def on_backup(self) -> None:
        """Back up... (Flow 1): the admission check, the passphrase twice, the
        save dialog (its FOLDER only), the location rule — refused, or the
        same-disk warning asked — then the gate taken and hop A started.
        Every exit before the gate closes the run object at once."""
        store, audit, gate = self._store, self._audit, self._archive_gate
        if store is None or audit is None or gate is None or self._run is not None:
            self._show_message(view.BACKUP_NOT_AVAILABLE)
            return
        self._disarm_delete()
        self._disarm_recording_delete()
        refusal = gate.archive_run_refusal()
        if refusal is not None:
            self._show_message(refusal)
            return
        layer = self._windows_layer
        if layer is None:  # fail closed: an unchecked destination is never written
            self._show_message(view.BACKUP_NO_LAYER)
            return
        passphrase = self._ask_passphrase(True)
        if passphrase is None:
            return
        run = ArchiveRun(passphrase)
        self._run = run
        self._run_failed_line = view.backup_failed_line
        try:
            self._backup_from_dialogs(run, layer, gate)
        except BaseException:
            # Review round 27 LOW-001 (D4): an unforeseen raise still closes
            # the run — both buffers zeroed, the gate released — and the
            # exception hook still logs its type name.
            self._fail_run(run)
            raise

    def _backup_from_dialogs(self, run: ArchiveRun, layer: WindowsLayer, gate: ArchiveGate) -> None:
        """``on_backup`` once the run object exists: the save dialog, the
        location rule, the gate, hop A."""
        self._render_controls()
        remembered = read_backup_settings(self._config_root).settings.folder
        start = proposed_backup_folder(layer, remembered)
        path = self._choose_backup_path(start, view.backup_default_name(self._clock(), self._zone))
        if path is None:
            self._end_run("")
            return
        folder = path.parent
        location = check_archive_backup_location(layer, folder)
        if location.outcome == "refused":
            self._end_run(view.backup_refused_line(location.line or ""))
            return
        if location.outcome == "warned" and not self._confirm(
            view.backup_same_disk_question(location.line or ""), view.BACKUP_SAME_DISK_ACTION
        ):
            self._end_run("")
            return
        # The admission again and the gate taken in ONE call, after the last
        # dialog and before the first worker (D11).
        refusal = gate.begin_archive_run(run)
        if refusal is not None:
            self._end_run(refusal)
            return
        accepted = location.outcome
        self._show_message(view.BACKUP_RUNNING)
        self._start_hop(
            run,
            partial(_derive_backup_key, run),
            partial(self._backup_key_ready, run, layer, folder, accepted),
        )

    def _backup_key_ready(
        self, run: ArchiveRun, layer: WindowsLayer, folder: Path, accepted: str, result: object
    ) -> None:
        """Hop A returned: the passphrase is zeroed at once. Then hop B here on
        the GUI thread — the archive's and the audit record's snapshot, each
        key wrapped under ``K_b`` (``prepare_backup``) — and hop C started on a
        worker, whose destination check admits only the location outcome the
        practitioner accepted (a folder that changed is refused)."""
        run.drop_passphrase()
        store, audit = self._store, self._audit
        if run is not self._run or store is None or audit is None:
            run.close()
            return
        if result is not True:
            self._end_run(view.backup_failed_line(self._noted("derive", _as_failure(result))))
            return
        try:
            plan = prepare_backup(store, audit, run, made_at=self._clock())
        except Exception as exc:  # noqa: BLE001 - a closed code, never exception text (C3)
            self._end_run(view.backup_failed_line(self._noted("snapshot", view.hop_failure(exc))))
            return

        def admit(candidate: Path) -> bool:
            return check_archive_backup_location(layer, candidate).outcome == accepted

        self._start_hop(
            run,
            partial(_write_backup, plan, run, folder, admit),
            partial(self._backup_written, run, folder),
        )

    def _backup_written(self, run: ArchiveRun, folder: Path, result: object) -> None:
        """Hop D: the published, verified file's report — the last-backup date
        and the folder saved (a failure to save adds D6's sentence and changes
        nothing else), the success line, the status line — or the failure's
        line. Nothing is recorded for a file that was not verified."""
        if run is not self._run:
            run.close()
            return
        if not isinstance(result, BackupReport):
            self._end_run(view.backup_failed_line(self._noted("write", _as_failure(result))))
            return
        saved = True
        try:
            save_backup_settings(
                BackupSettings(folder=str(folder), last_backup_at=result.made_at),
                config_root=self._config_root,
            )
        except (NoteConfigError, ValueError):
            saved = False
        else:
            self._last_backup_at = result.made_at
        self._end_run(view.backup_success_line(result, date_saved=saved))
        self._render_status()

    # --- Open a backup and Restore (Flows 2 and 3; D7, D8, D10, D11) --------

    def on_open_backup(self) -> None:
        """Open a backup... (Flow 2): the admission check, the open dialog,
        the SOURCE rule (a refused file receives no read), the header
        pre-check (its bounds, format and channel), the passphrase once, then
        the gate taken and hop A started. Every exit after the passphrase
        closes the run object."""
        store, audit, gate = self._store, self._audit, self._archive_gate
        if store is None or audit is None or gate is None or self._run is not None:
            self._show_message(view.OPEN_NOT_AVAILABLE)
            return
        self._disarm_delete()
        self._disarm_recording_delete()
        refusal = gate.archive_run_refusal()
        if refusal is not None:
            self._show_message(refusal)
            return
        layer = self._windows_layer
        if layer is None:  # fail closed: an unchecked source is never read
            self._show_message(view.OPEN_NO_LAYER)
            return
        remembered = read_backup_settings(self._config_root).settings.folder
        path = self._choose_backup_file(proposed_backup_folder(layer, remembered))
        if path is None:
            return
        refused = check_backup_source(layer, path)
        if refused is not None:
            self._show_message(view.open_refused_line(refused.line))
            return
        try:
            header = read_backup_header(path)
        except Exception as exc:  # noqa: BLE001 - a closed code, never exception text (C3)
            failure = self._noted("header", view.hop_failure(exc))
            self._show_message(view.backup_open_failed_line(failure))
            return
        passphrase = self._ask_passphrase(False)
        if passphrase is None:
            return
        run = ArchiveRun(passphrase)
        self._run = run
        self._run_failed_line = view.backup_open_failed_line
        try:
            self._open_from_dialogs(run, path, header.kdf, gate)
        except BaseException:
            # D4 (review round 27 LOW-001's rule): an unforeseen raise still
            # closes the run, and the exception hook still logs its type.
            self._fail_run(run)
            raise

    def _open_from_dialogs(
        self, run: ArchiveRun, path: Path, kdf: KdfParams, gate: ArchiveGate
    ) -> None:
        """``on_open_backup`` once the run object exists: the admission again
        and the gate in ONE call (D11), then hop A."""
        self._render_controls()
        refusal = gate.begin_archive_run(run)
        if refusal is not None:
            self._end_run(refusal)
            return
        self._show_message(view.OPEN_RUNNING)
        self._start_hop(
            run, partial(_open_backup, run, path, kdf), partial(self._backup_opened, run, path)
        )

    def _backup_opened(self, run: ArchiveRun, path: Path, result: object) -> None:
        """Hop A returned: the passphrase zeroed at once. Then, here on the
        GUI thread, the restore plan (ONE archive listing; the retention
        setting only from a file that read) and the summary dialog — Close
        ends the run with nothing written; Restore starts the second
        whole-file verification on a worker. Restore is disabled while the
        local audit key or the retention setting cannot be read (D8)."""
        run.drop_passphrase()
        store, audit = self._store, self._audit
        if run is not self._run or store is None or audit is None:
            run.close()
            return
        if not isinstance(result, BackupFacts):
            self._end_run(view.backup_open_failed_line(self._noted("open", _as_failure(result))))
            return
        key = run.backup_key
        if key is None:
            self._end_run(view.backup_open_failed_line(view.HopFailed("unexpected")))
            return
        reader = BackupReader(path, result)
        run.attach_reader(reader)
        # Each input of Restore's decision fails closed when its check raises
        # (stage-4 leg x3): the retention setting reads as unreadable — no age
        # is judged, and Restore is disabled with its own line.
        try:
            settings_read = self._reload_settings()
        except Exception:  # noqa: BLE001 - Restore fails closed
            settings_read = False
        retention = self._settings.retention_days if settings_read else None
        # D8: Restore is disabled while the local audit key cannot be opened
        # for ANY reason, a passing one included (review round 33), and a
        # check that raises counts as not opened (round 32: fail closed).
        try:
            audit_unreadable = audit.key_unopenable()
        except Exception:  # noqa: BLE001 - Restore fails closed
            audit_unreadable = True
        # Review round 39: the line names "Start a new audit record" only
        # when the page offers it (the reset button, re-checked here, as after
        # any failed audit read); a key that cannot be opened just now, or a
        # check that raised, has its own line.
        audit_line = view.RESTORE_AUDIT_UNAVAILABLE
        if audit_unreadable:
            self._recheck_audit_key()
            if self._audit_key_unreadable:
                audit_line = view.RESTORE_NEEDS_AUDIT
        try:
            plan = plan_restore(
                reader,
                store,
                audit,
                self._sessions_root,
                k_b=key,
                retention_days=retention,
                now=self._clock(),
            )
        except Exception as exc:  # noqa: BLE001 - a closed code, never exception text (C3)
            self._end_run(view.backup_open_failed_line(self._noted("plan", view.hop_failure(exc))))
            return
        # Every reason Restore is disabled, each its own line (round 32 LOW).
        refusals = [
            line
            for line, applies in (
                (audit_line, audit_unreadable),
                (view.RESTORE_NEEDS_RETENTION, not settings_read),
            )
            if applies
        ]
        lines = view.restore_summary_lines(
            result, plan, ages_known=settings_read, restore_refusals=refusals, zone=self._zone
        )
        if not self._show_backup_summary(lines, not refusals) or refusals:
            self._end_run(view.OPEN_CLOSED)
            return
        self._run_failed_line = view.restore_failed_line
        self._show_message(view.RESTORE_RUNNING)
        self._start_hop(
            run,
            partial(_reverify_backup, run, path, result.file_sha256),
            partial(self._backup_reverified, run, plan),
        )

    def _backup_reverified(self, run: ArchiveRun, plan: RestorePlan, result: object) -> None:
        """Restore (Flow 3), once the worker verified the whole file again:
        the restorer here on the GUI thread (rows first, then entries, each
        rechecked), the last-backup date advanced to the file's date when it
        is later (a failure to save it is one sentence and stops nothing), the
        run ended, the page re-listed, then the final report line."""
        store, audit = self._store, self._audit
        reader, key = run.reader, run.backup_key
        if run is not self._run or store is None or audit is None:
            run.close()
            return
        if result is not True:
            self._end_run(view.restore_failed_line(self._noted("reverify", _as_failure(result))))
            return
        if reader is None or key is None:
            self._end_run(view.restore_failed_line(view.HopFailed("unexpected")))
            return
        try:
            report = restore_backup(reader, plan, store, audit, k_b=key, now=self._clock())
        except Exception as exc:  # noqa: BLE001 - a closed code, never exception text (C3)
            self._end_run(view.restore_failed_line(self._noted("restore", view.hop_failure(exc))))
            return
        if report.error_type is not None:
            self._noted("restore", view.HopFailed("unexpected", error_type=report.error_type))
        # Review round 32 LOW: the writes stand, so nothing after them may
        # end the run with a line that denies them.
        try:
            saved = self._advance_backup_date(reader.manifest.made_at)
        except Exception as exc:  # noqa: BLE001 - the date only; the type name logged (D4)
            self._noted("date", view.hop_failure(exc))
            saved = False
        self._end_run(None)
        self.refresh()  # the page re-listed BEFORE the line shows
        self._show_after_relist(view.restore_report_line(report, date_saved=saved))

    def _advance_backup_date(self, made_at: datetime) -> bool:
        """D10: ``last_backup_at`` advanced to a restored file's ``made_at``
        when that is later (the folder kept). False when a needed save failed
        — or when the file cannot be read just now: it is then left as it is,
        never rewritten without its folder or with an earlier date (review
        round 32 LOW)."""
        found = read_backup_settings(self._config_root)
        if found.unreadable:
            return False
        current = found.settings
        if current.last_backup_at is not None and made_at <= current.last_backup_at:
            return True
        try:
            save_backup_settings(
                BackupSettings(folder=current.folder, last_backup_at=made_at),
                config_root=self._config_root,
            )
        except (NoteConfigError, ValueError):
            return False
        self._last_backup_at = made_at
        return True

    # --- the set-aside (D8, D10; decision 0.15) ------------------------------

    def on_set_aside(self) -> None:
        """Set aside sessions that cannot be opened...: one confirmation, the
        run gate's admission (D11), then ``set_aside_refused`` — ONE call that
        runs to its end without yielding, so it takes no gate. The page is
        re-listed, the sweep's undated count lowered by the number moved, then
        the report line. A refusal moves nothing."""
        store, gate = self._store, self._archive_gate
        if store is None or gate is None or self._run is not None:
            self._show_message(view.SET_ASIDE_NOT_AVAILABLE)
            return
        self._disarm_delete()
        self._disarm_recording_delete()
        if not self._confirm(view.SET_ASIDE_CONFIRM, view.SET_ASIDE_ACTION):
            return
        refusal = gate.archive_run_refusal()
        if refusal is not None:
            self._show_message(refusal)
            return
        try:
            report = store.set_aside_refused()
        except Exception as exc:  # noqa: BLE001 - the view maps it to an authored line (C3)
            if not isinstance(exc, PastSessionError):
                self._noted("set_aside", view.hop_failure(exc))
            self.refresh()
            self._show_after_relist(view.set_aside_failed_line(exc))
            return
        self.refresh()
        moved = len(report.moved)
        swept = self._current_sweep()
        if moved and swept is not None and swept.undated:
            # The undated entries the sweep kept: those moved are gone (D10).
            self._last_sweep = (
                self._settings.retention_days,
                replace(swept, undated=max(0, swept.undated - moved)),
            )
            self._render_status()
        self._show_after_relist(view.set_aside_line(report))

    def _show_after_relist(self, line: str) -> None:
        """A line shown after the page re-listed itself (Restore, Set aside).
        When that re-list could not read the archive, its own line stays
        beside this one, so an archive that cannot be listed never looks
        empty (review round 39; round 16 LOW-003's rule)."""
        if self._store is not None and not self._listed and view.LIST_UNREADABLE not in line:
            line = f"{line} {view.LIST_UNREADABLE}"
        self._show_message(line)

    def _end_run(self, line: str | None) -> None:
        """Every exit of a run: the run object closed (both buffers zeroed,
        the gate released), then the line shown (None: the message is left
        as it is)."""
        run, self._run = self._run, None
        if run is not None:
            run.close()
        if line is not None:
            self._show_message(line)
        self._render_controls()

    def _fail_run(self, run: ArchiveRun) -> None:
        """An unforeseen failure: ``run`` closed, with the fixed line of its
        kind (Back up or Open a backup) when it is still the page's run
        (D4)."""
        if run is self._run:
            self._end_run(self._run_failed_line(view.HopFailed("unexpected")))
        else:
            run.close()

    def _start_hop(self, run: ArchiveRun, work: Callable[[], object], done: HopDone) -> None:
        """Dispatch one hop; a dispatch that fails ends the run, and so does a
        handler that raises (D4; review round 27 LOW-001 — re-raised, so the
        exception hook logs its type name)."""

        def handled(result: object) -> None:
            try:
                done(result)
            except BaseException:
                self._fail_run(run)
                raise

        try:
            self._run_hop(work, handled)
        except Exception as exc:  # noqa: BLE001 - a failed dispatch is a closed code
            self._noted("dispatch", view.hop_failure(exc))
            self._fail_run(run)

    def _noted(self, stage: str, failure: view.HopFailed) -> view.HopFailed:
        """D4 (peer round 29 PR-LOW-202): an UNFORESEEN failure's type name
        logged once, at the boundary that still has it, with its stage — the
        name only, never its text, a path or anything of the run. A named
        refusal or failure is its own line and is not logged. ``failure`` is
        returned for the caller's line."""
        if failure.error_type is not None and self._logger is not None:
            log_event(
                self._logger, "backup_unexpected", detail_code=stage, error_code=failure.error_type
            )
        return failure

    # --- the real worker and dialogs (production only; tests inject them) ---

    def _run_task(self, work: Callable[[], object], done: HopDone) -> None:
        """``work`` on a ``TaskThread`` child of this page; ``done`` is called
        exactly once on the GUI thread: with the result, with ``unexpected``
        when the worker failed, or — the fallback (D4) — with ``unexpected``
        when it ended with neither result signal. A start that raises before
        the thread runs takes its registration back (peer round 29
        PR-LOW-201: a thread that never ran sends no ``finished``, so nothing
        else would) and re-raises to the dispatch, which ends the run."""
        task = TaskThread(work, self)
        task.succeeded.connect(self._on_hop_succeeded)
        task.failed.connect(self._on_hop_failed)
        task.finished.connect(self._on_hop_finished)
        self._pending_hops[task] = done
        self._hops.append(task)
        try:
            task.start()
        except BaseException:
            if not task.isRunning():  # a running worker keeps close protection
                self._pending_hops.pop(task, None)
                if task in self._hops:
                    self._hops.remove(task)
                task.deleteLater()
            raise

    def _deliver(self, task: object, result: object) -> None:
        done = self._pending_hops.pop(task, None) if isinstance(task, TaskThread) else None
        if done is not None:
            done(result)

    def _on_hop_succeeded(self, result: object) -> None:
        self._deliver(self.sender(), result)

    def _on_hop_failed(self, _message: str) -> None:
        # ``Type: message`` is never shown or logged (C3): a closed code only.
        self._deliver(self.sender(), view.HopFailed("unexpected"))

    def _on_hop_finished(self) -> None:
        task = self.sender()
        if isinstance(task, TaskThread):
            self._hop_ended(task)

    def _hop_ended(self, task: TaskThread) -> None:
        """The worker ended: it leaves the busy list, and a hop that gave
        neither result signal is delivered as ``unexpected`` (D4's fallback;
        a delivered hop is not delivered again)."""
        if task in self._hops:
            self._hops.remove(task)
        task.finish()
        self._deliver(task, view.HopFailed("unexpected"))
        task.deleteLater()

    def _ask_real_passphrase(self, confirm: bool) -> bytearray | None:
        return backup_dialog.ask_passphrase(self.window(), confirm=confirm)

    def _ask_backup_path(self, start: Path | None, proposed: str) -> Path | None:
        """The backup's save dialog: the remembered folder while it still
        passes the location rule, else the system drive's root — never
        Documents (D7). Only the chosen folder is used, so the dialog never
        asks to replace a file (D6)."""
        folder = start if start is not None else Path(os.environ.get("SystemDrive", "C:") + "\\")
        name, _filter = QFileDialog.getSaveFileName(
            self,
            view.BACKUP_DIALOG_TITLE,
            str(folder / proposed),
            view.BACKUP_FILTER,
            options=QFileDialog.Option.DontConfirmOverwrite,
        )
        return Path(name) if name else None

    def _ask_backup_file(self, start: Path | None) -> Path | None:
        """Open a backup's open dialog: the remembered folder while it still
        passes the location rule, else the system drive's root (D7)."""
        folder = start if start is not None else Path(os.environ.get("SystemDrive", "C:") + "\\")
        name, _filter = QFileDialog.getOpenFileName(
            self, view.OPEN_BACKUP_DIALOG_TITLE, str(folder), view.BACKUP_FILTER
        )
        return Path(name) if name else None

    def _show_real_summary(self, lines: Sequence[str], restore_enabled: bool) -> bool:
        return backup_dialog.show_summary(self.window(), lines, restore_enabled=restore_enabled)

    # --- settings -------------------------------------------------------------

    def _load_settings(self) -> bool:
        """Read the settings file into ``_settings``. Unreadable: retention
        reads "never" (nothing is deleted — the sweep refuses) and names are
        HIDDEN (round 16 MED-001: fail toward hiding); the status line says
        so. Readable: a Hide names choice the file did not take
        (``_hide_override``) still stands, and a removed shorter window reads
        as 7 years (``_retention_raised``; the status line says so). True
        when the file was read."""
        try:
            read = read_past_session_settings(self._config_root)
        except PastSessionSettingsError:
            self._settings_unreadable = True
            self._retention_raised = False
            self._settings = PastSessionSettings(retention_days=None, hide_names=True)
            return False
        self._settings_unreadable = False
        self._retention_raised = read.retention_raised
        loaded = read.settings
        if self._hide_override is not None:
            loaded = PastSessionSettings(
                retention_days=loaded.retention_days, hide_names=self._hide_override
            )
        self._settings = loaded
        return True

    def _reload_settings(self) -> bool:
        """``_load_settings``, then the controls — and the list and the
        opened entry when the mask changed (no decrypt) — and ALWAYS the
        status line (round 19 PR-LOW-015): every route that reloads the
        settings (the tab opening, the sweep, Hide names, every exit of a
        retention choice) repaints the status from the state just read."""
        hidden = self._settings.hide_names
        readable = self._load_settings()
        self._render_settings()
        if self._settings.hide_names != hidden:
            self._render_list()
            self._render_entry()
        self._render_status()
        return readable

    def _render_settings(self) -> None:
        self.retention_combo.blockSignals(True)
        self.hide_names_checkbox.blockSignals(True)
        try:
            self.retention_combo.setCurrentIndex(
                view.retention_index(self._settings.retention_days)
            )
            self.hide_names_checkbox.setChecked(self._settings.hide_names)
        finally:
            self.retention_combo.blockSignals(False)
            self.hide_names_checkbox.blockSignals(False)

    def on_retention_chosen(self, index: int) -> None:
        """A retention choice — the one write that may replace an unreadable
        settings file. A SHORTER one asks first, is saved, then the sweep
        runs; a longer one is saved. An unsaved choice changes nothing. The
        same choice again saves only over a file that still holds a removed
        shorter window (``_retention_raised``) — that writes 7 years."""
        if not 0 <= index < len(view.RETENTION_OPTIONS):
            return
        days = view.RETENTION_OPTIONS[index][1]
        self._reload_settings()  # decide against the file as it is now
        # An unreadable file deletes nothing today: treat it as "never".
        old = None if self._settings_unreadable else self._settings.retention_days
        if days == old and not self._settings_unreadable and not self._retention_raised:
            return
        lowering = view.is_lowering(old, days)
        if lowering and not self._confirm(
            view.retention_confirm_text(days), view.RETENTION_CONFIRM_ACTION
        ):
            self._render_settings()
            self._show_message(view.retention_kept_line(old))
            return
        updated = PastSessionSettings(retention_days=days, hide_names=self._settings.hide_names)
        try:
            save_past_session_settings(updated, config_root=self._config_root)
        except PastSessionSettingsError:
            self._render_settings()
            self._show_message(view.SETTINGS_NOT_SAVED)
            return
        self._settings = updated
        self._settings_unreadable = False
        self._retention_raised = False  # the file now holds what is shown
        self._hide_override = None  # the mask shown is now the one saved
        self._render_settings()
        self._render_status()
        deleted = self.run_retention_sweep() if lowering else []
        swept = self._current_sweep()
        self._show_message(
            view.retention_changed_line(
                days, len(deleted), problem=lowering and swept is not None and swept.problem
            )
        )

    def on_hide_names(self, checked: bool) -> None:
        """Hide names (D13): masks every name on this screen at once, and is
        saved with the retention setting in the file. REFUSED while the
        settings file is unreadable — re-read at the click (round 16
        MED-001); the box is disabled then and names are hidden: saving it
        would write a retention the practitioner never chose over a file
        that may be recoverable, and only an explicit retention choice
        replaces that file. A choice the file did not take is kept for the
        rest of the run (``_hide_override``)."""
        if not self._reload_settings():  # repaints the status itself
            self._show_message(view.HIDE_NAMES_REFUSED)
            return
        updated = PastSessionSettings(
            retention_days=self._settings.retention_days, hide_names=bool(checked)
        )
        self._settings = updated
        self._render_settings()
        self._render_list()
        self._render_entry()
        try:
            save_past_session_settings(updated, config_root=self._config_root)
        except PastSessionSettingsError:
            self._hide_override = bool(checked)
            self._show_message(view.HIDE_NAMES_NOT_SAVED)
            return
        self._hide_override = None
        if self._retention_raised:  # the save wrote 7 years over the shorter one
            self._retention_raised = False
            self._render_status()

    # --- the retention sweep (Task 3.2) -----------------------------------

    def run_retention_sweep(self) -> list[str]:
        """Flow 4: load the setting (unreadable -> nothing deleted, and the
        status line says so), sweep the ONE shared store and record each
        deleted id as ``expired`` (``past_sessions_view.retention_sweep``).
        Deleted entries leave the list in memory; a sweep that could not
        delete everything due says so on the status line until one does
        (round 16 MED-002). Returns the ids deleted; NEVER raises (it runs
        from the app's timer)."""
        if self._store is None:
            return []
        try:
            if not self._reload_settings():  # repaints the status itself
                return []
            days = self._settings.retention_days
            report = view.retention_sweep(self._store, self._audit, days, self._clock())
        except Exception:  # noqa: BLE001 - a later tick tries again
            self._last_sweep = (
                self._settings.retention_days,
                RetentionSweepReport(complete=False),
            )
            self._render_status()
            return []
        self._last_sweep = (days, report)
        self._render_status()
        expired = [session_id for session_id, _date in report.expired]
        if expired:
            self._drop(expired)
        return expired

    # --- the audit record -------------------------------------------------

    def on_export(self) -> None:
        """Export CSV (Flow 5) to a path the practitioner chooses. The file
        is plaintext and outside custody — the line beside the button and
        the outcome say so."""
        audit = self._audit
        if audit is None or self._audit_key_unreadable:
            return
        path = self._choose_csv_path()
        if path is None:
            return
        try:
            count = audit.export_csv(path)
        except Exception as exc:  # noqa: BLE001 - the view maps it to an authored line (C3)
            self._show_message(view.export_failed_line(exc))
            self._recheck_audit_key()
            return
        self._show_message(view.export_done_line(count))

    def on_reset_audit(self) -> None:
        """D9: set the unreadable audit record aside and start a new one,
        after a confirmation. Nothing is deleted either way."""
        audit = self._audit
        if audit is None or not self._confirm(
            view.AUDIT_RESET_CONFIRM, view.AUDIT_RESET_CONFIRM_ACTION
        ):
            return
        try:
            audit.reset()
        except Exception as exc:  # noqa: BLE001 - the view maps it to an authored line (C3)
            self._show_message(view.reset_failed_line(exc))
        else:
            self._show_message(view.AUDIT_RESET_DONE)
        self._recheck_audit_key()

    # --- status and controls ----------------------------------------------

    def _current_sweep(self) -> RetentionSweepReport | None:
        """The latest sweep's report while it still describes the CURRENT
        setting — the file readable, the retention not "never", and the
        same one the sweep ran under (round 18 PR-LOW-014). Choosing "never",
        raising the setting, a hand-edit picked up by a reload, or an
        unreadable file drops the sweep's status lines at once, with no
        sweep (a raise still decrypts nothing); the next sweep under the
        new setting derives them again."""
        last = self._last_sweep
        if last is None or self._settings_unreadable:
            return None
        days, report = last
        if days is None or days != self._settings.retention_days:
            return None
        return report

    def status_lines(self) -> list[str]:
        """The persistent status line's parts, in order."""
        lines: list[str] = []
        if self._store is None:
            lines.append(view.STORE_UNAVAILABLE)
        if self._settings_unreadable:
            lines.append(view.SETTINGS_UNREADABLE_LINE)
        if self._retention_raised:
            lines.append(view.RETENTION_RAISED_LINE)
        swept = self._current_sweep()
        if swept is not None and swept.too_short:
            lines.append(view.SWEEP_TOO_SHORT_LINE)
        if swept is not None and swept.problem:
            lines.append(view.SWEEP_PROBLEM_LINE)
        if swept is not None and swept.undated:
            lines.append(view.undated_line(swept.undated))
        if self._audit_key_unreadable:
            lines.append(view.AUDIT_KEY_UNREADABLE_LINE)
        failures = self._audit_failures()
        if failures:
            lines.append(view.audit_failures_line(failures))
        # Development-recordings D9: the kept recordings due for review —
        # from the listing in memory (no decryption beyond the labels it
        # already read), so only while the tab holds a listing.
        due, _selected_due = self._review_state()
        if due:
            lines.append(view.review_due_line(due))
        # Past-sessions-backup plan D10: the backup reminder, from the listing
        # in memory, so only while the page holds one.
        backup = self._backup_line()
        if backup is not None:
            lines.append(backup)
        lines.extend(self._export_recovery_lines)
        lines.extend(self._exclusion_warnings)
        return lines

    def _audit_failures(self) -> int:
        return self._audit.failure_count if self._audit is not None else 0

    def _review_state(self) -> tuple[int, bool]:
        """D9's review reminder as now: how many kept recordings are due,
        and whether the selected entry's is — what the status line and the
        "Review due." mark show (codex round 23 PR-LOW-006: ``_tick``
        re-renders when it changes, so a recording that crosses its 12
        months while the tab stays open is marked without a refresh)."""
        now = self._clock()
        due = sum(
            1 for item in self._listings if item.recording_kept and view.review_due(item.label, now)
        )
        listing = self._selected_listing()
        selected = (
            listing is not None and listing.recording_kept and view.review_due(listing.label, now)
        )
        return due, selected

    def _backup_line(self) -> str | None:
        """D10's reminder (``backup_status_line``) over the listed entries'
        completion dates — an entry whose label cannot be read is not
        counted — or None while the page holds no listing."""
        if not self._listed:
            return None
        return view.backup_status_line(
            self._last_backup_at,
            [item.label.completed_at for item in self._listings if item.label is not None],
            self._clock(),
            zone=self._zone,
        )

    def _load_last_backup(self) -> None:
        """The last backup's date from ``config\\backup.json`` (absent or
        unreadable: none recorded)."""
        self._last_backup_at = read_backup_settings(self._config_root).settings.last_backup_at

    def _render_status(self) -> None:
        self._shown_failures = self._audit_failures()
        self._shown_review = self._review_state()
        self._shown_backup = self._backup_line()
        lines = self.status_lines()
        self.status_label.setText("\n".join(lines))
        self.status_label.setVisible(bool(lines))
        self.reset_audit_button.setVisible(self._audit_key_unreadable)
        self._render_controls()  # Hide names and Export follow these states

    def _render_controls(self) -> None:
        has_store = self._store is not None
        self.delete_button.setEnabled(has_store and self._selected_id() is not None)
        self.retention_combo.setEnabled(has_store)
        self.hide_names_checkbox.setEnabled(has_store and not self._settings_unreadable)
        # Round 16 LOW-009: an export the key cannot serve is disabled, and
        # the status line says why.
        self.export_button.setEnabled(self._audit is not None and not self._audit_key_unreadable)
        # Past-sessions-backup plan D10: always enabled, subject only to the
        # run gate (which disables the whole page) and this page's own run.
        self.backup_button.setEnabled(
            has_store and self._audit is not None and self._run is None
        )
        self.open_backup_button.setEnabled(
            has_store and self._audit is not None and self._run is None
        )
        # Task 3.4: shown only while the listing holds a session whose label
        # cannot be read (the store decides what qualifies; D8).
        unreadable = self._listed and any(item.label is None for item in self._listings)
        self.set_aside_button.setVisible(has_store and unreadable)
        self.set_aside_button.setEnabled(has_store and unreadable and self._run is None)
        opened = self._open_entry is not None
        reason = self._copy_reason()
        self.copy_button.setEnabled(reason is None)
        self.copy_button.setToolTip(reason or "")
        shown = reason if opened else None
        self.copy_reason_label.setText(shown or "")
        self.copy_reason_label.setVisible(shown is not None)
        self.transcript_button.setEnabled(opened)
        # Development-recordings Phase 3: the selected entry's kept recording
        # (from the listing's file check — no decryption).
        listing = self._selected_listing()
        kept = has_store and listing is not None and listing.recording_kept
        self.recording_box.setVisible(kept)
        self.delete_recording_button.setEnabled(kept)
        self.export_recording_button.setEnabled(kept)
        self.recording_line_label.setText(
            view.recording_line(listing.label, now=self._clock(), zone=self._zone)
            if kept and listing is not None
            else ""
        )

    def _tick(self) -> None:
        armed = self._delete_armed
        if armed is not None and not self._delete_confirmable(armed, armed[0]):
            self._disarm_delete()
        armed = self._recording_delete_armed
        if armed is not None and not self._delete_confirmable(armed, armed[0]):
            self._disarm_recording_delete()
        if (
            self._audit_failures() != self._shown_failures
            or self._review_state() != self._shown_review
            or self._backup_line() != self._shown_backup
        ):
            self._render_status()

    def _show_message(self, text: str) -> None:
        self.message_label.setText(text)

    # --- the real dialogs (production only; tests inject both) -------------

    def _ask(self, text: str, action: str) -> bool:
        """A confirmation whose buttons are named for what they do (design-
        system Microcopy), the safe one the default."""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(view.PAST_SESSIONS_TAB_TITLE)
        box.setText(text)
        go = box.addButton(action, QMessageBox.ButtonRole.AcceptRole)
        keep = box.addButton(view.CONFIRM_CANCEL, QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(keep)
        box.setEscapeButton(keep)
        box.exec()
        return box.clickedButton() is go

    def _ask_csv_path(self) -> Path | None:
        """The save dialog, opened in the practitioner's Documents folder
        (round 16 LOW-014: never the process's working directory)."""
        folder = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        start = str(Path(folder) / view.EXPORT_DEFAULT_NAME) if folder else view.EXPORT_DEFAULT_NAME
        name, _filter = QFileDialog.getSaveFileName(
            self, view.EXPORT_DIALOG_TITLE, start, view.EXPORT_FILTER
        )
        return Path(name) if name else None

    def _ask_wav_path(self, session_id: str) -> Path | None:
        """Development-recordings Task 3.3: the recording export's save
        dialog, proposing ``<session id>.wav`` in Documents. Only the chosen
        folder is used — the file is always named by the session id, so the
        dialog never asks to replace a file (review round 21 LOW-005: nothing
        is ever replaced; the success line names the file written)."""
        folder = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        proposed = f"{session_id}.wav"
        start = str(Path(folder) / proposed) if folder else proposed
        name, _filter = QFileDialog.getSaveFileName(
            self,
            view.EXPORT_RECORDING_DIALOG_TITLE,
            start,
            view.EXPORT_RECORDING_FILTER,
            options=QFileDialog.Option.DontConfirmOverwrite,
        )
        return Path(name) if name else None
