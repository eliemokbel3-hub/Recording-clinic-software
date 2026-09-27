"""The native host's end of the host <-> app pipe (Task 4.4).

Cliniko workflow safeguards plan Task 4.4 (D2), on Task 4.3's connect
contract — decided (b) on 2026-09-27: the logon session plus the user-only
DACL, with the same-user residue accepted as threat-model boundary 2.

CONNECT. ``AppPipeConnector.connect`` makes one bounded attempt: a
``WaitNamedPipe`` of at most ``WAIT_MS``, then ``CreateFile`` with
``SECURITY_SQOS_PRESENT | SECURITY_IDENTIFICATION`` (the server may learn
who the host is but can never impersonate it) and overlapped I/O. An absent
or busy pipe is ``None`` — the caller keeps re-waiting; nothing here exits.

VERIFIED means ALL of the following, read from the connected handle before a
single frame crosses (``unverified_reason``):

1. the server process runs in the host's own Windows logon session
   (``GetNamedPipeServerSessionId`` equals ``ProcessIdToSessionId`` of the
   host);
2. the server process's token user is the host's own user SID;
3. the pipe's DACL is the one ``scribe-app`` creates (``pipe_server.pipe_sddl``):
   protected, exactly one entry, an ALLOW for the host's user SID with no ACE
   flags and the full access ``GA`` grants (codex round 28 PR-LOW-142: the
   flags and the mask are compared too, not only the type and the SID).

A pipe that exists but fails any of these — including one whose check cannot
be made (a server whose token the host may not query), or one whose DACL
denies the host outright — is ``ServerUnverified``: a hard error, never a
retry and never a relay. What "verified" does NOT establish: WHICH of this
user's programs is the server (two processes of the same user are
indistinguishable here — the accepted residue, threat model "The Chrome
link").

Task 4.3's tripwire: the server's executable path is logged at connect
(``pipe_peer``), as the host logs its own at startup; it gates nothing.
"""

from __future__ import annotations

import io
import logging
import os
import sys
import threading
from dataclasses import dataclass
from typing import Any, Final

from scribe_desktop.framing import EndOfStream, FramingError, read_frame, write_frame
from scribe_desktop.logging_setup import log_event
from scribe_desktop.pipe_server import (
    PipeUnavailable,
    _cancel_own_io,
    _new_overlapped,
    _OverlappedReader,
    _Stopped,
    current_user_sid,
    pipe_name,
    pipe_peer_pid,
    pipe_server_session_id,
    process_image_path,
    process_session_id,
    process_user_sid,
)

if sys.platform == "win32":
    import pywintypes
    import win32con
    import win32event
    import win32file
    import win32pipe
    import win32security

FILE_FLAG_OVERLAPPED: Final = 0x40000000
SECURITY_SQOS_PRESENT: Final = 0x00100000
SECURITY_IDENTIFICATION: Final = 0x00010000
OPEN_FLAGS: Final = FILE_FLAG_OVERLAPPED | SECURITY_SQOS_PRESENT | SECURITY_IDENTIFICATION
# One bounded WaitNamedPipe per attempt (plan Task 4.4).
WAIT_MS: Final = 1_000
WRITE_TIMEOUT_MS: Final = 5_000
SE_DACL_PROTECTED: Final = 0x1000
ACCESS_ALLOWED_ACE_TYPE: Final = 0
# The one ACE ``pipe_sddl`` writes, ``(A;;GA;;;<SID>)``: no ACE flags, and
# ``GA`` — stored mapped to FILE_ALL_ACCESS when Windows creates the pipe
# (GENERIC_ALL is accepted too, the same grant left unmapped). The real
# app-created pipe passing is pinned by test_pipe_client.py.
APP_ACE_FLAGS: Final = 0
FILE_ALL_ACCESS: Final = 0x001F01FF
GENERIC_ALL: Final = 0x10000000
APP_ACE_MASKS: Final = frozenset({FILE_ALL_ACCESS, GENERIC_ALL})

_ERROR_ACCESS_DENIED: Final = 5
_WAIT_OBJECT_0: Final = 0


