"""Step 8: status/self-test logic tests + offscreen window smoke test.

Phase 2 Step 12 adds the single-instance guard battery (named mutex,
peer round 18 PR4 — priority raised by the 2026-07-28 live smoke).
"""

import os
import sys
from uuid import uuid4

import pytest

from scribe_desktop.status import read_registration_status, run_self_test

windows_only = pytest.mark.skipif(
    sys.platform != "win32", reason="named mutexes are Windows-only"
)


def test_registration_status_reads_real_machine_state() -> None:
    # LOW-016: skip loudly on unregistered machines instead of passing vacuously.
    status = read_registration_status()
    if status.registry_value is None:
        pytest.skip("machine not registered — run scripts/register-native-host.py")
    assert status.manifest_exists
    assert status.launcher_exists
    assert status.registered


def test_registration_chain_is_chrome_resolvable() -> None:
    """Both silent-failure modes found at the Phase-1 gate, now enforced:
    Chrome resolves neither a manifest under a path containing spaces nor a
    .bat/.cmd host — in both cases it reports only 'host not found'."""
    import json
    from pathlib import Path

    status = read_registration_status()
    if status.registry_value is None:
        pytest.skip("machine not registered — run scripts/register-native-host.py")

    manifest_path = Path(status.registry_value)
    assert " " not in str(manifest_path), f"manifest path has spaces: {manifest_path}"
    host_path = Path(json.loads(manifest_path.read_text(encoding="utf-8"))["path"])
    assert " " not in str(host_path), f"host path has spaces: {host_path}"
    assert host_path.suffix.lower() == ".exe", f"host must be an .exe, got {host_path}"
    assert host_path.is_file()


def test_self_test_passes_end_to_end() -> None:
    results = run_self_test()
    assert [r.name for r in results] == ["credential_store", "session_crypto"]
    assert all(r.passed for r in results), [f"{r.name}: {r.detail}" for r in results]


@pytest.mark.skipif(os.environ.get("SCRIBE_SKIP_GUI") == "1", reason="GUI smoke disabled")
def test_window_offscreen_smoke(tmp_path) -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from scribe_desktop.audio_capture import MockCaptureBackend
    from scribe_desktop.session import SessionController
    from scribe_desktop.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    backend = MockCaptureBackend()
    controller = SessionController(backend, sessions_root=tmp_path / "sessions")
    window = MainWindow(controller, backend, sessions_root=tmp_path / "sessions")
    panel = window.status_panel
    assert "Registration:" in panel.registration_label.text()
    panel.on_self_test()
    assert "PASS" in panel.self_test_label.text()
    assert "FAIL" not in panel.self_test_label.text()
    window.close()
    del app


def test_sweep_protected_ids_covers_nonterminal_controller_session(tmp_path) -> None:
    """Round 42 MED-001 (guard-only, pending user ratification): the sweep
    exemption must include the controller's own session in ANY non-terminal
    state — a QUEUED transcript open for review must not lose its key at
    the 24 h boundary mid-review (PR-round-18 PR2 gave recovered checkouts
    this protection; the live path gets the same)."""
    from scribe_desktop.app import sweep_protected_ids
    from scribe_desktop.audio_capture import MockCaptureBackend
    from scribe_desktop.session import SessionController, SessionState

    controller = SessionController(MockCaptureBackend(), sessions_root=tmp_path)
    assert sweep_protected_ids(controller) == frozenset()

    session = controller.start(0)
    assert session.session_id in sweep_protected_ids(controller)  # state-active

    controller.finish()
    controller.mark_queued()
    assert controller.state is SessionState.QUEUED
    # QUEUED is NOT state-active — the MED-001 widening must still cover it,
    # and extra ids (recovery checkouts) must pass through untouched.
    protected = sweep_protected_ids(controller, frozenset({"extra-checkout"}))
    assert session.session_id in protected
    assert "extra-checkout" in protected

    controller.discard()  # terminal: protection correctly lapses
    assert sweep_protected_ids(controller) == frozenset()


# ---------------------------------------------------------------------------
# Step 12: single-instance guard (named mutex; peer round 18 PR4)
# ---------------------------------------------------------------------------


def _unique_mutex_name() -> str:
    # Global\ deliberately: the production default uses the Global namespace,
    # so these tests also prove a standard user can create there.
    return f"Global\\ClinikoScribe-test-{uuid4().hex}"


@windows_only
class TestSingleInstanceLock:
    def test_first_acquire_owns_and_second_refuses(self) -> None:
        from scribe_desktop.app import acquire_single_instance_lock, release_single_instance_lock

        name = _unique_mutex_name()
        acquired, handle = acquire_single_instance_lock(name)
        assert acquired and handle
        try:
            assert acquire_single_instance_lock(name) == (False, 0)
        finally:
            release_single_instance_lock(handle)

    def test_released_lock_can_be_reacquired(self) -> None:
        from scribe_desktop.app import acquire_single_instance_lock, release_single_instance_lock

        name = _unique_mutex_name()
        acquired, handle = acquire_single_instance_lock(name)
        assert acquired
        release_single_instance_lock(handle)
        acquired_again, handle_again = acquire_single_instance_lock(name)
        assert acquired_again and handle_again
        release_single_instance_lock(handle_again)

    def test_busy_probe_does_not_pin_the_name(self) -> None:
        # The (False, 0) path must CLOSE the handle CreateMutexW returned:
        # a refused second launch must not keep the name alive after the
        # first instance exits.
        from scribe_desktop.app import acquire_single_instance_lock, release_single_instance_lock

        name = _unique_mutex_name()
        _, owner_handle = acquire_single_instance_lock(name)
        assert acquire_single_instance_lock(name) == (False, 0)
        release_single_instance_lock(owner_handle)
        acquired, handle = acquire_single_instance_lock(name)
        assert acquired and handle, "busy probe leaked a handle and pinned the mutex name"
        release_single_instance_lock(handle)

    def test_default_name_is_per_user_and_namespace_safe(self) -> None:
        from scribe_desktop.app import _single_instance_mutex_name

        name = _single_instance_mutex_name()
        assert name.startswith("Global\\ClinikoScribe-app-")
        # Backslash is the kernel object-namespace separator — the user part
        # must never introduce one.
        assert "\\" not in name.removeprefix("Global\\")


@windows_only
def test_main_refuses_second_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() wiring: a refused lock shows the warning and exits 0 BEFORE any
    backend/controller/sweep exists (no MainWindow, no sessions-root touch)."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from scribe_desktop import app as app_module

    warned: list[str] = []
    monkeypatch.setattr(
        app_module, "acquire_single_instance_lock", lambda name=None: (False, 0)
    )
    monkeypatch.setattr(
        app_module, "_show_already_running_warning", lambda: warned.append("warned")
    )
    # A QApplication may already exist in this pytest process; main()'s
    # unconditional QApplication([]) is only valid in a fresh app process.
    monkeypatch.setattr(
        app_module, "QApplication", lambda argv: QApplication.instance() or QApplication(argv)
    )
    # Guard proof: the refusal path must return before SoundDeviceBackend is
    # even constructed — poison it so any touch fails loudly.
    monkeypatch.setattr(
        app_module,
        "SoundDeviceBackend",
        lambda: (_ for _ in ()).throw(AssertionError("refused instance touched the backend")),
    )
    assert app_module.main() == 0
    assert warned == ["warned"]
