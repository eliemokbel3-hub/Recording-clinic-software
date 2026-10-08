"""The kept-recordings replay tool (development-recordings plan Phase 4,
Tasks 4.1a and 4.1b; D11, Critical Constraints C1, C5, C6, C8).

A practitioner-run, read-only tool over ONE Past-sessions folder named on
its command line. For every committed entry holding a recording kept under
written development consent, it re-transcribes the recording through the
CURRENT pipeline and compares the result with what the app kept at the
time — the transcript, and the clinician's saved note — printing numbers
keyed by session id only. Every number is DRIFT (the app against its own
earlier output and the clinician's reviewed note), never accuracy: nothing
here knows what was actually said.

Run it YOURSELF from a normal terminal on the developer build (never an
agent shell — those cannot see the user's model folder or unwrap this
Windows user's keys, docs/lessons.md), with Clinic Scribe closed (either
build) and the models downloaded by ``scripts/setup-models.py``, pointing it
at the Past-sessions folder explicitly — for the installed app that is
``%LOCALAPPDATA%\\ClinikoScribe\\past_sessions``, for the developer build
``%LOCALAPPDATA%\\ClinikoScribe-dev\\past_sessions``. See
``docs/testing/kept-recordings.md``.

What this module enforces, and what it does not:

- **A pure, explicitly pointed reader (D11, C8).** The folder is the
  command line's; this module never resolves the app's data folder. It
  calls only ``PastSessionStore.kept_session_ids`` (names and a zero-check —
  nothing is decrypted for an entry it does not replay; round 29 MED-001) /
  ``read_replay_inputs`` (the replayed entry's transcript and saved note —
  never its label, so no patient's name, nor its generated note; round 30)
  / ``read_recording`` and writes nothing in the folder. Refused, in this
  order and each before any decryption: a command line argparse cannot
  parse (fixed text — argparse's own message would quote the value), the
  packaged build, an ``--only`` value not shaped as a session id (never
  echoed; the WHOLE run is refused, stricter than skipping it), a
  ``--model`` value not shaped as a name, an ``--enrolment`` that is not a
  file, a path that is not a folder (not echoed: it is not known to be the
  archive), a folder that cannot be scanned, a folder holding no entry key
  (``key.dpapi``) — "not a Past-sessions folder" — and an app that is open:
  the run takes the app's instance exclusion (``app.acquire_instance_
  exclusion``, the one production path the developer build already
  shares) and proceeds ONLY when it is ``acquired`` — ``already_running``
  and ``unavailable`` both refuse. It HOLDS the exclusion for the whole run
  and releases it in ``finally``, so neither build can start, sweep or
  reconcile underneath. The acquire and release are resolved per call
  (``_acquire_exclusion`` / ``_release_exclusion``), so tests replace them.
- **Custody (C5).** Each kept recording's PCM is held in memory for its own
  entry only, then handed to ``speaker_eval.transcribe_in_temporary_store``
  with ``persist_key=False``: the temporary store's key lives in memory
  only, so an interrupted run leaves ciphertext with no key anywhere, and
  the store is torn down key-first on every path. A store that cannot be
  shown gone — or is gone but a teardown step failed — STOPS the run with
  ``speaker_eval``'s own custody diagnostic (the temporary path, the key
  state, and whether anything remains to delete by hand) — the one line
  that names a resolved path other than the folder given (C6); a Ctrl+C
  names only ``%TEMP%``, and a missing model "the developer build's models
  folder" (round 29 LOW-003) — naming the model only when it is the default
  (a ``--model`` value is the practitioner's typing; round 30).
- **Text-free output (C1, C6).** Session ids, numbers and fixed text only:
  no transcript, note, name or label text; a kept transcript's model name is
  printed only when it is shaped like one. An unexpected failure is
  reported by its exception TYPE (``validation._error_type``) and a
  Past-sessions failure by its closed reason code; besides the custody
  diagnostic, ONE exception's own text is printed — an ``EnrolmentError``'s,
  whose every raiser on this path (``enrolment.enrol``) is fixed,
  numbers-only text (a new raiser must stay so; review round 31). Each is
  written after its
  ``except`` block ends (review round 26: a failed write inside one would
  chain the handled exception). No audit row and no Past-sessions entry is
  written.
- **Offline.** ``main`` applies and asserts the offline kill-switches before
  any model is constructed (``validation.main``'s order).
- **Shipped defaults (4.1b).** The note leg regenerates under the SHIPPED
  default note config (an empty config folder), never the app's own
  ``config\\`` — so its drift includes the practitioner's learned cues, as
  the report's header says.
"""

