#!/usr/bin/env python3
"""Mechanical full-history Review History checker for /execute-loop (v31.0).

The downstream-valid owner of the F13 half of promotion-patch point 9
(plan-v31-promotion-patch PR-MED-001 + PR-HIGH-002): the canonical
`/execute-loop` composer invokes this exact installed path —

  python3 scripts/loop-history-check.py <plan path>

— at step-3 completion (executor-complete) and on EVERY composer-takeover
path, and stops the loop on a failure. It parses the plan's COMPLETE
`## Review History` section and rejects:

  * duplicate round numbers (one logical round = exactly ONE authoritative
    summary line; the seat that FINISHES a round owns its line — a takeover
    UPDATES the pending entry in place, a resume after a closed round
    allocates the NEXT number),
  * non-monotonic ordering (displayed round numbers must be strictly
    increasing in file order),
  * contradictory duplicate statuses (two same-number entries whose text
    disagrees — the exact defect the run-3 takeover produced, F13).

T18(a2): the SAME single-pass section scan additionally polices the plan's
`## Review Findings Log` round headings (single validation owner — never a
second parser; fence tracking and section bounds are shared):

  * duplicate `### Round N` headings (one round owns ONE heading; leg
    sub-blocks are `####` — the round-31 read-hazard: two `### Round 31`
    headings made the composer dispose from the peer's block),
  * non-monotonic `### Round N` ordering (strictly increasing in file
    order),
  * `####` sub-headings are LEGAL and never count as round headings, even
    when they carry a round number (`#### Round 48 — LEG 1 verified tuples`
    is a leg sub-block, not a duplicate),
  * a duplicate `## Review Findings Log` section (one section owns the log).
    Section ABSENCE stays legal here (unlike Review History's fail-closed
    rule): the guarded defect class is heading collisions WITHIN the log,
    and the History fail-closed rule already proves template presence.

Round-3 R10 (F-16/F-17 — the DIRECTIONAL invariant, codex r1-P5): a CLOSED
or SUPERSEDED Findings-Log round WITH findings REQUIRES its Review History
line (exit 1 when absent — exactly F-17's live miss: run-5's workload plan
jumped `round 4 -> round 8` with finding-bearing Rounds 5/6/7 all Closed and
line-less, and the pre-R10 checker printed BOTH counts and exited 0).
Deliberately NOT two-set equality (PR-HIGH-005/010 — incompatible with real
plan history):
  * History-only rounds are LEGAL (in-session rounds recorded only there);
  * zero-finding Findings-only rounds are LEGAL (a converged confirm);
  * a round carrying a RECOGNIZED in-flight `Round status:` (Open /
    in-progress / pending / ... — the newest in-flight round) is LEGAL
    pending its line; but a finding-bearing round with a MISSING, UNKNOWN,
    decorated (`**Closed**`), or typo'd status is FAIL-CLOSED (subject to
    the invariant — R18's status-less half + R19 PR-MED-002's unknown-token
    half; the exemption keys on a DECLARED, RECOGNIZED non-terminal status,
    never on "not terminal" (which admitted garbage) or on absence, so a
    Closed round that dropped or mistyped its status line cannot escape);
  * a COMPACTED round counts by its surviving `### Round N` digest heading +
    digest bullets (the marker contract keeps headings — compaction is
    census-neutral, r2-B4);
  * plan-peer-review rounds (`Source: ... plan peer-review`) are SUBJECT to
    the invariant;
  * legacy failures are GRANDFATHERED by the EXPLICIT (plan basename, round)
    list below — documented cutoff 2026-07-30; never silently migrated,
    never retroactively rewritten.

Ships as a bootstrap payload (D4 pattern: shipped skill text may only invoke
shipped executables). Stdlib only; python3 everywhere.

Usage:
  python3 scripts/loop-history-check.py <plan.md>   # exit 0 = history OK
  python3 scripts/loop-history-check.py --self-test # embedded fixtures
Exit codes: 0 OK; 1 integrity failure (or failed self-test); 2 usage/IO.

Fail-closed: a plan with NO `## Review History` section fails (exit 1) — the
v22 plan template always carries the section, so its absence on a
loop-governed plan is itself an integrity signal, never a silent pass.
"""

import os
import re
import sys