class ServerUnverified(Exception):
    """The pipe exists but its server is not verified (see the module
    docstring). ``reason``: ``session``, ``user``, ``dacl``,
    ``access_denied`` or ``own_identity``."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"the app's pipe failed verification ({reason})")
        self.reason = reason


@dataclass(frozen=True)
class ServerIdentity:
    """What the host could read about the pipe's server (None: unreadable)."""

    session_id: int | None
    user_sid: str | None
    dacl_protected: bool
    # (ACE type, ACE flags, access mask, SID string)
    dacl_entries: tuple[tuple[int, int, int, str], ...]


def unverified_reason(identity: ServerIdentity, *, own_session: int, own_sid: str) -> str | None:
    """The first check ``identity`` fails, or None when the server is
    verified. Pure: the whole connect contract in one place."""
    if identity.session_id is None or identity.session_id != own_session:
        return "session"
    if identity.user_sid is None or identity.user_sid != own_sid:
        return "user"
    entries = identity.dacl_entries
    if not identity.dacl_protected or len(entries) != 1:
        return "dacl"
    ace_type, ace_flags, mask, sid = entries[0]
    if (
        ace_type != ACCESS_ALLOWED_ACE_TYPE
        or ace_flags != APP_ACE_FLAGS
        or mask not in APP_ACE_MASKS
        or sid != own_sid
    ):
        return "dacl"
    return None


def _pipe_dacl(handle: Any) -> tuple[bool, tuple[tuple[int, int, int, str], ...]]:
    try:
        descriptor = win32security.GetSecurityInfo(
            handle, win32security.SE_KERNEL_OBJECT, win32security.DACL_SECURITY_INFORMATION
        )
        control, _revision = descriptor.GetSecurityDescriptorControl()
        dacl = descriptor.GetSecurityDescriptorDacl()
        if dacl is None:  # a NULL DACL grants everyone everything
            return False, ()
        entries = []
        for index in range(dacl.GetAceCount()):
            (ace_type, ace_flags), mask, sid = dacl.GetAce(index)
            entries.append(
                (
                    int(ace_type),
                    int(ace_flags),
                    int(mask) & 0xFFFFFFFF,  # pywin32 may hand back a signed value
                    str(win32security.ConvertSidToStringSid(sid)),
                )
            )
    except (pywintypes.error, TypeError, ValueError):
        return False, ()
    return bool(control & SE_DACL_PROTECTED), tuple(entries)


def read_server_identity(handle: Any) -> ServerIdentity:
    """Read the three facts ``unverified_reason`` judges from a connected
    client handle. Never raises: an unreadable fact is None / empty."""
    pid = pipe_peer_pid(handle, server=True)
    protected, entries = _pipe_dacl(handle)
    return ServerIdentity(
        session_id=pipe_server_session_id(handle),
        user_sid=process_user_sid(pid) if pid is not None else None,
        dacl_protected=protected,
        dacl_entries=entries,
    )


class PipeConnection:
    """A verified connection to the app. ``read_frame`` blocks on the relay
    thread until a frame, the app going away (``EndOfStream``), the
    connector's stop or this connection's ``retire``; ``write_frame`` is
    bounded and may run on another thread (overlapped I/O: a pending read
    never blocks a write).

    Codex round 28 PR-MED-140/141: only the READING thread closes the
    handle, after its read has settled. Another thread ends the connection
    with ``retire`` (a failed write) or the connector's ``stop`` — each an
    event the read waits on — and never with ``close``. Once either event is
    set, ``write_frame`` refuses BEFORE issuing any I/O (codex round 30
    PR-MED-161), so nothing follows a possibly partial frame on the stream."""

    def __init__(self, handle: Any, stop_event: Any) -> None:
        self._handle = handle
        self._stop = stop_event
        self._retire = win32event.CreateEvent(None, True, False, None)
        self._reader = _OverlappedReader(handle, stop_event, self._retire)
        self._lock = threading.Lock()
        self._closed = False

    def retire(self) -> None:
        """End this connection from another thread: the pending read
        settles and ends (``EndOfStream``), and its thread closes it."""
        win32event.SetEvent(self._retire)

    def _ended(self) -> bool:
        """Retired or stopped (either event already set). ``retire`` stays a
        lock-free ``SetEvent`` so a write blocked in its wait still sees it;
        the one writer is also the one retirer (the host's main thread), so
        this check-then-write has no interleaving to lose."""
        return any(
            win32event.WaitForSingleObject(event, 0) == _WAIT_OBJECT_0
            for event in (self._retire, self._stop)
        )

    def read_frame(self) -> Any:
        try:
            return read_frame(self._reader)
        except _Stopped:
            raise EndOfStream() from None
        except pywintypes.error:
            raise EndOfStream() from None

    def write_frame(self, value: Any) -> bool:
        buffer = io.BytesIO()
        try:
            write_frame(buffer, value)
        except FramingError:
            return False
        with self._lock:
            if self._closed or self._ended():
                return False
            overlapped = _new_overlapped()
            try:
                win32file.WriteFile(self._handle, buffer.getvalue(), overlapped)
            except pywintypes.error:
                return False
            fired = win32event.WaitForMultipleObjects(
                [overlapped.hEvent, self._stop, self._retire], False, WRITE_TIMEOUT_MS
            )
            if fired != _WAIT_OBJECT_0:
                _cancel_own_io(self._handle, overlapped)
                return False
            try:
                win32file.GetOverlappedResult(self._handle, overlapped, True)
            except pywintypes.error:
                return False
            return True

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            try:
                win32file.CloseHandle(self._handle)
            except pywintypes.error:
                pass


