---
name: update-workflow
description: Update this repo's installed Cursor/Codex/Claude Code workflow to a newer bootstrap version — pin one source identity, gate on tree/live-run safety, apply payloads transactionally via the installed extractor, verify, commit with provenance, and report the remaining UPDATE ONLY steps as a checklist. Shared Cursor/Codex/Claude Code workflow; invoke as /update-workflow in Cursor or Claude Code, or $update-workflow in Codex. Side-effecting; explicit invocation only.
disable-model-invocation: true
---

This is a shared Cursor/Codex/Claude Code Skill. Invoke it as `/update-workflow` in Cursor or Claude Code, or `$update-workflow` in Codex.

When this Skill references another shared workflow, use the current tool's sigil: `/workflow` in Cursor, `$workflow` in Codex, and `/workflow` in Claude Code.

This workflow is side-effecting. Cursor uses `disable-model-invocation: true`; Codex uses `agents/openai.yaml` with `policy.allow_implicit_invocation: false`; both require explicit user invocation.

Update this repo's installed workflow (the `.cursor/`, `.claude/`, `.agents/`, `.codex/`, and repo-root `scripts/` payloads) to a newer version of `bootstrap.md`, safely and transactionally. This skill EXECUTES payload extraction plus the installed-version marker write, and nothing else: the fetched bootstrap's post-extractor UPDATE ONLY steps are REPORTED as a checklist at the end, never run by this skill. It never pushes.

**Scope of every write this run may make:** the fetched bootstrap's manifest payload targets + the installed-version marker (`.cursor/bootstrap/installed-version`), all behind one confirm. Anything else on disk is out of bounds.

## Step 0 — Parse the invocation (before any network or write)

The total grammar is:

`/update-workflow [--reapply] [--source <path-or-slug>]`

Parse intent ONCE, first:
- `--source <path-or-slug>` names the source: a bootstrap FILE, a clone DIRECTORY, or a repo SLUG (`owner/repo`). A path or repo literally named `reapply` stays unambiguous here.
- a bare `<path-or-slug>` argument is accepted as `--source`'s value when no flags are present
- `--reapply` is the ONE explicit re-apply route (Step 4): it makes SAME and OLDER sources applyable through the full gate chain. It is never inferred ad hoc.
- no arguments = the default configured-channel path (Step 2, mode ② then ③)

Duplicate flags, unknown flags, or any ambiguous/malformed form: REFUSE read-only — print the accepted syntax above, change nothing, stop. Every accepted invocation maps to exactly one source identity and one reapply boolean before anything else runs.

## Step 1 — Pin the helper, check the installed tooling

The shipped helper `.cursor/bootstrap/workflow-source.py` owns the configured source slug, the version grammar, header extraction, marker read/write, and the transaction's inventory/snapshot/delta/restore pipeline. The helper is itself an extractor payload this update may overwrite mid-run, so pin one implementation for the whole invocation:

1. If `.cursor/bootstrap/extract-bootstrap.py` is missing, STOP with zero writes: this repo was never bootstrapped (or pre-dates v29). Remediation: run FULL INSTALL from `bootstrap.md` per its own instructions — this skill cannot substitute for it.
2. If `.cursor/bootstrap/workflow-source.py` is missing, STOP with zero writes: the installed workflow pre-dates v31.2. Remediation: run the manual UPDATE ONLY sequence from the latest `bootstrap.md` once; this skill works from the next version onward.
3. Create ONE run-temp root OUTSIDE the repo (`mktemp -d`) holding TWO sibling areas with NON-OVERLAPPING lifetimes: `<run-temp>/state` — the `<state-dir>` passed to every helper `--state` call (helper-owned; the helper enforces 0700/0600, and `cleanup --state` recursively removes exactly this directory) — and `<run-temp>/source` — the pinned-source area where the run's one bootstrap copy lives (the FILE private copy, the gh-fetched temp file, or the `git show` output). Helper cleanup NEVER touches `<run-temp>/source`: on the success path the pinned copy must outlive Step 9.6's state cleanup so Step 10 can read it.

   **ABORT-CLEANUP (the one whole-run cleanup procedure):** run helper `cleanup --state <state-dir>` if `<state-dir>` still exists, then remove the ENTIRE `<run-temp>` root — bounded to the updater-created absolute `mktemp` path; in FILE mode the user's original lives outside it and is never touched. EVERY non-success exit after run-temp creation runs ABORT-CLEANUP (after snapshot restore where applicable): source/header errors (Step 2), safety-gate pauses (Step 5), preflight/inventory/snapshot/containment refusals (Steps 7–8), confirm-no (Step 7.4), the pre-write revalidation stop (Step 8.1), and restored failure (Step 8.3). Step 9.6's state-only cleanup is EXCLUSIVELY the success path that continues to Step 10. Then pin:
   - `python3 .cursor/bootstrap/workflow-source.py pin --state <state-dir>`
   - record the printed sha256; from here call ONLY the pinned copy `<state-dir>/pinned-helper.py` for the entire run — pre-check through success, rollback, and cleanup. Newly extracted helper bytes activate on the NEXT invocation only.
   - `python3 <state-dir>/pinned-helper.py contract` must print `contract=1`; anything else is a version-skew fail-closed stop (name both versions, remove the state dir, change nothing).

The configured source slug comes from `python3 <state-dir>/pinned-helper.py slug` — the single operator-editable line lives in the helper, never in this skill.

## Step 2 — Resolve ONE pinned source identity

Every mode yields one pinned identity naming the exact bytes acted on, an advertised version, the bootstrap bytes, and provenance. First hit wins in the order below; the resolved mode and identity are shown to the user before anything is compared or applied.

**Identity serialization (one spelling everywhere):** a commit-pinned identity is recorded as the FIRST 12 HEX of the pinned commit sha (e.g. `ba2d92b5ff26`); a FILE identity as `file:<first 12 hex of the sha256>`. Marker write, the SAME-identity compare, display, and the commit message all use this exact serialization — never mix full and shortened forms.

