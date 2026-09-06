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
                                  "week_pct": null, "week_resets": null,
                                  "usage_quality": "none", "usage_source": "none",
                                  "availability_band": "unknown",
                                  "limit_status": null, "limit_utilization": null,
                                  "limit_resets_at": null, "limit_resets": null},
                        "config_dir": "/home/user/.claude",
                        "config_source": "builtin",
                        "aliases_profile": null,
                        "marker_email": null,
                        "recent_repos": {"status": "ok", "error": null, "entries": [
                            {"name": "-home-user-projects-example-app",
                             "age_min": 4.2, "in_use": true}]}},
    "profiles": [
      {"dir": "/home/user/.claude-work", "identity": "work@example.com (Work Org)",
       "status": "ok", "plan": "max",
       "marker_email": null,
       "usage": {"status": "ok",
                 "headline": "Current session: 12% used - resets Jul 20, 9pm "
                             "(Area/City) | Current week (all models): 34% used "
                             "- resets Jul 27, 1pm (Area/City)",
                 "session_pct": 12, "session_resets": "Jul 20, 9pm (Area/City)",
                 "week_pct": 34, "week_resets": "Jul 27, 1pm (Area/City)",
                 "usage_quality": "exact", "usage_source": "panel",
                 "availability_band": "allowed",
                 "limit_status": null, "limit_utilization": null,
                 "limit_resets_at": null, "limit_resets": null},
       "recent_repos": {"status": "ok", "error": null, "entries": [
           {"name": "-home-user-projects-other-repo",
            "age_min": 3.0, "in_use": true}]}}
    ],
    "pool_ranking": {"recommended": "/home/user/.claude-work",
                     "reason": "band=allowed; idle; most headroom",
                     "bands": {"default": "warning",
                               "/home/user/.claude-work": "allowed"}}
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

- claude usage (LAYERED probe, v32 TD.1 -- only behind --usage; probe_schema
  stays 1, every new field ADDITIVE-optional in both UPDATE ONLY skew
  directions). Print-mode /usage on CLI 2.1.226+ NEVER returns quota lines
  (verified live 2026-08-10), so the probe layers three evidence sources,
  best-first, each failure falling through silently:
    1. tmux interactive-panel probe (preferred; UNBILLED; exact at every
       usage level). Runs the pinned CLI interactively inside a throwaway
       private-socket tmux session (unique -L label + session name; killed
       in finally on every path; bounded by a hard deadline), sends
       "/usage", captures the pane, and parses the panel: line-wrapped
       bars are parsed ACROSS lines; "Per-model breakdown unavailable
       (rate limited)" can coexist with valid bars and never blocks; a
       panel missing the week line gets ONE "r" retry; a workspace-trust
       prompt is answered once. SEATED-STORE ONLY: the canonical
       CLAUDE_CODE_OAUTH_TOKEN is stripped from the panel subprocess env
       (a token in the env suppresses the quota bars -- verified live
       2026-08-10). tmux absent/timeout/unparseable -> fall through.
       No-file-creation note: the tmux SERVER creates its own socket
       under the system tmux dir OUTSIDE the repo (plus the CLI's own
       store writes, as any probe invocation); the script itself still
       creates nothing.
       -> usage_quality "exact", usage_source "panel".
    2. ONE billed fallback call: '<pinned> -p "/usage" --output-format
       stream-json --verbose' (retry-once on timeout/failed per v30.1;
       absent never retries). An older CLI that still prints quota lines
       yields EXACT print evidence from the result text (usage_source
       "print" -- the old/new-CLI skew path, exact-prefix anchors below);
       on 2.1.226+ the stream's rate_limit_event yields THRESHOLD
       evidence: rate_limit_info.status allowed | allowed_warning |
       rejected (+ utilization/resetsAt when exposed). Exact utilization
       only appears past the ~75% warning threshold -- below it "allowed"
       means healthy headroom, never a percentage.
       -> usage_quality "exact"/"threshold", usage_source
       "print"/"rate-limit-event".
    3. Degraded: no panel, no % lines, no event -> the existing
       degraded/headline path (usage_quality "none", usage_source "none").
  Threshold evidence is NEVER rendered as a percentage: session_pct /
  week_pct stay null on threshold evidence; the raw event rides the
  additive limit_status / limit_utilization / limit_resets_at /
  limit_resets fields (limit_utilization is machine evidence for the
  final ranking tie-break only -- never a usage display value; the
  threshold headline is percentage-free by construction).
  availability_band (additive, every usage entry) maps ANY observation
  into the shared bands: allowed | warning | rejected | unknown --
  exact percentages band by the SAME thresholds as threshold events
  (>= 100 rejected, >= 75 warning), so the two evidence classes rank
  on one dimension (PR-MED-010).
  Exact-parse anchors (print + panel alike): session_pct/session_resets
  parse ONLY from the exact "Current session:" line and week_pct/
  week_resets ONLY from the exact "Current week (all models):" line;
  model-specific "Current week (<Model>):" lines and insight/contribution
  percentage lines are NEVER substituted (all-models line absent ->
  week_pct stays null, never another percentage). The separator between
  the percent and the resets clause is a non-ASCII middle dot on observed
  hosts and is never keyed on; resets text is carried verbatim (hour-only
  shapes observed; minute-bearing tolerated as forward-compat). A 0% cell
  omits its resets clause entirely, so reset fields are nullable even at
  status ok. A logged-out store's /usage carries no % lines -> the
  degraded/headline path, unchanged. Structured-parse failure never
  changes status or headline: the structured fields simply stay null
  alongside them.

