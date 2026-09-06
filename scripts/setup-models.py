"""One-time ML model setup for Cliniko Scribe.

This script is the ONLY sanctioned network user in the project (see
docs/security/data-flow-map.md and the Phase 2 plan). It runs as a separate,
explicit setup step -- never at runtime. Runtime processes load models from
the local cache with network access disabled and asserted off.

Downloads into %LOCALAPPDATA%\\ClinikoScribe\\models\\:
  - silero-vad ONNX model (voice activity detection)
  - faster-whisper (CTranslate2) model candidates for the Step D6 benchmark
  - speaker-embedding ONNX model (voice enrolment; practitioner-profile plan)

Idempotent: existing complete downloads are skipped. No clinical data is
involved at any point.

The speaker-embedding entry has two modes, decided by its SHA-256 pin:
  - CANDIDATE mode (pin EMPTY, the state until Task 0.5 of the
    practitioner-profile plan): ``--only speaker-embedding`` downloads to
    ``speaker-embedding/<name>.onnx.candidate``, prints the size and SHA-256
    for the practitioner's report, and does NOT promote the file. A run
    without ``--only`` skips this entry (printed, never silent). No URL is
    recorded yet either: pass ``--candidate-url https://...`` (Task 0.4). The
    URL must be https and so must EVERY redirect hop - a redirect to http is
    refused before it is fetched, because the bytes reported here are the
    ones the pin step trusts.
  - PINNED mode (pin set): an existing ``.onnx.candidate`` is verified
    against the pin and promoted to ``<name>.onnx`` (Task 0.6); otherwise
    the file is downloaded, verified and written, exactly like silero-vad.
    ``--candidate-url`` is refused once the entry is pinned.

Usage:
    .venv\\Scripts\\python.exe scripts\\setup-models.py [--only NAME]
    .venv\\Scripts\\python.exe scripts\\setup-models.py --only speaker-embedding --candidate-url URL
"""

from __future__ import annotations

import argparse
import hashlib
import os
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

# Speaker-embedding candidate (practitioner-profile plan, Phase 0 Task 0.3).
# The plan's first candidate is the WeSpeaker VoxCeleb ResNet34-LM ONNX export
# (about 26 MB; 80-bin Kaldi fbank in, 256-dim embedding out). The planning
# session never fetched it, so NOTHING below is verified yet: the URL is to be
# supplied by the practitioner on the command line (--candidate-url) at Task
# 0.4, and Task 0.5 records the URL, size and SHA-256 here from that report.
# An EMPTY SHA-256 pin is what puts the entry in candidate mode (see the
# module docstring); filling it switches the entry to verify-and-promote.
SPEAKER_EMBEDDING_NAME = "wespeaker-voxceleb-resnet34-LM"
SPEAKER_EMBEDDING_URL = ""  # TO BE SUPPLIED by the practitioner (Task 0.4 / pinned at 0.5)
SPEAKER_EMBEDDING_EXPECTED_SIZE = "about 26 MiB (plan finding, unverified until Task 0.4)"
SPEAKER_EMBEDDING_SHA256 = ""  # EMPTY = candidate mode; Task 0.5 fills it
# Anything smaller than this is an error page or a stub, not a speaker model:
# refuse it instead of reporting a digest the practitioner would then pin.
SPEAKER_EMBEDDING_MIN_BYTES = 1024 * 1024

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
    """``(promoted, candidate)`` paths: ``<name>.onnx`` and ``<name>.onnx.candidate``."""
    target = root / "speaker-embedding" / f"{SPEAKER_EMBEDDING_NAME}.onnx"
    return target, target.with_name(f"{SPEAKER_EMBEDDING_NAME}.onnx.candidate")


def speaker_embedding_pinned() -> bool:
    return bool(SPEAKER_EMBEDDING_SHA256)


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class _HttpsOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse any redirect whose target is not ``https://`` BEFORE the hop is
    fetched. The stdlib default follows ``http://`` targets, which would move
    the candidate's bytes - the very bytes Task 0.5 pins - onto an
    unauthenticated transport (peer round 6 PR-HIGH-002). ``redirect_request``
    receives the ABSOLUTE target (``http_error_302`` joins a relative
    ``Location`` first), so every hop of a chain is checked here. Ordinary
    https -> https redirects (Hugging Face ``resolve`` -> CDN, GitHub
    releases) pass unchanged. Installed for the speaker-embedding helper
    only; silero's already-pinned fetch is untouched."""

    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> Any:
        if not str(newurl).lower().startswith("https://"):
            raise SystemExit(
                f"speaker-embedding download refused: {req.full_url} redirects to the "
                f"non-https target {newurl!r}; the candidate must arrive over https on "
                "every hop, so nothing was fetched from it and no candidate was written"
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


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
    print(f"       sha256  : {_sha256_of(candidate)}")
    print(
        "       NOT promoted (candidate mode - no pin yet). Report the size and SHA-256 "
        "on Task 0.4; the smoke reads this .candidate path directly."
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
            if _sha256_of(target) == SPEAKER_EMBEDDING_SHA256:
                print(
                    f"[skip] speaker-embedding already present ({human(target.stat().st_size)})"
                )
                return
            print("[redo] speaker-embedding present but checksum mismatch; re-downloading")
        if candidate.exists() and candidate.stat().st_size > 0:
            digest = _sha256_of(candidate)
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
            "no URL is recorded for the speaker-embedding candidate (the plan pinned "
            "none). Pass it explicitly:\n"
            "    setup-models.py --only speaker-embedding --candidate-url https://...\n"
            "(practitioner-profile plan Task 0.4; the URL is pinned here at Task 0.5)"
        )
    data = _download_speaker_embedding(url)
    _write_atomically(candidate, data)
    _report_candidate(candidate)


def valid_only_names() -> set[str]:
    return {"silero-vad", "speaker-embedding", *WHISPER_CANDIDATES}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--only",
        help="download only one entry: 'silero-vad', 'speaker-embedding' or a whisper "
        f"candidate name ({', '.join(WHISPER_CANDIDATES)})",
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

    total = dir_size_bytes(root)
    print(f"Total model cache size: {human(total)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
