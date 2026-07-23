#!/usr/bin/env python3
"""Deterministic wizard model-probe script (execute-loop Setup wizard Step 0
plus the accounts probe submode).

Runs every shell-probeable Step 0 probe and emits ONE JSON document on stdout
(nothing else is ever printed to stdout). The wizard consumes the fields by the
exact names below; the prose bullets in the execute-loop skill remain the
canonical probe DEFINITIONS and the documented no-python fallback. The same
document powers the execute-loop accounts probe submode and the Q1R keep-or-
switch re-check (per-account structured usage, plan tier, and recent-repos
activity).

NORMATIVE GOLDEN EXAMPLE (probe_schema 1 -- the pinned consumption contract;
field names, nesting, and status vocabulary are normative; values illustrate):

{
  "probe_schema": 1,
  "generated": "2026-07-10T13:20:00+10:00",
  "host": {"platform": "linux", "is_wsl": true, "python": "3.12.3"},
  "capabilities": ["profile-dir-filter"],
  "codex": {
    "status": "ok",
    "error": null,
    "listed_count": 7,
    "total_count": 8,
    "models": [
      {
        "slug": "gpt-5.6-sol",
        "display_name": "GPT-5.6-Sol",
        "visibility": "list",
        "default_effort": "low",
        "efforts": ["low", "medium", "high", "xhigh", "max", "ultra"],
        "priority": 1
      }
    ],
    "usage": {"status": "ok", "error": null, "plan": "pro",
              "session_pct": 12, "session_resets": "2026-07-11T02:40+10:00",
              "session_resets_at": 1783622400,
              "week_pct": 42, "week_resets": "2026-07-16T14:00+10:00",
              "week_resets_at": 1784095200}
  },
  "claude": {
    "status": "ok",
    "error": null,
    "candidates": [
      {
        "path": "/home/user/.nvm/versions/node/v24.17.0/bin/claude",
        "source": "nvm-glob",
        "environment_native": true,
        "isolation_probe": {"status": "ok", "detail": "logged out under bogus CLAUDE_CONFIG_DIR"}
      }
    ],
    "pinned": "/home/user/.nvm/versions/node/v24.17.0/bin/claude",
    "help": {"status": "ok", "aliases": ["fable", "opus", "sonnet"],
             "efforts": ["low", "medium", "high", "xhigh", "max"]},
    "version": {"value": "2.1.201 (Claude Code)", "status": "ok", "error": null},
    "advisor": {"value": null, "status": "skipped", "error": null, "version": null},
    "profile_dir_filter": null,
    "default_account": {"identity": "user@example.com (Example Org)", "status": "ok",
                        "plan": "max",
                        "usage": {"status": "skipped", "headline": null,
                                  "session_pct": null, "session_resets": null,
                                  "week_pct": null, "week_resets": null},
                        "config_dir": "/home/user/.claude",
                        "config_source": "builtin",
                        "aliases_profile": null,
                        "recent_repos": {"status": "ok", "error": null, "entries": [
                            {"name": "-home-user-projects-example-app",
                             "age_min": 4.2, "in_use": true}]}},
    "profiles": [
      {"dir": "/home/user/.claude-work", "identity": "work@example.com (Work Org)",
       "status": "ok", "plan": "max",
       "usage": {"status": "ok",
                 "headline": "Current session: 12% used - resets Jul 20, 9pm "
                             "(Area/City) | Current week (all models): 34% used "
                             "- resets Jul 27, 1pm (Area/City)",
                 "session_pct": 12, "session_resets": "Jul 20, 9pm (Area/City)",
                 "week_pct": 34, "week_resets": "Jul 27, 1pm (Area/City)"},
       "recent_repos": {"status": "ok", "error": null, "entries": [
           {"name": "-home-user-projects-other-repo",
            "age_min": 3.0, "in_use": true}]}}
    ]
  },
  "cursor": {
    "status": "in-context",
    "note": "no shell surface exists; the composer enumerates in-context subagent slugs"
  },
  "plans": {
    "status": "ok",
    "plans_dir": ".cursor/plans",
    "scanned": 3,
    "active_candidates": [
      {"file": "plan-loop-reliability-v29-1.md",
       "loop_config": "executor=claude-p model=\\"fable\\"; peer=codex model=\\"gpt-5.6-sol\\""}
    ],
    "non_active_with_config": 2,
    "archived_fallback": null,
    "q1_offer": {
      "offer": "active",
      "plan": "plan-loop-reliability-v29-1.md",
      "label": "same as last run -- plan-loop-reliability-v29-1.md",
      "reason": "exactly one Active plan with a parseable Loop config: line"
    }
  },
  "report_line": "Probes: codex OK (7 models) | claude OK (v2.1.201; 3 aliases, 1 profile) | cursor {CURSOR_SLUGS} | plans: 1 Active candidate (offer: same as last run -- plan-loop-reliability-v29-1.md)"
}

Status vocabulary (per-probe "status" fields; the only legal values):
    ok | degraded | absent | failed | timeout | no-candidate-passed |
    in-context | skipped | partial

Null/error representation: a probe that did not produce a value carries value
null (never a sentinel string) plus a status from the vocabulary; failure
detail rides an "error" string field next to the status, null when clean.

State mappings pinned by the v29.1 plan (W4) plus the Stage B accounts
extensions (probe_schema stays 1; every Stage B field is additive-optional
-- consumers tolerate absence in BOTH directions of the UPDATE ONLY skew):

- claude.advisor -- the FOUR-STATE advisor-capability entry. The acceptance
  probe is BILLED and runs only behind --probe-advisor (gated like --usage,
  never by default; it spawns one cheap advisored 'claude -p' invocation whose
  prompt INSTRUCTS the model to consult the advisor once -- advisor use is
  opportunistic, so only an engagement-forcing prompt probes deterministically):
    not probed (default) -> {"value": null,  "status": "skipped"}  -- NEVER
        "absent": absent is reserved for an OBSERVED not-supported result,
        and an unrun probe observed nothing
    engaged (advisor model present in the result modelUsage)
                         -> {"value": true,  "status": "ok", "version": <the
                            separate version probe's parsed value, or null
                            when that value was not actually observed>}
    rejected (nonzero exit / no engagement evidence on a clean exit)
                         -> {"value": null,  "status": "failed", "error": "..."}
        (a clean exit with no advisor model in modelUsage is a FAILED
        capability probe, never ok and never absent -- capability is only
        asserted on observed engagement; the error string distinguishes a
        captured stderr "cannot advise" pairing strip from a plain
        no-engagement completion)
    timed out            -> {"value": null,  "status": "timeout"}

- claude.version -- the SEPARATE timeout-bounded '<pinned> --version'
  subprocess (never folded into the --help parse), same WSL/shim env handling:
    parsed               -> {"value": "2.1.201 (Claude Code)", "status": "ok"}
    nonzero exit         -> {"value": null, "status": "failed", "error": "..."}
    timeout              -> {"value": null, "status": "timeout"}
    unexpected shape     -> {"value": null, "status": "failed", "error":
                            "unexpected version output shape: ..."}
  Only a parsed version value ever produces a version attribution downstream
  (advisor.version copies it on engagement, else stays null).

- claude.candidates[].isolation_probe -- the canonical bogus-dir probe per
  candidate ('CLAUDE_CONFIG_DIR=<bogus> <candidate> auth status' must report
  logged-out; the bogus dir is root-anchored so it can never be created):
    ok = logged out (PASS; only this state can pin) | failed = still logged
    in (env var not reaching the binary) | degraded = indeterminate output |
    timeout. Indeterminate and timeout NEVER pin. Under WSL a /mnt/ shim
    candidate gets CLAUDE_CONFIG_DIR auto-merged into WSLENV so the variable
    crosses the interop boundary.

- claude.status -- ok (pinned + full help parse) | degraded (pinned, but help
  parse failed or partial: degrade the affected menus to free-text entry) |
  no-candidate-passed (candidates exist, none passed the isolation probe:
  the wizard fires the environment-readiness pause) | absent (no candidate
  binary found) | failed (internal error).

- claude usage structured fields (accounts-probe extension; only behind
  --usage) -- session_pct/session_resets parse ONLY from the exact
  "Current session:" line and week_pct/week_resets ONLY from the exact
  "Current week (all models):" line; model-specific "Current week
  (<Model>):" lines and insight/contribution percentage lines are NEVER
  substituted (all-models line absent -> week_pct stays null, never another
  percentage). The separator between the percent and the resets clause is a
  non-ASCII middle dot on observed hosts and is never keyed on; resets text
  is carried verbatim (hour-only shapes observed; minute-bearing tolerated
  as forward-compat). A 0% cell omits its resets clause entirely, so reset
  fields are nullable even at status ok. A logged-out store's /usage exits
  0 with a local-stats block carrying no % lines -> the existing
  degraded/headline path, unchanged. Structured-parse failure never changes
  status or headline: the new fields simply stay null alongside them.

- codex.usage -- the app-server account/rateLimits/read exchange (only
  behind --usage; SKIPPED when --profile-dir is present -- that flag names
  claude dirs and the Q1R re-check needs no codex leg). Popen-based BY
  DESIGN, never run_cli: the server exits on closed stdin, so stdin stays
  OPEN across scripted write+sleep windows; the deadline is max(--timeout,
  30) with the sleeps INSIDE it, and the recorded child is terminated ->
  bounded-waited -> killed -> reaped on every success/failure/timeout path
  (recorded identity only, never broad process matching). The response is
  correlated on the rate-limit request id ONLY; initialize responses,
  notifications, and banner lines are tolerated and ignored. Windows are
  classified by windowDurationMins (300 = session, 10080 = week), NEVER by
  primary/secondary position (position drift observed live: primary held
  the weekly window with secondary null); an absent window leaves its
  fields null and the table renders "not exposed". resetsAt rides verbatim
  as *_resets_at (epoch seconds) plus a derived local-ISO *_resets string.
  plan <- rateLimits.planType when present. The response exposes NO account
  identity; the accounts table's codex account cell renders "not exposed".
  statuses: ok (>=1 window classified) | degraded (id:2 parsed but no
  rateLimits object / no recognizable window: shape drift) | failed (no
  id:2 response, rpc error object, or spawn/write failure) | timeout |
  absent (no codex executable) | skipped. Edge: a response that arrives
  only during the bounded post-deadline reap still parses (status ok --
  data present beats a timeout label); "timeout" means no id-correlated
  response was ever captured.

- recent_repos (per claude account; ALWAYS-ON, no CLI call) -- a read-only
  mtime scan of <config-root>/projects/ entries, snapshotted in
  probe_claude's pass 1 BEFORE any pass-2 identity/usage subprocess so the
  advisory input is pre-probe truth (a usage run itself adds/cleans
  projects entries). Entries are mtime-sorted newest-first: {"name":
  <munged dir name>, "age_min": <minutes>, "in_use": age < 10 min
  (explicitly a heuristic)}. Excluded probe artifacts, keyed by munged name
  (every non-alphanumeric character -> "-"): the script's own cwd
  (current-repo entries are never "foreign"), the neutral probe cwd, and
  the neutral cwd's PARENT entry when -- and only when -- it is
  memory-only. That parent exclusion is CONTENT-AWARE: a same-named entry
  carrying anything else (e.g. a <session-uuid>.jsonl transcript) stays
  visible, and an unreadable entry stays visible too (the exclusion never
  broadens). statuses: ok | degraded (some children unreadable) | failed
  (projects/ unreadable, or a malformed non-directory projects path) |
  absent (config root is not a readable directory
  -- the table renders "unavailable"). An unclassifiable (unreadable-
  content) parent-token entry stays VISIBLE but degrades the snapshot --
  incomplete metadata is never presented as a complete healthy advisory.
  Pass-2 usage probes run from the neutral cwd (resolved READ-ONLY from
  TMPDIR/TEMP/TMP else the platform temp candidates -- never
  tempfile.gettempdir(), whose usability probe CREATES a file; falls back
  to the script cwd when no candidate exists -- both munges are excluded
  either way), so probe-created entries always land under excluded names.

- default_account extras -- the default store is ENVIRONMENT-RESOLVED:
  config_dir = CLAUDE_CONFIG_DIR from the script's own environment when
  non-empty (config_source "env") else ~/.claude (config_source
  "builtin"). The resolved default can ALIAS an enumerated profile;
  aliases_profile carries that profile row's dir value (realpath-keyed
  dedup against the emitted profile rows) or null. The row reports its
  RESOLVED auth state -- a resolved store can hold stale credentials and
  still be logged out. When the resolved root is not a readable directory,
  recent_repos degrades to status "absent" (rendered "unavailable");
  identity/usage still probe whatever the CLI itself resolves.

- profile eligibility -- is_eligible_profile_dir() is the ONE named
  predicate shared by enumeration, --profile-dir validation, and every
  consumer: a real directory (realpath) at ~/.claude*, EXCLUDING the
  built-in default store ~/.claude itself (special default handling
  above), *.lock control dirs, any dir carrying the ".quarantined-"
  marker, and malformed/non-directory entries. Enumeration
  realpath-dedups. A quarantined or control dir is never probed, rendered,
  or accepted as a profile.

- capabilities / profile_dir_filter -- the top-level capabilities list
  advertises optional behaviours (currently "profile-dir-filter");
  consumers MUST treat it as optional (older scripts omit it -- absence
  means fall back to the full run). When --profile-dir is passed,
  claude.profile_dir_filter records {"requested", "selected", "invalid"};
  ineligible values land in "invalid", are never probed, and never change
  the exit code. The reserved literal 'default' is exclusive: when present,
  every co-specified dir is reported invalid and no named profile is
  probed. plan fields (claude subscriptionType / codex planType) are null
  when the source surface does not expose one -- the table renders "not
  exposed".

- plans.q1_offer -- the wizard Q1 reuse rule applied mechanically:
    offer "active":   exactly one Active plan in <plans-dir> has a parseable
                      'Loop config:' bullet in its Current State / Handoff
                      Note section -> offer "same as last run" naming it.
    offer "none":     multiple Active candidates (reason says so), or zero
                      candidates in both locations, or no plans dir, or an
                      INCOMPLETE scan -- any unreadable candidate file fails
                      closed (an unreadable file could hide an Active
                      candidate, so neither exactly-one-Active nor the
                      newest-archived premise is established): a partial
                      scan never offers reuse, and the PARTIAL fourth
                      segment carries the bounded reason.
    offer "archived": no Active plan qualifies; the single most recently
                      modified plan under <plans-dir>/completed/ with a
                      parseable config line is offered "(from archived plan
                      <name>)" -- the config is reused, not the plan.
  Candidate rule (LOAD-BEARING Active filter): a plan is a candidate iff its
  '## Lifecycle State' section leads with 'Active' AND a '- Loop config: '
  bullet inside '## Current State / Handoff Note' parses (at least one
  semicolon-separated key=value group parses; unknown keys are ignored --
  the forward-compat rule). Both scans are heading-scoped and fence-skipping,
  so quoted examples inside fenced blocks never count.

- report_line -- preassembled four-segment probe report with EXACTLY ONE
  composer-filled placeholder, the literal token {CURSOR_SLUGS} in the cursor
  segment (no shell surface exists for Cursor slugs; the composer replaces
  the token with its in-context enumeration and prints the line verbatim).

Flags:
    --usage          run the per-account usage probes for BOTH families:
                     claude '<pinned> -p "/usage" --output-format text' per
                     account (~2-7s each; structured fields + headline) and
                     the codex app-server rateLimits exchange (~10s).
                     Default off: usage entries report status "skipped".
                     The wizard and the accounts probe submode run this
                     LAZILY -- only when a menu or table actually needs
                     usage values.
    --profile-dir D  repeatable: restrict the claude profile surface
                     (enumeration, recent_repos, identity, usage) to the
                     named eligible profile dir(s) PLUS the default
                     account; the reserved literal value 'default' selects
                     the default account alone (the Q1R re-check shapes)
                     and is EXCLUSIVE -- when present, co-specified dirs
                     are reported invalid and never probed. Skips the
                     codex usage leg. Ineligible values land in
                     claude.profile_dir_filter.invalid (exit stays 0).
    --probe-advisor  run the BILLED advisor acceptance probe (one cheap
                     advisored invocation). Default off: status "skipped".
    --timeout N      per-subprocess timeout in seconds (default 15; the
                     advisor probe uses max(N, 180), usage max(N, 30) --
                     the codex usage exchange's scripted sleeps run INSIDE
                     that deadline).
    --plans-dir P    plans directory for the Q1 scan (default .cursor/plans).

Behaviour contract: ASCII-only source, stdlib-only, strictly read-only (the
only outputs are stdout/stderr; every subprocess is a read-only probe; the
optional advisor probe bills tokens but writes nothing; the script itself
never creates a file or directory anywhere), no literal triple-backtick
sequences (fence tokens are built programmatically), every subprocess
carries a timeout and stdin=DEVNULL so the script never hangs (single
exception: the codex usage exchange holds stdin OPEN by protocol necessity
-- Popen-recorded, deadline-bounded, terminated/killed/reaped in finally),
and the JSON document is ALWAYS emitted with exit code 0 -- per-probe
failures land in statuses, never in the exit code. Exit 2 only when the JSON
itself could not be produced.

Usage (from the project root; use plain 'python' if 'python3' is absent):
    python3 .cursor/bootstrap/probe-models.py
    python3 .cursor/bootstrap/probe-models.py --usage --timeout 20
    python3 .cursor/bootstrap/probe-models.py --usage --profile-dir default
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import platform
import re
import stat
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

FENCE = "`" * 3  # never a literal fence in this source
BOGUS_CONFIG_DIR = "/nonexistent-claude-config-dir-probe"  # root-anchored: uncreatable
CURSOR_PLACEHOLDER = "{CURSOR_SLUGS}"
LOOP_CONFIG_PREFIX = "- Loop config: "
CONFIG_TOKEN_RE = re.compile(r'^[A-Za-z_][\w-]*=(?:"[^"]*"|[^\s"]+)$')
VERSION_RE = re.compile(r"^v?\d+(\.\d+)+")
ADVISOR_MAIN = "sonnet"     # verified-cheap accepted pairing (observed live 2026-07-10)
ADVISOR_MODEL = "opus"

# Accounts-probe constants (Stage B). The neutral cwd keeps probe-created
# projects entries under a known excluded munge instead of refreshing the
# current repo's entry in every probed store; it is never created by this
# script (read-only contract) -- when missing, probes fall back to the
# script's own cwd, whose munge is excluded too.


def _resolve_neutral_probe_cwd() -> str:
    """READ-ONLY neutral-cwd resolution. Deliberately NOT
    tempfile.gettempdir(): CPython probes candidate usability by CREATING
    and deleting a test file, which would violate this script's strict
    read-only contract (and can raise at import). Mirrors CPython's
    candidate ORDER (env vars, then the user-local Windows temp before the
    system one, then the platform fallbacks) with metadata-only checks --
    isdir plus an access(R|X) searchability test, so one existing-but-
    unusable candidate never blocks a later usable one. Falls back to the
    invoking cwd, whose munge is excluded from recent_repos anyway."""
    cands = []
    for env_name in ("TMPDIR", "TEMP", "TMP"):
        v = (os.environ.get(env_name) or "").strip()
        if v:
            cands.append(v)
    if os.name == "nt":
        cands.append(os.path.expanduser("~\\AppData\\Local\\Temp"))
        for v in (os.environ.get("SYSTEMROOT"), os.environ.get("windir")):
            if v:
                cands.append(os.path.join(v, "Temp"))
        cands.extend(["c:\\temp", "c:\\tmp", "\\temp", "\\tmp"])
    else:
        cands.extend(["/tmp", "/var/tmp", "/usr/tmp"])
    for cand in cands:
        try:
            real = os.path.realpath(cand)
            if os.path.isdir(real) and os.access(real, os.R_OK | os.X_OK):
                return real
        except OSError:
            continue
    try:
        return os.path.realpath(os.getcwd())
    except OSError:
        return "."


NEUTRAL_PROBE_CWD = _resolve_neutral_probe_cwd()
IN_USE_THRESHOLD_MIN = 10.0  # projects-entry age below this reads "in use" (heuristic)
QUARANTINE_MARKER = ".quarantined-"  # delete-path rename marker; predicate-excluded
SESSION_LINE_PREFIX = "Current session:"
WEEK_ALL_LINE_PREFIX = "Current week (all models):"
CODEX_USAGE_INIT_REQ = ('{"jsonrpc":"2.0","id":1,"method":"initialize","params":'
                        '{"clientInfo":{"name":"probe","title":"probe",'
                        '"version":"0.0.1"}}}')
CODEX_USAGE_RATE_REQ = ('{"jsonrpc":"2.0","id":2,'
                        '"method":"account/rateLimits/read","params":{}}')
CODEX_USAGE_RATE_ID = 2
CODEX_USAGE_INIT_WINDOW_S = 2.0      # scripted sleep after the initialize write
CODEX_USAGE_RESPONSE_WINDOW_S = 8.0  # scripted sleep after the rate-limit write
CODEX_SESSION_WINDOW_MINS = 300      # windowDurationMins value classifying "session"
CODEX_WEEK_WINDOW_MINS = 10080       # windowDurationMins value classifying "week"


def host_is_wsl() -> bool:
    try:
        with open("/proc/version", "r", encoding="utf-8", errors="replace") as fh:
            return "microsoft" in fh.read().lower()
    except OSError:
        return False


def run_cli(cmd: list[str], timeout: float, env: dict | None = None,
            cwd: str | None = None):
    """Run a probe subprocess; returns (status, stdout, stderr, returncode).

    status is one of: ok (ran, exit 0), failed (ran, nonzero), timeout,
    absent (executable not found). Never raises; never inherits stdin.
    cwd optionally redirects the subprocess (the neutral-cwd usage probes).
    """
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            stdin=subprocess.DEVNULL, env=env, cwd=cwd,
        )
        return ("ok" if proc.returncode == 0 else "failed",
                proc.stdout, proc.stderr, proc.returncode)
    except FileNotFoundError:
        return ("absent", "", "executable not found: " + cmd[0], None)
    except subprocess.TimeoutExpired:
        return ("timeout", "", "timed out after " + str(timeout) + "s", None)
    except OSError as exc:
        return ("failed", "", str(exc), None)


def candidate_names(name: str, is_windows: bool, pathext: str) -> list[str]:
    """Executable filenames to test per PATH directory: the literal name,
    plus PATHEXT-suffixed variants on native Windows (shutil.which
    semantics -- an npm-installed CLI is exposed as name.cmd / name.exe
    there, and NTFS name lookup is case-insensitive so one casing
    suffices). Order: literal name first, then PATHEXT order."""
    if not is_windows:
        return [name]
    exts = [e.strip() for e in (pathext or ".COM;.EXE;.BAT;.CMD").split(";")
            if e.strip()]
    names = [name]
    lower = name.lower()
    for ext in exts:
        if not lower.endswith(ext.lower()):
            names.append(name + ext.lower())
    return names


def which_all(name: str) -> list[str]:
    """All executable PATH matches for name, in PATH order (like which -a).

    On native Windows the PATHEXT variants are tested per directory
    (candidate_names above) and the X_OK check is skipped (unreliable
    there); elsewhere the literal name must be executable.
    """
    is_windows = os.name == "nt"
    names = candidate_names(name, is_windows, os.environ.get("PATHEXT", ""))
    hits: list[str] = []
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if not d:
            continue
        for n in names:
            cand = os.path.join(d, n)
            if (os.path.isfile(cand)
                    and (is_windows or os.access(cand, os.X_OK))
                    and cand not in hits):
                hits.append(cand)
    return hits


def claude_env(candidate: str, is_wsl: bool, config_dir: str | None = None) -> dict:
    """Probe environment for a claude candidate.

    When a config dir is passed, set CLAUDE_CONFIG_DIR -- and for a /mnt/
    (Windows-shim-under-WSL) candidate, auto-merge CLAUDE_CONFIG_DIR/up into
    WSLENV so the variable crosses the interop boundary (existing WSLENV
    entries are preserved).
    """
    env = dict(os.environ)
    if config_dir is not None:
        env["CLAUDE_CONFIG_DIR"] = config_dir
        if is_wsl and candidate.startswith("/mnt/"):
            parts = [p for p in env.get("WSLENV", "").split(":") if p]
            if not any(p.split("/")[0] == "CLAUDE_CONFIG_DIR" for p in parts):
                parts.append("CLAUDE_CONFIG_DIR/up")
            env["WSLENV"] = ":".join(parts)
    return env


def iter_json_objects(chunk: str):
    """Yield parseable JSON values from a chunk: the whole chunk first, then
    every independently decodable {...} object found by scanning brace
    offsets with raw_decode -- tolerates banner or notice lines around the
    JSON, brace-bearing ones included (an outer-span slice cannot)."""
    try:
        yield json.loads(chunk)
        return
    except ValueError:
        pass
    decoder = json.JSONDecoder()
    idx = chunk.find("{")
    while idx != -1:
        try:
            obj, end = decoder.raw_decode(chunk, idx)
        except ValueError:
            idx = chunk.find("{", idx + 1)
            continue
        yield obj
        idx = chunk.find("{", end)


def parse_auth_status(stdout: str, stderr: str):
    """Classify an 'auth status' probe: (state, identity, plan).

    state: logged-in | logged-out | indeterminate. Prefers the JSON shape
    (2.1.201 emits a JSON object with a loggedIn field; banner-wrapped JSON
    is found by raw_decode scanning, and only a dict carrying loggedIn
    counts); falls back to string matching for older text output. plan is
    the JSON subscriptionType field (the claude plan-tier source evidenced
    live) or None -- the text fallback never yields one.
    """
    text = (stdout or "").strip()
    for chunk in (text, (stderr or "").strip()):
        if not chunk:
            continue
        for data in iter_json_objects(chunk):
            if not (isinstance(data, dict) and "loggedIn" in data):
                continue
            plan = data.get("subscriptionType")
            plan = plan if isinstance(plan, str) and plan else None
            if not data.get("loggedIn"):
                return "logged-out", None, plan
            email = data.get("email") or ""
            org = data.get("orgName") or ""
            identity = (email + (" (" + org + ")" if org else "")).strip() or "logged in"
            return "logged-in", identity, plan
    blob = (text + "\n" + (stderr or "")).lower()
    if re.search(r"not logged in|logged out|no credentials|unauthenticated|please log ?in", blob):
        return "logged-out", None, None
    if "logged in" in blob or "email" in blob:
        m = re.search(r"[\w.+-]+@[\w.-]+", text + " " + (stderr or ""))
        return "logged-in", (m.group(0) if m else "logged in"), None
    return "indeterminate", None, None


def munge_project_path(path: str) -> str:
    """The observed projects/-store munge: every non-alphanumeric character
    becomes '-' (case preserved; lossy by construction -- never resolve a
    real path FROM a munged name)."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def neutral_probe_cwd() -> str | None:
    """The neutral cwd for pass-2 usage subprocesses, or None (inherit the
    script cwd -- its munge is excluded too) when the temp dir is missing.
    Never created by this script: read-only contract."""
    return NEUTRAL_PROBE_CWD if os.path.isdir(NEUTRAL_PROBE_CWD) else None


