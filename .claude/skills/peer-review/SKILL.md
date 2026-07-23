---
name: peer-review
description: Perform an independent second-agent review in a separate session by validating prior review findings against the code, checking for downstream breakage, and looking for anything the first review missed. Shared Cursor/Codex/Claude Code workflow; invoke as /peer-review in Cursor or Claude Code, or $peer-review in Codex.
disable-model-invocation: false
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/peer-review` in Cursor or Claude Code, or `$peer-review` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

This workflow reads and writes the same `.cursor/plans/` files as Cursor and Claude Code, so no copy-paste handoff is needed when switching tools.

Treat this as an independent peer review in a separate agent session. By default, `/peer-review` auto-detects what to review from the active plan and disk — no manual paste is required. The six Step 0 sub-steps below establish inputs and emit a confirmation summary; only when auto-detect cannot proceed (no plan / no Findings Log) or the user opts out does the 3-option fallback menu fire.

## Step 0 — Auto-detect plan, findings, and changed files

1. **Find the active plan.** Look in `.cursor/plans/` for `plan-*.md` files, excluding anything under `.cursor/plans/completed/`. If exactly one plan exists, use it. If multiple plans exist, prefer the one with the most recent `Last plan sync` timestamp in its `Current State / Handoff Note`. If no plan file is found, fall through to the Step 0 fallback menu below and skip the remaining sub-steps.

2. **Read the latest applicable Findings Log round.** Locate the most recent round block in the plan's `Review Findings Log` section. If that round's `Source:` field is `Cursor peer-review`, `Claude Code peer-review`, or `Codex peer-review` — or a plan peer-review value (`Cursor plan peer-review`, `Claude Code plan peer-review`, or `Codex plan peer-review`; plan-scoped rounds written by the headless plan-review variant of the non-interactive contract below) — skip back to the most recent `/review`-class round instead — peer-review's job is to validate `/review`-class output, not to re-review other peer-reviews, and a plan peer-review round is never a code-validate target. A `/review`-class round is any round whose `Source:` is a `/review` (or `$review`) run OR a propose-only reviewer that writes `/review`-compatible findings: `… simplify` and `… security-review` rounds (carrying `SIMP-`/`SEC-` IDs) ARE `/review`-class and are valid targets to validate; only `… peer-review` rounds (which by construction includes `… plan peer-review`) are skipped. For each finding in the targeted round, read the severity / title / location header, the structured per-finding fields (`Triage:`, `Fix route:`, `Why it matters:`, `Current behaviour:`, `Desired behaviour:`, `Pattern to follow:`, `Pattern siblings:`, `Invariant:`, `Verification:`, `Regression risk:`, `Scope-expansion disposition:`), and the per-finding `/fix decision:`, `/fix notes:`, `/fix date:`, `/fix applied by:` fields. If the plan has no `Review Findings Log` section, the section contains only a `(no findings logged yet)` placeholder, or its only rounds are `… plan peer-review` rounds (plan-scoped critique does not make the plan "already reviewed"), this is a pre-execution (or not-yet-reviewed) plan — set **mode = plan review** (see `## Mode — plan review vs code review` below) rather than treating it as an error. The Step 0 fallback menu (sub-step 6) stays available, so the user can instead pick a code review of working-tree changes (option 3).

3. **Read the plan body for context.** From the plan file, read `Goal`, `Design Decisions`, `Critical Constraints`, `Files / Symbols Involved` (under `Key Findings`), `Validation / Verification`, `Current State / Handoff Note`, and `Review History`. These set the reference frame for the review — pattern matches, invariants, in-scope vs out-of-scope work, and what prior reviews already found.

4. **Discover changed files on disk.** Run `git status --short` and `git diff --name-only HEAD`. If the plan's `Files / Symbols Involved` lists explicit files, filter the changed-files list to that set; otherwise show all changed files. **Cross-tool prerequisite:** when `/peer-review` runs in a different tool than the one that ran `/review` (e.g. Cursor `/review` → Claude Code `/peer-review`, Codex `$review` → Cursor `/peer-review`, or any other cross-tool pairing across Cursor / Claude Code / Codex), all tools must point at the same working directory on disk for uncommitted changes to be visible. If the tools sit on separate clones or worktrees, commit and push first, or use the paste fallback (option 2 of the menu below).

