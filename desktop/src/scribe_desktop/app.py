"""PySide6 status window (`scribe-app`) — plan Step 8 (minimal by design).

Shows host-registration state (informational only) and a self-test button
running the Flow 2 storage round-trip. NO host<->UI live-state plumbing in
Phase 1 (plan Excluded); connection state is proven by the extension badge.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scribe_desktop.logging_setup import log_event, setup_logging
from scribe_desktop.protocol import HOST_NAME
from scribe_desktop.status import read_registration_status, run_self_test


class StatusWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Cliniko Scribe — Phase 1")
        self.registration_label = QLabel()
        self.self_test_label = QLabel("Self-test: not run")
        self.self_test_button = QPushButton("Run self-test")
        self.self_test_button.clicked.connect(self.on_self_test)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Native host: {HOST_NAME}"))
        layout.addWidget(self.registration_label)
        layout.addWidget(self.self_test_button)
        layout.addWidget(self.self_test_label)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.refresh_registration()

    def refresh_registration(self) -> None:
        status = read_registration_status()
        if status.registered:
            text = "registered ✓"
        else:
            text = "NOT registered — run scripts/register-native-host.py"
        self.registration_label.setText(f"Registration: {text}")

    def on_self_test(self) -> None:
        results = run_self_test()
        lines = [f"{r.name}: {'PASS' if r.passed else 'FAIL'} ({r.detail})" for r in results]
        self.self_test_label.setText("Self-test:\n" + "\n".join(lines))


def main() -> int:
    logger = setup_logging("scribe-app")
    log_event(logger, "app_start", state="starting")
    app = QApplication([])
    window = StatusWindow()
    window.show()
    code = app.exec()
    log_event(logger, "app_exit", state="closed")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
