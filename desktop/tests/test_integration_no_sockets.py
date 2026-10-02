"""Steps 10 + 13: end-to-end integration through REAL processes + the
no-socket proof for every path that must stay offline.

Scope since the Cliniko workflow safeguards plan (D9, Task 1.2): the app's
offline contract is "no connection except Cliniko's API, and none at startup
or idle". Every leg here covers a path that must open NO connection at all —
the host, the app's startup and idle, the app with the Chrome link's named
pipe open and a client connected (Tasks 4.2 + 4.5), the host relaying to an
open app pipe (Task 4.4), capture, transcription, prose — and
asserts exactly zero, with no allow-list. The Cliniko client
(``cliniko_client.py``, the one network-capable module) has no caller on any
of these paths; its own tests (``test_cliniko_client.py``) inject a fake
transport and never open a socket.

Step 10 legacy coverage (kept):
- the venv's `scribe-host.exe` spawned exactly as Chrome does, full
  hello -> ping handshake, stdout-purity check, and a FULL
  ``net_connections()`` poll of the host tree mid-session;
- a launched scribe-app (offscreen MainWindow startup path) polled for
  sockets while idle.

Step 13 extends the proof to the RECORDER UNDER LOAD (plan: the no-sockets
test covers the recorder mid-capture and mid-transcription):
- a real recorder process is polled with FULL ``net_connections()`` while
  chunks are streaming through the encrypt-append path AND while the
  transcription pipeline is in flight (phase-gated over stdin/stdout, so
  every poll provably lands inside the claimed phase); the offline env
  kill-switches are applied AND asserted inside every child before any ML
  import (mirroring app startup);
- the same poll runs against the REAL local ML stack (silero VAD + the
  RESOLVED faster-whisper model: `medium` default, `small` fallback —
  Step 13 policy), including the model-load window where any
  download/telemetry attempt would occur (skip-if-absent for CI);
- a crash-sim runs END-TO-END: hard-kill mid-recording, then a fresh
  process recovers the session (DPAPI unwrap), re-transcribes the durable
  chunks, verifies the transcript decrypts, and drives the binding
  Complete custody ordering (verify -> delete key);
- transcription must SUCCEED with the Python socket layer stubbed to fail
  before any ML import (plan: Runtime offline enforcement — env
  kill-switches are the primary control; the stub proves behaviour when
  the Python network stack is hard-down);
- (note-learning plan Task 1.5) the LIVE path: a recorder whose live worker
  transcribes windows during capture is polled across that work, its
  processing callable drains the worker without building a batch model,
  and Complete follows; the crash-sim also runs with a live worker attached
  at the kill, recovering through the unchanged batch path. The live leg is
  mock-ML by design: the worker drives the SAME provider class the real-ML
  leg already proves socketless, so a second real-ML leg would only re-run
  that proof;
- (note-learning plan Task 4.4, D8) the PROSE runtime: `llama-cpp-python`
  reads no offline kill-switch, so THESE legs are its enforcing offline
  control, with different coverage each — the mock leg (always) proves the
  stage's ORCHESTRATION opens no socket while the process is inside a model
  call (no native code runs there); the real leg proves the RUNTIME across
  the real model's load + one generation once the hashed wheel and the
  pinned GGUF are present (skip-by-name otherwise, so that evidence is
  conditional).

Honest limits, recorded deliberately: polling samples the OS socket table,
so a sufficiently short-lived connection could in principle dodge a poll
tick (why env enforcement is primary); the Python-level socket stub cannot
intercept NATIVE socket use inside onnxruntime/ctranslate2 — the OS-level
polls (which do see native sockets) and the user's independent network
monitor at the manual completion gate cover that layer.

Skipped automatically if Step 6's registration artifacts are absent
(e.g. a fresh clone before running scripts/register-native-host.py).
"""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import IO, Any, NamedTuple

import psutil
import pytest

from conftest import on_real_ml_root, real_ml_skip_reason
from scribe_desktop.benchmark import apply_offline_env
from scribe_desktop.identity import NONCE_HEX_LENGTH, expected_origin, pipe_prefix
from scribe_desktop.protocol import PROTOCOL_VERSION
from scribe_desktop.session_store import (
    AUDIO_FILENAME,
    KEY_FILENAME,
    complete_session,
    store_has_footer,
    sweep_sessions,
)
from scribe_desktop.speech import MockSpeechProvider
from scribe_desktop.transcription import (
    read_transcript,
    recover_session_transcription,
)
from scribe_desktop.ui.models import models_ready

REPO = Path(__file__).resolve().parents[2]
TESTS_DIR = Path(__file__).resolve().parent
LAUNCHER = Path(sys.executable).parent / "scribe-host.exe"
# Installation plan D2: the launcher's host is a real source run, so it is
# the DEV channel — it accepts only the dev extension's origin and relays to
# the dev app's pipe (this process's channel is pinned to production).
ORIGIN = expected_origin("dev")
CREATE_NO_WINDOW = 0x08000000  # Chrome spawns native hosts windowless

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="Windows-only launcher"),
    # LOW-015: skipping the no-sockets proof must be a deliberate, loud choice.
    pytest.mark.skipif(
        os.environ.get("SCRIBE_SKIP_INTEGRATION") == "1",
        reason="integration explicitly skipped via SCRIBE_SKIP_INTEGRATION=1",
    ),
]

# Real-ML legs are skip-if-absent for CI (plan: model files never live on
# runners); everything else in this module runs everywhere on Windows.
# The gate IS production readiness (round 42 LOW-013: `models_ready` is
# the same VAD+resolved-whisper check the app's report uses — the gate
# can no longer drift from production model resolution).
# Installation plan Task 2.6: the gate looks in the source run's DEV models
# root — the root the real-ML children load from (each pins it after its
# channel pin) — never the production data folder (C8).
requires_ml_models = pytest.mark.skipif(
    not on_real_ml_root(models_ready),
    reason=real_ml_skip_reason("local silero + whisper models"),
)


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


class _ChildTree(NamedTuple):
    """A spawned child as the socket polls must see it.

    Round 70 (leg stage-9-exec-k16, docs/lessons.md): a child started with
    ``sys.executable`` is the venv's LAUNCHER, and the interpreter that runs
    the child's code — the process that would hold a socket — is the
    launcher's own child. ``root`` is the ``Popen`` process; ``interpreter_pid``
    is the process that runs the code, as the child itself reported it (or,
    for the entry-point host, the one leaf of its launcher chain)."""

    root: psutil.Process
    interpreter_pid: int


def assert_no_connections(tree: _ChildTree, label: str) -> None:
    """A MANDATORY poll: no connection in the root or ANY descendant, and the
    interpreter must be among them and actually inspected (round 71
    PR-LOW-390: a launcher-only sample is never a pass). A descendant other
    than the interpreter that exits mid-walk holds no socket and is skipped;
    the root vanishing raises ``psutil.NoSuchProcess``."""
    members = [tree.root, *tree.root.children(recursive=True)]
    inspected = False
    for member in members:
        try:
            conns = member.net_connections(kind="all")
        except psutil.NoSuchProcess:
            if member is tree.root:
                raise
            if member.pid == tree.interpreter_pid:
                raise AssertionError(
                    f"{label}: the interpreter (pid={tree.interpreter_pid}) exited mid-poll"
                ) from None
            continue
        assert conns == [], f"{label} (pid={member.pid}) has network connections: {conns}"
        if member.pid == tree.interpreter_pid:
            inspected = True
    assert inspected, (
        f"{label}: the interpreter (pid={tree.interpreter_pid}) is not in the process tree "
        f"{[m.pid for m in members]} - the poll would have checked only the launcher"
    )


def _sample_after_exit(tree: _ChildTree, label: str) -> None:
    """An OPTIONAL sample once the child was released to finish: whatever is
    still alive holds no connection, and an exited process (the root
    included) is skipped. Never a substitute for the mandatory polls."""
    try:
        members = [tree.root, *tree.root.children(recursive=True)]
    except psutil.NoSuchProcess:
        return
    for member in members:
        try:
            conns = member.net_connections(kind="all")
        except psutil.NoSuchProcess:
            continue
        assert conns == [], f"{label} (pid={member.pid}) has network connections: {conns}"


def _reported_tree(popen: subprocess.Popen[bytes], line: bytes, marker: bytes) -> _ChildTree:
    """The tree for a child whose readiness line is ``<marker> <pid> …``."""
    words = line.split()
    assert words[:1] == [marker] and len(words) >= 2, line
    return _ChildTree(psutil.Process(popen.pid), int(words[1]))


def _leaf_interpreter(root: psutil.Process) -> int:
    """The entry-point host (``scribe-host.exe``) cannot report its pid on
    stdout (that is the framed channel): its interpreter is the one Python
    leaf of its launcher chain. (A windowless console child may also own a
    hidden ``conhost.exe``, which runs none of our code.)"""
    def is_python(process: psutil.Process) -> bool:
        return process.name().lower().startswith("python")

    leaves = [
        p
        for p in root.children(recursive=True)
        if is_python(p) and not any(is_python(c) for c in p.children())
    ]
    assert len(leaves) == 1, f"expected one interpreter under the launcher, got {leaves}"
    return leaves[0].pid


def _read_line_within(stream: IO[bytes], seconds: float) -> bytes:
    """One line from ``stream``, or b"" if none arrives in ``seconds``."""
    lines: list[bytes] = []
    reader = threading.Thread(target=lambda: lines.append(stream.readline()), daemon=True)
    reader.start()
    reader.join(seconds)
    return lines[0] if lines else b""


