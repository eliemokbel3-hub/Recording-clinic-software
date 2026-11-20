# Exit gate options (2026-11)

Written at the show-the-doubt plan's Task 5.1 (`.cursor/plans/plan-show-the-doubt.md`, 2026-11-20), for the practitioner to read. **It decides nothing.** It is not a gate proposal: `docs/pilot/exit-gate.md` and every rule file are unchanged, and nothing here is a line to tick. Every synthetic number comes from the seven seen sets (`scripts`, `heldout`, `heldout-2` … `heldout-6`), so it is a measurement, never a prediction or a gate reading. Synthetic ids only; the one real-speech result is the status, recording counts and verdict words this plan recorded.

## Where things stand

- Shadow mode is on and 0.4.0 is installed. The last run of record, run 9 under rule v6, did not meet the gate (`docs/testing/validation-harness.md`, "Runs of record").
- After a failed run the pilot's P.5 stays "keep shadow on" (`.cursor/plans/plan-validation-run8.md` D7). Turning shadow mode off now would need **a new dated decision against that rule**.
- The findings register has no `high` row open. 89 `controlled` rows open their control with "Shadow mode on for every recording" (`docs/pilot/findings-register.md`).

## The six families of counted failures

The gate-failure map (`docs/testing/validation-harness.md`, "Gate-failure map (2026-11)"; the follow-on-lines plan's Task 5.3 brief) has 67 failure rows on take 1. Rule v6 counts 33 of them:

| Family | Counted | What it is | What it would take |
|---|---|---|---|
| Misheard or partly quoted facts, and their residue | 9 | 7 wrong facts with no review mark (2 on a line the answer hop joined or the carry placed, 2 on a suggested line, 2 on a cue-routed line, 1 on a split line), plus recogniser residue over its ceiling on `heldout-3` and `heldout-4` | A better recogniser (none measured did better, below), a visible mark (not met on real speech, below), or a change to how the measurement reads renderings (next section) |
| Silent only on the audio | 6 | A warning lost at audio 3, a split piece 1, a question heard without its question form 1, an overlapped line returned with no words 1 | The later-reply flag with a harness credit reaches 1 (`h2-07/f3`); no candidate reaches the other 5 |
| Next patient or wrongly present | 6 | Next-patient residue over its ceiling on three sets 3, a line a suggested section added 2, a mislabelled segment 1 | A change to the frozen next-patient phrase lists (a new dated decision with a repeated run); a suggestion stage that adds no wrong line; better speaker labelling (`AGENTS.md`, Known Issues) |
| Silent on the script's own words too | 6 | The replier's own cue-routed line closed the reply window 3, no rule reaches it 2, a segment mislabelled at audio 1 | The later-reply flag with a harness credit reaches the 3 (and reverses the answer-hop plan's D4 credit rule); the follow-on line reaches `h2-04/f6` only through a merged speaker label; no candidate reaches the other 2 |
| Uncertainty not surfaced | 5 | 3 encounters, plus uncertainty residue over its ceiling on `heldout` and `heldout-2` | All 17 such facts, on the three sets that count them, were heard correctly, 13 with every word at 0.94 or more (this plan's Key Findings), so a mark on the recogniser's doubt would miss at least those 13. The doubt is in words outside the frozen hedge list (F-098, F-123, F-143); widening the list is a new dated decision with a repeated run |
| An unsupported line | 1 | `h6-09` (F-160: not excused, cause not shown) | — |

## Renderings: right words, written differently?

Plan D7 asks which counted "wrong" facts may be renderings of the right words rather than mishearings. That is a question about the measurement, and it is not decided here. Each is read from the plan's Key Findings, the scripts and the register. For seven of these encounters the register records a misheard word or number (F-091, F-097, F-130, F-141, F-142, F-166, F-172); whether that is the right reading of each fact is the question:

- **Spelling.** `hld-14/f1` and `hld-21/f3`: the reference word written as a different word one letter shorter (heard at 0.90 and 0.77). `h6-13/f1`: a contraction lost its apostrophe; F-158 already records "whether the measurement should fold it is undecided".
- **Word form.** `h6-09/f1`: the reference verb heard in another form, on a line the answer hop joined (F-172).
- **Unit, number or abbreviation.** The four residue facts behind the R1 rows of `heldout-3` and `heldout-4` (`h3-03/f0`, `h3-13/f2`, `h4-01/f5`, `h4-07/f0`). All four already carry a review mark.
- **Not renderings.** `h5-17/f0` is a dropped word (F-149). `h2-15/f9` and `h6-14/f5` are recorded as misheard words on suggested lines (F-169, F-159).

Folding any of these would be a metric amendment, which needs **a new rule version, a fresh blind set and pre-registration**. On today's map a fold alone would not clear `heldout` or `heldout-6`: other counted rows remain there (uncertainty residue on `heldout`; silent facts and next-patient residue on `heldout-6`).

## What has been tried, and what no rule reaches

- **Larger speech model** (2026-11-06, no change). `large-v3` is too slow the app's way, and the two eligible candidates got more material facts wrong than `medium` (F-148).
- **GPU decoding** (2026-11-07, no change). On the graphics card, `large-v3` got 9 material facts wrong and left 28 out silently over five seen sets, against `medium` on the processor's 7 and 26 (F-154).
- **Suggestion repair** (2026-11-15, no-go). Five prompt attempts. Each one that recovered more lost facts also added wrong facts (4 to 7) and next patients' lines (3 to 7) on `heldout-6` ("Suggestion-stage measurement").
- **Answers follow their question** (0.3.7, 2026-11-17). Silent facts went from 25 to 4 on `heldout-2` and from 24 to 8 on `heldout-6` in the gate configuration, with the new reply credit. That is an improvement, not a pass, and it brought one new harm (F-172) ("Answer-hop simulation").
- **Follow-on lines** (2026-11-19, no change). No routing rule makes the gate reachable. 21 counted rows lie outside routing, and no candidate reaches 7 of the 12 silent facts ("Gate-failure map (2026-11)").
- **Show the doubt** (this plan, 2026-11-20, no change; "Low-confidence mark measurement"). On the synthetic sets the mark would carry information (bar B (i), measured on seen sets): 18 of the 99 lines it would mark hold a word error, against 27 of the other 1,054. On 2 kept recordings, both with a confirmed clinician, a `COMPLETE` run gave `not met` for its review load at every threshold from 0.30 to 0.60. At word reach, no threshold above 0.60 newly marks more than one counted wrong fact that the reference reading holds (a suggested line's fact is not held; bar A, confirmatory). A wider reach adds only `h5-17/f0`, from 0.50: the mark lands on the dropped word's neighbour, which says nothing about the deletion itself (the harness section's Bar A bullet). Dropped words cannot be judged: there are 5 scored runs, against the 20 needed.

**What no rule tried so far reaches:**
- confident errors, some of them possibly renderings;
- a dropped word;
- doubt voiced in words outside the frozen list;
- seven of the twelve silent facts.

Two controls hold for these today: the 89 controlled rows above open with the first, and F-149, for one, names both. Shadow mode on for every recording keeps the generated note out of Cliniko. The clinician reads the note against the transcript and writes their own Cliniko note; catching what the generated note gets wrong is the purpose of that review, and no measurement here shows how much of it the review catches. Route 3 below would leave only the second.

**Candidate amendments from this plan: none** (Task 2.4). Bars A and C were not met; the dropped-word signals were scored, but the confirmation half had too few scored runs (4, against the 5 needed) to judge either family; and no lower threshold met the load. The Deferred "stricter threshold" and "dropped-word mark" items stay deferred, because neither trigger has fired.

## Routes to shadow-off, in a recommended order

1. **Keep shadow on and finish the live evidence.** This means the ten eligible shadow consultations scored live under `clean` (Task 9.1, `docs/testing/shipping-gate.md`) and F-088's count.
   - Cost: clinic time only.
   - Risk: none to the record, because a shadow note never reaches Cliniko; the gate stays closed.
   - Every other route reads this evidence.
2. **A measurement amendment, tested cheaply first.** Write it in full as a new rule version: for example, fold the renderings above, count a line already carrying an omission warning as warned (2 such silent facts at audio, `h6-16/f5` and `h6-22/f0`), or give a review mark line-wide credit. Then re-read the seen sets under it. That re-reading is a measurement, not a gate reading. Stop there if counted rows the amendment does not touch remain, as they do on today's map. Only after that come a fresh blind set, pre-registration and a run.
   - Cost: one plan, a blind author and a gate-configuration run of hours.
   - Risk: a measure loosened until it passes. It is controlled only by deciding the amendment before the new set exists.
3. **Change what the gate asks.** Make shadow-off rest on the clinician's review as the control for the families above, judged on route 1's evidence, as **a new dated decision against `plan-validation-run8.md` D7**. The exit gate's "Validation passed" line would be re-worded and approved, and the practice documents' independent review done. In the same commit, the 89 controlled rows would be re-worded to their review-guide control, as that plan's D7 laid down for shadow-off after a pass.
   - Cost: documents and decisions, no build.
   - Risk: every counted family stays in the product, and the clinician's reading of every line becomes the whole control.
4. **A product change aimed at one family.** For example, the later-reply flag with its credit, a dropped-word mark, or a widened hedge or greeting list. Each needs its own plan, version and build of record.
   - Cost: the highest of the four.
   - Risk: new harms. The routing changes measured so far brought harms of their own: F-172 from the answer hop, wrong facts added by every suggestion attempt that recovered more, and one must-stay-out fact quoted by every follow-on-line form. On today's measurements none makes the gate reachable.

**Why this order:** route 1 costs nothing and every other route needs it. Route 2 keeps the gate as it is and can stop after a cheap reading. Route 3 is a choice only the practitioner can make. Every plan listed above tried a change of route 4's kind, and none reached a pass.

## Open items on the exit gate

- The proposed "Validation passed" wording dated 2026-11-06 (rule v5 from run 8; `plan-validation-run8.md` D7), awaiting the practitioner's approval.
- The dated addition of 2026-11-09 for rule v6 (`plan-note-content-design.md` D11). It changes nothing until the first is approved.
