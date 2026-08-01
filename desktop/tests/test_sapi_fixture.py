"""Tests for the shared SAPI speech fixture (`sapi_fixture`).

This helper exists because SAPI writes 22050 Hz whatever format it is asked
for, and every live VAD/Whisper test in the suite used to hand those frames on
as if they were 16 kHz — i.e. 0.726x speed, pitch dropped to match. The bug was
invisible precisely because nothing asserted the fixture's rate, so these tests
pin it:

- the resampler is exercised on a SYNTHETIC 22050 Hz WAV (no SAPI, no ML
  model), so duration and pitch preservation are checked wherever `av` exists;
- a SAPI-gated test compares the synthesized file's own header against what the
  helper returns, which is the check that would have caught the original bug.

No clinical audio: a generated tone and one non-clinical sentence.
"""

from __future__ import annotations

import math
import struct
import sys
import wave
from pathlib import Path

import pytest

from sapi_fixture import (
    BYTES_PER_SAMPLE,
    TARGET_SAMPLE_RATE,
    resample_wav_to_pcm16,
    synthesize_speech_pcm,
    synthesize_speech_wav,
)

SOURCE_RATE = 22_050  # what SAPI actually renders on the dev machine
TONE_HZ = 440.0
TONE_SECONDS = 2.0


def write_tone_wav(path: Path, rate: int, seconds: float, frequency: float) -> None:
    count = int(seconds * rate)
    samples = struct.pack(
        f"<{count}h",
        *(
            int(0.5 * 32767 * math.sin(2 * math.pi * frequency * i / rate))
            for i in range(count)
        ),
    )
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(BYTES_PER_SAMPLE)
        wav.setframerate(rate)
        wav.writeframes(samples)


def dominant_frequency(pcm: bytes, rate: int) -> float:
    import numpy as np

    signal = np.frombuffer(pcm, dtype="<i2").astype(np.float64)
    spectrum = np.abs(np.fft.rfft(signal * np.hanning(len(signal))))
    return float(np.argmax(spectrum)) * rate / len(signal)


class TestResampleWavToPcm16:
    def test_duration_is_preserved_from_the_files_own_rate(self, tmp_path: Path) -> None:
        pytest.importorskip("av")
        source = tmp_path / "tone.wav"
        write_tone_wav(source, SOURCE_RATE, TONE_SECONDS, TONE_HZ)

        pcm = resample_wav_to_pcm16(source)

        seconds = len(pcm) / (BYTES_PER_SAMPLE * TARGET_SAMPLE_RATE)
        assert seconds == pytest.approx(TONE_SECONDS, abs=0.01)
        # The bug this pins: reading the frames straight out of the 22050 Hz
        # file and calling them 16 kHz stretches them by 22050/16000.
        with wave.open(str(source), "rb") as wav:
            raw = wav.readframes(wav.getnframes())
        naive_seconds = len(raw) / (BYTES_PER_SAMPLE * TARGET_SAMPLE_RATE)
        stretched = TONE_SECONDS * SOURCE_RATE / TARGET_SAMPLE_RATE
        assert naive_seconds == pytest.approx(stretched, abs=0.01)

    def test_pitch_is_preserved(self, tmp_path: Path) -> None:
        pytest.importorskip("av")
        pytest.importorskip("numpy")
        source = tmp_path / "tone.wav"
        write_tone_wav(source, SOURCE_RATE, TONE_SECONDS, TONE_HZ)

        pcm = resample_wav_to_pcm16(source)

        # Resampled: still 440 Hz. Reinterpreted: 440 * 16000/22050 = 319 Hz.
        assert dominant_frequency(pcm, TARGET_SAMPLE_RATE) == pytest.approx(TONE_HZ, abs=5.0)

    def test_already_16k_audio_passes_through_unchanged_in_duration(
        self, tmp_path: Path
    ) -> None:
        pytest.importorskip("av")
        source = tmp_path / "tone16k.wav"
        write_tone_wav(source, TARGET_SAMPLE_RATE, 1.0, TONE_HZ)

        pcm = resample_wav_to_pcm16(source)

        assert len(pcm) / (BYTES_PER_SAMPLE * TARGET_SAMPLE_RATE) == pytest.approx(1.0, abs=0.01)


@pytest.mark.skipif(sys.platform != "win32", reason="SAPI is Windows-only")
class TestSynthesizeSpeechPcm:
    def test_returned_pcm_matches_the_wav_files_true_duration(self, tmp_path: Path) -> None:
        """The check that would have caught the original bug: the helper's
        output, read as 16 kHz, must last exactly as long as the file SAPI
        wrote — whatever rate SAPI chose for it."""
        pytest.importorskip("av")
        text = "The lighthouse keeper counted eleven boats returning with the tide."
        source = tmp_path / "speech.wav"
        synthesize_speech_wav(text, source)
        with wave.open(str(source), "rb") as wav:
            true_seconds = wav.getnframes() / wav.getframerate()
            source_rate = wav.getframerate()

        pcm = resample_wav_to_pcm16(source)

        seconds = len(pcm) / (BYTES_PER_SAMPLE * TARGET_SAMPLE_RATE)
        assert seconds == pytest.approx(true_seconds, abs=0.01)
        if source_rate != TARGET_SAMPLE_RATE:
            # Recorded, not required: on the dev machine SAPI ignores the
            # requested 16 kHz. If a voice ever honours it this simply passes.
            assert len(pcm) != source.stat().st_size

    def test_synthesize_speech_pcm_produces_plausible_16k_speech(self) -> None:
        pytest.importorskip("av")
        pcm = synthesize_speech_pcm("A short reset check sentence.")

        assert len(pcm) % BYTES_PER_SAMPLE == 0
        seconds = len(pcm) / (BYTES_PER_SAMPLE * TARGET_SAMPLE_RATE)
        # Five words at any sane speaking rate; the pre-fix path reported this
        # sentence ~38% longer than it really was.
        assert 0.8 < seconds < 4.0
        assert any(pcm), "synthesized speech is all silence"
