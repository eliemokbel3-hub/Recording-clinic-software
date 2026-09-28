"""Task 4.2: the app's named-pipe server (``pipe_server.py``).

Real named pipes, each with a unique test name — a named pipe is not a
socket, and nothing here touches the network or the real per-user pipe name
(so a running ``scribe-app`` on this machine is never disturbed). The pinned
facts: the hardening flags and the user-only DACL; a held name is refused,
never shared; one client at a time; framing over short reads; a new client
gets a new connection number; anything but a nonce-free ``context`` or
``command`` closes the connection; a frame meant for one connection never
reaches the next; stop is prompt in every state.
"""

from __future__ import annotations

import json
import struct
import sys
import threading
import time
import uuid
from typing import Any

import pytest

from scribe_desktop.protocol import PROTOCOL_VERSION, Envelope, make_pipe_envelope

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows named pipes")

if sys.platform == "win32":
    import pywintypes
    import win32con
    import win32event
    import win32file
    import win32security

    from scribe_desktop import pipe_server
    from scribe_desktop.pipe_server import (
        FILE_FLAG_FIRST_PIPE_INSTANCE,
        MAX_INSTANCES,
        OPEN_MODE,
        PIPE_MODE,
        PIPE_REJECT_REMOTE_CLIENTS,
        PipeServer,
        PipeUnavailable,
        current_user_sid,
        pipe_name,
        pipe_sddl,
    )

WAIT_S = 10.0
CONTEXT = {
    "seq": 1,
    "tab_id": 7,
    "window_id": 1,
    "focused": True,
    "page": "note",
    "host": "example-clinic.au1.cliniko.com",
    "patient_id": "1001",
    "note_id": "2002",
}
STATE = {
    "state_rev": 1,
    "app_running": True,
    "allow_list": ["example-clinic.au1.cliniko.com"],
    "hotkey": {"available": False},
    "spoken_pause": False,
    "warnings": [],
}


def _frame(value: object) -> bytes:
    body = json.dumps(value).encode("utf-8")
    return struct.pack("=I", len(body)) + body


def _pipe_message(message_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"protocol_version": PROTOCOL_VERSION, "type": message_type, "payload": payload}


