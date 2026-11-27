"""``app.main`` gives the recording's backend to the controller and the level
meter's to the window (capture-overflow plan D1/D4; the review's MED finding
that nothing pinned which backend goes where)."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import pytest

from conftest import InertWarmup
from scribe_desktop.past_sessions import ExportRecovery


class _StopMain(Exception):
    pass


class _InertAudit:
    """Never the real audit root: prunes and records nothing."""

    def __init__(self, **kwargs: Any) -> None:
        pass

    def prune(self) -> int:
        return 0

    def record_deletion(self, *args: Any, **kwargs: Any) -> bool:
        return True

    def record_past_session(self, *args: Any, **kwargs: Any) -> bool:
        return True


class _InertPastSessions:
    """Never the real archive root: cleans, removes and commits nothing."""

    def __init__(self, **kwargs: Any) -> None:
        pass

    def recover_exports(self) -> ExportRecovery:
        return ExportRecovery()

    def clean_staging(self) -> int:
        return 0

    def remove_pending_entry(self, session_id: str) -> bool:
        return True

    def reconcile_pending(self, sessions_root: Path) -> list[str]:
        return []

    def entry_label(self, session_id: str) -> Any:
        return None

    def kept_entries(self) -> list[Any]:
        return []

    def deleted_recordings(self) -> list[Any]:
        return []

    def tidy_dead_recordings(self, *, cleared: frozenset[str] | None = None) -> int:
        return 0


class TestTheCaptureBackends:
    def test_the_recording_backend_goes_to_the_controller_and_the_meter_to_the_window(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        from scribe_desktop import app as app_module

        logger = logging.getLogger("test-app-capture-wiring")
        built: list[tuple[dict[str, Any], object]] = []

        def backend(**kwargs: Any) -> object:
            sentinel = object()
            built.append((kwargs, sentinel))
            return sentinel

        received: dict[str, Any] = {}

        class FakeController:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                received["controller"] = (args, kwargs)

            def custody_protected_ids(self) -> frozenset[str]:
                return frozenset()

            def set_clinic_user_resolver(self, resolver: Any) -> None:
                pass

        class FakeWindow:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                received["window"] = (args, kwargs)

            def clinic_user_id(self, clinic_id: str) -> str | None:
                return None

            def reconstruct_reminders(self) -> None:
                raise _StopMain()

        for name, value in {
            "setup_logging": lambda name: logger,
            # Never this process's hooks or the real Windows layer.
            "install_exception_hooks": lambda logger: lambda: None,
            "Win32WindowsLayer": lambda: None,
            "startup_exclusions": lambda *args, **kwargs: (),
            "apply_offline_env": lambda: None,
            "assert_offline_env": lambda: None,
            "QApplication": lambda argv: QApplication.instance() or QApplication(argv),
            "acquire_instance_exclusion": lambda name=None, lock_path=None: (
                app_module.InstanceExclusion("acquired")
            ),
            "SoundDeviceBackend": backend,
            "ImportWarmup": InertWarmup,  # no warm-up thread
            "AuditLog": _InertAudit,
            "PastSessionStore": _InertPastSessions,
            "SessionController": FakeController,
            "default_sessions_root": lambda: tmp_path / "sessions",
            "sweep_sessions": lambda *args, **kwargs: [],
            "MainWindow": FakeWindow,
        }.items():
            monkeypatch.setattr(app_module, name, value)
        with pytest.raises(_StopMain):
            app_module.main()
        assert len(built) == 2
        recording = [sentinel for kwargs, sentinel in built if kwargs == {"logger": logger}]
        meter = [sentinel for kwargs, sentinel in built if kwargs == {"input_latency": None}]
        assert len(recording) == 1 and len(meter) == 1
        controller_args, _controller_kwargs = received["controller"]
        window_args, _window_kwargs = received["window"]
        assert controller_args[0] is recording[0]
        assert window_args[1] is meter[0]
