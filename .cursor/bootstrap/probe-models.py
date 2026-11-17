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
  "capabilities": ["profile-dir-filter", "week-model", "org-id", "print-only",
                   "codex-homes", "no-session-persistence"],
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
              "week_resets_at": 1784095200},
    "accounts": [
      {"home": "/home/user/.codex", "is_default": true, "status": "ok",
       "error": null, "email": "user@example.com", "plan": "pro",
       "account_id": "5b2e0c1d-0000-4a8e-9f10-c0ffee000003",
       "session_pct": 12, "session_resets_at": 1783622400,
       "week_pct": 42, "week_resets_at": 1784095200,
       "reset_credits": {"available_count": 1, "items": [
           {"id": "credit-1", "status": "available",
            "granted_at": 1783000000, "expires_at": null, "title": null}]},
       "daily_tokens": [{"date": "2026-07-09", "tokens": 120345}],
       "additional_limits": null}
    ]
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
             "efforts": ["low", "medium", "high", "xhigh", "max"],
             "no_session_persistence": true},
    "version": {"value": "2.1.201 (Claude Code)", "status": "ok", "error": null},
    "advisor": {"value": null, "status": "skipped", "error": null, "version": null},
    "profile_dir_filter": null,
    "default_account": {"identity": "user@example.com (Example Org)", "status": "ok",
                        "plan": "max",
                        "org_id": "3f9c1a2e-0000-4d51-9b77-c0ffee000001",
                        "auth_state": "logged-in",
                        "usage": {"status": "skipped", "headline": null,
                                  "session_pct": null, "session_resets": null,
                                  "week_pct": null, "week_resets": null,
                                  "usage_quality": "none", "usage_source": "none",
                                  "availability_band": "unknown",
                                  "limit_status": null, "limit_utilization": null,
                                  "limit_resets_at": null, "limit_resets": null,
                                  "week_model_pct": null, "week_model_name": null,
                                  "week_model_resets": null},
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
       "org_id": "3f9c1a2e-0000-4d51-9b77-c0ffee000002",
       "auth_state": "logged-in",
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
                 "limit_resets_at": null, "limit_resets": null,
                 "week_model_pct": 88, "week_model_name": "Fable",
                 "week_model_resets": "Jul 27, 1pm (Area/City)"},
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
    in-context | skipped | partial |
    logged-out (v33.6; codex.accounts[].status only)

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
  directions). Print-mode /usage returns exact quota lines on CLI 2.1.278
  (verified live 2026-09-20) and returned none at 2.1.226 on Cursor Cloud
  VMs -- the probe tries the one-call print path first and falls back to
  the tmux panel only where print-mode is dark (v33.3 order):
    1. ONE billed call, FIRST: '<pinned> -p "/usage" --output-format
       stream-json --verbose' (retry-once on timeout/failed per v30.1;
       absent never retries; v33.6: every attempt appends
       --no-session-persistence when the pinned CLI's --help advertises
       it, so no session log is written -- verified live 2026-09-26 on
       CLI 2.1.282: the flagged call parses exact, with the same field
       set as the unflagged one). A result text carrying an ANCHORED quota
       field (the exact-prefix anchors below; a partial parse stays
       exact) is EXACT print evidence (usage_source "print") and returns
       at once -- the panel never launches. A bare "%" line
       (contribution stats, promo lines) is NEVER exact. Where
       print-mode is dark the stream's rate_limit_event yields THRESHOLD
       evidence: rate_limit_info.status allowed | allowed_warning |
       rejected (+ utilization/resetsAt when exposed). Exact utilization
       only appears past the ~75% warning threshold -- below it "allowed"
       means healthy headroom, never a percentage. A DEGRADED
       classification on a store the identity probe observed as
       auth_state "logged-in" runs the same call ONCE more and
       re-classifies (v33.5; max 2 attempts on that branch) -- a
       logged-out / indeterminate / unknown auth_state never pays it,
       since a logged-out store has no quota lines to recover.
       v33.7 (CLI 2.1.286, read live and from its bundle 2026-10-02):
       the quota lines come from the CLI's own GET /api/oauth/usage
       (5 s timeout; a 60 s snapshot and a 1 h seed kept in the store's
       .claude.json). When that read fails with no seed left the CLI
       OMITS the quota lines and prints only its subscription banner
       ("You are currently using your subscription/overages ...") plus
       the "What's contributing to your limits usage?" report -- this
       FAILED-READ shape degrades with the fixed percentage-free
       headline USAGE_READ_FAILED_HEADLINE, never the report's
       unrelated percentages. The exact headline carries quota-shaped
       lines only. The same call's assistant event (observed on
       2.1.286) carries a structured twin, usage_report.rate_limits.limits[] ({kind:
       session | weekly_all | weekly_scoped, percent, resets_at ISO,
       scope.model.display_name}): when the text has NO anchored line
       the twin is exact print evidence too (percent floored like the
       print line; resets as the local ISO minute string; the first
       named weekly_scoped fills week_model_*, never week_*); text
       lines always outrank it, and on the failed-read shape it is
       null as well.
       -> usage_quality "exact"/"threshold", usage_source
       "print"/"rate-limit-event".
    2. tmux interactive-panel probe, ONLY when call 1 produced no exact
       evidence (threshold, degraded, timeout, failed) AND --print-only
       was not passed (v33.5: that flag pins the probe to layer 1 --
       every non-exact layer-1 outcome is returned exactly as
       computed): UNBILLED; exact
       at every usage level; a PARSED panel outranks the call-1 outcome,
       and every panel failure returns that outcome exactly as computed.
       Runs the pinned CLI interactively inside a throwaway
       private-socket tmux session (per-call unique -L label + session
       name; killed in finally on every path; bounded by a hard
       deadline), sends "/usage", captures the pane, and parses the
       panel: line-wrapped bars are parsed ACROSS lines; "Per-model
       breakdown unavailable (rate limited)" can coexist with valid bars
       and never blocks; a panel missing the week line gets ONE "r"
       retry; a workspace-trust prompt is answered once, by EXPLICIT
       selection of the trust option (the highlighted option is read
       from the pane; an unrecognized highlight is re-captured and never
       confirmed); the 2.1.278 "Chrome extension detected" interstitial
       is declined with Enter only while its decline option is
       highlighted; input readiness = any PANEL_READY_MARKERS entry (the
       legacy "? for shortcuts" line, or the 2.1.278 permission-mode
       status line); a pane showing the CLI's failed-read text ("Failed
       to load usage data") with no parsable bars ends the panel at once
       (v33.7: the panel reads the same endpoint, so nothing would parse
       before the deadline). SEATED-STORE ONLY: the canonical
       CLAUDE_CODE_OAUTH_TOKEN is stripped from the panel subprocess env
       (a token in the env suppresses the quota bars -- verified live
       2026-08-10). tmux absent/timeout/unparseable -> the call-1
       outcome stands.
       No-file-creation note: the tmux SERVER creates its own socket
       under the system tmux dir OUTSIDE the repo (plus the CLI's own
       store writes, as any probe invocation); the script itself still
       creates nothing.
       Neutral-cwd trust note: every usage subprocess runs from the
       neutral probe cwd -- the first usable temp dir (TMPDIR / TEMP /
       TMP, then /tmp, /var/tmp, /usr/tmp), normally a SHARED,
       world-writable directory. Answering the trust prompt tells the
       CLI to trust THAT directory, and the CLI may record the answer in
       the probed store (its own store write; persistence is CLI
       behaviour, not verified here); print-mode never asks, and either
       mode may read project-level CLI config found in that directory.
       On a multi-user host whose other local users are not trusted,
       point TMPDIR at an EXISTING private directory before running
       --usage: the resolver honours it first (a missing one falls
       through to /tmp), so the probes and the trust answer move there
       (the old temp dir's projects/ entry is then no longer
       excluded from recent_repos).
       -> usage_quality "exact", usage_source "panel".
    3. Degraded: no anchored quota line, no event, no panel -> the
       existing degraded/headline path (usage_quality "none",
       usage_source "none").
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
  week_pct stays null, never another percentage). The model-specific line
  is instead REPORTED separately (v33.5, additive): the FIRST "Current
  week (<name>):" line/block that is not the all-models one fills
  week_model_pct, week_model_name (the parenthesised name, stripped) and
  week_model_resets (verbatim, null when the line carries no resets
  clause) -- later model lines are
  ignored, the fields are null when no model line exists, and a model line
  ALONE is never exact evidence (it neither makes a print result exact nor
  turns a panel with no session/week block into a usage block). The
  separator between
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
  claude dirs and the Q1R re-check needs no codex leg -- and under a
  --codex-home list that does not include ~/.codex, v33.6). Popen-based BY
  DESIGN, never run_cli: the server exits on closed stdin, so stdin stays
  OPEN across the whole read-until-reply exchange (no scripted sleeps since
  v33.3); the deadline max(--timeout, 30) is the ceiling of that whole
  exchange, and the recorded child is terminated ->
  bounded-waited -> killed -> reaped on every success/failure/timeout path
  (recorded identity only, never broad process matching). The response is
  correlated on the rate-limit request id ONLY; initialize responses,
  notifications, and banner lines are tolerated and ignored. Windows are
  classified by windowDurationMins (300 = session, 10080 = week), NEVER by
  primary/secondary position (position drift observed live: primary held
  the weekly window with secondary null); an absent window leaves its
  fields null and the table renders "not exposed". resetsAt rides verbatim
  as *_resets_at (epoch seconds) plus a derived local-ISO *_resets string.
  plan <- rateLimits.planType when present. Account identity rides
  codex.accounts[] (v33.6); codex.usage carries no identity fields, and
  the accounts table's codex account cell still renders "not exposed".
  statuses: ok (>=1 window classified) | degraded (id:2 parsed but no
  rateLimits object / no recognizable window: shape drift) | failed (no
  id:2 response, rpc error object, or spawn/write failure) | timeout |
  absent (no codex executable) | skipped. Edge: a reply present in the
  wait-end transcript beats the timeout label; a reply arriving during
  the shutdown is not parsed; "timeout" means no id-correlated response
  was captured.

