"""Step 8: status/self-test logic tests + offscreen window smoke test.

Phase 2 Step 12 adds the single-instance guard battery (named mutex,
peer round 18 PR4 — priority raised by the 2026-07-28 live smoke).
"""

import os
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from conftest import start_unlinked, use_channel
from scribe_desktop.install_layout import Channel
from scribe_desktop.status import read_registration_status, run_self_test

windows_only = pytest.mark.skipif(
    sys.platform != "win32", reason="named mutexes are Windows-only"
)


def test_registration_status_reads_nothing_without_a_layer() -> None:
    """Installation plan Task 2.3 (C6): the reader goes through the Windows
    layer ``app.main`` builds; with none (every test) it reads no registry.
    The two former real-machine checks read this computer's HKCU entry —
    host state a test must not depend on (C6) — and their no-spaces rule is
    superseded by Task 0.2 (the installed host runs from Program Files). The
    reader's cases, through a fake layer: ``test_frozen_runtime.py``
    ``TestRegistrationStatus``."""
    status = read_registration_status(None)
    assert not status.checked
    assert not status.registered


def test_self_test_passes_end_to_end() -> None:
    results = run_self_test()
    assert [r.name for r in results] == ["credential_store", "session_crypto"]
    assert all(r.passed for r in results), [f"{r.name}: {r.detail}" for r in results]


@pytest.mark.skipif(os.environ.get("SCRIBE_SKIP_GUI") == "1", reason="GUI smoke disabled")
def test_window_offscreen_smoke(tmp_path) -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from scribe_desktop.audio_capture import MockCaptureBackend
    from scribe_desktop.clinics import ClinicRegistry
    from scribe_desktop.past_sessions import PastSessionStore
    from scribe_desktop.session import SessionController
    from scribe_desktop.ui import models
    from scribe_desktop.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    backend = MockCaptureBackend()
    controller = SessionController(backend, sessions_root=tmp_path / "sessions")
    window = MainWindow(
        controller,
        backend,
        sessions_root=tmp_path / "sessions",
        profile_root=tmp_path / "profile",
        config_root=tmp_path / "config",  # peer round 55 PR-LOW-041: off the real config
        style_root=tmp_path / "style",  # Phase H round 24 MED-006: never the real store
        language_model_available=lambda: False,  # nor the real model's presence
        # Cliniko safeguards Task 2.2: never the real clinics.json.
        clinic_registry=ClinicRegistry(tmp_path / "clinics.json"),
        # Privacy-professional-controls Task 3.1: never the real archive root.
        past_sessions=PastSessionStore(tmp_path / "past_sessions"),
    )
    panel = window.status_panel
    # Task 3.3 (D14): the intended-use line heads the Status tab.
    assert panel.intended_use_label.text() == models.INTENDED_USE_LINE
    assert "Registration:" in panel.registration_label.text()
    panel.on_self_test()
    assert "PASS" in panel.self_test_label.text()
    assert "FAIL" not in panel.self_test_label.text()
    window.close()
    del app


def test_sweep_protected_ids_covers_nonterminal_controller_session(tmp_path) -> None:
    """Round 42 MED-001 (guard-only, pending user ratification): the sweep
    exemption must include the controller's own session in ANY non-terminal
    state — a QUEUED transcript open for review must not lose its key at
    the 24 h boundary mid-review (PR-round-18 PR2 gave recovered checkouts
    this protection; the live path gets the same)."""
    from scribe_desktop.app import sweep_protected_ids
    from scribe_desktop.audio_capture import MockCaptureBackend
    from scribe_desktop.session import SessionController, SessionState

    controller = SessionController(MockCaptureBackend(), sessions_root=tmp_path)
    assert sweep_protected_ids(controller) == frozenset()

    session = start_unlinked(controller)
    assert session.session_id in sweep_protected_ids(controller)  # state-active

    controller.finish()
    controller.mark_queued()
    assert controller.state is SessionState.QUEUED
    # QUEUED is NOT state-active — the MED-001 widening must still cover it,
    # and extra ids (recovery checkouts) must pass through untouched.
    protected = sweep_protected_ids(controller, frozenset({"extra-checkout"}))
    assert session.session_id in protected
    assert "extra-checkout" in protected

    controller.discard()  # terminal: protection correctly lapses
    assert sweep_protected_ids(controller) == frozenset()


