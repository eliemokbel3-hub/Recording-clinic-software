"""Measure how long a stalled microphone callback this computer's input
stream survives (capture-overflow plan Task 0.1; D5, D7; C3, C4).

A recording ends when PortAudio reports dropped input frames (the app never
keeps a silent gap). This tool opens the microphone the way the app does
(16 kHz mono PCM16, 100 ms blocks), once with the default buffer and once per
candidate ``latency=`` value, and measures - under the rule FROZEN in the
plan's D5 before any run - which is the smallest buffer that survives a 2.0 s
stall of the callback without changing the stream's cadence, its tail at a
stop, or its open and close times. The script adds no measurement rule of its
own: every trial, count and time is D5's sampling protocol.

Run it YOURSELF from a normal PowerShell (never an agent shell), outside
clinic hours, with Clinic Scribe closed (either build). About 20 minutes:

    & 'C:\\Recording clinic software\\.venv\\Scripts\\python.exe' 'C:\\Recording clinic software\\.claude\\worktrees\\plan-run3-leftovers-8f7c7f\\scripts\\measure-capture-stall.py'

The same command with one option added:

- ``--list``: ids, host words and names, on screen only;
- ``--device <id>``: when the Microphone tab's choice is not the default input;
- ``--product``: after the build, the same stall and stop rows through the
  app's own ``SoundDeviceBackend.open_stream`` (set ``$env:PYTHONPATH`` to the
  checkout's ``desktop\\src`` first, so the built code is the one imported).

Custody (C3, C4). It keeps NO audio: a block's length is counted and the block
dropped; it writes no file of its own and no logger is called (holding the
app's single-instance lock opens, and creates when absent, the app's empty
``app.lock``). The paste block holds numbers, a device id, a host word,
library versions and which checkout's ``audio_capture`` was imported (the
word ``this checkout`` or ``another checkout``; no path is printed) - never a
device name (``--list`` shows names on screen only; do not paste that). A
failure during the measurement is reported by its exception TYPE only (never
its text or a traceback). It refuses (exit 2) before any stream unless Windows crash
reporting is excluded for the running interpreter (``exclusions.check_tool_wer``,
as ``measure-speakers.py``) and it holds the app's single-instance lock for
its run, so neither build can start meanwhile.

The scoring stall is ``time.sleep(S)`` inside the callback. One confirmation
row holds the interpreter lock instead (``ctypes.PyDLL``), after a self-check
that the hold really stops a second thread.

Every time is ``time.perf_counter_ns()`` taken at callback entry (the same
clock as ``perf_counter``, read as whole nanoseconds so the half-block tie of
D5's lost-block verdict is exact). Comparisons are made on unrounded values;
the paste block rounds to whole milliseconds for display only.
"""

from __future__ import annotations

import argparse
import ctypes
import os
import random
import statistics
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from math import ceil
from typing import Any, Final, Protocol

MS: Final = 1_000_000
SECOND: Final = 1_000_000_000
# The app's block: 1600 frames at 16 kHz (``audio_capture.BLOCK_FRAMES``).
BLOCK_NS: Final = 100 * MS

# --- D5, frozen 2026-11-26 before any run -------------------------------------------------
CANDIDATES: Final[tuple[float, ...]] = (1.0, 2.0, 2.5, 3.0)
PREMISE_STALL_S: Final = 0.3
PREMISE_TRIALS: Final = 5
PREMISE_MIN_FLAGS: Final = 4
SCORING_STALL_S: Final = 2.0
SCORING_TRIALS: Final = 10
STALL_PLAN: Final[tuple[tuple[float, int], ...]] = (
    (PREMISE_STALL_S, PREMISE_TRIALS),
    (1.0, 5),
    (SCORING_STALL_S, SCORING_TRIALS),
    (3.0, 5),
)
LEAD_CALLBACKS: Final = 10  # the stall is injected in the callback after these
MIN_TAIL_CALLBACKS: Final = 3
TAIL_TRIALS: Final = 20
CADENCE_LOW_NS: Final = 80 * MS
CADENCE_HIGH_NS: Final = 120 * MS
CADENCE_P99_NS: Final = 250 * MS
TAIL_EXTRA_NS: Final = 50 * MS
TAIL_MAX_NS: Final = 200 * MS
STOP_EXTRA_NS: Final = 250 * MS
FIRST_EXTRA_NS: Final = 250 * MS

HOST_WORDS: Final[Mapping[str, str]] = {
    "MME": "mme",
    "Windows DirectSound": "directsound",
    "Windows WASAPI": "wasapi",
    "Windows WDM-KS": "wdmks",
}
BARS: Final = ("a", "b", "c", "d", "e")
PRODUCT_BARS: Final = ("a", "c", "d", "e")  # --product runs no cadence row


