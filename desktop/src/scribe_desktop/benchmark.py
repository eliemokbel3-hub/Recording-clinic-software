"""Hardware benchmark: real-time-factor (RTF) measurement for Whisper candidates.

Measures, per candidate model in the local cache:
  - model load time
  - transcription time for a synthetic speech sample (word timestamps ON)
  - RTF = transcription seconds / audio seconds
  - peak process memory (each model runs in a fresh subprocess so the
    Windows peak-working-set counter is per-model, not cumulative)
  - live window latency: how long one live-transcription window of
    LIVE_WINDOW_SECONDS takes at the measured RTF, and whether the live
    worker keeps up on this machine

Threshold policy (plan: "RTF < 1.0 required with margin; warning on failure —
never cloud fallback"): RTF <= RTF_MARGIN is OK, RTF < RTF_REQUIRED is a
WARNING (usable but slow), RTF >= RTF_REQUIRED FAILS the threshold. A failed
threshold only ever produces a local warning; there is no cloud fallback.

Offline enforcement: the offline env kill-switches are set AND asserted before
any ML import. Models must already be local (``install_layout.models_root``:
scripts/setup-models.py from a source checkout, the installer's model pack in
a packaged build); this
module performs zero network I/O. ML imports are lazy so the module stays
importable without the ML stack installed.

No clinical audio is ever used: the benchmark sample is synthesized speech
(Windows SAPI text-to-speech of a fixed non-clinical script).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess  # noqa: S404 - spawns only sys.executable on this module
import sys
import tempfile
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

from scribe_desktop import install_layout
from scribe_desktop.logging_setup import exception_type_name

# RTF thresholds (plan Step 5 / Step 10). RTF < 1.0 is required; the margin
# leaves headroom for clinic machines slower than the dev machine.
RTF_REQUIRED = 1.0
RTF_MARGIN = 0.75

# Note-learning plan Task 1.6: the live worker transcribes one window of this
# many seconds at a time; the panel projects each model's measured RTF onto
# it. Kept here (not imported) because transcription imports this module —
# tests pin it equal to transcription.TRANSCRIBE_WINDOW_SECONDS.
LIVE_WINDOW_SECONDS = 30.0

# Offline kill-switches (plan Design Decision "Runtime offline enforcement").
OFFLINE_ENV: dict[str, str] = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
}
# Native-library overrides the offline contract REFUSES (note-learning plan
# Phase 4, codex round 22 PR-MED-033): `llama-cpp-python` loads its DLL from
# `LLAMA_CPP_LIB_PATH` when that variable is set, instead of the pinned
# wheel's own `lib/` — an inherited value would swap the native runtime the
# D8 hash pinned, possibly for one on a network share. `apply_offline_env`
# deletes it; `assert_offline_env` fails while it is present, naming it and
# touching no path. `CUDA_PATH` / `HIP_PATH` are NOT refused: the runtime only
# ADDS them as DLL search directories, the CPU wheel's bundled library has no
# CUDA/HIP dependency, and they are ordinary system variables on a GPU host.
FORBIDDEN_NATIVE_OVERRIDES: tuple[str, ...] = ("LLAMA_CPP_LIB_PATH",)
# TLS-secret exports the offline contract REFUSES (Cliniko workflow safeguards
# plan D9, Task 1.1): `ssl.create_default_context()` appends every session's
# TLS secrets to the file `SSLKEYLOGFILE` names, which would let anyone who
# can read that file decrypt the app's Cliniko traffic — the API key included.
# The Cliniko client builds its own context and never reads the variable; this
# closes it for every other context too. Same handling as the native
# overrides: deleted by `apply_offline_env`, refused BY NAME (its value is a
# path, never read) by `assert_offline_env`.
FORBIDDEN_TLS_OVERRIDES: tuple[str, ...] = ("SSLKEYLOGFILE",)

# Fixed, deliberately non-clinical benchmark script (~45 s of speech at
# default SAPI rate). Plain descriptive prose with numbers and names so the
# word-timestamp path is exercised realistically.
BENCHMARK_TEXT = (
    "The quick brown fox jumps over the lazy dog while seventeen geese fly "
    "south for the winter. On Tuesday the fourteenth of March, a train left "
    "the station at nine forty five in the morning, carrying two hundred and "
    "thirty passengers toward the coast. Margaret watched the clouds gather "
    "above the harbour and counted eleven fishing boats returning with the "
    "tide. The lighthouse keeper recorded wind speeds of thirty two knots "
    "and noted that the barometer had fallen sharply since noon. In the town "
    "below, the bakery sold its last loaf of sourdough at half past four, "
    "and the clock tower chimed five times as the ferry crossed the bay. "
    "Researchers measured the temperature at twenty one degrees and logged "
    "the humidity at sixty eight percent before closing the station for the "
    "evening. William packed the instruments carefully into three wooden "
    "crates and labelled each one with the date and destination."
)


# Internal marker: --single is a subprocess worker mode driven only by
# run_all() on its own synthesized sample; it is not a user-facing entry for
# arbitrary audio (the benchmark path never touches clinical recordings).
_WORKER_ENV = "SCRIBE_BENCHMARK_WORKER"

# Installation plan Task 2.1 (D11): a packaged build has no ``-m`` — its
# ``sys.executable`` is ``scribe-app.exe`` — so the worker is that exe with
# this flag first, dispatched by ``app.main`` right after the install-folder
# check (Task 2.7) and before anything else runs (``is_worker_argv``). The
# worker's JSON stays on stdout: Task 0.1 measured the windowed bootloader
# handing a child its parent's pipes intact.
WORKER_FLAG: Final = "--benchmark-worker"
# The worker's options, in the order ``worker_argv`` writes them; each takes
# exactly one value.
_WORKER_OPTIONS: Final = ("--single", "--models-root", "--audio", "--audio-seconds")

# Round 45 SEC-001 (availability): a hung model subprocess must never pin
# the benchmark TaskThread forever (the close guard would then refuse
# window close indefinitely). 10 min per model is ~15x the slowest
# measured candidate on the dev machine (load + transcribe of the ~45 s
# sample); a timeout surfaces as a normal benchmark failure.
_SINGLE_BENCHMARK_TIMEOUT_S: Final = 600.0


class OfflineEnvError(RuntimeError):
    """The offline kill-switches are not active where they are required."""


def apply_offline_env() -> None:
    """Set the offline kill-switch environment variables for this process and
    delete the forbidden native-library and TLS-secret overrides."""
    for key, value in OFFLINE_ENV.items():
        os.environ[key] = value
    for key in FORBIDDEN_NATIVE_OVERRIDES + FORBIDDEN_TLS_OVERRIDES:
        os.environ.pop(key, None)


def assert_offline_env() -> None:
    """Raise OfflineEnvError unless every offline kill-switch is set to '1'
    and no forbidden native-library or TLS-secret override is present (the
    variable is named; its value — a path — is never read or touched)."""
    missing = [k for k, v in OFFLINE_ENV.items() if os.environ.get(k) != v]
    if missing:
        raise OfflineEnvError(
            "offline kill-switches not active: " + ", ".join(sorted(missing))
        )
    present = [k for k in FORBIDDEN_NATIVE_OVERRIDES if k in os.environ]
    if present:
        raise OfflineEnvError(
            "native-library override present, refused: " + ", ".join(sorted(present))
        )
    tls = [k for k in FORBIDDEN_TLS_OVERRIDES if k in os.environ]
    if tls:
        raise OfflineEnvError("TLS key log export present, refused: " + ", ".join(sorted(tls)))


def default_models_root() -> Path:
    """Installation plan Task 1.2: ``install_layout.models_root()`` — the
    install folder's ``models`` when frozen, else the channel's data folder's;
    raises ``RuntimeError`` when ``LOCALAPPDATA`` is unset (source run)."""
    return install_layout.models_root()


# --- shared whisper snapshot completeness (smoke round 21) -----------------
# ONE checker for setup-models, the benchmark, the UI model report and the
# transcription provider. CTranslate2 whisper conversions ship EITHER a
# tokenizer.json (distil-* repos) OR a vocabulary.txt/vocabulary.json
# (Systran small/medium repos) — both layouts load fine; require one of them.
WHISPER_REQUIRED_FILES: Final = ("model.bin", "config.json")
WHISPER_TOKENIZER_FILES: Final = ("tokenizer.json", "vocabulary.txt", "vocabulary.json")


def _present(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def whisper_snapshot_missing(model_dir: Path) -> list[str]:
    """Names of required pieces missing from a CT2 whisper snapshot dir."""
    missing = [name for name in WHISPER_REQUIRED_FILES if not _present(model_dir / name)]
    if not any(_present(model_dir / name) for name in WHISPER_TOKENIZER_FILES):
        missing.append(" or ".join(WHISPER_TOKENIZER_FILES))
    return missing


def whisper_snapshot_complete(model_dir: Path) -> bool:
    return not whisper_snapshot_missing(model_dir)


def list_whisper_candidates(models_root: Path) -> list[str]:
    """Model names present in the local cache (complete CT2 snapshots)."""
    whisper_dir = models_root / "whisper"
    if not whisper_dir.is_dir():
        return []
    return sorted(p.name for p in whisper_dir.iterdir() if whisper_snapshot_complete(p))


@dataclass(frozen=True)
class BenchmarkResult:
    """One candidate model's measurements."""

    model_name: str
    audio_seconds: float
    load_seconds: float
    transcribe_seconds: float
    rtf: float
    peak_memory_bytes: int
    word_count: int

    @property
    def status(self) -> str:
        return classify_rtf(self.rtf)


