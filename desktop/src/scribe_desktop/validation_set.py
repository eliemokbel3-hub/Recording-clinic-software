"""Pilot plan Task 2.5: the synthetic validation-set builder (developer
build only).

Turns each synthetic encounter script (``validation.EncounterScript`` with
``conditions``) into the set-folder triple the harness reads: ``<id>.wav``
(16 kHz mono PCM16, the ``speaker_eval.read_wav_pcm`` contract), ``<id>.txt``
(the Audacity label track, one span per turn, labelled with its role) and a
byte-exact copy of ``<id>.json``.

The steps, each a pure function tested on generated tones:

1. **Voices.** The installed Windows voices are enumerated
   (``sapi_voices``) and a script's ``voice_slots`` index them, one distinct
   voice per role; fewer than two installed voices is refused by name.
2. **Synthesis.** Each line is spoken by its role's voice at the script's
   rate (``sapi_synthesize``) and resampled to TRUE 16 kHz
   (``resample_wav_to_pcm16`` — moved here from the test fixture, which
   re-imports it: SAPI writes 22050 Hz whatever it is asked for).
3. **Level.** Every turn is scaled to one RMS level (``TURN_RMS``), so no
   voice is louder than another.
4. **Placement.** Turns follow each other after ``GAP_SECONDS``; a line in
   ``overlap_lines`` starts ``overlap_seconds`` before the previous line
   ends (never before it starts). The label track is written from these
   FINAL sample offsets and the resampled turn lengths, so every span
   matches its turn to the sample after rate and overlap changes.
5. **Noise.** Gaussian noise from a seed fixed per encounter (its id's
   SHA-256) is scaled to the script's signal-to-noise ratio — speech power
   over the samples where a turn is active, against the noise's power over
   the same samples — and added across the whole recording.
6. **Peak.** The mix is scaled down only if it would clip, which keeps the
   ratio.

No real voice runs in the test suite: the voice list and the synthesizer
are injected (``build_set``), tested with zero, one and two voices. The
scripts are invented; nothing here reads a real consultation, and the
module logs nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import math
import os
import random
import re
import sys
import tempfile
from array import array
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from scribe_desktop import install_layout
from scribe_desktop.speaker_eval import configure_output
from scribe_desktop.speech import BYTES_PER_SAMPLE, SAMPLE_RATE
from scribe_desktop.speech import write_wav as speech_write_wav
from scribe_desktop.validation import (
    ENCOUNTER_ID_PATTERN,
    REPO_ROOT,
    UNNAMED_ENCOUNTER,
    EncounterScript,
    ScriptError,
    load_script,
    load_script_with_bytes,
)

TARGET_SAMPLE_RATE: Final = SAMPLE_RATE
# Every turn's RMS level: -20 dBFS.
TURN_RMS: Final = 0.1 * 32767
LEAD_SECONDS: Final = 0.5
GAP_SECONDS: Final = 0.6
TAIL_SECONDS: Final = 0.5
# The mix is scaled down when its peak would pass this (no clipping).
PEAK_LIMIT: Final = 0.95 * 32767
MIN_VOICES: Final = 2
_ENCOUNTER_ID_RE: Final = re.compile(ENCOUNTER_ID_PATTERN)
# SAPI's ``SVSFIsNotXML``: a line is spoken as text, never parsed as markup.
SAPI_IS_NOT_XML: Final = 16
# ``SAFT16kHz16BitMono`` — requested, not honoured by the OneCore voices
# (which is why every turn is resampled). Shared with ``tests/sapi_fixture``.
SAPI_16K_MONO: Final = 22
# ``SSFMCreateForWrite``.
SAPI_CREATE_FOR_WRITE: Final = 3

VoiceLister = Callable[[], Sequence[str]]
# (text, voice index, rate) -> TRUE 16 kHz mono PCM16.
Synthesizer = Callable[[str, int, int], bytes]


class BuildError(Exception):
    """An encounter or the set cannot be built (names and numbers only)."""


class TooFewVoicesError(BuildError):
    """Fewer than ``MIN_VOICES`` Windows voices are installed."""


class RolePlayScriptError(BuildError):
    """The script has no synthetic conditions: it is recorded, not built."""


# ---------------------------------------------------------------------------
# Resampling (moved from tests/sapi_fixture.py, which re-imports it).
# ---------------------------------------------------------------------------


def resample_wav_to_pcm16(wav_path: str | Path, sample_rate: int = TARGET_SAMPLE_RATE) -> bytes:
    """Decode a WAV at ANY rate/layout to mono PCM16 at ``sample_rate``.

    Reads the rate from the container rather than trusting what the writer
    was asked for: SAPI ignores the format requested on ``SPFileStream`` (the
    OneCore voices write 22050 Hz, measured 2026-07-30). PyAV's swresample is
    the resampler faster-whisper uses when it decodes audio itself, so the
    audio reaches the models the way production 16 kHz capture does. ``av``
    arrives with the ``[ml]`` extra and is imported here, not at module
    import.
    """
    import av
    from av.audio.resampler import AudioResampler

    resampler = AudioResampler(format="s16", layout="mono", rate=sample_rate)
    pcm = bytearray()
    with av.open(str(wav_path), mode="r") as container:
        for frame in container.decode(container.streams.audio[0]):
            for resampled in resampler.resample(frame):
                pcm += resampled.to_ndarray().tobytes()
    for resampled in resampler.resample(None):  # flush the resampler's tail
        pcm += resampled.to_ndarray().tobytes()
    return bytes(pcm)


# ---------------------------------------------------------------------------
# The real speech engine (never called by the test suite).
# ---------------------------------------------------------------------------


def sapi_voices() -> tuple[str, ...]:  # pragma: no cover - the real speech engine
    """The installed Windows (SAPI) voices' descriptions, in SAPI's order —
    the order a script's ``voice_slots`` index."""
    import win32com.client

    tokens = win32com.client.Dispatch("SAPI.SpVoice").GetVoices()
    return tuple(str(tokens.Item(index).GetDescription()) for index in range(tokens.Count))


