"""Capture-overflow plan Task 0.1: ``scripts/measure-capture-stall.py``, the
practitioner-run measurement of how long a stalled microphone callback the
input stream survives (D5's frozen rule and sampling protocol; C3, C4).

Hardware-free: the script is loaded through importlib and driven with a fake
``sounddevice`` (a thread that calls the callback on a short period) and a
fake capture module. No microphone, no PortAudio, no audio: the fake blocks
are empty. The frozen rule's figures are tested on hand-built tables and
entry-time lists; the end-to-end runs assert the shape of the paste block,
never a timing.
"""

from __future__ import annotations

import importlib.util
import io
import re
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from scribe_desktop import audio_capture, guard_eval
from speaker_fakes import VENV_PYTHON, WerLayer, excluded_wer_layer

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "measure-capture-stall.py"
MS = 1_000_000
DEVICE_NAME = "Jane Citizen's Headset"


@pytest.fixture(scope="module")
def tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("measure_capture_stall", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves a string annotation through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# --- fakes --------------------------------------------------------------------------------


class _Status:
    def __init__(self, flagged: bool) -> None:
        self.input_overflow = flagged

    def __bool__(self) -> bool:
        return self.input_overflow


class _Ticker:
    """A thread that calls ``tick`` every ``period_s`` until stopped; a tick
    that ran long is followed by one flagged tick (as a full device buffer)."""

    def __init__(self, period_s: float, tick: Callable[[bool], None]) -> None:
        self._period_s = period_s
        self._tick = tick
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        late = False
        while not self._stop.wait(self._period_s):
            began = time.perf_counter()
            self._tick(late)
            late = time.perf_counter() - began > 3 * self._period_s

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join()


class _FakeStream:
    latency = 0.1

    def __init__(self, period_s: float, callback: Callable[..., None]) -> None:
        self._ticker = _Ticker(period_s, lambda late: callback(b"", 160, None, _Status(late)))
        self.closed = False

    def start(self) -> None:
        self._ticker.start()

    def abort(self, ignore_errors: bool = True) -> None:
        self._ticker.stop()

    def close(self, ignore_errors: bool = True) -> None:
        self.closed = True


class _FakeSounddevice:
    """The parts of ``sounddevice`` the script reads. Device 0 has no input,
    device 1 is the default input, device 2 is the same microphone on WASAPI."""

    __version__ = "0.5.5"

    class PortAudioError(Exception):
        pass

    def __init__(self, *, host: str = "MME", refuse: tuple[float, ...] = ()) -> None:
        self.default = SimpleNamespace(device=(1, 3))
        self.refuse = refuse
        self.opened: list[dict[str, Any]] = []
        self.streams: list[_FakeStream] = []
        self._hosts = [{"name": host}, {"name": "Windows WASAPI"}]
        microphone = {
            "name": DEVICE_NAME,
            "max_input_channels": 2,
            "default_low_input_latency": 0.09,
            "default_high_input_latency": 0.18,
        }
        self._devices: list[dict[str, Any]] = [
            {"name": "Speakers", "max_input_channels": 0, "hostapi": 0},
            {**microphone, "hostapi": 0},
            {**microphone, "hostapi": 1},
        ]

    def query_devices(self, device: int | None = None) -> Any:
        if device is None:
            return list(self._devices)
        if device < 0:
            raise self.PortAudioError(f"no such device ({DEVICE_NAME})")
        return self._devices[device]

    def query_hostapis(self, index: int) -> dict[str, Any]:
        return self._hosts[index]

    def get_portaudio_version(self) -> tuple[int, str]:
        return (1246976, "PortAudio V19.7.0-devel, revision unknown")

    def RawInputStream(self, **kwargs: Any) -> _FakeStream:  # noqa: N802 - the library's name
        self.opened.append(kwargs)
        if kwargs.get("latency") in self.refuse:
            raise self.PortAudioError(f"{DEVICE_NAME}: invalid latency")
        stream = _FakeStream(0.01, kwargs["callback"])
        self.streams.append(stream)
        return stream


class _Seams:
    """The script's seams replaced: crash reports excluded, the exclusion
    acquired, and NO sounddevice until a test gives one."""

    def __init__(self, tool: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        self.acquired = 0
        self.released = 0
        self.state = "acquired"
        self.sounddevice: _FakeSounddevice | None = None
        self.imports = 0
        monkeypatch.setattr(sys, "executable", VENV_PYTHON)
        monkeypatch.setattr(tool, "_windows_layer", excluded_wer_layer)
        monkeypatch.setattr(tool, "_acquire_exclusion", self._acquire)
        monkeypatch.setattr(tool, "_release_exclusion", self._release)
        monkeypatch.setattr(tool, "_import_sounddevice", self._import)

    def _acquire(self) -> SimpleNamespace:
        self.acquired += 1
        return SimpleNamespace(state=self.state)

    def _release(self, exclusion: object) -> None:
        self.released += 1

    def _import(self) -> _FakeSounddevice:
        self.imports += 1
        assert self.sounddevice is not None, "sounddevice imported where no stream may open"
        return self.sounddevice


@pytest.fixture
def seams(tool: ModuleType, monkeypatch: pytest.MonkeyPatch) -> _Seams:
    return _Seams(tool, monkeypatch)


def _quick(tool: ModuleType) -> Any:
    """A schedule for the fake stream's 10 ms period: the same protocol, short."""
    return tool.Schedule(
        block_ns=10 * MS,
        observe_ns=60 * MS,
        tail_window_ns=50 * MS,
        cadence_ns=100 * MS,
        tail_run_ns=50 * MS,
        tail_jitter_ns=5 * MS,
        tail_trials=2,
        stall_plan=((0.03, 2),),
        candidates=(1.0, 2.5),
        stop_stall_s=0.04,
        lock_hold_s=0.03,
        wait_s=5.0,
    )


def _block_of(out: str) -> str:
    marker = "----- paste from the next line to the end -----\n"
    assert out.count(marker) == 1
    return out.split(marker)[1]


# --- the frozen rule ----------------------------------------------------------------------


def _trials(tool: ModuleType, count: int, *, flagged: int = 0, residual: int | None = 0) -> Any:
    return tuple(
        tool.StallTrial(flagged=index < flagged, residual_ns=residual) for index in range(count)
    )


def _default_row(tool: ModuleType, *, premise_flags: int = 5) -> Any:
    return tool.Row(
        "default",
        None,
        gaps_ns=(100 * MS,) * 200,
        cadence_flags=0,
        stalls={0.3: _trials(tool, 5, flagged=premise_flags)},
        tails_ns=(60 * MS,) * 20,
        stops_ns=(100 * MS,) * 20,
        firsts_ns=(150 * MS,) * 20,
    )


def _candidate(tool: ModuleType, latency: float, **changes: Any) -> Any:
    row = tool.Row(
        f"{latency:g} s",
        latency,
        gaps_ns=(100 * MS,) * 200,
        cadence_flags=0,
        stalls={2.0: _trials(tool, 10)},
        tails_ns=(60 * MS,) * 20,
        stops_ns=(100 * MS,) * 20,
        firsts_ns=(150 * MS,) * 20,
    )
    return replace(row, **changes)


def _one(tool: ModuleType, row: Any, default: Any | None = None) -> dict[str, bool | None]:
    result = tool.evaluate("mme", [default or _default_row(tool), row])
    return dict(result.bars[row.label])


class TestTheRule:
    def _table(self, tool: ModuleType) -> list[Any]:
        return [
            _default_row(tool),
            _candidate(tool, 1.0, stalls={2.0: _trials(tool, 10, flagged=10)}),
            _candidate(tool, 2.0, stalls={2.0: _trials(tool, 10, flagged=1)}),
            _candidate(tool, 2.5),
            _candidate(tool, 3.0),
        ]

    def test_the_smallest_candidate_that_meets_every_bar_is_chosen(self, tool: ModuleType) -> None:
        result = tool.evaluate("mme", self._table(tool))
        assert result.premise_met is True
        assert result.chosen == 2.5
        assert result.bars["1 s"]["a"] is False and result.bars["2 s"]["a"] is False
        assert all(result.bars["2.5 s"].values()) and all(result.bars["3 s"].values())

    def test_the_order_of_the_rows_does_not_matter(self, tool: ModuleType) -> None:
        assert tool.evaluate("mme", self._table(tool)[::-1]).chosen == 2.5

    def test_no_candidate_passing_chooses_nothing(self, tool: ModuleType) -> None:
        failing = {2.0: _trials(tool, 10, flagged=3)}
        rows = [_default_row(tool)] + [
            _candidate(tool, latency, stalls=failing) for latency in tool.CANDIDATES
        ]
        result = tool.evaluate("mme", rows)
        assert result.premise_met is True and result.chosen is None

    @pytest.mark.parametrize(("flags", "met"), [(5, True), (4, True), (3, False), (0, False)])
    def test_the_premise_is_four_flags_of_five_on_the_default(
        self, tool: ModuleType, flags: int, met: bool
    ) -> None:
        rows = [_default_row(tool, premise_flags=flags), _candidate(tool, 2.5)]
        result = tool.evaluate("mme", rows)
        assert result.premise_met is met
        # Without the premise nothing is chosen, whatever the candidates did.
        assert result.chosen == (2.5 if met else None)

    def test_a_premise_needs_its_five_trials(self, tool: ModuleType) -> None:
        short = replace(_default_row(tool), stalls={0.3: _trials(tool, 4, flagged=4)})
        assert tool.evaluate("mme", [short, _candidate(tool, 2.5)]).premise_met is False
        refused = tool.Row("default", None, refused=True)
        assert tool.evaluate("mme", [refused, _candidate(tool, 2.5)]).premise_met is False

    @pytest.mark.parametrize("host", ["directsound", "wasapi", "wdmks", "other"])
    def test_a_device_that_is_not_mme_is_not_scored(self, tool: ModuleType, host: str) -> None:
        result = tool.evaluate(host, self._table(tool))
        assert result.chosen is None

    def test_a_candidate_that_will_not_open_fails_a_and_the_rest_is_not_evaluated(
        self, tool: ModuleType
    ) -> None:
        refused = tool.Row("1 s", 1.0, refused=True)
        result = tool.evaluate("mme", [_default_row(tool), refused, _candidate(tool, 2.5)])
        assert dict(result.bars["1 s"]) == {"a": False, "b": None, "c": None, "d": None, "e": None}
        assert result.chosen == 2.5

    def test_every_table_has_an_answer(self, tool: ModuleType) -> None:
        empty = tool.evaluate("mme", [])
        assert (empty.premise_met, empty.chosen, dict(empty.bars)) == (False, None, {})
        # No default row: every comparison against it is a missing figure.
        alone = tool.evaluate("mme", [_candidate(tool, 2.5)])
        assert alone.chosen is None
        missing = {"a": True, "b": True, "c": False, "d": False, "e": False}
        assert dict(alone.bars["2.5 s"]) == missing
        bare = tool.evaluate("mme", [tool.Row("default", None), tool.Row("2.5 s", 2.5)])
        assert bare.chosen is None and not any(bare.bars["2.5 s"].values())

    @pytest.mark.parametrize(
        ("trials", "passes"),
        [
            ({"count": 10}, True),
            ({"count": 9}, False),  # ten of ten: a missing trial fails
            ({"count": 11}, False),
            ({"count": 10, "flagged": 1}, False),
            ({"count": 10, "residual": None}, False),  # an invalid trial fails
            ({"count": 10, "residual": 50 * MS - 1}, True),
            ({"count": 10, "residual": 50 * MS}, False),  # the half-block tie fails
            ({"count": 10, "residual": -40 * MS}, True),
        ],
    )
    def test_bar_a(self, tool: ModuleType, trials: dict[str, Any], passes: bool) -> None:
        rest = {key: value for key, value in trials.items() if key != "count"}
        row = _candidate(tool, 2.5, stalls={2.0: _trials(tool, trials["count"], **rest)})
        assert _one(tool, row)["a"] is passes

    @pytest.mark.parametrize(
        ("gaps", "flags", "passes"),
        [
            ((80 * MS,) * 200, 0, True),  # 80 to 120 ms inclusive
            ((120 * MS,) * 200, 0, True),
            ((80 * MS - 1,) * 200, 0, False),
            ((120 * MS + 1,) * 200, 0, False),
            ((100 * MS,) * 197 + (250 * MS,) * 3, 0, True),  # p99 (rank 198) at most 250 ms
            ((100 * MS,) * 197 + (250 * MS + 1,) * 3, 0, False),
            ((100 * MS,) * 200, 1, False),  # no flag
            ((100 * MS,) * 200, None, False),
            ((), 0, False),  # a missing figure fails its bar
        ],
    )
    def test_bar_b(
        self, tool: ModuleType, gaps: tuple[int, ...], flags: int | None, passes: bool
    ) -> None:
        row = _candidate(tool, 2.5, gaps_ns=gaps, cadence_flags=flags)
        assert _one(tool, row)["b"] is passes

    @pytest.mark.parametrize(
        ("tails", "passes"),
        [
            ((110 * MS,) * 19 + (200 * MS,), True),  # median +50 ms and max 200 ms, inclusive
            ((110 * MS + 1,) * 20, False),
            ((110 * MS,) * 19 + (200 * MS + 1,), False),
            ((60 * MS,) * 19, False),  # twenty trials: a missing one fails
        ],
    )
    def test_bar_c(self, tool: ModuleType, tails: tuple[int, ...], passes: bool) -> None:
        assert _one(tool, _candidate(tool, 2.5, tails_ns=tails))["c"] is passes

    def test_bar_c_needs_the_default_s_twenty_trials(self, tool: ModuleType) -> None:
        short_default = replace(_default_row(tool), tails_ns=(60 * MS,) * 19)
        assert _one(tool, _candidate(tool, 2.5), short_default)["c"] is False

    @pytest.mark.parametrize(
        ("bar", "changes"),
        [
            ("b", {"gaps_ns": (120 * MS + 1,) * 200}),
            ("c", {"tails_ns": (110 * MS + 1,) * 20}),
            ("d", {"stops_ns": (350 * MS + 1,) * 20}),
            ("e", {"firsts_ns": (400 * MS + 1,) * 20}),
        ],
    )
    def test_a_candidate_failing_one_bar_is_passed_over(
        self, tool: ModuleType, bar: str, changes: dict[str, Any]
    ) -> None:
        """D5: the smallest candidate that meets ALL of (a)-(e)."""
        rows = [_default_row(tool), _candidate(tool, 2.5, **changes), _candidate(tool, 3.0)]
        result = tool.evaluate("mme", rows)
        assert {key for key, value in result.bars["2.5 s"].items() if value is not True} == {bar}
        assert all(result.bars["3 s"].values())
        assert result.chosen == 3.0

    @pytest.mark.parametrize(
        ("bar", "name", "base"), [("d", "stops_ns", 100), ("e", "firsts_ns", 150)]
    )
    def test_bars_d_and_e_allow_the_default_plus_250_ms(
        self, tool: ModuleType, bar: str, name: str, base: int
    ) -> None:
        at = (base + 250) * MS
        assert _one(tool, _candidate(tool, 2.5, **{name: (at,) * 20}))[bar] is True
        assert _one(tool, _candidate(tool, 2.5, **{name: (at + 1,) * 20}))[bar] is False
        assert _one(tool, _candidate(tool, 2.5, **{name: (at,) * 19}))[bar] is False
        short_default = replace(_default_row(tool), **{name: (base * MS,) * 19})
        assert _one(tool, _candidate(tool, 2.5), short_default)[bar] is False

    def test_the_schedule_is_the_frozen_protocol(self, tool: ModuleType) -> None:
        """D5: a change of any of these is a new dated decision, never an edit."""
        sched = tool.DEFAULT_SCHEDULE
        assert sched.candidates == (1.0, 2.0, 2.5, 3.0)
        assert sched.stall_plan == ((0.3, 5), (1.0, 5), (2.0, 10), (3.0, 5))
        assert (sched.block_ns, sched.lead) == (100 * MS, 10)
        assert (sched.observe_ns, sched.tail_window_ns) == (1000 * MS, 500 * MS)
        assert (sched.cadence_ns, sched.tail_run_ns) == (20_000 * MS, 5000 * MS)
        assert (sched.tail_jitter_ns, sched.tail_trials) == (100 * MS, 20)
        assert audio_capture.BLOCK_FRAMES * 1000 == 100 * audio_capture.SAMPLE_RATE


class TestTheStatistics:
    def test_the_borderline_sample_passes_bar_b_by_nearest_rank(self, tool: ModuleType) -> None:
        """Peer round 3: 197 gaps at 97.2 ms, then 240, 300 and 310 ms. Rank
        ceil(0.99 x 200) = 198 is the 240 ms gap (an interpolating percentile
        would read above 250 ms)."""
        gaps = (97_200_000,) * 197 + (240 * MS, 300 * MS, 310 * MS)
        assert tool.nearest_rank(gaps, 0.99) == 240 * MS
        assert _one(tool, _candidate(tool, 2.5, gaps_ns=gaps))["b"] is True

    @pytest.mark.parametrize("count", [1, 2, 99, 100, 101, 199, 200, 201])
    def test_the_percentile_is_guard_eval_s(self, tool: ModuleType, count: int) -> None:
        values = [((index * 37) % count) * MS for index in range(count)]
        for share in (0.5, 0.99, 1.0):
            assert tool.nearest_rank(values, share) == guard_eval._percentile(values, share)
        assert tool.nearest_rank([], 0.99) is None

    def test_the_tail_is_the_clock_s_audio_less_the_delivered_blocks(
        self, tool: ModuleType
    ) -> None:
        # 5.04 s after the first callback, fifty blocks delivered: 140 ms.
        assert tool.tail_ns(7 * MS, 5047 * MS, 50) == 140 * MS
        assert tool.tail_ns(0, 5000 * MS, 51) == 0

    def test_the_host_word(self, tool: ModuleType) -> None:
        assert tool.host_word("MME") == "mme"
        assert tool.host_word("Windows DirectSound") == "directsound"
        assert tool.host_word("Windows WASAPI") == "wasapi"
        assert tool.host_word("Windows WDM-KS") == "wdmks"
        assert tool.host_word(DEVICE_NAME) == "other"


# --- the lost-block figure ----------------------------------------------------------------

ABORT = 4100 * MS  # the stall (2.0 s from 1100 ms) returns at 3100 ms; observe 1.0 s


def _stall_entries(
    *, lead_late: tuple[int, ...] = (0,) * 10, lost: int = 0, tail_late: int = 0
) -> list[int]:
    """Entry times, ns, of a 2.0 s stall trial on a buffer that holds it:
    ten lead callbacks (each ``lead_late`` ms after its block), the stalled
    eleventh, the backlog delivered as a burst when it returns (``lost``
    blocks of it never delivered), then one callback per block, each
    ``tail_late`` ms after its block."""
    entries = [(number * 100 + late) * MS for number, late in enumerate(lead_late, start=1)]
    entries.append(1100 * MS)
    entries += [3100 * MS + index * 10_000 for index in range(20 - lost)]
    entries += [(block * 100 + tail_late) * MS for block in range(32, 42)]
    return entries


def _verdict(tool: ModuleType, entries: list[int]) -> tuple[bool, int | None]:
    residual = tool.stall_residual_ns(entries, ABORT)
    trial = tool.StallTrial(flagged=False, residual_ns=residual)
    return tool.trial_passes(trial), None if residual is None else tool.lost_blocks(residual)


class TestLostBlocks:
    def test_a_healthy_trial_with_jitter_loses_nothing(self, tool: ModuleType) -> None:
        entries = _stall_entries(lead_late=(30, 10, 25, 5, 40, 15, 20, 10, 35, 10), tail_late=8)
        assert tool.stall_residual_ns(entries, ABORT) == 3 * MS
        assert _verdict(tool, entries) == (True, 0)

    def test_a_late_first_callback_does_not_hide_two_lost_blocks(self, tool: ModuleType) -> None:
        """Peer round 4's counterexample: the first callback 200 ms late (its
        backlog then delivered at once), two blocks lost with no flag. A figure
        taken between the first and last entries reads zero; this one reads 2."""
        entries = _stall_entries(lead_late=(200, 100, 0, 0, 0, 0, 0, 0, 0, 0), lost=2)
        assert tool.stall_residual_ns(entries, ABORT) == 200 * MS
        assert _verdict(tool, entries) == (False, 2)

    def test_one_lost_block_fails(self, tool: ModuleType) -> None:
        assert _verdict(tool, _stall_entries(lost=1)) == (False, 1)

    def test_a_tail_set_of_two_callbacks_is_invalid_and_fails(self, tool: ModuleType) -> None:
        entries = _stall_entries()[:11] + [3700 * MS, 3900 * MS]
        assert _verdict(tool, entries) == (False, None)
        # ... and so is a trial whose lead never completed.
        assert tool.stall_residual_ns(_stall_entries()[:9], ABORT) is None

    def test_the_tail_set_is_the_last_half_second_before_the_abort_call(
        self, tool: ModuleType
    ) -> None:
        # Blocks 36 to 40 (3600 to 4000 ms); the one entered AT the abort call is not in it.
        entries = _stall_entries()
        assert entries[-1] == ABORT
        assert tool.stall_residual_ns(entries, ABORT) == 0
        # ... and one entered a nanosecond before the call is (its phase reads -1 ns).
        assert tool.stall_residual_ns(entries[:-1] + [ABORT - 1], ABORT) == -1
        # A callback before the window never counts, however early its phase.
        early = [entry - 90 * MS if entry == 3500 * MS else entry for entry in entries]
        assert early != entries and tool.stall_residual_ns(early, ABORT) == 0

    def test_the_half_block_ties_fail(self, tool: ModuleType) -> None:
        """Peer round 5: exactly half a block is indeterminate, so it fails."""
        late_lead_one_lost = _stall_entries(lead_late=(50,) * 10, lost=1)
        assert tool.stall_residual_ns(late_lead_one_lost, ABORT) == 50 * MS
        assert _verdict(tool, late_lead_one_lost) == (False, 1)
        healthy_late_tail = _stall_entries(tail_late=50)
        assert tool.stall_residual_ns(healthy_late_tail, ABORT) == 50 * MS
        assert _verdict(tool, healthy_late_tail) == (False, 1)

    def test_just_inside_the_validity_bound_the_verdicts_are_right(self, tool: ModuleType) -> None:
        assert _verdict(tool, _stall_entries(lead_late=(49,) * 10, lost=1)) == (False, 1)
        assert _verdict(tool, _stall_entries(tail_late=49)) == (True, 0)
        # A lead that ran late with nothing lost reads below zero, shown as 0.
        assert _verdict(tool, _stall_entries(lead_late=(49,) * 10)) == (True, 0)


# --- the protocol as executed (a scripted opener; no timing is scored) --------------------


class _Numbered:
    """A thread that calls ``tick(number)`` every ``period_s``, numbering the
    calls from 1, until stopped."""

    def __init__(self, period_s: float, tick: Callable[[int], None]) -> None:
        self._period_s = period_s
        self._tick = tick
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def _run(self) -> None:
        number = 0
        while not self._stop.wait(self._period_s):
            number += 1
            self._tick(number)

    def stop(self) -> None:
        self._stop.set()
        if self.thread.is_alive():
            self.thread.join()


class _ScriptedOpener:
    """The script's ``OpenFn`` seam: its own thread drives the recorder's
    callbacks (a block every 10 ms, then a flag on each callback number in
    ``flag_on``, as the raw callback does); its Nth call, for each N in
    ``refuse_on``, raises the script's ``OpenRefused``."""

    def __init__(
        self, tool: ModuleType, *, flag_on: tuple[int, ...] = (), refuse_on: tuple[int, ...] = ()
    ) -> None:
        self._tool = tool
        self._flag_on = flag_on
        self._refuse_on = refuse_on
        self.calls = 0
        self.recorders: list[Any] = []
        self.threads: list[threading.Thread] = []
        self.stopped_ns: list[int] = []

    def __call__(self, recorder: Any) -> tuple[Callable[[], None], float | None]:
        self.calls += 1
        if self.calls in self._refuse_on:
            raise self._tool.OpenRefused

        def tick(number: int) -> None:
            recorder.block(160)
            if number in self._flag_on:
                recorder.flag()

        ticker = _Numbered(0.01, tick)
        self.recorders.append(recorder)
        self.threads.append(ticker.thread)
        ticker.start()

        def stop() -> None:
            self.stopped_ns.append(time.perf_counter_ns())
            ticker.stop()

        return stop, None


class _ScriptedStream:
    latency = 0.1

    def __init__(self, callback: Callable[..., None], flag_on: tuple[int, ...]) -> None:
        self._ticker = _Numbered(
            0.01, lambda number: callback(b"", 160, None, _Status(number in flag_on))
        )

    def start(self) -> None:
        self._ticker.start()

    def abort(self) -> None:
        self._ticker.stop()

    def close(self, ignore_errors: bool = True) -> None:
        pass


class _ScriptedSounddevice:
    class PortAudioError(Exception):
        pass

    def __init__(self, flag_on: tuple[int, ...]) -> None:
        self._flag_on = flag_on

    def RawInputStream(self, **kwargs: Any) -> _ScriptedStream:  # noqa: N802 - the library's name
        return _ScriptedStream(kwargs["callback"], self._flag_on)


class _OneStream:
    """A stream that records its calls; ``start`` or ``abort`` can raise."""

    latency = 0.1

    def __init__(
        self, start_raises: BaseException | None, abort_raises: BaseException | None
    ) -> None:
        self._start_raises = start_raises
        self._abort_raises = abort_raises
        self.calls: list[str] = []

    def start(self) -> None:
        self.calls.append("start")
        if self._start_raises is not None:
            raise self._start_raises

    def abort(self) -> None:
        self.calls.append("abort")
        if self._abort_raises is not None:
            raise self._abort_raises

    def close(self, ignore_errors: bool = False) -> None:
        self.calls.append("close")


class _OneStreamSounddevice:
    class PortAudioError(Exception):
        pass

    def __init__(
        self,
        *,
        start_raises: BaseException | None = None,
        abort_raises: BaseException | None = None,
    ) -> None:
        self._start_raises = start_raises
        self._abort_raises = abort_raises
        self.streams: list[_OneStream] = []

    def RawInputStream(self, **kwargs: Any) -> _OneStream:  # noqa: N802 - the library's name
        stream = _OneStream(self._start_raises, self._abort_raises)
        self.streams.append(stream)
        return stream


class _StopsEarlyOpener:
    """Two callbacks 100 ms apart, then none: a stream that stopped
    delivering early with no status flag."""

    def __init__(self) -> None:
        self.thread: threading.Thread | None = None

    def __call__(self, recorder: Any) -> tuple[Callable[[], None], float | None]:
        def run() -> None:
            recorder.block(160)
            time.sleep(0.1)
            recorder.block(160)

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

        def stop() -> None:
            assert self.thread is not None
            self.thread.join()

        return stop, None


class _EntriesOpener:
    """Callback entry times given as offsets from the open, written straight
    into the recorder (no thread, no flag)."""

    def __init__(self, offsets_ns: tuple[int, ...]) -> None:
        self._offsets_ns = offsets_ns

    def __call__(self, recorder: Any) -> tuple[Callable[[], None], float | None]:
        start = time.perf_counter_ns()
        recorder.entries.extend(start + offset for offset in self._offsets_ns)
        recorder.first.set()
        return lambda: None, None


class _ScriptedBackend:
    """``SoundDeviceBackend.open_stream``'s shape: a flag is an ``on_error``."""

    def __init__(self, flag_on: tuple[int, ...]) -> None:
        self._flag_on = flag_on

    def open_stream(
        self,
        device_id: int,
        on_block: Callable[[bytes], None],
        on_error: Callable[[Exception], None],
    ) -> SimpleNamespace:
        def tick(number: int) -> None:
            on_block(b"\x00\x00" * 160)
            if number in self._flag_on:
                on_error(audio_capture.CaptureOverflowError(DEVICE_NAME))

        ticker = _Numbered(0.01, tick)
        ticker.start()
        return SimpleNamespace(stop=ticker.stop)


def _counts_only(tool: ModuleType, row: Any) -> Any:
    """The measured row's COUNTS with every value a passing one, so the rule
    reads only what the run left missing (no timing is scored)."""
    if row.refused:
        return row
    stalls = next(iter(row.stalls.values()), ())
    return replace(
        row,
        gaps_ns=(100 * MS,) * len(row.gaps_ns),
        stalls={2.0: _trials(tool, len(stalls))},
        tails_ns=(60 * MS,) * len(row.tails_ns),
        stops_ns=(100 * MS,) * len(row.stops_ns),
        firsts_ns=(150 * MS,) * len(row.firsts_ns),
    )


class TestTheProtocolAsRun:
    @pytest.mark.parametrize(
        ("flag_on", "flagged", "offset"), [((3,), False, None), ((11,), True, 0), ((12,), True, 1)]
    )
    def test_a_stall_trial_counts_flags_from_the_stalled_callback(
        self, tool: ModuleType, flag_on: tuple[int, ...], flagged: bool, offset: int | None
    ) -> None:
        trial = tool.run_stall_trial(_ScriptedOpener(tool, flag_on=flag_on), 0.03, _quick(tool))
        assert (trial.flagged, trial.flag_offset) == (flagged, offset)

    def test_the_stall_is_in_the_eleventh_callback_after_its_entry_is_stamped(
        self, tool: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        opener = _ScriptedOpener(tool)
        seen: list[tuple[int, int, int, float]] = []

        def sleep(seconds: float) -> None:
            if opener.threads and threading.current_thread() is opener.threads[-1]:
                entries = opener.recorders[-1].entries
                seen.append((len(entries), entries[-1], time.perf_counter_ns(), seconds))
            time.sleep(seconds)

        clock = SimpleNamespace(perf_counter_ns=time.perf_counter_ns, sleep=sleep)
        monkeypatch.setattr(tool, "time", clock)
        tool.run_stall_trial(opener, 0.03, _quick(tool))
        assert len(seen) == 1
        entered, stamp, began, seconds = seen[0]
        assert (entered, seconds) == (11, 0.03)
        assert stamp <= began

    def test_the_observation_after_the_stall_is_honoured(self, tool: ModuleType) -> None:
        opener = _ScriptedOpener(tool)
        trial = tool.run_stall_trial(opener, 0.03, replace(_quick(tool), observe_ns=1000 * MS))
        recorder = opener.recorders[0]
        assert recorder.returned_ns - recorder.entries[10] >= 0.9 * 30 * MS
        assert opener.stopped_ns[0] - recorder.returned_ns >= 900 * MS
        assert trial.residual_ns is not None  # the tail set was observed

    def test_the_cadence_run_counts_a_flag(self, tool: ModuleType) -> None:
        gaps, flags, read_back = tool.run_cadence(_ScriptedOpener(tool, flag_on=(3,)), _quick(tool))
        assert flags == 1 and gaps and read_back is None
        assert tool.run_cadence(_ScriptedOpener(tool), _quick(tool))[1] == 0

    def test_callbacks_that_stop_early_are_an_incomplete_cadence(self, tool: ModuleType) -> None:
        """D5 (b) is measured over the whole window: two healthy callbacks
        100 ms apart and then none, with no flag, give no flag count, so bar
        (b) fails and a row passing every other bar is not chosen."""
        sched = replace(_quick(tool), cadence_ns=600 * MS)
        gaps, flags, _read_back = tool.run_cadence(_StopsEarlyOpener(), sched)
        assert len(gaps) == 1 and flags is None
        row = _candidate(tool, 2.5, gaps_ns=(100 * MS,) * len(gaps), cadence_flags=flags)
        result = tool.evaluate("mme", [_default_row(tool), row])
        assert {key for key, value in result.bars["2.5 s"].items() if value is not True} == {"b"}
        assert result.chosen is None
        # The same row with a whole window's flag count is chosen.
        whole = tool.evaluate("mme", [_default_row(tool), replace(row, cadence_flags=0)])
        assert whole.chosen == 2.5

    def test_a_full_window_cadence_has_a_flag_count_and_passes_bar_b(
        self, tool: ModuleType
    ) -> None:
        """The deliberate stop at the window's end does not make a normal run
        incomplete (the window is longer than the 250 ms bound here)."""
        sched = replace(_quick(tool), cadence_ns=600 * MS)
        gaps, flags, _read_back = tool.run_cadence(_ScriptedOpener(tool), sched)
        assert isinstance(flags, int) and flags == 0 and gaps
        row = _counts_only(tool, _candidate(tool, 2.5, gaps_ns=gaps, cadence_flags=flags))
        assert _one(tool, row)["b"] is True

    @pytest.mark.parametrize(("late_ns", "complete"), [(0, True), (1, False)])
    def test_the_incomplete_bound_is_the_p99_bar_before_the_window_ends(
        self, tool: ModuleType, late_ns: int, complete: bool
    ) -> None:
        """The last callback exactly ``CADENCE_P99_NS`` before the window's
        end still counts as a whole window; a nanosecond earlier does not."""
        window = 600 * MS
        last = window - tool.CADENCE_P99_NS - late_ns
        sched = replace(_quick(tool), cadence_ns=window)
        gaps, flags, _read_back = tool.run_cadence(_EntriesOpener((0, last)), sched)
        assert gaps == (last,)
        assert flags == (0 if complete else None)

    @pytest.mark.parametrize("mode", ["raw", "product"])
    def test_a_truthy_status_and_an_on_error_are_each_a_flag(
        self, tool: ModuleType, mode: str
    ) -> None:
        if mode == "raw":
            sd = _ScriptedSounddevice(flag_on=(12,))
            opener = tool.raw_opener(sd, audio_capture, 1, None)
        else:
            opener = tool.product_opener(audio_capture, _ScriptedBackend(flag_on=(12,)), 1)
        trial = tool.run_stall_trial(opener, 0.03, _quick(tool))
        assert (trial.flagged, trial.flag_offset) == (True, 1)

    def test_an_interrupted_start_closes_the_stream_and_propagates(
        self, tool: ModuleType
    ) -> None:
        """A KeyboardInterrupt during ``start()`` is not a refusal: the stream
        is closed and the interruption propagates unchanged, with no retry."""
        interruption = KeyboardInterrupt()
        sd = _OneStreamSounddevice(start_raises=interruption)
        opener = tool.raw_opener(sd, audio_capture, 1, 2.5)
        with pytest.raises(KeyboardInterrupt) as caught:
            opener(tool.Recorder())
        assert caught.value is interruption
        assert not isinstance(caught.value, tool.OpenRefused)
        (stream,) = sd.streams
        assert stream.calls == ["start", "close"]

    def test_a_stop_whose_abort_raises_still_closes_the_stream(self, tool: ModuleType) -> None:
        sd = _OneStreamSounddevice(abort_raises=RuntimeError("abort refused"))
        stop, read_back = tool.raw_opener(sd, audio_capture, 1, None)(tool.Recorder())
        assert read_back == 0.1
        with pytest.raises(RuntimeError, match="abort refused"):
            stop()
        (stream,) = sd.streams
        assert stream.calls == ["start", "abort", "close"]

    @pytest.mark.parametrize(
        ("refuse_on", "cadence", "failing"),
        [
            ((), True, set()),
            ((1,), True, None),  # the first open (the cadence run): the row is refused
            ((1,), False, None),  # --product: the first open is a stall trial
            ((2,), True, {"a"}),  # one stall trial missing
            ((12,), True, {"c", "d", "e"}),  # one tail trial missing
            ((32,), True, set()),  # the stop inside a stall is information only
        ],
    )
    def test_a_refused_open_fails_only_the_bars_needing_its_figure(
        self,
        tool: ModuleType,
        refuse_on: tuple[int, ...],
        cadence: bool,
        failing: set[str] | None,
    ) -> None:
        # Opens: 1 cadence, 2-11 the stall trials, 12-31 the tail trials, 32 the stop in a stall.
        sched = replace(
            _quick(tool),
            lead=1,
            observe_ns=10 * MS,
            cadence_ns=60 * MS,
            tail_run_ns=10 * MS,
            tail_jitter_ns=0,
            tail_trials=20,
            stall_plan=((0.0, 10),),
            stop_stall_s=0.0,
        )
        opener = _ScriptedOpener(tool, refuse_on=refuse_on)
        row = tool.measure_row("2.5 s", 2.5, opener, sched, lambda text: None, cadence=cadence)
        bars = _one(tool, _counts_only(tool, row))
        if failing is None:
            assert row.refused and opener.calls == 1
            assert bars == {"a": False, "b": None, "c": None, "d": None, "e": None}
            return
        assert not row.refused and opener.calls == 32
        assert {key for key, value in bars.items() if value is not True} == failing
        assert (row.stop_in_stall is None) is (refuse_on == (32,))


# --- the run: refusals, the list, the paste block -----------------------------------------


class TestRefusals:
    @pytest.mark.parametrize(
        ("layer", "expected"),
        [
            (lambda: WerLayer({}), "crash reports"),
            (lambda: WerLayer(error=OSError("denied")), "could not check"),
        ],
    )
    def test_crash_reports_not_excluded_refuses_before_anything_opens(
        self,
        tool: ModuleType,
        seams: _Seams,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        layer: Callable[[], WerLayer],
        expected: str,
    ) -> None:
        monkeypatch.setattr(tool, "_windows_layer", layer)
        assert tool.main([]) == 2
        out = capsys.readouterr().out
        assert out.count("[refused]") == 1 and expected in out
        # Before the instance exclusion and before sounddevice is imported.
        assert (seams.acquired, seams.imports) == (0, 0)

    @pytest.mark.parametrize("state", ["already_running", "unavailable"])
    def test_an_open_app_refuses_before_any_stream(
        self, tool: ModuleType, seams: _Seams, capsys: pytest.CaptureFixture[str], state: str
    ) -> None:
        seams.state = state
        assert tool.main([]) == 2
        out = capsys.readouterr().out
        assert out.count("[refused]") == 1 and "close Clinic Scribe first" in out
        assert (seams.acquired, seams.released, seams.imports) == (1, 1, 0)

    def test_product_mode_needs_the_built_constant(
        self,
        tool: ModuleType,
        seams: _Seams,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        unbuilt = SimpleNamespace(SAMPLE_RATE=16_000, BLOCK_FRAMES=1600, CHANNELS=1)
        monkeypatch.setattr(tool, "_import_audio_capture", lambda: unbuilt)
        assert tool.main(["--product"]) == 2
        assert "INPUT_LATENCY_SECONDS" in capsys.readouterr().out
        assert (seams.acquired, seams.imports) == (0, 0)

    def test_a_block_that_is_not_100_ms_refuses(
        self,
        tool: ModuleType,
        seams: _Seams,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        other = SimpleNamespace(SAMPLE_RATE=16_000, BLOCK_FRAMES=800, CHANNELS=1)
        monkeypatch.setattr(tool, "_import_audio_capture", lambda: other)
        assert tool.main([]) == 2
        assert "[refused]" in capsys.readouterr().out and seams.imports == 0

    @pytest.mark.parametrize("argv", [["--device", "0"], ["--device", "7"], ["--device", "-1"]])
    def test_a_device_that_is_not_an_input_is_refused_without_its_name(
        self, tool: ModuleType, seams: _Seams, capsys: pytest.CaptureFixture[str], argv: list[str]
    ) -> None:
        seams.sounddevice = _FakeSounddevice()
        assert tool.main(argv) == 2
        out = capsys.readouterr().out
        assert "not an input device id" in out and DEVICE_NAME not in out
        assert seams.sounddevice.opened == [] and seams.released == 1


class TestTheList:
    def test_the_list_shows_names_on_screen_and_opens_nothing(
        self,
        tool: ModuleType,
        seams: _Seams,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        seams.sounddevice = _FakeSounddevice()
        # No stream is opened, so the list needs neither refusal.
        monkeypatch.setattr(tool, "_windows_layer", lambda: WerLayer({}))
        assert tool.main(["--list"]) == 0
        out = capsys.readouterr().out
        assert "do NOT paste" in out
        assert re.search(rf"1\s+mme\s+{re.escape(DEVICE_NAME)} \(default\)", out)
        assert re.search(rf"2\s+wasapi\s+{re.escape(DEVICE_NAME)}", out)
        assert "Speakers" not in out  # no input channels
        assert (seams.acquired, seams.sounddevice.opened) == (0, [])

    def test_the_list_survives_a_redirected_stream_that_cannot_encode_a_name(
        self,
        tool: ModuleType,
        seams: _Seams,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake = _FakeSounddevice()
        fake.query_devices(1)["name"] = "Zo\u00eb\u2019s Headset"
        seams.sounddevice = fake
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="ascii", errors="strict")
        monkeypatch.setattr(sys, "stdout", stream)
        assert tool.main(["--list"]) == 0
        stream.flush()
        assert b"Zo??s Headset" in raw.getvalue()


class TestTheRun:
    def test_the_paste_block_holds_numbers_an_id_and_a_host_word_and_no_name(
        self, tool: ModuleType, seams: _Seams, capsys: pytest.CaptureFixture[str]
    ) -> None:
        fake = _FakeSounddevice(refuse=(1.0,))
        seams.sounddevice = fake
        assert tool.main([], schedule=_quick(tool)) == 0
        out = capsys.readouterr().out
        assert DEVICE_NAME not in out and "Jane" not in out
        block = _block_of(out)
        assert "- sounddevice 0.5.5; PortAudio V19.7.0-devel, revision unknown" in block
        assert re.search(r"^- audio_capture: (this|another) checkout$", block, flags=re.MULTILINE)
        assert audio_capture.__file__ not in block
        assert "- device id 1; host mme; mode raw" in block
        assert "- default input latency, low / high, ms: 90 / 180" in block
        assert "| 1 s | refused |" in block
        assert "| default | 100 |" in block and "| 2.5 s | 100 |" in block  # the read-back
        assert "| default | 0.03 | 2 |" in block and "| 2.5 s | 0.03 | 2 |" in block
        assert "| candidate | (a) | (b) | (c) | (d) | (e) |" in block
        assert "| 1 s | fail | - | - | - | - |" in block
        assert "- interpreter-lock row (default buffer): " in block
        lines = block.strip().splitlines()
        assert re.fullmatch(r"premise: (met|not met)", lines[-2])
        assert re.fullmatch(r"chosen: (none|\d\.\d)", lines[-1])
        assert (seams.acquired, seams.released) == (1, 1)

        # The app's own stream arguments; ``latency=`` only for a candidate.
        first = fake.opened[0]
        assert "latency" not in first
        assert {key: first[key] for key in first if key != "callback"} == {
            "samplerate": audio_capture.SAMPLE_RATE,
            "blocksize": audio_capture.BLOCK_FRAMES,
            "device": 1,
            "channels": audio_capture.CHANNELS,
            "dtype": "int16",
        }
        assert {kwargs.get("latency") for kwargs in fake.opened} == {None, 1.0, 2.5}
        # A refused row opens once; every stream that opened was closed.
        assert sum(kwargs.get("latency") == 1.0 for kwargs in fake.opened) == 1
        assert fake.streams and all(stream.closed for stream in fake.streams)

    def test_the_device_given_is_the_one_opened(
        self, tool: ModuleType, seams: _Seams, capsys: pytest.CaptureFixture[str]
    ) -> None:
        fake = _FakeSounddevice()
        fake.default = SimpleNamespace(device=(-1, 3))
        seams.sounddevice = fake
        sched = replace(_quick(tool), candidates=())
        assert tool.main(["--device", "1"], schedule=sched) == 0
        assert "- device id 1; host mme; mode raw" in _block_of(capsys.readouterr().out)
        assert {kwargs["device"] for kwargs in fake.opened} == {1}

    def test_a_device_that_is_not_mme_is_named_and_not_measured(
        self, tool: ModuleType, seams: _Seams, capsys: pytest.CaptureFixture[str]
    ) -> None:
        fake = _FakeSounddevice()
        seams.sounddevice = fake
        assert tool.main(["--device", "2"], schedule=_quick(tool)) == 0
        block = _block_of(capsys.readouterr().out)
        assert "- device id 2; host wasapi; mode raw" in block
        assert "- not scored: this device's host API is not MME" in block
        assert block.strip().splitlines()[-2:] == ["premise: not met", "chosen: none"]
        assert fake.opened == [] and DEVICE_NAME not in block

    def test_product_mode_runs_through_the_backend_s_own_open(
        self,
        tool: ModuleType,
        seams: _Seams,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        built: list[dict[str, Any]] = []
        opened: list[int] = []
        stopped: list[int] = []

        class Backend:
            def __init__(self, **kwargs: Any) -> None:
                built.append(kwargs)

            def open_stream(
                self,
                device_id: int,
                on_block: Callable[[bytes], None],
                on_error: Callable[[Exception], None],
            ) -> SimpleNamespace:
                def tick(late: bool) -> None:
                    on_block(b"\x00\x00" * 4)
                    if late:
                        on_error(audio_capture.CaptureOverflowError(DEVICE_NAME))

                ticker = _Ticker(0.01, tick)
                opened.append(device_id)

                def stop() -> None:
                    ticker.stop()
                    stopped.append(device_id)

                ticker.start()
                return SimpleNamespace(stop=stop)

        capture = SimpleNamespace(
            SAMPLE_RATE=16_000,
            BLOCK_FRAMES=1600,
            CHANNELS=1,
            SAMPLE_WIDTH=2,
            INPUT_LATENCY_SECONDS=2.5,
            AudioCaptureError=audio_capture.AudioCaptureError,
            SoundDeviceBackend=Backend,
            __file__=r"C:\checkout\src\scribe_desktop\audio_capture.py",
        )
        monkeypatch.setattr(tool, "_import_audio_capture", lambda: capture)
        fake = _FakeSounddevice()
        seams.sounddevice = fake
        assert tool.main(["--product"], schedule=_quick(tool)) == 0
        out = capsys.readouterr().out
        block = _block_of(out)
        # The default-buffer instance and the product's own.
        assert built == [{"input_latency": None}, {}]
        assert "- device id 1; host mme; mode product" in block
        assert "- audio_capture: another checkout" in block and r"C:\checkout" not in block
        assert "| product default | 0.03 | 2 |" in block and "| product 2.5 s | 0.03 | 2 |" in block
        assert "| candidate | (a) | (c) | (d) | (e) |" in block and "gap median" not in block
        assert re.fullmatch(r"product: (pass|fail)", block.strip().splitlines()[-1])
        assert "premise:" not in block and DEVICE_NAME not in out
        # Never a raw stream; every open through the backend was stopped.
        assert fake.opened == [] and opened and len(opened) == len(stopped)


def _identity(tool: ModuleType, *, host: str = "mme", mode: str = "raw") -> Any:
    return tool.Identity(
        sounddevice_version="0.5.5",
        portaudio_version="PortAudio V19.7.0-devel",
        module_checkout="this checkout",
        device_id=1,
        host=host,
        mode=mode,
    )


def _block_lines(tool: ModuleType, identity: Any, rows: list[Any]) -> list[str]:
    block = tool.paste_block(identity, rows, tool.evaluate(identity.host, rows))
    return str(block).splitlines()


def _product_rows(tool: ModuleType, **changes: Any) -> list[Any]:
    default = replace(_default_row(tool), label="product default")
    return [default, replace(_candidate(tool, 2.5, **changes), label="product 2.5 s")]


class TestTheVerdictLines:
    def test_a_product_row_passing_a_c_d_and_e_is_a_pass(self, tool: ModuleType) -> None:
        lines = _block_lines(tool, _identity(tool, mode="product"), _product_rows(tool))
        assert lines[-1] == "product: pass"

    @pytest.mark.parametrize(
        "changes",
        [
            {"stalls": {2.0: ()}},  # (a)
            {"tails_ns": (110 * MS + 1,) * 20},  # (c)
            {"stops_ns": (350 * MS + 1,) * 20},  # (d)
            {"firsts_ns": (400 * MS + 1,) * 20},  # (e)
        ],
    )
    def test_one_product_bar_failing_is_a_fail(
        self, tool: ModuleType, changes: dict[str, Any]
    ) -> None:
        lines = _block_lines(tool, _identity(tool, mode="product"), _product_rows(tool, **changes))
        assert lines[-1] == "product: fail"

    def test_a_product_run_off_mme_or_without_its_row_is_a_fail(self, tool: ModuleType) -> None:
        off_mme = _identity(tool, host="wasapi", mode="product")
        assert _block_lines(tool, off_mme, _product_rows(tool))[-1] == "product: fail"
        alone = _product_rows(tool)[:1]
        assert _block_lines(tool, _identity(tool, mode="product"), alone)[-1] == "product: fail"

    def test_a_refused_product_row_is_shown_in_the_stall_table(self, tool: ModuleType) -> None:
        rows = [
            tool.Row("product default", None, refused=True),
            tool.Row("product 2.5 s", 2.5, refused=True),
        ]
        lines = _block_lines(tool, _identity(tool, mode="product"), rows)
        assert "| product default | refused | - | - | - | - | - | - |" in lines
        assert "| product 2.5 s | refused | - | - | - | - | - | - |" in lines
        assert lines[-1] == "product: fail"

    def test_the_smallest_passing_candidate_is_the_chosen_line(self, tool: ModuleType) -> None:
        rows = [
            _default_row(tool),
            _candidate(tool, 2.0, stalls={2.0: _trials(tool, 10, flagged=1)}),
            _candidate(tool, 2.5),
            _candidate(tool, 3.0),
        ]
        assert _block_lines(tool, _identity(tool), rows)[-2:] == ["premise: met", "chosen: 2.5"]

    def test_no_passing_candidate_is_chosen_none(self, tool: ModuleType) -> None:
        failing = {2.0: _trials(tool, 10, flagged=1)}
        rows = [_default_row(tool)] + [
            _candidate(tool, latency, stalls=failing) for latency in tool.CANDIDATES
        ]
        assert _block_lines(tool, _identity(tool), rows)[-2:] == ["premise: met", "chosen: none"]


class TestTheMeasurementStops:
    @pytest.mark.parametrize(
        ("error", "line"),
        [
            (KeyboardInterrupt(), "[refused] interrupted"),
            (RuntimeError(DEVICE_NAME), "[refused] stopped: RuntimeError"),
        ],
    )
    def test_a_stopped_measurement_is_refused_by_type_and_the_lock_released(
        self,
        tool: ModuleType,
        seams: _Seams,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        error: BaseException,
        line: str,
    ) -> None:
        def measure(*args: object) -> int:
            raise error

        monkeypatch.setattr(tool, "_measure", measure)
        assert tool.main([]) == 2
        captured = capsys.readouterr()
        assert captured.out == line + "\n" and captured.err == ""
        assert "Traceback" not in captured.out and DEVICE_NAME not in captured.out
        assert (seams.acquired, seams.released) == (1, 1)

    def test_the_checkout_word(self, tool: ModuleType) -> None:
        own = REPO / "desktop" / "src" / "scribe_desktop" / "audio_capture.py"
        assert tool.checkout_word(str(own)) == "this checkout"
        assert tool.checkout_word(str(REPO / "desktop" / "src-other" / "x.py")) == (
            "another checkout"
        )
        assert tool.checkout_word(r"C:\checkout\src\scribe_desktop\audio_capture.py") == (
            "another checkout"
        )
        assert tool.checkout_word("scribe_desktop/audio_capture.py") == "another checkout"
        assert tool.checkout_word(None) == "another checkout"

    @pytest.mark.parametrize(
        ("module_file", "word"),
        [
            (str(REPO / "desktop" / "src" / "scribe_desktop" / "audio_capture.py"), "this"),
            (r"C:\checkout\src\scribe_desktop\audio_capture.py", "another"),
        ],
    )
    def test_the_audio_capture_line_names_the_checkout_never_its_path(
        self,
        tool: ModuleType,
        seams: _Seams,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        module_file: str,
        word: str,
    ) -> None:
        capture = SimpleNamespace(SAMPLE_RATE=16_000, BLOCK_FRAMES=1600, CHANNELS=1)
        capture.__file__ = module_file
        monkeypatch.setattr(tool, "_import_audio_capture", lambda: capture)
        seams.sounddevice = _FakeSounddevice()
        # Device 2 is on WASAPI: the block is printed and no stream opens.
        assert tool.main(["--device", "2"], schedule=_quick(tool)) == 0
        lines = _block_of(capsys.readouterr().out).splitlines()
        assert f"- audio_capture: {word} checkout" in lines
        assert not any("audio_capture.py" in text for text in lines)


class TestTheLockHold:
    def test_a_hold_that_releases_the_lock_fails_the_self_check(self, tool: ModuleType) -> None:
        # ``time.sleep`` releases the interpreter lock: the heartbeat goes on.
        assert tool.lock_hold_stops_a_thread(time.sleep, 1.0) is False

    @pytest.mark.skipif(sys.platform != "win32", reason="the lock-holding call is Windows-only")
    def test_the_real_lock_hold_stops_a_thread(self, tool: ModuleType) -> None:
        if not tool._gil_enabled():
            pytest.skip("this interpreter has no interpreter lock")
        assert tool.lock_hold_stops_a_thread(tool._hold_interpreter_lock, 0.5) is True

    def test_a_raising_hold_leaves_no_heartbeat_running(self, tool: ModuleType) -> None:
        before = threading.active_count()

        def hold(seconds: float) -> None:
            raise RuntimeError(DEVICE_NAME)

        with pytest.raises(RuntimeError):
            tool.lock_hold_stops_a_thread(hold, 0.1)
        assert threading.active_count() <= before

    @pytest.mark.skipif(sys.platform != "win32", reason="the lock-hold row runs on Windows only")
    def test_a_failing_lock_hold_row_is_reported_by_type(self, tool: ModuleType) -> None:
        if not tool._gil_enabled():
            pytest.skip("this interpreter has no interpreter lock")

        def hold(seconds: float) -> None:
            raise RuntimeError(DEVICE_NAME)

        row = tool.run_lock_hold(_ScriptedOpener(tool), _quick(tool), hold)
        assert row == "not measured (RuntimeError)"


class TestCustody:
    def test_the_script_writes_no_file_and_calls_no_logger(self) -> None:
        """C4, as a text guard (not a proof): no file is opened, no audio or
        logging module is imported, and ``sounddevice`` only inside its seam."""
        source = SCRIPT.read_text(encoding="utf-8")
        code = source.split('"""', 2)[2]
        assert not re.search(r"(?<![\w.])open\(", code)
        assert not re.search(r"\.write\(|write_text|write_bytes|Path\(", code)
        imported = set(re.findall(r"^\s*(?:import|from)\s+([\w.]+)", code, flags=re.MULTILINE))
        assert imported.isdisjoint({"wave", "logging", "pathlib", "tempfile", "numpy"})
        assert code.count("import sounddevice") == 1
        assert "def _import_sounddevice() -> Any:\n    import sounddevice\n" in code

    def test_the_docstring_gives_the_exact_command(self, tool: ModuleType) -> None:
        doc = tool.__doc__ or ""
        assert r"& 'C:\Recording clinic software\.venv\Scripts\python.exe'" in doc
        assert r"\scripts\measure-capture-stall.py'" in doc
