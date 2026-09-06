#!/usr/bin/env python3
"""loop-journal.py — stateless validated emission helper for /execute-loop
probe-log records (round-3 records-mechanization, plan
.cursor/plans/plan-v31-round3-records-mechanization.md, DR-2).

WHY: run #5's natural experiment — wrapper-emitted shapes had zero defects
all run; composer-emitted shapes produced ~24 findings. Emission moves into
tooling; models supply JUDGMENT VALUES (result one-liners, reasons, choices,
severities, counts), this tool supplies FORMAT. Unknown types, subtypes, or
enum values REFUSE loudly (exit 2, nothing written) — invention is
structurally impossible on tool-written lines.

INVOCATION SURFACE (pinned by DR-2; the checker-grant precedent —
`python3 scripts/loop-journal.py ...`):
  GLOBAL: --run <runkey> --role <role>            REQUIRED on every subcommand
          [--log <probe-log>]                     optional on emit/escape-check
                                                  (stdout default — the wrapper
                                                  redirect path); REQUIRED on
                                                  flush/idle-check
          --log-root <dir>                        REQUIRED on escape-check and
                                                  idle-check
          [--epoch <id>]                          where the shape carries epoch=
          [--event-ts <iso>]                      emit ONLY; REFUSED on computed
                                                  subcommands
  SUBCOMMANDS (exactly six):
    emit <TYPE> [--round <n> --id <finding-ID>] [--repo <root>] [key=value ...]
    escape-check --capture pre|post --leg <leg> --log-root <dir>
                 --root <name>=</abs/path> [--root ...]
    flush [--dry-run]
    idle-check
    run-close --iso <iso-id> --base </abs/base> --outcome <o> [--plan] [--attest]
    fold-delegation --base </abs/base> --iso <iso-id> --leg <leg>
                 (v32.2 T2.3 — the delegation staging→canonical promotion; the
                 canonical stage-<N>-delegation.log's ONLY writer; COMPOSER-ONLY
                 at the grant layer: spawned-role grants carry only the narrowed
                 emission shapes, so this mutating subcommand is unreachable
                 from a scoped role — under perms=bypass no grant boundary
                 exists and the close-table confirm covers it)

  emit TYPE tokens: MONITOR CONSUME CLASSIFY ADOPT KILL_DUP SENTINEL_ARMED
  SENTINEL_FIRE SPAWN VERIFY_FAIL
  IDENTITY VERIFY_OK NOTIFY:<state> WATCH:armed WATCH:cancelled ROLE:start
  ROLE:end OWNERSHIP:<subtype>.

SEAT GATE (R16 PR-HIGH-001, operator-disposed coherent extension): every
composer-owned OWNERSHIP subtype (COMPOSER_ONLY_SUBTYPES) and the flush WRITE
path require `--role composer`; the subject-role shapes (exit-census,
escape-check) and the role-owned `emit VERIFY_OK` stay role-open, and
`flush --dry-run` stays read-open for RESUME derivation. The gate is a
MIS-ATTRIBUTION guard, NOT caller authentication — `--role` is argv for every
caller; the boundary that makes composer-owned records unreachable from a
spawned role is the GRANT/PROCESS layer (the wrapper's composer-only
exact-path grant pattern), retained as the R12 PR-MED-001 item.

REFUSALS BY DESIGN (each closes a run-5 finding class):
  - `emit CONSUME source=idle-reentry` — the checkpoint/suppression shapes are
    `idle-check`'s alone (a hand-supplied gap_min= cannot bypass the
    computation; F-08/F-21).
  - `emit OWNERSHIP:escape-check` — digests are COMPUTED by the escape-check
    subcommand; a hand-supplied digest is F-04's exact bug class.
  - IDENTITY without session= (F-01); ROLE:start without phase= or carrying
    profile_dir= (F-07 + STICKY:51's prohibition); commit sha= (F-23);
    unknown subtypes `gate-decision`/`phase-close` (F-20/F-24); unknown types
    (`PHASE:` — the F-03 class; F-03's original token `SENTINEL_FIRE:` was
    ADMITTED at v32 TB.3, so the refusal is re-pinned on a still-unadmitted
    shape); caller-supplied ts=/logged_ts=/mode=/hash=.
  - INPUT SAFETY (Critical Constraint 13): any value containing \\n, \\r, or a
    C0 control character; any value containing `"` (the quote grammar has no
    escape — an embedded quote injects well-formed keys); root/path values
    containing `|` or `;` (roots-manifest delimiters). One invocation writes
    exactly the lines it declares; values are taken VERBATIM per key=value
    argv token, never re-split.

CLOCK: ts= is a real tool clock read (local ISO with offset). `--event-ts`
stamps ts=<event> plus logged_ts=<now> and refuses a backwards pair.

ATOMIC PAIR: a gate OWNERSHIP (auto-disposition | must-pause) emission is ONE
invocation writing the OWNERSHIP record + its paired NOTIFY: record with
identical ts=/key= (STICKY section 7 item 1); mode= is COMPUTED from
class+severity (the TIERING table is fully mechanical) and the per-OS desktop
notice fires on mode=immediate (override: LOOP_JOURNAL_NOTICE_CMD; the NOTIFY
state records the delivery truth — sent/failed/queued).

VOCABULARY: validated against the embedded V_base block below, generated by
`python3 scripts/loop-grammar-oracle.py --emit-vocab` (DR-7 single source).
The round-3 planned delta was reconciled and DELETED at R8 (2026-07-31): the
oracle admitted the delta shapes and its fixture suite asserts
V_oracle == V_effective — the block is byte-equal to --emit-vocab output, so
helper and oracle can never validate from diverging vocabularies.

Exit codes: 0 = emitted; 2 = refused (nothing written); 3 = environment
failure (unwritable log, git absent for --repo derivation).
"""

import datetime
import errno
import hashlib
import os
import re
import stat
import subprocess
import sys