def compute_rtf(transcribe_seconds: float, audio_seconds: float) -> float:
    if audio_seconds <= 0:
        raise ValueError("audio_seconds must be positive")
    return transcribe_seconds / audio_seconds


def classify_rtf(rtf: float) -> str:
    """'ok' (within margin), 'warning' (meets bar, no margin), or 'fail'."""
    if rtf < 0:
        raise ValueError("rtf cannot be negative")
    if rtf <= RTF_MARGIN:
        return "ok"
    if rtf < RTF_REQUIRED:
        return "warning"
    return "fail"


def live_window_latency(result: BenchmarkResult) -> float:
    """Seconds one live window of LIVE_WINDOW_SECONDS takes to transcribe."""
    return LIVE_WINDOW_SECONDS * result.rtf


def live_window_speed(result: BenchmarkResult) -> float:
    """Window seconds divided by the seconds spent transcribing that window."""
    if result.rtf <= 0:
        raise ValueError("rtf must be positive to project a live window speed")
    return LIVE_WINDOW_SECONDS / live_window_latency(result)


def live_keeps_up(result: BenchmarkResult) -> bool:
    """Whether the live worker keeps up (same threshold policy as the RTF status).

    Within the required bar the worker keeps up; at or above real time it would
    fall behind and stop itself, and the recording is transcribed after Finish.
    """
    return result.status != "fail"


