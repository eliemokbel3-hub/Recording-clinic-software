"""Step 4 session state-machine tests: exhaustive legal/illegal transitions,
controls wiring capture <-> store <-> custody, concurrency synchronization,
and the failed-(recoverable) routes for disk-full and device loss.

Controller-flow tests use the real DPAPI custody path and are Windows-only
(CI runners are Windows — executor fact); the transition-table tests are
platform-neutral."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from scribe_desktop.audio_capture import DeviceLostError, MockCaptureBackend
from scribe_desktop.session import (
    ACTIVE_STATES,
    LEGAL_TRANSITIONS,
    RECOVERABLE_STATES,
    TERMINAL_STATES,
    SessionActivityError,
    SessionController,
    SessionState,
)
from scribe_desktop.session_store import (
    KEY_FILENAME,
    TRANSCRIPT_FILENAME,
    SessionChunkStore,
    StoreWriteError,
    iter_chunks,
    sweep_sessions,
    unwrap_key_from_file,
)

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI custody is Windows-only")

CHUNK = 8  # small chunk size keeps tests fast


class TestTransitionTable:
    """The table IS the spec: assert it exhaustively, then derive the
    illegal set from its complement."""

    def test_table_matches_plan_exactly(self) -> None:
        expected: dict[SessionState, set[SessionState]] = {
            SessionState.IDLE: {SessionState.RECORDING},
            SessionState.RECORDING: {
                SessionState.PAUSED,
                SessionState.PROCESSING,
                SessionState.FAILED,
                SessionState.DISCARDED,
            },
            SessionState.PAUSED: {
                SessionState.RECORDING,
                SessionState.PROCESSING,
                SessionState.FAILED,
                SessionState.DISCARDED,
            },
            SessionState.PROCESSING: {
                SessionState.QUEUED,
                SessionState.FAILED,
                SessionState.DISCARDED,
            },
            SessionState.QUEUED: {
                SessionState.WRITTEN,
                SessionState.DISCARDED,
                SessionState.EXPIRED,
            },
            SessionState.FAILED: {
                SessionState.PROCESSING,
                SessionState.DISCARDED,
                SessionState.EXPIRED,
            },
            SessionState.WRITTEN: set(),
            SessionState.DISCARDED: set(),
            SessionState.EXPIRED: set(),
        }
        assert set(LEGAL_TRANSITIONS) == set(SessionState)  # every state present
        assert {k: set(v) for k, v in LEGAL_TRANSITIONS.items()} == expected

    @pytest.mark.parametrize("source", list(SessionState))
    @pytest.mark.parametrize("target", list(SessionState))
    def test_every_pair_classified(self, source: SessionState, target: SessionState) -> None:
        """Structural invariants over the full 9x9 matrix."""
        legal = target in LEGAL_TRANSITIONS[source]
        if source in TERMINAL_STATES:
            assert not legal  # terminal states never transition
        if legal:
            assert source != target  # no self-loops
            if target == SessionState.EXPIRED:
                # Only the sweep expires sessions, never active ones.
                assert source not in ACTIVE_STATES

    def test_failed_is_recoverable_not_terminal(self) -> None:
        assert SessionState.FAILED in RECOVERABLE_STATES
        assert SessionState.FAILED not in TERMINAL_STATES
        assert SessionState.PROCESSING in LEGAL_TRANSITIONS[SessionState.FAILED]


def _controller(tmp_path: Path) -> tuple[SessionController, MockCaptureBackend]:
    backend = MockCaptureBackend()
    return SessionController(backend, sessions_root=tmp_path), backend


def _start_small_chunks(
    controller: SessionController, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Start with a tiny chunk size so tests can fill chunks with few bytes."""
    from scribe_desktop import session as session_mod

    original = session_mod.CaptureWorker

    def patched(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("chunk_bytes", CHUNK)
        return original(*args, **kwargs)

    monkeypatch.setattr(session_mod, "CaptureWorker", patched)
    controller.start(0)


@windows_only
class TestControllerFlows:
    def test_start_orders_key_before_store_and_records(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        controller, backend = _controller(tmp_path)
        _start_small_chunks(controller, monkeypatch)
        session = controller.session
        assert session is not None
        assert session.state is SessionState.RECORDING
        assert session.key_reference == "key.dpapi"
        session_dir = tmp_path / session.session_id
        assert (session_dir / KEY_FILENAME).is_file()
        assert (session_dir / "audio.enc").is_file()

        backend.feed(b"\x01" * CHUNK)
        backend.feed(b"\x02" * (CHUNK // 2))
        finished = controller.finish()
        assert finished.state is SessionState.PROCESSING

        # Chunks decrypt through the DPAPI-unwrapped key — full custody loop.
        crypto = unwrap_key_from_file(session_dir)
        chunks = list(iter_chunks(session_dir / "audio.enc", crypto, require_footer=True))
        assert chunks == [b"\x01" * CHUNK, b"\x02" * (CHUNK // 2)]

    def test_single_active_session_invariant(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        controller.start(0)
        for state in (SessionState.RECORDING,):
            assert controller.state is state
        with pytest.raises(SessionActivityError, match="single-active-session"):
            controller.start(0)
        controller.pause()
        with pytest.raises(SessionActivityError):
            controller.start(0)
        controller.finish()  # processing is still active
        with pytest.raises(SessionActivityError):
            controller.start(0)

    def test_start_allowed_after_queued_and_old_session_stays_recoverable(
        self, tmp_path: Path
    ) -> None:
        controller, _backend = _controller(tmp_path)
        first = controller.start(0)
        controller.finish()
        controller.mark_queued()
        second = controller.start(0)
        assert second.session_id != first.session_id
        # The queued session's custody remains on disk: recoverable.
        assert (tmp_path / first.session_id / KEY_FILENAME).is_file()
        controller.discard()

    def test_pause_resume_flow(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        controller, backend = _controller(tmp_path)
        _start_small_chunks(controller, monkeypatch)
        backend.feed(b"\x01" * CHUNK)
        assert controller.pause().state is SessionState.PAUSED
        backend.feed(b"\x02" * CHUNK)  # while paused: cleanly dropped
        assert controller.resume().state is SessionState.RECORDING
        backend.feed(b"\x03" * CHUNK)
        session = controller.finish()
        crypto = unwrap_key_from_file(tmp_path / session.session_id)
        chunks = list(
            iter_chunks(tmp_path / session.session_id / "audio.enc", crypto, require_footer=True)
        )
        assert chunks == [b"\x01" * CHUNK, b"\x03" * CHUNK]

    def test_finish_from_paused(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        controller.start(0)
        controller.pause()
        assert controller.finish().state is SessionState.PROCESSING

    def test_complete_deletes_key_and_terminates(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        session = controller.start(0)
        session_dir = tmp_path / session.session_id
        controller.finish()
        controller.mark_queued()
        # Step 9 will write transcript.enc; simulate it under the session key.
        crypto = unwrap_key_from_file(session_dir)
        (session_dir / TRANSCRIPT_FILENAME).write_bytes(crypto.encrypt(b"transcript"))
        completed = controller.complete()
        assert completed.state is SessionState.WRITTEN
        assert not (session_dir / KEY_FILENAME).exists()  # cryptographic deletion
        assert controller.state is SessionState.IDLE
        assert controller.session is None

    def test_complete_failure_keeps_key_and_stays_queued(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        session = controller.start(0)
        session_dir = tmp_path / session.session_id
        controller.finish()
        controller.mark_queued()
        # No transcript.enc exists -> complete_session must fail, key retained.
        with pytest.raises(StoreWriteError):
            controller.complete()
        assert controller.state is SessionState.QUEUED
        assert (session_dir / KEY_FILENAME).is_file()

    @pytest.mark.parametrize(
        "prepare",
        ["recording", "paused", "processing", "queued", "failed"],
    )
    def test_discard_from_every_legal_state(self, tmp_path: Path, prepare: str) -> None:
        controller, backend = _controller(tmp_path)
        session = controller.start(0)
        session_dir = tmp_path / session.session_id
        if prepare == "paused":
            controller.pause()
        elif prepare == "processing":
            controller.finish()
        elif prepare == "queued":
            controller.finish()
            controller.mark_queued()
        elif prepare == "failed":
            backend.fail()
            _wait_for_state(controller, SessionState.FAILED)
        discarded = controller.discard()
        assert discarded.state is SessionState.DISCARDED
        assert not (session_dir / KEY_FILENAME).exists()
        assert not session_dir.exists()
        assert controller.state is SessionState.IDLE

    def test_device_loss_routes_to_failed_recoverable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        controller, backend = _controller(tmp_path)
        _start_small_chunks(controller, monkeypatch)
        backend.feed(b"\x07" * CHUNK)
        backend.feed(b"\x08" * (CHUNK // 2))  # buffered partial at loss time
        backend.fail(DeviceLostError("usb yanked"))
        _wait_for_state(controller, SessionState.FAILED)
        session = controller.session
        assert session is not None and session.state is SessionState.FAILED
        session_dir = tmp_path / session.session_id
        # RECOVERABLE: key custody + all captured audio (incl. the flushed
        # partial) survive — never silent data loss.
        assert (session_dir / KEY_FILENAME).is_file()
        crypto = unwrap_key_from_file(session_dir)
        chunks = list(iter_chunks(session_dir / "audio.enc", crypto))
        assert chunks == [b"\x07" * CHUNK, b"\x08" * (CHUNK // 2)]

    def test_disk_full_during_capture_routes_to_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        controller, backend = _controller(tmp_path)
        _start_small_chunks(controller, monkeypatch)
        session = controller.session
        assert session is not None
        monkeypatch.setattr(
            SessionChunkStore,
            "append_chunk",
            lambda self, data: (_ for _ in ()).throw(StoreWriteError("disk full")),
        )
        backend.feed(b"\x01" * CHUNK)
        _wait_for_state(controller, SessionState.FAILED)
        # Key retained: recoverable.
        assert (tmp_path / session.session_id / KEY_FILENAME).is_file()

    def test_disk_full_at_finish_routes_to_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        controller, _backend = _controller(tmp_path)
        session = controller.start(0)
        monkeypatch.setattr(
            SessionChunkStore,
            "finish",
            lambda self: (_ for _ in ()).throw(StoreWriteError("disk full at footer")),
        )
        finished = controller.finish()
        assert finished.state is SessionState.FAILED
        assert (tmp_path / session.session_id / KEY_FILENAME).is_file()

    def test_start_failure_cleans_up_completely(self, tmp_path: Path) -> None:
        backend = MockCaptureBackend()
        controller = SessionController(backend, sessions_root=tmp_path)
        with pytest.raises(DeviceLostError):
            controller.start(99)  # no such device
        assert controller.state is SessionState.IDLE
        assert list(tmp_path.iterdir()) == []  # no orphan session dir

    def test_pause_waits_for_in_flight_chunk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Plan-mandated synchronization test at the CONTROLLER level: a
        pause issued while a chunk write is mid-flight returns only after
        that chunk is fully written; the store then holds the whole chunk."""
        controller, backend = _controller(tmp_path)
        gate = threading.Event()
        entered = threading.Event()
        original_append = SessionChunkStore.append_chunk

        def slow_append(self: SessionChunkStore, data: bytes) -> int:
            entered.set()
            assert gate.wait(timeout=10)
            return original_append(self, data)

        monkeypatch.setattr(SessionChunkStore, "append_chunk", slow_append)
        _start_small_chunks(controller, monkeypatch)
        session = controller.session
        assert session is not None
        backend.feed(b"\x0c" * CHUNK)
        assert entered.wait(timeout=5)  # write in flight, blocked in the store

        paused = threading.Event()
        pauser = threading.Thread(target=lambda: (controller.pause(), paused.set()))
        pauser.start()
        time.sleep(0.05)
        assert not paused.is_set()  # pause() is waiting on the in-flight write
        assert controller.state is SessionState.RECORDING
        gate.set()
        pauser.join(timeout=5)
        assert paused.is_set()
        assert controller.state is SessionState.PAUSED
        monkeypatch.undo()
        controller.finish()
        crypto = unwrap_key_from_file(tmp_path / session.session_id)
        chunks = list(iter_chunks(tmp_path / session.session_id / "audio.enc", crypto))
        assert chunks == [b"\x0c" * CHUNK]  # fully written, exactly once

    def test_sweep_skips_active_session_by_state(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        session = controller.start(0)
        assert controller.active_session_ids() == frozenset({session.session_id})
        # Even with an absurdly old clock the ACTIVE session is untouched.
        results = sweep_sessions(
            tmp_path,
            active_session_ids=controller.active_session_ids(),
            now=time.time() + 10 * 24 * 3600,
        )
        assert [r.action for r in results] == ["skipped_active"]
        assert (tmp_path / session.session_id / KEY_FILENAME).is_file()
        controller.discard()
        assert controller.active_session_ids() == frozenset()


@windows_only
class TestIllegalOperations:
    def test_controls_require_correct_state(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        # No session at all:
        for operation in (
            controller.pause,
            controller.resume,
            controller.finish,
            controller.mark_queued,
            controller.complete,
            controller.discard,
        ):
            with pytest.raises(SessionActivityError):
                operation()
        controller.start(0)
        with pytest.raises(SessionActivityError):
            controller.resume()  # recording, not paused
        with pytest.raises(SessionActivityError):
            controller.mark_queued()  # not processing
        with pytest.raises(SessionActivityError):
            controller.complete()  # not queued
        controller.pause()
        with pytest.raises(SessionActivityError):
            controller.pause()  # already paused
        controller.finish()
        with pytest.raises(SessionActivityError):
            controller.finish()  # already processing
        with pytest.raises(SessionActivityError):
            controller.pause()
        controller.mark_queued()
        with pytest.raises(SessionActivityError):
            controller.finish()  # queued: finish illegal
        controller.discard()

    def test_discard_illegal_after_terminal(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        session = controller.start(0)
        session_dir = tmp_path / session.session_id
        controller.finish()
        controller.mark_queued()
        crypto = unwrap_key_from_file(session_dir)
        (session_dir / TRANSCRIPT_FILENAME).write_bytes(crypto.encrypt(b"t"))
        controller.complete()
        # Terminal: the controller no longer tracks it; discard has no target.
        with pytest.raises(SessionActivityError):
            controller.discard()


def _wait_for_state(
    controller: SessionController, state: SessionState, timeout: float = 5.0
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if controller.state is state:
            return
        time.sleep(0.01)
    raise AssertionError(f"controller never reached {state} (state={controller.state})")


@windows_only
class TestDiscardStartRace:
    def test_discard_never_deletes_a_concurrently_started_session(
        self, tmp_path: Path
    ) -> None:
        """PR-HIGH-001: discard() releases the controller lock around the
        worker stop; a concurrent start() may legally replace a failed
        session in that window. Discard must then delete the OLD session's
        artifacts only — never the freshly started recording's key."""
        controller, backend = _controller(tmp_path)
        old = controller.start(0)
        backend.fail()  # device loss -> failed (recoverable), worker retained
        _wait_for_state(controller, SessionState.FAILED)
        live = controller._live  # noqa: SLF001 - deliberate race injection
        assert live is not None and live.worker is not None
        real_worker = live.worker
        started: list[Any] = []

        class _RacingWorker:
            triggered = False

            def stop(self, *, flush: bool) -> None:
                real_worker.stop(flush=flush)
                if not _RacingWorker.triggered:  # concurrent start exactly once
                    _RacingWorker.triggered = True
                    started.append(controller.start(0))

        live.worker = _RacingWorker()  # type: ignore[assignment]
        discarded = controller.discard()

        assert discarded.session_id == old.session_id
        assert discarded.state is SessionState.DISCARDED
        new = started[0]
        current = controller.session
        assert current is not None and current.session_id == new.session_id
        assert controller.state is SessionState.RECORDING
        # The new session's key custody must be intact...
        assert (tmp_path / new.session_id / KEY_FILENAME).exists()
        # ...and the old session's directory is the one that was removed.
        assert not (tmp_path / old.session_id).exists()
        controller.discard()  # cleanup