# --- BEGIN EMBEDDED VOCABULARY V_base (generated by scripts/loop-grammar-oracle.py --emit-vocab; regenerated pure at R8, 2026-07-31 — DR-7) ---
# Generated by `python3 scripts/loop-grammar-oracle.py --emit-vocab` (DR-7,
# round-3 R8) — ONE vocabulary source: helper and oracle validate from the
# same enums. Do NOT hand-edit; regenerate + re-splice on any oracle
# vocabulary change (the oracle fixture suite asserts this block byte-equal
# to --emit-vocab output).
ENUMS = {
    "BACKENDS": {"claude-p", "codex", "cursor-subagent", "live-session"},
    "DELIVERY_ENUM": {"bg", "fg"},
    "ESCAPE_RESULTS": {"clean", "dirty"},
    "HANDOFF_REASONS": {"composer-run", "must-pause", "phase-complete"},
    "IDENTITY_KEYS": {"claude", "pid", "session", "shell"},
    "ISOLATION_MODES": {"branch", "none", "worktree"},
    "JOURNAL_TYPES": (
        "CONSUME",
        "CLASSIFY",
        "ADOPT",
        "KILL_DUP",
        "OWNERSHIP",
        "VERIFY_OK",
        "VERIFY_FAIL",
        "SENTINEL_ARMED",
        "SENTINEL_FIRE",
        "SPAWN",
        "IDENTITY",
        "NOTIFY",
    ),
    "LAYER1_ENUM": {"bg-shell", "fg-wait", "native", "subagent-harness"},
    "LAYER2_ENUM": {"monitor", "none", "sentinel"},
    "MONITOR_EVENTS": {"anchor", "anomaly", "dead-at-spawn", "exit", "liveness"},
    "NOTIFY_CLASSES": {
        "auto-disposition",
        "cap-accept",
        "cap-raise",
        "config-conflict",
        "docs-only",
        "invalid",
        "must-pause",
    },
    "NOTIFY_IMMEDIATE_CLASSES": {
        "cap-accept",
        "cap-raise",
        "config-conflict",
        "docs-only",
        "invalid",
        "must-pause",
    },
    "NOTIFY_MODES": {"immediate", "queued"},
    "NOTIFY_STATES": {"batch-flushed", "failed", "queued", "retried", "sent", "skipped"},
    "OWNERSHIP_SUBTYPES": {
        "auto-disposition",
        "commit",
        "config-change",
        "config-revoke",
        "config-snapshot",
        "escape-check",
        "exit-census",
        "gate-disposition",
        "label-snapshot",
        "must-pause",
        "phases-extended",
        "profile-switch",
        "run-close",
        "smoke-pass",
        "sticky-ack",
    },
    "ROLE_ENUM": {
        "advisor",
        "architect",
        "composer",
        "delegate",
        "executor",
        "peer",
        "reviewer",
    },
    "RUN_CLOSE_CELLS": {
        "cleaned",
        "contended",
        "crashed",
        "creation-window",
        "dirty",
        "identity-mismatch",
        "journal-artifact-mismatch",
        "marker-only",
        "merge-failed",
        "merging",
        "paused",
        "pre-journal",
        "retained-green",
        "verified-merge",
    },
    "RUN_CLOSE_VERDICTS": {"already-closed", "complete", "refused", "retained"},
    "SEVERITIES": {"crit", "high", "low", "med"},
    "WATCH_VERBS": {"armed", "cancelled"},
}
NOTIFY_MODE_BY_STATE = {
    "batch-flushed": {"queued"},
    "failed": {"immediate", "queued"},
    "queued": {"queued"},
    "retried": {"immediate", "queued"},
    "sent": {"immediate"},
    "skipped": {"immediate", "queued"},
}
MATRIX_REQUIRED = {
    "config-change": ("key", "from", "to"),
    "config-revoke": ("role", "key", "epoch"),
    "config-snapshot": ("role", "iso", "plan", "epoch", "key", "value"),
    "escape-check": ("role", "result", "before", "after", "roots"),
    "exit-census": ("role", "leg", "children"),
    "gate-disposition": ("key", "choice"),
    "label-snapshot": ("iso", "epoch", "plan"),
    "must-pause": ("key",),
    "profile-switch": ("from", "to", "transferred", "alive"),
    "run-close": ("role", "iso", "mode", "cell", "verdict"),
    "sticky-ack": ("role",),
}
TS_LOCAL_RE = re.compile(r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?[+-]\d{2}:\d{2}\Z")
DIGEST_RE = re.compile(r"\A[0-9a-f]{8,64}\Z")
# `REG` is an identity-only class: the verified severity is supplied
# separately as `severity=` / `verified=` on disposition records.
FINDING_ID_RE = re.compile(r"\A(?:PR\d*-)?(?:(REG)-\d+|(CRIT|HIGH|MED|LOW)-\d+)\Z")
RUNKEY_RE = re.compile(r"\Astage-\d+\Z")
IDLE_GAP_MIN = 30  # D8 threshold (DR-4), floored whole minutes
COMPOSER_WRITE_PREFIXES = (
    "Wake:",
    "WATCH:",
    "ROLE: start",
    "ROLE: end",
    "Loop config:",
    "CONSUME:",
    "CLASSIFY:",
    "ADOPT:",
    "KILL_DUP:",
    "OWNERSHIP:",
    "VERIFY_OK:",
    "SENTINEL_ARMED:",
    "IDENTITY:",
    "NOTIFY:",
    "SPAWN:",
    "VERIFY_FAIL:",
    "SPAWN_WRAPPER_START",
)
SUPPRESSION_KEYS = ("suppressed", "latest")
SUPPRESSED_VALUES = {"artifact-activity"}
REFUSED_VALUES = {"capture-failure"}
QUALIFIED_KEY_FORM = "<runkey>/r<round>/<finding-ID>"
EFFECTIVE_WRITE_TIME_RULE = (
    "valid logged_ts= else valid ts= per line (K7); the idle checkpoint/"
    "suppression record's ts= IS its write time (logged_ts refused there);"
    "the sticky-ack receipt is likewise contemporaneous (logged_ts refused — R4);"
    "never backwards, never future beyond FUTURE_SKEW_HOURS=24 (K5/K9)")
STRICT_CLASSES = (
    "exit-unexpanded-var",
    "bad-exit-shape",
    "modeless-legacy",
    "missing-epoch",
    "missing-batch",
    "batch-key-mismatch",
    "bad-mode",
    "bad-mode-state",
    "bad-ownership-subtype",
    "commit-seat-violation",
    "missing-hash",
    "missing-seat",
    "bad-children-count",
    "underscore-rearm-token",
    "live-token-drift",
    "role-no-space",
    "missing-key",
    "missing-choice",
    "missing-from",
    "missing-to",
    "missing-transferred",
    "bad-transferred",
    "missing-alive",
    "missing-result",
    "bad-result",
    "missing-before",
    "missing-after",
    "malformed-digest",
    "dirty-result-mismatch",
    "missing-roots",
    "malformed-roots",
    "missing-base",
    "roots-base-mismatch",
    "missing-label-check",
    "bad-label-check",
    "bad-role",
    "missing-gap-min",
    "bad-gap-min",
    "bad-class",
    "bad-class-mode",
    "ids-count-mismatch",
    "unparsed-item-key",
    "duplicate-pending-id",
    "bad-severity",
    "severity-key-mismatch",
    "bad-cap-raise",
    "mixed-route",
    "bad-verified",
    "orphan-verified",
    "missing-detail",
    "empty-detail",
    "missing-child",
    "bad-child",
    "logged-ts-on-checkpoint",
    "backwards-logged-ts",
    "bad-logged-ts",
    "future-ts",
    "empty-run",
    "empty-leg",
    "empty-epoch",
    "empty-session",
    "missing-iso",
    "missing-plan",
    "missing-labels",
    "bad-labels",
    "missing-role",
    "missing-leg",
    "missing-children",
    "bad-suppressed",
    "bad-refused",
    "refused-with-evidence",
    "missing-sticky-hash",
    "bad-config-key",
    "bad-config-value",
    "missing-config-hash",
    "config-hash-mismatch",
    "bad-revoke-epoch",
    "bad-authority-check",
    "missing-authority-epoch",
    "bad-authority-epoch",
    "orphan-authority-epoch",
    "mixed-attestation",
    "bad-cap-accept",
    "bad-delivery",
    "delivery-on-none",
)
WHOLE_FILE_CLASSES = (
    "duplicate-arm",
    "duplicate-start",
    "duplicate-end",
    "missing-leg",
    "reused-leg",
    "end-without-start",
    "handoff-unverified",
    "non-monotonic-write-order",
    "escape-check-window",
    "escape-check-root-shrink",
    "expected-roots-missing",
    "pending-ids",
    "idle-reentry-unfired",
    "idle-reentry-gap-mismatch",
    "queued-never-flushed",
    "dangling-retry",
    "class-route-mismatch",
    "mixed-owner-subtypes",
    "pairing",
    "wake-mode-drift",
    "unqualified-finding-key",
    "missing-sticky-ack",
    "queued-at-commit",
    "delivery-before-authority",
    "delivery-missing-wake",
    "delivery-arm-without-wake",
    "delivery-drift",
)
SCORED_BINDING_CLASSES = (
    "label-check-mismatch",
    "label-check-unauthorized",
    "label-check-unverifiable",
    "bad-label-snapshot",
    "bad-authority-snapshot",
    "authority-check-unverifiable",
    "authority-check-mismatch",
    "authority-unauthorized",
    "revoked-authority",
    "authority-epoch-mismatch",
    "bad-revocation",
)
VARIANT_TOKEN_CENSUS = (
    "backwards-logged-ts",
    "bad-authority-check",
    "bad-authority-epoch",
    "bad-backend",
    "bad-cap-accept",
    "bad-cap-raise",
    "bad-cell",
    "bad-child",
    "bad-children-count",
    "bad-class",
    "bad-class-mode",
    "bad-close-mode",
    "bad-config-key",
    "bad-config-value",
    "bad-delivery",
    "bad-gap-min",
    "bad-handoff-reason",
    "bad-label-check",
    "bad-labels",
    "bad-layer1",
    "bad-layer2",
    "bad-logged-ts",
    "bad-mode",
    "bad-mode-state",
    "bad-monitor-event",
    "bad-ownership-subtype",
    "bad-refused",
    "bad-result",
    "bad-revoke-epoch",
    "bad-role",
    "bad-severity",
    "bad-suppressed",
    "bad-transferred",
    "bad-verdict",
    "bad-verified",
    "batch-key-mismatch",
    "cancelled-without-reason",
    "commit-seat-violation",
    "config-hash-mismatch",
    "delivery-on-none",
    "dirty-result-mismatch",
    "duplicate-key",
    "duplicate-pending-id",
    "empty-after",
    "empty-alive",
    "empty-before",
    "empty-cell",
    "empty-children",
    "empty-choice",
    "empty-detail",
    "empty-epoch",
    "empty-from",
    "empty-iso",
    "empty-key",
    "empty-last",
    "empty-leg",
    "empty-log",
    "empty-mode",
    "empty-plan",
    "empty-result",
    "empty-role",
    "empty-roots",
    "empty-run",
    "empty-session",
    "empty-task",
    "empty-to",
    "empty-transferred",
    "empty-value",
    "empty-verdict",
    "future-ts",
    "ids-count-mismatch",
    "live-token-drift",
    "logged-ts-on-checkpoint",
    "malformed-digest",
    "malformed-quoting",
    "malformed-roots",
    "missing-after",
    "missing-alive",
    "missing-authority-epoch",
    "missing-backend",
    "missing-base",
    "missing-batch",
    "missing-before",
    "missing-cell",
    "missing-child",
    "missing-children",
    "missing-choice",
    "missing-config-hash",
    "missing-detail",
    "missing-epoch",
    "missing-event",
    "missing-from",
    "missing-gap-min",
    "missing-hash",
    "missing-iso",
    "missing-key",
    "missing-keys",
    "missing-label-check",
    "missing-labels",
    "missing-last",
    "missing-leg",
    "missing-log",
    "missing-mode",
    "missing-model",
    "missing-phase",
    "missing-plan",
    "missing-result",
    "missing-role",
    "missing-roots",
    "missing-round",
    "missing-run",
    "missing-seat",
    "missing-session",
    "missing-source",
    "missing-sticky-hash",
    "missing-task",
    "missing-to",
    "missing-transferred",
    "missing-value",
    "missing-verdict",
    "mixed-attestation",
    "mixed-route",
    "modeless-legacy",
    "none-without-reason",
    "orphan-authority-epoch",
    "orphan-verified",
    "profile-on-non-claude-p",
    "refused-with-evidence",
    "role-no-space",
    "roots-base-mismatch",
    "severity-key-mismatch",
    "stray-token",
    "underscore-rearm-token",
    "unparsed-item-key",
    "verb-form-monitor",
    "wake-key-legacy",
)
# --- END EMBEDDED VOCABULARY V_base ---

# The kv tokenizer — byte-identical to the oracle's parse_kv grammar (the
# oracle fixtures assert the embedded V_base block byte-equal to --emit-vocab;
# this constant lives OUTSIDE that block). The output chokepoint re-tokenizes
# an assembled line with the SAME grammar the downstream consumer uses.
PARSE_KV_RE = re.compile(r'(\S+?)="([^"]*)"|(\S+?)=(\S+)|(\S+)')
# The line-terminator set Python's str.splitlines() recognizes (incl. NEL
# U+0085 and the Unicode separators U+2028/U+2029): any one of these in an
# assembled record splits it into >1 physical line — a forged second record —
# even inside quotes. The output chokepoint (write_lines) rejects them
# regardless of the value's source (R28).
LINE_TERMINATORS = frozenset("\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029")

# DR-7 (R8, 2026-07-31): the ROUND-3 PLANNED DELTA block is DELETED — the
# oracle admitted the delta shapes (exit-census, the suppression keys, the
# DR-3 qualified-key form), the embedded block above is regenerated pure
# from `--emit-vocab`, and the oracle fixture suite asserts
# V_oracle == V_effective (byte-equality of the block). The V_* aliases
# collapse to the base table.
V_OWNERSHIP_SUBTYPES = ENUMS["OWNERSHIP_SUBTYPES"]
V_MATRIX = MATRIX_REQUIRED

# Per-type emission specs (V_base): required keys beyond ts/run, enum-valued
# keys, and canonical key order. `--role` fills role= where listed.
EMIT_SPECS = {
    "MONITOR": {"prefix": "MONITOR:", "verb": None,
                "required": ("event", "role", "task", "log", "last", "detail"),
                "enums": {"event": "MONITOR_EVENTS", "role": "ROLE_ENUM"}},
    "CONSUME": {"prefix": "CONSUME:", "verb": None, "required": ("source",), "enums": {}},
    "CLASSIFY": {"prefix": "CLASSIFY:", "verb": None, "required": (), "enums": {}},
    "ADOPT": {"prefix": "ADOPT:", "verb": None, "required": (), "enums": {}},
    "KILL_DUP": {"prefix": "KILL_DUP:", "verb": None, "required": (), "enums": {}},
    "SENTINEL_ARMED": {"prefix": "SENTINEL_ARMED:", "verb": None, "required": (), "enums": {}},
    # v32 TB.3 (run-7 F-2): the composer watch/sentinel narration families —
    # tool-emitted so no line-start token is ever hand-invented. SPAWN:/
    # VERIFY_FAIL: pin role (closed enum) + detail; SENTINEL_FIRE:'s role is
    # optional (the armed shell may omit it; enum-checked when present) and
    # its id=/reason= evidence keys ride as free kv. SENTINEL_FIRE is NOT a
    # COMPOSER_WRITE_PREFIXES member — see the V_base note (D8 idle clock).
    "SENTINEL_FIRE": {"prefix": "SENTINEL_FIRE:", "verb": None, "required": (),
                      "enums": {"role": "ROLE_ENUM"}},
    # SPAWN's role= is the WRITER (the --role identity owner, like every
    # record); the SPAWNED role rides child= (the exit-classify child-kind
    # vocabulary) — role= cannot carry it because role=/--role must agree.
    "SPAWN": {"prefix": "SPAWN:", "verb": None, "required": ("role", "child", "detail"),
              "enums": {"role": "ROLE_ENUM", "child": "ROLE_ENUM"}},
    "VERIFY_FAIL": {"prefix": "VERIFY_FAIL:", "verb": None, "required": ("role", "detail"),
                    "enums": {"role": "ROLE_ENUM"}},
    "IDENTITY": {"prefix": "IDENTITY:", "verb": "update",
                 "required": ("role", "session"), "enums": {"role": "ROLE_ENUM"}},
    "VERIFY_OK": {"prefix": "VERIFY_OK:", "verb": None, "required": ("children",), "enums": {}},
    # v32.2: delivery= is ADDITIVE-OPTIONAL on armed lines — RESOLVED values
    # only (fg|bg; `auto` is config vocabulary, never artifact state), and a
    # layer2=none arm never carries it (the oracle's delivery-on-none class;
    # the etype-specific check below owns that co-presence refusal).
    "WATCH:armed": {"prefix": "WATCH:", "verb": "armed",
                    "required": ("role", "layer1", "layer2"),
                    "enums": {"role": "ROLE_ENUM", "layer1": "LAYER1_ENUM",
                              "layer2": "LAYER2_ENUM",
                              "delivery": "DELIVERY_ENUM"}},
    "WATCH:cancelled": {"prefix": "WATCH:", "verb": "cancelled",
                        "required": ("role", "reason"), "enums": {"role": "ROLE_ENUM"}},
    "ROLE:start": {"prefix": "ROLE:", "verb": "start",
                   "required": ("phase", "role", "backend", "model", "leg"),
                   "enums": {"role": "ROLE_ENUM", "backend": "BACKENDS"}},
    "ROLE:end": {"prefix": "ROLE:", "verb": "end",
                 "required": ("role", "result", "leg"), "enums": {"role": "ROLE_ENUM"}},
}
# Gate subtypes whose emission is the ATOMIC OWNERSHIP+NOTIFY pair.
PAIR_SUBTYPES = {"auto-disposition", "must-pause"}
# R16 PR-HIGH-001 (uniform seat gate): every composer-owned OWNERSHIP subtype
# — all but the two subject-role shapes (exit-census is the wrapper/spawned
# role's record; escape-check is the spawning session's, refused via emit).
# The gate is a MIS-ATTRIBUTION guard, never caller authentication (see the
# cmd_emit note; the grant/process boundary is the retained R12 item).
# Round-4 S1 (DR4-1): `sticky-ack` JOINS the composer-owned set — the record
# is the composer's OWN run-start STICKY-read receipt (the helper stamps and
# enforces role=composer; a non-composer emission refuses).
COMPOSER_ONLY_SUBTYPES = frozenset(
    {"gate-disposition", "auto-disposition", "must-pause", "commit",
     "smoke-pass", "phases-extended", "config-change", "profile-switch",
     "label-snapshot", "sticky-ack", "config-snapshot", "config-revoke"})
# Reserved keys the CALLER may never supply on emit (tool-owned or refused).
RESERVED_KEYS = {"ts", "logged_ts", "run"}


def refuse(msg, expected=None):
    sys.stderr.write("REFUSE: %s\n" % msg)
    if expected:
        sys.stderr.write("EXPECTED: %s\n" % expected)
    sys.exit(2)


def envfail(msg):
    sys.stderr.write("ENVFAIL: %s\n" % msg)
    sys.exit(3)


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def parse_iso(value):
    if value is None or not TS_LOCAL_RE.match(value):
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError:
        return None


def check_value_safety(key, value, is_path=False):
    """Critical Constraint 13 — total, deterministic, refuse-not-sanitize.
    Whitespace-awareness is UNICODE, not ASCII (R13 H4 PR-HIGH-001 @ R27). Every
    downstream tokenizer (the helper + oracle parse_kv) uses Unicode `\\S`, and
    Python line-reading (`.splitlines()`) treats U+2028/U+2029/U+0085 as line
    terminators — so ANY whitespace beyond the ONE legal ASCII space (which
    fmt_kv quotes) can `\\S`-split or line-split a value and forge a field or a
    second record. Reproduced: `detail=ok<NBSP>seat=composer` forged the
    commit-authority `seat=` while classifying oracle-strict CLEAN. The prior
    guard rejected only `ord<0x20` (ASCII control), admitting the entire
    Unicode-whitespace class; that class is now rejected here (and fmt_kv also
    quotes on ANY whitespace, defense-in-depth). What this does NOT cover
    (stated honestly): value CONTENT beyond whitespace/quote/path-delimiter —
    prose, non-ASCII letters, ordinary paths — stays permitted; only the
    split / line-terminator vector is closed."""
    for ch in value:
        if ord(ch) < 0x20 or ord(ch) == 0x7f:
            refuse("value for %s= contains a control character (C0/\\n/\\r) — forged-record lever" % key)
        if ch != " " and ch.isspace():
            refuse("value for %s= contains Unicode whitespace (U+%04X) — only the ASCII space is legal (fmt_kv quotes it); any other whitespace lets a downstream Unicode-\\S tokenizer or .splitlines() split the value and forge a field (Constraint 13, PR-HIGH-001)" % (key, ord(ch)))
    if '"' in value:
        refuse("value for %s= contains a double quote — the quote grammar has no escape (injection lever)" % key)
    if is_path and ("|" in value or ";" in value):
        refuse("path/root value for %s= contains | or ; (roots-manifest delimiters)" % key)


KEY_ALLOWLIST_RE = re.compile(r"\A[a-z][a-z0-9_-]*\Z")  # \A..\Z, never ^..$ (R28: $ admits a trailing \n)


def check_key_safety(key):
    """Critical Constraint 13 — the KEY half, as a CLOSED ALLOWLIST (R13 H4
    PR-HIGH-001, hardened at R27). A caller key=value token's KEY reaches the
    record verbatim through fmt_kv, and every downstream tokenizer (the helper
    and oracle parse_kv) is Unicode-`\\S`-aware, so ANY whitespace in a key —
    ASCII **or Unicode** (NBSP, U+2028, U+3000, …) — splits the token and
    forges an extra/tool-owned field. The R26 fix was a DENYLIST of ASCII
    control bytes only (`ord<0x21`), which admitted the whole Unicode-
    whitespace class (reproduced: `<NBSP>ts=FORGED`). This is now an ALLOWLIST,
    closed BY CONSTRUCTION: a key MUST match `^[a-z][a-z0-9_-]*$` — the exact
    charset of the live emitted-key vocabulary (mechanically verified to cover
    all 55 keys incl. `cap-raise`/`gap_min`/`label_check`/`grants_include`).
    Nothing outside that regex can be emitted, so no whitespace, non-ASCII,
    quote, or structural byte ever reaches a key position. Empty keys are also
    refused at parse. What this does NOT cover (stated honestly): it does not
    validate key SEMANTICS — a well-formed but wrong key (e.g. `xyz=` on a
    record that has no such field) still passes here and rides the extras
    channel; that is out of scope for this forge boundary."""
    if not KEY_ALLOWLIST_RE.match(key):
        refuse("key %r is not in the closed key grammar ^[a-z][a-z0-9_-]*$ — a key is a lowercase [a-z0-9_-] token; any whitespace (ASCII or Unicode), non-ASCII, quote, or structural byte would let a downstream Unicode-\\S tokenizer split it and forge a field (Constraint 13, PR-HIGH-001)" % key[:60])


def fmt_kv(key, value):
    # Quote on ANY whitespace, not just ASCII space/tab (R27 defense-in-depth):
    # a quoted value cannot `\S`-split. check_value_safety already rejects every
    # non-ASCII-space whitespace, so for legal values this sees only the ASCII
    # space and the output is byte-identical to before — the isspace() widening
    # is a belt-and-suspenders guard against a future bypass, never a behaviour
    # change for the documented vocabulary. Keys are allowlist-clean (never spaced).
    if value == "" or any(ch.isspace() for ch in value):
        return '%s="%s"' % (key, value)
    return "%s=%s" % (key, value)


def parse_argv(argv):
    """Deterministic surface parse: flags (known set, each taking one value,
    except boolean --dry-run), one subcommand token, one optional TYPE token
    (emit), repeatable --root, and verbatim key=value tokens."""
    flags = {}
    roots = []
    kvs = []  # (key, value) in argv order
    sub = None
    etype = None
    dry_run = False
    value_flags = {"--run", "--role", "--log", "--log-root", "--epoch", "--event-ts",
                   "--round", "--id", "--repo", "--capture", "--leg",
                   "--iso", "--base", "--outcome", "--plan", "--attest"}
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--dry-run":
            dry_run = True
        elif tok == "--root":
            if i + 1 >= len(argv):
                refuse("--root needs a value", "--root name=/abs/path")
            roots.append(argv[i + 1])
            i += 1
        elif tok in value_flags:
            if i + 1 >= len(argv):
                refuse("%s needs a value" % tok)
            if tok in flags:
                refuse("duplicate flag %s" % tok)
            flags[tok] = argv[i + 1]
            i += 1
        elif tok.startswith("--"):
            refuse("unknown flag %s" % tok,
                   "global: --run --role [--log] [--log-root] [--epoch] [--event-ts]; "
                   "emit: [--round --id --repo]; escape-check: --capture --leg --root")
        elif sub is None:
            sub = tok
        elif sub == "emit" and etype is None and "=" not in tok:
            etype = tok
        elif "=" in tok:
            k, v = tok.split("=", 1)
            if not k:
                refuse("empty key in token %r" % tok)
            kvs.append((k, v))
        else:
            refuse("stray bare token %r" % tok, "values ride key=value tokens; the TYPE rides `emit <TYPE>`")
        i += 1
    return sub, etype, flags, roots, kvs, dry_run


def open_sink(flags):
    """stdout default; --log appends directly (one write per invocation)."""
    path = flags.get("--log")
    if path is None:
        return None
    if not os.path.isabs(path):
        refuse("--log must be an absolute path")
    return path


def assembled_line_ok(line, expected_tokens=None):
    """R28 OUTPUT CHOKEPOINT — the ROUND-TRIP FIDELITY invariant, and the actual
    GUARANTEE against forged records (the input-site checks are now fast-fail
    conveniences). Validates a FULLY ASSEMBLED record line immediately before
    write, PATH-INDEPENDENTLY — it does not matter whether a field came from a
    caller kv, a flag, a git-derived hash, or a child-read session id; if it is
    in the line, it is validated. Two checks:
      (1) NO line-terminator (LINE_TERMINATORS = str.splitlines()'s set, incl.
          U+0085 and the Unicode separators U+2028/U+2029) — a single physical
          line, so nothing forges a second record even inside quotes;
      (2) ROUND-TRIP FIDELITY — re-tokenizing with the helper's OWN PARSE_KV_RE
          (byte-identical to the oracle's) and rejoining on single spaces
          reproduces the line EXACTLY. A Unicode-whitespace / control split (a
          value/key that `\\S` breaks into extra fields) or abnormal spacing
          changes the token boundaries and the rejoin diverges → refuse. Uses the
          RAW matched text (m.group(0)), so hand-quoted values (roots="...") and
          fmt_kv-quoted values reproduce identically.
    Returns None if OK, else a reason string. COVERAGE (honest): HELPER-emitted
    records only — the wrapper's two native bash shapes (SPAWN_WRAPPER_START,
    EXIT:<code>) are written directly in bash and guarded by the wrapper's own
    require_token; this is NOT a global two-process chokepoint.

    R29 PR-HIGH-001: `expected_tokens` (the exact ordered token list the emitter
    BUILT — prefix bare-tokens + one element per fmt_kv'd field, quoted units
    counting as ONE token) is the INTENT. When supplied, the check compares the
    line's re-tokenization to it — parsed == INTENT, per the R28 design spec —
    so a value that split into an unintended extra field (e.g. an unquoted-space
    value forging `seat=composer`) is caught even though the line is internally
    self-consistent. When `expected_tokens` is None (records built without a
    threaded token list), the check falls back to SELF-CONSISTENCY (rejoin ==
    line) — sound only where every value is a tool-generated single token or a
    quoted literal; the emit/NOTIFY caller-taint paths always supply intent."""
    for ch in line:
        if ch in LINE_TERMINATORS:
            return "contains a line-terminator (U+%04X) — would forge a second physical record" % ord(ch)
    actual = [m.group(0) for m in PARSE_KV_RE.finditer(line)]
    if expected_tokens is not None:
        if actual != expected_tokens:
            return ("intent-fidelity failed — the assembled line re-parses to a token structure "
                    "that is NOT the one the emitter built (a split / injected / dropped field); "
                    "parsed=%r intended=%r" % (actual[:8], expected_tokens[:8]))
        return None
    if " ".join(actual) != line:
        return "round-trip fidelity failed — re-parsing the assembled line does not reproduce it (a split/injected field or abnormal spacing)"
    return None


def write_lines(sink, lines, token_lists=None):
    # R28 output chokepoint (R29: INTENT-fidelity): validate EVERY assembled line
    # BEFORE any write, so a refusal writes nothing (atomic across a multi-line
    # gate pair). token_lists (parallel to lines) supplies each emitter's INTENDED
    # token structure; None on a line falls back to self-consistency.
    for idx, l in enumerate(lines):
        exp = token_lists[idx] if token_lists is not None else None
        why = assembled_line_ok(l, exp)
        if why is not None:
            refuse("output chokepoint REFUSED a record before write: %s (R28/R29 fidelity; line=%r)"
                   % (why, l[:120]))
    payload = "".join(l + "\n" for l in lines)
    if sink is None:
        sys.stdout.write(payload)
        return
    try:
        with open(sink, "a", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
    except OSError as e:
        envfail("cannot append to --log %s: %s" % (sink, e))


NOTICE_TITLE = "execute-loop: operator needed"


def notice_spec(platform, runkey, summary):
    """Build (argv, env) for the desktop notice with the notification values
    carried ONLY as DATA — argv data elements on Linux/macOS, environment
    variables on Windows — NEVER concatenated into an interpreter program
    (PR-HIGH-001/round-7 lineage: PR-HIGH-003). The macOS `osascript` body
    reads its text from `argv`, and the Windows PowerShell body reads it from
    `$env:`, so a value containing a quote, `;`, backtick, or `$(...)` can
    never alter the executed program. The program text is byte-stable across
    values by construction."""
    body = "%s: %s" % (runkey, summary)
    if platform == "darwin":
        return (["osascript",
                 "-e", "on run argv",
                 "-e", "display notification (item 1 of argv) with title (item 2 of argv)",
                 "-e", "end run",
                 body, NOTICE_TITLE], {})
    if platform == "win32":
        prog = ("New-BurntToastNotification -Text "
                "$env:LOOP_JOURNAL_NOTICE_TITLE,$env:LOOP_JOURNAL_NOTICE_BODY")
        return (["powershell", "-NoProfile", "-NonInteractive", "-Command", prog],
                {"LOOP_JOURNAL_NOTICE_TITLE": NOTICE_TITLE,
                 "LOOP_JOURNAL_NOTICE_BODY": body})
    # linux and any other host: notify-send takes title/body as data args
    return (["notify-send", "-u", "critical", NOTICE_TITLE, body], {})


def fire_notice(runkey, summary):
    """One per-OS desktop notice; returns True on confirmed delivery.
    LOOP_JOURNAL_NOTICE_CMD overrides with title/body as DATA argv (selftest
    hook + operator custom). Built-in backends route through notice_spec so
    journal values never enter interpreter source on any host (PR-HIGH-003)."""
    override = os.environ.get("LOOP_JOURNAL_NOTICE_CMD")
    if override:
        cmd, env_extra = [override, NOTICE_TITLE, "%s: %s" % (runkey, summary)], {}
    else:
        cmd, env_extra = notice_spec(sys.platform, runkey, summary)
    env = None
    if env_extra:
        env = dict(os.environ)
        env.update(env_extra)
    try:
        r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=10, env=env)
        return r.returncode == 0
    except Exception:
        return False


def resolve_clock(flags):
    """Returns (ts, logged_ts_or_None). --event-ts stamps ts=<event> plus
    logged_ts=<now>; a backwards pair (event after now) refuses."""
    now = now_iso()
    ev = flags.get("--event-ts")
    if ev is None:
        return now, None
    evi = parse_iso(ev)
    if evi is None:
        refuse("--event-ts %r is not a valid local ISO-with-offset instant" % ev,
               "YYYY-MM-DDTHH:MM:SS+HH:MM (date -Iseconds)")
    nowi = parse_iso(now)
    if evi > nowi:
        refuse("--event-ts is in the future of the tool clock — a backwards ts/logged_ts pair is refused")
    return ev, now


LABEL_DIGEST_RE = re.compile(r"\A[0-9a-f]{64}\Z")  # \A..\Z (R28)


def parse_labels_map(value):
    """Mirror of the oracle's parse_labels_map (R47): a label-snapshot
    `labels=` value is `<phase identity>=<whole lowercase sha256>` entries
    joined by `;`; the LAST `=` separates the digest (rsplit). Returns
    (map, error list). An empty/blank value is the LEGAL recorded-empty
    shape -> ({}, []). PR-MED-001 (round 7): the helper validates this so it
    never emits an oracle-STRICT-failing label-snapshot."""
    label_map, errors = {}, []
    if value is None or not value.strip():
        return label_map, errors
    for entry in value.split(";"):
        entry = entry.strip()
        if not entry or "=" not in entry:
            errors.append("malformed entry %r (expected <phase identity>=<sha256>)" % entry[:60])
            continue
        ident, digest = entry.rsplit("=", 1)
        ident, digest = ident.strip(), digest.strip()
        if not ident:
            errors.append("entry with an empty phase identity")
            continue
        if not LABEL_DIGEST_RE.match(digest):
            errors.append("digest for %r is not a whole lowercase sha256" % ident[:60])
            continue
        if ident in label_map:
            errors.append("duplicate phase identity %r (ambiguous binding)" % ident[:60])
            continue
        label_map[ident] = digest
    return label_map, errors


def build_qualified_key(flags):
    """DR-3: the tool builds finding-route gate keys; composers never
    hand-compose. Requires --round (positive int) + --id (finding-ID grammar);
    --run is validated as a phase-scoped stage-<N> runkey upstream."""
    rnd = flags["--round"]
    fid = flags["--id"]
    if not rnd.isdigit() or int(rnd) < 1:
        refuse("--round must be a positive integer (got %r)" % rnd)
    if not FINDING_ID_RE.match(fid):
        refuse("--id %r does not match the finding-ID grammar" % fid,
               "(PR[n]-)?<REG|CRIT|HIGH|MED|LOW>-<nnn>")
    return "%s/r%s/%s" % (flags["--run"], rnd, fid)


def compute_mode(cls, severity):
    """STICKY section 7 TIERING, fully mechanical: immediate — HIGH routes,
    docs-only/invalid, every must-pause, config-conflict, cap-raise; queued —
    LOW/MED auto-routes only."""
    if cls in ENUMS["NOTIFY_IMMEDIATE_CLASSES"]:
        return "immediate"
    if cls == "auto-disposition" and severity == "high":
        return "immediate"
    return "queued"


def cmd_emit(flags, etype, kvs, sink):
    runkey = flags["--run"]
    role = flags["--role"]
    if etype is None:
        refuse("emit needs a TYPE", "emit <TYPE> [key=value ...]; TYPEs: %s"
               % ", ".join(sorted(EMIT_SPECS) + sorted("OWNERSHIP:" + s for s in V_OWNERSHIP_SUBTYPES - {"escape-check"}) + ["NOTIFY:<state>"]))
    # PR-MED-001 (round 8): --round/--id build finding-route keys and --repo
    # derives a commit hash — each is meaningful only on specific TYPEs; on any
    # other TYPE it would be silently ignored, so refuse.
    # PR-MED-002 (round 13): builder flags are accepted ONLY on the finding-route
    # gate/transition shapes (the finding-key owner set) — never on a non-gate
    # OWNERSHIP subtype (smoke-pass/config-change/…), which would otherwise BUILD
    # and serialize a qualified finding key= onto an unrelated record.
    if ("--round" in flags or "--id" in flags) and not (
            etype in ("OWNERSHIP:gate-disposition", "OWNERSHIP:auto-disposition",
                      "OWNERSHIP:must-pause")
            or etype.startswith("NOTIFY:")):
        refuse("--round/--id build finding-route keys and are only accepted on the finding-route shapes (OWNERSHIP:gate-disposition/auto-disposition/must-pause, NOTIFY:<state>), not %s" % etype)
    if "--repo" in flags and etype not in ("OWNERSHIP:commit", "OWNERSHIP:sticky-ack"):
        refuse("--repo is only accepted on emit OWNERSHIP:commit (hash= derivation) and emit OWNERSHIP:sticky-ack (sticky_hash= derivation), not %s" % etype)
    # R18 PR-LOW-001: `--epoch` is meaningful only on the emit shapes that
    # CARRY `epoch=` — the gate OWNERSHIP pairs (auto-disposition/must-pause,
    # whose paired NOTIFY carries it) and every NOTIFY:<state>. On any other
    # TYPE (simple journal types, non-pair OWNERSHIP subtypes incl.
    # gate-disposition/commit) it was silently DISCARDED — the round-8
    # total-argv contract ("an irrelevant flag REFUSES") applied to `--epoch`,
    # the last flag that leaked through. Type-specific, mirroring the
    # `--round`/`--id`/`--repo` refusals above.
    if "--epoch" in flags and not (
            etype in ("OWNERSHIP:auto-disposition", "OWNERSHIP:must-pause")
            or etype.startswith("NOTIFY:")):
        refuse("--epoch is only accepted where the emitted shape carries epoch= (the gate OWNERSHIP pairs OWNERSHIP:auto-disposition/must-pause, and NOTIFY:<state>), not %s — it would be silently discarded" % etype)

    # duplicate caller keys are lexical ambiguity (duplicate-key class)
    seen = set()
    for k, _v in kvs:
        if k in seen:
            refuse("duplicate key %s= — last-value-wins parsing would silently discard" % k)
        seen.add(k)
    kv = dict(kvs)

    for k, v in kvs:
        check_key_safety(k)  # PR-HIGH-001: the KEY reaches the line via fmt_kv, so validate it too
        if k in RESERVED_KEYS:
            refuse("%s= is tool-owned — the clock and run identity are never caller-supplied (use --event-ts / --run)" % k)
        check_value_safety(k, v, is_path=(k in ("roots", "latest", "log", "repo")))
        if v == "" and k != "labels":
            refuse("empty value for %s= — blank identity/evidence fails the empty-<key> floor (labels=\"\" is the one legal empty)" % k)

    # PR-MED-002 (round 7): --role is the SINGLE owner of record identity. A
    # caller role= token may not name a different actor than the required
    # --role — accept only a byte-equal token, refuse a conflict; absent, the
    # per-type stampers fill --role. (Sibling to the --round/--id-vs-key
    # conflict refusal.)
    if "role" in kv and kv["role"] != role:
        refuse("role=%s conflicts with the required --role %s — --role is the single identity owner (pass --role, or a byte-equal role= token)"
               % (kv["role"], role))

    ts, logged = resolve_clock(flags)
    lines = []
    token_lists = []  # R29: the INTENT (ordered token structure) parallel to `lines`

    # ---- OWNERSHIP family ----
    if etype.startswith("OWNERSHIP:"):
        st = etype[len("OWNERSHIP:"):]
        # PR-HIGH-001 (round 12): the severity the pair's TIERING consumes.
        # Defaults to the ID's own severity=; the auto-disposition validator
        # overrides it to the EFFECTIVE (executor-verified-else-severity) value.
        route_sev = kv.get("severity")
        if st == "escape-check":
            refuse("emit OWNERSHIP:escape-check is refused — digests are COMPUTED; use the escape-check subcommand (F-04 class)",
                   "escape-check --capture pre|post --leg <leg> --log-root <dir> --root name=/abs [--root ...]")
        if st == "run-close":
            refuse("emit OWNERSHIP:run-close is refused — cell/verdict are COMPUTED from disk state; use the run-close subcommand (a hand-authored close is a forged close — the F-04 class)",
                   "run-close --iso <iso-id> --base </abs/base> --outcome <outcome> [--plan </abs/plan.md>] [--attest owner-dead]")
        # PR-MED-001 (round 12), EXTENDED UNIFORM at R16 PR-HIGH-001 (operator-
        # disposed coherent extension): EVERY composer-owned OWNERSHIP subtype
        # requires --role composer before any notice or write — the SINGLE
        # gate owner (Round-11's commit-specific check is absorbed here).
        # Role-BEARING shapes keep their subject-role semantics: exit-census
        # carries the spawned role, and escape-check (refused via emit) is the
        # spawning session's — neither is gated. NOTE (the R12 retained
        # boundary, surfaced not closed): this gate is a MIS-ATTRIBUTION
        # guard, not caller authentication — --role is argv for every caller;
        # the authority boundary that makes composer-owned records unreachable
        # from a spawned role is the grant/process layer (the wrapper's
        # composer-only exact-path grant pattern), which stays the retained
        # R12 PR-MED-001 item.
        if st in COMPOSER_ONLY_SUBTYPES and role != "composer":
            refuse("OWNERSHIP:%s is a composer-owned record — it requires --role composer; a %s role can never certify one (dispositions/attestations are never delegated; the seat gate is a mis-attribution guard — caller AUTHORITY is the grant/process boundary, the retained R12 item)" % (st, role))
        if st not in V_OWNERSHIP_SUBTYPES:
            refuse("unknown OWNERSHIP subtype %r (invented vocabulary — the F-20/F-24 class)" % st,
                   "one of: %s" % ", ".join(sorted(V_OWNERSHIP_SUBTYPES)))
        if "sha" in kv:
            refuse("sha= is not a commit key — the required key is hash= and the tool derives it via --repo (F-23)")
        if "decision" in kv:
            refuse("decision= is not an admitted key — gate-disposition's required keys are key= + choice= (F-20)")
        # v32 TA.1 (round-8 in-session review): the retired label_check= key is
        # refused on EVERY OWNERSHIP subtype, not just the auto-disposition
        # route — a retired attestation must never ride forward as a stray
        # extra token either (recognize-in-historical-logs only).
        if "label_check" in kv:
            refuse("label_check= is retired at v32 on every OWNERSHIP shape — the successor attestation pair is authority_check=<config_hash> + authority_epoch=<N> (recognize historical records on replay, never emit forward)")

        # key= construction (DR-3) for finding routes
        key_from_builder = "--round" in flags and "--id" in flags
        if "--round" in flags or "--id" in flags:
            if not key_from_builder:
                refuse("--round and --id come together (the qualified-key builder needs both)")
            if "key" in kv:
                refuse("key= conflicts with --round/--id — the tool BUILDS finding-route keys (never hand-composed)")
            kv["key"] = build_qualified_key(flags)

        required = ("run",) + V_MATRIX.get(st, ())
        if st == "commit":
            required += ("hash", "seat")
            # PR-MED-001 (round 11): commit authority is COMPOSER-SEAT ONLY, so
            # the authoritative global --role must itself be composer — the tool
            # never converts a non-composer declared identity into a clean
            # `seat=composer` attestation (the Round-7 PR-MED-002 --role
            # single-owner rule applied to the commit audit surface).
            # (The composer-role gate is the uniform COMPOSER_ONLY_SUBTYPES
            # check above — single owner; commit rides it like every other
            # composer-owned subtype.)
            repo = flags.get("--repo")
            if "hash" in kv:
                refuse("hash= is DERIVED, never caller-typed — pass --repo <root> (F-23 closed by derivation)")
            if repo is None:
                refuse("emit OWNERSHIP:commit needs --repo <root> for hash= derivation")
            try:
                r = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"],
                                   capture_output=True, text=True, timeout=15)
            except Exception as e:
                envfail("git rev-parse failed under --repo %s: %s" % (repo, e))
            if r.returncode != 0:
                envfail("git rev-parse failed under --repo %s: %s" % (repo, r.stderr.strip()))
            kv["hash"] = r.stdout.strip()
            # PR-HIGH-004 sibling (round 7): a subprocess-derived value reaching
            # a journal line is Constraint-13-checked like any other.
            check_value_safety("hash", kv["hash"])
            kv.setdefault("seat", "composer")
            if kv["seat"] != "composer":
                refuse("seat=%s is a commit-authority violation — commits are composer-seat only; the tool never writes one" % kv["seat"])
        if st == "sticky-ack":
            # Round-4 S1 (DR4-1): the composer's run-start STICKY-read receipt.
            # sticky_hash= is COMPUTED, never caller-typed: the tool resolves
            # BOTH shipped STICKY mirrors under --repo, byte-compares them
            # (a mismatch REFUSES — the ack doubles as a free run-start
            # pair-discipline check), and hashes the compared bytes (sha256,
            # 12-hex prefix). Missing mirror files are an ENVIRONMENT failure
            # (exit 3, the git-absent precedent); a divergent pair is a
            # Constraint-5 violation the composer must fix (exit 2).
            required += ("sticky_hash",)
            kv.setdefault("role", role)
            # R6 (round-6 review): the receipt is CONTEMPORANEOUS by nature —
            # its ts= IS the read time (the idle-checkpoint precedent). A
            # backdated ack via --event-ts could forge the whole-file check's
            # cross-file strict ack.ts < spawn.ts fallback after the fact.
            if "--event-ts" in flags:
                refuse("OWNERSHIP:sticky-ack is a contemporaneous receipt — its ts= IS the read time; --event-ts/backfill is refused (a backdated ack could forge the cross-file ack-before-spawn fallback)")
            if "sticky_hash" in kv:
                refuse("sticky_hash= is DERIVED, never caller-typed — pass --repo <root>; the tool reads + byte-compares both STICKY mirrors and hashes the compared bytes (the F-23/F-04 derivation class)")
            repo = flags.get("--repo")
            if repo is None:
                refuse("emit OWNERSHIP:sticky-ack needs --repo <root> for sticky_hash= derivation (the shipped STICKY mirror pair lives under it)")
            import hashlib
            _mirror_rel = (os.path.join(".agents", "skills", "execute-loop", "STICKY.md"),
                           os.path.join(".claude", "skills", "execute-loop", "STICKY.md"))
            _mirror_bytes = []
            for _rel in _mirror_rel:
                _mp = os.path.join(repo, _rel)
                try:
                    with open(_mp, "rb") as _mf:
                        _mirror_bytes.append(_mf.read())
                except OSError as e:
                    envfail("cannot read STICKY mirror %s: %s" % (_mp, e))
            if _mirror_bytes[0] != _mirror_bytes[1]:
                refuse("the two STICKY mirrors under %s differ (byte-compare) — the ack is a run-start pair-discipline check; re-mirror before acknowledging (Constraint 5)" % repo)
            kv["sticky_hash"] = hashlib.sha256(_mirror_bytes[0]).hexdigest()[:12]
        if st == "exit-census":
            # DR-1 item 4 (admitted at R8): the wrapper's census record.
            kv.setdefault("role", role)
            if "children" in kv and not kv["children"].isdigit():
                refuse("exit-census children= must be a nonnegative integer (got %r)" % kv["children"])
            # R16 PR-MED-001: the ADMITTED capture-failure refusal shape — a
            # failed census emits `refused=capture-failure` and WAIVES
            # `children=` (a failed capture is never a fabricated clean zero;
            # the escape-check refusal-record precedent). Both keys together
            # would be contradictory evidence — refused.
            if kv.get("refused") is not None:
                if kv["refused"] != "capture-failure":
                    refuse("exit-census refused= admits only capture-failure")
                if "children" in kv:
                    refuse("exit-census refused=capture-failure and children= are mutually exclusive — a failed capture carries no confirmed count")
                required = tuple(k for k in required if k != "children")
        if st == "profile-switch" and kv.get("transferred") not in (None, "yes", "no"):
            refuse("profile-switch transferred= must be yes|no")
        if st == "label-snapshot":
            # v32 TA.1 (D1): the label snapshot is RETIRED forward — the
            # successor is OWNERSHIP:config-snapshot (the high-auto authority
            # attestation). Historical logs keep their records (the oracle
            # recognizes them); the helper never writes a new one.
            refuse("OWNERSHIP:label-snapshot is retired at v32 — the [gates: high-auto-ok] label grammar is gone; emit the successor attestation OWNERSHIP:config-snapshot (key=high-auto value=on|off; config_hash= derived)")
        if st == "config-snapshot":
            # v32 TA.1 (D1/PR-HIGH-013/015): the run-start high-auto authority
            # attestation — the label-snapshot successor, 1:1 on the policy-log
            # home, FIRST-wins, and fail-closed reads. key= is the closed
            # {high-auto} set this release; value= is the closed {on,off} set;
            # config_hash= is DERIVED (never caller-typed) over the canonical
            # serialization "iso=<iso>|plan=<plan>|epoch=<epoch>|high-auto=
            # <value>" (UTF-8, LF-normalized by construction — Constraint 13
            # refuses embedded line terminators — no trailing newline), so the
            # hash BINDS the isolation-run identity, authoritative plan, and
            # run-start epoch, not just the setting value. Contemporaneous
            # like sticky-ack: a backdated authority record could forge its
            # ordering against spawn boundaries, so --event-ts is refused.
            kv.setdefault("role", role)
            if "--event-ts" in flags:
                refuse("OWNERSHIP:config-snapshot is a contemporaneous authority record — its ts= IS the attestation time; --event-ts/backfill is refused")
            if kv.get("key") != "high-auto":
                refuse("OWNERSHIP:config-snapshot admits key=high-auto only (bad-config-key) — the run-level HIGH auto-route authorization is the sole attested key this release")
            if kv.get("value") not in ("on", "off"):
                refuse("OWNERSHIP:config-snapshot value= must be on|off (bad-config-value)")
            if "config_hash" in kv:
                refuse("config_hash= is DERIVED, never caller-typed — the tool computes it from iso/plan/epoch/value (the F-23/F-04 derivation class)")
            for _rk in ("iso", "plan", "epoch"):
                if not kv.get(_rk, "").strip():
                    refuse("OWNERSHIP:config-snapshot requires nonblank %s= — the hash binds the full identity (PR-HIGH-015)" % _rk)
            import hashlib
            kv["config_hash"] = hashlib.sha256(
                ("iso=%s|plan=%s|epoch=%s|high-auto=%s"
                 % (kv["iso"], kv["plan"], kv["epoch"], kv["value"]))
                .encode("utf-8")).hexdigest()[:12]
        if st == "config-revoke":
            # v32 TA.1 (PR-HIGH-006/016): the monotonic one-way revocation
            # record — the FIRST write of the pinned revoke-first disable
            # transaction; the authority boundary is effective at THIS append.
            # epoch= is the revocation counter (a positive integer from 1; the
            # snapshot is epoch 0); a duplicate/retry disable re-emits the same
            # epoch idempotently — monotonicity across records is the oracle's
            # scored-layer check (the stateless writer validates form).
            # Contemporaneous: --event-ts refused (a backdated boundary would
            # forge which dispositions it invalidates).
            kv.setdefault("role", role)
            if "--event-ts" in flags:
                refuse("OWNERSHIP:config-revoke is a contemporaneous authority boundary — its ts= IS the revocation time; --event-ts/backfill is refused")
            if kv.get("key") != "high-auto":
                refuse("OWNERSHIP:config-revoke admits key=high-auto only (bad-config-key)")
            _rep = kv.get("epoch", "")
            if _rep and (not _rep.isdigit() or int(_rep) < 1):
                refuse("OWNERSHIP:config-revoke epoch= must be a positive integer from 1 (bad-revoke-epoch) — the snapshot is epoch 0")
        if st in ("gate-disposition", "auto-disposition", "must-pause") and "key" in kv:
            # PR-REG-002 (round 8) + PR-MED-002 (round 13): builder ownership
            # (DR-3) applies to every OWNERSHIP finding-route owner — the two
            # pair subtypes AND gate-disposition. A finding-route key= (its last
            # segment parses to a finding-ID) must be built via --round/--id,
            # never hand-composed. Topology keys (no finding-ID: live-user-smoke,
            # config-conflict) stay unqualified and hand-supplied.
            _kseg = re.split(r"[^A-Za-z0-9-]+", kv["key"])[-1] or ""
            if FINDING_ID_RE.match(_kseg) and not key_from_builder:
                refuse("a finding-route key= must be built via --round/--id (DR-3 builder ownership), never hand-supplied — applies to OWNERSHIP:%s" % st)
        if st == "auto-disposition":
            # PR-HIGH-001 (round 7): ONE route-identity validator, resolved
            # BEFORE either pair member is assembled. A tool-emitted pair can
            # never encode a weaker route than the finding identity requires,
            # and the tool never emits an oracle-STRICT-failing ownership line.
            cap = kv.get("cap-raise")
            # v32 TA.3 (PR-MED-014): cap-accept=close is the explicit
            # accept-closure transition — the cap-raise topology rules
            # mirrored exactly (closed value; zero finding evidence; never
            # both cap keys on one record).
            capacc = kv.get("cap-accept")
            # v32 TA.1: label_check= is RETIRED forward with the label
            # grammar — refused for EVERY OWNERSHIP subtype by the shared
            # check above (round-8 review); the successor attestation pair is
            # authority_check= + authority_epoch=.
            key_sev = None
            key_is_finding = False
            if "key" in kv:
                m = FINDING_ID_RE.match(re.split(r"[^A-Za-z0-9-]+", kv["key"])[-1] or "")
                # `PR-REG-*` is a valid identity but carries no route
                # severity; verified severity remains the routing authority.
                key_is_finding = bool(m)
                key_sev = (m.group(2) or "").lower() or None if m else None
            # TB.2 (v32): finding evidence is EVERY finding-ID key, including
            # the identity-only `PR-REG-*` class — keyed off the severity
            # group alone, a REG key was invisible here, so it could ride a
            # cap topology record unrefused and (below) skip the
            # severity-required guard into a silent tiering-owner-unset queue.
            evidence = "severity" in kv or "verified" in kv or key_is_finding
            if cap is not None and capacc is not None:
                refuse("cap-raise= and cap-accept= are mutually exclusive — one record is ONE cap transition (mixed-route)")
            if cap is not None:
                if cap != "+1":
                    refuse("cap-raise= must be exactly +1 (bad-cap-raise)")
                if evidence:
                    refuse("cap-raise topology records carry ZERO finding evidence — no severity=/verified=/finding-ID key (mixed-route)")
            if capacc is not None:
                if capacc != "close":
                    refuse("cap-accept= must be exactly close (bad-cap-accept)")
                if evidence:
                    refuse("cap-accept topology records carry ZERO finding evidence — no severity=/verified=/finding-ID key (mixed-route)")
            # v32 TA.1: authority-attestation coherence when-present on any
            # route — authority_check= is the EXACT 12-hex config_hash echo
            # and travels WITH authority_epoch= (nonnegative revocation
            # count; 0 = no prior revocation).
            if "authority_check" in kv:
                if not re.match(r"\A[0-9a-f]{12}\Z", kv["authority_check"]):
                    refuse("authority_check= must be the exact 12-hex config_hash echo (bad-authority-check)")
                if "authority_epoch" not in kv:
                    refuse("authority_check= travels with authority_epoch= — the revocation-epoch binding is half the attestation (missing-authority-epoch, PR-HIGH-006)")
            if "authority_epoch" in kv:
                if not kv["authority_epoch"].isdigit():
                    refuse("authority_epoch= must be a nonnegative integer (bad-authority-epoch)")
                if "authority_check" not in kv:
                    refuse("authority_epoch= never rides without authority_check= (orphan-authority-epoch)")
            if "severity" in kv and kv["severity"] not in ENUMS["SEVERITIES"]:
                refuse("severity= must be one of %s" % ", ".join(sorted(ENUMS["SEVERITIES"])))
            if "verified" in kv:
                if kv["verified"] not in ENUMS["SEVERITIES"]:
                    refuse("verified= must be one of %s" % ", ".join(sorted(ENUMS["SEVERITIES"])))
                if "severity" not in kv:
                    refuse("verified= never rides without severity= — emit BOTH keys on a triage divergence (orphan-verified)")
            if cap is None and capacc is None:
                # builder ownership (DR-3) is enforced for BOTH pair subtypes by
                # the shared check above (PR-REG-002).
                # PR-HIGH-001 (round 9): a finding-route auto-disposition (a
                # finding-ID key) REQUIRES its own severity= (STICKY section 7).
                # The resolved severity is the SINGLE owner TIERING consumes, so
                # a HIGH route can never silently become mode=queued for lack of
                # an explicit severity=. Cap-raise topology is the documented
                # zero-severity exception (handled by the `cap is None` guard).
                # TB.2 (v32): the guard fires on ANY finding-ID key — for a
                # severity-classed ID severity= is the ID's own class; for an
                # identity-only ID (PR-REG-*) the unqualified key form is
                # accepted and severity= is the SOLE routing/TIERING owner.
                if key_is_finding and "severity" not in kv:
                    refuse("a finding-route auto-disposition requires severity= (the finding-ID's own class; for an identity-only PR-REG-* ID it is the sole routing authority — STICKY section 7) — without it the route's TIERING owner is unset and the route would silently queue")
                # severity= must AGREE with the finding-ID severity — the tool
                # refuses the mismatch rather than emitting an oracle
                # severity-key-mismatch line.
                if "severity" in kv and key_sev is not None and kv["severity"] != key_sev:
                    refuse("severity=%s disagrees with the finding-ID severity %s in key= — the tool never emits a mismatched route (severity-key-mismatch)"
                           % (kv["severity"], key_sev))
                resolved = kv.get("severity") or key_sev
                # PR-HIGH-001 (round 12): the executor-VERIFIED severity is the
                # ROUTING authority (STICKY section 7). The CRIT-pause and the
                # TIERING mode key on the EFFECTIVE severity (verified= when
                # present, else the ID's own severity=), so an executor upgrade
                # to CRIT pauses and an upgrade to HIGH is immediate — and a
                # downgrade routes to the lower tier. BOTH severity fields stay
                # recorded (severity= the ID's class + verified= the executor
                # class). Attestation (r9 PR-HIGH-018, one coherent rule): the
                # gate fires on resolved-OR-effective HIGH — an upgrade to
                # HIGH routes and attests as HIGH, and a HIGH->lower downgrade
                # STILL attests because the resolved class was HIGH (the log
                # cannot prove a downgrade legitimate). See the gate below.
                effective = kv.get("verified") or resolved
                route_sev = effective
                if effective == "crit":
                    refuse("a CRIT never auto-disposes — a verified/effective CRIT always pauses; route it as OWNERSHIP:must-pause (STICKY section 7)")
                # v32 TA.1 (r9 PR-HIGH-018): the attestation gate fires on
                # resolved-OR-effective HIGH — a verified-severity UPGRADE to
                # HIGH routes as HIGH and must attest like one (routing and
                # attestation share the effective value); the DOWNGRADE caveat
                # is unaffected: severity=high verified=low still requires the
                # pair via resolved==high (the log cannot prove a downgrade
                # legitimate). The successor pair replaces label_check=.
                if resolved == "high" or effective == "high":
                    if "authority_check" not in kv or "authority_epoch" not in kv:
                        refuse("a HIGH auto-route (resolved OR verified-effective HIGH) carries its authority_check=<config_hash> + authority_epoch=<N> attestation pair — bound to the run's OWNERSHIP:config-snapshot record (TA.1; r9 PR-HIGH-018 closed the verified-upgrade bypass)")
        for k in required:
            if k == "run":
                continue
            if k not in kv:
                refuse("OWNERSHIP:%s requires %s=" % (st, k),
                       "required keys: ts run " + " ".join(required[1:]))
            # PR-MED-001 (round 13): required identity/evidence values are
            # present AND nonblank (the simple/canonical types' floor applied to
            # the OWNERSHIP matrix + delta cells; the oracle keys empty-<key> on
            # exactly this). labels="" is not a matrix cell — its legal-empty
            # carve-out lives in the bespoke label-snapshot check.
            if not kv[k].strip():
                refuse("OWNERSHIP:%s %s= is present-but-blank (empty-%s floor) — a required identity/evidence value must be nonblank" % (st, k, k))

        # PR-MED-003 (round 12): a gate pair's epoch identity has ONE owner —
        # the required --epoch flag (consumed by the paired NOTIFY). A separate
        # epoch= kv token would ride the OWNERSHIP extras and split the two
        # members' epochs; refuse it (the pair analogue of the standalone
        # --epoch/epoch= conflict rule).
        if st in PAIR_SUBTYPES and "epoch" in kv:
            refuse("a gate pair's epoch has ONE owner — the required --epoch; a separate epoch= token is refused (it would split the OWNERSHIP/NOTIFY epochs)")
        # LOW-001 (round 5): class= belongs to the paired NOTIFY only — it
        # never rides the OWNERSHIP record.
        cls_arg = kv.pop("class", None) if st in PAIR_SUBTYPES else None

        parts = [st, fmt_kv("ts", ts)]
        if logged:
            parts.append(fmt_kv("logged_ts", logged))
        parts.append(fmt_kv("run", runkey))
        ordered = [k for k in required if k != "run" and k in kv]
        extras = [k for k, _ in kvs if k in kv and k not in ordered] + \
                 [k for k in kv if k not in ordered and k not in dict(kvs)]
        for k in ordered + [k for k in extras if k not in ordered]:
            parts.append(fmt_kv(k, kv[k]))
        lines.append("OWNERSHIP: " + " ".join(parts))
        token_lists.append(["OWNERSHIP:"] + parts)

        # ---- the atomic paired NOTIFY (gate routes) ----
        if st in PAIR_SUBTYPES:
            if "key" not in kv:
                refuse("a gate %s emission needs key= (or --round/--id) for its paired NOTIFY" % st)
            epoch = flags.get("--epoch")
            if epoch is None:
                refuse("a gate pair emission needs --epoch (epoch= rides every non-skipped NOTIFY)")
            check_value_safety("epoch", epoch)
            # PR-HIGH-001 (round 7): a must-pause ALWAYS binds class=must-pause
            # (hence immediate delivery) — a conflicting class= override that
            # would downgrade it to a queued notice is refused, never silently
            # honoured.
            if st == "must-pause":
                if cls_arg is not None and cls_arg != "must-pause":
                    refuse("OWNERSHIP:must-pause always routes class=must-pause (immediate) — a conflicting class=%s is refused" % cls_arg)
                cls = "must-pause"
            elif "cap-raise" in kv:
                # PR-HIGH-001 (round 10): a cap-raise route BINDS class=cap-raise
                # (hence immediate delivery + the mandatory desktop notice) —
                # the must-pause binding mirrored onto the cap path. A caller
                # class= is accepted only byte-equal; a conflicting value would
                # silently relabel the route to queued tiering.
                if cls_arg is not None and cls_arg != "cap-raise":
                    refuse("a cap-raise=+1 route always binds class=cap-raise (immediate) — a conflicting class=%s is refused (PR-HIGH-001 round 10)" % cls_arg)
                cls = "cap-raise"
            elif "cap-accept" in kv:
                # v32 TA.3 (PR-MED-014): the cap-raise binding mirrored — a
                # cap-accept=close route always binds class=cap-accept
                # (immediate delivery + the mandatory desktop notice).
                if cls_arg is not None and cls_arg != "cap-accept":
                    refuse("a cap-accept=close route always binds class=cap-accept (immediate) — a conflicting class=%s is refused (TA.3/PR-MED-014)" % cls_arg)
                cls = "cap-accept"
            else:
                cls = cls_arg or "auto-disposition"
                # PR-REG-002 (round 8) + PR-HIGH-001 (round 10): a NON-cap
                # auto-disposition route may carry ONLY its documented class
                # overrides — auto-disposition/docs-only/invalid (the
                # reclassification set). cap-raise now binds via its own branch
                # above, so class=cap-raise WITHOUT cap-raise= is a falsely
                # named route too; must-pause/config-conflict stay refused.
                if cls not in ("auto-disposition", "docs-only", "invalid"):
                    refuse("OWNERSHIP:auto-disposition may only route class in {auto-disposition, docs-only, invalid} (cap-raise binds via cap-raise=+1) — class=%s falsely names the route (PR-REG-002/PR-HIGH-001)" % cls)
            if cls not in ENUMS["NOTIFY_CLASSES"]:
                refuse("class= must be one of %s" % ", ".join(sorted(ENUMS["NOTIFY_CLASSES"])))
            if "mode" in kv:
                refuse("mode= is COMPUTED from class+severity (the TIERING table is mechanical) — never caller-supplied")
            mode = compute_mode(cls, route_sev)
            if mode == "immediate":
                summary = kv.get("detail") or kv.get("reason") or ("%s %s" % (st, kv["key"]))
                state = "sent" if fire_notice(runkey, summary) else "failed"
            else:
                state = "queued"
            # PR-MED-002 (round 11): under --event-ts the pair's OWNERSHIP member
            # carries ts=<event> logged_ts=<now>; the paired NOTIFY MUST carry the
            # same clock pair, else its effective write time (ts=<event>, past)
            # predates the first member's logged_ts and the whole-file monotonic
            # check flags the one-invocation pair. Both members share identical
            # ts=/logged_ts=/key= by construction.
            nparts = [state, fmt_kv("ts", ts)]
            if logged:
                nparts.append(fmt_kv("logged_ts", logged))
            nparts += [fmt_kv("run", runkey), fmt_kv("key", kv["key"]),
                       fmt_kv("epoch", epoch), fmt_kv("mode", mode), fmt_kv("class", cls)]
            lines.append("NOTIFY: " + " ".join(nparts))
            token_lists.append(["NOTIFY:"] + nparts)
        write_lines(sink, lines, token_lists=token_lists)
        return

    # ---- NOTIFY standalone ----
    if etype.startswith("NOTIFY:"):
        state = etype[len("NOTIFY:"):]
        if state not in ENUMS["NOTIFY_STATES"]:
            refuse("unknown NOTIFY state %r" % state,
                   "NOTIFY:<state>, state one of: %s" % ", ".join(sorted(ENUMS["NOTIFY_STATES"])))
        if "--round" in flags or "--id" in flags:
            if not ("--round" in flags and "--id" in flags):
                refuse("--round and --id come together")
            if "key" in kv:
                refuse("key= conflicts with --round/--id — the tool builds finding-route keys")
            kv["key"] = build_qualified_key(flags)
        if "key" not in kv:
            refuse("NOTIFY requires key= (gate identity)")
        cls = kv.get("class")
        if cls is not None and cls not in ENUMS["NOTIFY_CLASSES"]:
            refuse("class= must be one of %s" % ", ".join(sorted(ENUMS["NOTIFY_CLASSES"])))
        if state == "skipped":
            # PR-MED-002 (round 8): the skipped dedupe record's OPTIONAL fields
            # are still validated — the oracle validates mode=/class= on EVERY
            # NOTIFY, so an unvalidated skipped mode= would emit an
            # oracle-STRICT-failing line. Presence is optional; validity is not.
            # (The canonical minimal `NOTIFY: skipped ... key=` stays valid.)
            if "mode" in kv:
                if kv["mode"] not in ENUMS["NOTIFY_MODES"]:
                    refuse("mode= must be immediate|queued")
                if cls in ENUMS["NOTIFY_IMMEDIATE_CLASSES"] and kv["mode"] == "queued":
                    refuse("class=%s never rides mode=queued (bad-class-mode)" % cls)
            # R18 PR-LOW-001: NOTIFY:skipped's epoch= is OPTIONAL and was a
            # kv token only (the --epoch flag was discarded here). Map the flag
            # to epoch= with the same one-owner conflict rule as the non-skipped
            # branch, so --epoch is uniformly consumed across NOTIFY:* (never
            # silently dropped) while a no-epoch skipped record stays admitted.
            if "--epoch" in flags:
                if "epoch" in kv:
                    refuse("--epoch and an epoch= token conflict — supply exactly one (deterministic surface)")
                kv["epoch"] = flags["--epoch"]  # global --epoch nonblank-validated in main()
            # PR-REG-001 (round 11): a skipped record's OPTIONAL epoch= token is
            # still an activation identity — a present-but-blank/whitespace value
            # is serialized and the oracle classifies it `empty-epoch`. The
            # nonblank floor (Round 9) applies here too; no-epoch and valid
            # nonblank-epoch skipped records stay admitted.
            if "epoch" in kv and not kv["epoch"].strip():
                refuse("a skipped record's epoch= must be a nonblank activation id (empty-epoch)")
            # PR-MED-003 (round 12): batch= identity is reserved for flush-path
            # records (batch-flushed / queued failed|retried); a skipped record
            # never carries it (the Round-8 skipped-grammar's named batch-only row).
            if "batch" in kv:
                refuse("batch= is reserved for flush-path records — a skipped record never carries batch identity")
        if state != "skipped":
            if "--epoch" in flags and "epoch" in kv:
                refuse("--epoch and an epoch= token conflict — supply exactly one (deterministic surface)")
            epoch = flags.get("--epoch") or kv.get("epoch")
            if epoch is None:
                refuse("NOTIFY:%s requires epoch= (every non-skipped emission) — pass --epoch" % state)
            if not epoch.strip():
                # PR-MED-001 (round 9): the same nonblank floor for a kv epoch=
                # token (the general empty-value check catches "" but not
                # whitespace-only); an emitted non-skipped NOTIFY has a nonblank epoch.
                refuse("epoch must be a nonblank activation id (empty-epoch)")
            kv["epoch"] = epoch
            if cls is not None:
                if "mode" in kv:
                    refuse("mode= is COMPUTED when class= is present — never caller-supplied")
                kv["mode"] = compute_mode(cls, kv.get("severity"))
            elif "mode" not in kv:
                refuse("NOTIFY:%s needs mode= (or class=, from which mode is computed)" % state)
            if kv["mode"] not in ENUMS["NOTIFY_MODES"]:
                refuse("mode= must be immediate|queued")
            if kv["mode"] not in NOTIFY_MODE_BY_STATE[state]:
                refuse("mode=%s is illegal for state %s (D3 mode-state table)" % (kv["mode"], state))
            # PR-MED-002 (round 13): builder ownership on a standalone finding
            # NOTIFY — a finding-shaped key on a NEW standalone finding route
            # must be tool-built via --round/--id, never hand-composed. EXEMPT
            # are records that REFERENCE an existing gate or a flush batch (they
            # carry an already-built key by value): batch-flushed, any
            # batch-carrying record, and the delivery-owning immediate retry.
            _nkseg = re.split(r"[^A-Za-z0-9-]+", kv["key"])[-1] or ""
            if (FINDING_ID_RE.match(_nkseg)
                    and not ("--round" in flags and "--id" in flags)
                    and state != "batch-flushed" and "batch" not in kv
                    and kv["mode"] != "immediate"):
                refuse("a finding-route NOTIFY key= must be built via --round/--id (DR-3 builder ownership) — hand-composed finding keys are refused (topology keys, flush-derived batch transitions, and immediate-retry references stay exempt)")
            # PR-MED-003 (round 12+13): validate the COMPLETE class/batch grammar
            # BEFORE any delivery. The immediate-retry path below performs a
            # notice, so an invocation that will refuse (e.g. a forbidden batch=)
            # must refuse HERE — never after firing an unrecorded notice. batch=
            # is flush-path-only (batch-flushed / queued failed|retried); an
            # immediate transition (state=retried|failed, mode=immediate) is
            # never batch-legal, so a forbidden batch= is rejected pre-dispatch.
            if cls in ENUMS["NOTIFY_IMMEDIATE_CLASSES"] and kv["mode"] == "queued":
                refuse("class=%s never rides mode=queued (bad-class-mode)" % cls)
            _batch_legal = (state == "batch-flushed"
                            or (kv["mode"] == "queued" and state in ("failed", "retried")))
            if "batch" not in kv and _batch_legal:
                refuse("state=%s in mode=%s requires batch= (missing-batch)" % (state, kv["mode"]))
            if "batch" in kv and not _batch_legal:
                refuse("batch= is reserved for flush-path records (batch-flushed / queued failed|retried) — state=%s in mode=%s may not carry batch identity" % (state, kv["mode"]))
            if (kv["mode"] == "queued" and state in ("failed", "retried")
                    and kv.get("batch") is not None and kv.get("key") != kv.get("batch")):
                refuse("a queued-mode batch-level %s record keys ON the batch: key= == batch=" % state)
            # PR-HIGH-002 (round 7) + PR-REG-001 (round 8): a standalone
            # immediate NOTIFY cannot ASSERT a delivery it did not perform.
            # First-delivery (`sent`) is the OWNERSHIP+NOTIFY pair's job (it
            # fires + derives sent/failed); the ONE delivery-owning standalone
            # immediate transition is `retried` — the truthful recovery of a
            # prior FAILED immediate delivery. It PERFORMS the notice here and
            # DERIVES the outcome (retried on success, failed on failure) under
            # the <=1-retry-per-key-per-epoch cap read from the append-only log.
            if kv["mode"] == "immediate":
                if state != "retried":
                    refuse("a standalone immediate NOTIFY:%s cannot assert delivery it did not perform — immediate first-delivery is emitted by the OWNERSHIP+NOTIFY pair (fires + derives) or by flush (PR-HIGH-002)" % state)
                if "--log" not in flags:
                    refuse("an immediate NOTIFY:retried is delivery-owning and needs --log to enforce the per-key/epoch cap against the append-only record")
                has_failed, already_attempted = immediate_retry_state(
                    flags["--log"], runkey, kv["key"], kv["epoch"])
                if not has_failed:
                    refuse("no unrecovered failed immediate delivery for key=%s — nothing to retry (PR-REG-001)"
                           % kv["key"])
                if already_attempted:
                    refuse("an immediate retry was already attempted for key=%s in epoch %s — <=1 attempt per (run,key,epoch); a new activation epoch permits exactly one more"
                           % (kv["key"], kv["epoch"]))
                summary = kv.get("detail") or kv.get("reason") or ("retry %s" % kv["key"])
                state = "retried" if fire_notice(runkey, summary) else "failed"
        parts = [state, fmt_kv("ts", ts)]
        if logged:
            parts.append(fmt_kv("logged_ts", logged))
        parts.append(fmt_kv("run", runkey))
        for k in ("key", "epoch", "mode", "class", "batch"):
            if k in kv:
                parts.append(fmt_kv(k, kv[k]))
        for k, _ in kvs:
            if k in kv and k not in ("key", "epoch", "mode", "class", "batch"):
                parts.append(fmt_kv(k, kv[k]))
        write_lines(sink, ["NOTIFY: " + " ".join(parts)],
                    token_lists=[["NOTIFY:"] + parts])
        return

    # ---- simple + canonical types ----
    spec = EMIT_SPECS.get(etype)
    if spec is None:
        refuse("unknown emit TYPE %r (invented line-start types are the F-03 class)" % etype,
               "one of: %s, NOTIFY:<state>, OWNERSHIP:<subtype>" % ", ".join(sorted(EMIT_SPECS)))

    if etype == "CONSUME":
        if kv.get("source") == "idle-reentry":
            refuse("emit CONSUME source=idle-reentry is refused — the checkpoint/suppression shapes are idle-check's alone (a hand-supplied gap_min= cannot bypass the computation)")
        if "wake" in kv:
            refuse("wake= is RETIRED — the source key is source= (wake-key-legacy)")
    if etype in ("CONSUME", "CLASSIFY") and kv.get("result") == "live":
        refuse("the liveness token is `liveness`, never `live` (live-token-drift)")
    if etype == "CLASSIFY" and "ids" in kv:
        ids = [t for t in kv["ids"].split(",") if t]
        pend = kv.get("pending")
        if pend is None or not pend.isdigit() or int(pend) != len(ids):
            refuse("ids= requires pending= equal to the ids count (got pending=%r, %d ids)" % (pend, len(ids)))
        if len(set(ids)) != len(ids):
            refuse("ids= members must be unique (duplicate-pending-id)")
    if etype == "VERIFY_OK":
        if not kv.get("children", "").isdigit():
            refuse("emit VERIFY_OK requires children=<nonnegative integer> — the role's OWN declared count (r2-B2)")
    if etype == "IDENTITY" and "session" not in kv:
        refuse("IDENTITY: update REQUIRES session= — with no session id known, write no record (F-01 closed by refusal)")
    if etype == "MONITOR":
        if "detail" in kv and len(kv["detail"]) > 160:
            refuse("MONITOR detail= is a quoted summary <=160 chars, never pasted log content (STICKY section 3)")
    if etype == "ROLE:start":
        if "profile_dir" in kv:
            refuse("profile_dir lives in Loop config:, never as a start key (STICKY:51; observed F-07 adjunct)")
        if "profile" in kv and kv.get("backend") != "claude-p":
            refuse("profile= is admitted only on backend=claude-p (profile-on-non-claude-p)")
    if etype == "WATCH:armed":
        if kv.get("layer2") == "none" and "reason" not in kv:
            refuse("layer2=none requires reason= naming the real arm failure / resolved no-monitor case (none-without-reason)")
        if kv.get("layer2") == "none" and "delivery" in kv:
            refuse("a layer2=none armed line never carries delivery= — nothing to consume (the oracle's delivery-on-none class; v32.2)")

    kv.setdefault("role", role) if "role" in spec["required"] else None
    for k in spec["required"]:
        if k not in kv:
            refuse("%s requires %s=" % (etype, k),
                   "required keys: ts run " + " ".join(spec["required"]))
        if kv[k] == "" or not kv[k].strip():
            refuse("%s %s= is present-but-blank (empty-%s floor)" % (etype, k, k))
    for k, enum_name in spec["enums"].items():
        if k in kv and kv[k] not in ENUMS[enum_name]:
            refuse("%s %s= must be one of %s (got %r)"
                   % (etype, k, ", ".join(sorted(ENUMS[enum_name])), kv[k]))

    parts = []
    if spec["verb"]:
        parts.append(spec["verb"])
    parts.append(fmt_kv("ts", ts))
    if logged:
        parts.append(fmt_kv("logged_ts", logged))
    parts.append(fmt_kv("run", runkey))
    ordered = [k for k in spec["required"] if k in kv]
    listed = set(ordered)
    for k in ordered:
        parts.append(fmt_kv(k, kv[k]))
    for k, _ in kvs:
        if k in kv and k not in listed and k not in RESERVED_KEYS:
            parts.append(fmt_kv(k, kv[k]))
            listed.add(k)
    # R29: thread the INTENT — the prefix's bare tokens + each fmt_kv'd part is the
    # ordered token structure the emitter built; the chokepoint compares parsed==this.
    write_lines(sink, [spec["prefix"] + " " + " ".join(parts)],
                token_lists=[spec["prefix"].split() + parts])