- claude.pool_ranking (additive; emitted only when --usage ran) -- the
  TWO-DIMENSIONAL availability-first ranking (PR-MED-010) computed by
  rank_pool_candidates() over the default account + every probed profile:
  dimension 1, availability bands DECIDE (rejected/exhausted pools are
  NEVER recommended regardless of evidence quality; allowed beats
  warning); dimension 2, within a band the existing idle-first /
  most-headroom tie rules apply (the recent-repos completeness rule
  gates idle ranking), with evidence fidelity (exact > threshold) +
  freshness only as the FINAL tie-breaker. Incomparable or degraded
  observations produce an explicit no-recommendation ("recommended":
  null + a reason), never a silent guess. The wizard's menu prose
  applies the same rule; this field is the mechanical form.

- profile-email.txt identity markers (v32 TD.3; additive "marker_email"
  on default_account + every profile row) -- the CLAUDE_PROFILE_EMAILS
  labeling channel (writer: the cloud boot script, kount-side). Read
  under the PINNED SAFE-READ contract (PR-MED-005): a no-follow open of
  a REGULAR file inside the already-approved profile dir (O_NOFOLLOW +
  post-open fstat regular-file check on the OPENED descriptor, so a
  replacement race cannot swap in a symlink/FIFO/device), bounded to
  one short UTF-8 line under the pinned email grammar; invalid,
  oversized, multi-line/control-character, symlinked, special-file, or
  unreadable markers degrade fail-silent to null -- raw marker content
  never reaches JSON, stdout, or stderr.

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
  Paused plans (v32, additive): a lifecycle section leading with 'Paused' is
  reported in the additive 'paused_plans' list ({file, since, reason,
  has_loop_config} -- the two fields read from the section's 'Paused since:'/
  'Paused reason:' bullets, "" when absent). A Paused plan is NEVER an Active
  candidate and never offered for reuse; the wizard surfaces it as
  recoverable (resume = /load-plan's explicit Paused -> Active transition).

- report_line -- preassembled four-segment probe report with EXACTLY ONE
  composer-filled placeholder, the literal token {CURSOR_SLUGS} in the cursor
  segment (no shell surface exists for Cursor slugs; the composer replaces
  the token with its in-context enumeration and prints the line verbatim).

Flags:
    --usage          run the per-account usage probes for BOTH families:
                     the claude LAYERED probe per account (tmux panel,
                     unbilled/exact, up to ~45s -> one billed stream-json
                     fallback carrying print or rate_limit_event evidence
                     -> degraded; the claude-usage mapping block above)
                     and the codex app-server rateLimits exchange (~10s).
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
never creates a file or directory anywhere -- the usage panel probe's
throwaway tmux SERVER creates its own socket under the system tmux dir
outside the repo, and CLI probe invocations refresh their own stores, both
disclosed subprocess effects, not script writes), no literal triple-backtick
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

# Token-pool environment matrix (v32 TD.2 / PR-HIGH-009). The numbered
# pool variables and the wrapper's selector are SPAWN-TRANSPORT inputs,
# never probe inputs: they are stripped BY NAME from every claude probe
# subprocess (values are never read, compared, or logged here). The
# canonical env-auth variable stays by default (per-dir credentials
# outrank it in 2.1.x); the interactive panel probe is the one
# seated-store-only surface that also strips it.
CANONICAL_TOKEN_VAR = "CLAUDE_CODE_OAUTH_TOKEN"
NUMBERED_TOKEN_RE = re.compile(r"^CLAUDE_CODE_OAUTH_TOKEN_[1-9][0-9]*$")
TOKEN_SELECTOR_VAR = "LOOP_OAUTH_TOKEN_ENV"

# Layered usage probe (v32 TD.1). Bands are shared by exact and threshold
# evidence so ranking has ONE availability dimension (PR-MED-010): an
# exact percentage >= RATE_REJECTED_PCT is "rejected" (exhausted) and
# >= RATE_WARNING_PCT is "warning" -- the same thresholds the CLI's
# rate_limit_event statuses encode (exact utilization only surfaces past
# the ~75% warning threshold, observed live 2026-08-10 on 2.1.226).
RATE_WARNING_PCT = 75
RATE_REJECTED_PCT = 100
RATE_LIMIT_STATUSES = ("allowed", "allowed_warning", "rejected")
USAGE_PANEL_DEADLINE_S = 45.0   # hard ceiling on the whole tmux panel probe
USAGE_PANEL_POLL_S = 1.0        # capture-pane poll interval
TRUST_PROMPT_MARKER = "trust this folder"        # workspace-trust prompt
# (observed live 2026-08-11, CLI 2.1.226: "Quick safety check: Is this a
# project you created or one you trust? ... 1. Yes, I trust this folder";
# Enter confirms the highlighted trust option)
PANEL_READY_MARKER = "? for shortcuts"           # interactive input ready