def default_store_root() -> str:
    """Canonical realpath of the BUILT-IN default store ~/.claude (the
    predicate's default-store exclusion key)."""
    return os.path.realpath(os.path.expanduser("~/.claude"))


def resolve_default_root() -> tuple[str, str]:
    """The default account's METADATA root (Task 2 Chosen (a)): a non-empty
    CLAUDE_CONFIG_DIR in the script's own environment wins (config_source
    "env"), else the built-in fallback ~/.claude ("builtin"). This resolves
    the metadata surface ONLY (config_dir, recent-repos enumeration).
    Identity/usage probes run the pinned CLI with no explicit config dir:
    the CLI resolves its own default independently -- with an ABSOLUTE env
    value the two coincide (the CLI inherits the same environment), but a
    RELATIVE value (the usage subprocess runs from the neutral cwd) or a
    binary with a different built-in default can diverge; the row reports
    whatever the CLI itself resolves (the "default_account extras" block
    above; divergence recipes in docs/integrations/
    cross-agent-orchestration.md).
    Returns (absolute path, "env" | "builtin")."""
    env_dir = (os.environ.get("CLAUDE_CONFIG_DIR") or "").strip()
    if env_dir:
        return os.path.abspath(os.path.expanduser(env_dir)), "env"
    return os.path.abspath(os.path.expanduser("~/.claude")), "builtin"


