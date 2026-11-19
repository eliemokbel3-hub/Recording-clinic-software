# Feature Implementation Plan
**Feature:** show-the-doubt
**Overall Progress:** `8%` (2 of 26 tasks)

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: None. Seeded by `plan-follow-on-lines.md` (Retained Follow-Up Items, "Plan 2, the low-confidence mark's reach") and `plan-validation-run8.md` (Follow-Up Continuation Notes 1; Retained item 1, "the distinct mark for a low-confidence number").
- Follow-up plans: None

## Goal
Make the note body show the recogniser's doubt: a visible mark on a quoted note line that holds a low-confidence word, where today the line shows nothing. Measure, without building, whether a dropped word can be flagged. End with a written options brief on the exit gate. Shadow mode stays on; no gate claim is made.

## Planning Extraction Summary

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Fable 5.2; executor `claude-opus-5-5` high, peer codex `gpt-6.2-astra` medium (the practitioner's "Entirely premium (Recommended)", 2026-11-20); tier-gap dosing applied (design decisions, the mark's contract, the bars and the measurement definitions are fixed here).

### Agreed Scope (Build Now)
- A confirming sweep of the low-confidence threshold and the mark's reach over the saved synthetic traces (scratch only, minutes).
- A measurement of dropped-word signals: ground truth from the traces, trace-level signals, and (conditionally) timing and decode signals from one re-transcription. Reported, never built here (D5).
- A numbers-only real-speech run by the practitioner giving the new mark's review load (D6).
- If bar B is met and the practitioner chooses it at Task 2.4: the visible line mark `[check: unclear word]` (D3), its tests, documents, version, build of record and install with shadow mode on.
- On every exit: the measurement's records in the documents (Task 2.3), a hardening pass (Step H) and the exit-gate options brief (Task 5.1).

### Deferred — Actionable Later
- A dropped-word mark in the product.
  - Why deferred: the practitioner's "Mark only; measure dropped words (Recommended)" (2026-11-20). Its false alarms on real speech cannot be measured, only its load; two of its three seed rows sit on segments the note does not quote; two new marks in one build could not be told apart on the first clinic days.
  - Intended future outcome: a flagged line or segment where the recogniser probably dropped a word, at a review load the practitioner accepts.
  - Relevant files / subsystems: `note.line_marks`, Check 1 (`note_check.reconstruction_warnings`), `ui/models.py` flag sources, `validation.py` (`warned` is set only on an aligned word).
  - Dependencies / prerequisites: this plan's Tasks 0.4 and 1.3 tables; a new per-line review code (so stored bytes and a rollback section); constants treated as the invented-text guard's C2 treats its own.
  - Recommended next action: an amendment to this plan hardened by a scoped `/review-plan`, or its own plan, on the practitioner's word after Task 2.4.
  - Risk if deferred: correctness: a dropped word in a quoted line carries no mark (register F-149).
  - Revisit by: Task 2.4's tables showing a signal that meets D5's reporting threshold on the confirmation half.
- A stricter threshold for the line mark (0.50, 0.40 or 0.30) or any change to `UNCERTAINTY_THRESHOLD`.
  - Why deferred: a mark threshold other than 0.60 cannot be rendered from the existing per-word warnings (D3), and one constant feeds the transcript's `[word?]`, Check 1 and Check 2's grading.
  - Intended future outcome: a mark rare enough to carry information if the load at 0.60 fails bar B.
  - Relevant files / subsystems: `transcription.py:271`, `note_check.py:643` and `:1325`, `note.line_marks`.
  - Dependencies / prerequisites: the fallback load columns of Task 0.3 and the per-threshold verdict words of Task 2.2; the guard measurement repeated if `UNCERTAINTY_THRESHOLD` itself moves (Local Run Steps step 14).
  - Recommended next action: an amendment hardened by a scoped `/review-plan`.
  - Risk if deferred: ux-degradation: with bar B failed, the note keeps showing no mark for a doubted word.
  - Revisit by: bar B (ii) failing at Task 2.4 with a lower threshold's load verdict met.
- Line-wide harness credit for the low-confidence mark, and any spelling or word-form fold in the measurement.
  - Why deferred: each is a metric amendment that needs a new rule version, a fresh blind set and pre-registration (D4, D7).
  - Intended future outcome: decided from the options brief (Task 5.1), never here.
  - Relevant files / subsystems: `validation.REVIEW_MARK_CODES`, the harness's canonical spelling, `validation/rules/`.
  - Dependencies / prerequisites: the brief; the practitioner's choice of route.
  - Recommended next action: none in this plan.
  - Risk if deferred: minor: the measurement stays as strict as it is.
  - Revisit by: the practitioner's reading of the brief.

### Excluded — Revisit Only If Needed
- Any change to the `GUARD_*` constants, the primer, the recogniser, the cue file, the frozen vocabularies, the rule files, the held-out sets, the suggestion stage or the routing.
  - Why excluded: frozen things; the seed reading shows none of them is this plan's lever.
  - When to revisit: a new dated decision with its own measurement.
  - Relevant files / subsystems: `transcription.py`, `consultation_phrases.py`, `validation/`.
  - Recommended next action (if any): none.
- Decode-number signals (average log-probability, compression ratio) as a product signal.
  - Why excluded: they need a stored transcript field, which older builds refuse (the `suspect` precedent). They are measured on synthetic audio only and never on real data.
  - When to revisit: a dropped-word amendment that finds no stored-field-free signal.
  - Relevant files / subsystems: `speech.TranscribedWord`, `transcription.mark_segment_words`.
  - Recommended next action (if any): none.

### Accepted Assumptions — Revalidate Later
- Word probabilities from the installed SAPI voices are not representative of real speech.
  - Why accepted for now: the synthetic sets are the only ground truth; real speech gives load only (D6).
  - Risk if assumption becomes false: none; it is the reason the real-speech bar exists.
  - Trigger for revisit: the first clinic days on a build with the mark.
  - Recommended next action: watch the mark's load beside F-088's count.
- Two kept recordings with a confirmed clinician are enough to read the mark's real-speech load.
  - Why accepted for now: the practitioner's "2 is enough for this mark (Recommended)" (2026-11-20). The mark is review apparatus in shadow mode and rolls back with no data step.
  - Risk if assumption becomes false: the load on other consultations is heavier than measured (alarm fatigue).
  - Trigger for revisit: the first clinic days; a third kept recording.
  - Recommended next action: the practitioner may re-run Task 2.2's script when a third recording exists, for their own reading only: its block is not relayed or recorded (Task 2.2's rule).

### Key Design Decisions
- D1 to D9 under "Design Decisions". All still apply to follow-up work: Yes.

## Key Findings

