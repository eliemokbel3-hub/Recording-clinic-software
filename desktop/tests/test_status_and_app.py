"""Step 8: status/self-test logic tests + offscreen window smoke test."""

import os

import pytest

from scribe_desktop.status import read_registration_status, run_self_test


def test_registration_status_reads_real_machine_state() -> None:
    # Step 6 registered the host on this dev machine; the structure must be
    # coherent either way (informational only, never a security signal).
    status = read_registration_status()
    if status.registry_value is not None:
        assert status.manifest_exists
        assert status.launcher_exists
        assert status.registered


def test_self_test_passes_end_to_end() -> None:
    results = run_self_test()
    assert [r.name for r in results] == ["credential_store", "session_crypto"]
    assert all(r.passed for r in results), [f"{r.name}: {r.detail}" for r in results]


@pytest.mark.skipif(os.environ.get("SCRIBE_SKIP_GUI") == "1", reason="GUI smoke disabled")
def test_window_offscreen_smoke() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from scribe_desktop.app import StatusWindow

    app = QApplication.instance() or QApplication([])
    window = StatusWindow()
    assert "Registration:" in window.registration_label.text()
    window.on_self_test()
    assert "PASS" in window.self_test_label.text()
    assert "FAIL" not in window.self_test_label.text()
    window.close()
    del app