def is_eligible_profile_dir(path: str) -> bool:
    """The NAMED profile-eligibility predicate -- the single source of truth
    shared by enumeration, --profile-dir validation, and every consumer:
    a real directory at ~/.claude*, EXCLUDING the built-in default store
    ~/.claude itself (special default handling), *.lock control dirs, any
    dir carrying the quarantine marker, and malformed/non-directory
    entries. Realpath canonicalization resolves symlinks; the enumerator
    dedups on realpath."""
    p = os.path.abspath(os.path.expanduser(path))
    name = os.path.basename(p)
    if os.path.realpath(os.path.dirname(p)) != os.path.realpath(os.path.expanduser("~")):
        return False
    if not name.startswith(".claude") or name == ".claude":
        return False
    if name.endswith(".lock") or QUARANTINE_MARKER in name:
        return False
    real = os.path.realpath(p)
    if real == default_store_root():
        return False
    return os.path.isdir(real)


def enumerate_profile_dirs() -> list[dict]:
    """Eligible profile dirs (predicate-filtered), realpath-deduped, in
    sorted glob order. Items: {"dir": <glob path>, "real": <realpath>}."""
    out: list[dict] = []
    seen: set[str] = set()
    for d in sorted(glob.glob(os.path.expanduser("~/.claude*"))):
        if not is_eligible_profile_dir(d):
            continue
        real = os.path.realpath(d)
        if real in seen:
            continue
        seen.add(real)
        out.append({"dir": d, "real": real})
    return out


