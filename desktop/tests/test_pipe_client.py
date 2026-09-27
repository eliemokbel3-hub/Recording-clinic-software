"""Task 4.4: the native host's pipe client (``pipe_client.py``) on Task 4.3's
connect contract — decided (b), 2026-09-27: the logon session, the user and
the user-only DACL are checked before a frame crosses, and a pipe that exists
but fails any check is a hard error.

The contract itself is a pure function (``unverified_reason``), pinned as a
table on every platform. The Win32 legs use REAL named pipes with unique
test names — never the real per-user name, so a running ``scribe-app`` is
never touched — and a named pipe is not a socket."""

from __future__ import annotations

import os
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import pytest

from relay_fakes import (
    CONTEXT_PAYLOAD,
    STATE_PAYLOAD,
    HostRun,
    chrome_message,
    pipe_message,
)
from scribe_desktop.framing import EndOfStream
from scribe_desktop.pipe_client import (
    ACCESS_ALLOWED_ACE_TYPE,
    APP_ACE_MASKS,
    FILE_ALL_ACCESS,
    GENERIC_ALL,
    OPEN_FLAGS,
    SECURITY_IDENTIFICATION,
    SECURITY_SQOS_PRESENT,
    ServerIdentity,
    unverified_reason,
)
from scribe_desktop.protocol import make_pipe_envelope

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="Windows named pipes")

if sys.platform == "win32":
    import pywintypes
    import win32file
    import win32pipe
    import win32security

    from scribe_desktop import pipe_client
    from scribe_desktop.logging_setup import setup_logging
    from scribe_desktop.pipe_client import (
        AppPipeConnector,
        ServerUnverified,
        read_server_identity,
    )
    from scribe_desktop.pipe_server import (
        MAX_INSTANCES,
        OPEN_MODE,
        PIPE_MODE,
        PipeServer,
        current_user_sid,
        pipe_sddl,
        process_image_path,
        process_session_id,
    )
    from test_pipe_server import Recorder

OWN_SID = "S-1-5-21-1-2-3-1001"
OTHER_SID = "S-1-5-21-1-2-3-1002"
WAIT_S = 10.0


def _identity(**overrides: Any) -> ServerIdentity:
    fields: dict[str, Any] = {
        "session_id": 1,
        "user_sid": OWN_SID,
        "dacl_protected": True,
        "dacl_entries": ((ACCESS_ALLOWED_ACE_TYPE, 0, FILE_ALL_ACCESS, OWN_SID),),
    }
    fields.update(overrides)
    return ServerIdentity(**fields)


class TestContract:
    """``unverified_reason`` IS the (b) contract."""

    def test_the_apps_own_pipe_is_verified(self) -> None:
        assert unverified_reason(_identity(), own_session=1, own_sid=OWN_SID) is None
        unmapped = _identity(dacl_entries=((ACCESS_ALLOWED_ACE_TYPE, 0, GENERIC_ALL, OWN_SID),))
        assert unverified_reason(unmapped, own_session=1, own_sid=OWN_SID) is None

    @pytest.mark.parametrize(
        "overrides, reason",
        [
            ({"session_id": None}, "session"),
            ({"session_id": 2}, "session"),
            ({"user_sid": None}, "user"),
            ({"user_sid": OTHER_SID}, "user"),
            ({"dacl_protected": False}, "dacl"),
            ({"dacl_entries": ()}, "dacl"),
            ({"dacl_entries": ((ACCESS_ALLOWED_ACE_TYPE, 0, FILE_ALL_ACCESS, OTHER_SID),)}, "dacl"),
            ({"dacl_entries": ((1, 0, FILE_ALL_ACCESS, OWN_SID),)}, "dacl"),  # a DENY entry
            (
                {
                    "dacl_entries": (
                        (ACCESS_ALLOWED_ACE_TYPE, 0, FILE_ALL_ACCESS, OWN_SID),
                        (ACCESS_ALLOWED_ACE_TYPE, 0, FILE_ALL_ACCESS, "S-1-1-0"),  # Everyone
                    )
                },
                "dacl",
            ),
            # Codex round 28 PR-LOW-142: the flags and the mask count too.
            ({"dacl_entries": ((ACCESS_ALLOWED_ACE_TYPE, 0, 0x0012019F, OWN_SID),)}, "dacl"),
            ({"dacl_entries": ((ACCESS_ALLOWED_ACE_TYPE, 1, FILE_ALL_ACCESS, OWN_SID),)}, "dacl"),
        ],
        ids=[
            "session_unreadable",
            "other_session",
            "user_unreadable",
            "other_user",
            "unprotected",
            "empty",
            "other_sid",
            "deny",
            "wider",
            "read_write_mask",
            "inherit_flag",
        ],
    )
    def test_any_failed_check_names_itself(
        self, overrides: dict[str, Any], reason: str
    ) -> None:
        identity = _identity(**overrides)
        assert unverified_reason(identity, own_session=1, own_sid=OWN_SID) == reason

    def test_the_client_asks_for_identification_only(self) -> None:
        """The server may learn who the host is, never impersonate it."""
        assert OPEN_FLAGS & SECURITY_SQOS_PRESENT
        assert OPEN_FLAGS & SECURITY_IDENTIFICATION
        assert OPEN_FLAGS & 0x40000000  # FILE_FLAG_OVERLAPPED


