"""Task 4.4: the native host's two-way relay (Cliniko workflow safeguards
plan D2), driven through ``run_host`` between a fake Chrome and a scripted
connector — no pipe, no socket. The real Win32 client is
``test_pipe_client.py``; the process-level legs are in
``test_integration_no_sockets.py``."""

from __future__ import annotations

import io
import logging
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from conftest import NONCE, hello
from relay_fakes import (
    COMMAND_PAYLOAD,
    CONTEXT_PAYLOAD,
    HOST,
    NOTE_ID,
    PATIENT_ID,
    PATIENT_NAME,
    STATE_PAYLOAD,
    FakeConnector,
    FakeLink,
    HostRun,
    chrome_message,
    pipe_message,
)
from scribe_desktop.logging_setup import dropped_record_count, setup_logging
from scribe_desktop.native_host import (
    APP_NOT_RUNNING,
    RELAY_FAILED_MESSAGE,
    UNVERIFIED_MESSAGE,
    AppRelay,
    ChromeOut,
    HostSession,
    SessionViolation,
)
from scribe_desktop.pipe_client import ServerUnverified
from scribe_desktop.protocol import make_envelope, parse_envelope


@pytest.fixture
def logger(tmp_path: Path) -> logging.Logger:
    return setup_logging("scribe-host-relay-test", log_dir=tmp_path, stderr=False)


def _log_text(tmp_path: Path) -> str:
    return (tmp_path / "scribe-host-relay-test.log").read_text(encoding="utf-8")


def _not_running(frame: dict[str, Any]) -> bool:
    return frame["type"] == "state" and frame["payload"]["app_running"] is False


