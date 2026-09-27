"""Shared fakes for the native-host relay tests (Cliniko workflow safeguards
plan Task 4.4): Chrome's side of stdio (a blocking stdin the test feeds and a
stdout the test reads frames from), a fake pipe link to the app and a
scripted connector. No pipe, no socket."""

from __future__ import annotations

import io
import json
import logging
import queue
import struct
import threading
import time
from collections.abc import Callable
from typing import Any

from conftest import frame
from scribe_desktop.framing import EndOfStream
from scribe_desktop.native_host import AppRelay, ChromeOut, run_host
from scribe_desktop.protocol import PROTOCOL_VERSION

WAIT_S = 10.0
HOST = "example-clinic.au1.cliniko.com"
PATIENT_NAME = "Test Patient Placeholder"
# Placeholder ids, distinctive enough that a log search cannot hit a timestamp.
PATIENT_ID = "918273645"
NOTE_ID = "827364519"
CONTEXT_PAYLOAD: dict[str, Any] = {
    "seq": 1,
    "tab_id": 7,
    "window_id": 1,
    "focused": True,
    "page": "note",
    "host": HOST,
    "patient_id": PATIENT_ID,
    "note_id": NOTE_ID,
}
COMMAND_PAYLOAD: dict[str, Any] = {"action": "pause", "state_rev": 3}
STATE_PAYLOAD: dict[str, Any] = {
    "state_rev": 4,
    "app_running": True,
    "allow_list": [HOST],
    "hotkey": {"available": False},
    "spoken_pause": False,
    "warnings": [],
    "report": {
        "tab_id": 7,
        "clinic_host": HOST,
        "patient_id": PATIENT_ID,
        "note_id": NOTE_ID,
        "verification": "verified",
        "patient_name": PATIENT_NAME,
    },
}


def chrome_message(
    message_type: str, payload: dict[str, Any], nonce: str | None
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "type": message_type,
        "payload": payload,
    }
    if nonce is not None:
        message["session_nonce"] = nonce
    return message


def pipe_message(message_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"protocol_version": PROTOCOL_VERSION, "type": message_type, "payload": payload}


class ChromeStdin:
    """The host's stdin as Chrome drives it: blocks until the test feeds a
    frame; ``close`` is Chrome going away (EOF)."""

    def __init__(self) -> None:
        self._chunks: queue.Queue[bytes] = queue.Queue()
        self._buffer = b""
        self._eof = False

    def send(self, value: dict[str, Any]) -> None:
        self._chunks.put(frame(value))

    def close(self) -> None:
        self._chunks.put(b"")

    def read(self, size: int) -> bytes:
        while not self._buffer:
            if self._eof:
                return b""
            try:
                chunk = self._chunks.get(timeout=WAIT_S)
            except queue.Empty:
                chunk = b""  # a test that ended without closing: end quietly
            if chunk == b"":
                self._eof = True
                return b""
            self._buffer += chunk
        out, self._buffer = self._buffer[:size], self._buffer[size:]
        return out


class ChromeSink(io.RawIOBase):
    """The host's stdout as Chrome reads it (thread-safe; complete frames
    only)."""

    def __init__(self) -> None:
        super().__init__()
        self._data = bytearray()
        self._cond = threading.Condition()

    def writable(self) -> bool:
        return True

    def write(self, data: Any) -> int:
        with self._cond:
            self._data += bytes(data)
            self._cond.notify_all()
        return len(data)

    def frames(self) -> list[dict[str, Any]]:
        with self._cond:
            data = bytes(self._data)
        out: list[dict[str, Any]] = []
        offset = 0
        while offset + 4 <= len(data):
            (length,) = struct.unpack("=I", data[offset : offset + 4])
            if offset + 4 + length > len(data):
                break
            out.append(json.loads(data[offset + 4 : offset + 4 + length].decode("utf-8")))
            offset += 4 + length
        return out

    def wait_for(
        self, predicate: Callable[[list[dict[str, Any]]], bool], timeout: float = WAIT_S
    ) -> list[dict[str, Any]]:
        deadline = time.monotonic() + timeout
        while True:
            frames = self.frames()
            if predicate(frames):
                return frames
            remaining = deadline - time.monotonic()
            assert remaining > 0, f"timed out; frames so far: {[f['type'] for f in frames]}"
            with self._cond:
                self._cond.wait(min(remaining, 0.05))

    def states(self) -> list[dict[str, Any]]:
        return [f for f in self.frames() if f["type"] == "state"]


