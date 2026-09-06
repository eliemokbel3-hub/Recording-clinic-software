"""Speaker-embedding candidate smoke (practitioner-profile plan, Phase 0 Task 0.3).

Answers ONE question before anything is built on a candidate model: does it
place two recordings of the same voice clearly closer together than a
recording of someone else? Run it YOURSELF from a normal terminal (agent
shells cannot see the user's model cache - docs/lessons.md), after
``scripts/setup-models.py --only speaker-embedding`` has left the candidate
file in the cache:

    .venv\\Scripts\\python.exe scripts\\speaker-embedding-smoke.py ^
        --model "%LOCALAPPDATA%\\ClinikoScribe\\models\\speaker-embedding\\<name>.onnx.candidate" ^
        me-day1.wav me-day2.wav other-person.wav

The model path is EXPLICIT so the un-promoted ``.onnx.candidate`` can be
read; the same command works on the promoted ``<name>.onnx`` later.

What it does, in order:
  1. Sets AND asserts the offline kill-switches, then loads the ONNX model
     the way ``scribe_desktop.speech.SileroVad`` does - offline asserted
     BEFORE ``onnxruntime`` is imported, a UNC path and a missing file
     refused before it too, telemetry off, CPU provider only; from the
     import onward every failure (onnxruntime absent or broken, session
     options, telemetry, session construction) is a ``SpeakerModelError``.
  2. Reads each WAV (16 kHz mono 16-bit PCM, the ``speaker_eval`` reader;
     anything else is refused with the conversion recipe).
  3. Computes the model's front-end in numpy (plan Design Decision D12):
     Kaldi-style 80-bin log-mel fbank, 25 ms frames every 10 ms, DC removal,
     0.97 pre-emphasis, a Hamming window by default (``--window povey`` for
     the Kaldi default), 512-point FFT, mel filters from 20 Hz to Nyquist,
     no dither, then per-utterance mean subtraction.
  4. Runs the model once per WAV, checks that each output is ONE vector per
     utterance, L2-normalises it and prints the model's I/O signature, the
     embedding dimension and the cosine matrix. Output is text-free: file
     names, durations, frame counts and numbers only - nothing from the
     audio itself.

What the matrix does and does not prove: it is a separation / sanity check.
A clear same-speaker vs other-speaker gap says the export embeds voices
usefully with THIS front-end; a poor gap can expose an incompatible export.
It does NOT prove the front-end matches the model card - some mismatches
(a uniform scale, which per-utterance mean removal cancels; a different
window or frame geometry) only degrade the gap. The bin count is the one
mismatch the script refuses outright. Check the export's preprocessing
recipe (window, frame length / shift, bin count, sample scale, mean
normalisation) against its model card INDEPENDENTLY and record it on Task
0.4 beside the matrix; the ``[decision]`` D-P1 reads both.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any

from scribe_desktop.benchmark import apply_offline_env, assert_offline_env
from scribe_desktop.speaker_eval import WavFormatError, read_wav_pcm

# Kaldi fbank geometry at 16 kHz (WeSpeaker inference: 25 ms / 10 ms, 80 bins).
SAMPLE_RATE = 16_000
FRAME_LENGTH = 400  # 25 ms
FRAME_SHIFT = 160  # 10 ms
FFT_SIZE = 512  # Kaldi rounds the 400-sample window up to the next power of two
MEL_BINS = 80
LOW_FREQ_HZ = 20.0  # Kaldi's default low cut; the high cut is Nyquist
PREEMPHASIS = 0.97
BYTES_PER_SAMPLE = 2
WINDOWS = ("hamming", "povey")


class SpeakerModelError(RuntimeError):
    """The speaker-embedding model is missing, unreadable or the wrong shape."""


# --- front-end (numpy, model-specific; plan D12) ------------------------------


def _mel(hz: Any) -> Any:
    # Kaldi's mel scale (1127 ln(1 + f/700)), not the HTK 2595 log10 form.
    import numpy as np

    return 1127.0 * np.log1p(np.asarray(hz, dtype=np.float64) / 700.0)


def mel_filterbank() -> Any:
    """Kaldi's triangular mel filterbank: ``(MEL_BINS, FFT_SIZE // 2)`` weights
    over the FFT bins below Nyquist (Kaldi drops the Nyquist bin), each
    filter a triangle between three points equally spaced on the mel scale
    from ``LOW_FREQ_HZ`` to Nyquist."""
    import numpy as np

    num_fft_bins = FFT_SIZE // 2
    bin_width_hz = SAMPLE_RATE / FFT_SIZE
    mel_low = float(_mel(LOW_FREQ_HZ))
    mel_high = float(_mel(SAMPLE_RATE / 2.0))
    mel_delta = (mel_high - mel_low) / (MEL_BINS + 1)
    bin_mels = _mel(np.arange(num_fft_bins) * bin_width_hz)  # (num_fft_bins,)
    weights = np.zeros((MEL_BINS, num_fft_bins), dtype=np.float64)
    for band in range(MEL_BINS):
        left = mel_low + band * mel_delta
        center = left + mel_delta
        right = center + mel_delta
        rising = (bin_mels - left) / (center - left)
        falling = (right - bin_mels) / (right - center)
        up = (bin_mels > left) & (bin_mels <= center)
        down = (bin_mels > center) & (bin_mels < right)
        weights[band, up] = rising[up]
        weights[band, down] = falling[down]
    return weights.astype(np.float32)


def filter_center_frequencies_hz() -> Any:
    """Centre frequency of each mel filter in Hz (for reporting and tests)."""
    import numpy as np

    mel_low = float(_mel(LOW_FREQ_HZ))
    mel_high = float(_mel(SAMPLE_RATE / 2.0))
    mel_delta = (mel_high - mel_low) / (MEL_BINS + 1)
    centers_mel = mel_low + mel_delta * (np.arange(MEL_BINS) + 1)
    return 700.0 * (np.exp(centers_mel / 1127.0) - 1.0)


def analysis_window(kind: str) -> Any:
    """Kaldi's ``hamming`` (0.54 - 0.46 cos) or ``povey`` (hann ** 0.85) window
    over ``FRAME_LENGTH`` samples, both with the ``N - 1`` denominator Kaldi uses."""
    import numpy as np

    if kind not in WINDOWS:
        raise ValueError(f"window must be one of {WINDOWS}, got {kind!r}")
    n = np.arange(FRAME_LENGTH, dtype=np.float64)
    angle = 2.0 * math.pi * n / (FRAME_LENGTH - 1)
    if kind == "hamming":
        window = 0.54 - 0.46 * np.cos(angle)
    else:
        window = (0.5 - 0.5 * np.cos(angle)) ** 0.85
    return window.astype(np.float32)


def fbank(pcm16: bytes, *, window: str = "hamming", mean_normalise: bool = True) -> Any:
    """Kaldi-style log-mel fbank of 16 kHz mono PCM16 bytes: ``(frames, MEL_BINS)``
    float32, ``frames = 1 + (samples - 400) // 160`` (snip-edges framing, so a
    tail shorter than one frame is dropped). Samples stay on the int16 scale
    (WeSpeaker feeds ``waveform * 32768``); no dither, so the output is a
    pure function of the input. ``mean_normalise`` subtracts the per-utterance
    mean of every bin (the model's CMN); pass ``False`` to inspect raw energies."""
    import numpy as np

    if len(pcm16) % BYTES_PER_SAMPLE:
        raise ValueError("PCM16 byte count must be even (whole 16-bit samples)")
    samples = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32)
    if samples.size < FRAME_LENGTH:
        raise ValueError(
            f"need at least {FRAME_LENGTH} samples (25 ms) of audio, got {samples.size}"
        )
    frames = 1 + (samples.size - FRAME_LENGTH) // FRAME_SHIFT
    index = np.arange(FRAME_LENGTH)[None, :] + FRAME_SHIFT * np.arange(frames)[:, None]
    x = samples[index]  # (frames, FRAME_LENGTH)
    x = x - x.mean(axis=1, keepdims=True)  # Kaldi remove_dc_offset
    # Kaldi pre-emphasis: x[i] -= k * x[i-1], with x[0] -= k * x[0].
    x = np.concatenate(
        [x[:, :1] - PREEMPHASIS * x[:, :1], x[:, 1:] - PREEMPHASIS * x[:, :-1]], axis=1
    )
    x = x * analysis_window(window)[None, :]
    spectrum = np.abs(np.fft.rfft(x, n=FFT_SIZE, axis=1)) ** 2  # (frames, 257)
    power = spectrum[:, : FFT_SIZE // 2].astype(np.float32)  # Kaldi drops Nyquist
    mel = power @ mel_filterbank().T  # (frames, MEL_BINS)
    log_mel = np.log(np.maximum(mel, np.finfo(np.float32).eps))
    if mean_normalise:
        log_mel = log_mel - log_mel.mean(axis=0, keepdims=True)
    return log_mel.astype(np.float32)


# --- model (the SileroVad load contract) --------------------------------------


def load_session(model_path: Path) -> Any:
    """An onnxruntime session over ``model_path`` under the ``SileroVad``
    contract: offline asserted BEFORE the import (an ``OfflineEnvError`` is
    the one precondition failure that is not a ``SpeakerModelError``), UNC
    refused and the file's presence checked before the import, telemetry
    off, CPU only; from the import onward - a missing or DLL-broken
    onnxruntime, session options, telemetry, session construction - every
    failure is a ``SpeakerModelError`` naming the step (round 6 PR-LOW-020)."""
    assert_offline_env()
    if str(model_path).startswith(("\\\\", "//")):
        raise SpeakerModelError(f"speaker model path must be a local path, not UNC: {model_path}")
    if not model_path.is_file():
        raise SpeakerModelError(
            f"speaker model not found at {model_path} - run scripts/setup-models.py "
            "--only speaker-embedding (the candidate lands as <name>.onnx.candidate)"
        )
    try:
        import onnxruntime
    except Exception as exc:  # ImportError, or a DLL failure surfacing as OSError
        raise SpeakerModelError(
            f"onnxruntime is not importable ({exc}); it is part of the desktop [ml] "
            'extra: .venv\\Scripts\\python.exe -m pip install -e ".\\desktop[dev,ml]"'
        ) from exc
    step = "session options"
    try:
        options = onnxruntime.SessionOptions()
        options.inter_op_num_threads = 1
        options.intra_op_num_threads = 1
        step = "telemetry opt-out"
        onnxruntime.disable_telemetry_events()
        step = "session construction"
        return onnxruntime.InferenceSession(
            str(model_path), sess_options=options, providers=["CPUExecutionProvider"]
        )
    except Exception as exc:
        raise SpeakerModelError(
            f"failed to load speaker model at {model_path} ({step}): {exc}"
        ) from exc


def describe_io(session: Any) -> list[str]:
    lines = []
    for tensor in session.get_inputs():
        lines.append(f"input  {tensor.name}: shape={list(tensor.shape)} type={tensor.type}")
    for tensor in session.get_outputs():
        lines.append(f"output {tensor.name}: shape={list(tensor.shape)} type={tensor.type}")
    return lines


def _utterance_vector(output: Any, name: str) -> Any:
    """The one utterance vector in a model output: ``(dim,)`` or ``(1, dim)``
    (the singleton batch axis stripped). Anything else - a framewise
    ``(1, frames, dim)`` sequence, several vectors, a scalar - is refused as
    an incompatible export rather than flattened into a long "embedding"
    (peer round 6 PR-MED-018)."""
    import numpy as np

    array = np.asarray(output, dtype=np.float32)
    if array.ndim == 2 and array.shape[0] == 1:
        array = array[0]
    if array.ndim != 1:
        raise SpeakerModelError(
            f"model output {name} has shape {list(array.shape)}; a speaker embedding is "
            "ONE vector per utterance, (dim,) or (1, dim) - a framewise or multi-vector "
            "output means this export is not an utterance-level embedder"
        )
    if array.shape[0] < 2:
        raise SpeakerModelError(
            f"model output {name} has {array.shape[0]} element(s); not an embedding"
        )
    return array


def embed(session: Any, features: Any) -> Any:
    """Run one utterance's ``(frames, MEL_BINS)`` features through the model's
    single input (batched when the input is rank 3) and return the FIRST
    output - the rule for a multi-output export is that the utterance
    embedding must be listed first - validated as one vector per utterance
    (``_utterance_vector``) and L2-normalised. A fixed feature dimension
    other than ``MEL_BINS`` is refused up front - that is a front-end
    mismatch, not a model bug."""
    import numpy as np

    inputs = session.get_inputs()
    if len(inputs) != 1:
        raise SpeakerModelError(
            f"expected a single-input model, got {len(inputs)} inputs: "
            f"{[i.name for i in inputs]}"
        )
    spec = inputs[0]
    shape = list(spec.shape)
    if len(shape) not in (2, 3):
        raise SpeakerModelError(f"unsupported input rank {len(shape)} for {spec.name}: {shape}")
    last = shape[-1]
    if isinstance(last, int) and last != MEL_BINS:
        raise SpeakerModelError(
            f"model input {spec.name} expects {last} features per frame; this "
            f"front-end produces {MEL_BINS} (fbank) - wrong candidate or wrong front-end"
        )
    feed = features.astype(np.float32)
    if len(shape) == 3:
        feed = feed[None, :, :]
    outputs = session.get_outputs()
    output_name = outputs[0].name if outputs else "output[0]"
    output = session.run(None, {spec.name: feed})[0]
    vector = _utterance_vector(output, output_name)
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm) or norm == 0.0:
        raise SpeakerModelError("model returned a zero or non-finite embedding")
    return vector / norm