class AppPipeConnector:
    """The host's connector (the relay's ``Connector``): one bounded attempt
    per ``connect``; ``stop`` releases a blocked read at once."""

    def __init__(
        self,
        name: str,
        *,
        own_sid: str | None = None,
        wait_ms: int = WAIT_MS,
        logger: logging.Logger | None = None,
    ) -> None:
        self._name = name
        self._own_sid = own_sid
        self._wait_ms = wait_ms
        self._logger = logger
        self._stop_event = win32event.CreateEvent(None, True, False, None)

    @classmethod
    def for_current_user(cls, *, logger: logging.Logger | None = None) -> AppPipeConnector:
        """The per-user pipe ``scribe-app`` creates. The user SID is read
        once here; an unreadable one makes every connect a hard error."""
        try:
            sid: str | None = current_user_sid()
        except PipeUnavailable:
            sid = None
        name = pipe_name(sid) if sid is not None else "\\\\.\\pipe\\ClinikoScribe-unknown"
        return cls(name, own_sid=sid, logger=logger)

    def _identity(self) -> tuple[int, str]:
        own_sid = self._own_sid
        if own_sid is None:
            try:
                own_sid = current_user_sid()
            except PipeUnavailable:
                raise ServerUnverified("own_identity") from None
            self._own_sid = own_sid
        own_session = process_session_id(os.getpid())
        if own_session is None:
            raise ServerUnverified("own_identity")
        return own_session, own_sid

    def connect(self) -> PipeConnection | None:
        """One attempt: a verified connection, None when the pipe is absent
        or busy, or ``ServerUnverified``."""
        own_session, own_sid = self._identity()
        try:
            win32pipe.WaitNamedPipe(self._name, self._wait_ms)
        except pywintypes.error:
            # Absent (ERROR_FILE_NOT_FOUND), busy past the wait
            # (ERROR_SEM_TIMEOUT) or any other wait failure: not now.
            return None
        try:
            handle = win32file.CreateFile(
                self._name,
                win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                0,
                None,
                win32con.OPEN_EXISTING,
                OPEN_FLAGS,
                None,
            )
        except pywintypes.error as error:
            if error.winerror == _ERROR_ACCESS_DENIED:
                # The name exists but its DACL shuts this user out: not
                # the pipe scribe-app makes.
                raise ServerUnverified("access_denied") from None
            # Gone between the wait and the open (ERROR_FILE_NOT_FOUND),
            # taken by another client (ERROR_PIPE_BUSY), or any other
            # open failure: not now.
            return None
        identity = read_server_identity(handle)
        reason = unverified_reason(identity, own_session=own_session, own_sid=own_sid)
        if reason is not None:
            try:
                win32file.CloseHandle(handle)
            except pywintypes.error:
                pass
            raise ServerUnverified(reason)
        self._log_peer(handle)
        return PipeConnection(handle, self._stop_event)

    def _log_peer(self, handle: Any) -> None:
        if self._logger is None:
            return
        pid = pipe_peer_pid(handle, server=True)
        path = process_image_path(pid) if pid is not None else None
        if path is None:
            log_event(self._logger, "pipe_peer", state="unreadable")
        else:
            log_event(self._logger, "pipe_peer", path=path)

    def stop(self) -> None:
        win32event.SetEvent(self._stop_event)