class Recorder:
    """Thread-safe record of the server's calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, int, object]] = []
        self._cond = threading.Condition()

    def connected(self, conn_id: int) -> None:
        self._add(("connected", conn_id, None))

    def message(self, conn_id: int, envelope: Envelope) -> None:
        self._add(("message", conn_id, envelope))

    def disconnected(self, conn_id: int, reason: str) -> None:
        self._add(("disconnected", conn_id, reason))

    def _add(self, call: tuple[str, int, object]) -> None:
        with self._cond:
            self.calls.append(call)
            self._cond.notify_all()

    def wait_for(self, kind: str, count: int = 1) -> list[tuple[str, int, object]]:
        deadline = time.monotonic() + WAIT_S
        with self._cond:
            while True:
                found = [c for c in self.calls if c[0] == kind]
                if len(found) >= count:
                    return found
                remaining = deadline - time.monotonic()
                assert remaining > 0, f"timed out waiting for {count} {kind}: {self.calls}"
                self._cond.wait(remaining)


class Client:
    """A test client: overlapped I/O with bounded waits, so a failing test
    never hangs the suite."""

    def __init__(self, name: str) -> None:
        self.handle = win32file.CreateFile(
            name,
            win32con.GENERIC_READ | win32con.GENERIC_WRITE,
            0,
            None,
            win32con.OPEN_EXISTING,
            win32con.FILE_FLAG_OVERLAPPED,
            None,
        )

    def write(self, data: bytes) -> None:
        overlapped = pywintypes.OVERLAPPED()
        overlapped.hEvent = win32event.CreateEvent(None, True, False, None)
        win32file.WriteFile(self.handle, data, overlapped)
        assert win32event.WaitForSingleObject(overlapped.hEvent, int(WAIT_S * 1000)) == 0
        win32file.GetOverlappedResult(self.handle, overlapped, True)

    def read_exact(self, size: int) -> bytes:
        chunks = b""
        while len(chunks) < size:
            overlapped = pywintypes.OVERLAPPED()
            overlapped.hEvent = win32event.CreateEvent(None, True, False, None)
            buffer = win32file.AllocateReadBuffer(size - len(chunks))
            win32file.ReadFile(self.handle, buffer, overlapped)
            if win32event.WaitForSingleObject(overlapped.hEvent, int(WAIT_S * 1000)) != 0:
                win32file.CancelIo(self.handle)
                raise AssertionError("timed out reading from the pipe")
            count = win32file.GetOverlappedResult(self.handle, overlapped, True)
            chunks += bytes(buffer[:count])
        return chunks

    def read_frame(self) -> dict[str, Any]:
        (length,) = struct.unpack("=I", self.read_exact(4))
        value = json.loads(self.read_exact(length).decode("utf-8"))
        assert isinstance(value, dict)
        return value

    def close(self) -> None:
        win32file.CloseHandle(self.handle)


def _connect(name: str) -> Client:
    deadline = time.monotonic() + WAIT_S
    while True:
        try:
            return Client(name)
        except pywintypes.error as error:
            if error.winerror not in (2, 231) or time.monotonic() > deadline:
                raise
            time.sleep(0.02)  # not yet created, or busy: retry briefly


@pytest.fixture
def name() -> str:
    return f"\\\\.\\pipe\\ClinikoScribe-test-{uuid.uuid4().hex}"


@pytest.fixture
def server(name: str) -> Any:
    recorder = Recorder()
    server = PipeServer(name, recorder, sddl=pipe_sddl(current_user_sid()))
    server.start()
    server.recorder = recorder  # type: ignore[attr-defined]
    yield server
    assert server.stop(), "the pipe server did not stop in time"


# --- the hardening flags and the DACL ------------------------------------------


class TestHardening:
    def test_the_flags_are_pinned(self) -> None:
        assert FILE_FLAG_FIRST_PIPE_INSTANCE == 0x00080000
        assert OPEN_MODE & FILE_FLAG_FIRST_PIPE_INSTANCE
        assert OPEN_MODE & 0x40000000  # FILE_FLAG_OVERLAPPED
        assert OPEN_MODE & 0x3 == 0x3  # PIPE_ACCESS_DUPLEX
        assert PIPE_REJECT_REMOTE_CLIENTS == 0x00000008
        assert PIPE_MODE & PIPE_REJECT_REMOTE_CLIENTS
        assert MAX_INSTANCES == 1

    def test_create_named_pipe_receives_exactly_those_flags(
        self, monkeypatch: pytest.MonkeyPatch, name: str
    ) -> None:
        seen: list[tuple[Any, ...]] = []

        def spy(*args: Any) -> Any:
            seen.append(args)
            raise pywintypes.error(5, "CreateNamedPipe", "stopped by the test")

        monkeypatch.setattr(pipe_server.win32pipe, "CreateNamedPipe", spy)
        server = PipeServer(name, Recorder(), sddl=pipe_sddl(current_user_sid()))
        with pytest.raises(PipeUnavailable):
            server.start()
        (args,) = seen
        assert args[:4] == (name, OPEN_MODE, PIPE_MODE, MAX_INSTANCES)
        assert not args[7].bInheritHandle

    def test_the_dacl_grants_the_current_user_only(self, server: Any) -> None:
        descriptor = win32security.GetSecurityInfo(
            server._handle,
            win32security.SE_KERNEL_OBJECT,
            win32security.DACL_SECURITY_INFORMATION,
        )
        dacl = descriptor.GetSecurityDescriptorDacl()
        assert dacl.GetAceCount() == 1
        (_ace_type, _flags), _mask, sid = dacl.GetAce(0)
        assert win32security.ConvertSidToStringSid(sid) == current_user_sid()

    def test_the_sddl_is_protected_and_single_entry(self) -> None:
        sid = current_user_sid()
        assert pipe_sddl(sid) == f"O:{sid}D:P(A;;GA;;;{sid})"
        assert pipe_name(sid) == f"\\\\.\\pipe\\ClinikoScribe-{sid}"

    @pytest.mark.parametrize("bad", ["", "S-1", "S-1-5-21-1;(A;;GA;;;WD)", "not-a-sid"])
    def test_a_malformed_sid_is_refused(self, bad: str) -> None:
        with pytest.raises(ValueError):
            pipe_sddl(bad)
        with pytest.raises(ValueError):
            pipe_name(bad)

    def test_a_held_name_is_refused_never_shared(self, server: Any, name: str) -> None:
        second = PipeServer(name, Recorder(), sddl=pipe_sddl(current_user_sid()))
        with pytest.raises(PipeUnavailable) as caught:
            second.start()
        assert caught.value.reason == "name_taken"


# --- connections and messages ------------------------------------------------


class TestConnections:
    def test_a_client_connects_and_its_context_arrives_parsed(self, server: Any, name: str) -> None:
        client = _connect(name)
        try:
            assert server.recorder.wait_for("connected") == [("connected", 1, None)]
            client.write(_frame(_pipe_message("context", CONTEXT)))
            ((_, conn_id, envelope),) = server.recorder.wait_for("message")
            assert conn_id == 1
            assert isinstance(envelope, Envelope)
            assert envelope.type == "context" and envelope.session_nonce is None
            assert envelope.payload["note_id"] == "2002"
        finally:
            client.close()
        assert server.recorder.wait_for("disconnected") == [("disconnected", 1, "closed")]

    def test_a_frame_split_across_short_writes_is_assembled(self, server: Any, name: str) -> None:
        client = _connect(name)
        try:
            server.recorder.wait_for("connected")
            data = _frame(_pipe_message("context", CONTEXT))
            for piece in (data[:2], data[2:9], data[9:]):
                client.write(piece)
                time.sleep(0.05)
            ((_, _, envelope),) = server.recorder.wait_for("message")
            assert envelope.payload == CONTEXT
        finally:
            client.close()

    def test_the_app_sends_state_to_the_current_client(self, server: Any, name: str) -> None:
        client = _connect(name)
        try:
            server.recorder.wait_for("connected")
            assert server.send(1, make_pipe_envelope("state", payload=STATE))
            frame = client.read_frame()
            assert frame["type"] == "state" and "session_nonce" not in frame
            assert frame["payload"] == STATE
        finally:
            client.close()

    def test_a_frame_for_an_old_connection_never_reaches_the_next(
        self, server: Any, name: str
    ) -> None:
        first = _connect(name)
        server.recorder.wait_for("connected")
        first.close()
        server.recorder.wait_for("disconnected")
        assert not server.send(1, make_pipe_envelope("state", payload=STATE))
        second = _connect(name)
        try:
            assert server.recorder.wait_for("connected", 2)[-1] == ("connected", 2, None)
            assert server.send(2, make_pipe_envelope("state", payload={**STATE, "state_rev": 2}))
            assert client_state_rev(second) == 2  # never the old connection's frame
        finally:
            second.close()

    def test_one_client_at_a_time(self, server: Any, name: str) -> None:
        first = _connect(name)
        try:
            server.recorder.wait_for("connected")
            with pytest.raises(pywintypes.error) as caught:
                Client(name)
            assert caught.value.winerror == 231  # ERROR_PIPE_BUSY
        finally:
            first.close()

    def test_each_new_client_gets_a_new_connection_number(self, server: Any, name: str) -> None:
        for expected in (1, 2, 3):
            client = _connect(name)
            server.recorder.wait_for("connected", expected)
            client.close()
            server.recorder.wait_for("disconnected", expected)
        assert [c[1] for c in server.recorder.calls if c[0] == "connected"] == [1, 2, 3]


def client_state_rev(client: Client) -> int:
    frame = client.read_frame()
    value = frame["payload"]["state_rev"]
    assert isinstance(value, int)
    return value


# --- protocol faults close the connection ---------------------------------------


class TestFaults:
    @pytest.mark.parametrize(
        ("message", "reason"),
        [
            # a nonce never crosses the pipe (the host strips it)
            (
                {**_pipe_message("context", CONTEXT), "session_nonce": "n" * 32},
                "malformed",
            ),
            # the handshake stays between Chrome and the host
            (_pipe_message("hello", {}), "malformed"),
            # the app never accepts a state from its client
            (_pipe_message("state", STATE), "unexpected_type"),
            # an invalid payload (a leading-zero id)
            (_pipe_message("context", {**CONTEXT, "patient_id": "0123"}), "malformed"),
        ],
    )
    def test_a_fault_closes_the_connection(
        self, server: Any, name: str, message: dict[str, Any], reason: str
    ) -> None:
        client = _connect(name)
        try:
            server.recorder.wait_for("connected")
            client.write(_frame(message))
            assert server.recorder.wait_for("disconnected") == [("disconnected", 1, reason)]
            assert not [c for c in server.recorder.calls if c[0] == "message"]
        finally:
            client.close()

    def test_an_oversized_declared_length_closes_it_unread(self, server: Any, name: str) -> None:
        client = _connect(name)
        try:
            server.recorder.wait_for("connected")
            client.write(struct.pack("=I", 0xFFFF_FFF0))
            assert server.recorder.wait_for("disconnected") == [("disconnected", 1, "framing")]
        finally:
            client.close()

    def test_the_server_waits_for_the_next_client_after_a_fault(
        self, server: Any, name: str
    ) -> None:
        bad = _connect(name)
        server.recorder.wait_for("connected")
        bad.write(_frame(_pipe_message("hello", {})))
        server.recorder.wait_for("disconnected")
        bad.close()
        good = _connect(name)
        try:
            assert server.recorder.wait_for("connected", 2)[-1] == ("connected", 2, None)
        finally:
            good.close()

    def test_a_client_gone_before_the_connect_call_does_not_end_the_server(
        self, monkeypatch: pytest.MonkeyPatch, name: str
    ) -> None:
        # Round 57 SEC-002: ConnectNamedPipe raising ERROR_NO_DATA (a client
        # that connected and closed before the call) is served like the
        # overlapped case — the server waits on for the next client instead
        # of returning and freeing the name.
        real = pipe_server.win32pipe.ConnectNamedPipe
        calls: list[int] = []

        def gone_once(handle: Any, overlapped: Any) -> Any:
            calls.append(1)
            if len(calls) == 1:
                raise pywintypes.error(232, "ConnectNamedPipe", "the client came and went")
            return real(handle, overlapped)

        monkeypatch.setattr(pipe_server.win32pipe, "ConnectNamedPipe", gone_once)
        recorder = Recorder()
        server = PipeServer(name, recorder, sddl=pipe_sddl(current_user_sid()))
        server.start()
        try:
            recorder.wait_for("disconnected")
            good = _connect(name)
            try:
                assert recorder.wait_for("connected", 2)[-1] == ("connected", 2, None)
            finally:
                good.close()
        finally:
            assert server.stop(), "the pipe server did not stop in time"


# --- stopping --------------------------------------------------------------------


class TestStop:
    def test_stop_while_waiting_for_a_client(self, name: str) -> None:
        server = PipeServer(name, Recorder(), sddl=pipe_sddl(current_user_sid()))
        server.start()
        assert server.running
        started = time.monotonic()
        assert server.stop()
        assert time.monotonic() - started < WAIT_S
        assert not server.running

    def test_stop_while_a_client_is_connected(self, name: str) -> None:
        recorder = Recorder()
        server = PipeServer(name, recorder, sddl=pipe_sddl(current_user_sid()))
        server.start()
        client = _connect(name)
        try:
            recorder.wait_for("connected")
            assert server.stop()
            assert recorder.wait_for("disconnected") == [("disconnected", 1, "stopped")]
        finally:
            client.close()

    def test_the_name_is_free_again_after_stop(self, name: str) -> None:
        first = PipeServer(name, Recorder(), sddl=pipe_sddl(current_user_sid()))
        first.start()
        assert first.stop()
        second = PipeServer(name, Recorder(), sddl=pipe_sddl(current_user_sid()))
        second.start()
        assert second.stop()

    def test_stop_before_start_is_a_no_op(self, name: str) -> None:
        assert PipeServer(name, Recorder(), sddl=pipe_sddl(current_user_sid())).stop()


def test_the_current_user_sid_is_a_sid_string() -> None:
    sid = current_user_sid()
    assert sid.startswith("S-1-")
    assert pipe_name(sid).startswith("\\\\.\\pipe\\ClinikoScribe-S-1-")