# --- real pipes -----------------------------------------------------------------


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


def _raw_pipe(name: str, sddl: str) -> Any:
    """A pipe NOT made the way scribe-app makes it (a squatter stand-in)."""
    attributes = win32security.SECURITY_ATTRIBUTES()
    attributes.SECURITY_DESCRIPTOR = (
        win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
            sddl, win32security.SDDL_REVISION_1
        )
    )
    return win32pipe.CreateNamedPipe(
        name, OPEN_MODE, PIPE_MODE, MAX_INSTANCES, 65_536, 65_536, 0, attributes
    )


@windows_only
class TestConnect:
    def test_the_apps_pipe_connects_verified_both_ways(self, server: Any, name: str) -> None:
        connector = AppPipeConnector(name)
        link = connector.connect()
        assert link is not None
        try:
            ((_kind, conn_id, _none),) = server.recorder.wait_for("connected")
            identity = read_server_identity(link._handle)
            assert identity.session_id == process_session_id(os.getpid())
            assert identity.user_sid == current_user_sid()
            assert identity.dacl_protected
            ((ace_type, ace_flags, mask, sid),) = identity.dacl_entries
            assert (ace_type, ace_flags, sid) == (ACCESS_ALLOWED_ACE_TYPE, 0, current_user_sid())
            assert mask in APP_ACE_MASKS  # what `GA` became on the real pipe
            assert link.write_frame(pipe_message("context", CONTEXT_PAYLOAD))
            ((_kind, _conn, envelope),) = server.recorder.wait_for("message")
            assert envelope.payload == CONTEXT_PAYLOAD
            assert server.send(conn_id, make_pipe_envelope("state", payload=STATE_PAYLOAD))
            assert link.read_frame() == pipe_message("state", STATE_PAYLOAD)
        finally:
            link.close()
        server.recorder.wait_for("disconnected")

    def test_an_absent_pipe_is_none_within_the_bound(self, name: str) -> None:
        started = time.monotonic()
        assert AppPipeConnector(name, wait_ms=50).connect() is None
        assert time.monotonic() - started < 2.0

    def test_a_busy_pipe_is_none(self, server: Any, name: str) -> None:
        first = AppPipeConnector(name).connect()
        assert first is not None
        try:
            server.recorder.wait_for("connected")
            assert AppPipeConnector(name, wait_ms=100).connect() is None
        finally:
            first.close()

    @pytest.mark.parametrize(
        "template",
        [
            "D:P(A;;GA;;;{sid})(A;;GR;;;WD)",
            "D:(A;;GA;;;{sid})",
            "D:P(A;;GRGW;;;{sid})",  # codex round 28 PR-LOW-142: another mask
        ],
        ids=["wider", "unprotected", "read_write_only"],
    )
    def test_a_pipe_with_another_dacl_is_unverified(self, name: str, template: str) -> None:
        handle = _raw_pipe(name, template.format(sid=current_user_sid()))
        try:
            with pytest.raises(ServerUnverified) as caught:
                AppPipeConnector(name, wait_ms=500).connect()
            assert caught.value.reason == "dacl"
        finally:
            win32file.CloseHandle(handle)

    def test_a_pipe_that_shuts_this_user_out_is_unverified(self, name: str) -> None:
        handle = _raw_pipe(name, "D:P(A;;GA;;;SY)")  # SYSTEM only
        try:
            with pytest.raises(ServerUnverified) as caught:
                AppPipeConnector(name, wait_ms=500).connect()
            assert caught.value.reason == "access_denied"
        finally:
            win32file.CloseHandle(handle)

    def test_create_file_receives_the_identification_flags(
        self, server: Any, name: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[tuple[Any, ...]] = []

        def spy(*args: Any) -> Any:
            seen.append(args)
            raise pywintypes.error(2, "CreateFile", "stopped by the test")

        monkeypatch.setattr(pipe_client.win32file, "CreateFile", spy)
        assert AppPipeConnector(name).connect() is None
        (args,) = seen
        assert args[0] == name and args[5] == OPEN_FLAGS

    def test_stop_releases_a_blocked_read(self, server: Any, name: str) -> None:
        connector = AppPipeConnector(name)
        link = connector.connect()
        assert link is not None
        outcome: list[str] = []

        def reader() -> None:
            try:
                link.read_frame()
                outcome.append("frame")
            except EndOfStream:
                outcome.append("ended")

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        time.sleep(0.1)
        connector.stop()
        thread.join(WAIT_S)
        assert outcome == ["ended"]
        link.close()

    def test_retire_releases_a_blocked_read_and_its_thread_closes(
        self, server: Any, name: str
    ) -> None:
        """Codex round 28 PR-MED-140/141: another thread ends a connection
        with ``retire`` — an event the read waits on — and the READING thread
        closes the handle once its read has settled."""
        connector = AppPipeConnector(name)
        link = connector.connect()
        assert link is not None
        outcome: list[str] = []

        def reader() -> None:
            try:
                link.read_frame()
                outcome.append("frame")
            except EndOfStream:
                outcome.append("ended")
            link.close()

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        time.sleep(0.1)
        link.retire()
        thread.join(WAIT_S)
        assert outcome == ["ended"]
        assert link.write_frame(pipe_message("context", CONTEXT_PAYLOAD)) is False  # closed
        server.recorder.wait_for("disconnected")

    @pytest.mark.parametrize("ender", ["retire", "stop"])
    def test_a_retired_or_stopped_connection_writes_nothing(
        self, server: Any, name: str, ender: str
    ) -> None:
        """Codex round 30 PR-MED-161: once retired (a failed write) or
        stopped, ``write_frame`` refuses BEFORE any I/O — the connection is
        still open (no reader has closed it), yet nothing reaches the app."""
        connector = AppPipeConnector(name)
        link = connector.connect()
        assert link is not None
        try:
            server.recorder.wait_for("connected")
            if ender == "retire":
                link.retire()
            else:
                connector.stop()
            assert link.write_frame(pipe_message("context", CONTEXT_PAYLOAD)) is False
            assert link._closed is False  # refused as retired/stopped, not as closed
        finally:
            link.close()
        server.recorder.wait_for("disconnected")
        assert [call for call in server.recorder.calls if call[0] == "message"] == []

    def test_both_ends_log_the_peer_path_and_nothing_else(
        self, name: str, tmp_path: Path
    ) -> None:
        logger = setup_logging("pipe-peer-test", log_dir=tmp_path, stderr=False)
        recorder = Recorder()
        server = PipeServer(name, recorder, sddl=pipe_sddl(current_user_sid()), logger=logger)
        server.start()
        try:
            link = AppPipeConnector(name, logger=logger).connect()
            assert link is not None
            recorder.wait_for("connected")
            link.write_frame(pipe_message("context", CONTEXT_PAYLOAD))
            recorder.wait_for("message")
            link.close()
            recorder.wait_for("disconnected")
        finally:
            assert server.stop()
        text = (tmp_path / "pipe-peer-test.log").read_text(encoding="utf-8")
        own_path = process_image_path(os.getpid())
        assert own_path is not None
        # this process is both ends here: each logs the other's executable
        assert text.count(f"pipe_peer path={own_path}") == 2
        assert CONTEXT_PAYLOAD["patient_id"] not in text


@windows_only
class TestHostOverARealPipe:
    def test_the_host_relays_both_ways_through_the_apps_pipe(
        self, server: Any, name: str, tmp_path: Path
    ) -> None:
        logger = setup_logging("host-real-pipe-test", log_dir=tmp_path, stderr=False)
        connector = AppPipeConnector(name, logger=logger)
        host = HostRun(logger, connector)
        nonce = host.handshake()
        ((_kind, conn_id, _none),) = server.recorder.wait_for("connected")
        assert server.send(conn_id, make_pipe_envelope("state", payload=STATE_PAYLOAD))
        frames = host.stdout.wait_for(lambda fs: len(fs) >= 2)
        assert frames[1]["type"] == "state" and frames[1]["session_nonce"] == nonce
        assert frames[1]["payload"] == STATE_PAYLOAD
        host.stdin.send(chrome_message("context", CONTEXT_PAYLOAD, nonce))
        ((_kind, _conn, envelope),) = server.recorder.wait_for("message")
        assert envelope.session_nonce is None and envelope.payload == CONTEXT_PAYLOAD
        host.stdin.close()
        assert host.finish() == 0
        server.recorder.wait_for("disconnected")

    def test_the_app_stopping_says_not_running(
        self, name: str, tmp_path: Path
    ) -> None:
        logger = setup_logging("host-app-stop-test", log_dir=tmp_path, stderr=False)
        recorder = Recorder()
        server = PipeServer(name, recorder, sddl=pipe_sddl(current_user_sid()))
        server.start()
        host = HostRun(logger, AppPipeConnector(name, wait_ms=100))
        host.handshake()
        recorder.wait_for("connected")
        assert server.stop()
        frames = host.stdout.wait_for(
            lambda fs: any(
                f["type"] == "state" and f["payload"]["app_running"] is False for f in fs
            )
        )
        assert frames[-1]["payload"]["app_running"] is False
        host.stdin.close()
        assert host.finish() == 0