@dataclass(frozen=True)
class Schedule:
    """How long each part of the measurement runs. The defaults ARE D5's
    protocol; the tests pass a short one to a fake stream."""

    block_ns: int = BLOCK_NS
    lead: int = LEAD_CALLBACKS
    observe_ns: int = SECOND
    tail_window_ns: int = SECOND // 2
    cadence_ns: int = 20 * SECOND
    tail_run_ns: int = 5 * SECOND
    tail_jitter_ns: int = 100 * MS
    tail_trials: int = TAIL_TRIALS
    stall_plan: tuple[tuple[float, int], ...] = STALL_PLAN
    candidates: tuple[float, ...] = CANDIDATES
    stop_stall_s: float = 1.0
    lock_hold_s: float = 0.5
    wait_s: float = 10.0


DEFAULT_SCHEDULE: Final = Schedule()


# --- the figures (pure) -------------------------------------------------------------------


def host_word(name: str) -> str:
    """PortAudio's host API name as one fixed word; anything else is ``other``."""
    return HOST_WORDS.get(name, "other")


def nearest_rank(values: Sequence[int], share: float) -> int | None:
    """The nearest-rank percentile, the sorted value at rank ``ceil(share x n)``,
    as ``guard_eval._percentile`` computes it; None for none."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, ceil(share * len(ordered)) - 1)]


def stall_residual_ns(
    entries: Sequence[int],
    t_abort: int,
    *,
    block_ns: int = BLOCK_NS,
    lead: int = LEAD_CALLBACKS,
    tail_window_ns: int = SECOND // 2,
) -> int | None:
    """D5's lost-block residual for one stall trial, in nanoseconds (one block
    is ``block_ns``). ``entries[i - 1]`` is the entry time of the trial's i-th
    callback. ``T0`` is the earliest phase among the first ``lead`` callbacks;
    the tail set is every callback entered in the last ``tail_window_ns``
    before ``t_abort``; the residual is the smallest ``e_j - T0 - j x block``
    over the tail set. None when the trial is invalid: fewer than ``lead``
    callbacks, or fewer than three in the tail set."""
    if len(entries) < lead:
        return None
    origin = min(entries[i - 1] - i * block_ns for i in range(1, lead + 1))
    tail = [
        entry - origin - number * block_ns
        for number, entry in enumerate(entries, start=1)
        if t_abort - tail_window_ns <= entry < t_abort
    ]
    if len(tail) < MIN_TAIL_CALLBACKS:
        return None
    return min(tail)


def lost_blocks(residual_ns: int, block_ns: int = BLOCK_NS) -> int:
    """``max(0, floor(residual + 0.5))`` in blocks - for display only; the
    verdict reads the residual (``trial_passes``)."""
    return max(0, (2 * residual_ns + block_ns) // (2 * block_ns))


def tail_ns(t_first: int, t_abort: int, blocks: int, block_ns: int = BLOCK_NS) -> int:
    """D5 (c): the audio the clock says was captured by the abort call, less
    the blocks delivered before it."""
    return (t_abort - t_first) + block_ns - block_ns * blocks


@dataclass(frozen=True)
class StallTrial:
    flagged: bool
    residual_ns: int | None  # None: an invalid trial
    flag_offset: int | None = None  # 0 = the stalled callback itself, 1 = the next


def trial_passes(trial: StallTrial, block_ns: int = BLOCK_NS) -> bool:
    """No flag, and a residual STRICTLY below half a block (a tie fails)."""
    return (
        not trial.flagged and trial.residual_ns is not None and 2 * trial.residual_ns < block_ns
    )


@dataclass(frozen=True)
class StopInStall:
    stop_ns: int
    undelivered_ns: int
    late_callbacks: int


@dataclass(frozen=True)
class Row:
    """One buffer's figures. ``latency`` None is the default row."""

    label: str
    latency: float | None
    refused: bool = False
    read_back_s: float | None = None
    gaps_ns: tuple[int, ...] = ()
    cadence_flags: int | None = None
    stalls: Mapping[float, tuple[StallTrial, ...]] = field(default_factory=dict)
    tails_ns: tuple[int, ...] = ()
    stops_ns: tuple[int, ...] = ()
    firsts_ns: tuple[int, ...] = ()
    stop_in_stall: StopInStall | None = None


@dataclass(frozen=True)
class RuleResult:
    premise_met: bool
    chosen: float | None
    # Per candidate label: each bar's verdict; None = not evaluated (refused).
    bars: Mapping[str, Mapping[str, bool | None]]


def _premise(default: Row | None) -> bool:
    if default is None or default.refused:
        return False
    trials = default.stalls.get(PREMISE_STALL_S, ())
    return (
        len(trials) == PREMISE_TRIALS
        and sum(trial.flagged for trial in trials) >= PREMISE_MIN_FLAGS
    )