# profile-email.txt identity marker (v32 TD.3 / PR-MED-005).
PROFILE_EMAIL_MARKER = "profile-email.txt"
MARKER_MAX_BYTES = 320
MARKER_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?"
    r"\.[A-Za-z]{2,}$")
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


def strip_token_env(env: dict, seated_store_only: bool = False) -> dict:
    """Least-credential probe environment (v32 TD.2 / PR-HIGH-009).

    Removes every numbered token-pool variable (CLAUDE_CODE_OAUTH_TOKEN_N)
    and the wrapper's selector variable (LOOP_OAUTH_TOKEN_ENV) from a probe
    subprocess environment -- those are spawn-transport inputs, never probe
    inputs; removal is by NAME and no value is ever read, compared, or
    echoed. The ambient canonical CLAUDE_CODE_OAUTH_TOKEN stays by default
    (it is the CLI's documented env-auth surface, and per-dir credentials
    outrank it in 2.1.x); seated_store_only=True additionally removes it --
    the interactive /usage panel probe is the one seated-store-only surface
    (a token in the env suppresses the panel's quota bars; verified live
    2026-08-10 on CLI 2.1.226).
    """
    out = {k: v for k, v in env.items()
           if not NUMBERED_TOKEN_RE.match(k) and k != TOKEN_SELECTOR_VAR}
    if seated_store_only:
        out.pop(CANONICAL_TOKEN_VAR, None)
    return out


def probe_env() -> dict:
    """Least-credential environment for a probe subprocess that does NOT
    take a claude config dir (v32 TD.2 / PR-HIGH-021): `claude --help`,
    `codex debug models`, the codex app-server usage exchange. These went
    through `run_cli(..., env=None)` and so inherited the numbered pool
    variables + the selector wholesale from probe-models.py's own
    environment (a cloud run carries them). Strip them by name here; the
    ambient canonical token stays (harmless to a help parse and ignored by
    codex, matching claude_env's default). claude_env() owns the
    config-dir-bearing claude probes."""
    return strip_token_env(dict(os.environ))


def claude_env(candidate: str, is_wsl: bool, config_dir: str | None = None,
               seated_store_only: bool = False) -> dict:
    """Probe environment for a claude candidate.

    When a config dir is passed, set CLAUDE_CONFIG_DIR -- and for a /mnt/
    (Windows-shim-under-WSL) candidate, auto-merge CLAUDE_CONFIG_DIR/up into
    WSLENV so the variable crosses the interop boundary (existing WSLENV
    entries are preserved). Every claude probe env is token-stripped per
    strip_token_env (v32 TD.2 -- the former wholesale os.environ clone
    leaked unselected pool credentials into probe children);
    seated_store_only rides through for the panel probe.
    """
    env = strip_token_env(dict(os.environ), seated_store_only=seated_store_only)
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
    """The claude usage placeholder (structured fields present, null; the
    v32 additive evidence fields present at their fail-closed values)."""
    return {"status": "skipped", "headline": None, "session_pct": None,
            "session_resets": None, "week_pct": None, "week_resets": None,
            "usage_quality": "none", "usage_source": "none",
            "availability_band": "unknown", "limit_status": None,
            "limit_utilization": None, "limit_resets_at": None,
            "limit_resets": None}


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


def read_profile_email_marker(profile_dir: str):
    """profile-email.txt identity-marker SAFE READ (v32 TD.3; PR-MED-005).

    Returns the validated one-line email label, or None. Fail-silent by
    contract: EVERY failure -- missing, unreadable, oversized, malformed
    UTF-8, multi-line or control characters, symlinked, special-file
    (FIFO/device/dir), grammar mismatch, or a replacement race -- degrades
    to None, and raw marker content NEVER reaches JSON, stdout, or stderr
    (this function never raises and never echoes what it read).

    Mechanics (DIRFD-ANCHORED, v32 PR-MED-022): the profile dir is opened
    O_RDONLY|O_DIRECTORY|O_NOFOLLOW, then the marker is opened with
    `openat(dirfd, "profile-email.txt", O_NOFOLLOW|O_NONBLOCK)` (os.open
    dir_fd=). Anchoring on the dir fd kills the parent-symlink class the
    final-component O_NOFOLLOW missed (a symlinked profile dir now fails
    at the O_NOFOLLOW dir open, degrading fail-silent -- fail-closed is
    the safe outcome for a v32 identity label) AND the check/open race
    (openat resolves the leaf relative to the already-opened dir, not a
    re-walked path). O_NOFOLLOW on the leaf still rejects a symlinked
    marker; the fstat runs on the OPENED marker descriptor, so a
    path-swap cannot substitute a special file; O_NONBLOCK keeps a FIFO
    open from blocking. Hosts without openat (`dir_fd` unsupported) fall
    back to the single-open form with an lstat symlink pre-check --
    best-effort there, and the leaf O_NOFOLLOW + fstat type check still
    hold. The read is bounded to MARKER_MAX_BYTES+1 bytes; the content
    must strict-decode as UTF-8, be exactly one line (one optional
    trailing newline), carry no control characters, and match the pinned
    email grammar MARKER_EMAIL_RE.
    """
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    nonblock = getattr(os, "O_NONBLOCK", 0)
    o_directory = getattr(os, "O_DIRECTORY", 0)
    use_dirfd = (os.open in getattr(os, "supports_dir_fd", set())
                 and o_directory and nofollow)
    fd = None
    dfd = None
    try:
        if use_dirfd:
            # anchor on the profile dir itself (O_NOFOLLOW rejects a
            # symlinked profile dir), then openat the leaf relative to it
            dfd = os.open(profile_dir, os.O_RDONLY | o_directory | nofollow)
            fd = os.open(PROFILE_EMAIL_MARKER,
                         os.O_RDONLY | nofollow | nonblock, dir_fd=dfd)
        else:
            path = os.path.join(profile_dir, PROFILE_EMAIL_MARKER)
            if not nofollow:
                if stat.S_ISLNK(os.lstat(path).st_mode):
                    return None
            fd = os.open(path, os.O_RDONLY | nofollow | nonblock)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None
        raw = os.read(fd, MARKER_MAX_BYTES + 1)
    except (OSError, ValueError):
        return None
    finally:
        for _fd in (fd, dfd):
            if _fd is not None:
                try:
                    os.close(_fd)
                except OSError:
                    pass
    if len(raw) > MARKER_MAX_BYTES:
        return None  # oversized: never partially honored
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None
    if text.endswith("\r\n"):
        text = text[:-2]
    elif text.endswith("\n"):
        text = text[:-1]
    if any(ord(ch) < 0x20 or ord(ch) == 0x7f for ch in text):
        return None  # a second line or any control character invalidates
    label = text.strip()
    if not label or label != text:
        return None  # surrounding whitespace is not the pinned grammar
    if not MARKER_EMAIL_RE.match(label):
        return None
    return label