- codex.accounts (v33.6; ALWAYS emitted, possibly []) -- ONE codex account
  per eligible CODEX_HOME. is_eligible_codex_home() is the ONE named
  predicate shared by enumeration, --codex-home, and every consumer: a
  real directory at ~/.codex or ~/.codex-cut<digits> (so never a *.lock
  control dir or a quarantine-marked dir) holding an auth.json file, its
  parent realpathing to $HOME. Unlike the claude profile predicate, a
  SYMLINKED home is INELIGIBLE -- never realpath-resolved: the app-server
  writes state files into whatever home it is pointed at, so the
  predicate runs before every spawn and an ineligible dir is never
  spawned. A symlinked ~/.codex is therefore itself never listed, while
  every other eligible home still is (the list is [] only when none
  exists); is_default = realpath(home) == realpath($HOME/.codex), so a
  link targeting an eligible cut home makes THAT entry the default.
  Consumer fallback: codex.accounts == [] with codex.usage ok (a
  symlinked default and no other home) -> render the codex.usage row.
  Enumeration (sorted glob ~/.codex*, predicate-filtered, realpath-
  deduped) includes the default home. --codex-home replaces enumeration
  with the requested homes in argument order: eligible spellings dedup
  by realpath (first wins), ineligible ones by their normalized path,
  and each ineligible dir is an entry with status "failed", error
  "ineligible home" -- with or without --usage. Homes are probed only
  behind --usage and never under --profile-dir (entries "skipped",
  every value field null, otherwise). Each probed home runs ONE
  app-server exchange (the codex.usage transport) with CODEX_HOME SET to
  the home -- the script's own ambient CODEX_HOME is ignored here (the
  codex.usage exchange and the models catalog still inherit it) -- and
  OPENAI_API_KEY / CODEX_API_KEY / CODEX_ACCESS_TOKEN removed by NAME
  (the binary honours them ahead of the home's auth.json), sending
  initialize, account/read, account/rateLimits/read, and
  account/usage/read; homes run in parallel through the --workers pool
  and are assembled in input order.
  Entry keys (every key in every entry, null when unknown, in this
  order): home, is_default, status, error, email (account/read's
  account.email, chatgpt accounts only), plan (rateLimits.planType, else
  account.planType), account_id (the rate-limit reply's accountId, else
  workspaceRouting.chatgptAccountId), session_pct / session_resets_at and
  week_pct / week_resets_at (the codex.usage window rules; epoch seconds
  verbatim, no derived ISO string), reset_credits ({"available_count",
  "items": null | [{id, status, granted_at, expires_at, title}]} from
  rateLimitResetCredits; null when that object is absent), daily_tokens
  ([{date, tokens}] from dailyUsageBuckets; null passthrough),
  additional_limits (null, reserved). Null-vs-empty passes through
  untouched.
  statuses, REPLY-FIRST in this fixed order (only replies in the
  wait-end transcript count): (1) spawn / write failure -> failed
  ("executable not found: codex" when the binary is absent -- an entry
  has no "absent" status); (2) account/read answering a null account ->
  logged-out (value fields null, error null; the authentication errors
  the other reads then return are expected); (3) no rate-limit reply ->
  timeout under the deadline, else failed; (4) the rate-limit reply
  decides: rpc error -> failed, no rateLimits object / no recognizable
  window -> degraded; (5) ok needs account/read and account/usage/read
  as parsed results too, else degraded with the error naming the read
  and the cause (e.g. "account/usage/read: no reply (eof)"). Value
  fields carry whatever replies were captured. An internal error becomes
  that home's own failed "internal: ..." entry. Worst-case codex leg
  wall clock (no global deadline): ceil(homes / workers) x
  (max(--timeout, 30) + ~16 s -- the shutdown ladder on a stubborn
  server: 2 s grace + 5 s terminate + 5 s kill + two 2 s reader joins),
  plus one such exchange for codex.usage.

- Consume mode (v33.6; the script's ONLY write-capable mode, env-gated):
  --consume-codex-reset --codex-home DIR --credit-id ID --idempotency-key
  KEY consumes ONE codex rate-limit reset credit for DIR's account and
  prints a mode-specific document INSTEAD of the probe document -- no
  probe runs. Grammar: ID and KEY each match [A-Za-z0-9_-]{1,128}; every
  argument is required exactly once. Refusals are usage errors (exit 2,
  argparse's usage text + one error line on stderr, NO JSON, no
  process) in two layers: (i) argparse syntax errors first (an
  unrecognized or abbreviated flag -- abbreviations are never expanded
  --, a missing value, an invalid --timeout); then (ii) the semantic
  checks IN THIS ORDER -- PROBE_ALLOW_CONSUME not exactly "1" (checked
  FIRST, so a well-formed mis-invocation reveals only "not enabled"),
  --credit-id / --idempotency-key missing or repeated, a value outside
  the grammar, any of the four mode flags --usage / --profile-dir /
  --print-only / --probe-advisor present, --codex-home not given exactly
  once. --workers, --plans-dir, and --timeout are accepted and inert
  (only --timeout is read: the exchange ceiling max(--timeout, 30));
  --credit-id / --idempotency-key without the mode flag are refused.
  The consume runner RE-CHECKS the gate and the --timeout bound before
  any spawn, so no direct call bypasses them. Otherwise the document is
  {"probe_schema": 1, "consume": {"home": DIR, "status": "ok" | "failed"
  | "timeout", "outcome": "reset" | "nothingToReset" | "noCredit" |
  "alreadyRedeemed" | null, "error": <string> | null}} at exit 0: an
  ineligible DIR (the codex.accounts predicate) -> failed "ineligible
  home" WITHOUT a spawn; else ONE app-server exchange on the per-home env
  (CODEX_HOME = DIR, the API-key variables removed) sending initialize
  and the consume request -- nothing else -- classified REPLY-FIRST: no
  process (codex absent -> "executable not found: codex", another spawn
  error -> its text) -> failed; a correlated consume reply decides
  whatever the transport verdict (an outcome in the four-value set ->
  ok; an rpc error or any other value -> failed, never an invented
  outcome); no reply -> failed "request write failed: ..." / timeout /
  failed "stdout closed before the consume reply". An internal error
  after the gate -> failed "internal: ..." at exit 0. The child is reaped
  by the same shutdown ladder on every path. INDETERMINACY: a timeout or
  failed returned AFTER the request was written does NOT mean "not
  consumed" -- the consumer re-reads account/rateLimits/read (the
  rateLimitResetCredits list) before retrying with the SAME idempotency
  key; the probe itself never retries. Run it only from the consumer, on
  the user's explicit instruction -- never from a test, a review, an
  acceptance run, or this repo.

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
  advertises optional behaviours (currently "profile-dir-filter", plus the
  three INFORMATIONAL v33.5 tokens "week-model" (the additive week_model_*
  usage fields), "org-id" (the additive org_id / auth_state account fields)
  and "print-only" (the --print-only flag exists), and the v33.6
  "codex-homes" (codex.accounts and --codex-home exist) and
  "no-session-persistence" -- a SUPPORT token, listed only when
  claude.help.no_session_persistence is true: the pinned CLI's --help
  advertises --no-session-persistence, so every print-mode claude call
  this run makes (each stream-json /usage attempt and the advisor probe;
  never auth status, --version, or the tmux panel) carries it -- present
  even when the run made no print-mode call, absent under --codex-home
  (the help probe never runs). claude.help.no_session_persistence is the
  additive bool beside aliases / efforts, computed from ACQUIRED help
  text alone (the alias / effort metadata status never suppresses it);
  false when no help text was acquired or the leg was skipped);
  consumers MUST treat it as optional (older scripts omit it -- absence
  means fall back to the full
  run) and MUST detect the FLAG itself via --help, never by reading a
  capabilities token out of a probe document they did not run. When
  --profile-dir is passed,
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
                     the claude LAYERED probe per account (one billed
                     stream-json call carrying print or rate_limit_event
                     evidence -> the tmux panel, unbilled/exact, up to
                     ~45s, only when that call was not exact -> degraded;
                     the claude-usage mapping block above), the codex
                     app-server rateLimits exchange (returns on the
                     reply), and one three-read exchange per eligible
                     codex home (codex.accounts, v33.6). Accounts are
                     probed in parallel (--workers).
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
                     codex usage leg and the codex accounts pool (every
                     codex.accounts entry "skipped"). Ineligible values
                     land in claude.profile_dir_filter.invalid (exit
                     stays 0).
    --codex-home D   (v33.6) repeatable: limit the codex accounts leg to
                     the named CODEX_HOME dir(s) -- codex.accounts lists
                     exactly those, in argument order -- and SKIP the
                     claude leg (claude is the "skipped" skeleton: no
                     candidate probe, subprocess, or projects/ snapshot;
                     report line "claude SKIPPED (--codex-home)").
                     codex.usage is probed only when ~/.codex is among
                     them. An ineligible dir is a failed "ineligible
                     home" entry, never spawned (with or without
                     --usage). Not with --profile-dir (usage error, exit
                     2); with --print-only accepted and inert.
    --print-only     (v33.5) pin the claude usage probe to layer 1: the
                     tmux interactive panel never launches, so a
                     threshold / degraded / timeout / failed print
                     outcome is reported exactly as computed. ADDITIVE
                     and defaulted (off); consumers detect it via --help.
    --probe-advisor  run the BILLED advisor acceptance probe (one cheap
                     advisored invocation). Default off: status "skipped".
    --timeout N      per-subprocess timeout in seconds (default 15; the
                     advisor probe uses max(N, 180), usage max(N, 30) --
                     the ceiling of each whole codex app-server exchange,
                     which returns as soon as its replies arrive). N must
                     be finite and at most PROBE_TIMEOUT_MAX_S (86400 s,
                     one day): anything else is a usage error (exit 2).
    --plans-dir P    plans directory for the Q1 scan (default .cursor/plans).
    --workers N      parallel per-account probe workers, N >= 1 (default 8,
                     capped at the account count; 1 = serial). ADDITIVE and
                     defaulted: an older skill never passes it. The JSON
                     document is identical at every N -- accounts are
                     assembled in enumeration order, never completion
                     order; wall clock scales with ceil(accounts / N)
                     batches. The same pool size governs the codex homes
                     separately (the codex.accounts worst-case bound).
    --consume-codex-reset
                     (v33.6) the env-gated, WRITE-capable consume mode (the
                     "Consume mode" block above): refused -- exit 2, no
                     JSON, no process -- unless PROBE_ALLOW_CONSUME=1;
                     needs --codex-home, --credit-id, and
                     --idempotency-key exactly once each and none of the
                     four mode flags. Consumers detect it via --help.
    --credit-id ID   (v33.6) consume mode only: the reset credit id,
                     [A-Za-z0-9_-]{1,128}.
    --idempotency-key KEY
                     (v33.6) consume mode only: the caller's idempotency
                     key, [A-Za-z0-9_-]{1,128}; reuse the SAME key when
                     retrying one attempt.