def parse_kv(text):
    """Tokenize key=value pairs exactly as the oracle does (double-quoted
    values may hold spaces). Returns (dict, list of bare tokens in order)."""
    kv, bare = {}, []
    for m in PARSE_KV_RE.finditer(text):
        if m.group(1) is not None:
            kv[m.group(1)] = m.group(2)
        elif m.group(3) is not None:
            kv[m.group(3)] = m.group(4)
        else:
            bare.append(m.group(5))
    return kv, bare


ROOT_NAME_RE = re.compile(r"\A[a-z0-9-]+\Z")  # \A..\Z (R28)
LEG_RE = re.compile(r"\A[A-Za-z0-9._-]+\Z")  # rides a state-file name — filename-safe; \A..\Z (R28)


def status_digest(root):
    """The PINNED digest convention (DR-1 item 3, F-04's fix): sha256 hex over
    the root's `git status --short` output with the trailing newline stripped.
    Returns (digest, None) or (None, error-string) — NEVER an empty-string
    digest on failure."""
    import hashlib
    try:
        r = subprocess.run(["git", "-C", root, "status", "--short"],
                           capture_output=True, text=True, timeout=60)
    except Exception as e:
        return None, "git status failed under %s: %s" % (root, e)
    if r.returncode != 0:
        return None, "git status failed under %s: %s" % (root, r.stderr.strip()[:200])
    return hashlib.sha256(r.stdout.rstrip("\n").encode("utf-8")).hexdigest(), None


