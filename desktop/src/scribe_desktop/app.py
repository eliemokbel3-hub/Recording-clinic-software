"""PySide6 desktop app (`scribe-app`) — Phase 2 Step 10.

The Phase-1 status window is now the Status tab of the multi-screen
main window (microphone / session / recovery / transcript-inspection).
Startup order (binding): offline kill-switches set AND asserted before
any ML code can run; then the 24-hour expiry sweep (Flow 3) before the
recovery screen lists anything; a periodic sweep keeps the cap enforced
while the app stays open.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from scribe_desktop.audio_capture import SoundDeviceBackend
from scribe_desktop.benchmark import apply_offline_env, assert_offline_env
from scribe_desktop.logging_setup import log_event, setup_logging
from scribe_desktop.session import SessionController
from scribe_desktop.session_store import default_sessions_root, sweep_sessions
from scribe_desktop.ui.main_window import MainWindow

# PR round 18 (PR8): 15-minute cadence bounds the worst-case overshoot of
# the 24 h cap to minutes, not an hour. The startup sweep runs immediately.
_SWEEP_INTERVAL_MS = 15 * 60 * 1000


def main() -> int:
    logger = setup_logging("scribe-app")
    # Offline kill-switches: set AND asserted before any ML code can run
    # (plan Design Decision "Runtime offline enforcement").
    apply_offline_env()
    assert_offline_env()
    log_event(logger, "app_start", state="starting")

    app = QApplication([])
    backend = SoundDeviceBackend()
    controller = SessionController(backend, logger=logger)
    sessions_root = default_sessions_root()

    def run_sweep(extra_protected: frozenset[str] = frozenset()) -> None:
        # Skips live sessions by STATE via active_session_ids (never mtime).
        sweep_sessions(
            sessions_root,
            active_session_ids=controller.active_session_ids() | extra_protected,
            logger=logger,
        )

    run_sweep()  # Flow 3: app start -> sweep BEFORE the recovery list renders
    window = MainWindow(controller, backend, sessions_root=sessions_root)

    sweep_timer = QTimer(window)
    sweep_timer.setInterval(_SWEEP_INTERVAL_MS)

    def periodic_sweep() -> None:
        # PR round 18 (PR2): a resume-processing run and a recovered session
        # awaiting Complete/Discard are protected from the sweep too — the
        # sweep must never destroy a store mid-recovery.
        run_sweep(window.recovery_screen.protected_session_ids())
        window.recovery_screen.refresh()

    sweep_timer.timeout.connect(periodic_sweep)
    sweep_timer.start()

    window.show()
    code = app.exec()
    log_event(logger, "app_exit", state="closed")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