Behaviour contract: ASCII-only source, stdlib-only, read-only except the
env-gated --consume-codex-reset mode (the ONLY write-capable mode: one
account/rateLimitResetCredit/consume request, refused as a usage error --
exit 2, no JSON, no process -- unless PROBE_ALLOW_CONSUME=1; every other
subprocess is a read-only probe; the script itself still creates nothing):
the only outputs are stdout/stderr; the optional advisor probe bills
tokens but writes nothing; the script itself never creates a file or
directory anywhere -- the usage panel probe's throwaway tmux SERVER creates
its own socket under the system tmux dir outside the repo, and CLI probe
invocations refresh their own stores, both disclosed subprocess effects,
not script writes. No literal triple-backtick sequences (fence tokens are
built programmatically), every subprocess carries a timeout and
stdin=DEVNULL so the script never hangs (single exception: the codex
app-server exchanges -- codex.usage, each codex.accounts home, and the
consume exchange -- hold stdin OPEN by protocol necessity -- Popen-
recorded, deadline-bounded, terminated/killed/reaped in finally), and the
JSON document (the probe document, or consume mode's own) is ALWAYS
emitted with exit code 0 -- per-probe failures land in statuses, never in
the exit code. Exit 2 only when no JSON could be produced: a usage error,
including every consume refusal.

Usage (from the project root; use plain 'python' if 'python3' is absent):
    python3 .cursor/bootstrap/probe-models.py
    python3 .cursor/bootstrap/probe-models.py --usage --timeout 20
    python3 .cursor/bootstrap/probe-models.py --usage --profile-dir default
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import platform
import re
import stat
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
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
# v33.5 model-specific weekly line/heading (the FIRST one observed wins;
# its values ride the additive week_model_* fields and are NEVER
# substituted into week_pct): the print shape carries the colon, the
# panel heading is colon-less
WEEK_MODEL_LINE_RE = re.compile(r"^Current week \((?!all models\))([^()]+)\):")
WEEK_MODEL_NAME_RE = re.compile(r"^Current week \(([^()]+)\)")
# v33.7 (CLI 2.1.286, read from its bundle 2026-10-02): print-mode /usage
# opens with one of these banners whenever the store is a logged-in
# subscription. The quota lines that follow come from the CLI's own
# GET /api/oauth/usage (5 s timeout; a fresh-60s / seed-1h snapshot in the
# store's .claude.json); when that read fails and no seed is left the CLI
# OMITS them and prints the banner + the contribution report only -- the
# "usage read failed" shape, which gets a fixed percentage-free headline.
SUBSCRIPTION_BANNER_PREFIXES = (
    "You are currently using your subscription",
    "You are currently using your overages")
USAGE_READ_FAILED_HEADLINE = ("usage limits not reported: the CLI's usage "
                              "read failed (subscription banner only)")
# the interactive panel's text for the same failed read (2.1.286 bundle):
# the panel can never parse once it shows this, so it stops waiting
PANEL_USAGE_FAILED_MARKER = "Failed to load usage data"

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
PROBE_WORKERS = 8               # per-account probe pool ceiling (--workers N)
PROBE_TIMEOUT_MAX_S = 86400.0   # --timeout ceiling (one day; v33.6 PR-MED-012)
USAGE_PANEL_DEADLINE_S = 45.0   # hard ceiling on the whole tmux panel probe
USAGE_PANEL_POLL_S = 1.0        # capture-pane poll interval
TRUST_PROMPT_MARKER = "trust this folder"        # workspace-trust prompt
# (observed live 2026-08-11, CLI 2.1.226: "Quick safety check: Is this a
# project you created or one you trust? ... 1. Yes, I trust this folder";
# Enter confirms the highlighted trust option; observed live 2026-09-20,
# CLI 2.1.278: "No, exit" is listed AND highlighted first, no option
# numbers -- so the answer is an explicit selection, never a bare Enter)
# group 1 = the highlight glyph (U+276F, or the legacy ">"), group 2 = the
# option text; the optional "N." option number is never keyed on
TRUST_OPTION_RE = re.compile(
    "^\\s*([\\u276f>])?\\s*(?:\\d+\\.\\s*)?(Yes, I trust|No, exit)\\b",
    re.IGNORECASE)
# Interactive-input readiness: ANY marker present = the idle input screen.
# "? for shortcuts" is the 2.1.226-era hint line (kept: older CLIs, and
# any host where it still shows). On the CLI 2.1.278 hand-run host (auto
# permission mode, 2026-09-20) it never appeared (waited 30 s twice) --
# the idle screen carried the permission-mode status line instead:
# "<U+23F5><U+23F5> auto mode on (shift+tab to cycle)". Both the glyph
# prefix and the ASCII "(shift+tab to cycle)" tail are accepted (the tail
# rides every non-default mode's status line). The input-prompt hint text
# ('Try "edit <filepath> ..."') varies per launch and is never keyed on.
PANEL_READY_MARKERS = ("? for shortcuts", chr(0x23F5) * 2 + " ",
                       "(shift+tab to cycle)")
# Second interstitial (observed live 2026-09-20, CLI 2.1.278, first launch
# only): "Claude in Chrome extension detected ... <glyph> No, keep browser
# tools off / Yes, use my browser / Enter to confirm - Esc to keep browser
# tools off". Declined by Enter ONLY while the decline option carries the
# highlight; never Down, never treated as the trust prompt.
CHROME_PROMPT_MARKERS = ("chrome extension detected", "keep browser tools off")
CHROME_OPTION_RE = re.compile(
    "^\\s*([\\u276f>])?\\s*(?:\\d+\\.\\s*)?"
    "(No, keep browser tools off|Yes, use my browser)\\b",
    re.IGNORECASE)

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
CODEX_USAGE_DEADLINE_FLOOR_S = 30.0  # exchange ceiling = max(--timeout, this)
CODEX_USAGE_INIT_WINDOW_S = 2.0      # CEILING on the id:1 (initialize) reply wait
CODEX_USAGE_EXIT_GRACE_S = 2.0       # clean-exit wait after stdin closes, pre-terminate
CODEX_USAGE_READER_JOIN_S = 2.0      # per-reader join bound; a live reader is abandoned
CODEX_SESSION_WINDOW_MINS = 300      # windowDurationMins value classifying "session"
CODEX_WEEK_WINDOW_MINS = 10080       # windowDurationMins value classifying "week"
# v33.6 per-home accounts exchange: initialize (id:1) + three reads, one id each
CODEX_HOME_NAME_RE = re.compile(r"\.codex(-cut[0-9]+)?")
CODEX_ACCOUNT_READ_REQ = ('{"jsonrpc":"2.0","id":2,'
                          '"method":"account/read","params":{}}')
CODEX_ACCOUNT_RATE_REQ = ('{"jsonrpc":"2.0","id":3,'
                          '"method":"account/rateLimits/read","params":{}}')
CODEX_ACCOUNT_USAGE_REQ = ('{"jsonrpc":"2.0","id":4,'
                           '"method":"account/usage/read","params":{}}')
CODEX_ACCOUNT_READ_ID = 2
CODEX_ACCOUNT_RATE_ID = 3
CODEX_ACCOUNT_USAGE_ID = 4
# auth-source variables the codex binary honours ahead of CODEX_HOME's
# auth.json -- popped BY NAME from every per-home env (D20), never read
CODEX_API_KEY_VARS = ("OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_ACCESS_TOKEN")
# v33.6 consume mode: the env gate (exactly "1"), the argument grammar, the
# consume request id, and the four legal outcomes
CONSUME_GATE_VAR = "PROBE_ALLOW_CONSUME"
CONSUME_ARG_RE = re.compile(r"[A-Za-z0-9_-]{1,128}")
CODEX_CONSUME_ID = 2
CODEX_CONSUME_OUTCOMES = ("reset", "nothingToReset", "noCredit", "alreadyRedeemed")


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
    """Classify an 'auth status' probe: (state, identity, plan, org_id).

    state: logged-in | logged-out | indeterminate. Prefers the JSON shape
    (2.1.201 emits a JSON object with a loggedIn field; banner-wrapped JSON
    is found by raw_decode scanning, and only a dict carrying loggedIn
    counts); falls back to string matching for older text output. plan is
    the JSON subscriptionType field (the claude plan-tier source evidenced
    live) or None -- the text fallback never yields one. org_id (v33.5) is
    the JSON orgId field on a LOGGED-IN answer only, and only when it is a
    non-empty string: logged-out, the text fallback, and indeterminate all
    yield None.
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
                return "logged-out", None, plan, None
            org_id = data.get("orgId")
            org_id = org_id if isinstance(org_id, str) and org_id else None
            email = data.get("email") or ""
            org = data.get("orgName") or ""
            identity = (email + (" (" + org + ")" if org else "")).strip() or "logged in"
            return "logged-in", identity, plan, org_id
    blob = (text + "\n" + (stderr or "")).lower()
    if re.search(r"not logged in|logged out|no credentials|unauthenticated|please log ?in", blob):
        return "logged-out", None, None, None
    if "logged in" in blob or "email" in blob:
        m = re.search(r"[\w.+-]+@[\w.-]+", text + " " + (stderr or ""))
        return "logged-in", (m.group(0) if m else "logged in"), None, None
    return "indeterminate", None, None, None


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


def is_eligible_codex_home(path: str) -> bool:
    """The NAMED codex-home eligibility predicate (v33.6) -- shared by
    enumeration, --codex-home validation, and consume mode, and checked
    BEFORE every app-server spawn (the server writes state files into
    whatever home it is pointed at): a real directory (NOT a symlink) at
    ~/.codex or ~/.codex-cut<digits> containing an auth.json file. The name
    rule excludes *.lock control dirs and quarantine-marked dirs by
    construction. Unlike is_eligible_profile_dir() a symlinked home is
    INELIGIBLE -- never realpath-resolved (a link would let the server
    write through it); the parent must still realpath to $HOME."""
    p = os.path.abspath(os.path.expanduser(path))
    if os.path.realpath(os.path.dirname(p)) != os.path.realpath(os.path.expanduser("~")):
        return False
    if not CODEX_HOME_NAME_RE.fullmatch(os.path.basename(p)):
        return False
    if os.path.islink(p) or not os.path.isdir(p):
        return False
    return os.path.isfile(os.path.join(p, "auth.json"))


def enumerate_codex_homes() -> list[dict]:
    """Eligible codex homes (predicate-filtered), realpath-deduped, in
    sorted glob order -- the default ~/.codex INCLUDED (unlike the claude
    enumerator). Items: {"home": <glob path>, "real": <realpath>}."""
    out: list[dict] = []
    seen: set[str] = set()
    for d in sorted(glob.glob(os.path.expanduser("~/.codex*"))):
        if not is_eligible_codex_home(d):
            continue
        real = os.path.realpath(d)
        if real in seen:
            continue
        seen.add(real)
        out.append({"home": d, "real": real})
    return out


def codex_default_home_real() -> str:
    """Realpath of $HOME/.codex -- the is_default key (a symlinked default
    resolves to its target, so the target's own entry is the default)."""
    return os.path.realpath(os.path.expanduser("~/.codex"))


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
    v32 additive evidence fields present at their fail-closed values, plus
    the v33.5 additive week_model_* fields)."""
    return {"status": "skipped", "headline": None, "session_pct": None,
            "session_resets": None, "week_pct": None, "week_resets": None,
            "usage_quality": "none", "usage_source": "none",
            "availability_band": "unknown", "limit_status": None,
            "limit_utilization": None, "limit_resets_at": None,
            "limit_resets": None, "week_model_pct": None,
            "week_model_name": None, "week_model_resets": None}


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


def trust_prompt_keys(text: str):
    """The key sequence that selects the TRUST option on a captured
    workspace-trust prompt, or None when the selection is not established
    (v33.3 D2 -- the caller re-captures and NEVER confirms on None).

    Observed shapes: CLI 2.1.226 lists " > 1. Yes, I trust this folder" /
    "   2. No, exit" (Yes highlighted first); CLI 2.1.278 lists
    "<glyph> No, exit" / "  Yes, I trust this folder" with NO option
    numbers and "No, exit" highlighted first (verified live 2026-09-20),
    so a bare Enter there quits the CLI. Three outcomes:
      highlighted Yes                      -> ["Enter"]
      highlighted No, Yes listed BELOW it  -> ["Down", "Enter"]
      anything else -- no highlight, both highlighted, a duplicated
      option line (the capture is the whole scrollback, so a stale frame
      can ride along), an unexpected layout -> None.
    """
    options = []  # (kind, highlighted) in pane order
    for ln in (text or "").split("\n"):
        m = TRUST_OPTION_RE.match(ln)
        if m:
            options.append(("yes" if m.group(2).lower().startswith("yes")
                            else "no", bool(m.group(1))))
    kinds = [k for k, _h in options]
    if kinds.count("yes") != 1 or kinds.count("no") != 1:
        return None
    lit = [k for k, h in options if h]
    if lit == ["yes"]:
        return ["Enter"]
    if lit == ["no"] and kinds == ["no", "yes"]:
        return ["Down", "Enter"]
    return None


def panel_has_chrome_prompt(text: str) -> bool:
    """The "Claude in Chrome extension detected" interstitial (2.1.278:
    can follow the trust answer on a first launch). Marker-based; shares
    no marker with the workspace-trust prompt."""
    low = (text or "").lower()
    return any(marker in low for marker in CHROME_PROMPT_MARKERS)


def chrome_prompt_keys(text: str):
    """["Enter"] when the Chrome interstitial's DECLINE option ("No, keep
    browser tools off") is the one highlighted option, else None (the
    caller re-captures and never confirms -- the D2 rule; Down is never
    sent, so the probe can never turn browser tools ON)."""
    options = []
    for ln in (text or "").split("\n"):
        m = CHROME_OPTION_RE.match(ln)
        if m:
            options.append(("no" if m.group(2).lower().startswith("no")
                            else "yes", bool(m.group(1))))
    kinds = [k for k, _h in options]
    if kinds.count("no") != 1 or kinds.count("yes") > 1:
        return None
    if [k for k, h in options if h] == ["no"]:
        return ["Enter"]
    return None


def panel_input_ready(text: str) -> bool:
    """Interactive-input readiness on a captured pane: any of the
    PANEL_READY_MARKERS (the legacy shortcut hint line, or the 2.1.278
    permission-mode status line)."""
    return any(marker in (text or "") for marker in PANEL_READY_MARKERS)


def _panel_heading(line: str):
    """Classify a panel line as a segment boundary. Returns 'session' /
    'week' (the two PARSED anchors), 'model' (v33.5: a model-specific
    weekly block, parsed into the additive week_model_* fields and NEVER
    substituted into the week anchors), 'other' (a boundary that ends the
    current segment without opening a parsed one -- the contribution/
    skills sections, or a model block whose name is unextractable), or
    None."""
    s = line.strip()
    if s.startswith("Current session"):
        return "session"
    if s.startswith("Current week (all models)"):
        return "week"
    if s.startswith("Current week ("):
        return "model" if WEEK_MODEL_NAME_RE.match(s) else "other"
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
    week (<Model>):" blocks are 'model' segments whose values ride the
    additive week_model_* fields (v33.5 -- the FIRST such segment only,
    never week_pct/week_resets, and model evidence ALONE is not a usage
    block: a pane carrying no session/week anchor still returns None);
    promo lines ("+50% weekly limits promo...") carry no "% used";
    contribution lines ("92% of your usage...") carry no "used" after
    the percent; "Per-model breakdown unavailable (rate limited)"
    matches nothing and never blocks. Bar glyphs and the non-ASCII
    separator collapse to spaces before matching (never keyed on).
    """
    lines = [re.sub(r"[^\x20-\x7e]", " ", ln)
             for ln in (text or "").split("\n")]
    found: dict = {}
    model: dict = {}
    i = 0
    n = len(lines)
    while i < n:
        kind = _panel_heading(lines[i])
        if kind not in ("session", "week", "model"):
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
            elif kind == "model" and not model:
                # v33.5: the FIRST model segment only, kept apart from
                # found so a model-only pane is still "no usage block"
                name = WEEK_MODEL_NAME_RE.match(lines[i].strip())
                model = {"week_model_pct": pct,
                         "week_model_name": (name.group(1).strip()
                                             if name else None),
                         "week_model_resets": resets}
        i = j
    if found and model:
        found.update(model)
    return found or None