def test_sweep_protected_ids_covers_reserved_discard_targets(tmp_path) -> None:
    """Round 30 PR-MED-001: an in-flight Discard's reserved target must be
    sweep-protected FROM THE RESERVATION SET — the admitted concurrent
    start() can swap the live pointer mid-window, so the non-terminal-
    session rule alone stops naming the discarding session."""
    from scribe_desktop.app import sweep_protected_ids
    from scribe_desktop.audio_capture import MockCaptureBackend
    from scribe_desktop.session import SessionController

    controller = SessionController(MockCaptureBackend(), sessions_root=tmp_path)
    reserved_id = "f" * 32
    # Simulate a held reservation exactly as discard() holds one (the
    # controller-private helper is the single producer; deliberate injection).
    with controller._lock:  # noqa: SLF001
        controller._reserve_custody_locked(reserved_id)  # noqa: SLF001
    try:
        assert reserved_id in sweep_protected_ids(controller)
        assert reserved_id in controller.reserved_session_ids()
    finally:
        with controller._lock:  # noqa: SLF001
            controller._release_custody_locked(reserved_id)  # noqa: SLF001
    assert reserved_id not in sweep_protected_ids(controller)


def test_sweep_protected_ids_is_one_atomic_snapshot() -> None:
    """Round 31 PR-MED-001: sweep protection is ONE controller snapshot plus
    the extra checkouts — composing separate reserved/active/session reads
    was itself a race (a Discard-reserve + admitted Start between two reads
    yielded a set omitting the still-reserved target)."""
    from scribe_desktop.app import sweep_protected_ids

    class _Probe:
        def __init__(self) -> None:
            self.snapshot_calls = 0

        def custody_protected_ids(self) -> frozenset[str]:
            self.snapshot_calls += 1
            return frozenset({"a" * 32})

        def reserved_session_ids(self) -> frozenset[str]:
            raise AssertionError("split read: reserved_session_ids composed")

        def active_session_ids(self) -> frozenset[str]:
            raise AssertionError("split read: active_session_ids composed")

        @property
        def session(self) -> object:
            raise AssertionError("split read: session composed")

    probe = _Probe()
    protected = sweep_protected_ids(probe, frozenset({"extra-checkout"}))  # type: ignore[arg-type]
    assert protected == frozenset({"a" * 32, "extra-checkout"})
    assert probe.snapshot_calls == 1


def test_expiry_sweep_skips_reserved_discard_target(tmp_path) -> None:
    """Round 31 Verification: an ACTUAL expiry sweep driven by the atomic
    snapshot leaves a reserved directory intact; on release, the 24 h cap
    reclaims it — protection is transient by construction."""
    from datetime import timedelta

    from scribe_desktop.app import sweep_protected_ids
    from scribe_desktop.audio_capture import MockCaptureBackend
    from scribe_desktop.session import SessionController
    from scribe_desktop.session_store import sweep_sessions

    controller = SessionController(MockCaptureBackend(), sessions_root=tmp_path)
    reserved_id = "e" * 32
    directory = tmp_path / reserved_id
    directory.mkdir()
    (directory / "key.dpapi").write_bytes(b"\0" * 64)
    with controller._lock:  # noqa: SLF001 - discard() is the single producer; deliberate injection
        controller._reserve_custody_locked(reserved_id)  # noqa: SLF001
    try:
        results = sweep_sessions(
            tmp_path,
            active_session_ids=sweep_protected_ids(controller),
            max_age=timedelta(0),
        )
        assert [(r.session_id, r.action) for r in results] == [
            (reserved_id, "skipped_active")
        ]
        assert (directory / "key.dpapi").is_file()
    finally:
        with controller._lock:  # noqa: SLF001
            controller._release_custody_locked(reserved_id)  # noqa: SLF001
    results = sweep_sessions(
        tmp_path,
        active_session_ids=sweep_protected_ids(controller),
        max_age=timedelta(0),
    )
    assert [(r.session_id, r.action) for r in results] == [(reserved_id, "expired")]
    assert not directory.exists()


# ---------------------------------------------------------------------------
# Step 12: single-instance guard (named mutex; peer round 18 PR4)
# ---------------------------------------------------------------------------


