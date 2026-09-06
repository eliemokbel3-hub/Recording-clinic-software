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

v32 TB.6 (PR-MED-012 rebaseline): the checks above are PRESERVATION /
regression coverage — the genuinely NEW integrity gates are:

  * the NUL-byte scan (BOTH modes): any U+0000 in the plan text fails —
    the historical escape is the kount ledger-run NUL bytes that rode a
    plan file through every text-shaped check (census 2026-08-11: 161 plan
    files across all three corpora, zero NULs — the gate adds zero baseline
    failures);
  * the PHASE-CLOSE no-Open-rounds gate (`--phase-close`): a Findings-Log
    round still carrying a RECOGNIZED in-flight `Round status:` (Open /
    in-progress / ...) fails AT PHASE CLOSE — the run-7 escape: a phase
    closed to commit while a round was still Open. Mid-phase, an Open round
    stays fully legal (the directional invariant's in-flight exemption is
    untouched — default-mode fixtures stay green); the loop's close
    contract invokes this mode BEFORE the phase's commit record — the gate
    is a COMPOSER duty on every close path (r31 MED-001: the Phase E close
    helper does NOT invoke this checker);
  * the COMPACTED-DIGEST integrity gate (BOTH modes; r35 H4 peer; r36pre
    TOTAL): every compacted round (a `Compacted … → <sidecar>` marker line)
    is validated against its sidecar round block by ID-SET EQUALITY — an
    unavailable sidecar, a missing round block, missing digest bullets
    (partial digests), unknown digest bullets, and duplicate digest bullets
    ALL fail. The historical escape: every pre-r35 em-dash-form digest
    bullet (`- <ID> — …`) was invisible to `FINDING_BULLET_RE` (canonical
    colon-form `- <ID>: file:line — title — decision: …`), so all 29
    compacted rounds in the live plan parsed to zero findings — and the
    r35 zero-parse-only gate still skipped duplicate/partial shapes once
    anything parsed (the r36 peer's probes). A genuinely zero-count
    compacted round (sidecar block with no findings) stays legal.

v32 TF.1 (PR-MED-012 rebaseline, peer-loop): the ROUND CENSUS — the
mechanical owner of `/peer-loop`'s post-spawn appended-round assertion (the
prose rule existed and was bypassed in practice; four live no-round-append
peer exits in the v32 run alone — three integrity-gate withheld appends and
a refusal-exit pair):

  * `--round-census`: after the standard integrity checks pass, print ONE
    deterministic census line —
    `ROUND-CENSUS plan=<basename> findings_max=<K> history_max=<H> history_rounds=<n> findings_rounds=<m>`
    — where `findings_max` (the ASSERTION AUTHORITY) is the highest
    `### Round N` heading in the Findings Log and `history_max` is the
    highest Review History round (INFORMATIONAL ONLY — it never drives the
    assertion; both 0 when their section has no rounds). The authority is
    the ALLOCATION DOMAIN (r29 PR-HIGH-024): `/review`'s canonical round
    allocation is Findings-Log-max + 1 — never a History number — so a
    LEGAL zero-count History-only converged line (History max ahead of
    Findings max) must never inflate the baseline above what the next
    canonically-allocated append can satisfy. The orchestrator captures
    `findings_max` BEFORE every peer spawn as the baseline.
  * `--expect-new-round-since <N>` (census implied): after the spawn, exit 0
    ONLY when `findings_max > N`. An unchanged census (`NO-NEW-ROUND`) exits
    1: the round is INCONCLUSIVE — a withheld append (the peer's
    pair-integrity gate held its write) and a refusal/error exit leave the
    SAME disk shape, so the classification is exit-reason-independent —
    never converged, never zero-findings, never stalemate. A peer that
    appended a DUPLICATE round number fails the standard integrity checks
    first (exit 1) — an unincremented round aborts the same way.
    Fail-closed: census over a corrupt history is meaningless, so any
    violation exits 1 before the census line prints.

