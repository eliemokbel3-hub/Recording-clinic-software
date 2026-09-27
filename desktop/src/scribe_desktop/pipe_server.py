"""The named pipe between the native host and ``scribe-app`` (Task 4.2).

Cliniko workflow safeguards plan Task 4.2 (D2, D4; Critical Constraint 10):
the host <-> app leg of the locked Phase 1 topology is a NAMED PIPE, never a
socket. ``scribe-app`` creates it; the native host (Task 4.4) connects to it.

THE PIPE, as created (``PipeServer.start``; every flag pinned by test):

- name ``\\\\.\\pipe\\ClinikoScribe-<user SID>`` (per Windows user);
- ``FILE_FLAG_FIRST_PIPE_INSTANCE`` (the literal ``0x00080000`` — pywin32 has
  no constant): creation FAILS if any process already holds the name, so the
  app never shares its name with a squatter (``PipeUnavailable``,
  ``name_taken``);
- ``nMaxInstances = 1``: one client at a time — a second connect waits (the
  client sees ``ERROR_PIPE_BUSY``) until the first has gone;
- ``PIPE_REJECT_REMOTE_CLIENTS``: no connection from another machine;
- a protected DACL from SDDL granting access to the current user's SID only
  (``D:P(A;;GA;;;<SID>)``) — no other account, no inherited entries.

What that does NOT stop, stated as the residue (Task 4.3 decided (b) on
2026-09-27: accepted as threat-model boundary 2, no peer gate): any process
running as the SAME Windows user can connect,
exactly as it can open the single-instance mutex (``app.py``). The DACL and
the flags keep other users and other machines out; they do not tell this
user's processes apart.

I/O: overlapped, with one stop event. A server thread waits for a client
(``ConnectNamedPipe``), then reads frames through ``_OverlappedReader`` — a
``ReadFile`` adapter whose ``read(n)`` returns what one read delivered, so
``framing.read_frame``'s short-read loops assemble each frame — and a writer
thread per connection writes frames from a latest-wins mailbox (the app only
ever sends full ``state`` snapshots, so an unsent older snapshot is safely
superseded). Every blocking wait also waits on the stop event, and each
thread cancels ONLY its own I/O (``CancelIo``; pywin32 has no
``CancelIoEx``).

Messages: every inbound frame is validated as a PIPE envelope
(``protocol.parse_pipe_envelope`` — ``context`` or ``command``, no nonce);
anything else is a fatal protocol fault and the connection is closed. The
server calls its ``PipeEvents`` from its own thread; the app's bridge
(``ui/bridge.py``) turns each call into a QUEUED Qt signal, so nothing here
touches the GUI or the session controller. Every new client gets a new
connection number; the bridge treats a new client as pipe loss and bumps
D4's ``conn_gen``.

Logging: whitelisted metadata only (a connection number and a close reason);
never a payload. Task 4.3's tripwire (decided (b), 2026-09-27): each
client's executable path is logged at connect (``pipe_peer``) — a path, as
the native host logs its own at startup; it gates nothing.
"""

from __future__ import annotations

import ctypes
import functools
import io
import logging
import re
import sys
import threading
from dataclasses import dataclass
from typing import Any, Final, Protocol

from pydantic import ValidationError

from scribe_desktop.framing import EndOfStream, FramingError, read_frame, write_frame
from scribe_desktop.logging_setup import log_event
from scribe_desktop.protocol import Envelope, parse_pipe_envelope

if sys.platform == "win32":
    import pywintypes
    import win32api
    import win32con
    import win32event
    import win32file
    import win32pipe
    import win32security

PIPE_PREFIX: Final = "\\\\.\\pipe\\ClinikoScribe-"

# CreateNamedPipe flags, as literals (pinned by test_pipe_server.py).
PIPE_ACCESS_DUPLEX: Final = 0x00000003
FILE_FLAG_OVERLAPPED: Final = 0x40000000
FILE_FLAG_FIRST_PIPE_INSTANCE: Final = 0x00080000
PIPE_TYPE_BYTE: Final = 0x00000000
PIPE_READMODE_BYTE: Final = 0x00000000
PIPE_WAIT: Final = 0x00000000
PIPE_REJECT_REMOTE_CLIENTS: Final = 0x00000008
OPEN_MODE: Final = PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED | FILE_FLAG_FIRST_PIPE_INSTANCE
PIPE_MODE: Final = PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS
MAX_INSTANCES: Final = 1
BUFFER_BYTES: Final = 65_536
# The types a client may send the app over the pipe (D2).
INBOUND_TYPES: Final = frozenset({"context", "command"})