def sapi_synthesize(text: str, voice_index: int, rate: int) -> bytes:  # pragma: no cover
    """Speak ``text`` with installed voice ``voice_index`` at SAPI ``rate``
    (-10..10) into a temporary WAV and return it resampled to TRUE 16 kHz.
    The text is synthetic script text; the temporary folder is removed."""
    import win32com.client

    with tempfile.TemporaryDirectory(prefix="scribe-validation-set-") as folder:
        target = Path(folder) / "turn.wav"
        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        stream.Format.Type = SAPI_16K_MONO
        stream.Open(str(target), SAPI_CREATE_FOR_WRITE)
        try:
            voice = win32com.client.Dispatch("SAPI.SpVoice")
            voice.Voice = voice.GetVoices().Item(voice_index)
            voice.Rate = rate
            voice.AudioOutputStream = stream
            voice.Speak(text, SAPI_IS_NOT_XML)
        finally:
            # Review round 22: an open stream would keep turn.wav locked and
            # the folder's removal would then fail under the speech error.
            stream.Close()
        return resample_wav_to_pcm16(target)


# ---------------------------------------------------------------------------
# Signal processing (pure; tested on tones).
# ---------------------------------------------------------------------------


def pcm_samples(pcm: bytes) -> list[int]:
    """Little-endian PCM16 bytes as sample values."""
    if len(pcm) % BYTES_PER_SAMPLE:
        raise BuildError("a turn's audio ends with a partial sample")
    samples = array("h")
    samples.frombytes(pcm)
    if sys.byteorder == "big":  # pragma: no cover - Windows is little-endian
        samples.byteswap()
    return list(samples)


def rms(samples: Sequence[float]) -> float:
    """Root mean square (0 for no samples)."""
    if not samples:
        return 0.0
    return math.sqrt(math.fsum(value * value for value in samples) / len(samples))


def level_turn(samples: Sequence[int], target_rms: float = TURN_RMS) -> list[float]:
    """``samples`` scaled to ``target_rms``; a silent turn is refused (a voice
    that produced nothing would be a span with no speech)."""
    level = rms(samples)
    if level == 0.0:
        raise BuildError("a turn was synthesised as silence")
    gain = target_rms / level
    return [value * gain for value in samples]


@dataclass(frozen=True)
class Placement:
    """Where each turn sits in the mix: its first sample and its length, in
    16 kHz samples, and the mix's total length."""

    offsets: tuple[int, ...]
    lengths: tuple[int, ...]
    total: int