def panel_has_trust_prompt(text: str) -> bool:
    """Workspace-trust prompt detection on a captured pane (marker-based;
    the prompt asks whether to trust the files in the folder)."""
    return TRUST_PROMPT_MARKER in text.lower()


def panel_input_ready(text: str) -> bool:
    """Interactive-input readiness on a captured pane: the CLI's shortcut
    hint line is the stable marker across observed 2.1.x builds."""
    return PANEL_READY_MARKER in text


def _panel_heading(line: str):
    """Classify a panel line as a segment boundary. Returns 'session' /
    'week' (the two PARSED anchors), 'other' (a boundary that ends the
    current segment without opening a parsed one -- a model-specific
    weekly block, the contribution/skills sections), or None."""
    s = line.strip()
    if s.startswith("Current session"):
        return "session"
    if s.startswith("Current week (all models)"):
        return "week"
    if s.startswith("Current week ("):
        return "other"  # model-specific weekly: NEVER substituted
    if (s.startswith("What's contributing") or s.startswith("Skills")
            or s.startswith("Usage credits")):
        return "other"
    return None


def parse_usage_panel(text: str):
    """Parse a captured /usage panel -> the exact structured fields, or
    None when no recognizable usage block exists yet.

    The LIVE panel shape (captured 2026-08-11, CLI 2.1.226) is
    MULTI-LINE per metric: a colon-less heading line ("Current session" /
    "Current week (all models)"), a bar line carrying "N% used", and a
    "Resets <time>" line -- so parsing is segment-scoped across lines:
    a segment runs from its heading to the next heading-class line, and
    within it the FIRST "N% used" match is the percentage and the FIRST
    "resets"-word match (case-insensitive) is the resets text. A resets
    clause whose parenthetical is left unbalanced by a line wrap joins
    its continuation line(s) -- the parse-across-lines contract. The
    inline print-form shape ("Current session: 12% used - resets ...")
    parses through the same walk (heading and values share a line).
    Never-substituted noise, by construction: model-specific "Current
    week (<Model>):" blocks are 'other' boundaries; promo lines
    ("+50% weekly limits promo...") carry no "% used"; contribution
    lines ("92% of your usage...") carry no "used" after the percent;
    "Per-model breakdown unavailable (rate limited)" matches nothing
    and never blocks. Bar glyphs and the non-ASCII separator collapse
    to spaces before matching (never keyed on).
    """
    lines = [re.sub(r"[^\x20-\x7e]", " ", ln)
             for ln in (text or "").split("\n")]
    found: dict = {}
    i = 0
    n = len(lines)
    while i < n:
        kind = _panel_heading(lines[i])
        if kind not in ("session", "week"):
            i += 1
            continue
        seg = [lines[i]]
        j = i + 1
        while j < n and _panel_heading(lines[j]) is None:
            seg.append(lines[j])
            j += 1
        pct = None
        resets = None
        for k, raw in enumerate(seg):
            flat = re.sub(r"\s+", " ", raw).strip()
            if pct is None:
                m = re.search(r"(\d+)\s*%\s*used\b", flat)
                if m:
                    pct = int(m.group(1))
            if resets is None:
                m = re.search(r"(?i)\bresets\s+(.+?)\s*$", flat)
                m_end = re.search(r"(?i)\bresets\s*$", flat)
                if m or (m_end and k + 1 < len(seg)):
                    if m:
                        val = m.group(1)
                        kk = k
                    else:
                        # the wrap fell exactly after the word "resets":
                        # the value starts on the next segment line
                        kk = k + 1
                        val = re.sub(r"\s+", " ", seg[kk]).strip()
                    # line-wrap continuation: an unbalanced parenthetical
                    # joins the following line(s) of the same segment
                    while (val.count("(") > val.count(")")
                           and kk + 1 < len(seg)):
                        kk += 1
                        val = (val + " "
                               + re.sub(r"\s+", " ", seg[kk]).strip()).strip()
                    resets = re.sub(r"\s+", " ", val).strip() or None
        if pct is not None:
            if kind == "session" and "session_pct" not in found:
                found["session_pct"], found["session_resets"] = pct, resets
            elif kind == "week" and "week_pct" not in found:
                found["week_pct"], found["week_resets"] = pct, resets
        i = j
    return found or None


