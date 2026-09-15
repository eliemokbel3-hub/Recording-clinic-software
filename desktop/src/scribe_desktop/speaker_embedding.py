"""Speaker embeddings for voice enrolment (practitioner-profile plan, Phase 1).

ONE front-end and ONE load contract (plan Task 1.1): the numpy Kaldi-style
fbank front-end the D-P1 smoke was run with lives here, and
``scripts/speaker-embedding-smoke.py`` imports it, so the shipped code and the
D-P1 evidence are the same code. The model-specific constants the runtime
needs (name, cache subdirectory, pinned size and SHA-256) are defined here
once; ``scripts/setup-models.py`` imports them, never a second literal.

Two embedders behind one protocol (plan Design Decision D16):

- ``OnnxSpeakerEmbedder`` — the pinned WeSpeaker VoxCeleb ResNet34-LM ONNX
  export (input ``feats`` ``[B, T, 80]`` float, output ``embs`` ``[B, 256]``),
  loaded under the ``SileroVad`` contract: the offline kill-switches asserted
  BEFORE ``onnxruntime`` is imported, a UNC path and a missing file refused
  before the import too, the file's SHA-256 checked against the pin before
  the import (a shape-compatible substitute cannot pass as the pinned model,
  round 1 PR-MED-003), telemetry off, CPU only, the I/O signature probed and
  one smoke inference run at construction so an incompatible export fails
  here as ``SpeakerModelError`` — never on the first consultation segment.
- ``SpectralSpeakerEmbedder`` — the pipeline's existing CMN'd mel embedding
  (``transcription._segment_embedding``) wrapped; no file, always available.

``SHIPPED_SPEAKER_EMBEDDER`` records the D-P1 choice (2026-09-15: the onnx
embedder) and ``ATTRIBUTION_THRESHOLD`` the practitioner's cosine threshold
(0.50); ``build_speaker_embedder`` / ``speaker_embedder_available`` key on the
selected kind. ``MockSpeakerEmbedder`` is the deterministic test double.

Front-end (plan D12, pinned at D-P1): 80-bin Kaldi fbank over 16 kHz mono
PCM16 kept on the int16 scale, 25 ms frames every 10 ms (snip-edges), DC
removal, 0.97 pre-emphasis, the POVEY window (WeSpeaker's ``kaldi.fbank``
default — the Task 0.4 smoke used Hamming; the module pins Povey and the smoke
keeps ``--window`` for comparison), 512-point FFT without the Nyquist bin,
mel filters from 20 Hz to Nyquist, no dither, float32-eps log floor, then
per-utterance mean subtraction. No dither means every function here is a pure
function of its input.

Constraints honoured: numpy and onnxruntime are imported lazily inside
functions (the module imports without the ``[ml]`` extra, like ``speech.py``);
the offline kill-switches are asserted before EVERY ML import; nothing in this
module logs, and neither embedder keeps a reference to the PCM it was given
(the test double holds only the lookup map its caller supplied — see its
docstring).
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final, Literal, Protocol

from scribe_desktop.benchmark import assert_offline_env, default_models_root

# --- the pinned model (single source; scripts/setup-models.py imports these) ---

SPEAKER_MODEL_NAME: Final = "wespeaker-voxceleb-resnet34-LM"
SPEAKER_MODEL_SUBDIR: Final = "speaker-embedding"
# Trust-on-first-download pin, recorded 2026-09-15 from the practitioner's
# Task 0.4 fetch and confirmed by the D-P1 smoke (practitioner-profile plan
# Task 0.5). The digest is what pins the bytes, exactly as for silero-vad.
SPEAKER_MODEL_SIZE_BYTES: Final = 26_530_309
SPEAKER_MODEL_SHA256: Final = (
    "7bb2f06e9df17cdf1ef14ee8a15ab08ed28e8d0ef5054ee135741560df2ec068"
)
# The identity a profile records (D16: a profile is usable only with the
# embedder that produced it). Naming the export, not the file.
ONNX_MODEL_ID: Final = SPEAKER_MODEL_NAME
SPECTRAL_MODEL_ID: Final = "spectral-cmn-v1"
MOCK_MODEL_ID: Final = "mock-speaker-embedder-v1"

EmbedderKind = Literal["onnx", "spectral"]
# D-P1 (practitioner, 2026-09-15): candidate 1, the onnx embedder, ships.
SHIPPED_SPEAKER_EMBEDDER: Final[EmbedderKind] = "onnx"
# D-P1: cosine similarity at or above this against the enrolled vector
# attributes a segment to the practitioner (raw cosine in [-1, 1], never a
# 0-1 clamp — plan D3). Stricter than the 0.44 midpoint by the practitioner's
# choice (fewer false matches over recall); re-checked in Phase 6.
ATTRIBUTION_THRESHOLD: Final = 0.50

# --- Kaldi fbank geometry at 16 kHz (WeSpeaker inference: 25 ms / 10 ms, 80 bins)

SAMPLE_RATE: Final = 16_000
FRAME_LENGTH: Final = 400  # 25 ms
FRAME_SHIFT: Final = 160  # 10 ms
FFT_SIZE: Final = 512  # Kaldi rounds the 400-sample window up to the next power of two
MEL_BINS: Final = 80
LOW_FREQ_HZ: Final = 20.0  # Kaldi's default low cut; the high cut is Nyquist
PREEMPHASIS: Final = 0.97
BYTES_PER_SAMPLE: Final = 2
WINDOWS: Final = ("povey", "hamming")
DEFAULT_WINDOW: Final = "povey"  # pinned at D-P1 (WeSpeaker's kaldi.fbank default)

# Smoke inference at load: one second of a deterministic 440 Hz tone at a
# moderate int16 amplitude (98 frames) — enough to exercise the batch/time/
# feature axes and the output layout without taking noticeable time on the
# 26 MB ResNet. NOT digital silence: silence is degenerate through the
# front-end (a constant fbank, all zero after CMN), and a model's response
# to an all-zero input is exactly the kind of edge that could read as a
# zero or non-finite vector and fail every construction (review round 12
# MED-001). A tone is an ordinary, non-degenerate input.
_SMOKE_TONE_HZ: Final = 440.0
_SMOKE_AMPLITUDE: Final = 8000


def _smoke_pcm() -> bytes:
    np = _numpy()
    t = np.arange(SAMPLE_RATE, dtype=np.float64) / SAMPLE_RATE
    tone = _SMOKE_AMPLITUDE * np.sin(2.0 * math.pi * _SMOKE_TONE_HZ * t)
    return bytes(tone.astype(np.int16).tobytes())


class SpeakerModelError(RuntimeError):
    """The speaker-embedding model is missing, unreadable, not the pinned
    bytes, the wrong shape, or produced an unusable embedding."""


def _numpy() -> Any:
    # Offline env asserted before EVERY ML-stack import (the transcription
    # module's binding pattern, PR round 15).
    assert_offline_env()
    import numpy

    return numpy


# --- front-end (numpy, model-specific; plan D12) ------------------------------


def _mel(hz: Any) -> Any:
    # Kaldi's mel scale (1127 ln(1 + f/700)), not the HTK 2595 log10 form.
    np = _numpy()
    return 1127.0 * np.log1p(np.asarray(hz, dtype=np.float64) / 700.0)


_filterbank_cache: Any = None
_window_cache: dict[str, Any] = {}


def mel_filterbank() -> Any:
    """Kaldi's triangular mel filterbank: ``(MEL_BINS, FFT_SIZE // 2)`` float32
    weights over the FFT bins below Nyquist (Kaldi drops the Nyquist bin),
    each filter a triangle between three points equally spaced on the mel
    scale from ``LOW_FREQ_HZ`` to Nyquist. Computed once and returned as a
    READ-ONLY array (the per-segment path calls this for every segment)."""
    global _filterbank_cache
    if _filterbank_cache is not None:
        return _filterbank_cache
    np = _numpy()
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
    result = weights.astype(np.float32)
    result.setflags(write=False)
    _filterbank_cache = result
    return result


def filter_center_frequencies_hz() -> Any:
    """Centre frequency of each mel filter in Hz (for reporting and tests)."""
    np = _numpy()
    mel_low = float(_mel(LOW_FREQ_HZ))
    mel_high = float(_mel(SAMPLE_RATE / 2.0))
    mel_delta = (mel_high - mel_low) / (MEL_BINS + 1)
    centers_mel = mel_low + mel_delta * (np.arange(MEL_BINS) + 1)
    return 700.0 * (np.exp(centers_mel / 1127.0) - 1.0)


def analysis_window(kind: str) -> Any:
    """Kaldi's ``povey`` (hann ** 0.85) or ``hamming`` (0.54 - 0.46 cos) window
    over ``FRAME_LENGTH`` samples, both with the ``N - 1`` denominator Kaldi
    uses. Cached per kind and returned READ-ONLY."""
    if kind not in WINDOWS:
        raise ValueError(f"window must be one of {WINDOWS}, got {kind!r}")
    cached = _window_cache.get(kind)
    if cached is not None:
        return cached
    np = _numpy()
    n = np.arange(FRAME_LENGTH, dtype=np.float64)
    angle = 2.0 * math.pi * n / (FRAME_LENGTH - 1)
    if kind == "hamming":
        window = 0.54 - 0.46 * np.cos(angle)
    else:
        window = (0.5 - 0.5 * np.cos(angle)) ** 0.85
    result = window.astype(np.float32)
    result.setflags(write=False)
    _window_cache[kind] = result
    return result


def fbank(pcm16: bytes, *, window: str = DEFAULT_WINDOW, mean_normalise: bool = True) -> Any:
    """Kaldi-style log-mel fbank of 16 kHz mono PCM16 bytes: ``(frames, MEL_BINS)``
    float32, ``frames = 1 + (samples - 400) // 160`` (snip-edges framing, so a
    tail shorter than one frame is dropped). Samples stay on the int16 scale
    (WeSpeaker feeds ``waveform * 32768``); no dither, so the output is a
    pure function of the input. ``mean_normalise`` subtracts the per-utterance
    mean of every bin (the model's CMN); pass ``False`` to inspect raw
    energies. The default window is the D-P1 pin (Povey)."""
    np = _numpy()
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


# --- the load contract (SileroVad's, plus the digest pin) ---------------------


def default_speaker_model_path() -> Path:
    return default_models_root() / SPEAKER_MODEL_SUBDIR / f"{SPEAKER_MODEL_NAME}.onnx"


def _is_unc(path: Path) -> bool:
    return str(path).startswith(("\\\\", "//"))


def speaker_model_available(model_path: Path | None = None) -> bool:
    """True when the pinned model FILE exists — a STAT-only probe (mirrors
    ``speech.vad_model_available``): a UNC-redirected ``LOCALAPPDATA`` must
    cause zero SMB I/O, so UNC paths are refused BEFORE any filesystem touch
    and report unavailable. Presence only — the digest is verified by
    ``OnnxSpeakerEmbedder`` at load, not here."""
    try:
        path = model_path if model_path is not None else default_speaker_model_path()
    except (RuntimeError, OSError):
        return False
    if _is_unc(path):
        return False
    return path.is_file()


def sha256_of_file(path: Path) -> str:
    """Streamed SHA-256 of the file's bytes (the model is ~25 MiB)."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_onnx_session(model_path: Path, *, expected_sha256: str | None = None) -> Any:
    """An onnxruntime session over ``model_path`` under the ``SileroVad``
    contract: offline asserted BEFORE the import (an ``OfflineEnvError`` is
    the one precondition failure that is not a ``SpeakerModelError``), UNC
    refused and the file's presence checked before the import, the file's
    SHA-256 checked against ``expected_sha256`` when one is given (also
    before the import — a mismatch names both digests), telemetry off, CPU
    only; from the import onward — a missing or DLL-broken onnxruntime,
    session options, telemetry, session construction — every failure is a
    ``SpeakerModelError`` naming the step (round 6 PR-LOW-020)."""
    assert_offline_env()
    if _is_unc(model_path):
        raise SpeakerModelError(f"speaker model path must be a local path, not UNC: {model_path}")
    if not model_path.is_file():
        raise SpeakerModelError(
            f"speaker model not found at {model_path} - run scripts/setup-models.py "
            "--only speaker-embedding (the pinned entry is written or promoted as "
            "<name>.onnx; an unpinned candidate fetch leaves <name>.onnx.candidate)"
        )
    if expected_sha256 is not None:
        try:
            actual = sha256_of_file(model_path)
        except OSError as exc:
            raise SpeakerModelError(
                f"speaker model at {model_path} is unreadable: {exc}"
            ) from exc
        if actual != expected_sha256:
            raise SpeakerModelError(
                f"speaker model at {model_path} is not the pinned model: expected SHA-256 "
                f"{expected_sha256}, got {actual} - re-run scripts/setup-models.py "
                "--only speaker-embedding"
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


def _utterance_vector(output: Any, name: str) -> Any:
    """The one utterance vector in a model output: ``(dim,)`` or ``(1, dim)``
    (the singleton batch axis stripped). Anything else - a framewise
    ``(1, frames, dim)`` sequence, several vectors, a scalar - is refused as
    an incompatible export rather than flattened into a long "embedding"
    (peer round 6 PR-MED-018)."""
    np = _numpy()
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


def _l2_normalised(vector: Any, np: Any) -> Any:
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm) or norm == 0.0:
        raise SpeakerModelError("model returned a zero or non-finite embedding")
    return (vector / norm).astype(np.float32)


def embed_features(session: Any, features: Any) -> Any:
    """Run one utterance's ``(frames, MEL_BINS)`` features through the model's
    single input (batched when the input is rank 3) and return the FIRST
    output - the rule for a multi-output export is that the utterance
    embedding must be listed first - validated as one vector per utterance
    (``_utterance_vector``) and L2-normalised. A fixed feature dimension
    other than ``MEL_BINS`` is refused up front - that is a front-end
    mismatch, not a model bug."""
    np = _numpy()
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
    return _l2_normalised(_utterance_vector(output, output_name), np)


# --- the embedders (D16) --------------------------------------------------------


class SpeakerEmbedder(Protocol):
    """One utterance of 16 kHz mono PCM16 -> one L2-normalised float32 vector.

    ``model_id`` names the embedder that produced a vector (a profile is
    usable only with the same id, D16); ``model_sha256`` is the verified
    digest of the model file (empty for the file-less embedders);
    ``embedding_dim`` is the vector length every ``embed`` call returns.
    ``embed`` accepts any PCM of at least ``FRAME_LENGTH`` samples (one 25 ms
    front-end frame); a shorter input MAY be refused with ``ValueError``, so
    the pipeline does not ask (``transcription.MIN_ATTRIBUTION_PCM_BYTES``).
    """

    @property
    def model_id(self) -> str: ...

    @property
    def model_sha256(self) -> str: ...

    @property
    def embedding_dim(self) -> int: ...

    def embed(self, pcm16: bytes) -> Any: ...


class OnnxSpeakerEmbedder:
    """The pinned ONNX speaker model (module docstring: the load contract).

    Construction is the whole load contract: offline asserted before the
    import, UNC/missing refused, the file's SHA-256 checked against
    ``SPEAKER_MODEL_SHA256`` (``model_sha256`` is that computed digest, taken
    once from the bytes at construction), the I/O signature probed (one
    input of rank 2 or 3 whose fixed feature axis is ``MEL_BINS``; at least
    one output) and one smoke inference run whose result must be one finite
    vector per utterance — so ``embedding_dim`` is KNOWN, not declared, and a
    shape-incompatible export dies here as ``SpeakerModelError``.
    """

    def __init__(self, model_path: Path | None = None) -> None:
        assert_offline_env()
        path = model_path if model_path is not None else default_speaker_model_path()
        self._path = path
        self._session = load_onnx_session(path, expected_sha256=SPEAKER_MODEL_SHA256)
        self._sha256 = SPEAKER_MODEL_SHA256
        try:
            smoke = embed_features(self._session, fbank(_smoke_pcm()))
        except SpeakerModelError:
            raise
        except Exception as exc:
            raise SpeakerModelError(
                f"speaker model at {path} failed smoke inference: {exc}"
            ) from exc
        self._dim = int(smoke.shape[0])

    @property
    def model_path(self) -> Path:
        return self._path

    @property
    def model_id(self) -> str:
        return ONNX_MODEL_ID

    @property
    def model_sha256(self) -> str:
        return self._sha256

    @property
    def embedding_dim(self) -> int:
        return self._dim

    def embed(self, pcm16: bytes) -> Any:
        """Front-end (Povey, CMN) -> model -> one L2-normalised vector.
        ``ValueError`` for PCM shorter than one 25 ms frame or an odd byte
        count; ``SpeakerModelError`` for an unusable model output."""
        vector = embed_features(self._session, fbank(pcm16))
        if int(vector.shape[0]) != self._dim:
            raise SpeakerModelError(
                f"speaker model returned a {int(vector.shape[0])}-dim vector; "
                f"{self._dim} at load"
            )
        return vector


class SpectralSpeakerEmbedder:
    """The pipeline's own CMN'd 24-mel + low-band-centroid embedding
    (``transcription._segment_embedding``), L2-normalised; no file, always
    available (D16). Kept for tests, the harness and the measured comparison
    — never substituted for the onnx embedder silently (round 1 PR-MED-005)."""

    _DIM: Final = 25  # 24 mel bands + the low-band centroid

    @property
    def model_id(self) -> str:
        return SPECTRAL_MODEL_ID

    @property
    def model_sha256(self) -> str:
        return ""

    @property
    def embedding_dim(self) -> int:
        return self._DIM

    def embed(self, pcm16: bytes) -> Any:
        if len(pcm16) % BYTES_PER_SAMPLE:
            raise ValueError("PCM16 byte count must be even (whole 16-bit samples)")
        if not pcm16:
            raise ValueError("cannot embed empty PCM")
        # Deferred import: transcription.py will import THIS module for the
        # protocol type in Phase 2, so the dependency must not be circular at
        # import time.
        from scribe_desktop.transcription import _segment_embedding

        np = _numpy()
        return _l2_normalised(_segment_embedding(pcm16, np), np)


class MockSpeakerEmbedder:
    """Deterministic, ML-free test double.

    ``vectors`` maps EXACT PCM byte strings to the vector to return (any
    length ``embedding_dim``, L2-normalised on the way out); PCM absent from
    the map embeds to a vector derived from its SHA-256, so the same bytes
    always give the same vector and different bytes (almost surely) differ.
    What it holds: the caller's map (whose KEYS are PCM the test itself
    supplied, kept for lookup) and the LENGTH of each PCM it embedded
    (``embedded_lengths``). It never stores the bytes it is asked to embed,
    so a test asserting "no PCM retained" over the code under test is not
    undermined by its own double.
    """

    def __init__(
        self,
        vectors: Mapping[bytes, Sequence[float]] | None = None,
        *,
        embedding_dim: int = 4,
    ) -> None:
        if embedding_dim < 2:
            raise ValueError("embedding_dim must be at least 2")
        self._dim = embedding_dim
        self._vectors: dict[bytes, tuple[float, ...]] = {
            key: tuple(float(v) for v in value) for key, value in (vectors or {}).items()
        }
        for key, value in self._vectors.items():
            if len(value) != embedding_dim:
                raise ValueError(
                    f"mapped vector for a {len(key)}-byte input has {len(value)} "
                    f"elements; embedding_dim is {embedding_dim}"
                )
        self.embedded_lengths: list[int] = []

    @property
    def model_id(self) -> str:
        return MOCK_MODEL_ID

    @property
    def model_sha256(self) -> str:
        return ""

    @property
    def embedding_dim(self) -> int:
        return self._dim

    def embed(self, pcm16: bytes) -> Any:
        np = _numpy()
        self.embedded_lengths.append(len(pcm16))
        mapped = self._vectors.get(pcm16)
        if mapped is not None:
            return _l2_normalised(np.asarray(mapped, dtype=np.float32), np)
        digest = hashlib.sha256(pcm16).digest()
        raw = [((digest[i % len(digest)] / 255.0) * 2.0 - 1.0) for i in range(self._dim)]
        return _l2_normalised(np.asarray(raw, dtype=np.float32), np)


def shipped_embedder_identity(kind: EmbedderKind = SHIPPED_SPEAKER_EMBEDDER) -> tuple[str, str]:
    """``(model_id, model_sha256)`` the selected embedder reports once built —
    known WITHOUT loading it: the onnx embedder refuses to load unless the
    file digests to ``SPEAKER_MODEL_SHA256``, so that pin IS its verified
    digest, and spectral has no file. Lets the composition layer and the
    Transcript screen's status line decide whether a stored profile matches
    the shipped embedder (D3 / D16) off the worker thread, from a stat and a
    profile read, before any model is constructed."""
    if kind == "spectral":
        return SPECTRAL_MODEL_ID, ""
    return ONNX_MODEL_ID, SPEAKER_MODEL_SHA256


def speaker_embedder_available(kind: EmbedderKind = SHIPPED_SPEAKER_EMBEDDER) -> bool:
    """Whether the SELECTED embedder can be built: spectral always; onnx iff
    the pinned model file is present (a STAT-only, UNC-safe probe — the
    digest is checked at load, D16)."""
    if kind == "spectral":
        return True
    return speaker_model_available()


def build_speaker_embedder(kind: EmbedderKind = SHIPPED_SPEAKER_EMBEDDER) -> SpeakerEmbedder:
    """The selected embedder (D16). For ``"onnx"`` this IS the load contract
    and raises ``SpeakerModelError`` (or ``OfflineEnvError``) — callers that
    want the visible D2 fallback check ``speaker_embedder_available`` first
    and report; spectral is never substituted here."""
    if kind == "spectral":
        return SpectralSpeakerEmbedder()
    return OnnxSpeakerEmbedder()


__all__ = [
    "ATTRIBUTION_THRESHOLD",
    "BYTES_PER_SAMPLE",
    "DEFAULT_WINDOW",
    "FFT_SIZE",
    "FRAME_LENGTH",
    "FRAME_SHIFT",
    "LOW_FREQ_HZ",
    "MEL_BINS",
    "MOCK_MODEL_ID",
    "ONNX_MODEL_ID",
    "PREEMPHASIS",
    "SAMPLE_RATE",
    "SHIPPED_SPEAKER_EMBEDDER",
    "SPEAKER_MODEL_NAME",
    "SPEAKER_MODEL_SHA256",
    "SPEAKER_MODEL_SIZE_BYTES",
    "SPEAKER_MODEL_SUBDIR",
    "SPECTRAL_MODEL_ID",
    "WINDOWS",
    "EmbedderKind",
    "MockSpeakerEmbedder",
    "OnnxSpeakerEmbedder",
    "SpeakerEmbedder",
    "SpeakerModelError",
    "SpectralSpeakerEmbedder",
    "analysis_window",
    "build_speaker_embedder",
    "default_speaker_model_path",
    "embed_features",
    "fbank",
    "filter_center_frequencies_hz",
    "load_onnx_session",
    "mel_filterbank",
    "sha256_of_file",
    "shipped_embedder_identity",
    "speaker_embedder_available",
    "speaker_model_available",
]