def parse_root_args(roots):
    """--root name=/abs/path, repeatable. Names lowercase [a-z0-9-]+, UNIQUE;
    base REQUIRED and FIRST; paths absolute; delimiter/control rejection per
    Constraint 13. Returns ordered [(name, path)]."""
    if not roots:
        refuse("escape-check needs at least one --root", "--root base=/abs/path [--root name=/abs/path ...]")
    out = []
    seen = set()
    for spec in roots:
        if "=" not in spec:
            refuse("--root %r is not name=/abs/path" % spec)
        name, path = spec.split("=", 1)
        if not ROOT_NAME_RE.match(name):
            refuse("root name %r must be lowercase [a-z0-9-]+" % name)
        if name in seen:
            refuse("duplicate root name %r" % name)
        seen.add(name)
        check_value_safety("root", path, is_path=True)
        if not os.path.isabs(path):
            refuse("root path %r must be absolute (require_abs)" % path)
        out.append((name, path))
    if out[0][0] != "base":
        refuse("the first root must be base= (the LOOP_ESCAPE_ROOTS grammar: base REQUIRED and FIRST)")
    return out


def cmd_escape_check(flags, roots, sink):
    """The helper twin of DR-1 item 3 for NON-wrapper headless activations
    (codex peers, inline fallbacks). Pre-capture state lives OUTSIDE the
    probe-log grammar — a state file under the log root (codex r1-P2: a
    partial emitted line would parse as a FINAL escape-check record); the post
    leg reads it and emits EXACTLY ONE complete record. Pre failure: exit 2,
    nothing written. Post failure is TWO distinct exits (PR-MED-001): a
    git-status CAPTURE failure emits the refusal record naming the root
    (`refused=capture-failure root=<name>` — R8 admits it) and exits 3 (record
    WRITTEN); a `refuse()` — missing/malformed pre-state, or a post root
    set/order that differs from pre — writes ONLY a stderr diagnostic and exits
    2 (NO probe-log record). The wrapper folds either to non-success and words
    its warning per this exit code; a record is never an empty-string digest."""
    capture = flags.get("--capture")
    if capture not in ("pre", "post"):
        refuse("escape-check needs --capture pre|post")
    leg = flags.get("--leg")
    if leg is None:
        refuse("escape-check needs --leg <leg> (binds the record to its activation)")
    if not LEG_RE.match(leg):
        refuse("--leg %r must be filename-safe [A-Za-z0-9._-]+ (it names the pre-state file)" % leg)
    log_root = flags["--log-root"]
    if not os.path.isdir(log_root):
        envfail("--log-root %s is not a directory" % log_root)
    pairs = parse_root_args(roots)
    state_path = os.path.join(log_root, "%s-escape-%s.pre" % (flags["--run"], leg))

    if capture == "pre":
        lines = []
        for name, path in pairs:
            digest, err = status_digest(path)
            if err:
                refuse("pre-capture FAILED for root %s — refusing (exit 2, no spawn, nothing written): %s"
                       % (name, err))
            lines.append("%s|%s|%s" % (name, path, digest))
        # PR-HIGH-001 (round 8): the pre-state is created EXACTLY ONCE and is
        # IMMUTABLE until --capture post consumes it. A second --capture pre for
        # the same (run,leg) is refused so it can never silently re-baseline and
        # mask a post-baseline mutation (the true pre-spawn baseline is the one
        # the clean/dirty verdict proves against). Exclusive create (O_EXCL)
        # closes the concurrent-same-leg race; a FAILED write is cleaned up so a
        # legitimate retry after a failed pre still works.
        payload = ("\n".join(lines) + "\n").encode("utf-8")
        try:
            fd = os.open(state_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            refuse("pre-state %s already exists — a second --capture pre for the same (run,leg) is refused; the baseline is immutable until --capture post consumes it"
                   % state_path)
        except OSError as e:
            envfail("cannot create pre-state file %s: %s" % (state_path, e))
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
        except OSError as e:
            try:
                os.unlink(state_path)  # a failed write leaves no state -> retry stays possible
            except OSError:
                pass
            envfail("cannot write pre-state file %s: %s" % (state_path, e))
        return

    # post
    if not os.path.exists(state_path):
        refuse("no pre-state file %s — the pre leg must run first (one record per pre/post pair)" % state_path)
    # PR-HIGH-001 (round 8): parse the saved state FAIL-CLOSED before formatting
    # any record — exact field count, unique root names, validated absolute
    # paths, whole lowercase digests, and value safety (the filesystem-derived
    # Constraint-13 sibling Round-7 PR-HIGH-004 required auditing on this path).
    pre = {}
    order = []
    for raw in open(state_path, encoding="utf-8"):
        raw = raw.rstrip("\n")
        if not raw:
            continue
        parts = raw.split("|")
        if len(parts) != 3:
            refuse("malformed pre-state line (expected name|path|digest): %r" % raw[:80])
        name, path, digest = parts
        if not ROOT_NAME_RE.match(name):
            refuse("pre-state root name %r is not lowercase [a-z0-9-]+" % name[:40])
        if name in pre:
            refuse("duplicate root name %r in pre-state (ambiguous baseline)" % name)
        if not os.path.isabs(path):
            refuse("pre-state root path %r is not absolute" % path[:80])
        check_value_safety("root", path, is_path=True)
        if not DIGEST_RE.match(digest):
            refuse("pre-state digest for root %s is not an 8-64 char lowercase hex digest" % name)
        pre[name] = (path, digest)
        order.append(name)
    if not order:
        refuse("pre-state file %s is empty — no baseline to prove against" % state_path)
    if [n for n, _ in pairs] != order or any(pre[n][0] != p for n, p in pairs):
        refuse("post root set/order differs from the pre capture (%s) — the root set never shrinks or reorders mid-run"
               % ", ".join(order))
    ts = now_iso()
    manifest = []
    for name, path in pairs:
        after, err = status_digest(path)
        if err:
            # PR-HIGH-004 (round 7): NEVER copy subprocess/filesystem
            # diagnostics into a journal value — a multiline git stderr would
            # forge a second physical line (Constraint 13). The refusal record
            # names ONLY the validated root (ROOT_NAME_RE) + validated leg and
            # carries a FIXED safe detail; the diagnostic goes to stderr. The
            # record names the root — never an empty-string digest.
            sys.stderr.write("ENVFAIL: post-capture git status failed for root %s: %s\n"
                             % (name, err))
            rec = ("OWNERSHIP: escape-check ts=%s run=%s role=%s leg=%s refused=capture-failure root=%s detail=\"post-capture git status failed; diagnostic on stderr\""
                   % (ts, flags["--run"], flags["--role"], leg, name))
            write_lines(sink, [rec])
            sys.exit(3)
        manifest.append((name, path, pre[name][1], after))
    all_eq = all(b == a for _n, _p, b, a in manifest)
    result = "clean" if all_eq else "dirty"
    roots_val = "; ".join("%s=%s|%s|%s" % m for m in manifest)
    base = manifest[0]
    rec = ("OWNERSHIP: escape-check ts=%s run=%s role=%s result=%s before=%s after=%s roots=\"%s\" leg=%s"
           % (ts, flags["--run"], flags["--role"], result, base[2], base[3], roots_val, leg))
    write_lines(sink, [rec])
    try:
        os.remove(state_path)  # consumed — exactly one record per pre/post pair
    except OSError:
        pass


def immediate_retry_state(log_path, expected_run, key, epoch):
    """PR-REG-001 (round 8, hardened round 9): the immediate-retry cap +
    run-binding, mirroring derive_pending. Returns (has_failed,
    already_attempted): whether a prior `failed mode=immediate` delivery for
    `key` is currently UNRECOVERED (nothing to retry otherwise), and whether a
    retry has already been ATTEMPTED in THIS epoch (success OR failure consumes
    the per-(run,key,epoch) budget — the round-8 gap where a failed retry never
    consumed the cap). A NOTIFY record from another run, or a qualified key
    prefix from another run, fails CLOSED (the round-8 immediate path never
    checked run= — a cross-run retry delivered another run's gate)."""
    if "/" in key and key.split("/", 1)[0] != expected_run:
        refuse("immediate retry key=%s belongs to run %s, not %s (cross-run delivery)"
               % (key, key.split("/", 1)[0], expected_run))
    unrecovered = False            # a failed immediate delivery awaits recovery
    attempts_by_epoch = {}         # epoch -> retry ATTEMPTS on the unrecovered delivery
    try:
        lines = open(log_path, encoding="utf-8").read().splitlines()
    except OSError as e:
        envfail("cannot read --log %s: %s" % (log_path, e))
    for raw in lines:
        if not raw.startswith("NOTIFY:"):
            continue
        kv, bare = parse_kv(raw[len("NOTIFY:"):])
        st = bare[0] if bare else None
        # PR-REG-001 (round 10): run ownership is TOTAL — a NOTIFY record with a
        # MISSING run= (the oracle's missing-run) is not owned by any run and
        # must not participate in delivery derivation. Missing AND foreign both
        # fail closed before any notice/append.
        rec_run = kv.get("run")
        if rec_run != expected_run:
            refuse("immediate retry --run %s found a NOTIFY record whose run=%r is not this run — a retry only acts on delivery state owned by its own run (missing/foreign run fails closed)"
                   % (expected_run, rec_run))
        if kv.get("key") != key or kv.get("mode") != "immediate":
            continue
        ep = kv.get("epoch", "")
        if st == "failed":
            if not unrecovered:
                unrecovered = True  # a fresh INITIAL immediate-delivery failure
            else:
                attempts_by_epoch[ep] = attempts_by_epoch.get(ep, 0) + 1  # a failed retry attempt
        elif st == "retried":
            attempts_by_epoch[ep] = attempts_by_epoch.get(ep, 0) + 1       # a retry attempt
            unrecovered = False     # a successful retry recovers the delivery
        elif st == "sent":
            unrecovered = False
    return unrecovered, attempts_by_epoch.get(epoch, 0) >= 1


def derive_pending(log_path, expected_run):
    """The RESUME-from-records derivation (implemented HERE ONCE; STICKY's
    RESUME duty points at `flush --dry-run`): a member is pending iff its
    NEWEST queued record has no LATER batch-flushed record for the same key
    (MED-001, round 5 — last-state-wins in append order; a re-fire in a new
    epoch legally re-queues a member flushed earlier). Returns
    (pending, is_retry, retry_attempts_by_epoch). PR-MED-003 (round 7): retry
    state is MEMBER-LEVEL and unresolved-only — is_retry is true iff a CURRENTLY
    pending member experienced a failed flush while queued and has not been
    batch-flushed since. PR-MED-003 (round 8): the retry BUDGET is per-epoch
    ATTEMPT accounting on the current unresolved batch — the FIRST batch-level
    queued failed/retried in a run is the initial flush; each LATER one is a
    retry attempt (success OR failure consumes the budget); a batch-flushed
    resolves the run; unrelated immediate transitions (mode != queued) never
    count. This both stops unlimited failed retries and stops unrelated
    retries from over-blocking."""
    last_state = {}    # key -> ("queued"|"flushed", epoch)
    saw_failed = {}    # key -> bool: a failed flush occurred while this member was queued
    order = []         # first-appearance order of keys
    retry_attempts_by_epoch = {}   # epoch -> retry ATTEMPTS on the current unresolved batch
    seen_initial = False           # the run's initial flush failure has been seen
    try:
        lines = open(log_path, encoding="utf-8").read().splitlines()
    except OSError as e:
        envfail("cannot read --log %s: %s" % (log_path, e))
    for raw in lines:
        if not raw.startswith("NOTIFY:"):
            continue
        kv, bare = parse_kv(raw[len("NOTIFY:"):])
        state = bare[0] if bare else None
        key = kv.get("key")
        # PR-MED-004 (round 8): a flush only owns queue state for its own --run.
        # A NOTIFY record from another run in the log fails CLOSED (a
        # caller-selected wrong/mixed log is an error, never a silent filter),
        # and a qualified finding-member key embeds the run identity, so its
        # prefix must match too. Topology keys (no `/`) bind via the record's
        # run= alone. PR-REG-001 (round 10): the ownership check is TOTAL — a
        # MISSING run= (the oracle's missing-run) is owned by no run and fails
        # closed too, so no run-less record participates in flush derivation.
        rec_run = kv.get("run")
        if rec_run != expected_run:
            refuse("flush --run %s found a NOTIFY record whose run=%r is not this run — a flush only delivers/records queue state owned by its own run (missing/foreign run fails closed; point --log at the right run's log)"
                   % (expected_run, rec_run))
        if key and "/" in key and key.split("/", 1)[0] != expected_run:
            refuse("a queued finding member key=%s belongs to run %s, not %s (cross-run delivery)"
                   % (key, key.split("/", 1)[0], expected_run))
        batch_level = (key is not None and key == kv.get("batch")
                       and kv.get("mode") == "queued")
        if state == "queued" and key:
            if key not in last_state:
                order.append(key)
            last_state[key] = ("queued", kv.get("epoch", ""))
            saw_failed[key] = False  # a fresh queue clears prior failure history
        elif state == "batch-flushed" and key:
            if key not in last_state:
                order.append(key)
            last_state[key] = ("flushed", kv.get("epoch", ""))
            seen_initial = False  # the unresolved run is resolved
        elif state == "failed" and key and kv.get("batch") == key:
            # a batch-level flush failure hits every member pending at the time
            for m, (st, _ep) in last_state.items():
                if st == "queued":
                    saw_failed[m] = True
        if batch_level and state in ("failed", "retried"):
            if not seen_initial:
                seen_initial = True  # the initial flush of this unresolved run
            else:
                ep = kv.get("epoch", "")
                retry_attempts_by_epoch[ep] = retry_attempts_by_epoch.get(ep, 0) + 1
    pending = [(k, last_state[k][1]) for k in order if last_state[k][0] == "queued"]
    is_retry = any(saw_failed.get(k) for k, _ in pending)
    return pending, is_retry, retry_attempts_by_epoch


def cmd_flush(flags, dry_run, sink):
    """Phase-boundary + Termination-stop flush: derives queued-not-flushed
    members from the probe log by qualified key=, emits per-member
    `NOTIFY: batch-flushed` on ONE fresh batch= key + the single per-OS
    desktop notice, honors the failed/retried epoch rules. Empty queue =
    exit 0 noop (non-vacuousness is the BAR's leg via R14's seeded members,
    never this tool's). --dry-run is the SOLE read-only surface."""
    # R16 PR-HIGH-001 (uniform seat gate): flushing durable notices is a
    # composer-owned transition — the same coherence gate as the composer-only
    # OWNERSHIP subtypes (a mis-attribution guard, not authentication). Only
    # the WRITE path is gated: --dry-run writes nothing and stays open to any
    # role for RESUME reconstruction.
    if not dry_run and flags["--role"] != "composer":
        refuse("flush is a composer-owned transition — it requires --role composer (a %s role can never flush durable notices); flush --dry-run stays read-open for RESUME derivation" % flags["--role"])
    log_path = flags["--log"]
    pending, is_retry, retry_attempts_by_epoch = derive_pending(log_path, flags["--run"])
    if dry_run:
        sys.stdout.write("flush-dry-run: pending=%d\n" % len(pending))
        for key, epoch in pending:
            sys.stdout.write("pending-member key=%s queued_epoch=%s\n" % (key, epoch))
        return
    if not pending:
        return  # exit-0 noop — a zero-member flush is legal at a boundary with nothing pending
    epoch = flags.get("--epoch")
    if epoch is None:
        refuse("flush with pending members needs --epoch (epoch= rides every non-skipped NOTIFY)")
    check_value_safety("epoch", epoch)
    # PR-MED-003 (round 8): the retry BUDGET is a per-epoch ATTEMPT count on the
    # current unresolved batch — a prior retry attempt (success OR failure) in
    # this epoch consumes it; unrelated (immediate) transitions never do.
    if is_retry and retry_attempts_by_epoch.get(epoch, 0) >= 1:
        refuse("a retry was already attempted in epoch %s — <=1 retry attempt per epoch on the unresolved batch; a NEW activation epoch permits exactly one more" % epoch)
    ts = now_iso()
    batch = "%s-flush-%s" % (flags["--run"], ts.replace(":", "").replace("-", "").replace("+", "p"))
    # PR-MED-002 (round 12): every computed flush field goes through the same
    # canonical fmt_kv() the emit paths use — a valid opaque epoch/key with
    # spaces would otherwise be interpolated unquoted and split into two tokens
    # (a non-STRICT flush record). Record-derived member keys are additionally
    # value-safety-checked before they reach a new line/notice.
    def flush_line(state, key):
        return "NOTIFY: " + " ".join([state, fmt_kv("ts", ts), fmt_kv("run", flags["--run"]),
                                      fmt_kv("key", key), fmt_kv("epoch", epoch),
                                      fmt_kv("mode", "queued"), fmt_kv("batch", batch)])
    for key, _qep in pending:
        check_value_safety("key", key)
    summary = "flushing %d queued notice(s): %s" % (len(pending), ", ".join(k for k, _ in pending))
    if not fire_notice(flags["--run"], summary):
        # a failed flush leaves members queued: ONE failed record on the batch key
        write_lines(sink, [flush_line("failed", batch)])
        return
    lines = []
    if is_retry:
        lines.append(flush_line("retried", batch))
    for key, _qep in pending:
        lines.append(flush_line("batch-flushed", key))
    write_lines(sink, lines)


FUTURE_SKEW_HOURS = 24  # the oracle's K9 bound, mirrored


def future_instant(t):
    if t is None:
        return False
    return t > datetime.datetime.now().astimezone() + datetime.timedelta(hours=FUTURE_SKEW_HOURS)


def composer_write_time(line):
    """Effective composer-WRITE time of a probe-log line — MIRRORS the
    oracle's _composer_write_time (K7: VALID logged_ts= else VALID ts=; K9:
    an impossible-future stamp is invalid for the clock; the idle checkpoint
    never carries its own logged_ts=). None for excluded writers/unparseable
    stamps."""
    if not line.startswith(COMPOSER_WRITE_PREFIXES):
        return None
    kv, _ = parse_kv(line)
    if line.startswith("CONSUME:") and kv.get("source") == "idle-reentry":
        t = parse_iso(kv.get("ts"))
        return None if future_instant(t) else t
    t = parse_iso(kv.get("logged_ts"))
    if t is None or future_instant(t):
        t = parse_iso(kv.get("ts"))
    if t is not None and future_instant(t):
        return None
    return t


def _idle_delivery_echo(lines, run):
    """v32.3 T2.3 — the fg/bg salience echo: stdout NARRATION ONLY, never a
    record (no journal append, no new refusal, no exit-status change). Selects
    the newest `Wake:` line by APPEND ORDER whose run= matches this run — the
    echo's OWN eligibility scan, separate from the composer-clock scan above
    (whose refusal semantics stay byte-untouched; canonical Wake: lines are
    clock-less and never reach that scan's ownership check). Foreign-run or
    missing-run Wake: lines are silently INELIGIBLE here, never refused;
    duplicate run=/delivery= keys resolve by parse_kv's existing semantics
    (last occurrence wins). The selected line's delivery= must validate
    against the canonical resolved enum (V_base DELIVERY_ENUM — reused, never
    redefined). No eligible Wake:, or an eligible newest Wake: with no
    delivery= key, is silent-legal (pre-v32.2 logs, layer2=none resolutions —
    omission never inherits from an older delivery-bearing line). An INVALID
    present value suppresses the echo with ONE escaped-and-bounded stderr
    diagnostic (r1 PR-MED-004: the echo can never advertise an unresolved or
    out-of-domain value, and never replays control bytes to a terminal).
    Evaluated INDEPENDENTLY of idle due-ness so it fires on ordinary
    short-gap wakes — the composer receives the fg duty from tool output even
    when compaction has dropped it from context."""
    chosen = None
    for raw in lines:
        if not raw.startswith("Wake:"):
            continue
        kv, _ = parse_kv(raw)
        if kv.get("run") != run:
            continue
        chosen = kv
    if chosen is None or "delivery" not in chosen:
        return
    delivery = chosen["delivery"]
    if delivery not in ENUMS["DELIVERY_ENUM"]:
        rendered = ascii(delivery)
        if len(rendered) > 40:
            rendered = rendered[:40] + "...(bounded)"
        sys.stderr.write(
            "idle-check: delivery echo suppressed — the newest same-run Wake: "
            "line carries delivery=%s, outside the resolved enum fg|bg "
            "(records, journal bytes, and exit status unchanged)\n" % rendered)
        return
    if delivery == "fg":
        sys.stdout.write("idle-check: resolved delivery=fg — consume the Layer-2 watch foreground (chunked ≤2min polls)\n")
    else:
        sys.stdout.write("idle-check: resolved delivery=bg — background return delivery; consume returns on wake\n")


def cmd_idle_check(flags, sink):
    """DR-4 (D8's dual fix, F-08 + F-21 as ONE change), run UNCONDITIONALLY on
    every wake: the tool computes the gap AND decides due-ness. Gap = now
    minus the newest composer-authored probe-line write (the oracle's
    COMPOSER_WRITE_PREFIXES clock domain), floored whole minutes. At a
    qualifying gap (>= IDLE_GAP_MIN):
      - run-owned artifact activity under --log-root IN the window (mtime
        evidence at check time; the probe log itself is excluded — it is the
        clock's own substrate) -> the PINNED suppression record
        (self-documenting: the oracle can never see mtimes at census time);
      - genuinely idle -> the checkpoint record (open-role reconciliation
        stays the composer's judgment duty, per the STICKY).
    No composer line in the log, or gap below threshold -> no record (exit 0).
    Independent of due-ness, the delivery echo (_idle_delivery_echo, v32.3
    T2.3) may print ONE informational stdout line from the newest eligible
    same-run Wake: — after the ownership scan (a refusal precedes any echo),
    before the due-ness early returns, journal bytes untouched."""
    log_path = flags["--log"]
    log_root = flags["--log-root"]
    if not os.path.isdir(log_root):
        envfail("--log-root %s is not a directory" % log_root)
    try:
        lines = open(log_path, encoding="utf-8").read().splitlines()
    except OSError as e:
        envfail("cannot read --log %s: %s" % (log_path, e))
    last = None
    for raw in lines:
        t = composer_write_time(raw)
        if t is None:
            continue  # excluded writer (MONITOR/EXIT/…) or unparseable stamp — not a clock sample
        # PR-REG-002 (round 11): a composer-clock record that participates in the
        # idle derivation must be OWNED by this run — the idle-check sibling of
        # the derive_pending/immediate_retry_state run-binding. A missing or
        # foreign run= fails CLOSED before any checkpoint/suppression append;
        # excluded writers (composer_write_time -> None) are never checked.
        rec_run = parse_kv(raw)[0].get("run")
        if rec_run != flags["--run"]:
            refuse("idle-check --run %s found a composer-clock record whose run=%r is not this run — the idle gap is derived only from clock evidence owned by its own run (missing/foreign fails closed)"
                   % (flags["--run"], rec_run))
        if last is None or t > last:
            last = t
    # v32.3 T2.3: the delivery echo — AFTER the ownership scan above (a
    # refusal precedes any echo), BEFORE the due-ness early returns (it fires
    # on ordinary short-gap wakes). Stdout narration only; journal untouched.
    _idle_delivery_echo(lines, flags["--run"])
    if last is None:
        return  # no composer clock sample — nothing to measure
    now = datetime.datetime.now().astimezone()
    gap_min = int((now - last).total_seconds() // 60)
    if gap_min < IDLE_GAP_MIN:
        return
    # artifact evidence: newest in-window mtime under the log root
    latest_name, latest_mtime = None, None
    log_real = os.path.realpath(log_path)
    for dirpath, _dirs, files in os.walk(log_root):
        for fn in files:
            p = os.path.join(dirpath, fn)
            if os.path.realpath(p) == log_real:
                continue
            try:
                m = os.path.getmtime(p)
            except OSError:
                continue
            mt = datetime.datetime.fromtimestamp(m).astimezone()
            # PR-MED-005 (round 8): artifact evidence must lie INSIDE the
            # measured idle window `last < mtime <= check_now`. A future mtime
            # (clock skew, an extracted/touched-future file) is NOT activity in
            # the window and must never suppress the checkpoint. The bound is
            # the local check time with NO skew — artifact mtimes share the
            # checker's wall clock (unlike cross-host record stamps, which carry
            # the K9 24h tolerance in composer_write_time).
            if last < mt <= now and (latest_mtime is None or mt > latest_mtime):
                latest_name, latest_mtime = os.path.relpath(p, log_root), mt
    ts = now.isoformat(timespec="seconds")
    if latest_name is not None:
        check_value_safety("latest", latest_name, is_path=True)
        rec = ("CONSUME: source=idle-reentry ts=%s run=%s gap_min=%d suppressed=artifact-activity latest=\"%s@%s\""
               % (ts, flags["--run"], gap_min, latest_name,
                  latest_mtime.isoformat(timespec="seconds")))
    else:
        rec = ("CONSUME: source=idle-reentry ts=%s run=%s gap_min=%d"
               % (ts, flags["--run"], gap_min))
    write_lines(sink, [rec])


ISO_ID_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]*\Z")  # filename-safe; derives journal/marker names
# CLI outcome vocabulary -> the close-state machine's requested transition.
# `complete` is the branch/none marker-disposition close; `reconcile` is the
# retroactive-record convergence for the two evidence-verified stale cells
# (journal-artifact-mismatch; pre-journal marker with --attest owner-dead).
RUN_CLOSE_OUTCOMES = {"retained-green", "merged", "paused", "crashed",
                      "merge-failed", "complete", "reconcile"}
# journal state= value written per requested outcome (worktree mode)
_OUTCOME_STATE = {"retained-green": "retained-green", "paused": "paused",
                  "crashed": "crashed/recovery-needed", "merge-failed": "merge-failed"}
_TERMINAL_STATES = {"cleaned", "retained-green", "paused",
                    "crashed/recovery-needed", "merge-failed"}
# terminal journal state that satisfies each outcome idempotently
_OUTCOME_TERMINAL = {"retained-green": "retained-green", "merged": "cleaned",
                     "paused": "paused", "crashed": "crashed/recovery-needed",
                     "merge-failed": "merge-failed", "reconcile": "cleaned"}


def _rc_parse_kv_lines(raw):
    """Best-effort key=value parse of already-read journal/marker lines. Returns
    (dict, raw-lines) — first occurrence wins; unquotes the serialization rule's
    double-quoted strings (\\\" \\\\ \\n). Split out (PR-HIGH-001 r12) so the
    delegation fold can feed bytes read no-follow through a HELD dir fd rather
    than re-opening the journal/marker by pathname (the check/open gap)."""
    kv = {}
    for line in raw:
        if "=" not in line or line.startswith("#"):
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        if not KEY_ALLOWLIST_RE.match(k) or k in kv:
            continue
        if len(v) >= 2 and v.startswith('"') and v.endswith('"'):
            # Ordered left-to-right unescape (R24 LOW-001): sequential
            # str.replace corrupts values holding literal backslashes
            # (`\\` handled last turns a stored `\\n` into a newline).
            out, i2 = [], 1
            body = v[:-1]
            while i2 < len(body):
                ch = body[i2]
                if ch == "\\" and i2 + 1 < len(body):
                    nxt = body[i2 + 1]
                    out.append({"n": "\n", '"': '"', "\\": "\\"}.get(nxt, "\\" + nxt))
                    i2 += 2
                else:
                    out.append(ch)
                    i2 += 1
            v = "".join(out)
        kv[k] = v
    return kv, raw


def _rc_read_kv_file(path):
    """Read a journal/marker file by path and parse it (the pathname-read
    callers: recovery, run-close). The delegation fold instead reads these
    no-follow through a held dir fd and calls _rc_parse_kv_lines directly."""
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read().splitlines()
    except OSError as e:
        envfail("cannot read %s: %s" % (path, e))
    return _rc_parse_kv_lines(raw)


def _rc_rewrite_journal(path, raw_lines, new_state, extra_key, extra_value):
    """Write-then-atomic-rename journal rewrite: state= replaced, every other
    line byte-preserved, one optional appended key (closed=/reconciled=)."""
    import tempfile
    out = []
    replaced = False
    for line in raw_lines:
        if line.startswith("state=") and not replaced:
            out.append("state=%s" % new_state)
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append("state=%s" % new_state)
    if extra_key is not None:
        out = [l for l in out if not l.startswith(extra_key + "=")]
        out.append('%s="%s"' % (extra_key, extra_value))
    payload = "\n".join(out) + "\n"
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".rc-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except OSError as e:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        envfail("cannot rewrite journal %s: %s" % (path, e))


def _rc_git(base, *args):
    """Run git under the BASE checkout; returns (rc, stdout-stripped)."""
    try:
        r = subprocess.run(["git", "-C", base] + list(args),
                           capture_output=True, text=True, timeout=60)
    except Exception as e:
        return 1, "git failed: %s" % e
    return r.returncode, (r.stdout or "").strip()


def _rc_report(flags, sink, iso, mode, cell, verdict, detail=None):
    """Emit the ONE run-close report record; returns the verdict for exit
    mapping. detail values are fixed tool-authored strings (value-safe)."""
    ts = now_iso()
    rec = ("OWNERSHIP: run-close ts=%s run=%s role=%s iso=%s mode=%s cell=%s verdict=%s"
           % (ts, flags["--run"], flags["--role"], iso, mode, cell, verdict))
    if detail:
        check_value_safety("detail", detail)
        rec += ' detail="%s"' % detail
    write_lines(sink, [rec])
    return verdict


# r25 PR-MED-028: the close-lock release context — set by cmd_run_close after
# the contention check, consumed at finish. The close-lock contract holds the
# lock through the cleanup DECISION and then releases it, so every own-lock
# path that reaches a decided verdict (complete / retained / already-closed)
# unlinks it; refusal cells RETAIN the lock conservatively (recovery may still
# key on it), and foreign/malformed locks are NEVER touched (ownership is
# re-verified at release time, not assumed from the earlier scan).
_RC_LOCK_CTX = None


def _rc_release_own_lock():
    if _RC_LOCK_CTX is None:
        return
    lock_path, iso = _RC_LOCK_CTX
    if not os.path.exists(lock_path):
        return
    lkv, _ = _rc_read_kv_file(lock_path)
    if lkv.get("iso") != iso:
        return  # foreign or malformed — never removed here
    try:
        os.unlink(lock_path)
    except OSError as e:
        sys.stderr.write("own close.lock release failed: %s\n" % e)


def _rc_finish(verdict):
    if verdict in ("complete", "retained", "already-closed"):
        _rc_release_own_lock()
        sys.exit(0)
    sys.exit(3)


def _rc_dispose_marker(marker_path):
    """`-active` -> `.complete-<ts>` (verified close only); idempotent."""
    if not os.path.exists(marker_path):
        return
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        os.replace(marker_path, "%s.complete-%s" % (marker_path, stamp))
    except OSError as e:
        envfail("cannot disposition marker %s: %s" % (marker_path, e))


def _rc_retro_pointer_gap(flags):
    """Green-close obligation: the plan must carry a `Retro report:` pointer.
    Returns a detail string on a gap, else None. --plan is REQUIRED on green
    outcomes (the caller enforces requiredness); check is read-only."""
    plan = flags.get("--plan")
    if plan is None:
        return "plan-flag-missing"
    if not os.path.isabs(plan):
        refuse("--plan must be an absolute path")
    try:
        with open(plan, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return "plan-unreadable"
    if "Retro report:" not in text:
        return "retro-pointer-missing"
    return None


def cmd_run_close(flags, sink):
    """v32 TE.1 (D5/PR-HIGH-005/PR-HIGH-011): the mechanical run-close — a
    TOTAL state machine over the canonical close-state table (execute-loop
    SKILL `Run isolation` + the orchestration doc). One invocation classifies
    the run's on-disk close state into exactly one CELL, performs that cell's
    LEGAL actions only, and emits ONE `OWNERSHIP: run-close` report record.

    Hard rules: destructive teardown (worktree removal, run-branch deletion)
    happens ONLY in the verified-merge worktree cell (journal `merged`,
    branch tip verified merged into base HEAD) — plus the marker-only unlink
    in the pre-journal cell under an explicit `--attest owner-dead` with zero
    matching git artifacts. retained-green / paused / crashed / merge-failed /
    contended / dirty / mismatch cells verify + disposition + report, NEVER
    remove. `-active` -> `.complete-<ts>` only on a verified close. Branch/
    `none` modes carry markers but no journal: their close is marker
    disposition against verified marker evidence — a missing journal NEVER
    implies cleanup authority, and destructive checkout cleanup is
    WORKTREE-ONLY. Idempotent: re-running any cell converges (partial
    cleanups complete; terminal states report already-closed).
    Exit: 0 on complete/retained/already-closed; 3 on a refused cell (record
    written); 2 on grammar/identity refusals (nothing written)."""
    if flags["--role"] != "composer":
        refuse("run-close requires --role composer — the close is a composer-seat duty (dispositions are never a spawned role's)")
    iso = flags.get("--iso")
    base = flags.get("--base")
    outcome = flags.get("--outcome")
    if iso is None or base is None or outcome is None:
        refuse("run-close requires --iso <iso-id> --base </abs/base> --outcome <o>",
               "outcomes: %s" % " | ".join(sorted(RUN_CLOSE_OUTCOMES)))
    if not ISO_ID_RE.match(iso):
        refuse("--iso %r is not a filename-safe iso-id" % iso[:60])
    check_value_safety("iso", iso)
    if outcome not in RUN_CLOSE_OUTCOMES:
        refuse("--outcome %r is not a close outcome" % outcome[:40],
               " | ".join(sorted(RUN_CLOSE_OUTCOMES)))
    if flags.get("--attest") not in (None, "owner-dead"):
        refuse("--attest accepts exactly `owner-dead` (the pre-journal marker disposition's explicit operator attestation)")
    if not os.path.isabs(base):
        refuse("--base must be an absolute path")
    if not os.path.isdir(base):
        envfail("--base %s is not a directory" % base)
    base_real = os.path.realpath(base)
    loops = os.path.join(base_real, ".cursor", "loops")
    journal_path = os.path.join(loops, "%s-isolation" % iso)
    marker_path = os.path.join(loops, "%s-active" % iso)
    lock_path = os.path.join(loops, "close.lock")
    has_journal = os.path.exists(journal_path)
    has_marker = os.path.exists(marker_path)
    disposed = []
    if os.path.isdir(loops):
        disposed = [n for n in sorted(os.listdir(loops))
                    if n.startswith("%s-active.complete-" % iso)]

    # Contention: a close lock naming ANOTHER holder retains everything. An
    # OWN lock arms the release context (r25 PR-MED-028): the lock is removed
    # at any decided verdict, retained on refusals, ownership re-checked at
    # release.
    global _RC_LOCK_CTX
    if os.path.exists(lock_path):
        lkv, _ = _rc_read_kv_file(lock_path)
        holder = lkv.get("iso", "")
        if holder != iso:
            mode_guess = "worktree" if has_journal else "none"
            _rc_finish(_rc_report(flags, sink, iso, mode_guess, "contended", "refused",
                                  "close.lock held by another run"))
        _RC_LOCK_CTX = (lock_path, iso)

    if not has_journal and not has_marker:
        if not disposed:
            refuse("no journal, marker, or disposition found for iso %s under %s — nothing to close (wrong --iso or wrong --base?)" % (iso, loops))
        # Fully closed already: mode from the preserved marker content.
        mkv, _ = _rc_read_kv_file(os.path.join(loops, disposed[-1]))
        mode = mkv.get("mode", "")
        if mode not in ENUMS["ISOLATION_MODES"]:
            refuse("disposed marker %s records no parseable mode= — cannot classify (fail-closed)" % disposed[-1])
        _rc_finish(_rc_report(flags, sink, iso, mode, "cleaned", "already-closed",
                              "marker already dispositioned"))

    # ---- no journal, marker present ----
    if not has_journal:
        mkv, _ = _rc_read_kv_file(marker_path)
        mode = mkv.get("mode", "")
        if mode not in ENUMS["ISOLATION_MODES"]:
            refuse("marker %s records no parseable mode= key — cannot classify the close cell (fail-closed; fix the marker, never guess)" % marker_path)
        # r25 PR-HIGH-022: the marker's documented identity fields (iso-ID,
        # mode, checkout realpath) are MANDATORY before any marker-only
        # disposition — absence refuses, never a pass-through. The pre-journal
        # worktree cell keeps checkout advisory (its unlink is separately
        # gated by --attest + the zero-artifact census), but iso is required
        # everywhere.
        if mkv.get("iso") != iso:
            _rc_finish(_rc_report(flags, sink, iso, mode, "identity-mismatch", "refused",
                                  "marker iso missing or mismatched against --iso"))
        mchk = mkv.get("checkout")
        if mode != "worktree":
            if mchk is None:
                _rc_finish(_rc_report(flags, sink, iso, mode, "identity-mismatch", "refused",
                                      "marker records no checkout= — the documented identity fields are required before any disposition"))
            if os.path.realpath(mchk) != base_real:
                _rc_finish(_rc_report(flags, sink, iso, mode, "identity-mismatch", "refused",
                                      "marker checkout does not match --base"))
        if mode == "worktree":
            # Pre-journal crash window (claim-to-journal-rename gap).
            branch_rc, _ = _rc_git(base_real, "rev-parse", "--verify", "--quiet",
                                   "refs/heads/loop/%s" % iso)
            _, wt_list = _rc_git(base_real, "worktree", "list", "--porcelain")
            artifact = (branch_rc == 0) or (iso in wt_list)
            if artifact:
                _rc_finish(_rc_report(flags, sink, iso, mode, "pre-journal", "refused",
                                      "matching git artifacts exist but no journal — journal-contract recovery owns this"))
            if outcome == "reconcile" and flags.get("--attest") == "owner-dead":
                try:
                    os.unlink(marker_path)
                except OSError as e:
                    envfail("cannot remove pre-journal marker: %s" % e)
                _rc_finish(_rc_report(flags, sink, iso, mode, "pre-journal", "complete",
                                      "owner-dead attested; zero artifacts; marker removed"))
            _rc_finish(_rc_report(flags, sink, iso, mode, "pre-journal", "refused",
                                  "unknown-liveness — retain; reconcile requires --attest owner-dead and --outcome reconcile"))
        # branch / none: marker disposition is the WHOLE close (no journal,
        # no merge-back lifecycle, no checkout mutation EVER).
        if outcome == "complete":
            gap = _rc_retro_pointer_gap(flags)
            if gap:
                _rc_finish(_rc_report(flags, sink, iso, mode, "marker-only", "refused", gap))
            _rc_dispose_marker(marker_path)
            _rc_finish(_rc_report(flags, sink, iso, mode, "marker-only", "complete",
                                  "marker dispositioned; checkout untouched"))
        if outcome in ("paused", "crashed"):
            _rc_finish(_rc_report(flags, sink, iso, mode, "marker-only", "retained",
                                  "marker retained; %s recorded here (no journal in this mode)" % outcome))
        _rc_finish(_rc_report(flags, sink, iso, mode, "marker-only", "refused",
                              "outcome %s is not legal without an isolation journal" % outcome))

    # ---- journal present (worktree lifecycle) ----
    # r25 PR-HIGH-022: MANDATORY identity binding. The journal is the sole
    # authority admitting the one destructive cell, so every identity field is
    # required and bound — absence is a refusal, never a pass-through. A
    # branch/none-mode journal can NEVER reach the worktree lifecycle:
    # journals exist only for worktree runs (the SKILL's registry contract).
    jkv, jraw = _rc_read_kv_file(journal_path)
    mode = jkv.get("mode", "")
    if mode not in ENUMS["ISOLATION_MODES"]:
        refuse("journal %s records no parseable mode= — cannot classify (fail-closed)" % journal_path)
    if mode != "worktree":
        _rc_finish(_rc_report(flags, sink, iso, mode, "identity-mismatch", "refused",
                              "journal records a non-worktree mode — journals exist only for worktree runs; nothing dispositioned"))
    if jkv.get("iso") != iso:
        _rc_finish(_rc_report(flags, sink, iso, mode, "identity-mismatch", "refused",
                              "journal iso missing or mismatched against --iso"))
    jbase = jkv.get("base")
    if jbase is None or os.path.realpath(jbase) != base_real:
        _rc_finish(_rc_report(flags, sink, iso, mode, "identity-mismatch", "refused",
                              "journal base missing or mismatched against --base"))
    state = jkv.get("state", "")
    if outcome == "complete":
        refuse("--outcome complete is the journal-less (branch/none) close — a journaled run closes via its lifecycle outcomes",
               "retained-green | merged | paused | crashed | merge-failed | reconcile")
    worktree = jkv.get("worktree", "")
    branch = jkv.get("branch", "")
    wt_exists = bool(worktree) and os.path.isdir(worktree)
    br_exists = False
    if branch:
        br_rc, _ = _rc_git(base_real, "rev-parse", "--verify", "--quiet",
                           "refs/heads/%s" % branch)
        br_exists = (br_rc == 0)

    terminal_cell = {"cleaned": "cleaned", "retained-green": "retained-green",
                     "paused": "paused", "crashed/recovery-needed": "crashed",
                     "merge-failed": "merge-failed"}
    if state in _TERMINAL_STATES:
        if _OUTCOME_TERMINAL.get(outcome) == state:
            if state == "cleaned" and (wt_exists or br_exists):
                _rc_finish(_rc_report(flags, sink, iso, mode, "journal-artifact-mismatch", "refused",
                                      "journal cleaned but artifacts persist — re-run the merged close after reconciling"))
            # Idempotent convergence; complete a partial marker disposition
            # on the two verified-close terminals only.
            if state in ("cleaned", "retained-green"):
                _rc_dispose_marker(marker_path)
            _rc_finish(_rc_report(flags, sink, iso, mode, terminal_cell[state],
                                  "already-closed"))
        _rc_finish(_rc_report(flags, sink, iso, mode, terminal_cell[state],
                              "refused", "journal already terminal (%s) — a different close needs resume-reconciliation first" % state.split("/")[0]))

    if state in ("intent", "created"):
        _rc_finish(_rc_report(flags, sink, iso, mode, "creation-window", "refused",
                              "creation never completed — recovery owns this window; nothing torn down"))
    if state == "merging":
        _rc_finish(_rc_report(flags, sink, iso, mode, "merging", "refused",
                              "journal mid-merge — close-lock recovery owns this; never torn down here"))
    if state == "active":
        if not wt_exists and not br_exists:
            # The v31merge shape (T0.5): journal claims active, artifacts gone.
            if outcome == "reconcile":
                _rc_rewrite_journal(journal_path, jraw, "cleaned", "reconciled",
                                    "%s retroactive-record: worktree and branch already absent at close" % now_iso())
                _rc_dispose_marker(marker_path)
                _rc_finish(_rc_report(flags, sink, iso, mode, "journal-artifact-mismatch", "complete",
                                      "retroactive reconcile recorded; nothing was torn down"))
            _rc_finish(_rc_report(flags, sink, iso, mode, "journal-artifact-mismatch", "refused",
                                  "journal active but worktree and branch are gone — reconcile explicitly with --outcome reconcile"))
        if outcome == "reconcile":
            _rc_finish(_rc_report(flags, sink, iso, mode, "journal-artifact-mismatch", "refused",
                                  "artifacts still exist — reconcile is only for the verified-absent shape"))
        if outcome == "merged":
            _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "refused",
                                  "journal still active — the merge-back (close lock, merging, merged) is the composer's step and must precede cleanup"))
        if outcome == "retained-green":
            if not wt_exists or not br_exists:
                _rc_finish(_rc_report(flags, sink, iso, mode, "journal-artifact-mismatch", "refused",
                                      "retained-green requires the worktree and branch to exist"))
            gap = _rc_retro_pointer_gap(flags)
            if gap:
                _rc_finish(_rc_report(flags, sink, iso, mode, "retained-green", "refused", gap))
            _rc_rewrite_journal(journal_path, jraw, "retained-green", "closed", now_iso())
            _rc_dispose_marker(marker_path)
            _rc_finish(_rc_report(flags, sink, iso, mode, "retained-green", "complete",
                                  "worktree and branch retained; journal retained-green; marker dispositioned"))
        # paused / crashed / merge-failed: persist the outcome, retain ALL.
        _rc_rewrite_journal(journal_path, jraw, _OUTCOME_STATE[outcome], None, None)
        _rc_finish(_rc_report(flags, sink, iso, mode, outcome, "retained",
                              "outcome persisted; worktree, branch, journal and marker all retained"))
    if state == "merged":
        if outcome != "merged":
            _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "refused",
                                  "journal is merged — only --outcome merged may complete this close"))
        # r25 PR-HIGH-022: the ONE destructive cell admits only a COMPLETE,
        # internally consistent worktree-run identity, every leg bound to git
        # evidence — never to arbitrary journal strings.
        # (a) The journal must name both artifacts.
        if not branch or not worktree:
            _rc_finish(_rc_report(flags, sink, iso, mode, "identity-mismatch", "refused",
                                  "journal names no branch or no worktree — the destructive cell requires the full recorded identity"))
        # (b) Worktree-registration binding: the recorded path must be a
        # REGISTERED worktree of this base, checked out on the run branch. A
        # directory that exists but is not registered — or is registered on a
        # different/detached HEAD — is never removed.
        wt_real = os.path.realpath(worktree)
        _, wt_porc = _rc_git(base_real, "worktree", "list", "--porcelain")
        wt_registered = False
        wt_ref = None
        cur_path = None
        for pline in wt_porc.splitlines():
            if pline.startswith("worktree "):
                cur_path = os.path.realpath(pline[len("worktree "):])
            elif pline.startswith("branch ") and cur_path == wt_real:
                wt_ref = pline[len("branch "):]
            elif pline.startswith("detached") and cur_path == wt_real:
                wt_ref = "detached"
            if cur_path == wt_real:
                wt_registered = True
        if wt_exists and not wt_registered:
            _rc_finish(_rc_report(flags, sink, iso, mode, "identity-mismatch", "refused",
                                  "recorded worktree directory exists but is not a registered worktree of this base — never removed"))
        if wt_registered and wt_ref != "refs/heads/%s" % branch:
            _rc_finish(_rc_report(flags, sink, iso, mode, "identity-mismatch", "refused",
                                  "registered worktree is not checked out on the recorded run branch (detached or wrong branch) — never removed"))
        # (c) Ancestry binding against the RESOLVED base: the run-branch tip
        # must resolve AND be an ancestor of the recorded base branch (HEAD
        # fallback only when the journal predates base_branch). An ABSENT
        # branch ref fails closed to report-only whenever anything remains to
        # tear down — the only ref-less admission is the both-already-gone
        # idempotent convergence.
        base_ref = "refs/heads/%s" % jkv["base_branch"] if jkv.get("base_branch") else "HEAD"
        tip_rc, tip = _rc_git(base_real, "rev-parse", "--verify", "--quiet",
                              "refs/heads/%s" % branch)
        if tip_rc != 0:
            if wt_exists or wt_registered:
                _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "refused",
                                      "run-branch ref is absent so the merge cannot be re-verified — worktree retained, report-only"))
        else:
            anc_rc, _ = _rc_git(base_real, "merge-base", "--is-ancestor", tip, base_ref)
            if anc_rc != 0:
                _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "refused",
                                      "merge verification failed — run branch tip is not in the resolved base; everything retained"))
        gap = _rc_retro_pointer_gap(flags)
        if gap:
            _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "refused", gap))
        if wt_exists:
            r = subprocess.run(["git", "-C", base_real, "worktree", "remove", worktree],
                               capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                sys.stderr.write("worktree remove refused: %s\n" % (r.stderr or "").strip()[:400])
                _rc_finish(_rc_report(flags, sink, iso, mode, "dirty", "refused",
                                      "non-force worktree removal refused (dirty or locked) — everything retained"))
        else:
            _rc_git(base_real, "worktree", "prune")
        if tip_rc == 0:
            r = subprocess.run(["git", "-C", base_real, "branch", "-d", branch],
                               capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                sys.stderr.write("branch -d refused: %s\n" % (r.stderr or "").strip()[:400])
                _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "refused",
                                      "non-force branch deletion refused — re-run after reconciling"))
        _rc_rewrite_journal(journal_path, jraw, "cleaned", "closed", now_iso())
        _rc_dispose_marker(marker_path)
        _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "complete",
                              "merge verified; worktree removed; branch deleted; journal cleaned; marker dispositioned"))
    _rc_finish(_rc_report(flags, sink, iso, mode, "journal-artifact-mismatch", "refused",
                          "unrecognized journal state — retain everything and reconcile by hand"))


