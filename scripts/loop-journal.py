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
          [--help | -h]                           (v46.4 D2) prints the usage and
                                                  exits 0 — the overall text, or
                                                  one subcommand's when its name
                                                  precedes the flag; generated
                                                  from the grammar tables; reads
                                                  no log, writes nothing, needs
                                                  no --run / --role; a token that
                                                  is a flag's VALUE or a
                                                  key=value is never read as it
  SUBCOMMANDS (exactly ten):
    emit <TYPE> [--round <n> --id <finding-ID>] [--repo <root>] [key=value ...]
                 [--policy-log </abs> --iso <iso-id> --plan <plan>]  (v47.0 D4:
                 REQUIRED on an away `merge` `choice=start` — an auto- or
                 gate-disposition carrying the away pair — and refused on
                 every other emission. Its key= is `<--run>-merge` — any other
                 merge key is refused, `merge-key-not-run` — because the
                 lines below are matched by it. The listing check: the policy
                 log reads
                 `bound` for that identity, the open grant's number and hash
                 are the record's pair, `merge` is in its scope, the grant's
                 departure file under the --log's directory digests to its
                 departure=, and EVERY `Stop: merge key=<runkey>-merge
                 kind=stop-3|reserved subject=<path>[,…] — pre-approved |
                 around | park — <reason>` line of that file is folded,
                 whatever the order: a malformed `Stop: merge` line refuses
                 every away merge start (`departure-stop-malformed`); no line
                 for the key admits the start as before unless it carries
                 allow=operator-merge (`operator-merge-not-listed`); one
                 `around` | `park` line for the key refuses
                 (`departure-stop-restricts`); all `pre-approved` admits it
                 only with allow=operator-merge, the class in force by the
                 pre-approval fold, a `passed` verdict, no ungated= and no
                 --event-ts, and the subject test over the union of those
                 lines' subjects — each in the merge's diff (tip against its
                 merge base with the journal's base branch), no other path
                 of the diff in any subject's own directory. Whether the
                 merge deploys production, and what else its diff holds, is
                 NOT read here — the composer's read, as before)
                 [--read-log <probe-log>]  (v33.0 D3: the READ-ONLY prior-record
                 source for a keyed ROLE:start or a keyed cap transition —
                 the sink stays stdout)
                 [--liveness <min>|off]    (v33.0 D5: the must-pause re-fire
                 dedupe window; needs --log; default 10)
                 [--allow-repeat-hash]     (v34.1 D10: OWNERSHIP:commit with
                 --log ONLY — record a hash that log already holds; value-less)
    escape-check --capture pre|post --leg <leg> --log-root <dir>
                 --root <name>=</abs/path> [--root ...]
                 [--edit-surface <root-name>] [--allow-path <root>:<rel>[;...]]
                 [--iso <this run>] [--liveness <min>|off]
                 (v33.0 D4: the edit-surface-aware verdict + the liveness-gated
                 base-dirt attribution)
    flush [--dry-run]
    idle-check
    run-close --iso <iso-id> --base </abs/base> --outcome <o> [--plan] [--attest]
                 [--merge-commit <7-40 hex>]  (v33.2 /close-run D10/D11: the
                 squash-aware merged close — `--outcome merged` (and, v40.0,
                 `--outcome group-merged`, below) ONLY; admits a
                 retained-green | merged | active+`--attest owner-dead` journal,
                 verifies the sha against the fetched base (ancestry fast path,
                 else `merge-tree --write-tree`), writes `merged="<ts> <sha>"`,
                 then enters the EXISTING verified-merge teardown with
                 `branch -D`; refuses report-only on every other outcome)
                 (v33.8: `--outcome reconcile` closes RECORD-ONLY any journal
                 not intent | created | merging | cleaned | active whose
                 absolute worktree= and branch= are both confirmed gone —
                 state=cleaned + reconciled="... prior-state=<token>"; deletes
                 nothing; refuses exit 2 before any write when the --log
                 folder is missing)
                 (v48.0 D17: THE LIVE-ROLE GUARD — the two cells that tear
                 down, the verified-merge cell and the pre-journal marker
                 unlink, refuse before their first write unless the
                 role-liveness reader says `over` for every leg the run's log
                 folder holds evidence of: a `live` leg refuses whatever was
                 attested; an `unknown` leg refuses unless `--attest
                 owner-dead` rides the call; no leg evidence admits)
                 (v40.0 Phase 1 D2/D3: `--run stage-<N> --outcome group-merged
                 --merge-commit <sha>` — the GROUP close of a LIVE run, no
                 teardown: admits an `active` journal (its live marker
                 expected, no --attest), looks `stage-<N>` up in the journal's
                 composer-written `groups=stage-<N>:<tag>[,…]` key (a non-final
                 entry), binds the merge commit — in the fetched base, ON the
                 base branch's first-parent chain, exactly two parents,
                 `<sha>^2` == the run-branch tip — then appends
                 `merged_stage_<N>="<ts> <sha> <tag>"` (state stays `active`)
                 and writes `cell=group-merge verdict=complete group=<tag>
                 merge_commit=<sha>`; THEN the fast-forward leg: fetch
                 `origin/<base-branch>`, `merge --ff-only <that sha>` on the base
                 checkout (on its base branch) and on the recorded worktree —
                 both with nothing in progress and no tracked change, both
                 ancestor-or-equal of the sha before either moves, both EQUAL
                 to it after — `ff_stage_<N>="<ts>
                 <sha>"`, `cell=group-ff verdict=complete ff=<sha>` — refused
                 with the group key kept, the record naming the cause (v46.4
                 D8): `detail=checkout-not-ready` (a precondition failed before
                 the fetch — no usable base_branch=, the base off its branch,
                 an operation in progress, an uncommitted tracked change),
                 `detail=fetch-failed` (the fetch failed, or its ref did not
                 resolve), else `detail=base-not-fast-forwardable`. A
                 present `merged_stage_<N>` REPLAYS: a matching sha and tag →
                 `verdict=already-closed` and the fast-forward leg when
                 `ff_stage_<N>` is absent (both present → the two records,
                 nothing written); a mismatch → refused
                 `detail=group-identity-mismatch`. Refused before any write:
                 `journal-not-active`, `group-not-in-journal`,
                 `group-is-final`, `merge-commit not found`, `worktree-absent`,
                 the identity-mismatch cell, `merge-commit not in base (fetch
                 first)`, `run-branch ref absent`, `merge-parent-mismatch`, and
                 the retro-pointer refusal; no `merged=` is ever written here)
                 (v46.4 D8: on BOTH --merge-commit paths — `--outcome merged`
                 and `--outcome group-merged` — a sha the base checkout cannot
                 resolve is resolved ONCE more after `git fetch --quiet origin
                 refs/heads/<base-branch>` on the base checkout, when the
                 journal names a usable base_branch=; `merge-commit not found`
                 is reported only if it is still missing)
                 [--grant <n> --away-check <12hex>]  (v44.0 D4 — the group close
                 under a bound away grant: both or none (`grant-flags-pair`),
                 `--outcome group-merged` only (`grant-flags-outcome`), --log
                 named stage-<N>-probe.log (`grant-flags-log`). Once BOTH
                 checkouts hold the fetched base, and BEFORE `ff_stage_<N>` is
                 written, the leg appends ONE unpaired `OWNERSHIP:
                 auto-disposition … key=stage-<N>-set-refresh choice=rebaselined
                 to=<the group's MERGE COMMIT> rec=composer:group-ff away=<n>
                 away_check=<h>` to that log — the accepted VERSION of every
                 file at the merge commit for `quoted-block`'s fold (never set
                 membership) — and prints `group-ff: rebaselined at
                 <log>:<line>` on stderr after the report. The existence check
                 runs before every append (the normal path, the replay, the
                 already-closed branch): a matching record → nothing written;
                 the same key and pair at another to= → refused
                 `rebaseline-conflict`; a doubtful line naming the key →
                 refused `rebaseline-unreadable`. Without the pair: the v40.0
                 close, no record)
    fold-delegation --base </abs/base> --iso <iso-id> --leg <leg>
                 (v32.2 T2.3 — the delegation staging→canonical promotion; the
                 canonical stage-<N>-delegation.log's ONLY writer; COMPOSER-ONLY
                 at the grant layer: spawned-role grants carry only the narrowed
                 emission shapes, so this mutating subcommand is unreachable
                 from a scoped role — under perms=bypass no grant boundary
                 exists and the close-table confirm covers it)
    attest-check --policy-log </abs/policy.log> --iso <iso-id> --plan <plan>
                 [--key high-auto|gates]
                 (v33.0 D12 — the READ-ONLY identity-bound attestation read:
                 the FIRST config-snapshot per key, validated with the SAME
                 emit-side rules the writer applied, bound to --iso/--plan;
                 exit 0 = bound + unrevoked; exit 3 = absent | malformed |
                 wrong-identity | off-at-start | revoked, each named on
                 stdout; COMPOSER-ONLY under the grant sentence)
    away grant|end|check|report|ci-verdict|lint --run <runkey> --role composer
                 --policy-log </abs/policy.log> --iso <iso-id> --plan <plan>
                 [--log-root </abs/log-root>] [--out </abs/file>] [--base </abs/base>]
                 [scope=<s> [allows=<class>[:<n>][,…]] [widens=<n>] | grant=<n> reason=<r> | grant=<n> | pr=<n> tip=<sha>]
                 (v47.0 D5 — the ONE departure check that refuses: `grant`
                 refuses, `departure-missing-fallback`, nothing written and
                 before any warning line, a departure file with no answered
                 `Usage fallback:` line — `Usage fallback: <profile dir>`,
                 `none — <why>…` or `n/a — <why>`, an optional list marker
                 before it, fenced lines not read; `lint` prints the word
                 `usage-fallback-missing`, first, and still exits 0. Every
                 other check stays a warning: among them, v47.0 D3, one
                 `merge-stop-malformed line=<N>` per line that begins `Stop:
                 merge` and is not in the fixed form — see `emit`.
                 v47.0 D22 — `grant … widens=<n>`: the one-step widening, the
                 one `grant` admitted while a grant is bound. Admitted only
                 when grant n is the bound grant, the new scope is a strict
                 superset of its scope, no release act of it is in flight,
                 no fold of `away check` reads unknown, and the new departure
                 file's bytes BEGIN with grant n's own (which still digest to
                 its departure=). ONE write of the two existing shapes —
                 grant n's `away-end reason=back`, then grant n+1 — and three
                 stdout lines: `away: ended …`, grant n's report recipe,
                 `away: granted …`. The new grant's allows= is the departure
                 classes in force under grant n (a limit written out) plus
                 the call's own allows= — except that a widening adding
                 staging or production never carries foreign-merge or
                 operator-merge: they ride only when the call names them
                 again. widens= is stored on neither record. A retry after an
                 interrupted write: grant n still bound → the widening; grant
                 n ended and none bound → refused `widen-prior-ended` with
                 the plain grant to type; a malformed log → refused; grant
                 n+1 bound at this scope with its file intact → its `away:
                 granted` line printed again, nothing written)
                 (v46.4 D5 — `lint`: READ-ONLY, the departure-file check BEFORE
                 a grant binds. `grant`'s four flags, all required, and no key.
                 It reads the file the NEXT grant would read —
                 <log-root>/away-<recorded grants + 1>-departure.md — through
                 the one function `grant` warns from, and prints on stdout one
                 `away-lint: <warning>` line per warning, then `away-lint:
                 file=<base name> warnings=<n>`; exit 0 whenever the file was
                 read, whatever the policy log's state (lint reports, it
                 never refuses — v47.0: the missing `Usage fallback:` line
                 included, which `grant` does refuse);
                 a missing or unreadable file is `grant`'s refusal,
                 an unreadable policy log its exit 3; no record and no file is
                 written. D6 — a warning BOTH verbs print, `grant` as
                 `away-warning:` on stderr with its exit and record unchanged:
                 `heading-has-double-quote line=<N>` for each line of the
                 departure file, outside a fenced block and wherever it sits,
                 that quotes a heading holding a double quote — the word
                 `heading`, then the text in backticks (a double quote before
                 the closing backtick) or in double quotes (more than two
                 double quotes from the opening one to the next backtick or
                 the line's end); one per line, after the item-7 warnings. A
                 best-effort read of free text: a spelling it does not know is
                 not warned about, and a second quoted phrase on the line can
                 be warned about needlessly)
                 (v44.0 — plan-away-autonomous-rails D2/D3/D9/D16/D17:
                 `grant` admits `allows=` — the departure-time pre-approvals,
                 comma-joined from records-merge,pr-fix-cycles,ci-advisory-fix,
                 foreign-merge,operator-merge (v47.0 D1 — the last one: a
                 merge the departure file lists `pre-approved`, enforced at
                 the merge start, see `emit`), `:<n>` on pr-fix-cycles only
                 (bare = limit 3), operator-task refused (per task — a
                 record), else
                 `bad-allows`; stored as a trailing kv on the away-grant record
                 outside config_hash; and WARNS on stderr, exit and record
                 unchanged, `away-warning: markdown-without-heading file=<path>`
                 for every bullet of the departure file's LAST item 7 block
                 (`## 7.` / `### 7.`) whose backtick token names a `.md` path
                 with no `heading` on the bullet, or `away-warning:
                 item7-section-not-found`. The `away:` line carries, after
                 holds=/held= and before reason=, ` parks=<n|unknown>[
                 parked="<key>[ path=<p>][; …]"]` — the STRICT production-park
                 fold: open deploy-production must-pauses per (run=, key=),
                 closed by a later writer-valid gate-disposition only, EVERY
                 doubtful relevant line → unknown — then ` allows=<n|unknown>[
                 allowed="<class>[ path=<p>][ limit=<n>][; …]"]` — the
                 pre-approval fold: the bound grant's allows= entries, then its
                 `OWNERSHIP: auto-disposition key=stage-<N>-pre-approval
                 instr=<12hex> choice=allowed|cleared allow=<class> [path=<id>]
                 [limit=<n>] rec=composer:allow|clear` records (the away pair
                 required; instr= distinct per instruction, a replay ignored, a
                 conflict unknown) in reader order, the last distinct word per
                 class (+ path) winning; unknown whenever the state is not
                 bound, on a doubtful `-pre-approval` line, or an unreadable
                 log — nothing proceeds on unknown. `report` §1 lists the
                 pre-approvals in force and the clears from the same fold.)
    away census --run <runkey> --role composer --base </abs/base>
                 (v37.0 Decisions 4/8 — READ-ONLY: one `census:` line per
                 <base>/.cursor/loops/<iso>-policy.log — its away state, open
                 grant, the run's journal state, marker, newest probe-log age —
                 a filled `away end` `recipe:` line after each bound log whose
                 journal is cleaned or merged, then `census: logs=<n> bound=<n>`;
                 writes nothing; exit 0 once the directory is listed. v37.0
                 Decision 2: `away end` reason=release-done|run-stop WITH
                 --log-root refuses while the open grant's window holds a
                 release act `start` with no outcome. v40.0 D5: `away end`
                 reason=release-done WITH --log-root also REQUIRES --base and
                 is admitted only while <base>/.cursor/loops/<iso>-isolation
                 reads merged | cleaned | retained-green — refused
                 `run-not-closed state=<s>` on every other state, nothing
                 written; a park at any release group keeps the grant bound)
                 (v34.0 D4/D5 — the away grant: `grant` reads
                 <log-root>/away-<n>-departure.md and appends
                 `OWNERSHIP: away-grant` (grant= numbered by the tool,
                 departure= + config_hash= derived); `end` appends
                 `OWNERSHIP: away-end`; `check` prints ONE `away: state=…` line
                 — exit 0 = bound (departure file intact), 3 = ended | absent |
                 malformed | wrong-identity | departure-mismatch — with the run's
                 open holds (`holds=<n|unknown> [held="…"]`, v35.1); `report`
                 prints the eight-section report built from the policy log and
                 every stage-*-probe.log under --log-root, and with --out also
                 writes it — sections 1–7 as at v46.3, byte for byte; section
                 8 (v46.4 D9), "Also decided or stopped during the grant",
                 lists what the grant's window holds that they do not: each
                 auto-disposition, gate-disposition, profile-switch and
                 smoke-pass record sections 3–7 leave out (a decision under
                 the run's standing settings, a cap raise or accept, a profile
                 switch, a smoke section 5 does not list — one with no
                 smoke_by= marked as read as operator), with its subtype and
                 every key=value it holds, or as `not a writer-valid record:
                 <why>` when the writer would refuse it; and each question
                 answered inside the window, whenever it was opened, with the
                 answer and the wait (no wait when the answer's timestamp is
                 the earlier one). The ONE state function serves every verb;
                 COMPOSER-ONLY — `emit` refuses the grant records)
                 (v35.1 Decisions 1–4 — `ci-verdict`: the helper's own CI read
                 for pull request pr= at commit tip= — `gh pr view` plus the two
                 commit-bound inventories, by argv, from --base, under ONE 90 s
                 deadline — judged by ONE pure verdict function, appended as
                 `OWNERSHIP: ci-verdict` to <log-root>/<runkey>-probe.log, then
                 printed as ONE `ci-verdict: verdict=…` line; exit 3 unless the
                 away state is bound with `merge` in scope, or on a failed write;
                 `emit` refuses the subtype. The away `merge` `choice=start` is
                 admitted only on a fresh admitting verdict for its tip=)
    quoted-block --base </abs/base> --file <repo-relative> --heading <text>
                 --from <commit-ish|blob> --to <commit-ish|blob>
                 [--baseline <commit-ish|blob>] [--log-root </abs> grant=<n> away_check=<hash>]
                 (v40.0 Phase 0 D8 — READ-ONLY, identity-less, writes no
                 record: compares the bytes of ONE heading-scoped markdown
                 block of <file> between two sides — a commit-ish reads <file>
                 at that commit, a blob id reads the blob itself (the departure
                 file's recorded blob); both as raw bytes through `cat-file -p`,
                 no textconv or filter — and prints ONE line `quoted-block
                 file=… heading=… from=<sha> to=<sha>
                 verdict=same|changed|missing|ambiguous[ detail=from|to|both]
                 accepted=<n> matched=from|baseline|<ts>|none
                 [matched_at=<log>:<line>] [matched_class=<c>] mode=block|blob`;
                 the block is the ATX heading line whose text equals --heading
                 VERBATIM through the line before the next heading of equal or
                 higher level (a `#` line inside a ``` / ~~~ fence is never a
                 heading); exit 0 on same | changed, exit 2 on missing (the
                 file or the heading absent on a side) | ambiguous (the heading
                 recurs on a side) with the line still printed; the one reader
                 of /close-run → Under an away grant item 4's quoted-block
                 contract, which items 5 and 10 and the execute-loop SKILL's
                 effective-set readers point at.
                 v42.0 (D1 — refresh-aware): --heading is OPTIONAL — absent,
                 the whole blob of <file> is compared (mode=blob; `ambiguous`
                 never) for a refreshed workflow or configuration path;
                 --log-root </abs> with the TWO admitted keys grant=<n> and
                 away_check=<the grant's 12-hex config_hash> (all three or
                 none; an existing directory; any other key refuses) folds
                 the grant's `OWNERSHIP: auto-disposition` records of key
                 class `set-refresh` for the file — those carrying THIS
                 grant's number AND hash and a completed choice
                 (requoted|refreshed|rebaselined; a same-number record of another grant,
                 a log copied from another run, or a `start` shape never
                 folds — round 13 PR-MED-018; no policy-log read) — in block
                 mode those whose heading= equals --heading, in blob mode
                 those with no heading= (v44.0 D5: a `rebaselined` record —
                 the group close's re-baseline at the group's merge commit,
                 no file= / heading= — bypasses both filters: its to= must be
                 a commit, <to>:<file> is read like a side, and a `missing` or
                 `ambiguous` read SKIPS the record, never refuses; versions
                 only, never membership) — read from every stage-*-probe.log
                 under the root (the permissive reader; a writer-invalid line
                 is not a record), each record's to= (40-hex; a commit or a blob id,
                 resolved like a side) one ACCEPTED VERSION; --baseline (the
                 reader's opt-in — item 4's departure blob on a Markdown
                 quoted-procedure file) joins the set. The verdict keeps
                 today's order: BOTH original sides first — missing on either
                 wins, then ambiguous, each matched=none with no accepted
                 version consulted — and only when both yield one block is it
                 `same` when the --to block equals the --from block
                 (matched=from), the --baseline block (matched=baseline), or
                 ANY accepted version (matched=<that record's ts>, with
                 matched_at=<log>:<line> and, when the record carries
                 workflow_class=, matched_class=<value>; the first equal
                 version in reader order), `changed` when it equals none
                 (matched=none); --from is never replaced; accepted=<n> is the
                 count folded (0 without --log-root). A --baseline that yields
                 no single block, an unreadable log, or a record whose to= is
                 malformed, unresolvable, of another object kind (a tree, a
                 tag — a record copies a printed commit or blob id), or
                 yields no single block REFUSES, naming the record's log line —
                 exit 2, nothing printed: the reader parks, never a silent
                 requote; the log root is read only, nothing written)
    records-delta --worktree </abs checkout>
                 --base-ref <commit-ish> --tip <commit-ish>            (merge mode)
                 | --range <from>..<to|WORKTREE> --alphabet records|docs (path mode)
                 [--also <path|prefix/>[,…]] [--departure </abs file>]
                 (v47.0 D7 / D9 — READ-ONLY, identity-less, writes no record:
                 the records-path reader. It prints `records-delta:
                 mode=merge|path alphabet=records|docs
                 delta=empty|records|docs|mixed marker=yes|no|n/a files=<n>
                 outside=<n> …` and one `records-delta: file=<path>
                 class=records|docs|other[ both_sides=yes][ marker=yes]` line
                 per path. MERGE mode classifies a merge of --base-ref into
                 --tip in the records alphabet: the both-sides files (changed
                 since the merge base on each side) plus every path whose
                 working-tree content differs from both commits; marker=yes on
                 an unmerged index entry or a conflict-marker line in a delta
                 file — a run of at least the path's effective
                 `conflict-marker-size` (seven by default; the SMALLER of the
                 attribute at --tip and in the working tree, a malformed or
                 out-of-range value read on its low side — never a size above
                 the one Git wrote the markers at; needs Git 2.40 or newer for
                 `check-attr --source`, else exit 3) of `<` or `>` at a
                 line's start, then a blank or the line's end; a delta file
                 whose metadata or bytes cannot be read, or that is not a
                 regular file, is exit 3, never marker=no — and so is a delta
                 file Git may not have written as it merged it: one whose
                 attributes, at the tip or in the working tree, name a
                 `working-tree-encoding`, a `filter`, or a `merge` driver other
                 than text / binary / union, or any scanned file under a
                 `merge.default` that is not one of those three
                 (marker-scan-unfit; end-of-line conversion is not such a
                 case — the scan reads a CRLF marker), and any scan at all
                 when a tracked attribute file moved across the merge: a
                 `.gitattributes`, at any depth, that changed between the
                 merge base and --base-ref or differs in the working tree
                 from --tip (the two attribute reads are then not known to
                 be the attributes Git wrote under). Every name diff
                 here, and the listing check's, pins
                 `--ignore-submodules=dirty`: a changed submodule pointer is
                 listed whatever `diff.ignoreSubmodules` or `.gitmodules`
                 say; a submodule's own uncommitted content is not.
                 PATH mode classifies the paths that differ across a
                 range (WORKTREE: the working tree, untracked files included)
                 in the named alphabet. The RECORDS set: any CHANGELOG.md, the
                 root AGENTS.md, everything under .cursor/plans/, plus
                 declared exact paths and `/`-terminated prefixes (--also; the
                 `Records paths:` lines of --departure, read together) — no
                 wildcards; a spawn dependency and anything under a directory
                 named .github, scripts, .claude, .agents or .codex, at any
                 depth, is never a records file, tested on every declaration
                 (refused: records-path-protected; a malformed entry:
                 records-path-malformed) and on every path classified. The
                 DOCS floor: a `.md` file that is not an instruction surface —
                 no SKILL.md, STICKY.md, AGENTS.md, CLAUDE.md or bootstrap.md,
                 nothing under a directory named .claude, .agents, .codex or
                 .github, or under .cursor/rules, .cursor/commands, .cursor/templates
                 or .cursor/bootstrap, at any depth.
                 Exit 0 whenever the input was read; 2 on a usage or
                 declaration refusal; 3 on an input that cannot be read)
    (v46.0: `run-bounded` is REFUSED here — the bounded runner is `python3 scripts/loop-run-bounded.py`)

  emit TYPE tokens: MONITOR CONSUME CLASSIFY ADOPT KILL_DUP SENTINEL_ARMED
  SENTINEL_FIRE SPAWN VERIFY_FAIL
  IDENTITY VERIFY_OK NOTIFY:<state> WATCH:armed WATCH:cancelled ROLE:start
  ROLE:end ROLE:round OWNERSHIP:<subtype>.

SEAT GATE (R16 PR-HIGH-001, operator-disposed coherent extension): every
composer-owned OWNERSHIP subtype (COMPOSER_ONLY_SUBTYPES) and the flush WRITE
path require `--role composer`; the subject-role shapes (exit-census,
escape-check) and the role-owned `emit VERIFY_OK` stay role-open, and
`flush --dry-run` stays read-open for RESUME derivation. The gate is a
MIS-ATTRIBUTION guard, NOT caller authentication — `--role` is argv for every
caller; the boundary that makes composer-owned records unreachable from a
spawned role is the GRANT/PROCESS layer (the wrapper's composer-only
exact-path grant pattern), retained as the R12 PR-MED-001 item.

THE COMPOSER SEAT (v48.0, plan-loop-autonomy-group-2 D12 / D14): while a
watcher takeover (scripts/loop-watchdog.py) holds a run's seat — the lock on
`<base>/.cursor/loops/<iso>-seat` — every composer-owned write of that run is
refused (exit 2, nothing written) unless the caller carries the takeover's
nonce in LOOP_SEAT: `emit` under `--role composer`, `idle-check`, the `flush`
write path, `away grant | end | ci-verdict`, `run-close`, `fold-delegation`.
An emit under a role's own flag, every `escape-check` and every read-only
subcommand are never gated; a run with no seat file is admitted as before.
The admission holds the run's gate (`<iso>-seat.gate`) through the
subcommand's read, decision and write. With LOOP_SEAT set, `emit` refuses an
away production start. The tables, the one admission routine and what the
seat does not protect are stated at SEAT_SUBCOMMANDS below; the readers the
watcher loads are named by WATCHER_RUNTIME.

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
import json
import os
import re
import secrets
import shutil
import signal
import stat
import subprocess
import sys
import time

# --- v45.0 (plan-windows-port-and-router T1.1 / D21) — host capabilities -----
# ONE two-field table, read at import and FLIPPED by the selftest's Linux legs
# on the imported module (`helper.HOST["fd_relative"] = False`): `fd_relative`
# — the host opens and stats RELATIVE to a held directory descriptor with
# no-follow semantics (os.supports_dir_fd non-empty AND O_NOFOLLOW present:
# Linux, macOS, the BSDs); `is_windows` — the path spelling is drive-lettered
# (os.name "nt"; canon_path's spelling rules key on it, never on sys.platform).
# The three primitives below (_open_at / _stat_at / _replace_at) hold the ONLY
# dir_fd= / O_NOFOLLOW / O_DIRECTORY / O_NONBLOCK uses in this file: on the
# fd-relative leg they emit today's syscalls byte-for-byte (the ELOOP and
# race-guard legs are unchanged); the FALLBACK leg (Windows: no dir_fd, no
# O_NOFOLLOW, a directory is not openable as a descriptor) holds the directory
# PATH as its handle, lstat-refuses a symlink BEFORE the open and identity-binds
# (st_dev, st_ino) across it — an st_ino of 0 is unbindable and refuses. The
# fallback is check-then-open: its lstat→open window is a documented residual
# (D8 / Accepted Assumptions), never claimed equivalent to the held-fd leg.
HOST = {
    "fd_relative": bool(os.supports_dir_fd) and hasattr(os, "O_NOFOLLOW"),
    "is_windows": os.name == "nt",
}


class _AtIdentityError(OSError):
    """Fallback leg: the object at the name changed identity between the
    pre-open lstat and the post-open fstat, or has no bindable identity
    (st_ino 0). An OSError, so a reader that classifies OSError (the census)
    reads it as unreadable; the `_fd_*` family maps it to its existing
    check/open-race refusal class."""


def _at_path(dir, name):
    """The fallback leg's pathname for `name` under the directory handle
    `dir` (a PATH there; None means `name` is already the whole path)."""
    return name if dir is None else os.path.join(dir, name)


# Windows FILE_ATTRIBUTE_REPARSE_POINT — set on a directory JUNCTION (and every
# other reparse point) whose lstat reports S_IFDIR with the link bit CLEAR
# (round 18 PR-HIGH-001). A POSIX stat result has no st_file_attributes, so the
# test reads 0 there and the fd-relative leg is untouched.
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def _is_redirect(st):
    """A symlink OR a Windows reparse point (a junction / name surrogate):
    the one "this component redirects" test the fallback leg's no-follow
    checks apply — the link bit alone would admit a junction."""
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & _FILE_ATTRIBUTE_REPARSE_POINT)


def _open_at(dir, name, flags, *, follow, mode=0o644, directory=False, nonblock=False):
    """Open `name` relative to the held directory handle `dir` — an fd on the
    fd-relative leg, a PATH on the fallback leg, None when `name` is absolute.
    `directory=True` returns a DIRECTORY HANDLE: an O_DIRECTORY fd on the
    fd-relative leg, the joined PATH on the fallback leg (after a stat proving
    a real directory — a symlink OR a Windows reparse point (a junction —
    round 18 PR-HIGH-001) raises ELOOP under follow=False, a non-directory
    ENOTDIR). `follow=False` refuses a redirection at the final component:
    O_NOFOLLOW on the fd-relative leg; on the fallback leg an lstat before the
    open (ELOOP on a symlink or reparse point) plus the (st_dev, st_ino) bind
    after it (_AtIdentityError on a mismatch or an unbindable st_ino 0). An O_CREAT
    open tolerates an absent name on the fallback lstat exactly as O_CREAT
    does. `nonblock=True` adds O_NONBLOCK where the host has it (a FIFO never
    stalls the open; the caller fstat-classifies the leaf). Raises OSError as
    os.open does; a ValueError (a NUL in the name) propagates as today."""
    if HOST["fd_relative"]:
        f = flags
        if directory:
            f |= os.O_DIRECTORY
        if not follow:
            f |= os.O_NOFOLLOW
        if nonblock:
            f |= os.O_NONBLOCK
        return os.open(name, f, mode, dir_fd=dir)
    path = _at_path(dir, name)
    pre = None
    if directory or not follow:
        try:
            pre = os.stat(path) if follow else os.lstat(path)
        except FileNotFoundError:
            if directory or not (flags & os.O_CREAT):
                raise
        if pre is not None and _is_redirect(pre):
            raise OSError(errno.ELOOP, "symbolic link or reparse point not followed (fallback leg)", path)
    if directory:
        if not stat.S_ISDIR(pre.st_mode):
            raise NotADirectoryError(errno.ENOTDIR, "not a directory", path)
        return path
    if nonblock:
        flags |= getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags | getattr(os, "O_BINARY", 0), mode)
    if pre is not None:
        try:
            post = os.fstat(fd)
        except OSError:
            os.close(fd)
            raise
        if pre.st_ino == 0 or post.st_ino == 0 or (post.st_dev, post.st_ino) != (pre.st_dev, pre.st_ino):
            os.close(fd)
            raise _AtIdentityError(errno.EIO, "identity changed between check and open, or unbindable (st_ino 0)", path)
    return fd


def _stat_at(dir, name, *, follow):
    """stat `name` relative to the held directory handle (fstatat on the
    fd-relative leg; a pathname stat / lstat on the fallback leg)."""
    if HOST["fd_relative"]:
        return os.stat(name, dir_fd=dir, follow_symlinks=follow)
    return (os.stat if follow else os.lstat)(_at_path(dir, name))


def _replace_at(src_dir, src, dst_dir, dst):
    """renameat relative to the held directory handles (pathnames on the
    fallback leg). The launcher's bounded retry on a held-open destination
    (Windows PermissionError) is its own (T2.5); this primitive raises as
    os.replace does."""
    if HOST["fd_relative"]:
        os.replace(src, dst, src_dir_fd=src_dir, dst_dir_fd=dst_dir)
    else:
        os.replace(_at_path(src_dir, src), _at_path(dst_dir, dst))


def _dir_close(handle):
    """Release a directory handle a walk returned: an fd is closed; a
    fallback-leg PATH has nothing to release. os.listdir accepts both."""
    if isinstance(handle, int):
        os.close(handle)


def canon_path(p, resolve=True):
    """v45.0 (T1.3 — D17 / D31): THE one canonical path spelling, produced by
    Python — absolute, forward slashes, an upper-case drive letter on a
    Windows host (`C:/Users/...`), recorded in identity records, escape
    baselines, journal and marker alike. `resolve=True` (the default) is the
    PHYSICAL form (realpath first); `resolve=False` is the SPELLING form —
    the separator, drive-letter and MSYS conversions ONLY, no realpath and no
    normpath (component collapse belongs to physical resolution or to the
    containment walk's own normpath: `sym/../x` denotes different objects
    lexically and physically — PR-MED-001 round 10) — reserved for the ONE
    site that must keep a recorded descendant's components visible until its
    no-follow walk (_fd_walk_contained_logroot). On a POSIX host every output
    is byte-identical to today's realpath (or to the input, unresolved): a
    backslash is a legal filename character there and is never reinterpreted.
    On a Windows host (HOST["is_windows"]): a UNC spelling (`//srv/share`,
    `\\\\srv\\share`) refuses by the path-rule class naming it; under MSYSTEM
    an MSYS drive spelling `/c/...` converts by the `^/([A-Za-z])(/|$)` →
    `C:/` regex alone — what `cygpath -m` prints for a drive path, no
    subprocess (D31); any other `/`-rooted spelling refuses by name (spell it
    `C:/...`); `\\` becomes `/`; the drive letter upper-cases; a realpath that
    lands on a UNC share refuses the same way. A relative input is left to the
    callers' existing absolute-path checks (realpath absolutises against cwd
    exactly as today)."""
    if not HOST["is_windows"]:
        return os.path.realpath(p) if resolve else p
    import ntpath
    s = p.replace("\\", "/")
    if s.startswith("//"):
        refuse("path %s is a UNC spelling — the loop's canonical spelling is a drive path (`C:/...`); a UNC share is refused by name (path-rule)" % p[:120])
    m = re.match(r"\A/([A-Za-z])(/|\Z)", s)
    if m and os.environ.get("MSYSTEM"):
        s = m.group(1).upper() + ":/" + s[len(m.group(0)):]
    elif s.startswith("/"):
        refuse("path %s is a `/`-rooted spelling on a Windows-native host — spell it as a drive path (`C:/...`)%s"
               % (p[:120], "" if os.environ.get("MSYSTEM") else " (the MSYS `/c/...` form converts under MSYSTEM only)"))
    if resolve:
        s = ntpath.realpath(s).replace("\\", "/")
    if len(s) >= 2 and s[1] == ":" and s[0].isalpha():
        s = s[0].upper() + s[1:]
    if s.startswith("//"):
        refuse("path %s resolves to a UNC share (%s) — the loop's canonical spelling is a drive path; refused by name (path-rule)" % (p[:120], s[:120]))
    return s


def path_inside(path, root):
    """v45.0 (T1.3; PR-MED-001 round 4): THE one containment predicate over
    CANONICAL values (canon_path on both sides). `/` is the separator on every
    host — never os.sep, which is `\\` on Windows and would never prefix-match
    a `C:/...` value (the launcher's `inside()` and the Python wrapper's
    containment rules consume this, T2.3 / T2.5). Equality is inside;
    `root + "/"` is the descendant prefix, a root already ending in `/`
    (POSIX `/`, a drive root `C:/`) used as is; a different drive is outside;
    a sibling sharing a name prefix (`C:/a/bc` against `C:/a/b`) is outside."""
    if path == root:
        return True
    prefix = root if root.endswith("/") else root + "/"
    return path.startswith(prefix)


def _configure_std_streams():
    """v45.0 (T1.4): UTF-8 + LF on the helper's own text streams, at the
    executable boundary ONLY — called from main(), never at import (D30: the
    module import has no side effect; the launcher and the Python wrapper
    configure their own streams the same guarded way at their entrypoints,
    T2.3 / T2.5; v46.0: scripts/loop-run-bounded.py, which loads this module
    and never passes through main(), calls this function at ITS entrypoint
    before cmd_run_bounded). Windows Python's piped stdout is the console code page
    (cp1252) until 3.15 and would raise on `→` or an em-dash; `newline="\\n"`
    keeps LF framing on every host. Guarded: a stream with no `reconfigure`
    (a replaced sys.stdout, None) is left alone, and a reconfigure the stream
    refuses is swallowed — the helper's output then falls back to the host's
    own configuration rather than failing before its first record."""
    for name in ("stdout", "stderr"):
        s = getattr(sys, name, None)
        if s is None or not hasattr(s, "reconfigure"):
            continue
        try:
            s.reconfigure(encoding="utf-8", newline="\n")
        except Exception:
            pass


_GIT_BIN = []

# v47.0 Step HA3 (candidate 2): git's own repository-LOCAL environment — the
# names `git rev-parse --local-env-vars` prints — is never handed to a git
# call of this helper. Every call names its checkout with `-C`; an inherited
# GIT_DIR / GIT_WORK_TREE / GIT_INDEX_FILE / GIT_OBJECT_DIRECTORY (a hook's
# environment, or a tool's that exported them) points that call at ANOTHER
# repository, index or object store than the one `-C` names, and an inherited
# GIT_CONFIG_COUNT / GIT_CONFIG_PARAMETERS puts configuration under the
# evidence reads. ALL the helper's git calls drop them, reads and acts alike —
# a verification read from one repository beside an act on another would be
# worse than either. The list is git's own; what is not repository-local
# stays as the caller has it (GIT_CONFIG_GLOBAL / _SYSTEM / _NOSYSTEM, the
# identity and editor variables, GIT_OPTIONAL_LOCKS).
GIT_LOCAL_ENV = ("GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_CONFIG", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT",
                 "GIT_OBJECT_DIRECTORY", "GIT_DIR", "GIT_WORK_TREE", "GIT_IMPLICIT_WORK_TREE", "GIT_GRAFT_FILE",
                 "GIT_INDEX_FILE", "GIT_NO_REPLACE_OBJECTS", "GIT_REPLACE_REF_BASE", "GIT_PREFIX", "GIT_SHALLOW_FILE",
                 "GIT_COMMON_DIR")


def _git_env(**extra):
    """The environment of every git call this helper makes: the caller's,
    minus git's repository-local variables (GIT_LOCAL_ENV), plus `extra`."""
    env = {k: v for k, v in os.environ.items() if k.upper() not in GIT_LOCAL_ENV}
    env.update(extra)
    return env


def _git_bin():
    """v45.0 T1.1 (PR-MED-001 round 7): the ONE git resolution for every
    subprocess site that ran a bare `git` — shutil.which("git") at first use,
    cached for the process. PATHEXT-aware on Windows, so a PATH-leading
    `git.cmd` shim intercepts (CreateProcess never searches PATHEXT for a bare
    name); the PATH-first binary on POSIX, exactly as the bare name resolved.
    Mirrors gh's resolution (gh_executable). An absent git keeps the bare
    name so the launch fails as today, through each caller's exception shape."""
    if not _GIT_BIN:
        _GIT_BIN.append(shutil.which("git") or "git")
    return _GIT_BIN[0]


# --- BEGIN EMBEDDED VOCABULARY V_base (generated by scripts/loop-grammar-oracle.py --emit-vocab; regenerated pure at R8, 2026-07-31 — DR-7) ---
# Generated by `python3 scripts/loop-grammar-oracle.py --emit-vocab` (DR-7,
# round-3 R8) — ONE vocabulary source: helper and oracle validate from the
# same enums. Do NOT hand-edit; regenerate + re-splice on any oracle
# vocabulary change (the oracle fixture suite asserts this block byte-equal
# to --emit-vocab output).
ENUMS = {
    "BACKENDS": {"claude-p", "codex", "cursor-subagent", "live-session"},
    "CI_VERDICTS": {"failed", "no-checks", "passed", "pending", "unreadable"},
    "DELIVERY_ENUM": {"bg", "fg"},
    "ESCAPE_RESULTS": {"clean", "dirty"},
    "GH_OVERRIDE_VALUES": {"override"},
    "HANDOFF_REASONS": {"composer-run", "must-pause", "phase-complete"},
    "HOLD_CHOICES": {"clear", "hold"},
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
    "NOTIFY_IMMEDIATE_CLASSES": {"cap-accept", "cap-raise", "config-conflict", "must-pause"},
    "NOTIFY_MODES": {"immediate", "queued"},
    "NOTIFY_STATES": {"batch-flushed", "failed", "queued", "retried", "sent", "skipped"},
    "OWNERSHIP_SUBTYPES": {
        "auto-disposition",
        "away-end",
        "away-grant",
        "ci-verdict",
        "commit",
        "config-change",
        "config-revoke",
        "config-snapshot",
        "escape-check",
        "exit-census",
        "gate-disposition",
        "hold",
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
        "group-ff",
        "group-merge",
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
    "away-end": ("role", "iso", "plan", "grant", "reason"),
    "away-grant": ("role", "iso", "plan", "grant", "scope", "departure"),
    "ci-verdict": ("role", "iso", "tip", "verdict"),
    "config-change": ("key", "from", "to"),
    "config-revoke": ("role", "key", "epoch"),
    "config-snapshot": ("role", "iso", "plan", "epoch", "key", "value"),
    "escape-check": ("role", "result", "before", "after", "roots"),
    "exit-census": ("role", "leg", "children"),
    "gate-disposition": ("key", "choice"),
    "hold": ("role", "key", "choice", "iso", "detail"),
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
RESIDUE_VALUES = {"deferred"}
EDIT_SURFACE_STATES = {"changed", "unchanged"}
REC_SOURCES = {"composer", "executor"}
AUTHORITY_KEYS = {"gates", "high-auto"}
GATES_MODES = {"executor", "fix-biased", "strict"}
AWAY_SCOPE_TOKENS = {"merge", "production", "smoke", "staging"}
AWAY_END_REASONS = {"autonomy-off", "back", "release-done", "run-stop"}
SMOKE_BY_VALUES = {"agent", "operator"}
AWAY_ACT_CLASSES = {
    "deploy-production",
    "deploy-staging",
    "merge",
    "pr-fix",
    "rollback",
    "snapshot",
}
UNGATED_VALUES = {"merge"}
AUTHORITY_VALUE_DOMAINS = {
    "gates": ("executor", "fix-biased", "strict"),
    "high-auto": ("on", "off"),
}
AWAY_SCOPE_ORDER = ("smoke", "merge", "staging", "production")
AWAY_SCOPE_REQUIRES = {
    "production": "staging",
    "staging": "merge",
}
AWAY_PAIR_SUBTYPES = ("auto-disposition", "gate-disposition", "smoke-pass")
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
    "bad-edit-surface",
    "edit-surface-root-absent",
    "edit-surface-mismatch",
    "bad-attributed",
    "partial-pass-keys",
    "bad-pass",
    "bad-peer-round",
    "bad-cap",
    "peer-round-over-cap",
    "pass-keys-on-non-peer",
    "peer-round-on-transition",
    "pass-keys-on-finding-route",
    "bad-residue",
    "bad-rec",
    "missing-grant",
    "missing-scope",
    "missing-departure",
    "missing-reason",
    "bad-grant",
    "bad-scope",
    "bad-away-reason",
    "bad-away",
    "bad-away-check",
    "partial-away-pair",
    "away-pair-misplaced",
    "bad-smoke-by",
    "missing-tip",
    "bad-tip",
    "bad-gh",
    "bad-ungated",
    "bad-hold-choice",
    "bad-hold-class",
    "missing-hold-id",
    "bad-hold-id",
    "hold-id-on-clear",
    "missing-clears",
    "bad-clears",
    "clears-on-hold",
    "bad-hold-path",
    "missing-group",
    "missing-ff",
    "bad-ff",
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
    "pass-sequence",
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
    "away-pair-misplaced",
    "backwards-logged-ts",
    "bad-attributed",
    "bad-authority-check",
    "bad-authority-epoch",
    "bad-away",
    "bad-away-check",
    "bad-away-reason",
    "bad-backend",
    "bad-cap",
    "bad-cap-accept",
    "bad-cap-raise",
    "bad-cell",
    "bad-child",
    "bad-children-count",
    "bad-class",
    "bad-class-mode",
    "bad-clears",
    "bad-close-mode",
    "bad-config-key",
    "bad-config-value",
    "bad-delivery",
    "bad-edit-surface",
    "bad-ff",
    "bad-gap-min",
    "bad-gh",
    "bad-grant",
    "bad-handoff-reason",
    "bad-hold-choice",
    "bad-hold-class",
    "bad-hold-id",
    "bad-hold-path",
    "bad-label-check",
    "bad-labels",
    "bad-layer1",
    "bad-layer2",
    "bad-logged-ts",
    "bad-mode",
    "bad-mode-state",
    "bad-monitor-event",
    "bad-ownership-subtype",
    "bad-pass",
    "bad-peer-round",
    "bad-rec",
    "bad-refused",
    "bad-residue",
    "bad-result",
    "bad-revoke-epoch",
    "bad-role",
    "bad-scope",
    "bad-severity",
    "bad-smoke-by",
    "bad-suppressed",
    "bad-tip",
    "bad-transferred",
    "bad-ungated",
    "bad-verdict",
    "bad-verified",
    "batch-key-mismatch",
    "cancelled-without-reason",
    "clears-on-hold",
    "commit-seat-violation",
    "config-hash-mismatch",
    "delivery-on-none",
    "dirty-result-mismatch",
    "duplicate-key",
    "duplicate-pending-id",
    "edit-surface-mismatch",
    "edit-surface-root-absent",
    "empty-after",
    "empty-alive",
    "empty-before",
    "empty-cell",
    "empty-children",
    "empty-choice",
    "empty-departure",
    "empty-detail",
    "empty-epoch",
    "empty-from",
    "empty-grant",
    "empty-iso",
    "empty-key",
    "empty-last",
    "empty-leg",
    "empty-log",
    "empty-mode",
    "empty-plan",
    "empty-reason",
    "empty-result",
    "empty-role",
    "empty-roots",
    "empty-run",
    "empty-scope",
    "empty-session",
    "empty-task",
    "empty-tip",
    "empty-to",
    "empty-transferred",
    "empty-value",
    "empty-verdict",
    "future-ts",
    "hold-id-on-clear",
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
    "missing-clears",
    "missing-config-hash",
    "missing-departure",
    "missing-detail",
    "missing-epoch",
    "missing-event",
    "missing-ff",
    "missing-from",
    "missing-gap-min",
    "missing-grant",
    "missing-group",
    "missing-hash",
    "missing-hold-id",
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
    "missing-reason",
    "missing-result",
    "missing-role",
    "missing-roots",
    "missing-round",
    "missing-run",
    "missing-scope",
    "missing-seat",
    "missing-session",
    "missing-source",
    "missing-sticky-hash",
    "missing-task",
    "missing-tip",
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
    "partial-away-pair",
    "partial-pass-keys",
    "pass-keys-on-finding-route",
    "pass-keys-on-non-peer",
    "peer-round-on-transition",
    "peer-round-over-cap",
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
    # v34.1 D8: the in-session review round's record (`/review-loop`'s shape,
    # the oracle's T6b fixture key order). Open to any seat; NOT a
    # COMPOSER_WRITE_PREFIXES member — a round line never moves the idle clock.
    "ROLE:round": {"prefix": "ROLE:", "verb": "round",
                   "required": ("role", "backend", "model", "round"),
                   "enums": {"role": "ROLE_ENUM", "backend": "BACKENDS"}},
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
# v34.0 (D4): the away grant's two records join — composer-owned, and written
# only by the `away` subcommand (`emit` refuses both outright).
# v35.1 (Decisions 4–5): `ci-verdict` (written only by `away ci-verdict`) and
# `hold` (the operator's durable hold, a composer-only emit) join.
COMPOSER_ONLY_SUBTYPES = frozenset(
    {"gate-disposition", "auto-disposition", "must-pause", "commit",
     "smoke-pass", "phases-extended", "config-change", "profile-switch",
     "label-snapshot", "sticky-ack", "config-snapshot", "config-revoke",
     "away-grant", "away-end", "ci-verdict", "hold"})
# v34.0 (D4): the subtypes `emit` refuses outright because a dedicated
# subcommand COMPUTES them (escape-check / run-close are refused by their own
# branches in cmd_emit; the away pair is written by `away grant|end`).
AWAY_RECORD_SUBTYPES = ("away-grant", "away-end")
# v35.1 (Decision 4): the verdict record is READ and JUDGED by `away
# ci-verdict` — `emit` refuses it on the away-grant model.
TOOL_ONLY_SUBTYPES = ("ci-verdict",)
# Reserved keys the CALLER may never supply on emit (tool-owned or refused).
RESERVED_KEYS = {"ts", "logged_ts", "run"}


class _Refusal(Exception):
    """R14 class fix: a refusal captured as a REASON instead of an exit — raised
    by refuse() only while reason_of() has the capture flag set, so the
    writer's validators can be reused by the READERS without duplicating
    their rules (the single-validation-owner constraint)."""


_CAPTURE_REFUSALS = [False]


def refuse(msg, expected=None):
    if _CAPTURE_REFUSALS[0]:
        raise _Refusal(msg)
    sys.stderr.write("REFUSE: %s\n" % msg)
    if expected:
        sys.stderr.write("EXPECTED: %s\n" % expected)
    sys.exit(2)


def reason_of(fn, *args, **kwargs):
    """Run a refuse()-mode validator in REASON mode: returns None when it
    passes, else the refusal message. The writer path (capture off) is
    byte-equivalent — refuse() still exits 2 there."""
    prev = _CAPTURE_REFUSALS[0]
    _CAPTURE_REFUSALS[0] = True
    try:
        fn(*args, **kwargs)
        return None
    except _Refusal as e:
        return str(e)
    finally:
        _CAPTURE_REFUSALS[0] = prev


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


def check_field_safety(key, value):
    """R15 class fix — the ONE owner of the generic per-FIELD rules every
    record field obeys (the writer applies it to each caller token; the
    readers apply it to each field of a prior record through validate_record):
    the closed key charset, value safety (control / Unicode-whitespace /
    quote / path-delimiter), and the empty-value floor (labels="" is the one
    legal empty)."""
    check_key_safety(key)
    check_value_safety(key, value, is_path=(key in ("roots", "latest", "log", "repo")))
    if value == "" and key != "labels":
        refuse("empty value for %s= — blank identity/evidence fails the empty-<key> floor (labels=\"\" is the one legal empty)" % key)
    # R16 PR-MED-001: the oracle's centralized blank-IDENTITY floor (R43
    # PR-HIGH-026 — run/leg/epoch/session are audit identities; present-but-
    # blank fails `empty-<key>` whether the shape requires the key or not) is
    # the writer's rule too: a whitespace-only optional identity carries
    # nothing and is refused rather than emitted (absence stays legal). Non-
    # identity prose keeps its own value; the required-cell floors are separate.
    if key in AUDIT_IDENTITY_KEYS and not value.strip():
        refuse("%s= is present-but-blank — an audit identity carries a nonblank value or is absent (empty-%s)" % (key, key))


# the oracle's blank-identity floor keys (R43 PR-HIGH-026): present ⇒ nonblank
AUDIT_IDENTITY_KEYS = frozenset({"run", "leg", "epoch", "session"})

COUNT_MAX_DIGITS = 9


def parse_count(s, max_digits=COUNT_MAX_DIGITS):
    """R16 PR-MED-002 — the ONE total numeric-admission primitive: an ASCII
    decimal digit string of 1..max_digits digits → its int, else None. Never
    raises. `str.isdigit()` alone admits what `int()` rejects (U+00B2 '²' →
    ValueError) and admits non-ASCII numerals `int()` accepts ('١٢' → 12), and
    an unbounded digit string trips Python's int-conversion limit — each was a
    traceback (writer, readers, attest-check, --liveness) or a non-canonical
    numeral in a record. Callers keep their own bounds (`< 1` for positive
    counts). The oracle carries the byte-equal twin (no import either way)."""
    if not (0 < len(s) <= max_digits) or not s.isascii() or not s.isdigit():
        return None
    return int(s)


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
    (emit), repeatable --root, and verbatim key=value tokens. v46.4 (D2): a
    `--help` / `-h` token prints the usage and exits 0 before anything else
    is judged (the pre-pass below)."""
    flags = {}
    roots = []
    kvs = []  # (key, value) in argv order
    sub = None
    etype = None
    dry_run = False
    # v33.0 (Phase 1): --edit-surface / --liveness (D4, escape-check + the
    # must-pause re-fire dedupe), --read-log (D3, the read-only prior-record
    # source for a keyed ROLE:start), --policy-log / --key (D12, attest-check).
    # Each is registered ONCE here; the per-subcommand SUB_GRAMMAR (applied in
    # main()) decides where it is accepted (an irrelevant flag still REFUSES there).
    # v33.2 (/close-run T1.1): --merge-commit (D10/D11, run-close ONLY — and
    # only with `--outcome merged` or, v40.0 Phase 1, `--outcome group-merged`;
    # cmd_run_close refuses it on every other outcome). No new subcommand at
    # v33.2: the flag is an ENTRY PATH into the existing verified-merge cell
    # (v40.0: and into the group close's own two cells). v34.0 (D4) adds the eighth
    # subcommand, `away`, with --out (report only); --log-root is reused.
    # v40.0 Phase 0 (D8): --file / --heading / --from / --to — the read-only
    # `quoted-block` subcommand's four flags (--base is reused); accepted by
    # that subcommand only (SUB_GRAMMAR), refused everywhere else. v42.0 (D1):
    # --baseline — quoted-block's optional accepted version (--log-root reused).
    # v44.0 (plan-away-autonomous-rails T0.2 / D4): --grant / --away-check — the
    # group close's re-baseline trio (both or none; outcome-scoped to
    # `group-merged` inside cmd_run_close, the --merge-commit precedent).
    value_flags = {"--run", "--role", "--log", "--log-root", "--epoch", "--event-ts",
                   "--round", "--id", "--repo", "--capture", "--leg",
                   "--iso", "--base", "--outcome", "--plan", "--attest", "--merge-commit",
                   "--edit-surface", "--liveness", "--read-log", "--policy-log", "--key",
                   "--out", "--file", "--heading", "--from", "--to", "--baseline",
                   "--grant", "--away-check",
                   # v47.0 (T1.4 / D7, D9): the read-only `records-delta`
                   # subcommand's seven flags — accepted by it alone
                   "--worktree", "--base-ref", "--tip", "--range", "--alphabet", "--also", "--departure"}
    allow_paths = []  # v33.0 D4: --allow-path <root>:<repo-relative>, repeatable (list, like --root)
    # v46.4 (D2): `--help` / `-h` at ANY token position prints the usage and
    # exits 0 — read here, before every refusal this parse or main() raises for
    # another token (an unknown flag, a duplicate, a missing --run / --role), so
    # a call typed from memory still gets the grammar. A token a flag consumes
    # as its VALUE is never a help request (`--leg -h` names a leg) and a
    # key=value token never is, so no record-writing call becomes a help print
    # through a value. The subcommand whose text prints is the first bare token
    # before the flag (none: the overall usage).
    _sub = None
    _i = 0
    while _i < len(argv):
        _tok = argv[_i]
        if _tok in HELP_FLAGS:
            sys.stdout.write(help_text(_sub))
            sys.exit(0)
        if _tok in value_flags or _tok in ("--root", "--allow-path"):
            _i += 1
        elif _sub is None and not _tok.startswith("--"):
            _sub = _tok
        _i += 1
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--dry-run":
            dry_run = True
        elif tok == "--allow-repeat-hash":
            # v34.1 D10: value-less; type-scoped inside cmd_emit (OWNERSHIP:commit + --log only).
            if tok in flags:
                refuse("duplicate flag %s" % tok)
            flags[tok] = True
        elif tok == "--root":
            if i + 1 >= len(argv):
                refuse("--root needs a value", "--root name=/abs/path")
            roots.append(argv[i + 1])
            i += 1
        elif tok == "--allow-path":
            if i + 1 >= len(argv):
                refuse("--allow-path needs a value", "--allow-path <root-name>:<repo-relative path>[;<root>:<path>...]")
            # the wrapper passes LOOP_ALLOW_PATH as ONE `;`-joined value; a
            # composer may repeat the flag — both spellings land in one list.
            allow_paths.extend(p for p in argv[i + 1].split(";") if p != "")
            i += 1
        elif tok in value_flags:
            if i + 1 >= len(argv):
                refuse("%s needs a value" % tok)
            if tok in flags:
                refuse("duplicate flag %s" % tok)
            flags[tok] = argv[i + 1]
            i += 1
        elif tok.startswith("--"):
            # v46.4 (D2): the hint is generated from SUB_GRAMMAR (usage_hint)
            refuse("unknown flag %s" % tok, usage_hint())
        elif sub is None:
            sub = tok
        elif sub in ("emit", "away") and etype is None and "=" not in tok:
            # the TYPE rides `emit <TYPE>`; v34.0: the VERB rides `away <verb>`
            etype = tok
        elif "=" in tok:
            k, v = tok.split("=", 1)
            if not k:
                refuse("empty key in token %r" % tok)
            kvs.append((k, v))
        else:
            refuse("stray bare token %r" % tok, "values ride key=value tokens; the TYPE rides `emit <TYPE>`")
        i += 1
    # --allow-path rides `flags` as a LIST under its own key (the one
    # list-valued flag; SUB_GRAMMAR keys on the flag NAME, so the per-subcommand
    # admission check covers it like any other flag).
    if allow_paths:
        flags["--allow-path"] = allow_paths
    return sub, etype, flags, roots, kvs, dry_run


SINK_CONTROL_SUFFIXES = ("-isolation", "-active", "-seat", "-seat.gate", "-notakeover", "-composer", "-takeovers", ".live", ".exit")


def _sink_is_control(name):
    """Is `name` — a file's own name, no folder — one of a run's control
    files, AS A FILE SYSTEM MAY READ IT (round 71 PR-LOW-031)? The suffix is
    tested with case folded and a trailing dot or space dropped: a file
    system that folds case (macOS by default, a Windows host) writes
    `<iso>-SEAT` into `<iso>-seat`, and a Windows host drops a trailing dot or
    space from a name. No log of the loop is named so, so the wider test
    refuses nothing a run writes."""
    return name.rstrip(". ").lower().endswith(SINK_CONTROL_SUFFIXES)


def open_sink(flags):
    """stdout default; --log appends directly (one write per invocation)."""
    path = flags.get("--log")
    if path is None:
        return None
    if not os.path.isabs(path):
        refuse("--log must be an absolute path")
    # round 69 SEC-004: a record is appended to a LOG — never to one of a run's control files. `--log` rides every
    # role's granted helper shape and takes any absolute path, so without this a role could create or grow, in the
    # base's loops directory, the files the watcher and the close read as STATE: a marker or a journal (a run that
    # was never started, notified about at every new name), the seat's files, the no-takeover mark, the identity
    # record, the ledger, a leg's `.live` / `.exit`. No parser reads a record line as one of their keys; what the
    # refusal ends is the denial and the noise.
    if _sink_is_control(os.path.basename(path)):
        refuse("--log %s names one of a run's control files (a marker, a journal, a seat or leg file), never a log — a record is appended to a log only"
               % os.path.basename(path)[:120])
    # round 71 PR-LOW-031: the name that is TESTED is the name the append LANDS on. The append follows a link at the
    # sink's own name, so a `probe.log` that is a link to `<iso>-takeovers` passed the test above and grew the ledger.
    # The sink is resolved through every link, the leaf included (as seat_where resolves it — round 49 PR-MED-031), and
    # its own name is tested the same way. A link to an ordinary log, and a linked FOLDER that holds one, stay allowed.
    # What a name test cannot see, stated: a hard link, and a link swapped between this test and the append — both are
    # edits of the loops folder by another hand.
    # Resolved by canon_path, the helper's one resolver; a spelling it refuses (a Windows host: a UNC or a `/`-rooted
    # path) is not this test's to refuse — the name as typed, tested above, stands for it there.
    landed = os.path.basename(path)
    try:
        if reason_of(canon_path, path) is None:
            landed = os.path.basename(canon_path(path))
    except (OSError, ValueError):
        pass
    if _sink_is_control(landed):
        refuse("--log %s is a link to one of a run's control files (%s), never a log — a record is appended to a log only, and the append follows the link"
               % (os.path.basename(path)[:120], landed[:120]))
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
        with open(sink, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
    except OSError as e:
        envfail("cannot append to --log %s: %s" % (sink, e))


NOTICE_TITLE = "execute-loop: operator needed"
# v33.0 D5 — notification TIERS (no new class, no new state; urgency is
# orthogonal to mode=). The operator-needed tier: `class=must-pause` (every
# reason — live-smoke, usage/auth, limit-death, [decision], escape, a SURFACED
# cap) and `class=config-conflict` → critical, persistent, NOTICE_TITLE. Every
# other class (auto-disposition, docs-only, invalid, the AUTOMATIC cap-raise /
# cap-accept transitions, HIGH auto-routes) is act-and-inform → normal, 20 s
# expiry, the per-run "done" title. An UNKNOWN/absent class (a legacy retry
# record without class=) fails toward the LOUDER tier.
NOTICE_CRITICAL_CLASSES = frozenset({"must-pause", "config-conflict"})
NOTICE_INFO_EXPIRY_MS = 20000
NOTICE_CRITICAL_EXPIRY_MS = 0  # persistent by design (GNOME ignores -t on critical)


def notice_tier(cls):
    """(urgency, expiry_ms) for a NOTIFY class — the D5 tier map."""
    if cls is None or cls in NOTICE_CRITICAL_CLASSES:
        return "critical", NOTICE_CRITICAL_EXPIRY_MS
    return "normal", NOTICE_INFO_EXPIRY_MS


def notice_title(runkey, urgency):
    return NOTICE_TITLE if urgency == "critical" else "execute-loop: %s — done" % runkey


def notice_spec(platform, runkey, summary, urgency="critical", expiry_ms=NOTICE_CRITICAL_EXPIRY_MS, title=None):
    """Build (argv, env) for the desktop notice with the notification values
    carried ONLY as DATA — argv data elements on Linux/macOS, environment
    variables on Windows — NEVER concatenated into an interpreter program
    (PR-HIGH-001/round-7 lineage: PR-HIGH-003). The macOS `osascript` body
    reads its text from `argv`, and the Windows PowerShell body reads it from
    `$env:`, so a value containing a quote, `;`, backtick, or `$(...)` can
    never alter the executed program. The program text is byte-stable across
    values by construction.

    v33.0 D5: `urgency`/`expiry_ms`/`title` carry the tier — Linux gets
    `-u <urgency>` (+ `-t <ms>` on the informational tier; the critical tier
    is persistent by design, so no `-t`); macOS/Windows have no urgency or
    expiry, so the tier degrades to the TITLE split."""
    body = "%s: %s" % (runkey, summary)
    title = title if title is not None else notice_title(runkey, urgency)
    if platform == "darwin":
        return (["osascript",
                 "-e", "on run argv",
                 "-e", "display notification (item 1 of argv) with title (item 2 of argv)",
                 "-e", "end run",
                 body, title], {})
    if platform == "win32":
        # v45.0 (T1.3): the BurntToast module is checked FIRST — absent, the
        # program exits NOTICE_WIN32_MODULE_ABSENT before any cmdlet runs
        # (fire_notice prints the ONE stderr WARN and reports the notice
        # failed; nothing is sent). The program text stays CONSTANT — the
        # title and body ride the environment, never the program (PR-HIGH-003).
        prog = ("if (-not (Get-Module -ListAvailable -Name BurntToast)) { exit %d }; "
                "New-BurntToastNotification -Text "
                "$env:LOOP_JOURNAL_NOTICE_TITLE,$env:LOOP_JOURNAL_NOTICE_BODY" % NOTICE_WIN32_MODULE_ABSENT)
        return (["powershell", "-NoProfile", "-NonInteractive", "-Command", prog],
                {"LOOP_JOURNAL_NOTICE_TITLE": title,
                 "LOOP_JOURNAL_NOTICE_BODY": body})
    # linux and any other host: notify-send takes title/body as data args
    argv = ["notify-send", "-u", urgency]
    if urgency != "critical":
        argv += ["-t", str(expiry_ms)]
    return (argv + [title, body], {})


def notify_policy():
    """v33.0 D5: LOOP_NOTIFY=action-only|all (exported by the composer at
    preflight from the `notify=` key). Absent → `all`; an unrecognized value
    fails CLOSED to `all` (the louder policy) with ONE stderr warning — a
    typo never silences a notice."""
    raw = os.environ.get("LOOP_NOTIFY")
    if raw is None or raw == "all":
        return "all"
    if raw == "action-only":
        return "action-only"
    sys.stderr.write("WARN: LOOP_NOTIFY=%r is not action-only|all — treated as `all` (fail-closed to the louder policy)\n" % raw[:40])
    return "all"


def fire_notice(runkey, summary, cls=None, reason=None):
    """One per-OS desktop notice; returns True on confirmed delivery.
    LOOP_JOURNAL_NOTICE_CMD overrides with the TIERED argv as DATA —
    `[override, "-u", <urgency>, "-t", <ms>, <title>, <body>]` (v33.0 D5: the
    selftest hook observes the tier; `-t 0` = the persistent critical tier).
    Built-in backends route through notice_spec so journal values never
    enter interpreter source on any host (PR-HIGH-003). `cls` selects the
    tier (D5); `reason` is carried for the operator-needed body only."""
    urgency, expiry_ms = notice_tier(cls)
    title = notice_title(runkey, urgency)
    if reason and urgency == "critical" and reason not in summary:
        summary = "%s [reason=%s]" % (summary, reason)
    override = os.environ.get("LOOP_JOURNAL_NOTICE_CMD")
    platform = _notice_platform()
    if override:
        cmd, env_extra = [override, "-u", urgency, "-t", str(expiry_ms), title,
                          "%s: %s" % (runkey, summary)], {}
    else:
        cmd, env_extra = notice_spec(platform, runkey, summary, urgency, expiry_ms, title)
    env = None
    if env_extra:
        env = dict(os.environ)
        env.update(env_extra)
    try:
        r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=10, env=env)
    except Exception:
        return False
    if not override and platform == "win32" and r.returncode == NOTICE_WIN32_MODULE_ABSENT:
        # v45.0 (T1.3): the win32 backend's module-absent exit — ONE stderr
        # warning, nothing sent; the NOTIFY state records the failure as today.
        sys.stderr.write("WARN: desktop notice not sent — the BurntToast PowerShell module is absent (Install-Module BurntToast); the NOTIFY record carries the failure\n")
        return False
    return r.returncode == 0


# v45.0 (T1.3): the win32 notice program's module-absent exit code, and the
# platform read behind fire_notice (a function so the selftest can exercise
# the win32 branch on a Linux host without touching sys.platform).
NOTICE_WIN32_MODULE_ABSENT = 3


def _notice_platform():
    return sys.platform


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


def authority_hash(iso, plan, epoch, key, value):
    """The per-key config_hash serialization (v33.0 D1 — byte-identical to the
    v32 form for key=high-auto): sha256("iso=…|plan=…|epoch=…|<key>=<value>")[:12]."""
    return hashlib.sha256(("iso=%s|plan=%s|epoch=%s|%s=%s" % (iso, plan, epoch, key, value))
                          .encode("utf-8")).hexdigest()[:12]


def validate_authority_record(kv, st, check_hash=True):
    """v33.0 D12 — the ONE record-shape owner for the two authority subtypes,
    applied by the WRITER (cmd_emit, before it derives the hash) and by the
    READER (attest-check / read_authority) alike, so the shipped helper never
    imports the unshipped oracle and the two cannot drift. Returns None when
    the record is well-formed, else a short reason (the oracle's class token
    in parentheses). Rules: role=composer; key in AUTHORITY_KEYS; value in the
    key's closed domain (snapshot); nonblank iso/plan/epoch (snapshot);
    revoke epoch a positive integer from 1; and — reading — config_hash= is
    the exact 12-hex recompute over the record's own fields."""
    # R13 PR-HIGH-001: NO composer default here — the WRITER stamps role= via
    # its own setdefault BEFORE calling; the READER must see the record's own
    # role= (a role-less snapshot is the oracle's missing-role, never bound).
    if kv.get("role") != "composer":
        return "is a composer-owned record — role=%s (%s)" % (kv.get("role"), "missing-role" if "role" not in kv else "bad-role")
    key = kv.get("key")
    if key not in AUTHORITY_KEYS:
        return "admits key=%s only (bad-config-key) — got key=%r" % ("|".join(sorted(AUTHORITY_KEYS)), key)
    if st == "config-snapshot":
        if kv.get("value") not in AUTHORITY_VALUE_DOMAINS[key]:
            return "value= for key=%s must be %s (bad-config-value)" % (key, "|".join(AUTHORITY_VALUE_DOMAINS[key]))
        for rk in ("iso", "plan", "epoch"):
            if not kv.get(rk, "").strip():
                return "requires nonblank %s= — the hash binds the full identity (PR-HIGH-015; missing-%s)" % (rk, rk)
        if check_hash:
            ch = kv.get("config_hash")
            if ch is None:
                return "carries no config_hash= (missing-config-hash)"
            if not re.match(r"\A[0-9a-f]{12}\Z", ch):
                return "config_hash= is not 12 lowercase hex (malformed-digest)"
            if ch != authority_hash(kv["iso"], kv["plan"], kv["epoch"], key, kv["value"]):
                return "config_hash= does not recompute from the record's own iso/plan/epoch/key/value (config-hash-mismatch)"
        return None
    # config-revoke
    ep = kv.get("epoch", "")
    if not ep.strip():
        return "requires epoch= (missing-epoch)"
    _epn = parse_count(ep)
    if _epn is None or _epn < 1:
        return "epoch= must be a positive integer from 1 (bad-revoke-epoch) — the snapshot is epoch 0"
    return None


def validate_gate_record_fields(st, kv):
    """R14 class fix — the ONE owner of the gate-record FIELD rules shared by
    the writer (cmd_emit, refuse mode) and the readers (reason mode via
    emittable_record): `rec=` rides must-pause/gate-disposition (and, v34.0,
    an auto-disposition beside the away pair — see below) and is
    `<executor|composer>:<nonblank>` (D6); a gate-disposition on a cap key
    carries the pass=+cap= bundle both-or-neither and never residue=, a
    non-cap gate-disposition none of the pass keys (D3/D2). v34.0 D6: `rec=`
    also rides an auto-disposition, but only beside the away pair (the away
    decision record)."""
    if "rec" in kv:
        if not (st in ("must-pause", "gate-disposition")
                or (st == "auto-disposition" and "away" in kv and "away_check" in kv)):
            refuse("rec= rides OWNERSHIP:must-pause and OWNERSHIP:gate-disposition (the recommendation-first ask — D6), and OWNERSHIP:auto-disposition only beside the away pair away=+away_check= (v34.0 D6), not OWNERSHIP:%s%s"
                   % (st, " without the away pair" if st == "auto-disposition" else ""))
        _rs, _sep, _rd = kv["rec"].partition(":")
        if not _sep or _rs not in REC_SOURCES or not _rd.strip():
            refuse("rec= must be <source>:<disposition> with source in %s and a nonblank disposition (bad-rec; D6) — got %r"
                   % ("|".join(sorted(REC_SOURCES)), kv["rec"][:60]))
    if st == "gate-disposition":
        if kv.get("key") in CAP_TRANSITION_GATE_KEYS:
            if "residue" in kv:
                refuse("residue= rides the cap-accept=close auto-disposition only, never a gate-disposition (D2)")
            check_cap_transition_bundle(kv, "OWNERSHIP:gate-disposition (cap key)")
        elif any(k in kv for k in PASS_KEYS) or "residue" in kv:
            refuse("pass=/peer_round=/cap=/residue= ride a cap gate-disposition (key=cap-raise|peer-cap|peer-cap-accept) only (D3)")


def finding_evidence(kv):
    """The auto-disposition route discriminator (TB.2): severity=, verified=,
    or a finding-ID key (identity-only PR-REG-* included)."""
    key_is_finding = False
    if "key" in kv:
        key_is_finding = bool(FINDING_ID_RE.match(re.split(r"[^A-Za-z0-9-]+", kv["key"])[-1] or ""))
    return "severity" in kv or "verified" in kv or key_is_finding


def validate_cap_route(kv):
    """R14 class fix — the ONE owner of the auto-disposition CAP-ROUTE rules
    (writer + readers): exactly one of cap-raise=+1 / cap-accept=close, closed
    values, ZERO finding evidence on a cap route (mixed-route), the pass=+cap=
    bundle both-or-neither (never peer_round=; residue= on accept-close only),
    and none of the pass keys on a finding route."""
    cap, capacc = kv.get("cap-raise"), kv.get("cap-accept")
    if cap is not None and capacc is not None:
        refuse("cap-raise= and cap-accept= are mutually exclusive — one record is ONE cap transition (mixed-route)")
    if cap is not None or capacc is not None:
        check_cap_transition_bundle(kv, "OWNERSHIP:auto-disposition (cap transition)")
    elif any(k in kv for k in PASS_KEYS) or "residue" in kv:
        refuse("pass=/peer_round=/cap=/residue= ride cap-transition records (cap-raise=+1 / cap-accept=close) — a finding route carries none of them (D3)")
    evidence = finding_evidence(kv)
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


# the shapes whose ts= IS the write time — the writer refuses --event-ts on
# them, so a logged_ts= can never appear on one (the oracle's
# logged-ts-on-checkpoint class).
CONTEMPORANEOUS_SUBTYPES = frozenset({"config-snapshot", "config-revoke", "sticky-ack", "run-close",
                                      "away-grant", "away-end", "ci-verdict", "hold"})


def away_scope_ok(value):
    """v34.0 D4 — the byte-equal twin of the oracle's away_scope_ok (no import
    either way): scope= is a comma-joined subset of AWAY_SCOPE_ORDER (the
    generated block), in that order, unique, nonempty, with the generated
    AWAY_SCOPE_REQUIRES implications production ⇒ staging ⇒ merge."""
    toks = value.split(",")
    if not toks or any(t not in AWAY_SCOPE_TOKENS for t in toks):
        return False
    if len(set(toks)) != len(toks):
        return False
    if toks != [t for t in AWAY_SCOPE_ORDER if t in toks]:
        return False
    return all(AWAY_SCOPE_REQUIRES[t] in toks for t in toks if t in AWAY_SCOPE_REQUIRES)


def away_grant_hash(iso, plan, grant, scope, departure):
    """v34.0 D4 — the away-grant config_hash: sha256("iso=…|plan=…|grant=…|
    away=<scope>|departure=…")[:12] (the oracle's byte-equal twin)."""
    return hashlib.sha256(("iso=%s|plan=%s|grant=%s|away=%s|departure=%s"
                           % (iso, plan, grant, scope, departure)).encode("utf-8")).hexdigest()[:12]


HEX12_RE = re.compile(r"\A[0-9a-f]{12}\Z")
# v35.1 (Decisions 3–5): the oracle's byte-equal twins (no import either way)
# — the checked commit's full sha, and the hold path alphabet that keeps the
# printed `held=` list unambiguous.
CI_TIP_RE = re.compile(r"\A[0-9a-f]{40}\Z")
HOLD_PATH_RE = re.compile(r"\A[A-Za-z0-9._/-]+\Z")
# v44.0 (plan-away-autonomous-rails T0.1 / D1, D2, D16): the pre-approval key
# class on OWNERSHIP:auto-disposition — a FREE key class (the v42.0 set-refresh
# precedent: no enum, no subtype, no schema bump). PREAPPROVAL_CLASSES is every
# class; the DEPARTURE classes — PREAPPROVAL_GRANT_CLASSES, an explicit tuple,
# never a slice of the other — may ride the away-grant record's trailing
# `allows=` kv (D16); `operator-task` is per task and exists only as a
# post-grant record carrying path=<task id>. The task-id alphabet is
# HOLD_PATH_RE without `/` — a token the printed `allowed="…"` suffix can carry
# unambiguously beside its space and `;` delimiters; an unrepresentable id is
# REFUSED, never normalised.
# v47.0 (plan-loop-autonomy-group-2 T1.1 / D1): `operator-merge` joins as a
# departure class, before `operator-task` (the fold prints in this order). It
# takes no `:<n>` and no `path=`, and stays a free key class like the others.
# What it admits is D2's list; the helper's part is the listing check at every
# away merge start (away_merge_listing_refusal, D4).
PREAPPROVAL_CLASSES = ("records-merge", "pr-fix-cycles", "ci-advisory-fix", "foreign-merge", "operator-merge",
                       "operator-task")
PREAPPROVAL_GRANT_CLASSES = ("records-merge", "pr-fix-cycles", "ci-advisory-fix", "foreign-merge", "operator-merge")
PREAPPROVAL_CHOICES = ("allowed", "cleared")
PREAPPROVAL_DEFAULT_LIMIT = 3     # a bare pr-fix-cycles (grant entry or record) — the effective limit
PREAPPROVAL_PATH_RE = re.compile(r"\A[A-Za-z0-9._-]+\Z")


def validate_ci_verdict_record(kv):
    """v35.1 Decision 4 — the ONE record-shape owner for `ci-verdict` (the
    writer, `away ci-verdict`, and every reader through validate_record):
    role=composer; tip= a 40-hex sha; verdict= from the generated CI_VERDICTS;
    gh= admits only `override`. Presence of the required cells is
    ownership_required's job. Returns None when well-formed, else a reason
    (the oracle's class token in parentheses)."""
    if kv.get("role") != "composer":
        return "is a composer-owned record — role=%s (%s)" % (kv.get("role"), "missing-role" if "role" not in kv else "bad-role")
    if "tip" in kv and kv["tip"].strip() and not CI_TIP_RE.match(kv["tip"]):
        return "tip= must be the checked commit's full 40-hex sha (bad-tip)"
    if "verdict" in kv and kv["verdict"].strip() and kv["verdict"] not in ENUMS["CI_VERDICTS"]:
        return "verdict= must be one of %s (bad-verdict)" % "|".join(sorted(ENUMS["CI_VERDICTS"]))
    if "gh" in kv and kv["gh"] not in ENUMS["GH_OVERRIDE_VALUES"]:
        return "gh= admits only %s — the LOOP_JOURNAL_GH stamp (bad-gh)" % "|".join(sorted(ENUMS["GH_OVERRIDE_VALUES"]))
    # detail= presence is BESPOKE (round 9 MED-003): it is serialised LAST,
    # after the optional gh= stamp, so no prefix of a stamped record is a
    # writer-valid unstamped one (a tear that drops the stamp also cuts the
    # quoted detail). The oracle carries the same bespoke check.
    if "detail" not in kv:
        return "requires detail= (missing-detail)"
    if not kv["detail"].strip():
        return "detail= is present-but-blank (empty-detail)"
    return None


def validate_hold_record(kv):
    """v35.1 Decision 5 — the ONE record-shape owner for `hold` (the writer and
    the hold fold alike): role=composer; key= names an AWAY_ACT_CLASSES class;
    choice= hold|clear; a hold carries the writer-generated 12-hex hold_id=
    and never clears=; a clear carries clears= (the hold_id it closes) and
    never hold_id=; path= keeps to HOLD_PATH_RE. Returns None or a reason."""
    if kv.get("role") != "composer":
        return "is a composer-owned record — role=%s (%s)" % (kv.get("role"), "missing-role" if "role" not in kv else "bad-role")
    key = kv.get("key", "")
    if key.strip() and _away_act_class(key) not in AWAY_ACT_CLASSES:
        return ("key= must be <runkey>-<class> with the class one of %s — a hold names a release act (bad-hold-class)"
                % "|".join(sorted(AWAY_ACT_CLASSES)))
    choice = kv.get("choice")
    if choice is not None and choice.strip() and choice not in ENUMS["HOLD_CHOICES"]:
        return "choice= must be one of %s (bad-hold-choice)" % "|".join(sorted(ENUMS["HOLD_CHOICES"]))
    if "hold_id" in kv and not HEX12_RE.match(kv["hold_id"]):
        return "hold_id= is not 12 lowercase hex (bad-hold-id)"
    if "clears" in kv and not HEX12_RE.match(kv["clears"]):
        return "clears= is not 12 lowercase hex — copy the hold's hold_id from `away check`'s held= list (bad-clears)"
    if choice == "hold":
        if "hold_id" not in kv:
            return "a hold carries the writer-generated hold_id= (missing-hold-id)"
        if "clears" in kv:
            return "clears= rides a clear only (clears-on-hold)"
    elif choice == "clear":
        if "clears" not in kv:
            return "a clear names the hold it closes in clears=<that hold's hold_id> (missing-clears)"
        if "hold_id" in kv:
            return "hold_id= rides a hold only (hold-id-on-clear)"
    if "path" in kv and not HOLD_PATH_RE.match(kv["path"]):
        return ("path= must match [A-Za-z0-9._/-]+ (bad-hold-path) — a departure path outside that alphabet is held "
                "class-wide: write the hold WITHOUT path= and name the path in detail=")
    return None


def parse_grant_allows(value):
    """v44.0 D16 — the away-grant record's `allows=<class>[:<n>][,<class>[:<n>]…]`
    kv (the departure-time pre-approvals, outside config_hash): the departure
    classes only (PREAPPROVAL_GRANT_CLASSES), unique, any order; `:<n>` a positive integer
    admitted on pr-fix-cycles only (a bare pr-fix-cycles has the effective
    limit PREAPPROVAL_DEFAULT_LIMIT); operator-task is REFUSED here (per task
    — it exists only as a post-grant record with path=). Shared by the writer
    (`away grant`), validate_away_record (so a grant carrying a malformed
    allows= is never writer-valid), and the fold. Returns ([(class, limit or
    None)], None) or (None, reason)."""
    out, seen = [], set()
    for tok in value.split(","):
        cls, sep, lim = tok.partition(":")
        if cls == "operator-task":
            return None, ("operator-task is per task — it rides a pre-approval record with path=<task id> after the grant, "
                          "never the grant's allows= (bad-allows)")
        if cls not in PREAPPROVAL_GRANT_CLASSES:
            return None, "allows= entry %r is not one of %s (bad-allows)" % (tok[:40], ",".join(PREAPPROVAL_GRANT_CLASSES))
        if cls in seen:
            return None, "allows= names %s twice (bad-allows)" % cls
        seen.add(cls)
        limit = None
        if sep:
            if cls != "pr-fix-cycles":
                return None, "allows= admits :<n> on pr-fix-cycles only — got %r (bad-allows)" % tok[:40]
            limit = parse_count(lim)
            if limit is None or limit < 1:
                return None, "allows= pr-fix-cycles:<n> needs a positive integer — got %r (bad-allows)" % tok[:40]
        out.append((cls, limit))
    return out, None


def validate_preapproval_record(kv):
    """v44.0 (plan-away-autonomous-rails T0.1 / D1) — the ONE record-shape owner
    for the `pre-approval` key class on OWNERSHIP:auto-disposition (the writer
    through validate_record and the fold through emittable_record alike — the
    validate_hold_record precedent): choice=allowed|cleared; allow= one of
    PREAPPROVAL_CLASSES; instr= the 12-hex instruction identity, minted
    by the caller ONCE per operator instruction and carried unchanged on a
    retry (the fold's replay / conflict test — D2); path= REQUIRED on
    operator-task (the task-id alphabet PREAPPROVAL_PATH_RE — unrepresentable
    ids refused, never normalised) and refused on the other classes; limit= a
    positive integer on pr-fix-cycles only; rec=composer:allow on an allowed,
    composer:clear on a cleared; the away pair present (the record binds to
    the grant it is honoured under — through validate_record the pair-less
    shape is refused one owner earlier, by validate_gate_record_fields' rule
    that rec= rides an auto-disposition only beside the pair, so this last
    rule is reached by a direct caller alone). Returns None or a reason."""
    choice = kv.get("choice")
    if choice not in PREAPPROVAL_CHOICES:
        return "choice= must be %s on a pre-approval record (bad-preapproval-choice)" % "|".join(PREAPPROVAL_CHOICES)
    allow = kv.get("allow")
    if allow is None:
        return "a pre-approval record names its class in allow=<%s> (missing-allow)" % "|".join(PREAPPROVAL_CLASSES)
    if allow not in PREAPPROVAL_CLASSES:
        return "allow= must be one of %s (bad-allow)" % "|".join(PREAPPROVAL_CLASSES)
    instr = kv.get("instr")
    if instr is None:
        return ("a pre-approval record carries instr=<12 lowercase hex> — the instruction identity, minted once per "
                "operator instruction and carried unchanged on a retry (missing-instr)")
    if not HEX12_RE.match(instr):
        return "instr= is not 12 lowercase hex (bad-instr)"
    if allow == "operator-task":
        if "path" not in kv:
            return "an operator-task pre-approval names the task in path=<task id> (missing-preapproval-path)"
        if not PREAPPROVAL_PATH_RE.match(kv["path"]):
            return ("path= must be the task's ID token, matching [A-Za-z0-9._-]+ — a space, `;`, `/`, or any other byte is "
                    "unrepresentable in the printed allowed=\"…\" suffix and is refused, never normalised (bad-preapproval-path)")
    elif "path" in kv:
        return "path= rides an operator-task pre-approval only — the other classes are run-wide (path-on-class)"
    if "limit" in kv:
        if allow != "pr-fix-cycles":
            return "limit= rides a pr-fix-cycles pre-approval only (limit-on-class)"
        _ln = parse_count(kv["limit"])
        if _ln is None or _ln < 1:
            return "limit= must be a positive integer (bad-limit)"
    want_rec = "composer:allow" if choice == "allowed" else "composer:clear"
    if kv.get("rec") != want_rec:
        return "rec= must be %s on a pre-approval choice=%s (bad-preapproval-rec)" % (want_rec, choice)
    if "away" not in kv or "away_check" not in kv:
        return ("a pre-approval record carries the away pair away=<n> away_check=<config_hash> — it binds to the grant "
                "it is honoured under (missing-away-pair)")
    return None


def validate_away_record(kv, st):
    """v34.0 D4 — the ONE record-shape owner for the two away subtypes (the
    validate_authority_record pattern: the writer and the `away` state
    function apply the same rules). Returns None when well-formed, else a
    short reason (the oracle's class token in parentheses). Presence of the
    required cells is ownership_required's job; this owns the VALUES."""
    if kv.get("role") != "composer":
        return "is a composer-owned record — role=%s (%s)" % (kv.get("role"), "missing-role" if "role" not in kv else "bad-role")
    if "grant" in kv:
        _gn = parse_count(kv["grant"])
        if _gn is None or _gn < 1:
            return "grant= must be a positive integer from 1 (bad-grant)"
    if st == "away-end":
        if "reason" in kv and kv["reason"] not in AWAY_END_REASONS:
            return "reason= must be one of %s (bad-away-reason)" % "|".join(sorted(AWAY_END_REASONS))
        return None
    if "scope" in kv and not away_scope_ok(kv["scope"]):
        return ("scope= must be comma-joined from %s in that order, unique, at least one, production requiring staging and staging requiring merge (bad-scope)"
                % ",".join(AWAY_SCOPE_ORDER))
    if "departure" in kv and not HEX12_RE.match(kv["departure"]):
        return "departure= is not 12 lowercase hex (malformed-digest)"
    if "config_hash" in kv:
        if not HEX12_RE.match(kv["config_hash"]):
            return "config_hash= is not 12 lowercase hex (malformed-digest)"
        if all(kv.get(k, "").strip() for k in ("iso", "plan", "grant", "scope", "departure")):
            if kv["config_hash"] != away_grant_hash(kv["iso"], kv["plan"], kv["grant"], kv["scope"], kv["departure"]):
                return "config_hash= does not recompute from the record's own iso/plan/grant/scope/departure (config-hash-mismatch)"
    if "allows" in kv:
        # v44.0 D16: the trailing departure-time pre-approvals kv — outside the
        # hash, validated by the one grammar the fold reads with.
        _why = parse_grant_allows(kv["allows"])[1]
        if _why:
            return _why
    return None


def validate_away_keys(st, kv):
    """v34.0 D6 — the away pair and smoke_by= on existing records (writer +
    readers): away=<positive int> away_check=<12 lowercase hex>, both or
    neither, admitted on AWAY_PAIR_SUBTYPES only; smoke_by= from
    SMOKE_BY_VALUES on smoke-pass only (absent reads as operator; with the
    away pair the writer requires the key from v46.4 — that rule is cmd_emit's
    own, D10: this validator, which every reader shares, admits a paired
    smoke without the key exactly as before). The emit does not read the
    policy log — whether a pair matches a grant is the report's check (D5) —
    with ONE exception (v47.0 D4): an away `merge` `choice=start`, which
    cmd_emit checks against the bound grant and its departure file before
    the write (away_merge_listing_refusal). That check is cmd_emit's own
    sequencing rule, never this validator's: no reader re-applies it."""
    if "away" in kv or "away_check" in kv:
        if st not in AWAY_PAIR_SUBTYPES:
            refuse("the away pair away=/away_check= rides OWNERSHIP:%s only, not OWNERSHIP:%s (away-pair-misplaced; D6)"
                   % ("|".join(AWAY_PAIR_SUBTYPES), st))
        if ("away" in kv) != ("away_check" in kv):
            refuse("away= and away_check= travel together — both or neither (partial-away-pair; D6)")
        _an = parse_count(kv["away"])
        if _an is None or _an < 1:
            refuse("away= must be a positive integer — the grant number (bad-away; D6)")
        if not HEX12_RE.match(kv["away_check"]):
            refuse("away_check= must be the grant's config_hash — 12 lowercase hex (bad-away-check; D6)")
    if "smoke_by" in kv:
        if st != "smoke-pass":
            refuse("smoke_by= rides OWNERSHIP:smoke-pass only, not OWNERSHIP:%s (bad-smoke-by; D6)" % st)
        if kv["smoke_by"] not in SMOKE_BY_VALUES:
            refuse("smoke_by= must be one of %s (bad-smoke-by; D6)" % "|".join(sorted(SMOKE_BY_VALUES)))


def check_seat_gate(st, actor):
    """The composer-seat gate (PR-MED-001 round 12 / R16 PR-HIGH-001): every
    composer-owned OWNERSHIP subtype is certified by role=composer only. ONE
    owner — the writer applies it to --role before any derivation, and
    validate_record applies it to the record's own role= (else the writer's
    --role) so a carried non-composer actor is never emittable. The gate is a
    mis-attribution guard, not caller authentication (the grant/process layer
    is the authority boundary — the retained R12 item)."""
    if st in COMPOSER_ONLY_SUBTYPES and actor != "composer":
        refuse("OWNERSHIP:%s is a composer-owned record — it requires --role composer; a %s role can never certify one (dispositions/attestations are never delegated; the seat gate is a mis-attribution guard — caller AUTHORITY is the grant/process boundary, the retained R12 item)" % (st, actor))


def ownership_required(st, kv):
    """R15 class fix — the ONE owner of an OWNERSHIP subtype's required cell
    set (the MATRIX row, plus commit's derived hash=/seat= and sticky-ack's
    derived sticky_hash=, minus exit-census's children= when the capture
    failed). Shared by the writer (ordering + floor) and validate_record."""
    required = ("run",) + V_MATRIX.get(st, ())
    if st == "commit":
        required += ("hash", "seat")
    if st == "sticky-ack":
        required += ("sticky_hash",)
    if st == "away-grant":
        required += ("config_hash",)  # v34.0 D4: tool-derived, like sticky_hash=
    if st == "exit-census" and kv.get("refused") is not None:
        required = tuple(k for k in required if k != "children")
    return required


def validate_auto_disposition(kv):
    """R15 class fix — the ONE owner of the auto-disposition ROUTE rules
    beyond the cap route: the when-present authority-attestation pair
    coherence, the severity=/verified= enums and the orphan-verified rider,
    and the finding-route rules (a finding-ID key requires severity=,
    severity= agrees with the ID's class, a CRIT never auto-disposes, a
    resolved-or-effective HIGH carries the attestation pair)."""
    validate_cap_route(kv)
    cap, capacc = kv.get("cap-raise"), kv.get("cap-accept")
    key_sev = None
    key_is_finding = False
    if "key" in kv:
        m = FINDING_ID_RE.match(re.split(r"[^A-Za-z0-9-]+", kv["key"])[-1] or "")
        # `PR-REG-*` is a valid identity but carries no route severity;
        # verified severity remains the routing authority.
        key_is_finding = bool(m)
        key_sev = (m.group(2) or "").lower() or None if m else None
    # v32 TA.1: authority-attestation coherence when-present on any route —
    # authority_check= is the EXACT 12-hex config_hash echo and travels WITH
    # authority_epoch= (nonnegative revocation count; 0 = no prior revocation).
    if "authority_check" in kv:
        if not re.match(r"\A[0-9a-f]{12}\Z", kv["authority_check"]):
            refuse("authority_check= must be the exact 12-hex config_hash echo (bad-authority-check)")
        if "authority_epoch" not in kv:
            refuse("authority_check= travels with authority_epoch= — the revocation-epoch binding is half the attestation (missing-authority-epoch, PR-HIGH-006)")
    if "authority_epoch" in kv:
        if parse_count(kv["authority_epoch"]) is None:
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
        # PR-HIGH-001 (round 9): a finding-route auto-disposition (a finding-ID
        # key) REQUIRES its own severity= (STICKY section 7) — the resolved
        # severity is the SINGLE owner TIERING consumes. TB.2 (v32): the guard
        # fires on ANY finding-ID key (identity-only PR-REG-* included).
        if key_is_finding and "severity" not in kv:
            refuse("a finding-route auto-disposition requires severity= (the finding-ID's own class; for an identity-only PR-REG-* ID it is the sole routing authority — STICKY section 7) — without it the route's TIERING owner is unset and the route would silently queue")
        if "severity" in kv and key_sev is not None and kv["severity"] != key_sev:
            refuse("severity=%s disagrees with the finding-ID severity %s in key= — the tool never emits a mismatched route (severity-key-mismatch)"
                   % (kv["severity"], key_sev))
        resolved = kv.get("severity") or key_sev
        # PR-HIGH-001 (round 12): the executor-VERIFIED severity is the ROUTING
        # authority — the CRIT-pause and the attestation gate key on the
        # EFFECTIVE severity (verified= when present, else the ID's own).
        effective = kv.get("verified") or resolved
        if effective == "crit":
            refuse("a CRIT never auto-disposes — a verified/effective CRIT always pauses; route it as OWNERSHIP:must-pause (STICKY section 7)")
        # v32 TA.1 (r9 PR-HIGH-018): the attestation gate fires on resolved-OR-
        # effective HIGH (a downgrade from HIGH still attests — the log cannot
        # prove a downgrade legitimate).
        if resolved == "high" or effective == "high":
            if "authority_check" not in kv or "authority_epoch" not in kv:
                refuse("a HIGH auto-route (resolved OR verified-effective HIGH) carries its authority_check=<config_hash> + authority_epoch=<N> attestation pair — bound to the run's OWNERSHIP:config-snapshot record (TA.1; r9 PR-HIGH-018 closed the verified-upgrade bypass)")


def route_severity(kv):
    """The EFFECTIVE severity the pair's TIERING consumes (the auto-disposition
    finding route: verified= else severity= else the finding-ID's class; a cap
    route or any other subtype: the record's own severity=, usually absent)."""
    if kv.get("cap-raise") is None and kv.get("cap-accept") is None and "key" in kv:
        m = FINDING_ID_RE.match(re.split(r"[^A-Za-z0-9-]+", kv["key"])[-1] or "")
        key_sev = (m.group(2) or "").lower() or None if m else None
        return kv.get("verified") or kv.get("severity") or key_sev
    return kv.get("severity")


def validate_record(family, kv, role=None, reader=False):
    """R15 class fix (Round 15 PR-HIGH-001 — the residual of the Rounds 13–15
    reader-trust class): THE single owner of every RECORD-INTRINSIC rule the
    writer applies, invoked by BOTH the writer (cmd_emit, refuse mode, on the
    ASSEMBLED kv — after role stamping and hash derivation, before the
    prior-log sequencing checks and any notice) and the readers (via
    emittable_record in reason mode). There is deliberately no second list:
    a rule that lives here is enforced on emission AND on every prior-record
    read; a rule that does not live here is one of the documented ARGV-ONLY
    rules below, which a completed record cannot carry.

    Rules owned here — every OWNERSHIP subtype: the generic per-field rules
    (check_field_safety) on every non-tool-owned field; the composer-seat
    gate on the actor (`role=` when carried, else the writer's --role); the
    closed subtype vocabulary; the retired/reserved extras (sha=, decision=,
    label_check=); the retired label-snapshot; commit's seat=composer;
    exit-census's children=/refused= rules; profile-switch's transferred=;
    the authority records (validate_authority_record, config_hash= recomputed
    — the writer's pre-derivation form check + derivation run in cmd_emit
    first); the gate-record field rules (validate_gate_record_fields); the
    auto-disposition route rules (validate_auto_disposition); the
    required-cell presence + nonblank floor (ownership_required); no
    epoch=/mode=/class= token on a gate pair's OWNER line (the pair's epoch
    has ONE owner, --epoch → the NOTIFY; mode is COMPUTED; class= is consumed
    by the writer into the NOTIFY).
    Every EMIT_SPECS family (ROLE:start/end/round and the simple types): the
    spec's required presence + nonblank floor and closed enums; ROLE:start's
    profile_dir refusal, profile=-on-claude-p-only, and the pass-key form +
    role=peer rule (check_pass_key_forms); ROLE:round's positive-integer
    round= (v34.1 D8).

    ARGV-ONLY rules (writer only — a completed record cannot violate them):
    the type-scoped flag admissions (--round/--id/--repo/--epoch/--liveness/
    --read-log/--event-ts/--allow-repeat-hash), the tool-owned RESERVED_KEYS
    and the caller-typed derived fields (config_hash=/hash=/sticky_hash= — the completed record
    legitimately CARRIES them), the role=-token-vs---role conflict, the
    finding-key builder ownership (hand-typed vs built), the conflicting-
    class= value rules on a pair emission (the NOTIFY member's), and the
    prior-log SEQUENCING (pass_start_check / cap_transition_check / the
    must-pause dedupe / v34.1's closed-leg end and repeated-commit-hash
    refusals) which stays in cmd_emit.

    WRITER-ONLY RECORD RULE (v46.4 D10 — the one rule a completed record CAN
    break that is deliberately NOT owned here): `emit` refuses an away-pair
    OWNERSHIP:smoke-pass without smoke_by= (cmd_emit, directly after this
    call). It stays out of this function so that a paired smoke written
    before v46.4 without the key remains writer-valid to every reader.

    HISTORICAL CARVE-OUT (reader=True only, the one documented exception):
    leg= on a ROLE record is the whole-file --forward-legs duty — a legacy
    (pre-v31) start/end may omit it; when PRESENT it must be nonblank."""
    prefix, _sep, sub = family.partition(":")
    for k, v in kv.items():
        if k in RESERVED_KEYS:
            continue
        check_field_safety(k, v)
    if prefix == "OWNERSHIP":
        st = sub
        actor = kv.get("role", role)
        if actor is not None:
            check_seat_gate(st, actor)
        if st not in V_OWNERSHIP_SUBTYPES:
            refuse("unknown OWNERSHIP subtype %r (invented vocabulary — the F-20/F-24 class)" % st,
                   "one of: %s" % ", ".join(sorted(V_OWNERSHIP_SUBTYPES)))
        if "sha" in kv:
            refuse("sha= is not a commit key — the required key is hash= and the tool derives it via --repo (F-23)")
        if "decision" in kv:
            refuse("decision= is not an admitted key — gate-disposition's required keys are key= + choice= (F-20)")
        # v32 TA.1 (round-8 in-session review): the retired label_check= key is
        # refused on EVERY OWNERSHIP subtype (recognize-in-historical-logs only).
        if "label_check" in kv:
            refuse("label_check= is retired at v32 on every OWNERSHIP shape — the successor attestation pair is authority_check=<config_hash> + authority_epoch=<N> (recognize historical records on replay, never emit forward)")
        # class= belongs to the paired NOTIFY only (LOW-001 round 5) — the
        # writer pops the caller token off a PAIR subtype before this point, so
        # a pair OWNER line carrying class= is never its output; on the other
        # subtypes class= is an ordinary extra (unchanged writer acceptance).
        if st in PAIR_SUBTYPES and "class" in kv:
            refuse("class= never rides a gate pair's OWNERSHIP owner line — it belongs to the paired NOTIFY only (LOW-001 round 5)")
        if st == "commit" and kv.get("seat", "composer") != "composer":
            refuse("seat=%s is a commit-authority violation — commits are composer-seat only; the tool never writes one" % kv["seat"])
        if st == "exit-census":
            # Peer round 23 (PR-LOW-005): both exit-census integers are ASCII
            # decimal digits ONLY — `str.isdigit()` alone admits U+00B2 (which
            # `int()` rejects) and non-ASCII numerals, neither of which the
            # wrapper's `[!0-9]` reader can produce. Unbounded on purpose: this
            # is NOT parse_count (no nine-digit cap on either key). The OTHER
            # older isdigit()/int() sites stay with their retained follow-up.
            if "children" in kv and not (kv["children"].isascii() and kv["children"].isdigit()):
                refuse("exit-census children= must be a nonnegative integer (got %r)" % kv["children"])
            # v33.4: the wrapper pump's mirror-rewrite receipt — the children=
            # rule's twin. The count is independent of the process census, so
            # it is legal beside refused=capture-failure (unlike children=).
            if "rl_suppressed" in kv and not (kv["rl_suppressed"].isascii() and kv["rl_suppressed"].isdigit()):
                refuse("exit-census rl_suppressed= must be a nonnegative integer (got %r)" % kv["rl_suppressed"])
            # R16 PR-MED-001: the ADMITTED capture-failure refusal shape waives
            # children= — both keys together are contradictory evidence.
            if kv.get("refused") is not None:
                if kv["refused"] != "capture-failure":
                    refuse("exit-census refused= admits only capture-failure")
                if "children" in kv:
                    refuse("exit-census refused=capture-failure and children= are mutually exclusive — a failed capture carries no confirmed count")
        if st == "profile-switch" and kv.get("transferred") not in (None, "yes", "no"):
            refuse("profile-switch transferred= must be yes|no")
        if st == "label-snapshot":
            refuse("OWNERSHIP:label-snapshot is retired at v32 — the [gates: high-auto-ok] label grammar is gone; emit the successor attestation OWNERSHIP:config-snapshot (key=high-auto value=on|off; config_hash= derived)")
        if st in ("config-snapshot", "config-revoke"):
            # the writer's pre-derivation form check + derivation happen in
            # cmd_emit before this call, so the completed record (writer or
            # read) always recomputes its own config_hash= here.
            _why = validate_authority_record(kv, st)
            if _why:
                refuse("OWNERSHIP:%s %s" % (st, _why))
        if st in AWAY_RECORD_SUBTYPES:
            # v34.0 D4: the away records' value rules (config_hash= recomputed).
            _why = validate_away_record(kv, st)
            if _why:
                refuse("OWNERSHIP:%s %s" % (st, _why))
        if st == "ci-verdict":
            # v35.1 Decision 4: the verdict record's value rules.
            _why = validate_ci_verdict_record(kv)
            if _why:
                refuse("OWNERSHIP:ci-verdict %s" % _why)
        if st == "hold":
            # v35.1 Decision 5: the hold record's value rules.
            _why = validate_hold_record(kv)
            if _why:
                refuse("OWNERSHIP:hold %s" % _why)
        if st in ("auto-disposition", "gate-disposition"):
            # v35.1 Decision 3: FORMAT rules only on the two new merge-start
            # keys — presence (tip= on an away merge start) and the ungated
            # route are cmd_emit's sequencing rules, so v35.0 logs stay valid.
            if "tip" in kv and not CI_TIP_RE.match(kv["tip"]):
                refuse("OWNERSHIP:%s tip= must be the checked commit's full 40-hex sha (bad-tip)" % st)
            if "ungated" in kv and kv["ungated"] not in UNGATED_VALUES:
                refuse("OWNERSHIP:%s ungated= admits only %s — the no-checks merge's marker (bad-ungated)"
                       % (st, "|".join(sorted(UNGATED_VALUES))))
        validate_away_keys(st, kv)
        validate_gate_record_fields(st, kv)
        if st == "auto-disposition":
            validate_auto_disposition(kv)
            if _away_act_class(kv.get("key")) == "pre-approval":
                # v44.0 D1: the pre-approval class's value rules — ONE owner,
                # shared by the writer and the fold (a malformed pre-approval
                # line is never writer-valid, so the fold reads it as doubt).
                _why = validate_preapproval_record(kv)
                if _why:
                    refuse("OWNERSHIP:auto-disposition pre-approval %s" % _why)
        required = ownership_required(st, kv)
        for k in required:
            if k == "run":
                continue
            if k not in kv:
                refuse("OWNERSHIP:%s requires %s=" % (st, k),
                       "required keys: ts run " + " ".join(required[1:]))
            # PR-MED-001 (round 13): required identity/evidence values are
            # present AND nonblank (the oracle keys empty-<key> on exactly this).
            if not kv[k].strip():
                refuse("OWNERSHIP:%s %s= is present-but-blank (empty-%s floor) — a required identity/evidence value must be nonblank" % (st, k, k))
        # PR-MED-003 (round 12): a gate pair's epoch identity has ONE owner — the
        # required --epoch flag (consumed by the paired NOTIFY); a separate
        # epoch= token would split the two members' epochs.
        if st in PAIR_SUBTYPES and "epoch" in kv:
            refuse("a gate pair's epoch has ONE owner — the required --epoch; a separate epoch= token is refused (it would split the OWNERSHIP/NOTIFY epochs)")
        if st in PAIR_SUBTYPES and "mode" in kv:
            refuse("mode= is COMPUTED from class+severity (the TIERING table is mechanical) — never caller-supplied")
        return
    spec = EMIT_SPECS.get(family)
    if spec is None:
        refuse("unknown emit TYPE %r (invented line-start types are the F-03 class)" % family,
               "one of: %s, NOTIFY:<state>, OWNERSHIP:<subtype>" % ", ".join(sorted(EMIT_SPECS)))
    if family == "ROLE:start":
        if "profile_dir" in kv:
            refuse("profile_dir lives in Loop config:, never as a start key (STICKY:51; observed F-07 adjunct)")
        if "profile" in kv and kv.get("backend") != "claude-p":
            refuse("profile= is admitted only on backend=claude-p (profile-on-non-claude-p)")
        # v33.0 D3: the per-pass cap keys on an orchestrated peer start —
        # all-or-none, peer-only (the SEQUENCING bind stays in cmd_emit).
        if check_pass_key_forms(kv, "ROLE:start") is not None and kv.get("role", role) != "peer":
            refuse("pass=/peer_round=/cap= ride a ROLE:start role=peer only — the per-pass cap counter is the peer pass's (D3)")
    for k in spec["required"]:
        if k not in kv:
            if reader and k == "leg":
                continue  # HISTORICAL CARVE-OUT: a legacy ROLE record may omit leg= (see the docstring)
            refuse("%s requires %s=" % (family, k),
                   "required keys: ts run " + " ".join(spec["required"]))
        if kv[k] == "" or not kv[k].strip():
            refuse("%s %s= is present-but-blank (empty-%s floor)" % (family, k, k))
    for k, enum_name in spec["enums"].items():
        if k in kv and kv[k] not in ENUMS[enum_name]:
            refuse("%s %s= must be one of %s (got %r)"
                   % (family, k, ", ".join(sorted(ENUMS[enum_name])), kv[k]))
    if family == "ROLE:round":
        # v34.1 D8: the one type-specific rule — a positive integer by parse_count.
        _rn = parse_count(kv["round"])
        if _rn is None or _rn < 1:
            refuse("ROLE:round round= must be a positive integer (got %r)" % kv["round"])


def assemble_ownership_record(st, ts, logged, runkey, required, kv, kvs):
    """The writer's OWN OWNERSHIP serializer (R15: exposed so the selftest's
    generated corpus assembles a would-be record through the writer, never a
    hand-typed twin): `OWNERSHIP: <st> ts= [logged_ts=] run= <required in
    matrix order> <extras in caller order, then derived>`. Returns (line,
    intent tokens)."""
    parts = [st, fmt_kv("ts", ts)]
    if logged:
        parts.append(fmt_kv("logged_ts", logged))
    parts.append(fmt_kv("run", runkey))
    ordered = [k for k in required if k != "run" and k in kv]
    extras = [k for k, _ in kvs if k in kv and k not in ordered] + \
             [k for k in kv if k not in ordered and k not in dict(kvs)]
    for k in ordered + [k for k in extras if k not in ordered]:
        parts.append(fmt_kv(k, kv[k]))
    return "OWNERSHIP: " + " ".join(parts), ["OWNERSHIP:"] + parts


def assemble_simple_record(spec, ts, logged, runkey, kv, kvs):
    """The writer's OWN serializer for the EMIT_SPECS families (ROLE:start/end
    and the simple types): `<prefix> [<verb>] ts= [logged_ts=] run= <required
    in spec order> <extras in caller order>`. Returns (line, intent tokens)."""
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
    return spec["prefix"] + " " + " ".join(parts), spec["prefix"].split() + parts


def emittable_record(line, family, byte_only=False):
    """R14 class fix (Rounds 13–14 were ONE class: helper READERS of prior
    records trusting shapes the helper's own WRITER refuses and the oracle
    rejects). THE shared predicate every prior-record reader consults —
    "would this helper's writer have emitted this line?" — built from the
    helper's own primitives only (never an oracle import):
      lexical — an even double-quote count (the classifier's malformed-
        quoting), no duplicate keys (last-wins would rebind identity), and
        exactly the family's bare token (`<subtype>` / `start` / `end`);
      clock — ts= parses (parse_iso, calendar-total) and is not impossible-
        future (future_instant, the K9 skew bound); logged_ts= is refused on
        the contemporaneous shapes, and elsewhere must parse, not be future,
        and never precede ts= (backwards-logged-ts);
      identity — run= is a stage-<N> runkey (the F-12 domain split);
      fields — the MATRIX_REQUIRED presence + nonblank floor, then the
        subtype's own writer validators reused in REASON mode:
        validate_authority_record / validate_gate_record_fields /
        validate_cap_route / check_pass_key_forms (a keyed ROLE:start must be
        role=peer) / the ROLE enums.
    Returns (kv, bare, None) when emittable, else (kv_or_None, bare_or_None,
    reason). Readers SKIP a non-emittable record toward their documented
    fail-closed side; a class-level parity corpus in the selftest asserts
    `reason is not None` ⇔ the oracle classifies the line non-strict.

    R15 class fix (Round 15 PR-HIGH-001): the field/subtype rules are no
    longer re-listed here — after the LINE layers (the writer's exact emitted
    prefix `<PREFIX>: <verb> `, the assembled_line_ok round-trip, quoting,
    duplicates, bare token, clock, run=) the predicate invokes the writer's
    ONE record owner, validate_record(reader=True), in reason mode — so no
    writer rule can be omitted by construction. Where the writer is STRICTER
    than the oracle (key charset / value safety inside quoted content /
    spacing fidelity / glued OWNERSHIP prefix / retired extras / a non-
    composer role token / mode= or class= or epoch= on the owner / CRIT auto /
    profile_dir=) the direction "oracle non-strict ⇒ helper refuses" still
    holds and the reverse is the selftest's enumerated carve-out set.

    v35.1 (Decision 5, byte-only validity): `byte_only=True` skips ONLY the
    two clock-relative future-time checks, so a line's verdict depends on its
    bytes alone and never changes as the clock moves. Passed by the raw
    probe-log readers alone (raw_record_valid — the hold fold, the CI-history
    classifier, the late-start exemption, the post-verdict scan); every
    existing caller is unchanged.

    v46.4 (D10): ONE record rule of the writer is outside this predicate, by
    decision — `emit` refuses an away-pair smoke-pass without smoke_by=, and a
    record without it (written before v46.4) still passes here, for every
    reader."""
    line = line.rstrip("\r\n")
    prefix, _sep, sub = family.partition(":")
    head = prefix + ":"
    if not line.startswith(head):
        return None, None, "not a %s record" % head
    # the writer emits exactly `<PREFIX>: <verb> ` — a glued or double-spaced
    # prefix is never its output (the oracle's role-no-space class on ROLE;
    # the R12-MED-001 glued-OWNERSHIP trigger shape).
    if not line.startswith(head + " " + sub + " "):
        return None, None, "prefix is not the writer's exact `%s %s ` (glued or misplaced verb — role-no-space)" % (head, sub)
    fidelity = assembled_line_ok(line)
    if fidelity:
        return None, None, fidelity
    body = line[len(head):]
    if body.count('"') % 2:
        return None, None, "odd double-quote count — an unbalanced quote lets a value swallow fields (malformed-quoting)"
    keys = []
    for m in PARSE_KV_RE.finditer(body):
        k = m.group(1) if m.group(1) is not None else m.group(3)
        if k is not None:
            keys.append(k)
    dups = sorted(set(k for k in keys if keys.count(k) > 1))
    if dups:
        return None, None, "duplicate key(s) %s — last-value-wins parsing would silently rebind identity (duplicate-key)" % ",".join(dups)
    kv, bare = parse_kv(body)
    if bare != [sub]:
        return kv, bare, "bare token(s) %r — a %s%s record is exactly `%s` + key=value fields (stray-token / missing verb)" % (bare[:3], head, " " + sub, sub)
    t = parse_iso(kv.get("ts"))
    if t is None:
        return kv, bare, "ts= missing or not a valid local ISO-with-offset instant (ts-malformed)"
    if not byte_only and future_instant(t):
        return kv, bare, "ts= is an impossible-future instant beyond the %dh skew bound (future-ts)" % FUTURE_SKEW_HOURS
    if "logged_ts" in kv:
        if sub in CONTEMPORANEOUS_SUBTYPES:
            return kv, bare, "carries logged_ts= — a contemporaneous record's ts= IS its write time (logged-ts-on-checkpoint)"
        lt = parse_iso(kv["logged_ts"])
        if lt is None:
            return kv, bare, "logged_ts= is not a valid local ISO-with-offset instant (bad-logged-ts)"
        if not byte_only and future_instant(lt):
            return kv, bare, "logged_ts= is an impossible-future instant (future-ts)"
        if lt < t:
            return kv, bare, "logged_ts= precedes ts= — a backdated append (backwards-logged-ts)"
    if not RUNKEY_RE.match(kv.get("run", "")):
        return kv, bare, "run= missing or not a stage-<N> runkey (missing-run)"
    if prefix not in ("OWNERSHIP", "ROLE"):
        return kv, bare, "family %r is not a reader-consulted record family" % family
    # the writer's ONE record owner, in reason mode (R15 class fix)
    return kv, bare, reason_of(validate_record, family, kv, reader=True)


def read_authority(lines, expect_iso, expect_plan, key):
    """v33.0 D12 — the identity-bound authority READ implemented in the shipped
    helper on the emit-side rules (never an import from the oracle). Selects
    the FIRST snapshot-shaped record PER KEY (FIRST-wins — a malformed,
    hash-mismatched, or wrong-identity first record poisons the key; a later
    valid snapshot never repairs or replaces it), then scans the per-key
    revocation stream (every `config-revoke` whose key= is this key — valid or
    malformed, fail-closed — PLUS any revoke-shaped record with a missing or
    unknown key, which revokes every key). Returns (state, info) with state in
    {"bound", "absent", "malformed", "wrong-identity", "off-at-start",
    "revoked"} and info the snapshot fields (+ `revoke_ts`/`revoke_valid` when
    revoked, `reason` when unusable)."""
    snap, snap_reason, snap_seen = None, None, False
    revokes = []
    for n, raw in enumerate(lines, 1):
        line = raw.rstrip("\r\n")
        if not line.startswith("OWNERSHIP:"):
            continue
        kv, bare = parse_kv(line[len("OWNERSHIP:"):])
        if not bare:
            continue
        if bare[0] == "config-snapshot" and kv.get("key") == key and not snap_seen:
            snap_seen = True
            # R13 PR-HIGH-001 → R14 class fix: the shared "would the writer
            # have emitted this?" predicate (lexical + clock + identity +
            # MATRIX + validate_authority_record) — a failure poisons this key
            # (never repaired by a later record).
            why = emittable_record(line, "OWNERSHIP:config-snapshot")[2]
            if why:
                snap_reason = "line %d: %s" % (n, why)
            elif kv["iso"] != expect_iso or kv["plan"] != expect_plan:
                snap_reason = ("line %d: identity mismatch — record iso=%s plan=%s vs expected iso=%s plan=%s (a copied or wrongly-selected policy log is never bearer authority; PR-HIGH-015)"
                               % (n, kv["iso"][:40], kv["plan"][:60], expect_iso[:40], expect_plan[:60]))
                snap_reason = "wrong-identity:" + snap_reason
            else:
                snap = dict(kv, line=n)
        elif bare[0] == "config-revoke":
            rkey = kv.get("key")
            if rkey == key or rkey not in AUTHORITY_KEYS:
                # a malformed revoke (shape OR rules) is recorded valid=False
                # and STILL revokes — fail-closed (unchanged semantics; R13
                # PR-HIGH-001 adds the shape check to the validity flag).
                _rvalid = emittable_record(line, "OWNERSHIP:config-revoke")[2] is None and rkey == key
                revokes.append((n, kv.get("ts"), _rvalid))
    if not snap_seen:
        return "absent", {"reason": "no OWNERSHIP: config-snapshot key=%s record in the policy log" % key}
    if snap is None:
        if snap_reason.startswith("wrong-identity:"):
            return "wrong-identity", {"reason": snap_reason[len("wrong-identity:"):]}
        return "malformed", {"reason": snap_reason}
    if key == "high-auto" and snap["value"] == "off":
        return "off-at-start", dict(snap, reason="value=off at run start — nothing was ever authorized")
    if revokes:
        n, ts, valid = revokes[0]
        return "revoked", dict(snap, revoke_line=n, revoke_ts=ts, revoke_valid=valid,
                               reason="a config-revoke for key=%s follows at line %d (%s) — the boundary is effective at its write"
                               % (key, n, "valid" if valid else "malformed; fail-closed"))
    return "bound", snap


def cmd_attest_check(flags):
    """v33.0 D12 — `attest-check`: the READ-ONLY identity-bound attestation
    read for the composer seat (COMPOSER-ONLY at the grant layer; the seat gate
    here is the mis-attribution guard). Prints ONE result line to stdout; exit
    0 only on a bound, unrevoked `on`/mode; exit 3 on every non-usable state
    (absent, malformed/hash-mismatch, wrong identity, off-at-start, revoked);
    exit 2 on a grammar refusal. Never writes a probe-log record."""
    if flags["--role"] != "composer":
        refuse("attest-check is a composer-seat read — it requires --role composer (spawned-role grants never carry it; SKILL Setup wizard close table)")
    key = flags.get("--key", "high-auto")
    if key not in AUTHORITY_KEYS:
        refuse("--key must be one of %s" % "|".join(sorted(AUTHORITY_KEYS)))
    # v46.4 (D3): every missing flag named in ONE refusal
    missing = [req for req in ("--policy-log", "--iso", "--plan") if req not in flags]
    if missing:
        refuse("attest-check REQUIRES %s — a policy log is never bearer authority for another run; the expected identity is fail-closed input (PR-HIGH-015)" % " ".join(missing))
    pol = flags["--policy-log"]
    if not os.path.isabs(pol):
        refuse("--policy-log must be an absolute path")
    if not ISO_ID_RE.match(flags["--iso"]):
        refuse("--iso %r is not a filename-safe iso-id" % flags["--iso"][:60])
    try:
        with open(pol, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        sys.stdout.write("attest-check: key=%s state=absent reason=\"policy log unreadable: %s\"\n" % (key, str(e).replace('"', "'")[:120]))
        sys.exit(3)
    state, info = read_authority(lines, flags["--iso"], flags["--plan"], key)
    if state == "bound":
        sys.stdout.write("attest-check: key=%s state=bound value=%s config_hash=%s epoch=%s iso=%s plan=\"%s\" ts=%s revoked=no\n"
                         % (key, info["value"], info["config_hash"], info["epoch"], info["iso"], info["plan"], info.get("ts", "")))
        return
    extra = ""
    if state == "revoked":
        extra = " value=%s config_hash=%s revoke_ts=%s revoke_valid=%s" % (
            info["value"], info["config_hash"], info.get("revoke_ts"), "yes" if info.get("revoke_valid") else "no")
    sys.stdout.write("attest-check: key=%s state=%s%s reason=\"%s\"\n" % (key, state, extra, info["reason"].replace('"', "'")))
    if state == "absent" and key != "high-auto":
        sys.stdout.write("attest-check: note — an absent key=%s snapshot on a strict/fix-biased run is INFORMATIONAL, never a downgrade (only gates=executor requires one; D1)\n" % key)
    sys.exit(3)


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
    every must-pause, config-conflict, cap-raise, cap-accept; queued —
    LOW/MED auto-routes and (v33.0 D5) the docs-only/invalid triage
    resolutions, delivered as the phase-boundary batch. The immediate set is
    the generated ENUMS["NOTIFY_IMMEDIATE_CLASSES"] (oracle-owned)."""
    if cls in ENUMS["NOTIFY_IMMEDIATE_CLASSES"]:
        return "immediate"
    if cls == "auto-disposition" and severity == "high":
        return "immediate"
    return "queued"


def cmd_emit(flags, etype, kvs, sink):
    runkey = flags["--run"]
    role = flags["--role"]
    if etype is None:
        refuse("emit needs a TYPE", "emit <TYPE> [key=value ...]; TYPEs: %s" % ", ".join(emit_type_names()))
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
        # v46.4 (D4): the EXPECTED: line says what to type instead
        refuse("--epoch is only accepted where the emitted shape carries epoch= (the gate OWNERSHIP pairs OWNERSHIP:auto-disposition/must-pause, and NOTIFY:<state>), not %s — it would be silently discarded" % etype,
               "the same command without --epoch — emit %s carries no epoch=" % etype)
    # v33.0 D5: --liveness is the must-pause re-fire dedupe window — meaningful
    # on emit OWNERSHIP:must-pause ONLY (the same type-scoped total-argv rule).
    if "--liveness" in flags and etype != "OWNERSHIP:must-pause":
        refuse("--liveness is accepted on emit OWNERSHIP:must-pause only (the re-fire dedupe window), not %s — it would be silently discarded" % etype)
    # v34.1 D10: --allow-repeat-hash skips the repeated-hash refusal — meaningful
    # on emit OWNERSHIP:commit ONLY, and only where that check runs (--log).
    if "--allow-repeat-hash" in flags:
        if etype != "OWNERSHIP:commit":
            refuse("--allow-repeat-hash is accepted on emit OWNERSHIP:commit only (the repeated-hash override), not %s — it would be silently discarded" % etype)
        if "--log" not in flags:
            refuse("--allow-repeat-hash needs --log — the repeated-hash check reads the prior-record source; without --log there is no check to override")

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
        check_field_safety(k, v)  # R15: the ONE per-field owner (value safety + the empty floor), shared with the readers

    # PR-MED-002 (round 7): --role is the SINGLE owner of record identity. A
    # caller role= token may not name a different actor than the required
    # --role — accept only a byte-equal token, refuse a conflict; absent, the
    # per-type stampers fill --role. (Sibling to the --round/--id-vs-key
    # conflict refusal.)
    if "role" in kv and kv["role"] != role:
        refuse("role=%s conflicts with the required --role %s — --role is the single identity owner (pass --role, or a byte-equal role= token)"
               % (kv["role"], role))

    # v47.0 (plan-loop-autonomy-group-2 T1.2 / D4): --policy-log / --iso /
    # --plan are meaningful on ONE emit shape — an away `merge` `choice=start`
    # (an auto- or gate-disposition carrying the away pair), where they are
    # REQUIRED (the refusal is in the OWNERSHIP branch below, beside the
    # verdict check). On every other emission they would be silently ignored,
    # so they refuse (the round-8 total-argv contract, as --read-log).
    _ms_given = [f for f in AWAY_MERGE_START_FLAGS if f in flags]
    if _ms_given and not (etype in ("OWNERSHIP:auto-disposition", "OWNERSHIP:gate-disposition")
                          and "away" in kv and kv.get("choice") == "start"
                          and _away_act_class(kv.get("key")) == "merge"):
        refuse("%s %s accepted on emit only for an away merge start (OWNERSHIP:auto-disposition|gate-disposition key=<runkey>-merge choice=start with the away pair) — on this emission %s would be silently ignored"
               % (" ".join(_ms_given), "is" if len(_ms_given) == 1 else "are", "it" if len(_ms_given) == 1 else "they"))

    # v48.0 (D14 / Critical Constraint 3): a takeover never starts a production
    # act. With LOOP_SEAT set — a watcher takeover's environment — an away
    # `choice=start` whose key class is `deploy-production` is refused,
    # whatever the role flag and wherever the line would go; the run parks
    # there for a composer the operator can see. Round 69 SEC-002: WITH OR
    # WITHOUT the away pair — a start written in the attended form (no
    # `away=` / `away_check=`) is the same production act, and a takeover has
    # no operator beside it to attend one; the constraint is "never".
    if (os.environ.get(SEAT_ENV) and etype in ("OWNERSHIP:auto-disposition", "OWNERSHIP:gate-disposition")
            and kv.get("choice") == "start"
            and _away_act_class(kv.get("key")) == "deploy-production"):
        refuse("an away production start (key=%s choice=start) is refused under %s — a watcher takeover never starts a production act; "
               "write the must-pause that parks the run for a composer the operator can see (takeover-production-start)"
               % (kv.get("key"), SEAT_ENV))

    ts, logged = resolve_clock(flags)
    lines = []
    token_lists = []  # R29: the INTENT (ordered token structure) parallel to `lines`

    # v33.0 D3 / R13 PR-MED-002: --read-log is meaningful ONLY where a keyed
    # shape consumes it (a keyed ROLE:start, a keyed cap transition on
    # auto-disposition / a cap-key gate-disposition); every branch that admits
    # it sets read_log_consumed, and an unconsumed --read-log refuses below
    # (the round-8 total-argv contract — never silently discarded).
    read_log_consumed = False

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
                   "run-close --iso <iso-id> --base </abs/base> --outcome <outcome> [--plan </abs/plan.md>] [--attest owner-dead] [--merge-commit <sha>]")
        if st in AWAY_RECORD_SUBTYPES:
            # v34.0 D4 (Critical Constraint 3): the grant is written ONLY by the
            # `away` subcommand — it numbers the grant, reads the departure
            # file, and derives config_hash=; spawned roles hold the emit
            # grant, so emit can never write either record.
            refuse("emit OWNERSHIP:%s is refused — the away grant is written ONLY by the composer-only `away` subcommand (grant numbering, the departure digest, and config_hash= are COMPUTED; a hand-authored grant is a forged grant)" % st,
                   "away grant|end --run <runkey> --role composer --policy-log </abs> --iso <iso-id> --plan <plan> [--log-root </abs>] scope=<s> | grant=<n> reason=<r>")
        if st in TOOL_ONLY_SUBTYPES:
            # v35.1 Decision 4 (Critical Constraint 2): the verdict is READ and
            # JUDGED by `away ci-verdict` — the pull request and the commit-bound
            # inventories through gh, one pure verdict function, one egress. A
            # hand-authored verdict is a forged CI read.
            refuse("emit OWNERSHIP:%s is refused — the CI verdict is READ (gh pr view + the two commit-bound inventories) and JUDGED by the composer-only `away ci-verdict` verb; a hand-authored verdict is a forged CI read" % st,
                   CI_VERDICT_RECIPE)
        if st == "hold":
            # v35.1 Decision 5: the operator's durable hold on a release act —
            # composer-only, contemporaneous, persisted ONLY to a stage probe
            # log (the names the hold fold reads); the hold's identity is the
            # tool's hold_id= (a clear names it in clears=). The value rules
            # live in validate_hold_record (shared with the fold).
            kv.setdefault("role", role)
            if "--event-ts" in flags:
                refuse("OWNERSHIP:hold is contemporaneous — its ts= IS the operator's word; --event-ts/backfill is refused")
            if "--log" not in flags:
                refuse("emit OWNERSHIP:hold REQUIRES --log <log-root>/stage-<N>-probe.log — the hold fold reads the stage probe logs; an unpersisted hold holds nothing (Decision 5)")
            if not PROBE_LOG_NAME_RE.match(os.path.basename(flags["--log"])):
                refuse("--log for OWNERSHIP:hold must be named stage-<N>-probe.log (got %r) — the only names `away check` and `away report` read (Decision 5)" % os.path.basename(flags["--log"])[:60])
            if "hold_id" in kv:
                refuse("hold_id= is GENERATED by the tool on a hold, never caller-typed — a clear names the hold it closes in clears=<that hold_id> (Decision 5)")
            if kv.get("choice") == "hold":
                kv["hold_id"] = secrets.token_hex(HOLD_ID_BYTES)
        # PR-MED-001 (round 12) / R16 PR-HIGH-001: EVERY composer-owned OWNERSHIP
        # subtype requires --role composer before any notice or write — the
        # gate is a MIS-ATTRIBUTION guard, not caller authentication (the
        # grant/process layer is the authority boundary, the retained R12
        # item). R15 class fix: the gate, the closed subtype vocabulary and the
        # retired/reserved extras (sha=/decision=/label_check=) now live in
        # validate_record — the ONE record owner (applied below, after the
        # subtype branches stamp/derive their fields). The seat gate is kept
        # HERE as well (the same check_seat_gate owner) so a non-composer
        # caller is refused before any derivation (git/STICKY reads) runs.
        check_seat_gate(st, role)
        if st not in V_OWNERSHIP_SUBTYPES:
            refuse("unknown OWNERSHIP subtype %r (invented vocabulary — the F-20/F-24 class)" % st,
                   "one of: %s" % ", ".join(sorted(V_OWNERSHIP_SUBTYPES)))

        # key= construction (DR-3) for finding routes
        key_from_builder = "--round" in flags and "--id" in flags
        if "--round" in flags or "--id" in flags:
            if not key_from_builder:
                refuse("--round and --id come together (the qualified-key builder needs both)")
            if "key" in kv:
                refuse("key= conflicts with --round/--id — the tool BUILDS finding-route keys (never hand-composed)")
            kv["key"] = build_qualified_key(flags)

        # (the required cell set is ownership_required — the R15 single owner,
        # consumed by validate_record and the serializer below)
        if st == "commit":
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
                r = subprocess.run([_git_bin(), "-C", repo, "rev-parse", "HEAD"],
                                   capture_output=True, text=True, timeout=15, env=_git_env())
            except Exception as e:
                envfail("git rev-parse failed under --repo %s: %s" % (repo, e))
            if r.returncode != 0:
                envfail("git rev-parse failed under --repo %s: %s" % (repo, r.stderr.strip()))
            kv["hash"] = r.stdout.strip()
            # PR-HIGH-004 sibling (round 7): a subprocess-derived value reaching
            # a journal line is Constraint-13-checked like any other.
            check_value_safety("hash", kv["hash"])
            kv.setdefault("seat", "composer")  # seat=composer is enforced by validate_record
        if st == "sticky-ack":
            # Round-4 S1 (DR4-1): the composer's run-start STICKY-read receipt.
            # sticky_hash= is COMPUTED, never caller-typed: the tool resolves
            # BOTH shipped STICKY mirrors under --repo, byte-compares them
            # (a mismatch REFUSES — the ack doubles as a free run-start
            # pair-discipline check), and hashes the compared bytes (sha256,
            # 12-hex prefix). Missing mirror files are an ENVIRONMENT failure
            # (exit 3, the git-absent precedent); a divergent pair is a
            # Constraint-5 violation the composer must fix (exit 2).
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
            # DR-1 item 4 (admitted at R8): the wrapper's census record — the
            # children=/refused= rules (R16 PR-MED-001) live in validate_record.
            kv.setdefault("role", role)
        # profile-switch transferred= and the retired label-snapshot (v32 TA.1)
        # are validate_record rules too.
        if st == "config-snapshot":
            # v32 TA.1 (D1/PR-HIGH-013/015): the run-start authority
            # attestation — the label-snapshot successor, 1:1 on the policy-log
            # home, FIRST-wins PER KEY, and fail-closed reads. v33.0 D1/T1.6
            # WIDENS the admitted keys to AUTHORITY_KEYS {high-auto, gates}
            # with per-key value domains (high-auto: on|off; gates:
            # strict|fix-biased|executor) and PER-KEY hash serialization
            # "iso=<iso>|plan=<plan>|epoch=<epoch>|<key>=<value>" — for
            # key=high-auto this is BYTE-IDENTICAL to the v32 serialization, so
            # every existing high-auto hash is unchanged. config_hash= is
            # DERIVED (never caller-typed); the hash BINDS the isolation-run
            # identity, authoritative plan, and run-start epoch, not just the
            # setting value. Contemporaneous like sticky-ack: --event-ts is
            # refused. The RULES live in validate_authority_record — the ONE
            # record-shape owner the attest-check reader also applies (D12).
            kv.setdefault("role", role)
            if "--event-ts" in flags:
                refuse("OWNERSHIP:config-snapshot is a contemporaneous authority record — its ts= IS the attestation time; --event-ts/backfill is refused")
            if "config_hash" in kv:
                refuse("config_hash= is DERIVED, never caller-typed — the tool computes it from iso/plan/epoch/key/value (the F-23/F-04 derivation class)")
            _why = validate_authority_record(kv, "config-snapshot", check_hash=False)
            if _why:
                refuse("OWNERSHIP:config-snapshot %s" % _why)
            kv["config_hash"] = authority_hash(kv["iso"], kv["plan"], kv["epoch"], kv["key"], kv["value"])
        if st == "config-revoke":
            # v32 TA.1 (PR-HIGH-006/016): the monotonic one-way revocation
            # record — the FIRST write of the pinned revoke-first disable
            # transaction; the authority boundary is effective at THIS append.
            # epoch= is the revocation counter (a positive integer from 1; the
            # snapshot is epoch 0); a duplicate/retry disable re-emits the same
            # epoch idempotently — monotonicity across records is the oracle's
            # scored-layer check (the stateless writer validates form).
            # v33.0 D1: key= admits AUTHORITY_KEYS — a `key=gates` revoke is the
            # same one-way transaction on its OWN per-key stream.
            # Contemporaneous: --event-ts refused.
            kv.setdefault("role", role)
            if "--event-ts" in flags:
                refuse("OWNERSHIP:config-revoke is a contemporaneous authority boundary — its ts= IS the revocation time; --event-ts/backfill is refused")
        # LOW-001 (round 5): class= belongs to the paired NOTIFY only — it never
        # rides the OWNERSHIP record (consumed here, before the record check).
        cls_arg = kv.pop("class", None) if st in PAIR_SUBTYPES else None
        # R15 class fix: THE record check — every record-intrinsic rule (the
        # R14 validate_gate_record_fields / validate_cap_route owners included)
        # on the ASSEMBLED kv, in refuse mode; the readers apply the same
        # function in reason mode via emittable_record. Only ARGV rules and the
        # prior-log SEQUENCING checks remain below.
        validate_record("OWNERSHIP:" + st, kv, role=role)
        # v46.4 (plan-loop-field-review-fixes D10): the WRITER requires
        # smoke_by= on a grant-tagged smoke, so the away report can say who
        # performed it. Here, on the emit path, and never in validate_record:
        # the readers share that validator, and a paired smoke written before
        # v46.4 without the key must keep reading as it does (absent reads as
        # operator) — no old record becomes invalid or changes section.
        if st == "smoke-pass" and "away" in kv and "smoke_by" not in kv:
            _by = "|".join(sorted(SMOKE_BY_VALUES))
            refuse("an away-pair OWNERSHIP:smoke-pass carries smoke_by=<%s> — who performed the smoke; the writer requires it on a grant-tagged smoke from v46.4 (bad-smoke-by; D10)" % _by,
                   "emit OWNERSHIP:smoke-pass smoke_by=<%s> away=<n> away_check=<config_hash> [detail=...]" % _by)
        if st == "commit" and "--log" in flags and "--allow-repeat-hash" not in flags:
            # v34.1 D10: a hash this log already records is refused before any write.
            _prior_ts = recorded_commit_ts(flags["--log"], kv["hash"])
            if _prior_ts is not None:
                refuse("OWNERSHIP:commit hash=%s is already recorded in this log (the earlier record's ts=%s) — the usual cause: HEAD did not move, so the commit did not happen; check `git log -1`. Pass --allow-repeat-hash only when the same commit is meant to be recorded again in this log (D10)"
                       % (kv["hash"], _prior_ts))
        # v35.1 Decision 3 (D9 (b)/(d); Critical Constraints 5–6): the away-start
        # refusals — prior-log SEQUENCING beside the repeated-hash check, never
        # inside validate_record (readers never re-apply a clock-relative rule).
        # The guarantee is ORDER, not authorship: a writer-valid, unstamped,
        # fresh admitting `ci-verdict` for the tip precedes an away merge
        # `choice=start` in the same log — except a TRUE late start (D9 (b)),
        # a record repair admitted on the pairing owner's say-so without a
        # verdict; who wrote a line is not authenticated.
        _away_cls = _away_act_class(kv.get("key"))

        def _prior_raw():
            # the prior-record source, read ONCE per emission through the raw
            # reader (an unreadable --log is the sink's own envfail, exit 3)
            _raw, _rerr = raw_record_lines(flags["--log"])
            if _raw is None:
                envfail("cannot read the prior-record source %s: %s" % (flags["--log"], _rerr))
            return _raw
        if "away" in kv and kv.get("choice") == "start":
            if st == "smoke-pass":
                refuse("an away-pair OWNERSHIP:smoke-pass never carries choice=start — a release act's start rides OWNERSHIP:auto-disposition or OWNERSHIP:gate-disposition only (Decision 3)")
            if _away_cls not in AWAY_ACT_CLASSES:
                refuse("an away-pair choice=start needs a release-act key class — key=<runkey>-<%s>, got key=%r (D9 (d))"
                       % ("|".join(sorted(AWAY_ACT_CLASSES)), kv.get("key", "")[:60]))
            if _away_cls == "merge":
                if "--log" not in flags:
                    refuse("an away merge start REQUIRES --log — its admission reads the log's latest ci-verdict (an unpersisted start admits nothing)", CI_VERDICT_RECIPE)
                if "tip" not in kv:
                    refuse("an away merge start carries tip=<the checked commit's 40-hex sha> — the verdict it rides names that tip", CI_VERDICT_RECIPE)
                # v47.0 (D4): the three flags the listing check reads with —
                # required on EVERY away merge start, named in one refusal,
                # before any log is read
                _ms_missing = [f for f in AWAY_MERGE_START_FLAGS if f not in flags]
                if _ms_missing:
                    refuse("an away merge start REQUIRES %s — every away merge start is checked against the bound grant and its departure file's `Stop: merge` lines (v47.0 D4)"
                           % " ".join(_ms_missing), AWAY_MERGE_START_RECIPE)
                # v47.0 (round 7 MED-001): the key is bound to the runkey. A
                # `Stop: merge` line is matched to a start by the start's own
                # key=, so a start written under ANOTHER merge key would read
                # as unlisted and pass a `park` line; the published recipes
                # spell key=<runkey>-merge, and here it is the only key
                # admitted. A mislabel now needs a wrong --run too — and the
                # verdict is looked up under that run.
                if kv["key"] != "%s-merge" % runkey:
                    refuse("an away merge start's key= is <--run>-merge — got key=%s under --run %s; the departure file's `Stop: merge` lines are matched by this key, so it names this run's own merge (merge-key-not-run)"
                           % (kv["key"][:60], runkey), AWAY_MERGE_START_RECIPE)
                _raw = _prior_raw()
                if "--event-ts" in flags:
                    _why = ci_late_start_refusal(_raw, runkey, kv, ts)
                else:
                    _why = ci_merge_start_refusal(_raw, runkey, kv["tip"], kv.get("ungated") == "merge", parse_iso(ts))
                if _why:
                    refuse("an away merge start is refused: %s" % _why, CI_VERDICT_RECIPE)
                # v47.0 (D4): the listing check — after the verdict check, whose
                # refusals keep their text and order; nothing is written above
                _why = away_merge_listing_refusal(flags["--policy-log"], flags["--iso"], flags["--plan"],
                                                  os.path.dirname(flags["--log"]), runkey, kv,
                                                  "--event-ts" in flags, _raw)
                if _why:
                    refuse("an away merge start is refused: %s" % _why, AWAY_MERGE_START_RECIPE)
        elif (st in ("auto-disposition", "gate-disposition") and "away" not in kv and _away_cls == "merge"
              and kv.get("choice") == "start" and "--log" in flags):
            # Fable review F2: a merge start that dropped its away pair, in a log
            # that already holds a verdict line (whatever its validity), is a slip.
            # "A verdict line" is raw_classify's notion — the one every reader
            # shares: a valid or doubtful ci-verdict line counts; a writer-valid
            # record of another family that merely QUOTES the marker does not
            # (round 10 LOW-4; Step H round 22 LOW).
            if any(raw_classify(t, "ci-verdict") is not None for t in _prior_raw()):
                refuse("a merge start WITHOUT the away pair in a log that holds a ci-verdict line — an unattended merge start carries away=<n> away_check=<config_hash> (Decision 3, F2)")
        # v35.0 A9 / D8: the record-before-act guard — read the prior log BEFORE
        # the write; the warning is printed after it and never refuses.
        _no_start_warn = (st in ("auto-disposition", "gate-disposition") and "--log" in flags
                          and "away" in kv and kv.get("choice") in ("done", "failed")
                          and _away_act_class(kv.get("key")) in AWAY_ACT_CLASSES
                          and away_outcome_without_start(flags["--log"], runkey, kv))
        route_sev = route_severity(kv) if st == "auto-disposition" else kv.get("severity")
        if st == "gate-disposition":
            if kv.get("key") in CAP_TRANSITION_GATE_KEYS:
                _bundle = check_cap_transition_bundle(kv, "OWNERSHIP:gate-disposition (cap key)")
                if _bundle is not None:
                    # R13 PR-MED-002: an operator raise records a LARGER cap;
                    # any other cap disposition records the current budget.
                    _src = flags.get("--log") or flags.get("--read-log")
                    if _src is None:
                        refuse("a keyed cap gate-disposition (pass=/cap=) REQUIRES a readable prior-record source — pass --log <probe-log> or --read-log <probe-log> (D3, R13 PR-MED-002)")
                    read_log_consumed = True
                    cap_transition_check(_src, runkey, _bundle[0],
                                         "operator-raise" if kv.get("choice") == "raise" else "operator-other", _bundle[1])
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
            # BEFORE either pair member is assembled — R14/R15: it is
            # validate_auto_disposition (cap route + attestation coherence +
            # severity/verified + the finding-route rules), applied by
            # validate_record above. Only the KEYED transition's prior-log
            # sequencing (R13 PR-MED-002) remains here.
            cap = kv.get("cap-raise")
            capacc = kv.get("cap-accept")
            if cap is not None or capacc is not None:
                _bundle = check_cap_transition_bundle(kv, "OWNERSHIP:auto-disposition (cap transition)")
                if _bundle is not None:
                    # R13 PR-MED-002: a KEYED transition is validated against
                    # the pass's recorded budget in the prior log — a raise
                    # records budget+1, an accept-close the current budget.
                    _src = flags.get("--log") or flags.get("--read-log")
                    if _src is None:
                        refuse("a keyed cap transition (pass=/cap=) REQUIRES a readable prior-record source — pass --log <probe-log> or --read-log <probe-log> (the pass's budget lives on its own records; D3/D2, R13 PR-MED-002)")
                    read_log_consumed = True
                    cap_transition_check(_src, runkey, _bundle[0],
                                         "auto-raise" if cap is not None else "accept-close", _bundle[1])

        if "--read-log" in flags and not read_log_consumed:
            refuse("--read-log is accepted only where a KEYED shape reads the prior log (a keyed ROLE:start, a keyed cap-raise/cap-accept auto-disposition, a keyed cap gate-disposition), not OWNERSHIP:%s — it would be silently ignored" % st)

        # the writer's OWN serializer (R15: shared with the selftest's generated corpus)
        _line, _tokens = assemble_ownership_record(st, ts, logged, runkey, ownership_required(st, kv), kv, kvs)
        lines.append(_line)
        token_lists.append(_tokens)

        # ---- the atomic paired NOTIFY (gate routes) ----
        if st in PAIR_SUBTYPES:
            if "key" not in kv:
                refuse("a gate %s emission needs key= (or --round/--id) for its paired NOTIFY" % st)
            epoch = flags.get("--epoch")
            if epoch is None:
                # v46.4 (D4): the EXPECTED: line is the one-line shape with the flag
                refuse("a gate pair emission needs --epoch (epoch= rides every non-skipped NOTIFY)",
                       "--run %s --role %s [--log <probe-log>] --epoch <activation id> emit OWNERSHIP:%s key=<key> [key=value ...]" % (runkey, role, st))
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
            # (a caller mode= token is refused by validate_record — mode is COMPUTED)
            mode = compute_mode(cls, route_sev)
            # v33.0 D5 (PR-MED-005): the must-pause RE-FIRE dedupe runs BEFORE
            # any notice or write — with --log present, the same qualified key
            # already owning a must-pause with NO later gate-disposition, whose
            # owner is younger than the liveness window, REFUSES the whole pair
            # (nothing written; the still-open gate keeps its existing owner +
            # notice). Past the window on a new epoch the full pair fires as
            # today; the same-key-same-epoch `NOTIFY: skipped` shape is untouched.
            if st == "must-pause":
                _lv = parse_liveness(flags)
                if "--liveness" in flags and "--log" not in flags:
                    refuse("--liveness needs --log — the must-pause re-fire dedupe reads the prior-record source (an unpersisted stdout pair has no record to dedupe against)")
                if "--log" in flags and _lv is not None:
                    _open_age = must_pause_open_owner_age(flags["--log"], runkey, kv["key"])
                    if _open_age is not None and _open_age < _lv * 60:
                        refuse("OWNERSHIP:must-pause key=%s already has an OPEN owner %d s old (no later gate-disposition) inside the %d-min liveness window — the re-fire is REFUSED as a whole pair; the open gate keeps its existing owner and notice (D5, PR-MED-005); narrate in chat only"
                               % (kv["key"], _open_age, _lv))
            _paused = kv.get("detail") or kv.get("reason") or ("%s %s" % (st, kv["key"]))
            if mode == "immediate":
                summary = _paused
                if "rec" in kv:
                    summary = "%s [rec=%s]" % (summary, kv["rec"])  # D6: the recommendation rides the body
                state = "sent" if fire_notice(runkey, summary, cls, kv.get("reason")) else "failed"
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
        if _no_start_warn:
            sys.stderr.write("warning: %s%s outcome recorded with no start before it — record starts before the act\n"
                             % (kv["key"], " path=%s" % kv["path"] if "path" in kv else ""))
        if st == "must-pause" and sink is not None:
            # v34.1 D11: the paste-ready ask — after the pair, file sink only.
            _print_pause_ask(kv["key"], epoch, state, _paused, kv.get("rec"), kv.get("options"))
        return

    # ---- NOTIFY standalone ----
    if etype.startswith("NOTIFY:"):
        if "--read-log" in flags:
            refuse("--read-log is accepted only on the keyed emit shapes (ROLE:start / cap transitions), not %s — it would be silently ignored" % etype)
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
                # v33.0 D5: the retry fires at ITS class's tier (a class-less
                # legacy record fails toward the louder critical tier).
                state = "retried" if fire_notice(runkey, summary, cls, kv.get("reason")) else "failed"
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

    kv.setdefault("role", role) if "role" in spec["required"] else None
    # R15 class fix: THE record check FIRST (spec required floor + enums + the
    # ROLE:start field rules) — the same owner the readers apply in reason mode;
    # the type-specific ARGV rules and the prior-log sequencing follow.
    validate_record(etype, kv, role=role)

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
        # profile_dir / profile-on-claude-p-only / the pass-key form + role=peer
        # rule are validate_record's (R15) — applied below with the spec floor.
        # v33.0 D3: a keyed peer start is SEQUENCED against the actual prior log
        # (--log, or the READ-ONLY --read-log whose sink stays stdout).
        _pk = check_pass_key_forms(kv, "ROLE:start")
        if _pk is not None:
            _src = flags.get("--log") or flags.get("--read-log")
            if _src is None:
                refuse("a keyed ROLE:start (pass=/peer_round=/cap=) REQUIRES a readable prior-record source — pass --log <probe-log> (composer emission) or --read-log <probe-log> (read-only; the wrapper's retained-descriptor write stays the sink) (D3, PR-MED-003)")
            pass_start_check(_src, runkey, _pk[0], _pk[1], _pk[2])
        elif "--read-log" in flags:
            refuse("--read-log is meaningful only on a keyed ROLE:start (pass=/peer_round=/cap= present) — on any other emission it would be silently ignored")
    elif "--read-log" in flags:
        refuse("--read-log is accepted only on the keyed emit shapes (a keyed ROLE:start, a keyed cap transition), not %s" % etype)
    if etype == "ROLE:end" and "--log" in flags:
        # v34.1 D9: an end for a leg that is already closed is refused before any write.
        _closed_ts = closed_leg_end_ts(flags["--log"], runkey, kv["role"], kv["leg"])
        if _closed_ts is not None:
            refuse("ROLE:end run=%s role=%s leg=%s — this leg is already closed by an earlier ROLE: end (ts=%s); a second end is refused (the duplicate-end class). A verdict on the finished leg belongs on the CONSUME: record, not on another end (D9)"
                   % (runkey, kv["role"], kv["leg"], _closed_ts))
        # v48.0 D23: a wrapper-spawned leg's end is its wrapper's; anyone else's
        # is the clean close, admitted on the role-liveness reader's `over`
        _end_why = leg_end_refusal(os.path.dirname(flags["--log"]), runkey, kv["leg"], kv["result"])
        if _end_why is not None:
            refuse(_end_why)
    if etype == "SPAWN":
        # v33.0 D3: the same three keys ride `SPAWN … child=peer` ADDITIVELY
        # (diagnostic) — form + all-or-none only; the sequencing bind lives on
        # the ROLE: start (one validation owner).
        if check_pass_key_forms(kv, "SPAWN") is not None and kv.get("child") != "peer":
            refuse("pass=/peer_round=/cap= on SPAWN ride a child=peer spawn only (D3)")
    if etype == "WATCH:armed":
        if kv.get("layer2") == "none" and "reason" not in kv:
            refuse("layer2=none requires reason= naming the real arm failure / resolved no-monitor case (none-without-reason)")
        if kv.get("layer2") == "none" and "delivery" in kv:
            refuse("a layer2=none armed line never carries delivery= — nothing to consume (the oracle's delivery-on-none class; v32.2)")

    # the writer's OWN serializer; R29: the INTENT token list rides beside the
    # line — the chokepoint compares parsed==this.
    _line, _tokens = assemble_simple_record(spec, ts, logged, runkey, kv, kvs)
    write_lines(sink, [_line], token_lists=[_tokens])


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


def status_digest(root, allow=()):
    """The PINNED digest convention (DR-1 item 3, F-04's fix): sha256 hex over
    the root's `git status --short` output with the trailing newline stripped.
    Returns (digest, None) or (None, error-string) — NEVER an empty-string
    digest on failure.

    v33.0 D4 `allow` (the --allow-path list for THIS root, repo-relative):
    status lines whose path is EXACTLY one of the allowed paths are dropped
    BEFORE hashing — on both the pre and post capture, so a permitted write
    (a peer's authoritative plan file / findings sidecar) is invisible to the
    verdict while any other change in the root stays visible. Exact-path only:
    a rename line (`R  a -> b`) or a quoted path never matches an allow entry."""
    import hashlib
    try:
        r = subprocess.run([_git_bin(), "-C", root, "status", "--short"],
                           capture_output=True, text=True, timeout=60, env=_git_env())
    except Exception as e:
        return None, "git status failed under %s: %s" % (root, e)
    if r.returncode != 0:
        return None, "git status failed under %s: %s" % (root, r.stderr.strip()[:200])
    out = r.stdout.rstrip("\n")
    if allow:
        allowed = set(allow)
        kept = [l for l in out.split("\n") if not (len(l) > 3 and l[3:] in allowed)]
        out = "\n".join(kept)
    return hashlib.sha256(out.encode("utf-8")).hexdigest(), None


# R13 PR-MED-001: a leading `.` is LEGAL (the canonical `.cursor/plans/plan-*.md`
# + `findings-*.md` allow-list); traversal is refused by the SEGMENT rule in
# allow_path_ok, never by the charset. Charset still excludes whitespace,
# quotes, and every pre-state delimiter (`|` `,` `;`).
ALLOW_PATH_RE = re.compile(r"\A[A-Za-z0-9._][A-Za-z0-9._/@+-]*\Z")


def allow_path_ok(rel):
    """v33.0 D4 — the ONE admission rule for an allow-path (CLI `--allow-path`
    and the 5-field pre-state share it — R13 PR-MED-001): repo-relative, the
    charset above, never absolute, and every `/`-split segment nonempty and
    not `.`/`..` (so `./x`, `a//b`, `a/./b`, `../x`, and a trailing `/` all
    refuse while `.cursor/plans/plan.md` and `apps/x/.cursor/plans/plan.md`
    are exact, canonical spellings)."""
    if not ALLOW_PATH_RE.match(rel) or os.path.isabs(rel):
        return False
    return all(seg not in ("", ".", "..") for seg in rel.split("/"))


def parse_allow_paths(entries, root_names):
    """v33.0 D4: `<root-name>:<repo-relative path>` entries → {root: [paths]}.
    Fail-closed: the root must be a manifest root, the path must be relative
    (never absolute, never a `..` segment), and its charset excludes every
    pre-state delimiter (`|` `,` `;`) plus whitespace/quotes (Constraint 13)."""
    by_root = {}
    for ent in entries:
        if ":" not in ent:
            refuse("--allow-path %r is not <root-name>:<repo-relative path>" % ent[:80])
        rname, rel = ent.split(":", 1)
        if rname not in root_names:
            refuse("--allow-path names root %r which is not in the --root manifest (%s)" % (rname[:40], ", ".join(root_names)))
        if not allow_path_ok(rel):
            refuse("--allow-path path %r must be an exact repo-relative path — no empty/`.`/`..` segment, no absolute prefix, no whitespace, quote, or delimiter (| , ;)" % rel[:80])
        lst = by_root.setdefault(rname, [])
        if rel not in lst:
            lst.append(rel)
    return by_root


def parse_liveness(flags):
    """v33.0 D4/D5: `--liveness <min>|off` → positive int minutes, or None for
    OFF (no freshness basis: attribution / the re-fire dedupe are disabled).
    Absent → the helper default 10 (the wizard's liveness default)."""
    raw = flags.get("--liveness")
    if raw is None:
        return 10
    if raw == "off":
        return None
    _n = parse_count(raw)
    if _n is None or _n < 1:
        refuse("--liveness must be a positive integer (minutes) or `off` (got %r)" % raw[:20])
    return _n


def attribute_base_dirt(base_path, own_iso, liveness_min, changed_paths):
    """v33.0 D4 (advisory attribution, KNOWN-WEAK — Accepted Assumptions):
    scan `<base>/.cursor/loops/*-active` for a marker of a DIFFERENT run that
    (a) has no `<iso>-active.complete-*` sibling, (b) claims (`checkout=`,
    realpath'd) the realpath of EVERY changed root, and (c) has a newest
    GENUINE probe log — `.cursor/loops/<iso>/stage-*-probe.log` exactly,
    `*harness-probe*` transcripts excluded — whose mtime is within
    2 x liveness_min of now. Returns (iso, age_min) for the FRESHEST such
    marker, else None. Liveness OFF (None) ⇒ None (no freshness basis).
    Never raises on unreadable markers — an unreadable/foreign-shaped marker
    simply does not attribute (attribution is advisory; the pause is the
    safe default)."""
    import glob as _glob
    import time as _time
    if liveness_min is None or not changed_paths:
        return None
    try:
        changed_real = set(os.path.realpath(p) for p in changed_paths)
    except OSError:
        return None
    loops = os.path.join(base_path, ".cursor", "loops")
    window_s = 2 * liveness_min * 60
    now = _time.time()
    best = None
    for marker in sorted(_glob.glob(os.path.join(loops, "*-active"))):
        iso = os.path.basename(marker)[:-len("-active")]
        if not iso or iso == own_iso or not ISO_ID_RE.match(iso):
            continue
        if _glob.glob(marker + ".complete-*"):
            continue
        try:
            with open(marker, encoding="utf-8") as f:
                kv, _raw = _rc_parse_kv_lines(f.read().splitlines())
        except (OSError, UnicodeDecodeError):
            # R17 PR-MED-001: an unreadable OR undecodable foreign marker is
            # unusable ADVISORY evidence — skip the candidate; the escape
            # verdict stays dirty-unattributed and is still written.
            continue
        if kv.get("iso") != iso:
            continue  # a marker whose body disagrees with its name is not evidence
        chk = kv.get("checkout")
        if not chk or not os.path.isabs(chk):
            continue
        try:
            chk_real = os.path.realpath(chk)
        except OSError:
            continue
        if changed_real != {chk_real}:
            continue  # every changed root must BE the claimed checkout
        newest = None
        for p in _glob.glob(os.path.join(loops, iso, "stage-*-probe.log")):
            if "harness-probe" in os.path.basename(p):
                continue
            try:
                m = os.stat(p).st_mtime
            except OSError:
                continue
            newest = m if newest is None or m > newest else newest
        if newest is None:
            continue
        age_s = now - newest
        if age_s < 0 or age_s > window_s:
            continue
        age_min = int(age_s // 60)
        if best is None or age_min < best[1]:
            best = (iso, age_min)
    return best


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
    root_names = [n for n, _p in pairs]
    state_path = os.path.join(log_root, "%s-escape-%s.pre" % (flags["--run"], leg))
    # v33.0 D4: the edit-surface declaration, the allow-path list, the run's
    # own iso (attribution needs a DIFFERENT run's marker) and the liveness
    # window — validated on BOTH captures (a bad value never reaches the
    # pre-state file or a record).
    edit_surface = flags.get("--edit-surface")
    if edit_surface is not None and edit_surface not in root_names:
        refuse("--edit-surface %r must name one of the --root manifest roots (%s)"
               % (edit_surface[:40], ", ".join(root_names)))
    allow_by_root = parse_allow_paths(flags.get("--allow-path", []), root_names)
    own_iso = flags.get("--iso")
    if own_iso is not None and not ISO_ID_RE.match(own_iso):
        refuse("--iso %r is not a filename-safe iso-id" % own_iso[:60])
    liveness_min = parse_liveness(flags)

    if capture == "pre":
        lines = []
        for name, path in pairs:
            digest, err = status_digest(path, allow_by_root.get(name, ()))
            if err:
                refuse("pre-capture FAILED for root %s — refusing (exit 2, no spawn, nothing written): %s"
                       % (name, err))
            # v33.0 D4: FIVE fields — name|path|digest|edit-surface-flag|allow-list
            # (allow-list `,`-joined, empty when none). A v32.5 helper refuses
            # this width (a downgrade is legal only at a completed-leg
            # boundary); a v33.0 helper reading a legacy 3-field file falls
            # back to the all-roots verdict (the post branch below).
            lines.append("%s|%s|%s|%s|%s" % (name, path, digest,
                                             "1" if name == edit_surface else "0",
                                             ",".join(allow_by_root.get(name, ()))))
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
    pre_edit = {}    # v33.0: name -> "1"/"0" (5-field files only)
    pre_allow = {}   # v33.0: name -> [paths]  (5-field files only)
    widths = set()
    try:
        _pre_lines = open(state_path, encoding="utf-8").read().splitlines()
    except UnicodeDecodeError as e:
        # R17 PR-MED-001: a pre-state the helper cannot decode is a CAPTURE
        # FAILURE, never a verdict — the ONE admitted refusal record (exit 3),
        # naming the first declared root; the diagnostic stays on stderr and
        # the unusable pre-state is consumed like every other post outcome.
        sys.stderr.write("ENVFAIL: pre-state file %s is not valid UTF-8 (%s) — no baseline to prove against\n" % (state_path, e))
        rec = ("OWNERSHIP: escape-check ts=%s run=%s role=%s leg=%s refused=capture-failure root=%s detail=\"pre-state file undecodable; diagnostic on stderr\""
               % (now_iso(), flags["--run"], flags["--role"], leg, pairs[0][0]))
        write_lines(sink, [rec])
        try:
            os.remove(state_path)
        except OSError:
            pass
        sys.exit(3)
    for raw in _pre_lines:
        raw = raw.rstrip("\n")
        if not raw:
            continue
        parts = raw.split("|")
        # v33.0 D4: FIVE fields forward; the legacy THREE-field shape (a leg
        # whose pre ran on a v32.5 helper) is accepted with the all-roots
        # verdict. Any other width, or a mixed-width file, is malformed.
        if len(parts) not in (3, 5):
            refuse("malformed pre-state line (expected name|path|digest[|edit-surface-flag|allow-list]): %r" % raw[:80])
        widths.add(len(parts))
        if len(widths) > 1:
            refuse("pre-state file mixes 3-field and 5-field lines — one baseline, one width")
        name, path, digest = parts[0], parts[1], parts[2]
        if not ROOT_NAME_RE.match(name):
            refuse("pre-state root name %r is not lowercase [a-z0-9-]+" % name[:40])
        if name in pre:
            refuse("duplicate root name %r in pre-state (ambiguous baseline)" % name)
        if not os.path.isabs(path):
            refuse("pre-state root path %r is not absolute" % path[:80])
        check_value_safety("root", path, is_path=True)
        if not DIGEST_RE.match(digest):
            refuse("pre-state digest for root %s is not an 8-64 char lowercase hex digest" % name)
        if len(parts) == 5:
            if parts[3] not in ("0", "1"):
                refuse("pre-state edit-surface flag for root %s must be 0|1 (got %r)" % (name, parts[3][:10]))
            pre_edit[name] = parts[3]
            pre_allow[name] = [p for p in parts[4].split(",") if p]
            for p in pre_allow[name]:
                if not allow_path_ok(p):  # the same single owner as the CLI parse (R13 PR-MED-001)
                    refuse("pre-state allow-list entry %r for root %s is not an exact repo-relative path" % (p[:60], name))
        pre[name] = (path, digest)
        order.append(name)
    if not order:
        refuse("pre-state file %s is empty — no baseline to prove against" % state_path)
    if [n for n, _ in pairs] != order or any(pre[n][0] != p for n, p in pairs):
        refuse("post root set/order differs from the pre capture (%s) — the root set never shrinks or reorders mid-run"
               % ", ".join(order))
    legacy = (widths == {3})
    ts = now_iso()
    if legacy:
        # Mixed-version leg (D4): the pre digests were UNFILTERED and carried no
        # edit-surface declaration, so the post must compare like-for-like —
        # all-roots verdict, no edit_surface= key, no allow filtering, and the
        # post-side flags are ignored for the verdict (they cannot be applied
        # to a baseline that never saw them).
        edit_surface = None
        allow_by_root = {}
    else:
        # v33.0 D4 (PR-MED-002): a pre/post edit-surface or allow-path
        # MISMATCH is not a grammar refusal — the activation already ran, so
        # the evidence must land: the ONE admitted refusal record
        # (`refused=capture-failure`, exit 3) naming the first mismatching
        # root, never a recordless exit 2.
        for name, _p in pairs:
            want_edit = "1" if name == edit_surface else "0"
            if pre_edit.get(name) != want_edit or pre_allow.get(name, []) != list(allow_by_root.get(name, [])):
                sys.stderr.write("ENVFAIL: edit-surface/allow-path declaration for root %s differs between pre and post (pre edit=%s allow=%s; post edit=%s allow=%s)\n"
                                 % (name, pre_edit.get(name), ",".join(pre_allow.get(name, [])),
                                    want_edit, ",".join(allow_by_root.get(name, []))))
                rec = ("OWNERSHIP: escape-check ts=%s run=%s role=%s leg=%s refused=capture-failure root=%s detail=\"edit-surface/allow-path mismatch between pre and post\""
                       % (ts, flags["--run"], flags["--role"], leg, name))
                write_lines(sink, [rec])
                try:
                    os.remove(state_path)  # the pair is consumed by its refusal record
                except OSError:
                    pass
                sys.exit(3)
    manifest = []
    for name, path in pairs:
        after, err = status_digest(path, allow_by_root.get(name, ()))
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
            try:
                os.remove(state_path)  # v33.0 (R11 LOW-001): the refusal record IS the pair's record — consumed like every other post outcome
            except OSError:
                pass
            sys.exit(3)
        manifest.append((name, path, pre[name][1], after))
    # v33.0 D4: the verdict is computed over the NON-edit-surface roots; the
    # edit-surface root is REPORTED (edit_surface=<name>:<changed|unchanged>),
    # never judged — an executor's own worktree product is not an escape.
    # `before=`/`after=` stay the base root's pair (manifest[0]); the oracle's
    # agreement rule (R27-HIGH-01, amended) excludes the edit-surface root.
    judged = [m for m in manifest if m[0] != edit_surface]
    all_eq = all(b == a for _n, _p, b, a in judged)
    result = "clean" if all_eq else "dirty"
    roots_val = "; ".join("%s=%s|%s|%s" % m for m in manifest)
    base = manifest[0]
    rec = ("OWNERSHIP: escape-check ts=%s run=%s role=%s result=%s before=%s after=%s roots=\"%s\" leg=%s"
           % (ts, flags["--run"], flags["--role"], result, base[2], base[3], roots_val, leg))
    if edit_surface is not None:
        es = [m for m in manifest if m[0] == edit_surface][0]
        rec += " edit_surface=%s:%s" % (edit_surface, "changed" if es[2] != es[3] else "unchanged")
    if result == "dirty" and own_iso is not None:
        # v33.0 D4 (advisory attribution): only when EVERY changed judged root
        # is the checkout a LIVE foreign marker claims (base/external — never
        # the worktree), within 2x the liveness window; liveness OFF or no
        # --iso ⇒ unattributed (a `dirty` without attribution pauses in every
        # mode — the composer rule, STICKY §4.7 / SKILL Filesystem-escape).
        changed = [m[1] for m in judged if m[2] != m[3]]
        att = attribute_base_dirt(base[1], own_iso, liveness_min, changed)
        if att is not None:
            check_value_safety("attributed", att[0])
            rec += " attributed=%s attributed_age=%d" % (att[0], att[1])
    write_lines(sink, [rec])
    try:
        os.remove(state_path)  # consumed — exactly one record per pre/post pair
    except OSError:
        pass


PASS_ID_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]*\.p[1-9]\d*\Z")  # <phase-or-slice>.p<N> (D3)
PASS_KEYS = ("pass", "peer_round", "cap")
CAP_TRANSITION_GATE_KEYS = {"cap-raise", "peer-cap", "peer-cap-accept"}
INCONCLUSIVE_RESULT_RE = re.compile(r"(?i)(?<![A-Za-z])(inconclusive|incomplete)(?![A-Za-z])")


def check_pass_key_forms(kv, shape):
    """v33.0 D3 (Critical Constraint 16): the three per-pass keys are
    ALL-OR-NONE on `shape` — absence is the legal standalone/legacy shape,
    partial presence is the grammar error. Returns (pass, peer_round, cap)
    as (str, int, int) when all three ride, else None."""
    present = [k for k in PASS_KEYS if k in kv]
    if not present:
        return None
    if len(present) != len(PASS_KEYS):
        refuse("%s carries %s but not %s — pass= peer_round= cap= ride together or not at all (partial-pass-keys; absence is the standalone shape, Constraint 16)"
               % (shape, "/".join(present), "/".join(k for k in PASS_KEYS if k not in kv)))
    if not PASS_ID_RE.match(kv["pass"]):
        refuse("pass=%r is not an invocation-unique pass id <phase-or-slice>.p<N> (bad-pass; D3)" % kv["pass"][:60])
    _n = {}
    for k in ("peer_round", "cap"):
        _n[k] = parse_count(kv[k])  # R16 PR-MED-002: total admission — never a ValueError
        if _n[k] is None or _n[k] < 1:
            refuse("%s= must be a positive integer (bad-%s; D3)" % (k, k.replace("_", "-")))
    if _n["peer_round"] > _n["cap"]:
        refuse("peer_round=%s exceeds cap=%s — a pass never runs past its cap (peer-round-over-cap; D3)"
               % (kv["peer_round"], kv["cap"]))
    return kv["pass"], _n["peer_round"], _n["cap"]


def check_cap_transition_bundle(kv, shape):
    """v33.0 D3 (R2 PR-MED-003): a cap-transition record carries the TWO-key
    bundle pass=+cap= both (orchestrated) or neither (standalone/legacy),
    never peer_round=; residue= (D2) rides ONLY a cap-accept=close record
    and only with a RESIDUE_VALUES member. Returns (pass, cap) or None."""
    if "peer_round" in kv:
        refuse("%s never carries peer_round= — a cap transition is pass-scoped, not round-scoped (D3)" % shape)
    has_pass, has_cap = "pass" in kv, "cap" in kv
    if has_pass != has_cap:
        refuse("%s carries %s without %s — a cap transition's pass=/cap= bundle rides together or not at all (partial-pass-keys; D3 R2 PR-MED-003)"
               % (shape, "pass=" if has_pass else "cap=", "cap=" if has_pass else "pass="))
    if "residue" in kv:
        if kv.get("cap-accept") != "close":
            refuse("residue= rides ONLY a cap-accept=close record (the defer-residue verdict — D2)")
        if kv["residue"] not in RESIDUE_VALUES:
            refuse("residue= must be one of %s (bad-residue; D2)" % ", ".join(sorted(RESIDUE_VALUES)))
    if not has_pass:
        return None
    if not PASS_ID_RE.match(kv["pass"]):
        refuse("pass=%r is not an invocation-unique pass id <phase-or-slice>.p<N> (bad-pass; D3)" % kv["pass"][:60])
    _cap = parse_count(kv["cap"])  # R16 PR-MED-002: total admission
    if _cap is None or _cap < 1:
        refuse("cap= must be a positive integer (bad-cap; D3)")
    return kv["pass"], _cap


def _pass_records(lines, expected_run, pass_id):
    """v33.0 D3 — the pass's records in append order: keyed same-pass peer
    starts, every ROLE: end, and the same-pass KEYED cap transitions as
    (index, kind, recorded cap or None) with kind in auto-raise
    (`cap-raise=+1`), accept-close (`cap-accept=close`), operator-raise
    (`gate-disposition key=<cap key> choice=raise`), operator-other (any other
    choice on a cap key). Records of another run= are ignored."""
    # R14 class fix (PR-MED-001): every state-bearing record is admitted ONLY
    # when the shared emittable_record predicate passes — a start the writer
    # could not have emitted (over-cap, non-numeric, non-peer, partial keys),
    # a route-incoherent transition (mixed-route, both cap keys, a bad bundle),
    # or a malformed end never seeds, advances, counts, or closes anything
    # (the same skip the oracle's check_pass_sequencing applies via strictness).
    starts, ends, transitions = [], [], []
    for i, raw in enumerate(lines):
        if raw.startswith("ROLE: "):
            kv0, bare0 = parse_kv(raw[len("ROLE:"):].strip())
            if kv0.get("run") != expected_run or not bare0:
                continue
            if bare0[0] == "start":
                if kv0.get("pass") != pass_id or not all(k in kv0 for k in PASS_KEYS):
                    continue
                kv, _b, why = emittable_record(raw, "ROLE:start")
                if why is None:
                    starts.append((i, kv))
            elif bare0[0] == "end":
                kv, _b, why = emittable_record(raw, "ROLE:end")
                if why is None:
                    ends.append((i, kv))
        elif raw.startswith("OWNERSHIP:"):
            kv0, bare0 = parse_kv(raw[len("OWNERSHIP:"):])
            if not bare0 or kv0.get("run") != expected_run or kv0.get("pass") != pass_id:
                continue
            if bare0[0] not in ("auto-disposition", "gate-disposition"):
                continue
            kv, _b, why = emittable_record(raw, "OWNERSHIP:" + bare0[0])
            if why is not None:
                continue
            cap = parse_count(kv.get("cap", ""))  # R16: total — None on anything but an ASCII count
            if bare0[0] == "auto-disposition" and kv.get("cap-raise") == "+1":
                transitions.append((i, "auto-raise", cap))
            elif bare0[0] == "auto-disposition" and kv.get("cap-accept") == "close":
                transitions.append((i, "accept-close", cap))
            elif bare0[0] == "gate-disposition" and kv.get("key") in CAP_TRANSITION_GATE_KEYS:
                transitions.append((i, "operator-raise" if kv.get("choice") == "raise" else "operator-other", cap))
    return starts, ends, transitions


def transition_ok(kind, cap, budget):
    """R13 PR-MED-002 — D2's record contract per transition kind against the
    running budget: an automatic raise records exactly budget+1; an operator
    raise records a LARGER cap; an accept-close (or any other operator cap
    disposition) records the CURRENT budget. Returns (valid, new_budget,
    expected-description)."""
    if kind == "auto-raise":
        return cap == budget + 1, budget + 1, "cap=%d (the budget %d + 1)" % (budget + 1, budget)
    if kind == "operator-raise":
        valid = cap is not None and cap > budget
        return valid, (cap if valid else budget), "cap > %d (the current budget)" % budget
    return cap == budget, budget, "cap=%d (the current budget)" % budget


def pass_budget(starts, transitions):
    """R13 PR-MED-002 — the pass's recorded budget: the seed start's cap= plus
    every VALID ordered same-pass transition after it (transition_ok); an
    INVALID transition (a recorded cap disagreeing with its kind's expected
    result, or one before the seed) is NOT counted — the budget never moves on
    a lie. Returns (budget, invalid) or (None, []) when the pass has no seed."""
    if not starts:
        return None, []
    seed_i, seed = starts[0]
    budget = int(seed["cap"])
    invalid = []
    for ti, kind, cap in transitions:
        if ti < seed_i:
            invalid.append((ti, kind, cap, "before the pass's seed start"))
            continue
        valid, nb, exp = transition_ok(kind, cap, budget)
        if valid:
            budget = nb
        else:
            invalid.append((ti, kind, cap, exp))
    return budget, invalid


def cap_transition_check(source_path, expected_run, pass_id, kind, cap):
    """R13 PR-MED-002 — WRITER-side validation of a KEYED cap transition
    (the pass=+cap= bundle) against the pass's recorded budget in the prior
    log: the pass must have a seed start, and the recorded cap= must be its
    kind's expected result (transition_ok). Refuses otherwise, naming the
    expected value. Unkeyed standalone transitions never reach here."""
    try:
        lines = open(source_path, encoding="utf-8").read().splitlines()
    except (OSError, UnicodeDecodeError) as e:
        # R17 PR-MED-001: a REQUIRED prior-record source that cannot be read
        # OR decoded is the same controlled failure (exit 3, nothing written)
        # — a budget is never bound against a corrupt log.
        envfail("cannot read the prior-record source %s: %s" % (source_path, e))
    starts, _ends, transitions = _pass_records(lines, expected_run, pass_id)
    budget, _invalid = pass_budget(starts, transitions)
    if budget is None:
        refuse("a keyed cap transition for pass=%s precedes any keyed ROLE:start for that pass — a pass's budget is seeded by its first start (D3); emit the start first or drop the bundle for a standalone transition" % pass_id)
    valid, _nb, exp = transition_ok(kind, cap, budget)
    if not valid:
        refuse("pass=%s %s records cap=%d but the pass's recorded budget is %d — expected %s (D2 record contract; R13 PR-MED-002)"
               % (pass_id, kind, cap, budget, exp))


def pass_start_check(source_path, expected_run, pass_id, peer_round, cap):
    """v33.0 D3 — the per-pass cap counter, MECHANIZED on the enforced record
    (the single validation owner — Critical Constraint 4; never a second
    parser in the wrapper or the history checker). Reads the prior records
    of this run from `source_path` (the --log sink or the read-only
    --read-log) and validates a keyed `ROLE: start role=peer`:
      * no prior keyed start for this pass ⇒ the GRANDFATHER seed: any
        peer_round <= cap is accepted (a v33.0 composer resuming a v32.5-
        started run restarts the counter; never SPAWN_REFUSED);
      * else peer_round == previous same-pass start's peer_round + 1, with ONE
        admitted exception (R4 PR-MED-001, the inconclusive retry): the SAME
        peer_round is accepted when the previous activation is CLOSED by a
        `ROLE: end` whose result= names an inconclusive/incomplete outcome
        (word match: `inconclusive` | `incomplete`) — a same-round start over
        an OPEN activation, or after a completed round, refuses;
      * cap= is BOUND to the pass's recorded budget (R2 PR-MED-002): the seed
        cap (its first keyed start) + every ordered same-pass transition —
        an automatic `cap-raise=+1` auto-disposition (+1) or an operator
        `gate-disposition key=cap-raise|peer-cap choice=raise pass=<p>
        cap=<N+k>` (+k = its cap= minus the previous expected cap; counted
        ONCE — R5 PR-MED-001) — larger or smaller refuses; a transition
        recorded under ANOTHER pass= never counts.
    Records of another run= are ignored here (a probe log is per-run; the
    flush/retry paths own their fail-closed run checks)."""
    try:
        lines = open(source_path, encoding="utf-8").read().splitlines()
    except (OSError, UnicodeDecodeError) as e:
        # R17 PR-MED-001: an undecodable source is the unreadable-source
        # controlled failure — never a grandfather seed over a corrupt log.
        envfail("cannot read the prior-record source %s: %s" % (source_path, e))
    starts, ends, transitions = _pass_records(lines, expected_run, pass_id)
    if not starts:
        return  # grandfather seed — any peer_round <= cap (form-checked by the caller)
    prev_i, prev = starts[-1]
    prev_round = int(prev["peer_round"])
    if peer_round != prev_round + 1:
        if peer_round == prev_round:
            # the inconclusive-retry exception: the previous activation must
            # be CLOSED by an inconclusive/incomplete end.
            closing = None
            for ei, ekv in ends:
                if ei <= prev_i:
                    continue
                if prev.get("leg") and ekv.get("leg") not in (None, prev.get("leg")):
                    continue
                if ekv.get("role") not in (None, prev.get("role", "peer")):
                    continue
                closing = ekv
                break
            if closing is None:
                refuse("pass=%s peer_round=%d repeats the previous start's round over an OPEN activation (no closing ROLE: end) — the same round is legal only as the inconclusive retry (D3, R4 PR-MED-001)"
                       % (pass_id, peer_round))
            if not INCONCLUSIVE_RESULT_RE.search(closing.get("result", "")):
                refuse("pass=%s peer_round=%d repeats a COMPLETED round (the closing ROLE: end result=%r names no inconclusive/incomplete outcome) — rounds are consecutive per pass (D3)"
                       % (pass_id, peer_round, closing.get("result", "")[:60]))
        else:
            refuse("pass=%s peer_round=%d is not consecutive — the previous same-pass start was peer_round=%d (expected %d; D3)"
                   % (pass_id, peer_round, prev_round, prev_round + 1))
    # R13 PR-MED-002: the budget counts only VALID transitions (transition_ok)
    # — a forged/inconsistent transition never moves it, so a start at the
    # lie's value refuses and a start at the true budget is accepted.
    expected_cap, invalid = pass_budget(starts, transitions)
    if cap != expected_cap:
        refuse("pass=%s cap=%d does not equal the pass's recorded budget %d (seed cap=%s + %d valid same-pass transition(s); %d inconsistent transition(s) ignored) — a start binds to its OWN pass's records; a raise recorded under another pass never counts (D3, R2 PR-MED-002)"
               % (pass_id, cap, expected_cap, starts[0][1]["cap"], len(transitions) - len(invalid), len(invalid)))


def must_pause_fold(records, upto=None):
    """The ONE open-must-pause rule (the re-fire dedupe below AND the v34.0
    `away report`'s "Waiting for you" section — D5 uses exactly this rule):
    records in append order; for each (run=, key=) pair the newest
    `OWNERSHIP: must-pause` OWNER stays open until a later
    `OWNERSHIP: gate-disposition` for the SAME run key and key closes it.
    R14 class fix (PR-MED-002): an OWNER counts only when the shared
    emittable_record predicate passes — a forged/impossible-future/malformed
    must-pause record is never suppression evidence (fail toward FIRING), and
    it clears the pair's owner. A gate-disposition on the key closes the gate
    whatever its shape (closing is the firing direction — the fail-closed
    side here); an auto-disposition never closes one. `records` holds raw
    lines or (raw, location) tuples; `upto` (an aware datetime) skips records
    whose ts= parses to a later instant (the report's window end). Returns
    {(run, key): (owner kv, location)} for the OPEN pairs only."""
    owners = {}
    for item in records:
        raw, loc = item if isinstance(item, tuple) else (item, None)
        if not raw.startswith("OWNERSHIP:"):
            continue
        kv, bare = parse_kv(raw[len("OWNERSHIP:"):])
        if not bare or "run" not in kv or "key" not in kv:
            continue
        if upto is not None:
            _t = parse_iso(kv.get("ts"))
            if _t is not None and _t > upto:
                continue
        pair = (kv["run"], kv["key"])
        if bare[0] == "must-pause":
            okv, _b, why = emittable_record(raw, "OWNERSHIP:must-pause")
            owners[pair] = (okv, loc) if why is None else None
        elif bare[0] == "gate-disposition":
            owners[pair] = None  # the operator closed the gate — a later fire is a NEW gate
    return {p: o for p, o in owners.items() if o is not None}


def _prior_record_lines(log_path):
    """v34.1 D9/D10 — the --log sink read as a prior-record source. A log that
    does not exist yet holds no prior record ([] — the emission then creates
    it, as before); one that exists but cannot be read or decoded is an
    environment failure (exit 3, nothing written — the R17 PR-MED-001
    precedent). Read-then-append, unlocked, like every other reader here."""
    try:
        return open(log_path, encoding="utf-8").read().splitlines()
    except FileNotFoundError:
        return []
    except (OSError, UnicodeDecodeError) as e:
        envfail("cannot read the prior-record source %s: %s" % (log_path, e))


def closed_leg_end_ts(log_path, expected_run, role, leg):
    """v34.1 D9 — the oracle's duplicate-end class at write time. Among the
    prior `ROLE: start` / `ROLE: end` records emittable_record admits with
    this run=, role=, and leg=, the MOST RECENT decides: an end ⇒ the leg is
    closed (returns that end's ts=); a start, or no such record ⇒ None. So a
    reopened leg, another role's or another leg's end, and a first end are
    never refused, and an end the writer could not have emitted never blocks."""
    last = None
    for raw in _prior_record_lines(log_path):
        for verb in ("start", "end"):
            if not raw.startswith("ROLE: %s " % verb):
                continue
            kv, _b, why = emittable_record(raw, "ROLE:" + verb)
            if (why is None and kv.get("run") == expected_run
                    and kv.get("role") == role and kv.get("leg") == leg):
                last = (verb, kv.get("ts"))
    return last[1] if last is not None and last[0] == "end" else None


def recorded_commit_ts(log_path, commit_hash):
    """v34.1 D10 — the ts= of the first prior `OWNERSHIP: commit` record in
    this log that emittable_record admits and that carries hash=<commit_hash>,
    else None."""
    for raw in _prior_record_lines(log_path):
        if not raw.startswith("OWNERSHIP: commit "):
            continue
        kv, _b, why = emittable_record(raw, "OWNERSHIP:commit")
        if why is None and kv.get("hash") == commit_hash:
            return kv.get("ts")
    return None


def _print_pause_ask(key, epoch, state, paused, rec, options):
    """v34.1 D11 — the paste-ready ask: stdout NARRATION ONLY, never a record
    (no journal append, no new refusal, no exit-status change — the
    _idle_delivery_echo precedent). Five lines, fixed order; the three value
    lines are quoted so they read as data. Every value is the record's own
    (already field-checked, so newline-free); a character the stream cannot
    encode is written as a backslash escape. A print that fails (a closed
    stream, a full device) is swallowed — the pair and the notice have already
    happened — and stdout is pointed at the null device so the interpreter's
    exit-time flush cannot turn the failure into a nonzero exit."""
    block = "".join(l + "\n" for l in (
        "ASK key=%s epoch=%s notice=%s" % (key, epoch, state),
        'Paused: "%s"' % paused,
        ('Recommended: "%s"' % rec) if rec is not None else "Recommended: none recorded",
        ('Options: "%s"' % options) if options is not None else "Options: not recorded - state them in the ask",
        "The pause is recorded. Put this ask in chat now."))
    try:
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        sys.stdout.write(block.encode(enc, "backslashreplace").decode(enc))
        sys.stdout.flush()
    except Exception:
        try:
            _null = os.open(os.devnull, os.O_WRONLY)
            os.dup2(_null, sys.stdout.fileno())
            os.close(_null)
        except Exception:
            pass


def must_pause_open_owner_age(log_path, expected_run, key):
    """v33.0 D5 (PR-MED-005): the age in seconds of the NEWEST
    `OWNERSHIP: must-pause` owner for `key` in this run that has NO later
    `OWNERSHIP: gate-disposition` on the same key — i.e. the gate is still
    OPEN — or None when no open owner exists (never owned, or closed by a
    disposition). The owner's own ts= (K7 write time) is the age source; an
    unparseable ts= is treated as no-owner (fail toward firing — a notice
    is never suppressed on unreadable evidence)."""
    try:
        lines = open(log_path, encoding="utf-8").read().splitlines()
    except OSError as e:
        envfail("cannot read --log %s: %s" % (log_path, e))
    except UnicodeDecodeError as e:
        # R17 PR-MED-001: suppression evidence that cannot be decoded is NO
        # owner — the pair FIRES (the documented direction: a notice is never
        # suppressed on unreadable evidence). Diagnostic on stderr only.
        sys.stderr.write("WARN: --log %s is not valid UTF-8 (%s) — no usable must-pause owner evidence; the pair fires\n" % (log_path, e))
        return None
    owner = must_pause_fold(lines).get((expected_run, key))
    owner_ts = owner[0].get("ts") if owner is not None else None
    if owner_ts is None:
        return None
    t = parse_iso(owner_ts)
    if t is None or future_instant(t):
        return None  # unreadable or impossible clock ⇒ no owner ⇒ the pair fires
    age = (datetime.datetime.now().astimezone() - t).total_seconds()
    return int(age) if age >= 0 else 0


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
    (pending, is_retry, retry_attempts_by_epoch, member_classes) — the fourth
    element (v33.0 D5) maps each pending key to the class= on its newest
    queued record. PR-MED-003 (round 7): retry
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
    member_cls = {}    # key -> the class= on its newest queued record (v33.0 D5 batch tier)
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
            member_cls[key] = kv.get("class")
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
    # v33.0 D5: the pending members' class= (from each member's newest queued
    # record) — the flush synthesizes the batch notice's tier from it.
    member_classes = {k: member_cls.get(k) for k, _ in pending}
    return pending, is_retry, retry_attempts_by_epoch, member_classes


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
    pending, is_retry, retry_attempts_by_epoch, member_classes = derive_pending(log_path, flags["--run"])
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
    def flush_line(state, key, detail=None):
        parts = [state, fmt_kv("ts", ts), fmt_kv("run", flags["--run"]),
                 fmt_kv("key", key), fmt_kv("epoch", epoch),
                 fmt_kv("mode", "queued"), fmt_kv("batch", batch)]
        if detail is not None:
            parts.append(fmt_kv("detail", detail))
        return "NOTIFY: " + " ".join(parts)
    for key, _qep in pending:
        check_value_safety("key", key)
    summary = "flushing %d queued notice(s): %s" % (len(pending), ", ".join(k for k, _ in pending))
    # v33.0 D5: the batch notice's TIER is the members' highest class (an
    # operator-needed member — impossible today, since must-pause never queues,
    # but the synthesis stays truthful — lifts the whole batch to critical).
    _batch_cls = next((c for c in member_classes.values() if c in NOTICE_CRITICAL_CLASSES), "auto-disposition")
    # v33.0 D5 (R4 PR-MED-004): LOOP_NOTIFY=action-only suppresses ONLY the
    # batch DESKTOP notice — the queue still SETTLES truthfully: per-member
    # batch-flushed records carry detail="policy-suppressed notify=action-only",
    # a suppressed settlement is never a delivery or a successful retry (no
    # `retried` record), and the members leave the pending set.
    if notify_policy() == "action-only":
        write_lines(sink, [flush_line("batch-flushed", key, "policy-suppressed notify=action-only")
                           for key, _qep in pending])
        return
    if not fire_notice(flags["--run"], summary, _batch_cls):
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
# v33.8 (plan-run-hygiene D1-D3): the journal-artifact-mismatch reconcile also
# admits any journal state outside _RECONCILE_EXCLUDED_STATES (terminal,
# `merged`, hand-written, empty, or missing) when its worktree and branch are
# CONFIRMED gone — record-only, same cell / verdict / detail.
RUN_CLOSE_OUTCOMES = {"retained-green", "merged", "paused", "crashed",
                      "merge-failed", "complete", "reconcile", "group-merged"}
# v40.0 Phase 1 (plan-one-run-per-plan D2/D10): `group-merged` is the in-run
# close of ONE non-final release group — it keeps the journal `active`, so it
# has NO entry in _OUTCOME_STATE or _OUTCOME_TERMINAL (its branch in
# cmd_run_close returns before the `active` fall-through indexes them).
# journal state= value written per requested outcome (worktree mode)
_OUTCOME_STATE = {"retained-green": "retained-green", "paused": "paused",
                  "crashed": "crashed/recovery-needed", "merge-failed": "merge-failed"}
_TERMINAL_STATES = {"cleaned", "retained-green", "paused",
                    "crashed/recovery-needed", "merge-failed"}
# terminal journal state that satisfies each outcome idempotently
_OUTCOME_TERMINAL = {"retained-green": "retained-green", "merged": "cleaned",
                     "paused": "paused", "crashed": "crashed/recovery-needed",
                     "merge-failed": "merge-failed", "reconcile": "cleaned"}
# v33.8 (D1): the journal states the record-only reconcile admission never
# takes — a run still being created or mid-merge (recovery owns those), an
# already-cleaned record (today's already-closed path), and `active` (today's
# byte-unchanged reconcile path in the active cell).
_RECONCILE_EXCLUDED_STATES = frozenset({"intent", "created", "merging", "cleaned", "active"})
# v33.8 (D3): the `prior-state=` token — journal text never reaches the
# journal unvalidated; anything else is recorded as `unrecognized`.
_PRIOR_STATE_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9/_-]{0,39}\Z")
# v33.8 (Step H r23 PR-LOW-001): the branch names whose exact ref survives
# _rc_git's `.strip()` and `str.splitlines()` unchanged — printable ASCII, no
# whitespace. Any other name is never confirmed absent through that output.
_RC_LOSSLESS_BRANCH_RE = re.compile(r"\A[!-~]+\Z")


def _rc_state_line_rewritable(raw):
    """v33.8 (D1): True when _rc_rewrite_journal will replace the line the
    READER takes as the state — the first line whose key reads `state` (the
    reader's rule: has `=`, no leading `#`, key stripped) starts with `state=`
    at column 0 — or when the journal has no state line at all (the rewrite
    appends one). An indented `  state=x` or a `state = x` line is seen by the
    reader and missed by the rewriter, so it is False (fall through)."""
    for line in raw:
        if "=" not in line or line.startswith("#"):
            continue
        if line.split("=", 1)[0].strip() == "state":
            return line.startswith("state=")
    return True


def _rc_artifacts_confirmed_gone(base_real, worktree, branch):
    """v33.8 (D2): True ONLY on confirmed absence of BOTH artifacts — "could
    not check" is never absence. The journal must record a non-empty branch=
    and a non-empty ABSOLUTE worktree= (never inferred from a missing key or
    a relative path resolved against the caller's cwd); `lstat` of the
    worktree path must answer "not found" (ENOENT — anything present at the
    path, a dangling symlink included, is not absence; a permission / I/O /
    other error is indeterminate); and an exact-ref `for-each-ref` that git
    COMPLETES (exit 0) must not list `refs/heads/<branch>` (a git error, a
    timeout, or a launch failure is indeterminate — _rc_git's shared failure
    code is never read as absence here). The existing wt_exists / br_exists
    reads are untouched (Constraint 2)."""
    if not branch or not worktree or not os.path.isabs(worktree):
        return False
    if not _RC_LOSSLESS_BRANCH_RE.match(branch):
        # Unicode whitespace at the end, or a Unicode line boundary inside,
        # would be lost by the shared output normalization and a PRESENT
        # branch could read as absent — indeterminate, never absence.
        return False
    try:
        os.lstat(worktree)
        return False
    except FileNotFoundError:
        pass
    except (OSError, ValueError):
        return False
    ref = "refs/heads/%s" % branch
    rc, out = _rc_git(base_real, "for-each-ref", "--format=%(refname)", ref)
    if rc != 0:
        return False
    return ref not in out.splitlines()


def _rc_journal_lossless(path, jraw=None):
    """v33.8 (Step H r24 PR-LOW-001): True only when the journal's raw text has
    no line terminator but LF — so the shared reader's `splitlines()` (and
    `open()`'s universal-newline translation) cut no recorded value short and
    `_rc_rewrite_journal`'s LF re-join preserves every other line's bytes.
    Read in BINARY, strict UTF-8; an unreadable or undecodable journal, or any
    other LINE_TERMINATORS member (CR, VT, FF, FS/GS/RS, NEL, U+2028, U+2029),
    is False — the new reconcile admission then falls through, never confirms.
    v33.8 (Step H r25 PR-LOW-001): given `jraw` (the lines the admission parsed
    and will rewrite), the certified bytes must ALSO split into exactly those
    lines, binding the certificate to the snapshot every admitted value came
    from; a journal replaced between the two reads is False."""
    try:
        with open(path, "rb") as f:
            text = f.read().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    if any(ch in LINE_TERMINATORS for ch in text if ch != "\n"):
        return False
    if jraw is None:
        return True
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines == list(jraw)


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
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
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
        r = subprocess.run([_git_bin(), "-C", base] + list(args),
                           capture_output=True, text=True, timeout=60, env=_git_env())
    except Exception as e:
        return 1, "git failed: %s" % e
    return r.returncode, (r.stdout or "").strip()


def _rc_report(flags, sink, iso, mode, cell, verdict, detail=None, merge_commit=None,
               group=None, ff=None):
    """Emit the ONE run-close report record; returns the verdict for exit
    mapping. detail values are fixed tool-authored strings (value-safe).
    v33.2 (/close-run): `merge_commit=<full sha>` is the ONE additive key —
    emitted before `detail=` on the --merge-commit path only, once the sha
    has resolved (presence-only in the oracle's run-close matrix).
    v40.0 Phase 1 (D2/D3): the group close's two additive keys — `group=<tag>`
    (before merge_commit=, on the group-merge cell) and `ff=<full sha>` (after
    it, on the group-ff cell) — the oracle validates both by form."""
    ts = now_iso()
    rec = ("OWNERSHIP: run-close ts=%s run=%s role=%s iso=%s mode=%s cell=%s verdict=%s"
           % (ts, flags["--run"], flags["--role"], iso, mode, cell, verdict))
    if group is not None:
        check_value_safety("group", group)
        rec += " group=%s" % group
    if merge_commit is not None:
        check_value_safety("merge_commit", merge_commit)
        rec += " merge_commit=%s" % merge_commit
    if ff is not None:
        check_value_safety("ff", ff)
        rec += " ff=%s" % ff
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


LOOP_STOP_RECIPE = "python3 scripts/loop-watchdog.py stop --iso %s"


def journal_log_root(jkv, default):
    """THE ONE READING of a journal's `log_root=` (round 72 PR-MED-039) — the
    run listing's (watch_runs) and the close's live-role guard's alike, so no
    reader that decides where a run's legs are has a predicate of its own.
    `jkv` is the parsed journal (_rc_parse_kv_lines: the FIRST `log_root=`
    line is the one read), `default` is `<base>/.cursor/loops/<iso>`. Returns
    `(folder, how)`:
      `named`     the key is there and usable — its value passes the writer's
                  value check, is an ABSOLUTE path, and is spelled as the
                  host's path rules accept. The folder is that path, trailing
                  slashes dropped — whether or not anything exists there: a
                  path that is missing, or is a file, is still the folder the
                  journal NAMES, and it holds no leg.
      `default`   the key is NOT there — the documented fallback (a journal
                  from before the key, a hand-written one). The folder is
                  `default`.
      `unusable`  the key IS there and cannot be used: an empty value, one
                  that fails the value check, a path that is not absolute, a
                  spelling the host refuses. The journal has said where the
                  run's legs are in words the reader cannot follow, so the
                  folder is NOT established. `default` is handed back for a
                  reader that still looks there best-effort, never as the
                  run's folder.
    Omission and an unusable value are two things: the first keeps the
    fallback, the second never becomes it. A relative value is resolved
    against nothing — not the base, not the caller's directory."""
    if "log_root" not in jkv:
        return default, "default"
    value = jkv["log_root"]
    if not value or reason_of(check_value_safety, "log_root", value) is not None or not os.path.isabs(value):
        return default, "unusable"
    root = value.rstrip("/") or "/"
    if reason_of(canon_path, root) is not None:
        # a spelling this host's path rules refuse (a Windows host: a UNC or a `/`-rooted path) — round 66 LOW-004
        return default, "unusable"
    return root, "named"


def _rc_live_role_guard(flags, sink, iso, mode, cell, base_real, jkv, merge_commit=None):
    """v48.0 (plan-loop-autonomy-group-2 T6.4 / D17): the close's live-role
    guard — called by every cell that tears down, BEFORE its first write.
    The role-liveness reader (run_legs) is asked for every leg the run's log
    root holds evidence of — the folder the journal's `log_root=` NAMES, or
    `<base>/.cursor/loops/<iso>` when the journal has no such key (and for
    the pre-journal cell, which has no journal): journal_log_root, the one
    reading the run listing uses too. A `live` leg refuses, and `--attest
    owner-dead` does not override it: a process of the role is running. An
    `unknown` leg refuses too — the evidence cannot tie a process to the
    role — and there the operator's `--attest owner-dead` is the ONE
    override. Every leg `over`, or no leg evidence at all, admits.
    A `log_root=` that is THERE AND CANNOT BE USED refuses as an `unknown`
    leg does (round 72 PR-MED-039): empty, unsafe, or not an absolute path,
    it leaves the folder this run's legs are in unestablished — the default
    folder is still read (a `live` leg there refuses as ever), but finding
    no leg in a folder nobody named rules no role out, so the teardown waits
    for the operator's `--attest owner-dead`. Before, such a journal fell
    back to the default folder and the close tore the run down beside roles
    it had not looked for. The refusal is the calling cell's own refused
    form (no new cell token); its detail names the first such leg, the
    reader's word, the recorded pids and the stop command — or the unusable
    `log_root=`. Returns only when admitted."""
    default = os.path.join(base_real, ".cursor", "loops", iso)
    log_root, how = (default, "default") if jkv is None else journal_log_root(jkv, default)
    attested = flags.get("--attest") == "owner-dead"
    legs = run_legs(log_root)
    live = [l for l in legs if l["word"] == "live"]
    unknown = [l for l in legs if l["word"] == "unknown"]
    blocking = live or ([] if attested else unknown)
    if not blocking and how == "unusable" and not attested:
        detail = ("the journal's log_root= is there and is not a usable absolute path — the folder this run's legs are in is not established, so "
                  "no role was ruled out; nothing torn down; stop the run's roles: %s — or, when its roles are known to be dead, re-run with "
                  "--attest owner-dead (the one override)" % (LOOP_STOP_RECIPE % iso))
        _rc_finish(_rc_report(flags, sink, iso, mode, cell, "refused", detail, merge_commit=merge_commit))
    if not blocking:
        return
    first = blocking[0]
    leg = first["leg"] if LEG_RE.match(first["leg"]) else "<unprintable>"
    stop = LOOP_STOP_RECIPE % iso
    more = "" if len(blocking) == 1 else "; %d legs read %s" % (len(blocking), first["word"])
    if live:
        detail = ("leg %s reads live (%s)%s — a role of this run is still running; nothing torn down; stop it first: %s (--attest owner-dead does not override a live leg)"
                  % (leg, first["pids"], more, stop))
    else:
        detail = ("leg %s reads unknown (%s)%s — the evidence cannot tie a process to the role; nothing torn down; stop the run's roles: %s — or, when the role is known to be dead, re-run with --attest owner-dead (the one override)"
                  % (leg, first["pids"], more, stop))
    _rc_finish(_rc_report(flags, sink, iso, mode, cell, "refused", detail, merge_commit=merge_commit))


def _rc_dispose_marker(marker_path):
    """`-active` -> `.complete-<ts>` (verified close only); idempotent."""
    if not os.path.exists(marker_path):
        return
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        os.replace(marker_path, "%s.complete-%s" % (marker_path, stamp))
    except OSError as e:
        envfail("cannot disposition marker %s: %s" % (marker_path, e))


_RC_HANDOFF_HEADING = re.compile(r"## Current State / Handoff Note[ \t]*\Z")
_RC_SECTION_END = re.compile(r" {0,3}#{1,2}(?:[ \t]|\Z)")
_RC_FENCE_OPEN = re.compile(r" {0,3}(`{3,}|~{3,})")
_RC_RETRO_POINTER = re.compile(r"(?:- )?Retro report:[ \t]*\S")


def _rc_has_retro_pointer(text):
    """True when the plan's `## Current State / Handoff Note` section holds a
    `/retro` pointer LINE — `Retro report: <path>` at column 0, optionally as
    a `- ` bullet, with a non-empty path — outside fenced code. A prose
    mention elsewhere in the plan (Key Findings, Design Decisions, a quoted
    example in a fence) is not the pointer. The named report is NOT required
    to exist: it is gitignored and machine-local (and a `persist=on` close
    re-points it at a relative tracked `docs/retros/` copy)."""
    in_section = False
    fence = None  # (char, length) of the open fence, else None
    for line in text.splitlines():
        if fence is not None:
            m = re.match(r" {0,3}(%s{%d,})[ \t]*\Z" % (re.escape(fence[0]), fence[1]), line)
            if m:
                fence = None
            continue
        m = _RC_FENCE_OPEN.match(line)
        if m and not (m.group(1)[0] == "`" and "`" in line[m.end():]):
            fence = (m.group(1)[0], len(m.group(1)))
            continue
        if _RC_HANDOFF_HEADING.match(line):
            in_section = True
            continue
        if _RC_SECTION_END.match(line):
            in_section = False
            continue
        if in_section and _RC_RETRO_POINTER.match(line):
            return True
    return False


def _rc_retro_pointer_gap(flags):
    """Green-close obligation: the plan must carry a `Retro report:` pointer
    line in its `Current State / Handoff Note` (see _rc_has_retro_pointer).
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
    except (OSError, UnicodeDecodeError):
        return "plan-unreadable"
    if not _rc_has_retro_pointer(text):
        return "retro-pointer-missing"
    return None


# ---- v33.2 (/close-run, plan-close-run D10/D11/D17/D19): the squash-aware
# merged close. `run-close --outcome merged --merge-commit <sha>` is an ENTRY
# PATH into the EXISTING verified-merge cell (Critical Constraint 1/2: one
# destructive cell, no new cell/verdict/subcommand): it verifies the sha
# against the fetched base BEFORE any write, records `merged="<ts> <sha>"`,
# and lets the cell tear down with `branch -D` (the squash verdict replaces
# the ancestry leg — `-d` refuses a squash-merged branch). Every refusal
# below is report-only with the journal byte-identical.
_MERGE_COMMIT_RE = re.compile(r"\A[0-9a-fA-F]{7,40}\Z")
_FULL_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_MERGE_TREE_MIN_GIT = (2, 38)  # `git merge-tree --write-tree`


def _rc_recorded_merge_sha(jkv):
    """The sha an existing `merged=` journal line records, if any: a
    `commit=<sha>` token when present (the by-hand shape `merged=<ts>
    commit=<short> note="..."` this repo's older journals carry), else the
    LAST whitespace token when it is 7-40 hex (the helper's own `<ts> <sha>`
    shape). Prose words inside a note= are never scanned. Used ONLY to refuse
    a re-entry whose supplied sha disagrees (D10 `merge-commit disagrees with
    journal`) — never as merge evidence; that is the git legs' job."""
    val = jkv.get("merged")
    if not val:
        return None
    toks = val.split()
    for tok in toks:
        if tok.startswith("commit=") and _MERGE_COMMIT_RE.match(tok[len("commit="):]):
            return tok[len("commit="):].lower()
    if toks and _MERGE_COMMIT_RE.match(toks[-1]):
        return toks[-1].lower()
    return None


def _rc_base_ref(base_real, jkv):
    """D10/D19 base binding: `refs/remotes/origin/<base_branch>` whenever that
    fetched ref exists (a diverged local base never admits a close on its
    own); only when no remote ref exists the local `refs/heads/<base_branch>`;
    `HEAD` when the journal predates `base_branch=`."""
    bb = jkv.get("base_branch")
    if not bb:
        return "HEAD"
    remote = "refs/remotes/origin/%s" % bb
    rc, _ = _rc_git(base_real, "rev-parse", "--verify", "--quiet", remote)
    if rc == 0:
        return remote
    return "refs/heads/%s" % bb


def _rc_resolve_merge_commit(base_real, jkv, merge_commit):
    """v46.4 (plan-loop-field-review-fixes D8 a) — resolve `--merge-commit` on
    the base checkout, for the two `merge-commit not found` sites: returns
    (rc, full sha) as the `rev-parse --verify --quiet <sha>^{commit}` they ran
    before. When that first resolve fails and the journal holds a usable
    `base_branch=` (the fast-forward leg's test), ONE `git fetch --quiet origin
    refs/heads/<base_branch>` runs on the base checkout and the sha is resolved
    once more — a merge commit that exists only on the remote (the base has
    not fetched since the merge) is found; one that is nowhere is refused as
    before. The fetch's own exit is not read: the second resolve is the
    evidence. No usable base_branch= means no fetch target and no fetch."""
    spec = "%s^{commit}" % merge_commit
    rc, full = _rc_git(base_real, "rev-parse", "--verify", "--quiet", spec)
    if rc != 0 or not _FULL_SHA_RE.match(full):
        bb = jkv.get("base_branch")
        if bb and _RC_LOSSLESS_BRANCH_RE.match(bb):
            _rc_git(base_real, "fetch", "--quiet", "origin", "refs/heads/%s" % bb)
            rc, full = _rc_git(base_real, "rev-parse", "--verify", "--quiet", spec)
    return rc, full


def _rc_git_supports_merge_tree(base_real):
    """git >= 2.38 has `merge-tree --write-tree`; parsed from `git --version`
    under the base checkout. An unparseable version fails TOWARD the
    tree-equality fallback (which refuses more, never less)."""
    rc, out = _rc_git(base_real, "--version")
    m = re.match(r"git version (\d+)\.(\d+)", out) if rc == 0 else None
    if not m:
        return False
    return (int(m.group(1)), int(m.group(2))) >= _MERGE_TREE_MIN_GIT


def _rc_d10_tip_covered(base_real, full, tip):
    """D10 leg 2 — the squash predicate, reached only when the ancestry fast
    path (checked by the caller) failed: `git merge-tree --write-tree <sha>^1
    <tip>` must exit 0 with ONE 40-hex line equal to `<sha>^{tree}` (true for
    an unmoved AND a moved base; a tip that continued past the merge, or a
    conflict (rc 1), fails closed). Below git 2.38: plain `<sha>^{tree} ==
    <tip>^{tree}` (refuses a moved-base squash — the documented fallback).
    Returns None when covered, else the pinned refusal detail."""
    rc, mtree = _rc_git(base_real, "rev-parse", "--verify", "--quiet", "%s^{tree}" % full)
    if rc != 0 or not _FULL_SHA_RE.match(mtree):
        return "tip not covered by merge-commit"
    if _rc_git_supports_merge_tree(base_real):
        rc, out = _rc_git(base_real, "merge-tree", "--write-tree", "%s^1" % full, tip)
        lines = out.splitlines()
        if rc != 0 or len(lines) != 1 or lines[0] != mtree:
            return "tip not covered by merge-commit"
        return None
    rc, ttree = _rc_git(base_real, "rev-parse", "--verify", "--quiet", "%s^{tree}" % tip)
    if rc != 0 or ttree != mtree:
        return "merge-tree unavailable (git < 2.38) and tree mismatch"
    return None


def _rc_identity_bind(flags, sink, iso, mode, base_real, branch, worktree, wt_exists,
                      merge_commit=None):
    """The destructive cell's identity checks (a) + (b) (r25 PR-HIGH-022) —
    ONE owner, shared by the cell and the v33.2 --merge-commit admission
    block (which runs them BEFORE any write; the cell re-runs them right
    before it destroys anything). Refuses via _rc_finish on any mismatch;
    returns wt_registered."""
    # (a) The journal must name both artifacts.
    if not branch or not worktree:
        _rc_finish(_rc_report(flags, sink, iso, mode, "identity-mismatch", "refused",
                              "journal names no branch or no worktree — the destructive cell requires the full recorded identity",
                              merge_commit=merge_commit))
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
                              "recorded worktree directory exists but is not a registered worktree of this base — never removed",
                              merge_commit=merge_commit))
    if wt_registered and wt_ref != "refs/heads/%s" % branch:
        _rc_finish(_rc_report(flags, sink, iso, mode, "identity-mismatch", "refused",
                              "registered worktree is not checked out on the recorded run branch (detached or wrong branch) — never removed",
                              merge_commit=merge_commit))
    return wt_registered


# ---- v40.0 Phase 1 (plan-one-run-per-plan D2/D3/D5/D10; T1.1): the GROUP close ----
# `run-close --run stage-<N> --outcome group-merged --merge-commit <sha>` closes
# ONE non-final release group of a LIVE run inside the run: the v33.2 admission
# legs re-used on an `active` journal — its live marker expected, not read;
# the state is the liveness claim (no --attest — the run is live by design) —
# the squash path REPLACED by the merge-parent binding
# (the merge commit has exactly two parents and its second parent IS the
# run-branch tip, so a squash, a rebase, a fast-forward hand merge, a tip
# passed as its own merge commit, and a merge-forward tip all fail it — the
# run branch continues as the next group's pull-request head), the first write
# ONE appended journal key per group (`merged_stage_<N>`) instead of `merged=`,
# the state kept `active`, and NO teardown. The group's identity is `--run
# stage-<N>` (the record's run=), looked up in the journal's composer-written
# `groups=` key; the tag is that entry's label. Then the fast-forward leg (D3)
# moves the base checkout and the worktree to ONE sha — the fetched
# `origin/<base-branch>` — and records it as `ff_stage_<N>` with a `group-ff`
# record. Every refusal before the first write leaves the journal
# byte-identical; a replay converges (verdict=already-closed; the fast-forward
# leg alone when its key is absent).
_GROUPS_ENTRY_RE = re.compile(r"\Astage-(\d+):([A-Za-z0-9][A-Za-z0-9._-]*)\Z")


def _rc_groups(jkv):
    """The journal's `groups=` key — `stage-<N>:<tag>[,stage-<N>:<tag>…]`
    (each group's LAST stage with its tag, in plan order; a tag may repeat)
    — as an ordered list of (stage number, tag). None when the key is absent.
    A malformed or non-increasing value REFUSES (exit 2, nothing written):
    journal text never reaches a record unvalidated, and the helper never
    guesses a group identity."""
    val = jkv.get("groups")
    if val is None:
        return None
    out = []
    for tok in val.split(","):
        m = _GROUPS_ENTRY_RE.match(tok.strip())
        if not m:
            refuse("journal groups=%r is malformed — expected stage-<N>:<tag>[,stage-<N>:<tag>...] (each group's last stage with its tag, in plan order); fix the journal, never guess" % val[:80])
        n = int(m.group(1))
        if out and n <= out[-1][0]:
            refuse("journal groups=%r is not strictly increasing by stage — fix the journal, never guess" % val[:80])
        out.append((n, m.group(2)))
    return out


def _rc_group_ff(flags, sink, iso, mode, base_real, journal_path, worktree, branch, fkey, rebase=None):
    """D3 — the fast-forward leg, the last leg of `--outcome group-merged`
    (and the whole of a replay whose group key is present and `ff_stage_<N>`
    absent). FIRST the identity binding at the moment of mutation (the
    verified-merge cell's rule, r25 PR-HIGH-022): the recorded worktree must
    exist and be a REGISTERED worktree of this base checked out on the run
    branch (_rc_identity_bind — the identity-mismatch cell on a mismatch; an
    absent or unregistered directory is `cell=group-ff verdict=refused
    detail=worktree-absent`) — on the replay path this is the ONLY bind, so a
    tampered or empty `worktree=` never aims `merge --ff-only` at an
    unverified directory. Then EVERY precondition of BOTH checkouts, settled
    before the fetch and before either merge (round 14 PR-MED-001): the base
    on `<base-branch>` (the worktree's branch is the identity bind's), and on
    each of the base and the worktree no merge / rebase / cherry-pick in
    progress (`MERGE_HEAD` / `REBASE_HEAD` / `CHERRY_PICK_HEAD` read under
    that checkout's own git dir) and no uncommitted TRACKED change (`status
    --porcelain --untracked-files=no` empty — untracked files are not a
    guard; today's /close-run Flow 1 step 6 hand step, applied to both).
    Then ONE target — `git fetch origin refs/heads/<base-branch>`, the sha of
    `refs/remotes/origin/<base-branch>` read once — and the DIRECTION check
    (round 14 PR-HIGH-001): each checkout's HEAD must be an ancestor-or-equal
    of the target BEFORE either merge (`--ff-only` exits 0 as "Already up to
    date" on a checkout AHEAD of the target without moving it, so exit status
    alone is not evidence; an ahead or diverged side refuses with NOTHING
    moved). Then `merge --ff-only <target>` on the base checkout and on the
    bound worktree (the run branch, so it becomes the merged base and the next
    group's commits diff cleanly), each followed by a `rev-parse HEAD` that
    must EQUAL the target — the completion evidence — so both checkouts hold
    the SAME sha, other runs' merged work included. Success appends
    `ff_stage_<N>="<ts> <sha>"` (state stays `active`) and writes
    `cell=group-ff verdict=complete ff=<sha>`; any other failure writes
    `cell=group-ff verdict=refused detail=<cause>` (the side and git's words
    on stderr) and exits 3 — a park, never a rebase, reset, or switch. The
    cause (v46.4 D8 b): `checkout-not-ready` for a precondition that failed
    before the fetch (no usable `base_branch=`, the base off its branch, an
    operation in progress, an uncommitted tracked change), `fetch-failed` for
    a failed fetch or a remote ref that did not resolve after it, and
    `base-not-fast-forwardable` for everything after the target is known — a
    HEAD that does not resolve or is not an ancestor of it, a failed `merge
    --ff-only`, a side that does not hold it afterwards. The base ff is
    idempotent (`--ff-only` onto its own sha is a no-op), so a replay after a
    worktree-side failure completes the leg.
    v44.0 (D4): `rebase` = (grant number, config_hash, the group's merge
    commit) when the composer passed `--grant`/`--away-check` — after BOTH
    sides' completion check and BEFORE the `ff_stage_<N>` rewrite the leg
    writes the re-baseline record (_rc_rebaseline; a refused fast-forward
    never writes one, and a failed write leaves the key absent so the replay
    re-enters here and writes again — the existence check keeps it to ONE);
    its stderr note prints after the report record."""
    cell = "group-ff"

    def refused(why, ff=None, detail="base-not-fast-forwardable"):
        sys.stderr.write("group-ff refused: %s\n" % why)
        _rc_finish(_rc_report(flags, sink, iso, mode, cell, "refused", detail, ff=ff))

    wt_exists = bool(worktree) and os.path.isdir(worktree)
    wt_registered = _rc_identity_bind(flags, sink, iso, mode, base_real, branch, worktree, wt_exists)
    if not wt_exists or not wt_registered:
        refused("the recorded worktree %s is absent or not a registered worktree of this base — the fast-forward leg mutates it, so nothing runs"
                % (worktree or "(none)"), detail="worktree-absent")
    jkv, jraw = _rc_read_kv_file(journal_path)
    bb = jkv.get("base_branch")
    # v46.4 (D8 b): the record names the real cause — a precondition that
    # failed before the fetch is `checkout-not-ready`, a failed fetch or an
    # unresolved remote ref `fetch-failed`; `base-not-fast-forwardable` (the
    # default) stays for every refusal after the target is known (the
    # docstring lists them). stderr, exit 3 and the park are unchanged.
    if not bb or not _RC_LOSSLESS_BRANCH_RE.match(bb):
        refused("the journal records no usable base_branch= — no fetch target", detail="checkout-not-ready")
    rc, head = _rc_git(base_real, "symbolic-ref", "--quiet", "--short", "HEAD")
    if rc != 0 or head != bb:
        refused("the base checkout is not on %s (HEAD %s)" % (bb, head or "detached"), detail="checkout-not-ready")
    sides = (("base", base_real), ("worktree", worktree))
    # round 14 PR-MED-001: every precondition of BOTH checkouts before the
    # fetch and before either merge — a known precondition never fails after
    # one side has already moved.
    for side, cwd in sides:
        for ref in ("MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD"):
            rc, _ = _rc_git(cwd, "rev-parse", "--verify", "--quiet", ref)
            if rc == 0:
                refused("%s exists — an operation is in progress on the %s checkout" % (ref, side), detail="checkout-not-ready")
        rc, status = _rc_git(cwd, "status", "--porcelain", "--untracked-files=no")
        if rc != 0 or status:
            refused("the %s checkout has uncommitted tracked changes (git status --porcelain --untracked-files=no is not empty)" % side,
                    detail="checkout-not-ready")
    rc, _ = _rc_git(base_real, "fetch", "--quiet", "origin", "refs/heads/%s" % bb)
    if rc != 0:
        refused("git fetch origin refs/heads/%s failed on the base checkout" % bb, detail="fetch-failed")
    rc, target = _rc_git(base_real, "rev-parse", "--verify", "--quiet", "refs/remotes/origin/%s" % bb)
    if rc != 0 or not _FULL_SHA_RE.match(target):
        refused("refs/remotes/origin/%s did not resolve after the fetch" % bb, detail="fetch-failed")
    # round 14 PR-HIGH-001: the DIRECTION check on both sides BEFORE either
    # merge — `--ff-only` exits 0 ("Already up to date") on a checkout AHEAD
    # of the target without moving it, so exit status alone is no evidence;
    # equal is admitted (the replay after the base already advanced).
    for side, cwd in sides:
        rc, head_sha = _rc_git(cwd, "rev-parse", "--verify", "--quiet", "HEAD")
        if rc != 0 or not _FULL_SHA_RE.match(head_sha):
            refused("the %s checkout's HEAD did not resolve" % side, ff=target)
        rc, _ = _rc_git(cwd, "merge-base", "--is-ancestor", head_sha, target)
        if rc != 0:
            refused("the %s checkout's HEAD %s is not an ancestor of %s (ahead of, or diverged from, the fetched base) — nothing moved"
                    % (side, head_sha[:12], target), ff=target)
    for side, cwd in sides:
        try:
            r = subprocess.run([_git_bin(), "-C", cwd, "merge", "--ff-only", target],
                               capture_output=True, text=True, timeout=120, env=_git_env())
            m_rc, m_err = r.returncode, (r.stderr or "").strip()[:400]
        except Exception as e:
            m_rc, m_err = 1, "merge --ff-only did not complete: %s" % e
        if m_rc != 0:
            refused("the %s side refused `merge --ff-only %s`: %s" % (side, target, m_err), ff=target)
        # the completion evidence: the checkout now holds the target
        rc, head_sha = _rc_git(cwd, "rev-parse", "--verify", "--quiet", "HEAD")
        if rc != 0 or head_sha != target:
            refused("the %s side reported success but its HEAD is %s, not %s" % (side, head_sha[:12] or "(unresolved)", target), ff=target)
    # v44.0 D4: the durable evidence BEFORE the journal claims completion
    note = _rc_rebaseline(flags, sink, iso, mode, rebase[0], rebase[1], rebase[2], target) if rebase else None
    jkv, jraw = _rc_read_kv_file(journal_path)
    _rc_rewrite_journal(journal_path, jraw, "active", fkey, "%s %s" % (now_iso(), target))
    v = _rc_report(flags, sink, iso, mode, cell, "complete", ff=target)
    if note:
        sys.stderr.write(note)
    _rc_finish(v)


def _rc_rebaseline(flags, sink, iso, mode, gn, h, full, ff):
    """v44.0 (plan-away-autonomous-rails T0.2 / D4, KD3) — the re-baseline record
    the group close writes under a bound away grant: ONE unpaired
    `OWNERSHIP: auto-disposition … key=stage-<N>-set-refresh choice=rebaselined
    to=<the group's MERGE COMMIT> rec=composer:group-ff away=<n>
    away_check=<h>` (no NOTIFY twin, no epoch= field — the shape
    emittable_record accepts, so `quoted-block`'s fold reads it as the
    accepted VERSION of every file present at <to>; never set membership)
    written DIRECTLY with write_lines into the stage probe log (--log), the
    run-close / ci-verdict / grant precedent. `to=` is the merge commit, not
    the fetched tip, so a foreign commit landed after the merge still reads
    `changed` (RISK-1). The EXISTENCE CHECK runs before every possible append
    — the normal path, the `ff_stage_<N>`-absent replay, and the
    already-closed branch — over ALL the log's raw lines (round 12
    PR-MED-1202: the whole scan precedes the decision, so a matching record
    never masks later evidence): a writer-valid `rebaselined` record of the
    reader's eligible shape (_qb_rebaseline_shape — no file= / heading=;
    round 12 PR-REG-1201: a shape the reader skips is not evidence) with the
    same key, away pair, and to= → nothing appended (the record already is
    the evidence; returns None); such a record with a DIFFERENT to= →
    refused `rebaseline-conflict`; a doubtful auto-disposition line naming
    the key → refused `rebaseline-unreadable` (fail closed); an unreadable
    log → the same.
    Returns the stderr note `group-ff: rebaselined at <log>:<line>` for the
    caller to print AFTER its report record, so the record sits one line
    above the `cell=group-ff` report. Refusals report `cell=group-ff
    verdict=refused detail=<which> ff=<ff>` and exit 3, nothing appended."""
    runkey = flags["--run"]
    key = "stage-%d-set-refresh" % int(runkey[len("stage-"):])
    log = flags["--log"]

    def refused(detail, why):
        sys.stderr.write("group-ff refused: %s\n" % why)
        _rc_finish(_rc_report(flags, sink, iso, mode, "group-ff", "refused", detail, ff=ff))

    lines, err = raw_record_lines(log)
    if lines is None:
        refused("rebaseline-unreadable", "the stage probe log %s could not be read (%s) — the re-baseline's existence check needs it" % (log, err))
    # round 12 PR-MED-1202: the WHOLE log is scanned before the present /
    # append decision — a conflict or a doubtful line of the key refuses
    # wherever it sits, a matching record earlier in the log never masks it.
    found = False
    for i, text in enumerate(lines, 1):
        r = raw_classify(text, "auto-disposition")
        if r is None:
            continue
        kv, why = r
        if kv is None:
            if _away_text_has(text, key):
                refused("rebaseline-unreadable", "%s:%d is a %s line the writer could not have emitted (%s) — fail closed"
                        % (os.path.basename(log), i, key, why))
            continue
        if kv.get("key") != key or parse_count(kv.get("away", "")) != gn or kv.get("away_check") != h:
            continue
        # round 12 PR-REG-1201: the ONE eligibility rule the version reader
        # applies (_qb_rebaseline_shape) — a record the reader skips is not
        # evidence here either, so the genuine record is appended (the repair)
        if not _qb_rebaseline_shape(kv):
            continue
        if kv.get("to") != full:
            refused("rebaseline-conflict", "%s:%d already re-baselines grant %d at to=%s, not this group's merge commit %s"
                    % (os.path.basename(log), i, gn, kv.get("to", "")[:40], full))
        found = True
    if found:
        return None   # present — the record already is the evidence
    kv = {"key": key, "choice": "rebaselined", "to": full, "rec": "composer:group-ff", "away": str(gn), "away_check": h}
    validate_record("OWNERSHIP:auto-disposition", kv, role="composer")
    line, tokens = assemble_ownership_record("auto-disposition", now_iso(), None, runkey,
                                             ownership_required("auto-disposition", kv), kv, list(kv.items()))
    _k, _b, why = emittable_record(line, "OWNERSHIP:auto-disposition")
    if why:
        refuse("the re-baseline record the helper assembled is not one its own writer accepts (%s) — nothing written" % why)
    write_lines(sink, [line], token_lists=[tokens])
    return "group-ff: rebaselined at %s:%d\n" % (log, len(lines) + 1)


def _rc_group_close(flags, sink, iso, mode, base_real, journal_path, jkv, jraw,
                    state, worktree, branch, wt_exists, merge_commit, rebase=None):
    """D2 — the group-merge legs, in order: the journal MUST be `active`
    (refused `journal-not-active`); `--run stage-<N>` looked up in `groups=`
    (`group-not-in-journal`; the LAST entry is `group-is-final` — the final
    group closes through `--outcome merged`); the sha resolves (`merge-commit
    not found` — v46.4 D8: only after _rc_resolve_merge_commit's one fetch of
    the base branch and second resolve); a present `merged_stage_<N>` REPLAYS — the stored sha and tag
    must equal this call's (`group-identity-mismatch`, no write), on a match
    the group-merge record is written again as `verdict=already-closed` (the
    tip-ancestry leg skipped: the branch may have advanced; the stored sha is
    the authority) and the fast-forward leg runs when `ff_stage_<N>` is absent
    — it binds the worktree identity itself before it mutates anything (both
    present → the second record `cell=group-ff verdict=already-closed`,
    nothing written); else the fresh path — _rc_identity_bind, the worktree
    present and registered (`worktree-absent`), the sha in the fetched base
    (`merge-commit not in base (fetch first)`), the run-branch tip
    (`run-branch ref absent`), the MERGE-PARENT BINDING — two-sided: `<sha>`
    has exactly two parents and `<sha>^2` == tip (the run side), AND `<sha>`
    lies on the base ref's first-parent chain (the base side — `rev-list
    --first-parent <base_ref> ^<sha>^1` lists it), else
    `merge-parent-mismatch` — the retro
    pointer, THEN the first write `merged_stage_<N>="<ts> <sha> <tag>"` and
    `cell=group-merge verdict=complete group=<tag> merge_commit=<sha>`, then
    the fast-forward leg. Every path ends in _rc_finish or refuse."""
    cell = "group-merge"
    if state != "active":
        _rc_finish(_rc_report(flags, sink, iso, mode, cell, "refused", "journal-not-active"))
    n = int(flags["--run"][len("stage-"):])  # RUNKEY_RE held in main
    groups = _rc_groups(jkv)
    if groups is None or n not in dict(groups):
        _rc_finish(_rc_report(flags, sink, iso, mode, cell, "refused", "group-not-in-journal"))
    if n == groups[-1][0]:
        _rc_finish(_rc_report(flags, sink, iso, mode, cell, "refused", "group-is-final"))
    tag = dict(groups)[n]
    gkey, fkey = "merged_stage_%d" % n, "ff_stage_%d" % n
    mc_rc, full = _rc_resolve_merge_commit(base_real, jkv, merge_commit)   # v46.4 D8 (a): one fetch before the refusal
    if mc_rc != 0 or not _FULL_SHA_RE.match(full):
        _rc_finish(_rc_report(flags, sink, iso, mode, cell, "refused", "merge-commit not found", group=tag))
    stored = jkv.get(gkey)
    if stored is not None:
        toks = stored.split()
        if len(toks) != 3 or toks[1] != full or toks[2] != tag:
            _rc_finish(_rc_report(flags, sink, iso, mode, cell, "refused", "group-identity-mismatch",
                                  group=tag, merge_commit=full))
        _rc_report(flags, sink, iso, mode, cell, "already-closed", group=tag, merge_commit=full)
        ff_stored = jkv.get(fkey)
        if ff_stored is not None:
            ff_toks = ff_stored.split()
            ff_sha = ff_toks[-1] if ff_toks and _FULL_SHA_RE.match(ff_toks[-1]) else None
            # v44.0 D4: with the trio, the already-closed branch runs the SAME
            # existence check and appends the missing re-baseline (the
            # idempotent repair — exactly one record after any replay);
            # "nothing written" holds only when the matching record exists.
            note = _rc_rebaseline(flags, sink, iso, mode, rebase[0], rebase[1], full, ff_sha) if rebase else None
            v = _rc_report(flags, sink, iso, mode, "group-ff", "already-closed", ff=ff_sha)
            if note:
                sys.stderr.write(note)
            _rc_finish(v)
        _rc_group_ff(flags, sink, iso, mode, base_real, journal_path, worktree, branch, fkey,
                     rebase=(rebase[0], rebase[1], full) if rebase else None)
    wt_registered = _rc_identity_bind(flags, sink, iso, mode, base_real, branch, worktree, wt_exists)
    if not wt_exists or not wt_registered:
        _rc_finish(_rc_report(flags, sink, iso, mode, cell, "refused", "worktree-absent", group=tag))
    base_ref = _rc_base_ref(base_real, jkv)
    anc_rc, _ = _rc_git(base_real, "merge-base", "--is-ancestor", full, base_ref)
    if anc_rc != 0:
        _rc_finish(_rc_report(flags, sink, iso, mode, cell, "refused", "merge-commit not in base (fetch first)",
                              group=tag, merge_commit=full))
    tip_rc, tip = _rc_git(base_real, "rev-parse", "--verify", "--quiet", "refs/heads/%s" % branch)
    if tip_rc != 0 or not _FULL_SHA_RE.match(tip):
        _rc_finish(_rc_report(flags, sink, iso, mode, cell, "refused", "run-branch ref absent",
                              group=tag, merge_commit=full))
    par_rc, parents = _rc_git(base_real, "rev-list", "--parents", "-n", "1", full)
    ptoks = parents.split()
    if par_rc != 0 or len(ptoks) != 3 or ptoks[0] != full or ptoks[2] != tip:
        _rc_finish(_rc_report(flags, sink, iso, mode, cell, "refused", "merge-parent-mismatch",
                              group=tag, merge_commit=full))
    # round 14 PR-MED-002: the BASE side of the binding — the merge commit
    # must lie on the base ref's FIRST-PARENT chain (a GitHub merge into
    # <base-branch> always does; a nested merge of the run tip into another
    # branch that later reached the base is reachable only through a second
    # parent and is not listed). `^<sha>^1` bounds the walk at the merge's
    # own base-side parent; the base moving before or after the genuine merge
    # keeps it on the chain.
    fp_rc, chain = _rc_git(base_real, "rev-list", "--first-parent", base_ref, "^%s^1" % full)
    if fp_rc != 0 or full not in chain.split():
        _rc_finish(_rc_report(flags, sink, iso, mode, cell, "refused", "merge-parent-mismatch",
                              group=tag, merge_commit=full))
    gap = _rc_retro_pointer_gap(flags)
    if gap:
        _rc_finish(_rc_report(flags, sink, iso, mode, cell, "refused", gap, group=tag, merge_commit=full))
    _rc_rewrite_journal(journal_path, jraw, "active", gkey, "%s %s %s" % (now_iso(), full, tag))
    _rc_report(flags, sink, iso, mode, cell, "complete", group=tag, merge_commit=full)
    _rc_group_ff(flags, sink, iso, mode, base_real, journal_path, worktree, branch, fkey,
                 rebase=(rebase[0], rebase[1], full) if rebase else None)


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
    written); 2 on grammar/identity refusals (nothing written).

    v33.2 (/close-run D10/D11): `--outcome merged --merge-commit <sha>` is the
    squash-aware ENTRY into that same verified-merge cell: admitted from a
    `retained-green`, `merged` (re-entry after a refused/interrupted
    teardown) or `active` + `--attest owner-dead` journal; every D10 leg runs
    BEFORE the first write (`merged="<ts> <full sha>"`), the cell then skips
    its ancestry leg and deletes the branch with `-D`. A `merged` journal
    with both artifacts already gone converges record-only (the cell's
    existing both-gone exception; the recorded `merged=` line preserved).

    v33.8 (plan-run-hygiene D1-D3): `--outcome reconcile` also closes,
    RECORD-ONLY, a journal whose first state is none of intent / created /
    merging / cleaned / active (a terminal state, `merged`, or a hand-written,
    empty, or missing one) when the state line is rewritable at column 0 and
    the recorded absolute worktree= and branch= are both CONFIRMED gone
    (_rc_artifacts_confirmed_gone — indeterminate is never absence): the
    first state= line becomes `cleaned`, one `reconciled="<ts>
    retroactive-record: ...; prior-state=<token>"` key is appended (replacing
    any earlier one), the marker is retired, and the existing
    journal-artifact-mismatch / complete record is written. A missing --log
    folder refuses exit 2 before any write. Every other shape falls through
    to the cells below, unchanged.

    v40.0 Phase 1 (plan-one-run-per-plan D2/D3): `--run stage-<N> --outcome
    group-merged --merge-commit <sha>` is the in-run close of ONE non-final
    release group (_rc_group_close, dispatched BEFORE the --merge-commit
    admission block): it REQUIRES an `active` journal (its live marker
    expected, not read — `state=active` is the liveness claim this path
    admits, as the v33.2 live-run guard reads it; no --attest), writes one
    `merged_stage_<N>` key and one `ff_stage_<N>` key (two
    records — the group-merge and group-ff cells), fast-forwards the base
    checkout and the worktree onto the fetched base, tears nothing down, and
    never writes `merged=`. The hard rules above are unchanged: destructive
    teardown still happens ONLY in the verified-merge cell.

    v48.0 (plan-loop-autonomy-group-2 D17): THE LIVE-ROLE GUARD. The two
    cells that tear down — the verified-merge cell (on both of its entries)
    and the pre-journal marker unlink — refuse, before their first write,
    unless the role-liveness reader (run_legs) says `over` for every leg the
    run's log root holds evidence of. A `live` leg refuses whatever was
    attested; an `unknown` leg refuses unless `--attest owner-dead` rides the
    call (so from v48.0 the flag is also read on a `merged` and a
    `retained-green` journal's `--outcome merged`, where it was accepted and
    ignored). No leg evidence admits. The refusal is the cell's existing
    refused form with a `detail=` naming the leg, the word, the pids and the
    stop command; no cell token is added. Every other cell — the group
    close, retained-green, the record-only reconciles, the marker-only
    close — tears nothing down and is not guarded."""
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
    # v33.2 (/close-run T1.1): --merge-commit rides `--outcome merged` ONLY —
    # v40.0 Phase 1: and `--outcome group-merged`, where it is REQUIRED (a
    # grammar refusal on every other outcome, and on a flag-less group close —
    # exit 2, nothing written); 7-40 hex admitted here, resolved to the FULL
    # sha by the D10 legs / the group-close legs below.
    merge_commit = flags.get("--merge-commit")
    if outcome == "group-merged" and merge_commit is None:
        refuse("--outcome group-merged REQUIRES --merge-commit <7-40 hex> (the group's merge commit — the close has nothing to verify without it)",
               "run-close --run stage-<N> --iso <iso-id> --base </abs/base> --outcome group-merged --merge-commit <7-40 hex> --plan </abs/plan.md>")
    if merge_commit is not None:
        if outcome not in ("merged", "group-merged"):
            refuse("--merge-commit is accepted ONLY with --outcome merged (the squash-aware merged close) or --outcome group-merged (the group close) — got --outcome %s" % outcome,
                   "run-close --iso <iso-id> --base </abs/base> --outcome merged|group-merged --merge-commit <7-40 hex> --plan </abs/plan.md>")
        if not _MERGE_COMMIT_RE.match(merge_commit):
            refuse("--merge-commit %r is not a 7-40 hex commit id" % merge_commit[:60])
        merge_commit = merge_commit.lower()
    # v44.0 (plan-away-autonomous-rails T0.2 / D4): the re-baseline trio —
    # `--grant <n> --away-check <12hex>` accepted only TOGETHER
    # (grant-flags-pair), only with `--outcome group-merged`
    # (grant-flags-outcome), and only when --log is a stage probe log the
    # folds read (grant-flags-log — the OWNERSHIP:hold precedent; the
    # harness's `<loops>/probe.log` is a name no fold reads). Without the pair
    # the group close behaves exactly as v40.0 (no record) — the mixed-version
    # safety. Grammar refusals: exit 2, nothing written.
    rebase = None
    _gn, _ac = flags.get("--grant"), flags.get("--away-check")
    if (_gn is None) != (_ac is None):
        refuse("--grant <n> and --away-check <config_hash> travel together — both or none (grant-flags-pair; the bound grant's number and hash from the `away:` line)",
               "run-close --run stage-<N> --iso <iso-id> --base </abs/base> --outcome group-merged --merge-commit <sha> --grant <n> --away-check <12hex> --log <log-root>/stage-<N>-probe.log")
    if _gn is not None:
        if outcome != "group-merged":
            refuse("--grant/--away-check ride --outcome group-merged only — the re-baseline is the group close's (grant-flags-outcome); got --outcome %s" % outcome)
        if not PROBE_LOG_NAME_RE.match(os.path.basename(flags["--log"])):
            refuse("--log with --grant/--away-check must be named stage-<N>-probe.log (got %r) — the only names `quoted-block`'s fold reads; a re-baseline written elsewhere is never an accepted version (grant-flags-log)"
                   % os.path.basename(flags["--log"])[:60])
        _n = parse_count(_gn)
        if _n is None or _n < 1:
            refuse("--grant must be a positive integer — the bound grant's number (bad-grant)")
        if not HEX12_RE.match(_ac):
            refuse("--away-check must be the grant's config_hash — 12 lowercase hex (bad-away-check)")
        rebase = (_n, _ac)
    if not os.path.isabs(base):
        refuse("--base must be an absolute path")
    if not os.path.isdir(base):
        envfail("--base %s is not a directory" % base)
    base_real = canon_path(base)
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
            if canon_path(mchk) != base_real:
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
                # v48.0 (D17): the marker-only unlink is a teardown too — a live
                # leg under this iso's log folder refuses it (no journal here,
                # so the folder is <loops>/<iso>); the attestation this cell
                # already requires is what admits an `unknown` one
                _rc_live_role_guard(flags, sink, iso, mode, "pre-journal", base_real, None)
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
    if jbase is None or canon_path(jbase) != base_real:
        _rc_finish(_rc_report(flags, sink, iso, mode, "identity-mismatch", "refused",
                              "journal base missing or mismatched against --base"))
    state = jkv.get("state", "")
    if outcome == "complete":
        refuse("--outcome complete is the journal-less (branch/none) close — a journaled run closes via its lifecycle outcomes",
               "retained-green | merged | paused | crashed | merge-failed | reconcile | group-merged")
    worktree = jkv.get("worktree", "")
    branch = jkv.get("branch", "")
    wt_exists = bool(worktree) and os.path.isdir(worktree)
    br_exists = False
    if branch:
        br_rc, _ = _rc_git(base_real, "rev-parse", "--verify", "--quiet",
                           "refs/heads/%s" % branch)
        br_exists = (br_rc == 0)

    # ---- v40.0 Phase 1 (plan-one-run-per-plan D2/D3): the GROUP close ----
    # Sits BEFORE the --merge-commit admission block, whose live-run guard
    # would otherwise refuse the `active` journal a group close REQUIRES; the
    # branch always finishes (exit 0 / 3 with its records, or an exit-2
    # refusal with nothing written) — it never reaches the `active`
    # fall-through, which has no _OUTCOME_STATE entry for this outcome.
    if outcome == "group-merged":
        _rc_group_close(flags, sink, iso, mode, base_real, journal_path, jkv, jraw,
                        state, worktree, branch, wt_exists, merge_commit, rebase)

    # ---- v33.2 (/close-run D10/D11): the --merge-commit admission block ----
    # Sits BEFORE the terminal-state block (which would otherwise refuse a
    # retained-green journal as already-terminal) and admits ONLY the three
    # D11 sources; every other state falls through to today's refusals
    # (intent/created, merging, paused / crashed / merge-failed as terminal,
    # cleaned as already-closed). Order: live-run guard -> identity (a)(b)
    # -> sha resolves -> re-entry sha agrees with the recorded merged= ->
    # sha in the fetched base -> tip covered (ancestry fast path, else the
    # merge-tree recompute) -> retro pointer -> THE FIRST WRITE (merged=),
    # then the cell with pre_verified=True. Nothing is written before every
    # leg passes, so a pre-verification refusal leaves the journal
    # byte-identical.
    pre_verified = False
    merge_commit_full = None
    if merge_commit is not None and state in ("retained-green", "merged", "active"):
        if state == "active" and flags.get("--attest") != "owner-dead":
            # D11/D13 live-run guard: tip evidence never authorizes a teardown
            # of a run whose journal still claims liveness.
            _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "refused",
                                  "journal active with a live marker (close the run or attest owner-dead)"))
        wt_registered = _rc_identity_bind(flags, sink, iso, mode, base_real, branch,
                                          worktree, wt_exists)
        mc_rc, full = _rc_resolve_merge_commit(base_real, jkv, merge_commit)   # v46.4 D8 (a): one fetch before the refusal
        if mc_rc != 0 or not _FULL_SHA_RE.match(full):
            _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "refused",
                                  "merge-commit not found"))
        recorded = _rc_recorded_merge_sha(jkv) if state == "merged" else None
        if recorded is not None and not full.startswith(recorded):
            _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "refused",
                                  "merge-commit disagrees with journal", merge_commit=full))
        base_ref = _rc_base_ref(base_real, jkv)
        anc_rc, _ = _rc_git(base_real, "merge-base", "--is-ancestor", full, base_ref)
        if anc_rc != 0:
            _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "refused",
                                  "merge-commit not in base (fetch first)", merge_commit=full))
        tip_rc, tip = _rc_git(base_real, "rev-parse", "--verify", "--quiet",
                              "refs/heads/%s" % branch)
        # Both-artifacts-gone convergence (PR-MED-001 r1): a `merged` re-entry
        # after a close deleted the branch but died before the cleaned
        # rewrite — identity-checked above, record-only from here (no tip
        # leg, nothing to destroy, the recorded merged= line preserved).
        both_gone = (state == "merged" and tip_rc != 0 and not wt_exists and not wt_registered)
        if tip_rc != 0 and not both_gone:
            _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "refused",
                                  "run-branch ref absent", merge_commit=full))
        if not both_gone:
            fast_rc, _ = _rc_git(base_real, "merge-base", "--is-ancestor", tip, base_ref)
            if fast_rc != 0:
                why = _rc_d10_tip_covered(base_real, full, tip)
                if why is not None:
                    _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "refused",
                                          why, merge_commit=full))
        gap = _rc_retro_pointer_gap(flags)
        if gap:
            _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "refused", gap,
                                  merge_commit=full))
        # v48.0 (D17): the live-role guard — the last leg before the first
        # write, so a refusal here leaves the journal byte-identical too
        _rc_live_role_guard(flags, sink, iso, mode, "verified-merge", base_real, jkv, merge_commit=full)
        if not both_gone:
            # THE first write: merged="<ts> <full sha>" (replaces any by-hand
            # merged= line — the one-appended-key rewrite rule), then the
            # local state and the raw lines are refreshed so the cell below
            # sees the journal it is about to close.
            _rc_rewrite_journal(journal_path, jraw, "merged", "merged",
                                "%s %s" % (now_iso(), full))
            jkv, jraw = _rc_read_kv_file(journal_path)
            state = "merged"
        pre_verified = True
        merge_commit_full = full

    # ---- v33.8 (plan-run-hygiene D1-D3): the record-only reconcile of a
    # finished run whose artifacts are gone ----
    # Sits AFTER identity binding and the --merge-commit block (which cannot
    # accompany reconcile) and BEFORE the terminal-state block (which would
    # otherwise refuse a retained-green / paused / ... journal as already
    # terminal). Fires ONLY when every D1 condition holds; otherwise control
    # falls through to today's code unchanged. Writes nothing but the journal
    # rewrite, the marker retirement, and the one report record — no
    # worktree removal, branch deletion, prune, fetch, or commit.
    if (outcome == "reconcile" and state not in _RECONCILE_EXCLUDED_STATES
            and _rc_state_line_rewritable(jraw)
            and _rc_journal_lossless(journal_path, jraw)
            and _rc_artifacts_confirmed_gone(base_real, worktree, branch)):
        log_path = flags.get("--log")
        if log_path is not None and not os.path.isdir(os.path.dirname(log_path)):
            # Before ANY write: a missing log folder would let the journal be
            # rewritten and then fail the close record's append.
            refuse("--log folder %s does not exist — the reconcile writes nothing until its close record can persist"
                   % os.path.dirname(log_path))
        toks = state.split()
        token = toks[0] if toks and _PRIOR_STATE_RE.match(toks[0]) else "unrecognized"
        _rc_rewrite_journal(journal_path, jraw, "cleaned", "reconciled",
                            "%s retroactive-record: worktree and branch already absent at close; prior-state=%s"
                            % (now_iso(), token))
        _rc_dispose_marker(marker_path)
        _rc_finish(_rc_report(flags, sink, iso, mode, "journal-artifact-mismatch", "complete",
                              "retroactive reconcile recorded; nothing was torn down"))

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
        # evidence — never to arbitrary journal strings. Checks (a) + (b)
        # live in _rc_identity_bind (shared with the v33.2 admission block,
        # which already ran them once BEFORE its merged= write; re-run here so
        # the binding holds at the moment of destruction).
        wt_registered = _rc_identity_bind(flags, sink, iso, mode, base_real, branch,
                                          worktree, wt_exists, merge_commit=merge_commit_full)
        # (c) Ancestry binding against the RESOLVED base: the run-branch tip
        # must resolve AND be an ancestor of the recorded base branch (HEAD
        # fallback only when the journal predates base_branch). An ABSENT
        # branch ref fails closed to report-only whenever anything remains to
        # tear down — the only ref-less admission is the both-already-gone
        # idempotent convergence. v33.2: the --merge-commit path arrives
        # pre_verified (D10 replaced this leg with the squash verdict) and
        # skips ONLY the ancestry test — the absent-ref refusal still holds.
        base_ref = "refs/heads/%s" % jkv["base_branch"] if jkv.get("base_branch") else "HEAD"
        tip_rc, tip = _rc_git(base_real, "rev-parse", "--verify", "--quiet",
                              "refs/heads/%s" % branch)
        if tip_rc != 0:
            if wt_exists or wt_registered:
                _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "refused",
                                      "run-branch ref is absent so the merge cannot be re-verified — worktree retained, report-only",
                                      merge_commit=merge_commit_full))
        elif not pre_verified:
            anc_rc, _ = _rc_git(base_real, "merge-base", "--is-ancestor", tip, base_ref)
            if anc_rc != 0:
                _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "refused",
                                      "merge verification failed — run branch tip is not in the resolved base; everything retained"))
        gap = _rc_retro_pointer_gap(flags)
        if gap:
            _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "refused", gap,
                                  merge_commit=merge_commit_full))
        # v48.0 (D17): the live-role guard at the moment of destruction — the
        # ONE check on the ancestry path (a `merged` journal with no
        # --merge-commit), and on the flag path a second read after the
        # admission block's (a role can have been started since)
        _rc_live_role_guard(flags, sink, iso, mode, "verified-merge", base_real, jkv,
                            merge_commit=merge_commit_full)
        if wt_exists:
            # v33.2: the _rc_git exception shape — a removal timeout (a
            # multi-GB worktree) or a launch failure is a dirty/refused
            # verdict with everything retained, never a traceback.
            try:
                r = subprocess.run([_git_bin(), "-C", base_real, "worktree", "remove", worktree],
                                   capture_output=True, text=True, timeout=120, env=_git_env())
                rm_rc, rm_err = r.returncode, (r.stderr or "").strip()[:400]
            except Exception as e:
                rm_rc, rm_err = 1, "worktree remove did not complete: %s" % e
            if rm_rc != 0:
                sys.stderr.write("worktree remove refused: %s\n" % rm_err)
                _rc_finish(_rc_report(flags, sink, iso, mode, "dirty", "refused",
                                      "non-force worktree removal refused (dirty or locked) — everything retained",
                                      merge_commit=merge_commit_full))
        else:
            _rc_git(base_real, "worktree", "prune")
        if tip_rc == 0:
            # D17: `-D` ONLY behind the verified squash verdict (a squash-merged
            # branch is never "fully merged" to git's `-d`); the ancestry path
            # keeps the non-force `-d`.
            del_flag = "-D" if pre_verified else "-d"
            r = subprocess.run([_git_bin(), "-C", base_real, "branch", del_flag, branch],
                               capture_output=True, text=True, timeout=60, env=_git_env())
            if r.returncode != 0:
                sys.stderr.write("branch %s refused: %s\n" % (del_flag, (r.stderr or "").strip()[:400]))
                _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "refused",
                                      ("forced branch deletion refused — re-run after reconciling" if pre_verified
                                       else "non-force branch deletion refused — re-run after reconciling"),
                                      merge_commit=merge_commit_full))
        # Re-read before the closing rewrite so the merged= line the v33.2
        # admission block wrote above survives byte-for-byte (the cell's
        # `jraw` predates that write on the flag path); the cleaned rewrite
        # replaces state= and the closed= line only. This is the helper's own
        # write being picked up — the journal's one-writer contract is
        # unchanged and no concurrent-writer guarantee is implied.
        jkv, jraw = _rc_read_kv_file(journal_path)
        _rc_rewrite_journal(journal_path, jraw, "cleaned", "closed", now_iso())
        _rc_dispose_marker(marker_path)
        _rc_finish(_rc_report(flags, sink, iso, mode, "verified-merge", "complete",
                              "merge verified; worktree removed; branch deleted; journal cleaned; marker dispositioned",
                              merge_commit=merge_commit_full))
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
    below-root component with a no-follow directory openat, returning a
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
    before any payload read or write. v45.0 (T1.1): every open and stat goes
    through the host primitives — the fd-relative leg is this openat walk
    unchanged; the fallback leg (HOST["fd_relative"] False) carries the
    directory PATH as the handle and lstat-refuses each component before
    descending, so a symlink below the root still refuses on both legs (D8:
    the fallback's check-then-open window is the documented residual)."""
    try:
        rst = os.lstat(root_real)
    except OSError:
        refuse("%s authority root %s does not exist (retain + surface)" % (what, root_real))
    if _is_redirect(rst) or not stat.S_ISDIR(rst.st_mode):
        refuse("%s authority root %s is not a real directory (retain + surface)" % (what, root_real))
    try:
        dfd = _open_at(None, root_real, os.O_RDONLY, follow=True, directory=True)
    except OSError as e:
        envfail("cannot open %s authority root %s: %s" % (what, root_real, e))
    ok = False
    try:
        for seg in rel_segments:
            if seg in ("", ".", ".."):
                refuse("%s path escapes the authority root via %r (root-escape; retain + surface)" % (what, seg))
            # Classify the component no-follow relative to the HELD parent for
            # a precise message (a symlink-to-dir opens as ELOOP on some kernels
            # and ENOTDIR on others); the no-follow open below stays the real
            # guard and catches any swap between this stat and the open.
            try:
                lst = _stat_at(dfd, seg, follow=False)
            except FileNotFoundError:
                refuse("%s component %r is missing (retain + surface)" % (what, seg))
            except OSError as e:
                envfail("cannot stat %s component %r: %s" % (what, seg, e))
            if _is_redirect(lst):
                refuse("%s component %r is a symlink — no-follow containment forbids a symlink below the recorded root (root-escape; retain + surface)"
                       % (what, seg))
            if not stat.S_ISDIR(lst.st_mode):
                refuse("%s component %r is not a directory (root-escape; retain + surface)" % (what, seg))
            try:
                nfd = _open_at(dfd, seg, os.O_RDONLY, follow=False, directory=True)
            except OSError as e:
                if e.errno in (errno.ELOOP, errno.EMLINK, errno.ENOTDIR):
                    refuse("%s component %r changed to a symlink/non-directory between check and open (check/open race; root-escape; retain + surface)"
                           % (what, seg))
                if e.errno == errno.ENOENT:
                    refuse("%s component %r vanished between check and open (retain + surface)" % (what, seg))
                envfail("cannot open %s component %r: %s" % (what, seg, e))
            _dir_close(dfd)
            dfd = nfd
        ok = True
        return dfd
    finally:
        if not ok:
            try:
                _dir_close(dfd)
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
    Returns a HELD directory fd for the log root (caller closes). v45.0
    (T1.3 — D17's ONE exception, PR-MED-001 rounds 3 and 10): base_real
    arrives PHYSICAL (canon_path) and the recorded `base=` / `log_root=` are
    taken through canon_path's SPELLING form (resolve=False — separators,
    the drive letter, the MSYS conversion; never realpath, never normpath),
    so the relpath below is still lexical and the segments reach the walk
    unresolved on both host legs; a cross-drive relpath (ntpath raises
    ValueError) is the same root-escape refusal."""
    try:
        rel = os.path.relpath(os.path.normpath(canon_path(log_root, resolve=False)),
                              os.path.normpath(canon_path(recorded_base, resolve=False)))
    except ValueError:
        refuse("%s %s is not under the recorded base checkout %s (root-escape — a different drive; retain + surface)"
               % (what, log_root, recorded_base))
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
        st = _stat_at(dir_fd, name, follow=False)
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
    dir fd no-follow + a post-open fstat regular check. The held dir fd
    already defeats a parent-component swap; when `expect_st` is supplied the
    (st_dev, st_ino) identity-bind additionally rejects a same-directory
    substitution of the final component between its stat and this open. Returns
    the bytes read; refuses a symlink, a non-regular target, or an identity
    mismatch."""
    try:
        fd = _open_at(dir_fd, name, os.O_RDONLY, follow=False)
    except _AtIdentityError:
        refuse("%s %r changed identity between check and open (check/open race; retain + surface)" % (what, name))
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
    """PR-HIGH-001 (r12/r13): append RELATIVE to the held dir fd no-follow
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
    flags = os.O_WRONLY | os.O_APPEND
    if create:
        flags |= os.O_CREAT | os.O_EXCL
    try:
        fd = _open_at(dir_fd, name, flags, follow=False, mode=0o644)
    except _AtIdentityError:
        refuse("%s %r changed identity between validation and append (check/open race; never advance to published; retain + surface)"
               % (what, name))
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
    Reads through the no-follow dir-fd-relative payload opener with the
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
        st = _stat_at(dir_fd, name, follow=False)
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
        _replace_at(dir_fd, name, dir_fd, target)
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
    base_real = canon_path(base)
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
            if jbase is None or canon_path(jbase) != base_real:
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
            # The recorded worktree/base are the authority roots (canonical —
            # physically resolved, so a symlinked ancestor above them is
            # permitted); nothing symlinked below.
            staging_fd = _fd_walk_dir(canon_path(worktree), (".cursor", "loops"),
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
            if mchk is None or canon_path(mchk) != base_real:
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
        # set() closes each unique descriptor exactly once (a fallback-leg PATH
        # handle has nothing to close — _dir_close).
        for _fd in set(open_fds):
            try:
                _dir_close(_fd)
            except OSError:
                pass


# --- v34.0 D4/D5: `away` — the away grant (grant | end | check | report) -------

# An away line is any policy-log line whose OWNERSHIP subtype token starts
# `away` (glued or spaced): every such line is judged by the state function,
# so an invented `away-*` token or a glued prefix makes the log malformed
# rather than being silently ignored.
AWAY_LINE_RE = re.compile(r"\AOWNERSHIP:\s*away(?![A-Za-z0-9_])")
AWAY_VERBS = ("grant", "end", "check", "report", "ci-verdict", "census", "lint")
# v37.0 Decision 2: the automatic end reasons (members of the V_base
# AWAY_END_REASONS) — refused while a release act is in flight
AWAY_AUTO_END_REASONS = ("release-done", "run-stop")
# v40.0 Phase 1 (plan-one-run-per-plan D5): the journal states on which an
# `away end reason=release-done` WITH --log-root is admitted — the run has
# CLOSED (the final group's verified merge, its teardown, or its green close).
# A PURPOSE-SPECIFIC set, never _TERMINAL_STATES (whose close-idempotency
# readers deliberately include the interrupted outcomes paused /
# crashed/recovery-needed / merge-failed — a park, not a close); and never the
# group keys (after group B's close every non-final key may be present while
# the next group is unstarted). One grant per run: a park at any group keeps
# it bound.
AWAY_RELEASE_DONE_STATES = ("merged", "cleaned", "retained-green")
# Per-verb argv grammar (the SUB_GRAMMAR pattern, one level down): the flags
# beyond --run/--role, which of them are required, and the admitted kv keys.
AWAY_VERB_GRAMMAR = {
    # v44.0 D16: `allows=` — the departure-time pre-approvals, a trailing kv on
    # the grant record (outside config_hash), validated by parse_grant_allows.
    # v47.0 D22: `widens=<n>` — the one-step widening of the bound grant n
    # (an invocation argument: stored on neither record it writes).
    "grant":  {"flags": {"--policy-log", "--iso", "--plan", "--log-root"},
               "required": ("--policy-log", "--iso", "--plan", "--log-root"),
               "kvs": {"scope", "allows", "widens"}, "kvs_required": ("scope",)},
    # v35.0 A11: --log-root is OPTIONAL on end (never required) — it fills the
    # printed report recipe; a legacy end without it writes the same record.
    # v40.0 D5: --base — REQUIRED with reason=release-done and --log-root (the
    # closed-run gate reads <base>/.cursor/loops/<iso>-isolation), refused on
    # every other end (the total-argv contract); registered at value_flags,
    # the unknown-flag hint, and `away`'s SUB_GRAMMAR already (v35.1).
    "end":    {"flags": {"--policy-log", "--iso", "--plan", "--log-root", "--base"},
               "required": ("--policy-log", "--iso", "--plan"),
               "kvs": {"grant", "reason"}, "kvs_required": ("grant", "reason")},
    "check":  {"flags": {"--policy-log", "--iso", "--plan", "--log-root"},
               "required": ("--policy-log", "--iso", "--plan", "--log-root"),
               "kvs": set(), "kvs_required": ()},
    "report": {"flags": {"--policy-log", "--iso", "--plan", "--log-root", "--out"},
               "required": ("--policy-log", "--iso", "--plan", "--log-root"),
               "kvs": {"grant"}, "kvs_required": ()},
    # v35.1 Decisions 2/4: the helper's own CI read — every flag required
    # (--base is gh's working directory, absolute), pr= digits, tip= 40 hex.
    "ci-verdict": {"flags": {"--policy-log", "--iso", "--plan", "--log-root", "--base"},
                   "required": ("--policy-log", "--iso", "--plan", "--log-root", "--base"),
                   "kvs": {"pr", "tip"}, "kvs_required": ("pr", "tip")},
    # v37.0 Decisions 4/8: the read-only census of every policy log under
    # <base>/.cursor/loops — --base only; no identity flag, no kv.
    "census": {"flags": {"--base"}, "required": ("--base",), "kvs": set(), "kvs_required": ()},
    # v46.4 (plan-loop-field-review-fixes D5): the read-only departure-file
    # check before a grant binds — `grant`'s four flags, all required; no kv.
    "lint":   {"flags": {"--policy-log", "--iso", "--plan", "--log-root"},
               "required": ("--policy-log", "--iso", "--plan", "--log-root"),
               "kvs": set(), "kvs_required": ()},
}
# the recipe every merge-start refusal names (the published one is T2.3's,
# in the execute-loop SKILL's Record grammar — this is the helper's hint)
CI_VERDICT_RECIPE = ("away ci-verdict --run <runkey> --role composer --policy-log </abs> --iso <iso-id> "
                     "--plan <plan> --log-root </abs> --base </abs> pr=<n> tip=<40-hex>")
# D6's release-act key classes (`<runkey>-<class>`): the report's section 6
# (v35.0 A7 adds `snapshot`). No writer refuses a record FOR its release
# class; from v35.1 (Decision 3, condition 6) `emit` READS the set — a
# release-class disposition written after the latest verdict voids that
# verdict for the next away merge start. The ACT classes are the generated
# AWAY_ACT_CLASSES (V_base, v35.1): the record-before-act guard's set (v35.0
# A9), and — Decisions 3 and 5 — an ENFORCED domain: `emit` refuses an
# away-pair `choice=start` and a `hold` whose key class is outside it.
AWAY_RELEASE_CLASSES = ("close-run-confirm", "retro-pointer", "pr-fix", "merge",
                        "deploy-staging", "staging-checklist", "deploy-production", "rollback",
                        "snapshot")
AWAY_KEY_CLASS_RE = re.compile(r"\Astage-\d+-(.+)\Z")  # the oracle's byte-equal twin
AWAY_OPEN_START_FLAG = "started; outcome not recorded — check the real state"
AWAY_NO_START_FLAG = "outcome recorded with no start before it"
AWAY_LATE_START_FLAG = "late start — recorded after its outcome"
PROBE_LOG_NAME_RE = re.compile(r"\Astage-(\d+)-probe\.log\Z")


def away_state(lines, expect_iso, expect_plan):
    """v34.0 D4 — THE one state function, shared by every `away` verb.
    Reads the policy log's away lines in order: a valid `away-grant`
    numbered (valid grants so far) + 1 while none is open → bound; a valid
    `away-end` naming the open grant → ended. Validity is the writer's own
    predicate (emittable_record → validate_record → validate_away_record, so
    config_hash= is recomputed on read). Any other away line — one that
    fails validation, carries the wrong number, a grant while one is open,
    an end with none open — makes the log MALFORMED from that line on, for
    the rest of the run (no later line re-opens it); a line whose iso= or
    plan= differs from the expected identity makes it WRONG-IDENTITY, equally
    sticky. Returns a dict: state (absent|bound|ended|malformed|
    wrong-identity), grants (each {n, kv, line, end_kv, end_line}), open
    (the open grant or None), bad ((line number, raw line, reason) or None)."""
    grants, open_g, bad, bad_state = [], None, None, None
    for n, raw in enumerate(lines, 1):
        line = raw.rstrip("\r\n")
        if not AWAY_LINE_RE.match(line):
            continue
        if bad is not None:
            continue  # sticky: no later line re-opens a malformed / wrong-identity log
        _kv, bare = parse_kv(line[len("OWNERSHIP:"):])
        sub = bare[0] if bare else ""
        if sub not in AWAY_RECORD_SUBTYPES:
            bad, bad_state = (n, line, "unknown away record token %r" % sub[:40]), "malformed"
            continue
        kv, _b, why = emittable_record(line, "OWNERSHIP:" + sub)
        if why:
            bad, bad_state = (n, line, why), "malformed"
        elif kv["iso"] != expect_iso or kv["plan"] != expect_plan:
            bad, bad_state = (n, line, "identity mismatch — record iso=%s plan=%s vs expected iso=%s plan=%s"
                              % (kv["iso"][:40], kv["plan"][:60], expect_iso[:40], expect_plan[:60])), "wrong-identity"
        elif sub == "away-grant":
            num = parse_count(kv["grant"])
            if open_g is not None:
                bad, bad_state = (n, line, "a grant while grant %d is open" % open_g["n"]), "malformed"
            elif num != len(grants) + 1:
                bad, bad_state = (n, line, "grant=%s is not the next number %d" % (kv["grant"], len(grants) + 1)), "malformed"
            else:
                open_g = {"n": num, "kv": kv, "line": n, "end_kv": None, "end_line": None}
                grants.append(open_g)
        else:
            if open_g is None:
                bad, bad_state = (n, line, "an away-end with no grant open"), "malformed"
            elif parse_count(kv["grant"]) != open_g["n"]:
                bad, bad_state = (n, line, "away-end names grant=%s but grant %d is open" % (kv["grant"], open_g["n"])), "malformed"
            else:
                open_g["end_kv"], open_g["end_line"] = kv, n
                open_g = None
    if bad is not None:
        state = bad_state
    elif open_g is not None:
        state = "bound"
    elif grants:
        state = "ended"
    else:
        state = "absent"
    return {"state": state, "grants": grants, "open": open_g, "bad": bad}


def _away_departure_path(log_root, n):
    return os.path.join(log_root, "away-%d-departure.md" % n)


def _away_departure_bytes(log_root, n):
    """The bytes of the departure file grant `n` reads, for the two verbs
    that read it before a grant exists — `away grant`, and (v46.4 D5) `away
    lint`: ONE read and ONE refusal, so a missing or unreadable file is
    refused in `grant`'s words whichever verb met it."""
    dep_path = _away_departure_path(log_root, n)
    try:
        with open(dep_path, "rb") as f:
            return f.read()
    except OSError as e:
        refuse("away grant reads the departure file %s — missing or unreadable (%s); write it first" % (dep_path, e))


# v37.0 Decision 4 — the census's per-file read cap (a policy log, journal, or
# marker; kount's largest policy log was 4 KB at hardening). A larger file reads
# `unreadable`; the permissive profile below has no cap.
AWAY_CENSUS_CAP = 1 << 20


def _away_file_kind(mode):
    for test, name in ((stat.S_ISDIR, "directory"), (stat.S_ISFIFO, "FIFO"), (stat.S_ISCHR, "character device"),
                       (stat.S_ISBLK, "block device"), (stat.S_ISSOCK, "socket")):
        if test(mode):
            return name
    return "special file"


def _away_read_bytes(name, dir_handle=None, follow=True, cap=None):
    """v37.0 Decision 4 — THE one byte reader for every foreign file the away
    family opens; no separate check precedes the open. The file is opened
    non-blocking (a FIFO never stalls the open) and `fstat` on the DESCRIPTOR
    must report a regular file before any byte is read; anything else raises
    OSError("not a regular file (<kind>)"). Two admission profiles: the
    census's STRICT reads pass `dir_handle` (the held loops directory),
    follow=False (no-follow — a symlink raises ELOOP) and `cap` (at most
    cap + 1 bytes are read; more raises); the existing readers' PERMISSIVE
    reads keep a pathname (relative or absolute), follow symlinks, and have no
    cap — so their one newly rejected input class is a special file at the
    leaf, which takes each caller's existing doubt path. A missing file raises
    FileNotFoundError, as open() does. v45.0 (T1.2): the open goes through
    `_open_at` — BINARY on every host (the departure fingerprint is over
    exact bytes, CRLF and control characters included), `follow` honoured on
    both legs (the no-follow open on the fd-relative leg; the lstat refusal +
    identity bind on the fallback leg, where `dir_handle` is the loops
    directory PATH)."""
    fd = _open_at(dir_handle, name, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0), follow=follow, nonblock=True)
    try:
        fst = os.fstat(fd)
        if not stat.S_ISREG(fst.st_mode):
            raise OSError("not a regular file (%s)" % _away_file_kind(fst.st_mode))
        limit = None if cap is None else cap + 1
        chunks, got = [], 0
        while limit is None or got < limit:
            b = os.read(fd, 1 << 16 if limit is None else min(1 << 16, limit - got))
            if not b:
                break
            chunks.append(b)
            got += len(b)
        if cap is not None and got > cap:
            raise OSError("larger than the %d-byte census cap" % cap)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _away_departure_digest(log_root, n):
    """The first 12 hex of the departure file's sha256, or None when the file
    is missing or unreadable (a special file included — v37.0)."""
    try:
        return hashlib.sha256(_away_read_bytes(_away_departure_path(log_root, n))).hexdigest()[:12]
    except OSError:
        return None


# v36.0 Decision 4 — a continuation run's departure file opens with this
# literal line (Release work item 8). Matched on bytes, printed, never parsed.
AWAY_CARRIED_FROM_RE = re.compile(rb"Carried from: [A-Za-z0-9][A-Za-z0-9._-]* grant [1-9][0-9]*")


def _away_carried_from(log_root, n, departure):
    """The departure file's LITERAL first line when it fully matches the
    `Carried from:` pattern AND the same bytes digest to the grant's
    departure= — otherwise None (nothing is warned)."""
    try:
        data = _away_read_bytes(_away_departure_path(log_root, n))
    except OSError:
        return None
    if hashlib.sha256(data).hexdigest()[:12] != departure:
        return None
    first = data.split(b"\n", 1)[0]
    return first.decode("ascii") if AWAY_CARRIED_FROM_RE.fullmatch(first) else None


# v44.0 (plan-away-autonomous-rails T0.3 / A9, D9): the departure file's
# effective-set warning — a Markdown file in the set with no quoted heading is
# blob-compared, which under KD2 costs a noisy record at every close. The scan
# runs over the bytes `away grant` already holds, authorises nothing, and
# prints `away-warning:` lines to stderr only (a prefix distinct from the
# oracle-pinned `away:` state line, so a 2>&1 reader never confuses them);
# the exit, the record, and the digest are unchanged. A warning, never a
# refusal (KD7): a false positive is noise the composer ignores. ONE departure
# check refuses (v47.0 D5, the single exception to KD7): a file with no
# answered `Usage fallback:` line — `away grant` refuses it
# (`departure-missing-fallback`) before any warning is printed; `away lint`
# reports it as the word `usage-fallback-missing` and still exits 0.
_AWAY_ITEM7_RE = re.compile(r"\A7\.(?!\d)")      # the item 7 heading text — `## 7.` / `### 7.`; a `7.1` sub-heading is inside the block, never the block (round 32)
_AWAY_BULLET_RE = re.compile(r"\A([ \t]*)[-*+][ \t]+")
_AWAY_TICK_RE = re.compile(r"`([^`]*)`")
# v46.4 (plan-loop-field-review-fixes D6): a QUOTED HEADING — the word
# `heading`, optional blanks and one optional colon, then the opening backtick
# or double quote. Departure files spell a quoted procedure several ways (the
# skill prescribes its content, not a syntax), so this is a best-effort read
# of free text. The blanks after the colon sit INSIDE the optional group: with
# the two blank runs side by side (`[ \t]*:?[ \t]*`) a long run of blanks after
# the word that no quote follows is tried at every split of the run — quadratic
# in its length; this form matches the same strings in one pass.
_AWAY_QUOTED_HEADING_RE = re.compile(r"\bheading\b[ \t]*(?::[ \t]*)?([`\"])")


def _away_heading_holds_quote(line):
    """v46.4 D6 — does ONE departure-file line quote a heading that holds a
    double quote (a heading no record can carry: the record grammar has no
    escape for one)? For each quoted heading on the line: in the BACKTICK form,
    yes when the text up to the closing backtick holds a double quote (no
    closing backtick: not this form, no); in the DOUBLE-QUOTE form, yes when
    the stretch from the opening quote to the next backtick, or to the end of
    the line, holds more than two double quotes. Best-effort both ways: a
    spelling this does not know is a no; and text that only resembles a
    quoted heading is a needless yes — a second quoted phrase in that stretch,
    or the word itself written in backticks ahead of a quoted phrase and a
    later backtick. Neither blocks anything."""
    for m in _AWAY_QUOTED_HEADING_RE.finditer(line):
        rest = line[m.end():]
        tick = rest.find("`")
        if m.group(1) == "`":
            if tick >= 0 and '"' in rest[:tick]:
                return True
        elif 1 + (rest if tick < 0 else rest[:tick]).count('"') > 2:
            return True
    return False


def _away_departure_scan(data):
    """The departure file's bytes as every check here reads them: (text,
    fenced, heads) — the lines (LF-split, one trailing CR dropped, decoded
    with surrogateescape), a per-line flag for a line that is a fence or
    inside a fenced block (_QB_FENCE_RE, the quoted-block reader's fence
    rules), and the ATX headings outside fences as (line index, level, text).
    ONE scan, so the item-7 warning, the quoted-heading warning and the
    departure-line reader can never disagree about what is fenced."""
    text = [(p[:-1] if p.endswith(b"\r") else p).decode("utf-8", "surrogateescape") for p in data.split(b"\n")]
    fence, heads, fenced = None, [], [False] * len(text)
    for i, line in enumerate(text):
        m = _QB_FENCE_RE.match(line)
        if fence is not None:
            fenced[i] = True
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1] and line.strip() == m.group(1):
                fence = None
            continue
        if m:
            if m.group(1)[0] == "`" and "`" in line[m.end():]:
                continue   # CommonMark: a backtick opener's info string may not hold a backtick — plain text
            fence = (m.group(1)[0], len(m.group(1)))
            fenced[i] = True
            continue
        h = _QB_HEADING_RE.match(line)
        if h:
            heads.append((i, len(h.group(1)), h.group(2) or ""))
    return text, fenced, heads


# --- v47.0 (plan-loop-autonomy-group-2 D3, D4, D5, D7, D19): the departure
# lines the tooling READS. One rule for every kind (D19): every matching line
# outside a fenced block is read, wherever it sits and in whatever order; a
# malformed line of a kind is never read as that kind's absence; where lines
# disagree the restriction wins. A line is of a kind when — after optional
# indentation and ONE optional list marker, a bullet (`- `, `* `, `+ `) or an
# ordered one (`2. `, `2) ` — Step HA1, round 26 LOW-002: a `park` line written
# as a numbered item was of no kind, so its merge read as unlisted) — it begins
# with the kind's label. The kinds: `Stop: merge` (the fixed merge-stop form, folded
# at every away merge start), `Usage fallback:` (a presence test — the
# fallback in force is the run's `profile-fallback=`, never the line) and
# `Records paths:` (declared records files for `records-delta`). Release 2's
# `Watcher takeover:` reads through the same function. A stated limit: only a
# FENCED block is skipped. Indentation is tolerated so that a line nested
# under a list item is read, which means a line inside an INDENTED code block
# (four blanks, no fence) is read as well — and so is a line of its own
# between `<!--` and `-->`: the scan knows fences and headings, not HTML
# comments (round 9 PR-LOW-004). An example line, or one that is retired,
# belongs in a fence. What is never read is a line that BEGINS with something
# else: a quoted line (`> …`), emphasis or other markup before the label
# (`**Stop: merge …`), or a line that itself opens the comment
# (`<!-- Usage fallback: … -->`) — `away lint` says nothing about such a line.
_AWAY_DEP_LEAD_RE = re.compile(r"\A[ \t]*(?:(?:[-*+]|[0-9]{1,9}[.)])[ \t]+)?")
AWAY_STOP_MERGE_LABEL = "Stop: merge"
AWAY_FALLBACK_LABEL = "Usage fallback:"
AWAY_RECORDS_PATHS_LABEL = "Records paths:"
# D3's fixed form, after the label: ` key=<runkey>-merge kind=stop-3|reserved
# subject=<path>[,<path>…] — pre-approved|around|park — <reason…>` — single
# spaces, the em dash, the paths in the hold records' alphabet.
_AWAY_STOP_MERGE_RE = re.compile(
    r"\A key=(stage-\d+-merge) kind=(stop-3|reserved) subject=([A-Za-z0-9._/-]+(?:,[A-Za-z0-9._/-]+)*)"
    r" — (pre-approved|around|park) — \S.*\Z")


def repo_rel_path_ok(path, prefix=False):
    """Is `path` a repo-relative path in the hold records' alphabet
    (HOLD_PATH_RE) — no leading `/`, no empty, `.` or `..` segment? With
    `prefix=True` the path is a directory prefix: it ends in exactly one `/`,
    and what precedes it obeys the same rule."""
    if prefix:
        if not path.endswith("/"):
            return False
        path = path[:-1]
    return bool(HOLD_PATH_RE.match(path)) and all(seg not in ("", ".", "..") for seg in path.split("/"))


def away_departure_lines(data, label):
    """D19's one reader: [(line number from 1, the text after the label)] for
    every line of the departure file outside a fenced block that begins —
    after optional indentation and one optional list marker — with `label`,
    in file order. What the text after the label means is the caller's."""
    text, fenced, _heads = _away_departure_scan(data)
    out = []
    for i, line in enumerate(text):
        if fenced[i]:
            continue
        rest = line[_AWAY_DEP_LEAD_RE.match(line).end():]
        if rest.startswith(label):
            out.append((i + 1, rest[len(label):]))
    return out


def away_stop_merge_lines(data):
    """D3 — the departure file's merge-stop lines: (entries, malformed).
    entries: [(line number, key, kind, (subject, …), word)] for each line in
    the fixed form, word one of pre-approved | around | park; malformed: the
    line numbers of every OTHER line that begins `Stop: merge` — the label
    followed by anything but a name character, so `Stop: merge-queue setup`
    names another act and is not of this kind. A malformed line is never read
    as no listing: the callers warn (`merge-stop-malformed`) and refuse
    (`departure-stop-malformed`)."""
    entries, malformed = [], []
    for n, rest in away_departure_lines(data, AWAY_STOP_MERGE_LABEL):
        if re.match(r"[A-Za-z0-9_-]", rest[:1]):
            continue
        m = _AWAY_STOP_MERGE_RE.match(rest)
        subjects = tuple(m.group(3).split(",")) if m else ()
        if m is None or not all(repo_rel_path_ok(s) for s in subjects):
            malformed.append(n)
        else:
            entries.append((n, m.group(1), m.group(2), subjects, m.group(4)))
    return entries, malformed


def away_departure_has_fallback(data):
    """D5 — does the departure file answer the usage fallback: at least one
    `Usage fallback:` line with something after the colon? A presence test
    only (D19). A line with nothing after the colon is not an answer, so a
    file holding only such lines reads as missing — the refusing side."""
    return any(rest.strip() for _n, rest in away_departure_lines(data, AWAY_FALLBACK_LABEL))


def away_departure_warnings(data):
    """The effective set block = the LAST item 7 heading at level 2 or 3 (a
    Widened section's `### 7.` included — the authoritative set) to the next
    heading of equal or higher level; fenced blocks (_QB_FENCE_RE, the
    quoted-block reader's fence rules) are skipped as headings AND as bullet
    text; a bullet = its `- ` line plus every following blank, indented, or
    nested-bullet line (a wrapped bullet; a production path's `blob` /
    `heading` sub-lines) up to the next bullet at the list's indent or a
    non-indented paragraph line. Predicate: for each backtick token on the
    joined bullet take its FIRST whitespace-delimited word — the path in both
    layouts, `` `docs/x.md` `` and `` `docs/x.md <40-hex>` `` — and warn when
    that word ends in `.md` and the bullet has no `heading` substring: one
    `markdown-without-heading file=<path>` per distinct path, the path printed
    only when it matches the hold path alphabet (HOLD_PATH_RE), else
    `file=<unprintable, line N>` (N = the bullet's first line);
    `item7-section-not-found` when no block exists. v46.4 (D6), beside that
    scan and sharing its fence handling: EVERY line of the file outside a
    fenced block — not item 7 alone, a quoted procedure is also written as
    prose — is read by _away_heading_holds_quote, and each line that quotes a
    heading holding a double quote adds one `heading-has-double-quote
    line=<N>` (N = the line's number in the file; one per line), after the
    item-7 warnings and in line order. Returns the warning texts (without the
    caller's `away-warning: ` / `away-lint: ` prefix); `away grant` and `away
    lint` both print them, and neither is refused by one.
    v47.0 (plan-loop-autonomy-group-2 D3 / D5), two more words, from the
    departure-line reader below: `usage-fallback-missing`, FIRST, when the
    file holds no answered `Usage fallback:` line — the one word `away grant`
    never prints, because it REFUSES such a file before its warning loop
    (`departure-missing-fallback`; `away lint` prints the word and exits 0);
    and, LAST and in line order, one `merge-stop-malformed line=<N>` per line
    that begins `Stop: merge` and is not in the fixed form — a warning here as
    every other, and a refusal of every away merge start while it stands
    (away_merge_listing_refusal)."""
    text, fenced, heads = _away_departure_scan(data)
    lead = [] if away_departure_has_fallback(data) else ["usage-fallback-missing"]
    tail = ["merge-stop-malformed line=%d" % n for n in away_stop_merge_lines(data)[1]]
    # v46.4 D6: the line-by-line read — every line outside a fence, wherever it sits
    quoted = ["heading-has-double-quote line=%d" % (i + 1) for i, line in enumerate(text)
              if not fenced[i] and _away_heading_holds_quote(line)]
    item7 = [(i, lvl) for i, lvl, t in heads if lvl in (2, 3) and _AWAY_ITEM7_RE.match(t)]
    if not item7:
        return lead + ["item7-section-not-found"] + quoted + tail
    start, level = item7[-1]
    end = next((j for j, lvl, _t in heads if j > start and lvl <= level), len(text))
    bullets, cur, indent = [], None, None   # [first line no (1-based), joined text]
    for i in range(start + 1, end):
        if fenced[i]:
            continue
        line = text[i]
        m = _AWAY_BULLET_RE.match(line)
        if m:
            ind = len(m.group(1).expandtabs(4))
            if indent is None or ind <= indent:
                cur = [i + 1, line]
                bullets.append(cur)
                indent = ind
                continue
        if cur is not None and (m or not line.strip() or line[:1] in (" ", "\t")):
            cur[1] += "\n" + line   # a continuation: a nested bullet, a blank, or an indented line
        elif line.strip():
            cur = None            # a non-indented paragraph line ends the bullet
    out, seen = [], set()
    for lineno, body in bullets:
        if "heading" in body:
            continue
        for tm in _AWAY_TICK_RE.finditer(body):
            words = tm.group(1).split()
            if not words or not words[0].endswith(".md"):
                continue
            shown = "file=%s" % words[0] if HOLD_PATH_RE.match(words[0]) else "file=<unprintable, line %d>" % lineno
            if shown not in seen:
                seen.add(shown)
                out.append("markdown-without-heading %s" % shown)
    return lead + out + quoted + tail


def _away_policy_lines(data):
    """A policy log's bytes as the state function reads them: UTF-8 with
    replacement, universal newlines, each line keeping its terminator (what a
    text-mode readlines() returns) — shared by `_away_read_policy` and the
    census."""
    import io
    return io.TextIOWrapper(io.BytesIO(data), encoding="utf-8", errors="replace").readlines()


def _away_read_policy(path):
    """(lines, error) — a missing file is ([], None); any other read failure
    is (None, message). v37.0: the bytes come through _away_read_bytes
    (permissive profile), so a special file is (None, message), never a
    blocked open."""
    try:
        return _away_policy_lines(_away_read_bytes(path)), None
    except FileNotFoundError:
        return [], None
    except OSError as e:
        return None, str(e)


def _away_q(text):
    return str(text).replace('"', "'")


def _away_check_line(st, log_root, iso):
    """(state token, the one `away:` line) — the D4 output shape. `bound` only
    when the open grant's departure file exists and its digest equals the
    grant's departure=; otherwise departure-mismatch. v35.1 (Decision 5): on
    EVERY state the line carries ` holds=<n|unknown>` and, when n > 0,
    ` held="<hold_id> <class>[ path=<p>][; …]"` before ` reason=` — the run's
    open holds from the one fold, keyed by --iso."""
    state = st["state"]
    grants = st["grants"]
    g = st["open"] if state == "bound" else (grants[-1] if grants else None)
    reason = None
    if state == "bound":
        dig = _away_departure_digest(log_root, g["n"])
        if dig != g["kv"]["departure"]:
            state = "departure-mismatch"
            reason = ("departure file %s is missing or unreadable" % _away_departure_path(log_root, g["n"]) if dig is None
                      else "departure file %s digests to %s, the grant records %s" % (_away_departure_path(log_root, g["n"]), dig, g["kv"]["departure"]))
    elif state == "ended":
        reason = "grant %d ended at %s (reason=%s)" % (g["n"], g["end_kv"]["ts"], g["end_kv"]["reason"])
    elif state == "absent":
        reason = "no away-grant record in the policy log"
    else:
        reason = "policy log line %d: %s" % (st["bad"][0], st["bad"][2])
    out = "away: state=%s grants=%d" % (state, len(grants))
    if g is not None and state in ("bound", "departure-mismatch", "ended"):
        out += " grant=%d scope=%s departure=%s config_hash=%s ts=%s" % (
            g["n"], g["kv"]["scope"], g["kv"]["departure"], g["kv"]["config_hash"], g["kv"]["ts"])
    _hs, _hreason = _away_holds_suffix(log_root, iso)
    out += _hs
    if _hreason:
        reason = "%s; %s" % (reason, _hreason) if reason else _hreason
    # v44.0 D17: ` parks=` — the strict production-park fold (every state)
    _ps, _preason = _away_parks_suffix(log_root)
    out += _ps
    if _preason:
        reason = "%s; %s" % (reason, _preason) if reason else _preason
    # v44.0 D3: ` allows=` — the pre-approval fold, bound to the OPEN grant only
    # (every other state, departure-mismatch included, reads unknown)
    _as, _areason = _away_allows_suffix(log_root, g if state == "bound" else None)
    out += _as
    if _areason:
        reason = "%s; %s" % (reason, _areason) if reason else _areason
    if reason:
        out += ' reason="%s"' % _away_q(reason)
    return state, out


def _away_probe_log_names(log_root):
    """The `stage-<N>-probe.log` names directly under the log root, stage-
    ordered then by name: (names, problems) — problems names an unlistable
    root (v35.1: factored out of _away_probe_records for the hold fold)."""
    try:
        names = os.listdir(log_root)
    except OSError as e:
        return [], ["the log root %s could not be listed (%s) — no probe log was read" % (log_root, e)]
    return sorted((int(m.group(1)), nm) for nm in names for m in [PROBE_LOG_NAME_RE.match(nm)] if m), []


def _away_probe_records(log_root):
    """Every OWNERSHIP line of every `stage-<N>-probe.log` directly under the
    log root, stage-ordered then append-ordered: (records, problems) with
    records [(raw, (file name, line no))] and problems naming every input
    that could not be read — the report prints them, so a "none" section is
    never an all-clear built on evidence it never saw."""
    logs, problems = _away_probe_log_names(log_root)
    if problems:
        return [], problems
    out = []
    for _num, nm in logs:
        try:
            # v37.0: bytes through the one reader (a special file is a problem);
            # the decoding and the line split are unchanged
            lines = _away_read_bytes(os.path.join(log_root, nm)).decode("utf-8", "replace").splitlines()
        except OSError as e:
            problems.append("probe log %s could not be read (%s) — its records are missing from every section" % (nm, e))
            continue
        for i, raw in enumerate(lines, 1):
            if raw.startswith("OWNERSHIP:"):
                out.append((raw, (nm, i)))
    return out, problems


def _away_window(g):
    start = parse_iso(g["kv"]["ts"])
    end = parse_iso(g["end_kv"]["ts"]) if g["end_kv"] is not None else None
    return start, end


def _away_in_window(t, g):
    start, end = _away_window(g)
    return t is not None and start is not None and t >= start and (end is None or t <= end)


def _away_item(kv, loc, extra=""):
    parts = [kv.get("ts", "?"), kv.get("run", "?")]
    for k in ("key", "path", "choice", "hold_id", "clears", "rec", "smoke_by", "cell", "verdict"):
        if k in kv:
            parts.append("%s=%s" % (k, kv[k]))
    text = "- " + " · ".join(parts)
    if extra:
        text += " — " + extra
    if kv.get("detail"):
        text += " — %s" % kv["detail"]
    if loc is not None:
        text += " (%s:%d)" % loc
    return text


def _away_act_class(key):
    cm = AWAY_KEY_CLASS_RE.match(key or "")
    return cm.group(1) if cm else None


def away_release_pairing(events):
    """v35.0 A9 / Decision 15 — THE one start/outcome pairing owner, shared by
    the report's section 6 and emit's record-before-act warning. `events` are
    away-pair release records (kv dicts) in append order, already admitted by
    the caller. The identity is (run, key, away number, away_check, path) — the
    grant is part of it, so a start under another grant never pairs with this
    grant's outcome, and `path=` (absent is its own value) keeps two same-class
    paths of one merge apart. Only choice=start|done|failed are events; any
    other choice= is ignored. Returns (open, no_start, late): the indices of
    starts with no later outcome for their identity (every release class, as
    before); of act-class outcomes whose most recent prior event for their
    identity is not a start; and of LATE starts — a start written after a
    no-start outcome of its identity with an event time (ts=, via
    --event-ts) strictly before that outcome's: it answers that outcome,
    opens nothing, and leaves the outcome's flag in place (round 7 MED-001)."""
    last, open_at, no_start, late = {}, {}, set(), set()
    for i, kv in enumerate(events):
        ident = (kv.get("run"), kv.get("key"), parse_count(kv.get("away", "")),
                 kv.get("away_check"), kv.get("path"))
        choice = kv.get("choice")
        if choice == "start":
            prev = last.get(ident)
            t = parse_iso(kv.get("ts"))
            if (prev is not None and prev[1] in no_start and t is not None
                    and prev[2] is not None and t < prev[2]):
                late.add(i)
                last[ident] = ("late-start", i, None)
                continue
            open_at[ident] = i
            last[ident] = (choice, i, t)
        elif choice in ("done", "failed"):
            if (last.get(ident) or ("",))[0] != "start" and _away_act_class(kv.get("key")) in AWAY_ACT_CLASSES:
                no_start.add(i)
            open_at.pop(ident, None)
            last[ident] = (choice, i, parse_iso(kv.get("ts")))
    return set(open_at.values()), no_start, late


def away_outcome_without_start(log_path, runkey, kv):
    """v35.0 A9 / D8 — emit's warning check: True when `kv` (an act-class
    outcome carrying the away pair) would be flagged by away_release_pairing
    over the prior log filtered to writer-valid auto-/gate-disposition records
    with the SAME away pair (PR-MED-006). Advisory: the report additionally
    joins the grant, its window, and the unmatched filter, which emit cannot
    (no policy log) — where they differ the report is authoritative. A log
    that does not exist yet holds no start; one that cannot be read yields no
    warning (never a refusal)."""
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        lines = []
    except OSError:
        return False
    want = (parse_count(kv.get("away", "")), kv.get("away_check"))
    events = []
    for raw in lines:
        if not raw.startswith("OWNERSHIP:"):
            continue
        pkv, bare = parse_kv(raw[len("OWNERSHIP:"):])
        sub = bare[0] if bare else ""
        if (sub not in ("auto-disposition", "gate-disposition") or pkv.get("run") != runkey
                or pkv.get("key") != kv.get("key") or "away" not in pkv
                or (parse_count(pkv["away"]), pkv.get("away_check")) != want):
            continue
        if emittable_record(raw, "OWNERSHIP:" + sub)[2] is None:
            events.append(pkv)
    events.append(dict(kv, run=runkey))
    return (len(events) - 1) in away_release_pairing(events)[1]


# --- v35.1 Decisions 1–5: the raw probe-log reader, the CI verdict, the hold --

# the marker a raw reader looks for ANYWHERE in a physical line: `OWNERSHIP:`,
# optional whitespace, the subtype token, then not a token character
_MARKER_RES = {}


def _marker_re(sub):
    if sub not in _MARKER_RES:
        _MARKER_RES[sub] = re.compile(r"OWNERSHIP:\s*%s(?![A-Za-z0-9_-])" % re.escape(sub))
    return _MARKER_RES[sub]


# the line-start prefixes of the helper's own record families — a line that
# starts with one, re-tokenizes cleanly, carries an EVEN number of double
# quotes, and mentions a marker ONLY inside a double-quoted value is that
# family's record quoting data, never a record of the marker's subtype
# (round 10 LOW-4). A narration line, or a record merged onto a predecessor
# torn OUTSIDE a quote, has the marker outside any quoted value; a record
# merged onto a predecessor torn INSIDE an open quote has the marker swallowed
# into that value — a merged record with no quoted value leaves the marker in
# no span at all, one whose quoted value abuts the swallowed closing quote
# fails the rejoin, and the odd quote count catches every shape, because the
# writer never emits a `"` inside a value (Step H rounds 23–24).
RECORD_PREFIXES = tuple("%s:" % t for t in ENUMS["JOURNAL_TYPES"]) + ("ROLE:", "Wake:", "WATCH:", "MONITOR:", "DELEGATION:", "Loop config:")


def _marker_quoted_only(text, sub):
    spans = [m.span(2) for m in PARSE_KV_RE.finditer(text) if m.group(1) is not None]
    return all(any(a <= mm.start() and mm.end() <= b for a, b in spans) for mm in _marker_re(sub).finditer(text))


def _strict_decode(b):
    """str when the physical line is strict UTF-8, else the raw BYTES (round 9
    LOW-005): an undecodable line is judged by its bytes — a marker found in
    them makes it a doubtful line of that subtype, no marker means it is
    not that subtype's line at all."""
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b


def _marker_in(text, sub):
    """Does the physical line (str or undecodable bytes) carry the
    `OWNERSHIP: <sub>` marker anywhere? Bytes are searched through a
    replacement decode with the SAME text regex (a replacement character can
    never complete a match, and `\\s*` keeps its Unicode meaning — round 10
    LOW-3)."""
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    return text is not None and _marker_re(sub).search(text) is not None


def raw_record_lines(path, missing_is_error=False):
    """Decision 5's RAW probe-log reader, shared by every reader that admits,
    parks, or clears (the hold fold, the CI-history classifier, the late-start
    exemption, the post-verdict scan). The input is BYTES split on LF only; a
    CR is removed only when it directly precedes that LF (a CRLF terminator);
    a final unterminated fragment is kept exactly as it is; each physical line
    is decoded STRICTLY — an undecodable line stays bytes. Never `splitlines()`
    (U+2028 / U+0085 / a lone CR would split a damaged record into a clean-
    looking prefix) and never `errors="replace"`. Returns (lines, error): an
    unreadable file is (None, message); a MISSING file is ([], None) for the
    callers that may run before an emission log exists (the merge-start
    reads, the verb's post-write settlement) — and (None, message) under
    `missing_is_error=True`, which the hold fold passes because it has
    already DISCOVERED the name in the directory listing: a dangling
    `stage-<N>-probe.log` symlink, or a log removed between the listing and
    the open, must never read as an empty log (round 11 PR-MED-1101). v37.0:
    the bytes come through _away_read_bytes (permissive profile), so a special
    file is (None, message) like any other unreadable file."""
    try:
        data = _away_read_bytes(path)
    except FileNotFoundError as e:
        if missing_is_error:
            return None, "listed but could not be opened (%s)" % e.__class__.__name__
        return [], None
    except OSError as e:
        return None, str(e)
    pieces = data.split(b"\n")
    last = pieces.pop()  # after the final LF: b"" when terminated, else the torn fragment
    out = []
    for p in pieces:
        if p.endswith(b"\r"):
            p = p[:-1]
        out.append(_strict_decode(p))
    if last:
        out.append(_strict_decode(last))
    return out, None


def raw_record_valid(text, family):
    """Whole-line, BYTE-ONLY validity (Decision 5): the physical line is first
    checked WHOLE with the writer's own assembled_line_ok (emittable_record
    itself trims a trailing CR/LF, so a line with extra CRs before its LF
    would otherwise pass), then the writer's predicate with only its clock-
    relative future-time check skipped. Returns (kv, None) when the writer
    could have emitted it, else (None, reason). No reader normalisation can
    turn a line the writer would refuse into valid evidence."""
    if isinstance(text, bytes):
        return None, "undecodable physical line (not strict UTF-8)"
    why = assembled_line_ok(text)
    if why:
        return None, why
    kv, _bare, why = emittable_record(text, family, byte_only=True)
    return (kv, None) if why is None else (None, why)


def raw_classify(text, sub):
    """Classify-before-filtering (Decision 5): None when the physical line
    carries no `OWNERSHIP: <sub>` marker, or is a writer-valid OWNERSHIP /
    ROLE record of ANOTHER subtype that merely mentions the marker (in a
    quoted detail=, say); otherwise (kv, None) for a writer-valid <sub>
    record, or (None, reason) for a DOUBTFUL one — torn, merged onto a torn
    predecessor, separator-damaged, undecodable, or with a missing, malformed,
    or duplicated identity. A doubtful line is judged by its caller toward
    the fail-closed side, never dropped. An undecodable line is judged by
    its BYTES: with the marker it is doubtful, without it it is not this
    subtype's line (round 9 LOW-005)."""
    if not _marker_in(text, sub):
        return None
    if isinstance(text, bytes):
        return None, "undecodable physical line (not strict UTF-8)"
    # the exemptions apply only to a line the writer could have shaped: one
    # that re-tokenizes cleanly AND carries an even number of `"` — a merged
    # line whose predecessor tore inside an open quote is odd, whatever the
    # rejoin says (Step H round 23)
    if assembled_line_ok(text) is None and text.count('"') % 2 == 0:
        m = re.match(r"\A(OWNERSHIP|ROLE): ([A-Za-z0-9_-]+) ", text)
        if m and not (m.group(1) == "OWNERSHIP" and m.group(2) == sub):
            if emittable_record(text, "%s:%s" % (m.group(1), m.group(2)), byte_only=True)[2] is None:
                return None
        # any OTHER record family (a SPAWN: or VERIFY_FAIL: narrating a helper
        # refusal, say) that quotes the marker as data inside a value
        if not text.startswith("OWNERSHIP:") and text.startswith(RECORD_PREFIXES) and _marker_quoted_only(text, sub):
            return None
    return raw_record_valid(text, "OWNERSHIP:" + sub)


def raw_dispositions(lines):
    """Every auto-/gate-disposition line raw_classify recognises, in append
    order (text-major, subtype-minor): (subtype, kv) for a writer-valid one,
    (subtype, None) for a DOUBTFUL one. The ONE scanner Decision 3's two
    readers share — condition 6's post-verdict scan and the late-start
    exemption — so "which lines are dispositions" is spelled once (Step H
    round 25, SIMP-001). away_outcome_without_start, the v35.0 advisory
    reader, keeps its own path by design."""
    for text in lines:
        for sub in ("auto-disposition", "gate-disposition"):
            r = raw_classify(text, sub)
            if r is not None:
                yield sub, r[0]


# --- the gh runner (Decision 2) ---
GH_DEADLINE_S = 90          # ONE total deadline shared by the three reads, under a host's 120 s tool timeout
GH_SCRUB_ENV = ("GH_REPO", "GH_HOST", "GH_FORCE_TTY", "GH_PAGER", "PAGER", "CLICOLOR_FORCE")
GH_PR_FIELDS = "url,state,headRefName,headRefOid,baseRefName,mergeable,statusCheckRollup"
# the pull request's own url, ASCII classes only (a JSON escape can smuggle a
# NUL or a surrogate into a looser class — round 9 LOW-012); https only, the
# one scheme gh emits and the one _ci_rerun_ids anchors run ids under (Step H
# round 22 LOW: one scheme rule for the url and the rerun= prefix). No
# segment starts with `-` (an option-looking value) and neither owner nor
# repo is a bare `.` or `..` (a path-climbing API segment) — a `.github`
# repository still matches (Step H round 26, SEC-001; defence in depth: gh
# never emits such a url, and the API path is one argv element).
PR_URL_RE = re.compile(r"\Ahttps://(?!-)([A-Za-z0-9.:_-]+)/(?!-)(?!\.\.?/)([A-Za-z0-9._-]+)/(?!-)(?!\.\.?/)([A-Za-z0-9._-]+)/pull/[0-9]+\Z")
CI_VERDICT_FRESH_S = 15 * 60  # Decision 3 condition 3: at most 15 minutes before the tool clock
CI_VERDICT_FUTURE_S = 60      # ... and at most 60 s after it
CI_SETTLE_S = 120             # Decision 1: a no-checks streak settles at 120 s
CI_NAME_LIMIT = 80            # the sanitise helper's per-name cap
CI_DETAIL_LIMIT = 400         # ... and the whole detail= cap
CI_TOKEN_LIMIT = 256          # an unquoted identity token on the stdout line (a git ref fits whole)
CI_REASON_NAMES = 8           # how many check names a failed / pending reason lists
HOLD_ID_BYTES = 6             # secrets.token_hex(6) = the 12-hex hold_id shape (HEX12_RE)
GH_MISSING_SENTINEL = os.path.join(os.sep, "nonexistent", "gh-not-on-path")  # an absolute path that cannot start


def gh_executable():
    """The gh to run: LOOP_JOURNAL_GH (an ABSOLUTE path to an executable —
    anything else is a usage refusal; the selftest's and rehearsal leg A's
    stub hook, LOOP_JOURNAL_NOTICE_CMD's precedent) or `gh` resolved from
    PATH here, never by the child relative to --base (round 9 LOW-014).
    Returns (executable, override)."""
    ov = os.environ.get("LOOP_JOURNAL_GH")
    if ov is None:
        # ABSOLUTE, or a path that cannot exist — never a bare `gh` or a
        # relative `bin/gh` the child would resolve against --base (round 10 LOW-2)
        found = shutil.which("gh")
        return (os.path.abspath(found) if found else GH_MISSING_SENTINEL), False
    if not os.path.isabs(ov) or not os.path.isfile(ov) or not os.access(ov, os.X_OK):
        refuse("LOOP_JOURNAL_GH=%r must be an absolute path to an executable (the gh stub hook); unset it to run the real gh" % ov[:80])
    return ov, True


def gh_argv(kind, pr=None, host=None, owner=None, repo=None, tip=None):
    """The runner BUILDS the argv from a kind — there is no argv parameter, so
    no caller-supplied command can run (Critical Constraint 3): never
    --method, -f/-F, --input, or a write subcommand."""
    if kind == "pr":
        return ["gh", "pr", "view", str(pr), "--json", GH_PR_FIELDS]
    if kind in ("check-runs", "status"):
        return ["gh", "api", "--hostname", host, "--paginate", "--slurp",
                "repos/%s/%s/commits/%s/%s" % (owner, repo, tip, kind)]
    raise ValueError("unknown gh read kind %r" % (kind,))


def gh_env():
    """The caller's environment minus the keys that could redirect a read
    (GH_REPO / GH_HOST steer the repository and host; the pager / colour
    keys alter stdout), plus GH_PROMPT_DISABLED=1."""
    env = {k: v for k, v in os.environ.items() if k not in GH_SCRUB_ENV}
    env["GH_PROMPT_DISABLED"] = "1"
    return env


def run_gh(kind, exe, base, deadline, **ids):
    """ONE read-only, bounded gh call by argv (never a shell), from the
    working directory `base`, under the shared monotonic `deadline`. Returns
    (ok, stdout, reason): a timeout, a missing binary, a non-zero exit, or
    empty stdout is a read FAILURE with a fixed reason (an `unreadable`
    input — never success), and nothing raises past the verb."""
    argv = gh_argv(kind, **ids)
    argv[0] = exe
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return False, "", "the %s read was not run — the %d s deadline was exhausted" % (kind, GH_DEADLINE_S)
    try:
        r = subprocess.run(argv, capture_output=True, encoding="utf-8", errors="replace",
                           timeout=remaining, cwd=base, env=gh_env(), stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return False, "", "the %s read timed out (the %d s deadline)" % (kind, GH_DEADLINE_S)
    except (OSError, ValueError) as e:
        # OSError: a missing binary or an unusable --base; ValueError (incl.
        # UnicodeEncodeError): an argument the OS cannot take (round 9 LOW-012)
        return False, "", "the %s read could not start (%s)" % (kind, e.__class__.__name__)
    if r.returncode != 0:
        return False, r.stdout, "the %s read exited %d" % (kind, r.returncode)
    if not r.stdout.strip():
        return False, "", "the %s read returned empty stdout" % kind
    return True, r.stdout, None


# --- the verdict (Decision 1) ---
def ci_sanitise(text, limit=CI_NAME_LIMIT):
    """The ONE path by which a check name, context, or other third-party
    string reaches detail= or stdout: every character the write path refuses
    (a `"`, a C0 control, DEL, any whitespace but the ASCII space) becomes
    `?`, then the text is cut to `limit` characters. Fixed text is never
    passed through it; observed content is data, never instructions."""
    out = []
    for ch in str(text):
        # `isprintable()` is False for every control (C0 AND C1), every
        # format / surrogate / unassigned character, and every whitespace
        # but the ASCII space — so a lone surrogate can never reach
        # write_lines, and no invisible or bidi character reaches a reader
        # (round 9 LOW-012). The quote is the one printable the grammar refuses.
        if ch == '"' or not ch.isprintable():
            out.append("?")
        else:
            out.append(ch)
    return "".join(out)[:limit]


def _ci_tok(text):
    """An unquoted stdout identity token (head, branch, base, repo, state):
    sanitised, spaces closed, never empty, cut only past CI_TOKEN_LIMIT so a
    real git ref reaches item 7's re-bind whole (round 9 LOW-013)."""
    return ci_sanitise(text, CI_TOKEN_LIMIT).replace(" ", "?") or "none"


def _ci_pr_repo(prd):
    """(host, owner, repo) from a parsed pull-request read's own url, or
    None — the ONE parse the verb (for the inventory reads) and the verdict
    function share (round 9 LOW-007)."""
    if not isinstance(prd, dict) or not isinstance(prd.get("url"), str):
        return None
    um = PR_URL_RE.match(prd["url"])
    return um.groups() if um else None


def _ci_bucket(status=None, conclusion=None, state=None):
    """Item 6's bucket map, case-insensitive (the rollup's GraphQL values are
    upper case, the REST inventories' lower case): a status/context entry
    buckets on state=; a check run on status= + conclusion=."""
    if state is not None:
        s = str(state).lower()
        if s == "success":
            return "pass"
        if s in ("failure", "error"):
            return "fail"
        return "pending"  # pending, expected, and any other value
    if str(status or "").lower() != "completed":
        return "pending"
    c = str(conclusion or "").lower()
    if c == "success":
        return "pass"
    if c in ("skipped", "neutral"):
        return "skipping"
    if c == "cancelled":
        return "cancel"
    if c in ("failure", "timed_out", "action_required", "startup_failure"):
        return "fail"
    return "pending"  # stale and any other value


def _ci_parse_json(ok, text):
    """(parsed, reason): a failed read, or stdout that is not JSON, parses to
    nothing — an `unreadable` input."""
    if not ok:
        return None, None
    try:
        return json.loads(text), None
    except (ValueError, RecursionError):  # not JSON, or nested past the interpreter's limit (round 9 LOW-012)
        return None, "stdout is not JSON"


def _ci_inventory(pages, kind):
    """One commit-bound inventory from its --slurp pages: (entries, reason)
    with entries [(name, bucket, url)] — EVERY entry that parsed, so step 2's
    fail/cancel scan sees a failing check even in an incomplete read (round 9
    MED-002) — and reason None only when the read is COMPLETE: a list of
    objects, each page with one agreed total_count, each entry an object with
    its name, and the summed entries == total_count."""
    if not isinstance(pages, list) or not pages:
        return [], "the %s read did not parse as a list of pages" % kind
    field = "check_runs" if kind == "check-runs" else "statuses"
    name_key = "name" if kind == "check-runs" else "context"
    total, entries, reason = None, [], None
    for page in pages:
        if not isinstance(page, dict) or not isinstance(page.get("total_count"), int) or isinstance(page.get("total_count"), bool):
            reason = reason or "a %s page lacks total_count" % kind
            if not isinstance(page, dict):
                continue
        elif total is None:
            total = page["total_count"]
        elif page["total_count"] != total:
            reason = reason or "the %s pages disagree on total_count" % kind
        items = page.get(field)
        if not isinstance(items, list):
            reason = reason or "a %s page lacks its %s list" % (kind, field)
            continue
        for it in items:
            if not isinstance(it, dict) or not isinstance(it.get(name_key), str):
                reason = reason or "a %s entry lacks its %s" % (kind, name_key)
                continue
            if kind == "check-runs":
                b = _ci_bucket(status=it.get("status"), conclusion=it.get("conclusion"))
                url = it.get("details_url")
            else:
                b = _ci_bucket(state=it.get("state"))
                url = ""  # a commit status's target_url never feeds rerun= (round 9 MED-001)
            entries.append((it[name_key], b, url if isinstance(url, str) else ""))
    if reason is None and len(entries) != total:
        reason = "the %s read is not complete — %d entries against total_count=%d" % (kind, len(entries), total)
    return entries, reason


def _ci_rollup(rollup):
    """The pull request's statusCheckRollup: (entries, reason) with entries
    [(name, bucket, url)] — a CheckRun on status/conclusion with its
    detailsUrl, a StatusContext on state with NO url (a status never feeds
    rerun= — round 9 MED-001); any other shape is unreadable."""
    if not isinstance(rollup, list):
        return None, "statusCheckRollup is not a list"
    out = []
    for e in rollup:
        if not isinstance(e, dict):
            return None, "a rollup entry is not an object"
        tn = e.get("__typename")
        if tn == "StatusContext" or (tn is None and "context" in e):
            name = e.get("context")
            b = _ci_bucket(state=e.get("state"))
            url = ""
        else:
            name = e.get("name")
            b = _ci_bucket(status=e.get("status"), conclusion=e.get("conclusion"))
            url = e.get("detailsUrl")
        if not isinstance(name, str):
            return None, "a rollup entry lacks its name"
        out.append((name, b, url if isinstance(url, str) else ""))
    return out, None


def _ci_rerun_ids(entries, host, owner, repo):
    """The run ids item 8 may re-run (`gh run rerun <id> --failed` is a
    WRITE): one anchored id per failing CheckRun url, admitted only under
    `https://<host>/<owner>/<repo>/actions/runs/` built from the pull
    request's OWN url — never from a status, never from another repository,
    never from a substring (round 9 MED-001)."""
    prefix = "https://%s/%s/%s/actions/runs/" % (host, owner, repo)
    ids = []
    for _n, _b, url in entries:
        if not url.startswith(prefix):
            continue
        m = re.match(r"\A([0-9]+)(?:[/?#]|\Z)", url[len(prefix):])
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


def ci_verdict(pr_read, cr_read, st_read, tip):
    """Decision 1 — ONE pure verdict function, no I/O. Each read is (ok,
    stdout, reason) from run_gh. Returns a dict: verdict (CI_VERDICTS),
    head, checks (the inventory entry count), rerun (run ids), reason (fixed
    text + sanitised names), and the pull request's state / branch / base /
    mergeable / repo for the stdout line ("none" when unread). `unreadable`
    is the DEFAULT: nothing short of complete, parsed, consistent reads
    produces `passed` or `no-checks` (Critical Constraint 2)."""
    meta = {"head": "none", "state": "none", "branch": "none", "base": "none", "mergeable": "none", "repo": "none"}

    def out(verdict, reason, checks=0, rerun=()):
        return dict(meta, verdict=verdict, reason=reason, checks=checks, rerun=list(rerun))

    # 1. the pull request
    pr_ok, pr_text, pr_why = pr_read
    prd, why = _ci_parse_json(pr_ok, pr_text)
    if not pr_ok:
        return out("unreadable", "pull-request read failed: %s" % pr_why)
    if why or not isinstance(prd, dict):
        return out("unreadable", "pull-request read did not parse")
    for k in ("url", "state", "headRefName", "headRefOid", "baseRefName", "mergeable"):
        if not isinstance(prd.get(k), str):
            return out("unreadable", "pull-request read lacks %s" % k)
    ident = _ci_pr_repo(prd)
    if ident is None:
        return out("unreadable", "pull-request url yields no host/owner/repo")
    host, owner, repo = ident
    meta.update(head=_ci_tok(prd["headRefOid"]), state=_ci_tok(prd["state"]), branch=_ci_tok(prd["headRefName"]),
                base=_ci_tok(prd["baseRefName"]), mergeable=_ci_tok(prd["mergeable"]),
                repo=_ci_tok("%s/%s/%s" % ident))
    if prd["state"] != "OPEN":
        return out("unreadable", "pull request state=%s, not OPEN" % _ci_tok(prd["state"]))
    if prd["headRefOid"] != tip:
        return out("unreadable", "head-moved: the pull request head is %s, not the checked tip" % meta["head"])
    rollup, roll_why = _ci_rollup(prd.get("statusCheckRollup"))
    if roll_why:
        return out("unreadable", roll_why)
    # the inventories — parsed where they parse, so a fail in either read counts
    cr_ok, cr_text, cr_why = cr_read
    st_ok, st_text, st_why = st_read
    crp, _w1 = _ci_parse_json(cr_ok, cr_text)
    stp, _w2 = _ci_parse_json(st_ok, st_text)
    cr_entries, cr_reason = (_ci_inventory(crp, "check-runs") if cr_ok and _w1 is None
                             else ([], cr_why or _w1 or "the check-runs read failed"))
    st_entries, st_reason = (_ci_inventory(stp, "status") if st_ok and _w2 is None
                             else ([], st_why or _w2 or "the status read failed"))
    parsed = list(rollup) + cr_entries + st_entries
    inventory = cr_entries + st_entries
    checks = len(inventory)
    # 2. failed on any fail or cancel in any read that parsed — an incomplete
    # inventory's parsed entries included (round 9 MED-002)
    bad = [e for e in parsed if e[1] in ("fail", "cancel")]
    if bad:
        return out("failed", "failed: %s" % ", ".join(ci_sanitise(n) for n, _b, _u in bad[:CI_REASON_NAMES]), checks,
                   _ci_rerun_ids(bad, host, owner, repo))
    # 3. unreadable on an incomplete or inconsistent inventory
    if cr_reason:
        return out("unreadable", "check-runs inventory: %s" % cr_reason, checks)
    if st_reason:
        return out("unreadable", "status inventory: %s" % st_reason, checks)
    names = set(n for n, _b, _u in inventory)
    absent = [n for n, _b, _u in rollup if n not in names]
    if absent:
        return out("unreadable", "rollup name absent from the inventory: %s" % ci_sanitise(absent[0]), checks)
    # 4. pending
    pend = [e for e in parsed if e[1] == "pending"]
    if pend:
        return out("pending", "pending: %s" % ", ".join(ci_sanitise(n) for n, _b, _u in pend[:CI_REASON_NAMES]), checks)
    # 5. passed — the inventory has >= 1 pass and every entry (inventory and rollup) is pass or skipping
    if any(b == "pass" for _n, b, _u in inventory) and all(b in ("pass", "skipping") for _n, b, _u in parsed):
        return out("passed", "every entry pass or skipping (%d pass)" % sum(1 for _n, b, _u in inventory if b == "pass"), checks)
    # 6. no-checks — nothing ran, or everything was skipped (D9 (c))
    if not inventory and not rollup:
        return out("no-checks", "no check run, status, or rollup entry for the tip", 0)
    if parsed and all(b == "skipping" for _n, b, _u in parsed):
        return out("no-checks", "every entry skipped (%d)" % len(parsed), checks)
    return out("unreadable", "inconsistent reads — the inventory and the rollup disagree", checks)


# --- the CI history, settlement, and the merge-start admission (Decisions 1, 3) ---
def ci_history(lines, runkey):
    """Decision 1's ONE CI-history classifier over the raw reader's lines:
    [(line index, kv or None)] in append order — a verdict line recognised
    by its marker anywhere BEFORE any run= filter; a writer-valid line of
    another run= is foreign and ignored; a writer-invalid one (torn, merged,
    damaged, or with a missing / malformed / duplicated run=) is DOUBTFUL
    (kv None) — as the latest entry it refuses admission, inside a streak it
    breaks the streak; the next writer-valid read supersedes it."""
    out = []
    for i, text in enumerate(lines):
        r = raw_classify(text, "ci-verdict")
        if r is None:
            continue
        kv, _why = r
        if kv is not None and kv.get("run") != runkey:
            continue
        out.append((i, kv))
    return out


def ci_settled(history, tip):
    """Decision 1's shared `settled`: the unbroken TRAILING streak of eligible
    records — writer-valid, unstamped (no gh=override), naming `tip`, reading
    no-checks — spans >= 120 s. An ineligible latest entry means no streak
    at all, never a skip to older evidence. Used by the verb (over the log
    as written) and the refusal (over the same log) alike."""
    streak = []
    for _i, kv in reversed(history):
        if kv is None or "gh" in kv or kv.get("tip") != tip or kv.get("verdict") != "no-checks":
            break
        streak.append(kv)
    if not streak:
        return False
    t_last, t_first = parse_iso(streak[0].get("ts")), parse_iso(streak[-1].get("ts"))
    return t_last is not None and t_first is not None and (t_last - t_first).total_seconds() >= CI_SETTLE_S


def ci_merge_start_refusal(lines, runkey, tip, ungated, now):
    """Decision 3's six admission conditions, in order, over the raw reader's
    lines; None when the away merge start is admitted, else the FIRST unmet
    condition as a reason. The clock is the tool's own `now`, never
    --event-ts."""
    hist = ci_history(lines, runkey)
    if not hist:
        return "no ci-verdict record for run=%s in this log — run the verdict first" % runkey
    idx, kv = hist[-1]
    if kv is None:
        return "the latest ci-verdict line is not one the writer could have emitted (torn, malformed, or a missing / duplicated run=) — run a fresh verdict"
    if kv.get("tip") != tip:
        return "the latest verdict names tip=%s, not this start's tip=%s" % (kv.get("tip", "")[:40], tip)
    t = parse_iso(kv.get("ts"))
    age = (now - t).total_seconds()
    if age > CI_VERDICT_FRESH_S:
        return "the latest verdict is %d s old — older than %d s; run a fresh one" % (age, CI_VERDICT_FRESH_S)
    if age < -CI_VERDICT_FUTURE_S:
        return "the latest verdict is %d s in the future of the tool clock (the bound is %d s)" % (-age, CI_VERDICT_FUTURE_S)
    v = kv.get("verdict")
    if v == "no-checks":
        if not ungated:
            return "the latest verdict is no-checks — a no-checks merge start carries ungated=merge (and the departure's `Ungated merge: merge`)"
        if not ci_settled(hist, tip):
            return "the latest verdict is no-checks but not yet settled — the trailing no-checks streak for this tip spans under %d s" % CI_SETTLE_S
    elif v != "passed":
        return "the latest verdict is %s — only passed, or settled no-checks with ungated=merge, admits a merge" % v
    if kv.get("gh") == "override":
        return "the latest verdict was produced through LOOP_JOURNAL_GH (gh=override) — a stubbed read never admits a merge"
    for sub, dkv in raw_dispositions(lines[idx + 1:]):
        if dkv is None:
            return "a doubtful %s line follows the latest verdict — it may be a release record; run a fresh verdict" % sub
        if dkv.get("run") == runkey and _away_act_class(dkv.get("key")) in AWAY_RELEASE_CLASSES:
            return ("a %s for key=%s choice=%s follows the latest verdict — one verdict admits one release record; run a fresh verdict"
                    % (sub, dkv.get("key", "")[:60], dkv.get("choice", "")[:30]))
    return None


def ci_late_start_refusal(lines, runkey, kv, event_ts):
    """D9 (b): --event-ts on an away merge start is admitted ONLY on a TRUE
    late start — the candidate lands in away_release_pairing's `late` set
    (the single pairing owner, never a second rule) over the log's writer-
    valid same-pair disposition events plus the candidate; ANY doubtful
    auto-/gate-disposition line in the log refuses the exemption outright.
    None when admitted (a record repair, without a verdict), else a reason."""
    want = (parse_count(kv.get("away", "")), kv.get("away_check"))
    events = []
    for sub, dkv in raw_dispositions(lines):
        if dkv is None:
            return "a doubtful %s line is in the log — the late-start exemption needs a wholly writer-valid disposition history" % sub
        if dkv.get("run") != runkey or "away" not in dkv:
            continue
        if (parse_count(dkv["away"]), dkv.get("away_check")) != want:
            continue
        events.append(dkv)
    events.append(dict(kv, run=runkey, ts=event_ts))
    if (len(events) - 1) not in away_release_pairing(events)[2]:
        return ("--event-ts on an away merge start is admitted only on a TRUE late start — one answering an outcome of its own "
                "identity (run, key, grant, path) recorded with no start, not yet answered, with a ts= strictly before it (D9 (b)); "
                "every other merge start is contemporaneous and needs a fresh verdict")
    return None


# --- the folds' RAW input path (Decision 5; v44.0 D2 / D17 share it) ---
def _away_raw_probe_lines(log_root, problems):
    """THE raw input path every fail-closed fold reads — the hold fold (v35.1),
    the pre-approval fold (v44.0 D2) and the strict production-park fold
    (v44.0 D17): every `stage-<N>-probe.log` directly under the root in stage
    order (an unlistable root → a problem, nothing yielded), each through
    raw_record_lines under its strict-missing profile — a DISCOVERED name that
    cannot be opened (missing, dangling, unreadable) is doubt appended to `problems`,
    never an empty log (round 11 PR-MED-1101) — and every physical line in
    order as (log name, line no, text-or-bytes). Never _away_probe_records:
    its replacement decode, `splitlines()`, and `OWNERSHIP:`-prefix filter
    would erase or split a damaged record before any validity check (that
    reader stays as it is for the report). Yields; `problems` is the caller's
    list, appended in reading order."""
    logs, listing = _away_probe_log_names(log_root)
    problems.extend(listing)
    for _num, nm in logs:
        lines, err = raw_record_lines(os.path.join(log_root, nm), missing_is_error=True)
        if lines is None:
            problems.append("probe log %s could not be read (%s)" % (nm, err))
            continue
        for i, text in enumerate(lines, 1):
            yield nm, i, text


def _away_text_has(text, sub):
    """Does the physical line (str or undecodable bytes) contain `sub` anywhere?
    Bytes are searched through a replacement decode (the _marker_in shape)."""
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    return text is not None and sub in text


# --- the hold fold (Decision 5) ---
def away_hold_fold(log_root, iso):
    """THE one fold owner (used by `away check` and `away report`): every
    stage probe log under the root, read through the RAW reader; a hold line
    is recognised by its marker anywhere, judged WHOLE with byte-only
    validity, and classified BEFORE filtering — a writer-valid record of
    another iso= is foreign and ignored; EVERY writer-invalid hold line
    (holds and clears alike — an invalid clear never clears) makes the count
    `unknown`, as does an unreadable log or root. The open set is ORDER-FREE:
    a hold is open unless a writer-valid clear for the same iso=, class, and
    path names its hold_id= in clears=. Returns (count or None for unknown,
    open [(hold_id, class, path, kv, loc)], clears [(kv, loc)], problems)."""
    if log_root is None:
        return None, [], [], ["no --log-root — the hold fold reads <log-root>/stage-<N>-probe.log"]
    unknown = []
    holds, clears = [], []
    for nm, i, text in _away_raw_probe_lines(log_root, unknown):
        r = raw_classify(text, "hold")
        if r is None:
            continue
        kv, why = r
        if kv is None:
            unknown.append("%s:%d is a hold line the writer could not have emitted (%s)" % (nm, i, why))
            continue
        if kv.get("iso") != iso:
            continue
        (holds if kv["choice"] == "hold" else clears).append((kv, (nm, i)))
    ids = [kv["hold_id"] for kv, _l in holds]
    for hid in sorted(set(h for h in ids if ids.count(h) > 1)):
        unknown.append("hold_id=%s names more than one hold — ambiguous identity" % hid)
    if unknown:
        return None, [], clears, unknown
    closed = set()
    for ckv, _cl in clears:
        for hkv, _hl in holds:
            if (hkv["hold_id"] == ckv["clears"] and _away_act_class(hkv["key"]) == _away_act_class(ckv["key"])
                    and hkv.get("path") == ckv.get("path")):
                closed.add(hkv["hold_id"])
    opens = [(hkv["hold_id"], _away_act_class(hkv["key"]), hkv.get("path"), hkv, loc)
             for hkv, loc in holds if hkv["hold_id"] not in closed]
    return len(opens), opens, clears, []


def _away_holds_suffix(log_root, iso):
    """` holds=<n|unknown>[ held="…"]` for the `away:` line, plus the unknown
    causes (joined) for its reason=."""
    n, opens, _c, problems = away_hold_fold(log_root, iso)
    out = " holds=%s" % ("unknown" if n is None else n)
    if n:
        out += ' held="%s"' % "; ".join("%s %s%s" % (hid, cls, " path=%s" % p if p else "")
                                       for hid, cls, p, _kv, _loc in opens)
    return out, ("holds unknown: " + "; ".join(problems)) if n is None else None


# --- the strict production-park fold (v44.0 D17) ---
_AWAY_OTHER_MARKERS = RECORD_PREFIXES + ("OWNERSHIP:", "SPAWN_WRAPPER_START")


def _away_doubtful_key(text, sub):
    """The ONE INTACT `key=` field of a doubtful `OWNERSHIP: <sub>` line, else
    None — positively established only when (round 12 PR-MED-1201, round 13
    PR-MED-1301): the line is strict text (an undecodable line's key bytes
    are never read as intact); its double-quote count is even (an odd count
    means a torn quoted value, so grammar and data cannot be told apart — the
    raw_classify parity gate); the physical line STARTS with the writer's
    exact prefix `OWNERSHIP: <sub> ` of the subtype being classified (so no
    predecessor fragment precedes the record — a record merged onto a torn
    predecessor is never attributed the predecessor's key); no OTHER record
    marker follows at the top level (a bare token starting a record family —
    `OWNERSHIP:`, `NOTIFY:`, `SPAWN:`, … — outside a quoted value: a merged
    successor or a both-marker line is never attributed); exactly one
    TOP-LEVEL `key=` field exists under the writer's own tokenization
    (PARSE_KV_RE — a `key=…` word inside a quoted value is data, never a
    field); and at least one token follows it (a key field that ENDS the
    line may itself be torn, `key=stage-2-deploy-prod`). Absent, duplicated,
    quoted, trailing, or unattributable reads None. The caller fails closed
    on None.
    Round 14 PR-MED-1401 — the class-closing rule: the text after the prefix
    is tokenized ONCE, and EVERY double quote in it must be a delimiter of a
    writer-shaped quoted FIELD value (`<key>="…"`, the opening quote right
    after the field's `=`); bare quoted prose, a separated `= "` boundary, or
    a quote inside a token leaves quotes unaccounted for → None. The marker
    exclusion and the key attribution then both read that one validated
    token list, so every remaining token is top-level by construction: a key
    can come neither from data, nor from another record on the line, nor
    from an unparseable span — only from the record's own syntactic field.
    Round 15 PR-MED-1501 — the writer's own LEXICAL owner gates everything
    above: the line must pass assembled_line_ok (the R28 round-trip identity
    — re-tokenizing with PARSE_KV_RE and rejoining on single spaces reproduces
    the line exactly, and no line terminator is present). PARSE_KV_RE is a
    scanner, not a boundary validator — a match may start at the character
    after a closing quote (`reason="r"key=stage-2-deploy-staging`, or
    `key="…"junk`) — so only the round-trip identity proves every character
    sits inside a token with one ASCII space between tokens. raw_record_valid
    runs the SAME check first, so the exemption can reach only a line the
    writer's lexical grammar accepts and its VALUE rules refuse (a bad ts=, a
    missing required field — the designed other-class control)."""
    if not isinstance(text, str) or assembled_line_ok(text) is not None:
        return None
    prefix = "OWNERSHIP: %s " % sub
    if not text.startswith(prefix):
        return None
    body = text[len(prefix):]
    toks = list(PARSE_KV_RE.finditer(body))
    # every quote accounted for as a quoted FIELD value's delimiter
    if body.count('"') != 2 * sum(1 for m in toks if m.group(1) is not None):
        return None
    # a record marker anywhere outside those values — a bare token, or glued
    # onto the end of a field (`reason=rOWNERSHIP: must-pause …`) — is another
    # record's fragment on this physical line, never attributable
    unquoted = re.sub(r'"[^"]*"', '""', body)
    if any(mk in unquoted for mk in _AWAY_OTHER_MARKERS):
        return None
    keys = [(m.group(2) if m.group(1) is not None else m.group(4), m.end())
            for m in toks if (m.group(1) or m.group(3)) == "key"]
    if len(keys) != 1 or not body[keys[0][1]:].strip():
        return None
    return keys[0][0]


def away_pause_fold(log_root):
    """v44.0 (plan-away-autonomous-rails T0.4 / D17, KD12) — the STRICT
    production-park fold: is this run's production provably unparked? Read by
    the coordinated wait (`away check` run with the OTHER run's identity) and
    printed as ` parks=` on every `away:` line. On the hold fold's RAW input
    path (_away_raw_probe_lines — never _away_probe_records): every physical
    line classified by raw_classify(text, "must-pause") and
    raw_classify(text, "gate-disposition") BEFORE filtering — `None` is not
    that subtype's line (no marker, or a writer-valid record of another
    subtype merely quoting it); a writer-valid record is a CANDIDATE when its
    key class is `deploy-production`; a DOUBTFUL line (torn, merged onto a
    torn predecessor, separator-damaged, undecodable, or with a missing /
    malformed / duplicated identity) makes the count `unknown` with its cause
    UNLESS its one intact `key=` field — attributable to THIS record by
    _away_doubtful_key's rule: the exact subtype prefix at the line start,
    no other record marker after it, the sole top-level key with a token
    after it — names ANOTHER class (then it is another fold's doubt) — a key
    that cannot be read or attributed, or that names no class, is treated as
    this class's (fail closed). For each (run=, key=)
    pair in reading order the newest writer-valid `must-pause` is open until
    a later writer-valid `gate-disposition` for the same pair; an
    `auto-disposition` never closes one; so EVERY doubtful relevant line — a
    pause or a disposition alike — is `unknown` (an invalid disposition never
    closes; an invalid pause never clears the owner — the two branches
    must_pause_fold resolves the OTHER way for the notice re-fire, and that
    fold, the report's §2, and the dedupe are untouched). `path` is the
    record's path= when it matches HOLD_PATH_RE, else None = class-wide (a
    pathless production park counts for EVERY path — `key=` is the only
    required must-pause key). Returns (count or None for unknown, open
    [(key, path or None, kv, loc)] in reading order, problems)."""
    if log_root is None:
        return None, [], ["no --log-root — the production-park fold reads <log-root>/stage-<N>-probe.log"]
    problems, owners = [], {}
    for nm, i, text in _away_raw_probe_lines(log_root, problems):
        for sub in ("must-pause", "gate-disposition"):
            r = raw_classify(text, sub)
            if r is None:
                continue
            kv, why = r
            if kv is None:
                _k = _away_doubtful_key(text, sub)
                _cls = _away_act_class(_k) if _k is not None else None
                if _cls is not None and _cls != "deploy-production":
                    continue   # another class's doubt — not this fold's
                problems.append("%s:%d is a %s line the writer could not have emitted (%s)" % (nm, i, sub, why))
                break      # one cause per physical line (a line carrying both markers is one doubt)
            if _away_act_class(kv.get("key")) != "deploy-production":
                continue
            pair = (kv["run"], kv["key"])
            owners[pair] = (kv, (nm, i)) if sub == "must-pause" else None
    if problems:
        return None, [], problems
    opens = [(kv["key"], kv["path"] if HOLD_PATH_RE.match(kv.get("path") or "") else None, kv, loc)
             for _pair, v in owners.items() if v is not None for kv, loc in [v]]
    return len(opens), opens, []


def _away_parks_suffix(log_root):
    """` parks=<n|unknown>[ parked="<key>[ path=<p>][; …]"]` for the `away:`
    line (v44.0 D17), plus the unknown causes for its reason=."""
    n, opens, problems = away_pause_fold(log_root)
    out = " parks=%s" % ("unknown" if n is None else n)
    if n:
        out += ' parked="%s"' % "; ".join("%s%s" % (key, " path=%s" % p if p else "") for key, p, _kv, _loc in opens)
    return out, ("parks unknown: " + "; ".join(problems)) if n is None else None


# --- the pre-approval fold (v44.0 D2) ---
def _preapproval_limit(cls, limit):
    if limit is not None:
        return limit
    return PREAPPROVAL_DEFAULT_LIMIT if cls == "pr-fix-cycles" else None


def _preapproval_text(cls, path, limit):
    """`<class>[ path=<p>][ limit=<n>]` — the printed form (the suffix and the report)."""
    return "%s%s%s" % (cls, " path=%s" % path if path else "", " limit=%d" % limit if limit is not None else "")


def away_preapproval_fold(log_root, grant_n, config_hash, grant_allows):
    """v44.0 (plan-away-autonomous-rails T0.1 / D2) — THE one pre-approval fold
    (used by `away check` and `away report`), on the hold fold's RAW input
    path (_away_raw_probe_lines, never _away_probe_records). The open set
    starts from the bound grant's `allows=` entries (the EARLIEST
    instructions, source "grant"); the records follow in READER ORDER — stage-
    ordered, then physical-line order — each line classified by raw_classify
    BEFORE filtering: a writer-valid `OWNERSHIP: auto-disposition` of key
    class `pre-approval` bound by the away pair (away= parses to grant_n AND
    away_check= equals config_hash byte for byte — exactly as
    _qb_accepted_versions binds; another grant's record never folds) is an
    instruction; the effective entry per class (+ path) is the LAST DISTINCT
    instruction — an `allowed` opens it with ITS limit (a bare pr-fix-cycles
    reads PREAPPROVAL_DEFAULT_LIMIT; a later `allowed` after a `cleared`
    re-opens, a later `allowed` with another limit replaces it — the
    operator's latest word, never the maximum), a `cleared` closes it (one
    with no prior allow is legal and closes nothing). Distinctness is
    instr=: the FIRST writer-valid record carrying an instr= is that
    instruction; a later record with the same instr= and identical class /
    path / choice / limit is a retry and is IGNORED wherever it sits (it never
    re-opens a cleared class or restores an older limit); the same instr=
    with differing values is a conflict → unknown. FAIL CLOSED: a doubtful
    auto-disposition line whose raw text contains `-pre-approval` (torn,
    merged onto a torn predecessor, separator-damaged, undecodable, or
    malformed — a line validate_preapproval_record refuses is doubt here, by
    construction) → unknown with its cause; other doubtful lines belong to
    other folds; an unlistable root or unreadable log → unknown; a grant
    `allows=` the grammar refuses → unknown. Unlike the hold fold the set is
    NOT order-free (a clear names a class, not a unique id). Returns (count
    or None for unknown, open [(class, path or None, limit or None, source —
    "grant" or "<log>:<line>")] in class order, cleared [(class, path or
    None, "<log>:<line>")] in reader order, problems)."""
    if log_root is None:
        return None, [], [], ["no --log-root — the pre-approval fold reads <log-root>/stage-<N>-probe.log"]
    entries, why = parse_grant_allows(grant_allows) if grant_allows is not None else ([], None)
    if why:
        return None, [], [], ["the grant's allows= could not be read — %s" % why]
    state = {}   # (class, path) -> {"open": bool, "limit": int|None, "source": str}
    for cls, limit in entries:
        state[(cls, None)] = {"open": True, "limit": _preapproval_limit(cls, limit), "source": "grant"}
    problems, cleared, seen = [], [], {}
    for nm, i, text in _away_raw_probe_lines(log_root, problems):
        r = raw_classify(text, "auto-disposition")
        if r is None:
            continue
        kv, why = r
        if kv is None:
            if _away_text_has(text, "-pre-approval"):
                problems.append("%s:%d is a pre-approval line the writer could not have emitted (%s)" % (nm, i, why))
            continue
        if _away_act_class(kv.get("key")) != "pre-approval":
            continue
        if parse_count(kv.get("away", "")) != grant_n or kv.get("away_check") != config_hash:
            continue   # another grant's instruction (or a log copied from another run)
        limit = parse_count(kv["limit"]) if "limit" in kv else None
        ident = (kv["allow"], kv.get("path"), kv["choice"], limit)
        prior = seen.get(kv["instr"])
        if prior is not None:
            if prior != ident:
                problems.append("%s:%d repeats instr=%s with different values — a conflicting retry (the earlier line is the instruction)"
                                % (nm, i, kv["instr"]))
            continue   # an identical retry is a replay — ignored wherever it sits
        seen[kv["instr"]] = ident
        key, where = (kv["allow"], kv.get("path")), "%s:%d" % (nm, i)
        if kv["choice"] == "allowed":
            state[key] = {"open": True, "limit": _preapproval_limit(kv["allow"], limit), "source": where}
        else:
            if key in state:
                state[key]["open"] = False
            cleared.append((kv["allow"], kv.get("path"), where))
    if problems:
        return None, [], cleared, problems
    opens = sorted(((c, p, s["limit"], s["source"]) for (c, p), s in state.items() if s["open"]),
                   key=lambda t: (PREAPPROVAL_CLASSES.index(t[0]), t[1] or ""))
    return len(opens), opens, cleared, []


def _away_allows_suffix(log_root, g):
    """` allows=<n|unknown>[ allowed="<class>[ path=<p>][ limit=<n>][; …]"]` for
    the `away:` line (v44.0 D3), plus the unknown causes for its reason=. `g`
    is the BOUND grant — None whenever the state is not bound (no grant to
    bind pre-approvals to → unknown; nothing proceeds on unknown)."""
    if g is None:
        return " allows=unknown", "allows unknown: no bound grant to bind pre-approvals to"
    n, opens, _cl, problems = away_preapproval_fold(log_root, g["n"], g["kv"]["config_hash"], g["kv"].get("allows"))
    out = " allows=%s" % ("unknown" if n is None else n)
    if n:
        out += ' allowed="%s"' % "; ".join(_preapproval_text(cls, p, lim) for cls, p, lim, _src in opens)
    return out, ("allows unknown: " + "; ".join(problems)) if n is None else None


# --- v47.0 (plan-loop-autonomy-group-2 T1.2 / D2, D4): the listing check at
# EVERY away merge start — the first use-time class check the helper makes.
# `emit` takes three more flags on an away `merge` `choice=start` and nowhere
# else; with them it reads the policy log, the bound grant's departure file
# and — for a listed pre-approved merge only — the merge's diff.
AWAY_MERGE_START_FLAGS = ("--policy-log", "--iso", "--plan")
AWAY_MERGE_START_RECIPE = (
    "--run <runkey> --role composer --log <log-root>/stage-<N>-probe.log --policy-log </abs> --iso <iso-id> "
    "--plan <plan> [--epoch <activation id>] emit OWNERSHIP:auto-disposition|gate-disposition key=<runkey>-merge "
    "choice=start rec=<source>:<disposition> away=<n> away_check=<config_hash> tip=<40-hex> "
    "[allow=operator-merge] [ungated=merge]")


# The ONE argument vector of every name diff an ADMISSION reads (D2's subject
# test here; `records-delta`'s five reads). Each option pins a default that a
# repository's or a user's configuration could otherwise change under the
# evidence: `--no-renames` (a rename reads as a removal and an addition), `-z`
# (no quoting), and — round 12 PR-MED-020 — `--ignore-submodules=dirty`.
# Without it `diff.ignoreSubmodules=all`, or `ignore = all` on a submodule in
# `.gitmodules` or the config, makes porcelain `git diff` DROP a changed
# gitlink from the list with exit 0, between two commits as well as against
# the working tree, while a commit still records the pointer change. The
# explicit value overrides both. The policy it states: a changed submodule
# POINTER is a changed path (a submodule checked out at another commit
# included); a submodule's own uncommitted or untracked content is not,
# because no merge commit records it.
GIT_NAME_DIFF = ("diff", "--name-only", "--no-renames", "--ignore-submodules=dirty", "-z")


def git_one_merge_base(repo, a, b):
    """The ONE merge base of commits `a` and `b` under `repo`: (sha, None), or
    (None, why). v47.0 Step HA3 (candidate 1): `git merge-base --all`, never
    the bare form. A criss-cross history has SEVERAL merge bases; the bare
    command prints one of them, and a name diff against that one alone can
    lack a path the real merge changes (the path equals this base on one side
    and differs from the other base). Both admissions that read "the names
    changed since the merge base" — D2's subject test and `records-delta`'s
    both-sides set — therefore take a single merge base or refuse: with more
    than one there is no one diff to read, and the merge takes the route that
    needs no such reading (the operator's, or the full cycle)."""
    rc, out = _rc_git(repo, "merge-base", "--all", a, b)
    bases = out.split()
    if rc != 0 or not bases or not all(_FULL_SHA_RE.match(x) for x in bases):
        return None, "no merge base could be read"
    if len(bases) > 1:
        return None, ("%d merge bases (a criss-cross history: %s) — a name diff against one of them is not the merge's diff"
                      % (len(bases), ", ".join(x[:12] for x in bases[:4])))
    return bases[0], None


def _merge_start_diff_names(pol, iso, tip):
    """The names a merge of `tip` would change, for D2's subject test: `git
    diff --name-only --no-renames --ignore-submodules=dirty` (GIT_NAME_DIFF)
    between `tip` and its merge base with the
    run's base branch. The base branch and the checkout come from the run's
    journal — <the policy log's directory>/<iso>-isolation — as `run-close`
    reads them (_rc_base_ref: the fetched `refs/remotes/origin/<base_branch>`
    when it exists, else the local branch; the ref is read as it stands — this
    function fetches nothing). Returns (names, None), or (None, reason) when
    anything on the way cannot be read: an unreadable diff refuses — a tip
    with MORE THAN ONE merge base with that branch included (Step HA3,
    git_one_merge_base: no one diff is the merge's then). A run with
    no journal (isolation branch | none — journals exist only for worktree
    runs) therefore never takes a listed merge under the class: its start is
    refused and the merge waits for the operator."""
    jpath = os.path.join(os.path.dirname(pol), "%s-isolation" % iso)
    try:
        with open(jpath, encoding="utf-8") as jf:
            jkv = _rc_parse_kv_lines(jf.read().splitlines())[0]
    except (OSError, UnicodeDecodeError) as e:
        return None, "the run's journal %s could not be read (%s)" % (jpath, e)
    if jkv.get("iso") != iso:
        return None, "the journal %s records iso=%s, not %s" % (jpath, jkv.get("iso", "(none)")[:40], iso)
    base = jkv.get("base", "")
    if not os.path.isabs(base) or not os.path.isdir(base):
        return None, "the journal %s records no usable base= checkout" % jpath
    bb = jkv.get("base_branch")
    if not bb or not _RC_LOSSLESS_BRANCH_RE.match(bb):
        return None, "the journal %s records no usable base_branch=" % jpath
    repo = canon_path(base)
    ref = _rc_base_ref(repo, jkv)
    mb, why = git_one_merge_base(repo, tip, ref)
    if mb is None:
        return None, "tip=%s and %s in %s: %s" % (tip, ref, repo, why)
    try:
        r = subprocess.run([_git_bin(), "-C", repo] + list(GIT_NAME_DIFF) + [mb, tip],
                           capture_output=True, timeout=60, env=_git_env())
    except Exception as e:
        return None, "git diff failed in %s: %s" % (repo, e)
    if r.returncode != 0:
        return None, "git diff %s %s failed in %s" % (mb, tip, repo)
    return [os.fsdecode(p) for p in r.stdout.split(b"\0") if p], None


def away_merge_listing_refusal(pol, iso, plan, log_root, runkey, kv, late, raw):
    """D4 — the listing check at an away `merge` `choice=start`: None when the
    start is admitted, else the reason (its class word in parentheses). `kv`
    is the start as it will be written; `late` says it is an --event-ts start;
    `raw` is the probe log's raw lines, already read by the caller.
    In order:
    (1) the three flags' own form, then the away state through the ONE state
        function, identity fail-closed (the attest-check precedent): the
        policy log is `bound` for --iso / --plan, the open grant's number and
        hash equal the record's away pair, `merge` is in its scope, and the
        grant's departure file under the log root (the --log's directory)
        digests to the grant's departure=;
    (2) the fold over EVERY `Stop: merge` line of that file, whatever their
        order: any malformed line refuses (`departure-stop-malformed`); with
        no well-formed line for this start's key the start is admitted as
        before — unless it carries the label, which is refused
        (`operator-merge-not-listed`); one `around` or `park` line for the
        key refuses whatever the others say (`departure-stop-restricts`);
    (3) every line for the key reads `pre-approved`: admitted only when the
        start carries allow=operator-merge (`operator-merge-label-missing`),
        the class is in force by the pre-approval fold — never on unknown,
        never after a clear (`operator-merge-not-in-force`), the start is
        neither late nor ungated and the log's latest verdict for the run is
        `passed` (D2 condition 3), and the subject test holds over the UNION
        of those lines' subjects: every subject is in the merge's diff, and
        the diff holds no other path in any subject's own directory — added,
        changed or removed (`operator-merge-subject-absent` /
        `operator-merge-extra-file`; an unreadable diff refuses).
    The label is `operator-merge` as allow='s value or as one entry of a
    comma-joined value. What this does and does not give, exactly: the START
    RECORD of a merge the departure file lists is written only as its line
    allows — the act follows its record by the composer's record-then-act
    rule, which this function does not enforce; a line is matched to a start
    by the start's own key=, which cmd_emit admits only as `<--run>-merge`
    (`merge-key-not-run`, checked before this function runs — a direct
    caller that passes another key is read by that key); and D2 conditions 5
    and 6, with the stop-3 read of the rest of
    the diff, stay the composer's read — an unlisted change is not found
    here."""
    if not os.path.isabs(pol):
        return "--policy-log must be an absolute path"
    if not ISO_ID_RE.match(iso):
        return "--iso %r is not a filename-safe iso-id" % iso[:60]
    check_value_safety("plan", plan)
    if not plan.strip():
        return "--plan must be a nonblank identity string (the journal's plan= value; the file need not exist)"
    lines, err = _away_read_policy(pol)
    if lines is None:
        return "the policy log %s could not be read (%s) (away-not-bound)" % (pol, err)
    st = away_state(lines, iso, plan)
    if st["state"] != "bound":
        return ("the policy log reads state=%s for --iso / --plan%s — an away merge start needs the grant it names bound (away-not-bound)"
                % (st["state"], " (line %d: %s)" % (st["bad"][0], st["bad"][2]) if st["bad"] else ""))
    g = st["open"]
    if parse_count(kv.get("away", "")) != g["n"] or kv.get("away_check") != g["kv"]["config_hash"]:
        return ("the start's pair away=%s away_check=%s is not the bound grant's (grant=%d config_hash=%s) (grant-pair-mismatch)"
                % (kv.get("away"), kv.get("away_check"), g["n"], g["kv"]["config_hash"]))
    if "merge" not in g["kv"]["scope"].split(","):
        return "the bound grant's scope=%s does not hold merge (merge-not-in-scope)" % g["kv"]["scope"]
    dep_path = _away_departure_path(log_root, g["n"])
    try:
        dep_bytes = _away_read_bytes(dep_path)
    except OSError as e:
        return "the grant's departure file %s could not be read (%s) (departure-mismatch)" % (dep_path, e)
    if hashlib.sha256(dep_bytes).hexdigest()[:12] != g["kv"]["departure"]:
        return "the departure file %s no longer digests to the grant's departure=%s (departure-mismatch)" % (dep_path, g["kv"]["departure"])
    entries, malformed = away_stop_merge_lines(dep_bytes)
    if malformed:
        return ("the departure file holds a `Stop: merge` line that is not in the fixed form — line%s %s; a line meant to restrict "
                "a merge is never read as no listing, so no away merge start is admitted while it stands (departure-stop-malformed)"
                % ("" if len(malformed) == 1 else "s", ", ".join(str(n) for n in malformed)))
    key = kv.get("key")
    labelled = "operator-merge" in kv.get("allow", "").split(",")
    mine = [e for e in entries if e[1] == key]
    if not mine:
        if labelled:
            return ("the start carries allow=operator-merge but the departure file lists no `Stop: merge key=%s` line — the class "
                    "reaches listed merges only (operator-merge-not-listed)" % key)
        return None
    veto = [e for e in mine if e[4] != "pre-approved"]
    if veto:
        return ("the departure file's line %d reads `Stop: merge key=%s … — %s` — one restriction vetoes, whatever the other lines "
                "say; this merge waits for the operator (departure-stop-restricts)" % (veto[0][0], key, veto[0][4]))
    if not labelled:
        return ("the departure file lists this merge `pre-approved` (line %d) — its start carries allow=operator-merge, or it does "
                "not start (operator-merge-label-missing)" % mine[0][0])
    n, opens, _cl, problems = away_preapproval_fold(log_root, g["n"], g["kv"]["config_hash"], g["kv"].get("allows"))
    if n is None:
        return "the pre-approval fold reads unknown — nothing proceeds on unknown: %s (operator-merge-not-in-force)" % "; ".join(problems)
    if not any(cls == "operator-merge" for cls, _p, _lim, _src in opens):
        return ("operator-merge is not in force under grant %d — it is not in the grant's allows= and no later record allows it, or it "
                "was cleared (operator-merge-not-in-force)" % g["n"])
    if late:
        return "an --event-ts (late) start never rides operator-merge — the class admits a merge before it happens (operator-merge-late-start)"
    if "ungated" in kv:
        return "a start carrying ungated= never rides operator-merge — the class needs a passed verdict (operator-merge-ungated)"
    hist = ci_history(raw, runkey)
    if not hist or hist[-1][1] is None or hist[-1][1].get("verdict") != "passed":
        return "the log's latest verdict for run=%s is not `passed` — the class admits a merge on green CI only (operator-merge-verdict)" % runkey
    names, why = _merge_start_diff_names(pol, iso, kv["tip"])
    if names is None:
        return "the merge's diff could not be read — %s (operator-merge-diff-unreadable)" % why
    subjects = sorted(set(s for e in mine for s in e[3]))
    absent = [s for s in subjects if s not in names]
    if absent:
        return ("the listed subject%s %s %s not in the merge's diff (operator-merge-subject-absent)"
                % ("" if len(absent) == 1 else "s", ", ".join(absent), "is" if len(absent) == 1 else "are"))
    dirs = set(s.rpartition("/")[0] for s in subjects)
    extra = sorted(p for p in set(names) if p not in subjects and p.rpartition("/")[0] in dirs)
    if extra:
        return ("the merge's diff holds %d other path%s in a listed subject's directory — %s; the line names what it covers and "
                "nothing beside it (operator-merge-extra-file)"
                % (len(extra), "" if len(extra) == 1 else "s", ", ".join(ci_sanitise(p, 120) for p in extra[:5])))
    return None


def _away_classify(records, grants, g):
    """The report's one-pass classification of the probe records against the
    policy log's grants, for grant `g` (v37.0 T1.2: moved here whole so the
    report and `away end`'s guard share ONE join — lesson L148). Returns
    (composer_alone, on_rec, smokes, release, unmatched): `release` holds
    (kv, loc) tuples in append order — callers hand away_release_pairing the
    kv dicts and keep the locations for their diagnostics; the other four are
    rendered report items."""
    # Classify every away-pair record and every agent smoke. v35.1 (R2): a
    # release-class record goes to section 6 ONLY, whatever its rec= prefix.
    composer_alone, on_rec, smokes, release, unmatched = [], [], [], [], []
    for raw, loc in records:
        kv, bare = parse_kv(raw[len("OWNERSHIP:"):])
        sub = bare[0] if bare else ""
        has_pair = "away" in kv or "away_check" in kv
        t = parse_iso(kv.get("ts"))
        if not has_pair:
            if (g is not None and sub == "smoke-pass" and kv.get("smoke_by") == "agent"
                    and _away_in_window(t, g)
                    and emittable_record(raw, "OWNERSHIP:smoke-pass")[2] is None):
                smokes.append(_away_item(kv, loc))
            continue
        if sub not in AWAY_PAIR_SUBTYPES:
            unmatched.append(_away_item(kv, loc, "the away pair on OWNERSHIP:%s" % sub[:40]))
            continue
        _kv, _b, why = emittable_record(raw, "OWNERSHIP:" + sub)
        if why:
            unmatched.append(_away_item(kv, loc, "not a writer-valid record: %s" % why))
            continue
        # r15 PR-LOW-001: join on the PARSED number (the writer admits any
        # parse_count spelling — `01` is grant 1), the hash compared exactly.
        _an = parse_count(kv["away"])
        m = [x for x in grants if x["n"] == _an and x["kv"]["config_hash"] == kv["away_check"]]
        if not m:
            unmatched.append(_away_item(kv, loc, "away=%s away_check=%s matches no grant in the policy log"
                                        % (kv["away"], kv["away_check"])))
            continue
        if not _away_in_window(t, m[0]):
            unmatched.append(_away_item(kv, loc, "written outside grant %d's window" % m[0]["n"]))
            continue
        if g is None or m[0] is not g:
            continue
        if sub == "smoke-pass":
            if kv.get("smoke_by") == "agent":
                smokes.append(_away_item(kv, loc, "under grant %d" % g["n"]))
            continue
        is_release = _away_act_class(kv.get("key")) in AWAY_RELEASE_CLASSES
        if is_release:
            release.append((kv, loc))
        elif kv.get("rec", "").startswith("composer:"):
            composer_alone.append(_away_item(kv, loc))
        else:
            on_rec.append(_away_item(kv, loc))
    return composer_alone, on_rec, smokes, release, unmatched


# --- v46.4 (plan-loop-field-review-fixes D9): the report's section 8 ---------
# "Also decided or stopped during the grant" — what the selected grant's window
# holds that sections 2–7 do not list. Built BESIDE them: _away_classify, its
# result, `away end`'s guard, _away_item and the bytes of sections 1–7 are
# unchanged (the selftest renders them against a frozen v46.3 copy).
AWAY_ALSO_TITLE = "## 8. Also decided or stopped during the grant"
AWAY_ALSO_SUBTYPES = ("auto-disposition", "gate-disposition", "profile-switch", "smoke-pass")
# what _away_item prints itself: ts=, run=, the nine key=value fields of its
# loop, detail=. A section-8 line shows every OTHER key=value the record holds
# through _away_item's `extra`. Two owners of one list — the selftest pins
# this tuple to _away_item's own output, so neither can drift unseen.
_AWAY_ITEM_KEYS = ("ts", "run", "key", "path", "choice", "hold_id", "clears", "rec", "smoke_by", "cell", "verdict", "detail")


def _away_also_item(sub, kv, loc, notes=()):
    """One section-8 line: the record's subtype, then _away_item's own
    rendering of it — its usual fields; then, through its `extra`, the notes
    and every other key=value the record holds, in the record's own order (a
    value that is empty or holds a blank is shown in double quotes); then its
    detail and location."""
    other = " · ".join(('%s="%s"' if (not v or " " in v or "\t" in v) else "%s=%s") % (k, v)
                       for k, v in kv.items() if k not in _AWAY_ITEM_KEYS)
    return "- %s · %s" % (sub, _away_item(kv, loc, "; ".join([n for n in notes if n] + ([other] if other else [])))[2:])


def _away_wait_text(opened, answered):
    """How long a question waited, from the two parsed instants: `answered
    after <duration>` in whole days, hours and minutes (`under a minute` below
    sixty seconds; `0 minutes` only for the same instant). The helper admits a
    backdated event time, so an answer can carry an EARLIER timestamp than its
    question: then no wait is shown — never a negative, zero or absolute one.
    The sub-minute test is on the interval as parsed, BEFORE it is cut to whole
    seconds: an event time may carry a fraction of a second, and a positive
    wait below one second is not the same instant."""
    if answered < opened:
        return "wait not shown — the answer's timestamp is earlier than the question's"
    wait = (answered - opened).total_seconds()
    if 0 < wait < 60:
        return "answered after under a minute"
    secs = int(wait)
    days, rem = divmod(secs // 60, 1440)
    hours, mins = divmod(rem, 60)
    parts = ["%d %s%s" % (n, word, "" if n == 1 else "s")
             for n, word in ((days, "day"), (hours, "hour"), (mins, "minute")) if n]
    return "answered after %s" % (" ".join(parts) or "0 minutes")


def _away_also_decided(records, grants, g):
    """v46.4 D9 — section 8's lines for grant `g` (none selected: no line), in
    log order, of two kinds.
    (i) RECORDS: each OWNERSHIP record whose ts= is inside the grant's window,
    whose subtype is one of AWAY_ALSO_SUBTYPES, and that sections 3–7 did not
    list — asked of _away_classify itself, one record at a time (it holds no
    state across records), so the two can never disagree about what is listed;
    section 2 lists must-pause and hold records only, never one of these
    subtypes. So: a decision taken under the run's standing settings (no away
    pair), a cap raise or accept, a profile switch, and every smoke section 5
    does not list — an operator's, and one with no smoke_by=, which is marked
    as read as operator (the grammar's default). A record that passes the
    writer's own validity check for its subtype (emittable_record) is shown
    as it stands; one that fails is still listed, as `not a writer-valid
    record: <why>` — a diagnostic, never a decision. (A grant-tagged record
    that is not writer-valid is section 7's, as before, and so not here.) Two
    edges of that selection, as it is written: a record whose ts= does not
    parse is inside no window and is not listed; and another grant's own
    record whose ts= also falls inside this window (two grants sharing a
    boundary second) is one sections 3–7 of THIS report pass over, so it is
    listed here, its away pair shown.
    (ii) ANSWERED QUESTIONS: a must-pause whose closing gate-disposition has
    its ts= inside the window, whenever the question was opened (before the
    grant: marked, as section 2 marks it). The pairing is must_pause_fold's
    own rule — the fold itself, run at the window's end over the records of
    that (run=, key=) pair that precede the closing one (the fold treats each
    pair on its own, so that prefix decides what the full log would). One
    line: the question, `answered by` the closing record — which is therefore
    not listed again under (i), though a closing record that is itself a
    decision under the away grant stays in sections 3–4 as before — and the
    wait (_away_wait_text). A closing record that is not writer-valid still
    closes its question (the fold's rule): the line says so and shows its
    time alone, never its choice=. A question answered after the window's end
    is not here; it is in section 2, as waiting at the grant's end. A LIMIT of
    this pairing: a question fired again under the same key before it was
    answered is one open owner to the fold — its LATEST fire — so the line is
    that fire's and the wait is counted from it, not from the first fire."""
    if g is None:
        return []
    g_start, g_end = _away_window(g)
    out, by_pair = [], {}
    for raw, loc in records:
        kv, bare = parse_kv(raw[len("OWNERSHIP:"):])
        sub = bare[0] if bare else ""
        in_window = _away_in_window(parse_iso(kv.get("ts")), g)
        # the fold's own admission: a bare token, run= and key=
        prior = by_pair.setdefault((kv["run"], kv["key"]), []) if bare and "run" in kv and "key" in kv else None
        line = None
        if sub == "gate-disposition" and prior is not None and in_window:
            owner = must_pause_fold(prior, upto=g_end).get((kv["run"], kv["key"]))
            if owner is not None:
                okv, oloc = owner
                opened, answered = parse_iso(okv.get("ts")), parse_iso(kv.get("ts"))
                before = opened is not None and g_start is not None and opened < g_start
                why = emittable_record(raw, "OWNERSHIP:gate-disposition")[2]
                answer = (_away_also_item(sub, kv, loc)[2:] if why is None
                          else "%s · %s — not a writer-valid record: %s (%s:%d)" % (sub, kv.get("ts", "?"), why, loc[0], loc[1]))
                line = "%s — answered by %s — %s" % (
                    _away_also_item("must-pause", okv, oloc, ["open before the grant"] if before else []),
                    answer, _away_wait_text(opened, answered))
        if (line is None and in_window and sub in AWAY_ALSO_SUBTYPES
                and not any(_away_classify([(raw, loc)], grants, g))):
            why = emittable_record(raw, "OWNERSHIP:" + sub)[2]
            if why is not None:
                line = _away_also_item(sub, kv, loc, ["not a writer-valid record: %s" % why])
            else:
                line = _away_also_item(sub, kv, loc, ["smoke_by not recorded — read as operator"]
                                       if sub == "smoke-pass" and "smoke_by" not in kv else [])
        if prior is not None:
            prior.append((raw, loc))
        if line is not None:
            out.append(line)
    return out


def away_report_text(st, log_root, iso, selected, policy_err=None):
    """v34.0 D5 — the report: plain markdown, eight sections in order (v46.4
    D9 added the eighth, after the seven it had; those seven are unchanged),
    each printed even when empty ("none"). Built ONLY from the policy log (via
    the shared state function) and the probe logs — never composed by hand."""
    grants = st["grants"]
    g = selected
    records, unread = _away_probe_records(log_root)
    out = ["# Away report — %s" % iso]
    # v36.0 Decision 4: a continuation run's source, once, in the header.
    _carried = _away_carried_from(log_root, g["n"], g["kv"]["departure"]) if g is not None else None
    if _carried is not None:
        out.append(_carried)
    out.append("")
    # 1. Grant
    out.append("## 1. Grant")
    if policy_err:
        out.append("- policy log unreadable: %s" % policy_err)
    for _p in unread:
        out.append("- INPUT NOT READ: %s" % _p)
    if g is None:
        out.append("none — no away grant is recorded in the policy log (log state: %s)" % st["state"])
    else:
        dig = _away_departure_digest(log_root, g["n"])
        dstate = ("matches the departure file" if dig == g["kv"]["departure"]
                  else "departure file missing or unreadable" if dig is None
                  else "departure file now digests to %s — it was edited" % dig)
        out.append("- Grant %d, scope %s" % (g["n"], g["kv"]["scope"]))
        out.append("- Given at %s" % g["kv"]["ts"])
        if g["end_kv"] is not None:
            out.append("- Ended at %s (reason: %s)" % (g["end_kv"]["ts"], g["end_kv"]["reason"]))
        else:
            out.append("- Still in force")
        out.append("- Departure digest %s (%s); config_hash %s" % (g["kv"]["departure"], dstate, g["kv"]["config_hash"]))
        out.append("- Policy log state: %s; grants recorded: %d" % (st["state"], len(grants)))
        # v44.0 D2/D3: the pre-approvals in force and the clears — the SAME fold
        # `away check` prints (one fold, one truth), for the selected grant.
        _pn, _popen, _pcleared, _pprob = away_preapproval_fold(log_root, g["n"], g["kv"]["config_hash"], g["kv"].get("allows"))
        if _pn is None:
            out.append("- Pre-approvals in force: unknown — nothing proceeds on a pre-approval: " + "; ".join(_pprob))
        elif not _popen:
            out.append("- Pre-approvals in force: none")
        else:
            out.append("- Pre-approvals in force:")
            for _pc, _pp, _pl, _ps in _popen:
                out.append("  - %s — %s" % (_preapproval_text(_pc, _pp, _pl), "the grant's allows=" if _ps == "grant" else _ps))
        if not _pcleared:
            out.append("- Cleared: none")
        else:
            out.append("- Cleared:")
            for _pc, _pp, _ps in _pcleared:
                out.append("  - %s — %s" % (_preapproval_text(_pc, _pp, None), _ps))
    out.append("")
    # 2. Waiting for you — the helper's own open-must-pause rule, at the
    # grant's window end (now, for a grant still in force).
    out.append("## 2. Waiting for you")
    waiting = []
    if g is not None:
        g_start, g_end = _away_window(g)
        order = {loc: i for i, (_raw, loc) in enumerate(records)}
        for (run, key), (okv, loc) in sorted(must_pause_fold(records, upto=g_end).items(),
                                             key=lambda p: order.get(p[1][1], 0)):
            t = parse_iso(okv.get("ts"))
            before = t is not None and g_start is not None and t < g_start
            waiting.append(_away_item(okv, loc, ("open before the grant; " if before else "")
                                      + "reason=%s" % okv.get("reason", "?")))
    # v35.1 Decision 5: the run's open holds and every clear, whatever the
    # grant window (holds are run-scoped), from the one fold.
    _hn, _hopen, _hclears, _hprob = away_hold_fold(log_root, iso)
    if _hn is None:
        waiting.append("- holds=unknown — every release act parks: " + "; ".join(_hprob))
    for _hid, _hcls, _hp, _hkv, _hloc in _hopen:
        waiting.append(_away_item(_hkv, _hloc, "open hold %s on %s%s" % (_hid, _hcls, " path=%s" % _hp if _hp else "")))
    for _ckv, _cloc in _hclears:
        waiting.append(_away_item(_ckv, _cloc, "clear of hold %s" % _ckv.get("clears", "?")))
    out.extend(waiting or ["none"])
    out.append("")
    composer_alone, on_rec, smokes, release, unmatched = _away_classify(records, grants, g)
    out.append("## 3. Decided by the composer alone")
    out.extend(composer_alone or ["none"])
    out.append("")
    out.append("## 4. Decided on the executor's recommendation")
    out.extend(on_rec or ["none"])
    out.append("")
    out.append("## 5. Smokes run by an agent")
    out.extend(smokes or ["none"])
    out.append("")
    # 6. Merge, fixes and deploys — away_release_pairing (v35.0 A9) flags a
    # `choice=start` with no later outcome (choice=done|failed) for the same
    # (run, key, grant, path), an act-class outcome with no start before it,
    # and labels a late start (backdated before the outcome it answers).
    out.append("## 6. Merge, fixes and deploys")
    open_idx, no_start_idx, late_idx = away_release_pairing([kv for kv, _loc in release])
    sec6 = []
    for idx, (kv, loc) in enumerate(release):
        flag = (AWAY_OPEN_START_FLAG if idx in open_idx
                else AWAY_NO_START_FLAG if idx in no_start_idx
                else AWAY_LATE_START_FLAG if idx in late_idx else "")
        sec6.append(_away_item(kv, loc, flag))
    for raw, loc in records:
        kv, bare = parse_kv(raw[len("OWNERSHIP:"):])
        if bare and bare[0] == "run-close":
            sec6.append(_away_item(kv, loc, "run-close"))
    out.extend(sec6 or ["none"])
    out.append("")
    # 7. Records that do not match the grant
    out.append("## 7. Records that do not match the grant")
    if st["bad"] is not None:
        unmatched.append("- policy log line %d made the log %s: %s — %s"
                         % (st["bad"][0], st["state"], st["bad"][2], st["bad"][1][:200]))
    out.extend(unmatched or ["none"])
    # 8. Also decided or stopped during the grant (v46.4 D9) — appended after
    # section 7; nothing above this line changed for it.
    out.append("")
    out.append(AWAY_ALSO_TITLE)
    out.extend(_away_also_decided(records, grants, g) or ["none"])
    return "\n".join(out) + "\n"


# --- v37.0 Decisions 4/8: `away census` — every policy log on one base ------

AWAY_CENSUS_RECIPE_STATES = ("cleaned", "merged")  # a closed run's journal — the only lines with a recipe
_CENSUS_JOURNAL_VALUES = ("plan", "log_root", "phases")  # journal values that reach a line or a recipe


def _census_esc(text, limit=300):
    """A diagnostic rendered on ONE physical line: line terminators and every
    control, DEL, non-space whitespace, and lone surrogate escaped; a double
    quote becomes ' (the reason="…" quoting has no escape). Not a validator —
    values that reach a census field are checked, never escaped."""
    out = []
    for ch in str(text)[:limit]:
        o = ord(ch)
        if ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif o < 0x20 or o == 0x7f:
            out.append("\\x%02x" % o)
        elif (ch != " " and ch.isspace()) or 0xd800 <= o <= 0xdfff:
            out.append("\\u%04x" % o)
        elif ch == '"':
            out.append("'")
        else:
            out.append(ch)
    return "".join(out)


def _census_why(e):
    if isinstance(e, OSError) and e.errno == errno.ELOOP:
        return "a symlink (never followed)"
    return str(e)


def _census_read(dir_fd, name):
    """The strict-profile read of one file directly under the loops directory:
    bytes, or None when it does not exist; raises OSError otherwise."""
    try:
        return _away_read_bytes(name, dir_fd, follow=False, cap=AWAY_CENSUS_CAP)
    except FileNotFoundError:
        return None


def _census_last_away(data):
    """The rehydrate hook's text test, on bytes: split on LF, one trailing CR
    dropped, the LAST line starting `OWNERSHIP: away-` — `grant` when it starts
    `OWNERSHIP: away-grant `, `end` for any other away line (not a grant),
    `none` when there is no away line."""
    last = None
    for piece in data.split(b"\n"):
        if piece.endswith(b"\r"):
            piece = piece[:-1]
        if piece.startswith(b"OWNERSHIP: away-"):
            last = piece
    if last is None:
        return "none"
    return "grant" if last.startswith(b"OWNERSHIP: away-grant ") else "end"


def _census_self_plan(lines):
    """The plan= of the log's first writer-valid away-grant record, or None."""
    for raw in lines:
        line = raw.rstrip("\r\n")
        if not AWAY_LINE_RE.match(line):
            continue
        _kv, bare = parse_kv(line[len("OWNERSHIP:"):])
        if bare and bare[0] == "away-grant":
            kv, _b, why = emittable_record(line, "OWNERSHIP:away-grant")
            if why is None:
                return kv["plan"]
    return None


def _census_probe_age(log_root):
    """Minutes since the newest `stage-<N>-probe.log` under the log root was
    modified (a stat, never a read), or None when there is none or the root
    cannot be opened. The names are listed and stat'ed through ONE held
    directory descriptor (Decision 4; round 7 PR-LOW-001), so the age comes
    from the directory whose names were listed; a probe-log symlink is
    followed, as the shipped writers allow. v45.0 (T1.2): the handle comes
    from `_open_at(directory=True)` — a held fd on the fd-relative leg, the
    directory PATH on the fallback leg (`os.listdir(path)`, then a pathname
    stat per name)."""
    try:
        root_fd = _open_at(None, log_root, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0), follow=True, directory=True)
    except (OSError, ValueError):
        return None
    try:
        try:
            names = os.listdir(root_fd)
        except OSError:
            return None
        newest = None
        for nm in names:
            if not PROBE_LOG_NAME_RE.match(nm):
                continue
            try:
                m = _stat_at(root_fd, nm, follow=True).st_mtime
            except OSError:
                continue
            newest = m if newest is None or m > newest else newest
        return None if newest is None else max(0, int((time.time() - newest) // 60))
    finally:
        _dir_close(root_fd)


def _census_one(dir_fd, base, names, iso):
    """(census line, recipe line or None, bound?) for one `<iso>-policy.log`.
    Raises on nothing it can classify; the caller catches the rest per log."""
    import shlex
    loops = os.path.join(base, ".cursor", "loops")
    reasons = []
    # the run's journal — best-effort, first-wins (_rc_parse_kv_lines)
    jkv, journal = None, "none"
    try:
        jdata = _census_read(dir_fd, "%s-isolation" % iso)
        if jdata is not None:
            jkv = _rc_parse_kv_lines(jdata.decode("utf-8").splitlines())[0]
    except (OSError, UnicodeDecodeError) as e:
        journal = "unreadable"
        reasons.append("journal unreadable: %s" % _census_why(e))
    if jkv is not None:
        st_tok = jkv.get("state")
        journal = st_tok if st_tok is not None and _PRIOR_STATE_RE.match(st_tok) else "unrecognized"
    # journal values that reach a field or a recipe: the writer's own value
    # predicate in REASON mode (non-aborting) — a failing value makes the log
    # unreadable and is never printed
    unsafe = [k for k in _CENSUS_JOURNAL_VALUES
              if jkv is not None and k in jkv and reason_of(check_value_safety, k, jkv[k]) is not None]
    jplan = jkv.get("plan") if jkv is not None and "plan" not in unsafe else None
    if jplan is not None and not jplan.strip():
        jplan = None
    jlr = jkv.get("log_root") if jkv is not None and "log_root" not in unsafe else None
    if jlr is not None and os.path.isabs(jlr):
        log_root = jlr.rstrip("/") or "/"
    elif "log_root" in unsafe:
        log_root = None
    else:
        log_root = os.path.join(loops, iso)
    # the marker: live only with no .complete-* sibling and a matching body iso=
    if any(n.startswith("%s-active.complete-" % iso) for n in names):
        marker = "retired"
    else:
        marker = "none"
        try:
            mdata = _census_read(dir_fd, "%s-active" % iso)
            if mdata is not None:
                mkv = _rc_parse_kv_lines(mdata.decode("utf-8").splitlines())[0]
                if mkv.get("iso") == iso:
                    marker = "live"
                else:
                    reasons.append("marker body iso=%s does not match its name" % mkv.get("iso", "(none)"))
        except (OSError, UnicodeDecodeError) as e:
            marker = "unreadable"
            reasons.append("marker unreadable: %s" % _census_why(e))
    age = _census_probe_age(log_root) if log_root is not None else None
    # the policy log, through the one state function with the log's own identity
    st, state, plan_used, plan_self, last_away = None, "unreadable", None, False, None
    try:
        pdata = _census_read(dir_fd, "%s-policy.log" % iso)
        if pdata is None:
            raise FileNotFoundError("the policy log disappeared after the listing")
    except OSError as e:
        reasons.insert(0, "policy log unreadable: %s" % _census_why(e))
    else:
        if unsafe:
            reasons.insert(0, "journal value unsafe: %s" % ", ".join(unsafe))
        else:
            lines = _away_policy_lines(pdata)
            self_plan = _census_self_plan(lines)
            if jplan is not None:
                plan_used = jplan
                st = away_state(lines, iso, jplan)
                if st["state"] == "wrong-identity" and self_plan is not None and self_plan != jplan:
                    plan_used, plan_self = self_plan, True
                    st = away_state(lines, iso, self_plan)
            else:
                plan_used, plan_self = self_plan, self_plan is not None
                st = away_state(lines, iso, self_plan or "")
            state = st["state"]
            if st["bad"] is not None:
                reasons.insert(0, "policy log line %d: %s" % (st["bad"][0], st["bad"][2]))
            if state == "malformed":
                last_away = _census_last_away(pdata)
    parts = ["census: iso=%s" % iso, "state=%s" % state, "grants=%d" % (len(st["grants"]) if st else 0)]
    recipe = None
    if state == "bound":
        g = st["open"]
        scope = g["kv"]["scope"]
        parts += ["grant=%d" % g["n"], "scope=%s" % scope, "ts=%s" % g["kv"]["ts"],
                  fmt_kv("plan", plan_used), fmt_kv("log_root", log_root)]
        if journal in AWAY_CENSUS_RECIPE_STATES:
            nums = re.findall(r"stage-([0-9]+)", jkv.get("phases") or "")
            n = parse_count(nums[-1]) if nums else None
            runkey = "stage-%d" % n if n is not None else "stage-1"
            q = shlex.quote
            reason = "release-done" if "merge" in scope.split(",") else "run-stop"
            # v40.0 D5: the release-done end REQUIRES --base (the closed-run
            # gate reads this base's journal — cleaned or merged here, so the
            # printed recipe is admitted); run-stop takes no --base.
            recipe = ("recipe: python3 scripts/loop-journal.py away end --run %s --role composer --policy-log %s"
                      " --iso %s --plan %s --log-root %s%s grant=%d reason=%s"
                      % (q(runkey), q(os.path.join(loops, "%s-policy.log" % iso)), q(iso), q(plan_used), q(log_root),
                         " --base %s" % q(base) if reason == "release-done" else "", g["n"], reason))
    parts += ["journal=%s" % journal, "marker=%s" % marker, "probe_age_min=%s" % ("none" if age is None else age)]
    if plan_self:
        parts.append("plan_source=self")
    if last_away is not None:
        parts.append("last_away=%s" % last_away)
    if reasons:
        parts.append('reason="%s"' % "; ".join(_census_esc(r) for r in reasons))
    return " ".join(parts), recipe, state == "bound"


def cmd_away_census(flags):
    """v37.0 Decisions 4/8 — `away census --base <abs>`: READ-ONLY, writes
    nothing. One `census:` line per `<iso>-policy.log` directly under
    <base>/.cursor/loops (iso-id stems only, byte-sorted), a `recipe:` line
    after each bound log whose run's journal is cleaned or merged, then ONE
    summary line. Raw facts only — no departure-digest check, no holds fold,
    no departure-file read, no probe-record read, no liveness verdict. Every
    file is read through _away_read_bytes's strict profile; a per-log failure
    becomes that log's state=unreadable and the census continues. Exit 0 when
    the loops directory was listed (absent → `logs=0`); 3 when it could not
    be, or --base is not a directory; 2 on a relative --base."""
    base = flags["--base"]
    if not os.path.isabs(base):
        refuse("--base must be an absolute path (the base checkout whose .cursor/loops the census reads)")
    check_value_safety("base", base)
    try:
        base.encode("utf-8")
    except UnicodeEncodeError:
        refuse("--base is not valid UTF-8")
    if not os.path.isdir(base):
        envfail("--base %s is not a directory" % base)
    loops = os.path.join(base, ".cursor", "loops")
    try:
        dir_fd = _open_at(None, loops, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0), follow=True, directory=True)
    except FileNotFoundError:
        sys.stdout.write("census: logs=0 bound=0\n")
        return
    except OSError as e:
        envfail("cannot open %s: %s" % (loops, e))
    try:
        try:
            names = os.listdir(dir_fd)
        except OSError as e:
            envfail("cannot list %s: %s" % (loops, e))
        isos = sorted(nm[:-len("-policy.log")] for nm in names
                      if nm.endswith("-policy.log") and ISO_ID_RE.match(nm[:-len("-policy.log")]))
        out, bound = [], 0
        for iso in isos:
            try:
                line, recipe, is_bound = _census_one(dir_fd, base, names, iso)
            except Exception as e:  # a foreign value never aborts the census (ValueError on a NUL included)
                line, recipe, is_bound = ('census: iso=%s state=unreadable grants=0 journal=unreadable marker=unreadable'
                                          ' probe_age_min=none reason="census error: %s"'
                                          % (iso, _census_esc("%s: %s" % (e.__class__.__name__, e)))), None, False
            out.append(line)
            if recipe is not None:
                out.append(recipe)
            bound += 1 if is_bound else 0
        out.append("census: logs=%d bound=%d" % (len(isos), bound))
        sys.stdout.write("\n".join(out) + "\n")
    finally:
        _dir_close(dir_fd)


def _away_report_recipe(runkey, pol, iso, plan, log_root, grant):
    """v35.0 A11: the report recipe for a grant just ended, as ONE line —
    helper OUTPUT, not a published recipe; every flag from the call, the
    canonical --out file under the log root (the literal `<log-root>`
    placeholder, for the composer to fill, when --log-root was not given).
    Printed by `away end` and (v47.0 D22) by a widening, for the grant it
    ended."""
    import shlex
    q = shlex.quote
    lr = q(log_root) if log_root is not None else "<log-root>"
    out_file = (q(os.path.join(log_root, "away-%s-report.md" % grant)) if log_root is not None
                else "<log-root>/away-%s-report.md" % grant)
    return ("python3 scripts/loop-journal.py away report --run %s --role composer --policy-log %s"
            " --iso %s --plan %s --log-root %s grant=%s --out %s\n"
            % (q(runkey), q(pol), q(iso), q(plan), lr, grant, out_file))


def away_release_open(log_root, grants, g):
    """v37.0 Decision 2's read, as one function (v47.0: `away end`'s automatic
    reasons and the widening share it): grant `g`'s release acts that have a
    `start` and no outcome, through the report's own join (_away_classify →
    away_release_pairing). Returns (acts, problems): acts [(kv, (log name,
    line))] in append order; problems names every probe log that could not be
    read — the callers refuse on it (evidence that cannot be read is never
    "nothing in flight")."""
    records, problems = _away_probe_records(log_root)
    if problems:
        return [], problems
    release = _away_classify(records, grants, g)[3]
    open_idx = away_release_pairing([rkv for rkv, _loc in release])[0]
    return [(rkv, loc) for idx, (rkv, loc) in enumerate(release) if idx in open_idx], []


# v47.0 (plan-loop-autonomy-group-2 T1.8 / D22): widening in one step.
# The classes whose reach grows with the scope: a widening that adds `staging`
# or `production` never carries them — they ride the new grant only when the
# call names them again in allows= (the operator's answer in the added block).
AWAY_WIDEN_REASK_CLASSES = ("foreign-merge", "operator-merge")
AWAY_WIDEN_REASK_SCOPES = ("staging", "production")


def away_widen_carried(log_root, prior, new_scope):
    """D22 — what a widening of grant `prior` to `new_scope` CARRIES: the
    departure classes in force under `prior` by the one pre-approval fold
    (ended or bound — the fold reads a grant by its number and hash), each
    with its limit (pr-fix-cycles), minus AWAY_WIDEN_REASK_CLASSES when the
    new scope gains a token of AWAY_WIDEN_REASK_SCOPES. Per-task
    `operator-task` approvals never carry (they bind to the grant they were
    given under). Returns ([(class, limit or None)], None), or (None,
    problems) when the fold reads unknown."""
    n, opens, _cl, problems = away_preapproval_fold(log_root, prior["n"], prior["kv"]["config_hash"], prior["kv"].get("allows"))
    if n is None:
        return None, problems
    grew = set(new_scope.split(",")) - set(prior["kv"]["scope"].split(","))
    reask = bool(grew & set(AWAY_WIDEN_REASK_SCOPES))
    return [(cls, lim) for cls, path, lim, _src in opens
            if path is None and cls in PREAPPROVAL_GRANT_CLASSES and not (reask and cls in AWAY_WIDEN_REASK_CLASSES)], None


def away_widen_allows(carried, given):
    """The new grant's allows= value at a widening: the carried classes, then
    the call's own allows= entries (already validated; an entry for a carried
    class replaces it — the operator's latest word), in
    PREAPPROVAL_GRANT_CLASSES order, a limit always written out. None when
    the set is empty (the record then carries no allows=)."""
    merged = dict(carried)
    if given is not None:
        for cls, lim in parse_grant_allows(given)[0]:
            merged[cls] = _preapproval_limit(cls, lim)
    if not merged:
        return None
    return ",".join(cls if merged[cls] is None else "%s:%d" % (cls, merged[cls])
                    for cls in PREAPPROVAL_GRANT_CLASSES if cls in merged)


def away_widen_plan(st, log_root, iso, kv_in):
    """D22 — `away grant … widens=<n>`: decide the call before anything is
    read for the new grant. Returns ("widen", grant n, carried classes, grant
    n's departure bytes) when grant n is BOUND and every condition holds; or
    ("replay", the bound grant n+1) when the widening already landed; every
    other case refuses, nothing written.
    The conditions, grant n bound: the new scope is a STRICT superset of
    grant n's; grant n's own departure file still digests to its departure=;
    no release act of grant n is in flight (away_release_open — unreadable
    evidence refuses); and none of the three folds `away check` prints reads
    unknown (holds, parks, the pre-approvals). The caller then requires the
    new departure file to BEGIN with the returned bytes.
    An interrupted widening — one write is not a transaction, and nothing
    here undoes a written prefix — has four outcomes, each with its retry:
    (1) nothing was written: grant n is still bound, the same call is the
    widening; (2) the end landed and the grant did not: grant n reads ended,
    the run is un-granted and never widened — refused, with the plain `away
    grant` to type instead, the carried classes as its allows=; (3) the grant
    line is torn: the policy log reads malformed, which is already the
    operator's stop — refused; (4) both landed and success was not reported:
    grant n+1 is bound at the requested scope with its departure file
    intact — the replay: printed, nothing written. In no outcome does the
    scope grow without the complete new grant."""
    w = parse_count(kv_in["widens"])
    if w is None or w < 1:
        refuse("away grant refused: widens= must be the bound grant's number — a positive integer (bad-widens)")
    scope = kv_in["scope"]
    if st["state"] in ("malformed", "wrong-identity"):
        refuse("away grant refused: widens=%d — the policy log is %s (line %d: %s); nothing is granted or widened on it — raise a must-pause (widen-log-%s)"
               % (w, st["state"], st["bad"][0], st["bad"][2], st["state"]))
    prior = next((x for x in st["grants"] if x["n"] == w), None)
    if prior is None:
        refuse("away grant refused: widens=%d names no recorded grant (%d recorded) (bad-widens)" % (w, len(st["grants"])))
    if st["state"] == "bound" and st["open"]["n"] == w + 1 and prior["end_kv"]["reason"] == "back":
        og = st["open"]
        if og["kv"]["scope"] == scope and _away_departure_digest(log_root, og["n"]) == og["kv"]["departure"]:
            return ("replay", og)
        refuse("away grant refused: widens=%d — grant %d is already bound (scope=%s) and is not this widening's result: its scope or its departure file differs from this call's; `away end` it first (widen-not-bound)"
               % (w, og["n"], og["kv"]["scope"]))
    if st["state"] != "bound" or st["open"]["n"] != w:
        if st["state"] == "ended" and st["grants"][-1]["n"] == w:
            carried, _prob = away_widen_carried(log_root, prior, scope)
            _al = (away_widen_allows(carried, kv_in.get("allows")) if carried is not None else None)
            refuse("away grant refused: widens=%d — grant %d is ENDED: the run is un-granted, never widened (a widening interrupted after its first record, or a grant ended since); nothing written (widen-prior-ended)" % (w, w),
                   "a plain grant at the new scope and file — away grant … scope=%s%s (no widens=), reading away-%d-departure.md%s"
                   % (scope, " allows=%s" % _al if _al else "", w + 1,
                      "" if carried is not None else "; the carried classes could not be read — take them from `away report … grant=%d` section 1" % w))
        refuse("away grant refused: widens=%d — grant %d is not the bound grant (log state %s%s) (widen-not-bound)"
               % (w, w, st["state"], ", grant %d open" % st["open"]["n"] if st["open"] else ""))
    old_toks, new_toks = set(prior["kv"]["scope"].split(",")), set(scope.split(","))
    if not old_toks < new_toks:
        refuse("away grant refused: widens=%d — scope=%s is not a strict superset of grant %d's scope=%s; a widening only adds (widen-scope-not-wider)"
               % (w, scope, w, prior["kv"]["scope"]))
    try:
        prior_dep = _away_read_bytes(_away_departure_path(log_root, w))
    except OSError as e:
        refuse("away grant refused: widens=%d — grant %d's departure file %s could not be read (%s) (departure-mismatch)"
               % (w, w, _away_departure_path(log_root, w), e))
    if hashlib.sha256(prior_dep).hexdigest()[:12] != prior["kv"]["departure"]:
        refuse("away grant refused: widens=%d — grant %d's departure file no longer digests to its departure=%s (departure-mismatch)"
               % (w, w, prior["kv"]["departure"]))
    acts, problems = away_release_open(log_root, st["grants"], prior)
    if problems:
        refuse("away grant refused: widens=%d reads every probe log under --log-root to find an act in flight, and %s — nothing written (fail-closed)"
               % (w, "; ".join(problems)))
    if acts:
        refuse("away grant refused: widens=%d — grant %d has a release act in flight — %s; record its outcome first — nothing written (widen-act-in-flight)"
               % (w, w, "; ".join("%s%s (%s:%d)" % (rkv.get("key", "?"), " path=%s" % rkv["path"] if rkv.get("path") else "", loc[0], loc[1])
                                  for rkv, loc in acts)))
    unknown = [r for r in (_away_holds_suffix(log_root, iso)[1], _away_parks_suffix(log_root)[1]) if r]
    carried, _prob = away_widen_carried(log_root, prior, scope)
    if carried is None:
        unknown.append("allows unknown: " + "; ".join(_prob))
    if unknown:
        refuse("away grant refused: widens=%d — `away check` reads unknown, and nothing widens on unknown: %s — nothing written (widen-unknown)"
               % (w, "; ".join(unknown)))
    return ("widen", prior, carried, prior_dep)


def cmd_away(flags, verb, kvs):
    """v34.0 D4/D5 — `away grant|end|check|report`, (v35.1) `ci-verdict`, and
    (v37.0) `census`: the away grant's ONE writer (grant/end append to the
    policy log) and ONE reader (check/report), every verb sharing
    away_state(); `ci-verdict` reads the state, then reads CI and appends its
    verdict to the run's probe log (Decision 4); `census` reads every policy
    log under --base and writes nothing (cmd_away_census); (v46.4 D5) `lint`
    reads the policy log and the departure file the NEXT grant would read,
    prints that file's warnings, and writes nothing; (v47.0) `grant` refuses a
    departure file with no answered `Usage fallback:` line (D5 — the one
    departure check that refuses) and, with `widens=<n>`, ends the bound
    grant n and binds grant n+1 in one write (D22, away_widen_plan).
    COMPOSER-ONLY: --role composer is
    the mis-attribution guard; the boundary is that spawned roles hold only
    the emit/escape-check grants (under perms=bypass nothing technical stops
    a caller — the pre-departure check says so)."""
    if flags["--role"] != "composer":
        refuse("away is a composer-seat subcommand — it requires --role composer (spawned-role grants never carry it; v34.0 D4)")
    if verb not in AWAY_VERBS:
        refuse("away needs a verb — one of %s (got %r)" % ("|".join(AWAY_VERBS), verb),
               "away %s --run <runkey> --role composer --policy-log </abs> --iso <iso-id> --plan <plan> [--log-root </abs>] [--base </abs>] ..."
               % "|".join(AWAY_VERBS))
    g = AWAY_VERB_GRAMMAR[verb]
    for f in flags:
        if f not in ("--run", "--role") and f not in g["flags"]:
            refuse("%s is not accepted by `away %s`" % (f, verb),
                   "`away %s` accepts: --run --role %s" % (verb, " ".join(sorted(g["flags"]))))
    # v46.4 (D3): ONE refusal names everything missing. With a required flag
    # missing, the verb's missing required keys are named beside it — read
    # from the key NAMES alone, since the key checks below have not run. With
    # every flag present those checks keep their place and the key refusal
    # after them names every missing key. The refusal is the ONE line it was:
    # with one item missing its stderr is v46.3's, byte for byte.
    missing = [f for f in g["required"] if f not in flags]
    if missing:
        given = set(k for k, _v in kvs)
        missing += ["%s=" % k for k in g["kvs_required"] if k not in given]
        refuse("away %s REQUIRES %s" % (verb, " ".join(missing)))
    seen = set()
    for k, v in kvs:
        if k in seen:
            refuse("duplicate key %s=" % k)
        seen.add(k)
        if k not in g["kvs"]:
            refuse("%s= is not accepted by `away %s` (admitted: %s)" % (k, verb, ", ".join(sorted(g["kvs"])) or "none"))
        check_field_safety(k, v)
    kv_in = dict(kvs)
    missing = ["%s=" % k for k in g["kvs_required"] if k not in kv_in]
    if missing:
        refuse("away %s REQUIRES %s" % (verb, " ".join(missing)))
    if verb == "census":
        # v37.0 Decision 8: before the identity reads below (census has none)
        return cmd_away_census(flags)
    pol = flags["--policy-log"]
    if not os.path.isabs(pol):
        refuse("--policy-log must be an absolute path")
    iso = flags["--iso"]
    if not ISO_ID_RE.match(iso):
        refuse("--iso %r is not a filename-safe iso-id" % iso[:60])
    plan = flags["--plan"]
    check_value_safety("plan", plan)
    if not plan.strip():
        refuse("--plan must be a nonblank identity string (the journal's plan= value; the file need not exist)")
    log_root = flags.get("--log-root")
    if log_root is not None and not os.path.isabs(log_root):
        refuse("--log-root must be an absolute path")
    if verb == "ci-verdict":
        # the verb's own usage rules, BEFORE any read (round 9 LOW-004): a
        # usage error is exit 2 whatever the policy log's state
        if not os.path.isabs(flags["--base"]):
            refuse("--base must be an absolute path (gh's working directory)")
        if parse_count(kv_in["pr"]) is None or parse_count(kv_in["pr"]) < 1:
            refuse("pr= must be the pull request number (ASCII digits, from 1)")
        if not CI_TIP_RE.match(kv_in["tip"]):
            refuse("tip= must be the checked commit's full 40-hex sha")
    lines, err = _away_read_policy(pol)
    if verb in ("check", "ci-verdict") and lines is None:
        # the unreadable-policy-log branch carries the fold's holds= too (v35.1)
        # — and, v44.0 D3, allows=unknown (no readable grant to bind to)
        _hs, _hreason = _away_holds_suffix(log_root, iso)
        _ps, _preason = _away_parks_suffix(log_root)
        _as, _areason = _away_allows_suffix(log_root, None)
        _tail = "; ".join(_away_q(x) for x in (_hreason, _preason, _areason) if x)
        sys.stdout.write('away: state=absent grants=0%s%s%s reason="policy log unreadable: %s%s"\n'
                         % (_hs, _ps, _as, _away_q(err)[:160], "; " + _tail if _tail else ""))
        sys.exit(3)
    if verb == "check":
        state, out = _away_check_line(away_state(lines, iso, plan), log_root, iso)
        sys.stdout.write(out + "\n")
        if state != "bound":
            sys.exit(3)
        return
    if verb == "ci-verdict":
        # v35.1 Decisions 1, 2, 4 — the helper's own CI read, in this order:
        # (1) the away state: unless bound with `merge` in scope, print the
        # `away:` line and exit 3, writing nothing; (2) the three reads under
        # one deadline; (3) the pure verdict; (4) the record through
        # write_lines (a failed write exits 3 through envfail, printing no
        # verdict line); (5) only then settled= over the log AS WRITTEN and
        # the one output line.
        base, pr, tip = flags["--base"], kv_in["pr"], kv_in["tip"]
        st = away_state(lines, iso, plan)
        state, out = _away_check_line(st, log_root, iso)
        scope = st["open"]["kv"]["scope"].split(",") if state == "bound" else []
        if state != "bound" or "merge" not in scope:
            sys.stdout.write(out + "\n")
            sys.exit(3)
        exe, override = gh_executable()  # after the state gate: a bad stub hook is a usage error only where a read would run
        deadline = time.monotonic() + GH_DEADLINE_S
        pr_read = run_gh("pr", exe, base, deadline, pr=pr)
        cr_read = st_read = (False, "", "the pull-request read did not establish host/owner/repo")
        ident = _ci_pr_repo(_ci_parse_json(pr_read[0], pr_read[1])[0])
        if ident:
            host, owner, repo = ident
            cr_read = run_gh("check-runs", exe, base, deadline, host=host, owner=owner, repo=repo, tip=tip)
            st_read = run_gh("status", exe, base, deadline, host=host, owner=owner, repo=repo, tip=tip)
        v = ci_verdict(pr_read, cr_read, st_read, tip)
        runkey = flags["--run"]
        detail = ci_sanitise("pr=%s head=%s checks=%d %s" % (pr, v["head"], v["checks"], v["reason"]), CI_DETAIL_LIMIT)
        kv = {"role": "composer", "iso": iso, "tip": tip, "verdict": v["verdict"]}
        # caller-ordered extras: the stamp BEFORE the quoted detail, so no
        # prefix of a stamped record is a writer-valid unstamped one (MED-003)
        extras = ([("gh", "override")] if override else []) + [("detail", detail)]
        kv.update(extras)
        validate_record("OWNERSHIP:ci-verdict", kv, role="composer")
        ts = now_iso()
        line, tokens = assemble_ownership_record("ci-verdict", ts, None, runkey,
                                                 ownership_required("ci-verdict", kv), kv, extras)
        probe = os.path.join(log_root, "%s-probe.log" % runkey)
        write_lines(probe, [line], token_lists=[tokens])
        raw, rerr = raw_record_lines(probe)
        settled = raw is not None and ci_settled(ci_history(raw, runkey), tip)
        parts = ["ci-verdict: verdict=%s settled=%s pr=%s tip=%s head=%s state=%s branch=%s base=%s mergeable=%s repo=%s checks=%d"
                 % (v["verdict"], "yes" if settled else "no", pr, tip, v["head"], v["state"], v["branch"], v["base"],
                    v["mergeable"], v["repo"], v["checks"])]
        if v["rerun"]:
            parts.append("rerun=%s" % ",".join(v["rerun"]))
        if override:
            parts.append("gh=override")
        parts.append('reason="%s"' % ci_sanitise(v["reason"], CI_DETAIL_LIMIT))
        sys.stdout.write(" ".join(parts) + "\n")
        return
    if verb == "report":
        st = away_state(lines or [], iso, plan)
        sel = st["grants"][-1] if st["grants"] else None
        if "grant" in kv_in:
            want = parse_count(kv_in["grant"])
            sel = next((x for x in st["grants"] if x["n"] == want), None) if want else None
            if sel is None:
                refuse("grant=%s names no recorded grant in the policy log (%d recorded)" % (kv_in["grant"], len(st["grants"])))
        out_path = flags.get("--out")
        if out_path is not None and not os.path.isabs(out_path):
            refuse("--out must be an absolute path")
        text = away_report_text(st, log_root, iso, sel, policy_err=err)
        if out_path is not None:
            try:
                with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
            except OSError as e:
                envfail("cannot write --out %s: %s" % (out_path, e))
        sys.stdout.write(text)
        return
    if verb == "lint":
        # v46.4 (plan-loop-field-review-fixes D5): the departure-file check
        # BEFORE the grant binds — READ-ONLY (two reads: the policy log, for
        # the next grant's number, and that grant's departure file; no record,
        # no file, no network, no git). The file is the one `away grant` would
        # read next, the warnings are the ones it would print (one function),
        # and — as there (KD7) — a warning never refuses: exit 0 whenever the
        # file was read, whatever the policy log's state. A missing or
        # unreadable file is `grant`'s refusal; an unreadable policy log is
        # its environment failure (exit 3). v47.0 (D5): the one check `grant`
        # REFUSES on — no answered `Usage fallback:` line — is reported here
        # as the word `usage-fallback-missing`, counted like any other, and
        # the exit stays 0: lint reports, it never refuses.
        if lines is None:
            envfail("cannot read --policy-log %s: %s" % (pol, err))
        n = len(away_state(lines, iso, plan)["grants"]) + 1
        _warnings = away_departure_warnings(_away_departure_bytes(log_root, n))
        for _w in _warnings:
            sys.stdout.write("away-lint: %s\n" % _w)
        sys.stdout.write("away-lint: file=%s warnings=%d\n"
                         % (os.path.basename(_away_departure_path(log_root, n)), len(_warnings)))
        return
    # grant / end — the two writes
    if lines is None:
        envfail("cannot read --policy-log %s: %s" % (pol, err))
    st = away_state(lines, iso, plan)
    ts = now_iso()
    runkey = flags["--run"]
    if verb == "grant":
        if "widens" not in kv_in and st["state"] not in ("absent", "ended"):
            why = ("grant %d is open — `away end` it first" % st["open"]["n"] if st["state"] == "bound"
                   else "the policy log is %s (%s) — no later grant is admitted for this run; raise a must-pause"
                   % (st["state"], "line %d: %s" % (st["bad"][0], st["bad"][2])))
            refuse("away grant refused: %s" % why)
        scope = kv_in["scope"]
        if not away_scope_ok(scope):
            refuse("scope=%s — comma-joined from %s in that order, unique, at least one; production requires staging, staging requires merge (bad-scope)"
                   % (scope, ",".join(AWAY_SCOPE_ORDER)))
        if "allows" in kv_in:
            # v44.0 D16: the departure-time pre-approvals — validated by the one
            # grammar the fold reads with, BEFORE the departure read (a grammar
            # refusal precedes every side effect of the verb, the warning
            # lines included); stored below AFTER the pinned fields and the
            # derived config_hash= (outside the hash; away_grant_hash untouched)
            _why = parse_grant_allows(kv_in["allows"])[1]
            if _why:
                refuse("away grant refused: %s" % _why,
                       "allows=<class>[:<n>][,<class>…] from %s — :<n> on pr-fix-cycles only" % ",".join(PREAPPROVAL_GRANT_CLASSES))
        # v47.0 (plan-loop-autonomy-group-2 T1.8 / D22): `widens=<n>` — the
        # one-step widening, the ONE form admitted while a grant is bound.
        # away_widen_plan decides it before anything is read for the new
        # grant: a refusal (nothing written), a replay (the widening already
        # landed — printed, nothing written), or the prior grant to end.
        widen = None
        if "widens" in kv_in:
            widen = away_widen_plan(st, log_root, iso, kv_in)
            if widen[0] == "replay":
                _rg = widen[1]
                sys.stdout.write("away: granted grant=%s scope=%s departure=%s config_hash=%s ts=%s%s\n"
                                 % (_rg["kv"]["grant"], _rg["kv"]["scope"], _rg["kv"]["departure"], _rg["kv"]["config_hash"],
                                    _rg["kv"]["ts"], " allows=%s" % _rg["kv"]["allows"] if "allows" in _rg["kv"] else ""))
                return
        n = len(st["grants"]) + 1
        dep_bytes = _away_departure_bytes(log_root, n)   # missing or unreadable → refused, nothing written
        dep = hashlib.sha256(dep_bytes).hexdigest()[:12]
        # v47.0 (D5): the ONE departure check that refuses — a file with no
        # answered `Usage fallback:` line never binds. After the bytes are
        # read and before the first warning line; nothing is written.
        if not away_departure_has_fallback(dep_bytes):
            refuse("away grant refused: the departure file %s holds no answered `Usage fallback:` line (departure-missing-fallback) — every departure answers what takes over when the executor's account runs out; nothing written"
                   % _away_departure_path(log_root, n),
                   "one line in the departure file's Answers block: `Usage fallback: <profile dir>`, `Usage fallback: none — <why>; the run stops on exhaustion (stop 4)`, or `Usage fallback: n/a — <why>` — `away lint` reports it as usage-fallback-missing")
        allows = kv_in.get("allows")
        if widen is not None:
            # D22: the new file keeps the old file's bytes — it can add lines
            # and never remove one — and the classes in force are carried
            _prior, _carried = widen[1], widen[2]
            if not dep_bytes.startswith(widen[3]):
                refuse("away grant refused: widens=%d — the new departure file %s does not begin with the bytes of grant %d's departure file; a widening adds to the departure file and never rewrites it (widen-not-prefix) — nothing written"
                       % (_prior["n"], _away_departure_path(log_root, n), _prior["n"]))
            allows = away_widen_allows(_carried, allows)
        # v44.0 A9 / D9: the effective-set warning over the bytes just read
        # (v46.4 D6: and the quoted-heading warning, from the same function) —
        # stderr only; the digest is of these unchanged bytes, the record and
        # the exit are untouched (KD7: a warning, never a refusal — the
        # fallback check above is the one exception, v47.0 D5)
        for _w in away_departure_warnings(dep_bytes):
            sys.stderr.write("away-warning: %s\n" % _w)
        kv = {"role": "composer", "iso": iso, "plan": plan, "grant": str(n), "scope": scope,
              "departure": dep, "config_hash": away_grant_hash(iso, plan, str(n), scope, dep)}
        if allows is not None:
            kv["allows"] = allows   # validated above, before the departure read (a widening's: built from the fold)
        st_name = "away-grant"
        if widen is not None:
            # D22: the two EXISTING record shapes in ONE write — grant n's end
            # with reason=back, then grant n+1. One write is not a
            # transaction: away_widen_plan owns what a retry does after an
            # interrupted one. `widens=` is stored on neither record.
            _ekv = {"role": "composer", "iso": iso, "plan": plan, "grant": str(_prior["n"]), "reason": "back"}
            validate_record("OWNERSHIP:away-end", _ekv, role="composer")
            validate_record("OWNERSHIP:away-grant", kv, role="composer")
            _eline, _etok = assemble_ownership_record("away-end", ts, None, runkey,
                                                      ownership_required("away-end", _ekv), _ekv, [])
            _gline, _gtok = assemble_ownership_record("away-grant", ts, None, runkey,
                                                      ownership_required("away-grant", kv), kv, [])
            write_lines(pol, [_eline, _gline], token_lists=[_etok, _gtok])
            sys.stdout.write("away: ended grant=%d reason=back ts=%s\n" % (_prior["n"], ts))
            sys.stdout.write(_away_report_recipe(runkey, pol, iso, plan, log_root, str(_prior["n"])))
            sys.stdout.write("away: granted grant=%s scope=%s departure=%s config_hash=%s ts=%s%s\n"
                             % (kv["grant"], scope, kv["departure"], kv["config_hash"], ts,
                                " allows=%s" % kv["allows"] if "allows" in kv else ""))
            return
    else:
        if st["state"] != "bound":
            refuse("away end refused: no grant is open (log state %s)" % st["state"])
        want = parse_count(kv_in["grant"])
        if want != st["open"]["n"]:
            refuse("away end refused: grant=%s is not the open grant %d" % (kv_in["grant"], st["open"]["n"]))
        if kv_in["reason"] not in AWAY_END_REASONS:
            refuse("reason= must be one of %s (bad-away-reason)" % "|".join(sorted(AWAY_END_REASONS)))
        if log_root is not None and kv_in["reason"] == "release-done":
            # v40.0 Phase 1 (D5 — the helper's half of "release-done after the
            # LAST group"): the modern end REQUIRES --base and is admitted only
            # while the run's isolation journal reads one of exactly three
            # closed states (AWAY_RELEASE_DONE_STATES); every other state —
            # `active` (a group closed, the next unstarted; a park at the final
            # group), `merging`, `paused`, `crashed/recovery-needed`,
            # `merge-failed` — refuses `run-not-closed state=<s>`, nothing
            # written. A missing or unreadable journal is fail-closed. The
            # legacy end without --log-root (the v37.0 shape) is untouched.
            base = flags.get("--base")
            if base is None:
                refuse("away end reason=release-done with --log-root REQUIRES --base </abs/base> (v40.0 D5: the end is admitted only once the run has closed — the helper reads <base>/.cursor/loops/<iso>-isolation)",
                       "away end --run <runkey> --role composer --policy-log </abs> --iso <iso-id> --plan <plan> --log-root </abs> --base </abs/base> grant=<n> reason=release-done")
            if not os.path.isabs(base):
                refuse("--base must be an absolute path")
            jpath = os.path.join(base, ".cursor", "loops", "%s-isolation" % iso)
            try:
                with open(jpath, encoding="utf-8") as jf:
                    jraw = jf.read().splitlines()
            except (OSError, UnicodeDecodeError) as e:
                refuse("away end refused: run-not-closed state=%s — the run's journal %s could not be read (%s); reason=release-done ends a grant only after the final close — nothing written (the operator's \"back\" still ends it)"
                       % ("absent" if isinstance(e, FileNotFoundError) else "unreadable", jpath, e))
            jkv_end = _rc_parse_kv_lines(jraw)[0]
            if jkv_end.get("iso") != iso:
                # the identity bind every journal reader applies (run-close:
                # "journal iso missing or mismatched") — a --base pointing at
                # another repository's journal admits nothing
                refuse("away end refused: the journal %s records iso=%s, not %s — wrong identity; nothing written"
                       % (jpath, jkv_end.get("iso", "(none)"), iso))
            jst = jkv_end.get("state", "")
            jtok = jst.split()[0] if jst.split() and _PRIOR_STATE_RE.match(jst.split()[0]) else "unrecognized"
            if jst not in AWAY_RELEASE_DONE_STATES:
                refuse("away end refused: run-not-closed state=%s — reason=release-done ends the grant only after the FINAL close (journal %s); a park at any release group keeps the grant bound, and the next group's close resumes under it — nothing written (the operator's \"back\" still ends it)"
                       % (jtok, " | ".join(AWAY_RELEASE_DONE_STATES)))
        elif flags.get("--base") is not None:
            refuse("--base is accepted by `away end` only with reason=release-done and --log-root (the closed-run gate) — got reason=%s%s"
                   % (kv_in["reason"], "" if log_root is not None else " without --log-root"))
        if log_root is not None and kv_in["reason"] in AWAY_AUTO_END_REASONS:
            # v37.0 Decision 2 (the helper's half): an automatic end never
            # strips a grant mid-release. The open grant's release acts are
            # read through the report's own join (_away_classify →
            # away_release_pairing); evidence that cannot be read refuses
            # (fail-closed). `back` / `autonomy-off` and the legacy end
            # without --log-root are untouched. Nothing is written above.
            _open_acts, problems = away_release_open(log_root, st["grants"], st["open"])
            if problems:
                refuse("away end refused: reason=%s reads every probe log under --log-root to find an act in flight, and %s"
                       " — nothing written (fail-closed; the operator's \"back\" still ends it)"
                       % (kv_in["reason"], "; ".join(problems)))
            if _open_acts:
                acts = ["%s%s started; outcome not recorded — record its outcome first (%s:%d)"
                        % (rkv.get("key", "?"), " path=%s" % rkv["path"] if rkv.get("path") else "", loc[0], loc[1])
                        for rkv, loc in _open_acts]
                refuse("away end refused: grant %d has a release act in flight — %s; reason=%s never ends a grant mid-release"
                       " — nothing written (the operator's \"back\" still ends it)"
                       % (st["open"]["n"], "; ".join(acts), kv_in["reason"]))
        kv = {"role": "composer", "iso": iso, "plan": plan, "grant": str(want), "reason": kv_in["reason"]}
        st_name = "away-end"
    validate_record("OWNERSHIP:" + st_name, kv, role="composer")
    line, tokens = assemble_ownership_record(st_name, ts, None, runkey,
                                             ownership_required(st_name, kv), kv, [])
    write_lines(pol, [line], token_lists=[tokens])
    if verb == "grant":
        sys.stdout.write("away: granted grant=%s scope=%s departure=%s config_hash=%s ts=%s%s\n"
                         % (kv["grant"], scope, kv["departure"], kv["config_hash"], ts,
                            " allows=%s" % kv["allows"] if "allows" in kv else ""))
    else:
        sys.stdout.write("away: ended grant=%s reason=%s ts=%s\n" % (kv["grant"], kv["reason"], ts))
        sys.stdout.write(_away_report_recipe(runkey, pol, iso, plan, log_root, kv["grant"]))


# ---- v40.0 Phase 0 (plan-one-run-per-plan T0.1 / D8): the `quoted-block` subcommand ----
# READ-ONLY and identity-less (the run-close pattern — a top-level subcommand,
# never an `away` verb, so cmd_away's pre-identity carve-out stays `census`
# alone): compares the bytes of ONE heading-scoped markdown block of a file
# between two sides and prints ONE stdout line; no record, no journal, no
# file is written, so the oracle learns no line — the selftest is its gate.
# The reader: /close-run → Under an away grant item 4's quoted-block contract
# (the pull request's diff), read again by item 5 (the fetched base against
# the departure file's recorded blob) and item 10 (the merged base), and by
# the execute-loop SKILL's effective-set readers (Release work items 3–5,
# Widening's inventory) — one contract, so an edit outside the quoted block
# admitted before a merge is never a machinery-change failure after it.
# v42.0 (plan-loop-field-fixes T0.4 / D1, D10): refresh-aware — the grant's
# `set-refresh` records (`OWNERSHIP: auto-disposition`, a documented free key
# class, choice=requoted|refreshed, the free keys file= heading= from= to=
# workflow_class=) are ACCEPTED VERSIONS folded here (_qb_accepted_versions),
# heading-scoped, never a replacement of --from; --baseline and the optional
# --heading (blob mode) are the readers' opt-ins. Still no record written, no
# verb, no enum (set-refresh stays outside AWAY_RELEASE_CLASSES).
_QB_FENCE_RE = re.compile(r"\A {0,3}(`{3,}|~{3,})")
# round 7 LOW-001: CommonMark's 0–3 leading spaces; round 10 PR-LOW-001: an EMPTY heading (hashes alone, with or
# without trailing blanks) is a heading too — the separator-and-text group is optional, so `##` is a boundary while
# `##A` (no separator) and a seven-hash line stay excluded.
_QB_HEADING_RE = re.compile(r"\A {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*\Z")
_QB_VERDICT_EXIT = {"same": 0, "changed": 0, "missing": 2, "ambiguous": 2}


def _qb_git_bytes(base, *args):
    """git under <base>, stdout as RAW BYTES (no text decoding, no stripping —
    the block comparison is byte-exact). Returns (rc, stdout bytes, stderr str)."""
    try:
        r = subprocess.run([_git_bin(), "-C", base] + list(args), capture_output=True, timeout=60, env=_git_env())
    except Exception as e:
        return 1, b"", "git failed: %s" % e
    return r.returncode, r.stdout or b"", (r.stderr or b"").decode("utf-8", "replace").strip()


def _qb_blocks(data, heading):
    """Every heading-scoped block of `data` (bytes) whose ATX heading text
    equals `heading` VERBATIM (inline code, trailing punctuation, closing
    hashes included; trailing spaces/tabs and the line ending excluded). A
    block runs from its heading line through the line before the next heading
    of equal or higher level (as many `#` or fewer — an EMPTY heading, hashes
    alone, is a boundary too; it never matches a target, since the target is
    nonempty), or to the end of the file. A line inside a fenced code block (``` or ~~~ with up to three
    leading spaces — a backtick opener whose info string holds another
    backtick is NOT a fence, a tilde opener's may; closed by a line of at
    least as many of the same fence character and nothing else, else the
    fence runs to the end of the file) is never a heading — a `# comment`
    in a quoted shell procedure neither ends a block nor matches one. Setext
    (underlined) headings are not headings here. Returns a list of byte
    blocks, one per matching heading: zero = missing, two or more = ambiguous."""
    lines = data.splitlines(keepends=True)
    heads = []  # (line index, level, text)
    fence = None  # (fence char, fence length) while inside a fence
    for i, raw in enumerate(lines):
        line = raw.decode("utf-8", "surrogateescape").rstrip("\r\n")
        m = _QB_FENCE_RE.match(line)
        if fence is not None:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1] and line.strip() == m.group(1):
                fence = None
            continue
        if m:
            # round 9 PR-MED-001: a backtick fence's info string may not hold a
            # backtick (CommonMark) — such a line is plain text, never an
            # opener that would hide every later heading; a tilde fence's
            # info string may hold one. A plain line starting with backticks
            # cannot be a heading either, so it simply passes.
            if m.group(1)[0] == "`" and "`" in line[m.end():]:
                continue
            fence = (m.group(1)[0], len(m.group(1)))
            continue
        h = _QB_HEADING_RE.match(line)
        if h:
            heads.append((i, len(h.group(1)), h.group(2) or ""))
    out = []
    for n, (i, level, text) in enumerate(heads):
        if text != heading:
            continue
        end = len(lines)
        for j, lvl, _t in heads[n + 1:]:
            if lvl <= level:
                end = j
                break
        out.append(b"".join(lines[i:end]))
    return out


def _qb_side(base, file_rel, heading, side, arg):
    """Resolve ONE side of the comparison. `arg` is a blob id (the departure
    file's recorded blob — the bytes themselves, `cat-file -p`) or a
    commit-ish (a ref, a sha, a tag — <file> read at that commit as the raw
    blob, `cat-file -p <sha>:<file>`; no textconv, no filter, on either
    side). Returns (full sha printed as <side>=, verdict-or-None,
    blocks): the verdict is `missing` when the file is absent at a commit or
    no heading matches, `ambiguous` when more than one does; a side whose
    argument does not resolve is a usage refusal (exit 2, nothing printed)."""
    rc, out, err = _qb_git_bytes(base, "cat-file", "-t", arg)
    if rc != 0:
        refuse("--%s %r does not resolve to a git object under --base (%s)" % (side, arg[:80], err[:160]),
               "--from / --to: a commit-ish (a ref, a sha, a tag) or a blob id")
    kind = out.decode("ascii", "replace").strip()
    if kind == "blob":
        rc, sha_b, err = _qb_git_bytes(base, "rev-parse", "--verify", arg)
        if rc != 0:
            refuse("--%s %r: blob id did not resolve (%s)" % (side, arg[:80], err[:160]))
        sha = sha_b.decode("ascii", "replace").strip()
        rc, data, err = _qb_git_bytes(base, "cat-file", "-p", sha)
        if rc != 0:
            envfail("--%s: git cat-file -p %s failed (%s)" % (side, sha, err[:160]))
    elif kind in ("commit", "tag"):
        rc, sha_b, err = _qb_git_bytes(base, "rev-parse", "--verify", arg + "^{commit}")
        if rc != 0:
            refuse("--%s %r: commit did not resolve (%s)" % (side, arg[:80], err[:160]))
        sha = sha_b.decode("ascii", "replace").strip()
        # round 7 MED-001 (corrected to LOW in place): the RAW blob at
        # <sha>:<file> — `cat-file -p`, never `git show`, which MAY apply a
        # configured textconv filter to a blob (version-dependent: the
        # selftest's premise row observed raw output on this host) and would
        # then make this side a filtered view while the blob side is raw
        # bytes; `cat-file -p` is the documented raw read, symmetric with the
        # blob side by construction. A path that is not a blob there (absent,
        # a tree, a submodule) is `missing`, never a listing.
        rc, kind_at, err = _qb_git_bytes(base, "cat-file", "-t", "%s:%s" % (sha, file_rel))
        if rc != 0 or kind_at.decode("ascii", "replace").strip() != "blob":
            return sha, "missing", []
        rc, data, err = _qb_git_bytes(base, "cat-file", "-p", "%s:%s" % (sha, file_rel))
        if rc != 0:
            envfail("--%s: git cat-file -p %s:%s failed (%s)" % (side, sha, file_rel, err[:160]))
    else:
        refuse("--%s %r is a %s object — a commit-ish or a blob id is expected" % (side, arg[:80], kind))
    if heading is None:
        # v42.0 (D1 blob mode): no heading — the whole blob is the one "block"
        # (`ambiguous` never; `missing` only when the path is no blob at a commit)
        return sha, None, [data]
    blocks = _qb_blocks(data, heading)
    if not blocks:
        return sha, "missing", blocks
    if len(blocks) > 1:
        return sha, "ambiguous", blocks
    return sha, None, blocks


def _qb_rebaseline_shape(kv):
    """The ONE eligibility rule for the helper-written re-baseline (round 12
    PR-REG-1201), shared by the version reader (_qb_accepted_versions) and the
    group close's existence check (_rc_rebaseline): a writer-valid set-refresh
    record with choice=rebaselined and NEITHER file= nor heading= (D1's shape —
    the helper never writes those keys on it). A record carrying either is
    skipped by the reader and is therefore no evidence for the close."""
    return kv.get("choice") == "rebaselined" and "file" not in kv and "heading" not in kv


def _qb_accepted_versions(base_real, file_rel, heading, log_root, grant, away_check):
    """v42.0 D1 — the fold: every `OWNERSHIP: auto-disposition` of key class
    `set-refresh` under grant `grant` for `file_rel`, across every
    `stage-*-probe.log` directly under `log_root` (the permissive
    _away_probe_records reader, stage-ordered then append-ordered), BOUND to
    the grant (round 13 PR-MED-018): its away= must parse to `grant` AND its
    away_check= must equal `away_check` byte for byte — the grant's
    config_hash the reader passes (the same value the composer wrote on the
    record; the hash binds iso / plan / grant / scope / departure, so a
    same-number record of another grant or a log copied from another run
    never folds — no policy-log read, the subcommand stays identity-less) —
    and a COMPLETED refresh: choice=requoted|refreshed (D10's two choices; a
    `start` or any other choice is not a refresh and is skipped, the shape
    the writer refuses for this class). Kept —
    in block mode — only when its heading= equals `heading` and — in blob
    mode (heading None) — only when it carries no heading= key (heading-
    scoped: a heading's record never covers another heading of the same file;
    a headingless record covers whole-blob readers only). Each kept record's
    to= (40-hex, then resolved through _qb_side like a side — a commit id or a
    blob id) is one ACCEPTED VERSION. Returns [(block bytes, ts, "<log>:<line>",
    workflow_class or None)] in reader order. REFUSES (exit 2 — the reader
    parks, never a silent requote): an unlistable or unreadable log, a kept
    record whose to= is not 40-hex, does not resolve, or names an object that
    is neither a commit nor a blob (a tree, a tag — a record copies a PRINTED
    to=, never a tag id) — each refusal naming the record's log line, never
    the reader's own --to — or one whose to= yields
    no single block for the heading. A line the writer would not have
    emitted (emittable_record) is not a record and is skipped; the records
    are never written to — the fold reads only.
    v44.0 (plan-away-autonomous-rails T0.2 / D5): a kept record with
    choice=rebaselined — the group close's re-baseline at the group's MERGE
    COMMIT (_rc_rebaseline; no file=, no heading=) — BYPASSES the file= filter
    and both heading filters: its to= must be a COMMIT (a blob to= refuses as
    a bad record does; a tag the same), the fold reads <to>:<file> through
    _qb_side exactly like a side — block mode the heading's block, blob mode
    the blob — and SKIPS the record (never a refusal) when that read is
    `missing` or `ambiguous`: a file absent at <to>, or a heading moved or
    duplicated there, simply gets no accepted version from it (the reader's
    own sides keep their precedence). A VERSION source only — never set
    membership, never a change to the outer verdict contract. The whitelist
    is requoted | refreshed | rebaselined: A1's audit choices (removed |
    heading-missing | heading-ambiguous) and every other choice are skipped
    like a `start`, so the malformed-record guard below is untouched."""
    records, problems = _away_probe_records(log_root)
    if problems:
        refuse("--log-root %s: %s" % (log_root, "; ".join(problems)),
               "an existing directory whose stage-*-probe.log files are readable")
    out = []
    for raw, loc in records:
        kv, _bare, why = emittable_record(raw, "OWNERSHIP:auto-disposition")
        if why:
            continue
        if _away_act_class(kv.get("key")) != "set-refresh" or parse_count(kv.get("away", "")) != grant:
            continue
        if kv.get("away_check") != away_check or kv.get("choice") not in ("requoted", "refreshed", "rebaselined"):
            continue   # another grant's hash, or not a completed refresh (round 13 PR-MED-018)
        rebased = kv.get("choice") == "rebaselined"
        if rebased:
            if not _qb_rebaseline_shape(kv):
                continue   # not the helper's shape (D1: no file=, no heading=) — no accepted version from it, never a refusal
        else:
            if kv.get("file") != file_rel:
                continue
            if heading is None:
                if "heading" in kv:
                    continue
            elif kv.get("heading") != heading:
                continue
        to = kv.get("to", "")
        where = "%s:%d" % loc
        if not _FULL_SHA_RE.match(to):
            refuse("set-refresh record at %s: to=%r is not a 40-hex commit or blob id — the fold cannot accept it (the reader parks)" % (where, to[:80]))
        rc, kind_b, _err = _qb_git_bytes(base_real, "cat-file", "-t", to)
        if rc != 0:
            refuse("set-refresh record at %s: to=%s does not resolve to a git object under --base — the fold cannot accept it (the reader parks)" % (where, to))
        kind = kind_b.decode("ascii", "replace").strip()
        if kind not in ("blob", "commit"):
            # Step H round 25 LOW-003 / round 29 PR-LOW-001: the kind is judged HERE,
            # naming the record — _qb_side's own refusals are worded for the reader's
            # --to flag. A record's to= copies a PRINTED to= — the peeled commit sha
            # or the blob sha — so a tag id (of anything) is never a record value.
            refuse("set-refresh record at %s: to=%s is a %s object — a record's to= is the printed commit or blob id, never a tag (the fold cannot accept it; the reader parks)" % (where, to, kind))
        if rebased and kind != "commit":
            refuse("set-refresh record at %s: a rebaselined record's to=%s must be the group's merge COMMIT, not a %s — the fold cannot accept it (the reader parks)" % (where, to, kind))
        _sha, verdict, blocks = _qb_side(base_real, file_rel, heading, "to", to)
        if verdict is not None:
            if rebased:
                continue   # D5: no accepted version from the re-baseline for this file / heading — never a refusal
            refuse("set-refresh record at %s: to=%s yields no single block for the heading (%s) — the fold cannot accept it (the reader parks)" % (where, to, verdict))
        out.append((blocks[0], kv.get("ts", ""), where, kv.get("workflow_class")))
    return out


def cmd_quoted_block(flags, kvs):
    """`quoted-block --base </abs/base> --file <repo-relative> [--heading <text>]
    --from <commit-ish|blob> --to <commit-ish|blob> [--baseline <commit-ish|blob>]
    [--log-root </abs> grant=<n> away_check=<12-hex>]` — prints ONE line
    `quoted-block file=<f> [heading=<h>] from=<sha> to=<sha>
    verdict=same|changed|missing|ambiguous[ detail=<side>] accepted=<n>
    matched=from|baseline|<ts>|none [matched_at=<log>:<line>]
    [matched_class=<c>] mode=block|blob` and exits 0 on same | changed, 2 on
    missing | ambiguous (the line still printed — the reader routes on
    verdict=); a grammar or resolution refusal exits 2 with nothing on stdout.
    v42.0 (D1, refresh-aware): --heading is OPTIONAL — absent, the whole blob
    of <file> at each side is compared (mode=blob; `ambiguous` never; a path
    that is no blob at a commit is `missing`), for a refreshed workflow or
    configuration path. --log-root </abs> with the keys grant=<n> and
    away_check=<the grant's 12-hex config_hash> (all three or none; the
    directory must exist) folds the grant's `set-refresh` records for the
    file and the heading (block mode) or the headingless ones (blob mode) —
    _qb_accepted_versions: a record folds only with THIS grant's number AND
    hash and a completed choice (requoted|refreshed; round 13 PR-MED-018) —
    as ACCEPTED VERSIONS; --baseline
    (optional; the reader's opt-in — item 4 passes the departure's recorded
    blob for a Markdown quoted-procedure file) is resolved like a side and
    joins the accepted set. The verdict is reached in today's order: BOTH
    original sides first — `missing` on either wins (detail=from|to|both),
    then `ambiguous` (the same detail), each with matched=none and no accepted
    version consulted — and only when both sides yield one block (one blob) is
    it `same` when the --to block equals the --from block, the --baseline
    block, or ANY accepted version's (in that order — the first equal version
    is the match: matched=from|baseline|<the record's ts>, a record match
    also printing matched_at=<its log>:<line> and, when it carries
    workflow_class=, matched_class=<value>), `changed` when it equals none
    (matched=none); --from is never replaced. accepted=<n> counts the records
    folded (0 without --log-root). A --baseline that yields no single block,
    an unreadable log, or a record whose to= is malformed, unresolvable, or
    yields no single block refuses — exit 2, nothing printed: the reader
    parks. Writes nothing anywhere (the log root is read only)."""
    base = flags.get("--base")
    file_rel = flags.get("--file")
    heading = flags.get("--heading")
    side_from = flags.get("--from")
    side_to = flags.get("--to")
    baseline = flags.get("--baseline")
    log_root = flags.get("--log-root")
    if base is None or file_rel is None or side_from is None or side_to is None:
        refuse("quoted-block requires --base </abs/base> --file <repo-relative path> --from <commit-ish|blob> --to <commit-ish|blob> (and --heading <heading text> for block mode — absent, the whole blob is compared)")
    # v42.0 D1: the TWO admitted keys — grant=<positive integer> and
    # away_check=<the grant's 12-hex config_hash> (round 13 PR-MED-018), each
    # exactly once, beside --log-root (all three or none)
    grant = None
    away_check = None
    for k, v in kvs:
        if k == "grant":
            if grant is not None:
                refuse("duplicate grant= — exactly one")
            grant = parse_count(v)
            if grant is None or grant < 1:
                refuse("grant= must be a positive integer — the bound grant's number (got %r)" % v[:40])
        elif k == "away_check":
            if away_check is not None:
                refuse("duplicate away_check= — exactly one")
            if not HEX12_RE.match(v):
                refuse("away_check= must be the grant's config_hash — 12 lowercase hex (got %r)" % v[:40])
            away_check = v
        else:
            refuse("quoted-block accepts the keys grant=<n> and away_check=<config_hash> only (the fold's grant identity, beside --log-root) — got %s=" % k)
    if not (log_root is None and grant is None and away_check is None) \
            and not (log_root is not None and grant is not None and away_check is not None):
        refuse("--log-root </abs>, grant=<n>, and away_check=<config_hash> travel together — all three or none (the fold's inputs: the records' root and the grant identity they must carry)")
    if log_root is not None:
        if not os.path.isabs(log_root):
            refuse("--log-root must be an absolute path")
        if not os.path.isdir(log_root):
            refuse("--log-root %s is not an existing directory" % log_root[:200])
    if not os.path.isabs(base):
        refuse("--base must be an absolute path")
    if not os.path.isdir(base):
        envfail("--base %s is not a directory" % base)
    base_real = canon_path(base)
    # round 49 (PC1 leg (c), run 5): a `/`-rooted --file is refused on EVERY host — os.path.isabs is the
    # interpreter's flavour, and on a Windows host it calls `/abs/deploy.md` relative (no drive), so the
    # rule let it through to a `missing` verdict there. On POSIX the added test repeats what isabs said.
    if file_rel == "" or os.path.isabs(file_rel) or file_rel.startswith("/") or file_rel.startswith("-") or ".." in file_rel.split("/"):
        refuse("--file must be a nonempty repo-relative path with no `..` segment (got %r)" % file_rel[:80])
    check_value_safety("file", file_rel)
    if heading is not None:
        if heading.strip() == "":
            refuse("--heading must be a nonempty heading text (the ATX heading line's text after its `#`s, verbatim)")
        check_value_safety("heading", heading)
    sides = [("from", side_from), ("to", side_to)]
    if baseline is not None:
        sides.append(("baseline", baseline))
    for side, arg in sides:
        if arg == "" or arg.startswith("-") or any(ch.isspace() for ch in arg):
            refuse("--%s must be a commit-ish or a blob id — nonempty, no whitespace, never starting with `-` (got %r)" % (side, arg[:80]))
        check_value_safety(side, arg)
    rc, _out, err = _qb_git_bytes(base_real, "rev-parse", "--git-dir")
    if rc != 0:
        envfail("--base %s is not a git checkout (%s)" % (base, err[:160]))
    from_sha, from_v, from_blocks = _qb_side(base_real, file_rel, heading, "from", side_from)
    to_sha, to_v, to_blocks = _qb_side(base_real, file_rel, heading, "to", side_to)
    # the accepted set (v42.0 D1): the --baseline block, then the folded records
    # — resolved now so accepted= is always the folded count and a malformed
    # input always refuses; CONSULTED only in the equality branch below
    baseline_block = None
    if baseline is not None:
        _bsha, b_v, b_blocks = _qb_side(base_real, file_rel, heading, "baseline", baseline)
        if b_v is not None:
            refuse("--baseline %r yields no single block for the heading (%s) — it cannot join the accepted set (the reader parks)" % (baseline[:80], b_v))
        baseline_block = b_blocks[0]
    accepted = []
    if log_root is not None:
        accepted = _qb_accepted_versions(base_real, file_rel, heading, log_root, grant, away_check)
    detail = None
    matched, matched_at, matched_class = "none", None, None
    if from_v == "missing" or to_v == "missing":
        verdict = "missing"
        detail = "both" if (from_v == "missing" and to_v == "missing") else ("from" if from_v == "missing" else "to")
    elif from_v == "ambiguous" or to_v == "ambiguous":
        verdict = "ambiguous"
        detail = "both" if (from_v == "ambiguous" and to_v == "ambiguous") else ("from" if from_v == "ambiguous" else "to")
    else:
        target = to_blocks[0]
        if target == from_blocks[0]:
            verdict, matched = "same", "from"
        elif baseline_block is not None and target == baseline_block:
            verdict, matched = "same", "baseline"
        else:
            verdict = "changed"
            for block, ts, where, wclass in accepted:
                if block == target:
                    verdict, matched, matched_at, matched_class = "same", ts, where, wclass
                    break
    parts = ["quoted-block", fmt_kv("file", file_rel)]
    if heading is not None:
        parts.append(fmt_kv("heading", heading))
    parts += [fmt_kv("from", from_sha), fmt_kv("to", to_sha), fmt_kv("verdict", verdict)]
    if detail is not None:
        parts.append(fmt_kv("detail", detail))
    parts += [fmt_kv("accepted", "%d" % len(accepted)), fmt_kv("matched", matched)]
    if matched_at is not None:
        parts.append(fmt_kv("matched_at", matched_at))
    if matched_class is not None:
        parts.append(fmt_kv("matched_class", matched_class))
    parts.append(fmt_kv("mode", "blob" if heading is None else "block"))
    sys.stdout.write(" ".join(parts) + "\n")
    sys.stdout.flush()
    code = _QB_VERDICT_EXIT[verdict]
    if code:
        sys.exit(code)


# ---- v47.0 (plan-loop-autonomy-group-2 T1.4 / D7, D9): the `records-delta`
# subcommand — the records-path reader. READ-ONLY and identity-less (the
# quoted-block pattern: a top-level subcommand, never an `away` verb, since it
# is used outside a grant too): it classifies a set of changed paths against
# ONE of two path alphabets and prints what it found; no record, no journal,
# no file is written, so the oracle learns no line — the selftest is its gate.
#   records (D7) — a RECORDS file: any `CHANGELOG.md`, at any depth; the root
#     `AGENTS.md`; everything under `.cursor/plans/`; plus what the caller
#     declares (--also, and every `Records paths:` line of a --departure
#     file): exact repo-relative paths and directory prefixes (a prefix ends
#     in `/` and means everything under it), in the hold records' path
#     alphabet — no wildcards, so each entry has one meaning. A PROTECTED
#     location is never a records file, whatever is declared: a spawn
#     dependency, and anything under a directory named .github, scripts,
#     .claude, .agents or .codex — at ANY depth (`tools/scripts/x.sh` is
#     protected like `scripts/x.sh`). The exclusion is applied twice — to
#     each declaration (a path under a protected directory, a prefix that is
#     one or lies under one, a spawn dependency or a prefix above one,
#     refuses) and to every path classified. A declaration is NOT refused for
#     what may sit under it later: `tools/` is admitted, and it is the second
#     test that keeps `tools/scripts/deploy.sh` off the fast path.
#   docs (D9) — the docs floor: a Markdown file (`.md`) that is not an
#     INSTRUCTION surface — any SKILL.md, STICKY.md, AGENTS.md, CLAUDE.md or
#     bootstrap.md, and anything under a directory named .claude, .agents,
#     .codex or .github (Step HA3, round 29 SEC-003: `.github/` holds agent
#     instruction files — `copilot-instructions.md` — and the records
#     alphabet already protects it), or under .cursor/rules, .cursor/commands,
#     .cursor/templates or .cursor/bootstrap — at any depth. A non-Markdown
#     file never passes, wherever it sits.
# A path outside the hold records' path alphabet is in neither set.
RECORDS_SPAWN_DEPENDENCIES = ("scripts/loop-journal.py", "scripts/loop-spawn-wrapper.sh", "scripts/loop-spawn-wrapper.py",
                              "scripts/loop-peer-launcher.py", "scripts/loop-history-check.py")
RECORDS_PROTECTED_DIRS = (".github", "scripts", ".claude", ".agents", ".codex")
DOCS_INSTRUCTION_NAMES = ("SKILL.md", "STICKY.md", "AGENTS.md", "CLAUDE.md", "bootstrap.md")
DOCS_INSTRUCTION_DIRS = (".claude", ".agents", ".codex", ".github")
DOCS_INSTRUCTION_CURSOR_DIRS = ("rules", "commands", "templates", "bootstrap")
RECORDS_DELTA_ALPHABETS = ("records", "docs")
RECORDS_WORKTREE_WORD = "WORKTREE"
# The conflict-marker scan (round 9 PR-MED-017). Git writes its markers at
# the path's `conflict-marker-size` attribute — seven when it is unspecified,
# unset, set with no value, or not a positive number (git's own rule) — and
# LONGER ones for an inner conflict of a recursive merge. A marker line here
# is a run of AT LEAST the path's effective size of `<` or of `>` at the start
# of a line, followed by a blank or the line's end (git writes the marker,
# then a blank and a label when it has one). The conservative side: a longer
# run than the effective size counts; the cost is a needless marker=yes on a
# line that only resembles one, which sends a merge the slower way.
# Round 30 PR-LOW-009 — the size this scan uses is NEVER ABOVE the size Git
# wrote the markers at; where the two could differ it takes the smaller. Two
# things can make them differ, and each is read on the low side:
#   the VALUE — Git hands the value's BYTES to the C library's base-10 parse:
#     zero or more of the six C whitespace bytes (space, \t, \n, \v, \f, \r),
#     at most one sign (`+` or `-`), one or more ASCII digits `0`-`9`. No
#     other byte is whitespace or a digit to it — no Unicode digit, no
#     no-break space, no control separator (round 31 PR-LOW-010: Python's
#     default `\d` and `\s` are far wider, and read `１０` as ten). Git has
#     used the parse two ways: the older Git stops at the first other byte
#     and ignores the rest (`atoi`: `10abc` is ten); the current Git wants
#     the WHOLE value consumed and the number in `int` range, else seven
#     with a warning (`10abc`, `8x`, `99999999999`). _rd_marker_size reads
#     the value on that ASCII grammar and returns a size no reading of
#     either Git can be below;
#   the SOURCE — Git writes the markers under the attributes of the side the
#     merge runs ON (the tip's), as they stood when it ran; the working tree's
#     attributes AFTER the merge may be the other side's (a `.gitattributes`
#     line only the base adds, or one only the base removes, merges in cleanly
#     and is no delta path). _rd_marker_sizes reads the attribute at the tip
#     as well as in the working tree and takes the smaller.
# Round 32 PR-LOW-011 — and the BYTES it scans are the bytes Git wrote the
# markers into only where Git writes the path unconverted: a path with a
# working-tree encoding, a filter, or a merge driver that is not Git's own
# is not scanned at all — the read is refused (the comment below
# _rd_marker_sizes states the rule).
# Round 33 PR-LOW-012 — and the two reads are the attributes Git wrote under
# only while no tracked attribute file MOVED: a `.gitattributes` the base side
# changed, or one that differs in the working tree from the tip, refuses the
# scan (the comment above RD_ATTR_FILE states the rule and its boundary).
# Under that rule the two reads agree on every tracked attribute file, so the
# "smaller of the two" above is a second net, kept.
RD_MARKER_DEFAULT_SIZE = 7
RD_MARKER_INT_MAX = 2147483647
RD_MARKER_FLOOR = 1
# Git's grammar for the value, WHOLE: explicit ASCII classes, never `\s` / `\d`
_RD_MARKER_VALUE_RE = re.compile(r"[ \t\n\v\f\r]*([+-]?)([0-9]+)")
_RD_MARKER_DIGITS_RE = re.compile(r"[0-9]+")
_RD_MARKER_RES = {}


def _rd_marker_run(digits):
    """The number an ASCII digit run stands for, or None when it is above
    `int` range. Judged by the run's LENGTH before any conversion (ten
    significant digits at most), so no run is too long to read."""
    d = digits.lstrip("0")
    if len(d) > 10:
        return None
    n = int(d) if d else 0
    return n if n <= RD_MARKER_INT_MAX else None


def _rd_marker_size(value):
    """A `conflict-marker-size` attribute value as the scan uses it: a size
    that neither Git's reading of the value can be BELOW (round 30
    PR-LOW-009; on Git's own ASCII grammar from round 31 PR-LOW-010 — the
    comment above states it).
    (a) The value IS the grammar, whole — the six C whitespace bytes, one
        optional sign, ASCII digits, nothing after: both Gits read the same
        number. Positive and in `int` range: that number. Zero or negative:
        the default seven.
    (b) It is not (trailing text, a doubled sign, whitespace after the sign
        or the digits, any other byte before them, no digits at all): the
        current Git reads seven; the older Git reads the leading digit run,
        if the grammar's prefix is what precedes it. The size is the SMALLER
        of seven and the FIRST ASCII digit run in the value, wherever it
        starts, when that run is a positive number — which also covers a
        C library whose locale calls some other byte whitespace (`\\xa03`
        is three) at the cost of a needlessly low size for `x3`.
    A digit run above `int` range, in (a) or (b), with either sign: the
    current Git reads seven, and the older Git's result is the platform's
    (the low bits of the number — it can be below seven), so the size is the
    FLOOR, one: every run of `<` or `>` at a line's start then counts.
    So `10` is 10, `10abc` and `１０` are 7, `3abc` is 3, `-3` is 7,
    `99999999999` is 1 — never a size above the one either Git would have
    written."""
    m = _RD_MARKER_VALUE_RE.fullmatch(value)
    if m:
        n = _rd_marker_run(m.group(2))
        if n is None:
            return RD_MARKER_FLOOR
        return n if (n > 0 and m.group(1) != "-") else RD_MARKER_DEFAULT_SIZE
    r = _RD_MARKER_DIGITS_RE.search(value)
    if r is None:
        return RD_MARKER_DEFAULT_SIZE
    n = _rd_marker_run(r.group(0))
    if n is None:
        return RD_MARKER_FLOOR
    return min(n, RD_MARKER_DEFAULT_SIZE) if n > 0 else RD_MARKER_DEFAULT_SIZE


def _rd_marker_re(size):
    if size not in _RD_MARKER_RES:
        _RD_MARKER_RES[size] = re.compile(b"(?m)^(?:<{%d,}|>{%d,})(?=[ \\r\\n]|\\Z)" % (size, size))
    return _RD_MARKER_RES[size]


def records_path_protected(path, prefix=False):
    """D7 — is `path` a protected location (never a records file)? A spawn
    dependency, or a path with a directory segment named in
    RECORDS_PROTECTED_DIRS, at any depth. With `prefix=True` the path is a
    directory prefix (a trailing `/`): every segment is a directory, and a
    prefix that is an ancestor of a spawn dependency is protected too."""
    segs = path.rstrip("/").split("/")
    if any(d in RECORDS_PROTECTED_DIRS for d in (segs if prefix else segs[:-1])):
        return True
    if prefix:
        return any(dep.startswith(path) for dep in RECORDS_SPAWN_DEPENDENCIES)
    return path in RECORDS_SPAWN_DEPENDENCIES


def docs_instruction_surface(path):
    """D9 — is `path` an instruction surface (never inside the docs floor)?"""
    segs = path.split("/")
    dirs = segs[:-1]
    return (segs[-1] in DOCS_INSTRUCTION_NAMES or any(d in DOCS_INSTRUCTION_DIRS for d in dirs)
            or any(dirs[i] == ".cursor" and dirs[i + 1] in DOCS_INSTRUCTION_CURSOR_DIRS for i in range(len(dirs) - 1)))


def parse_records_paths(value):
    """D7's declaration grammar, shared by --also and every `Records paths:`
    line: a comma-joined list of repo-relative exact file paths and directory
    prefixes (a trailing `/`), each in the hold records' path alphabet.
    Returns ((exact paths, prefixes), None) or (None, reason) — one refused or
    malformed entry refuses the whole value (D19). `records-path-malformed`:
    an empty entry, a wildcard or any other byte outside the alphabet, a
    leading `/`, an empty, `.` or `..` segment. `records-path-protected`: an
    entry that is a protected location or lies under one, or a prefix that
    is one, lies under one, or is above a spawn dependency
    (records_path_protected) — never a prefix for what may later sit under
    it: records_path_class tests every classified path again."""
    exact, prefixes = [], []
    for tok in value.split(","):
        tok = tok.strip()
        is_prefix = tok.endswith("/")
        if not repo_rel_path_ok(tok, prefix=is_prefix):
            return None, ("entry %r is not a repo-relative path or a `/`-terminated directory prefix in [A-Za-z0-9._/-] — no "
                          "wildcard, no leading `/`, no empty, `.` or `..` segment (records-path-malformed)" % tok[:60])
        if records_path_protected(tok, prefix=is_prefix):
            return None, ("entry %r names a protected location — a spawn dependency, or anything under a directory named %s, is "
                          "never a records file (records-path-protected)" % (tok[:60], ", ".join(RECORDS_PROTECTED_DIRS)))
        (prefixes if is_prefix else exact).append(tok)
    return (exact, prefixes), None


def away_departure_records_paths(data):
    """D7 / D19 — every `Records paths:` line of a departure file, read
    together: the UNION of their declarations, ((exact, prefixes), None); one
    malformed or refused entry on any line refuses the whole read — (None,
    reason naming the line). No such line: (([], []), None)."""
    exact, prefixes = [], []
    for n, rest in away_departure_lines(data, AWAY_RECORDS_PATHS_LABEL):
        got, why = parse_records_paths(rest.strip())
        if why:
            return None, "line %d: %s" % (n, why)
        exact += got[0]
        prefixes += got[1]
    return (exact, prefixes), None


def records_path_class(path, alphabet, declared=((), ())):
    """One changed path's class in `alphabet`: True when it is inside the set
    (a records file / a docs-floor file), else False. The protected-location
    and instruction-surface exclusions are applied HERE, to every path."""
    if not repo_rel_path_ok(path):
        return False
    name = path.rpartition("/")[2]
    if alphabet == "docs":
        return path.endswith(".md") and not docs_instruction_surface(path)
    if records_path_protected(path):
        return False
    return (name == "CHANGELOG.md" or path == "AGENTS.md" or path.startswith(".cursor/plans/")
            or path in declared[0] or any(path.startswith(p) for p in declared[1]))


def _rd_git_z(worktree, *args, stdin=None, fields=False, silent=False):
    """git under the checkout, NUL-separated names out: a list of str, or
    envfail (exit 3) — an input that cannot be read is never an empty one.
    GIT_OPTIONAL_LOCKS=0: a working-tree diff would otherwise refresh and
    rewrite the checkout's index when it can take the lock; this reader
    writes nothing, the index included. `stdin` feeds the command bytes;
    `fields=True` keeps EVERY NUL-terminated field, an empty one included
    (a record reader counts fields; a name reader drops the empties).
    `silent=True` (round 13 PR-MED-021) is for a read whose reply is evidence
    only when Git said NOTHING on stderr: a zero exit with a diagnostic is
    then an unreadable input too — exit 3, the diagnostic carried — because
    Git exits 0 after it could not read a source it meant to (an attributes
    file it has no permission for) and answers as if the source were empty.
    Asked of the `check-attr` read ALONE. The name diffs and the untracked
    listing keep the exit status as their test, by decision: Git prints
    benign warnings on those under ordinary configurations (a line-ending
    conversion notice on a working-tree diff), and refusing on any of them
    would make this reader exit 3 on every such host. What such a warning can
    hide was read at Step HA3 (the selftest's candidate-4 rows): on the
    untracked listing Git exits 0, warns, and leaves out an untracked file
    under a directory Git could not open; on a name diff a tracked path Git
    cannot reach is LISTED (as removed), nothing on stderr. So a warning
    stands for a missing name only for a path Git itself cannot read — and
    `git add` cannot stage that path either, so the commit made from the same
    tree while the state holds does not contain it."""
    try:
        r = subprocess.run([_git_bin(), "-C", worktree] + list(args), capture_output=True, timeout=120,
                           input=stdin, env=_git_env(GIT_OPTIONAL_LOCKS="0"))
    except Exception as e:
        envfail("records-delta: git %s failed under %s: %s" % (args[0], worktree, e))
    if r.returncode != 0:
        envfail("records-delta: git %s failed under %s: %s"
                % (" ".join(args[:2]), worktree, r.stderr.decode("utf-8", "replace").strip()[:200]))
    if silent and r.stderr.strip():
        envfail("records-delta: git %s under %s exited 0 with a diagnostic — its reply is not a complete read: %s"
                % (args[0], worktree, ci_sanitise(r.stderr.decode("utf-8", "replace").strip(), 300)))
    if fields:
        return [os.fsdecode(p) for p in r.stdout.split(b"\0")[:-1]]
    return [os.fsdecode(p) for p in r.stdout.split(b"\0") if p]


def _rd_marker_sizes(worktree, paths, tip):
    """{path: the conflict-marker size the scan uses} for `paths`: the SMALLER
    of two `git check-attr -z --stdin conflict-marker-size` reads over the
    checkout (the paths on stdin, so their number is unbounded) — the
    attributes of the working tree as it stands, and (round 30 PR-LOW-009)
    the attributes at the commit `tip`, read with `--source=<tip>`. Git wrote
    the markers under the tip's attributes, before the merge's result reached
    the working tree; the working tree may by now hold the OTHER side's
    `.gitattributes`, a larger size or none, and a size taken from it alone
    misses markers Git wrote smaller. `--source` needs Git 2.40 or newer: an
    older Git fails the call, and that is an unreadable input like any other
    (exit 3 — the merge takes the full cycle). A reply that is not whole
    path / attribute / value records is an unreadable input (exit 3); a path
    neither reply names reads the default. So is a reply that came with
    ANYTHING on stderr (round 13 PR-MED-021, `silent=True`): Git warns, exits
    0 and answers `unspecified` when it could not read an attributes source,
    and a default taken from an unread source is not an established size —
    it would miss a marker at a configured size below seven.
    The same two reads carry round 32's rule (PR-LOW-011; the comment below
    this function states it): they also ask for `working-tree-encoding`,
    `filter` and `merge`, and a path for which EITHER read names a
    conversion or a merge driver that is not Git's own is not scanned — the
    read is refused, exit 3, the path and the attribute named
    (rd_scan_attr_refusal); and one configuration read refuses a
    `merge.default` that is not built in (_rd_scan_config_refusal). The
    refusals run before any file is read.
    What the two reads cannot say is whether they are the attributes Git
    wrote the bytes under — round 33 PR-LOW-012; the caller asks that next,
    of the attribute FILES (_rd_attr_files_refusal), before any file is
    read."""
    if not paths:
        return {}
    _rd_scan_config_refusal(worktree)
    sizes = {}
    for source in ((), ("--source=%s" % tip,)):
        out = _rd_git_z(worktree, "check-attr", *source, "-z", "--stdin", *RD_SCAN_ATTRS, fields=True, silent=True,
                        stdin=b"".join(os.fsencode(p) + b"\0" for p in paths))
        if len(out) % 3:
            envfail("records-delta: git check-attr under %s returned %d fields — not whole path/attribute/value records" % (worktree, len(out)))
        for i in range(0, len(out), 3):
            path, attr, value = out[i], out[i + 1], out[i + 2]
            if attr == RD_SCAN_ATTRS[0]:
                n = _rd_marker_size(value)
                sizes[path] = min(n, sizes.get(path, n))
                continue
            why = rd_scan_attr_refusal(attr, value)
            if why:
                envfail("records-delta: the delta file %s carries %s=%s %s — %s; its working-tree bytes are not scanned for conflict markers and the delta is not classified (marker-scan-unfit)"
                        % (path if repo_rel_path_ok(path) else "<unprintable>", attr, ci_sanitise(value, 60),
                           "at the tip" if source else "in the working tree", why))
    return sizes


# Round 32 PR-LOW-011 — the BYTES the scan reads. Git writes its conflict
# markers into a path's canonical content and then puts that content into the
# working tree through the path's checkout conversions; the scan reads the far
# side of them. So the scan trusts a path's working-tree bytes only when Git
# writes the path AS IT MERGED IT. Three things can stand between, and each is
# a REFUSAL of the read (exit 3 — the merge takes the full cycle), never a
# scan of converted bytes and never a decoding of them:
#   `working-tree-encoding` — UTF-16 puts a NUL between every two `<`;
#   `filter` — a smudge command or filter process may rewrite the lines;
#   a merge driver that is not Git's own — `merge=<name>` other than the
#     built-in text / binary / union, or a `merge.default` that is not one of
#     them: Git did not write the markers at all.
# The three attributes ride the two `check-attr` reads that fetch the marker
# size (the working tree's attributes and the tip's): EITHER read naming one
# refuses. (Whether those two reads are the attributes Git wrote under is
# round 33's question — the comment above RD_ATTR_FILE.) What is NOT refused,
# because it does not move a marker's bytes:
# end-of-line conversion (the pattern admits a CR after the marker), `ident`,
# `merge.conflictStyle`, the three built-in merge drivers.
# `check-attr` prints the STATES of an attribute as the words `unspecified`,
# `unset` and `set` — and prints a literal value of the same spelling the same
# way. A filter or merge driver CONFIGURED under one of those names
# (`filter.unset.smudge`) therefore cannot be told from the state, and is
# refused from the configuration instead, for every scanned path.
RD_SCAN_ATTRS = ("conflict-marker-size", "working-tree-encoding", "filter", "merge")
RD_MERGE_BUILTIN = ("text", "binary", "union")
RD_ATTR_STATE_WORDS = ("unspecified", "unset", "set")
RD_SCAN_CONFIG_RE = r"^(merge\.default|(filter|merge)\.(unspecified|unset|set)\..*)$"


def rd_scan_attr_refusal(attr, value):
    """Why a scanned path's attribute makes its working-tree bytes unfit for
    the marker scan, or None (round 32 PR-LOW-011). `working-tree-encoding`
    and `filter`: anything but `unspecified` or `unset`. `merge`: anything
    but the states (`unspecified`; `set` is the text driver, `unset` the
    binary one) and the three built-in driver names."""
    if attr in ("working-tree-encoding", "filter"):
        if value in ("unspecified", "unset"):
            return None
        return ("Git re-encodes the file between its merge and the working tree" if attr == "working-tree-encoding"
                else "a filter driver may rewrite the file between Git's merge and the working tree")
    if attr == "merge":
        if value in RD_ATTR_STATE_WORDS or value in RD_MERGE_BUILTIN:
            return None
        return "a merge driver that is not Git's own writes its conflicts its own way"
    return None


def _rd_scan_config_refusal(worktree):
    """The configuration half of round 32's rule, one read: a `merge.default`
    that is not a built-in driver (it is the driver of every path whose
    `merge` attribute is unspecified), or a filter or merge driver configured
    under a name `check-attr` prints as an attribute STATE, refuses the scan
    for every path — exit 3. `git config --get-regexp` exits 1 when nothing
    matches; any other failure is an unreadable input."""
    rc, out = _rc_git(worktree, "config", "-z", "--get-regexp", RD_SCAN_CONFIG_RE)
    if rc == 1 and not out:
        return
    if rc != 0:
        envfail("records-delta: git config --get-regexp failed under %s (exit %s) — the merge and filter drivers in force could not be read" % (worktree, rc))
    for rec in out.split("\0"):
        key, _sep, val = rec.partition("\n")
        if not key:
            continue
        if key == "merge.default" and val in RD_MERGE_BUILTIN:
            continue
        envfail("records-delta: the configuration holds %s=%s — %s; working-tree bytes are not scanned for conflict markers under it and the delta is not classified (marker-scan-unfit)"
                % (ci_sanitise(key, 80), ci_sanitise(val, 60),
                   "a default merge driver that is not Git's own writes its conflicts its own way" if key == "merge.default"
                   else "a driver named like an attribute state cannot be told from that state in `git check-attr`'s reply"))


# Round 33 PR-LOW-012 — WHICH attributes the two reads report. Round 32's rule
# asks what the tip's attributes and the working tree's name; it holds only if
# those are the attributes Git wrote the scanned bytes under. They need not
# be. Git checks a conflicted path out under the attribute files as the merge
# leaves them — file by file the tip's, the base side's, or a textual merge of
# the two — and a path taken WHOLE from one side is no delta path (the delta is
# what differs from both commits): an attribute file the base side added and
# the resolution removed again leaves no trace in the delta or in either read,
# while the file it converted is still in the working tree, converted. The
# attribute files of a merge's RESULT can even name a conversion that neither
# side's own files name: one side sets it in the root file, under a nested
# file that unsets it; the other side removes the nested file. Each file is
# changed by one side only, so neither is a delta path, and a third read, at
# the base ref, would not close it (the selftest holds it on an actual merge.
# Done in ONE file — set above a line that unsets it, the line removed by the
# other side — the file is a both-sides file and the delta is `mixed`).
# The rule is on NAMES ALREADY READ, no further Git call: when there is a
# path to scan, the read is REFUSED (exit 3) if any path whose last segment is
# `.gitattributes`, in any letter case, either
#   changed between the merge base and --base-ref, or
#   differs in the working tree from --tip (tracked, or untracked).
# When neither holds, the base side brought no change to any tracked attribute
# file, so the merge's result holds the tip's, and the working tree holds the
# tip's too: ONE set of tracked attribute files from the merge's start to this
# read, and it is the set the two reads report. Nothing in that argument
# depends on the order in which Git reads attributes during a merge. The test
# runs after the two attribute reads, so a path one of them names keeps round
# 32's message.
# THE BOUNDARY — what no read made after the merge can establish, and this
# reader does not claim (the plan's Retained Follow-Up Items carry it):
#   a state that existed only between the merge and this read (Git checking
#     the file out again under an attribute file changed and then put back);
#   a writer that is not Git (a tool that saves the file re-encoded);
#   attribute and driver sources that are in no commit, if they differed when
#     the merge ran — `$GIT_DIR/info/attributes`, the user's and the system's
#     attribute files, an ignored `.gitattributes` in the working tree (Git
#     reads it; the untracked listing leaves it out), `attr.tree`, the
#     configuration, and anything given to the merge command alone (`-c`,
#     `--attr-source`, `GIT_ATTR_SOURCE`);
#   an attribute file staged in the index and absent from both the working
#     tree and the tip;
#   a name a file system resolves to `.gitattributes` beyond letter case (an
#     NTFS short name, a trailing dot or space, a stream suffix, an HFS+
#     ignorable character).
RD_ATTR_FILE = ".gitattributes"


def rd_attr_file_name(path):
    """Is `path`'s last segment `.gitattributes`, in any letter case? Both
    foldings are asked (`casefold` and `upper`), so a letter either one maps
    onto the name counts — a case-insensitive file system opens such a file
    under the name Git asks for."""
    name = path.rpartition("/")[2]
    return name.casefold() == RD_ATTR_FILE or name.upper() == RD_ATTR_FILE.upper()


def _rd_attr_files_refusal(base_side, off_tip):
    """Round 33 PR-LOW-012 (the comment above states the rule and its
    boundary): refuse the marker scan — exit 3, nothing printed — when a
    tracked attribute file is not the tip's from the merge's start to this
    read. `base_side` is the names changed between the merge base and
    --base-ref, `off_tip` the names whose working-tree content differs from
    --tip (untracked files included); both are the caller's, already read.
    The first such path, in sorted order, is named, with which of the two it
    is. Called only when at least one delta path is to be scanned."""
    for path in sorted(base_side | off_tip):
        if not rd_attr_file_name(path):
            continue
        envfail("records-delta: the attribute file %s %s — the attributes Git wrote the delta files under are not established by a read made now; working-tree bytes are not scanned for conflict markers and the delta is not classified (marker-scan-unfit)"
                % (path if repo_rel_path_ok(path) else "<unprintable>",
                   "changed between the merge base and --base-ref" if path in base_side else "differs in the working tree from --tip"))


def _rd_file_marked(worktree, path, size):
    """Does the working-tree file `path` hold a conflict-marker line at
    `size` (_rd_marker_re)? The caller has already refused every path whose
    working-tree bytes may not be the bytes Git merged (_rd_marker_sizes,
    round 32 PR-LOW-011: an encoding, a filter, a merge driver not Git's
    own), and the whole scan when a tracked attribute file moved across the
    merge (_rd_attr_files_refusal, round 33 PR-LOW-012) — this function reads
    RAW bytes and is only ever asked of a path Git writes unconverted but for
    its line endings, as far as the tracked attribute files and the
    configuration read now can establish (the boundary is stated above
    RD_ATTR_FILE).
    A path with no file bytes of its own cannot hold one: one
    that is absent (removed in the working tree), a directory (a gitlink),
    or a symbolic link (its content is its target's name; it is never read
    through). EVERY other failure to read is an unreadable input — exit 3,
    the path named — never a `no` (round 9 PR-MED-016), and that holds for
    the metadata read as for the bytes (round 10 PR-MED-018): ONE `lstat`
    decides, and only its not-found answers (the path, or a directory on the
    way to it, is not there) read as absent. `os.path.lexists` / `islink` /
    `isdir` are not used: each turns a failed stat — a permission or I/O
    error — into False, which here would be a `no`.
    Only REGULAR-file bytes are read (round 11 PR-MED-019). A path the
    `lstat` names a FIFO, a device or a socket is an unreadable input before
    any open — nothing here opens a file that can block or be consumed. And
    the bytes come through _away_read_bytes with follow=False, the helper's
    one guarded reader: a no-follow, NON-BLOCKING open and an `fstat` on the
    descriptor that must say regular file before a byte is read. What that
    does for a path that changed kind between this function's `lstat` and the
    open depends on the leg _open_at takes (its docstring states both). A
    FIFO, a device or a socket put there is refused on either leg, never
    waited on: the descriptor's `fstat` does not say regular file. A LINK
    put there is refused at the open where the host has a no-follow open
    (the fd-relative leg). On the fallback leg (Windows) the leg's own
    `lstat` refuses a link that is already there; one put in place after
    that `lstat` is followed by the open, and the identity bind then refuses
    a link to a DIFFERENT file, while a link back to the same file that
    `lstat` named is read — the leg's documented residual, pinned by the
    selftest's fallback-only row (round 38)."""
    full = os.path.join(worktree, path)
    shown = path if repo_rel_path_ok(path) else "<unprintable>"
    try:
        st = os.lstat(full)
    except (FileNotFoundError, NotADirectoryError):
        return False
    except (OSError, ValueError) as e:
        envfail("records-delta: cannot read the delta file %s for conflict markers: %s" % (shown, e))
    if _is_redirect(st) or stat.S_ISDIR(st.st_mode):
        return False   # a link (or a Windows reparse point) is never read through; a directory holds no bytes
    if not stat.S_ISREG(st.st_mode):
        envfail("records-delta: cannot read the delta file %s for conflict markers: not a regular file (%s)"
                % (shown, _away_file_kind(st.st_mode)))
    try:
        data = _away_read_bytes(full, follow=False)
    except (OSError, ValueError) as e:
        envfail("records-delta: cannot read the delta file %s for conflict markers: %s" % (shown, e))
    return _rd_marker_re(size).search(data) is not None


def _rd_resolve(worktree, ref, what):
    if ref.startswith("-"):
        refuse("records-delta: %s %r is not a commit-ish" % (what, ref[:60]))
    rc, full = _rc_git(worktree, "rev-parse", "--verify", "--quiet", "%s^{commit}" % ref)
    if rc != 0 or not _FULL_SHA_RE.match(full):
        envfail("records-delta: %s %s does not resolve to a commit under %s" % (what, ref[:80], worktree))
    return full


def _rd_worktree_names(worktree, commit):
    """The paths whose working-tree content differs from `commit` — tracked
    changes (staged or not, unmerged included) plus untracked, non-ignored
    files (a new file differs from every commit). GIT_NAME_DIFF's submodule
    policy holds here as in every name diff of this reader: a submodule
    checked out at another commit than `commit` records is a changed path,
    whatever the submodule-ignore settings; its own uncommitted or untracked
    content is not one."""
    return set(_rd_git_z(worktree, *GIT_NAME_DIFF, commit)) \
        | set(_rd_git_z(worktree, "ls-files", "--others", "--exclude-standard", "-z"))


def cmd_records_delta(flags):
    """v47.0 (T1.4 / D7, D9) — `records-delta`: READ-ONLY; prints one summary
    line, then one line per path, and writes nothing.
      MERGE mode   --worktree </abs checkout> --base-ref <commit-ish> --tip <commit-ish>
                   [--also <decl>[,<decl>…]] [--departure </abs file>]
        a prepared (or not yet prepared) merge of --base-ref into --tip, in
        the `records` alphabet. The delta is the UNION of (a) the both-sides
        files — changed between the merge base and --tip AND between the merge
        base and --base-ref — and (b) every path whose working-tree content
        differs from BOTH --tip and --base-ref (a resolution, a hand edit, a
        new file). `marker=yes` when the index holds an unmerged path or a
        delta file's working-tree bytes hold a conflict-marker line — a run
        of at least the path's effective `conflict-marker-size` (seven by
        default) of `<` or of `>` at a line's start, then a blank or the
        line's end. That size is the smaller of the attribute at --tip (the
        side Git wrote the markers under) and in the working tree, a
        malformed or out-of-range value read on its low side (round 30
        PR-LOW-009; _rd_marker_sizes). A delta path that is absent, a directory or a symbolic
        link has no bytes to scan; a delta path whose metadata or bytes
        cannot be read, or that is not a regular file (a FIFO, a device, a
        socket — never opened), is an unreadable input.
      Both modes list a changed submodule POINTER as a changed path, whatever
      the repository's or the user's submodule-ignore settings (GIT_NAME_DIFF:
      `--ignore-submodules=dirty`); a submodule's own uncommitted content is
      not a changed path.
      PATH mode    --worktree </abs checkout> --range <from>..<to> --alphabet records|docs
                   [--also …] [--departure …]   (records alphabet only)
        the paths that differ between two commits; <to> may be the word
        WORKTREE — the working tree against <from>, untracked files included.
        marker= is not read (`marker=n/a`).
    Output: `records-delta: mode=<merge|path> alphabet=<a> delta=<empty|records|docs|mixed>
    marker=<yes|no|n/a> files=<n> outside=<n> …ids` — delta=empty when no path
    is in the delta, the alphabet's own word when every path is inside its
    set, mixed otherwise — then, per path in sorted order, `records-delta:
    file=<path> class=<records|docs|other>[ both_sides=yes][ marker=yes]` (a
    path outside the printable alphabet is `file=<unprintable>`, class
    other). Exit 0 whenever the input was read, whatever the words; 2 on a
    usage refusal or a refused declaration (records-path-malformed /
    records-path-protected); 3 when an input cannot be read (the checkout, a
    ref, git, the departure file, a delta file's metadata or bytes in merge
    mode, a marker-size read Git answered with a diagnostic or — an older
    Git, without `check-attr --source` — could not make, a delta file whose
    attributes or whose repository's `merge.default` mean Git may not have
    written it as it merged it (round 32: marker-scan-unfit), a scan across a
    tracked attribute file that moved — any `.gitattributes` changed between
    the merge base and --base-ref, or differing in the working tree from
    --tip (round 33: marker-scan-unfit too) — and — Step HA3 —
    a merge-mode pair with more than one merge base) —
    nothing is printed then: an unread input never becomes a word.
    --worktree is the checkout's TOP-LEVEL directory (Step HA3): under a
    subdirectory git prints the name diffs from the top and the untracked
    listing from the subdirectory, and the marker scan would look for each
    name under the wrong directory and read a missing file as no marker — so
    a --worktree that is not the top level is refused (exit 2)."""
    worktree = flags.get("--worktree")
    if worktree is None:
        refuse("records-delta REQUIRES --worktree </abs checkout>",
               "records-delta --worktree </abs> --base-ref <commit-ish> --tip <commit-ish> | --range <from>..<to> --alphabet records|docs [--also <path|prefix/>[,…]] [--departure </abs file>]")
    if not os.path.isabs(worktree):
        refuse("--worktree must be an absolute path")
    if not os.path.isdir(worktree):
        envfail("--worktree %s is not a directory" % worktree)
    rc, top = _rc_git(worktree, "rev-parse", "--show-toplevel")
    if rc != 0 or not top:
        envfail("records-delta: --worktree %s is not a git checkout (git rev-parse --show-toplevel failed)" % worktree)
    try:
        at_top = os.path.samefile(top, worktree)
    except (OSError, ValueError):
        at_top = False
    if not at_top:
        refuse("records-delta: --worktree %s is not the checkout's top-level directory (%s) — the reader's name reads and its marker scan are the top level's" % (worktree, top[:200]))
    rng = flags.get("--range")
    if rng is not None:
        mode = "path"
        if "--base-ref" in flags or "--tip" in flags:
            refuse("records-delta: --range (path mode) and --base-ref / --tip (merge mode) are two modes — pass one")
        alphabet = flags.get("--alphabet")
        if alphabet not in RECORDS_DELTA_ALPHABETS:
            refuse("records-delta path mode REQUIRES --alphabet %s" % "|".join(RECORDS_DELTA_ALPHABETS))
        frm, sep, to = rng.partition("..")
        if not sep or not frm or not to or to.startswith(".") or ".." in to:
            refuse("--range must be <from>..<to> — two commit-ish, or <from>..%s for the working tree" % RECORDS_WORKTREE_WORD)
    else:
        mode, alphabet = "merge", "records"
        missing = [f for f in ("--base-ref", "--tip") if f not in flags]
        if missing:
            refuse("records-delta merge mode REQUIRES %s (or --range <from>..<to> --alphabet … for path mode)" % " ".join(missing))
        if "--alphabet" in flags:
            refuse("--alphabet is path mode's — merge mode reads the records alphabet only")
    declared = ([], [])
    if alphabet == "docs" and ("--also" in flags or "--departure" in flags):
        refuse("--also / --departure declare RECORDS paths — they are not accepted with --alphabet docs")
    if "--also" in flags:
        got, why = parse_records_paths(flags["--also"])
        if why:
            refuse("records-delta: --also %s" % why)
        declared = (declared[0] + got[0], declared[1] + got[1])
    if "--departure" in flags:
        if not os.path.isabs(flags["--departure"]):
            refuse("--departure must be an absolute path")
        try:
            dep_bytes = _away_read_bytes(flags["--departure"])
        except OSError as e:
            envfail("records-delta: cannot read --departure %s: %s" % (flags["--departure"], e))
        got, why = away_departure_records_paths(dep_bytes)
        if why:
            refuse("records-delta: the departure file's `Records paths:` %s" % why)
        declared = (declared[0] + got[0], declared[1] + got[1])
    both, marked, ids = set(), set(), ""
    if mode == "merge":
        tip = _rd_resolve(worktree, flags["--tip"], "--tip")
        base = _rd_resolve(worktree, flags["--base-ref"], "--base-ref")
        mb, why = git_one_merge_base(worktree, tip, base)
        if mb is None:
            envfail("records-delta: --tip %s and --base-ref %s under %s: %s" % (tip, base, worktree, why))
        tip_side = set(_rd_git_z(worktree, *GIT_NAME_DIFF, mb, tip))
        base_side = set(_rd_git_z(worktree, *GIT_NAME_DIFF, mb, base))
        off_tip = _rd_worktree_names(worktree, tip)
        both = tip_side & base_side
        names = both | (off_tip & _rd_worktree_names(worktree, base))
        marked = set(_rd_git_z(worktree, *GIT_NAME_DIFF, "--diff-filter=U"))
        unread = sorted(names - marked)
        sizes = _rd_marker_sizes(worktree, unread, tip)
        if unread:
            _rd_attr_files_refusal(base_side, off_tip)
        for p in unread:
            if _rd_file_marked(worktree, p, sizes.get(p, RD_MARKER_DEFAULT_SIZE)):
                marked.add(p)
        names |= marked
        ids = " tip=%s base=%s merge_base=%s" % (tip, base, mb)
    else:
        f_sha = _rd_resolve(worktree, frm, "--range <from>")
        if to == RECORDS_WORKTREE_WORD:
            names = _rd_worktree_names(worktree, f_sha)
            ids = " from=%s to=%s" % (f_sha, RECORDS_WORKTREE_WORD)
        else:
            t_sha = _rd_resolve(worktree, to, "--range <to>")
            names = set(_rd_git_z(worktree, *GIT_NAME_DIFF, f_sha, t_sha))
            ids = " from=%s to=%s" % (f_sha, t_sha)
    rows = [(p, records_path_class(p, alphabet, declared)) for p in sorted(names)]
    outside = sum(1 for _p, inside in rows if not inside)
    delta = "empty" if not rows else (alphabet if not outside else "mixed")
    out = ["records-delta: mode=%s alphabet=%s delta=%s marker=%s files=%d outside=%d%s"
           % (mode, alphabet, delta, ("yes" if marked else "no") if mode == "merge" else "n/a", len(rows), outside, ids)]
    for p, inside in rows:
        out.append("records-delta: file=%s class=%s%s%s"
                   % (p if repo_rel_path_ok(p) else "<unprintable>", alphabet if inside else "other",
                      " both_sides=yes" if p in both else "", " marker=yes" if p in marked else ""))
    sys.stdout.write("".join(l + "\n" for l in out))


# --- v45.0 (T1.5 — D9 / D27 / D15): the process-group / Job primitive and the
# bounded runner. The group primitive is the RUNTIME's (T2.2 imports it from
# the blob-verified snapshot for the wrapper's spawn and the launcher's stop
# ladder): on POSIX the child leads a new session (its pid is the pgid) and
# the census is `ps -eo pgid=,pid=`; on Windows a Job Object with
# KILL_ON_JOB_CLOSE is the group, QueryInformationJobObject's process-id list
# the census, TerminateJobObject the stop — ctypes `kernel32` only. The child
# is assigned AFTER Popen returns (the assignment gap — Accepted Assumptions).
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
_JobObjectExtendedLimitInformation = 9
_JobObjectBasicProcessIdList = 3


def _job_kernel32():
    import ctypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    return ctypes, k


def _job_create():
    """A Job Object that kills every member when its last handle closes."""
    import ctypes
    from ctypes import wintypes
    ctypes, k = _job_kernel32()
    job = k.CreateJobObjectW(None, None)
    if not job:
        raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")

    class _IoCounters(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                                                      "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class _BasicLimits(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class _ExtendedLimits(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", _BasicLimits), ("IoInfo", _IoCounters),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    info = _ExtendedLimits()
    info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not k.SetInformationJobObject(job, _JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info)):
        err = ctypes.get_last_error()
        k.CloseHandle(job)
        raise OSError(err, "SetInformationJobObject failed")
    return job


class _GroupSetupError(OSError):
    """round 23 PR-MED-001: a failure of the runner's OWN group machinery (the
    Job's creation or assignment) — distinguished by PROVENANCE from what
    `Popen` raises for the command itself, so bounded_run maps it to 125 and
    every command-invocation failure to 126 / 127."""


def group_launch(argv, cwd=None, stdout=None, stderr=None, stdin=subprocess.DEVNULL, env=None, pass_fds=()):
    """Start `argv` as the leader of a fresh group: a new session on POSIX, a
    Job Object on Windows (assigned after Popen returns). Returns the group
    handle `{"proc": Popen, "job": <handle or None>}`; raises what Popen
    raises for the command (FileNotFoundError / any other OSError) with
    nothing started, and _GroupSetupError for the runner's own Job failures.
    `pass_fds` (OPTIONAL — round 33 PR-MED-001; POSIX only, ignored on
    Windows): descriptors the leader inherits beside 0 / 1 / 2 — the spawn
    wrapper hands its spawn-lock descriptor over so the role keeps the lock's
    open file description alive as v44.0's inherited fd 9 did; every other
    caller passes nothing and every other descriptor stays closed in the child."""
    if not HOST["is_windows"]:
        p = subprocess.Popen(argv, cwd=cwd, stdout=stdout, stderr=stderr, stdin=stdin, env=env,
                             start_new_session=True, pass_fds=tuple(pass_fds))
        return {"proc": p, "job": None}
    try:
        job = _job_create()
    except OSError as e:
        raise _GroupSetupError(e.errno, str(e)) from e
    ctypes, k = _job_kernel32()
    try:
        p = subprocess.Popen(argv, cwd=cwd, stdout=stdout, stderr=stderr, stdin=stdin, env=env)
    except BaseException:
        k.CloseHandle(job)
        raise
    if not k.AssignProcessToJobObject(job, int(p._handle)):
        err = ctypes.get_last_error()
        # round 24 PR-MED-001: the child is already running outside the Job —
        # its ownership is kept through a contained kill and ONE bounded reap,
        # the Job is released on every path, and the disposition is NAMED in
        # the setup error (an unconfirmed survivor is said so, never silent)
        try:
            p.kill()
            outcome = None
        except OSError as e:
            outcome = "kill failed — %s: %s; the child %d may survive" % (type(e).__name__, str(e)[:120], p.pid)
        if outcome is None:
            try:
                p.wait(timeout=_RB_KILL_REAP_S)
                outcome = "the child %d was killed and reaped" % p.pid
            except subprocess.TimeoutExpired:
                outcome = "the child %d did not exit within the reap bound; it may survive" % p.pid
            except OSError as e:
                outcome = "reap failed — %s: %s; the child %d may survive" % (type(e).__name__, str(e)[:120], p.pid)
        k.CloseHandle(job)
        raise _GroupSetupError(err, "AssignProcessToJobObject failed; %s" % outcome)
    return {"proc": p, "job": job}


def group_members(h):
    """The pids still in the group — the exit census. POSIX: `ps -eo pgid=,pid=`
    filtered on the leader's pgid (the leader's pid); Windows: the Job's
    process-id list. None when the census itself failed (no `ps`, a failed
    query) — a caller never reports `children=0` on None."""
    if not HOST["is_windows"]:
        try:
            r = subprocess.run(["ps", "-eo", "pgid=,pid="], capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError, ValueError):
            # round 19 PR-MED-001: the census's OWN failures only — an interrupt
            # raised inside this call is never read as an unknown census
            return None
        if r.returncode != 0:
            return None
        # round 21 PR-MED-002: the snapshot is validated BEFORE the pgid filter —
        # every line two integers, and the runner's own pid present (a genuine
        # all-process snapshot always lists the process that took it); an empty
        # or malformed snapshot is UNKNOWN (None), never an empty group
        pids = []
        seen_self = False
        me = os.getpid()
        for line in r.stdout.splitlines():
            parts = line.split()
            if not parts:
                continue
            if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
                return None
            if int(parts[1]) == me:
                seen_self = True
            if int(parts[0]) == h["proc"].pid:
                pids.append(int(parts[1]))
        if not seen_self:
            return None
        return pids
    import ctypes
    from ctypes import wintypes
    ctypes, k = _job_kernel32()
    n = 64
    while True:
        class _IdList(ctypes.Structure):
            _fields_ = [("NumberOfAssignedProcesses", wintypes.DWORD), ("NumberOfProcessIdsInList", wintypes.DWORD),
                        ("ProcessIdList", ctypes.c_size_t * n)]
        buf = _IdList()
        okq = k.QueryInformationJobObject(h["job"], _JobObjectBasicProcessIdList, ctypes.byref(buf), ctypes.sizeof(buf), None)
        if okq:
            return [int(buf.ProcessIdList[i]) for i in range(buf.NumberOfProcessIdsInList)]
        err = ctypes.get_last_error()
        if err == 234 and n < 65536:  # ERROR_MORE_DATA — grow the list
            n *= 4
            continue
        return None


def group_alive(h):
    """True while the leader runs or any member survives; a FAILED census
    (None) reads as alive — unknown is never "gone" (round 18 PR-MED-001;
    the wrapper's `children=0 only when the census succeeded` rule, T2.2)."""
    if h["proc"].poll() is None:
        return True
    m = group_members(h)
    return True if m is None else bool(m)


def group_stop(h, kill=False):
    """TERM (kill=False) or KILL (kill=True) the whole group. On Windows both
    are TerminateJobObject (no graceful signal reaches a non-console child);
    a group already gone is not an error."""
    if not HOST["is_windows"]:
        import signal
        try:
            os.killpg(h["proc"].pid, signal.SIGKILL if kill else signal.SIGTERM)
        except ProcessLookupError:
            pass
        return
    ctypes, k = _job_kernel32()
    if not k.TerminateJobObject(h["job"], 137 if kill else 124):
        # round 21 PR-MED-001: a failed termination is an error the cleanup
        # owner names — never a silent "stopped"
        raise OSError("TerminateJobObject failed (winerror %d)" % ctypes.get_last_error())


def group_close(h):
    """Release the Job handle (KILL_ON_JOB_CLOSE sweeps any survivor); a no-op
    on POSIX."""
    if h.get("job"):
        ctypes, k = _job_kernel32()
        k.CloseHandle(h["job"])
        h["job"] = None


_RB_TIMEOUT_MAX = 86400.0
# round 22 PR-MED-001: the post-KILL reap's OWN bound — independent of the
# operator's TERM-to-KILL grace (`--kill-after`, zero accepted: KILL right
# after the TERM); a successfully KILLed leader needs a moment to exit, so
# "still alive after the KILL" is named only once this bound has elapsed
_RB_KILL_REAP_S = 5.0


def _rb_seconds(tok, flag, zero_ok):
    """A non-negative decimal seconds value for --timeout / --kill-after."""
    try:
        v = float(tok)
    except ValueError:
        refuse("%s %r is not a decimal number of seconds" % (flag, tok[:40]))
    if v != v or v < 0 or v > _RB_TIMEOUT_MAX or (v == 0 and not zero_ok):
        refuse("%s must be %s and at most %d seconds (got %r)" % (flag, "non-negative" if zero_ok else "positive", int(_RB_TIMEOUT_MAX), tok[:40]))
    return v


# round 18 → 20 PR-MED-001: cmd_run_bounded's SIGINT / SIGTERM handler NEVER
# raises — it only LATCHES the signal number. bounded_run's principal wait is
# POLLED (short `p.wait` slices) and reads the latch between slices, so a stop
# request is honoured within ~200 ms with the group stopped while its leader is
# alive, a request that arrived during the launch is consumed before the first
# slice, and no exception can escape at any handoff — launch return, wait end,
# the cleanup owner (stop, grace, KILL, reap, census, sweep); a signal latched
# DURING the cleanup is reported after it as the runner's failure.
_RUNNER_SIGNALS = {"latched": []}


def _runner_signal_handler(signum, frame):
    _RUNNER_SIGNALS["latched"].append(signum)


def _signal_name(signum):
    import signal
    try:
        return signal.Signals(signum).name
    except (ValueError, AttributeError):
        return "signal %s" % signum


def bounded_run(argv, timeout, kill_after=2.0, cwd=None, env=None, interrupts=None):
    """v45.0 (D9 / D27): run `argv` in its own group under `timeout` seconds,
    TERM at the deadline, KILL after `kill_after`; on EVERY exit path a
    member that outlives the leader is swept with KILL (round 16 LOW-001:
    the group dies with the runner on both hosts — the Job's
    KILL_ON_JOB_CLOSE semantics, mirrored on POSIX). A census that FAILS
    (None) is retried once and then reported as the runner's own failure —
    never read as "no survivors", and never an unconditional kill (a reaped
    leader's pgid may already be reused by an unrelated group). `interrupts`
    is the caller's stop-request latch (a list the caller's signal handler
    appends to — cmd_run_bounded's; None when the caller has none): the
    principal wait is polled in short slices and a latched request ends it as
    an interrupt, so the group is stopped while its leader is alive and 125
    is reported (rounds 18 → 20 PR-MED-001) — nothing raises out of the wait
    or the cleanup. stdout and stderr are captured to temporary files
    the CALLER streams and closes (round 16 LOW-003: never read whole into
    memory). Returns (exit_code, elapsed_s, timed_out, killed, stdout_file,
    stderr_file, runner_error) — the files positioned at 0, or None each when
    the launch itself failed; `exit_code` already mapped as coreutils
    `timeout` maps it: the child's code; 124 timed out; 137 killed after the
    grace (or the child's own fatal signal as 128+n); 126 found but not
    executable (any invocation failure of the command other than not-found);
    127 not found; 125 the runner's own failure (`runner_error` names it — a
    capture allocation or rewind fault, a group-setup failure, an interrupt,
    a failed cleanup operation, a failed census; the caller adds a capture
    fault during the replay)."""
    import tempfile
    t0 = time.monotonic()

    def _close_quiet(f):
        if f is not None:
            try:
                f.close()
            except (OSError, ValueError):
                pass

    # round 23 PR-MED-002: the captures are acquired INSIDE the runner's failure
    # boundary — a failed allocation is the runner's own 125 with nothing
    # started, and a capture acquired before the failure is released here
    out_f = err_f = None
    try:
        out_f = tempfile.TemporaryFile()
        err_f = tempfile.TemporaryFile()
    except (OSError, ValueError) as e:
        _close_quiet(out_f)
        _close_quiet(err_f)
        return 125, time.monotonic() - t0, False, False, None, None, "runner failed to prepare its capture files: %s" % e
    try:
        h = group_launch(argv, cwd=cwd, stdout=out_f, stderr=err_f, env=env)
    except OSError as e:
        # round 23 PR-MED-001: classified by PROVENANCE — the runner's own group
        # machinery is 125; what Popen raised for the COMMAND is coreutils
        # `timeout`'s rule: not found 127, any other invocation failure 126
        # (EACCES, ENOEXEC, ENOTDIR, E2BIG, a bad executable format, …)
        _close_quiet(out_f)
        _close_quiet(err_f)
        if isinstance(e, _GroupSetupError):
            return 125, time.monotonic() - t0, False, False, None, None, "runner failed to set up the group: %s" % e
        if isinstance(e, FileNotFoundError):
            return 127, time.monotonic() - t0, False, False, None, None, "command not found: %s" % e
        return 126, time.monotonic() - t0, False, False, None, None, "command not executable: %s" % e
    p = h["proc"]
    timed_out = killed = stopped = False
    runner_error = None
    cleanup_error = None
    rc = None
    deadline = t0 + timeout

    # round 21 PR-MED-001: a cleanup OPERATION that fails (an `OSError` from
    # the stop — EPERM over a child that changed credentials, a failed
    # TerminateJobObject — or a wait that fails otherwise than by its timeout)
    # is NAMED, never raised, and never claims the group was stopped; the later
    # safe steps still run, and nothing here waits unbounded
    def _cleanup_name(step, e):
        nonlocal cleanup_error
        cleanup_error = cleanup_error or ("%s failed — %s: %s; survivors may remain"
                                          % (step, type(e).__name__, str(e)[:120]))

    def _cleanup_try(step, fn):
        try:
            fn()
            return True
        except (OSError, subprocess.SubprocessError, ValueError) as e:
            _cleanup_name(step, e)
            return False

    def _cleanup_wait(t):
        """The leader's exit code, or None while it is still alive (the wait
        timed out) or when the wait itself failed (named)."""
        try:
            return p.wait(timeout=t)
        except subprocess.TimeoutExpired:
            return None
        except (OSError, subprocess.SubprocessError, ValueError) as e:
            _cleanup_name("reap", e)
            return None

    try:
        # ---- the principal wait, POLLED (round 20 PR-MED-001): short slices, the
        # interrupt latch read between them — a latched stop request (one that
        # arrived during the launch included) ends the wait like an interrupt;
        # the deadline ends it like a timeout; nothing raises out of here
        while True:
            if interrupts:
                stopped = True
                runner_error = "interrupted by %s — the group was stopped" % _signal_name(interrupts[0])
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            try:
                rc = p.wait(timeout=min(0.2, remaining))
                break
            except subprocess.TimeoutExpired:
                continue
            except (Exception, KeyboardInterrupt) as e:
                # an unexpected wait failure (round 19 PR-MED-001): still own the
                # cleanup below, then report the runner's failure
                stopped = True
                runner_error = "wait failed — %s: %s; the group was stopped" % (type(e).__name__, str(e)[:120])
                break
        # ---- the ONE cleanup owner (round 19 PR-MED-001): stop, grace, KILL,
        # reap, census, sweep — a signal arriving now is latched for the caller;
        # every operation contained (round 21 PR-MED-001)
        if p.poll() is None:
            # the leader is alive — the pgid is held, so a group stop is safe:
            # TERM, the operator's grace, then KILL and the reap's own bound
            # (round 22 PR-MED-001: never the grace again — it may be zero)
            _cleanup_try("stop", lambda: group_stop(h, kill=False))
            rc = _cleanup_wait(kill_after)
            if rc is None and p.poll() is None:
                if _cleanup_try("kill", lambda: group_stop(h, kill=True)):
                    killed = True
                rc = _cleanup_wait(_RB_KILL_REAP_S)
                if rc is None and p.poll() is None:
                    _cleanup_name("kill", RuntimeError("the leader is still alive after the KILL"))
            if stopped and cleanup_error is None:
                # an interrupt's stop counts as the kill only when every operation succeeded
                killed = True
        # the leader is gone; a surviving member (a grandchild) is swept on
        # every exit path, so the group never outlives the runner — when the
        # census can tell. A failed census is retried once, then named.
        members = group_members(h)
        if members is None:
            members = group_members(h)
        if members is None:
            runner_error = runner_error or "census failed — survivors unknown (no `ps` / Job query answered); the group may have outlived the runner"
        else:
            survivors = [x for x in members if x != p.pid]
            if survivors and _cleanup_try("sweep", lambda: group_stop(h, kill=True)):
                killed = True
    finally:
        group_close(h)
    if cleanup_error is not None:
        # the honest disposition: the earlier line's "stopped" claim withdrawn, the failed operation named
        runner_error = (("%s; " % runner_error.replace(" — the group was stopped", "")) if runner_error else "") + cleanup_error
    if rc is None:
        rc = p.poll() if p.poll() is not None else 125
    elapsed = time.monotonic() - t0
    if runner_error is not None:
        code = 125
    elif timed_out:
        code = 137 if killed else 124
    elif rc < 0:
        code = 128 + (-rc)
    else:
        code = rc
    try:
        out_f.seek(0)
        err_f.seek(0)
    except (OSError, ValueError) as e:
        # round 23 PR-MED-002: a capture that cannot be rewound is the runner's
        # own failure, named — the group's cleanup owner has already run
        _close_quiet(out_f)
        _close_quiet(err_f)
        runner_error = (("%s; " % runner_error) if runner_error else "") + "capture rewind failed — %s: %s" % (type(e).__name__, str(e)[:120])
        return 125, elapsed, timed_out, killed, None, None, runner_error
    return code, elapsed, timed_out, killed, out_f, err_f, runner_error


def cmd_run_bounded(argv):
    """The bounded runner's entry point. `argv` is `[--run <runkey> --role
    <role>] --timeout <s> [--kill-after <s>] [--cwd </abs/dir>] -- <cmd>
    [args...]` — no subcommand name in it; the ONE command line that reaches
    this function is `python3 scripts/loop-run-bounded.py <argv>` (v46.0: this
    helper's own CLI refuses the name `run-bounded`). The argv grammar (exit 2
    on a refusal, nothing run), then bounded_run, the verbatim replay (stdout,
    then stderr) and the ONE summary line LAST on stderr; the mapped code is
    the exit status. Writes no record (D27)."""
    timeout = kill_after = cwd = None
    seen = set()
    i = 0
    cmd = None
    while i < len(argv):
        tok = argv[i]
        if tok == "--":
            cmd = argv[i + 1:]
            break
        if tok in ("--timeout", "--kill-after", "--cwd", "--run", "--role"):
            if i + 1 >= len(argv):
                refuse("%s needs a value" % tok)
            if tok in seen:
                refuse("duplicate flag %s" % tok)
            seen.add(tok)
            val = argv[i + 1]
            if tok == "--timeout":
                timeout = _rb_seconds(val, tok, zero_ok=False)
            elif tok == "--kill-after":
                kill_after = _rb_seconds(val, tok, zero_ok=True)
            elif tok == "--cwd":
                if not os.path.isabs(val):
                    refuse("--cwd must be an absolute path")
                if not os.path.isdir(val):
                    envfail("--cwd %s is not a directory" % val)
                cwd = val
            elif tok == "--run":
                if not RUNKEY_RE.match(val):
                    refuse("--run %r is not a phase-scoped runkey — an iso-id never rides run= (the F-12 domain split)" % val, "stage-<N>")
            else:
                if val not in ENUMS["ROLE_ENUM"]:
                    refuse("--role must be one of %s" % ", ".join(sorted(ENUMS["ROLE_ENUM"])))
            i += 2
            continue
        refuse("run-bounded does not accept %r — its grammar is [--run <runkey> --role <role>] --timeout <s> [--kill-after <s>] [--cwd </abs/dir>] -- <cmd> [args...]" % tok[:60])
    if timeout is None:
        refuse("run-bounded requires --timeout <s>")
    if cmd is None:
        refuse("run-bounded requires `--` before the command")
    if not cmd:
        refuse("run-bounded: no command after `--`")
    # round 18 → 20 PR-MED-001: SIGINT / SIGTERM reach the runner at its executable boundary — the handler only
    # LATCHES; bounded_run's polled wait reads the latch and stops the group while its leader is alive; the
    # previous handlers are restored afterwards
    import signal
    _saved = {}
    _RUNNER_SIGNALS["latched"].clear()
    for _name in ("SIGINT", "SIGTERM"):
        _sig = getattr(signal, _name, None)
        if _sig is not None:
            try:
                _saved[_sig] = signal.signal(_sig, _runner_signal_handler)
            except (ValueError, OSError):
                pass
    try:
        code, elapsed, timed_out, killed, out_f, err_f, runner_error = bounded_run(
            cmd, timeout, 2.0 if kill_after is None else kill_after, cwd=cwd, interrupts=_RUNNER_SIGNALS["latched"])
    finally:
        for _sig, _prev in _saved.items():
            try:
                signal.signal(_sig, _prev)
            except (ValueError, OSError):
                pass
    if _RUNNER_SIGNALS["latched"]:
        # a signal that arrived DURING the cleanup (after the wait had ended) was latched — the group is already
        # handled; it is reported as the runner's failure (125) with the summary intact
        runner_error = runner_error or ("interrupted by %s during cleanup — the group was stopped"
                                        % _signal_name(_RUNNER_SIGNALS["latched"][0]))
        code = 125
        _RUNNER_SIGNALS["latched"].clear()
    # the verbatim replay — streamed from the capture files (round 16 LOW-003), stdout first, then stderr,
    # then the ONE summary line last on stderr; a closed or unwritable stream never changes the exit code.
    # round 18 PR-LOW-001: a non-empty stderr capture that does not end in LF gets ONE framing newline before
    # the summary (helper framing — the child's bytes are untouched), so the summary is always its own line.
    # round 24 PR-MED-002: the runner's own CAPTURE (source) faults — the tail probe, a read, a close — are named and
    # make the code 125; the DESTINATION's faults (a closed or unwritable stdout / stderr) stay tolerated as before.
    # A capture whose probe or read failed is framed with ONE newline regardless (its tail is unknown).
    _source_faults = []
    _err_needs_lf = False
    if err_f is not None:
        try:
            _size = err_f.seek(0, 2)
            if _size > 0:
                err_f.seek(-1, 2)
                _err_needs_lf = err_f.read(1) != b"\n"
            err_f.seek(0)
        except (OSError, ValueError) as e:
            _source_faults.append("capture probe failed — %s: %s" % (type(e).__name__, str(e)[:120]))
            _err_needs_lf = True
    for stream, cap in ((sys.stdout, out_f), (sys.stderr, err_f)):
        _dest_ok = True
        try:
            stream.flush()
        except (OSError, ValueError, AttributeError):
            _dest_ok = False
        if cap is None:
            continue
        _faulted = False
        try:
            while _dest_ok:
                try:
                    chunk = cap.read(1 << 16)
                except (OSError, ValueError) as e:
                    _source_faults.append("capture read failed — %s: %s" % (type(e).__name__, str(e)[:120]))
                    _faulted = True
                    break
                if not chunk:
                    break
                try:
                    stream.buffer.write(chunk)
                except (OSError, ValueError, AttributeError):
                    _dest_ok = False
            if _dest_ok:
                try:
                    if cap is err_f and (_err_needs_lf or _faulted):
                        stream.buffer.write(b"\n")
                    stream.buffer.flush()
                except (OSError, ValueError, AttributeError):
                    pass
        finally:
            try:
                cap.close()
            except (OSError, ValueError) as e:
                _source_faults.append("capture close failed — %s: %s" % (type(e).__name__, str(e)[:120]))
    if _source_faults:
        runner_error = (("%s; " % runner_error) if runner_error else "") + "; ".join(_source_faults)
        code = 125
    try:
        if runner_error is not None:
            sys.stderr.write("run-bounded: %s\n" % runner_error)
        sys.stderr.write("run-bounded: exit=%d elapsed=%.1f timed_out=%s killed=%s\n"
                         % (code, elapsed, "yes" if timed_out else "no", "yes" if killed else "no"))
        sys.stderr.flush()
    except (OSError, ValueError, AttributeError):
        pass
    sys.exit(code)


# --- v45.0 (T2.2 — D15 / D30): the RUNTIME — the shared functions the Python
# spawn wrapper (scripts/loop-spawn-wrapper.py) and the peer launcher
# (scripts/loop-peer-launcher.py) import from the blob-verified SNAPSHOT of
# this file (`importlib.util.spec_from_file_location` on the snapshot copy,
# never the checkout copy post-spawn — D30). The runtime is SMALL by decision:
# the route collector with its constants (below), the process-group / Job
# primitive (group_launch / group_members / group_alive / group_stop /
# group_close, above), `exit_census`, `canon_path` / `path_inside` (T1.3) and
# `bounded_run` (T1.5) — and, from v48.0, the role-liveness reader with its two
# probes (`proc_start_token`, `group_any`, `proc_alive`, `leg_liveness`,
# `run_legs`; below `exit_census`). Nothing here runs at import time: the
# module level is constants and definitions only (the helper's main() is
# __main__-guarded).
#
# The route collector is the ONE implementation of what v44.0 carried TWICE —
# the wrapper's embedded `ROUTE_SRC` one-shot and the launcher's `route_*`
# family — with the ownership rule every round from 9 to 41 hardened: the
# router in its OWN session with stdin from the null device and every other
# descriptor closed; both pipes drained concurrently, at most ROUTE_CAP bytes
# of each retained and the rest discarded (a producer never blocks on a full
# pipe; NO file-size limit is ever placed on the router — its own lease-store
# writes stay free); a stream past the cap ends the router's group at once →
# `overflow`; the ROUTE_DEADLINE on the whole collection → TERM on the group,
# a ROUTE_GRACE, KILL, reap → `timeout`; after the leader exits the readers
# get ROUTE_READER_GRACE to reach EOF, then the group is killed (a descendant
# holding a pipe) and both readers are joined under one further grace; a
# cancellation the CALLER's handler recorded (the `cancel` list — TERM / INT /
# HUP) is a terminal condition: the group ended at once, the verdict `other`
# (PR-MED-035); the group is SWEPT at every return (PR-MED-036); the leader's
# exit is OBSERVED with waitid / WNOWAIT, never reaped, until the last group
# signal — the ONE reap follows the sweep and releases the identity, nothing
# is signalled after it (PR-MED-037); ECHILD is a LOST reservation → released,
# `other` (PR-MED-041); on a python3 without os.waitid NO router is started
# (PR-MED-038 — the caller checks `hasattr(os, "waitid")` before calling and
# takes `other`). The ANSWER RULE's shape checks (`route_shape`) and folder
# checks (`route_dir_word`) and the second-line sanitizer (`route_skipped_text`
# — the records helper's value rule, line joins, ROUTE_SKIP_CAP bytes) are the
# one owner each; the wrapper and the launcher print their own line / note
# shapes from these results.
ROUTE_CAP = 4096
ROUTE_SKIP_CAP = 512   # the second outcome line's / second note's byte cap (v42.0 D5)
ROUTE_DEADLINE = 20.0
ROUTE_GRACE = 2.0
ROUTE_READER_GRACE = 1.0
# the contract's eleven stderr reason words (claude-switch-gui `route` schema 1)
ROUTE_WORDS = ("cache-dir-not-private", "lock-timeout", "records-unreadable",
               "bound-account-gone", "no-snapshot", "router-off", "no-server",
               "stale-snapshot", "records-full", "records-unwritable", "no-candidate")
# the collector's and the folder rule's OWN verdict words (v44.0's shell `case`
# guard: WORDS + these eight); `resume-mismatch` is the wrapper's resume rule
# (D6), applied by the wrapper after the collector; anything outside this
# closed grammar is `other`
ROUTE_OWN_WORDS = ("ok", "usage", "timeout", "overflow", "bad-json", "bad-schema", "no-dir", "bad-dir")
ROUTE_VERDICT_WORDS = ROUTE_WORDS + ROUTE_OWN_WORDS
_ROUTE_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


class _RouteStream(object):
    """One drained pipe. The stream holds the pipe HANDLE (the Popen's
    BufferedReader), never the bare descriptor number (round 18 PR-MED-029): a
    reader allowed to outlive the collection — a holder outside the router's
    group keeping the pipe open — then keeps the file object, and with it the
    descriptor, alive exactly as long as it can read again; the reaped Popen's
    finalizer cannot close the descriptor beneath it and a later open cannot
    reuse the number under it. The handle closes when the reader ends."""
    def __init__(self, handle):
        self.handle = handle
        self.kept = b""
        self.total = 0


def _route_drain(stream, flag):
    """Retain the first ROUTE_CAP bytes, discard the rest as it arrives (the
    producer never blocks on a full pipe); past the cap set the flag — the
    caller ends the group. Never raises; ends at EOF, on a read error, or on a
    handle the collector has closed (its fileno() raises ValueError)."""
    while True:
        try:
            chunk = os.read(stream.handle.fileno(), 65536)
        except (OSError, ValueError):
            return
        if not chunk:
            return
        stream.total += len(chunk)
        if len(stream.kept) < ROUTE_CAP:
            stream.kept += chunk[:ROUTE_CAP - len(stream.kept)]
        if stream.total > ROUTE_CAP:
            flag.set()


def _route_signal_group(pgid, sig):
    try:
        os.killpg(pgid, sig)
    except OSError:
        pass


def _route_reap(proc, bound):
    try:
        proc.wait(timeout=bound)
    except subprocess.TimeoutExpired:
        pass


def _route_leader_exited(proc, state):
    """Observe the router leader's exit WITHOUT reaping it (round 37
    PR-MED-037): a zombie leader keeps its struct pid referenced as the pid AND
    as the group's id, so every killpg on that number is ours until the ONE
    reap (_route_release). WNOWAIT leaves the status in place for that reap;
    WNOHANG never blocks. Never a reaping poll: a platform without os.waitid
    (CPython on macOS) never reaches here — the caller takes the no-answer
    fallback BEFORE any router is started (round 38 PR-MED-038). ECHILD is a
    LOST reservation, never an owned zombie (round 39 PR-MED-041): the leader
    was reaped behind our back (an ignored SIGCHLD auto-reaps — the callers
    set the default disposition before the pick, so this is defence in depth),
    its number is no longer ours, and nothing is signalled through it from
    here on — released on the spot, the verdict `other` (its exit status is
    unknowable)."""
    try:
        return os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
    except ChildProcessError:
        state["released"] = True
        state["lost"] = True
        return True
    except OSError:
        return False


def _route_wait_exited(proc, bound, state):
    """The grace between two group signals: wait, observing and never reaping,
    for the leader's exit."""
    limit = time.monotonic() + bound
    while not _route_leader_exited(proc, state):
        if time.monotonic() >= limit:
            return False
        time.sleep(0.05)
    return True


def _route_release(proc, state):
    """The ONE reap, after the last group signal. It RELEASES the identity:
    _route_end_group is a no-op from here on, so nothing is ever signalled
    through a number this collector no longer holds. proc.returncode is set."""
    state["released"] = True
    _route_reap(proc, ROUTE_GRACE)


def _route_end_group(pgid, proc, state):
    """TERM the router's whole group, a grace (observing, never reaping), then
    KILL the group unconditionally (a descendant that outlived a TERM-honouring
    leader is ended too). Signals only while the identity is still OURS — a
    released group is never signalled (PR-MED-037); the grace itself can lose
    the reservation (ECHILD, PR-MED-041), so the flag is read again before the
    KILL."""
    if state["released"]:
        return
    _route_signal_group(pgid, signal.SIGTERM)
    _route_wait_exited(proc, ROUTE_GRACE, state)
    if state["released"]:
        return
    _route_signal_group(pgid, signal.SIGKILL)
    _route_wait_exited(proc, ROUTE_GRACE, state)


def route_shape(kept):
    """The answer rule's SHAPE checks on the retained stdout prefix: (word,
    sticky, dir, reason) — `ok` with the literal dir, or a no-answer word;
    `reason` is this rule's own `<dir> <check>` on its bad-dir (relative /
    quote / control-byte / unicode-space, in that order — v42.0 D5/D9), ""
    otherwise. RecursionError: the decoder's nesting limit (about 1000
    containers, inside the cap) — a data failure, never an escaped exception
    (PR-MED-025)."""
    try:
        obj = json.loads(kept.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return "bad-json", False, "", ""
    if not isinstance(obj, dict):
        return "bad-json", False, "", ""
    schema = obj.get("route_schema")
    if isinstance(schema, bool) or not isinstance(schema, int) or schema != 1:
        return "bad-schema", False, "", ""
    folder = obj.get("dir")
    sticky = obj.get("sticky")
    if not isinstance(folder, str) or not isinstance(sticky, bool):
        return "bad-json", False, "", ""
    if not folder.startswith("/"):
        return "bad-dir", False, "", folder + " relative"
    if '"' in folder:
        return "bad-dir", False, "", folder + " quote"
    if any(ord(ch) < 32 or ord(ch) == 127 or 0xD800 <= ord(ch) <= 0xDFFF for ch in folder):
        # a lone surrogate the JSON decoder admitted counts as a control byte
        # (round 13 PR-MED-020): it cannot be written to stdout or exported
        return "bad-dir", False, "", folder + " control-byte"
    if any(ch != " " and ch.isspace() for ch in folder):
        # round 13 PR-MED-019: non-space Unicode whitespace in a folder fails
        # the answer rule, so every honoured folder — the SPAWN_ROUTE line /
        # the note, the export, the identity record — satisfies the records
        # helper's value rule by construction
        return "bad-dir", False, "", folder + " unicode-space"
    return "ok", sticky, folder, ""


def route_skipped_text(kept_err, local):
    """The second outcome line's / second note's text (v42.0 D5): what the
    router said beyond its reason word — its retained stderr AFTER the first
    line (the per-candidate `<dir> <reason>` lines a diagnosing router prints)
    — or, when the shape or folder rule refused the folder, that rule's own
    `<dir> <check>` (`local`). Child-controlled bytes that reach a journaled
    line: sanitized under the records helper's value rule (check_value_safety
    — a control byte, a double quote, or a non-space Unicode whitespace never
    reaches a record; each becomes a space here), line breaks joined with
    `; `, whitespace runs collapsed, at most ROUTE_SKIP_CAP bytes (a cut
    multibyte tail dropped). "" when nothing follows the word."""
    if local:
        text = local
    else:
        text = kept_err.decode("utf-8", "replace").strip()
        text = text.split("\n", 1)[1] if "\n" in text else ""
    parts = []
    for line in text.split("\n"):
        chars = []
        for ch in line:
            if (ord(ch) < 32 or ord(ch) == 127 or ch == '"' or (ch != " " and ch.isspace())
                    or 0xD800 <= ord(ch) <= 0xDFFF):
                # a lone surrogate (the JSON decoder admits one) is a space too
                # (round 13 PR-MED-020): the sanitizer is total over every
                # decoded router string and never raises
                chars.append(" ")
            else:
                chars.append(ch)
        clean = " ".join("".join(chars).split())
        if clean:
            parts.append(clean)
    return "; ".join(parts).encode("utf-8", "replace")[:ROUTE_SKIP_CAP].decode("utf-8", "ignore")


def _canon_quiet(p):
    """canon_path(p) or None — a path-rule refusal (a UNC spelling, a
    `/`-rooted spelling on Windows) answers None here instead of exiting: the
    folder rule reads it as `unresolvable`, never a refusal of the spawn."""
    try:
        if reason_of(canon_path, p) is not None:
            return None
        return canon_path(p)
    except (OSError, ValueError):
        return None


def route_dir_word(folder, roots):
    """The answer rule's FOLDER checks — the ONE owner (D3): (word, check) —
    the no-answer word AND the failing check (v42.0 D9) for a folder that
    fails, ("", "") for one that passes. `no-dir` = the folder does not exist
    (check `no-dir`); `bad-dir` = relative (`relative`), a double quote
    (`quote`) or a control character (`control-byte`) in the path, not owned
    by this user (`not-owned`), group- or world-writable (`group-writable` /
    `world-writable`), unresolvable or resolving to a path with a control
    character (`unresolvable`), or inside an executor- / peer-writable root
    (`inside-root`). `roots` are CANONICAL physical paths (canon_path); the
    containment is judged on the folder's canonical physical path through
    path_inside; the LITERAL folder is what the child receives and the
    identity records. On a Windows host the owner and mode checks do not apply
    (POSIX ownership and mode bits are not the NTFS model; router mode on a
    Windows-native host is deferred — Step 0 writes `Router: off`)."""
    if not folder.startswith("/"):
        return "bad-dir", "relative"
    if '"' in folder:
        return "bad-dir", "quote"
    if _ROUTE_CONTROL_RE.search(folder):
        return "bad-dir", "control-byte"
    if not os.path.isdir(folder):
        return "no-dir", "no-dir"
    try:
        st = os.stat(folder)
    except OSError:
        return "bad-dir", "unresolvable"
    if not HOST["is_windows"]:
        if st.st_uid != os.getuid():
            return "bad-dir", "not-owned"
        if st.st_mode & 0o020:
            return "bad-dir", "group-writable"
        if st.st_mode & 0o002:
            return "bad-dir", "world-writable"
    resolved = _canon_quiet(folder)
    if not resolved or _ROUTE_CONTROL_RE.search(resolved):
        return "bad-dir", "unresolvable"
    if any(path_inside(resolved, root) for root in roots):
        return "bad-dir", "inside-root"
    return "", ""


def _route_settle_readers(readers, proc):
    """After the router's group was ended on an exceptional exit: join the
    readers that are ALIVE (bounded; a never-started reader is not alive and
    is never joined — a join on it would raise), then release the pipe handles
    once none is alive (never under a blocked read)."""
    limit = time.monotonic() + ROUTE_GRACE
    for reader in readers:
        if reader.is_alive():
            try:
                reader.join(max(0.0, limit - time.monotonic()))
            except RuntimeError:
                pass
    if not any(reader.is_alive() for reader in readers):
        for handle in (proc.stdout, proc.stderr):
            try:
                handle.close()
            except OSError:
                pass


def route_collect(cmd, env=None, cancel=None):
    """Run the router ONCE through the collector: (word, sticky, dir, retained
    stdout bytes, retained stderr bytes, the shape rule's own reason — ""
    unless its bad-dir). `cancel` is the CALLER's recorded-signal list (its
    TERM / INT / HUP handler appends to it; None when the caller has none): a
    recorded cancellation is a terminal condition — the group ended inside the
    bound, the verdict `other` (PR-MED-035). The deadline covers the draining
    and the readers' completion, not only the direct child. The caller gates
    `hasattr(os, "waitid")` BEFORE calling (PR-MED-038) and sets the default
    SIGCHLD disposition for the router window (PR-MED-041)."""
    import threading
    flag = threading.Event()
    out = _RouteStream(None)
    err = _RouteStream(None)
    readers = []
    cancel = cancel if cancel is not None else []
    state = {"released": False, "lost": False}   # the identity is OURS until _route_release() reaps (PR-MED-037)
    #   — or until ECHILD reports it gone (`lost`, PR-MED-041); allocated BEFORE the router exists (PR-MED-039)
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=env, close_fds=True,
                                start_new_session=True)
    except OSError:
        return "other", False, "", b"", b"", ""
    pgid = proc.pid
    # ONE ownership boundary (round 17 PR-MED-028; round 16's reader-start guard
    # folded in): from here to the verdict the collector owns a live router in
    # its own session, and EVERY exceptional exit — whatever the exception,
    # wherever it is raised — ends that group (bounded), settles the readers
    # that are alive, releases the pipe handles, and then either returns the
    # no-answer verdict (an Exception — the caller continues on its fallback)
    # or re-raises after the same cleanup (an interruption that must propagate).
    # The one irreducible residue: an allocation failure inside the cleanup's
    # own few syscalls (killpg, waitpid) — no boundary in any program covers it.
    try:
        out.handle = proc.stdout
        err.handle = proc.stderr
        for stream in (out, err):
            reader = threading.Thread(target=_route_drain, args=(stream, flag))
            reader.daemon = True
            readers.append(reader)   # listed BEFORE start: an unstarted reader is not alive and is never joined
            reader.start()
        started = time.monotonic()
        timed_out = False
        cancelled = False
        while not _route_leader_exited(proc, state):
            if cancel:
                # a cancellation the caller's handler recorded (armed before the
                # router started, so one arriving during Popen is seen on the
                # first iteration): the terminal condition — the group ended now
                cancelled = True
                _route_end_group(pgid, proc, state)
                break
            if flag.is_set():
                _route_end_group(pgid, proc, state)
                break
            if time.monotonic() - started >= ROUTE_DEADLINE:
                timed_out = True
                _route_end_group(pgid, proc, state)
                break
            flag.wait(0.05)
        # The leader is gone (or the group was ended): the readers get a grace
        # to reach EOF, then the group is killed (a pipe-holding descendant) and
        # both readers are joined under one further grace.
        limit = time.monotonic() + ROUTE_READER_GRACE
        for reader in readers:
            reader.join(max(0.0, limit - time.monotonic()))
        if any(reader.is_alive() for reader in readers):
            if not state["released"]:   # a lost reservation is never signalled (PR-MED-041)
                _route_signal_group(pgid, signal.SIGKILL)
            limit = time.monotonic() + ROUTE_GRACE
            for reader in readers:
                reader.join(max(0.0, limit - time.monotonic()))
        if any(reader.is_alive() for reader in readers):
            # A holder outside the group keeps a pipe open: the drain did not
            # complete inside the bound, so the call is a timeout. The daemon
            # readers are left alone (a descriptor closed under a blocked read
            # is not ended and its number would be reused); they end with the
            # process.
            timed_out = True
        if time.monotonic() - started > ROUTE_DEADLINE:
            # ONE absolute deadline for the whole collection (round 15
            # PR-MED-026): a leader that exited just before it while the
            # draining or the reader joins ended after it is a timeout — never a
            # late honoured answer — and takes the terminal cleanup below (a
            # quiet same-group descendant included). The cleanup graces stay
            # separate from this deadline.
            timed_out = True
        if cancel:
            cancelled = True   # recorded after the leader exited: the verdict is still `other`
        # The group is SWEPT at every return (round 36 PR-MED-036), not only on
        # a terminal condition: a quiet same-group descendant of a normally
        # exited leader — its output descriptors closed, so both readers
        # reached EOF and no reader-liveness kill fired — or a cancellation
        # recorded after the sample above would otherwise outlive this
        # collector, the only owner the router's session has. The identity is
        # still OURS here: the leader was observed, never reaped (round 37
        # PR-MED-037), so the sweep's signals name a group the zombie leader
        # still reserves. The leader's exit still ends the REQUEST; the group
        # goes with it. Then the ONE reap releases the identity — nothing is
        # signalled after it.
        _route_end_group(pgid, proc, state)
        _route_release(proc, state)
        if not any(reader.is_alive() for reader in readers):
            for handle in (proc.stdout, proc.stderr):
                try:
                    handle.close()
                except OSError:
                    pass
        status = proc.returncode
        if state["lost"]:
            # the reservation was lost (ECHILD, PR-MED-041): the leader's exit
            # status is unknowable — Popen fabricates 0 on ECHILD — so no
            # answer, never the answer rule's "exit 0"
            return "other", False, "", out.kept, err.kept, ""
        if flag.is_set():
            return "overflow", False, "", out.kept, err.kept, ""
        if cancelled:
            return "other", False, "", out.kept, err.kept, ""
        if timed_out or status is None:
            return "timeout", False, "", out.kept, err.kept, ""
        if status < 0:
            return "other", False, "", out.kept, err.kept, ""
        if status == 2:
            return "usage", False, "", out.kept, err.kept, ""
        if status == 3:
            word = err.kept.decode("utf-8", "replace").strip().split("\n")[0].strip()
            return (word if word in ROUTE_WORDS else "other"), False, "", out.kept, err.kept, ""
        if status != 0:
            return "other", False, "", out.kept, err.kept, ""
        word, sticky, folder, local = route_shape(out.kept)
        return word, sticky, folder, out.kept, err.kept, local
    except BaseException as exc:
        _route_end_group(pgid, proc, state)   # a no-op once released: never a signal through a stale number
        _route_release(proc, state)
        _route_settle_readers(readers, proc)
        if not isinstance(exc, Exception):
            raise
        return "other", False, "", out.kept, err.kept, ""


def exit_census(h):
    """The wrapper's exit census over a group handle (T2.2): the number of
    processes still in the group after the leader was reaped — survivors — or
    None when the census itself failed (the caller records
    `refused=capture-failure`, never a fabricated `children=0`)."""
    members = group_members(h)
    if members is None:
        return None
    return len([pid for pid in members if pid != h["proc"].pid])


# --- v48.0 (plan-loop-autonomy-group-2 T6.1 / D16, D17, D23): the role-liveness
# reader. ONE implementation, in the runtime: the close's live-role guard
# (cmd_run_close), the watcher's verdict and its stop command, and the
# composer's clean close all ask it. (The spawn wrapper's pre-import code — its
# own start token in `<leg>.live`, and the tail's test that a supervisor it
# cannot wait for has gone — runs on a wrapper-local boot twin of
# proc_start_token, pinned to this function by the wrapper selftest: the tail
# never imports this module.)
#
# The evidence, per leg, in the run's log root:
#   <stem>.live   written by the wrapper when it starts (its own pid and start
#                 token) and rewritten once the role is launched (the role's
#                 pid, start token and process group);
#   <stem>.exit   what `.live` becomes when the wrapper ends: the role's
#                 identity kept, the exit code, the time and the exit census's
#                 result added. It says the WRAPPER finished — never that the
#                 role's work has stopped (a normal exit records surviving
#                 children and kills none; a signalled wrapper does not wait
#                 for a role that ignores the signal);
#   an identity record (a file holding a `wrapper_pid=` line and a `leg=`
#                 line, whatever its name) — the only evidence a leg from
#                 before this release has: two pids, no start token.
# <stem> is the leg, or the leg with a numbered suffix when that name was
# taken; a reader goes by the `leg=` line inside, never by the file's name.
#
# The three words. `live`: the wrapper is alive by its token, or the recorded
# role is, or any process remains in the role's group — whatever files exist.
# `over`: positive termination — the wrapper is dead or wrote `.exit`, the
# recorded role is dead, and no process remains in its group; or `.exit`
# records that no role was launched; on a Windows host the `.exit` of a
# launched leg alone, because the wrapper writes it after it closed the role's
# Job (which ends every member). `unknown`: everything else — a malformed
# record included, on every host. A dead wrapper alone is never `over`,
# and `unknown` is never treated as `over` by any caller.
LEG_LIVE_SUFFIX = ".live"
LEG_EXIT_SUFFIX = ".exit"
LEG_FILE_CAP = 65536          # a leg file or an identity record is a few hundred bytes
LEG_WORDS = ("live", "over", "unknown")
_PROC_STAT = "/proc/%d/stat"


def proc_start_token(pid):
    """The start token of process `pid`, as `(state, token)`:
    ("alive", <token>) — the process exists and its token was read;
    ("gone", None) — no such process; ("unknown", None) — it may exist, and
    the token could not be read, or this host has neither source.
    Linux: field 22 of /proc/<pid>/stat (the start time in clock ticks since
    boot), parsed after the LAST `)` — the command name before it may hold
    blanks and parentheses. Any other POSIX host: `LC_ALL=C ps -o lstart= -p
    <pid>` (macOS has no /proc). A Windows host has neither: unknown. The
    token is OPAQUE — compared for equality with a recorded one, never
    ordered or parsed. A zombie still has its token and reads alive: it
    holds its pid (and its group) until it is reaped."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0 or pid > LEG_PID_MAX:
        return "unknown", None
    if HOST["is_windows"]:
        return "unknown", None
    try:
        with open(_PROC_STAT % pid, "rb") as fh:
            data = fh.read(4096)
    except (FileNotFoundError, ProcessLookupError):
        # no such entry: the process is gone IF this host has a procfs at all
        if os.path.exists(_PROC_STAT % os.getpid()):
            return "gone", None
        data = None
    except OSError:
        return "unknown", None
    if data is not None:
        fields = data.rpartition(b")")[2].split()
        # after the `)`: field 3 (state) is index 0, so field 22 is index 19
        if len(fields) > 19 and fields[19].isdigit():
            return "alive", fields[19].decode("ascii")
        return "unknown", None
    try:
        r = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True,
                           timeout=20, env=dict(os.environ, LC_ALL="C"))
    except (OSError, subprocess.SubprocessError, ValueError):
        return "unknown", None
    token = " ".join((r.stdout or "").split())
    if r.returncode == 0 and token:
        return "alive", token
    if r.returncode == 1 and not token and not (r.stderr or "").strip():
        return "gone", None      # `ps -p` exits 1 and prints nothing when no process matched
    return "unknown", None


def proc_alive(pid, token):
    """Is the process RECORDED as `(pid, start token)` still running?
    "live" — the pid exists and its token equals the recorded one; "dead" —
    the pid does not exist (a pid that is gone is dead without needing a
    token), or it exists under ANOTHER token (the number was reused);
    "unknown" — the pid exists and its token cannot be read, or the record
    holds no token to compare (a leg from before this release), or the
    record's pid is no positive integer."""
    state, current = proc_start_token(pid)
    if state == "gone":
        return "dead"
    if state != "alive" or not token or token == "unknown":
        return "unknown"
    return "live" if current == token else "dead"


def group_any(pgid):
    """Is any process left in process group `pgid`? True / False, or None
    when it could not be tested (a Windows host — a Job has no number another
    process can ask by — or an error other than the two the kernel answers
    with). Signal 0 is the test: delivered to nothing, it only reports — no
    such group (False), or a group this user may not signal (True: it
    exists). A zombie member counts until it is reaped. A number the OS call
    itself refuses — above what a C `pid_t` holds (round 42 PR-LOW-013) — is
    "could not be tested", never an exception."""
    if HOST["is_windows"] or not isinstance(pgid, int) or isinstance(pgid, bool) or pgid <= 1 or pgid > LEG_PID_MAX:
        return None
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (OSError, OverflowError, ValueError):
        return None
    return True


LEG_PID_MAX = 2147483647      # the largest pid a C `int` holds; a larger number in a leg file names no process


def _leg_int(kv, key):
    """A pid field of a leg file or an identity record as an int, or None
    when it is not one (round 42 PR-LOW-013): ASCII decimal digits only —
    `str.isdigit` alone is true for digits `int` refuses, a superscript two
    among them — and nothing above LEG_PID_MAX, which the OS calls refuse.
    None is what every caller already reads as a malformed record:
    `unknown`. `0` stays a number (the legacy `claude_pid=0` of a launch
    that started no role)."""
    v = kv.get(key, "")
    if not v or len(v) > 10 or not (v.isascii() and v.isdigit()):
        return None
    n = int(v)
    return n if n <= LEG_PID_MAX else None


def _role_over(role_pid, role_token, pgid):
    """The recorded role and its group: "live" (the role runs, or a process
    remains in its group), "over" (the role is dead and its group is empty),
    or "unknown". A process group's number is its first leader's pid, and a
    pid is not handed out again while a group of that number exists — so a
    role pid that now belongs to ANOTHER process (a different token, or a pid
    that was gone and is there again after the group test) proves the role's
    own group was already empty; without that rule a recycled number would
    read `live` for as long as its new owner runs. The rule needs the role to
    have led its group (the wrapper starts every role in a new session, so
    the two numbers are equal); a record where they differ is `unknown`."""
    if pgid != role_pid:
        return "unknown"
    state, current = proc_start_token(role_pid)
    if state == "unknown":
        return "unknown"
    if state == "alive":
        if not role_token or role_token == "unknown":
            return "unknown"
        return "live" if current == role_token else "over"
    members = group_any(pgid)
    if members is None:
        return "unknown"
    if not members:
        return "over"
    again, _tok = proc_start_token(role_pid)
    if again == "gone":
        return "live"       # the leader is gone and its group still has a member
    return "over" if again == "alive" else "unknown"


def leg_liveness(kind, kv):
    """One leg's word from its evidence — `kind` is "exit", "live" or
    "identity", `kv` the file's key=value lines. Returns `(word, pids)`:
    the word is one of LEG_WORDS, `pids` the recorded numbers as text for a
    refusal's detail."""
    def shown(n):
        return "none" if n is None else "%d" % n   # a number this reader parsed, never the file's own text

    wpid = _leg_int(kv, "wrapper_pid")
    if kind == "identity":
        rpid = _leg_int(kv, "claude_pid")
        pids = "wrapper_pid=%s claude_pid=%s" % (shown(wpid), shown(rpid))
        if wpid is None or rpid is None:
            return "unknown", pids
        # two pids and no token: gone is dead, anything else cannot be tied to the leg
        if proc_start_token(wpid)[0] != "gone":
            return "unknown", pids
        if rpid == 0:
            return "over", pids                 # the record of a launch that started no role
        if proc_start_token(rpid)[0] != "gone":
            return "unknown", pids
        members = group_any(rpid)               # the role led its own group: the group is its pid
        if members is None:
            return "unknown", pids
        if not members:
            return "over", pids
        return ("live" if proc_start_token(rpid)[0] == "gone" else "unknown"), pids
    rpid, pgid = _leg_int(kv, "role_pid"), _leg_int(kv, "role_pgid")
    pids = "wrapper_pid=%s role_pid=%s role_pgid=%s" % (shown(wpid), shown(rpid), shown(pgid))
    if kind == "exit":
        if kv.get("launched") == "no":
            return "over", pids
        if kv.get("launched") != "yes" or rpid is None or pgid is None:
            # `launched=unknown` (a child may run outside the group), no such line,
            # or a launched leg with no role identity: a malformed record on every host
            return "unknown", pids
        if HOST["is_windows"]:
            return "over", pids                 # written after the Job was closed: no member outlives that
        return _role_over(rpid, kv.get("role_start"), pgid), pids
    # kind == "live": the wrapper has not written its end
    if wpid is None:
        return "unknown", pids
    wrapper = proc_alive(wpid, kv.get("wrapper_start"))
    if wrapper == "live":
        return "live", pids
    if rpid is None or pgid is None:
        return "unknown", pids                  # it died (or cannot be read) before it recorded a role
    role = "unknown" if HOST["is_windows"] else _role_over(rpid, kv.get("role_start"), pgid)
    if role == "live":
        return "live", pids
    return ("over" if role == "over" and wrapper == "dead" else "unknown"), pids


def _leg_word(kind, kv):
    """leg_liveness as a TOTAL read (round 42 PR-LOW-013): a record whose
    values make a probe raise is a malformed record, and a malformed record
    is `unknown` — the reader never ends its caller in a traceback and never
    turns a failure into `over`."""
    try:
        return leg_liveness(kind, kv)
    except Exception:
        return "unknown", "none"


def _leg_read(log_root, name):
    """One log-root file's key=value lines (first wins), or None when it is
    not a small regular file read without following a link."""
    try:
        data = _away_read_bytes(os.path.join(log_root, name), follow=False, cap=LEG_FILE_CAP)
        return _rc_parse_kv_lines(data.decode("utf-8").splitlines())[0]
    except (OSError, ValueError):
        return None


def run_legs(log_root):
    """Every leg the log root holds evidence of, as a list of
    `{"leg", "run", "word", "pids", "source", "file"[, "wrapper_pid"]}`
    sorted by file name — `[]` when the folder does not exist or holds none
    (a run with no leg evidence blocks nothing). ONE entry per wrapper, which
    is one per file STEM: its `.exit` file, else its `.live` file — so a leg
    value used twice (`<leg>.*`, `<leg>.2.*`) has two entries with the same
    `leg`, and the first wrapper's `.exit` never stands in for the second
    one's role. A `.live` / `.exit` file that cannot be read is an entry
    whose word is `unknown`; so is a log root that exists and cannot be
    listed. An identity record is taken only for a leg value NO leg file
    names (every wrapper of this release writes its leg files beside its
    identity record): it is the evidence of a leg from before this
    release."""
    try:
        names = sorted(os.listdir(log_root))
    except (FileNotFoundError, NotADirectoryError):
        return []
    except OSError:
        return [{"leg": "?", "run": "?", "word": "unknown", "pids": "none", "source": "log-root", "file": "."}]
    legs, seen, present = [], set(), set(names)
    for suffix, kind in ((LEG_EXIT_SUFFIX, "exit"), (LEG_LIVE_SUFFIX, "live")):
        for name in names:
            if not name.endswith(suffix):
                continue
            if kind == "live" and name[:-len(suffix)] + LEG_EXIT_SUFFIX in present:
                continue                         # the SAME wrapper's `.exit` outranks the `.live` left beside it
            kv = _leg_read(log_root, name)
            if kv is None or not kv.get("leg"):
                legs.append({"leg": "?", "run": "?", "word": "unknown", "pids": "none", "source": kind, "file": name})
                continue
            # one entry per FILE STEM, not per leg value: a leg value used twice has
            # two wrappers (`<leg>.*`, `<leg>.2.*`), and the first one's `.exit`
            # says nothing about the second one's role
            seen.add((kv.get("run", ""), kv["leg"]))
            word, pids = _leg_word(kind, kv)
            legs.append({"leg": kv["leg"], "run": kv.get("run", ""), "word": word, "pids": pids, "source": kind, "file": name,
                         "wrapper_pid": _leg_int(kv, "wrapper_pid")})
    for name in names:
        if name.endswith((LEG_EXIT_SUFFIX, LEG_LIVE_SUFFIX, ".log", ".out", ".err", ".pre")):
            continue
        try:
            st = os.lstat(os.path.join(log_root, name))
        except OSError:
            continue
        if not stat.S_ISREG(st.st_mode) or st.st_size > LEG_FILE_CAP:
            continue
        kv = _leg_read(log_root, name)
        if kv is None or not kv.get("leg") or "wrapper_pid" not in kv:
            continue                             # (a `wrapper_pid=` that is no pid is still an identity record: `unknown`)
        key = (kv.get("run", ""), kv["leg"])
        if key in seen:
            continue
        seen.add(key)
        word, pids = _leg_word("identity", kv)
        legs.append({"leg": kv["leg"], "run": kv.get("run", ""), "word": word, "pids": pids, "source": "identity", "file": name,
                     "wrapper_pid": _leg_int(kv, "wrapper_pid")})
    return sorted(legs, key=lambda l: l["file"])


LEG_ATTEST_WORD = "owner-dead"   # D17's attestation word; D23: an `unknown` leg's composer-written end names it in result=


def leg_end_refusal(log_root, run, leg, result):
    """v48.0 (D23): may a `ROLE: end` for `leg` be written now? None when it
    may, else the refusal's text. The rule binds only a leg the log's folder
    holds evidence of (a `.live` / `.exit` file or an identity record naming
    this run= and leg=) — a launcher leg, a hand-route activation and every
    leg of a run with no such file are admitted as before. For such a leg:
      - the leg's OWN WRAPPER is admitted: the calling process's parent is
        the `wrapper_pid` the leg's `.live` file (or identity record) names
        and that file is not an `.exit` — the wrapper runs this helper as
        its child, and writes the end before its `.exit`;
      - anyone else — the composer's clean close — is admitted only when the
        reader says `over` for every file of the leg; a `live` leg refuses
        (its wrapper writes the end itself, or its role still runs); an
        `unknown` leg refuses unless `result=` names the operator's
        attestation (the word `owner-dead`, which also admits the close).
    A mis-attribution guard like the helper's other seat rules, never caller
    authentication."""
    mine = [l for l in run_legs(log_root) if l["run"] == run and l["leg"] == leg]
    if not mine or any(l["source"] != "exit" and l.get("wrapper_pid") == os.getppid() for l in mine):
        return None
    for word in ("live", "unknown"):
        hit = next((l for l in mine if l["word"] == word), None)
        if hit is None or (word == "unknown" and LEG_ATTEST_WORD in result):
            continue
        tail = ("its wrapper writes the leg's end itself when it finishes, and a role that outlived its wrapper is still running"
                if word == "live" else
                "the evidence cannot tie a process to the role; the end is written only on the operator's attestation, named in result= by the word `%s` (the word that admits the close)" % LEG_ATTEST_WORD)
        return ("ROLE:end run=%s leg=%s — the leg reads %s (%s; %s): a composer-written end for a wrapper-spawned leg is the clean close, admitted only once the role-liveness reader says over — %s (v48.0 D23)"
                % (run, leg, word, hit["pids"], hit["file"] if LEG_RE.match(hit["file"]) else "<unprintable>", tail))
    return None


# --- v48.0 (plan-loop-autonomy-group-2 T7.6 / D12, D14): the composer seat ----
# A watcher takeover (scripts/loop-watchdog.py) is a second composer for a run
# whose own composer's process is gone. The seat is what keeps the two from
# both writing the run's records. Five files, named after the run and placed
# beside its journal and its policy log, in `<base>/.cursor/loops`:
#   <iso>-seat        a takeover holds an exclusive lock on it for its whole
#                     life (taken by the watcher, inherited by the takeover's
#                     process, released by the kernel when that process ends);
#                     its bytes name the holder — nonce=, ts=, watcher_pid=,
#                     and, once the takeover's group is published, pgid= with
#                     stage_start=, the start token of that group's leader
#                     (round 49 PR-HIGH-006: the lock says SOMEBODY holds the
#                     file; only the token says whose group the text names —
#                     signal_authority is the one test, and a record that
#                     does not pass it is never signalled);
#   <iso>-seat.gate   a short lock that serialises every admission below and
#                     the watcher's acquisition;
#   <iso>-notakeover  the operator's durable no-takeover mark (the stop
#                     command writes it; an interactive identity write clears
#                     it);
#   <iso>-composer    the composer identity record (D11);
#   <iso>-takeovers   the run's takeover ledger (round 49 PR-MED-033): the
#                     stall in progress, its attempts and next step, and the
#                     day's attempt times — the run's own, whatever folder a
#                     watcher keeps its state in. The watcher writes it.
# `loop-watchdog.py identity` creates the first two, and never removes either
# (round 49 PR-MED-032: a lock file's path is stable for the run's life; a
# seat file with no gate beside it admits no protected write). A run with no
# `<iso>-seat` file — one started before this release, a host without file locks (Windows),
# a run whose log folder is not `<base>/.cursor/loops/<iso>`, a run with no
# journal (a run with no run worktree) or with one that cannot be read — is admitted
# exactly as before, and the watcher never takes it over.
#
# WHAT IS PROTECTED is defined by ownership, in three tables read by main():
# SEAT_SUBCOMMANDS classes every subcommand, SEAT_AWAY_VERBS every `away`
# verb, and SEAT_WHERE says where a gated subcommand's run is read from. Inside
# `emit` the test is the record's owner, the role flag: an emit under
# `--role composer` is gated; an emit under a role's own flag is never gated
# (and the helper already refuses a composer-owned subtype under such a flag —
# check_seat_gate). Never gated: a role's wrapper's and the peer launcher's
# records (they ride the role's flag), every `escape-check`, a role's own
# `VERIFY_OK` and `ROLE:round`, and every read-only subcommand and verb.
# One boundary, stated: the run is found from where the write GOES — the
# folder of `--log` for emit / flush / idle-check, `--base` and `--iso` for
# run-close and fold-delegation, the policy log's folder and `--iso` for
# `away`. A composer-flagged `emit` with no `--log` prints its line to stdout,
# names no run, and is not gated: the helper writes nothing for it.
#
# THE ONE ADMISSION ROUTINE (seat_admit): take the gate; while holding it,
# test the seat's lock; free → admitted when the caller carries no LOOP_SEAT;
# held → admitted only when the caller's LOOP_SEAT equals the recorded nonce.
# main() holds the gate through the entry point's own read, decision and
# write and releases it only after them, so no check-then-unlocked-write
# window exists: a writer holds the gate through its append, and the watcher
# needs the gate to take the seat. Two rules on the refusing side beyond D12's
# words: a caller that carries LOOP_SEAT is admitted ONLY as the holder (a
# free seat, another nonce, or a run with no seat file refuses it — a
# takeover's leftover shell never writes after its takeover has ended), and
# while the no-takeover mark stands a holder's writes are refused as well.
# This is a MIS-ATTRIBUTION guard like the helper's other seat rules, never
# caller authentication: it protects the run's records and release acts, not
# file edits and not the transcript. Record-then-act is what turns a refused
# record into a stopped act.
try:
    import fcntl as _fcntl
except ImportError:                      # a host without POSIX file locks: no seat, no takeover
    _fcntl = None
SEAT_ENV = "LOOP_SEAT"
SEAT_NONCE_RE = re.compile(r"\A[0-9a-f]{32}\Z")
SEAT_FILE_SUFFIXES = (("seat", "-seat"), ("gate", "-seat.gate"), ("mark", "-notakeover"), ("composer", "-composer"),
                      ("ledger", "-takeovers"))
SEAT_FILE_CAP = 4096
SEAT_GATE_WAIT_S = 30.0          # a writer's bounded wait for the gate
SEAT_GATE_POLL_S = 0.05
SEAT_CLASSES = ("gated", "open", "read")
# every subcommand of SUB_GRAMMAR, classed: `gated` — a composer-owned write;
# `open` — a role-owned write (the exception list); `read` — writes no
# record; `by-role` / `by-verb` / `by-dry-run` — decided by seat_class below
SEAT_SUBCOMMANDS = {
    "emit": "by-role", "escape-check": "open", "flush": "by-dry-run", "idle-check": "gated",
    "run-close": "gated", "fold-delegation": "gated", "attest-check": "read", "away": "by-verb",
    "records-delta": "read", "quoted-block": "read",
}
SEAT_AWAY_VERBS = {"grant": "gated", "end": "gated", "ci-verdict": "gated",
                   "check": "read", "report": "read", "census": "read", "lint": "read"}
# where a gated subcommand's run is read from: the folder of --log, --base
# with --iso, or the policy log's folder with --iso
SEAT_WHERE = {"emit": "log", "flush": "log", "idle-check": "log",
              "run-close": "base", "fold-delegation": "base", "away": "policy"}
SEAT_POLICY_LOG_SUFFIX = "-policy.log"   # `<loops>/<iso>-policy.log`: a `--log` sink of this name is the run's policy log


class _SeatBusy(Exception):
    """The gate could not be had in the bounded wait (or could not be opened)."""


def seat_supported():
    """Does this host have the seat at all — POSIX file locks that a child
    inherits and the kernel releases at its death?"""
    return _fcntl is not None and not HOST["is_windows"]


def seat_paths(loops, iso):
    """The run's five seat-family paths under the loops directory, by kind."""
    return dict((kind, os.path.join(loops, iso + suffix)) for kind, suffix in SEAT_FILE_SUFFIXES)


def seat_class(sub, etype=None, role=None, dry_run=False):
    """One invocation's seat class — `gated`, `open` or `read` — from the
    tables above. `etype` is emit's TYPE, or `away`'s verb. A subcommand or a
    verb the tables do not name is `gated`: an unclassified writer fails
    toward the protected side."""
    cls = SEAT_SUBCOMMANDS.get(sub, "gated")
    if cls == "by-role":
        return "gated" if role == "composer" else "open"
    if cls == "by-verb":
        return SEAT_AWAY_VERBS.get(etype, "gated")
    if cls == "by-dry-run":
        return "read" if dry_run else "gated"
    return cls


def _seat_sink(path):
    """Where a write to `path` will LAND (round 49 PR-MED-031): the physical
    path, every link resolved, the leaf included — canon_path's physical
    form, the helper's one resolver. On a host with no seat the spelling is
    kept as it is (nothing is looked up there, and canon_path's own refusals
    for a path spelling are not this lookup's to raise)."""
    return canon_path(path) if seat_supported() else os.path.abspath(path)


def seat_where(sub, flags):
    """`(loops directory, iso)` for a gated invocation, or None when its argv
    names no run folder — a relative or missing path (the subcommand's own
    refusal follows), or an `emit` that prints to stdout.
    Round 49 PR-MED-031: for the `log` and `policy` families the run is read
    from where the write will LAND, not from how its path is spelled — the
    sink is resolved through every link first (_seat_sink, the leaf
    included, as the append follows them), so a symlink to the run's log
    folder, or one standing at the log's own name, selects the same seat as
    the canonical path. The residual, stated: a path swapped between this
    read and the append is a file edit by another hand, which the seat does
    not protect (a mis-attribution guard, never caller authentication)."""
    how = SEAT_WHERE.get(sub)
    if how == "log":
        path = flags.get("--log")
        if not path or not os.path.isabs(path):
            return None
        sink = _seat_sink(path)
        folder, name = os.path.dirname(sink), os.path.basename(sink)
        if name.endswith(SEAT_POLICY_LOG_SUFFIX) and ISO_ID_RE.match(name[:-len(SEAT_POLICY_LOG_SUFFIX)]):
            # round 69 SEC-001: a record emitted INTO the run's policy log (`config-snapshot`, `config-revoke` — the
            # card's `--log <policy log>` recipes). That log sits in the loops directory itself, beside the journal: the
            # run is named by the FILE, not by its folder. Read as a stage log it named the run `loops` under
            # `<base>/.cursor`, whose seat never exists — so the write was admitted beside a held seat, and a
            # takeover's own was refused as a carrier with no seat.
            loops, iso = folder, name[:-len(SEAT_POLICY_LOG_SUFFIX)]
        else:
            loops, iso = os.path.dirname(folder), os.path.basename(folder)
    elif how == "base":
        base, iso = flags.get("--base"), flags.get("--iso")
        if not base or not os.path.isabs(base):
            return None
        loops = os.path.join(os.path.abspath(base), ".cursor", "loops")
    elif how == "policy":
        pol, iso = flags.get("--policy-log"), flags.get("--iso")
        if not pol or not os.path.isabs(pol):
            return None
        loops = os.path.dirname(_seat_sink(pol))
    else:
        return None
    return (loops, iso) if iso and ISO_ID_RE.match(iso) else None


def _seat_kv(path):
    """The seat file's key=value lines (first wins), or None when it is not a
    small regular file read without following a link."""
    try:
        data = _away_read_bytes(path, follow=False, cap=SEAT_FILE_CAP)
        return _rc_parse_kv_lines(data.decode("utf-8").splitlines())[0]
    except (OSError, ValueError):
        return None


def _seat_lock_busy(e):
    return e.errno in (errno.EWOULDBLOCK, errno.EAGAIN, errno.EACCES)


def seat_state(paths):
    """Who holds the run's seat: `(word, kv)`.
      `none`    — there is no seat file, or this host has no file locks;
      `free`    — the seat file is there and nobody holds its lock;
      `held`    — a takeover holds it; `kv` is the file's holder record
                  (nonce=, ts=, watcher_pid=, pgid= once published);
      `unknown` — the file is there and could not be opened or tested.
    The test is a SHARED non-blocking lock, released at once: it conflicts
    with the holder's exclusive lock alone, so two readers never make each
    other read `held`."""
    if not seat_supported():
        return "none", {}
    try:
        fd = _open_at(None, paths["seat"], os.O_RDONLY | getattr(os, "O_CLOEXEC", 0), follow=False, nonblock=True)
    except FileNotFoundError:
        return "none", {}
    except (OSError, ValueError):
        return "unknown", {}
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return "unknown", {}
        try:
            _fcntl.flock(fd, _fcntl.LOCK_SH | _fcntl.LOCK_NB)
        except OSError as e:
            if _seat_lock_busy(e):
                return "held", (_seat_kv(paths["seat"]) or {})
            return "unknown", {}
        return "free", {}
    finally:
        os.close(fd)


def seat_gate_take(paths, wait_s=None):
    """Take the run's gate: the descriptor that holds it, or None when there
    is no gate file (or no file locks on this host). Raises _SeatBusy when the
    gate is not free within `wait_s` seconds (SEAT_GATE_WAIT_S by default; 0
    is one try) or cannot be opened. Released by seat_gate_release, or by the
    kernel when the process ends."""
    if not seat_supported():
        return None
    try:
        fd = _open_at(None, paths["gate"], os.O_RDONLY | getattr(os, "O_CLOEXEC", 0), follow=False, nonblock=True)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        raise _SeatBusy("the seat's gate %s could not be opened (%s)" % (paths["gate"], e))
    deadline = time.monotonic() + (SEAT_GATE_WAIT_S if wait_s is None else wait_s)
    while True:
        try:
            _fcntl.flock(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
            return fd
        except OSError as e:
            if not _seat_lock_busy(e):
                os.close(fd)
                raise _SeatBusy("the seat's gate %s could not be locked (%s)" % (paths["gate"], e))
        if time.monotonic() >= deadline:
            os.close(fd)
            raise _SeatBusy("the seat's gate %s was not free in the bounded wait — another protected write, or a takeover's launch, holds it; try again"
                            % paths["gate"])
        time.sleep(SEAT_GATE_POLL_S)


def seat_gate_release(fd):
    if fd is not None:
        try:
            os.close(fd)
        except OSError:
            pass


def seat_refusal(paths, nonce, iso):
    """The seat's verdict on ONE protected write, read under the gate: None
    when it is admitted, else the refusal's text with its class word in
    parentheses — `seat-held` (a takeover holds the seat and the caller is not
    it), `seat-not-holder` (the caller carries LOOP_SEAT and is not the
    holder, or the no-takeover mark stands), `seat-unknown` (the seat file is
    there and could not be tested: evidence that cannot be read never
    admits)."""
    word, kv = seat_state(paths)
    stop = LOOP_STOP_RECIPE % iso
    if nonce:
        if os.path.lexists(paths["mark"]):
            return ("the no-takeover mark %s stands — the operator stopped automatic continuation for this run, and a takeover's "
                    "writes are refused from then on (seat-not-holder)" % paths["mark"])
        if word == "held" and SEAT_NONCE_RE.match(nonce) and kv.get("nonce") == nonce:
            return None
        return ("%s is set in this environment and it is not the nonce of a takeover holding this run's seat (the seat reads %s) — "
                "a takeover's shell writes only while its own takeover holds the seat (seat-not-holder)" % (SEAT_ENV, word))
    if word == "held":
        pgid, since = _leg_int(kv, "pgid"), kv.get("ts", "")
        return ("the run's composer seat is held by a watcher takeover (group %s, since %s) and this write is not the holder's — "
                "nothing was written; an interactive composer goes on only after the operator's stop: %s --takeover-only (seat-held)"
                % ("unpublished" if pgid is None else "%d" % pgid, since if TS_LOCAL_RE.match(since) else "unknown", stop))
    if word == "unknown":
        return ("the run's seat file %s could not be opened or tested — a seat that cannot be read never admits a composer write; "
                "nothing was written (seat-unknown)" % paths["seat"])
    return None


def seat_admit(loops, iso, env=None, wait_s=None):
    """THE one admission routine (D12): `(gate, refusal)`. A run with no seat
    file and a caller with no LOOP_SEAT is admitted as before this release —
    `(None, None)`, nothing opened. Otherwise the gate is taken (a bounded
    wait) and the seat judged under it: admitted → `(gate descriptor or None,
    None)`, and the CALLER keeps the gate through its own read, decision and
    write, releasing it with seat_gate_release only after them; refused →
    `(None, text)`, the gate already released."""
    env = os.environ if env is None else env
    nonce = env.get(SEAT_ENV, "")
    paths = seat_paths(loops, iso)
    if not nonce and not os.path.lexists(paths["seat"]):
        return None, None
    try:
        gate = seat_gate_take(paths, wait_s)
    except _SeatBusy as e:
        return None, "%s (seat-gate-busy)" % e
    if gate is None and seat_supported() and os.path.lexists(paths["seat"]):
        # round 49 PR-MED-032: an incomplete pair never lets a writer skip the
        # serialisation — a holder may still own the seat, and nothing would
        # order this write against the watcher's acquisition
        return None, ("the run's seat file %s is there and its gate %s is not — a protected write is never admitted without the gate; "
                      "nothing was written. `python3 scripts/loop-watchdog.py identity` recreates the missing file and removes neither "
                      "(seat-gate-missing)" % (paths["seat"], paths["gate"]))
    why = seat_refusal(paths, nonce, iso)
    if why is not None:
        seat_gate_release(gate)
        return None, why
    return gate, None


# --- v48.0 (T7.2 / D13, D14, D19): the readers the watcher loads --------------
# The watcher (scripts/loop-watchdog.py) judges each live run from this
# runtime and writes nothing under any run's log root. WATCHER_RUNTIME names
# every function it may call; the watcher refuses a helper that lacks one of
# those it does call (its own RUNTIME_NAMES, a subset of this tuple).
#
# D13's two predicates, which are not the same thing. ACTIVITY is any
# composer-written record: `Wake:`, `WATCH:`, `CONSUME:`, `CLASSIFY:`,
# `ADOPT:`, `NOTIFY:`, and an `OWNERSHIP:` record of a composer-only subtype.
# ADVANCEMENT is what shows the run moved: a leg consumed (`CONSUME:` other
# than the idle checkpoint), a new leg started (`ROLE: start`), a disposition
# (auto- or gate-), a stop opened or answered (must-pause, hold, their
# dispositions), a commit, a release act's start or outcome (dispositions
# too), a close (run-close). Entering the wake path — a `Wake:` line, a watch
# armed, the idle checkpoint, a notice — is activity and never advancement.
# Every advancement line also counts as activity. File times and transcript
# times are neither. Records carry no writer key, so a line a role wrote in
# one of these shapes is read like the composer's: it can only make a run
# look busier, which is the side on which the watcher does nothing.
WATCH_ACTIVITY_PREFIXES = ("Wake:", "WATCH:", "CONSUME:", "CLASSIFY:", "ADOPT:", "NOTIFY:")
WATCH_ADVANCE_SUBTYPES = ("auto-disposition", "gate-disposition", "must-pause", "hold", "commit", "run-close")
WATCH_LOG_CAP = 64 << 20         # a stage log larger than this is a problem, never a partial read
AWAY_TAKEOVER_LABEL = "Watcher takeover:"
AWAY_TAKEOVER_WORDS = ("on", "off")


def watch_line_class(raw):
    """One stage-log line as D13 reads it: `advancement`, `activity`, or None
    (a role's or a tool's line — MONITOR, VERIFY_OK, ROLE: end, EXIT — and
    anything else)."""
    if raw.startswith("CONSUME:"):
        return "activity" if parse_kv(raw)[0].get("source") == "idle-reentry" else "advancement"
    if raw.startswith("ROLE: start "):
        return "advancement"
    if raw.startswith("OWNERSHIP:"):
        _kv, bare = parse_kv(raw[len("OWNERSHIP:"):])
        sub = bare[0] if bare else ""
        if sub in WATCH_ADVANCE_SUBTYPES:
            return "advancement"
        return "activity" if sub in COMPOSER_ONLY_SUBTYPES else None
    return "activity" if raw.startswith(WATCH_ACTIVITY_PREFIXES) else None


def watch_line_time(raw):
    """The line's own write time — a valid `logged_ts=`, else a valid `ts=`
    (the idle clock's rule; an impossible-future stamp is no time) — or None:
    a canonical `Wake:` line carries no clock."""
    kv = parse_kv(raw)[0]
    t = parse_iso(kv.get("logged_ts"))
    if t is None or future_instant(t):
        t = parse_iso(kv.get("ts"))
    return None if t is None or future_instant(t) else t


def watch_read(log_root):
    """Every line of every `stage-<N>-probe.log` directly under the log root,
    stage-ordered then in append order: `(records, lengths, problems)` —
    records `[(log name, end offset in bytes, text)]`, lengths `{log name:
    bytes read}`, problems naming every input that could not be read (the
    watcher never calls a run stalled on evidence it could not read). A line
    with no terminator yet — a write in progress — is not a record and is not
    counted in its log's length."""
    logs, problems = _away_probe_log_names(log_root)
    records, lengths = [], {}
    for _num, name in logs:
        try:
            data = _away_read_bytes(os.path.join(log_root, name), cap=WATCH_LOG_CAP)
        except OSError as e:
            problems.append("probe log %s could not be read (%s)" % (name, e))
            continue
        end = 0
        for piece in data.split(b"\n")[:-1]:
            end += len(piece) + 1
            records.append((name, end, (piece[:-1] if piece.endswith(b"\r") else piece).decode("utf-8", "replace")))
        lengths[name] = end
    return records, lengths, problems


def _watch_any(records, word, since, base):
    for name, end, raw in records:
        cls = watch_line_class(raw)
        if cls is None or (word == "advancement" and cls != "advancement"):
            continue
        if base is not None and end > base.get(name, 0):
            return True
        if since is not None:
            t = watch_line_time(raw)
            if t is not None and t >= since:
                return True
    return False


def run_activity(records, since=None, base=None):
    """D13's ACTIVITY predicate over watch_read's records: is there a
    composer-written record that is NEW — written at or after `since` (an
    aware datetime, by the line's own clock), or lying beyond `base` (a
    `{log name: length}` sample taken earlier; a log the sample does not name
    counts whole)? Either test may be None; with both, either one suffices. A
    clock-less line (`Wake:`) is found by `base` alone."""
    return _watch_any(records, "activity", since, base)


def run_advancement(records, since=None, base=None):
    """D13's ADVANCEMENT predicate — the same two tests over the records that
    show the run moved (the block comment above lists them)."""
    return _watch_any(records, "advancement", since, base)


def run_open_stops(log_root, iso):
    """Is the run parked: `(stops, problems)`. stops: one text per open stop —
    an open must-pause in any stage log, by must_pause_fold exactly as the
    notice dedupe and the away report read it, and an open hold, by
    away_hold_fold as it is. problems: what could not be read (a hold count
    of `unknown` included) — never an empty answer."""
    records, problems = _away_probe_records(log_root)
    stops = ["must-pause %s %s" % pair for pair in sorted(must_pause_fold(records))]
    count, opens, _clears, hold_problems = away_hold_fold(log_root, iso)
    if count is None:
        problems = problems + ["holds unknown: " + "; ".join(hold_problems)]
    else:
        stops += ["hold %s %s" % (hid, cls) for hid, cls, _path, _kv, _loc in opens]
    return stops, problems


def away_takeover_word(data):
    """D19's one rule for the departure file's `Watcher takeover:` lines:
    `on` only when at least one such line exists outside a fenced block and
    EVERY one says `on`; `off` when any says `off` or there is none; and
    `malformed` when any line of the kind says neither word — a malformed
    line is never read as the kind's absence, and it never reads `on`. The
    result does not depend on line order."""
    words = [rest.strip() for _n, rest in away_departure_lines(data, AWAY_TAKEOVER_LABEL)]
    if any(w not in AWAY_TAKEOVER_WORDS for w in words):
        return "malformed"
    return "on" if words and all(w == "on" for w in words) else "off"


def watch_away(pol, iso, plan, log_root):
    """The run's away state as the watcher needs it, through the one state
    function: a dict —
      state      absent | bound | ended | malformed | wrong-identity | unreadable
      grant      the bound grant's number (bound only), else None
      check      its config_hash (bound only), else None
      takeover   on | off | malformed — the bound grant's departure file, read
                 only when its bytes digest to the grant's departure= (the
                 hash test the listing check makes); `mismatch` when they do
                 not or the file cannot be read; None when no grant is bound
      release    [(key, log name, line)] — release acts with a start and no
                 outcome, over EVERY grant of the policy log (away_release_open
                 as `away end` reads it)
      problems   every input that could not be read"""
    out = {"state": "unreadable", "grant": None, "check": None, "takeover": None, "release": [], "problems": []}
    lines, err = _away_read_policy(pol)
    if lines is None:
        out["problems"].append("policy log unreadable: %s" % err)
        return out
    st = away_state(lines, iso, plan)
    out["state"] = st["state"]
    for g in st["grants"]:
        acts, problems = away_release_open(log_root, st["grants"], g)
        out["problems"] += [p for p in problems if p not in out["problems"]]
        out["release"] += [(kv.get("key", "?"), loc[0], loc[1]) for kv, loc in acts]
    g = st["open"] if st["state"] == "bound" else None
    if g is not None:
        out["grant"], out["check"] = g["n"], g["kv"]["config_hash"]
        try:
            dep = _away_read_bytes(_away_departure_path(log_root, g["n"]))
        except OSError:
            dep = None
        if dep is None or hashlib.sha256(dep).hexdigest()[:12] != g["kv"]["departure"]:
            out["takeover"] = "mismatch"
        else:
            out["takeover"] = away_takeover_word(dep)
    return out


def signal_authority(kind, pid, token, pgid=None):
    """THE one rule for signalling a number that was read from a file (round
    49 PR-HIGH-005 / PR-HIGH-006): is the process (`kind="pid"`) or the
    process group (`kind="group"`: `pid` its leader, `pgid` its number) that
    the record names still the one that is there NOW? `live`, `over` or
    `unknown`; only `live` authorises a signal, and the caller asks
    immediately before each one.
      - A record with no start token authorises nothing: `unknown`. A lock
        being held, a leg's aggregate word, or another process of the same
        record being alive says nothing about THIS target.
      - A process: `live` when it runs under the recorded token; `over` when
        the pid is gone or belongs to another process.
      - A group: its OWN rule (_group_authority; round 53 PR-MED-035), NOT
        the liveness reader's — `live` only when the group's leader runs
        under the recorded token; `over` when the leader's number now
        belongs to another process, or the leader is gone and the group is
        empty; `unknown` when the leader is gone and a process remains in
        the group, and for a group that is not its leader's own pid.
    PRESENCE IS ENOUGH TO REFUSE AND NEVER ENOUGH TO SIGNAL. _role_over is
    right to call a group `live` while a process remains in it — a takeover
    and a close are refused on that — but with the leader gone there is no
    process to compare the recorded token with, and the group of that number
    may be the role's own orphans or another group that took the number and
    lost its own leader. As first written this function returned _role_over's
    word, and so signalled such a group on its presence alone.
    What no rule of this kind reaches is the instant between this read and
    the signal — the floor under every signal sent by number."""
    if not token or token == "unknown" or not isinstance(pid, int) or isinstance(pid, bool) or pid <= 1:
        return "unknown"
    try:
        if kind == "pid":
            return {"live": "live", "dead": "over"}.get(proc_alive(pid, token), "unknown")
        if kind == "group" and isinstance(pgid, int) and not isinstance(pgid, bool):
            return _group_authority(pid, token, pgid)
    except Exception:
        pass
    return "unknown"


def _group_authority(leader, token, pgid):
    """May the process group `pgid`, recorded with its leader's pid and start
    token, be SIGNALLED? `live` at ONE place: its leader runs under the
    recorded token. A leader running under another token is `over` — a pid is
    not handed out again while a group of that number has a member, so the
    recorded group is empty. A leader that is gone: `over` when the group is
    empty; `unknown` when a process remains in it (it cannot be tied to the
    record), and when the group cannot be tested. The caller has already
    refused a record with no token."""
    if pgid != leader:
        return "unknown"
    state, current = proc_start_token(leader)
    if state == "alive":
        return "live" if current == token else "over"
    if state != "gone":
        return "unknown"
    members = group_any(pgid)
    if members is None or members:
        return "unknown"
    return "over"


def leg_signal_targets(log_root, entry):
    """For the stop command: the EVIDENCE for each thing a leg's record lets
    a caller signal, from ONE read of the file the run_legs entry names —
    `{"wrapper": (pid, start token), "group": (role pid, role start token,
    role pgid)}`, a member None where the file does not record it — or None
    when the file no longer is that entry's record (gone, unreadable, or
    naming another run, leg or wrapper: a leg file replaced between the
    verdict and the signal authorises nothing). The decision is
    signal_authority's, per target, at the moment of the signal; a
    pre-release identity record carries no token, so it authorises none."""
    kv = _leg_read(log_root, entry.get("file", ""))
    if (kv is None or kv.get("leg") != entry.get("leg") or kv.get("run", "") != entry.get("run")
            or _leg_int(kv, "wrapper_pid") != entry.get("wrapper_pid")):
        return None
    if entry.get("source") == "identity":
        return {"wrapper": (_leg_int(kv, "wrapper_pid"), None), "group": (_leg_int(kv, "claude_pid") or None, None, _leg_int(kv, "claude_pid") or None)}
    return {"wrapper": (_leg_int(kv, "wrapper_pid"), kv.get("wrapper_start")),
            "group": (_leg_int(kv, "role_pid"), kv.get("role_start"), _leg_int(kv, "role_pgid"))}


def watch_runs(base):
    """Every run the base's loops directory names by a journal or a marker:
    `(runs, problem)` — `problem` is set when the directory itself could not
    be listed (no run is then reported: an unlistable directory is never "no
    live run"). Each run is a dict:
      iso           the run's iso-id
      journal       its first `state=` token, or none | unreadable | unrecognized.
                    `unreadable` is a journal that could not be read OR whose
                    content cannot be used: a `log_root=` that is there and
                    is empty, fails the value check, is not an absolute path
                    or is refused by the host's path rules (journal_log_root
                    — round 72 PR-MED-039), or no state and no `log_root=`
                    at all (an empty file, one cut short — round 71
                    PR-MED-038). `unrecognized` is left for a journal with
                    no state token that DOES name a usable `log_root=`
      marker        live | retired | none | unreadable (the census's rule: live
                    is an `<iso>-active` file with no `.complete-*` sibling
                    whose body names the same iso)
      plan          the journal's plan= identity string, or None
      worktree      the journal's worktree= value, or None
      log_root      the journal's absolute log_root=, else <loops>/<iso>
      default_root  a journal that was READ establishes that folder as
                    `<loops>/<iso>` — where the seat's files sit beside it (no
                    other layout is ever taken over). False for a run with no
                    journal (a run with no run worktree: its logs are in the
                    flat loops root) and for one whose journal is
                    `unreadable`: there `<loops>/<iso>` is only the default
      closed        the run is not live: no live marker, or a terminal journal
                    state (cleaned, retained-green, paused,
                    crashed/recovery-needed, merge-failed)
    Every file is read no-follow and capped; a journal value that fails the
    writer's value check is dropped, never used."""
    loops = os.path.join(base, ".cursor", "loops")
    try:
        names = sorted(os.listdir(loops))
    except FileNotFoundError:
        return [], None
    except OSError as e:
        return [], "the loops directory %s could not be listed (%s)" % (loops, e)
    isos = set()
    for nm in names:
        for suffix in ("-isolation", "-active"):
            if nm.endswith(suffix) and ISO_ID_RE.match(nm[:-len(suffix)]):
                isos.add(nm[:-len(suffix)])
    runs = []
    for iso in sorted(isos):
        run = {"iso": iso, "journal": "none", "marker": "none", "plan": None, "worktree": None,
               "log_root": os.path.join(loops, iso), "default_root": True}
        jkv = None
        try:
            jdata = _away_read_bytes(os.path.join(loops, iso + "-isolation"), follow=False, cap=AWAY_CENSUS_CAP)
            jkv = _rc_parse_kv_lines(jdata.decode("utf-8").splitlines())[0]
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            run["journal"] = "unreadable"
        if jkv is not None:
            st_tok = jkv.get("state")
            run["journal"] = st_tok if st_tok is not None and _PRIOR_STATE_RE.match(st_tok) else "unrecognized"
            safe = dict((k, jkv[k]) for k in ("plan", "worktree")
                        if jkv.get(k) and reason_of(check_value_safety, k, jkv[k]) is None)
            run["plan"] = safe["plan"] if safe.get("plan", "").strip() else None
            run["worktree"] = safe["worktree"] if os.path.isabs(safe.get("worktree", "")) else None
            # WHERE THE RUN'S LEGS ARE — one reading, journal_log_root, shared with the close's guard (round 72
            # PR-MED-039). Three answers and no fourth:
            #   unusable  a `log_root=` that is THERE and cannot be used — empty, a value that fails the value check, a
            #             path that is not absolute, a spelling the host refuses (round 66 LOW-004: that is this ONE
            #             run's journal, never the end of the whole listing). The journal is `unreadable`: a log root
            #             that cannot be followed is never guessed around. Before round 72 a value that passed the
            #             check and was merely RELATIVE fell through beside a state token and kept the default folder
            #             as established — `stop` said `done`, `identity` made a seat.
            #   named     the folder is the one the journal names; the seat is beside it only when that IS the default.
            #   default   no `log_root=` key at all: the documented fallback — unless the journal has no state either
            #             (round 71 PR-MED-038: a journal that says nothing establishes nothing — an empty file, one
            #             cut short ahead of its `state=`), which is `unreadable` too.
            root, how = journal_log_root(jkv, run["log_root"])
            if how == "unusable":
                run["journal"] = "unreadable"
            elif how == "named":
                run["log_root"] = root
                run["default_root"] = canon_path(root) == canon_path(os.path.join(loops, iso))
            elif run["journal"] == "unrecognized":
                run["journal"] = "unreadable"
        if run["journal"] in ("none", "unreadable"):
            # the log folder is ESTABLISHED only by a journal that was read (round 66 LOW-003): a run with no journal — a
            # run with no run worktree keeps its logs in the flat loops root — and one whose journal cannot be read keep
            # `<loops>/<iso>` as a default nobody established, so no seat is created beside it and it is never taken over
            run["default_root"] = False
        if any(n.startswith("%s-active.complete-" % iso) for n in names):
            run["marker"] = "retired"
        else:
            try:
                mdata = _away_read_bytes(os.path.join(loops, iso + "-active"), follow=False, cap=AWAY_CENSUS_CAP)
                mkv = _rc_parse_kv_lines(mdata.decode("utf-8").splitlines())[0]
                run["marker"] = "live" if mkv.get("iso") == iso else "unreadable"
            except FileNotFoundError:
                pass
            except (OSError, ValueError):
                run["marker"] = "unreadable"
        run["closed"] = run["marker"] in ("none", "retired") or run["journal"] in _TERMINAL_STATES
        runs.append(run)
    return runs, None


WATCHER_RUNTIME = (
    "watch_runs", "run_legs", "leg_signal_targets", "signal_authority", "proc_alive", "proc_start_token", "group_any",
    "watch_read", "watch_line_class", "watch_line_time", "run_activity", "run_advancement",
    "run_open_stops", "must_pause_fold", "away_hold_fold", "away_release_open", "watch_away", "away_takeover_word",
    "seat_supported", "seat_paths", "seat_state", "seat_gate_take", "seat_gate_release", "seat_admit",
    "fire_notice", "now_iso", "parse_iso", "canon_path", "path_inside", "_configure_std_streams",
)


# PR-MED-001 (round 8): TOTAL per-subcommand argv grammar — every accepted
# token changes behaviour exactly as its documented subcommand says; an
# irrelevant flag/root/token REFUSES rather than silently disappearing (a
# `--dry-run`-labelled invocation never reaches a mutating subcommand).
# v46.4 (D2): at module level — it sat inside main() through v46.3 — so the
# help text and the unknown-flag hint are generated from the table main()
# applies; no entry changed in the move.
SUB_GRAMMAR = {
    # v33.0: --read-log (D3 — the keyed ROLE:start's read-only prior-record
    # source; type-scoped inside cmd_emit) and --liveness (D5 — the
    # must-pause re-fire dedupe window; type-scoped inside cmd_emit).
    # v34.1 D10: --allow-repeat-hash (the repeated-commit-hash override;
    # type-scoped inside cmd_emit).
    # v47.0 (D4): --policy-log / --iso / --plan — the listing check's three
    # flags; type-scoped inside cmd_emit to an away `merge` `choice=start`,
    # where they are required.
    "emit":         {"flags": {"--run", "--role", "--log", "--epoch", "--event-ts",
                               "--round", "--id", "--repo", "--read-log", "--liveness",
                               "--allow-repeat-hash", "--policy-log", "--iso", "--plan"},
                     "roots": False, "kvs": True, "dry_run": False},
    # v33.0 D4: --edit-surface / --allow-path / --iso / --liveness — the
    # edit-surface-aware verdict + the liveness-gated base-dirt attribution.
    "escape-check": {"flags": {"--run", "--role", "--log", "--log-root",
                               "--capture", "--leg", "--edit-surface",
                               "--allow-path", "--iso", "--liveness"},
                     "roots": True, "kvs": False, "dry_run": False},
    "flush":        {"flags": {"--run", "--role", "--log", "--epoch"},
                     "roots": False, "kvs": False, "dry_run": True},
    "idle-check":   {"flags": {"--run", "--role", "--log", "--log-root"},
                     "roots": False, "kvs": False, "dry_run": False},
    # v33.2 (/close-run T1.1): --merge-commit — the squash-aware merged
    # close's ENTRY flag (D10/D11); outcome-scoped inside cmd_run_close.
    # v44.0 (D4): --grant / --away-check — the re-baseline trio on the group
    # close; both-or-none, outcome- and stage-log-scoped inside cmd_run_close.
    "run-close":    {"flags": {"--run", "--role", "--log", "--iso", "--base",
                               "--outcome", "--plan", "--attest", "--merge-commit",
                               "--grant", "--away-check"},
                     "roots": False, "kvs": False, "dry_run": False},
    # v32.2 T2.3: no --log — the receipts sidecar + retirement ARE the
    # durable evidence; the fold writes no probe-log record.
    "fold-delegation": {"flags": {"--run", "--role", "--base", "--iso", "--leg"},
                        "roots": False, "kvs": False, "dry_run": False},
    # v33.0 D12: the read-only identity-bound attestation read — no --log
    # (it writes nothing), --iso/--plan REQUIRED, --key optional.
    "attest-check": {"flags": {"--run", "--role", "--policy-log", "--iso", "--plan", "--key"},
                     "roots": False, "kvs": False, "dry_run": False},
    # v34.0 D4: the away grant — the per-VERB grammar (required flags,
    # --log-root / --out placement, the admitted kv keys) is
    # AWAY_VERB_GRAMMAR, applied inside cmd_away.
    # v35.1 (Decision 2): --base — `away ci-verdict`'s gh working directory.
    "away":         {"flags": {"--run", "--role", "--policy-log", "--iso", "--plan",
                               "--log-root", "--out", "--base"},
                     "roots": False, "kvs": True, "dry_run": False},
    # v47.0 (T1.4 / D7, D9): the read-only records-path reader — no --log (it
    # writes nothing), no identity flags, no key=value. Placed BEFORE
    # quoted-block, which stays the table's (and so the usage hint's) last
    # entry — two selftest pins read that position.
    "records-delta": {"flags": {"--run", "--role", "--worktree", "--base-ref", "--tip", "--range",
                                "--alphabet", "--also", "--departure"},
                      "roots": False, "kvs": False, "dry_run": False},
    # v40.0 Phase 0 (D8): the read-only block comparison — no --log (it
    # writes nothing), no identity flags; --base is the git checkout the
    # two sides are read from. v42.0 (D1): --log-root (with the TWO
    # admitted keys grant=<n> away_check=<hash> — kvs flipped on;
    # cmd_quoted_block refuses every other key) folds the grant's
    # set-refresh records bound to that grant identity; --baseline
    # joins the accepted set; --heading is optional (blob mode).
    "quoted-block": {"flags": {"--run", "--role", "--base", "--file", "--heading",
                               "--from", "--to", "--baseline", "--log-root"},
                     "roots": False, "kvs": True, "dry_run": False},
}

# v46.4 (plan-loop-field-review-fixes D2): `--help` / `-h`. The usage text and
# the unknown-flag refusal's EXPECTED: line are GENERATED from the tables the
# parser applies — SUB_GRAMMAR, AWAY_VERB_GRAMMAR and the emit type table — so
# each has one owner: a flag, verb, key or type added to a table is in both
# with no second edit. parse_argv's pre-pass decides when the text prints.
HELP_FLAGS = ("--help", "-h")
_HELP_CMD = "python3 scripts/loop-journal.py"


def _grammar_words(g):
    """One SUB_GRAMMAR entry as usage words: its flags beyond the global
    --run / --role pair, sorted, then the token kinds it admits (`--root`,
    `--dry-run`, `key=value`)."""
    words = sorted(g["flags"] - {"--run", "--role"})
    if g["roots"]:
        words.append("--root")
    if g["dry_run"]:
        words.append("--dry-run")
    if g["kvs"]:
        words.append("key=value")
    return words


def usage_hint():
    """The unknown-flag refusal's EXPECTED: line — every subcommand with what
    it accepts, in SUB_GRAMMAR's order."""
    return ("every subcommand: --run --role; "
            + "; ".join("%s: %s" % (sub, " ".join(_grammar_words(g))) for sub, g in SUB_GRAMMAR.items())
            + "; --help | -h prints the usage")


def emit_type_names():
    """Every TYPE `emit` accepts, in the order the `emit needs a TYPE` refusal
    lists them: the EMIT_SPECS names, the OWNERSHIP subtypes `emit` itself
    writes (a subtype a dedicated subcommand computes is absent), NOTIFY."""
    return (sorted(EMIT_SPECS)
            + sorted("OWNERSHIP:" + s for s in V_OWNERSHIP_SUBTYPES - {"escape-check"} - set(AWAY_RECORD_SUBTYPES) - set(TOOL_ONLY_SUBTYPES))
            + ["NOTIFY:<state>"])


def away_verb_usage(verb):
    """`away <verb>` as ONE line generated from AWAY_VERB_GRAMMAR: the global
    pair, the verb's required flags in table order and its required keys
    (`<key>=`), then the optional flags and keys in brackets. It is the help
    text's verb line."""
    g = AWAY_VERB_GRAMMAR[verb]
    req = list(g["required"]) + ["%s=" % k for k in g["kvs_required"]]
    opt = sorted(g["flags"] - set(g["required"])) + ["%s=" % k for k in sorted(g["kvs"] - set(g["kvs_required"]))]
    return "away %s --run --role %s%s" % (verb, " ".join(req), " [%s]" % " ".join(opt) if opt else "")


def help_text(sub=None):
    """v46.4 (D2) — what `--help` / `-h` prints: the overall usage, or one
    subcommand's when `sub` names one (for `away` each verb's line, for `emit`
    the TYPEs). Which flags a subcommand REQUIRES is in a table only for
    `away`'s verbs, so only they are printed as required; every other
    subcommand's own refusal names what it needs."""
    verbs = ["verbs — required flags and keys first, optional ones in brackets:"] + ["  " + away_verb_usage(v) for v in AWAY_VERBS]
    if sub == "away":
        lines = ["usage: %s --run <runkey> --role composer away <verb> [flags] [key=value ...]" % _HELP_CMD] + verbs
    elif sub in SUB_GRAMMAR:
        lines = ["usage: %s --run <runkey> --role <role> %s%s [flags]" % (_HELP_CMD, sub, " <TYPE>" if sub == "emit" else ""),
                 "accepts beyond --run / --role: %s" % " ".join(_grammar_words(SUB_GRAMMAR[sub]))]
        if sub == "emit":
            lines += ["TYPEs:"] + ["  " + t for t in emit_type_names()]
    else:
        lines = (["usage: %s --run <runkey> --role <role> <subcommand> [flags] [key=value ...]" % _HELP_CMD,
                  "       %s [<subcommand>] --help" % _HELP_CMD,
                  "--run (stage-<N>) and --role (%s) are REQUIRED on every subcommand." % " | ".join(sorted(ENUMS["ROLE_ENUM"])),
                  "subcommands — what each accepts beyond that pair:"]
                 + ["  %s: %s" % (s, " ".join(_grammar_words(g))) for s, g in SUB_GRAMMAR.items()]
                 + ["away " + verbs[0]] + verbs[1:]
                 + ["`<subcommand> --help` prints one subcommand; `emit --help` lists the TYPEs."])
    lines.append("--help / -h reads no log and writes nothing.")
    return "".join(l + "\n" for l in lines)


def main(argv):
    _configure_std_streams()
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
    # v46.0 (D5): `run-bounded` is REFUSED by NAME — the bounded runner is
    # scripts/loop-run-bounded.py, and nothing after the name is run or read.
    # The match stays ahead of parse_argv and the identity check below, so
    # the refusal names the new script with or without a --run / --role pair
    # before the name, never asking for the pair first.
    _i = 0
    while _i + 1 < len(argv) and argv[_i] in ("--run", "--role"):
        _i += 2
    if _i < len(argv) and argv[_i] == "run-bounded":
        refuse("run-bounded is not a subcommand of this helper — the bounded runner is scripts/loop-run-bounded.py (v46.0); nothing was run",
               "python3 scripts/loop-run-bounded.py [--run <runkey> --role <role>] --timeout <s> [--kill-after <s>] [--cwd </abs/dir>] -- <cmd> [args...]")
    sub, etype, flags, roots, kvs, dry_run = parse_argv(argv)
    if sub is None:
        refuse("no subcommand", "emit | escape-check | flush | idle-check | run-close | fold-delegation | attest-check | away | records-delta | quoted-block")
    if sub not in ("emit", "escape-check", "flush", "idle-check", "run-close", "fold-delegation", "attest-check", "away", "records-delta", "quoted-block"):
        refuse("unknown subcommand %r" % sub, "emit | escape-check | flush | idle-check | run-close | fold-delegation | attest-check | away | records-delta | quoted-block (exactly ten)")
    # v46.4 (D3): both flags of the pair named in ONE refusal (one missing:
    # the text is the earlier one)
    missing = [req for req in ("--run", "--role") if req not in flags]
    if missing:
        refuse("%s %s REQUIRED on every subcommand" % (" and ".join(missing), "is" if len(missing) == 1 else "are"),
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
    # PR-MED-001 (round 8): the TOTAL per-subcommand argv grammar — SUB_GRAMMAR,
    # at module level from v46.4 — applied here, unchanged.
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

    if "--read-log" in flags:
        # v33.0 D3 (PR-MED-003): --read-log is a READ-ONLY prior-record source
        # and NEVER the sink — the wrapper keeps its retained-descriptor write
        # (>&8), so the ROLE: start still lands exactly once. Absolute, and
        # never beside --log (one prior-record source per invocation).
        if not os.path.isabs(flags["--read-log"]):
            refuse("--read-log must be an absolute path")
        if "--log" in flags:
            refuse("--read-log and --log together are ambiguous — --log already IS the prior-record source (and the sink); pass exactly one")
    sink = open_sink(flags)
    # v48.0 (D12): THE seat admission — one call site for every composer-owned
    # write (seat_class reads the ownership tables; seat_where finds the run).
    # The gate is taken here and held through the subcommand's own read,
    # decision and write: the `finally` below releases it only after them, on
    # every way out (a refusal's or an environment failure's exit included).
    gate = None
    if seat_class(sub, etype, flags["--role"], dry_run) == "gated":
        where = seat_where(sub, flags)
        if where is not None:
            gate, why = seat_admit(where[0], where[1])
            if why is not None:
                refuse(why)
    try:
        _dispatch(sub, etype, flags, roots, kvs, dry_run, sink)
    finally:
        seat_gate_release(gate)
    return 0


def _dispatch(sub, etype, flags, roots, kvs, dry_run, sink):
    """main()'s dispatch, one subcommand function per name — a function of
    its own from v48.0 so that main() can hold the seat's gate around it (the
    chain itself is unchanged; main() has already refused an unknown name)."""
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
    elif sub == "attest-check":
        cmd_attest_check(flags)
    elif sub == "away":
        cmd_away(flags, etype, kvs)
    elif sub == "quoted-block":
        cmd_quoted_block(flags, kvs)
    elif sub == "records-delta":
        cmd_records_delta(flags)
    else:
        cmd_idle_check(flags, sink)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