**① Explicit `--source` argument:**
- **FILE** (path to a bootstrap file): read the supplied path ONCE, copying its bytes into a PRIVATE run-temp copy (in the Step 1 pinned-source area `<run-temp>/source/` — OUTSIDE `<state-dir>`, so helper cleanup never touches it; restrictive permissions) while computing the sha256 of those same bytes — identity = `file:<first 12 hex of sha256>` OF THE COPY. From here EVERY read — header parse, sub-note selection, preflight, inventory, real extraction, and the Step 10 checklist — uses ONLY that private copy; the user's original path is never re-read, never mutated, never deleted (a later change to the original cannot desynchronize the identity from the bytes acted on). Parse the COPY's `**Version:**` header IMMEDIATELY via the pinned helper (`header --bootstrap <private copy>`); the header IS the advertised version, so the cheap `VERSION` probe and the VERSION↔header cross-check are SKIPPED in this mode. A missing, duplicate, or malformed header errors exactly (the helper's exit 4 messages) — a read-only stop via the Step 1 ABORT-CLEANUP (the private copy already exists; the original is never touched).
- **DIRECTORY** (path to a source clone): a labelled LOCAL OVERRIDE — it never claims to be "latest". Pin `<sha>` = that clone's current HEAD and record override provenance (`local clone @ <sha>`). At this stage read ONLY `VERSION`, WITHOUT MUTATION, via `git show <sha>:VERSION` — `bootstrap.md` is read from the SAME pin (`git show <sha>:bootstrap.md`) only on a continuing route (Step 4). NEVER `git pull`; updating the sibling clone is the operator's own separate action. The clone must be byte/status-unchanged by this run, on completion and on cancellation alike.
- **SLUG** (`owner/repo`): treated as mode ③ against that slug.

**② Auto-detected local clone (default path, tried first):** scan the repo root's PARENT directory for a directory whose `bootstrap.md` carries the installer header AND whose git remote matches the configured slug. ELIGIBLE only on an UNAMBIGUOUS single match whose pinned HEAD equals the CURRENT remote `main` SHA (one network check, non-mutating: `git -C <clone> ls-remote origin main` — the default path installs exactly remote-main bytes). Offline, ahead/behind/diverged, detached, or feature-branch HEAD: report the state and offer the gh path (③) or an explicit ①-style local override — never proceed silently. MULTIPLE matching directories: fail closed, list them, ask for an explicit `--source`. Read without mutation: pin `<sha>` = the verified HEAD and read ONLY `VERSION` via `git show <sha>:VERSION` at this stage; `bootstrap.md` comes from the same pin only on a continuing route (Step 4).

**③ `gh api` raw fetch (default fallback; also SLUG mode):** resolve the pin FIRST — `gh api /repos/<slug>/commits/main --jq .sha` — then fetch ONLY the ~10-byte `VERSION` object from that immutable commit at this stage:
- `gh api -H "Accept: application/vnd.github.raw" "/repos/<slug>/contents/VERSION?ref=<sha>"`

The full `bootstrap.md` is fetched from the SAME pin only on a continuing route (Step 4):
- `gh api -H "Accept: application/vnd.github.raw" "/repos/<slug>/contents/bootstrap.md?ref=<sha>" > <temp file>`

The raw media type is REQUIRED for that continuing-route fetch: `bootstrap.md` is ~1.9 MB, over the contents-API 1 MB JSON cap — a default `gh api .../contents/bootstrap.md` returns no content (raw serves files to 100 MB). Both reads carry `?ref=<sha>` so displayed, compared, applied, and committed bytes all come from one commit even when `main` moves mid-run. No `gh` / not authenticated: report it and offer the local-clone or FILE modes — never retry-loop.

**Source trust (Decision 16, carried verbatim from the plan):** Source trust (PR-HIGH-010/011 — DISSOLVED by the 2026-08-04 descope, kept as the boundary record): with Decision 14 executing nothing, EVERY source mode is payload-only by construction — the extractor's manifest verification plus the no-follow containment rule bound what any source can touch, and no prose from any fetched file is ever executed. The checklist Decision 14 prints is DISPLAY text, clearly framed as quoted-from-the-fetched-bootstrap, never instructions this run acts on. The full trust table (configured-channel authentication before prose execution; header + manifest self-consistency is NOT authentication; no runtime elevation) is RECORDED with the Deferred auto-execution item — it is the entry bar for ever building that feature.

## Step 3 — Version pre-check (cheap probe, canonical grammar)

All version values — marker, `VERSION`, header, sub-note destinations — go through the pinned helper's ONE grammar (`parse` / `compare`): exactly two unsigned decimal components in canonical spelling (`31.2.0` and `031.2` are MALFORMED, fail closed), compared as integer tuples (`31.10` > `31.2`), MAJOR = first-component increase. Never compare version strings lexically or with shell arithmetic.

- Advertised source version: the ~10-byte `VERSION` object in directory/GitHub modes — preserve the RAW object bytes to a restrictive run-temp file (redirect the `git show` / `gh api` output; never capture it via shell command substitution, which strips ALL trailing newlines and silently repairs malformed multi-line framing) and validate it via the pinned helper's ONE framing boundary: `python3 <state-dir>/pinned-helper.py version-read --file <tmp>` (exactly one line + one optional trailing LF; CR, extra/blank lines, surrounding whitespace fail closed, exit 4). In FILE mode the advertised version is the already-parsed header.
- Installed version: `python3 <state-dir>/pinned-helper.py marker-read --target .`

In directory/GitHub modes, once the full bootstrap is in hand its `**Version:**` header is authoritative for what gets applied — a VERSION↔header mismatch is a source-repo error to surface, never reconcile silently.

## Step 4 — Marker state machine (decides the route)

The marker is `.cursor/bootstrap/installed-version`, COMMITTED, one line: `<version> <source-identity>` (e.g. `31.2 ba2d92b5ff26`, or `file:<12-hex>`). The nudge in `/start-session` parses field 1 only. Route on the helper's classification:

- **VALID + SAME, configured channel (② or ③), same identity** → a true READ-ONLY NO-OP: report up-to-date, no prompt, no write, no commit (an identical rewrite has no diff to commit). Nothing beyond the cheap probe is fetched. `--reapply` overrides this into the full gate chain.
- **VALID + SAME, configured channel, DIFFERENT identity** → NOT up-to-date: version-to-bytes immutability on the configured channel is a declared source-repo release constraint, so a same-version content change on `main` is a release ERROR — surface it deterministically and offer the gated `--reapply`; never report a silent up-to-date.
- **VALID + SAME, identity-less marker** (pre-identity or adoption form) → compares by version only; report up-to-date; the marker heals to the two-field form at the next accepted apply.
- **VALID + SAME, from an OVERRIDE source (FILE / explicit directory)** → NOT silently equal: the marker stores a version and one identity, and this source's identity differs or is unproven — report that content may differ and offer the gated `--reapply` instead of a no-op.
- **ABSENT** → `installed=unknown`. NEVER fabricate a version — this IS the bootstrap/repair path: a full gated apply whose provenance commit contains AT MINIMUM the marker (identical payloads degrade it to a marker-only REAL diff — the marker file is new). Display rule for the unknown baseline: show the TARGET version's sub-note plus one explicit "installed baseline unknown" line — never a guessed delta.
- **MALFORMED** → fail closed: treat as ABSENT with one warning line naming the malformation. Marker repair rides this branch — there is no separate repair mode.
- **Source OLDER than marker** → report both versions and STOP. `--reapply` makes it applyable through the full gate chain (downgrade stays a deliberate act).
- **Source NEWER** → the normal upgrade path: continue.

On any continuing route — and ONLY then — read the full `bootstrap.md` from the SAME pinned identity (already in hand only in FILE mode as the Step 2 private copy; directory/auto-clone modes read it NOW via `git show <sha>:bootstrap.md`, gh/slug mode fetches it NOW via the Step 2 ③ ref-pinned raw call) and parse ITS header via the pinned helper — that header is what gets applied and recorded. In EVERY mode the continuing-route bytes live in ONE private run-temp file in the pinned-source area (`<run-temp>/source/`, outside `<state-dir>`) — the pinned source copy — and every later step's `<fetched file>` means exactly that file, never a re-read of a user-supplied or remote path. A non-continuing route (the read-only SAME no-op, or an OLDER stop without `--reapply`) never touches `bootstrap.md`.

## Step 5 — Safety gates (all BEFORE the confirm)

**(a) Clean tree required — no override.** Run `git status --short`. ANY output pauses the run, showing the exact status lines: the operator commits or stashes and re-runs. There is no dirty-tree override in v31.2 — an override could overwrite or commit user changes in payload paths.

**(b) Live-loop-run guard — canonical ownership, never filenames.** Resolve the BASE worktree with one exact, non-mutating procedure that covers linked worktrees: `git worktree list --porcelain` — the FIRST `worktree <path>` entry is the main (base) worktree (git documents main-worktree-first ordering); canonicalize it (realpath). Do NOT derive the base from `git rev-parse --git-common-dir`: that names the shared `.git` DIRECTORY, not the base checkout — appending `.cursor/loops` to it inspects a nonexistent path and silently misses every real marker. Inspect `<base-realpath>/.cursor/loops/` for `<iso-id>-active` ownership markers and compare each marker's recorded checkout realpath against the realpaths of BOTH the base checkout and the current (possibly linked-worktree) checkout — a marker claiming either BLOCKS; a marker whose owner or checkout field cannot be read or resolved blocks CONSERVATIVELY (unknown = pause, never proceed). ANY marker claiming this checkout BLOCKS the updater — live, UNKNOWN, and conclusively-DEAD owners alike (a dead owner means a crashed/recoverable run whose ownership must be reconciled, not a closed run). Pause with the marker evidence shown and hand off to `/execute-loop`'s recovery/close flow, which ALONE removes markers — this skill NEVER mutates a loop artifact. Stale `*-spawn.lock` files and log mtimes are SUPPORTING evidence only, never the primary authority: a lock alone must not block (this source repo's own flat `.cursor/loops/` carries stale locks from archived runs). A live composer re-reads `STICKY.md` on every wake — overwriting it mid-run breaks the run; that is what this gate exists to prevent.

**(c) Same-or-older source** → already routed by Step 4's state machine (report and stop; `--reapply` is the one gated exception).

**(d) MAJOR version jump** (first component increases) → recommend the sandbox-first convention (run the update in a throwaway repo first) before applying to a real repo. Advisory only, not a block.

**(e) Committed-marker precondition.** If `git check-ignore -q -- .cursor/bootstrap/installed-version` matches, the provenance contract (Step 9's commit CONTAINS the marker) can never be satisfied — FAIL CLOSED before the confirm and before any write, showing the matching `.gitignore` source (`git check-ignore -v`). Remediation is fixing `.gitignore` (the bootstrap's own contract forbids ignoring `.cursor/`), never force-adding.

## Step 6 — Show the delta and the applicable sub-notes

Display, before the confirm:
- installed → target version (or the unknown-baseline line per Step 4)
- the pinned source identity and mode (e.g. `github kountlabs/Cursor-Bootstrap-Guide @ <sha>`, `local clone @ <sha> (override)`, `file:<12-hex> (override)`)
- every applicable `vX → vY sub-note` from the FETCHED bootstrap, selected by the canonical rule: every sub-note whose DESTINATION version is > installed and ≤ target, compared via the pinned helper. Wildcard-source headings (e.g. `v30.x → v31.0`) are included by their DESTINATION — the wildcard is heading prose, not a parsed version value.

## Step 7 — Build the mutation inventory, preflight, snapshot, ONE confirm

All mechanical transaction work runs through the pinned helper — never ad-hoc shell choreography. Every refusal or pause in Steps 5–8 ends the invocation via the Step 1 ABORT-CLEANUP (after snapshot restore where applicable) — no early exit may leave the pinned copy or run-temp root behind.

1. **Temp-target preflight:** run the fetched bootstrap through the INSTALLED extractor into a TEMP directory OUTSIDE the repo (`<run-temp>/preflight` — beside, never inside, `<state-dir>` or the pinned-source area) — `python3 .cursor/bootstrap/extract-bootstrap.py --bootstrap <fetched file> --target <temp dir>` — and require every payload verified (N/N OK, exit 0). A structural failure here (the installed extractor cannot parse a newer payload format) PAUSES naming the mismatch; remediation is the manual SECTION 0 extractor-refresh from the fetched bootstrap's own instructions. No partial state: the real target is untouched.
2. **Inventory + containment:** `python3 <state-dir>/pinned-helper.py inventory --bootstrap <fetched file> --target . --state <state-dir>` — the TOUCH/SNAPSHOT inventory is the UNION of the manifest targets, the discovered SECTION 0–4 payload-block paths (equal to the manifest set on a well-formed bootstrap — the extractor writes payloads before its manifest lookup, so the union is the true write superset), and the marker; the helper lstat-walks every write path under a NO-FOLLOW containment rule: a symlinked final component or ancestor, or an existing non-regular write target, FAILS CLOSED (exit 5) to a manual-remediation pause showing the offending paths — lexical checks are not containment (the extractor's `safe_relpath()` is lexical and its `open()` follows links). Deliberate workflow-dir symlinks get the pause, never silent traversal; special files are refused.
3. **Snapshot:** `python3 <state-dir>/pinned-helper.py snapshot --state <state-dir>` — records existence, type, bytes, and mode of every inventoried path, tracked, untracked, and IGNORED alike (`git status --short` misses ignored files, and a HEAD checkout cannot restore a pre-existing ignored file the extractor overwrote).
4. **The single confirm:** present the inventory (path count + the full list or a summarized tree), the version delta and sub-notes from Step 6, and the provenance that will be recorded. One yes/no. On no: run the Step 1 ABORT-CLEANUP (state + entire run-temp root, pinned copy included), stop, nothing written.

## Step 8 — Transactional apply

1. **Revalidate immediately before the first real write:** `git status --short` still clean, and `python3 <state-dir>/pinned-helper.py verify-containment --state <state-dir>` still exit 0. Either failing: stop via the Step 1 ABORT-CLEANUP, nothing written.
2. **Apply:** `python3 .cursor/bootstrap/extract-bootstrap.py --bootstrap <fetched file> --target .` — record the per-file report and the N/N OK count. The extractor's manifest verification is the payload success check.
3. **On ANY failure from here through the commit** (extractor FAIL lines, nonzero exit, staging or commit failure): restore FROM THE SNAPSHOT — `python3 <state-dir>/pinned-helper.py restore --state <state-dir>` (bounded to the inventory, byte/type/mode-identical, created files removed — never a broad destructive checkout), then restore the git INDEX (`git reset` — the baseline was clean, so an empty index is the pre-state), verify with `delta --state <state-dir>` printing zero lines, report the failure with the evidence, then run the Step 1 ABORT-CLEANUP (restore first, cleanup after), stop. The tree ends with no updater-owned dirt and no run-temp residue.

## Step 9 — Marker, staging, provenance commit

The THREE-SET contract: (1) the TOUCH inventory (Step 7) is a declared superset; (2) the ACTUAL DELTA is what really changed; (3) the COMMITTABLE DELTA — the actual delta minus every path `.gitignore` excludes (`git check-ignore`) — and the STAGED set equals exactly the committable delta. Never stage the inventory wholesale — that could add pre-existing ignored files — and never force-add (`git add -f`) an ignored path: a gitignored payload path stays APPLIED on disk but is never staged or committed, and is REPORTED as applied-but-ignored (Steps 9.2/9.5).

1. **Write + verify the marker:** `python3 <state-dir>/pinned-helper.py marker-write --target . --version <target version> --identity <pinned identity>` (identity per Step 2's 12-hex serialization rule). The helper read-back-verifies.
2. **Compute and DISPLAY the actual delta:** `python3 <state-dir>/pinned-helper.py delta --state <state-dir>` — the changed/created subset of the inventory (unchanged payloads drop out; on an absent-marker repair with identical payloads this degrades to the marker alone — that is the expected marker-only commit). Show the operator this delta summary together with the extractor's N/N OK count BEFORE staging — the delta + verification evidence precedes the commit that records it — splitting out the applied-but-ignored subset (delta paths `git check-ignore -q -- <path>` matches) when one exists.
3. **Empty-COMMITTABLE routes (confirmed `--reapply` only):** TWO states share the intentional `git commit --allow-empty` provenance commit, because a bare `git commit` with nothing staged exits `nothing to commit` and would be misread as an apply failure (wrongly triggering Step 8.3's rollback): (i) EMPTY ACTUAL delta — the expected outcome of a SAME-identity `--reapply` (identical payloads and an identical marker rewrite all drop out) — message note `reapply, zero delta`; (ii) ACTUAL delta non-empty but COMMITTABLE delta EMPTY — the same reapply where every remaining delta member is gitignored (the marker rewrite is identical, so only ignored payload drift survives) — message note `reapply, ignored-only delta`, with the applied-but-ignored set REPORTED per 9.2/9.5; the applied ignored changes stay on disk. Both states are verified SUCCESS — the empty result itself never triggers Step 8.3 — but a FAILING allow-empty commit (nonzero exit) is still a commit failure under Step 8.3 and restores from the snapshot exactly like any other commit failure. The allow-empty form is limited to exactly these two states: on any other route an empty COMMITTABLE delta is a defect to surface (the ABSENT-marker repair and every version-changing upgrade always commit at least the marker — guaranteed stageable by the Step 5(e) precondition).
4. **Stage exactly the committable-delta set:** for each actual-delta path, skip it when `git check-ignore -q -- <path>` matches (it stays applied but unstaged — never `git add -f`), otherwise `git add -- <path>`; verify `git diff --cached --name-only` equals the committable delta, and commit. The commit CONTAINS the marker and exactly the committable delta, nothing else. Message shape: target version, the pinned source identity (`source <sha>` / `local clone @ <sha>` / `file:<12-hex>`), and the extractor's N/N OK count — e.g. `workflow: update to v31.2 (source ba2d92b5ff26, extractor 68/68 OK)`.
5. **Show the result:** the extractor report summary and `git show --stat` of the provenance commit, plus the applied-but-ignored path list when it is non-empty.
6. `python3 <state-dir>/pinned-helper.py cleanup --state <state-dir>` — removes exactly `<state-dir>` (pinned helper copy + snapshot state), on success and on restored failure alike; also remove `<run-temp>/preflight`. The pinned source copy in `<run-temp>/source/` is NOT touched by either — it survives this step by construction (separate sibling directory, non-overlapping lifetimes): Step 10's checklist MUST be derived from those exact pinned bytes — never a re-fetch after the commit — and the copy plus the run-temp root are removed at the end of Step 10. Non-success exits never reach this step: every cancel/refusal/failure path already ran the Step 1 ABORT-CLEANUP where it occurred, so this state-only cleanup is exclusively the success path continuing to Step 10.

## Step 10 — REPORT the remaining UPDATE ONLY steps (print-only, post-commit)

Extraction is only STEP 1 of the canonical UPDATE ONLY contract — the fetched bootstrap's UPDATE ONLY section also owns advisories, stale-surface removals, `.gitignore` repairs, and plan-location/doc migrations the extractor cannot perform. After the commit:

- READ the FETCHED bootstrap's UPDATE ONLY section and PRINT the applicable post-extractor steps as a CHECKLIST, each item clearly framed as QUOTED from the fetched bootstrap, with a pointer into that file's own instructions.
- State plainly: the payload update is complete and committed, but the canonical UPDATE ONLY contract has these remaining manual steps — the operator/agent runs them under the bootstrap's own canonical text.
- This skill EXECUTES none of them — zero writes beyond payloads + marker, under `--reapply` and the normal confirm alike, from every source mode. It never maintains its own copy of migration steps; a newer release's checklist always comes from THAT release's fetched bytes — the retained temp copy from Step 9.6, never a post-commit re-fetch.
- After the checklist is printed, remove the retained pinned source copy and the now-empty run-temp root (in FILE mode the copy is the private one — the user's original path is never touched) — every run-temp artifact is now gone on this path too.

## Step 11 — Close

End by stating the repo's ahead/behind state versus its upstream (e.g. from `git status --short --branch`). Push is NEVER automatic — suggest `/push` when the operator wants the update published.

## Self-update note (do not "fix" this)

This skill's own `SKILL.md`, its `openai.yaml`, and the helper are extractor payloads this run overwrites mid-apply. That is safe by design: the executing session already holds these instructions in context, and the helper runs pinned (Step 1) — one implementation and one state schema govern the whole transaction; new bytes take effect on the next invocation. Do not add a self-exclusion here.