from __future__ import annotations

import argparse
import itertools
import os
import re
import sys
import tempfile
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, NoReturn, Protocol

from scribe_desktop import install_layout
from scribe_desktop.benchmark import apply_offline_env, assert_offline_env
from scribe_desktop.enrolment import EnrolmentError
from scribe_desktop.note import GeneratedNote, compose_draft, finalise_note
from scribe_desktop.note_check import check_note
from scribe_desktop.note_config import NoteConfig, NoteConfigError, load_note_config
from scribe_desktop.past_sessions import (
    PAST_SESSION_REASONS,
    PastSessionError,
    PastSessionStore,
)
from scribe_desktop.session_store import KEY_FILENAME, SESSION_ID_PATTERN
from scribe_desktop.speaker_embedding import build_speaker_embedder
from scribe_desktop.speaker_eval import (
    TEMP_DIR_PREFIX,
    WAV_FORMAT_HELP,
    EnrolmentInputs,
    SpeakerEvalError,
    WavFormatError,
    configure_output,
    enrolment_inputs,
    read_wav_pcm,
    transcribe_in_temporary_store,
)
from scribe_desktop.speech import (
    BYTES_PER_SAMPLE,
    SAMPLE_RATE,
    FrameProbabilityFn,
    SileroVad,
    SpeechProvider,
    vad_model_available,
)
from scribe_desktop.transcription import (
    DEFAULT_WHISPER_MODEL,
    TranscriptDocument,
    WhisperSpeechProvider,
    whisper_model_available,
)
from scribe_desktop.ui.models import extractive_provider_from_config
from scribe_desktop.validation import (
    # Package-private by name, shared deliberately (the note.py convention):
    # the transcript's tokens in segment order and their (segment, word)
    # coordinates — the harness's own tokenisation, so the two tools cannot
    # disagree about what a word is — and the type-only error rule.
    _error_type,
    _hypothesis,
    align_transcripts,
    confirm_all,
    first_detected_prefill,
)

_SESSION_ID_RE: Final = re.compile(SESSION_ID_PATTERN)
# Printed in place of an ``--only`` value that is not a session id: such a
# value could be anything (a patient's name included), so it is never echoed.
UNNAMED_SESSION: Final = "(a value not shaped as a session id)"
# A model name as the report may print it; anything else is ``(unnamed)``.
_MODEL_NAME_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
# The best one-to-one label mapping is found exhaustively; a transcript with
# more distinct speaker labels than this on either side is not mapped (the
# shipped pipeline emits at most three).
MAX_MAPPED_LABELS: Final = 6
CONFIG_TEMP_PREFIX: Final = "scribe-replay-config-"


class ExclusionLike(Protocol):
    """What ``app.acquire_instance_exclusion`` returns, as this tool reads it."""

    @property
    def state(self) -> str: ...


def _acquire_exclusion() -> ExclusionLike:
    """The app's instance exclusion (``app`` imported here, not at module
    level: it imports Qt, and importing it runs no start-up)."""
    from scribe_desktop import app

    return app.acquire_instance_exclusion()


def _release_exclusion(exclusion: ExclusionLike) -> None:
    from scribe_desktop import app

    if isinstance(exclusion, app.InstanceExclusion):
        app.release_instance_exclusion(exclusion)