def is_memory_only_entry(entry_path: str):
    """True iff the projects entry holds NOTHING but the memory/ DIRECTORY
    artifact (the observed parent-root shape a non-git -p run leaves
    behind) -- the sole child must actually BE a directory (captured-mode
    stat.S_ISDIR semantics); a mere file named "memory" never excludes.
    False when anything else is present, including a non-directory sole
    child or a child that vanished during classification. The string
    "gone" when the entry itself vanished between stat and listing (raced
    deletion -- callers skip it silently, never emitting a stale entry).
    None when unreadable for any other reason (callers keep the entry
    VISIBLE and degrade the snapshot -- the exclusion never broadens)."""
    try:
        children = os.listdir(entry_path)
    except FileNotFoundError:
        return "gone"
    except OSError:
        return None
    if not (bool(children) and all(c == "memory" for c in children)):
        return False
    try:
        child_st = os.stat(os.path.join(entry_path, "memory"))
    except FileNotFoundError:
        return False  # child vanished: no longer the artifact shape
    except OSError:
        return None  # unclassifiable child metadata: visible + degraded
    return bool(stat.S_ISDIR(child_st.st_mode))


def enumerate_projects(config_root: str, excluded_names: set,
                       parent_token: str, now: float) -> dict:
    """ALWAYS-ON read-only recent-repos scan of <config_root>/projects.

    Pure stdlib mtime scan (no CLI call); mtime-sorted newest-first with the
    <10 min in_use heuristic. excluded_names carries the by-name exclusions
    (own cwd + neutral cwd munges); parent_token is excluded CONTENT-AWARE
    (memory-only entries only). status "absent" renders "unavailable" at
    the table layer.
    """
    out: dict = {"status": "ok", "error": None, "entries": []}
    if not config_root or not os.path.isdir(config_root):
        out["status"] = "absent"
        out["error"] = "config root is not a readable directory"
        return out
    projects = os.path.join(config_root, "projects")
    # stat() distinguishes a genuinely-missing projects/ (a fresh store:
    # ok + zero entries) from a traversal-denied root (absent -- metadata
    # unobservable must never read as an idle account); the captured mode
    # also classifies a malformed non-directory projects path truthfully
    try:
        proj_st = os.stat(projects)
    except FileNotFoundError:
        return out  # readable store with no projects/ dir: zero recent repos
    except OSError:
        out["status"] = "absent"
        out["error"] = "config root/projects metadata is not readable"
        return out
    if not stat.S_ISDIR(proj_st.st_mode):
        out["status"] = "failed"
        out["error"] = "projects path exists but is not a directory"
        return out
    try:
        names = os.listdir(projects)
    except OSError as exc:
        out["status"] = "failed"
        out["error"] = "projects/ unreadable: " + str(exc)[:120]
        return out
    unreadable = 0
    unclassifiable = 0
    for name in sorted(names):
        if name in excluded_names:
            continue
        full = os.path.join(projects, name)
        try:
            entry_st = os.stat(full)
        except FileNotFoundError:
            continue  # broken link / raced deletion: not an entry
        except OSError:
            unreadable += 1  # permission-denied metadata: truthfully counted
            continue
        if not stat.S_ISDIR(entry_st.st_mode):
            continue  # classified from the captured mode: no re-stat race
        if name == parent_token:
            mo = is_memory_only_entry(full)
            if mo is True:
                continue  # content-aware: only the memory-only artifact shape
            if mo == "gone":
                continue  # raced deletion: never emit a vanished entry
            if mo is None:
                # unreadable content: the entry stays VISIBLE (the exclusion
                # never broadens) but the snapshot degrades -- incomplete
                # classification must never read as a complete advisory
                unclassifiable += 1
        age_min = max(0.0, (now - entry_st.st_mtime) / 60.0)
        out["entries"].append({"name": name,
                               "age_min": round(age_min, 1),
                               "in_use": age_min < IN_USE_THRESHOLD_MIN})
    out["entries"].sort(key=lambda e: e["age_min"])
    if unreadable or unclassifiable:
        problems = []
        if unreadable:
            problems.append("unreadable projects entries: " + str(unreadable))
        if unclassifiable:
            problems.append("unclassifiable parent-artifact entries kept "
                            "visible: " + str(unclassifiable))
        out["status"] = "degraded"
        out["error"] = "; ".join(problems)
    return out


def usage_skipped() -> dict:
    """The claude usage placeholder (structured fields present, null)."""
    return {"status": "skipped", "headline": None, "session_pct": None,
            "session_resets": None, "week_pct": None, "week_resets": None}