def tmux_binary():
    """First tmux on PATH, or None (absent -> the panel layer is skipped)."""
    hits = which_all("tmux")
    return hits[0] if hits else None


def probe_usage_panel(pinned: str, is_wsl: bool, config_dir: str | None,
                      cwd: str | None = None, tmux: str | None = None):
    """Layer-2 tmux interactive-panel usage probe (v32 TD.1; layer 2 since
    v33.3 -- probe_usage() launches it only when the one stream-json call
    produced no exact evidence). Returns a complete usage dict on a PARSED
    panel, else None (on every failure the caller keeps the stream-json
    outcome it already holds -- this layer never errors the row).

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
    # per-CALL unique (uuid4), never per-process: pooled panel probes that
    # start in the same millisecond must not share a tmux server (D3)
    label = "cbg-usage-" + uuid.uuid4().hex
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
        chrome_answered = False
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
                    # D2: select the trust option EXPLICITLY; an
                    # unestablished selection is re-captured on the next
                    # poll (within the deadline) and never confirmed
                    keys = trust_prompt_keys(pane)
                    if keys is not None:
                        for key in keys:
                            tmux_call(["send-keys", "-t", target, key])
                        trust_answered = True
                    continue
                if panel_has_chrome_prompt(pane) and not chrome_answered:
                    # the Chrome-extension interstitial: decline with Enter
                    # ONLY while the decline option is highlighted; checked
                    # BEFORE readiness so "/usage" is never typed into it
                    keys = chrome_prompt_keys(pane)
                    if keys is not None:
                        for key in keys:
                            tmux_call(["send-keys", "-t", target, key])
                        chrome_answered = True
                    continue
                if panel_input_ready(pane):
                    tmux_call(["send-keys", "-t", target, "/usage"])
                    tmux_call(["send-keys", "-t", target, "Enter"])
                    usage_sent = True
                continue
            parsed = parse_usage_panel(pane)
            if parsed is None:
                if PANEL_USAGE_FAILED_MARKER in pane:
                    # v33.7: the CLI's usage read failed and the panel
                    # shows no bars -- nothing will parse before the
                    # deadline, so the layer-1 outcome stands now
                    return None
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
                        "week_pct", "week_resets",
                        "week_model_pct", "week_model_name",
                        "week_model_resets"):
                if parsed.get(key) is not None:
                    result[key] = parsed[key]
            result["headline"] = anchored_headline(result)
            result["availability_band"] = usage_band(result)
            return result
        return None
    finally:
        try:
            run_cli([tmux, "-L", label, "kill-server"], 5.0, env=env)
        except Exception:
            pass


def anchored_headline(result: dict):
    """The headline rebuilt from the two anchored fields (the panel and
    the v33.7 usage_report path, whose evidence carries no print lines)."""
    bits = []
    if result["session_pct"] is not None:
        bits.append(SESSION_LINE_PREFIX + " " + str(result["session_pct"])
                    + "% used" + (" - resets " + result["session_resets"]
                                  if result["session_resets"] else ""))
    if result["week_pct"] is not None:
        bits.append(WEEK_ALL_LINE_PREFIX + " " + str(result["week_pct"])
                    + "% used" + (" - resets " + result["week_resets"]
                                  if result["week_resets"] else ""))
    return " | ".join(bits) or None


def parse_usage_report(out: str):
    """The usage_report twin of print-mode /usage (v33.7; observed on CLI
    2.1.286 on the local-command assistant event): the LAST assistant
    event's usage_report.rate_limits.limits list, or None (no report, or
    rate_limits null -- the failed-read shape)."""
    limits = None
    for obj in iter_json_objects(out or ""):
        if not isinstance(obj, dict) or obj.get("type") != "assistant":
            continue
        report = obj.get("usage_report")
        if not isinstance(report, dict):
            continue
        rate_limits = report.get("rate_limits")
        found = (rate_limits.get("limits")
                 if isinstance(rate_limits, dict) else None)
        limits = found if isinstance(found, list) else None
    return limits


def _report_resets(value):
    """A usage_report resets_at (ISO-8601 with an offset) -> the local ISO
    minute string (the codex.usage *_resets form), or None. A naive or
    unparseable stamp is never guessed into a zone."""
    if not isinstance(value, str) or not value:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        stamp = datetime.fromisoformat(text)
        if stamp.tzinfo is None:
            return None
        return stamp.astimezone().isoformat(timespec="minutes")
    except (OverflowError, OSError, ValueError):
        return None


def usage_from_report(limits) -> tuple:
    """Map a usage_report limits list onto the anchored fields (v33.7) ->
    (anchored, model) in _usage_from_stream's shapes. kind "session" ->
    session_*, "weekly_all" -> week_* (the FIRST of each); the FIRST
    "weekly_scoped" entry naming a model -> week_model_* (never
    substituted into week_*). percent floors to an int like the CLI's own
    print line; a non-numeric, negative or non-finite percent is skipped."""
    anchored: dict = {}
    model: dict = {}
    for item in limits or []:
        if not isinstance(item, dict):
            continue
        pct = item.get("percent")
        if (isinstance(pct, bool) or not isinstance(pct, (int, float))
                or not math.isfinite(pct) or pct < 0):
            continue
        pct = int(math.floor(pct))
        resets = _report_resets(item.get("resets_at"))
        kind = item.get("kind")
        if kind == "session" and "session_pct" not in anchored:
            anchored["session_pct"], anchored["session_resets"] = pct, resets
        elif kind == "weekly_all" and "week_pct" not in anchored:
            anchored["week_pct"], anchored["week_resets"] = pct, resets
        elif kind == "weekly_scoped" and not model:
            scope = item.get("scope")
            scoped = scope.get("model") if isinstance(scope, dict) else None
            name = (scoped.get("display_name")
                    if isinstance(scoped, dict) else None)
            if isinstance(name, str) and name.strip():
                model = {"week_model_pct": pct,
                         "week_model_name": name.strip(),
                         "week_model_resets": resets}
    return anchored, model


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
    state, _identity, _plan, _org = parse_auth_status(out, err)
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
        # no help text acquired: the flag counts as not advertised (v33.6)
        return {"status": status if status in ("timeout",) else "failed",
                "aliases": [], "efforts": [],
                "error": (err or out or "").strip()[:300] or "help probe failed",
                "no_session_persistence": False}
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
    # v33.6 D10: computed from the acquired text alone -- the alias / effort
    # metadata status above never suppresses it
    return {"status": st, "aliases": aliases, "efforts": efforts,
            "error": None if st == "ok" else "help parsed but alias/effort extraction incomplete",
            "no_session_persistence":
                option_block(out, "--no-session-persistence") is not None}


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


def probe_claude_advisor(pinned: str, is_wsl: bool, timeout: float, version_value,
                         no_session_persistence: bool = False):
    """BILLED acceptance probe (only behind --probe-advisor): one cheap advisored run.

    The prompt INSTRUCTS the model to consult its advisor once -- advisor use
    is opportunistic (observed live 2026-07-10: a trivial prompt completed
    clean with zero engagement), so an engagement-forcing prompt is what makes
    the probe deterministic. Engagement detector: the advisor model appears in
    the result modelUsage (end-of-run deterministic check; it also rejects the
    silent soft-strip, whose stderr warning is captured for the error detail).
    v33.6: when the pinned CLI advertises it, the print-mode call carries the
    session-persistence opt-out (no session log is written).
    """
    cmd = [pinned, "-p",
           "Consult your advisor tool once on this question: is 2+2=4? "
           "Then reply with exactly: ok",
           "--model", ADVISOR_MAIN,
           "--advisor", ADVISOR_MODEL, "--output-format", "json"]
    if no_session_persistence:
        cmd.append("--no-session-persistence")
    status, out, err, rc = run_cli(cmd, max(timeout, 180.0), claude_env(pinned, is_wsl))
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
    """Per-account auth identity. The v33.5 additive org_id/auth_state ride
    after "plan": auth_state is the OBSERVED auth classification
    (logged-in | logged-out | indeterminate), and a command that never
    answered (timeout, absent binary) is "indeterminate" -- never a
    logout. org_id is populated on a logged-in answer only."""
    env = claude_env(pinned, is_wsl, config_dir)
    status, out, err, _rc = run_cli([pinned, "auth", "status"], timeout, env)
    if status == "timeout":
        return {"identity": None, "status": "timeout", "plan": None,
                "org_id": None, "auth_state": "indeterminate"}
    if status == "absent":
        return {"identity": None, "status": "failed", "plan": None,
                "org_id": None, "auth_state": "indeterminate"}
    state, identity, plan, org_id = parse_auth_status(out, err)
    if state == "logged-in":
        return {"identity": identity, "status": "ok", "plan": plan,
                "org_id": org_id, "auth_state": "logged-in"}
    if state == "logged-out":
        return {"identity": None, "status": "degraded",
                "plan": None, "org_id": None,
                "auth_state": "logged-out"}  # enumerable but not logged in
    return {"identity": None, "status": "degraded", "plan": None,
            "org_id": None, "auth_state": "indeterminate"}


def probe_accounts(pinned: str, is_wsl: bool, timeout: float,
                   config_dirs: list, cwd: str | None, usage: bool,
                   workers: int | None = None,
                   print_only: bool = False,
                   no_session_persistence: bool = False) -> list:
    """Identity + usage for every account, IN INPUT ORDER (v33.3 D3).

    config_dirs is the ordered account list (None = the default account,
    then each eligible profile dir). One job per account runs through a
    bounded thread pool -- run_cli / subprocess.run carry an explicit env
    and cwd per call and share no mutable state, and the panel layer's
    tmux label is per-call unique -- and the results come back in the
    SAME order as config_dirs regardless of completion order, so the
    emitted JSON document is byte-for-byte the serial shape. Workers =
    min(workers or PROBE_WORKERS, accounts); 1 runs serially in-thread.
    Wall clock scales with ceil(accounts / workers) batches. Each entry
    is probe_identity()'s dict plus its "usage" key. v33.5: print_only
    forwards --print-only (layer 2 never launches), and the identity's
    observed auth_state is handed to probe_usage so only a LOGGED-IN
    account can pay the degraded retry. v33.6: no_session_persistence
    (the pinned CLI advertises the flag) rides through to probe_usage.
    """
    def one(config_dir):
        entry = probe_identity(pinned, is_wsl, timeout, config_dir)
        entry["usage"] = (probe_usage(pinned, is_wsl, timeout, config_dir,
                                      cwd=cwd, print_only=print_only,
                                      auth_state=entry["auth_state"],
                                      no_session_persistence=no_session_persistence)
                          if usage else usage_skipped())
        return entry

    return _pooled_in_order(one, config_dirs, workers)


def _pooled_in_order(fn, items, workers: int | None) -> list:
    """[fn(item) for item in items], IN INPUT ORDER, through a bounded
    thread pool (v33.6 D3 -- the ONE pool site, shared by the claude
    accounts and the codex homes). Workers = min(workers or PROBE_WORKERS,
    len(items)); 1 runs serially in-thread; pool.map() yields in input
    order regardless of completion order."""
    items = list(items)
    count = max(1, min(workers or PROBE_WORKERS, len(items)))
    if count == 1:
        return [fn(item) for item in items]
    with ThreadPoolExecutor(max_workers=count) as pool:
        return list(pool.map(fn, items))  # map() yields in input order


def probe_usage(pinned: str, is_wsl: bool, timeout: float,
                config_dir: str | None, cwd: str | None = None,
                print_only: bool = False,
                auth_state: str | None = None,
                no_session_persistence: bool = False) -> dict:
    """LAYERED per-account usage probe (v32 TD.1; the full evidence
    contract lives in the module docstring's claude-usage mapping block).

    Layer 1 -- ONE billed '<pinned> -p "/usage" --output-format
    stream-json --verbose' call, FIRST (v33.3): print-mode /usage returns
    exact quota lines on CLI 2.1.278 (verified live 2026-09-20) and
    returned none at 2.1.226 on Cursor Cloud VMs. A result text carrying
    an ANCHORED quota field (parse_usage_line on the exact "Current
    session:" / "Current week (all models):" prefixes; a partial parse
    stays exact) is EXACT print evidence (usage_source "print") and
    returns at once -- the panel never launches. A bare "%" line
    (contribution stats, promo lines) is NEVER exact. Otherwise the
    stream's rate_limit_event yields THRESHOLD evidence (allowed /
    allowed_warning / rejected), else the degraded outcome. A
    timeout/failed first attempt is retried ONCE before degrading
    (v30.1: a cold store's first call can pay an OAuth token refresh
    that overruns the budget; 'absent' never retries). v33.5 degraded
    retry: a DEGRADED classification on a store the identity probe
    observed as auth_state "logged-in" runs the same call ONCE more and
    re-classifies (max 2 attempts on that branch) -- a logged-out,
    indeterminate, or unknown auth_state never pays it, since a
    logged-out store has no quota lines to recover.
    Layer 2 -- tmux interactive-panel probe, ONLY when layer 1 produced
    no exact evidence (threshold, degraded, timeout, failed): unbilled,
    exact, seated-store only. A PARSED panel outranks the layer-1
    outcome; tmux absent, deadline, or an unparseable panel returns the
    layer-1 outcome exactly as computed. An 'absent' pinned binary
    skips the panel (nothing to launch), and under print_only
    (--print-only) the panel never launches at all: every non-exact
    layer-1 outcome is returned exactly as computed.
    Layer 3 -- degraded: the existing status/headline behaviour, with
    usage_quality/usage_source "none" (v33.7: the CLI's failed-read
    shape -- banner, no quota lines -- carries the fixed
    USAGE_READ_FAILED_HEADLINE instead of the raw report text).
    v33.7: with no anchored text line, layer 1 also reads the call's
    structured usage_report twin as exact print evidence (text first).

    Threshold evidence NEVER lands in session_pct/week_pct and its
    headline is percentage-free; availability_band is computed on every
    outcome (PR-MED-002/PR-MED-010). v33.6: when the pinned CLI advertises
    it, every layer-1 attempt carries the session-persistence opt-out (the
    panel is interactive and never does).
    """
    env = claude_env(pinned, is_wsl, config_dir)
    cmd = [pinned, "-p", "/usage", "--output-format", "stream-json", "--verbose"]
    if no_session_persistence:
        cmd.append("--no-session-persistence")
    status, out, err, _rc = run_cli(cmd, max(timeout, 30.0), env, cwd=cwd)
    if status in ("timeout", "failed"):
        status, out, err, _rc = run_cli(cmd, max(timeout, 30.0), env, cwd=cwd)
    result = _usage_from_stream(status, out, err)
    if result["status"] == "degraded" and auth_state == "logged-in":
        # v33.5: a logged-in store that answered without quota lines is a
        # flaky print run, not a quota-less store -- one more call, then
        # the re-classification stands: this branch never re-runs a
        # second time (with the timeout/failed retry above, at most
        # three stream calls per account)
        status, out, err, _rc = run_cli(cmd, max(timeout, 30.0), env, cwd=cwd)
        result = _usage_from_stream(status, out, err)
    if result["usage_quality"] == "exact" or status == "absent":
        return result
    if print_only:
        return result  # --print-only: layer 2 never launches
    # no exact evidence in hand: the panel is the only other exact source
    panel = probe_usage_panel(pinned, is_wsl, config_dir, cwd=cwd)
    if panel is not None:
        return panel
    return result


def _usage_from_stream(status: str, out: str, err: str) -> dict:
    """Classify ONE finished stream-json /usage call (after the retry-once
    rule) into a complete usage dict: exact print evidence, threshold
    evidence, or the timeout / failed / degraded outcome."""
    result = usage_skipped()
    if status == "timeout":
        result.update(status="timeout", headline=None)
        return result
    if status in ("failed", "absent"):
        result.update(status="failed",
                      headline=(err or out or "").strip()[:200] or None)
        return result
    info, result_text = parse_rate_limit_stream(out)
    # exact print evidence first -- higher fidelity than threshold. EXACT
    # means an anchored quota field parsed; percent-bearing noise alone
    # (contribution / promo lines) continues to threshold / degraded.
    lines = [ln.strip() for ln in (result_text or "").split("\n")]
    anchored: dict = {}
    model: dict = {}   # v33.5: never exact evidence on its own
    for ln in lines:
        if "session_pct" not in anchored:
            hit = parse_usage_line(ln, SESSION_LINE_PREFIX)
            if hit is not None:
                anchored["session_pct"], anchored["session_resets"] = hit
                continue
        if "week_pct" not in anchored:
            hit = parse_usage_line(ln, WEEK_ALL_LINE_PREFIX)
            if hit is not None:
                anchored["week_pct"], anchored["week_resets"] = hit
                continue
        if not model:
            m = WEEK_MODEL_LINE_RE.match(ln)
            if m is not None:
                hit = parse_usage_line(ln, m.group(0))
                if hit is not None:
                    model = {"week_model_pct": hit[0],
                             "week_model_name": m.group(1).strip(),
                             "week_model_resets": hit[1]}
    if anchored:
        # v33.7: quota-shaped lines only -- the 2.1.286 report appends
        # contribution percentages ("86% of your usage ...") after them
        pct_lines = [ln for ln in lines if "%" in ln
                     and ln.startswith(("Current session", "Current week ("))]
        result.update(status="ok", headline=" | ".join(pct_lines[:4]),
                      usage_quality="exact", usage_source="print")
        result.update(anchored)
        result.update(model)
        result["availability_band"] = usage_band(result)
        return result
    # v33.7: no anchored text line -- the structured usage_report twin is
    # the same reading, so it is exact print evidence too (it shields the
    # parse from a reworded print line; on the failed-read shape it is
    # null as well and the chain continues unchanged)
    anchored, model = usage_from_report(parse_usage_report(out))
    if anchored:
        result.update(status="ok", usage_quality="exact", usage_source="print")
        result.update(anchored)
        result.update(model)
        result["headline"] = anchored_headline(result)
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
    # no anchored quota line, no event: the logged-out local-stats block
    # and every other unrecognized-but-clean exit land here
    text = (result_text or "").strip()
    if text.startswith(SUBSCRIPTION_BANNER_PREFIXES):
        # v33.7: a logged-in subscription report without quota lines is
        # the CLI's failed usage read -- name it, instead of carrying the
        # contribution report's unrelated percentages as the headline
        result.update(status="degraded", headline=USAGE_READ_FAILED_HEADLINE)
        return result
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


def codex_app_server_exchange(requests: list, env: dict, timeout: float) -> dict:
    """ONE codex app-server JSON-RPC exchange -- the transport shared by
    every app-server caller (v33.6 D1; extracted from the v33.3
    probe_codex_usage body with every D4 invariant below kept).

    `requests` is a list of JSON-RPC request strings, the first of them
    `initialize`; each request's wait id is read from its own JSON `id`.
    Returns {"replies": {<id>: <obj>}, "verdict": "ok" | "write-failed" |
    "eof" | "timeout" | "absent" | "spawn-failed", "detail": <str|None>,
    "stderr_tail": <str>, "deadline": <float>} -- `replies` holds the
    id-correlated reply objects present in the wait-end transcript (a
    verdict never removes a captured reply; every caller decides reply-
    first). `absent` = FileNotFoundError on spawn, `spawn-failed` = any
    other OSError (detail = the exception text); `write-failed` = a broken
    stdin write (detail = the error); otherwise, read from the wait-end
    snapshot: `ok` = every request AFTER the first has a correlated reply
    (the first, initialize, is awaited only up to the init window), else
    `timeout` / `eof` = the deadline / stdout EOF ended the wait first.

    Popen-based BY DESIGN, never run_cli: the server exits on closed stdin,
    so stdin must stay OPEN across the exchange. READ-UNTIL-REPLY (v33.3
    D4), no scripted sleeps: write the first request (initialize, id:1);
    wait until a parsed stdout line carries its id OR the init window
    elapses; write every remaining request; wait until each of their ids
    has a parsed line, stdout EOF, or the deadline -- max(timeout, 30),
    the ceiling of the whole exchange -- whichever first. The stdout
    transcript is FINAL at that moment (snapshotted once, under the lock,
    BEFORE the shutdown: a reply arriving during the shutdown is not
    parsed).

    ONE OWNER PER PIPE: two daemon reader threads own proc.stdout and
    proc.stderr from spawn to EOF (stderr is drained concurrently so a
    chatty server never blocks on a full pipe). There is NO communicate()
    call anywhere -- it would compete with the readers for the same
    pipes. Stream DISPOSAL is reader-owned: each reader closes its own
    stream at EOF; the main thread closes ONLY stdin and NEVER touches
    stdout/stderr (a CPython buffered close() takes the lock a blocked
    readline() holds, so closing a stream under a live reader would hang).
    Shutdown, on every success/failure/timeout path: close stdin ->
    bounded wait for the server's clean exit -> terminate -> wait(5) ->
    kill -> wait(5) on the RECORDED child only (recorded identity --
    never broad process matching) -> a bounded join on each reader. A
    reader still alive after its join bound (a descendant retaining the
    pipe) is ABANDONED -- daemon thread, stream left open for interpreter
    exit -- and the recorded child is still reaped within its own bound.

    This is the TRANSPORT layer only: a matching response id establishes
    CORRELATION, never success -- each caller's own semantic block over
    `replies` is the sole source of its statuses. Replies correlate on the
    requests' own ids ONLY (a bool id never correlates); notifications and
    banner lines are tolerated and ignored.
    """
    deadline = max(timeout, CODEX_USAGE_DEADLINE_FLOOR_S)
    wait_ids = [json.loads(req)["id"] for req in requests]
    ex = {"replies": {}, "verdict": "ok", "detail": None, "stderr_tail": "",
          "deadline": deadline}
    try:
        proc = subprocess.Popen(
            ["codex", "app-server"], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            cwd=neutral_probe_cwd(), env=env)
    except FileNotFoundError:
        ex.update(verdict="absent", detail="executable not found: codex")
        return ex
    except OSError as exc:
        ex.update(verdict="spawn-failed", detail=str(exc)[:200])
        return ex
    t0 = time.monotonic()
    timed_out = False
    write_error = None
    cond = threading.Condition()
    out_lines: list = []
    err_lines: list = []
    seen = {"ids": set(), "eof": False}  # stdout-side state, under cond

    def reply_id(line: str):
        """The JSON-RPC id of one stdout line, or None (banner/notice
        lines and id-less notifications tolerated; an id that is not a
        plain int/str -- unhashable shapes included -- is an ignorable
        line, never a reader crash)."""
        line = line.strip()
        if not line.startswith("{"):
            return None
        try:
            obj = json.loads(line)
        except ValueError:
            return None
        rid = obj.get("id") if isinstance(obj, dict) else None
        if isinstance(rid, bool) or not isinstance(rid, (int, str)):
            return None  # True == 1 in a set: a bool id must never correlate
        return rid

    def pump(stream, sink, is_stdout: bool) -> None:
        """The ONE owner of its pipe, spawn to EOF: appends every line
        under the lock and, at EOF, closes its OWN stream."""
        try:
            for line in iter(stream.readline, ""):
                with cond:
                    sink.append(line)
                    if is_stdout:
                        rid = reply_id(line)
                        if rid is not None:
                            seen["ids"].add(rid)
                    cond.notify_all()
        except (OSError, ValueError):
            pass  # a torn-down pipe reads as EOF
        finally:
            try:
                stream.close()
            except (OSError, ValueError):
                pass
            if is_stdout:
                with cond:
                    seen["eof"] = True
                    cond.notify_all()

    def wait_for_replies(rids: list, until: float) -> bool:
        """Block until a parsed stdout line carries each id in rids, stdout
        EOF, or the monotonic instant `until` -- whichever first."""
        with cond:
            while (not all(rid in seen["ids"] for rid in rids)
                   and not seen["eof"]):
                left = until - time.monotonic()
                if left <= 0:
                    break
                cond.wait(left)
            return all(rid in seen["ids"] for rid in rids)

    readers = [
        threading.Thread(target=pump, args=(proc.stdout, out_lines, True),
                         name="codex-usage-stdout", daemon=True),
        threading.Thread(target=pump, args=(proc.stderr, err_lines, False),
                         name="codex-usage-stderr", daemon=True)]
    for reader in readers:
        reader.start()

    stdout_data = ""
    try:
        try:
            proc.stdin.write(requests[0] + "\n")
            proc.stdin.flush()
            # the init window survives only as the id:1 wait CEILING
            wait_for_replies(wait_ids[:1], min(t0 + CODEX_USAGE_INIT_WINDOW_S,
                                               t0 + deadline))
            for req in requests[1:]:
                proc.stdin.write(req + "\n")
                proc.stdin.flush()
        except (OSError, ValueError) as exc:
            write_error = str(exc)[:200]
        if write_error is None:
            if not wait_for_replies(wait_ids[1:], t0 + deadline):
                with cond:
                    timed_out = not seen["eof"]
        # transport wait over (reply / EOF / deadline / write error): the
        # stdout transcript is FINAL here -- one snapshot, under the lock
        with cond:
            stdout_data = "".join(out_lines)
    finally:
        # recorded-identity shutdown, guaranteed on every path: close
        # stdin (OURS -- the only stream the main thread ever closes),
        # bounded clean-exit wait -> terminate -> wait -> kill -> wait on
        # the Popen handle recorded above (never any other process),
        # then bounded reader joins. A reader outliving its join bound is
        # abandoned with its stream OPEN (reader-owned disposal).
        try:
            proc.stdin.close()
        except (OSError, ValueError):
            pass
        try:
            try:
                proc.wait(timeout=CODEX_USAGE_EXIT_GRACE_S)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:
                    proc.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    try:
                        proc.wait(timeout=5.0)
                    except subprocess.TimeoutExpired:
                        pass
        except OSError:
            pass  # terminate/kill raced an already-gone child
        for reader in readers:
            reader.join(CODEX_USAGE_READER_JOIN_S)
    with cond:
        stderr_data = "".join(err_lines)  # diagnostic tail only

    for line in stdout_data.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue  # banner/notice lines tolerated
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        # exact-id correlation ONLY (the last matching line wins); id-less
        # notifications are tolerated and ignored
        rid = obj.get("id") if isinstance(obj, dict) else None
        if isinstance(rid, bool):
            continue
        for want in wait_ids:
            if rid == want:
                ex["replies"][want] = obj
    ex["stderr_tail"] = (stderr_data or "").strip()[:200]
    # the verdict is read from the SNAPSHOT: a reply that landed after the
    # wait's deadline exit but before the snapshot counts as replied
    if write_error is not None:
        ex.update(verdict="write-failed", detail=write_error)
    elif all(rid in ex["replies"] for rid in wait_ids[1:]):
        ex["verdict"] = "ok"
    elif timed_out:
        ex["verdict"] = "timeout"
    else:
        ex["verdict"] = "eof"
    return ex


def classify_codex_windows(limits: dict, result: dict, with_iso: bool) -> int:
    """Fill result's session_* / week_* fields from a rateLimits object's
    primary/secondary cells, classified by windowDurationMins (300 session
    / 10080 week), NEVER by position; returns the number of windows whose
    usedPercent classified. Shared by codex.usage (with_iso=True: the
    derived local-ISO *_resets strings too) and codex.accounts[]
    (with_iso=False: *_resets_at only)."""
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
            if with_iso:
                try:
                    result[key + "_resets"] = (
                        datetime.fromtimestamp(resets_at).astimezone()
                        .isoformat(timespec="minutes"))
                except (OverflowError, OSError, ValueError):
                    result[key + "_resets"] = None
    return classified


def probe_codex_usage(timeout: float) -> dict:
    """The codex app-server account/rateLimits/read usage probe (--usage).

    ONE codex_app_server_exchange() (above: spawn, read-until-reply wait,
    recorded-identity shutdown) with [initialize (id:1),
    account/rateLimits/read (id:2)] on probe_env() -- the ambient
    CODEX_HOME inherited, exactly as v33.5. Outcomes are two-layered.
    TRANSPORT, consulted ONLY when no id:2 reply was captured: a broken
    stdin write -> failed; stdout EOF before the reply -> failed (stderr
    tail); the deadline -> timeout. A matching response id establishes
    CORRELATION, never success: the captured reply then passes through the
    semantic block below, the sole source of ok / degraded / failed. The
    response is correlated on the rate-limit request id ONLY; initialize
    responses, notifications, and banner lines are tolerated and ignored.
    Windows classify by windowDurationMins (300 session / 10080 week),
    never by primary/secondary position.
    """
    result = codex_usage_skipped()
    result.update(status="failed")
    ex = codex_app_server_exchange(
        [CODEX_USAGE_INIT_REQ, CODEX_USAGE_RATE_REQ], probe_env(),
        timeout)  # v32 PR-HIGH-021
    if ex["verdict"] == "absent":
        result.update(status="absent", error=ex["detail"])
        return result
    if ex["verdict"] == "spawn-failed":
        result.update(status="failed", error=ex["detail"])
        return result
    resp = ex["replies"].get(CODEX_USAGE_RATE_ID)
    if resp is None:
        # precedence: a captured response would have won above; a concrete
        # transport/write failure is never hidden by the later timeout state
        # (a write error with EMPTY text falls through, as v33.3's
        # `if write_error:` did)
        if ex["verdict"] == "write-failed" and ex["detail"]:
            result.update(status="failed",
                          error="request write failed: " + ex["detail"])
        elif ex["verdict"] == "timeout":
            result.update(status="timeout",
                          error="no rate-limit response within "
                                + str(ex["deadline"]) + "s")
        else:
            result.update(status="failed",
                          error="no id:" + str(CODEX_USAGE_RATE_ID)
                                + " response; stderr: "
                                + ex["stderr_tail"])
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
    classified = classify_codex_windows(limits, result, with_iso=True)
    if classified:
        result.update(status="ok", error=None)
    else:
        result.update(status="degraded",
                      error="rateLimits parsed but no recognizable "
                            "windowDurationMins (300/10080)")
    return result


def codex_home_env(home: str) -> dict:
    """The per-home app-server env (v33.6 D20): probe_env() (token-
    stripped), the API-key auth variables popped BY NAME (never read,
    compared, or echoed -- the binary honours them ahead of the home's
    auth.json, so one exported would make every home answer as that key),
    then CODEX_HOME SET explicitly (never inherited). The legacy
    codex.usage exchange and 'codex debug models' keep probe_env()."""
    env = probe_env()
    for name in CODEX_API_KEY_VARS:
        env.pop(name, None)
    env["CODEX_HOME"] = home
    return env


def codex_account_entry(home: str, status: str = "skipped", error=None) -> dict:
    """One codex.accounts[] entry: every contract key present, in contract
    order, value fields null until a reply fills them. is_default =
    realpath(home) == realpath($HOME/.codex)."""
    return {"home": home,
            "is_default": os.path.realpath(home) == codex_default_home_real(),
            "status": status, "error": error, "email": None, "plan": None,
            "account_id": None, "session_pct": None, "session_resets_at": None,
            "week_pct": None, "week_resets_at": None, "reset_credits": None,
            "daily_tokens": None, "additional_limits": None}


def _codex_result(reply):
    """A reply's result object, or None (no reply / rpc error / drift)."""
    if isinstance(reply, dict) and isinstance(reply.get("result"), dict):
        return reply["result"]
    return None