5. **Auto-fire the model-diversity warning when same-tool same-model is detected.** Read the targeted round's `Source:` field. If `Source: Cursor` and this `/peer-review` is running in Cursor, OR `Source: Claude Code` and this `/peer-review` is running in Claude Code, OR `Source: Codex` and this `/peer-review` is running in Codex, surface the model-diversity expectation prominently — see the `## Model-diversity expectation (v22)` section below for the full warning text. The warning fires automatically here instead of relying on the user to volunteer model information; the user can override and proceed anyway after seeing it. If the `Source:` indicates a cross-tool run, mark model-diversity OK and continue silently — but note Codex defaults to GPT-5.x (same model family as Cursor's default), so cross-tool Cursor ↔ Codex peer-review delivers the tool diversity but not the cross-family gain; Claude Code is the stronger cross-family pairing for either.

6. **Emit the confirmation summary and proceed prompt.** Print:
   - Mode: code review (a targetable `/review`-class round present) / plan review (no Findings Log, or only plan peer-review rounds — pre-execution plan)
   - Plan: `<plan filename>` (or `none — falling through to menu`)
   - Target round: round N from `<YYYY-MM-DD>` (or `no targetable round — plan-review mode`)
   - Findings counts: X CRIT / X HIGH / X MED / X LOW; `/fix decision` breakdown (P Pending / A Applied / etc.) — `n/a` in plan-review mode
   - Changed files: N files (list inline if ≤5; otherwise state the count and offer to expand)
   - Model-diversity: OK (cross-tool) / WARNING (same-tool — see warning below) / n/a (plan-review mode)

   Then ask: `Proceed with auto-detected inputs? (y / show menu)`. If the user types `show menu` or otherwise declines, switch to the Step 0 fallback menu below.

## Step 0 fallback — 3-option menu (when auto-detect fails or user opts out)

Fires when Step 0 sub-step 1 finds no plan, or sub-step 6 receives `show menu` (or a decline) from the user. A plan with no Findings Log round (or whose only rounds are `… plan peer-review` rounds) does NOT auto-fire this menu — it enters plan-review mode per sub-step 2; the user reaches this menu from plan-review mode by choosing `show menu` at sub-step 6 (e.g. to run a code review of working-tree changes via option 3). Present the three options below and wait for an explicit choice; whichever option the user picks, hand off cleanly into Steps 1–4 with the input it produced.

1. **Describe what you want reviewed.** The user types a one-line description of what was built or what to look at. Treat the description as the scope brief for Steps 1–4; there is no Findings Log baseline, so Step 2 (Validate the provided findings) becomes a no-op — skip directly to Step 3 (independent pass for missed issues) and Step 4 (downstream breakage). Useful when no plan or no prior `/review` exists yet.

2. **Paste a `/review` output from another agent.** The user pastes the full `/review` output — this is the legacy manual-paste flow. Treat the paste as the Step 2 baseline and validate each finding against the actual code per Steps 1–4 as previously written. Useful when the prior `/review` ran outside this repo (e.g. external reviewer, a different machine, or a session whose plan file is unreachable from here).

3. **Read the changed files directly.** Run `git status --short` and `git diff --name-only HEAD` (same as Step 0 sub-step 4). If a plan file exists but its `Review Findings Log` is empty or absent, additionally use the plan's `Files / Symbols Involved` to filter the discovered list to plan-relevant files. Hand the resulting changed-files list to Steps 1–4 as the scope; Step 2 becomes a no-op (no prior findings) and Steps 3–4 run against the discovered files. Useful when a plan exists but `/review` was not run before `/peer-review`, or when the user wants a fresh independent pass against working-tree changes.

## Non-interactive headless contract (invoked by /peer-loop)