def codex_usage_skipped() -> dict:
    """The codex usage placeholder (all value fields present, null)."""
    return {"status": "skipped", "error": None, "plan": None,
            "session_pct": None, "session_resets": None,
            "session_resets_at": None, "week_pct": None,
            "week_resets": None, "week_resets_at": None}


def parse_usage_line(line: str, prefix: str):
    """Exact-prefix percent-line parse -> (pct, resets_text | None) or None.

    Only the two anchored prefixes are ever passed in; the separator between
    the percent and the resets clause is never keyed on (non-ASCII on
    observed hosts) and the resets text rides verbatim (a 0% cell omits the
    clause entirely -> resets None even at status ok)."""
    if not line.startswith(prefix):
        return None
    rest = line[len(prefix):]
    m = re.match(r"\s*(\d+)%\s*used\b", rest)
    if not m:
        return None
    r = re.search(r"\bresets\s+(.+?)\s*$", rest)
    return int(m.group(1)), (r.group(1) if r else None)


def enumerate_claude_candidates(is_wsl: bool) -> list[dict]:
    """PATH hits + nvm-glob hits, environment-native first, newest-nvm first."""
    seen: dict[str, dict] = {}
    for path in which_all("claude"):
        real = os.path.realpath(path)
        if real not in seen:
            seen[real] = {"path": path, "source": "PATH"}
    for path in sorted(glob.glob(os.path.expanduser("~/.nvm/versions/node/*/bin/claude"))):
        real = os.path.realpath(path)
        if real not in seen:
            seen[real] = {"path": path, "source": "nvm-glob"}

    def version_key(entry: dict):
        m = re.search(r"/node/v(\d+)\.(\d+)\.(\d+)/", entry["path"])
        return tuple(int(g) for g in m.groups()) if m else (0, 0, 0)

    cands = list(seen.values())
    for c in cands:
        c["environment_native"] = not (is_wsl and c["path"].startswith("/mnt/"))
    cands.sort(key=lambda c: (not c["environment_native"], [-v for v in version_key(c)]))
    return cands


def isolation_probe(candidate: str, is_wsl: bool, timeout: float) -> dict:
    """The canonical bogus-dir probe: PASS (status ok) iff logged-out."""
    env = claude_env(candidate, is_wsl, BOGUS_CONFIG_DIR)
    status, out, err, _rc = run_cli([candidate, "auth", "status"], timeout, env)
    if status == "timeout":
        return {"status": "timeout", "detail": "auth status timed out (never pins)"}
    if status == "absent":
        return {"status": "failed", "detail": err}
    state, _identity, _plan = parse_auth_status(out, err)
    if state == "logged-out":
        return {"status": "ok", "detail": "logged out under bogus CLAUDE_CONFIG_DIR"}
    if state == "logged-in":
        return {"status": "failed",
                "detail": "still logged in: CLAUDE_CONFIG_DIR is not reaching the binary"}
    return {"status": "degraded", "detail": "indeterminate auth status output (never pins)"}


def option_block(help_text: str, flag: str) -> str | None:
    """The help lines belonging to one option (flag line + wrapped description)."""
    lines = help_text.split("\n")
    start = None
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith(flag + " ") or ln.lstrip() == flag:
            start = i
            break
    if start is None:
        return None
    block = [lines[start]]
    for ln in lines[start + 1:]:
        s = ln.lstrip()
        if s.startswith("-") and not s.startswith("- "):
            break
        block.append(ln)
    return "\n".join(block)


def probe_claude_help(pinned: str, timeout: float) -> dict:
    status, out, err, _rc = run_cli([pinned, "--help"], timeout)
    if status != "ok":
        return {"status": status if status in ("timeout",) else "failed",
                "aliases": [], "efforts": [],
                "error": (err or out or "").strip()[:300] or "help probe failed"}
    aliases: list[str] = []
    model_block = option_block(out, "--model")
    if model_block:
        aliases = [t for t in re.findall(r"'([A-Za-z0-9][\w.-]*)'", model_block)
                   if not t.startswith("claude-")]
    efforts: list[str] = []
    effort_block = option_block(out, "--effort")
    if effort_block:
        m = re.search(r"\(([a-z][a-z, ]+)\)", effort_block)
        if m:
            efforts = [t.strip() for t in m.group(1).split(",") if t.strip()]
    if aliases and efforts:
        st = "ok"
    elif aliases or efforts:
        st = "partial"
    else:
        st = "failed"
    return {"status": st, "aliases": aliases, "efforts": efforts,
            "error": None if st == "ok" else "help parsed but alias/effort extraction incomplete"}


def probe_claude_version(pinned: str, is_wsl: bool, timeout: float) -> dict:
    status, out, err, rc = run_cli([pinned, "--version"], timeout,
                                   claude_env(pinned, is_wsl))
    if status == "timeout":
        return {"value": None, "status": "timeout", "error": err}
    if status in ("failed", "absent"):
        return {"value": None, "status": "failed",
                "error": ("exit " + str(rc) + ": " if rc is not None else "")
                         + (err or out or "").strip()[:300]}
    first = (out or "").strip().split("\n")[0].strip()
    if VERSION_RE.match(first):
        return {"value": first, "status": "ok", "error": None}
    return {"value": None, "status": "failed",
            "error": "unexpected version output shape: " + first[:120]}


def probe_claude_advisor(pinned: str, is_wsl: bool, timeout: float, version_value):
    """BILLED acceptance probe (only behind --probe-advisor): one cheap advisored run.

    The prompt INSTRUCTS the model to consult its advisor once -- advisor use
    is opportunistic (observed live 2026-07-10: a trivial prompt completed
    clean with zero engagement), so an engagement-forcing prompt is what makes
    the probe deterministic. Engagement detector: the advisor model appears in
    the result modelUsage (end-of-run deterministic check; it also rejects the
    silent soft-strip, whose stderr warning is captured for the error detail).
    """
    status, out, err, rc = run_cli(
        [pinned, "-p",
         "Consult your advisor tool once on this question: is 2+2=4? "
         "Then reply with exactly: ok",
         "--model", ADVISOR_MAIN,
         "--advisor", ADVISOR_MODEL, "--output-format", "json"],
        max(timeout, 180.0), claude_env(pinned, is_wsl))
    if status == "timeout":
        return {"value": None, "status": "timeout", "error": err, "version": None}
    if status in ("failed", "absent"):
        return {"value": None, "status": "failed",
                "error": ("exit " + str(rc) + ": " if rc is not None else "")
                         + (err or out or "").strip()[:300],
                "version": None}
    result = None
    try:
        result = json.loads(out)
    except ValueError:
        for line in reversed((out or "").strip().split("\n")):
            if line.startswith("{"):
                try:
                    result = json.loads(line)
                except ValueError:
                    result = None
                break
    if not isinstance(result, dict):
        return {"value": None, "status": "failed",
                "error": "unparseable advisor-probe result output", "version": None}
    usage_models = list((result.get("modelUsage") or {}).keys())
    if any(ADVISOR_MODEL in m for m in usage_models):
        return {"value": True, "status": "ok", "error": None,
                "version": version_value}  # only an actually-parsed version attributes
    if "cannot advise" in (err or ""):
        return {"value": None, "status": "failed",
                "error": "advisor silently stripped (stderr pairing warning): "
                         + err.strip()[:200],
                "version": None}
    return {"value": None, "status": "failed",
            "error": "completed without advisor engagement evidence "
                     "(no " + ADVISOR_MODEL + " model in modelUsage)",
            "version": None}


def probe_identity(pinned: str, is_wsl: bool, timeout: float,
                   config_dir: str | None) -> dict:
    env = claude_env(pinned, is_wsl, config_dir)
    status, out, err, _rc = run_cli([pinned, "auth", "status"], timeout, env)
    if status == "timeout":
        return {"identity": None, "status": "timeout", "plan": None}
    if status == "absent":
        return {"identity": None, "status": "failed", "plan": None}
    state, identity, plan = parse_auth_status(out, err)
    if state == "logged-in":
        return {"identity": identity, "status": "ok", "plan": plan}
    if state == "logged-out":
        return {"identity": None, "status": "degraded",
                "plan": None}  # enumerable but not logged in
    return {"identity": None, "status": "degraded", "plan": None}