Usage:
  python3 scripts/loop-history-check.py <plan.md>   # exit 0 = history OK
  python3 scripts/loop-history-check.py --phase-close <plan.md>
                                                    # + the no-Open-rounds gate
  python3 scripts/loop-history-check.py --round-census <plan.md>
                                                    # + the ROUND-CENSUS line
  python3 scripts/loop-history-check.py --expect-new-round-since N <plan.md>
                                                    # post-spawn assertion
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
# r35 H4: the compaction marker (template-canonical text starts exactly this
# way) — captures the sidecar filename the round's full blocks moved to.
COMPACTED_MARKER_RE = re.compile(r"^Compacted \d{4}-\d{2}-\d{2} → (\S+)")
# r35 H4: sidecar finding entries — full `#### <ID>: …` blocks (FINDING_HEAD_RE)
# plus the observed one-line shapes: `- **[SEV]** ID: …`, `- **[SEV] ID: …`
# (the round-13 live form — the closing `**` sits at the END of the line, so
# it is fully optional here; r36pre), `- ID: …`, and the bare `- ID — …`.
# LEG-tuple reference bullets reuse IDs, so counting is by UNIQUE ID per round.
SIDECAR_ONELINE_RE = re.compile(
    r"^- (?:\*\*\[(?:CRIT|HIGH|MED|LOW)\](?:\*\*)? )?((?:[A-Z][A-Za-z0-9]*-)+\d+)(?:\*\*)?\s*(?::| —)")
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
    """Return (entries, findings_rounds, violations, compacted) from ONE
    single-pass scan: entries = [(round, date, tail, lineno)] from the
    `## Review History` section; findings_rounds = [(round, lineno, status,
    finding_count)] from the `## Review Findings Log` section's `### Round N`
    headings (T18a2 — same scanner, same fence tracking, same section bounds;
    never a second parser; R10 adds the per-round status + finding-item
    census on the SAME pass; r35 H4 adds compacted = [(round, lineno,
    sidecar_name)] for rounds carrying a compaction marker, same pass).
    Fenced blocks are skipped everywhere; the template's placeholder prose
    never matches either shape and is ignored (the section's own 'ignore the
    placeholder line' rule). r36pre: digest_ids maps round -> [bullet IDs in
    file order, duplicates preserved] for the total compacted-digest gate.
    Returns (entries, findings_rounds, violations, compacted, digest_ids)."""
    entries, findings_rounds, violations = [], [], []
    compacted = []
    digest_ids = {}
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
                cm = None if sm else COMPACTED_MARKER_RE.match(line)
                if sm:
                    if findings_rounds[-1][2] is None:
                        findings_rounds[-1][2] = sm.group(1)
                elif cm:
                    compacted.append((findings_rounds[-1][0], lineno, cm.group(1)))
                else:
                    bm = FINDING_BULLET_RE.match(line)
                    hm = None if bm else FINDING_HEAD_RE.match(line)
                    if bm or hm:
                        findings_rounds[-1][3] += 1
                        if bm:
                            digest_ids.setdefault(
                                findings_rounds[-1][0], []).append(bm.group(1))
    if history_seen == 0:
        violations.append("no `## Review History` section found — fail-closed (the v22 template always carries it)")
    # Findings Log ABSENCE stays legal (see module docstring) — only heading
    # collisions/order within a present section are the guarded class.
    return entries, [tuple(fr) for fr in findings_rounds], violations, compacted, digest_ids


def sidecar_round_ids(sidecar_text, round_num):
    """r35 H4 (r36pre: returns the ID SET for the total gate): the UNIQUE
    finding IDs in the sidecar's `### Round N` block (full `####` heads + the
    one-line shapes; LEG-tuple bullets reuse IDs, so uniqueness dedupes them).
    Returns None when the sidecar has no block for the round (a partial
    sidecar — the caller fails closed). Fence-aware with the same CommonMark
    tuple rule as the main scan."""
    ids, in_round, fence = set(), False, None
    for line in sidecar_text.splitlines():
        if fence is not None:
            m = FENCE_CLOSE_RE.match(line)
            if m and m.group(2)[0] == fence[0] and len(m.group(2)) >= fence[1]:
                fence = None
            continue
        opener = fence_opener(line)
        if opener is not None:
            fence = opener
            continue
        m = ROUND_HEAD_RE.match(line)
        if m:
            if in_round:
                break
            in_round = int(m.group(1)) == round_num
            continue
        if in_round and (line.startswith("## ") or line.startswith("### ")):
            break
        if in_round:
            m = FINDING_HEAD_RE.match(line) or SIDECAR_ONELINE_RE.match(line)
            if m:
                ids.add(m.group(1))
    if not in_round and not ids:
        # never entered the round's block at all
        return None
    return ids


