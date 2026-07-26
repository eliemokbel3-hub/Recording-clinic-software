"""One-time ML model setup for Cliniko Scribe.

This script is the ONLY sanctioned network user in the project (see
docs/security/data-flow-map.md and the Phase 2 plan). It runs as a separate,
explicit setup step -- never at runtime. Runtime processes load models from
the local cache with network access disabled and asserted off.

Downloads into %LOCALAPPDATA%\\ClinikoScribe\\models\\:
  - silero-vad ONNX model (voice activity detection)
  - faster-whisper (CTranslate2) model candidates for the Step D6 benchmark

Idempotent: existing complete downloads are skipped. No clinical data is
involved at any point.

Usage:
    .venv\\Scripts\\python.exe scripts\\setup-models.py [--only NAME]
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import urllib.request
from pathlib import Path

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

# A CTranslate2 whisper snapshot is complete only with all of these present.
REQUIRED_WHISPER_FILES = ("model.bin", "config.json", "tokenizer.json")


def whisper_snapshot_complete(target: Path) -> bool:
    return all((target / f).is_file() and (target / f).stat().st_size > 0
               for f in REQUIRED_WHISPER_FILES)


def models_root() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise SystemExit("LOCALAPPDATA is not set; this script is Windows-only.")
    return Path(local_app_data) / "ClinikoScribe" / "models"


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
    if not whisper_snapshot_complete(target):
        raise SystemExit(
            f"whisper/{name} download finished but required files are missing "
            f"({', '.join(REQUIRED_WHISPER_FILES)}); re-run setup"
        )
    print(f"[ok  ] whisper/{name} ({human(dir_size_bytes(target))}) -> {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        help="download only one entry: 'silero-vad' or a whisper candidate name "
        f"({', '.join(WHISPER_CANDIDATES)})",
    )
    args = parser.parse_args()

    valid_only = {"silero-vad", *WHISPER_CANDIDATES}
    if args.only is not None and args.only not in valid_only:
        parser.error(
            f"unknown --only value {args.only!r}; choose one of: "
            + ", ".join(sorted(valid_only))
        )

    root = models_root()
    root.mkdir(parents=True, exist_ok=True)
    print(f"Model cache: {root}")

    if args.only is None or args.only == "silero-vad":
        fetch_silero_vad(root)
    for name, (repo_id, revision) in WHISPER_CANDIDATES.items():
        if args.only is None or args.only == name:
            fetch_whisper(root, name, repo_id, revision)

    total = dir_size_bytes(root)
    print(f"Total model cache size: {human(total)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