# --- v32.2 T2.3: fold-delegation — the delegation staging→canonical promotion -

# The CLOSED delegation record matrix consumed at the fold boundary. NORMATIVE
# OWNER: scripts/fixtures/delegation-variants.json (r4 PR-MED-002 + r5
# PR-MED-001 — one auditable schema). The GENERATED block below is produced by
# `python3 scripts/loop-journal.py --emit-delegation-variants` from that fixture
# (PR-LOW-003: the V_base pattern — a deterministic generation/verification path,
# not two hand-maintained schema copies); the journal selftest asserts the
# embedded block is byte-equal to the generator output, so a stale hand-edit
# FAILS. Runtime is INDEPENDENT of the repo-only fixture — the embedded literal
# is authoritative at run time; the fixture is read only by the dev/selftest
# generator. Strictness scopes to the NEW promotion boundary ONLY: historical
# probe-log DELEGATION lines (any-kv shapes, the kount ledger `peer` verb) stay
# corpus-legal under the oracle's unchanged loose admission.
DELEGATION_BLOCK_BEGIN = "# --- BEGIN GENERATED DELEGATION_VARIANTS"
DELEGATION_BLOCK_END = "# --- END GENERATED DELEGATION_VARIANTS ---"


def _py_str_tuple(items):
    """A deterministic Python source tuple of double-quoted strings, with the
    single-element trailing comma so `("x",)` stays a tuple."""
    inner = ", ".join('"%s"' % s for s in items)
    return "(%s,)" % inner if len(items) == 1 else "(%s)" % inner