def tmux_binary():
    """First tmux on PATH, or None (absent -> the panel layer is skipped)."""
    hits = which_all("tmux")
    return hits[0] if hits else None


def probe_usage_panel(pinned: str, is_wsl: bool, config_dir: str | None,
                      cwd: str | None = None, tmux: str | None = None):
    """Layer-1 tmux interactive-panel usage probe (v32 TD.1). Returns a
    complete usage dict on a PARSED panel, else None (every failure falls
    through to the billed fallback -- this layer never errors the row).

    Seated-store only: the pane env strips the canonical token alongside
    the pool/selector variables (claude_env seated_store_only=True). The
    throwaway tmux server runs on a UNIQUE private socket label with a
    unique session name, so it never touches a user's tmux server and a
    prior run's stale session can never be captured; the finally block
    kills the private server on every path (success, timeout, parse
    failure), which is also the stale-session cleanup. All tmux output is
    captured -- nothing reaches this script's stdout (JSON-only contract).
    The tmux SERVER creates its socket under the system tmux directory
    OUTSIDE the repo; the script itself creates no files (the documented
    no-file-creation note).
    """
    if tmux is None:
        tmux = tmux_binary()
    if tmux is None:
        return None
    env = claude_env(pinned, is_wsl, config_dir, seated_store_only=True)
    label = "cbg-usage-%d-%d" % (os.getpid(), int(time.time() * 1000) % 1000000000)
    session = "usage-probe"
    target = session + ":"
    deadline = time.monotonic() + USAGE_PANEL_DEADLINE_S

    def tmux_call(args, timeout=5.0):
        return run_cli([tmux, "-L", label] + args, timeout, env=env)

    try:
        new_args = ["new-session", "-d", "-s", session, "-x", "200", "-y", "50"]
        if cwd:
            new_args += ["-c", cwd]
        new_args.append(pinned)
        status, _out, _err, _rc = tmux_call(new_args, timeout=10.0)
        if status != "ok":
            return None
        trust_answered = False
        usage_sent = False
        week_retried = False
        retry_grace = 0
        cap_fails = 0
        while time.monotonic() < deadline:
            time.sleep(USAGE_PANEL_POLL_S)
            # -S - captures the WHOLE scrollback, not just the visible pane:
            # the panel's skills/contribution rows grow per account, and a
            # panel taller than the pane scrolls the session block off-screen
            status, pane, _err, _rc = tmux_call(
                ["capture-pane", "-p", "-S", "-", "-t", target])
            if status != "ok":
                # a dead session fails every capture -- fall through early
                # instead of spinning out the whole deadline (r19)
                cap_fails += 1
                if cap_fails >= 5:
                    return None
                continue
            cap_fails = 0
            if not usage_sent:
                if panel_has_trust_prompt(pane) and not trust_answered:
                    tmux_call(["send-keys", "-t", target, "Enter"])
                    trust_answered = True
                    continue
                if panel_input_ready(pane):
                    tmux_call(["send-keys", "-t", target, "/usage"])
                    tmux_call(["send-keys", "-t", target, "Enter"])
                    usage_sent = True
                continue
            parsed = parse_usage_panel(pane)
            if parsed is None:
                continue
            if parsed.get("week_pct") is None and not week_retried:
                # a panel missing the week line gets ONE "r" retry, then a
                # short settle window before the partial result is accepted
                tmux_call(["send-keys", "-t", target, "r"])
                week_retried = True
                retry_grace = 5
                continue
            if parsed.get("week_pct") is None and retry_grace > 0:
                retry_grace -= 1
                continue
            result = usage_skipped()
            result.update(status="ok", usage_quality="exact",
                          usage_source="panel")
            for key in ("session_pct", "session_resets",
                        "week_pct", "week_resets"):
                if parsed.get(key) is not None:
                    result[key] = parsed[key]
            bits = []
            if result["session_pct"] is not None:
                bits.append(SESSION_LINE_PREFIX + " " + str(result["session_pct"])
                            + "% used" + (" - resets " + result["session_resets"]
                                          if result["session_resets"] else ""))
            if result["week_pct"] is not None:
                bits.append(WEEK_ALL_LINE_PREFIX + " " + str(result["week_pct"])
                            + "% used" + (" - resets " + result["week_resets"]
                                          if result["week_resets"] else ""))
            result["headline"] = " | ".join(bits) or None
            result["availability_band"] = usage_band(result)
            return result
        return None
    finally:
        try:
            run_cli([tmux, "-L", label, "kill-server"], 5.0, env=env)
        except Exception:
            pass


