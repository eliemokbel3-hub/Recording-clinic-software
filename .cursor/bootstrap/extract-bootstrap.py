#!/usr/bin/env python3
"""Bootstrap payload extractor (SECTION 0 -- INSTALLER).

Extracts every SECTION 0-4 '## FILE:' payload embedded in bootstrap.md and
writes it byte-exactly into the project tree, then verifies each written
file against the PAYLOAD MANIFEST section at the end of bootstrap.md.

Behaviour contract:
- Read-normalizes CRLF to LF on bootstrap.md before parsing and hashing
  (the file travels by upload/copy; any transport leg can convert line
  endings). Payload bytes are written exactly: UTF-8, no BOM, LF newlines,
  binary-mode writes.
- NEVER writes SECTION 5 templates (AGENTS.md, CLAUDE.md, CHANGELOG.md,
  .env.example) in any mode. Those stay agent-handled.
- Re-extracts its own payload (.cursor/bootstrap/extract-bootstrap.py), so a
  mistyped-but-runnable hand-typed copy heals itself; a broken copy fails
  loudly -- re-compare your copy with the SECTION 0 payload and retry.
- Verifies every written file's byte count and sha256 against the embedded
  manifest; prints a per-file OK/FAIL report; exits non-zero on any FAIL.
- Deterministic and idempotent: same bootstrap in, same files out;
  re-running is always safe (overwrite semantics for Sections 0-4).

Usage (from the project root; use plain 'python' if 'python3' is absent):
    python3 .cursor/bootstrap/extract-bootstrap.py
    python3 .cursor/bootstrap/extract-bootstrap.py --bootstrap bootstrap.md --target .

This file is ASCII-only and contains no triple-backtick sequences (fence
tokens are built programmatically), so it stays safe to hand-type and to
embed as a fenced payload.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

FENCE = "`" * 3  # never a literal fence in this source
SECTION_RE = re.compile(r"^# SECTION (\d+)")
FILE_MARKER_RE = re.compile(r"^## FILE: `([^`]+)`$")
MANIFEST_HEADING = "## PAYLOAD MANIFEST"
MANIFEST_LINE_RE = re.compile(r"^MANIFEST: ([0-9a-f]{64}) (\d+) (.+)$")
MAX_SECTION = 4  # SECTION 5 templates are agent-handled and never extracted


def normalize(raw: bytes) -> str:
    """Decode UTF-8 (tolerating a transport-added BOM) and normalize CRLF to LF."""
    return raw.decode("utf-8-sig").replace("\r\n", "\n")


def parse_payloads(text: str) -> list[tuple[str, str]]:
    """Return (path, payload_text) for every SECTION 0-4 FILE block, in order.

    Any line-start fence after a FILE marker opens the payload; the matching
    closing fence is found by depth-tracking nested fences (same logic as
    scripts/sync-bootstrap-payload.py), so payloads that contain their own
    fenced blocks are extracted to the LAST closing fence, never truncated.
    """
    lines = text.split("\n")
    payloads: list[tuple[str, str]] = []
    section = None
    i = 0
    n = len(lines)
    while i < n:
        sec = SECTION_RE.match(lines[i])
        if sec:
            section = int(sec.group(1))
            i += 1
            continue
        mark = FILE_MARKER_RE.match(lines[i])
        if not (mark and section is not None and section <= MAX_SECTION):
            i += 1
            continue
        path = mark.group(1)
        j = i + 1
        while j < n and not lines[j].startswith(FENCE):
            j += 1
        if j >= n:
            raise SystemExit("ERROR: no opening fence after FILE marker for " + path)
        depth = 1
        end = None
        for k in range(j + 1, n):
            line = lines[k]
            if line == FENCE:
                depth -= 1
                if depth == 0:
                    end = k
                    break
            elif line.startswith(FENCE) and len(line) > 3:
                depth += 1
        if end is None:
            raise SystemExit("ERROR: no closing fence for " + path)
        payload = "\n".join(lines[j + 1 : end])
        if payload:
            payload += "\n"
        payloads.append((path, payload))
        i = end + 1
    return payloads


def parse_manifest(text: str) -> dict[str, tuple[int, str]]:
    """Return {path: (bytes, sha256)} from the PAYLOAD MANIFEST section.

    Anchors on the LAST heading occurrence (end-of-file placement), matching
    the sync script's generator.
    """
    idx = text.rfind("\n" + MANIFEST_HEADING + "\n")
    if idx < 0:
        raise SystemExit(
            "ERROR: no " + MANIFEST_HEADING + " section found in the bootstrap file"
        )
    entries: dict[str, tuple[int, str]] = {}
    for line in text[idx:].split("\n"):
        m = MANIFEST_LINE_RE.match(line)
        if m:
            entries[m.group(3)] = (int(m.group(2)), m.group(1))
    if not entries:
        raise SystemExit("ERROR: PAYLOAD MANIFEST section has no entries")
    return entries


def safe_relpath(path: str) -> Path:
    """Reject absolute or parent-escaping payload paths."""
    p = Path(path)
    if p.is_absolute() or ".." in p.parts:
        raise SystemExit("ERROR: unsafe payload path " + path)
    return p


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Extract and verify the SECTION 0-4 payloads from bootstrap.md."
    )
    ap.add_argument("--bootstrap", default="bootstrap.md", help="path to bootstrap.md")
    ap.add_argument("--target", default=".", help="directory to extract into")
    args = ap.parse_args()

    bootstrap = Path(args.bootstrap)
    target = Path(args.target)
    if not bootstrap.is_file():
        print("ERROR: bootstrap file not found: " + str(bootstrap), file=sys.stderr)
        return 2
    text = normalize(bootstrap.read_bytes())
    payloads = parse_payloads(text)
    manifest = parse_manifest(text)
    if not payloads:
        print("ERROR: no SECTION 0-4 FILE payloads found", file=sys.stderr)
        return 2

    failures = 0
    seen = set()
    for path, payload in payloads:
        seen.add(path)
        out = target / safe_relpath(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "wb") as fh:
            fh.write(payload.encode("utf-8"))
        data = out.read_bytes()  # verify what actually landed on disk
        digest = hashlib.sha256(data).hexdigest()
        expected = manifest.get(path)
        if expected is None:
            print("FAIL " + path + ": payload has no manifest entry")
            failures += 1
        elif expected != (len(data), digest):
            print(
                "FAIL " + path + ": bytes/sha256 mismatch vs manifest (wrote "
                + str(len(data)) + " bytes, expected " + str(expected[0]) + ")"
            )
            failures += 1
        else:
            print("OK   " + path + " (" + str(len(data)) + " bytes)")

    for path in sorted(manifest):
        if path not in seen:
            print("FAIL " + path + ": manifest entry has no extracted payload")
            failures += 1

    print("")
    print(
        "Extracted " + str(len(payloads)) + " payloads into " + str(target)
        + "; failures: " + str(failures)
    )
    if failures:
        print("One or more payloads FAILED verification.")
        print("If you hand-typed this script, re-compare your copy with the")
        print("SECTION 0 payload in bootstrap.md and rerun (a successful run")
        print("self-heals its own copy).")
        return 1
    print("All payloads verified against the embedded manifest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