@dataclass(frozen=True)
class ProseBenchmark:
    """Installation plan Task 2.5 (D11): one timing of the prose stage (the
    Narrative style over fixed, non-clinical lines). Numbers only — the
    rendered text is never kept. ``skipped`` is the named line when it was
    not timed (the language model absent, its load failed, a model call
    failed, or no section could be given to it). ``load_seconds`` is the
    model's load, and ``preloaded`` says the process already held the model,
    so no load was timed; ``wall_seconds``
    and ``cpu_seconds`` cover the sections only, the load excluded (round 13
    LOW-001)."""

    sections: int = 0
    rendered: int = 0
    load_seconds: float = 0.0
    model_seconds: float = 0.0
    wall_seconds: float = 0.0
    cpu_seconds: float = 0.0
    skipped: str | None = None
    preloaded: bool = False

    @property
    def seconds_per_section(self) -> float:
        """The model's wall seconds per section it rendered (``rendered``)."""
        return self.model_seconds / self.rendered if self.rendered else 0.0

    @property
    def cpu_per_section(self) -> float:
        """This process's CPU seconds (every thread, the load excluded) per
        section the model rendered."""
        return self.cpu_seconds / self.rendered if self.rendered else 0.0

    @property
    def status(self) -> str:
        return classify_prose(self.seconds_per_section)


# Task 2.5's verdict on the prose stage, in the model's wall seconds per
# section — an INTERPRETATION of the practitioner's 2026-09-18 note-learning
# decision that CPU inference is "acceptable for a few seconds per section",
# pending their ratification: within PROSE_MARGIN_S is OK, below
# PROSE_REQUIRED_S a NOTE, at or above it a WARNING. Like the RTF bar it only
# ever produces a local line; the Clean clinical style never waits on it.
PROSE_MARGIN_S: Final = 5.0
PROSE_REQUIRED_S: Final = 10.0