def parse_rate_limit_stream(out: str):
    """Scan a stream-json transcript for rate-limit + result evidence.

    Returns (rate_limit_info | None, result_text | None): the LAST
    top-level rate_limit_event's rate_limit_info dict (latest state wins)
    and the final result event's text. Banner lines and unknown event
    shapes are tolerated and ignored (iter_json_objects semantics).
    """
    info = None
    result_text = None
    for obj in iter_json_objects(out or ""):
        if not isinstance(obj, dict):
            continue
        if obj.get("type") == "rate_limit_event":
            candidate = obj.get("rate_limit_info")
            if isinstance(candidate, dict):
                info = candidate
        elif obj.get("type") == "result":
            text = obj.get("result")
            if isinstance(text, str):
                result_text = text
    return info, result_text


def usage_band(entry: dict) -> str:
    """Availability band for ONE usage entry (PR-MED-010, dimension 1).

    allowed | warning | rejected | unknown. Exact percentages map into
    the SAME bands as threshold events (worst of session/week: >=
    RATE_REJECTED_PCT -> rejected, >= RATE_WARNING_PCT -> warning, else
    allowed); threshold evidence maps by rate-limit status. No usable
    evidence -> unknown -- the explicit no-recommendation input, never a
    silent guess.
    """
    quality = entry.get("usage_quality")
    if quality == "exact":
        pcts = [p for p in (entry.get("session_pct"), entry.get("week_pct"))
                if isinstance(p, int)]
        if not pcts:
            return "unknown"
        worst = max(pcts)
        if worst >= RATE_REJECTED_PCT:
            return "rejected"
        if worst >= RATE_WARNING_PCT:
            return "warning"
        return "allowed"
    if quality == "threshold":
        status = entry.get("limit_status")
        if status == "allowed":
            return "allowed"
        if status == "allowed_warning":
            return "warning"
        if status == "rejected":
            return "rejected"
    return "unknown"