def delegation_variants_block(fixture):
    """The deterministic Python source (exclusive of the marker lines) for the
    DELEGATION_VARIANTS constant + bounds, generated from the fixture dict
    (PR-LOW-003). One line per variant, in fixture order."""
    out = []
    out.append("# Generated by `python3 scripts/loop-journal.py --emit-delegation-variants`")
    out.append("# from scripts/fixtures/delegation-variants.json (PR-LOW-003 — the schema owner).")
    out.append("# Do NOT hand-edit; regenerate + re-splice on any fixture change.")
    out.append("DELEGATION_VARIANTS = {")
    for name, spec in fixture["variants"].items():
        out.append('    "%s": {"required": %s, "optional": %s},'
                   % (name, _py_str_tuple(spec["required"]), _py_str_tuple(spec["optional"])))
    out.append("}")
    b = fixture["bounds"]
    out.append("DELEGATION_MAX_SOURCE_BYTES = %d  # the 256 KiB staging bound (T2.3)"
               % b["max_source_bytes"])
    out.append("DELEGATION_MAX_LINE_BYTES = %d" % b["max_line_bytes"])
    out.append("DELEGATION_MAX_VALUE_CHARS = %d" % b["max_value_chars"])
    return "\n".join(out) + "\n"


# --- BEGIN GENERATED DELEGATION_VARIANTS (python3 scripts/loop-journal.py --emit-delegation-variants) ---
# Generated by `python3 scripts/loop-journal.py --emit-delegation-variants`
# from scripts/fixtures/delegation-variants.json (PR-LOW-003 — the schema owner).
# Do NOT hand-edit; regenerate + re-splice on any fixture change.
DELEGATION_VARIANTS = {
    "decision": {"required": ("ts", "run", "unit", "spec", "delegate"), "optional": ("backend", "model", "detail")},
    "outcome": {"required": ("ts", "run", "unit", "result"), "optional": ("misses", "smoke", "detail")},
    "roi": {"required": ("ts", "run", "unit", "detail"), "optional": ("tokens", "duration")},
    "smoke-addendum": {"required": ("ts", "run", "unit", "result"), "optional": ("detail",)},
}
DELEGATION_MAX_SOURCE_BYTES = 262144  # the 256 KiB staging bound (T2.3)
DELEGATION_MAX_LINE_BYTES = 4096
DELEGATION_MAX_VALUE_CHARS = 1024
# --- END GENERATED DELEGATION_VARIANTS ---