def _bar_a(row: Row) -> bool:
    trials = row.stalls.get(SCORING_STALL_S, ())
    return len(trials) == SCORING_TRIALS and all(trial_passes(trial) for trial in trials)


def _bar_b(row: Row) -> bool:
    if not row.gaps_ns or row.cadence_flags != 0:
        return False
    p99 = nearest_rank(row.gaps_ns, 0.99)
    median = statistics.median(row.gaps_ns)
    return CADENCE_LOW_NS <= median <= CADENCE_HIGH_NS and p99 is not None and p99 <= CADENCE_P99_NS


def _full(values: Sequence[int]) -> bool:
    return len(values) == TAIL_TRIALS


def _bar_c(row: Row, default: Row | None) -> bool:
    if default is None or not _full(row.tails_ns) or not _full(default.tails_ns):
        return False
    extra = statistics.median(row.tails_ns) - statistics.median(default.tails_ns)
    return extra <= TAIL_EXTRA_NS and max(row.tails_ns) <= TAIL_MAX_NS


def _bar_median(candidate: Sequence[int], default: Sequence[int] | None, extra_ns: int) -> bool:
    if default is None or not _full(candidate) or not _full(default):
        return False
    return statistics.median(candidate) <= statistics.median(default) + extra_ns


def evaluate(host: str, rows: Sequence[Row]) -> RuleResult:
    """D5's rule, whole: the premise on the default row, each candidate's bars
    (a)-(e), and the smallest candidate that meets all five - chosen only on
    MME with the premise met. Never raises: a missing figure fails its bar, and
    a candidate that would not open fails (a) with the rest not evaluated."""
    default = next((row for row in rows if row.latency is None), None)
    candidates = sorted(
        (row for row in rows if row.latency is not None), key=lambda row: row.latency or 0.0
    )
    bars: dict[str, dict[str, bool | None]] = {}
    for row in candidates:
        if row.refused:
            bars[row.label] = {"a": False, "b": None, "c": None, "d": None, "e": None}
            continue
        bars[row.label] = {
            "a": _bar_a(row),
            "b": _bar_b(row),
            "c": _bar_c(row, default),
            "d": _bar_median(row.stops_ns, default.stops_ns if default else None, STOP_EXTRA_NS),
            "e": _bar_median(
                row.firsts_ns, default.firsts_ns if default else None, FIRST_EXTRA_NS
            ),
        }
    premise = _premise(default)
    chosen: float | None = None
    if host == "mme" and premise:
        chosen = next(
            (row.latency for row in candidates if all(bars[row.label][bar] for bar in BARS)),
            None,
        )
    return RuleResult(premise, chosen, bars)


# --- one stream at a time -----------------------------------------------------------------


class OpenRefused(Exception):
    """The stream would not open (PortAudio's text is never kept)."""


class Recorder:
    """What one trial's callbacks record: entry times and flags. The block
    itself is counted and dropped (C4)."""

    def __init__(self, stall_at: int | None = None, stall_s: float = 0.0) -> None:
        self.entries: list[int] = []
        self.flagged: list[int] = []  # the number of the callback each flag was seen on
        self.frames = 0
        self.first = threading.Event()
        self.reached = threading.Event()  # callback ``stall_at`` has entered
        self.returned = threading.Event()  # ... and its stall is over
        self.returned_ns = 0
        self._stall_at = stall_at
        self._stall_s = stall_s

    def block(self, frames: int) -> None:
        now = time.perf_counter_ns()
        self.entries.append(now)
        self.frames += frames
        number = len(self.entries)
        if number == 1:
            self.first.set()
        if number == self._stall_at:
            self.reached.set()
            if self._stall_s > 0:
                time.sleep(self._stall_s)
            self.returned_ns = time.perf_counter_ns()
            self.returned.set()

    def flag(self) -> None:
        self.flagged.append(len(self.entries))


# A stream opener: starts a stream feeding the recorder, and returns how to
# stop it (abort, then close) and the read-back latency in seconds, if any.
OpenFn = Callable[[Recorder], tuple[Callable[[], None], float | None]]


def raw_opener(sd: Any, capture: Any, device: int, latency: float | None) -> OpenFn:
    """The app's own stream arguments, with ``latency=`` only for a candidate."""

    def open_stream(recorder: Recorder) -> tuple[Callable[[], None], float | None]:
        def callback(indata: Any, frames: int, time_info: object, status: object) -> None:
            recorder.block(frames)
            if status:
                recorder.flag()

        kwargs: dict[str, Any] = {
            "samplerate": capture.SAMPLE_RATE,
            "blocksize": capture.BLOCK_FRAMES,
            "device": device,
            "channels": capture.CHANNELS,
            "dtype": "int16",
            "callback": callback,
        }
        if latency is not None:
            kwargs["latency"] = latency
        stream: Any = None
        try:
            stream = sd.RawInputStream(**kwargs)
            stream.start()
        except sd.PortAudioError:
            if stream is not None:
                stream.close(ignore_errors=True)
            raise OpenRefused from None
        except BaseException:
            if stream is not None:
                stream.close(ignore_errors=True)
            raise

        def stop() -> None:
            try:
                stream.abort()
            finally:
                stream.close()

        try:
            read_back: float | None = float(stream.latency)
        except (TypeError, ValueError):
            read_back = None
        return stop, read_back

    return open_stream