SECTION_RE = re.compile(r"^## Review History\s*$")
FINDINGS_SECTION_RE = re.compile(r"^## Review Findings Log\s*$")
HEADING_RE = re.compile(r"^## ")
# Summary-line shape: `- 2026-07-28 round 5: ...` / `- 2026-07-28 round 3 (CAP): ...`
ENTRY_RE = re.compile(r"^\s*-\s+(\d{4}-\d{2}-\d{2})\s+round\s+(\d+)\b\s*(.*)$")
# Findings Log round heading (T18a2): EXACTLY `### Round N ...` at heading level 3.
# `####` leg sub-blocks never match — `^### ` requires the space after three
# marker chars, so a fourth `#` fails the match by construction.
ROUND_HEAD_RE = re.compile(r"^### Round (\d+)\b")
# CommonMark fenced-code opener: up to 3 spaces indent, then >=3 of one marker
# char, then an optional info string. PR-MED-025: track (marker_char, length)
# so an inner shorter/opposite delimiter stays content and a >=4-space-indented
# ``` is indented code, not a fence. PR-MED-027: the info-string legality is
# MARKER-SPECIFIC — a backtick fence's info string forbids a backtick, a tilde
# fence's info string allows any character; the marker is parsed first, then the
# marker-specific info rule is applied (see fence_opener).
FENCE_MARKER_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
FENCE_CLOSE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})[ \t]*$")
# R10 (the directional invariant): per-round state parsed from the SAME scan.
# Status values follow the template's `Round status:` line; a finding ITEM is
# either a full `#### <ID>: ...` block heading or a compacted digest bullet
# `- <ID>: ... — <disposition>` (the sidecar-compaction marker contract). The
# ID grammar matches the observed population (PR-HIGH-001 / PR9-MED-001 /
# HIGH-001 / F1-LOW-001 ...): hyphen-joined uppercase-led groups ending in a
# numeric tail. `#### Round N — LEG ...` sub-blocks never match (no numeric
# hyphen tail after an ID-shaped head).
ROUND_STATUS_RE = re.compile(r"^Round status:\s*(\S+)")
# R18/R19: the TERMINAL statuses (subject to the directional invariant) and the
# RECOGNIZED in-flight statuses (exempt, pending their History line). R19
# PR-MED-002: the in-flight exemption keys on a RECOGNIZED status ALLOWLIST, not
# on "any non-terminal token" — an unknown/decorated/typo'd/absent status is
# FAIL-CLOSED (subject), so a Closed round with a mistyped or bold `**Closed**`
# status cannot escape. Tokens are normalized (surrounding markdown emphasis
# stripped, case-folded) before classification. CENSUS-FIRST (2026-08-01): the
# whole-corpus status population is Closed x387 / None x94 / Open x3 /
# **Closed** x2 — the in-flight vocabulary is {open} (synonyms added for
# forward-compat); both **Closed** rounds carry their History lines, so
# tightening adds ZERO new baseline failures.
TERMINAL_STATUSES = frozenset({"closed", "superseded"})
INFLIGHT_STATUSES = frozenset({"open", "in-progress", "in-flight", "pending", "wip"})


def normalize_status(tok):
    """Strip surrounding markdown emphasis (* _) and case-fold a `Round status:`
    token so `**Closed**` / `Closed` / `closed` all classify identically."""
    if tok is None:
        return None
    return tok.strip("*_").lower()
FINDING_BULLET_RE = re.compile(r"^\s*-\s+((?:[A-Z][A-Za-z0-9]*-)+\d+)\s*:")
FINDING_HEAD_RE = re.compile(r"^####\s+((?:[A-Z][A-Za-z0-9]*-)+\d+)\s*:")
# R10 (F-17): the legacy GRANDFATHER list — (plan basename, round) tuples
# predating the directional invariant (documented cutoff 2026-07-30), from
# the r3 sweep + the R10 baseline-table sweep. Explicit and closed: a new
# violating round in ANY plan fails; these exact tuples never do.
GRANDFATHERED = frozenset({
    ("plan-v31-promotion-patch.md", 43),
    ("plan-workflow-v30-program.md", 1),
    ("plan-workflow-v30-program.md", 2),
    ("plan-workflow-v30-program.md", 3),
    ("plan-workflow-v30-program.md", 4),
})


def fence_opener(line):
    """Return (marker_char, opening_length) if `line` is a legal CommonMark
    fenced-code opener, else None. PR-MED-027: apply the info-string rule by
    marker — a backtick opener's info string must contain no backtick; a tilde
    opener's info string may contain anything (backticks included)."""
    m = FENCE_MARKER_RE.match(line)
    if not m:
        return None
    marker, info = m.group(2), m.group(3)
    if marker[0] == "`" and "`" in info:
        return None  # backtick fence info strings forbid a backtick
    return (marker[0], len(marker))


def extract_history(text):
    """Return (entries, findings_rounds, violations) from ONE single-pass scan:
    entries = [(round, date, tail, lineno)] from the `## Review History`
    section; findings_rounds = [(round, lineno, status, finding_count)] from
    the `## Review Findings Log` section's `### Round N` headings (T18a2 —
    same scanner, same fence tracking, same section bounds; never a second
    parser; R10 adds the per-round status + finding-item census on the SAME
    pass). Fenced blocks are skipped everywhere; the template's placeholder
    prose never matches either shape and is ignored (the section's own
    'ignore the placeholder line' rule)."""
    entries, findings_rounds, violations = [], [], []
    in_history = False
    in_findings = False
    history_seen = 0
    findings_seen = 0
    fence = None  # (marker_char, opening_length) while inside a fenced block
    for lineno, line in enumerate(text.splitlines(), 1):
        # Markdown fence state is tracked ACROSS THE WHOLE FILE (PR-MED-020) as a
        # proper CommonMark tuple (PR-MED-025): a fenced `## Review History`
        # example ANYWHERE must not open/duplicate the authoritative section, and
        # only a REAL fence boundary suppresses headings — an inner shorter/
        # opposite delimiter or >=4-space-indented ``` is content, not a fence.
        if fence is not None:
            m = FENCE_CLOSE_RE.match(line)
            if m and m.group(2)[0] == fence[0] and len(m.group(2)) >= fence[1]:
                fence = None
            continue  # inside a fence: never a heading or an entry
        opener = fence_opener(line)
        if opener is not None:
            fence = opener
            continue
        if SECTION_RE.match(line):
            history_seen += 1
            if history_seen > 1:
                violations.append(
                    "line %d: duplicate `## Review History` section — one section owns the history" % lineno)
            in_history, in_findings = True, False
            continue
        if FINDINGS_SECTION_RE.match(line):
            findings_seen += 1
            if findings_seen > 1:
                violations.append(
                    "line %d: duplicate `## Review Findings Log` section — one section owns the log" % lineno)
            in_history, in_findings = False, True
            continue
        if (in_history or in_findings) and HEADING_RE.match(line):
            in_history = in_findings = False
            continue
        if in_history:
            m = ENTRY_RE.match(line)
            if m:
                entries.append((int(m.group(2)), m.group(1), m.group(3).strip(), lineno))
        elif in_findings:
            m = ROUND_HEAD_RE.match(line)
            if m:
                findings_rounds.append([int(m.group(1)), lineno, None, 0])
            elif findings_rounds:
                # R10: status + finding-item census attach to the CURRENT round.
                sm = ROUND_STATUS_RE.match(line)
                if sm:
                    if findings_rounds[-1][2] is None:
                        findings_rounds[-1][2] = sm.group(1)
                elif FINDING_BULLET_RE.match(line) or FINDING_HEAD_RE.match(line):
                    findings_rounds[-1][3] += 1
    if history_seen == 0:
        violations.append("no `## Review History` section found — fail-closed (the v22 template always carries it)")
    # Findings Log ABSENCE stays legal (see module docstring) — only heading
    # collisions/order within a present section are the guarded class.
    return entries, [tuple(fr) for fr in findings_rounds], violations