def probe_usage(pinned: str, is_wsl: bool, timeout: float,
                config_dir: str | None, cwd: str | None = None) -> dict:
    """Per-account /usage probe: unchanged status/headline behaviour plus
    the structured session/week fields (see the docstring mapping -- exact
    line anchors only; parse failure leaves the fields null alongside the
    unchanged headline)."""
    env = claude_env(pinned, is_wsl, config_dir)
    status, out, err, _rc = run_cli(
        [pinned, "-p", "/usage", "--output-format", "text"],
        max(timeout, 30.0), env, cwd=cwd)
    result = usage_skipped()
    if status == "timeout":
        result.update(status="timeout", headline=None)
        return result
    if status in ("failed", "absent"):
        result.update(status="failed",
                      headline=(err or out or "").strip()[:200] or None)
        return result
    lines = [ln.strip() for ln in (out or "").split("\n")]
    pct_lines = [ln for ln in lines if "%" in ln]
    if not pct_lines:
        # the logged-out local-stats block lands here: no % lines at all
        result.update(status="degraded",
                      headline=(out or "").strip()[:200] or None)
        return result
    result.update(status="ok", headline=" | ".join(pct_lines[:4]))
    for ln in lines:
        if result["session_pct"] is None:
            hit = parse_usage_line(ln, SESSION_LINE_PREFIX)
            if hit is not None:
                result["session_pct"], result["session_resets"] = hit
                continue
        if result["week_pct"] is None:
            hit = parse_usage_line(ln, WEEK_ALL_LINE_PREFIX)
            if hit is not None:
                result["week_pct"], result["week_resets"] = hit
    return result


def probe_codex(timeout: float) -> dict:
    status, out, err, rc = run_cli(["codex", "debug", "models"], timeout)
    if status == "absent":
        return {"status": "absent", "error": err, "listed_count": 0,
                "total_count": 0, "models": []}
    if status == "timeout":
        return {"status": "timeout", "error": err, "listed_count": 0,
                "total_count": 0, "models": []}
    if status == "failed":
        return {"status": "failed",
                "error": ("exit " + str(rc) + ": " if rc is not None else "")
                         + (err or out or "").strip()[:300],
                "listed_count": 0, "total_count": 0, "models": []}
    try:
        data = json.loads(out)
    except ValueError:
        return {"status": "failed", "error": "catalog output is not valid JSON",
                "listed_count": 0, "total_count": 0, "models": []}
    raw = data.get("models") if isinstance(data, dict) else data
    if not isinstance(raw, list):
        return {"status": "failed", "error": "catalog JSON has no models list",
                "listed_count": 0, "total_count": 0, "models": []}
    models = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        levels = entry.get("supported_reasoning_levels") or []
        efforts = [l.get("effort") for l in levels
                   if isinstance(l, dict) and l.get("effort")]
        models.append({
            "slug": entry.get("slug") or entry.get("id"),
            "display_name": entry.get("display_name") or entry.get("name"),
            "visibility": entry.get("visibility"),
            "default_effort": entry.get("default_reasoning_level"),
            "efforts": efforts,
            "priority": entry.get("priority"),
        })
    listed = [m for m in models if m["visibility"] == "list"]
    listed.sort(key=lambda m: (m["priority"] is None,
                               m["priority"] if isinstance(m["priority"], int) else 0))
    return {"status": "ok" if listed else "partial",
            "error": None if listed else "catalog parsed but no listed models",
            "listed_count": len(listed), "total_count": len(models),
            "models": listed}


def probe_codex_usage(timeout: float) -> dict:
    """The codex app-server account/rateLimits/read usage probe (--usage).

    Popen-based BY DESIGN, never run_cli: the server exits on closed stdin,
    so stdin must stay OPEN across the exchange -- write initialize (id:1),
    sleep, write the rate-limit request (id:2), sleep out the response
    window, then close stdin (communicate) and collect. The deadline is
    max(timeout, 30) with the scripted sleeps INSIDE it; the finally block
    terminates -> bounded-waits -> kills -> reaps the RECORDED child on
    every success/failure/timeout path (recorded identity only -- never
    broad process matching). The response is correlated on the rate-limit
    request id ONLY; initialize responses, notifications, and banner lines
    are tolerated and ignored. Windows classify by windowDurationMins
    (300 session / 10080 week), never by primary/secondary position.
    """
    result = codex_usage_skipped()
    result.update(status="failed")
    deadline = max(timeout, 30.0)
    try:
        proc = subprocess.Popen(
            ["codex", "app-server"], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            cwd=neutral_probe_cwd())
    except FileNotFoundError:
        result.update(status="absent", error="executable not found: codex")
        return result
    except OSError as exc:
        result.update(status="failed", error=str(exc)[:200])
        return result
    t0 = time.monotonic()
    stdout_data = ""
    stderr_data = ""
    timed_out = False
    write_error = None
    # newest TimeoutExpired partials (CPython reports the FULL accumulated
    # buffer on each timeout, as bytes even in text mode; a later successful
    # communicate() returns that same accumulation, so partials are consumed
    # ONLY when no communicate() ever succeeds -- never double-appended)
    partial = {"out": None, "err": None}

    def remaining() -> float:
        return deadline - (time.monotonic() - t0)

    def _to_text(data) -> str:
        if data is None:
            return ""
        if isinstance(data, bytes):
            return data.decode("utf-8", "replace")
        return data

    def note_partial(exc) -> None:
        if exc.stdout is not None:
            partial["out"] = exc.stdout
        if exc.stderr is not None:
            partial["err"] = exc.stderr

    try:
        try:
            proc.stdin.write(CODEX_USAGE_INIT_REQ + "\n")
            proc.stdin.flush()
            time.sleep(max(0.0, min(CODEX_USAGE_INIT_WINDOW_S, remaining())))
            proc.stdin.write(CODEX_USAGE_RATE_REQ + "\n")
            proc.stdin.flush()
            time.sleep(max(0.0, min(CODEX_USAGE_RESPONSE_WINDOW_S, remaining())))
        except OSError as exc:
            write_error = str(exc)[:200]
        try:
            # communicate() closes stdin (the response window is over), then
            # collects output and waits for the server's clean exit.
            out_rest, err_rest = proc.communicate(timeout=max(1.0, remaining()))
            stdout_data += out_rest or ""
            stderr_data += err_rest or ""
            partial = {"out": None, "err": None}  # subsumed by the return
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            note_partial(exc)
    finally:
        # recorded-identity cleanup, guaranteed on every path: drain the
        # boundary output (preserving timeout partials so a captured id:2
        # is never lost), terminate -> bounded wait -> kill, close OUR
        # descriptors, then reap the recorded child independently of pipe
        # EOF (a descendant holding the pipes must not block the reap).
        # Only ever the Popen handle recorded above -- never any other
        # process.
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    out_rest, err_rest = proc.communicate(timeout=5.0)
                    stdout_data += out_rest or ""
                    stderr_data += err_rest or ""
                    partial = {"out": None, "err": None}
                except subprocess.TimeoutExpired as exc:
                    note_partial(exc)
                    proc.kill()
                    try:
                        out_rest, err_rest = proc.communicate(timeout=5.0)
                        stdout_data += out_rest or ""
                        stderr_data += err_rest or ""
                        partial = {"out": None, "err": None}
                    except subprocess.TimeoutExpired as exc2:
                        note_partial(exc2)
                    except (ValueError, OSError):
                        pass
                except (ValueError, OSError):
                    pass
            else:
                # exited between the timeout and this poll: drain so a
                # response at the deadline edge is not lost
                try:
                    out_rest, err_rest = proc.communicate(timeout=5.0)
                    stdout_data += out_rest or ""
                    stderr_data += err_rest or ""
                    partial = {"out": None, "err": None}
                except subprocess.TimeoutExpired as exc:
                    note_partial(exc)
                except (ValueError, OSError):
                    pass
        except OSError:
            pass  # terminate/kill raced an already-gone child
        finally:
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                try:
                    if stream is not None and not stream.closed:
                        stream.close()
                except OSError:
                    pass
            try:
                proc.wait(timeout=5.0)  # reap regardless of pipe state
            except (subprocess.TimeoutExpired, OSError):
                pass

    # no communicate() ever succeeded: consume the newest timeout partials
    # (the full accumulated buffers) so a deadline-edge response still parses
    stdout_data += _to_text(partial["out"])
    stderr_data += _to_text(partial["err"])

    resp = None
    for line in stdout_data.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue  # banner/notice lines tolerated
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        # exact-id correlation ONLY: the initialize response (id:1) and
        # id-less notifications are tolerated and ignored
        if isinstance(obj, dict) and obj.get("id") == CODEX_USAGE_RATE_ID:
            resp = obj
    if resp is None:
        # precedence: a captured response would have won above; a concrete
        # transport/write failure is never hidden by the later timeout state
        if write_error:
            result.update(status="failed",
                          error="request write failed: " + write_error)
        elif timed_out:
            result.update(status="timeout",
                          error="no rate-limit response within "
                                + str(deadline) + "s")
        else:
            result.update(status="failed",
                          error="no id:" + str(CODEX_USAGE_RATE_ID)
                                + " response; stderr: "
                                + (stderr_data or "").strip()[:200])
        return result
    if not isinstance(resp.get("result"), dict):
        detail = resp.get("error")
        result.update(status="failed",
                      error="rate-limit response carries no result object"
                            + (": " + json.dumps(detail)[:200] if detail else ""))
        return result
    limits = resp["result"].get("rateLimits")
    if not isinstance(limits, dict):
        result.update(status="degraded",
                      error="response parsed but no rateLimits object (shape drift)")
        return result
    plan = limits.get("planType")
    result["plan"] = plan if isinstance(plan, str) and plan else None
    classified = 0
    for cell in (limits.get("primary"), limits.get("secondary")):
        if not isinstance(cell, dict):
            continue  # either window may be absent (observed: secondary null)
        dur = cell.get("windowDurationMins")
        if dur == CODEX_SESSION_WINDOW_MINS:
            key = "session"
        elif dur == CODEX_WEEK_WINDOW_MINS:
            key = "week"
        else:
            continue  # unknown window duration: drift-tolerated, never guessed
        if result[key + "_pct"] is not None:
            continue
        pct = cell.get("usedPercent")
        if isinstance(pct, (int, float)) and not isinstance(pct, bool):
            result[key + "_pct"] = pct
            classified += 1
        resets_at = cell.get("resetsAt")
        if isinstance(resets_at, (int, float)) and not isinstance(resets_at, bool):
            result[key + "_resets_at"] = resets_at
            try:
                result[key + "_resets"] = (
                    datetime.fromtimestamp(resets_at).astimezone()
                    .isoformat(timespec="minutes"))
            except (OverflowError, OSError, ValueError):
                result[key + "_resets"] = None
    if classified:
        result.update(status="ok", error=None)
    else:
        result.update(status="degraded",
                      error="rateLimits parsed but no recognizable "
                            "windowDurationMins (300/10080)")
    return result