def _wait_until(predicate: Any, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < deadline, "condition not reached in time"
        time.sleep(0.005)


class TestHostSession:
    def test_a_relayed_type_with_the_session_nonce_is_for_the_app(self) -> None:
        session = HostSession(nonce_factory=lambda: NONCE)
        session.handle(parse_envelope(hello()))
        for message_type, payload in (("context", CONTEXT_PAYLOAD), ("command", COMMAND_PAYLOAD)):
            envelope = parse_envelope(chrome_message(message_type, payload, NONCE))
            assert session.handle(envelope) is None

    def test_a_relayed_type_with_another_nonce_is_bad_nonce(self) -> None:
        session = HostSession(nonce_factory=lambda: NONCE)
        session.handle(parse_envelope(hello()))
        envelope = parse_envelope(chrome_message("context", CONTEXT_PAYLOAD, "0" * 32))
        with pytest.raises(SessionViolation) as caught:
            session.handle(envelope)
        assert caught.value.error.payload["code"] == "bad_nonce"

    def test_a_state_from_chrome_is_refused(self) -> None:
        session = HostSession(nonce_factory=lambda: NONCE)
        session.handle(parse_envelope(hello()))
        with pytest.raises(SessionViolation) as caught:
            session.handle(parse_envelope(chrome_message("state", STATE_PAYLOAD, NONCE)))
        assert caught.value.error.payload["code"] == "malformed"

    def test_the_not_running_state_is_a_valid_v2_state(self) -> None:
        envelope = make_envelope("state", payload=dict(APP_NOT_RUNNING), session_nonce=NONCE)
        assert envelope.payload["app_running"] is False


class TestAppAbsent:
    def test_the_host_says_not_running_once_after_the_ack_and_keeps_waiting(
        self, logger: logging.Logger
    ) -> None:
        connector = FakeConnector()
        host = HostRun(logger, connector)
        nonce = host.handshake()
        frames = host.stdout.wait_for(lambda fs: any(_not_running(f) for f in fs))
        assert [f["type"] for f in frames] == ["hello_ack", "state"]
        assert frames[1]["session_nonce"] == nonce
        assert frames[1]["payload"] == APP_NOT_RUNNING
        _wait_until(lambda: connector.attempts >= 5)  # re-waiting, never exiting
        assert host.code is None
        assert len(host.stdout.states()) == 1  # announced once per absence
        host.stdin.close()
        assert host.finish() == 0
        assert connector.stopped.is_set()

    def test_a_gone_chrome_ends_the_relay_instead_of_retrying(
        self, logger: logging.Logger
    ) -> None:
        class Broken(io.BytesIO):
            def write(self, *_args: object) -> int:
                raise BrokenPipeError()

        connector = FakeConnector()
        relay = AppRelay(
            connector, ChromeOut(Broken(), logger), logger, on_fatal=lambda: None, retry_s=0.01
        )
        relay.start(NONCE)
        assert relay._thread is not None
        relay._thread.join(5)
        assert not relay._thread.is_alive()
        assert connector.attempts == 1

    def test_a_message_while_the_app_is_absent_is_dropped(self, logger: logging.Logger) -> None:
        host = HostRun(logger, FakeConnector())
        nonce = host.handshake()
        host.stdin.send(chrome_message("context", CONTEXT_PAYLOAD, nonce))
        host.stdin.send(chrome_message("ping", {}, nonce))
        host.stdout.wait_for(lambda fs: any(f["type"] == "pong" for f in fs))
        assert not any(f["type"] == "error" for f in host.stdout.frames())
        host.stdin.close()
        assert host.finish() == 0


class TestRelay:
    def test_a_state_from_the_app_reaches_chrome_with_the_session_nonce(
        self, logger: logging.Logger
    ) -> None:
        link = FakeLink()
        host = HostRun(logger, FakeConnector(link))
        nonce = host.handshake()
        link.app_sends(pipe_message("state", STATE_PAYLOAD))
        frames = host.stdout.wait_for(lambda fs: len(fs) >= 2)
        assert [f["type"] for f in frames] == ["hello_ack", "state"]  # never "not running"
        assert frames[1]["session_nonce"] == nonce
        assert frames[1]["payload"] == STATE_PAYLOAD
        host.stdin.close()
        assert host.finish() == 0

    def test_context_and_command_reach_the_app_without_the_nonce(
        self, logger: logging.Logger
    ) -> None:
        link = FakeLink()
        host = HostRun(logger, FakeConnector(link))
        nonce = host.handshake()
        link.app_sends(pipe_message("state", STATE_PAYLOAD))
        host.stdout.wait_for(lambda fs: len(fs) >= 2)  # the link is up
        context = chrome_message("context", CONTEXT_PAYLOAD, nonce)
        context["request_id"] = "ctx-1"
        host.stdin.send(context)
        host.stdin.send(chrome_message("command", COMMAND_PAYLOAD, nonce))
        _wait_until(lambda: len(link.written) == 2)
        assert link.written == [
            pipe_message("context", CONTEXT_PAYLOAD),
            pipe_message("command", COMMAND_PAYLOAD),
        ]
        assert all("session_nonce" not in m and "request_id" not in m for m in link.written)
        host.stdin.close()
        assert host.finish() == 0

    def test_a_relayed_message_with_a_foreign_nonce_is_fatal_and_not_forwarded(
        self, logger: logging.Logger
    ) -> None:
        link = FakeLink()
        host = HostRun(logger, FakeConnector(link))
        host.handshake()
        link.app_sends(pipe_message("state", STATE_PAYLOAD))
        host.stdout.wait_for(lambda fs: len(fs) >= 2)
        host.stdin.send(chrome_message("command", COMMAND_PAYLOAD, "0" * 64))
        assert host.finish() == 1
        assert host.stdout.frames()[-1]["payload"]["code"] == "bad_nonce"
        assert link.written == []
        assert link.closed.is_set()

    def test_a_relayed_message_before_hello_is_refused(self, logger: logging.Logger) -> None:
        link = FakeLink()
        connector = FakeConnector(link)
        host = HostRun(logger, connector)
        host.stdin.send(chrome_message("context", CONTEXT_PAYLOAD, NONCE))
        assert host.finish() == 1
        (error,) = host.stdout.frames()
        assert error["payload"]["code"] == "malformed"
        assert connector.attempts == 0  # the relay never started
        assert link.written == []

    def test_the_app_going_away_says_not_running_and_a_new_app_is_relayed(
        self, logger: logging.Logger
    ) -> None:
        first, second = FakeLink(), FakeLink()
        connector = FakeConnector(first)
        host = HostRun(logger, connector)
        nonce = host.handshake()
        first.app_sends(pipe_message("state", STATE_PAYLOAD))
        host.stdout.wait_for(lambda fs: len(fs) >= 2)
        first.app_closes()
        host.stdout.wait_for(lambda fs: any(_not_running(f) for f in fs))
        assert first.closed.is_set()
        connector.script(second)
        again = dict(STATE_PAYLOAD, state_rev=1)
        second.app_sends(pipe_message("state", again))
        frames = host.stdout.wait_for(lambda fs: len(fs) >= 4)
        assert [f["payload"]["app_running"] for f in frames[1:]] == [True, False, True]
        assert frames[3]["payload"] == again and frames[3]["session_nonce"] == nonce
        host.stdin.close()
        assert host.finish() == 0

    @pytest.mark.parametrize(
        "bad",
        [
            pipe_message("context", CONTEXT_PAYLOAD),  # the app never sends a context
            {**pipe_message("state", STATE_PAYLOAD), "session_nonce": NONCE},  # nor a nonce
            {"not": "an envelope"},
            pipe_message("state", {**STATE_PAYLOAD, "report": {"verification": "verified"}}),
        ],
        ids=["context", "nonce", "not_an_envelope", "invalid_state"],
    )
    def test_anything_but_a_valid_nonce_free_state_ends_that_connection(
        self, logger: logging.Logger, bad: dict[str, Any]
    ) -> None:
        link = FakeLink()
        host = HostRun(logger, FakeConnector(link))
        host.handshake()
        link.app_sends(bad)
        frames = host.stdout.wait_for(lambda fs: any(_not_running(f) for f in fs))
        assert [f["type"] for f in frames] == ["hello_ack", "state"]  # nothing relayed
        assert link.closed.is_set()
        host.stdin.close()
        assert host.finish() == 0

    def test_chrome_eof_stops_the_relay_and_closes_the_link(
        self, logger: logging.Logger
    ) -> None:
        link = FakeLink()
        connector = FakeConnector(link)
        host = HostRun(logger, connector)
        host.handshake()
        link.app_sends(pipe_message("state", STATE_PAYLOAD))
        host.stdout.wait_for(lambda fs: len(fs) >= 2)
        host.stdin.close()
        assert host.finish() == 0
        assert connector.stopped.is_set() and link.closed.is_set()

    def test_on_stop_only_the_relay_thread_closes_the_link_after_its_read(
        self, logger: logging.Logger
    ) -> None:
        """Codex round 28 PR-MED-140: stop once closed the link from the
        stopping thread BEFORE the relay thread's read had settled — on a
        real pipe, closing the handle under the reader's cancel-and-settle.
        Now the stop only releases the read; the reader's thread closes.
        Deterministic: the old order put "closed" first, synchronously."""
        link = FakeLink()
        host = HostRun(logger, FakeConnector(link))
        host.handshake()
        link.app_sends(pipe_message("state", STATE_PAYLOAD))
        host.stdout.wait_for(lambda fs: len(fs) >= 2)
        host.stdin.close()
        assert host.finish() == 0
        assert link.events == ["settled", "closed"]
        assert link.close_threads == ["scribe-host-relay"]

    def test_a_failed_write_retires_the_connection_and_is_never_replayed(
        self, logger: logging.Logger
    ) -> None:
        """Codex round 28 PR-MED-141: a failed or timed-out write may leave
        part of a frame on the pipe, so that connection is never reused —
        it is retired (the relay thread closes it), Chrome hears "not
        running", the relay reconnects, and the dropped message is not
        replayed on the new connection."""
        first, second = FakeLink(write_ok=False), FakeLink()
        connector = FakeConnector(first)
        host = HostRun(logger, connector)
        nonce = host.handshake()
        first.app_sends(pipe_message("state", STATE_PAYLOAD))
        host.stdout.wait_for(lambda fs: len(fs) >= 2)  # the link is up
        connector.script(second)
        host.stdin.send(chrome_message("command", COMMAND_PAYLOAD, nonce))
        host.stdout.wait_for(lambda fs: any(_not_running(f) for f in fs))
        assert first.retired.is_set() and first.closed.is_set()
        assert first.close_threads == ["scribe-host-relay"]
        assert first.written == [pipe_message("command", COMMAND_PAYLOAD)]
        again = dict(STATE_PAYLOAD, state_rev=5)
        second.app_sends(pipe_message("state", again))
        frames = host.stdout.wait_for(lambda fs: len(fs) >= 4)
        assert [f["payload"]["app_running"] for f in frames[1:]] == [True, False, True]
        assert second.written == []  # never replayed
        host.stdin.close()
        assert host.finish() == 0


class TestLinkOwnership:
    """Codex round 30: the reader alone closes its link — even when a stop
    times out — and a retired link takes no further write."""

    def test_a_stop_that_times_out_never_closes_the_link(
        self, logger: logging.Logger
    ) -> None:
        """PR-LOW-160: the read is held past the join timeout; ``stop``
        returns False WITHOUT closing (the old last-resort close raced the
        reader's settle). Once the read settles, the relay thread closes."""
        gate = threading.Event()
        link = FakeLink(settle_gate=gate)
        relay = AppRelay(
            FakeConnector(link),
            ChromeOut(io.BytesIO(), logger),
            logger,
            on_fatal=lambda: None,
            retry_s=0.01,
        )
        relay.start(NONCE)
        _wait_until(lambda: relay._link is link)
        assert relay.stop(timeout=0.05) is False
        assert link.close_threads == []  # the stopper closed nothing
        gate.set()
        assert relay._thread is not None
        relay._thread.join(5)
        assert not relay._thread.is_alive()
        assert link.events == ["settled", "closed"]
        assert link.close_threads == ["scribe-host-relay"]

    def test_after_a_failed_write_no_later_message_reaches_that_link(
        self, logger: logging.Logger
    ) -> None:
        """PR-MED-161: with the retired link's read held (so the relay thread
        cannot end it yet), a second command is dropped — never written onto
        the stream that may hold part of the first frame."""
        gate = threading.Event()
        link = FakeLink(write_ok=False, settle_gate=gate)
        host = HostRun(logger, FakeConnector(link))
        nonce = host.handshake()
        link.app_sends(pipe_message("state", STATE_PAYLOAD))
        host.stdout.wait_for(lambda fs: len(fs) >= 2)  # the link is up
        host.stdin.send(chrome_message("command", COMMAND_PAYLOAD, nonce))
        second = dict(COMMAND_PAYLOAD, state_rev=4)
        host.stdin.send(chrome_message("command", second, nonce))
        host.stdin.send(chrome_message("ping", {}, nonce))  # both commands handled
        host.stdout.wait_for(lambda fs: any(f["type"] == "pong" for f in fs))
        assert link.retired.is_set()
        assert link.written == [pipe_message("command", COMMAND_PAYLOAD)]
        assert link.close_threads == []  # still held: only its reader may close it
        gate.set()
        host.stdout.wait_for(lambda fs: any(_not_running(f) for f in fs))
        assert link.close_threads == ["scribe-host-relay"]
        host.stdin.close()
        assert host.finish() == 0


class TestHardErrors:
    @pytest.mark.parametrize("reason", ["session", "user", "dacl", "owner", "access_denied"])
    def test_an_unverified_server_is_a_hard_error(
        self, logger: logging.Logger, reason: str
    ) -> None:
        connector = FakeConnector(ServerUnverified(reason))
        host = HostRun(logger, connector)
        host.handshake()
        assert host.finish() == 1  # without Chrome closing stdin
        frames = host.stdout.frames()
        assert [f["type"] for f in frames] == ["hello_ack", "error"]
        assert frames[1]["payload"] == {"code": "internal", "message": UNVERIFIED_MESSAGE}
        assert connector.attempts == 1  # never retried

    def test_an_unexpected_connector_failure_is_fatal_too(self, logger: logging.Logger) -> None:
        host = HostRun(logger, FakeConnector(RuntimeError("boom")))
        host.handshake()
        assert host.finish() == 1
        assert host.stdout.frames()[-1]["payload"]["message"] == RELAY_FAILED_MESSAGE


class TestNoRelay:
    def test_without_a_relay_a_context_is_accepted_and_dropped(
        self, logger: logging.Logger
    ) -> None:
        host = HostRun(logger, None)
        nonce = host.handshake()
        host.stdin.send(chrome_message("context", CONTEXT_PAYLOAD, nonce))
        host.stdin.close()
        assert host.finish() == 0
        assert [f["type"] for f in host.stdout.frames()] == ["hello_ack"]


class TestLogging:
    def test_no_relayed_payload_is_ever_logged(
        self, logger: logging.Logger, tmp_path: Path
    ) -> None:
        before = dropped_record_count()
        first, second = FakeLink(), FakeLink()
        connector = FakeConnector(first)
        host = HostRun(logger, connector)
        nonce = host.handshake()
        first.app_sends(pipe_message("state", STATE_PAYLOAD))
        host.stdout.wait_for(lambda fs: len(fs) >= 2)
        host.stdin.send(chrome_message("context", CONTEXT_PAYLOAD, nonce))
        _wait_until(lambda: len(first.written) == 1)
        first.app_sends({"not": "an envelope"})
        host.stdout.wait_for(lambda fs: any(_not_running(f) for f in fs))
        connector.script(second)
        second.app_sends(pipe_message("state", STATE_PAYLOAD))
        host.stdout.wait_for(lambda fs: len(fs) >= 4)
        host.stdin.close()
        assert host.finish() == 0
        text = _log_text(tmp_path)
        assert "relay_connected" in text and "relay_disconnected state=malformed" in text
        for secret in (PATIENT_NAME, HOST, PATIENT_ID, NOTE_ID, nonce):
            assert secret not in text
        assert dropped_record_count() == before  # nothing even tried to log one