def cosine_matrix(vectors: list[Any]) -> Any:
    """Pairwise cosine similarity of already validated, L2-normalised 1-D
    vectors of one common dimension; anything else is refused (no reshaping
    happens here - ``_utterance_vector`` is the only place a shape is decided)."""
    import numpy as np

    arrays = [np.asarray(v, dtype=np.float32) for v in vectors]
    dims = {a.shape for a in arrays}
    if any(a.ndim != 1 for a in arrays) or len(dims) != 1:
        raise SpeakerModelError(
            f"embeddings must be 1-D vectors of one dimension, got shapes {sorted(dims)}"
        )
    stacked = np.stack(arrays)
    return stacked @ stacked.T


def render_matrix(names: list[str], matrix: Any) -> list[str]:
    width = max([len(name) for name in names] + [6])  # never narrower than a "-0.123" cell
    header = " " * (width + 2) + "  ".join(f"{name:>{width}}" for name in names)
    lines = [header]
    for name, row in zip(names, matrix, strict=True):
        cells = "  ".join(f"{float(value):>{width}.3f}" for value in row)
        lines.append(f"{name:<{width}}  {cells}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--model",
        required=True,
        type=Path,
        help="explicit path to the ONNX model (the .onnx.candidate file or the promoted .onnx)",
    )
    parser.add_argument(
        "--window",
        choices=WINDOWS,
        default="hamming",
        help="analysis window (hamming = WeSpeaker inference default; povey = Kaldi default)",
    )
    parser.add_argument("wavs", nargs="+", type=Path, help="16 kHz mono 16-bit WAV files")
    args = parser.parse_args(argv)

    apply_offline_env()
    assert_offline_env()
    try:
        session = load_session(args.model)
    except SpeakerModelError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Model: {args.model}")
    for line in describe_io(session):
        print(f"  {line}")
    print(f"Front-end: {MEL_BINS}-bin fbank, {args.window} window, per-utterance mean removed")

    names: list[str] = []
    vectors: list[Any] = []
    for wav in args.wavs:
        try:
            pcm = read_wav_pcm(wav)
        except WavFormatError as exc:
            raise SystemExit(str(exc)) from exc
        seconds = len(pcm) / (BYTES_PER_SAMPLE * SAMPLE_RATE)
        try:
            features = fbank(pcm, window=args.window)
            vector = embed(session, features)
        except (ValueError, SpeakerModelError) as exc:
            raise SystemExit(f"{wav.name}: {exc}") from exc
        names.append(wav.name)
        vectors.append(vector)
        print(
            f"  {wav.name}: {seconds:.1f} s, {features.shape[0]} frames x {features.shape[1]}"
            f" -> embedding dim {vector.shape[0]}"
        )

    dims = {int(v.shape[0]) for v in vectors}
    print(f"Embedding dimension: {', '.join(str(d) for d in sorted(dims))}")
    print("Cosine similarity (L2-normalised embeddings):")
    try:
        matrix = cosine_matrix(vectors)
    except SpeakerModelError as exc:
        raise SystemExit(str(exc)) from exc
    for line in render_matrix(names, matrix):
        print(f"  {line}")
    if len(vectors) < 2:
        print("  (one recording: the matrix is trivially 1.000 - add a second WAV to compare)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
