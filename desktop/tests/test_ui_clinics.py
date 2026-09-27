"""Clinics tab (Cliniko workflow safeguards plan Task 2.2): offscreen, with an
injected registry, key store and Cliniko transport — nothing touches the
network, Credential Manager or the host's ``clinics.json``."""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from scribe_desktop import cliniko_client as cc  # noqa: E402
from scribe_desktop.clinics import ClinicRefusal, ClinicRegistry, Refused  # noqa: E402
from scribe_desktop.ui import models  # noqa: E402
from test_clinics import (  # noqa: E402
    EMAIL,
    KEY,
    KEY_2,
    KEY_SECRET_NAME,
    PRACTITIONERS,
    MemoryKeyStore,
    ScriptedTransport,
    make_registry,
    ok,
    status,
)


@pytest.fixture(scope="module")
def qapp() -> Any:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _process_until(qapp: Any, predicate: Callable[[], bool], timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qapp.processEvents()
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


class GatedTransport(ScriptedTransport):
    """Blocks every request until ``release`` — a check still in flight."""

    def __init__(self, **routes: Any) -> None:
        super().__init__(**routes)
        self.entered = threading.Event()
        self.gate = threading.Event()

    def request(
        self, method: str, host: str, path: str, headers: Mapping[str, str], max_body: int
    ) -> cc.RawResponse:
        self.entered.set()
        assert self.gate.wait(10), "the test never released the gate"
        return super().request(method, host, path, headers, max_body)


def _screen(
    registry: ClinicRegistry, live: Callable[[], str | None] | None = None
) -> Any:
    from scribe_desktop.ui.clinics import ClinicsScreen

    return ClinicsScreen(registry, live_session_clinic=live)


def _fill(screen: Any, *, key: str = KEY, name: str = "Northside", address: str = "") -> None:
    screen.name_field.setText(name)
    screen.email_field.setText(EMAIL)
    screen.key_field.setText(key)
    screen.address_field.setText(address)


def _validate(qapp: Any, screen: Any, **fill: Any) -> None:
    _fill(screen, **fill)
    screen.on_validate()
    assert _process_until(qapp, lambda: not screen.is_busy)


def _select(screen: Any, row: int = 0) -> None:
    screen.clinic_list.setCurrentRow(row)


def _reaches(root: object, predicate: Callable[[object], bool], depth: int = 8) -> bool:
    """Breadth-first over ``gc.get_referents`` from ``root`` (types and
    modules not followed): does any reachable object satisfy ``predicate``?"""
    import gc
    import types

    seen: set[int] = {id(root)}
    frontier: list[object] = [root]
    for _ in range(depth):
        following: list[object] = []
        for obj in frontier:
            for ref in gc.get_referents(obj):
                if id(ref) in seen:
                    continue
                seen.add(id(ref))
                if predicate(ref):
                    return True
                if not isinstance(ref, (type, types.ModuleType)):
                    following.append(ref)
        frontier = following
    return False


def _no_key_on_screen(screen: Any) -> None:
    from PySide6.QtWidgets import QLabel, QLineEdit

    shown = [w.text() for w in screen.findChildren(QLabel)]
    shown += [w.text() for w in screen.findChildren(QLineEdit) if w is not screen.key_field]
    shown += [screen.clinic_list.item(i).text() for i in range(screen.clinic_list.count())]
    for text in shown:
        for key in (KEY, KEY_2):
            assert key not in text and key.split("-")[0] not in text


class TestConstruction:
    def test_nothing_is_called_or_read_at_startup_or_idle(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        store = MemoryKeyStore()
        transport = ScriptedTransport()
        seeded = make_registry(tmp_path, ScriptedTransport(), MemoryKeyStore())
        _validate(qapp, _screen(seeded))  # writes clinics.json
        registry = make_registry(tmp_path, transport, store)
        screen = _screen(registry)
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline:  # idle
            qapp.processEvents()
            time.sleep(0.01)
        assert transport.calls == []
        assert store.reads == 0
        assert screen.clinic_list.count() == 1
        screen.deleteLater()

    def test_the_form_masks_the_key_and_shows_the_advice(self, qapp: Any, tmp_path: Path) -> None:
        from PySide6.QtWidgets import QLabel, QLineEdit

        registry = make_registry(tmp_path)
        screen = _screen(registry)
        assert screen.key_field.echoMode() == QLineEdit.EchoMode.Password
        labels = [w.text() for w in screen.findChildren(QLabel)]
        assert models.CLINIC_KEY_CLIPBOARD_ADVICE in labels
        assert models.CLINICS_INTRO in labels
        assert not screen.replace_button.isEnabled()
        assert not screen.remove_button.isEnabled()
        assert screen.validate_button.isEnabled()
        screen.deleteLater()

    def test_the_saved_contact_email_is_prefilled(self, qapp: Any, tmp_path: Path) -> None:
        _validate(qapp, _screen(make_registry(tmp_path)))
        screen = _screen(make_registry(tmp_path))
        assert screen.email_field.text() == EMAIL
        screen.deleteLater()

    def test_a_damaged_list_is_named_and_every_change_is_disabled(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        (tmp_path / "clinics.json").write_bytes(b"{damaged")
        screen = _screen(make_registry(tmp_path))
        assert not screen.load_problem_label.isHidden()
        assert str(tmp_path / "clinics.json") in screen.load_problem_label.text()
        assert not screen.validate_button.isEnabled()
        assert not screen.replace_button.isEnabled()
        assert not screen.remove_button.isEnabled()
        screen.deleteLater()


class TestValidate:
    def test_validate_adds_the_clinic_and_clears_the_key_at_once(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        store = MemoryKeyStore()
        transport = GatedTransport()
        registry = make_registry(tmp_path, transport, store)
        screen = _screen(registry)
        changed: list[None] = []
        screen.clinics_changed.connect(lambda: changed.append(None))
        _fill(screen)
        screen.on_validate()
        # Cleared before the check runs, and its undo history with it.
        assert screen.key_field.text() == ""
        assert not screen.key_field.isUndoAvailable()
        assert screen.is_busy
        assert screen.status_label.text() == models.CLINIC_CHECKING_LINE
        assert not screen.validate_button.isEnabled()
        transport.gate.set()
        assert _process_until(qapp, lambda: not screen.is_busy)
        record = registry.records[0]
        assert screen.status_label.text() == models.clinic_success_line(_committed(record))
        assert screen.clinic_list.count() == 1
        assert screen.clinic_list.item(0).text() == models.clinic_row(record)
        assert store.keys == {(record.clinic_id, KEY_SECRET_NAME): KEY}
        assert changed
        assert screen.name_field.text() == ""
        _no_key_on_screen(screen)
        screen.deleteLater()

    def test_a_finished_check_leaves_no_reference_to_the_request(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 15 MED-006: the thread object stays a child of the tab, so
        its closure must not keep the request — and with it the typed key —
        alive after the result is committed."""
        from PySide6.QtCore import QThread

        from scribe_desktop.clinics import ValidationRequest

        screen = _screen(make_registry(tmp_path))
        _validate(qapp, screen)
        _validate(qapp, screen, key=KEY_2, name="Southside")  # a refused second check
        threads = [t for t in screen.findChildren(QThread) if hasattr(t, "_fn")]
        assert threads, "no finished check thread found to inspect"
        for thread in threads:
            assert not _reaches(thread._fn, lambda o: isinstance(o, ValidationRequest))
        assert screen._pending is None
        screen.deleteLater()

    def test_surrounding_whitespace_on_a_pasted_key_is_dropped(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Round 15 LOW-008: a paste often brings a space or a line end."""
        store = MemoryKeyStore()
        registry = make_registry(tmp_path, ScriptedTransport(), store)
        screen = _screen(registry)
        _validate(qapp, screen, key=f"  {KEY}\t ")
        assert store.keys == {(registry.records[0].clinic_id, KEY_SECRET_NAME): KEY}
        screen.deleteLater()

    def test_a_local_refusal_names_the_fix_and_sends_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        transport = ScriptedTransport()
        registry = make_registry(tmp_path, transport)
        screen = _screen(registry)
        _fill(screen, key="not-a-cliniko-key")
        screen.on_validate()
        assert not screen.is_busy
        assert screen.key_field.text() == ""
        assert screen.status_label.text() == models.clinic_refusal_line(
            Refused(ClinicRefusal.KEY_FORMAT),
            operation="add",
            clinic_name="",
            path=registry.path,
        )
        assert transport.calls == []
        screen.deleteLater()

    def test_a_refusal_from_cliniko_is_named_and_nothing_is_saved(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        store = MemoryKeyStore()
        registry = make_registry(tmp_path, ScriptedTransport(user=status(401)), store)
        screen = _screen(registry)
        _validate(qapp, screen)
        assert "Cliniko refused this key" in screen.status_label.text()
        assert store.keys == {} and screen.clinic_list.count() == 0
        _no_key_on_screen(screen)
        screen.deleteLater()

    def test_the_typed_address_route_says_it_is_unconfirmed(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        registry = make_registry(tmp_path, ScriptedTransport(public=status(403)))
        screen = _screen(registry)
        _validate(qapp, screen)
        assert "Type it in the clinic web address field" in screen.status_label.text()
        _validate(qapp, screen, address="northside.au2.cliniko.com")
        assert "confirmed the first time a note is checked" in screen.status_label.text()
        assert "not yet confirmed by a note" in screen.clinic_list.item(0).text()
        screen.deleteLater()

    def test_a_worker_failure_shows_fixed_copy_never_its_text(
        self, qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        registry = make_registry(tmp_path)

        def exploding(_request: Any) -> Any:
            raise RuntimeError(KEY)

        monkeypatch.setattr(registry, "run_validation", exploding)
        screen = _screen(registry)
        _validate(qapp, screen)
        assert screen.status_label.text() == models.CLINIC_CHECK_STOPPED_LINE
        assert registry.records == ()
        _no_key_on_screen(screen)
        screen.deleteLater()


def _committed(record: Any) -> Any:
    from scribe_desktop.clinics import Committed

    return Committed(record, replaced=False)


class TestReplaceAndRemove:
    def _one(self, qapp: Any, tmp_path: Path, transport: Any = None) -> tuple[Any, Any, Any]:
        store = MemoryKeyStore()
        registry = make_registry(tmp_path, transport or ScriptedTransport(), store)
        screen = _screen(registry)
        _validate(qapp, screen)
        _select(screen)
        return registry, store, screen

    def test_replace_key_checks_and_stores_the_new_key(self, qapp: Any, tmp_path: Path) -> None:
        registry, store, screen = self._one(qapp, tmp_path)
        clinic_id = registry.records[0].clinic_id
        changed: list[None] = []
        screen.clinics_changed.connect(lambda: changed.append(None))
        screen.key_field.setText(KEY_2)
        screen.on_replace_key()
        assert screen.key_field.text() == "" and changed  # the dispatch bumped the rev
        assert _process_until(qapp, lambda: not screen.is_busy)
        assert screen.status_label.text().startswith("The key for Northside was replaced")
        assert store.keys == {(clinic_id, KEY_SECRET_NAME): KEY_2}
        _no_key_on_screen(screen)
        screen.deleteLater()

    def test_replace_with_nothing_selected_clears_the_key_and_says_so(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        screen = _screen(make_registry(tmp_path))
        screen.key_field.setText(KEY_2)
        screen.on_replace_key()
        assert screen.key_field.text() == ""
        assert screen.status_label.text() == models.CLINIC_NO_SELECTION_LINE
        screen.deleteLater()

    def test_remove_needs_a_second_confirming_click(self, qapp: Any, tmp_path: Path) -> None:
        registry, store, screen = self._one(qapp, tmp_path)
        screen.on_remove()
        assert screen.remove_button.text() == models.CLINIC_REMOVE_CONFIRM_LABEL
        assert screen.status_label.text() == models.clinic_remove_prompt("Northside")
        assert len(registry.records) == 1 and store.keys
        screen.on_remove()
        assert registry.records == () and store.keys == {}
        assert screen.clinic_list.count() == 0
        assert screen.remove_button.text() == models.CLINIC_REMOVE_LABEL
        assert screen.status_label.text().startswith("Northside removed")
        screen.deleteLater()

    def test_changing_the_selection_disarms_remove(self, qapp: Any, tmp_path: Path) -> None:
        subdomains = iter(["northside", "southside"])
        transport = ScriptedTransport(
            public=lambda: ok({"account": {"subdomain": next(subdomains)}})
        )
        registry, _, screen = self._one(qapp, tmp_path, transport)
        _validate(qapp, screen, key=KEY_2, name="Southside")
        _select(screen, 0)
        screen.on_remove()
        _select(screen, 1)
        assert screen.remove_button.text() == models.CLINIC_REMOVE_LABEL
        screen.on_remove()  # arms again for the new selection; removes nothing
        assert len(registry.records) == 2
        screen.deleteLater()

    def test_remove_is_refused_while_the_live_session_is_linked(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        store = MemoryKeyStore()
        registry = make_registry(tmp_path, ScriptedTransport(), store)
        linked: list[str | None] = [None]
        screen = _screen(registry, live=lambda: linked[0])
        _validate(qapp, screen)
        _select(screen)
        linked[0] = registry.records[0].clinic_id
        screen.on_remove()
        screen.on_remove()
        assert screen.status_label.text() == (
            "Finish or discard the recording for Northside first."
        )
        assert len(registry.records) == 1 and store.keys
        screen.deleteLater()

    def test_removing_the_other_clinic_leaves_the_linked_one(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        subdomains = iter(["northside", "southside"])
        transport = ScriptedTransport(
            public=lambda: ok({"account": {"subdomain": next(subdomains)}})
        )
        store = MemoryKeyStore()
        registry = make_registry(tmp_path, transport, store)
        linked: list[str | None] = [None]
        screen = _screen(registry, live=lambda: linked[0])
        _validate(qapp, screen)
        _validate(qapp, screen, key=KEY_2, name="Southside")
        first, second = registry.records
        linked[0] = first.clinic_id
        rev = registry.rev(first.clinic_id)
        _select(screen, 1)
        screen.on_remove()
        screen.on_remove()
        assert registry.records == (first,) and registry.rev(first.clinic_id) == rev
        assert store.keys == {(first.clinic_id, KEY_SECRET_NAME): KEY}
        screen.deleteLater()


class TestDelayedResults:
    """Task 2.2's clinic-mutation verification through the tab."""

    def test_a_replace_result_landing_after_remove_restores_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        store = MemoryKeyStore()
        registry = make_registry(tmp_path, ScriptedTransport(), store)
        screen = _screen(registry)
        _validate(qapp, screen)
        gated = GatedTransport()
        registry._transport = gated  # the next check blocks in flight
        _select(screen)
        screen.key_field.setText(KEY_2)
        screen.on_replace_key()
        assert gated.entered.wait(5)
        # Remove stays available while a check runs, precisely to supersede it.
        assert screen.remove_button.isEnabled()
        assert not screen.replace_button.isEnabled()
        screen.on_remove()
        screen.on_remove()
        assert registry.records == () and store.keys == {}
        gated.gate.set()
        assert _process_until(qapp, lambda: not screen.is_busy)
        assert registry.records == () and store.keys == {}
        assert screen.clinic_list.count() == 0
        assert screen.status_label.text() == models.clinic_refusal_line(
            Refused(ClinicRefusal.CLINIC_GONE),
            operation="replace",
            clinic_name="",
            path=registry.path,
        )
        screen.deleteLater()

    def test_a_refused_replace_landing_after_remove_is_named_gone(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Codex round 17 PR-LOW-070: Cliniko's refusal of the superseded
        check never replaces the removal with a stale "refused this key"."""
        store = MemoryKeyStore()
        registry = make_registry(tmp_path, ScriptedTransport(), store)
        screen = _screen(registry)
        _validate(qapp, screen)
        gated = GatedTransport(user=status(401))
        registry._transport = gated
        _select(screen)
        screen.key_field.setText(KEY_2)
        screen.on_replace_key()
        assert gated.entered.wait(5)
        screen.on_remove()
        screen.on_remove()
        assert registry.records == () and store.keys == {}
        gated.gate.set()
        assert _process_until(qapp, lambda: not screen.is_busy)
        assert registry.records == () and store.keys == {}
        assert screen.clinic_list.count() == 0
        assert screen.status_label.text() == models.clinic_refusal_line(
            Refused(ClinicRefusal.CLINIC_GONE),
            operation="replace",
            clinic_name="",
            path=registry.path,
        )
        screen.deleteLater()

    def test_a_replace_landing_between_the_requests_drops_the_check(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        store = MemoryKeyStore()
        transport = ScriptedTransport()
        registry = make_registry(tmp_path, transport, store)
        screen = _screen(registry)
        _validate(qapp, screen)
        clinic_id = registry.records[0].clinic_id

        def practitioners_then_replace() -> cc.RawResponse:
            # A second Replace key dispatched mid-check (GUI-thread work the
            # registry would do; here from the worker for determinism).
            registry.begin_validation(api_key=KEY, contact_email=EMAIL, clinic_id=clinic_id)
            return ok(PRACTITIONERS)

        transport.routes["/v1/practitioners"] = practitioners_then_replace
        _select(screen)
        screen.key_field.setText(KEY_2)
        screen.on_replace_key()
        assert _process_until(qapp, lambda: not screen.is_busy)
        assert "was not used" in screen.status_label.text()
        assert store.keys == {(clinic_id, KEY_SECRET_NAME): KEY}
        screen.deleteLater()


class TestCopy:
    def test_every_refusal_has_copy_for_every_operation(self, tmp_path: Path) -> None:
        for reason in ClinicRefusal:
            for operation in ("add", "replace", "remove"):
                line = models.clinic_refusal_line(
                    Refused(reason, "0123456789abcdef"),
                    operation=operation,  # type: ignore[arg-type]
                    clinic_name="Northside",
                    path=tmp_path / "clinics.json",
                )
                assert line and "{" not in line and "!" not in line
