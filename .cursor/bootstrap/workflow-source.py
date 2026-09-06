#!/usr/bin/env python3
"""Workflow source/version helper (SECTION 0 -- SHARED BY /update-workflow AND /start-session).

The SINGLE owner of: the configured workflow-source repo slug, the version
grammar (parse / compare / canonical serialization), bootstrap-header
extraction, installed-version marker read/write, and the update
transaction's inventory / snapshot / delta / restore pipeline
(the state contract: TOUCH inventory -> ACTUAL DELTA -> COMMITTABLE
DELTA (the actual delta minus gitignored paths) -> STAGED set; this
helper COMPUTES inventory/snapshot/delta only -- the check-ignore
split, staging, and the empty-COMMITTABLE routing stay CALLER-owned
per the update SKILL's Step 9).

Both installed skills CALL this helper instead of re-implementing any of
those rules; the source repo's sync verifier reuses the same grammar.
Changing the slug or the grammar here updates every consumer at once.

VERSIONED CLI/STATE CONTRACT (contract=1). This helper is itself an
extractor payload that an update run OVERWRITES mid-transaction. The
calling skill therefore PINS one implementation per invocation: it runs
'pin --state <dir>' first, then calls ONLY the pinned copy
(<state>/pinned-helper.py) for the entire transaction -- pre-check
through success, rollback, and cleanup. Newly extracted helper bytes
activate on the NEXT invocation only. The contract below is what an
older pinned copy may rely on across that replacement:

Subcommands (contract=1):
  contract                             print 'contract=1'
  slug                                 print the configured source slug
  parse <version>                      validate; print canonical spelling
  version-read --file <path>           the ONE raw VERSION-object framing
                                       boundary: exactly one line + one
                                       optional trailing LF (CR, extra or
                                       blank lines, surrounding whitespace,
                                       non-UTF-8 all malformed, exit 4);
                                       prints the canonical version
  compare <a> <b>                      print 'result=<older|same|newer> major=<yes|no>'
                                       (<a> relative to <b>; major=yes ONLY
                                       when <a>'s first component is GREATER
                                       -- a first-component INCREASE, per the
                                       MAJOR definition -- never for a
                                       cross-major downgrade)
  header --bootstrap <file>            print the canonical version parsed from
                                       the file's single '**Version:**' header
  marker-read --target <dir>           print 'state=valid version=<v> identity=<id|->'
                                       or 'state=absent' or 'state=malformed ...'
  marker-write --target <dir> --version <v> --identity <id>
                                       write '<v> <id>' + read-back verify
  pin --state <dir>                    copy THIS file to <state>/pinned-helper.py
                                       (0600, state dir 0700); print its sha256
  inventory --bootstrap <file> --target <dir> --state <dir>
                                       TOUCH inventory -> state: the UNION of
                                       manifest targets, discovered SECTION
                                       0-4 payload-block paths (equal sets on
                                       a well-formed bootstrap; the extractor
                                       writes payloads BEFORE its manifest
                                       lookup, so the union is the true write
                                       superset), and the marker path;
                                       containment lstat-walk (fail-closed)
  snapshot --state <dir>               record pre-state (existence/type/mode/
                                       bytes) of every inventoried path,
                                       tracked/untracked/ignored alike
  verify-containment --state <dir>     re-run the lstat walk (call immediately
                                       before the first real write)
  delta --state <dir>                  print 'changed|created|deleted <path>'
                                       for every inventoried path whose
                                       post-state differs from the snapshot
  restore --state <dir>                restore every inventoried path from the
                                       snapshot (bytes/type/mode identical;
                                       created files removed, created dirs
                                       pruned); verified after restore
  cleanup --state <dir>                remove the state dir on both exit paths

Exit codes (contract=1):
  0 success            1 operation/verification failure
  2 usage/state error  4 malformed version/header/marker/bootstrap input
  5 containment refusal (symlinked component, non-regular target)
Note: marker-read is a state QUERY -- printing 'state=malformed ...'
with exit 0 IS its successful result (the caller routes on the printed
state); exit 4 applies to malformed INPUT arguments (e.g. marker-write
--version) and to malformed bootstrap bytes/headers, always as a
controlled 'ERROR:' line, never an uncaught traceback.

State format (contract=1): <state>/state.json (0600) holding contract,
target, bootstrap, marker_path, inventory[], snapshot{path: {exists,
type, mode, size, sha256}}, dirs_preexist{dir: bool}; payload bytes at
<state>/blobs/<sha256> (0600). Temp copies and snapshot state carry
restrictive permissions and are removed by 'cleanup' on success and on
restored failure alike.

Grammar: a version is EXACTLY TWO unsigned decimal components in
canonical decimal spelling -- no leading zeros, no third component
('31.2.0' and '031.2' are MALFORMED, fail closed) -- compared as
canonical decimal strings ordered by (length, lexicographic), true
arbitrary precision with NO str-to-int conversion, so no interpreter
digit-count ceiling applies ('31.10' > '31.2'). The parser matches the EXACT
token: surrounding whitespace is malformed. File framing is owned by
each read boundary (the header line's label + line end; the marker's
single optional trailing newline; the raw fetched/read VERSION object
is persisted to a restrictive temp file and validated via
'version-read' -- NEVER via shell command substitution, which strips
ALL trailing newlines and would silently repair malformed multi-line
framing; 'parse'/'compare' take bare canonical tokens). Malformed
values always fail closed (exit 4).

This file is ASCII-only and contains no triple-backtick sequences, so it
stays safe to embed as a fenced payload in bootstrap.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
from pathlib import Path

# The single operator-editable source-of-truth line (Accepted Assumption):
SOURCE_SLUG = "kountlabs/Cursor-Bootstrap-Guide"

CONTRACT = 1
MARKER_RELPATH = ".cursor/bootstrap/installed-version"
VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
HEADER_RE = re.compile(r"^\*\*Version:\*\*\s*(.*?)\s*$")
MANIFEST_HEADING = "## PAYLOAD MANIFEST"
MANIFEST_LINE_RE = re.compile(r"^MANIFEST: ([0-9a-f]{64}) (\d+) (.+)$")
SECTION_RE = re.compile(r"^# SECTION (\d+)")
FILE_MARKER_RE = re.compile(r"^## FILE: `([^`]+)`$")
FENCE = "`" * 3
MAX_SECTION = 4

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_MALFORMED = 4
EXIT_CONTAINMENT = 5


def fail(code: int, message: str) -> int:
    print("ERROR: " + message, file=sys.stderr)
    return code


def parse_version(text: str):
    """Return the (major, minor) component tuple, or None if malformed.

    Matches the EXACT token -- no whitespace normalization here. File
    framing (a header line's label, the marker's single trailing
    newline) is handled at each read boundary, never by this parser:
    surrounding whitespace on the token itself is malformed.
    """
    # fullmatch, not match: Python's '$' would accept a trailing newline
    # on the token, which the exact-token contract forbids.
    m = VERSION_RE.fullmatch(text)
    if not m:
        return None
    return (m.group(1), m.group(2))


def component_key(c: str):
    """Ordering key for one canonical decimal component: (length, lexicographic).

    Canonical spelling has no leading zeros, so a longer digit string is
    strictly larger and equal-length strings order lexicographically.
    No str-to-int conversion anywhere, so the interpreter's decimal
    digit-count ceiling cannot reject a regex-valid component.
    """
    return (len(c), c)


def version_key(v):
    return (component_key(v[0]), component_key(v[1]))


def canonical(v) -> str:
    return str(v[0]) + "." + str(v[1])


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- header ----

def read_bootstrap_text(bootstrap: Path):
    """Controlled read+decode of a bootstrap file: (text, None) or (None, error)."""
    if not bootstrap.is_file():
        return None, "bootstrap file not found: " + str(bootstrap)
    try:
        raw = bootstrap.read_bytes()
    except OSError as e:
        return None, "unreadable bootstrap file " + str(bootstrap) + ": " + str(e)
    try:
        return raw.decode("utf-8-sig").replace("\r\n", "\n"), None
    except UnicodeDecodeError as e:
        return None, ("malformed bootstrap file " + str(bootstrap)
                      + ": not valid UTF-8 (" + str(e) + ")")


def extract_header(bootstrap: Path):
    """Return (version_tuple, None) or (None, error message)."""
    text, err = read_bootstrap_text(bootstrap)
    if err:
        return None, err
    matches = [m.group(1) for line in text.split("\n")
               for m in [HEADER_RE.match(line)] if m]
    if not matches:
        return None, "no **Version:** header found in " + str(bootstrap)
    if len(matches) > 1:
        return None, ("duplicate **Version:** header in " + str(bootstrap)
                      + " (" + str(len(matches)) + " occurrences)")
    v = parse_version(matches[0])
    if v is None:
        return None, ("malformed **Version:** header value "
                      + repr(matches[0]) + " (grammar: two unsigned decimal "
                      "components, canonical spelling)")
    return v, None


# ---------------------------------------------------------------- marker ----

def read_version_file(path: Path):
    """The ONE raw VERSION-object framing boundary: (canonical, None) or (None, error).

    Accepts exactly one line carrying the bare version token plus ONE
    optional trailing LF. CR (CRLF framing), extra or blank lines,
    surrounding whitespace, and non-UTF-8 bytes are all malformed --
    framing errors must fail closed here, never be repaired upstream
    (shell command substitution strips ALL trailing newlines and would
    silently validate a malformed multi-line object).
    """
    if not path.is_file():
        return None, "VERSION file not found: " + str(path)
    try:
        raw = path.read_bytes()
    except OSError as e:
        return None, "unreadable VERSION file " + str(path) + ": " + str(e)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        return None, ("malformed VERSION file " + str(path)
                      + ": not valid UTF-8 (" + str(e) + ")")
    content = text[:-1] if text.endswith("\n") else text
    if not content or "\n" in content or "\r" in content:
        return None, ("malformed VERSION framing in " + str(path)
                      + ": must be exactly one LF-terminated line")
    v = parse_version(content)
    if v is None:
        return None, ("malformed version token " + repr(content)
                      + " in " + str(path))
    return canonical(v), None


def marker_path(target: Path) -> Path:
    return target / MARKER_RELPATH


def read_marker(target: Path):
    """Classify the installed-version marker.

    Returns (state, version_tuple_or_None, identity_or_None, detail):
    state is one of 'valid', 'absent', 'malformed'. An identity-less
    (pre-identity / adoption) marker is valid with identity None.
    """
    p = marker_path(target)
    if not p.exists() and not p.is_symlink():
        return "absent", None, None, ""
    try:
        if p.is_symlink() or not p.is_file():
            return "malformed", None, None, "marker is not a regular file"
        raw = p.read_bytes().decode("utf-8", errors="strict")
    except (OSError, UnicodeDecodeError) as e:
        return "malformed", None, None, "unreadable marker: " + str(e)
    # Framing: exactly one line with ONE optional trailing newline --
    # extra lines, blank lines, or other surrounding whitespace are
    # malformed, never silently normalized away.
    content = raw[:-1] if raw.endswith("\n") else raw
    if not content or "\n" in content:
        return "malformed", None, None, ("marker must be exactly one line "
                                         "with one optional trailing newline")
    fields = content.split(" ")
    if any(f == "" for f in fields):
        return "malformed", None, None, ("marker fields must be separated by "
                                         "single spaces with no extra "
                                         "whitespace")
    v = parse_version(fields[0])
    if v is None:
        return "malformed", None, None, ("malformed version field "
                                         + repr(fields[0]))
    if len(fields) == 1:
        return "valid", v, None, ""
    if len(fields) == 2:
        return "valid", v, fields[1], ""
    return "malformed", None, None, "marker has more than two fields"


def write_marker(target: Path, version: str, identity: str) -> int:
    v = parse_version(version)
    if v is None:
        return fail(EXIT_MALFORMED, "malformed version " + repr(version))
    if not identity or any(c.isspace() for c in identity):
        return fail(EXIT_USAGE, "identity must be one non-whitespace token")
    p = marker_path(target)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = canonical(v) + " " + identity + "\n"
    with open(p, "wb") as fh:
        fh.write(line.encode("utf-8"))
    state, rv, rid, detail = read_marker(target)
    if state != "valid" or rv != v or rid != identity:
        return fail(EXIT_FAIL, "marker read-back verification failed ("
                    + state + " " + detail + ")")
    print("marker-written path=" + str(p) + " version=" + canonical(v)
          + " identity=" + identity)
    return EXIT_OK


# ------------------------------------------------------------- manifest ----

def manifest_paths(bootstrap: Path):
    """Return the manifest target paths, or (None, error)."""
    text, err = read_bootstrap_text(bootstrap)
    if err:
        return None, err
    idx = text.rfind("\n" + MANIFEST_HEADING + "\n")
    if idx < 0:
        return None, "no " + MANIFEST_HEADING + " section in " + str(bootstrap)
    paths = []
    for line in text[idx:].split("\n"):
        m = MANIFEST_LINE_RE.match(line)
        if m:
            paths.append(m.group(3))
    if not paths:
        return None, MANIFEST_HEADING + " section has no entries"
    return paths, None


def payload_paths(text: str):
    """Return the SECTION 0-4 FILE-payload paths, fence-skipping like the extractor.

    The extractor WRITES each payload before its manifest lookup, so the
    TOUCH inventory must cover payload-block paths too, not only manifest
    entries -- an unmanifested block would otherwise land outside the
    snapshot. Same section/marker/fence walk as extract-bootstrap.py.
    """
    lines = text.split("\n")
    paths = []
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
            paths.append(path)
            break
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
        paths.append(path)
        i = (end + 1) if end is not None else n
    return paths


def safe_relpath(path: str):
    p = Path(path)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        return None
    return p


# ---------------------------------------------------------- containment ----

def containment_walk(target: Path, relpaths):
    """No-follow lstat walk over every write path (fail-closed).

    Returns a list of 'path: reason' violation strings. A symlinked final
    component or ancestor, or an existing non-regular write target, is a
    violation -- lexical checks are not containment, and the extractor's
    own open() follows links, so an external referent could otherwise
    change. Deliberate workflow-dir symlinks get a manual-remediation
    pause upstream, never silent traversal.
    """
    violations = []
    root = target.resolve()
    for rel in relpaths:
        rp = safe_relpath(rel)
        if rp is None:
            violations.append(rel + ": absolute or parent-escaping path")
            continue
        cur = root
        parts = rp.parts
        for i, part in enumerate(parts):
            cur = cur / part
            try:
                st = os.lstat(cur)
            except FileNotFoundError:
                break  # nothing below exists yet; creation is contained
            except OSError as e:
                violations.append(rel + ": lstat failed at " + str(cur)
                                  + " (" + str(e) + ")")
                break
            is_final = i == len(parts) - 1
            if stat.S_ISLNK(st.st_mode):
                violations.append(rel + ": symlinked "
                                  + ("final component" if is_final
                                     else "ancestor") + " at " + str(cur))
                break
            if is_final:
                if not stat.S_ISREG(st.st_mode):
                    violations.append(rel + ": existing non-regular write "
                                      "target at " + str(cur))
            elif not stat.S_ISDIR(st.st_mode):
                violations.append(rel + ": non-directory ancestor at "
                                  + str(cur))
                break
    return violations


# ------------------------------------------------------- state handling ----

def state_paths(state_dir: Path):
    return state_dir / "state.json", state_dir / "blobs"


def load_state(state_dir: Path):
    sp, _ = state_paths(state_dir)
    if not sp.is_file():
        return None, "no state.json in " + str(state_dir) + " (run inventory first)"
    try:
        data = json.loads(sp.read_bytes().decode("utf-8"))
    except (OSError, ValueError) as e:
        return None, "unreadable state.json: " + str(e)
    if data.get("contract") != CONTRACT:
        return None, ("state contract mismatch: state="
                      + str(data.get("contract")) + " helper=" + str(CONTRACT))
    return data, None


def save_state(state_dir: Path, data) -> None:
    sp, _ = state_paths(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(state_dir, 0o700)
    with open(sp, "wb") as fh:
        fh.write(json.dumps(data, indent=1, sort_keys=True).encode("utf-8"))
    os.chmod(sp, 0o600)


def record_path_state(target: Path, rel: str, blobs: Path):
    """Return the snapshot record for one path; stores bytes as a blob."""
    p = target / rel
    try:
        st = os.lstat(p)
    except FileNotFoundError:
        return {"exists": False}
    rec = {"exists": True, "mode": st.st_mode, "size": st.st_size}
    if stat.S_ISREG(st.st_mode):
        data = p.read_bytes()
        digest = sha256_bytes(data)
        rec["type"] = "file"
        rec["sha256"] = digest
        blob = blobs / digest
        if not blob.exists():
            blobs.mkdir(parents=True, exist_ok=True)
            os.chmod(blobs, 0o700)
            with open(blob, "wb") as fh:
                fh.write(data)
            os.chmod(blob, 0o600)
    else:
        rec["type"] = "other"  # containment refuses these before any write
    return rec


def cmd_inventory(bootstrap: Path, target: Path, state_dir: Path) -> int:
    if not bootstrap.is_file():
        return fail(EXIT_USAGE, "bootstrap file not found: " + str(bootstrap))
    if not target.is_dir():
        return fail(EXIT_USAGE, "target is not a directory: " + str(target))
    paths, err = manifest_paths(bootstrap)
    if err:
        return fail(EXIT_MALFORMED, err)
    text, err = read_bootstrap_text(bootstrap)
    if err:
        return fail(EXIT_MALFORMED, err)
    inventory = sorted(set(paths + payload_paths(text) + [MARKER_RELPATH]))
    violations = containment_walk(target, inventory)
    if violations:
        for v in violations:
            print("CONTAINMENT " + v, file=sys.stderr)
        return fail(EXIT_CONTAINMENT,
                    str(len(violations)) + " containment violation(s); "
                    "fail-closed, nothing written")
    data = {
        "contract": CONTRACT,
        "target": str(target.resolve()),
        "bootstrap": str(bootstrap.resolve()),
        "marker_path": MARKER_RELPATH,
        "inventory": inventory,
        "snapshot": None,
        "dirs_preexist": None,
    }
    save_state(state_dir, data)
    for rel in inventory:
        print(rel)
    print("inventory-ok count=" + str(len(inventory)))
    return EXIT_OK


def cmd_snapshot(state_dir: Path) -> int:
    data, err = load_state(state_dir)
    if err:
        return fail(EXIT_USAGE, err)
    target = Path(data["target"])
    violations = containment_walk(target, data["inventory"])
    if violations:
        for v in violations:
            print("CONTAINMENT " + v, file=sys.stderr)
        return fail(EXIT_CONTAINMENT, "containment violation(s) at snapshot")
    _, blobs = state_paths(state_dir)
    snapshot = {}
    dirs = {}
    for rel in data["inventory"]:
        snapshot[rel] = record_path_state(target, rel, blobs)
        parent = Path(rel).parent
        while parent.as_posix() not in ("", "."):
            key = parent.as_posix()
            if key not in dirs:
                dirs[key] = (target / parent).is_dir()
            parent = parent.parent
    data["snapshot"] = snapshot
    data["dirs_preexist"] = dirs
    save_state(state_dir, data)
    print("snapshot-ok paths=" + str(len(snapshot)))
    return EXIT_OK


def cmd_verify_containment(state_dir: Path) -> int:
    data, err = load_state(state_dir)
    if err:
        return fail(EXIT_USAGE, err)
    violations = containment_walk(Path(data["target"]), data["inventory"])
    if violations:
        for v in violations:
            print("CONTAINMENT " + v, file=sys.stderr)
        return fail(EXIT_CONTAINMENT, "containment violation(s); do not write")
    print("containment-ok")
    return EXIT_OK


def compute_delta(data):
    """Return (kind, rel) pairs where post-state differs from the snapshot."""
    target = Path(data["target"])
    delta = []
    for rel in data["inventory"]:
        pre = data["snapshot"][rel]
        p = target / rel
        try:
            st = os.lstat(p)
            exists = True
        except FileNotFoundError:
            exists = False
        if not pre["exists"] and exists:
            delta.append(("created", rel))
        elif pre["exists"] and not exists:
            delta.append(("deleted", rel))
        elif exists and pre["exists"]:
            if stat.S_ISREG(st.st_mode) and pre.get("type") == "file":
                if (st.st_size != pre["size"]
                        or sha256_bytes(p.read_bytes()) != pre["sha256"]
                        or stat.S_IMODE(st.st_mode) != stat.S_IMODE(pre["mode"])):
                    delta.append(("changed", rel))
            elif stat.S_ISREG(st.st_mode) != (pre.get("type") == "file"):
                delta.append(("changed", rel))
    return delta


def cmd_delta(state_dir: Path) -> int:
    data, err = load_state(state_dir)
    if err:
        return fail(EXIT_USAGE, err)
    if not data.get("snapshot"):
        return fail(EXIT_USAGE, "no snapshot in state (run snapshot first)")
    delta = compute_delta(data)
    for kind, rel in delta:
        print(kind + " " + rel)
    print("delta-ok count=" + str(len(delta)))
    return EXIT_OK


def cmd_restore(state_dir: Path) -> int:
    data, err = load_state(state_dir)
    if err:
        return fail(EXIT_USAGE, err)
    if not data.get("snapshot"):
        return fail(EXIT_USAGE, "no snapshot in state (run snapshot first)")
    target = Path(data["target"])
    _, blobs = state_paths(state_dir)
    failures = 0
    for rel in data["inventory"]:
        pre = data["snapshot"][rel]
        p = target / rel
        try:
            if pre["exists"] and pre.get("type") == "file":
                blob = blobs / pre["sha256"]
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, "wb") as fh:
                    fh.write(blob.read_bytes())
                os.chmod(p, stat.S_IMODE(pre["mode"]))
            elif not pre["exists"]:
                if p.exists() or p.is_symlink():
                    p.unlink()
        except OSError as e:
            print("FAIL restore " + rel + ": " + str(e), file=sys.stderr)
            failures += 1
    # Prune directories this run created (deepest-first), only when empty.
    created_dirs = [d for d, pre in (data.get("dirs_preexist") or {}).items()
                    if not pre]
    for d in sorted(created_dirs, key=lambda s: len(Path(s).parts), reverse=True):
        dp = target / d
        try:
            if dp.is_dir() and not any(dp.iterdir()):
                dp.rmdir()
        except OSError:
            pass  # non-empty or busy: leave it; the delta check reports state
    # Verify: post-restore state must match the snapshot exactly.
    residue = compute_delta(data)
    for kind, rel in residue:
        print("FAIL residue " + kind + " " + rel, file=sys.stderr)
    if failures or residue:
        return fail(EXIT_FAIL, "restore incomplete: " + str(failures)
                    + " write failure(s), " + str(len(residue)) + " residue path(s)")
    print("restore-ok paths=" + str(len(data["inventory"])))
    return EXIT_OK


def cmd_pin(state_dir: Path) -> int:
    src = Path(__file__).resolve()
    state_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(state_dir, 0o700)
    dest = state_dir / "pinned-helper.py"
    data = src.read_bytes()
    with open(dest, "wb") as fh:
        fh.write(data)
    os.chmod(dest, 0o600)
    print("pinned=" + str(dest) + " sha256=" + sha256_bytes(data))
    return EXIT_OK


def cmd_cleanup(state_dir: Path) -> int:
    if state_dir.exists():
        shutil.rmtree(state_dir)
    print("cleanup-ok")
    return EXIT_OK


# ------------------------------------------------------------------ main ----

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Workflow source/version helper (contract="
                    + str(CONTRACT) + "). See the module docstring for the "
                    "full CLI/state contract.")
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("contract")
    sub.add_parser("slug")
    p = sub.add_parser("parse")
    p.add_argument("version")
    p = sub.add_parser("compare")
    p.add_argument("a")
    p.add_argument("b")
    p = sub.add_parser("version-read")
    p.add_argument("--file", required=True)
    p = sub.add_parser("header")
    p.add_argument("--bootstrap", required=True)
    p = sub.add_parser("marker-read")
    p.add_argument("--target", default=".")
    p = sub.add_parser("marker-write")
    p.add_argument("--target", default=".")
    p.add_argument("--version", required=True)
    p.add_argument("--identity", required=True)
    for name in ("pin", "snapshot", "verify-containment", "delta",
                 "restore", "cleanup"):
        p = sub.add_parser(name)
        p.add_argument("--state", required=True)
    p = sub.add_parser("inventory")
    p.add_argument("--bootstrap", required=True)
    p.add_argument("--target", default=".")
    p.add_argument("--state", required=True)

    args = ap.parse_args()
    if args.cmd is None:
        ap.print_help()
        return EXIT_USAGE

    if args.cmd == "contract":
        print("contract=" + str(CONTRACT))
        return EXIT_OK
    if args.cmd == "slug":
        print(SOURCE_SLUG)
        return EXIT_OK
    if args.cmd == "parse":
        v = parse_version(args.version)
        if v is None:
            return fail(EXIT_MALFORMED, "malformed version " + repr(args.version))
        print(canonical(v))
        return EXIT_OK
    if args.cmd == "compare":
        va, vb = parse_version(args.a), parse_version(args.b)
        if va is None or vb is None:
            bad = args.a if va is None else args.b
            return fail(EXIT_MALFORMED, "malformed version " + repr(bad))
        ka, kb = version_key(va), version_key(vb)
        result = "older" if ka < kb else ("newer" if ka > kb else "same")
        major = "yes" if component_key(va[0]) > component_key(vb[0]) else "no"
        print("result=" + result + " major=" + major)
        return EXIT_OK
    if args.cmd == "version-read":
        v, err = read_version_file(Path(args.file))
        if err:
            return fail(EXIT_MALFORMED, err)
        print(v)
        return EXIT_OK
    if args.cmd == "header":
        v, err = extract_header(Path(args.bootstrap))
        if err:
            return fail(EXIT_MALFORMED, err)
        print(canonical(v))
        return EXIT_OK
    if args.cmd == "marker-read":
        state, v, ident, detail = read_marker(Path(args.target))
        if state == "valid":
            print("state=valid version=" + canonical(v) + " identity="
                  + (ident if ident else "-"))
        elif state == "absent":
            print("state=absent")
        else:
            print("state=malformed reason=" + repr(detail))
        return EXIT_OK
    if args.cmd == "marker-write":
        return write_marker(Path(args.target), args.version, args.identity)
    if args.cmd == "pin":
        return cmd_pin(Path(args.state))
    if args.cmd == "inventory":
        return cmd_inventory(Path(args.bootstrap), Path(args.target),
                             Path(args.state))
    if args.cmd == "snapshot":
        return cmd_snapshot(Path(args.state))
    if args.cmd == "verify-containment":
        return cmd_verify_containment(Path(args.state))
    if args.cmd == "delta":
        return cmd_delta(Path(args.state))
    if args.cmd == "restore":
        return cmd_restore(Path(args.state))
    if args.cmd == "cleanup":
        return cmd_cleanup(Path(args.state))
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