# Win32 error codes (winerror.h).
_ERROR_ACCESS_DENIED: Final = 5
_ERROR_BROKEN_PIPE: Final = 109
_ERROR_PIPE_BUSY: Final = 231
_ERROR_NO_DATA: Final = 232
_ERROR_PIPE_NOT_CONNECTED: Final = 233
_ERROR_PIPE_CONNECTED: Final = 535
_ERROR_OPERATION_ABORTED: Final = 995
_PEER_GONE: Final = frozenset(
    {_ERROR_BROKEN_PIPE, _ERROR_NO_DATA, _ERROR_PIPE_NOT_CONNECTED, _ERROR_OPERATION_ABORTED}
)
_WAIT_OBJECT_0: Final = 0
_INFINITE: Final = 0xFFFFFFFF
_JOIN_TIMEOUT_S: Final = 5.0
_SID_RE: Final = re.compile(r"S-1-[0-9]+(-[0-9]+)+")
PROCESS_QUERY_LIMITED_INFORMATION: Final = 0x1000
_IMAGE_PATH_CHARS: Final = 32_768


class PipeUnavailable(Exception):
    """The pipe could not be created. ``reason`` is ``name_taken`` (another
    process holds the name — never shared) or ``create_failed``."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"the Chrome link pipe is unavailable ({reason})")
        self.reason = reason


class PipeEvents(Protocol):
    """What the server reports, from ITS OWN thread (the bridge queues each
    call to the GUI thread). ``conn_id`` numbers clients from 1."""

    def connected(self, conn_id: int) -> None: ...

    def message(self, conn_id: int, envelope: Envelope) -> None: ...

    def disconnected(self, conn_id: int, reason: str) -> None: ...


def current_user_sid() -> str:
    """The current Windows user's SID as a string (``S-1-5-21-...``);
    ``PipeUnavailable`` when it cannot be read."""
    try:
        token = win32security.OpenProcessToken(
            win32api.GetCurrentProcess(), win32con.TOKEN_QUERY
        )
        try:
            sid, _attributes = win32security.GetTokenInformation(
                token, win32security.TokenUser
            )
        finally:
            token.Close()
        text = str(win32security.ConvertSidToStringSid(sid))
    except pywintypes.error:
        raise PipeUnavailable("create_failed") from None
    if _SID_RE.fullmatch(text) is None:
        raise PipeUnavailable("create_failed")
    return text


def pipe_name(sid: str) -> str:
    """The per-user pipe name (plan Config Impact)."""
    if _SID_RE.fullmatch(sid) is None:
        raise ValueError("not a SID string")
    return f"{PIPE_PREFIX}{sid}"


def pipe_sddl(sid: str) -> str:
    """A PROTECTED DACL with one entry: full access for ``sid`` only."""
    if _SID_RE.fullmatch(sid) is None:
        raise ValueError("not a SID string")
    return f"D:P(A;;GA;;;{sid})"


# --- the process at the other end (Task 4.3's checks and tripwire) ----------


@functools.cache
def _kernel32() -> Any:
    """kernel32 with the prototypes the peer lookups use (pywin32 exposes
    none of these four calls)."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ulong_p = ctypes.POINTER(ctypes.c_ulong)
    for name in (
        "GetNamedPipeServerProcessId",
        "GetNamedPipeClientProcessId",
        "GetNamedPipeServerSessionId",
    ):
        function = getattr(kernel32, name)
        function.argtypes = [ctypes.c_void_p, ulong_p]
        function.restype = ctypes.c_int
    kernel32.ProcessIdToSessionId.argtypes = [ctypes.c_ulong, ulong_p]
    kernel32.ProcessIdToSessionId.restype = ctypes.c_int
    kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.QueryFullProcessImageNameW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_wchar_p,
        ulong_p,
    ]
    kernel32.QueryFullProcessImageNameW.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    return kernel32


