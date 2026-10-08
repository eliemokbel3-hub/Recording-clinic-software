"""Shared ML-free speaker fakes (``test_speaker_eval.py`` and the
kept-recordings replay tool's ``test_replay_kept.py``, development-recordings
review round 29 LOW-015): no model file, no clinical audio — tones only."""

from __future__ import annotations

import struct

from scribe_desktop.speech import SAMPLE_RATE


class FrequencyEmbedder:
    """An ML-free ``SpeakerEmbedder`` for the enrolled condition: the unit
    vector e1 for a low-pitched tone (zero-crossing rate under 1000/s), e2
    otherwise — so a 220 Hz voice matches an e1 profile and a 2600 Hz voice
    does not, deterministically, with no model file."""

    @property
    def model_id(self) -> str:
        return "mock-frequency-v1"

    @property
    def model_sha256(self) -> str:
        return ""

    @property
    def embedding_dim(self) -> int:
        return 2

    def embed(self, pcm16: bytes) -> object:
        import numpy as np

        samples = struct.unpack(f"<{len(pcm16) // 2}h", pcm16)
        pairs = zip(samples, samples[1:], strict=False)
        crossings = sum(1 for a, b in pairs if (a < 0) != (b < 0))
        rate = crossings / (len(samples) / SAMPLE_RATE)
        return np.asarray([1.0, 0.0] if rate < 1000 else [0.0, 1.0], dtype=np.float32)