def validate_delegation_snapshot(data, runkey):
    """Validate ONE staging snapshot (bytes) against the closed variant matrix.
    Returns the admitted record count. Refuses (exit 2, no side effects — the
    caller has written nothing yet, so staging is retained by construction) on:
    over-bound source, invalid UTF-8, a torn trailing line, any non-DELEGATION
    line-start, control characters, stray prose tokens, an unknown/missing
    variant verb, duplicate/unknown keys, missing or blank required values,
    over-bound lines/values, a malformed ts=, or a record claiming another
    stage's run="""
    if len(data) > DELEGATION_MAX_SOURCE_BYTES:
        refuse("staging snapshot exceeds the %d-byte bound (over-bound source — retain + surface)"
               % DELEGATION_MAX_SOURCE_BYTES)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        refuse("staging snapshot is not valid UTF-8 (retain + surface)")
    if text and not text.endswith("\n"):
        refuse("staging snapshot ends in a partial (torn) trailing line — never a partial promotion (retain + surface)")
    records = 0
    for n, line in enumerate(text.split("\n")[:-1] if text else [], start=1):
        if not line.strip():
            continue  # blank separator lines are tolerated, never records
        for ch in line:
            if ord(ch) < 0x20 or ord(ch) == 0x7f:
                refuse("staging line %d carries a control character — forged-record lever (retain + surface)" % n)
        if len(line.encode("utf-8")) > DELEGATION_MAX_LINE_BYTES:
            refuse("staging line %d exceeds the %d-byte line bound (retain + surface)"
                   % (n, DELEGATION_MAX_LINE_BYTES))
        if not line.startswith("DELEGATION: "):
            refuse("staging line %d is not a literal line-start `DELEGATION: ` record — mixed prose never promotes (retain + surface)" % n)
        why = assembled_line_ok(line)
        if why is not None:
            refuse("staging line %d fails the output-chokepoint fidelity check: %s (retain + surface)" % (n, why))
        keys, kv, bare = [], {}, []
        for m in PARSE_KV_RE.finditer(line):
            if m.group(1) is not None:
                keys.append(m.group(1))
                kv[m.group(1)] = m.group(2)
            elif m.group(3) is not None:
                keys.append(m.group(3))
                kv[m.group(3)] = m.group(4)
            else:
                bare.append(m.group(5))
        # bare[0] is the "DELEGATION:" prefix token itself; bare[1] the variant.
        if len(bare) < 2:
            refuse("staging line %d carries no variant verb — the closed matrix is %s (retain + surface)"
                   % (n, "|".join(sorted(DELEGATION_VARIANTS))))
        if len(bare) > 2:
            refuse("staging line %d carries stray prose tokens %r — a record is one variant verb + key=value only (retain + surface)"
                   % (n, bare[2:4]))
        variant = bare[1]
        if variant not in DELEGATION_VARIANTS:
            refuse("staging line %d names unknown variant %r — the closed matrix is %s (retain + surface)"
                   % (n, variant[:40], "|".join(sorted(DELEGATION_VARIANTS))))
        spec = DELEGATION_VARIANTS[variant]
        if len(set(keys)) != len(keys):
            refuse("staging line %d carries a duplicate key (uniqueness rule; retain + surface)" % n)
        admitted = set(spec["required"]) | set(spec["optional"])
        for k in keys:
            if k not in admitted:
                refuse("staging line %d carries unknown key %s= for variant %s (closed per-variant key sets; retain + surface)"
                       % (n, k[:40], variant))
        for k in spec["required"]:
            if k not in kv:
                refuse("staging line %d (%s) is missing required key %s= (retain + surface)"
                       % (n, variant, k))
            if not kv[k].strip():
                refuse("staging line %d (%s) has a blank required %s= value (nonblank floor; retain + surface)"
                       % (n, variant, k))
        for k, v in kv.items():
            if len(v) > DELEGATION_MAX_VALUE_CHARS:
                refuse("staging line %d value %s= exceeds the %d-char value bound (retain + surface)"
                       % (n, k, DELEGATION_MAX_VALUE_CHARS))
        if not TS_LOCAL_RE.match(kv["ts"]):
            refuse("staging line %d ts=%r is not a local ISO-with-offset clock read (the ts-form pin; retain + surface)"
                   % (n, kv["ts"][:40]))
        if kv["run"] != runkey:
            refuse("staging line %d claims run=%s but this fold is --run %s — a record never promotes into another stage's canonical file (retain + surface)"
                   % (n, kv["run"][:40], runkey))
        records += 1
    return records


def _fd_walk_dir(root_real, rel_segments, what):
    """PR-HIGH-001 (v32.2 r12): open the authority root and walk each
    below-root component with openat + O_DIRECTORY|O_NOFOLLOW, returning a
    HELD directory fd for the final directory — the CALLER owns the close.
    Holding the fd across validation AND use closes the check/open race a
    pathname re-open leaves open: a parent component swapped to a symlink
    *after* the walk cannot redirect a descriptor already bound to the
    validated inode (the reproduced `<worktree>/.cursor/loops → /outside`
    swap). root_real is a realpath (symlink-free chain), so a legitimately-
    symlinked ANCESTOR *above* the recorded checkout is already resolved into
    it and the root open follows that canonical path (the finding's regression
    guard); every component BELOW the root is opened no-follow, so a symlink
    there refuses. A missing component, a symlink, or a non-directory refuses
    before any payload read or write."""
    try:
        rst = os.lstat(root_real)
    except OSError:
        refuse("%s authority root %s does not exist (retain + surface)" % (what, root_real))
    if stat.S_ISLNK(rst.st_mode) or not stat.S_ISDIR(rst.st_mode):
        refuse("%s authority root %s is not a real directory (retain + surface)" % (what, root_real))
    try:
        dfd = os.open(root_real, os.O_RDONLY | os.O_DIRECTORY)
    except OSError as e:
        envfail("cannot open %s authority root %s: %s" % (what, root_real, e))
    ok = False
    try:
        for seg in rel_segments:
            if seg in ("", ".", ".."):
                refuse("%s path escapes the authority root via %r (root-escape; retain + surface)" % (what, seg))
            # Classify the component no-follow relative to the HELD parent fd for
            # a precise message (a symlink-to-dir opens as ELOOP on some kernels
            # and ENOTDIR on others); the openat O_NOFOLLOW below stays the real
            # guard and catches any swap between this lstat-at and the open.
            try:
                lst = os.stat(seg, dir_fd=dfd, follow_symlinks=False)
            except FileNotFoundError:
                refuse("%s component %r is missing (retain + surface)" % (what, seg))
            except OSError as e:
                envfail("cannot stat %s component %r: %s" % (what, seg, e))
            if stat.S_ISLNK(lst.st_mode):
                refuse("%s component %r is a symlink — no-follow containment forbids a symlink below the recorded root (root-escape; retain + surface)"
                       % (what, seg))
            if not stat.S_ISDIR(lst.st_mode):
                refuse("%s component %r is not a directory (root-escape; retain + surface)" % (what, seg))
            try:
                nfd = os.open(seg, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dfd)
            except OSError as e:
                if e.errno in (errno.ELOOP, errno.EMLINK, errno.ENOTDIR):
                    refuse("%s component %r changed to a symlink/non-directory between check and open (check/open race; root-escape; retain + surface)"
                           % (what, seg))
                if e.errno == errno.ENOENT:
                    refuse("%s component %r vanished between check and open (retain + surface)" % (what, seg))
                envfail("cannot open %s component %r: %s" % (what, seg, e))
            os.close(dfd)
            dfd = nfd
        ok = True
        return dfd
    finally:
        if not ok:
            try:
                os.close(dfd)
            except OSError:
                pass


def _fd_walk_contained_logroot(base_real, recorded_base, log_root, what):
    """PR-HIGH-001 (r12): open a HELD dir fd for the journal-recorded
    `log_root=`, which must live UNDER the base checkout. The relative segments
    are derived TEXTUALLY against the recorded `base=` (which shares log_root's
    path spelling by journal construction), NOT against base_real — so a
    legitimately-symlinked ANCESTOR above the checkout cancels in the relpath
    and is permitted (the finding's regression guard), while any `..` escape
    refuses. The no-follow walk then runs from base_real, so a symlink
    component BELOW the checkout still refuses (never realpath the log_root — a
    below-root symlink would resolve away and defeat the no-follow guard).
    Returns a HELD directory fd for the log root (caller closes)."""
    rel = os.path.relpath(os.path.normpath(log_root), os.path.normpath(recorded_base))
    if rel == os.pardir or rel.startswith(os.pardir + os.sep) or os.path.isabs(rel):
        refuse("%s %s is not under the recorded base checkout %s (root-escape; retain + surface)"
               % (what, log_root, recorded_base))
    rel_segs = [] if rel == os.curdir else rel.split(os.sep)
    return _fd_walk_dir(base_real, rel_segs, what)


def _fd_regular_at(dir_fd, name, what):
    """PR-HIGH-001 (r12): no-follow fstatat relative to a HELD dir fd — an
    existing name must be a REGULAR file (symlink/dir/special refuses). Returns
    the stat (carrying st_dev/st_ino for identity-binding across a later open),
    or None when absent. `name` is a single path component, never a subpath."""
    try:
        st = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as e:
        envfail("cannot stat %s %r: %s" % (what, name, e))
    if not stat.S_ISREG(st.st_mode):
        refuse("%s %r is not a regular file (no-follow — symlink/dir/special refuses; retain + surface)"
               % (what, name))
    return st


def _fd_open_ro_at(dir_fd, name, what, expect_st=None):
    """PR-HIGH-001 (r12): open a payload file read-only RELATIVE to the held
    dir fd with O_NOFOLLOW + a post-open fstat regular check. The held dir fd
    already defeats a parent-component swap; when `expect_st` is supplied the
    (st_dev, st_ino) identity-bind additionally rejects a same-directory
    substitution of the final component between its stat and this open. Returns
    the bytes read; refuses a symlink, a non-regular target, or an identity
    mismatch."""
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dir_fd)
    except OSError as e:
        if e.errno in (errno.ELOOP, errno.EMLINK):
            refuse("%s %r is a symlink (no-follow open; root-escape; retain + surface)" % (what, name))
        envfail("cannot open %s %r: %s" % (what, name, e))
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            refuse("%s %r is not a regular file after open (retain + surface)" % (what, name))
        if expect_st is not None and (st.st_dev, st.st_ino) != (expect_st.st_dev, expect_st.st_ino):
            refuse("%s %r changed identity between check and open (check/open race; retain + surface)" % (what, name))
        with os.fdopen(fd, "rb") as fh:
            fd = -1
            return fh.read()
    finally:
        if fd >= 0:
            os.close(fd)


def _fd_append_at(dir_fd, name, data, what, expect_st=None, create=False):
    """PR-HIGH-001 (r12/r13): append RELATIVE to the held dir fd with O_NOFOLLOW
    + O_APPEND and a post-open fstat regular check. **Identity-bound WRITE
    (r13):** the reads were `(st_dev,st_ino)`-bound (`_fd_open_ro_at`); the write
    side now is too. `expect_st` (an existing destination's pre-captured stat) —
    the file MUST already exist (no O_CREAT) and its post-open `fstat` MUST match
    `(st_dev,st_ino)` BEFORE any byte is written, so a same-directory
    rename-aside + regular-file replacement of the final component is REFUSED
    rather than appended-to-then-`published` (the live r13 canonical-swap
    repro); a removed expected-existing destination (ENOENT) likewise refuses.
    `create=True` (an expected-absent first publish) opens O_CREAT|O_EXCL — a
    name that appeared in the interval fails closed (EEXIST). Returns the written
    inode's stat so a later append on the SAME file threads its identity.
    `create` and `expect_st` are mutually exclusive. PR-REG-001 (r12): a CHECKED
    write loop advancing by the returned byte count until EVERY byte is
    persisted, with zero forward progress a hard failure (never advance to
    `published`, staging retained)."""
    if create and expect_st is not None:
        envfail("%s %r: create and expect_st are mutually exclusive (internal invariant)" % (what, name))
    flags = os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW
    if create:
        flags |= os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(name, flags, 0o644, dir_fd=dir_fd)
    except OSError as e:
        if e.errno in (errno.ELOOP, errno.EMLINK):
            refuse("%s %r is a symlink (no-follow open; root-escape; retain + surface)" % (what, name))
        if create and e.errno == errno.EEXIST:
            refuse("%s %r appeared between validation and create — an expected-absent destination was substituted (never advance to published; retain + surface)"
                   % (what, name))
        if not create and e.errno == errno.ENOENT:
            refuse("%s %r vanished between validation and append — an expected-existing destination was removed (never advance to published; retain + surface)"
                   % (what, name))
        envfail("cannot open %s %r for append: %s" % (what, name, e))
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            refuse("%s %r is not a regular file after open (retain + surface)" % (what, name))
        if expect_st is not None and (st.st_dev, st.st_ino) != (expect_st.st_dev, expect_st.st_ino):
            refuse("%s %r changed identity between validation and append (check/open race; never advance to published; retain + surface)"
                   % (what, name))
        mv = memoryview(data)
        total = 0
        while total < len(mv):
            try:
                n = os.write(fd, mv[total:])
            except OSError as e:
                envfail("%s %r: write failed after %d/%d bytes (partial durable append; never advance to published; retain + surface): %s"
                        % (what, name, total, len(mv), e))
            if n <= 0:
                envfail("%s %r: os.write made zero progress after %d/%d bytes (partial durable append; never advance to published; retain + surface)"
                        % (what, name, total, len(mv)))
            total += n
        os.fsync(fd)
        return st
    finally:
        os.close(fd)


def _fd_read_kv_at(dir_fd, name, what, expect_st):
    """PR-HIGH-001 (r12): read a journal/marker file no-follow RELATIVE to a
    held dir fd (identity-bound) and parse its key=value lines — no pathname
    re-open, so a parent-component symlink swapped in between the stat and the
    authority read cannot redirect it. Returns the parsed dict."""
    blob = _fd_open_ro_at(dir_fd, name, what, expect_st=expect_st)
    try:
        raw = blob.decode("utf-8").splitlines()
    except UnicodeDecodeError as e:
        envfail("cannot decode %s %r: %s" % (what, name, e))
    kv, _ = _rc_parse_kv_lines(raw)
    return kv


def _fd_read_receipts(dir_fd, name, leg):
    """Newest receipt for this leg from the tool-owned sidecar (append-only;
    one `leg= state= digest= offset= length= lines= ts=` line per transaction
    phase), read RELATIVE to the held log-root dir fd (PR-HIGH-001 r12). A
    malformed line refuses — the sidecar is tool-written, so corruption is an
    evidence problem, never skippable."""
    st = _fd_regular_at(dir_fd, name, "receipts sidecar")
    if st is None:
        return None, None
    blob = _fd_open_ro_at(dir_fd, name, "receipts sidecar", expect_st=st)
    try:
        raw = blob.decode("utf-8").splitlines()
    except UnicodeDecodeError as e:
        envfail("cannot decode receipts sidecar %r: %s" % (name, e))
    prior = None
    for n, line in enumerate(raw, start=1):
        if not line.strip():
            continue
        rkv, rbare = parse_kv(line)
        needed = ("leg", "state", "digest", "offset", "length", "lines", "ts")
        if rbare or any(k not in rkv for k in needed):
            refuse("receipts sidecar line %d is malformed — the sidecar is tool-owned; reconcile before folding (retain + surface)" % n)
        if rkv["state"] not in ("intent", "published"):
            refuse("receipts sidecar line %d has unknown state=%r" % (n, rkv["state"][:20]))
        if not rkv["offset"].isdigit() or not rkv["length"].isdigit():
            refuse("receipts sidecar line %d has a non-numeric offset=/length=" % n)
        if rkv["leg"] == leg:
            prior = rkv
    # PR-HIGH-001 (r13): return the read inode's stat so every subsequent
    # receipts append binds to the SAME identity (no read/re-stat TOCTOU).
    return prior, st