def _ulong_call(function: Any, first: Any) -> int | None:
    value = ctypes.c_ulong(0)
    if not function(first, ctypes.byref(value)):
        return None
    return int(value.value)


def pipe_peer_pid(handle: Any, *, server: bool) -> int | None:
    """The process id at the other end of a connected pipe handle: the
    server's (``server=True``, asked by the client) or the client's; None
    when Windows will not say."""
    kernel32 = _kernel32()
    function = (
        kernel32.GetNamedPipeServerProcessId if server else kernel32.GetNamedPipeClientProcessId
    )
    return _ulong_call(function, int(handle))


def pipe_server_session_id(handle: Any) -> int | None:
    """The Windows (Terminal Services) session of a connected pipe's server
    process — the session, not the logon session: another account signed in
    to the same session shares it (round 57)."""
    return _ulong_call(_kernel32().GetNamedPipeServerSessionId, int(handle))


def process_session_id(pid: int) -> int | None:
    """The Windows (Terminal Services) session of process ``pid``."""
    return _ulong_call(_kernel32().ProcessIdToSessionId, pid)


def process_image_path(pid: int) -> str | None:
    """The executable path of process ``pid`` (limited query rights only);
    None when it cannot be read."""
    kernel32 = _kernel32()
    process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
    if not process:
        return None
    try:
        buffer = ctypes.create_unicode_buffer(_IMAGE_PATH_CHARS)
        size = ctypes.c_ulong(_IMAGE_PATH_CHARS)
        if not kernel32.QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(size)):
            return None
        return str(buffer.value)
    finally:
        kernel32.CloseHandle(process)


def process_user_sid(pid: int) -> str | None:
    """The user SID of process ``pid``'s token; None when it cannot be read
    (another user's process, or an elevated one, refuses the query)."""
    try:
        process = win32api.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    except pywintypes.error:
        return None
    try:
        token = win32security.OpenProcessToken(process, win32con.TOKEN_QUERY)
        try:
            sid, _attributes = win32security.GetTokenInformation(
                token, win32security.TokenUser
            )
        finally:
            token.Close()
        return str(win32security.ConvertSidToStringSid(sid))
    except pywintypes.error:
        return None
    finally:
        process.Close()


class _Stopped(Exception):
    """The server's stop event fired during a wait."""


def _cancel_own_io(handle: Any, overlapped: Any) -> None:
    """Cancel THIS thread's pending I/O on ``handle`` and wait for it to
    settle, so the buffer is no longer in the kernel's hands."""
    try:
        win32file.CancelIo(handle)
    except pywintypes.error:
        pass
    try:
        win32file.GetOverlappedResult(handle, overlapped, True)
    except pywintypes.error:
        pass


def _new_overlapped() -> Any:
    overlapped = pywintypes.OVERLAPPED()
    overlapped.hEvent = win32event.CreateEvent(None, True, False, None)
    return overlapped


class _OverlappedReader:
    """``read(n)`` for ``framing.read_frame``: ONE overlapped ``ReadFile`` of
    at most ``n`` bytes, returning what it delivered (possibly fewer — the
    framing loops assemble the rest), ``b""`` once the client has gone, and
    ``_Stopped`` when a stop event fires first (the host's connection also
    passes its own retire event, codex round 28 PR-MED-140/141)."""

    def __init__(self, handle: Any, stop_event: Any, *more_stops: Any) -> None:
        self._handle = handle
        self._stops = [stop_event, *more_stops]
        self._overlapped = _new_overlapped()

    def read(self, size: int) -> bytes:
        if size <= 0:
            return b""
        while True:
            win32event.ResetEvent(self._overlapped.hEvent)
            buffer = win32file.AllocateReadBuffer(size)
            try:
                win32file.ReadFile(self._handle, buffer, self._overlapped)
            except pywintypes.error as error:
                if error.winerror in _PEER_GONE:
                    return b""
                raise
            fired = win32event.WaitForMultipleObjects(
                [self._overlapped.hEvent, *self._stops], False, _INFINITE
            )
            if fired != _WAIT_OBJECT_0:
                _cancel_own_io(self._handle, self._overlapped)
                raise _Stopped()
            try:
                count = win32file.GetOverlappedResult(self._handle, self._overlapped, True)
            except pywintypes.error as error:
                if error.winerror in _PEER_GONE:
                    return b""
                raise
            if count > 0:
                return bytes(buffer[:count])
            # A zero-byte completion is not the end of the stream: read again.


