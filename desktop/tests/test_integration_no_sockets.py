"""Step 10: end-to-end integration through the REAL host exe + no-sockets proof.

Spawns the host exactly as Chrome does — the venv's `scribe-host.exe` with the
bare origin argv, no shell, CREATE_NO_WINDOW, and a foreign working directory
(Chrome cannot launch .bat hosts at all, so the exe IS the shipped path),
completes the full hello -> ping handshake over real pipes, asserts the first
stdout bytes are a valid length prefix (launcher stdout-purity), and polls the
FULL net_connections() list of the host — and a launched scribe-app — during
the exchange: both must stay completely empty (Critical Constraint: not just
no LISTEN entries, no connections at all).

Skipped automatically if Step 6's registration artifacts are absent
(e.g. a fresh clone before running scripts/register-native-host.py).
"""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import time
from pathlib import Path

import psutil
import pytest

from scribe_desktop.identity import EXPECTED_ORIGIN as ORIGIN
from scribe_desktop.identity import NONCE_HEX_LENGTH

REPO = Path(__file__).resolve().parents[2]
LAUNCHER = Path(sys.executable).parent / "scribe-host.exe"
CREATE_NO_WINDOW = 0x08000000  # Chrome spawns native hosts windowless

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="Windows-only launcher"),
    # LOW-015: skipping the no-sockets proof must be a deliberate, loud choice.
    pytest.mark.skipif(
        os.environ.get("SCRIBE_SKIP_INTEGRATION") == "1",
        reason="integration explicitly skipped via SCRIBE_SKIP_INTEGRATION=1",
    ),
]


@pytest.fixture(autouse=True)
def require_registration() -> None:
    if not LAUNCHER.exists():
        pytest.fail(
            "scribe-host.exe missing — run `pip install -e desktop` in this venv, "
            "or set SCRIBE_SKIP_INTEGRATION=1 to skip deliberately"
        )


def frame(value: dict) -> bytes:
    body = json.dumps(value).encode()
    return struct.pack("=I", len(body)) + body


def read_one_frame(stream) -> dict:
    prefix = stream.read(4)
    assert len(prefix) == 4, "stdout did not start with a full length prefix"
    (length,) = struct.unpack("=I", prefix)
    assert 0 < length <= 1_048_576, f"implausible first length prefix {length} — stdout impure?"
    body = stream.read(length)
    assert len(body) == length
    return json.loads(body.decode("utf-8"))


def assert_no_connections(proc: psutil.Process, label: str) -> None:
    conns = proc.net_connections(kind="all")
    assert conns == [], f"{label} has network connections: {conns}"


def test_full_handshake_via_launcher_with_no_sockets() -> None:
    host = subprocess.Popen(
        [str(LAUNCHER), ORIGIN, "--parent-window=0"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=os.environ.get("SystemRoot", "C:\\Windows"),  # Chrome uses an arbitrary cwd
        creationflags=CREATE_NO_WINDOW,
    )
    try:
        ps_host = psutil.Process(host.pid)
        assert host.stdin and host.stdout

        host.stdin.write(
            frame({"protocol_version": 1, "type": "hello", "request_id": "it-1", "payload": {}})
        )
        host.stdin.flush()
        ack = read_one_frame(host.stdout)
        assert ack["type"] == "hello_ack"
        nonce = ack["session_nonce"]
        assert len(nonce) == NONCE_HEX_LENGTH

        # Poll the whole process tree (the .bat wraps cmd -> python) mid-session.
        procs = [ps_host, *ps_host.children(recursive=True)]
        for _ in range(5):
            for proc in procs:
                if proc.is_running():
                    assert_no_connections(proc, f"host tree pid={proc.pid}")
            time.sleep(0.1)

        host.stdin.write(
            frame(
                {
                    "protocol_version": 1,
                    "type": "ping",
                    "request_id": "it-2",
                    "session_nonce": nonce,
                    "payload": {},
                }
            )
        )
        host.stdin.flush()
        pong = read_one_frame(host.stdout)
        assert pong["type"] == "pong"
        assert pong["session_nonce"] == nonce
        assert pong["request_id"] == "it-2"

        host.stdin.close()
        assert host.wait(timeout=15) == 0
    finally:
        if host.poll() is None:
            host.kill()


def test_scribe_app_process_has_no_sockets(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    code = (
        "from PySide6.QtWidgets import QApplication\n"
        "from scribe_desktop.app import StatusWindow\n"
        "import time\n"
        "app = QApplication([])\n"
        "w = StatusWindow()\n"
        "w.on_self_test()\n"
        "print('READY', flush=True)\n"
        "time.sleep(5)\n"
    )
    app = subprocess.Popen(
        [sys.executable, "-c", code],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
        cwd=str(REPO),
    )
    try:
        assert app.stdout
        assert app.stdout.readline().strip() == b"READY"
        ps_app = psutil.Process(app.pid)
        for _ in range(5):
            assert_no_connections(ps_app, "scribe-app")
            time.sleep(0.1)
    finally:
        app.kill()