def check_history(text, plan_name=None, phase_close=False, sidecars=None):
    """Full-history integrity: returns (entries, findings_rounds, violations)
    — the same three-value contract as extract_history(). Covers the Review
    History summary lines, (T18a2) the Review Findings Log's `### Round N`
    headings from the same scan, and (R10) the DIRECTIONAL invariant: a
    Closed/Superseded finding-bearing Findings-Log round requires its Review
    History line. `plan_name` (the plan's basename) keys the explicit
    GRANDFATHERED legacy exemptions; None = no exemption. v32 TB.6:
    `phase_close=True` additionally fails any round still carrying a
    RECOGNIZED in-flight status (the no-Open-rounds gate — the run-7
    open-round-past-phase-close escape); the NUL-byte scan runs in BOTH
    modes (the ledger NUL-bytes escape — corruption is never mode-scoped).
    r35 H4 (r36pre: TOTAL): `sidecars` maps sidecar filename -> text for the
    compacted-digest integrity gate (BOTH modes). When sidecar texts are
    supplied, EVERY compacted round is validated against its sidecar block by
    ID-SET EQUALITY — an unavailable sidecar, a missing round block, missing
    digest bullets (partial digests), unknown digest bullets, and duplicate
    digest bullets ALL fail. sidecars=None (a text-only caller) runs the
    text-local duplicate check plus the r35 zero-parse fail-closed rule only
    — main() and the compacted self-test matrix always supply texts, so the
    CLI path is always total."""
    entries, findings_rounds, violations, compacted, digest_ids = extract_history(text)
    # r35 H4 / r36pre: the compacted-digest integrity gate — the historical
    # escape is the pre-r35 em-dash digest form, invisible to
    # FINDING_BULLET_RE, which made every compacted round census as zero
    # findings; the r36 peer's residual probes showed the zero-parse-only
    # gate skipped duplicate and partial-digest shapes once anything parsed.
    for _rnd, _lineno, _name in compacted:
        _ids = digest_ids.get(_rnd, [])
        _dups = sorted(set(i for i in _ids if _ids.count(i) > 1))
        if _dups:
            violations.append(
                "line %d: compacted Round %d carries duplicate digest bullet(s) %s — one finding, "
                "one digest line (stale duplicates; r36pre)" % (_lineno, _rnd, ", ".join(_dups)))
        if sidecars is None:
            if not _ids:
                violations.append(
                    "line %d: Round %d is compacted to %s but no sidecar text is available and its "
                    "digest bullets parse to ZERO findings — digest completeness cannot be verified "
                    "(fail-closed, r35 H4)" % (_lineno, _rnd, _name))
            continue
        _sc = sidecars.get(_name)
        if _sc is None:
            violations.append(
                "line %d: Round %d is compacted to %s but the sidecar is unavailable/unreadable — "
                "digest completeness cannot be verified (fail-closed, r35 H4)" % (_lineno, _rnd, _name))
            continue
        _scids = sidecar_round_ids(_sc, _rnd)
        if _scids is None:
            violations.append(
                "line %d: Round %d is compacted to %s but the sidecar has no `### Round %d` block — "
                "a partial sidecar is an error, never 'no findings' (r35 H4)" % (_lineno, _rnd, _name, _rnd))
            continue
        _missing = sorted(_scids - set(_ids))
        _extra = sorted(set(_ids) - _scids)
        if _missing:
            violations.append(
                "line %d: compacted Round %d is missing digest bullet(s) for sidecar finding(s) %s — "
                "partial digests (canonical form `- <ID>: file:line — title — decision: ...`; r36pre total gate)"
                % (_lineno, _rnd, ", ".join(_missing)))
        if _extra:
            violations.append(
                "line %d: compacted Round %d digest bullet(s) %s have no sidecar finding — stale/unknown "
                "digests (r36pre total gate)" % (_lineno, _rnd, ", ".join(_extra)))
    # v32 TB.6: the NUL-byte scan — a U+0000 anywhere in the plan text is
    # file corruption that rides through every text-shaped check (the kount
    # ledger-run escape). Reported once with the first offending line number.
    if "\x00" in text:
        _nul_line = text[:text.index("\x00")].count("\n") + 1
        violations.append(
            "line %d: NUL byte (U+0000) in the plan text — file corruption; "
            "a plan carrying NULs is never integrity-OK (the ledger-run escape, v32 TB.6)" % _nul_line)
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
    # v32 TB.6 (PR-MED-012): the PHASE-CLOSE no-Open-rounds gate — at a phase
    # boundary no Findings-Log round may still carry a RECOGNIZED in-flight
    # status (the run-7 escape: a phase closed to commit over an Open round).
    # Keyed on the SAME recognized-in-flight allowlist the directional
    # invariant exempts, so the two rules partition cleanly: mid-phase an Open
    # round is legal pending its line; at close it is the violation. Zero-
    # finding in-flight rounds fail too — an open round is open regardless of
    # whether its findings landed yet.
    if phase_close:
        for rnd, lineno, status, _fcount in findings_rounds:
            if normalize_status(status) in INFLIGHT_STATUSES:
                violations.append(
                    "line %d: Round %d is still `Round status: %s` at PHASE CLOSE — no Open/in-flight "
                    "round may cross a phase boundary (close the round or record its terminal state "
                    "before the phase's commit record; the run-7 open-round-past-phase-close escape, v32 TB.6)"
                    % (lineno, rnd, status))
    return entries, findings_rounds, violations


def round_census(entries, findings_rounds):
    """v32 TF.1 (authority per r29 PR-HIGH-024): the deterministic round
    census — (findings_max, history_max, history_rounds, findings_rounds
    counts). `findings_max` — the highest `### Round N` heading in the
    Findings Log — is the ASSERTION AUTHORITY because it is the ALLOCATION
    DOMAIN: `/review`'s canonical rule mints the next round from the
    Findings-Log max alone, and a peer's append always lands a Round block
    there (an in-flight `Round status: Open` block with no History line is
    a landed round). `history_max` is reported INFORMATIONALLY and never
    drives the assertion — a legal zero-count History-only converged line
    would otherwise inflate the baseline above what the next
    canonically-allocated append can satisfy (the reproduced false abort).
    Both maxima are 0 when their section has no rounds."""
    history_max = 0
    for r, _d, _t, _l in entries:
        if r > history_max:
            history_max = r
    findings_max = 0
    for r, _l, _s, _f in findings_rounds:
        if r > findings_max:
            findings_max = r
    return findings_max, history_max, len(entries), len(findings_rounds)


