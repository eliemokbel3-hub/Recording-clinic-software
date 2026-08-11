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
import uuid
from pathlib import Path
from typing import Any

import pytest

from scribe_desktop.audio_capture import DeviceLostError, MockCaptureBackend
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import (
    ACTIVE_STATES,
    LEGAL_TRANSITIONS,
    RECOVERABLE_STATES,
    TERMINAL_STATES,
    GenerationInProgressError,
    SessionActivityError,
    SessionController,
    SessionControllerError,
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


# ---------------------------------------------------------------------------
# Task 6.3: the controller-owned note-generation lease.
# ---------------------------------------------------------------------------


def _recovered_dir(tmp_path: Path) -> tuple[Path, SessionCrypto]:
    """A recovered-session directory: custody blob stand-in + a transcript
    encrypted under an unwrapped in-memory key (mirrors the store tests'
    dummy-key discipline — the recovered ops never touch DPAPI)."""
    directory = tmp_path / uuid.uuid4().hex
    directory.mkdir()
    (directory / KEY_FILENAME).write_bytes(b"\0" * 64)
    crypto = SessionCrypto()
    (directory / TRANSCRIPT_FILENAME).write_bytes(crypto.encrypt(b"transcript"))
    return directory, crypto


class TestGenerationLeaseTokens:
    """The lease token contract, platform-neutral (no session involved)."""

    def test_second_acquisition_refused(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        assert not controller.generating
        lease = controller.begin_generation()
        assert controller.generating
        with pytest.raises(GenerationInProgressError):
            controller.begin_generation()
        controller.end_generation(lease)
        assert not controller.generating

    def test_release_is_idempotent_but_foreign_tokens_are_refused(
        self, tmp_path: Path
    ) -> None:
        controller, _backend = _controller(tmp_path)
        first = controller.begin_generation()
        controller.end_generation(first)
        controller.end_generation(first)  # double release: no-op
        second = controller.begin_generation()
        with pytest.raises(SessionControllerError, match="not held"):
            controller.end_generation(first)  # stale token while another is held
        assert controller.generating  # the refusal released nothing
        controller.end_generation(second)

    def test_reservations_for_different_targets_are_independent(
        self, tmp_path: Path
    ) -> None:
        """Round 31 Verification: two simultaneous reservations for different
        ids — releasing one leaves the other protected in the atomic
        snapshot (per-id lifetime, never a global bit)."""
        controller, _backend = _controller(tmp_path)
        first, second = "a" * 32, "b" * 32
        with controller._lock:  # noqa: SLF001 - discard() is the single producer; deliberate injection
            controller._reserve_custody_locked(first)  # noqa: SLF001
            controller._reserve_custody_locked(second)  # noqa: SLF001
        assert {first, second} <= controller.custody_protected_ids()
        with controller._lock:  # noqa: SLF001
            controller._release_custody_locked(first)  # noqa: SLF001
        snapshot = controller.custody_protected_ids()
        assert second in snapshot
        assert first not in snapshot
        with controller._lock:  # noqa: SLF001
            controller._release_custody_locked(second)  # noqa: SLF001
        assert controller.custody_protected_ids() == frozenset()


class TestGenerationLeaseRecoveredPath:
    """The recovered custody coordinator: Complete / Discard / key
    destruction blocked while generating, performed normally when free."""

    def test_complete_recovered_blocked_then_allowed(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        directory, crypto = _recovered_dir(tmp_path)
        lease = controller.begin_generation()
        with pytest.raises(GenerationInProgressError, match="complete"):
            controller.complete_recovered(directory, crypto)
        assert (directory / KEY_FILENAME).exists()
        assert not crypto.destroyed
        controller.end_generation(lease)
        controller.complete_recovered(directory, crypto)
        assert not (directory / KEY_FILENAME).exists()
        assert crypto.destroyed

    def test_discard_recovered_blocked_then_allowed(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        directory, crypto = _recovered_dir(tmp_path)
        lease = controller.begin_generation()
        with pytest.raises(GenerationInProgressError, match="discard"):
            controller.discard_recovered(directory, crypto)
        assert directory.exists()
        assert not crypto.destroyed
        controller.end_generation(lease)
        controller.discard_recovered(directory, crypto)
        assert not directory.exists()
        assert crypto.destroyed

    def test_destroy_recovered_crypto_blocked_then_allowed(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        crypto = SessionCrypto()
        lease = controller.begin_generation()
        with pytest.raises(GenerationInProgressError, match="recovered-key destruction"):
            controller.destroy_recovered_crypto(crypto)
        assert not crypto.destroyed
        controller.end_generation(lease)
        controller.destroy_recovered_crypto(crypto)
        assert crypto.destroyed


@windows_only
class TestGenerationLeaseLivePath:
    """The live-session side of the Task 6.3 Done-when: start()-, Complete-
    and Discard-during-generation, plus the barrier the lease exists for."""

    def _queued_session(self, tmp_path: Path) -> tuple[SessionController, Path]:
        controller, _backend = _controller(tmp_path)
        session = controller.start(0)
        session_dir = tmp_path / session.session_id
        controller.finish()
        controller.mark_queued()
        crypto = unwrap_key_from_file(session_dir)
        (session_dir / TRANSCRIPT_FILENAME).write_bytes(crypto.encrypt(b"transcript"))
        return controller, session_dir

    def test_lease_blocks_start_complete_discard(self, tmp_path: Path) -> None:
        controller, session_dir = self._queued_session(tmp_path)
        queued = controller.session
        assert queued is not None
        lease = controller.begin_generation()
        with pytest.raises(GenerationInProgressError, match="start"):
            controller.start(0)
        with pytest.raises(GenerationInProgressError, match="complete"):
            controller.complete()
        with pytest.raises(GenerationInProgressError, match="discard"):
            controller.discard()
        # The queued session's handle and custody are untouched by the
        # refusals: no retirement happened, the key is still on disk.
        current = controller.session
        assert current is not None and current.session_id == queued.session_id
        assert controller.state is SessionState.QUEUED
        assert (session_dir / KEY_FILENAME).is_file()
        controller.end_generation(lease)
        assert controller.complete().state is SessionState.WRITTEN

    def test_lease_spans_worker_return_until_write_note(self, tmp_path: Path) -> None:
        """THE barrier test (Task 6.3 Done-when): the custody-critical gap is
        exactly AFTER the generation worker returns and BEFORE the GUI-thread
        write_note — a worker-scoped lease would already have been released
        here. The token must still be held at that point, and released only
        by the explicit end_generation after the write."""
        controller, session_dir = self._queued_session(tmp_path)
        lease = controller.begin_generation()
        returned = threading.Event()

        def worker() -> None:
            # Stands for the compose/finalise work; its RETURN is the moment
            # a worker-scoped lease would have been dropped.
            returned.set()

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        assert returned.is_set()
        # Worker has returned; write_note has NOT run. The lease must hold.
        with pytest.raises(GenerationInProgressError):
            controller.complete()
        with pytest.raises(GenerationInProgressError):
            controller.start(0)
        # ...the GUI-thread write_note would run here...
        controller.end_generation(lease)
        assert controller.complete().state is SessionState.WRITTEN

    def test_begin_generation_refused_inside_discard_unlocked_window(
        self, tmp_path: Path
    ) -> None:
        """Round 27 PR-MED-001, the exact interleaving, deterministically via
        the `TestDiscardStartRace` worker-wrapper pattern: discard() has
        passed its entry lease check and released the lock for the worker
        join; a lease acquisition attempted INSIDE that window must be
        refused by the custody reservation — the lease can never be held
        while `discard_session` deletes the key. The reservation clears on
        exit, so a generation can begin normally afterwards."""
        controller, _backend = _controller(tmp_path)
        session = controller.start(0)
        session_dir = tmp_path / session.session_id
        live = controller._live  # noqa: SLF001 - deliberate race injection
        assert live is not None and live.worker is not None
        real_worker = live.worker
        outcomes: list[str] = []

        class _RacingWorker:
            def stop(self, *, flush: bool) -> None:
                real_worker.stop(flush=flush)
                # discard() is inside its unlocked window RIGHT NOW — the
                # round-27 interleaving. The acquisition must refuse; if it
                # were granted, the key deletion below would run while the
                # lease is held.
                try:
                    controller.begin_generation()
                except SessionActivityError:
                    outcomes.append("refused")
                else:
                    outcomes.append("acquired")

        live.worker = _RacingWorker()  # type: ignore[assignment]
        discarded = controller.discard()
        assert discarded.state is SessionState.DISCARDED
        assert outcomes == ["refused"]
        assert not controller.generating  # no lease survived the window
        assert not (session_dir / KEY_FILENAME).exists()
        # Reservation cleared on exit: generation is available again.
        lease = controller.begin_generation()
        controller.end_generation(lease)

    def test_complete_refused_inside_discard_unlocked_window(
        self, tmp_path: Path
    ) -> None:
        """Round 29 PR-MED-001, the exact interleaving as a deterministic
        two-thread barrier (events, never scheduler sleeps): a QUEUED
        discard() is paused INSIDE its unlocked window with the reservation
        held; complete() attempted from another thread must refuse BEFORE
        `complete_session` mutates custody, and the released discard alone
        reaches DISCARDED with key-first deletion."""
        controller, session_dir = self._queued_session(tmp_path)
        live = controller._live  # noqa: SLF001 - deliberate race injection
        assert live is not None and live.worker is None  # queued: no real worker
        in_window = threading.Event()
        release = threading.Event()

        class _BarrierWorker:
            def stop(self, *, flush: bool) -> None:
                # discard() has passed its first locked section — the
                # reservation is held and the lock is released. Hold it
                # here until the main thread has attempted complete().
                in_window.set()
                assert release.wait(timeout=10.0)

        live.worker = _BarrierWorker()  # type: ignore[assignment]
        results: list[Any] = []
        discard_thread = threading.Thread(
            target=lambda: results.append(controller.discard())
        )
        discard_thread.start()
        try:
            assert in_window.wait(timeout=10.0)
            with pytest.raises(SessionActivityError, match="discard is completing"):
                controller.complete()
            # The refusal came BEFORE any custody mutation: key intact.
            assert (session_dir / KEY_FILENAME).is_file()
        finally:
            release.set()
            discard_thread.join(timeout=10.0)
        assert not discard_thread.is_alive()
        # Exactly one terminal action won: the discard, key-first.
        assert [s.state for s in results] == [SessionState.DISCARDED]
        assert controller.session is None
        assert not (session_dir / KEY_FILENAME).exists()
        assert not session_dir.exists()

    def test_custody_reservation_clears_when_discard_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The reservation's `finally` discipline: a discard that dies inside
        its second section must still release the reservation, or generation
        would be refused forever."""
        from scribe_desktop import session as session_mod

        controller, _backend = _controller(tmp_path)
        controller.start(0)

        def boom(directory: Path, crypto: object = None) -> None:
            raise StoreWriteError("injected discard failure")

        monkeypatch.setattr(session_mod, "discard_session", boom)
        with pytest.raises(StoreWriteError, match="injected"):
            controller.discard()
        monkeypatch.undo()
        lease = controller.begin_generation()  # reservation was released
        controller.end_generation(lease)
        controller.discard()  # real cleanup

    def test_transcribe_refused_inside_discard_unlocked_window(
        self, tmp_path: Path
    ) -> None:
        """Round 32 PR-MED-001, the INVERSE of the round-42 transcribe-first
        guard, as a deterministic two-thread rendezvous: Discard(X) of a
        PROCESSING session parks inside its unlocked window with the
        reservation held; transcribe() from another thread must refuse
        BEFORE the supplied transcriber callable runs and before any
        transcript/store mutation; the released discard alone destroys X
        key-first and clears the reservation."""
        controller, _backend = _controller(tmp_path)
        x = controller.start(0)
        x_dir = tmp_path / x.session_id
        controller.finish()  # PROCESSING; transcribing is False
        live = controller._live  # noqa: SLF001 - deliberate race injection
        assert live is not None and live.worker is None
        in_window = threading.Event()
        release = threading.Event()

        class _BarrierWorker:
            parked = False

            def stop(self, *, flush: bool) -> None:
                if _BarrierWorker.parked:
                    return
                _BarrierWorker.parked = True
                in_window.set()
                assert release.wait(timeout=10.0)

        live.worker = _BarrierWorker()  # type: ignore[assignment]
        results: list[Any] = []
        discard_thread = threading.Thread(
            target=lambda: results.append(controller.discard())
        )
        discard_thread.start()
        try:
            assert in_window.wait(timeout=10.0)
            ran: list[str] = []

            def transcriber(directory: Path, crypto: Any) -> None:
                ran.append("ran")

            with pytest.raises(SessionActivityError, match="discard of this session"):
                controller.transcribe(transcriber)
            assert ran == []  # refused BEFORE the callable; no crypto/store use
            assert (x_dir / KEY_FILENAME).is_file()
        finally:
            release.set()
            discard_thread.join(timeout=10.0)
        assert not discard_thread.is_alive()
        assert [s.state for s in results] == [SessionState.DISCARDED]
        assert controller.reserved_session_ids() == frozenset()
        assert not x_dir.exists()

    def test_reserved_discard_target_protected_across_live_pointer_swap(
        self, tmp_path: Path
    ) -> None:
        """Round 30 PR-MED-001, the falsified-enumeration case as a
        deterministic barrier: Discard(X) parks inside its unlocked window;
        the ADMITTED concurrent start() retires X and installs Y — from that
        instant the live pointer names Y, and only the RESERVATION protects
        X. Prove X stays in `reserved_session_ids()` (the listing/sweep
        protection source), the recovered coordinator refuses X by RESOLVED
        identity before any custody mutation while an UNRESERVED directory
        still proceeds (identity-scoped, not coarse), and the released
        discard alone deletes X key-first with the reservation clearing and
        Y's custody intact."""
        controller, _backend = _controller(tmp_path)
        x = controller.start(0)
        x_dir = tmp_path / x.session_id
        controller.finish()
        controller.mark_queued()
        x_crypto = unwrap_key_from_file(x_dir)
        (x_dir / TRANSCRIPT_FILENAME).write_bytes(x_crypto.encrypt(b"transcript"))
        live = controller._live  # noqa: SLF001 - deliberate race injection
        assert live is not None and live.worker is None
        in_window = threading.Event()
        release = threading.Event()

        class _BarrierWorker:
            parked = False

            def stop(self, *, flush: bool) -> None:
                if _BarrierWorker.parked:
                    # start()'s _retire_locked stops this worker again UNDER
                    # the controller lock; a stopped real worker's join is a
                    # no-op there, so the barrier must be too (the
                    # TestDiscardStartRace triggered-guard idiom).
                    return
                _BarrierWorker.parked = True
                in_window.set()
                assert release.wait(timeout=10.0)

        live.worker = _BarrierWorker()  # type: ignore[assignment]
        results: list[Any] = []
        discard_thread = threading.Thread(
            target=lambda: results.append(controller.discard())
        )
        discard_thread.start()
        try:
            assert in_window.wait(timeout=10.0)
            # The admitted concurrent start(): retires X, installs Y — the
            # round-30 pivot. X's on-disk custody remains, but the live
            # pointer no longer names it.
            y = controller.start(0)
            assert x.session_id in controller.reserved_session_ids()
            assert y.session_id not in controller.reserved_session_ids()
            # Round 31: the atomic snapshot names BOTH the reserved X and
            # the live Y in one locked read — the split-read omission is
            # structurally unrepresentable.
            assert {x.session_id, y.session_id} <= controller.custody_protected_ids()
            # Recovered-coordinator attempts on X refuse by RESOLVED
            # identity, BEFORE any unwrap/mutation — key intact, foreign
            # crypto untouched.
            foreign = SessionCrypto()
            with pytest.raises(SessionActivityError, match="discard of this session"):
                controller.complete_recovered(x_dir, foreign)
            with pytest.raises(SessionActivityError, match="discard of this session"):
                controller.discard_recovered(x_dir, foreign)
            with pytest.raises(SessionActivityError, match="discard is in flight"):
                controller.destroy_recovered_crypto(foreign)
            assert not foreign.destroyed
            assert (x_dir / KEY_FILENAME).is_file()
            # Identity-scoped, not coarse: an UNRESERVED recovered directory
            # still completes during the window.
            z_dir, z_crypto = _recovered_dir(tmp_path)
            controller.complete_recovered(z_dir, z_crypto)
            assert z_crypto.destroyed
        finally:
            release.set()
            discard_thread.join(timeout=10.0)
        assert not discard_thread.is_alive()
        # The released discard alone won X: key-first deletion, reservation
        # cleared; Y untouched and still recording.
        assert [s.state for s in results] == [SessionState.DISCARDED]
        assert controller.reserved_session_ids() == frozenset()
        assert not (x_dir / KEY_FILENAME).exists()
        assert not x_dir.exists()
        assert (tmp_path / y.session_id / KEY_FILENAME).is_file()
        assert controller.state is SessionState.RECORDING
        controller.discard()  # cleanup Y

    def test_worker_failure_keeps_the_lease_until_cleanup_releases(
        self, tmp_path: Path
    ) -> None:
        controller, _session_dir = self._queued_session(tmp_path)
        lease = controller.begin_generation()
        failures: list[Exception] = []

        def failing_worker() -> None:
            # The injected failure is CAUGHT in-thread, exactly as the real
            # TaskThread catches worker exceptions and reports them to the
            # GUI-thread `failed` handler — nothing leaks unhandled.
            try:
                raise RuntimeError("generation failed")
            except RuntimeError as exc:
                failures.append(exc)

        thread = threading.Thread(target=failing_worker)
        thread.start()
        thread.join()
        assert len(failures) == 1
        # The worker FAILED; the lease is still held until failure cleanup
        # explicitly releases — custody stays protected through the gap.
        with pytest.raises(GenerationInProgressError):
            controller.discard()
        controller.end_generation(lease)  # the failure-cleanup release
        assert controller.discard().state is SessionState.DISCARDED