def product_opener(capture: Any, backend: Any, device: int) -> OpenFn:
    """The app's own ``SoundDeviceBackend.open_stream``: the stall sleeps
    inside ``on_block`` and a flag is an ``on_error`` call (whose exception,
    which can carry PortAudio's text, is dropped unread)."""

    def open_stream(recorder: Recorder) -> tuple[Callable[[], None], float | None]:
        def on_block(block: bytes) -> None:
            recorder.block(len(block) // capture.SAMPLE_WIDTH)

        def on_error(error: Exception) -> None:
            recorder.flag()

        try:
            handle = backend.open_stream(device, on_block, on_error)
        except capture.AudioCaptureError:
            raise OpenRefused from None
        return handle.stop, None

    return open_stream


def _sleep_until(target_ns: int) -> None:
    remaining = target_ns - time.perf_counter_ns()
    if remaining > 0:
        time.sleep(remaining / SECOND)


def run_cadence(
    open_fn: OpenFn, sched: Schedule
) -> tuple[tuple[int, ...], int | None, float | None]:
    """D5 (b): one open, ``cadence_ns`` from the first callback. The gaps
    between consecutive callback entries, the flag count (None when no
    callback ever arrived, and also when callbacks stopped arriving before the
    window ended - the last one more than ``CADENCE_P99_NS`` before its end -
    so a short healthy prefix is never scored as the full window) and the
    read-back latency."""
    recorder = Recorder()
    stop, read_back = open_fn(recorder)
    end = 0
    try:
        if recorder.first.wait(sched.wait_s):
            end = recorder.entries[0] + sched.cadence_ns
            _sleep_until(end)
    finally:
        stop()
    if not end:
        return (), None, read_back
    entries = [entry for entry in recorder.entries if entry <= end]
    gaps = tuple(later - earlier for earlier, later in zip(entries, entries[1:], strict=False))
    if entries[-1] < end - CADENCE_P99_NS:
        # Callbacks stopped before the window ended: the observation is incomplete.
        return gaps, None, read_back
    flags = sum(1 for number in recorder.flagged if number <= len(entries))
    return gaps, flags, read_back


def run_stall_trial(open_fn: OpenFn, stall_s: float, sched: Schedule) -> StallTrial:
    """D5's stall trial: ``lead`` callbacks arrive; the next one sleeps
    ``stall_s`` after its block is counted; observe ``observe_ns`` after it
    returns; then abort. Its own open and its own stream."""
    stall_at = sched.lead + 1
    recorder = Recorder(stall_at=stall_at, stall_s=stall_s)
    stop, _ = open_fn(recorder)
    t_abort = 0
    try:
        patience = sched.wait_s + stall_at * sched.block_ns / SECOND + stall_s
        if recorder.returned.wait(patience):
            _sleep_until(recorder.returned_ns + sched.observe_ns)
            t_abort = time.perf_counter_ns()
    finally:
        stop()
    flags = [number for number in recorder.flagged if number >= stall_at]
    offset = flags[0] - stall_at if flags else None
    if not t_abort:
        return StallTrial(bool(flags), None, offset)
    residual = stall_residual_ns(
        recorder.entries,
        t_abort,
        block_ns=sched.block_ns,
        lead=sched.lead,
        tail_window_ns=sched.tail_window_ns,
    )
    return StallTrial(bool(flags), residual, offset)


def run_tail_trial(
    open_fn: OpenFn, sched: Schedule, rng: random.Random
) -> tuple[int, int, int] | None:
    """D5 (c)-(e), one open: the tail at the abort call, the time from just
    before ``abort()`` to the return of ``close()``, and the time from just
    before the stream's constructor to the first callback's entry. None when
    no callback ever arrived (the figure is then missing)."""
    recorder = Recorder()
    t_open = time.perf_counter_ns()
    stop, _ = open_fn(recorder)
    t_abort = 0
    try:
        if recorder.first.wait(sched.wait_s):
            jitter = rng.randrange(sched.tail_jitter_ns + 1)
            _sleep_until(recorder.entries[0] + sched.tail_run_ns + jitter)
            t_abort = time.perf_counter_ns()
    finally:
        stop()
    t_closed = time.perf_counter_ns()
    if not t_abort:
        return None
    t_first = recorder.entries[0]
    blocks = sum(1 for entry in recorder.entries if entry < t_abort)
    return (
        tail_ns(t_first, t_abort, blocks, sched.block_ns),
        t_closed - t_abort,
        t_first - t_open,
    )


def run_stop_in_stall(open_fn: OpenFn, sched: Schedule) -> StopInStall | None:
    """Information only (D3's residue): a stop that lands half-way through a
    stalled callback. How long the stop took, the audio captured by then but
    never delivered, and the callbacks that still ran after the stop call."""
    stall_at = sched.lead + 1
    recorder = Recorder(stall_at=stall_at, stall_s=sched.stop_stall_s)
    stop, _ = open_fn(recorder)
    t_abort = 0
    try:
        patience = sched.wait_s + stall_at * sched.block_ns / SECOND
        if recorder.reached.wait(patience):
            time.sleep(sched.stop_stall_s / 2)
            t_abort = time.perf_counter_ns()
    finally:
        stop()
    t_closed = time.perf_counter_ns()
    if not t_abort or len(recorder.entries) < sched.lead:
        return None
    origin = min(recorder.entries[i - 1] - i * sched.block_ns for i in range(1, sched.lead + 1))
    before = sum(1 for entry in recorder.entries if entry < t_abort)
    undelivered = (t_abort - origin) - before * sched.block_ns
    return StopInStall(t_closed - t_abort, undelivered, len(recorder.entries) - before)


def measure_row(
    label: str,
    latency: float | None,
    open_fn: OpenFn,
    sched: Schedule,
    say: Callable[[str], None],
    *,
    cadence: bool = True,
    rng: random.Random | None = None,
) -> Row:
    """Every trial of one row, each its own open. A refusal of the row's FIRST
    open makes the row ``refused``; a later one leaves that figure missing."""
    rng = rng or random.Random()
    opened = False
    gaps: tuple[int, ...] = ()
    flags: int | None = None
    read_back: float | None = None
    if cadence:
        say(f"{label}: cadence, {sched.cadence_ns // SECOND} s")
        try:
            gaps, flags, read_back = run_cadence(open_fn, sched)
            opened = True
        except OpenRefused:
            return Row(label, latency, refused=True)
    stalls: dict[float, tuple[StallTrial, ...]] = {}
    for stall_s, count in sched.stall_plan:
        say(f"{label}: {count} stalls of {stall_s:g} s")
        trials: list[StallTrial] = []
        for _ in range(count):
            try:
                trials.append(run_stall_trial(open_fn, stall_s, sched))
                opened = True
            except OpenRefused:
                if not opened:
                    return Row(label, latency, refused=True)
        stalls[stall_s] = tuple(trials)
    say(f"{label}: {sched.tail_trials} stops after {sched.tail_run_ns // SECOND} s")
    tails: list[int] = []
    stops: list[int] = []
    firsts: list[int] = []
    for _ in range(sched.tail_trials):
        try:
            figures = run_tail_trial(open_fn, sched, rng)
        except OpenRefused:
            continue
        if figures is not None:
            tails.append(figures[0])
            stops.append(figures[1])
            firsts.append(figures[2])
    try:
        stop_in_stall = run_stop_in_stall(open_fn, sched)
    except OpenRefused:
        stop_in_stall = None
    return Row(
        label,
        latency,
        read_back_s=read_back,
        gaps_ns=gaps,
        cadence_flags=flags,
        stalls=stalls,
        tails_ns=tuple(tails),
        stops_ns=tuple(stops),
        firsts_ns=tuple(firsts),
        stop_in_stall=stop_in_stall,
    )


# --- the interpreter-lock confirmation row -------------------------------------------------


def _gil_enabled() -> bool:
    return bool(getattr(sys, "_is_gil_enabled", lambda: True)())


def _hold_interpreter_lock(seconds: float) -> None:
    """Sleep WITHOUT releasing the interpreter lock: a ``PyDLL`` call keeps it,
    which is what a stalled extension call does to the microphone callback."""
    ctypes.PyDLL("kernel32").Sleep(int(seconds * 1000))


def lock_hold_stops_a_thread(hold: Callable[[float], None], seconds: float) -> bool:
    """The self-check: while ``hold`` runs, a second thread's heartbeat stops
    for most of ``seconds``."""
    stamps: list[int] = []
    done = threading.Event()

    def beat() -> None:
        while not done.is_set():
            stamps.append(time.perf_counter_ns())
            time.sleep(0.002)

    thread = threading.Thread(target=beat, daemon=True)
    thread.start()
    try:
        time.sleep(0.05)
        hold(seconds)
        time.sleep(0.05)
    finally:
        # A raising hold never leaves the heartbeat running.
        done.set()
        thread.join()
    longest = max((b - a for a, b in zip(stamps, stamps[1:], strict=False)), default=0)
    return longest >= 0.8 * seconds * SECOND


def run_lock_hold(open_fn: OpenFn, sched: Schedule, hold: Callable[[float], None]) -> str:
    """One row on the default buffer: after ``lead`` callbacks the MAIN thread
    holds the interpreter lock for ``lock_hold_s``; a flag is expected."""
    if not sys.platform.startswith("win"):
        return "skipped (not Windows)"
    if not _gil_enabled():
        return "skipped (this interpreter has no interpreter lock)"
    try:
        if not lock_hold_stops_a_thread(hold, sched.lock_hold_s):
            return "skipped (the self-check failed: the hold did not stop a second thread)"
        recorder = Recorder(stall_at=sched.lead)
        stop, _ = open_fn(recorder)
        held = False
        try:
            if recorder.reached.wait(sched.wait_s + sched.lead * sched.block_ns / SECOND):
                hold(sched.lock_hold_s)
                held = True
                time.sleep(sched.observe_ns / SECOND)
        finally:
            stop()
    except OpenRefused:
        return "not measured (the stream would not open)"
    except OSError:
        return "skipped (the lock-holding call is not available)"
    except Exception as exc:  # noqa: BLE001 - reported by TYPE; the table above still prints
        return f"not measured ({type(exc).__name__})"
    if not held:
        return "not measured (no callbacks arrived)"
    flagged = any(number >= sched.lead for number in recorder.flagged)
    return f"{sched.lock_hold_s:g} s hold: flag {'yes' if flagged else 'no'} (expected yes)"


# --- the paste block (numbers, an id, a host word; never a device name) --------------------


@dataclass(frozen=True)
class Identity:
    sounddevice_version: str
    portaudio_version: str
    module_checkout: str  # "this checkout" or "another checkout" (``checkout_word``)
    device_id: int
    host: str
    mode: str
    default_low_s: float | None = None
    default_high_s: float | None = None


def checkout_word(module_file: object) -> str:
    """Which code ran, as a fixed word (a path could carry a Windows account
    name): ``this checkout`` when ``module_file`` resolves inside this
    script's own repository's ``desktop/src``, otherwise ``another checkout``."""
    own = os.path.normcase(
        os.path.realpath(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, "desktop", "src")
        )
    )
    if not isinstance(module_file, str) or not os.path.isabs(module_file):
        return "another checkout"
    try:
        found = os.path.normcase(os.path.realpath(module_file))
        inside = os.path.commonpath([own, found]) == own
    except (OSError, ValueError):  # another drive, or an unresolvable path
        inside = False
    return "this checkout" if inside else "another checkout"