def check_new_round(text, baseline, plan_name=None, phase_close=False, sidecars=None):
    """v32 TF.1: the post-spawn appended-round assertion — the ONE code path
    both the CLI and the self-test fixtures run. Returns
    (census, violations): the standard integrity checks run first
    (fail-closed — census over a corrupt history is meaningless, and a
    duplicate/unincremented round number is caught HERE, aborting the round
    the same way); then, when `baseline` is not None,
    `findings_max > baseline` is asserted (the allocation-domain authority,
    r29 PR-HIGH-024 — History numbers never drive it). The NO-NEW-ROUND
    violation classifies the peer round INCONCLUSIVE regardless of how the
    peer exited: a withheld append and a refusal/error exit leave the same
    disk shape."""
    entries, findings_rounds, violations = check_history(
        text, plan_name=plan_name, phase_close=phase_close, sidecars=sidecars)
    census = round_census(entries, findings_rounds)
    if not violations and baseline is not None and census[0] <= baseline:
        violations.append(
            "NO-NEW-ROUND: findings_max=%d, baseline=%d — no round appended since the peer spawn; "
            "classify the peer round INCONCLUSIVE (a withheld append and a refusal/error exit "
            "both leave this shape — never converged, zero-findings, or stalemate; v32 TF.1)"
            % (census[0], baseline))
    return census, violations


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
    # --- v32 TB.6: the NUL-byte scan (both modes) -------------------------------
    # The ledger-run escape: a NUL rides plan text through every text-shaped
    # check. Census 2026-08-11: 161 plan files across all three corpora, zero
    # NULs — zero baseline failures added.
    ("nul-byte-rejected", _HEADER
     + "- 2026-07-27 round 1: 0/0/1/0; action=fix\n\x00\n" + _FOOTER, False),
]

# --- v32 TB.6: the PHASE-CLOSE no-Open-rounds gate (phase_close=True) --------
# RED/GREEN baseline by construction: the escape text IS the default-mode
# green fixture `directional-inflight-open-legal` (the pre-v32 behaviour —
# an Open round is legal MID-PHASE), re-evaluated under --phase-close where
# it must REJECT (the run-7 open-round-past-phase-close escape).
_FX_BY_NAME = dict((n, t) for n, t, _e in FIXTURES)
_PC_OPEN_ESCAPE = _FX_BY_NAME["directional-inflight-open-legal"]
_PC_OPEN_CLOSED = (_PC_OPEN_ESCAPE
                   .replace("Round status: Open", "Round status: Closed", 1)
                   .replace("- 2026-07-30 round 1: 0/0/1/0; action=fix\n",
                            "- 2026-07-30 round 1: 0/0/1/0; action=fix\n"
                            "- 2026-07-31 round 2: 0/1/0/0; action=fix\n", 1))
PHASE_CLOSE_FIXTURES = [
    # The run-7 escape shape: green mid-phase (see the default-mode fixture),
    # REJECT at phase close.
    ("pc-run7-open-round-rejected", _PC_OPEN_ESCAPE, False),
    # Closing the round (+ its owed History line) makes the close legal.
    ("pc-all-rounds-closed-ok", _PC_OPEN_CLOSED, True),
    # Every recognized in-flight synonym is equally an open round at close.
    ("pc-inprogress-synonym-rejected",
     _PC_OPEN_ESCAPE.replace("Round status: Open", "Round status: in-progress", 1), False),
    # A ZERO-finding Open round is still an open round — the gate keys on the
    # declared status, not the finding count.
    ("pc-zero-finding-open-round-rejected", _HEADER
     + "- 2026-07-30 round 1: 0/0/1/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 1 — 2026-07-30\nRound status: Closed\n#### PR-LOW-001: a\n"
     + "### Round 2 — 2026-07-31\nRound status: Open\nno findings logged yet\n", False),
    # A status-less legacy round WITH its History line is not "open" — the
    # gate fires on RECOGNIZED in-flight statuses only.
    ("pc-statusless-legacy-with-line-ok", _HEADER
     + "- 2026-07-30 round 1: 0/0/1/0; action=fix\n"
     + "- 2026-07-31 round 2: 0/1/0/0; action=fix\n"
     + "\n## Review Findings Log\n\n"
     + "### Round 1 — 2026-07-30\nRound status: Closed\n#### PR-LOW-001: a\n"
     + "### Round 2 — 2026-07-31\n#### PR-HIGH-001: legacy status-less round, HAS its history line\n", True),
]
# The phase-close red/green mutation flip: closing the Open round (one
# variable: status + its owed line) restores green under --phase-close.
PHASE_CLOSE_FLIPS = [
    ("pc-open-round-closed-restores-green", _PC_OPEN_ESCAPE, _PC_OPEN_CLOSED),
]

# --- v32 TF.1: the peer-loop post-spawn ROUND-CENSUS assertion ---------------
# RED baseline replays the observed no-round-output shape (kpm-wp-embed r15
# "exhausted-peer-exits-0": the peer process exits with the plan unchanged —
# no round appended; the v32 run reproduced the class live FOUR times: the
# round-9/17/21 peers withheld their appends on integrity gates, and the
# round-25/26 first attempts died on safety refusals) through the REAL
# post-spawn path — check_new_round, the same function the CLI runs. A
# withheld append and a refusal exit leave the SAME disk shape, so the two
# red fixtures share one after-text and must BOTH classify INCONCLUSIVE —
# never converged, zero-findings, or stalemate.
_CENSUS_BEFORE = (_HEADER
    + "- 2026-08-01 round 1: 0/0/1/0; action=fix\n"
    + "- 2026-08-02 round 2: 0/0/0/0; CONVERGED\n"
    + "\n## Review Findings Log\n\n"
    + "### Round 1 — 2026-08-01\nRound status: Closed\n#### PR-MED-001: a\n")