def _open_store(folder: Path) -> PastSessionStore:
    """The archive at the folder given — the store's default DPAPI custody."""
    return PastSessionStore(folder)


@dataclass(frozen=True)
class ReplayModels:
    """What one run transcribes with: the speech provider, the VAD frame
    probability, the Whisper model's name and, with ``--enrolment``, the
    in-memory voice profile (``speaker_eval.EnrolmentInputs``)."""

    provider: SpeechProvider = field(repr=False)
    frame_probability: FrameProbabilityFn = field(repr=False)
    model_name: str
    enrolment: EnrolmentInputs | None = field(default=None, repr=False)


def _load_models(model_name: str, enrolment_wav: Path | None) -> ReplayModels:
    """Construct the developer build's models (after the availability
    checks in ``main``). Raises ``WavFormatError`` / ``EnrolmentError`` for an
    unusable enrolment WAV, anything else as itself."""
    vad = SileroVad()
    provider = WhisperSpeechProvider(model_name=model_name)
    enrolment: EnrolmentInputs | None = None
    if enrolment_wav is not None:
        embedder = build_speaker_embedder()
        enrolment = enrolment_inputs(read_wav_pcm(enrolment_wav), embedder, vad.frame_probability)
    return ReplayModels(provider, vad.frame_probability, model_name, enrolment)


# ---------------------------------------------------------------------------
# The metrics (pure; numbers only).
# ---------------------------------------------------------------------------


def label_agreement(pairs: Sequence[tuple[str, str]]) -> float | None:
    """The fraction of aligned word pairs (kept label, new label) whose
    speaker labels agree under the BEST one-to-one mapping of kept labels to
    new labels — label agreement, not accuracy (the replay has no label
    track). None when there is no aligned pair, or more than
    ``MAX_MAPPED_LABELS`` distinct labels on either side."""
    if not pairs:
        return None
    counts = Counter(pairs)
    kept = sorted({a for a, _ in pairs})
    new = sorted({b for _, b in pairs})
    if len(kept) > MAX_MAPPED_LABELS or len(new) > MAX_MAPPED_LABELS:
        return None
    best = 0
    if len(kept) <= len(new):
        for chosen in itertools.permutations(new, len(kept)):
            best = max(best, sum(counts[(a, b)] for a, b in zip(kept, chosen, strict=True)))
    else:
        for chosen in itertools.permutations(kept, len(new)):
            best = max(best, sum(counts[(a, b)] for a, b in zip(chosen, new, strict=True)))
    return best / len(pairs)


def _tokens_and_labels(document: TranscriptDocument) -> tuple[list[str], list[str]]:
    tokens, positions = _hypothesis(document)
    segments = document.transcript_segments
    return tokens, [segments[segment].speaker for segment, _word in positions]


def _present_sections(note: GeneratedNote) -> set[str]:
    return {section.section_key for section in note.note_sections if section.note_assertions}


@dataclass(frozen=True)
class NoteDrift:
    """The note leg's numbers (Task 4.1b): checker warnings on the
    regenerated note by severity, and how many sections the clinician's
    saved note holds that the regenerated one does not (None with no saved
    note). Counts only."""

    errors: int
    reviews: int
    sections_missing: int | None


@dataclass(frozen=True)
class ReplayRow:
    """One replayed entry: the session id (pattern-checked by the store),
    seconds of audio, the kept and new model names (shape-checked when
    printed), the word error parts kept -> new, label agreement and the note
    leg. Numbers and ids only."""

    session_id: str
    seconds: float
    kept_model: str = field(repr=False)
    new_model: str = field(repr=False)
    kept_words: int
    new_words: int
    edit_distance: int
    agreement: float | None
    note: NoteDrift

    @property
    def drift(self) -> float | None:
        return self.edit_distance / self.kept_words if self.kept_words else None