def check_history(text, plan_name=None):
    """Full-history integrity: returns (entries, findings_rounds, violations)
    — the same three-value contract as extract_history(). Covers the Review
    History summary lines, (T18a2) the Review Findings Log's `### Round N`
    headings from the same scan, and (R10) the DIRECTIONAL invariant: a
    Closed/Superseded finding-bearing Findings-Log round requires its Review
    History line. `plan_name` (the plan's basename) keys the explicit
    GRANDFATHERED legacy exemptions; None = no exemption."""
    entries, findings_rounds, violations = extract_history(text)
    seen = {}
    prev_round = None
    prev_line = None
    for rnd, date, tail, lineno in entries:
        if rnd in seen:
            other_tail, other_line = seen[rnd]
            if tail == other_tail:
                violations.append(
                    "line %d: duplicate round %d (first at line %d) — one logical round has exactly one entry"
                    % (lineno, rnd, other_line))
            else:
                violations.append(
                    "line %d: contradictory duplicate round %d (first at line %d, texts disagree) — "
                    "the F13 class: a takeover updates the pending entry in place, never re-records"
                    % (lineno, rnd, other_line))
        else:
            seen[rnd] = (tail, lineno)
            if prev_round is not None and rnd <= prev_round:
                violations.append(
                    "line %d: round %d out of order after round %d (line %d) — file order must be strictly increasing"
                    % (lineno, rnd, prev_round, prev_line))
        if prev_round is None or rnd > prev_round:
            prev_round, prev_line = rnd, lineno
    fseen = {}
    fprev = None
    fprev_line = None
    for rnd, lineno, _status, _fcount in findings_rounds:
        if rnd in fseen:
            violations.append(
                "line %d: duplicate `### Round %d` heading in the Review Findings Log (first at line %d) — "
                "one round owns one heading; leg sub-blocks are `####` (the round-31 read-hazard class)"
                % (lineno, rnd, fseen[rnd]))
        else:
            fseen[rnd] = lineno
            if fprev is not None and rnd <= fprev:
                violations.append(
                    "line %d: Findings Log `### Round %d` out of order after Round %d (line %d) — "
                    "file order must be strictly increasing"
                    % (lineno, rnd, fprev, fprev_line))
        if fprev is None or rnd > fprev:
            fprev, fprev_line = rnd, lineno
    # R10 (F-16/F-17): the DIRECTIONAL invariant — a Closed/Superseded
    # finding-bearing Findings-Log round REQUIRES its Review History line.
    # History-only rounds, zero-finding rounds, and EXPLICIT in-flight rounds
    # are legal by construction; explicit legacy tuples are grandfathered
    # (cutoff 2026-07-30 — see GRANDFATHERED).
    #
    # R18 PR-MED-001 (status-less half — the LOW-only half was INVALID and the
    # finding-counting is UNTOUCHED): a finding-bearing round with a MISSING or
    # unparseable `Round status:` line is FAIL-CLOSED (subject to the invariant),
    # so a Closed round that dropped BOTH its status line and its History line
    # can no longer silently escape (the run-5 miss was one status-line-deletion
    # from invisible). The EXPLICIT in-flight exemption is preserved: a round
    # carrying a parseable NON-terminal status (e.g. `Round status: Open`) stays
    # legal pending its line — the exemption keys on a DECLARED non-terminal
    # status, never on the ABSENCE of one. CENSUS-FIRST (the R10 baseline-table
    # discipline): measured 17 status-less finding-bearing rounds across the
    # plan corpus (2026-08-01); 16 carry their History lines and pass, the ONE
    # that does not (promotion-patch Round 43) is ALREADY grandfathered — so the
    # fail-closed treatment adds ZERO new baseline failures.
    history_rounds = set(r for r, _d, _t, _l in entries)
    for rnd, lineno, status, fcount in findings_rounds:
        if fcount == 0:
            continue
        _norm = normalize_status(status)
        # R19 PR-MED-002: ONLY a RECOGNIZED in-flight status exempts the round.
        # An unknown/decorated/typo'd/absent status is fail-closed (subject) —
        # the exemption keys on a DECLARED, recognized non-terminal status,
        # never on "not terminal" (which admitted garbage) or on absence.
        if _norm in INFLIGHT_STATUSES:
            continue  # explicit recognized in-flight (e.g. Open) — pending its line
        # terminal / unknown / decorated / typo'd / status-less -> subject.
        if rnd in history_rounds:
            continue
        if plan_name is not None and (plan_name, rnd) in GRANDFATHERED:
            continue
        if status is None:
            _label = "status-less"
        elif _norm in TERMINAL_STATUSES:
            _label = status
        else:
            _label = "unrecognized-status (%r)" % status
        violations.append(
            "line %d: %s finding-bearing Round %d has NO Review History line — "
            "the seat that finishes a round owns its summary line (the directional invariant, F-16/F-17; "
            "run-5's Rounds 5/6/7 are this exact miss; a missing/unrecognized Round status: is fail-closed per R18/R19 PR-MED-001/002)"
            % (lineno, _label, rnd))
    return entries, findings_rounds, violations