@dataclass
class _Mailbox:
    """The latest unsent frame for the current connection (latest wins)."""

    conn_id: int | None = None
    frame: bytes | None = None


class PipeServer:
    """The app's end of the host <-> app pipe (see the module docstring)."""

    def __init__(
        self,
        name: str,
        events: PipeEvents,
        *,
        sddl: str,
        logger: logging.Logger | None = None,
    ) -> None:
        self._name = name
        self._events = events
        self._sddl = sddl
        self._logger = logger
        self._handle: Any = None
        self._stop_event: Any = None
        self._send_event: Any = None
        self._closed_event: Any = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._mailbox = _Mailbox()
        self._conn_counter = 0

    @classmethod
    def for_current_user(
        cls, events: PipeEvents, *, logger: logging.Logger | None = None
    ) -> PipeServer:
        sid = current_user_sid()
        return cls(pipe_name(sid), events, sddl=pipe_sddl(sid), logger=logger)

    @property
    def name(self) -> str:
        return self._name

    @property
    def running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    # --- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        """Create the pipe (synchronously — ``PipeUnavailable`` names why it
        failed) and start serving. Nothing here opens a socket."""
        if self._thread is not None:
            raise RuntimeError("the pipe server is already started")
        attributes = win32security.SECURITY_ATTRIBUTES()
        attributes.SECURITY_DESCRIPTOR = (
            win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
                self._sddl, win32security.SDDL_REVISION_1
            )
        )
        attributes.bInheritHandle = False
        try:
            self._handle = win32pipe.CreateNamedPipe(
                self._name,
                OPEN_MODE,
                PIPE_MODE,
                MAX_INSTANCES,
                BUFFER_BYTES,
                BUFFER_BYTES,
                0,
                attributes,
            )
        except pywintypes.error as error:
            if error.winerror in (_ERROR_ACCESS_DENIED, _ERROR_PIPE_BUSY):
                raise PipeUnavailable("name_taken") from None
            raise PipeUnavailable("create_failed") from None
        self._stop_event = win32event.CreateEvent(None, True, False, None)
        self._send_event = win32event.CreateEvent(None, False, False, None)
        self._closed_event = win32event.CreateEvent(None, True, False, None)
        self._thread = threading.Thread(target=self._serve, name="scribe-pipe-server", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = _JOIN_TIMEOUT_S) -> bool:
        """Stop serving and close the pipe. True once the server thread has
        exited (a connected client is disconnected first)."""
        thread = self._thread
        if thread is None:
            return True
        win32event.SetEvent(self._stop_event)
        thread.join(timeout)
        return not thread.is_alive()

    # --- sending (any thread) ------------------------------------------------

    def send(self, conn_id: int, envelope: Envelope) -> bool:
        """Queue ``envelope`` for connection ``conn_id``. False when that
        connection is no longer current (the frame is dropped: a frame meant
        for one client never reaches the next). A newer frame replaces an
        unsent older one."""
        buffer = io.BytesIO()
        write_frame(buffer, envelope.model_dump(exclude_none=True))
        with self._lock:
            if self._mailbox.conn_id != conn_id:
                return False
            self._mailbox.frame = buffer.getvalue()
        win32event.SetEvent(self._send_event)
        return True

    # --- the server thread ---------------------------------------------------

    def _log(self, event: str, **fields: Any) -> None:
        if self._logger is not None:
            log_event(self._logger, event, **fields)

    def _log_peer(self) -> None:
        """Task 4.3's tripwire: the connected client's executable path —
        never a frame, and it gates nothing."""
        if self._logger is None:
            return
        pid = pipe_peer_pid(self._handle, server=False)
        path = process_image_path(pid) if pid is not None else None
        if path is None:
            self._log("pipe_peer", state="unreadable")
        else:
            self._log("pipe_peer", path=path)

    def _serve(self) -> None:
        try:
            while True:
                if not self._await_client():
                    return
                self._conn_counter += 1
                conn_id = self._conn_counter
                win32event.ResetEvent(self._closed_event)
                with self._lock:
                    self._mailbox = _Mailbox(conn_id=conn_id)
                writer = threading.Thread(
                    target=self._write_loop, args=(conn_id,), name="scribe-pipe-writer", daemon=True
                )
                writer.start()
                self._log("pipe_client", state="connected", count=conn_id)
                self._log_peer()
                self._events.connected(conn_id)
                reason = self._read_loop(conn_id)
                win32event.SetEvent(self._closed_event)
                writer.join(_JOIN_TIMEOUT_S)
                with self._lock:
                    self._mailbox = _Mailbox()
                try:
                    win32pipe.DisconnectNamedPipe(self._handle)
                except pywintypes.error:
                    pass
                self._log("pipe_client", state=reason, count=conn_id)
                self._events.disconnected(conn_id, reason)
                if reason == "stopped":
                    return
        finally:
            try:
                win32file.CloseHandle(self._handle)
            except pywintypes.error:
                pass

    def _await_client(self) -> bool:
        """Wait for a client. False when the stop event fires first."""
        overlapped = _new_overlapped()
        try:
            result = win32pipe.ConnectNamedPipe(self._handle, overlapped)
        except pywintypes.error as error:
            # NO_DATA: a client came and went before this call — served like
            # the overlapped case below (the read loop sees it gone), never an
            # end of the server that would free the name (round 57 SEC-002).
            if error.winerror in (_ERROR_PIPE_CONNECTED, _ERROR_NO_DATA):
                return True
            self._log("pipe_server", state="connect_failed", error_code=str(error.winerror))
            return False
        if result == _ERROR_PIPE_CONNECTED:
            return True
        fired = win32event.WaitForMultipleObjects(
            [overlapped.hEvent, self._stop_event], False, _INFINITE
        )
        if fired != _WAIT_OBJECT_0:
            _cancel_own_io(self._handle, overlapped)
            return False
        try:
            win32file.GetOverlappedResult(self._handle, overlapped, True)
        except pywintypes.error as error:
            if error.winerror != _ERROR_NO_DATA:
                self._log("pipe_server", state="connect_failed", error_code=str(error.winerror))
                return False
            # The client came and went: the read loop sees it gone at once.
        return True

    def _read_loop(self, conn_id: int) -> str:
        reader = _OverlappedReader(self._handle, self._stop_event)
        while True:
            try:
                raw = read_frame(reader)
            except EndOfStream:
                return "closed"
            except _Stopped:
                return "stopped"
            except FramingError:
                return "framing"
            except pywintypes.error:
                return "io_error"
            try:
                envelope = parse_pipe_envelope(raw)
            except ValidationError:
                return "malformed"
            if envelope.type not in INBOUND_TYPES:
                return "unexpected_type"
            self._events.message(conn_id, envelope)

    def _write_loop(self, conn_id: int) -> None:
        overlapped = _new_overlapped()
        waits = [self._send_event, self._closed_event, self._stop_event]
        while True:
            fired = win32event.WaitForMultipleObjects(waits, False, _INFINITE)
            if fired != _WAIT_OBJECT_0:
                return
            with self._lock:
                frame = self._mailbox.frame if self._mailbox.conn_id == conn_id else None
                self._mailbox.frame = None
            if frame is None:
                continue
            win32event.ResetEvent(overlapped.hEvent)
            try:
                win32file.WriteFile(self._handle, frame, overlapped)
            except pywintypes.error:
                return  # the client has gone: the reader sees it too
            done = win32event.WaitForMultipleObjects(
                [overlapped.hEvent, self._closed_event, self._stop_event], False, _INFINITE
            )
            if done != _WAIT_OBJECT_0:
                _cancel_own_io(self._handle, overlapped)
                return
            try:
                win32file.GetOverlappedResult(self._handle, overlapped, True)
            except pywintypes.error:
                return