def _fd_receipt_write(dir_fd, name, leg, state, digest, offset, length, lines_n,
                      expect_st=None, create=False):
    """Append one receipt line, identity-bound to the receipts inode (PR-HIGH-001
    r13): pass expect_st for an existing sidecar, create=True for the first
    receipt of a fresh fold. Returns the written inode's stat to thread to the
    next receipt append on the same file."""
    line = ("leg=%s state=%s digest=%s offset=%d length=%d lines=%d ts=%s\n"
            % (leg, state, digest, offset, length, lines_n, now_iso()))
    return _fd_append_at(dir_fd, name, line.encode("utf-8"), "receipts sidecar",
                         expect_st=expect_st, create=create)


def _fd_range_digest_ok(dir_fd, name, offset, length, digest, expect_st=None):
    """sha256 of canonical[offset:offset+length] equals the receipt digest —
    the append-only verification a retry keys on (staging content not needed).
    Reads through the O_NOFOLLOW dir-fd-relative payload opener with the
    canonical's pre-checked identity bound (PR-HIGH-001 r12)."""
    blob = _fd_open_ro_at(dir_fd, name, "canonical destination", expect_st=expect_st)
    chunk = blob[offset:offset + length]
    if len(chunk) != length:
        return False
    return hashlib.sha256(chunk).hexdigest() == digest


def _fd_retire(dir_fd, name, digest):
    """Atomic renameat retirement to a NON-corpus name (no trailing `.log` —
    leaves /retro's enumeration; r4 PR-MED-001), relative to the held staging
    dir fd (PR-HIGH-001 r12). DIGEST-BOUND (r24 PR-MED-001): the current
    occupant at `name` is re-read no-follow (identity-bound via
    `_fd_open_ro_at`) and compared against the leg's PROVEN digest — the
    receipt/validated digest the caller's path just verified — immediately
    before the rename, so retirement applies only to the bytes the receipt
    proves. A swap after the validated snapshot REFUSES with the occupant
    RETAINED at the corpus-visible staging name — never renamed to a
    non-corpus name under a success report (the fail-open loss class). The
    digest comparison is the load-bearing binding: the r24 leg-1 repro
    observed filesystem INODE REUSE across a remove+rewrite swap, so a
    (st_dev, st_ino) compare alone can pass over different bytes. Residual
    window: the re-read→rename gap only (no portable verify-and-rename
    atomic exists) — down from the whole fold. Idempotent: an absent staging
    file after a verified publication is the already-retired state."""
    try:
        st = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as e:
        envfail("cannot stat staging %r for retirement: %s" % (name, e))
    occupant = _fd_open_ro_at(dir_fd, name, "staging file at retirement", expect_st=st)
    if hashlib.sha256(occupant).hexdigest() != digest:
        refuse("staging %r at retirement does not match the leg's proven digest — occupant swapped after the validated snapshot; retirement refused, occupant retained at the staging name as corpus-visible evidence (r24 PR-MED-001; canonical/receipt state stands as published)" % name)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    target = "%s.staged-%s" % (name, stamp)
    try:
        os.replace(name, target, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
    except OSError as e:
        envfail("cannot retire staging %r: %s" % (name, e))
    return target


def cmd_fold_delegation(flags):
    """v32.2 T2.3 (r1 PR-HIGH-001 chain → r5): promote ONE spawned-architect
    activation's staging file into the canonical `<log-root>/stage-<N>-
    delegation.log` — the canonical file's ONLY writer. AUTHORITY-DERIVED
    paths (r5 PR-HIGH-003): worktree mode resolves BOTH endpoints from the
    isolation journal `<base>/.cursor/loops/<iso>-isolation` (iso/mode/base/
    worktree/log_root/state validated); branch/none — which have NO journal —
    resolve from the `<iso>-active` marker (iso/mode/checkout validated) with
    the flat base-side log root; no cwd inference anywhere, every mismatch
    refuses BEFORE any read or write. PUBLICATION is ACTIVATION-KEYED
    append-once (r5 PR-HIGH-002): validate the snapshot, two-phase durable
    receipt (intent → append → published) in the non-corpus `.receipts`
    sidecar, atomic staging retirement to a non-`.log` name after VERIFIED
    publication; a retry verifies receipt + canonical bytes, no-ops, and
    converges the retirement; canonical bytes are never rewritten or
    truncated. A MISSING staging channel with no receipt REFUSES — absence is
    never zero work (r4 PR-HIGH-002); the pre-created empty file folds as the
    explicit zero. Composer-only at the GRANT layer (spawned-role grants carry
    only the narrowed emission shapes; --role composer here is the
    mis-attribution gate, not authentication — under perms=bypass no grant
    boundary exists and the close-table confirm covers it)."""
    if flags["--role"] != "composer":
        refuse("fold-delegation requires --role composer — canonical delegation publication is a composer-seat duty (argv label; real ownership is the GRANT layer: spawned-role grants carry only the emission shapes)")
    iso = flags.get("--iso")
    base = flags.get("--base")
    leg = flags.get("--leg")
    if iso is None or base is None or leg is None:
        refuse("fold-delegation requires --base </abs/base> --iso <iso-id> --leg <leg> (r5 PR-HIGH-003's pinned argv — paths are authority-derived, never caller-chosen)")
    if not ISO_ID_RE.match(iso):
        refuse("--iso %r is not a filename-safe iso-id" % iso[:60])
    if not LEG_RE.match(leg):
        refuse("--leg %r must be filename-safe [A-Za-z0-9._-]+ (it keys the staging identity)" % leg[:60])
    if not os.path.isabs(base):
        refuse("--base must be an absolute path")
    if not os.path.isdir(base):
        envfail("--base %s is not a directory" % base)
    runkey = flags["--run"]
    base_real = os.path.realpath(base)
    loops = os.path.join(base_real, ".cursor", "loops")
    journal_name = "%s-isolation" % iso
    marker_name = "%s-active" % iso
    staging_name = "%s-delegation.%s.log" % (runkey, leg)
    canonical_name = "%s-delegation.log" % runkey
    receipts_name = "%s-delegation.receipts" % runkey

    # ---- authority walk + held-dir-fd I/O (PR-HIGH-001 r12) -----------------
    # Hold the base `.cursor/loops` dir fd FIRST, then read the journal/marker
    # NO-FOLLOW through it and open every payload openat-relative to a held dir
    # fd — so no parent component swapped to a symlink AFTER validation (journal,
    # marker, staging, canonical, or receipts) can redirect the fold outside the
    # authority pair (r12: the round-11 pathname re-opens left a check/open race
    # the swap defeated). A symlinked ANCESTOR above the recorded checkout stays
    # legal (roots realpath'd / relpath-derived); a symlink BELOW refuses. Every
    # mismatch refuses before any read or write.
    open_fds = []
    try:
        base_loops_fd = _fd_walk_dir(base_real, (".cursor", "loops"), "base loops dir")
        open_fds.append(base_loops_fd)
        j_st = _fd_regular_at(base_loops_fd, journal_name, "isolation journal")
        if j_st is not None:
            jkv = _fd_read_kv_at(base_loops_fd, journal_name, "isolation journal", j_st)
            if jkv.get("mode") != "worktree":
                refuse("journal records mode=%r — journals exist only for worktree runs; a branch/none fold resolves via the -active marker" % jkv.get("mode"))
            if jkv.get("iso") != iso:
                refuse("journal iso missing or mismatched against --iso (refuse before any read/write)")
            jbase = jkv.get("base")
            if jbase is None or os.path.realpath(jbase) != base_real:
                refuse("journal base missing or mismatched against --base (refuse before any read/write)")
            state = jkv.get("state", "")
            if state not in ("created", "active", "paused", "crashed/recovery-needed",
                             "retained-green", "merge-failed"):
                refuse("journal state=%r does not admit a delegation fold — staging exists only between spawn and close (intent/merging/merged/cleaned refuse)" % state[:40])
            worktree = jkv.get("worktree")
            if not worktree or not os.path.isabs(worktree):
                refuse("journal records no absolute worktree= — the authority walk derives the staging root from it (r5 PR-HIGH-003)")
            if not os.path.isdir(worktree):
                envfail("journal worktree %s is not a directory" % worktree)
            log_root = jkv.get("log_root")
            if not log_root or not os.path.isabs(log_root):
                refuse("journal records no absolute log_root= — the authority walk derives the canonical destination from it (r5 PR-HIGH-003)")
            if not os.path.isdir(log_root):
                envfail("journal log_root %s is not a directory" % log_root)
            # The recorded worktree/base are the authority roots (realpath'd — a
            # symlinked ancestor above them is permitted); nothing symlinked below.
            staging_fd = _fd_walk_dir(os.path.realpath(worktree), (".cursor", "loops"),
                                      "worktree staging dir")
            open_fds.append(staging_fd)
            log_root_fd = _fd_walk_contained_logroot(base_real, jbase, log_root, "canonical log-root")
            open_fds.append(log_root_fd)
        else:
            m_st = _fd_regular_at(base_loops_fd, marker_name, "ownership marker")
            if m_st is None:
                refuse("no isolation journal or ownership marker for iso %s under %s — fold paths are authority-derived, never cwd/caller-chosen (r5 PR-HIGH-003; wrong --iso or wrong --base?)" % (iso, loops))
            mkv = _fd_read_kv_at(base_loops_fd, marker_name, "ownership marker", m_st)
            if mkv.get("iso") != iso:
                refuse("marker iso missing or mismatched against --iso (refuse before any read/write)")
            mmode = mkv.get("mode")
            if mmode not in ("branch", "none"):
                refuse("marker records mode=%r without an isolation journal — a worktree fold requires the journal authority (never marker-only)" % (mmode,))
            mchk = mkv.get("checkout")
            if mchk is None or os.path.realpath(mchk) != base_real:
                refuse("marker checkout missing or mismatched against --base (refuse before any read/write)")
            # branch/none: staging and canonical live in the SAME base loops dir.
            staging_fd = log_root_fd = base_loops_fd

        # prior + the receipts inode identity (rst) — the SAME stat binds every
        # later receipts append (PR-HIGH-001 r13); rst is None when the sidecar
        # is absent (a fresh fold), which routes the first receipt write to
        # create=True.
        prior, rst = _fd_read_receipts(log_root_fd, receipts_name, leg)
        st = _fd_regular_at(staging_fd, staging_name, "staging file")
        data = None
        if st is not None:
            if st.st_size > DELEGATION_MAX_SOURCE_BYTES:
                refuse("staging %s exceeds the %d-byte bound (over-bound source — retain + surface)"
                       % (staging_name, DELEGATION_MAX_SOURCE_BYTES))
            data = _fd_open_ro_at(staging_fd, staging_name, "staging file", expect_st=st)  # ONE snapshot (T2.3)
        cst = _fd_regular_at(log_root_fd, canonical_name, "canonical destination")

        # ---- retry/convergence dispositions (r5 PR-HIGH-002's state machine)
        if prior is not None and prior["state"] == "published":
            p_off, p_len = int(prior["offset"]), int(prior["length"])
            if p_len > 0 and (cst is None or not _fd_range_digest_ok(log_root_fd, canonical_name, p_off, p_len, prior["digest"], expect_st=cst)):
                refuse("published receipt for leg %s does not verify against canonical bytes — the append-only invariant is broken (rewritten/truncated canonical); evidence retained" % leg)
            if data is not None:
                if hashlib.sha256(data).hexdigest() != prior["digest"]:
                    refuse("staging for leg %s diverges from its published receipt — a leg is never reused with different content (retain + surface)" % leg)
                _fd_retire(staging_fd, staging_name, prior["digest"])
            sys.stdout.write("fold-delegation: no-op leg=%s — receipt verified, canonical bytes intact (already published); retirement converged\n" % leg)
            return
        if prior is not None and prior["state"] == "intent":
            i_off, i_len = int(prior["offset"]), int(prior["length"])
            c_size = cst.st_size if cst is not None else 0
            if i_len == 0:
                # PR-MED-001 (r12): the explicit-zero channel skips canonical
                # creation by design, so an interrupted FIRST-empty publication
                # leaves NO canonical inode (cst is None) — a range-digest read
                # would envfail opening it and block convergence forever.
                # Converge WITHOUT a canonical read: require the empty digest, a
                # consistent zero-length range, and (if staging survives) the
                # empty digest again, then write the one published receipt and
                # retire. Refuse a non-empty digest, an inconsistent offset/size,
                # or a divergent surviving staging — never advance the
                # exactly-once authority on a bad state.
                if prior["digest"] != hashlib.sha256(b"").hexdigest():
                    refuse("intent receipt for leg %s declares length=0 but a non-empty digest — inconsistent zero-length intent (retain + surface)" % leg)
                if c_size != i_off:
                    refuse("canonical is torn against the zero-length intent for leg %s (size %d, expected %d) — reconcile before folding; evidence retained"
                           % (leg, c_size, i_off))
                if data is not None and hashlib.sha256(data).hexdigest() != prior["digest"]:
                    refuse("staging for leg %s diverges from its zero-length intent receipt — never advance to published on a divergent retry (retain + surface)" % leg)
                # receipts exists (a prior intent receipt) — identity-bind the append.
                _fd_receipt_write(log_root_fd, receipts_name, leg, "published", prior["digest"], i_off, 0, int(prior["lines"]), expect_st=rst)
                if data is not None:
                    _fd_retire(staging_fd, staging_name, prior["digest"])
                sys.stdout.write("fold-delegation: converged leg=%s — interrupted zero-length publication completed (no canonical inode by design)\n" % leg)
                return
            if c_size >= i_off + i_len and _fd_range_digest_ok(log_root_fd, canonical_name, i_off, i_len, prior["digest"], expect_st=cst):
                # The append landed; the published receipt/retirement were lost.
                # PR-MED-001: validate the surviving staging against the intent
                # BEFORE the durable `published` transition — a divergent same-leg
                # staging must REFUSE with the receipt stream byte-identical, never
                # advance the exactly-once authority to a terminal state on a merge
                # that returned refusal. A legitimately-absent post-append staging
                # (data is None) still converges on the intent+canonical proof.
                if data is not None and hashlib.sha256(data).hexdigest() != prior["digest"]:
                    refuse("staging for leg %s diverges from its intent receipt after a completed append — never advance to published on a divergent retry (retain + surface)" % leg)
                # receipts exists (a prior intent receipt) — identity-bind the append.
                _fd_receipt_write(log_root_fd, receipts_name, leg, "published", prior["digest"], i_off, i_len, int(prior["lines"]), expect_st=rst)
                if data is not None:
                    _fd_retire(staging_fd, staging_name, prior["digest"])
                sys.stdout.write("fold-delegation: converged leg=%s — interrupted publication completed (receipt + retirement)\n" % leg)
                return
            if c_size != i_off:
                refuse("canonical is torn against the intent receipt for leg %s (size %d, expected %d or %d) — reconcile before folding; evidence retained"
                       % (leg, c_size, i_off, i_off + i_len))
            # size == offset: the append never happened — fall through to a fresh
            # publish (a fresh intent supersedes; nothing was published).
        if data is None:
            refuse("staging channel %s is MISSING and no receipt proves a prior publication — absence is never zero work (r4 PR-HIGH-002: the composer pre-creates the empty channel at the spawn boundary); retain + surface" % staging_name)

        # ---- fresh publication (validate → intent → append → published → retire)
        # Every durable append is identity-bound (PR-HIGH-001 r13): the receipts
        # sidecar is created (rst is None) or bound to its pre-read inode; the
        # intent write returns the sidecar inode (rct) that the published write
        # then binds to; the canonical append is created (cst is None) or bound
        # to its pre-captured inode — a same-directory replacement of either
        # final component between validation and append REFUSES.
        records = validate_delegation_snapshot(data, runkey)
        digest = hashlib.sha256(data).hexdigest()
        offset = cst.st_size if cst is not None else 0
        length = len(data)
        rct = _fd_receipt_write(log_root_fd, receipts_name, leg, "intent", digest, offset, length, records,
                                expect_st=rst, create=(rst is None))
        if length > 0:
            _fd_append_at(log_root_fd, canonical_name, data, "canonical destination",
                          expect_st=cst, create=(cst is None))
        _fd_receipt_write(log_root_fd, receipts_name, leg, "published", digest, offset, length, records,
                          expect_st=rct)
        _fd_retire(staging_fd, staging_name, digest)
        if records == 0:
            sys.stdout.write("fold-delegation: published leg=%s records=0 bytes=0 (explicit empty channel) canonical=%s\n" % (leg, canonical_name))
        else:
            sys.stdout.write("fold-delegation: published leg=%s records=%d bytes=%d canonical=%s\n" % (leg, records, length, canonical_name))
    finally:
        # branch/none aliases base_loops_fd == staging_fd == log_root_fd; the
        # set() closes each unique descriptor exactly once.
        for _fd in set(open_fds):
            try:
                os.close(_fd)
            except OSError:
                pass


def main(argv):
    if argv and argv[0] == "--emit-delegation-variants":
        # PR-LOW-003: the dev/selftest generator — read the schema-owner fixture
        # and print the deterministic embedded block. NOT a runtime path (the
        # embedded literal is authoritative at run time; the fixture is repo-only).
        import json
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "fixtures", "delegation-variants.json"),
                  encoding="utf-8") as f:
            fixture = json.load(f)
        sys.stdout.write(delegation_variants_block(fixture))
        return 0
    sub, etype, flags, roots, kvs, dry_run = parse_argv(argv)
    if sub is None:
        refuse("no subcommand", "emit | escape-check | flush | idle-check | run-close | fold-delegation")
    if sub not in ("emit", "escape-check", "flush", "idle-check", "run-close", "fold-delegation"):
        refuse("unknown subcommand %r" % sub, "emit | escape-check | flush | idle-check | run-close | fold-delegation (exactly six)")
    for req in ("--run", "--role"):
        if req not in flags:
            refuse("%s is REQUIRED on every subcommand" % req,
                   "--run <runkey> --role <role>")
    if not RUNKEY_RE.match(flags["--run"]):
        refuse("--run %r is not a phase-scoped runkey — an iso-id never rides run= (the F-12 domain split)" % flags["--run"],
               "stage-<N>")
    if flags["--role"] not in ENUMS["ROLE_ENUM"]:
        refuse("--role must be one of %s" % ", ".join(sorted(ENUMS["ROLE_ENUM"])))
    if "--epoch" in flags:
        # HIGH-001 (round 5): ONE central owner — no argv-sourced value reaches
        # an emitted line without check_value_safety or a shape regex.
        check_value_safety("epoch", flags["--epoch"])
        # PR-MED-001 (round 9): the central nonblank floor — an epoch identity
        # is an activation id; a blank/whitespace --epoch would emit an
        # oracle-invalid `epoch=""` (empty-epoch) AND fire a spurious notice.
        # Validated here BEFORE any dispatch or side effect, so the pair,
        # standalone NOTIFY, and flush all share one nonblank epoch owner.
        if not flags["--epoch"].strip():
            refuse("--epoch must be a nonblank activation id (empty-epoch) — an invalid epoch causes no journal write and no notice attempt")
    if sub != "emit" and "--event-ts" in flags:
        refuse("--event-ts is admitted on emit ONLY — a computed subcommand's ts= IS its write time (r3-B3)")
    if sub in ("flush", "idle-check") and "--log" not in flags:
        refuse("--log is REQUIRED on %s (it derives from the log; a sink-less invocation is meaningless)" % sub)
    if sub == "run-close" and "--log" not in flags:
        refuse("--log is REQUIRED on run-close (the close record must PERSIST to the probe log — "
               "a stdout-only record dies with the terminal while close side-effects survive; r31 LOW-002)")
    if sub in ("escape-check", "idle-check") and "--log-root" not in flags:
        refuse("--log-root is REQUIRED on %s (r4-B1)" % sub)
    # PR-MED-001 (round 8): TOTAL per-subcommand argv grammar — every accepted
    # token changes behaviour exactly as its documented subcommand says; an
    # irrelevant flag/root/token REFUSES rather than silently disappearing (a
    # `--dry-run`-labelled invocation never reaches a mutating subcommand).
    SUB_GRAMMAR = {
        "emit":         {"flags": {"--run", "--role", "--log", "--epoch", "--event-ts",
                                   "--round", "--id", "--repo"},
                         "roots": False, "kvs": True, "dry_run": False},
        "escape-check": {"flags": {"--run", "--role", "--log", "--log-root",
                                   "--capture", "--leg"},
                         "roots": True, "kvs": False, "dry_run": False},
        "flush":        {"flags": {"--run", "--role", "--log", "--epoch"},
                         "roots": False, "kvs": False, "dry_run": True},
        "idle-check":   {"flags": {"--run", "--role", "--log", "--log-root"},
                         "roots": False, "kvs": False, "dry_run": False},
        "run-close":    {"flags": {"--run", "--role", "--log", "--iso", "--base",
                                   "--outcome", "--plan", "--attest"},
                         "roots": False, "kvs": False, "dry_run": False},
        # v32.2 T2.3: no --log — the receipts sidecar + retirement ARE the
        # durable evidence; the fold writes no probe-log record.
        "fold-delegation": {"flags": {"--run", "--role", "--base", "--iso", "--leg"},
                            "roots": False, "kvs": False, "dry_run": False},
    }
    g = SUB_GRAMMAR[sub]
    for f in flags:
        if f not in g["flags"]:
            refuse("%s is not accepted by `%s` (per-subcommand grammar)" % (f, sub),
                   "`%s` accepts: %s" % (sub, " ".join(sorted(g["flags"]))))
    if roots and not g["roots"]:
        refuse("--root is only accepted by escape-check, not `%s`" % sub)
    if kvs and not g["kvs"]:
        refuse("key=value tokens are only accepted by emit — `%s` got %s"
               % (sub, ", ".join("%s=" % k for k, _ in kvs)))
    if dry_run and not g["dry_run"]:
        refuse("--dry-run is only accepted by flush (its SOLE read-only surface) — it never previews a mutating subcommand (PR-MED-001)")

    sink = open_sink(flags)
    if sub == "emit":
        cmd_emit(flags, etype, kvs, sink)
    elif sub == "escape-check":
        cmd_escape_check(flags, roots, sink)
    elif sub == "flush":
        cmd_flush(flags, dry_run, sink)
    elif sub == "run-close":
        cmd_run_close(flags, sink)
    elif sub == "fold-delegation":
        cmd_fold_delegation(flags)
    else:
        cmd_idle_check(flags, sink)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
