"""Steps 10 + 13: end-to-end integration through REAL processes + the
no-network proof.

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
  the Python network stack is hard-down).

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
from pathlib import Path
from typing import IO

import psutil
import pytest

from scribe_desktop.benchmark import apply_offline_env
from scribe_desktop.identity import EXPECTED_ORIGIN as ORIGIN
from scribe_desktop.identity import NONCE_HEX_LENGTH
from scribe_desktop.session_store import (
    AUDIO_FILENAME,
    KEY_FILENAME,
    TRANSCRIPT_FILENAME,
    complete_session,
    store_has_footer,
    sweep_sessions,
)
from scribe_desktop.speech import MockSpeechProvider, vad_model_available
from scribe_desktop.transcription import (
    read_transcript,
    recover_session_transcription,
    resolve_whisper_model,
    whisper_model_available,
)

REPO = Path(__file__).resolve().parents[2]
TESTS_DIR = Path(__file__).resolve().parent
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

# Real-ML legs are skip-if-absent for CI (plan: model files never live on
# runners); everything else in this module runs everywhere on Windows.
# The gate mirrors production model resolution (Step 13: medium default,
# small fallback) so a fallback-only machine still runs the proof.
requires_ml_models = pytest.mark.skipif(
    not vad_model_available() or not whisper_model_available(resolve_whisper_model()),
    reason="local silero + whisper models required (run scripts/setup-models.py)",
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


def assert_no_connections(proc: psutil.Process, label: str) -> None:
    conns = proc.net_connections(kind="all")
    assert conns == [], f"{label} has network connections: {conns}"


def _amplitude_vad(frame_bytes: bytes) -> float:
    """Deterministic ML-free VAD stand-in (mirrors test_transcription)."""
    samples = struct.unpack(f"<{len(frame_bytes) // 2}h", frame_bytes)
    return 0.95 if max(abs(s) for s in samples) > 1000 else 0.02


# ---------------------------------------------------------------------------
# Step 10 tests (host handshake + idle app), unchanged in intent.
# ---------------------------------------------------------------------------


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
        "from scribe_desktop.ui.main_window import MainWindow\n"
        "import tempfile, time\n"
        "from pathlib import Path\n"
        "app = QApplication([])\n"
        "root = Path(tempfile.mkdtemp()) / 'sessions'\n"
        "backend = MockCaptureBackend()\n"
        "controller = SessionController(backend, sessions_root=root)\n"
        "w = MainWindow(controller, backend, sessions_root=root)\n"
        "w.status_panel.on_self_test()\n"
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
        app.wait(timeout=15)  # PR round 31: reap uniformly


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


def _poll_no_connections(
    proc: subprocess.Popen[bytes],
    ps: psutil.Process,
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
    # importable by default; prepending it lets them share `sapi_fixture` (the
    # SAPI-renders-22050 Hz correction must exist in exactly ONE place, not
    # re-copied into every child). Two stdlib statements, no imports of our own
    # — the socket-stub child still stubs before anything else loads.
    prelude = f"import sys\nsys.path.insert(0, {str(TESTS_DIR)!r})\n"
    script = tmp_path / name
    script.write_text(prelude + code, encoding="utf-8")
    return script


def _spawn_child(
    script: Path, sessions_root: Path, stderr_path: Path
) -> tuple[subprocess.Popen[bytes], _PipeReader]:
    with stderr_path.open("wb") as stderr:
        proc = subprocess.Popen(
            [sys.executable, str(script), str(sessions_root)],
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
print("OFFLINE-OK", flush=True)

from scribe_desktop.audio_capture import MockCaptureBackend
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
session = controller.start(0)
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
assert (session_dir / TRANSCRIPT_FILENAME).is_file(), "transcript artifact must remain"
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
        ps = psutil.Process(proc.pid)
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
        try:  # bonus post-Complete sample; the child may already have exited
            assert_no_connections(ps, "recorder after Complete")
        except psutil.NoSuchProcess:
            pass  # an exited process holds no sockets
        assert proc.wait(timeout=30) == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=15)  # PR round 30: reap before tmp_path cleanup


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
print("OFFLINE-OK", flush=True)

from scribe_desktop.audio_capture import MockCaptureBackend
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
session = controller.start(0)
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
assert (session_dir / TRANSCRIPT_FILENAME).is_file()
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
        ps = psutil.Process(proc.pid)
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
        try:
            assert_no_connections(ps, "recorder after Complete (real leg)")
        except psutil.NoSuchProcess:
            pass  # an exited process holds no sockets
        assert proc.wait(timeout=60) == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=15)  # PR round 30: reap before tmp_path cleanup


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

backend = MockCaptureBackend()
controller = SessionController(backend, sessions_root=root)
session = controller.start(0)
print("RECORDING %s" % session.session_id, flush=True)
while True:
    backend.feed(loud)
    time.sleep(0.01)
'''


def test_crash_kill_mid_recording_then_recover_transcribe_complete(
    tmp_path: Path,
) -> None:
    """Plan Step 13 crash-sim, END-TO-END: hard-kill a real recorder process
    mid-recording, then (as the restarted process) recover the session via
    DPAPI unwrap, re-transcribe the durable chunks, verify the transcript
    decrypts, and drive the binding Complete custody ordering."""
    script = _write_child(tmp_path, "crash_recorder_child.py", _CRASH_RECORDER_CHILD)
    root = tmp_path / "sessions"
    stderr_path = tmp_path / "child-stderr.txt"
    proc, reader = _spawn_child(script, root, stderr_path)
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
    assert (session_dir / TRANSCRIPT_FILENAME).is_file()
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
