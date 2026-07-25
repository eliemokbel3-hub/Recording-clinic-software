"""Step 8: status/self-test logic tests + offscreen window smoke test."""

import os

import pytest

from scribe_desktop.status import read_registration_status, run_self_test


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
