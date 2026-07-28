"""Recovery screen (Flow 3): lists recoverable session stores; the ONLY
actions are Resume processing and Discard — recording is NEVER resumed
after a crash (plan Critical Constraint). Stores without a Finish footer
carry the binding unfinished-store warning (PR-HIGH-007 residual)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop.session_store import default_sessions_root, discard_session
from scribe_desktop.transcription import RecoveryOutcome
from scribe_desktop.ui import models
from scribe_desktop.ui.tasks import TaskThread


def _describe(info: models.RecoverableSessionInfo) -> str:
    if info.created_at is not None:
        stamp = datetime.fromtimestamp(info.created_at, UTC).strftime("%Y-%m-%d %H:%M UTC")
    else:
        stamp = "unknown start time"
    label = f"Session {info.session_id[:8]}... ({stamp})"
    if not info.has_audio:
        return label + " - no audio recorded"
    if not info.store_finished:
        return label + " - did not finish cleanly"
    return label


class RecoveryScreen(QWidget):
    # Emitted with (Path, RecoveryOutcome) after resume-processing succeeds.
    recovered = Signal(object)

    def __init__(
        self,
        sessions_root: Path | None = None,
        *,
        active_ids_provider: Callable[[], frozenset[str]] | None = None,
        recovery_runner: Callable[[Path], RecoveryOutcome] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._root = sessions_root if sessions_root is not None else default_sessions_root()
        self._active_ids_provider = active_ids_provider or frozenset
        self._recovery_runner = (
            recovery_runner if recovery_runner is not None else models.build_recovery_runner()
        )
        self._task: TaskThread | None = None
        self._busy = False
        # PR round 18 (PR1/PR2, guard-only): sessions this screen has handed
        # off — an in-flight resume-processing run or a recovered session
        # whose transcript view still holds custody callbacks. They are
        # excluded from the listing (no second transcription / no discard
        # race against a pending Complete) AND reported to the sweep so it
        # never destroys a store mid-recovery.
        self._protected: set[str] = set()
        self._resuming_id: str | None = None

        self.session_list = QListWidget()
        self.session_list.currentItemChanged.connect(lambda *_: self._update_controls())
        self.warning_label = QLabel()
        self.warning_label.setStyleSheet("color: #b00020; font-weight: bold;")
        self.warning_label.setWordWrap(True)
        self.warning_label.hide()
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)

        self.resume_button = QPushButton("Resume processing")
        self.discard_button = QPushButton("Discard")
        self.refresh_button = QPushButton("Refresh")
        self.resume_button.clicked.connect(self.on_resume_processing)
        self.discard_button.clicked.connect(self.on_discard)
        self.refresh_button.clicked.connect(self.refresh)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()

        buttons = QHBoxLayout()
        buttons.addWidget(self.resume_button)
        buttons.addWidget(self.discard_button)
        buttons.addWidget(self.refresh_button)
        buttons.addStretch(1)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Recoverable sessions (24-hour window):"))
        layout.addWidget(self.session_list)
        layout.addWidget(self.warning_label)
        layout.addLayout(buttons)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.message_label)
        self.setLayout(layout)
        self.refresh()

    # --- listing -----------------------------------------------------------

    def refresh(self) -> None:
        self.session_list.clear()
        try:
            active = self._active_ids_provider()
        except Exception:  # noqa: BLE001 - conservative: exclude nothing
            active = frozenset()
        excluded = frozenset(active | self._protected)
        for info in models.list_recoverable_sessions(self._root, excluded):
            item = QListWidgetItem(_describe(info))
            item.setData(Qt.ItemDataRole.UserRole, info)
            self.session_list.addItem(item)
        self._update_controls()

    def _selected_info(self) -> models.RecoverableSessionInfo | None:
        item = self.session_list.currentItem()
        if item is None:
            return None
        info = item.data(Qt.ItemDataRole.UserRole)
        return info if isinstance(info, models.RecoverableSessionInfo) else None

    def _update_controls(self) -> None:
        info = self._selected_info()
        # PR round 19 (MED): while a recovered session's transcript is still
        # open (checked out), a second resume would overwrite its custody
        # callbacks — resume stays disabled until Complete/Discard releases.
        blocked = self._busy or bool(self._protected)
        has_selection = info is not None and not blocked
        self.resume_button.setEnabled(bool(has_selection and info is not None and info.has_audio))
        self.discard_button.setEnabled(bool(has_selection))
        self.refresh_button.setEnabled(not self._busy)
        if info is not None and not info.store_finished:
            # Binding Step-10 note: warn whenever store_finished is False.
            self.warning_label.setText(models.UNFINISHED_STORE_WARNING)
            self.warning_label.show()
        else:
            self.warning_label.hide()

    # --- checkout / sweep coordination --------------------------------------

    @property
    def is_busy(self) -> bool:
        """True while a resume-processing run is in flight."""
        return self._busy

    def protected_session_ids(self) -> frozenset[str]:
        """Session ids the expiry sweep must not touch: in-flight recovery
        plus recovered sessions awaiting Complete/Discard (PR round 18)."""
        return frozenset(self._protected)

    def release_checkout(self, session_id: str) -> None:
        """Release ONE recovered session once its transcript view closed
        (PR round 20, PR-HIGH-009: release must be scoped to the session
        that actually closed — an unscoped clear could strip sweep
        protection from an unrelated in-flight or open recovery)."""
        self._protected.discard(session_id)
        self.refresh()

    def release_checkouts(self) -> None:
        """Release every checkout (tests / teardown only — routing code
        must use the scoped ``release_checkout``)."""
        self._protected.clear()
        self.refresh()

    # --- actions -----------------------------------------------------------

    def on_resume_processing(self) -> None:
        info = self._selected_info()
        if info is None or self._busy:
            return
        if self._protected:
            self.message_label.setText(
                "Finish the open recovered transcript first (Complete or "
                "Discard) before resuming another session."
            )
            return
        self._busy = True
        self._resuming_id = info.session_id
        self._protected.add(info.session_id)
        self.progress_bar.show()
        self.message_label.setText("Resuming transcription locally...")
        self._update_controls()
        runner = self._recovery_runner
        directory = info.directory
        task = TaskThread(lambda: (directory, runner(directory)), self)
        task.succeeded.connect(self._on_recovered)
        task.failed.connect(self._on_recovery_failed)
        self._task = task
        task.start()

    def _join_task(self) -> None:
        if self._task is not None:
            self._task.wait(2000)
            self._task = None

    def _on_recovered(self, payload: object) -> None:
        self._busy = False
        self._resuming_id = None  # stays in _protected until release_checkouts
        self._join_task()
        self.progress_bar.hide()
        self.message_label.setText("Recovered - review the transcript.")
        self.refresh()
        self.recovered.emit(payload)

    def _on_recovery_failed(self, message: str) -> None:
        self._busy = False
        if self._resuming_id is not None:
            self._protected.discard(self._resuming_id)
            self._resuming_id = None
        self._join_task()
        self.progress_bar.hide()
        self.message_label.setText(
            f"Recovery failed ({message}). The session remains recoverable "
            "within its 24-hour window, or can be discarded."
        )
        self.refresh()

    def on_discard(self) -> None:
        info = self._selected_info()
        if info is None or self._busy:
            return
        try:
            # Key-first cryptographic deletion; no unwrapped key exists here.
            discard_session(info.directory, None)
            self.message_label.setText("Session discarded (audio cryptographically deleted).")
        except Exception as exc:  # noqa: BLE001
            self.message_label.setText(f"Discard failed: {type(exc).__name__}: {exc}")
        self.refresh()