def probe_claude(args, is_wsl: bool) -> dict:
    out: dict = {"status": "failed", "error": None, "candidates": [], "pinned": None,
                 "help": {"status": "skipped", "aliases": [], "efforts": [], "error": None},
                 "version": {"value": None, "status": "skipped", "error": None},
                 "advisor": {"value": None, "status": "skipped", "error": None,
                             "version": None},
                 "profile_dir_filter": None,
                 "default_account": {"identity": None, "status": "skipped",
                                     "plan": None, "usage": usage_skipped()},
                 "profiles": []}
    cands = enumerate_claude_candidates(is_wsl)
    if not cands:
        out["status"] = "absent"
        out["error"] = "no claude candidate on PATH or under ~/.nvm/versions/node/*/bin"
        return out
    pinned = None
    for cand in cands:
        cand["isolation_probe"] = isolation_probe(cand["path"], is_wsl, args.timeout)
        if pinned is None and cand["isolation_probe"]["status"] == "ok":
            pinned = cand["path"]  # only an observed logged-out PASS pins
    out["candidates"] = cands
    if pinned is None:
        out["status"] = "no-candidate-passed"
        out["error"] = ("candidates found but none passed the bogus-dir isolation "
                        "probe; the wizard fires the environment-readiness pause")
        return out
    out["pinned"] = pinned

    # ---- pass 1 (pure stdlib, no CLI subprocess): account census + the
    # projects/ recent-repos snapshot. The snapshot precedes EVERY store-
    # touching pass-2 subprocess so the advisory input is pre-probe truth.
    now = time.time()
    excluded = {munge_project_path(os.path.abspath(os.getcwd())),
                munge_project_path(os.path.realpath(os.getcwd())),
                munge_project_path(NEUTRAL_PROBE_CWD)}
    parent_token = munge_project_path(os.path.dirname(NEUTRAL_PROBE_CWD))
    default_dir, default_source = resolve_default_root()
    default_real = os.path.realpath(default_dir)
    prof_entries = enumerate_profile_dirs()
    requested = args.profile_dir or None
    if requested:
        by_real = {p["real"]: p for p in prof_entries}
        selected: list[dict] = []
        invalid: list[str] = []
        seen: set[str] = set()
        # the reserved literal is EXCLUSIVE: 'default' selects the default
        # account alone, so any co-specified dir is reported invalid and a
        # default-only selection can never probe a named profile
        default_only = "default" in requested
        for raw in requested:
            if raw == "default":
                continue
            if default_only:
                invalid.append(raw)
                continue
            cand_path = os.path.abspath(os.path.expanduser(raw))
            real = os.path.realpath(cand_path)
            hit = by_real.get(real)
            if hit is None or not is_eligible_profile_dir(cand_path):
                invalid.append(raw)
                continue
            if real in seen:
                continue
            seen.add(real)
            selected.append(hit)
        prof_entries = selected
        out["profile_dir_filter"] = {"requested": list(requested),
                                     "selected": [p["dir"] for p in selected],
                                     "invalid": invalid}
    alias_hit = next((p["dir"] for p in prof_entries
                      if p["real"] == default_real), None)
    snapshots = {p["real"]: enumerate_projects(p["dir"], excluded,
                                               parent_token, now)
                 for p in prof_entries}
    default_projects = enumerate_projects(default_dir, excluded,
                                          parent_token, now)

    # ---- binary-surface probes (no profile-store -p run): help, version,
    # advisor (the advisor probe is billed and gated behind its own flag)
    out["help"] = probe_claude_help(pinned, args.timeout)
    out["version"] = probe_claude_version(pinned, is_wsl, args.timeout)
    if args.probe_advisor:
        out["advisor"] = probe_claude_advisor(pinned, is_wsl, args.timeout,
                                              out["version"]["value"])

    # ---- pass 2 (store-touching CLI): identity + usage per account, from
    # the neutral cwd so probe-created entries land under excluded munges
    probe_cwd = neutral_probe_cwd()
    ident = probe_identity(pinned, is_wsl, args.timeout, None)
    ident["usage"] = (probe_usage(pinned, is_wsl, args.timeout, None,
                                  cwd=probe_cwd)
                      if args.usage else usage_skipped())
    ident["config_dir"] = default_dir
    ident["config_source"] = default_source
    ident["aliases_profile"] = alias_hit
    ident["recent_repos"] = default_projects
    out["default_account"] = ident
    for p in prof_entries:
        prof = {"dir": p["dir"]}
        prof.update(probe_identity(pinned, is_wsl, args.timeout, p["dir"]))
        prof["usage"] = (probe_usage(pinned, is_wsl, args.timeout, p["dir"],
                                     cwd=probe_cwd)
                         if args.usage else usage_skipped())
        prof["recent_repos"] = snapshots[p["real"]]
        out["profiles"].append(prof)
    out["status"] = "ok" if out["help"]["status"] == "ok" else "degraded"
    if out["status"] == "degraded":
        out["error"] = "help parse incomplete: alias/effort menus degrade to free-text entry"
    return out


def loop_config_parses(config: str) -> bool:
    """Forward-compat rule: the line parses iff >=1 key=value group parses."""
    parsed = 0
    for group in config.split(";"):
        toks = group.strip().split()
        if toks and all(CONFIG_TOKEN_RE.match(t) for t in toks):
            parsed += 1
    return parsed > 0