def note_drift(
    document: TranscriptDocument,
    config: NoteConfig,
    saved: GeneratedNote | None,
    *,
    clinician_speaker: str | None,
    now: datetime,
) -> NoteDrift:
    """Task 4.1b: a note regenerated from ``document`` through the
    validation harness's OWN pipeline (``validation.evaluate_encounter``'s
    steps): ``compose_draft`` with the extractive provider built from
    ``config`` and its only template profile, the earliest detected prefill,
    every proposal confirmed (``confirm_all``), ``finalise_note``, then
    ``check_note`` (Checks 1–4) — and section coverage against ``saved``."""
    draft = compose_draft(
        document,
        config,
        extractive_provider_from_config(config),
        None,
        clinician_speaker=clinician_speaker,
        prefill_id=first_detected_prefill(document, config),
        learned_rules=None,
        decided_at=now,
    )
    note = finalise_note(draft, confirm_all(draft, now), document, config, created_at=now)
    warnings = check_note(note, document, config)
    missing = (
        None if saved is None else len(_present_sections(saved) - _present_sections(note))
    )
    return NoteDrift(
        errors=sum(1 for warning in warnings if warning.severity == "error"),
        reviews=sum(1 for warning in warnings if warning.severity == "review"),
        sections_missing=missing,
    )


def _replay_entry(
    store: PastSessionStore,
    session_id: str,
    models: ReplayModels,
    config: NoteConfig,
    now: Callable[[], datetime],
) -> ReplayRow:
    """One kept recording: the kept transcript and saved note, the audio into
    memory for this entry only, the current pipeline over a memory-keyed
    temporary store, then the numbers. ``PastSessionError`` for the entry,
    ``SpeakerEvalError`` for custody, anything else as itself."""
    # The transcript and saved note only: the label (the patient's name) and
    # the generated note are never decrypted (review round 30).
    kept_transcript, saved_note = store.read_replay_inputs(session_id)
    pcm = b"".join(store.read_recording(session_id))
    seconds = len(pcm) / (SAMPLE_RATE * BYTES_PER_SAMPLE)
    plain, enrolled = transcribe_in_temporary_store(
        pcm,
        models.provider,
        models.frame_probability,
        enrolment=models.enrolment,
        persist_key=False,
    )
    del pcm
    # With --enrolment the new transcript is the one the app makes with the
    # voice profile applied, and its practitioner-attributed label is the
    # clinician; without it the role is left unresolved (stated in the
    # header) — the replay has no label track to derive it from.
    document = enrolled if enrolled is not None else plain
    clinician = enrolled.enrolled_speaker if enrolled is not None else None
    kept_tokens, kept_labels = _tokens_and_labels(kept_transcript)
    new_tokens, new_labels = _tokens_and_labels(document)
    alignment = align_transcripts(kept_tokens, new_tokens)
    agreement = label_agreement([(kept_labels[i], new_labels[j]) for i, j in alignment.pairs])
    note = note_drift(document, config, saved_note, clinician_speaker=clinician, now=now())
    return ReplayRow(
        session_id=session_id,
        seconds=seconds,
        kept_model=kept_transcript.model_name,
        new_model=document.model_name,
        kept_words=alignment.words.reference_tokens,
        new_words=alignment.words.hypothesis_tokens,
        edit_distance=alignment.words.edit_distance,
        agreement=agreement,
        note=note,
    )


# ---------------------------------------------------------------------------
# The report (text-free: ids, numbers and fixed text).
# ---------------------------------------------------------------------------


def _model(name: str) -> str:
    return name if _MODEL_NAME_RE.fullmatch(name) else "(unnamed)"