def rank_pool_candidates(rows: list) -> dict:
    """TWO-DIMENSIONAL availability-first pool ranking (v32 TD.1;
    PR-MED-010) -- the mechanical form of the wizard's menu-ranking rule.

    Input rows: {"label": <'default' or profile dir>, "usage": <usage
    dict>, "recent_repos": <snapshot dict>, "stale": <optional bool --
    evidence NOT refreshed this run>}. Output: {"recommended": <label |
    None>, "reason": <one line>, "bands": {label: band}}.

    Dimension 1 -- availability bands DECIDE: rejected/exhausted pools
    are NEVER recommended regardless of evidence quality; allowed beats
    warning; a band-unknown (degraded/incomparable) row never ranks.
    Dimension 2 -- within a band, only RECOMMENDABLE rows are eligible
    (v32 PR-MED-024): a row is recommendable iff its recent-repos
    snapshot is complete (status == "ok" -- the canonical completeness
    rule) AND its usage evidence is complete for its class (an exact row
    needs BOTH session_pct and week_pct -- a PARTIAL exact snapshot is
    never a pick, just as an incomplete recent-repos snapshot is not; a
    threshold row is complete by construction). Among recommendable rows
    the tie rules apply in order: idle-first (no in-use foreign entry),
    then most-headroom (lower is better -- exact rows by their worst
    percentage, threshold rows by limit_utilization where present, on
    one 0-100 scale within the band; a threshold row with no exposed
    utilization falls to the fidelity tie-break), then evidence fidelity
    + freshness (a FRESH observation beats a STALE one regardless of
    fidelity; at equal freshness exact > threshold), then the label as a
    FINAL deterministic tie-break (identical rows resolve the same
    regardless of input order). If a band has members but NONE are
    recommendable, the result is an explicit no-recommendation naming the
    band -- never a partial-snapshot pick.
    """
    bands = {}
    scored = []
    for row in rows:
        usage = row.get("usage") or {}
        band = usage.get("availability_band")
        if band not in ("allowed", "warning", "rejected"):
            band = usage_band(usage)
        bands[row.get("label")] = band
        scored.append((row, band))

    def is_recommendable(row):
        usage = row.get("usage") or {}
        repos = row.get("recent_repos") or {}
        if repos.get("status") != "ok":
            return False  # incomplete recent-repos snapshot
        quality = usage.get("usage_quality")
        if quality == "exact":
            # a PARTIAL exact snapshot (either half missing) is incomplete
            # usage evidence -- never a pick (PR-MED-024)
            return (isinstance(usage.get("session_pct"), int)
                    and isinstance(usage.get("week_pct"), int))
        if quality == "threshold":
            return usage.get("limit_status") in RATE_LIMIT_STATUSES
        return False  # unknown/degraded usage evidence is not recommendable

    for band_want in ("allowed", "warning"):
        members = [(row, band) for row, band in scored if band == band_want]
        if not members:
            continue
        eligible = [(row, band) for row, band in members if is_recommendable(row)]
        if not eligible:
            return {"recommended": None,
                    "reason": ("band=" + band_want + " reached but no row has a "
                               "complete recent-repos snapshot AND complete usage "
                               "evidence -- a partial snapshot is never recommended"),
                    "bands": bands}

        def sort_key(item):
            row, _band = item
            usage = row.get("usage") or {}
            repos = row.get("recent_repos") or {}
            busy = any(e.get("in_use") for e in (repos.get("entries") or []))
            idle_rank = 0 if not busy else 1
            # unified headroom (lower = more headroom) on one 0-100 scale;
            # STALE evidence never enters it (its numbers are not current
            # truth -- it falls to the freshness tie-break instead)
            headroom = 999
            if not row.get("stale"):
                if usage.get("usage_quality") == "exact":
                    pcts = [p for p in (usage.get("session_pct"),
                                        usage.get("week_pct"))
                            if isinstance(p, int)]
                    if pcts:
                        headroom = max(pcts)
                elif usage.get("usage_quality") == "threshold":
                    util = usage.get("limit_utilization")
                    if isinstance(util, int):
                        headroom = util  # order threshold rows by utilization
            fresh_rank = 1 if row.get("stale") else 0
            fidelity_rank = 0 if usage.get("usage_quality") == "exact" else 1
            # label is the FINAL deterministic tie-break (input-order-free)
            return (idle_rank, headroom, fresh_rank, fidelity_rank,
                    str(row.get("label")))

        eligible.sort(key=sort_key)
        best_row, _ = eligible[0]
        best_usage = best_row.get("usage") or {}
        repos = best_row.get("recent_repos") or {}
        idle = not any(e.get("in_use") for e in (repos.get("entries") or []))
        reason_bits = ["band=" + band_want]
        reason_bits.append("idle" if idle else "least-busy tie rules")
        if best_usage.get("usage_quality") == "exact":
            reason_bits.append("exact evidence")
        elif best_usage.get("usage_quality") == "threshold":
            # threshold evidence is percentage-free on EVERY surface (v32
            # PR-MED-026): limit_utilization is a machine-only ranking input,
            # never rendered as an NN% figure -- report the qualitative band
            # only (the reason already carries `band=<band>`)
            reason_bits.append("threshold evidence")
        return {"recommended": best_row.get("label"),
                "reason": "; ".join(reason_bits), "bands": bands}
    if any(band == "rejected" for _row, band in scored):
        return {"recommended": None,
                "reason": ("no pool outside the rejected band -- "
                           "rejected/exhausted pools are never recommended"),
                "bands": bands}
    return {"recommended": None,
            "reason": ("no comparable usage evidence -- degraded/unknown "
                       "observations never produce a silent guess"),
            "bands": bands}


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
    status, out, err, _rc = run_cli([pinned, "--help"], timeout, probe_env())
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
    """LAYERED per-account usage probe (v32 TD.1; the full evidence
    contract lives in the module docstring's claude-usage mapping block).

    Layer 1 -- tmux interactive-panel probe: preferred, unbilled, exact;
    seated-store only; tmux absent, deadline, or an unparseable panel
    falls through silently (print-mode /usage on CLI 2.1.226+ never
    returns quota lines, so the panel is the only unbilled exact source).
    Layer 2 -- ONE billed '<pinned> -p "/usage" --output-format
    stream-json --verbose' call: an older CLI's result text still carries
    the exact % lines (usage_source "print" -- the old/new skew path);
    on 2.1.226+ the stream's rate_limit_event yields THRESHOLD evidence
    (allowed / allowed_warning / rejected). A timeout/failed first
    attempt is retried ONCE before degrading (v30.1: a cold store's
    first call can pay an OAuth token refresh that overruns the budget;
    'absent' never retries).
    Layer 3 -- degraded: the existing status/headline behaviour, with
    usage_quality/usage_source "none".

    Threshold evidence NEVER lands in session_pct/week_pct and its
    headline is percentage-free; availability_band is computed on every
    outcome (PR-MED-002/PR-MED-010).
    """
    panel = probe_usage_panel(pinned, is_wsl, config_dir, cwd=cwd)
    if panel is not None:
        return panel
    env = claude_env(pinned, is_wsl, config_dir)
    cmd = [pinned, "-p", "/usage", "--output-format", "stream-json", "--verbose"]
    status, out, err, _rc = run_cli(cmd, max(timeout, 30.0), env, cwd=cwd)
    if status in ("timeout", "failed"):
        status, out, err, _rc = run_cli(cmd, max(timeout, 30.0), env, cwd=cwd)
    result = usage_skipped()
    if status == "timeout":
        result.update(status="timeout", headline=None)
        return result
    if status in ("failed", "absent"):
        result.update(status="failed",
                      headline=(err or out or "").strip()[:200] or None)
        return result
    info, result_text = parse_rate_limit_stream(out)
    # exact print evidence first (an older CLI whose /usage still prints
    # quota lines into the result text -- higher fidelity than threshold)
    lines = [ln.strip() for ln in (result_text or "").split("\n")]
    pct_lines = [ln for ln in lines if "%" in ln]
    if pct_lines:
        result.update(status="ok", headline=" | ".join(pct_lines[:4]),
                      usage_quality="exact", usage_source="print")
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
        result["availability_band"] = usage_band(result)
        return result
    if info is not None and info.get("status") in RATE_LIMIT_STATUSES:
        limit_status = info.get("status")
        util = info.get("utilization")
        resets_at = info.get("resetsAt")
        resets_iso = None
        if isinstance(resets_at, (int, float)) and resets_at > 0:
            try:
                resets_iso = (datetime.fromtimestamp(resets_at).astimezone()
                              .isoformat(timespec="seconds"))
            except (OverflowError, OSError, ValueError):
                resets_iso = None
        headline = "rate-limit status: " + limit_status
        if resets_iso:
            headline += " - resets " + resets_iso
        result.update(status="ok", usage_quality="threshold",
                      usage_source="rate-limit-event",
                      limit_status=limit_status,
                      limit_utilization=util if isinstance(util, int) else None,
                      limit_resets_at=(resets_at
                                       if isinstance(resets_at, (int, float))
                                       else None),
                      limit_resets=resets_iso, headline=headline)
        result["availability_band"] = usage_band(result)
        return result
    # no panel, no % lines, no event: the logged-out local-stats block and
    # every other unrecognized-but-clean exit land here
    result.update(status="degraded",
                  headline=(result_text or out or "").strip()[:200] or None)
    return result


