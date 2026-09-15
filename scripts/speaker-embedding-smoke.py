"""Speaker-embedding model smoke (practitioner-profile plan, Phase 0 Task 0.3).

Answers ONE question before anything is built on a speaker-embedding model:
does it place two recordings of the same voice clearly closer together than
a recording of someone else? Run it YOURSELF from a normal terminal (agent
shells cannot see the user's model cache - docs/lessons.md). The shipped
entry is PINNED (practitioner-profile plan Task 0.5), so
``scripts/setup-models.py --only speaker-embedding`` leaves the verified,
promoted model in the cache and the command is:

    .venv\\Scripts\\python.exe scripts\\speaker-embedding-smoke.py ^
        --model "%LOCALAPPDATA%\\ClinikoScribe\\models\\speaker-embedding\\wespeaker-voxceleb-resnet34-LM.onnx" ^
        me-day1.wav me-day2.wav other-person.wav

The model path is EXPLICIT so that an UNPINNED candidate - what a
``--candidate-url`` fetch of a future entry leaves as ``<name>.onnx.candidate``,
not yet promoted - can be read the same way: pass that ``.candidate`` path
instead. (Before the pin, Task 0.4 ran exactly that way.) For the same reason
the smoke does NOT check the file's digest against the shipped pin - the
runtime embedder (``scribe_desktop.speaker_embedding.OnnxSpeakerEmbedder``)
does.

Since Task 1.1 the front-end and the load contract are NOT this script's:
``fbank``, ``load_session`` and ``embed`` below are the runtime module's
``scribe_desktop.speaker_embedding.fbank`` / ``load_onnx_session`` /
``embed_features``, so the D-P1 evidence and the shipped code are the same
code. What it does, in order:
  1. Sets AND asserts the offline kill-switches, then loads the ONNX model
     under the ``SileroVad`` contract - offline asserted BEFORE
     ``onnxruntime`` is imported, a UNC path and a missing file refused
     before it too, telemetry off, CPU provider only; from the import onward
     every failure is a ``SpeakerModelError``.
  2. Reads each WAV (16 kHz mono 16-bit PCM, the ``speaker_eval`` reader;
     anything else is refused with the conversion recipe).
  3. Computes the shipped front-end (plan D12, pinned at D-P1): Kaldi-style
     80-bin log-mel fbank, 25 ms frames every 10 ms, DC removal, 0.97
     pre-emphasis, the POVEY window by default (``--window hamming``
     reproduces the Task 0.4 matrix), 512-point FFT, mel filters from 20 Hz
     to Nyquist, no dither, then per-utterance mean subtraction.
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
mismatch the front-end refuses outright. Check the export's preprocessing
recipe (window, frame length / shift, bin count, sample scale, mean
normalisation) against its model card INDEPENDENTLY and record it on Task
0.4 beside the matrix; the ``[decision]`` D-P1 reads both.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from scribe_desktop.benchmark import apply_offline_env, assert_offline_env
from scribe_desktop.speaker_embedding import (
    BYTES_PER_SAMPLE,
    DEFAULT_WINDOW,
    MEL_BINS,
    SAMPLE_RATE,
    WINDOWS,
    SpeakerModelError,
    embed_features,
    fbank,
    load_onnx_session,
)
from scribe_desktop.speaker_eval import WavFormatError, read_wav_pcm

# Module-level names so ``main`` resolves them at call time (the tests swap
# ``load_session`` for a fake session factory).
load_session = load_onnx_session
embed = embed_features


def describe_io(session: Any) -> list[str]:
    lines = []
    for tensor in session.get_inputs():
        lines.append(f"input  {tensor.name}: shape={list(tensor.shape)} type={tensor.type}")
    for tensor in session.get_outputs():
        lines.append(f"output {tensor.name}: shape={list(tensor.shape)} type={tensor.type}")
    return lines


def cosine_matrix(vectors: list[Any]) -> Any:
    """Pairwise cosine similarity of already validated, L2-normalised 1-D
    vectors of one common dimension; anything else is refused (no reshaping
    happens here - the embedder's output validation is the only place a
    shape is decided)."""
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
        default=DEFAULT_WINDOW,
        help="analysis window (povey = the shipped front-end, WeSpeaker's kaldi.fbank "
        "default; hamming = what the Task 0.4 matrix was run with)",
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