# --- embedded fixtures (--self-test) -----------------------------------------

_HEADER = "# Plan\n\n## Review History\nEach /review invocation appends a one-line entry here. Ignore the placeholder line\nwhen counting rounds.\n\n"
_FOOTER = "\n## Review Findings Log\n\n### Round 1 — 2026-07-28\nquoted `- 2026-07-28 round 99: decoy outside the section`\n"

FIXTURES = [
    ("normal-sequence", _HEADER
     + "- 2026-07-27 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-27 round 2: 0/0/0/1; action=none\n"
     + "- 2026-07-28 round 3 (CAP): 0/0/0/0; CONVERGED\n" + _FOOTER, True),
    ("takeover-updates-pending-round", _HEADER
     # The takeover finished round 2 by UPDATING the pending entry in place —
     # the summary level shows exactly one line per round (the legal shape).
     + "- 2026-07-27 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-28 round 2: 0/1/0/0; skew=takeover-closed; action=fix (Source: composer takeover)\n" + _FOOTER, True),
    ("resume-allocates-next-round", _HEADER
     + "- 2026-07-27 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-27 round 2: 0/0/0/0; CONVERGED\n"
     + "- 2026-07-28 round 3: 0/0/1/0; action=fix (Source: resumed session — next number allocated)\n" + _FOOTER, True),
    ("duplicate-same-number", _HEADER
     + "- 2026-07-27 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-27 round 2: 0/0/0/1; action=none\n"
     + "- 2026-07-27 round 2: 0/0/0/1; action=none\n" + _FOOTER, False),
    ("out-of-order", _HEADER
     # The exact live defect PR-HIGH-006 confirmed on this governing plan (1,3,2).
     + "- 2026-07-27 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-28 round 3: 0/2/2/0; action=amend\n"
     + "- 2026-07-28 round 2: 0/1/3/0; action=amend\n" + _FOOTER, False),
    ("contradictory-duplicates", _HEADER
     # The run-3 F13 shape: same round recorded twice with disagreeing content.
     + "- 2026-07-27 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-28 round 2: 0/0/2/0; action=fix\n"
     + "- 2026-07-28 round 2: 0/0/0/0; CONVERGED\n" + _FOOTER, False),
    ("fenced-decoy-ignored", _HEADER
     + "- 2026-07-27 round 1: 0/0/1/0; action=fix\n"
     + "```\n- 2026-07-27 round 1: fenced quoted decoy — never counted\n```\n"
     + "- 2026-07-27 round 2: 0/0/0/0; CONVERGED\n" + _FOOTER, True),
    # PR-MED-020: a fenced `## Review History` example BEFORE the real section
    # (a quoted schema / prior-review excerpt) must not become authoritative.
    ("pre-section-fenced-heading-backtick",
     "# Plan\n\nSchema example:\n```\n## Review History\n- 2026-07-28 round 9: example\n```\n\n"
     + "## Review History\nEach /review invocation appends a one-line entry here.\n\n"
     + "- 2026-07-28 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-28 round 2: 0/0/0/0; CONVERGED\n" + _FOOTER, True),
    ("pre-section-fenced-heading-tilde",
     "# Plan\n\nSchema example:\n~~~\n## Review History\n- 2026-07-28 round 9: example\n~~~\n\n"
     + "## Review History\nEach /review invocation appends a one-line entry here.\n\n"
     + "- 2026-07-28 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-28 round 2: 0/0/0/0; CONVERGED\n" + _FOOTER, True),
    # PR-MED-025: a >=4-space-indented ``` is INDENTED CODE, not a fence opener —
    # the naive toggle wrongly opened a fence and hid the real section ("no
    # section"). A single unbalanced indented ``` must NOT suppress the section.
    ("pre-section-indented-fence",
     "# Plan\n\n    ```\n    indented code sample, one line, no close\n\n"
     + "## Review History\n- 2026-07-28 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-28 round 2: 0/0/0/0; CONVERGED\n" + _FOOTER, True),
    # PR-MED-025: a 4-backtick fence containing a literal 3-backtick line + a
    # quoted `## Review History` — the inner 3-backtick must NOT close the fence
    # (length < opening), so the quoted heading stays content and the REAL
    # history is authoritative.
    ("pre-section-4backtick-fence",
     "# Plan\n\n````\n```\n## Review History\n- 2026-07-28 round 9: quoted example\n````\n\n"
     + "## Review History\n- 2026-07-28 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-28 round 2: 0/0/0/0; CONVERGED\n" + _FOOTER, True),
    # PR-MED-025: an opposite-marker line inside a fence is content, not a close.
    ("opposite-marker-inside-fence",
     "# Plan\n\n```\n~~~\n## Review History\n- 2026-07-28 round 9: quoted\n```\n\n"
     + "## Review History\n- 2026-07-28 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-28 round 2: 0/0/0/0; CONVERGED\n" + _FOOTER, True),
    # PR-MED-027: a TILDE fence's info string may contain backticks — it is a
    # legal opener, so its quoted `## Review History` must stay content and the
    # real history is authoritative.
    ("tilde-fence-with-backtick-info",
     "# Plan\n\n~~~ `inline code` in info\n## Review History\n- 2026-07-28 round 99: quoted\n~~~\n\n"
     + "## Review History\n- 2026-07-28 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-28 round 2: 0/0/0/0; CONVERGED\n" + _FOOTER, True),
    # PR-MED-027: a BACKTICK fence's info string may NOT contain a backtick, so
    # ``` `x` is NOT a valid opener — the following `## Review History` stays a
    # REAL heading, a duplicate of the real one -> REJECT. (No trailing fence
    # marker, which would otherwise become a lone unbalanced opener.)
    ("backtick-fence-with-backtick-info-not-opener",
     "# Plan\n\n``` `x`\n## Review History\n- 2026-07-28 round 9: not fenced (backtick-info is not an opener)\n\n"
     + "## Review History\n- 2026-07-28 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-28 round 2: 0/0/0/0; CONVERGED\n" + _FOOTER, False),
    ("empty-history-fresh-plan", _HEADER + _FOOTER, True),
    ("missing-section", "# Plan\n\n## Goal\nno history section\n", False),
    # --- T18(a2): Review Findings Log round-heading policing --------------------
    # Normal findings log: unique increasing `### Round N` headings with `####`
    # finding/leg sub-blocks between them.
    ("findings-normal-with-legs", _HEADER
     + "- 2026-07-27 round 1: 0/0/1/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 1 — 2026-07-27\n#### F1-LOW-001: a finding\nbody\n"
     + "### Round 2 — 2026-07-27 (peer)\n#### Round 2 — LEG 1 verified tuples\n- tuples\n"
     + "### Round 3 — 2026-07-28\nno findings — converged\n", True),
    # The round-31 read-hazard shape: TWO `### Round 31` headings (peer block +
    # leg-1 block at the same level) — REJECT.
    # (R18: an explicit in-flight status keeps Round 31 out of the directional
    # path — this fixture tests DUPLICATE HEADINGS only; without it the demoted
    # single-Round-31 restore form would trip the status-less fail-closed rule.)
    ("findings-duplicate-round-heading", _HEADER
     + "- 2026-07-27 round 1: 0/0/1/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 31 — peer block\nRound status: Open\n#### PR-MED-052: x\n"
     + "### Round 31 — leg-1 verified block\n- tuples\n", False),
    ("findings-out-of-order", _HEADER
     + "- 2026-07-27 round 1: 0/0/1/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 1 — a\n### Round 3 — b\n### Round 2 — c\n", False),
    # A `####` leg sub-block CARRYING the round number is legal and never counts
    # as a duplicate heading (the round-32 repair shape).
    ("findings-leg-subblock-with-round-number", _HEADER
     + "- 2026-07-27 round 1: 0/0/1/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 48 — peer round\n"
     + "#### Round 48 — LEG 1 verified tuples\n- tuples\n"
     + "#### Round 48 — LEG 2 operator brief\nbrief\n"
     + "### Round 49 — confirmation\n", True),
    # A fenced `### Round` decoy inside the findings section stays content
    # (whole-file fence tracking is shared with the history scan).
    ("findings-fenced-decoy-ignored", _HEADER
     + "- 2026-07-27 round 1: 0/0/1/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 1 — real\n"
     + "```\n### Round 1 — fenced quoted decoy, never counted\n```\n"
     + "### Round 2 — real\n", True),
    ("duplicate-findings-section", _HEADER
     + "- 2026-07-27 round 1: 0/0/1/0; action=fix\n"
     + "\n## Review Findings Log\n\n### Round 1 — a\n"
     + "\n## Review Findings Log\n\n### Round 2 — b\n", False),
    # PR-MED-070: the documented legal-absence branch, pinned green — a Review
    # History WITHOUT any Findings Log section (the pre-v22-log/legacy shape)
    # passes; only History absence is fail-closed.
    ("findings-section-absent-legal", _HEADER
     + "- 2026-07-27 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-27 round 2: 0/0/0/0; CONVERGED\n", True),
    # --- R10: the DIRECTIONAL invariant (F-16/F-17) -----------------------------
    # The run-5 live miss verbatim in shape: History jumps 4 -> 8 while
    # finding-bearing Rounds 5/6/7 are Closed and line-less -> REJECT.
    ("directional-run5-miss-rejected", _HEADER
     + "- 2026-07-30 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-30 round 2: 0/0/0/1; action=none\n"
     + "- 2026-07-30 round 3: 0/1/0/0; action=fix\n"
     + "- 2026-07-30 round 4: 0/0/1/0; action=fix\n"
     + "- 2026-07-31 round 8: 0/0/0/0; CONVERGED\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 5 — 2026-07-30\nRound status: Closed\n#### PR-MED-001: a finding\nbody\n"
     + "### Round 6 — 2026-07-30\nRound status: Closed\n#### PR-LOW-001: b\n"
     + "### Round 7 — 2026-07-30\nRound status: Closed\n#### PR-LOW-002: c\n"
     + "### Round 8 — 2026-07-31\nRound status: Closed\nno findings — converged\n", False),
    # The newest in-flight round (status Open) is legal pending its line.
    ("directional-inflight-open-legal", _HEADER
     + "- 2026-07-30 round 1: 0/0/1/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 1 — 2026-07-30\nRound status: Closed\n#### PR-LOW-001: a\n"
     + "### Round 2 — 2026-07-31\nRound status: Open\n#### PR-MED-001: pending verify\n", True),
    # A zero-finding Closed round (a converged confirm) needs no line.
    ("directional-zero-finding-round-legal", _HEADER
     + "- 2026-07-30 round 1: 0/0/1/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 1 — 2026-07-30\nRound status: Closed\n#### PR-LOW-001: a\n"
     + "### Round 2 — 2026-07-31\nRound status: Closed\nConverged — zero findings.\n", True),
    # Superseded-with-findings is SUBJECT (a superseded round still happened).
    ("directional-superseded-with-findings-rejected", _HEADER
     + "- 2026-07-30 round 1: 0/0/1/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 1 — 2026-07-30\nRound status: Closed\n#### PR-LOW-001: a\n"
     + "### Round 2 — 2026-07-31\nRound status: Superseded\n#### PR-MED-001: superseded finding\n", False),
    # A COMPACTED round counts by its surviving heading + digest bullets and is
    # census-neutral — WITH its History line it passes (r2-B4).
    ("directional-compacted-digest-ok", _HEADER
     + "- 2026-07-30 round 1: 0/2/0/1; action=fix\n"
     + "- 2026-07-30 round 2: 0/1/0/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 1 — 2026-07-30\nRound status: Closed\n"
     + "Compacted 2026-07-31 → findings-sidecar.md — full per-finding blocks live in that sidecar.\n"
     + "- PR-HIGH-001: wrapper census — Applied\n"
     + "- PR-LOW-001: label fix — Applied\n"
     + "### Round 2 — 2026-07-30\nRound status: Closed\n#### PR-HIGH-002: full block\n", True),
    # R18 PR-MED-001 (status-less half): a finding-bearing round with NO
    # `Round status:` line and NO History line is FAIL-CLOSED -> REJECT
    # (the Closed round that dropped its status line, the run-5 miss's twin).
    ("directional-statusless-missing-line-rejected", _HEADER
     + "- 2026-07-30 round 1: 0/0/1/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 1 — 2026-07-30\nRound status: Closed\n#### PR-LOW-001: a\n"
     + "### Round 2 — 2026-07-31\n#### PR-HIGH-001: finding, NO status line, NO history line\n", False),
    # A status-less finding-bearing round WITH its History line passes (the
    # legacy shape — 16 of the 17 measured status-less rounds are exactly this).
    ("directional-statusless-with-line-legal", _HEADER
     + "- 2026-07-30 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-31 round 2: 0/1/0/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 1 — 2026-07-30\nRound status: Closed\n#### PR-LOW-001: a\n"
     + "### Round 2 — 2026-07-31\n#### PR-HIGH-001: legacy status-less round, HAS its history line\n", True),
    # The RECOGNIZED in-flight exemption is preserved: `Round status: Open` with
    # no History line is legal (keys on the DECLARED recognized status).
    ("directional-explicit-open-missing-line-legal", _HEADER
     + "- 2026-07-30 round 1: 0/0/1/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 1 — 2026-07-30\nRound status: Closed\n#### PR-LOW-001: a\n"
     + "### Round 2 — 2026-07-31\nRound status: Open (2 pending)\n#### PR-HIGH-001: in-flight, no line yet\n", True),
    # R19 PR-MED-002: an UNKNOWN status token on a finding-bearing round with no
    # History line is FAIL-CLOSED -> REJECT (garbage no longer buys the in-flight
    # exemption; the run-5 miss was one typo away).
    ("directional-unknown-status-missing-line-rejected", _HEADER
     + "- 2026-07-30 round 1: 0/0/1/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 1 — 2026-07-30\nRound status: Closed\n#### PR-LOW-001: a\n"
     + "### Round 2 — 2026-07-31\nRound status: Frobnicated\n#### PR-HIGH-001: garbage status, no line\n", False),
    # A typo'd Closed (`Closd`) is likewise fail-closed (the observed threat).
    ("directional-typod-closed-missing-line-rejected", _HEADER
     + "- 2026-07-30 round 1: 0/0/1/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 1 — 2026-07-30\nRound status: Closed\n#### PR-LOW-001: a\n"
     + "### Round 2 — 2026-07-31\nRound status: Closd\n#### PR-HIGH-001: typo status, no line\n", False),
    # A DECORATED terminal (`**Closed**`) normalizes to Closed -> subject; WITH
    # its History line it passes (the 2 measured legacy rounds are this shape).
    ("directional-decorated-closed-with-line-legal", _HEADER
     + "- 2026-07-30 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-31 round 2: 0/1/0/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 1 — 2026-07-30\nRound status: Closed\n#### PR-LOW-001: a\n"
     + "### Round 2 — 2026-07-31\nRound status: **Closed**\n#### PR-HIGH-001: decorated terminal, HAS its line\n", True),
    # A recognized synonym (`in-progress`) is exempt like Open.
    ("directional-inprogress-synonym-missing-line-legal", _HEADER
     + "- 2026-07-30 round 1: 0/0/1/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 1 — 2026-07-30\nRound status: Closed\n#### PR-LOW-001: a\n"
     + "### Round 2 — 2026-07-31\nRound status: in-progress\n#### PR-HIGH-001: recognized in-flight synonym\n", True),
]

