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

TARGET_SAMPLE_RATE = 16_000
BYTES_PER_SAMPLE = 2  # PCM16


def resample_wav_to_pcm16(
    wav_path: str | Path, sample_rate: int = TARGET_SAMPLE_RATE
) -> bytes:
    """Decode a WAV at ANY rate/layout to mono PCM16 at ``sample_rate``.

    Reads the rate from the container rather than trusting what the writer was
    asked for — the whole point of this module.
    """
    import av
    from av.audio.resampler import AudioResampler

    resampler = AudioResampler(format="s16", layout="mono", rate=sample_rate)
    pcm = bytearray()
    with av.open(str(wav_path)) as container:
        for frame in container.decode(container.streams.audio[0]):
            for resampled in resampler.resample(frame):
                pcm += resampled.to_ndarray().tobytes()
    for resampled in resampler.resample(None):  # flush the resampler's tail
        pcm += resampled.to_ndarray().tobytes()
    return bytes(pcm)


def synthesize_speech_wav(text: str, target: str | Path) -> None:
    """Speak ``text`` through SAPI into ``target`` at WHATEVER rate SAPI picks.

    Split out from ``synthesize_speech_pcm`` so a test can inspect the raw file
    and pin the platform behaviour this module exists to correct.
    """
    import win32com.client

    stream = win32com.client.Dispatch("SAPI.SpFileStream")
    # Requested, not honoured here (see module docstring) — kept because it
    # costs nothing and voices that DO honour it then need no resampling.
    stream.Format.Type = 22  # SAFT16kHz16BitMono
    stream.Open(str(target), 3)  # 3 = SSFMCreateForWrite
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