def _codex_rpc_detail(reply) -> str:
    """The failure detail of a reply that carries no result object."""
    err = reply.get("error") if isinstance(reply, dict) else None
    if isinstance(err, dict) and isinstance(err.get("message"), str):
        return err["message"][:200]
    if err is not None:
        return json.dumps(err)[:200]
    return "reply carries no result object"


def _nonempty_str(value):
    return value if isinstance(value, str) and value else None


def _fill_codex_account(entry: dict, acct, rate, usage) -> None:
    """The D16 field mapping over the parsed read results (any may be
    None): identity from account/read, plan / account id / reset credits
    from account/rateLimits/read, daily tokens from account/usage/read.
    The app-server's null-vs-empty semantics pass through untouched."""
    account = acct.get("account") if acct else None
    account = account if isinstance(account, dict) else {}
    routing = acct.get("workspaceRouting") if acct else None
    routing = routing if isinstance(routing, dict) else {}
    limits = rate.get("rateLimits") if rate else None
    limits = limits if isinstance(limits, dict) else {}
    if account.get("type") == "chatgpt":
        entry["email"] = _nonempty_str(account.get("email"))
    entry["plan"] = (_nonempty_str(limits.get("planType"))
                     or _nonempty_str(account.get("planType")))
    entry["account_id"] = (_nonempty_str((rate or {}).get("accountId"))
                           or _nonempty_str(routing.get("chatgptAccountId")))
    credits = (rate or {}).get("rateLimitResetCredits")
    if isinstance(credits, dict):
        count = credits.get("availableCount")
        items = credits.get("credits")
        entry["reset_credits"] = {
            "available_count": (count if isinstance(count, int)
                                and not isinstance(count, bool) else None),
            "items": ([{"id": c.get("id"), "status": c.get("status"),
                        "granted_at": c.get("grantedAt"),
                        "expires_at": c.get("expiresAt"),
                        "title": c.get("title")}
                       for c in items if isinstance(c, dict)]
                      if isinstance(items, list) else None)}
    buckets = (usage or {}).get("dailyUsageBuckets")
    if isinstance(buckets, list):
        entry["daily_tokens"] = [{"date": b["startDate"], "tokens": b["tokens"]}
                                 for b in buckets if isinstance(b, dict)
                                 and "startDate" in b and "tokens" in b]