def classify_prose(seconds_per_section: float) -> str:
    """'ok', 'warning' or 'fail' for the prose stage (``PROSE_*_S``)."""
    if seconds_per_section < 0:
        raise ValueError("seconds cannot be negative")
    if seconds_per_section <= PROSE_MARGIN_S:
        return "ok"
    if seconds_per_section < PROSE_REQUIRED_S:
        return "warning"
    return "fail"


# The whisper model the installed build ships (D5); its verdict is summarised
# beside the prose stage's.
SHIPPED_WHISPER_MODEL: Final = "medium"


def prose_report(prose: ProseBenchmark) -> list[str]:
    """Task 2.5's lines for the prose stage: the timing, then the verdict
    when it is not OK. Never any text the model wrote."""
    if prose.skipped is not None:
        return [f"Prose stage: not timed - {prose.skipped}"]
    load = "model already loaded" if prose.preloaded else f"load {prose.load_seconds:.1f} s"
    lines = [
        f"Prose stage (Narrative style): {prose.rendered} of {prose.sections} sections, "
        f"{load}; sections {prose.wall_seconds:.1f} s wall, "
        f"{prose.cpu_seconds:.1f} s CPU; {prose.seconds_per_section:.1f} s wall and "
        f"{prose.cpu_per_section:.1f} s CPU per section  {prose.status.upper()}"
    ]
    if prose.status == "fail":
        lines.append(
            f"WARNING: the prose styles take {prose.seconds_per_section:.1f} s per section "
            f"(>= {PROSE_REQUIRED_S:.0f} s) on this machine. They stay local; the Clean "
            "clinical style does not use the language model."
        )
    elif prose.status == "warning":
        lines.append(
            f"NOTE: the prose styles take {prose.seconds_per_section:.1f} s per section "
            f"(> {PROSE_MARGIN_S:.0f} s) on this machine; a long note waits longer for them."
        )
    return lines


def hardware_verdict(results: list[BenchmarkResult], prose: ProseBenchmark) -> str:
    """Task 2.5: one line with the verdict for both — whisper ``medium``
    (the shipped model) and the prose stage."""
    medium = next((r for r in results if r.model_name == SHIPPED_WHISPER_MODEL), None)
    whisper = (
        f"whisper {SHIPPED_WHISPER_MODEL} RTF {medium.rtf:.2f} {medium.status.upper()}"
        if medium is not None
        else f"whisper {SHIPPED_WHISPER_MODEL} not measured (not installed)"
    )
    stage = (
        "prose stage not timed"
        if prose.skipped is not None
        else f"prose stage {prose.seconds_per_section:.1f} s per section {prose.status.upper()}"
    )
    return f"Hardware check: {whisper}; {stage}"


def threshold_report(
    results: list[BenchmarkResult], prose: ProseBenchmark | None = None
) -> list[str]:
    """Human-readable threshold report. Never suggests any cloud fallback.
    With ``prose`` (installation plan Task 2.5) the prose stage's lines and
    the verdict for both follow."""
    lines = [
        f"RTF thresholds: required < {RTF_REQUIRED:.2f}, margin <= {RTF_MARGIN:.2f}",
        f"{'model':<20} {'RTF':>6} {'load s':>7} {'audio s':>8} "
        f"{'peak MiB':>9} {'words':>6}  status",
    ]
    for r in results:
        lines.append(
            f"{r.model_name:<20} {r.rtf:>6.3f} {r.load_seconds:>7.2f} "
            f"{r.audio_seconds:>8.1f} {r.peak_memory_bytes / 2**20:>9.1f} "
            f"{r.word_count:>6}  {r.status.upper()}"
        )
    for r in results:
        if r.rtf <= 0:
            # Round 7 LOW-004: not a measurement (wall-clock over positive
            # audio cannot be zero); say so rather than fail the whole panel.
            lines.append(f"{r.model_name}: live window latency not measurable (RTF 0)")
            continue
        head = (
            f"{r.model_name}: live window latency {live_window_latency(r):.1f} s "
            f"per {LIVE_WINDOW_SECONDS:.0f} s window "
            f"({live_window_speed(r):.2f}x real time)"
        )
        if live_keeps_up(r):
            lines.append(f"{head} - live transcription keeps up on this machine")
        else:
            lines.append(
                f"{head} - live transcription would fall behind here; "
                "the recording is transcribed after Finish instead"
            )
    for r in results:
        if r.status == "fail":
            lines.append(
                f"WARNING: {r.model_name} transcribes slower than real time "
                f"(RTF {r.rtf:.2f} >= {RTF_REQUIRED:.2f}) on this machine. "
                "Transcription stays local; there is no cloud fallback."
            )
        elif r.status == "warning":
            lines.append(
                f"NOTE: {r.model_name} meets the real-time bar without margin "
                f"(RTF {r.rtf:.2f} > {RTF_MARGIN:.2f}); slower clinic hardware "
                "may fall behind real time."
            )
    if prose is not None:
        lines.extend(prose_report(prose))
        lines.append(hardware_verdict(results, prose))
    return lines