# One-variable mutation flips: each (name, broken, restored) pair must flip.
MUTATION_FLIPS = [
    ("dup-removed-restores-green", FIXTURES[3][1],
     FIXTURES[3][1].replace("- 2026-07-27 round 2: 0/0/0/1; action=none\n- 2026-07-27 round 2:",
                            "- 2026-07-27 round 2:", 1)),
    ("order-swap-restores-green", FIXTURES[4][1],
     FIXTURES[4][1].replace("round 3: 0/2/2/0; action=amend", "round TMP", 1)
     .replace("round 2: 0/1/3/0; action=amend", "round 3: 0/2/2/0; action=amend", 1)
     .replace("round TMP", "round 2: 0/1/3/0; action=amend", 1)),
    # PR-MED-020: unfencing the schema example makes its heading a REAL
    # duplicate section (broken=REJECT); the fenced original is green.
    ("pre-section-fence-removed-becomes-real-dup",
     FIXTURES[7][1].replace("```\n## Review History\n- 2026-07-28 round 9: example\n```\n",
                            "## Review History\n- 2026-07-28 round 9: example\n", 1),
     FIXTURES[7][1]),
    # PR-MED-025: unfencing the 4-backtick schema block makes its quoted
    # `## Review History` a REAL duplicate before the real one (broken=REJECT);
    # the properly-fenced original is green.
    ("4backtick-unfenced-becomes-real-dup",
     FIXTURES[10][1].replace(
         "````\n```\n## Review History\n- 2026-07-28 round 9: quoted example\n````\n",
         "## Review History\n- 2026-07-28 round 9: quoted example\n", 1),
     FIXTURES[10][1]),
    # PR-MED-027: swapping the tilde opener for a backtick opener with a backtick
    # in its info string makes it an INVALID opener (and removing the now-orphan
    # close) -> the quoted heading becomes a real duplicate (broken=REJECT); the
    # legal tilde-info original is green.
    ("tilde-to-backtick-info-invalidates-opener",
     FIXTURES[12][1].replace("~~~ `inline code` in info\n", "``` `inline code`\n", 1)
                    .replace("- 2026-07-28 round 99: quoted\n~~~\n", "- 2026-07-28 round 99: quoted\n\n", 1),
     FIXTURES[12][1]),
    # PR-MED-045: the F13 contradictory-duplicate class (same round number, two
    # entries whose texts disagree) is REJECT; collapsing the pending line so one
    # authoritative round entry remains (the takeover updates in place, never
    # re-records) restores OK. This is the sixth recorded history mutation flip —
    # the direct mutation proof for the contradictory-duplicate fixture.
    ("contradictory-duplicate-collapsed-restores-green",
     FIXTURES[5][1],
     FIXTURES[5][1].replace("- 2026-07-28 round 2: 0/0/2/0; action=fix\n", "", 1)),
    # --- T18(a2) flips: one variable each ----------------------------------------
    # The round-31 repair itself: DEMOTING the second `### Round 31` heading to a
    # `####` leg sub-block restores green (the round-32 repair shape).
    ("findings-dup-demoted-to-leg-restores-green",
     FIXTURES[17][1],
     FIXTURES[17][1].replace("### Round 31 — leg-1 verified block",
                             "#### Round 31 — LEG 1 verified tuples", 1)),
    ("findings-order-swap-restores-green",
     FIXTURES[18][1],
     FIXTURES[18][1].replace("### Round 3 — b\n### Round 2 — c\n",
                             "### Round 2 — c\n### Round 3 — b\n", 1)),
    # PROMOTING a legal `####` leg sub-block to `###` creates the round-31
    # duplicate (broken=REJECT); the legal original is green.
    ("leg-subblock-promotion-becomes-dup",
     FIXTURES[19][1].replace("#### Round 48 — LEG 1 verified tuples",
                             "### Round 48 — LEG 1 verified tuples", 1),
     FIXTURES[19][1]),
    # Unfencing the findings decoy makes it a REAL duplicate `### Round 1`
    # (broken=REJECT); the fenced original is green.
    ("findings-decoy-unfenced-becomes-dup",
     FIXTURES[20][1].replace("```\n### Round 1 — fenced quoted decoy, never counted\n```\n",
                             "### Round 1 — unfenced, now a real duplicate\n", 1),
     FIXTURES[20][1]),
    # PR-MED-070: collapsing the duplicate Findings-Log section to ONE
    # authoritative section (its rounds fold under the first) restores green —
    # the single-owner guard's one-variable restore counterpart.
    ("duplicate-findings-section-collapsed-restores-green",
     FIXTURES[21][1],
     FIXTURES[21][1].replace("\n## Review Findings Log\n\n### Round 2 — b\n",
                             "\n### Round 2 — b\n", 1)),
    # --- R10 flips: the directional invariant, one variable each ----------------
    # Writing the owed History line restores green (the F-16 repair shape).
    ("directional-missing-line-added-restores-green",
     FIXTURES[26][1],
     FIXTURES[26][1].replace("- 2026-07-30 round 1: 0/0/1/0; action=fix\n",
                             "- 2026-07-30 round 1: 0/0/1/0; action=fix\n"
                             "- 2026-07-31 round 2: 0/1/0/0; action=none (Source: superseded peer round)\n", 1)),
    # Demoting the terminal status to Open (a genuinely in-flight round)
    # restores green — the invariant binds TERMINAL rounds only.
    ("directional-status-open-restores-green",
     FIXTURES[26][1],
     FIXTURES[26][1].replace("Round status: Superseded", "Round status: Open", 1)),
    # R18 PR-MED-001: adding the owed History line restores green for the
    # status-less fail-closed round.
    ("statusless-missing-line-added-restores-green",
     FIXTURES[28][1],
     FIXTURES[28][1].replace("- 2026-07-30 round 1: 0/0/1/0; action=fix\n",
                             "- 2026-07-30 round 1: 0/0/1/0; action=fix\n"
                             "- 2026-07-31 round 2: 0/1/0/0; action=none\n", 1)),
    # R18 PR-MED-001: declaring an explicit in-flight status on the status-less
    # round also restores green (the exemption keys on the DECLARED status).
    ("statusless-declared-open-restores-green",
     FIXTURES[28][1],
     FIXTURES[28][1].replace(
         "### Round 2 — 2026-07-31\n#### PR-HIGH-001: finding, NO status line, NO history line",
         "### Round 2 — 2026-07-31\nRound status: Open\n#### PR-HIGH-001: now explicitly in-flight", 1)),
    # R19 PR-MED-002: correcting a typo'd/unknown status to a recognized
    # in-flight status restores green (the allowlist gate).
    ("unknown-status-corrected-to-open-restores-green",
     FIXTURES[31][1],
     FIXTURES[31][1].replace("Round status: Frobnicated", "Round status: Open", 1)),
    # R19 PR-MED-002: adding the owed History line also restores green for the
    # typo'd-Closed round (fail-closed terminal + line).
    ("typod-closed-line-added-restores-green",
     FIXTURES[32][1],
     FIXTURES[32][1].replace("- 2026-07-30 round 1: 0/0/1/0; action=fix\n",
                             "- 2026-07-30 round 1: 0/0/1/0; action=fix\n"
                             "- 2026-07-31 round 2: 0/1/0/0; action=none\n", 1)),
]