def _probe_codex_account(home: str, timeout: float) -> dict:
    entry = codex_account_entry(home, "failed")
    ex = codex_app_server_exchange(
        [CODEX_USAGE_INIT_REQ, CODEX_ACCOUNT_READ_REQ, CODEX_ACCOUNT_RATE_REQ,
         CODEX_ACCOUNT_USAGE_REQ], codex_home_env(home), timeout)
    verdict = ex["verdict"]
    stderr_note = "; stderr: " + ex["stderr_tail"] if ex["stderr_tail"] else ""
    # (1) transport failure: nothing was fully exchanged, no reply consulted
    if verdict in ("absent", "spawn-failed"):
        entry["error"] = ex["detail"]
        return entry
    if verdict == "write-failed":
        entry["error"] = ("request write failed: " + (ex["detail"] or "")
                          + stderr_note)[:300]
        return entry
    replies = ex["replies"]
    acct = _codex_result(replies.get(CODEX_ACCOUNT_READ_ID))
    # (2) a null account is conclusive: the -32600 errors after it are expected
    if acct is not None and "account" in acct and acct["account"] is None:
        entry.update(status="logged-out", error=None)
        return entry
    rate_reply = replies.get(CODEX_ACCOUNT_RATE_ID)
    rate = _codex_result(rate_reply)
    usage = _codex_result(replies.get(CODEX_ACCOUNT_USAGE_ID))
    _fill_codex_account(entry, acct, rate, usage)
    # (3) no deciding reply: the verdict decides
    if rate_reply is None:
        if verdict == "timeout":
            entry.update(status="timeout",
                         error="no rate-limit response within "
                               + str(ex["deadline"]) + "s")
        else:
            entry["error"] = ("stdout closed before account/rateLimits/read "
                              "replied" + stderr_note)[:300]
        return entry
    # (4) the rate-limit reply decides, whatever the verdict
    if rate is None:
        entry["error"] = "account/rateLimits/read: " + _codex_rpc_detail(rate_reply)
        return entry
    limits = rate.get("rateLimits")
    if not isinstance(limits, dict):
        entry.update(status="degraded",
                     error="account/rateLimits/read parsed but no rateLimits "
                           "object (shape drift)")
        return entry
    if not classify_codex_windows(limits, entry, with_iso=False):
        entry.update(status="degraded",
                     error="rateLimits parsed but no recognizable "
                           "windowDurationMins (300/10080)")
        return entry
    # (5) ok also needs both auxiliary reads as parsed result objects
    problems = []
    for rid, method, parsed in ((CODEX_ACCOUNT_READ_ID, "account/read", acct),
                                (CODEX_ACCOUNT_USAGE_ID, "account/usage/read",
                                 usage)):
        if parsed is not None:
            continue
        reply = replies.get(rid)
        problems.append(method + ": " + (_codex_rpc_detail(reply)
                                         if reply is not None
                                         else "no reply (" + verdict + ")"))
    if problems:
        entry.update(status="degraded", error="; ".join(problems)[:300])
    else:
        entry.update(status="ok", error=None)
    return entry