def _unique_mutex_name() -> str:
    # Global\ deliberately: the production default uses the Global namespace,
    # so these tests also prove a standard user can create there.
    return f"Global\\ClinikoScribe-test-{uuid4().hex}"


@windows_only
class TestSingleInstanceLock:
    def test_first_acquire_owns_and_second_refuses(self) -> None:
        from scribe_desktop.app import acquire_single_instance_lock, release_single_instance_lock

        name = _unique_mutex_name()
        acquired, handle = acquire_single_instance_lock(name)
        assert acquired and handle
        try:
            assert acquire_single_instance_lock(name) == (False, 0)
        finally:
            release_single_instance_lock(handle)

    def test_released_lock_can_be_reacquired(self) -> None:
        from scribe_desktop.app import acquire_single_instance_lock, release_single_instance_lock

        name = _unique_mutex_name()
        acquired, handle = acquire_single_instance_lock(name)
        assert acquired
        release_single_instance_lock(handle)
        acquired_again, handle_again = acquire_single_instance_lock(name)
        assert acquired_again and handle_again
        release_single_instance_lock(handle_again)

    def test_busy_probe_does_not_pin_the_name(self) -> None:
        # The (False, 0) path must CLOSE the handle CreateMutexW returned:
        # a refused second launch must not keep the name alive after the
        # first instance exits.
        from scribe_desktop.app import acquire_single_instance_lock, release_single_instance_lock

        name = _unique_mutex_name()
        _, owner_handle = acquire_single_instance_lock(name)
        assert acquire_single_instance_lock(name) == (False, 0)
        release_single_instance_lock(owner_handle)
        acquired, handle = acquire_single_instance_lock(name)
        assert acquired and handle, "busy probe leaked a handle and pinned the mutex name"
        release_single_instance_lock(handle)

    def test_the_mutex_is_owned_by_this_user(self) -> None:
        # Round 57 SEC-015: created with an explicit owner (an elevated start
        # too), read back from the real mutex.
        import win32security

        from scribe_desktop.app import (
            _mutex_owner_sid,
            acquire_single_instance_lock,
            release_single_instance_lock,
        )
        from scribe_desktop.pipe_server import current_user_sid

        acquired, handle = acquire_single_instance_lock(_unique_mutex_name())
        assert acquired and handle
        try:
            assert _mutex_owner_sid(handle) == current_user_sid()
            # The owner alone matches a default mutex too (for a non-elevated
            # run); the protected, single-entry DACL is the descriptor's own.
            descriptor = win32security.GetSecurityInfo(
                handle, win32security.SE_KERNEL_OBJECT, win32security.DACL_SECURITY_INFORMATION
            )
            control, _revision = descriptor.GetSecurityDescriptorControl()
            assert control & 0x1000  # SE_DACL_PROTECTED
            dacl = descriptor.GetSecurityDescriptorDacl()
            assert dacl.GetAceCount() == 1
            (_ace_type, _flags), _mask, sid = dacl.GetAce(0)
            assert win32security.ConvertSidToStringSid(sid) == current_user_sid()
        finally:
            release_single_instance_lock(handle)

    def test_another_accounts_mutex_is_reported_not_held(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Round 57 SEC-015: an existing mutex owned by ANOTHER account (a
        # squat) does not refuse; our own instance's still refuses (the
        # control). Round 69 PR-MED-370: (True, 0) is "not held" — the lock
        # file then decides (TestInstanceExclusion), never a bare start.
        from scribe_desktop import app

        name = _unique_mutex_name()
        acquired, handle = app.acquire_single_instance_lock(name)
        assert acquired and handle
        try:
            assert app.acquire_single_instance_lock(name) == (False, 0)
            monkeypatch.setattr(app, "_mutex_owner_sid", lambda _handle: "S-1-5-21-1-2-3-1001")
            assert app.acquire_single_instance_lock(name) == (True, 0)
        finally:
            app.release_single_instance_lock(handle)

    def test_an_unreadable_sid_keeps_the_plain_guard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scribe_desktop import app
        from scribe_desktop.pipe_server import PipeUnavailable

        def unreadable() -> str:
            raise PipeUnavailable("create_failed")

        monkeypatch.setattr(app, "current_user_sid", unreadable)
        monkeypatch.setattr(app, "_mutex_owner_sid", lambda _handle: "S-1-5-21-1-2-3-1001")
        name = _unique_mutex_name()
        acquired, handle = app.acquire_single_instance_lock(name)
        assert acquired and handle
        try:
            # No SID: no owner check, so even a "foreign" owner still refuses.
            assert app.acquire_single_instance_lock(name) == (False, 0)
        finally:
            app.release_single_instance_lock(handle)

    def test_default_name_is_per_user_and_namespace_safe(self) -> None:
        from scribe_desktop.app import _single_instance_mutex_name

        name = _single_instance_mutex_name()
        assert name.startswith("Global\\ClinikoScribe-app-")
        # Backslash is the kernel object-namespace separator — the user part
        # must never introduce one.
        assert "\\" not in name.removeprefix("Global\\")


_FOREIGN_SID = "S-1-5-21-1-2-3-1001"

# Takes the exclusion in a separate process, says so with ITS OWN pid, and
# waits to be killed. The pid matters (round 70, the k15 run): the venv's
# python.exe is a launcher that runs the real interpreter as a CHILD, so
# `Popen.kill()` ends only the launcher while the interpreter — the process
# holding the handles — dies later (docs/lessons.md).
_HOLDER_CHILD = """
import os, sys, time
from pathlib import Path
from scribe_desktop import app
state = app.acquire_instance_exclusion(sys.argv[1], Path(sys.argv[2])).state
print(state, os.getpid(), flush=True)
time.sleep(120)
"""


def _read_line_within(stream: Any, seconds: float) -> bytes:
    """One line from ``stream``, or b"" if none arrives in ``seconds``."""
    import threading

    lines: list[bytes] = []
    reader = threading.Thread(target=lambda: lines.append(stream.readline()), daemon=True)
    reader.start()
    reader.join(seconds)
    return lines[0] if lines else b""


def _end_descendants(launcher: Any, seconds: float) -> None:
    """Kill every process ``launcher`` (a ``psutil.Process``) started, and
    wait (bounded) until each has exited. Nothing to do once the launcher
    itself is gone: it outlives its interpreter unless killed."""
    import psutil

    try:
        descendants = launcher.children(recursive=True)
    except psutil.NoSuchProcess:
        return
    for process in descendants:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass
    _gone, alive = psutil.wait_procs(descendants, timeout=seconds)
    assert not alive, f"still running after the kill: {alive}"


def _terminate_and_wait(pid: int, seconds: float) -> bool:
    """End process ``pid`` and wait until it has exited (its handles closed).
    False if it had already gone; raises if it is still alive afterwards."""
    import pywintypes
    import win32api
    import win32con
    import win32event

    try:
        handle = win32api.OpenProcess(win32con.PROCESS_TERMINATE | win32con.SYNCHRONIZE, False, pid)
    except pywintypes.error:
        return False
    try:
        try:
            win32api.TerminateProcess(handle, 1)
        except pywintypes.error:
            pass  # already exiting; the wait below decides
        waited = win32event.WaitForSingleObject(handle, int(seconds * 1000))
        assert waited == win32event.WAIT_OBJECT_0, f"process {pid} did not exit"
        return True
    finally:
        win32api.CloseHandle(handle)


@windows_only
class TestInstanceExclusion:
    """Rounds 69-70 (PR-MED-370, PR-MED-380): exactly one instance of this
    user's app runs in EVERY case. The per-user lock file is required for
    every admitted instance; the named mutex only refuses a normal second
    launch early, and admits nothing on its own.

    Every test uses a tmp lock path, never the real ``%LOCALAPPDATA%`` (an
    agent shell's is virtualized — docs/lessons.md). Another account's squat
    is simulated by reading this user's own mutex as foreign-owned. What no
    test here can prove: a REAL second Windows account's mutex, and that
    such an account cannot open or create the lock file inside this user's
    profile (that rests on the profile's ACL)."""

    def test_the_normal_path_holds_both_and_refuses_a_second_launch(
        self, tmp_path: Path
    ) -> None:
        from scribe_desktop import app

        name, lock = _unique_mutex_name(), tmp_path / "app.lock"
        first = app.acquire_instance_exclusion(name, lock)
        try:
            assert first.state == "acquired" and len(first.handles) == 2
            assert app.acquire_instance_exclusion(name, lock) == ("already_running", ())
        finally:
            app.release_instance_exclusion(first)
        again = app.acquire_instance_exclusion(name, lock)
        assert again.state == "acquired"
        app.release_instance_exclusion(again)

    def test_a_squatted_name_admits_exactly_one_instance(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop import app

        name, lock = _unique_mutex_name(), tmp_path / "app.lock"
        squatter, squat_handle = app.acquire_single_instance_lock(name)
        assert squatter and squat_handle
        monkeypatch.setattr(app, "_mutex_owner_sid", lambda _handle: _FOREIGN_SID)
        try:
            first = app.acquire_instance_exclusion(name, lock)
            assert first.state == "acquired" and len(first.handles) == 1  # the file only
            try:
                # The PR-MED-370 case: before the fix this launch ran too.
                assert app.acquire_instance_exclusion(name, lock).state == "already_running"
            finally:
                app.release_instance_exclusion(first)
            later = app.acquire_instance_exclusion(name, lock)
            assert later.state == "acquired"
            app.release_instance_exclusion(later)
        finally:
            app.release_single_instance_lock(squat_handle)

    def test_the_squatter_leaving_does_not_admit_a_second_instance(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # An instance that started on the lock file alone keeps a later launch
        # out even once the name is free and that launch holds the mutex —
        # and the refused launch gives the name back.
        from scribe_desktop import app

        name, lock = _unique_mutex_name(), tmp_path / "app.lock"
        _, squat_handle = app.acquire_single_instance_lock(name)
        monkeypatch.setattr(app, "_mutex_owner_sid", lambda _handle: _FOREIGN_SID)
        first = app.acquire_instance_exclusion(name, lock)
        app.release_single_instance_lock(squat_handle)  # the squatter leaves
        try:
            assert first.state == "acquired"
            assert app.acquire_instance_exclusion(name, lock).state == "already_running"
            probe, probe_handle = app.acquire_single_instance_lock(name)
            assert probe and probe_handle, "the refused launch pinned the mutex name"
            app.release_single_instance_lock(probe_handle)
        finally:
            app.release_instance_exclusion(first)

    def test_no_mutex_and_no_lock_file_refuses_to_start(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop import app

        # CreateMutexW failed (or the name is another account's), and the lock
        # file cannot be created: its parent is a file.
        monkeypatch.setattr(app, "acquire_single_instance_lock", lambda name=None: (True, 0))
        blocker = tmp_path / "not-a-folder"
        blocker.write_bytes(b"")
        assert app.acquire_instance_exclusion(None, blocker / "app.lock") == ("unavailable", ())

    def test_no_mutex_with_the_lock_file_held_starts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop import app

        monkeypatch.setattr(app, "acquire_single_instance_lock", lambda name=None: (True, 0))
        lock = tmp_path / "app.lock"
        first = app.acquire_instance_exclusion(None, lock)
        try:
            assert first.state == "acquired" and len(first.handles) == 1
            assert app.acquire_instance_exclusion(None, lock).state == "already_running"
        finally:
            app.release_instance_exclusion(first)

    def test_a_held_mutex_with_a_failed_lock_file_refuses_to_start(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Round 70 PR-MED-380, the overlapping-lifetimes regression. Before
        # the fix, A started on the mutex alone while the file would not open;
        # later B, whose CreateMutexW failed, opened the file and started too.
        # A must now refuse, so B can never run beside it. A's refusal also
        # gives the name back.
        from scribe_desktop import app

        name, lock = _unique_mutex_name(), tmp_path / "app.lock"
        blocker = tmp_path / "not-a-folder"
        blocker.write_bytes(b"")
        assert app.acquire_instance_exclusion(name, blocker / "app.lock") == ("unavailable", ())
        probe, probe_handle = app.acquire_single_instance_lock(name)
        assert probe and probe_handle, "the refused launch pinned the mutex name"
        app.release_single_instance_lock(probe_handle)
        # B: the file now opens and its mutex failed — it is the only one.
        monkeypatch.setattr(app, "acquire_single_instance_lock", lambda name=None: (True, 0))
        b = app.acquire_instance_exclusion(name, lock)
        try:
            assert b.state == "acquired"
            assert app.acquire_instance_exclusion(name, lock).state == "already_running"
        finally:
            app.release_instance_exclusion(b)

    @pytest.mark.parametrize("mutex", ["created", "foreign_or_failed"])
    def test_a_lock_file_held_by_another_instance_is_already_running(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutex: str
    ) -> None:
        # Whatever the mutex does, the file decides: the holder here took it
        # under a DIFFERENT mutex name, so the launch's own mutex is free.
        from scribe_desktop import app

        lock = tmp_path / "app.lock"
        holder = app.acquire_instance_exclusion(_unique_mutex_name(), lock)
        assert holder.state == "acquired"
        try:
            name = _unique_mutex_name()
            if mutex == "foreign_or_failed":
                monkeypatch.setattr(
                    app, "acquire_single_instance_lock", lambda name=None: (True, 0)
                )
            assert app.acquire_instance_exclusion(name, lock) == ("already_running", ())
            if mutex == "created":
                probe, probe_handle = app.acquire_single_instance_lock(name)
                assert probe and probe_handle, "the refused launch pinned the mutex name"
                app.release_single_instance_lock(probe_handle)
        finally:
            app.release_instance_exclusion(holder)

    def test_a_killed_instances_lock_is_released_by_windows(self, tmp_path: Path) -> None:
        # A crash never strands the lock: Windows closes a dead process's
        # handles, so the next launch starts. The process killed is the one
        # that HOLDS the handles (its own pid), and the next launch runs only
        # once it has provably exited.
        import subprocess

        import psutil

        from scribe_desktop import app

        name, lock = _unique_mutex_name(), tmp_path / "app.lock"
        child = subprocess.Popen(
            [sys.executable, "-c", _HOLDER_CHILD, name, str(lock)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        try:
            # Taken at once, while the launcher certainly runs. Its pid cannot
            # be reused while `child` holds its process handle (until the
            # end of this test), so its descendants below are ours.
            launcher = psutil.Process(child.pid)
            try:
                assert child.stdout is not None
                words = _read_line_within(child.stdout, 60).split()
                assert words[:1] == [b"acquired"] and len(words) == 2, words
                holder_pid = int(words[1])
                assert app.acquire_instance_exclusion(name, lock).state == "already_running"
                assert _terminate_and_wait(holder_pid, 30), "the holder exited before the kill"
            finally:
                # Round 71 PR-LOW-391: whatever failed above — before the pid
                # handshake too — no process the launcher started survives.
                _end_descendants(launcher, 30)
        finally:
            # Nested: a failing descendant kill never skips the launcher's.
            child.kill()
            child.wait(timeout=60)
            if child.stdout is not None:
                child.stdout.close()
        after = app.acquire_instance_exclusion(name, lock)
        try:
            assert after.state == "acquired"
        finally:
            app.release_instance_exclusion(after)

    def test_the_default_lock_file_is_in_this_users_app_folder(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scribe_desktop import app

        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert app.default_instance_lock_path() == tmp_path / "ClinikoScribe" / "app.lock"
        assert not (tmp_path / "ClinikoScribe").exists()  # computing it creates nothing

    # Installation plan Task 1.5 (D3): ONE guard across both channels.

    @pytest.mark.parametrize("which", ["production", "dev"])
    def test_both_channels_use_the_same_lock_file_and_mutex_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, which: Channel
    ) -> None:
        from scribe_desktop import app, install_layout

        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        production_name = app._single_instance_mutex_name()
        use_channel(monkeypatch, which)
        assert app.default_instance_lock_path() == tmp_path / "ClinikoScribe" / "app.lock"
        assert app._single_instance_mutex_name() == production_name
        # ... while the channel's own data folder is the dev one in dev.
        expected = "ClinikoScribe" if which == "production" else "ClinikoScribe-dev"
        assert install_layout.data_root() == tmp_path / expected
        assert not tmp_path.joinpath("ClinikoScribe").exists()

    @pytest.mark.parametrize("first", ["production", "dev"])
    @pytest.mark.parametrize("mutex", ["created", "foreign_or_failed"])
    def test_whichever_channel_starts_first_excludes_the_other(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, first: Channel, mutex: str
    ) -> None:
        # Through the seam: the default lock path (LOCALAPPDATA redirected),
        # one channel's instance holding it, the other channel's launch
        # refused — with the mutex working, and with only the file deciding.
        from scribe_desktop import app

        second: Channel = "dev" if first == "production" else "production"
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        if mutex == "foreign_or_failed":
            monkeypatch.setattr(app, "acquire_single_instance_lock", lambda name=None: (True, 0))
        name = _unique_mutex_name()
        use_channel(monkeypatch, first)
        holder = app.acquire_instance_exclusion(name)
        assert holder.state == "acquired"
        try:
            use_channel(monkeypatch, second)
            assert app.acquire_instance_exclusion(name) == ("already_running", ())
        finally:
            app.release_instance_exclusion(holder)
        after = app.acquire_instance_exclusion(name)
        try:
            assert after.state == "acquired"
        finally:
            app.release_instance_exclusion(after)
        # Only the shared lock file was made in the production folder.
        assert sorted(p.name for p in (tmp_path / "ClinikoScribe").iterdir()) == ["app.lock"]
        assert not (tmp_path / "ClinikoScribe-dev").exists()


@windows_only
def test_main_refuses_to_start_without_an_exclusion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Round 69 PR-MED-370: neither the mutex nor the lock file held -> a
    plain refusal and exit 1 BEFORE any backend, controller or sweep."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import logging

    from PySide6.QtWidgets import QApplication

    from scribe_desktop import app as app_module

    warned: list[str] = []
    monkeypatch.setattr(
        app_module, "setup_logging", lambda name: logging.getLogger("test-no-exclusion")
    )
    # Privacy-professional-controls Task 4.1 (C6): never this process's hooks.
    monkeypatch.setattr(app_module, "install_exception_hooks", lambda logger: lambda: None)
    monkeypatch.setattr(app_module, "apply_offline_env", lambda: None)
    monkeypatch.setattr(app_module, "assert_offline_env", lambda: None)
    monkeypatch.setattr(
        app_module,
        "acquire_instance_exclusion",
        lambda name=None, lock_path=None: app_module.InstanceExclusion("unavailable"),
    )
    monkeypatch.setattr(app_module, "_show_cannot_start_warning", lambda: warned.append("cannot"))
    monkeypatch.setattr(
        app_module, "_show_already_running_warning", lambda: warned.append("running")
    )
    monkeypatch.setattr(
        app_module, "QApplication", lambda argv: QApplication.instance() or QApplication(argv)
    )
    monkeypatch.setattr(
        app_module,
        "SoundDeviceBackend",
        lambda: (_ for _ in ()).throw(AssertionError("refused start touched the backend")),
    )
    assert app_module.main() == 1
    assert warned == ["cannot"]


@windows_only
def test_main_refuses_second_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() wiring: a refused lock shows the warning and exits 0 BEFORE any
    backend/controller/sweep exists (no MainWindow, no sessions-root touch)."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import logging

    from PySide6.QtWidgets import QApplication

    from scribe_desktop import app as app_module

    warned: list[str] = []
    # Round 57 SEC-012: never the practitioner's real scribe-app.log, and no
    # offline switches left set on the pytest process.
    monkeypatch.setattr(
        app_module, "setup_logging", lambda name: logging.getLogger("test-second-instance")
    )
    # Privacy-professional-controls Task 4.1 (C6): never this process's hooks.
    monkeypatch.setattr(app_module, "install_exception_hooks", lambda logger: lambda: None)
    monkeypatch.setattr(app_module, "apply_offline_env", lambda: None)
    monkeypatch.setattr(app_module, "assert_offline_env", lambda: None)
    monkeypatch.setattr(
        app_module,
        "acquire_instance_exclusion",
        lambda name=None, lock_path=None: app_module.InstanceExclusion("already_running"),
    )
    monkeypatch.setattr(
        app_module, "_show_already_running_warning", lambda: warned.append("warned")
    )
    # A QApplication may already exist in this pytest process; main()'s
    # unconditional QApplication([]) is only valid in a fresh app process.
    monkeypatch.setattr(
        app_module, "QApplication", lambda argv: QApplication.instance() or QApplication(argv)
    )
    # Guard proof: the refusal path must return before SoundDeviceBackend is
    # even constructed — poison it so any touch fails loudly.
    monkeypatch.setattr(
        app_module,
        "SoundDeviceBackend",
        lambda: (_ for _ in ()).throw(AssertionError("refused instance touched the backend")),
    )
    # Installation plan round 35 MED-001: nor starts the ML import warm-up.
    monkeypatch.setattr(
        app_module,
        "ImportWarmup",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("refused instance warmed up")),
    )
    assert app_module.main() == 0
    assert warned == ["warned"]
