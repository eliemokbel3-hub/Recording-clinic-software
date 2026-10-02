"""Installation plan Task 0.1 SPIKE checks (``scribe-app.exe --spike-checks``) — throwaway.

Runs inside the FROZEN app, against the scratch profile only (the entry's
isolation guard has already passed), and writes one line per check to
``<scratch LOCALAPPDATA>\\spike-results\\checks.txt``. Every check USES the
library, not just imports it (lessons: "a library may raise on first USE"):

- frozen       interpreter version, frozen flag
- stdio        the raw stream state at entry, and a pipe echo through a child
               of this exe with and without the adaptation (spike_stdio.py)
- qt_platform  a QApplication is built; its platform plugin must be "windows"
- qt_network   QtNetwork / QtWebSockets not importable, no Qt6Network*.dll or
               Qt6WebSockets*.dll in the bundle, and not loaded by the app's
               own imports
- keyring      the resolved backend class (want WinVaultKeyring) and one READ
               of a service/name that does not exist (want None); nothing written
- config       config_defaults/*.json found through importlib.resources and
               parsed; ``note_config.load_note_config()`` resolves (pure: it
               writes nothing and creates no directory)
- audio        sounddevice imports and lists input devices (count only; no
               recording)
- onnx         onnxruntime sessions over the silero model and the speaker model
               (the speaker model is SHA-256-checked by the app's own loader)
- sapi_whisper the app's SAPI benchmark sample (fixed non-clinical text) is
               synthesised and transcribed by whisper "medium" in-process
               (ctranslate2, PyAV, tokenizers): word count and real-time factor
- prose        the pinned language model loads through the app's own loader
               (digest check + smoke generation), then the "narrative" prose
               provider renders one synthetic two-line section under Check 5:
               counts and seconds only

Failure details carry the exception type and its message (module and DLL
names are what Task 3.2 needs). There is no clinical data anywhere in a
scratch profile; the only inputs are the fixed synthetic texts below.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from spike_stdio import append_result

# Synthetic, non-clinical-record test lines (the shape of the prose test fixtures).
_PROSE_SECTION = "presenting_complaint"
_PROSE_LINES = ("Neck pain for three days", "Worse on turning left")


def _detail(exc: BaseException) -> str:
    text = " ".join(str(exc).split())
    return f"{type(exc).__name__}: {text[:300]}"


def _frozen() -> str:
    return (
        f"python={sys.version.split()[0]} frozen={getattr(sys, 'frozen', False)} "
        f"bundle={'yes' if hasattr(sys, '_MEIPASS') else 'no'}"
    )


def _stdio_echo(flag: str) -> str:
    proc = subprocess.run(  # noqa: S603 - this exe, fixed argv
        [sys.executable, flag],
        input=b"PING",
        capture_output=True,
        timeout=120,
        check=False,
    )
    if proc.returncode == 0 and proc.stdout == b"PING":
        return "echo=ok"
    return f"echo=failed exit={proc.returncode} bytes_back={len(proc.stdout)}"


def _qt_platform() -> str:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(["scribe-app"])
    name = app.platformName()
    if name != "windows":
        raise RuntimeError(f"platform plugin is {name!r}, not 'windows'")
    return f"platform={name}"


def _qt_network() -> str:
    import scribe_desktop.app  # noqa: F401 - what the app's own imports pull in

    importable = [
        name
        for name in ("PySide6.QtNetwork", "PySide6.QtWebSockets")
        if importlib.util.find_spec(name) is not None
    ]
    loaded = [name for name in ("PySide6.QtNetwork", "PySide6.QtWebSockets") if name in sys.modules]
    bundle = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    dlls = sorted(
        {p.name for pattern in ("Qt6Network*.dll", "Qt6WebSockets*.dll") for p in bundle.rglob(pattern)}
    )
    summary = (
        f"importable={','.join(importable) or 'none'} loaded={','.join(loaded) or 'none'} "
        f"dlls={','.join(dlls) or 'none'}"
    )
    if importable or loaded or dlls:
        raise RuntimeError(summary)
    return summary


def _keyring() -> str:
    import keyring

    backend = keyring.get_keyring()
    name = f"{type(backend).__module__}.{type(backend).__name__}"
    inner = [type(b).__name__ for b in getattr(backend, "backends", ())]
    value = keyring.get_password("ClinikoScribe-spike", "no-such-entry")
    summary = f"backend={name} inner={','.join(inner) or 'none'} read_missing={'None' if value is None else 'NOT-None'}"
    if "WinVaultKeyring" not in name and "WinVaultKeyring" not in inner:
        raise RuntimeError(summary)
    if value is not None:
        raise RuntimeError(summary)
    return summary


def _config() -> str:
    from importlib import resources

    from scribe_desktop.note_config import load_note_config

    folder = resources.files("scribe_desktop") / "config_defaults"
    names = sorted(p.name for p in folder.iterdir() if p.name.endswith(".json"))
    for name in names:
        json.loads((folder / name).read_text(encoding="utf-8"))
    if not names:
        raise RuntimeError("no config_defaults/*.json found")
    config = load_note_config()
    return f"defaults={len(names)} profiles={len(config.template_profiles)}"


def _audio() -> str:
    import sounddevice

    devices = sounddevice.query_devices()
    inputs = sum(1 for d in devices if d["max_input_channels"] > 0)
    return f"portaudio={sounddevice.get_portaudio_version()[1].split(',')[0]} input_devices={inputs}"


def _onnx() -> str:
    from scribe_desktop.benchmark import apply_offline_env, default_models_root
    from scribe_desktop.speaker_embedding import (
        SPEAKER_MODEL_SHA256,
        default_speaker_model_path,
        load_onnx_session,
    )

    apply_offline_env()
    silero = load_onnx_session(default_models_root() / "silero-vad" / "silero_vad.onnx")
    speaker = load_onnx_session(
        default_speaker_model_path(), expected_sha256=SPEAKER_MODEL_SHA256
    )
    import onnxruntime

    return (
        f"onnxruntime={onnxruntime.__version__} silero_inputs={len(silero.get_inputs())} "
        f"speaker_inputs={len(speaker.get_inputs())}"
    )


def _sapi_whisper() -> str:
    from scribe_desktop.benchmark import (
        apply_offline_env,
        default_models_root,
        generate_speech_sample,
        run_single,
    )

    apply_offline_env()
    with tempfile.TemporaryDirectory(dir=Path(default_models_root()).parent) as tmp:
        wav = Path(tmp) / "spike_sample.wav"
        seconds = generate_speech_sample(wav)
        result = run_single(default_models_root() / "whisper" / "medium", wav, seconds)
    if result.word_count <= 0:
        raise RuntimeError("whisper returned no words")
    return (
        f"audio_s={seconds:.1f} words={result.word_count} load_s={result.load_seconds:.1f} "
        f"rtf={result.rtf:.3f}"
    )


def _prose() -> str:
    from scribe_desktop.benchmark import apply_offline_env
    from scribe_desktop.language_model import LocalLanguageModel
    from scribe_desktop.prose_style import ProseInput, ProseStyleProvider

    apply_offline_env()
    started = time.perf_counter()
    model = LocalLanguageModel()
    load_s = time.perf_counter() - started
    provider = ProseStyleProvider(model, style="narrative")
    result = provider.render(ProseInput(((_PROSE_SECTION, _PROSE_LINES),)))
    passed = len(result.passed_sections)
    failed = len(result.failed_sections)
    errored = len(result.errored_sections)
    summary = (
        f"load_s={load_s:.1f} render_s={result.seconds:.1f} "
        f"passed={passed} failed={failed} errored={errored}"
    )
    if errored or passed + failed == 0:
        raise RuntimeError(summary)
    return summary


def run_checks(results: Path, stdio_before: str) -> int:
    out = results / "checks.txt"
    append_result(out, f"=== spike checks start {time.strftime('%Y-%m-%dT%H:%M:%S')} ===")
    checks: list[tuple[str, Callable[[], str]]] = [
        ("frozen", _frozen),
        ("stdio_at_entry", lambda: stdio_before),
        ("stdio_pipe_raw", lambda: _stdio_echo("--spike-stdio-echo-raw")),
        ("stdio_pipe_adapted", lambda: _stdio_echo("--spike-stdio-echo")),
        ("qt_platform", _qt_platform),
        ("qt_network", _qt_network),
        ("keyring", _keyring),
        ("config", _config),
        ("audio", _audio),
        ("onnx", _onnx),
        ("sapi_whisper", _sapi_whisper),
        ("prose", _prose),
    ]
    failures = 0
    for name, check in checks:
        started = time.perf_counter()
        try:
            detail = check()
            verdict = "PASS"
        except BaseException as exc:  # noqa: BLE001 - a spike reports every failure
            detail = _detail(exc)
            verdict = "FAIL"
            failures += 1
        append_result(
            out, f"{name}: {verdict} ({time.perf_counter() - started:.1f} s) {detail}"
        )
    append_result(out, f"=== spike checks done: {len(checks) - failures} of {len(checks)} passed ===")
    return 0 if failures == 0 else 1