def probe_codex_account(home: str, timeout: float) -> dict:
    """ONE codex account per eligible CODEX_HOME (v33.6; only behind
    --usage). One codex_app_server_exchange() on codex_home_env(home) with
    initialize (1), account/read (2), account/rateLimits/read (3), and
    account/usage/read (4). Status, REPLY-FIRST in this fixed order (D9;
    only replies in the wait-end transcript count): (1) a spawn / write
    failure -> failed; (2) account/read with a null account -> logged-out
    (every value field null); (3) no rate-limit reply -> timeout under the
    deadline, else failed; (4) the rate-limit reply decides -- an rpc
    error -> failed, no rateLimits object / no recognizable window ->
    degraded, >= 1 window -> (5) ok only when account/read and
    account/usage/read are parsed result objects too, else degraded with
    the read and cause named. Value fields reflect whatever replies were
    captured. Any internal error becomes this home's own failed entry
    (D18) -- one home never blanks the others."""
    try:
        return _probe_codex_account(home, timeout)
    except Exception as exc:
        return codex_account_entry(home, "failed", "internal: " + str(exc)[:200])


def probe_codex_accounts(homes: list, timeout: float,
                         workers: int | None = None) -> list:
    """probe_codex_account() for every home through the shared in-order
    pool (D3): results in input order, --workers bounded."""
    return _pooled_in_order(lambda home: probe_codex_account(home, timeout),
                            homes, workers)


def codex_consume_request(credit_id: str, key: str) -> str:
    """The consume-mode JSON-RPC request (v33.6): the ONE place the probe's
    single write-capable method is named (a selftest source pin)."""
    return json.dumps({"jsonrpc": "2.0", "id": CODEX_CONSUME_ID,
                       "method": "account/rateLimitResetCredit/consume",
                       "params": {"creditId": credit_id,
                                  "idempotencyKey": key}},
                      separators=(",", ":"))


def consume_document(home: str, status: str, outcome=None, error=None) -> dict:
    """The consume document's inner object -- exactly these four keys."""
    return {"home": home, "status": status, "outcome": outcome, "error": error}


def classify_consume(home: str, ex: dict) -> dict:
    """The consume document over one codex_app_server_exchange() result, by
    a TOTAL, reply-first table (v33.6): (1) no process (absent /
    spawn-failed) -> failed with the transport detail; (2) a correlated
    consume reply decides whatever the verdict (a write error can follow
    a request the server already answered) -- ok only with an outcome in
    the four-value set, else failed (an rpc error's detail, or the
    unexpected value; never an invented outcome); (3) no reply: write
    failure -> failed "request write failed: ...", deadline -> timeout,
    EOF -> failed "stdout closed before the consume reply". A timeout or
    failure AFTER the request was written is INDETERMINATE (the credit may
    have been consumed): the consumer re-reads account/rateLimits/read
    before retrying with the SAME idempotency key; the probe never retries."""
    verdict = ex["verdict"]
    stderr_note = "; stderr: " + ex["stderr_tail"] if ex["stderr_tail"] else ""
    if verdict in ("absent", "spawn-failed"):
        return consume_document(home, "failed", error=ex["detail"])
    reply = ex["replies"].get(CODEX_CONSUME_ID)
    if reply is not None:
        result = _codex_result(reply)
        if result is None:
            return consume_document(home, "failed",
                                    error="consume: " + _codex_rpc_detail(reply))
        outcome = result.get("outcome")
        if isinstance(outcome, str) and outcome in CODEX_CONSUME_OUTCOMES:
            return consume_document(home, "ok", outcome=outcome)
        return consume_document(home, "failed",
                                error=("unexpected outcome: "
                                       + json.dumps(outcome))[:200])
    if verdict == "write-failed":
        return consume_document(home, "failed",
                                error=("request write failed: "
                                       + (ex["detail"] or "") + stderr_note)[:300])
    if verdict == "timeout":
        return consume_document(home, "timeout",
                                error="no consume response within "
                                      + str(ex["deadline"]) + "s")
    return consume_document(home, "failed",
                            error=("stdout closed before the consume reply"
                                   + stderr_note)[:300])


def consume_codex_reset(home: str, credit_id: str, key: str,
                        timeout: float) -> dict:
    """ONE consume exchange against one CODEX_HOME (v33.6; reached only
    through run_consume(), behind the env gate): an ineligible home is the
    failed "ineligible home" document WITHOUT a spawn (the server writes
    state into whatever home it is pointed at); else initialize + the
    consume request on codex_home_env(home) -- nothing else is sent."""
    if not is_eligible_codex_home(home):
        return consume_document(home, "failed", error="ineligible home")
    ex = codex_app_server_exchange(
        [CODEX_USAGE_INIT_REQ, codex_consume_request(credit_id, key)],
        codex_home_env(home), timeout)
    return classify_consume(home, ex)


def select_codex_homes(requested) -> list:
    """The ordered codex.accounts rows: [{"home", "eligible"}]. No request
    = every enumerated eligible home. A request keeps argument order and
    runs the predicate PER SPELLING first (PR-MED-009): eligible spellings
    dedup by realpath (first wins), ineligible spellings by their
    normalized supplied path -- the two sets never suppress each other."""
    if not requested:
        return [{"home": h["home"], "eligible": True}
                for h in enumerate_codex_homes()]
    rows: list = []
    seen_real: set = set()
    seen_bad: set = set()
    for raw in requested:
        p = os.path.abspath(os.path.expanduser(raw))
        if is_eligible_codex_home(p):
            real = os.path.realpath(p)
            if real in seen_real:
                continue
            seen_real.add(real)
            rows.append({"home": p, "eligible": True})
        elif p not in seen_bad:
            seen_bad.add(p)
            rows.append({"home": p, "eligible": False})
    return rows


def build_codex_accounts(args) -> list:
    """codex.accounts (v33.6; ALWAYS emitted): an ineligible requested
    home is failed "ineligible home" and NEVER spawned (with or without
    --usage); eligible entries are probed under --usage (never under
    --profile-dir), else skipped."""
    rows = select_codex_homes(getattr(args, "codex_home", None))
    run = bool(args.usage) and not args.profile_dir
    probed = iter(probe_codex_accounts(
        [r["home"] for r in rows if r["eligible"]] if run else [],
        args.timeout, workers=getattr(args, "workers", None)))
    out: list = []
    for r in rows:
        if not r["eligible"]:
            out.append(codex_account_entry(r["home"], "failed", "ineligible home"))
        elif run:
            out.append(next(probed))
        else:
            out.append(codex_account_entry(r["home"]))
    return out


def legacy_codex_usage_runs(args) -> bool:
    """codex.usage is probed under --usage and no --profile-dir and (no
    --codex-home, or $HOME/.codex's realpath among the requested homes --
    v33.6 D2); otherwise it is the v33.5 skipped shape."""
    if not args.usage or args.profile_dir:
        return False
    requested = getattr(args, "codex_home", None)
    if not requested:
        return True
    default = codex_default_home_real()
    return any(os.path.realpath(os.path.abspath(os.path.expanduser(h))) == default
               for h in requested)


def claude_skeleton(status: str) -> dict:
    """The probe_claude() document before any probe ran (v33.6 D5): its
    initial dict ("failed" until proven) and the --codex-home skipped leg."""
    return {"status": status, "error": None, "candidates": [], "pinned": None,
            "help": {"status": "skipped", "aliases": [], "efforts": [],
                     "error": None, "no_session_persistence": False},
            "version": {"value": None, "status": "skipped", "error": None},
            "advisor": {"value": None, "status": "skipped", "error": None,
                        "version": None},
            "profile_dir_filter": None,
            "default_account": {"identity": None, "status": "skipped",
                                "plan": None, "org_id": None,
                                "auth_state": None,
                                "usage": usage_skipped()},
            "profiles": []}