_CENSUS_AFTER_BOTH = (_CENSUS_BEFORE.replace(
    "- 2026-08-02 round 2: 0/0/0/0; CONVERGED\n",
    "- 2026-08-02 round 2: 0/0/0/0; CONVERGED\n"
    "- 2026-08-03 round 3: 0/0/1/0; action=fix\n", 1)
    + "### Round 3 — 2026-08-03\nRound status: Closed\n#### PR-MED-002: b\n")
_CENSUS_AFTER_FINDINGS_ONLY = (_CENSUS_BEFORE
    + "### Round 3 — 2026-08-03\nRound status: Open\n#### PR-MED-002: b\n")
_CENSUS_AFTER_DUP_NUMBER = (_CENSUS_BEFORE
    + "### Round 1 — 2026-08-03\nRound status: Closed\n#### PR-MED-002: duplicate number\n")
# r29 PR-HIGH-024: the ALLOCATION-DOMAIN divergence pair — a LEGAL zero-count
# History-only converged line (History max 3, Findings max 2 — the live
# plan's History-28/Findings-27 shape, which every zero-count in-session
# confirmation round produces) followed by the CANONICALLY-ALLOCATED next
# append (`/review`: Findings max 2 + 1 = 3). Under the retired union-max
# authority this exact pair REPRODUCED the false abort (leg-1 tuple,
# 2026-08-12); under the findings_max authority it is the GREEN fixture.
_CENSUS_DIV_BEFORE = (_HEADER
    + "- 2026-08-01 round 1: 0/0/1/0; action=fix\n"
    + "- 2026-08-02 round 2: 0/0/1/0; action=fix\n"
    + "- 2026-08-03 round 3: 0/0/0/0; CONVERGED\n"
    + "\n## Review Findings Log\n\n"
    + "### Round 1 — 2026-08-01\nRound status: Closed\n#### PR-MED-001: a\n"
    + "### Round 2 — 2026-08-02\nRound status: Closed\n#### PR-MED-002: b\n")
_CENSUS_DIV_AFTER = (_CENSUS_DIV_BEFORE
    + "### Round 3 — 2026-08-04\nRound status: Open\n#### PR-MED-003: the canonically-allocated peer round\n")
# (name, before_text, after_text, expect_pass) — each fixture's baseline is
# MEASURED from its before-text through the same real path in self_test
# (never hardcoded), exactly as the orchestrator captures it pre-spawn.
CENSUS_FIXTURES = [
    # Green: the peer appended round 3 to both sections.
    ("census-green-round-appended-both", _CENSUS_BEFORE, _CENSUS_AFTER_BOTH, True),
    # Green: a Findings-only `Round status: Open` block IS a landed round —
    # the authority is the Findings side, so the in-flight legal shape passes.
    ("census-green-findings-only-open", _CENSUS_BEFORE, _CENSUS_AFTER_FINDINGS_ONLY, True),
    # Green (r29 PR-HIGH-024 — the leg-1 false-abort repro, now the fix's
    # proof): History max ahead of Findings max via a legal zero-count
    # History-only converged line, then the canonically-allocated append —
    # findings_max 2 -> 3 passes; the History number never drives it.
    ("census-green-history-ahead-canonical", _CENSUS_DIV_BEFORE, _CENSUS_DIV_AFTER, True),
    # Red: withheld append — the peer's integrity gate held its write; the
    # plan is byte-unchanged (the r9/r17/r21 shape).
    ("census-red-withheld-append", _CENSUS_BEFORE, _CENSUS_BEFORE, False),
    # Red: refusal exit — same unchanged disk shape as the withheld append
    # (the r25/26 attempt-1 shape); the classification is exit-reason-
    # independent BY CONSTRUCTION (identical after-text, identical verdict).
    ("census-red-refusal-exit", _CENSUS_BEFORE, _CENSUS_BEFORE, False),
    # Red: withheld/refusal on the History-ahead divergence shape — the
    # allocation-domain authority still catches a genuinely-absent append.
    ("census-red-no-output-on-divergence", _CENSUS_DIV_BEFORE, _CENSUS_DIV_BEFORE, False),
    # Red: an appended block REUSING an existing round number is an
    # unincremented round — the standard integrity checks abort it first.
    ("census-red-duplicate-number-append", _CENSUS_BEFORE, _CENSUS_AFTER_DUP_NUMBER, False),
]
# The census red/green mutation flips: one variable — the appended round —
# flips the no-round-output abort to a clean pass (both on the plain shape
# and on the r29 History-ahead divergence shape).
CENSUS_FLIPS = [
    ("census-append-restores-green", _CENSUS_BEFORE, _CENSUS_BEFORE, _CENSUS_AFTER_BOTH),
    ("census-div-append-restores-green", _CENSUS_DIV_BEFORE, _CENSUS_DIV_BEFORE, _CENSUS_DIV_AFTER),
]