def place_turns(
    lengths: Sequence[int],
    *,
    overlap_lines: Sequence[int] = (),
    overlap_seconds: float = 0.0,
    sample_rate: int = TARGET_SAMPLE_RATE,
) -> Placement:
    """Offsets for turns of ``lengths`` samples: ``LEAD_SECONDS`` of silence,
    each turn ``GAP_SECONDS`` after the latest end so far, a turn in
    ``overlap_lines`` starting ``overlap_seconds`` before the PREVIOUS turn
    ends (never before it starts), and ``TAIL_SECONDS`` after the last end."""
    lead = round(LEAD_SECONDS * sample_rate)
    gap = round(GAP_SECONDS * sample_rate)
    overlap = round(overlap_seconds * sample_rate)
    overlapped = set(overlap_lines)
    offsets: list[int] = []
    latest_end = lead - gap
    for index, length in enumerate(lengths):
        if index in overlapped and index > 0:
            previous_start = offsets[index - 1]
            previous_end = previous_start + lengths[index - 1]
            start = max(previous_start, previous_end - overlap)
        else:
            start = latest_end + gap
        offsets.append(start)
        latest_end = max(latest_end, start + length)
    total = latest_end + round(TAIL_SECONDS * sample_rate)
    return Placement(tuple(offsets), tuple(lengths), total)


def mix_turns(turns: Sequence[Sequence[float]], placement: Placement) -> list[float]:
    """The turns summed at their offsets (overlap adds)."""
    mix = [0.0] * placement.total
    for turn, offset in zip(turns, placement.offsets, strict=True):
        for index, value in enumerate(turn):
            mix[offset + index] += value
    return mix


def active_samples(placement: Placement) -> list[bool]:
    """True where at least one turn is speaking."""
    active = [False] * placement.total
    for offset, length in zip(placement.offsets, placement.lengths, strict=True):
        active[offset : offset + length] = [True] * length
    return active


def encounter_seed(encounter_id: str) -> int:
    """The noise seed fixed per encounter: its id's SHA-256, first 8 bytes."""
    return int.from_bytes(hashlib.sha256(encounter_id.encode("utf-8")).digest()[:8], "big")


def add_noise(
    mix: Sequence[float], active: Sequence[bool], snr_db: float, seed: int
) -> list[float]:
    """``mix`` plus Gaussian noise from ``seed``, scaled so that the speech
    power over the ``active`` samples over the noise power over the SAME
    samples is ``snr_db`` exactly (up to float rounding)."""
    generator = random.Random(seed)
    noise = [generator.gauss(0.0, 1.0) for _ in mix]
    speech = [value for value, on in zip(mix, active, strict=True) if on]
    under = [value for value, on in zip(noise, active, strict=True) if on]
    if not speech:
        raise BuildError("no turn is active, so no signal-to-noise ratio exists")
    speech_power = math.fsum(value * value for value in speech) / len(speech)
    noise_power = math.fsum(value * value for value in under) / len(under)
    gain = math.sqrt(speech_power / (noise_power * 10 ** (snr_db / 10)))
    return [value + gain * n for value, n in zip(mix, noise, strict=True)]


def to_pcm16(samples: Sequence[float], peak_limit: float = PEAK_LIMIT) -> bytes:
    """Rounded little-endian PCM16; the whole signal is scaled down first
    when its peak passes ``peak_limit`` (one gain, so ratios hold)."""
    peak = max((abs(value) for value in samples), default=0.0)
    gain = peak_limit / peak if peak > peak_limit else 1.0
    out = array("h", (max(-32768, min(32767, round(value * gain))) for value in samples))
    if sys.byteorder == "big":  # pragma: no cover - Windows is little-endian
        out.byteswap()
    return out.tobytes()


def label_track(roles: Sequence[str], placement: Placement) -> str:
    """The Audacity label track (``start<TAB>end<TAB>role``) from the final
    sample offsets. Seven decimals are exact for a 16 kHz offset
    (1/16000 s = 0.0000625 s), so a span parses back to its samples."""
    rows = []
    for role, offset, length in zip(roles, placement.offsets, placement.lengths, strict=True):
        start = offset / TARGET_SAMPLE_RATE
        end = (offset + length) / TARGET_SAMPLE_RATE
        rows.append(f"{start:.7f}\t{end:.7f}\t{role}\n")
    return "".join(rows)