def _amplitude_vad(frame_bytes: bytes) -> float:
    """Deterministic ML-free VAD stand-in (mirrors test_transcription)."""
    samples = struct.unpack(f"<{len(frame_bytes) // 2}h", frame_bytes)
    return 0.95 if max(abs(s) for s in samples) > 1000 else 0.02


# ---------------------------------------------------------------------------
# Step 10 tests (host handshake + idle app), unchanged in intent.
# ---------------------------------------------------------------------------


def _real_app_pipe_exists() -> bool:
    """Whether a scribe-app is listening on THIS user's real pipe (Task 4.4):
    the launcher leg's host relays to that name, so it must never reach a
    practitioner's running app (it would count as a new Chrome connection)."""
    import pywintypes
    import win32pipe

    from scribe_desktop.pipe_server import current_user_sid

    try:
        win32pipe.WaitNamedPipe(f"{pipe_prefix('dev')}{current_user_sid()}", 1)
    except pywintypes.error as error:
        return error.winerror != 2  # ERROR_FILE_NOT_FOUND: no app
    return True


def test_full_handshake_via_launcher_with_no_sockets(tmp_path: Path) -> None:
    # The skip is checked once, before the launch: an app started in between
    # would still see this host connect (the pipe name is the user's SID and
    # cannot be redirected) — run this leg with scribe-app closed.
    if _real_app_pipe_exists():
        pytest.skip("scribe-app is running on this host: close it to run the launcher leg")
    host = subprocess.Popen(
        [str(LAUNCHER), ORIGIN, "--parent-window=0"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=os.environ.get("SystemRoot", "C:\\Windows"),  # Chrome uses an arbitrary cwd
        # Round 57 SEC-012: the host logs under a test folder, never into the
        # practitioner's real scribe-host.log (an incident-process signal).
        env={**os.environ, "LOCALAPPDATA": str(tmp_path)},
        creationflags=CREATE_NO_WINDOW,
    )
    try:
        ps_host = psutil.Process(host.pid)
        assert host.stdin and host.stdout

        host.stdin.write(
            frame(
                {
                    "protocol_version": PROTOCOL_VERSION,
                    "type": "hello",
                    "request_id": "it-1",
                    "payload": {},
                }
            )
        )
        host.stdin.flush()
        ack = read_one_frame(host.stdout)
        assert ack["type"] == "hello_ack"
        nonce = ack["session_nonce"]
        assert len(nonce) == NONCE_HEX_LENGTH
        # Task 4.4: with no app, the relay says so once, stamped, and waits on.
        not_running = read_one_frame(host.stdout)
        assert not_running["type"] == "state", not_running["type"]
        assert not_running["session_nonce"] == nonce
        assert not_running["payload"]["app_running"] is False

        # Poll the whole process tree mid-session: the host stays alive until
        # its stdin closes below, and its interpreter must be inspected.
        host_tree = _ChildTree(ps_host, _leaf_interpreter(ps_host))
        for _ in range(5):
            assert_no_connections(host_tree, "host tree")
            time.sleep(0.1)

        host.stdin.write(
            frame(
                {
                    "protocol_version": PROTOCOL_VERSION,
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
            host.wait(timeout=15)  # PR round 31: reap uniformly


def test_scribe_app_process_has_no_sockets(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    code = (
        # Step 13: mirror app.main() startup order — offline kill-switches
        # set AND asserted before any ML/UI code runs.
        "from scribe_desktop.benchmark import apply_offline_env, assert_offline_env\n"
        "apply_offline_env()\n"
        "assert_offline_env()\n"
        "from PySide6.QtWidgets import QApplication\n"
        "from scribe_desktop.audio_capture import MockCaptureBackend\n"
        "from scribe_desktop.session import SessionController\n"
        "from scribe_desktop.clinics import ClinicRegistry\n"
        "from scribe_desktop.ui.main_window import MainWindow\n"
        "from scribe_desktop.audit import AuditLog\n"
        "from scribe_desktop.app import record_sweep_results, sweep_with_archive\n"
        "from scribe_desktop.past_sessions import PastSessionStore\n"
        "import tempfile, time\n"
        "from pathlib import Path\n"
        # Privacy-professional-controls Task 4.1: the exception hooks before the
        # QApplication and every store. app.main installs them right after
        # logging, ahead of the offline env; the child sets that env first
        # (Step 13 above) — the order changes no socket use (H1 round 32
        # LOW-006).
        "import logging, os\n"
        "from scribe_desktop.exclusions import install_exception_hooks, startup_exclusions\n"
        "install_exception_hooks(logging.getLogger('no-sockets-child'))\n"
        "app = QApplication([])\n"
        # Peer round 55 PR-LOW-041: every store root under the temp parent, so
        # the child never unwraps the developer's real profile or reads their
        # real config (the PR-REG-005 class). The clinic registry keeps its
        # REAL transport (Cliniko safeguards Task 2.2): the Clinics tab is
        # built, and startup + idle must still open no connection.
        "base = Path(tempfile.mkdtemp())\n"
        "root = base / 'sessions'\n"
        "backend = MockCaptureBackend()\n"
        # Privacy-professional-controls Task 1.3: the new start-up work — the
        # audit log (its root redirected too), its month prune, the sweep's
        # results recorded, and the clinic-user resolver.
        "audit = AuditLog(base / 'audit')\n"
        # Task 2.3: the Past-sessions archive (its root redirected too), and
        # the sweep with its staging clean-up, C1 hook and reconciliation.
        "past = PastSessionStore(base / 'past_sessions')\n"
        "controller = SessionController(backend, sessions_root=root, audit=audit,\n"
        "                               past_sessions=past)\n"
        "audit.prune()\n"
        "record_sweep_results(audit, sweep_with_archive(root, past, frozenset(), audit=audit))\n"
        # Task 4.1 (Flow 6): the start-up exclusion work before the window,
        # under the socket guard — through a FAKE Windows layer over the temp
        # parent (C6: the child never reads the real registry or environment,
        # and sets no real file attribute).
        "class FakeLayer:\n"
        "    def environ(self, name):\n"
        "        return str(base) if name in ('LOCALAPPDATA', 'USERPROFILE') else None\n"
        "    def realpath(self, path):\n"
        "        return os.path.realpath(path)\n"
        "    def drive_type(self, root):\n"
        "        return 3\n"
        "    def file_attributes(self, path):\n"
        "        return 0\n"
        "    def set_file_attributes(self, path, attributes):\n"
        "        return True\n"
        "    def wer_exclusions(self, hive='HKCU'):\n"
        "        return {}\n"
        "    def backup_exclusions(self):\n"
        "        return {}\n"
        "    def native_host_entries(self, key):\n"
        "        return ()\n"
        "warnings = startup_exclusions(FakeLayer(), executable='pythonw.exe',\n"
        "                              logger=logging.getLogger('no-sockets-child'), root=base)\n"
        "w = MainWindow(controller, backend, sessions_root=root,\n"
        "               profile_root=base / 'profile', config_root=base / 'config',\n"
        "               style_root=base / 'style', language_model_available=lambda: False,\n"
        "               clinic_registry=ClinicRegistry(base / 'clinics.json'), audit=audit,\n"
        "               past_sessions=past, exclusion_warnings=warnings)\n"
        "controller.set_clinic_user_resolver(w.clinic_user_id)\n"
        # As app.main: the reminder index rebuilt after the sweep (Cliniko
        # safeguards Task 5.5; nothing to decrypt under the empty root).
        "w.reconstruct_reminders()\n"
        # Task 3.2: the start-up retention sweep through the Past sessions
        # tab, and the tab listed as opening it would (Task 3.1).
        "w.past_sessions_screen.run_retention_sweep()\n"
        "w.past_sessions_screen.refresh()\n"
        "w.status_panel.on_self_test()\n"
        # Round 71 PR-LOW-390: report the interpreter's own pid, then stay up
        # until the parent releases the gate (stdin), not on a timer.
        "import os, sys\n"
        "print('READY', os.getpid(), flush=True)\n"
        "sys.stdin.readline()\n"
    )
    app = subprocess.Popen(
        [sys.executable, "-c", code],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
        cwd=str(REPO),
    )
    try:
        assert app.stdout
        app_tree = _reported_tree(app, _read_line_within(app.stdout, 60), b"READY")
        for _ in range(5):
            assert_no_connections(app_tree, "scribe-app")
            time.sleep(0.1)
    finally:  # the gate never opens on its own: the kill is the release
        app.kill()
        app.wait(timeout=15)  # PR round 31: reap uniformly


# Cliniko workflow safeguards Tasks 4.2 + 4.5: the app with the Chrome link
# OPEN — the named pipe listening, a client connected, a report in and the
# state snapshot out. The pipe name is unique to the child (never the real
# per-user name), the registry is empty (the report's host is not on the
# allow-list, so no Cliniko check is due), and the process must hold no
# socket while the pipe is connected: a named pipe is not a network endpoint.
_PIPE_APP_CHILD = """\
import json, struct, tempfile, threading, time, uuid
from pathlib import Path
from scribe_desktop.benchmark import apply_offline_env, assert_offline_env
apply_offline_env()
assert_offline_env()
import win32con, win32file
from PySide6.QtWidgets import QApplication
from scribe_desktop.audio_capture import MockCaptureBackend
from scribe_desktop.clinics import ClinicRegistry
from scribe_desktop.pipe_server import PipeServer, current_user_sid, pipe_sddl
from scribe_desktop.past_sessions import PastSessionStore
from scribe_desktop.protocol import PROTOCOL_VERSION
from scribe_desktop.session import SessionController
from scribe_desktop.ui.main_window import MainWindow
app = QApplication([])
base = Path(tempfile.mkdtemp())
root = base / 'sessions'
backend = MockCaptureBackend()
controller = SessionController(backend, sessions_root=root)
w = MainWindow(controller, backend, sessions_root=root,
               profile_root=base / 'profile', config_root=base / 'config',
               style_root=base / 'style', language_model_available=lambda: False,
               clinic_registry=ClinicRegistry(base / 'clinics.json'),
               past_sessions=PastSessionStore(base / 'past_sessions'))
bridge = w.attach_chrome_link()
name = '\\\\\\\\.\\\\pipe\\\\ClinikoScribe-test-' + uuid.uuid4().hex
server = PipeServer(name, bridge, sddl=pipe_sddl(current_user_sid()))
bridge.attach(server)
server.start()
frames = []
handles = []
def client():
    h = win32file.CreateFile(name, win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                             0, None, win32con.OPEN_EXISTING, 0, None)
    handles.append(h)
    body = json.dumps({'protocol_version': PROTOCOL_VERSION, 'type': 'context',
                       'payload': {'seq': 1, 'tab_id': 7, 'window_id': 1, 'focused': True,
                                   'page': 'note', 'host': 'example-clinic.au1.cliniko.com',
                                   'patient_id': '1001', 'note_id': '2002'}}).encode()
    win32file.WriteFile(h, struct.pack('=I', len(body)) + body)
    def read(n):
        data = b''
        while len(data) < n:
            _, chunk = win32file.ReadFile(h, n - len(data))
            data += chunk
        return data
    # The writer is latest-wins: the snapshot on connect may be superseded by
    # the one after the report, so read until that one arrives.
    while not frames or frames[-1]['payload'].get('notice') != 'clinic_not_set_up':
        (length,) = struct.unpack('=I', read(4))
        frames.append(json.loads(read(length)))
threading.Thread(target=client, daemon=True).start()
deadline = time.monotonic() + 20
while not frames or frames[-1]['payload'].get('notice') != 'clinic_not_set_up':
    if time.monotonic() > deadline:
        break
    app.processEvents()
    time.sleep(0.01)
last = frames[-1] if frames else {'type': 'none', 'payload': {}}
# Round 71 PR-LOW-390: the interpreter's own pid, then up until the parent's
# gate (a line on stdin) opens; 120 s is only a safety cap.
import os, sys
released = threading.Event()
threading.Thread(target=lambda: (sys.stdin.readline(), released.set()), daemon=True).start()
print('READY', os.getpid(), last['type'] + ':' + str(last['payload'].get('notice')), flush=True)
end = time.monotonic() + 120
while not released.is_set() and time.monotonic() < end:
    app.processEvents()
    time.sleep(0.02)
"""


def test_scribe_app_with_the_chrome_link_open_has_no_sockets(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    script = tmp_path / "pipe_app_child.py"
    script.write_text(_PIPE_APP_CHILD, encoding="utf-8")
    app = subprocess.Popen(
        [sys.executable, str(script)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
        cwd=str(REPO),
    )
    try:
        assert app.stdout
        line = _read_line_within(app.stdout, 90)
        assert line.split()[2:] == [b"state:clinic_not_set_up"], line
        app_tree = _reported_tree(app, line, b"READY")
        for _ in range(5):  # the pipe client is still connected here
            assert_no_connections(app_tree, "scribe-app with the Chrome link open")
            time.sleep(0.1)
    finally:  # the gate never opens on its own: the kill is the release
        app.kill()
        app.wait(timeout=15)


# Task 4.4: the whole relay, process to process — a real app (the bridge on a
# unique pipe name) and a real host process relaying to it, both polled with
# the host mid-session. The report's host is not on the (empty) allow-list,
# so no Cliniko check is due.
_APP_SERVER_CHILD = """\
import sys, tempfile, time
from pathlib import Path
from scribe_desktop.benchmark import apply_offline_env, assert_offline_env
apply_offline_env()
assert_offline_env()
from PySide6.QtWidgets import QApplication
from scribe_desktop.audio_capture import MockCaptureBackend
from scribe_desktop.clinics import ClinicRegistry
from scribe_desktop.past_sessions import PastSessionStore
from scribe_desktop.pipe_server import PipeServer, current_user_sid, pipe_sddl
from scribe_desktop.session import SessionController
from scribe_desktop.ui.main_window import MainWindow
app = QApplication([])
base = Path(tempfile.mkdtemp())
root = base / 'sessions'
backend = MockCaptureBackend()
controller = SessionController(backend, sessions_root=root)
w = MainWindow(controller, backend, sessions_root=root,
               profile_root=base / 'profile', config_root=base / 'config',
               style_root=base / 'style', language_model_available=lambda: False,
               clinic_registry=ClinicRegistry(base / 'clinics.json'),
               past_sessions=PastSessionStore(base / 'past_sessions'))
bridge = w.attach_chrome_link()
server = PipeServer(sys.argv[1], bridge, sddl=pipe_sddl(current_user_sid()))
bridge.attach(server)
server.start()
# Round 71 PR-LOW-390: the interpreter's own pid, then up until the parent's
# gate (a line on stdin) opens; 120 s is only a safety cap.
import os, threading
released = threading.Event()
threading.Thread(target=lambda: (sys.stdin.readline(), released.set()), daemon=True).start()
print('READY', os.getpid(), flush=True)
end = time.monotonic() + 120
while not released.is_set() and time.monotonic() < end:
    app.processEvents()
    time.sleep(0.01)
"""

# stdout is the framed channel, so the interpreter's pid goes to stderr.
_HOST_RELAY_CHILD = """\
import logging, os, sys
sys.stderr.write('PID %d\\n' % os.getpid())
sys.stderr.flush()
from scribe_desktop.framing import set_binary_stdio
from scribe_desktop.native_host import app_relay_factory, run_host
set_binary_stdio()
logger = logging.getLogger('host-relay-child')
logger.addHandler(logging.NullHandler())
logger.propagate = False
sys.exit(run_host(sys.stdin.buffer, sys.stdout.buffer, logger,
                  relay_factory=app_relay_factory(sys.argv[1])))
"""


def _read_state_until(
    stream: IO[bytes], predicate: Callable[[dict[str, Any]], bool], limit: int = 20
) -> dict[str, Any]:
    for _ in range(limit):
        message = read_one_frame(stream)
        assert message["type"] == "state", message["type"]
        if predicate(message):
            return message
    raise AssertionError("the expected state never arrived")


def test_host_relays_to_an_open_app_pipe_with_no_sockets(tmp_path: Path) -> None:
    import uuid

    pipe = f"\\\\.\\pipe\\ClinikoScribe-test-{uuid.uuid4().hex}"
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    app_script = tmp_path / "app_server_child.py"
    app_script.write_text(_APP_SERVER_CHILD, encoding="utf-8")
    host_script = tmp_path / "host_relay_child.py"
    host_script.write_text(_HOST_RELAY_CHILD, encoding="utf-8")
    app = subprocess.Popen(
        [sys.executable, str(app_script), pipe],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
        cwd=str(REPO),
    )
    host: subprocess.Popen[bytes] | None = None
    try:
        assert app.stdout
        app_tree = _reported_tree(app, _read_line_within(app.stdout, 90), b"READY")
        host = subprocess.Popen(
            [sys.executable, str(host_script), pipe],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(REPO),
            creationflags=CREATE_NO_WINDOW,
        )
        assert host.stdin and host.stdout and host.stderr
        host_tree = _reported_tree(host, _read_line_within(host.stderr, 60), b"PID")
        host.stdin.write(
            frame(
                {
                    "protocol_version": PROTOCOL_VERSION,
                    "type": "hello",
                    "request_id": "it-1",
                    "payload": {},
                }
            )
        )
        host.stdin.flush()
        ack = read_one_frame(host.stdout)
        assert ack["type"] == "hello_ack"
        nonce = ack["session_nonce"]
        # The app's snapshot on connect, relayed with this session's nonce.
        first = _read_state_until(host.stdout, lambda m: m["payload"]["app_running"] is True)
        assert first["session_nonce"] == nonce
        host.stdin.write(
            frame(
                {
                    "protocol_version": PROTOCOL_VERSION,
                    "type": "context",
                    "session_nonce": nonce,
                    "payload": {
                        "seq": 1,
                        "tab_id": 7,
                        "window_id": 1,
                        "focused": True,
                        "page": "note",
                        "host": "example-clinic.au1.cliniko.com",
                        "patient_id": "1001",
                        "note_id": "2002",
                    },
                }
            )
        )
        host.stdin.flush()
        # The report reached the app, and its answer came back through the host.
        answer = _read_state_until(
            host.stdout, lambda m: m["payload"].get("notice") == "clinic_not_set_up"
        )
        assert answer["session_nonce"] == nonce
        # The app is gated on stdin and the host lives until its stdin closes.
        for tree, name in ((app_tree, "app"), (host_tree, "host")):
            for _ in range(5):
                assert_no_connections(tree, f"relay leg {name}")
                time.sleep(0.05)
        host.stdin.close()
        assert host.wait(timeout=15) == 0
    finally:
        if host is not None and host.poll() is None:
            host.kill()
            host.wait(timeout=15)
        app.kill()
        app.wait(timeout=15)


# ---------------------------------------------------------------------------
# Step 13 harness: phase-gated recorder children + parent-side helpers.
#
# Child scripts are written to tmp_path and run in the venv python. They are
# deliberately data, not linted test modules: the offline-stub child must
# import `socket`, which the desktop ruff banned-api list forbids in linted
# code — the ban protects runtime code; these children exist to PROVE the
# runtime behaves without a network.
# ---------------------------------------------------------------------------


class _PipeReader(threading.Thread):
    """Collects child stdout lines so the main thread can poll the OS socket
    table while waiting for phase markers (never blocked on readline)."""

    def __init__(self, stream: IO[bytes]) -> None:
        super().__init__(daemon=True)
        self._stream = stream
        self._cond = threading.Condition()
        self.lines: list[str] = []
        self.eof = False

    def run(self) -> None:
        for raw in self._stream:
            with self._cond:
                self.lines.append(raw.decode("utf-8", "replace").strip())
                self._cond.notify_all()
        with self._cond:
            self.eof = True
            self._cond.notify_all()

    def find(self, prefix: str) -> str | None:
        with self._cond:
            for line in self.lines:
                if line.startswith(prefix):
                    return line
        return None

    def wait_for(self, prefix: str, timeout: float) -> str | None:
        deadline = time.monotonic() + timeout
        with self._cond:
            while True:
                for line in self.lines:
                    if line.startswith(prefix):
                        return line
                if self.eof:
                    return None
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._cond.wait(remaining)


def _child_failure(msg: str, reader: _PipeReader, stderr_path: Path) -> AssertionError:
    stderr_text = ""
    if stderr_path.exists():
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    return AssertionError(
        f"{msg}\nchild stdout lines: {reader.lines!r}\nchild stderr:\n{stderr_text}"
    )


def _await_marker(
    reader: _PipeReader,
    proc: subprocess.Popen[bytes],
    stderr_path: Path,
    prefix: str,
    timeout: float,
) -> str:
    line = reader.wait_for(prefix, timeout)
    if line is None:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=15)
        raise _child_failure(f"child never printed {prefix!r}", reader, stderr_path)
    return line


def _child_tree(
    proc: subprocess.Popen[bytes], reader: _PipeReader, stderr_path: Path
) -> _ChildTree:
    """The tree of a ``_write_child`` child: its prelude's first line is
    ``PID <the interpreter's own pid>`` (round 71 PR-LOW-390)."""
    line = _await_marker(reader, proc, stderr_path, "PID ", 60)
    return _ChildTree(psutil.Process(proc.pid), int(line.split()[1]))


def _poll_no_connections(
    proc: subprocess.Popen[bytes],
    ps: _ChildTree,
    reader: _PipeReader,
    stderr_path: Path,
    label: str,
    *,
    polls: int,
    interval: float = 0.05,
) -> None:
    for _ in range(polls):
        if proc.poll() is not None:
            raise _child_failure(f"child exited during {label}", reader, stderr_path)
        assert_no_connections(ps, label)
        time.sleep(interval)


def _write_child(tmp_path: Path, name: str, code: str) -> Path:
    # Children run from a temp dir with cwd=REPO, so the tests directory is not
    # importable by default; adding it lets them share `sapi_fixture` (the
    # SAPI-renders-22050 Hz correction must exist in exactly ONE place, not
    # re-copied into every child). Stdlib statements only, no imports of our own
    # — the socket-stub child still stubs before anything else loads.
    # SEC-001: APPEND, never insert(0, ...). At position 0 the tests directory
    # would precede the stdlib, so a future tests/socket.py or _socket.py would
    # be what the no-network-proof child imports and stubs — the proof would go
    # green while testing nothing. Appending resolves `sapi_fixture` (no other
    # source provides that name) and leaves stdlib resolution untouched.
    # Round 71 PR-LOW-390: the first line reports the interpreter's OWN pid
    # (the venv's python.exe is a launcher; its child runs this code), which
    # every mandatory socket poll must find and inspect. `os` is already
    # loaded by interpreter start-up and opens nothing.
    prelude = (
        f"import os, sys\nsys.path.append({str(TESTS_DIR)!r})\n"
        "print('PID %d' % os.getpid(), flush=True)\n"
    )
    script = tmp_path / name
    script.write_text(prelude + code, encoding="utf-8")
    return script


def _spawn_child(
    script: Path,
    sessions_root: Path,
    stderr_path: Path,
    extra_args: tuple[str, ...] = (),
) -> tuple[subprocess.Popen[bytes], _PipeReader]:
    with stderr_path.open("wb") as stderr:
        proc = subprocess.Popen(
            [sys.executable, str(script), str(sessions_root), *extra_args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr,
            cwd=str(REPO),
        )
    assert proc.stdout is not None  # PIPE requested above
    reader = _PipeReader(proc.stdout)
    reader.start()
    return proc, reader


def _send(
    proc: subprocess.Popen[bytes],
    reader: _PipeReader,
    stderr_path: Path,
    command: bytes,
) -> None:
    assert proc.stdin is not None
    try:
        proc.stdin.write(command + b"\n")
        proc.stdin.flush()
    except OSError as exc:  # child died inside the gate race window
        raise _child_failure(
            f"child pipe closed while sending {command!r}", reader, stderr_path
        ) from exc


# Child: full record -> finish -> transcribe -> Complete flow with the
# ML-free mock pipeline. Phase-gated: the parent polls the OS socket table
# while chunks stream through encrypt-append (CAPTURING window) and while
# the pipeline is provably in flight (MID-TRANSCRIBE blocks inside the
# provider until the parent's polls are done). Runs on CI without the [ml]
# extra: the audio is ONE tone burst, so exactly one VAD segment exists and
# the numpy speaker-embedding path is never reached.
_CAPTURE_TRANSCRIBE_CHILD = '''
import math
import struct
import sys
import threading
import time
from pathlib import Path

from scribe_desktop.benchmark import apply_offline_env, assert_offline_env

# Mirror app startup (plan: Runtime offline enforcement): kill-switches set
# AND asserted before any further scribe/ML code runs.
apply_offline_env()
assert_offline_env()
# Installation plan D2: the parent test is pinned to the production channel
# (conftest), and so is this child, so it loads any model where the
# parent's skip check found it (a bare source run is the dev channel).
from scribe_desktop import install_layout

install_layout.channel = lambda: "production"
install_layout.is_frozen = lambda: False  # a source run, as the parent pins (C6)
print("OFFLINE-OK", flush=True)

from scribe_desktop.audio_capture import MockCaptureBackend
from scribe_desktop.encounter import unlinked_consent
from scribe_desktop.session import SessionController
from scribe_desktop.session_store import (
    KEY_FILENAME,
    TRANSCRIPT_FILENAME,
    unwrap_key_from_file,
)
from scribe_desktop.speech import SAMPLE_RATE, MockSpeechProvider
from scribe_desktop.transcription import read_transcript, transcribe_session

root = Path(sys.argv[1])
count = int(0.05 * SAMPLE_RATE)
loud = struct.pack(
    "<%dh" % count,
    *(
        int(0.5 * 32767 * math.sin(2 * math.pi * 440.0 * i / SAMPLE_RATE))
        for i in range(count)
    ),
)
quiet = bytes(count * 2)


def amplitude_vad(frame):
    samples = struct.unpack("<%dh" % (len(frame) // 2), frame)
    return 0.95 if max(abs(s) for s in samples) > 1000 else 0.02


class GatedProvider:
    """Delegates to MockSpeechProvider, but blocks INSIDE the pipeline on
    the first segment until the parent finishes its mid-transcription poll."""

    def __init__(self):
        self._inner = MockSpeechProvider()
        self._gated = False

    def transcribe_segment(self, pcm, sample_rate):
        if not self._gated:
            self._gated = True
            print("MID-TRANSCRIBE", flush=True)
            line = sys.stdin.readline()
            assert line.strip() == "GO", "parent gate broken: %r" % line
        return self._inner.transcribe_segment(pcm, sample_rate)


backend = MockCaptureBackend()
controller = SessionController(backend, sessions_root=root)
session = controller.start(0, consent=unlinked_consent())
stop = threading.Event()


def feed():
    i = 0
    while not stop.is_set():
        # 0.6 s of tone then silence: exactly ONE speech segment.
        backend.feed(loud if i < 12 else quiet)
        i += 1
        time.sleep(0.02)


feeder = threading.Thread(target=feed, daemon=True)
feeder.start()
print("CAPTURING %s" % session.session_id, flush=True)
line = sys.stdin.readline()
assert line.strip() == "FINISH", "parent gate broken: %r" % line
stop.set()
feeder.join(timeout=10.0)
controller.finish()
print("TRANSCRIBING", flush=True)
provider = GatedProvider()
controller.transcribe(
    lambda directory, crypto: transcribe_session(
        directory, crypto, provider, amplitude_vad
    )
)
session_dir = root / session.session_id
recovered = unwrap_key_from_file(session_dir)
document = read_transcript(session_dir, recovered)
assert document.transcript_segments, "pipeline produced no segments"
assert (session_dir / KEY_FILENAME).is_file()
print("TRANSCRIBED", flush=True)
# PR round 31: block so the parent's post-transcription sample lands on a
# provably-live process before Complete runs.
line = sys.stdin.readline()
assert line.strip() == "CONTINUE", "parent gate broken: %r" % line
completed = controller.complete()
assert completed.state.value == "written"
assert not (session_dir / KEY_FILENAME).exists(), "Complete must delete key custody"
assert not (session_dir / TRANSCRIPT_FILENAME).exists(), "Complete removes the directory"
print("COMPLETED-OK", flush=True)
'''


def test_recorder_no_sockets_during_capture_and_transcription(tmp_path: Path) -> None:
    """Plan Step 13: the recorder keeps ZERO sockets while chunks stream
    through the encrypt-append path AND while the transcription pipeline is
    in flight; the offline kill-switches are asserted in-process first."""
    script = _write_child(tmp_path, "capture_transcribe_child.py", _CAPTURE_TRANSCRIBE_CHILD)
    root = tmp_path / "sessions"
    stderr_path = tmp_path / "child-stderr.txt"
    proc, reader = _spawn_child(script, root, stderr_path)
    try:
        _await_marker(reader, proc, stderr_path, "OFFLINE-OK", 60)
        capturing = _await_marker(reader, proc, stderr_path, "CAPTURING", 60)
        session_id = capturing.split()[1]
        # Binding custody ordering, observed externally mid-recording:
        # key.dpapi is durably on disk while chunks are still arriving.
        assert (root / session_id / KEY_FILENAME).is_file()
        ps = _child_tree(proc, reader, stderr_path)
        # PR round 30: the poll window must provably overlap live capture —
        # the encrypted store must GROW across it, or the poll is vacuous.
        audio_path = root / session_id / AUDIO_FILENAME
        size_before = audio_path.stat().st_size if audio_path.exists() else 0
        _poll_no_connections(
            proc, ps, reader, stderr_path, "recorder mid-capture", polls=10
        )
        size_after = audio_path.stat().st_size if audio_path.exists() else 0
        if size_after <= size_before:
            raise _child_failure(
                "no chunks were appended during the capture poll window",
                reader,
                stderr_path,
            )
        _send(proc, reader, stderr_path, b"FINISH")
        _await_marker(reader, proc, stderr_path, "TRANSCRIBING", 60)
        _await_marker(reader, proc, stderr_path, "MID-TRANSCRIBE", 60)
        _poll_no_connections(
            proc, ps, reader, stderr_path, "recorder mid-transcription", polls=10
        )
        _send(proc, reader, stderr_path, b"GO")
        _await_marker(reader, proc, stderr_path, "TRANSCRIBED", 60)
        # PR rounds 30/31: final sample on a PROVABLY-live child — it blocks
        # on the CONTINUE gate until released, then runs Complete.
        assert_no_connections(ps, "recorder after transcription")
        _send(proc, reader, stderr_path, b"CONTINUE")
        _await_marker(reader, proc, stderr_path, "COMPLETED-OK", 60)
        # Optional post-Complete sample; the child may already have exited.
        _sample_after_exit(ps, "recorder after Complete")
        assert proc.wait(timeout=30) == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=15)  # PR round 30: reap before tmp_path cleanup


# Child (note-learning plan Task 1.5): the LIVE path — a live worker attached
# by the controller's factory transcribes a window WHILE chunks stream through
# the tee (gated inside that provider call so the parent's polls provably
# overlap live inference), then Finish seals, the processing callable drains
# the worker (gated inside the tail window's call; no batch model may be
# built: both composition-layer model classes are replaced with raisers) and
# writes the transcript, and Complete runs the binding custody ordering.
# Mock provider + amplitude VAD; numpy only (the worker embeds every segment).
_LIVE_CAPTURE_CHILD = '''
import math
import struct
import sys
import threading
import time
from pathlib import Path

from scribe_desktop.benchmark import apply_offline_env, assert_offline_env

apply_offline_env()
assert_offline_env()
# Installation plan D2: the parent test is pinned to the production channel
# (conftest), and so is this child, so it loads any model where the
# parent's skip check found it (a bare source run is the dev channel).
from scribe_desktop import install_layout

install_layout.channel = lambda: "production"
install_layout.is_frozen = lambda: False  # a source run, as the parent pins (C6)
print("OFFLINE-OK", flush=True)

from scribe_desktop.audio_capture import MockCaptureBackend
from scribe_desktop.encounter import unlinked_consent
from scribe_desktop.session import SessionController
from scribe_desktop.session_store import (
    KEY_FILENAME,
    TRANSCRIPT_FILENAME,
    unwrap_key_from_file,
)
from scribe_desktop.speech import SAMPLE_RATE, MockSpeechProvider
from scribe_desktop.transcription import LiveTranscriber, read_transcript
from scribe_desktop.ui import models

root = Path(sys.argv[1])
count = int(0.05 * SAMPLE_RATE)
loud = struct.pack(
    "<%dh" % count,
    *(
        int(0.5 * 32767 * math.sin(2 * math.pi * 440.0 * i / SAMPLE_RATE))
        for i in range(count)
    ),
)
quiet = bytes(count * 2)


def amplitude_vad(frame):
    samples = struct.unpack("<%dh" % (len(frame) // 2), frame)
    return 0.95 if max(abs(s) for s in samples) > 1000 else 0.02


posted = []


class GatedLiveProvider:
    """Delegates to MockSpeechProvider, but blocks INSIDE the live worker's
    provider call: the first call (the window transcribed DURING capture)
    until the parent's mid-inference polls are done, the second (the tail
    window drained after Finish) until the parent's drain polls are done.
    Both reads happen on the WORKER thread while the main thread is not
    reading stdin (it reads FINISH only after LIVE-POSTED, and CONTINUE only
    after the drain returned), so the two readers never overlap."""

    def __init__(self):
        self._inner = MockSpeechProvider()
        self.calls = 0

    def transcribe_segment(self, pcm, sample_rate):
        self.calls += 1
        if self.calls == 1:
            print("MID-LIVE-TRANSCRIBE", flush=True)
            line = sys.stdin.readline()
            assert line.strip() == "GO", "parent gate broken: %r" % line
        elif self.calls == 2:
            print("MID-LIVE-DRAIN", flush=True)
            line = sys.stdin.readline()
            assert line.strip() == "GO2", "parent gate broken: %r" % line
        return self._inner.transcribe_segment(pcm, sample_rate)


gated = GatedLiveProvider()


def live_factory():
    return LiveTranscriber(
        provider_factory=lambda: gated,
        vad_factory=lambda: amplitude_vad,
        on_window=posted.append,
    )


backend = MockCaptureBackend()
controller = SessionController(
    backend, sessions_root=root, live_transcriber_factory=live_factory
)
session = controller.start(0, consent=unlinked_consent())
stop = threading.Event()
second_utterance = threading.Event()
tone_blocks_fed = [0]


def feed():
    i = 0
    while not stop.is_set():
        # 0.6 s of tone then silence: ONE speech segment, transcribed LIVE
        # once the silence proves its window complete (~4 s of audio in).
        # After the first window posted, a CONTINUOUS tone: an utterance
        # still open at Finish, so the drain has a tail window to transcribe.
        if second_utterance.is_set():
            backend.feed(loud)
            tone_blocks_fed[0] += 1
        else:
            backend.feed(loud if i < 12 else quiet)
        i += 1
        time.sleep(0.02)


feeder = threading.Thread(target=feed, daemon=True)
feeder.start()
print("CAPTURING %s" % session.session_id, flush=True)
deadline = time.monotonic() + 60
while not posted:
    assert time.monotonic() < deadline, "the live worker posted no window"
    time.sleep(0.02)
second_utterance.set()
# Deterministic tail: LIVE-POSTED (and so the parent's FINISH) is announced
# only once the open second utterance holds a full second of tone (20 blocks
# of 50 ms) — well past the segmenter's 0.25 s minimum speech length — so the
# seal's close of that span ALWAYS yields a segment, a tail window and the
# second (gated) provider call, whatever the parent's round-trip timing.
while tone_blocks_fed[0] < 20:
    assert time.monotonic() < deadline, "the second utterance was never fed"
    time.sleep(0.02)
print("LIVE-POSTED", flush=True)
line = sys.stdin.readline()
assert line.strip() == "FINISH", "parent gate broken: %r" % line
stop.set()
feeder.join(timeout=10.0)
controller.finish()
print("TRANSCRIBING", flush=True)


class _NoBatchModel:
    def __init__(self, *args, **kwargs):
        raise AssertionError("the batch fallback must not build a model on the live path")


models.SileroVad = _NoBatchModel
models.WhisperSpeechProvider = _NoBatchModel
statuses = []
controller.transcribe(
    models.build_transcriber(
        attribution=lambda: (None, None),
        live_source=controller.claim_live_transcriber,
        on_status=statuses.append,
    )
)
assert statuses == [models.LIVE_ASSEMBLED_STATUS], statuses
assert gated.calls == 2, gated.calls  # one live window, one drained tail window
session_dir = root / session.session_id
recovered = unwrap_key_from_file(session_dir)
document = read_transcript(session_dir, recovered)
assert len(document.transcript_segments) == 2, "one live segment + the drained tail"
assert len(document.transcript_segments) == sum(len(w) for w in posted)
assert (session_dir / KEY_FILENAME).is_file()
print("TRANSCRIBED", flush=True)
line = sys.stdin.readline()
assert line.strip() == "CONTINUE", "parent gate broken: %r" % line
completed = controller.complete()
assert completed.state.value == "written"
assert not (session_dir / KEY_FILENAME).exists(), "Complete must delete key custody"
assert not (session_dir / TRANSCRIPT_FILENAME).exists(), "Complete removes the directory"
print("COMPLETED-OK", flush=True)
'''


def test_recorder_no_sockets_during_live_transcription(tmp_path: Path) -> None:
    """Note-learning plan Task 1.5: the recorder keeps ZERO sockets while the
    LIVE worker is provably INSIDE a provider call during capture (the child
    blocks there on a gate while the parent polls and chunks keep arriving),
    while the processing callable drains the sealed tail — provably inside
    the tail window's provider call, no batch model built — and through
    Complete (peer round 9 PR-LOW-021: every poll overlaps the phase it
    claims to observe, on the batch leg's gate pattern)."""
    pytest.importorskip("numpy")  # the live worker embeds every segment
    script = _write_child(tmp_path, "live_capture_child.py", _LIVE_CAPTURE_CHILD)
    root = tmp_path / "sessions"
    stderr_path = tmp_path / "child-stderr.txt"
    proc, reader = _spawn_child(script, root, stderr_path)
    try:
        _await_marker(reader, proc, stderr_path, "OFFLINE-OK", 60)
        capturing = _await_marker(reader, proc, stderr_path, "CAPTURING", 60)
        session_id = capturing.split()[1]
        assert (root / session_id / KEY_FILENAME).is_file()
        ps = _child_tree(proc, reader, stderr_path)
        audio_path = root / session_id / AUDIO_FILENAME
        # The child's live worker is blocked INSIDE its first provider call
        # (a window transcribed DURING capture) until GO: the polls below
        # overlap live inference, and the store must keep growing across them.
        _await_marker(reader, proc, stderr_path, "MID-LIVE-TRANSCRIBE", 60)
        size_before = audio_path.stat().st_size if audio_path.exists() else 0
        _poll_no_connections(
            proc, ps, reader, stderr_path, "recorder mid-capture inside live inference", polls=10
        )
        size_after = audio_path.stat().st_size if audio_path.exists() else 0
        if size_after <= size_before:
            raise _child_failure(
                "no chunks were appended during the live inference poll window",
                reader,
                stderr_path,
            )
        _send(proc, reader, stderr_path, b"GO")
        _await_marker(reader, proc, stderr_path, "LIVE-POSTED", 60)
        _send(proc, reader, stderr_path, b"FINISH")
        _await_marker(reader, proc, stderr_path, "TRANSCRIBING", 60)
        # The sealed tail: the worker is blocked inside the tail window's
        # provider call until GO2 while the processing callable waits in
        # drain() — the polls overlap the drain.
        _await_marker(reader, proc, stderr_path, "MID-LIVE-DRAIN", 60)
        _poll_no_connections(
            proc, ps, reader, stderr_path, "recorder inside the live tail drain", polls=10
        )
        _send(proc, reader, stderr_path, b"GO2")
        _await_marker(reader, proc, stderr_path, "TRANSCRIBED", 60)
        assert_no_connections(ps, "recorder after the live drain")
        _send(proc, reader, stderr_path, b"CONTINUE")
        _await_marker(reader, proc, stderr_path, "COMPLETED-OK", 60)
        # Optional post-Complete sample; the child may already have exited.
        _sample_after_exit(ps, "recorder after Complete (live leg)")
        assert proc.wait(timeout=30) == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=15)


# Child: the REAL local ML stack under the same phase gates. The parent
# polls continuously from just before SileroVad/WhisperSpeechProvider
# construction (the model-LOAD window — exactly where download/telemetry
# attempts would occur) until the pipeline reports done. Audio is SAPI
# speech (non-clinical fixture text), fed faster than real time.
_REAL_TRANSCRIBE_CHILD = '''
import sys
import threading
import time
from pathlib import Path

from scribe_desktop.benchmark import apply_offline_env, assert_offline_env

apply_offline_env()
assert_offline_env()
# Installation plan D2: the parent test is pinned to the production channel
# (conftest), and so is this child. Task 2.6: it loads its models from the
# source run's DEV root, where the parent's skip check found them.
from scribe_desktop import install_layout

install_layout.channel = lambda: "production"
install_layout.is_frozen = lambda: False  # a source run, as the parent pins (C6)
_real_ml_root = install_layout.models_root("dev")
install_layout.models_root = lambda of=None: _real_ml_root
print("OFFLINE-OK", flush=True)

from scribe_desktop.audio_capture import MockCaptureBackend
from scribe_desktop.encounter import unlinked_consent
from scribe_desktop.session import SessionController
from scribe_desktop.session_store import (
    KEY_FILENAME,
    TRANSCRIPT_FILENAME,
    unwrap_key_from_file,
)
from scribe_desktop.speech import SAMPLE_RATE
from scribe_desktop.transcription import read_transcript, transcribe_session

root = Path(sys.argv[1])

# TRUE 16 kHz mono PCM16 — SAPI renders 22050 Hz whatever format is asked
# for, so the shared fixture resamples (see tests/sapi_fixture.py).
from sapi_fixture import synthesize_speech_pcm

speech = synthesize_speech_pcm(
    "Margaret counted seventeen boats near the lighthouse on Tuesday morning."
)
chunk_bytes = int(0.05 * SAMPLE_RATE) * 2
pcm = bytes(chunk_bytes * 6) + speech + bytes(chunk_bytes * 12)

backend = MockCaptureBackend()
controller = SessionController(backend, sessions_root=root)
session = controller.start(0, consent=unlinked_consent())
stop = threading.Event()


def feed():
    offset = 0
    announced = False
    silence_block = bytes(chunk_bytes)
    while not stop.is_set():
        block = pcm[offset : offset + chunk_bytes]
        if block:
            offset += len(block)
            backend.feed(block)
        else:
            if not announced:
                announced = True
                print("FED-ALL", flush=True)
            backend.feed(silence_block)
        time.sleep(0.01)


feeder = threading.Thread(target=feed, daemon=True)
print("CAPTURING %s" % session.session_id, flush=True)
feeder.start()
line = sys.stdin.readline()
assert line.strip() == "FINISH", "parent gate broken: %r" % line
stop.set()
feeder.join(timeout=10.0)
controller.finish()
print("TRANSCRIBING", flush=True)
# PR round 30: block until the parent's poll loop is armed, so the polled
# window deterministically covers the ML imports + model load below.
line = sys.stdin.readline()
assert line.strip() == "GO", "parent gate broken: %r" % line
from scribe_desktop.speech import SileroVad
from scribe_desktop.transcription import WhisperSpeechProvider, resolve_whisper_model

vad = SileroVad()
# Step 13: load the RESOLVED model (medium default, small fallback) inside
# the armed poll window — the production model is the one proven socketless.
provider = WhisperSpeechProvider(model_name=resolve_whisper_model())
controller.transcribe(
    lambda directory, crypto: transcribe_session(
        directory, crypto, provider, vad.frame_probability
    )
)
session_dir = root / session.session_id
recovered = unwrap_key_from_file(session_dir)
document = read_transcript(session_dir, recovered)
words = [w for s in document.transcript_segments for w in s.transcript_words]
assert document.transcript_segments, "real pipeline found no speech"
assert len(words) >= 2, "real whisper produced implausibly few words"
print("TRANSCRIBED", flush=True)
# PR round 31: block so the parent's post-transcription sample lands on a
# provably-live process before Complete runs.
line = sys.stdin.readline()
assert line.strip() == "CONTINUE", "parent gate broken: %r" % line
completed = controller.complete()
assert completed.state.value == "written"
assert not (session_dir / KEY_FILENAME).exists()
assert not (session_dir / TRANSCRIPT_FILENAME).exists()  # Complete removes the directory
print("COMPLETED-OK", flush=True)
'''


@requires_ml_models
def test_recorder_no_sockets_during_real_whisper_transcription(tmp_path: Path) -> None:
    """Plan Step 13: the poll against the REAL Whisper path — model load +
    silero VAD + faster-whisper transcription happen inside a continuously
    polled window; the process must hold zero sockets throughout."""
    apply_offline_env()  # offline BEFORE ML imports (PR-MED-009/-014 pattern)
    pytest.importorskip("numpy")
    pytest.importorskip("onnxruntime")
    pytest.importorskip("faster_whisper")
    script = _write_child(tmp_path, "real_transcribe_child.py", _REAL_TRANSCRIBE_CHILD)
    root = tmp_path / "sessions"
    stderr_path = tmp_path / "child-stderr.txt"
    proc, reader = _spawn_child(script, root, stderr_path)
    try:
        _await_marker(reader, proc, stderr_path, "OFFLINE-OK", 120)
        capturing = _await_marker(reader, proc, stderr_path, "CAPTURING", 120)
        session_id = capturing.split()[1]
        ps = _child_tree(proc, reader, stderr_path)
        # PR round 30: the poll window must provably overlap live capture.
        audio_path = root / session_id / AUDIO_FILENAME
        size_before = audio_path.stat().st_size if audio_path.exists() else 0
        _poll_no_connections(
            proc, ps, reader, stderr_path, "recorder mid-capture (real leg)", polls=10
        )
        size_after = audio_path.stat().st_size if audio_path.exists() else 0
        if size_after <= size_before:
            raise _child_failure(
                "no chunks were appended during the capture poll window",
                reader,
                stderr_path,
            )
        # Wait until the whole SAPI fixture is durably captured, then finish.
        _await_marker(reader, proc, stderr_path, "FED-ALL", 120)
        _send(proc, reader, stderr_path, b"FINISH")
        _await_marker(reader, proc, stderr_path, "TRANSCRIBING", 60)
        # PR rounds 30/31: the child blocks on GO before ANY ML construction.
        # Sample while it is provably blocked (the window opens clean), then
        # release it and poll continuously through imports + model load +
        # transcription.
        assert_no_connections(ps, "recorder at transcription start")
        _send(proc, reader, stderr_path, b"GO")
        polls = 0
        deadline = time.monotonic() + 300
        while reader.find("TRANSCRIBED") is None:
            if reader.eof or time.monotonic() > deadline:
                # Raises with full child stdout/stderr diagnostics.
                _await_marker(reader, proc, stderr_path, "TRANSCRIBED", 0.1)
                break
            assert_no_connections(ps, "recorder during real whisper transcription")
            polls += 1
            time.sleep(0.03)
        assert polls >= 3, "transcription window closed before any poll landed"
        # PR rounds 30/31: final sample on a PROVABLY-live child (blocked on
        # the CONTINUE gate), then release Complete and best-effort sample.
        assert_no_connections(ps, "recorder after real transcription")
        _send(proc, reader, stderr_path, b"CONTINUE")
        _await_marker(reader, proc, stderr_path, "COMPLETED-OK", 120)
        # Optional post-Complete sample; the child may already have exited.
        _sample_after_exit(ps, "recorder after Complete (real leg)")
        assert proc.wait(timeout=60) == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=15)  # PR round 30: reap before tmp_path cleanup


# Child (note-learning plan Task 4.4, D8): a PROSE generation under the same
# gate pattern. The stage is the real `models.build_prose_stage` over the
# mock language model; the model call blocks on a gate so the parent's polls
# provably land INSIDE a generation; the result is bound to the note and
# rendered through the one rendering path.
_PROSE_STAGE_CHILD = '''
import sys

from scribe_desktop.benchmark import apply_offline_env, assert_offline_env

apply_offline_env()
assert_offline_env()
print("OFFLINE-OK", flush=True)

from scribe_desktop.language_model import MockLanguageModel, echo_prompt_lines
from scribe_desktop.note import render_note
from scribe_desktop.ui import models
from test_prose_style import FIXTURE_NOTES, _note

note = _note(FIXTURE_NOTES[0], style="narrative")
gated = [False]


def responder(system_text, user_text):
    if not gated[0]:
        gated[0] = True
        print("MID-PROSE", flush=True)
        line = sys.stdin.readline()
        assert line.strip() == "GO", "parent gate broken: %r" % line
    return echo_prompt_lines(system_text, user_text)


stage = models.build_prose_stage(
    "narrative",
    model_factory=lambda: MockLanguageModel(responder=responder),
    cache=None,
    available=lambda: True,  # the mock leg runs where no model file exists
)
result = stage(note)
assert result.reason is None, result.reason
assert (result.passed, result.failed, result.errored) == (3, 0, 0), result
bound = models.bind_stage_result(note, result)
assert len(bound.style_renderings) == 3
assert render_note(bound, "narrative") != render_note(note, "clean")
print("PROSE-OK", flush=True)
line = sys.stdin.readline()
assert line.strip() == "CONTINUE", "parent gate broken: %r" % line
print("DONE", flush=True)
'''


def test_prose_generation_no_sockets_with_the_mock_model(tmp_path: Path) -> None:
    """Note-learning plan Task 4.4 (D8): the prose STAGE's orchestration —
    the prompt build, the section loop, Check 5, the binding — opens no socket
    while the process is provably inside a language-model call (the child
    blocks there on a gate while the parent polls) and after the rendering
    is bound. This leg runs everywhere over `MockLanguageModel`, so NO native
    runtime code runs here (codex round 22 PR-LOW-040): the runtime's own
    coverage is the real-model leg below, which is conditional on the wheel
    and the file. Neither is `assert_offline_env`'s: llama-cpp-python reads
    no kill-switch."""
    script = _write_child(tmp_path, "prose_stage_child.py", _PROSE_STAGE_CHILD)
    stderr_path = tmp_path / "child-stderr.txt"
    proc, reader = _spawn_child(script, tmp_path / "unused", stderr_path)
    try:
        _await_marker(reader, proc, stderr_path, "OFFLINE-OK", 60)
        ps = _child_tree(proc, reader, stderr_path)
        _await_marker(reader, proc, stderr_path, "MID-PROSE", 60)
        _poll_no_connections(
            proc, ps, reader, stderr_path, "inside a prose generation (mock model)", polls=10
        )
        _send(proc, reader, stderr_path, b"GO")
        _await_marker(reader, proc, stderr_path, "PROSE-OK", 60)
        assert_no_connections(ps, "after the prose rendering was bound")
        _send(proc, reader, stderr_path, b"CONTINUE")
        _await_marker(reader, proc, stderr_path, "DONE", 60)
        assert proc.wait(timeout=30) == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=15)


# Child (Task 4.4): the REAL prose runtime and the pinned model — the model
# LOAD window (digest, DLL load, the smoke generation) and one section's
# generation under a continuous poll. Skips by name until Task P.1 downloads
# the file and the hashed wheel is installed.
_REAL_PROSE_CHILD = '''
import sys

from scribe_desktop.benchmark import apply_offline_env, assert_offline_env

apply_offline_env()
assert_offline_env()
# Installation plan D2: pinned to the production channel, as the parent
# test is. Task 2.6: the model is loaded from the source run's DEV root,
# where the parent's skip check found it.
from scribe_desktop import install_layout

install_layout.channel = lambda: "production"
install_layout.is_frozen = lambda: False  # a source run, as the parent pins (C6)
_real_ml_root = install_layout.models_root("dev")
install_layout.models_root = lambda of=None: _real_ml_root
print("OFFLINE-OK", flush=True)
line = sys.stdin.readline()
assert line.strip() == "GO", "parent gate broken: %r" % line

from scribe_desktop.language_model import LocalLanguageModel
from scribe_desktop.note import render_note
from scribe_desktop.ui import models
from test_prose_style import FIXTURE_NOTES, _note

note = _note(FIXTURE_NOTES[0], style="narrative")
stage = models.build_prose_stage("narrative", model_factory=LocalLanguageModel, cache=None)
result = stage(note)
assert result.reason is None, result.reason
assert result.errored == 0, result
bound = models.bind_stage_result(note, result)
print("PROSE-DONE passed=%d failed=%d seconds=%.1f" % (
    result.passed, result.failed, result.seconds), flush=True)
line = sys.stdin.readline()
assert line.strip() == "CONTINUE", "parent gate broken: %r" % line
print("DONE", flush=True)
'''


def test_prose_generation_no_sockets_with_the_real_model(tmp_path: Path) -> None:
    """Task 4.4 (D8): the RUNTIME's coverage — the real library's load and
    one generation over the pinned GGUF under a continuous poll from before
    the model load until the section prose is bound — the leg that observes
    llama-cpp-python's native code (codex round 22 PR-LOW-040). Conditional
    evidence: it skips by name until the wheel and the file exist. The Check
    5 pass count is printed (the composer's record for Task 4.3), not
    asserted: fidelity is the gate's verdict, the socket table is this leg's."""
    from scribe_desktop.language_model import (
        language_model_file_available,
        language_runtime_importable,
    )

    if not language_runtime_importable():
        pytest.skip("the prose runtime is not installed (desktop/requirements-ml-prose.txt)")
    # Installation plan Task 2.6: looked for in the source run's DEV models
    # root, where the child loads it from.
    if not on_real_ml_root(language_model_file_available):
        pytest.skip(real_ml_skip_reason("the pinned language model"))
    apply_offline_env()
    script = _write_child(tmp_path, "real_prose_child.py", _REAL_PROSE_CHILD)
    stderr_path = tmp_path / "child-stderr.txt"
    proc, reader = _spawn_child(script, tmp_path / "unused", stderr_path)
    try:
        _await_marker(reader, proc, stderr_path, "OFFLINE-OK", 120)
        ps = _child_tree(proc, reader, stderr_path)
        assert_no_connections(ps, "before the language model load")
        _send(proc, reader, stderr_path, b"GO")
        polls = 0
        deadline = time.monotonic() + 900
        while reader.find("PROSE-DONE") is None:
            if reader.eof or time.monotonic() > deadline:
                _await_marker(reader, proc, stderr_path, "PROSE-DONE", 0.1)
                break
            assert_no_connections(ps, "during the language model load and generation")
            polls += 1
            time.sleep(0.05)
        assert polls >= 3, "the generation window closed before any poll landed"
        assert_no_connections(ps, "after the real prose rendering")
        _send(proc, reader, stderr_path, b"CONTINUE")
        _await_marker(reader, proc, stderr_path, "DONE", 120)
        assert proc.wait(timeout=60) == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=15)


# Child: records continuously until the parent hard-kills it (crash-sim).
# Continuous tone -> the recovered store yields ONE segment (numpy-free)
# no matter where the kill lands; a torn tail record is expected crash
# behaviour and must be tolerated by recovery.
_CRASH_RECORDER_CHILD = '''
import math
import struct
import sys
import time
from pathlib import Path

from scribe_desktop.benchmark import apply_offline_env, assert_offline_env

apply_offline_env()
assert_offline_env()

from scribe_desktop.audio_capture import MockCaptureBackend
from scribe_desktop.encounter import unlinked_consent
from scribe_desktop.session import SessionController
from scribe_desktop.speech import SAMPLE_RATE

root = Path(sys.argv[1])
count = int(0.05 * SAMPLE_RATE)
loud = struct.pack(
    "<%dh" % count,
    *(
        int(0.5 * 32767 * math.sin(2 * math.pi * 440.0 * i / SAMPLE_RATE))
        for i in range(count)
    ),
)

live_factory = None
if len(sys.argv) > 2 and sys.argv[2] == "live":
    # Note-learning plan Task 1.5: a live worker is attached at the crash.
    from scribe_desktop.speech import MockSpeechProvider
    from scribe_desktop.transcription import LiveTranscriber

    def amplitude_vad(frame):
        samples = struct.unpack("<%dh" % (len(frame) // 2), frame)
        return 0.95 if max(abs(s) for s in samples) > 1000 else 0.02

    def live_factory():
        return LiveTranscriber(
            provider_factory=MockSpeechProvider, vad_factory=lambda: amplitude_vad
        )

backend = MockCaptureBackend()
controller = SessionController(
    backend, sessions_root=root, live_transcriber_factory=live_factory
)
session = controller.start(0, consent=unlinked_consent())
print("RECORDING %s" % session.session_id, flush=True)
while True:
    backend.feed(loud)
    time.sleep(0.01)
'''


@pytest.mark.parametrize("with_live_worker", [False, True])
def test_crash_kill_mid_recording_then_recover_transcribe_complete(
    tmp_path: Path, with_live_worker: bool
) -> None:
    """Plan Step 13 crash-sim, END-TO-END: hard-kill a real recorder process
    mid-recording, then (as the restarted process) recover the session via
    DPAPI unwrap, re-transcribe the durable chunks, verify the transcript
    decrypts, and drive the binding Complete custody ordering.

    Note-learning plan Task 1.5: with a LIVE worker attached at the crash the
    recovery path is the UNCHANGED batch one — the worker's in-memory state
    died with the process and nothing of it exists on disk."""
    if with_live_worker:
        pytest.importorskip("numpy")
    script = _write_child(tmp_path, "crash_recorder_child.py", _CRASH_RECORDER_CHILD)
    root = tmp_path / "sessions"
    stderr_path = tmp_path / "child-stderr.txt"
    proc, reader = _spawn_child(
        script, root, stderr_path, extra_args=("live",) if with_live_worker else ()
    )
    try:
        recording = _await_marker(reader, proc, stderr_path, "RECORDING", 60)
        session_id = recording.split()[1]
        session_dir = root / session_id
        # Binding ordering: key.dpapi durably written BEFORE the first chunk.
        assert (session_dir / KEY_FILENAME).is_file()
        audio_path = session_dir / AUDIO_FILENAME
        deadline = time.monotonic() + 30
        while True:
            size = audio_path.stat().st_size if audio_path.exists() else 0
            if size >= 16_384:  # ~10 durable 50 ms tone records
                break
            if time.monotonic() > deadline:
                raise _child_failure(
                    f"audio store never grew (size={size})", reader, stderr_path
                )
            time.sleep(0.05)
        proc.kill()  # hard mid-recording termination: no flush, no cleanup
        assert proc.wait(timeout=30) != 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=15)  # PR round 30: reap before tmp_path cleanup

    # --- the "restarted app" half (this process never saw the key) ---------
    assert store_has_footer(audio_path) is False  # crash = unfinished store
    # The sweep must KEEP a fresh recoverable session (24 h window).
    results = sweep_sessions(root, active_session_ids=frozenset())
    actions = {result.session_id: result.action for result in results}
    assert actions.get(session_id) == "kept"
    assert (session_dir / KEY_FILENAME).is_file()

    outcome = recover_session_transcription(
        session_dir, MockSpeechProvider(), _amplitude_vad
    )
    assert outcome.store_finished is False  # recovery UI must warn: tail may be missing
    assert outcome.document.session_id == session_id
    assert outcome.document.transcript_segments, "recovered audio produced no segments"
    assert read_transcript(session_dir, outcome.crypto) == outcome.document

    # Complete custody ordering: fsync -> verify decrypt -> delete key.
    complete_session(session_dir, outcome.crypto)
    assert not (session_dir / KEY_FILENAME).exists()
    assert not session_dir.exists()  # every Complete removes the directory
    assert outcome.crypto.destroyed  # no in-memory decrypt capability remains
    with pytest.raises(RuntimeError):
        outcome.crypto.export_key()


# Child: the plan's "network stubbed to fail" offline-enforcement proof.
# The Python socket layer is replaced with raising stubs BEFORE any
# scribe/ML import; the REAL pipeline (silero + faster-whisper) must then
# succeed end-to-end. (Native socket use inside onnxruntime/ctranslate2 is
# outside the Python layer — the OS-level polls above cover it.)
_STUBBED_NETWORK_CHILD = '''
import _socket
import socket
import sys
from pathlib import Path


class _RefusingSocket(socket.socket):
    """Subclassable (stdlib ssl does `class SSLSocket(socket.socket)` at
    import time) but never constructible: creating ANY socket raises."""

    def __init__(self, *args, **kwargs):
        raise AssertionError("network access attempted during offline transcription")


def _refuse(*args, **kwargs):
    raise AssertionError("network access attempted during offline transcription")


# PR rounds 30/31: stub the Python network layer in BOTH `socket` and the
# `_socket` C module — `socket.SocketType` keeps binding the ORIGINAL class
# after `socket.socket` is replaced, `_socket` is directly importable, and
# its resolver functions would otherwise stay callable. Every stubbed name
# is recorded so the exit tamper-check re-verifies the WHOLE set. (Native
# sockets inside onnxruntime/ctranslate2 are out of Python's reach by
# construction — the OS-level polls cover that layer.)
_STUBBED = []


def _stub(module, name, value):
    if hasattr(module, name):
        setattr(module, name, value)
        _STUBBED.append((module, name, value))


for _module in (socket, _socket):
    _stub(_module, "socket", _RefusingSocket)
    _stub(_module, "SocketType", _RefusingSocket)
    for _name in (
        "create_connection",
        "getaddrinfo",
        "gethostbyname",
        "gethostbyname_ex",
        "gethostbyaddr",
        "getnameinfo",
        "getfqdn",
        "socketpair",
    ):
        _stub(_module, _name, _refuse)

assert any(m is socket and n == "socket" for m, n, v in _STUBBED)
assert any(m is _socket and n == "socket" for m, n, v in _STUBBED)
assert any(m is _socket and n == "getaddrinfo" for m, n, v in _STUBBED)

from scribe_desktop.benchmark import apply_offline_env, assert_offline_env

apply_offline_env()
assert_offline_env()
# Installation plan D2: pinned to the production channel, as the parent
# test is. Task 2.6: the models are loaded from the source run's DEV root,
# where the parent's skip check found them.
from scribe_desktop import install_layout

install_layout.channel = lambda: "production"
install_layout.is_frozen = lambda: False  # a source run, as the parent pins (C6)
_real_ml_root = install_layout.models_root("dev")
install_layout.models_root = lambda of=None: _real_ml_root

from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import (
    AUDIO_FILENAME,
    KEY_FILENAME,
    SessionChunkStore,
    complete_session,
    wrap_key_to_file,
)
from scribe_desktop.speech import SAMPLE_RATE, SileroVad
from scribe_desktop.transcription import (
    WhisperSpeechProvider,
    read_transcript,
    resolve_whisper_model,
    transcribe_session,
)


# TRUE 16 kHz mono PCM16 (see tests/sapi_fixture.py). Imported AFTER the
# stub registry above: the fixture reaches av/SAPI with sockets already dead.
from sapi_fixture import synthesize_speech_pcm

speech = synthesize_speech_pcm(
    "Margaret counted seventeen boats near the lighthouse on Tuesday morning."
)
session_id = "d" * 32
session_dir = Path(sys.argv[1]) / session_id
session_dir.mkdir(parents=True)
crypto = SessionCrypto()
wrap_key_to_file(crypto, session_dir)
store = SessionChunkStore.create(session_dir / AUDIO_FILENAME, crypto, session_id)
silence = bytes(int(0.5 * SAMPLE_RATE) * 2)
pcm = silence + speech + silence
for i in range(0, len(pcm), 32000):
    store.append_chunk(pcm[i : i + 32000])
store.finish()

vad = SileroVad()
# Step 13: the resolved production model must succeed with sockets dead.
provider = WhisperSpeechProvider(model_name=resolve_whisper_model())
document = transcribe_session(session_dir, crypto, provider, vad.frame_probability)
assert document.transcript_segments, "no speech found with network stubbed"
words = [w for s in document.transcript_segments for w in s.transcript_words]
assert len(words) >= 2, "real whisper produced implausibly few words"
assert read_transcript(session_dir, crypto) == document
complete_session(session_dir, crypto)
assert not (session_dir / KEY_FILENAME).exists()
# PR round 31: re-verify the ENTIRE stub set — nothing may have restored a
# real network entry point behind the proof's back.
for module, name, value in _STUBBED:
    assert getattr(module, name) is value, (
        "stub tampered: %s.%s" % (module.__name__, name)
    )
print("OFFLINE-TRANSCRIBE-OK", flush=True)
'''


@requires_ml_models
def test_transcription_succeeds_with_sockets_stubbed_to_fail(tmp_path: Path) -> None:
    """Plan Runtime offline enforcement: the REAL transcription stack must
    succeed with the Python socket layer stubbed to raise — any download or
    telemetry attempt at the Python layer fails the run loudly."""
    apply_offline_env()  # offline BEFORE ML imports (PR-MED-009/-014 pattern)
    pytest.importorskip("numpy")
    pytest.importorskip("onnxruntime")
    pytest.importorskip("faster_whisper")
    script = _write_child(tmp_path, "stubbed_network_child.py", _STUBBED_NETWORK_CHILD)
    result = subprocess.run(
        [sys.executable, str(script), str(tmp_path / "sessions")],
        capture_output=True,
        cwd=str(REPO),
        timeout=300,
        check=False,
    )
    detail = f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    assert result.returncode == 0, (
        f"offline transcription failed under the socket stub:\n{detail}"
    )
    assert b"OFFLINE-TRANSCRIBE-OK" in result.stdout, detail


# Cliniko draft-write plan Task 5.3's source pins (which modules may name the
# draft write or a PATCH) are pure AST checks, so they live beside the client's
# confinement pins in ``test_cliniko_client.py::TestWriteCallSites``, where
# neither this module's launcher fixture nor ``SCRIBE_SKIP_INTEGRATION`` skips them.