# r35 H4: the compacted-digest matrix — (name, plan_text, sidecars_dict,
# expect_ok). The RED baseline replays the live escape: pre-r35 em-dash
# digest bullets (`- <ID> — …`) are invisible to FINDING_BULLET_RE, so the
# round censuses as zero findings while its sidecar holds the blocks.
_CD_SIDECAR_TWO = ("# Review Findings — sidecar\n\n"
                   "### Round 1 — 2026-07-30\n"
                   "#### PR-HIGH-001: `a.py:1` — first finding\n- /fix decision: Applied\n"
                   "#### PR-LOW-001: `b.py:2` — second finding\n- /fix decision: Applied\n")
_CD_SIDECAR_ZERO = ("# Review Findings — sidecar\n\n"
                    "### Round 1 — 2026-07-30\nConverged — zero findings.\n")
_CD_PLAN_CANON = (_HEADER
                  + "- 2026-07-30 round 1: 0/1/0/1; action=fix\n"
                  + "\n## Review Findings Log\n\n"
                  + "### Round 1 — 2026-07-30\nRound status: Closed\n"
                  + "Compacted 2026-07-31 → findings-cd.md — full per-finding blocks live in that sidecar; "
                  + "treat a missing or partial sidecar as an error, never as \"no findings\".\n"
                  + "- PR-HIGH-001: `a.py:1` — first finding — decision: Applied\n"
                  + "- PR-LOW-001: `b.py:2` — second finding — decision: Applied\n")
_CD_PLAN_EMDASH = _CD_PLAN_CANON.replace(
    "- PR-HIGH-001: `a.py:1` — first finding — decision: Applied\n"
    "- PR-LOW-001: `b.py:2` — second finding — decision: Applied\n",
    "- PR-HIGH-001 — first finding — decision: Applied\n"
    "- PR-LOW-001 — second finding — decision: Applied\n")
_CD_PLAN_ZERO = (_HEADER
                 + "- 2026-07-30 round 1: 0/0/0/0; action=converged\n"
                 + "\n## Review Findings Log\n\n"
                 + "### Round 1 — 2026-07-30\nRound status: Closed\n"
                 + "Compacted 2026-07-31 → findings-cd.md — full per-finding blocks live in that sidecar; "
                 + "treat a missing or partial sidecar as an error, never as \"no findings\".\n")