def wav_bytes(pcm: bytes) -> bytes:
    """``pcm`` as a 16 kHz mono 16-bit WAV file's bytes (the
    ``speaker_eval.read_wav_pcm`` contract), through the package's ONE WAV
    writer (``speech.write_wav``; development-recordings plan D10)."""
    buffer = io.BytesIO()
    speech_write_wav(buffer, (pcm,))
    return buffer.getvalue()


def write_wav(path: Path, pcm: bytes) -> None:
    path.write_bytes(wav_bytes(pcm))


# ---------------------------------------------------------------------------
# One encounter, and the set.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BuiltEncounter:
    """What was written for one encounter: its id, its length in seconds and
    its turn placement (numbers only)."""

    encounter_id: str
    seconds: float
    placement: Placement


def render_encounter(
    script: EncounterScript, voices: Sequence[str], synthesize: Synthesizer
) -> tuple[bytes, str, Placement]:
    """The WAV bytes (PCM16), the label track and the placement for one
    synthetic script. Refuses a role-play script (no conditions) and a voice
    slot beyond the installed voices, by name."""
    conditions = script.conditions
    if conditions is None:
        raise RolePlayScriptError(
            f"{script.encounter_id}: a role-play script is recorded, not built"
        )
    turns: list[list[float]] = []
    for index, line in enumerate(script.lines):
        slot = conditions.voice_slots[line.role]
        if slot >= len(voices):
            raise BuildError(
                f"{script.encounter_id}: role {line.role!r} uses voice slot {slot}, but only "
                f"{len(voices)} voice(s) are installed"
            )
        try:
            turns.append(level_turn(pcm_samples(synthesize(line.text, slot, conditions.rate))))
        except BuildError as exc:
            raise BuildError(f"{script.encounter_id}: line {index}: {exc}") from None
    placement = place_turns(
        [len(turn) for turn in turns],
        overlap_lines=conditions.overlap_lines,
        overlap_seconds=conditions.overlap_seconds,
    )
    mix = mix_turns(turns, placement)
    if conditions.snr_db is not None:
        mix = add_noise(
            mix, active_samples(placement), conditions.snr_db, encounter_seed(script.encounter_id)
        )
    roles = [line.role for line in script.lines]
    return to_pcm16(mix), label_track(roles, placement), placement



