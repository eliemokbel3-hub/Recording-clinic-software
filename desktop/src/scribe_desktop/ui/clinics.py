"""Clinics tab (Cliniko workflow safeguards plan Task 2.2, D9/D10).

Where the practitioner adds each clinic's Cliniko API key, replaces it, or
removes the clinic. Nothing here talks to Cliniko on its own: the only calls
are the one ``ClinicRegistry.run_validation`` a Validate or Replace key
press dispatches, on a ``TaskThread``. Construction reads the registry's
file and nothing else — no key, no network, no timer.

The key field is password-masked and read ONCE per press, then cleared with
``setText("")`` (which also clears its undo history) before the check
starts; the key is never shown again, never put in a status line, and a
worker failure is reported with fixed copy (never the exception's text).

Stale results (D9): a result is committed on the GUI thread through
``ClinicRegistry.commit_validation``, which refuses it whole when the
clinic's ``clinic_rev`` moved since dispatch (a later Replace key or a
Remove) — Remove stays available while a check runs precisely so it can
supersede one. Remove takes a second, confirming click and is refused while
the live session is linked to that clinic (D10); the live-session link is
the ``live_session_clinic`` provider's answer at the confirming click.
Replace key is refused for the clinic a Cliniko draft write is in flight for
(the ``writing_clinic`` provider — cliniko-draft-write D9).
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop.clinics import (
    ClinicRegistry,
    Refused,
    ValidatedAccount,
    ValidationRequest,
)
from scribe_desktop.ui import models
from scribe_desktop.ui.lists import NoCopyListWidget
from scribe_desktop.ui.tasks import TaskThread


def _plain_label(text: str = "") -> QLabel:
    label = QLabel(text)
    # Plain text always: rows and lines carry practitioner-typed names.
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    return label


class ClinicsScreen(QWidget):
    # Emitted after any change to the registry or to a clinic's rev (a
    # Replace key dispatched, a commit, a Remove): the allow-list and every
    # clinic-bound result must be re-read by whoever holds them.
    clinics_changed = Signal()

    def __init__(
        self,
        registry: ClinicRegistry,
        *,
        live_session_clinic: Callable[[], str | None] | None = None,
        writing_clinic: Callable[[], str | None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._registry = registry
        self._live_session_clinic: Callable[[], str | None] = (
            live_session_clinic if live_session_clinic is not None else (lambda: None)
        )
        # Draft-write plan D9: the clinic a Cliniko draft write in flight uses
        # — its key was read once for the whole write, so Replace key waits.
        self._writing_clinic: Callable[[], str | None] = (
            writing_clinic if writing_clinic is not None else (lambda: None)
        )
        self._task: TaskThread | None = None
        self._pending: ValidationRequest | None = None
        self._pending_operation: models.ClinicOperation = "add"
        self._remove_armed: str | None = None

        self.clinic_list = NoCopyListWidget()
        self.clinic_list.currentItemChanged.connect(lambda *_: self._on_selection_changed())
        self.load_problem_label = _plain_label()
        self.load_problem_label.setStyleSheet("color: #b00020; font-weight: bold;")
        self.load_problem_label.hide()

        self.name_field = QLineEdit()
        self.name_field.setMaxLength(60)
        self.name_field.setPlaceholderText("e.g. Northside clinic")
        self.email_field = QLineEdit(registry.contact_email or "")
        self.email_field.setPlaceholderText("you@example.com")
        self.key_field = QLineEdit()
        self.key_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_field.setPlaceholderText("Paste the API key")
        self.address_field = QLineEdit()
        self.address_field.setPlaceholderText("yourclinic.au2.cliniko.com")

        form = QFormLayout()
        form.addRow("Clinic name", self.name_field)
        form.addRow("Your contact email", self.email_field)
        form.addRow("Cliniko API key", self.key_field)
        form.addRow("Clinic web address", self.address_field)

        self.validate_button = QPushButton("Validate")
        self.replace_button = QPushButton("Replace key")
        self.remove_button = QPushButton(models.CLINIC_REMOVE_LABEL)
        self.validate_button.clicked.connect(self.on_validate)
        self.replace_button.clicked.connect(self.on_replace_key)
        self.remove_button.clicked.connect(self.on_remove)
        buttons = QHBoxLayout()
        buttons.addWidget(self.validate_button)
        buttons.addWidget(self.replace_button)
        buttons.addWidget(self.remove_button)
        buttons.addStretch(1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        self.status_label = _plain_label()
        self.clipboard_label = _plain_label(models.CLINIC_KEY_CLIPBOARD_ADVICE)

        layout = QVBoxLayout()
        layout.addWidget(_plain_label(models.CLINICS_INTRO))
        layout.addWidget(QLabel("Clinics set up on this computer:"))
        layout.addWidget(self.clinic_list)
        layout.addWidget(self.load_problem_label)
        layout.addLayout(form)
        layout.addWidget(_plain_label(models.CLINIC_ADDRESS_HINT))
        layout.addWidget(self.clipboard_label)
        layout.addLayout(buttons)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addStretch(1)
        self.setLayout(layout)
        self.refresh()

    # --- state ---------------------------------------------------------------

    @property
    def is_busy(self) -> bool:
        """True while a Validate or Replace key check is in flight."""
        return self._pending is not None

    @property
    def pending_clinic_id(self) -> str | None:
        """The clinic a Validate or Replace key in flight is for (a new
        clinic's freshly minted id for a Validate), or None — the
        draft write refuses a Write click for that clinic (draft-write Task
        5.2, round 14 LOW-011: a Replace key committing during hop 2 would
        leave the PATCH under a key the registry no longer holds)."""
        pending = self._pending
        return pending.clinic_id if pending is not None else None

    def refresh(self) -> None:
        selected = self._selected_clinic_id()
        self.clinic_list.blockSignals(True)
        self.clinic_list.clear()
        for record in self._registry.records:
            item = QListWidgetItem(models.clinic_row(record))
            item.setData(Qt.ItemDataRole.UserRole, record.clinic_id)
            self.clinic_list.addItem(item)
            if record.clinic_id == selected:
                self.clinic_list.setCurrentItem(item)
        self.clinic_list.blockSignals(False)
        problem = self._registry.load_problem
        if problem is not None:
            self.load_problem_label.setText(
                models.clinic_load_problem_line(problem, self._registry.path)
            )
            self.load_problem_label.show()
        else:
            self.load_problem_label.hide()
        if self._remove_armed is not None and self._remove_armed != self._selected_clinic_id():
            self._disarm_remove()
        self._update_controls()

    def _selected_clinic_id(self) -> str | None:
        item = self.clinic_list.currentItem()
        if item is None:
            return None
        clinic_id = item.data(Qt.ItemDataRole.UserRole)
        return clinic_id if isinstance(clinic_id, str) else None

    def _clinic_name(self, clinic_id: str | None) -> str:
        record = self._registry.record(clinic_id) if clinic_id is not None else None
        return record.display_name if record is not None else ""

    def _update_controls(self) -> None:
        usable = self._registry.load_problem is None
        selected = self._selected_clinic_id() is not None
        self.validate_button.setEnabled(usable and not self.is_busy)
        self.replace_button.setEnabled(usable and selected and not self.is_busy)
        self.remove_button.setEnabled(usable and selected)

    def _on_selection_changed(self) -> None:
        self._disarm_remove()
        self._update_controls()

    def _disarm_remove(self) -> None:
        self._remove_armed = None
        self.remove_button.setText(models.CLINIC_REMOVE_LABEL)

    def _take_key(self) -> str:
        """Read the key once and clear the field (``setText`` also clears
        its undo history) before anything else runs. Surrounding whitespace
        from a paste is dropped (round 15 LOW-008): the key alphabet has
        none, and the registry stays strict about everything else."""
        key = self.key_field.text().strip()
        self.key_field.setText("")
        return key

    def _refuse(self, refusal: Refused, operation: models.ClinicOperation) -> None:
        self.status_label.setText(
            models.clinic_refusal_line(
                refusal,
                operation=operation,
                clinic_name=self._clinic_name(refusal.clinic_id),
                path=self._registry.path,
            )
        )

    # --- Validate / Replace key ------------------------------------------------

    def on_validate(self) -> None:
        if self.is_busy:
            return
        self._disarm_remove()
        request = self._registry.begin_validation(
            api_key=self._take_key(),
            contact_email=self.email_field.text(),
            display_name=self.name_field.text(),
            typed_address=self.address_field.text(),
        )
        self._dispatch(request, "add")

    def on_replace_key(self) -> None:
        if self.is_busy:
            return
        self._disarm_remove()
        clinic_id = self._selected_clinic_id()
        if clinic_id is None:
            self.key_field.setText("")
            self.status_label.setText(models.CLINIC_NO_SELECTION_LINE)
            return
        if self._writing_clinic() == clinic_id:
            self.key_field.setText("")
            self.status_label.setText(models.write_line("write_in_flight"))
            return
        request = self._registry.begin_validation(
            api_key=self._take_key(),
            contact_email=self.email_field.text(),
            clinic_id=clinic_id,
            typed_address=self.address_field.text(),
        )
        if not isinstance(request, Refused):
            # D9: the dispatch bumped the clinic's rev — anything clinic-bound
            # that was pending under the old key is now stale.
            self.clinics_changed.emit()
        self._dispatch(request, "replace")

    def _dispatch(
        self, request: ValidationRequest | Refused, operation: models.ClinicOperation
    ) -> None:
        if isinstance(request, Refused):
            self._refuse(request, operation)
            return
        registry = self._registry
        self._pending = request
        self._pending_operation = operation
        # The closure hands the request (and so the typed key) to the worker
        # and keeps NO reference to it afterwards — the holder pattern of
        # `ui/note.py`'s prose job: the thread object is a child of this tab,
        # so anything the closure retained would live as long as the tab does
        # (round 15 MED-006). The only other reference is `_pending`, dropped
        # when the result is committed.
        holder = [request]
        task = TaskThread(lambda: registry.run_validation(holder.pop()), self)
        task.succeeded.connect(self._on_checked)
        task.failed.connect(self._on_check_failed)
        self._task = task
        self.progress_bar.show()
        self.status_label.setText(models.CLINIC_CHECKING_LINE)
        self._update_controls()
        task.start()

    def _finish_task(self) -> tuple[ValidationRequest | None, models.ClinicOperation]:
        request, operation = self._pending, self._pending_operation
        self._pending = None
        if self._task is not None:
            self._task.finish()
            self._task = None
        self.progress_bar.hide()
        return request, operation

    def _on_checked(self, result: object) -> None:
        request, operation = self._finish_task()
        if request is None or not isinstance(result, (ValidatedAccount, Refused)):
            self.status_label.setText(models.CLINIC_CHECK_STOPPED_LINE)
            self.refresh()
            return
        outcome = self._registry.commit_validation(request, result)
        del request
        if isinstance(outcome, Refused):
            self._refuse(outcome, operation)
        else:
            self.status_label.setText(models.clinic_success_line(outcome))
            self.name_field.setText("")
            self.address_field.setText("")
        self.refresh()
        self.clinics_changed.emit()

    def _on_check_failed(self, _message: str) -> None:
        # The worker never raises (run_validation returns a refusal for every
        # failure); if it does, its text is never shown — fixed copy only.
        self._finish_task()
        self.status_label.setText(models.CLINIC_CHECK_STOPPED_LINE)
        self.refresh()

    # --- Remove ----------------------------------------------------------------

    def on_remove(self) -> None:
        clinic_id = self._selected_clinic_id()
        if clinic_id is None:
            self.status_label.setText(models.CLINIC_NO_SELECTION_LINE)
            return
        if self._remove_armed != clinic_id:
            self._remove_armed = clinic_id
            self.remove_button.setText(models.CLINIC_REMOVE_CONFIRM_LABEL)
            self.status_label.setText(models.clinic_remove_prompt(self._clinic_name(clinic_id)))
            return
        self._disarm_remove()
        name = self._clinic_name(clinic_id)
        outcome = self._registry.remove(clinic_id, live_session_clinic=self._live_session_clinic())
        if isinstance(outcome, Refused):
            self.status_label.setText(
                models.clinic_refusal_line(
                    outcome, operation="remove", clinic_name=name, path=self._registry.path
                )
            )
        else:
            self.status_label.setText(models.clinic_success_line(outcome))
        self.refresh()
        self.clinics_changed.emit()