_CD_SIDE = {"findings-cd.md": _CD_SIDECAR_TWO}
COMPACTED_FIXTURES = [
    # Green: canonical colon-form digests parse — census sees the findings.
    ("compacted-canonical-digests-parse", _CD_PLAN_CANON, _CD_SIDE, True),
    # Red (the live escape): em-dash digests parse to zero while the sidecar
    # holds two blocks.
    ("compacted-emdash-digests-rejected", _CD_PLAN_EMDASH, _CD_SIDE, False),
    # Red: zero-parse round with NO sidecar available — fail-closed.
    ("compacted-sidecar-unavailable-rejected", _CD_PLAN_EMDASH, {}, False),
    # Red: sidecar present but missing the round's block — partial sidecar.
    ("compacted-partial-sidecar-rejected", _CD_PLAN_ZERO,
     {"findings-cd.md": "# Review Findings — sidecar\n\n### Round 9 — 2026-07-30\nother round\n"}, False),
    # Green: a genuinely zero-count compacted round (sidecar block empty).
    ("compacted-zero-count-round-legal", _CD_PLAN_ZERO,
     {"findings-cd.md": _CD_SIDECAR_ZERO}, True),
    # r36pre probe A: a stale DUPLICATE digest bullet beside the two canonical
    # ones (the live round-15 residual shape) — total gate rejects.
    ("compacted-duplicate-digest-rejected",
     _CD_PLAN_CANON + "- PR-HIGH-001: `a.py:1` — first finding, stale duplicate — decision: Applied\n",
     _CD_SIDE, False),
    # r36pre probe B: PARTIAL digests — one sidecar finding has no digest
    # bullet; the sidecar entry uses the round-13 bold `**[SEV] ID:` live form,
    # so this fixture ALSO pins the r36pre regex fix (the missing ID must be
    # COUNTED to be reported missing).
    ("compacted-partial-digests-rejected",
     _CD_PLAN_CANON.replace("- PR-LOW-001: `b.py:2` — second finding — decision: Applied\n", ""),
     {"findings-cd.md": ("# Review Findings — sidecar\n\n### Round 1 — 2026-07-30\n"
                         "#### PR-HIGH-001: `a.py:1` — first finding\n- /fix decision: Applied\n"
                         "- **[LOW] PR-LOW-001: `b.py:2` — second finding, bold one-line form.**\n")},
     False),
    # r36pre probe C: an UNKNOWN digest bullet with no sidecar finding behind
    # it — total gate rejects.
    ("compacted-unknown-digest-rejected",
     _CD_PLAN_CANON + "- PR-MED-099: `c.py:3` — phantom finding — decision: Applied\n",
     _CD_SIDE, False),
]
# One-variable flip: restoring the canonical digest bullets flips the
# em-dash RED back to green over the SAME sidecar.
COMPACTED_FLIPS = [
    ("compacted-digest-form-restores-green", _CD_SIDE, _CD_PLAN_EMDASH, _CD_PLAN_CANON),
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
    # v32 TB.6: removing the NUL byte restores green (the ledger-run escape's
    # direct red/green pair — corruption in, corruption out).
    ("nul-byte-removed-restores-green",
     FIXTURES[35][1],
     FIXTURES[35][1].replace("\x00\n", "", 1)),
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
    # half) adds 4 fixtures / 2 flips: 35 fixtures / 17 mutation flips;
    # v32 TB.6 adds the NUL-byte fixture + flip (36/18) and the phase-close
    # matrix (5 fixtures / 1 flip, counted separately below).
    if len(FIXTURES) != 36:
        failed += 1
        print("FAIL  fixture-count: recorded matrix is 36, got %d" % len(FIXTURES))
    if len(MUTATION_FLIPS) != 18:
        failed += 1
        print("FAIL  flip-count: recorded matrix is 18, got %d" % len(MUTATION_FLIPS))
    if len(PHASE_CLOSE_FIXTURES) != 5:
        failed += 1
        print("FAIL  pc-fixture-count: recorded matrix is 5, got %d" % len(PHASE_CLOSE_FIXTURES))
    if len(PHASE_CLOSE_FLIPS) != 1:
        failed += 1
        print("FAIL  pc-flip-count: recorded matrix is 1, got %d" % len(PHASE_CLOSE_FLIPS))
    # v32 TF.1 (r29 PR-HIGH-024 extension): the round-census matrix
    # (7 fixtures / 2 flips, counted separately like the phase-close matrix).
    if len(CENSUS_FIXTURES) != 7:
        failed += 1
        print("FAIL  census-fixture-count: recorded matrix is 7, got %d" % len(CENSUS_FIXTURES))
    if len(CENSUS_FLIPS) != 2:
        failed += 1
        print("FAIL  census-flip-count: recorded matrix is 2, got %d" % len(CENSUS_FLIPS))
    # r35 H4 + r36pre: the compacted-digest matrix (8 fixtures / 1 flip,
    # counted separately like the phase-close and census matrices).
    if len(COMPACTED_FIXTURES) != 8:
        failed += 1
        print("FAIL  cd-fixture-count: recorded matrix is 8, got %d" % len(COMPACTED_FIXTURES))
    if len(COMPACTED_FLIPS) != 1:
        failed += 1
        print("FAIL  cd-flip-count: recorded matrix is 1, got %d" % len(COMPACTED_FLIPS))
    for name, text, side, expect_ok in COMPACTED_FIXTURES:
        _, _, violations = check_history(text, sidecars=side)
        cd_ok = not violations
        status = "PASS" if cd_ok == expect_ok else "FAIL"
        if cd_ok != expect_ok:
            failed += 1
        print("%s  %-40s expected %s got %s" % (status, name, "OK" if expect_ok else "REJECT", "OK" if cd_ok else "REJECT"))
        if cd_ok != expect_ok:
            for v in violations:
                print("      " + v)
    for name, side, broken, restored in COMPACTED_FLIPS:
        _, _, bv = check_history(broken, sidecars=side)
        _, _, rv = check_history(restored, sidecars=side)
        flipped = bool(bv) and not rv
        if not flipped:
            failed += 1
        print("%s  mutation-flip %-24s broken=%s restored=%s" % ("PASS" if flipped else "FAIL", name,
              "REJECT" if bv else "OK", "OK" if not rv else "REJECT"))
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
    # v32 TB.6: the phase-close matrix runs with phase_close=True; the RED
    # baseline linkage is asserted explicitly — the escape text is GREEN in
    # default mode (the pre-v32 behaviour) and REJECTS only at phase close.
    _, _, _mid = check_history(_PC_OPEN_ESCAPE)
    if _mid:
        failed += 1
        print("FAIL  pc-red-baseline: the escape text must stay GREEN mid-phase (default mode)")
    else:
        print("PASS  pc-red-baseline: escape text green mid-phase, gate fires only at --phase-close")
    for name, text, expect_ok in PHASE_CLOSE_FIXTURES:
        _, _, violations = check_history(text, phase_close=True)
        pc_ok = not violations
        status = "PASS" if pc_ok == expect_ok else "FAIL"
        if pc_ok != expect_ok:
            failed += 1
        print("%s  %-40s expected %s got %s" % (status, name, "OK" if expect_ok else "REJECT", "OK" if pc_ok else "REJECT"))
        if pc_ok != expect_ok:
            for v in violations:
                print("      " + v)
    for name, broken, restored in PHASE_CLOSE_FLIPS:
        _, _, bv = check_history(broken, phase_close=True)
        _, _, rv = check_history(restored, phase_close=True)
        flipped = bool(bv) and not rv
        if not flipped:
            failed += 1
        print("%s  mutation-flip %-24s broken=%s restored=%s" % ("PASS" if flipped else "FAIL", name,
              "REJECT" if bv else "OK", "OK" if not rv else "REJECT"))
    # v32 TF.1: the round-census matrix runs through the REAL post-spawn path
    # (check_new_round — the same function the CLI runs). Each fixture's
    # baseline is MEASURED from its before-text through that path, never
    # hardcoded — exactly the orchestrator's pre-spawn capture. The two
    # explicit baseline assertions pin the AUTHORITY choice (r29
    # PR-HIGH-024): the plain shape reads findings_max=1, and the
    # History-ahead divergence shape reads findings_max=2 / history_max=3
    # CLEANLY (the live plan's History-28/Findings-27 shape — a baseline the
    # retired union-max authority would have inflated to 3).
    _c_census, _c_v = check_new_round(_CENSUS_BEFORE, None)
    if _c_v or _c_census[0] != 1 or _c_census[1] != 2:
        failed += 1
        print("FAIL  census-baseline: before-text expected clean findings_max=1 history_max=2, got findings_max=%d history_max=%d violations=%d"
              % (_c_census[0], _c_census[1], len(_c_v)))
    else:
        print("PASS  census-baseline: before-text clean, findings_max=1 history_max=2 measured through the real path")
    _cd_census, _cd_v = check_new_round(_CENSUS_DIV_BEFORE, None)
    if _cd_v or _cd_census[0] != 2 or _cd_census[1] != 3:
        failed += 1
        print("FAIL  census-div-baseline: divergence before-text expected clean findings_max=2 history_max=3, got findings_max=%d history_max=%d violations=%d"
              % (_cd_census[0], _cd_census[1], len(_cd_v)))
    else:
        print("PASS  census-div-baseline: History-ahead shape clean, authority findings_max=2 (history_max=3 informational)")
    for name, before, after, expect_ok in CENSUS_FIXTURES:
        _b_census, _b_v = check_new_round(before, None)
        if _b_v:
            failed += 1
            print("FAIL  %-40s before-text must be clean to measure a baseline" % name)
            continue
        _, cv = check_new_round(after, _b_census[0])
        c_ok = not cv
        status = "PASS" if c_ok == expect_ok else "FAIL"
        if c_ok != expect_ok:
            failed += 1
        print("%s  %-40s expected %s got %s" % (status, name, "OK" if expect_ok else "REJECT", "OK" if c_ok else "REJECT"))
        if c_ok != expect_ok:
            for v in cv:
                print("      " + v)
    for name, before, broken, restored in CENSUS_FLIPS:
        _b_census, _b_v = check_new_round(before, None)
        if _b_v:
            failed += 1
            print("FAIL  mutation-flip %-24s before-text must be clean to measure a baseline" % name)
            continue
        _, bv = check_new_round(broken, _b_census[0])
        _, rv = check_new_round(restored, _b_census[0])
        flipped = bool(bv) and not rv
        if not flipped:
            failed += 1
        print("%s  mutation-flip %-24s broken=%s restored=%s" % ("PASS" if flipped else "FAIL", name,
              "REJECT" if bv else "OK", "OK" if not rv else "REJECT"))
    print("self-test: %s" % ("OK" if not failed else "%d failed" % failed))
    return failed == 0


def main(argv):
    args = list(argv[1:])
    phase_close = False
    census_flag = False
    expect_since = None
    if "--phase-close" in args:
        phase_close = True
        args.remove("--phase-close")
    if "--round-census" in args:
        census_flag = True
        args.remove("--round-census")
    if "--expect-new-round-since" in args:
        i = args.index("--expect-new-round-since")
        try:
            expect_since = int(args[i + 1])
        except (IndexError, ValueError):
            print(__doc__)
            return 2
        if expect_since < 0:
            print(__doc__)
            return 2
        del args[i:i + 2]
        census_flag = True  # the assertion implies the census line
    if len(args) != 1:
        print(__doc__)
        return 2
    if args[0] == "--self-test":
        return 0 if self_test() else 1
    try:
        with open(args[0], encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print("history-check: cannot read %s: %s" % (args[0], e))
        return 2
    plan_name = os.path.basename(args[0])
    # r35 H4: load every marker-named sidecar beside the plan for the
    # compacted-digest gate. Unreadable files are simply absent from the dict
    # — check_history fails closed on any zero-parse round that needs them.
    sidecars = {}
    plan_dir = os.path.dirname(os.path.abspath(args[0]))
    for _name in set(COMPACTED_MARKER_RE.match(l).group(1)
                     for l in text.splitlines() if COMPACTED_MARKER_RE.match(l)):
        try:
            with open(os.path.join(plan_dir, _name), encoding="utf-8") as f:
                sidecars[_name] = f.read()
        except OSError:
            pass
    # v32 TF.1: ALL CLI paths run through check_new_round — with no baseline
    # it is exactly the standard checks + census, so the pre-census behaviour
    # is unchanged and the self-test fixtures prove the same path the CLI runs.
    census, violations = check_new_round(
        text, expect_since, plan_name=plan_name, phase_close=phase_close,
        sidecars=sidecars)
    mode = " [phase-close]" if phase_close else ""
    if violations:
        print("history-check%s: %s: %d round entries, %d findings-log round heading(s), %d violation(s):"
              % (mode, args[0], census[2], census[3], len(violations)))
        for v in violations:
            print("  " + v)
        return 1
    if census_flag:
        print("ROUND-CENSUS plan=%s findings_max=%d history_max=%d history_rounds=%d findings_rounds=%d"
              % (plan_name, census[0], census[1], census[2], census[3]))
        if expect_since is not None:
            print("NEW-ROUND OK: findings_max=%d > baseline=%d" % (census[0], expect_since))
    print("history-check%s: %s: %d round entries + %d findings-log round heading(s), unique + strictly increasing — OK"
          % (mode, args[0], census[2], census[3]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
