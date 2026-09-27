"""Step 4 session state-machine tests: exhaustive legal/illegal transitions,
controls wiring capture <-> store <-> custody, concurrency synchronization,
and the failed-(recoverable) routes for disk-full and device loss.

Controller-flow tests use the real DPAPI custody path and are Windows-only
(CI runners are Windows — executor fact); the transition-table tests are
platform-neutral."""

from __future__ import annotations

import re
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import pytest

from conftest import start_unlinked
from encounter_fakes import NOW, consent_for
from encounter_fakes import context as enc_context
from scribe_desktop.audio_capture import DeviceLostError, MockCaptureBackend
from scribe_desktop.encounter import (
    ConsentAttestation,
    EncounterRecord,
    Verification,
    read_encounter_record,
    unlinked_consent,
)
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import (
    ACTIVE_STATES,
    LEGAL_TRANSITIONS,
    RECOVERABLE_STATES,
    TERMINAL_STATES,
    ConsentRequiredError,
    GenerationInProgressError,
    GenerationLease,
    SessionActivityError,
    SessionController,
    SessionControllerError,
    SessionState,
)
from scribe_desktop.session_store import (
    AUDIO_FILENAME,
    ENCOUNTER_FILENAME,
    KEY_FILENAME,
    NOTE_FILENAME,
    TRANSCRIPT_FILENAME,
    SessionChunkStore,
    StoreCorruptError,
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
    start_unlinked(controller)


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
        start_unlinked(controller)
        for state in (SessionState.RECORDING,):
            assert controller.state is state
        with pytest.raises(SessionActivityError, match="single-active-session"):
            start_unlinked(controller)
        controller.pause()
        with pytest.raises(SessionActivityError):
            start_unlinked(controller)
        controller.finish()  # processing is still active
        with pytest.raises(SessionActivityError):
            start_unlinked(controller)

    def test_start_allowed_after_queued_and_old_session_stays_recoverable(
        self, tmp_path: Path
    ) -> None:
        controller, _backend = _controller(tmp_path)
        first = start_unlinked(controller)
        controller.finish()
        controller.mark_queued()
        second = start_unlinked(controller)
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
        start_unlinked(controller)
        controller.pause()
        assert controller.finish().state is SessionState.PROCESSING

    def test_complete_deletes_key_and_terminates(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        session = start_unlinked(controller)
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
        session = start_unlinked(controller)
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
        session = start_unlinked(controller)
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
        session = start_unlinked(controller)
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
            start_unlinked(controller, 99)  # no such device
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
        session = start_unlinked(controller)
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
        start_unlinked(controller)
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
        session = start_unlinked(controller)
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
        old = start_unlinked(controller)
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
                    started.append(start_unlinked(controller))

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
        session = start_unlinked(controller)
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
            start_unlinked(controller)
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
            start_unlinked(controller)
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
        session = start_unlinked(controller)
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
        start_unlinked(controller)

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
        x = start_unlinked(controller)
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
        x = start_unlinked(controller)
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
            y = start_unlinked(controller)
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


@windows_only
class TestGenerationCustodyOp:
    """Task 7.2: the scoped, lease-aware `with_generation_custody` op — the
    live-path generation worker's and the GUI-thread write's ONE route to the
    QUEUED session's (directory, crypto), no raw accessors."""

    def _queued_session(self, tmp_path: Path) -> tuple[SessionController, Path]:
        controller, _backend = _controller(tmp_path)
        session = start_unlinked(controller)
        session_dir = tmp_path / session.session_id
        controller.finish()
        controller.mark_queued()
        crypto = unwrap_key_from_file(session_dir)
        (session_dir / TRANSCRIPT_FILENAME).write_bytes(crypto.encrypt(b"transcript"))
        return controller, session_dir

    def test_runs_action_with_queued_custody_under_the_lease(self, tmp_path: Path) -> None:
        controller, session_dir = self._queued_session(tmp_path)
        lease = controller.begin_generation()
        seen: list[Path] = []

        def action(directory: Path, crypto: SessionCrypto) -> str:
            seen.append(directory)
            # The custody is live: the crypto decrypts the on-disk transcript.
            assert crypto.decrypt((directory / TRANSCRIPT_FILENAME).read_bytes()) == b"transcript"
            return "ran"

        assert controller.with_generation_custody(lease, action) == "ran"
        assert seen == [session_dir]
        controller.end_generation(lease)

    def test_refused_without_a_lease(self, tmp_path: Path) -> None:
        controller, _session_dir = self._queued_session(tmp_path)
        with pytest.raises(GenerationInProgressError):
            controller.with_generation_custody(GenerationLease(), lambda d, c: None)

    def test_refused_with_a_foreign_lease(self, tmp_path: Path) -> None:
        controller, _session_dir = self._queued_session(tmp_path)
        held = controller.begin_generation()
        with pytest.raises(GenerationInProgressError):
            controller.with_generation_custody(GenerationLease(), lambda d, c: None)
        controller.end_generation(held)

    def test_refused_when_session_not_queued(self, tmp_path: Path) -> None:
        controller, _backend = _controller(tmp_path)
        start_unlinked(controller)  # RECORDING, not QUEUED
        lease = controller.begin_generation()
        with pytest.raises(SessionActivityError):
            controller.with_generation_custody(lease, lambda d, c: None)
        controller.end_generation(lease)
        controller.discard()


@windows_only
class TestCompleteWithoutNote:
    """Task 7.1 delete-note-and-complete-without-one, at the controller —
    round 35 PR-MED-001: runs UNDER the held lease and consumes it only on
    success, so a completion FAILURE leaves the lease held and the session
    QUEUED (never unleased mid-review)."""

    def _queued_session(self, tmp_path: Path) -> tuple[SessionController, Path]:
        controller, _backend = _controller(tmp_path)
        session = start_unlinked(controller)
        session_dir = tmp_path / session.session_id
        controller.finish()
        controller.mark_queued()
        crypto = unwrap_key_from_file(session_dir)
        (session_dir / TRANSCRIPT_FILENAME).write_bytes(crypto.encrypt(b"transcript"))
        (session_dir / NOTE_FILENAME).write_bytes(crypto.encrypt(b"note"))
        return controller, session_dir

    def test_deletes_note_and_completes_and_consumes_lease(self, tmp_path: Path) -> None:
        controller, session_dir = self._queued_session(tmp_path)
        lease = controller.begin_generation()
        assert (session_dir / NOTE_FILENAME).is_file()
        session = controller.complete_without_note(lease)
        assert session.state is SessionState.WRITTEN
        assert not (session_dir / NOTE_FILENAME).exists()  # note deleted first
        assert not (session_dir / KEY_FILENAME).exists()  # key destroyed
        assert controller.session is None
        assert not controller.generating  # lease consumed on success

    def test_completes_without_a_note_present(self, tmp_path: Path) -> None:
        controller, session_dir = self._queued_session(tmp_path)
        (session_dir / NOTE_FILENAME).unlink()  # no note.enc: delete_note is a no-op
        lease = controller.begin_generation()
        assert controller.complete_without_note(lease).state is SessionState.WRITTEN
        assert not (session_dir / KEY_FILENAME).exists()
        assert not controller.generating

    def test_refused_with_a_foreign_lease(self, tmp_path: Path) -> None:
        controller, session_dir = self._queued_session(tmp_path)
        controller.begin_generation()  # the held lease
        with pytest.raises(GenerationInProgressError):
            controller.complete_without_note(GenerationLease())  # not the held one
        assert (session_dir / KEY_FILENAME).is_file()  # nothing deleted
        assert (session_dir / NOTE_FILENAME).is_file()
        assert controller.generating  # the real lease survives

    def test_completion_failure_keeps_the_lease(self, tmp_path: Path) -> None:
        """Round 35 PR-MED-001 invariant: a failed complete-without-note must
        leave the lease held and the session QUEUED — never unleased."""
        controller, session_dir = self._queued_session(tmp_path)
        lease = controller.begin_generation()
        # Corrupt the transcript so complete_session's verify-decrypt fails
        # (InvalidTag) AFTER the note unlink -> completion raises, key retained.
        transcript_path = session_dir / TRANSCRIPT_FILENAME
        blob = bytearray(transcript_path.read_bytes())
        blob[-1] ^= 0xFF  # flip a GCM tag byte
        transcript_path.write_bytes(bytes(blob))
        with pytest.raises(StoreCorruptError):
            controller.complete_without_note(lease)
        assert controller.generating  # lease STILL held
        assert (session_dir / KEY_FILENAME).is_file()  # key retained
        assert controller.state is SessionState.QUEUED
        controller.end_generation(lease)  # cleanup


@windows_only
class TestCompleteDeletingSavedNote:
    """Round 36 PR-MED-001: the POST-Save (no-lease) delete-note-and-complete
    path — the note is already committed and no lease is held. Guarded like
    ``complete()`` (refused while generating / while a discard completes)."""

    def _queued_session(self, tmp_path: Path) -> tuple[SessionController, Path]:
        controller, _backend = _controller(tmp_path)
        session = start_unlinked(controller)
        session_dir = tmp_path / session.session_id
        controller.finish()
        controller.mark_queued()
        crypto = unwrap_key_from_file(session_dir)
        (session_dir / TRANSCRIPT_FILENAME).write_bytes(crypto.encrypt(b"transcript"))
        (session_dir / NOTE_FILENAME).write_bytes(crypto.encrypt(b"note"))
        return controller, session_dir

    def test_deletes_note_and_completes(self, tmp_path: Path) -> None:
        controller, session_dir = self._queued_session(tmp_path)
        session = controller.complete_deleting_saved_note()
        assert session.state is SessionState.WRITTEN
        assert not (session_dir / NOTE_FILENAME).exists()  # note deleted first
        assert not (session_dir / KEY_FILENAME).exists()  # key destroyed
        assert controller.session is None

    def test_refused_while_generating(self, tmp_path: Path) -> None:
        controller, session_dir = self._queued_session(tmp_path)
        lease = controller.begin_generation()
        with pytest.raises(GenerationInProgressError):
            controller.complete_deleting_saved_note()
        assert (session_dir / KEY_FILENAME).is_file()  # nothing deleted
        assert (session_dir / NOTE_FILENAME).is_file()
        controller.end_generation(lease)
        assert controller.complete_deleting_saved_note().state is SessionState.WRITTEN

    def test_failure_keeps_the_key(self, tmp_path: Path) -> None:
        controller, session_dir = self._queued_session(tmp_path)
        transcript_path = session_dir / TRANSCRIPT_FILENAME
        blob = bytearray(transcript_path.read_bytes())
        blob[-1] ^= 0xFF  # flip a GCM tag byte -> InvalidTag on decrypt
        transcript_path.write_bytes(bytes(blob))
        with pytest.raises(StoreCorruptError):
            controller.complete_deleting_saved_note()
        assert (session_dir / KEY_FILENAME).is_file()  # key retained
        assert controller.state is SessionState.QUEUED


# ---------------------------------------------------------------------------
# Cliniko workflow safeguards plan Task 3.3: consent, target and
# encounter.enc on start(), and D2's reference registry.
# ---------------------------------------------------------------------------


class _SimulatedCrash(BaseException):  # noqa: N818 - models a process death
    """Not an ``Exception``: start()'s failure cleanup does not run, exactly
    as when the process dies between two writes."""


def _read_record(directory: Path) -> EncounterRecord:
    return read_encounter_record(directory, unwrap_key_from_file(directory), directory.name)


class TestStartRefusesWithoutConsent:
    """Constraint 4 on the controller path (platform-neutral: the refusal
    happens before any custody write)."""

    @pytest.mark.parametrize("consent", [None, "yes", object()], ids=["none", "str", "object"])
    def test_start_without_a_consent_attestation_is_refused(
        self, tmp_path: Path, consent: Any
    ) -> None:
        controller, _ = _controller(tmp_path)
        with pytest.raises(ConsentRequiredError):
            controller.start(0, consent=consent)
        assert controller.session is None
        assert list(tmp_path.iterdir()) == []  # nothing created

    def test_start_with_no_consent_argument_is_a_type_error(self, tmp_path: Path) -> None:
        controller, _ = _controller(tmp_path)
        with pytest.raises(TypeError):
            controller.start(0)  # type: ignore[call-arg]
        assert list(tmp_path.iterdir()) == []

    @pytest.mark.parametrize(
        "consent_note, linked",
        [("2001", False), (None, True), ("2002", True)],
        ids=["unlinked-consent-names-a-note", "linked-consent-names-none", "another-note"],
    )
    def test_a_consent_that_does_not_name_the_note_is_refused(
        self, tmp_path: Path, consent_note: str | None, linked: bool
    ) -> None:
        controller, _ = _controller(tmp_path)
        consent = ConsentAttestation(confirmed_at=NOW, treatment_note_id=consent_note)
        with pytest.raises(ConsentRequiredError):
            controller.start(0, consent=consent, context=enc_context() if linked else None)
        assert list(tmp_path.iterdir()) == []

    def test_a_context_of_the_wrong_type_is_refused(self, tmp_path: Path) -> None:
        controller, _ = _controller(tmp_path)
        with pytest.raises(SessionControllerError):
            controller.start(
                0, consent=unlinked_consent(), context={"patient_id": "1"}  # type: ignore[arg-type]
            )
        assert list(tmp_path.iterdir()) == []


@windows_only
class TestEncounterRecordOnStart:
    def test_an_unlinked_start_records_its_consent(self, tmp_path: Path) -> None:
        controller, _ = _controller(tmp_path)
        consent = unlinked_consent()
        session = controller.start(0, consent=consent)
        directory = tmp_path / session.session_id
        assert session.consent == consent and session.encounter_context is None
        record = _read_record(directory)
        assert record.consent == consent and record.context is None
        controller.discard()

    def test_a_linked_start_records_consent_and_context(self, tmp_path: Path) -> None:
        controller, _ = _controller(tmp_path)
        ctx = enc_context()
        consent = consent_for(ctx)
        session = controller.start(0, consent=consent, context=ctx)
        assert session.encounter_context == ctx
        record = _read_record(tmp_path / session.session_id)
        assert record == EncounterRecord(consent=consent, context=ctx)
        controller.discard()

    def test_an_unverified_offline_start_records_the_same_way(self, tmp_path: Path) -> None:
        """The positive matrix case (the rest is in test_cross_patient.py)."""
        controller, _ = _controller(tmp_path)
        ctx = enc_context(Verification.UNVERIFIED_OFFLINE)
        session = controller.start(0, consent=consent_for(ctx), context=ctx)
        assert session.state is SessionState.RECORDING
        assert _read_record(tmp_path / session.session_id).context == ctx
        controller.discard()

    def test_every_start_writes_its_own_record(self, tmp_path: Path) -> None:
        controller, _ = _controller(tmp_path)
        first = start_unlinked(controller)
        controller.finish()
        controller.mark_queued()
        ctx = enc_context()
        second = controller.start(0, consent=consent_for(ctx), context=ctx)  # retires first
        assert _read_record(tmp_path / first.session_id).context is None
        assert _read_record(tmp_path / second.session_id).context == ctx
        controller.discard()

    def test_encounter_enc_is_written_after_the_key_and_before_audio(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop import session as session_mod

        order: list[tuple[str, bool, bool, bool]] = []
        real_write = session_mod.write_encounter_record
        real_create = session_mod.SessionChunkStore.create

        def seen(directory: Path) -> tuple[bool, bool, bool]:
            return (
                (directory / KEY_FILENAME).is_file(),
                (directory / ENCOUNTER_FILENAME).is_file(),
                (directory / AUDIO_FILENAME).exists(),
            )

        def spy_write(directory: Path, *args: Any) -> Any:
            order.append(("encounter", *seen(directory)))
            return real_write(directory, *args)

        def spy_create(path: Path, *args: Any, **kwargs: Any) -> Any:
            order.append(("audio", *seen(path.parent)))
            return real_create(path, *args, **kwargs)

        monkeypatch.setattr(session_mod, "write_encounter_record", spy_write)
        monkeypatch.setattr(session_mod.SessionChunkStore, "create", staticmethod(spy_create))
        controller, _ = _controller(tmp_path)
        start_unlinked(controller)
        # (step, key present, encounter present, audio present) at each write
        assert order == [("encounter", True, False, False), ("audio", True, True, False)]
        controller.discard()

    def test_a_crash_before_audio_leaves_the_consent_record_and_no_audio(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop import session as session_mod

        def crash(*_args: Any, **_kwargs: Any) -> Any:
            raise _SimulatedCrash()

        monkeypatch.setattr(session_mod.SessionChunkStore, "create", staticmethod(crash))
        controller, _ = _controller(tmp_path)
        with pytest.raises(_SimulatedCrash):
            start_unlinked(controller)
        (directory,) = list(tmp_path.iterdir())
        assert (directory / KEY_FILENAME).is_file()
        assert not (directory / AUDIO_FILENAME).exists()
        record = _read_record(directory)  # the consent outlives the crash
        assert record.consent.treatment_note_id is None

    def test_a_crash_before_the_encounter_write_leaves_no_audio(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop import session as session_mod

        def crash(*_args: Any, **_kwargs: Any) -> Any:
            raise _SimulatedCrash()

        monkeypatch.setattr(session_mod, "write_encounter_record", crash)
        controller, _ = _controller(tmp_path)
        with pytest.raises(_SimulatedCrash):
            start_unlinked(controller)
        (directory,) = list(tmp_path.iterdir())
        assert not (directory / AUDIO_FILENAME).exists()  # never audio without its record
        assert not (directory / ENCOUNTER_FILENAME).exists()

    def test_a_failed_encounter_write_cleans_up_and_creates_no_audio(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop import session as session_mod

        created: list[Path] = []

        def fail(*_args: Any, **_kwargs: Any) -> Any:
            raise StoreWriteError("failed writing encounter record: disk full")

        def spy_create(path: Path, *args: Any, **kwargs: Any) -> Any:
            created.append(path)
            raise AssertionError("audio.enc must not be created")

        monkeypatch.setattr(session_mod, "write_encounter_record", fail)
        monkeypatch.setattr(session_mod.SessionChunkStore, "create", staticmethod(spy_create))
        controller, _ = _controller(tmp_path)
        with pytest.raises(StoreWriteError):
            start_unlinked(controller)
        assert created == []
        assert list(tmp_path.iterdir()) == []  # the failure cleanup removed it all
        assert controller.session is None

    def test_discard_removes_the_record_with_the_session(self, tmp_path: Path) -> None:
        controller, _ = _controller(tmp_path)
        session = start_unlinked(controller)
        directory = tmp_path / session.session_id
        assert (directory / ENCOUNTER_FILENAME).is_file()
        controller.discard()
        assert not directory.exists()


@windows_only
class TestSessionRefs:
    """D2's reference registry (peer r2 PR-MED-001)."""

    def test_start_mints_an_opaque_ref_that_is_never_the_session_id(
        self, tmp_path: Path
    ) -> None:
        controller, _ = _controller(tmp_path)
        session = start_unlinked(controller)
        ref = controller.session_ref
        assert ref is not None and len(ref) == 24
        assert ref != session.session_id and session.session_id not in ref
        assert not re.fullmatch(r"[0-9a-f]{32}", ref)
        assert controller.resolve_session_ref(ref) == session.session_id
        assert ref not in [p.name for p in tmp_path.rglob("*")]  # never persisted as a name
        controller.discard()

    def test_each_start_gets_a_new_ref_and_retirement_keeps_the_old(
        self, tmp_path: Path
    ) -> None:
        controller, _ = _controller(tmp_path)
        first = start_unlinked(controller)
        first_ref = controller.session_ref
        controller.finish()
        controller.mark_queued()
        second = start_unlinked(controller)  # retires the first
        second_ref = controller.session_ref
        assert first_ref is not None and second_ref is not None and first_ref != second_ref
        assert controller.resolve_session_ref(first_ref) == first.session_id
        assert controller.resolve_session_ref(second_ref) == second.session_id
        controller.discard()

    def test_discard_and_complete_stop_the_ref_resolving(self, tmp_path: Path) -> None:
        controller, _ = _controller(tmp_path)
        start_unlinked(controller)
        ref = controller.session_ref
        assert ref is not None
        controller.discard()
        assert controller.resolve_session_ref(ref) is None

        session = start_unlinked(controller)
        ref = controller.session_ref
        assert ref is not None
        controller.finish()
        controller.mark_queued()
        directory = tmp_path / session.session_id
        crypto = unwrap_key_from_file(directory)
        (directory / TRANSCRIPT_FILENAME).write_bytes(crypto.encrypt(b"transcript"))
        controller.complete()
        assert controller.resolve_session_ref(ref) is None

    def test_a_recovered_discard_and_forget_remove_refs(self, tmp_path: Path) -> None:
        controller, _ = _controller(tmp_path)
        session = start_unlinked(controller)
        ref = controller.session_ref
        assert ref is not None
        controller.finish()
        controller.mark_queued()
        start_unlinked(controller)  # retires it: its ref still resolves
        assert controller.resolve_session_ref(ref) == session.session_id
        controller.discard_recovered(tmp_path / session.session_id, None)
        assert controller.resolve_session_ref(ref) is None
        live_ref = controller.session_ref
        assert live_ref is not None
        live_id = controller.resolve_session_ref(live_ref)
        assert live_id is not None
        controller.forget_session_ref(live_id)
        assert controller.resolve_session_ref(live_ref) is None
        controller.discard()

    def test_an_unknown_ref_resolves_to_nothing(self, tmp_path: Path) -> None:
        controller, _ = _controller(tmp_path)
        start_unlinked(controller)
        assert controller.resolve_session_ref("not-a-ref") is None
        controller.discard()
