"""One-time ML model setup for Clinic Scribe.

This script is one of the project's two SETUP-TIME network steps (the other is
the pinned prose-runtime wheel install, desktop/requirements-ml-prose.txt; see
flow 9 of docs/security/data-flow-map.md). It runs as a separate, explicit
setup step -- never at runtime, and the app never downloads a model. Runtime
processes load models from the local cache with the ML stack's network access
disabled and asserted off; the app's only network use is its read-only Cliniko
API client (flow 18).

Downloads into the models folder of this checkout's data folder -- since
installation plan Phase 1 a source checkout is the DEV channel, so that is
%LOCALAPPDATA%\\ClinikoScribe-dev\\models\\ (the installed app's models come
with its installer, never from this script):
  - silero-vad ONNX model (voice activity detection)
  - faster-whisper (CTranslate2) model candidates for the Step D6 benchmark
  - speaker-embedding ONNX model (voice enrolment; practitioner-profile plan)
  - language-model GGUF (the 4B instruct model behind the prose writing
    styles; note-learning-and-styles plan Phase 4)

Idempotent: existing complete downloads are skipped. No clinical data is
involved at any point.

The speaker-embedding entry is PINNED (practitioner-profile plan Task 0.5,
2026-09-15): URL, size and SHA-256 are recorded below from the practitioner's
Task 0.4 fetch, so it is handled exactly like silero-vad - an existing
``speaker-embedding/<name>.onnx.candidate`` left by that fetch is verified
against the pin and promoted to ``<name>.onnx`` (Task 0.6); otherwise the
file is downloaded, verified and written; a digest mismatch refuses and
leaves any candidate un-promoted; ``--candidate-url`` is refused. A run
without ``--only`` includes the entry.

An entry whose SHA-256 pin is EMPTY runs in CANDIDATE mode instead (the
route this entry took at Task 0.4, kept for evaluating a future candidate):
``--only <entry> --candidate-url https://...`` downloads to
``<name>.onnx.candidate``, prints the size and SHA-256 for the report, never
promotes, and a run without ``--only`` skips it (printed, never silent).
The speaker-embedding download - candidate and pinned alike - must be https
and so must EVERY redirect hop: a redirect to http is refused before it is
fetched, because the bytes a candidate fetch reports are the ones the pin
step trusts. That guard is installed for the speaker-embedding helper only;
silero-vad's fetch keeps the default opener and relies on its pre-existing
SHA-256 pin, and the whisper snapshots on their immutable commit SHAs.

The language-model entry is PINNED (note-learning-and-styles plan Task 4.1,
2026-09-20): name, size and SHA-256 are imported from
``scribe_desktop.language_model`` (the runtime verifies the same pin at every
load) and the URL is recorded below. The file is ~2.3 GiB, so it is STREAMED
to ``language-model/<name>.gguf.candidate`` in 1 MiB reads with HTTP Range
resume of a partial candidate, a free-space precondition before any byte is
fetched, and every read bounded by the pinned size (a declared Content-Length
is checked but never trusted as an allocation bound); the candidate is
promoted to ``<name>.gguf`` only after its size AND SHA-256 match the pin. A
run without ``--only`` includes it.

Usage:
    .venv\\Scripts\\python.exe scripts\\setup-models.py [--only NAME]
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import urllib.request
from pathlib import Path
from typing import Any

# Pinned silero-vad release (v5.1.2) -- ONNX model served from the GitHub tag.
SILERO_VAD_URL = (
    "https://raw.githubusercontent.com/snakers4/silero-vad/"
    "v5.1.2/src/silero_vad/data/silero_vad.onnx"
)
# Trust-on-first-download pin, computed 2026-07-26 from the v5.1.2 tag.
SILERO_VAD_SHA256 = "2623a2953f6ff3d2c1e61740c6cdb7168133479b267dfef114a4a3cc5bdd788f"

# Whisper candidates for the Step D6 benchmark (Systran CTranslate2 conversions).
# Each pinned to an immutable commit SHA (recorded 2026-07-27) so model bytes
# cannot change between installations without review.
WHISPER_CANDIDATES: dict[str, tuple[str, str]] = {
    "small": (
        "Systran/faster-whisper-small",
        "536b0662742c02347bc0e980a01041f333bce120",
    ),
    "distil-small.en": (
        "Systran/faster-distil-whisper-small.en",
        "ef77d90526ccd62cde3808ee70626a01e5cf83e4",
    ),
    "distil-medium.en": (
        "Systran/faster-distil-whisper-medium.en",
        "80ddfce281f77766d8943d63109199fc8145dfa5",
    ),
    "medium": (
        "Systran/faster-whisper-medium",
        "08e178d48790749d25932bbc082711ddcfdfbc4f",
    ),
}

# Snapshot completeness is defined ONCE, in scribe_desktop.benchmark (smoke
# round 21): model.bin + config.json + (tokenizer.json OR vocabulary.txt OR
# vocabulary.json) — both CT2 export layouts are valid. The skip guard, the
# post-download assert, the benchmark, the UI model report and the
# transcription provider all share that checker.
from scribe_desktop.benchmark import (  # noqa: E402
    default_models_root,
    whisper_snapshot_complete,
    whisper_snapshot_missing,
)

# The speaker-embedding pin is defined ONCE, in scribe_desktop.speaker_embedding
# (practitioner-profile plan Task 1.1): the runtime embedder verifies the
# model file against the SAME name, subdirectory, size and SHA-256 this script
# downloads and promotes by, so the two cannot drift.
from scribe_desktop.speaker_embedding import (  # noqa: E402
    SPEAKER_MODEL_NAME,
    SPEAKER_MODEL_SHA256,
    SPEAKER_MODEL_SIZE_BYTES,
    SPEAKER_MODEL_SUBDIR,
    sha256_of_file,
)

# The language-model pin is likewise defined ONCE, in
# scribe_desktop.language_model (note-learning-and-styles plan Task 4.1): the
# runtime verifies the SAME name, subdirectory, size and SHA-256 this script
# downloads and promotes by, at every load.
from scribe_desktop.language_model import (  # noqa: E402
    LANGUAGE_MODEL_FILENAME,
    LANGUAGE_MODEL_REPO,
    LANGUAGE_MODEL_SHA256,
    LANGUAGE_MODEL_SIZE_BYTES,
    LANGUAGE_MODEL_SUBDIR,
)

# Speaker-embedding model (practitioner-profile plan, Phase 0 Tasks 0.3-0.5):
# the WeSpeaker VoxCeleb ResNet34-LM ONNX export (80-bin Kaldi fbank in,
# 256-dim embedding out). Trust-on-first-download pin, computed
# 2026-09-15 from the practitioner's Task 0.4 fetch of the URL below (26530309
# bytes) and confirmed by the D-P1 smoke (same-speaker cosine 0.85-0.89,
# different-speaker -0.01-0.01). The Hugging Face `resolve/main` URL is not an
# immutable ref - the SHA-256 is what pins the bytes, exactly as for silero.
# An EMPTY SHA-256 pin would put the entry back into candidate mode (see the
# module docstring); a filled pin means verify-and-promote. The URL is the
# only setup-time-only constant; the rest mirror the runtime module's.
SPEAKER_EMBEDDING_NAME = SPEAKER_MODEL_NAME
SPEAKER_EMBEDDING_URL = (
    "https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34-LM/"
    "resolve/main/voxceleb_resnet34_LM.onnx"
)
SPEAKER_EMBEDDING_SIZE_BYTES = SPEAKER_MODEL_SIZE_BYTES  # 25.3 MiB, recorded at Task 0.4
SPEAKER_EMBEDDING_EXPECTED_SIZE = (
    f"{SPEAKER_EMBEDDING_SIZE_BYTES} bytes (25.3 MiB), recorded 2026-09-15"
)
SPEAKER_EMBEDDING_SHA256 = SPEAKER_MODEL_SHA256
# Anything smaller than this is an error page or a stub, not a speaker model:
# refuse it instead of reporting a digest the practitioner would then pin.
SPEAKER_EMBEDDING_MIN_BYTES = 1024 * 1024

# Language model (note-learning-and-styles plan Phase 4, Task 4.1): the
# Qwen3-4B-Instruct-2507 GGUF at Q4_K_M behind the two prose writing styles.
# The pin - size AND SHA-256 - is single-sourced from the runtime module
# (scribe_desktop.language_model), which verifies the very same values at
# every load, so the two surfaces cannot drift. The URL below is the only
# setup-time-only constant. The Hugging Face `resolve/main` URL is NOT an
# immutable ref - the digest is what pins the bytes, exactly as for silero and
# the speaker embedding. The quantiser `unsloth` is a third party (the
# upstream model is Qwen's, Apache-2.0); its bytes are trusted only because
# they hash to the recorded pin.
LANGUAGE_MODEL_URL = (
    f"https://huggingface.co/{LANGUAGE_MODEL_REPO}/resolve/main/{LANGUAGE_MODEL_FILENAME}"
)
LANGUAGE_MODEL_STREAM_CHUNK = 1024 * 1024  # one bounded read
LANGUAGE_MODEL_PROGRESS_EVERY = 64 * 1024 * 1024  # print progress per this many bytes
# Headroom demanded on top of the bytes still to fetch, so a download cannot
# fill the disk the app itself writes sessions to.
LANGUAGE_MODEL_FREE_SPACE_MARGIN = 256 * 1024 * 1024


def models_root() -> Path:
    # Single-sourced with the runtime (LOW-014): setup must download into the
    # SAME cache the app reads, so the root is never re-implemented here.
    try:
        return default_models_root()
    except RuntimeError as exc:  # LOCALAPPDATA unset — Windows-only script
        raise SystemExit(f"{exc}; this script is Windows-only.") from exc


def dir_size_bytes(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def human(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GiB"


# Belongs with the language-model constants above; defined here because it
# renders through `human`, which is declared on the line above.
LANGUAGE_MODEL_EXPECTED_SIZE = (
    f"{LANGUAGE_MODEL_SIZE_BYTES} bytes ({human(LANGUAGE_MODEL_SIZE_BYTES)}), "
    "recorded 2026-09-20"
)


def fetch_silero_vad(root: Path) -> None:
    target = root / "silero-vad" / "silero_vad.onnx"
    if target.exists() and target.stat().st_size > 0:
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest == SILERO_VAD_SHA256:
            print(f"[skip] silero-vad already present ({human(target.stat().st_size)})")
            return
        print("[redo] silero-vad present but checksum mismatch; re-downloading")
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"[get ] silero-vad <- {SILERO_VAD_URL}")
    tmp = target.with_suffix(".onnx.part")
    with urllib.request.urlopen(SILERO_VAD_URL) as resp:  # noqa: S310 - pinned https URL
        data = resp.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SILERO_VAD_SHA256:
        raise SystemExit(
            f"silero-vad checksum mismatch: expected {SILERO_VAD_SHA256}, got {digest}"
        )
    tmp.write_bytes(data)
    tmp.replace(target)
    print(f"[ok  ] silero-vad ({human(target.stat().st_size)}) -> {target}")


def fetch_whisper(root: Path, name: str, repo_id: str, revision: str) -> None:
    from huggingface_hub import snapshot_download  # network-capable; setup-only

    target = root / "whisper" / name
    if whisper_snapshot_complete(target):
        print(f"[skip] whisper/{name} already present ({human(dir_size_bytes(target))})")
        return
    if target.exists():
        print(f"[redo] whisper/{name} present but incomplete; resuming download")
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"[get ] whisper/{name} <- {repo_id}@{revision[:12]}")
    snapshot_download(
        repo_id=repo_id,
        revision=revision,
        local_dir=str(target),
        allow_patterns=["*.bin", "*.json", "*.txt"],
    )
    missing = whisper_snapshot_missing(target)
    if missing:
        raise SystemExit(
            f"whisper/{name} download finished but required files are missing "
            f"({', '.join(missing)}); re-run setup"
        )
    print(f"[ok  ] whisper/{name} ({human(dir_size_bytes(target))}) -> {target}")


def speaker_embedding_paths(root: Path) -> tuple[Path, Path]:
    """``(promoted, candidate)`` paths: ``<name>.onnx`` and ``<name>.onnx.candidate``
    under the runtime's subdirectory (``speaker_embedding.default_speaker_model_path``
    resolves the same promoted path from the same constants)."""
    target = root / SPEAKER_MODEL_SUBDIR / f"{SPEAKER_EMBEDDING_NAME}.onnx"
    return target, target.with_name(f"{SPEAKER_EMBEDDING_NAME}.onnx.candidate")


def speaker_embedding_pinned() -> bool:
    return bool(SPEAKER_EMBEDDING_SHA256)


class _HttpsOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse any redirect whose target is not ``https://`` BEFORE the hop is
    fetched. The stdlib default follows ``http://`` targets, which would move
    the candidate's bytes - the very bytes Task 0.5 pins - onto an
    unauthenticated transport (peer round 6 PR-HIGH-002). ``redirect_request``
    receives the ABSOLUTE target (``http_error_302`` joins a relative
    ``Location`` first), so every hop of a chain is checked here. Ordinary
    https -> https redirects (Hugging Face ``resolve`` -> CDN, GitHub
    releases) pass unchanged. Installed for the speaker-embedding helper and,
    through the subclass below, the language-model stream; silero's
    already-pinned fetch is untouched.

    ``label`` names the entry in the refusal so one implementation serves both
    downloads (Task 4.1) without either message going vague."""

    label = "speaker-embedding"

    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> Any:
        if not str(newurl).lower().startswith("https://"):
            raise SystemExit(
                f"{self.label} download refused: {req.full_url} redirects to the "
                f"non-https target {newurl!r}; the candidate must arrive over https on "
                "every hop, so nothing was fetched from it and no candidate was written"
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _LanguageModelRedirectHandler(_HttpsOnlyRedirectHandler):
    """The same https-only policy for the language-model stream."""

    label = "language-model"


def _download_speaker_embedding(url: str) -> bytes:
    if not url.startswith("https://"):
        raise SystemExit(f"speaker-embedding URL must be https://, got {url!r}")
    print(f"[get ] speaker-embedding <- {url}")
    # https is enforced on the supplied URL above and on every redirect hop by
    # the handler; build_opener swaps the default redirect handler for ours.
    opener = urllib.request.build_opener(_HttpsOnlyRedirectHandler)
    with opener.open(url) as resp:  # noqa: S310
        data: bytes = resp.read()
    if len(data) < SPEAKER_EMBEDDING_MIN_BYTES:
        raise SystemExit(
            f"speaker-embedding download is only {human(len(data))} - that is an error "
            "page or a stub, not a model; check the URL (expected "
            f"{SPEAKER_EMBEDDING_EXPECTED_SIZE})"
        )
    return data


def _write_atomically(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".part")
    tmp.write_bytes(data)
    tmp.replace(target)


def _report_candidate(candidate: Path) -> None:
    size = candidate.stat().st_size
    print(f"[cand] speaker-embedding candidate: {candidate}")
    print(f"       size    : {size} bytes ({human(size)}; {SPEAKER_EMBEDDING_EXPECTED_SIZE})")
    print(f"       sha256  : {sha256_of_file(candidate)}")
    print(
        "       NOT promoted (candidate mode - no pin yet). Report the size and SHA-256 "
        "for the pin step; the smoke reads this .candidate path directly."
    )


def fetch_speaker_embedding(root: Path, *, candidate_url: str | None = None) -> None:
    """Candidate mode (no pin): fetch to ``.onnx.candidate`` and report size +
    SHA-256, never promoting. Pinned mode: verify (a present candidate or a
    fresh download) against the pin and write ``<name>.onnx``; a mismatch
    leaves the candidate in place, un-promoted, and exits with the digests."""
    target, candidate = speaker_embedding_paths(root)

    if speaker_embedding_pinned():
        if candidate_url is not None:
            raise SystemExit(
                "--candidate-url is refused: the speaker-embedding model is pinned "
                "(URL, size and SHA-256 recorded in this script); re-run without it"
            )
        if target.exists() and target.stat().st_size > 0:
            if sha256_of_file(target) == SPEAKER_EMBEDDING_SHA256:
                print(
                    f"[skip] speaker-embedding already present ({human(target.stat().st_size)})"
                )
                return
            print("[redo] speaker-embedding present but checksum mismatch; re-downloading")
        if candidate.exists() and candidate.stat().st_size > 0:
            digest = sha256_of_file(candidate)
            if digest != SPEAKER_EMBEDDING_SHA256:
                raise SystemExit(
                    "speaker-embedding candidate checksum mismatch: expected "
                    f"{SPEAKER_EMBEDDING_SHA256}, got {digest}; the candidate at "
                    f"{candidate} is left un-promoted - re-fetch it or fix the pin"
                )
            candidate.replace(target)
            print(f"[ok  ] speaker-embedding promoted from candidate -> {target}")
            print(f"       size    : {target.stat().st_size} bytes ({human(target.stat().st_size)})")
            print(f"       sha256  : {digest} (verified against the pin)")
            return
        if not SPEAKER_EMBEDDING_URL:
            raise SystemExit(
                "speaker-embedding is pinned but has no URL recorded - the pin step "
                "must record SPEAKER_EMBEDDING_URL beside the SHA-256"
            )
        data = _download_speaker_embedding(SPEAKER_EMBEDDING_URL)
        digest = hashlib.sha256(data).hexdigest()
        if digest != SPEAKER_EMBEDDING_SHA256:
            raise SystemExit(
                "speaker-embedding checksum mismatch: expected "
                f"{SPEAKER_EMBEDDING_SHA256}, got {digest}"
            )
        _write_atomically(target, data)
        print(f"[ok  ] speaker-embedding ({human(target.stat().st_size)}) -> {target}")
        return

    # Candidate mode: no pin yet, so nothing is ever written to <name>.onnx.
    if candidate.exists() and candidate.stat().st_size > 0:
        print(
            "[skip] speaker-embedding candidate already downloaded (to fetch a DIFFERENT "
            "candidate, delete this .candidate file and re-run with its --candidate-url)"
        )
        _report_candidate(candidate)
        return
    url = candidate_url or SPEAKER_EMBEDDING_URL
    if not url:
        raise SystemExit(
            "no URL is recorded for the unpinned speaker-embedding candidate. Pass it "
            "explicitly:\n"
            "    setup-models.py --only speaker-embedding --candidate-url https://...\n"
            "(the pin step then records the URL, size and SHA-256 in this script)"
        )
    data = _download_speaker_embedding(url)
    _write_atomically(candidate, data)
    _report_candidate(candidate)


# --- the language model (note-learning-and-styles plan Task 4.1) -----------------


def language_model_paths(root: Path) -> tuple[Path, Path]:
    """``(promoted, candidate)`` paths: ``<name>.gguf`` and
    ``<name>.gguf.candidate`` under the runtime's subdirectory
    (``language_model.default_language_model_path`` resolves the same promoted
    path from the same constants)."""
    target = root / LANGUAGE_MODEL_SUBDIR / LANGUAGE_MODEL_FILENAME
    return target, target.with_name(f"{LANGUAGE_MODEL_FILENAME}.candidate")


def _require_free_space(directory: Path, needed: int) -> None:
    """Refuse BEFORE a single byte is fetched unless the volume holding
    ``directory`` has room for ``needed`` bytes plus the margin: a 2.3 GiB
    download that fills the disk would leave the app unable to write a
    session."""
    directory.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(directory).free
    if free < needed + LANGUAGE_MODEL_FREE_SPACE_MARGIN:
        raise SystemExit(
            f"language-model needs {needed} bytes ({human(needed)}) plus a "
            f"{LANGUAGE_MODEL_FREE_SPACE_MARGIN} byte "
            f"({human(LANGUAGE_MODEL_FREE_SPACE_MARGIN)}) margin at {directory}, but only "
            f"{free} bytes ({human(free)}) are free; nothing was fetched"
        )


def _stream_language_model(url: str, candidate: Path, *, expected_size: int) -> None:
    """Stream the pinned GGUF to ``candidate`` in bounded reads, resuming a
    partial candidate with an HTTP Range request. Nothing here trusts the
    server: a declared Content-Length must agree with the pin (and is never
    used as an allocation bound), every read is ``LANGUAGE_MODEL_STREAM_CHUNK``
    bytes at most, a body that runs past the pinned size deletes the candidate,
    and a short body KEEPS it so the next run resumes. The caller verifies the
    digest before anything is promoted."""
    if not url.startswith("https://"):
        raise SystemExit(f"language-model URL must be https://, got {url!r}")
    have = candidate.stat().st_size if candidate.exists() else 0
    if have > expected_size:
        raise SystemExit(
            f"language-model candidate at {candidate} is {have} bytes, larger than the "
            f"pinned size {expected_size}; delete it and re-run"
        )
    if have == expected_size:
        return  # complete already - no network; the caller verifies the digest
    request = urllib.request.Request(url)  # noqa: S310 - https enforced above
    if have > 0:
        request.add_header("Range", f"bytes={have}-")
        print(f"[get ] language-model resuming at {have} bytes")
    else:
        print(f"[get ] language-model <- {url}")
    # https is enforced on the supplied URL above and on every redirect hop by
    # the handler; build_opener swaps the default redirect handler for ours.
    opener = urllib.request.build_opener(_LanguageModelRedirectHandler)
    start = 0
    written = 0
    oversize = False
    with opener.open(request) as resp:  # noqa: S310
        status = getattr(resp, "status", 200)
        length = resp.headers.get("Content-Length")
        if have > 0 and status == 206:
            start, mode = have, "ab"
        elif status == 200:
            start, mode = 0, "wb"
            if have > 0:
                print("[redo] language-model server ignored the resume; starting over")
        else:
            raise SystemExit(
                f"language-model download refused: the server answered status {status}, "
                "not 200 or 206; nothing was written"
            )
        try:
            declared = None if length is None else int(length)
        except ValueError:
            raise SystemExit(
                f"language-model download refused: Content-Length {length!r} is not a "
                "number; nothing was written"
            ) from None
        if declared is not None and declared != expected_size - start:
            raise SystemExit(
                f"language-model Content-Length {length} does not match the pinned size "
                f"({expected_size - start} bytes expected from offset {start}); this is "
                "not the pinned file; nothing was written"
            )
        # Progress is reported against the total, so a resumed download does
        # not replay the milestones it already passed.
        next_progress = start + LANGUAGE_MODEL_PROGRESS_EVERY
        with candidate.open(mode) as handle:
            while True:
                chunk = resp.read(LANGUAGE_MODEL_STREAM_CHUNK)
                if not chunk:
                    break
                handle.write(chunk)
                written += len(chunk)
                if start + written > expected_size:
                    oversize = True
                    break
                if start + written >= next_progress:
                    print(
                        f"[    ] language-model {human(start + written)} / "
                        f"{human(expected_size)}"
                    )
                    next_progress += LANGUAGE_MODEL_PROGRESS_EVERY
    if oversize:
        candidate.unlink()
        raise SystemExit(
            f"language-model download body exceeds the pinned size {expected_size} bytes; "
            "the candidate was deleted"
        )
    if start + written < expected_size:
        raise SystemExit(
            f"language-model connection ended at {start + written} of {expected_size} "
            "bytes; re-run to resume"
        )


def fetch_language_model(root: Path) -> None:
    """Verify-and-promote, exactly like the pinned speaker-embedding branch,
    but over a streamed download: a present file that matches the pin is
    skipped, a present file that does not is re-downloaded, a full-size
    candidate is verified and promoted (or refused and left), and anything
    else is streamed, size-checked, digest-checked and only then promoted."""
    target, candidate = language_model_paths(root)

    if target.exists():
        size = target.stat().st_size
        if size == LANGUAGE_MODEL_SIZE_BYTES and sha256_of_file(target) == LANGUAGE_MODEL_SHA256:
            print(f"[skip] language-model already present ({human(size)})")
            return
        print("[redo] language-model present but not the pinned file; re-downloading")
        target.unlink()

    have = candidate.stat().st_size if candidate.exists() else 0
    if have == LANGUAGE_MODEL_SIZE_BYTES:
        digest = sha256_of_file(candidate)
        if digest != LANGUAGE_MODEL_SHA256:
            raise SystemExit(
                "language-model candidate checksum mismatch: expected "
                f"{LANGUAGE_MODEL_SHA256}, got {digest}; the candidate at {candidate} is "
                "left un-promoted - delete it to re-download"
            )
        candidate.replace(target)
        print(f"[ok  ] language-model promoted from candidate -> {target}")
        print(f"       size    : {target.stat().st_size} bytes ({human(target.stat().st_size)})")
        print(f"       sha256  : {digest} (verified against the pin)")
        return

    _require_free_space(target.parent, LANGUAGE_MODEL_SIZE_BYTES - have)
    _stream_language_model(
        LANGUAGE_MODEL_URL, candidate, expected_size=LANGUAGE_MODEL_SIZE_BYTES
    )
    size = candidate.stat().st_size
    if size != LANGUAGE_MODEL_SIZE_BYTES:
        raise SystemExit(
            f"language-model candidate at {candidate} is {size} bytes, not the pinned "
            f"{LANGUAGE_MODEL_SIZE_BYTES}; delete it to re-download"
        )
    digest = sha256_of_file(candidate)
    if digest != LANGUAGE_MODEL_SHA256:
        raise SystemExit(
            "language-model checksum mismatch: expected "
            f"{LANGUAGE_MODEL_SHA256}, got {digest}; the candidate at {candidate} is left "
            "in place - delete it to re-download"
        )
    candidate.replace(target)
    print(f"[ok  ] language-model ({human(target.stat().st_size)}) -> {target}")
    print(f"       size    : {target.stat().st_size} bytes ({human(target.stat().st_size)})")
    print(f"       sha256  : {digest} (verified against the pin)")


def valid_only_names() -> set[str]:
    return {"silero-vad", "speaker-embedding", "language-model", *WHISPER_CANDIDATES}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--only",
        help="download only one entry: 'silero-vad', 'speaker-embedding', "
        "'language-model' or a whisper candidate name "
        f"({', '.join(WHISPER_CANDIDATES)})",
    )
    parser.add_argument(
        "--candidate-url",
        metavar="URL",
        help="https URL of the speaker-embedding CANDIDATE (only with --only "
        "speaker-embedding, only while the entry is unpinned)",
    )
    args = parser.parse_args(argv)

    valid_only = valid_only_names()
    if args.only is not None and args.only not in valid_only:
        parser.error(
            f"unknown --only value {args.only!r}; choose one of: "
            + ", ".join(sorted(valid_only))
        )
    if args.candidate_url is not None and args.only != "speaker-embedding":
        parser.error("--candidate-url is only meaningful with --only speaker-embedding")

    root = models_root()
    root.mkdir(parents=True, exist_ok=True)
    print(f"Model cache: {root}")

    if args.only is None or args.only == "silero-vad":
        fetch_silero_vad(root)
    for name, (repo_id, revision) in WHISPER_CANDIDATES.items():
        if args.only is None or args.only == name:
            fetch_whisper(root, name, repo_id, revision)
    if args.only == "speaker-embedding":
        fetch_speaker_embedding(root, candidate_url=args.candidate_url)
    elif args.only is None:
        if speaker_embedding_pinned():
            fetch_speaker_embedding(root)
        else:
            print(
                "[skip] speaker-embedding: candidate mode (no pin yet) - fetch it "
                "explicitly with --only speaker-embedding --candidate-url URL"
            )
    if args.only is None or args.only == "language-model":
        fetch_language_model(root)

    total = dir_size_bytes(root)
    print(f"Total model cache size: {human(total)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