def _write_replacing(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` through a sibling temporary file and one
    ``os.replace``, so an interrupted write never leaves a half-written file
    under the final name."""
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


# The builder's ownership mark beside each triple it writes (peer round 14,
# PR-MED-057). ``find_encounters`` reads only ``.json`` / ``.wav`` / ``.txt``,
# so the harness never sees it. It is written BEFORE the earlier script copy
# is removed and stays with the triple, so a WAV and label track without
# their script are this builder's (an interrupted rebuild, which must stay
# rebuildable) exactly when the mark is beside them; without it they are
# someone's recording, and are never overwritten.
BUILT_MARKER_SUFFIX: Final = ".built"
_BUILT_MARKER: Final = b"written by the synthetic validation-set builder\n"


def _builder_owned_without_script(out_dir: Path, stem: str) -> bool:
    return (out_dir / f"{stem}{BUILT_MARKER_SUFFIX}").is_file()


def _refuse_to_overwrite(out_dir: Path, stem: str) -> None:
    """Refuse to replace ``stem``'s files in ``out_dir`` unless they are
    absent or this builder's own — a SYNTHETIC script there, or, with no
    script, the builder's ownership mark: a recorded role-play (its script,
    or its WAV or label track without one), or a script that does not load
    (one still being written), is never overwritten (round 12 LOW-005; peer
    round 14, PR-MED-057)."""
    existing = out_dir / f"{stem}.json"
    if not existing.exists():
        recorded = [
            f"{stem}{suffix}"
            for suffix in (".wav", ".txt")
            if (out_dir / f"{stem}{suffix}").exists()
        ]
        if recorded and not _builder_owned_without_script(out_dir, stem):
            raise BuildError(
                f"{stem}: {' and '.join(recorded)} already in the set folder without its "
                "script and not written by this builder (a recording?) - nothing was "
                "overwritten; add its script or move the files, then build again"
            )
        return
    try:
        earlier = load_script(existing)
    except ScriptError:
        raise BuildError(
            f"{stem}: an unreadable script already holds this name in the set folder - "
            "nothing was overwritten; move it, then build again"
        ) from None
    if earlier.conditions is None:
        raise BuildError(
            f"{stem}: a role-play already holds this name in the set folder - nothing was "
            "overwritten"
        )


def build_encounter(
    script_path: Path, out_dir: Path, voices: Sequence[str], synthesize: Synthesizer
) -> BuiltEncounter:
    """One script into ``out_dir``: ``<id>.wav``, ``<id>.txt`` and a byte-exact
    copy of the ``<id>.json`` bytes that were rendered (read once — round 12
    LOW-008), each written only after the whole encounter has rendered, and
    each replaced in one step. The earlier ``<id>.json`` goes first and the
    new one is written last, so an interruption leaves an incomplete triple
    the harness reports ("missing .json"), never a mixed one (round 12
    LOW-006). A write that fails (a file open in another program) is
    refused by name with what to do (round 13 LOW-008). The ownership mark
    is written first and stays (``BUILT_MARKER_SUFFIX``; peer round 14,
    PR-MED-057)."""
    script, blob = load_script_with_bytes(script_path)
    pcm, labels, placement = render_encounter(script, voices, synthesize)
    stem = script.encounter_id
    _refuse_to_overwrite(out_dir, stem)
    try:
        _write_replacing(out_dir / f"{stem}{BUILT_MARKER_SUFFIX}", _BUILT_MARKER)
        (out_dir / f"{stem}.json").unlink(missing_ok=True)
        _write_replacing(out_dir / f"{stem}.wav", wav_bytes(pcm))
        _write_replacing(out_dir / f"{stem}.txt", labels.encode("utf-8"))
        _write_replacing(out_dir / f"{stem}.json", blob)
    except OSError as exc:
        raise BuildError(
            f"{stem}: could not be written ({type(exc).__name__}) - close any program "
            f"holding {stem}.wav or {stem}.txt, or delete them, then build again"
        ) from None
    return BuiltEncounter(stem, placement.total / TARGET_SAMPLE_RATE, placement)


def _remove_earlier_build(out_dir: Path, stem: str) -> str:
    """Remove ``stem``'s earlier triple from ``out_dir`` when this builder
    wrote it — its script there is a SYNTHETIC one, or there is no script
    and the ownership mark is present (an interrupted rebuild; peer round
    14, PR-MED-057) — so a failed rebuild never leaves a stale build to be
    measured. A role-play's files (no conditions, or no mark) or a script
    that does not load are left untouched. The script goes first and the
    mark last, so a removal that fails part-way leaves an incomplete triple
    still marked as the builder's. A mark with nothing beside it (a first
    build that failed after writing it) is removed on its own (peer round
    15, PR-LOW-060). Returns the note for the error line (""
    when nothing was removed); a file that cannot be removed (open in
    another program) is named in it, never raised (round 12 LOW-007)."""
    script = out_dir / f"{stem}.json"
    if script.exists():
        try:
            earlier = load_script(script)
        except ScriptError:
            return ""
        if earlier.conditions is None:
            return ""
    elif not _builder_owned_without_script(out_dir, stem):
        return ""
    elif not any((out_dir / f"{stem}{suffix}").exists() for suffix in (".wav", ".txt")):
        # A lone mark (a first build that failed after writing it) owns
        # nothing, and left in place it would let a recording later put
        # under this id be overwritten (peer round 15, PR-LOW-060).
        try:
            (out_dir / f"{stem}{BUILT_MARKER_SUFFIX}").unlink(missing_ok=True)
        except OSError as exc:
            return (
                f"; its leftover build mark could not be removed ({type(exc).__name__}) - "
                f"delete {stem}{BUILT_MARKER_SUFFIX} by hand"
            )
        return f"; its leftover {stem}{BUILT_MARKER_SUFFIX} was removed"
    try:
        for suffix in (".json", ".wav", ".txt", BUILT_MARKER_SUFFIX):
            (out_dir / f"{stem}{suffix}").unlink(missing_ok=True)
    except OSError as exc:
        return (
            f"; its earlier build could not be removed ({type(exc).__name__}) - delete "
            f"{stem}.wav, {stem}.txt, {stem}.json and {stem}{BUILT_MARKER_SUFFIX} by hand"
        )
    return "; its earlier build was removed"


def _inside(path: Path, folder: Path) -> bool:
    return path.resolve().is_relative_to(folder.resolve())


def _app_data_folders() -> list[Path]:
    """Both channels' data folders (each read now; one that cannot be
    resolved is skipped, as the runner's own-config refusal does)."""
    folders: list[Path] = []
    channels: tuple[install_layout.Channel, ...] = ("production", "dev")
    for channel in channels:
        try:
            folders.append(install_layout.data_root(channel))
        except (OSError, RuntimeError):
            continue
    return folders


def build_set(
    scripts_dir: Path,
    out_dir: Path,
    *,
    voices: VoiceLister | None = None,
    synthesize: Synthesizer | None = None,
    only: Sequence[str] = (),
    repo_root: Path | None = None,
    progress: Callable[[str], None] = print,
) -> tuple[list[BuiltEncounter], int]:
    """Every synthetic script in ``scripts_dir`` (or those named in ``only``)
    into ``out_dir``: ``(built, errors)``. ``voices`` / ``synthesize``
    default to the real speech engine, looked up at call time. Refuses
    outright — before any voice speaks — an output folder that IS the
    scripts folder or lies inside ``repo_root`` or either channel's data
    folder (round 26), voices that cannot be
    listed, fewer than ``MIN_VOICES`` installed voices
    (``TooFewVoicesError``), a set folder that cannot be created, and a
    scripts folder that cannot be listed, in that order. A role-play script
    is skipped and said so; any other failing script is reported (its
    refusal text, or an exception TYPE) and counted, and its earlier
    synthetic build in ``out_dir`` is removed — except a script file not
    named as an encounter id, which is counted and reported without its name
    (``UNNAMED_ENCOUNTER``) and touches nothing. A name in ``only`` that
    matches no script exactly is an error."""
    if out_dir.resolve() == scripts_dir.resolve():
        raise BuildError("the output folder must not be the scripts folder")
    if repo_root is not None and _inside(out_dir, repo_root):
        raise BuildError("the set folder must be outside the repository")
    if any(_inside(out_dir, folder) for folder in _app_data_folders()):
        # Round 26: plaintext WAVs and scripts never land in either app
        # data folder (installation plan C8 for the production one).
        raise BuildError("the set folder must be outside the app's data folders")
    try:
        installed = tuple((voices or sapi_voices)())
    except Exception as exc:  # noqa: BLE001 - a COM failure: refused by TYPE (round 12 LOW-007)
        raise BuildError(f"the Windows voices cannot be listed ({type(exc).__name__})") from None
    if len(installed) < MIN_VOICES:
        raise TooFewVoicesError(
            f"{len(installed)} Windows voice(s) installed; the builder needs at least "
            f"{MIN_VOICES}, one per role - add a voice in Windows Settings (Time & language, "
            "Speech), then run this again"
        )
    speak = synthesize or sapi_synthesize
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BuildError(f"the set folder cannot be created ({type(exc).__name__})") from None
    try:
        scripts = sorted(scripts_dir.glob("*.json"))
    except OSError as exc:
        raise BuildError(f"the scripts folder cannot be listed ({type(exc).__name__})") from None
    wanted = set(only)
    built: list[BuiltEncounter] = []
    errors = 0
    for script_path in scripts:
        if wanted and script_path.stem not in wanted:
            continue
        if not _ENCOUNTER_ID_RE.fullmatch(script_path.stem):
            # Review round 22 (the runner's round 11 MED-006 rule): a file
            # name that is not an encounter id may be a person's name, so it
            # is never printed, and nothing in the set folder is touched.
            errors += 1
            progress(f"[error] {UNNAMED_ENCOUNTER}: not built (name it <encounter id>.json)")
            continue
        # Peer round 27 (PR-HIGH-066): each line is written AFTER its
        # ``except`` block ends — a failed write inside one would chain the
        # build's exception (the speech engine's text can carry a line).
        skipped: str | None = None
        failed: str | None = None
        try:
            built.append(build_encounter(script_path, out_dir, installed, speak))
        except RolePlayScriptError as exc:
            skipped = str(exc)
        except Exception as exc:  # noqa: BLE001 - our refusal text, else the TYPE only
            failed = str(exc) if isinstance(exc, ScriptError | BuildError) else (
                f"{script_path.name}: {type(exc).__name__}"
            )
        if skipped is not None:
            progress(f"[skip] {skipped}")
            continue
        if failed is not None:
            errors += 1
            progress(f"[error] {failed}" + _remove_earlier_build(out_dir, script_path.stem))
            continue
        progress(f"[built] {built[-1].encounter_id} ({built[-1].seconds:.1f} s)")
    for name in sorted(wanted - {path.stem for path in scripts}):
        # Peer round 27 (PR-HIGH-067): the round-22 rule for an unmatched
        # --only value too — a name that is not an encounter id is not printed.
        errors += 1
        shown = name if _ENCOUNTER_ID_RE.fullmatch(name) else UNNAMED_ENCOUNTER
        progress(f"[error] {shown}: no script has this exact name")
    return built, errors


def resampler_available() -> bool:
    """Whether PyAV (``av``, from the ``[ml]`` extra) can be imported — the
    real synthesizer resamples every turn with it. The test seam."""
    return importlib.util.find_spec("av") is not None


def main(
    argv: list[str] | None = None,
    *,
    voices: VoiceLister | None = None,
    synthesize: Synthesizer | None = None,
) -> int:
    """Exit status 0 when every chosen script was built; 2 for a refusal
    before any voice speaks (a packaged build, missing folders, a set folder
    inside the repository, PyAV missing for the real synthesizer, fewer than
    two voices); 1 otherwise. ``voices`` / ``synthesize`` are the test
    seams (default: the real speech engine)."""
    configure_output()
    parser = argparse.ArgumentParser(
        description=(
            "Build the synthetic validation set (pilot plan Task 2.5): each synthetic script "
            "becomes <id>.wav (16 kHz mono), <id>.txt (its label track) and a copy of "
            "<id>.json, spoken by the installed Windows voices. Developer build only."
        )
    )
    parser.add_argument("scripts_dir", type=Path, help="folder of <id>.json scripts")
    parser.add_argument("out_dir", type=Path, help="the set folder to write (outside the repo)")
    parser.add_argument("--only", nargs="+", default=(), metavar="ID", help="build only these")
    args = parser.parse_args(argv)
    if install_layout.channel() != "dev":
        print("[refused] the set builder runs only on the developer build")
        return 2
    scripts_dir: Path = args.scripts_dir
    if not scripts_dir.is_dir():
        print(f"[refused] {scripts_dir} is not a folder")
        return 2
    if synthesize is None and not resampler_available():
        print(
            "[refused] PyAV (`av`, installed with the [ml] extra) is missing; the builder "
            "resamples every spoken turn with it - install the [ml] extra (AGENTS.md step 2)"
        )
        return 2
    refusal: str | None = None
    try:
        built, errors = build_set(
            scripts_dir,
            args.out_dir,
            voices=voices,
            synthesize=synthesize,
            only=args.only,
            repo_root=REPO_ROOT,
        )
    except BuildError as exc:
        refusal = str(exc)  # printed after the handler (peer round 27, PR-HIGH-066)
    if refusal is not None:
        print(f"[refused] {refusal}")
        return 2
    print(f"built {len(built)} encounter(s); {errors} error(s)")
    return 0 if built and not errors else 1


__all__ = [
    "BUILT_MARKER_SUFFIX",
    "GAP_SECONDS",
    "LEAD_SECONDS",
    "MIN_VOICES",
    "PEAK_LIMIT",
    "SAPI_16K_MONO",
    "SAPI_CREATE_FOR_WRITE",
    "SAPI_IS_NOT_XML",
    "TAIL_SECONDS",
    "TARGET_SAMPLE_RATE",
    "TURN_RMS",
    "BuildError",
    "BuiltEncounter",
    "Placement",
    "RolePlayScriptError",
    "TooFewVoicesError",
    "active_samples",
    "add_noise",
    "build_encounter",
    "build_set",
    "encounter_seed",
    "label_track",
    "level_turn",
    "main",
    "mix_turns",
    "pcm_samples",
    "place_turns",
    "render_encounter",
    "resample_wav_to_pcm16",
    "resampler_available",
    "rms",
    "sapi_synthesize",
    "sapi_voices",
    "to_pcm16",
    "wav_bytes",
    "write_wav",
]


if __name__ == "__main__":
    sys.exit(main())