def probe_codex(timeout: float) -> dict:
    status, out, err, rc = run_cli(["codex", "debug", "models"], timeout,
                                   probe_env())
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
            cwd=neutral_probe_cwd(), env=probe_env())  # v32 PR-HIGH-021
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
    ident["marker_email"] = read_profile_email_marker(default_dir)
    ident["recent_repos"] = default_projects
    out["default_account"] = ident
    for p in prof_entries:
        prof = {"dir": p["dir"]}
        prof.update(probe_identity(pinned, is_wsl, args.timeout, p["dir"]))
        prof["usage"] = (probe_usage(pinned, is_wsl, args.timeout, p["dir"],
                                     cwd=probe_cwd)
                         if args.usage else usage_skipped())
        prof["marker_email"] = read_profile_email_marker(p["dir"])
        prof["recent_repos"] = snapshots[p["real"]]
        out["profiles"].append(prof)
    if args.usage:
        # additive advisory (v32 TD.1): the availability-first ranking over
        # every probed pool -- the wizard's menu prose applies the same rule
        rows = [{"label": "default", "usage": ident["usage"],
                 "recent_repos": default_projects}]
        rows += [{"label": prof["dir"], "usage": prof["usage"],
                  "recent_repos": prof["recent_repos"]}
                 for prof in out["profiles"]]
        out["pool_ranking"] = rank_pool_candidates(rows)
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

    Returns (leads_active, loop_config_or_None, paused_or_None). Fenced lines
    never count for headings or bullets, so quoted examples cannot
    false-positive. paused is None unless the lifecycle section leads with
    'Paused' (v32); then it is {"since": ..., "reason": ...} from the section's
    'Paused since:' / 'Paused reason:' bullets ("" when a field is absent —
    surfaced, never guessed).
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    section = None
    in_fence = False
    first_lifecycle_line = None
    paused_since = None
    paused_reason = None
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
        if section == "Lifecycle State" and line.strip():
            if first_lifecycle_line is None:
                first_lifecycle_line = line.strip()
            bullet = re.sub(r"^[-*]\s+", "", line.strip())
            if bullet.startswith("Paused since:") and paused_since is None:
                paused_since = bullet[len("Paused since:"):].strip()
            if bullet.startswith("Paused reason:") and paused_reason is None:
                paused_reason = bullet[len("Paused reason:"):].strip()
        if (section == "Current State / Handoff Note" and loop_config is None
                and line.strip().startswith(LOOP_CONFIG_PREFIX.strip() + " ")):
            candidate = line.strip()[len(LOOP_CONFIG_PREFIX):].strip()
            if loop_config_parses(candidate):
                loop_config = candidate
    lead = (re.sub(r"^[-*]\s+", "", first_lifecycle_line)
            if first_lifecycle_line else "")
    leads_active = lead.startswith("Active")
    paused = None
    if lead.startswith("Paused"):
        paused = {"since": paused_since or "", "reason": paused_reason or ""}
    return leads_active, loop_config, paused


def probe_plans(plans_dir: str) -> dict:
    out: dict = {"status": "ok", "plans_dir": plans_dir, "scanned": 0,
                 "active_candidates": [], "non_active_with_config": 0,
                 "paused_plans": [],
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
            leads_active, config, paused = scan_plan_file(f)
        except OSError:
            live_errors += 1
            continue
        # v32 (TE.4): Paused plans are surfaced regardless of a Loop config —
        # discoverable + recoverable, never an Active candidate. Additive
        # field inside probe_schema 1; a paused plan WITH a config also still
        # counts in non_active_with_config (paused IS non-active — the
        # pre-v32 count's semantics are unchanged).
        if paused is not None:
            out["paused_plans"].append({"file": f.name,
                                        "since": paused["since"],
                                        "reason": paused["reason"],
                                        "has_loop_config": config is not None})
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
                _active, config, _paused = scan_plan_file(f)
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