`/peer-loop` (and any future headless composer) runs this skill non-interactively in a single-shot headless CLI (`claude -p …`, `codex exec …`) that cannot answer mid-run prompts. To activate the contract, the composer places the exact sentinel token **`PEER_LOOP_NONINTERACTIVE`** as the invocation prompt's CONTROL HEADER — its first nonblank line. Only the control header selects the mode: the accepted header shapes are exactly `PEER_LOOP_NONINTERACTIVE` or `PEER_LOOP_NONINTERACTIVE PEER_LOOP_PLAN_REVIEW`, and token text appearing anywhere ELSE in the prompt (quoted, discussed, or in scope/context prose) is inert content that never changes the mode. This token is the single source of truth for the headless flag — `/peer-loop` passes it verbatim; do not rename it in one place only. When no control header is present, this skill behaves exactly as the interactive sections above describe (this is what keeps interactive `/peer-review` unchanged — including when the prompt merely mentions a token in passing).

A second mode token **`PEER_LOOP_PLAN_REVIEW`** may be passed ALONGSIDE `PEER_LOOP_NONINTERACTIVE` on that same control-header line (same verbatim-pass rule; never renamed independently). The token truth table is TOTAL, read from the control header alone: both tokens on the header = headless PLAN review (the token-gated variant in points 4–5 below); `PEER_LOOP_NONINTERACTIVE` alone = headless CODE review (the default contract as written); no control header = interactive (the sections above); a header carrying `PEER_LOOP_PLAN_REVIEW` WITHOUT the sentinel is INVALID — refuse loudly with a precise error naming the missing sentinel and write NOTHING (an interactive plan review remains this skill's own `## Mode — plan review vs code review` path, invoked directly, never via the loop token).

When (and only when) `PEER_LOOP_NONINTERACTIVE` leads the control header, apply the 5-point contract below, overriding the interactive Step 0 / Handoff behaviour (validated over 4 fresh headless peer runs in the v27 Stage 4 keystone spike):

1. **Suppress the Step 0 sub-step 6 proceed prompt** (`Proceed with auto-detected inputs? (y / show menu)`) — do not wait for input; proceed directly with the composer-supplied scope.
2. **Suppress the Step 0 sub-step 5 model-diversity warning** — the composer already enforces cross-family (the peer family differs from the live executor's), so the warning is redundant headless.
3. **Force path (b)** (always write findings to the `Review Findings Log`) — skip the `## Handoff — choose your path` (a)/(b) choice; there is no live chat to paste into. Append a new Round block per path (b).
4. **Force a fresh review of the composer-supplied scope, in the token-selected mode.** Without `PEER_LOOP_PLAN_REVIEW` (the default): force a fresh CODE review — review the specific changed files + plan path passed in the invocation, reading those files directly. Do not enter plan-review mode even when the Findings Log is empty, and do not target a stale prior round — always review the current (post-fix) code. This avoids the two traps the interactive auto-detect would otherwise hit: (i) an empty Findings Log routing into plan-review mode; (ii) a later loop iteration targeting the stale prior round instead of the post-fix code (`Step 0 sub-step 2`). With `PEER_LOOP_PLAN_REVIEW`: force a fresh PLAN review of the composer-supplied plan path instead — critique the plan itself across the `## Mode — plan review vs code review` lenses; scope is plan-only and the escape baseline is plan-file-only (the peer touches nothing but the plan file); the headless variant WRITES its plan findings as a normal Findings Log round per path (b) — the interactive-mode "Do NOT write plan findings" rule is explicitly scoped to interactive runs and does not apply under this token.
5. **Set the correct mode-distinct `Source:` attribution** for the tool this peer actually ran in, per path (b) — never hardcode Cursor. Code mode: `Cursor peer-review` / `Claude Code peer-review` / `Codex peer-review`. Plan-review mode (`PEER_LOOP_PLAN_REVIEW`): `Cursor plan peer-review` / `Claude Code plan peer-review` / `Codex plan peer-review` — the mode-distinct value marks the round plan-scoped for every downstream consumer (`/fix` excludes it; the owning planning session applies it).

Severity labels are non-deterministic across headless peer runs, so the composer converges on finding **presence/verification**, not exact severity counts.

## Model-diversity expectation (v22)

`/peer-review` is meant to catch issues the original `/review` missed because the original review was tunnel-visioned, anchored on its own findings, or shared the executor's blind-spot profile. To deliver on that, this command should run on a **different model family** from the one that ran the original `/review` — not just a different tool.

Recommended pairings:
- Original `/review` ran on Claude Opus (in Claude Code or via Cursor) → run this `/peer-review` on Cursor with **GPT 5.4 high/xhigh**, or as `$peer-review` in Codex on GPT-5.x. Either is cross-family from Opus.
- Original `/review` ran on Cursor with GPT 5.4 → run this `/peer-review` in Claude Code on **Opus 4.7**.
- Original `$review` ran in Codex on GPT-5.x → run this `/peer-review` in Claude Code on **Opus 4.7** for cross-family catch-rate. (Codex defaults to GPT-5.x, same family as Cursor; cross-family path is Claude Code.)

Same-model-family fallback (e.g. /review on Opus → /peer-review on Opus in a different tool) is acceptable only when the cross-family option is unavailable. Tool-only diversity does NOT deliver the catch-rate gain peer-review is designed for — the same model in a different tool keeps the same blind spots.

If the user does not state which model produced the original /review, ask. Mismatched diversity (e.g. both Opus) is not a blocker, but the user should know peer-review's value is reduced in that case.

## Mode — plan review vs code review

`/peer-review` runs in one of two modes, auto-detected in Step 0:

- **Code review** (default when a `/review`-sourced Findings Log round
  exists) — validate the prior `/review` findings and independently
  re-review the changed code. Steps 1–4, Finding Verification (Step 5),
  the Output format, and the `/fix` handoff below all apply as written.
- **Plan review** (default when the plan has no Findings Log round — a
  pre-execution or not-yet-reviewed plan) — independently critique the
  *plan itself* before it is executed, then hand findings back to the
  planner / `/review-plan`, NOT to `/fix`.

A plan that is mid-execution but never `/review`-ed lands in plan-
review mode by default; if the user actually wants a code review of the
working-tree changes, they pick fallback option 3 (Read the changed
files directly) from the Step 0 menu.

### Plan-review mode — what to critique

Read the plan file in full plus `AGENTS.md` and the actual code the
plan names in `Files / Symbols Involved` (judge feasibility against the
real codebase, not the plan's description of it). Then run the
independent critique across these named lenses:

- **Coverage** — does the task list actually deliver the `Goal` and
  every item in `Agreed Scope`? Name gaps and goal-implied work the
  plan never lists.
- **Practicality / feasibility / sequencing** — are the steps buildable
  as written and in a safe order? Flag steps that depend on later
  steps, underspecified steps, or steps that will not survive contact
  with the named code.
- **Unstated assumptions** — what must be true for the plan to work
  that it never states or verifies? Test the plan's own `Accepted
  Assumptions` against the code — are any actually false?
- **Simpler / safer alternatives** — is there a materially simpler or
  lower-risk approach that still meets the `Goal`? Propose it
  concretely.
- **Missing verification / rollback / migration** — does the plan have
  a real `Validation / Verification` story, and (where relevant) a
  rollback and a migration / parity story? Flag the gaps.

If parallel subagents are available, fan these lenses out per the
`## Parallel independent review (where supported)` section; otherwise
run them sequentially.

### Plan-review mode — output and handoff

Emit a prioritised, conversational critique grouped by the lenses
above; each plan finding names the plan section it challenges and a
concrete suggested change. Run the same Finding Verification filter
(Step 5): a plan finding must cite the plan section or the `file:line`
that grounds it, or it is dropped / downgraded.

In this INTERACTIVE plan-review mode, do NOT write plan findings to
the `Review Findings Log` (`/fix` must never ingest plan critique; the
one exception is the token-gated headless variant — see the
non-interactive contract's `PEER_LOOP_PLAN_REVIEW` points 4–5 — which
WRITES the round with the mode-distinct `Source:`). Instead, end by
recommending the user run `/review-plan` (`$review-plan` in Codex) to
fold the accepted critique into the plan, or apply small changes
directly. The PR-* code-review schema and the `/fix` handoff paths
below do not apply in this interactive plan-review mode (the
token-gated headless variant DOES log its plan findings per path (b),
using the PR-* IDs and per-finding schema; the `/fix` handoff paths
never apply to a plan round in either variant).

## Parallel independent review (where supported)

This workflow's independent passes are independent lenses over the same
inputs: validating the prior findings (Step 2), the missed-issue pass
(Step 3, including bounded structural quality), and downstream-breakage
analysis (Step 4) — or in plan-review mode the coverage / practicality
/ assumptions / simpler-path / verification lenses above. If your tool
supports parallel subagents (e.g. Cursor's Task subagents, Claude
Code's Task tool), you may fan them out: spawn one subagent per lens,
each reading the relevant files in full and returning candidate
findings with concrete `file:line` (or plan-section) evidence. Collect,
dedupe (same root cause at the same site = one finding), and reconcile
severities; the Finding Verification filter (Step 5) and the handoff
then run once in this orchestrating session.

If your tool does not support parallel subagents (e.g. Codex), run the
passes sequentially — the documented fallback, which changes nothing
about the findings, only how they are produced.

Subagents add **lens diversity, not model diversity**: they inherit
this session's model and share its blind-spot profile. Peer-review's
cross-model-family catch-rate gain comes from running this whole
`/peer-review` session on a different model family than the original
`/review` — see `## Model-diversity expectation (v22)` above. The
subagent layer is additive to that, not a substitute.

**Steps 1–4 below are the code-review path.** In plan-review mode,
Step 1's context-read still applies, but replace Steps 2–4 with the
`## Mode — plan review vs code review` lenses above; Step 5 (Finding
Verification) and the closing test-suite reminder apply to both modes.

## Step 1 — Read project context and the actual code
Read `AGENTS.md` first for project context (stack, architecture, current status).
Then read the relevant local files directly from disk before judging any findings.
Do not assume the provided or auto-detected findings are correct.

## Step 2 — Validate the targeted findings
For each finding in the targeted review round (auto-detected from the Findings Log, or pasted via fallback option 2):
1. verify it against the actual code
2. say whether you agree, partly agree, or disagree
3. explain why
4. propose a fix only if the issue is real

If the Step 0 fallback option 1 (describe) was used and there are no prior findings, skip this step and proceed directly to Step 3.

## Step 3 — Look for anything the first review missed
After validating the targeted findings (or, in the no-prior-findings case, starting fresh), perform an independent second pass for:
- correctness and likely bugs
- security issues
- missing validation or error handling
- production readiness
- architectural consistency
- obvious edge cases the first review did not mention
- **bounded structural quality** — oversized units, structural
  duplication, spaghetti conditionals, boundary/type leaks, and
  canonical-layer bypass, flagged only when acting on them would
  materially improve maintainability (same merge-bar and review-only
  boundary as `/review`'s Structural Quality Pass; a genuinely large
  restructure is a scope-expansion finding, never a silent fold-in)

## Step 4 — Check for downstream breakage risk
For every fix that was applied or proposed:
- identify what other files, functions, routes, or components call or depend on the changed code
- check whether the fix changes any function signature, return value, error behaviour, or data shape
- flag any caller that may now receive unexpected results or break
- if the project has a test suite or build command, suggest running it to catch regressions the review cannot see statically

This step matters most after fixes have been applied — a fix that is correct in the changed file but breaks a dependent file is not a safe fix.

## Step 5 — Finding Verification (false-positive filter)

Before emitting the New Findings (PR-*) and Regression Risks
(PR-REG-*) below — or, in plan-review mode, the plan critique — run a
Verification filter over your own candidate findings. This is the same
discipline `/review` applies to its findings: peer-review is only
useful if its findings are trustworthy.

For each candidate finding (PR-* / PR-REG-* / plan finding) confirm:
1. **Concrete evidence.** It cites a specific `file:line` (or, for a
   plan finding, the plan section) that actually exists and exhibits
   the problem when re-read. A finding with no locatable evidence is
   dropped, or downgraded to an explicit "needs investigation" note —
   it does not reach the handoff as a firm finding.
2. **The claim matches the code.** Re-read the cited lines; confirm the
   described current behaviour is what the code actually does, not what
   a diff fragment implied. Surrounding context frequently turns an
   apparent bug into a non-issue.
3. **Genuinely missed, not already handled.** Confirm the issue is not
   already covered by validation, a caller, a type, the prior
   `/review`, or a plan decision.
4. **Severity is justified.** Downgrade here if the evidence supports a
   lower severity, and note the downgrade.

Drop confirmed false positives — do not emit them. This filter is
distinct from Step 4: Step 4 asks "does a proposed fix break a
caller?"; this step asks "is each finding I am about to emit actually
real?". Carry the verification counts into the summary — the Handoff
summary line in code-review mode, or the plan-review critique summary
in plan-review mode.

## Output format (code-review mode)

In plan-review mode, use the plan-review output described under
`## Mode — plan review vs code review` instead of the sections below.

`/peer-review` uses PARTIAL schema parity with `/review`. New and
Regression Risk findings emit in /review-compatible per-finding
format (with `Triage:` and `Fix route:` fields) so `/fix` can ingest
them the same way it ingests /review findings. Confirmed and
Disputed sections stay conversational — they are commentary on the
prior /review's output, not new findings for /fix to process.

### Confirmed Findings (conversational)
- bullet-list each finding from the targeted /review round that you
  verified as correct, with one line of supporting evidence (e.g.
  "verified the call site does miss the lock — see `file:line`"). Do
  NOT promote these to the Findings Log; they are already there from
  the original /review.

### Disputed Findings (conversational)
- bullet-list each finding from the targeted /review round that is
  incorrect, overstated, or based on a misreading of the code, with
  one line explaining what the code actually does. Do NOT promote
  these to the Findings Log; the original /review's entry stays as-is
  and the user can choose to mark it `/fix decision: Not reproducible`
  or `Accepted` per their judgment.

### New Findings (/review-compatible — for /fix ingestion)
For each new issue the targeted /review missed, emit a full /review-
compatible per-finding block with stable IDs prefixed `PR-` (e.g.
`PR-CRIT-001`, `PR-HIGH-001`):

- **[SEVERITY]** `file:line` — short title
  - Triage: Fix-now / Accept / Defer / Fix-now-if-tied (use the same
    bias as /review — prefer Fix-now / Include in plan and reserve
    Defer for genuinely large or out-of-scope work; CRIT/HIGH default
    Fix-now; MED leans Include in plan; LOW default Fix-now, recommend
    Accept only when there is no benefit to fixing or a net downside;
    any Accept/Defer is gated when `/fix` ingests these findings, and an
    `Include in plan` finding is scoped-`/review-plan`-hardened when
    `/fix` ingests it — see `/review-plan`'s **Scoped mode**)
  - Fix route: fix-on-fast / premium-only / defer / accept
  - Why it matters: ...
  - Current behaviour: ...
  - Desired behaviour: ...
  - Pattern to follow: ...
  - Pattern siblings: ... (or "none found")
  - Invariant: ... (when applicable)
  - Verification: ...
  - Regression risk: ...

Choose how these PR- findings reach `/fix` at the `## Handoff — choose your path` section below: paste to the executor in chat (default), or write to the Findings Log (explicit opt-in).

### Regression Risks (/review-compatible — for /fix ingestion)
For each regression risk from changes that have been applied, emit a
full per-finding block with IDs prefixed `PR-REG-` (e.g.
`PR-REG-001`):

- **[SEVERITY]** `file:line` — regression
  - Triage: Fix-now / Defer / Accept
  - Fix route: fix-on-fast / premium-only / defer / accept
  - What changed: ...
  - Dependent code affected: ...
  - Recommended action: ...

Same ingestion path as New Findings.

### Recommended Action Plan (conversational)
- prioritised next steps for the user, summarising what to fix first
  (typically: any New CRIT/HIGH, then Regression Risks, then New MED,
  then any user-decision on Disputed)

## Handoff — choose your path

Once Steps 1–4 are complete and the Confirmed / Disputed / New (PR-*) / Regression Risks (PR-REG-*) / Recommended Action Plan sections are emitted above, end with the one-line summary below and present both handoff paths. Wait for an explicit choice — do not silently default to one or the other, and never silently write to the Findings Log.

Summary line: `(X confirmed / Y disputed / Z new PR-* / W regression PR-REG-*; verification: C candidates / D dropped / E downgraded)` — the counts that came out of this review.

### (a) Default — paste to the executor for in-chat triage [recommended when executor session is live]

Copy the PR-* and PR-REG-* blocks above into the executor's chat session for in-chat triage. The executor's session memory catches peer-review false positives that stateless `/fix` would miss — the executor often already considered and rejected the approach the peer-reviewer is proposing, or knows session context that contradicts the peer-reviewer's reading. This preserves the current executor-verifies-before-fix workflow and is the recommended path when the executor session is still live.

### (b) Write PR- findings to the Findings Log [recommended when executor session is gone]

On explicit user opt-in (e.g. the user says "write to log"), append a new Round N+1 block to the plan's `Review Findings Log` with:
- `Source:` set to where this `/peer-review` ran, in the mode-distinct form — code-review mode: `Cursor peer-review`, `Claude Code peer-review`, or `Codex peer-review`; token-gated headless plan-review mode (`PEER_LOOP_PLAN_REVIEW`): `Cursor plan peer-review`, `Claude Code plan peer-review`, or `Codex plan peer-review` (mirroring `/review`'s "set the Source line to where it ran"; do not hardcode Cursor). Step 0 sub-step 2's peer-round detection reads exactly these six values, and the plan-review value deliberately ends in `peer-review` so suffix-rule consumers exclude plan rounds even without knowing the specific value.
- `Round status:` — when X ≥ 1 (at least one PR-* / PR-REG- finding), `Open (X pending)` where X = the count of findings emitted above; when **X = 0** (a converged round with nothing to log — expected for a headless `PEER_LOOP_NONINTERACTIVE` run, where path (b) is forced even with zero findings), write `Round status: Closed` with a one-line `No new findings — converged` note instead of `Open (0 pending)`, so `/peer-loop` and `/fix` read the round as converged rather than open-with-nothing-pending
- One full per-finding block per PR-* and PR-REG-* finding, using the same schema as `/review` rounds (per-finding fields documented in `.cursor/templates/implementation-plan-template.md`), preserving the PR- / PR-REG- stable IDs from the review output above and setting `/fix decision: Pending` on each entry

After the write, routing branches on the round's mode-distinct `Source:`. For a code-review round, `/fix` on any of the three tools (Cursor, Claude Code, or `$fix` in Codex) picks up the new round via its existing Step 0 Findings Log path — no paste required. Recommended when the executor session is gone (a new chat, a different day, a different machine) and the in-chat triage benefit is unavailable. A token-gated plan-review round (`… plan peer-review`) is never picked up by `/fix` — its Step 0 selection excludes those rounds; the owning planning session applies the accepted findings as `/review-plan`-style amendments (or via a scoped `/review-plan`), marking per-finding dispositions on the round.

On code rounds, `/fix` enforces per-finding scope-locking, pattern-sibling propagation, invariant checks, and stop-on-failure verification — do not paste findings back with "fix these issues".

This command is iterative. After fixes, return and describe what changed; re-review the affected code with focus on Step 4 — each round of fixes can introduce new regression risks.