_EOF = object()


class FakeLink:
    """One connection to the app: ``app_sends`` / ``app_closes`` drive it,
    ``written`` records what the host forwarded. Like ``PipeConnection``, a
    blocked read ends on the connector's stop (``release``) or ``retire``;
    ``events`` records the read settling and the close, in order, and
    ``close_threads`` which thread closed it (codex round 28 PR-MED-140).
    ``write_ok`` False scripts a failed write (PR-MED-141); ``settle_gate``
    holds the read's END (after a release, retire or app close) until the
    test sets it — a read slow to settle (codex round 30)."""

    def __init__(
        self, *, write_ok: bool = True, settle_gate: threading.Event | None = None
    ) -> None:
        self._inbound: queue.Queue[Any] = queue.Queue()
        self.written: list[dict[str, Any]] = []
        self.write_ok = write_ok
        self.settle_gate = settle_gate
        self.closed = threading.Event()
        self.retired = threading.Event()
        self.events: list[str] = []
        self.close_threads: list[str] = []

    def app_sends(self, value: Any) -> None:
        self._inbound.put(value)

    def app_closes(self) -> None:
        self._inbound.put(_EOF)

    def release(self) -> None:
        """The connector's stop event, as the real read waits on it."""
        self._inbound.put(_EOF)

    def read_frame(self) -> Any:
        try:
            item = self._inbound.get(timeout=WAIT_S)
        except queue.Empty:
            item = _EOF
        if item is _EOF:
            if self.settle_gate is not None:
                self.settle_gate.wait(WAIT_S)
            self.events.append("settled")
            raise EndOfStream()
        return item

    def write_frame(self, value: Any) -> bool:
        self.written.append(value)
        return self.write_ok

    def retire(self) -> None:
        self.retired.set()
        self._inbound.put(_EOF)

    def close(self) -> None:
        self.events.append("closed")
        self.close_threads.append(threading.current_thread().name)
        self.closed.set()
        self._inbound.put(_EOF)


class FakeConnector:
    """``connect`` pops the next scripted outcome (a link or an exception),
    else None — the app is absent."""

    def __init__(self, *outcomes: Any) -> None:
        self._outcomes: queue.Queue[Any] = queue.Queue()
        for outcome in outcomes:
            self._outcomes.put(outcome)
        self.attempts = 0
        self.stopped = threading.Event()
        self._links: list[FakeLink] = []

    def script(self, outcome: Any) -> None:
        self._outcomes.put(outcome)

    def connect(self) -> Any:
        self.attempts += 1
        try:
            outcome = self._outcomes.get_nowait()
        except queue.Empty:
            return None
        if isinstance(outcome, BaseException):
            raise outcome
        if isinstance(outcome, FakeLink):
            self._links.append(outcome)
        return outcome

    def stop(self) -> None:
        # The real connector's stop event releases every connection's read.
        self.stopped.set()
        for link in self._links:
            link.release()


class HostRun:
    """``run_host`` on a thread, between a fake Chrome and ``connector``."""

    def __init__(self, logger: logging.Logger, connector: Any | None) -> None:
        self.stdin = ChromeStdin()
        self.stdout = ChromeSink()
        self.code: int | None = None

        def factory(out: ChromeOut, on_fatal: Callable[[], None], log: logging.Logger) -> AppRelay:
            return AppRelay(connector, out, log, on_fatal=on_fatal, retry_s=0.01)

        self._factory = factory if connector is not None else None
        self._thread = threading.Thread(target=self._run, args=(logger,), daemon=True)
        self._thread.start()

    def _run(self, logger: logging.Logger) -> None:
        stdin: Any = self.stdin  # a blocking reader, not a real BinaryIO
        self.code = run_host(stdin, self.stdout, logger, relay_factory=self._factory)

    def handshake(self) -> str:
        self.stdin.send(
            {
                "protocol_version": PROTOCOL_VERSION,
                "type": "hello",
                "request_id": "r1",
                "payload": {},
            }
        )
        frames = self.stdout.wait_for(lambda fs: any(f["type"] == "hello_ack" for f in fs))
        nonce = frames[0]["session_nonce"]
        assert isinstance(nonce, str)
        return nonce

    def finish(self, timeout: float = WAIT_S) -> int | None:
        self._thread.join(timeout)
        assert not self._thread.is_alive(), "the host did not exit"
        return self.code
