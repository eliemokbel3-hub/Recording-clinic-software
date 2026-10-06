"""Shared SAPI speech fixture: TRUE 16 kHz mono PCM16 for the live tests.

Why this module exists (measured on the dev machine 2026-07-30, re-verified
2026-07-31): SAPI ignores the format requested on ``SPFileStream``. The
OneCore default voice overrides it when the stream is assigned to
``SpVoice.AudioOutputStream``, so the file lands at 22050 Hz even though
``stream.Format.Type`` still READS back 22 (SAFT16kHz16BitMono);
``AllowAudioOutputFormatChangesOnNextSet = False`` plus a Format write-back
does not prevent it either. Handing those raw frames onward as if they were
16 kHz PCM plays them at 0.726x speed and drops the pitch to match, so the
live VAD/Whisper tests were exercising slowed, pitch-shifted speech.

The correction is to read the file's REAL rate and resample, which is what
``synthesize_speech_pcm`` does — via PyAV's swresample, the same resampler
faster-whisper uses when it decodes audio itself, so fixture audio reaches the
models the way production 16 kHz capture does. Every SAPI fixture in the suite
routes through here so the correction lives in exactly one place.

``av`` arrives with faster-whisper (the ``[ml]`` extra), and every caller is
already gated on the local ML stack being present.

Windows-only (SAPI COM). No clinical audio: callers pass non-clinical text.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

# Pilot plan Task 2.5 moved the resampler into ``src`` (the validation-set
# builder needs it); the fixture re-imports it so the correction still lives
# in exactly one place.
from scribe_desktop.validation_set import (
    SAPI_16K_MONO,
    SAPI_CREATE_FOR_WRITE,
    TARGET_SAMPLE_RATE,
    resample_wav_to_pcm16,
)

BYTES_PER_SAMPLE = 2  # PCM16

__all__ = [
    "BYTES_PER_SAMPLE",
    "TARGET_SAMPLE_RATE",
    "resample_wav_to_pcm16",
    "synthesize_speech_pcm",
    "synthesize_speech_wav",
]


def synthesize_speech_wav(text: str, target: str | Path) -> None:
    """Speak ``text`` through SAPI into ``target`` at WHATEVER rate SAPI picks.

    Split out from ``synthesize_speech_pcm`` so a test can inspect the raw file
    and pin the platform behaviour this module exists to correct.
    """
    import win32com.client

    stream = win32com.client.Dispatch("SAPI.SpFileStream")
    # Requested, not honoured here (see module docstring) — kept because it
    # costs nothing and voices that DO honour it then need no resampling.
    stream.Format.Type = SAPI_16K_MONO
    stream.Open(str(target), SAPI_CREATE_FOR_WRITE)
    voice = win32com.client.Dispatch("SAPI.SpVoice")
    voice.AudioOutputStream = stream
    voice.Speak(text)
    stream.Close()


def synthesize_speech_pcm(text: str, sample_rate: int = TARGET_SAMPLE_RATE) -> bytes:
    """Speak ``text`` through SAPI; return TRUE ``sample_rate`` mono PCM16."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sapi_fixture.wav"
        synthesize_speech_wav(text, path)
        return resample_wav_to_pcm16(path, sample_rate)
