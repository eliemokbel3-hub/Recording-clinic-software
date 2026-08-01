"""Hardware benchmark: real-time-factor (RTF) measurement for Whisper candidates.

Measures, per candidate model in the local cache:
  - model load time
  - transcription time for a synthetic speech sample (word timestamps ON)
  - RTF = transcription seconds / audio seconds
  - peak process memory (each model runs in a fresh subprocess so the
    Windows peak-working-set counter is per-model, not cumulative)

Threshold policy (plan: "RTF < 1.0 required with margin; warning on failure —
never cloud fallback"): RTF <= RTF_MARGIN is OK, RTF < RTF_REQUIRED is a
WARNING (usable but slow), RTF >= RTF_REQUIRED FAILS the threshold. A failed
threshold only ever produces a local warning; there is no cloud fallback.

Offline enforcement: the offline env kill-switches are set AND asserted before
any ML import. Models must already be local (scripts/setup-models.py); this
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
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

# RTF thresholds (plan Step 5 / Step 10). RTF < 1.0 is required; the margin
# leaves headroom for clinic machines slower than the dev machine.
RTF_REQUIRED = 1.0
RTF_MARGIN = 0.75

# Offline kill-switches (plan Design Decision "Runtime offline enforcement").
OFFLINE_ENV: dict[str, str] = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
}

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


class OfflineEnvError(RuntimeError):
    """The offline kill-switches are not active where they are required."""


def apply_offline_env() -> None:
    """Set the offline kill-switch environment variables for this process."""
    for key, value in OFFLINE_ENV.items():
        os.environ[key] = value


def assert_offline_env() -> None:
    """Raise OfflineEnvError unless every offline kill-switch is set to '1'."""
    missing = [k for k, v in OFFLINE_ENV.items() if os.environ.get(k) != v]
    if missing:
        raise OfflineEnvError(
            "offline kill-switches not active: " + ", ".join(sorted(missing))
        )


def default_models_root() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is not set; model cache location unknown")
    return Path(local_app_data) / "ClinikoScribe" / "models"


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


def threshold_report(results: list[BenchmarkResult]) -> list[str]:
    """Human-readable threshold report. Never suggests any cloud fallback."""
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
            f"no whisper models under {models_root} - run scripts/setup-models.py first"
        )

    with tempfile.TemporaryDirectory() as tmp:
        audio_path = Path(tmp) / "benchmark_sample.wav"
        audio_seconds = generate_speech_sample(audio_path)
        results: list[BenchmarkResult] = []
        for name in candidates:
            env = dict(os.environ) | OFFLINE_ENV | {_WORKER_ENV: "1"}
            proc = subprocess.run(  # noqa: S603 - fixed argv, our own interpreter
                [
                    sys.executable,
                    "-m",
                    "scribe_desktop.benchmark",
                    "--single",
                    name,
                    "--models-root",
                    str(models_root),
                    "--audio",
                    str(audio_path),
                    "--audio-seconds",
                    f"{audio_seconds}",
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
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