def _ms(value_ns: float | None) -> str:
    return "-" if value_ns is None else f"{value_ns / MS:.0f}"


def _median(values: Sequence[int]) -> float | None:
    return statistics.median(values) if values else None


def _verdict(value: bool | None) -> str:
    return "-" if value is None else ("pass" if value else "fail")


def _seconds_ms(value_s: float | None) -> str:
    return "-" if value_s is None else f"{value_s * 1000:.0f}"


def _cadence_lines(rows: Sequence[Row]) -> list[str]:
    lines = [
        "",
        "| row | read-back ms | gaps | gap median ms | gap p99 ms | gap max ms | flags |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        if row.refused:
            lines.append(f"| {row.label} | refused | | | | | |")
            continue
        flags = "-" if row.cadence_flags is None else str(row.cadence_flags)
        lines.append(
            f"| {row.label} | {_seconds_ms(row.read_back_s)} | {len(row.gaps_ns)} "
            f"| {_ms(_median(row.gaps_ns))} | {_ms(nearest_rank(row.gaps_ns, 0.99))} "
            f"| {_ms(max(row.gaps_ns, default=None))} | {flags} |"
        )
    return lines


def _stall_lines(rows: Sequence[Row], block_ns: int, *, show_refused: bool = False) -> list[str]:
    lines = [
        "",
        "| row | stall s | trials | flagged | passed | invalid | lost blocks (max) "
        "| flag on callback (0 = the stalled one) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        if show_refused and row.refused:
            # --product has no cadence table: a refused row shows here.
            lines.append(f"| {row.label} | refused | - | - | - | - | - | - |")
            continue
        for stall_s, trials in row.stalls.items():
            valid = [t.residual_ns for t in trials if t.residual_ns is not None]
            lost = str(max(lost_blocks(r, block_ns) for r in valid)) if valid else "-"
            offsets = sorted({t.flag_offset for t in trials if t.flag_offset is not None})
            lines.append(
                f"| {row.label} | {stall_s:g} | {len(trials)} "
                f"| {sum(t.flagged for t in trials)} "
                f"| {sum(trial_passes(t, block_ns) for t in trials)} "
                f"| {len(trials) - len(valid)} | {lost} "
                f"| {', '.join(str(o) for o in offsets) or '-'} |"
            )
    return lines


def _tail_lines(rows: Sequence[Row]) -> list[str]:
    lines = [
        "",
        "| row | stops | tail median ms | tail max ms | stop median ms | first block median ms "
        "| stop inside a stall: stop ms / undelivered ms / callbacks after |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        if row.refused:
            continue
        inside = row.stop_in_stall
        shown = (
            "-"
            if inside is None
            else f"{_ms(inside.stop_ns)} / {_ms(inside.undelivered_ns)} / {inside.late_callbacks}"
        )
        lines.append(
            f"| {row.label} | {len(row.tails_ns)} | {_ms(_median(row.tails_ns))} "
            f"| {_ms(max(row.tails_ns, default=None))} | {_ms(_median(row.stops_ns))} "
            f"| {_ms(_median(row.firsts_ns))} | {shown} |"
        )
    return lines


def paste_block(
    identity: Identity,
    rows: Sequence[Row],
    result: RuleResult,
    *,
    lock_hold: str | None = None,
    block_ns: int = BLOCK_NS,
) -> str:
    """The Markdown block the practitioner pastes into the plan."""
    product = identity.mode == "product"
    lines = [
        "### Capture-stall measurement (`scripts/measure-capture-stall.py`)",
        "",
        f"- sounddevice {identity.sounddevice_version}; {identity.portaudio_version}",
        f"- audio_capture: {identity.module_checkout}",
        f"- device id {identity.device_id}; host {identity.host}; mode {identity.mode}",
        "- default input latency, low / high, ms: "
        f"{_seconds_ms(identity.default_low_s)} / {_seconds_ms(identity.default_high_s)}",
    ]
    if identity.host != "mme":
        lines.append("- not scored: this device's host API is not MME")
    if rows:
        if not product:
            lines += _cadence_lines(rows)
        lines += _stall_lines(rows, block_ns, show_refused=product)
        lines += _tail_lines(rows)
        shown = PRODUCT_BARS if product else BARS
        lines += [
            "",
            "| candidate | " + " | ".join(f"({bar})" for bar in shown) + " |",
            "|---" * (len(shown) + 1) + "|",
        ]
        for label, bars in result.bars.items():
            cells = " | ".join(_verdict(bars[bar]) for bar in shown)
            lines.append(f"| {label} | {cells} |")
    if lock_hold is not None:
        lines += ["", f"- interpreter-lock row (default buffer): {lock_hold}"]
    lines.append("")
    if product:
        passed = bool(result.bars) and all(
            all(bars[bar] for bar in PRODUCT_BARS) for bars in result.bars.values()
        )
        lines.append(f"product: {'pass' if passed and identity.host == 'mme' else 'fail'}")
    else:
        lines.append(f"premise: {'met' if result.premise_met else 'not met'}")
        chosen = "none" if result.chosen is None else f"{result.chosen:.1f}"
        lines.append(f"chosen: {chosen}")
    return "\n".join(lines)


# --- seams (tests replace them) and main ---------------------------------------------------


class ExclusionLike(Protocol):
    @property
    def state(self) -> str: ...


def _windows_layer() -> Any:
    """The real Windows layer for the crash-report check (the conftest makes
    it raise in tests)."""
    from scribe_desktop import exclusions

    return exclusions.Win32WindowsLayer()


def _acquire_exclusion() -> ExclusionLike:
    """The app's single-instance exclusion (``app`` imports Qt; importing it
    runs no start-up)."""
    from scribe_desktop import app

    return app.acquire_instance_exclusion()


def _release_exclusion(exclusion: ExclusionLike) -> None:
    from scribe_desktop import app

    if isinstance(exclusion, app.InstanceExclusion):
        app.release_instance_exclusion(exclusion)


def _import_sounddevice() -> Any:
    import sounddevice

    return sounddevice


def _import_audio_capture() -> Any:
    from scribe_desktop import audio_capture

    return audio_capture


def _refuse(text: str) -> int:
    print(f"[refused] {text}")
    return 2


def _say(text: str) -> None:
    print(f"[running] {text}", flush=True)


def _host_of(sd: Any, info: Mapping[str, Any]) -> str:
    try:
        return host_word(str(sd.query_hostapis(int(info["hostapi"]))["name"]))
    except Exception:  # noqa: BLE001 - anything unresolved is "other"
        return "other"


def _list_devices(sd: Any) -> int:
    """On screen only: the names can carry a person's name (C4)."""
    # A redirected stdout may not encode every name: replace, never abort.
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(errors="replace")
    print("Input devices (on screen only - do NOT paste this list anywhere):")
    try:
        default = int(sd.default.device[0])
    except Exception:  # noqa: BLE001 - no default is shown as none
        default = -1
    for index, info in enumerate(sd.query_devices()):
        if int(info.get("max_input_channels", 0)) < 1:
            continue
        mark = " (default)" if index == default else ""
        print(f"  {index:>3}  {_host_of(sd, info):<11}  {info.get('name', '')}{mark}")
    print("Only an 'mme' entry is scored. Give its id as --device <id>.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure how long a stalled microphone callback the input stream survives. "
        "Keeps no audio; prints numbers only."
    )
    parser.add_argument("--list", action="store_true", help="list input devices (on screen only)")
    parser.add_argument("--device", type=int, default=None, help="the input device id")
    parser.add_argument(
        "--product",
        action="store_true",
        help="the stall and stop rows through the app's own SoundDeviceBackend.open_stream",
    )
    return parser


def _measure(args: argparse.Namespace, capture: Any, sched: Schedule) -> int:
    sd = _import_sounddevice()
    try:
        device = int(sd.default.device[0]) if args.device is None else int(args.device)
        info = sd.query_devices(device)
        usable = device >= 0 and int(info.get("max_input_channels", 0)) >= capture.CHANNELS
    except Exception:  # noqa: BLE001 - PortAudio's text is not echoed
        usable = False
    if not usable:
        return _refuse("that is not an input device id (see --list)")
    host = _host_of(sd, info)
    try:
        portaudio = str(sd.get_portaudio_version()[1])
    except Exception:  # noqa: BLE001
        portaudio = "PortAudio (version unknown)"

    def latency_of(key: str) -> float | None:
        try:
            return float(info[key])
        except (KeyError, TypeError, ValueError):
            return None

    identity = Identity(
        sounddevice_version=str(getattr(sd, "__version__", "unknown")),
        portaudio_version=portaudio,
        module_checkout=checkout_word(getattr(capture, "__file__", None)),
        device_id=device,
        host=host,
        mode="product" if args.product else "raw",
        default_low_s=latency_of("default_low_input_latency"),
        default_high_s=latency_of("default_high_input_latency"),
    )
    rows: list[Row] = []
    lock_hold: str | None = None
    if host == "mme":
        print(
            "Nothing is recorded: each block is counted and dropped. Leave the computer alone "
            "until the paste block appears.",
            flush=True,
        )
        if args.product:
            buffer = float(capture.INPUT_LATENCY_SECONDS)
            plan: list[tuple[str, float | None, OpenFn]] = [
                (
                    "product default",
                    None,
                    product_opener(capture, capture.SoundDeviceBackend(input_latency=None), device),
                ),
                (
                    f"product {buffer:g} s",
                    buffer,
                    product_opener(capture, capture.SoundDeviceBackend(), device),
                ),
            ]
        else:
            plan = [("default", None, raw_opener(sd, capture, device, None))]
            plan += [
                (f"{latency:g} s", latency, raw_opener(sd, capture, device, latency))
                for latency in sched.candidates
            ]
        for label, latency, open_fn in plan:
            rows.append(measure_row(label, latency, open_fn, sched, _say, cadence=not args.product))
        if not args.product:
            _say("default: the interpreter-lock row")
            lock_hold = run_lock_hold(
                raw_opener(sd, capture, device, None), sched, _hold_interpreter_lock
            )
    result = evaluate(host, rows)
    print()
    print("----- paste from the next line to the end -----")
    print(paste_block(identity, rows, result, lock_hold=lock_hold, block_ns=sched.block_ns))
    return 0


def main(argv: Sequence[str] | None = None, schedule: Schedule = DEFAULT_SCHEDULE) -> int:
    args = _parser().parse_args(argv)
    if args.list:
        return _list_devices(_import_sounddevice())
    capture = _import_audio_capture()
    if capture.BLOCK_FRAMES * SECOND != BLOCK_NS * capture.SAMPLE_RATE:
        return _refuse("the imported audio_capture's block is not 100 ms: the rule does not apply")
    if args.product and not hasattr(capture, "INPUT_LATENCY_SECONDS"):
        return _refuse(
            "--product needs the built app: the imported audio_capture has no "
            "INPUT_LATENCY_SECONDS (set PYTHONPATH to the checkout's desktop\\src)"
        )
    from scribe_desktop.exclusions import check_tool_wer, tool_wer_refusal_line

    crash_reports = check_tool_wer(_windows_layer, sys.executable)
    if crash_reports is not None:
        return _refuse(tool_wer_refusal_line(crash_reports, sys.executable))
    exclusion = _acquire_exclusion()  # module globals, looked up per call: tests replace them
    try:
        if exclusion.state != "acquired":
            return _refuse(
                "close Clinic Scribe first (either build): the measurement holds the app's "
                f"single-instance lock for its run ({exclusion.state})"
            )
        try:
            return _measure(args, capture, schedule)
        except KeyboardInterrupt:
            return _refuse("interrupted")
        except Exception as exc:  # noqa: BLE001 - reported by TYPE, never its text
            return _refuse(f"stopped: {type(exc).__name__}")
    finally:
        _release_exclusion(exclusion)


if __name__ == "__main__":
    sys.exit(main())