### What planning already read (declared; none of it is a prediction or a test)
From `.cursor/loops/ffl-out/` (synthetic, take 1, gate configuration, transcribed at `60cd138`; `git diff --stat` over `desktop/src`, `validation`, `scripts` and `extension` between `b8dac3d` (0.4.0), `60cd138` and HEAD is empty):
- **Premise, run during planning:** a transcript rebuilt from each saved trace, with the pickled gate note (`baseline/<take>/<set>/<id>.pickle`, `notes[-1]`) and the tracked script, reproduces the stored Check 1 warnings and the whole stored metrics object on all 227 encounters (183 take 1, 44 take 2): 0 differences, 8.4 s, no model loaded.
- **The seven counted wrong facts with no mark:** `hld-14/f1` "gluts" (0.90), `h6-09/f1` "gripped" (0.95), `h6-13/f1` "slings" (0.95) are confidently wrong; `hld-21/f3` "gluts" (0.77) is marked only from T = 0.80; `h5-17/f0` has its body-part word dropped, and the next word (0.47) already draws `low_confidence_source` outside the fact's words; `h2-15/f9` (0.62) and `h6-14/f5` sit on suggested lines, which the reference reading never holds.
- **Marks cannot clear a seen set:** a newly marked wrong fact becomes R1, and `heldout` and `heldout-5` are already at R1 1 of 1.
- **The four residue rows** (`h3-03/f0`, `h3-13/f2`, `h4-01/f5`, `h4-07/f0`) are already marked; all are renderings of a unit, a number or an abbreviation.
- **The silent seed rows** sit on segments the note does not quote. `h6-15/f5` is a zero-word segment (0.52 s, identical on take 2). `syn-22/f2` is a sparse segment (2 words in 2.73 s) that already carries `high_risk_omission`.
- **Unsurfaced uncertainty:** 17 facts on the three sets that require it, all heard correctly; 13 have a minimum aligned probability of 0.94 or more.
- **Mark load today (183 gate notes, T = 0.60):** 1,153 quoted lines; 229 (19.9%) carry a visible mark; 99 hold a low-confidence word; 54 of those (4.7% of quoted lines) show no visible mark, so 45 already show one. (No per-encounter incidence is recorded here: planning's figure for it could not be re-derived, and Task 0.3 prints it.)
- **Take 1 against take 2 at word level:** `heldout-2` identical on 22 of 22; `heldout-6` differs on 1 of 22 (`h6-16`, one word's text).
- **Still unread:** the load at every T other than 0.60, the share of marked lines that hold an error, the per-note distribution, the whole deletion-run table, every timing and decode signal, every real-speech number.

### Files / Symbols Involved
- `desktop/src/scribe_desktop/transcription.py`: `UNCERTAINTY_THRESHOLD = 0.60` (`:271`); `mark_words` (`:527`, its threshold a default argument bound at definition); `TranscriptWord` (`:360-380`, stores `probability`, `start_seconds`, `end_seconds`, `uncertain`, `suspect`).
- `desktop/src/scribe_desktop/note_check.py`: the import (`:306-307`); `reconstruction_warnings(note, document)` (`:591`); `low_confidence_source`, one review warning per word below the threshold, coordinates that one word (`:642-653`); the per-line loop that inverts `LINE_MARK_CODES` (`:610`, `:656-667`); `contradiction_warnings` (`:1422`) and its grading (`:1320-1333`).
- `desktop/src/scribe_desktop/note.py`: `NOTE_WARNING_SEVERITY` (`:299`); `LINE_MARK_CODES` (`:393`); `check_mark` (`:403`); `line_marks` (`:489-509`); `quoted_line_marks` (`:512-531`, appends the hedge's "unsure" last); `line_marks_by_assertion` (`:1046-1072`, reads only a warning's code and `assertion_id`); `section_marks_line` (`:1227-1250`); the unknown-review-warning reader (`:377-381`, `:790-814`).
- `desktop/src/scribe_desktop/ui/models.py`: `_segment_words` renders `[word?]` from `uncertain` (`:1855-1861`); the warning copy "A quoted line includes a word the transcription was unsure about" (`:2272`); `summarise_warnings` groups by code (`:2445-2472`); `SEPARATELY_ACKNOWLEDGED_CODES` / `_NAMES` (`:2490-2523`); `format_note_body` stores the generated body with check marks (`:2658-2663`); the line editor reads `quoted_line_marks` (`:3411-3434`).
- `desktop/src/scribe_desktop/validation.py`: `_Alignment` (`:1291`, `diagonal` `:1317`, `deletion` `:1323`); `REVIEW_MARK_CODES` (`:1846`); `_marked_words` (`:1851`), called twice only (`:2132` with `{"low_confidence_source"}`, `:2133` with `REVIEW_MARK_CODES`); `_excused_by_r1` (`:1867-1880`); `encounter_metrics(document, note, script, *, reference=None, suggested_segments=frozenset(), reply_credit=True)` (`:1971`); `_compose_note(document, clinician, ...)` (`:3248`).
- `desktop/src/scribe_desktop/replay_kept.py`: `_open_store` (`:206`), `_load_models(model_name, enrolment_wav, device)` (`:230`), the review count (`:363`); `past_sessions.py`: `kept_session_ids` (`:952`), `read_recording` (`:1023`); `speaker_eval.transcribe_in_temporary_store` (`:1066`); `guard_eval._RecordingProvider` (`:453`).
- Scratch, git-ignored, under `.cursor/loops/`: `ffl_lib.py` (frozen, SHA-256 `f7d2d75c4e1dbac9ba91413ee7f42d546fc7fc0575e3ffe0b6aba43314d38d03`), `ffl-measure-kept.py` (frozen, `36e215c5fe92e0734f7161226c99b72b0fd956235c8a8630395ccb8df25f603d`), `afq-transcribe.py` (already saves the whole document, word times included, `:238`), `ffl-out/trace/<set>/` (7 sets), `ffl-out/trace-docs-t2/` (2 sets), `ffl-out/baseline/{docs,docs-t2}/<set>/*.pickle`, `ffl-out/map-7.md`. A trace word is `[text, probability (4 dp), suspect, uncertain]`.

### Codebase Integration Notes
- The harness already credits `low_confidence_source` as a review mark, while the note line shows none: the clinician sees one grouped warning row that "Acknowledge all" clears, and `[word?]` in the transcript panel (which also sits on every number and name-like token, `transcription.py:534`).
- No checker or metric reads per-word times, so a document rebuilt from a trace with invented word times is equivalent for Check 1 and the metrics. A saved note or draft paired with a rebuilt document cannot pass `check_note` (`note_check.py:2123-2129`): `transcript_digest` covers the whole document bytes. A note composed fresh from a rebuilt document and finalised against that same document passes (Task 2.1's bare branch).
- `mark_words` may be referenced only inside `mark_segment_words`, pinned by AST in `test_shadow_exits.py`. This plan does not touch it.
- Line endings: the plans, the findings register and `docs/pilot/` are LF. `AGENTS.md`, `CHANGELOG.md`, `docs/testing/validation-harness.md`, `docs/testing/kept-recordings.md`, `docs/security/threat-model.md` and `docs/security/data-flow-map.md` are CRLF in the working tree; check `git ls-files --eol` for every other document edited.
- Planning-time baselines (2026-11-20, `main` at `ec16c6c`, tree clean): desktop suite 11121 passed, 9 skipped; ruff and mypy clean; extension 313 passed; version fields 0.4.0.

### External / API Findings
N/A.

## Planned Workflow Summary

### Flow 1 — Diagnose from the saved traces
The scratch proves it reproduces the stored result, the bars are frozen in a commit, then the sweep and the deletion-run table are read.

### Flow 2 — One re-transcription (conditional)
On the practitioner's "start now", the seven sets are rebuilt and transcribed once with word times and decode numbers captured; each encounter is matched to its saved trace before any timing signal is scored.

### Flow 3 — Real speech and the exit
The practitioner runs a frozen numbers-only script over the kept recordings and pastes its paste block (status, recording counts and verdict words). The tables go into the documents. The practitioner chooses: build the mark, or close with no change.

### Flow 4 — Build, release, brief
If chosen: the mark, its tests, documents and version; hardening; a build of record; install with shadow mode on. On every exit: hardening and the exit-gate options brief.

## Design Decisions
- **D1 — Scratch only until the exit decision.** New `.cursor/loops/lcm_lib.py`, `lcm-measure.py` and (a separate file for the real-data entry point) `lcm-measure-kept.py`; outputs under `.cursor/loops/lcm-out/`. The `ffl_*` files are frozen method records: import or copy from them, never edit them, and check `ffl_lib.py`'s SHA-256 before importing. No file under `desktop/`, `scripts/`, `validation/` or `extension/` changes before Task 3.2.
  Alternatives considered: a tracked developer tool (rejected: a no-change exit would leave an unused tool in the tree).
- **D2 — The sweep.** In the scratch process only: patch `note_check.UNCERTAINTY_THRESHOLD`, re-run `reconstruction_warnings`, swap the Check 1 warnings into the saved note with `model_copy`, and call the real `encounter_metrics`. Reach is simulated by wrapping `validation._marked_words` for the `REVIEW_MARK_CODES` call only, clipped to the quoted line's coordinates (resolved through the warning's `assertion_id`), so `uncertainty_surfaced` stays word-level. No imported `ffl_lib` cost helper runs under the wrap (`ffl_lib.review_marked_segments` calls `_marked_words` too). Grid: T in 0.30, 0.40, 0.50, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90; reach in word, ±1, ±3, line. Tie rule (a trace stores a probability rounded to 4 dp, and the checker tests strict `<`, `note_check.py:643` and `:1320-1326`): ties are resolved from stored evidence first. At T = 0.60 a word in a quoted line is below the threshold exactly when the stored warnings hold its `low_confidence_source`, and any word whose stored `uncertain` flag is False is not below (`mark_words` sets the flag on every word below the threshold, `transcription.py:532-545`); the parity row is anchored so, never on the rounded value. A word still tied (its 4-dp probability equals T and no stored evidence decides) is undetermined. A count is printed as its two extreme assignments. Every other figure (a share, a median, a maximum, a met or not met) is not monotone in the ties, so it is computed under every assignment of the undetermined words when there are at most 12 of them and printed as its range; with more, or when the range straddles a bar's number, the figure or the bar is reported as indeterminate, never as met. The self-test holds a mixed case (one tied word on a line with a word error, one on a line without). The harm column for a coupled threshold is Check 2 grade changes (`contradiction_warnings` re-run and swapped in) plus a hand count of `[word?]` display marks; `mark_words` is not patched.
  Alternatives considered: re-transcribing for the sweep (rejected: the premise holds at 0 differences without it).
- **D3 — The visible mark, with no new warning code.** `LINE_MARK_CODES` gains `low_confidence_source` with the kind `unclear word`, ordered number, possibly not speech, unclear word, unsure. `line_marks` earns the kind when a quoted span holds a word with `probability < UNCERTAINTY_THRESHOLD` and holds no suspect word; it is earned on any speaker's line, the clinician's included, and on a line that also earns `number`. Check 1's per-line loop skips this kind, so the per-word warnings stay exactly as they are and no line-wide `low_confidence_source` is ever emitted. The renderers get the mark from the existing per-word warnings through `line_marks_by_assertion` and `section_marks_line`, dropping it where the same assertion carries `suspect_source`; the line editor gets it from `quoted_line_marks`. The two must agree on every freshly checked line whose words rebuild its text (the one-rule test: the note's warnings and the editor's reading made under the same rule from the same document). Outside that, each is pinned on its own: a removed, replaced, coordinate-free or mismatched row shows no mark in the editor (`ui/models.py:3411-3434`); a stored note's renderings follow its stored warnings whatever rule made them; `suspect_source` on the same assertion wins in both. Consequences: no warning changes, so `REVIEW_MARK_CODES`, the surfaced-doubt measure, the replay's review count and `len(NOTE_WARNING_SEVERITY)` are untouched; no stored schema change; a structured note saved before the upgrade shows the mark wherever it is rendered again (it comes from its stored warnings), while a generated-body snapshot is stored text and never changes: on Past sessions the saved-note pane of an older entry gains the mark and its generated pane does not (`ui/past_sessions.py:526-535`), and after a rollback the saved-note pane loses it while a snapshot made on the new build keeps its mark text. No reader changes behaviour on a low-confidence word. "Acknowledge all" keeps clearing the row unless the practitioner decides otherwise at Task 2.4.
  Alternatives considered: a new per-line review code (rejected: two review rows for one doubt, a new stored code that can never be retired, a rollback section, and an inconsistent "Acknowledge all"); rendering only, with no kind in `line_marks` (rejected: the line editor reads `quoted_line_marks`, not warnings).
- **D4 — No harness credit change.** D3 changes no warning, so no metric moves. Line-wide credit is a metric loosening and is only reported for the brief, from Task 0.3's paired word-reach and line-reach rows of the real `encounter_metrics`. Bar C is a different measurement (a low-confidence word beside a dropped word): a deleted token has no hypothesis word for `_marked_words` to mark, so it says nothing about harness credit.
- **D5 — Dropped words are measured, not built.** Tokens are the canonical reference and hypothesis tokens `encounter_metrics` aligns; the alignment is its `_Alignment`; a canonical hypothesis token's raw words are `hypothesis.consumed[j]` (segment and word positions, `validation.py:1774-1789`); a quoted line is D9's. The population is take 1's 183 encounters throughout D5, bar C and Phase 1's condition; take 2's 44 are printed apart and count toward nothing. The classification order is fixed.
  (1) Join spans first, and locally: a hypothesis token `h_j` and adjacent reference tokens `r_i..r_k` (`k > i`) whose concatenation equals `h_j` ("5km" for "5 km"), where the cells `(i, j)` and `(k+1, j+1)` are linked by an optimal subpath of one substitution and `k - i` deletions (`forward[i][j] + (k - i + 1) + backward[k+1][j+1] == total`). On equal-cost paths either joined reference token can be the deleted one, so this is found before any deletion filter. Every reference token of a join span is class join, counted apart and never scored; a join at one place never exempts the same words deleted elsewhere. The reverse (one reference token rendered as several hypothesis tokens) deletes nothing and is not a run.
  (2) Of the remaining reference tokens, a mandatory deletion is one that lies on a diagonal edge of no optimal alignment. A remaining reference token that has both an optimal deletion edge and an optimal diagonal (one of a repeated pair, as `a x x b` heard as `a x b`) is a floating deletion: a possible deletion with an equally optimal diagonal (for a repeated pair one copy is lost but not which; for `a b` heard as `b a` no token need be lost at all), so it is neutral and never scored. (3) Adjacent mandatory deletions form a run. (4) A run's boundary is the hypothesis position `j` at which its first token's `deletion(i, j)` is optimal: one such `j` locates the run, several make it ambiguous (counted apart, never scored).
  (5) Raw span, the one mapping used for placing a run and for matching alarms: for a located run at `j`, L is the last raw word consumed by token `j - 1` and R the first raw word consumed by token `j`; the run's raw span is every raw-word boundary from L to R in document order (raw words that gave no token lie inside it). When L and R are one raw word (a split), the span is that word's two boundaries. At `j = 0` the span is the boundary before R; at `j = m`, the boundary after L. A run whose neighbour token has no raw word is unscorable, counted apart.
  (6) Place: inside a quoted line when L and R (or the one word) lie under the same note line's coordinates; at a line's edge when exactly one does, or they lie under different lines; unquoted when neither does. A run at the encounter's first or last word is placed by its one neighbour (edge or unquoted, never inside), and a run across a segment boundary is never inside (a note line lies within one segment).
  (7) The scored population is the located runs that hold a content or fact token and are inside a quoted line. Every other run (join, ambiguous, unscorable, edge, unquoted, no content token) is neutral and printed in its own row. Neutral boundaries, for the scoring below: a located neutral run gives its raw span; an ambiguous run gives the raw span at each of its optimal positions; a floating deletion gives the raw span at each of its optimal deletion positions; a join span gives the two boundaries of each raw word its hypothesis token consumed; an unscorable run gives none. The scratch's self-test pins these worked cases before any trace is read: an ambiguous join; a join with the same words deleted elsewhere; a unique boundary; a split word at the boundary; a raw word without a token inside the span; a segment boundary; an encounter end; an alarm at one of an ambiguous run's two positions (neutral, never a false alarm); a split word ending a segment before a zero-word segment (not a hit); a repeated token with one copy dropped (an alarm beside the surviving copy is neutral).
  Signals. Each family emits alarm units whose alarmed boundaries are raw-word boundaries computed from the hypothesis alone, so the same function counts them on real speech. A zero-word segment between text-bearing segments (0.3, 0.5, 1.0 s): the unit is the segment, alarming the boundary between its neighbours. A sparse segment (at least one raw word, and at most 1.0 or 1.5 words per second over at least 1.5 s; a zero-word segment belongs to the zero-word family only): the unit is the segment, alarming every boundary between its words and its two outer boundaries. A low-confidence word (below 0.60, one variant, no selection): the unit is the word, alarming its two boundaries; bar C reads this family. From Phase 1: a gap (inner, leading or trailing) that would hold 1, 1.5 or 2 words at the segment's own pace: the unit is the gap, alarming its own boundary. The pace is seconds per word while speaking: the sum of the segment's word durations (`end_seconds - start_seconds`) over its word count; a segment whose word durations sum to 0 raises no gap alarm. An inner gap is the next word's start minus the previous word's end, a leading gap the first word's start minus the segment's start, a trailing gap the segment's end minus the last word's end; a gap alarms at cutoff k when its seconds are at least k times the pace (the self-test's case: two half-second words and a one-second gap in a three-second segment is 2 words at speaking pace, an alarm at every cutoff, where whole-segment pace would give none). Also from Phase 1: a stretched word (0.8, 1.0, 1.5 s): the unit is the word, alarming its two boundaries. The zero-word family is exempt, by rule, from scored matching and from selection: it alarms a segment boundary, which lies inside no quoted line (only a split word ending a segment could put a scored run's span there, and the self-test pins that case as not a hit). All three of its cutoffs are reported descriptively, by their hits on located content runs at an edge or unquoted, and its inside-line threshold is inapplicable. The three per-decode numbers raise no alarm: for each, the table gives its median over decode windows holding a scored run and over windows holding none, and the count of windows with no value. One value per window and number: the lowest average log-probability, the highest compression ratio and the highest no-speech probability among its words' finite values (the reduction `guard_eval.py:527-541` uses for the first two); a window with no word or no finite value has none; no cutoff, no selection, no threshold verdict (they are excluded as a product signal).
  Scoring, per alarm unit and in this order: a hit when one of its alarmed boundaries lies in a scored run's raw span (a run counts as hit once per family variant however many units land on it); otherwise neutral when one lies in a neutral run's raw span; otherwise a false alarm when at least one of its alarmed boundaries is inside a quoted line (both adjacent raw words under one note line); otherwise outside (printed, never counted). The false-alarm rate is false alarms over every encounter of the half that is in the measurement: all of the half's encounters for the trace-level families, the matched encounters after P1's exclusions for the timing families.
  Selection, to limit a forking-paths search: on the development half (`scripts`, `heldout`, `heldout-2`, `heldout-3`) one variant per family is chosen: the most hits among variants at no more than 1 false alarm per 2 encounters, ties to the fewer false alarms and then the stricter constant (the longer duration, the lower pace, the larger gap); if no variant is inside that limit, the fewest false alarms, then the most hits, then the stricter constant, labelled so. Only that variant is scored, unchanged, on the confirmation half (`heldout-4`, `heldout-5`, `heldout-6`). Fewer than 5 scored runs on the confirmation half, counted again after P1's exclusions for the timing families, is reported as unmeasured there. Reporting threshold for "worth an amendment": at least half of the scored runs hit at no more than 1 false alarm per 2 encounters, on a measured confirmation half.
  Alternatives considered: building a signal in this plan (rejected by the practitioner, 2026-11-20).
- **D6 — Real speech gives load, never hit rate.** `lcm-measure-kept.py` copies `ffl-measure-kept.py`'s frame: the replay's refusal order (developer channel, enrolment, config, folder, entries, the crash-report exclusion check, the single-instance lock held to the end, the offline environment), ordinals only, `--list`, COMPLETE / INCOMPLETE, errors by type name only. It reuses `replay_kept._open_store` and `_load_models`, `kept_session_ids`, `read_recording`, `transcribe_in_temporary_store(persist_key=False)` and `validation._compose_note`; it reads neither the kept transcript nor the saved note, and it never captures decode numbers. Quoted-line columns need the confirmed clinician (`--enrolment`); transcript-wide columns print for every recording. One pass, under the installed app's own configuration; every run prints the same kind of paste block (Task 2.1), and Task 2.2 says which blocks are relayed. Both it and `lcm_lib.py` are hash-frozen before the run. After the freeze, a change to any measurement file (these two, `lcm-measure.py`, Task 1.1's capture adapter) re-opens Task 2.1 for the changed path before the files are used again and before any evidence from them serves a decision, a release or the close: the affected tables, branches and comparisons are re-run (a corrected capture adapter re-captures first, Task 1.1), the changed path is reviewed again (the security review too when refusals, custody or output are touched), the whole final self-test passes against the replacement files, and the hashes are re-recorded. Then Step H's stop rule is read. A change that could alter the real-speech path or its numbers after a verdict-bearing block was recorded supersedes that block (Task 2.2); it is never answered by a second relayed run.
  Alternatives considered: a second pass under `validation\config` (rejected: the load that matters is the one the installed app would show).
- **D7 — Renderings go in the brief, not the build.** Which counted "wrong" facts are spelling, word-form or unit renderings is a question about the measurement. This plan lists them for the brief and amends no metric.
- **D8 — The brief's home and limits.** `docs/testing/exit-gate-options.md`, with one pointer line from `docs/pilot/README.md`. It may not: edit `docs/pilot/exit-gate.md` or any rule file; add a tickable or "proposed wording" line; present seen-set numbers as predictions or as a gate reading; offer shadow-off after a failed run without saying it needs a new dated decision against `plan-validation-run8.md` D7; propose a metric or rule amendment without saying it needs a new rule version, a fresh blind set and pre-registration; carry anything from real speech beyond the paste block's status, recording counts and verdict words, any session id, any per-recording figure or any word from a kept recording. It lists `exit-gate.md`'s two pending wording proposals as open items.
  Alternatives considered: `docs/pilot/` (rejected: that folder holds the run-and-judge documents, and a brief there reads as a third gate proposal).
- **D9 — Bar B (i)'s definition (frozen with the bars).** The alignment is the one `encounter_metrics` builds for the encounter (canonical tokens). A transcript word is in error when a canonical hypothesis token that consumed it is flagged by `_Alignment.possibly_unsupported()` (substituted or inserted on some optimal alignment, `validation.py:1333-1347`), mapped to words through `hypothesis.consumed` exactly as `encounter_metrics` maps unsupported lines (`validation.py:2211-2225`); a token that consumed several words flags each of them. A deletion is not a word error here (it has no hypothesis word to mark; deletions are D5's subject). A quoted line is a note assertion with transcript coordinates whose words rebuild its text; it holds a word error when at least one word under its coordinates is in error. Group M is the quoted lines earning the new kind under D3 at 0.60, membership anchored on the stored `low_confidence_source` warnings (D2's tie rule); group N is every other quoted line, suspect lines included. Suggested lines are in both groups as the gate notes hold them.
  Alternatives considered: counting deletions as word errors (rejected: nothing on the line could carry the mark).

## Schema / Data Changes
- No stored schema change (D3). Stored content that changes after a build: the generated note body kept in `generated.enc` and the Past-sessions archive is the rendered text with check marks, so it carries the new mark text; an older build shows it as text. Snapshots are kept byte for byte in both directions: an older snapshot never gains the mark, and a newer one keeps it after a rollback; only a structured saved note follows the reader's rule. Rollback needs no data step.

## Config / Environment / Deployment Impact
- No environment variable, no new dependency, no config file.
- If built: one version bump (Task 4.1), a build of record by the CI `Release` workflow, an install on this computer with shadow mode on. `docs/release/pilot-builds.md` gains the build's row and a short rolling-back note (no data step; the mark disappears from every re-rendered note and stays as text in generated snapshots made on the new build).

## Critical Constraints
- **C1 — No product change before the exit decision.** Before Task 2.4 only the plan, the scratch and Task 2.3's documents change.
- **C2 — Real data.** The agent never reads, plays or describes a kept recording, transcript or note, and reads nothing of the practitioner's console beyond the paste block (Task 2.1). No real-speech quantity enters a tracked file or the paste block: the load is recorded as one verdict word per threshold, with the run's status and recording counts, over at least 2 recordings; no session id, per-recording number, pooled total or accent count. Real paths are given in chat from `AGENTS.local.md`, never written in the plan, and a command with a placeholder path is never printed for the practitioner.
- **C3 — Synthetic only** in `C:\lcm-sets\` and `.cursor/loops/lcm-out/`. The synthetic and real-data entry points are separate files that share no id-printing code. Decode numbers are never captured on real data.
- **C4 — Frozen things stay frozen:** `UNCERTAINTY_THRESHOLD`, the `GUARD_*` constants, the primer, the cue file, the vocabularies, the rule files, the held-out sets, the prompts, the consent texts, the frozen `ffl_*` files. A later change to the mark's rule or to any signal's constants is a new dated decision with this measurement repeated.
- **C5 — Nothing is a gate.** All seven sets are seen: every number here is a measurement, never a run of record. Three provenances are kept apart wherever a number is reported: bar A rests on numbers planning already read (the seven facts' probabilities), so it is a confirmation; the mark's load at 0.60 (54 of 1,153 lines) was read by planning; bar B (i)'s error-share comparison was not read, but it is taken on seen sets, so it is a measurement and never a prediction test.
- **C6 — Freeze before numbers.** Before Task 0.2's commit only `lcm-measure.py --premise` may run, and its log prints difference counts only. The bars, grid and definitions are never changed after a new number has been read.
- **C7 — Long runs** go in the background, lid open, mains power, installed app closed, every Python call in Bash ending `< /dev/null`, and start only on the practitioner's "start now".
- **C8 — Words.** Nothing is committed, pushed, merged or installed without the practitioner's word (under `/execute-loop` with autocommit on, local per-phase commits are authorised). Cloud sessions stay off. Line endings are kept (Codebase Integration Notes).
- **C9 — Shadow mode stays on** before, during and after. `test_shadow_exits.py` is not edited; no copy and no Cliniko write carries a check mark.

## Validation / Verification
- Phase 0: `ffl_lib.py`'s SHA-256 equals its frozen value; the premise at 0 differences on 227, each set's class counts equal to its `_set.json`, the take-1 map reproduced from both row producers (67 rows, 33 counted); the freeze commit precedes every new number; the sweep's T = 0.60, reach = word row equals the stored baseline.
- Phase 1: P1 per encounter (Task 1.2) before any timing signal is scored; excluded encounters named and counted.
- Phase 2: the real-speech script's and `lcm_lib.py`'s hashes match their frozen values before the practitioner's run; the shared counter over the saved gate notes equals Phase 0's tables, and the practitioner path's dry run equals the bare-composition baseline (Task 2.1's three checks); the script's review pass is closed before its hash is recorded; a numbers-only grep over every log.
- Build: `ruff check . && mypy && pytest` green in `desktop/` (baseline 11121 passed, 9 skipped, plus the new tests); `npm run qa` in `extension/` (313 passed); `git diff` of `test_shadow_exits.py` empty; the product comparison of Task 3.4 at 0 differences.
- Live: the practitioner's install smoke (Task 5.5); shadow mode on before and after.

## Deferred / Out of Scope
See the Planning Extraction Summary. In one line each: a dropped-word mark (deferred to an amendment); a stricter mark threshold or any threshold change (deferred to an amendment); harness credit and spelling folds (the brief's, never this plan's); every frozen thing (excluded).

## Current State / Handoff Note
- Last completed step: Planning complete (Plan Mode with Fable, then `/review-plan`, 2026-11-20); codex plan peer-review rounds 1 to 5 applied (2026-11-20; the cap of 5 reached, not converged); a second pass on the practitioner's "another pass", rounds 6 to 10 applied (its cap of 5 reached too, not converged).
- Current in-progress step: `/execute-loop` run `show-the-doubt-20261120-084151-76e5` (started 2026-11-20 on the practitioner's confirm; builds on `main`, isolation none, autocommit on); preflight done, harness probe PASS.
- Immediate next action: spawn the Phase 0 executor (stage-0) for Task 0.1, the premise.
- Loop config: executor=claude-p model="claude-opus-5-5" effort=high profile=default; peer=codex model="gpt-6.2-astra" effort=medium; architect=off; cadence=every-phase; caps=review:3,peer:5; gates=executor; cap-raise=executor; high-auto=on; peer-max=12; notify=action-only; scope=all; autocommit=on; isolation=none; merge=off; perms=scoped; liveness=10; monitor-delivery=auto; verify=composer
- Executor handoff (leg x3), 2026-11-20T09:14:57+11:00, reason=phase-complete: Task 0.2 recorded 🟩 (the practitioner's "Confirm as written (Recommended)", 2026-11-20). Next: the composer's freeze commit of this plan (its hash added to Task 0.2 afterwards), then Task 0.3, the sweep, which builds `--sweep` only after that commit (C6). Task 0.3 not started; nothing run, no number read.
- Executor handoff (leg x2), 2026-11-20T08:58:19+11:00, reason=phase-complete: the premise holds (the composer's run at 2026-11-20T08:58+11:00, exit 0, `PREMISE differences: 0`, log `.cursor/loops/lcm-out/premise-1.log`); Task 0.1 is 🟩. Next: Task 0.2, the practitioner's freeze decision (`[decision]`, MUST-PAUSE; no new number before its commit, C6). Not started.
- Executor handoff (leg x1), 2026-11-20T08:57:03+11:00, Task 0.1 🟨, reason=composer-run: wrote `.cursor/loops/lcm_lib.py` (refuses, exit 2, before importing `ffl_lib` unless its SHA-256 is `f7d2d75c…d38d03`; rebuilds a document from each saved trace, word times spread evenly over the segment; loads each encounter's gate payload, `notes[-1]` and tracked script; Check 1 keys; the suggested segments from the gate note's `m<segment>` lines; the take-1 map's two producers copied from `ffl-measure.py` `map_report`; `map-7.md`'s Failure rows parsed back) and `.cursor/loops/lcm-measure.py` (`--premise` only; `--sweep` and `--runs` refuse until Task 0.2's freeze, C6). The composer runs `cd "/c/Recording clinic software" && .venv/Scripts/python.exe .cursor/loops/lcm-measure.py --premise < /dev/null` (no `--config`: nothing in the premise reads it). Expected: three tables of difference counts (encounter level per take and set, 9 rows; set level, 9 rows; map, 10 checks), each 0, `Encounters checked against the pinned 227: difference 0`, `PREMISE differences: 0`, a last line `log: .cursor/loops/lcm-out/premise-1.log`, exit 0. On a nonzero count, run again with `--details` (ids, check and field names, warning codes only, no value) and resume this leg with the output. Interpretations, for the reviewer: Check 1 is compared in order on (code, severity, section, assertion, coordinates) over the six codes Check 1 emits; the class counts are compared for the gate configuration only (QT and without the reply credit; the `off` configuration has no saved note), members compared as sets; the map is compared by identity (set, encounter, fact or code, predicate) on class and counted disposition, plus the pinned totals 67 and 33; take 2's `_set.json` files are checked too (9 in all).
- Open blockers / open questions: Task 1.1 needs the practitioner's "start now"; Task 2.2 is the practitioner's run from a normal terminal; Tasks 0.2, 2.4, 3.1, 4.1 and 4.3 are the practitioner's decisions.
- Last plan sync: 2026-11-20

## Review History
- 2026-11-20 — `/review-plan` (Fable 5.2; two subagent lenses: practicality against the code, coverage and risk against the project's rules) — 8 HIGH / 22 MED / 12 LOW raised across the lenses, all disposed in this hardened plan: the mark with no new warning code (D3), the dropped-word half measured and not built (the practitioner's choice), P1 made per encounter with a retry and a tolerated maximum, firm bars fixed before any new number, records and hardening on every exit, the real-speech script's full specification, the brief moved to `docs/testing/`, the version as a decision, a discovery run in place of a closed test list.
- 2026-11-20 round 1: 0 CRIT / 4 HIGH / 12 MED / 2 LOW; skew=none; action=none (codex `gpt-6.2-astra` medium plan peer-review; Materiality 16 build-affecting / 2 record-only / 0 invalid, verified as labelled; all eighteen applied as plan amendments; round 2 owed — plan mode never converges on round 1)
- 2026-11-20 round 2: 0 CRIT / 4 HIGH / 9 MED / 3 LOW; skew=none; action=none (codex `gpt-6.2-astra` medium plan peer-review, a fresh peer; Materiality 14 build-affecting / 2 record-only / 0 invalid, verified as labelled; all sixteen applied as plan amendments; not converged — round 3 owed)
- 2026-11-20 round 3: 0 CRIT / 3 HIGH / 5 MED / 1 LOW; skew=mixed; action=none (skew corrected 2026-11-20: about six of the nine were against text written by round 2's fixes; codex `gpt-6.2-astra` medium plan peer-review, a fresh peer; Materiality 8 build-affecting / 1 record-only / 0 invalid, verified as labelled; all nine applied as plan amendments; not converged — round 4 owed)
- 2026-11-20 round 4: 0 CRIT / 2 HIGH / 9 MED / 1 LOW; skew=mixed; action=none (skew corrected 2026-11-20: about six of the twelve were against text written by round 3's fixes; codex `gpt-6.2-astra` medium plan peer-review, a fresh peer; Materiality 11 build-affecting / 1 record-only / 0 invalid, verified as labelled; all twelve applied as plan amendments, four of them by simplifying: the paste block holds verdict words only, and the measurement is hardened before the exit decision with a stop rule after it; not converged — round 5, the cap's last, owed)
- 2026-11-20 round 5: 0 CRIT / 1 HIGH / 3 MED / 2 LOW; skew=mixed; action=none (skew corrected 2026-11-20: four of the six were against text written by round 4's fixes; codex `gpt-6.2-astra` medium plan peer-review, a fresh peer; Materiality 4 build-affecting / 2 record-only / 0 invalid, verified as labelled; all six applied as plan amendments; CAP REACHED at round 5 of 5, NOT converged — build-affecting findings by round: 16, 14, 8, 11, 4; round 5's fixes have not been re-read by a peer)
- 2026-11-20 round 6: 0 CRIT / 2 HIGH / 5 MED / 2 LOW; skew=mixed; action=none (second pass, round 1 of a cap of 5, on the practitioner's "another pass"; codex `gpt-6.2-astra` medium plan peer-review, a fresh peer; Materiality 7 build-affecting / 2 record-only / 0 invalid, verified as labelled; three of the nine were against text written by round 5's fixes; all nine applied as small local amendments; round 7 owed — a pass never converges on its first round)
- 2026-11-20 round 7: 0 CRIT / 1 HIGH / 3 MED / 1 LOW; skew=mixed; action=none (second pass, round 2 of 5; codex `gpt-6.2-astra` medium plan peer-review, a fresh peer; Materiality 4 build-affecting / 1 record-only / 0 invalid, verified as labelled; two of the five were against text written by rounds 5 and 6's fixes; all five applied as small local amendments; not converged — round 8 owed)
- 2026-11-20 round 8: 0 CRIT / 3 HIGH / 1 MED / 0 LOW; skew=fix-induced; action=none (second pass, round 3 of 5; codex `gpt-6.2-astra` medium plan peer-review, a fresh peer; Materiality 4 build-affecting / 0 record-only / 0 invalid, verified as labelled; all four were against text written by round 7's fixes, so they were applied by simplifying, not by adding branches: one verdict-bearing block is ever relayed, and one rule covers any change to a measurement file after the freeze; not converged — round 9 owed)
- 2026-11-20 round 9: 0 CRIT / 0 HIGH / 3 MED / 0 LOW; skew=mixed; action=none (second pass, round 4 of 5; codex `gpt-6.2-astra` medium plan peer-review, a fresh peer; Materiality 3 build-affecting / 0 record-only / 0 invalid, verified as labelled; round 8's simplifications were confirmed coherent; all three applied as one-sentence amendments; not converged — round 10, the pass's last, owed)
- 2026-11-20 round 10: 0 CRIT / 0 HIGH / 3 MED / 0 LOW; skew=mixed; action=none (second pass, round 5 of 5; codex `gpt-6.2-astra` medium plan peer-review, a fresh peer; Materiality 3 build-affecting / 0 record-only / 0 invalid, verified as labelled; round 9's fixes confirmed coherent; all three applied as one-sentence amendments; CAP REACHED at round 5 of 5 of the second pass, NOT converged — build-affecting findings by round across both passes: 16, 14, 8, 11, 4, then 7, 4, 4, 3, 3; round 10's fixes have not been re-read by a peer)

## Review Findings Log
### Round 1 — 2026-11-20
Round status: Closed
Source: Codex gpt-6.2-astra medium plan peer-review
Materiality: 16 build-affecting / 2 record-only / 0 invalid
(Composer-recorded: the peer ran read-only and printed its round; transcribed from `.cursor/loops/show-the-doubt-plan-peer-r1.log`, the last `### Round 1` header. Each finding was verified against the code and the plan by the owning planning session before any amendment; all eighteen held as labelled.)

#### PR-HIGH-001: `plan:Task 0.2`, `validation.py:1333-1347` — bar B (i) turns on an undefined "word error"
- Materiality: build-affecting (verified)
- Why it matters: `possibly_unsupported` flags a hypothesis token substituted or inserted on any optimal alignment; a deletion has no hypothesis token and a canonical token can consume several words (`validation.py:1774-1789`, `:2211-2225`), so two implementations could reach different build decisions.
- Proposed amendment: specify the alignment, the mapping from erroneous tokens to quoted spans, whether deletions count, and the empty-group and zero-share outcomes.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D9 (new), Task 0.2 (bar B (i), the freeze list), Planning Extraction Summary (D1 to D9). Siblings reconciled.

#### PR-HIGH-002: `plan:Task 2.1`, `validation.py:3248-3270`, `:3451-3461` — the dry run compares different notes
- Materiality: build-affecting (verified)
- Why it matters: Phase 0's tables come from gate notes that hold suggested lines; the practitioner path calls `_compose_note` bare, so equality with Phase 0 cannot hold, and P1 exclusions change the cohort.
- Proposed amendment: check the shared counter against Phase 0 on the saved gate notes, and the bare path against a baseline made by the same path.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (two checks), Validation (Phase 2). Siblings reconciled.

#### PR-HIGH-003: `plan:Tasks 0.2, 2.2, 2.4`, `ffl-measure-kept.py:793-834` — an INCOMPLETE run could meet the build condition
- Materiality: build-affecting (verified)
- Why it matters: the copied frame prints totals for the successful rows when another entry failed; two successes and one failure could authorise a build without the heaviest note, and two enrolled recordings can give zero quoted lines.
- Proposed amendment: read bar B (ii) only after COMPLETE with a positive pooled quoted-line count; otherwise retry or record unmeasured.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 0.2 (bar B), Task 2.2, Task 2.4 (option (a)). Siblings reconciled.

#### PR-HIGH-004: `plan:C2`, `plan:Task 2.1` — with two recordings the aggregate block discloses each note's count
- Materiality: build-affecting (verified)
- Why it matters: a pooled count and a numeric maximum over two notes give both counts exactly, against C2's no-per-recording rule.
- Proposed amendment: compute the median and maximum tests in the script and print only met or not met with the pooled figures.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (the aggregate block), Task 2.2 (what is recorded), C2. Siblings reconciled.

#### PR-MED-001: `plan:Task 0.1`, `ffl-measure.py:2993`, `:3009-3038` — the premise left out the map's set-level rows
- Materiality: build-affecting (verified)
- Why it matters: the map is built by `classify_trace` per encounter and by `set_level_rows` per set; counted set-level rows exist (`map-7.md:33`, `:50`).
- Proposed amendment: rebuild the take-1 map with both producers and compare row identities and counted dispositions.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 0.1, Validation (Phase 0). Siblings reconciled.

#### PR-MED-002: `plan:Task 0.2` — bar A did not isolate the threshold
- Materiality: build-affecting (verified)
- Why it matters: "some T" over a threshold-by-reach grid lets a wider-reach cell meet the bar, and the 5-point increase had no named baseline.
- Proposed amendment: freeze bar A to word reach and name the baseline numerator, denominator and take.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 0.2 (bar A). Siblings reconciled.

#### PR-MED-003: `plan:D2`, `ffl_lib.py:2025`, `note_check.py:643` — rounded ties had no decision rule
- Materiality: build-affecting (verified)
- Why it matters: a trace stores 4-dp probabilities and the checker tests strict `<`; calling the checker on a tie makes a definite choice the plan called undetermined.
- Proposed amendment: anchor the 0.60 row on the stored warnings and carry unresolved ties as bounds, a straddled bar being indeterminate.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D2 (the tie rule), Task 0.2 (the freeze list), D9 (group M's anchor). Siblings reconciled.

#### PR-MED-004: `plan:D5`, `validation.py:1317-1331` — the deletion filter could discard the joining case
- Materiality: build-affecting (verified)
- Why it matters: for two reference tokens rendered as one fused token, equal-cost paths delete opposite tokens, so neither is deleted on every alignment.
- Proposed amendment: freeze the token representation, classify joining spans before the deletion filter, and pin worked cases.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D5 (steps 1 to 6, the four worked cases). Siblings reconciled.

#### PR-MED-005: `plan:D5`, `plan:Tasks 0.2, 1.3, 2.1` — no reproducible alarm, matching or selection rule
- Materiality: build-affecting (verified)
- Why it matters: the real-speech path must count a signal without knowing where a deletion is; duplicates, segment-to-boundary matching and variant selection were open; the 20-run trigger could pass with no confirmation runs.
- Proposed amendment: freeze how each signal alarms from the hypothesis alone, how alarms match runs, how duplicates count, how one variant is selected, and an unmeasured confirmation half.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D5 (signals, scoring, selection, the floor of 5), Task 0.2 (Phase 1's condition), Task 2.1 (every grid variant). Siblings reconciled.

#### PR-MED-006: `plan:D3`, `ui/past_sessions.py:526-535`, `ui/models.py:2644-2666` — two display paths were conflated
- Materiality: build-affecting (verified)
- Why it matters: Past sessions shows the generated snapshot verbatim and re-renders the saved note; an old snapshot cannot gain the mark and a new one keeps it after a rollback.
- Proposed amendment: test and document both panes in both directions.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D3, Schema / Data Changes, Config / Deployment, Tasks 3.3 and 4.2. Siblings reconciled.

#### PR-MED-007: `plan:D3`, `ui/models.py:3411-3434`, `note.py:943-949` — editor and renderer parity needs a scope
- Materiality: build-affecting (verified)
- Why it matters: the renderer reads stored warnings; the editor recomputes from the words and shows nothing for removed, replaced, coordinate-free or mismatched rows; a stored note's warnings are not rederived.
- Proposed amendment: require parity for freshly checked, reconstructable lines and pin the other cases apart.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D3, Task 3.3. Siblings reconciled.

#### PR-MED-008: `plan:Task 3.3`, `note.py:1292-1298` — the Check 5 test named the wrong boundary
- Materiality: build-affecting (verified)
- Why it matters: the count line is appended after the usable prose is chosen, so the fold never receives it; teaching the fold to ignore text would change clinical checking.
- Proposed amendment: assert the verdict unchanged for the same inputs, and the count line separately.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 3.3. Siblings reconciled.

#### PR-MED-009: `plan:Tasks 2.1, 2.2`, `ffl-measure-kept.py:550-561`, `speaker_eval.py:1076-1089` — the script's first real use preceded its review
- Materiality: build-affecting (verified)
- Why it matters: the pre-run smoke covered argument refusals only; the custody and print-surface inspection came after the practitioner's run, and a hash only identifies bytes already reviewed.
- Proposed amendment: inspect and exercise the sensitive paths with synthetic failures and review the script before the freeze; keep H3 for the final diff.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (the pre-freeze inspection and review), Validation (Phase 2). Siblings reconciled.

#### PR-MED-010: `plan:Tasks 2.3, 2.4`, `docs/pilot/README.md:177-184` — outcome-dependent records came before the decision
- Materiality: build-affecting (verified)
- Why it matters: the predecessor plan's line differs by exit, and the pilot gives entering findings to the practitioner.
- Proposed amendment: keep the tables in 2.3, take the register disposition at 2.4, write the predecessor lines at close.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Tasks 2.3, 2.4 and 5.7. Siblings reconciled.

#### PR-MED-011: `plan:Task 5.5`, `ui/models.py:1925-1942` — the smoke asked for a Copy that shadow mode refuses
- Materiality: build-affecting (verified)
- Why it matters: a shadow recording's note cannot be copied, and a prose section shows a count line, not a mark on the line.
- Proposed amendment: have the practitioner check the refusal, the line marks in clean and verbatim, and the prose count line.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 5.5. Siblings reconciled.

#### PR-MED-012: `plan:Task 5.6`, `replay_kept.py:471-490` — the replay's Totals line holds no review count
- Materiality: build-affecting (verified)
- Why it matters: the per-session review count is printed beside a session id; the pasted totals cannot show review parity.
- Proposed amendment: prove review-count parity synthetically and limit the practitioner replay to its existing totals.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Tasks 3.4 and 5.6. Siblings reconciled.

#### PR-LOW-001: `plan:Key Findings` — 54 lines cannot span 72 encounters
- Materiality: record-only (verified)
- Why it matters: each encounter counted needs at least one such line.
- Proposed amendment: name the population or drop the figure.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Key Findings (the figure dropped; Task 0.3 prints the incidence). Siblings reconciled.

#### PR-LOW-002: `plan:C5`, `plan:Task 2.3` — bar B (i) carried two provenance labels
- Materiality: record-only (verified)
- Why it matters: the error share was called unread in one place and already read in another; planning read the load, not the share.
- Proposed amendment: record the three provenances apart.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: C5, Task 2.3. Siblings reconciled.

### Round 2 — 2026-11-20
Round status: Closed
Source: Codex gpt-6.2-astra medium plan peer-review
Materiality: 14 build-affecting / 2 record-only / 0 invalid
(Composer-recorded: a fresh read-only peer; transcribed from `.cursor/loops/show-the-doubt-plan-peer-r2.log`, the last `### Round 2` header. Each finding was verified against the code and the plan by the owning planning session before any amendment; all sixteen held as labelled.)

#### PR-HIGH-001: `plan:Tasks 2.1, 2.2`, `ffl-measure-kept.py:816-833` — the pasted block can still disclose one recording's counts
- Materiality: build-affecting (verified)
- Why it matters: the block is pasted even with one contributor or an INCOMPLETE run; a pooled newly-marked count of 16 with the maximum met gives 8 and 8; a third-recording repeat lets the new one be subtracted out.
- Proposed amendment: keep the full report on the console and build a separate paste block that suppresses singleton totals, totals that reveal counts beside the verdicts, and repeat totals, with fixtures.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (the console report and the paste block, `--verdicts-only`, three fixtures), Task 2.2, Task 0.2 (bar B (ii)'s reading), C2, D6, D8, Flow 3, the accepted assumption. Siblings reconciled.

#### PR-HIGH-002: `plan:D6`, `plan:Step H` — hardening can invalidate the decision it follows
- Materiality: build-affecting (verified)
- Why it matters: a correction in Step H can change the real-speech calculation after the exit was chosen, the register written and the brief drafted, and Task 5.2 would follow under the earlier approval.
- Proposed amendment: when a correction changes decision evidence, return to Tasks 2.3 and 2.4 and require a fresh disposition before release.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Step H (H4's line). Siblings reconciled.

#### PR-HIGH-003: `plan:D5`, `validation.py:1316-1331` — a join elsewhere could hide a real deletion
- Materiality: build-affecting (verified)
- Why it matters: the join test was by concatenation alone, with no positional link between the reference and hypothesis spans.
- Proposed amendment: require both spans to lie on one local optimal subpath, and add a worked case with a join and a separate deletion of the same words.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D5 (1) and (7). Siblings reconciled.

#### PR-HIGH-004: `plan:D5`, `validation.py:1624-1666`, `:1774-1789` — canonical boundaries were scored against raw-word alarms
- Materiality: build-affecting (verified)
- Why it matters: a split puts a canonical position inside one raw word, a join absorbs a raw boundary, and punctuation or fillers leave raw words between canonical tokens; different projections change bar C and Phase 1's trigger.
- Proposed amendment: freeze one mapping between canonical positions and raw boundaries for placing and alarms, with unscorable outcomes and fixtures.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D5 (5), (6), (7) and the signals paragraph; Task 2.1 (A). Siblings reconciled.

#### PR-MED-001: `plan:D5` — the scored population and the false-alarm denominator had two readings
- Materiality: build-affecting (verified)
- Why it matters: an alarm landing only on an edge run could count as a hit or as neutral; fallback ties were open; P1 can change both halves before Task 1.3.
- Proposed amendment: define the scored inside population, the hit-then-neutral order, the neutral sets, the encounters in the rate, the fallback tie-break, and re-apply the floor after P1.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D5 (7), the scoring and selection paragraphs; Task 0.2 (Phase 1's condition). Siblings reconciled.

#### PR-MED-002: `plan:D5`, `transcription.py:1298-1327` — the decode numbers had no alarm rule
- Materiality: build-affecting (verified)
- Why it matters: no cutoff, direction or grid was frozen for them, they may be None, and a wordless decode carries no value.
- Proposed amendment: freeze a comparator and values, or the handling of missing windows, before any result is read.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D5 (the decode numbers are descriptive only: medians and a missing count, no alarm), Task 1.3. Siblings reconciled.

#### PR-MED-003: `plan:D5` — the zero-word signal cannot hit the scored population
- Materiality: build-affecting (verified)
- Why it matters: it alarms a segment boundary, and a segment boundary is never inside a quoted line.
- Proposed amendment: report its edge and unquoted detections descriptively and label its inside-line threshold inapplicable.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D5 (the signals paragraph). Siblings reconciled.

#### PR-MED-004: `plan:D4`, `plan:Task 0.2`, `validation.py:1851-1865` — bar C measured adjacency but was called line-wide credit
- Materiality: build-affecting (verified)
- Why it matters: a deleted token has no hypothesis word to mark, and a mark elsewhere on the line affects the reach simulation without meeting bar C.
- Proposed amendment: report bar C as adjacency and take the credit comparison from Task 0.3's paired rows.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D4, Task 0.2 (bar C). Siblings reconciled.

#### PR-MED-005: `plan:D2`, `ffl_lib.py:2024-2026`, `transcription.py:532-545` — two tie assignments do not bound a share
- Materiality: build-affecting (verified)
- Why it matters: all-below and all-above bound a count, not the error share among marked lines; some ties are decidable from the stored `uncertain` flag.
- Proposed amendment: resolve ties from stored evidence first, then give metric-specific bounds or indeterminate, with a mixed fixture.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D2 (the tie rule), Task 0.3. Siblings reconciled.

#### PR-MED-006: `plan:Task 2.1`, `validation.py:2823-2853`, `afq-transcribe.py:231-239` — the comparison lacked a result for several columns
- Materiality: build-affecting (verified)
- Why it matters: Phase 0 prints only the selected variant on the confirmation half and no timing column, and the outcome holds no clinician label.
- Proposed amendment: list the exact common columns, ids and variants, check the rest by fixtures or matched documents, and name the label's source.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (the three checks), Validation (Phase 2). Siblings reconciled.

#### PR-MED-007: `plan:Task 2.1` — one real-speech signal family was missing
- Materiality: build-affecting (verified)
- Why it matters: the low-confidence word's alarm units were not among the real-speech columns.
- Proposed amendment: add its one variant in total and inside quoted lines by the same mapping.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (A). Siblings reconciled.

#### PR-MED-008: `plan:Tasks 2.1, 2.4` — a fallback threshold's load could not be read
- Materiality: build-affecting (verified)
- Why it matters: median and maximum verdicts existed for 0.60 only, and pooled counts cannot separate (9, 0, 0) from (6, 3, 0).
- Proposed amendment: evaluate all three conditions in the script at each fallback threshold and print one verdict each.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (B), Task 2.2, Task 2.4, the deferred threshold item. Siblings reconciled.

#### PR-MED-009: `plan:Tasks 0.3, 3.4`, `replay_kept.py:346-364` — the product comparison needed line identities
- Materiality: build-affecting (verified)
- Why it matters: Task 0.3 gave counts and shares only, so a mark moving between lines would pass; the replay's counter composes a fresh bare note.
- Proposed amendment: save the expected assertion ids for all 227 and compare review-severity counts on the same gate warnings.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Tasks 0.3 and 3.4. Siblings reconciled.

#### PR-LOW-001: `plan:Task 3.1`, `note_check.py:610`, `:656-665` — a reworded kind could collide with an existing one
- Materiality: build-affecting (verified)
- Why it matters: Check 1 inverts the mapping by kind, so a duplicate would suppress or change an existing warning.
- Proposed amendment: require a distinct, non-empty kind and test that every existing kind keeps its code.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Tasks 3.1 and 3.3. Siblings reconciled.

#### PR-LOW-002: `plan:Integration Notes`, `note_check.py:2123-2129` — the digest limit was stated too broadly
- Materiality: record-only (verified)
- Why it matters: a note composed fresh from a rebuilt document finalises against it; only a saved note paired with a rebuilt document is refused.
- Proposed amendment: limit the statement to that pairing.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Codebase Integration Notes, Follow-Up Continuation Notes. Siblings reconciled.

#### PR-LOW-003: `plan:Task 4.2`, `note.py:1292-1300` — the prose fallback was left out
- Materiality: record-only (verified)
- Why it matters: a section with usable prose shows the count line; a fallback section uses the clean rendering and shows line marks.
- Proposed amendment: describe both outcomes.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 4.2. Siblings reconciled.

### Round 3 — 2026-11-20
Round status: Closed
Source: Codex gpt-6.2-astra medium plan peer-review
Materiality: 8 build-affecting / 1 record-only / 0 invalid
(Composer-recorded: a fresh read-only peer; transcribed from `.cursor/loops/show-the-doubt-plan-peer-r3.log`, the last `### Round 3` header. Each finding was verified against the code and the plan by the owning planning session before any amendment; all nine held as labelled.)

#### PR-HIGH-001: `plan:Task 2.1` — the paste block could rebuild the newly-marked counts it withheld
- Materiality: build-affecting (verified)
- Why it matters: it kept the lines marked today and the lines earning the kind; with none marked today the second is the withheld total, and a verdict beside it can force each note's count (3, 3 and 8).
- Proposed amendment: an explicit allowlist, tested across columns and thresholds, keeping the four verdict words.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (B) (the allowlist, no line-mark column, the allowlist fixture), Task 2.2, C2. Siblings reconciled.

#### PR-HIGH-002: `plan:Task 5.6`, `replay_kept.py:479-490` — the drift replay's Totals line can be one recording's
- Materiality: build-affecting (verified)
- Why it matters: the line is summed over successful rows, and two confirmed recordings at Task 2.2 do not guarantee two successful replays; it also holds more fields than the task listed.
- Proposed amendment: the practitioner checks the replayed count locally and relays the line only at 2 or more, with the permitted fields listed.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 5.6. Siblings reconciled.

#### PR-HIGH-003: `plan:Step H` — a reversed decision could leave the build in a no-change close
- Materiality: build-affecting (verified)
- Why it matters: the return rule refreshed records and skipped release, but the mark, tests, version and documents would stay in the checkout; the other way, hardening done on documents only cannot cover a mark built afterwards.
- Proposed amendment: on a changed disposition, bring the checkout to the new exit and verify it before release or close.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Step H (H4's return rule). Siblings reconciled.

#### PR-MED-001: `plan:Tasks 2.1, 2.2`, `plan:D6` — retries and corrections had no one rule for totals
- Materiality: build-affecting (verified)
- Why it matters: an INCOMPLETE first attempt releases no totals, yet its retry fell under verdicts-only; a wrong total found later could not be replaced by a verdicts-only run.
- Proposed amendment: separate the first release of totals from a status-only attempt, and withdraw superseded totals.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (B), Task 2.2, D6. Siblings reconciled.

#### PR-MED-002: `plan:D5`, `validation.py:1319-1327` — neutral classes had no span for an alarm to match
- Materiality: build-affecting (verified)
- Why it matters: an ambiguous run has several positions, a join is classed before any boundary, an unscorable run has no neighbour; an alarm there could be forgiven or charged.
- Proposed amendment: define each class's neutral boundaries and pin a fixture.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D5 (7) (neutral boundaries, two more worked cases). Siblings reconciled.

#### PR-MED-003: `plan:Tasks 0.4, 1.3, 2.1`, `validation.py:3450-3461` — Task 2.1 compared against counts Phase 0 never produced
- Materiality: build-affecting (verified)
- Why it matters: the counter reports alarm units; the tables report runs hit and false alarms, from which units cannot be recovered.
- Proposed amendment: save unit counts per encounter and variant in Tasks 0.4 and 1.3 and compare on the same gate notes.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Tasks 0.4, 1.3 and 2.1 (checks (1) and (3)). Siblings reconciled.

#### PR-MED-004: `plan:Tasks 1.2, 2.1` — a failed P1 tolerance left Task 2.1 waiting for a table
- Materiality: build-affecting (verified)
- Why it matters: more than ten exclusions leaves Task 1.3 undone while Task 2.1 still required its counts.
- Proposed amendment: treat it as a timing skip downstream and require the empirical comparison only when Task 1.3 produced a table.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Tasks 1.2 and 2.1 (checks (2) and (3)). Siblings reconciled.

#### PR-MED-005: `plan:D5`, `plan:Task 0.2` — which takes count toward the run floors was open
- Materiality: build-affecting (verified)
- Why it matters: 227 encounter-takes include 44 repeats; counting them could cross the 20-run trigger or the floor of 5.
- Proposed amendment: freeze take 1's 183 as the population and report take 2 apart.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D5 (the population), Task 0.2 (bar C, Phase 1's condition), Task 0.4. Siblings reconciled.

#### PR-LOW-001: `plan:D5`, `validation.py:1678-1682` — a split word contradicted the zero-word reasoning
- Materiality: record-only (verified)
- Why it matters: a glued word ending a segment gives a scored run both outer boundaries, so a zero-word alarm could intersect it.
- Proposed amendment: exempt the family from scored matching and selection by rule, and add the fixture.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D5 (the signals paragraph, a worked case), Task 0.4. Siblings reconciled.

### Round 4 — 2026-11-20
Round status: Closed
Source: Codex gpt-6.2-astra medium plan peer-review
Materiality: 11 build-affecting / 1 record-only / 0 invalid
(Composer-recorded: a fresh read-only peer; transcribed from `.cursor/loops/show-the-doubt-plan-peer-r4.log`, the last `### Round 4` header. Each finding was verified against the code and the plan by the owning planning session before any amendment; all twelve held as labelled.)

#### PR-HIGH-001: `plan:Task 2.1`, `note_check.py:642-653` — the first paste block could still fix a positive per-recording load
- Materiality: build-affecting (verified)
- Why it matters: five notes, nine warnings and a `not met` verdict force 9, 0, 0, 0, 0; the accepted zero case does not cover it.
- Proposed amendment: keep the quantities on the practitioner's console and release status, recording counts and verdicts only.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (B) (verdict words only), Task 2.2, Task 2.3, C2, D6, D8, Flow 3, the accepted assumption. Siblings reconciled.

#### PR-HIGH-002: `plan:Task 5.6`, `replay_kept.py:479-489` — two permitted replay totals could isolate one recording
- Materiality: build-affecting (verified)
- Why it matters: a third recording succeeding on a retry lets its kept-word count be subtracted out; the guide's table rows carry session ids.
- Proposed amendment: keep replay totals local and relay execution counts and a local verdict.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 5.6 (counts and a yes or no only), Task 4.2 (the guide's dated line). Siblings reconciled.

#### PR-MED-001: `plan:D6`, `plan:Tasks 2.1, 2.2` — a retry after totals had two instructions
- Materiality: build-affecting (verified)
- Why it matters: COMPLETE with totals, then an INCOMPLETE repeat, then its retry: ordinary by one sentence, verdicts-only by another.
- Proposed amendment: let the first disclosure fix the retry mode for good.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (B) (every run prints the same kind of block; no second mode), D6, Task 2.2. Siblings reconciled.

#### PR-MED-002: `plan:Task 2.1`, `note.py:1057-1069` — a repeat after the build could count the new mark as already visible
- Materiality: build-affecting (verified)
- Why it matters: the renderer derives visible marks from the current `LINE_MARK_CODES`, so after exit (a) every note would show zero newly marked lines.
- Proposed amendment: define already visible by 0.4.0's kinds for the measurement's lifetime, with a before-and-after fixture.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (B). Siblings reconciled.

#### PR-MED-003: `plan:D2`, `plan:Task 2.1` — check (1) could ask an integer to equal a range
- Materiality: build-affecting (verified)
- Why it matters: a quoted word stored as 0.5000 is undetermined at T = 0.50, and a rebuilt document exercises one assignment only.
- Proposed amendment: run the counter under the same tie assignments and compare bounds.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (check (1)). Siblings reconciled.

#### PR-MED-004: `plan:D5`, `validation.py:1317-1325` — a certain deletion of a repeated token was nobody's
- Materiality: build-affecting (verified)
- Why it matters: for `a x x b` heard as `a x b` each `x` has an optimal diagonal, so neither is mandatory and neither boundary was neutral; an alarm there counted as false.
- Proposed amendment: give neutral boundaries to optimal deletion edges whose token also has an optimal diagonal, and pin the case.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D5 (2) (floating deletions), (7) (neutral boundaries, a worked case). Siblings reconciled.

#### PR-MED-005: `plan:D5` — an empty segment also met the sparse rule
- Materiality: build-affecting (verified)
- Why it matters: a 1.5 s zero-word segment satisfies both sparse cutoffs and would bring back the boundary the zero-word exemption removed.
- Proposed amendment: require at least one raw word for the sparse family.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D5 (the signals paragraph). Siblings reconciled.

#### PR-MED-006: `plan:D5`, `transcription.py:360-391` — the gap rule left its pace open
- Materiality: build-affecting (verified)
- Why it matters: whole-segment pace and speaking pace give different alarms for the same gap.
- Proposed amendment: freeze the formula, the comparison and zero durations, with a fixture that tells the two apart.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D5 (the signals paragraph). Siblings reconciled.

#### PR-MED-007: `plan:Step H`, `ui/models.py:2490-2523` — a fresh decision could change the build without changing the exit letter
- Materiality: build-affecting (verified)
- Why it matters: the practitioner can choose (a) again with a different "Acknowledge all" behaviour, and the return rule had no branch for it.
- Proposed amendment: compare the whole disposition and redo what it affects before release.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Step H (the stop rule: any change of disposition stops work and is planned as a hardened amendment). Siblings reconciled.

#### PR-MED-008: `plan:Step H`, `plan:C8` — the no-build check missed uncommitted build-only documents
- Materiality: build-affecting (verified)
- Why it matters: reverting commits cannot remove uncommitted Phase 3 or 4 edits, and the four-folder comparison does not see documents.
- Proposed amendment: remove committed and uncommitted build-only changes and verify every Phase 3 and 4 file.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Step H (the stop rule names committed and uncommitted work; the undo is a hardened amendment). Siblings reconciled.

#### PR-MED-009: `plan:Step H` — the return rule stopped at the checkout after an install
- Materiality: build-affecting (verified)
- Why it matters: evidence corrected after the install could leave the superseded build installed and its build of record published.
- Proposed amendment: add a post-release branch with a practitioner-authorised rollback.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Step H (the stop rule names a published and an installed build); Task 2.1 (the measurement hardened before the decision, so the case is rare). Siblings reconciled.

#### PR-LOW-001: `plan:D5`, `guard_eval.py:527-541` — the decode medians had no per-window reduction
- Materiality: record-only (verified)
- Why it matters: values ride on words, and a window can hold different ones.
- Proposed amendment: name one reduction per number and how missing values count.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D5 (the signals paragraph). Siblings reconciled.

### Round 5 — 2026-11-20
Round status: Closed
Source: Codex gpt-6.2-astra medium plan peer-review
Materiality: 4 build-affecting / 2 record-only / 0 invalid
(Composer-recorded: a fresh read-only peer; transcribed from `.cursor/loops/show-the-doubt-plan-peer-r5.log`, the last `### Round 5` header. Each finding was verified against the code and the plan by the owning planning session before any amendment; all six held as labelled. This was the cap's last round: the pass stopped NOT converged, and these six fixes have not been re-read by a peer.)

#### PR-HIGH-001: `plan:Tasks 0.2, 2.1` — the `unmeasured` verdict gave each recording's count
- Materiality: build-affecting (verified)
- Why it matters: on a COMPLETE run with two or more recordings it meant a pooled quoted-line count of 0, so every recording had none.
- Proposed amendment: keep the zero-denominator diagnosis on the console and print the same outward verdict as a failed load, with a fixture.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 0.2 (bar B (ii)'s reading), Task 2.1 (B) (two verdict words, the identical-blocks fixture). Siblings reconciled.

#### PR-MED-001: `plan:Task 2.2`, `ffl-measure-kept.py:806-814` — a stopped run prints no paste block
- Materiality: build-affecting (verified)
- Why it matters: a custody stop or an interruption returns before the aggregate, leaving nothing permitted to relay or record.
- Proposed amendment: accept a fixed "no complete block" report, apply the one-retry rule, and allow the no-build exit.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.2, Task 0.2 (the retry sentence). Siblings reconciled.

#### PR-MED-002: `plan:Tasks 0.2, 2.1` — a correction before the decision could undo Phase 1's skip
- Materiality: build-affecting (verified)
- Why it matters: a corrected Task 0.4 table can cross the 20-run trigger after Phase 1 was skipped, and the timing tables would not exist.
- Proposed amendment: re-decide the branch when a correction changes its inputs, with the "start now" for a newly required run, and repeat the affected checks.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (the hardening sentence). Siblings reconciled.

#### PR-MED-003: `plan:Task 5.6`, `replay_kept.py:795-810` — the replay's record needed more than the relay allowed
- Materiality: build-affecting (verified)
- Why it matters: `not clean` asked for error type names the relay cannot carry, and a stopped replay prints no report at all.
- Proposed amendment: have the practitioner classify it locally and drop the error types.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 5.6. Siblings reconciled.

#### PR-LOW-001: `plan:D5`, `validation.py:1317-1325` — a possible deletion was called a certain loss
- Materiality: record-only (verified)
- Why it matters: `a b` heard as `b a` has an optimal path with no deletion.
- Proposed amendment: describe the class as a possible deletion with an equally optimal diagonal.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D5 (2). Siblings reconciled.

#### PR-LOW-002: `plan:Follow-Up Continuation Notes` — a counted row was confused with a set verdict
- Materiality: record-only (verified)
- Why it matters: `hld-21/f3` changes class at T = 0.80 while its set still fails, so "removes none of the 33 rows" overstated it.
- Proposed amendment: state the conclusion at set level and point to Task 0.3's paired rows.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Follow-Up Continuation Notes. Siblings reconciled.

### Round 6 — 2026-11-20
Round status: Closed
Source: Codex gpt-6.2-astra medium plan peer-review
Materiality: 7 build-affecting / 2 record-only / 0 invalid
(Composer-recorded: a fresh read-only peer, the second pass's first round; transcribed from `.cursor/loops/show-the-doubt-plan-peer-r6.log`, the last `### Round 6` header. Each finding was verified against the code and the plan by the owning planning session before any amendment; all nine held as labelled.)

#### PR-HIGH-001: `plan:Task 2.1` — the script could be frozen after its privacy fixtures last passed
- Materiality: build-affecting (verified)
- Why it matters: a review fix to the formatter or an exception handler changes no table, so nothing required the fixtures to run again before the hash.
- Proposed amendment: re-run the output and refusal fixtures against the final files before recording the hashes.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (the last step before the hashes). Siblings reconciled.

#### PR-HIGH-002: `plan:Task 5.6`, `replay_kept.py:471-490` — `clean` said each recording's Check errors were 0
- Materiality: build-affecting (verified)
- Why it matters: the word folds a per-row clinical check into the relay, the same all-zero inference round 5 removed from the load verdict.
- Proposed amendment: keep the Check-error reading on the practitioner's screen and define the relay from operational completion and the counts.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 5.6 (`completed` or `not completed`). Siblings reconciled.

#### PR-MED-001: `plan:Tasks 2.2, 2.3, 2.4` — no record form for a run without a block or a verdict
- Materiality: build-affecting (verified)
- Why it matters: two attempts can end in "no complete block", and a COMPLETE run with fewer than two confirmed recordings has no verdict word, yet the records asked for both.
- Proposed amendment: one rule: record only what was received, `load unmeasured` where no verdict exists.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Tasks 2.3 and 2.4. Siblings reconciled.

#### PR-MED-002: `plan:Task 0.2` — the change option reopened the practitioner's fixed limits
- Materiality: build-affecting (verified)
- Why it matters: "change a value before the freeze" covered bar B (ii) and (iii), decided on 2026-11-20.
- Proposed amendment: scope the option to the values still open.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 0.2 (Options). Siblings reconciled.

#### PR-MED-003: `plan:Task 2.1` — nothing checked the median calculation
- Materiality: build-affecting (verified)
- Why it matters: counts of 3 and 4 give a median of 3.5, which truncation would pass; the relay cannot expose the error.
- Proposed amendment: known-answer verdict fixtures: an even cohort at 3.5, equality at each limit, a failure from each limit alone.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (B) (fixtures). Siblings reconciled.

#### PR-MED-004: `plan:Task 2.4` — the fallback could recommend a lower threshold for a non-load failure
- Materiality: build-affecting (verified)
- Why it matters: with (i) failed and the load met at 0.60 and 0.50, the text reported 0.50 as a candidate.
- Proposed amendment: trigger the fallback only on `not met` at 0.60 with `met` lower, from a COMPLETE run.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.4 (Blocks), the deferred threshold item (Revisit by). Siblings reconciled.

#### PR-MED-005: `plan:Task 3.1`, `ui/models.py:2127-2147`, `note.py:1036-1043` — a permitted wording could corrupt a partial selection copy
- Materiality: build-affecting (verified)
- Why it matters: the selection mapper matches the unmarked text greedily, so a kind such as "faint word" would lend its "f" to "from transcript".
- Proposed amendment: test the chosen wording with selections of just the mark and just the provenance label.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Tasks 3.1 and 3.3. Siblings reconciled.

#### PR-LOW-001: `plan:Tasks 1.1, 2.1`, `guard_eval.py:508-526` — the capture adapter was outside the review
- Materiality: record-only (verified)
- Why it matters: swapping two windows' decode values would pass P1, which compares transcript fields.
- Proposed amendment: review the adapter when Phase 1 runs and check window attribution with two distinguishable windows.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (the hardening sentence). Siblings reconciled.

#### PR-LOW-002: `plan:Task 5.7` — the generic mark was taken to settle the number-specific item
- Materiality: record-only (verified)
- Why it matters: a doubtful number and a doubtful word beside a confident number give the same marks, and the mark does not point at the word.
- Proposed amendment: record the coverage and leave the item open unless the practitioner supersedes it.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 5.7. Siblings reconciled.

### Round 7 — 2026-11-20
Round status: Closed
Source: Codex gpt-6.2-astra medium plan peer-review
Materiality: 4 build-affecting / 1 record-only / 0 invalid
(Composer-recorded: a fresh read-only peer, the second pass's second round; transcribed from `.cursor/loops/show-the-doubt-plan-peer-r7.log`, the last `### Round 7` header. Each finding was verified against the plan and the code by the owning planning session before any amendment; all five held as labelled.)

#### PR-HIGH-001: `plan:Task 2.1` — a correction could bring in Phase 1 evidence after its review
- Materiality: build-affecting (verified)
- Why it matters: if the review's own correction turns Phase 1 from skipped to required, the adapter and the timing table did not exist when the peer read, and Task 2.4 could rest on them unseen.
- Proposed amendment: send a Phase 1 that a correction activates through Task 2.1's reviews before the final self-test and the freeze.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (the hardening sentence). Siblings reconciled.

#### PR-MED-001: `plan:D6` — a replacement hash could be recorded without the privacy fixtures
- Materiality: build-affecting (verified)
- Why it matters: the final self-test stood before the first hash only; a re-freeze repeated premises and tables, not the allowlist and refusal fixtures.
- Proposed amendment: make D6 require the whole final self-test against the replacement files first.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D6. Siblings reconciled.

#### PR-MED-002: `plan:Tasks 0.2, 1.2` — Task 1.2 hard-coded a tolerance the practitioner may change
- Materiality: build-affecting (verified)
- Why it matters: Task 0.2 lets P1's tolerance be changed, while Task 1.2 said "more than 10".
- Proposed amendment: compare the exclusion count with the tolerance frozen at Task 0.2.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 1.2. Siblings reconciled.

#### PR-MED-003: `plan:Tasks 2.1, 2.2`, `plan:D6` — two permitted blocks could say something about one recording
- Materiality: build-affecting (verified)
- Why it matters: a `met` verdict over two recordings followed by `not met` over three says the third holds a newly marked line; the plan recommended exactly that repeat.
- Proposed amendment: keep a one-recording-increment repeat local and do not relay or record its verdict.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.2 (which blocks are relayed), Task 2.1 (B), D6, the accepted assumption. Siblings reconciled.

#### PR-LOW-001: `plan:Task 5.7`, `plan:Follow-Up Continuation Notes` — the closeout wording assumed open outcomes
- Materiality: record-only (verified)
- Why it matters: Task 5.7 runs on both exits but described what the mark covers; the note spoke of the brief's chosen route though the brief only recommends.
- Proposed amendment: record whether the mark shipped, and name any later route as the practitioner's choice.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 5.7, Follow-Up Continuation Notes. Siblings reconciled.

### Round 8 — 2026-11-20
Round status: Closed
Source: Codex gpt-6.2-astra medium plan peer-review
Materiality: 4 build-affecting / 0 record-only / 0 invalid
(Composer-recorded: a fresh read-only peer, the second pass's third round; transcribed from `.cursor/loops/show-the-doubt-plan-peer-r8.log`, the last `### Round 8` header. Each finding was verified against the plan and the code by the owning planning session before any amendment; all four held as labelled.)

#### PR-HIGH-001: `plan:Task 2.2`, `ffl-measure-kept.py:683-702` — the repeat-relay check compared the wrong set
- Materiality: build-affecting (verified)
- Why it matters: only recordings with a confirmed clinician contribute, and that is decided afresh on each run, so the same files can contribute two notes on one run and three on the next.
- Proposed amendment: permit a second verdict-bearing relay only when both the kept and the contributing recordings are shown identical, else the local route.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.2 (at most one verdict-bearing block is ever relayed; simpler than a second check), Task 2.1 (B). Siblings reconciled.

#### PR-HIGH-002: `plan:Tasks 2.2, 2.3, 2.4` — a local-only corrected run had no exit
- Materiality: build-affecting (verified)
- Why it matters: `load read locally` had no case in the records, the decision or the fallback.
- Proposed amendment: mark the earlier block superseded and state that only exit (b) is available without a current admissible block.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.2 (`load unmeasured (superseded)`, exit (b) only, an amendment for a fresh reading), Tasks 2.3 and 2.4. Siblings reconciled.

#### PR-HIGH-003: `plan:D6`, `speaker_eval.py:1074-1082` — a replacement script could reach kept recordings unreviewed
- Materiality: build-affecting (verified)
- Why it matters: the re-freeze required the self-test and new hashes, not a review of the changed path.
- Proposed amendment: repeat Task 2.1's review of the changed path, the security review included, before a replacement runs.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D6 (one rule for any change after the freeze; a superseded block is never answered by a second relayed run). Siblings reconciled.

#### PR-MED-001: `plan:D6`, `plan:Step H` — a correction after the decision could leave an old table in force
- Materiality: build-affecting (verified)
- Why it matters: a change to `lcm-measure.py` or the capture adapter fell outside D6, so its table need never be regenerated.
- Proposed amendment: apply Task 2.1's re-runs to any measurement producer before the stop rule is read.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D6 (every measurement file), Step H (H4). Siblings reconciled.

### Round 9 — 2026-11-20
Round status: Closed
Source: Codex gpt-6.2-astra medium plan peer-review
Materiality: 3 build-affecting / 0 record-only / 0 invalid
(Composer-recorded: a fresh read-only peer, the second pass's fourth round; transcribed from `.cursor/loops/show-the-doubt-plan-peer-r9.log`, the last `### Round 9` header. Each finding was verified against the plan and the code by the owning planning session before any amendment; all three held as labelled.)

#### PR-MED-001: `plan:D6`, `plan:Task 2.1` — two reviewed measurement files had no recorded fingerprint
- Materiality: build-affecting (verified)
- Why it matters: D6 covers four files but hashes were recorded for two; the others are git-ignored, so a later session could not tell a changed source from the reviewed one.
- Proposed amendment: record a hash for every measurement source used at each freeze and check it before reusing its evidence.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (the freeze). Siblings reconciled.

#### PR-MED-002: `plan:Task 1.1`, `afq-transcribe.py:211-215` — a corrected adapter could reuse its predecessor's output
- Materiality: build-affecting (verified)
- Why it matters: the copied loop skips an encounter whose pickle exists, and P1 compares transcript fields, so stale decode attribution would pass.
- Proposed amendment: re-capture the affected encounters into a fresh output folder on "start now".
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 1.1, D6. Siblings reconciled.

#### PR-MED-003: `plan:Step H` — the stop rule missed a change of which facts support the decision
- Materiality: build-affecting (verified)
- Why it matters: a correction can swap one newly marked fact for another with every count and verdict unchanged, and the brief reads facts by id.
- Proposed amendment: trigger the stop rule on any changed finding or recommendation the practitioner relied on.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Step H (the stop rule's trigger). Siblings reconciled.

### Round 10 — 2026-11-20
Round status: Closed
Source: Codex gpt-6.2-astra medium plan peer-review
Materiality: 3 build-affecting / 0 record-only / 0 invalid
(Composer-recorded: a fresh read-only peer, the second pass's fifth and last round; transcribed from `.cursor/loops/show-the-doubt-plan-peer-r10.log`, the last `### Round 10` header. Each finding was verified against the plan and the code by the owning planning session before any amendment; all three held as labelled. The pass stopped at its cap NOT converged, and these three fixes have not been re-read by a peer.)

#### PR-MED-001: `plan:Task 2.1`, `ffl-measure-kept.py:735-736` — the first freeze could keep a comparison made with an earlier script
- Materiality: build-affecting (verified)
- Why it matters: a review fix to how the dry run takes the clinician label changes no table or branch, so comparison (2) need not have passed against the hashed file.
- Proposed amendment: run the three synthetic comparisons against the final files, beside the fixture suite, before the first hashes.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 2.1 (the last step before the hashes). Siblings reconciled.

#### PR-MED-002: `plan:Task 1.1`, `speaker_eval.py:1057-1063`, `:1123-1128` — the capture wrapper misses a window served from the cache
- Materiality: build-affecting (verified)
- Why it matters: a PCM-keyed cache sits in front of the provider on the enrolled path, so two identical windows give one recorder call and the copied one-per-window mapping rejects the encounter.
- Proposed amendment: capture results including cache hits and verify identical-PCM and distinguishable pairs.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 1.1 (a mismatch gives missing decode rows, never a failed capture), Task 2.1 (the adapter's check). Siblings reconciled.

#### PR-MED-003: `plan:Task 1.2` — a whole-set retry could leave two eligible captures for one encounter
- Materiality: build-affecting (verified)
- Why it matters: an encounter that matched first can match again with different word times, and the choice changes the gap and stretched-word hits.
- Proposed amendment: keep each first-pass match and use a passing retry only for an encounter that failed first.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 1.2. Siblings reconciled.

## Tasks

Labels: `[decision]` is the practitioner's recorded choice; `[operator]` is an act only the practitioner takes. The "start now" for a long run and the word to commit or push are constraints (C7, C8), not labels.

### Phase 0 — Diagnose from the saved traces
- [x] 🟩 **0.1 Scratch and premise.** Done 2026-11-20 (log `.cursor/loops/lcm-out/premise-1.log`; composer-run, exit 0): 227 encounters checked against the pinned 227 (difference 0); Check 1 and the whole metrics object 0 differences on every take and set; class counts against all 9 `_set.json` files 0 (with and without the reply credit, problems 0); take 1's map against `map-7.md` 0 on every check (67 rows and 33 counted on both sides); `PREMISE differences: 0`. Write `.cursor/loops/lcm_lib.py` and `lcm-measure.py` (D1, D2, D5). Check `ffl_lib.py`'s SHA-256 against `f7d2d75c4e1dbac9ba91413ee7f42d546fc7fc0575e3ffe0b6aba43314d38d03` before importing from it. `lcm-measure.py --premise` prints difference counts only: per encounter, `reconstruction_warnings(note, rebuilt)` against the stored Check 1 warnings (code, assertion, coordinates) and `encounter_metrics(rebuilt, note, script, reference=outcome.reference, suggested_segments=...)` against `outcome.metrics`, whole object, on all 227; each set's class counts against its `_set.json`; the take-1 map rebuilt with both of `ffl-measure.py`'s row producers (`classify_trace` per encounter, and `set_level_rows` after `set_level_problems` and `set_membership_problems` on each `_set.json`) against `map-7.md`, by row identity and counted disposition (67 rows, 33 counted; the counted set-level rows included). Both takes stay in the 227 encounter-level checks; the map is take 1's. Done when every count is 0 and the log name is recorded here.
- [x] 🟩 **0.2 Freeze.** `[decision]` One commit of this plan, before any new number, recording the bars below as confirmed or changed by the practitioner, the grid and tie rule (D2), the definitions (D5, D9) and the declaration of what planning read.
  - Chosen: "Confirm as written (Recommended)" (2026-11-20, the practitioner); rationale: bars confirmed as written; grid, tie rule (D2), definitions (D5, D9) and the declaration of what planning read frozen with them. Bars A, B (i), C, Phase 1's condition and P1's tolerance (10) stand exactly as stated below; bar B (ii) and (iii) unchanged at their recorded values. The freeze commit is the composer's next act; its hash is added here later.
  - Options: confirm the bars as written / change a value still open before the freeze (bar A, bar B (i), bar C, Phase 1's condition, P1's tolerance). Bar B (ii) and (iii) are recorded at the practitioner's values of 2026-11-20 and are not re-asked.
  - Decide after: Task 0.1's premise at 0.
  - Blocks: Tasks 0.3 onward.
  - **Bar A (a threshold change; confirmatory, predicted NOT met):** read at reach = word only. Some T above 0.60 newly marks at least 3 counted wrong facts that the reference reading holds, and at that T the share of quoted lines showing any mark (today's kinds plus the new kind at T) is at most 5 percentage points above the same share with the new kind at 0.60, both over take 1's 183 gate notes and their 1,153 quoted lines. A wider-reach cell never meets bar A. Met or not, no threshold change is built here; met is reported in the brief.
  - **Bar B (the mark at 0.60):** (i) synthetic, unread, by D9's definition: the share of group M (quoted lines earning the new kind) that hold a word error is at least twice the share of group N (every other quoted line), pooled over take 1's 183 gate notes; M empty is unmeasured and not met, N's share 0 with M's above 0 is met, both 0 is not met; (ii) real speech, the practitioner's "1 in 5 lines; median 3, max 8 (Recommended)" (2026-11-20): newly marked lines (earning the kind and showing no mark today) are at most 1 in 5 quoted lines pooled, with a median of at most 3 and a maximum of 8 per note; (iii) at least 2 kept recordings with a confirmed clinician, else unmeasured and no build ("2 is enough for this mark (Recommended)"). Bar B (ii) is evaluated inside the practitioner's script and read as its verdict word at 0.60 (`met` or `not met`; a pooled quoted-line count of 0 prints `not met` with its cause on the console only, because a third word on a COMPLETE run would say each recording had no quoted line) from a paste block whose status is COMPLETE (Task 2.1); an INCOMPLETE run, or a run that stopped before printing a block, is retried once after its cause is fixed, and otherwise the load is recorded as unmeasured and nothing is built.
  - **Bar C (a low-confidence word beside a dropped word; reported only):** at least half of 20 or more scored runs (D5 (7)), over take 1's 183 encounters, are hit by the low-confidence family (D5). It describes adjacency, never harness credit (D4).
  - **Phase 1's condition:** at least 20 scored runs (D5 (7)) over take 1's 183 encounters; otherwise Tasks 1.1 to 1.3 are recorded as skipped. With fewer than 5 of them on the confirmation half, the confirmation read is unmeasured (D5).
  - **P1's tolerance:** at most 10 of 183 encounters excluded after one retry.
- [ ] 🟥 **0.3 The sweep.** `lcm-measure.py --sweep`, T by reach with the real metrics, per set and pooled: facts newly marked (named by id), R1 members against ceilings, the R1 exemption of unsupported lines, `uncertainty_surfaced` and R2, lines earning the kind and newly marked lines (count and share of quoted lines), newly marked lines per note (median and maximum), bar B (i)'s two shares, the suspect-line overlap, and the coupled-threshold harm column. Figures touched by an undetermined tie follow D2's tie rule. The assertion ids earning the kind at 0.60 are saved to `lcm-out/`, keyed by take, set and encounter, for all 227 encounters (Task 3.4 compares against them). Done when the T = 0.60, reach = word row equals the stored baseline and the table is written to `lcm-out/`.
- [ ] 🟥 **0.4 Deletion runs.** `lcm-measure.py --runs`: the ground-truth table by D5's definitions (scored, join spans, ambiguous, all runs; inside quoted lines, at a line's edge and unquoted), the self-test's worked cases passing first, and each scored trace-level family's hits and false alarms: every variant on the development half, the selected variant alone on the confirmation half (D5); the zero-word family's three cutoffs are described apart. All over take 1's 183 encounters, take 2 printed apart. It also saves to `lcm-out/`, per take-1 encounter and variant, each trace-level family's alarm units in total and inside quoted lines, counted on the gate notes (counts from the hypothesis alone, so every variant on both halves), for Task 2.1's check (1). Done when bar C and Phase 1's condition can be read from it.

### Phase 1 — One re-transcription (conditional on Task 0.2's condition)
- [ ] 🟥 **1.1 Capture.** On the practitioner's "start now" (C7): the voice-baseline check; `scripts/build-validation-set.py` for the seven sets into a new `C:\lcm-sets\` (about 3 min; a chain script that refuses an existing root); one take of all seven (about 75 min) with a copy of `afq-transcribe.py` whose provider is wrapped as `guard_eval._RecordingProvider` does, saving the three per-decode numbers per word through the scratch's own `pack_transcription_windows` and `assign_words_to_segments` pass (the document already holds word times). The enrolled path puts a PCM-keyed cache in front of the provider (`speaker_eval.py:1057-1063`), which answers a repeated PCM without a call: when the recorder's calls do not match the pass's packed windows one for one, that encounter's decode rows are counted as missing. This never fails the capture and never touches the timing families. A re-capture, whatever its cause (P1's retry, a corrected adapter), writes into a fresh output folder on the practitioner's "start now": the copied loop skips an encounter whose pickle exists (`afq-transcribe.py:211-215`), so an old folder would silently keep the old capture. Done when every encounter has a pickle and the chain reports 0 problems.
- [ ] 🟥 **1.2 Premise P1.** Per encounter against its saved take-1 trace: segment start, end and label, each word's text, suspect and uncertain flags exact, probability after `round(p, 4)`. A differing set is re-transcribed once into its own folder. An encounter that matched on the first pass keeps its first-pass pickle; the retry's pickle is used only for an encounter that failed first and matches on the retry; an encounter that still differs is excluded by name from every timing signal. The pickle so selected is the one Tasks 1.3 and 2.1 use. More excluded than the tolerance frozen at Task 0.2 (proposed: 10) is a timing skip downstream: stop, report, record Task 1.3 as not done, and Task 2.1 proceeds as if Task 1.1 had been skipped (trace-rebuilt documents in its dry run; the real-speech timing columns still print, checked by fixtures only). The saved gate notes apply to matched encounters, so the 2.6 h language-model baseline is not repeated.
- [ ] 🟥 **1.3 Timing and decode signals.** Scored against Task 0.4's ground truth over the matched encounters, constants chosen on the development half and scored unchanged on the confirmation half (D5). Done when the table states, per timing family, hits, false alarms per encounter and the denominator, and whether D5's reporting threshold is met, not met or unmeasured, and gives the three decode numbers' descriptive rows (D5). It also saves to `lcm-out/`, per matched take-1 encounter and variant, each timing family's alarm units in total and inside quoted lines, counted on the gate notes, for Task 2.1's check (3).

### Phase 2 — Real speech, the records and the exit
- [ ] 🟥 **2.1 The real-speech script.** Write `.cursor/loops/lcm-measure-kept.py` (D6). It prints two things. (A) The console report, which stays on the practitioner's screen and is never pasted. Per ordinal, integers only: words, and words below each T; text-bearing segments, and segments with a word below each T; quoted lines, lines with a visible mark today, lines earning the kind and newly marked lines at each T of 0.30 to 0.60; `low_confidence_source` warnings; contradiction warnings by grade; zero-word segments by duration bucket; and the alarm units of every grid variant of each stored-field-free signal family of D5 (zero-word segment, sparse segment, low-confidence word, gap, stretched word), in total and inside quoted lines, by D5's raw-boundary mapping (every variant, so the columns do not depend on Task 1.3's selection); then the pooled totals and bar B (ii)'s three parts at each T, for the practitioner's own reading. (B) The paste block, the only thing the practitioner pastes, built by one function with an allowlist fixture. It holds exactly: the status line; the counts of recordings expected, measured, failed and with a confirmed clinician; and, only when the run is COMPLETE with at least 2 recordings with a confirmed clinician, one verdict word for each T of 0.30 to 0.60, `load at T: met|not met`, from bar B (ii)'s three conditions evaluated in the script at full precision (at most 1 in 5 pooled, a median of at most 3, a maximum of 8). A pooled quoted-line count of 0 prints `not met` like any failed load, its cause on the console only. It holds no total, count, share, median or maximum of any column. Three review rounds each found a combination of pooled totals and a verdict that fixes one recording's figure (five notes, nine warnings and `not met` can only be 9, 0, 0, 0, 0), so every quantity stays on the practitioner's console. Every run prints the same kind of block; which blocks are relayed is Task 2.2's rule, because two verdict-bearing blocks can say something about a recording that contributes to only one of them, and which recordings contribute is decided afresh on each run (a verdict that turns from `met` to `not met` says the added one holds a newly marked line). "Already visible", for a newly marked line, means 0.4.0's three kinds (`number`, `possibly not speech`, `unsure`), held as a literal in `lcm_lib.py` and never read from `LINE_MARK_CODES`, so a repeat after the mark is built counts the same lines; a fixture shows identical counts with the product mapping as it is and with the new kind added to it. Fixtures: a single contributor; an INCOMPLETE run; a zero quoted-line run and a failed load giving identical blocks; known-answer verdicts (an even cohort whose median is 3.5 is `not met`, the median of an even count being the mean of its two middle values, never truncated; equality at each of the three limits is `met`; a failure owed to each limit alone); the allowlist itself (a block holding anything else fails).
  Three synthetic checks. (1) The shared per-document counter in `lcm_lib.py`, fed the saved gate notes over the same encounters, equals what Phase 0 saved: Task 0.3's line columns at each T over take 1's 183 encounters, and the alarm-unit counts (in total and inside quoted lines) Task 0.4 saved per encounter and variant. Unit counts are compared with unit counts, never with Task 0.4's hits or false alarms. Where D2's tie rule leaves a figure as a range, the counter is run under the same tie assignments and compared range with range; a figure the stored evidence decides is compared as an exact integer. The gate notes hold suggested lines, which the practitioner path never composes. (2) The practitioner path itself (`--dry-run-docs`: bare `_compose_note` under `validation\config`) equals a baseline that `lcm-measure.py --bare` makes with the same bare composition over the same documents and encounter ids: Task 1.1's matched documents with every column (the clinician label from the pickle's `clinician` field, which `afq-transcribe.py:236` saves beside the outcome), or trace-rebuilt documents with the timing columns disabled on both sides (the label from the trace's `clinician` field) if 1.1 was skipped, if P1's tolerance failed, and for any encounter P1 excluded. Check (2) is a plumbing check; its numbers are never reported as Phase 0's. (3) The gap and stretched-word columns, which no Phase 0 table holds, are checked by known-answer fixtures in the self-test and, only when Task 1.3 produced a table, against the alarm-unit counts Task 1.3 saved per matched encounter and variant, counted on the same gate notes.
  A refusal smoke covers a non-folder, an empty folder, no `--enrolment`, a missing `--config`. Before the freeze, the sensitive paths are inspected and exercised on synthetic input (injected fakes where the real check cannot be reached from an agent shell): each refusal in D6's order, the crash-report and single-instance refusals included; an error inside the measurement printed by type name only (the temporary store's custody failure can carry a path, `speaker_eval.py:1076-1089`, so no exception message is ever printed); and an INCOMPLETE run. Then the measurement is hardened before any decision rests on it: one `/review-loop` pass and one cross-family codex round over `lcm_lib.py`, `lcm-measure.py`, this script and the Phase 0 and Phase 1 tables (and, when Phase 1 ran, Task 1.1's capture adapter, its window attribution checked with two distinguishable synthetic windows and with an identical-PCM pair, which must give missing decode rows and an intact capture), and a `/security-review` of this script's refusals, custody and print surface (Step H's H3 re-reads the final diff). A correction that changes a table re-runs it before the freeze. If it changes Phase 1's condition or P1's exclusions, that branch is decided again first (a newly required Task 1.1 run waits for the practitioner's "start now"), and every check the revised branch touches is repeated before the freeze; a Phase 1 that a correction brings in has its capture adapter and its tables put through this same review before the final self-test and the freeze. Last, the three synthetic checks that apply to the final branch and the whole self-test (every output, refusal, custody and verdict fixture) are run once more against the final files, whatever the review changed, and only then are the SHA-256 of the script and of `lcm_lib.py` recorded here, with those of `lcm-measure.py` and, when Phase 1 ran, the capture adapter. The practitioner checks the first two before the run (Task 2.2); the agent checks all of them before any later use of their evidence, so a changed source is noticed.
- [ ] 🟥 **2.2 The practitioner's run.** `[operator]` Both builds closed, mains power, lid open. The agent gives, in chat, one PowerShell command per block with the real paths from `AGENTS.local.md` (no `>` redirect, no placeholder): the two hash checks, `--list`, then the run under the installed app's configuration with `--enrolment`. The practitioner pastes the paste block only. Recorded here: the verdict word at each T, both hashes read True, COMPLETE or INCOMPLETE, the recording counts. No real-speech quantity is recorded. If the script stops before printing a paste block (a refusal, a custody stop, an interruption), the practitioner relays the fixed words "no complete block" and nothing else, no count and no console line; Task 0.2's one-retry rule applies, and with no COMPLETE block the load is unmeasured and only exit (b) is open. At most one verdict-bearing block is relayed and recorded in this plan. Before it, a retry of a run that gave no verdict is relayed (such a block holds a status and recording counts only). After it, no later run's block is relayed: any later run is for the practitioner's own reading. If a correction supersedes the recorded block (D6), the record marks it superseded, the load is `load unmeasured (superseded)`, no lower-threshold verdict is inferred, only exit (b) is open in this plan, and a fresh real-speech reading needs an amendment hardened by a scoped `/review-plan`. An INCOMPLETE block is not read against bar B (Task 0.2).
- [ ] 🟥 **2.3 The records (every exit).** `docs/testing/validation-harness.md`: a dated section beside "Gate-failure map (2026-11)", outside the three rule sections, with the sweep, the deletion-run and signal tables, the real-speech result, only as received (the paste block's status, recording counts and verdict words; `load unmeasured` where no verdict word exists, as for an INCOMPLETE block or fewer than 2 recordings with a confirmed clinician; `load unmeasured (superseded)` where a correction superseded the recorded block; the words "no complete block" where none was printed) and bars A to C read against them (synthetic ids only; each number labelled by C5's provenance: bar A confirmatory, the load at 0.60 already read, B (i) unread on seen sets). `docs/testing/kept-recordings.md`, the threat model's "Kept recordings" measurement scratch and flow 27 of `docs/security/data-flow-map.md` name `lcm-measure-kept.py` beside `ffl-measure-kept.py`. The findings-register entry waits for the practitioner's disposition at Task 2.4, and the predecessor plans' lines for the close (Task 5.7): both depend on the decision.
- [ ] 🟥 **2.4 The exit.** `[decision]` A plain-English brief for the practitioner with the tables against the bars and the executor's recommendation first. For real speech the brief holds what Task 2.3 recorded (the verdict words, or `load unmeasured` in either form, which leaves only exit (b) open); the quantities behind them are on the practitioner's own console from Task 2.2.
  - Options: (a) build the mark at 0.60 (only if bar B is met in all three parts, read from a COMPLETE run) / (b) close with no change. With (a): whether "Acknowledge all" keeps clearing the low-confidence row (default: yes, as today). With either: the practitioner's disposition of the findings-register entry (the pilot's rule: the practitioner enters and closes findings), a row for the visible-mark gap and F-149's control line within the pinned vocabularies (month only), which the agent writes in `docs/pilot/findings-register.md` after the decision.
  - Decide after: Tasks 0.3, 0.4, 1.3 (or its skip), 2.2 and 2.3.
  - Blocks: Phases 3 and 4 and Tasks 5.3 to 5.6, all skipped on (b). A met bar A or C, a signal meeting D5's reporting threshold, or a COMPLETE run whose load verdict is `not met` at 0.60 and `met` at a lower threshold (the load fallback; a bar B failed on (i) or (iii) is no reason for a lower threshold) is reported here and in the brief as a candidate amendment; none is built without one.

### Phase 3 — Build the mark (only on exit (a))
- [ ] 🟥 **3.1 The wording.** `[decision]` The mark's kind string and any reworded warning copy and tooltip.
  - Options: `[check: unclear word]` (proposed) / the practitioner's own wording. Any kind must be non-empty, different from every existing kind (`number`, `possibly not speech`, `unsure`) and must not contain "unsure": Check 1 inverts the mapping by kind (`note_check.py:610`), so a duplicate would change an existing warning. It must also leave the selection copy right: `unmarked_selection` matches the unmarked text greedily (`ui/models.py:2127-2147`), so a kind holding an "f" could swallow the start of "from transcript" (the proposed kind holds none).
  - Decide after: Task 2.4 chooses (a).
  - Blocks: Tasks 3.2 onward.
- [ ] 🟥 **3.2 Discovery run.** With D3's change in a working copy, run the full desktop suite once and name every failing test here before editing any test. Expected to move: `test_note_render.py` (the exact `LINE_MARK_CODES` pin, `TestCheckMarks`, `test_the_code_maps_to_the_unsure_mark_last`), `test_note_check.py` (`test_line_marks_is_the_one_rule`, `TestCheck1LineMarks`), `test_note_matrix.py` (the expected-marks cells), `test_ui_models.py`, `test_ui_screens.py` and `test_ui_review.py` (mark strings; the two loops over `LINE_MARK_CODES` absorb the kind), `test_ui_phase_s.py` (`:389`, `:444`, the 150 % width pins). Not expected to move: `test_validation_metrics.py`, `test_replay_kept.py`, `test_note.py:688`, `test_shadow_exits.py`. A failure outside the expected list is reported before it is touched.
- [ ] 🟥 **3.3 The change.** `note.py` (`LINE_MARK_CODES`, `line_marks`, `line_marks_by_assertion`, `section_marks_line`), `note_check.py` (the per-line loop's skip), `ui/models.py` (copy and, if chosen, `SEPARATELY_ACKNOWLEDGED_NAMES` and `ACKNOWLEDGE_ALL_TOOLTIP`), each to D3's contract. New tests: the kind is earned on a low-probability word in a quoted span, on a clinician's line and on a number line, and not on a suspect line; the editor and the renderers agree on every freshly checked, reconstructable line, and the three cases outside that are pinned apart (a stored note's historical warnings, suspect precedence, a coordinate-free or replaced row); Check 1 emits no line-wide `low_confidence_source`, and every existing kind still maps to its original warning code; clean, verbatim and prose renderings show the mark in order; Copy, a selection copy and the Cliniko body carry none, a selection of just the mark copies nothing and a selection of just the provenance label copies the label; Check 5's verdict on a section is unchanged by this build for the same clinical inputs and raw prose (the section count line is appended after the usable prose is chosen, `note.py:1292-1298`, so the fold never sees it and is not edited), and separately the rendered section gains the count line; a note generated on 0.4.0 and reopened (Recovery, Unreviewed, the Past-sessions saved-note pane) shows the mark from its stored warnings, while the Past-sessions generated pane shows its stored snapshot byte for byte (an old snapshot gains nothing; a snapshot holding the mark text is shown as stored); the longest marked row still fits at 150 %.
- [ ] 🟥 **3.4 Product comparison.** Over all 227 trace-rebuilt documents with their saved gate notes: the product's `reconstruction_warnings` equals the stored Check 1 warnings (no warning changed), the count of review-severity warnings on each gate note is the same before and after the product's Check 1 warnings are swapped in, `encounter_metrics` equals the stored metrics, and the assertion ids the product marks equal, encounter by encounter on both takes, the ids Task 0.3 saved. Done at 0 differences.

### Phase 4 — Version and documents (only on exit (a))
- [ ] 🟥 **4.1 The version.** `[decision]`
  - Options: take 0.4.1 here (proposed) / another number.
  - Decide after: Task 2.4 chooses (a).
  - Blocks: Task 4.2. If 0.4.1 is taken: one dated reconciliation line in `plan-ui-refresh.md` (its Agreed Scope heading and P.4), and every "0.4.1" that means the UI refresh's Phase 6 reworded to "the UI refresh's Phase 6" in the same commit (`AGENTS.md`, `docs/design-system.md`, `docs/security/threat-model.md`, the comment at `ui/review.py:172`). Version fields: `desktop/pyproject.toml`, `scribe_desktop/__init__.py`, `extension/package.json` and the rest of the six.
- [ ] 🟥 **4.2 Documents.** `docs/security/threat-model.md` Phase 3A surfaces 4 and 5 (the mark kinds Copy and the Cliniko body leave out; the named residues: the mark does not point at the word, the transcript's `[word?]` also sits on numbers and names, a successfully rendered prose section shows only a section count line while a section that falls back to the clean rendering shows the mark on its lines, an entry saved before the upgrade shows the mark in its saved-note pane and not in its generated snapshot, and the reverse after a rollback); `docs/security/data-flow-map.md` flows 7 and 10; `docs/security/retention-schedule.md` (no new row; say what stored text changes); `docs/design-system.md` (the mark, its order); `docs/testing/shipping-gate.md` (an addendum: review apparatus, not a rubric change; it must exist before the first consultation on the new build; the 0.3.2 clarification's initials stay open); `docs/testing/kept-recordings.md` (one dated line: the mark changes no replay number, and what Task 5.6 relays); `docs/release/pilot-builds.md` (a short rolling-back note: no data step; re-rendered notes lose the mark, generated snapshots keep their text); `docs/pilot/README.md` (no validation run, shadow mode on, `exit-gate.md` unchanged); `docs/practice/README.md` (the dated per-version line); `docs/practice/clinician-review-guide.md` (`:49-60` and `:122-139` reworded, as drafts awaiting approval); `docs/testing/validation-harness.md` (one dated line: review-mark renderings in reports of record predate the mark); `CHANGELOG.md`, `AGENTS.md` (the transcription-guard pointer names `line_marks`), `PLAN.md`'s delivery note and `docs/architecture/phase-history.md`.
- [ ] 🟥 **4.3 The review guide's lines.** `[decision]`
  - Options: approve the reworded lines / change them.
  - Decide after: Task 4.2.
  - Blocks: Task 5.4 (the install).

### Phase 5 — The brief, hardening, release and close
- [ ] 🟥 **5.1 The exit-gate options brief (every exit).** `docs/testing/exit-gate-options.md` to D8, one page in plain English: the six families of counted failures and what each would take; which counted wrong facts are spelling, word-form or unit renderings (D7); what five plans' measurements say no deterministic rule reaches; the candidate amendments Task 2.4 reported; the realistic routes to shadow-off, each with its cost and its risk, in a recommended order. It decides nothing. One pointer line in `docs/pilot/README.md`.
- [ ] 🟥 **Step H: Hardening pass (every exit; proportional when nothing was built)**
  - [ ] 🟥 H1: `/review-loop` to convergence over the documents, the brief and (if built) the whole code diff. The scratch method and its tables were hardened at Task 2.1 and are re-read only if they changed since.
  - [ ] 🟥 H2: `/simplify`: log findings; trivial → `/fix`, substantial → scoped `/review-plan`. N/A with a one-line record when nothing was built.
  - [ ] 🟥 H3: `/security-review`: the real-speech script's refusals, custody and print surface, and (if built) the mark's exits. Same routing.
  - [ ] 🟥 H4: a cross-family codex re-check, code and documents as separate slices with a per-job evidence line. If H changes a measurement file, D6's rule applies first. Stop rule: if anything after Task 2.4 changes a number, a verdict, a named fact or a recommendation that decision read (a different fact id behind an unchanged count included), or the practitioner changes any part of the disposition (the exit, or a build choice such as the "Acknowledge all" behaviour or the wording), work stops before the next release act (a push, the build of record, an install) and before the close. The corrected reading goes to the practitioner for a fresh Task 2.4 disposition; an approval given on superseded evidence does not carry. What then has to be redone or undone (code, tests and documents, committed or not; a published build; an installed build and its rollback under `docs/release/pilot-builds.md`) is written as an amendment to this plan and hardened by a scoped `/review-plan` before it is carried out. Nothing is reverted, rebuilt, rolled back, released or closed on the old approval.
- [ ] 🟥 **5.2 Build of record (only on exit (a)).** On the practitioner's word: push, the CI `Release` workflow, the attestation and hash checks, the row in `docs/release/pilot-builds.md`.
- [ ] 🟥 **5.3 Re-verify the download.** `[operator]` From a normal terminal (`gh attestation verify`, `Get-FileHash` against `SHA256SUMS.txt`).
- [ ] 🟥 **5.4 Install, shadow mode on.** `[operator]` After the day's last Complete or Discard; reload the extension; restart Chrome.
- [ ] 🟥 **5.5 The smoke.** `[operator]` A mock with one deliberately quiet or mumbled line: a quoted line holding a doubted word shows the mark on the line in the clean and verbatim styles and in the line editor, and a successfully rendered prose section shows its count line; Copy is refused (a shadow recording; what a copy carries is proved by Task 3.3's tests, never here); "Acknowledge all" behaves as chosen; the longest marked row fits at 150 %; shadow mode still on. A second take is allowed; "not observed" is recorded honestly.
- [ ] 🟥 **5.6 The drift replay.** `[operator]` The kept-recordings replay on the installed version's code, run as `docs/testing/kept-recordings.md` says. The relay is operational only: one word, `completed` (exit status 0 and a report with no error) or `not completed` (anything else, a run that produced no report included), with the replayed, error and skipped counts when a report exists. No error type and nothing from a row is relayed or recorded: the per-row columns, Check errors included, are read by the practitioner on their own screen (a `clean` word would say each recording's Check errors were 0), and anything seen there is theirs to raise as a finding in their own words. A `not completed` is investigated on synthetic input only, before the close. No table row and no pooled total is relayed or recorded: totals from two replays over different sets of recordings could isolate one recording. Review-count parity is Task 3.4's synthetic proof (the replay prints no pooled review count, `replay_kept.py:471-490`).
- [ ] 🟥 **5.7 Close (every exit).** The dated decision lines, with one dated reconciliation line each on `plan-follow-on-lines.md` (its plan 2 item) and `plan-validation-run8.md` (Retained item 1: the line records whether the generic mark shipped or was measured and left unbuilt, and what it covers if it shipped, a doubted word on the line, number or not, without pointing at it; the number-specific item stays open unless the practitioner supersedes it); `/document`; the plan's lifecycle state and Retained Follow-Up Items; the practitioner deletes `C:\lcm-sets\` if Task 1.1 ran (`[operator]` part, recorded as open until done).

## Retained Follow-Up Items
(Filled at completion.)

## Follow-Up Continuation Notes
- Focus first: the route the practitioner chooses after reading the options brief (the brief only recommends an order); then a dropped-word amendment if Task 2.4 reported a signal worth one.
- Out of scope later too: tuning any bar, grid or constant on the seen sets after the numbers were read.
- Decisions that still apply: D3 (no new warning code for a doubt the note already records), D5's ground-truth definitions, D8's limits on what a brief may do.
- Do not rediscover: a threshold or reach change clears no seen set's verdict (one row can change class, as `hld-21/f3` does at T = 0.80, becoming an R1 member of a set already at its ceiling; Task 0.3's paired rows are the source for any claim about one row); `mark_words`' threshold is bound at definition; a trace-rebuilt document reproduces Check 1 and the metrics exactly, but a saved note paired with it cannot pass the digest check (a note composed fresh from it can).

---
*Plan saved to: .cursor/plans/plan-show-the-doubt.md*
*To resume in a new session: open a fresh Agent (Ctrl+I), run /start-session, then run /load-plan*