def scan_plan_file(path: Path):
    """Heading-scoped, fence-skipping scan of one plan file.

    Returns (leads_active, loop_config_or_None). Fenced lines never count for
    headings or bullets, so quoted examples cannot false-positive.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    section = None
    in_fence = False
    first_lifecycle_line = None
    loop_config = None
    for raw in text.split("\n"):
        line = raw.rstrip()
        if line.lstrip().startswith(FENCE):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("## ") and not line.startswith("###"):
            section = line[3:].strip()
            continue
        if section == "Lifecycle State" and first_lifecycle_line is None and line.strip():
            first_lifecycle_line = line.strip()
        if (section == "Current State / Handoff Note" and loop_config is None
                and line.strip().startswith(LOOP_CONFIG_PREFIX.strip() + " ")):
            candidate = line.strip()[len(LOOP_CONFIG_PREFIX):].strip()
            if loop_config_parses(candidate):
                loop_config = candidate
    leads_active = bool(first_lifecycle_line
                        and re.sub(r"^[-*]\s+", "", first_lifecycle_line).startswith("Active"))
    return leads_active, loop_config


def probe_plans(plans_dir: str) -> dict:
    out: dict = {"status": "ok", "plans_dir": plans_dir, "scanned": 0,
                 "active_candidates": [], "non_active_with_config": 0,
                 "archived_fallback": None,
                 "q1_offer": {"offer": "none", "plan": None, "label": None, "reason": ""}}
    base = Path(plans_dir)
    if not base.is_dir():
        out["status"] = "absent"
        out["q1_offer"]["reason"] = "plans directory not found -- offer omitted"
        return out
    live_errors = 0
    archived_errors = 0
    for f in sorted(base.glob("*.md")):
        out["scanned"] += 1
        try:
            leads_active, config = scan_plan_file(f)
        except OSError:
            live_errors += 1
            continue
        if config is None:
            continue
        if leads_active:
            out["active_candidates"].append({"file": f.name, "loop_config": config})
        else:
            out["non_active_with_config"] += 1
    actives = out["active_candidates"]
    offer = out["q1_offer"]
    # Fail closed on an incomplete scan: an unreadable file could hide an
    # Active candidate, so neither the exactly-one rule nor the archived
    # fallback's no-Active premise is established -- a partial scan never
    # offers reuse.
    if live_errors:
        offer.update(offer="none", plan=None, label=None,
                     reason="plan scan incomplete: " + str(live_errors)
                            + " unreadable file(s) -- offer omitted "
                            "(exactly-one-Active not established)")
    elif len(actives) == 1:
        offer.update(offer="active", plan=actives[0]["file"],
                     label="same as last run -- " + actives[0]["file"],
                     reason="exactly one Active plan with a parseable Loop config: line")
    elif len(actives) > 1:
        offer.update(offer="none", plan=None, label=None,
                     reason="multiple Active candidates (" + str(len(actives))
                            + ") -- offer omitted")
    else:
        best = None
        for f in sorted((base / "completed").glob("*.md")):
            try:
                _active, config = scan_plan_file(f)
            except OSError:
                archived_errors += 1
                continue
            if config is None:
                continue
            mtime = f.stat().st_mtime
            if best is None or mtime > best[0]:
                best = (mtime, f.name, config)
        if archived_errors:
            offer.update(offer="none", plan=None, label=None,
                         reason="archived scan incomplete: " + str(archived_errors)
                                + " unreadable file(s) -- offer omitted "
                                "(newest-archived not established)")
        elif best is not None:
            out["archived_fallback"] = {"file": best[1], "loop_config": best[2]}
            offer.update(offer="archived", plan=best[1],
                         label="same as last run (from archived plan " + best[1] + ")",
                         reason="no Active plan qualifies; single most recently "
                                "modified archived plan with a parseable "
                                "Loop config: line")
        else:
            offer.update(offer="none", plan=None, label=None,
                         reason="zero candidates in both locations -- offer omitted")
    if live_errors or archived_errors:
        out["status"] = "partial"
    return out


def build_report_line(codex: dict, claude: dict, plans: dict) -> str:
    if codex["status"] == "ok":
        codex_seg = "codex OK (" + str(codex["listed_count"]) + " models)"
    elif codex["status"] == "absent":
        codex_seg = "codex ABSENT"
    elif codex["status"] == "timeout":
        codex_seg = "codex TIMEOUT"
    elif codex["status"] == "partial":
        codex_seg = "codex PARTIAL (no listed models)"
    else:
        codex_seg = "codex FAILED"
    if claude["status"] in ("ok", "degraded"):
        ver = claude["version"]["value"]
        bits = []
        if ver:
            bits.append("v" + ver.split()[0])
        bits.append(str(len(claude["help"]["aliases"])) + " aliases")
        n_prof = len(claude["profiles"])
        bits.append(str(n_prof) + (" profile" if n_prof == 1 else " profiles"))
        claude_seg = ("claude " + ("OK" if claude["status"] == "ok" else "DEGRADED")
                      + " (" + "; ".join([bits[0], ", ".join(bits[1:])] if ver else
                                         [", ".join(bits)]) + ")")
    elif claude["status"] == "no-candidate-passed":
        claude_seg = "claude NO-CANDIDATE-PASSED (environment-readiness pause)"
    elif claude["status"] == "absent":
        claude_seg = "claude ABSENT"
    else:
        claude_seg = "claude FAILED"
    offer = plans["q1_offer"]
    n_active = len(plans.get("active_candidates", []))
    if plans["status"] == "failed":
        reason = " ".join((offer.get("reason") or "scan failed").split())
        plans_seg = ("plans: " + reason.replace("|", "/")[:120]
                     + " (offer omitted)")
    elif plans["status"] == "partial":
        # a partial scan never carries an offer (probe_plans fails closed);
        # checked before the offer branches so an incomplete scan can never
        # render as a clean success
        reason = " ".join((offer.get("reason") or "scan incomplete").split())
        plans_seg = "plans: scan PARTIAL; " + reason.replace("|", "/")[:120]
    elif offer["offer"] == "active":
        plans_seg = ("plans: 1 Active candidate (offer: " + offer["label"] + ")")
    elif offer["offer"] == "archived":
        plans_seg = ("plans: 0 Active; archived fallback " + offer["plan"])
    elif n_active > 1:
        plans_seg = ("plans: " + str(n_active)
                     + " Active candidates (offer omitted: multiple)")
    elif plans["status"] == "absent":
        plans_seg = "plans: no plans directory (offer omitted)"
    else:
        plans_seg = "plans: no Loop config candidates (offer omitted)"
    return ("Probes: " + codex_seg + " | " + claude_seg + " | cursor "
            + CURSOR_PLACEHOLDER + " | " + plans_seg)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run the execute-loop wizard Step 0 probes; emit one JSON document.")
    ap.add_argument("--usage", action="store_true",
                    help="run the per-account usage probes for both families: "
                         "claude per-profile /usage (structured fields + "
                         "headline) and the codex app-server rateLimits "
                         "exchange (slow; wizard and probe submode run this "
                         "lazily)")
    ap.add_argument("--profile-dir", dest="profile_dir", action="append",
                    metavar="DIR",
                    help="repeatable: restrict claude enumeration + usage "
                         "probing to the named eligible profile dir(s) plus "
                         "the default account; the literal value 'default' "
                         "selects the default account alone; skips the codex "
                         "usage leg")
    ap.add_argument("--probe-advisor", dest="probe_advisor", action="store_true",
                    help="run the BILLED advisor acceptance probe (one advisored spawn)")
    ap.add_argument("--timeout", type=float, default=15.0,
                    help="per-subprocess timeout in seconds (default 15)")
    ap.add_argument("--plans-dir", default=".cursor/plans",
                    help="plans directory for the Q1 scan (default .cursor/plans)")
    args = ap.parse_args()

    is_wsl = host_is_wsl()
    doc: dict = {
        "probe_schema": 1,
        "generated": datetime.now().astimezone().isoformat(timespec="seconds"),
        "host": {"platform": sys.platform, "is_wsl": is_wsl,
                 "python": platform.python_version()},
        "capabilities": ["profile-dir-filter"],
    }
    try:
        doc["codex"] = probe_codex(args.timeout)
    except Exception as exc:  # never let one probe kill the document
        doc["codex"] = {"status": "failed", "error": "internal: " + str(exc)[:200],
                        "listed_count": 0, "total_count": 0, "models": []}
    try:
        doc["claude"] = probe_claude(args, is_wsl)
    except Exception as exc:
        doc["claude"] = {"status": "failed", "error": "internal: " + str(exc)[:200],
                         "candidates": [], "pinned": None,
                         "help": {"status": "failed", "aliases": [], "efforts": [],
                                  "error": None},
                         "version": {"value": None, "status": "failed", "error": None},
                         "advisor": {"value": None, "status": "skipped", "error": None,
                                     "version": None},
                         "default_account": {"identity": None, "status": "failed",
                                             "plan": None,
                                             "usage": {"status": "skipped",
                                                       "headline": None,
                                                       "session_pct": None,
                                                       "session_resets": None,
                                                       "week_pct": None,
                                                       "week_resets": None}},
                         "profiles": []}
    # The codex usage leg runs AFTER probe_claude so every projects/
    # snapshot precedes every usage subprocess (snapshot-before-usage, both
    # families); it is skipped under --profile-dir (a claude-only re-check).
    if args.usage and not args.profile_dir:
        try:
            doc["codex"]["usage"] = probe_codex_usage(args.timeout)
        except Exception as exc:
            fallback = codex_usage_skipped()
            fallback.update(status="failed", error="internal: " + str(exc)[:200])
            doc["codex"]["usage"] = fallback
    else:
        doc["codex"]["usage"] = codex_usage_skipped()
    doc["cursor"] = {"status": "in-context",
                     "note": "no shell surface exists; the composer enumerates "
                             "in-context subagent slugs"}
    try:
        doc["plans"] = probe_plans(args.plans_dir)
    except Exception as exc:
        doc["plans"] = {"status": "failed", "plans_dir": args.plans_dir, "scanned": 0,
                        "active_candidates": [], "non_active_with_config": 0,
                        "archived_fallback": None,
                        "q1_offer": {"offer": "none", "plan": None, "label": None,
                                     "reason": "scan failed: " + str(exc)[:120]}}
    doc["report_line"] = build_report_line(doc["codex"], doc["claude"], doc["plans"])
    print(json.dumps(doc, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
