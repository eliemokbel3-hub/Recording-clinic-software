"""Clinics tab (Cliniko workflow safeguards plan Task 2.2): offscreen, with an
injected registry, key store and Cliniko transport — nothing touches the
network, Credential Manager or the host's ``clinics.json``."""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, get_args

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
        self,
        method: str,
        host: str,
        path: str,
        headers: Mapping[str, str],
        max_body: int,
        *,
        body: bytes | None = None,
    ) -> cc.RawResponse:
        self.entered.set()
        assert self.gate.wait(10), "the test never released the gate"
        return super().request(method, host, path, headers, max_body, body=body)


def _screen(
    registry: ClinicRegistry,
    live: Callable[[], str | None] | None = None,
    writing: Callable[[], str | None] | None = None,
    config_root: Path | None = None,
) -> Any:
    """Every screen a test builds gets a config root under the test's own
    directory (draft-write Task 5.4) — never the real ``%LOCALAPPDATA%``."""
    from scribe_desktop.ui.clinics import ClinicsScreen

    root = config_root if config_root is not None else registry.path.parent / "config"
    return ClinicsScreen(
        registry, live_session_clinic=live, writing_clinic=writing, config_root=root
    )


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

    def test_replace_key_is_refused_for_the_clinic_a_draft_write_uses(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        """Draft-write plan D9 (Task 4.1): the write read the clinic's key
        once for both hops, so Replace key waits for it — refused by the
        write-in-flight line, the typed key cleared, nothing dispatched, the
        rev and the stored key unchanged; after the write it works again."""
        store = MemoryKeyStore()
        registry = make_registry(tmp_path, ScriptedTransport(), store)
        writing: list[str | None] = [None]
        screen = _screen(registry, writing=lambda: writing[0])
        _validate(qapp, screen)
        _select(screen)
        clinic_id = registry.records[0].clinic_id
        rev = registry.rev(clinic_id)
        writing[0] = clinic_id
        changed: list[None] = []
        screen.clinics_changed.connect(lambda: changed.append(None))
        screen.key_field.setText(KEY_2)
        screen.on_replace_key()
        assert screen.status_label.text() == models.write_line("write_in_flight")
        assert screen.key_field.text() == ""
        assert not screen.is_busy and not changed
        assert registry.rev(clinic_id) == rev
        assert store.keys == {(clinic_id, KEY_SECRET_NAME): KEY}
        writing[0] = None
        screen.key_field.setText(KEY_2)
        screen.on_replace_key()
        assert _process_until(qapp, lambda: not screen.is_busy)
        assert store.keys == {(clinic_id, KEY_SECRET_NAME): KEY_2}
        screen.deleteLater()

    def test_replace_key_for_another_clinic_is_not_refused_by_a_write(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        subdomains = iter(["northside", "southside", "southside"])
        transport = ScriptedTransport(
            public=lambda: ok({"account": {"subdomain": next(subdomains)}})
        )
        store = MemoryKeyStore()
        registry = make_registry(tmp_path, transport, store)
        writing: list[str | None] = [None]
        screen = _screen(registry, writing=lambda: writing[0])
        _validate(qapp, screen)
        _validate(qapp, screen, key=KEY_2, name="Southside")
        first, second = registry.records
        writing[0] = first.clinic_id
        rev = registry.rev(second.clinic_id)
        _select(screen, 1)
        screen.key_field.setText(KEY_2)
        screen.on_replace_key()
        assert screen.status_label.text() != models.write_line("write_in_flight")
        assert _process_until(qapp, lambda: not screen.is_busy)
        assert screen.status_label.text().startswith("The key for Southside was replaced")
        assert registry.rev(second.clinic_id) != rev
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


class TestEmptyKey:
    """Draft-write Task 5.4 (the smoke follow-up, R22-11): an empty or
    whitespace-only key is named as missing, not as a bad format."""

    @pytest.mark.parametrize("key", ["", "   \t "])
    def test_validate_and_replace_name_a_missing_key(
        self, qapp: Any, tmp_path: Path, key: str
    ) -> None:
        transport = ScriptedTransport()
        registry = make_registry(tmp_path, transport)
        screen = _screen(registry)
        _fill(screen, key=key)
        screen.on_validate()
        missing = "Paste the clinic's Cliniko API key, then press Validate or Replace key."
        assert screen.status_label.text() == missing
        assert transport.calls == [] and not screen.is_busy
        _validate(qapp, screen)
        _select(screen)
        calls = len(transport.calls)
        screen.key_field.setText(key)
        screen.on_replace_key()
        assert screen.status_label.text() == missing
        assert len(transport.calls) == calls and not screen.is_busy
        screen.deleteLater()


class TestDefaultSource:
    """Draft-write Task 5.4 (D14): the selected clinic's "Cliniko template" /
    "My own defaults" choice and "Check file". No Cliniko request, ever."""

    def _one(
        self, qapp: Any, tmp_path: Path, writing: Callable[[], str | None] | None = None
    ) -> tuple[Any, Any, Any]:
        transport = ScriptedTransport()
        registry = make_registry(tmp_path, transport)
        screen = _screen(registry, writing=writing, config_root=tmp_path / "config")
        _validate(qapp, screen)
        transport.calls.clear()
        return registry, transport, screen

    @staticmethod
    def _defaults_file(tmp_path: Path, registry: Any) -> Path:
        return tmp_path / "config" / "template_defaults" / f"{registry.records[0].host}.json"

    def test_the_radios_follow_the_selection_and_a_refresh_writes_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        registry, transport, screen = self._one(qapp, tmp_path)
        assert not screen.source_group.isEnabled()  # nothing selected
        assert not screen.template_radio.isChecked() and not screen.own_radio.isChecked()
        saved = registry.path.read_bytes()
        _select(screen)
        assert screen.source_group.isEnabled()
        assert screen.template_radio.isChecked() and not screen.own_radio.isChecked()
        assert screen.check_file_button.isHidden() and screen.defaults_path_label.isHidden()
        screen.refresh()
        assert registry.path.read_bytes() == saved
        # Changed behind the tab: the next refresh shows it, and writes nothing.
        clinic_id = registry.records[0].clinic_id
        registry.set_default_source(clinic_id, "own_file", writing_clinic=None)
        changed = registry.path.read_bytes()
        screen.refresh()
        assert screen.own_radio.isChecked() and not screen.template_radio.isChecked()
        assert registry.path.read_bytes() == changed
        screen.clinic_list.setCurrentRow(-1)
        assert not screen.template_radio.isChecked() and not screen.own_radio.isChecked()
        assert registry.path.read_bytes() == changed
        assert transport.calls == []
        screen.deleteLater()

    def test_a_click_writes_once_and_the_same_value_writes_nothing(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        registry, transport, screen = self._one(qapp, tmp_path)
        _select(screen)
        clinic_id = registry.records[0].clinic_id
        writes: list[str] = []
        real = registry.set_default_source

        def spy(cid: str, source: Any, *, writing_clinic: str | None) -> Any:
            writes.append(source)
            return real(cid, source, writing_clinic=writing_clinic)

        registry.set_default_source = spy  # type: ignore[method-assign]
        screen.own_radio.click()
        assert writes == ["own_file"]
        assert registry.record(clinic_id).default_source == "own_file"
        assert screen.status_label.text() == models.clinic_default_source_line(
            "Northside", "own_file"
        )
        assert screen.own_radio.isChecked()
        assert not screen.check_file_button.isHidden()
        path = self._defaults_file(tmp_path, registry)
        assert screen.defaults_path_label.text() == models.clinic_defaults_path_line(path)
        screen.own_radio.click()  # the same value
        assert writes == ["own_file"]
        screen.template_radio.click()
        assert writes == ["own_file", "cliniko_template"]
        assert screen.check_file_button.isHidden()
        assert transport.calls == []
        assert not path.parent.exists()  # the app never creates the directory
        screen.deleteLater()

    def test_a_refused_write_puts_the_radio_back(self, qapp: Any, tmp_path: Path) -> None:
        writing: list[str | None] = [None]
        registry, transport, screen = self._one(qapp, tmp_path, writing=lambda: writing[0])
        _select(screen)
        clinic_id = registry.records[0].clinic_id
        # The clinic a draft write is in flight for.
        writing[0] = clinic_id
        screen.own_radio.click()
        assert screen.status_label.text() == models.write_line("write_in_flight")
        assert screen.template_radio.isChecked() and not screen.own_radio.isChecked()
        writing[0] = None
        # A write that fails leaves the file and the setting unchanged.
        saved = registry.path.read_bytes()

        def failing(*_args: Any) -> None:
            raise OSError("disk full")

        registry._write = failing  # type: ignore[method-assign]
        screen.own_radio.click()
        assert screen.status_label.text() == (
            "The setting for Northside could not be saved; it is unchanged."
        )
        assert screen.template_radio.isChecked()
        assert registry.path.read_bytes() == saved
        assert registry.record(clinic_id).default_source == "cliniko_template"
        # The registry's own gone-clinic refusal (a Remove landing between
        # the tab's read and the write) is named and the radio put back.
        del registry._write
        real = registry.set_default_source

        def gone(cid: str, source: Any, *, writing_clinic: str | None) -> Any:
            return Refused(ClinicRefusal.CLINIC_GONE, cid)

        registry.set_default_source = gone  # type: ignore[method-assign]
        screen.own_radio.click()
        assert screen.status_label.text() == "Northside is no longer set up in this app."
        assert screen.template_radio.isChecked() and not screen.own_radio.isChecked()
        registry.set_default_source = real  # type: ignore[method-assign]
        # A clinic gone behind the tab (no refresh yet) writes nothing and
        # shows no choice.
        registry._records = ()
        screen.own_radio.click()
        assert not screen.template_radio.isChecked() and not screen.own_radio.isChecked()
        assert registry.path.read_bytes() == saved
        assert transport.calls == []
        screen.deleteLater()

    def test_the_group_is_disabled_while_busy_and_with_a_load_problem(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        registry, _transport, screen = self._one(qapp, tmp_path)
        _select(screen)
        assert screen.source_group.isEnabled()
        screen._pending = object()  # a Validate or Replace key in flight
        screen._update_controls()
        assert not screen.source_group.isEnabled()
        screen._on_source_clicked(1)  # a click that still arrives writes nothing
        assert registry.records[0].default_source == "cliniko_template"
        assert not screen.own_radio.isChecked()
        screen._pending = None
        screen._update_controls()
        assert screen.source_group.isEnabled()
        screen.deleteLater()
        (tmp_path / "clinics.json").write_bytes(b"{damaged")
        damaged = _screen(make_registry(tmp_path), config_root=tmp_path / "config")
        assert not damaged.source_group.isEnabled()
        damaged.deleteLater()

    def test_check_file_names_each_outcome_and_reads_only_on_the_press(
        self, qapp: Any, tmp_path: Path
    ) -> None:
        registry, transport, screen = self._one(qapp, tmp_path)
        _select(screen)
        screen.own_radio.click()
        assert screen.defaults_label.text() == ""  # nothing read on the change
        path = self._defaults_file(tmp_path, registry)
        screen.on_check_file()
        assert screen.defaults_label.text() == models.CLINIC_DEFAULTS_MISSING
        path.parent.mkdir(parents=True)
        path.write_text(
            '{"schema_version": 1, "templates": {"Standard Consultation": '
            '{"History": {"Presenting complaint": "Site -"}}}}',
            encoding="utf-8",
        )
        assert screen.defaults_label.text() == models.CLINIC_DEFAULTS_MISSING  # no timer
        screen.check_file_button.click()
        assert screen.defaults_label.text() == models.CLINIC_DEFAULTS_OK.format(
            templates="1 template"
        )
        path.write_text("{not json", encoding="utf-8")
        screen.on_check_file()
        assert screen.defaults_label.text() == models.CLINIC_DEFAULTS_PROBLEM.format(
            problem="it is not in the expected format", location=": the file is not JSON"
        )
        path.write_bytes(b" " * (64 * 1024 + 1))
        screen.on_check_file()
        assert "it is larger than 64 KB" in screen.defaults_label.text()
        # The line goes with the clinic it was for.
        screen.template_radio.click()
        assert screen.defaults_label.text() == ""
        assert transport.calls == []
        screen.deleteLater()

    def test_the_check_lines_name_only_keys(self) -> None:
        from scribe_desktop.note_config import OwnDefaults, OwnDefaultsProblem

        two = OwnDefaults.model_validate(
            {"templates": {"A": {"S": {"Q": "x"}}, "B": {}}}
        )
        assert "lists 2 templates" in models.clinic_defaults_check_line(two)
        assert models.clinic_defaults_check_line(OwnDefaultsProblem("unreadable")) == (
            "The file cannot be used (it cannot be read). Correct it, then press Check "
            "file again."
        )
        from scribe_desktop.note_config import OwnDefaultsProblemKind

        for kind in get_args(OwnDefaultsProblemKind):  # every kind has a line
            line = models.clinic_defaults_check_line(OwnDefaultsProblem(kind))
            assert line and "{" not in line, kind


class TestCopy:
    def test_every_refusal_has_copy_for_every_operation(self, tmp_path: Path) -> None:
        operations = get_args(models.ClinicOperation)
        assert operations == ("add", "replace", "remove", "default_source")
        for reason in ClinicRefusal:
            for operation in operations:
                line = models.clinic_refusal_line(
                    Refused(reason, "0123456789abcdef"),
                    operation=operation,
                    clinic_name="Northside",
                    path=tmp_path / "clinics.json",
                )
                assert line and "{" not in line and "!" not in line

    def _line(self, reason: ClinicRefusal, operation: Any, tmp_path: Path) -> str:
        return models.clinic_refusal_line(
            Refused(reason, "0123456789abcdef"),
            operation=operation,
            clinic_name="Northside",
            path=tmp_path / "clinics.json",
        )

    def test_the_default_source_change_has_its_own_lines(self, tmp_path: Path) -> None:
        """Cliniko draft-write plan Task 3.1a (R22-05): the setting's write
        failure and gone clinic read as a setting change, and the writing
        clinic's refusal is the write's own sentence."""
        assert self._line(ClinicRefusal.REGISTRY_WRITE_FAILED, "default_source", tmp_path) == (
            "The setting for Northside could not be saved; it is unchanged."
        )
        assert self._line(ClinicRefusal.CLINIC_GONE, "default_source", tmp_path) == (
            "Northside is no longer set up in this app."
        )
        # The other operations keep the shared "result" wording.
        assert "the result was not used" in self._line(
            ClinicRefusal.CLINIC_GONE, "replace", tmp_path
        )
        for operation in get_args(models.ClinicOperation):
            assert self._line(ClinicRefusal.WRITE_IN_FLIGHT, operation, tmp_path) == (
                models.WRITE_LINES["write_in_flight"]
            )
