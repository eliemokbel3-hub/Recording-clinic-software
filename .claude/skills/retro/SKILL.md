---
name: retro
description: Synthesize a structured run report from a loop run's logs and the plan's review data — what happened, what it cost, what failed and why. Propose-only — writes only the report file and one plan pointer line, never edits code or skills. Shared Cursor/Codex/Claude Code workflow; invoke as /retro in Cursor or Claude Code, or $retro in Codex.
disable-model-invocation: false
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/retro` in Cursor or Claude Code, or `$retro` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

`/retro` is a focused, propose-only diagnostics pass: after a loop run (`/execute-loop`, `/peer-loop`, `/review-loop`, or any run that left logs in `.cursor/loops/`), it reads the run's loop logs and the governing plan's review data and writes a structured run report answering "what happened, what did it cost, what failed and why". The report is the deliverable — `/retro` NEVER edits code or skills, never applies fixes, and never appends `Review Findings Log` rounds (findings rounds are `/review`-family artifacts with round-numbering semantics that `/fix` ingests; a retro report is synthesis, not findings). Its only writes are the report file and a single pointer line in the plan's `Current State / Handoff Note`.

This workflow is propose-only and agent-invocable: it carries `disable-model-invocation: false` (Cursor + Claude Code) and NO `agents/openai.yaml` (Codex), so an agent may invoke it automatically — for example right after a loop run converges — and you can still invoke it explicitly. Because its only writes are the gitignored report and the one pointer line, agent invocation cannot mutate code, skills, or docs.

Plan files are shared across all three tools. Handoff is through disk state, the plan file, and git, not conversation memory.

## Step 0 — Locate the run and the plan

Resolve three things before reading anything else. Explicit user-supplied overrides — a logs directory, a plan path, or a run key — ALWAYS win over the defaults below; they are what make sandboxed/dogfood runs possible (point `/retro` at a snapshot directory and a plan copy, and every write confines itself there).

- **Logs directory:** default `.cursor/loops/` in the current repo.
- **Run key:** default = the `stage-<N>` log-file prefix present in the resolved logs directory (e.g. `stage-4` from `stage-4-executor.log`). If several prefixes exist, prefer the most recently modified; if none exist, fall back to the governing plan's feature name.
- **Governing plan:** find the plan in `.cursor/plans/` (excluding `completed/`) that the run built — on ambiguity prefer the most recent `Last plan sync`; if still ambiguous, ask the user which plan governs the run.

Degradations, flagged in the report rather than guessed around:
- **No loop logs** (the logs directory is missing, empty, or has no matching files) → produce a **plan-only report** from the plan's `Review History` / `Review Findings Log`, and flag prominently that no log evidence was available.
- **No plan** → produce a conversation-only summary in the chat and make **NO writes at all** (no report file, no pointer).

## Step 1 — Ingest the evidence

From the resolved logs directory:
- parse **`ROLE:` lines** (`start` / `end` pairs, per-round `round` lines, and `handoff` exit sentinels) — the key=value convention defined canonically in `/execute-loop`'s Visibility + run-state section: role, backend, model, timestamps, and any best-effort usage fields (`turns≈` / `tokens≈` / duration). Timestamp trust follows that canonical definition: composer-written `start`/`end` `ts=` values are the run's ordering truth; a role's self-written `ROLE: handoff` `ts=` is ADVISORY — headless sessions emit junk wall-clock (observed live: placeholder midnight timestamps) — so treat it as approximate, never as ordering evidence.
- parse **`DELEGATION:` lines** (`decision` / `outcome` / `roi` / `smoke-addendum` variants) — same key=value family: unit, spec one-liner, delegate backend/model, diff-vs-spec result, misses, smoke results, ROI observations.
- scan the **per-role tee logs** (`<runkey>-<role>*.log`) for hard evidence worth citing: verification failures, gate pauses, filesystem-escape checks, smoke results.

From the governing plan:
- parse **`Review History`** lines — the `X CRIT / X HIGH / X MED / X LOW` counts, `skew=`, and `action=` fields, using `/review`'s vocabulary verbatim (`skew` ∈ none / pre-existing / fix-induced / same-family / mixed; `action` ∈ none / escalate / strengthen-siblings / triage-and-ship). Do not invent a parallel taxonomy.
- parse **`Review Findings Log`** rounds — `Source:` (which tool/family produced the round; a `Source:` ending in `plan peer-review` marks a PLAN peer-review round — label it plan-scoped in the round story, never as a code-review round), per-finding severities, `Triage:`, `/fix decision:`, and any scope-expansion or Deferral Confirmation Gate dispositions.

**`ROLE:`-less logs are normal** — every log written before the convention existed has none. Infer role identity from `DELEGATION:` fields (`delegate=`, backend/model values), log filenames (`stage-<N>-<role>*.log`), and plan prose — and mark EVERY inferred identity as *(inferred)* in the report. Never present an inference as a logged fact.

## Step 2 — Synthesize

Build the run story from the evidence:

- **Rounds and findings by skew class** — how many review/peer rounds ran, finding counts per round, and the failure classes: fix-induced regressions vs same-family siblings vs pre-existing surfacing vs genuinely new. Where did the rounds go — which loop (review vs peer), and which model family caught what (same-family vs cross-family catches).
- **Per-role identity and usage** — a table of roles (composer / executor / architect / delegate / peer / advisor) with backend, model, activation count, and whatever usage evidence exists: `turns≈` / `tokens≈` / durations from `ROLE:` end lines or CLI output, timestamps otherwise. Where a backend exposes nothing, state **"not exposed"** — never estimate or fabricate a number. Cost-attribution caveats — apply them explicitly whenever citing cost or usage numbers: per-invocation figures (`total_cost_usd`, token counts printed by a spawned CLI session) are per-spawned-session and are the trustworthy per-run numbers; account-pool percentages (`/usage` headlines, usage-checkpoint lines in the logs) are ACCOUNT-GLOBAL — concurrent runs on other repos/devices share the pool — so cite them as context only, NEVER attributed to a single run; and `total_cost_usd` is API-equivalent pricing, not actual subscription draw — comparable between runs, not a bill.
- **Delegation outcomes** — decisions taken (unit + delegate), diff-vs-spec results, misses and how they were handled, smoke results, and the logged ROI observations.
- **Gate pauses** — every MUST-PAUSE surfaced to the user, every AUTO-DISPOSABLE candidate auto-applied and logged, and the dispositions taken.
- **Calibration readout** — map the round story onto the existing Round Classification guidance: mostly fix-induced findings → the executor model is the problem (escalate); mostly same-family siblings → reviews are missing pattern siblings (strengthen the next review); mostly pre-existing LOWs → the natural tail (triage and ship). Say which of these the run's evidence supports.
- **Evidence gaps** — what the report could not determine and why (no `ROLE:` lines, usage not exposed, missing tee logs), so the reader knows the confidence level.

## Step 3 — Write the report

Write the report to **`<resolved logs dir>/retro-<runkey>-<YYYY-MM-DD>.md`** — default `.cursor/loops/` (gitignored, transient); an explicit logs-dir override redirects the report there, so a sandboxed run never dirties the invoking repo or the corpus source. A same-day rerun overwrites the file; a new date writes a new file.

Use these stable top-level headings, in this order — `/document`'s lessons distillation and other consumers grep them:

1. `Run identity` — run key, plan, date range, phases/tasks covered, backends/models involved.
2. `Rounds and findings` — the per-round story with skew classes.
3. `Per-role usage` — the identity/usage table, inferences marked.
4. `Delegation` — decisions, outcomes, misses, ROI (or "no delegation in this run").
5. `Gate pauses` — pauses and dispositions (or "none fired").
6. `Calibration` — the readout against Round Classification guidance.
7. `Evidence gaps` — what could not be determined and why.

Then update the RESOLVED plan file's `Current State / Handoff Note` with the single pointer line:

```text
Retro report: <resolved logs dir>/retro-<runkey>-<YYYY-MM-DD>.md (YYYY-MM-DD)
```

Replace any existing `Retro report:` line rather than stacking a second one. If the governing plan's `Lifecycle State` is not Active (e.g. `Completed — Follow-ups Retained`), do not dirty it silently — skip the pointer and say so in the chat summary, or write it only on explicit user confirmation. This pointer and the report file are the ONLY writes `/retro` makes.

## Step 4 — Report in chat

Give a short summary: headline counts (rounds, findings by severity, delegations, gate pauses), the calibration readout in one sentence, and the report path. Restate that `/retro` made no code or skill edits — applying anything the report suggests is separate, human-gated work (`/fix`, a plan amendment, or the next stage's planning).