def self_test():
    failed = 0
    # PR-MED-045: the executable proof surface must equal the recorded matrix
    # count; a silent removal fails here. T18(a2) extends the T6b-recorded 16/6
    # with the Findings Log rows (22/10); the round-52 PR-MED-070 fix adds the
    # legal-absence fixture + the duplicate-section restore flip (23/11);
    # round-3 R10 adds the directional-invariant rows: 28 fixtures /
    # 13 mutation flips; R18 PR-MED-001's status-less half adds 4 fixtures /
    # 2 flips: 31 fixtures / 15 mutation flips; R19 PR-MED-002 (unknown-status
    # half) adds 4 fixtures / 2 flips: 35 fixtures / 17 mutation flips.
    if len(FIXTURES) != 35:
        failed += 1
        print("FAIL  fixture-count: recorded matrix is 35, got %d" % len(FIXTURES))
    if len(MUTATION_FLIPS) != 17:
        failed += 1
        print("FAIL  flip-count: recorded matrix is 17, got %d" % len(MUTATION_FLIPS))
    for name, text, expect_ok in FIXTURES:
        _, _, violations = check_history(text)
        ok = not violations
        status = "PASS" if ok == expect_ok else "FAIL"
        if ok != expect_ok:
            failed += 1
        print("%s  %-40s expected %s got %s" % (status, name, "OK" if expect_ok else "REJECT", "OK" if ok else "REJECT"))
        if ok != expect_ok:
            for v in violations:
                print("      " + v)
    for name, broken, restored in MUTATION_FLIPS:
        _, _, bv = check_history(broken)
        _, _, rv = check_history(restored)
        flipped = bool(bv) and not rv
        if not flipped:
            failed += 1
        print("%s  mutation-flip %-24s broken=%s restored=%s" % ("PASS" if flipped else "FAIL", name,
              "REJECT" if bv else "OK", "OK" if not rv else "REJECT"))
    print("self-test: %s" % ("OK" if not failed else "%d failed" % failed))
    return failed == 0


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    if argv[1] == "--self-test":
        return 0 if self_test() else 1
    try:
        with open(argv[1], encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print("history-check: cannot read %s: %s" % (argv[1], e))
        return 2
    entries, findings_rounds, violations = check_history(text, plan_name=os.path.basename(argv[1]))
    if violations:
        print("history-check: %s: %d round entries, %d findings-log round heading(s), %d violation(s):"
              % (argv[1], len(entries), len(findings_rounds), len(violations)))
        for v in violations:
            print("  " + v)
        return 1
    print("history-check: %s: %d round entries + %d findings-log round heading(s), unique + strictly increasing — OK"
          % (argv[1], len(entries), len(findings_rounds)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
