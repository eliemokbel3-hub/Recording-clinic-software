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
- The confirmations and the save dialog are injected seams (``confirm``,
  ``choose_csv_path``), so a test never opens a real dialog (C6).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime, tzinfo
from pathlib import Path

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
from scribe_desktop.past_sessions import (
    PastSessionEntry,
    PastSessionListing,
    PastSessionSettings,
    PastSessionSettingsError,
    PastSessionStore,
    RetentionSweepReport,
    read_past_session_settings,
    save_past_session_settings,
)
from scribe_desktop.ui import models
from scribe_desktop.ui import past_sessions_view as view
from scribe_desktop.ui.lists import NoCopyComboBox, NoCopyListWidget
from scribe_desktop.ui.note import _place_note_text

# How often the tab re-checks what changes without a click: the Delete now
# arming's expiry and the audit's in-memory failure count (no disk, no key).
_TICK_MS = 1000

# ``confirm(text, action)``: the question and the name of the button that
# goes ahead (the other one keeps things as they are). True to go ahead.
Confirm = Callable[[str, str], bool]
ChooseCsvPath = Callable[[], Path | None]


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
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        # Task 4.1 (Flow 6): the start-up exclusion warnings — fixed for the
        # run (computed before the window was built), so the derived status
        # line always carries them.
        self._exclusion_warnings = tuple(exclusion_warnings)
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

        left = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(list_box, 1)
        left_layout.addWidget(settings_box)
        left_layout.addWidget(export_box)
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
        self._show_message("")
        self._reload_settings()
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
        self._listings = []
        self._listed = False
        self._render_list()

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

    def _on_selection_changed(self) -> None:
        self._disarm_delete()
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
        listing = PastSessionListing(entry.label.session_id, entry.label)
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
        if _place_note_text(
            models.format_note_body(entry.saved_note), shadow=entry.label.shadow
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
        self._listings = [item for item in self._listings if item.session_id not in gone]
        self._render_list()

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
        lines.extend(self._exclusion_warnings)
        return lines

    def _audit_failures(self) -> int:
        return self._audit.failure_count if self._audit is not None else 0

    def _render_status(self) -> None:
        self._shown_failures = self._audit_failures()
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
        opened = self._open_entry is not None
        reason = self._copy_reason()
        self.copy_button.setEnabled(reason is None)
        self.copy_button.setToolTip(reason or "")
        shown = reason if opened else None
        self.copy_reason_label.setText(shown or "")
        self.copy_reason_label.setVisible(shown is not None)
        self.transcript_button.setEnabled(opened)

    def _tick(self) -> None:
        armed = self._delete_armed
        if armed is not None and not self._delete_confirmable(armed, armed[0]):
            self._disarm_delete()
        if self._audit_failures() != self._shown_failures:
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