def _fraction(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


def _count(value: int | None) -> str:
    return "-" if value is None else str(value)


def render_report(
    rows: Sequence[ReplayRow],
    *,
    folder: Path,
    model_name: str,
    enrolled: bool,
    errors: int,
    skipped: int,
) -> str:
    role = (
        "the practitioner-attributed label (--enrolment)"
        if enrolled
        else "unresolved (no --enrolment: no clinician label is set)"
    )
    lines = [
        "# Kept-recording replay - DRIFT, not accuracy",
        "",
        "Every number compares the CURRENT pipeline with what the app kept at the time "
        "(the kept transcript; the clinician's saved note) - it says how much the output "
        "changed, not how right either one is.",
        "",
        f"- Folder: {folder}",
        f"- Whisper model (new): {_model(model_name)}; VAD: silero",
        f"- Clinician role for the regenerated note: {role}",
        "- Note config: shipped defaults - drift includes your learned cues",
        "",
        "| Session | Seconds | Kept model | New model | Kept words | New words | Edit distance "
        "| Drift WER | Label agreement | Sections missing | Check errors | Check reviews |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.session_id} | {row.seconds:.1f} | {_model(row.kept_model)} "
            f"| {_model(row.new_model)} | {row.kept_words} | {row.new_words} "
            f"| {row.edit_distance} | {_fraction(row.drift)} | {_fraction(row.agreement)} "
            f"| {_count(row.note.sections_missing)} | {row.note.errors} | {row.note.reviews} |"
        )
    kept_words = sum(row.kept_words for row in rows)
    edits = sum(row.edit_distance for row in rows)
    pooled = edits / kept_words if kept_words else None
    lines += [
        "",
        f"Totals: {len(rows)} replayed, {errors} error(s), {skipped} skipped; "
        f"{sum(row.seconds for row in rows):.1f} s of audio; pooled drift WER "
        f"{_fraction(pooled)} ({edits} edits over {kept_words} kept words).",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI. Run by the PRACTITIONER from a normal terminal (docs/lessons.md).
# ---------------------------------------------------------------------------


class _QuietParser(argparse.ArgumentParser):
    """argparse's own errors quote what they could not parse
    (``unrecognized arguments: …``) — an unquoted ``--only Jane Citizen``
    would echo a name — so a command-line error is fixed text, with the
    usage (option names only) on stderr (round 29 LOW-001)."""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, "[refused] the command line was not understood - see --help\n")


def _parser() -> argparse.ArgumentParser:
    parser = _QuietParser(
        description=(
            "Replay the recordings kept for development in one Past-sessions folder through "
            "the current pipeline and print text-free DRIFT numbers per session id "
            "(development-recordings plan Phase 4). Developer build only; close Clinic "
            "Scribe first."
        )
    )
    parser.add_argument(
        "past_sessions_dir",
        type=Path,
        help="the Past-sessions folder to read (named explicitly; see the docs)",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=None,
        metavar="SESSION_ID",
        help="replay only this session id (repeatable)",
    )
    parser.add_argument(
        "--enrolment",
        type=Path,
        default=None,
        metavar="WAV",
        help=(
            "a 16 kHz mono 16-bit PCM WAV of the practitioner reading aloud; the new "
            "transcript is made with that voice profile applied in memory (never saved), "
            "and the regenerated note's clinician is the practitioner-attributed label"
        ),
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_WHISPER_MODEL,
        help=f"the Whisper model to transcribe with (default: {DEFAULT_WHISPER_MODEL})",
    )
    return parser


def _holds_entries(folder: Path) -> bool:
    """Whether ``folder`` holds at least one Past-sessions entry: a folder
    named as a session id with an entry key in it. Names and existence only
    — nothing is opened or decrypted."""
    with os.scandir(folder) as children:
        for child in children:
            if (
                _SESSION_ID_RE.fullmatch(child.name)
                and child.is_dir(follow_symlinks=False)
                and (Path(child.path) / KEY_FILENAME).is_file()
            ):
                return True
    return False


def main(argv: list[str] | None = None) -> int:
    """Exit status 0 only when at least one kept recording was replayed and
    none failed; 2 for a refusal before any recording is read; 1 otherwise
    (no kept recording to replay, an entry that failed, an interrupted or
    stopped run). Refusals, in order: a command line that cannot be parsed
    (exit 2 through ``SystemExit``), a packaged build, an ``--only`` value
    that is not a session id, a ``--model`` value that is not a model name,
    an ``--enrolment`` that is not a file, a path that is not a folder, a
    folder that cannot be scanned, a folder holding no entry key, the app's
    instance exclusion not acquired, then (with the offline switches
    applied) a models folder that cannot be located, the models by name, a
    config or model that cannot be loaded (by type), and an archive that
    cannot be listed (by reason code)."""
    configure_output()
    args = _parser().parse_args(argv)
    if install_layout.channel() != "dev":
        print("[refused] the replay tool runs only on the developer build")
        return 2
    only: list[str] = list(args.only or [])
    if any(not _SESSION_ID_RE.fullmatch(value) for value in only):
        print(f"[refused] --only {UNNAMED_SESSION}: give session ids only")
        return 2
    model_name: str = args.model
    if not _MODEL_NAME_RE.fullmatch(model_name):
        print("[refused] --model: not a Whisper model name")
        return 2
    enrolment_wav: Path | None = args.enrolment
    if enrolment_wav is not None and not enrolment_wav.is_file():
        # Round 30: before the lock and the models, and never echoed.
        print("[refused] --enrolment: not a file (give the path to your enrolment WAV)")
        return 2
    folder: Path = args.past_sessions_dir
    if not folder.is_dir():
        # Round 30: not echoed — a path that is not a folder is not known to
        # be the archive, and could be anything typed.
        print("[refused] the path given is not a folder (give the Past-sessions folder)")
        return 2
    scan_failure: str | None = None
    holds = False
    try:
        holds = _holds_entries(folder)
    except OSError as exc:
        scan_failure = _error_type(exc)
    if scan_failure is not None:
        print(f"[refused] {folder} cannot be listed ({scan_failure})")
        return 2
    if not holds:
        print(f"[refused] {folder} is not a Past-sessions folder (it holds no entry key)")
        return 2

    acquire = _acquire_exclusion  # resolved per call: tests replace them
    release = _release_exclusion
    exclusion = acquire()
    try:
        if exclusion.state != "acquired":
            print(
                "[refused] close Clinic Scribe first (either build): the replay holds the "
                f"app's single-instance lock for its run ({exclusion.state})"
            )
            return 2
        return _run(folder, only, model_name, enrolment_wav)
    finally:
        release(exclusion)


def _run(folder: Path, only: list[str], model_name: str, enrolment_wav: Path | None) -> int:
    """Everything after the exclusion is held (``main`` releases it)."""
    apply_offline_env()
    assert_offline_env()
    models_failure: str | None = None
    try:
        install_layout.models_root()  # located, never printed (round 29 LOW-003)
    except (OSError, RuntimeError) as exc:
        models_failure = _error_type(exc)
    if models_failure is not None:
        print(f"[refused] the models folder cannot be located ({models_failure})")
        return 2
    if not whisper_model_available(model_name):
        # Round 30: a --model value is the practitioner's typing, shape-checked
        # only — named here only when it is the default.
        named = f"`{model_name}`" if model_name == DEFAULT_WHISPER_MODEL else "named by --model"
        print(
            f"[refused] Whisper {named} is not installed in the developer build's "
            f"models folder: {install_layout.model_remedy()}"
        )
        return 2
    if not vad_model_available():
        print(
            "[refused] the silero VAD model is not installed in the developer build's "
            f"models folder: {install_layout.model_remedy()}"
        )
        return 2
    config_failure: str | None = None
    config: NoteConfig | None = None
    try:
        with tempfile.TemporaryDirectory(prefix=CONFIG_TEMP_PREFIX) as empty:
            config = load_note_config(Path(empty))
    except (NoteConfigError, OSError) as exc:
        config_failure = _error_type(exc)
    if config_failure is not None or config is None:
        print(f"[refused] the shipped default note config cannot be loaded ({config_failure})")
        return 2

    load_failure: str | None = None
    load_detail: str | None = None
    load_interrupted = False
    models: ReplayModels | None = None
    try:
        models = _load_models(model_name, enrolment_wav)
    except KeyboardInterrupt:
        load_interrupted = True
    except WavFormatError as exc:
        # Round 29 LOW-002: ``read_wav_pcm``'s text names the file; the fixed
        # format help is printed instead.
        load_failure = _error_type(exc)
        load_detail = f"the --enrolment WAV must be a {WAV_FORMAT_HELP}"
    except EnrolmentError as exc:
        load_failure = _error_type(exc)
        # Enrolment's own authored text, numbers only — the module docstring's
        # one other printed exception text (C6 as built; review round 31).
        load_detail = str(exc)
    except Exception as exc:  # noqa: BLE001 - reported by TYPE (round 26)
        load_failure = _error_type(exc)
    if load_interrupted:
        print("[stopped] the run was interrupted while the models loaded; nothing was run")
        return 1
    if load_failure is not None or models is None:
        line = f"[refused] the models could not be loaded ({load_failure})"
        print(line if load_detail is None else f"{line}: {load_detail}")
        return 2

    store = _open_store(folder)
    listing_failure: str | None = None
    kept: list[str] = []
    try:
        # Names and the key file's zero-check only: no label (no patient's
        # name) is decrypted for an entry the run does not replay (round 29
        # MED-001).
        kept = sorted(store.kept_session_ids())
    except PastSessionError as exc:
        listing_failure = _reason(exc)
    except Exception as exc:  # noqa: BLE001 - reported by TYPE
        listing_failure = _error_type(exc)
    if listing_failure is not None:
        print(f"[refused] {folder} cannot be listed ({listing_failure})")
        return 2
    skipped = 0
    if only:
        wanted = list(dict.fromkeys(only))
        for session_id in wanted:
            if session_id not in kept:
                skipped += 1
                print(f"[skip] {session_id}: no kept recording in this folder")
        kept = [session_id for session_id in kept if session_id in wanted]
    if not kept:
        print(f"[error] no kept recordings to replay in {folder}")
        return 1
    return _replay_all(store, kept, models, config, folder=folder, skipped=skipped)


def _reason(exc: PastSessionError) -> str:
    return exc.reason if exc.reason in PAST_SESSION_REASONS else _error_type(exc)


def _replay_all(
    store: PastSessionStore,
    session_ids: Sequence[str],
    models: ReplayModels,
    config: NoteConfig,
    *,
    folder: Path,
    skipped: int,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> int:
    rows: list[ReplayRow] = []
    errors = 0
    custody: str | None = None
    interrupted = False
    try:
        for session_id in session_ids:
            print(f"[run ] {session_id}", flush=True)
            failure: str | None = None
            try:
                rows.append(_replay_entry(store, session_id, models, config, now))
            except PastSessionError as exc:
                failure = _reason(exc)
            except SpeakerEvalError:
                raise  # custody: a teardown not shown complete stops the run
            except Exception as exc:  # noqa: BLE001 - reported by TYPE only, run continues
                failure = _error_type(exc)
            if failure is not None:
                errors += 1
                print(f"[error] {session_id}: {failure}")
    except SpeakerEvalError as exc:
        custody = str(exc)  # speaker_eval's own text naming the temporary path
    except KeyboardInterrupt:
        interrupted = True
    if custody is not None:
        print(f"[custody] the run stopped: {custody}")
        return 1
    if interrupted:
        print(
            "[stopped] the run was interrupted, so there is no report - look in your "
            f"temporary folder (%TEMP%) for a {TEMP_DIR_PREFIX}* folder an interrupted "
            "teardown may have left (its key was never written to disk; delete it)"
        )
        return 1
    print()
    print(
        render_report(
            rows,
            folder=folder,
            model_name=models.model_name,
            enrolled=models.enrolment is not None,
            errors=errors,
            skipped=skipped,
        )
    )
    return 0 if rows and not errors else 1


__all__ = [
    "MAX_MAPPED_LABELS",
    "UNNAMED_SESSION",
    "NoteDrift",
    "ReplayModels",
    "ReplayRow",
    "label_agreement",
    "main",
    "note_drift",
    "render_report",
]