def probe_claude(args, is_wsl: bool) -> dict:
    out = claude_skeleton("failed")
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
    # v33.6 D10: every print-mode call carries the session-persistence
    # opt-out when the pinned CLI advertises it (.get: a help dict without
    # the key means "not advertised")
    nsp = out["help"].get("no_session_persistence", False)
    out["version"] = probe_claude_version(pinned, is_wsl, args.timeout)
    if args.probe_advisor:
        out["advisor"] = probe_claude_advisor(pinned, is_wsl, args.timeout,
                                              out["version"]["value"],
                                              no_session_persistence=nsp)

    # ---- pass 2 (store-touching CLI): identity + usage per account, from
    # the neutral cwd so probe-created entries land under excluded munges
    # (v33.3 D3: one pooled job per account, assembled in input order; the
    # snapshots above were taken BEFORE the pool starts)
    probe_cwd = neutral_probe_cwd()
    probed = probe_accounts(pinned, is_wsl, args.timeout,
                            [None] + [p["dir"] for p in prof_entries],
                            probe_cwd, bool(args.usage),
                            workers=getattr(args, "workers", None),
                            print_only=getattr(args, "print_only", False),
                            no_session_persistence=nsp)
    ident = probed[0]
    ident["config_dir"] = default_dir
    ident["config_source"] = default_source
    ident["aliases_profile"] = alias_hit
    ident["marker_email"] = read_profile_email_marker(default_dir)
    ident["recent_repos"] = default_projects
    out["default_account"] = ident
    for p, entry in zip(prof_entries, probed[1:]):
        prof = {"dir": p["dir"]}
        prof.update(entry)
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
    'Paused since:' / 'Paused reason:' bullets ("" when a field is absent --
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
        # v32 (TE.4): Paused plans are surfaced regardless of a Loop config --
        # discoverable + recoverable, never an Active candidate. Additive
        # field inside probe_schema 1; a paused plan WITH a config also still
        # counts in non_active_with_config (paused IS non-active -- the
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
    elif claude["status"] == "skipped":
        claude_seg = "claude SKIPPED (--codex-home)"
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


def _workers_arg(value: str) -> int:
    """argparse type for --workers: an integer >= 1."""
    try:
        n = int(value)
    except ValueError:
        n = 0
    if n < 1:
        raise argparse.ArgumentTypeError("--workers must be an integer >= 1")
    return n


TIMEOUT_BOUND_MSG = ("--timeout must be a finite number of seconds, at most "
                     + str(int(PROBE_TIMEOUT_MAX_S)))


def _timeout_in_bounds(value) -> bool:
    """The --timeout rule, shared by the parse-time type and run_consume()'s
    direct-seam re-check: a real number, finite, at most one day. An int
    is compared exactly -- never converted to a float, which overflows
    for a huge int (v33.6 PR-LOW-013); zero and negative values pass (the
    per-probe floor applies), as in v33.5."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, int):
        return value <= PROBE_TIMEOUT_MAX_S
    return math.isfinite(value) and value <= PROBE_TIMEOUT_MAX_S


def _timeout_arg(value: str) -> float:
    """argparse type for --timeout (v33.6 PR-MED-011 / PR-MED-012): a
    finite number of seconds, at most PROBE_TIMEOUT_MAX_S -- a NaN would
    make every exchange deadline NaN (an unbounded wait) and a huge value
    overflows the timed waits. Zero and negative values keep their v33.5
    behaviour (each probe's own floor applies)."""
    try:
        v = float(value)
    except ValueError:
        v = float("nan")
    if not _timeout_in_bounds(v):
        raise argparse.ArgumentTypeError(TIMEOUT_BOUND_MSG)
    return v


def build_parser() -> argparse.ArgumentParser:
    """The command-line parser (v33.6 D7; allow_abbrev=False -- an
    abbreviated flag is refused, never silently expanded)."""
    ap = argparse.ArgumentParser(
        description="Run the execute-loop wizard Step 0 probes; emit one JSON document.",
        allow_abbrev=False)
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
    ap.add_argument("--print-only", dest="print_only", action="store_true",
                    help="claude usage layer 1 ONLY: the tmux interactive "
                         "panel (layer 2) never launches, so every non-exact "
                         "print outcome (threshold, degraded, timeout, "
                         "failed) is reported as computed")
    ap.add_argument("--probe-advisor", dest="probe_advisor", action="store_true",
                    help="run the BILLED advisor acceptance probe (one advisored spawn)")
    ap.add_argument("--timeout", type=_timeout_arg, default=15.0,
                    help="per-subprocess timeout in seconds (default 15)")
    ap.add_argument("--plans-dir", default=".cursor/plans",
                    help="plans directory for the Q1 scan (default .cursor/plans)")
    ap.add_argument("--workers", type=_workers_arg, default=None, metavar="N",
                    help="parallel per-account probe workers, N >= 1 "
                         "(default " + str(PROBE_WORKERS) + ", capped at the "
                         "account count; 1 = serial)")
    ap.add_argument("--codex-home", dest="codex_home", action="append",
                    metavar="DIR",
                    help="repeatable: limit the codex accounts leg to the "
                         "named CODEX_HOME dir(s) and SKIP the claude leg; "
                         "an ineligible DIR is reported failed, never "
                         "probed; not with --profile-dir")
    ap.add_argument("--consume-codex-reset", dest="consume_codex_reset",
                    action="store_true",
                    help="WRITE-capable, env-gated: consume ONE codex rate-"
                         "limit reset credit for the single --codex-home "
                         "DIR; needs --credit-id and --idempotency-key once "
                         "each; refused (exit 2, nothing run) unless the "
                         "environment enables it; no other mode flag")
    ap.add_argument("--credit-id", dest="credit_id", action="append",
                    metavar="ID",
                    help="consume mode only: the reset credit id "
                         "([A-Za-z0-9_-]{1,128})")
    ap.add_argument("--idempotency-key", dest="idempotency_key",
                    action="append", metavar="KEY",
                    help="consume mode only: the caller's idempotency key "
                         "([A-Za-z0-9_-]{1,128}; reuse it when retrying)")
    return ap


def resolve_mode(parser: argparse.ArgumentParser, args, environ) -> str:
    """Every cross-argument check (v33.6 D7), refused via parser.error()
    (exit 2, usage + one error line on stderr, nothing on stdout).
    Returns the run mode: "probe" or "consume".

    Consume mode (D6 / D8), checked IN THIS ORDER: the env gate FIRST (its
    message wins over every other semantic error), then --credit-id and
    --idempotency-key exactly once each, both values in the grammar, none
    of the four mode flags, --codex-home exactly once. --workers,
    --plans-dir, and --timeout are accepted and inert (only --timeout is
    read: the exchange ceiling)."""
    if args.consume_codex_reset:
        if environ.get(CONSUME_GATE_VAR) != "1":
            parser.error("--consume-codex-reset is not enabled")
        for flag, values in (("--credit-id", args.credit_id),
                             ("--idempotency-key", args.idempotency_key)):
            if not values or len(values) != 1:
                parser.error("--consume-codex-reset needs " + flag
                             + " exactly once")
        for flag, values in (("--credit-id", args.credit_id),
                             ("--idempotency-key", args.idempotency_key)):
            if not CONSUME_ARG_RE.fullmatch(values[0]):
                parser.error(flag + " must match [A-Za-z0-9_-]{1,128}")
        for flag, present in (("--usage", args.usage),
                              ("--profile-dir", args.profile_dir),
                              ("--print-only", args.print_only),
                              ("--probe-advisor", args.probe_advisor)):
            if present:
                parser.error("--consume-codex-reset cannot be combined with "
                             + flag)
        if not args.codex_home or len(args.codex_home) != 1:
            parser.error("--consume-codex-reset needs --codex-home exactly once")
        return "consume"
    if args.credit_id or args.idempotency_key:
        parser.error("--credit-id / --idempotency-key need --consume-codex-reset")
    if args.codex_home and args.profile_dir:
        parser.error("--codex-home cannot be combined with --profile-dir")
    return "probe"


def run_consume(parser: argparse.ArgumentParser, home: str, credit_id: str,
                key: str, timeout: float, environ) -> int:
    """Consume mode (v33.6): print {"probe_schema": 1, "consume": {...}} and
    return 0. The env gate is RE-CHECKED here (D21: no direct call can
    bypass resolve_mode()), then the --timeout bound (the direct seam
    cannot bypass the parse-time guard) -- both refusals exit 2 before any
    spawn. Everything after them is wrapped: an internal error prints the
    failed "internal: ..." document at exit 0 (D23), never a traceback."""
    if environ.get(CONSUME_GATE_VAR) != "1":
        parser.error("--consume-codex-reset is not enabled")
    if not _timeout_in_bounds(timeout):
        parser.error(TIMEOUT_BOUND_MSG)
    path = home
    try:
        path = os.path.abspath(os.path.expanduser(home))
        doc = consume_codex_reset(path, credit_id, key, timeout)
    except Exception as exc:
        doc = consume_document(path, "failed", error="internal: " + str(exc)[:200])
    print(json.dumps({"probe_schema": 1, "consume": doc}, indent=2))
    return 0


def main(argv: list | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if resolve_mode(parser, args, os.environ) == "consume":
        return run_consume(parser, args.codex_home[0], args.credit_id[0],
                           args.idempotency_key[0], args.timeout, os.environ)

    is_wsl = host_is_wsl()
    doc: dict = {
        "probe_schema": 1,
        "generated": datetime.now().astimezone().isoformat(timespec="seconds"),
        "host": {"platform": sys.platform, "is_wsl": is_wsl,
                 "python": platform.python_version()},
        "capabilities": ["profile-dir-filter", "week-model", "org-id",
                         "print-only", "codex-homes"],
    }
    try:
        doc["codex"] = probe_codex(args.timeout)
    except Exception as exc:  # never let one probe kill the document
        doc["codex"] = {"status": "failed", "error": "internal: " + str(exc)[:200],
                        "listed_count": 0, "total_count": 0, "models": []}
    try:
        # --codex-home limits the run to the codex accounts leg (D5): the
        # claude leg never runs -- no candidate, subprocess, or snapshot
        doc["claude"] = (claude_skeleton("skipped") if args.codex_home
                         else probe_claude(args, is_wsl))
    except Exception as exc:
        doc["claude"] = {"status": "failed", "error": "internal: " + str(exc)[:200],
                         "candidates": [], "pinned": None,
                         "help": {"status": "failed", "aliases": [], "efforts": [],
                                  "error": None, "no_session_persistence": False},
                         "version": {"value": None, "status": "failed", "error": None},
                         "advisor": {"value": None, "status": "skipped", "error": None,
                                     "version": None},
                         "default_account": {"identity": None, "status": "failed",
                                             "plan": None, "org_id": None,
                                             "auth_state": None,
                                             "usage": {"status": "skipped",
                                                       "headline": None,
                                                       "session_pct": None,
                                                       "session_resets": None,
                                                       "week_pct": None,
                                                       "week_resets": None,
                                                       "week_model_pct": None,
                                                       "week_model_name": None,
                                                       "week_model_resets": None}},
                         "profiles": []}
    # a SUPPORT token (v33.6 D10): the pinned CLI advertises the flag, so
    # every print-mode call this run makes carries it
    if doc["claude"]["help"].get("no_session_persistence") is True:
        doc["capabilities"].append("no-session-persistence")
    # The codex usage leg runs AFTER probe_claude so every projects/
    # snapshot precedes every usage subprocess (snapshot-before-usage, both
    # families); it is skipped under --profile-dir (a claude-only re-check)
    # and under a --codex-home list without $HOME/.codex (v33.6 D2).
    if legacy_codex_usage_runs(args):
        try:
            doc["codex"]["usage"] = probe_codex_usage(args.timeout)
        except Exception as exc:
            fallback = codex_usage_skipped()
            fallback.update(status="failed", error="internal: " + str(exc)[:200])
            doc["codex"]["usage"] = fallback
    else:
        doc["codex"]["usage"] = codex_usage_skipped()
    # the per-home accounts pool runs after the legacy exchange, never
    # concurrently with it; an enumeration failure yields [] (D18)
    try:
        doc["codex"]["accounts"] = build_codex_accounts(args)
    except Exception:
        doc["codex"]["accounts"] = []
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
