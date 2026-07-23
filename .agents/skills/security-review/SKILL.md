---
name: security-review
description: Run a documented security threat-model pass over recent work, delegating to each tool's native security reviewer where available, and write findings to the plan. Propose-only — never auto-edits. Shared Cursor/Codex/Claude Code workflow; invoke as /security-review in Cursor or Claude Code, or $security-review in Codex.
disable-model-invocation: false
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/security-review` in Cursor or Claude Code, or `$security-review` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

`/security-review` is a focused, propose-only security pass: it runs a documented threat-model review of recent work and writes the results as `/review`-compatible findings — it NEVER edits code itself. Producing the findings is the deliverable; applying a fix belongs to `/fix` (localized) or to a plan-amending disposition plus a scoped `/review-plan` (substantial hardening). It is the deliberate, heavier security counterpart to everyday `/review` (mirroring the `/document` ↔ `/document-review` split): everyday `/review` stays fast, and security gets its own thorough pass you run on security-sensitive work or on a periodic cadence.

This workflow is propose-only and agent-invocable: it carries `disable-model-invocation: false` (Cursor + Claude Code) and NO `agents/openai.yaml` (Codex), so an agent may invoke it automatically — for example inside a Hardening stage or a review loop — and you can still invoke it explicitly. Because it only writes findings and never edits code, agent invocation cannot mutate code or docs; the apply step is always a separate, human-gated `/fix`.

Plan files are shared across all three tools. Handoff is through disk state, the plan file, and git, not conversation memory.

## Step 0 — Read plan context and scope

Mirror `/review` Step 0:

- check `.cursor/plans/` (excluding `.cursor/plans/completed/`) for a plan file; if running in the same session that produced the work, use that plan; if multiple, prefer the most recent `Last plan sync`; if none, proceed against the code and project conventions and note that findings persist only in the conversation.
- if a plan is in scope, read its `Goal`, `Design Decisions`, `Critical Constraints`, and `Integration Notes` so a deliberate, documented security trade-off is not re-flagged as a bug.
- establish the scope: by default the changed files since the plan's `Last plan sync` (or the feature/change baseline), or an explicit target the user named. Pay special attention to the trust boundaries the change crosses: request handlers, auth/permission checks, data access, file/network I/O, deserialization, and template rendering.
- read every in-scope user-authored file in full before judging it; skip generated artefacts and read their upstream source.

## Step 1 — Threat-model pass (delegate to a native reviewer where available)

Run a security threat-model review of the in-scope changes. Where the tool ships a native security reviewer, delegate the heavy scan to it and then normalise its results into this workflow's Findings Log; where it does not, run the portable checklist below in this session. The native reviewers and this fallback are all review-and-report (propose) — none auto-edit — so the propose-only boundary holds regardless of path.

- **Cursor** — delegate to the native security review subagent (the `review-security` skill / "Security Review" Task subagent). Run it over the same changed-files scope, then fold its findings into the Findings Log below.
- **Claude Code** — delegate to its security-review skill where available, then fold the results in.
- **Codex** — use the portable checklist below (Codex's built-in `/review` can supply an additional security lens).
- **Portable fallback (any tool)** — work through the threat-model checklist directly in this session.

Threat-model checklist (the portable lens; also the gap-check after a native scan):
- **AuthN / AuthZ** — missing or incorrect authentication; broken access control / IDOR; missing ownership or role checks; privilege-escalation paths.
- **Injection & taint** — untrusted input reaching a dangerous sink: SQL/NoSQL injection, command/shell injection, XSS, template injection, path traversal, unsafe deserialization. Trace input → sink.
- **Secrets & sensitive data** — hardcoded secrets/keys; secrets in logs or error messages; sensitive data logged or returned to the client; weak or missing encryption at rest/in transit.
- **SSRF & outbound requests** — user-controlled URLs/hosts reaching server-side fetches; missing allow-listing.
- **Crypto & sessions** — weak algorithms, predictable tokens, missing CSRF protection, insecure cookie/session handling.
- **Resource & availability** — missing rate limits, unbounded input, ReDoS, unbounded resource allocation.
- **Dependencies & config** — risky new dependency, insecure default config, debug/verbose mode left enabled.

Where a finding is pattern-shaped (e.g. one unparameterised query), record its Pattern siblings — the other sites likely sharing the flaw.

## Step 2 — Verify candidates (false-positive filter)

Before logging anything, re-read the cited lines for each candidate and confirm, mirroring `/review`'s Finding Verification pass:

1. **Concrete evidence** — a real `file:line` (or tight region) that exists and exhibits the issue; trace the actual taint path or the missing check.
2. **The claim matches the code** — confirm the vulnerable behaviour is what the code actually does, not what a diff fragment suggested; surrounding guards, framework defaults, or callers frequently neutralise an apparent issue.
3. **Not already mitigated** — confirm the input isn't already validated/escaped upstream, the route isn't already gated, or a framework default doesn't already protect it.
4. **Severity justified** — size by real exploitability and blast radius; downgrade theoretical issues.

Drop confirmed false positives. Keep a one-line note for any finding downgraded or that survived a genuine challenge.

## Step 3 — Severity routing and Findings Log

Assign each surviving finding a severity using the existing `/review` severity vocabulary by exploitability and blast radius (security findings legitimately reach CRIT/HIGH). Route as `/review` does:

- **CRIT / HIGH** → default `Triage: Fix-now` (severity dominates). If the fix is outside the plan's `Agreed Scope`, follow `/review`'s CRIT/HIGH scope-expansion disposition contract (explicit user disposition: Amend plan now / Downgrade severity / Fold-in / Open follow-up / Retained with a `Risk if deferred:` tag) before logging.
- **localized fix** (add one validation, parameterise one query, gate one route) → `Triage: Fix-now`; `/fix` applies it with re-read + verification + stop-on-failure.
- **substantial / cross-cutting hardening** (introduce an auth layer, a sanitisation boundary, a shape change across many call sites) → route through a **plan-amending disposition**: append a 🟥 task to the CURRENT plan (bias toward tacking onto the active/stage plan over a new follow-up plan), then run a **scoped `/review-plan`** on just that task before it is executed. The scoped behaviour is defined once in `/review-plan`'s scoped-mode section — point there; do not restate it.
- **MED / LOW** → run through the Deferral Confirmation Gate exactly as in `/review` (default Fix-now / Include in plan; reserve Defer for genuinely large work).

Write findings to the plan's `Review Findings Log` as a `/review`-compatible round so `/fix` ingests them unchanged:

- append a `### Round N — YYYY-MM-DD` block, where N continues the plan's existing Review History / Findings Log round count; also append the one-line `Review History` entry.
- set `Source:` to where this ran plus the skill: `Cursor security-review` / `Claude Code security-review` / `Codex security-review`. If a native reviewer produced findings, note that in the round (e.g. "via Cursor security-review subagent") but keep the per-finding schema.
- assign stable IDs with the `SEC-` prefix in finding order: `SEC-001`, `SEC-002`, … (numbering resets per round). Each finding carries its severity (CRIT/HIGH/MED/LOW) as a field.
- use the full per-finding block from `.cursor/templates/implementation-plan-template.md` (Triage, Fix route, Why it matters, Current/Desired behaviour, Pattern to follow, Pattern siblings, Verification, Regression risk, `/fix decision: Pending`, etc.). A substantial finding becomes a new 🟥 task in the plan, logged with `Triage: Fix-now` so `/fix` ingests it — the same representation `/review` uses for an `Include in plan` outcome (`Include in plan` is NOT a `Scope-expansion disposition` field value; use only the values the template documents for that field). The scoped `/review-plan` then hardens that new task.
- append only after the pass is complete; never for an aborted pass. If no plan file is in scope, skip the log and report findings in the conversation only.

## Output format

Mirror `/review`'s shape, scoped to security:

- **Scope** — files read, trust boundaries examined, baseline, any skips, and which reviewer ran (native subagent vs portable checklist).
- **Security findings** — one entry per finding with its `SEC-NNN` ID, severity, `file:line`, the threat (what an attacker does), why it is exploitable, the mitigation, and its route.
- **Checked and clean** — the threat-model categories examined that produced nothing, so coverage is auditable (name the categories, not every line).
- **Summary** — counts by severity and route, plus the round number; state "no security issues found in scope" if that is the honest result, and recommend running the project's own security tests / dependency audit where one exists.