def generate_speech_sample(target: Path) -> float:
    """Synthesize the fixed benchmark script to a mono WAV via SAPI.

    Returns the audio duration in seconds, read from the file's OWN header —
    do not assume the requested rate. SAPI ignores the format asked for here:
    the OneCore default voice overrides it at ``AudioOutputStream`` assignment
    and renders 22050 Hz while ``stream.Format.Type`` still reads back 22
    (measured on the dev machine 2026-07-30). That is harmless for benchmarking
    because the WAV goes to faster-whisper by PATH and it resamples on decode,
    and because the duration below comes from the real rate. Anything that
    consumes the raw frames as 16 kHz PCM must resample first — see
    ``tests/sapi_fixture.py``.

    Windows-only (uses SAPI COM). No network, no clinical content.
    """
    import wave

    import win32com.client

    stream = win32com.client.Dispatch("SAPI.SpFileStream")
    # Requested, but not honoured on this machine (see docstring).
    stream.Format.Type = 22  # 22 = SAFT16kHz16BitMono
    stream.Open(str(target), 3)  # 3 = SSFMCreateForWrite
    voice = win32com.client.Dispatch("SAPI.SpVoice")
    voice.AudioOutputStream = stream
    voice.Speak(BENCHMARK_TEXT)
    stream.Close()
    with wave.open(str(target), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


def run_single(model_dir: Path, audio_path: Path, audio_seconds: float) -> BenchmarkResult:
    """Benchmark one local model in THIS process. Offline env must be active."""
    assert_offline_env()
    import psutil
    from faster_whisper import WhisperModel

    started = time.perf_counter()
    model = WhisperModel(
        str(model_dir), device="cpu", compute_type="int8", local_files_only=True
    )
    load_seconds = time.perf_counter() - started

    started = time.perf_counter()
    segments, _info = model.transcribe(str(audio_path), word_timestamps=True)
    word_count = sum(len(segment.words or []) for segment in segments)
    transcribe_seconds = time.perf_counter() - started

    mem = psutil.Process().memory_info()
    peak = int(getattr(mem, "peak_wset", mem.rss))
    return BenchmarkResult(
        model_name=model_dir.name,
        audio_seconds=audio_seconds,
        load_seconds=load_seconds,
        transcribe_seconds=transcribe_seconds,
        rtf=compute_rtf(transcribe_seconds, audio_seconds),
        peak_memory_bytes=peak,
        word_count=word_count,
    )


def worker_argv(
    name: str, models_root: Path, audio_path: Path, audio_seconds: float
) -> list[str]:
    """The argv ``run_all`` spawns for one model: this module under ``-m``
    from a source run; ``scribe-app.exe --benchmark-worker`` in a packaged
    build (installation plan Task 2.1), never a second app — so a packaged
    build refuses (``RuntimeError``) a shape its own dispatch would not
    take, such as a candidate folder named like an option (round 13
    LOW-004)."""
    tail = [
        "--single",
        name,
        "--models-root",
        str(models_root),
        "--audio",
        str(audio_path),
        "--audio-seconds",
        f"{audio_seconds}",
    ]
    if install_layout.is_frozen():
        argv = [sys.executable, WORKER_FLAG, *tail]
        if not is_worker_argv(argv):
            raise RuntimeError(f"benchmark worker arguments for {name} are not admissible")
        return argv
    return [sys.executable, "-m", "scribe_desktop.benchmark", *tail]


def is_worker_argv(argv: Sequence[str]) -> bool:
    """Whether ``argv`` (``sys.argv``, program first) is EXACTLY the frozen
    worker's shape — ``WORKER_FLAG`` then each worker option once, in
    ``worker_argv``'s order, each with one value that is not itself an
    option. Anything else (a missing, extra, reordered or repeated argument)
    is not the worker."""
    rest = list(argv[1:])
    if len(rest) != 1 + 2 * len(_WORKER_OPTIONS) or rest[0] != WORKER_FLAG:
        return False
    pairs = rest[1:]
    for index, option in enumerate(_WORKER_OPTIONS):
        value = pairs[2 * index + 1]
        if pairs[2 * index] != option or not value or value.startswith("-"):
            return False
    return True


def run_worker(argv: Sequence[str]) -> int | None:
    """``app.main``'s first step (installation plan Task 2.1): when this
    launch is the frozen benchmark worker — ``SCRIBE_BENCHMARK_WORKER=1`` set
    by ``run_all`` AND ``is_worker_argv`` — run ``main`` on the options and
    return its exit code. Otherwise ``None``: the launch is not the worker,
    and the arguments are ignored.

    Round 13 MED-003 (C3): the worker runs before ``app.main`` installs its
    exception hooks, so it is its own boundary — an exception is ONE
    ``benchmark_worker error_code=<type name>`` line on stderr (which
    ``run_all`` shows) and exit 1, never a traceback or its message, and
    never the windowed bootloader's traceback box."""
    if os.environ.get(_WORKER_ENV) != "1" or not is_worker_argv(argv):
        return None
    try:
        return main(list(argv[2:]))
    except Exception as exc:  # noqa: BLE001 - the worker's one boundary
        if sys.stderr is not None:
            print(
                f"benchmark_worker error_code={exception_type_name(type(exc))}",
                file=sys.stderr,
                flush=True,
            )
        return 1


def run_all(models_root: Path, names: list[str] | None = None) -> list[BenchmarkResult]:
    """Benchmark each candidate in a fresh subprocess; aggregate results."""
    candidates = list_whisper_candidates(models_root)
    if names:
        unknown = sorted(set(names) - set(candidates))
        if unknown:
            raise RuntimeError(f"models not in local cache: {', '.join(unknown)}")
        candidates = [n for n in candidates if n in names]
    if not candidates:
        raise RuntimeError(
            f"no whisper models under {models_root} - {install_layout.model_remedy()}"
        )

    with tempfile.TemporaryDirectory() as tmp:
        audio_path = Path(tmp) / "benchmark_sample.wav"
        audio_seconds = generate_speech_sample(audio_path)
        results: list[BenchmarkResult] = []
        for name in candidates:
            env = dict(os.environ) | OFFLINE_ENV | {_WORKER_ENV: "1"}
            try:
                proc = subprocess.run(  # noqa: S603 - fixed argv, our own interpreter
                    worker_argv(name, models_root, audio_path, audio_seconds),
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=_SINGLE_BENCHMARK_TIMEOUT_S,
                )
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(
                    f"benchmark subprocess for {name} timed out after "
                    f"{int(_SINGLE_BENCHMARK_TIMEOUT_S)}s"
                ) from exc
            if proc.returncode != 0:
                raise RuntimeError(
                    f"benchmark subprocess for {name} failed: {proc.stderr.strip()}"
                )
            payload = json.loads(proc.stdout)
            results.append(BenchmarkResult(**payload))
        return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--single", help="benchmark one model and print JSON")
    parser.add_argument("--models-root", type=Path, default=None)
    parser.add_argument("--audio", type=Path, help="audio file (single mode)")
    parser.add_argument("--audio-seconds", type=float, help="duration (single mode)")
    parser.add_argument("--models", nargs="*", help="subset of candidates to run")
    args = parser.parse_args(argv)

    apply_offline_env()
    assert_offline_env()
    models_root = args.models_root or default_models_root()

    if args.single:
        if os.environ.get(_WORKER_ENV) != "1":
            parser.error(
                "--single is an internal worker mode used by the aggregate "
                "benchmark run; invoke the benchmark without --single"
            )
        if args.audio is None or args.audio_seconds is None:
            parser.error("--single requires --audio and --audio-seconds")
        result = run_single(
            models_root / "whisper" / args.single, args.audio, args.audio_seconds
        )
        print(json.dumps(asdict(result)))
        return 0

    results = run_all(models_root, args.models or None)
    for line in threshold_report(results):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
